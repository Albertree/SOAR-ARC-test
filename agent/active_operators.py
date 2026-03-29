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
from ARCKG.comparison import compare as arckg_compare


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

        # Strategy: vertical mirror append (output = input + flipped input)
        rule = self._try_vertical_mirror_append(patterns, task)

        # Strategy: fill outlined rectangles by interior area
        if rule is None:
            rule = self._try_fill_rectangles_by_size(patterns, task)

        # Strategy: reverse concentric rings
        if rule is None:
            rule = self._try_reverse_rings(patterns, task)

        # Strategy: pixel scale-up (each pixel becomes NxN block)
        if rule is None:
            rule = self._try_pixel_scale(patterns, task)

        # Strategy: recolor components by size (largest=1, next=2, ...)
        if rule is None:
            rule = self._try_recolor_by_size(patterns, task)

        # Strategy: L-path chain (source + directional waypoints)
        if rule is None:
            rule = self._try_lpath_chain(patterns, task)

        # Strategy: arrow chain mirror (separator row + arrow chains)
        if rule is None:
            rule = self._try_arrow_chain_mirror(patterns, task)

        # Strategy: sequential recoloring (e.g., color objects 1, 2, 3, ...)
        if rule is None:
            rule = self._try_recolor_sequential(patterns)

        # Strategy: keep only center column (before color_mapping — more specific)
        if rule is None:
            rule = self._try_keep_center_column(patterns, task)

        # Strategy: staircase growth (1-row input → growing triangle)
        if rule is None:
            rule = self._try_staircase_growth(patterns, task)

        # Strategy: corner-fill quadrants (rectangle + 4 corner markers)
        if rule is None:
            rule = self._try_corner_fill_quadrants(patterns, task)

        # Strategy: gravity slide (objects drop toward wall with 1-cell gap)
        if rule is None:
            rule = self._try_gravity_slide(patterns, task)

        # Strategy: diamond bridge (connect aligned diamond shapes with lines)
        if rule is None:
            rule = self._try_diamond_bridge(patterns, task)

        # Strategy: stripe zone fill (spine + colored stripes → zone filling)
        if rule is None:
            rule = self._try_stripe_zone_fill(patterns, task)

        # Strategy: cross projection to edges (crosses with missing arm)
        if rule is None:
            rule = self._try_cross_projection(patterns, task)

        # Strategy: quadrant shape swap (grid divided by 0-lines)
        if rule is None:
            rule = self._try_quadrant_shape_swap(patterns, task)

        # Strategy: grid zigzag shear (rectangle/grid rows shift ±1 in period-4 wave)
        if rule is None:
            rule = self._try_grid_zigzag_shear(patterns, task)

        # Strategy: three-shape rearrange (connector moves into split block)
        if rule is None:
            rule = self._try_three_shape_rearrange(patterns, task)

        # Strategy: template reconstruct (shapes rebuilt at marker positions with D4 symmetry)
        if rule is None:
            rule = self._try_template_reconstruct(patterns, task)

        # Strategy: block grid gravity (30x30 block grid compressed with directional gravity)
        if rule is None:
            rule = self._try_block_grid_gravity(patterns, task)

        # Strategy: scatter count X-diamond (count two scatter colors → W×H X pattern)
        if rule is None:
            rule = self._try_scatter_count_x(patterns, task)

        # Strategy: rotation tiling (NxN → 2Nx2N with 4 rotations)
        if rule is None:
            rule = self._try_rotation_tiling(patterns, task)

        # Strategy: rectangle interior count (count colored pixels inside 1-rectangle → filled grid)
        if rule is None:
            rule = self._try_rectangle_interior_count(patterns, task)

        # Strategy: pattern tile fill (fill uniform-bg rows with cyclic pattern repeat)
        if rule is None:
            rule = self._try_pattern_tile_fill(patterns, task)

        # Strategy: nearest corner lines (pixel → L-line to nearest corner)
        if rule is None:
            rule = self._try_nearest_corner_lines(patterns, task)

        # Strategy: frame inversion (nested rectangle border↔interior swap)
        if rule is None:
            rule = self._try_frame_inversion(patterns, task)

        # Strategy: horizontal mirror mark (symmetric 5-pixels → recolor)
        if rule is None:
            rule = self._try_horizontal_mirror_mark(patterns, task)

        # Strategy: denoise keep rectangles (remove isolated pixels, keep solid rectangular blocks)
        if rule is None:
            rule = self._try_denoise_keep_rectangles(patterns, task)

        # Strategy: extend diagonal arms (2×2 block with diagonal tips → extend tips to grid edge)
        if rule is None:
            rule = self._try_extend_diagonal_arms(patterns, task)

        # Strategy: seed quadrant project (2×2 seed projects diag-opposite colors into quadrants)
        if rule is None:
            rule = self._try_seed_quadrant_project(patterns, task)

        # Strategy: flood fill partition (two bg regions → two distinct colors)
        if rule is None:
            rule = self._try_flood_fill_partition(patterns, task)

        # Strategy: rotation tile repeat (NxN → 4Nx4N, quadrants = 2×2 tiles of rotations)
        if rule is None:
            rule = self._try_rotation_tile_repeat(patterns, task)

        # Strategy: cross arm mode (plus-shapes centered on 4 → most frequent arm color)
        if rule is None:
            rule = self._try_cross_arm_mode(patterns, task)

        # Strategy: grid intersection compress (tiled grid → compressed 3×3)
        if rule is None:
            rule = self._try_grid_intersection_compress(patterns, task)

        # Strategy: enclosed rectangle fill (fill closed 2-borders with 1)
        if rule is None:
            rule = self._try_enclosed_rect_fill(patterns, task)

        # Strategy: color key remap (shape + scattered key pairs → substituted shape)
        if rule is None:
            rule = self._try_color_key_remap(patterns, task)

        # Strategy: square corner mark (mark corners of square borders)
        if rule is None:
            rule = self._try_square_corner_mark(patterns, task)

        # Strategy: domino cross intersection (mark where domino gap-centers cross)
        if rule is None:
            rule = self._try_domino_cross_intersection(patterns, task)

        # Strategy: separator projection (crop to separator frame, project pixels)
        if rule is None:
            rule = self._try_separator_projection(patterns, task)

        # Strategy: marker arm extend (rectangles + isolated markers → arms with cross ends)
        if rule is None:
            rule = self._try_marker_arm_extend(patterns, task)

        # Strategy: subgrid invert (0-separated grid, swap pattern↔uniform, remove 5-noise)
        if rule is None:
            rule = self._try_subgrid_invert(patterns, task)

        # Strategy: invert tile (swap 0↔nonzero, tile 2x2)
        if rule is None:
            rule = self._try_invert_tile(patterns, task)

        # Strategy: double mirror (reflect H+V → 2Nx2N)
        if rule is None:
            rule = self._try_double_mirror(patterns, task)

        # Strategy: column fill tile (active columns filled with 8, tile 2x2)
        if rule is None:
            rule = self._try_column_fill_tile(patterns, task)

        # Strategy: simple 1:1 color mapping
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

    # ---- strategy: gravity slide -----------------------------------------

    def _try_gravity_slide(self, patterns, task):
        """
        Detect: grid has 3 colors (bg, wall, object). Objects slide downward
        toward the wall, stopping with exactly 1 empty cell gap.
        Category: gravity / sliding toward boundary tasks.
        """
        if task is None:
            return None
        if not patterns.get("grid_size_preserved"):
            return None

        for pair in task.example_pairs:
            g0, g1 = pair.input_grid, pair.output_grid
            if g0 is None or g1 is None:
                return None
            raw_in = g0.raw
            raw_out = g1.raw
            h = len(raw_in)
            w = len(raw_in[0]) if raw_in else 0

            color_counts = Counter(c for row in raw_in for c in row)
            if len(color_counts) != 3:
                return None

            colors = [c for c, _ in color_counts.most_common()]

            # Try all 6 permutations of (bg, wall, obj)
            matched = False
            for bg, wall_color, obj_color in permutations(colors):
                if self._simulate_gravity(raw_in, raw_out, bg, wall_color, obj_color, h, w):
                    matched = True
                    break

            if not matched:
                return None

        return {"type": "gravity_slide", "confidence": 0.9}

    @staticmethod
    def _gravity_slide_grid(raw_in, bg, wall_color, obj_color, h, w):
        """Compute gravity slide result. Returns the output grid."""
        components = GeneralizeOperator._find_components(raw_in, obj_color)
        if not components:
            return None

        # Working grid: start with input, clear all object cells
        wg = [row[:] for row in raw_in]
        for comp in components:
            for r, c in comp:
                wg[r][c] = bg

        # Sort components bottom-first (largest max-row first)
        components.sort(key=lambda comp: max(r for r, c in comp), reverse=True)

        for comp in components:
            max_slide = h
            for r, c in comp:
                # Find first non-bg cell below in the working grid
                obstacle_row = h  # grid boundary
                is_wall = True  # treat boundary like wall
                for rr in range(r + 1, h):
                    if wg[rr][c] != bg:
                        obstacle_row = rr
                        is_wall = (wg[rr][c] == wall_color)
                        break
                # 1-cell gap for wall, 0-cell gap for other objects
                gap = 2 if is_wall else 1
                cell_slide = obstacle_row - r - gap
                if cell_slide < max_slide:
                    max_slide = cell_slide

            if max_slide < 0:
                max_slide = 0

            for r, c in comp:
                nr = r + max_slide
                if 0 <= nr < h:
                    wg[nr][c] = obj_color

        return wg

    def _simulate_gravity(self, raw_in, raw_out, bg, wall_color, obj_color, h, w):
        """Simulate gravity slide and check if it matches expected output."""
        components = self._find_components(raw_in, obj_color)
        if not components:
            return False
        result = self._gravity_slide_grid(raw_in, bg, wall_color, obj_color, h, w)
        return result == raw_out

    # ---- strategy: diamond bridge ----------------------------------------

    def _try_diamond_bridge(self, patterns, task):
        """
        Detect: grid has 3x3 diamond shapes (top, left, right, bottom pixels
        of one color, center is 0). Aligned diamonds are connected by lines
        of a bridge color. Category: connect aligned shapes tasks.
        """
        if task is None:
            return None
        if not patterns.get("grid_size_preserved"):
            return None

        bridge_color = None
        diamond_color = None

        for pair in task.example_pairs:
            g0, g1 = pair.input_grid, pair.output_grid
            if g0 is None or g1 is None:
                return None
            raw_in = g0.raw
            raw_out = g1.raw
            h = len(raw_in)
            w = len(raw_in[0]) if raw_in else 0

            # Find diamond centers in input
            centers = self._find_diamond_centers(raw_in, h, w)
            if not centers:
                return None

            dc = raw_in[centers[0][0] - 1][centers[0][1]]
            if diamond_color is None:
                diamond_color = dc
            elif diamond_color != dc:
                return None

            # Simulate bridge drawing and verify output
            predicted = self._draw_diamond_bridges(raw_in, centers, h, w)
            if predicted is None:
                return None

            # Find the bridge color from the diff
            bc = None
            for r in range(h):
                for c in range(w):
                    if raw_out[r][c] != raw_in[r][c]:
                        if raw_out[r][c] == 0:
                            return None  # shouldn't remove pixels
                        if bc is None:
                            bc = raw_out[r][c]
                        elif raw_out[r][c] != bc:
                            return None

            if bc is None:
                return None  # no changes found
            if bridge_color is None:
                bridge_color = bc
            elif bridge_color != bc:
                return None

            # Verify our prediction matches output
            predicted_bc = self._draw_diamond_bridges_with_color(
                raw_in, centers, h, w, bc
            )
            if predicted_bc != raw_out:
                return None

        return {
            "type": "diamond_bridge",
            "diamond_color": diamond_color,
            "bridge_color": bridge_color,
            "confidence": 1.0,
        }

    @staticmethod
    def _find_diamond_centers(grid, h, w):
        """Find centers of 3x3 diamond shapes (4 cardinal pixels same color, center=0)."""
        centers = []
        for r in range(1, h - 1):
            for c in range(1, w - 1):
                if grid[r][c] != 0:
                    continue
                top = grid[r - 1][c]
                bot = grid[r + 1][c]
                left = grid[r][c - 1]
                right = grid[r][c + 1]
                if top != 0 and top == bot == left == right:
                    centers.append((r, c))
        return centers

    @staticmethod
    def _draw_diamond_bridges(raw_in, centers, h, w):
        """Compute which cells should be bridged (returns set of positions)."""
        bridge_cells = set()

        # Group centers by row and column
        by_row = {}
        by_col = {}
        for r, c in centers:
            by_row.setdefault(r, []).append(c)
            by_col.setdefault(c, []).append(r)

        # Horizontal bridges between diamonds on the same row
        for row, cols in by_row.items():
            cols_sorted = sorted(cols)
            for i in range(len(cols_sorted) - 1):
                c1 = cols_sorted[i]
                c2 = cols_sorted[i + 1]
                # Bridge from right tip of left diamond to left tip of right diamond
                for cc in range(c1 + 2, c2 - 1):
                    bridge_cells.add((row, cc))

        # Vertical bridges between diamonds on the same column
        for col, rows in by_col.items():
            rows_sorted = sorted(rows)
            for i in range(len(rows_sorted) - 1):
                r1 = rows_sorted[i]
                r2 = rows_sorted[i + 1]
                for rr in range(r1 + 2, r2 - 1):
                    bridge_cells.add((rr, col))

        return bridge_cells

    @staticmethod
    def _draw_diamond_bridges_with_color(raw_in, centers, h, w, bridge_color):
        """Draw bridges on a copy of the grid."""
        output = [row[:] for row in raw_in]
        bridge_cells = GeneralizeOperator._draw_diamond_bridges(raw_in, centers, h, w)
        for r, c in bridge_cells:
            output[r][c] = bridge_color
        return output

    # ---- strategy: stripe zone fill --------------------------------------

    def _try_stripe_zone_fill(self, patterns, task):
        """
        Detect: grid has a vertical spine of color 8, background 7, and
        colored horizontal stripes (with 1 at the spine intersection).
        Output fills zones around each stripe with its color.
        Category: spine + stripe zone-filling tasks.
        """
        if task is None:
            return None
        if not patterns.get("grid_size_preserved"):
            return None

        for pair in task.example_pairs:
            g0, g1 = pair.input_grid, pair.output_grid
            if g0 is None or g1 is None:
                return None
            raw_in = g0.raw
            raw_out = g1.raw
            h = len(raw_in)
            w = len(raw_in[0]) if raw_in else 0

            # Find spine column (column with 8s and 1s)
            spine_col = self._find_spine_column(raw_in, h, w)
            if spine_col is None:
                return None

            # Find stripe rows
            stripes = self._find_stripe_rows(raw_in, h, w, spine_col)
            if not stripes:
                return None

            # Verify output matches zone fill
            predicted = self._compute_stripe_zone_fill(raw_in, h, w, spine_col, stripes)
            if predicted != raw_out:
                return None

        return {"type": "stripe_zone_fill", "confidence": 1.0}

    @staticmethod
    def _find_spine_column(grid, h, w):
        """Find the column that has 8 on non-stripe rows."""
        for c in range(w):
            is_spine = True
            has_8 = False
            for r in range(h):
                v = grid[r][c]
                if v == 8:
                    has_8 = True
                elif v != 1:
                    is_spine = False
                    break
            if is_spine and has_8:
                return c
        return None

    @staticmethod
    def _find_stripe_rows(grid, h, w, spine_col):
        """Find rows that are colored stripes (uniform non-7 color, 1 at spine)."""
        stripes = []
        for r in range(h):
            if grid[r][spine_col] != 1:
                continue
            # Check all non-spine cells are the same non-7 color
            color = None
            valid = True
            for c in range(w):
                if c == spine_col:
                    continue
                v = grid[r][c]
                if v == 7:
                    valid = False
                    break
                if color is None:
                    color = v
                elif v != color:
                    valid = False
                    break
            if valid and color is not None:
                stripes.append((r, color))
        return stripes

    @staticmethod
    def _compute_stripe_zone_fill(raw_in, h, w, spine_col, stripes):
        """Compute the zone-filled output grid."""
        output = [[0] * w for _ in range(h)]

        stripe_rows = [s[0] for s in stripes]
        stripe_colors = {s[0]: s[1] for s in stripes}

        # Assign each row to a stripe color or make it a separator
        row_assignment = [None] * h  # (color, is_stripe, is_separator)

        # Mark stripe rows
        for r in stripe_rows:
            row_assignment[r] = ("stripe", stripe_colors[r])

        # Process gaps between consecutive stripes (including before first and after last)
        boundaries = [-1] + stripe_rows + [h]
        for i in range(len(boundaries) - 1):
            prev_b = boundaries[i]
            next_b = boundaries[i + 1]

            if prev_b == -1 and next_b == h:
                continue  # no stripes at all

            # Get rows in this gap
            if prev_b == -1:
                # Before first stripe
                gap_start = 0
                gap_end = next_b - 1
                color = stripe_colors[next_b]
                for r in range(gap_start, gap_end + 1):
                    if row_assignment[r] is None:
                        row_assignment[r] = ("zone", color)
            elif next_b == h:
                # After last stripe
                gap_start = prev_b + 1
                gap_end = h - 1
                color = stripe_colors[prev_b]
                for r in range(gap_start, gap_end + 1):
                    if row_assignment[r] is None:
                        row_assignment[r] = ("zone", color)
            else:
                # Between two stripes
                gap_start = prev_b + 1
                gap_end = next_b - 1
                gap_size = gap_end - gap_start + 1
                color_above = stripe_colors[prev_b]
                color_below = stripe_colors[next_b]

                if gap_size <= 0:
                    continue

                if color_above == color_below:
                    # Same color: fill entire gap, no separator
                    for r in range(gap_start, gap_end + 1):
                        if row_assignment[r] is None:
                            row_assignment[r] = ("zone", color_above)
                elif gap_size % 2 == 1:
                    # Odd gap: middle row is separator
                    mid = gap_start + gap_size // 2
                    for r in range(gap_start, mid):
                        if row_assignment[r] is None:
                            row_assignment[r] = ("zone", color_above)
                    row_assignment[mid] = ("separator", None)
                    for r in range(mid + 1, gap_end + 1):
                        if row_assignment[r] is None:
                            row_assignment[r] = ("zone", color_below)
                else:
                    # Even gap: clean split
                    half = gap_size // 2
                    for r in range(gap_start, gap_start + half):
                        if row_assignment[r] is None:
                            row_assignment[r] = ("zone", color_above)
                    for r in range(gap_start + half, gap_end + 1):
                        if row_assignment[r] is None:
                            row_assignment[r] = ("zone", color_below)

        # Build output grid
        for r in range(h):
            assign = row_assignment[r]
            if assign is None:
                output[r] = raw_in[r][:]
                continue

            kind, color = assign
            if kind == "stripe":
                # Inverted: fill with 1, spine with 8
                for c in range(w):
                    output[r][c] = 8 if c == spine_col else 1
            elif kind == "zone":
                # Fill with zone color, spine with 1
                for c in range(w):
                    output[r][c] = 1 if c == spine_col else color
            elif kind == "separator":
                # All 1s
                for c in range(w):
                    output[r][c] = 1

        return output

    # ---- strategy: grid zigzag shear ----------------------------------------

    def _try_grid_zigzag_shear(self, patterns, task):
        """
        Detect: a single-color rectangular grid (with optional internal grid lines)
        on a background of 0. Output shifts each row of the bounding box
        horizontally in a period-4 sinusoidal pattern: [0, 1, 0, -1] with
        phase = (1 - bbox_height) % 4.
        Category: grid/rectangle zigzag shear tasks.
        """
        if task is None or not patterns.get("grid_size_preserved"):
            return None

        pairs = task.example_pairs
        if not pairs:
            return None

        for pair in pairs:
            inp = pair.input_grid.raw
            out = pair.output_grid.raw
            h, w = len(inp), len(inp[0])
            if len(out) != h or len(out[0]) != w:
                return None

            # Find non-background colors (exactly 2 colors: bg + shape)
            colors = set()
            for r in range(h):
                for c in range(w):
                    colors.add(inp[r][c])

            if len(colors) != 2:
                return None

            # Background = most frequent color
            counts = Counter()
            for r in range(h):
                for c in range(w):
                    counts[inp[r][c]] += 1
            bg_c = counts.most_common(1)[0][0]
            sc = [c for c in colors if c != bg_c][0]

            # Find bounding box of shape_color in input
            rows_with_sc = [r for r in range(h) for c in range(w) if inp[r][c] == sc]
            cols_with_sc = [c for r in range(h) for c in range(w) if inp[r][c] == sc]
            if not rows_with_sc:
                return None
            r0, r1 = min(rows_with_sc), max(rows_with_sc)
            c0, c1 = min(cols_with_sc), max(cols_with_sc)
            box_h = r1 - r0 + 1

            # Compute expected shifts
            sin_table = [0, 1, 0, -1]
            phase = (1 - box_h) % 4

            # Build expected output and compare
            expected_out = set()
            for ri in range(box_h):
                shift = sin_table[(ri + phase) % 4]
                for ci in range(c1 - c0 + 1):
                    in_r, in_c = r0 + ri, c0 + ci
                    if inp[in_r][in_c] == sc:
                        out_c = in_c + shift
                        if not (0 <= out_c < w):
                            return None
                        expected_out.add((in_r, out_c))

            actual_out = set()
            for r in range(h):
                for c in range(w):
                    if out[r][c] == sc:
                        actual_out.add((r, c))

            if expected_out != actual_out:
                return None

        return {
            "type": "grid_zigzag_shear",
            "confidence": 1.0,
        }

    # ---- strategy: three-shape rearrange ------------------------------------

    def _try_three_shape_rearrange(self, patterns, task):
        """
        Detect: 3 non-background colored objects on a uniform background.
        The smallest (connector) is between two larger objects along one axis.
        In the output, the connector moves into the region of one outer object,
        which splits in half (perpendicular to the axis) to make room.
        The split block must have perpendicular extent >= 2 * connector's
        perpendicular extent. The other outer block stays unchanged.
        Category: three-shape connector/split rearrangement tasks.
        """
        if task is None or not patterns.get("grid_size_preserved"):
            return None

        pairs = task.example_pairs
        if not pairs:
            return None

        for pair in pairs:
            inp = pair.input_grid.raw
            out = pair.output_grid.raw
            h, w = len(inp), len(inp[0])
            if len(out) != h or len(out[0]) != w:
                return None

            result = self._analyze_three_shape(inp, out, h, w)
            if result is None:
                return None

        return {
            "type": "three_shape_rearrange",
            "confidence": 1.0,
        }

    def _analyze_three_shape(self, inp, out, h, w):
        """Analyze a single pair for three-shape rearrange pattern. Returns info or None."""
        counts = Counter()
        for r in range(h):
            for c in range(w):
                counts[inp[r][c]] += 1
        bg = counts.most_common(1)[0][0]

        obj_colors = set()
        for r in range(h):
            for c in range(w):
                if inp[r][c] != bg:
                    obj_colors.add(inp[r][c])

        if len(obj_colors) != 3:
            return None

        objs = {}
        for color in obj_colors:
            pixels = [(r, c) for r in range(h) for c in range(w) if inp[r][c] == color]
            rmin = min(r for r, c in pixels)
            rmax = max(r for r, c in pixels)
            cmin = min(c for r, c in pixels)
            cmax = max(c for r, c in pixels)
            objs[color] = {
                "pixels": pixels, "count": len(pixels),
                "rmin": rmin, "rmax": rmax, "cmin": cmin, "cmax": cmax,
                "height": rmax - rmin + 1, "width": cmax - cmin + 1,
            }

        sorted_colors = sorted(obj_colors, key=lambda c: objs[c]["count"])
        conn_color = sorted_colors[0]
        outer_colors = sorted_colors[1:]

        connector = objs[conn_color]
        conn_cr = (connector["rmin"] + connector["rmax"]) / 2
        conn_cc = (connector["cmin"] + connector["cmax"]) / 2

        a_cr = (objs[outer_colors[0]]["rmin"] + objs[outer_colors[0]]["rmax"]) / 2
        a_cc = (objs[outer_colors[0]]["cmin"] + objs[outer_colors[0]]["cmax"]) / 2
        b_cr = (objs[outer_colors[1]]["rmin"] + objs[outer_colors[1]]["rmax"]) / 2
        b_cc = (objs[outer_colors[1]]["cmin"] + objs[outer_colors[1]]["cmax"]) / 2

        v_between = (min(a_cr, b_cr) <= conn_cr <= max(a_cr, b_cr))
        h_between = (min(a_cc, b_cc) <= conn_cc <= max(a_cc, b_cc))

        if not v_between and not h_between:
            return None

        if v_between and not h_between:
            axis = "vertical"
        elif h_between and not v_between:
            axis = "horizontal"
        else:
            v_spread = max(a_cr, b_cr) - min(a_cr, b_cr)
            h_spread = max(a_cc, b_cc) - min(a_cc, b_cc)
            axis = "vertical" if v_spread > h_spread else "horizontal"

        # Determine which block splits by checking perpendicular extent
        if axis == "vertical":
            conn_perp = connector["width"]
            a_perp = objs[outer_colors[0]]["width"]
            b_perp = objs[outer_colors[1]]["width"]
        else:
            conn_perp = connector["height"]
            a_perp = objs[outer_colors[0]]["height"]
            b_perp = objs[outer_colors[1]]["height"]

        a_can = (a_perp >= 2 * conn_perp)
        b_can = (b_perp >= 2 * conn_perp)

        if not a_can and not b_can:
            return None

        if a_can and not b_can:
            split_color = outer_colors[0]
            stay_color = outer_colors[1]
        elif b_can and not a_can:
            split_color = outer_colors[1]
            stay_color = outer_colors[0]
        else:
            # Both can split — check which one is unchanged in the output
            a_in = set(objs[outer_colors[0]]["pixels"])
            a_out = set((r, c) for r in range(h) for c in range(w) if out[r][c] == outer_colors[0])
            b_in = set(objs[outer_colors[1]]["pixels"])
            b_out = set((r, c) for r in range(h) for c in range(w) if out[r][c] == outer_colors[1])
            if a_in == a_out:
                split_color = outer_colors[1]
                stay_color = outer_colors[0]
            elif b_in == b_out:
                split_color = outer_colors[0]
                stay_color = outer_colors[1]
            else:
                return None

        # Verify by computing predicted output
        predicted = self._compute_three_shape_output(
            inp, bg, conn_color, split_color, stay_color, objs, axis, h, w)
        if predicted is None:
            return None
        for r in range(h):
            for c in range(w):
                if predicted[r][c] != out[r][c]:
                    return None

        return {"axis": axis, "split_color": split_color, "stay_color": stay_color}

    @staticmethod
    def _compute_three_shape_output(inp, bg, conn_color, split_color, stay_color,
                                     objs, axis, h, w):
        """Compute the predicted output for three-shape rearrange."""
        connector = objs[conn_color]
        split_obj = objs[split_color]

        output = [[bg] * w for _ in range(h)]

        # Keep stay object unchanged
        for r in range(h):
            for c in range(w):
                if inp[r][c] == stay_color:
                    output[r][c] = stay_color

        if axis == "vertical":
            # Determine direction: connector came from above or below split
            conn_cr = (connector["rmin"] + connector["rmax"]) / 2
            split_cr = (split_obj["rmin"] + split_obj["rmax"]) / 2

            # Split the split_obj left/right (perpendicular to vertical axis)
            split_mid_c = (split_obj["cmin"] + split_obj["cmax"] + 1) / 2.0
            for r, c in split_obj["pixels"]:
                nc = c - 1 if c < split_mid_c else c + 1
                if 0 <= nc < w:
                    output[r][nc] = split_color

            # Place connector at far side of split block along axis
            # Centered on split block perpendicular (columns)
            conn_new_cmin = int(
                (split_obj["cmin"] + split_obj["cmax"] + 1) / 2.0
                - connector["width"] / 2.0
            )
            if conn_cr > split_cr:
                # Connector came from below → place above split block
                conn_new_rmin = split_obj["rmin"] - connector["height"]
            else:
                # Connector came from above → place at bottom of split block
                conn_new_rmin = split_obj["rmax"] - connector["height"] + 1

            for r, c in connector["pixels"]:
                nr = r - connector["rmin"] + conn_new_rmin
                nc = c - connector["cmin"] + conn_new_cmin
                if 0 <= nr < h and 0 <= nc < w:
                    output[nr][nc] = conn_color

        else:  # horizontal
            conn_cc = (connector["cmin"] + connector["cmax"]) / 2
            split_cc = (split_obj["cmin"] + split_obj["cmax"]) / 2

            # Split the split_obj top/bottom (perpendicular to horizontal axis)
            split_mid_r = (split_obj["rmin"] + split_obj["rmax"] + 1) / 2.0
            for r, c in split_obj["pixels"]:
                nr = r - 1 if r < split_mid_r else r + 1
                if 0 <= nr < h:
                    output[nr][c] = split_color

            # Place connector at far side of split block along axis
            # Centered on split block perpendicular (rows)
            conn_new_rmin = int(
                (split_obj["rmin"] + split_obj["rmax"] + 1) / 2.0
                - connector["height"] / 2.0
            )
            if conn_cc > split_cc:
                # Connector came from right → place at left of split block
                conn_new_cmin = split_obj["cmin"] - connector["width"] + 1
            else:
                # Connector came from left → place at right of split block
                conn_new_cmin = split_obj["cmax"] - connector["width"] + 1

            for r, c in connector["pixels"]:
                nr = r - connector["rmin"] + conn_new_rmin
                nc = c - connector["cmin"] + conn_new_cmin
                if 0 <= nr < h and 0 <= nc < w:
                    output[nr][nc] = conn_color

        return output

    # ---- strategy: nearest corner lines -----------------------------------

    def _try_nearest_corner_lines(self, patterns, task):
        """
        Each non-background pixel projects an L-shaped line toward its nearest
        corner (nearest vertical edge + nearest horizontal edge).
        """
        pairs = task.example_pairs
        if not pairs:
            return None

        for pair in pairs:
            ig = pair.input_grid.raw if hasattr(pair.input_grid, 'raw') else pair.input_grid
            og = pair.output_grid.raw if hasattr(pair.output_grid, 'raw') else pair.output_grid
            h, w = len(ig), len(ig[0])
            oh, ow = len(og), len(og[0])
            if h != oh or w != ow:
                return None

            # Find non-zero pixels in input
            pixels = []
            for r in range(h):
                for c in range(w):
                    if ig[r][c] != 0:
                        pixels.append((r, c, ig[r][c]))
            if not pixels:
                return None

            # Simulate: draw L-lines for each pixel toward nearest corner
            sim = [[0] * w for _ in range(h)]
            for r, c, color in pixels:
                # Nearest vertical edge
                if r <= h - 1 - r:
                    # closer to top
                    for rr in range(0, r + 1):
                        sim[rr][c] = color
                else:
                    # closer to bottom
                    for rr in range(r, h):
                        sim[rr][c] = color
                # Nearest horizontal edge
                if c <= w - 1 - c:
                    # closer to left
                    for cc in range(0, c + 1):
                        sim[r][cc] = color
                else:
                    # closer to right
                    for cc in range(c, w):
                        sim[r][cc] = color

            if sim != [list(row) for row in og]:
                return None

        return {"type": "nearest_corner_lines", "confidence": 0.95}

    # ---- strategy: frame inversion -----------------------------------------

    def _try_frame_inversion(self, patterns, task):
        """
        Input has a single nested rectangle on a black bg: outer border color A,
        interior color B. Output extracts the rectangle and swaps A↔B.
        """
        pairs = task.example_pairs
        if not pairs:
            return None

        for pair in pairs:
            ig = pair.input_grid.raw if hasattr(pair.input_grid, 'raw') else pair.input_grid
            og = pair.output_grid.raw if hasattr(pair.output_grid, 'raw') else pair.output_grid
            h, w = len(ig), len(ig[0])

            # Find bounding box of non-zero pixels
            non_zero = [(r, c) for r in range(h) for c in range(w) if ig[r][c] != 0]
            if not non_zero:
                return None
            min_r = min(r for r, c in non_zero)
            max_r = max(r for r, c in non_zero)
            min_c = min(c for r, c in non_zero)
            max_c = max(c for r, c in non_zero)

            obj_h = max_r - min_r + 1
            obj_w = max_c - min_c + 1
            oh, ow = len(og), len(og[0])

            if obj_h != oh or obj_w != ow:
                return None
            if obj_h < 3 or obj_w < 3:
                return None

            # Extract the rectangle object
            obj = [ig[r][min_c:max_c + 1] for r in range(min_r, max_r + 1)]

            # Border color = color of corners
            border_color = obj[0][0]
            if border_color == 0:
                return None
            # All border pixels must be the same
            for c2 in range(obj_w):
                if obj[0][c2] != border_color or obj[obj_h - 1][c2] != border_color:
                    return None
            for r2 in range(obj_h):
                if obj[r2][0] != border_color or obj[r2][obj_w - 1] != border_color:
                    return None

            # Find interior color(s) -- should be exactly one non-border color
            interior_colors = set()
            for r2 in range(1, obj_h - 1):
                for c2 in range(1, obj_w - 1):
                    if obj[r2][c2] != border_color:
                        interior_colors.add(obj[r2][c2])
            if len(interior_colors) != 1:
                return None
            interior_color = interior_colors.pop()

            # Verify swap: output border = interior_color, output interior = border_color
            for r2 in range(oh):
                for c2 in range(ow):
                    is_border = (r2 == 0 or r2 == oh - 1 or c2 == 0 or c2 == ow - 1)
                    # Check if this cell was border in original
                    orig = obj[r2][c2]
                    expected = interior_color if orig == border_color else border_color
                    if og[r2][c2] != expected:
                        return None

        return {"type": "frame_inversion", "confidence": 0.95}

    # ---- strategy: horizontal mirror mark ----------------------------------

    def _try_horizontal_mirror_mark(self, patterns, task):
        """
        Grid has pixels of one foreground color on black bg. Pixels whose
        horizontally mirrored position (across the vertical center axis) also
        has the same color are recolored to a new color; others stay.
        """
        pairs = task.example_pairs
        if not pairs:
            return None

        fg_color = None
        new_color = None

        for pair in pairs:
            ig = pair.input_grid.raw if hasattr(pair.input_grid, 'raw') else pair.input_grid
            og = pair.output_grid.raw if hasattr(pair.output_grid, 'raw') else pair.output_grid
            h, w = len(ig), len(ig[0])
            oh, ow = len(og), len(og[0])
            if h != oh or w != ow:
                return None

            # Find the single foreground color in input
            in_colors = set()
            for r in range(h):
                for c in range(w):
                    if ig[r][c] != 0:
                        in_colors.add(ig[r][c])
            if len(in_colors) != 1:
                return None
            pair_fg = in_colors.pop()

            # Find colors in output that aren't in input and aren't 0
            out_colors = set()
            for r in range(h):
                for c in range(w):
                    if og[r][c] != 0:
                        out_colors.add(og[r][c])
            pair_new = out_colors - {pair_fg}
            if len(pair_new) != 1:
                return None
            pair_nc = pair_new.pop()

            if fg_color is None:
                fg_color = pair_fg
                new_color = pair_nc
            elif fg_color != pair_fg or new_color != pair_nc:
                return None

            # Verify the rule
            for r in range(h):
                for c in range(w):
                    mirror_c = w - 1 - c
                    if ig[r][c] == fg_color:
                        if ig[r][mirror_c] == fg_color:
                            expected = new_color
                        else:
                            expected = fg_color
                        if og[r][c] != expected:
                            return None
                    else:
                        if og[r][c] != ig[r][c]:
                            return None

        if fg_color is None:
            return None
        return {"type": "horizontal_mirror_mark", "fg_color": fg_color,
                "new_color": new_color, "confidence": 0.95}

    # ---- strategy: denoise keep rectangles --------------------------------

    def _try_denoise_keep_rectangles(self, patterns, task):
        """
        Detect pattern: input has solid filled rectangles plus scattered single
        pixels (noise) of the same color.  Output keeps only the rectangles
        and removes the noise.  Handles denoise / keep-rectangles tasks.
        """
        if not patterns.get("grid_size_preserved"):
            return None
        pairs = task.example_pairs if task else []
        if not pairs:
            return None

        for pair in pairs:
            g0, g1 = pair.input_grid, pair.output_grid
            if g0 is None or g1 is None:
                return None
            inp, out = g0.raw, g1.raw
            h, w = len(inp), len(inp[0])
            if len(out) != h or len(out[0]) != w:
                return None

            # Find foreground color(s) – non-zero
            fg_colors = set()
            for r in range(h):
                for c in range(w):
                    if inp[r][c] != 0:
                        fg_colors.add(inp[r][c])

            # Expect exactly one fg color per pair
            if len(fg_colors) != 1:
                return None
            fg = list(fg_colors)[0]

            # A fg pixel is "kept" iff it belongs to at least one 2×2 all-fg block.
            # This separates thick rectangular structures from isolated noise.
            keep = [[False] * w for _ in range(h)]
            for r in range(h - 1):
                for c in range(w - 1):
                    if inp[r][c] == fg and inp[r][c + 1] == fg and \
                       inp[r + 1][c] == fg and inp[r + 1][c + 1] == fg:
                        keep[r][c] = True
                        keep[r][c + 1] = True
                        keep[r + 1][c] = True
                        keep[r + 1][c + 1] = True

            # Must have both kept and removed fg pixels
            has_kept = any(keep[r][c] for r in range(h) for c in range(w))
            has_noise = any(inp[r][c] == fg and not keep[r][c]
                           for r in range(h) for c in range(w))
            if not has_kept or not has_noise:
                return None

            # Verify output matches: kept pixels = fg, rest = 0
            expected = [[fg if keep[r][c] else 0 for c in range(w)] for r in range(h)]
            if expected != out:
                return None

        return {"type": "denoise_keep_rectangles", "confidence": 0.9}

    # ---- strategy: extend diagonal arms ------------------------------------

    def _try_extend_diagonal_arms(self, patterns, task):
        """
        Detect pattern: a 2×2 block of one color with 1-2 single-pixel diagonal
        tips.  Each tip extends diagonally (same direction from the block) to the
        grid edge.  Handles diagonal-ray / arm-extension tasks.
        """
        if not patterns.get("grid_size_preserved"):
            return None
        pairs = task.example_pairs if task else []
        if not pairs:
            return None

        for pair in pairs:
            g0, g1 = pair.input_grid, pair.output_grid
            if g0 is None or g1 is None:
                return None
            inp, out = g0.raw, g1.raw
            h, w = len(inp), len(inp[0])
            if len(out) != h or len(out[0]) != w:
                return None

            # Find foreground color
            fg_colors = set()
            for r in range(h):
                for c in range(w):
                    if inp[r][c] != 0:
                        fg_colors.add(inp[r][c])
            if len(fg_colors) != 1:
                return None
            fg = list(fg_colors)[0]

            # Find connected component(s) of fg (8-connectivity)
            visited = [[False] * w for _ in range(h)]
            components = []
            for r in range(h):
                for c in range(w):
                    if inp[r][c] == fg and not visited[r][c]:
                        comp = []
                        queue = [(r, c)]
                        visited[r][c] = True
                        while queue:
                            cr, cc = queue.pop(0)
                            comp.append((cr, cc))
                            for dr, dc in [(-1, 0), (1, 0), (0, -1), (0, 1),
                                           (-1, -1), (-1, 1), (1, -1), (1, 1)]:
                                nr, nc = cr + dr, cc + dc
                                if 0 <= nr < h and 0 <= nc < w and not visited[nr][nc] and inp[nr][nc] == fg:
                                    visited[nr][nc] = True
                                    queue.append((nr, nc))
                        components.append(comp)

            if len(components) != 1:
                return None
            comp = components[0]
            comp_set = set(comp)

            # Find the 2×2 block within the component
            block = None
            for r in range(h - 1):
                for c in range(w - 1):
                    if (r, c) in comp_set and (r, c + 1) in comp_set and \
                       (r + 1, c) in comp_set and (r + 1, c + 1) in comp_set:
                        block = (r, c)
                        break
                if block:
                    break

            if block is None:
                return None

            br, bc = block
            block_cells = {(br, bc), (br, bc + 1), (br + 1, bc), (br + 1, bc + 1)}
            tips = [p for p in comp if p not in block_cells]

            if len(tips) < 1 or len(tips) > 2:
                return None

            # Each tip must be diagonally adjacent to the block
            for (tr, tc) in tips:
                corners = [(br - 1, bc - 1), (br - 1, bc + 2),
                           (br + 2, bc - 1), (br + 2, bc + 2)]
                if (tr, tc) not in corners:
                    return None

            # Verify output: block stays, each tip extends diagonally to edge
            expected = [[0] * w for _ in range(h)]
            for (cr, cc) in block_cells:
                expected[cr][cc] = fg
            for (tr, tc) in tips:
                dr = 1 if tr > br else -1
                dc = 1 if tc > bc else -1
                r2, c2 = tr, tc
                while 0 <= r2 < h and 0 <= c2 < w:
                    expected[r2][c2] = fg
                    r2 += dr
                    c2 += dc

            if expected != out:
                return None

        return {"type": "extend_diagonal_arms", "confidence": 0.95}

    # ---- strategy: seed quadrant project -----------------------------------

    def _try_seed_quadrant_project(self, patterns, task):
        """
        Detect pattern: a 2×2 non-zero seed in an otherwise zero grid.
        Each quadrant around the seed gets filled with the diagonally-opposite
        seed color.  Fill size = min(2, available_space) in each dimension,
        positioned adjacent to the seed.
        """
        if not patterns.get("grid_size_preserved"):
            return None
        pairs = task.example_pairs if task else []
        if not pairs:
            return None

        for pair in pairs:
            g0, g1 = pair.input_grid, pair.output_grid
            if g0 is None or g1 is None:
                return None
            inp, out = g0.raw, g1.raw
            h, w = len(inp), len(inp[0])
            if len(out) != h or len(out[0]) != w:
                return None

            # Find non-zero cells → must form exactly a 2×2 block
            nz = [(r, c) for r in range(h) for c in range(w) if inp[r][c] != 0]
            if len(nz) != 4:
                return None
            rows = sorted(set(r for r, c in nz))
            cols = sorted(set(c for r, c in nz))
            if len(rows) != 2 or len(cols) != 2:
                return None
            if rows[1] - rows[0] != 1 or cols[1] - cols[0] != 1:
                return None

            sr, sc = rows[0], cols[0]  # top-left of 2×2 seed
            seed = [[inp[sr][sc], inp[sr][sc + 1]],
                    [inp[sr + 1][sc], inp[sr + 1][sc + 1]]]

            # All 4 seed values must be non-zero and distinct
            seed_vals = [seed[0][0], seed[0][1], seed[1][0], seed[1][1]]
            if 0 in seed_vals or len(set(seed_vals)) != 4:
                return None

            # Build expected output
            expected = [[0] * w for _ in range(h)]
            # Copy seed
            for dr in range(2):
                for dc in range(2):
                    expected[sr + dr][sc + dc] = seed[dr][dc]

            # Quadrant fills: color = diag opposite, size = min(2, available)
            above = sr
            below = h - sr - 2
            left = sc
            right = w - sc - 2

            # Top-left: color = seed[1][1] (bottom-right)
            fh, fw = min(2, above), min(2, left)
            for dr in range(fh):
                for dc in range(fw):
                    expected[sr - fh + dr][sc - fw + dc] = seed[1][1]

            # Top-right: color = seed[1][0] (bottom-left)
            fh, fw = min(2, above), min(2, right)
            for dr in range(fh):
                for dc in range(fw):
                    expected[sr - fh + dr][sc + 2 + dc] = seed[1][0]

            # Bottom-left: color = seed[0][1] (top-right)
            fh, fw = min(2, below), min(2, left)
            for dr in range(fh):
                for dc in range(fw):
                    expected[sr + 2 + dr][sc - fw + dc] = seed[0][1]

            # Bottom-right: color = seed[0][0] (top-left)
            fh, fw = min(2, below), min(2, right)
            for dr in range(fh):
                for dc in range(fw):
                    expected[sr + 2 + dr][sc + 2 + dc] = seed[0][0]

            if expected != out:
                return None

        return {"type": "seed_quadrant_project", "confidence": 0.95}

    # ---- strategy: flood fill partition ---------------------------------

    def _try_flood_fill_partition(self, patterns, task):
        """
        Detect: one color vanishes, replaced by two new colors. Border-reachable
        cells of the vanishing color (4-connected to any grid edge) get one
        replacement color (exterior), unreachable cells get the other (interior).
        Category: inside/outside region coloring, maze partitioning tasks.
        """
        if not patterns.get("grid_size_preserved"):
            return None
        pairs = task.example_pairs if task else []
        if not pairs:
            return None

        zero_color = None
        exterior_color = None
        interior_color = None

        for pair in pairs:
            g0, g1 = pair.input_grid, pair.output_grid
            if g0 is None or g1 is None:
                return None
            inp, out = g0.raw, g1.raw
            h, w = len(inp), len(inp[0])
            if len(out) != h or len(out[0]) != w:
                return None

            in_colors = set(c for row in inp for c in row)
            out_colors = set(c for row in out for c in row)
            vanished = in_colors - out_colors
            appeared = out_colors - in_colors

            if len(vanished) != 1 or len(appeared) != 2:
                return None

            zc = vanished.pop()
            if zero_color is None:
                zero_color = zc
            elif zc != zero_color:
                return None

            # Verify non-vanishing cells are unchanged
            for r in range(h):
                for c in range(w):
                    if inp[r][c] != zero_color and inp[r][c] != out[r][c]:
                        return None

            # Flood-fill from border zero-cells (4-connected)
            visited = [[False] * w for _ in range(h)]
            queue = []
            for r in range(h):
                for c in range(w):
                    if inp[r][c] == zero_color and (r == 0 or r == h - 1 or c == 0 or c == w - 1):
                        if not visited[r][c]:
                            visited[r][c] = True
                            queue.append((r, c))

            exterior = set()
            qi = 0
            while qi < len(queue):
                cr, cc = queue[qi]
                qi += 1
                exterior.add((cr, cc))
                for dr, dc in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                    nr, nc = cr + dr, cc + dc
                    if 0 <= nr < h and 0 <= nc < w and not visited[nr][nc] and inp[nr][nc] == zero_color:
                        visited[nr][nc] = True
                        queue.append((nr, nc))

            interior = set()
            for r in range(h):
                for c in range(w):
                    if inp[r][c] == zero_color and (r, c) not in exterior:
                        interior.add((r, c))

            if not exterior or not interior:
                return None

            # Determine which replacement color is exterior vs interior
            ext_sample = next(iter(exterior))
            int_sample = next(iter(interior))
            ext_c = out[ext_sample[0]][ext_sample[1]]
            int_c = out[int_sample[0]][int_sample[1]]
            if ext_c == int_c:
                return None

            # Verify consistency
            for r, c in exterior:
                if out[r][c] != ext_c:
                    return None
            for r, c in interior:
                if out[r][c] != int_c:
                    return None

            if exterior_color is None:
                exterior_color = ext_c
                interior_color = int_c
            elif ext_c != exterior_color or int_c != interior_color:
                return None

        return {
            "type": "flood_fill_partition",
            "zero_color": zero_color,
            "color_a": exterior_color,
            "color_b": interior_color,
            "confidence": 1.0,
        }

    # ---- strategy: rotation tile repeat ---------------------------------

    def _try_rotation_tile_repeat(self, patterns, task):
        """
        Detect: NxN input → 4Nx4N output. The output is a 2×2 arrangement of
        quadrants (each 2N×2N), and each quadrant is a 2×2 tiling of a rotated
        version of the input (0°/90°/180°/270°).
        Category: rotation symmetry / tiling expansion tasks.
        """
        if task is None:
            return None
        pairs = task.example_pairs
        if not pairs:
            return None

        layout = None  # will be a tuple of 4 rotation indices for TL,TR,BL,BR

        def rot(grid, n, k):
            """Rotate grid by k*90 degrees CW."""
            g = [row[:] for row in grid]
            for _ in range(k % 4):
                g = [[g[n - 1 - c][r] for c in range(n)] for r in range(n)]
            return g

        for pair in pairs:
            ig = pair.input_grid.raw
            og = pair.output_grid.raw
            ih, iw = len(ig), len(ig[0])
            oh, ow = len(og), len(og[0])
            if ih != iw:
                return None
            n = ih
            if oh != 4 * n or ow != 4 * n:
                return None

            # Pre-compute all 4 rotations
            rotations = [rot(ig, n, k) for k in range(4)]

            # For each quadrant, find which rotation (tiled 2x2) matches
            quadrant_offsets = [(0, 0), (0, 2 * n), (2 * n, 0), (2 * n, 2 * n)]
            found_layout = []
            for qr, qc in quadrant_offsets:
                matched = -1
                for k in range(4):
                    rk = rotations[k]
                    ok = True
                    for r in range(2 * n):
                        for c in range(2 * n):
                            if og[qr + r][qc + c] != rk[r % n][c % n]:
                                ok = False
                                break
                        if not ok:
                            break
                    if ok:
                        matched = k
                        break
                if matched == -1:
                    return None
                found_layout.append(matched)

            found_layout = tuple(found_layout)
            if layout is None:
                layout = found_layout
            elif layout != found_layout:
                return None

        return {
            "type": "rotation_tile_repeat",
            "layout": list(layout),  # [TL, TR, BL, BR] rotation indices
            "confidence": 1.0,
        }

    # ---- strategy: cross arm mode ---------------------------------------

    def _try_cross_arm_mode(self, patterns, task):
        """
        Detect: grid contains plus/cross patterns centered on a specific color
        (center_color). Each cross has 4 orthogonal arms of the same non-bg color.
        Output is 1×1: the arm color that appears in the most crosses.
        Category: pattern counting / mode-finding tasks.
        """
        if task is None:
            return None
        pairs = task.example_pairs
        if not pairs:
            return None

        center_color = None

        for pair in pairs:
            ig = pair.input_grid.raw
            og = pair.output_grid.raw
            oh, ow = len(og), len(og[0])
            if oh != 1 or ow != 1:
                return None

            h, w = len(ig), len(ig[0])
            expected_output = og[0][0]

            # Find the background color (most common)
            color_counts = Counter(c for row in ig for c in row)
            bg = color_counts.most_common(1)[0][0]

            # Find all cells that could be cross centers:
            # 4 orthogonal neighbors all same non-bg color
            crosses = {}  # center_val -> list of arm colors
            for r in range(1, h - 1):
                for c in range(1, w - 1):
                    cv = ig[r][c]
                    if cv == bg:
                        continue
                    neighbors = [ig[r - 1][c], ig[r + 1][c], ig[r][c - 1], ig[r][c + 1]]
                    if len(set(neighbors)) == 1 and neighbors[0] != bg and neighbors[0] != cv:
                        crosses.setdefault(cv, []).append(neighbors[0])

            if not crosses:
                return None

            # Should be exactly one center color
            if len(crosses) != 1:
                return None
            cc = list(crosses.keys())[0]

            if center_color is None:
                center_color = cc
            elif center_color != cc:
                return None

            arm_colors = crosses[cc]
            # Find the mode
            arm_counts = Counter(arm_colors)
            mode_color = arm_counts.most_common(1)[0][0]
            if mode_color != expected_output:
                return None

        return {
            "type": "cross_arm_mode",
            "center_color": center_color,
            "confidence": 1.0,
        }

    # ---- strategy: grid intersection compress -----------------------------

    @staticmethod
    def _detect_grid_structure(raw):
        """Detect a regular grid: find the grid-line color and positions."""
        h, w = len(raw), len(raw[0]) if raw else 0
        if h < 5 or w < 5:
            return None

        # Try each row to find a full horizontal grid line (all same non-0 color)
        for r in range(h):
            vals = set(raw[r])
            if len(vals) == 1 and raw[r][0] != 0:
                grid_color = raw[r][0]
                # Find all full horizontal grid-line rows
                h_lines = [rr for rr in range(h) if all(raw[rr][c] == grid_color or raw[rr][c] != 0 for c in range(w)) and all(raw[rr][c] != 0 for c in range(w))]
                # Actually, grid lines may have non-grid colors at intersections
                # A grid-line row is one where the majority of values == grid_color
                break
        else:
            return None

        # Find grid-line rows: rows where at least 80% of values are grid_color
        h_lines = []
        for r in range(h):
            gc_count = sum(1 for c in range(w) if raw[r][c] == grid_color)
            if gc_count >= w * 0.7:
                h_lines.append(r)

        # Find grid-line cols: cols where at least 80% of values are grid_color
        v_lines = []
        for c in range(w):
            gc_count = sum(1 for r in range(h) if raw[r][c] == grid_color)
            if gc_count >= h * 0.7:
                v_lines.append(c)

        if len(h_lines) < 2 or len(v_lines) < 2:
            return None

        # Check regular spacing
        h_diffs = [h_lines[i+1] - h_lines[i] for i in range(len(h_lines)-1)]
        v_diffs = [v_lines[i+1] - v_lines[i] for i in range(len(v_lines)-1)]
        if len(set(h_diffs)) != 1 or len(set(v_diffs)) != 1:
            return None

        return grid_color, h_lines, v_lines

    def _try_grid_intersection_compress(self, patterns, task):
        """
        Detect: input is a large tiled grid with colored intersections on the
        grid lines. Output is a small compressed grid showing the intersection
        pattern. The 4×4 bounding box of colored intersections compresses to
        3×3 via overlap of middle rows/cols.
        Category: grid intersection summarization / compression tasks.
        """
        if task is None:
            return None
        # Output must be smaller than input
        if patterns.get("grid_size_preserved"):
            return None

        pairs = task.example_pairs
        if not pairs:
            return None

        for pair in pairs:
            g0, g1 = pair.input_grid, pair.output_grid
            if g0 is None or g1 is None:
                return None
            inp, out = g0.raw, g1.raw
            oh, ow = len(out), len(out[0])

            det = self._detect_grid_structure(inp)
            if det is None:
                return None
            grid_color, h_lines, v_lines = det

            # Extract intersection values
            int_grid = {}
            for ri, r in enumerate(h_lines):
                for ci, c in enumerate(v_lines):
                    val = inp[r][c]
                    if val != grid_color:
                        int_grid[(ri, ci)] = val

            if not int_grid:
                return None

            # Find bounding box
            min_r = min(k[0] for k in int_grid)
            max_r = max(k[0] for k in int_grid)
            min_c = min(k[1] for k in int_grid)
            max_c = max(k[1] for k in int_grid)

            bbox_h = max_r - min_r + 1
            bbox_w = max_c - min_c + 1

            if bbox_h != 4 or bbox_w != 4:
                return None

            # Extract 4×4 pattern (0 for grid-color positions)
            pat = [[0]*4 for _ in range(4)]
            for (ri, ci), val in int_grid.items():
                pat[ri - min_r][ci - min_c] = val

            # Compress 4×4 → 3×3
            compressed = self._compress_4x4_to_3x3(pat)

            # Verify against output
            if oh != 3 or ow != 3:
                return None
            if compressed != out:
                return None

        return {"type": "grid_intersection_compress", "confidence": 1.0}

    @staticmethod
    def _compress_4x4_to_3x3(pat):
        """Compress a 4×4 intersection pattern to 3×3.
        Row 0 stays, Row 3 stays, Row 1&2 overlap (agree→val, disagree→0).
        Same for columns."""
        # Step 1: compress rows 4→3
        mid = [0]*4
        for c in range(4):
            mid[c] = pat[1][c] if pat[1][c] == pat[2][c] else 0
        rows3 = [pat[0][:], mid, pat[3][:]]

        # Step 2: compress cols 4→3
        result = [[0]*3 for _ in range(3)]
        for r in range(3):
            result[r][0] = rows3[r][0]
            result[r][2] = rows3[r][3]
            result[r][1] = rows3[r][1] if rows3[r][1] == rows3[r][2] else 0
        return result

    # ---- strategy: enclosed rectangle fill --------------------------------

    def _try_enclosed_rect_fill(self, patterns, task):
        """
        Detect: input has shapes drawn with a border color on background 0.
        Closed rectangular regions (border cells fully enclosing an interior)
        get their interior 0-cells filled with color 1. Open/incomplete shapes
        are unchanged.
        Category: enclosed region detection / interior fill tasks.
        """
        if not patterns.get("grid_size_preserved"):
            return None
        pairs = task.example_pairs if task else []
        if not pairs:
            return None

        border_color = None

        for pair in pairs:
            g0, g1 = pair.input_grid, pair.output_grid
            if g0 is None or g1 is None:
                return None
            inp, out = g0.raw, g1.raw
            h, w = len(inp), len(inp[0])
            if len(out) != h or len(out[0]) != w:
                return None

            # Find border color: non-zero color(s) present in input
            in_colors = set(c for row in inp for c in row) - {0}
            out_colors = set(c for row in out for c in row) - {0}

            # Output should have exactly one new color (1) not in input
            new_colors = out_colors - in_colors
            if new_colors != {1}:
                return None

            # All input non-zero colors should be the same (border color)
            if len(in_colors) != 1:
                return None
            bc = in_colors.pop()
            if border_color is None:
                border_color = bc
            elif bc != border_color:
                return None

            # All non-zero, non-1 cells should be unchanged
            for r in range(h):
                for c in range(w):
                    if inp[r][c] != 0 and inp[r][c] != out[r][c]:
                        return None
                    if inp[r][c] == 0 and out[r][c] not in (0, 1):
                        return None

            # Flood-fill from border 0-cells
            visited = [[False]*w for _ in range(h)]
            queue = []
            for r in range(h):
                for c in range(w):
                    if inp[r][c] == 0 and (r == 0 or r == h-1 or c == 0 or c == w-1):
                        if not visited[r][c]:
                            visited[r][c] = True
                            queue.append((r, c))
            qi = 0
            while qi < len(queue):
                cr, cc = queue[qi]; qi += 1
                for dr, dc in [(-1,0),(1,0),(0,-1),(0,1)]:
                    nr, nc = cr+dr, cc+dc
                    if 0 <= nr < h and 0 <= nc < w and not visited[nr][nc] and inp[nr][nc] == 0:
                        visited[nr][nc] = True
                        queue.append((nr, nc))

            # Interior 0-cells (not reached) should become 1 in output
            for r in range(h):
                for c in range(w):
                    if inp[r][c] == 0:
                        if not visited[r][c]:
                            if out[r][c] != 1:
                                return None
                        else:
                            if out[r][c] != 0:
                                return None

        return {
            "type": "enclosed_rect_fill",
            "border_color": border_color,
            "confidence": 1.0,
        }

    # ---- strategy: color key remap ----------------------------------------

    def _try_color_key_remap(self, patterns, task):
        """
        Detect: input has a bordered rectangular shape plus isolated 2-pixel
        key pairs. Each key pair (a, b) means 'replace color b with color a'
        in the shape. Output is just the shape with colors substituted.
        Category: color substitution / palette remapping tasks.
        """
        if task is None:
            return None
        if patterns.get("grid_size_preserved"):
            return None

        pairs = task.example_pairs
        if not pairs:
            return None

        for pair in pairs:
            g0, g1 = pair.input_grid, pair.output_grid
            if g0 is None or g1 is None:
                return None
            inp, out = g0.raw, g1.raw

            result = self._analyze_color_key_remap(inp)
            if result is None:
                return None

            shape_region, color_map = result

            # Apply substitution and check
            sr, sc, er, ec = shape_region
            oh, ow = len(out), len(out[0])
            if oh != er - sr or ow != ec - sc:
                return None

            for r in range(oh):
                for c in range(ow):
                    orig = inp[sr + r][sc + c]
                    expected = color_map.get(orig, orig)
                    if expected != out[r][c]:
                        return None

        return {"type": "color_key_remap", "confidence": 1.0}

    @staticmethod
    def _analyze_color_key_remap(inp):
        """Analyze input grid for color key remap: find shape and key pairs."""
        h, w = len(inp), len(inp[0])

        # Find all non-zero connected components
        visited = [[False]*w for _ in range(h)]
        components = []
        for r in range(h):
            for c in range(w):
                if inp[r][c] != 0 and not visited[r][c]:
                    comp = []
                    queue = [(r, c)]
                    visited[r][c] = True
                    while queue:
                        cr, cc = queue.pop(0)
                        comp.append((cr, cc))
                        for dr, dc in [(-1,0),(1,0),(0,-1),(0,1)]:
                            nr, nc = cr+dr, cc+dc
                            if 0 <= nr < h and 0 <= nc < w and not visited[nr][nc] and inp[nr][nc] != 0:
                                visited[nr][nc] = True
                                queue.append((nr, nc))
                    components.append(comp)

        if len(components) < 2:
            return None

        # The largest component is the shape
        components.sort(key=len, reverse=True)
        shape_comp = components[0]
        key_comps = components[1:]

        # Shape bounding box
        sr = min(p[0] for p in shape_comp)
        sc = min(p[1] for p in shape_comp)
        er = max(p[0] for p in shape_comp) + 1
        ec = max(p[1] for p in shape_comp) + 1

        # Verify shape fills its bounding box (all non-zero)
        for r in range(sr, er):
            for c in range(sc, ec):
                if inp[r][c] == 0:
                    return None

        # Key pairs: each should be exactly 2 pixels, horizontal
        color_map = {}
        for comp in key_comps:
            if len(comp) != 2:
                return None
            (r1, c1), (r2, c2) = comp
            # Must be horizontal adjacent
            if r1 != r2 or abs(c1 - c2) != 1:
                return None
            # Left pixel = new color, right pixel = old color
            left_c = min(c1, c2)
            right_c = max(c1, c2)
            new_color = inp[r1][left_c]
            old_color = inp[r1][right_c]
            if old_color in color_map and color_map[old_color] != new_color:
                return None
            color_map[old_color] = new_color

        if not color_map:
            return None

        return (sr, sc, er, ec), color_map

    # ---- strategy: square corner mark ------------------------------------

    def _try_square_corner_mark(self, patterns, task):
        """
        Detect: input has square rectangular borders (perimeter-only shapes where
        width == height >= 2) on a uniform background. Output adds marker pixels
        at the four corner extensions of each square border.
        """
        if task is None:
            return None
        if not patterns.get("grid_size_preserved"):
            return None

        pairs = task.example_pairs
        if not pairs:
            return None

        marker_color = None

        for pair in pairs:
            g0, g1 = pair.input_grid, pair.output_grid
            if g0 is None or g1 is None:
                return None
            inp, out = g0.raw, g1.raw
            h, w = len(inp), len(inp[0])
            if len(out) != h or len(out[0]) != w:
                return None

            # Find background color (most common in input)
            from collections import Counter
            bg = Counter(inp[r][c] for r in range(h) for c in range(w)).most_common(1)[0][0]

            # Find connected components of non-bg color
            visited = [[False]*w for _ in range(h)]
            squares = []
            for r in range(h):
                for c in range(w):
                    if inp[r][c] != bg and not visited[r][c]:
                        comp = []
                        color = inp[r][c]
                        queue = [(r, c)]
                        visited[r][c] = True
                        while queue:
                            cr, cc = queue.pop(0)
                            comp.append((cr, cc))
                            for dr, dc in [(-1,0),(1,0),(0,-1),(0,1)]:
                                nr, nc = cr+dr, cc+dc
                                if 0 <= nr < h and 0 <= nc < w and not visited[nr][nc] and inp[nr][nc] == color:
                                    visited[nr][nc] = True
                                    queue.append((nr, nc))
                        # Check if this is a square rectangular border
                        r1 = min(p[0] for p in comp)
                        c1 = min(p[1] for p in comp)
                        r2 = max(p[0] for p in comp)
                        c2 = max(p[1] for p in comp)
                        bh = r2 - r1 + 1
                        bw = c2 - c1 + 1
                        if bh != bw or bh < 2:
                            continue
                        # Check perimeter cells are filled with color
                        perimeter = set()
                        for rr in range(r1, r2+1):
                            for cc2 in range(c1, c2+1):
                                if rr == r1 or rr == r2 or cc2 == c1 or cc2 == c2:
                                    perimeter.add((rr, cc2))
                        if set(comp) != perimeter:
                            continue
                        squares.append((r1, c1, r2, c2, color))

            if not squares:
                return None

            # Build expected output: start with input, add corner marks
            expected = [row[:] for row in inp]
            for (r1, c1, r2, c2, color) in squares:
                marks = [
                    (r1-1, c1), (r1, c1-1),   # top-left corner
                    (r1-1, c2), (r1, c2+1),   # top-right corner
                    (r2+1, c1), (r2, c1-1),   # bottom-left corner
                    (r2+1, c2), (r2, c2+1),   # bottom-right corner
                ]
                for mr, mc in marks:
                    if 0 <= mr < h and 0 <= mc < w:
                        # Detect marker color from actual output diff
                        if out[mr][mc] != inp[mr][mc] and out[mr][mc] != bg:
                            if marker_color is None:
                                marker_color = out[mr][mc]
                            elif marker_color != out[mr][mc]:
                                return None
                        expected[mr][mc] = out[mr][mc]

            if marker_color is None:
                return None

            # Re-build expected with the learned marker color
            expected2 = [row[:] for row in inp]
            for (r1, c1, r2, c2, color) in squares:
                marks = [
                    (r1-1, c1), (r1, c1-1),
                    (r1-1, c2), (r1, c2+1),
                    (r2+1, c1), (r2, c1-1),
                    (r2+1, c2), (r2, c2+1),
                ]
                for mr, mc in marks:
                    if 0 <= mr < h and 0 <= mc < w:
                        expected2[mr][mc] = marker_color

            if expected2 != out:
                return None

        return {"type": "square_corner_mark", "confidence": 1.0, "marker_color": marker_color}

    # ---- strategy: domino cross intersection ------------------------------

    def _try_domino_cross_intersection(self, patterns, task):
        """
        Detect: dominos (2-cell horizontal or vertical components) on a background.
        Where gap-centers of aligned consecutive dominos intersect, a marker is placed.
        """
        if task is None:
            return None
        if not patterns.get("grid_size_preserved"):
            return None

        pairs = task.example_pairs
        if not pairs:
            return None

        marker_color = None

        for pair in pairs:
            g0, g1 = pair.input_grid, pair.output_grid
            if g0 is None or g1 is None:
                return None
            inp, out = g0.raw, g1.raw
            h, w = len(inp), len(inp[0])
            if len(out) != h or len(out[0]) != w:
                return None

            from collections import Counter
            bg = Counter(inp[r][c] for r in range(h) for c in range(w)).most_common(1)[0][0]

            # Find connected components of non-bg color
            visited = [[False]*w for _ in range(h)]
            dominos_h = []  # horizontal dominos: (row, c_left, c_right)
            dominos_v = []  # vertical dominos: (col, r_top, r_bot)
            for r in range(h):
                for c in range(w):
                    if inp[r][c] != bg and not visited[r][c]:
                        comp = []
                        queue = [(r, c)]
                        visited[r][c] = True
                        while queue:
                            cr, cc = queue.pop(0)
                            comp.append((cr, cc))
                            for dr, dc in [(-1,0),(1,0),(0,-1),(0,1)]:
                                nr, nc = cr+dr, cc+dc
                                if 0 <= nr < h and 0 <= nc < w and not visited[nr][nc] and inp[nr][nc] != bg:
                                    visited[nr][nc] = True
                                    queue.append((nr, nc))
                        if len(comp) == 2:
                            (r1, c1), (r2, c2) = comp
                            if r1 == r2 and abs(c1 - c2) == 1:
                                dominos_h.append((r1, min(c1, c2), max(c1, c2)))
                            elif c1 == c2 and abs(r1 - r2) == 1:
                                dominos_v.append((min(c1, c2), min(r1, r2), max(r1, r2)))

            if not dominos_h and not dominos_v:
                return None

            # Find gap centers for consecutive aligned dominos
            # Horizontal dominos: group by row, find gap centers (column-wise)
            from collections import defaultdict
            h_by_row = defaultdict(list)
            for row, cl, cr in dominos_h:
                h_by_row[row].append((cl, cr))
            h_gap_centers = set()  # (row, col_center)
            for row, doms in h_by_row.items():
                doms.sort()
                for i in range(len(doms) - 1):
                    _, cr1 = doms[i]
                    cl2, _ = doms[i+1]
                    if cl2 > cr1 + 1:
                        gap_sum = (cr1 + 1 + cl2 - 1)
                        if gap_sum % 2 == 0:
                            h_gap_centers.add((row, gap_sum // 2))

            # Vertical dominos: group by column, find gap centers (row-wise)
            v_by_col = defaultdict(list)
            for col, rt, rb in dominos_v:
                v_by_col[col].append((rt, rb))
            v_gap_centers = set()  # (row_center, col)
            for col, doms in v_by_col.items():
                doms.sort()
                for i in range(len(doms) - 1):
                    _, rb1 = doms[i]
                    rt2, _ = doms[i+1]
                    if rt2 > rb1 + 1:
                        gap_sum = (rb1 + 1 + rt2 - 1)
                        if gap_sum % 2 == 0:
                            v_gap_centers.add((gap_sum // 2, col))

            # Find intersections
            intersections = set()
            for (hr, hc) in h_gap_centers:
                for (vr, vc) in v_gap_centers:
                    if hr == vr and hc == vc:
                        intersections.add((hr, hc))

            if not intersections:
                return None

            # Detect marker color from output
            for (ir, ic) in intersections:
                if out[ir][ic] != inp[ir][ic] and out[ir][ic] != bg:
                    if marker_color is None:
                        marker_color = out[ir][ic]
                    elif marker_color != out[ir][ic]:
                        return None

            if marker_color is None:
                return None

            # Verify output matches
            expected = [row[:] for row in inp]
            for (ir, ic) in intersections:
                expected[ir][ic] = marker_color

            if expected != out:
                return None

        return {"type": "domino_cross_intersection", "confidence": 1.0, "marker_color": marker_color}

    # ---- strategy: separator projection -----------------------------------

    @staticmethod
    def _find_separator_frame(inp):
        """Find 4 separator lines (2 rows, 2 cols) by dominant non-zero color.
        Returns (row1, color1, row2, color2, col1, color1, col2, color2) sorted,
        or None if not found. Separator = row/col where one non-zero color
        appears in >= 60% of cells.
        """
        from collections import Counter
        h, w = len(inp), len(inp[0])

        sep_rows = []
        for r in range(h):
            cnt = Counter(inp[r])
            for color, count in cnt.most_common():
                if color != 0 and count >= w * 0.6:
                    sep_rows.append((r, color))
                    break

        sep_cols = []
        for c in range(w):
            col = [inp[r][c] for r in range(h)]
            cnt = Counter(col)
            for color, count in cnt.most_common():
                if color != 0 and count >= h * 0.6:
                    sep_cols.append((c, color))
                    break

        if len(sep_rows) != 2 or len(sep_cols) != 2:
            return None

        fr1, fc1 = sep_rows[0]
        fr2, fc2 = sep_rows[1]
        fco1, fcc1 = sep_cols[0]
        fco2, fcc2 = sep_cols[1]

        if fr1 > fr2:
            fr1, fc1, fr2, fc2 = fr2, fc2, fr1, fc1
        if fco1 > fco2:
            fco1, fcc1, fco2, fcc2 = fco2, fcc2, fco1, fcc1

        sep_colors = {fc1, fc2, fcc1, fcc2}
        if len(sep_colors) != 4:
            return None

        return (fr1, fc1, fr2, fc2, fco1, fcc1, fco2, fcc2)

    def _try_separator_projection(self, patterns, task):
        """
        Detect: grid has 4 separator lines (2 rows, 2 cols) each with a distinct
        color. Scattered pixels of a color matching one separator. Output is
        cropped to the separator frame with projections toward the matching
        separator.
        """
        if task is None:
            return None
        if patterns.get("grid_size_preserved"):
            return None

        pairs = task.example_pairs
        if not pairs:
            return None

        for pair in pairs:
            g0, g1 = pair.input_grid, pair.output_grid
            if g0 is None or g1 is None:
                return None
            inp, out = g0.raw, g1.raw
            h, w = len(inp), len(inp[0])
            oh, ow = len(out), len(out[0])

            frame = self._find_separator_frame(inp)
            if frame is None:
                return None
            fr1, fc1, fr2, fc2, fco1, fcc1, fco2, fcc2 = frame
            sep_colors = {fc1, fc2, fcc1, fcc2}

            inner_r1, inner_r2 = fr1 + 1, fr2 - 1
            inner_c1, inner_c2 = fco1 + 1, fco2 - 1
            if inner_r1 > inner_r2 or inner_c1 > inner_c2:
                return None

            frame_h = fr2 - fr1 + 1
            frame_w = fco2 - fco1 + 1
            if oh != frame_h or ow != frame_w:
                return None

            # Find scattered pixels in the inner region (exclude sep rows/cols)
            scattered = []
            scattered_color = None
            sep_row_set = {fr1, fr2}
            sep_col_set = {fco1, fco2}
            for r in range(inner_r1, inner_r2 + 1):
                for c in range(inner_c1, inner_c2 + 1):
                    v = inp[r][c]
                    if v != 0:
                        if scattered_color is None:
                            scattered_color = v
                        elif v != scattered_color:
                            return None
                        scattered.append((r, c))

            if scattered_color is None:
                return None
            if scattered_color not in sep_colors:
                return None

            # Determine projection direction
            match_dir = None
            if scattered_color == fc1:
                match_dir = "top"
            elif scattered_color == fc2:
                match_dir = "bottom"
            elif scattered_color == fcc1:
                match_dir = "left"
            elif scattered_color == fcc2:
                match_dir = "right"

            # Build expected output: copy frame borders from input
            expected = [[0]*frame_w for _ in range(frame_h)]
            for c in range(frame_w):
                expected[0][c] = inp[fr1][fco1 + c]
                expected[frame_h - 1][c] = inp[fr2][fco1 + c]
            for r in range(frame_h):
                expected[r][0] = inp[fr1 + r][fco1]
                expected[r][frame_w - 1] = inp[fr1 + r][fco2]

            for (sr, sc) in scattered:
                ofr = sr - fr1
                ofc = sc - fco1
                expected[ofr][ofc] = scattered_color
                if match_dir == "top":
                    for rr in range(1, ofr):
                        expected[rr][ofc] = scattered_color
                elif match_dir == "bottom":
                    for rr in range(ofr + 1, frame_h - 1):
                        expected[rr][ofc] = scattered_color
                elif match_dir == "left":
                    for cc in range(1, ofc):
                        expected[ofr][cc] = scattered_color
                elif match_dir == "right":
                    for cc in range(ofc + 1, frame_w - 1):
                        expected[ofr][cc] = scattered_color

            if expected != out:
                return None

        return {"type": "separator_projection", "confidence": 1.0}

    # ---- strategy: marker arm extend ------------------------------------

    def _try_marker_arm_extend(self, patterns, task):
        """
        Detect: background grid with solid rectangular blocks and isolated
        single-pixel markers of the same colour.  Each marker causes an arm
        to extend from the nearest rectangle edge toward (and past) the
        marker, with cross-shaped endpoints.
        Category: rectangle-marker arm-extension tasks.
        """
        if task is None:
            return None
        pairs = task.example_pairs
        if not pairs:
            return None

        for pair in pairs:
            ig = pair.input_grid.raw
            og = pair.output_grid.raw
            h, w = len(ig), len(ig[0])
            if (len(og), len(og[0])) != (h, w):
                return None

            predicted = _marker_arm_extend_transform(ig)
            if predicted is None:
                return None
            if predicted != og:
                return None

        return {"type": "marker_arm_extend", "confidence": 1.0}

    # ---- strategy: subgrid invert ----------------------------------------

    def _try_subgrid_invert(self, patterns, task):
        """
        Detect: grid divided into NxM sub-grids by full rows/cols of 0.
        Each sub-grid is either a repeating pattern template or uniform fill.
        Colour 5 may corrupt some cells.  The output swaps pattern↔uniform
        and removes all 5-noise.
        Category: sub-grid pattern/uniform inversion with denoising.
        """
        if task is None:
            return None
        pairs = task.example_pairs
        if not pairs:
            return None

        for pair in pairs:
            ig = pair.input_grid.raw
            og = pair.output_grid.raw
            h, w = len(ig), len(ig[0])
            if (len(og), len(og[0])) != (h, w):
                return None

            predicted = _subgrid_invert_transform(ig)
            if predicted is None:
                return None
            if predicted != og:
                return None

        return {"type": "subgrid_invert", "confidence": 1.0}

    # ---- strategy: invert tile (swap 0↔nonzero, tile 2x2) ---------------

    def _try_invert_tile(self, patterns, task):
        """
        Detect: output = 2Nx2N tiling of the NxN input with 0↔nonzero swapped.
        Category: color-inversion + simple tiling tasks.
        """
        pairs = task.example_pairs
        if not pairs:
            return None
        for pair in pairs:
            ig = pair.input_grid.raw
            og = pair.output_grid.raw
            h, w = len(ig), len(ig[0])
            oh, ow = len(og), len(og[0])
            if oh != 2 * h or ow != 2 * w:
                return None
            # Detect the single non-zero color in input
            nz = set()
            for row in ig:
                for c in row:
                    if c != 0:
                        nz.add(c)
            if len(nz) != 1:
                return None
            fg = next(iter(nz))
            # Build inverted grid
            inv = []
            for row in ig:
                inv.append([fg if c == 0 else 0 for c in row])
            # Verify tiling 2x2
            for r in range(oh):
                for c in range(ow):
                    if og[r][c] != inv[r % h][c % w]:
                        return None
        return {"type": "invert_tile", "confidence": 1.0}

    # ---- strategy: double mirror (reflect H+V → 2Nx2N) ------------------

    def _try_double_mirror(self, patterns, task):
        """
        Detect: output is 2Nx2N created by reflecting NxN input horizontally
        (left-right) then reflecting the combined result vertically (top-bottom).
        Category: kaleidoscope / 4-fold mirror symmetry expansion tasks.
        """
        pairs = task.example_pairs
        if not pairs:
            return None
        for pair in pairs:
            ig = pair.input_grid.raw
            og = pair.output_grid.raw
            h, w = len(ig), len(ig[0])
            oh, ow = len(og), len(og[0])
            if oh != 2 * h or ow != 2 * w:
                return None
            # Build the expected 2Nx2N by H-mirror then V-mirror
            wide = []
            for row in ig:
                wide.append(list(row) + list(reversed(row)))
            full = wide + list(reversed(wide))
            for r in range(oh):
                for c in range(ow):
                    if og[r][c] != full[r][c]:
                        return None
        return {"type": "double_mirror", "confidence": 1.0}

    # ---- strategy: column fill tile (active columns → 8, tile 2x2) ------

    def _try_column_fill_tile(self, patterns, task):
        """
        Detect: columns with any non-zero cell get 0→fill_color replacement;
        all-zero columns stay 0. Result is tiled 2x2 to produce 2Nx2N output.
        Category: column-activation fill + tiling tasks.
        """
        pairs = task.example_pairs
        if not pairs:
            return None
        fill_color = None
        for pair in pairs:
            ig = pair.input_grid.raw
            og = pair.output_grid.raw
            h, w = len(ig), len(ig[0])
            oh, ow = len(og), len(og[0])
            if oh != 2 * h or ow != 2 * w:
                return None
            # Determine active columns
            active = set()
            for c in range(w):
                for r in range(h):
                    if ig[r][c] != 0:
                        active.add(c)
                        break
            # Determine fill color from output (non-zero, non-input-color 0 replacements)
            for c in active:
                for r in range(h):
                    if ig[r][c] == 0:
                        fc = og[r][c]
                        if fc == 0:
                            return None  # should be filled
                        if fill_color is None:
                            fill_color = fc
                        elif fill_color != fc:
                            return None
            # Build transformed grid
            transformed = []
            for r in range(h):
                row = []
                for c in range(w):
                    if c in active:
                        row.append(ig[r][c] if ig[r][c] != 0 else fill_color)
                    else:
                        row.append(0)
                transformed.append(row)
            # Verify tiling 2x2
            for r in range(oh):
                for c in range(ow):
                    if og[r][c] != transformed[r % h][c % w]:
                        return None
        if fill_color is None:
            return None
        return {"type": "column_fill_tile", "fill_color": fill_color, "confidence": 1.0}

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

    # ---- strategy: vertical mirror append --------------------------------

    def _try_vertical_mirror_append(self, patterns, task):
        """
        Detect: output is the input rows followed by the input rows in
        reverse order (vertical mirror/reflection appended below).
        Category: any task where output_h == 2 * input_h and the bottom
        half is the vertically flipped top half.
        """
        if task is None:
            return None
        # This strategy is for size-changing tasks
        if patterns.get("grid_size_preserved"):
            return None

        for pair in task.example_pairs:
            g0, g1 = pair.input_grid, pair.output_grid
            if g0 is None or g1 is None:
                return None
            raw_in = g0.raw
            raw_out = g1.raw
            h_in = len(raw_in)
            w_in = len(raw_in[0]) if raw_in else 0
            h_out = len(raw_out)
            w_out = len(raw_out[0]) if raw_out else 0

            if h_out != 2 * h_in or w_out != w_in:
                return None

            # Top half must equal input, bottom half must equal reversed input
            for r in range(h_in):
                if raw_out[r] != raw_in[r]:
                    return None
                if raw_out[h_out - 1 - r] != raw_in[r]:
                    return None

        return {"type": "vertical_mirror_append", "confidence": 1.0}

    # ---- strategy: fill rectangles by interior size ----------------------

    def _try_fill_rectangles_by_size(self, patterns, task):
        """
        Detect: rectangles outlined with one color on a background; each
        rectangle's interior is filled with a color that depends on its
        interior area.  Category: size-based rectangle fill.
        """
        if task is None:
            return None
        if not patterns.get("grid_size_preserved"):
            return None

        # Determine bg and outline colors from first example input
        raw0 = task.example_pairs[0].input_grid.raw
        flat = [c for row in raw0 for c in row]
        bg_color = Counter(flat).most_common(1)[0][0]
        non_bg = [c for c in flat if c != bg_color]
        if not non_bg:
            return None
        outline_color = Counter(non_bg).most_common(1)[0][0]

        size_to_color = {}

        for pair in task.example_pairs:
            g0, g1 = pair.input_grid, pair.output_grid
            if g0 is None or g1 is None:
                return None
            raw_in = g0.raw
            raw_out = g1.raw

            rects = _find_outlined_rectangles(raw_in, outline_color, bg_color)
            if not rects:
                return None

            for (r1, c1, r2, c2) in rects:
                interior_h = r2 - r1 - 1
                interior_w = c2 - c1 - 1
                if interior_h <= 0 or interior_w <= 0:
                    return None
                area = interior_h * interior_w

                # What color fills the interior in the output?
                fill_color = raw_out[r1 + 1][c1 + 1]
                # Verify entire interior has the same fill
                for rr in range(r1 + 1, r2):
                    for cc in range(c1 + 1, c2):
                        if raw_out[rr][cc] != fill_color:
                            return None

                if area in size_to_color:
                    if size_to_color[area] != fill_color:
                        return None
                else:
                    size_to_color[area] = fill_color

        if not size_to_color:
            return None

        return {
            "type": "fill_rectangles_by_size",
            "outline_color": outline_color,
            "bg_color": bg_color,
            "size_to_color": size_to_color,
            "confidence": 0.9,
        }

    # ---- strategy: reverse concentric rings --------------------------------

    def _try_reverse_rings(self, patterns, task):
        """
        Detect: grid is concentric rectangular rings of distinct colors.
        Output reverses the ring order (outermost ↔ innermost).
        Category: concentric ring reversal tasks.
        """
        if task is None:
            return None
        if not patterns.get("grid_size_preserved"):
            return None

        for pair in task.example_pairs:
            g0, g1 = pair.input_grid, pair.output_grid
            if g0 is None or g1 is None:
                return None
            raw_in = g0.raw
            raw_out = g1.raw
            h, w = len(raw_in), len(raw_in[0]) if raw_in else 0

            # Extract ring colors from input (layer 0 = outermost)
            ring_colors_in = self._extract_ring_colors(raw_in)
            if ring_colors_in is None:
                return None

            ring_colors_out = self._extract_ring_colors(raw_out)
            if ring_colors_out is None:
                return None

            # Check that output rings are the reverse of input rings
            if ring_colors_out != list(reversed(ring_colors_in)):
                return None

        return {"type": "reverse_rings", "confidence": 1.0}

    @staticmethod
    def _extract_ring_colors(grid):
        """Extract colors of concentric rectangular rings from outside in."""
        h = len(grid)
        w = len(grid[0]) if grid else 0
        colors = []
        max_layers = min(h, w) // 2 + (1 if min(h, w) % 2 else 0)

        for layer in range(max_layers):
            # Get the color of the top-left cell of this ring
            color = grid[layer][layer]

            # Verify entire ring has this color
            # Top and bottom rows of the ring
            for c in range(layer, w - layer):
                if grid[layer][c] != color or grid[h - 1 - layer][c] != color:
                    return None
            # Left and right columns of the ring
            for r in range(layer, h - layer):
                if grid[r][layer] != color or grid[r][w - 1 - layer] != color:
                    return None

            colors.append(color)

        return colors

    # ---- strategy: pixel scale-up ----------------------------------------

    def _try_pixel_scale(self, patterns, task):
        """
        Detect: output dimensions are an integer multiple of input dimensions,
        and each input pixel maps to a uniform NxN block in output.
        Category: pixel upscaling / zoom tasks.
        """
        if task is None:
            return None
        # This is for size-changing tasks
        if patterns.get("grid_size_preserved"):
            return None

        scale = None

        for pair in task.example_pairs:
            g0, g1 = pair.input_grid, pair.output_grid
            if g0 is None or g1 is None:
                return None
            raw_in = g0.raw
            raw_out = g1.raw
            h_in = len(raw_in)
            w_in = len(raw_in[0]) if raw_in else 0
            h_out = len(raw_out)
            w_out = len(raw_out[0]) if raw_out else 0

            if h_in == 0 or w_in == 0:
                return None
            if h_out % h_in != 0 or w_out % w_in != 0:
                return None

            sh = h_out // h_in
            sw = w_out // w_in
            if sh != sw or sh < 2:
                return None

            if scale is None:
                scale = sh
            elif scale != sh:
                return None

            # Verify each input pixel maps to a uniform block
            for r in range(h_in):
                for c in range(w_in):
                    expected = raw_in[r][c]
                    for dr in range(scale):
                        for dc in range(scale):
                            if raw_out[r * scale + dr][c * scale + dc] != expected:
                                return None

        return {"type": "pixel_scale", "scale": scale, "confidence": 1.0}

    # ---- strategy: recolor components by size ----------------------------

    def _try_recolor_by_size(self, patterns, task):
        """
        Detect: all connected components of a single 'source' color are
        recolored based on their size group (largest group=1, next size=2, etc.).
        Components of the same size get the same color.
        Category: size-based component classification tasks.
        """
        if task is None:
            return None
        if not patterns.get("grid_size_preserved"):
            return None

        source_color = None

        for pair in task.example_pairs:
            g0, g1 = pair.input_grid, pair.output_grid
            if g0 is None or g1 is None:
                return None
            raw_in = g0.raw
            raw_out = g1.raw
            h = len(raw_in)
            w = len(raw_in[0]) if raw_in else 0

            # Find non-zero colors in input
            in_colors = set()
            for row in raw_in:
                for c in row:
                    if c != 0:
                        in_colors.add(c)

            # Input should have exactly one non-bg color
            if len(in_colors) != 1:
                return None
            src = list(in_colors)[0]
            if source_color is None:
                source_color = src
            elif source_color != src:
                return None

            # Find connected components of source color
            components = self._find_components(raw_in, source_color)
            if not components:
                return None

            # Build size-to-color mapping: distinct sizes sorted descending
            sizes = sorted(set(len(c) for c in components), reverse=True)
            size_to_color = {s: rank + 1 for rank, s in enumerate(sizes)}

            # Check that each component is recolored by its size group
            for comp in components:
                expected_color = size_to_color[len(comp)]
                for (r, c) in comp:
                    if raw_out[r][c] != expected_color:
                        return None

            # Check that non-source cells are unchanged
            for r in range(h):
                for c in range(w):
                    if raw_in[r][c] != source_color and raw_out[r][c] != raw_in[r][c]:
                        return None

        return {
            "type": "recolor_by_size",
            "source_color": source_color,
            "confidence": 1.0,
        }

    @staticmethod
    def _find_components(grid, color):
        """Find all connected components of a given color in grid."""
        h = len(grid)
        w = len(grid[0]) if grid else 0
        visited = set()
        components = []
        for r in range(h):
            for c in range(w):
                if grid[r][c] == color and (r, c) not in visited:
                    comp = []
                    queue = [(r, c)]
                    visited.add((r, c))
                    while queue:
                        cr, cc = queue.pop(0)
                        comp.append((cr, cc))
                        for dr, dc in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                            nr, nc = cr + dr, cc + dc
                            if 0 <= nr < h and 0 <= nc < w and (nr, nc) not in visited and grid[nr][nc] == color:
                                visited.add((nr, nc))
                                queue.append((nr, nc))
                    components.append(comp)
        return components

    # ---- strategy: staircase growth ----------------------------------------

    def _try_staircase_growth(self, patterns, task):
        """
        Detect: input is a single row with N cells of color C on the left,
        rest 0. Output has W/2 rows; row i has N+i cells of color C.
        Category: 1D-to-2D staircase / triangle expansion.
        """
        if task is None:
            return None
        # Must be size-changing (1 row → multiple rows)
        if patterns.get("grid_size_preserved"):
            return None

        color = None
        for pair in task.example_pairs:
            g0, g1 = pair.input_grid, pair.output_grid
            if g0 is None or g1 is None:
                return None
            raw_in = g0.raw
            raw_out = g1.raw

            # Input must be exactly 1 row
            if len(raw_in) != 1:
                return None
            w = len(raw_in[0])
            if w < 2 or w % 2 != 0:
                return None

            # Count leading non-zero cells of a single color
            row = raw_in[0]
            c = row[0]
            if c == 0:
                return None
            n = 0
            for v in row:
                if v == c:
                    n += 1
                else:
                    break
            # Rest must be 0
            if any(v != 0 for v in row[n:]):
                return None

            # Color can differ across pairs (each pair uses its own color)

            # Verify output: W/2 rows, row i has N+i cells of color C
            expected_rows = w // 2
            if len(raw_out) != expected_rows:
                return None
            if len(raw_out[0]) != w:
                return None

            for i in range(expected_rows):
                count = n + i
                for j in range(w):
                    expected = c if j < count else 0
                    if raw_out[i][j] != expected:
                        return None

        return {"type": "staircase_growth", "confidence": 1.0}

    # ---- strategy: corner-fill quadrants -----------------------------------

    def _try_corner_fill_quadrants(self, patterns, task):
        """
        Detect: one or more rectangular blocks of a filler color (e.g. 5) on
        bg (0), each with 4 colored pixels at diagonal corners just outside.
        Output replaces each filler block with 4 quadrants colored by corners.
        Category: rectangle + corner markers → quadrant coloring.
        """
        if task is None:
            return None
        if not patterns.get("grid_size_preserved"):
            return None

        filler_color = None
        bg_color = 0

        for pair in task.example_pairs:
            g0, g1 = pair.input_grid, pair.output_grid
            if g0 is None or g1 is None:
                return None
            raw_in = g0.raw
            raw_out = g1.raw
            h = len(raw_in)
            w = len(raw_in[0]) if raw_in else 0

            # Find candidate filler color (most frequent non-bg)
            freq = Counter(v for row in raw_in for v in row if v != bg_color)
            if not freq:
                return None

            # Try each candidate filler color
            found = False
            for fc, _ in freq.most_common():
                rects = self._find_filler_rectangles(raw_in, fc, h, w)
                if not rects:
                    continue

                # Verify all rects have valid corners and correct output
                all_ok = True
                for (r1, c1, r2, c2) in rects:
                    rect_h = r2 - r1 + 1
                    rect_w = c2 - c1 + 1
                    if rect_h % 2 != 0 or rect_w % 2 != 0:
                        all_ok = False
                        break

                    corners = self._get_rect_corners(raw_in, r1, c1, r2, c2, h, w, bg_color, fc)
                    if corners is None:
                        all_ok = False
                        break

                    half_h = rect_h // 2
                    half_w = rect_w // 2
                    for r in range(r1, r2 + 1):
                        for c in range(c1, c2 + 1):
                            qr = "t" if r < r1 + half_h else "b"
                            qc = "l" if c < c1 + half_w else "r"
                            if raw_out[r][c] != corners[qr + qc]:
                                all_ok = False
                                break
                        if not all_ok:
                            break
                    if not all_ok:
                        break

                    # Verify corners removed
                    for cr, cc in [(r1-1,c1-1),(r1-1,c2+1),(r2+1,c1-1),(r2+1,c2+1)]:
                        if 0 <= cr < h and 0 <= cc < w and raw_out[cr][cc] != bg_color:
                            all_ok = False
                            break
                    if not all_ok:
                        break

                if all_ok and rects:
                    if filler_color is None:
                        filler_color = fc
                    elif filler_color != fc:
                        return None
                    found = True
                    break

            if not found:
                return None

        return {
            "type": "corner_fill_quadrants",
            "filler_color": filler_color,
            "bg_color": bg_color,
            "confidence": 1.0,
        }

    @staticmethod
    def _find_filler_rectangles(grid, filler, h, w):
        """Find all connected rectangular blocks of filler color."""
        visited = set()
        rects = []
        for r in range(h):
            for c in range(w):
                if grid[r][c] == filler and (r, c) not in visited:
                    # BFS to find connected component
                    comp = []
                    queue = [(r, c)]
                    visited.add((r, c))
                    while queue:
                        cr, cc = queue.pop(0)
                        comp.append((cr, cc))
                        for dr, dc in [(-1,0),(1,0),(0,-1),(0,1)]:
                            nr, nc = cr+dr, cc+dc
                            if 0 <= nr < h and 0 <= nc < w and (nr, nc) not in visited and grid[nr][nc] == filler:
                                visited.add((nr, nc))
                                queue.append((nr, nc))
                    # Check if component is a perfect rectangle
                    rows = [p[0] for p in comp]
                    cols = [p[1] for p in comp]
                    min_r, max_r = min(rows), max(rows)
                    min_c, max_c = min(cols), max(cols)
                    expected = (max_r - min_r + 1) * (max_c - min_c + 1)
                    if len(comp) == expected:
                        rects.append((min_r, min_c, max_r, max_c))
        return rects

    @staticmethod
    def _get_rect_corners(grid, r1, c1, r2, c2, h, w, bg_color, filler):
        """Get 4 diagonal corner colors of a rectangle, or None if invalid."""
        corners = {}
        for key, (cr, cc) in [("tl",(r1-1,c1-1)),("tr",(r1-1,c2+1)),
                               ("bl",(r2+1,c1-1)),("br",(r2+1,c2+1))]:
            if cr < 0 or cr >= h or cc < 0 or cc >= w:
                return None
            v = grid[cr][cc]
            if v == bg_color or v == filler:
                return None
            corners[key] = v
        return corners

    # ---- strategy: keep center column ------------------------------------

    def _try_cross_projection(self, patterns, task):
        """
        Detect: cross shapes (one arm color, different center color) on a
        uniform background. The missing arm direction determines projection.
        Center color projects every 2 cells to the grid edge, and that entire
        edge row/col becomes the center color. Corners where edges meet = 0.
        Category: directional projection from cross markers to grid edges.
        """
        if task is None or not patterns.get("grid_size_preserved"):
            return None

        pairs = task.example_pairs
        if not pairs:
            return None

        def find_crosses(grid, bg_color):
            """Find cross shapes: arm_color cells surrounding a center_color cell."""
            h, w = len(grid), len(grid[0])
            non_bg = {}
            for r in range(h):
                for c in range(w):
                    if grid[r][c] != bg_color:
                        non_bg[(r, c)] = grid[r][c]
            if not non_bg:
                return None

            # Group non-bg cells by connected components
            visited = set()
            components = []
            for pos in non_bg:
                if pos in visited:
                    continue
                comp = []
                stack = [pos]
                visited.add(pos)
                while stack:
                    p = stack.pop()
                    comp.append(p)
                    for dr, dc in [(-1,0),(1,0),(0,-1),(0,1)]:
                        np_ = (p[0]+dr, p[1]+dc)
                        if np_ in non_bg and np_ not in visited:
                            visited.add(np_)
                            stack.append(np_)
                components.append(comp)

            crosses = []
            for comp in components:
                colors_in_comp = set(non_bg[p] for p in comp)
                if len(colors_in_comp) != 2:
                    continue
                # One color should be the arm color (majority), the other is center
                color_counts = Counter(non_bg[p] for p in comp)
                arm_color, center_color = color_counts.most_common(2)[0][0], color_counts.most_common(2)[1][0]
                # Find the center cell
                center_cells = [p for p in comp if non_bg[p] == center_color]
                if len(center_cells) != 1:
                    continue
                cr, cc = center_cells[0]
                arm_cells = [p for p in comp if non_bg[p] == arm_color]

                # Check which cardinal directions have arms
                has_up = any(r < cr and c == cc for r, c in arm_cells)
                has_down = any(r > cr and c == cc for r, c in arm_cells)
                has_left = any(r == cr and c < cc for r, c in arm_cells)
                has_right = any(r == cr and c > cc for r, c in arm_cells)

                dirs = [has_up, has_down, has_left, has_right]
                if sum(dirs) != 3:
                    continue  # Need exactly one missing arm

                if not has_up:
                    missing = 'up'
                elif not has_down:
                    missing = 'down'
                elif not has_left:
                    missing = 'left'
                else:
                    missing = 'right'

                crosses.append({
                    'center': (cr, cc),
                    'center_color': center_color,
                    'arm_color': arm_color,
                    'missing': missing,
                })
            return crosses if crosses else None

        # Validate on all example pairs
        for pair in pairs:
            g_in = pair.input_grid.raw
            g_out = pair.output_grid.raw
            h, w = len(g_in), len(g_in[0])

            # Detect background per pair (most common color)
            bg = Counter(c for row in g_in for c in row).most_common(1)[0][0]

            crosses = find_crosses(g_in, bg)
            if not crosses:
                return None

            # Build expected output
            expected = [row[:] for row in g_in]

            # Track which edges are claimed by which center colors
            edge_colors = {}  # 'up'/'down'/'left'/'right' -> center_color
            projections = []

            for cross in crosses:
                cr, cc = cross['center']
                cc_color = cross['center_color']
                missing = cross['missing']
                edge_colors[missing] = cc_color

                # Project center color every 2 cells in missing direction
                if missing == 'up':
                    r = cr - 2
                    while r > 0:
                        projections.append((r, cc, cc_color))
                        r -= 2
                elif missing == 'down':
                    r = cr + 2
                    while r < h - 1:
                        projections.append((r, cc, cc_color))
                        r += 2
                elif missing == 'left':
                    c = cc - 2
                    while c > 0:
                        projections.append((cr, c, cc_color))
                        c -= 2
                elif missing == 'right':
                    c = cc + 2
                    while c < w - 1:
                        projections.append((cr, c, cc_color))
                        c += 2

            for r, c, color in projections:
                expected[r][c] = color

            # Fill edges
            for direction, color in edge_colors.items():
                if direction == 'up':
                    for c in range(w):
                        expected[0][c] = color
                elif direction == 'down':
                    for c in range(w):
                        expected[h-1][c] = color
                elif direction == 'left':
                    for r in range(h):
                        expected[r][0] = color
                elif direction == 'right':
                    for r in range(h):
                        expected[r][w-1] = color

            # Corners where edges meet become 0
            corner_dirs = {
                (0, 0): ('up', 'left'),
                (0, w-1): ('up', 'right'),
                (h-1, 0): ('down', 'left'),
                (h-1, w-1): ('down', 'right'),
            }
            for (cr_, cc_), (d1, d2) in corner_dirs.items():
                if d1 in edge_colors and d2 in edge_colors:
                    expected[cr_][cc_] = 0

            if expected != g_out:
                return None

        return {
            "type": "cross_projection",
            "confidence": 0.9,
        }

    def _try_quadrant_shape_swap(self, patterns, task):
        """
        Detect: grid divided into cells by rows/columns of 0s. Each cell has a
        background color and a foreground shape. Horizontally paired cells swap
        their shapes, drawing the swapped shape in the partner's background color.
        When both cells share the same bg, swapped shapes become invisible (blank).
        Category: cross-quadrant shape color swapping.
        """
        if task is None or not patterns.get("grid_size_preserved"):
            return None

        pairs = task.example_pairs
        if not pairs:
            return None

        def find_dividers(grid):
            """Find rows and cols that are entirely 0."""
            h, w = len(grid), len(grid[0])
            zero_rows = [r for r in range(h) if all(grid[r][c] == 0 for c in range(w))]
            zero_cols = [c for c in range(w) if all(grid[r][c] == 0 for r in range(h))]
            return zero_rows, zero_cols

        def get_sections(dividers, total):
            """Get ranges between divider lines."""
            sections = []
            prev = 0
            groups = []
            # Group consecutive dividers
            i = 0
            while i < len(dividers):
                start = dividers[i]
                end = start
                while i + 1 < len(dividers) and dividers[i+1] == end + 1:
                    i += 1
                    end = dividers[i]
                groups.append((start, end))
                i += 1
            # Sections are ranges between groups
            prev = 0
            for gs, ge in groups:
                if gs > prev:
                    sections.append((prev, gs - 1))
                prev = ge + 1
            if prev < total:
                sections.append((prev, total - 1))
            return sections

        def extract_cell(grid, r_start, r_end, c_start, c_end):
            """Extract a sub-grid."""
            return [grid[r][c_start:c_end+1] for r in range(r_start, r_end+1)]

        def cell_bg_and_shape(cell):
            """Find background color and shape pixels in a cell."""
            flat = [c for row in cell for c in row]
            if not flat:
                return None, None, None
            bg = Counter(flat).most_common(1)[0][0]
            shape_colors = set(flat) - {bg}
            if len(shape_colors) > 1:
                return None, None, None
            fg = shape_colors.pop() if shape_colors else None
            # Extract relative shape positions
            shape = set()
            if fg is not None:
                for r, row in enumerate(cell):
                    for c, v in enumerate(row):
                        if v == fg:
                            shape.add((r, c))
            return bg, fg, shape

        # Validate on all example pairs
        for pair in pairs:
            g_in = pair.input_grid.raw
            g_out = pair.output_grid.raw
            h, w = len(g_in), len(g_in[0])

            zero_rows, zero_cols = find_dividers(g_in)
            if not zero_cols:
                return None  # Need at least vertical dividers for horizontal pairing

            row_sections = get_sections(zero_rows, h)
            col_sections = get_sections(zero_cols, w)

            if len(col_sections) % 2 != 0:
                return None  # Need even number of column sections for pairing

            # Build expected output
            expected = [row[:] for row in g_in]

            for rs, re in row_sections:
                # Pair columns left-to-right: (0,1), (2,3), ...
                for ci in range(0, len(col_sections), 2):
                    if ci + 1 >= len(col_sections):
                        return None
                    cs_l, ce_l = col_sections[ci]
                    cs_r, ce_r = col_sections[ci + 1]

                    cell_l = extract_cell(g_in, rs, re, cs_l, ce_l)
                    cell_r = extract_cell(g_in, rs, re, cs_r, ce_r)

                    bg_l, fg_l, shape_l = cell_bg_and_shape(cell_l)
                    bg_r, fg_r, shape_r = cell_bg_and_shape(cell_r)

                    if bg_l is None or bg_r is None:
                        return None

                    # Left cell gets right's shape in right's bg color
                    cell_h = re - rs + 1
                    cell_w_l = ce_l - cs_l + 1
                    cell_w_r = ce_r - cs_r + 1

                    # Clear left cell to its bg, then draw right's shape
                    for r in range(cell_h):
                        for c in range(cell_w_l):
                            expected[rs + r][cs_l + c] = bg_l
                    if shape_r and cell_w_l == cell_w_r:
                        for (sr, sc) in shape_r:
                            if 0 <= sr < cell_h and 0 <= sc < cell_w_l:
                                expected[rs + sr][cs_l + sc] = bg_r

                    # Clear right cell to its bg, then draw left's shape
                    for r in range(cell_h):
                        for c in range(cell_w_r):
                            expected[rs + r][cs_r + c] = bg_r
                    if shape_l and cell_w_l == cell_w_r:
                        for (sr, sc) in shape_l:
                            if 0 <= sr < cell_h and 0 <= sc < cell_w_r:
                                expected[rs + sr][cs_r + sc] = bg_l

            if expected != g_out:
                return None

        return {
            "type": "quadrant_shape_swap",
            "confidence": 0.9,
        }

    def _try_keep_center_column(self, patterns, task):
        """
        Detect: output is all background except the center column, which
        preserves the input values.
        Category: column extraction / projection.
        """
        if task is None:
            return None
        if not patterns.get("grid_size_preserved"):
            return None

        bg_color = None

        for pair in task.example_pairs:
            g0, g1 = pair.input_grid, pair.output_grid
            if g0 is None or g1 is None:
                return None
            raw_in = g0.raw
            raw_out = g1.raw
            h = len(raw_in)
            w = len(raw_in[0]) if raw_in else 0

            if w == 0 or h != len(raw_out) or w != (len(raw_out[0]) if raw_out else 0):
                return None

            center_col = w // 2

            # Determine bg from output (most common value)
            flat_out = [c for row in raw_out for c in row]
            pair_bg = Counter(flat_out).most_common(1)[0][0]
            if bg_color is None:
                bg_color = pair_bg
            elif bg_color != pair_bg:
                return None

            # Every non-center-column cell must be bg
            for r in range(h):
                for c in range(w):
                    if c == center_col:
                        if raw_out[r][c] != raw_in[r][c]:
                            return None
                    else:
                        if raw_out[r][c] != bg_color:
                            return None

        return {
            "type": "keep_center_column",
            "bg_color": bg_color,
            "confidence": 0.8,
        }


    # ---- strategy: L-path chain ------------------------------------------

    def _try_lpath_chain(self, patterns, task):
        """
        Detect: a grid with a source pixel (color S), directional waypoints
        (two distinct colors D and U), and background. The output draws an
        L-shaped chain of S-colored pixels connecting waypoints.
        D-waypoints cause downward turns, U-waypoints cause upward turns.
        Category: L-path routing / zigzag connector tasks.
        """
        if task is None:
            return None

        for pair in task.example_pairs:
            g0, g1 = pair.input_grid, pair.output_grid
            if g0 is None or g1 is None:
                return None
            if len(g0.raw) != len(g1.raw) or len(g0.raw[0]) != len(g1.raw[0]):
                return None

        # Find the path color and waypoint colors across ALL pairs
        first_in = task.example_pairs[0].input_grid.raw
        bg = Counter(c for row in first_in for c in row).most_common(1)[0][0]

        # Gather all non-bg colors across all pairs
        in_colors = set()
        new_in_output = set()
        for pair in task.example_pairs:
            raw_in, raw_out = pair.input_grid.raw, pair.output_grid.raw
            h, w = len(raw_in), len(raw_in[0])
            for r in range(h):
                for c in range(w):
                    if raw_in[r][c] != bg:
                        in_colors.add(raw_in[r][c])
                    if raw_in[r][c] == bg and raw_out[r][c] != bg:
                        new_in_output.add(raw_out[r][c])

        # The path color appears in output where input was bg
        if len(new_in_output) != 1:
            return None
        path_color = new_in_output.pop()
        if path_color not in in_colors:
            return None

        # The waypoint colors are the other non-bg, non-path colors
        waypoint_colors = in_colors - {path_color}
        if len(waypoint_colors) != 2:
            return None

        # Determine which is DOWN and which is UP by simulating
        wc_list = list(waypoint_colors)
        for down_color, up_color in [(wc_list[0], wc_list[1]), (wc_list[1], wc_list[0])]:
            if self._validate_lpath(task, bg, path_color, down_color, up_color):
                return {
                    "type": "lpath_chain",
                    "bg": bg,
                    "path_color": path_color,
                    "down_color": down_color,
                    "up_color": up_color,
                    "confidence": 0.95,
                }
        return None

    def _validate_lpath(self, task, bg, path_color, down_color, up_color):
        """Validate L-path chain rule on all example pairs."""
        for pair in task.example_pairs:
            predicted = self._run_lpath(pair.input_grid.raw, bg, path_color, down_color, up_color)
            if predicted != pair.output_grid.raw:
                return False
        return True

    @staticmethod
    def _run_lpath(raw, bg, path_color, down_color, up_color):
        """Execute L-path chain algorithm on a grid."""
        h, w = len(raw), len(raw[0])
        output = [row[:] for row in raw]

        # Find the source cell (path_color in input)
        sources = [(r, c) for r in range(h) for c in range(w) if raw[r][c] == path_color]
        if len(sources) != 1:
            return output
        sr, sc = sources[0]

        # Build waypoint sets
        waypoints = set()
        for r in range(h):
            for c in range(w):
                if raw[r][c] in (down_color, up_color):
                    waypoints.add((r, c))

        # Trace path
        cr, cc = sr, sc
        direction = "right"
        max_steps = h * w  # safety limit

        for _ in range(max_steps):
            if direction == "right":
                # Find nearest waypoint on this row to the right
                target_col = None
                for wc_pos in sorted(waypoints, key=lambda p: p[1]):
                    if wc_pos[0] == cr and wc_pos[1] > cc:
                        target_col = wc_pos[1]
                        break
                if target_col is not None:
                    # Fill from cc+1 to target_col-1
                    for c in range(cc + 1, target_col):
                        output[cr][c] = path_color
                    cc = target_col - 1
                    wp_color = raw[cr][target_col]
                    direction = "down" if wp_color == down_color else "up"
                else:
                    # Fill to right edge
                    for c in range(cc + 1, w):
                        output[cr][c] = path_color
                    break

            elif direction == "up":
                # Find nearest waypoint in this column above
                target_row = None
                for wr, wc_c in sorted(waypoints, key=lambda p: -p[0]):
                    if wc_c == cc and wr < cr:
                        target_row = wr
                        break
                if target_row is not None:
                    for r in range(cr - 1, target_row, -1):
                        output[r][cc] = path_color
                    cr = target_row + 1
                    direction = "right"
                else:
                    for r in range(cr - 1, -1, -1):
                        output[r][cc] = path_color
                    break

            elif direction == "down":
                # Find nearest waypoint in this column below
                target_row = None
                for wr, wc_c in sorted(waypoints, key=lambda p: p[0]):
                    if wc_c == cc and wr > cr:
                        target_row = wr
                        break
                if target_row is not None:
                    for r in range(cr + 1, target_row):
                        output[r][cc] = path_color
                    cr = target_row - 1
                    direction = "right"
                else:
                    for r in range(cr + 1, h):
                        output[r][cc] = path_color
                    break

        return output

    # ---- strategy: arrow chain mirror -------------------------------------

    def _try_arrow_chain_mirror(self, patterns, task):
        """
        Detect: grid split by a separator row (all one color). Bottom half
        has 'dot' pixels and 'arrow' pixels. Each dot follows its adjacent
        chain of arrows to the end position. Top half mirrors the final
        dot positions across the separator.
        Category: separator + directional chain + mirror tasks.
        """
        if task is None:
            return None

        for pair in task.example_pairs:
            g0, g1 = pair.input_grid, pair.output_grid
            if g0 is None or g1 is None:
                return None
            if len(g0.raw) != len(g1.raw) or len(g0.raw[0]) != len(g1.raw[0]):
                return None

        first_in = task.example_pairs[0].input_grid.raw
        h, w = len(first_in), len(first_in[0])
        bg = Counter(c for row in first_in for c in row).most_common(1)[0][0]

        # Find separator row (all same non-bg color)
        sep_row = None
        sep_color = None
        for r in range(h):
            row_vals = set(first_in[r])
            if len(row_vals) == 1 and first_in[r][0] != bg:
                sep_row = r
                sep_color = first_in[r][0]
                break
        if sep_row is None:
            return None

        # Identify colors in top and bottom halves
        top_colors = set()
        bot_colors = set()
        for r in range(h):
            for c in range(w):
                v = first_in[r][c]
                if v == bg or v == sep_color:
                    continue
                if r < sep_row:
                    top_colors.add(v)
                elif r > sep_row:
                    bot_colors.add(v)

        if len(top_colors) != 1 or len(bot_colors) != 2:
            return None

        top_color = top_colors.pop()
        bot_list = list(bot_colors)

        # Determine which is dot_color and which is arrow_color
        for dot_color, arrow_color in [(bot_list[0], bot_list[1]), (bot_list[1], bot_list[0])]:
            if self._validate_arrow_mirror(task, bg, sep_color, sep_row, top_color, dot_color, arrow_color):
                return {
                    "type": "arrow_chain_mirror",
                    "bg": bg,
                    "sep_color": sep_color,
                    "top_color": top_color,
                    "dot_color": dot_color,
                    "arrow_color": arrow_color,
                    "confidence": 0.95,
                }
        return None

    def _validate_arrow_mirror(self, task, bg, sep_color, sep_row_ref, top_color, dot_color, arrow_color):
        """Validate arrow chain mirror rule on all example pairs."""
        for pair in task.example_pairs:
            raw = pair.input_grid.raw
            h, w = len(raw), len(raw[0])

            # Find separator row in this pair
            sep_row = None
            for r in range(h):
                if all(raw[r][c] == sep_color for c in range(w)):
                    sep_row = r
                    break
            if sep_row is None:
                return False

            predicted = self._run_arrow_mirror(raw, bg, sep_color, sep_row, top_color, dot_color, arrow_color)
            if predicted != pair.output_grid.raw:
                return False
        return True

    @staticmethod
    def _run_arrow_mirror(raw, bg, sep_color, sep_row, top_color, dot_color, arrow_color):
        """Execute arrow chain mirror algorithm."""
        h, w = len(raw), len(raw[0])
        output = [row[:] for row in raw]

        # Clear top half (except separator)
        for r in range(sep_row):
            for c in range(w):
                if output[r][c] != sep_color:
                    output[r][c] = bg

        # Find dots and arrows in bottom half
        dots = []
        arrows = set()
        for r in range(sep_row + 1, h):
            for c in range(w):
                if raw[r][c] == dot_color:
                    dots.append((r, c))
                elif raw[r][c] == arrow_color:
                    arrows.add((r, c))

        # Clear bottom half
        for r in range(sep_row + 1, h):
            for c in range(w):
                if output[r][c] != sep_color:
                    output[r][c] = bg

        # For each dot, follow the arrow chain
        new_dot_positions = []
        for dr, dc in dots:
            # Find adjacent arrow
            best_pos = (dr, dc)  # fallback: stay
            for ddr, ddc in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                nr, nc = dr + ddr, dc + ddc
                if (nr, nc) in arrows:
                    # Follow chain in this direction
                    cur_r, cur_c = nr, nc
                    while (cur_r, cur_c) in arrows:
                        next_r, next_c = cur_r + ddr, cur_c + ddc
                        if (next_r, next_c) in arrows:
                            cur_r, cur_c = next_r, next_c
                        else:
                            break
                    best_pos = (cur_r, cur_c)
                    break
            new_dot_positions.append(best_pos)

        # Place dots at new positions
        for r, c in new_dot_positions:
            output[r][c] = dot_color

        # Mirror dot positions to top half
        for r, c in new_dot_positions:
            mirror_r = 2 * sep_row - r
            if 0 <= mirror_r < sep_row:
                output[mirror_r][c] = top_color

        # Keep separator
        for c in range(w):
            output[sep_row][c] = sep_color

        return output


    # ---- strategy: template reconstruct -----------------------------------

    def _try_template_reconstruct(self, patterns, task):
        """
        Detect: input has template shapes (multi-colour connected components
        with a body colour and endpoint colours) plus isolated marker pixels.
        Output removes templates and draws D4-transformed copies at markers.

        Category: template-to-marker reconstruction with rotation/reflection.
        """
        for pair in task.example_pairs:
            g0, g1 = pair.input_grid, pair.output_grid
            if g0 is None or g1 is None:
                return None
            if g0.height != g1.height or g0.width != g1.width:
                return None
            result = _template_reconstruct_transform(g0.raw)
            if result is None or result != g1.raw:
                return None
        return {"type": "template_reconstruct", "confidence": 1.0}

    # ---- strategy: block grid gravity ------------------------------------

    def _try_block_grid_gravity(self, patterns, task):
        """
        Detect: large grid with 3x3 hollow-square blocks on a 4-cell grid.
        One edge has a line of 1s (border). Output is a compressed block-color
        grid with gravity applied perpendicular to the border direction.

        Category: block-grid summarisation with directional compaction.
        """
        if patterns.get("grid_size_preserved"):
            return None

        for pair in task.example_pairs:
            g0, g1 = pair.input_grid, pair.output_grid
            if g0 is None or g1 is None:
                return None
            if g0.height < 20 or g0.width < 20:
                return None

        # Validate on every training pair
        for pair in task.example_pairs:
            raw = pair.input_grid.raw
            h, w = len(raw), len(raw[0])
            result = _block_grid_gravity_transform(raw, h, w)
            if result is None:
                return None
            if result != pair.output_grid.raw:
                return None

        return {"type": "block_grid_gravity", "confidence": 1.0}

    # ---- strategy: scatter count X-diamond --------------------------------

    def _try_scatter_count_x(self, patterns, task):
        """
        Detect: input has background + exactly 2 scattered non-bg colors (all
        single pixels). Output is a fixed-size grid (consistent across pairs)
        with background everywhere except a rectangle anchored at the
        bottom-left corner filled with one color and an X (two crossing
        diagonals) drawn in another.
        Width = count of more-frequent scatter color,
        Height = count of less-frequent scatter color.
        Category: scatter-pixel counting → geometric shape output.
        """
        if task is None:
            return None

        fill_color = None
        diag_color = None
        bg_color = None
        out_h = None
        out_w = None

        for pair in task.example_pairs:
            g0, g1 = pair.input_grid, pair.output_grid
            if g0 is None or g1 is None:
                return None
            raw_in = g0.raw
            raw_out = g1.raw
            h = len(raw_in)
            w = len(raw_in[0]) if raw_in else 0
            oh = len(raw_out)
            ow = len(raw_out[0]) if raw_out else 0

            # Output size must be consistent across pairs
            if out_h is None:
                out_h, out_w = oh, ow
            elif oh != out_h or ow != out_w:
                return None

            # Input must have exactly 3 colors: bg + 2 scatter colors
            in_counts = Counter(c for row in raw_in for c in row)
            if len(in_counts) != 3:
                return None

            bg = in_counts.most_common(1)[0][0]
            scatter_colors = [c for c in in_counts if c != bg]

            # All scatter pixels must be single (not touching same color)
            for sc in scatter_colors:
                positions = [(r, c) for r in range(h) for c in range(w)
                             if raw_in[r][c] == sc]
                for r, c in positions:
                    for dr, dc in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                        nr, nc = r + dr, c + dc
                        if 0 <= nr < h and 0 <= nc < w and raw_in[nr][nc] == sc:
                            return None

            cnt_a = in_counts[scatter_colors[0]]
            cnt_b = in_counts[scatter_colors[1]]
            rect_w = max(cnt_a, cnt_b)
            rect_h = min(cnt_a, cnt_b)

            # Output must have exactly 3 colors: bg + fill + diagonal
            out_counts = Counter(c for row in raw_out for c in row)
            non_bg_out = [c for c in out_counts if c != bg]
            if len(non_bg_out) != 2:
                return None

            # Identify fill (more frequent non-bg) and diagonal (less frequent)
            non_bg_sorted = sorted(non_bg_out, key=lambda c: out_counts[c], reverse=True)
            pair_fill = non_bg_sorted[0]
            pair_diag = non_bg_sorted[1]

            if fill_color is None:
                fill_color = pair_fill
                diag_color = pair_diag
                bg_color = bg
            else:
                if pair_fill != fill_color or pair_diag != diag_color or bg != bg_color:
                    return None

            # Verify the output rectangle region and X pattern
            expected = _build_scatter_x_grid(oh, ow, rect_h, rect_w,
                                             bg, fill_color, diag_color)
            if expected != raw_out:
                return None

        return {
            "type": "scatter_count_x",
            "bg_color": bg_color,
            "fill_color": fill_color,
            "diag_color": diag_color,
            "out_h": out_h,
            "out_w": out_w,
            "confidence": 1.0,
        }

    # ---- strategy: rotation tiling ----------------------------------------

    def _try_rotation_tiling(self, patterns, task):
        """
        Detect: NxN input → 2Nx2N output composed of 4 rotations of the input.
        Layout: top-left = original, top-right = 270° CW, bottom-left = 180°,
        bottom-right = 90° CW.
        Category: rotation tiling / symmetry expansion tasks.
        """
        if task is None:
            return None
        pairs = task.example_pairs
        if not pairs:
            return None

        for pair in pairs:
            ig = pair.input_grid.raw
            og = pair.output_grid.raw
            ih, iw = len(ig), len(ig[0])
            oh, ow = len(og), len(og[0])
            if oh != 2 * ih or ow != 2 * iw:
                return None
            if ih != iw:
                return None
            n = ih

            def rot90(grid, n):
                return [[grid[n - 1 - c][r] for c in range(n)] for r in range(n)]

            def rot180(grid, n):
                return [[grid[n - 1 - r][n - 1 - c] for c in range(n)] for r in range(n)]

            def rot270(grid, n):
                return [[grid[c][n - 1 - r] for c in range(n)] for r in range(n)]

            r0 = ig
            r90 = rot90(ig, n)
            r180 = rot180(ig, n)
            r270 = rot270(ig, n)

            # Check layout: TL=original, TR=rot270, BL=rot180, BR=rot90
            ok = True
            for r in range(n):
                for c in range(n):
                    if og[r][c] != r0[r][c]:
                        ok = False; break
                    if og[r][n + c] != r270[r][c]:
                        ok = False; break
                    if og[n + r][c] != r180[r][c]:
                        ok = False; break
                    if og[n + r][n + c] != r90[r][c]:
                        ok = False; break
                if not ok:
                    break
            if not ok:
                return None

        return {"type": "rotation_tiling", "confidence": 1.0}

    # ---- strategy: rectangle interior count --------------------------------

    def _try_rectangle_interior_count(self, patterns, task):
        """
        Detect: input has a rectangle bordered by 1s. Inside, some cells have
        a non-0/non-1 color. Outside, scattered pixels of the same color.
        Output is a small grid (consistent size across pairs) filled
        left-to-right, top-to-bottom with the count of colored interior pixels.
        Category: count-inside-rectangle → summary grid tasks.
        """
        if task is None:
            return None
        pairs = task.example_pairs
        if not pairs:
            return None

        out_h = None
        out_w = None

        for pair in pairs:
            ig = pair.input_grid.raw
            og = pair.output_grid.raw
            oh, ow = len(og), len(og[0])

            rect = self._find_one_rectangle(ig)
            if rect is None:
                return None
            r1, c1, r2, c2 = rect

            color = None
            count = 0
            for r in range(r1 + 1, r2):
                for c in range(c1 + 1, c2):
                    if ig[r][c] != 0:
                        if color is None:
                            color = ig[r][c]
                        elif ig[r][c] != color:
                            return None
                        count += 1

            if color is None:
                return None

            if out_h is None:
                out_h, out_w = oh, ow
            elif (oh, ow) != (out_h, out_w):
                return None

            filled = 0
            for r in range(oh):
                for c in range(ow):
                    idx = r * ow + c
                    if idx < count:
                        if og[r][c] != color:
                            return None
                        filled += 1
                    else:
                        if og[r][c] != 0:
                            return None

            if filled != count:
                return None

        return {
            "type": "rectangle_interior_count",
            "out_h": out_h,
            "out_w": out_w,
            "confidence": 1.0,
        }

    def _find_one_rectangle(self, grid):
        """Find a rectangle of 1s (border) in the grid. Returns (r1,c1,r2,c2) or None."""
        h, w = len(grid), len(grid[0])
        ones = [(r, c) for r in range(h) for c in range(w) if grid[r][c] == 1]
        if not ones:
            return None
        r_min = min(r for r, c in ones)
        r_max = max(r for r, c in ones)
        c_min = min(c for r, c in ones)
        c_max = max(c for r, c in ones)
        for c in range(c_min, c_max + 1):
            if grid[r_min][c] != 1 or grid[r_max][c] != 1:
                return None
        for r in range(r_min, r_max + 1):
            if grid[r][c_min] != 1 or grid[r][c_max] != 1:
                return None
        return (r_min, c_min, r_max, c_max)

    # ---- strategy: pattern tile fill ---------------------------------------

    def _try_pattern_tile_fill(self, patterns, task):
        """
        Detect: grid has a region of uniform background and a pattern region.
        The pattern tiles cyclically upward to fill the blank region.
        Category: pattern repetition / tile-fill tasks.
        """
        if task is None:
            return None
        pairs = task.example_pairs
        if not pairs:
            return None

        for pair in pairs:
            ig = pair.input_grid.raw
            og = pair.output_grid.raw
            h, w = len(ig), len(ig[0])
            oh, ow = len(og), len(og[0])
            if (oh, ow) != (h, w):
                return None

            from collections import Counter
            counts = Counter(c for row in ig for c in row)
            bg = counts.most_common(1)[0][0]

            pattern_rows = []
            blank_rows = []
            for r in range(h):
                if all(ig[r][c] == bg for c in range(w)):
                    blank_rows.append(r)
                else:
                    pattern_rows.append(r)

            if not pattern_rows or not blank_rows:
                return None

            pr_min, pr_max = min(pattern_rows), max(pattern_rows)
            if list(range(pr_min, pr_max + 1)) != pattern_rows:
                return None

            if pr_max != h - 1 and pr_min != 0:
                return None

            pat_len = len(pattern_rows)
            pat = [ig[r] for r in pattern_rows]

            for r in range(h):
                if pr_max == h - 1:
                    dist_from_bottom = h - 1 - r
                    cycle_row = pat[pat_len - 1 - (dist_from_bottom % pat_len)]
                else:
                    dist_from_top = r
                    cycle_row = pat[dist_from_top % pat_len]

                if og[r] != cycle_row:
                    return None

        return {"type": "pattern_tile_fill", "confidence": 1.0}


def _marker_arm_extend_transform(raw):
    """
    Transform for marker-arm-extend tasks.
    Finds rectangular blocks on a uniform background, finds isolated
    single-pixel markers of the same colour, then for each marker draws
    an arm from the nearest rect edge with cross-shaped endpoints.
    """
    from collections import Counter

    h = len(raw)
    w = len(raw[0]) if raw else 0
    if h == 0 or w == 0:
        return None

    counts = Counter(c for row in raw for c in row)
    bg = counts.most_common(1)[0][0]

    # Find connected components of non-bg cells (4-connected)
    visited = [[False] * w for _ in range(h)]
    components = []
    for r in range(h):
        for c in range(w):
            if raw[r][c] != bg and not visited[r][c]:
                comp = []
                color = raw[r][c]
                q = [(r, c)]
                visited[r][c] = True
                while q:
                    cr, cc = q.pop(0)
                    comp.append((cr, cc))
                    for dr, dc in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                        nr, nc = cr + dr, cc + dc
                        if 0 <= nr < h and 0 <= nc < w and not visited[nr][nc] and raw[nr][nc] == color:
                            visited[nr][nc] = True
                            q.append((nr, nc))
                components.append((color, comp))

    if not components:
        return None

    # Classify: rectangles (size > 1, actually rectangular) vs markers (size == 1)
    rects = []
    markers = []
    for color, comp in components:
        if len(comp) == 1:
            markers.append((comp[0][0], comp[0][1], color))
        else:
            rows = [r for r, c in comp]
            cols = [c for r, c in comp]
            r0, r1 = min(rows), max(rows)
            c0, c1 = min(cols), max(cols)
            if len(comp) == (r1 - r0 + 1) * (c1 - c0 + 1):
                rects.append((r0, r1, c0, c1, color))

    if not rects or not markers:
        return None

    out = [row[:] for row in raw]

    for mr, mc, mcolor in markers:
        # Find the rectangle of the same colour
        best_rect = None
        best_dist = float('inf')
        for r0, r1, c0, c1, rcolor in rects:
            if rcolor != mcolor:
                continue
            # Distance from marker to rect bounding box
            dr = max(r0 - mr, 0, mr - r1)
            dc = max(c0 - mc, 0, mc - c1)
            dist = dr + dc
            if dist < best_dist:
                best_dist = dist
                best_rect = (r0, r1, c0, c1)

        if best_rect is None:
            continue

        r0, r1, c0, c1 = best_rect

        # Determine which edge is nearest and the arm direction
        # Marker must be outside the rect
        if r0 <= mr <= r1 and c0 <= mc <= c1:
            continue  # marker inside rect, skip

        # Check if marker is aligned with rect rows or cols
        in_row_range = r0 <= mr <= r1
        in_col_range = c0 <= mc <= c1

        if in_col_range and not in_row_range:
            # Vertical arm (marker above or below rect)
            if mr < r0:
                # Marker above, arm goes up from top edge
                arm_start = r0 - 1
                arm_end = mr + 1  # stop one past marker (toward rect)
                past_marker = mr - 1
                # Draw arm
                for ar in range(arm_end, arm_start + 1):
                    out[ar][mc] = mcolor
                # Cross at arm start (adjacent to rect)
                if 0 <= mc - 1:
                    out[arm_start][mc - 1] = mcolor
                if mc + 1 < w:
                    out[arm_start][mc + 1] = mcolor
                # Cross at marker
                out[mr][mc] = bg  # marker position becomes bg
                if 0 <= mc - 1:
                    out[mr][mc - 1] = mcolor
                if mc + 1 < w:
                    out[mr][mc + 1] = mcolor
                # One past marker
                if 0 <= past_marker:
                    out[past_marker][mc] = mcolor
            else:
                # Marker below, arm goes down from bottom edge
                arm_start = r1 + 1
                arm_end = mr - 1
                past_marker = mr + 1
                for ar in range(arm_start, arm_end + 1):
                    out[ar][mc] = mcolor
                if 0 <= mc - 1:
                    out[arm_start][mc - 1] = mcolor
                if mc + 1 < w:
                    out[arm_start][mc + 1] = mcolor
                out[mr][mc] = bg
                if 0 <= mc - 1:
                    out[mr][mc - 1] = mcolor
                if mc + 1 < w:
                    out[mr][mc + 1] = mcolor
                if past_marker < h:
                    out[past_marker][mc] = mcolor

        elif in_row_range and not in_col_range:
            # Horizontal arm (marker left or right of rect)
            if mc < c0:
                # Marker to the left
                arm_start = c0 - 1
                arm_end = mc + 1
                past_marker = mc - 1
                for ac in range(arm_end, arm_start + 1):
                    out[mr][ac] = mcolor
                if 0 <= mr - 1:
                    out[mr - 1][arm_start] = mcolor
                if mr + 1 < h:
                    out[mr + 1][arm_start] = mcolor
                out[mr][mc] = bg
                if 0 <= mr - 1:
                    out[mr - 1][mc] = mcolor
                if mr + 1 < h:
                    out[mr + 1][mc] = mcolor
                if 0 <= past_marker:
                    out[mr][past_marker] = mcolor
            else:
                # Marker to the right
                arm_start = c1 + 1
                arm_end = mc - 1
                past_marker = mc + 1
                for ac in range(arm_start, arm_end + 1):
                    out[mr][ac] = mcolor
                if 0 <= mr - 1:
                    out[mr - 1][arm_start] = mcolor
                if mr + 1 < h:
                    out[mr + 1][arm_start] = mcolor
                out[mr][mc] = bg
                if 0 <= mr - 1:
                    out[mr - 1][mc] = mcolor
                if mr + 1 < h:
                    out[mr + 1][mc] = mcolor
                if past_marker < w:
                    out[mr][past_marker] = mcolor

        else:
            # Diagonal marker (not aligned) — skip
            continue

    return out


def _subgrid_invert_transform(raw):
    """
    Transform for subgrid-invert tasks.
    Grid is divided by 0-separator rows/cols into sub-grids.
    Each sub-grid is either a pattern template or uniform fill.
    Colour 5 may be noise.  Output swaps pattern↔uniform.
    """
    from collections import Counter

    h = len(raw)
    w = len(raw[0]) if raw else 0
    if h == 0 or w == 0:
        return None

    # Find separator rows (all 0 or all {0,5})
    sep_rows = []
    for r in range(h):
        if all(raw[r][c] in (0, 5) for c in range(w)):
            sep_rows.append(r)

    sep_cols = []
    for c in range(w):
        if all(raw[r][c] in (0, 5) for r in range(h)):
            sep_cols.append(c)

    if not sep_rows and not sep_cols:
        return None

    # Build row and col ranges for sub-grids
    row_ranges = []
    prev = 0
    for sr in sep_rows:
        if sr > prev:
            row_ranges.append((prev, sr))
        prev = sr + 1
    if prev < h:
        row_ranges.append((prev, h))

    col_ranges = []
    prev = 0
    for sc in sep_cols:
        if sc > prev:
            col_ranges.append((prev, sc))
        prev = sc + 1
    if prev < w:
        col_ranges.append((prev, w))

    if not row_ranges or not col_ranges:
        return None

    # All sub-grids must be same size
    sg_h = row_ranges[0][1] - row_ranges[0][0]
    sg_w = col_ranges[0][1] - col_ranges[0][0]
    for rr in row_ranges:
        if rr[1] - rr[0] != sg_h:
            return None
    for cr in col_ranges:
        if cr[1] - cr[0] != sg_w:
            return None

    num_r = len(row_ranges)
    num_c = len(col_ranges)

    # Extract sub-grids, replacing 5 with None (unknown)
    subgrids = {}
    for ri, (r0, r1) in enumerate(row_ranges):
        for ci, (c0, c1) in enumerate(col_ranges):
            sg = []
            for r in range(r0, r1):
                row = []
                for c in range(c0, c1):
                    v = raw[r][c]
                    row.append(None if v == 5 else v)
                sg.append(row)
            subgrids[(ri, ci)] = sg

    # Find the template pattern from the cleanest sub-grid
    # (the one with the most non-None cells and at least 2 distinct colours)
    best_template = None
    best_count = -1

    for sg in subgrids.values():
        vals = set()
        count = 0
        for row in sg:
            for v in row:
                if v is not None:
                    vals.add(v)
                    count += 1
        if len(vals) >= 2 and count > best_count:
            best_count = count
            best_template = sg

    if best_template is None:
        return None

    # Reconstruct the clean template: merge non-None cells from all multi-colour sub-grids
    template = [row[:] for row in best_template]
    for sg in subgrids.values():
        vals = set(v for row in sg for v in row if v is not None)
        if len(vals) < 2:
            continue
        for r in range(sg_h):
            for c in range(sg_w):
                if template[r][c] is None and sg[r][c] is not None:
                    template[r][c] = sg[r][c]

    # If template still has None, cannot proceed
    if any(v is None for row in template for v in row):
        return None

    # Determine majority colour (used for uniform fill in output)
    tcounts = Counter(v for row in template for v in row)
    majority_color = tcounts.most_common(1)[0][0]
    # Minority colour = the colour used for uniform sub-grids in input
    minority_color = tcounts.most_common()[-1][0]

    # Classify each sub-grid: uniform (minority-filled) vs pattern
    # In the input, uniform sub-grids are filled with the minority colour.
    # If all non-None cells in a sub-grid equal the minority colour → uniform.
    # Otherwise → pattern (the non-None cells should match the template).
    is_pattern = {}
    for (ri, ci), sg in subgrids.items():
        non_none_vals = [v for row in sg for v in row if v is not None]
        if not non_none_vals:
            # Fully corrupted — heuristic: check if majority of template cells
            # at these positions would be minority
            is_pattern[(ri, ci)] = True  # default to pattern
        elif all(v == minority_color for v in non_none_vals):
            is_pattern[(ri, ci)] = False  # uniform
        else:
            is_pattern[(ri, ci)] = True   # pattern

    # Build output: invert pattern↔uniform
    out = [[0] * w for _ in range(h)]

    # Fill separator rows and cols with 0
    for r in sep_rows:
        for c in range(w):
            out[r][c] = 0
    for c in sep_cols:
        for r in range(h):
            out[r][c] = 0

    # Fill sub-grids
    for ri, (r0, r1) in enumerate(row_ranges):
        for ci, (c0, c1) in enumerate(col_ranges):
            was_pattern = is_pattern.get((ri, ci), False)
            for r in range(sg_h):
                for c in range(sg_w):
                    if was_pattern:
                        # Was pattern → becomes uniform (majority colour)
                        out[r0 + r][c0 + c] = majority_color
                    else:
                        # Was uniform → becomes pattern
                        out[r0 + r][c0 + c] = template[r][c]

    return out


def _build_scatter_x_grid(grid_h, grid_w, rect_h, rect_w, bg, fill, diag):
    """Build output grid with X-diamond in bottom-left rectangle."""
    if rect_h > grid_h or rect_w > grid_w or rect_h <= 0 or rect_w <= 0:
        return None
    out = [[bg] * grid_w for _ in range(grid_h)]
    start_row = grid_h - rect_h
    for r in range(rect_h):
        for c in range(rect_w):
            out[start_row + r][c] = fill
    for i in range(rect_h):
        grid_r = grid_h - 1 - i
        col_left = i
        col_right = rect_w - 1 - i
        out[grid_r][col_left] = diag
        out[grid_r][col_right] = diag
    return out


# D4 symmetry transforms: (r,c) -> transformed (r,c)
_D4 = [
    lambda r, c: (r, c),       # identity
    lambda r, c: (c, -r),      # 90 CW
    lambda r, c: (-r, -c),     # 180
    lambda r, c: (-c, r),      # 90 CCW
    lambda r, c: (r, -c),      # h-flip
    lambda r, c: (-r, c),      # v-flip
    lambda r, c: (c, r),       # main diagonal
    lambda r, c: (-c, -r),     # anti-diagonal
]


def _template_reconstruct_transform(raw):
    """
    Given a grid with template shapes and marker pixels, find the D4
    transform mapping each template onto its marker group and draw the
    result on a blank grid.
    """
    h = len(raw)
    w = len(raw[0]) if raw else 0
    if h == 0 or w == 0:
        return None

    # --- find 4-connected components of non-zero cells ---
    visited = [[False] * w for _ in range(h)]
    components = []
    for r in range(h):
        for c in range(w):
            if raw[r][c] != 0 and not visited[r][c]:
                comp = []
                q = [(r, c)]
                visited[r][c] = True
                while q:
                    cr, cc = q.pop(0)
                    comp.append((cr, cc))
                    for dr, dc in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                        nr, nc = cr + dr, cc + dc
                        if 0 <= nr < h and 0 <= nc < w and not visited[nr][nc] and raw[nr][nc] != 0:
                            visited[nr][nc] = True
                            q.append((nr, nc))
                components.append(comp)

    templates = []
    marker_list = []
    for comp in components:
        if len(comp) == 1:
            r, c = comp[0]
            marker_list.append((r, c, raw[r][c]))
        elif len(comp) > 3:
            templates.append(comp)

    if not templates or not marker_list:
        return None

    # --- parse each template ---
    tpl_data = []
    for comp in templates:
        cc = {}
        for r, c in comp:
            v = raw[r][c]
            cc[v] = cc.get(v, 0) + 1
        body = max(cc, key=cc.get)
        eps = {}
        for r, c in comp:
            v = raw[r][c]
            if v != body:
                if v in eps:
                    return None
                eps[v] = (r, c)
        if len(eps) < 2:
            return None
        ep_colors = sorted(eps.keys())
        ref = ep_colors[0]
        rr, rc = eps[ref]
        rel = [(r - rr, c - rc, raw[r][c]) for r, c in comp]
        rel_eps = {v: (r - rr, c - rc) for v, (r, c) in eps.items() if v != ref}
        tpl_data.append({
            'rel': rel, 'body': body, 'ep_colors': ep_colors,
            'ref': ref, 'rel_eps': rel_eps,
        })

    ep_set = frozenset(tpl_data[0]['ep_colors'])
    if any(frozenset(t['ep_colors']) != ep_set for t in tpl_data):
        return None

    ep_colors = tpl_data[0]['ep_colors']
    ref_color = ep_colors[0]
    non_ref = [c for c in ep_colors if c != ref_color]

    mbc = {}
    for r, c, v in marker_list:
        if v in ep_set:
            mbc.setdefault(v, []).append((r, c))

    for v in ep_colors:
        if v not in mbc:
            return None

    ng = len(mbc[ref_color])
    if ng != len(templates):
        return None
    for v in ep_colors:
        if len(mbc[v]) != ng:
            return None

    # --- match templates to marker groups via D4 transforms ---
    ref_markers = mbc[ref_color]
    non_ref_perms = [list(permutations(mbc[c])) for c in non_ref]

    for combo in product(*non_ref_perms):
        groups = []
        for j in range(ng):
            g = {ref_color: ref_markers[j]}
            for i, c in enumerate(non_ref):
                g[c] = combo[i][j]
            groups.append(g)

        for tperm in permutations(range(ng)):
            assignment = []
            ok = True
            for gidx in range(ng):
                tidx = tperm[gidx]
                td = tpl_data[tidx]
                mg_ref = groups[gidx][ref_color]
                mg_rel = {}
                for cv in non_ref:
                    pr, pc = groups[gidx][cv]
                    mg_rel[cv] = (pr - mg_ref[0], pc - mg_ref[1])

                found = None
                for di, tf in enumerate(_D4):
                    if all(tf(*td['rel_eps'][cv]) == mg_rel[cv] for cv in non_ref):
                        found = di
                        break
                if found is None:
                    ok = False
                    break
                assignment.append((tidx, gidx, found))

            if ok:
                result = [[0] * w for _ in range(h)]
                for tidx, gidx, di in assignment:
                    td = tpl_data[tidx]
                    mg_ref = groups[gidx][ref_color]
                    tf = _D4[di]
                    for dr, dc, color in td['rel']:
                        tr, tc = tf(dr, dc)
                        nr, nc = mg_ref[0] + tr, mg_ref[1] + tc
                        if 0 <= nr < h and 0 <= nc < w:
                            result[nr][nc] = color
                return result

    return None


def _find_block_border(raw, h, w):
    """Find which edge of a grid has a solid line of 1s."""
    if all(raw[0][c] == 1 for c in range(w)):
        return "top"
    if all(raw[h - 1][c] == 1 for c in range(w)):
        return "bottom"
    if all(raw[r][0] == 1 for r in range(h)):
        return "left"
    if all(raw[r][w - 1] == 1 for r in range(h)):
        return "right"
    return None


def _parse_block_grid(raw, h, w, border):
    """
    Parse a grid of 3x3 hollow-square blocks spaced 4 cells apart.
    Returns a 2-D list of block colours (0 where no block exists).
    """
    # Block start offsets depend on which edge the border occupies.
    if border == "top":
        row_start, col_start = 2, 1
    elif border == "bottom":
        row_start, col_start = 1, 1
    elif border == "left":
        row_start, col_start = 1, 2
    else:  # right
        row_start, col_start = 1, 1

    row_positions = list(range(row_start, h - 2, 4))
    col_positions = list(range(col_start, w - 2, 4))

    if not row_positions or not col_positions:
        return None

    grid = []
    for br in row_positions:
        row = []
        for bc in col_positions:
            color = raw[br][bc]
            if color != 0 and raw[br + 1][bc + 1] == 0:
                row.append(color)
            else:
                row.append(0)
        grid.append(row)
    return grid


def _block_grid_gravity_transform(raw, h, w):
    """Full transform: parse blocks, remove separators, apply gravity."""
    border = _find_block_border(raw, h, w)
    if border is None:
        return None

    block_grid = _parse_block_grid(raw, h, w, border)
    if block_grid is None:
        return None

    rows = len(block_grid)
    cols = len(block_grid[0])

    # Remove all-zero rows and columns (separators)
    zero_rows = {r for r in range(rows)
                 if all(block_grid[r][c] == 0 for c in range(cols))}
    zero_cols = {c for c in range(cols)
                 if all(block_grid[r][c] == 0 for r in range(rows))}

    kept_rows = [r for r in range(rows) if r not in zero_rows]
    kept_cols = [c for c in range(cols) if c not in zero_cols]

    grid = [[block_grid[r][c] for c in kept_cols] for r in kept_rows]

    num_rows = len(grid)
    num_cols = len(grid[0]) if grid else 0

    if num_rows == 0 or num_cols == 0:
        return None

    # Apply gravity perpendicular to the border
    if border in ("top", "bottom"):
        # Row-based compaction
        result = []
        for row in grid:
            nz = [v for v in row if v != 0]
            if border == "top":
                result.append([0] * (num_cols - len(nz)) + nz)
            else:
                result.append(nz + [0] * (num_cols - len(nz)))
        return result
    else:
        # Column-based compaction
        result = [[0] * num_cols for _ in range(num_rows)]
        for c in range(num_cols):
            nz = [grid[r][c] for r in range(num_rows) if grid[r][c] != 0]
            if border == "left":
                for i, v in enumerate(nz):
                    result[i][c] = v
            else:
                off = num_rows - len(nz)
                for i, v in enumerate(nz):
                    result[off + i][c] = v
        return result


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
        if rule_type == "vertical_mirror_append":
            return self._apply_vertical_mirror_append(rule, input_grid)
        if rule_type == "fill_rectangles_by_size":
            return self._apply_fill_rectangles_by_size(rule, input_grid)
        if rule_type == "keep_center_column":
            return self._apply_keep_center_column(rule, input_grid)
        if rule_type == "reverse_rings":
            return self._apply_reverse_rings(rule, input_grid)
        if rule_type == "pixel_scale":
            return self._apply_pixel_scale(rule, input_grid)
        if rule_type == "recolor_by_size":
            return self._apply_recolor_by_size(rule, input_grid)
        if rule_type == "staircase_growth":
            return self._apply_staircase_growth(rule, input_grid)
        if rule_type == "corner_fill_quadrants":
            return self._apply_corner_fill_quadrants(rule, input_grid)
        if rule_type == "gravity_slide":
            return self._apply_gravity_slide(rule, input_grid)
        if rule_type == "diamond_bridge":
            return self._apply_diamond_bridge(rule, input_grid)
        if rule_type == "stripe_zone_fill":
            return self._apply_stripe_zone_fill(rule, input_grid)
        if rule_type == "cross_projection":
            return self._apply_cross_projection(rule, input_grid)
        if rule_type == "quadrant_shape_swap":
            return self._apply_quadrant_shape_swap(rule, input_grid)
        if rule_type == "lpath_chain":
            return self._apply_lpath_chain(rule, input_grid)
        if rule_type == "arrow_chain_mirror":
            return self._apply_arrow_chain_mirror(rule, input_grid)
        if rule_type == "grid_zigzag_shear":
            return self._apply_grid_zigzag_shear(rule, input_grid)
        if rule_type == "three_shape_rearrange":
            return self._apply_three_shape_rearrange(rule, input_grid)
        if rule_type == "block_grid_gravity":
            return self._apply_block_grid_gravity(rule, input_grid)
        if rule_type == "template_reconstruct":
            return self._apply_template_reconstruct(rule, input_grid)
        if rule_type == "scatter_count_x":
            return self._apply_scatter_count_x(rule, input_grid)
        if rule_type == "rotation_tiling":
            return self._apply_rotation_tiling(rule, input_grid)
        if rule_type == "rectangle_interior_count":
            return self._apply_rectangle_interior_count(rule, input_grid)
        if rule_type == "pattern_tile_fill":
            return self._apply_pattern_tile_fill(rule, input_grid)
        if rule_type == "nearest_corner_lines":
            return self._apply_nearest_corner_lines(rule, input_grid)
        if rule_type == "frame_inversion":
            return self._apply_frame_inversion(rule, input_grid)
        if rule_type == "horizontal_mirror_mark":
            return self._apply_horizontal_mirror_mark(rule, input_grid)
        if rule_type == "denoise_keep_rectangles":
            return self._apply_denoise_keep_rectangles(rule, input_grid)
        if rule_type == "extend_diagonal_arms":
            return self._apply_extend_diagonal_arms(rule, input_grid)
        if rule_type == "seed_quadrant_project":
            return self._apply_seed_quadrant_project(rule, input_grid)
        if rule_type == "flood_fill_partition":
            return self._apply_flood_fill_partition(rule, input_grid)
        if rule_type == "rotation_tile_repeat":
            return self._apply_rotation_tile_repeat(rule, input_grid)
        if rule_type == "cross_arm_mode":
            return self._apply_cross_arm_mode(rule, input_grid)
        if rule_type == "grid_intersection_compress":
            return self._apply_grid_intersection_compress(rule, input_grid)
        if rule_type == "enclosed_rect_fill":
            return self._apply_enclosed_rect_fill(rule, input_grid)
        if rule_type == "color_key_remap":
            return self._apply_color_key_remap(rule, input_grid)
        if rule_type == "square_corner_mark":
            return self._apply_square_corner_mark(rule, input_grid)
        if rule_type == "domino_cross_intersection":
            return self._apply_domino_cross_intersection(rule, input_grid)
        if rule_type == "separator_projection":
            return self._apply_separator_projection(rule, input_grid)
        if rule_type == "marker_arm_extend":
            return self._apply_marker_arm_extend(rule, input_grid)
        if rule_type == "subgrid_invert":
            return self._apply_subgrid_invert(rule, input_grid)
        if rule_type == "invert_tile":
            return self._apply_invert_tile(rule, input_grid)
        if rule_type == "double_mirror":
            return self._apply_double_mirror(rule, input_grid)
        if rule_type == "column_fill_tile":
            return self._apply_column_fill_tile(rule, input_grid)
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

    def _apply_vertical_mirror_append(self, rule, input_grid):
        """Output = input rows followed by input rows reversed."""
        raw = input_grid.raw
        output = [row[:] for row in raw]
        for r in range(len(raw) - 1, -1, -1):
            output.append(raw[r][:])
        return output

    def _apply_fill_rectangles_by_size(self, rule, input_grid):
        """Find outlined rectangles and fill interiors based on area."""
        raw = input_grid.raw
        outline_color = rule["outline_color"]
        bg_color = rule["bg_color"]
        size_to_color = rule["size_to_color"]

        output = [row[:] for row in raw]
        rects = _find_outlined_rectangles(raw, outline_color, bg_color)

        for (r1, c1, r2, c2) in rects:
            interior_h = r2 - r1 - 1
            interior_w = c2 - c1 - 1
            area = interior_h * interior_w
            # Handle both int and string keys (JSON round-trip)
            fill_color = size_to_color.get(area)
            if fill_color is None:
                fill_color = size_to_color.get(str(area))
            if fill_color is not None:
                for rr in range(r1 + 1, r2):
                    for cc in range(c1 + 1, c2):
                        output[rr][cc] = fill_color

        return output

    def _apply_keep_center_column(self, rule, input_grid):
        """Keep only the center column from input, fill rest with bg."""
        raw = input_grid.raw
        bg_color = rule["bg_color"]
        h = len(raw)
        w = len(raw[0]) if raw else 0
        center_col = w // 2

        output = [[bg_color] * w for _ in range(h)]
        for r in range(h):
            output[r][center_col] = raw[r][center_col]
        return output

    def _apply_reverse_rings(self, rule, input_grid):
        """Reverse the order of concentric rectangular ring colors."""
        raw = input_grid.raw
        h = len(raw)
        w = len(raw[0]) if raw else 0
        ring_colors = GeneralizeOperator._extract_ring_colors(raw)
        if ring_colors is None:
            return [row[:] for row in raw]
        reversed_colors = list(reversed(ring_colors))
        output = [row[:] for row in raw]
        max_layers = len(ring_colors)
        for layer in range(max_layers):
            color = reversed_colors[layer]
            for c in range(layer, w - layer):
                output[layer][c] = color
                output[h - 1 - layer][c] = color
            for r in range(layer, h - layer):
                output[r][layer] = color
                output[r][w - 1 - layer] = color
        return output

    def _apply_pixel_scale(self, rule, input_grid):
        """Scale each pixel to an NxN block."""
        raw = input_grid.raw
        scale = rule["scale"]
        h_in = len(raw)
        w_in = len(raw[0]) if raw else 0
        output = [[0] * (w_in * scale) for _ in range(h_in * scale)]
        for r in range(h_in):
            for c in range(w_in):
                color = raw[r][c]
                for dr in range(scale):
                    for dc in range(scale):
                        output[r * scale + dr][c * scale + dc] = color
        return output

    def _apply_recolor_by_size(self, rule, input_grid):
        """Recolor connected components by size group (largest size=1, etc.)."""
        raw = input_grid.raw
        source_color = rule["source_color"]
        components = GeneralizeOperator._find_components(raw, source_color)
        sizes = sorted(set(len(c) for c in components), reverse=True)
        size_to_color = {s: rank + 1 for rank, s in enumerate(sizes)}
        output = [row[:] for row in raw]
        for comp in components:
            new_color = size_to_color[len(comp)]
            for (r, c) in comp:
                output[r][c] = new_color
        return output

    def _apply_staircase_growth(self, rule, input_grid):
        """1-row input → W/2 rows, each row adds one more colored cell."""
        raw = input_grid.raw
        if len(raw) != 1:
            return [row[:] for row in raw]
        row = raw[0]
        w = len(row)

        # Find color and count
        color = row[0]
        n = 0
        for v in row:
            if v == color:
                n += 1
            else:
                break

        num_rows = w // 2
        output = []
        for i in range(num_rows):
            count = n + i
            output.append([color if j < count else 0 for j in range(w)])
        return output

    def _apply_gravity_slide(self, rule, input_grid):
        """Slide object-color components down toward wall with 1-cell gap."""
        from itertools import permutations
        raw = input_grid.raw
        h = len(raw)
        w = len(raw[0]) if raw else 0

        color_counts = Counter(c for row in raw for c in row)
        if len(color_counts) != 3:
            return [row[:] for row in raw]

        colors = [c for c, _ in color_counts.most_common()]

        for bg, wall_color, obj_color in permutations(colors):
            components = GeneralizeOperator._find_components(raw, obj_color)
            if not components:
                continue

            result = GeneralizeOperator._gravity_slide_grid(
                raw, bg, wall_color, obj_color, h, w
            )
            if result is None:
                continue

            # Verify wall cells unchanged and result differs from input
            valid = True
            changed = False
            for r in range(h):
                for c in range(w):
                    if raw[r][c] == wall_color and result[r][c] != wall_color:
                        valid = False
                        break
                    if result[r][c] != raw[r][c]:
                        changed = True
                if not valid:
                    break

            if valid and changed:
                return result

        return [row[:] for row in raw]

    def _apply_corner_fill_quadrants(self, rule, input_grid):
        """Rectangle(s) with corner markers → fill quadrants with corner colors."""
        raw = input_grid.raw
        h = len(raw)
        w = len(raw[0]) if raw else 0
        filler_color = rule["filler_color"]
        bg_color = rule["bg_color"]

        rects = GeneralizeOperator._find_filler_rectangles(raw, filler_color, h, w)
        if not rects:
            return [row[:] for row in raw]

        output = [row[:] for row in raw]

        for (r1, c1, r2, c2) in rects:
            corners = GeneralizeOperator._get_rect_corners(raw, r1, c1, r2, c2, h, w, bg_color, filler_color)
            if corners is None:
                continue

            rect_h = r2 - r1 + 1
            rect_w = c2 - c1 + 1
            half_h = rect_h // 2
            half_w = rect_w // 2

            for r in range(r1, r2 + 1):
                for c in range(c1, c2 + 1):
                    qr = "t" if r < r1 + half_h else "b"
                    qc = "l" if c < c1 + half_w else "r"
                    output[r][c] = corners[qr + qc]

            # Remove corner pixels
            for cr, cc in [(r1-1,c1-1),(r1-1,c2+1),(r2+1,c1-1),(r2+1,c2+1)]:
                if 0 <= cr < h and 0 <= cc < w:
                    output[cr][cc] = bg_color

        return output

    def _apply_diamond_bridge(self, rule, input_grid):
        """Find diamond shapes and connect aligned ones with bridge color."""
        raw = input_grid.raw
        h = len(raw)
        w = len(raw[0]) if raw else 0
        bridge_color = rule["bridge_color"]

        centers = GeneralizeOperator._find_diamond_centers(raw, h, w)
        if not centers:
            return [row[:] for row in raw]

        return GeneralizeOperator._draw_diamond_bridges_with_color(
            raw, centers, h, w, bridge_color
        )

    def _apply_stripe_zone_fill(self, rule, input_grid):
        """Apply stripe zone fill transformation."""
        raw = input_grid.raw
        h = len(raw)
        w = len(raw[0]) if raw else 0

        spine_col = GeneralizeOperator._find_spine_column(raw, h, w)
        if spine_col is None:
            return [row[:] for row in raw]

        stripes = GeneralizeOperator._find_stripe_rows(raw, h, w, spine_col)
        if not stripes:
            return [row[:] for row in raw]

        return GeneralizeOperator._compute_stripe_zone_fill(
            raw, h, w, spine_col, stripes
        )

    def _apply_cross_projection(self, rule, input_grid):
        """Find crosses with missing arm, project center color to edge."""
        raw = input_grid.raw
        h, w = len(raw), len(raw[0])
        bg = Counter(c for row in raw for c in row).most_common(1)[0][0]

        # Find crosses (same logic as detection)
        non_bg = {}
        for r in range(h):
            for c in range(w):
                if raw[r][c] != bg:
                    non_bg[(r, c)] = raw[r][c]

        visited = set()
        components = []
        for pos in non_bg:
            if pos in visited:
                continue
            comp = []
            stack = [pos]
            visited.add(pos)
            while stack:
                p = stack.pop()
                comp.append(p)
                for dr, dc in [(-1,0),(1,0),(0,-1),(0,1)]:
                    np_ = (p[0]+dr, p[1]+dc)
                    if np_ in non_bg and np_ not in visited:
                        visited.add(np_)
                        stack.append(np_)
            components.append(comp)

        crosses = []
        for comp in components:
            color_counts = Counter(non_bg[p] for p in comp)
            if len(color_counts) != 2:
                continue
            arm_color = color_counts.most_common(2)[0][0]
            center_color = color_counts.most_common(2)[1][0]
            center_cells = [p for p in comp if non_bg[p] == center_color]
            if len(center_cells) != 1:
                continue
            cr, cc = center_cells[0]
            arm_cells = [p for p in comp if non_bg[p] == arm_color]
            has_up = any(r < cr and c == cc for r, c in arm_cells)
            has_down = any(r > cr and c == cc for r, c in arm_cells)
            has_left = any(r == cr and c < cc for r, c in arm_cells)
            has_right = any(r == cr and c > cc for r, c in arm_cells)
            dirs = [has_up, has_down, has_left, has_right]
            if sum(dirs) != 3:
                continue
            if not has_up: missing = 'up'
            elif not has_down: missing = 'down'
            elif not has_left: missing = 'left'
            else: missing = 'right'
            crosses.append({'center': (cr, cc), 'center_color': center_color, 'missing': missing})

        output = [row[:] for row in raw]
        edge_colors = {}
        for cross in crosses:
            cr, cc = cross['center']
            cc_color = cross['center_color']
            missing = cross['missing']
            edge_colors[missing] = cc_color
            if missing == 'up':
                r = cr - 2
                while r > 0:
                    output[r][cc] = cc_color
                    r -= 2
            elif missing == 'down':
                r = cr + 2
                while r < h - 1:
                    output[r][cc] = cc_color
                    r += 2
            elif missing == 'left':
                c = cc - 2
                while c > 0:
                    output[cr][c] = cc_color
                    c -= 2
            elif missing == 'right':
                c = cc + 2
                while c < w - 1:
                    output[cr][c] = cc_color
                    c += 2
        for direction, color in edge_colors.items():
            if direction == 'up':
                for c in range(w): output[0][c] = color
            elif direction == 'down':
                for c in range(w): output[h-1][c] = color
            elif direction == 'left':
                for r in range(h): output[r][0] = color
            elif direction == 'right':
                for r in range(h): output[r][w-1] = color
        corner_dirs = {
            (0, 0): ('up', 'left'), (0, w-1): ('up', 'right'),
            (h-1, 0): ('down', 'left'), (h-1, w-1): ('down', 'right'),
        }
        for (cr_, cc_), (d1, d2) in corner_dirs.items():
            if d1 in edge_colors and d2 in edge_colors:
                output[cr_][cc_] = 0
        return output

    def _apply_quadrant_shape_swap(self, rule, input_grid):
        """Swap shapes between horizontally paired quadrants."""
        raw = input_grid.raw
        h, w = len(raw), len(raw[0])

        # Find dividers
        zero_rows = [r for r in range(h) if all(raw[r][c] == 0 for c in range(w))]
        zero_cols = [c for c in range(w) if all(raw[r][c] == 0 for r in range(h))]

        def get_sections(dividers, total):
            sections = []
            groups = []
            i = 0
            while i < len(dividers):
                start = dividers[i]
                end = start
                while i + 1 < len(dividers) and dividers[i+1] == end + 1:
                    i += 1
                    end = dividers[i]
                groups.append((start, end))
                i += 1
            prev = 0
            for gs, ge in groups:
                if gs > prev:
                    sections.append((prev, gs - 1))
                prev = ge + 1
            if prev < total:
                sections.append((prev, total - 1))
            return sections

        row_sections = get_sections(zero_rows, h)
        col_sections = get_sections(zero_cols, w)

        output = [row[:] for row in raw]

        for rs, re in row_sections:
            for ci in range(0, len(col_sections) - 1, 2):
                cs_l, ce_l = col_sections[ci]
                cs_r, ce_r = col_sections[ci + 1]
                cell_h = re - rs + 1
                cell_w_l = ce_l - cs_l + 1
                cell_w_r = ce_r - cs_r + 1

                # Extract cells
                cell_l = [raw[r][cs_l:ce_l+1] for r in range(rs, re+1)]
                cell_r = [raw[r][cs_r:ce_r+1] for r in range(rs, re+1)]

                # Find bg and shape
                flat_l = [c for row in cell_l for c in row]
                flat_r = [c for row in cell_r for c in row]
                bg_l = Counter(flat_l).most_common(1)[0][0]
                bg_r = Counter(flat_r).most_common(1)[0][0]

                # Get shapes
                shape_r = set()
                for r, row in enumerate(cell_r):
                    for c, v in enumerate(row):
                        if v != bg_r:
                            shape_r.add((r, c))
                shape_l = set()
                for r, row in enumerate(cell_l):
                    for c, v in enumerate(row):
                        if v != bg_l:
                            shape_l.add((r, c))

                # Clear left, draw right's shape in right's bg
                for r in range(cell_h):
                    for c in range(cell_w_l):
                        output[rs + r][cs_l + c] = bg_l
                if cell_w_l == cell_w_r:
                    for (sr, sc) in shape_r:
                        if 0 <= sr < cell_h and 0 <= sc < cell_w_l:
                            output[rs + sr][cs_l + sc] = bg_r

                # Clear right, draw left's shape in left's bg
                for r in range(cell_h):
                    for c in range(cell_w_r):
                        output[rs + r][cs_r + c] = bg_r
                if cell_w_l == cell_w_r:
                    for (sr, sc) in shape_l:
                        if 0 <= sr < cell_h and 0 <= sc < cell_w_r:
                            output[rs + sr][cs_r + sc] = bg_l

        return output

    def _apply_lpath_chain(self, rule, input_grid):
        """Apply L-path chain rule."""
        raw = input_grid.raw
        return GeneralizeOperator._run_lpath(
            raw, rule["bg"], rule["path_color"],
            rule["down_color"], rule["up_color"]
        )

    def _apply_arrow_chain_mirror(self, rule, input_grid):
        """Apply arrow chain mirror rule."""
        raw = input_grid.raw
        h, w = len(raw), len(raw[0])
        sep_color = rule["sep_color"]

        # Find separator row
        sep_row = None
        for r in range(h):
            if all(raw[r][c] == sep_color for c in range(w)):
                sep_row = r
                break
        if sep_row is None:
            return [row[:] for row in raw]

        return GeneralizeOperator._run_arrow_mirror(
            raw, rule["bg"], sep_color, sep_row,
            rule["top_color"], rule["dot_color"], rule["arrow_color"]
        )

    # ---- apply: grid zigzag shear ------------------------------------------

    def _apply_grid_zigzag_shear(self, rule, input_grid):
        """Apply grid zigzag shear rule."""
        raw = input_grid.raw
        h, w = len(raw), len(raw[0])

        # Detect bg (most frequent) and shape color dynamically
        counts = Counter()
        for r in range(h):
            for c in range(w):
                counts[raw[r][c]] += 1
        bg = counts.most_common(1)[0][0]
        non_bg = [c for c in counts if c != bg]
        if not non_bg:
            return [row[:] for row in raw]
        sc = non_bg[0]

        # Find bounding box
        rows_with_sc = [r for r in range(h) for c in range(w) if raw[r][c] == sc]
        cols_with_sc = [c for r in range(h) for c in range(w) if raw[r][c] == sc]
        if not rows_with_sc:
            return [row[:] for row in raw]
        r0, r1 = min(rows_with_sc), max(rows_with_sc)
        c0, c1 = min(cols_with_sc), max(cols_with_sc)
        box_h = r1 - r0 + 1

        sin_table = [0, 1, 0, -1]
        phase = (1 - box_h) % 4

        output = [[bg] * w for _ in range(h)]
        for ri in range(box_h):
            shift = sin_table[(ri + phase) % 4]
            for ci in range(c1 - c0 + 1):
                in_r, in_c = r0 + ri, c0 + ci
                out_c = in_c + shift
                if 0 <= out_c < w and raw[in_r][in_c] == sc:
                    output[in_r][out_c] = sc
        return output

    # ---- apply: three-shape rearrange --------------------------------------

    def _apply_three_shape_rearrange(self, rule, input_grid):
        """Apply three-shape rearrange rule."""
        raw = input_grid.raw
        h, w = len(raw), len(raw[0])

        counts = Counter()
        for r in range(h):
            for c in range(w):
                counts[raw[r][c]] += 1
        bg = counts.most_common(1)[0][0]

        obj_colors = set()
        for r in range(h):
            for c in range(w):
                if raw[r][c] != bg:
                    obj_colors.add(raw[r][c])

        if len(obj_colors) != 3:
            return [row[:] for row in raw]

        objs = {}
        for color in obj_colors:
            pixels = [(r, c) for r in range(h) for c in range(w) if raw[r][c] == color]
            rmin = min(r for r, c in pixels)
            rmax = max(r for r, c in pixels)
            cmin = min(c for r, c in pixels)
            cmax = max(c for r, c in pixels)
            objs[color] = {
                "pixels": pixels, "count": len(pixels),
                "rmin": rmin, "rmax": rmax, "cmin": cmin, "cmax": cmax,
                "height": rmax - rmin + 1, "width": cmax - cmin + 1,
            }

        sorted_colors = sorted(obj_colors, key=lambda c: objs[c]["count"])
        conn_color = sorted_colors[0]
        outer_colors = sorted_colors[1:]

        connector = objs[conn_color]
        conn_cr = (connector["rmin"] + connector["rmax"]) / 2
        conn_cc = (connector["cmin"] + connector["cmax"]) / 2

        a_cr = (objs[outer_colors[0]]["rmin"] + objs[outer_colors[0]]["rmax"]) / 2
        a_cc = (objs[outer_colors[0]]["cmin"] + objs[outer_colors[0]]["cmax"]) / 2
        b_cr = (objs[outer_colors[1]]["rmin"] + objs[outer_colors[1]]["rmax"]) / 2
        b_cc = (objs[outer_colors[1]]["cmin"] + objs[outer_colors[1]]["cmax"]) / 2

        v_between = (min(a_cr, b_cr) <= conn_cr <= max(a_cr, b_cr))
        h_between = (min(a_cc, b_cc) <= conn_cc <= max(a_cc, b_cc))

        if v_between and not h_between:
            axis = "vertical"
        elif h_between and not v_between:
            axis = "horizontal"
        elif v_between and h_between:
            v_spread = max(a_cr, b_cr) - min(a_cr, b_cr)
            h_spread = max(a_cc, b_cc) - min(a_cc, b_cc)
            axis = "vertical" if v_spread > h_spread else "horizontal"
        else:
            return [row[:] for row in raw]

        if axis == "vertical":
            conn_perp = connector["width"]
            a_perp = objs[outer_colors[0]]["width"]
            b_perp = objs[outer_colors[1]]["width"]
        else:
            conn_perp = connector["height"]
            a_perp = objs[outer_colors[0]]["height"]
            b_perp = objs[outer_colors[1]]["height"]

        a_can = (a_perp >= 2 * conn_perp)
        b_can = (b_perp >= 2 * conn_perp)

        if a_can and not b_can:
            split_color = outer_colors[0]
            stay_color = outer_colors[1]
        elif b_can and not a_can:
            split_color = outer_colors[1]
            stay_color = outer_colors[0]
        elif a_can and b_can:
            # Pick the one with smaller perpendicular extent (cleaner split)
            if a_perp <= b_perp:
                split_color = outer_colors[0]
                stay_color = outer_colors[1]
            else:
                split_color = outer_colors[1]
                stay_color = outer_colors[0]
        else:
            return [row[:] for row in raw]

        result = GeneralizeOperator._compute_three_shape_output(
            raw, bg, conn_color, split_color, stay_color, objs, axis, h, w)
        return result if result else [row[:] for row in raw]

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

    def _apply_block_grid_gravity(self, rule, input_grid):
        raw = input_grid.raw
        h, w = len(raw), len(raw[0])
        result = _block_grid_gravity_transform(raw, h, w)
        if result is None:
            return [row[:] for row in raw]
        return result

    def _apply_template_reconstruct(self, rule, input_grid):
        raw = input_grid.raw
        result = _template_reconstruct_transform(raw)
        if result is None:
            return [row[:] for row in raw]
        return result

    def _apply_scatter_count_x(self, rule, input_grid):
        raw = input_grid.raw
        bg = rule["bg_color"]
        fill = rule["fill_color"]
        diag = rule["diag_color"]
        out_h = rule["out_h"]
        out_w = rule["out_w"]

        # Count scatter colors
        in_counts = Counter(c for row in raw for c in row)
        scatter_colors = sorted([c for c in in_counts if c != bg],
                                key=lambda c: in_counts[c], reverse=True)
        if len(scatter_colors) != 2:
            return [row[:] for row in raw]

        rect_w = in_counts[scatter_colors[0]]
        rect_h = in_counts[scatter_colors[1]]

        result = _build_scatter_x_grid(
            out_h, out_w, rect_h, rect_w, bg, fill, diag)
        if result is None:
            return [row[:] for row in raw]
        return result

    def _apply_rotation_tiling(self, rule, input_grid):
        raw = input_grid.raw
        h = len(raw)
        w = len(raw[0]) if raw else 0
        if h != w or h == 0:
            return [row[:] for row in raw]
        n = h

        def rot90(g):
            return [[g[n - 1 - c][r] for c in range(n)] for r in range(n)]

        def rot180(g):
            return [[g[n - 1 - r][n - 1 - c] for c in range(n)] for r in range(n)]

        def rot270(g):
            return [[g[c][n - 1 - r] for c in range(n)] for r in range(n)]

        r0 = raw
        r90_g = rot90(raw)
        r180_g = rot180(raw)
        r270_g = rot270(raw)

        out = [[0] * (2 * n) for _ in range(2 * n)]
        for r in range(n):
            for c in range(n):
                out[r][c] = r0[r][c]
                out[r][n + c] = r270_g[r][c]
                out[n + r][c] = r180_g[r][c]
                out[n + r][n + c] = r90_g[r][c]
        return out

    def _apply_rectangle_interior_count(self, rule, input_grid):
        raw = input_grid.raw
        h, w = len(raw), len(raw[0])
        out_h = rule["out_h"]
        out_w = rule["out_w"]

        # Find 1-bordered rectangle
        ones = [(r, c) for r in range(h) for c in range(w) if raw[r][c] == 1]
        if not ones:
            return [[0] * out_w for _ in range(out_h)]
        r_min = min(r for r, c in ones)
        r_max = max(r for r, c in ones)
        c_min = min(c for r, c in ones)
        c_max = max(c for r, c in ones)

        # Count interior colored pixels
        color = 0
        count = 0
        for r in range(r_min + 1, r_max):
            for c in range(c_min + 1, c_max):
                if raw[r][c] != 0 and raw[r][c] != 1:
                    if color == 0:
                        color = raw[r][c]
                    count += 1

        # Fill output grid left-to-right, top-to-bottom
        out = [[0] * out_w for _ in range(out_h)]
        for i in range(count):
            r, c = divmod(i, out_w)
            if r < out_h:
                out[r][c] = color
        return out

    def _apply_pattern_tile_fill(self, rule, input_grid):
        raw = input_grid.raw
        h, w = len(raw), len(raw[0])

        from collections import Counter
        counts = Counter(c for row in raw for c in row)
        bg = counts.most_common(1)[0][0]

        # Find pattern rows
        pattern_rows = []
        for r in range(h):
            if not all(raw[r][c] == bg for c in range(w)):
                pattern_rows.append(r)

        if not pattern_rows:
            return [row[:] for row in raw]

        pat = [list(raw[r]) for r in pattern_rows]
        pat_len = len(pat)
        pr_max = max(pattern_rows)

        # Fill all rows with cyclic pattern from bottom
        out = []
        for r in range(h):
            dist_from_bottom = h - 1 - r
            cycle_row = pat[pat_len - 1 - (dist_from_bottom % pat_len)]
            out.append(list(cycle_row))
        return out

    def _apply_nearest_corner_lines(self, rule, input_grid):
        raw = input_grid.raw
        h, w = len(raw), len(raw[0])
        out = [[0] * w for _ in range(h)]

        pixels = []
        for r in range(h):
            for c in range(w):
                if raw[r][c] != 0:
                    pixels.append((r, c, raw[r][c]))

        for r, c, color in pixels:
            # Vertical line toward nearest top/bottom edge
            if r <= h - 1 - r:
                for rr in range(0, r + 1):
                    out[rr][c] = color
            else:
                for rr in range(r, h):
                    out[rr][c] = color
            # Horizontal line toward nearest left/right edge
            if c <= w - 1 - c:
                for cc in range(0, c + 1):
                    out[r][cc] = color
            else:
                for cc in range(c, w):
                    out[r][cc] = color

        return out

    def _apply_frame_inversion(self, rule, input_grid):
        raw = input_grid.raw
        h, w = len(raw), len(raw[0])

        # Find bounding box of non-zero pixels
        non_zero = [(r, c) for r in range(h) for c in range(w) if raw[r][c] != 0]
        if not non_zero:
            return [row[:] for row in raw]
        min_r = min(r for r, c in non_zero)
        max_r = max(r for r, c in non_zero)
        min_c = min(c for r, c in non_zero)
        max_c = max(c for r, c in non_zero)

        obj_h = max_r - min_r + 1
        obj_w = max_c - min_c + 1

        # Extract object
        obj = [raw[r][min_c:max_c + 1] for r in range(min_r, max_r + 1)]

        # Border color = corners
        border_color = obj[0][0]
        # Find interior color
        interior_color = None
        for r2 in range(1, obj_h - 1):
            for c2 in range(1, obj_w - 1):
                if obj[r2][c2] != border_color:
                    interior_color = obj[r2][c2]
                    break
            if interior_color is not None:
                break
        if interior_color is None:
            interior_color = border_color

        # Swap colors
        out = [[0] * obj_w for _ in range(obj_h)]
        for r2 in range(obj_h):
            for c2 in range(obj_w):
                if obj[r2][c2] == border_color:
                    out[r2][c2] = interior_color
                elif obj[r2][c2] == interior_color:
                    out[r2][c2] = border_color
                else:
                    out[r2][c2] = obj[r2][c2]
        return out

    def _apply_horizontal_mirror_mark(self, rule, input_grid):
        raw = input_grid.raw
        h, w = len(raw), len(raw[0])
        fg = rule["fg_color"]
        nc = rule["new_color"]

        out = [list(row) for row in raw]
        for r in range(h):
            for c in range(w):
                if raw[r][c] == fg:
                    mirror_c = w - 1 - c
                    if raw[r][mirror_c] == fg:
                        out[r][c] = nc
        return out

    def _apply_denoise_keep_rectangles(self, rule, input_grid):
        raw = input_grid.raw
        h, w = len(raw), len(raw[0])
        # Find fg color
        fg = None
        for r in range(h):
            for c in range(w):
                if raw[r][c] != 0:
                    fg = raw[r][c]
                    break
            if fg is not None:
                break
        if fg is None:
            return [row[:] for row in raw]

        # Keep pixels that belong to at least one 2×2 all-fg block
        keep = [[False] * w for _ in range(h)]
        for r in range(h - 1):
            for c in range(w - 1):
                if raw[r][c] == fg and raw[r][c + 1] == fg and \
                   raw[r + 1][c] == fg and raw[r + 1][c + 1] == fg:
                    keep[r][c] = True
                    keep[r][c + 1] = True
                    keep[r + 1][c] = True
                    keep[r + 1][c + 1] = True

        return [[fg if keep[r][c] else 0 for c in range(w)] for r in range(h)]

    def _apply_extend_diagonal_arms(self, rule, input_grid):
        raw = input_grid.raw
        h, w = len(raw), len(raw[0])
        # Find fg color
        fg = None
        for r in range(h):
            for c in range(w):
                if raw[r][c] != 0:
                    fg = raw[r][c]
                    break
            if fg is not None:
                break
        if fg is None:
            return [row[:] for row in raw]

        # Find all fg cells using 8-connectivity
        visited = [[False] * w for _ in range(h)]
        comp = []
        for r in range(h):
            for c in range(w):
                if raw[r][c] == fg and not visited[r][c]:
                    queue = [(r, c)]
                    visited[r][c] = True
                    while queue:
                        cr, cc = queue.pop(0)
                        comp.append((cr, cc))
                        for dr, dc in [(-1, 0), (1, 0), (0, -1), (0, 1),
                                       (-1, -1), (-1, 1), (1, -1), (1, 1)]:
                            nr, nc = cr + dr, cc + dc
                            if 0 <= nr < h and 0 <= nc < w and not visited[nr][nc] and raw[nr][nc] == fg:
                                visited[nr][nc] = True
                                queue.append((nr, nc))
                    break
            if comp:
                break

        comp_set = set(comp)

        # Find 2×2 block
        block = None
        for r in range(h - 1):
            for c in range(w - 1):
                if (r, c) in comp_set and (r, c + 1) in comp_set and \
                   (r + 1, c) in comp_set and (r + 1, c + 1) in comp_set:
                    block = (r, c)
                    break
            if block:
                break

        if block is None:
            return [row[:] for row in raw]

        br, bc = block
        block_cells = {(br, bc), (br, bc + 1), (br + 1, bc), (br + 1, bc + 1)}
        tips = [p for p in comp if p not in block_cells]

        out = [[0] * w for _ in range(h)]
        for (cr, cc) in block_cells:
            out[cr][cc] = fg

        for (tr, tc) in tips:
            dr = 1 if tr > br else -1
            dc = 1 if tc > bc else -1
            r2, c2 = tr, tc
            while 0 <= r2 < h and 0 <= c2 < w:
                out[r2][c2] = fg
                r2 += dr
                c2 += dc
        return out

    def _apply_seed_quadrant_project(self, rule, input_grid):
        raw = input_grid.raw
        h, w = len(raw), len(raw[0])

        # Find 2×2 seed
        sr = sc = None
        for r in range(h - 1):
            for c in range(w - 1):
                if raw[r][c] != 0 and raw[r][c + 1] != 0 and \
                   raw[r + 1][c] != 0 and raw[r + 1][c + 1] != 0:
                    sr, sc = r, c
                    break
            if sr is not None:
                break

        if sr is None:
            return [row[:] for row in raw]

        seed = [[raw[sr][sc], raw[sr][sc + 1]],
                [raw[sr + 1][sc], raw[sr + 1][sc + 1]]]

        out = [[0] * w for _ in range(h)]
        # Copy seed
        for dr in range(2):
            for dc in range(2):
                out[sr + dr][sc + dc] = seed[dr][dc]

        above = sr
        below = h - sr - 2
        left = sc
        right = w - sc - 2

        # Top-left: color = seed[1][1]
        fh, fw = min(2, above), min(2, left)
        for dr in range(fh):
            for dc in range(fw):
                out[sr - fh + dr][sc - fw + dc] = seed[1][1]

        # Top-right: color = seed[1][0]
        fh, fw = min(2, above), min(2, right)
        for dr in range(fh):
            for dc in range(fw):
                out[sr - fh + dr][sc + 2 + dc] = seed[1][0]

        # Bottom-left: color = seed[0][1]
        fh, fw = min(2, below), min(2, left)
        for dr in range(fh):
            for dc in range(fw):
                out[sr + 2 + dr][sc - fw + dc] = seed[0][1]

        # Bottom-right: color = seed[0][0]
        fh, fw = min(2, below), min(2, right)
        for dr in range(fh):
            for dc in range(fw):
                out[sr + 2 + dr][sc + 2 + dc] = seed[0][0]

        return out

    def _apply_flood_fill_partition(self, rule, input_grid):
        raw = input_grid.raw
        h, w = len(raw), len(raw[0])
        zero_color = rule["zero_color"]
        color_a = rule["color_a"]   # exterior (border-reachable)
        color_b = rule["color_b"]   # interior

        # Flood-fill from border zero-cells (4-connected)
        visited = [[False] * w for _ in range(h)]
        queue = []
        for r in range(h):
            for c in range(w):
                if raw[r][c] == zero_color and (r == 0 or r == h - 1 or c == 0 or c == w - 1):
                    if not visited[r][c]:
                        visited[r][c] = True
                        queue.append((r, c))

        exterior = set()
        qi = 0
        while qi < len(queue):
            cr, cc = queue[qi]
            qi += 1
            exterior.add((cr, cc))
            for dr, dc in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                nr, nc = cr + dr, cc + dc
                if 0 <= nr < h and 0 <= nc < w and not visited[nr][nc] and raw[nr][nc] == zero_color:
                    visited[nr][nc] = True
                    queue.append((nr, nc))

        out = [row[:] for row in raw]
        for r in range(h):
            for c in range(w):
                if raw[r][c] == zero_color:
                    out[r][c] = color_a if (r, c) in exterior else color_b
        return out

    def _apply_rotation_tile_repeat(self, rule, input_grid):
        raw = input_grid.raw
        h = len(raw)
        w = len(raw[0]) if raw else 0
        if h != w or h == 0:
            return [row[:] for row in raw]
        n = h
        layout = rule["layout"]  # [TL, TR, BL, BR] rotation indices

        def rot(grid, k):
            g = [row[:] for row in grid]
            for _ in range(k % 4):
                g = [[g[n - 1 - c][r] for c in range(n)] for r in range(n)]
            return g

        rotations = [rot(raw, k) for k in range(4)]

        out = [[0] * (4 * n) for _ in range(4 * n)]
        quadrant_offsets = [(0, 0), (0, 2 * n), (2 * n, 0), (2 * n, 2 * n)]
        for idx, (qr, qc) in enumerate(quadrant_offsets):
            rk = rotations[layout[idx]]
            for r in range(2 * n):
                for c in range(2 * n):
                    out[qr + r][qc + c] = rk[r % n][c % n]
        return out

    def _apply_cross_arm_mode(self, rule, input_grid):
        raw = input_grid.raw
        h, w = len(raw), len(raw[0])
        center_color = rule["center_color"]

        # Find background color
        color_counts = Counter(c for row in raw for c in row)
        bg = color_counts.most_common(1)[0][0]

        # Find all crosses
        arm_colors = []
        for r in range(1, h - 1):
            for c in range(1, w - 1):
                if raw[r][c] != center_color:
                    continue
                neighbors = [raw[r - 1][c], raw[r + 1][c], raw[r][c - 1], raw[r][c + 1]]
                if len(set(neighbors)) == 1 and neighbors[0] != bg and neighbors[0] != center_color:
                    arm_colors.append(neighbors[0])

        if not arm_colors:
            return [[0]]

        mode_color = Counter(arm_colors).most_common(1)[0][0]
        return [[mode_color]]

    def _apply_grid_intersection_compress(self, rule, input_grid):
        raw = input_grid.raw
        det = GeneralizeOperator._detect_grid_structure(raw)
        if det is None:
            return [row[:] for row in raw]
        grid_color, h_lines, v_lines = det

        # Extract intersection values
        int_grid = {}
        for ri, r in enumerate(h_lines):
            for ci, c in enumerate(v_lines):
                val = raw[r][c]
                if val != grid_color:
                    int_grid[(ri, ci)] = val

        if not int_grid:
            return [row[:] for row in raw]

        min_r = min(k[0] for k in int_grid)
        max_r = max(k[0] for k in int_grid)
        min_c = min(k[1] for k in int_grid)
        max_c = max(k[1] for k in int_grid)

        bbox_h = max_r - min_r + 1
        bbox_w = max_c - min_c + 1

        if bbox_h != 4 or bbox_w != 4:
            return [row[:] for row in raw]

        pat = [[0]*4 for _ in range(4)]
        for (ri, ci), val in int_grid.items():
            pat[ri - min_r][ci - min_c] = val

        return GeneralizeOperator._compress_4x4_to_3x3(pat)

    def _apply_enclosed_rect_fill(self, rule, input_grid):
        raw = input_grid.raw
        h, w = len(raw), len(raw[0])
        out = [row[:] for row in raw]

        # Flood-fill from border 0-cells
        visited = [[False]*w for _ in range(h)]
        queue = []
        for r in range(h):
            for c in range(w):
                if raw[r][c] == 0 and (r == 0 or r == h-1 or c == 0 or c == w-1):
                    if not visited[r][c]:
                        visited[r][c] = True
                        queue.append((r, c))
        qi = 0
        while qi < len(queue):
            cr, cc = queue[qi]; qi += 1
            for dr, dc in [(-1,0),(1,0),(0,-1),(0,1)]:
                nr, nc = cr+dr, cc+dc
                if 0 <= nr < h and 0 <= nc < w and not visited[nr][nc] and raw[nr][nc] == 0:
                    visited[nr][nc] = True
                    queue.append((nr, nc))

        # Fill interior 0-cells with 1
        for r in range(h):
            for c in range(w):
                if raw[r][c] == 0 and not visited[r][c]:
                    out[r][c] = 1
        return out

    def _apply_square_corner_mark(self, rule, input_grid):
        raw = input_grid.raw
        h, w = len(raw), len(raw[0])
        marker_color = rule.get("marker_color", 2)
        out = [row[:] for row in raw]

        from collections import Counter
        bg = Counter(raw[r][c] for r in range(h) for c in range(w)).most_common(1)[0][0]

        # Find connected components of non-bg color
        visited = [[False]*w for _ in range(h)]
        for r in range(h):
            for c in range(w):
                if raw[r][c] != bg and not visited[r][c]:
                    comp = []
                    color = raw[r][c]
                    queue = [(r, c)]
                    visited[r][c] = True
                    while queue:
                        cr, cc = queue.pop(0)
                        comp.append((cr, cc))
                        for dr, dc in [(-1,0),(1,0),(0,-1),(0,1)]:
                            nr, nc = cr+dr, cc+dc
                            if 0 <= nr < h and 0 <= nc < w and not visited[nr][nc] and raw[nr][nc] == color:
                                visited[nr][nc] = True
                                queue.append((nr, nc))
                    # Check if square rectangular border
                    r1 = min(p[0] for p in comp)
                    c1 = min(p[1] for p in comp)
                    r2 = max(p[0] for p in comp)
                    c2 = max(p[1] for p in comp)
                    bh = r2 - r1 + 1
                    bw = c2 - c1 + 1
                    if bh != bw or bh < 2:
                        continue
                    perimeter = set()
                    for rr in range(r1, r2+1):
                        for cc2 in range(c1, c2+1):
                            if rr == r1 or rr == r2 or cc2 == c1 or cc2 == c2:
                                perimeter.add((rr, cc2))
                    if set(comp) != perimeter:
                        continue
                    # Place corner marks
                    marks = [
                        (r1-1, c1), (r1, c1-1),
                        (r1-1, c2), (r1, c2+1),
                        (r2+1, c1), (r2, c1-1),
                        (r2+1, c2), (r2, c2+1),
                    ]
                    for mr, mc in marks:
                        if 0 <= mr < h and 0 <= mc < w:
                            out[mr][mc] = marker_color
        return out

    def _apply_domino_cross_intersection(self, rule, input_grid):
        raw = input_grid.raw
        h, w = len(raw), len(raw[0])
        marker_color = rule.get("marker_color", 4)
        out = [row[:] for row in raw]

        from collections import Counter, defaultdict
        bg = Counter(raw[r][c] for r in range(h) for c in range(w)).most_common(1)[0][0]

        # Find connected components
        visited = [[False]*w for _ in range(h)]
        dominos_h = []
        dominos_v = []
        for r in range(h):
            for c in range(w):
                if raw[r][c] != bg and not visited[r][c]:
                    comp = []
                    queue = [(r, c)]
                    visited[r][c] = True
                    while queue:
                        cr, cc = queue.pop(0)
                        comp.append((cr, cc))
                        for dr, dc in [(-1,0),(1,0),(0,-1),(0,1)]:
                            nr, nc = cr+dr, cc+dc
                            if 0 <= nr < h and 0 <= nc < w and not visited[nr][nc] and raw[nr][nc] != bg:
                                visited[nr][nc] = True
                                queue.append((nr, nc))
                    if len(comp) == 2:
                        (r1, c1), (r2, c2) = comp
                        if r1 == r2 and abs(c1 - c2) == 1:
                            dominos_h.append((r1, min(c1, c2), max(c1, c2)))
                        elif c1 == c2 and abs(r1 - r2) == 1:
                            dominos_v.append((min(c1, c2), min(r1, r2), max(r1, r2)))

        # Horizontal gap centers
        h_by_row = defaultdict(list)
        for row, cl, cr in dominos_h:
            h_by_row[row].append((cl, cr))
        h_gap_centers = set()
        for row, doms in h_by_row.items():
            doms.sort()
            for i in range(len(doms) - 1):
                _, cr1 = doms[i]
                cl2, _ = doms[i+1]
                if cl2 > cr1 + 1:
                    gap_sum = (cr1 + 1 + cl2 - 1)
                    if gap_sum % 2 == 0:
                        h_gap_centers.add((row, gap_sum // 2))

        # Vertical gap centers
        v_by_col = defaultdict(list)
        for col, rt, rb in dominos_v:
            v_by_col[col].append((rt, rb))
        v_gap_centers = set()
        for col, doms in v_by_col.items():
            doms.sort()
            for i in range(len(doms) - 1):
                _, rb1 = doms[i]
                rt2, _ = doms[i+1]
                if rt2 > rb1 + 1:
                    gap_sum = (rb1 + 1 + rt2 - 1)
                    if gap_sum % 2 == 0:
                        v_gap_centers.add((gap_sum // 2, col))

        # Intersections
        for (hr, hc) in h_gap_centers:
            for (vr, vc) in v_gap_centers:
                if hr == vr and hc == vc:
                    out[hr][hc] = marker_color

        return out

    def _apply_separator_projection(self, rule, input_grid):
        raw = input_grid.raw
        h, w = len(raw), len(raw[0])

        frame = GeneralizeOperator._find_separator_frame(raw)
        if frame is None:
            return [row[:] for row in raw]
        fr1, fc1, fr2, fc2, fco1, fcc1, fco2, fcc2 = frame
        sep_colors = {fc1, fc2, fcc1, fcc2}

        inner_r1, inner_r2 = fr1 + 1, fr2 - 1
        inner_c1, inner_c2 = fco1 + 1, fco2 - 1
        frame_h = fr2 - fr1 + 1
        frame_w = fco2 - fco1 + 1

        # Find scattered pixels
        scattered = []
        scattered_color = None
        for r in range(inner_r1, inner_r2 + 1):
            for c in range(inner_c1, inner_c2 + 1):
                v = raw[r][c]
                if v != 0:
                    if scattered_color is None:
                        scattered_color = v
                    scattered.append((r, c))

        if scattered_color is None:
            scattered_color = 0

        # Determine projection direction
        match_dir = None
        if scattered_color == fc1:
            match_dir = "top"
        elif scattered_color == fc2:
            match_dir = "bottom"
        elif scattered_color == fcc1:
            match_dir = "left"
        elif scattered_color == fcc2:
            match_dir = "right"

        # Build output frame: copy borders from input
        out = [[0]*frame_w for _ in range(frame_h)]
        for c in range(frame_w):
            out[0][c] = raw[fr1][fco1 + c]
            out[frame_h - 1][c] = raw[fr2][fco1 + c]
        for r in range(frame_h):
            out[r][0] = raw[fr1 + r][fco1]
            out[r][frame_w - 1] = raw[fr1 + r][fco2]

        for (sr, sc) in scattered:
            ofr = sr - fr1
            ofc = sc - fco1
            out[ofr][ofc] = scattered_color
            if match_dir == "top":
                for rr in range(1, ofr):
                    out[rr][ofc] = scattered_color
            elif match_dir == "bottom":
                for rr in range(ofr + 1, frame_h - 1):
                    out[rr][ofc] = scattered_color
            elif match_dir == "left":
                for cc in range(1, ofc):
                    out[ofr][cc] = scattered_color
            elif match_dir == "right":
                for cc in range(ofc + 1, frame_w - 1):
                    out[ofr][cc] = scattered_color

        return out

    def _apply_color_key_remap(self, rule, input_grid):
        raw = input_grid.raw
        result = GeneralizeOperator._analyze_color_key_remap(raw)
        if result is None:
            return [row[:] for row in raw]
        (sr, sc, er, ec), color_map = result
        oh, ow = er - sr, ec - sc
        out = [[0]*ow for _ in range(oh)]
        for r in range(oh):
            for c in range(ow):
                orig = raw[sr + r][sc + c]
                out[r][c] = color_map.get(orig, orig)
        return out

    def _apply_marker_arm_extend(self, rule, input_grid):
        raw = input_grid.raw
        result = _marker_arm_extend_transform(raw)
        return result if result is not None else [row[:] for row in raw]

    def _apply_subgrid_invert(self, rule, input_grid):
        raw = input_grid.raw
        result = _subgrid_invert_transform(raw)
        return result if result is not None else [row[:] for row in raw]

    def _apply_invert_tile(self, rule, input_grid):
        raw = input_grid.raw
        h, w = len(raw), len(raw[0])
        nz = set()
        for row in raw:
            for c in row:
                if c != 0:
                    nz.add(c)
        fg = next(iter(nz)) if nz else 0
        inv = []
        for row in raw:
            inv.append([fg if c == 0 else 0 for c in row])
        # Tile 2x2
        out = []
        for r in range(2 * h):
            out.append([inv[r % h][c % w] for c in range(2 * w)])
        return out

    def _apply_double_mirror(self, rule, input_grid):
        raw = input_grid.raw
        h, w = len(raw), len(raw[0])
        wide = []
        for row in raw:
            wide.append(list(row) + list(reversed(row)))
        full = wide + list(reversed(wide))
        return full

    def _apply_column_fill_tile(self, rule, input_grid):
        raw = input_grid.raw
        h, w = len(raw), len(raw[0])
        fill_color = rule.get("fill_color", 8)
        active = set()
        for c in range(w):
            for r in range(h):
                if raw[r][c] != 0:
                    active.add(c)
                    break
        transformed = []
        for r in range(h):
            row = []
            for c in range(w):
                if c in active:
                    row.append(raw[r][c] if raw[r][c] != 0 else fill_color)
                else:
                    row.append(0)
            transformed.append(row)
        # Tile 2x2
        out = []
        for r in range(2 * h):
            out.append([transformed[r % h][c % w] for c in range(2 * w)])
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
