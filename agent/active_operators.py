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

        task = wm.task
        rule = None

        # Strategy 1: sequential recoloring (e.g., color objects 1, 2, 3, ...)
        rule = self._try_recolor_sequential(patterns)

        # Strategy 2: simple 1:1 color mapping
        if rule is None:
            rule = self._try_color_mapping(patterns)

        # Strategy 3: pixel scaling (each pixel -> NxN block)
        if rule is None:
            rule = self._try_pixel_scaling(patterns, task)

        # Strategy 4: tile with reflection (output = tiled/reflected input)
        if rule is None:
            rule = self._try_tile_reflect(patterns, task)

        # Strategy 5: recolor objects by size ranking
        if rule is None:
            rule = self._try_recolor_by_size(patterns, task)

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

    # ---- strategy: pixel scaling ----------------------------------------

    def _try_pixel_scaling(self, patterns, task):
        """
        Detect pattern: output is an NxN nearest-neighbor upscale of input.
        Each input pixel becomes an NxN block of the same color.
        """
        if not task or not task.example_pairs:
            return None

        pair = task.example_pairs[0]
        g0, g1 = pair.input_grid, pair.output_grid
        if not g0 or not g1:
            return None

        in_h, in_w = g0.height, g0.width
        out_h, out_w = g1.height, g1.width
        if in_h == 0 or in_w == 0:
            return None
        if out_h % in_h != 0 or out_w % in_w != 0:
            return None

        scale_h = out_h // in_h
        scale_w = out_w // in_w
        if scale_h != scale_w or scale_h < 2:
            return None

        scale = scale_h

        for pair in task.example_pairs:
            g0, g1 = pair.input_grid, pair.output_grid
            if not g0 or not g1:
                return None
            if g1.height != g0.height * scale or g1.width != g0.width * scale:
                return None
            raw_in = g0.raw
            raw_out = g1.raw
            for r in range(g0.height):
                for c in range(g0.width):
                    expected = raw_in[r][c]
                    for dr in range(scale):
                        for dc in range(scale):
                            if raw_out[r * scale + dr][c * scale + dc] != expected:
                                return None

        return {"type": "pixel_scaling", "scale": scale, "confidence": 1.0}

    # ---- strategy: tile with reflection ---------------------------------

    def _try_tile_reflect(self, patterns, task):
        """
        Detect pattern: output is tiled copies of input, each tile possibly
        reflected (identity, flip_v, flip_h, or flip_vh).
        Covers vertical/horizontal mirroring and 2x2 tiling.
        """
        if not task or not task.example_pairs:
            return None

        pair = task.example_pairs[0]
        g0, g1 = pair.input_grid, pair.output_grid
        if not g0 or not g1:
            return None

        in_h, in_w = g0.height, g0.width
        out_h, out_w = g1.height, g1.width
        if in_h == 0 or in_w == 0:
            return None
        if out_h % in_h != 0 or out_w % in_w != 0:
            return None

        tiles_h = out_h // in_h
        tiles_w = out_w // in_w
        if tiles_h * tiles_w < 2:
            return None

        tile_map = {}

        for pair in task.example_pairs:
            g0, g1 = pair.input_grid, pair.output_grid
            if not g0 or not g1:
                return None
            if g1.height != g0.height * tiles_h or g1.width != g0.width * tiles_w:
                return None

            raw_in = g0.raw
            raw_out = g1.raw
            h, w = g0.height, g0.width

            for tr in range(tiles_h):
                for tc in range(tiles_w):
                    tile = []
                    for r in range(h):
                        row = []
                        for c in range(w):
                            row.append(raw_out[tr * h + r][tc * w + c])
                        tile.append(row)

                    found = None
                    for name, fn in self._tile_transforms().items():
                        if fn(raw_in) == tile:
                            found = name
                            break

                    if found is None:
                        return None

                    key = f"{tr}_{tc}"
                    if key in tile_map:
                        if tile_map[key] != found:
                            return None
                    else:
                        tile_map[key] = found

        return {
            "type": "tile_reflect",
            "tiles_h": tiles_h,
            "tiles_w": tiles_w,
            "tile_map": tile_map,
            "confidence": 1.0,
        }

    @staticmethod
    def _tile_transforms():
        """Return dict of tile transformation functions."""
        return {
            "identity": lambda g: [r[:] for r in g],
            "flip_v": lambda g: [r[:] for r in g[::-1]],
            "flip_h": lambda g: [r[::-1] for r in g],
            "flip_vh": lambda g: [r[::-1] for r in g[::-1]],
        }

    # ---- strategy: recolor by size ranking ------------------------------

    def _try_recolor_by_size(self, patterns, task):
        """
        Detect pattern: all non-background cells share one color in input.
        Each connected component is recolored based on its size ranking:
        largest -> color 1, second largest -> color 2, etc.
        Ties (same size) get the same color.
        """
        if not task or not task.example_pairs:
            return None
        if not patterns.get("grid_size_preserved"):
            return None

        source_color = None
        rank_to_color = None

        for pair in task.example_pairs:
            g0, g1 = pair.input_grid, pair.output_grid
            if not g0 or not g1:
                return None

            raw_in = g0.raw
            raw_out = g1.raw

            in_colors = set()
            for row in raw_in:
                for c in row:
                    if c != 0:
                        in_colors.add(c)

            if len(in_colors) != 1:
                return None

            sc = list(in_colors)[0]
            if source_color is None:
                source_color = sc
            elif source_color != sc:
                return None

            components = self._find_components(raw_in, source_color)
            if not components:
                return None

            sizes = sorted(set(len(comp) for comp in components), reverse=True)
            size_to_rank = {s: i for i, s in enumerate(sizes)}

            pair_rank_to_color = {}
            valid = True
            for comp in components:
                rank = size_to_rank[len(comp)]
                r0, c0 = comp[0]
                out_color = raw_out[r0][c0]
                if out_color == 0:
                    valid = False
                    break

                for r, c in comp:
                    if raw_out[r][c] != out_color:
                        valid = False
                        break
                if not valid:
                    break

                if rank in pair_rank_to_color:
                    if pair_rank_to_color[rank] != out_color:
                        valid = False
                        break
                else:
                    pair_rank_to_color[rank] = out_color

            if not valid:
                return None

            # Verify background unchanged
            for r in range(len(raw_in)):
                for c in range(len(raw_in[0])):
                    if raw_in[r][c] == 0 and raw_out[r][c] != 0:
                        return None

            if rank_to_color is None:
                rank_to_color = pair_rank_to_color
            elif rank_to_color != pair_rank_to_color:
                return None

        return {
            "type": "recolor_by_size",
            "source_color": source_color,
            "rank_to_color": rank_to_color,
            "confidence": 1.0,
        }

    @staticmethod
    def _find_components(grid, color):
        """Find all 4-connected components of the given color in grid."""
        h = len(grid)
        w = len(grid[0]) if grid else 0
        visited = set()
        components = []

        for r in range(h):
            for c in range(w):
                if grid[r][c] == color and (r, c) not in visited:
                    comp = []
                    queue = [(r, c)]
                    while queue:
                        p = queue.pop(0)
                        if p in visited:
                            continue
                        pr, pc = p
                        if pr < 0 or pr >= h or pc < 0 or pc >= w:
                            continue
                        if grid[pr][pc] != color:
                            continue
                        visited.add(p)
                        comp.append(p)
                        for dr, dc in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                            nb = (pr + dr, pc + dc)
                            if nb not in visited:
                                queue.append(nb)
                    components.append(comp)

        return components


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
        if rule_type == "color_mapping":
            return self._apply_color_mapping(rule, input_grid)
        if rule_type == "pixel_scaling":
            return self._apply_pixel_scaling(rule, input_grid)
        if rule_type == "tile_reflect":
            return self._apply_tile_reflect(rule, input_grid)
        if rule_type == "recolor_by_size":
            return self._apply_recolor_by_size(rule, input_grid)
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

    def _apply_pixel_scaling(self, rule, input_grid):
        raw = input_grid.raw
        scale = rule["scale"]
        output = []
        for row in raw:
            scaled_row = []
            for cell in row:
                scaled_row.extend([cell] * scale)
            for _ in range(scale):
                output.append(scaled_row[:])
        return output

    def _apply_tile_reflect(self, rule, input_grid):
        raw = input_grid.raw
        in_h = len(raw)
        in_w = len(raw[0]) if raw else 0
        tiles_h = rule["tiles_h"]
        tiles_w = rule["tiles_w"]
        tile_map = rule["tile_map"]

        transforms = GeneralizeOperator._tile_transforms()

        output = [[0] * (in_w * tiles_w) for _ in range(in_h * tiles_h)]
        for tr in range(tiles_h):
            for tc in range(tiles_w):
                key = f"{tr}_{tc}"
                transform_name = tile_map.get(key, "identity")
                transformed = transforms[transform_name](raw)
                for r in range(in_h):
                    for c in range(in_w):
                        output[tr * in_h + r][tc * in_w + c] = transformed[r][c]
        return output

    def _apply_recolor_by_size(self, rule, input_grid):
        raw = input_grid.raw
        source_color = rule["source_color"]
        rank_to_color = {int(k): v for k, v in rule["rank_to_color"].items()}

        components = GeneralizeOperator._find_components(raw, source_color)
        if not components:
            return [row[:] for row in raw]

        sizes = sorted(set(len(comp) for comp in components), reverse=True)
        size_to_rank = {s: i for i, s in enumerate(sizes)}

        output = [row[:] for row in raw]
        for comp in components:
            rank = size_to_rank[len(comp)]
            color = rank_to_color.get(rank, source_color)
            for r, c in comp:
                output[r][c] = color
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
