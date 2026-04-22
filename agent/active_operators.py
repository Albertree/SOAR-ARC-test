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
            cells = []
            for cell in group_cells:
                input_colors.add(cell["input_color"])
                output_colors.add(cell["output_color"])
                positions.append((cell["row"], cell["col"]))
                cells.append(cell)

            top_row = min(r for r, c in positions)
            top_col = min(c for r, c in positions)

            group_analyses.append({
                "input_colors": sorted(input_colors),
                "output_colors": sorted(output_colors),
                "top_row": top_row,
                "top_col": top_col,
                "cell_count": len(group_cells),
                "cells": cells,
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

        # Strategy 1: sequential recoloring (e.g., color objects 1, 2, 3, ...)
        rule = self._try_recolor_sequential(patterns)

        # Strategy 2: single-pixel relocation
        if rule is None:
            rule = self._try_pixel_relocate(patterns)

        # Strategy 3: simple 1:1 color mapping
        if rule is None:
            rule = self._try_color_mapping(patterns)

        # Fallback: identity (copy input as output)
        if rule is None:
            rule = {"type": "identity", "confidence": 0.0}

        wm.s1["active-rules"] = [rule]

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

    # ---- strategy: single-pixel relocation -------------------------------

    def _try_pixel_relocate(self, patterns):
        """
        Detect pattern: each training pair has exactly one non-bg pixel that
        moves to a new position (possibly with a color change).  Two sub-modes:
          fixed        -- all pairs share the same destination position
          conditional  -- destination depends on input pixel color
        """
        pair_analyses = patterns.get("pair_analyses", [])
        if not pair_analyses or not patterns.get("grid_size_preserved"):
            return None

        relocations = []  # (src_row, src_col, src_color, dst_row, dst_col, dst_color)
        for analysis in pair_analyses:
            info = self._extract_relocation(analysis)
            if info is None:
                return None
            relocations.append(info)

        # --- Try fixed-destination mode (all pairs same dest) ---
        dest_positions = set((r["dst_row"], r["dst_col"]) for r in relocations)
        if len(dest_positions) == 1:
            dr, dc = dest_positions.pop()
            # Determine color mode
            dst_colors = [r["dst_color"] for r in relocations]
            src_colors = [r["src_color"] for r in relocations]
            if len(set(dst_colors)) == 1:
                # All output colors identical -> fixed color
                return {
                    "type": "pixel_relocate",
                    "mode": "fixed",
                    "dest_row": dr,
                    "dest_col": dc,
                    "color_mode": "fixed",
                    "fixed_color": dst_colors[0],
                    "confidence": 1.0,
                }
            elif all(d == s for d, s in zip(dst_colors, src_colors)):
                # Output color matches input color -> preserve
                return {
                    "type": "pixel_relocate",
                    "mode": "fixed",
                    "dest_row": dr,
                    "dest_col": dc,
                    "color_mode": "preserve",
                    "fixed_color": None,
                    "confidence": 1.0,
                }
            else:
                # Colors disagree — if there's exactly one non-source color, use it
                all_src = set(src_colors)
                non_src = set(dst_colors) - all_src
                if len(non_src) == 1:
                    return {
                        "type": "pixel_relocate",
                        "mode": "fixed",
                        "dest_row": dr,
                        "dest_col": dc,
                        "color_mode": "fixed",
                        "fixed_color": non_src.pop(),
                        "confidence": 0.8,
                    }

        # --- Try color-conditional mode (group by input color) ---
        color_groups = {}
        for r in relocations:
            c = r["src_color"]
            if c not in color_groups:
                color_groups[c] = []
            color_groups[c].append(r)

        if len(color_groups) < 2:
            # Same color but different dests — try source-position-conditional
            src_positions = set(
                (r["src_row"], r["src_col"]) for r in relocations
            )
            if len(src_positions) == len(relocations) and len(src_positions) > 1:
                # Each pair has a unique source position — build position lookup
                pos_rules = {}
                for rel in relocations:
                    key = f"{rel['src_row']},{rel['src_col']}"
                    pos_rules[key] = {
                        "dest_row": rel["dst_row"],
                        "dest_col": rel["dst_col"],
                        "output_color": rel["dst_color"],
                    }
                return {
                    "type": "pixel_relocate",
                    "mode": "source_conditional",
                    "position_rules": pos_rules,
                    "confidence": 0.8,
                }
            # Fallback: use first pair's relocation
            return {
                "type": "pixel_relocate",
                "mode": "multi_exemplar",
                "relocations": relocations,
                "confidence": 0.6,
            }

        color_rules = {}
        for c, group in color_groups.items():
            dests = set((r["dst_row"], r["dst_col"]) for r in group)
            ocolors = set(r["dst_color"] for r in group)
            if len(dests) != 1 or len(ocolors) != 1:
                # Inconsistent — try source-position-conditional
                src_positions = set(
                    (r["src_row"], r["src_col"]) for r in relocations
                )
                if len(src_positions) == len(relocations) and len(src_positions) > 1:
                    pos_rules = {}
                    for rel in relocations:
                        key = f"{rel['src_row']},{rel['src_col']}"
                        pos_rules[key] = {
                            "dest_row": rel["dst_row"],
                            "dest_col": rel["dst_col"],
                            "output_color": rel["dst_color"],
                        }
                    return {
                        "type": "pixel_relocate",
                        "mode": "source_conditional",
                        "position_rules": pos_rules,
                        "confidence": 0.8,
                    }
                return {
                    "type": "pixel_relocate",
                    "mode": "multi_exemplar",
                    "relocations": relocations,
                    "confidence": 0.6,
                }
            dr, dc = dests.pop()
            oc = ocolors.pop()
            color_rules[c] = {"dest_row": dr, "dest_col": dc, "output_color": oc}

        return {
            "type": "pixel_relocate",
            "mode": "conditional",
            "color_rules": color_rules,
            "confidence": 0.9,
        }

    @staticmethod
    def _extract_relocation(analysis):
        """
        From a pair analysis, extract source and destination of a single-pixel
        relocation.  Returns dict with src_row/col/color, dst_row/col/color
        or None if the pattern doesn't match.

        Handles two cases:
          - 2 groups of 1 cell each (source/dest non-adjacent)
          - 1 group of 2 cells (source/dest are adjacent)
        """
        if analysis["total_changes"] != 2:
            return None

        if analysis["num_groups"] == 2:
            source = dest = None
            for g in analysis["groups"]:
                if g["cell_count"] != 1:
                    return None
                if len(g["input_colors"]) != 1 or len(g["output_colors"]) != 1:
                    return None
                ic, oc = g["input_colors"][0], g["output_colors"][0]
                if ic != 0 and oc == 0:
                    source = g
                elif ic == 0 and oc != 0:
                    dest = g
                else:
                    return None

            if source is None or dest is None:
                return None
            return {
                "src_row": source["top_row"],
                "src_col": source["top_col"],
                "src_color": source["input_colors"][0],
                "dst_row": dest["top_row"],
                "dst_col": dest["top_col"],
                "dst_color": dest["output_colors"][0],
            }

        if analysis["num_groups"] == 1:
            g = analysis["groups"][0]
            if g["cell_count"] != 2:
                return None
            # Adjacent source/dest: one cell nonzero->0, other 0->nonzero
            cells = g.get("cells", [])
            if len(cells) != 2:
                return None
            source = dest = None
            for cell in cells:
                ic, oc = cell["input_color"], cell["output_color"]
                if ic != 0 and oc == 0:
                    source = cell
                elif ic == 0 and oc != 0:
                    dest = cell
                else:
                    return None
            if source is None or dest is None:
                return None
            return {
                "src_row": source["row"],
                "src_col": source["col"],
                "src_color": source["input_color"],
                "dst_row": dest["row"],
                "dst_col": dest["col"],
                "dst_color": dest["output_color"],
            }

        return None

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
        if rule_type == "recolor_sequential":
            return self._apply_recolor_sequential(rule, input_grid)
        if rule_type == "pixel_relocate":
            return self._apply_pixel_relocate(rule, input_grid)
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

    def _apply_pixel_relocate(self, rule, input_grid):
        raw = input_grid.raw
        h = len(raw)
        w = len(raw[0]) if raw else 0

        # Find the single non-zero pixel in the input
        src_color = None
        src_r = src_c = None
        for r in range(h):
            for c in range(w):
                if raw[r][c] != 0:
                    src_color = raw[r][c]
                    src_r, src_c = r, c
                    break
            if src_color is not None:
                break

        if src_color is None:
            return [row[:] for row in raw]

        output = [[0] * w for _ in range(h)]
        mode = rule.get("mode")

        if mode == "fixed":
            dr = rule["dest_row"]
            dc = rule["dest_col"]
            if rule.get("color_mode") == "preserve":
                out_color = src_color
            else:
                out_color = rule.get("fixed_color", src_color)
            if 0 <= dr < h and 0 <= dc < w:
                output[dr][dc] = out_color

        elif mode == "conditional":
            color_rules = rule.get("color_rules", {})
            cr = color_rules.get(src_color)
            if cr is not None:
                dr, dc = cr["dest_row"], cr["dest_col"]
                out_color = cr["output_color"]
                if 0 <= dr < h and 0 <= dc < w:
                    output[dr][dc] = out_color
            else:
                # Unseen color: fall back to identity
                return [row[:] for row in raw]

        elif mode == "source_conditional":
            pos_rules = rule.get("position_rules", {})
            key = f"{src_r},{src_c}"
            pr = pos_rules.get(key)
            if pr is not None:
                dr, dc = pr["dest_row"], pr["dest_col"]
                out_color = pr["output_color"]
                if 0 <= dr < h and 0 <= dc < w:
                    output[dr][dc] = out_color
            else:
                return [row[:] for row in raw]

        elif mode == "multi_exemplar":
            relocations = rule.get("relocations", [])
            if relocations:
                rel = relocations[0]
                dr, dc = rel["dst_row"], rel["dst_col"]
                out_color = rel["dst_color"]
                if 0 <= dr < h and 0 <= dc < w:
                    output[dr][dc] = out_color

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
