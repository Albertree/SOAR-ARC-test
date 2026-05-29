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
from agent import conditions
from agent.compare_scheduler import build_patterns


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

        # Recognition-first (Slice 1): the value-agnostic all-outputs-COMM path.
        # When the example pairs are complete + the test output is missing
        # (test_output_missing) AND every example output grid is COMM under a
        # role-aligned Inter-Grid comparison (all_outputs_comm), the test output
        # is the *common* example output — copied, not computed. This dispatches
        # via the recognition registry (CLAUDE.md §6.3), not a hand-coded
        # detector, so no new _try_* is introduced.
        if self._recognizes_copy_common_output(wm):
            rule = {"type": "copy_common_output", "confidence": 1.0}

        # No principled (comparison-grounded) rule recognised -> identity, the
        # null hypothesis. ARBOR deliberately does NOT fall back to hand-coded
        # surface detectors here: an answer must have a basis in COMM/DIFF
        # comparison (P3/P4), and a missing basis is reported as "no
        # transformation found" (identity, confidence 0) rather than papered
        # over with a pattern-matched heuristic. The mechanism that *discovers*
        # new bases is anti-unification (CLAUDE.md §8), never a growing _try_*
        # family (CLAUDE.md §5.1). The retired detectors (recolor_sequential /
        # color_mapping) were that family; they are gone, not extended.
        if rule is None:
            rule = {"type": "identity", "confidence": 0.0}

        wm.s1["active-rules"] = [rule]

    # ---- recognition: value-agnostic copy-common-output -----------------

    @staticmethod
    def _recognizes_copy_common_output(wm) -> bool:
        """True iff the Slice-1 copy-common-output mechanism applies.

        The intended §3 two-step (SLICE_1_LOOP.md §3), fed by module C
        (compare_scheduler.build_patterns) and both value-agnostic — the matchers
        read only COMM/DIFF verdicts and grid counts, never a colour/coordinate
        value, so it fires identically for easy000a (red) and easy000a2 (green):
          1. test_output_missing (PAIR): the test pair carries input only
             (grid_count 1 vs the examples' 2) — its output must be constructed.
             Live now that ARCManager loads it with output_grid=None (P5).
          2. all_outputs_comm (GRID): role-aligned Inter-Grid over the example
             outputs is COMM on {size, color, contents}, so the test output is
             that common grid. min_evidence=1 needs >=2 outputs compared.
        """
        task = getattr(wm, "task", None)
        if task is None:
            return False
        patterns = build_patterns(task)
        if not conditions.match("test_output_missing", patterns,
                                {"min_evidence": 1}):
            return False
        return bool(
            conditions.match(
                "all_outputs_comm", patterns,
                {"min_evidence": 1,
                 "required_properties": ["size", "color", "contents"]},
            )
        )


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

        # Value-agnostic copy-common-output (Slice 1): the answer is the common
        # example output grid, *copied* — never a hard-coded literal. It is read
        # from the task's own example outputs here (where wm.task is available),
        # so the same rule stays general across tasks with different outputs.
        common_output = None
        if rule.get("type") == "copy_common_output":
            common_output = self._common_example_output(task)

        for i, test_pair in enumerate(task.test_pairs):
            key = f"test_{i}"
            if key in predictions:
                continue
            g0 = test_pair.input_grid
            if g0 is None:
                continue
            if common_output is not None:
                # Materialise the answer bottom-up through the two frozen DSL
                # primitives (make_grid + coloring) rather than copying it
                # wholesale, so the copy_common_output action's declared
                # action.dsl is actually executed (CLAUDE.md §6.1/§6.2). Still
                # value-agnostic: reconstructed from the task's own common
                # example output, with no stored literal.
                from agent.memory import reconstruct_via_dsl
                predicted = reconstruct_via_dsl(common_output)
            else:
                predicted = self._apply_rule(rule, g0)
            if predicted is not None:
                predictions[key] = predicted

        wm.s1["predictions"] = predictions

    @staticmethod
    def _common_example_output(task):
        """Return the common example output grid (raw) iff all example outputs
        are identical, else None.

        Value-agnostic: returns *whatever* the shared output is. The
        all_outputs_comm precondition guarantees this is well-defined when the
        copy-common-output rule fires; the equality re-check here is a guard so
        a misfire degrades to "no prediction" rather than a wrong answer.
        """
        raws = []
        for pair in task.example_pairs:
            g1 = pair.output_grid
            if g1 is None:
                return None
            raws.append(g1.raw)
        if not raws:
            return None
        first = raws[0]
        for other in raws[1:]:
            if other != first:
                return None
        return [row[:] for row in first]

    # ---- rule application dispatchers ------------------------------------

    def _apply_rule(self, rule, input_grid):
        """Apply a per-grid transform rule to one input grid.

        Only the value-agnostic ``identity`` (null transform) survives here.
        The hand-coded ``recolor_sequential`` / ``color_mapping`` appliers were
        retired together with their producers (the closed _try_*/_apply_*
        family, CLAUDE.md §5.1) — new transformational vocabulary is meant to be
        *discovered* via anti-unification and dispatched from the data layer
        (CLAUDE.md §6.2), not hand-written here. An unrecognised rule type
        yields ``None`` ("no prediction") rather than a guessed transform (P3).
        """
        rule_type = rule.get("type")
        if rule_type == "identity":
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
