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
from itertools import permutations, product

from agent.operators import Operator
from agent.memory_router import log_routing
from ARCKG.comparison import compare as arckg_compare


# ======================================================================
# Composition log (T-UPDATE-1)
# ======================================================================

def _log_composition(rule, task, wm, start_time):
    """Append entry to episodic_memory/composition_log.jsonl. Non-fatal on failure."""
    import os, json, time as _time
    from procedural_memory.base_rules._concept_engine import (
        _last_failure_diagnostics, _ensure_loaded, _concepts, _execute_concept
    )

    os.makedirs("episodic_memory", exist_ok=True)

    nm = _last_failure_diagnostics.get("best_near_miss") if _last_failure_diagnostics else None
    partial_score_before = nm.get("partial_score", 0.0) if nm else 0.0

    intermediate_example = None
    try:
        _ensure_loaded()
        concept_a = next(
            (c for c in _concepts if c["concept_id"] == rule["concept_id_a"]), None
        )
        if concept_a:
            for pair in task.example_pairs:
                if pair.input_grid is not None:
                    intermediate_example = _execute_concept(
                        concept_a, rule.get("params_a", {}), pair.input_grid.raw
                    )
                    break
    except Exception:
        pass

    log_path = "episodic_memory/composition_log.jsonl"
    pair_key = f"{rule['concept_id_a']}+{rule['concept_id_b']}"
    prior_count = 0
    if os.path.exists(log_path):
        try:
            with open(log_path) as f:
                for line in f:
                    try:
                        e = json.loads(line)
                        c = e.get("composition", {})
                        if f"{c.get('concept_id_a')}+{c.get('concept_id_b')}" == pair_key:
                            prior_count += 1
                    except (json.JSONDecodeError, KeyError):
                        continue
        except IOError:
            pass

    entry = {
        "task_hex": task.task_hex,
        "timestamp": _time.strftime("%Y-%m-%dT%H:%M:%S"),
        "composition": {
            "concept_id_a": rule.get("concept_id_a"),
            "params_a": rule.get("params_a", {}),
            "concept_id_b": rule.get("concept_id_b"),
            "params_b": rule.get("params_b", {}),
        },
        "topology": wm.s1.get("task_topology_str"),
        "partial_score_before": partial_score_before,
        "time_to_find_sec": round(_time.time() - start_time, 3),
        "intermediate_example": intermediate_example,
        "formalization_candidate": prior_count >= 4,
    }
    with open(log_path, "a") as f:
        f.write(json.dumps(entry) + "\n")

    if entry["formalization_candidate"]:
        print(f"[COMPOSE] FORMALIZATION CANDIDATE: {pair_key} appeared "
              f"{prior_count + 1} times — consider formalizing as a named concept.")


# ======================================================================
# Shared helpers
# ======================================================================

def _find_outlined_rectangles(grid, outline_color, bg_color):
    """Find rectangles outlined with outline_color whose interior is bg_color."""
    h = len(grid)
    w = len(grid[0]) if grid else 0
    visited = [[False] * w for _ in range(h)]
    rects = []

    for r in range(h):
        for c in range(w):
            if grid[r][c] == outline_color and not visited[r][c]:
                # BFS to find connected component of outline_color
                component = []
                queue = [(r, c)]
                visited[r][c] = True
                while queue:
                    cr, cc = queue.pop(0)
                    component.append((cr, cc))
                    for dr, dc in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                        nr, nc = cr + dr, cc + dc
                        if 0 <= nr < h and 0 <= nc < w and not visited[nr][nc] and grid[nr][nc] == outline_color:
                            visited[nr][nc] = True
                            queue.append((nr, nc))

                # Bounding box
                min_r = min(p[0] for p in component)
                max_r = max(p[0] for p in component)
                min_c = min(p[1] for p in component)
                max_c = max(p[1] for p in component)

                if max_r - min_r < 2 or max_c - min_c < 2:
                    continue

                # Check component matches a perfect rectangle outline
                expected = set()
                for rr in range(min_r, max_r + 1):
                    expected.add((rr, min_c))
                    expected.add((rr, max_c))
                for cc in range(min_c, max_c + 1):
                    expected.add((min_r, cc))
                    expected.add((max_r, cc))

                if set(component) != expected:
                    continue

                # Check interior is all bg_color
                interior_ok = True
                for rr in range(min_r + 1, max_r):
                    for cc in range(min_c + 1, max_c):
                        if grid[rr][cc] != bg_color:
                            interior_ok = False
                            break
                    if not interior_ok:
                        break

                if interior_ok:
                    rects.append((min_r, min_c, max_r, max_c))

    return rects


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
        level = (wm.s1.get("focus") or {}).get("level", "GRID")
        log_routing("select_target", level)

        task = wm.task
        if task is None:
            return

        # G2: Inter-pair check — are all output grids identical across training pairs?
        output_grids = [
            pair.output_grid.raw
            for pair in task.example_pairs
            if pair.output_grid is not None
        ]
        if len(output_grids) >= 2 and all(g == output_grids[0] for g in output_grids[1:]):
            wm.s1["g2_constant_output"] = True
            wm.s1["g2_output_grid"] = output_grids[0]

        # G1 agenda: build GRID-level comparison specs
        agenda = []
        pending = []

        if level == "GRID":
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

        # At OBJECT level: register objects and build object comparison agenda
        if level == "OBJECT":
            from ARCKG.object_matcher import match_objects

            for idx, pair in enumerate(task.example_pairs):
                if pair.input_grid is None or pair.output_grid is None:
                    continue

                in_objs = pair.input_grid.objects or []
                out_objs = pair.output_grid.objects or []

                for obj in in_objs + out_objs:
                    node_lookup[obj.node_id] = obj

                match_result = match_objects(in_objs, out_objs)

                for in_obj, out_obj in match_result["matched"]:
                    spec = {
                        "type": "object",
                        "pair_idx": idx,
                        "pair_type": "example",
                        "id1": in_obj.node_id,
                        "id2": out_obj.node_id,
                        "match_confidence": match_result["match_confidence"],
                    }
                    agenda.append(spec)
                    pending.append(spec)

                if match_result["added"]:
                    wm.s1.setdefault("object_additions", []).extend(
                        {"pair_idx": idx, "node_id": o.node_id}
                        for o in match_result["added"]
                    )
                if match_result["deleted"]:
                    wm.s1.setdefault("object_deletions", []).extend(
                        {"pair_idx": idx, "node_id": o.node_id}
                        for o in match_result["deleted"]
                    )

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
        level = (wm.s1.get("focus") or {}).get("level", "GRID")
        log_routing("compare", level)

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
        level = (wm.s1.get("focus") or {}).get("level", "GRID")
        log_routing("extract_pattern", level)

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

        # Inter-pair consistency: does the transformation look the same across pairs?
        pair_analyses = patterns.get("pair_analyses", [])
        if len(pair_analyses) >= 2:
            pa0 = pair_analyses[0]
            pa1 = pair_analyses[1]
            groups_match = pa0.get("num_groups", 0) == pa1.get("num_groups", 0)
            tc0 = pa0.get("total_changes", 0)
            tc1 = pa1.get("total_changes", 0)
            changes_similar = abs(tc0 - tc1) <= max(tc0, tc1, 1) * 0.2
            patterns["inter_pair_consistent"] = groups_match and changes_similar
            patterns["inter_pair_group_count_match"] = groups_match
        else:
            patterns["inter_pair_consistent"] = None

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
                "max_row": max(r for r, c in positions),
                "max_col": max(c for r, c in positions),
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
    Delegates to the rule engine which dynamically loads rule modules from
    procedural_memory/base_rules/. If no rule matches, falls back to identity.
    """

    def __init__(self, generalize_fn=None, save_fn=None):
        super().__init__("generalize")
        self._generalize_fn = generalize_fn
        self._save_fn = save_fn

    def precondition(self, wm) -> bool:
        raise NotImplementedError("GeneralizeOperator.precondition() not implemented.")

    def effect(self, wm):
        level = (wm.s1.get("focus") or {}).get("level", "GRID")
        log_routing("generalize", level)

        patterns = wm.s1.get("patterns")
        if not patterns:
            return

        task = wm.task
        comparisons = wm.s1.get("comparisons", {})

        # Try chunked activation rules first (topology-based shortcut)
        rule = None
        chunked_hint = None
        try:
            from agent.chunking import try_chunked_rules
            chunked_hint = try_chunked_rules(comparisons, task, patterns=patterns)
            if chunked_hint:
                # Validate the chunked hint against examples
                concept_id = chunked_hint.get("concept_id", "")
                from agent.rule_engine import try_all
                rule = try_all(patterns, task)
                if rule and rule.get("concept_id") == concept_id:
                    print(f"[CHUNK] Chunked rule confirmed: {concept_id}")
                elif rule:
                    pass  # different concept won, that's fine
                # If try_all found nothing, try_all already returns None
        except Exception:
            pass

        # Standard concept matching
        focus_level = (wm.s1.get("focus") or {}).get("level", "GRID")
        if rule is None:
            from agent.rule_engine import try_all
            rule = try_all(patterns, task, focus_level=focus_level)

        # Try two-step composition before falling back to identity
        if rule is None or rule.get("type") == "identity":
            import time as _time
            composition_start_time = _time.time()
            try:
                from procedural_memory.base_rules._concept_engine import try_two_step_composition
                comp = try_two_step_composition(patterns, task, time_budget_sec=2.0)
                if comp is not None:
                    rule = comp
                    print(f"[COMPOSE] Found: {comp['type']}")
                    try:
                        _log_composition(comp, task, wm, composition_start_time)
                    except Exception:
                        pass
            except Exception:
                pass

        # G2 fallback: if all outputs are identical and nothing else matched
        if wm.s1.get("g2_constant_output") and (rule is None or rule.get("type") == "identity"):
            rule = {
                "type": "constant_output",
                "output_grid": wm.s1["g2_output_grid"],
                "confidence": 1.0,
            }

        # Fallback: identity (copy input as output)
        if rule is None:
            rule = {"type": "identity", "confidence": 0.0}
            # Track failure for chunked rules that triggered but didn't validate
            if chunked_hint and chunked_hint.get("chunked_rule_id"):
                try:
                    from agent.chunking import increment_chunked_rule_failure
                    increment_chunked_rule_failure(chunked_hint["chunked_rule_id"])
                except Exception:
                    pass

        # Capture concept-matching diagnostics for failed tasks
        try:
            from procedural_memory.base_rules._concept_engine import _last_failure_diagnostics
            if _last_failure_diagnostics is not None:
                wm.s1["generalize-diagnostics"] = _last_failure_diagnostics
                wm.s1["concepts-tried-count"] = _last_failure_diagnostics.get("concepts_tried", 0)
        except Exception:
            pass

        wm.s1["active-rules"] = [rule]

        # Chunk the resolution if a non-identity rule was found
        if rule.get("type", "identity") != "identity" and comparisons:
            try:
                from agent.chunking import chunk_resolution_to_rule
                chunk_resolution_to_rule(comparisons, rule, task.task_hex, patterns=patterns)
            except Exception:
                pass


# ======================================================================
# DescendOperator -- placeholder for deeper KG exploration
# ======================================================================

class DescendOperator(Operator):
    """Clears GRID-level state, sets focus to OBJECT for object-level analysis."""

    def __init__(self):
        super().__init__("descend")

    def precondition(self, wm) -> bool:
        raise NotImplementedError("DescendOperator.precondition() not implemented.")

    def effect(self, wm):
        # Increment counter FIRST — if clearing fails, counter still blocks re-entry
        wm.s1["descent_count"] = wm.s1.get("descent_count", 0) + 1

        # Record failure type for future type-aware descent
        failure_type = "unknown"
        try:
            from procedural_memory.base_rules._concept_engine import _last_failure_diagnostics
            nm = (_last_failure_diagnostics.get("best_near_miss")
                  if _last_failure_diagnostics else None)
            partial = nm.get("partial_score", 0.0) if nm else 0.0
            if partial > 0.7:
                failure_type = "property_value_mismatch"
            elif partial > 0.4:
                failure_type = "partial_structural"
            else:
                failure_type = "structural"
        except Exception:
            pass

        # Clear GRID-level pipeline state
        for key in ["comparison-agenda", "pending-comparisons", "comparisons",
                    "patterns", "active-rules", "predictions", "generalize-diagnostics"]:
            wm.s1.pop(key, None)

        # Clear elaboration flags so pipeline restarts at SelectTarget
        for key in ["has_pending_comparison", "ready_for_pattern_extraction",
                    "ready_for_generalization", "ready_for_prediction",
                    "all_outputs_found", "needs_target_selection"]:
            wm.active.pop(key, None)

        wm.s1["focus"] = {
            "level": "OBJECT",
            "scope": "within_pair_examples",
            "failure_type": failure_type,
        }

        print(f"[DESCEND] Grid-level failed (type={failure_type}, "
              f"depth={wm.s1['descent_count']}) — descending to OBJECT level")


# ======================================================================
# PredictOperator -- apply rule to test input
# ======================================================================

class PredictOperator(Operator):
    """
    Reads the best rule from active-rules and applies it to each test
    pair's input grid to produce a predicted output grid.
    Delegates to the rule engine for rule application.
    """

    def __init__(self):
        super().__init__("predict")

    def precondition(self, wm) -> bool:
        raise NotImplementedError("PredictOperator.precondition() not implemented.")

    def effect(self, wm):
        level = (wm.s1.get("focus") or {}).get("level", "GRID")
        log_routing("predict", level)

        task = wm.task
        active_rules = wm.s1.get("active-rules")
        if not task or not active_rules:
            return

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

    # ---- rule application dispatcher ------------------------------------

    def _apply_rule(self, rule, input_grid):
        rule_type = rule.get("type")
        if rule_type == "identity":
            return [row[:] for row in input_grid.raw]
        from agent.rule_engine import apply
        return apply(rule_type, rule, input_grid)


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
        level = (wm.s1.get("focus") or {}).get("level", "GRID")
        log_routing("submit", level)

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
