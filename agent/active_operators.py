"""
active_operators -- SOAR Operator implementations.

Pipeline operators (all fire in S2, read/write S1):
  SelectTargetOperator  -> set up comparison agenda from example pairs
  CompareOperator       -> execute one comparison using ARCKG compare()
  ExtractPatternOperator-> cell-level analysis of input/output changes
  GeneralizeOperator    -> create transformation rule from patterns
  PredictOperator       -> apply rule to test input
  SubmitOperator        -> write prediction to output-link, satisfy goal
"""

from agent.operators import Operator
from ARCKG.comparison import compare as arckg_compare


# ======================================================================
# SolveTaskOperator -- abstract top-level goal (S1)
# ======================================================================

class SolveTaskOperator(Operator):
    """
    Abstract operator at S1. Intentionally makes no WM change so
    the cycle detects no-change and creates an S2 substate.
    """

    def __init__(self):
        super().__init__("solve-task")
        self.proposal_preference = "+"

    def precondition(self, wm) -> bool:
        raise NotImplementedError("SolveTaskOperator.precondition() not implemented.")

    def effect(self, wm):
        # Intentionally empty -- triggers no-change impasse -> S2
        return


# ======================================================================
# SelectTargetOperator -- set up comparison agenda
# ======================================================================

class SelectTargetOperator(Operator):
    """
    Reads wm.task to find example pairs and sets up comparison targets.
    For each example pair: compare input grid (G0) vs output grid (G1).
    Writes comparison-agenda, pending-comparisons, and empty comparisons to S1.
    """

    def __init__(self):
        super().__init__("select_target")

    def precondition(self, wm) -> bool:
        raise NotImplementedError("SelectTargetOperator.precondition() not implemented.")

    def effect(self, wm):
        task = wm.task
        if task is None:
            return

        agenda = []
        pending = []

        for idx, pair in enumerate(task.example_pairs):
            if pair.input_grid is not None and pair.output_grid is not None:
                spec = {
                    "type": "grid",
                    "pair_idx": idx,
                    "pair_type": "example",
                    "id1": pair.input_grid.node_id,
                    "id2": pair.output_grid.node_id,
                }
                agenda.append(spec)
                pending.append(spec)

        # Build node lookup so CompareOperator can find ARCKG nodes by ID
        node_lookup = {}
        for pair in task.example_pairs + task.test_pairs:
            if pair.input_grid:
                node_lookup[pair.input_grid.node_id] = pair.input_grid
            if pair.output_grid:
                node_lookup[pair.output_grid.node_id] = pair.output_grid
        wm.node_lookup = node_lookup

        wm.s1["comparison-agenda"] = agenda
        wm.s1["pending-comparisons"] = pending
        wm.s1["comparisons"] = {}


# ======================================================================
# CompareOperator -- execute one comparison
# ======================================================================

class CompareOperator(Operator):
    """
    Pops one item from pending-comparisons, calls ARCKG compare(),
    and stores the result in the comparisons dict on S1.
    """

    def __init__(self, compare_fn=None):
        super().__init__("compare")
        self._compare_fn = compare_fn

    def precondition(self, wm) -> bool:
        raise NotImplementedError("CompareOperator.precondition() not implemented.")

    def effect(self, wm):
        pending = list(wm.s1.get("pending-comparisons") or [])
        if not pending:
            return

        item = pending.pop(0)

        # Find the actual ARCKG nodes
        node_lookup = getattr(wm, "node_lookup", {})
        node_a = node_lookup.get(item["id1"])
        node_b = node_lookup.get(item["id2"])

        if node_a is None or node_b is None:
            wm.s1["pending-comparisons"] = pending
            return

        # Execute comparison
        fn = self._compare_fn or arckg_compare
        result = fn(node_a, node_b)

        # Store result keyed by type and pair index
        key = f"{item['type']}_{item.get('pair_idx', 0)}"
        comparisons = dict(wm.s1.get("comparisons") or {})
        comparisons[key] = {"spec": item, "result": result}

        wm.s1["pending-comparisons"] = pending
        wm.s1["comparisons"] = comparisons


# ======================================================================
# ExtractPatternOperator -- cell-level transformation analysis
# ======================================================================

class ExtractPatternOperator(Operator):
    """
    Analyzes each example pair at the cell level to discover what changes
    between input and output grids. Groups changed cells into connected
    components and records color/position information for generalization.
    """

    def __init__(self):
        super().__init__("extract_pattern")

    def precondition(self, wm) -> bool:
        raise NotImplementedError("ExtractPatternOperator.precondition() not implemented.")

    def effect(self, wm):
        task = wm.task
        if task is None:
            return

        patterns = {
            "grid_size_preserved": True,
            "pair_analyses": [],
        }

        for pair in task.example_pairs:
            g0 = pair.input_grid
            g1 = pair.output_grid
            if g0 is None or g1 is None:
                continue

            analysis = self._analyze_pair(g0, g1)
            patterns["pair_analyses"].append(analysis)

            if g0.height != g1.height or g0.width != g1.width:
                patterns["grid_size_preserved"] = False

        # Inter-Grid COMM over example outputs: are all example G1 identical?
        # This is the evidence R0's `constant_output` matcher keys on — when every
        # example output is the same grid, the answer is that common grid (the
        # COMM-copy path, BACKLOG_LOOP.md R0). Surfaced here as a symbolic signal
        # rather than acted on, so the recognition stays value-agnostic.
        example_outputs = [
            pair.output_grid.raw
            for pair in task.example_pairs
            if pair.output_grid is not None
        ]
        all_equal = bool(example_outputs) and all(
            o == example_outputs[0] for o in example_outputs
        )
        patterns["output_invariant"] = {
            "all_equal": all_equal,
            "evidence_count": len(example_outputs),
            "common_output": example_outputs[0] if all_equal else None,
        }

        # Object-level motion signal (BACKLOG_LOOP.md R1, §2.5-2b). For each
        # example pair, describe what happens to *the single foreground object*:
        # is it unique, are its colour/shape and the grid size preserved, and
        # *where does its bbox top-left land* (src -> dst, with grid/object
        # dims)? Then fit one value-agnostic target expression across the pairs
        # (`agent/dsl_expr.fit_target`: corner / constant / translation). This is
        # the evidence the `object_motion` matcher keys on — surfaced symbolically
        # here so the recognition lives in the matcher and the *destination is a
        # fitted argument expression*, never a literal baked per task.
        patterns["object_motion"] = self._object_motion(task)

        wm.s1["patterns"] = patterns

    # ---- object-level analysis (R1) -------------------------------------

    @staticmethod
    def _object_motion(task):
        """Per-pair object motion analysis using the seed selection vocabulary
        (agent/dsl_expr). Reads only G0/G1 properties — no literal coordinates or
        object indices are baked in, so the resulting signal is value-agnostic.
        Fits three orthogonal argument *expressions* across the pairs so the move
        family resolves to a single rule (§2.5-2b): a *selector* naming which
        object moves (unique/largest/smallest), a *target* naming where it lands
        (corner/constant/translation), and an *output-shape* expression."""
        from agent.dsl_expr import (
            objects_of, position_of, color_of, obj_origin_extent,
            fit_target, fit_output_shape, fit_selector,
        )

        pairs = []
        motions = []     # geometry feeding fit_target, only for clean pairs
        shapes = []      # in/out grid dims feeding fit_output_shape (same pairs)
        selections = []  # (objects, selected idx) feeding fit_selector
        scenes = []      # per-pair scene ("drop"/"preserve"), clean pairs only
        for pair in task.example_pairs:
            g0, g1 = pair.input_grid, pair.output_grid
            if g0 is None or g1 is None:
                continue

            objs_in = objects_of(g0.raw)
            objs_out = objects_of(g1.raw)

            # Identify *which* input object moved and what becomes of the
            # *unselected* objects — both read from the example comparison, never a
            # literal index (§2.5-2b / §2.1 multi-object selection + output). The
            # moved object is matched by colour-set + size (both preserved by a
            # move); `scene` names whether the others are dropped (output holds only
            # the moved object) or preserved (they survive unchanged). An absent /
            # ambiguous match leaves the selection undefined and the pair declines.
            sel_idx, obj_out, scene = ExtractPatternOperator._identify_move(
                objs_in, objs_out
            )
            obj_in = objs_in[sel_idx] if sel_idx is not None else None

            color_preserved = (
                obj_in is not None and obj_out is not None
                and color_of(obj_in) is not None
                and color_of(obj_in) == color_of(obj_out)
            )
            size_preserved = (
                obj_in is not None and obj_out is not None
                and obj_in["size"] == obj_out["size"]
            )
            grid_size_preserved = g0.height == g1.height and g0.width == g1.width

            entry = {
                "scene": scene,
                "selected_ok": obj_in is not None,
                "color_preserved": color_preserved,
                "size_preserved": size_preserved,
                "grid_size_preserved": grid_size_preserved,
            }

            # Record geometry for the target/shape/selector fits only when the
            # pair is a clean object-preserving, size-preserving move of an
            # identified object. The *grid* size may change (easy000i resizes) —
            # that is fitted separately as an output-shape expression — so it is
            # NOT a gate here.
            if (
                obj_in is not None and obj_out is not None
                and color_preserved and size_preserved
            ):
                (oh, ow) = obj_origin_extent(obj_in)[1]
                # H/W are the *output* grid dims so a corner target lands flush in
                # the output grid even when it resizes (size-preserved tasks have
                # output dims == input dims, so this is unchanged for them).
                motions.append({
                    "src": position_of(obj_in),
                    "dst": position_of(obj_out),
                    "H": g1.height,
                    "W": g1.width,
                    "oh": oh,
                    "ow": ow,
                })
                shapes.append({
                    "in": (g0.height, g0.width),
                    "out": (g1.height, g1.width),
                    # object's own bbox extent — lets fit_output_shape recognise
                    # an output whose size is a function of an object property
                    # (the `object_extent` reading, §2.1 / §2.5-2b).
                    "obj": (oh, ow),
                    # number of input objects — lets fit_output_shape recognise an
                    # output whose size is a function of the object *count*, a
                    # grid-level feature (the `object_count` reading, §2.1).
                    "count": len(objs_in),
                })
                selections.append({"objects": objs_in, "selected": sel_idx})
                scenes.append(scene)

            pairs.append(entry)

        # Fit selector + target + output-shape + scene expressions only if every
        # recorded pair is clean (so a task with any dirty pair declines rather than
        # over-generalising). Each is an independent value-agnostic argument
        # expression — which object moves (selector), where it lands (target), the
        # output shape, and whether the unselected objects survive (scene) — letting
        # one rule cover the single- and multi-object move families alike. `scene`
        # fits only when every clean pair agrees (drop *or* preserve, never a mix).
        clean = bool(motions) and len(motions) == len(pairs)
        target = fit_target(motions) if clean else None
        out_shape = fit_output_shape(shapes) if clean else None
        selector = fit_selector(selections) if clean else None
        scene = scenes[0] if (clean and len(set(scenes)) == 1) else None

        return {
            "evidence_count": len(pairs),
            "pairs": pairs,
            "target": target,
            "out_shape": out_shape,
            "selector": selector,
            "scene": scene,
        }

    @staticmethod
    def _identify_move(objs_in, objs_out):
        """Identify which input object the move acted on and what becomes of the
        *unselected* objects, reading both from the input→output comparison (P3/P4)
        rather than a literal. Returns ``(selected_index, output_object, scene)``
        where ``scene`` is:

          * ``"drop"``     — the output holds only the moved object; every other
            input object vanishes (easy000c–i and the size/position/colour-selected
            multi-object tasks).
          * ``"preserve"`` — the output keeps every *other* input object unchanged
            (same pixels at the same place) and exactly one object moved (the
            §2.1 multi-object-*output* concept).

        Returns ``(None, None, None)`` when the pair is not a clean single-object
        move, so the pair declines rather than guessing."""
        # drop: a lone output object, matched back to one input object by the
        # colour-set + size a move preserves.
        if len(objs_out) == 1:
            obj_out = objs_out[0]
            key = (tuple(obj_out["color_set"]), obj_out["size"])
            cands = [
                i for i, o in enumerate(objs_in)
                if (tuple(o["color_set"]), o["size"]) == key
            ]
            if len(cands) == 1:
                return cands[0], obj_out, "drop"
            return None, None, None

        # preserve: same object count in and out; every object but one is
        # byte-identical (same pixels at the same coordinates → it did not move),
        # and exactly one input object has no in-place twin (it moved) and reappears
        # as the one unmatched output object with the same colour-set + size. That
        # unmatched input object is the selected one; the rest survive untouched.
        if len(objs_in) == len(objs_out) and len(objs_in) >= 2:
            used_out = set()
            moved_in = []
            for i, oi in enumerate(objs_in):
                twin = next(
                    (j for j, oj in enumerate(objs_out)
                     if j not in used_out and oj["pixels"] == oi["pixels"]),
                    None,
                )
                if twin is None:
                    moved_in.append(i)
                else:
                    used_out.add(twin)
            moved_out = [j for j in range(len(objs_out)) if j not in used_out]
            if len(moved_in) == 1 and len(moved_out) == 1:
                oi = objs_in[moved_in[0]]
                oj = objs_out[moved_out[0]]
                if ((tuple(oi["color_set"]), oi["size"])
                        == (tuple(oj["color_set"]), oj["size"])):
                    return moved_in[0], oj, "preserve"

        return None, None, None

    # ---- internal helpers ------------------------------------------------

    def _analyze_pair(self, g0, g1):
        """Cell-level diff between input and output grid."""
        raw_in = g0.raw
        raw_out = g1.raw
        h = min(len(raw_in), len(raw_out))
        w = min(
            len(raw_in[0]) if raw_in else 0,
            len(raw_out[0]) if raw_out else 0,
        )

        changes = []
        for r in range(h):
            for c in range(w):
                if raw_in[r][c] != raw_out[r][c]:
                    changes.append({
                        "row": r, "col": c,
                        "input_color": raw_in[r][c],
                        "output_color": raw_out[r][c],
                    })

        groups = self._group_changes(changes)

        group_analyses = []
        for group_cells in groups:
            input_colors = set()
            output_colors = set()
            positions = []
            for cell in group_cells:
                input_colors.add(cell["input_color"])
                output_colors.add(cell["output_color"])
                positions.append((cell["row"], cell["col"]))

            top_row = min(r for r, c in positions)
            top_col = min(c for r, c in positions)

            group_analyses.append({
                "input_colors": sorted(input_colors),
                "output_colors": sorted(output_colors),
                "top_row": top_row,
                "top_col": top_col,
                "cell_count": len(group_cells),
            })

        return {
            "total_changes": len(changes),
            "num_groups": len(groups),
            "groups": group_analyses,
            "size_match": (
                len(raw_in) == len(raw_out)
                and (len(raw_in[0]) if raw_in else 0)
                    == (len(raw_out[0]) if raw_out else 0)
            ),
        }

    @staticmethod
    def _group_changes(changes):
        """Group changed cells into 4-connected components."""
        if not changes:
            return []

        pos_to_change = {}
        for c in changes:
            pos_to_change[(c["row"], c["col"])] = c

        visited = set()
        groups = []

        for change in changes:
            pos = (change["row"], change["col"])
            if pos in visited:
                continue

            group = []
            queue = [pos]
            while queue:
                p = queue.pop(0)
                if p in visited or p not in pos_to_change:
                    continue
                visited.add(p)
                group.append(pos_to_change[p])
                for dr, dc in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                    nb = (p[0] + dr, p[1] + dc)
                    if nb in pos_to_change and nb not in visited:
                        queue.append(nb)
            groups.append(group)

        return groups


# ======================================================================
# GeneralizeOperator -- rule creation from patterns
# ======================================================================

class GeneralizeOperator(Operator):
    """
    Reads extracted patterns and attempts to create a transformation rule.
    Tries multiple strategies in priority order. If no strategy succeeds,
    falls back to an identity rule so the pipeline can still complete.
    """

    def __init__(self, generalize_fn=None, save_fn=None):
        super().__init__("generalize")
        self._generalize_fn = generalize_fn
        self._save_fn = save_fn

    def precondition(self, wm) -> bool:
        raise NotImplementedError("GeneralizeOperator.precondition() not implemented.")

    def effect(self, wm):
        patterns = wm.s1.get("patterns")
        if not patterns:
            return

        rule = None

        # R0 (BACKLOG_LOOP.md): value-agnostic COMM-copy. When every example
        # output is the same grid, the answer is that common output — recognized
        # by the registered `constant_output` matcher (agent/conditions). This is
        # checked *before* the legacy strategies so a constant-output task is
        # solved the intended way — one general {condition, action} rule for the
        # whole family — rather than mis-generalized into a per-task color_mapping.
        # The action carries no literal grid (the grid is reconstructed at predict
        # time from make_grid + coloring), which is what keeps a single rule
        # covering easy000a, easy000b and every other constant-output task.
        if self._matches_constant_output(patterns):
            rule = {
                "type": "constant_output",
                "condition": {
                    "type": "constant_output",
                    "params": {"min_evidence": 2},
                    "min_evidence": 2,
                },
                "action": {"dsl": "copy_common_output", "args": {}},
                "confidence": 1.0,
            }

        # R1 (BACKLOG_LOOP.md §2.5-2b): object-level move with a *fitted* target
        # expression. When every example moves the single foreground object to a
        # destination describable by one value-agnostic target expression
        # (corner / constant / translation — fitted by ExtractPattern), emit one
        # {condition, action} rule. The action carries NO literal target — the
        # destination is re-derived from each task's own example comparison at
        # predict time, then rendered via make_grid + coloring. Because the rule
        # dict is identical for every move task, save_rule merges them into a
        # single rule covering easy000c/g (corner), easy000d/h (constant) and
        # easy000e/f (translation) — the R1 analogue of R0's constant_output,
        # not one detector per variant (§2.5-3). Recognition stays in the
        # registry matcher (`object_motion`), not re-implemented here.
        if rule is None and self._matches_object_motion(patterns):
            rule = {
                "type": "object_motion",
                "condition": {
                    "type": "object_motion",
                    "params": {"min_evidence": 2},
                    "min_evidence": 2,
                },
                "action": {"dsl": "place_object", "args": {}},
                "confidence": 1.0,
            }

        # Strategy 1: sequential recoloring (e.g., color objects 1, 2, 3, ...)
        if rule is None:
            rule = self._try_recolor_sequential(patterns)

        # Strategy 2: simple 1:1 color mapping
        if rule is None:
            rule = self._try_color_mapping(patterns)

        # Fallback: identity (copy input as output)
        if rule is None:
            rule = {"type": "identity", "confidence": 0.0}

        wm.s1["active-rules"] = [rule]

    # ---- recognition: delegate to the condition-matcher registry ---------

    @staticmethod
    def _matches_constant_output(patterns):
        """True iff the registered `constant_output` matcher fires on the
        extracted patterns. Thin wrapper so the matcher (agent/conditions) stays
        the single source of truth for the recognition — GeneralizeOperator does
        not re-implement the predicate, it consults the registry."""
        from agent.conditions import match as match_condition
        try:
            return match_condition(
                "constant_output", patterns, {"min_evidence": 2}
            )
        except KeyError:
            return False

    @staticmethod
    def _matches_object_motion(patterns):
        """True iff the registered `object_motion` matcher fires. Thin wrapper so
        the matcher (agent/conditions) stays the single source of truth for the
        recognition (mirrors `_matches_constant_output`)."""
        from agent.conditions import match as match_condition
        try:
            return match_condition(
                "object_motion", patterns, {"min_evidence": 2}
            )
        except KeyError:
            return False

    # ---- strategy: sequential recoloring --------------------------------

    def _try_recolor_sequential(self, patterns):
        """
        Detect pattern: all changed-cell groups have one source color,
        output colors are sequential (1,2,3,...), ordered by position.
        """
        pair_analyses = patterns.get("pair_analyses", [])
        if not pair_analyses or not patterns.get("grid_size_preserved"):
            return None

        # All pairs must have the same number of change groups
        group_counts = [a["num_groups"] for a in pair_analyses]
        if len(set(group_counts)) != 1 or group_counts[0] == 0:
            return None

        all_source_colors = set()

        for analysis in pair_analyses:
            for g in analysis["groups"]:
                if len(g["input_colors"]) != 1 or len(g["output_colors"]) != 1:
                    return None
                all_source_colors.add(g["input_colors"][0])

            out_colors = sorted(set(g["output_colors"][0] for g in analysis["groups"]))
            expected = list(range(min(out_colors), min(out_colors) + len(out_colors)))
            if out_colors != expected:
                return None

        # Try sorting by different position keys
        for sort_key in ["top_row", "top_col"]:
            if self._check_sort_key(pair_analyses, sort_key):
                start_color = min(
                    g["output_colors"][0]
                    for g in pair_analyses[0]["groups"]
                )
                return {
                    "type": "recolor_sequential",
                    "sort_key": sort_key,
                    "start_color": start_color,
                    "source_colors": sorted(all_source_colors),
                    "confidence": 1.0,
                }

        return None

    @staticmethod
    def _check_sort_key(pair_analyses, sort_key):
        """Verify that sorting groups by sort_key produces sequential output colors."""
        for analysis in pair_analyses:
            groups = analysis["groups"]
            sorted_groups = sorted(groups, key=lambda g: g[sort_key])
            colors = [g["output_colors"][0] for g in sorted_groups]
            if colors != list(range(colors[0], colors[0] + len(colors))):
                return False
        return True

    # ---- strategy: simple color mapping ---------------------------------

    def _try_color_mapping(self, patterns):
        """
        Detect pattern: each input color consistently maps to one output color.
        """
        pair_analyses = patterns.get("pair_analyses", [])
        if not pair_analyses or not patterns.get("grid_size_preserved"):
            return None

        # Collect all observed color transitions
        color_map = {}
        for analysis in pair_analyses:
            for group in analysis["groups"]:
                for ic in group["input_colors"]:
                    for oc in group["output_colors"]:
                        if ic not in color_map:
                            color_map[ic] = set()
                        color_map[ic].add(oc)

        # Each input color must map to exactly one output color
        simple_map = {}
        for ic, ocs in color_map.items():
            if len(ocs) != 1:
                return None
            simple_map[ic] = list(ocs)[0]

        if simple_map:
            return {
                "type": "color_mapping",
                "mapping": simple_map,
                "confidence": 0.8,
            }

        return None


# ======================================================================
# DescendOperator -- placeholder for deeper KG exploration
# ======================================================================

class DescendOperator(Operator):
    """
    Placeholder: moves focus to a deeper KG level when current-level
    analysis is insufficient. Not yet needed for the basic pipeline.
    """

    def __init__(self):
        super().__init__("descend")

    def precondition(self, wm) -> bool:
        raise NotImplementedError("DescendOperator.precondition() not implemented.")

    def effect(self, wm):
        raise NotImplementedError("DescendOperator.effect() not implemented.")


# ======================================================================
# PredictOperator -- apply rule to test input
# ======================================================================

class PredictOperator(Operator):
    """
    Reads the best rule from active-rules and applies it to each test
    pair's input grid to produce a predicted output grid.
    """

    def __init__(self):
        super().__init__("predict")

    def precondition(self, wm) -> bool:
        raise NotImplementedError("PredictOperator.precondition() not implemented.")

    def effect(self, wm):
        task = wm.task
        active_rules = wm.s1.get("active-rules")
        if not task or not active_rules:
            return

        rule = active_rules[0]
        predictions = dict(wm.s1.get("predictions") or {})

        # R0 COMM-copy path: a constant-output rule predicts the common example
        # output (surfaced by ExtractPatternOperator), reconstructed from the two
        # frozen DSL primitives rather than read from a stored literal. This keeps
        # the prediction value-agnostic: the same rule, run on a different
        # constant-output task, yields *that* task's common output.
        common_grid = None
        if rule.get("type") == "constant_output":
            invariant = (wm.s1.get("patterns") or {}).get("output_invariant") or {}
            common_grid = invariant.get("common_output")

        # R1 object_motion: the target expression was fitted from this task's own
        # example comparison (ExtractPattern) — read it here so the destination is
        # re-derived per task, never stored as a literal on the rule. This is what
        # keeps a single value-agnostic rule covering the whole move family, the
        # same way constant_output re-derives its common output per task.
        motion_target = None
        motion_out_shape = None
        motion_selector = None
        if rule.get("type") == "object_motion":
            motion = (wm.s1.get("patterns") or {}).get("object_motion") or {}
            motion_target = motion.get("target")
            motion_out_shape = motion.get("out_shape")
            motion_selector = motion.get("selector")
            motion_scene = motion.get("scene")

        for i, test_pair in enumerate(task.test_pairs):
            key = f"test_{i}"
            if key in predictions:
                continue
            g0 = test_pair.input_grid
            if g0 is None:
                continue
            if rule.get("type") == "constant_output":
                predicted = (
                    self._render_common_output(common_grid)
                    if common_grid is not None
                    else None
                )
            elif rule.get("type") == "object_motion":
                predicted = self._render_object_motion(
                    g0, motion_target, motion_out_shape, motion_selector,
                    motion_scene,
                )
            else:
                predicted = self._apply_rule(rule, g0)
            if predicted is not None:
                predictions[key] = predicted

        wm.s1["predictions"] = predictions

    # ---- COMM-copy rendering via the two frozen DSL primitives -----------

    @staticmethod
    def _render_common_output(common_grid):
        """Reconstruct `common_grid` from make_grid + coloring (CLAUDE.md §6.2):
        a make_grid canvas filled with the background (most-frequent) colour,
        then one coloring call per non-background cell. No literal grid is stored
        on the rule, so the constant-output rule stays value-agnostic (R0)."""
        from procedural_memory.DSL.apply import apply_DSL

        h = len(common_grid)
        w = len(common_grid[0]) if h else 0
        if h == 0 or w == 0:
            return [row[:] for row in common_grid]

        counts = {}
        for row in common_grid:
            for v in row:
                counts[v] = counts.get(v, 0) + 1
        background = max(counts, key=counts.get)

        out = apply_DSL("make_grid", height=h, width=w, color=background)
        for r in range(h):
            for c in range(w):
                if common_grid[r][c] != background:
                    out = apply_DSL(
                        "coloring", out,
                        selection=(r, c), color=common_grid[r][c],
                    )
        return out

    # ---- rule application dispatchers ------------------------------------

    def _apply_rule(self, rule, input_grid):
        rule_type = rule.get("type")
        # object_motion is intentionally absent here: its destination is fitted
        # from the task's *example comparison*, which the fast path's
        # input-grid-only interface cannot supply. So the fast path declines (this
        # returns None) and object_motion is always solved on the slow path, where
        # save_rule merges every move task into one value-agnostic rule (covers>1)
        # — exactly as constant_output behaves. (R5 fast-path reuse of these
        # comparison-fitted rules is a separate, later gap.)
        if rule_type == "recolor_sequential":
            return self._apply_recolor_sequential(rule, input_grid)
        if rule_type == "color_mapping":
            return self._apply_color_mapping(rule, input_grid)
        if rule_type == "identity":
            return [row[:] for row in input_grid.raw]
        return None

    # ---- object-move rendering via the two frozen DSL primitives ----------

    @staticmethod
    def _render_object_motion(input_grid, target_desc, out_shape_desc=None,
                              selector_desc=None, scene_desc=None):
        """Place the object named by `selector_desc` (the selector expression
        fitted from this task's example comparison — unique / largest / smallest)
        at the destination named by `target_desc` (corner / constant / translation),
        on an output canvas whose shape is named by `out_shape_desc` (same /
        input+delta / constant — defaults to the input shape when absent). The fitted
        `scene_desc` fixes the fate of the *unselected* objects: ``"drop"`` (the
        default / legacy behaviour — the canvas holds only the moved object) or
        ``"preserve"`` (every other object is repainted at its original place, the
        §2.1 multi-object-output concept). Built only from make_grid + coloring
        (CLAUDE.md §6.2): a fresh background canvas at the output shape, the
        preserved objects (if any) repainted in place, then each selected-object
        cell repainted translated so its bbox top-left lands at the resolved
        destination. No literal coordinate, grid size, or object index lives on the
        rule — all are expressions resolved per input from G0 alone (P5) — so one
        rule serves every grid size, move variant, resize, object count, and the
        drop/preserve scene. Declines (returns None) if the selector picks no object
        or any painted cell would fall off the output grid."""
        from procedural_memory.DSL.apply import apply_DSL
        from agent.dsl_expr import (
            objects_of, select_object, background_of, target_position,
            output_shape,
        )

        if target_desc is None:
            return None

        raw = input_grid.raw
        in_h = len(raw)
        in_w = len(raw[0]) if in_h else 0
        bg = background_of(raw)

        objs = objects_of(raw, bg)
        # Default to the sole object when no selector was fitted (in-place callers),
        # otherwise resolve the fitted selector — which names the object from G0
        # alone, so the multi-object case stays value-agnostic.
        obj = (
            select_object(objs, selector_desc) if selector_desc is not None
            else (objs[0] if len(objs) == 1 else None)
        )
        if obj is None or in_h == 0 or in_w == 0:
            return None

        # Output grid shape: a fitted expression over the input shape, defaulting
        # to the input shape itself when no descriptor is supplied (in-place move).
        # The selected object feeds the `object_extent` reading and the input
        # object count feeds the `object_count` reading; both are computed from G0
        # alone (P5), keeping the shape value-agnostic.
        out_dims = (
            output_shape(out_shape_desc, (in_h, in_w), obj, len(objs))
            if out_shape_desc is not None
            else (in_h, in_w)
        )
        if out_dims is None:
            return None
        out_h, out_w = out_dims
        if out_h <= 0 or out_w <= 0:
            return None

        dst = target_position(target_desc, (out_h, out_w), obj)
        if dst is None:
            return None

        r0, c0, _r1, _c1 = obj["bbox"]
        dr, dc = dst[0] - r0, dst[1] - c0

        out = apply_DSL("make_grid", height=out_h, width=out_w, color=bg)

        # preserve scene: repaint every *unselected* object at its original place
        # (read from G0, P5) before the moved object lands on top.
        if scene_desc == "preserve":
            for other in objs:
                if other is obj:
                    continue
                for (r, c), color in other["pixels"].items():
                    if not (0 <= r < out_h and 0 <= c < out_w):
                        return None  # preserved object falls off the output → decline
                    out = apply_DSL("coloring", out, selection=(r, c), color=color)

        for (r, c), color in obj["pixels"].items():
            nr, nc = r + dr, c + dc
            if not (0 <= nr < out_h and 0 <= nc < out_w):
                return None  # destination pushes the object off-grid → decline
            out = apply_DSL("coloring", out, selection=(nr, nc), color=color)
        return out

    def _apply_recolor_sequential(self, rule, input_grid):
        raw = input_grid.raw
        height = len(raw)
        width = len(raw[0]) if raw else 0
        sort_key = rule["sort_key"]
        start_color = rule["start_color"]
        source_colors = set(rule.get("source_colors", []))

        # Find target cells
        target_cells = []
        for r in range(height):
            for c in range(width):
                if raw[r][c] in source_colors:
                    target_cells.append((r, c))

        if not target_cells:
            return [row[:] for row in raw]

        # Group into connected components
        groups = self._group_positions(target_cells)

        # Sort groups by the rule's sort key
        def _sort_val(group):
            if sort_key == "top_row":
                return min(r for r, c in group)
            if sort_key == "top_col":
                return min(c for r, c in group)
            return 0

        sorted_groups = sorted(groups, key=_sort_val)

        # Build output grid
        output = [row[:] for row in raw]
        for idx, group in enumerate(sorted_groups):
            new_color = start_color + idx
            for r, c in group:
                output[r][c] = new_color

        return output

    def _apply_color_mapping(self, rule, input_grid):
        raw = input_grid.raw
        mapping = rule.get("mapping", {})

        output = []
        for row in raw:
            output.append([mapping.get(cell, cell) for cell in row])
        return output

    # ---- helpers ---------------------------------------------------------

    @staticmethod
    def _group_positions(positions):
        """Group (row, col) positions into 4-connected components."""
        pos_set = set(positions)
        visited = set()
        groups = []

        for pos in positions:
            if pos in visited:
                continue
            group = []
            queue = [pos]
            while queue:
                p = queue.pop(0)
                if p in visited or p not in pos_set:
                    continue
                visited.add(p)
                group.append(p)
                r, c = p
                for dr, dc in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                    nb = (r + dr, c + dc)
                    if nb in pos_set and nb not in visited:
                        queue.append(nb)
            groups.append(group)

        return groups


# ======================================================================
# SubmitOperator -- finalize and satisfy goal
# ======================================================================

class SubmitOperator(Operator):
    """
    Writes predicted grids to S1 output-link in the format expected by
    run_task.py, and marks the goal as satisfied.
    """

    def __init__(self):
        super().__init__("submit")

    def precondition(self, wm) -> bool:
        raise NotImplementedError("SubmitOperator.precondition() not implemented.")

    def effect(self, wm):
        predictions = wm.s1.get("predictions")
        if not predictions:
            return

        task = wm.task
        if not task:
            return

        predicted_grids = []
        for i in range(len(task.test_pairs)):
            grid = predictions.get(f"test_{i}")
            if grid is not None:
                predicted_grids.append(grid)

        if not predicted_grids:
            return

        # Write to output-link (format expected by run_task.py)
        wm.s1["S1"] = {"output-link": "O_out"}
        wm.s1["O_out"] = {"predicted-grid": predicted_grids}

        # Mark goal as satisfied
        wm.s1["goal"] = {"subgoals": {
            f"test_{i}": {"status": "solved"}
            for i in range(len(predicted_grids))
        }}


class VerifyOperator(SubmitOperator):
    """Alias for the verify operation (same mechanism as submit)."""

    def __init__(self):
        super().__init__()
        self.name = "verify"
