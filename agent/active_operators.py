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

from collections import Counter

from agent.operators import Operator
from agent.conditions import match as match_condition
from agent.dsl_expr import (
    objects_of, unique, color_of, size_of, position_of, corners_at, corner_cell,
)
from procedural_memory.DSL.apply import apply_DSL
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

        # Object-level transition: for each example pair, select the single
        # foreground object in G0 and G1 (via the seed selection vocabulary) and
        # record the COMM/DIFF between them — same color/size (COMM), moved
        # position (DIFF). This is the symbolic evidence R1's object-level
        # matcher keys on (BACKLOG_LOOP.md R1, §2.5-2b): a moving object selected
        # by `unique(objects_of(G))` and read by `color_of`/`size_of`/
        # `position_of`, never a raw cell literal. Surfaced here as a signal
        # only; acting on it (placing via make_grid/coloring + the R3 lift) is a
        # later rung, exactly as `output_invariant` preceded the R0 wiring.
        patterns["object_transition"] = self._object_transition(task)

        wm.s1["patterns"] = patterns

    def _object_transition(self, task):
        """Aggregate the per-pair single-object COMM/DIFF across example pairs.

        Returns a symbolic dict::

            {
              "all_single":      bool,   # every pair: exactly one fg object in G0 and G1
              "color_preserved": bool,   # every pair: color_of(G0 obj) == color_of(G1 obj)
              "shape_preserved": bool,   # every pair: size_of(G0 obj) == size_of(G1 obj)
              "moved":           bool,   # every pair: position_of differs G0->G1
              "evidence_count":  int,    # number of example pairs examined
            }

        Computed purely from `agent.dsl_expr` so the selection/property reads
        are the lift-ready expressions (`unique(objects_of(G))`, `color_of`,
        `size_of`, `position_of`), not ad-hoc cell scans.

        Also surfaces the two *target-filling* sub-signals (BACKLOG_LOOP.md R1,
        §2.5-2b), each the precondition of one filling of `place_object`'s target
        hole:
          - fixed cell: every output object lands on the same cell
            (`target_constant` / `target_cell` — the COMM of the example output
            positions), read by `single_object_move_fixed_target`;
          - constant displacement: every pair shares one Δ=(dr, dc)
            (`displacement_constant` / `displacement` — the COMM of the per-pair
            position DIFFs), read by `single_object_move_constant_displacement`.
        Plus whether the output grid keeps the input grid's size
        (`outsize_preserved`). These extra keys are ignored by the base
        `single_object_move` matcher.
        """
        pairs = []
        for pair in task.example_pairs:
            if pair.input_grid is None or pair.output_grid is None:
                continue
            src = unique(objects_of(pair.input_grid.raw))
            dst = unique(objects_of(pair.output_grid.raw))
            in_size = (pair.input_grid.height, pair.input_grid.width)
            out_size = (pair.output_grid.height, pair.output_grid.width)
            pairs.append((src, dst, in_size, out_size))

        if not pairs:
            return {
                "all_single": False, "color_preserved": False,
                "shape_preserved": False, "moved": False,
                "target_constant": False, "target_cell": None,
                "displacement_constant": False, "displacement": None,
                "corner_constant": False, "corner": None,
                "outsize_preserved": False, "evidence_count": 0,
            }

        all_single = all(src is not None and dst is not None for src, dst, _, _ in pairs)
        color_preserved = all_single and all(
            color_of(src) == color_of(dst) for src, dst, _, _ in pairs
        )
        shape_preserved = all_single and all(
            size_of(src) == size_of(dst) for src, dst, _, _ in pairs
        )
        moved = all_single and all(
            position_of(src) != position_of(dst) for src, dst, _, _ in pairs
        )

        # Fixed-cell target: every output object at the same (row, col) — the
        # COMM of the example output positions, derived value-agnostically.
        out_positions = [position_of(dst) for _, dst, _, _ in pairs] if all_single else []
        target_constant = bool(out_positions) and all(
            p == out_positions[0] for p in out_positions
        )
        target_cell = out_positions[0] if target_constant else None

        # Constant displacement: every pair's object moves by the same Δ — the
        # COMM of the per-pair position DIFFs (DIFF position_of(G0)->G1). Disjoint
        # from target_constant: a fixed landing cell forces Δ to vary, and a
        # constant Δ forces the landing cell to vary (the next filling, §2.5-2b).
        displacements = [
            (position_of(dst)[0] - position_of(src)[0],
             position_of(dst)[1] - position_of(src)[1])
            for src, dst, _, _ in pairs
        ] if all_single else []
        displacement_constant = bool(displacements) and all(
            d == displacements[0] for d in displacements
        )
        displacement = displacements[0] if displacement_constant else None

        # Relative corner: every output object lands on the same grid corner —
        # the COMM (intersection) of `corners_at(position_of(dst), H, W)` across
        # pairs, relative to each output grid's own bounds. A corner is invariant
        # across differently-sized grids where a fixed cell is not (the next
        # filling, §2.5-2b); disjoint from displacement (a corner tracking the
        # bounds gives a varying Δ when the grids differ in size).
        corner_sets = [
            corners_at(position_of(dst), outsz[0], outsz[1])
            for _, dst, _, outsz in pairs
        ] if all_single else []
        common_corners = (
            set.intersection(*corner_sets) if corner_sets else set()
        )
        corner_constant = bool(common_corners)
        corner = sorted(common_corners)[0] if common_corners else None

        outsize_preserved = all(insz == outsz for _, _, insz, outsz in pairs)

        return {
            "all_single": all_single,
            "color_preserved": color_preserved,
            "shape_preserved": shape_preserved,
            "moved": moved,
            "target_constant": target_constant,
            "target_cell": target_cell,
            "displacement_constant": displacement_constant,
            "displacement": displacement,
            "corner_constant": corner_constant,
            "corner": corner,
            "outsize_preserved": outsize_preserved,
            "evidence_count": len(pairs),
        }

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
    Reads extracted patterns and builds a `{condition, action}` transformation
    rule by consulting the condition-matcher registry (recognition vocabulary).

    R0 path: when the `constant_output` matcher fires (all example outputs are
    the same grid — the Inter-Grid G1 COMM), emit a value-agnostic rule whose
    action reconstructs that common grid via the two frozen primitives
    (`make_grid` ∘ `coloring`). The *same module* handles every member of the
    constant-output family (easy0001/0005/0009/0013/000a/000b); the differing
    grid is derived from each task's example outputs at apply time, never
    hard-coded — so all of them dedup into one rule with a growing `covers`
    (BACKLOG_LOOP.md R0, §2.5). When no matcher fires, fall back to identity so
    the pipeline still completes (identity is not persisted).
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

        # R0: recognize the constant-output family via the registered matcher.
        if match_condition("constant_output", patterns):
            rule = self._build_constant_output_rule(patterns)

        # R1: recognize a single object relocated onto a fixed cell (the COMM of
        # the example output positions). One value-agnostic `place_object` rule
        # covers the whole fixed-target subfamily (easy000c/d/h); the cell and
        # the object's colour are derived per task at apply time, never stored in
        # the rule, so the rule dedups into one with a growing `covers`
        # (BACKLOG_LOOP.md R1, §2.5-2b). Checked after constant_output so the
        # constant-output members (easy000a/b) keep their R0 path.
        elif match_condition("single_object_move_fixed_target", patterns):
            rule = self._build_place_object_rule(patterns)

        # R1: the *constant-displacement* filling of the same `place_object`
        # skeleton — every pair moves the object by one Δ (the COMM of the
        # per-pair DIFFs), landing on different cells (easy000e/f). The skeleton
        # is identical to the fixed-target rule; only the target *function*
        # differs (carried in action.args.target_mode) — exactly the variable
        # R3's anti-unification will abstract over the two fillings (§2.5-2b).
        # Disjoint from the fixed-target branch, so order is immaterial here.
        elif match_condition("single_object_move_constant_displacement", patterns):
            rule = self._build_place_object_displacement_rule(patterns)

        # R1: the *relative-corner* filling of the same `place_object` skeleton —
        # every pair lands the object on the same grid corner (the COMM of
        # `corners_at`), which resolves to a different cell per grid size
        # (easy000g). Same skeleton as the other two fillings; only the target
        # function differs (action.args.target_mode="corner") — so save_rule's
        # subsumption folds it into the existing place_object abstraction rather
        # than minting a per-task rule (§2.5-2b/§2.5-4). Disjoint from the prior
        # two branches, so order is immaterial here.
        elif match_condition("single_object_move_relative_corner", patterns):
            rule = self._build_place_object_corner_rule(patterns)

        # Fallback: identity (copy input as output); not persisted.
        if rule is None:
            rule = {"type": "identity", "confidence": 0.0}

        wm.s1["active-rules"] = [rule]

    # ---- R0: constant-output rule construction --------------------------

    def _build_constant_output_rule(self, patterns):
        """Build the value-agnostic `{condition, action}` rule for the
        constant-output family. The action is the *recipe* `copy_common_output`
        — "emit the grid that is the COMM of the example outputs", replayed at
        apply time as `make_grid` ∘ `coloring`. Args are empty: the value comes
        from each task's example outputs, not from this rule (so one rule covers
        the whole family)."""
        invariant = patterns.get("output_invariant") or {}
        if not invariant.get("all_equal") or invariant.get("common_output") is None:
            return None
        return {
            "type": "constant_output",            # WM dispatch tag for PredictOperator
            "concept": "copy_common_output",
            "category": "constant_output",
            "condition": {
                "type": "constant_output",
                "params": {},
                "min_evidence": 2,
            },
            "action": {
                "dsl": "copy_common_output",
                "args": {},
            },
            "confidence": 1.0,
        }

    # ---- R1: place-object rule construction -----------------------------

    def _build_place_object_rule(self, patterns):
        """Build the value-agnostic `{condition, action}` rule for the
        fixed-target move subfamily. The action is the *recipe* `place_object`
        — "relocate the single object onto the cell that is the COMM of the
        example output positions", replayed at apply time as
        `make_grid` ∘ `coloring`. Args are empty: the target cell and the
        object colour are derived from each task's own grids (P5: from G0 +
        the example outputs), not stored here — so one rule covers the whole
        subfamily (§2.5-2b / §2.5-3)."""
        transition = patterns.get("object_transition") or {}
        if not transition.get("target_constant") or transition.get("target_cell") is None:
            return None
        return {
            "type": "place_object",               # WM dispatch tag for PredictOperator
            "concept": "place_moved_object",
            "category": "single_object_move",
            "condition": {
                # Persisted condition.type is the *parent* matcher (the move
                # family), not the dispatch-time filling matcher. The two
                # fillings (fixed / displacement) therefore share a skeleton
                # (same condition.type + action.dsl), differing only in
                # action.args.target_mode — exactly the position R3's
                # anti_unification.unify() lifts to one variable (§2.5-2b).
                "type": "single_object_move",
                "params": {"min_evidence": 2},
            },
            "action": {
                "dsl": "place_object",
                "args": {},               # target_mode absent ⇒ "fixed" (render default)
            },
            "confidence": 1.0,
        }

    def _build_place_object_displacement_rule(self, patterns):
        """Build the value-agnostic `{condition, action}` rule for the
        constant-displacement move subfamily. Same `place_object` recipe as the
        fixed-target rule — "relocate the single object, erase its source, paint
        at the target" via `make_grid` ∘ `coloring` — but the target is the test
        object's own position offset by the COMM displacement Δ
        (`action.args.target_mode = "displacement"`). Args carry only the filling
        *mode*, not Δ itself: Δ is re-derived from each task's example pairs at
        apply time (P5: from G0->G1 of the examples), so one rule covers the
        whole subfamily (easy000e/f) and never stores a per-task literal
        (§2.5-2b / §2.5-3)."""
        transition = patterns.get("object_transition") or {}
        if not transition.get("displacement_constant") or transition.get("displacement") is None:
            return None
        return {
            "type": "place_object",               # WM dispatch tag for PredictOperator
            "concept": "place_displaced_object",
            "category": "single_object_move",
            "condition": {
                # Same parent skeleton as the fixed-target filling (see
                # _build_place_object_rule); the *only* structural difference is
                # action.args.target_mode below, which R3 lifts to a variable.
                "type": "single_object_move",
                "params": {"min_evidence": 2},
            },
            "action": {
                "dsl": "place_object",
                "args": {"target_mode": "displacement"},
            },
            "confidence": 1.0,
        }

    def _build_place_object_corner_rule(self, patterns):
        """Build the value-agnostic `{condition, action}` rule for the
        relative-corner move subfamily. Same `place_object` recipe as the other
        fillings — "relocate the single object, erase its source, paint at the
        target" via `make_grid` ∘ `coloring` — but the target is the grid corner
        the examples agree on (`action.args.target_mode = "corner"`). Args carry
        only the filling *mode*, not which corner: the corner id is re-derived as
        the COMM of `corners_at` over each task's example outputs at apply time
        (P5: from the example G1s, resolved against the test grid's own bounds),
        so one rule covers the whole subfamily (easy000g) and never stores a
        per-task literal (§2.5-2b / §2.5-3)."""
        transition = patterns.get("object_transition") or {}
        if not transition.get("corner_constant") or transition.get("corner") is None:
            return None
        return {
            "type": "place_object",               # WM dispatch tag for PredictOperator
            "concept": "place_cornered_object",
            "category": "single_object_move",
            "condition": {
                # Same parent skeleton as the other fillings (see
                # _build_place_object_rule); the *only* structural difference is
                # action.args.target_mode below, which R3 lifts to a variable.
                "type": "single_object_move",
                "params": {"min_evidence": 2},
            },
            "action": {
                "dsl": "place_object",
                "args": {"target_mode": "corner"},
            },
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
        # Task in scope for the current effect(); read by constant_output
        # rendering, which derives its grid from the task's example outputs.
        self._task = None

    def precondition(self, wm) -> bool:
        raise NotImplementedError("PredictOperator.precondition() not implemented.")

    def effect(self, wm):
        task = wm.task
        active_rules = wm.s1.get("active-rules")
        if not task or not active_rules:
            return

        self._task = task
        rule = active_rules[0]
        predictions = dict(wm.s1.get("predictions") or {})

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

    # ---- rule application dispatchers ------------------------------------

    def _apply_rule(self, rule, input_grid):
        rule_type = rule.get("type")
        if rule_type == "constant_output":
            return self._render_constant_output(rule, self._task)
        if rule_type == "place_object":
            return self._render_place_object(rule, self._task, input_grid)
        if rule_type == "identity":
            return [row[:] for row in input_grid.raw]
        return None

    def _render_constant_output(self, rule, task):
        """Render the R0 `copy_common_output` action: emit the grid that is the
        COMM of the example outputs, reconstructed via the two frozen primitives
        (`make_grid` ∘ `coloring`). Value-agnostic — the grid is read from the
        task's example outputs (the matcher guarantees they are all identical),
        never from the test pair's own output (P5), and never hard-coded."""
        if task is None:
            return None
        example_outputs = [
            pair.output_grid.raw
            for pair in task.example_pairs
            if pair.output_grid is not None
        ]
        if not example_outputs:
            return None

        common = example_outputs[0]
        height = len(common)
        width = len(common[0]) if common else 0
        if height == 0 or width == 0:
            return None

        # Background = the most frequent color → fewest `coloring` strokes.
        flat = [cell for row in common for cell in row]
        background = Counter(flat).most_common(1)[0][0]

        # make_grid(background) ∘ coloring(non-background cells).
        out = apply_DSL("make_grid", None, height=height, width=width,
                        color=background)
        for r in range(height):
            for c in range(width):
                if common[r][c] != background:
                    out = apply_DSL("coloring", out, selection=(r, c),
                                    color=common[r][c])
        return out

    def _derive_place_target(self, rule, task, src_pos, grid_dims=None):
        """Compute `place_object`'s target cell for the test object at `src_pos`,
        per the rule's filling mode (`action.args.target_mode`, default "fixed").
        `grid_dims` is the test grid's (height, width), used by size-preserving
        fillings (e.g. "corner") to resolve a bounds-relative target. Returns the
        (row, col) target or None if the examples do not actually exhibit the
        mode's invariant. This is the §2.5-2b *target function* — the single point
        at which the fillings differ and the variable R3 lifts."""
        mode = ((rule.get("action") or {}).get("args") or {}).get("target_mode", "fixed")

        if mode == "fixed":
            # COMM of the example output positions (constant landing cell).
            out_positions = []
            for pair in task.example_pairs:
                if pair.output_grid is None:
                    continue
                o = unique(objects_of(pair.output_grid.raw))
                if o is None:
                    return None
                out_positions.append(position_of(o))
            if not out_positions or any(p != out_positions[0] for p in out_positions):
                return None
            return out_positions[0]

        if mode == "displacement":
            # COMM of the per-pair displacements, applied to the test object.
            deltas = []
            for pair in task.example_pairs:
                if pair.input_grid is None or pair.output_grid is None:
                    continue
                si = unique(objects_of(pair.input_grid.raw))
                so = unique(objects_of(pair.output_grid.raw))
                if si is None or so is None:
                    return None
                pi = position_of(si)
                po = position_of(so)
                deltas.append((po[0] - pi[0], po[1] - pi[1]))
            if not deltas or any(d != deltas[0] for d in deltas):
                return None
            return (src_pos[0] + deltas[0][0], src_pos[1] + deltas[0][1])

        if mode == "corner":
            # COMM of the per-pair corner the output object lands on (relative to
            # each output grid's bounds), resolved against the test grid's own
            # bounds. Value-agnostic: the corner is read from the example outputs,
            # the cell from the test grid (size preserved across this filling).
            if grid_dims is None:
                return None
            common = None
            for pair in task.example_pairs:
                if pair.output_grid is None:
                    return None
                o = unique(objects_of(pair.output_grid.raw))
                if o is None:
                    return None
                cs = corners_at(position_of(o),
                                pair.output_grid.height, pair.output_grid.width)
                common = cs if common is None else (common & cs)
            if not common:
                return None
            return corner_cell(sorted(common)[0], grid_dims[0], grid_dims[1])

        return None

    def _render_place_object(self, rule, task, input_grid):
        """Render the R1 `place_object` action: relocate the test grid's single
        object onto a derived target cell, reconstructed via the two frozen
        primitives (`make_grid` ∘ `coloring`).

        The skeleton (read object → erase source by a fresh canvas → paint at
        target) is shared across fillings; only the *target function* differs,
        selected by `action.args.target_mode` (the §2.5-2b variable R3 will
        abstract): "fixed" → the COMM of the example output positions;
        "displacement" → the test object's position offset by the COMM Δ. Both
        derive the target value-agnostically from the example pairs and read the
        object's colour/cells from the *test G0* (never its absent G1, P5);
        nothing is hard-coded."""
        if task is None or input_grid is None:
            return None

        # Read the test object via the seed selection/property vocabulary.
        obj = unique(objects_of(input_grid.raw))
        if obj is None:
            return None
        color = color_of(obj)
        src_pos = position_of(obj)
        if color is None or src_pos is None:
            return None

        height = len(input_grid.raw)
        width = len(input_grid.raw[0]) if input_grid.raw else 0
        if height == 0 or width == 0:
            return None

        target = self._derive_place_target(rule, task, src_pos,
                                           grid_dims=(height, width))
        if target is None:
            return None

        # Background = most-frequent colour across the example outputs (their
        # shared fill), so the source cells are erased by the fresh canvas.
        flat = [
            cell
            for pair in task.example_pairs if pair.output_grid is not None
            for row in pair.output_grid.raw
            for cell in row
        ]
        if not flat:
            return None
        background = Counter(flat).most_common(1)[0][0]

        # Translate the object's cells so its top-left lands on `target`
        # (handles 1×1 and larger single-colour shapes uniformly).
        dr = target[0] - src_pos[0]
        dc = target[1] - src_pos[1]
        placed = []
        for (r, c) in sorted(obj.get("cells") or []):
            nr, nc = r + dr, c + dc
            if not (0 <= nr < height and 0 <= nc < width):
                return None
            placed.append((nr, nc))
        if not placed:
            return None

        out = apply_DSL("make_grid", None, height=height, width=width,
                        color=background)
        for (nr, nc) in placed:
            out = apply_DSL("coloring", out, selection=(nr, nc), color=color)
        return out


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
