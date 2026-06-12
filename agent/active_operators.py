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
from agent.conditions import match as match_condition
from agent.dsl_expr.render import render_grid_via_primitives, render_object_at
from agent.dsl_expr.selection import (
    analyze_object_move,
    analyze_object_select_move,
    background_of,
    corner_anchor,
    extent_of,
    objects_of,
    unique_object,
    SELECTOR_VOCAB,
)

#: condition.type the GeneralizeOperator emits for the constant-output family
CONSTANT_OUTPUT_DSL = "copy_common_output"

#: action.dsl the GeneralizeOperator emits for the constant-target object move
#: family (R1) — a make_grid ∘ coloring composition rendered at predict time.
PLACE_OBJECT_DSL = "place_object_constant"

#: action.dsl for the constant-*offset* object move family (R1, easy000e/f) —
#: same make_grid ∘ coloring composition, but the per-test target is the test
#: object's own anchor plus the cross-pair constant displacement.
PLACE_OBJECT_RELATIVE_DSL = "place_object_relative"

#: action.dsl for the constant-*corner* object move family (R1, easy000g) —
#: same make_grid ∘ coloring composition, but the per-test target is a
#: grid-relative corner anchor recomputed against each test grid's own size.
PLACE_OBJECT_CORNER_DSL = "place_object_corner"

#: action.dsl for the grid-*resize* object move family (R1, easy000i) — same
#: make_grid ∘ coloring composition, but make_grid sizes a *constant resized*
#: canvas (the cross-pair COMM on the output dimensions) instead of copying the
#: input size, and the object is placed at the constant target on it.
PLACE_OBJECT_RESIZE_DSL = "place_object_resize"

#: action.dsl for the multi-object *selection* move family (R1 / §2.5-2b) — same
#: make_grid ∘ coloring composition, but the object placed is the one a learned
#: property selector (max_size/min_size/unique_color) picks out of several, the
#: non-selected distractors simply not drawn. The selector is the §2.5-2b lift.
PLACE_OBJECT_SELECT_DSL = "place_object_select"


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

        # Object-level analysis (R1, BACKLOG_LOOP §3): descend to OBJECT level
        # when the whole-grid signal is insufficient. Surfaces, per pair, whether
        # a single object simply moved (color/shape kept) and whether all example
        # outputs share one anchor — the cross-pair COMM the `object_constant_
        # target` matcher keys on. Computed via the §2.5 selection vocabulary
        # (agent/dsl_expr/selection), not hand-coded here.
        patterns["object_move"] = analyze_object_move(task.example_pairs)

        # Multi-object *selection* (R1 / §2.5-2b): the converse case where several
        # objects are present and the rule keeps the one a learned property
        # selector picks. Inert (multi_object_all=False) on the single-object
        # family, so it never perturbs the readings above. Computed via the §2.5
        # selection vocabulary, not hand-coded here.
        patterns["object_select_move"] = analyze_object_select_move(task.example_pairs)

        wm.s1["patterns"] = patterns

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

        # Strategy 0 (R0, BACKLOG_LOOP §3): the constant-output family. If the
        # `constant_output` matcher fires (all example outputs identical — the
        # Inter-Grid G1 COMM signal), emit a canonical {condition, action} rule
        # value-agnostically. The action is the discovered composition
        # `copy_common_output`, which PredictOperator renders from the two
        # frozen primitives. This is recognition-driven, not a hand-coded
        # detector: the decision is delegated to the registered matcher.
        rule = self._constant_output_rule(patterns)

        # Strategy 0b (R1, BACKLOG_LOOP §3): the constant-target object-move
        # family. If the `object_constant_target` matcher fires (single object
        # moved to one shared anchor across examples), emit a canonical
        # {condition, action} rule whose action recomputes the target at predict
        # time — value-agnostic in color and source position, so one rule covers
        # the whole family. Recognition is delegated to the registered matcher,
        # not a hand-coded detector.
        if rule is None:
            rule = self._object_constant_target_rule(patterns)

        # Strategy 0c (R1, easy000e/f): the constant-*offset* object-move family.
        # If the `object_constant_offset` matcher fires (single object moved by
        # one shared displacement across examples), emit a canonical {condition,
        # action} rule whose action recomputes the offset at predict time and
        # adds it to each test object's own anchor — value-agnostic in color and
        # source position. Recognition is delegated to the registered matcher.
        if rule is None:
            rule = self._object_constant_offset_rule(patterns)

        # Strategy 0d (R1, easy000g): the constant-*corner* object-move family.
        # If the `object_corner_target` matcher fires (single object moved flush
        # into one shared grid corner across examples, but with neither a constant
        # absolute target nor a constant offset), emit a canonical {condition,
        # action} rule whose action recomputes the corner anchor against each test
        # grid's own size at predict time — value-agnostic in color, source
        # position, and grid size. Recognition is delegated to the registered
        # matcher, not a hand-coded detector.
        if rule is None:
            rule = self._object_corner_target_rule(patterns)

        # Strategy 0e (R1, easy000i): the grid-*resize* object-move family. If
        # the `object_resize_target` matcher fires (single object moved onto a
        # constant-sized output canvas that differs from the input size, at one
        # shared target), emit a canonical {condition, action} rule whose action
        # sizes the canvas from the cross-pair output-dimension COMM and places
        # the test object at the recomputed target — value-agnostic in color,
        # source position, and input size. Recognition is delegated to the
        # registered matcher, not a hand-coded detector.
        if rule is None:
            rule = self._object_resize_target_rule(patterns)

        # Strategy 0f (R1 / §2.5-2b): the multi-object *selection* move family. If
        # the `object_select_target` matcher fires (several objects present, one
        # kept by a learned property selector and placed at one shared target),
        # emit a canonical {condition, action} rule carrying the selector. The
        # selector and target are recomputed at predict time — value-agnostic in
        # colour, source position and the distractors — so one rule covers the
        # family. Recognition is delegated to the registered matcher, not a
        # hand-coded detector.
        if rule is None:
            rule = self._object_select_target_rule(patterns)

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

    # ---- strategy: constant output (R0 COMM-copy) -----------------------

    def _constant_output_rule(self, patterns):
        """Emit the canonical constant-output rule when the matcher fires.

        Not a `_try_*`-family detector: the recognition is delegated to the
        registered `constant_output` matcher (agent/conditions/), and the result
        is a schema-canonical `{condition, action}` rule, not a literal grid.
        The common output is recomputed at predict time, so the rule stays
        value-agnostic and one rule covers the whole family.
        """
        invariant = patterns.get("output_invariant") or {}
        evidence = invariant.get("evidence_count", 0)
        params = {"min_evidence": 2}
        if not match_condition("constant_output", patterns, params):
            return None
        return {
            "condition": {
                "type": "constant_output",
                "params": dict(params),
                "min_evidence": max(2, evidence),
            },
            "action": {
                "dsl": CONSTANT_OUTPUT_DSL,
                "args": {},
            },
            "concept": "copy_common_output",
            "category": "constant_output",
            "confidence": 1.0,
        }

    # ---- strategy: constant-target object move (R1) ---------------------

    def _object_constant_target_rule(self, patterns):
        """Emit the canonical constant-target move rule when the matcher fires.

        Not a `_try_*`-family detector: recognition is delegated to the
        registered `object_constant_target` matcher (agent/conditions/), and the
        result is a schema-canonical {condition, action} rule. The constant
        target is recomputed at predict time from the example outputs (so the
        rule stays value-agnostic and one rule covers easy000c/d/h), exactly
        mirroring the COMM-copy design one level up.
        """
        params = {"min_evidence": 2}
        if not match_condition("object_constant_target", patterns, params):
            return None
        move = patterns.get("object_move") or {}
        evidence = len(move.get("per_pair") or [])
        return {
            "condition": {
                "type": "object_constant_target",
                "params": dict(params),
                "min_evidence": max(2, evidence),
            },
            "action": {
                "dsl": PLACE_OBJECT_DSL,
                "args": {},
            },
            "concept": "move_object_to_constant_target",
            "category": "object_move",
            "confidence": 1.0,
        }

    def _object_constant_offset_rule(self, patterns):
        """Emit the canonical constant-offset move rule when the matcher fires.

        Not a `_try_*`-family detector: recognition is delegated to the
        registered `object_constant_offset` matcher (agent/conditions/), and the
        result is a schema-canonical {condition, action} rule. The constant
        displacement is recomputed at predict time from the example pairs (so the
        rule stays value-agnostic and one rule covers easy000e/f), mirroring the
        constant-target rule but on the *relative* reading of the move DIFF.
        """
        params = {"min_evidence": 2}
        if not match_condition("object_constant_offset", patterns, params):
            return None
        move = patterns.get("object_move") or {}
        evidence = len(move.get("per_pair") or [])
        return {
            "condition": {
                "type": "object_constant_offset",
                "params": dict(params),
                "min_evidence": max(2, evidence),
            },
            "action": {
                "dsl": PLACE_OBJECT_RELATIVE_DSL,
                "args": {},
            },
            "concept": "move_object_by_constant_offset",
            "category": "object_move",
            "confidence": 1.0,
        }

    def _object_corner_target_rule(self, patterns):
        """Emit the canonical constant-corner move rule when the matcher fires.

        Not a `_try_*`-family detector: recognition is delegated to the
        registered `object_corner_target` matcher (agent/conditions/), and the
        result is a schema-canonical {condition, action} rule. The shared corner
        is a *grid-relative* reading (the cross-pair COMM on which canvas corner
        the object lands in); the per-test anchor is recomputed from each test
        grid's own size at predict time, so one rule covers easy000g across
        differing grid sizes. A sibling of the constant-target/offset readings,
        so it lifts into the same `place_object` abstraction (R3)."""
        params = {"min_evidence": 2}
        if not match_condition("object_corner_target", patterns, params):
            return None
        move = patterns.get("object_move") or {}
        evidence = len(move.get("per_pair") or [])
        return {
            "condition": {
                "type": "object_corner_target",
                "params": dict(params),
                "min_evidence": max(2, evidence),
            },
            "action": {
                "dsl": PLACE_OBJECT_CORNER_DSL,
                "args": {"corner": move.get("constant_corner")},
            },
            "concept": "move_object_to_grid_corner",
            "category": "object_move",
            "confidence": 1.0,
        }

    def _object_resize_target_rule(self, patterns):
        """Emit the canonical grid-resize move rule when the matcher fires.

        Not a `_try_*`-family detector: recognition is delegated to the
        registered `object_resize_target` matcher (agent/conditions/), and the
        result is a schema-canonical {condition, action} rule. The output canvas
        size and the target anchor are cross-pair COMMs recomputed at predict
        time from the example outputs (so the rule stays value-agnostic in the
        object's color, source position, and the input size, and one rule covers
        the whole resize family). A sibling of the constant-target/offset/corner
        readings, so it lifts into the same `place_object` abstraction (R3)."""
        params = {"min_evidence": 2}
        if not match_condition("object_resize_target", patterns, params):
            return None
        move = patterns.get("object_move") or {}
        evidence = len(move.get("per_pair") or [])
        return {
            "condition": {
                "type": "object_resize_target",
                "params": dict(params),
                "min_evidence": max(2, evidence),
            },
            "action": {
                "dsl": PLACE_OBJECT_RESIZE_DSL,
                "args": {},
            },
            "concept": "move_object_onto_resized_canvas",
            "category": "object_move",
            "confidence": 1.0,
        }

    def _object_select_target_rule(self, patterns):
        """Emit the canonical multi-object selection move rule when the matcher
        fires.

        Not a `_try_*`-family detector: recognition is delegated to the registered
        `object_select_target` matcher (agent/conditions/), and the result is a
        schema-canonical {condition, action} rule. The learned property selector
        (max_size/min_size/unique_color — agent/dsl_expr/selection.SELECTOR_VOCAB)
        is carried in the action args and re-applied at predict time, while the
        shared target is recomputed from the example outputs, so the rule stays
        value-agnostic in colour, source position and the non-selected
        distractors. A sibling of the constant-target/offset/corner/resize
        readings (it places the *selected* object at a constant target), so it
        lifts into the same `place_object` abstraction (R3)."""
        params = {"min_evidence": 2}
        if not match_condition("object_select_target", patterns, params):
            return None
        sel = patterns.get("object_select_move") or {}
        evidence = len(sel.get("per_pair") or [])
        return {
            "condition": {
                "type": "object_select_target",
                "params": dict(params),
                "min_evidence": max(2, evidence),
            },
            "action": {
                "dsl": PLACE_OBJECT_SELECT_DSL,
                "args": {"selector": sel.get("selector")},
            },
            "concept": "select_object_to_constant_target",
            "category": "object_move",
            "confidence": 1.0,
        }

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

        # Canonical {condition, action} rule for the constant-output family
        # (R0). The prediction is value-agnostic: recompute the common example
        # output and render it via the two frozen primitives, independent of the
        # test input. P5 (variable origin): the answer comes from G0/G1 of the
        # examples, never from the test G1 (there is none).
        action = rule.get("action") if isinstance(rule, dict) else None
        if action and action.get("dsl") == CONSTANT_OUTPUT_DSL:
            common = self._common_output_grid(task)
            if common is not None:
                for i in range(len(task.test_pairs)):
                    key = f"test_{i}"
                    if key not in predictions:
                        predictions[key] = common
            wm.s1["predictions"] = predictions
            return

        # Constant-target object move (R1). Recompute the shared target anchor
        # from the example outputs, then for each test pair render the test
        # object (its color/shape from G0 — P5 variable origin) onto a fresh
        # canvas at that target via make_grid ∘ coloring.
        if action and action.get("dsl") == PLACE_OBJECT_DSL:
            for i, grid in self._place_object_grids(task).items():
                key = f"test_{i}"
                if key not in predictions and grid is not None:
                    predictions[key] = grid
            wm.s1["predictions"] = predictions
            return

        # Constant-*offset* object move (R1, easy000e/f). Recompute the shared
        # displacement from the example pairs, then for each test pair render the
        # test object onto a fresh canvas at (its own anchor + offset).
        if action and action.get("dsl") == PLACE_OBJECT_RELATIVE_DSL:
            for i, grid in self._place_object_offset_grids(task).items():
                key = f"test_{i}"
                if key not in predictions and grid is not None:
                    predictions[key] = grid
            wm.s1["predictions"] = predictions
            return

        # Constant-*corner* object move (R1, easy000g). Recompute the shared grid
        # corner from the example outputs, then for each test pair render the test
        # object flush into that corner of its *own* canvas (size from G0 — P5).
        if action and action.get("dsl") == PLACE_OBJECT_CORNER_DSL:
            for i, grid in self._place_object_corner_grids(task).items():
                key = f"test_{i}"
                if key not in predictions and grid is not None:
                    predictions[key] = grid
            wm.s1["predictions"] = predictions
            return

        # Grid-*resize* object move (R1, easy000i). Recompute the constant output
        # dimensions and the shared target from the example outputs, then for each
        # test pair render the test object onto a fresh canvas of those
        # dimensions (color/shape/background from G0 — P5) at that target.
        if action and action.get("dsl") == PLACE_OBJECT_RESIZE_DSL:
            for i, grid in self._place_object_resize_grids(task).items():
                key = f"test_{i}"
                if key not in predictions and grid is not None:
                    predictions[key] = grid
            wm.s1["predictions"] = predictions
            return

        # Multi-object *selection* move (R1 / §2.5-2b). Recompute the learned
        # selector and shared target from the examples, then for each test pair
        # pick the object the selector names out of that test input's objects and
        # render it onto a fresh canvas at the target (its color/shape/background
        # from G0 — P5; the distractors are simply not drawn).
        if action and action.get("dsl") == PLACE_OBJECT_SELECT_DSL:
            for i, grid in self._place_object_select_grids(task).items():
                key = f"test_{i}"
                if key not in predictions and grid is not None:
                    predictions[key] = grid
            wm.s1["predictions"] = predictions
            return

        for i, test_pair in enumerate(task.test_pairs):
            key = f"test_{i}"
            if key in predictions:
                continue
            g0 = test_pair.input_grid
            if g0 is None:
                continue
            predicted = self._apply_rule(rule, g0)
            if predicted is not None:
                predictions[key] = predicted

        wm.s1["predictions"] = predictions

    @staticmethod
    def _common_output_grid(task):
        """The output grid shared by all example pairs, rendered from the two
        frozen primitives — or None if the example outputs are not all equal."""
        outputs = [
            p.output_grid.raw
            for p in task.example_pairs
            if p.output_grid is not None
        ]
        if not outputs or any(o != outputs[0] for o in outputs):
            return None
        return render_grid_via_primitives(outputs[0])

    @staticmethod
    def _place_object_grids(task):
        """Map test-pair index -> predicted grid for the constant-target move.

        The target is the cross-pair COMM anchor recomputed from the example
        outputs; each test object's color/shape/background come from its own G0
        (never a test G1 — P5). Returns {} when the move analysis does not yield
        a constant target."""
        move = analyze_object_move(task.example_pairs)
        target = move.get("constant_target")
        if target is None:
            return {}

        grids = {}
        for i, test_pair in enumerate(task.test_pairs):
            g0 = test_pair.input_grid
            if g0 is None:
                continue
            obj = unique_object(g0.raw)
            if obj is None:
                continue
            bg = background_of(g0.raw)
            height = len(g0.raw)
            width = len(g0.raw[0]) if g0.raw else 0
            grids[i] = render_object_at(
                height, width, bg, obj["pixels"], tuple(target),
            )
        return grids

    @staticmethod
    def _place_object_offset_grids(task):
        """Map test-pair index -> predicted grid for the constant-offset move.

        The displacement is the cross-pair COMM recomputed from the example
        pairs; each test object's target anchor is its *own* G0 position plus
        that offset (color/shape/background also from its own G0 — never a test
        G1, P5). Returns {} when the move analysis yields no constant offset."""
        move = analyze_object_move(task.example_pairs)
        offset = move.get("constant_offset")
        if offset is None:
            return {}

        grids = {}
        for i, test_pair in enumerate(task.test_pairs):
            g0 = test_pair.input_grid
            if g0 is None:
                continue
            obj = unique_object(g0.raw)
            if obj is None:
                continue
            bg = background_of(g0.raw)
            height = len(g0.raw)
            width = len(g0.raw[0]) if g0.raw else 0
            r0, c0 = obj["position"]
            target = (r0 + offset[0], c0 + offset[1])
            grids[i] = render_object_at(
                height, width, bg, obj["pixels"], target,
            )
        return grids

    @staticmethod
    def _place_object_corner_grids(task):
        """Map test-pair index -> predicted grid for the constant-corner move.

        The corner is the cross-pair COMM (a *grid-relative* reading) recomputed
        from the example outputs; each test object's anchor is the corresponding
        corner of its *own* G0 canvas (color/shape/background/size also from its
        own G0 — never a test G1, P5). Returns {} when the move analysis yields no
        constant corner."""
        move = analyze_object_move(task.example_pairs)
        corner = move.get("constant_corner")
        if corner is None:
            return {}

        grids = {}
        for i, test_pair in enumerate(task.test_pairs):
            g0 = test_pair.input_grid
            if g0 is None:
                continue
            obj = unique_object(g0.raw)
            if obj is None:
                continue
            bg = background_of(g0.raw)
            height = len(g0.raw)
            width = len(g0.raw[0]) if g0.raw else 0
            obj_h, obj_w = extent_of(obj)
            target = corner_anchor(corner, height, width, obj_h, obj_w)
            grids[i] = render_object_at(
                height, width, bg, obj["pixels"], target,
            )
        return grids

    @staticmethod
    def _place_object_resize_grids(task):
        """Map test-pair index -> predicted grid for the grid-resize move.

        The output canvas size and the target anchor are cross-pair COMMs
        recomputed from the example outputs; each test object's color/shape/
        background come from its own G0 (never a test G1 — P5), but the canvas is
        sized by the learned output dimensions rather than the input. Returns {}
        when the move analysis yields no constant output size or target."""
        move = analyze_object_move(task.example_pairs)
        output_dims = move.get("output_dims")
        target = move.get("constant_target")
        if output_dims is None or target is None:
            return {}

        out_h, out_w = output_dims
        grids = {}
        for i, test_pair in enumerate(task.test_pairs):
            g0 = test_pair.input_grid
            if g0 is None:
                continue
            obj = unique_object(g0.raw)
            if obj is None:
                continue
            bg = background_of(g0.raw)
            grids[i] = render_object_at(
                out_h, out_w, bg, obj["pixels"], tuple(target),
            )
        return grids

    @staticmethod
    def _place_object_select_grids(task):
        """Map test-pair index -> predicted grid for the multi-object selection
        move.

        The selector name and shared target are recomputed from the example pairs
        (the §2.5-2b lift: the criterion that consistently picks the preserved
        object); each test object is *chosen* from its own G0's objects by that
        selector and rendered at the target (color/shape/background from its own
        G0 — never a test G1, P5; non-selected objects are not drawn). Returns {}
        when the analysis yields no consistent selector or target."""
        sel = analyze_object_select_move(task.example_pairs)
        selector_name = sel.get("selector")
        target = sel.get("constant_target")
        if selector_name is None or target is None:
            return {}
        selector = SELECTOR_VOCAB.get(selector_name)
        if selector is None:
            return {}

        grids = {}
        for i, test_pair in enumerate(task.test_pairs):
            g0 = test_pair.input_grid
            if g0 is None:
                continue
            obj = selector(objects_of(g0.raw), g0.raw)
            if obj is None:
                continue
            bg = background_of(g0.raw)
            height = len(g0.raw)
            width = len(g0.raw[0]) if g0.raw else 0
            grids[i] = render_object_at(
                height, width, bg, obj["pixels"], tuple(target),
            )
        return grids

    # ---- rule application dispatchers ------------------------------------

    def _apply_rule(self, rule, input_grid):
        rule_type = rule.get("type")
        if rule_type == "recolor_sequential":
            return self._apply_recolor_sequential(rule, input_grid)
        if rule_type == "color_mapping":
            return self._apply_color_mapping(rule, input_grid)
        if rule_type == "identity":
            return [row[:] for row in input_grid.raw]
        return None

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
