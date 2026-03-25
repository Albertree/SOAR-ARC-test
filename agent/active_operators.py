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

        # Strategy 2: keep only the center column
        if rule is None:
            rule = self._try_center_column_extract(patterns, task)

        # Strategy 3: simple 1:1 color mapping
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

        # Strategy 6: corner quadrant fill (placeholder block + diagonal corner markers)
        if rule is None:
            rule = self._try_corner_quadrant_fill(patterns, task)

        # Strategy 7: fill hollow frames by interior size
        if rule is None:
            rule = self._try_frame_fill_by_size(patterns, task)

        # Strategy 8: staircase growth (1D row -> 2D incremental triangle)
        if rule is None:
            rule = self._try_staircase_growth(patterns, task)

        # Strategy 9: concentric ring color reversal (outside↔inside)
        if rule is None:
            rule = self._try_concentric_ring_reversal(patterns, task)

        # Strategy 10: band section fill (separator rows + axis column)
        if rule is None:
            rule = self._try_band_section_fill(patterns, task)

        # Strategy 11: path waypoint drawing (3=start, 6=right turn, 8=left turn)
        if rule is None:
            rule = self._try_path_waypoint(patterns, task)

        # Strategy 12: diamond bridge (connect aligned cross shapes with 1s)
        if rule is None:
            rule = self._try_diamond_bridge(patterns, task)

        # Strategy 13: mirror separator (9-row divides grid, 2+6 move, 5 mirrors)
        if rule is None:
            rule = self._try_mirror_separator(patterns, task)

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
                if g["input_colors"][0] == 0:
                    return None  # Skip if recoloring background
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
            if ic == 0:
                return None  # Skip if mapping background
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

    @staticmethod
    def _find_solid_blocks(grid, color):
        """Find all solid rectangular blocks of the given color via BFS."""
        h = len(grid)
        w = len(grid[0]) if grid else 0
        visited = set()
        blocks = []

        for r in range(h):
            for c in range(w):
                if grid[r][c] != color or (r, c) in visited:
                    continue
                comp = []
                queue = [(r, c)]
                visited.add((r, c))
                while queue:
                    pr, pc = queue.pop(0)
                    comp.append((pr, pc))
                    for dr, dc in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                        nr, nc = pr + dr, pc + dc
                        if 0 <= nr < h and 0 <= nc < w and (nr, nc) not in visited and grid[nr][nc] == color:
                            visited.add((nr, nc))
                            queue.append((nr, nc))
                min_r = min(p[0] for p in comp)
                max_r = max(p[0] for p in comp)
                min_c = min(p[1] for p in comp)
                max_c = max(p[1] for p in comp)
                bh = max_r - min_r + 1
                bw = max_c - min_c + 1
                if len(comp) == bh * bw:
                    blocks.append({
                        'top_row': min_r, 'top_col': min_c,
                        'height': bh, 'width': bw,
                    })

        return blocks

    @staticmethod
    def _find_frames(grid):
        """Find all hollow rectangular frames (border of one color, interior all 0)."""
        h_grid = len(grid)
        w_grid = len(grid[0]) if grid else 0
        used = set()
        frames = []

        for r in range(h_grid):
            for c in range(w_grid):
                if grid[r][c] == 0 or (r, c) in used:
                    continue
                color = grid[r][c]
                fw = 0
                while c + fw < w_grid and grid[r][c + fw] == color and (r, c + fw) not in used:
                    fw += 1
                if fw < 3:
                    continue
                fh = None
                broken = False
                for rr in range(r + 1, h_grid):
                    is_full = all(grid[rr][c + cc] == color for cc in range(fw))
                    has_edges = (grid[rr][c] == color and grid[rr][c + fw - 1] == color)
                    if is_full:
                        fh = rr - r + 1
                        break
                    elif has_edges:
                        continue
                    else:
                        broken = True
                        break
                if broken or fh is None or fh < 3:
                    continue
                interior_ok = True
                for rr in range(r + 1, r + fh - 1):
                    for cc in range(c + 1, c + fw - 1):
                        if grid[rr][cc] != 0:
                            interior_ok = False
                            break
                    if not interior_ok:
                        break
                if not interior_ok:
                    continue
                for rr in range(r, r + fh):
                    for cc in range(c, c + fw):
                        if rr == r or rr == r + fh - 1 or cc == c or cc == c + fw - 1:
                            used.add((rr, cc))
                frames.append({
                    'color': color,
                    'top_row': r, 'top_col': c,
                    'frame_height': fh, 'frame_width': fw,
                    'inner_row': r + 1, 'inner_col': c + 1,
                    'inner_height': fh - 2, 'inner_width': fw - 2,
                })

        return frames

    # ---- strategy: corner quadrant fill -----------------------------------

    def _try_corner_quadrant_fill(self, patterns, task):
        """
        Detect pattern: rectangular block of a placeholder color with four
        colored corner markers diagonally adjacent. Output replaces the block
        with four quadrants colored by the corresponding corners.
        """
        if not task or not task.example_pairs:
            return None

        placeholder = None

        for pair in task.example_pairs:
            g0, g1 = pair.input_grid, pair.output_grid
            if not g0 or not g1:
                return None
            if g0.height != g1.height or g0.width != g1.width:
                return None

            raw_in = g0.raw
            raw_out = g1.raw
            h, w = g0.height, g0.width

            colors = set()
            for row in raw_in:
                for cell in row:
                    if cell != 0:
                        colors.add(cell)

            found_ph = None
            for color in colors:
                blocks = self._find_solid_blocks(raw_in, color)
                if not blocks:
                    continue
                all_valid = True
                for block in blocks:
                    br, bc = block['top_row'], block['top_col']
                    bh, bw = block['height'], block['width']
                    if bh < 2 or bw < 2 or bh % 2 != 0 or bw % 2 != 0:
                        all_valid = False
                        break
                    corners = [
                        (br - 1, bc - 1), (br - 1, bc + bw),
                        (br + bh, bc - 1), (br + bh, bc + bw),
                    ]
                    corner_colors = []
                    for cr, cc in corners:
                        if cr < 0 or cr >= h or cc < 0 or cc >= w:
                            all_valid = False
                            break
                        cv = raw_in[cr][cc]
                        if cv == 0 or cv == color:
                            all_valid = False
                            break
                        corner_colors.append(cv)
                    if not all_valid:
                        break
                    mid_r = br + bh // 2
                    mid_c = bc + bw // 2
                    quads = [
                        (br, bc, mid_r, mid_c),
                        (br, mid_c, mid_r, bc + bw),
                        (mid_r, bc, br + bh, mid_c),
                        (mid_r, mid_c, br + bh, bc + bw),
                    ]
                    for qi, (qr1, qc1, qr2, qc2) in enumerate(quads):
                        for rr in range(qr1, qr2):
                            for cc in range(qc1, qc2):
                                if raw_out[rr][cc] != corner_colors[qi]:
                                    all_valid = False
                                    break
                            if not all_valid:
                                break
                        if not all_valid:
                            break
                    if not all_valid:
                        break
                    for cr, cc in corners:
                        if raw_out[cr][cc] != 0:
                            all_valid = False
                            break
                    if not all_valid:
                        break
                if all_valid and blocks:
                    found_ph = color
                    break
            if found_ph is None:
                return None
            if placeholder is None:
                placeholder = found_ph
            elif placeholder != found_ph:
                return None

        return {
            'type': 'corner_quadrant_fill',
            'placeholder': placeholder,
            'confidence': 1.0,
        }

    # ---- strategy: frame fill by interior size ----------------------------

    def _try_frame_fill_by_size(self, patterns, task):
        """
        Detect pattern: hollow rectangular frames of a single color with 0-interiors.
        Each frame's interior is filled with a color based on interior side length.
        """
        if not task or not task.example_pairs:
            return None

        frame_color = None
        size_to_color = {}

        for pair in task.example_pairs:
            g0, g1 = pair.input_grid, pair.output_grid
            if not g0 or not g1:
                return None
            if g0.height != g1.height or g0.width != g1.width:
                return None

            raw_in = g0.raw
            raw_out = g1.raw
            frames = self._find_frames(raw_in)
            if not frames:
                return None

            for frame in frames:
                fc = frame['color']
                if frame_color is None:
                    frame_color = fc
                elif frame_color != fc:
                    return None
                ih, iw = frame['inner_height'], frame['inner_width']
                if ih != iw:
                    return None
                ir, ic = frame['inner_row'], frame['inner_col']
                fill = raw_out[ir][ic]
                if fill == 0:
                    return None
                ok = True
                for rr in range(ir, ir + ih):
                    for cc in range(ic, ic + iw):
                        if raw_out[rr][cc] != fill:
                            ok = False
                            break
                    if not ok:
                        break
                if not ok:
                    return None
                if ih in size_to_color:
                    if size_to_color[ih] != fill:
                        return None
                else:
                    size_to_color[ih] = fill

        if not size_to_color:
            return None

        formula = all(size_to_color[s] == frame_color + s for s in size_to_color)

        return {
            'type': 'frame_fill_by_size',
            'frame_color': frame_color,
            'size_to_color': size_to_color,
            'additive_formula': formula,
            'confidence': 1.0,
        }

    # ---- strategy: staircase growth --------------------------------------

    def _try_staircase_growth(self, patterns, task):
        """
        Detect pattern: input is a single row with C colored cells on the left.
        Output grows to (W//2) rows, each row i has (C+i) colored cells.
        """
        if not task or not task.example_pairs:
            return None

        for pair in task.example_pairs:
            g0, g1 = pair.input_grid, pair.output_grid
            if not g0 or not g1:
                return None

            raw_in = g0.raw
            raw_out = g1.raw

            if g0.height != 1:
                return None

            w = g0.width
            row = raw_in[0]
            c_count = 0
            c_color = None
            for v in row:
                if v != 0:
                    if c_color is None:
                        c_color = v
                    elif v != c_color:
                        return None
                    c_count += 1
                else:
                    break
            if c_count == 0 or c_color is None:
                return None
            if any(v != 0 for v in row[c_count:]):
                return None

            expected_rows = w // 2
            if g1.height != expected_rows or g1.width != w:
                return None

            for i in range(expected_rows):
                count = c_count + i
                for j in range(w):
                    if j < count:
                        if raw_out[i][j] != c_color:
                            return None
                    else:
                        if raw_out[i][j] != 0:
                            return None

        return {'type': 'staircase_growth', 'confidence': 1.0}

    # ---- strategy: center column extraction --------------------------------

    def _try_center_column_extract(self, patterns, task):
        """
        Detect pattern: output keeps only the center column (index W//2)
        of the input grid and zeros everything else. Generalizes to any
        task that filters to a single axis line.
        """
        if not task or not task.example_pairs:
            return None
        if not patterns.get("grid_size_preserved"):
            return None

        for pair in task.example_pairs:
            g0, g1 = pair.input_grid, pair.output_grid
            if not g0 or not g1:
                return None
            if g0.height != g1.height or g0.width != g1.width:
                return None

            raw_in = g0.raw
            raw_out = g1.raw
            h, w = g0.height, g0.width
            if w < 3:
                return None
            center = w // 2

            for r in range(h):
                for c in range(w):
                    if c == center:
                        if raw_out[r][c] != raw_in[r][c]:
                            return None
                    else:
                        if raw_out[r][c] != 0:
                            return None

        return {'type': 'center_column_extract', 'confidence': 1.0}

    # ---- strategy: concentric ring reversal --------------------------------

    def _try_concentric_ring_reversal(self, patterns, task):
        """
        Detect pattern: grid consists of concentric rectangular rings of
        uniform colors. Output reverses the ring color order (outside↔inside).
        """
        if not task or not task.example_pairs:
            return None
        if not patterns.get("grid_size_preserved"):
            return None

        for pair in task.example_pairs:
            g0, g1 = pair.input_grid, pair.output_grid
            if not g0 or not g1:
                return None
            if g0.height != g1.height or g0.width != g1.width:
                return None

            in_layers = self._peel_concentric_layers(g0.raw)
            out_layers = self._peel_concentric_layers(g1.raw)

            if in_layers is None or out_layers is None:
                return None
            if len(in_layers) < 2:
                return None
            if in_layers != list(reversed(out_layers)):
                return None

        return {'type': 'concentric_ring_reversal', 'confidence': 1.0}

    @staticmethod
    def _peel_concentric_layers(grid):
        """Extract concentric ring colors from outside in."""
        h = len(grid)
        w = len(grid[0]) if grid else 0
        if h == 0 or w == 0:
            return None

        layers = []
        top, bottom, left, right = 0, h - 1, 0, w - 1

        while top <= bottom and left <= right:
            color = grid[top][left]
            for c in range(left, right + 1):
                if grid[top][c] != color:
                    return None
                if top != bottom and grid[bottom][c] != color:
                    return None
            for r in range(top + 1, bottom):
                if grid[r][left] != color:
                    return None
                if left != right and grid[r][right] != color:
                    return None
            layers.append(color)
            top += 1
            bottom -= 1
            left += 1
            right -= 1

        return layers

    # ---- strategy: band section fill ---------------------------------------

    def _try_band_section_fill(self, patterns, task):
        """
        Detect pattern: grid with a vertical axis column (one color) and
        horizontal colored separator rows. Background is uniform. Output
        fills sections between separators with the separator colors and
        turns separators into border rows.
        """
        if not task or not task.example_pairs:
            return None
        if not patterns.get("grid_size_preserved"):
            return None

        axis_col = None
        axis_color = None
        intersect_color = None

        for pair in task.example_pairs:
            g0, g1 = pair.input_grid, pair.output_grid
            if not g0 or not g1:
                return None
            if g0.height != g1.height or g0.width != g1.width:
                return None

            raw_in = g0.raw
            raw_out = g1.raw
            h, w = g0.height, g0.width

            found = False
            for col in range(w):
                col_vals = [raw_in[r][col] for r in range(h)]
                unique = set(col_vals)
                if len(unique) != 2:
                    continue

                counts = {v: col_vals.count(v) for v in unique}
                ax_c = max(counts, key=counts.get)
                int_c = min(counts, key=counts.get)

                sep_rows = [r for r in range(h) if raw_in[r][col] == int_c]
                if len(sep_rows) < 2:
                    continue

                seps_valid = True
                sep_colors = []
                for sr in sep_rows:
                    row_vals = set()
                    for c in range(w):
                        if c != col:
                            row_vals.add(raw_in[sr][c])
                    if len(row_vals) != 1:
                        seps_valid = False
                        break
                    sep_colors.append(list(row_vals)[0])
                if not seps_valid:
                    continue

                bg_color = None
                bg_valid = True
                sep_set = set(sep_rows)
                for r in range(h):
                    if r in sep_set:
                        continue
                    for c in range(w):
                        if c == col:
                            if raw_in[r][c] != ax_c:
                                bg_valid = False
                                break
                        else:
                            if bg_color is None:
                                bg_color = raw_in[r][c]
                            elif raw_in[r][c] != bg_color:
                                bg_valid = False
                                break
                    if not bg_valid:
                        break
                if not bg_valid or bg_color is None:
                    continue

                expected = self._compute_band_fill(
                    h, w, col, ax_c, int_c, sep_rows, sep_colors)
                if expected == raw_out:
                    if axis_color is None:
                        axis_color = ax_c
                        intersect_color = int_c
                    elif axis_color != ax_c or intersect_color != int_c:
                        return None
                    found = True
                    break

            if not found:
                return None

        return {
            'type': 'band_section_fill',
            'axis_color': axis_color,
            'intersect_color': intersect_color,
            'confidence': 1.0,
        }

    # ---- strategy: path waypoint drawing ------------------------------------

    def _try_path_waypoint(self, patterns, task):
        """
        Detect pattern: grid has a start marker (color A), and waypoint markers
        (one or two other colors B and C). A path of color A is drawn from start
        going right initially, turning right-relative at B markers and
        left-relative at C markers, until grid edge after last waypoint.
        Some pairs may only use one waypoint color.
        """
        if not task or not task.example_pairs:
            return None
        if not patterns.get("grid_size_preserved"):
            return None

        # First pass: identify start color and collect all waypoint colors
        start_color = None
        all_wp_colors = set()

        for pair in task.example_pairs:
            g0, g1 = pair.input_grid, pair.output_grid
            if not g0 or not g1:
                return None
            if g0.height != g1.height or g0.width != g1.width:
                return None

            raw_in = g0.raw
            raw_out = g1.raw
            h, w = g0.height, g0.width

            in_colors = {}
            for r in range(h):
                for c in range(w):
                    v = raw_in[r][c]
                    if v != 0:
                        if v not in in_colors:
                            in_colors[v] = []
                        in_colors[v].append((r, c))

            if len(in_colors) < 2:
                return None

            candidates = []
            for color, positions in in_colors.items():
                out_count = sum(1 for r in range(h) for c in range(w)
                                if raw_out[r][c] == color)
                if len(positions) == 1 and out_count > 1:
                    candidates.append(color)

            if len(candidates) != 1:
                return None

            sc = candidates[0]
            if start_color is None:
                start_color = sc
            elif start_color != sc:
                return None

            for c in in_colors:
                if c != start_color:
                    all_wp_colors.add(c)

        if start_color is None or len(all_wp_colors) != 2:
            return None

        wp_list = sorted(all_wp_colors)

        # Second pass: try both turn assignments, validate all pairs
        right_turn_color = None
        left_turn_color = None

        for assign in [(wp_list[0], wp_list[1]),
                       (wp_list[1], wp_list[0])]:
            rt, lt = assign
            all_match = True
            for pair in task.example_pairs:
                g0, g1 = pair.input_grid, pair.output_grid
                raw_in = g0.raw
                raw_out = g1.raw
                h, w = g0.height, g0.width

                start_pos = None
                waypoints = {}
                for r in range(h):
                    for c in range(w):
                        v = raw_in[r][c]
                        if v == start_color:
                            start_pos = (r, c)
                        elif v in all_wp_colors:
                            waypoints[(r, c)] = v

                if start_pos is None:
                    all_match = False
                    break

                simulated = self._simulate_path(
                    raw_in, h, w, start_pos, start_color, rt, lt, waypoints)
                if simulated != raw_out:
                    all_match = False
                    break

            if all_match:
                right_turn_color = rt
                left_turn_color = lt
                break

        if right_turn_color is None:
            return None

        return {
            'type': 'path_waypoint',
            'start_color': start_color,
            'right_turn_color': right_turn_color,
            'left_turn_color': left_turn_color,
            'confidence': 1.0,
        }

    @staticmethod
    def _simulate_path(raw_in, h, w, start_pos, path_color,
                       right_turn_color, left_turn_color, waypoints):
        """Simulate path drawing and return expected output grid."""
        output = [row[:] for row in raw_in]
        sr, sc = start_pos
        # Initial direction: right
        dr, dc = 0, 1

        # Relative turn mappings
        def turn_right(dr, dc):
            return dc, -dr

        def turn_left(dr, dc):
            return -dc, dr

        r, c = sr, sc
        output[r][c] = path_color

        max_steps = h * w * 2
        steps = 0
        while steps < max_steps:
            steps += 1
            nr, nc = r + dr, c + dc
            if nr < 0 or nr >= h or nc < 0 or nc >= w:
                break
            if (nr, nc) in waypoints:
                wp_color = waypoints[(nr, nc)]
                # Don't overwrite waypoint cell; turn based on its color
                if wp_color == right_turn_color:
                    dr, dc = turn_right(dr, dc)
                elif wp_color == left_turn_color:
                    dr, dc = turn_left(dr, dc)
                # Continue from current position in new direction
                continue
            output[nr][nc] = path_color
            r, c = nr, nc

        return output

    # ---- strategy: diamond bridge ------------------------------------------

    def _try_diamond_bridge(self, patterns, task):
        """
        Detect pattern: cross/diamond shapes (4 cells in a plus pattern)
        of one color. When two diamonds' tips align horizontally or vertically,
        the gap between them is filled with a bridge color (e.g. 1).
        """
        if not task or not task.example_pairs:
            return None
        if not patterns.get("grid_size_preserved"):
            return None

        diamond_color = None
        bridge_color = None

        for pair in task.example_pairs:
            g0, g1 = pair.input_grid, pair.output_grid
            if not g0 or not g1:
                return None
            if g0.height != g1.height or g0.width != g1.width:
                return None

            raw_in = g0.raw
            raw_out = g1.raw
            h, w = g0.height, g0.width

            # Find diamonds (cross/plus shapes)
            diamonds = self._find_diamonds(raw_in, h, w)
            if not diamonds:
                return None

            dc = diamonds[0]['color']
            if diamond_color is None:
                diamond_color = dc
            elif diamond_color != dc:
                return None

            # Find bridge color: new color in output not in input
            new_cells = []
            for r in range(h):
                for c in range(w):
                    if raw_out[r][c] != raw_in[r][c] and raw_out[r][c] != 0:
                        new_cells.append((r, c, raw_out[r][c]))

            if not new_cells:
                return None

            bc = new_cells[0][2]
            if not all(nc[2] == bc for nc in new_cells):
                return None

            if bridge_color is None:
                bridge_color = bc
            elif bridge_color != bc:
                return None

            # Verify: simulate bridging and compare
            simulated = self._simulate_diamond_bridge(
                raw_in, h, w, diamonds, bridge_color)
            if simulated != raw_out:
                return None

        if diamond_color is None or bridge_color is None:
            return None

        return {
            'type': 'diamond_bridge',
            'diamond_color': diamond_color,
            'bridge_color': bridge_color,
            'confidence': 1.0,
        }

    @staticmethod
    def _find_diamonds(grid, h, w):
        """Find cross/plus shapes: center cell with 4 orthogonal neighbors
        of the same non-zero color, center cell is background (0)."""
        diamonds = []
        visited_centers = set()
        for r in range(1, h - 1):
            for c in range(1, w - 1):
                if grid[r][c] != 0 or (r, c) in visited_centers:
                    continue
                top = grid[r - 1][c]
                bot = grid[r + 1][c]
                left = grid[r][c - 1]
                right = grid[r][c + 1]
                if top != 0 and top == bot == left == right:
                    visited_centers.add((r, c))
                    diamonds.append({
                        'center': (r, c),
                        'color': top,
                        'top': (r - 1, c),
                        'bottom': (r + 1, c),
                        'left': (r, c - 1),
                        'right': (r, c + 1),
                    })
        return diamonds

    @staticmethod
    def _simulate_diamond_bridge(raw_in, h, w, diamonds, bridge_color):
        """Connect aligned diamond tips with bridge lines.
        Only bridges tips with a clear path (all gap cells are 0)."""
        output = [row[:] for row in raw_in]

        def _gap_clear_h(row, c_start, c_end):
            """Check all cells in horizontal gap are background (0)."""
            for c in range(c_start, c_end + 1):
                if raw_in[row][c] != 0:
                    return False
            return True

        def _gap_clear_v(col, r_start, r_end):
            """Check all cells in vertical gap are background (0)."""
            for r in range(r_start, r_end + 1):
                if raw_in[r][col] != 0:
                    return False
            return True

        for i in range(len(diamonds)):
            for j in range(i + 1, len(diamonds)):
                d1 = diamonds[i]
                d2 = diamonds[j]

                # Horizontal: d1 right -> d2 left
                if d1['right'][0] == d2['left'][0]:
                    row = d1['right'][0]
                    c1, c2 = d1['right'][1], d2['left'][1]
                    if c1 < c2:
                        gs, ge = c1 + 1, c2 - 1
                        if gs <= ge and _gap_clear_h(row, gs, ge):
                            for c in range(gs, ge + 1):
                                output[row][c] = bridge_color

                # Horizontal: d2 right -> d1 left
                if d2['right'][0] == d1['left'][0]:
                    row = d2['right'][0]
                    c1, c2 = d2['right'][1], d1['left'][1]
                    if c1 < c2:
                        gs, ge = c1 + 1, c2 - 1
                        if gs <= ge and _gap_clear_h(row, gs, ge):
                            for c in range(gs, ge + 1):
                                output[row][c] = bridge_color

                # Vertical: d1 bottom -> d2 top
                if d1['bottom'][1] == d2['top'][1]:
                    col = d1['bottom'][1]
                    r1, r2 = d1['bottom'][0], d2['top'][0]
                    if r1 < r2:
                        gs, ge = r1 + 1, r2 - 1
                        if gs <= ge and _gap_clear_v(col, gs, ge):
                            for r in range(gs, ge + 1):
                                output[r][col] = bridge_color

                # Vertical: d2 bottom -> d1 top
                if d2['bottom'][1] == d1['top'][1]:
                    col = d2['bottom'][1]
                    r1, r2 = d2['bottom'][0], d1['top'][0]
                    if r1 < r2:
                        gs, ge = r1 + 1, r2 - 1
                        if gs <= ge and _gap_clear_v(col, gs, ge):
                            for r in range(gs, ge + 1):
                                output[r][col] = bridge_color

        return output

    # ---- strategy: mirror separator ----------------------------------------

    def _try_mirror_separator(self, patterns, task):
        """
        Detect pattern: a row of 9s separates the grid into top and bottom
        halves. Bottom half has 'object' pixels and 'arrow' pixels. Each object
        pixel is adjacent to one arrow pixel defining its movement direction.
        Top half has mirror pixels at reflected positions that move in the
        vertically-mirrored direction.
        """
        if not task or not task.example_pairs:
            return None
        if not patterns.get("grid_size_preserved"):
            return None

        sep_color = None
        obj_color = None
        arrow_color = None
        mirror_color = None
        bg_color = None

        for pair in task.example_pairs:
            g0, g1 = pair.input_grid, pair.output_grid
            if not g0 or not g1:
                return None
            if g0.height != g1.height or g0.width != g1.width:
                return None

            raw_in = g0.raw
            raw_out = g1.raw
            h, w = g0.height, g0.width

            # Find background color (most common in the grid)
            color_freq = {}
            for r in range(h):
                for c in range(w):
                    v = raw_in[r][c]
                    color_freq[v] = color_freq.get(v, 0) + 1
            bg = max(color_freq, key=color_freq.get)

            # Find separator row: uniform non-background color
            sep_row = None
            for r in range(h):
                row = raw_in[r]
                vals = set(row)
                if len(vals) == 1 and row[0] != bg:
                    if sep_row is None:
                        sep_row = r
                        sc = row[0]
                    else:
                        return None  # Multiple separator rows
            if sep_row is None:
                return None

            if sep_color is None:
                sep_color = sc
            elif sep_color != sc:
                return None

            # bg already computed above from color_freq

            if bg_color is None:
                bg_color = bg
            elif bg_color != bg:
                return None

            # Identify colors in bottom and top halves
            bottom_colors = set()
            top_colors = set()
            for r in range(sep_row + 1, h):
                for c in range(w):
                    v = raw_in[r][c]
                    if v != bg:
                        bottom_colors.add(v)
            for r in range(sep_row):
                for c in range(w):
                    v = raw_in[r][c]
                    if v != bg:
                        top_colors.add(v)

            if len(bottom_colors) != 2 or len(top_colors) != 1:
                return None

            mc = list(top_colors)[0]

            # Determine which bottom color is object, which is arrow
            # by checking: in output, arrows disappear, objects move
            for assign in list(bottom_colors):
                other = [c for c in bottom_colors if c != assign][0]
                oc, ac = assign, other
                # Verify: simulate and compare
                result = self._simulate_mirror_sep(
                    raw_in, raw_out, h, w, sep_row, bg, oc, ac, mc)
                if result is not None:
                    if obj_color is None:
                        obj_color = oc
                        arrow_color = ac
                        mirror_color = mc
                    elif obj_color != oc or arrow_color != ac:
                        return None
                    break
            else:
                return None

        if obj_color is None:
            return None

        return {
            'type': 'mirror_separator',
            'sep_color': sep_color,
            'bg_color': bg_color,
            'obj_color': obj_color,
            'arrow_color': arrow_color,
            'mirror_color': mirror_color,
            'confidence': 1.0,
        }

    @staticmethod
    def _simulate_mirror_sep(raw_in, raw_out, h, w, sep_row, bg,
                             obj_color, arrow_color, mirror_color):
        """Simulate mirror-separator transformation. Returns output if valid."""
        output = [[bg] * w for _ in range(h)]
        # Copy separator row
        for c in range(w):
            output[sep_row][c] = raw_in[sep_row][c]

        # Bottom half: find each obj pixel and its adjacent arrow
        obj_positions = []
        arrow_positions = []
        for r in range(sep_row + 1, h):
            for c in range(w):
                if raw_in[r][c] == obj_color:
                    obj_positions.append((r, c))
                elif raw_in[r][c] == arrow_color:
                    arrow_positions.append((r, c))

        arrow_set = set(arrow_positions)
        movements = []

        for (or_, oc_) in obj_positions:
            # Find adjacent arrow
            adj_arrow = None
            for dr, dc in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                nr, nc = or_ + dr, oc_ + dc
                if (nr, nc) in arrow_set:
                    adj_arrow = (nr, nc, dr, dc)
                    break
            if adj_arrow is None:
                return None

            ar, ac, dr, dc = adj_arrow
            # Follow chain of arrows in that direction
            final_r, final_c = ar, ac
            while True:
                next_r = final_r + dr
                next_c = final_c + dc
                if (next_r, next_c) in arrow_set:
                    final_r, final_c = next_r, next_c
                else:
                    break

            move_dr = final_r - or_
            move_dc = final_c - oc_
            movements.append((or_, oc_, final_r, final_c, move_dr, move_dc))

        # Place objects at new positions in bottom half
        for (_, _, fr, fc, _, _) in movements:
            output[fr][fc] = obj_color

        # Top half: mirror each movement
        for (or_, oc_, _, _, move_dr, move_dc) in movements:
            # Mirror position of object
            dist = or_ - sep_row
            mirror_r = sep_row - dist
            mirror_c = oc_
            # Mirror movement: negate vertical, keep horizontal
            new_r = mirror_r - move_dr
            new_c = mirror_c + move_dc
            if 0 <= new_r < h and 0 <= new_c < w:
                output[new_r][new_c] = mirror_color

        if output == raw_out:
            return output
        return None

    @staticmethod
    def _compute_band_fill(h, w, axis_col, axis_color, intersect_color,
                           sep_rows, sep_colors):
        """Compute the expected band fill output grid."""
        output = [[0] * w for _ in range(h)]

        sections = []

        if sep_rows[0] > 0:
            sections.append((0, sep_rows[0] - 1, sep_colors[0]))

        for i in range(len(sep_rows) - 1):
            gap_start = sep_rows[i] + 1
            gap_end = sep_rows[i + 1] - 1
            if gap_start > gap_end:
                continue
            upper_color = sep_colors[i]
            lower_color = sep_colors[i + 1]
            gap_size = gap_end - gap_start + 1

            if upper_color == lower_color:
                sections.append((gap_start, gap_end, upper_color))
            else:
                half = gap_size // 2
                if gap_size % 2 == 0:
                    sections.append((gap_start, gap_start + half - 1,
                                     upper_color))
                    sections.append((gap_start + half, gap_end, lower_color))
                else:
                    sections.append((gap_start, gap_start + half - 1,
                                     upper_color))
                    sections.append((gap_start + half, gap_start + half,
                                     'mid_separator'))
                    sections.append((gap_start + half + 1, gap_end,
                                     lower_color))

        if sep_rows[-1] < h - 1:
            sections.append((sep_rows[-1] + 1, h - 1, sep_colors[-1]))

        for sr in sep_rows:
            for c in range(w):
                output[sr][c] = intersect_color if c != axis_col else axis_color

        for start, end, color in sections:
            if color == 'mid_separator':
                for c in range(w):
                    output[start][c] = intersect_color
            else:
                for r in range(start, end + 1):
                    for c in range(w):
                        output[r][c] = (color if c != axis_col
                                        else intersect_color)

        return output


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
        if rule_type == "corner_quadrant_fill":
            return self._apply_corner_quadrant_fill(rule, input_grid)
        if rule_type == "frame_fill_by_size":
            return self._apply_frame_fill_by_size(rule, input_grid)
        if rule_type == "staircase_growth":
            return self._apply_staircase_growth(rule, input_grid)
        if rule_type == "center_column_extract":
            return self._apply_center_column_extract(rule, input_grid)
        if rule_type == "concentric_ring_reversal":
            return self._apply_concentric_ring_reversal(rule, input_grid)
        if rule_type == "band_section_fill":
            return self._apply_band_section_fill(rule, input_grid)
        if rule_type == "path_waypoint":
            return self._apply_path_waypoint(rule, input_grid)
        if rule_type == "diamond_bridge":
            return self._apply_diamond_bridge(rule, input_grid)
        if rule_type == "mirror_separator":
            return self._apply_mirror_separator(rule, input_grid)
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

    def _apply_corner_quadrant_fill(self, rule, input_grid):
        raw = input_grid.raw
        h = len(raw)
        w = len(raw[0]) if raw else 0
        placeholder = rule['placeholder']

        blocks = GeneralizeOperator._find_solid_blocks(raw, placeholder)
        output = [row[:] for row in raw]

        for block in blocks:
            br, bc = block['top_row'], block['top_col']
            bh, bw = block['height'], block['width']
            corners = [
                (br - 1, bc - 1), (br - 1, bc + bw),
                (br + bh, bc - 1), (br + bh, bc + bw),
            ]
            corner_colors = []
            valid = True
            for cr, cc in corners:
                if cr < 0 or cr >= h or cc < 0 or cc >= w:
                    valid = False
                    break
                cv = raw[cr][cc]
                if cv == 0 or cv == placeholder:
                    valid = False
                    break
                corner_colors.append(cv)
            if not valid:
                continue
            mid_r = br + bh // 2
            mid_c = bc + bw // 2
            for r in range(br, mid_r):
                for c in range(bc, mid_c):
                    output[r][c] = corner_colors[0]
            for r in range(br, mid_r):
                for c in range(mid_c, bc + bw):
                    output[r][c] = corner_colors[1]
            for r in range(mid_r, br + bh):
                for c in range(bc, mid_c):
                    output[r][c] = corner_colors[2]
            for r in range(mid_r, br + bh):
                for c in range(mid_c, bc + bw):
                    output[r][c] = corner_colors[3]
            for cr, cc in corners:
                output[cr][cc] = 0
        return output

    def _apply_frame_fill_by_size(self, rule, input_grid):
        raw = input_grid.raw
        frame_color = rule['frame_color']
        size_to_color = {int(k): v for k, v in rule['size_to_color'].items()}
        additive = rule.get('additive_formula', False)

        frames = GeneralizeOperator._find_frames(raw)
        output = [row[:] for row in raw]

        for frame in frames:
            if frame['color'] != frame_color:
                continue
            ih = frame['inner_height']
            if ih in size_to_color:
                fill = size_to_color[ih]
            elif additive:
                fill = frame_color + ih
            else:
                continue
            ir, ic = frame['inner_row'], frame['inner_col']
            iw = frame['inner_width']
            for r in range(ir, ir + ih):
                for c in range(ic, ic + iw):
                    output[r][c] = fill
        return output

    def _apply_staircase_growth(self, rule, input_grid):
        raw = input_grid.raw
        if len(raw) != 1:
            return [row[:] for row in raw]

        w = len(raw[0])
        row = raw[0]
        c_count = 0
        c_color = 0
        for v in row:
            if v != 0:
                c_color = v
                c_count += 1
            else:
                break
        if c_count == 0:
            return [row[:]]

        num_rows = w // 2
        output = []
        for i in range(num_rows):
            count = c_count + i
            output.append([c_color if j < count else 0 for j in range(w)])
        return output

    def _apply_center_column_extract(self, rule, input_grid):
        raw = input_grid.raw
        h = len(raw)
        w = len(raw[0]) if raw else 0
        center = w // 2
        output = [[0] * w for _ in range(h)]
        for r in range(h):
            output[r][center] = raw[r][center]
        return output

    def _apply_concentric_ring_reversal(self, rule, input_grid):
        raw = input_grid.raw
        h = len(raw)
        w = len(raw[0]) if raw else 0

        layers = GeneralizeOperator._peel_concentric_layers(raw)
        if layers is None:
            return [row[:] for row in raw]

        reversed_layers = list(reversed(layers))
        output = [[0] * w for _ in range(h)]
        top, bottom, left, right = 0, h - 1, 0, w - 1
        idx = 0

        while top <= bottom and left <= right:
            color = reversed_layers[idx]
            for r in range(top, bottom + 1):
                for c in range(left, right + 1):
                    if r == top or r == bottom or c == left or c == right:
                        output[r][c] = color
            top += 1
            bottom -= 1
            left += 1
            right -= 1
            idx += 1

        return output

    def _apply_band_section_fill(self, rule, input_grid):
        raw = input_grid.raw
        h = len(raw)
        w = len(raw[0]) if raw else 0
        axis_color = rule['axis_color']
        intersect_color = rule['intersect_color']

        # Find axis column in this input
        axis_col = None
        for col in range(w):
            col_vals = [raw[r][col] for r in range(h)]
            unique = set(col_vals)
            if unique == {axis_color, intersect_color}:
                axis_col = col
                break
        if axis_col is None:
            return [row[:] for row in raw]

        sep_rows = []
        sep_colors = []
        for r in range(h):
            if raw[r][axis_col] == intersect_color:
                sep_rows.append(r)
                row_vals = set()
                for c in range(w):
                    if c != axis_col:
                        row_vals.add(raw[r][c])
                if len(row_vals) == 1:
                    sep_colors.append(list(row_vals)[0])
                else:
                    return [row[:] for row in raw]

        if len(sep_rows) < 2:
            return [row[:] for row in raw]

        return GeneralizeOperator._compute_band_fill(
            h, w, axis_col, axis_color, intersect_color, sep_rows, sep_colors)

    def _apply_path_waypoint(self, rule, input_grid):
        raw = input_grid.raw
        h = len(raw)
        w = len(raw[0]) if raw else 0
        start_color = rule['start_color']
        right_turn_color = rule['right_turn_color']
        left_turn_color = rule['left_turn_color']

        # Find start position
        start_pos = None
        waypoints = {}
        for r in range(h):
            for c in range(w):
                v = raw[r][c]
                if v == start_color:
                    start_pos = (r, c)
                elif v in (right_turn_color, left_turn_color):
                    waypoints[(r, c)] = v

        if start_pos is None:
            return [row[:] for row in raw]

        return GeneralizeOperator._simulate_path(
            raw, h, w, start_pos, start_color,
            right_turn_color, left_turn_color, waypoints)

    def _apply_diamond_bridge(self, rule, input_grid):
        raw = input_grid.raw
        h = len(raw)
        w = len(raw[0]) if raw else 0
        bridge_color = rule['bridge_color']

        diamonds = GeneralizeOperator._find_diamonds(raw, h, w)
        return GeneralizeOperator._simulate_diamond_bridge(
            raw, h, w, diamonds, bridge_color)

    def _apply_mirror_separator(self, rule, input_grid):
        raw = input_grid.raw
        h = len(raw)
        w = len(raw[0]) if raw else 0
        sep_color = rule['sep_color']
        bg = rule['bg_color']
        obj_color = rule['obj_color']
        arrow_color = rule['arrow_color']
        mirror_color = rule['mirror_color']

        # Find separator row
        sep_row = None
        for r in range(h):
            if all(raw[r][c] == sep_color for c in range(w)):
                sep_row = r
                break
        if sep_row is None:
            return [row[:] for row in raw]

        output = [[bg] * w for _ in range(h)]
        for c in range(w):
            output[sep_row][c] = sep_color

        # Bottom half: find objects and arrows
        obj_positions = []
        arrow_set = set()
        for r in range(sep_row + 1, h):
            for c in range(w):
                if raw[r][c] == obj_color:
                    obj_positions.append((r, c))
                elif raw[r][c] == arrow_color:
                    arrow_set.add((r, c))

        for (or_, oc_) in obj_positions:
            # Find adjacent arrow
            adj_arrow = None
            for dr, dc in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                nr, nc = or_ + dr, oc_ + dc
                if (nr, nc) in arrow_set:
                    adj_arrow = (nr, nc, dr, dc)
                    break
            if adj_arrow is None:
                output[or_][oc_] = obj_color
                continue

            ar, ac, dr, dc = adj_arrow
            final_r, final_c = ar, ac
            while True:
                next_r = final_r + dr
                next_c = final_c + dc
                if (next_r, next_c) in arrow_set:
                    final_r, final_c = next_r, next_c
                else:
                    break

            move_dr = final_r - or_
            move_dc = final_c - oc_
            output[final_r][final_c] = obj_color

            # Mirror in top half
            dist = or_ - sep_row
            mirror_r = sep_row - dist
            new_r = mirror_r - move_dr
            new_c = oc_ + move_dc
            if 0 <= new_r < h and 0 <= new_c < w:
                output[new_r][new_c] = mirror_color

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
