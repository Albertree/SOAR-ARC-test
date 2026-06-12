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
    output_dims, argmax, cells_of,
)
from agent.variable_resolution import resolve_variable
from procedural_memory.DSL.apply import apply_DSL
from ARCKG.comparison import compare as arckg_compare


# The bounded, already-known domain of `place_object` target fillings (§2.5-2b).
# When an anti-unification-lifted place_object rule reaches apply time with its
# target_mode still an unresolved `?vN` hole, the render path fills it by
# selecting the first of these that reproduces the examples — NOT by inventing a
# new filling (that is the open Q-B3/Q-B4). Order = the slow-path build priority
# (GeneralizeOperator.effect), so a self-applied abstraction and a freshly-built
# concrete rule resolve identically. Each filling's invariant is checked inside
# `_derive_place_target`, so a non-matching filling renders None and is rejected.
PLACE_OBJECT_FILLINGS = ("fixed", "displacement", "corner")


def _with_target_mode(rule, mode):
    """Return a shallow copy of `rule` with `action.args.target_mode` set to
    `mode` (the concrete filling chosen for an abstract rule's `?vN` hole). The
    nested action/args dicts are copied so the stored abstract rule is left
    untouched — instantiation produces a fresh concrete rule, never a mutation."""
    new = dict(rule)
    action = dict(new.get("action") or {})
    args = dict(action.get("args") or {})
    args["target_mode"] = mode
    action["args"] = args
    new["action"] = action
    return new


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

        # Object-ranking transition (R4, BACKLOG_LOOP.md "2nd-order / ranking
        # relation"): when a grid holds *several* objects, `unique` goes dark and
        # the move pathway above cannot pick *which* object to act on. The ranking
        # selector `argmax(objects_of(G0), size_of)` resolves that by comparing the
        # objects to each other on a property (R1 §2.5-2b's seed selector; the
        # agent-side expression of R4's edge-of-edge relation). Surfaced here as
        # the `object_ranking` signal the `recolor_largest_object` matcher
        # (registered iter 13) keys on — value-agnostic, derived only from the
        # example COMM/DIFF, never a stored literal (P3/P4).
        patterns["object_ranking"] = self._object_ranking(task)

        wm.s1["patterns"] = patterns

    def _object_ranking(self, task):
        """Aggregate the per-pair *size-ranked recolor* signal across example
        pairs (BACKLOG_LOOP.md R4). For each pair: select the single size-maximal
        object of a multi-object G0 via `argmax(objects_of(G0), size_of)` and ask
        whether the output equals the input except that one object is recolored to
        a constant color.

        Returns a symbolic dict (the contract `agent/conditions/
        recolor_largest_object.py` documents)::

            {
              "multi_object":     bool,  # every pair: >1 foreground object in G0
              "select_extreme":   bool,  # every pair: argmax(...,size_of) well-defined
              "recolor_constant": bool,  # every pair: the selected object genuinely
                                         #   recolored to a single color
              "recolor_color":    int|None,  # that fill color, constant across pairs
              "others_unchanged": bool,  # every pair: all non-selected cells identical
              "evidence_count":   int,
            }

        Computed purely from `agent.dsl_expr` (`objects_of` / `argmax` / `size_of`
        / `cells_of`) so the selection is the lift-ready expression
        `argmax(objects_of(G0), size_of)`, not an ad-hoc cell scan. The recolor
        color is read from the example outputs (the COMM of the selected object's
        new color), never from the test pair — so one value-agnostic rule covers
        the whole "recolor the largest object" family (§2.5-3)."""
        pairs = [
            (pair.input_grid, pair.output_grid)
            for pair in task.example_pairs
            if pair.input_grid is not None and pair.output_grid is not None
        ]
        if not pairs:
            return {
                "multi_object": False, "select_extreme": False,
                "recolor_constant": False, "recolor_color": None,
                "others_unchanged": False, "evidence_count": 0,
            }

        sels = []
        multi = []
        for g0, _ in pairs:
            objs = objects_of(g0.raw)
            multi.append(len(objs) > 1)
            # argmax abstains (None) on a tie, so an ambiguous "largest" declines
            # rather than guessing — the value-agnostic discipline (P7).
            sels.append(argmax(objs, size_of) if len(objs) > 1 else None)

        multi_object = all(multi)
        select_extreme = multi_object and all(s is not None for s in sels)

        recolor_ok = []
        others_ok = []
        recolor_colors = []
        if select_extreme:
            for (g0, g1), sel in zip(pairs, sels):
                raw0, raw1 = g0.raw, g1.raw
                if g0.height != g1.height or g0.width != g1.width:
                    recolor_ok.append(False)
                    others_ok.append(False)
                    continue
                cells = cells_of(sel)
                out_colors = {raw1[r][c] for (r, c) in cells}
                # Genuine recolor: the selected object's cells become one color
                # *and* at least one of them actually changed (else it is identity
                # on that object, not a recolor).
                genuine = (
                    len(out_colors) == 1
                    and any(raw0[r][c] != raw1[r][c] for (r, c) in cells)
                )
                recolor_ok.append(genuine)
                recolor_colors.append(next(iter(out_colors)) if genuine else None)
                others_ok.append(all(
                    raw0[r][c] == raw1[r][c]
                    for r in range(g0.height) for c in range(g0.width)
                    if (r, c) not in cells
                ))

        recolor_constant = (
            select_extreme and bool(recolor_ok) and all(recolor_ok)
        )
        others_unchanged = (
            select_extreme and bool(others_ok) and all(others_ok)
        )
        colors = set(recolor_colors) if recolor_constant else set()
        recolor_color = next(iter(colors)) if len(colors) == 1 else None

        return {
            "multi_object": multi_object,
            "select_extreme": select_extreme,
            "recolor_constant": recolor_constant,
            "recolor_color": recolor_color,
            "others_unchanged": others_unchanged,
            "evidence_count": len(pairs),
        }

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
                "outsize_preserved": False, "outsize_constant": False,
                "outsize": None, "evidence_count": 0,
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

        # Constant output size: every output grid shares one (h, w) — the COMM of
        # the example output dims — even when the inputs differ in size (the
        # resize filling, §2.5-1: make_grid's dimensions parameterized from the
        # examples rather than copied from the input, easy000i 6×6->5×5). Disjoint
        # neither way from outsize_preserved: when sizes are preserved *and* the
        # inputs are constant both hold; that overlap is harmless (the corner
        # matcher's disjunction). The actual dims are re-derived value-agnostically
        # at apply time via dsl_expr.output_dims, never stored in the rule.
        out_sizes = {outsz for _, _, _, outsz in pairs}
        outsize_constant = len(out_sizes) == 1
        outsize = next(iter(out_sizes)) if outsize_constant else None

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
            "outsize_constant": outsize_constant,
            "outsize": outsize,
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

        # R4: recognise a *multi-object* grid whose single size-maximal object is
        # recolored to one constant color, everything else untouched. This is the
        # ranking pathway the `single_object_move_*` branches cannot reach (they
        # gate on `all_single`); `argmax(objects_of(G0), size_of)` selects *which*
        # object by comparing them to each other on size (BACKLOG_LOOP.md R4,
        # §2.5-2b). Disjoint from every branch above (multi-object vs single), so
        # order is immaterial. One value-agnostic `recolor_largest` rule covers the
        # whole family — the fill color is re-derived from each task's example
        # outputs at apply time, never stored — so it dedups into one rule with a
        # growing `covers` rather than one per task (§2.5-3).
        elif match_condition("recolor_largest_object", patterns):
            rule = self._build_recolor_largest_rule(patterns)

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
        (P5: from the example G1s, resolved against the *derived output* bounds —
        the input size when preserved, the constant example-output size when
        resized), so one rule covers the whole subfamily — both the size-preserved
        corner movers (easy000g) and the resized one (easy000i 6×6->5×5) — and
        never stores a per-task literal (§2.5-2b / §2.5-3)."""
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

    # ---- R4: recolor-largest rule construction --------------------------

    def _build_recolor_largest_rule(self, patterns):
        """Build the value-agnostic `{condition, action}` rule for the
        size-ranked recolor family. The action is the *recipe* `recolor_largest`
        — "recolor the single size-maximal object to the constant color the
        examples agree on" — replayed at apply time as `coloring` over
        `cells_of(argmax(objects_of(G0), size_of))`. Args are empty: the fill
        color is the COMM of the example outputs' recolored object, re-derived per
        task at apply time (P3/P4), not stored — so one rule covers the whole
        family (§2.5-3)."""
        ranking = patterns.get("object_ranking") or {}
        if not ranking.get("recolor_constant") or ranking.get("recolor_color") is None:
            return None
        return {
            "type": "recolor_largest",            # WM dispatch tag for PredictOperator
            "concept": "recolor_largest_object",
            "category": "object_recolor",
            "condition": {
                "type": "recolor_largest_object",
                "params": {"min_evidence": 2},
            },
            "action": {
                "dsl": "recolor_largest",
                "args": {},               # fill color re-derived at apply time
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
        if rule_type == "recolor_largest":
            return self._render_recolor_largest(rule, self._task, input_grid)
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

    def _render_recolor_largest(self, rule, task, input_grid):
        """Render the R4 `recolor_largest` action: recolor the test grid's single
        size-maximal object to the color the examples agree on, via the frozen
        `coloring` primitive.

        Two value-agnostic derivations, both reading the example pairs (never the
        test pair's absent output, P5):
          - *which object*: `argmax(objects_of(G0), size_of)` — the ranking
            selector picks the largest by comparing the objects to each other;
            abstains (None) on a tie, so an ambiguous "largest" renders nothing.
          - *what color*: the COMM of the example outputs' recolored object (the
            single color the selected cells take in every example G1). If that
            color is not constant across pairs, the recolor is not derivable and
            render returns None.

        The transformation itself is exactly `coloring(cells_of(argmax(...)),
        color)` applied to the test input: the rest of the grid is preserved (the
        matcher guarantees others-unchanged + size-preserved), so the input *is*
        the canvas and only the selected cells are painted — no `make_grid` is
        needed. The selected cells are a lifted expression (`cells_of` of the
        ranked object), never a stored cell-list literal (§2.5-2b)."""
        if task is None or input_grid is None:
            return None

        # Derive the constant fill color from the example outputs (value-agnostic).
        colors = set()
        for pair in task.example_pairs:
            if pair.input_grid is None or pair.output_grid is None:
                return None
            sel = argmax(objects_of(pair.input_grid.raw), size_of)
            if sel is None:
                return None
            cells = cells_of(sel)
            if not cells:
                return None
            out_colors = {pair.output_grid.raw[r][c] for (r, c) in cells}
            if len(out_colors) != 1:
                return None
            colors.add(next(iter(out_colors)))
        if len(colors) != 1:
            return None
        color = next(iter(colors))

        # Select the test grid's largest object and paint its cells.
        sel = argmax(objects_of(input_grid.raw), size_of)
        if sel is None:
            return None
        cells = sorted(cells_of(sel))
        if not cells:
            return None

        out = [row[:] for row in input_grid.raw]
        out = apply_DSL("coloring", out, selection=cells, color=color)
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
        "displacement" → the test object's position offset by the COMM Δ;
        "corner" → the COMM grid corner resolved against the *output* bounds. Both
        derive the target value-agnostically from the example pairs and read the
        object's colour/cells from the *test G0* (never its absent G1, P5);
        nothing is hard-coded.

        The output canvas dimensions are themselves derived value-agnostically
        (`dsl_expr.output_dims`): the same input size when the examples preserve
        size, or the constant example-output size when they resize (easy000i
        6×6->5×5). make_grid's height/width are thus an *argument expression* over
        the examples (§2.5-1), not copied from the input — and the corner target
        is resolved against those derived bounds so a resized corner lands
        correctly.

        If `target_mode` is still an unresolved anti-unification hole (a `?vN`,
        as on the disk-stored abstract rule that R3 lifted), it is *filled* here
        before rendering, by bounded example-grounded selection over
        `PLACE_OBJECT_FILLINGS` (`variable_resolution.resolve_variable`, §2.5-2b):
        the first filling that reproduces every example output is chosen. This is
        what makes the lifted abstraction *self-applying* (the fast path can reuse
        it) instead of a dead, incomplete rule — selection, not invention (the
        candidate set is the already-known fillings; inventing a new one is the
        open Q-B3/Q-B4, out of scope)."""
        if task is None or input_grid is None:
            return None

        # Fill an unresolved target_mode hole by example-grounded selection over
        # the bounded known fillings. resolve_variable invokes this render only
        # with concrete (already-substituted) modes, so it does not recurse.
        mode = ((rule.get("action") or {}).get("args") or {}).get("target_mode", "fixed")
        if isinstance(mode, str) and mode.startswith("?"):
            resolved = resolve_variable(
                task,
                PLACE_OBJECT_FILLINGS,
                lambda m: _with_target_mode(rule, m),
                self._render_place_object,
            )
            if resolved is None:
                return None
            rule = _with_target_mode(rule, resolved)

        # Read the test object via the seed selection/property vocabulary.
        obj = unique(objects_of(input_grid.raw))
        if obj is None:
            return None
        color = color_of(obj)
        src_pos = position_of(obj)
        if color is None or src_pos is None:
            return None

        in_h = len(input_grid.raw)
        in_w = len(input_grid.raw[0]) if input_grid.raw else 0
        if in_h == 0 or in_w == 0:
            return None

        # Derive the output canvas size from how the example outputs relate to
        # their inputs (size-preserved → track the input; constant → that size).
        pair_dims = [
            ((pair.input_grid.height, pair.input_grid.width),
             (pair.output_grid.height, pair.output_grid.width))
            for pair in task.example_pairs
            if pair.input_grid is not None and pair.output_grid is not None
        ]
        dims = output_dims(pair_dims, (in_h, in_w))
        if dims is None:
            return None
        height, width = dims

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
