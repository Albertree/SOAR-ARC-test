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
from agent.dsl_expr.render import (
    render_geometric_transform,
    render_scale_transform,
    render_grid_via_primitives,
    render_object_at,
    render_object_recolor,
    render_recolor,
    render_recolor_rank,
    render_solid_rect,
    render_solid_square,
)
from agent.dsl_expr.selection import (
    analyze_canvas_fill,
    analyze_color_remap,
    analyze_geometric_transform,
    analyze_object_move,
    analyze_object_select_move,
    analyze_object_select_recolor,
    analyze_object_size_grid,
    analyze_recolor_rank,
    analyze_scale_transform,
    background_of,
    color_of,
    corner_anchor,
    extent_of,
    objects_of,
    objects_by_color,
    unique_object,
    most_frequent_color,
    COLOR_READING_VOCAB,
    DIM_PROPERTY_VOCAB,
    GRID_DIM_PROPERTY_VOCAB,
    GRID_RECT_DIM_VOCAB,
    RECT_DIM_VOCAB,
    SCALE_FACTOR_VOCAB,
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

#: action.dsl for the multi-object *selective recolor* family (R1 / §2.5-2b) — a
#: same-size grid in which exactly one object (the one a learned selector picks)
#: is repainted to a new colour while every other object is left untouched. The
#: transformation is a single `coloring` call on the selected object's cells; the
#: whole content is the *argument* (the selector + the new colour, read off the
#: example DIFF and recomputed at predict time), so one value-agnostic rule covers
#: the family. The recolor-axis sibling of PLACE_OBJECT_SELECT_DSL and the
#: multi-object converse of RECOLOR_DSL (which a global 1:1 map cannot express).
OBJECT_SELECT_RECOLOR_DSL = "recolor_selected_object"

#: action.dsl for the object-property *canvas-sizing* family (R1 / §2.1 "grid
#: size is a function of an object's property") — the output is a solid square
#: rendered by a single make_grid call whose side is a learned scalar object
#: property (`size_of`) and whose colour is the object's colour. The orthogonal
#: axis to the move families: the dimension *argument* is the lift, not a literal.
SIZE_GRID_DSL = "size_to_grid"

#: action.dsl for the recolor family (R1 / arbor-dsl-taxonomy) — a same-size grid
#: repainted by a learned 1:1 colour map. The transformation is a `coloring`
#: composition (one call per remapped source colour); the whole content is the
#: *argument* (the colour map read off the example DIFF), recomputed at predict
#: time so one condition-bearing rule covers the family and lifts under AU. The
#: canonical replacement for the legacy condition-less `{type: color_mapping}`.
RECOLOR_DSL = "recolor_map"

#: action.dsl for the rank-based sequential-recolor family (R1 / §2.5-2b ranking
#: selector) — a same-size grid whose source-coloured groups are repainted a
#: contiguous colour run ordered by position. The transformation is a `coloring`
#: composition (one call per group); the whole content is the *argument* — a
#: `rank-by(position)` selector + start colour read off the example DIFF — so one
#: condition-bearing rule covers the family and lifts under AU. The canonical
#: replacement for the legacy condition-less `{type: recolor_sequential}`.
RECOLOR_RANK_DSL = "recolor_by_rank"

#: action.dsl for the solid-canvas colour-fill family (R1 / §2.5-2b colour
#: reading) — the output is a solid canvas at the input's own size whose colour is
#: a learned grid colour-reading (`most_frequent_color`). The colour analogue of
#: SIZE_GRID_DSL: a single `make_grid` fill whose *colour argument* is the lift
#: (read off the test input — P5), not a literal. Solves the "fill with the
#: dominant colour" family (5582e5ca) that the 1:1 `color_remap` cannot express.
CANVAS_FILL_DSL = "fill_canvas"

#: action.dsl for the whole-grid *geometric transform* family (R1 / BACKLOG_LOOP
#: §2.5-1 worked example) — the input grid flipped / rotated / transposed by a
#: single learned coordinate permutation (flip_h/flip_v/rot90/rot180/rot270/
#: transpose/anti_transpose — agent/dsl_expr/selection.GEOMETRIC_VOCAB). The
#: transformation is the frozen `coloring` primitive applied at the *mapped
#: coordinate* (render_geometric_transform): a flip/rotation is `coloring` with a
#: coordinate-mapping expression, not a new primitive (§2.5-1, F3). The whole
#: content is the *argument* — which permutation, read off the example COMM and
#: recomputed at predict time — so one value-agnostic rule covers the family.
GEOMETRIC_TRANSFORM_DSL = "geometric_transform"

#: action.dsl for the whole-grid *scale / replicate* family (R1 / BACKLOG_LOOP
#: §2.5-1 worked example, the scale axis) — the input grid block-upscaled (each
#: cell → a kh×kw block) or tiled (the whole grid repeated kh×kw) by a single
#: learned constant factor + mode (agent/dsl_expr/selection.SCALE_VOCAB). The
#: transformation is the frozen `coloring` primitive applied at the *replicated
#: coordinate* on a `make_grid` canvas (render_scale_transform): a scale/tile is
#: `coloring` with a coordinate-replication expression, not a new primitive
#: (§2.5-1, F3). The whole content is the *argument* — the mode and factor, read
#: off the example COMM (output/input dimension ratio) and recomputed at predict
#: time — so one value-agnostic rule covers the family.
SCALE_TRANSFORM_DSL = "scale_transform"


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

        # Multi-object *selective recolor* (R1 / §2.5-2b, the recolor-axis sibling
        # of object_select_move and the multi-object converse of color_remap):
        # several objects present, exactly one repainted to a new colour by a
        # learned selector, the rest untouched — the blind spot a global 1:1
        # colour map cannot express. Inert (valid_all False) on single-object and
        # global-recolor grids, so it never perturbs the readings above. Computed
        # via the §2.5 selection vocabulary, not hand-coded here.
        patterns["object_select_recolor"] = analyze_object_select_recolor(
            task.example_pairs)

        # Object-property *canvas sizing* (R1 / §2.1 "grid size is a function of
        # an object's property"): the orthogonal axis where the output's
        # dimensions are read off a scalar object property rather than its
        # position. Inert (dim_property None) on the move families, so it never
        # perturbs the readings above. Computed via the §2.5 property vocabulary
        # (agent/dsl_expr/selection), not hand-coded here.
        patterns["object_size_grid"] = analyze_object_size_grid(task.example_pairs)

        # Recolor family (R1 / arbor-dsl-taxonomy): the orthogonal GRID-level
        # reading where geometry is preserved and only colour changes, by a 1:1
        # colour map (the cross-pair COMM on the colour DIFF). Inert (color_map
        # None) whenever the grid resizes or the map is not a function, so it
        # never perturbs the object/size readings above. Computed via the §2.5
        # vocabulary (agent/dsl_expr/selection), not hand-coded here.
        patterns["color_remap"] = analyze_color_remap(task.example_pairs)

        # Rank-based sequential recolor (R1 / §2.5-2b ranking selector): the
        # sibling recolor reading where the new colour is a function of a changed
        # group's *rank by position* (a contiguous colour run) rather than its
        # source colour. Inert (sort_key None) whenever the grid resizes, a group
        # is not single-coloured, or the colours are not a sortable run, so it
        # never perturbs the readings above. Computed via the §2.5 selection
        # vocabulary (agent/dsl_expr/selection), not hand-coded here — the
        # canonical replacement for the legacy condition-less producer.
        patterns["recolor_rank"] = analyze_recolor_rank(task.example_pairs)

        # Solid-canvas colour fill (R1 / §2.5-2b colour reading): the colour
        # analogue of object_size_grid — the output is a solid canvas at the
        # input's own size whose colour is a learned grid colour-reading
        # (`most_frequent_color`). Inert (fill_reading None) unless every output is
        # a same-size solid fill whose colour a named reading reproduces, so it
        # never perturbs the readings above. Computed via the §2.5 colour-reading
        # vocabulary (agent/dsl_expr/selection), not hand-coded here.
        patterns["canvas_fill"] = analyze_canvas_fill(task.example_pairs)

        # Whole-grid *geometric transform* (R1 / BACKLOG_LOOP §2.5-1 worked
        # example): the input flipped / rotated / transposed by a single learned
        # coordinate permutation — a flip/rotation expressed as the frozen
        # `coloring` primitive at a mapped coordinate, not a new primitive. Inert
        # (transform None) whenever no single map reproduces all pairs, so it never
        # perturbs the move / recolor / sizing readings above. Computed via the
        # §2.5 coordinate vocabulary (agent/dsl_expr/selection), not hand-coded here.
        patterns["geometric_transform"] = analyze_geometric_transform(
            task.example_pairs)

        # Whole-grid *scale / replicate* (R1 / BACKLOG_LOOP §2.5-1 worked example,
        # scale axis): the input block-upscaled (each cell → a block) or tiled by a
        # single learned constant factor + mode — a scale/tile expressed as the
        # frozen `coloring` primitive at a replicated coordinate on a `make_grid`
        # canvas, not a new primitive. Inert (mode None) whenever no single constant
        # factor+mode reproduces all pairs (in particular on every same-size task),
        # so it never perturbs the readings above. Computed via the §2.5 scale
        # vocabulary (agent/dsl_expr/selection), not hand-coded here.
        patterns["scale_transform"] = analyze_scale_transform(task.example_pairs)

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

        # Strategy 0a (R1 / BACKLOG_LOOP §2.5-1 worked example): the whole-grid
        # *geometric transform* family. If the `geometric_transform` matcher fires
        # (a single learned coordinate permutation — flip/rotation/transpose —
        # reproduces every example output exactly), emit a canonical {condition,
        # action} rule carrying *empty* args — the transform name is recomputed at
        # predict time, so one value-agnostic rule covers the family (it merges by
        # condition+action equivalence, like `copy_common_output`, rather than
        # accreting one literal rule per task — §2.5-3/4). Checked first among the
        # transform strategies: it is an exact full-grid reproduction, so it never
        # mis-fires for a move / recolor / sizing task (those abstain on a flip,
        # and a flip abstains unless the whole grid maps), and ordering it ahead
        # keeps a genuine geometric task from being mis-claimed downstream.
        # Recognition is delegated to the registered matcher, not a hand-coded
        # detector.
        if rule is None:
            rule = self._geometric_transform_rule(patterns)

        # Strategy 0a' (R1 / BACKLOG_LOOP §2.5-1 worked example, scale axis): the
        # whole-grid *scale / replicate* family. If the `scale_transform` matcher
        # fires (a single learned constant factor + mode — block-upscale or tile —
        # reproduces every example output exactly), emit a canonical {condition,
        # action} rule carrying *empty* args — the mode and factor are recomputed at
        # predict time, so one value-agnostic rule covers the family (it merges by
        # condition+action equivalence, like the geometric family, rather than
        # accreting one literal rule per task — §2.5-3/4). Like the geometric family
        # this is an exact full-grid reproduction, and it only fires when the output
        # is an integer multiple of the input size, so it never mis-fires for a
        # same-size move / recolor / sizing / geometric task. Recognition is
        # delegated to the registered matcher, not a hand-coded detector.
        if rule is None:
            rule = self._scale_transform_rule(patterns)

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

        # Strategy 0g (R1 / §2.1): the object-property *canvas-sizing* family. If
        # the `object_size_grid` matcher fires (every example renders a solid
        # square whose side is a learned scalar object property and whose colour
        # is the object's colour), emit a canonical {condition, action} rule
        # carrying the dimension property. The property and colour are recomputed
        # at predict time off each test object — value-agnostic in colour, size,
        # shape and position — so one rule covers the family. Recognition is
        # delegated to the registered matcher, not a hand-coded detector.
        if rule is None:
            rule = self._object_size_grid_rule(patterns)

        # Strategy 0h (R1 / arbor-dsl-taxonomy): the recolor family. If the
        # `color_remap` matcher fires (a same-size grid repainted by a 1:1 colour
        # map that is constant across examples), emit a canonical {condition,
        # action} rule whose action is a `coloring` composition keyed on the map.
        # The map is recomputed at predict time off the example DIFF, so the rule
        # is value-agnostic in geometry and — being condition-bearing — liftable
        # by anti-unification (R3) and reusable by the Fast path, unlike the
        # legacy condition-less `{type: color_mapping}` envelope it replaces.
        if rule is None:
            rule = self._color_remap_rule(patterns)

        # Strategy 0i (R1 / §2.5-2b selection lift): multi-object *selective
        # recolor*. If the `object_select_recolor` matcher fires (several objects
        # present, exactly one repainted to a new colour by a learned selector,
        # the rest untouched), emit a canonical {condition, action} rule whose
        # action carries empty args — the selector and new colour are recomputed at
        # predict time, so one value-agnostic rule covers the whole family. Checked
        # *after* `color_remap` so a genuine global 1:1 map (e.g. a unique-coloured
        # object) keeps its `color_remap` reading, but *before* `recolor_rank` so a
        # single changed group is not mis-claimed by the rank family (whose render
        # would repaint *all* same-coloured cells, including the untouched
        # distractor). This fires only in the blind spot a global map cannot express
        # (one of two same-coloured objects recolored). Recognition is delegated to
        # the registered matcher, not a hand-coded detector.
        if rule is None:
            rule = self._object_select_recolor_rule(patterns)

        # Strategy 1 (R1 / §2.5-2b colour reading): solid-canvas colour fill. If
        # the `canvas_fill` matcher fires (every example output is a solid canvas
        # at the input's own size whose colour a learned grid colour-reading
        # reproduces), emit a canonical {condition, action} rule carrying the
        # reading name — the colour analogue of the object-property canvas sizing
        # (Strategy 0g). The reading is recomputed at predict time off each test
        # input, so the rule is value-agnostic in the actual fill colour. Checked
        # *before* `recolor_rank`: a uniform single-colour output is more
        # specifically a *fill* than a rank-recolor, and on a background-dominant
        # grid `recolor_rank` would otherwise misclaim it (reading the lone
        # background region as a ranked group and painting a literal start colour).
        # `canvas_fill` only matches when *every* output is a same-size solid
        # colour, which a genuine rank-recolor (multi-colour output) never is, so
        # taking precedence here cannot steal a task `recolor_rank` solves
        # correctly. Covers the minority-fill family (madeup_fill_foreground_color,
        # least_frequent_color) and the dominant-fill family (5582e5ca,
        # most_frequent_color), lifted into one rule by R3 anti-unification.
        if rule is None:
            rule = self._canvas_fill_rule(patterns)

        # Strategy 2 (R1 / §2.5-2b ranking selector): rank-based sequential
        # recolor. If the `recolor_rank` matcher fires (changed groups repainted a
        # contiguous colour run ordered by a consistent position key), emit a
        # canonical {condition, action} rule carrying the ordering key — the
        # condition-bearing replacement for the legacy condition-less
        # `_try_recolor_sequential` producer (dropped this iter, §5.1-allowed).
        if rule is None:
            rule = self._recolor_rank_rule(patterns)

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

    # ---- strategy: whole-grid geometric transform (R1) ------------------

    def _geometric_transform_rule(self, patterns):
        """Emit the canonical whole-grid geometric-transform rule when the
        `geometric_transform` matcher fires.

        Not a `_try_*`-family detector: recognition is delegated to the registered
        `geometric_transform` matcher (agent/conditions/), and the result is a
        schema-canonical {condition, action} rule. The action carries *empty* args
        — the learned coordinate permutation (flip_h/flip_v/rot90/rot180/rot270/
        transpose/anti_transpose — agent/dsl_expr/selection.GEOMETRIC_VOCAB) is
        recomputed at predict time from the example pairs, so the rule is value-,
        colour-, shape- and size-agnostic and one rule covers the whole family (it
        merges by condition+action equivalence, like `copy_common_output`, rather
        than accreting one literal rule per task — §2.5-3/4). The transformation
        bottoms out in the frozen `coloring` primitive applied at the mapped
        coordinate (render_geometric_transform); no new transformation is
        introduced (§2.5-1, F3)."""
        params = {"min_evidence": 2}
        if not match_condition("geometric_transform", patterns, params):
            return None
        sig = patterns.get("geometric_transform") or {}
        evidence = int(sig.get("evidence", 0))
        return {
            "condition": {
                "type": "geometric_transform",
                "params": dict(params),
                "min_evidence": max(2, evidence),
            },
            "action": {
                "dsl": GEOMETRIC_TRANSFORM_DSL,
                "args": {},
            },
            "concept": "geometric_transform",
            "category": "geometric_transform",
            "confidence": 1.0,
        }

    # ---- strategy: whole-grid scale / replicate (R1) --------------------

    def _scale_transform_rule(self, patterns):
        """Emit the canonical whole-grid scale/replicate rule when the
        `scale_transform` matcher fires.

        Not a `_try_*`-family detector: recognition is delegated to the registered
        `scale_transform` matcher (agent/conditions/), and the result is a
        schema-canonical {condition, action} rule. The action carries *empty* args
        — the learned mode + constant factor (block/tile × (kh, kw) —
        agent/dsl_expr/selection.SCALE_VOCAB) is recomputed at predict time from the
        example pairs, so the rule is value-, colour- and content-agnostic and one
        rule covers the whole family (it merges by condition+action equivalence,
        like the geometric family, rather than accreting one literal rule per task —
        §2.5-3/4). The transformation bottoms out in the frozen `coloring` primitive
        applied at the replicated coordinate on a `make_grid` canvas
        (render_scale_transform); no new transformation is introduced (§2.5-1,
        F3)."""
        params = {"min_evidence": 2}
        if not match_condition("scale_transform", patterns, params):
            return None
        sig = patterns.get("scale_transform") or {}
        evidence = int(sig.get("evidence", 0))
        return {
            "condition": {
                "type": "scale_transform",
                "params": dict(params),
                "min_evidence": max(2, evidence),
            },
            "action": {
                "dsl": SCALE_TRANSFORM_DSL,
                "args": {},
            },
            "concept": "scale_transform",
            "category": "scale_transform",
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
        shared placement (a constant target *or* a constant offset of the selected
        object) is recomputed from the example pairs, so the rule stays
        value-agnostic in colour, source position and the non-selected
        distractors. A sibling of the constant-target/offset/corner/resize
        readings (it places the *selected* object by a constant target or offset),
        so it lifts into the same `place_object` abstraction (R3)."""
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
            "concept": "select_object_constant_move",
            "category": "object_move",
            "confidence": 1.0,
        }

    def _object_size_grid_rule(self, patterns):
        """Emit the canonical object-property canvas-sizing rule when the matcher
        fires.

        Not a `_try_*`-family detector: recognition is delegated to the registered
        `object_size_grid` matcher (agent/conditions/), and the result is a
        schema-canonical {condition, action} rule. The learned dimension property
        (`object_size` — agent/dsl_expr/selection.DIM_PROPERTY_VOCAB) is carried in
        the action args and re-applied at predict time, while the colour and the
        side are recomputed off each test object, so the rule stays value-agnostic
        in the object's colour, size, shape and position. The orthogonal sibling
        of the object-move readings: it sizes a fresh canvas from a *property
        expression* instead of placing the object's pixels, but bottoms out in the
        same frozen `make_grid` primitive (§2.5-1)."""
        params = {"min_evidence": 2}
        if not match_condition("object_size_grid", patterns, params):
            return None
        sz = patterns.get("object_size_grid") or {}
        evidence = len(sz.get("per_pair") or [])
        # The dimension property is the lift key (one `size_to_grid` skeleton
        # spans object_size/bbox_height/object_count). When the subject is a
        # *selected* object among several (§2.5-2b), the learned selector is
        # recorded too so the rule is self-describing — the AU lift keys only on
        # `dim_property`, so a selector-bearing rule still folds into the same
        # abstraction (the selector is re-derived at predict time off the test
        # objects, like the property and colour).
        args = {"dim_property": sz.get("dim_property")}
        if sz.get("selector"):
            args["selector"] = sz.get("selector")
        return {
            "condition": {
                "type": "object_size_grid",
                "params": dict(params),
                "min_evidence": max(2, evidence),
            },
            "action": {
                "dsl": SIZE_GRID_DSL,
                "args": args,
            },
            "concept": "object_size_to_solid_square",
            "category": "object_size_grid",
            "confidence": 1.0,
        }

    # ---- strategy: sequential recoloring --------------------------------

    def _recolor_rank_rule(self, patterns):
        """Emit the canonical rank-based recolor rule when the `recolor_rank`
        matcher fires.

        Not a `_try_*`-family detector: recognition is delegated to the registered
        `recolor_rank` matcher (agent/conditions/), and the result is a
        schema-canonical {condition, action} rule. This is the canonical
        replacement for the legacy condition-less `_try_recolor_sequential`
        (arbor.md 진단 #4: a dropped-condition rule is an anti-unification
        dead-end). The learned argument is a `rank-by(position)` selector (the
        §2.5-2b ranking selector — `argsort` in the selection vocabulary), carried
        in the action args *and* recomputed at predict time off the example DIFF,
        so the rule stays value-agnostic in the absolute colours, positions and
        group count and one rule covers the family. Being condition-bearing and
        keyed on an ordinal selector, two such rules lift under anti-unification
        (R3); the transformation bottoms out in the frozen `coloring` primitive
        (§2.5-1), the rank ordering being the only argument.
        """
        params = {"min_evidence": 2}
        if not match_condition("recolor_rank", patterns, params):
            return None
        sig = patterns.get("recolor_rank") or {}
        return {
            "condition": {
                "type": "recolor_rank",
                "params": dict(params),
                "min_evidence": max(2, sig.get("evidence", 2)),
            },
            "action": {
                "dsl": RECOLOR_RANK_DSL,
                # The selector is recomputed from the examples at predict time, so
                # this carried copy is for self-description / AU lifting, not the
                # live argument.
                "args": {
                    "sort_key": sig.get("sort_key"),
                    "start_color": sig.get("start_color"),
                    "source_colors": list(sig.get("source_colors") or []),
                },
            },
            "concept": "recolor_objects_by_rank",
            "category": "recolor_rank",
            "confidence": 1.0,
        }

    # ---- strategy: multi-object selective recolor (§2.5-2b) -------------

    def _object_select_recolor_rule(self, patterns):
        """Emit the canonical multi-object selective-recolor rule when the
        `object_select_recolor` matcher fires.

        Not a `_try_*`-family detector: recognition is delegated to the registered
        `object_select_recolor` matcher (agent/conditions/), and the result is a
        schema-canonical {condition, action} rule. The action carries *empty* args
        — the learned selector (max_size/min_size/unique_color/unique_shape/
        border_object — agent/dsl_expr/selection.SELECTOR_VOCAB) and the new colour
        are both recomputed at predict time from the example pairs, so the rule is
        value-agnostic in colour, position and the non-selected distractors and one
        rule covers the whole family (it merges by condition+action equivalence,
        like `place_object_constant`, rather than accreting one literal rule per
        task — §2.5-3/4). The recolor-axis sibling of `_object_select_target_rule`
        and the multi-object converse of `_color_remap_rule`: it repaints the
        *selected* object's cells (one frozen `coloring` call) where a global 1:1
        map cannot (two same-coloured objects must diverge). Recognition is
        delegated to the registered matcher, not a hand-coded detector."""
        params = {"min_evidence": 2}
        if not match_condition("object_select_recolor", patterns, params):
            return None
        sig = patterns.get("object_select_recolor") or {}
        evidence = len(sig.get("per_pair") or [])
        return {
            "condition": {
                "type": "object_select_recolor",
                "params": dict(params),
                "min_evidence": max(2, evidence),
            },
            "action": {
                "dsl": OBJECT_SELECT_RECOLOR_DSL,
                "args": {},
            },
            "concept": "recolor_selected_object",
            "category": "object_select_recolor",
            "confidence": 1.0,
        }

    # ---- strategy: recolor by 1:1 colour map (canonical) ----------------

    def _color_remap_rule(self, patterns):
        """Emit the canonical recolor rule when the `color_remap` matcher fires.

        Not a `_try_*`-family detector: recognition is delegated to the registered
        `color_remap` matcher (agent/conditions/), and the result is a
        schema-canonical {condition, action} rule. This is the canonical
        replacement for the legacy condition-less `_try_color_mapping` (arbor.md
        진단 #4: a dropped-condition rule is an anti-unification dead-end). The
        learned colour map is carried in the action args *and* recomputed at
        predict time off the examples, so the rule stays value-agnostic in
        geometry and one rule covers the whole recolor family. Being
        condition-bearing and keyed on a colour→colour COMM, two such rules lift
        under anti-unification (R3); the transformation bottoms out in the frozen
        `coloring` primitive (§2.5-1), the map being the only argument.
        """
        params = {"min_evidence": 2}
        if not match_condition("color_remap", patterns, params):
            return None
        sig = patterns.get("color_remap") or {}
        color_map = sig.get("color_map") or {}
        return {
            "condition": {
                "type": "color_remap",
                "params": dict(params),
                "min_evidence": max(2, sig.get("evidence", 2)),
            },
            "action": {
                "dsl": RECOLOR_DSL,
                # JSON keys must be strings; the map is recomputed from the
                # examples at predict time, so this carried copy is for
                # self-description / AU lifting, not the live argument.
                "args": {"color_map": {str(k): v for k, v in color_map.items()}},
            },
            "concept": "recolor_by_color_map",
            "category": "color_remap",
            "confidence": 1.0,
        }

    # ---- strategy: solid-canvas colour fill (canonical) -----------------

    def _canvas_fill_rule(self, patterns):
        """Emit the canonical solid-canvas colour-fill rule when the `canvas_fill`
        matcher fires.

        Not a `_try_*`-family detector: recognition is delegated to the registered
        `canvas_fill` matcher (agent/conditions/), and the result is a
        schema-canonical {condition, action} rule. The colour analogue of
        `_object_size_grid_rule`: the output is a solid canvas (a single
        `make_grid` fill, §2.5-1) whose *colour* is a learned grid colour-reading
        (`most_frequent_color`) recomputed at predict time off each test input, so
        the rule stays value-agnostic in the actual fill colour and one rule covers
        the family. The reading — not the literal colour — is the lifted argument,
        so this is the §2.5-2b "colour hole filled by a grounded reading" point on
        the colour axis. Solves the "fill with the dominant colour" family
        (ARC-AGI-2 5582e5ca) the 1:1 `color_remap` structurally cannot.
        """
        params = {"min_evidence": 2}
        if not match_condition("canvas_fill", patterns, params):
            return None
        sig = patterns.get("canvas_fill") or {}
        return {
            "condition": {
                "type": "canvas_fill",
                "params": dict(params),
                "min_evidence": max(2, sig.get("evidence", 2)),
            },
            "action": {
                "dsl": CANVAS_FILL_DSL,
                # The reading is recomputed from the test input at predict time, so
                # this carried copy is for self-description / AU lifting, not the
                # live argument.
                "args": {"fill_reading": sig.get("fill_reading")},
            },
            "concept": "fill_canvas_with_color_reading",
            "category": "canvas_fill",
            "confidence": 1.0,
        }


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

        # Multi-object *selective recolor* (R1 / §2.5-2b). Recompute the learned
        # selector and constant new colour from the examples, then for each test
        # pair pick the object the selector names out of that test input's objects
        # and repaint only its cells to the new colour via one `coloring` call
        # (the rest of the grid, including same-coloured distractors, untouched —
        # P5: selector/colour from the example DIFF, geometry from the test G0).
        if action and action.get("dsl") == OBJECT_SELECT_RECOLOR_DSL:
            for i, grid in self._object_select_recolor_grids(task).items():
                key = f"test_{i}"
                if key not in predictions and grid is not None:
                    predictions[key] = grid
            wm.s1["predictions"] = predictions
            return

        # Whole-grid *geometric transform* (R1 / §2.5-1). Recompute the learned
        # coordinate permutation from the examples, then for each test pair apply
        # it to that test input (P5: the transform name is read off the example
        # COMM, the cells are the test G0) — a flip/rotation rendered as the frozen
        # `coloring` primitive at the mapped coordinate.
        if action and action.get("dsl") == GEOMETRIC_TRANSFORM_DSL:
            for i, grid in self._geometric_transform_grids(task).items():
                key = f"test_{i}"
                if key not in predictions and grid is not None:
                    predictions[key] = grid
            wm.s1["predictions"] = predictions
            return

        # Whole-grid *scale / replicate* (R1 / §2.5-1, scale axis). Recompute the
        # learned mode + constant factor from the examples, then for each test pair
        # apply it to that test input (P5: the mode/factor read off the example
        # COMM, the cells from the test G0) — a block-upscale / tile rendered as the
        # frozen `coloring` primitive at the replicated coordinate on a `make_grid`
        # canvas.
        if action and action.get("dsl") == SCALE_TRANSFORM_DSL:
            for i, grid in self._scale_transform_grids(task).items():
                key = f"test_{i}"
                if key not in predictions and grid is not None:
                    predictions[key] = grid
            wm.s1["predictions"] = predictions
            return

        # Object-property *canvas sizing* (R1 / §2.1). Recompute the learned
        # dimension property from the examples, then for each test pair read that
        # property and the colour off the test object (P5) and render a solid
        # square of that side via a single make_grid call.
        if action and action.get("dsl") == SIZE_GRID_DSL:
            for i, grid in self._place_size_grid_grids(task).items():
                key = f"test_{i}"
                if key not in predictions and grid is not None:
                    predictions[key] = grid
            wm.s1["predictions"] = predictions
            return

        # Recolor family (R1 / arbor-dsl-taxonomy). Recompute the 1:1 colour map
        # from the example DIFF (P5 variable origin: the map comes from G0/G1 of
        # the examples), then repaint each test input by it via `coloring`. The
        # geometry of the test input is preserved; only colours change.
        if action and action.get("dsl") == RECOLOR_DSL:
            for i, grid in self._recolor_grids(task).items():
                key = f"test_{i}"
                if key not in predictions and grid is not None:
                    predictions[key] = grid
            wm.s1["predictions"] = predictions
            return

        # Rank-based sequential recolor (R1 / §2.5-2b). Recompute the ordering key
        # and start colour from the example DIFF (P5 variable origin), then repaint
        # each test input's source-coloured groups in that rank order via
        # `coloring`. Geometry is preserved; only the group colours change.
        if action and action.get("dsl") == RECOLOR_RANK_DSL:
            for i, grid in self._recolor_rank_grids(task).items():
                key = f"test_{i}"
                if key not in predictions and grid is not None:
                    predictions[key] = grid
            wm.s1["predictions"] = predictions
            return

        # Solid-canvas colour fill (R1 / §2.5-2b). Recompute the learned colour
        # reading from the examples, then for each test pair fill a fresh canvas at
        # that test input's own size with the reading's value off the test input
        # (P5 variable origin: the colour is read from G0, never a test G1).
        if action and action.get("dsl") == CANVAS_FILL_DSL:
            for i, grid in self._canvas_fill_grids(task).items():
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

        The selector name and the shared placement reading are recomputed from the
        example pairs (the §2.5-2b lift: the criterion that consistently picks the
        preserved object, plus the cross-pair COMM on its move). Each test object is
        *chosen* from its own G0's objects by that selector and rendered at the
        learned placement — a constant absolute target, or its own anchor plus a
        constant offset when the absolute target varies (mirroring the single-object
        constant-offset family). color/shape/background come from its own G0 (never
        a test G1, P5); non-selected objects are not drawn. Returns {} when the
        analysis yields no consistent selector or placement reading."""
        sel = analyze_object_select_move(task.example_pairs)
        selector_name = sel.get("selector")
        target = sel.get("constant_target")
        offset = sel.get("constant_offset")
        if selector_name is None or (target is None and offset is None):
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
            if target is not None:
                anchor = tuple(target)
            else:
                r0, c0 = obj["position"]
                anchor = (r0 + offset[0], c0 + offset[1])
            grids[i] = render_object_at(
                height, width, bg, obj["pixels"], anchor,
            )
        return grids

    @staticmethod
    def _geometric_transform_grids(task):
        """Map test-pair index -> predicted grid for the whole-grid geometric
        transform family.

        The coordinate permutation (flip/rotation/transpose) is recomputed from the
        example pairs (the §2.5-1 lifted argument: the single named map that
        reproduces every example output). For each test pair that map is applied to
        the test input via render_geometric_transform — `make_grid` + `coloring` at
        the mapped coordinate (P5: the transform name from the example COMM, the
        cells from the test G0). Returns {} when the analysis yields no consistent
        transform."""
        sig = analyze_geometric_transform(task.example_pairs)
        transform = sig.get("transform")
        if transform is None:
            return {}

        grids = {}
        for i, test_pair in enumerate(task.test_pairs):
            g0 = test_pair.input_grid
            if g0 is None:
                continue
            grids[i] = render_geometric_transform(g0.raw, transform)
        return grids

    @staticmethod
    def _scale_transform_grids(task):
        """Map test-pair index -> predicted grid for the whole-grid scale/replicate
        family.

        The mode + factor (block-upscale or tile × (kh, kw)) is recomputed from the
        example pairs (the §2.5-1 lifted argument: the single mode+factor that
        reproduces every example output). The factor is either a cross-pair constant
        or — the §2.5-2b factor-axis lift — a property *read off each input*
        (`factor_expr`, e.g. distinct-colour count / grid side). For each test pair
        the replication is applied to the test input via render_scale_transform —
        `make_grid` + `coloring` at the replicated coordinate (P5: the mode/factor
        from the example COMM, the per-test factor and cells from the test G0).
        Returns {} when the analysis yields no consistent mode+factor."""
        sig = analyze_scale_transform(task.example_pairs)
        mode = sig.get("mode")
        if mode is None:
            return {}
        factor = sig.get("factor")
        factor_expr = sig.get("factor_expr")

        grids = {}
        for i, test_pair in enumerate(task.test_pairs):
            g0 = test_pair.input_grid
            if g0 is None:
                continue
            if factor is not None:
                kh, kw = factor
            elif factor_expr is not None:
                # Read the per-test factor off this test input (P5: variables come
                # from the test G0), the same property that fit every example pair.
                k = SCALE_FACTOR_VOCAB[factor_expr](g0.raw)
                if not isinstance(k, int) or k < 1:
                    continue
                kh = kw = k
            else:
                continue
            grids[i] = render_scale_transform(g0.raw, mode, kh, kw)
        return grids

    @staticmethod
    def _object_select_recolor_grids(task):
        """Map test-pair index -> predicted grid for the multi-object selective
        recolor family.

        The selector name and the new colour are recomputed from the example pairs
        (the §2.5-2b lift: the criterion that consistently picks the recolored
        object, plus the new colour). The new colour is either a constant cross-pair
        COMM (`new_color`) or a *reading* off another object — the colour of the
        object a learned donor selector (`color_reading`) picks, the colour-argument
        analogue of the selector lift. For each test pair the selector chooses one
        object out of that test input's own objects, and only its cells are
        repainted to the (per-test recomputed) colour via one frozen `coloring`
        call — every other object (including a same-coloured distractor) is left
        untouched, which is precisely what a global 1:1 map cannot do. Geometry comes
        from the test G0 (P5). Returns {} when the analysis yields no consistent
        selector, or neither a constant colour nor a donor reading."""
        sig = analyze_object_select_recolor(task.example_pairs)
        selector_name = sig.get("selector")
        new_color = sig.get("new_color")
        reading = sig.get("color_reading")
        if selector_name is None or (new_color is None and reading is None):
            return {}
        selector = SELECTOR_VOCAB.get(selector_name)
        if selector is None:
            return {}
        donor = SELECTOR_VOCAB.get(reading) if new_color is None else None
        if new_color is None and donor is None:
            return {}

        grids = {}
        for i, test_pair in enumerate(task.test_pairs):
            g0 = test_pair.input_grid
            if g0 is None:
                continue
            objs = objects_of(g0.raw)
            obj = selector(objs, g0.raw)
            if obj is None:
                continue
            color = new_color
            if color is None:
                donor_obj = donor(objs, g0.raw)
                color = color_of(donor_obj) if donor_obj is not None else None
                if color is None:
                    continue
            grids[i] = render_object_recolor(g0.raw, obj["cells"], color)
        return grids

    @staticmethod
    def _place_size_grid_grids(task):
        """Map test-pair index -> predicted grid for the object-property
        canvas-sizing family.

        The dimension property is recomputed from the example pairs (the §2.1
        lift: the scalar object property whose value reproduces the output side in
        every pair). For each test pair the property and the colour are read off
        that test input's own object (P5), and a solid square of that side is
        rendered by a single make_grid call. Returns {} when the analysis yields
        no consistent dimension property, or the test object is missing / has no
        single colour."""
        sz = analyze_object_size_grid(task.example_pairs)
        prop_name = sz.get("dim_property")
        if prop_name is None:
            return {}
        selector_name = sz.get("selector")
        obj_prop = DIM_PROPERTY_VOCAB.get(prop_name)
        grid_prop = GRID_DIM_PROPERTY_VOCAB.get(prop_name)
        rect_prop = RECT_DIM_VOCAB.get(prop_name)
        grid_rect_prop = GRID_RECT_DIM_VOCAB.get(prop_name)
        if (obj_prop is None and grid_prop is None and rect_prop is None
                and grid_rect_prop is None):
            return {}
        select_fn = SELECTOR_VOCAB.get(selector_name) if selector_name else None
        if selector_name is not None and select_fn is None:
            return {}

        grids = {}
        for i, test_pair in enumerate(task.test_pairs):
            g0 = test_pair.input_grid
            if g0 is None:
                continue
            if rect_prop is not None:
                # Rectangular reading (§2.1 non-square): the canvas is an object's
                # bbox extent ``(h, w)``, colour its own colour — value-agnostic in
                # the object's colour, size, shape and position (P5). A single
                # make_grid fill, no square assumption.
                if select_fn is not None:
                    # Selected-object subject (§2.5-2b): among several test objects
                    # the selector picks the one whose extent sizes the canvas, read
                    # off the analysis's learned segmentation (per-colour when nested
                    # coloured regions must be separated). value-agnostic in the
                    # distractors, colours, sizes and positions (P5).
                    seg = sz.get("segmentation", "connected")
                    objs = (objects_by_color(g0.raw) if seg == "by_color"
                            else objects_of(g0.raw))
                    obj = select_fn(objs, g0.raw)
                else:
                    obj = unique_object(g0.raw)
                if obj is None:
                    continue
                color = color_of(obj)
                h, w = rect_prop(obj)
                if color is None or h < 1 or w < 1:
                    continue
                grids[i] = render_solid_rect(h, w, color)
                continue
            if grid_rect_prop is not None:
                # Grid-level rectangular reading (§2.1 grid-size = f(input
                # structure)): the canvas dims count the test input's own
                # separator-delimited partition bands, the fill is its content
                # (majority) colour — value-agnostic in the separator/content
                # colours, the band counts and the grid size (P5). A single
                # make_grid fill, no object and no square assumption.
                raw = g0.raw or []
                dims = grid_rect_prop(raw)
                color = most_frequent_color(raw) if raw else None
                if dims is None or color is None:
                    continue
                h, w = dims
                if h < 1 or w < 1:
                    continue
                grids[i] = render_solid_rect(h, w, color)
                continue
            if select_fn is not None:
                # Selected-object subject (§2.5-2b): among several test objects,
                # the selector picks the one the size is read off; the property
                # and colour come from that chosen object — value-agnostic in the
                # distractors, colours, sizes and positions (P5).
                chosen = select_fn(objects_of(g0.raw), g0.raw)
                if chosen is None:
                    continue
                color = color_of(chosen)
                side = obj_prop(chosen)
            elif obj_prop is not None:
                # Per-object property: read it (and the colour) off the single
                # test object — value-agnostic in colour/size/shape/position (P5).
                obj = unique_object(g0.raw)
                if obj is None:
                    continue
                color = color_of(obj)
                side = obj_prop(obj)
            else:
                # Grid-level property (object_count): the side counts the test
                # grid's own objects; the colour is the object-set's shared colour.
                objs = objects_of(g0.raw)
                colors = {o["color"] for o in objs if o.get("color") is not None}
                color = next(iter(colors)) if len(colors) == 1 else None
                side = grid_prop(objs)
            if color is None or side < 1:
                continue
            grids[i] = render_solid_square(side, color)
        return grids

    @staticmethod
    def _recolor_grids(task):
        """Per-test grids for the recolor family. Recompute the 1:1 colour map
        from the example DIFF (value-agnostic, P5: from G0/G1 of the examples),
        then repaint each test input by it via the frozen `coloring` primitive."""
        sig = analyze_color_remap(task.example_pairs)
        color_map = sig.get("color_map")
        grids = {}
        if not color_map:
            return grids
        for i, test_pair in enumerate(task.test_pairs):
            g0 = test_pair.input_grid
            if g0 is None:
                continue
            grids[i] = render_recolor(g0.raw, color_map)
        return grids

    @staticmethod
    def _recolor_rank_grids(task):
        """Per-test grids for the rank-based recolor family. Recompute the ordering
        key, start colour and source colours from the example DIFF (value-agnostic,
        P5: from G0/G1 of the examples), then repaint each test input's
        source-coloured groups in that rank order via the frozen `coloring`
        primitive. Returns {} when the analysis yields no consistent ordering."""
        sig = analyze_recolor_rank(task.example_pairs)
        if sig.get("sort_key") is None:
            return {}
        grids = {}
        for i, test_pair in enumerate(task.test_pairs):
            g0 = test_pair.input_grid
            if g0 is None:
                continue
            grids[i] = render_recolor_rank(
                g0.raw,
                sig["sort_key"],
                sig["start_color"],
                sig["source_colors"],
            )
        return grids

    @staticmethod
    def _canvas_fill_grids(task):
        """Per-test grids for the solid-canvas colour-fill family. Recompute the
        learned colour reading from the examples (value-agnostic, P5: the reading
        is fixed by the examples but its *value* is read off each test input), then
        fill a fresh canvas at the test input's own size with that colour via the
        frozen `make_grid` primitive. Returns {} when the analysis yields no
        consistent reading."""
        sig = analyze_canvas_fill(task.example_pairs)
        name = sig.get("fill_reading")
        if name is None:
            return {}
        reading = COLOR_READING_VOCAB[name]
        grids = {}
        for i, test_pair in enumerate(task.test_pairs):
            g0 = test_pair.input_grid
            if g0 is None:
                continue
            raw = g0.raw or []
            height = len(raw)
            width = len(raw[0]) if height else 0
            if height < 1 or width < 1:
                continue
            grids[i] = render_solid_rect(height, width, reading(raw))
        return grids

    # ---- rule application dispatchers ------------------------------------

    def _apply_rule(self, rule, input_grid):
        # Canonical {condition, action} rules are rendered by the action.dsl
        # branches in PredictOperator.effect (copy_common_output / size_to_grid /
        # recolor / recolor_rank / fill_canvas / place_object). This fallback only
        # handles the `identity` no-op rule the generalizer emits when no family
        # matches. The legacy `{type: recolor_sequential | color_mapping}` appliers
        # were removed once the canonical `recolor_rank` / `color_remap`
        # condition-bearing families superseded them (INVARIANTS P6 / §5.1: remove
        # methods that anti-unification-based generalization made dead — there is
        # no producer and no stored rule in that legacy shape).
        if rule.get("type") == "identity":
            return [row[:] for row in input_grid.raw]
        return None


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
