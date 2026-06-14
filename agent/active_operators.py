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

        # Object-level *recolour* signal (BACKLOG_LOOP.md R1, §2.5-2b). For each
        # pair, is exactly one object recoloured in place (cells unchanged, colour
        # changed, others untouched, grid size preserved)? Then fit two
        # value-agnostic selector expressions across the pairs: which object is
        # recoloured (`fit_selector`) and whose colour it takes
        # (`fit_color_source`). This is the evidence the `object_recolor` matcher
        # keys on — the first non-positional transformation family, recognised the
        # intended way (one rule with fitted argument expressions) rather than via
        # the legacy value-keyed `_try_color_mapping`.
        patterns["object_recolor"] = self._object_recolor(task)

        # Raw train pairs for the general Slow-path synthesizer (modules F/G,
        # BACKLOG_LOOP.md R5/R6). The synthesizer SEARCHES a bounded space of
        # make_grid+coloring programs reproducing every pair, rather than
        # recognising one hand-picked shape — so it needs the input/output grids
        # themselves, not the per-shape signals above. Surfaced symbolically here
        # (raw grids, P7) so GeneralizeOperator can hand them to
        # `program.synthesis.synthesize_task` as the no-family-fired fallback.
        patterns["synthesis_pairs"] = [
            {"input": pair.input_grid.raw, "output": pair.output_grid.raw}
            for pair in task.example_pairs
            if pair.input_grid is not None and pair.output_grid is not None
        ]

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
            fit_target, fit_output_shape, fit_selector, fit_color_source,
        )

        pairs = []
        motions = []     # geometry feeding fit_target, only for clean pairs
        shapes = []      # in/out grid dims feeding fit_output_shape (same pairs)
        selections = []  # (objects, selected idx) feeding fit_selector
        scenes = []      # per-pair scene ("drop"/"preserve"), clean pairs only
        recolors = []    # per recorded pair: {"objects", "color"} if recoloured
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
            # the moved object) or preserved (they survive unchanged). `new_color`
            # is non-None when the move *also recolours* the object (translate ∘
            # recolour) — a colour-invariant shape match identifies it. An absent /
            # ambiguous match leaves the selection undefined and the pair declines.
            sel_idx, obj_out, scene, new_color = (
                ExtractPatternOperator._identify_move(objs_in, objs_out)
            )
            obj_in = objs_in[sel_idx] if sel_idx is not None else None

            color_preserved = (
                obj_in is not None and obj_out is not None
                and color_of(obj_in) is not None
                and color_of(obj_in) == color_of(obj_out)
            )
            # A recoloured move keeps the object's shape/size but changes its
            # colour; `new_color` carries the destination colour (None when the
            # colour is preserved). Either is an acceptable move — the colour, when
            # it changes, becomes a fitted argument expression (below).
            recolored = new_color is not None
            size_preserved = (
                obj_in is not None and obj_out is not None
                and obj_in["size"] == obj_out["size"]
            )
            grid_size_preserved = g0.height == g1.height and g0.width == g1.width

            entry = {
                "scene": scene,
                "selected_ok": obj_in is not None,
                "color_preserved": color_preserved,
                "recolored": recolored,
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
                and size_preserved and (color_preserved or recolored)
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
                    # positions of the *unselected* input objects — the anchor
                    # candidates for the relational `to_anchor` target (§2.5-1),
                    # read from G0 alone (P5), never a literal coordinate.
                    "others": [
                        position_of(o)
                        for j, o in enumerate(objs_in) if j != sel_idx
                    ],
                    # the full *unselected* object dicts — fed to fit_target's
                    # anchor *selector* so `to_anchor` names *which* of several
                    # other objects is the anchor (§2.5-2b), not just the lone one.
                    "other_objs": [
                        o for j, o in enumerate(objs_in) if j != sel_idx
                    ],
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
                # Record the recoloured object's *new* colour (or None when the
                # colour is preserved) parallel to the move geometry, so a colour
                # expression can be fitted across the recorded pairs.
                recolors.append(
                    {"objects": objs_in, "color": new_color}
                    if recolored else None
                )

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

        # Fit the *new colour* expression only when the move recolours the object
        # on EVERY recorded pair (a mix of recoloured and colour-preserving pairs is
        # inconsistent → decline, leaving `color=None` and the family unaffected).
        # The colour is the same value-agnostic argument expression the in-place
        # recolour family fits (`fit_color_source`: another object's colour, or a
        # fitted constant), so the destination *and* the new colour are both fitted
        # from the example comparison and one rule covers move ∘ recolour.
        recolored_flags = [r is not None for r in recolors]
        color = (
            fit_color_source([r for r in recolors if r is not None])
            if (clean and recolored_flags and all(recolored_flags))
            else None
        )

        return {
            "evidence_count": len(pairs),
            "pairs": pairs,
            "target": target,
            "out_shape": out_shape,
            "selector": selector,
            "scene": scene,
            "color": color,
            # Multi-object "map-all" reading (gravity / "all objects fall"): every
            # object moves by ONE per-object displacement target. Fitted
            # independently of the single-object analysis above and only when the
            # input holds ≥2 objects, so it never competes with the move family the
            # select-one path already covers (the matcher prefers the single-object
            # fit; map_all is consulted only when that declines). This is the R1
            # "next gap" — generalising select-one to map-all (§2.5-2b).
            "map_all": ExtractPatternOperator._fit_map_all(task),
        }

    @staticmethod
    def _fit_map_all(task):
        """Fit a multi-object *map-all* uniform motion across the example pairs.

        Every input object maps to an output object (a unique bijection by the
        colour-set + size + shape a move preserves), and ONE per-object
        displacement target — a uniform ``offset`` or a per-object ``to_edge`` fall
        — explains *every* object on *every* pair. This is the canonical gravity /
        "all objects fall" transform, the select-one→map-all generalisation of the
        single-object move (§2.5-2b, BACKLOG_LOOP R1 "next gap"). Reads only G0/G1
        object properties — no literal coordinate or index — so the signal stays
        value-agnostic and computable from G0 alone at test time (P5).

        Returns ``{"target": <descriptor>, "evidence_count": n, "clean": True}`` or
        ``None`` (decline). Requires ≥2 objects on every pair so it is *never*
        consulted for the single-object move family the select-one path covers, and
        declines on any ambiguous bijection (two objects sharing colour+size+shape)
        rather than guessing which fell where — column-disambiguated identical-object
        gravity is a later refinement.
        """
        from agent.dsl_expr import (
            objects_of, position_of, obj_origin_extent, color_of,
            fit_uniform_target,
        )
        from agent.dsl_expr.selection import _shape_signature

        all_motions = []
        npairs = 0
        for pair in task.example_pairs:
            g0, g1 = pair.input_grid, pair.output_grid
            if g0 is None or g1 is None:
                continue
            if g0.height != g1.height or g0.width != g1.width:
                return None  # map_all is size-preserving
            objs_in = objects_of(g0.raw)
            objs_out = objects_of(g1.raw)
            if len(objs_in) < 2 or len(objs_in) != len(objs_out):
                return None

            used = set()
            moved_any = False
            for oi in objs_in:
                key = (tuple(oi["color_set"]), oi["size"], _shape_signature(oi))
                cands = [
                    j for j, oj in enumerate(objs_out)
                    if j not in used
                    and (tuple(oj["color_set"]), oj["size"], _shape_signature(oj))
                    == key
                ]
                if len(cands) != 1:
                    return None  # ambiguous / unmatched object → decline
                j = cands[0]
                used.add(j)
                oj = objs_out[j]
                if color_of(oi) is None or color_of(oi) != color_of(oj):
                    return None  # colour not preserved → not a plain move
                (oh, ow) = obj_origin_extent(oi)[1]
                src, dst = position_of(oi), position_of(oj)
                if src != dst:
                    moved_any = True
                all_motions.append({
                    "src": src, "dst": dst,
                    "H": g1.height, "W": g1.width, "oh": oh, "ow": ow,
                })
            if not moved_any:
                return None  # a static scene is not a fall
            npairs += 1

        if npairs == 0 or not all_motions:
            return None
        target = fit_uniform_target(all_motions)
        if target is None:
            return None
        return {"target": target, "evidence_count": npairs, "clean": True}

    @staticmethod
    def _identify_move(objs_in, objs_out):
        """Identify which input object the move acted on and what becomes of the
        *unselected* objects, reading both from the input→output comparison (P3/P4)
        rather than a literal. Returns ``(selected_index, output_object, scene,
        new_color)`` where ``scene`` is:

          * ``"drop"``     — the output holds only the moved object; every other
            input object vanishes (easy000c–i and the size/position/colour-selected
            multi-object tasks).
          * ``"preserve"`` — the output keeps every *other* input object unchanged
            (same pixels at the same place) and exactly one object moved (the
            §2.1 multi-object-*output* concept).

        ``new_color`` is ``None`` for a colour-preserving move (the object keeps its
        colour) and the object's *new* single colour for a move that *also recolours*
        the object (translate ∘ recolour — a two-transformation composition no single
        family handles: object_motion alone gates on colour preserved, object_recolor
        alone gates on cells unchanged). The recoloured object is matched back to its
        input by a colour-invariant *shape* signature + size — tried only after the
        colour-set + size match fails, so every existing colour-preserving move is
        identified exactly as before (zero regression).

        Returns ``(None, None, None, None)`` when the pair is not a clean
        single-object move, so the pair declines rather than guessing."""
        from agent.dsl_expr import color_of
        from agent.dsl_expr.selection import _shape_signature

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
                return cands[0], obj_out, "drop", None
            # recolour fallback: the colour changed, so match the moved object back
            # to its input by shape (translation- and colour-invariant signature) +
            # size instead. A *unique* shape+size match whose single colour differs
            # is a move that also recolours; its new colour is read from the output
            # object (P3/P4), never a literal.
            sig = _shape_signature(obj_out)
            new_color = color_of(obj_out)
            shape_cands = [
                i for i, o in enumerate(objs_in)
                if o["size"] == obj_out["size"] and _shape_signature(o) == sig
            ]
            if len(shape_cands) == 1 and new_color is not None:
                return shape_cands[0], obj_out, "drop", new_color
            return None, None, None, None

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
                    return moved_in[0], oj, "preserve", None

        return None, None, None, None

    # ---- object-level recolour analysis (R1) ----------------------------

    @staticmethod
    def _object_recolor(task):
        """Per-pair in-place *recolour* analysis using the seed selection
        vocabulary (agent/dsl_expr). Reads only G0/G1 properties — no literal
        colour or object index is baked in, so the signal is value-agnostic. Fits
        two orthogonal selector *expressions* across the pairs (§2.5-2b): a
        *selector* naming which object is recoloured, and a *source* naming the
        object whose colour it takes (the new colour is `color_of` that object,
        never a stored literal)."""
        from agent.dsl_expr import objects_of, fit_selector, fit_color_source

        pairs = []
        selections = []   # (objects, recoloured idx) feeding fit_selector
        sources = []      # (objects, new colour) feeding fit_color_source
        for pair in task.example_pairs:
            g0, g1 = pair.input_grid, pair.output_grid
            if g0 is None or g1 is None:
                continue

            grid_size_preserved = (
                g0.height == g1.height and g0.width == g1.width
            )
            objs_in = objects_of(g0.raw)
            sel_idx, new_color = (None, None)
            if grid_size_preserved:
                sel_idx, new_color = ExtractPatternOperator._identify_recolor(
                    objs_in, objects_of(g1.raw)
                )

            recolor_ok = sel_idx is not None and new_color is not None
            if recolor_ok:
                selections.append({"objects": objs_in, "selected": sel_idx})
                sources.append({"objects": objs_in, "color": new_color})

            pairs.append({
                "recolor_ok": recolor_ok,
                "grid_size_preserved": grid_size_preserved,
            })

        # Fit both selector expressions only if every pair is a clean recolour
        # (so a task with any dirty pair declines rather than over-generalising).
        clean = bool(selections) and len(selections) == len(pairs)
        selector = fit_selector(selections) if clean else None
        source = fit_color_source(sources) if clean else None

        return {
            "evidence_count": len(pairs),
            "pairs": pairs,
            "selector": selector,
            "source": source,
        }

    @staticmethod
    def _identify_recolor(objs_in, objs_out):
        """Identify the single object recoloured *in place*: same cells, a
        different single colour, with every *other* object byte-identical in and
        out. Returns ``(selected_index, new_color)`` or ``(None, None)`` when the
        pair is not a clean single-object in-place recolour (so the pair declines
        rather than guessing). Reads the change from the input->output comparison
        (P3/P4), never a literal."""
        from agent.dsl_expr import color_of

        if len(objs_in) != len(objs_out) or len(objs_in) == 0:
            return None, None

        # Map each output object by its (frozen) cell-set so an input object can
        # be matched to the output object occupying the SAME cells. A moved or
        # merged object has no same-cell twin and makes the pair decline.
        out_by_cells = {}
        for oj in objs_out:
            out_by_cells.setdefault(oj["cells"], []).append(oj)

        recoloured = []
        for i, oi in enumerate(objs_in):
            matches = out_by_cells.get(oi["cells"])
            if not matches or len(matches) != 1:
                return None, None  # cells must align one-to-one (no move/merge)
            oj = matches[0]
            if oj["pixels"] == oi["pixels"]:
                continue  # unchanged object — left untouched
            new_color = color_of(oj)
            if new_color is None:
                return None, None  # recoloured to multi-colour — not a recolour
            recoloured.append((i, new_color))

        if len(recoloured) == 1:
            return recoloured[0]
        return None, None

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
            motion = patterns.get("object_motion") or {}
            # The multi-object "map-all" move (gravity) records its own fitted target
            # when the single-object analysis declined; the rule dict is otherwise
            # identical (type object_motion / dsl place_object / a target arg), so a
            # map-all task merges into the same value-agnostic move rule and lifts its
            # coverage rather than minting a separate detector (§2.5-3).
            map_all = motion.get("map_all")
            if motion.get("selector") is None and isinstance(map_all, dict):
                target_expr = map_all.get("target")
            else:
                target_expr = motion.get("target")
            color_expr = motion.get("color")
            rule = {
                "type": "object_motion",
                "condition": {
                    "type": "object_motion",
                    "params": {"min_evidence": 2},
                    "min_evidence": 2,
                },
                # The fitted *target expression* (corner / constant / translation
                # — `agent/dsl_expr.fit_target`) is the principal argument of
                # place_object. It is recorded here so two move tasks whose
                # targets diverge become anti-unifiable: `agent/memory.save_rule`
                # lifts the divergent target to a `?v` variable via
                # `anti_unification.unify()` (R3 / BACKLOG_LOOP §2.5-2), converging
                # the family to ONE rule with covers>1 + an anti_unification_trace
                # instead of one detector per target kind (P1·P2·P3 together,
                # §2.5-4). This does NOT change solving: PredictOperator re-derives
                # the concrete target from each task's own example comparison (it
                # reads `wm.s1["patterns"]`, never these args), so the recorded
                # expression is for generalization/coverage only.
                # The fitted new-colour expression (when the move also recolours the
                # object) rides alongside the target as a second argument, so two
                # move∘recolour tasks whose colour expressions diverge anti-unify the
                # same way the targets do (R3). Omitted entirely for a pure move, so
                # the existing colour-preserving rule dict is byte-for-byte unchanged
                # and still merges with every prior move task.
                "action": {
                    "dsl": "place_object",
                    "args": (
                        {**({"target": target_expr} if target_expr is not None else {}),
                         **({"color": color_expr} if color_expr is not None else {})}
                    ),
                },
                "confidence": 1.0,
            }

        # R1 (BACKLOG_LOOP.md §2.5-2b): object-level *recolour* with fitted
        # selector + colour-source expressions. When every example recolours one
        # selected object in place to a colour read from another object (both named
        # by value-agnostic selectors fitted by ExtractPattern), emit one
        # {condition, action} rule. The recoloured object's selector and the
        # colour-source selector are recorded as the action's arguments so two
        # recolour tasks whose (selector, source) diverge become anti-unifiable:
        # `agent/memory.save_rule` lifts the divergent positions to `?v` variables
        # via `anti_unification.unify()` (R3), converging the family to ONE rule
        # with covers>1 + an anti_unification_trace instead of one value-keyed
        # color_mapping per task (the legacy `_try_color_mapping` failure mode;
        # P1·P2·P3 together, §2.5-4). This does NOT change solving: PredictOperator
        # re-derives both selectors from each task's own example comparison (it
        # reads `wm.s1["patterns"]`, never these args), so the recorded expressions
        # are for generalization/coverage only. Checked before the legacy
        # color-strategies so a recolour task is solved the intended way.
        if rule is None and self._matches_object_recolor(patterns):
            rec = patterns.get("object_recolor") or {}
            args = {}
            if rec.get("selector") is not None:
                args["selector"] = rec.get("selector")
            if rec.get("source") is not None:
                args["source"] = rec.get("source")
            rule = {
                "type": "object_recolor",
                "condition": {
                    "type": "object_recolor",
                    "params": {"min_evidence": 2},
                    "min_evidence": 2,
                },
                "action": {"dsl": "recolor_object", "args": args},
                "confidence": 1.0,
            }

        # Color-transform tasks are handled the *intended* way by the
        # value-agnostic `object_recolor` family above (selector + colour-source
        # argument expressions, anti-unifiable into one covers>1 rule). The
        # legacy `_try_recolor_sequential` / `_try_color_mapping` detectors that
        # used to live here were retired (CLAUDE.md §5.1, INVARIANTS P6): they
        # baked literal in->out colour maps into per-task rules with no
        # `condition` key — the conditionless, never-lifted accretion that is
        # arbor.md's 진단 #4/#5 (the 168-rule failure mode). When no principled
        # family recognises the task, fall through to identity (no rule saved)
        # rather than mint an overfit special case.

        # General Slow-path synthesizer (BACKLOG_LOOP.md R5/R6, arbor-modules F/G).
        # When NO hand-picked family recognises the task, do not give up to
        # identity yet — SEARCH a bounded space of programs built only from the two
        # frozen primitives (make_grid / coloring) for one that reproduces every
        # example pair (`program.synthesis.synthesize_task`). This is the general
        # mechanism the families are special cases of: it solves transformations
        # outside any recognised shape (e.g. a multi-object grid resize with no
        # single mover) the §6.2 "discovered layer is data, not code" way — the
        # synthesized program is persisted as the rule's `action.args.program`, a
        # value-agnostic recipe, not a per-task literal. Recognition stays in the
        # registry: the synthesized program is gated through the
        # `synthesized_program` matcher (same discipline as the families above)
        # before it becomes a rule. A `None` from the search is an honest miss —
        # fall through to identity rather than fabricate a per-pair literal fit.
        if rule is None:
            program = self._synthesize_program(patterns)
            if program:
                rule = {
                    "type": "synthesized_program",
                    "condition": {
                        "type": "synthesized_program",
                        "params": {"program": program, "min_evidence": 1},
                        "min_evidence": 1,
                    },
                    # The searched program is the action argument that
                    # `anti_unification.unify()` lifts when two synthesizer tasks
                    # share a skeleton but differ in their programs (R3 via the
                    # synthesizer — the cross-family frontier the family matchers
                    # cannot reach). Carried as data, so apply_DSL's discovered
                    # layer (CLAUDE.md §6.2) runs it without any new primitive.
                    "action": {"dsl": "run_program", "args": {"program": program}},
                    "confidence": 1.0,
                }

        # Fallback: identity (copy input as output)
        if rule is None:
            rule = {"type": "identity", "confidence": 0.0}

        wm.s1["active-rules"] = [rule]

    # ---- general Slow-path synthesizer (modules F/G) ---------------------

    @staticmethod
    def _synthesize_program(patterns):
        """Search for a value-agnostic make_grid+coloring program reproducing every
        train pair (`program.synthesis.synthesize_task`), then confirm it through
        the registered `synthesized_program` matcher so recognition stays in the
        registry (mirrors `_matches_constant_output` et al.). Returns the program
        (a non-empty list of steps) or None — an empty program is identity, left to
        the identity fallback rather than minted as a learned rule."""
        pairs = patterns.get("synthesis_pairs") if isinstance(patterns, dict) else None
        if not pairs:
            return None
        from program.synthesis import synthesize_task
        from agent.conditions import match as match_condition

        program = synthesize_task(pairs)
        if not program:  # None (miss) or [] (identity) → not a learned rule
            return None
        try:
            if match_condition(
                "synthesized_program", patterns,
                {"program": program, "min_evidence": 1},
            ):
                return program
        except KeyError:
            return None
        return None

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
                "object_motion", patterns, {"min_evidence": 1}
            )
        except KeyError:
            return False

    @staticmethod
    def _matches_object_recolor(patterns):
        """True iff the registered `object_recolor` matcher fires. Thin wrapper so
        the matcher (agent/conditions) stays the single source of truth for the
        recognition (mirrors `_matches_object_motion`)."""
        from agent.conditions import match as match_condition
        try:
            return match_condition(
                "object_recolor", patterns, {"min_evidence": 1}
            )
        except KeyError:
            return False

    # Legacy color-transform strategies (`_try_recolor_sequential`,
    # `_check_sort_key`, `_try_color_mapping`) were removed here — they are
    # superseded by the value-agnostic `object_recolor` family and were the
    # source of conditionless per-task rules (CLAUDE.md §5.1, INVARIANTS P6).


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
        motion_color = None
        motion_map_all = None
        if rule.get("type") == "object_motion":
            motion = (wm.s1.get("patterns") or {}).get("object_motion") or {}
            motion_target = motion.get("target")
            motion_out_shape = motion.get("out_shape")
            motion_selector = motion.get("selector")
            motion_scene = motion.get("scene")
            motion_color = motion.get("color")
            # Multi-object map-all (gravity) is rendered only when the single-object
            # analysis declined (no fitted selector), so the select-one renderer still
            # serves the move family it already covers.
            if motion_selector is None:
                motion_map_all = motion.get("map_all")

        # R1 object_recolor: the selector + colour-source were fitted from this
        # task's own example comparison — read them here so the recolour is
        # re-derived per task, never stored as a literal on the rule (same
        # value-agnostic discipline as object_motion's target).
        recolor_selector = None
        recolor_source = None
        if rule.get("type") == "object_recolor":
            rec = (wm.s1.get("patterns") or {}).get("object_recolor") or {}
            recolor_selector = rec.get("selector")
            recolor_source = rec.get("source")

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
                if (
                    isinstance(motion_map_all, dict)
                    and motion_map_all.get("target") is not None
                ):
                    predicted = self._render_map_all_motion(
                        g0, motion_map_all.get("target")
                    )
                else:
                    predicted = self._render_object_motion(
                        g0, motion_target, motion_out_shape, motion_selector,
                        motion_scene, motion_color,
                    )
            elif rule.get("type") == "object_recolor":
                predicted = self._render_object_recolor(
                    g0, recolor_selector, recolor_source,
                )
            elif rule.get("type") == "synthesized_program":
                # General Slow-path synthesizer (modules F/G): run the searched
                # value-agnostic program on this test input. Every variable
                # originates in G0 (P5), so the program transfers unchanged from
                # the train pairs to the test input.
                predicted = self._render_synthesized_program(rule, g0)
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
        if rule_type == "identity":
            return [row[:] for row in input_grid.raw]
        if rule_type == "synthesized_program":
            # Fast-path reuse of a stored synthesizer rule (R5): the program is
            # value-agnostic, so it applies straight from a single input grid (no
            # example comparison needed), unlike the comparison-fitted families.
            return PredictOperator._render_synthesized_program(rule, input_grid)
        return None

    @staticmethod
    def _render_synthesized_program(rule, input_grid):
        """Run the rule's searched make_grid+coloring program on `input_grid`.
        Reads the program from `action.args.program` (the canonical store) and
        declines (None) when an expression does not resolve against this input —
        renderers must decline, not raise (memory: runtime_resolvable_speculative_apply)."""
        program = (
            (rule.get("action") or {}).get("args", {}).get("program")
            if isinstance(rule.get("action"), dict) else None
        )
        if not program:
            return None
        from program.synthesis import run_program, _Unevaluable
        try:
            return run_program(program, input_grid.raw)
        except _Unevaluable:
            return None

    # ---- object-move rendering via the two frozen DSL primitives ----------

    @staticmethod
    def _render_object_motion(input_grid, target_desc, out_shape_desc=None,
                              selector_desc=None, scene_desc=None,
                              color_desc=None):
        """Place the object named by `selector_desc` (the selector expression
        fitted from this task's example comparison — unique / largest / smallest)
        at the destination named by `target_desc` (corner / constant / translation
        / on another object — the relational `to_anchor` target),
        on an output canvas whose shape is named by `out_shape_desc` (same /
        input+delta / constant — defaults to the input shape when absent). The fitted
        `scene_desc` fixes the fate of the *unselected* objects: ``"drop"`` (the
        default / legacy behaviour — the canvas holds only the moved object) or
        ``"preserve"`` (every other object is repainted at its original place, the
        §2.1 multi-object-output concept). The fitted `color_desc`, when present,
        names the moved object's *new* colour (another object's colour, or a fitted
        constant — `agent/dsl_expr.color_source`): the move then *also recolours* the
        object (translate ∘ recolour); absent it the object keeps its own colours.
        Built only from make_grid + coloring (CLAUDE.md §6.2): a fresh background
        canvas at the output shape, the preserved objects (if any) repainted in place,
        then each selected-object cell repainted translated so its bbox top-left lands
        at the resolved destination, in the resolved new colour when recolouring. No
        literal coordinate, grid size, colour, or object index lives on the rule —
        all are expressions resolved per input from G0 alone (P5) — so one rule serves
        every grid size, move variant, resize, object count, the drop/preserve scene,
        and the optional recolour. Declines (returns None) if the selector picks no
        object, the colour expression resolves to nothing, or any painted cell would
        fall off the output grid."""
        from procedural_memory.DSL.apply import apply_DSL
        from agent.dsl_expr import (
            objects_of, select_object, background_of, target_position,
            output_shape, color_source,
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

        # Pass the full object list so the relational `to_anchor` target can name
        # its anchor (another object) from G0 alone (P5); grid-relative and
        # constant targets ignore it.
        dst = target_position(target_desc, (out_h, out_w), obj, objs)
        if dst is None:
            return None

        # Resolve the move's new colour (when it also recolours) from G0 alone (P5)
        # — another object's colour or the fitted constant. Decline if it resolves
        # to nothing (e.g. a colour-source selector that picks no object here).
        new_color = None
        if color_desc is not None:
            new_color = color_source(color_desc, objs)
            if new_color is None:
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
            paint = new_color if new_color is not None else color
            out = apply_DSL("coloring", out, selection=(nr, nc), color=paint)
        return out

    @staticmethod
    def _render_map_all_motion(input_grid, target_desc):
        """Render a multi-object *map-all* move: place **every** object at the
        destination named by `target_desc` (the per-object displacement expression
        fitted from this task's example comparison — a uniform ``offset`` or a
        per-object ``to_edge`` fall), on a same-shape canvas. The select-one→map-all
        generalisation of `_render_object_motion` (§2.5-2b): instead of moving one
        fitted-selector object, the same fitted target is resolved *per object* and
        applied to all. Built only from make_grid + coloring (CLAUDE.md §6.2): a
        fresh background canvas, then each object's cells repainted translated so its
        bbox top-left lands at its resolved destination. No literal coordinate, size,
        or count lives on the rule — the destination is an expression resolved per
        object from G0 alone (P5) — so one value-agnostic rule serves the whole
        gravity family. Declines (returns None) if the target resolves to nothing for
        any object or any painted cell would fall off the grid."""
        from procedural_memory.DSL.apply import apply_DSL
        from agent.dsl_expr import (
            objects_of, background_of, target_position,
        )

        if target_desc is None:
            return None
        raw = input_grid.raw
        h = len(raw)
        w = len(raw[0]) if h else 0
        if h == 0 or w == 0:
            return None

        bg = background_of(raw)
        objs = objects_of(raw, bg)
        if len(objs) < 2:
            return None

        out = apply_DSL("make_grid", height=h, width=w, color=bg)
        for obj in objs:
            dst = target_position(target_desc, (h, w), obj, objs)
            if dst is None:
                return None
            r0, c0, _r1, _c1 = obj["bbox"]
            dr, dc = dst[0] - r0, dst[1] - c0
            for (r, c), color in obj["pixels"].items():
                nr, nc = r + dr, c + dc
                if not (0 <= nr < h and 0 <= nc < w):
                    return None  # destination pushes the object off-grid → decline
                out = apply_DSL("coloring", out, selection=(nr, nc), color=color)
        return out

    # ---- object-recolour rendering via the two frozen DSL primitives ------

    @staticmethod
    def _render_object_recolor(input_grid, selector_desc, source_desc):
        """Recolour the object named by `selector_desc` to the colour of the
        object named by `source_desc` (both selector expressions fitted from this
        task's example comparison), in place on a same-shape canvas. Built only
        from make_grid + coloring (CLAUDE.md §6.2): a fresh background canvas, every
        object repainted at its original cells, and the selected object's cells
        repainted in the sourced colour instead of its own. No literal colour or
        object index lives on the rule — both are expressions resolved per input
        from G0 alone (P5) — so one rule serves every recolour in the family.
        Declines (returns None) if either selector picks no object or the source
        object has no single colour."""
        from procedural_memory.DSL.apply import apply_DSL
        from agent.dsl_expr import (
            objects_of, select_object, background_of, color_source,
        )

        if selector_desc is None or source_desc is None:
            return None

        raw = input_grid.raw
        h = len(raw)
        w = len(raw[0]) if h else 0
        if h == 0 or w == 0:
            return None

        bg = background_of(raw)
        objs = objects_of(raw, bg)
        target = select_object(objs, selector_desc)
        new_color = color_source(source_desc, objs)
        if target is None or new_color is None:
            return None

        out = apply_DSL("make_grid", height=h, width=w, color=bg)
        for obj in objs:
            for (r, c), color in obj["pixels"].items():
                paint = new_color if obj is target else color
                out = apply_DSL("coloring", out, selection=(r, c), color=paint)
        return out

    # `_apply_recolor_sequential`, `_apply_color_mapping`, and their
    # `_group_positions` helper were removed alongside the legacy color-transform
    # detectors above (CLAUDE.md §5.1, INVARIANTS P6) — no rule of those types is
    # produced any more, so the appliers were dead code.


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
