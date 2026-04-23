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
# Module-level helpers (shared across operators)
# ======================================================================

def _find_rect_frames(raw, frame_color, bg_color, H, W):
    """Find rectangular frames with exactly one gap in the border."""
    visited = set()
    frames = []
    for sr in range(H):
        for sc in range(W):
            if raw[sr][sc] == frame_color and (sr, sc) not in visited:
                component = []
                queue = [(sr, sc)]
                visited.add((sr, sc))
                while queue:
                    r, c = queue.pop(0)
                    component.append((r, c))
                    for dr, dc in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                        nr, nc = r + dr, c + dc
                        if (0 <= nr < H and 0 <= nc < W
                                and (nr, nc) not in visited
                                and raw[nr][nc] == frame_color):
                            visited.add((nr, nc))
                            queue.append((nr, nc))
                if len(component) < 6:
                    continue
                comp_set = set(component)
                min_r = min(r for r, c in component)
                max_r = max(r for r, c in component)
                min_c = min(c for r, c in component)
                max_c = max(c for r, c in component)
                border_cells = set()
                for r in range(min_r, max_r + 1):
                    for c in range(min_c, max_c + 1):
                        if r in (min_r, max_r) or c in (min_c, max_c):
                            border_cells.add((r, c))
                if not comp_set.issubset(border_cells):
                    continue
                gaps = border_cells - comp_set
                if len(gaps) != 1:
                    continue
                gap_r, gap_c = gaps.pop()
                if gap_r == min_r:
                    gap_side = "top"
                elif gap_r == max_r:
                    gap_side = "bottom"
                elif gap_c == min_c:
                    gap_side = "left"
                else:
                    gap_side = "right"
                frames.append((min_r, min_c, max_r, max_c,
                               gap_r, gap_c, gap_side))
    return frames


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
            patterns = {}
            wm.s1["patterns"] = patterns

        rule = None

        # Strategy 1: path tracing between turn markers
        rule = self._try_path_trace(patterns, wm)

        # Strategy 2: diamond connection (+ shapes linked by lines)
        if rule is None:
            rule = self._try_diamond_connect(patterns, wm)

        # Strategy 3: cross-grid band fill (column axis + colored rows)
        if rule is None:
            rule = self._try_cross_grid_fill(patterns, wm)

        # Strategy 3b: grid lines pattern (all-zero → 1 at even row/col positions)
        if rule is None:
            rule = self._try_grid_lines_pattern(patterns, wm)

        # Strategy 63: bar chart balance (bg=7, 8/2 bars at odd cols → add color-5 balance bar)
        # (placed early to prevent false-positive match by recolor_sequential)
        if rule is None:
            rule = self._try_bar_chart_balance(patterns, wm)

        # Strategy 4: sequential recoloring (e.g., color objects 1, 2, 3, ...)
        if rule is None:
            rule = self._try_recolor_sequential(patterns)

        # Strategy 5: reverse concentric rectangular rings
        if rule is None:
            rule = self._try_reverse_concentric_rings(patterns, wm)

        # Strategy 6: keep only the center column
        if rule is None:
            rule = self._try_keep_center_column(patterns, wm)

        # Strategy 6b: flood fill enclosed regions with color 1
        if rule is None:
            rule = self._try_flood_fill_enclosed(patterns, wm)

        # Strategy 6c: denoise rectangles (remove noise pixels, keep rect cores)
        if rule is None:
            rule = self._try_denoise_rectangles(patterns, wm)

        # Strategy 6d: corner mark square (project marks from square shape corners)
        if rule is None:
            rule = self._try_corner_mark_square(patterns, wm)

        # Strategy 6e: cross center mark (4 equidistant domino pairs → mark center)
        if rule is None:
            rule = self._try_cross_center_mark(patterns, wm)

        # Strategy 6f: mirror symmetry recolor (symmetric fg pairs → color 1)
        if rule is None:
            rule = self._try_mirror_symmetry_recolor(patterns, wm)

        # Strategy 6g: rect-pixel bridge (connect rect to isolated pixel)
        if rule is None:
            rule = self._try_rect_pixel_bridge(patterns, wm)

        # Strategy 6h: fractal block denoise (self-similar block grid repair)
        if rule is None:
            rule = self._try_fractal_block_denoise(patterns, wm)

        # Strategy 52: pixel collect snake (scattered pixels → 3×3 boustrophedon)
        if rule is None:
            rule = self._try_pixel_collect_snake(patterns, wm)

        # Strategy 53: frame scale pattern (2×2 quadrant pattern → fill frame interior)
        if rule is None:
            rule = self._try_frame_scale_pattern(patterns, wm)

        # Strategy 54: box slide trail (3×3 box slides along dotted trail)
        if rule is None:
            rule = self._try_box_slide_trail(patterns, wm)

        # Strategy 49: bbox fill (fill 0-cells within bounding box of fg shape)
        if rule is None:
            rule = self._try_bbox_fill(patterns, wm)

        # Strategy 50: symmetry complete (complete 4-fold rotational symmetry)
        if rule is None:
            rule = self._try_symmetry_complete(patterns, wm)

        # Strategy 51: accelerating sequence (colors at triangular-number positions)
        if rule is None:
            rule = self._try_accelerating_sequence(patterns, wm)

        # Strategy 55: cross pair lines (pixel pairs → lines, vertical wins)
        if rule is None:
            rule = self._try_cross_pair_lines(patterns, wm)

        # Strategy 56: multi-layer overlay (stacked layers merged with priority)
        if rule is None:
            rule = self._try_multi_layer_overlay(patterns, wm)

        # Strategy 57: tile grid recolor (5-colored tiles + key matrix → recolor)
        if rule is None:
            rule = self._try_tile_grid_recolor(patterns, wm)

        # Strategy 64: largest blob color (noisy grid + solid patches → 3×3 of largest CC color)
        if rule is None:
            rule = self._try_largest_blob_color(patterns, wm)

        # Strategy 66: spiral from seed (3-pixel center → rectangular spiral, 2s are obstacles)
        if rule is None:
            rule = self._try_spiral_from_seed(patterns, wm)

        # Strategy 65: shape stamp fill (0/5 grid with 2-template → stamp matching regions)
        if rule is None:
            rule = self._try_shape_stamp_fill(patterns, wm)

        # Strategy 70: separator sequence reflect (compare dot lines across separator)
        if rule is None:
            rule = self._try_separator_sequence_reflect(patterns, wm)

        # Strategy 7: simple 1:1 color mapping
        if rule is None:
            rule = self._try_color_mapping(patterns, wm)

        # Strategy 8: uniform scaling (output = NxN blocks of input cells)
        if rule is None:
            rule = self._try_uniform_scale(patterns, wm)

        # Strategy 9: recolor by connected-component size
        if rule is None:
            rule = self._try_recolor_by_size(patterns, wm)

        # Strategy 10: corner-marker quadrant fill
        if rule is None:
            rule = self._try_corner_fill(patterns, wm)

        # Strategy 11: vertical mirror (output = input rows + reversed rows)
        if rule is None:
            rule = self._try_vertical_mirror(patterns, wm)

        # Strategy 12: fill hollow rectangles by interior size
        if rule is None:
            rule = self._try_fill_rect_by_size(patterns, wm)

        # Strategy 13: staircase growth (single row expands into triangle)
        if rule is None:
            rule = self._try_staircase_growth(patterns, wm)

        # Strategy 14: trail displacement along marker chains
        if rule is None:
            rule = self._try_trail_displacement(patterns, wm)

        # Strategy 15: zigzag warp of rectangular frame
        if rule is None:
            rule = self._try_zigzag_warp(patterns, wm)

        # Strategy 16: gravity slide toward wall boundary
        if rule is None:
            rule = self._try_gravity_slide(patterns, wm)

        # Strategy 17: arrow projection to grid edges
        if rule is None:
            rule = self._try_arrow_projection(patterns, wm)

        # Strategy 18: quadrant pattern swap (left/right sections swap fg patterns)
        if rule is None:
            rule = self._try_quadrant_pattern_swap(patterns, wm)

        # Strategy 19: block wedge split (middle block inserts into adjacent block)
        if rule is None:
            rule = self._try_block_wedge_split(patterns, wm)

        # Strategy 20: block grid bar chart (meta-grid of 3x3 blocks → bar chart)
        if rule is None:
            rule = self._try_block_grid_bar_chart(patterns, wm)

        # Strategy 21: template stamp with rotation/reflection
        if rule is None:
            rule = self._try_template_stamp_rotate(patterns, wm)

        # Strategy 22: pixel count diamond (count two colors → rectangle dims, draw X)
        if rule is None:
            rule = self._try_pixel_count_diamond(patterns, wm)

        # Strategy 23: rotation tile 2×2 (NxM → 2N×2M by tiling 4 rotations)
        if rule is None:
            rule = self._try_rotate_tile_2x2(patterns, wm)

        # Strategy 24: diagonal extend (2×2 block + diagonal tails → extend to edges)
        if rule is None:
            rule = self._try_diagonal_extend(patterns, wm)

        # Strategy 25: quadrant diagonal fill (2×2 seed colors → fill corners)
        if rule is None:
            rule = self._try_quadrant_diagonal_fill(patterns, wm)

        # Strategy 26: corner ray projection to nearest grid corner
        if rule is None:
            rule = self._try_corner_ray(patterns, wm)

        # Strategy 28: count signal pixels in 1-bordered rect → fill 3×3
        if rule is None:
            rule = self._try_count_fill_grid(patterns, wm)

        # Strategy 29: grid intersection summary (large grid → small summary)
        if rule is None:
            rule = self._try_grid_intersection_summary(patterns, wm)

        # Strategy 30: frame color swap (extract rectangle, swap border/interior)
        if rule is None:
            rule = self._try_frame_color_swap(patterns, wm)

        # Strategy 31: tile pattern upward (bottom pattern fills entire grid)
        if rule is None:
            rule = self._try_tile_pattern_upward(patterns, wm)

        # Strategy 32: color substitution template (bordered rect + pair lookup)
        if rule is None:
            rule = self._try_color_substitution_template(patterns, wm)

        # Strategy 33: cross marker duplicate detection (1×1 output)
        if rule is None:
            rule = self._try_cross_marker_duplicate(patterns, wm)

        # Strategy 34: border flood fill (border-connected → color A, interior → B)
        if rule is None:
            rule = self._try_border_flood_fill(patterns, wm)

        # Strategy 35: separator histogram (scatter dots → bar chart in framed center)
        if rule is None:
            rule = self._try_separator_histogram(patterns, wm)

        # Strategy 36: rotation quadrant tile 4×4 (NxN → 4Nx4N rotation symmetry)
        if rule is None:
            rule = self._try_rotation_quadrant_tile_4x4(patterns, wm)

        # Strategy 37: self-tiling (NxN → N²xN², each non-zero cell → copy of input)
        if rule is None:
            rule = self._try_self_tiling(patterns, wm)

        # Strategy 38: double mirror / kaleidoscope (NxN → 2Nx2N)
        if rule is None:
            rule = self._try_double_mirror(patterns, wm)

        # Strategy 39: XOR comparison (two halves separated by row of X → 3 where XOR)
        if rule is None:
            rule = self._try_xor_comparison(patterns, wm)

        # Strategy 40: half-grid boolean (OR/AND/NOR/NAND between two halves)
        if rule is None:
            rule = self._try_half_grid_boolean(patterns, wm)

        # Strategy 41: inverse tile (invert 0↔color, tile 2×2)
        if rule is None:
            rule = self._try_inverse_tile(patterns, wm)

        # Strategy 42: grid separator max fill (fill cells with max non-zero count)
        if rule is None:
            rule = self._try_grid_separator_max_fill(patterns, wm)

        # Strategy 44: column shadow tile (mark 0s in non-zero cols → 8, tile 2×2)
        if rule is None:
            rule = self._try_column_shadow_tile(patterns, wm)

        # Strategy 45: concentric ring rotate (shift ring colors by 1 outward)
        if rule is None:
            rule = self._try_concentric_ring_rotate(patterns, wm)

        # Strategy 46: wedge expansion (seed line → triangle up/down)
        if rule is None:
            rule = self._try_wedge_expansion(patterns, wm)

        # Strategy 47: mirror row tile (each row → rev+row, tiled 2×)
        if rule is None:
            rule = self._try_mirror_row_tile(patterns, wm)

        # Strategy 48: larger interior rect (two rects → 2×2 of larger interior color)
        if rule is None:
            rule = self._try_larger_interior_rect(patterns, wm)

        # Strategy 58: rect minority gridlines (uniform rect + minority cells → grid lines)
        if rule is None:
            rule = self._try_rect_minority_gridlines(patterns, wm)

        # Strategy 59: rect directional tile (hollow rect + 1-lines → tile in direction)
        if rule is None:
            rule = self._try_rect_directional_tile(patterns, wm)

        # Strategy 60: corner block shift (corner blocks shift inward by block dims)
        if rule is None:
            rule = self._try_corner_block_shift(patterns, wm)

        # Strategy 61: grid section key lookup (5-line grid → key section maps positions to fill colors)
        if rule is None:
            rule = self._try_grid_section_key_lookup(patterns, wm)

        # Strategy 62: shape template catalog (key area templates + 3-shapes → recolor by shape match)
        if rule is None:
            rule = self._try_shape_template_catalog(patterns, wm)

        # Strategy 63: bar chart balance (bg=7, 8/2 bars at odd cols → add color-5 balance bar)
        if rule is None:
            rule = self._try_bar_chart_balance(patterns, wm)

        # Strategy 67: panel hole classify (3 panels with optional 2x2 holes → color code)
        if rule is None:
            rule = self._try_panel_hole_classify(patterns, wm)

        # Strategy 68: grid panel decode (N×M panel matrix → merge pattern+color)
        if rule is None:
            rule = self._try_grid_panel_decode(patterns, wm)

        # Strategy 69: shape gravity sort (objects reorder by enclosed vs open shape)
        if rule is None:
            rule = self._try_shape_gravity_sort(patterns, wm)

        # Strategy 71: stamp tile toward bar (3×3 stamp tiles toward matching color bar)
        if rule is None:
            rule = self._try_stamp_tile_toward_bar(patterns, wm)

        # Strategy 72: shape jigsaw assemble (scattered shapes → compact rectangle)
        if rule is None:
            rule = self._try_shape_jigsaw_assemble(patterns, wm)

        # Strategy 74: frame hole recolor (1-frame holes classify 5-shapes → recolor to 2)
        if rule is None:
            rule = self._try_frame_hole_recolor(patterns, wm)

        # Strategy 75: L-shape corner complete (mark missing corner of 3-cell L-shapes)
        if rule is None:
            rule = self._try_l_corner_complete(patterns, wm)

        # Strategy 76: quadrant locator (4x4 grid, find target color → fill its 2x2 quadrant)
        if rule is None:
            rule = self._try_quadrant_locator(patterns, wm)

        # Strategy 77: periodic pattern extend (remove border, extend repeating tile shifted +1 col)
        if rule is None:
            rule = self._try_periodic_pattern_extend(patterns, wm)

        # Strategy 78: cluster bounding box border (connected 2-clusters get 3-border)
        if rule is None:
            rule = self._try_cluster_bbox_border(patterns, wm)

        # Strategy 79: crop solid rect + horizontal flip
        if rule is None:
            rule = self._try_crop_rect_flip(patterns, wm)

        # Strategy 80: frame extract (extract 5/8 framed rectangle from noisy grid)
        if rule is None:
            rule = self._try_frame_extract(patterns, wm)

        # Strategy 81: marker shape extract (find shape containing marker 8, extract it)
        if rule is None:
            rule = self._try_marker_shape_extract(patterns, wm)

        # Strategy 82: template placeholder stamp (stamp template onto placeholder blocks)
        if rule is None:
            rule = self._try_template_placeholder_stamp(patterns, wm)

        # Strategy 83: unique quadrant extract (4 quadrants, extract the unique-color one)
        if rule is None:
            rule = self._try_unique_quadrant_extract(patterns, wm)

        # Strategy 84: self-ref grid fill (grid of blocks, hole at block position)
        if rule is None:
            rule = self._try_self_ref_grid_fill(patterns, wm)

        # Strategy 85: point reflect tile (NxM → 2Nx2M via rot180/vflip/hflip/orig quadrants)
        if rule is None:
            rule = self._try_point_reflect_tile(patterns, wm)

        # Strategy 86: nested rect color reverse (reverse color order of concentric rect layers)
        if rule is None:
            rule = self._try_nested_rect_color_reverse(patterns, wm)

        # Strategy 87: diagonal ring fill (diagonal color sequence fills rect interior as concentric rings)
        if rule is None:
            rule = self._try_diagonal_ring_fill(patterns, wm)

        # Strategy 88: denoise isolated pixels (remove 8-isolated single pixels)
        if rule is None:
            rule = self._try_denoise_isolated(patterns, wm)

        # Strategy 89: L-shape diagonal ray (shoot diagonal from missing 2x2 corner)
        if rule is None:
            rule = self._try_l_diagonal_ray(patterns, wm)

        # Strategy 90: nest rectangles by size (scattered rects → concentric nested output)
        if rule is None:
            rule = self._try_nest_rectangles(patterns, wm)

        # Strategy 91: column rank recolor (0s on uniform bg → color by column rank)
        if rule is None:
            rule = self._try_column_rank_recolor(patterns, wm)

        # Strategy 92: rect frame gap ray (rectangular frame with gap → fill interior + ray)
        if rule is None:
            rule = self._try_rect_frame_gap_ray(patterns, wm)

        # Strategy 93: asymmetric block select (3 stacked NxN blocks, select the non-diagonal-symmetric one)
        if rule is None:
            rule = self._try_asymmetric_block_select(patterns, wm)

        # Strategy 94: seed pixel stamp (isolated seed pixels → 3×3 diamond stamp)
        if rule is None:
            rule = self._try_seed_pixel_stamp(patterns, wm)

        # Strategy 95: color count expand (NxN input → each cell expands to KxK block, K=unique colors)
        if rule is None:
            rule = self._try_color_count_expand(patterns, wm)

        # Strategy 96: line rank recolor (5-lines ranked by length → 1/4/2)
        if rule is None:
            rule = self._try_line_rank_recolor(patterns, wm)

        # Strategy 97: max rect fill (fill maximal ≥2×2 rectangles of 0s with 1)
        if rule is None:
            rule = self._try_max_rect_fill(patterns, wm)

        # Strategy 98: divider complement merge (two halves: merge if complementary)
        if rule is None:
            rule = self._try_divider_complement_merge(patterns, wm)

        # Strategy 99: multi rect fill ray (fill all rectangular frames, ray from gap)
        if rule is None:
            rule = self._try_multi_rect_fill_ray(patterns, wm)

        # Strategy 100: corner seed symmetric frame (corner pixels → nested symmetric frames)
        if rule is None:
            rule = self._try_corner_seed_symmetric_frame(patterns, wm)

        # Strategy 101: frame corner projectile (L/U frame content → diagonal ray from corners)
        if rule is None:
            rule = self._try_frame_corner_projectile(patterns, wm)

        # Fallback: identity (copy input as output)
        if rule is None:
            rule = {"type": "identity", "confidence": 0.0}

        wm.s1["active-rules"] = [rule]

    # ---- strategy 67: panel hole classify --------------------------------

    def _try_panel_hole_classify(self, patterns, wm):
        """
        Detect: input is a 4-row grid with 3 panels (4 cols each) separated by
        single-column dividers of 0. Each panel is filled with color 5 but may
        have a 2×2 block of 0s at a specific position. Output is 3×3 where each
        row's color encodes the hole position of the corresponding panel.
        Category: grid panel feature classification / spatial encoding.
        """
        task = wm.task
        if not task or not task.example_pairs:
            return None

        # Check: all examples have 4-row input and 3-row output with 3 cols
        for pair in task.example_pairs:
            g0, g1 = pair.input_grid, pair.output_grid
            if not g0 or not g1:
                return None
            if len(g0.raw) != 4:
                return None
            if len(g1.raw) != 3 or (g1.raw and len(g1.raw[0]) != 3):
                return None

        # Check: input has column dividers of 0 at cols 4 and 9
        for pair in task.example_pairs:
            raw = pair.input_grid.raw
            w = len(raw[0]) if raw else 0
            if w != 14:
                return None
            for r in range(4):
                if raw[r][4] != 0 or raw[r][9] != 0:
                    return None

        # Build the position→color mapping from training examples
        pos_color_map = {}  # maps hole_position_key → output_color
        for pair in task.example_pairs:
            raw_in = pair.input_grid.raw
            raw_out = pair.output_grid.raw
            # Extract 3 panels: cols 0-3, 5-8, 10-13
            panel_starts = [0, 5, 10]
            for pidx, pc in enumerate(panel_starts):
                panel = []
                for r in range(4):
                    row = []
                    for c in range(pc, pc + 4):
                        row.append(raw_in[r][c])
                    panel.append(row)
                # Find hole position (2×2 block of 0s within the 4×4 panel)
                hole_key = self._panel_hole_key(panel)
                out_color = raw_out[pidx][0]  # all 3 cols same color
                # Verify all cols same
                if not all(raw_out[pidx][c] == out_color for c in range(3)):
                    return None
                if hole_key in pos_color_map:
                    if pos_color_map[hole_key] != out_color:
                        return None
                else:
                    pos_color_map[hole_key] = out_color

        if not pos_color_map:
            return None

        return {
            "type": "panel_hole_classify",
            "pos_color_map": pos_color_map,
            "confidence": 1.0,
        }

    @staticmethod
    def _panel_hole_key(panel):
        """Return a string key describing the hole position in a 4×4 panel."""
        # Find all 0-positions
        zeros = []
        for r in range(4):
            for c in range(4):
                if panel[r][c] == 0:
                    zeros.append((r, c))
        if not zeros:
            return "none"
        # Sort and create a canonical key
        zeros.sort()
        return str(zeros)

    # ---- strategy 68: grid panel decode ----------------------------------

    def _try_grid_panel_decode(self, patterns, wm):
        """
        Detect: input is a grid of NxM panels separated by lines of a separator
        color (e.g. 8). Each panel has a 1-border. Within each column of panels,
        exactly one panel is solid-filled with a non-pattern color, and the rest
        have a 2/bg pattern. The output merges each column's pattern with its
        solid color, using the solid panel's row-label as border color.
        Category: grid panel key/pattern merge / lookup table.
        """
        task = wm.task
        if not task or not task.example_pairs:
            return None

        # Work from the first example pair
        pair0 = task.example_pairs[0]
        g0, g1 = pair0.input_grid, pair0.output_grid
        if not g0 or not g1:
            return None
        raw = g0.raw
        H = len(raw)
        W = len(raw[0]) if raw else 0
        if H < 7 or W < 7:
            return None

        # Find separator color: the color of row 0 (should be uniform)
        sep = raw[0][0]
        if not all(raw[0][c] == sep for c in range(W)):
            return None

        # Find horizontal separator rows (entire row == sep)
        h_seps = []
        for r in range(H):
            if all(raw[r][c] == sep for c in range(W)):
                h_seps.append(r)

        # Find vertical separator cols (entire col == sep)
        v_seps = []
        for c in range(W):
            if all(raw[r][c] == sep for r in range(H)):
                v_seps.append(c)

        if len(h_seps) < 2 or len(v_seps) < 1:
            return None

        # Extract panel row bands and column bands
        row_bands = []  # list of (start_row, end_row) exclusive
        for i in range(len(h_seps) - 1):
            r0 = h_seps[i] + 1
            r1 = h_seps[i + 1]
            if r1 > r0:
                row_bands.append((r0, r1))

        col_bands = []
        # Add bands between vertical separators
        all_v = sorted(set(v_seps))
        # Find contiguous separator groups
        v_groups = []
        i = 0
        while i < len(all_v):
            start = all_v[i]
            while i + 1 < len(all_v) and all_v[i + 1] == all_v[i] + 1:
                i += 1
            v_groups.append((start, all_v[i]))
            i += 1

        # Column bands are between consecutive v_groups (and edges)
        prev_end = -1
        for vg_start, vg_end in v_groups:
            if vg_start > prev_end + 1:
                col_bands.append((prev_end + 1, vg_start))
            prev_end = vg_end
        # Last band after the last v_group
        if prev_end < W - 1:
            col_bands.append((prev_end + 1, W))

        if len(row_bands) < 2 or len(col_bands) < 2:
            return None

        # Extract row labels (first non-sep column in each panel row)
        row_labels = []
        for r0, r1 in row_bands:
            # The label is typically the color in column 0 of each row band
            label = None
            for r in range(r0, r1):
                c0_val = raw[r][0]
                if c0_val != sep:
                    label = c0_val
                    break
            row_labels.append(label)

        # Each panel has a 1-border; extract interior
        def get_panel_interior(r0, r1, c0, c1):
            """Extract the interior of a panel (skip 1-cell border of 1s)."""
            # Find the border color (typically 1)
            border_r0 = r0
            border_c0 = c0
            # Check if first col is a label column (non-1, non-sep)
            first_col_val = raw[border_r0][border_c0]
            if first_col_val != 1 and first_col_val != sep:
                border_c0 += 1  # skip label column

            # Now find the 1-border region
            # The interior is surrounded by 1s
            interior = []
            for r in range(border_r0 + 1, r1 - 1):
                row = []
                for c in range(border_c0 + 1, c1 - 1):
                    row.append(raw[r][c])
                if row:
                    interior.append(row)
            return interior

        # For each column of panels, identify solid vs pattern panels
        n_rows = len(row_bands)
        n_cols = len(col_bands)

        panel_grid = []
        for ri, (r0, r1) in enumerate(row_bands):
            panel_row = []
            for ci, (c0, c1) in enumerate(col_bands):
                interior = get_panel_interior(r0, r1, c0, c1)
                panel_row.append(interior)
            panel_grid.append(panel_row)

        # For each column, find which panel is solid (all same non-bg color)
        col_info = []
        pattern_color = None  # the color used in patterns (typically 2)
        for ci in range(n_cols):
            solid_ri = None
            solid_color = None
            pattern_interior = None
            for ri in range(n_rows):
                interior = panel_grid[ri][ci]
                if not interior or not interior[0]:
                    continue
                # Check if all cells are the same non-sep, non-pattern color
                colors = set()
                for row in interior:
                    for v in row:
                        colors.add(v)
                if len(colors) == 1:
                    c_val = colors.pop()
                    if c_val != sep:
                        solid_ri = ri
                        solid_color = c_val
                else:
                    # This is a pattern panel - should contain 2 and bg
                    pattern_interior = interior
                    for row in interior:
                        for v in row:
                            if v != sep and pattern_color is None:
                                # First non-sep in pattern is the pattern color
                                pass
                    # Detect pattern color (the non-sep color in patterns)
                    for row in interior:
                        for v in row:
                            if v != sep:
                                pattern_color = v
                                break
                        if pattern_color is not None:
                            break

            if solid_ri is None or pattern_interior is None:
                return None
            col_info.append({
                "solid_ri": solid_ri,
                "solid_color": solid_color,
                "pattern": pattern_interior,
                "label": row_labels[solid_ri],
            })

        if not col_info or pattern_color is None:
            return None

        # Verify against output of first example
        out_raw = g1.raw
        out_H = len(out_raw)
        out_W = len(out_raw[0]) if out_raw else 0

        # Output should be one row of panels
        # Each output panel: border = label color, interior = pattern with pattern_color → solid_color
        # Verify by reconstruction
        expected = self._build_grid_panel_decode_output(col_info, pattern_color, sep, raw, row_bands, col_bands)
        if expected is None:
            return None

        if len(expected) != out_H or (expected and len(expected[0]) != out_W):
            return None
        for r in range(out_H):
            for c in range(out_W):
                if expected[r][c] != out_raw[r][c]:
                    return None

        # Verify all examples
        for pair in task.example_pairs[1:]:
            gi, go = pair.input_grid, pair.output_grid
            if not gi or not go:
                return None
            test_result = self._decode_grid_panels(gi.raw)
            if test_result is None:
                return None
            exp = test_result
            if len(exp) != len(go.raw):
                return None
            for r in range(len(exp)):
                if len(exp[r]) != len(go.raw[r]):
                    return None
                for c in range(len(exp[r])):
                    if exp[r][c] != go.raw[r][c]:
                        return None

        return {
            "type": "grid_panel_decode",
            "confidence": 1.0,
        }

    @staticmethod
    def _decode_grid_panels(raw):
        """Full decode of a grid-panel-matrix input → merged output."""
        H = len(raw)
        W = len(raw[0]) if raw else 0
        if H < 7 or W < 7:
            return None

        sep = raw[0][0]
        if not all(raw[0][c] == sep for c in range(W)):
            return None

        h_seps = [r for r in range(H) if all(raw[r][c] == sep for c in range(W))]
        v_seps = [c for c in range(W) if all(raw[r][c] == sep for r in range(H))]
        if len(h_seps) < 2 or len(v_seps) < 1:
            return None

        row_bands = []
        for i in range(len(h_seps) - 1):
            r0, r1 = h_seps[i] + 1, h_seps[i + 1]
            if r1 > r0:
                row_bands.append((r0, r1))

        all_v = sorted(set(v_seps))
        v_groups = []
        i = 0
        while i < len(all_v):
            start = all_v[i]
            while i + 1 < len(all_v) and all_v[i + 1] == all_v[i] + 1:
                i += 1
            v_groups.append((start, all_v[i]))
            i += 1

        col_bands = []
        prev_end = -1
        for vg_start, vg_end in v_groups:
            if vg_start > prev_end + 1:
                col_bands.append((prev_end + 1, vg_start))
            prev_end = vg_end
        if prev_end < W - 1:
            col_bands.append((prev_end + 1, W))

        if len(row_bands) < 2 or len(col_bands) < 2:
            return None

        row_labels = []
        for r0, r1 in row_bands:
            label = None
            for r in range(r0, r1):
                if raw[r][0] != sep:
                    label = raw[r][0]
                    break
            row_labels.append(label)

        n_rows = len(row_bands)
        n_cols = len(col_bands)

        def get_interior(r0, r1, c0, c1):
            bc0 = c0
            if raw[r0][bc0] != 1 and raw[r0][bc0] != sep:
                bc0 += 1
            interior = []
            for r in range(r0 + 1, r1 - 1):
                row = []
                for c in range(bc0 + 1, c1 - 1):
                    row.append(raw[r][c])
                if row:
                    interior.append(row)
            return interior

        panel_grid = []
        for ri, (r0, r1) in enumerate(row_bands):
            panel_row = []
            for ci, (c0, c1) in enumerate(col_bands):
                panel_row.append(get_interior(r0, r1, c0, c1))
            panel_grid.append(panel_row)

        col_info = []
        for ci in range(n_cols):
            solid_ri = None
            solid_color = None
            pattern_interior = None
            for ri in range(n_rows):
                interior = panel_grid[ri][ci]
                if not interior or not interior[0]:
                    continue
                colors = set()
                for row in interior:
                    for v in row:
                        colors.add(v)
                if len(colors) == 1:
                    c_val = colors.pop()
                    if c_val != sep:
                        solid_ri = ri
                        solid_color = c_val
                else:
                    pattern_interior = interior

            if solid_ri is None or pattern_interior is None:
                return None
            col_info.append({
                "solid_ri": solid_ri,
                "solid_color": solid_color,
                "pattern": pattern_interior,
                "label": row_labels[solid_ri],
            })

        if not col_info:
            return None

        # Detect pattern color (non-sep color appearing in pattern interiors)
        pattern_color = None
        for ci_data in col_info:
            for row in ci_data["pattern"]:
                for v in row:
                    if v != sep:
                        pattern_color = v
                        break
                if pattern_color is not None:
                    break
            if pattern_color is not None:
                break

        if pattern_color is None:
            return None

        # Build output: one row of panels separated by sep columns
        # Each panel = border of label + interior with pattern_color → solid_color
        panel_h = len(col_info[0]["pattern"])
        panel_w = len(col_info[0]["pattern"][0]) if col_info[0]["pattern"] else 0

        out_panel_h = panel_h + 2  # with border
        out_panel_w = panel_w + 2

        out_W = n_cols * out_panel_w + (n_cols - 1)  # panels + sep cols
        out_H = out_panel_h
        output = [[sep] * out_W for _ in range(out_H)]

        for ci, ci_data in enumerate(col_info):
            label = ci_data["label"]
            solid_color = ci_data["solid_color"]
            pat = ci_data["pattern"]
            oc = ci * (out_panel_w + 1)  # output column start

            # Draw border
            for r in range(out_panel_h):
                for c in range(out_panel_w):
                    if r == 0 or r == out_panel_h - 1 or c == 0 or c == out_panel_w - 1:
                        output[r][oc + c] = label
            # Draw interior
            for r in range(panel_h):
                for c in range(panel_w):
                    val = pat[r][c]
                    if val == pattern_color:
                        output[1 + r][oc + 1 + c] = solid_color
                    else:
                        output[1 + r][oc + 1 + c] = val

        return output

    @staticmethod
    def _build_grid_panel_decode_output(col_info, pattern_color, sep, raw, row_bands, col_bands):
        """Build expected output from decoded panel info."""
        n_cols = len(col_info)
        if not col_info:
            return None
        panel_h = len(col_info[0]["pattern"])
        panel_w = len(col_info[0]["pattern"][0]) if col_info[0]["pattern"] else 0

        out_panel_h = panel_h + 2
        out_panel_w = panel_w + 2
        out_W = n_cols * out_panel_w + (n_cols - 1)
        out_H = out_panel_h
        output = [[sep] * out_W for _ in range(out_H)]

        for ci, ci_data in enumerate(col_info):
            label = ci_data["label"]
            solid_color = ci_data["solid_color"]
            pat = ci_data["pattern"]
            oc = ci * (out_panel_w + 1)

            for r in range(out_panel_h):
                for c in range(out_panel_w):
                    if r == 0 or r == out_panel_h - 1 or c == 0 or c == out_panel_w - 1:
                        output[r][oc + c] = label
            for r in range(panel_h):
                for c in range(panel_w):
                    val = pat[r][c]
                    if val == pattern_color:
                        output[1 + r][oc + 1 + c] = solid_color
                    else:
                        output[1 + r][oc + 1 + c] = val

        return output

    # ---- strategy 69: shape gravity sort ---------------------------------

    def _try_shape_gravity_sort(self, patterns, wm):
        """
        Detect: input has multiple distinct colored shapes on a bg=0 grid.
        Shapes are categorized as 'enclosed' (rectangles with interior holes)
        vs 'open' (crosses, lines). Enclosed shapes move to top, open shapes
        to bottom. The grid size stays the same.
        Category: shape classification / spatial reorganization.
        """
        task = wm.task
        if not task or not task.example_pairs:
            return None

        # Verify grid sizes preserved
        for pair in task.example_pairs:
            g0, g1 = pair.input_grid, pair.output_grid
            if not g0 or not g1:
                return None
            if len(g0.raw) != len(g1.raw):
                return None
            if len(g0.raw[0]) != len(g1.raw[0]):
                return None

        # Quick check: first example must have >=3 objects with both enclosed and open
        raw_in = task.example_pairs[0].input_grid.raw
        objects_in = self._find_colored_objects(raw_in)
        if len(objects_in) < 3:
            return None

        has_enclosed = False
        has_open = False
        for obj in objects_in:
            cells = obj["cells"]
            cell_set = set(cells)
            rows = [r for r, c in cells]
            cols = [c for r, c in cells]
            min_r, max_r = min(rows), max(rows)
            min_c, max_c = min(cols), max(cols)
            is_enc = False
            for r in range(min_r, max_r + 1):
                for c in range(min_c, max_c + 1):
                    if (r, c) not in cell_set:
                        if self._is_interior_cell(r, c, cell_set, min_r, max_r, min_c, max_c):
                            is_enc = True
                            break
                if is_enc:
                    break
            if is_enc:
                has_enclosed = True
            else:
                has_open = True

        if not has_enclosed or not has_open:
            return None

        # Verify by applying to ALL examples
        for pair in task.example_pairs:
            result = self._apply_shape_gravity_sort_grid(pair.input_grid.raw)
            if result is None:
                return None
            out = pair.output_grid.raw
            if len(result) != len(out):
                return None
            for r in range(len(result)):
                if result[r] != out[r]:
                    return None

        return {
            "type": "shape_gravity_sort",
            "confidence": 1.0,
        }

    @staticmethod
    def _find_colored_objects(grid):
        """Find connected components of non-zero cells, grouped by color."""
        H = len(grid)
        W = len(grid[0]) if grid else 0
        visited = set()
        objects = []

        for r in range(H):
            for c in range(W):
                if grid[r][c] != 0 and (r, c) not in visited:
                    color = grid[r][c]
                    # BFS to find all connected cells of same color
                    cells = []
                    queue = [(r, c)]
                    while queue:
                        cr, cc = queue.pop(0)
                        if (cr, cc) in visited:
                            continue
                        if cr < 0 or cr >= H or cc < 0 or cc >= W:
                            continue
                        if grid[cr][cc] != color:
                            continue
                        visited.add((cr, cc))
                        cells.append((cr, cc))
                        for dr, dc in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                            nr, nc = cr + dr, cc + dc
                            if 0 <= nr < H and 0 <= nc < W and (nr, nc) not in visited:
                                queue.append((nr, nc))
                    objects.append({"color": color, "cells": cells})
        return objects

    @staticmethod
    def _is_interior_cell(r, c, cell_set, min_r, max_r, min_c, max_c):
        """Check if (r,c) is enclosed by cell_set (can't reach bbox boundary through 0s)."""
        visited = set()
        queue = [(r, c)]
        while queue:
            cr, cc = queue.pop(0)
            if (cr, cc) in visited:
                continue
            if (cr, cc) in cell_set:
                continue
            visited.add((cr, cc))
            if cr <= min_r or cr >= max_r or cc <= min_c or cc >= max_c:
                return False  # reached boundary = not interior
            for dr, dc in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                nr, nc = cr + dr, cc + dc
                if (nr, nc) not in visited:
                    queue.append((nr, nc))
        return True

    def _apply_shape_gravity_sort_grid(self, raw):
        """Apply shape gravity sort to a grid.
        Enclosed shapes pack to top, open shapes pack to bottom.
        Column positions preserved; shapes stack when columns overlap."""
        H = len(raw)
        W = len(raw[0]) if raw else 0
        objects = self._find_colored_objects(raw)
        if len(objects) < 3:
            return None

        # Classify
        enclosed = []
        open_objs = []
        for obj in objects:
            cells = obj["cells"]
            cell_set = set(cells)
            rows = [r for r, c in cells]
            cols = [c for r, c in cells]
            min_r, max_r = min(rows), max(rows)
            min_c, max_c = min(cols), max(cols)
            is_enc = False
            for r in range(min_r, max_r + 1):
                for c in range(min_c, max_c + 1):
                    if (r, c) not in cell_set:
                        if self._is_interior_cell(r, c, cell_set, min_r, max_r, min_c, max_c):
                            is_enc = True
                            break
                if is_enc:
                    break
            if is_enc:
                enclosed.append(obj)
            else:
                open_objs.append(obj)

        if not enclosed or not open_objs:
            return None

        output = [[0] * W for _ in range(H)]

        # Sort by original top-row
        enclosed.sort(key=lambda o: min(r for r, c in o["cells"]))
        open_objs.sort(key=lambda o: min(r for r, c in o["cells"]))

        # Pack enclosed objects from top using column height map
        col_height = [0] * W  # next available row for each column
        for obj in enclosed:
            cells = obj["cells"]
            min_r = min(r for r, c in cells)
            cols_used = set(c for r, c in cells)
            # Find the offset: the object needs to start at the max of col_height
            # for all columns it occupies
            start_row = max(col_height[c] for c in cols_used)
            shift = start_row - min_r
            for r, c in cells:
                nr = r + shift
                if 0 <= nr < H and 0 <= c < W:
                    output[nr][c] = obj["color"]
            # Update height map
            for r, c in cells:
                nr = r + shift
                col_height[c] = max(col_height[c], nr + 1)

        # Pack open objects from bottom using column floor map
        col_floor = [H - 1] * W  # lowest available row for each column
        for obj in reversed(open_objs):
            cells = obj["cells"]
            max_r = max(r for r, c in cells)
            cols_used = set(c for r, c in cells)
            # Object bottom edge needs to be at min of col_floor
            end_row = min(col_floor[c] for c in cols_used)
            shift = end_row - max_r
            for r, c in cells:
                nr = r + shift
                if 0 <= nr < H and 0 <= c < W:
                    output[nr][c] = obj["color"]
            # Update floor map
            for r, c in cells:
                nr = r + shift
                col_floor[c] = min(col_floor[c], nr - 1)

        return output

    # ---- strategy 52: pixel collect snake --------------------------------

    def _try_pixel_collect_snake(self, patterns, wm):
        """
        Detect: sparse grid (mostly 0s) with scattered single non-zero pixels.
        Output is a smaller grid (e.g. 3×3) filled by sorting pixels by column
        and placing them in boustrophedon (snake) order: even rows L→R, odd rows R→L.
        Category: pixel collection / spatial sorting into compact grids.
        """
        task = wm.task
        if task is None:
            return None

        out_rows = out_cols = None

        for pair in task.example_pairs:
            g0, g1 = pair.input_grid, pair.output_grid
            if g0 is None or g1 is None:
                return None
            raw_in, raw_out = g0.raw, g1.raw
            H_in = len(raw_in)
            W_in = len(raw_in[0]) if raw_in else 0
            H_out = len(raw_out)
            W_out = len(raw_out[0]) if raw_out else 0

            # Output must be smaller than input
            if H_out >= H_in or W_out >= W_in:
                return None

            # Collect non-zero pixels from input, sorted by column then row
            pixels = []
            for r in range(H_in):
                for c in range(W_in):
                    if raw_in[r][c] != 0:
                        pixels.append((c, r, raw_in[r][c]))
            # Sort by column (primary), then row (secondary)
            pixels.sort(key=lambda p: (p[0], p[1]))

            # Must fit into output grid
            if len(pixels) > H_out * W_out:
                return None

            # Place in boustrophedon order and verify
            expected = [[0] * W_out for _ in range(H_out)]
            idx = 0
            for row in range(H_out):
                if row % 2 == 0:
                    cols = range(W_out)
                else:
                    cols = range(W_out - 1, -1, -1)
                for col in cols:
                    if idx < len(pixels):
                        expected[row][col] = pixels[idx][2]
                        idx += 1

            # Verify against actual output
            for r in range(H_out):
                for c in range(W_out):
                    if expected[r][c] != raw_out[r][c]:
                        return None

            # Check consistent output size
            if out_rows is None:
                out_rows = H_out
                out_cols = W_out
            elif out_rows != H_out or out_cols != W_out:
                return None

        return {"type": "pixel_collect_snake", "out_rows": out_rows,
                "out_cols": out_cols, "confidence": 1.0}

    # ---- strategy 53: frame scale pattern --------------------------------

    def _try_frame_scale_pattern(self, patterns, wm):
        """
        Detect: rectangular frame of color F on bg 0, with a 2×2 quadrant
        color pattern inside. Output crops to the frame and scales the 2×2
        pattern to fill the entire interior evenly.
        Category: crop + scale-up / frame extraction with pattern expansion.
        """
        task = wm.task
        if task is None:
            return None

        for pair in task.example_pairs:
            g0, g1 = pair.input_grid, pair.output_grid
            if g0 is None or g1 is None:
                return None
            raw_in, raw_out = g0.raw, g1.raw
            H_in = len(raw_in)
            W_in = len(raw_in[0]) if raw_in else 0
            H_out = len(raw_out)
            W_out = len(raw_out[0]) if raw_out else 0

            # Find the frame: a rectangle of uniform non-zero color
            frame_color = None
            fr_top = fr_bot = fr_left = fr_right = None
            for r in range(H_in):
                for c in range(W_in):
                    v = raw_in[r][c]
                    if v != 0:
                        if frame_color is None:
                            frame_color = v
                        if v == frame_color:
                            if fr_top is None or r < fr_top:
                                fr_top = r
                            if fr_bot is None or r > fr_bot:
                                fr_bot = r
                            if fr_left is None or c < fr_left:
                                fr_left = c
                            if fr_right is None or c > fr_right:
                                fr_right = c
            if frame_color is None or fr_top is None:
                return None

            # Verify frame border: top/bottom rows and left/right cols should be frame_color
            for c in range(fr_left, fr_right + 1):
                if raw_in[fr_top][c] != frame_color or raw_in[fr_bot][c] != frame_color:
                    return None
            for r in range(fr_top, fr_bot + 1):
                if raw_in[r][fr_left] != frame_color or raw_in[r][fr_right] != frame_color:
                    return None

            int_top = fr_top + 1
            int_bot = fr_bot - 1
            int_left = fr_left + 1
            int_right = fr_right - 1
            int_h = int_bot - int_top + 1
            int_w = int_right - int_left + 1

            if int_h < 2 or int_w < 2:
                return None

            # Find the 2×2 quadrant pattern inside the frame
            # Collect non-zero non-frame cells in the interior
            pattern_cells = []
            for r in range(int_top, int_bot + 1):
                for c in range(int_left, int_right + 1):
                    v = raw_in[r][c]
                    if v != 0 and v != frame_color:
                        pattern_cells.append((r, c, v))

            if not pattern_cells:
                return None

            # Find bounding box of pattern
            pr_min = min(r for r, c, v in pattern_cells)
            pr_max = max(r for r, c, v in pattern_cells)
            pc_min = min(c for r, c, v in pattern_cells)
            pc_max = max(c for r, c, v in pattern_cells)

            pat_h = pr_max - pr_min + 1
            pat_w = pc_max - pc_min + 1

            # Must be even dimensions (2×2 pattern potentially scaled)
            if pat_h % 2 != 0 or pat_w % 2 != 0:
                return None

            half_h = pat_h // 2
            half_w = pat_w // 2

            # Extract the 4 quadrant colors
            tl_color = raw_in[pr_min][pc_min]
            tr_color = raw_in[pr_min][pc_min + half_w]
            bl_color = raw_in[pr_min + half_h][pc_min]
            br_color = raw_in[pr_min + half_h][pc_min + half_w]

            if any(c == 0 or c == frame_color for c in [tl_color, tr_color, bl_color, br_color]):
                return None

            # Verify all pattern cells match their quadrant
            for r, c, v in pattern_cells:
                qr = 0 if r < pr_min + half_h else 1
                qc = 0 if c < pc_min + half_w else 1
                expected_color = [tl_color, tr_color, bl_color, br_color][qr * 2 + qc]
                if v != expected_color:
                    return None

            # Interior must be evenly divisible into 4 quadrants
            if int_h % 2 != 0 or int_w % 2 != 0:
                return None

            # Verify output: should be the frame with scaled pattern
            expected_h = fr_bot - fr_top + 1
            expected_w = fr_right - fr_left + 1
            if H_out != expected_h or W_out != expected_w:
                return None

            q_h = int_h // 2
            q_w = int_w // 2
            for r in range(H_out):
                for c in range(W_out):
                    if r == 0 or r == H_out - 1 or c == 0 or c == W_out - 1:
                        if raw_out[r][c] != frame_color:
                            return None
                    else:
                        ir = r - 1  # interior row
                        ic = c - 1  # interior col
                        qr = 0 if ir < q_h else 1
                        qc = 0 if ic < q_w else 1
                        expected_color = [tl_color, tr_color, bl_color, br_color][qr * 2 + qc]
                        if raw_out[r][c] != expected_color:
                            return None

        return {"type": "frame_scale_pattern", "confidence": 1.0}

    # ---- strategy 54: box slide trail ------------------------------------

    def _try_box_slide_trail(self, patterns, wm):
        """
        Detect: 3×3 box of border_color (2) with center_color (3) inside,
        plus a trail of center_color dots spaced 2 apart along the same
        row/column. The box slides 1 step (2 cells) along the trail toward
        the side with more dots (or positive direction if tied).
        Category: object translation / sliding along marker path.
        """
        task = wm.task
        if task is None:
            return None

        for pair in task.example_pairs:
            g0, g1 = pair.input_grid, pair.output_grid
            if g0 is None or g1 is None:
                return None
            raw_in, raw_out = g0.raw, g1.raw
            H = len(raw_in)
            W = len(raw_in[0]) if raw_in else 0
            if len(raw_out) != H or (raw_out and len(raw_out[0]) != W):
                return None

            # Find the 3×3 box: look for a 3×3 block where border is one color
            # and center is another color
            box_found = False
            for r in range(H - 2):
                for c in range(W - 2):
                    center_val = raw_in[r + 1][c + 1]
                    if center_val == 0:
                        continue
                    border_val = raw_in[r][c]
                    if border_val == 0 or border_val == center_val:
                        continue
                    # Check all 8 border cells
                    is_box = True
                    for dr in range(3):
                        for dc in range(3):
                            if dr == 1 and dc == 1:
                                continue
                            if raw_in[r + dr][c + dc] != border_val:
                                is_box = False
                                break
                        if not is_box:
                            break
                    if is_box:
                        box_r, box_c = r, c
                        box_found = True
                        break
                if box_found:
                    break
            if not box_found:
                return None

            center_r = box_r + 1
            center_c = box_c + 1
            center_val = raw_in[center_r][center_c]
            border_val = raw_in[box_r][box_c]

            # Find trail: same-color dots along the center row or col
            h_trail = []
            for c in range(W):
                if raw_in[center_r][c] == center_val and not (box_c <= c <= box_c + 2):
                    h_trail.append(c)

            v_trail = []
            for r in range(H):
                if raw_in[r][center_c] == center_val and not (box_r <= r <= box_r + 2):
                    v_trail.append(r)

            if not h_trail and not v_trail:
                return None

            # Determine direction
            if h_trail:
                left_count = sum(1 for c in h_trail if c < box_c)
                right_count = sum(1 for c in h_trail if c > box_c + 2)
                if right_count > left_count:
                    dr, dc = 0, 2
                elif left_count > right_count:
                    dr, dc = 0, -2
                else:
                    dr, dc = 0, 2  # tie → positive direction
            else:
                above_count = sum(1 for r in v_trail if r < box_r)
                below_count = sum(1 for r in v_trail if r > box_r + 2)
                if below_count > above_count:
                    dr, dc = 2, 0
                elif above_count > below_count:
                    dr, dc = -2, 0
                else:
                    dr, dc = 2, 0  # tie ��� positive direction

            # Build expected output: move box by (dr, dc)
            new_box_r = box_r + dr
            new_box_c = box_c + dc
            if new_box_r < 0 or new_box_r + 2 >= H or new_box_c < 0 or new_box_c + 2 >= W:
                return None

            expected = [[0] * W for _ in range(H)]
            # Copy trail dots and other content
            for r in range(H):
                for c in range(W):
                    expected[r][c] = raw_in[r][c]

            # Erase old box
            for drr in range(3):
                for dcc in range(3):
                    expected[box_r + drr][box_c + dcc] = 0

            # The old center becomes a trail dot
            expected[center_r][center_c] = center_val

            # Place new box
            new_center_r = new_box_r + 1
            new_center_c = new_box_c + 1
            for drr in range(3):
                for dcc in range(3):
                    if drr == 1 and dcc == 1:
                        expected[new_box_r + drr][new_box_c + dcc] = center_val
                    else:
                        expected[new_box_r + drr][new_box_c + dcc] = border_val

            # Verify against actual output
            for r in range(H):
                for c in range(W):
                    if expected[r][c] != raw_out[r][c]:
                        return None

        return {"type": "box_slide_trail", "confidence": 1.0}

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

    # ---- strategy: reverse concentric rings ------------------------------

    def _try_reverse_concentric_rings(self, patterns, wm):
        """
        Detect pattern: grid consists of concentric rectangular rings, each
        of uniform color. Output reverses the ring order (innermost ↔ outermost).
        """
        task = wm.task
        if not task or not patterns.get("grid_size_preserved"):
            return None

        for pair in task.example_pairs:
            g0, g1 = pair.input_grid, pair.output_grid
            if not g0 or not g1:
                return None
            raw_in, raw_out = g0.raw, g1.raw
            h = len(raw_in)
            w = len(raw_in[0]) if raw_in else 0

            num_rings = (min(h, w) + 1) // 2
            if num_rings < 2:
                return None

            in_rings = [None] * num_rings
            out_rings = [None] * num_rings

            valid = True
            for r in range(h):
                for c in range(w):
                    d = min(r, c, h - 1 - r, w - 1 - c)
                    if in_rings[d] is None:
                        in_rings[d] = raw_in[r][c]
                    elif in_rings[d] != raw_in[r][c]:
                        valid = False
                        break
                    if out_rings[d] is None:
                        out_rings[d] = raw_out[r][c]
                    elif out_rings[d] != raw_out[r][c]:
                        valid = False
                        break
                if not valid:
                    break

            if not valid:
                return None

            # All ring colors must be distinct in input
            if len(set(in_rings)) != num_rings:
                return None

            # Output rings must be the reverse of input rings
            if out_rings != list(reversed(in_rings)):
                return None

        return {"type": "reverse_concentric_rings", "confidence": 1.0}

    # ---- strategy: keep center column ------------------------------------

    def _try_keep_center_column(self, patterns, wm):
        """
        Detect pattern: output preserves only the center column of the input
        grid, setting all other cells to zero (or background).
        """
        task = wm.task
        if not task or not patterns.get("grid_size_preserved"):
            return None

        bg_color = 0

        for pair in task.example_pairs:
            g0, g1 = pair.input_grid, pair.output_grid
            if not g0 or not g1:
                return None
            raw_in, raw_out = g0.raw, g1.raw
            h = len(raw_in)
            w = len(raw_in[0]) if raw_in else 0

            if w < 3 or w % 2 == 0:
                return None

            mid_c = w // 2

            for r in range(h):
                for c in range(w):
                    if c == mid_c:
                        if raw_out[r][c] != raw_in[r][c]:
                            return None
                    else:
                        if raw_out[r][c] != bg_color:
                            return None

        return {"type": "keep_center_column", "bg_color": bg_color, "confidence": 0.9}

    # ---- strategy: mirror symmetry recolor --------------------------------

    def _try_mirror_symmetry_recolor(self, patterns, wm):
        """
        Detect pattern: grid has bg=0 and one fg color (e.g. 5). For each row,
        fg cells that have a symmetric partner across the vertical center axis
        become a new color (e.g. 1), while unpaired fg cells stay unchanged.
        Category: symmetric-pair detection tasks.
        """
        task = wm.task
        if task is None:
            return None
        if not patterns.get("grid_size_preserved"):
            return None

        for pair in task.example_pairs:
            g0, g1 = pair.input_grid, pair.output_grid
            if g0 is None or g1 is None:
                return None
            raw_in, raw_out = g0.raw, g1.raw
            H, W = len(raw_in), len(raw_in[0])

            # Detect: exactly 2 non-bg colors in input, same grid size
            colors_in = set()
            for r in range(H):
                for c in range(W):
                    if raw_in[r][c] != 0:
                        colors_in.add(raw_in[r][c])
            if len(colors_in) != 1:
                return None
            fg_color = colors_in.pop()

            # Output should have fg_color and exactly one new_color (not in input)
            colors_out = set()
            for r in range(H):
                for c in range(W):
                    v = raw_out[r][c]
                    if v != 0 and v != fg_color:
                        colors_out.add(v)
            if len(colors_out) != 1:
                return None
            new_color = colors_out.pop()

            # Verify the mirror symmetry rule: paired fg cells → new_color
            for r in range(H):
                for c in range(W):
                    if raw_in[r][c] == fg_color:
                        mirror_c = W - 1 - c
                        has_partner = raw_in[r][mirror_c] == fg_color
                        expected = new_color if has_partner else fg_color
                        if raw_out[r][c] != expected:
                            return None

        return {
            "type": "mirror_symmetry_recolor",
            "fg_color": fg_color,
            "new_color": new_color,
            "confidence": 0.95,
        }

    # ---- strategy: rect-pixel bridge connection ----------------------------

    def _try_rect_pixel_bridge(self, patterns, wm):
        """
        Detect pattern: bg grid has colored rectangles (solid blocks) and
        isolated single pixels of the same color. Each isolated pixel connects
        to the nearest edge of its same-color rect via a bridge line, the pixel
        shifts 1 cell further, and perpendicular marks appear at bridge start
        and pixel original position.
        Category: object connection/attraction tasks.
        """
        task = wm.task
        if task is None:
            return None
        if not patterns.get("grid_size_preserved"):
            return None

        # Need at least 2 examples to validate
        if len(task.example_pairs) < 2:
            return None

        validated_any = False
        for pair in task.example_pairs:
            g0, g1 = pair.input_grid, pair.output_grid
            if g0 is None or g1 is None:
                return None
            raw_in, raw_out = g0.raw, g1.raw
            H, W = len(raw_in), len(raw_in[0])
            if len(raw_out) != H or len(raw_out[0]) != W:
                return None

            bg = self._rect_pixel_detect_bg(raw_in, H, W)
            if bg is None:
                return None

            # Find all non-bg colors
            color_cells = {}
            for r in range(H):
                for c in range(W):
                    v = raw_in[r][c]
                    if v != bg:
                        color_cells.setdefault(v, []).append((r, c))

            if not color_cells:
                return None

            # For each color, find rects and isolated pixels
            pair_had_bridge = False
            for color, cells in color_cells.items():
                rects, isolates = self._find_rects_and_isolates(cells, color, raw_in, H, W, bg)
                if not rects:
                    continue
                if not isolates:
                    continue

                pair_had_bridge = True

                # Verify bridge pattern for each isolated pixel
                predicted = [row[:] for row in raw_in]
                for iso_r, iso_c in isolates:
                    self._draw_bridge(predicted, rects, iso_r, iso_c, color, bg, H, W)

                # Check if predicted matches output for this color's changes
                for r in range(H):
                    for c in range(W):
                        if raw_in[r][c] == color or predicted[r][c] == color:
                            if predicted[r][c] != raw_out[r][c]:
                                return None

            if pair_had_bridge:
                validated_any = True

        if not validated_any:
            return None

        return {
            "type": "rect_pixel_bridge",
            "confidence": 0.95,
        }

    def _rect_pixel_detect_bg(self, raw, H, W):
        """Find background color (most common)."""
        from collections import Counter
        counts = Counter()
        for r in range(H):
            for c in range(W):
                counts[raw[r][c]] += 1
        if counts:
            return counts.most_common(1)[0][0]
        return None

    def _find_rects_and_isolates(self, cells, color, raw, H, W, bg):
        """Separate cells of one color into rectangular blocks vs isolated pixels."""
        cell_set = set(cells)
        visited = set()
        components = []

        for cell in cells:
            if cell in visited:
                continue
            # BFS to find connected component
            comp = []
            queue = [cell]
            visited.add(cell)
            while queue:
                cr, cc = queue.pop(0)
                comp.append((cr, cc))
                for dr, dc in [(-1,0),(1,0),(0,-1),(0,1)]:
                    nr, nc = cr+dr, cc+dc
                    if (nr, nc) in cell_set and (nr, nc) not in visited:
                        visited.add((nr, nc))
                        queue.append((nr, nc))
            components.append(comp)

        rects = []
        isolates = []
        for comp in components:
            if len(comp) == 1:
                isolates.append(comp[0])
            else:
                # Check if it forms a solid rectangle
                rows = [p[0] for p in comp]
                cols = [p[1] for p in comp]
                r0, r1 = min(rows), max(rows)
                c0, c1 = min(cols), max(cols)
                expected_size = (r1 - r0 + 1) * (c1 - c0 + 1)
                if len(comp) == expected_size:
                    rects.append((r0, r1, c0, c1))

        return rects, isolates

    def _draw_bridge(self, grid, rects, iso_r, iso_c, color, bg, H, W):
        """Draw bridge from nearest rect edge to isolated pixel."""
        # Find nearest rect edge point
        best_dist = float('inf')
        best_edge = None
        best_axis = None  # 'h' for horizontal, 'v' for vertical
        best_direction = 0

        for r0, r1, c0, c1 in rects:
            # Check if pixel is in the rect's row range → horizontal connection
            if r0 <= iso_r <= r1:
                # Left side
                if iso_c < c0:
                    dist = c0 - iso_c
                    if dist < best_dist:
                        best_dist = dist
                        best_edge = (iso_r, c0)
                        best_axis = 'h'
                        best_direction = -1  # pixel is to the left
                # Right side
                elif iso_c > c1:
                    dist = iso_c - c1
                    if dist < best_dist:
                        best_dist = dist
                        best_edge = (iso_r, c1)
                        best_axis = 'h'
                        best_direction = 1  # pixel is to the right

            # Check if pixel is in the rect's col range → vertical connection
            if c0 <= iso_c <= c1:
                # Above
                if iso_r < r0:
                    dist = r0 - iso_r
                    if dist < best_dist:
                        best_dist = dist
                        best_edge = (r0, iso_c)
                        best_axis = 'v'
                        best_direction = -1  # pixel is above
                # Below
                elif iso_r > r1:
                    dist = iso_r - r1
                    if dist < best_dist:
                        best_dist = dist
                        best_edge = (r1, iso_c)
                        best_axis = 'v'
                        best_direction = 1  # pixel is below

        if best_edge is None or best_dist < 2:
            return

        er, ec = best_edge

        if best_axis == 'h':
            # Horizontal bridge along iso_r
            step = best_direction  # +1 = pixel to the right, -1 = left
            # Bridge cells: from edge+1 to pixel-1
            bridge_c_start = ec + step
            bridge_c_end = iso_c - step  # one before pixel
            c_lo = min(bridge_c_start, bridge_c_end)
            c_hi = max(bridge_c_start, bridge_c_end)
            for bc in range(c_lo, c_hi + 1):
                if 0 <= bc < W:
                    grid[iso_r][bc] = color
            # Remove pixel from original position
            grid[iso_r][iso_c] = bg
            # Shifted pixel
            new_c = iso_c + step
            if 0 <= new_c < W:
                grid[iso_r][new_c] = color
            # Perpendicular marks at bridge start (edge+step) on rows ±1
            mark_c_bridge = ec + step
            for dr in [-1, 1]:
                nr = iso_r + dr
                if 0 <= nr < H and 0 <= mark_c_bridge < W:
                    grid[nr][mark_c_bridge] = color
            # Perpendicular marks at original pixel position on rows ±1
            for dr in [-1, 1]:
                nr = iso_r + dr
                if 0 <= nr < H:
                    grid[nr][iso_c] = color
        else:
            # Vertical bridge along iso_c
            step = best_direction  # +1 = pixel below, -1 = above
            bridge_r_start = er + step
            bridge_r_end = iso_r - step
            r_lo = min(bridge_r_start, bridge_r_end)
            r_hi = max(bridge_r_start, bridge_r_end)
            for br in range(r_lo, r_hi + 1):
                if 0 <= br < H:
                    grid[br][iso_c] = color
            # Remove pixel from original position
            grid[iso_r][iso_c] = bg
            # Shifted pixel
            new_r = iso_r + step
            if 0 <= new_r < H:
                grid[new_r][iso_c] = color
            # Perpendicular marks at bridge start on cols ±1
            mark_r_bridge = er + step
            for dc in [-1, 1]:
                nc = iso_c + dc
                if 0 <= mark_r_bridge < H and 0 <= nc < W:
                    grid[mark_r_bridge][nc] = color
            # Perpendicular marks at original pixel position on cols ±1
            for dc in [-1, 1]:
                nc = iso_c + dc
                if 0 <= nc < W and 0 <= iso_r < H:
                    grid[iso_r][nc] = color

    # ---- strategy: fractal block denoise -----------------------------------

    def _try_fractal_block_denoise(self, patterns, wm):
        """
        Detect pattern: grid divided by 0-separator lines into NxM blocks.
        Color 5 is noise. Each block is either a template pattern (2 colors)
        or a pure fill. The meta-grid of blocks mirrors the template itself:
        blocks at template's minority-color positions show the template,
        blocks at dominant-color positions are pure dominant.
        Category: self-similar / fractal grid denoising tasks.
        """
        task = wm.task
        if task is None:
            return None
        if not patterns.get("grid_size_preserved"):
            return None

        for pair in task.example_pairs:
            g0, g1 = pair.input_grid, pair.output_grid
            if g0 is None or g1 is None:
                return None
            raw_in, raw_out = g0.raw, g1.raw
            H, W = len(raw_in), len(raw_in[0])

            # Find separator rows and columns (all 0 or all 5→0)
            sep_rows = self._find_separator_lines(raw_in, H, W, axis='row')
            sep_cols = self._find_separator_lines(raw_in, H, W, axis='col')

            if not sep_rows or not sep_cols:
                return None

            # Extract blocks
            row_ranges = self._get_ranges(sep_rows, H)
            col_ranges = self._get_ranges(sep_cols, W)

            if not row_ranges or not col_ranges:
                return None

            # All blocks must be same size
            block_h = row_ranges[0][1] - row_ranges[0][0] + 1
            block_w = col_ranges[0][1] - col_ranges[0][0] + 1
            for rr in row_ranges:
                if rr[1] - rr[0] + 1 != block_h:
                    return None
            for cr in col_ranges:
                if cr[1] - cr[0] + 1 != block_w:
                    return None

            n_block_rows = len(row_ranges)
            n_block_cols = len(col_ranges)

            # Extract all blocks, removing noise (5)
            blocks_in = []
            for ri, (r0, r1) in enumerate(row_ranges):
                row_blocks = []
                for ci, (c0, c1) in enumerate(col_ranges):
                    block = []
                    for r in range(r0, r1 + 1):
                        row_data = []
                        for c in range(c0, c1 + 1):
                            v = raw_in[r][c]
                            row_data.append(v)
                        block.append(row_data)
                    row_blocks.append(block)
                blocks_in.append(row_blocks)

            # Extract output blocks
            blocks_out = []
            for ri, (r0, r1) in enumerate(row_ranges):
                row_blocks = []
                for ci, (c0, c1) in enumerate(col_ranges):
                    block = []
                    for r in range(r0, r1 + 1):
                        row_data = []
                        for c in range(c0, c1 + 1):
                            row_data.append(raw_out[r][c])
                        block.append(row_data)
                    row_blocks.append(block)
                blocks_out.append(row_blocks)

            # Find the template: the most common non-pure block in the output
            # (output has no noise)
            template = None
            dominant_color = None
            for ri in range(n_block_rows):
                for ci in range(n_block_cols):
                    block = blocks_out[ri][ci]
                    colors = set()
                    for row in block:
                        for v in row:
                            colors.add(v)
                    if len(colors) == 2:
                        template = block
                        # Dominant = more frequent color in template
                        from collections import Counter
                        cnt = Counter()
                        for row in block:
                            for v in row:
                                cnt[v] += 1
                        dominant_color = cnt.most_common(1)[0][0]
                        break
                if template is not None:
                    break

            if template is None:
                return None

            minority_colors = set()
            for row in template:
                for v in row:
                    if v != dominant_color:
                        minority_colors.add(v)
            if len(minority_colors) != 1:
                return None
            minority_color = minority_colors.pop()

            # Build the meta-pattern from the template
            # Position (bi, bj) in the template's block gives dominant or minority
            # At template level: position (tr, tc) → dominant_color or minority_color
            # Meta-grid: block at (bi, bj) → if template[bi][bj] == minority_color → show template
            #                                → if template[bi][bj] == dominant_color → pure dominant
            # But block rows/cols don't necessarily match template rows/cols 1:1
            # Template has block_h rows and block_w cols; meta-grid has n_block_rows × n_block_cols
            # These must match!
            if n_block_rows != block_h or n_block_cols != block_w:
                return None

            # Verify the self-similar rule
            pure_block = [[dominant_color]*block_w for _ in range(block_h)]

            for bi in range(n_block_rows):
                for bj in range(n_block_cols):
                    if template[bi][bj] == minority_color:
                        expected = template
                    else:
                        expected = pure_block
                    if blocks_out[bi][bj] != expected:
                        return None

            # Verify output separators are all 0
            for sr in sep_rows:
                for c in range(W):
                    if raw_out[sr][c] != 0:
                        return None
            for sc in sep_cols:
                for r in range(H):
                    if raw_out[r][sc] != 0:
                        return None

        return {
            "type": "fractal_block_denoise",
            "confidence": 0.95,
        }

    def _find_separator_lines(self, raw, H, W, axis):
        """Find rows or columns that are all 0 (ignoring noise value 5)."""
        seps = []
        if axis == 'row':
            for r in range(H):
                if all(raw[r][c] == 0 or raw[r][c] == 5 for c in range(W)):
                    seps.append(r)
        else:
            for c in range(W):
                if all(raw[r][c] == 0 or raw[r][c] == 5 for r in range(H)):
                    seps.append(c)
        return seps

    def _get_ranges(self, seps, total):
        """Given separator positions, return ranges of non-separator segments."""
        ranges = []
        prev = -1
        for s in sorted(seps):
            if s > prev + 1:
                ranges.append((prev + 1, s - 1))
            prev = s
        if prev < total - 1:
            ranges.append((prev + 1, total - 1))
        return ranges

    # ---- strategy: simple color mapping ---------------------------------

    def _try_color_mapping(self, patterns, wm=None):
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

        if not simple_map:
            return None

        # Validate mapping against full grids (patterns only show diffs)
        if wm and wm.task:
            for pair in wm.task.example_pairs:
                if pair.input_grid and pair.output_grid:
                    ri, ro = pair.input_grid.raw, pair.output_grid.raw
                    for r in range(len(ri)):
                        for c in range(len(ri[0])):
                            ic = ri[r][c]
                            oc = ro[r][c]
                            if ic in simple_map and simple_map[ic] != oc:
                                return None
                            if ic not in simple_map and ic != oc:
                                return None

        return {
            "type": "color_mapping",
            "mapping": simple_map,
            "confidence": 0.8,
        }

        return None

    # ---- strategy: uniform scaling --------------------------------------

    def _try_uniform_scale(self, patterns, wm):
        """
        Detect pattern: output grid is an integer scale-up of input grid.
        Each input cell becomes an NxN block of the same color in the output.
        """
        task = wm.task
        if not task or not task.example_pairs:
            return None

        scale_factors = set()
        for pair in task.example_pairs:
            g0, g1 = pair.input_grid, pair.output_grid
            if not g0 or not g1:
                return None
            h_in, w_in = len(g0.raw), len(g0.raw[0]) if g0.raw else 0
            h_out, w_out = len(g1.raw), len(g1.raw[0]) if g1.raw else 0
            if h_in == 0 or w_in == 0:
                return None
            if h_out % h_in != 0 or w_out % w_in != 0:
                return None
            sh, sw = h_out // h_in, w_out // w_in
            if sh != sw or sh < 2:
                return None
            scale_factors.add(sh)

        if len(scale_factors) != 1:
            return None
        scale = scale_factors.pop()

        # Verify: each input cell maps to a scale x scale block in output
        for pair in task.example_pairs:
            raw_in, raw_out = pair.input_grid.raw, pair.output_grid.raw
            for r in range(len(raw_in)):
                for c in range(len(raw_in[0])):
                    expected = raw_in[r][c]
                    for dr in range(scale):
                        for dc in range(scale):
                            if raw_out[r * scale + dr][c * scale + dc] != expected:
                                return None

        return {"type": "uniform_scale", "scale": scale, "confidence": 1.0}

    # ---- strategy: recolor by component size ----------------------------

    def _try_recolor_by_size(self, patterns, wm):
        """
        Detect pattern: all objects share one color; each connected component
        is recolored based on its size (e.g., size 4 -> color 1, size 3 -> 2).
        """
        task = wm.task
        if not task or not patterns.get("grid_size_preserved"):
            return None

        size_to_color = {}
        source_color = None
        bg_color = None

        for pair in task.example_pairs:
            g0, g1 = pair.input_grid, pair.output_grid
            if not g0 or not g1:
                return None
            raw_in, raw_out = g0.raw, g1.raw
            h, w = len(raw_in), len(raw_in[0]) if raw_in else 0

            # Detect background as most frequent color
            freq = {}
            for r in range(h):
                for c in range(w):
                    freq[raw_in[r][c]] = freq.get(raw_in[r][c], 0) + 1
            pair_bg = max(freq, key=freq.get)
            if bg_color is None:
                bg_color = pair_bg
            elif bg_color != pair_bg:
                return None

            # All non-background cells must share one source color
            obj_positions = []
            for r in range(h):
                for c in range(w):
                    v = raw_in[r][c]
                    if v != bg_color:
                        if source_color is None:
                            source_color = v
                        elif v != source_color:
                            return None
                        obj_positions.append((r, c))

            if not obj_positions:
                return None

            groups = PredictOperator._group_positions(obj_positions)

            for group in groups:
                size = len(group)
                out_colors = set()
                for r, c in group:
                    out_colors.add(raw_out[r][c])
                if len(out_colors) != 1:
                    return None
                oc = out_colors.pop()
                if oc == bg_color:
                    return None
                if size in size_to_color:
                    if size_to_color[size] != oc:
                        return None
                else:
                    size_to_color[size] = oc

            # Background cells must remain background
            for r in range(h):
                for c in range(w):
                    if raw_in[r][c] == bg_color and raw_out[r][c] != bg_color:
                        return None

        if not size_to_color or source_color is None:
            return None

        return {
            "type": "recolor_by_size",
            "source_color": source_color,
            "bg_color": bg_color,
            "size_to_color": size_to_color,
            "confidence": 0.9,
        }

    # ---- strategy: corner-marker quadrant fill --------------------------

    def _try_corner_fill(self, patterns, wm):
        """
        Detect pattern: rectangles of a fill color with 4 corner markers.
        Output replaces each rectangle with quadrants colored by the corners.
        """
        task = wm.task
        if not task or not patterns.get("grid_size_preserved"):
            return None

        fill_color = None
        bg_color = None

        for pair in task.example_pairs:
            g0, g1 = pair.input_grid, pair.output_grid
            if not g0 or not g1:
                return None
            raw_in, raw_out = g0.raw, g1.raw
            h, w = len(raw_in), len(raw_in[0]) if raw_in else 0

            freq = {}
            for r in range(h):
                for c in range(w):
                    freq[raw_in[r][c]] = freq.get(raw_in[r][c], 0) + 1
            pair_bg = max(freq, key=freq.get)
            if bg_color is None:
                bg_color = pair_bg
            elif bg_color != pair_bg:
                return None

            # Find candidate fill colors that form rectangles with corners
            color_positions = {}
            for r in range(h):
                for c in range(w):
                    v = raw_in[r][c]
                    if v != bg_color:
                        color_positions.setdefault(v, []).append((r, c))

            found_fill = None
            for color, positions in color_positions.items():
                groups = PredictOperator._group_positions(positions)
                all_valid = True
                for group in groups:
                    rows = [r for r, c in group]
                    cols = [c for r, c in group]
                    r1, r2 = min(rows), max(rows)
                    c1, c2 = min(cols), max(cols)
                    rect_h = r2 - r1 + 1
                    rect_w = c2 - c1 + 1
                    if len(group) != rect_h * rect_w or rect_h < 2 or rect_w < 2:
                        all_valid = False
                        break
                    corners = [
                        (r1 - 1, c1 - 1), (r1 - 1, c2 + 1),
                        (r2 + 1, c1 - 1), (r2 + 1, c2 + 1),
                    ]
                    for cr, cc in corners:
                        if cr < 0 or cr >= h or cc < 0 or cc >= w:
                            all_valid = False
                            break
                        cv = raw_in[cr][cc]
                        if cv == bg_color or cv == color:
                            all_valid = False
                            break
                    if not all_valid:
                        break
                if all_valid and groups:
                    found_fill = color
                    break

            if found_fill is None:
                return None
            if fill_color is None:
                fill_color = found_fill
            elif fill_color != found_fill:
                return None

            # Verify output: quadrants filled, corners removed
            positions = [(r, c) for r in range(h) for c in range(w)
                         if raw_in[r][c] == fill_color]
            groups = PredictOperator._group_positions(positions)
            for group in groups:
                rows = [r for r, c in group]
                cols = [c for r, c in group]
                r1, r2 = min(rows), max(rows)
                c1, c2 = min(cols), max(cols)
                rect_h = r2 - r1 + 1
                rect_w = c2 - c1 + 1
                mid_r = r1 + rect_h // 2
                mid_c = c1 + rect_w // 2

                tl = raw_in[r1 - 1][c1 - 1]
                tr = raw_in[r1 - 1][c2 + 1]
                bl = raw_in[r2 + 1][c1 - 1]
                br = raw_in[r2 + 1][c2 + 1]

                for r in range(r1, r2 + 1):
                    for c in range(c1, c2 + 1):
                        if r < mid_r and c < mid_c:
                            expected = tl
                        elif r < mid_r and c >= mid_c:
                            expected = tr
                        elif r >= mid_r and c < mid_c:
                            expected = bl
                        else:
                            expected = br
                        if raw_out[r][c] != expected:
                            return None

                for cr, cc in [(r1 - 1, c1 - 1), (r1 - 1, c2 + 1),
                               (r2 + 1, c1 - 1), (r2 + 1, c2 + 1)]:
                    if raw_out[cr][cc] != bg_color:
                        return None

        return {
            "type": "corner_fill",
            "fill_color": fill_color,
            "bg_color": bg_color,
            "confidence": 0.95,
        }

    # ---- strategy: vertical mirror (append reversed rows) ---------------

    def _try_vertical_mirror(self, patterns, wm):
        """
        Detect pattern: output is input rows followed by input rows reversed.
        Output height = 2 * input height, same width.
        """
        task = wm.task
        if not task:
            return None

        for pair in task.example_pairs:
            g0, g1 = pair.input_grid, pair.output_grid
            if not g0 or not g1:
                return None
            raw_in, raw_out = g0.raw, g1.raw
            h_in = len(raw_in)
            w_in = len(raw_in[0]) if raw_in else 0
            h_out = len(raw_out)
            w_out = len(raw_out[0]) if raw_out else 0

            if h_out != 2 * h_in or w_out != w_in:
                return None

            # Top half must equal input
            for r in range(h_in):
                for c in range(w_in):
                    if raw_out[r][c] != raw_in[r][c]:
                        return None

            # Bottom half must equal reversed input
            for r in range(h_in):
                for c in range(w_in):
                    if raw_out[h_in + r][c] != raw_in[h_in - 1 - r][c]:
                        return None

        return {"type": "vertical_mirror", "confidence": 1.0}

    # ---- strategy: fill hollow rectangles by interior size ---------------

    def _try_fill_rect_by_size(self, patterns, wm):
        """
        Detect pattern: rectangular frames of one color with hollow interiors.
        Each interior is filled with a color determined by the interior's
        minimum dimension (e.g., 1x1->6, 2x2->7, 3x3->8).
        """
        task = wm.task
        if not task or not patterns.get("grid_size_preserved"):
            return None

        bg_color = None
        frame_color = None
        size_to_color = {}

        for pair in task.example_pairs:
            g0, g1 = pair.input_grid, pair.output_grid
            if not g0 or not g1:
                return None
            raw_in, raw_out = g0.raw, g1.raw
            h, w = len(raw_in), len(raw_in[0]) if raw_in else 0

            # Detect background
            freq = {}
            for r in range(h):
                for c in range(w):
                    freq[raw_in[r][c]] = freq.get(raw_in[r][c], 0) + 1
            pair_bg = max(freq, key=freq.get)
            if bg_color is None:
                bg_color = pair_bg
            elif bg_color != pair_bg:
                return None

            # Collect non-bg colors in input
            non_bg_colors = set()
            for r in range(h):
                for c in range(w):
                    if raw_in[r][c] != bg_color:
                        non_bg_colors.add(raw_in[r][c])

            if not non_bg_colors:
                return None

            # Try each non-bg color as frame color
            found = False
            for fc in sorted(non_bg_colors):
                positions = [(r, c) for r in range(h) for c in range(w)
                             if raw_in[r][c] == fc]
                groups = PredictOperator._group_positions(positions)
                if not groups:
                    continue

                all_valid = True
                pair_map = {}

                for group in groups:
                    rows = [r for r, c in group]
                    cols = [c for r, c in group]
                    r1, r2 = min(rows), max(rows)
                    c1, c2 = min(cols), max(cols)
                    bh = r2 - r1 + 1
                    bw = c2 - c1 + 1

                    if bh < 3 or bw < 3:
                        all_valid = False
                        break

                    # Check all border cells present, no interior cells
                    group_set = set(group)
                    for r in range(r1, r2 + 1):
                        for c in range(c1, c2 + 1):
                            is_border = (r == r1 or r == r2
                                         or c == c1 or c == c2)
                            if is_border and (r, c) not in group_set:
                                all_valid = False
                                break
                            if not is_border and (r, c) in group_set:
                                all_valid = False
                                break
                        if not all_valid:
                            break
                    if not all_valid:
                        break

                    # Interior must be bg in input
                    for r in range(r1 + 1, r2):
                        for c in range(c1 + 1, c2):
                            if raw_in[r][c] != bg_color:
                                all_valid = False
                                break
                        if not all_valid:
                            break
                    if not all_valid:
                        break

                    # Interior must be one consistent fill color in output
                    fill_colors = set()
                    for r in range(r1 + 1, r2):
                        for c in range(c1 + 1, c2):
                            fill_colors.add(raw_out[r][c])
                    if len(fill_colors) != 1:
                        all_valid = False
                        break
                    fill_c = fill_colors.pop()
                    if fill_c == bg_color or fill_c == fc:
                        all_valid = False
                        break

                    key = min(bh - 2, bw - 2)
                    if key in pair_map and pair_map[key] != fill_c:
                        all_valid = False
                        break
                    pair_map[key] = fill_c

                if all_valid and pair_map:
                    if frame_color is None:
                        frame_color = fc
                    elif frame_color != fc:
                        return None
                    for k, v in pair_map.items():
                        if k in size_to_color and size_to_color[k] != v:
                            return None
                        size_to_color[k] = v
                    found = True
                    break

            if not found:
                return None

        if frame_color is None or not size_to_color:
            return None

        return {
            "type": "fill_rect_by_size",
            "frame_color": frame_color,
            "bg_color": bg_color,
            "size_to_color": size_to_color,
            "confidence": 0.95,
        }

    # ---- strategy: staircase growth (single row -> triangle) -------------

    def _try_staircase_growth(self, patterns, wm):
        """
        Detect pattern: input is a single row with K colored cells from the
        left. Output has width//2 rows where row i has K+i colored cells.
        """
        task = wm.task
        if not task:
            return None

        for pair in task.example_pairs:
            g0, g1 = pair.input_grid, pair.output_grid
            if not g0 or not g1:
                return None
            raw_in, raw_out = g0.raw, g1.raw
            h_in = len(raw_in)
            w_in = len(raw_in[0]) if raw_in else 0
            h_out = len(raw_out)
            w_out = len(raw_out[0]) if raw_out else 0

            if h_in != 1 or w_out != w_in:
                return None
            if w_in < 2 or h_out != w_in // 2:
                return None

            # Find contiguous colored cells from left
            row = raw_in[0]
            pair_color = None
            start_count = 0
            for c in range(w_in):
                if row[c] != 0:
                    if pair_color is None:
                        pair_color = row[c]
                    elif row[c] != pair_color:
                        return None
                    start_count += 1
                else:
                    break

            if pair_color is None or start_count == 0:
                return None

            # Rest must be 0
            for c in range(start_count, w_in):
                if row[c] != 0:
                    return None

            # Verify output: each row adds one more colored cell
            for r in range(h_out):
                count = start_count + r
                for c in range(w_out):
                    expected = pair_color if c < count else 0
                    if raw_out[r][c] != expected:
                        return None

        return {"type": "staircase_growth", "confidence": 1.0}


# ======================================================================
# DescendOperator -- placeholder for deeper KG exploration
# ======================================================================

    # ---- strategy: path tracing between turn markers ----------------------

    def _try_path_trace(self, patterns, wm):
        """
        Detect pattern: a start marker traces L-shaped paths toward turn
        markers. One marker color causes clockwise turns, another causes
        counter-clockwise turns. The path is drawn with the start color.
        """
        task = wm.task
        if not task or not patterns.get("grid_size_preserved"):
            return None

        for pair in task.example_pairs:
            g0, g1 = pair.input_grid, pair.output_grid
            if not g0 or not g1:
                return None

        # Scan ALL example pairs to identify colors
        bg = None
        all_in_colors = set()
        start_color = None

        for pair in task.example_pairs:
            g0, g1 = pair.input_grid, pair.output_grid
            raw_in, raw_out = g0.raw, g1.raw
            h = len(raw_in)
            w = len(raw_in[0]) if raw_in else 0

            # Find background (most frequent in input)
            freq = {}
            for r in range(h):
                for c in range(w):
                    freq[raw_in[r][c]] = freq.get(raw_in[r][c], 0) + 1
            pair_bg = max(freq, key=freq.get)
            if bg is None:
                bg = pair_bg
            elif bg != pair_bg:
                return None

            # Collect non-bg colors
            in_cnt = {}
            out_cnt = {}
            for r in range(h):
                for c in range(w):
                    v = raw_in[r][c]
                    if v != bg:
                        in_cnt[v] = in_cnt.get(v, 0) + 1
                        all_in_colors.add(v)
                    v2 = raw_out[r][c]
                    if v2 != bg:
                        out_cnt[v2] = out_cnt.get(v2, 0) + 1

            # The start/path color grows in the output
            for c in in_cnt:
                if out_cnt.get(c, 0) > in_cnt[c]:
                    if start_color is None:
                        start_color = c
                    elif start_color != c:
                        return None

        if start_color is None or len(all_in_colors) < 2 or len(all_in_colors) > 3:
            return None

        marker_colors = sorted(c for c in all_in_colors if c != start_color)
        if not marker_colors or len(marker_colors) > 2:
            return None

        # Determine starting direction from first pair
        raw_in = task.example_pairs[0].input_grid.raw
        h = len(raw_in)
        w = len(raw_in[0]) if raw_in else 0

        start_positions = []
        for r in range(h):
            for c in range(w):
                if raw_in[r][c] == start_color:
                    start_positions.append((r, c))
        if len(start_positions) != 1:
            return None
        start_pos = start_positions[0]

        sr, sc = start_pos
        directions = []
        if sc == 0:
            directions.append((0, 1))   # RIGHT
        if sc == w - 1:
            directions.append((0, -1))  # LEFT
        if sr == 0:
            directions.append((1, 0))   # DOWN
        if sr == h - 1:
            directions.append((-1, 0))  # UP
        if not directions:
            return None

        CW = {(0, 1): (1, 0), (1, 0): (0, -1),
              (0, -1): (-1, 0), (-1, 0): (0, 1)}
        CCW = {(0, 1): (-1, 0), (-1, 0): (0, -1),
               (0, -1): (1, 0), (1, 0): (0, 1)}

        # Try all combinations of direction and marker assignment
        if len(marker_colors) == 2:
            assignments = [
                {marker_colors[0]: CW, marker_colors[1]: CCW},
                {marker_colors[0]: CCW, marker_colors[1]: CW},
            ]
        else:
            assignments = [
                {marker_colors[0]: CW},
                {marker_colors[0]: CCW},
            ]

        for init_dir in directions:
            for assign in assignments:
                # Simulate path for ALL example pairs
                all_match = True
                for pair in task.example_pairs:
                    g0, g1 = pair.input_grid, pair.output_grid
                    ri = g0.raw
                    hi, wi = len(ri), len(ri[0]) if ri else 0

                    # Find start and markers in this pair
                    sp = None
                    mm = {}
                    for r in range(hi):
                        for c in range(wi):
                            if ri[r][c] == start_color:
                                sp = (r, c)
                            elif ri[r][c] != bg:
                                mm[(r, c)] = ri[r][c]

                    if sp is None:
                        all_match = False
                        break

                    predicted = self._simulate_path(
                        ri, sp, init_dir, mm, assign, start_color, bg, hi, wi)
                    if predicted != g1.raw:
                        all_match = False
                        break

                if all_match:
                    cw_color = None
                    ccw_color = None
                    for mc, turn_map in assign.items():
                        if turn_map is CW:
                            cw_color = mc
                        else:
                            ccw_color = mc
                    return {
                        "type": "path_trace",
                        "start_color": start_color,
                        "bg_color": bg,
                        "cw_color": cw_color,
                        "ccw_color": ccw_color,
                        "init_dir": list(init_dir),
                        "confidence": 1.0,
                    }

        return None

    @staticmethod
    def _simulate_path(raw_in, start, init_dir, marker_map, assign, start_color, bg, h, w):
        """Simulate path tracing and return predicted grid."""
        output = [row[:] for row in raw_in]
        # Clear start from output (will be redrawn as path)
        r, c = start
        output[r][c] = bg

        # Trace path
        dr, dc = init_dir
        pr, pc = start

        for _ in range(h * w * 4):  # safety limit
            output[pr][pc] = start_color

            # Look ahead
            nr, nc = pr + dr, pc + dc
            if nr < 0 or nr >= h or nc < 0 or nc >= w:
                break  # hit edge

            if (nr, nc) in marker_map:
                mc = marker_map[(nr, nc)]
                turn_map = assign.get(mc)
                if turn_map is not None:
                    dr, dc = turn_map[(dr, dc)]
                else:
                    break
                # Stay at current position, continue in new direction
            else:
                pr, pc = nr, nc

        return output

    # ---- strategy: diamond connection (+ shapes linked by lines) ----------

    def _try_diamond_connect(self, patterns, wm):
        """
        Detect pattern: diamond shapes (+ of 4 cells around empty center)
        on same row or column are connected by lines of a connector color
        between their facing tips.
        """
        task = wm.task
        if not task or not patterns.get("grid_size_preserved"):
            return None

        diamond_color = None
        connector_color = None
        bg_color = None

        for pair in task.example_pairs:
            g0, g1 = pair.input_grid, pair.output_grid
            if not g0 or not g1:
                return None
            raw_in, raw_out = g0.raw, g1.raw
            h = len(raw_in)
            w = len(raw_in[0]) if raw_in else 0

            # Find background
            freq = {}
            for r in range(h):
                for c in range(w):
                    freq[raw_in[r][c]] = freq.get(raw_in[r][c], 0) + 1
            pair_bg = max(freq, key=freq.get)
            if bg_color is None:
                bg_color = pair_bg
            elif bg_color != pair_bg:
                return None

            # Find diamond centers (bg cells with 4 same-color non-bg neighbors)
            centers = []
            for r in range(1, h - 1):
                for c in range(1, w - 1):
                    if raw_in[r][c] != bg_color:
                        continue
                    neighbors = [raw_in[r - 1][c], raw_in[r + 1][c],
                                 raw_in[r][c - 1], raw_in[r][c + 1]]
                    if all(n != bg_color for n in neighbors) and len(set(neighbors)) == 1:
                        centers.append((r, c))
                        dc = neighbors[0]
                        if diamond_color is None:
                            diamond_color = dc
                        elif diamond_color != dc:
                            return None

            if not centers or diamond_color is None:
                return None

            # All non-bg input cells should be diamond_color
            for r in range(h):
                for c in range(w):
                    v = raw_in[r][c]
                    if v != bg_color and v != diamond_color:
                        return None

            # Determine connector color from output diff
            for r in range(h):
                for c in range(w):
                    if raw_out[r][c] != raw_in[r][c]:
                        cc = raw_out[r][c]
                        if connector_color is None:
                            connector_color = cc
                        elif connector_color != cc:
                            return None

            # Verify by simulating connections
            predicted = self._predict_diamond_connect(
                raw_in, centers, diamond_color, connector_color, bg_color, h, w)
            if predicted != raw_out:
                return None

        if connector_color is None:
            return None

        return {
            "type": "diamond_connect",
            "diamond_color": diamond_color,
            "connector_color": connector_color,
            "bg_color": bg_color,
            "confidence": 1.0,
        }

    @staticmethod
    def _predict_diamond_connect(raw_in, centers, diamond_color, connector_color, bg_color, h, w):
        """Connect diamond tips on same row/column with connector lines."""
        output = [row[:] for row in raw_in]

        # Group centers by row and by column
        by_row = {}
        by_col = {}
        for r, c in centers:
            by_row.setdefault(r, []).append(c)
            by_col.setdefault(c, []).append(r)

        # Connect horizontally (same row)
        for r, cols in by_row.items():
            cols_sorted = sorted(cols)
            for i in range(len(cols_sorted) - 1):
                c1 = cols_sorted[i]
                c2 = cols_sorted[i + 1]
                # Right tip of left diamond at (r, c1+1)
                # Left tip of right diamond at (r, c2-1)
                # Fill (r, c1+2) to (r, c2-2) with connector
                for c in range(c1 + 2, c2 - 1):
                    output[r][c] = connector_color

        # Connect vertically (same column)
        for c, rows in by_col.items():
            rows_sorted = sorted(rows)
            for i in range(len(rows_sorted) - 1):
                r1 = rows_sorted[i]
                r2 = rows_sorted[i + 1]
                for r in range(r1 + 2, r2 - 1):
                    output[r][c] = connector_color

        return output

    # ---- strategy: cross-grid band fill ----------------------------------

    def _try_cross_grid_fill(self, patterns, wm):
        """
        Detect pattern: grid has a column axis of one color (with intersection
        markers) and colored horizontal rows. Output fills bands between
        colored rows with band colors, axis becomes intersection color,
        colored rows become intersection color (axis position gets axis color).
        Axis column position may vary between examples.
        """
        task = wm.task
        if not task or not patterns.get("grid_size_preserved"):
            return None

        bg_color = None
        axis_color = None
        intersection_color = None

        for pair in task.example_pairs:
            g0, g1 = pair.input_grid, pair.output_grid
            if not g0 or not g1:
                return None
            raw_in, raw_out = g0.raw, g1.raw
            h = len(raw_in)
            w = len(raw_in[0]) if raw_in else 0

            # Find background
            freq = {}
            for r in range(h):
                for c in range(w):
                    freq[raw_in[r][c]] = freq.get(raw_in[r][c], 0) + 1
            pair_bg = max(freq, key=freq.get)
            if bg_color is None:
                bg_color = pair_bg
            elif bg_color != pair_bg:
                return None

            # Find axis column for THIS example
            pair_axis_col = None
            pair_ac = None
            pair_ic = None
            for c in range(w):
                col_vals = set(raw_in[r][c] for r in range(h))
                if bg_color in col_vals:
                    continue
                if len(col_vals) != 2:
                    continue
                vals = list(col_vals)
                cnt0 = sum(1 for r in range(h) if raw_in[r][c] == vals[0])
                cnt1 = sum(1 for r in range(h) if raw_in[r][c] == vals[1])
                ac = vals[0] if cnt0 > cnt1 else vals[1]
                ic = vals[1] if cnt0 > cnt1 else vals[0]
                pair_axis_col = c
                pair_ac = ac
                pair_ic = ic
                break

            if pair_axis_col is None:
                return None

            # Axis color and intersection color must be consistent
            if axis_color is None:
                axis_color = pair_ac
            elif axis_color != pair_ac:
                return None
            if intersection_color is None:
                intersection_color = pair_ic
            elif intersection_color != pair_ic:
                return None

            # Find colored rows
            pair_colored_rows = []
            for r in range(h):
                if raw_in[r][pair_axis_col] == intersection_color:
                    row_colors = set()
                    for c2 in range(w):
                        if c2 == pair_axis_col:
                            continue
                        if raw_in[r][c2] != bg_color:
                            row_colors.add(raw_in[r][c2])
                    if len(row_colors) != 1:
                        return None
                    pair_colored_rows.append((r, row_colors.pop()))

            if not pair_colored_rows:
                return None

            # Verify output matches prediction
            predicted = self._predict_cross_grid_fill(
                h, w, pair_axis_col, axis_color, intersection_color,
                bg_color, pair_colored_rows)
            if predicted != raw_out:
                return None

        return {
            "type": "cross_grid_fill",
            "axis_color": axis_color,
            "intersection_color": intersection_color,
            "bg_color": bg_color,
            "confidence": 1.0,
        }

    @staticmethod
    def _predict_cross_grid_fill(h, w, axis_col, axis_color, intersection_color,
                                  bg_color, colored_rows):
        """Build output grid for cross-grid band fill."""
        # Build band assignments
        # Group consecutive same-color colored rows
        cr_list = sorted(colored_rows, key=lambda x: x[0])

        # Find boundaries between different-color bands
        # Each row gets assigned a band color
        row_band = [None] * h
        row_is_colored = [False] * h
        row_is_transition = [False] * h

        for r, color in cr_list:
            row_is_colored[r] = True

        # Find transitions between different-color bands
        transitions = []
        for i in range(len(cr_list) - 1):
            r1, c1 = cr_list[i]
            r2, c2 = cr_list[i + 1]
            if c1 != c2:
                mid = (r1 + r2) / 2
                if mid == int(mid):
                    transitions.append(int(mid))

        for t in transitions:
            row_is_transition[t] = True

        # Assign band colors using Voronoi (nearest colored row)
        for r in range(h):
            if row_is_transition[r]:
                continue
            best_dist = h + 1
            best_color = None
            for cr, cc in cr_list:
                d = abs(r - cr)
                if d < best_dist:
                    best_dist = d
                    best_color = cc
            row_band[r] = best_color

        # Build output
        output = [[bg_color] * w for _ in range(h)]
        for r in range(h):
            if row_is_transition[r]:
                for c in range(w):
                    output[r][c] = intersection_color
            elif row_is_colored[r]:
                for c in range(w):
                    if c == axis_col:
                        output[r][c] = axis_color
                    else:
                        output[r][c] = intersection_color
            else:
                band_c = row_band[r]
                for c in range(w):
                    if c == axis_col:
                        output[r][c] = intersection_color
                    else:
                        output[r][c] = band_c

        return output

    # ---- strategy: trail displacement along marker chains --------------------

    def _try_trail_displacement(self, patterns, wm):
        """
        Detect pattern: grid divided by a separator row (uniform non-bg color).
        Top half has 'target' colored cells, bottom half has 'active' + 'trail'
        colored cells. Each active cell slides along its adjacent trail chain.
        Each target cell (mirrored across separator) applies the same displacement
        with the vertical component negated.
        """
        task = wm.task
        if not task or not patterns.get("grid_size_preserved"):
            return None

        for pair in task.example_pairs:
            g0, g1 = pair.input_grid, pair.output_grid
            if not g0 or not g1:
                return None

        # Detect from first pair
        raw_in = task.example_pairs[0].input_grid.raw
        raw_out = task.example_pairs[0].output_grid.raw
        h = len(raw_in)
        w = len(raw_in[0]) if raw_in else 0

        # Find background
        freq = {}
        for r in range(h):
            for c in range(w):
                freq[raw_in[r][c]] = freq.get(raw_in[r][c], 0) + 1
        bg = max(freq, key=freq.get)

        # Find separator row (all cells same non-bg color)
        sep_row = None
        sep_color = None
        for r in range(1, h - 1):
            row_vals = set(raw_in[r])
            if len(row_vals) == 1 and raw_in[r][0] != bg:
                sep_row = r
                sep_color = raw_in[r][0]
                break

        if sep_row is None:
            return None

        # Collect non-bg, non-sep colors in each half
        top_colors = set()
        bottom_colors = set()
        for r in range(h):
            if r == sep_row:
                continue
            for c in range(w):
                v = raw_in[r][c]
                if v != bg and v != sep_color:
                    if r < sep_row:
                        top_colors.add(v)
                    else:
                        bottom_colors.add(v)

        if len(top_colors) != 1 or len(bottom_colors) != 2:
            return None

        target_color = top_colors.pop()

        # Determine active vs trail: trail disappears in output
        bottom_out_colors = set()
        for r in range(sep_row + 1, h):
            for c in range(w):
                v = raw_out[r][c]
                if v != bg and v != sep_color:
                    bottom_out_colors.add(v)

        trail_color = None
        active_color = None
        for c in bottom_colors:
            if c not in bottom_out_colors:
                trail_color = c
            else:
                active_color = c

        if trail_color is None or active_color is None:
            return None

        # Verify on all pairs
        for pair in task.example_pairs:
            g0, g1 = pair.input_grid, pair.output_grid
            raw_i, raw_o = g0.raw, g1.raw
            hi = len(raw_i)

            pair_sep = None
            for r in range(1, hi - 1):
                if len(set(raw_i[r])) == 1 and raw_i[r][0] == sep_color:
                    pair_sep = r
                    break
            if pair_sep is None:
                return None

            predicted = self._predict_trail_displacement(
                raw_i, pair_sep, sep_color, bg,
                target_color, active_color, trail_color)
            if predicted != raw_o:
                return None

        return {
            "type": "trail_displacement",
            "sep_color": sep_color,
            "bg_color": bg,
            "target_color": target_color,
            "active_color": active_color,
            "trail_color": trail_color,
            "confidence": 1.0,
        }

    @staticmethod
    def _predict_trail_displacement(raw_in, sep_row, sep_color, bg,
                                     target_color, active_color, trail_color):
        """Slide each active cell along its trail chain; mirror for targets."""
        h = len(raw_in)
        w = len(raw_in[0]) if raw_in else 0

        output = [[bg] * w for _ in range(h)]
        for c in range(w):
            output[sep_row][c] = sep_color

        # Collect active and trail positions in bottom half
        active_positions = []
        trail_set = set()
        for r in range(sep_row + 1, h):
            for c in range(w):
                if raw_in[r][c] == active_color:
                    active_positions.append((r, c))
                elif raw_in[r][c] == trail_color:
                    trail_set.add((r, c))

        # Trace each active cell's trail chain
        displacements = {}
        used_trails = set()

        for ar, ac in active_positions:
            visited = {(ar, ac)}
            pos = (ar, ac)

            while True:
                pr, pc = pos
                found_next = False
                for dr, dc in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                    nr, nc = pr + dr, pc + dc
                    if (nr, nc) in visited:
                        continue
                    if (nr, nc) in trail_set and (nr, nc) not in used_trails:
                        visited.add((nr, nc))
                        used_trails.add((nr, nc))
                        pos = (nr, nc)
                        found_next = True
                        break
                if not found_next:
                    break

            end_r, end_c = pos
            displacements[(ar, ac)] = (end_r - ar, end_c - ac)

        # Place moved active cells
        for (ar, ac), (dr, dc) in displacements.items():
            nr, nc = ar + dr, ac + dc
            if 0 <= nr < h and 0 <= nc < w:
                output[nr][nc] = active_color

        # Mirror displacement for target cells in top half
        for r in range(sep_row):
            for c in range(w):
                if raw_in[r][c] == target_color:
                    mirror_r = 2 * sep_row - r
                    if (mirror_r, c) in displacements:
                        dr, dc = displacements[(mirror_r, c)]
                        nr, nc = r - dr, c + dc
                        if 0 <= nr < h and 0 <= nc < w:
                            output[nr][nc] = target_color

        return output

    # ---- strategy: zigzag warp of rectangular frame --------------------------

    def _try_zigzag_warp(self, patterns, wm):
        """
        Detect pattern: rectangular frame of one color on zero background.
        Each row of the frame is horizontally shifted by a zigzag offset
        cycling through [0, -1, 0, +1]. Starting phase = (1 - internal_rows) % 4.
        """
        task = wm.task
        if not task or not patterns.get("grid_size_preserved"):
            return None

        CYCLE = [0, -1, 0, 1]

        for pair in task.example_pairs:
            g0, g1 = pair.input_grid, pair.output_grid
            if not g0 or not g1:
                return None
            raw_in, raw_out = g0.raw, g1.raw
            h = len(raw_in)
            w = len(raw_in[0]) if raw_in else 0

            bg = raw_in[0][0]

            # All non-bg cells must share one color
            frame_color = None
            top_r = bot_r = None
            for r in range(h):
                for c in range(w):
                    v = raw_in[r][c]
                    if v != bg:
                        if frame_color is None:
                            frame_color = v
                        elif v != frame_color:
                            return None
                        if top_r is None:
                            top_r = r
                        bot_r = r

            if frame_color is None or top_r is None:
                return None

            frame_h = bot_r - top_r + 1
            internal_rows = frame_h - 2
            if internal_rows < 1:
                return None

            phase = (1 - internal_rows) % 4

            # Verify each frame row matches the expected shift
            for row_idx in range(frame_h):
                r = top_r + row_idx
                offset = CYCLE[(phase + row_idx) % 4]
                for c in range(w):
                    src_c = c - offset
                    expected = raw_in[r][src_c] if 0 <= src_c < w else bg
                    if raw_out[r][c] != expected:
                        return None

            # Non-frame rows must be unchanged
            for r in range(h):
                if r < top_r or r > bot_r:
                    for c in range(w):
                        if raw_out[r][c] != raw_in[r][c]:
                            return None

        return {"type": "zigzag_warp", "confidence": 1.0}


    # ---- strategy: gravity slide toward wall boundary ----------------------

    def _try_gravity_slide(self, patterns, wm):
        """
        Detect pattern: grid has 3 colors (bg, wall, object). Wall forms
        stepped boundary that stays fixed. Object components slide down
        toward wall, stopping 1 row before contact. Against already-placed
        objects, components touch (gap 0).
        """
        task = wm.task
        if not task or not patterns.get("grid_size_preserved"):
            return None

        # Detect bg as the color present in ALL pairs with highest total count
        total_freq = {}
        pair_color_sets = []
        for pair in task.example_pairs:
            g0 = pair.input_grid
            if not g0:
                return None
            raw_in = g0.raw
            h = len(raw_in)
            w = len(raw_in[0]) if raw_in else 0
            pc = set()
            for r in range(h):
                for c in range(w):
                    v = raw_in[r][c]
                    total_freq[v] = total_freq.get(v, 0) + 1
                    pc.add(v)
            pair_color_sets.append(pc)

        common_colors = pair_color_sets[0]
        for pc in pair_color_sets[1:]:
            common_colors = common_colors & pc
        if not common_colors:
            return None
        bg = max(common_colors, key=lambda c: total_freq[c])

        for pair in task.example_pairs:
            g0, g1 = pair.input_grid, pair.output_grid
            if not g0 or not g1:
                return None
            raw_in, raw_out = g0.raw, g1.raw
            h = len(raw_in)
            w = len(raw_in[0]) if raw_in else 0

            # Count per-pair colors
            freq = {}
            for r in range(h):
                for c in range(w):
                    freq[raw_in[r][c]] = freq.get(raw_in[r][c], 0) + 1

            non_bg = [c for c in freq if c != bg]
            if len(non_bg) != 2:
                return None

            # Wall = unchanged between input and output
            wall_color = obj_color = None
            for color in non_bg:
                in_pos = {(r2, c2) for r2 in range(h) for c2 in range(w)
                          if raw_in[r2][c2] == color}
                out_pos = {(r2, c2) for r2 in range(h) for c2 in range(w)
                           if raw_out[r2][c2] == color}
                if in_pos == out_pos:
                    wall_color = color
                else:
                    obj_color = color

            if wall_color is None or obj_color is None:
                return None

            predicted = GeneralizeOperator._predict_gravity_slide(
                raw_in, bg, wall_color, obj_color, h, w)
            if predicted != raw_out:
                return None

        return {"type": "gravity_slide", "bg_color": bg, "confidence": 1.0}

    @staticmethod
    def _predict_gravity_slide(raw_in, bg, wall_color, obj_color, h, w):
        """Slide object components down, gap=1 from wall, gap=0 from placed."""
        obj_cells = set()
        wall_cells = set()
        for r in range(h):
            for c in range(w):
                if raw_in[r][c] == obj_color:
                    obj_cells.add((r, c))
                elif raw_in[r][c] == wall_color:
                    wall_cells.add((r, c))

        # Connected components
        components = []
        visited = set()
        for cell in obj_cells:
            if cell in visited:
                continue
            comp = []
            queue = [cell]
            while queue:
                p = queue.pop(0)
                if p in visited or p not in obj_cells:
                    continue
                visited.add(p)
                comp.append(p)
                r, c = p
                for dr, dc in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                    nb = (r + dr, c + dc)
                    if nb in obj_cells and nb not in visited:
                        queue.append(nb)
            components.append(comp)

        # Process bottom-first (highest bottom row first)
        components.sort(key=lambda comp: -max(r for r, c in comp))

        output = [row[:] for row in raw_in]
        for r, c in obj_cells:
            output[r][c] = bg

        placed = set()

        for comp in components:
            col_bottoms = {}
            for r, c in comp:
                if c not in col_bottoms or r > col_bottoms[c]:
                    col_bottoms[c] = r

            min_shift = h
            for c, bottom_r in col_bottoms.items():
                obs_r = h
                obs_is_wall = True
                for r in range(bottom_r + 1, h):
                    if (r, c) in wall_cells:
                        obs_r = r
                        obs_is_wall = True
                        break
                    if (r, c) in placed:
                        obs_r = r
                        obs_is_wall = False
                        break

                gap = obs_r - bottom_r - 1
                shift = max(0, gap - 1) if obs_is_wall else gap
                if shift < min_shift:
                    min_shift = shift

            for r, c in comp:
                nr = r + min_shift
                if 0 <= nr < h:
                    output[nr][c] = obj_color
                    placed.add((nr, c))

        return output

    # ---- strategy: arrow projection to grid edges ----------------------------

    def _try_arrow_projection(self, patterns, wm):
        """
        Detect pattern: shapes have a core color and a single special-color
        cell. The special cell projects a ray (every 2 cells) toward the
        nearest grid edge, filling that edge with the special color.
        Corners where two borders meet become 0.
        """
        task = wm.task
        if not task or not patterns.get("grid_size_preserved"):
            return None

        for pair in task.example_pairs:
            g0, g1 = pair.input_grid, pair.output_grid
            if not g0 or not g1:
                return None
            raw_in, raw_out = g0.raw, g1.raw
            h = len(raw_in)
            w = len(raw_in[0]) if raw_in else 0

            freq = {}
            for r in range(h):
                for c in range(w):
                    freq[raw_in[r][c]] = freq.get(raw_in[r][c], 0) + 1
            pair_bg = max(freq, key=freq.get)

            shape_infos = GeneralizeOperator._detect_arrow_shapes(
                raw_in, pair_bg, h, w)
            if shape_infos is None:
                return None

            predicted = GeneralizeOperator._predict_arrow_projection(
                raw_in, pair_bg, shape_infos, h, w)
            if predicted != raw_out:
                return None

        return {"type": "arrow_projection", "confidence": 1.0}

    @staticmethod
    def _detect_arrow_shapes(raw, bg, h, w):
        """Find shapes with core + single special cell, determine direction."""
        non_bg = set()
        for r in range(h):
            for c in range(w):
                if raw[r][c] != bg:
                    non_bg.add((r, c))

        if not non_bg:
            return None

        # Connected components
        visited = set()
        shapes = []
        for cell in sorted(non_bg):
            if cell in visited:
                continue
            comp = []
            queue = [cell]
            while queue:
                p = queue.pop(0)
                if p in visited or p not in non_bg:
                    continue
                visited.add(p)
                comp.append(p)
                r, c = p
                for dr, dc in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                    nb = (r + dr, c + dc)
                    if nb in non_bg and nb not in visited:
                        queue.append(nb)
            shapes.append(comp)

        infos = []
        for comp in shapes:
            cc = {}
            for r, c in comp:
                v = raw[r][c]
                cc[v] = cc.get(v, 0) + 1
            if len(cc) != 2:
                continue

            sorted_cc = sorted(cc.items(), key=lambda x: -x[1])
            special_color = sorted_cc[1][0]

            special_cells = [(r, c) for r, c in comp if raw[r][c] == special_color]
            if len(special_cells) != 1:
                continue

            sr, sc = special_cells[0]
            comp_set = set(comp)
            dirs = []
            for dr, dc in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                nr, nc = sr + dr, sc + dc
                if (nr, nc) not in comp_set:
                    if 0 <= nr < h and 0 <= nc < w:
                        if raw[nr][nc] == bg:
                            dirs.append((dr, dc))
                    else:
                        dirs.append((dr, dc))
            if len(dirs) != 1:
                continue

            infos.append({
                "special_color": special_color,
                "special_pos": (sr, sc),
                "direction": dirs[0],
            })

        if not infos:
            return None
        return infos

    @staticmethod
    def _predict_arrow_projection(raw, bg, shape_infos, h, w):
        """Project rays and fill borders for arrow shapes."""
        output = [row[:] for row in raw]

        # Phase 1: place ray dots (every 2 cells from special cell)
        for info in shape_infos:
            sr, sc = info["special_pos"]
            dr, dc = info["direction"]
            sp_color = info["special_color"]
            r, c = sr + dr, sc + dc
            step = 1
            while 0 <= r < h and 0 <= c < w:
                if step % 2 == 0:
                    output[r][c] = sp_color
                r += dr
                c += dc
                step += 1

        # Phase 2: fill border rows/columns
        border_info = {}
        for info in shape_infos:
            dr, dc = info["direction"]
            sp_color = info["special_color"]
            if dr == -1:
                border_info["top"] = sp_color
                for c2 in range(w):
                    output[0][c2] = sp_color
            elif dr == 1:
                border_info["bottom"] = sp_color
                for c2 in range(w):
                    output[h - 1][c2] = sp_color
            elif dc == -1:
                border_info["left"] = sp_color
                for r2 in range(h):
                    output[r2][0] = sp_color
            elif dc == 1:
                border_info["right"] = sp_color
                for r2 in range(h):
                    output[r2][w - 1] = sp_color

        # Phase 3: corners where two borders meet become 0
        for cr, cc, e1, e2 in [(0, 0, "top", "left"),
                                (0, w - 1, "top", "right"),
                                (h - 1, 0, "bottom", "left"),
                                (h - 1, w - 1, "bottom", "right")]:
            if e1 in border_info and e2 in border_info:
                output[cr][cc] = 0

        return output


    # ---- strategy: quadrant pattern swap ------------------------------------

    def _try_quadrant_pattern_swap(self, patterns, wm):
        """
        Detect pattern: grid divided into sections by separator rows/cols of 0.
        Each section has a left and right quadrant with different bg colors.
        Output swaps the foreground patterns: right's pattern -> left (colored as
        right's bg), left's pattern -> right (colored as left's bg).
        If both quadrants share the same bg, both patterns are erased.
        """
        task = wm.task
        if not task:
            return None

        for pair in task.example_pairs:
            g0, g1 = pair.input_grid, pair.output_grid
            if not g0 or not g1:
                return None
            if len(g0.raw) != len(g1.raw):
                return None
            if (len(g0.raw[0]) if g0.raw else 0) != (len(g1.raw[0]) if g1.raw else 0):
                return None

        # Validate each training pair independently
        for pair in task.example_pairs:
            raw_in = pair.input_grid.raw
            raw_out = pair.output_grid.raw
            h = len(raw_in)
            w = len(raw_in[0]) if raw_in else 0
            if h < 3 or w < 5:
                return None

            # Find separator columns (all-zero columns)
            sep_cols = [c for c in range(w)
                        if all(raw_in[r][c] == 0 for r in range(h))]
            if not sep_cols:
                return None

            # Must be a single contiguous run
            for i in range(len(sep_cols) - 1):
                if sep_cols[i + 1] != sep_cols[i] + 1:
                    return None

            left_c0, left_c1 = 0, sep_cols[0] - 1
            right_c0, right_c1 = sep_cols[-1] + 1, w - 1
            if left_c1 < 0 or right_c0 > w - 1:
                return None
            left_w = left_c1 - left_c0 + 1
            right_w = right_c1 - right_c0 + 1
            if left_w != right_w or left_w < 2:
                return None

            # Find separator rows (all-zero rows)
            sep_row_set = set()
            for r in range(h):
                if all(raw_in[r][c] == 0 for c in range(w)):
                    sep_row_set.add(r)

            # Build sections
            sections = []
            r = 0
            while r < h:
                if r in sep_row_set:
                    r += 1
                    continue
                start = r
                while r < h and r not in sep_row_set:
                    r += 1
                sections.append((start, r - 1))
            if len(sections) < 2:
                return None

            # Validate each section
            for rs, re in sections:
                left_bg = self._quadrant_bg(raw_in, rs, re, left_c0, left_c1)
                right_bg = self._quadrant_bg(raw_in, rs, re, right_c0, right_c1)
                if left_bg is None or right_bg is None:
                    return None

                left_pat = self._quadrant_fg(raw_in, rs, re, left_c0, left_c1, left_bg)
                right_pat = self._quadrant_fg(raw_in, rs, re, right_c0, right_c1, right_bg)

                if left_bg == right_bg:
                    # Both patterns erased
                    for r in range(rs, re + 1):
                        for c in range(left_c0, left_c1 + 1):
                            if raw_out[r][c] != left_bg:
                                return None
                        for c in range(right_c0, right_c1 + 1):
                            if raw_out[r][c] != right_bg:
                                return None
                else:
                    # Patterns swap
                    for r in range(rs, re + 1):
                        for c in range(left_c0, left_c1 + 1):
                            rel = (r - rs, c - left_c0)
                            expected = right_bg if rel in right_pat else left_bg
                            if raw_out[r][c] != expected:
                                return None
                        for c in range(right_c0, right_c1 + 1):
                            rel = (r - rs, c - right_c0)
                            expected = left_bg if rel in left_pat else right_bg
                            if raw_out[r][c] != expected:
                                return None

        return {"type": "quadrant_pattern_swap", "confidence": 1.0}

    @staticmethod
    def _quadrant_bg(raw, rs, re, c0, c1):
        freq = {}
        for r in range(rs, re + 1):
            for c in range(c0, c1 + 1):
                v = raw[r][c]
                freq[v] = freq.get(v, 0) + 1
        return max(freq, key=freq.get) if freq else None

    @staticmethod
    def _quadrant_fg(raw, rs, re, c0, c1, bg):
        pat = set()
        for r in range(rs, re + 1):
            for c in range(c0, c1 + 1):
                if raw[r][c] != bg:
                    pat.add((r - rs, c - c0))
        return pat

    # ---- strategy: block wedge split --------------------------------------

    def _try_block_wedge_split(self, patterns, wm):
        """
        Detect pattern: 3 colored blocks on a background. The middle block
        slides into one adjacent block, splitting it into two halves.
        The other block stays in place.
        """
        task = wm.task
        if not task or not patterns.get("grid_size_preserved"):
            return None

        for pair in task.example_pairs:
            g0, g1 = pair.input_grid, pair.output_grid
            if not g0 or not g1:
                return None
            raw_in, raw_out = g0.raw, g1.raw
            h = len(raw_in)
            w = len(raw_in[0]) if raw_in else 0

            # Find background (most frequent)
            freq = {}
            for r in range(h):
                for c in range(w):
                    freq[raw_in[r][c]] = freq.get(raw_in[r][c], 0) + 1
            bg = max(freq, key=freq.get)

            # Group non-bg cells by color (blocks are uniform color)
            color_cells = {}
            for r in range(h):
                for c in range(w):
                    v = raw_in[r][c]
                    if v != bg:
                        color_cells.setdefault(v, []).append((r, c))
            if len(color_cells) != 3:
                return None

            block_infos = []
            for color, cells in color_cells.items():
                rows = [r for r, c in cells]
                cols = [c for r, c in cells]
                block_infos.append({
                    "color": color,
                    "cells": set(cells),
                    "r0": min(rows), "r1": max(rows),
                    "c0": min(cols), "c1": max(cols),
                })

            # Determine arrangement axis and find middle block
            mid = self._find_middle_block(block_infos)
            if mid is None:
                return None

            # Verify the output matches an expected split
            if not self._verify_wedge_split(raw_in, raw_out, block_infos, mid, bg, h, w):
                return None

        return {"type": "block_wedge_split", "confidence": 1.0}

    @staticmethod
    def _find_middle_block(infos):
        """Find the block whose bounding box center is between the other two."""
        for axis in ["r", "c"]:
            centers = []
            for i, b in enumerate(infos):
                centers.append((i, (b[f"{axis}0"] + b[f"{axis}1"]) / 2))
            centers.sort(key=lambda x: x[1])
            idx_low, idx_mid, idx_high = centers[0][0], centers[1][0], centers[2][0]
            # Middle block's range must overlap with both others in the perpendicular axis
            perp = "c" if axis == "r" else "r"
            b_mid = infos[idx_mid]
            b_low = infos[idx_low]
            b_high = infos[idx_high]
            mid_range = (b_mid[f"{perp}0"], b_mid[f"{perp}1"])
            low_range = (b_low[f"{perp}0"], b_low[f"{perp}1"])
            high_range = (b_high[f"{perp}0"], b_high[f"{perp}1"])
            # Check overlap in perpendicular axis
            if (mid_range[1] >= low_range[0] and mid_range[0] <= low_range[1] and
                    mid_range[1] >= high_range[0] and mid_range[0] <= high_range[1]):
                return {"mid": idx_mid, "low": idx_low, "high": idx_high, "axis": axis}
        return None

    @staticmethod
    def _verify_wedge_split(raw_in, raw_out, infos, mid_info, bg, h, w):
        """Verify the output is a valid block wedge split."""
        idx_mid = mid_info["mid"]
        idx_low = mid_info["low"]
        idx_high = mid_info["high"]
        axis = mid_info["axis"]
        b_mid = infos[idx_mid]
        b_low = infos[idx_low]
        b_high = infos[idx_high]

        # Check which neighbor stays in place in the output
        low_stays = all(raw_out[r][c] == raw_in[r][c] for r, c in b_low["cells"])
        high_stays = all(raw_out[r][c] == raw_in[r][c] for r, c in b_high["cells"])

        if not low_stays and not high_stays:
            return False
        if low_stays and high_stays:
            return False  # Both can't stay -- one must split

        anchor_idx = idx_low if low_stays else idx_high
        target_idx = idx_high if low_stays else idx_low

        b_anchor = infos[anchor_idx]
        b_target = infos[target_idx]

        # The target block should be cleared from its original position in the output
        for r, c in b_target["cells"]:
            if raw_out[r][c] == b_target["color"]:
                # It's OK if target cells became the same color in a new arrangement
                pass

        # The middle block should be cleared from its original position
        for r, c in b_mid["cells"]:
            if raw_out[r][c] == b_mid["color"]:
                # Could be part of the new arrangement, allow it
                pass

        # Find where the middle block color appears in the output
        mid_in_out = set()
        for r in range(h):
            for c in range(w):
                if raw_out[r][c] == b_mid["color"]:
                    mid_in_out.add((r, c))

        # The middle block should have moved, same number of cells
        if len(mid_in_out) != len(b_mid["cells"]):
            return False

        # Find where the target block color appears in the output
        tgt_in_out = set()
        for r in range(h):
            for c in range(w):
                if raw_out[r][c] == b_target["color"]:
                    tgt_in_out.add((r, c))

        # Target should have same number of cells
        if len(tgt_in_out) != len(b_target["cells"]):
            return False

        return True

    # ---- block wedge split helpers ----------------------------------------

    @staticmethod
    def _detect_blocks_and_split(raw, bg, h, w):
        """Detect 3 blocks and compute the wedge split transformation."""
        color_cells = {}
        for r in range(h):
            for c in range(w):
                v = raw[r][c]
                if v != bg:
                    color_cells.setdefault(v, []).append((r, c))
        if len(color_cells) != 3:
            return None

        block_infos = []
        for color, cells in color_cells.items():
            rows = [r for r, c in cells]
            cols = [c for r, c in cells]
            block_infos.append({
                "color": color,
                "cells": set(cells),
                "r0": min(rows), "r1": max(rows),
                "c0": min(cols), "c1": max(cols),
            })

        mid_info = GeneralizeOperator._find_middle_block(block_infos)
        if mid_info is None:
            return None

        return block_infos, mid_info

    # ---- strategy: block grid bar chart ------------------------------------

    def _try_block_grid_bar_chart(self, patterns, wm):
        """
        Detect pattern: large grid with 3x3 block tiles arranged in a meta-grid.
        One section has 8-tiles, another has colored tiles. A divider row/column
        of 1s at one edge indicates orientation. Output is a small bar chart
        summary where each bar length = colored-count + eight-count.
        """
        task = wm.task
        if not task:
            return None
        if patterns.get("grid_size_preserved"):
            return None

        for pair in task.example_pairs:
            g0, g1 = pair.input_grid, pair.output_grid
            if not g0 or not g1:
                return None
            predicted = GeneralizeOperator._solve_bar_chart(g0.raw)
            if predicted is None or predicted != g1.raw:
                return None

        return {"type": "block_grid_bar_chart", "confidence": 1.0}

    @staticmethod
    def _solve_bar_chart(raw):
        """Parse block-grid input and produce bar chart output."""
        h = len(raw)
        w = len(raw[0]) if raw else 0
        if h < 10 or w < 10:
            return None

        # Find divider (edge row/col of all 1s)
        divider = None
        if all(raw[0][c] == 1 for c in range(w)):
            divider = 'top'
        elif all(raw[h - 1][c] == 1 for c in range(w)):
            divider = 'bottom'
        elif all(raw[r][0] == 1 for r in range(h)):
            divider = 'left'
        elif all(raw[r][w - 1] == 1 for r in range(h)):
            divider = 'right'
        if divider is None:
            return None

        # Scan ranges excluding divider
        if divider == 'top':
            rr, cr = range(1, h), range(w)
        elif divider == 'bottom':
            rr, cr = range(h - 1), range(w)
        elif divider == 'left':
            rr, cr = range(h), range(1, w)
        else:
            rr, cr = range(h), range(w - 1)

        # Find row-groups (consecutive rows with non-0 content)
        active_rows = set()
        for r in rr:
            for c in cr:
                if raw[r][c] != 0:
                    active_rows.add(r)
                    break
        row_groups = GeneralizeOperator._group_consecutive(sorted(active_rows))
        if not row_groups or any(e - s + 1 != 3 for s, e in row_groups):
            return None

        # Find col-slots (consecutive cols with non-0 content)
        active_cols = set()
        for c in cr:
            for r in rr:
                if raw[r][c] != 0:
                    active_cols.add(c)
                    break
        col_slots = GeneralizeOperator._group_consecutive(sorted(active_cols))
        if not col_slots or any(e - s + 1 != 3 for s, e in col_slots):
            return None

        n_rg = len(row_groups)
        n_cs = len(col_slots)

        # Build meta-grid: each cell = block color or 0
        meta = [[0] * n_cs for _ in range(n_rg)]
        for ri, (rs, re) in enumerate(row_groups):
            for ci, (cs, ce) in enumerate(col_slots):
                bc = None
                for r in range(rs, re + 1):
                    for c in range(cs, ce + 1):
                        v = raw[r][c]
                        if v != 0:
                            if bc is None:
                                bc = v
                            elif v != bc:
                                return None
                meta[ri][ci] = bc if bc else 0

        if divider in ('top', 'bottom'):
            # Horizontal bars — compare column positions of 8 vs colored
            e_avg, e_cnt, c_avg, c_cnt = 0, 0, 0, 0
            for ci in range(n_cs):
                for ri in range(n_rg):
                    v = meta[ri][ci]
                    if v == 8:
                        e_avg += ci; e_cnt += 1
                    elif v != 0:
                        c_avg += ci; c_cnt += 1
            if e_cnt == 0 or c_cnt == 0:
                return None
            eight_first = (e_avg / e_cnt) < (c_avg / c_cnt)

            rows_out = []
            for ri in range(n_rg):
                cc, ec, rc = 0, 0, 0
                for ci in range(n_cs):
                    v = meta[ri][ci]
                    if v == 8:
                        ec += 1
                    elif v != 0:
                        cc += 1; rc = v
                rows_out.append((cc, ec, rc))

            out_w = max(x + y for x, y, _ in rows_out)
            if out_w == 0:
                return None
            output = []
            for cc, ec, rc in rows_out:
                pad = out_w - cc - ec
                if eight_first:
                    bar = [8] * ec + ([rc] * cc if cc else [])
                else:
                    bar = ([rc] * cc if cc else []) + [8] * ec
                if divider == 'top':
                    output.append([0] * pad + bar)
                else:
                    output.append(bar + [0] * pad)
            return output

        else:  # left / right — vertical bars
            e_avg, e_cnt, c_avg, c_cnt = 0, 0, 0, 0
            for ri in range(n_rg):
                for ci in range(n_cs):
                    v = meta[ri][ci]
                    if v == 8:
                        e_avg += ri; e_cnt += 1
                    elif v != 0:
                        c_avg += ri; c_cnt += 1
            if e_cnt == 0 or c_cnt == 0:
                return None
            eight_first = (e_avg / e_cnt) < (c_avg / c_cnt)

            cols_out = []
            for ci in range(n_cs):
                ec, cc, col_c = 0, 0, 0
                for ri in range(n_rg):
                    v = meta[ri][ci]
                    if v == 8:
                        ec += 1
                    elif v != 0:
                        cc += 1; col_c = v
                cols_out.append((ec, cc, col_c))

            out_h = max(e + c for e, c, _ in cols_out)
            if out_h == 0:
                return None
            output = [[0] * n_cs for _ in range(out_h)]
            for ci, (ec, cc, col_c) in enumerate(cols_out):
                pad = out_h - ec - cc
                if eight_first:
                    cells = [8] * ec + ([col_c] * cc if cc else [])
                else:
                    cells = ([col_c] * cc if cc else []) + [8] * ec
                if divider == 'left':
                    for i, v in enumerate(cells):
                        output[i][ci] = v
                else:
                    for i, v in enumerate(cells):
                        output[pad + i][ci] = v
            return output

    @staticmethod
    def _group_consecutive(sorted_vals):
        """Group consecutive integers into (start, end) ranges."""
        if not sorted_vals:
            return []
        groups = []
        i = 0
        while i < len(sorted_vals):
            s = sorted_vals[i]
            e = s
            while i + 1 < len(sorted_vals) and sorted_vals[i + 1] == e + 1:
                i += 1
                e = sorted_vals[i]
            groups.append((s, e))
            i += 1
        return groups

    # ---- strategy: template stamp with rotation/reflection ------------------

    def _try_template_stamp_rotate(self, patterns, wm):
        """
        Detect pattern: template shapes (body color + marker colors) and groups
        of scattered marker pixels. Output places rotated/reflected template
        body at each marker group, erasing the originals. Body and marker
        colors may vary between pairs.
        """
        task = wm.task
        if not task or not patterns.get("grid_size_preserved"):
            return None

        for pair in task.example_pairs:
            g0, g1 = pair.input_grid, pair.output_grid
            if not g0 or not g1:
                return None
            raw_in, raw_out = g0.raw, g1.raw
            h = len(raw_in)
            w = len(raw_in[0]) if raw_in else 0

            freq = {}
            for r in range(h):
                for c in range(w):
                    freq[raw_in[r][c]] = freq.get(raw_in[r][c], 0) + 1
            bg = max(freq, key=freq.get)

            result = GeneralizeOperator._solve_template_stamp(raw_in, bg, h, w)
            if result is None:
                return None
            predicted = result[0]
            if predicted != raw_out:
                return None

        return {"type": "template_stamp_rotate", "confidence": 1.0}

    @staticmethod
    def _solve_template_stamp(raw, bg, h, w):
        """
        Find templates and marker groups, match, transform, and build output.
        Returns (output_grid, body_color, marker_colors) or None.
        """
        # 8 rigid transformations: (a,b,c,d) maps (dr,dc) -> (a*dr+b*dc, c*dr+d*dc)
        TRANSFORMS = [
            (1, 0, 0, 1), (0, 1, -1, 0), (-1, 0, 0, -1), (0, -1, 1, 0),
            (1, 0, 0, -1), (-1, 0, 0, 1), (0, 1, 1, 0), (0, -1, -1, 0),
        ]

        # Find connected components of non-bg cells
        non_bg = {}
        for r in range(h):
            for c in range(w):
                v = raw[r][c]
                if v != bg:
                    non_bg[(r, c)] = v
        if not non_bg:
            return None

        visited = set()
        components = []
        for pos in sorted(non_bg):
            if pos in visited:
                continue
            comp = set()
            queue = [pos]
            while queue:
                p = queue.pop(0)
                if p in visited:
                    continue
                visited.add(p)
                comp.add(p)
                r, c = p
                for dr, dc in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                    nb = (r + dr, c + dc)
                    if nb in non_bg and nb not in visited:
                        queue.append(nb)
            components.append(comp)

        # Classify: template (multi-cell, >=3 colors) vs marker (single cell)
        templates = []
        markers = []
        body_color = None
        marker_colors = None

        for comp in components:
            if len(comp) == 1:
                markers.append(list(comp)[0])
                continue
            colors = {}
            for p in comp:
                v = non_bg[p]
                colors[v] = colors.get(v, 0) + 1
            if len(colors) < 3:
                return None
            bc = max(colors, key=colors.get)
            mc = frozenset(c for c in colors if c != bc)
            if not all(colors[c] == 1 for c in mc) or len(mc) < 2:
                return None
            if body_color is None:
                body_color = bc
                marker_colors = mc
            elif bc != body_color or mc != marker_colors:
                return None
            templates.append({
                'body': {p for p in comp if non_bg[p] == bc},
                'markers': {non_bg[p]: p for p in comp if non_bg[p] != bc},
            })

        if not templates or marker_colors is None:
            return None

        # Group scattered markers (filter to marker colors only)
        marker_by_color = {}
        for pos in markers:
            c = non_bg[pos]
            if c in marker_colors:
                marker_by_color.setdefault(c, []).append(pos)

        if len(marker_by_color) != len(marker_colors):
            return None
        counts = [len(v) for v in marker_by_color.values()]
        if len(set(counts)) != 1:
            return None
        n_groups = counts[0]
        if n_groups != len(templates):
            return None

        # Form marker groups by proximity
        colors_list = sorted(marker_colors)
        ref_color = colors_list[0]
        other_colors = colors_list[1:]
        groups = []
        used = {c: set() for c in other_colors}

        for ref_pos in sorted(marker_by_color[ref_color]):
            group = {ref_color: ref_pos}
            for oc in other_colors:
                best, best_d = None, float('inf')
                for pos in marker_by_color[oc]:
                    if pos in used[oc]:
                        continue
                    d = abs(pos[0] - ref_pos[0]) + abs(pos[1] - ref_pos[1])
                    if d < best_d:
                        best_d = d
                        best = pos
                if best is None:
                    return None
                group[oc] = best
                used[oc].add(best)
            groups.append(group)

        # Match templates to groups via transformation search
        def find_transform(t, g):
            t_ref = t['markers'][ref_color]
            a_ref = g[ref_color]
            for trans in TRANSFORMS:
                a, b, c, d = trans
                ok = True
                for mc in colors_list[1:]:
                    dr = t['markers'][mc][0] - t_ref[0]
                    dc = t['markers'][mc][1] - t_ref[1]
                    er = a_ref[0] + a * dr + b * dc
                    ec = a_ref[1] + c * dr + d * dc
                    if (er, ec) != g[mc]:
                        ok = False
                        break
                if ok:
                    return trans
            return None

        # Try all permutations (max 2 templates)
        if n_groups == 1:
            perms = [(0,)]
        elif n_groups == 2:
            perms = [(0, 1), (1, 0)]
        else:
            return None

        assignment = None
        for perm in perms:
            matches = []
            ok = True
            for ti, gi in enumerate(perm):
                trans = find_transform(templates[ti], groups[gi])
                if trans is None:
                    ok = False
                    break
                matches.append((ti, gi, trans))
            if ok:
                assignment = matches
                break

        if assignment is None:
            return None

        # Build output
        output = [[bg] * w for _ in range(h)]
        for ti, gi, trans in assignment:
            t = templates[ti]
            g = groups[gi]
            a, b, c, d = trans
            t_ref = t['markers'][ref_color]
            a_ref = g[ref_color]

            # Place markers at anchor positions
            for mc, pos in g.items():
                output[pos[0]][pos[1]] = mc

            # Place transformed body
            for bp in t['body']:
                dr = bp[0] - t_ref[0]
                dc = bp[1] - t_ref[1]
                nr = a_ref[0] + a * dr + b * dc
                nc = a_ref[1] + c * dr + d * dc
                if 0 <= nr < h and 0 <= nc < w:
                    output[nr][nc] = body_color

        return (output, body_color, marker_colors)


    # ---- strategy: pixel count diamond (count colors → rectangle + X) ----

    def _try_pixel_count_diamond(self, patterns, wm):
        """
        Detect pattern: input has background + exactly 2 non-background colors.
        Output is a fixed-size grid (16×16) with a bottom-left rectangle filled
        with color 2, and two diagonal lines (color 4) from the bottom corners
        forming a V / X / diamond shape.

        Width of rectangle = count of the more frequent non-bg color.
        Height of rectangle = count of the less frequent non-bg color.

        Category: tasks where pixel counts of scattered dots determine the
        dimensions of a geometric output pattern.
        """
        task = wm.task
        if not task or len(task.example_pairs) < 1:
            return None

        # Verify across all training examples
        for pair in task.example_pairs:
            g0, g1 = pair.input_grid, pair.output_grid
            if not g0 or not g1:
                return None
            raw_in = g0.raw
            raw_out = g1.raw
            h_out = len(raw_out)
            w_out = len(raw_out[0]) if raw_out else 0

            # Output must be 16×16
            if h_out != 16 or w_out != 16:
                return None

            # Count non-background colors in input
            bg, counts = self._count_non_bg(raw_in)
            if bg is None or len(counts) != 2:
                return None

            colors_sorted = sorted(counts.keys(), key=lambda c: counts[c], reverse=True)
            width = counts[colors_sorted[0]]
            height = counts[colors_sorted[1]]

            if width < 1 or height < 1 or width > 16 or height > 16:
                return None

            # Verify output structure: bottom-left rectangle of 2+4, rest is bg
            start_row = 16 - height
            for r in range(16):
                for c in range(16):
                    v = raw_out[r][c]
                    in_rect = (r >= start_row and c < width)
                    if in_rect:
                        if v not in (2, 4):
                            return None
                    else:
                        if v != bg:
                            return None

            # Verify diagonal pattern inside rectangle
            for r in range(start_row, 16):
                d = 15 - r
                left_col = d
                right_col = (width - 1) - d
                for c in range(width):
                    expected = 4 if (c == left_col or c == right_col) else 2
                    if raw_out[r][c] != expected:
                        return None

        return {
            "type": "pixel_count_diamond",
            "bg": bg,
            "confidence": 1.0,
        }

    # ---- strategy: rotation tile 2×2 ------------------------------------

    def _try_rotate_tile_2x2(self, patterns, wm):
        """
        Detect pattern: output is 2× the input dimensions, formed by tiling
        4 rotations of the input (original, 90°CCW, 180°, 90°CW) in a 2×2
        arrangement: TL=original, TR=90°CCW, BL=180°, BR=90°CW.

        Category: tasks where a small grid is expanded by rotation tiling.
        """
        task = wm.task
        if not task or len(task.example_pairs) < 1:
            return None

        for pair in task.example_pairs:
            g0, g1 = pair.input_grid, pair.output_grid
            if not g0 or not g1:
                return None
            raw_in = g0.raw
            raw_out = g1.raw
            h_in = len(raw_in)
            w_in = len(raw_in[0]) if raw_in else 0
            h_out = len(raw_out)
            w_out = len(raw_out[0]) if raw_out else 0

            if h_out != 2 * h_in or w_out != 2 * w_in:
                return None

            orig = [row[:] for row in raw_in]
            ccw90 = self._rotate_ccw90(orig)
            rot180 = self._rotate_180(orig)
            cw90 = self._rotate_cw90(orig)

            if not self._check_quadrant(raw_out, 0, 0, orig):
                return None
            if not self._check_quadrant(raw_out, 0, w_in, ccw90):
                return None
            if not self._check_quadrant(raw_out, h_in, 0, rot180):
                return None
            if not self._check_quadrant(raw_out, h_in, w_in, cw90):
                return None

        return {"type": "rotate_tile_2x2", "confidence": 1.0}

    @staticmethod
    def _rotate_cw90(grid):
        h = len(grid)
        w = len(grid[0]) if grid else 0
        return [[grid[h - 1 - c][r] for c in range(h)] for r in range(w)]

    @staticmethod
    def _rotate_ccw90(grid):
        h = len(grid)
        w = len(grid[0]) if grid else 0
        return [[grid[c][w - 1 - r] for c in range(h)] for r in range(w)]

    @staticmethod
    def _rotate_180(grid):
        h = len(grid)
        w = len(grid[0]) if grid else 0
        return [[grid[h - 1 - r][w - 1 - c] for c in range(w)] for r in range(h)]

    @staticmethod
    def _check_quadrant(output, row_off, col_off, expected):
        h = len(expected)
        w = len(expected[0]) if expected else 0
        for r in range(h):
            for c in range(w):
                if output[row_off + r][col_off + c] != expected[r][c]:
                    return False
        return True

    # ---- strategy: diagonal extend ---------------------------------------

    def _try_diagonal_extend(self, patterns, wm):
        """
        Detect pattern: a 2×2 block of one color with diagonal 'tail' pixels
        of the same color. Each tail is extended as a diagonal line from the
        tail pixel to the grid edge, in the direction away from the block.

        Category: tasks with a compact core that projects diagonal rays.
        """
        task = wm.task
        if not task or len(task.example_pairs) < 1:
            return None

        for pair in task.example_pairs:
            g0, g1 = pair.input_grid, pair.output_grid
            if not g0 or not g1:
                return None
            raw_in = g0.raw
            raw_out = g1.raw
            h = len(raw_in)
            w = len(raw_in[0]) if raw_in else 0

            if len(raw_out) != h or (raw_out and len(raw_out[0]) != w):
                return None

            # Find foreground color and positions
            fg_color = None
            fg_positions = []
            for r in range(h):
                for c in range(w):
                    if raw_in[r][c] != 0:
                        fg_positions.append((r, c))
                        if fg_color is None:
                            fg_color = raw_in[r][c]
                        elif raw_in[r][c] != fg_color:
                            return None

            if fg_color is None or len(fg_positions) < 5:
                return None

            # Find the 2×2 block
            block_pos = None
            for r in range(h - 1):
                for c in range(w - 1):
                    if (raw_in[r][c] == fg_color and raw_in[r][c + 1] == fg_color and
                            raw_in[r + 1][c] == fg_color and raw_in[r + 1][c + 1] == fg_color):
                        block_pos = (r, c)
                        break
                if block_pos:
                    break

            if block_pos is None:
                return None

            blk_r, blk_c = block_pos
            block_cells = {(blk_r, blk_c), (blk_r, blk_c + 1),
                           (blk_r + 1, blk_c), (blk_r + 1, blk_c + 1)}
            tails = [p for p in fg_positions if p not in block_cells]
            if not tails:
                return None

            # Each tail must be diagonally adjacent to a block corner
            for tr, tc in tails:
                is_diag = any(
                    abs(tr - cr) == 1 and abs(tc - cc) == 1
                    for cr, cc in block_cells
                )
                if not is_diag:
                    return None

            # Build expected output
            expected = [[0] * w for _ in range(h)]
            for r, c in fg_positions:
                expected[r][c] = fg_color

            center_r = blk_r + 0.5
            center_c = blk_c + 0.5
            for tr, tc in tails:
                dr = 1 if tr > center_r else -1
                dc = 1 if tc > center_c else -1
                nr, nc = tr + dr, tc + dc
                while 0 <= nr < h and 0 <= nc < w:
                    expected[nr][nc] = fg_color
                    nr += dr
                    nc += dc

            if expected != raw_out:
                return None

        return {"type": "diagonal_extend", "confidence": 1.0}

    # ---- strategy: quadrant diagonal fill --------------------------------

    def _try_quadrant_diagonal_fill(self, patterns, wm):
        """
        Detect pattern: grid with a 2×2 block of 4 distinct non-zero colors
        on a zero background. Output fills each corner region (relative to
        the 2×2 block) with the diagonally opposite color from the block.

        Category: tasks with a colored seed block that projects corner fills.
        """
        task = wm.task
        if not task or len(task.example_pairs) < 1:
            return None

        for pair in task.example_pairs:
            g0, g1 = pair.input_grid, pair.output_grid
            if not g0 or not g1:
                return None
            raw_in = g0.raw
            raw_out = g1.raw
            h = len(raw_in)
            w = len(raw_in[0]) if raw_in else 0

            if len(raw_out) != h or (raw_out and len(raw_out[0]) != w):
                return None

            # Find 2×2 block of 4 distinct non-zero colors
            block_pos = None
            block_colors = None
            for r in range(h - 1):
                for c in range(w - 1):
                    tl = raw_in[r][c]
                    tr = raw_in[r][c + 1]
                    bl = raw_in[r + 1][c]
                    br = raw_in[r + 1][c + 1]
                    if tl != 0 and tr != 0 and bl != 0 and br != 0:
                        if len({tl, tr, bl, br}) == 4:
                            block_pos = (r, c)
                            block_colors = (tl, tr, bl, br)
                            break
                if block_pos:
                    break

            if block_pos is None:
                return None

            blk_r, blk_c = block_pos
            tl_c, tr_c, bl_c, br_c = block_colors

            # All other input cells should be 0
            for r in range(h):
                for c in range(w):
                    if (r, c) in {(blk_r, blk_c), (blk_r, blk_c + 1),
                                  (blk_r + 1, blk_c), (blk_r + 1, blk_c + 1)}:
                        continue
                    if raw_in[r][c] != 0:
                        return None

            # Build expected output: place 2×2 fills at diagonal neighbors,
            # clipped to grid boundaries
            expected = [row[:] for row in raw_in]
            # TL fill: rows [blk_r-2, blk_r), cols [blk_c-2, blk_c)
            for r in range(max(0, blk_r - 2), blk_r):
                for c in range(max(0, blk_c - 2), blk_c):
                    expected[r][c] = br_c
            # TR fill: rows [blk_r-2, blk_r), cols [blk_c+2, blk_c+4)
            for r in range(max(0, blk_r - 2), blk_r):
                for c in range(blk_c + 2, min(w, blk_c + 4)):
                    expected[r][c] = bl_c
            # BL fill: rows [blk_r+2, blk_r+4), cols [blk_c-2, blk_c)
            for r in range(blk_r + 2, min(h, blk_r + 4)):
                for c in range(max(0, blk_c - 2), blk_c):
                    expected[r][c] = tr_c
            # BR fill: rows [blk_r+2, blk_r+4), cols [blk_c+2, blk_c+4)
            for r in range(blk_r + 2, min(h, blk_r + 4)):
                for c in range(blk_c + 2, min(w, blk_c + 4)):
                    expected[r][c] = tl_c

            if expected != raw_out:
                return None

        return {"type": "quadrant_diagonal_fill", "confidence": 1.0}

    # ---- strategy: corner ray projection -----------------------------------

    def _try_corner_ray(self, patterns, wm):
        """
        Detect: sparse grid (mostly 0s) with isolated non-zero pixels.
        Each pixel shoots L-shaped rays toward the nearest grid corner.
        """
        task = wm.task
        if task is None:
            return None

        for pair in task.example_pairs:
            raw_in = pair.input_grid.raw
            raw_out = pair.output_grid.raw
            h = len(raw_in)
            w = len(raw_in[0]) if raw_in else 0

            if len(raw_out) != h or (raw_out and len(raw_out[0]) != w):
                return None

            # Collect non-zero pixels from input
            pixels = []
            for r in range(h):
                for c in range(w):
                    if raw_in[r][c] != 0:
                        pixels.append((r, c, raw_in[r][c]))

            if not pixels:
                return None

            # Must be sparse (mostly background)
            if len(pixels) > h * w * 0.3:
                return None

            # Build expected output
            expected = [[0] * w for _ in range(h)]
            for r, c, color in pixels:
                corners = [
                    (0, 0, r + c),
                    (0, w - 1, r + (w - 1 - c)),
                    (h - 1, 0, (h - 1 - r) + c),
                    (h - 1, w - 1, (h - 1 - r) + (w - 1 - c)),
                ]
                corners.sort(key=lambda x: x[2])
                cr, cc, _ = corners[0]

                # Vertical ray toward corner row
                for rr in range(min(r, cr), max(r, cr) + 1):
                    expected[rr][c] = color
                # Horizontal ray toward corner col
                for cc2 in range(min(c, cc), max(c, cc) + 1):
                    expected[r][cc2] = color

            if expected != raw_out:
                return None

        return {"type": "corner_ray", "confidence": 1.0}

    # ---- strategy: flood fill enclosed regions ------------------------------

    def _try_flood_fill_enclosed(self, patterns, wm):
        """
        Detect: grid has non-zero frame color forming closed shapes on 0 bg.
        Enclosed 0-cells (not reachable from grid border via 0-path) become 1.
        """
        task = wm.task
        if task is None:
            return None

        for pair in task.example_pairs:
            raw_in = pair.input_grid.raw
            raw_out = pair.output_grid.raw
            h = len(raw_in)
            w = len(raw_in[0]) if raw_in else 0

            if len(raw_out) != h or (raw_out and len(raw_out[0]) != w):
                return None

            # Input must have only 0 and frame color(s)
            # Output introduces color 1 for enclosed cells
            has_one_in = any(raw_in[r][c] == 1 for r in range(h) for c in range(w))
            has_one_out = any(raw_out[r][c] == 1 for r in range(h) for c in range(w))
            if has_one_in or not has_one_out:
                return None

            # Flood fill from border: find all 0-cells reachable from border
            reachable = [[False] * w for _ in range(h)]
            queue = []
            for r in range(h):
                for c in range(w):
                    if (r == 0 or r == h - 1 or c == 0 or c == w - 1) and raw_in[r][c] == 0:
                        if not reachable[r][c]:
                            reachable[r][c] = True
                            queue.append((r, c))

            qi = 0
            while qi < len(queue):
                r, c = queue[qi]
                qi += 1
                for dr, dc in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                    nr, nc = r + dr, c + dc
                    if 0 <= nr < h and 0 <= nc < w and not reachable[nr][nc] and raw_in[nr][nc] == 0:
                        reachable[nr][nc] = True
                        queue.append((nr, nc))

            # Build expected output
            expected = [row[:] for row in raw_in]
            enclosed_count = 0
            for r in range(h):
                for c in range(w):
                    if raw_in[r][c] == 0 and not reachable[r][c]:
                        expected[r][c] = 1
                        enclosed_count += 1

            if enclosed_count == 0:
                return None

            if expected != raw_out:
                return None

        return {"type": "flood_fill_enclosed", "confidence": 1.0}

    # ---- strategy: count signal pixels in rect → fill 3×3 -----------------

    def _try_count_fill_grid(self, patterns, wm):
        """
        Detect: input has 1-bordered rectangle + signal-colored pixels.
        Output is 3×3 grid, N cells filled in reading order with signal color,
        where N = count of signal pixels inside the rectangle.
        """
        task = wm.task
        if task is None:
            return None

        for pair in task.example_pairs:
            raw_in = pair.input_grid.raw
            raw_out = pair.output_grid.raw
            h_in = len(raw_in)
            w_in = len(raw_in[0]) if raw_in else 0
            h_out = len(raw_out)
            w_out = len(raw_out[0]) if raw_out else 0

            # Output must be 3×3
            if h_out != 3 or w_out != 3:
                return None

            # Find 1-bordered rectangle in input
            ones = [(r, c) for r in range(h_in) for c in range(w_in) if raw_in[r][c] == 1]
            if not ones:
                return None

            min_r = min(r for r, c in ones)
            max_r = max(r for r, c in ones)
            min_c = min(c for r, c in ones)
            max_c = max(c for r, c in ones)

            # Verify rectangle border is all 1s
            border_ok = True
            for r in range(min_r, max_r + 1):
                for c in range(min_c, max_c + 1):
                    on_border = (r == min_r or r == max_r or c == min_c or c == max_c)
                    if on_border and raw_in[r][c] != 1:
                        border_ok = False
                        break
                if not border_ok:
                    break
            if not border_ok:
                return None

            # Find signal color (non-0, non-1)
            signal_color = None
            for r in range(h_in):
                for c in range(w_in):
                    v = raw_in[r][c]
                    if v != 0 and v != 1:
                        signal_color = v
                        break
                if signal_color is not None:
                    break
            if signal_color is None:
                return None

            # Count signal pixels inside the rectangle (not on border)
            inside_count = 0
            for r in range(min_r + 1, max_r):
                for c in range(min_c + 1, max_c):
                    if raw_in[r][c] == signal_color:
                        inside_count += 1

            # Build expected 3×3 output
            expected = [[0, 0, 0] for _ in range(3)]
            filled = 0
            for r in range(3):
                for c in range(3):
                    if filled < inside_count:
                        expected[r][c] = signal_color
                        filled += 1

            if expected != raw_out:
                return None

        return {"type": "count_fill_grid", "confidence": 1.0}

    # ---- strategy: grid intersection summary --------------------------------

    def _try_grid_intersection_summary(self, patterns, wm):
        """
        Detect: input is a large grid divided by separator lines of one color.
        Some separator intersections have non-grid colors forming rectangular
        regions. Output is a small (N-1)x(M-1) grid where each cell is the
        color if the four surrounding intersection corners share that color,
        else 0.

        Category: tasks with regular grids and colored intersection markers.
        """
        task = wm.task
        if task is None or len(task.example_pairs) < 1:
            return None

        for pair in task.example_pairs:
            g0, g1 = pair.input_grid, pair.output_grid
            if not g0 or not g1:
                return None
            raw_in = g0.raw
            raw_out = g1.raw
            h = len(raw_in)
            w = len(raw_in[0]) if raw_in else 0
            h_out = len(raw_out)
            w_out = len(raw_out[0]) if raw_out else 0

            # Must shrink significantly
            if h_out >= h or w_out >= w or h < 10 or w < 10:
                return None

            # Detect grid separator color and spacing
            info = self._detect_grid_separators(raw_in)
            if info is None:
                return None

            grid_color, sep_rows, sep_cols = info

            # Extract intersection values
            int_grid = []
            for sr in sep_rows:
                row_vals = []
                for sc in sep_cols:
                    row_vals.append(raw_in[sr][sc])
                int_grid.append(row_vals)

            # Find bounding box of non-grid intersections
            marked_rows = []
            marked_cols = []
            for ri, sr in enumerate(sep_rows):
                for ci, sc in enumerate(sep_cols):
                    if int_grid[ri][ci] != grid_color:
                        marked_rows.append(ri)
                        marked_cols.append(ci)

            if not marked_rows:
                return None

            min_ri = min(marked_rows)
            max_ri = max(marked_rows)
            min_ci = min(marked_cols)
            max_ci = max(marked_cols)

            n_rows = max_ri - min_ri + 1
            n_cols = max_ci - min_ci + 1

            if n_rows < 2 or n_cols < 2:
                return None

            # Output should be (n_rows-1) x (n_cols-1)
            if h_out != n_rows - 1 or w_out != n_cols - 1:
                return None

            # Build expected output: each cell (i,j) = color if all 4 corners
            # at (i,j), (i,j+1), (i+1,j), (i+1,j+1) share same non-grid color
            expected = []
            for i in range(n_rows - 1):
                row = []
                for j in range(n_cols - 1):
                    tl = int_grid[min_ri + i][min_ci + j]
                    tr = int_grid[min_ri + i][min_ci + j + 1]
                    bl = int_grid[min_ri + i + 1][min_ci + j]
                    br = int_grid[min_ri + i + 1][min_ci + j + 1]
                    if (tl == tr == bl == br) and tl != grid_color:
                        row.append(tl)
                    else:
                        row.append(0)
                expected.append(row)

            if expected != raw_out:
                return None

        return {"type": "grid_intersection_summary", "confidence": 1.0}

    @staticmethod
    def _detect_grid_separators(raw):
        """Detect uniform grid separator lines and their color/positions."""
        h = len(raw)
        w = len(raw[0]) if raw else 0
        if h < 5 or w < 5:
            return None

        from collections import Counter

        # Find the separator color by looking for rows that are nearly uniform.
        # For each row, find its dominant color and how dominant it is.
        row_dominant = {}  # color -> list of rows where it dominates
        for r in range(h):
            row_freq = Counter(raw[r][c] for c in range(w))
            dom_color, dom_count = row_freq.most_common(1)[0]
            if dom_count >= w * 0.8:
                row_dominant.setdefault(dom_color, []).append(r)

        # Try each candidate separator color
        for grid_color, sep_rows_candidate in sorted(
            row_dominant.items(), key=lambda x: -len(x[1])
        ):
            if len(sep_rows_candidate) < 3:
                continue

            # Check regular spacing
            row_diffs = [sep_rows_candidate[i+1] - sep_rows_candidate[i]
                         for i in range(len(sep_rows_candidate)-1)]
            if len(set(row_diffs)) != 1:
                continue

            # Find separator cols for this color
            sep_cols = []
            for c in range(w):
                gc_count = sum(1 for r in range(h) if raw[r][c] == grid_color)
                if gc_count >= h * 0.8:
                    sep_cols.append(c)

            if len(sep_cols) < 3:
                continue

            col_diffs = [sep_cols[i+1] - sep_cols[i]
                         for i in range(len(sep_cols)-1)]
            if len(set(col_diffs)) != 1:
                continue

            return grid_color, sep_rows_candidate, sep_cols

        return None

    # ---- strategy: frame color swap -----------------------------------------

    def _try_frame_color_swap(self, patterns, wm):
        """
        Detect: input is mostly 0 with a single rectangle of border_color
        surrounding interior cells of interior_color. Output is just the
        rectangle extracted with colors swapped (border↔interior).

        Category: tasks with bordered rectangles on black backgrounds.
        """
        task = wm.task
        if task is None or len(task.example_pairs) < 1:
            return None

        for pair in task.example_pairs:
            g0, g1 = pair.input_grid, pair.output_grid
            if not g0 or not g1:
                return None
            raw_in = g0.raw
            raw_out = g1.raw
            h_in = len(raw_in)
            w_in = len(raw_in[0]) if raw_in else 0

            # Find non-zero bounding box
            nz_positions = []
            for r in range(h_in):
                for c in range(w_in):
                    if raw_in[r][c] != 0:
                        nz_positions.append((r, c))
            if len(nz_positions) < 4:
                return None

            min_r = min(r for r, c in nz_positions)
            max_r = max(r for r, c in nz_positions)
            min_c = min(c for r, c in nz_positions)
            max_c = max(c for r, c in nz_positions)

            rect_h = max_r - min_r + 1
            rect_w = max_c - min_c + 1

            if rect_h < 3 or rect_w < 3:
                return None

            # Output must match rectangle dimensions
            h_out = len(raw_out)
            w_out = len(raw_out[0]) if raw_out else 0
            if h_out != rect_h or w_out != rect_w:
                return None

            # Extract rectangle from input
            rect = []
            for r in range(min_r, max_r + 1):
                rect.append([raw_in[r][c] for c in range(min_c, max_c + 1)])

            # Find border color (on the rectangle border) and interior color
            border_color = rect[0][0]
            if border_color == 0:
                return None

            # All border cells must be border_color
            interior_color = None
            for r in range(rect_h):
                for c in range(rect_w):
                    on_border = (r == 0 or r == rect_h - 1 or c == 0 or c == rect_w - 1)
                    if on_border:
                        if rect[r][c] != border_color:
                            return None
                    else:
                        if rect[r][c] != border_color:
                            if interior_color is None:
                                interior_color = rect[r][c]
                            elif rect[r][c] != interior_color:
                                return None

            if interior_color is None:
                return None

            # Verify output is the swapped version
            expected = []
            for r in range(rect_h):
                row = []
                for c in range(rect_w):
                    if rect[r][c] == border_color:
                        row.append(interior_color)
                    elif rect[r][c] == interior_color:
                        row.append(border_color)
                    else:
                        row.append(rect[r][c])
                expected.append(row)

            if expected != raw_out:
                return None

        return {"type": "frame_color_swap", "confidence": 1.0}

    # ---- strategy: tile pattern upward --------------------------------------

    def _try_tile_pattern_upward(self, patterns, wm):
        """
        Detect: input has background at top and a pattern at the bottom.
        Output tiles the bottom pattern upward to fill the entire grid.

        Category: tasks where a pattern at one edge repeats to fill the grid.
        """
        task = wm.task
        if task is None or len(task.example_pairs) < 1:
            return None

        if not patterns.get("grid_size_preserved"):
            return None

        for pair in task.example_pairs:
            g0, g1 = pair.input_grid, pair.output_grid
            if not g0 or not g1:
                return None
            raw_in = g0.raw
            raw_out = g1.raw
            h = len(raw_in)
            w = len(raw_in[0]) if raw_in else 0

            if h < 4 or w < 2:
                return None

            # Find background color (the color of the top-left cell)
            bg = raw_in[0][0]

            # Verify top rows are uniform bg
            first_non_bg_row = None
            for r in range(h):
                if any(raw_in[r][c] != bg for c in range(w)):
                    first_non_bg_row = r
                    break

            if first_non_bg_row is None or first_non_bg_row == 0:
                return None

            # Pattern is from first_non_bg_row to end
            pattern_rows = h - first_non_bg_row
            if pattern_rows < 2 or pattern_rows >= h:
                return None

            # Extract the pattern
            pattern = [raw_in[r][:] for r in range(first_non_bg_row, h)]

            # Verify output is the pattern tiled from bottom upward
            for r in range(h):
                # Map output row r to pattern row, tiling from bottom
                pattern_idx = (h - 1 - r) % pattern_rows
                # Since we tile from bottom, the bottom of output = bottom of pattern
                expected_row_idx = pattern_rows - 1 - pattern_idx
                if raw_out[r] != pattern[expected_row_idx]:
                    return None

        return {"type": "tile_pattern_upward", "confidence": 1.0}

    @staticmethod
    def _count_non_bg(raw):
        """Find background color (most frequent) and count non-bg colors."""
        from collections import Counter
        freq = Counter()
        for row in raw:
            for v in row:
                freq[v] += 1
        if not freq:
            return None, {}
        bg = freq.most_common(1)[0][0]
        counts = {c: n for c, n in freq.items() if c != bg}
        return bg, counts


    # ---- strategy: denoise rectangles (remove noise, keep rect cores) ------

    def _try_denoise_rectangles(self, patterns, wm):
        """
        Detect: grid has one fg color on bg 0. Connected components include
        solid rectangles + noise (isolated pixels or protrusions). Output
        removes noise and keeps only the largest inscribed rectangle per component.
        Category: noise removal / rectangle extraction.
        """
        task = wm.task
        if task is None:
            return None
        if not patterns.get("grid_size_preserved"):
            return None

        for pair in task.example_pairs:
            raw_in = pair.input_grid.raw
            raw_out = pair.output_grid.raw
            h = len(raw_in)
            w = len(raw_in[0]) if raw_in else 0

            if len(raw_out) != h or (raw_out and len(raw_out[0]) != w):
                return None

            # Find non-zero colors in input
            fg_colors = set()
            for r in range(h):
                for c in range(w):
                    if raw_in[r][c] != 0:
                        fg_colors.add(raw_in[r][c])

            # Must have exactly one foreground color
            if len(fg_colors) != 1:
                return None
            fg = next(iter(fg_colors))

            # Output must only contain fg and 0
            for r in range(h):
                for c in range(w):
                    if raw_out[r][c] != 0 and raw_out[r][c] != fg:
                        return None

            # Find connected components of fg in input
            fg_cells = [(r, c) for r in range(h) for c in range(w)
                        if raw_in[r][c] == fg]
            components = self._cc_group(fg_cells)

            # For each component, find largest inscribed rectangle
            expected = [[0] * w for _ in range(h)]
            for comp in components:
                rect_cells = self._largest_inscribed_rect(comp)
                for r, c in rect_cells:
                    expected[r][c] = fg

            if expected != raw_out:
                return None

        return {"type": "denoise_rectangles", "confidence": 1.0}

    # ---- strategy: color substitution template ----------------------------

    def _try_color_substitution_template(self, patterns, wm):
        """
        Detect: input has a bordered rectangular template on bg 0 plus
        scattered 2-cell pairs. Each pair maps one template interior color
        to a new color. Output = extracted template with substitutions.
        Category: color substitution / palette swap with lookup table.
        """
        task = wm.task
        if task is None:
            return None

        # Output must be smaller than input (extracted template)
        if patterns.get("grid_size_preserved"):
            return None

        for pair in task.example_pairs:
            raw_in = pair.input_grid.raw
            raw_out = pair.output_grid.raw

            result = self._analyze_color_sub_template(raw_in)
            if result is None:
                return None

            template_block, border_color, color_map = result

            # Build expected output
            expected = []
            for row in template_block:
                out_row = []
                for c in row:
                    if c == border_color:
                        out_row.append(c)
                    else:
                        out_row.append(color_map.get(c, c))
                expected.append(out_row)

            if expected != raw_out:
                return None

        return {"type": "color_substitution_template", "confidence": 1.0}

    @staticmethod
    def _analyze_color_sub_template(raw):
        """Find the template rectangle, border color, and color mapping."""
        h = len(raw)
        w = len(raw[0]) if raw else 0

        # Find all non-zero cells and group into connected components
        non_zero = [(r, c) for r in range(h) for c in range(w) if raw[r][c] != 0]
        if not non_zero:
            return None

        pos_set = set(non_zero)
        visited = set()
        components = []
        for pos in non_zero:
            if pos in visited:
                continue
            comp = []
            queue = [pos]
            while queue:
                p = queue.pop(0)
                if p in visited or p not in pos_set:
                    continue
                visited.add(p)
                comp.append(p)
                r, c = p
                for dr, dc in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                    nb = (r + dr, c + dc)
                    if nb in pos_set and nb not in visited:
                        queue.append(nb)
            components.append(comp)

        if len(components) < 2:
            return None

        # Largest component is the template
        components.sort(key=len, reverse=True)
        template_comp = components[0]
        pair_comps = components[1:]

        if len(template_comp) < 6:
            return None

        # All non-template components must have exactly 2 cells
        for pc in pair_comps:
            if len(pc) != 2:
                return None

        # Extract template bounding box
        min_r = min(r for r, c in template_comp)
        max_r = max(r for r, c in template_comp)
        min_c = min(c for r, c in template_comp)
        max_c = max(c for r, c in template_comp)

        # Template must fill its bounding box completely
        template_set = set(template_comp)
        for r in range(min_r, max_r + 1):
            for c in range(min_c, max_c + 1):
                if (r, c) not in template_set:
                    return None

        # Extract template block
        template_block = [
            [raw[r][c] for c in range(min_c, max_c + 1)]
            for r in range(min_r, max_r + 1)
        ]

        # Border color = color at all 4 corners
        corners = [
            template_block[0][0],
            template_block[0][-1],
            template_block[-1][0],
            template_block[-1][-1],
        ]
        if len(set(corners)) != 1:
            return None
        border_color = corners[0]

        # Interior colors (non-border within template)
        interior_colors = set()
        for row in template_block:
            for c in row:
                if c != border_color:
                    interior_colors.add(c)

        # Build color mapping from pairs
        color_map = {}
        for pc in pair_comps:
            c1 = raw[pc[0][0]][pc[0][1]]
            c2 = raw[pc[1][0]][pc[1][1]]

            if c1 in interior_colors and c2 not in interior_colors:
                color_map[c1] = c2
            elif c2 in interior_colors and c1 not in interior_colors:
                color_map[c2] = c1
            else:
                return None

        return template_block, border_color, color_map

    # ---- strategy: cross marker duplicate detection -----------------------

    def _try_cross_marker_duplicate(self, patterns, wm):
        """
        Detect: grid has background + cross patterns (center_color=4 with
        same arm color X on all 4 orthogonal neighbors). One arm color X
        appears in exactly 2 crosses. Output = 1×1 grid with that color.
        Category: pattern counting / duplicate detection.
        """
        task = wm.task
        if task is None:
            return None

        for pair in task.example_pairs:
            raw_in = pair.input_grid.raw
            raw_out = pair.output_grid.raw
            h_out = len(raw_out)
            w_out = len(raw_out[0]) if raw_out else 0

            # Output must be 1×1
            if h_out != 1 or w_out != 1:
                return None

            expected_color = raw_out[0][0]

            # Find cross patterns
            crosses = self._find_cross_patterns(raw_in, 4)
            if len(crosses) < 2:
                return None

            # Count arm colors
            from collections import Counter
            arm_counts = Counter(crosses.values())

            # Find the arm color appearing exactly 2+ times
            dup_color = None
            for color, count in arm_counts.items():
                if count >= 2:
                    if dup_color is not None:
                        return None  # Multiple duplicates
                    dup_color = color

            if dup_color is None or dup_color != expected_color:
                return None

        return {"type": "cross_marker_duplicate", "center_color": 4,
                "confidence": 1.0}

    @staticmethod
    def _find_cross_patterns(raw, center_color):
        """Find cross patterns: center_color at center, same color on 4 arms.
        Returns dict: (row, col) -> arm_color."""
        h = len(raw)
        w = len(raw[0]) if raw else 0
        crosses = {}

        for r in range(1, h - 1):
            for c in range(1, w - 1):
                if raw[r][c] != center_color:
                    continue
                up = raw[r - 1][c]
                down = raw[r + 1][c]
                left = raw[r][c - 1]
                right = raw[r][c + 1]
                if up == down == left == right and up != center_color:
                    crosses[(r, c)] = up

        return crosses

    # ---- strategy: border flood fill (interior/exterior classification) ----

    def _try_border_flood_fill(self, patterns, wm):
        """
        Detect: grid has a 'source' color replaced by two new colors:
        source cells reachable from grid border via source-color path → border_color,
        source cells NOT reachable from border → interior_color.
        Category: flood fill / inside-outside classification.
        """
        task = wm.task
        if task is None:
            return None

        source_color = None
        border_color = None
        interior_color = None

        for pair in task.example_pairs:
            raw_in = pair.input_grid.raw
            raw_out = pair.output_grid.raw
            h = len(raw_in)
            w = len(raw_in[0]) if raw_in else 0

            if len(raw_out) != h or (raw_out and len(raw_out[0]) != w):
                return None

            in_colors = set()
            out_colors = set()
            for r in range(h):
                for c in range(w):
                    in_colors.add(raw_in[r][c])
                    out_colors.add(raw_out[r][c])

            source_cands = in_colors - out_colors
            new_cands = out_colors - in_colors
            if len(source_cands) != 1 or len(new_cands) != 2:
                return None

            sc = source_cands.pop()
            new_list = sorted(new_cands)

            reachable = self._bfs_border(raw_in, sc, h, w)

            matched = False
            for bc, ic in [(new_list[0], new_list[1]), (new_list[1], new_list[0])]:
                expected = [row[:] for row in raw_in]
                for r in range(h):
                    for c in range(w):
                        if raw_in[r][c] == sc:
                            expected[r][c] = bc if reachable[r][c] else ic
                if expected == raw_out:
                    if source_color is None:
                        source_color, border_color, interior_color = sc, bc, ic
                    elif sc != source_color or bc != border_color or ic != interior_color:
                        return None
                    matched = True
                    break
            if not matched:
                return None

        return {"type": "border_flood_fill", "source_color": source_color,
                "border_color": border_color, "interior_color": interior_color,
                "confidence": 1.0}

    @staticmethod
    def _bfs_border(raw, source, h, w):
        """BFS from border cells of source color. Returns reachable grid."""
        reachable = [[False] * w for _ in range(h)]
        queue = []
        for r in range(h):
            for c in range(w):
                if (r == 0 or r == h - 1 or c == 0 or c == w - 1) and raw[r][c] == source:
                    reachable[r][c] = True
                    queue.append((r, c))
        qi = 0
        while qi < len(queue):
            r, c = queue[qi]
            qi += 1
            for dr, dc in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                nr, nc = r + dr, c + dc
                if 0 <= nr < h and 0 <= nc < w and not reachable[nr][nc] and raw[nr][nc] == source:
                    reachable[nr][nc] = True
                    queue.append((nr, nc))
        return reachable

    # ---- strategy: corner mark square (project marks from square shapes) ----

    def _try_corner_mark_square(self, patterns, wm):
        """
        Detect: bg grid with rectangular shapes (frames or solid blocks).
        Square shapes (W=H, side >= 2) get mark-color cells at each corner's
        outward-projecting neighbors (1 cell out perpendicular to each edge).
        Category: shape detection / corner marking.
        """
        task = wm.task
        if task is None:
            return None

        mark_color = None

        for pair in task.example_pairs:
            raw_in = pair.input_grid.raw
            raw_out = pair.output_grid.raw
            h = len(raw_in)
            w = len(raw_in[0]) if raw_in else 0

            if len(raw_out) != h or (raw_out and len(raw_out[0]) != w):
                return None

            from collections import Counter
            counts = Counter()
            for r in range(h):
                for c in range(w):
                    counts[raw_in[r][c]] += 1
            bg = counts.most_common(1)[0][0]

            in_colors = set(raw_in[r][c] for r in range(h) for c in range(w))
            out_colors = set(raw_out[r][c] for r in range(h) for c in range(w))
            new_colors = out_colors - in_colors
            if len(new_colors) != 1:
                return None
            mc = new_colors.pop()

            if mark_color is None:
                mark_color = mc
            elif mc != mark_color:
                return None

            expected = self._build_corner_marks(raw_in, bg, mc, h, w)
            if expected != raw_out:
                return None

        return {"type": "corner_mark_square", "mark_color": mark_color,
                "confidence": 1.0}

    def _build_corner_marks(self, raw, bg, mc, h, w):
        """Build output by marking corners of square components."""
        non_bg = [(r, c) for r in range(h) for c in range(w) if raw[r][c] != bg]
        groups = self._cc_group(non_bg)

        out = [row[:] for row in raw]
        for group in groups:
            if len(group) < 4:
                continue
            group_set = set(group)
            rows_g = [r for r, c in group]
            cols_g = [c for r, c in group]
            r1, r2 = min(rows_g), max(rows_g)
            c1, c2 = min(cols_g), max(cols_g)
            bh = r2 - r1 + 1
            bw = c2 - c1 + 1
            if bh != bw or bh < 2:
                continue
            if not all((r, c) in group_set
                       for r, c in [(r1, c1), (r1, c2), (r2, c1), (r2, c2)]):
                continue
            for cr, cc in [(r1, c1), (r1, c2), (r2, c1), (r2, c2)]:
                dr = -1 if cr == r1 else 1
                dc = -1 if cc == c1 else 1
                nr = cr + dr
                if 0 <= nr < h:
                    out[nr][cc] = mc
                nc = cc + dc
                if 0 <= nc < w:
                    out[cr][nc] = mc
        return out

    # ---- strategy: cross center mark (4 equidistant domino pairs) ----------

    def _try_cross_center_mark(self, patterns, wm):
        """
        Detect: grid has bg + fg domino pairs (2-cell segments). When 4 pairs
        form a symmetric cross (1 gap cell + 2 pair cells in each of 4
        directions from a center), the center cell becomes mark color.
        Category: spatial symmetry / cross pattern detection.
        """
        task = wm.task
        if task is None:
            return None

        bg = None
        fg = None
        mark = None

        for pair in task.example_pairs:
            raw_in = pair.input_grid.raw
            raw_out = pair.output_grid.raw
            h = len(raw_in)
            w = len(raw_in[0]) if raw_in else 0

            if len(raw_out) != h or (raw_out and len(raw_out[0]) != w):
                return None

            in_colors = set()
            out_colors = set()
            for r in range(h):
                for c in range(w):
                    in_colors.add(raw_in[r][c])
                    out_colors.add(raw_out[r][c])
            if len(in_colors) != 2:
                return None
            new_colors = out_colors - in_colors
            if len(new_colors) != 1:
                return None

            mk = new_colors.pop()

            from collections import Counter
            cc = Counter()
            for r in range(h):
                for c in range(w):
                    cc[raw_in[r][c]] += 1
            sorted_c = cc.most_common()
            bg_c, fg_c = sorted_c[0][0], sorted_c[1][0]

            if bg is None:
                bg, fg, mark = bg_c, fg_c, mk
            elif bg_c != bg or fg_c != fg or mk != mark:
                return None

            centers = self._find_domino_cross_centers(raw_in, bg, fg, h, w)
            if not centers:
                return None

            expected = [row[:] for row in raw_in]
            for r, c in centers:
                expected[r][c] = mark

            if expected != raw_out:
                return None

        return {"type": "cross_center_mark", "bg": bg, "fg": fg, "mark": mark,
                "confidence": 1.0}

    @staticmethod
    def _find_domino_cross_centers(raw, bg, fg, h, w):
        """Find cells that are centers of 4-directional domino cross patterns.
        Pattern per arm: center(bg) - gap(bg) - near(fg) - far(fg)."""
        centers = []
        for r in range(h):
            for c in range(w):
                if raw[r][c] != bg:
                    continue
                valid = True
                for dr, dc in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                    gr, gc = r + dr, c + dc
                    if not (0 <= gr < h and 0 <= gc < w) or raw[gr][gc] != bg:
                        valid = False
                        break
                    nr, nc = r + 2 * dr, c + 2 * dc
                    if not (0 <= nr < h and 0 <= nc < w) or raw[nr][nc] != fg:
                        valid = False
                        break
                    fr, fc = r + 3 * dr, c + 3 * dc
                    if not (0 <= fr < h and 0 <= fc < w) or raw[fr][fc] != fg:
                        valid = False
                        break
                if valid:
                    centers.append((r, c))
        return centers

    # ---- shared helpers for generalize ------------------------------------

    @staticmethod
    def _cc_group(positions):
        """Group (row, col) into 4-connected components."""
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

    @staticmethod
    def _largest_inscribed_rect(cells):
        """Find the largest filled rectangle inscribed in a set of cells.
        Returns set of (row, col) in that rectangle, or empty set if < 2 cells."""
        if not cells:
            return set()
        cell_set = set(cells)
        if len(cell_set) <= 1:
            return set()

        rows = sorted(set(r for r, c in cells))
        cols = sorted(set(c for r, c in cells))
        min_r, max_r = rows[0], rows[-1]
        min_c, max_c = cols[0], cols[-1]

        best_area = 0
        best_rect = None

        for r1 in range(min_r, max_r + 1):
            for r2 in range(max_r, r1 - 1, -1):
                max_possible = (r2 - r1 + 1) * (max_c - min_c + 1)
                if max_possible <= best_area:
                    break
                for c1 in range(min_c, max_c + 1):
                    for c2 in range(max_c, c1 - 1, -1):
                        area = (r2 - r1 + 1) * (c2 - c1 + 1)
                        if area <= best_area:
                            break
                        if all(
                            (r, c) in cell_set
                            for r in range(r1, r2 + 1)
                            for c in range(c1, c2 + 1)
                        ):
                            best_area = area
                            best_rect = (r1, r2, c1, c2)

        if best_rect is None:
            return set()

        r1, r2, c1, c2 = best_rect
        return {(r, c) for r in range(r1, r2 + 1) for c in range(c1, c2 + 1)}


    # ---- strategy: separator histogram -------------------------------------

    def _try_separator_histogram(self, patterns, wm):
        """
        Detect pattern: grid divided by 2 horizontal + 2 vertical colored
        separator lines.  Center section has scattered dots whose color
        matches one separator.  Output = framed center with histogram bars
        extending from the matching separator.

        Category: grids with colored separator lines and scattered marker
        dots that collapse into a bar-chart / histogram.
        """
        task = wm.task
        if not task or len(task.example_pairs) < 1:
            return None

        for pair in task.example_pairs:
            g0, g1 = pair.input_grid, pair.output_grid
            if not g0 or not g1:
                return None
            raw_in = g0.raw
            raw_out = g1.raw

            params = self._sep_hist_detect(raw_in)
            if params is None:
                return None

            predicted = self._sep_hist_build(raw_in, params)
            if predicted is None:
                return None

            if len(predicted) != len(raw_out):
                return None
            for r in range(len(predicted)):
                if len(predicted[r]) != len(raw_out[r]):
                    return None
                for c in range(len(predicted[r])):
                    if predicted[r][c] != raw_out[r][c]:
                        return None

        return {"type": "separator_histogram", "confidence": 1.0}

    @staticmethod
    def _sep_hist_detect(grid):
        """Detect separator lines and marker colour in *grid*."""
        H = len(grid)
        W = len(grid[0]) if grid else 0
        if H < 5 or W < 5:
            return None

        # Find horizontal separator rows
        sep_rows = []
        for r in range(H):
            counts = {}
            for c in range(W):
                v = grid[r][c]
                if v != 0:
                    counts[v] = counts.get(v, 0) + 1
            if not counts:
                continue
            dom = max(counts, key=counts.get)
            if counts[dom] >= W * 0.7:
                sep_rows.append((r, dom))

        # Find vertical separator columns
        sep_cols = []
        for c in range(W):
            counts = {}
            for r in range(H):
                v = grid[r][c]
                if v != 0:
                    counts[v] = counts.get(v, 0) + 1
            if not counts:
                continue
            dom = max(counts, key=counts.get)
            if counts[dom] >= H * 0.7:
                sep_cols.append((c, dom))

        if len(sep_rows) != 2 or len(sep_cols) != 2:
            return None

        sep_rows.sort()
        sep_cols.sort()

        hr1, hc1 = sep_rows[0]
        hr2, hc2 = sep_rows[1]
        vc1, vcc1 = sep_cols[0]
        vc2, vcc2 = sep_cols[1]

        r_start, r_end = hr1 + 1, hr2 - 1
        c_start, c_end = vc1 + 1, vc2 - 1
        if r_start > r_end or c_start > c_end:
            return None

        # Find marker colour in center section
        marker_counts = {}
        for r in range(r_start, r_end + 1):
            for c in range(c_start, c_end + 1):
                v = grid[r][c]
                if v != 0:
                    marker_counts[v] = marker_counts.get(v, 0) + 1

        if not marker_counts:
            return None

        marker_color = max(marker_counts, key=marker_counts.get)

        sep_map = {hc1: 'top', hc2: 'bottom', vcc1: 'left', vcc2: 'right'}
        if marker_color not in sep_map:
            return None

        return {
            'sep_rows': [(hr1, hc1), (hr2, hc2)],
            'sep_cols': [(vc1, vcc1), (vc2, vcc2)],
            'center': (r_start, r_end, c_start, c_end),
            'marker_color': marker_color,
            'fill_direction': sep_map[marker_color],
        }

    @staticmethod
    def _sep_hist_build(grid, params):
        """Build the histogram output grid from detected parameters."""
        (hr1, hc1), (hr2, hc2) = params['sep_rows']
        (vc1, vcc1), (vc2, vcc2) = params['sep_cols']
        r_start, r_end, c_start, c_end = params['center']
        marker = params['marker_color']
        fill = params['fill_direction']

        center_h = r_end - r_start + 1
        center_w = c_end - c_start + 1
        out_h = center_h + 2
        out_w = center_w + 2

        out = [[0] * out_w for _ in range(out_h)]

        # Separator borders
        for c in range(out_w):
            out[0][c] = hc1
            out[out_h - 1][c] = hc2
        for r in range(out_h):
            out[r][0] = vcc1
            out[r][out_w - 1] = vcc2

        # Corners from input crossing points
        out[0][0] = grid[hr1][vc1]
        out[0][out_w - 1] = grid[hr1][vc2]
        out[out_h - 1][0] = grid[hr2][vc1]
        out[out_h - 1][out_w - 1] = grid[hr2][vc2]

        # Build histogram bars
        if fill == 'bottom':
            for ci in range(center_w):
                topmost = None
                for ri in range(r_start, r_end + 1):
                    if grid[ri][c_start + ci] == marker:
                        topmost = ri
                        break
                if topmost is not None:
                    for ri in range(topmost, r_end + 1):
                        out[1 + ri - r_start][1 + ci] = marker
        elif fill == 'top':
            for ci in range(center_w):
                bottommost = None
                for ri in range(r_end, r_start - 1, -1):
                    if grid[ri][c_start + ci] == marker:
                        bottommost = ri
                        break
                if bottommost is not None:
                    for ri in range(r_start, bottommost + 1):
                        out[1 + ri - r_start][1 + ci] = marker
        elif fill == 'right':
            for ri in range(center_h):
                leftmost = None
                for ci in range(c_start, c_end + 1):
                    if grid[r_start + ri][ci] == marker:
                        leftmost = ci
                        break
                if leftmost is not None:
                    for ci in range(leftmost, c_end + 1):
                        out[1 + ri][1 + ci - c_start] = marker
        elif fill == 'left':
            for ri in range(center_h):
                rightmost = None
                for ci in range(c_end, c_start - 1, -1):
                    if grid[r_start + ri][ci] == marker:
                        rightmost = ci
                        break
                if rightmost is not None:
                    for ci in range(c_start, rightmost + 1):
                        out[1 + ri][1 + ci - c_start] = marker

        return out

    # ---- strategy: rotation quadrant tile 4×4 ------------------------------

    def _try_rotation_quadrant_tile_4x4(self, patterns, wm):
        """
        Detect pattern: input is NxN, output is 4Nx4N.  The output is a
        4×4 arrangement of NxN blocks where each 2×2 quadrant shares one
        rotation:
            TL = 180°   TR = 90° CW
            BL = 90° CCW BR = original

        Category: small tiles expanded into 4-fold rotation-symmetry
        mosaics.
        """
        task = wm.task
        if not task or len(task.example_pairs) < 1:
            return None

        for pair in task.example_pairs:
            g0, g1 = pair.input_grid, pair.output_grid
            if not g0 or not g1:
                return None
            raw_in = g0.raw
            raw_out = g1.raw
            n = len(raw_in)
            w = len(raw_in[0]) if raw_in else 0
            if n == 0 or n != w:
                return None
            if len(raw_out) != 4 * n or len(raw_out[0]) != 4 * n:
                return None

            orig = [row[:] for row in raw_in]
            rot180 = self._rotate_180(orig)
            cw90 = self._rotate_cw90(orig)
            ccw90 = self._rotate_ccw90(orig)

            layout = [
                [rot180, rot180, cw90, cw90],
                [rot180, rot180, cw90, cw90],
                [ccw90, ccw90, orig, orig],
                [ccw90, ccw90, orig, orig],
            ]

            for br in range(4):
                for bc in range(4):
                    if not self._check_quadrant(raw_out, br * n, bc * n,
                                                layout[br][bc]):
                        return None

        return {"type": "rotation_quadrant_tile_4x4", "confidence": 1.0}

    # ---- strategy: self-tiling (NxN input as its own tile template) ------

    def _try_self_tiling(self, patterns, wm):
        """
        Detect: NxN input → N²xN² output. Each cell in the input maps to an
        NxN block: if the cell is non-zero, the block is a copy of the input;
        if zero, the block is all zeros. The input acts as its own template.
        Category: fractal/self-referential zoom patterns.
        """
        pair_analyses = patterns.get("pair_analyses", [])
        if not pair_analyses:
            return None

        task = wm.task
        if task is None:
            return None

        for idx, pair in enumerate(task.example_pairs):
            ig = pair.input_grid
            og = pair.output_grid
            if ig is None or og is None:
                return None
            raw_in = ig.raw
            raw_out = og.raw
            H_in = len(raw_in)
            W_in = len(raw_in[0]) if raw_in else 0
            H_out = len(raw_out)
            W_out = len(raw_out[0]) if raw_out else 0

            # Must be NxN input and N²xN² output
            if H_in != W_in or H_in == 0:
                return None
            n = H_in
            if H_out != n * n or W_out != n * n:
                return None

            # Verify each block
            for br in range(n):
                for bc in range(n):
                    cell_val = raw_in[br][bc]
                    for dr in range(n):
                        for dc in range(n):
                            out_val = raw_out[br * n + dr][bc * n + dc]
                            if cell_val != 0:
                                if out_val != raw_in[dr][dc]:
                                    return None
                            else:
                                if out_val != 0:
                                    return None

        return {"type": "self_tiling", "confidence": 1.0}

    # ---- strategy: double mirror / kaleidoscope --------------------------

    def _try_double_mirror(self, patterns, wm):
        """
        Detect: NxM input → 2Nx2M output by mirroring horizontally then vertically.
        Output = [[row + reversed(row)] for each row] + reversed version of that.
        Category: reflection/symmetry expansion patterns.
        """
        pair_analyses = patterns.get("pair_analyses", [])
        if not pair_analyses:
            return None

        task = wm.task
        if task is None:
            return None

        for idx, pair in enumerate(task.example_pairs):
            ig = pair.input_grid
            og = pair.output_grid
            if ig is None or og is None:
                return None
            raw_in = ig.raw
            raw_out = og.raw
            H_in = len(raw_in)
            W_in = len(raw_in[0]) if raw_in else 0
            H_out = len(raw_out)
            W_out = len(raw_out[0]) if raw_out else 0

            if H_out != 2 * H_in or W_out != 2 * W_in:
                return None

            # Build expected output
            top_half = []
            for r in range(H_in):
                row = raw_in[r]
                mirrored_row = list(row) + list(reversed(row))
                top_half.append(mirrored_row)

            expected = top_half + list(reversed(top_half))

            for r in range(H_out):
                for c in range(W_out):
                    if raw_out[r][c] != expected[r][c]:
                        return None

        return {"type": "double_mirror", "confidence": 1.0}

    # ---- strategy: XOR comparison (two halves, separator row) -----------

    def _try_xor_comparison(self, patterns, wm):
        """
        Detect: input has two sub-grids separated by a row of uniform color.
        Top uses color A on bg 0, bottom uses color B on bg 0.
        Output = same dimensions as one half; cells are color 3 where exactly
        one half has a non-zero cell (XOR), 0 otherwise.
        Category: set operation / comparison patterns (XOR, AND, OR).
        """
        pair_analyses = patterns.get("pair_analyses", [])
        if not pair_analyses:
            return None

        task = wm.task
        if task is None:
            return None

        # Detect consistent separator and XOR pattern across all pairs
        sep_color = None
        out_color = None

        for idx, pair in enumerate(task.example_pairs):
            ig = pair.input_grid
            og = pair.output_grid
            if ig is None or og is None:
                return None
            raw_in = ig.raw
            raw_out = og.raw
            H = len(raw_in)
            W = len(raw_in[0]) if raw_in else 0

            # Find separator row: a row where all cells are the same non-zero color
            sep_row = None
            sc = None
            for r in range(H):
                row = raw_in[r]
                if len(set(row)) == 1 and row[0] != 0:
                    sep_row = r
                    sc = row[0]
                    break

            if sep_row is None:
                return None

            if sep_color is None:
                sep_color = sc
            elif sep_color != sc:
                return None

            top_h = sep_row
            bot_h = H - sep_row - 1
            if top_h != bot_h and top_h != len(raw_out) and bot_h != len(raw_out):
                return None

            # Determine which half matches output dimensions
            out_h = len(raw_out)
            out_w = len(raw_out[0]) if raw_out else 0
            if out_w != W:
                return None

            if top_h == out_h:
                top = [raw_in[r] for r in range(top_h)]
                bot = [raw_in[r] for r in range(sep_row + 1, sep_row + 1 + top_h)]
            elif bot_h == out_h:
                top = [raw_in[r] for r in range(bot_h)]
                bot = [raw_in[r] for r in range(sep_row + 1, sep_row + 1 + bot_h)]
            else:
                return None

            half_h = out_h

            # Verify XOR: output cell = X where exactly one of top/bot is non-zero
            for r in range(half_h):
                for c in range(W):
                    t = top[r][c] != 0
                    b = bot[r][c] != 0
                    o = raw_out[r][c]
                    if t != b:  # XOR = True
                        if o == 0:
                            return None
                        if out_color is None:
                            out_color = o
                        elif o != out_color:
                            return None
                    else:  # XOR = False
                        if o != 0:
                            return None

        if out_color is None:
            return None

        return {
            "type": "xor_comparison",
            "confidence": 1.0,
            "sep_color": sep_color,
            "out_color": out_color,
        }

    # ---- strategy: half-grid boolean (OR/AND/NOR/NAND) -------------------

    def _try_half_grid_boolean(self, patterns, wm):
        """
        Detect: input is split into two halves (horizontal separator, vertical
        separator, or simple width/height bisection).  A consistent boolean
        operation (OR, AND, NOR, NAND) maps the two halves to the output.
        Output uses a single result color on a 0 background.
        Category: set operation / comparison patterns.
        """
        task = wm.task
        if task is None:
            return None
        pair_analyses = patterns.get("pair_analyses", [])
        if not pair_analyses:
            return None

        for split_mode in ["h_separator", "v_separator", "v_half", "h_half"]:
            result = self._check_boolean_split(task, split_mode)
            if result is not None:
                return result
        return None

    def _check_boolean_split(self, task, split_mode):
        """Check if *split_mode* yields a consistent boolean op across pairs."""
        candidates = None
        sep_color = None

        for pair in task.example_pairs:
            ig, og = pair.input_grid, pair.output_grid
            if ig is None or og is None:
                return None
            raw_in, raw_out = ig.raw, og.raw
            H = len(raw_in)
            W = len(raw_in[0]) if raw_in else 0
            oH = len(raw_out)
            oW = len(raw_out[0]) if raw_out else 0

            half_a = half_b = None

            if split_mode == "h_separator":
                sep_row = sc = None
                for r in range(1, H - 1):
                    row = raw_in[r]
                    if len(set(row)) == 1 and row[0] != 0:
                        th = r
                        bh = H - r - 1
                        # Accept only if it divides into equal halves matching output
                        if th == bh and oH == th and oW == W:
                            if sep_color is None or sep_color == row[0]:
                                sep_row, sc = r, row[0]
                                break
                if sep_row is None:
                    return None
                if sep_color is None:
                    sep_color = sc
                top_h = sep_row
                bot_start = sep_row + 1
                half_a = [raw_in[r] for r in range(top_h)]
                half_b = [raw_in[r] for r in range(bot_start, bot_start + top_h)]

            elif split_mode == "v_separator":
                sep_col = sc = None
                for c in range(1, W - 1):
                    col_vals = [raw_in[r][c] for r in range(H)]
                    if len(set(col_vals)) == 1 and col_vals[0] != 0:
                        sep_col, sc = c, col_vals[0]
                        break
                if sep_col is None:
                    return None
                if sep_color is None:
                    sep_color = sc
                elif sep_color != sc:
                    return None
                left_w = sep_col
                right_start = sep_col + 1
                right_w = W - right_start
                if left_w != right_w or oH != H or oW != left_w:
                    return None
                half_a = [row[:left_w] for row in raw_in]
                half_b = [row[right_start:right_start + left_w] for row in raw_in]

            elif split_mode == "v_half":
                if W % 2 != 0:
                    return None
                hw = W // 2
                if oH != H or oW != hw:
                    return None
                half_a = [row[:hw] for row in raw_in]
                half_b = [row[hw:] for row in raw_in]

            elif split_mode == "h_half":
                if H % 2 != 0:
                    return None
                hh = H // 2
                if oH != hh or oW != W:
                    return None
                half_a = [raw_in[r] for r in range(hh)]
                half_b = [raw_in[r] for r in range(hh, H)]

            if half_a is None:
                return None

            pair_matches = []
            for op in ["or", "and", "nor", "nand"]:
                out_c = None
                ok = True
                for r in range(oH):
                    for c in range(oW):
                        a = half_a[r][c] != 0
                        b = half_b[r][c] != 0
                        if op == "or":
                            res = a or b
                        elif op == "and":
                            res = a and b
                        elif op == "nor":
                            res = not (a or b)
                        else:
                            res = not (a and b)
                        o = raw_out[r][c]
                        if res:
                            if o == 0:
                                ok = False
                                break
                            if out_c is None:
                                out_c = o
                            elif o != out_c:
                                ok = False
                                break
                        else:
                            if o != 0:
                                ok = False
                                break
                    if not ok:
                        break
                if ok and out_c is not None:
                    pair_matches.append((op, out_c))

            if not pair_matches:
                return None
            candidates = pair_matches if candidates is None else [
                c for c in candidates if c in pair_matches
            ]
            if not candidates:
                return None

        if not candidates:
            return None
        op, out_c = candidates[0]
        return {
            "type": "half_grid_boolean",
            "confidence": 1.0,
            "operation": op,
            "split_mode": split_mode,
            "sep_color": sep_color,
            "out_color": out_c,
        }

    # ---- strategy: inverse tile (invert then tile 2×2) -------------------

    def _try_inverse_tile(self, patterns, wm):
        """
        Detect: output is 2× input dimensions.  The output equals the colour-
        inverted input (0↔non-zero colour) tiled 2×2.
        Category: tiling with colour inversion.
        """
        task = wm.task
        if task is None:
            return None
        pair_analyses = patterns.get("pair_analyses", [])
        if not pair_analyses:
            return None

        for pair in task.example_pairs:
            ig, og = pair.input_grid, pair.output_grid
            if ig is None or og is None:
                return None
            raw_in, raw_out = ig.raw, og.raw
            H = len(raw_in)
            W = len(raw_in[0]) if raw_in else 0
            oH = len(raw_out)
            oW = len(raw_out[0]) if raw_out else 0
            if oH != 2 * H or oW != 2 * W:
                return None

            # Single non-zero colour in input
            colors = set()
            for row in raw_in:
                for v in row:
                    if v != 0:
                        colors.add(v)
            if len(colors) != 1:
                return None
            fg = colors.pop()

            inv = [[fg if v == 0 else 0 for v in row] for row in raw_in]
            for qr in range(2):
                for qc in range(2):
                    for r in range(H):
                        for c in range(W):
                            if raw_out[qr * H + r][qc * W + c] != inv[r][c]:
                                return None

        return {"type": "inverse_tile", "confidence": 1.0}

    # ---- strategy: grid separator max fill -------------------------------

    def _try_grid_separator_max_fill(self, patterns, wm):
        """
        Detect: input divided by separator rows/columns into a regular grid of
        cells.  Cells whose non-zero pixel count equals the maximum across all
        cells are filled entirely with their colour; others are cleared.
        Category: grid quantisation / max-fill.
        """
        task = wm.task
        if task is None:
            return None
        if not patterns.get("grid_size_preserved"):
            return None

        sep_color = None

        for pair in task.example_pairs:
            ig, og = pair.input_grid, pair.output_grid
            if ig is None or og is None:
                return None
            raw_in, raw_out = ig.raw, og.raw
            H = len(raw_in)
            W = len(raw_in[0]) if raw_in else 0
            if len(raw_out) != H or (raw_out and len(raw_out[0]) != W):
                return None

            # Detect separator colour from full rows
            sc = None
            sep_rows = []
            for r in range(H):
                vals = set(raw_in[r])
                if len(vals) == 1 and raw_in[r][0] != 0:
                    sep_rows.append(r)
                    if sc is None:
                        sc = raw_in[r][0]
                    elif raw_in[r][0] != sc:
                        return None

            sep_cols = []
            if sc is not None:
                for c in range(W):
                    col_vals = set(raw_in[r][c] for r in range(H))
                    if len(col_vals) == 1 and raw_in[0][c] == sc:
                        sep_cols.append(c)

            if sc is None or not sep_rows or not sep_cols:
                return None
            if sep_color is None:
                sep_color = sc
            elif sep_color != sc:
                return None

            # Cell bounds
            row_bounds = []
            prev = 0
            for sr in sorted(sep_rows):
                if sr > prev:
                    row_bounds.append((prev, sr))
                prev = sr + 1
            if prev < H:
                row_bounds.append((prev, H))

            col_bounds = []
            prev = 0
            for sci in sorted(sep_cols):
                if sci > prev:
                    col_bounds.append((prev, sci))
                prev = sci + 1
            if prev < W:
                col_bounds.append((prev, W))

            if not row_bounds or not col_bounds:
                return None

            # Count non-zero, non-separator pixels per cell
            cell_counts = []
            cell_colors = []
            for rb in row_bounds:
                rc, rclr = [], []
                for cb in col_bounds:
                    cnt = 0
                    cc = None
                    for r in range(rb[0], rb[1]):
                        for c in range(cb[0], cb[1]):
                            v = raw_in[r][c]
                            if v != 0 and v != sep_color:
                                cnt += 1
                                cc = v
                    rc.append(cnt)
                    rclr.append(cc)
                cell_counts.append(rc)
                cell_colors.append(rclr)

            max_cnt = max(max(row) for row in cell_counts)
            if max_cnt == 0:
                return None

            # Verify output matches expectation
            for ri, rb in enumerate(row_bounds):
                for ci, cb in enumerate(col_bounds):
                    is_max = cell_counts[ri][ci] == max_cnt
                    fill_c = cell_colors[ri][ci] if is_max else None
                    for r in range(rb[0], rb[1]):
                        for c in range(cb[0], cb[1]):
                            o = raw_out[r][c]
                            if is_max:
                                if o != fill_c:
                                    return None
                            else:
                                if o != 0:
                                    return None

            # Verify separators preserved
            for r in sep_rows:
                for c in range(W):
                    if raw_out[r][c] != sep_color:
                        return None
            for c in sep_cols:
                for r in range(H):
                    if raw_out[r][c] != sep_color:
                        return None

        return {
            "type": "grid_separator_max_fill",
            "confidence": 1.0,
            "sep_color": sep_color,
        }

    # ---- strategy 43: grid lines pattern ---------------------------------

    def _try_grid_lines_pattern(self, patterns, wm):
        """
        Detect: input is entirely one color (typically 0), output is same-size
        grid with a second color at cells where row%2==0 OR col%2==0.
        Category: uniform-input grid pattern generation.
        """
        task = wm.task
        if task is None:
            return None
        if not patterns.get("grid_size_preserved"):
            return None

        for pair in task.example_pairs:
            g0, g1 = pair.input_grid, pair.output_grid
            if g0 is None or g1 is None:
                return None
            raw_in, raw_out = g0.raw, g1.raw
            H, W = len(raw_in), len(raw_in[0])
            if H != len(raw_out) or W != len(raw_out[0]):
                return None

            # Input must be entirely one color
            bg = raw_in[0][0]
            if not all(raw_in[r][c] == bg for r in range(H) for c in range(W)):
                return None

            # Determine fill color from output
            fill_colors = set()
            for r in range(H):
                for c in range(W):
                    if raw_out[r][c] != bg:
                        fill_colors.add(raw_out[r][c])
            if len(fill_colors) != 1:
                return None
            fill_color = fill_colors.pop()

            # Verify pattern: fill where r%2==0 or c%2==0
            for r in range(H):
                for c in range(W):
                    on_grid = (r % 2 == 0) or (c % 2 == 0)
                    expected = fill_color if on_grid else bg
                    if raw_out[r][c] != expected:
                        return None

        return {
            "type": "grid_lines_pattern",
            "confidence": 1.0,
        }

    # ---- strategy 44: column shadow tile ---------------------------------

    def _try_column_shadow_tile(self, patterns, wm):
        """
        Detect: output is 2× input dims; zero cells in columns that contain
        any non-zero cell are replaced with shadow color (8), then the
        modified grid is tiled 2×2.
        Category: column-projection + tile expansion.
        """
        task = wm.task
        if task is None:
            return None
        if patterns.get("grid_size_preserved"):
            return None  # output must be different size

        for pair in task.example_pairs:
            g0, g1 = pair.input_grid, pair.output_grid
            if g0 is None or g1 is None:
                return None
            raw_in, raw_out = g0.raw, g1.raw
            H, W = len(raw_in), len(raw_in[0])
            oH, oW = len(raw_out), len(raw_out[0])
            if oH != 2 * H or oW != 2 * W:
                return None

            # Build shadow grid: replace 0s in non-zero columns with 8
            shadow = [row[:] for row in raw_in]
            for c in range(W):
                has_nonzero = any(raw_in[r][c] != 0 for r in range(H))
                if has_nonzero:
                    for r in range(H):
                        if shadow[r][c] == 0:
                            shadow[r][c] = 8

            # Verify 2×2 tiling
            for r in range(oH):
                for c in range(oW):
                    if raw_out[r][c] != shadow[r % H][c % W]:
                        return None

        return {
            "type": "column_shadow_tile",
            "confidence": 1.0,
        }

    # ---- strategy 45: concentric ring color rotate -----------------------

    def _try_concentric_ring_rotate(self, patterns, wm):
        """
        Detect: input has concentric rectangular rings of uniform color.
        Output rotates the ring color sequence by 1 position outward
        (innermost color becomes outermost).
        Category: concentric ring permutation.
        """
        task = wm.task
        if task is None:
            return None
        if not patterns.get("grid_size_preserved"):
            return None

        for pair in task.example_pairs:
            g0, g1 = pair.input_grid, pair.output_grid
            if g0 is None or g1 is None:
                return None
            raw_in, raw_out = g0.raw, g1.raw
            H, W = len(raw_in), len(raw_in[0])
            if H != len(raw_out) or W != len(raw_out[0]):
                return None
            if H < 2 or W < 2:
                return None

            # Extract ring colors (outer to inner)
            ring_colors = self._extract_ring_colors(raw_in, H, W)
            if ring_colors is None or len(ring_colors) < 2:
                return None

            # Build color mapping: rotate unique colors right by 1
            unique_ordered = []
            seen = set()
            for c in ring_colors:
                if c not in seen:
                    unique_ordered.append(c)
                    seen.add(c)
            if len(unique_ordered) < 2:
                return None

            # Right rotate: [a, b, c] → [c, a, b]
            rotated = [unique_ordered[-1]] + unique_ordered[:-1]
            color_map = {}
            for i, old_c in enumerate(unique_ordered):
                color_map[old_c] = rotated[i]

            # Verify output matches the color mapping
            for r in range(H):
                for c in range(W):
                    expected = color_map.get(raw_in[r][c], raw_in[r][c])
                    if raw_out[r][c] != expected:
                        return None

        return {
            "type": "concentric_ring_rotate",
            "confidence": 1.0,
        }

    def _extract_ring_colors(self, raw, H, W):
        """Extract colors of concentric rectangular rings, outer to inner."""
        ring_colors = []
        max_rings = min(H, W) // 2 + (1 if min(H, W) % 2 else 0)
        for ring in range(max_rings):
            r0, c0 = ring, ring
            r1, c1 = H - 1 - ring, W - 1 - ring
            if r0 > r1 or c0 > c1:
                break
            # All cells on this ring should be the same color
            color = raw[r0][c0]
            for r in range(r0, r1 + 1):
                for c in range(c0, c1 + 1):
                    if r == r0 or r == r1 or c == c0 or c == c1:
                        if raw[r][c] != color:
                            return None
            ring_colors.append(color)
        return ring_colors if ring_colors else None


    # ---- strategy: wedge expansion ----------------------------------------

    def _try_wedge_expansion(self, patterns, wm):
        """
        Detect: input has a single horizontal line of color K (e.g. 2)
        starting from col 0. Output expands upward with color 3 (each row
        adds +1 cell) and contracts downward with color 1 (each row removes
        -1 cell).
        Category: triangular/wedge expansion from a seed line.
        """
        task = wm.task
        if task is None:
            return None

        for pair in task.example_pairs:
            g0, g1 = pair.input_grid, pair.output_grid
            if g0 is None or g1 is None:
                return None
            raw_in, raw_out = g0.raw, g1.raw
            H, W = len(raw_in), len(raw_in[0])
            oH, oW = len(raw_out), len(raw_out[0])
            if H != oH or W != oW:
                return None

            # Find the seed row: exactly one row with non-zero cells,
            # all the same color, starting from column 0, contiguous
            seed_row = None
            seed_color = None
            seed_len = None
            for r in range(H):
                nz = [(c, raw_in[r][c]) for c in range(W) if raw_in[r][c] != 0]
                if nz:
                    if seed_row is not None:
                        return None  # multiple non-zero rows
                    # Check contiguous from col 0, same color
                    cols = [c for c, v in nz]
                    colors = set(v for c, v in nz)
                    if len(colors) != 1:
                        return None
                    if cols != list(range(len(cols))):
                        return None
                    seed_row = r
                    seed_color = nz[0][1]
                    seed_len = len(cols)

            if seed_row is None or seed_len is None:
                return None

            # Verify output pattern:
            # Above seed: row (seed_row - d) has (seed_len + d) cells of up_color
            # Below seed: row (seed_row + d) has (seed_len - d) cells of down_color
            # Seed row itself: same as input
            up_color = None
            down_color = None

            for r in range(H):
                if r == seed_row:
                    # Should match input
                    for c in range(W):
                        if raw_out[r][c] != raw_in[r][c]:
                            return None
                    continue

                d_up = seed_row - r  # positive if above seed
                d_down = r - seed_row  # positive if below seed

                if d_up > 0:
                    expected_len = seed_len + d_up
                    if expected_len > W:
                        expected_len = W
                    # Check row has expected_len cells of some color from col 0
                    nz = [(c, raw_out[r][c]) for c in range(W) if raw_out[r][c] != 0]
                    if not nz and expected_len <= 0:
                        continue
                    if len(nz) != expected_len:
                        return None
                    row_color = nz[0][1]
                    if row_color == seed_color:
                        return None
                    if up_color is None:
                        up_color = row_color
                    elif row_color != up_color:
                        return None
                    cols = [c for c, v in nz]
                    if cols != list(range(expected_len)):
                        return None

                elif d_down > 0:
                    expected_len = seed_len - d_down
                    if expected_len <= 0:
                        # Row should be all zeros
                        if any(raw_out[r][c] != 0 for c in range(W)):
                            return None
                        continue
                    nz = [(c, raw_out[r][c]) for c in range(W) if raw_out[r][c] != 0]
                    if len(nz) != expected_len:
                        return None
                    row_color = nz[0][1]
                    if row_color == seed_color:
                        return None
                    if down_color is None:
                        down_color = row_color
                    elif row_color != down_color:
                        return None
                    cols = [c for c, v in nz]
                    if cols != list(range(expected_len)):
                        return None

        if up_color is None or down_color is None:
            return None

        return {
            "type": "wedge_expansion",
            "seed_color": seed_color,
            "up_color": up_color,
            "down_color": down_color,
            "confidence": 1.0,
        }

    # ---- strategy: mirror row tile ----------------------------------------

    def _try_mirror_row_tile(self, patterns, wm):
        """
        Detect: output width = 4 × input width, same height.
        Each output row = (reversed(row) + row) repeated 2×.
        Category: row-wise horizontal mirror and tile.
        """
        task = wm.task
        if task is None:
            return None

        for pair in task.example_pairs:
            g0, g1 = pair.input_grid, pair.output_grid
            if g0 is None or g1 is None:
                return None
            raw_in, raw_out = g0.raw, g1.raw
            H, W = len(raw_in), len(raw_in[0])
            oH, oW = len(raw_out), len(raw_out[0])

            if oH != H or oW != 4 * W:
                return None

            # Verify each row
            for r in range(H):
                row = raw_in[r]
                rev = list(reversed(row))
                unit = rev + row  # 2W wide
                expected = unit + unit  # 4W wide
                if raw_out[r] != expected:
                    return None

        return {
            "type": "mirror_row_tile",
            "confidence": 1.0,
        }

    # ---- strategy: larger interior rect ------------------------------------

    def _try_larger_interior_rect(self, patterns, wm):
        """
        Detect: input has two hollow rectangles on bg 0, output is 2×2
        filled with the color of the rectangle having the larger interior.
        Category: rectangle comparison by interior area.
        """
        task = wm.task
        if task is None:
            return None

        for pair in task.example_pairs:
            g0, g1 = pair.input_grid, pair.output_grid
            if g0 is None or g1 is None:
                return None
            raw_in, raw_out = g0.raw, g1.raw
            oH, oW = len(raw_out), len(raw_out[0])

            # Output must be 2×2 with uniform color
            if oH != 2 or oW != 2:
                return None
            out_color = raw_out[0][0]
            if not all(raw_out[r][c] == out_color for r in range(2) for c in range(2)):
                return None

            # Find rectangles in input
            rects = self._find_hollow_rects(raw_in)
            if len(rects) != 2:
                return None

            # Compute interior areas
            areas = []
            for color, r0, c0, r1, c1 in rects:
                int_h = r1 - r0 - 1
                int_w = c1 - c0 - 1
                area = max(0, int_h) * max(0, int_w)
                areas.append((area, color))

            # The color with larger interior should match output
            areas.sort(reverse=True)
            if areas[0][1] != out_color:
                return None

        return {
            "type": "larger_interior_rect",
            "confidence": 1.0,
        }

    # ---- strategy: bbox fill -------------------------------------------------

    def _try_bbox_fill(self, patterns, wm):
        """
        Detect: input has a single fg color forming a shape on bg 0.
        Output fills 0-cells within the bounding box of the fg shape with
        a second fill color. Cells outside bbox stay unchanged.
        Category: bounding box completion / shape infill.
        """
        task = wm.task
        if task is None:
            return None

        fg_color = None
        fill_color = None

        for pair in task.example_pairs:
            g0, g1 = pair.input_grid, pair.output_grid
            if g0 is None or g1 is None:
                return None
            raw_in, raw_out = g0.raw, g1.raw
            H = len(raw_in)
            W = len(raw_in[0]) if raw_in else 0
            if len(raw_out) != H or (raw_out and len(raw_out[0]) != W):
                return None

            # Input should have exactly one non-zero color
            in_colors = set()
            for r in range(H):
                for c in range(W):
                    if raw_in[r][c] != 0:
                        in_colors.add(raw_in[r][c])
            if len(in_colors) != 1:
                return None
            pair_fg = in_colors.pop()

            # Output should have exactly two non-zero colors: fg and fill
            out_colors = set()
            for r in range(H):
                for c in range(W):
                    if raw_out[r][c] != 0:
                        out_colors.add(raw_out[r][c])
            if len(out_colors) != 2 or pair_fg not in out_colors:
                return None
            pair_fill = (out_colors - {pair_fg}).pop()

            if fg_color is None:
                fg_color = pair_fg
                fill_color = pair_fill
            elif pair_fg != fg_color or pair_fill != fill_color:
                return None

            # Compute bounding box of fg cells
            fg_rows = [r for r in range(H) for c in range(W) if raw_in[r][c] == fg_color]
            fg_cols = [c for r in range(H) for c in range(W) if raw_in[r][c] == fg_color]
            if not fg_rows:
                return None
            min_r, max_r = min(fg_rows), max(fg_rows)
            min_c, max_c = min(fg_cols), max(fg_cols)

            # Verify: within bbox, 0→fill_color; fg stays fg; outside bbox unchanged
            for r in range(H):
                for c in range(W):
                    in_val = raw_in[r][c]
                    out_val = raw_out[r][c]
                    if min_r <= r <= max_r and min_c <= c <= max_c:
                        if in_val == fg_color:
                            if out_val != fg_color:
                                return None
                        elif in_val == 0:
                            if out_val != fill_color:
                                return None
                    else:
                        if out_val != in_val:
                            return None

        if fg_color is None:
            return None

        return {
            "type": "bbox_fill",
            "fg_color": fg_color,
            "fill_color": fill_color,
            "confidence": 1.0,
        }

    # ---- strategy: symmetry complete -----------------------------------------

    def _try_symmetry_complete(self, patterns, wm):
        """
        Detect: input has a pattern on bg 0 that is nearly 4-fold rotationally
        symmetric about the center of its bounding box. Output completes the
        symmetry by filling in missing rotational counterparts.
        Category: symmetry completion patterns (diamond, checkerboard, etc.).
        """
        task = wm.task
        if task is None:
            return None

        for pair in task.example_pairs:
            g0, g1 = pair.input_grid, pair.output_grid
            if g0 is None or g1 is None:
                return None
            raw_in, raw_out = g0.raw, g1.raw
            H = len(raw_in)
            W = len(raw_in[0]) if raw_in else 0
            if len(raw_out) != H or (raw_out and len(raw_out[0]) != W):
                return None

            # Find non-zero cells
            nz_cells = []
            for r in range(H):
                for c in range(W):
                    if raw_in[r][c] != 0:
                        nz_cells.append((r, c, raw_in[r][c]))
            if len(nz_cells) < 3:
                return None

            rows = [r for r, c, v in nz_cells]
            cols = [c for r, c, v in nz_cells]
            min_r, max_r = min(rows), max(rows)
            min_c, max_c = min(cols), max(cols)

            # Bbox must be square for 4-fold rotation
            if (max_r - min_r) != (max_c - min_c) or (max_r - min_r) < 2:
                return None

            cr = (min_r + max_r) / 2.0
            cc = (min_c + max_c) / 2.0

            # Build symmetry-completed grid
            completed = [row[:] for row in raw_in]
            for r, c, v in nz_cells:
                for nr, nc in [
                    (cr + (c - cc), cc - (r - cr)),       # 90° CW
                    (2 * cr - r, 2 * cc - c),             # 180°
                    (cr - (c - cc), cc + (r - cr)),       # 270°
                ]:
                    nri, nci = int(round(nr)), int(round(nc))
                    if 0 <= nri < H and 0 <= nci < W:
                        if completed[nri][nci] == 0:
                            completed[nri][nci] = v
                        elif completed[nri][nci] != v:
                            return None  # Conflict

            # Verify completed matches output
            for r in range(H):
                for c in range(W):
                    if completed[r][c] != raw_out[r][c]:
                        return None

        return {"type": "symmetry_complete", "confidence": 1.0}

    # ---- strategy: accelerating sequence -------------------------------------

    def _try_accelerating_sequence(self, patterns, wm):
        """
        Detect: input has one row with seed colors; output fills that row with
        colors cycling through the seed at triangular-number positions
        (gaps increase by 1 each step: 1, 2, 3, 4, ...).
        Category: accelerating / expanding sequence patterns.
        """
        task = wm.task
        if task is None:
            return None

        for pair in task.example_pairs:
            g0, g1 = pair.input_grid, pair.output_grid
            if g0 is None or g1 is None:
                return None
            raw_in, raw_out = g0.raw, g1.raw
            H = len(raw_in)
            W = len(raw_in[0]) if raw_in else 0
            if len(raw_out) != H or (raw_out and len(raw_out[0]) != W):
                return None

            # Find the single non-zero row
            nz_row = None
            for r in range(H):
                if any(raw_in[r][c] != 0 for c in range(W)):
                    if nz_row is not None:
                        return None
                    nz_row = r
            if nz_row is None:
                return None

            # Collect seed colors
            seed_colors = []
            for c in range(W):
                if raw_in[nz_row][c] != 0:
                    seed_colors.append(raw_in[nz_row][c])
            if len(seed_colors) < 2:
                return None

            # Verify seed positions match triangular numbers
            seed_positions = [c for c in range(W) if raw_in[nz_row][c] != 0]
            for i, pos in enumerate(seed_positions):
                if pos != i * (i + 1) // 2:
                    return None

            # Generate expected output row
            expected_row = [0] * W
            pos = 0
            gap = 1
            ci = 0
            while pos < W:
                expected_row[pos] = seed_colors[ci % len(seed_colors)]
                ci += 1
                pos += gap
                gap += 1

            # Verify output
            for c in range(W):
                if raw_out[nz_row][c] != expected_row[c]:
                    return None
            for r in range(H):
                if r != nz_row:
                    for c in range(W):
                        if raw_out[r][c] != 0:
                            return None

        return {"type": "accelerating_sequence", "confidence": 1.0}

    def _find_hollow_rects(self, raw):
        """Find hollow or solid rectangles of non-zero colors on bg 0."""
        H = len(raw)
        W = len(raw[0]) if raw else 0
        visited = [[False] * W for _ in range(H)]
        rects = []

        for r in range(H):
            for c in range(W):
                if raw[r][c] != 0 and not visited[r][c]:
                    color = raw[r][c]
                    # BFS to find all connected cells of this color
                    cells = set()
                    queue = [(r, c)]
                    visited[r][c] = True
                    while queue:
                        cr, cc = queue.pop(0)
                        cells.add((cr, cc))
                        for dr, dc in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                            nr, nc = cr + dr, cc + dc
                            if 0 <= nr < H and 0 <= nc < W and not visited[nr][nc] and raw[nr][nc] == color:
                                visited[nr][nc] = True
                                queue.append((nr, nc))

                    # Check if cells form a rectangle border
                    min_r = min(cr for cr, cc in cells)
                    max_r = max(cr for cr, cc in cells)
                    min_c = min(cc for cr, cc in cells)
                    max_c = max(cc for cr, cc in cells)

                    # All border cells must be present
                    is_rect = True
                    for br in range(min_r, max_r + 1):
                        for bc in range(min_c, max_c + 1):
                            on_border = (br == min_r or br == max_r or
                                         bc == min_c or bc == max_c)
                            if on_border and (br, bc) not in cells:
                                is_rect = False
                                break
                        if not is_rect:
                            break

                    if is_rect:
                        rects.append((color, min_r, min_c, max_r, max_c))

        return rects

    # ---- strategy 55: cross pair lines ------------------------------------

    def _try_cross_pair_lines(self, patterns, wm):
        """
        Detect: bg-0 grid with scattered pixels; each non-zero color appears
        exactly twice forming a horizontal pair (same row) or vertical pair
        (same column). Output draws filled lines between each pair's endpoints.
        Vertical lines overwrite horizontal lines at crossings.
        Category: pair-based line drawing / crosshatch.
        """
        task = wm.task
        if not task or not task.example_pairs:
            return None

        for pair in task.example_pairs:
            g0, g1 = pair.input_grid, pair.output_grid
            if g0 is None or g1 is None:
                return None
            inp, out = g0.raw, g1.raw
            H, W = len(inp), len(inp[0])
            if len(out) != H or len(out[0]) != W:
                return None

            # Collect non-zero pixels by color
            color_pos = {}
            for r in range(H):
                for c in range(W):
                    v = inp[r][c]
                    if v != 0:
                        color_pos.setdefault(v, []).append((r, c))

            if len(color_pos) < 2:
                return None

            # Each color must appear exactly 2 times
            for color, positions in color_pos.items():
                if len(positions) != 2:
                    return None

            # Each pair must be aligned (same row or same column)
            h_lines = []
            v_lines = []
            for color, positions in color_pos.items():
                (r1, c1), (r2, c2) = positions
                if r1 == r2:
                    h_lines.append((r1, min(c1, c2), max(c1, c2), color))
                elif c1 == c2:
                    v_lines.append((c1, min(r1, r2), max(r1, r2), color))
                else:
                    return None

            if not h_lines and not v_lines:
                return None

            # Verify output: draw horizontal first, then vertical overwrites
            expected = [[0] * W for _ in range(H)]
            for row, c_min, c_max, color in h_lines:
                for c in range(c_min, c_max + 1):
                    expected[row][c] = color
            for col, r_min, r_max, color in v_lines:
                for r in range(r_min, r_max + 1):
                    expected[r][col] = color

            if expected != out:
                return None

        return {"type": "cross_pair_lines", "confidence": 1.0}

    # ---- strategy 56: multi-layer overlay ---------------------------------

    def _try_multi_layer_overlay(self, patterns, wm):
        """
        Detect: input is N stacked layers of the same dimensions, each with
        one non-zero color and 0s (binary mask per color). Output merges all
        layers into a single layer. Where multiple layers overlap, the winner
        is determined by a priority learned from training examples.
        Category: layer compositing / z-order merge.
        """
        task = wm.task
        if not task or not task.example_pairs:
            return None

        first_pair = task.example_pairs[0]
        g0, g1 = first_pair.input_grid, first_pair.output_grid
        if g0 is None or g1 is None:
            return None
        inp0, out0 = g0.raw, g1.raw
        H_in = len(inp0)
        W = len(inp0[0])
        H_out = len(out0)
        W_out = len(out0[0])

        if W != W_out or H_in == H_out:
            return None
        if H_in % H_out != 0:
            return None

        N = H_in // H_out
        if N < 2 or N > 10:
            return None

        # Determine layer colors from first pair
        layer_colors = []
        for li in range(N):
            sr = li * H_out
            colors = set()
            for r in range(sr, sr + H_out):
                for c in range(W):
                    if inp0[r][c] != 0:
                        colors.add(inp0[r][c])
            if len(colors) != 1:
                return None
            layer_colors.append(colors.pop())

        if len(set(layer_colors)) != N:
            return None

        # Verify structure across all example pairs
        for pair in task.example_pairs:
            g0, g1 = pair.input_grid, pair.output_grid
            if g0 is None or g1 is None:
                return None
            inp, out = g0.raw, g1.raw
            if len(inp) != H_in or len(inp[0]) != W:
                return None
            if len(out) != H_out or len(out[0]) != W_out:
                return None
            for li in range(N):
                sr = li * H_out
                for r in range(sr, sr + H_out):
                    for c in range(W):
                        v = inp[r][c]
                        if v != 0 and v != layer_colors[li]:
                            return None

        # Learn priority from pairwise wins
        wins_over = set()
        for pair in task.example_pairs:
            g0, g1 = pair.input_grid, pair.output_grid
            inp, out = g0.raw, g1.raw
            for r in range(H_out):
                for c in range(W_out):
                    out_val = out[r][c]
                    non_zero = []
                    for li in range(N):
                        if inp[li * H_out + r][c] != 0:
                            non_zero.append(layer_colors[li])
                    if out_val == 0:
                        if non_zero:
                            return None
                    elif len(non_zero) > 1:
                        if out_val not in non_zero:
                            return None
                        for loser in non_zero:
                            if loser != out_val:
                                if (loser, out_val) in wins_over:
                                    return None  # contradiction
                                wins_over.add((out_val, loser))
                    elif len(non_zero) == 1:
                        if out_val != non_zero[0]:
                            return None

        # Sort by win count (most wins = highest priority)
        priority = sorted(
            layer_colors,
            key=lambda c: sum(1 for (w, _l) in wins_over if w == c),
            reverse=True,
        )

        # Final verification against all example pairs
        for pair in task.example_pairs:
            g0, g1 = pair.input_grid, pair.output_grid
            inp, out = g0.raw, g1.raw
            for r in range(H_out):
                for c in range(W_out):
                    exp = 0
                    for color in priority:
                        li = layer_colors.index(color)
                        if inp[li * H_out + r][c] != 0:
                            exp = color
                            break
                    if exp != out[r][c]:
                        return None

        return {
            "type": "multi_layer_overlay",
            "confidence": 1.0,
            "num_layers": N,
            "layer_height": H_out,
            "layer_colors": layer_colors,
            "priority": priority,
        }

    # ---- strategy 57: tile grid recolor -----------------------------------

    def _try_tile_grid_recolor(self, patterns, wm):
        """
        Detect: grid has a regular array of tiles (color 5) arranged in
        rows/cols separated by 0-gaps, plus a separate key matrix (non-0,
        non-5 rectangular block) whose dimensions match the tile grid.
        Output replaces each tile's 5-cells with the corresponding key color.
        Category: template coloring / lookup table.
        """
        task = wm.task
        if not task or not task.example_pairs:
            return None

        for pair in task.example_pairs:
            g0, g1 = pair.input_grid, pair.output_grid
            if g0 is None or g1 is None:
                return None
            inp, out = g0.raw, g1.raw
            H, W = len(inp), len(inp[0])
            if len(out) != H or len(out[0]) != W:
                return None

            # Find 5-cells (tiles)
            five_cells = set()
            for r in range(H):
                for c in range(W):
                    if inp[r][c] == 5:
                        five_cells.add((r, c))
            if not five_cells:
                return None

            # Find key cells (non-0, non-5)
            key_cells = {}
            for r in range(H):
                for c in range(W):
                    v = inp[r][c]
                    if v != 0 and v != 5:
                        key_cells[(r, c)] = v
            if not key_cells:
                return None

            # Check key forms a dense rectangle
            kr_min = min(r for r, c in key_cells)
            kr_max = max(r for r, c in key_cells)
            kc_min = min(c for r, c in key_cells)
            kc_max = max(c for r, c in key_cells)
            for r in range(kr_min, kr_max + 1):
                for c in range(kc_min, kc_max + 1):
                    if (r, c) not in key_cells:
                        return None
            key_h = kr_max - kr_min + 1
            key_w = kc_max - kc_min + 1

            # Group 5-cells into tile row-bands and column-sections
            tile_rows = sorted(set(r for r, c in five_cells))
            tile_cols = sorted(set(c for r, c in five_cells))
            if not tile_rows or not tile_cols:
                return None

            row_bands = []
            cur = [tile_rows[0]]
            for i in range(1, len(tile_rows)):
                if tile_rows[i] == cur[-1] + 1:
                    cur.append(tile_rows[i])
                else:
                    row_bands.append(cur)
                    cur = [tile_rows[i]]
            row_bands.append(cur)

            col_sections = []
            cur = [tile_cols[0]]
            for i in range(1, len(tile_cols)):
                if tile_cols[i] == cur[-1] + 1:
                    cur.append(tile_cols[i])
                else:
                    col_sections.append(cur)
                    cur = [tile_cols[i]]
            col_sections.append(cur)

            # Key dimensions must match tile grid dimensions
            if len(row_bands) != key_h or len(col_sections) != key_w:
                return None

            # Verify output: tiles recolored, everything else unchanged
            for tr in range(len(row_bands)):
                for tc in range(len(col_sections)):
                    key_color = key_cells[(kr_min + tr, kc_min + tc)]
                    for r in row_bands[tr]:
                        for c in col_sections[tc]:
                            if inp[r][c] == 5:
                                if out[r][c] != key_color:
                                    return None
                            elif out[r][c] != inp[r][c]:
                                return None

            # Non-tile, non-key cells must be unchanged
            tile_region = set()
            for band in row_bands:
                for sec in col_sections:
                    for r in band:
                        for c in sec:
                            tile_region.add((r, c))
            for r in range(H):
                for c in range(W):
                    if (r, c) not in tile_region and (r, c) not in key_cells:
                        if out[r][c] != inp[r][c]:
                            return None

        return {"type": "tile_grid_recolor", "confidence": 1.0, "tile_color": 5}

    # ---- strategy 58: rect minority gridlines --------------------------------

    def _try_rect_minority_gridlines(self, patterns, wm):
        """
        Detect: grid with a rectangular region of mostly one color (dominant)
        containing a few cells of another color (minority). The output extracts
        just the rectangle and draws full horizontal+vertical grid lines through
        each minority cell position. The rect may be embedded in noisy surroundings.
        Category: pattern extraction / grid line inference from embedded markers.
        """
        task = wm.task
        if not task or not task.example_pairs:
            return None

        for pair in task.example_pairs:
            g0, g1 = pair.input_grid, pair.output_grid
            if g0 is None or g1 is None:
                return None
            inp, out = g0.raw, g1.raw
            H, W = len(inp), len(inp[0])
            oH, oW = len(out), len(out[0])

            if oH >= H and oW >= W:
                return None  # output not smaller than input

            # Scan all possible top-left positions for a rect of output dims
            found = False
            for rmin in range(H - oH + 1):
                for cmin in range(W - oW + 1):
                    # Extract subgrid
                    from collections import Counter as _Counter
                    color_counts = _Counter()
                    for r in range(rmin, rmin + oH):
                        for c in range(cmin, cmin + oW):
                            color_counts[inp[r][c]] += 1

                    total = oH * oW
                    if not color_counts:
                        continue

                    dom_color, dom_count = color_counts.most_common(1)[0]
                    if dom_count < total * 0.7:
                        continue

                    # Check that non-dominant cells are all one color
                    minority_color = None
                    minority_positions = []
                    valid = True
                    for r in range(rmin, rmin + oH):
                        for c in range(cmin, cmin + oW):
                            v = inp[r][c]
                            if v != dom_color:
                                if minority_color is None:
                                    minority_color = v
                                elif v != minority_color:
                                    valid = False
                                    break
                                minority_positions.append((r - rmin, c - cmin))
                        if not valid:
                            break

                    if not valid or minority_color is None:
                        continue
                    if len(minority_positions) < 1:
                        continue

                    # Verify output: gridlines at minority positions
                    min_rows = set(r for r, c in minority_positions)
                    min_cols = set(c for r, c in minority_positions)

                    expected = [[dom_color] * oW for _ in range(oH)]
                    for mr in min_rows:
                        for c in range(oW):
                            expected[mr][c] = minority_color
                    for mc in min_cols:
                        for r in range(oH):
                            expected[r][mc] = minority_color

                    if expected == out:
                        found = True
                        break
                if found:
                    break

            if not found:
                return None

        return {"type": "rect_minority_gridlines", "confidence": 1.0}

    # ---- strategy 59: rect directional tile ----------------------------------

    def _try_rect_directional_tile(self, patterns, wm):
        """
        Detect: grid has hollow rectangles (frame color X, interior bg 0) and
        lines of color 1 as direction indicators. Each rect tiles in the direction(s)
        indicated by 1-lines, extending from its position to the 1-line.
        The 1-lines are replaced by the tiled pattern. Untouched rects stay.
        Category: directional tiling / pattern extrusion.
        """
        task = wm.task
        if not task or not task.example_pairs:
            return None

        for pair in task.example_pairs:
            g0, g1 = pair.input_grid, pair.output_grid
            if g0 is None or g1 is None:
                return None
            inp, out = g0.raw, g1.raw
            H, W = len(inp), len(inp[0])
            if len(out) != H or len(out[0]) != W:
                return None

            # Find hollow rects: 4×4 frame of color X with 2×2 interior of 0
            rects = []
            used = set()
            for r in range(H - 3):
                for c in range(W - 3):
                    v = inp[r][c]
                    if v == 0 or v == 1:
                        continue
                    # Check 4×4 hollow rect
                    frame_ok = True
                    for dr in range(4):
                        for dc in range(4):
                            cell = inp[r + dr][c + dc]
                            if dr in (0, 3) or dc in (0, 3):
                                if cell != v:
                                    frame_ok = False
                                    break
                            else:
                                if cell != 0:
                                    frame_ok = False
                                    break
                        if not frame_ok:
                            break
                    if frame_ok and (r, c) not in used:
                        rects.append((r, c, v))
                        for dr in range(4):
                            for dc in range(4):
                                used.add((r + dr, c + dc))

            if not rects:
                return None

            # Find 1-lines (horizontal segments and vertical segments)
            one_cells = set()
            for r in range(H):
                for c in range(W):
                    if inp[r][c] == 1:
                        one_cells.add((r, c))

            if not one_cells:
                return None

            # For each rect, find associated 1-lines by alignment
            # Build expected output
            expected = [[inp[r][c] for c in range(W)] for r in range(H)]
            # Remove 1-lines from expected
            for r, c in one_cells:
                expected[r][c] = 0

            for rect_r, rect_c, rect_color in rects:
                rect_pattern = [[inp[rect_r + dr][rect_c + dc] for dc in range(4)] for dr in range(4)]

                # Check for horizontal 1-line (same row span as rect)
                # Right side
                h_one_r = None
                for c_check in range(rect_c + 4, W):
                    row_span_ones = all((rect_r + dr, c_check) in one_cells for dr in range(4))
                    if row_span_ones:
                        h_one_r = c_check
                        break
                if h_one_r is not None:
                    # Tile rightward from rect to h_one_r
                    for c_pos in range(rect_c + 4, h_one_r + 1):
                        dc = (c_pos - rect_c) % 4
                        for dr in range(4):
                            expected[rect_r + dr][c_pos] = rect_pattern[dr][dc]

                # Left side
                h_one_l = None
                for c_check in range(rect_c - 1, -1, -1):
                    row_span_ones = all((rect_r + dr, c_check) in one_cells for dr in range(4))
                    if row_span_ones:
                        h_one_l = c_check
                        break
                if h_one_l is not None:
                    # Tile leftward from rect to h_one_l
                    for c_pos in range(rect_c - 1, h_one_l - 1, -1):
                        dc = (c_pos - rect_c) % 4
                        for dr in range(4):
                            expected[rect_r + dr][c_pos] = rect_pattern[dr][dc]

                # Check for vertical 1-line (same col span as rect)
                # Below
                v_one_b = None
                for r_check in range(rect_r + 4, H):
                    col_span_ones = all((r_check, rect_c + dc) in one_cells for dc in range(4))
                    if col_span_ones:
                        v_one_b = r_check
                        break
                if v_one_b is not None:
                    for r_pos in range(rect_r + 4, v_one_b + 1):
                        dr = (r_pos - rect_r) % 4
                        for dc in range(4):
                            expected[r_pos][rect_c + dc] = rect_pattern[dr][dc]

                # Above
                v_one_t = None
                for r_check in range(rect_r - 1, -1, -1):
                    col_span_ones = all((r_check, rect_c + dc) in one_cells for dc in range(4))
                    if col_span_ones:
                        v_one_t = r_check
                        break
                if v_one_t is not None:
                    for r_pos in range(rect_r - 1, v_one_t - 1, -1):
                        dr = (r_pos - rect_r) % 4
                        for dc in range(4):
                            expected[r_pos][rect_c + dc] = rect_pattern[dr][dc]

            if expected != out:
                return None

        return {"type": "rect_directional_tile", "confidence": 1.0}

    # ---- strategy 60: corner block shift -------------------------------------

    def _try_corner_block_shift(self, patterns, wm):
        """
        Detect: grid with uniform background has rectangular blocks of non-bg
        colors at corner-like positions. The most frequent non-bg color among
        corner blocks shifts inward by one block dimension. Minority-color
        blocks stay in place.
        Category: object motion / corner block inward displacement.
        """
        task = wm.task
        if not task or not task.example_pairs:
            return None

        for pair in task.example_pairs:
            g0, g1 = pair.input_grid, pair.output_grid
            if g0 is None or g1 is None:
                return None
            inp, out = g0.raw, g1.raw
            H, W = len(inp), len(inp[0])
            if len(out) != H or len(out[0]) != W:
                return None

            # Find background color (most common)
            from collections import Counter
            flat = [inp[r][c] for r in range(H) for c in range(W)]
            bg = Counter(flat).most_common(1)[0][0]

            # Find connected components of non-bg cells
            visited = set()
            blocks = []
            for r in range(H):
                for c in range(W):
                    if inp[r][c] != bg and (r, c) not in visited:
                        color = inp[r][c]
                        # BFS
                        comp = []
                        queue = [(r, c)]
                        while queue:
                            cr, cc = queue.pop(0)
                            if (cr, cc) in visited:
                                continue
                            if cr < 0 or cr >= H or cc < 0 or cc >= W:
                                continue
                            if inp[cr][cc] != color:
                                continue
                            visited.add((cr, cc))
                            comp.append((cr, cc))
                            for dr, dc in [(-1,0),(1,0),(0,-1),(0,1)]:
                                queue.append((cr+dr, cc+dc))
                        rmin = min(r2 for r2, c2 in comp)
                        rmax = max(r2 for r2, c2 in comp)
                        cmin = min(c2 for r2, c2 in comp)
                        cmax = max(c2 for r2, c2 in comp)
                        bh = rmax - rmin + 1
                        bw = cmax - cmin + 1
                        # Must be solid rectangle
                        if len(comp) == bh * bw:
                            blocks.append({
                                "color": color,
                                "rmin": rmin, "rmax": rmax,
                                "cmin": cmin, "cmax": cmax,
                                "h": bh, "w": bw
                            })

            if len(blocks) < 2:
                return None

            # Count color frequencies
            color_counts = Counter(b["color"] for b in blocks)
            if len(color_counts) < 2:
                # All same color — all shift
                majority_color = blocks[0]["color"]
            else:
                majority_color = color_counts.most_common(1)[0][0]

            # Build expected output
            expected = [[bg] * W for _ in range(H)]

            for b in blocks:
                if b["color"] != majority_color:
                    # Minority blocks stay
                    for r in range(b["rmin"], b["rmax"] + 1):
                        for c in range(b["cmin"], b["cmax"] + 1):
                            expected[r][c] = b["color"]
                else:
                    # Majority blocks shift inward by their own dimensions
                    # Determine direction: toward center of grid
                    center_r = (H - 1) / 2.0
                    center_c = (W - 1) / 2.0
                    block_center_r = (b["rmin"] + b["rmax"]) / 2.0
                    block_center_c = (b["cmin"] + b["cmax"]) / 2.0

                    dr = 0
                    if block_center_r < center_r:
                        dr = b["h"]
                    elif block_center_r > center_r:
                        dr = -b["h"]

                    dc = 0
                    if block_center_c < center_c:
                        dc = b["w"]
                    elif block_center_c > center_c:
                        dc = -b["w"]

                    nr = b["rmin"] + dr
                    nc = b["cmin"] + dc
                    for r in range(nr, nr + b["h"]):
                        for c in range(nc, nc + b["w"]):
                            if 0 <= r < H and 0 <= c < W:
                                expected[r][c] = b["color"]

            if expected != out:
                return None

        return {"type": "corner_block_shift", "confidence": 1.0}

    # ---- strategy 61: grid section key lookup --------------------------------

    def _try_grid_section_key_lookup(self, patterns, wm):
        """Grid divided by color-5 lines into 3×3 sections. One 'key' section
        has exactly 4 non-zero cells (missing color 8). Each value V at local
        position (r,c) in the key section → fill section at meta-position (r,c)
        with color V. Other sections get 0."""
        if wm.task is None:
            return None
        for pair in wm.task.example_pairs:
            raw_in = pair.input_grid.raw
            raw_out = pair.output_grid.raw
            H, W = len(raw_in), len(raw_in[0])
            if H != len(raw_out) or W != len(raw_out[0]):
                return None
            # Find separator rows and cols (all cells == 5)
            sep_rows = [r for r in range(H) if all(raw_in[r][c] == 5 for c in range(W))]
            sep_cols = [c for c in range(W) if all(raw_in[r][c] == 5 for r in range(H))]
            if len(sep_rows) != 2 or len(sep_cols) != 2:
                return None
            # Build section row/col bands
            row_bands = []
            prev = 0
            for sr in sep_rows:
                row_bands.append((prev, sr))
                prev = sr + 1
            row_bands.append((prev, H))
            col_bands = []
            prev = 0
            for sc in sep_cols:
                col_bands.append((prev, sc))
                prev = sc + 1
            col_bands.append((prev, W))
            if len(row_bands) != 3 or len(col_bands) != 3:
                return None
            # Find key section: exactly 4 non-zero cells with 4 unique values
            key_section = None
            key_mr = key_mc = -1
            for mr in range(3):
                for mc in range(3):
                    r0, r1 = row_bands[mr]
                    c0, c1 = col_bands[mc]
                    cells = {}
                    for r in range(r0, r1):
                        for c in range(c0, c1):
                            v = raw_in[r][c]
                            if v != 0:
                                cells[(r - r0, c - c0)] = v
                    unique_vals = set(cells.values())
                    if len(cells) == 4 and len(unique_vals) == 4 and 8 not in unique_vals:
                        if key_section is not None:
                            return None  # multiple keys
                        key_section = cells
                        key_mr, key_mc = mr, mc
            if key_section is None:
                return None
            # Build expected output
            expected = [[0] * W for _ in range(H)]
            # Keep separator lines
            for sr in sep_rows:
                for c in range(W):
                    expected[sr][c] = 5
            for sc in sep_cols:
                for r in range(H):
                    expected[r][sc] = 5
            # Fill sections based on key
            for (lr, lc), v in key_section.items():
                tr, tc = lr, lc  # target meta-position
                r0, r1 = row_bands[tr]
                c0, c1 = col_bands[tc]
                for r in range(r0, r1):
                    for c in range(c0, c1):
                        expected[r][c] = v
            if expected != raw_out:
                return None
        return {"type": "grid_section_key_lookup", "confidence": 1.0}

    # ---- strategy 62: shape template catalog ---------------------------------

    @staticmethod
    def _normalize_shape(cells):
        """Normalize a set of (r,c) positions to origin-relative frozenset."""
        if not cells:
            return frozenset()
        min_r = min(r for r, c in cells)
        min_c = min(c for r, c in cells)
        return frozenset((r - min_r, c - min_c) for r, c in cells)

    @staticmethod
    def _shape_orientations(shape):
        """Return all 8 orientations (4 rotations × 2 reflections) of a shape."""
        orientations = set()
        current = set(shape)
        for _ in range(4):
            # normalize
            min_r = min(r for r, c in current)
            min_c = min(c for r, c in current)
            normed = frozenset((r - min_r, c - min_c) for r, c in current)
            orientations.add(normed)
            # reflect horizontally
            reflected = set()
            for r, c in normed:
                reflected.add((r, -c))
            min_c2 = min(c for r, c in reflected)
            ref_normed = frozenset((r, c - min_c2) for r, c in reflected)
            orientations.add(ref_normed)
            # rotate 90 CW: (r,c) -> (c, -r)
            current = set((c, -r) for r, c in current)
        return orientations

    @staticmethod
    def _find_connected_components(grid, H, W, target_colors, region=None):
        """Find 4-connected components of cells matching target_colors.
        region is optional (r0,r1,c0,c1) bounds."""
        r0, r1 = (0, H) if region is None else (region[0], region[1])
        c0, c1 = (0, W) if region is None else (region[2], region[3])
        visited = set()
        components = []
        for r in range(r0, r1):
            for c in range(c0, c1):
                if grid[r][c] in target_colors and (r, c) not in visited:
                    color = grid[r][c]
                    comp = []
                    queue = [(r, c)]
                    while queue:
                        cr, cc = queue.pop(0)
                        if (cr, cc) in visited:
                            continue
                        if cr < r0 or cr >= r1 or cc < c0 or cc >= c1:
                            continue
                        if grid[cr][cc] != color:
                            continue
                        visited.add((cr, cc))
                        comp.append((cr, cc))
                        for dr, dc in [(-1,0),(1,0),(0,-1),(0,1)]:
                            queue.append((cr+dr, cc+dc))
                    components.append((color, comp))
        return components

    def _try_shape_template_catalog(self, patterns, wm):
        """Key area (above/left of 5-dividers) has template shapes of distinct
        colors. Rest of grid has color-3 shapes. Each 3-shape matches one
        template (with rotation/reflection). Replace 3 with matching color."""
        if wm.task is None:
            return None
        for pair in wm.task.example_pairs:
            raw_in = pair.input_grid.raw
            raw_out = pair.output_grid.raw
            H, W = len(raw_in), len(raw_in[0])
            if H != len(raw_out) or W != len(raw_out[0]):
                return None
            # Find sep_col: first column with 5 in row 0 (vertical separator)
            sep_col = None
            for c in range(W):
                if raw_in[0][c] == 5:
                    sep_col = c
                    break
            if sep_col is None or sep_col < 1:
                return None
            # Find sep_row: first row where cols 0..sep_col are all 5
            sep_row = None
            for r in range(1, H):
                if all(raw_in[r][c] == 5 for c in range(sep_col + 1)):
                    sep_row = r
                    break
            if sep_row is None or sep_row < 1:
                return None
            # Extract templates from key area (rows 0..sep_row-1, cols 0..sep_col-1)
            key_colors = set()
            for r in range(sep_row):
                for c in range(sep_col):
                    v = raw_in[r][c]
                    if v != 0 and v != 5:
                        key_colors.add(v)
            if 3 in key_colors:
                return None  # 3 should only be in the non-key area
            templates = {}  # color -> set of orientations
            comps = self._find_connected_components(
                raw_in, H, W, key_colors, region=(0, sep_row, 0, sep_col))
            for color, cells in comps:
                shape = self._normalize_shape(cells)
                orients = self._shape_orientations(shape)
                templates[color] = orients
            if not templates:
                return None
            # Find all color-3 components in the full grid
            comps_3 = self._find_connected_components(raw_in, H, W, {3})
            if not comps_3:
                return None
            # Match each 3-component to a template
            expected = [row[:] for row in raw_in]
            for _, cells in comps_3:
                shape = self._normalize_shape(cells)
                matched_color = None
                for color, orients in templates.items():
                    if shape in orients:
                        matched_color = color
                        break
                if matched_color is None:
                    return None  # unmatched shape
                for r, c in cells:
                    expected[r][c] = matched_color
            if expected != raw_out:
                return None
        return {"type": "shape_template_catalog", "confidence": 1.0}

    # ---- strategy 63: bar chart balance --------------------------------------

    def _try_bar_chart_balance(self, patterns, wm):
        """Grid bg=7 with vertical bars of colors 8 and 2 at odd columns.
        Add a new bar of color 5 at the next odd column. Height = sum(8 heights) - sum(2 heights)."""
        if wm.task is None:
            return None
        for pair in wm.task.example_pairs:
            raw_in = pair.input_grid.raw
            raw_out = pair.output_grid.raw
            H, W = len(raw_in), len(raw_in[0])
            if H != len(raw_out) or W != len(raw_out[0]):
                return None
            # Verify background is 7
            from collections import Counter
            flat = [raw_in[r][c] for r in range(H) for c in range(W)]
            bg = Counter(flat).most_common(1)[0][0]
            if bg != 7:
                return None
            # Scan odd columns for bars extending from bottom
            sum_8 = 0
            sum_2 = 0
            max_bar_col = -1
            for c in range(1, W, 2):
                h = 0
                bar_color = None
                for r in range(H - 1, -1, -1):
                    if raw_in[r][c] != 7:
                        if bar_color is None:
                            bar_color = raw_in[r][c]
                        if raw_in[r][c] == bar_color:
                            h += 1
                        else:
                            break
                    else:
                        break
                if h > 0 and bar_color in (8, 2):
                    if bar_color == 8:
                        sum_8 += h
                    else:
                        sum_2 += h
                    max_bar_col = max(max_bar_col, c)
            balance_height = sum_8 - sum_2
            if balance_height <= 0:
                return None
            # Target column: next odd column after the last bar
            target_col = max_bar_col + 2
            if target_col >= W or target_col % 2 == 0:
                return None
            # Build expected output
            expected = [row[:] for row in raw_in]
            for r in range(H - balance_height, H):
                if 0 <= r < H:
                    expected[r][target_col] = 5
            if expected != raw_out:
                return None
        return {"type": "bar_chart_balance", "confidence": 1.0,
                "bg_color": 7, "bar_color_pos": 8, "bar_color_neg": 2, "fill_color": 5}


    # ---- strategy 64: largest blob color -----------------------------------

    def _try_largest_blob_color(self, patterns, wm):
        """Noisy grid with solid-colored patches; output = 3×3 grid of
        the color with the largest connected component.
        Category: object detection / largest CC identification."""
        task = wm.task
        if task is None:
            return None

        for pair in task.example_pairs:
            g0, g1 = pair.input_grid, pair.output_grid
            if g0 is None or g1 is None:
                return None
            raw_in, raw_out = g0.raw, g1.raw
            H_out, W_out = len(raw_out), len(raw_out[0])
            # Output must be small uniform grid (e.g. 3×3)
            if H_out > 5 or W_out > 5:
                return None
            # Output must be uniform (all same color)
            out_color = raw_out[0][0]
            if not all(raw_out[r][c] == out_color for r in range(H_out) for c in range(W_out)):
                return None
            # Find largest CC in input
            best_color = self._find_largest_cc_color(raw_in)
            if best_color != out_color:
                return None

        return {"type": "largest_blob_color", "confidence": 1.0,
                "out_rows": H_out, "out_cols": W_out}

    @staticmethod
    def _find_largest_cc_color(raw):
        """Return color of largest connected patch in a noisy grid.
        Patches are colors where ALL cells form a single connected component
        (largest_cc == total_count). Among those, return the one with the
        most cells. Noise colors are fragmented and filtered out."""
        from collections import Counter
        H = len(raw)
        W = len(raw[0]) if raw else 0
        counts = Counter()
        for r in range(H):
            for c in range(W):
                counts[raw[r][c]] += 1
        # For each color, find its largest CC
        visited = [[False] * W for _ in range(H)]
        largest_cc = {}  # color -> max cc size
        for r in range(H):
            for c in range(W):
                if visited[r][c]:
                    continue
                color = raw[r][c]
                queue = [(r, c)]
                visited[r][c] = True
                size = 0
                while queue:
                    cr, cc = queue.pop(0)
                    size += 1
                    for dr, dc in ((-1, 0), (1, 0), (0, -1), (0, 1)):
                        nr, nc = cr + dr, cc + dc
                        if 0 <= nr < H and 0 <= nc < W and not visited[nr][nc] and raw[nr][nc] == color:
                            visited[nr][nc] = True
                            queue.append((nr, nc))
                largest_cc[color] = max(largest_cc.get(color, 0), size)
        # Filter: patch colors have largest_cc == total count (fully connected)
        # and at least 4 cells
        best_size = 0
        best_color = 0
        for color, cc_size in largest_cc.items():
            if cc_size == counts[color] and cc_size >= 4:
                if cc_size > best_size:
                    best_size = cc_size
                    best_color = color
        return best_color

    # ---- strategy 65: shape stamp fill ------------------------------------

    def _try_shape_stamp_fill(self, patterns, wm):
        """Grid of 0s and 5s with some 2-cells forming a shape template.
        All groups of 0-cells matching the same shape get filled with 2.
        Uses progressive matching (earlier matches block later ones) and
        checks that interior holes of the shape are non-0.
        Category: template matching / shape stamping."""
        task = wm.task
        if task is None:
            return None

        for pair in task.example_pairs:
            g0, g1 = pair.input_grid, pair.output_grid
            if g0 is None or g1 is None:
                return None
            raw_in, raw_out = g0.raw, g1.raw
            H, W = len(raw_in), len(raw_in[0])
            if H != len(raw_out) or W != len(raw_out[0]):
                return None
            # Grid must have exactly 3 colors: 0, 5, and 2
            colors_in = set()
            for r in range(H):
                for c in range(W):
                    colors_in.add(raw_in[r][c])
            if 2 not in colors_in or 5 not in colors_in or 0 not in colors_in:
                return None
            if len(colors_in) > 3:
                return None
            expected = self._stamp_fill_grid(raw_in)
            if expected != raw_out:
                return None

        return {"type": "shape_stamp_fill", "confidence": 1.0}

    @staticmethod
    def _stamp_fill_grid(raw_in):
        """Apply shape stamp fill: find 2-template, match 0-regions, fill.
        For 1D shapes (single row/column), stamps only on the same row/col.
        For 2D shapes, stamps anywhere. Uses isolation-score ordering with
        progressive stamping to resolve overlapping positions."""
        H, W = len(raw_in), len(raw_in[0])
        template_cells = []
        for r in range(H):
            for c in range(W):
                if raw_in[r][c] == 2:
                    template_cells.append((r, c))
        if not template_cells:
            return [row[:] for row in raw_in]
        min_r = min(r for r, c in template_cells)
        min_c = min(c for r, c in template_cells)
        shape = frozenset((r - min_r, c - min_c) for r, c in template_cells)
        shape_h = max(r for r, c in shape) + 1
        shape_w = max(c for r, c in shape) + 1
        # 1D filter: if shape is a single row or column, constrain stamps
        rows_used = set(r for r, c in shape)
        cols_used = set(c for r, c in shape)
        is_horiz = len(rows_used) == 1
        is_vert = len(cols_used) == 1
        tmpl_row = min_r if is_horiz else None
        tmpl_col = min_c if is_vert else None
        # Find all valid stamp positions
        positions = []
        for r in range(H - shape_h + 1):
            for c in range(W - shape_w + 1):
                cells = [(r + dr, c + dc) for dr, dc in shape]
                if not all(raw_in[cr][cc] == 0 for cr, cc in cells):
                    continue
                if is_horiz and r != tmpl_row:
                    continue
                if is_vert and c != tmpl_col:
                    continue
                positions.append((r, c, cells))
        # Sort by isolation score (external 0-neighbor count, ascending)
        scored = []
        for r, c, cells in positions:
            cell_set = set(cells)
            ext = set()
            for cr, cc in cells:
                for dr, dc in ((-1, 0), (1, 0), (0, -1), (0, 1)):
                    nr, nc = cr + dr, cc + dc
                    if 0 <= nr < H and 0 <= nc < W:
                        if (nr, nc) not in cell_set and raw_in[nr][nc] == 0:
                            ext.add((nr, nc))
            scored.append((len(ext), r, c, cells))
        scored.sort(key=lambda x: (x[0], x[1], x[2]))
        # Progressive stamping
        output = [row[:] for row in raw_in]
        for _, r, c, cells in scored:
            if all(output[cr][cc] == 0 for cr, cc in cells):
                for cr, cc in cells:
                    output[cr][cc] = 2
        return output

    # ---- strategy 66: spiral from seed ------------------------------------

    def _try_spiral_from_seed(self, patterns, wm):
        """Grid with a single color-3 pixel (seed) and color-2 obstacles on
        bg 0. Output draws a rectangular spiral of 3s outward from the seed.
        Arm lengths: 2,2,4,4,6,6,... Directions: up,right,down,left.
        Stops entire spiral when hitting a 2 or an already-drawn cell from
        a non-adjacent arm. 2-pixels preserved unchanged.
        Category: geometric construction / rectangular spiral."""
        task = wm.task
        if task is None:
            return None

        for pair in task.example_pairs:
            g0, g1 = pair.input_grid, pair.output_grid
            if g0 is None or g1 is None:
                return None
            raw_in, raw_out = g0.raw, g1.raw
            H, W = len(raw_in), len(raw_in[0])
            if H != len(raw_out) or W != len(raw_out[0]):
                return None
            # Find seed (single 3-pixel)
            seeds = [(r, c) for r in range(H) for c in range(W) if raw_in[r][c] == 3]
            if len(seeds) != 1:
                return None
            # Check that non-seed, non-obstacle cells are 0
            for r in range(H):
                for c in range(W):
                    if raw_in[r][c] not in (0, 2, 3):
                        return None
            # Generate spiral and compare
            expected = self._generate_spiral(raw_in, seeds[0], H, W)
            if expected != raw_out:
                return None

        return {"type": "spiral_from_seed", "confidence": 1.0}

    @staticmethod
    def _generate_spiral(raw_in, seed, H, W):
        """Generate the rectangular spiral output.
        Arms: length 2,2,4,4,6,6,... Dirs: up,right,down,left.
        OOB cells are skipped but cursor still moves theoretically.
        Stops on obstacle (2) or self-collision."""
        grid = [row[:] for row in raw_in]
        sr, sc = seed
        grid[sr][sc] = 3
        drawn = set()
        drawn.add((sr, sc))

        dirs = [(-1, 0), (0, 1), (1, 0), (0, -1)]
        cr, cc = sr, sc
        arm_idx = 0
        consecutive_no_draw = 0

        while arm_idx < 200:
            arm_len = 2 * ((arm_idx // 2) + 1)
            d = arm_idx % 4
            dr, dc = dirs[d]
            drew_any = False
            hit_stop = False

            for step in range(arm_len):
                nr, nc = cr + dr, cc + dc
                if 0 <= nr < H and 0 <= nc < W:
                    if raw_in[nr][nc] == 2:
                        hit_stop = True
                        break
                    if (nr, nc) in drawn:
                        hit_stop = True
                        break
                    grid[nr][nc] = 3
                    drawn.add((nr, nc))
                    drew_any = True
                # Always advance cursor (even if OOB/skipped)
                cr, cc = nr, nc

            if hit_stop:
                break
            if drew_any:
                consecutive_no_draw = 0
            else:
                consecutive_no_draw += 1
                if consecutive_no_draw >= 8:
                    break
            arm_idx += 1

        return grid

    # ---- strategy 70: separator sequence reflect ----------------------------

    def _try_separator_sequence_reflect(self, patterns, wm):
        """Grid divided by a full-row or full-column separator. Each side has
        a line of colored dots. The 'moving' side's dots get redistributed:
        matching dots → adjacent to separator, differing → far edge.
        Category: sequence comparison / spatial reflection."""
        task = wm.task
        if task is None:
            return None
        for pair in task.example_pairs:
            g0, g1 = pair.input_grid, pair.output_grid
            if g0 is None or g1 is None:
                return None
            raw_in, raw_out = g0.raw, g1.raw
            H, W = len(raw_in), len(raw_in[0])
            if H != len(raw_out) or W != len(raw_out[0]):
                return None
            info = self._detect_sep_reflect(raw_in)
            if info is None:
                return None
            expected = self._apply_sep_reflect(raw_in, info)
            if expected != raw_out:
                return None
        return {"type": "separator_sequence_reflect", "confidence": 1.0}

    @staticmethod
    def _detect_sep_reflect(raw):
        """Detect a separator (full row/col of one color) with dot lines on
        each side. Returns detection info dict or None."""
        H, W = len(raw), len(raw[0])
        from collections import Counter

        def section_bg(rows, cols, exclude):
            cnt = Counter()
            for r in rows:
                for c in cols:
                    v = raw[r][c]
                    if v not in exclude:
                        cnt[v] += 1
            return cnt.most_common(1)[0][0] if cnt else None

        def dot_line_row(rows, cols, bg, exclude):
            found = []
            for r in rows:
                for c in cols:
                    v = raw[r][c]
                    if v != bg and v not in exclude:
                        found.append(r)
                        break
            return found[0] if len(found) == 1 else None

        def dot_line_col(rows, cols, bg, exclude):
            found = []
            for c in cols:
                for r in rows:
                    v = raw[r][c]
                    if v != bg and v not in exclude:
                        found.append(c)
                        break
            return found[0] if len(found) == 1 else None

        def dots_in_row(row, cols, bg, exclude):
            d = {}
            for c in cols:
                v = raw[row][c]
                if v != bg and v not in exclude:
                    d[c] = v
            return d

        def dots_in_col(col, rows, bg, exclude):
            d = {}
            for r in rows:
                v = raw[r][col]
                if v != bg and v not in exclude:
                    d[r] = v
            return d

        # Try row separators
        for r in range(1, H - 1):
            if len(set(raw[r])) != 1:
                continue
            sc = raw[r][0]
            tr, br = list(range(0, r)), list(range(r + 1, H))
            ac = list(range(W))
            tb = section_bg(tr, ac, {sc})
            bb = section_bg(br, ac, {sc})
            if tb is None or bb is None:
                continue
            tdr = dot_line_row(tr, ac, tb, {sc})
            bdr = dot_line_row(br, ac, bb, {sc})
            if tdr is None or bdr is None:
                continue
            td = dots_in_row(tdr, ac, tb, {sc})
            bd = dots_in_row(bdr, ac, bb, {sc})
            if not td or not bd or set(td.keys()) != set(bd.keys()):
                continue
            tdist, bdist = r - tdr, bdr - r
            if tdist > bdist:
                mv = 'a'
            elif bdist > tdist:
                mv = 'b'
            else:
                mv = 'a' if r <= H - r - 1 else 'b'
            return {
                'axis': 'row', 'sep': r, 'sc': sc,
                'a': {'bg': tb, 'dl': tdr, 'dots': td,
                      'near': r - 1, 'far': 0},
                'b': {'bg': bb, 'dl': bdr, 'dots': bd,
                      'near': r + 1, 'far': H - 1},
                'mv': mv,
            }

        # Try column separators
        for c in range(1, W - 1):
            if len(set(raw[r][c] for r in range(H))) != 1:
                continue
            sc = raw[0][c]
            lc, rc = list(range(0, c)), list(range(c + 1, W))
            ar = list(range(H))
            lb = section_bg(ar, lc, {sc})
            rb = section_bg(ar, rc, {sc})
            if lb is None or rb is None:
                continue
            ldc = dot_line_col(ar, lc, lb, {sc})
            rdc = dot_line_col(ar, rc, rb, {sc})
            if ldc is None or rdc is None:
                continue
            ld = dots_in_col(ldc, ar, lb, {sc})
            rd = dots_in_col(rdc, ar, rb, {sc})
            if not ld or not rd or set(ld.keys()) != set(rd.keys()):
                continue
            ldist, rdist = c - ldc, rdc - c
            if ldist > rdist:
                mv = 'a'
            elif rdist > ldist:
                mv = 'b'
            else:
                mv = 'a' if c <= W - c - 1 else 'b'
            return {
                'axis': 'col', 'sep': c, 'sc': sc,
                'a': {'bg': lb, 'dl': ldc, 'dots': ld,
                      'near': c - 1, 'far': 0},
                'b': {'bg': rb, 'dl': rdc, 'dots': rd,
                      'near': c + 1, 'far': W - 1},
                'mv': mv,
            }

        return None

    @staticmethod
    def _apply_sep_reflect(raw, info):
        """Apply the separator sequence reflect transformation."""
        H, W = len(raw), len(raw[0])
        out = [row[:] for row in raw]
        ms = info[info['mv']]          # moving side
        fs = info['b' if info['mv'] == 'a' else 'a']  # fixed side
        bg = ms['bg']
        near, far = ms['near'], ms['far']
        m_dots, f_dots = ms['dots'], fs['dots']

        if info['axis'] == 'row':
            dl = ms['dl']
            for c in range(W):
                if out[dl][c] != info['sc']:
                    out[dl][c] = bg
            for pos, mv in m_dots.items():
                fv = f_dots.get(pos)
                if mv == fv:
                    out[near][pos] = mv
                else:
                    out[far][pos] = mv
        else:
            dl = ms['dl']
            for r in range(H):
                if out[r][dl] != info['sc']:
                    out[r][dl] = bg
            for pos, mv in m_dots.items():
                fv = f_dots.get(pos)
                if mv == fv:
                    out[pos][near] = mv
                else:
                    out[pos][far] = mv

        return out

    # ---- strategy 71: stamp tile toward bar --------------------------------

    def _try_stamp_tile_toward_bar(self, patterns, wm):
        """
        Detect: bg-colored grid with 3×3 'stamps' (uniform border color B,
        different center color C) and large solid-color rectangular 'bars'.
        Each stamp's center color matches a bar's color. The stamp tiles
        repeatedly from its position toward the matching bar, stopping when
        a copy reaches the bar's near edge.
        Category: directional pattern tiling / stamp-bar association.
        """
        try:
            return self._try_stamp_tile_toward_bar_inner(patterns, wm)
        except Exception:
            return None

    def _try_stamp_tile_toward_bar_inner(self, patterns, wm):
        task = wm.task
        if not task or not task.example_pairs:
            return None

        # Verify size preserved
        for pair in task.example_pairs:
            g0, g1 = pair.input_grid, pair.output_grid
            if not g0 or not g1:
                return None
            if len(g0.raw) != len(g1.raw) or len(g0.raw[0]) != len(g1.raw[0]):
                return None

        raw0 = task.example_pairs[0].input_grid.raw
        H, W = len(raw0), len(raw0[0])
        if H < 6 or W < 6:
            return None

        # Find bg color
        color_counts = {}
        for r in range(H):
            for c in range(W):
                v = raw0[r][c]
                color_counts[v] = color_counts.get(v, 0) + 1
        bg = max(color_counts, key=color_counts.get)

        # Find stamps: 3×3 with uniform non-bg border and different non-bg center
        stamps = self._find_stamps(raw0, bg)
        if not stamps:
            return None

        # Find bars: large rectangular solid-color regions (non-bg)
        bars = self._find_bars(raw0, bg, stamps)
        if not bars:
            return None

        # Match stamps to bars (center color = bar color)
        matched = []
        for stamp in stamps:
            for bar in bars:
                if stamp['center_color'] == bar['color']:
                    matched.append((stamp, bar))
                    break

        if len(matched) != len(stamps):
            return None

        # Validate on all training examples
        for pair in task.example_pairs:
            g0, g1 = pair.input_grid, pair.output_grid
            predicted = self._apply_stamp_tile_grid(g0.raw)
            if predicted is None or predicted != g1.raw:
                return None

        return {"type": "stamp_tile_toward_bar", "confidence": 1.0}

    def _find_stamps(self, raw, bg):
        """Find all 3×3 stamps with uniform border and different center."""
        H, W = len(raw), len(raw[0])
        stamps = []
        used = set()
        for r in range(H - 2):
            for c in range(W - 2):
                border_cells = [
                    raw[r][c], raw[r][c+1], raw[r][c+2],
                    raw[r+1][c], raw[r+1][c+2],
                    raw[r+2][c], raw[r+2][c+1], raw[r+2][c+2],
                ]
                center = raw[r+1][c+1]
                if center == bg:
                    continue
                border_color = border_cells[0]
                if border_color == bg or border_color == center:
                    continue
                if all(b == border_color for b in border_cells):
                    key = (r, c)
                    if key not in used:
                        used.add(key)
                        stamps.append({
                            'row': r, 'col': c,
                            'border_color': border_color,
                            'center_color': center,
                        })
        return stamps

    def _find_bars(self, raw, bg, stamps):
        """Find large solid-color rectangular regions (bars)."""
        H, W = len(raw), len(raw[0])
        # Mark stamp cells to exclude
        stamp_cells = set()
        for s in stamps:
            for dr in range(3):
                for dc in range(3):
                    stamp_cells.add((s['row'] + dr, s['col'] + dc))

        # Find connected components of each non-bg color (excluding stamp cells)
        color_cells = {}
        for r in range(H):
            for c in range(W):
                if (r, c) in stamp_cells:
                    continue
                v = raw[r][c]
                if v == bg:
                    continue
                color_cells.setdefault(v, []).append((r, c))

        bars = []
        for color, cells in color_cells.items():
            if len(cells) < 4:
                continue
            # Check if cells form a rectangle
            rows = [r for r, c in cells]
            cols = [c for r, c in cells]
            r_min, r_max = min(rows), max(rows)
            c_min, c_max = min(cols), max(cols)
            expected = (r_max - r_min + 1) * (c_max - c_min + 1)
            if expected == len(cells):
                bars.append({
                    'color': color,
                    'r_min': r_min, 'r_max': r_max,
                    'c_min': c_min, 'c_max': c_max,
                })
        return bars

    @staticmethod
    def _apply_stamp_tile_grid(raw):
        """Apply stamp-tile-toward-bar transformation to a raw grid."""
        H, W = len(raw), len(raw[0])
        # Find bg
        cc = {}
        for r in range(H):
            for c in range(W):
                v = raw[r][c]
                cc[v] = cc.get(v, 0) + 1
        bg = max(cc, key=cc.get)

        # Find stamps
        stamps = []
        for r in range(H - 2):
            for c in range(W - 2):
                border_cells = [
                    raw[r][c], raw[r][c+1], raw[r][c+2],
                    raw[r+1][c], raw[r+1][c+2],
                    raw[r+2][c], raw[r+2][c+1], raw[r+2][c+2],
                ]
                center = raw[r+1][c+1]
                if center == bg:
                    continue
                bc = border_cells[0]
                if bc == bg or bc == center:
                    continue
                if all(b == bc for b in border_cells):
                    stamps.append({
                        'row': r, 'col': c,
                        'border_color': bc,
                        'center_color': center,
                        'pattern': [
                            [raw[r][c], raw[r][c+1], raw[r][c+2]],
                            [raw[r+1][c], raw[r+1][c+1], raw[r+1][c+2]],
                            [raw[r+2][c], raw[r+2][c+1], raw[r+2][c+2]],
                        ],
                    })
        if not stamps:
            return None

        # Find bars
        stamp_cells = set()
        for s in stamps:
            for dr in range(3):
                for dc in range(3):
                    stamp_cells.add((s['row'] + dr, s['col'] + dc))

        color_cells = {}
        for r in range(H):
            for c in range(W):
                if (r, c) in stamp_cells:
                    continue
                v = raw[r][c]
                if v == bg:
                    continue
                color_cells.setdefault(v, []).append((r, c))

        bars = []
        for color, cells in color_cells.items():
            if len(cells) < 4:
                continue
            rows_l = [r for r, c in cells]
            cols_l = [c for r, c in cells]
            r_min, r_max = min(rows_l), max(rows_l)
            c_min, c_max = min(cols_l), max(cols_l)
            expected = (r_max - r_min + 1) * (c_max - c_min + 1)
            if expected == len(cells):
                bars.append({
                    'color': color,
                    'r_min': r_min, 'r_max': r_max,
                    'c_min': c_min, 'c_max': c_max,
                })

        if not bars:
            return None

        # Build output
        out = [row[:] for row in raw]

        for stamp in stamps:
            # Find matching bar
            bar = None
            for b in bars:
                if b['color'] == stamp['center_color']:
                    bar = b
                    break
            if bar is None:
                continue

            sr, sc = stamp['row'], stamp['col']
            pat = stamp['pattern']

            # Determine direction
            # Check if bar is to the right, left, below, or above
            if bar['c_min'] > sc + 2:
                # Bar to the right → tile right
                direction = 'right'
            elif bar['c_max'] < sc:
                # Bar to the left → tile left
                direction = 'left'
            elif bar['r_min'] > sr + 2:
                # Bar below → tile down
                direction = 'down'
            elif bar['r_max'] < sr:
                # Bar above → tile up
                direction = 'up'
            else:
                continue

            if direction == 'right':
                # Tile from stamp col rightward until copy covers bar left edge
                col = sc
                while col + 2 < bar['c_min']:
                    col += 3
                # Now tile from sc to col+2
                c = sc
                while c <= col + 2:
                    idx = (c - sc) % 3
                    for dr in range(3):
                        if 0 <= sr + dr < H and 0 <= c < W:
                            out[sr + dr][c] = pat[dr][idx]
                    c += 1
            elif direction == 'left':
                # Tile from stamp col leftward until copy covers bar right edge
                col = sc
                while col > bar['c_max']:
                    col -= 3
                # Now tile from col to sc+2
                c = col
                while c <= sc + 2:
                    idx = (c - sc) % 3
                    if idx < 0:
                        idx += 3
                    for dr in range(3):
                        if 0 <= sr + dr < H and 0 <= c < W:
                            out[sr + dr][c] = pat[dr][idx]
                    c += 1
            elif direction == 'down':
                # Tile from stamp row downward until copy covers bar top row
                row = sr
                while row + 2 < bar['r_min']:
                    row += 3
                r = sr
                while r <= row + 2:
                    idx = (r - sr) % 3
                    for dc in range(3):
                        if 0 <= r < H and 0 <= sc + dc < W:
                            out[r][sc + dc] = pat[idx][dc]
                    r += 1
            elif direction == 'up':
                # Tile from stamp row upward until copy covers bar bottom row
                row = sr
                while row > bar['r_max']:
                    row -= 3
                r = row
                while r <= sr + 2:
                    idx = (r - sr) % 3
                    if idx < 0:
                        idx += 3
                    for dc in range(3):
                        if 0 <= r < H and 0 <= sc + dc < W:
                            out[r][sc + dc] = pat[idx][dc]
                    r += 1

        return out

    # ---- strategy 72: shape jigsaw assemble --------------------------------

    def _try_shape_jigsaw_assemble(self, patterns, wm):
        """
        Detect: input has several small colored shapes on bg=0. The output
        is a compact filled rectangle containing all shapes assembled together
        (like jigsaw pieces). Shapes may be rotated to fit.
        Category: shape assembly / jigsaw packing.
        """
        try:
            return self._try_shape_jigsaw_assemble_inner(patterns, wm)
        except Exception:
            return None

    def _try_shape_jigsaw_assemble_inner(self, patterns, wm):
        task = wm.task
        if not task or not task.example_pairs:
            return None

        for pair in task.example_pairs:
            g0, g1 = pair.input_grid, pair.output_grid
            if not g0 or not g1:
                return None
            raw_in = g0.raw
            raw_out = g1.raw

            # Input must be larger than output
            if len(raw_in) * len(raw_in[0]) <= len(raw_out) * len(raw_out[0]):
                return None

            # Output must be fully filled (no bg=0 cells)
            for row in raw_out:
                for v in row:
                    if v == 0:
                        return None

            # Count non-zero cells in input must equal output area
            nz_count = sum(1 for r in raw_in for v in r if v != 0)
            out_area = len(raw_out) * len(raw_out[0])
            if nz_count != out_area:
                return None

        # Validate: try solving each training example
        for pair in task.example_pairs:
            result = self._solve_jigsaw(pair.input_grid.raw)
            if result is None or result != pair.output_grid.raw:
                return None

        return {"type": "shape_jigsaw_assemble", "confidence": 1.0}

    @staticmethod
    def _extract_shapes(raw):
        """Extract connected components of non-zero colors."""
        H, W = len(raw), len(raw[0])
        visited = set()
        shapes = []
        for r in range(H):
            for c in range(W):
                if raw[r][c] != 0 and (r, c) not in visited:
                    # BFS to find connected component
                    color = raw[r][c]
                    component = []
                    queue = [(r, c)]
                    visited.add((r, c))
                    while queue:
                        cr, cc = queue.pop(0)
                        component.append((cr, cc, raw[cr][cc]))
                        for dr, dc in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                            nr, nc = cr + dr, cc + dc
                            if 0 <= nr < H and 0 <= nc < W and (nr, nc) not in visited and raw[nr][nc] != 0:
                                visited.add((nr, nc))
                                queue.append((nr, nc))
                    # Normalize: relative to top-left corner
                    min_r = min(p[0] for p in component)
                    min_c = min(p[1] for p in component)
                    shape = [(p[0] - min_r, p[1] - min_c, p[2]) for p in component]
                    shapes.append(shape)
        return shapes

    @staticmethod
    def _shape_orientations(shape):
        """Generate all 8 orientations (4 rotations × 2 reflections).
        Original orientation is first in the returned list.
        Accepts either (r, c) or (r, c, v) tuples."""
        # Detect tuple width
        sample = next(iter(shape))
        has_value = len(sample) == 3

        seen = set()
        result = []

        if has_value:
            def normalize(cells):
                min_r = min(r for r, c, v in cells)
                min_c = min(c for r, c, v in cells)
                return tuple(sorted((r - min_r, c - min_c, v) for r, c, v in cells))

            def rotate90(cells):
                return [(c, -r, v) for r, c, v in cells]

            def reflect(cells):
                return [(-r, c, v) for r, c, v in cells]
        else:
            def normalize(cells):
                min_r = min(r for r, c in cells)
                min_c = min(c for r, c in cells)
                return frozenset((r - min_r, c - min_c) for r, c in cells)

            def rotate90(cells):
                return [(c, -r) for r, c in cells]

            def reflect(cells):
                return [(-r, c) for r, c in cells]

        current = list(shape)
        for _ in range(4):
            n = normalize(current)
            if n not in seen:
                seen.add(n)
                result.append(list(n) if has_value else n)
            n2 = normalize(reflect(current))
            if n2 not in seen:
                seen.add(n2)
                result.append(list(n2) if has_value else n2)
            current = rotate90(current)

        return result

    @staticmethod
    def _solve_jigsaw(raw):
        """Solve the jigsaw assembly problem."""
        shapes = GeneralizeOperator._extract_shapes(raw)
        if not shapes:
            return None

        # Sort shapes by size descending (largest first for better pruning),
        # then by minimum color ascending (deterministic tie-breaking)
        shapes.sort(key=lambda s: (-len(s), min(v for _, _, v in s)))

        total_cells = sum(len(s) for s in shapes)

        # Determine possible output dimensions
        dims = []
        for h in range(1, total_cells + 1):
            if total_cells % h == 0:
                w = total_cells // h
                dims.append((h, w))

        # Generate all orientations for each shape (original first)
        all_orientations = []
        for shape in shapes:
            orients = GeneralizeOperator._shape_orientations(shape)
            all_orientations.append(orients)

        # Try each dimension
        for out_h, out_w in dims:
            # Backtracking search
            grid = [[0] * out_w for _ in range(out_h)]
            result = GeneralizeOperator._backtrack_jigsaw(
                grid, out_h, out_w, all_orientations, 0
            )
            if result is not None:
                return result

        return None

    @staticmethod
    def _backtrack_jigsaw(grid, H, W, all_orientations, shape_idx):
        """Backtracking to place shapes into grid."""
        if shape_idx == len(all_orientations):
            # All shapes placed, check grid is fully filled
            for r in range(H):
                for c in range(W):
                    if grid[r][c] == 0:
                        return None
            return [row[:] for row in grid]

        for orient in all_orientations[shape_idx]:
            # Get bounding box of this orientation
            max_r = max(r for r, c, v in orient)
            max_c = max(c for r, c, v in orient)

            # Try each position
            for pr in range(H - max_r):
                for pc in range(W - max_c):
                    # Check if shape fits
                    fits = True
                    for r, c, v in orient:
                        if grid[pr + r][pc + c] != 0:
                            fits = False
                            break
                    if not fits:
                        continue

                    # Place shape
                    for r, c, v in orient:
                        grid[pr + r][pc + c] = v

                    result = GeneralizeOperator._backtrack_jigsaw(
                        grid, H, W, all_orientations, shape_idx + 1
                    )
                    if result is not None:
                        return result

                    # Undo placement
                    for r, c, v in orient:
                        grid[pr + r][pc + c] = 0

        return None

    # ---- strategy 73: stamp shape match ------------------------------------

    def _try_stamp_shape_match(self, patterns, wm):
        """
        Detect: grid of two main colors (bg_color and fg_color) plus a small
        connected component of a third marker color. The marker shape is
        "stamped" onto every location where bg_color cells form the same shape.
        Category: shape-template stamping / pattern replication.
        """
        task = wm.task
        if task is None:
            return None
        examples = task.example_pairs
        if not examples:
            return None

        # Validate on first example, then verify on all
        raw0_in = examples[0].input_grid.raw
        raw0_out = examples[0].output_grid.raw
        H, W = len(raw0_in), len(raw0_in[0])

        # Find all colors in input
        colors_in = set()
        for r in range(H):
            for c in range(W):
                colors_in.add(raw0_in[r][c])

        if len(colors_in) != 3:
            return None

        # Find marker color: appears in input, and some cells change to it in output
        # Marker color cells in input are kept, and new marker cells appear in output
        marker_color = None
        bg_color = None
        fg_color = None

        # Count occurrences
        color_counts = {}
        for r in range(H):
            for c in range(W):
                v = raw0_in[r][c]
                color_counts[v] = color_counts.get(v, 0) + 1

        # The marker is the rarest non-bg color, and bg is the one that gets replaced
        sorted_colors = sorted(color_counts.items(), key=lambda x: x[1])
        # Expect: marker (least), then two others
        if len(sorted_colors) != 3:
            return None

        candidate_marker = sorted_colors[0][0]

        # Check output has same dimensions and marker cells appear in new places
        if len(raw0_out) != H or len(raw0_out[0]) != W:
            return None

        # Find which color gets replaced by marker in output
        replaced_color = None
        for r in range(H):
            for c in range(W):
                if raw0_in[r][c] != raw0_out[r][c]:
                    if raw0_out[r][c] == candidate_marker:
                        replaced_color = raw0_in[r][c]
                        break
            if replaced_color is not None:
                break

        if replaced_color is None:
            return None

        marker_color = candidate_marker
        bg_color = replaced_color
        fg_color = None
        for clr in colors_in:
            if clr != marker_color and clr != bg_color:
                fg_color = clr
                break

        if fg_color is None:
            return None

        # Verify all changes are bg_color -> marker_color
        for r in range(H):
            for c in range(W):
                if raw0_in[r][c] != raw0_out[r][c]:
                    if raw0_in[r][c] != bg_color or raw0_out[r][c] != marker_color:
                        return None

        # Extract marker shape (connected component of marker_color)
        marker_cells = set()
        for r in range(H):
            for c in range(W):
                if raw0_in[r][c] == marker_color:
                    marker_cells.add((r, c))

        if not marker_cells or len(marker_cells) < 2:
            return None

        # Get relative offsets of the marker shape (need not be 4-connected)
        marker_list = sorted(marker_cells)
        origin_r, origin_c = marker_list[0]
        shape_offsets = tuple(sorted((r - origin_r, c - origin_c) for r, c in marker_list))

        # Now apply the rule to input and check it produces correct output
        def apply_stamp(raw_grid):
            h = len(raw_grid)
            w = len(raw_grid[0])
            out = [row[:] for row in raw_grid]
            # Find marker cells in this grid
            mc = set()
            for rr in range(h):
                for cc in range(w):
                    if raw_grid[rr][cc] == marker_color:
                        mc.add((rr, cc))
            # Get shape offsets from this grid's marker
            mc_sorted = sorted(mc)
            if not mc_sorted:
                return out
            or_r, or_c = mc_sorted[0]
            s_off = tuple(sorted((rr - or_r, cc - or_c) for rr, cc in mc_sorted))
            if s_off != shape_offsets:
                return None  # Shape mismatch
            # Scan for all placements on bg_color cells
            for r in range(h):
                for c in range(w):
                    fits = True
                    for dr, dc in shape_offsets:
                        nr, nc = r + dr, c + dc
                        if nr < 0 or nr >= h or nc < 0 or nc >= w:
                            fits = False
                            break
                        if raw_grid[nr][nc] != bg_color:
                            fits = False
                            break
                    if fits:
                        for dr, dc in shape_offsets:
                            out[r + dr][c + dc] = marker_color
            return out

        # Verify on all examples
        for pair in examples:
            inp = pair.input_grid.raw
            exp = pair.output_grid.raw
            got = apply_stamp(inp)
            if got is None or got != exp:
                return None

        return {
            "type": "stamp_shape_match",
            "marker_color": marker_color,
            "bg_color": bg_color,
            "shape_offsets": [list(o) for o in shape_offsets],
            "confidence": 1.0,
        }

    @staticmethod
    def _get_connected_components(cells):
        """Return list of sets, each a 4-connected component of (r,c) positions."""
        remaining = set(cells)
        components = []
        while remaining:
            seed = next(iter(remaining))
            component = set()
            stack = [seed]
            while stack:
                pos = stack.pop()
                if pos in component:
                    continue
                component.add(pos)
                remaining.discard(pos)
                r, c = pos
                for dr, dc in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                    nb = (r + dr, c + dc)
                    if nb in remaining:
                        stack.append(nb)
            components.append(component)
        return components

    # ---- strategy 74: frame hole recolor -----------------------------------

    def _try_frame_hole_recolor(self, patterns, wm):
        """
        Detect: a frame of 1-cells with rectangular enclosed holes at top.
        Below: scattered shapes of 5-cells. Shapes whose columns overlap with
        a rectangle are checked against THAT rectangle's hole shape; shapes
        with no overlap are checked against ALL holes. If a shape contains
        the hole as a sub-pattern → recolored to 2. Otherwise stays 5.
        Category: frame-based shape classification / template matching.
        """
        task = wm.task
        if task is None:
            return None
        examples = task.example_pairs
        if not examples:
            return None

        # Quick structural check on first example
        raw_in = examples[0].input_grid.raw
        raw_out = examples[0].output_grid.raw
        H, W = len(raw_in), len(raw_in[0])
        oH, oW = len(raw_out), len(raw_out[0]) if raw_out else 0

        # Input/output must be same size
        if H != oH or W != oW:
            return None

        # Must have colors 0, 1, 5 in input and 0, 1, 2, 5 in output
        colors_in = set()
        colors_out = set()
        for r in range(H):
            for c in range(W):
                colors_in.add(raw_in[r][c])
                colors_out.add(raw_out[r][c])

        if 1 not in colors_in or 5 not in colors_in:
            return None
        if 2 not in colors_out:
            return None

        # All changes must be 5 → 2
        for r in range(H):
            for c in range(W):
                if raw_in[r][c] != raw_out[r][c]:
                    if raw_in[r][c] != 5 or raw_out[r][c] != 2:
                        return None

        def solve_frame_hole(raw):
            """Apply the frame-hole-recolor rule to a grid. Returns predicted output."""
            h = len(raw)
            w = len(raw[0])

            # Find frame (1-cells) rows
            frame_rows = set()
            for r in range(h):
                for c in range(w):
                    if raw[r][c] == 1:
                        frame_rows.add(r)
            if not frame_rows:
                return None

            frame_bottom = max(frame_rows)

            # Find all 1-cells
            one_cells = set()
            for r in range(h):
                for c in range(w):
                    if raw[r][c] == 1:
                        one_cells.add((r, c))

            # Find enclosed 0-cells (holes) within the frame region
            # These are 0-cells in frame rows bounded by 1-cells
            frame_top = min(frame_rows)

            # Find rectangular holes: 0-cells in frame region enclosed by 1-cells
            # Use flood-fill from grid border to find exterior 0-cells
            exterior = set()
            border_seeds = []
            for r in range(h):
                for c in range(w):
                    if raw[r][c] == 0 and (r == 0 or r == h - 1 or c == 0 or c == w - 1):
                        border_seeds.append((r, c))

            stack = list(border_seeds)
            visited = set()
            while stack:
                pos = stack.pop()
                if pos in visited:
                    continue
                visited.add(pos)
                r, c = pos
                if raw[r][c] != 0:
                    continue
                exterior.add(pos)
                for dr, dc in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                    nr, nc = r + dr, c + dc
                    if 0 <= nr < h and 0 <= nc < w and (nr, nc) not in visited:
                        stack.append((nr, nc))

            # Interior 0-cells = 0-cells in frame rows that are NOT exterior
            # But holes may also connect downward through the frame opening
            # So instead: find 0-cells within frame rows bounded by 1-walls
            hole_cells = set()
            for r in range(frame_top, frame_bottom + 1):
                for c in range(w):
                    if raw[r][c] == 0:
                        # Check if bounded by 1-cells on left and right in same row
                        has_left = any(raw[r][lc] == 1 for lc in range(c))
                        has_right = any(raw[r][rc] == 1 for rc in range(c + 1, w))
                        # Check bounded above (in some row)
                        has_above = any(raw[ar][c] == 1 for ar in range(frame_top, r))
                        if has_left and has_right and has_above:
                            hole_cells.add((r, c))

            if not hole_cells:
                return None

            # Group hole cells into connected components → each is a "rectangle hole"
            hole_ccs = GeneralizeOperator._get_connected_components(hole_cells)

            # For each hole CC, get its column range, wall range, and shape
            rectangles = []
            for hcc in hole_ccs:
                cols = set(c for _, c in hcc)
                min_r = min(r for r, _ in hcc)
                min_c = min(c for _, c in hcc)
                shape = frozenset((r - min_r, c - min_c) for r, c in hcc)
                hole_col_range = (min(cols), max(cols))
                # Wall range: hole cols ± 1
                wall_col_range = (min(cols) - 1, max(cols) + 1)
                hole_width = max(cols) - min(cols) + 1
                rectangles.append({
                    "hole_col_range": hole_col_range,
                    "wall_col_range": wall_col_range,
                    "hole_width": hole_width,
                    "shape": shape,
                })

            if not rectangles:
                return None

            # Find 5-groups below the frame
            five_cells = set()
            for r in range(frame_bottom + 1, h):
                for c in range(w):
                    if raw[r][c] == 5:
                        five_cells.add((r, c))

            if not five_cells:
                return None

            five_groups = GeneralizeOperator._get_connected_components(five_cells)

            # For each 5-group, determine if it should be recolored
            out = [row[:] for row in raw]
            for group in five_groups:
                group_cols = set(c for _, c in group)
                group_width = max(group_cols) - min(group_cols) + 1
                min_r = min(r for r, _ in group)
                min_c = min(c for _, c in group)
                group_shape = frozenset((r - min_r, c - min_c) for r, c in group)

                # Check if group is entirely within any rectangle's wall range
                enclosing_rect = None
                for rect in rectangles:
                    wmin, wmax = rect["wall_col_range"]
                    if all(wmin <= c <= wmax for c in group_cols):
                        enclosing_rect = rect
                        break

                should_recolor = False
                if enclosing_rect is not None:
                    # Group is within a rectangle — check width match + containment
                    if group_width == enclosing_rect["hole_width"]:
                        if GeneralizeOperator._shape_contains_subshape(
                            group_shape, enclosing_rect["shape"]
                        ):
                            should_recolor = True
                else:
                    # Group outside all rectangles — check containment vs any hole
                    for rect in rectangles:
                        if GeneralizeOperator._shape_contains_subshape(
                            group_shape, rect["shape"]
                        ):
                            should_recolor = True
                            break

                if should_recolor:
                    for r, c in group:
                        out[r][c] = 2

            return out

        # Verify on all examples
        for pair in examples:
            inp = pair.input_grid.raw
            exp = pair.output_grid.raw
            got = solve_frame_hole(inp)
            if got is None or got != exp:
                return None

        return {
            "type": "frame_hole_recolor",
            "confidence": 1.0,
        }

    @staticmethod
    def _shape_contains_subshape(big_shape, small_shape):
        """Check if big_shape contains small_shape as a translated sub-pattern."""
        if len(small_shape) > len(big_shape):
            return False
        if not small_shape:
            return True
        # Normalize small_shape
        sm_list = sorted(small_shape)
        sm_origin = sm_list[0]
        sm_norm = frozenset((r - sm_origin[0], c - sm_origin[1]) for r, c in sm_list)

        # Try all possible translations: offset each cell in big_shape as origin
        big_list = sorted(big_shape)
        for br, bc in big_list:
            # If we place sm_norm origin at (br, bc), check all sm cells are in big
            all_in = True
            for dr, dc in sm_norm:
                if (br + dr, bc + dc) not in big_shape:
                    all_in = False
                    break
            if all_in:
                return True
        return False


    # ------------------------------------------------------------------
    # Strategy 75: L-shape corner complete
    # ------------------------------------------------------------------
    def _try_l_corner_complete(self, patterns, wm):
        """
        Detect: grid with bg=0 and L-shaped groups of 3 cells (one fg color).
        Each L occupies 3 cells of a 2x2 bounding box, leaving 1 corner empty.
        Output fills that empty corner with a mark color.
        Category: structural completion / L-shape corner detection.
        """
        task = wm.task
        if task is None:
            return None
        examples = task.example_pairs
        if not examples:
            return None

        raw_in = examples[0].input_grid.raw
        raw_out = examples[0].output_grid.raw
        H, W = len(raw_in), len(raw_in[0])

        # Same dimensions
        if len(raw_out) != H or len(raw_out[0]) != W:
            return None

        # Find fg color (non-zero) and mark color (added in output)
        in_colors = set()
        out_colors = set()
        for r in range(H):
            for c in range(W):
                if raw_in[r][c] != 0:
                    in_colors.add(raw_in[r][c])
                if raw_out[r][c] != 0:
                    out_colors.add(raw_out[r][c])

        if len(in_colors) != 1:
            return None
        fg_color = in_colors.pop()
        new_colors = out_colors - {fg_color}
        if len(new_colors) != 1:
            return None
        mark_color = new_colors.pop()

        # All fg cells must be preserved
        for r in range(H):
            for c in range(W):
                if raw_in[r][c] == fg_color and raw_out[r][c] != fg_color:
                    return None

        def find_l_corners(raw, fg):
            """Find connected components of fg, filter to L-shapes, return missing corners."""
            h, w = len(raw), len(raw[0])
            visited = [[False]*w for _ in range(h)]
            corners = []
            for sr in range(h):
                for sc in range(w):
                    if raw[sr][sc] == fg and not visited[sr][sc]:
                        # BFS to find component
                        comp = []
                        stack = [(sr, sc)]
                        visited[sr][sc] = True
                        while stack:
                            cr, cc = stack.pop()
                            comp.append((cr, cc))
                            for dr, dc in [(-1,0),(1,0),(0,-1),(0,1)]:
                                nr, nc = cr+dr, cc+dc
                                if 0 <= nr < h and 0 <= nc < w and not visited[nr][nc] and raw[nr][nc] == fg:
                                    visited[nr][nc] = True
                                    stack.append((nr, nc))
                        if len(comp) == 3:
                            # Check if it's an L in a 2x2 box
                            min_r = min(r for r,c in comp)
                            max_r = max(r for r,c in comp)
                            min_c = min(c for r,c in comp)
                            max_c = max(c for r,c in comp)
                            if max_r - min_r == 1 and max_c - min_c == 1:
                                comp_set = set(comp)
                                for cr in [min_r, max_r]:
                                    for cc in [min_c, max_c]:
                                        if (cr, cc) not in comp_set:
                                            corners.append((cr, cc))
            return corners

        # Validate on all examples
        for ex in examples:
            ri = ex.input_grid.raw
            ro = ex.output_grid.raw
            corners = find_l_corners(ri, fg_color)
            if not corners:
                return None
            # Check each corner becomes mark_color in output
            for cr, cc in corners:
                if ro[cr][cc] != mark_color:
                    return None
            # Check no other changes
            for r in range(len(ri)):
                for c in range(len(ri[0])):
                    if ri[r][c] != ro[r][c]:
                        if (r, c) not in corners:
                            return None

        return {"type": "l_corner_complete", "fg_color": fg_color, "mark_color": mark_color}

    # ------------------------------------------------------------------
    # Strategy 76: Quadrant locator
    # ------------------------------------------------------------------
    def _try_quadrant_locator(self, patterns, wm):
        """
        Detect: small grid (e.g. 4x4) mostly filled with bg_color, with scattered
        non-bg values including a target_color that appears exactly once. Output fills
        the 2x2 quadrant containing target_color with that color, rest becomes bg.
        Category: spatial localization / quadrant expansion.
        """
        task = wm.task
        if task is None:
            return None
        examples = task.example_pairs
        if not examples:
            return None

        raw_in0 = examples[0].input_grid.raw
        raw_out0 = examples[0].output_grid.raw
        H, W = len(raw_in0), len(raw_in0[0])

        # Must be same dimensions, even rows and cols (for quadrant split)
        if len(raw_out0) != H or len(raw_out0[0]) != W:
            return None
        if H % 2 != 0 or W % 2 != 0:
            return None

        # Output must have exactly 2 colors: bg_color filling 3 quadrants, target filling 1
        out_colors = set()
        for r in range(H):
            for c in range(W):
                out_colors.add(raw_out0[r][c])
        if len(out_colors) != 2:
            return None

        # Identify which color fills 3 quadrants (bg) vs 1 (target)
        half_r, half_c = H // 2, W // 2
        quadrant_colors = []
        for qr_start in [0, half_r]:
            for qc_start in [0, half_c]:
                qcolor = raw_out0[qr_start][qc_start]
                # Check quadrant is uniform
                uniform = True
                for r in range(qr_start, qr_start + half_r):
                    for c in range(qc_start, qc_start + half_c):
                        if raw_out0[r][c] != qcolor:
                            uniform = False
                            break
                    if not uniform:
                        break
                if not uniform:
                    return None
                quadrant_colors.append(qcolor)

        from collections import Counter
        qc_count = Counter(quadrant_colors)
        if len(qc_count) != 2:
            return None
        bg_color = qc_count.most_common(1)[0][0]
        target_color = [c for c in qc_count if c != bg_color][0]
        if qc_count[bg_color] != 3 or qc_count[target_color] != 1:
            return None

        # Validate on all examples
        for ex in examples:
            ri = ex.input_grid.raw
            ro = ex.output_grid.raw
            h, w = len(ri), len(ri[0])
            if h != H or w != W:
                return None
            # Find target_color position in input
            target_pos = None
            for r in range(h):
                for c in range(w):
                    if ri[r][c] == target_color:
                        if target_pos is not None:
                            return None  # target must appear exactly once
                        target_pos = (r, c)
            if target_pos is None:
                return None
            # Determine which quadrant
            tr, tc = target_pos
            qr = 0 if tr < half_r else half_r
            qc = 0 if tc < half_c else half_c
            # Verify output matches
            for r in range(h):
                for c in range(w):
                    expected = target_color if (qr <= r < qr + half_r and qc <= c < qc + half_c) else bg_color
                    if ro[r][c] != expected:
                        return None

        return {"type": "quadrant_locator", "bg_color": bg_color, "target_color": target_color,
                "half_r": half_r, "half_c": half_c}

    # ------------------------------------------------------------------
    # Strategy 77: Periodic pattern extend
    # ------------------------------------------------------------------
    def _try_periodic_pattern_extend(self, patterns, wm):
        """
        Detect: grid with a repeating tile pattern occupying most of the area,
        with a uniform border color filling the remaining edge (right cols,
        bottom rows, or L-shaped right+bottom). Output is same dimensions with
        the repeating tile extended to fill everything, shifted +1 column.
        Category: pattern completion / periodic fill.
        """
        task = wm.task
        if task is None:
            return None
        examples = task.example_pairs
        if not examples:
            return None

        def detect_border_and_tile(raw):
            """Detect border color, strip it, extract repeating tile. Returns (tile, border_color) or None."""
            h, w = len(raw), len(raw[0])

            # Find border color by checking right col and bottom row
            # Border must be a single uniform color on at least one edge
            border_color = None

            # Check rightmost column
            right_col = set(raw[r][w-1] for r in range(h))
            bottom_row = set(raw[h-1][c] for c in range(w))

            if len(right_col) == 1 and len(bottom_row) == 1 and right_col == bottom_row:
                border_color = right_col.pop()
            elif len(right_col) == 1:
                border_color = right_col.pop()
            elif len(bottom_row) == 1:
                border_color = bottom_row.pop()
            else:
                return None

            # Strip border columns from right
            core_w = w
            for c in range(w - 1, -1, -1):
                if all(raw[r][c] == border_color for r in range(h)):
                    core_w = c
                else:
                    break
            # Strip border rows from bottom
            core_h = h
            for r in range(h - 1, -1, -1):
                if all(raw[r][c] == border_color for c in range(w)):
                    core_h = r
                else:
                    break

            if core_h < 1 or core_w < 1:
                return None

            # The core is raw[0:core_h][0:core_w]
            core = [row[:core_w] for row in raw[:core_h]]

            # Border color must not appear in core
            for r in range(core_h):
                for c in range(core_w):
                    if core[r][c] == border_color:
                        return None

            # Detect column period from first row
            row0 = core[0]
            col_period = None
            for p in range(1, core_w + 1):
                if all(row0[c] == row0[c % p] for c in range(core_w)):
                    col_period = p
                    break
            if col_period is None:
                return None

            # Detect row period (how many rows before the column-start pattern repeats)
            row_period = None
            for rp in range(1, core_h + 1):
                match = True
                for r in range(core_h):
                    for c in range(core_w):
                        if core[r][c] != core[r % rp][c]:
                            match = False
                            break
                    if not match:
                        break
                if match:
                    row_period = rp
                    break
            if row_period is None:
                return None

            tile = [core[r][:col_period] for r in range(row_period)]
            return tile, border_color

        # Try to detect on first example
        result = detect_border_and_tile(examples[0].input_grid.raw)
        if result is None:
            return None
        tile, border_color = result
        tile_h = len(tile)
        tile_w = len(tile[0])

        # Validate: each example must have a border+tile, and output must match shifted tile
        for ex in examples:
            ri = ex.input_grid.raw
            ro = ex.output_grid.raw
            h, w = len(ri), len(ri[0])
            if len(ro) != h or len(ro[0]) != w:
                return None
            # Re-detect tile for this example (border color and tile dims may vary)
            res = detect_border_and_tile(ri)
            if res is None:
                return None
            ex_tile, ex_bc = res
            ex_th = len(ex_tile)
            ex_tw = len(ex_tile[0])
            # Verify output matches shifted tile
            for r in range(h):
                for c in range(w):
                    expected = ex_tile[r % ex_th][(c + 1) % ex_tw]
                    if ro[r][c] != expected:
                        return None

        return {"type": "periodic_pattern_extend"}

    # ---- strategy 78: cluster bbox border ------------------------------------

    def _try_cluster_bbox_border(self, patterns, wm):
        """
        Detect: scattered pixels of one color (marker_color) on background 0.
        Connected components (4-connected) of size >= 2 get a border of
        border_color drawn around their bounding box (1 cell outward, clipped).
        Isolated single pixels remain unchanged.
        Category: cluster detection / bounding box annotation.
        """
        task = wm.task
        if task is None:
            return None
        examples = task.example_pairs

        marker_color = None
        border_color = None

        for pair in examples:
            ri = pair.input_grid.raw
            ro = pair.output_grid.raw
            H, W = len(ri), len(ri[0])

            # Find non-zero colors in input
            in_colors = set()
            for r in range(H):
                for c in range(W):
                    if ri[r][c] != 0:
                        in_colors.add(ri[r][c])

            # Must have exactly one non-zero color in input
            if len(in_colors) != 1:
                return None
            mc = in_colors.pop()

            # Output must have exactly 2 non-zero colors (marker + border)
            out_colors = set()
            for r in range(H):
                for c in range(W):
                    if ro[r][c] != 0:
                        out_colors.add(ro[r][c])
            if mc not in out_colors or len(out_colors) != 2:
                return None
            bc = (out_colors - {mc}).pop()

            if marker_color is None:
                marker_color = mc
                border_color = bc
            elif mc != marker_color or bc != border_color:
                return None

            # Validate: find connected components of marker_color
            positions = set()
            for r in range(H):
                for c in range(W):
                    if ri[r][c] == marker_color:
                        positions.add((r, c))

            clusters = self._flood_components(positions)

            # Build expected output
            expected = [row[:] for row in ri]
            for cluster in clusters:
                if len(cluster) < 2:
                    continue
                min_r = min(r for r, c in cluster)
                max_r = max(r for r, c in cluster)
                min_c = min(c for r, c in cluster)
                max_c = max(c for r, c in cluster)
                # Draw border 1 cell outside bbox
                br0 = max(0, min_r - 1)
                br1 = min(H - 1, max_r + 1)
                bc0 = max(0, min_c - 1)
                bc1 = min(W - 1, max_c + 1)
                for r in range(br0, br1 + 1):
                    for c in range(bc0, bc1 + 1):
                        if expected[r][c] == 0:
                            # Only fill border ring, not interior
                            if r == br0 or r == br1 or c == bc0 or c == bc1:
                                expected[r][c] = border_color

            if expected != ro:
                return None

        return {"type": "cluster_bbox_border",
                "marker_color": marker_color,
                "border_color": border_color}

    def _flood_components(self, positions):
        """Find 4-connected components from a set of (r,c) positions."""
        remaining = set(positions)
        components = []
        while remaining:
            start = next(iter(remaining))
            comp = set()
            queue = [start]
            while queue:
                pos = queue.pop()
                if pos in comp:
                    continue
                if pos not in remaining:
                    continue
                comp.add(pos)
                remaining.discard(pos)
                r, c = pos
                for dr, dc in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                    nb = (r + dr, c + dc)
                    if nb in remaining:
                        queue.append(nb)
            components.append(comp)
        return components

    # ---- strategy 79: crop solid rect + flip ---------------------------------

    def _try_crop_rect_flip(self, patterns, wm):
        """
        Detect: input has a solid-colored rectangle (dominant color) with a
        minority pattern inside, on a zero background. Output = that rectangle
        cropped and horizontally flipped.
        Category: rectangle extraction + horizontal mirror.
        """
        task = wm.task
        if task is None:
            return None
        examples = task.example_pairs
        if len(examples) < 2:
            return None

        for pair in examples:
            ri = pair.input_grid.raw
            ro = pair.output_grid.raw
            H, W = len(ri), len(ri[0])
            oH, oW = len(ro), len(ro[0])

            # Find bounding box of all non-zero cells
            non_zero = [(r, c) for r in range(H) for c in range(W) if ri[r][c] != 0]
            if not non_zero:
                return None
            min_r = min(r for r, c in non_zero)
            max_r = max(r for r, c in non_zero)
            min_c = min(c for r, c in non_zero)
            max_c = max(c for r, c in non_zero)

            crop_h = max_r - min_r + 1
            crop_w = max_c - min_c + 1

            if crop_h != oH or crop_w != oW:
                return None

            # The cropped region must be a solid rectangle (all cells non-zero)
            cropped = [ri[r][min_c:max_c + 1] for r in range(min_r, max_r + 1)]
            all_filled = all(cropped[r][c] != 0
                            for r in range(crop_h) for c in range(crop_w))
            if not all_filled:
                return None

            # Must have exactly 2 non-zero colors in the rectangle
            rect_colors = set()
            for row in cropped:
                for v in row:
                    if v != 0:
                        rect_colors.add(v)
            if len(rect_colors) != 2:
                return None

            # Output should be horizontal flip of cropped
            flipped = [row[::-1] for row in cropped]
            if flipped != ro:
                return None

        return {"type": "crop_rect_flip"}

    # ---- strategy 80: frame extract ------------------------------------------

    def _try_frame_extract(self, patterns, wm):
        """
        Detect: input has a rectangular frame on a zero background.
        The frame has corner_color at corners and edge_color on edges (vertical
        sides). Noise pixels of corner_color may be scattered outside.
        Output = the frame rectangle cropped out.
        Category: framed object extraction / noise removal.
        """
        task = wm.task
        if task is None:
            return None
        examples = task.example_pairs
        if len(examples) < 2:
            return None

        edge_color = None

        for pair in examples:
            ri = pair.input_grid.raw
            ro = pair.output_grid.raw
            H, W = len(ri), len(ri[0])
            oH, oW = len(ro), len(ro[0])

            # Find cells with edge_color candidates (non-zero, non-dominant)
            # The edge color appears only on the frame edges, not as noise
            color_counts = {}
            for r in range(H):
                for c in range(W):
                    v = ri[r][c]
                    if v != 0:
                        color_counts[v] = color_counts.get(v, 0) + 1

            if len(color_counts) < 2:
                return None

            # Edge color should appear less than corner color (it's only on sides)
            # Try each non-zero color as edge color
            found = False
            for ec in color_counts:
                # Find bounding box of edge-color cells
                ec_cells = [(r, c) for r in range(H) for c in range(W) if ri[r][c] == ec]
                if len(ec_cells) < 2:
                    continue

                ec_min_r = min(r for r, c in ec_cells)
                ec_max_r = max(r for r, c in ec_cells)
                ec_min_c = min(c for r, c in ec_cells)
                ec_max_c = max(c for r, c in ec_cells)

                # Edge cells should all be in 2 columns (left and right edges)
                ec_cols = set(c for r, c in ec_cells)
                if len(ec_cols) != 2:
                    continue
                left_c, right_c = min(ec_cols), max(ec_cols)

                # Frame rectangle: corners are 1 row above/below edge rows
                frame_min_r = ec_min_r - 1
                frame_max_r = ec_max_r + 1
                frame_min_c = left_c
                frame_max_c = right_c

                if frame_min_r < 0 or frame_max_r >= H:
                    continue

                crop_h = frame_max_r - frame_min_r + 1
                crop_w = frame_max_c - frame_min_c + 1

                if crop_h != oH or crop_w != oW:
                    continue

                # Verify output matches cropped frame
                cropped = [ri[r][frame_min_c:frame_max_c + 1]
                           for r in range(frame_min_r, frame_max_r + 1)]
                if cropped == ro:
                    if edge_color is None:
                        edge_color = ec
                    elif ec != edge_color:
                        return None
                    found = True
                    break

            if not found:
                return None

        return {"type": "frame_extract", "edge_color": edge_color}

    # ---- strategy 81: marker shape extract ----------------------------------

    def _try_marker_shape_extract(self, patterns, wm):
        """
        Detect: input has several colored shapes on a black (0) background.
        Exactly one shape contains a marker pixel (color 8). Output is that
        shape's bounding box with the marker replaced by the shape's own color.
        Category: shape selection by marker / extraction.
        """
        task = wm.task
        if not task or not task.example_pairs:
            return None

        marker_color = 8

        for pair in task.example_pairs:
            g0, g1 = pair.input_grid, pair.output_grid
            if not g0 or not g1:
                return None
            ri, ro = g0.raw, g1.raw
            H, W = len(ri), len(ri[0])
            oH, oW = len(ro), len(ro[0])

            # Find marker pixel(s)
            marker_cells = [(r, c) for r in range(H) for c in range(W)
                            if ri[r][c] == marker_color]
            if len(marker_cells) != 1:
                return None
            mr, mc = marker_cells[0]

            # Find the shape that contains/touches the marker
            # The shape is the connected component of non-zero, non-background
            # cells around the marker (including adjacent non-zero cells)
            # First find all non-zero cells
            non_bg = set()
            for r in range(H):
                for c in range(W):
                    if ri[r][c] != 0:
                        non_bg.add((r, c))

            # BFS from marker to find its connected shape
            visited = set()
            queue = [(mr, mc)]
            shape_cells = []
            while queue:
                p = queue.pop(0)
                if p in visited or p not in non_bg:
                    continue
                visited.add(p)
                shape_cells.append(p)
                for dr, dc in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                    nb = (p[0] + dr, p[1] + dc)
                    if nb not in visited and nb in non_bg:
                        queue.append(nb)

            if not shape_cells:
                return None

            # Find shape color (most common non-marker color in shape)
            color_counts = {}
            for r, c in shape_cells:
                v = ri[r][c]
                if v != marker_color:
                    color_counts[v] = color_counts.get(v, 0) + 1
            if not color_counts:
                return None
            shape_color = max(color_counts, key=color_counts.get)

            # Get bounding box of shape
            min_r = min(r for r, c in shape_cells)
            max_r = max(r for r, c in shape_cells)
            min_c = min(c for r, c in shape_cells)
            max_c = max(c for r, c in shape_cells)

            bbox_h = max_r - min_r + 1
            bbox_w = max_c - min_c + 1

            if bbox_h != oH or bbox_w != oW:
                return None

            # Build expected output: crop bbox, replace marker with shape_color
            expected = []
            for r in range(min_r, max_r + 1):
                row = []
                for c in range(min_c, max_c + 1):
                    v = ri[r][c]
                    if v == marker_color:
                        v = shape_color
                    row.append(v)
                expected.append(row)

            if expected != ro:
                return None

        return {"type": "marker_shape_extract", "marker_color": marker_color}

    # ---- strategy 82: template placeholder stamp ----------------------------

    def _try_template_placeholder_stamp(self, patterns, wm):
        """
        Detect: input has one multi-color template shape and one or more
        placeholder blocks (all same color, typically 5). Each placeholder
        has the same dimensions as the template. Output replaces each
        placeholder with a copy of the template.
        Category: pattern replication / template stamping.
        """
        task = wm.task
        if not task or not task.example_pairs:
            return None

        placeholder_color = None
        template_data = None

        for pair in task.example_pairs:
            g0, g1 = pair.input_grid, pair.output_grid
            if not g0 or not g1:
                return None
            ri, ro = g0.raw, g1.raw
            H, W = len(ri), len(ri[0])
            oH, oW = len(ro), len(ro[0])

            if H != oH or W != oW:
                return None

            # Find connected components of non-zero cells
            non_bg = set()
            for r in range(H):
                for c in range(W):
                    if ri[r][c] != 0:
                        non_bg.add((r, c))

            visited = set()
            components = []
            for pos in non_bg:
                if pos in visited:
                    continue
                queue = [pos]
                comp = []
                while queue:
                    p = queue.pop(0)
                    if p in visited or p not in non_bg:
                        continue
                    visited.add(p)
                    comp.append(p)
                    for dr, dc in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                        nb = (p[0] + dr, p[1] + dc)
                        if nb not in visited and nb in non_bg:
                            queue.append(nb)
                components.append(comp)

            if len(components) < 2:
                return None

            # Classify components: uniform (all same color) vs multi-color
            uniform_comps = []
            multi_comps = []
            for comp in components:
                colors = set(ri[r][c] for r, c in comp)
                if len(colors) == 1:
                    uniform_comps.append((comp, list(colors)[0]))
                else:
                    multi_comps.append(comp)

            # Need exactly 1 multi-color template and >=1 uniform placeholders
            if len(multi_comps) != 1 or len(uniform_comps) < 1:
                return None

            template_comp = multi_comps[0]

            # Check all uniform comps have same color
            pc = uniform_comps[0][1]
            if not all(c == pc for _, c in uniform_comps):
                return None

            if placeholder_color is None:
                placeholder_color = pc
            elif placeholder_color != pc:
                return None

            # Get template bbox
            t_min_r = min(r for r, c in template_comp)
            t_max_r = max(r for r, c in template_comp)
            t_min_c = min(c for r, c in template_comp)
            t_max_c = max(c for r, c in template_comp)
            t_h = t_max_r - t_min_r + 1
            t_w = t_max_c - t_min_c + 1

            # Extract template pattern (relative to bbox, bg = 0)
            tpl = [[0] * t_w for _ in range(t_h)]
            for r, c in template_comp:
                tpl[r - t_min_r][c - t_min_c] = ri[r][c]

            template_data = tpl  # template shape varies per example

            # Verify each placeholder has matching bbox dimensions
            for comp, _ in uniform_comps:
                p_min_r = min(r for r, c in comp)
                p_max_r = max(r for r, c in comp)
                p_min_c = min(c for r, c in comp)
                p_max_c = max(c for r, c in comp)
                p_h = p_max_r - p_min_r + 1
                p_w = p_max_c - p_min_c + 1
                if p_h != t_h or p_w != t_w:
                    return None

            # Verify output: template unchanged, placeholders replaced
            for comp, _ in uniform_comps:
                p_min_r = min(r for r, c in comp)
                p_min_c = min(c for r, c in comp)
                for dr in range(t_h):
                    for dc in range(t_w):
                        expected = tpl[dr][dc]
                        actual = ro[p_min_r + dr][p_min_c + dc]
                        if expected != actual:
                            return None

        return {
            "type": "template_placeholder_stamp",
            "placeholder_color": placeholder_color,
        }

    # ---- strategy 83: unique quadrant extract --------------------------------

    def _try_unique_quadrant_extract(self, patterns, wm):
        """
        Detect: grid divided into 4 quadrants by zero-separator rows/columns.
        Three quadrants use the same non-zero main color, one uses a different
        color. Output = the unique-color quadrant extracted.
        Category: quadrant selection / region extraction by color uniqueness.
        """
        task = wm.task
        if not task or not task.example_pairs:
            return None

        for pair in task.example_pairs:
            g0, g1 = pair.input_grid, pair.output_grid
            if not g0 or not g1:
                return None
            ri, ro = g0.raw, g1.raw
            H, W = len(ri), len(ri[0])
            oH, oW = len(ro), len(ro[0])

            # Find separator rows (all zeros)
            sep_rows = [r for r in range(H) if all(ri[r][c] == 0 for c in range(W))]
            # Find separator cols (all zeros)
            sep_cols = [c for c in range(W) if all(ri[r][c] == 0 for r in range(H))]

            if not sep_rows or not sep_cols:
                return None

            # Find contiguous blocks of separator rows
            row_bands = self._find_separator_bands(sep_rows, H)
            col_bands = self._find_separator_bands(sep_cols, W)

            if len(row_bands) != 1 or len(col_bands) != 1:
                return None

            # Define 4 quadrants
            r_sep_start, r_sep_end = row_bands[0]
            c_sep_start, c_sep_end = col_bands[0]

            quadrants = [
                (0, r_sep_start - 1, 0, c_sep_start - 1),               # TL
                (0, r_sep_start - 1, c_sep_end + 1, W - 1),             # TR
                (r_sep_end + 1, H - 1, 0, c_sep_start - 1),             # BL
                (r_sep_end + 1, H - 1, c_sep_end + 1, W - 1),           # BR
            ]

            # Check each quadrant is valid
            valid_quads = []
            for r0, r1, c0, c1 in quadrants:
                if r0 > r1 or c0 > c1:
                    return None
                valid_quads.append((r0, r1, c0, c1))

            # Determine dominant non-zero color for each quadrant
            quad_colors = []
            for r0, r1, c0, c1 in valid_quads:
                color_counts = {}
                for r in range(r0, r1 + 1):
                    for c in range(c0, c1 + 1):
                        v = ri[r][c]
                        if v != 0:
                            color_counts[v] = color_counts.get(v, 0) + 1
                if not color_counts:
                    return None
                dominant = max(color_counts, key=color_counts.get)
                quad_colors.append(dominant)

            # Find the unique color (appears exactly once among 4 quadrants)
            from collections import Counter
            cc = Counter(quad_colors)
            unique_colors = [c for c, n in cc.items() if n == 1]
            if len(unique_colors) != 1:
                return None

            unique_idx = quad_colors.index(unique_colors[0])
            r0, r1, c0, c1 = valid_quads[unique_idx]

            # Verify output matches this quadrant
            quad_h = r1 - r0 + 1
            quad_w = c1 - c0 + 1
            if quad_h != oH or quad_w != oW:
                return None

            extracted = [ri[r][c0:c1 + 1] for r in range(r0, r1 + 1)]
            if extracted != ro:
                return None

        return {"type": "unique_quadrant_extract"}

    @staticmethod
    def _find_separator_bands(sep_indices, total):
        """Group consecutive separator indices into bands.
        Returns list of (start, end) tuples."""
        if not sep_indices:
            return []
        bands = []
        start = sep_indices[0]
        prev = sep_indices[0]
        for idx in sep_indices[1:]:
            if idx == prev + 1:
                prev = idx
            else:
                bands.append((start, prev))
                start = idx
                prev = idx
        bands.append((start, prev))
        return bands

    # ---- strategy 84: self-referential grid fill ----------------------------

    def _try_self_ref_grid_fill(self, patterns, wm):
        """
        Detect: grid divided into NxN blocks by zero-separator rows/columns.
        Each block is filled with a foreground color except for a single 0-cell
        whose position within the block equals the block's position in the grid.
        Some blocks may be empty (all 0) in input; output fills them.
        Category: self-referential positional grid / pattern completion.
        """
        task = wm.task
        if not task or not task.example_pairs:
            return None

        for pair in task.example_pairs:
            g0, g1 = pair.input_grid, pair.output_grid
            if not g0 or not g1:
                return None
            ri, ro = g0.raw, g1.raw
            H, W = len(ri), len(ri[0])
            oH, oW = len(ro), len(ro[0])
            if H != oH or W != oW:
                return None

            # Find separator rows and cols
            sep_rows = [r for r in range(H) if all(ri[r][c] == 0 for c in range(W))
                        and all(ro[r][c] == 0 for c in range(W))]
            sep_cols = [c for c in range(W) if all(ri[r][c] == 0 for r in range(H))
                        and all(ro[r][c] == 0 for r in range(H))]

            if not sep_rows and not sep_cols:
                # Could be no separators (e.g., 2×2 grid with no separator lines)
                # For now require at least one kind
                pass

            # Build row and col groups (non-separator bands)
            sep_r_set = set(sep_rows)
            sep_c_set = set(sep_cols)

            row_groups = []
            r = 0
            while r < H:
                if r in sep_r_set:
                    r += 1
                    continue
                start = r
                while r < H and r not in sep_r_set:
                    r += 1
                row_groups.append((start, r - 1))

            col_groups = []
            c = 0
            while c < W:
                if c in sep_c_set:
                    c += 1
                    continue
                start = c
                while c < W and c not in sep_c_set:
                    c += 1
                col_groups.append((start, c - 1))

            n_rows = len(row_groups)
            n_cols = len(col_groups)
            if n_rows < 2 or n_cols < 2 or n_rows != n_cols:
                return None

            # All blocks should have same dimensions
            block_h = row_groups[0][1] - row_groups[0][0] + 1
            block_w = col_groups[0][1] - col_groups[0][0] + 1
            if block_h != n_rows or block_w != n_cols:
                return None
            for rg in row_groups:
                if rg[1] - rg[0] + 1 != block_h:
                    return None
            for cg in col_groups:
                if cg[1] - cg[0] + 1 != block_w:
                    return None

            # Determine foreground color from output (most common non-zero)
            fg_counts = {}
            for r in range(H):
                for c in range(W):
                    v = ro[r][c]
                    if v != 0 and r not in sep_r_set and c not in sep_c_set:
                        fg_counts[v] = fg_counts.get(v, 0) + 1
            if not fg_counts:
                return None
            fg_color = max(fg_counts, key=fg_counts.get)

            # Verify each block in output: filled with fg, hole at (bi, bj)
            for bi in range(n_rows):
                for bj in range(n_cols):
                    rs, re = row_groups[bi]
                    cs, ce = col_groups[bj]
                    for lr in range(block_h):
                        for lc in range(block_w):
                            expected = 0 if (lr == bi and lc == bj) else fg_color
                            actual = ro[rs + lr][cs + lc]
                            if actual != expected:
                                return None

        return {"type": "self_ref_grid_fill"}


    # ---- strategy 85: point reflect tile ------------------------------------

    def _try_point_reflect_tile(self, patterns, wm):
        """
        Detect: NxM input → 2Nx2M output by placing 4 reflected copies to
        create point symmetry (180° rotational symmetry about the center).
        Layout: [rot180 | vflip] / [hflip | orig]
        Category: symmetry expansion / reflection tiling patterns.
        """
        task = wm.task
        if not task or not task.example_pairs:
            return None

        for pair in task.example_pairs:
            ig, og = pair.input_grid, pair.output_grid
            if not ig or not og:
                return None
            ri, ro = ig.raw, og.raw
            H, W = len(ri), len(ri[0])
            oH, oW = len(ro), len(ro[0])

            if oH != 2 * H or oW != 2 * W:
                return None

            # Build expected: top-left=rot180, top-right=vflip,
            #                 bottom-left=hflip, bottom-right=orig
            for r in range(H):
                for c in range(W):
                    # rot180 in top-left quadrant
                    if ro[r][c] != ri[H - 1 - r][W - 1 - c]:
                        return None
                    # vflip in top-right quadrant
                    if ro[r][W + c] != ri[H - 1 - r][c]:
                        return None
                    # hflip in bottom-left quadrant
                    if ro[H + r][c] != ri[r][W - 1 - c]:
                        return None
                    # orig in bottom-right quadrant
                    if ro[H + r][W + c] != ri[r][c]:
                        return None

        return {"type": "point_reflect_tile", "confidence": 1.0}

    # ---- strategy 86: nested rect color reverse ------------------------------

    def _try_nested_rect_color_reverse(self, patterns, wm):
        """
        Detect: grid contains one or more nested rectangular structures
        (concentric rect layers, each a uniform non-zero color). The output
        reverses the color sequence: outermost gets innermost color, etc.
        Category: concentric shape / color permutation patterns.
        """
        task = wm.task
        if not task or not task.example_pairs:
            return None

        for pair in task.example_pairs:
            ig, og = pair.input_grid, pair.output_grid
            if not ig or not og:
                return None
            ri, ro = ig.raw, og.raw
            H, W = len(ri), len(ri[0])
            oH, oW = len(ro), len(ro[0])
            if H != oH or W != oW:
                return None

            # Find all non-zero connected rectangular objects
            visited = [[False] * W for _ in range(H)]
            objects = []  # list of (bounding_box, layer_colors)

            for r in range(H):
                for c in range(W):
                    if ri[r][c] != 0 and not visited[r][c]:
                        # BFS to find connected component of non-zero cells
                        color = ri[r][c]
                        stack = [(r, c)]
                        cells = set()
                        while stack:
                            cr, cc = stack.pop()
                            if cr < 0 or cr >= H or cc < 0 or cc >= W:
                                continue
                            if (cr, cc) in cells or visited[cr][cc]:
                                continue
                            if ri[cr][cc] == 0:
                                continue
                            cells.add((cr, cc))
                            visited[cr][cc] = True
                            stack.extend([(cr+1, cc), (cr-1, cc), (cr, cc+1), (cr, cc-1)])

                        if not cells:
                            continue

                        min_r = min(cr for cr, cc in cells)
                        max_r = max(cr for cr, cc in cells)
                        min_c = min(cc for cr, cc in cells)
                        max_c = max(cc for cr, cc in cells)

                        # Check that the bounding box is fully filled with non-zero
                        is_rect = True
                        for br in range(min_r, max_r + 1):
                            for bc in range(min_c, max_c + 1):
                                if ri[br][bc] == 0:
                                    is_rect = False
                                    break
                            if not is_rect:
                                break
                        if not is_rect:
                            return None

                        # Extract concentric layer colors (outside→inside)
                        layer_colors = []
                        tr, br, lc, rc = min_r, max_r, min_c, max_c
                        while tr <= br and lc <= rc:
                            c_val = ri[tr][lc]
                            layer_colors.append(c_val)
                            # Verify all cells on this ring are same color
                            for bc2 in range(lc, rc + 1):
                                if ri[tr][bc2] != c_val or ri[br][bc2] != c_val:
                                    return None
                            for br2 in range(tr, br + 1):
                                if ri[br2][lc] != c_val or ri[br2][rc] != c_val:
                                    return None
                            tr += 1
                            br -= 1
                            lc += 1
                            rc -= 1

                        if len(layer_colors) < 2:
                            return None

                        # Build unique color sequence (preserve order, deduplicate)
                        unique_colors = []
                        for cv in layer_colors:
                            if not unique_colors or unique_colors[-1] != cv:
                                unique_colors.append(cv)
                        if len(unique_colors) < 2:
                            return None

                        # Build color mapping: reverse the unique sequence
                        rev_unique = list(reversed(unique_colors))
                        color_map = {}
                        for uc, rc2 in zip(unique_colors, rev_unique):
                            color_map[uc] = rc2

                        # Verify output matches mapped colors for this object
                        for br2 in range(min_r, max_r + 1):
                            for bc2 in range(min_c, max_c + 1):
                                expected = color_map.get(ri[br2][bc2])
                                if expected is None or ro[br2][bc2] != expected:
                                    return None

                        objects.append((min_r, max_r, min_c, max_c, layer_colors))

            if not objects:
                return None

        return {"type": "nested_rect_color_reverse", "confidence": 1.0}

    # ---- strategy 87: diagonal ring fill ------------------------------------

    def _try_diagonal_ring_fill(self, patterns, wm):
        """
        Detect: diagonal color markers at (0,0), (1,1), (2,2), ... plus a
        hollow rectangle outlined in color 1. Output fills the rect interior
        with concentric rings using the diagonal color sequence.
        Category: concentric ring fill / sequence-driven patterns.
        """
        task = wm.task
        if not task or not task.example_pairs:
            return None

        for pair in task.example_pairs:
            ig, og = pair.input_grid, pair.output_grid
            if not ig or not og:
                return None
            ri, ro = ig.raw, og.raw
            H, W = len(ri), len(ri[0])
            if H != len(ro) or W != len(ro[0]):
                return None

            # Extract diagonal color sequence
            diag_colors = []
            for i in range(min(H, W)):
                v = ri[i][i]
                if v == 0 or v == 1:
                    break
                diag_colors.append(v)

            if len(diag_colors) < 1:
                return None

            # Find the rectangle outlined in color 1
            rect_top = rect_bot = rect_left = rect_right = None
            border_color = 1
            for r in range(H):
                for c in range(W):
                    if ri[r][c] == border_color:
                        if rect_top is None or r < rect_top:
                            rect_top = r
                        if rect_bot is None or r > rect_bot:
                            rect_bot = r
                        if rect_left is None or c < rect_left:
                            rect_left = c
                        if rect_right is None or c > rect_right:
                            rect_right = c

            if rect_top is None:
                return None

            # Verify the border is a proper rectangle of 1s
            for c in range(rect_left, rect_right + 1):
                if ri[rect_top][c] != border_color or ri[rect_bot][c] != border_color:
                    return None
            for r in range(rect_top, rect_bot + 1):
                if ri[r][rect_left] != border_color or ri[r][rect_right] != border_color:
                    return None

            # Verify the interior is all 0 in input
            for r in range(rect_top + 1, rect_bot):
                for c in range(rect_left + 1, rect_right):
                    if ri[r][c] != 0:
                        return None

            # Check output: border unchanged, interior filled with concentric rings
            # using diag_colors in order (outermost ring = diag_colors[0])
            int_top = rect_top + 1
            int_bot = rect_bot - 1
            int_left = rect_left + 1
            int_right = rect_right - 1

            t, b, l, rr = int_top, int_bot, int_left, int_right
            ci = 0
            while t <= b and l <= rr:
                # Use next color, or repeat last color if sequence exhausted
                if ci < len(diag_colors):
                    expected = diag_colors[ci]
                else:
                    expected = diag_colors[-1]
                # Check top and bottom rows of this ring
                for c in range(l, rr + 1):
                    if ro[t][c] != expected or ro[b][c] != expected:
                        return None
                # Check left and right columns of this ring
                for r in range(t, b + 1):
                    if ro[r][l] != expected or ro[r][rr] != expected:
                        return None
                t += 1
                b -= 1
                l += 1
                rr -= 1
                ci += 1

        return {"type": "diagonal_ring_fill", "confidence": 1.0}

    # ---- strategy 88: denoise isolated pixels --------------------------------

    def _try_denoise_isolated(self, patterns, wm):
        """
        Detect: grid has one non-zero color scattered on bg=0. Output removes
        all pixels that are 8-isolated (no same-color neighbor in any of 8 dirs).
        Only 8-connected components of size >= 2 survive.
        Category: noise removal / 8-connected component filtering.
        """
        task = wm.task
        if not task or not task.example_pairs:
            return None
        # Must preserve grid size
        for pair in task.example_pairs:
            g0, g1 = pair.input_grid, pair.output_grid
            if not g0 or not g1:
                return None
            if len(g0.raw) != len(g1.raw):
                return None
            if len(g0.raw[0]) != len(g1.raw[0]):
                return None
        # Must have exactly one non-zero color (or possibly bg=0 + 1 fg color)
        for pair in task.example_pairs:
            ri = pair.input_grid.raw
            ro = pair.output_grid.raw
            H = len(ri)
            W = len(ri[0])
            fg_colors_in = set()
            for r in range(H):
                for c in range(W):
                    if ri[r][c] != 0:
                        fg_colors_in.add(ri[r][c])
            if len(fg_colors_in) != 1:
                return None
            fg = list(fg_colors_in)[0]
            # Output should only have bg=0 and this same fg color
            for r in range(H):
                for c in range(W):
                    if ro[r][c] != 0 and ro[r][c] != fg:
                        return None
            # Validate: output == input with 8-isolated pixels removed
            for r in range(H):
                for c in range(W):
                    has_neighbor = False
                    if ri[r][c] == fg:
                        for dr in (-1, 0, 1):
                            for dc in (-1, 0, 1):
                                if dr == 0 and dc == 0:
                                    continue
                                nr, nc = r + dr, c + dc
                                if 0 <= nr < H and 0 <= nc < W and ri[nr][nc] == fg:
                                    has_neighbor = True
                                    break
                            if has_neighbor:
                                break
                        expected = fg if has_neighbor else 0
                    else:
                        expected = 0
                    if ro[r][c] != expected:
                        return None
        return {"type": "denoise_isolated", "confidence": 1.0}

    # ---- strategy 89: L-shape diagonal ray -----------------------------------

    def _try_l_diagonal_ray(self, patterns, wm):
        """
        Detect: grid has L-shaped groups of 3 cells (each forming 3 of 4 cells
        of a 2x2 box) of a single fg color on bg=0. Output keeps the L-shapes
        and shoots a diagonal ray from the missing corner outward (away from
        the filled opposite corner) until hitting the grid edge.
        Category: geometric projection / L-shape diagonal extension.
        """
        task = wm.task
        if not task or not task.example_pairs:
            return None
        for pair in task.example_pairs:
            g0, g1 = pair.input_grid, pair.output_grid
            if not g0 or not g1:
                return None
            if len(g0.raw) != len(g1.raw) or len(g0.raw[0]) != len(g1.raw[0]):
                return None
        # Validate on each example
        for pair in task.example_pairs:
            ri = pair.input_grid.raw
            ro = pair.output_grid.raw
            H = len(ri)
            W = len(ri[0])
            # Find fg color
            fg_colors = set()
            for r in range(H):
                for c in range(W):
                    if ri[r][c] != 0:
                        fg_colors.add(ri[r][c])
            if len(fg_colors) != 1:
                return None
            fg = list(fg_colors)[0]
            # Find 8-connected components
            visited = [[False]*W for _ in range(H)]
            comps = []
            for r in range(H):
                for c in range(W):
                    if ri[r][c] == fg and not visited[r][c]:
                        comp = []
                        stack = [(r, c)]
                        while stack:
                            cr, cc = stack.pop()
                            if visited[cr][cc]:
                                continue
                            visited[cr][cc] = True
                            comp.append((cr, cc))
                            for dr in (-1, 0, 1):
                                for dc in (-1, 0, 1):
                                    if dr == 0 and dc == 0:
                                        continue
                                    nr, nc = cr + dr, cc + dc
                                    if 0 <= nr < H and 0 <= nc < W and ri[nr][nc] == fg and not visited[nr][nc]:
                                        stack.append((nr, nc))
                        comps.append(comp)
            # Each component should be an L-shape (3 cells of a 2x2 box)
            predicted = [row[:] for row in ri]
            for comp in comps:
                if len(comp) != 3:
                    return None  # not all components are 3-cell L-shapes
                cs = set(comp)
                # Find the 2x2 box containing all 3
                min_r = min(r for r, c in cs)
                max_r = max(r for r, c in cs)
                min_c = min(c for r, c in cs)
                max_c = max(c for r, c in cs)
                if max_r - min_r != 1 or max_c - min_c != 1:
                    return None  # doesn't fit in a 2x2 box
                # Find missing corner
                missing = None
                for br in (min_r, max_r):
                    for bc in (min_c, max_c):
                        if (br, bc) not in cs:
                            missing = (br, bc)
                if missing is None:
                    return None
                # Opposite corner (diagonally across)
                opp_r = min_r if missing[0] == max_r else max_r
                opp_c = min_c if missing[1] == max_c else max_c
                # Direction from opposite to missing
                dr = missing[0] - opp_r  # +1 or -1
                dc = missing[1] - opp_c  # +1 or -1
                # Shoot ray from missing corner outward
                cr, cc = missing[0] + dr, missing[1] + dc
                while 0 <= cr < H and 0 <= cc < W:
                    predicted[cr][cc] = fg
                    cr += dr
                    cc += dc
            # Validate predicted matches output
            if predicted != ro:
                return None
        return {"type": "l_diagonal_ray", "confidence": 1.0}

    # ---- strategy 90: nest rectangles by size --------------------------------

    def _try_nest_rectangles(self, patterns, wm):
        """
        Detect: input has several colored rectangular shapes (hollow frames or
        solid blocks) scattered on bg=0, each a different color. Output is a
        single nested concentric rectangle where colors are layered from
        outermost (largest input rect) to innermost (smallest).
        Output dims = innermost_dim + 2*(n_colors-1) for each axis.
        Category: shape assembly / rectangle nesting by size.
        """
        task = wm.task
        if not task or not task.example_pairs:
            return None
        for pair in task.example_pairs:
            g0, g1 = pair.input_grid, pair.output_grid
            if not g0 or not g1:
                return None
            if len(g1.raw) > len(g0.raw) or len(g1.raw[0]) > len(g0.raw[0]):
                return None
        for pair in task.example_pairs:
            ri = pair.input_grid.raw
            ro = pair.output_grid.raw
            H = len(ri)
            W = len(ri[0])
            oH = len(ro)
            oW = len(ro[0])
            color_cells = {}
            for r in range(H):
                for c in range(W):
                    v = ri[r][c]
                    if v != 0:
                        if v not in color_cells:
                            color_cells[v] = []
                        color_cells[v].append((r, c))
            if len(color_cells) < 2:
                return None
            rects = []
            for color, cells in color_cells.items():
                min_r = min(r for r, c in cells)
                max_r = max(r for r, c in cells)
                min_c = min(c for r, c in cells)
                max_c = max(c for r, c in cells)
                h = max_r - min_r + 1
                w = max_c - min_c + 1
                rects.append((color, h, w, h * w))
            rects.sort(key=lambda x: -x[3])
            n = len(rects)
            # Innermost rect determines center fill
            inner_h = rects[-1][1]
            inner_w = rects[-1][2]
            exp_h = inner_h + 2 * (n - 1)
            exp_w = inner_w + 2 * (n - 1)
            if oH != exp_h or oW != exp_w:
                return None
            expected = [[0]*oW for _ in range(oH)]
            for ci, (color, _, _, _) in enumerate(rects):
                t, b, l, rr2 = ci, oH - 1 - ci, ci, oW - 1 - ci
                if t > b or l > rr2:
                    break
                for c in range(l, rr2 + 1):
                    expected[t][c] = color
                    expected[b][c] = color
                for r in range(t, b + 1):
                    expected[r][l] = color
                    expected[r][rr2] = color
            if expected != ro:
                return None
        return {"type": "nest_rectangles", "confidence": 1.0}

    # ---- strategy 91: column rank recolor --------------------------------

    def _try_column_rank_recolor(self, patterns, wm):
        """
        Detect: grid has a uniform background (one dominant colour) with
        scattered cells of a single minority colour (typically 0).  Each
        minority cell is replaced with a colour 1, 2, 3, … determined by
        the left-to-right rank of its column among all columns that contain
        minority cells.
        Category: positional encoding / column-based recolouring.
        """
        task = wm.task
        if not task or not task.example_pairs:
            return None
        if not patterns.get("grid_size_preserved", False):
            return None

        from collections import Counter

        pair0 = task.example_pairs[0]
        g0 = pair0.input_grid
        if not g0:
            return None
        raw0 = g0.raw
        H, W = len(raw0), len(raw0[0]) if raw0 else 0
        freq = Counter()
        for r in range(H):
            for c in range(W):
                freq[raw0[r][c]] += 1
        bg_color = freq.most_common(1)[0][0]
        input_colors = set(freq.keys()) - {bg_color}
        if len(input_colors) != 1:
            return None
        minority_color = input_colors.pop()

        for pair in task.example_pairs:
            g0, g1 = pair.input_grid, pair.output_grid
            if not g0 or not g1:
                return None
            raw_in = g0.raw
            raw_out = g1.raw
            H2, W2 = len(raw_in), len(raw_in[0]) if raw_in else 0
            if H2 != len(raw_out) or W2 != (len(raw_out[0]) if raw_out else 0):
                return None

            in_clrs = set()
            for r in range(H2):
                for c in range(W2):
                    in_clrs.add(raw_in[r][c])
            if in_clrs - {bg_color, minority_color}:
                return None

            minority_cols = sorted(set(
                c for r in range(H2) for c in range(W2)
                if raw_in[r][c] == minority_color
            ))
            if not minority_cols:
                return None
            col_to_color = {col: idx + 1 for idx, col in enumerate(minority_cols)}

            for r in range(H2):
                for c in range(W2):
                    if raw_in[r][c] == minority_color:
                        if raw_out[r][c] != col_to_color[c]:
                            return None
                    else:
                        if raw_out[r][c] != raw_in[r][c]:
                            return None

        return {
            "type": "column_rank_recolor",
            "bg_color": bg_color,
            "minority_color": minority_color,
            "confidence": 1.0,
        }

    # ---- strategy 92: rect frame gap ray ---------------------------------

    def _try_rect_frame_gap_ray(self, patterns, wm):
        """
        Detect: rectangular frames drawn in frame_color on a uniform
        background.  Each frame has exactly one gap (missing border cell).
        Interior is filled with fill_color and a ray of fill_color extends
        from the gap outward to the grid boundary.
        Category: frame gap detection / interior fill / ray projection.
        """
        task = wm.task
        if not task or not task.example_pairs:
            return None
        if not patterns.get("grid_size_preserved", False):
            return None

        from collections import Counter

        pair0 = task.example_pairs[0]
        g0, g1 = pair0.input_grid, pair0.output_grid
        if not g0 or not g1:
            return None
        raw_in0 = g0.raw
        raw_out0 = g1.raw
        H, W = len(raw_in0), len(raw_in0[0]) if raw_in0 else 0

        freq = Counter()
        for r in range(H):
            for c in range(W):
                freq[raw_in0[r][c]] += 1
        bg_color = freq.most_common(1)[0][0]
        in_colors = set(freq.keys())
        if len(in_colors) != 2:
            return None
        frame_color = (in_colors - {bg_color}).pop()

        out_colors = set()
        for r in range(H):
            for c in range(W):
                out_colors.add(raw_out0[r][c])
        new_colors = out_colors - in_colors
        if len(new_colors) != 1:
            return None
        fill_color = new_colors.pop()

        for pair in task.example_pairs:
            raw_in = pair.input_grid.raw
            raw_out = pair.output_grid.raw
            pH = len(raw_in)
            pW = len(raw_in[0]) if raw_in else 0

            frames = _find_rect_frames(raw_in, frame_color, bg_color, pH, pW)
            if not frames:
                return None

            expected = [row[:] for row in raw_in]
            for r1, c1, r2, c2, gap_r, gap_c, gap_side in frames:
                for r in range(r1 + 1, r2):
                    for c in range(c1 + 1, c2):
                        expected[r][c] = fill_color
                expected[gap_r][gap_c] = fill_color
                if gap_side == "top":
                    for r in range(gap_r - 1, -1, -1):
                        expected[r][gap_c] = fill_color
                elif gap_side == "bottom":
                    for r in range(gap_r + 1, pH):
                        expected[r][gap_c] = fill_color
                elif gap_side == "left":
                    for c in range(gap_c - 1, -1, -1):
                        expected[gap_r][c] = fill_color
                elif gap_side == "right":
                    for c in range(gap_c + 1, pW):
                        expected[gap_r][c] = fill_color

            if expected != raw_out:
                return None

        return {
            "type": "rect_frame_gap_ray",
            "bg_color": bg_color,
            "frame_color": frame_color,
            "fill_color": fill_color,
            "confidence": 1.0,
        }


    # ---- strategy 93: asymmetric block select -----------------------------

    def _try_asymmetric_block_select(self, patterns, wm):
        """
        Detect: input is K stacked NxN blocks (total rows = K*N, cols = N).
        Exactly one block is NOT symmetric about the main diagonal (A[r][c] != A[c][r]).
        Output = that asymmetric block.
        Category: block selection by structural symmetry property.
        """
        task = wm.task
        if not task or not task.example_pairs:
            return None

        for pair in task.example_pairs:
            g0, g1 = pair.input_grid, pair.output_grid
            if not g0 or not g1:
                return None
            raw_in = g0.raw
            raw_out = g1.raw
            H = len(raw_in)
            W = len(raw_in[0]) if raw_in else 0
            oH = len(raw_out)
            oW = len(raw_out[0]) if raw_out else 0
            if W == 0 or oW != W or oH != W:
                return None
            N = W
            if H % N != 0:
                return None
            K = H // N
            if K < 2:
                return None

            # Extract blocks and find the non-diagonal-symmetric one
            found = None
            for bi in range(K):
                block = [raw_in[bi * N + r][:N] for r in range(N)]
                is_sym = True
                for r in range(N):
                    for c in range(r + 1, N):
                        if block[r][c] != block[c][r]:
                            is_sym = False
                            break
                    if not is_sym:
                        break
                if not is_sym:
                    if found is not None:
                        return None  # more than one asymmetric block
                    found = block

            if found is None:
                return None
            if found != raw_out:
                return None

        return {
            "type": "asymmetric_block_select",
            "confidence": 1.0,
        }

    # ---- strategy 94: seed pixel stamp -----------------------------------

    def _try_seed_pixel_stamp(self, patterns, wm):
        """
        Detect: sparse grid on bg 0 with isolated single-color seed pixels.
        Each seed gets a 3×3 stamp centered on it. The stamp pattern is
        learned from examples.
        Category: pixel expansion / stamp generation from seeds.
        """
        task = wm.task
        if not task or not task.example_pairs:
            return None
        if not patterns.get("grid_size_preserved", False):
            return None

        pair0 = task.example_pairs[0]
        g0, g1 = pair0.input_grid, pair0.output_grid
        if not g0 or not g1:
            return None
        raw_in = g0.raw
        raw_out = g1.raw
        H = len(raw_in)
        W = len(raw_in[0]) if raw_in else 0

        # Find seed color (non-zero, sparse, isolated single pixels)
        from collections import Counter
        freq = Counter()
        for r in range(H):
            for c in range(W):
                if raw_in[r][c] != 0:
                    freq[raw_in[r][c]] += 1
        if not freq:
            return None
        # Should be exactly one non-zero color in input
        if len(freq) != 1:
            return None
        seed_color = list(freq.keys())[0]
        seeds = [(r, c) for r in range(H) for c in range(W) if raw_in[r][c] == seed_color]
        if len(seeds) < 2:
            return None

        # Check seeds are isolated (no two adjacent)
        seed_set = set(seeds)
        for r, c in seeds:
            for dr, dc in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                if (r + dr, c + dc) in seed_set:
                    return None

        # Learn the stamp from the first seed
        sr, sc = seeds[0]
        stamp = {}
        for dr in range(-1, 2):
            for dc in range(-1, 2):
                nr, nc = sr + dr, sc + dc
                if 0 <= nr < H and 0 <= nc < W:
                    stamp[(dr, dc)] = raw_out[nr][nc]

        # Verify stamp is consistent across all seeds in all examples
        for pair in task.example_pairs:
            raw_i = pair.input_grid.raw
            raw_o = pair.output_grid.raw
            pH = len(raw_i)
            pW = len(raw_i[0]) if raw_i else 0
            p_seeds = [(r, c) for r in range(pH) for c in range(pW) if raw_i[r][c] == seed_color]

            # Build expected output
            expected = [[0] * pW for _ in range(pH)]
            for sr2, sc2 in p_seeds:
                for (dr, dc), val in stamp.items():
                    nr, nc = sr2 + dr, sc2 + dc
                    if 0 <= nr < pH and 0 <= nc < pW:
                        expected[nr][nc] = val
            if expected != raw_o:
                return None

        # Serialize stamp
        stamp_list = {f"{dr},{dc}": v for (dr, dc), v in stamp.items()}
        return {
            "type": "seed_pixel_stamp",
            "seed_color": seed_color,
            "stamp": stamp_list,
            "confidence": 1.0,
        }

    # ---- strategy 95: color count expand ---------------------------------

    def _try_color_count_expand(self, patterns, wm):
        """
        Detect: small NxM input grid. Output = each cell expanded to KxK block
        where K = number of unique colors in the input. Output dims = N*K x M*K.
        If K=1, output = input unchanged.
        Category: block expansion / scaling by color diversity.
        """
        task = wm.task
        if not task or not task.example_pairs:
            return None

        for pair in task.example_pairs:
            g0, g1 = pair.input_grid, pair.output_grid
            if not g0 or not g1:
                return None
            raw_in = g0.raw
            raw_out = g1.raw
            iH = len(raw_in)
            iW = len(raw_in[0]) if raw_in else 0
            oH = len(raw_out)
            oW = len(raw_out[0]) if raw_out else 0
            if iH == 0 or iW == 0:
                return None

            # Count unique colors
            colors = set()
            for r in range(iH):
                for c in range(iW):
                    colors.add(raw_in[r][c])
            K = len(colors)
            if K == 0:
                return None

            # Check output dimensions match
            if oH != iH * K or oW != iW * K:
                return None

            # Verify each cell expanded to KxK block
            for r in range(iH):
                for c in range(iW):
                    val = raw_in[r][c]
                    for dr in range(K):
                        for dc in range(K):
                            if raw_out[r * K + dr][c * K + dc] != val:
                                return None

        return {
            "type": "color_count_expand",
            "confidence": 1.0,
        }

    # ---- strategy 96: line rank recolor ------------------------------------

    def _try_line_rank_recolor(self, patterns, wm):
        """
        Detect: grid of 0s with several straight lines of color 5 (horizontal
        or vertical).  Output replaces 5 with a color determined by length rank:
        longest → color A, middle → color B, shortest → color C (learned).
        Category: line detection + rank-based recoloring.
        """
        task = wm.task
        if not task:
            return None
        pairs = task.example_pairs
        if len(pairs) < 2:
            return None

        for pair in pairs:
            inp = pair.input_grid.raw
            out = pair.output_grid.raw
            if len(inp) != len(out) or len(inp[0]) != len(out[0]):
                return None

        # Check that inputs are only 0 and 5
        for pair in pairs:
            inp = pair.input_grid.raw
            for row in inp:
                for v in row:
                    if v not in (0, 5):
                        return None

        def find_lines_cc(grid):
            """Find lines as connected components of 5-cells."""
            H = len(grid)
            W = len(grid[0])
            visited = set()
            lines = []
            for r in range(H):
                for c in range(W):
                    if grid[r][c] != 5 or (r, c) in visited:
                        continue
                    comp = []
                    queue = [(r, c)]
                    visited.add((r, c))
                    while queue:
                        cr, cc = queue.pop(0)
                        comp.append((cr, cc))
                        for dr, dc in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                            nr, nc = cr + dr, cc + dc
                            if (0 <= nr < H and 0 <= nc < W
                                    and (nr, nc) not in visited
                                    and grid[nr][nc] == 5):
                                visited.add((nr, nc))
                                queue.append((nr, nc))
                    if len(comp) < 2:
                        continue
                    rows = set(r2 for r2, c2 in comp)
                    cols = set(c2 for r2, c2 in comp)
                    if len(rows) == 1 or len(cols) == 1:
                        lines.append(comp)
            return lines

        # Validate on all pairs
        rank_colors = None
        for pair in pairs:
            inp = pair.input_grid.raw
            out = pair.output_grid.raw
            lines = find_lines_cc(inp)
            if len(lines) < 2 or len(lines) > 5:
                return None
            lines.sort(key=lambda L: -len(L))
            pair_colors = []
            for line in lines:
                r0, c0 = line[0]
                color = out[r0][c0]
                if color == 0 or color == 5:
                    return None
                for r, c in line:
                    if out[r][c] != color:
                        return None
                pair_colors.append(color)
            if rank_colors is None:
                rank_colors = pair_colors
            else:
                if pair_colors != rank_colors:
                    return None

        return {"type": "line_rank_recolor", "rank_colors": rank_colors,
                "confidence": 0.95}

    # ---- strategy 97: max rect fill ----------------------------------------

    def _try_max_rect_fill(self, patterns, wm):
        """
        Detect: grid of 0s and 5s.  Maximal squares of 0-cells (side >= 2)
        are filled with a single color; greedy largest-first non-overlapping.
        Category: square region detection and fill.
        """
        task = wm.task
        if not task:
            return None
        pairs = task.example_pairs
        if len(pairs) < 2:
            return None

        for pair in pairs:
            inp = pair.input_grid.raw
            out = pair.output_grid.raw
            if len(inp) != len(out) or len(inp[0]) != len(out[0]):
                return None

        # Check inputs are only 0 and 5
        for pair in pairs:
            for row in pair.input_grid.raw:
                for v in row:
                    if v not in (0, 5):
                        return None

        fill_color = None

        def find_fill_cells(grid):
            """Find cells to fill using maximal-square greedy selection."""
            H = len(grid)
            W = len(grid[0])
            # dp[r][c] = max side of all-0 square with (r,c) as top-left
            dp = [[0] * W for _ in range(H)]
            for r in range(H - 1, -1, -1):
                for c in range(W - 1, -1, -1):
                    if grid[r][c] != 0:
                        dp[r][c] = 0
                    elif r == H - 1 or c == W - 1:
                        dp[r][c] = 1
                    else:
                        dp[r][c] = 1 + min(dp[r + 1][c],
                                           dp[r][c + 1],
                                           dp[r + 1][c + 1])
            # Collect all squares of side >= 2
            squares = []
            for r in range(H):
                for c in range(W):
                    if dp[r][c] >= 2:
                        squares.append((dp[r][c], r, c))
            # Sort by side desc, then position for stability
            squares.sort(key=lambda x: (-x[0], x[1], x[2]))
            # Greedy: select non-overlapping
            filled = set()
            for s, r, c in squares:
                cells = set()
                for dr in range(s):
                    for dc in range(s):
                        cells.add((r + dr, c + dc))
                if cells & filled:
                    continue
                filled |= cells
            return filled

        for pair in pairs:
            inp = pair.input_grid.raw
            out = pair.output_grid.raw
            H = len(inp)
            W = len(inp[0])
            filled_cells = find_fill_cells(inp)
            if not filled_cells:
                return None

            # Determine fill color from first filled cell
            r0, c0 = min(filled_cells)
            fc = out[r0][c0]
            if fc == 0 or fc == 5:
                return None
            if fill_color is None:
                fill_color = fc
            elif fill_color != fc:
                return None

            # Verify: input + fill = output
            expected = [row[:] for row in inp]
            for (r, c) in filled_cells:
                expected[r][c] = fill_color
            if expected != out:
                return None

        return {"type": "max_rect_fill", "fill_color": fill_color,
                "confidence": 0.95}

    # ---- strategy 98: divider complement merge ------------------------------

    def _try_divider_complement_merge(self, patterns, wm):
        """
        Detect: input has two halves separated by a single-column divider
        of uniform color.  Left half has shape-color cells and 0-cells;
        right half has colored cells and 0-cells.  If the right non-zero cells
        exactly complement the left zero cells, output merges both;
        otherwise output = left side only.
        Category: split-grid comparison and conditional merge.
        """
        task = wm.task
        if not task:
            return None
        pairs = task.example_pairs
        if len(pairs) < 3:
            return None

        H0 = len(pairs[0].input_grid.raw)
        W0 = len(pairs[0].input_grid.raw[0])
        for pair in pairs:
            inp = pair.input_grid.raw
            out = pair.output_grid.raw
            if len(inp) != H0 or len(inp[0]) != W0:
                return None

        # Detect vertical divider column
        divider_col = None
        divider_color = None
        for c in range(1, W0 - 1):
            col_vals = [pairs[0].input_grid.raw[r][c] for r in range(H0)]
            if len(set(col_vals)) == 1 and col_vals[0] != 0:
                ok = True
                for pair in pairs:
                    cv = [pair.input_grid.raw[r][c] for r in range(H0)]
                    if cv != col_vals:
                        ok = False
                        break
                if ok:
                    divider_col = c
                    divider_color = col_vals[0]
                    break

        if divider_col is None:
            return None

        left_w = divider_col
        right_w = W0 - divider_col - 1
        if left_w != right_w or left_w < 2:
            return None

        for pair in pairs:
            out = pair.output_grid.raw
            if len(out) != H0 or len(out[0]) != left_w:
                return None

        shape_color = None
        for pair in pairs:
            inp = pair.input_grid.raw
            for r in range(H0):
                for c in range(left_w):
                    v = inp[r][c]
                    if v != 0:
                        if shape_color is None:
                            shape_color = v
                        elif v != shape_color:
                            return None

        if shape_color is None:
            return None

        for pair in pairs:
            inp = pair.input_grid.raw
            out = pair.output_grid.raw
            left = [[inp[r][c] for c in range(left_w)] for r in range(H0)]
            right = [[inp[r][divider_col + 1 + c] for c in range(right_w)]
                     for r in range(H0)]

            complementary = True
            for r in range(H0):
                for c in range(left_w):
                    if left[r][c] != 0 and right[r][c] != 0:
                        complementary = False
                        break
                if not complementary:
                    break

            if complementary:
                expected = [row[:] for row in left]
                for r in range(H0):
                    for c in range(left_w):
                        if right[r][c] != 0:
                            expected[r][c] = right[r][c]
                if expected != out:
                    return None
            else:
                if left != out:
                    return None

        return {"type": "divider_complement_merge",
                "divider_col": divider_col,
                "divider_color": divider_color,
                "left_w": left_w,
                "shape_color": shape_color,
                "confidence": 0.92}


    # ---- strategy 99: multi rect fill ray ----------------------------------

    def _try_multi_rect_fill_ray(self, patterns, wm):
        """
        Detect: rectangular frames (color 1) on bg (color 0) with 0 or 1 gaps.
        Fill interior with fill_color, shoot ray from gap if present.
        Generalizes rect_frame_gap_ray to handle complete (0-gap) frames too.
        Category: frame detection / interior fill / optional ray.
        """
        task = wm.task
        if not task or not task.example_pairs:
            return None
        if not patterns.get("grid_size_preserved", False):
            return None

        from collections import Counter

        pair0 = task.example_pairs[0]
        g0, g1 = pair0.input_grid, pair0.output_grid
        if not g0 or not g1:
            return None
        raw_in0 = g0.raw
        raw_out0 = g1.raw
        H, W = len(raw_in0), len(raw_in0[0]) if raw_in0 else 0

        freq = Counter()
        for r in range(H):
            for c in range(W):
                freq[raw_in0[r][c]] += 1
        bg_color = freq.most_common(1)[0][0]
        in_colors = set(freq.keys())
        if len(in_colors) != 2:
            return None
        frame_color = (in_colors - {bg_color}).pop()

        out_colors = set()
        for r in range(H):
            for c in range(W):
                out_colors.add(raw_out0[r][c])
        new_colors = out_colors - in_colors
        if len(new_colors) != 1:
            return None
        fill_color = new_colors.pop()

        for pair in task.example_pairs:
            raw_in = pair.input_grid.raw
            raw_out = pair.output_grid.raw
            pH = len(raw_in)
            pW = len(raw_in[0]) if raw_in else 0

            frames = self._find_rect_frames_any(
                raw_in, frame_color, bg_color, pH, pW)
            if not frames:
                return None

            expected = [row[:] for row in raw_in]
            for r1, c1, r2, c2, gap_r, gap_c, gap_side in frames:
                for r in range(r1 + 1, r2):
                    for c in range(c1 + 1, c2):
                        expected[r][c] = fill_color
                if gap_r is not None:
                    expected[gap_r][gap_c] = fill_color
                    if gap_side == "top":
                        for r in range(gap_r - 1, -1, -1):
                            expected[r][gap_c] = fill_color
                    elif gap_side == "bottom":
                        for r in range(gap_r + 1, pH):
                            expected[r][gap_c] = fill_color
                    elif gap_side == "left":
                        for c in range(gap_c - 1, -1, -1):
                            expected[gap_r][c] = fill_color
                    elif gap_side == "right":
                        for c in range(gap_c + 1, pW):
                            expected[gap_r][c] = fill_color

            if expected != raw_out:
                return None

        return {
            "type": "multi_rect_fill_ray",
            "bg_color": bg_color,
            "frame_color": frame_color,
            "fill_color": fill_color,
            "confidence": 1.0,
        }

    @staticmethod
    def _find_rect_frames_any(raw, frame_color, bg_color, H, W):
        """Find rectangular frames with 0 or 1 gaps in the border."""
        visited = set()
        frames = []
        for sr in range(H):
            for sc in range(W):
                if raw[sr][sc] == frame_color and (sr, sc) not in visited:
                    component = []
                    queue = [(sr, sc)]
                    visited.add((sr, sc))
                    while queue:
                        r, c = queue.pop(0)
                        component.append((r, c))
                        for dr, dc in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                            nr, nc = r + dr, c + dc
                            if (0 <= nr < H and 0 <= nc < W
                                    and (nr, nc) not in visited
                                    and raw[nr][nc] == frame_color):
                                visited.add((nr, nc))
                                queue.append((nr, nc))
                    if len(component) < 6:
                        continue
                    comp_set = set(component)
                    min_r = min(r for r, c in component)
                    max_r = max(r for r, c in component)
                    min_c = min(c for r, c in component)
                    max_c = max(c for r, c in component)
                    border_cells = set()
                    for r in range(min_r, max_r + 1):
                        for c in range(min_c, max_c + 1):
                            if r in (min_r, max_r) or c in (min_c, max_c):
                                border_cells.add((r, c))
                    if not comp_set.issubset(border_cells):
                        continue
                    gaps = border_cells - comp_set
                    if len(gaps) == 0:
                        frames.append((min_r, min_c, max_r, max_c,
                                       None, None, None))
                    elif len(gaps) == 1:
                        gap_r, gap_c = gaps.pop()
                        if gap_r == min_r:
                            gap_side = "top"
                        elif gap_r == max_r:
                            gap_side = "bottom"
                        elif gap_c == min_c:
                            gap_side = "left"
                        else:
                            gap_side = "right"
                        frames.append((min_r, min_c, max_r, max_c,
                                       gap_r, gap_c, gap_side))
        return frames

    # ---- strategy 100: corner seed symmetric frame --------------------------

    def _try_corner_seed_symmetric_frame(self, patterns, wm):
        """
        Detect: odd-dimension square grid with a few non-zero pixels clustered
        in one corner at odd row/col positions. Output = 4-fold symmetric
        nested rectangular frames built from the corner specification.
        Diagonal pixels (r==c in normalized form) are rectangle corners.
        Off-diagonal pixels fill the edges between corners.
        Category: symmetry expansion / nested frames from seed.
        """
        task = wm.task
        if not task or not task.example_pairs:
            return None
        if not patterns.get("grid_size_preserved", False):
            return None

        for pair in task.example_pairs:
            g0, g1 = pair.input_grid, pair.output_grid
            if not g0 or not g1:
                return None
            raw_in = g0.raw
            raw_out = g1.raw
            H, W = len(raw_in), len(raw_in[0])
            if H != W or H % 2 == 0 or H < 5:
                return None

            pixels = []
            for r in range(H):
                for c in range(W):
                    if raw_in[r][c] != 0:
                        pixels.append((r, c, raw_in[r][c]))
            if len(pixels) < 2 or len(pixels) > 30:
                return None
            if not all(r % 2 == 1 and c % 2 == 1 for r, c, v in pixels):
                return None

            center = H // 2
            quadrants = set()
            for r, c, v in pixels:
                qr = 0 if r <= center else 1
                qc = 0 if c <= center else 1
                quadrants.add((qr, qc))
            if len(quadrants) != 1:
                return None
            qr, qc = quadrants.pop()

            normalized = []
            for r, c, v in pixels:
                nr = r if qr == 0 else H - 1 - r
                nc = c if qc == 0 else W - 1 - c
                normalized.append((nr, nc, v))
            normalized.sort()

            expected = self._build_corner_seed_frame(normalized, H, W)
            if expected != raw_out:
                return None

        return {"type": "corner_seed_symmetric_frame", "confidence": 0.95}

    @staticmethod
    def _build_corner_seed_frame(normalized_pixels, H, W):
        """Build the 4-fold symmetric frame output from corner seed pixels."""
        out = [[0] * W for _ in range(H)]

        # Place all 4-reflected pixels
        for r, c, v in normalized_pixels:
            for rr, cc in [(r, c), (r, W - 1 - c),
                           (H - 1 - r, c), (H - 1 - r, W - 1 - c)]:
                out[rr][cc] = v

        # Horizontal edge fills: off-diagonal pixels where c > r
        for r, c, v in normalized_pixels:
            if c > r:
                mirror_c = W - 1 - c
                for fc in range(c, mirror_c + 1, 2):
                    out[r][fc] = v
                    out[H - 1 - r][fc] = v

        # Vertical edge fills: off-diagonal pixels where r > c
        for r, c, v in normalized_pixels:
            if r > c:
                mirror_r = H - 1 - r
                for fr in range(r, mirror_r + 1, 2):
                    out[fr][c] = v
                    out[fr][W - 1 - c] = v

        return out

    # ---- strategy 101: frame corner projectile ------------------------------

    def _try_frame_corner_projectile(self, patterns, wm):
        """
        Detect: L-shaped or U-shaped frame (one color) with enclosed content
        (another color). Diagonal ray of content color shoots from each
        external frame corner into the open space.
        Colors may differ per example; the pattern (not the colors) is the rule.
        Category: frame detection / diagonal projection.
        """
        task = wm.task
        if not task or not task.example_pairs:
            return None
        if not patterns.get("grid_size_preserved", False):
            return None

        from collections import Counter

        bg_color = None

        for pair in task.example_pairs:
            inp = pair.input_grid.raw
            out = pair.output_grid.raw
            H = len(inp)
            W = len(inp[0]) if inp else 0
            freq = Counter()
            for r in range(H):
                for c in range(W):
                    freq[inp[r][c]] += 1
            bg = freq.most_common(1)[0][0]
            non_bg = sorted(set(freq.keys()) - {bg})
            if len(non_bg) != 2:
                return None
            if bg_color is None:
                bg_color = bg
            elif bg_color != bg:
                return None

            # Detect frame/content per example and verify
            fc, cc = self._detect_frame_content(inp, H, W, non_bg)
            if fc is None:
                return None
            predicted = self._compute_frame_projectile(inp, H, W, bg, fc, cc)
            if predicted is None or predicted != out:
                return None

        return {
            "type": "frame_corner_projectile",
            "bg_color": bg_color,
            "confidence": 0.95,
        }

    @staticmethod
    def _detect_frame_content(raw, H, W, non_bg):
        """Detect frame vs content color: frame's bbox contains content's."""
        cells_a = [(r, c) for r in range(H) for c in range(W)
                   if raw[r][c] == non_bg[0]]
        cells_b = [(r, c) for r in range(H) for c in range(W)
                   if raw[r][c] == non_bg[1]]
        if not cells_a or not cells_b:
            return None, None
        bbox_a = (min(r for r, c in cells_a), min(c for r, c in cells_a),
                  max(r for r, c in cells_a), max(c for r, c in cells_a))
        bbox_b = (min(r for r, c in cells_b), min(c for r, c in cells_b),
                  max(r for r, c in cells_b), max(c for r, c in cells_b))
        a_contains_b = (bbox_a[0] <= bbox_b[0] and bbox_a[1] <= bbox_b[1]
                        and bbox_a[2] >= bbox_b[2]
                        and bbox_a[3] >= bbox_b[3])
        b_contains_a = (bbox_b[0] <= bbox_a[0] and bbox_b[1] <= bbox_a[1]
                        and bbox_b[2] >= bbox_a[2]
                        and bbox_b[3] >= bbox_a[3])
        if a_contains_b and not b_contains_a:
            return non_bg[0], non_bg[1]
        if b_contains_a and not a_contains_b:
            return non_bg[1], non_bg[0]
        # Fallback: frame has more cells
        if len(cells_a) >= len(cells_b):
            return non_bg[0], non_bg[1]
        return non_bg[1], non_bg[0]

    @staticmethod
    def _compute_frame_projectile(raw, H, W, bg, fc, cc):
        """Compute output for frame_corner_projectile transformation."""
        # Collect frame and content cells
        frame_cells = set()
        content_cells = set()
        for r in range(H):
            for c in range(W):
                if raw[r][c] == fc:
                    frame_cells.add((r, c))
                elif raw[r][c] == cc:
                    content_cells.add((r, c))
        if not frame_cells or not content_cells:
            return None

        # Find corners: frame cells with exactly 2 perpendicular frame neighbors
        corners = []
        for r, c in frame_cells:
            h_dirs = []
            v_dirs = []
            for dr, dc in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                nr, nc = r + dr, c + dc
                if (nr, nc) in frame_cells:
                    if dr == 0:
                        h_dirs.append((dr, dc))
                    else:
                        v_dirs.append((dr, dc))
            if len(h_dirs) == 1 and len(v_dirs) == 1:
                # Corner with one horizontal and one vertical frame neighbor
                diag_dr = -v_dirs[0][0]
                diag_dc = -h_dirs[0][1]
                corners.append((r, c, diag_dr, diag_dc))

        if not corners:
            return None

        # Check if any corner's diagonal immediately goes out of bounds
        # If so, compute shift needed
        shift_r = 0
        shift_c = 0
        all_cells = frame_cells | content_cells
        min_r = min(r for r, c in all_cells)
        max_r = max(r for r, c in all_cells)
        min_c = min(c for r, c in all_cells)
        max_c = max(c for r, c in all_cells)

        for cr, cc_pos, dr, dc in corners:
            # Check if first diagonal step is out of bounds
            nr, nc = cr + dr, cc_pos + dc
            if nr < 0 or nr >= H or nc < 0 or nc >= W:
                if dr < 0:  # diagonal goes up, shift down
                    shift_r = max(shift_r, H - 1 - max_r)
                elif dr > 0:  # diagonal goes down, shift up
                    shift_r = min(shift_r, -min_r)
                if dc < 0:  # diagonal goes left, shift right
                    shift_c = max(shift_c, W - 1 - max_c)
                elif dc > 0:  # diagonal goes right, shift left
                    shift_c = min(shift_c, -min_c)

        # Build output
        out = [[bg] * W for _ in range(H)]

        # Place shifted frame and content
        for r, c in frame_cells:
            nr, nc = r + shift_r, c + shift_c
            if 0 <= nr < H and 0 <= nc < W:
                out[nr][nc] = fc
        for r, c in content_cells:
            nr, nc = r + shift_r, c + shift_c
            if 0 <= nr < H and 0 <= nc < W:
                out[nr][nc] = cc

        # Draw diagonal rays from shifted corners
        for cr, cc_pos, dr, dc in corners:
            sr, sc = cr + shift_r, cc_pos + shift_c
            r, c = sr + dr, sc + dc
            while 0 <= r < H and 0 <= c < W:
                out[r][c] = cc
                r += dr
                c += dc

        return out


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
        if rule_type == "reverse_concentric_rings":
            return self._apply_reverse_concentric_rings(rule, input_grid)
        if rule_type == "keep_center_column":
            return self._apply_keep_center_column(rule, input_grid)
        if rule_type == "color_mapping":
            return self._apply_color_mapping(rule, input_grid)
        if rule_type == "uniform_scale":
            return self._apply_uniform_scale(rule, input_grid)
        if rule_type == "recolor_by_size":
            return self._apply_recolor_by_size(rule, input_grid)
        if rule_type == "corner_fill":
            return self._apply_corner_fill(rule, input_grid)
        if rule_type == "vertical_mirror":
            return self._apply_vertical_mirror(rule, input_grid)
        if rule_type == "fill_rect_by_size":
            return self._apply_fill_rect_by_size(rule, input_grid)
        if rule_type == "staircase_growth":
            return self._apply_staircase_growth(rule, input_grid)
        if rule_type == "path_trace":
            return self._apply_path_trace(rule, input_grid)
        if rule_type == "diamond_connect":
            return self._apply_diamond_connect(rule, input_grid)
        if rule_type == "cross_grid_fill":
            return self._apply_cross_grid_fill(rule, input_grid)
        if rule_type == "trail_displacement":
            return self._apply_trail_displacement(rule, input_grid)
        if rule_type == "zigzag_warp":
            return self._apply_zigzag_warp(rule, input_grid)
        if rule_type == "gravity_slide":
            return self._apply_gravity_slide(rule, input_grid)
        if rule_type == "arrow_projection":
            return self._apply_arrow_projection(rule, input_grid)
        if rule_type == "quadrant_pattern_swap":
            return self._apply_quadrant_pattern_swap(rule, input_grid)
        if rule_type == "block_wedge_split":
            return self._apply_block_wedge_split(rule, input_grid)
        if rule_type == "block_grid_bar_chart":
            return self._apply_block_grid_bar_chart(rule, input_grid)
        if rule_type == "template_stamp_rotate":
            return self._apply_template_stamp_rotate(rule, input_grid)
        if rule_type == "pixel_count_diamond":
            return self._apply_pixel_count_diamond(rule, input_grid)
        if rule_type == "rotate_tile_2x2":
            return self._apply_rotate_tile_2x2(rule, input_grid)
        if rule_type == "diagonal_extend":
            return self._apply_diagonal_extend(rule, input_grid)
        if rule_type == "quadrant_diagonal_fill":
            return self._apply_quadrant_diagonal_fill(rule, input_grid)
        if rule_type == "corner_ray":
            return self._apply_corner_ray(rule, input_grid)
        if rule_type == "flood_fill_enclosed":
            return self._apply_flood_fill_enclosed(rule, input_grid)
        if rule_type == "count_fill_grid":
            return self._apply_count_fill_grid(rule, input_grid)
        if rule_type == "grid_intersection_summary":
            return self._apply_grid_intersection_summary(rule, input_grid)
        if rule_type == "frame_color_swap":
            return self._apply_frame_color_swap(rule, input_grid)
        if rule_type == "tile_pattern_upward":
            return self._apply_tile_pattern_upward(rule, input_grid)
        if rule_type == "denoise_rectangles":
            return self._apply_denoise_rectangles(rule, input_grid)
        if rule_type == "color_substitution_template":
            return self._apply_color_substitution_template(rule, input_grid)
        if rule_type == "cross_marker_duplicate":
            return self._apply_cross_marker_duplicate(rule, input_grid)
        if rule_type == "border_flood_fill":
            return self._apply_border_flood_fill(rule, input_grid)
        if rule_type == "corner_mark_square":
            return self._apply_corner_mark_square(rule, input_grid)
        if rule_type == "cross_center_mark":
            return self._apply_cross_center_mark(rule, input_grid)
        if rule_type == "mirror_symmetry_recolor":
            return self._apply_mirror_symmetry_recolor(rule, input_grid)
        if rule_type == "rect_pixel_bridge":
            return self._apply_rect_pixel_bridge(rule, input_grid)
        if rule_type == "fractal_block_denoise":
            return self._apply_fractal_block_denoise(rule, input_grid)
        if rule_type == "separator_histogram":
            return self._apply_separator_histogram(rule, input_grid)
        if rule_type == "rotation_quadrant_tile_4x4":
            return self._apply_rotation_quadrant_tile_4x4(rule, input_grid)
        if rule_type == "self_tiling":
            return self._apply_self_tiling(rule, input_grid)
        if rule_type == "double_mirror":
            return self._apply_double_mirror(rule, input_grid)
        if rule_type == "xor_comparison":
            return self._apply_xor_comparison(rule, input_grid)
        if rule_type == "half_grid_boolean":
            return self._apply_half_grid_boolean(rule, input_grid)
        if rule_type == "inverse_tile":
            return self._apply_inverse_tile(rule, input_grid)
        if rule_type == "grid_separator_max_fill":
            return self._apply_grid_separator_max_fill(rule, input_grid)
        if rule_type == "grid_lines_pattern":
            return self._apply_grid_lines_pattern(rule, input_grid)
        if rule_type == "column_shadow_tile":
            return self._apply_column_shadow_tile(rule, input_grid)
        if rule_type == "concentric_ring_rotate":
            return self._apply_concentric_ring_rotate(rule, input_grid)
        if rule_type == "wedge_expansion":
            return self._apply_wedge_expansion(rule, input_grid)
        if rule_type == "mirror_row_tile":
            return self._apply_mirror_row_tile(rule, input_grid)
        if rule_type == "larger_interior_rect":
            return self._apply_larger_interior_rect(rule, input_grid)
        if rule_type == "bbox_fill":
            return self._apply_bbox_fill(rule, input_grid)
        if rule_type == "symmetry_complete":
            return self._apply_symmetry_complete(rule, input_grid)
        if rule_type == "accelerating_sequence":
            return self._apply_accelerating_sequence(rule, input_grid)
        if rule_type == "pixel_collect_snake":
            return self._apply_pixel_collect_snake(rule, input_grid)
        if rule_type == "frame_scale_pattern":
            return self._apply_frame_scale_pattern(rule, input_grid)
        if rule_type == "box_slide_trail":
            return self._apply_box_slide_trail(rule, input_grid)
        if rule_type == "cross_pair_lines":
            return self._apply_cross_pair_lines(rule, input_grid)
        if rule_type == "multi_layer_overlay":
            return self._apply_multi_layer_overlay(rule, input_grid)
        if rule_type == "tile_grid_recolor":
            return self._apply_tile_grid_recolor(rule, input_grid)
        if rule_type == "rect_minority_gridlines":
            return self._apply_rect_minority_gridlines(rule, input_grid)
        if rule_type == "rect_directional_tile":
            return self._apply_rect_directional_tile(rule, input_grid)
        if rule_type == "corner_block_shift":
            return self._apply_corner_block_shift(rule, input_grid)
        if rule_type == "grid_section_key_lookup":
            return self._apply_grid_section_key_lookup(rule, input_grid)
        if rule_type == "shape_template_catalog":
            return self._apply_shape_template_catalog(rule, input_grid)
        if rule_type == "bar_chart_balance":
            return self._apply_bar_chart_balance(rule, input_grid)
        if rule_type == "largest_blob_color":
            return self._apply_largest_blob_color(rule, input_grid)
        if rule_type == "shape_stamp_fill":
            return self._apply_shape_stamp_fill(rule, input_grid)
        if rule_type == "spiral_from_seed":
            return self._apply_spiral_from_seed(rule, input_grid)
        if rule_type == "panel_hole_classify":
            return self._apply_panel_hole_classify(rule, input_grid)
        if rule_type == "grid_panel_decode":
            return self._apply_grid_panel_decode(rule, input_grid)
        if rule_type == "shape_gravity_sort":
            return self._apply_shape_gravity_sort(rule, input_grid)
        if rule_type == "separator_sequence_reflect":
            return self._apply_separator_sequence_reflect(rule, input_grid)
        if rule_type == "stamp_tile_toward_bar":
            return self._apply_stamp_tile_toward_bar(rule, input_grid)
        if rule_type == "shape_jigsaw_assemble":
            return self._apply_shape_jigsaw_assemble(rule, input_grid)
        if rule_type == "stamp_shape_match":
            return self._apply_stamp_shape_match(rule, input_grid)
        if rule_type == "frame_hole_recolor":
            return self._apply_frame_hole_recolor(rule, input_grid)
        if rule_type == "l_corner_complete":
            return self._apply_l_corner_complete(rule, input_grid)
        if rule_type == "quadrant_locator":
            return self._apply_quadrant_locator(rule, input_grid)
        if rule_type == "periodic_pattern_extend":
            return self._apply_periodic_pattern_extend(rule, input_grid)
        if rule_type == "cluster_bbox_border":
            return self._apply_cluster_bbox_border(rule, input_grid)
        if rule_type == "crop_rect_flip":
            return self._apply_crop_rect_flip(rule, input_grid)
        if rule_type == "frame_extract":
            return self._apply_frame_extract(rule, input_grid)
        if rule_type == "marker_shape_extract":
            return self._apply_marker_shape_extract(rule, input_grid)
        if rule_type == "template_placeholder_stamp":
            return self._apply_template_placeholder_stamp(rule, input_grid)
        if rule_type == "unique_quadrant_extract":
            return self._apply_unique_quadrant_extract(rule, input_grid)
        if rule_type == "self_ref_grid_fill":
            return self._apply_self_ref_grid_fill(rule, input_grid)
        if rule_type == "point_reflect_tile":
            return self._apply_point_reflect_tile(rule, input_grid)
        if rule_type == "nested_rect_color_reverse":
            return self._apply_nested_rect_color_reverse(rule, input_grid)
        if rule_type == "diagonal_ring_fill":
            return self._apply_diagonal_ring_fill(rule, input_grid)
        if rule_type == "denoise_isolated":
            return self._apply_denoise_isolated(rule, input_grid)
        if rule_type == "l_diagonal_ray":
            return self._apply_l_diagonal_ray(rule, input_grid)
        if rule_type == "nest_rectangles":
            return self._apply_nest_rectangles(rule, input_grid)
        if rule_type == "column_rank_recolor":
            return self._apply_column_rank_recolor(rule, input_grid)
        if rule_type == "rect_frame_gap_ray":
            return self._apply_rect_frame_gap_ray(rule, input_grid)
        if rule_type == "asymmetric_block_select":
            return self._apply_asymmetric_block_select(rule, input_grid)
        if rule_type == "seed_pixel_stamp":
            return self._apply_seed_pixel_stamp(rule, input_grid)
        if rule_type == "color_count_expand":
            return self._apply_color_count_expand(rule, input_grid)
        if rule_type == "line_rank_recolor":
            return self._apply_line_rank_recolor(rule, input_grid)
        if rule_type == "max_rect_fill":
            return self._apply_max_rect_fill(rule, input_grid)
        if rule_type == "divider_complement_merge":
            return self._apply_divider_complement_merge(rule, input_grid)
        if rule_type == "multi_rect_fill_ray":
            return self._apply_multi_rect_fill_ray(rule, input_grid)
        if rule_type == "corner_seed_symmetric_frame":
            return self._apply_corner_seed_symmetric_frame(rule, input_grid)
        if rule_type == "frame_corner_projectile":
            return self._apply_frame_corner_projectile(rule, input_grid)
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

    def _apply_reverse_concentric_rings(self, rule, input_grid):
        raw = input_grid.raw
        h = len(raw)
        w = len(raw[0]) if raw else 0
        num_rings = (min(h, w) + 1) // 2

        # Extract ring colors from input
        ring_colors = [None] * num_rings
        for r in range(h):
            for c in range(w):
                d = min(r, c, h - 1 - r, w - 1 - c)
                if ring_colors[d] is None:
                    ring_colors[d] = raw[r][c]

        reversed_colors = list(reversed(ring_colors))

        output = []
        for r in range(h):
            row = []
            for c in range(w):
                d = min(r, c, h - 1 - r, w - 1 - c)
                row.append(reversed_colors[d])
            output.append(row)
        return output

    def _apply_keep_center_column(self, rule, input_grid):
        raw = input_grid.raw
        h = len(raw)
        w = len(raw[0]) if raw else 0
        bg = rule.get("bg_color", 0)
        mid_c = w // 2

        output = [[bg] * w for _ in range(h)]
        for r in range(h):
            output[r][mid_c] = raw[r][mid_c]
        return output

    def _apply_color_mapping(self, rule, input_grid):
        raw = input_grid.raw
        mapping = rule.get("mapping", {})

        output = []
        for row in raw:
            output.append([mapping.get(cell, cell) for cell in row])
        return output

    def _apply_uniform_scale(self, rule, input_grid):
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

    def _apply_recolor_by_size(self, rule, input_grid):
        raw = input_grid.raw
        h, w = len(raw), len(raw[0]) if raw else 0
        source_color = rule["source_color"]
        size_to_color = {int(k): v for k, v in rule["size_to_color"].items()}

        obj_positions = [(r, c) for r in range(h) for c in range(w)
                         if raw[r][c] == source_color]
        groups = self._group_positions(obj_positions)

        output = [row[:] for row in raw]
        for group in groups:
            size = len(group)
            color = size_to_color.get(size)
            if color is None:
                closest = min(size_to_color.keys(), key=lambda s: abs(s - size))
                color = size_to_color[closest]
            for r, c in group:
                output[r][c] = color
        return output

    def _apply_corner_fill(self, rule, input_grid):
        raw = input_grid.raw
        h, w = len(raw), len(raw[0]) if raw else 0
        fill_color = rule["fill_color"]
        bg_color = rule.get("bg_color", 0)

        output = [row[:] for row in raw]
        positions = [(r, c) for r in range(h) for c in range(w)
                     if raw[r][c] == fill_color]
        groups = self._group_positions(positions)

        for group in groups:
            rows = [r for r, c in group]
            cols = [c for r, c in group]
            r1, r2 = min(rows), max(rows)
            c1, c2 = min(cols), max(cols)
            rect_h = r2 - r1 + 1
            rect_w = c2 - c1 + 1

            tl_r, tl_c = r1 - 1, c1 - 1
            tr_r, tr_c = r1 - 1, c2 + 1
            bl_r, bl_c = r2 + 1, c1 - 1
            br_r, br_c = r2 + 1, c2 + 1

            if (tl_r < 0 or tl_c < 0 or tr_c >= w or
                    bl_r >= h or br_r >= h or br_c >= w):
                continue

            tl = raw[tl_r][tl_c]
            tr = raw[tr_r][tr_c]
            bl = raw[bl_r][bl_c]
            br = raw[br_r][br_c]

            mid_r = r1 + rect_h // 2
            mid_c = c1 + rect_w // 2

            for r in range(r1, r2 + 1):
                for c in range(c1, c2 + 1):
                    if r < mid_r and c < mid_c:
                        output[r][c] = tl
                    elif r < mid_r and c >= mid_c:
                        output[r][c] = tr
                    elif r >= mid_r and c < mid_c:
                        output[r][c] = bl
                    else:
                        output[r][c] = br

            output[tl_r][tl_c] = bg_color
            output[tr_r][tr_c] = bg_color
            output[bl_r][bl_c] = bg_color
            output[br_r][br_c] = bg_color

        return output

    def _apply_vertical_mirror(self, rule, input_grid):
        raw = input_grid.raw
        output = [row[:] for row in raw]
        for row in reversed(raw):
            output.append(row[:])
        return output

    def _apply_fill_rect_by_size(self, rule, input_grid):
        raw = input_grid.raw
        h, w = len(raw), len(raw[0]) if raw else 0
        frame_color = rule["frame_color"]
        size_to_color = {int(k): v for k, v in rule["size_to_color"].items()}

        output = [row[:] for row in raw]
        positions = [(r, c) for r in range(h) for c in range(w)
                     if raw[r][c] == frame_color]
        groups = self._group_positions(positions)

        for group in groups:
            rows = [r for r, c in group]
            cols = [c for r, c in group]
            r1, r2 = min(rows), max(rows)
            c1, c2 = min(cols), max(cols)
            int_h = r2 - r1 - 1
            int_w = c2 - c1 - 1
            if int_h < 1 or int_w < 1:
                continue

            # Verify it's a rectangular frame before filling
            group_set = set(group)
            is_frame = True
            for r in range(r1, r2 + 1):
                for c in range(c1, c2 + 1):
                    is_border = (r == r1 or r == r2
                                 or c == c1 or c == c2)
                    if is_border and (r, c) not in group_set:
                        is_frame = False
                        break
                    if not is_border and (r, c) in group_set:
                        is_frame = False
                        break
                if not is_frame:
                    break
            if not is_frame:
                continue

            key = min(int_h, int_w)
            fill_c = size_to_color.get(key)
            if fill_c is None and size_to_color:
                closest = min(size_to_color.keys(),
                              key=lambda s: abs(s - key))
                fill_c = size_to_color[closest]
            if fill_c is None:
                continue

            for r in range(r1 + 1, r2):
                for c in range(c1 + 1, c2):
                    output[r][c] = fill_c

        return output

    def _apply_staircase_growth(self, rule, input_grid):
        raw = input_grid.raw
        if len(raw) != 1:
            return [row[:] for row in raw]

        row = raw[0]
        w = len(row)

        # Find color and count
        color = None
        start_count = 0
        for c in range(w):
            if row[c] != 0:
                if color is None:
                    color = row[c]
                start_count += 1
            else:
                break

        if color is None:
            return [row[:]]

        num_rows = w // 2
        output = []
        for r in range(num_rows):
            count = start_count + r
            output.append([color if c < count else 0 for c in range(w)])
        return output

    def _apply_path_trace(self, rule, input_grid):
        raw = input_grid.raw
        h = len(raw)
        w = len(raw[0]) if raw else 0
        start_color = rule["start_color"]
        bg = rule["bg_color"]
        cw_color = rule.get("cw_color")
        ccw_color = rule.get("ccw_color")
        init_dir = tuple(rule["init_dir"])

        CW = {(0, 1): (1, 0), (1, 0): (0, -1),
              (0, -1): (-1, 0), (-1, 0): (0, 1)}
        CCW = {(0, 1): (-1, 0), (-1, 0): (0, -1),
               (0, -1): (1, 0), (1, 0): (0, 1)}

        # Find start and markers
        start = None
        marker_map = {}
        for r in range(h):
            for c in range(w):
                v = raw[r][c]
                if v == start_color:
                    start = (r, c)
                elif v != bg:
                    marker_map[(r, c)] = v

        if start is None:
            return [row[:] for row in raw]

        assign = {}
        if cw_color is not None:
            assign[cw_color] = CW
        if ccw_color is not None:
            assign[ccw_color] = CCW

        return GeneralizeOperator._simulate_path(
            raw, start, init_dir, marker_map, assign, start_color, bg, h, w)

    def _apply_diamond_connect(self, rule, input_grid):
        raw = input_grid.raw
        h = len(raw)
        w = len(raw[0]) if raw else 0
        diamond_color = rule["diamond_color"]
        connector_color = rule["connector_color"]
        bg_color = rule["bg_color"]

        # Find diamond centers
        centers = []
        for r in range(1, h - 1):
            for c in range(1, w - 1):
                if raw[r][c] != bg_color:
                    continue
                neighbors = [raw[r - 1][c], raw[r + 1][c],
                             raw[r][c - 1], raw[r][c + 1]]
                if all(n == diamond_color for n in neighbors):
                    centers.append((r, c))

        return GeneralizeOperator._predict_diamond_connect(
            raw, centers, diamond_color, connector_color, bg_color, h, w)

    def _apply_cross_grid_fill(self, rule, input_grid):
        raw = input_grid.raw
        h = len(raw)
        w = len(raw[0]) if raw else 0
        axis_color = rule["axis_color"]
        intersection_color = rule["intersection_color"]
        bg_color = rule["bg_color"]

        # Find axis column from this input
        axis_col = None
        for c in range(w):
            col_vals = set(raw[r][c] for r in range(h))
            if bg_color not in col_vals and len(col_vals) <= 2:
                if axis_color in col_vals:
                    axis_col = c
                    break

        if axis_col is None:
            return [row[:] for row in raw]

        # Find colored rows from the input
        colored_rows = []
        for r in range(h):
            if raw[r][axis_col] == intersection_color:
                row_colors = set()
                for c in range(w):
                    if c == axis_col:
                        continue
                    if raw[r][c] != bg_color:
                        row_colors.add(raw[r][c])
                if len(row_colors) == 1:
                    colored_rows.append((r, row_colors.pop()))

        return GeneralizeOperator._predict_cross_grid_fill(
            h, w, axis_col, axis_color, intersection_color,
            bg_color, colored_rows)

    def _apply_trail_displacement(self, rule, input_grid):
        raw = input_grid.raw
        h = len(raw)
        w = len(raw[0]) if raw else 0
        sep_color = rule["sep_color"]
        bg = rule["bg_color"]
        target_color = rule["target_color"]
        active_color = rule["active_color"]
        trail_color = rule["trail_color"]

        # Find separator row
        sep_row = None
        for r in range(h):
            if len(set(raw[r])) == 1 and raw[r][0] == sep_color:
                sep_row = r
                break

        if sep_row is None:
            return [row[:] for row in raw]

        return GeneralizeOperator._predict_trail_displacement(
            raw, sep_row, sep_color, bg, target_color, active_color, trail_color)

    def _apply_zigzag_warp(self, rule, input_grid):
        raw = input_grid.raw
        h = len(raw)
        w = len(raw[0]) if raw else 0

        bg = raw[0][0]

        # Find frame bounding box
        top_r = bot_r = None
        for r in range(h):
            for c in range(w):
                if raw[r][c] != bg:
                    if top_r is None:
                        top_r = r
                    bot_r = r

        if top_r is None:
            return [row[:] for row in raw]

        frame_h = bot_r - top_r + 1
        internal_rows = frame_h - 2
        if internal_rows < 1:
            return [row[:] for row in raw]

        phase = (1 - internal_rows) % 4
        CYCLE = [0, -1, 0, 1]

        output = [row[:] for row in raw]
        for row_idx in range(frame_h):
            r = top_r + row_idx
            offset = CYCLE[(phase + row_idx) % 4]
            if offset == 0:
                continue
            new_row = [bg] * w
            for c in range(w):
                src_c = c - offset
                if 0 <= src_c < w:
                    new_row[c] = raw[r][src_c]
            output[r] = new_row

        return output

    def _apply_gravity_slide(self, rule, input_grid):
        raw = input_grid.raw
        h = len(raw)
        w = len(raw[0]) if raw else 0
        bg = rule["bg_color"]

        freq = {}
        for r in range(h):
            for c in range(w):
                freq[raw[r][c]] = freq.get(raw[r][c], 0) + 1

        non_bg = [c for c in freq if c != bg]
        if len(non_bg) != 2:
            return [row[:] for row in raw]

        # Wall = non-bg color that appears in the last row (or first row/col)
        # Try last row first, then first col, then first row
        wall_color = None
        for check_cells in [
            [(h - 1, c) for c in range(w)],
            [(r, 0) for r in range(h)],
            [(0, c) for c in range(w)],
        ]:
            counts = {}
            for r2, c2 in check_cells:
                v = raw[r2][c2]
                if v != bg:
                    counts[v] = counts.get(v, 0) + 1
            if counts:
                wall_color = max(counts, key=counts.get)
                break

        if wall_color is None:
            return [row[:] for row in raw]

        obj_candidates = [c for c in non_bg if c != wall_color]
        if len(obj_candidates) != 1:
            return [row[:] for row in raw]

        return GeneralizeOperator._predict_gravity_slide(
            raw, bg, wall_color, obj_candidates[0], h, w)

    def _apply_arrow_projection(self, rule, input_grid):
        raw = input_grid.raw
        h = len(raw)
        w = len(raw[0]) if raw else 0

        # Detect bg as most frequent color
        freq = {}
        for r in range(h):
            for c in range(w):
                freq[raw[r][c]] = freq.get(raw[r][c], 0) + 1
        bg = max(freq, key=freq.get)

        shape_infos = GeneralizeOperator._detect_arrow_shapes(raw, bg, h, w)
        if not shape_infos:
            return [row[:] for row in raw]

        return GeneralizeOperator._predict_arrow_projection(
            raw, bg, shape_infos, h, w)

    def _apply_quadrant_pattern_swap(self, rule, input_grid):
        raw = input_grid.raw
        h = len(raw)
        w = len(raw[0]) if raw else 0
        output = [row[:] for row in raw]

        # Find separator columns
        sep_cols = [c for c in range(w)
                    if all(raw[r][c] == 0 for r in range(h))]
        if not sep_cols:
            return output

        left_c0, left_c1 = 0, sep_cols[0] - 1
        right_c0, right_c1 = sep_cols[-1] + 1, w - 1

        # Find separator rows
        sep_row_set = set()
        for r in range(h):
            if all(raw[r][c] == 0 for c in range(w)):
                sep_row_set.add(r)

        # Build sections
        sections = []
        r = 0
        while r < h:
            if r in sep_row_set:
                r += 1
                continue
            start = r
            while r < h and r not in sep_row_set:
                r += 1
            sections.append((start, r - 1))

        for rs, re in sections:
            left_bg = GeneralizeOperator._quadrant_bg(raw, rs, re, left_c0, left_c1)
            right_bg = GeneralizeOperator._quadrant_bg(raw, rs, re, right_c0, right_c1)
            left_pat = GeneralizeOperator._quadrant_fg(raw, rs, re, left_c0, left_c1, left_bg)
            right_pat = GeneralizeOperator._quadrant_fg(raw, rs, re, right_c0, right_c1, right_bg)

            if left_bg == right_bg:
                for r in range(rs, re + 1):
                    for c in range(left_c0, left_c1 + 1):
                        output[r][c] = left_bg
                    for c in range(right_c0, right_c1 + 1):
                        output[r][c] = right_bg
            else:
                for r in range(rs, re + 1):
                    for c in range(left_c0, left_c1 + 1):
                        rel = (r - rs, c - left_c0)
                        output[r][c] = right_bg if rel in right_pat else left_bg
                    for c in range(right_c0, right_c1 + 1):
                        rel = (r - rs, c - right_c0)
                        output[r][c] = left_bg if rel in left_pat else right_bg

        return output

    def _apply_block_wedge_split(self, rule, input_grid):
        raw = input_grid.raw
        h = len(raw)
        w = len(raw[0]) if raw else 0

        # Find bg
        freq = {}
        for r in range(h):
            for c in range(w):
                freq[raw[r][c]] = freq.get(raw[r][c], 0) + 1
        bg = max(freq, key=freq.get)

        result = GeneralizeOperator._detect_blocks_and_split(raw, bg, h, w)
        if result is None:
            return [row[:] for row in raw]

        block_infos, mid_info = result
        idx_mid = mid_info["mid"]
        idx_low = mid_info["low"]
        idx_high = mid_info["high"]
        axis = mid_info["axis"]

        b_mid = block_infos[idx_mid]
        b_low = block_infos[idx_low]
        b_high = block_infos[idx_high]

        perp = "c" if axis == "r" else "r"

        # Determine which block to insert into: the one whose perpendicular
        # extent is strictly > mid's perpendicular extent; prefer tighter fit
        mid_perp = b_mid[f"{perp}1"] - b_mid[f"{perp}0"] + 1
        low_perp = b_low[f"{perp}1"] - b_low[f"{perp}0"] + 1
        high_perp = b_high[f"{perp}1"] - b_high[f"{perp}0"] + 1

        # Determine target: prefer the rectangular block; tiebreak by larger perp
        def _is_rect(b):
            return len(b["cells"]) == (b["r1"] - b["r0"] + 1) * (b["c1"] - b["c0"] + 1)

        low_rect = _is_rect(b_low)
        high_rect = _is_rect(b_high)

        if low_rect and not high_rect:
            target_idx = idx_low
        elif high_rect and not low_rect:
            target_idx = idx_high
        elif low_perp > high_perp:
            target_idx = idx_low
        elif high_perp > low_perp:
            target_idx = idx_high
        elif low_perp > mid_perp:
            target_idx = idx_low
        else:
            target_idx = idx_high

        anchor_idx = idx_high if target_idx == idx_low else idx_low

        b_target = block_infos[target_idx]
        b_anchor = block_infos[anchor_idx]

        # Movement direction: mid moves toward target, away from anchor
        if axis == "r":
            # Blocks stacked vertically
            mid_center = (b_mid["r0"] + b_mid["r1"]) / 2
            target_center = (b_target["r0"] + b_target["r1"]) / 2
            move_dir = 1 if target_center > mid_center else -1
        else:
            mid_center = (b_mid["c0"] + b_mid["c1"]) / 2
            target_center = (b_target["c0"] + b_target["c1"]) / 2
            move_dir = 1 if target_center > mid_center else -1

        # Build output
        output = [[bg] * w for _ in range(h)]

        # Place anchor block unchanged
        for r, c in b_anchor["cells"]:
            output[r][c] = b_anchor["color"]

        # Compute target split
        target_perp = b_target[f"{perp}1"] - b_target[f"{perp}0"] + 1
        half_size = target_perp // 2

        # Target's perpendicular center
        target_perp_center = (b_target[f"{perp}0"] + b_target[f"{perp}1"]) / 2

        # Each half shifts outward by mid_perp/2
        shift = (mid_perp + 1) // 2  # round up for odd

        # Build target cell map relative to bounding box
        target_cells_by_rel = {}
        for r, c in b_target["cells"]:
            if perp == "c":
                rel_perp = c - b_target["c0"]
                along = r
            else:
                rel_perp = r - b_target["r0"]
                along = c
            target_cells_by_rel.setdefault(rel_perp, []).append(along)

        # Split target into low-half and high-half
        for rel_perp, alongs in target_cells_by_rel.items():
            if rel_perp < half_size:
                # Low half -- shift toward lower perp values
                new_perp = b_target[f"{perp}0"] + rel_perp - shift
            else:
                # High half -- shift toward higher perp values
                new_perp = b_target[f"{perp}0"] + rel_perp + shift

            for along_val in alongs:
                if perp == "c":
                    nr, nc = along_val, new_perp
                else:
                    nr, nc = new_perp, along_val
                if 0 <= nr < h and 0 <= nc < w:
                    output[nr][nc] = b_target["color"]

        # Place mid block at its new position (clamped to grid bounds)
        mid_depth = b_mid[f"{axis}1"] - b_mid[f"{axis}0"] + 1
        target_depth = b_target[f"{axis}1"] - b_target[f"{axis}0"] + 1

        if axis == "r":
            if move_dir > 0:
                if mid_depth < target_depth:
                    new_r0 = b_target["r1"] + 1 - mid_depth
                else:
                    new_r0 = b_target["r1"] + 1
                new_r0 = max(0, min(new_r0, h - mid_depth))
            else:
                if mid_depth < target_depth:
                    new_r0 = b_target["r0"]
                else:
                    new_r0 = b_target["r0"] - mid_depth
                new_r0 = max(0, min(new_r0, h - mid_depth))
            new_c0 = b_mid["c0"]
            for r, c in b_mid["cells"]:
                nr = new_r0 + (r - b_mid["r0"])
                nc = new_c0 + (c - b_mid["c0"])
                if 0 <= nr < h and 0 <= nc < w:
                    output[nr][nc] = b_mid["color"]
        else:
            if move_dir > 0:
                if mid_depth < target_depth:
                    new_c0 = b_target["c1"] + 1 - mid_depth
                else:
                    new_c0 = b_target["c1"] + 1
                new_c0 = max(0, min(new_c0, w - mid_depth))
            else:
                if mid_depth < target_depth:
                    new_c0 = b_target["c0"]
                else:
                    new_c0 = b_target["c0"] - mid_depth
                new_c0 = max(0, min(new_c0, w - mid_depth))
            new_r0 = b_mid["r0"]
            for r, c in b_mid["cells"]:
                nr = new_r0 + (r - b_mid["r0"])
                nc = new_c0 + (c - b_mid["c0"])
                if 0 <= nr < h and 0 <= nc < w:
                    output[nr][nc] = b_mid["color"]

        return output

    def _apply_block_grid_bar_chart(self, rule, input_grid):
        result = GeneralizeOperator._solve_bar_chart(input_grid.raw)
        return result if result is not None else [row[:] for row in input_grid.raw]

    def _apply_template_stamp_rotate(self, rule, input_grid):
        raw = input_grid.raw
        h = len(raw)
        w = len(raw[0]) if raw else 0
        freq = {}
        for r in range(h):
            for c in range(w):
                freq[raw[r][c]] = freq.get(raw[r][c], 0) + 1
        bg = max(freq, key=freq.get)
        result = GeneralizeOperator._solve_template_stamp(raw, bg, h, w)
        if result is not None:
            return result[0]
        return [row[:] for row in raw]

    def _apply_pixel_count_diamond(self, rule, input_grid):
        """
        Count two non-bg colors in input. Larger count = width, smaller = height.
        Create 16×16 grid with bottom-left rectangle (filled with 2) and
        diagonal X lines from bottom corners (drawn with 4).
        """
        raw = input_grid.raw
        bg = rule.get("bg", 7)

        # Count non-background colors
        from collections import Counter
        freq = Counter()
        for row in raw:
            for v in row:
                if v != bg:
                    freq[v] += 1

        if len(freq) != 2:
            return [[bg] * 16 for _ in range(16)]

        counts = sorted(freq.values(), reverse=True)
        width = counts[0]
        height = counts[1]

        # Clamp to 16×16
        width = min(width, 16)
        height = min(height, 16)

        out_size = 16
        grid = [[bg] * out_size for _ in range(out_size)]

        start_row = out_size - height

        for r in range(start_row, out_size):
            for c in range(width):
                grid[r][c] = 2

        # Draw diagonal lines from bottom corners
        for r in range(start_row, out_size):
            d = (out_size - 1) - r  # distance from bottom row
            left_col = d
            right_col = (width - 1) - d
            if 0 <= left_col < width:
                grid[r][left_col] = 4
            if 0 <= right_col < width:
                grid[r][right_col] = 4

        return grid

    def _apply_rotate_tile_2x2(self, rule, input_grid):
        """Tile 4 rotations of input into 2×2 output grid."""
        raw = input_grid.raw
        h = len(raw)
        w = len(raw[0]) if raw else 0
        if h == 0 or w == 0 or h != w:
            return None
        orig = [row[:] for row in raw]
        ccw90 = GeneralizeOperator._rotate_ccw90(orig)
        rot180 = GeneralizeOperator._rotate_180(orig)
        cw90 = GeneralizeOperator._rotate_cw90(orig)

        out = [[0] * (2 * w) for _ in range(2 * h)]
        for r in range(h):
            for c in range(w):
                out[r][c] = orig[r][c]
                out[r][w + c] = ccw90[r][c]
                out[h + r][c] = rot180[r][c]
                out[h + r][w + c] = cw90[r][c]
        return out

    def _apply_diagonal_extend(self, rule, input_grid):
        """Extend diagonal tails from 2×2 block to grid edges."""
        raw = input_grid.raw
        h = len(raw)
        w = len(raw[0]) if raw else 0
        out = [row[:] for row in raw]

        fg_color = None
        fg_positions = []
        for r in range(h):
            for c in range(w):
                if raw[r][c] != 0:
                    fg_positions.append((r, c))
                    if fg_color is None:
                        fg_color = raw[r][c]

        if fg_color is None:
            return out

        block_pos = None
        for r in range(h - 1):
            for c in range(w - 1):
                if (raw[r][c] == fg_color and raw[r][c + 1] == fg_color and
                        raw[r + 1][c] == fg_color and raw[r + 1][c + 1] == fg_color):
                    block_pos = (r, c)
                    break
            if block_pos:
                break

        if block_pos is None:
            return out

        blk_r, blk_c = block_pos
        block_cells = {(blk_r, blk_c), (blk_r, blk_c + 1),
                       (blk_r + 1, blk_c), (blk_r + 1, blk_c + 1)}
        tails = [(r, c) for r, c in fg_positions if (r, c) not in block_cells]

        center_r = blk_r + 0.5
        center_c = blk_c + 0.5
        for tr, tc in tails:
            dr = 1 if tr > center_r else -1
            dc = 1 if tc > center_c else -1
            nr, nc = tr + dr, tc + dc
            while 0 <= nr < h and 0 <= nc < w:
                out[nr][nc] = fg_color
                nr += dr
                nc += dc

        return out

    def _apply_quadrant_diagonal_fill(self, rule, input_grid):
        """Fill corner regions with diagonally opposite colors from 2×2 seed."""
        raw = input_grid.raw
        h = len(raw)
        w = len(raw[0]) if raw else 0
        out = [row[:] for row in raw]

        block_pos = None
        block_colors = None
        for r in range(h - 1):
            for c in range(w - 1):
                tl = raw[r][c]
                tr = raw[r][c + 1]
                bl = raw[r + 1][c]
                br = raw[r + 1][c + 1]
                if tl != 0 and tr != 0 and bl != 0 and br != 0:
                    if len({tl, tr, bl, br}) == 4:
                        block_pos = (r, c)
                        block_colors = (tl, tr, bl, br)
                        break
            if block_pos:
                break

        if block_pos is None:
            return out

        blk_r, blk_c = block_pos
        tl_c, tr_c, bl_c, br_c = block_colors

        # Place 2×2 fills at diagonal neighbors, clipped to grid boundaries
        for r in range(max(0, blk_r - 2), blk_r):
            for c in range(max(0, blk_c - 2), blk_c):
                out[r][c] = br_c
        for r in range(max(0, blk_r - 2), blk_r):
            for c in range(blk_c + 2, min(w, blk_c + 4)):
                out[r][c] = bl_c
        for r in range(blk_r + 2, min(h, blk_r + 4)):
            for c in range(max(0, blk_c - 2), blk_c):
                out[r][c] = tr_c
        for r in range(blk_r + 2, min(h, blk_r + 4)):
            for c in range(blk_c + 2, min(w, blk_c + 4)):
                out[r][c] = tl_c

        return out

    # ---- apply: corner ray projection --------------------------------------

    def _apply_corner_ray(self, rule, input_grid):
        raw = input_grid.raw
        h = len(raw)
        w = len(raw[0]) if raw else 0
        out = [[0] * w for _ in range(h)]

        for r in range(h):
            for c in range(w):
                if raw[r][c] != 0:
                    color = raw[r][c]
                    corners = [
                        (0, 0, r + c),
                        (0, w - 1, r + (w - 1 - c)),
                        (h - 1, 0, (h - 1 - r) + c),
                        (h - 1, w - 1, (h - 1 - r) + (w - 1 - c)),
                    ]
                    corners.sort(key=lambda x: x[2])
                    cr, cc, _ = corners[0]

                    for rr in range(min(r, cr), max(r, cr) + 1):
                        out[rr][c] = color
                    for cc2 in range(min(c, cc), max(c, cc) + 1):
                        out[r][cc2] = color

        return out

    # ---- apply: flood fill enclosed regions --------------------------------

    def _apply_flood_fill_enclosed(self, rule, input_grid):
        raw = input_grid.raw
        h = len(raw)
        w = len(raw[0]) if raw else 0
        out = [row[:] for row in raw]

        reachable = [[False] * w for _ in range(h)]
        queue = []
        for r in range(h):
            for c in range(w):
                if (r == 0 or r == h - 1 or c == 0 or c == w - 1) and raw[r][c] == 0:
                    if not reachable[r][c]:
                        reachable[r][c] = True
                        queue.append((r, c))

        qi = 0
        while qi < len(queue):
            r, c = queue[qi]
            qi += 1
            for dr, dc in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                nr, nc = r + dr, c + dc
                if 0 <= nr < h and 0 <= nc < w and not reachable[nr][nc] and raw[nr][nc] == 0:
                    reachable[nr][nc] = True
                    queue.append((nr, nc))

        for r in range(h):
            for c in range(w):
                if raw[r][c] == 0 and not reachable[r][c]:
                    out[r][c] = 1

        return out

    # ---- apply: count fill grid (3×3) --------------------------------------

    def _apply_count_fill_grid(self, rule, input_grid):
        raw = input_grid.raw
        h = len(raw)
        w = len(raw[0]) if raw else 0

        ones = [(r, c) for r in range(h) for c in range(w) if raw[r][c] == 1]
        if not ones:
            return [[0, 0, 0] for _ in range(3)]

        min_r = min(r for r, c in ones)
        max_r = max(r for r, c in ones)
        min_c = min(c for r, c in ones)
        max_c = max(c for r, c in ones)

        signal_color = 0
        for r in range(h):
            for c in range(w):
                v = raw[r][c]
                if v != 0 and v != 1:
                    signal_color = v
                    break
            if signal_color:
                break

        inside_count = 0
        for r in range(min_r + 1, max_r):
            for c in range(min_c + 1, max_c):
                if raw[r][c] == signal_color:
                    inside_count += 1

        out = [[0, 0, 0] for _ in range(3)]
        filled = 0
        for r in range(3):
            for c in range(3):
                if filled < inside_count:
                    out[r][c] = signal_color
                    filled += 1

        return out

    def _apply_grid_intersection_summary(self, rule, input_grid):
        """Extract grid intersection colors and produce summary grid."""
        raw = input_grid.raw
        info = GeneralizeOperator._detect_grid_separators(raw)
        if info is None:
            return [row[:] for row in raw]

        grid_color, sep_rows, sep_cols = info

        # Build intersection grid
        int_grid = []
        for sr in sep_rows:
            row_vals = []
            for sc in sep_cols:
                row_vals.append(raw[sr][sc])
            int_grid.append(row_vals)

        # Find bounding box of non-grid intersections
        marked_rows = []
        marked_cols = []
        for ri in range(len(sep_rows)):
            for ci in range(len(sep_cols)):
                if int_grid[ri][ci] != grid_color:
                    marked_rows.append(ri)
                    marked_cols.append(ci)

        if not marked_rows:
            return [[0]]

        min_ri = min(marked_rows)
        max_ri = max(marked_rows)
        min_ci = min(marked_cols)
        max_ci = max(marked_cols)

        n_rows = max_ri - min_ri + 1
        n_cols = max_ci - min_ci + 1

        # Build output: (n_rows-1) x (n_cols-1)
        out = []
        for i in range(n_rows - 1):
            row = []
            for j in range(n_cols - 1):
                tl = int_grid[min_ri + i][min_ci + j]
                tr = int_grid[min_ri + i][min_ci + j + 1]
                bl = int_grid[min_ri + i + 1][min_ci + j]
                br = int_grid[min_ri + i + 1][min_ci + j + 1]
                if (tl == tr == bl == br) and tl != grid_color:
                    row.append(tl)
                else:
                    row.append(0)
            out.append(row)

        return out if out else [[0]]

    def _apply_frame_color_swap(self, rule, input_grid):
        """Extract rectangle, swap border and interior colors."""
        raw = input_grid.raw
        h = len(raw)
        w = len(raw[0]) if raw else 0

        # Find non-zero bounding box
        nz = [(r, c) for r in range(h) for c in range(w) if raw[r][c] != 0]
        if not nz:
            return [row[:] for row in raw]

        min_r = min(r for r, c in nz)
        max_r = max(r for r, c in nz)
        min_c = min(c for r, c in nz)
        max_c = max(c for r, c in nz)

        rect_h = max_r - min_r + 1
        rect_w = max_c - min_c + 1

        # Extract rectangle
        rect = []
        for r in range(min_r, max_r + 1):
            rect.append([raw[r][c] for c in range(min_c, max_c + 1)])

        border_color = rect[0][0]

        # Find interior color
        interior_color = None
        for r in range(rect_h):
            for c in range(rect_w):
                on_border = (r == 0 or r == rect_h - 1 or c == 0 or c == rect_w - 1)
                if not on_border and rect[r][c] != border_color:
                    interior_color = rect[r][c]
                    break
            if interior_color is not None:
                break

        if interior_color is None:
            return rect

        # Swap colors
        out = []
        for r in range(rect_h):
            row = []
            for c in range(rect_w):
                if rect[r][c] == border_color:
                    row.append(interior_color)
                elif rect[r][c] == interior_color:
                    row.append(border_color)
                else:
                    row.append(rect[r][c])
            out.append(row)

        return out

    def _apply_tile_pattern_upward(self, rule, input_grid):
        """Tile bottom pattern upward to fill entire grid."""
        raw = input_grid.raw
        h = len(raw)
        w = len(raw[0]) if raw else 0

        # Find background color
        bg = raw[0][0]

        # Find first non-bg row
        first_non_bg_row = None
        for r in range(h):
            if any(raw[r][c] != bg for c in range(w)):
                first_non_bg_row = r
                break

        if first_non_bg_row is None or first_non_bg_row == 0:
            return [row[:] for row in raw]

        # Extract pattern
        pattern = [raw[r][:] for r in range(first_non_bg_row, h)]
        pattern_len = len(pattern)

        # Tile from bottom upward
        out = [[0] * w for _ in range(h)]
        for r in range(h):
            # Distance from bottom
            dist_from_bottom = h - 1 - r
            pattern_idx = pattern_len - 1 - (dist_from_bottom % pattern_len)
            out[r] = pattern[pattern_idx][:]

        return out

    # ---- apply: denoise rectangles ----------------------------------------

    def _apply_denoise_rectangles(self, rule, input_grid):
        """Remove noise pixels, keep only largest inscribed rectangles."""
        raw = input_grid.raw
        h = len(raw)
        w = len(raw[0]) if raw else 0

        # Find foreground color (the single non-zero color)
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

        # Find connected components
        fg_cells = [(r, c) for r in range(h) for c in range(w) if raw[r][c] == fg]
        components = self._group_positions(fg_cells)

        # Build output with only rectangle cores
        out = [[0] * w for _ in range(h)]
        for comp in components:
            rect = GeneralizeOperator._largest_inscribed_rect(comp)
            for r, c in rect:
                out[r][c] = fg

        return out

    # ---- apply: color substitution template --------------------------------

    def _apply_color_substitution_template(self, rule, input_grid):
        """Extract template, apply color substitution from scattered pairs."""
        raw = input_grid.raw
        result = GeneralizeOperator._analyze_color_sub_template(raw)
        if result is None:
            return [row[:] for row in raw]

        template_block, border_color, color_map = result

        out = []
        for row in template_block:
            out_row = []
            for c in row:
                if c == border_color:
                    out_row.append(c)
                else:
                    out_row.append(color_map.get(c, c))
            out.append(out_row)

        return out

    # ---- apply: cross marker duplicate -------------------------------------

    def _apply_cross_marker_duplicate(self, rule, input_grid):
        """Find cross patterns, return 1×1 grid with duplicated arm color."""
        raw = input_grid.raw
        center_color = rule.get("center_color", 4)
        crosses = GeneralizeOperator._find_cross_patterns(raw, center_color)

        from collections import Counter
        arm_counts = Counter(crosses.values())

        for color, count in arm_counts.items():
            if count >= 2:
                return [[color]]

        return [[0]]

    # ---- apply: border flood fill ------------------------------------------

    def _apply_border_flood_fill(self, rule, input_grid):
        raw = input_grid.raw
        h = len(raw)
        w = len(raw[0]) if raw else 0
        sc = rule["source_color"]
        bc = rule["border_color"]
        ic = rule["interior_color"]

        out = [row[:] for row in raw]
        reachable = GeneralizeOperator._bfs_border(raw, sc, h, w)

        for r in range(h):
            for c in range(w):
                if raw[r][c] == sc:
                    out[r][c] = bc if reachable[r][c] else ic
        return out

    # ---- apply: corner mark square -----------------------------------------

    def _apply_corner_mark_square(self, rule, input_grid):
        raw = input_grid.raw
        h = len(raw)
        w = len(raw[0]) if raw else 0
        mc = rule["mark_color"]

        from collections import Counter
        counts = Counter()
        for r in range(h):
            for c in range(w):
                counts[raw[r][c]] += 1
        bg = counts.most_common(1)[0][0]

        non_bg = [(r, c) for r in range(h) for c in range(w) if raw[r][c] != bg]
        groups = GeneralizeOperator._cc_group(non_bg)

        out = [row[:] for row in raw]
        for group in groups:
            if len(group) < 4:
                continue
            group_set = set(group)
            rows_g = [r for r, c in group]
            cols_g = [c for r, c in group]
            r1, r2 = min(rows_g), max(rows_g)
            c1, c2 = min(cols_g), max(cols_g)
            bh = r2 - r1 + 1
            bw = c2 - c1 + 1
            if bh != bw or bh < 2:
                continue
            if not all((r, c) in group_set
                       for r, c in [(r1, c1), (r1, c2), (r2, c1), (r2, c2)]):
                continue
            for cr, cc in [(r1, c1), (r1, c2), (r2, c1), (r2, c2)]:
                dr = -1 if cr == r1 else 1
                dc = -1 if cc == c1 else 1
                nr = cr + dr
                if 0 <= nr < h:
                    out[nr][cc] = mc
                nc = cc + dc
                if 0 <= nc < w:
                    out[cr][nc] = mc
        return out

    # ---- apply: cross center mark ------------------------------------------

    def _apply_cross_center_mark(self, rule, input_grid):
        raw = input_grid.raw
        h = len(raw)
        w = len(raw[0]) if raw else 0
        bg = rule["bg"]
        fg = rule["fg"]
        mark = rule["mark"]

        out = [row[:] for row in raw]
        centers = GeneralizeOperator._find_domino_cross_centers(raw, bg, fg, h, w)
        for r, c in centers:
            out[r][c] = mark
        return out

    def _apply_mirror_symmetry_recolor(self, rule, input_grid):
        raw = input_grid.raw
        H = len(raw)
        W = len(raw[0]) if raw else 0
        fg_color = rule["fg_color"]
        new_color = rule["new_color"]

        out = [row[:] for row in raw]
        for r in range(H):
            for c in range(W):
                if raw[r][c] == fg_color:
                    mirror_c = W - 1 - c
                    if raw[r][mirror_c] == fg_color:
                        out[r][c] = new_color
        return out

    def _apply_rect_pixel_bridge(self, rule, input_grid):
        raw = input_grid.raw
        H = len(raw)
        W = len(raw[0]) if raw else 0

        # Detect bg
        from collections import Counter
        counts = Counter()
        for r in range(H):
            for c in range(W):
                counts[raw[r][c]] += 1
        bg = counts.most_common(1)[0][0]

        out = [row[:] for row in raw]

        # Find all non-bg colors
        color_cells = {}
        for r in range(H):
            for c in range(W):
                v = raw[r][c]
                if v != bg:
                    color_cells.setdefault(v, []).append((r, c))

        for color, cells in color_cells.items():
            rects, isolates = GeneralizeOperator._find_rects_and_isolates(
                None, cells, color, raw, H, W, bg
            )
            if not rects or not isolates:
                continue
            for iso_r, iso_c in isolates:
                GeneralizeOperator._draw_bridge(
                    None, out, rects, iso_r, iso_c, color, bg, H, W
                )
        return out

    def _apply_fractal_block_denoise(self, rule, input_grid):
        raw = input_grid.raw
        H = len(raw)
        W = len(raw[0]) if raw else 0

        # Find separator lines
        sep_rows = GeneralizeOperator._find_separator_lines(None, raw, H, W, 'row')
        sep_cols = GeneralizeOperator._find_separator_lines(None, raw, H, W, 'col')

        row_ranges = GeneralizeOperator._get_ranges(None, sep_rows, H)
        col_ranges = GeneralizeOperator._get_ranges(None, sep_cols, W)

        if not row_ranges or not col_ranges:
            return [row[:] for row in raw]

        block_h = row_ranges[0][1] - row_ranges[0][0] + 1
        block_w = col_ranges[0][1] - col_ranges[0][0] + 1
        n_block_rows = len(row_ranges)
        n_block_cols = len(col_ranges)

        # Extract blocks, clean noise (5 → ignore)
        blocks_clean = []
        for ri, (r0, r1) in enumerate(row_ranges):
            row_blocks = []
            for ci, (c0, c1) in enumerate(col_ranges):
                block = []
                for r in range(r0, r1 + 1):
                    row_data = []
                    for c in range(c0, c1 + 1):
                        v = raw[r][c]
                        row_data.append(v if v != 5 else None)
                    block.append(row_data)
                row_blocks.append(block)
            blocks_clean.append(row_blocks)

        # Find template: block with exactly 2 non-zero, non-5 colors and no None/5
        # Try to find a clean block first
        template = None
        dominant_color = None
        minority_color = None

        for ri in range(n_block_rows):
            for ci in range(n_block_cols):
                block = blocks_clean[ri][ci]
                colors = set()
                has_none = False
                for row in block:
                    for v in row:
                        if v is None:
                            has_none = True
                        elif v != 5:
                            colors.add(v)
                if has_none:
                    continue
                if len(colors) == 2:
                    from collections import Counter
                    cnt = Counter()
                    for row in block:
                        for v in row:
                            if v is not None:
                                cnt[v] += 1
                    dominant_color = cnt.most_common(1)[0][0]
                    colors.discard(dominant_color)
                    minority_color = colors.pop()
                    template = [row[:] for row in block]
                    break
            if template is not None:
                break

        if template is None or dominant_color is None:
            return [row[:] for row in raw]

        # Build output
        pure_block = [[dominant_color]*block_w for _ in range(block_h)]

        out = [[0]*W for _ in range(H)]

        # Fill separator lines with 0
        for sr in sep_rows:
            for c in range(W):
                out[sr][c] = 0
        for sc in sep_cols:
            for r in range(H):
                out[r][sc] = 0

        # Fill blocks based on self-similar rule
        t_rows = len(template)
        t_cols = len(template[0]) if template else 0
        for bi in range(n_block_rows):
            for bj in range(n_block_cols):
                # Determine which block to place
                if bi < t_rows and bj < t_cols:
                    if template[bi][bj] == minority_color:
                        source = template
                    else:
                        source = pure_block
                else:
                    source = pure_block

                r0, r1 = row_ranges[bi]
                c0, c1 = col_ranges[bj]
                actual_h = r1 - r0 + 1
                actual_w = c1 - c0 + 1
                for dr in range(min(actual_h, len(source))):
                    for dc in range(min(actual_w, len(source[0]) if source else 0)):
                        if r0 + dr < H and c0 + dc < W:
                            out[r0 + dr][c0 + dc] = source[dr][dc]

        return out

    # ---- apply: separator histogram ----------------------------------------

    def _apply_separator_histogram(self, rule, input_grid):
        raw = input_grid.raw
        params = GeneralizeOperator._sep_hist_detect(raw)
        if params is None:
            return [row[:] for row in raw]
        return GeneralizeOperator._sep_hist_build(raw, params)

    # ---- apply: rotation quadrant tile 4×4 --------------------------------

    def _apply_rotation_quadrant_tile_4x4(self, rule, input_grid):
        raw = input_grid.raw
        n = len(raw)
        w = len(raw[0]) if raw else 0
        if n == 0 or n != w:
            return None

        orig = [row[:] for row in raw]
        rot180 = GeneralizeOperator._rotate_180(orig)
        cw90 = GeneralizeOperator._rotate_cw90(orig)
        ccw90 = GeneralizeOperator._rotate_ccw90(orig)

        layout = [
            [rot180, rot180, cw90, cw90],
            [rot180, rot180, cw90, cw90],
            [ccw90, ccw90, orig, orig],
            [ccw90, ccw90, orig, orig],
        ]

        out = [[0] * (4 * n) for _ in range(4 * n)]
        for br in range(4):
            for bc in range(4):
                blk = layout[br][bc]
                for r in range(n):
                    for c in range(n):
                        out[br * n + r][bc * n + c] = blk[r][c]
        return out

    # ---- apply: self-tiling (fractal zoom) ---------------------------------

    def _apply_self_tiling(self, rule, input_grid):
        raw = input_grid.raw
        n = len(raw)
        w = len(raw[0]) if raw else 0
        if n == 0 or n != w:
            return None
        out_size = n * n
        out = [[0] * out_size for _ in range(out_size)]
        for br in range(n):
            for bc in range(n):
                if raw[br][bc] != 0:
                    for dr in range(n):
                        for dc in range(n):
                            out[br * n + dr][bc * n + dc] = raw[dr][dc]
        return out

    # ---- apply: double mirror / kaleidoscope ----------------------------

    def _apply_double_mirror(self, rule, input_grid):
        raw = input_grid.raw
        H = len(raw)
        W = len(raw[0]) if raw else 0
        top_half = []
        for r in range(H):
            row = list(raw[r]) + list(reversed(raw[r]))
            top_half.append(row)
        return top_half + list(reversed(top_half))

    # ---- apply: XOR comparison ------------------------------------------

    def _apply_xor_comparison(self, rule, input_grid):
        raw = input_grid.raw
        H = len(raw)
        W = len(raw[0]) if raw else 0
        sep_color = rule.get("sep_color")
        out_color = rule.get("out_color", 3)

        # Find separator row
        sep_row = None
        for r in range(H):
            if len(set(raw[r])) == 1 and raw[r][0] == sep_color:
                sep_row = r
                break
        if sep_row is None:
            return [row[:] for row in raw]

        top_h = sep_row
        bot_start = sep_row + 1
        bot_h = H - bot_start

        half_h = min(top_h, bot_h)
        out = [[0] * W for _ in range(half_h)]
        for r in range(half_h):
            for c in range(W):
                t = raw[r][c] != 0
                b = raw[bot_start + r][c] != 0
                if t != b:
                    out[r][c] = out_color
        return out

    # ---- apply: half-grid boolean ----------------------------------------

    def _apply_half_grid_boolean(self, rule, input_grid):
        raw = input_grid.raw
        H = len(raw)
        W = len(raw[0]) if raw else 0
        op = rule.get("operation")
        split_mode = rule.get("split_mode")
        sep_color = rule.get("sep_color")
        out_color = rule.get("out_color")

        half_a = half_b = None
        out_h = out_w = 0

        if split_mode == "h_separator":
            sep_row = None
            for r in range(H):
                if len(set(raw[r])) == 1 and raw[r][0] == sep_color:
                    sep_row = r
                    break
            if sep_row is None:
                return [row[:] for row in raw]
            top_h = sep_row
            bot_start = sep_row + 1
            if bot_start + top_h > H:
                return [row[:] for row in raw]
            half_a = [raw[r] for r in range(top_h)]
            half_b = [raw[r] for r in range(bot_start, bot_start + top_h)]
            out_h, out_w = top_h, W

        elif split_mode == "v_separator":
            sep_col = None
            for c in range(W):
                col_vals = [raw[r][c] for r in range(H)]
                if len(set(col_vals)) == 1 and col_vals[0] == sep_color:
                    sep_col = c
                    break
            if sep_col is None:
                return [row[:] for row in raw]
            left_w = sep_col
            right_start = sep_col + 1
            half_a = [row[:left_w] for row in raw]
            half_b = [row[right_start:right_start + left_w] for row in raw]
            out_h, out_w = H, left_w

        elif split_mode == "v_half":
            hw = W // 2
            half_a = [row[:hw] for row in raw]
            half_b = [row[hw:] for row in raw]
            out_h, out_w = H, hw

        elif split_mode == "h_half":
            hh = H // 2
            half_a = [raw[r] for r in range(hh)]
            half_b = [raw[r] for r in range(hh, H)]
            out_h, out_w = hh, W

        if half_a is None:
            return [row[:] for row in raw]

        out = [[0] * out_w for _ in range(out_h)]
        for r in range(out_h):
            for c in range(out_w):
                a = half_a[r][c] != 0
                b = half_b[r][c] != 0
                if op == "or":
                    res = a or b
                elif op == "and":
                    res = a and b
                elif op == "nor":
                    res = not (a or b)
                else:
                    res = not (a and b)
                if res:
                    out[r][c] = out_color
        return out

    # ---- apply: inverse tile ---------------------------------------------

    def _apply_inverse_tile(self, rule, input_grid):
        raw = input_grid.raw
        H = len(raw)
        W = len(raw[0]) if raw else 0
        fg = 0
        for row in raw:
            for v in row:
                if v != 0:
                    fg = v
                    break
            if fg:
                break
        if fg == 0:
            fg = 1
        inv = [[fg if v == 0 else 0 for v in row] for row in raw]
        out = [[0] * (2 * W) for _ in range(2 * H)]
        for r in range(H):
            for c in range(W):
                val = inv[r][c]
                out[r][c] = val
                out[r][W + c] = val
                out[H + r][c] = val
                out[H + r][W + c] = val
        return out

    # ---- apply: grid separator max fill ----------------------------------

    def _apply_grid_separator_max_fill(self, rule, input_grid):
        raw = input_grid.raw
        H = len(raw)
        W = len(raw[0]) if raw else 0
        sep_color = rule.get("sep_color")

        sep_rows = [r for r in range(H)
                     if len(set(raw[r])) == 1 and raw[r][0] == sep_color]
        sep_cols = [c for c in range(W)
                     if len(set(raw[r][c] for r in range(H))) == 1
                     and raw[0][c] == sep_color]

        def _bounds(seps, total):
            bounds = []
            prev = 0
            for s in sorted(seps):
                if s > prev:
                    bounds.append((prev, s))
                prev = s + 1
            if prev < total:
                bounds.append((prev, total))
            return bounds

        row_bounds = _bounds(sep_rows, H)
        col_bounds = _bounds(sep_cols, W)

        cell_counts = []
        cell_colors = []
        for rb in row_bounds:
            rc, rclr = [], []
            for cb in col_bounds:
                cnt = 0
                cc = None
                for r in range(rb[0], rb[1]):
                    for c in range(cb[0], cb[1]):
                        v = raw[r][c]
                        if v != 0 and v != sep_color:
                            cnt += 1
                            cc = v
                rc.append(cnt)
                rclr.append(cc)
            cell_counts.append(rc)
            cell_colors.append(rclr)

        max_cnt = max(max(row) for row in cell_counts) if cell_counts else 0
        out = [[0] * W for _ in range(H)]

        for r in sep_rows:
            for c in range(W):
                out[r][c] = sep_color
        for c in sep_cols:
            for r in range(H):
                out[r][c] = sep_color

        for ri, rb in enumerate(row_bounds):
            for ci, cb in enumerate(col_bounds):
                if cell_counts[ri][ci] == max_cnt and cell_colors[ri][ci] is not None:
                    for r in range(rb[0], rb[1]):
                        for c in range(cb[0], cb[1]):
                            out[r][c] = cell_colors[ri][ci]
        return out

    # ---- apply: grid lines pattern ---------------------------------------

    def _apply_grid_lines_pattern(self, rule, input_grid):
        """All-zero NxN → 1 at cells where row%2==0 or col%2==0."""
        raw = input_grid.raw
        H = len(raw)
        W = len(raw[0]) if raw else 0
        bg = raw[0][0] if H > 0 and W > 0 else 0
        # Determine fill color: use 1 (standard for this pattern)
        fill = 1
        out = [[bg] * W for _ in range(H)]
        for r in range(H):
            for c in range(W):
                if r % 2 == 0 or c % 2 == 0:
                    out[r][c] = fill
        return out

    # ---- apply: column shadow tile ---------------------------------------

    def _apply_column_shadow_tile(self, rule, input_grid):
        """Replace 0s in columns with non-zero cells with 8, tile 2×2."""
        raw = input_grid.raw
        H = len(raw)
        W = len(raw[0]) if raw else 0

        shadow = [row[:] for row in raw]
        for c in range(W):
            has_nonzero = any(raw[r][c] != 0 for r in range(H))
            if has_nonzero:
                for r in range(H):
                    if shadow[r][c] == 0:
                        shadow[r][c] = 8

        # Tile 2×2
        oH, oW = 2 * H, 2 * W
        out = [[0] * oW for _ in range(oH)]
        for r in range(oH):
            for c in range(oW):
                out[r][c] = shadow[r % H][c % W]
        return out

    # ---- apply: concentric ring rotate -----------------------------------

    def _apply_concentric_ring_rotate(self, rule, input_grid):
        """Rotate concentric ring colors by 1 position outward."""
        raw = input_grid.raw
        H = len(raw)
        W = len(raw[0]) if raw else 0

        # Extract ring colors
        ring_colors = []
        max_rings = min(H, W) // 2 + (1 if min(H, W) % 2 else 0)
        for ring in range(max_rings):
            r0, c0 = ring, ring
            r1, c1 = H - 1 - ring, W - 1 - ring
            if r0 > r1 or c0 > c1:
                break
            ring_colors.append(raw[r0][c0])

        if len(ring_colors) < 2:
            return [row[:] for row in raw]

        # Build unique ordered color list, then rotate right
        unique_ordered = []
        seen = set()
        for c in ring_colors:
            if c not in seen:
                unique_ordered.append(c)
                seen.add(c)

        rotated = [unique_ordered[-1]] + unique_ordered[:-1]
        color_map = {}
        for i, old_c in enumerate(unique_ordered):
            color_map[old_c] = rotated[i]

        out = [[color_map.get(raw[r][c], raw[r][c]) for c in range(W)]
               for r in range(H)]
        return out

    # ---- apply: wedge expansion --------------------------------------------

    def _apply_wedge_expansion(self, rule, input_grid):
        """Expand seed line into triangle above (up_color) and below (down_color)."""
        raw = input_grid.raw
        H = len(raw)
        W = len(raw[0]) if raw else 0
        seed_color = rule["seed_color"]
        up_color = rule["up_color"]
        down_color = rule["down_color"]

        # Find seed row
        seed_row = None
        seed_len = 0
        for r in range(H):
            nz = [c for c in range(W) if raw[r][c] != 0]
            if nz:
                seed_row = r
                seed_len = len(nz)
                break

        if seed_row is None:
            return [row[:] for row in raw]

        out = [[0] * W for _ in range(H)]

        for r in range(H):
            if r == seed_row:
                out[r] = raw[r][:]
            elif r < seed_row:
                d = seed_row - r
                fill_len = min(seed_len + d, W)
                for c in range(fill_len):
                    out[r][c] = up_color
            else:
                d = r - seed_row
                fill_len = seed_len - d
                if fill_len > 0:
                    for c in range(fill_len):
                        out[r][c] = down_color

        return out

    # ---- apply: mirror row tile -------------------------------------------

    def _apply_mirror_row_tile(self, rule, input_grid):
        """Each row → reversed(row) + row, tiled 2×."""
        raw = input_grid.raw
        H = len(raw)
        out = []
        for r in range(H):
            row = raw[r]
            rev = list(reversed(row))
            unit = rev + row
            out.append(unit + unit)
        return out

    # ---- apply: larger interior rect --------------------------------------

    def _apply_larger_interior_rect(self, rule, input_grid):
        """Find two rects, output 2×2 with color of larger interior."""
        raw = input_grid.raw
        H = len(raw)
        W = len(raw[0]) if raw else 0

        # Find rectangles
        visited = [[False] * W for _ in range(H)]
        rects = []
        for r in range(H):
            for c in range(W):
                if raw[r][c] != 0 and not visited[r][c]:
                    color = raw[r][c]
                    cells = set()
                    queue = [(r, c)]
                    visited[r][c] = True
                    while queue:
                        cr, cc = queue.pop(0)
                        cells.add((cr, cc))
                        for dr, dc in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                            nr, nc = cr + dr, cc + dc
                            if 0 <= nr < H and 0 <= nc < W and not visited[nr][nc] and raw[nr][nc] == color:
                                visited[nr][nc] = True
                                queue.append((nr, nc))
                    min_r = min(cr for cr, cc in cells)
                    max_r = max(cr for cr, cc in cells)
                    min_c = min(cc for cr, cc in cells)
                    max_c = max(cc for cr, cc in cells)
                    int_h = max_r - min_r - 1
                    int_w = max_c - min_c - 1
                    area = max(0, int_h) * max(0, int_w)
                    rects.append((area, color))

        if not rects:
            return [[0, 0], [0, 0]]

        rects.sort(reverse=True)
        winner = rects[0][1]
        return [[winner, winner], [winner, winner]]

    # ---- apply: bbox fill ---------------------------------------------------

    def _apply_bbox_fill(self, rule, input_grid):
        """Fill 0-cells within bounding box of fg shape with fill_color."""
        raw = input_grid.raw
        H = len(raw)
        W = len(raw[0]) if raw else 0
        fg_color = rule["fg_color"]
        fill_color = rule["fill_color"]

        min_r, max_r = H, -1
        min_c, max_c = W, -1
        for r in range(H):
            for c in range(W):
                if raw[r][c] == fg_color:
                    if r < min_r: min_r = r
                    if r > max_r: max_r = r
                    if c < min_c: min_c = c
                    if c > max_c: max_c = c

        out = [row[:] for row in raw]
        if max_r >= 0:
            for r in range(min_r, max_r + 1):
                for c in range(min_c, max_c + 1):
                    if out[r][c] == 0:
                        out[r][c] = fill_color
        return out

    # ---- apply: symmetry complete -------------------------------------------

    def _apply_symmetry_complete(self, rule, input_grid):
        """Complete 4-fold rotational symmetry about the bbox center."""
        raw = input_grid.raw
        H = len(raw)
        W = len(raw[0]) if raw else 0

        nz_cells = []
        for r in range(H):
            for c in range(W):
                if raw[r][c] != 0:
                    nz_cells.append((r, c, raw[r][c]))

        if not nz_cells:
            return [row[:] for row in raw]

        rows = [r for r, c, v in nz_cells]
        cols = [c for r, c, v in nz_cells]
        cr = (min(rows) + max(rows)) / 2.0
        cc = (min(cols) + max(cols)) / 2.0

        out = [row[:] for row in raw]
        for r, c, v in nz_cells:
            for nr, nc in [
                (cr + (c - cc), cc - (r - cr)),
                (2 * cr - r, 2 * cc - c),
                (cr - (c - cc), cc + (r - cr)),
            ]:
                nri, nci = int(round(nr)), int(round(nc))
                if 0 <= nri < H and 0 <= nci < W and out[nri][nci] == 0:
                    out[nri][nci] = v
        return out

    # ---- apply: accelerating sequence ---------------------------------------

    def _apply_accelerating_sequence(self, rule, input_grid):
        """Place cycling seed colors at triangular-number positions."""
        raw = input_grid.raw
        H = len(raw)
        W = len(raw[0]) if raw else 0

        nz_row = None
        for r in range(H):
            if any(raw[r][c] != 0 for c in range(W)):
                nz_row = r
                break
        if nz_row is None:
            return [row[:] for row in raw]

        seed_colors = [raw[nz_row][c] for c in range(W) if raw[nz_row][c] != 0]

        out = [[0] * W for _ in range(H)]
        pos = 0
        gap = 1
        ci = 0
        while pos < W:
            out[nz_row][pos] = seed_colors[ci % len(seed_colors)]
            ci += 1
            pos += gap
            gap += 1
        return out

    # ---- apply: pixel collect snake --------------------------------------

    def _apply_pixel_collect_snake(self, rule, input_grid):
        raw = input_grid.raw
        H = len(raw)
        W = len(raw[0]) if raw else 0
        out_rows = rule["out_rows"]
        out_cols = rule["out_cols"]

        # Collect non-zero pixels sorted by column then row
        pixels = []
        for r in range(H):
            for c in range(W):
                if raw[r][c] != 0:
                    pixels.append((c, r, raw[r][c]))
        pixels.sort(key=lambda p: (p[0], p[1]))

        # Place in boustrophedon order
        output = [[0] * out_cols for _ in range(out_rows)]
        idx = 0
        for row in range(out_rows):
            if row % 2 == 0:
                cols = range(out_cols)
            else:
                cols = range(out_cols - 1, -1, -1)
            for col in cols:
                if idx < len(pixels):
                    output[row][col] = pixels[idx][2]
                    idx += 1
        return output

    # ---- apply: frame scale pattern --------------------------------------

    def _apply_frame_scale_pattern(self, rule, input_grid):
        raw = input_grid.raw
        H = len(raw)
        W = len(raw[0]) if raw else 0

        # Find the frame
        frame_color = None
        fr_top = fr_bot = fr_left = fr_right = None
        for r in range(H):
            for c in range(W):
                v = raw[r][c]
                if v != 0:
                    if frame_color is None:
                        frame_color = v
                    if v == frame_color:
                        if fr_top is None or r < fr_top:
                            fr_top = r
                        if fr_bot is None or r > fr_bot:
                            fr_bot = r
                        if fr_left is None or c < fr_left:
                            fr_left = c
                        if fr_right is None or c > fr_right:
                            fr_right = c
        if frame_color is None:
            return [row[:] for row in raw]

        int_top = fr_top + 1
        int_bot = fr_bot - 1
        int_left = fr_left + 1
        int_right = fr_right - 1
        int_h = int_bot - int_top + 1
        int_w = int_right - int_left + 1

        # Find the 2×2 pattern
        pattern_cells = []
        for r in range(int_top, int_bot + 1):
            for c in range(int_left, int_right + 1):
                v = raw[r][c]
                if v != 0 and v != frame_color:
                    pattern_cells.append((r, c, v))

        if not pattern_cells:
            return [row[:] for row in raw]

        pr_min = min(r for r, c, v in pattern_cells)
        pc_min = min(c for r, c, v in pattern_cells)
        pr_max = max(r for r, c, v in pattern_cells)
        pc_max = max(c for r, c, v in pattern_cells)
        pat_h = pr_max - pr_min + 1
        pat_w = pc_max - pc_min + 1
        half_h = max(pat_h // 2, 1)
        half_w = max(pat_w // 2, 1)

        tl = raw[pr_min][pc_min]
        tr = raw[pr_min][pc_min + half_w]
        bl = raw[pr_min + half_h][pc_min]
        br = raw[pr_min + half_h][pc_min + half_w]

        # Build output: frame + scaled pattern
        out_h = fr_bot - fr_top + 1
        out_w = fr_right - fr_left + 1
        q_h = int_h // 2
        q_w = int_w // 2

        output = [[0] * out_w for _ in range(out_h)]
        for r in range(out_h):
            for c in range(out_w):
                if r == 0 or r == out_h - 1 or c == 0 or c == out_w - 1:
                    output[r][c] = frame_color
                else:
                    ir = r - 1
                    ic = c - 1
                    qr = 0 if ir < q_h else 1
                    qc = 0 if ic < q_w else 1
                    output[r][c] = [tl, tr, bl, br][qr * 2 + qc]
        return output

    # ---- apply: box slide trail ------------------------------------------

    def _apply_box_slide_trail(self, rule, input_grid):
        raw = input_grid.raw
        H = len(raw)
        W = len(raw[0]) if raw else 0

        # Find the 3×3 box
        box_r = box_c = None
        center_val = border_val = None
        for r in range(H - 2):
            for c in range(W - 2):
                cv = raw[r + 1][c + 1]
                if cv == 0:
                    continue
                bv = raw[r][c]
                if bv == 0 or bv == cv:
                    continue
                is_box = True
                for dr in range(3):
                    for dc in range(3):
                        if dr == 1 and dc == 1:
                            continue
                        if raw[r + dr][c + dc] != bv:
                            is_box = False
                            break
                    if not is_box:
                        break
                if is_box:
                    box_r, box_c = r, c
                    center_val, border_val = cv, bv
                    break
            if box_r is not None:
                break

        if box_r is None:
            return [row[:] for row in raw]

        center_r = box_r + 1
        center_c = box_c + 1

        # Find trail along center row and center col
        h_trail = []
        for c in range(W):
            if raw[center_r][c] == center_val and not (box_c <= c <= box_c + 2):
                h_trail.append(c)

        v_trail = []
        for r in range(H):
            if raw[r][center_c] == center_val and not (box_r <= r <= box_r + 2):
                v_trail.append(r)

        # Determine direction
        if h_trail:
            left_count = sum(1 for c in h_trail if c < box_c)
            right_count = sum(1 for c in h_trail if c > box_c + 2)
            if right_count > left_count:
                dr, dc = 0, 2
            elif left_count > right_count:
                dr, dc = 0, -2
            else:
                dr, dc = 0, 2
        elif v_trail:
            above_count = sum(1 for r in v_trail if r < box_r)
            below_count = sum(1 for r in v_trail if r > box_r + 2)
            if below_count > above_count:
                dr, dc = 2, 0
            elif above_count > below_count:
                dr, dc = -2, 0
            else:
                dr, dc = 2, 0
        else:
            return [row[:] for row in raw]

        # Build output
        new_box_r = box_r + dr
        new_box_c = box_c + dc
        if new_box_r < 0 or new_box_r + 2 >= H or new_box_c < 0 or new_box_c + 2 >= W:
            return [row[:] for row in raw]

        output = [row[:] for row in raw]

        # Erase old box
        for drr in range(3):
            for dcc in range(3):
                output[box_r + drr][box_c + dcc] = 0

        # Old center becomes trail dot
        output[center_r][center_c] = center_val

        # Place new box
        for drr in range(3):
            for dcc in range(3):
                if drr == 1 and dcc == 1:
                    output[new_box_r + drr][new_box_c + dcc] = center_val
                else:
                    output[new_box_r + drr][new_box_c + dcc] = border_val

        return output

    # ---- apply: cross pair lines ------------------------------------------

    def _apply_cross_pair_lines(self, rule, input_grid):
        raw = input_grid.raw
        H, W = len(raw), len(raw[0])

        # Collect pixel pairs by color
        color_pos = {}
        for r in range(H):
            for c in range(W):
                v = raw[r][c]
                if v != 0:
                    color_pos.setdefault(v, []).append((r, c))

        output = [[0] * W for _ in range(H)]

        h_lines = []
        v_lines = []
        for color, positions in color_pos.items():
            if len(positions) != 2:
                continue
            (r1, c1), (r2, c2) = positions
            if r1 == r2:
                h_lines.append((r1, min(c1, c2), max(c1, c2), color))
            elif c1 == c2:
                v_lines.append((c1, min(r1, r2), max(r1, r2), color))

        # Draw horizontal lines first
        for row, c_min, c_max, color in h_lines:
            for c in range(c_min, c_max + 1):
                output[row][c] = color

        # Vertical lines overwrite at crossings
        for col, r_min, r_max, color in v_lines:
            for r in range(r_min, r_max + 1):
                output[r][col] = color

        return output

    # ---- apply: multi-layer overlay ---------------------------------------

    def _apply_multi_layer_overlay(self, rule, input_grid):
        raw = input_grid.raw
        H_in = len(raw)
        W = len(raw[0])
        N = rule["num_layers"]
        H_out = rule["layer_height"]
        layer_colors = rule["layer_colors"]
        priority = rule["priority"]

        if H_in != N * H_out:
            return [row[:] for row in raw]

        output = [[0] * W for _ in range(H_out)]
        for r in range(H_out):
            for c in range(W):
                for color in priority:
                    li = layer_colors.index(color)
                    if raw[li * H_out + r][c] != 0:
                        output[r][c] = color
                        break
        return output

    # ---- apply: tile grid recolor -----------------------------------------

    def _apply_tile_grid_recolor(self, rule, input_grid):
        raw = input_grid.raw
        H, W = len(raw), len(raw[0])

        # Find 5-cells
        five_cells = set()
        for r in range(H):
            for c in range(W):
                if raw[r][c] == 5:
                    five_cells.add((r, c))

        if not five_cells:
            return [row[:] for row in raw]

        # Find key cells (non-0, non-5)
        key_cells = {}
        for r in range(H):
            for c in range(W):
                v = raw[r][c]
                if v != 0 and v != 5:
                    key_cells[(r, c)] = v

        if not key_cells:
            return [row[:] for row in raw]

        kr_min = min(r for r, c in key_cells)
        kc_min = min(c for r, c in key_cells)

        # Find tile structure
        tile_rows = sorted(set(r for r, c in five_cells))
        tile_cols = sorted(set(c for r, c in five_cells))

        row_bands = []
        cur = [tile_rows[0]]
        for i in range(1, len(tile_rows)):
            if tile_rows[i] == cur[-1] + 1:
                cur.append(tile_rows[i])
            else:
                row_bands.append(cur)
                cur = [tile_rows[i]]
        row_bands.append(cur)

        col_sections = []
        cur = [tile_cols[0]]
        for i in range(1, len(tile_cols)):
            if tile_cols[i] == cur[-1] + 1:
                cur.append(tile_cols[i])
            else:
                col_sections.append(cur)
                cur = [tile_cols[i]]
        col_sections.append(cur)

        output = [row[:] for row in raw]
        for tr in range(len(row_bands)):
            for tc in range(len(col_sections)):
                kr = kr_min + tr
                kc = kc_min + tc
                key_color = key_cells.get((kr, kc), 0)
                for r in row_bands[tr]:
                    for c in col_sections[tc]:
                        if raw[r][c] == 5:
                            output[r][c] = key_color
        return output

    # ---- strategy 58 apply: rect minority gridlines -------------------------

    def _apply_rect_minority_gridlines(self, rule, input_grid):
        raw = input_grid.raw
        H, W = len(raw), len(raw[0])

        # Find the uniform rect by density analysis per color
        best = None
        best_area = 0
        for dom_color in range(10):
            # Compute per-row density of dom_color
            row_counts = [0] * H
            for r in range(H):
                for c in range(W):
                    if raw[r][c] == dom_color:
                        row_counts[r] += 1

            # Find contiguous row range with high density (> 40% of width)
            thresh = max(3, W * 0.4)
            high_rows = [r for r in range(H) if row_counts[r] >= thresh]
            if len(high_rows) < 3:
                continue

            # Find contiguous groups of high-density rows
            groups = []
            start = high_rows[0]
            for i in range(1, len(high_rows)):
                if high_rows[i] != high_rows[i - 1] + 1:
                    groups.append((start, high_rows[i - 1]))
                    start = high_rows[i]
            groups.append((start, high_rows[-1]))

            for rmin, rmax in groups:
                if rmax - rmin + 1 < 3:
                    continue
                # Find column range within these rows
                col_counts = [0] * W
                row_span = rmax - rmin + 1
                for r in range(rmin, rmax + 1):
                    for c in range(W):
                        if raw[r][c] == dom_color:
                            col_counts[c] += 1
                col_thresh = max(2, row_span * 0.4)
                high_cols = [c for c in range(W)
                             if col_counts[c] >= col_thresh]
                if len(high_cols) < 3:
                    continue
                cmin, cmax = high_cols[0], high_cols[-1]
                rect_h = rmax - rmin + 1
                rect_w = cmax - cmin + 1
                total = rect_h * rect_w

                # Check purity and single minority
                dom_count = 0
                minority_color = None
                minority_positions = []
                valid = True
                for r in range(rmin, rmax + 1):
                    for c in range(cmin, cmax + 1):
                        v = raw[r][c]
                        if v == dom_color:
                            dom_count += 1
                        else:
                            if minority_color is None:
                                minority_color = v
                            elif v != minority_color:
                                valid = False
                                break
                            minority_positions.append(
                                (r - rmin, c - cmin))
                    if not valid:
                        break

                if not valid or minority_color is None:
                    continue
                if dom_count < total * 0.7:
                    continue
                if total > best_area:
                    best_area = total
                    best = (rect_h, rect_w, dom_color, minority_color,
                            minority_positions)

        if best:
            rect_h, rect_w, dom_color, minority_color, mpos = best
            min_rows = set(r for r, c in mpos)
            min_cols = set(c for r, c in mpos)
            output = [[dom_color] * rect_w for _ in range(rect_h)]
            for mr in min_rows:
                for c in range(rect_w):
                    output[mr][c] = minority_color
            for mc in min_cols:
                for r in range(rect_h):
                    output[r][mc] = minority_color
            return output

        return [row[:] for row in raw]

    # ---- strategy 59 apply: rect directional tile ----------------------------

    def _apply_rect_directional_tile(self, rule, input_grid):
        raw = input_grid.raw
        H, W = len(raw), len(raw[0])

        # Find hollow 4×4 rects
        rects = []
        used = set()
        for r in range(H - 3):
            for c in range(W - 3):
                v = raw[r][c]
                if v == 0 or v == 1:
                    continue
                frame_ok = True
                for dr in range(4):
                    for dc in range(4):
                        cell = raw[r + dr][c + dc]
                        if dr in (0, 3) or dc in (0, 3):
                            if cell != v:
                                frame_ok = False
                                break
                        else:
                            if cell != 0:
                                frame_ok = False
                                break
                    if not frame_ok:
                        break
                if frame_ok and (r, c) not in used:
                    rects.append((r, c, v))
                    for dr in range(4):
                        for dc in range(4):
                            used.add((r + dr, c + dc))

        # Find 1-lines
        one_cells = set()
        for r in range(H):
            for c in range(W):
                if raw[r][c] == 1:
                    one_cells.add((r, c))

        output = [[raw[r][c] for c in range(W)] for r in range(H)]
        # Remove 1-lines
        for r, c in one_cells:
            output[r][c] = 0

        for rect_r, rect_c, rect_color in rects:
            rect_pattern = [[raw[rect_r + dr][rect_c + dc] for dc in range(4)] for dr in range(4)]

            # Right
            h_one_r = None
            for c_check in range(rect_c + 4, W):
                if all((rect_r + dr, c_check) in one_cells for dr in range(4)):
                    h_one_r = c_check
                    break
            if h_one_r is not None:
                for c_pos in range(rect_c + 4, h_one_r + 1):
                    dc = (c_pos - rect_c) % 4
                    for dr in range(4):
                        output[rect_r + dr][c_pos] = rect_pattern[dr][dc]

            # Left
            h_one_l = None
            for c_check in range(rect_c - 1, -1, -1):
                if all((rect_r + dr, c_check) in one_cells for dr in range(4)):
                    h_one_l = c_check
                    break
            if h_one_l is not None:
                for c_pos in range(rect_c - 1, h_one_l - 1, -1):
                    dc = (c_pos - rect_c) % 4
                    for dr in range(4):
                        output[rect_r + dr][c_pos] = rect_pattern[dr][dc]

            # Below
            v_one_b = None
            for r_check in range(rect_r + 4, H):
                if all((r_check, rect_c + dc) in one_cells for dc in range(4)):
                    v_one_b = r_check
                    break
            if v_one_b is not None:
                for r_pos in range(rect_r + 4, v_one_b + 1):
                    dr = (r_pos - rect_r) % 4
                    for dc in range(4):
                        output[r_pos][rect_c + dc] = rect_pattern[dr][dc]

            # Above
            v_one_t = None
            for r_check in range(rect_r - 1, -1, -1):
                if all((r_check, rect_c + dc) in one_cells for dc in range(4)):
                    v_one_t = r_check
                    break
            if v_one_t is not None:
                for r_pos in range(rect_r - 1, v_one_t - 1, -1):
                    dr = (r_pos - rect_r) % 4
                    for dc in range(4):
                        output[r_pos][rect_c + dc] = rect_pattern[dr][dc]

        return output

    # ---- strategy 60 apply: corner block shift -------------------------------

    def _apply_corner_block_shift(self, rule, input_grid):
        raw = input_grid.raw
        H, W = len(raw), len(raw[0])

        from collections import Counter
        flat = [raw[r][c] for r in range(H) for c in range(W)]
        bg = Counter(flat).most_common(1)[0][0]

        # Find blocks
        visited = set()
        blocks = []
        for r in range(H):
            for c in range(W):
                if raw[r][c] != bg and (r, c) not in visited:
                    color = raw[r][c]
                    comp = []
                    queue = [(r, c)]
                    while queue:
                        cr, cc = queue.pop(0)
                        if (cr, cc) in visited:
                            continue
                        if cr < 0 or cr >= H or cc < 0 or cc >= W:
                            continue
                        if raw[cr][cc] != color:
                            continue
                        visited.add((cr, cc))
                        comp.append((cr, cc))
                        for dr2, dc2 in [(-1,0),(1,0),(0,-1),(0,1)]:
                            queue.append((cr+dr2, cc+dc2))
                    rmin = min(r2 for r2, c2 in comp)
                    rmax = max(r2 for r2, c2 in comp)
                    cmin = min(c2 for r2, c2 in comp)
                    cmax = max(c2 for r2, c2 in comp)
                    bh = rmax - rmin + 1
                    bw = cmax - cmin + 1
                    if len(comp) == bh * bw:
                        blocks.append({
                            "color": color,
                            "rmin": rmin, "rmax": rmax,
                            "cmin": cmin, "cmax": cmax,
                            "h": bh, "w": bw
                        })

        color_counts = Counter(b["color"] for b in blocks)
        if len(color_counts) < 2:
            majority_color = blocks[0]["color"] if blocks else bg
        else:
            majority_color = color_counts.most_common(1)[0][0]

        output = [[bg] * W for _ in range(H)]
        center_r = (H - 1) / 2.0
        center_c = (W - 1) / 2.0

        for b in blocks:
            if b["color"] != majority_color:
                for r in range(b["rmin"], b["rmax"] + 1):
                    for c in range(b["cmin"], b["cmax"] + 1):
                        output[r][c] = b["color"]
            else:
                block_center_r = (b["rmin"] + b["rmax"]) / 2.0
                block_center_c = (b["cmin"] + b["cmax"]) / 2.0

                dr = 0
                if block_center_r < center_r:
                    dr = b["h"]
                elif block_center_r > center_r:
                    dr = -b["h"]

                dc = 0
                if block_center_c < center_c:
                    dc = b["w"]
                elif block_center_c > center_c:
                    dc = -b["w"]

                nr = b["rmin"] + dr
                nc = b["cmin"] + dc
                for r in range(nr, nr + b["h"]):
                    for c in range(nc, nc + b["w"]):
                        if 0 <= r < H and 0 <= c < W:
                            output[r][c] = b["color"]

        return output

    # ---- strategy 61 apply: grid section key lookup --------------------------

    def _apply_grid_section_key_lookup(self, rule, input_grid):
        raw = input_grid.raw
        H, W = len(raw), len(raw[0])
        # Find separator rows and cols
        sep_rows = [r for r in range(H) if all(raw[r][c] == 5 for c in range(W))]
        sep_cols = [c for c in range(W) if all(raw[r][c] == 5 for r in range(H))]
        if len(sep_rows) != 2 or len(sep_cols) != 2:
            return [row[:] for row in raw]
        # Build section bands
        row_bands = []
        prev = 0
        for sr in sep_rows:
            row_bands.append((prev, sr))
            prev = sr + 1
        row_bands.append((prev, H))
        col_bands = []
        prev = 0
        for sc in sep_cols:
            col_bands.append((prev, sc))
            prev = sc + 1
        col_bands.append((prev, W))
        # Find key section
        key_section = None
        for mr in range(3):
            for mc in range(3):
                r0, r1 = row_bands[mr]
                c0, c1 = col_bands[mc]
                cells = {}
                for r in range(r0, r1):
                    for c in range(c0, c1):
                        v = raw[r][c]
                        if v != 0:
                            cells[(r - r0, c - c0)] = v
                unique_vals = set(cells.values())
                if len(cells) == 4 and len(unique_vals) == 4 and 8 not in unique_vals:
                    key_section = cells
                    break
            if key_section is not None:
                break
        if key_section is None:
            return [row[:] for row in raw]
        # Build output
        output = [[0] * W for _ in range(H)]
        for sr in sep_rows:
            for c in range(W):
                output[sr][c] = 5
        for sc in sep_cols:
            for r in range(H):
                output[r][sc] = 5
        for (lr, lc), v in key_section.items():
            r0, r1 = row_bands[lr]
            c0, c1 = col_bands[lc]
            for r in range(r0, r1):
                for c in range(c0, c1):
                    output[r][c] = v
        return output

    # ---- strategy 62 apply: shape template catalog ---------------------------

    def _apply_shape_template_catalog(self, rule, input_grid):
        raw = input_grid.raw
        H, W = len(raw), len(raw[0])
        # Find sep_col: first column with 5 in row 0
        sep_col = None
        for c in range(W):
            if raw[0][c] == 5:
                sep_col = c
                break
        # Find sep_row: first row where cols 0..sep_col are all 5
        sep_row = None
        if sep_col is not None:
            for r in range(1, H):
                if all(raw[r][c] == 5 for c in range(sep_col + 1)):
                    sep_row = r
                    break
        if sep_row is None or sep_col is None:
            return [row[:] for row in raw]
        # Extract templates
        key_colors = set()
        for r in range(sep_row):
            for c in range(sep_col):
                v = raw[r][c]
                if v != 0 and v != 5:
                    key_colors.add(v)
        templates = {}
        comps = GeneralizeOperator._find_connected_components(
            raw, H, W, key_colors, region=(0, sep_row, 0, sep_col))
        for color, cells in comps:
            shape = GeneralizeOperator._normalize_shape(cells)
            orients = GeneralizeOperator._shape_orientations(shape)
            templates[color] = orients
        # Find and replace color-3 components
        output = [row[:] for row in raw]
        comps_3 = GeneralizeOperator._find_connected_components(raw, H, W, {3})
        for _, cells in comps_3:
            shape = GeneralizeOperator._normalize_shape(cells)
            for color, orients in templates.items():
                if shape in orients:
                    for r, c in cells:
                        output[r][c] = color
                    break
        return output

    # ---- strategy 63 apply: bar chart balance --------------------------------

    def _apply_bar_chart_balance(self, rule, input_grid):
        raw = input_grid.raw
        H, W = len(raw), len(raw[0])
        bg = rule.get("bg_color", 7)
        pos_color = rule.get("bar_color_pos", 8)
        neg_color = rule.get("bar_color_neg", 2)
        fill_color = rule.get("fill_color", 5)
        sum_pos = 0
        sum_neg = 0
        max_bar_col = -1
        for c in range(1, W, 2):
            h = 0
            bar_color = None
            for r in range(H - 1, -1, -1):
                if raw[r][c] != bg:
                    if bar_color is None:
                        bar_color = raw[r][c]
                    if raw[r][c] == bar_color:
                        h += 1
                    else:
                        break
                else:
                    break
            if h > 0 and bar_color in (pos_color, neg_color):
                if bar_color == pos_color:
                    sum_pos += h
                else:
                    sum_neg += h
                max_bar_col = max(max_bar_col, c)
        balance_height = sum_pos - sum_neg
        target_col = max_bar_col + 2
        output = [row[:] for row in raw]
        if balance_height > 0 and 0 <= target_col < W:
            for r in range(H - balance_height, H):
                if 0 <= r < H:
                    output[r][target_col] = fill_color
        return output

    # ---- strategy 64: apply largest blob color ----------------------------

    def _apply_largest_blob_color(self, rule, input_grid):
        raw = input_grid.raw
        best_color = GeneralizeOperator._find_largest_cc_color(raw)
        out_rows = rule.get("out_rows", 3)
        out_cols = rule.get("out_cols", 3)
        return [[best_color] * out_cols for _ in range(out_rows)]

    # ---- strategy 65: apply shape stamp fill ------------------------------

    def _apply_shape_stamp_fill(self, rule, input_grid):
        return GeneralizeOperator._stamp_fill_grid(input_grid.raw)

    # ---- strategy 66: apply spiral from seed ------------------------------

    def _apply_spiral_from_seed(self, rule, input_grid):
        raw = input_grid.raw
        H, W = len(raw), len(raw[0])
        seeds = [(r, c) for r in range(H) for c in range(W) if raw[r][c] == 3]
        if len(seeds) != 1:
            return [row[:] for row in raw]
        return GeneralizeOperator._generate_spiral(raw, seeds[0], H, W)

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

    # ---- apply: panel hole classify --------------------------------------

    def _apply_panel_hole_classify(self, rule, input_grid):
        """Apply panel hole classification rule."""
        raw = input_grid.raw
        if len(raw) != 4:
            return None
        W = len(raw[0]) if raw else 0
        if W != 14:
            return None

        pos_color_map = rule.get("pos_color_map", {})
        panel_starts = [0, 5, 10]
        output = []

        for pc in panel_starts:
            panel = []
            for r in range(4):
                row = []
                for c in range(pc, pc + 4):
                    row.append(raw[r][c])
                panel.append(row)
            hole_key = GeneralizeOperator._panel_hole_key(panel)
            color = pos_color_map.get(hole_key)
            if color is None:
                return None
            output.append([color, color, color])

        return output

    # ---- apply: grid panel decode ----------------------------------------

    def _apply_grid_panel_decode(self, rule, input_grid):
        """Apply grid panel decode rule."""
        return GeneralizeOperator._decode_grid_panels(input_grid.raw)

    # ---- apply: shape gravity sort ---------------------------------------

    def _apply_shape_gravity_sort(self, rule, input_grid):
        """Apply shape gravity sort rule."""
        return GeneralizeOperator._apply_shape_gravity_sort_grid(
            GeneralizeOperator, input_grid.raw
        )

    # ---- strategy 70: apply separator sequence reflect ----------------------

    def _apply_separator_sequence_reflect(self, rule, input_grid):
        """Apply separator sequence reflect rule."""
        detect_result = GeneralizeOperator._detect_sep_reflect(input_grid.raw)
        if detect_result is None:
            return [row[:] for row in input_grid.raw]
        return GeneralizeOperator._apply_sep_reflect(input_grid.raw, detect_result)

    # ---- apply: stamp tile toward bar ------------------------------------

    def _apply_stamp_tile_toward_bar(self, rule, input_grid):
        """Apply stamp-tile-toward-bar rule."""
        return GeneralizeOperator._apply_stamp_tile_grid(input_grid.raw)

    # ---- apply: shape jigsaw assemble ------------------------------------

    def _apply_shape_jigsaw_assemble(self, rule, input_grid):
        """Apply shape jigsaw assembly rule."""
        return GeneralizeOperator._solve_jigsaw(input_grid.raw)

    # ---- apply: stamp shape match ------------------------------------------

    def _apply_stamp_shape_match(self, rule, input_grid):
        """Apply stamp-shape-match rule: find marker shape, stamp on all bg_color matches."""
        raw = input_grid.raw
        h = len(raw)
        w = len(raw[0])
        marker_color = rule["marker_color"]
        bg_color = rule["bg_color"]
        shape_offsets = [tuple(o) for o in rule["shape_offsets"]]

        out = [row[:] for row in raw]
        # Scan for all placements on bg_color cells
        for r in range(h):
            for c in range(w):
                fits = True
                for dr, dc in shape_offsets:
                    nr, nc = r + dr, c + dc
                    if nr < 0 or nr >= h or nc < 0 or nc >= w:
                        fits = False
                        break
                    if raw[nr][nc] != bg_color:
                        fits = False
                        break
                if fits:
                    for dr, dc in shape_offsets:
                        out[r + dr][c + dc] = marker_color
        return out

    # ---- apply: frame hole recolor -----------------------------------------

    def _apply_frame_hole_recolor(self, rule, input_grid):
        """Apply frame-hole-recolor rule: classify 5-shapes by frame holes."""
        raw = input_grid.raw
        h = len(raw)
        w = len(raw[0])

        # Find frame rows
        frame_rows = set()
        for r in range(h):
            for c in range(w):
                if raw[r][c] == 1:
                    frame_rows.add(r)
        if not frame_rows:
            return [row[:] for row in raw]

        frame_bottom = max(frame_rows)
        frame_top = min(frame_rows)

        # Find hole cells
        hole_cells = set()
        for r in range(frame_top, frame_bottom + 1):
            for c in range(w):
                if raw[r][c] == 0:
                    has_left = any(raw[r][lc] == 1 for lc in range(c))
                    has_right = any(raw[r][rc] == 1 for rc in range(c + 1, w))
                    has_above = any(raw[ar][c] == 1 for ar in range(frame_top, r))
                    if has_left and has_right and has_above:
                        hole_cells.add((r, c))

        if not hole_cells:
            return [row[:] for row in raw]

        hole_ccs = GeneralizeOperator._get_connected_components(hole_cells)
        rectangles = []
        for hcc in hole_ccs:
            cols = set(c for _, c in hcc)
            min_r = min(r for r, _ in hcc)
            min_c = min(c for _, c in hcc)
            shape = frozenset((r - min_r, c - min_c) for r, c in hcc)
            hole_col_range = (min(cols), max(cols))
            wall_col_range = (min(cols) - 1, max(cols) + 1)
            hole_width = max(cols) - min(cols) + 1
            rectangles.append({
                "hole_col_range": hole_col_range,
                "wall_col_range": wall_col_range,
                "hole_width": hole_width,
                "shape": shape,
            })

        # Find 5-groups
        five_cells = set()
        for r in range(frame_bottom + 1, h):
            for c in range(w):
                if raw[r][c] == 5:
                    five_cells.add((r, c))

        if not five_cells:
            return [row[:] for row in raw]

        five_groups = GeneralizeOperator._get_connected_components(five_cells)

        out = [row[:] for row in raw]
        for group in five_groups:
            group_cols = set(c for _, c in group)
            group_width = max(group_cols) - min(group_cols) + 1
            min_r = min(r for r, _ in group)
            min_c = min(c for _, c in group)
            group_shape = frozenset((r - min_r, c - min_c) for r, c in group)

            enclosing_rect = None
            for rect in rectangles:
                wmin, wmax = rect["wall_col_range"]
                if all(wmin <= c <= wmax for c in group_cols):
                    enclosing_rect = rect
                    break

            should_recolor = False
            if enclosing_rect is not None:
                if group_width == enclosing_rect["hole_width"]:
                    if GeneralizeOperator._shape_contains_subshape(
                        group_shape, enclosing_rect["shape"]
                    ):
                        should_recolor = True
            else:
                for rect in rectangles:
                    if GeneralizeOperator._shape_contains_subshape(
                        group_shape, rect["shape"]
                    ):
                        should_recolor = True
                        break

            if should_recolor:
                for r, c in group:
                    out[r][c] = 2

        return out

    # ------------------------------------------------------------------
    # _apply_l_corner_complete
    # ------------------------------------------------------------------
    def _apply_l_corner_complete(self, rule, input_grid):
        raw = input_grid.raw
        h, w = len(raw), len(raw[0])
        fg_color = rule["fg_color"]
        mark_color = rule["mark_color"]
        out = [row[:] for row in raw]

        visited = [[False]*w for _ in range(h)]
        for sr in range(h):
            for sc in range(w):
                if raw[sr][sc] == fg_color and not visited[sr][sc]:
                    comp = []
                    stack = [(sr, sc)]
                    visited[sr][sc] = True
                    while stack:
                        cr, cc = stack.pop()
                        comp.append((cr, cc))
                        for dr, dc in [(-1,0),(1,0),(0,-1),(0,1)]:
                            nr, nc = cr+dr, cc+dc
                            if 0 <= nr < h and 0 <= nc < w and not visited[nr][nc] and raw[nr][nc] == fg_color:
                                visited[nr][nc] = True
                                stack.append((nr, nc))
                    if len(comp) == 3:
                        min_r = min(r for r,c in comp)
                        max_r = max(r for r,c in comp)
                        min_c = min(c for r,c in comp)
                        max_c = max(c for r,c in comp)
                        if max_r - min_r == 1 and max_c - min_c == 1:
                            comp_set = set(comp)
                            for cr in [min_r, max_r]:
                                for cc in [min_c, max_c]:
                                    if (cr, cc) not in comp_set:
                                        if 0 <= cr < h and 0 <= cc < w:
                                            out[cr][cc] = mark_color
        return out

    # ------------------------------------------------------------------
    # _apply_quadrant_locator
    # ------------------------------------------------------------------
    def _apply_quadrant_locator(self, rule, input_grid):
        raw = input_grid.raw
        h, w = len(raw), len(raw[0])
        bg_color = rule["bg_color"]
        target_color = rule["target_color"]
        half_r = rule["half_r"]
        half_c = rule["half_c"]

        # Find target_color position
        target_pos = None
        for r in range(h):
            for c in range(w):
                if raw[r][c] == target_color:
                    target_pos = (r, c)
                    break
            if target_pos:
                break
        if target_pos is None:
            return [row[:] for row in raw]

        tr, tc = target_pos
        qr = 0 if tr < half_r else half_r
        qc = 0 if tc < half_c else half_c

        out = [[bg_color]*w for _ in range(h)]
        for r in range(qr, min(qr + half_r, h)):
            for c in range(qc, min(qc + half_c, w)):
                out[r][c] = target_color
        return out

    # ------------------------------------------------------------------
    # _apply_periodic_pattern_extend
    # ------------------------------------------------------------------
    def _apply_periodic_pattern_extend(self, rule, input_grid):
        raw = input_grid.raw
        h, w = len(raw), len(raw[0])

        # Detect border color from edges
        right_col = set(raw[r][w-1] for r in range(h))
        bottom_row = set(raw[h-1][c] for c in range(w))
        border_color = None
        if len(right_col) == 1 and len(bottom_row) == 1 and right_col == bottom_row:
            border_color = right_col.pop()
        elif len(right_col) == 1:
            border_color = right_col.pop()
        elif len(bottom_row) == 1:
            border_color = bottom_row.pop()
        if border_color is None:
            return [row[:] for row in raw]

        # Strip border to find core
        core_w = w
        for c in range(w - 1, -1, -1):
            if all(raw[r][c] == border_color for r in range(h)):
                core_w = c
            else:
                break
        core_h = h
        for r in range(h - 1, -1, -1):
            if all(raw[r][c] == border_color for c in range(w)):
                core_h = r
            else:
                break
        if core_h < 1 or core_w < 1:
            return [row[:] for row in raw]

        core = [row[:core_w] for row in raw[:core_h]]

        # Detect column period
        row0 = core[0]
        col_period = 1
        for p in range(1, core_w + 1):
            if all(row0[c] == row0[c % p] for c in range(core_w)):
                col_period = p
                break

        # Detect row period
        row_period = 1
        for rp in range(1, core_h + 1):
            ok = True
            for r in range(core_h):
                for c in range(core_w):
                    if core[r][c] != core[r % rp][c]:
                        ok = False
                        break
                if not ok:
                    break
            if ok:
                row_period = rp
                break

        tile = [core[r][:col_period] for r in range(row_period)]
        tile_h, tile_w = len(tile), len(tile[0])

        # Fill output with shifted tile
        out = [[0]*w for _ in range(h)]
        for r in range(h):
            for c in range(w):
                out[r][c] = tile[r % tile_h][(c + 1) % tile_w]
        return out

    # ------------------------------------------------------------------
    # _apply_cluster_bbox_border
    # ------------------------------------------------------------------
    def _apply_cluster_bbox_border(self, rule, input_grid):
        raw = input_grid.raw
        H, W = len(raw), len(raw[0])
        marker_color = rule["marker_color"]
        border_color = rule["border_color"]

        positions = set()
        for r in range(H):
            for c in range(W):
                if raw[r][c] == marker_color:
                    positions.add((r, c))

        clusters = GeneralizeOperator(None)._flood_components(positions)

        out = [row[:] for row in raw]
        for cluster in clusters:
            if len(cluster) < 2:
                continue
            min_r = min(r for r, c in cluster)
            max_r = max(r for r, c in cluster)
            min_c = min(c for r, c in cluster)
            max_c = max(c for r, c in cluster)
            br0 = max(0, min_r - 1)
            br1 = min(H - 1, max_r + 1)
            bc0 = max(0, min_c - 1)
            bc1 = min(W - 1, max_c + 1)
            for r in range(br0, br1 + 1):
                for c in range(bc0, bc1 + 1):
                    if out[r][c] == 0:
                        if r == br0 or r == br1 or c == bc0 or c == bc1:
                            out[r][c] = border_color
        return out

    # ------------------------------------------------------------------
    # _apply_crop_rect_flip
    # ------------------------------------------------------------------
    def _apply_crop_rect_flip(self, rule, input_grid):
        raw = input_grid.raw
        H, W = len(raw), len(raw[0])

        non_zero = [(r, c) for r in range(H) for c in range(W) if raw[r][c] != 0]
        if not non_zero:
            return [row[:] for row in raw]
        min_r = min(r for r, c in non_zero)
        max_r = max(r for r, c in non_zero)
        min_c = min(c for r, c in non_zero)
        max_c = max(c for r, c in non_zero)

        cropped = [raw[r][min_c:max_c + 1] for r in range(min_r, max_r + 1)]
        return [row[::-1] for row in cropped]

    # ------------------------------------------------------------------
    # _apply_frame_extract
    # ------------------------------------------------------------------
    def _apply_frame_extract(self, rule, input_grid):
        raw = input_grid.raw
        H, W = len(raw), len(raw[0])
        edge_color = rule["edge_color"]

        ec_cells = [(r, c) for r in range(H) for c in range(W)
                    if raw[r][c] == edge_color]
        if not ec_cells:
            return [row[:] for row in raw]

        ec_cols = set(c for r, c in ec_cells)
        if len(ec_cols) != 2:
            return [row[:] for row in raw]

        left_c, right_c = min(ec_cols), max(ec_cols)
        ec_min_r = min(r for r, c in ec_cells)
        ec_max_r = max(r for r, c in ec_cells)

        frame_min_r = ec_min_r - 1
        frame_max_r = ec_max_r + 1
        frame_min_c = left_c
        frame_max_c = right_c

        if frame_min_r < 0:
            frame_min_r = 0
        if frame_max_r >= H:
            frame_max_r = H - 1

        return [raw[r][frame_min_c:frame_max_c + 1]
                for r in range(frame_min_r, frame_max_r + 1)]

    def _apply_marker_shape_extract(self, rule, input_grid):
        raw = input_grid.raw
        H, W = len(raw), len(raw[0])
        marker_color = rule["marker_color"]

        # Find marker
        marker_cells = [(r, c) for r in range(H) for c in range(W)
                        if raw[r][c] == marker_color]
        if not marker_cells:
            return [row[:] for row in raw]
        mr, mc = marker_cells[0]

        # BFS to find connected shape
        non_bg = set()
        for r in range(H):
            for c in range(W):
                if raw[r][c] != 0:
                    non_bg.add((r, c))

        visited = set()
        queue = [(mr, mc)]
        shape_cells = []
        while queue:
            p = queue.pop(0)
            if p in visited or p not in non_bg:
                continue
            visited.add(p)
            shape_cells.append(p)
            for dr, dc in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                nb = (p[0] + dr, p[1] + dc)
                if nb not in visited and nb in non_bg:
                    queue.append(nb)

        if not shape_cells:
            return [row[:] for row in raw]

        # Determine shape color
        color_counts = {}
        for r, c in shape_cells:
            v = raw[r][c]
            if v != marker_color:
                color_counts[v] = color_counts.get(v, 0) + 1
        shape_color = max(color_counts, key=color_counts.get) if color_counts else 0

        # Extract bounding box, replace marker with shape color
        min_r = min(r for r, c in shape_cells)
        max_r = max(r for r, c in shape_cells)
        min_c = min(c for r, c in shape_cells)
        max_c = max(c for r, c in shape_cells)

        output = []
        for r in range(min_r, max_r + 1):
            row = []
            for c in range(min_c, max_c + 1):
                v = raw[r][c]
                if v == marker_color:
                    v = shape_color
                row.append(v)
            output.append(row)
        return output

    def _apply_template_placeholder_stamp(self, rule, input_grid):
        raw = input_grid.raw
        H, W = len(raw), len(raw[0])
        placeholder_color = rule["placeholder_color"]

        # Find connected components of non-zero cells
        non_bg = set()
        for r in range(H):
            for c in range(W):
                if raw[r][c] != 0:
                    non_bg.add((r, c))

        visited = set()
        components = []
        for pos in sorted(non_bg):
            if pos in visited:
                continue
            queue = [pos]
            comp = []
            while queue:
                p = queue.pop(0)
                if p in visited or p not in non_bg:
                    continue
                visited.add(p)
                comp.append(p)
                for dr, dc in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                    nb = (p[0] + dr, p[1] + dc)
                    if nb not in visited and nb in non_bg:
                        queue.append(nb)
            components.append(comp)

        # Classify components
        template_comp = None
        placeholder_comps = []
        for comp in components:
            colors = set(raw[r][c] for r, c in comp)
            if len(colors) == 1 and list(colors)[0] == placeholder_color:
                placeholder_comps.append(comp)
            elif len(colors) > 1 or (len(colors) == 1 and list(colors)[0] != placeholder_color):
                if template_comp is None:
                    template_comp = comp
                # Multiple non-placeholder comps: pick the multi-color one
                elif len(colors) > 1:
                    template_comp = comp

        if template_comp is None:
            return [row[:] for row in raw]

        # Extract template
        t_min_r = min(r for r, c in template_comp)
        t_max_r = max(r for r, c in template_comp)
        t_min_c = min(c for r, c in template_comp)
        t_max_c = max(c for r, c in template_comp)
        t_h = t_max_r - t_min_r + 1
        t_w = t_max_c - t_min_c + 1

        tpl = [[0] * t_w for _ in range(t_h)]
        for r, c in template_comp:
            tpl[r - t_min_r][c - t_min_c] = raw[r][c]

        # Build output: copy input, replace each placeholder with template
        output = [row[:] for row in raw]
        for comp in placeholder_comps:
            p_min_r = min(r for r, c in comp)
            p_min_c = min(c for r, c in comp)
            for dr in range(t_h):
                for dc in range(t_w):
                    if p_min_r + dr < H and p_min_c + dc < W:
                        output[p_min_r + dr][p_min_c + dc] = tpl[dr][dc]

        return output

    def _apply_unique_quadrant_extract(self, rule, input_grid):
        raw = input_grid.raw
        H, W = len(raw), len(raw[0])

        # Find separator rows and cols
        sep_rows = [r for r in range(H) if all(raw[r][c] == 0 for c in range(W))]
        sep_cols = [c for c in range(W) if all(raw[r][c] == 0 for r in range(H))]

        row_bands = GeneralizeOperator._find_separator_bands(sep_rows, H)
        col_bands = GeneralizeOperator._find_separator_bands(sep_cols, W)

        if len(row_bands) != 1 or len(col_bands) != 1:
            return [row[:] for row in raw]

        r_sep_start, r_sep_end = row_bands[0]
        c_sep_start, c_sep_end = col_bands[0]

        quadrants = [
            (0, r_sep_start - 1, 0, c_sep_start - 1),
            (0, r_sep_start - 1, c_sep_end + 1, W - 1),
            (r_sep_end + 1, H - 1, 0, c_sep_start - 1),
            (r_sep_end + 1, H - 1, c_sep_end + 1, W - 1),
        ]

        # Find dominant color per quadrant
        quad_colors = []
        for r0, r1, c0, c1 in quadrants:
            color_counts = {}
            for r in range(r0, r1 + 1):
                for c in range(c0, c1 + 1):
                    v = raw[r][c]
                    if v != 0:
                        color_counts[v] = color_counts.get(v, 0) + 1
            dominant = max(color_counts, key=color_counts.get) if color_counts else 0
            quad_colors.append(dominant)

        # Find unique color
        from collections import Counter
        cc = Counter(quad_colors)
        unique_colors = [c for c, n in cc.items() if n == 1]
        if not unique_colors:
            return [row[:] for row in raw]

        unique_idx = quad_colors.index(unique_colors[0])
        r0, r1, c0, c1 = quadrants[unique_idx]

        return [raw[r][c0:c1 + 1] for r in range(r0, r1 + 1)]

    def _apply_self_ref_grid_fill(self, rule, input_grid):
        raw = input_grid.raw
        H, W = len(raw), len(raw[0])

        # Find separator rows and cols (all zero in input)
        sep_r_set = set()
        sep_c_set = set()
        for r in range(H):
            if all(raw[r][c] == 0 for c in range(W)):
                sep_r_set.add(r)
        for c in range(W):
            if all(raw[r][c] == 0 for r in range(H)):
                sep_c_set.add(c)

        # Build row and col groups
        row_groups = []
        r = 0
        while r < H:
            if r in sep_r_set:
                r += 1
                continue
            start = r
            while r < H and r not in sep_r_set:
                r += 1
            row_groups.append((start, r - 1))

        col_groups = []
        c = 0
        while c < W:
            if c in sep_c_set:
                c += 1
                continue
            start = c
            while c < W and c not in sep_c_set:
                c += 1
            col_groups.append((start, c - 1))

        n = len(row_groups)
        if n < 2 or n != len(col_groups):
            return [row[:] for row in raw]

        block_h = row_groups[0][1] - row_groups[0][0] + 1
        block_w = col_groups[0][1] - col_groups[0][0] + 1

        # Validate block dimensions match grid count
        if block_h != n or block_w != n:
            return [row[:] for row in raw]

        # Validate all blocks have consistent dimensions
        for rg in row_groups:
            if rg[1] - rg[0] + 1 != block_h:
                return [row[:] for row in raw]
        for cg in col_groups:
            if cg[1] - cg[0] + 1 != block_w:
                return [row[:] for row in raw]

        # Find foreground color from non-empty blocks
        fg_color = None
        for bi in range(n):
            for bj in range(n):
                rs = row_groups[bi][0]
                cs = col_groups[bj][0]
                for lr in range(block_h):
                    for lc in range(block_w):
                        if rs + lr < H and cs + lc < W:
                            v = raw[rs + lr][cs + lc]
                            if v != 0:
                                fg_color = v
                                break
                    if fg_color:
                        break
                if fg_color:
                    break
            if fg_color:
                break

        if fg_color is None:
            return [row[:] for row in raw]

        # Build output: copy separators, fill blocks
        output = [row[:] for row in raw]
        for bi in range(n):
            for bj in range(n):
                rs = row_groups[bi][0]
                cs = col_groups[bj][0]
                for lr in range(block_h):
                    for lc in range(block_w):
                        if rs + lr < H and cs + lc < W:
                            if lr == bi and lc == bj:
                                output[rs + lr][cs + lc] = 0
                            else:
                                output[rs + lr][cs + lc] = fg_color

        return output


    # ---- apply: point reflect tile -----------------------------------------

    def _apply_point_reflect_tile(self, rule, input_grid):
        raw = input_grid.raw
        H = len(raw)
        W = len(raw[0]) if raw else 0
        out = [[0] * (2 * W) for _ in range(2 * H)]
        for r in range(H):
            for c in range(W):
                v = raw[r][c]
                # rot180 in top-left
                out[r][c] = raw[H - 1 - r][W - 1 - c]
                # vflip in top-right
                out[r][W + c] = raw[H - 1 - r][c]
                # hflip in bottom-left
                out[H + r][c] = raw[r][W - 1 - c]
                # orig in bottom-right
                out[H + r][W + c] = v
        return out

    # ---- apply: nested rect color reverse -----------------------------------

    def _apply_nested_rect_color_reverse(self, rule, input_grid):
        raw = input_grid.raw
        H = len(raw)
        W = len(raw[0]) if raw else 0
        output = [row[:] for row in raw]

        # Find all connected non-zero rectangular objects
        visited = [[False] * W for _ in range(H)]
        for r in range(H):
            for c in range(W):
                if raw[r][c] != 0 and not visited[r][c]:
                    # BFS to find connected non-zero region
                    stack = [(r, c)]
                    cells = set()
                    while stack:
                        cr, cc = stack.pop()
                        if cr < 0 or cr >= H or cc < 0 or cc >= W:
                            continue
                        if (cr, cc) in cells or visited[cr][cc]:
                            continue
                        if raw[cr][cc] == 0:
                            continue
                        cells.add((cr, cc))
                        visited[cr][cc] = True
                        stack.extend([(cr+1, cc), (cr-1, cc), (cr, cc+1), (cr, cc-1)])

                    if not cells:
                        continue

                    min_r = min(cr for cr, cc in cells)
                    max_r = max(cr for cr, cc in cells)
                    min_c = min(cc for cr, cc in cells)
                    max_c = max(cc for cr, cc in cells)

                    # Extract concentric layer colors
                    layer_colors = []
                    tr, br, lc, rc = min_r, max_r, min_c, max_c
                    while tr <= br and lc <= rc:
                        layer_colors.append(raw[tr][lc])
                        tr += 1
                        br -= 1
                        lc += 1
                        rc -= 1

                    if len(layer_colors) < 2:
                        continue

                    # Build unique color sequence and reverse mapping
                    unique_colors = []
                    for cv in layer_colors:
                        if not unique_colors or unique_colors[-1] != cv:
                            unique_colors.append(cv)
                    if len(unique_colors) < 2:
                        continue

                    rev_unique = list(reversed(unique_colors))
                    color_map = {}
                    for uc, rc2 in zip(unique_colors, rev_unique):
                        color_map[uc] = rc2

                    # Apply color mapping to all cells in this object
                    for br2 in range(min_r, max_r + 1):
                        for bc in range(min_c, max_c + 1):
                            v = raw[br2][bc]
                            if v in color_map:
                                output[br2][bc] = color_map[v]

        return output

    # ---- apply: diagonal ring fill ------------------------------------------

    def _apply_diagonal_ring_fill(self, rule, input_grid):
        raw = input_grid.raw
        H = len(raw)
        W = len(raw[0]) if raw else 0
        output = [row[:] for row in raw]

        # Extract diagonal color sequence
        diag_colors = []
        for i in range(min(H, W)):
            v = raw[i][i]
            if v == 0 or v == 1:
                break
            diag_colors.append(v)

        # Find rectangle outlined in color 1
        border_color = 1
        rect_top = rect_bot = rect_left = rect_right = None
        for r in range(H):
            for c in range(W):
                if raw[r][c] == border_color:
                    if rect_top is None or r < rect_top:
                        rect_top = r
                    if rect_bot is None or r > rect_bot:
                        rect_bot = r
                    if rect_left is None or c < rect_left:
                        rect_left = c
                    if rect_right is None or c > rect_right:
                        rect_right = c

        if rect_top is None or not diag_colors:
            return [row[:] for row in raw]

        # Fill interior with concentric rings
        t = rect_top + 1
        b = rect_bot - 1
        l = rect_left + 1
        rr = rect_right - 1
        ci = 0
        while t <= b and l <= rr and ci < len(diag_colors):
            color = diag_colors[ci]
            for c in range(l, rr + 1):
                output[t][c] = color
                output[b][c] = color
            for r in range(t, b + 1):
                output[r][l] = color
                output[r][rr] = color
            t += 1
            b -= 1
            l += 1
            rr -= 1
            ci += 1

        # If there's still interior and we ran out of colors, fill with last
        while t <= b and l <= rr:
            color = diag_colors[-1]
            for c in range(l, rr + 1):
                output[t][c] = color
                output[b][c] = color
            for r in range(t, b + 1):
                output[r][l] = color
                output[r][rr] = color
            t += 1
            b -= 1
            l += 1
            rr -= 1

        return output

    # ---- apply: denoise isolated pixels --------------------------------------

    def _apply_denoise_isolated(self, rule, input_grid):
        """Remove all 8-isolated pixels (no same-color neighbor in 8 dirs)."""
        raw = input_grid.raw
        H = len(raw)
        W = len(raw[0]) if raw else 0
        output = [[0]*W for _ in range(H)]
        for r in range(H):
            for c in range(W):
                v = raw[r][c]
                if v == 0:
                    continue
                has_neighbor = False
                for dr in (-1, 0, 1):
                    for dc in (-1, 0, 1):
                        if dr == 0 and dc == 0:
                            continue
                        nr, nc = r + dr, c + dc
                        if 0 <= nr < H and 0 <= nc < W and raw[nr][nc] == v:
                            has_neighbor = True
                            break
                    if has_neighbor:
                        break
                if has_neighbor:
                    output[r][c] = v
        return output

    # ---- apply: L-shape diagonal ray -----------------------------------------

    def _apply_l_diagonal_ray(self, rule, input_grid):
        """For each 3-cell L-shape, shoot diagonal ray from missing 2x2 corner."""
        raw = input_grid.raw
        H = len(raw)
        W = len(raw[0]) if raw else 0
        output = [row[:] for row in raw]
        # Find fg color
        fg = 0
        for r in range(H):
            for c in range(W):
                if raw[r][c] != 0:
                    fg = raw[r][c]
                    break
            if fg:
                break
        if not fg:
            return output
        # Find 8-connected components
        visited = [[False]*W for _ in range(H)]
        comps = []
        for r in range(H):
            for c in range(W):
                if raw[r][c] == fg and not visited[r][c]:
                    comp = []
                    stack = [(r, c)]
                    while stack:
                        cr, cc = stack.pop()
                        if visited[cr][cc]:
                            continue
                        visited[cr][cc] = True
                        comp.append((cr, cc))
                        for dr2 in (-1, 0, 1):
                            for dc2 in (-1, 0, 1):
                                if dr2 == 0 and dc2 == 0:
                                    continue
                                nr, nc = cr + dr2, cc + dc2
                                if 0 <= nr < H and 0 <= nc < W and raw[nr][nc] == fg and not visited[nr][nc]:
                                    stack.append((nr, nc))
                    comps.append(comp)
        for comp in comps:
            if len(comp) != 3:
                continue
            cs = set(comp)
            min_r = min(r for r, c in cs)
            max_r = max(r for r, c in cs)
            min_c = min(c for r, c in cs)
            max_c = max(c for r, c in cs)
            if max_r - min_r != 1 or max_c - min_c != 1:
                continue
            missing = None
            for br in (min_r, max_r):
                for bc in (min_c, max_c):
                    if (br, bc) not in cs:
                        missing = (br, bc)
            if missing is None:
                continue
            opp_r = min_r if missing[0] == max_r else max_r
            opp_c = min_c if missing[1] == max_c else max_c
            dr = missing[0] - opp_r
            dc = missing[1] - opp_c
            cr, cc = missing[0] + dr, missing[1] + dc
            while 0 <= cr < H and 0 <= cc < W:
                output[cr][cc] = fg
                cr += dr
                cc += dc
        return output

    # ---- apply: nest rectangles by size --------------------------------------

    def _apply_nest_rectangles(self, rule, input_grid):
        """Detect rect shapes, sort by size, build nested concentric output."""
        raw = input_grid.raw
        H = len(raw)
        W = len(raw[0]) if raw else 0
        color_cells = {}
        for r in range(H):
            for c in range(W):
                v = raw[r][c]
                if v != 0:
                    if v not in color_cells:
                        color_cells[v] = []
                    color_cells[v].append((r, c))
        rects = []
        for color, cells in color_cells.items():
            min_r = min(r for r, c in cells)
            max_r = max(r for r, c in cells)
            min_c = min(c for r, c in cells)
            max_c = max(c for r, c in cells)
            h = max_r - min_r + 1
            w = max_c - min_c + 1
            rects.append((color, h, w, h * w))
        rects.sort(key=lambda x: -x[3])
        n = len(rects)
        inner_h = rects[-1][1]
        inner_w = rects[-1][2]
        oH = inner_h + 2 * (n - 1)
        oW = inner_w + 2 * (n - 1)
        output = [[0]*oW for _ in range(oH)]
        for ci, (color, _, _, _) in enumerate(rects):
            t, b, l, rr2 = ci, oH - 1 - ci, ci, oW - 1 - ci
            if t > b or l > rr2:
                break
            for c in range(l, rr2 + 1):
                output[t][c] = color
                output[b][c] = color
            for r in range(t, b + 1):
                output[r][l] = color
                output[r][rr2] = color
        return output

    # ---- apply: column_rank_recolor --------------------------------------

    def _apply_column_rank_recolor(self, rule, input_grid):
        raw = input_grid.raw
        H = len(raw)
        W = len(raw[0]) if raw else 0
        minority_color = rule["minority_color"]
        minority_cols = sorted(set(
            c for r in range(H) for c in range(W)
            if raw[r][c] == minority_color
        ))
        col_to_color = {col: idx + 1 for idx, col in enumerate(minority_cols)}
        out = [row[:] for row in raw]
        for r in range(H):
            for c in range(W):
                if raw[r][c] == minority_color:
                    out[r][c] = col_to_color.get(c, minority_color)
        return out

    # ---- apply: rect_frame_gap_ray ---------------------------------------

    def _apply_rect_frame_gap_ray(self, rule, input_grid):
        raw = input_grid.raw
        H = len(raw)
        W = len(raw[0]) if raw else 0
        bg_color = rule["bg_color"]
        frame_color = rule["frame_color"]
        fill_color = rule["fill_color"]
        frames = _find_rect_frames(raw, frame_color, bg_color, H, W)
        out = [row[:] for row in raw]
        for r1, c1, r2, c2, gap_r, gap_c, gap_side in frames:
            for r in range(r1 + 1, r2):
                for c in range(c1 + 1, c2):
                    out[r][c] = fill_color
            out[gap_r][gap_c] = fill_color
            if gap_side == "top":
                for r in range(gap_r - 1, -1, -1):
                    out[r][gap_c] = fill_color
            elif gap_side == "bottom":
                for r in range(gap_r + 1, H):
                    out[r][gap_c] = fill_color
            elif gap_side == "left":
                for c in range(gap_c - 1, -1, -1):
                    out[gap_r][c] = fill_color
            elif gap_side == "right":
                for c in range(gap_c + 1, W):
                    out[gap_r][c] = fill_color
        return out


    # ---- apply: asymmetric_block_select -----------------------------------

    def _apply_asymmetric_block_select(self, rule, input_grid):
        raw = input_grid.raw
        H = len(raw)
        W = len(raw[0]) if raw else 0
        N = W
        if N == 0 or H % N != 0:
            return [row[:] for row in raw]
        K = H // N
        for bi in range(K):
            block = [raw[bi * N + r][:N] for r in range(N)]
            is_sym = True
            for r in range(N):
                for c in range(r + 1, N):
                    if block[r][c] != block[c][r]:
                        is_sym = False
                        break
                if not is_sym:
                    break
            if not is_sym:
                return block
        # Fallback: return first block
        return [raw[r][:N] for r in range(N)]

    # ---- apply: seed_pixel_stamp -----------------------------------------

    def _apply_seed_pixel_stamp(self, rule, input_grid):
        raw = input_grid.raw
        H = len(raw)
        W = len(raw[0]) if raw else 0
        seed_color = rule["seed_color"]
        stamp_raw = rule["stamp"]
        stamp = {}
        for k, v in stamp_raw.items():
            dr, dc = map(int, k.split(","))
            stamp[(dr, dc)] = v

        seeds = [(r, c) for r in range(H) for c in range(W) if raw[r][c] == seed_color]
        out = [[0] * W for _ in range(H)]
        for sr, sc in seeds:
            for (dr, dc), val in stamp.items():
                nr, nc = sr + dr, sc + dc
                if 0 <= nr < H and 0 <= nc < W:
                    out[nr][nc] = val
        return out

    # ---- apply: color_count_expand ---------------------------------------

    def _apply_color_count_expand(self, rule, input_grid):
        raw = input_grid.raw
        iH = len(raw)
        iW = len(raw[0]) if raw else 0
        colors = set()
        for r in range(iH):
            for c in range(iW):
                colors.add(raw[r][c])
        K = len(colors)
        if K <= 1:
            return [row[:] for row in raw]
        oH = iH * K
        oW = iW * K
        out = [[0] * oW for _ in range(oH)]
        for r in range(iH):
            for c in range(iW):
                val = raw[r][c]
                for dr in range(K):
                    for dc in range(K):
                        out[r * K + dr][c * K + dc] = val
        return out

    def _apply_line_rank_recolor(self, rule, input_grid):
        """Replace each line of 5s with a color based on its length rank."""
        raw = input_grid.raw
        H = len(raw)
        W = len(raw[0]) if raw else 0
        rank_colors = rule["rank_colors"]
        if not rank_colors:
            return None
        out = [row[:] for row in raw]

        # Find lines as connected components of 5-cells
        visited = set()
        lines = []
        for r in range(H):
            for c in range(W):
                if raw[r][c] != 5 or (r, c) in visited:
                    continue
                comp = []
                queue = [(r, c)]
                visited.add((r, c))
                while queue:
                    cr, cc = queue.pop(0)
                    comp.append((cr, cc))
                    for dr, dc in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                        nr, nc = cr + dr, cc + dc
                        if (0 <= nr < H and 0 <= nc < W
                                and (nr, nc) not in visited
                                and raw[nr][nc] == 5):
                            visited.add((nr, nc))
                            queue.append((nr, nc))
                if len(comp) >= 2:
                    lines.append(comp)

        lines.sort(key=lambda L: -len(L))
        for i, line in enumerate(lines):
            color = rank_colors[i] if i < len(rank_colors) else rank_colors[-1]
            for r, c in line:
                out[r][c] = color
        return out

    def _apply_max_rect_fill(self, rule, input_grid):
        """Fill maximal squares of 0s (greedy largest-first) with fill_color."""
        raw = input_grid.raw
        H = len(raw)
        W = len(raw[0]) if raw else 0
        fill_color = rule["fill_color"]
        out = [row[:] for row in raw]

        # dp[r][c] = max side of all-0 square with (r,c) as top-left
        dp = [[0] * W for _ in range(H)]
        for r in range(H - 1, -1, -1):
            for c in range(W - 1, -1, -1):
                if raw[r][c] != 0:
                    dp[r][c] = 0
                elif r == H - 1 or c == W - 1:
                    dp[r][c] = 1
                else:
                    dp[r][c] = 1 + min(dp[r + 1][c],
                                       dp[r][c + 1],
                                       dp[r + 1][c + 1])
        squares = []
        for r in range(H):
            for c in range(W):
                if dp[r][c] >= 2:
                    squares.append((dp[r][c], r, c))
        squares.sort(key=lambda x: (-x[0], x[1], x[2]))
        filled = set()
        for s, r, c in squares:
            cells = set()
            for dr in range(s):
                for dc in range(s):
                    cells.add((r + dr, c + dc))
            if cells & filled:
                continue
            filled |= cells
        for (r, c) in filled:
            out[r][c] = fill_color
        return out

    def _apply_divider_complement_merge(self, rule, input_grid):
        """Split on divider, merge halves if complementary, else keep left."""
        raw = input_grid.raw
        H = len(raw)
        W = len(raw[0]) if raw else 0
        divider_col = rule["divider_col"]
        left_w = rule["left_w"]

        # Bounds check: grid must be wide enough for divider + both halves
        if divider_col >= W or divider_col + 1 + left_w > W or left_w > divider_col:
            return None

        left = [[raw[r][c] for c in range(left_w)] for r in range(H)]
        right = [[raw[r][divider_col + 1 + c] for c in range(left_w)]
                 for r in range(H)]

        # Check if right non-zero cells complement left zero cells
        complementary = True
        for r in range(H):
            for c in range(left_w):
                if left[r][c] != 0 and right[r][c] != 0:
                    complementary = False
                    break
            if not complementary:
                break

        if complementary:
            out = [row[:] for row in left]
            for r in range(H):
                for c in range(left_w):
                    if right[r][c] != 0:
                        out[r][c] = right[r][c]
            return out
        else:
            return left

    # ---- apply: multi_rect_fill_ray ----------------------------------------

    def _apply_multi_rect_fill_ray(self, rule, input_grid):
        raw = input_grid.raw
        H = len(raw)
        W = len(raw[0]) if raw else 0
        bg_color = rule["bg_color"]
        frame_color = rule["frame_color"]
        fill_color = rule["fill_color"]
        frames = GeneralizeOperator._find_rect_frames_any(
            raw, frame_color, bg_color, H, W)
        out = [row[:] for row in raw]
        for r1, c1, r2, c2, gap_r, gap_c, gap_side in frames:
            for r in range(r1 + 1, r2):
                for c in range(c1 + 1, c2):
                    out[r][c] = fill_color
            if gap_r is not None:
                out[gap_r][gap_c] = fill_color
                if gap_side == "top":
                    for r in range(gap_r - 1, -1, -1):
                        out[r][gap_c] = fill_color
                elif gap_side == "bottom":
                    for r in range(gap_r + 1, H):
                        out[r][gap_c] = fill_color
                elif gap_side == "left":
                    for c in range(gap_c - 1, -1, -1):
                        out[gap_r][c] = fill_color
                elif gap_side == "right":
                    for c in range(gap_c + 1, W):
                        out[gap_r][c] = fill_color
        return out

    # ---- apply: corner_seed_symmetric_frame --------------------------------

    def _apply_corner_seed_symmetric_frame(self, rule, input_grid):
        raw = input_grid.raw
        H = len(raw)
        W = len(raw[0]) if raw else 0
        if H != W or H % 2 == 0:
            return [row[:] for row in raw]

        pixels = []
        for r in range(H):
            for c in range(W):
                if raw[r][c] != 0:
                    pixels.append((r, c, raw[r][c]))

        if not pixels:
            return [row[:] for row in raw]

        center = H // 2
        quadrants = set()
        for r, c, v in pixels:
            qr = 0 if r <= center else 1
            qc = 0 if c <= center else 1
            quadrants.add((qr, qc))

        if len(quadrants) != 1:
            return [row[:] for row in raw]
        qr, qc = quadrants.pop()

        normalized = []
        for r, c, v in pixels:
            nr = r if qr == 0 else H - 1 - r
            nc = c if qc == 0 else W - 1 - c
            normalized.append((nr, nc, v))
        normalized.sort()

        return GeneralizeOperator._build_corner_seed_frame(normalized, H, W)

    # ---- apply: frame_corner_projectile ------------------------------------

    def _apply_frame_corner_projectile(self, rule, input_grid):
        from collections import Counter
        raw = input_grid.raw
        H = len(raw)
        W = len(raw[0]) if raw else 0
        bg = rule["bg_color"]
        freq = Counter()
        for r in range(H):
            for c in range(W):
                freq[raw[r][c]] += 1
        non_bg = sorted(set(freq.keys()) - {bg})
        if len(non_bg) != 2:
            return [row[:] for row in raw]
        fc, cc = GeneralizeOperator._detect_frame_content(raw, H, W, non_bg)
        if fc is None:
            return [row[:] for row in raw]
        result = GeneralizeOperator._compute_frame_projectile(
            raw, H, W, bg, fc, cc)
        if result is None:
            return [row[:] for row in raw]
        return result


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
