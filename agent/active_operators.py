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
# Module-level prediction helpers (shared by Generalize + Predict)
# ======================================================================

_ORTHO_TRANSFORMS = [
    (1, 0, 0, 1),    # identity
    (-1, 0, 0, -1),  # 180 deg
    (0, -1, 1, 0),   # 90 deg CCW
    (0, 1, -1, 0),   # 90 deg CW
    (1, 0, 0, -1),   # reflect horizontal
    (-1, 0, 0, 1),   # reflect vertical
    (0, 1, 1, 0),    # reflect main diagonal
    (0, -1, -1, 0),  # reflect anti-diagonal
]


def _find_nonzero_components(raw):
    """Find 4-connected components of non-zero cells."""
    h = len(raw)
    w = len(raw[0]) if raw else 0
    visited = set()
    components = []
    for r in range(h):
        for c in range(w):
            if raw[r][c] == 0 or (r, c) in visited:
                continue
            comp = []
            queue = [(r, c)]
            while queue:
                cr, cc = queue.pop(0)
                if (cr, cc) in visited:
                    continue
                visited.add((cr, cc))
                comp.append((cr, cc, raw[cr][cc]))
                for dr, dc in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                    nr, nc = cr + dr, cc + dc
                    if 0 <= nr < h and 0 <= nc < w and (nr, nc) not in visited and raw[nr][nc] != 0:
                        queue.append((nr, nc))
            components.append(comp)
    return components


def _anchor_template_predict(raw):
    """Predict output for anchor-template-placement tasks.

    Template shapes (multi-cell connected components with body + anchor colors)
    are removed.  Each group of scattered anchor pixels gets a rotated/reflected
    copy of its matching template placed around it.
    """
    h = len(raw)
    w = len(raw[0]) if raw else 0
    comps = _find_nonzero_components(raw)

    templates = [c for c in comps if len(c) > 1]
    scattered = [c[0] for c in comps if len(c) == 1]

    if not templates or not scattered:
        return None

    # Analyze templates
    tinfos = []
    for comp in templates:
        colors = {}
        for r, c, col in comp:
            colors[col] = colors.get(col, 0) + 1
        body = max(colors, key=colors.get)
        anchors = sorted(c for c in colors if c != body)
        if not anchors:
            return None
        tinfos.append({'cells': comp, 'body': body, 'anchors': set(anchors)})

    by_color = {}
    for r, c, col in scattered:
        by_color.setdefault(col, []).append((r, c))

    used_s = set()
    used_t = set()
    placements = []

    for ti, tinfo in enumerate(tinfos):
        if ti in used_t:
            continue
        matched = False
        for s_r, s_c, s_col in scattered:
            if (s_r, s_c) in used_s or s_col not in tinfo['anchors']:
                continue
            t_pos = None
            for r, c, col in tinfo['cells']:
                if col == s_col:
                    t_pos = (r, c)
                    break
            if t_pos is None:
                continue
            rel = {}
            for r, c, col in tinfo['cells']:
                if col in tinfo['anchors'] and col != s_col:
                    rel[col] = (r - t_pos[0], c - t_pos[1])
            body_rel = [(r - t_pos[0], c - t_pos[1])
                        for r, c, col in tinfo['cells'] if col == tinfo['body']]
            anchor_rel = {s_col: (0, 0)}
            anchor_rel.update(rel)

            for a, b, ct, dd in _ORTHO_TRANSFORMS:
                group = [(s_r, s_c, s_col)]
                ok = True
                for ac, (tdr, tdc) in rel.items():
                    er = s_r + a * tdr + b * tdc
                    ec = s_c + ct * tdr + dd * tdc
                    found = False
                    for pr, pc in by_color.get(ac, []):
                        if (pr, pc) not in used_s and pr == er and pc == ec:
                            group.append((pr, pc, ac))
                            found = True
                            break
                    if not found:
                        ok = False
                        break
                if ok and len(group) == len(tinfo['anchors']):
                    placements.append({
                        'ref': (s_r, s_c),
                        'transform': (a, b, ct, dd),
                        'body_rel': body_rel,
                        'body_color': tinfo['body'],
                        'anchor_rel': anchor_rel,
                    })
                    for r, c, _ in group:
                        used_s.add((r, c))
                    used_t.add(ti)
                    matched = True
                    break
            if matched:
                break

    if not placements:
        return None

    output = [[0] * w for _ in range(h)]
    for p in placements:
        a, b, ct, dd = p['transform']
        sr, sc = p['ref']
        for dr, dc in p['body_rel']:
            nr = sr + a * dr + b * dc
            nc = sc + ct * dr + dd * dc
            if 0 <= nr < h and 0 <= nc < w:
                output[nr][nc] = p['body_color']
        for col, (dr, dc) in p['anchor_rel'].items():
            nr = sr + a * dr + b * dc
            nc = sc + ct * dr + dd * dc
            if 0 <= nr < h and 0 <= nc < w:
                output[nr][nc] = col
    return output


def _find_divider_edge(raw, h, w):
    """Find which edge has a line of 1s."""
    if all(raw[0][c] == 1 for c in range(w)):
        return 'top'
    if all(raw[h - 1][c] == 1 for c in range(w)):
        return 'bottom'
    if all(raw[r][0] == 1 for r in range(h)):
        return 'left'
    if all(raw[r][w - 1] == 1 for r in range(h)):
        return 'right'
    return None


def _find_hollow_blocks(raw, h, w):
    """Find 3x3 hollow square blocks (xxx/x0x/xxx pattern)."""
    blocks = []
    used = set()
    for r in range(h - 2):
        for c in range(w - 2):
            if (r, c) in used:
                continue
            color = raw[r][c]
            if color <= 1:
                continue
            if (raw[r][c + 1] == color and raw[r][c + 2] == color and
                raw[r + 1][c] == color and raw[r + 1][c + 1] == 0 and
                raw[r + 1][c + 2] == color and
                raw[r + 2][c] == color and raw[r + 2][c + 1] == color and
                raw[r + 2][c + 2] == color):
                blocks.append((r, c, color))
                for dr in range(3):
                    for dc in range(3):
                        used.add((r + dr, c + dc))
    return blocks


def _find_zone_split(positions):
    """Find index where positions have the largest gap (zone boundary)."""
    if len(positions) < 2:
        return None
    gaps = [(positions[i] - positions[i - 1], i) for i in range(1, len(positions))]
    max_gap = max(gaps, key=lambda x: x[0])
    min_gap = min(gaps, key=lambda x: x[0])
    if max_gap[0] > min_gap[0]:
        return max_gap[1]
    return None


def _block_gravity_predict(raw):
    """Predict output for block-count-gravity tasks.

    Detects 3x3 hollow blocks, finds the divider edge, splits zones,
    counts blocks per zone per row/col, and packs them toward the divider.
    """
    h = len(raw)
    w = len(raw[0]) if raw else 0

    divider = _find_divider_edge(raw, h, w)
    if divider is None:
        return None

    blocks = _find_hollow_blocks(raw, h, w)
    if not blocks:
        return None

    row_pos = sorted(set(r for r, c, color in blocks))
    col_pos = sorted(set(c for r, c, color in blocks))
    ri = {rp: i for i, rp in enumerate(row_pos)}
    ci = {cp: j for j, cp in enumerate(col_pos)}
    gh, gw = len(row_pos), len(col_pos)

    grid = [[0] * gw for _ in range(gh)]
    for r, c, color in blocks:
        grid[ri[r]][ci[c]] = color

    if divider in ('top', 'bottom'):
        zs = _find_zone_split(col_pos)
        if zs is None:
            return None
        out = [[0] * gw for _ in range(gh)]
        for i in range(gh):
            z1 = [grid[i][j] for j in range(zs) if grid[i][j] != 0]
            z2 = [grid[i][j] for j in range(zs, gw) if grid[i][j] != 0]
            combined = z1 + z2
            n = len(combined)
            if divider == 'top':
                for k, v in enumerate(combined):
                    out[i][gw - n + k] = v
            else:
                for k, v in enumerate(combined):
                    out[i][k] = v
        return out
    else:
        zs = _find_zone_split(row_pos)
        if zs is None:
            return None
        out = [[0] * gw for _ in range(gh)]
        for j in range(gw):
            z1 = [grid[i][j] for i in range(zs) if grid[i][j] != 0]
            z2 = [grid[i][j] for i in range(zs, gh) if grid[i][j] != 0]
            combined = z1 + z2
            n = len(combined)
            if divider == 'right':
                for k, v in enumerate(combined):
                    out[gh - n + k][j] = v
            else:
                for k, v in enumerate(combined):
                    out[k][j] = v
        return out


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

        # Strategy 0a: path with turn signals (L-path drawing) -- high specificity
        rule = self._try_path_turn_signals(task)

        # Strategy 0b: arrow slide with mirror across divider -- high specificity
        if rule is None:
            rule = self._try_arrow_slide_mirror(task)

        # Strategy 0c: quadrant shape swap -- high specificity
        if rule is None:
            rule = self._try_quadrant_shape_swap(task)

        # Strategy 1: sequential recoloring (e.g., color objects 1, 2, 3, ...)
        if rule is None:
            rule = self._try_recolor_sequential(patterns)

        # Strategy 2: max column filter (before color_mapping to avoid false match)
        if rule is None:
            rule = self._try_max_column(task)

        # Strategy 3: connect aligned diamond shapes
        if rule is None:
            rule = self._try_connect_diamonds(task)

        # Strategy 4: fill rectangular interiors by area
        if rule is None:
            rule = self._try_fill_rect_interior(task)

        # Strategy 4b: flood fill interior of closed boundary regions
        if rule is None:
            rule = self._try_flood_fill_interior(task)

        # Strategy 26: noise removal -- keep only cells in 2x2+ solid rectangles
        if rule is None:
            rule = self._try_noise_remove_rect(task)

        # Strategy 44: mirror symmetric recolor (symmetric 5-pairs become 1)
        if rule is None:
            rule = self._try_mirror_symmetric_recolor(task)

        # Strategy 49: rect outline decorate (square outlines get color-2 corner marks)
        # (must run before color_mapping to avoid false match)
        if rule is None:
            rule = self._try_rect_outline_decorate(task)

        # Strategy 46: cross center mark (equidistant pair-cross intersections get marked)
        # (must run before color_mapping to avoid false match on bg->mark transitions)
        if rule is None:
            rule = self._try_cross_center_mark(task)

        # Strategy 59: pair diagonal reflect (must run before color_mapping to avoid false match)
        if rule is None:
            rule = self._try_pair_diagonal_reflect(task)

        # Strategy 72: corner rect fill (must run before color_mapping to avoid false match)
        if rule is None:
            rule = self._try_corner_rect_fill(task)

        # Strategy 73: dot expand band (single 0-dot in uniform color band -> full column stripe)
        if rule is None:
            rule = self._try_dot_expand_band(task)

        # Strategy 74: fill square holes (rectangular 5-frames, fill interior with 2 only if square)
        if rule is None:
            rule = self._try_fill_square_holes(task)

        # Strategy 75: column staircase shadow (vertical 5-column casts 8-left / 6-right triangles)
        if rule is None:
            rule = self._try_column_staircase_shadow(task)

        # Strategy 5: simple 1:1 color mapping
        if rule is None:
            rule = self._try_color_mapping(patterns)

        # Strategy 4: recolor connected components by size rank
        if rule is None:
            rule = self._try_recolor_by_size(patterns)

        # Strategy 5: scale up (each cell -> NxN block)
        if rule is None:
            rule = self._try_scale_up(task)

        # Strategy 6: flip and stack (mirror reflection)
        if rule is None:
            rule = self._try_flip_stack(task)

        # Strategy 7: concentric ring reversal
        if rule is None:
            rule = self._try_ring_reversal(task)

        # Strategy 8: staircase fill (single row -> triangle)
        if rule is None:
            rule = self._try_staircase_fill(task)

        # Strategy 9: corner quadrant fill
        if rule is None:
            rule = self._try_corner_quadrant(task)

        # Strategy 10: stripe zone fill (colored stripes expand to fill zones)
        if rule is None:
            rule = self._try_stripe_zone_fill(task)

        # Strategy 11: cross/arrow shapes project center color to grid borders
        if rule is None:
            rule = self._try_cross_border_project(task)

        # Strategy 12: grid lines oscillate with zigzag pattern
        if rule is None:
            rule = self._try_grid_zigzag(task)

        # Strategy 13: three blocks in a line, middle slides through splittable outer
        if rule is None:
            rule = self._try_block_slide_split(task)

        # Strategy 14: gravity fall -- objects fall toward border wall
        if rule is None:
            rule = self._try_gravity_fall(task)

        # Strategy 15: count diamond -- scattered dots counted, V/diamond drawn
        if rule is None:
            rule = self._try_count_diamond(task)

        # Strategy 16: anchor template placement (template shape + scattered anchors)
        if rule is None:
            rule = self._try_anchor_template_place(task)

        # Strategy 17: block count gravity (3x3 hollow blocks + divider line)
        if rule is None:
            rule = self._try_block_count_gravity(task)

        # Strategy 18: cross/diagonal decoration around isolated pixels
        if rule is None:
            rule = self._try_cross_decorator(task)

        # Strategy 19: 2x2 point-symmetric tiling (double dimensions)
        if rule is None:
            rule = self._try_tile_mirror(task)

        # Strategy 20: boolean NOR of two grid sections split by divider row
        if rule is None:
            rule = self._try_mask_nor(task)

        # Strategy 21: count marker color inside frame, encode as filled 3x3
        if rule is None:
            rule = self._try_count_inside_frame(task)

        # Strategy 23: rotation quad tile (0°, 90°CCW, 180°, 90°CW)
        if rule is None:
            rule = self._try_rotation_quad_tile(task)

        # Strategy 24: diagonal line extension from 2x2 block
        if rule is None:
            rule = self._try_diagonal_extend(task)

        # Strategy 25: 2x2 core quadrant fill (diag-opposite color in each quadrant)
        if rule is None:
            rule = self._try_core_quadrant_fill(task)

        # Strategy 26: frame color swap (extract rect block, swap 2 colors)
        if rule is None:
            rule = self._try_frame_color_swap(task)

        # Strategy 27: pattern tile fill (tile pattern upward to fill grid)
        if rule is None:
            rule = self._try_pattern_tile_fill(task)

        # Strategy 28: template color remap (extract block, remap via key pairs)
        if rule is None:
            rule = self._try_template_color_remap(task)

        # Strategy 29: marker ray fill (isolated pixels fill right then down)
        if rule is None:
            rule = self._try_marker_ray_fill(task)

        # Strategy 30: crop bounding box (extract non-bg region)
        if rule is None:
            rule = self._try_crop_bbox(task)

        # Strategy 31: binary grid XOR (two grid halves split by divider, XOR)
        if rule is None:
            rule = self._try_binary_grid_xor(task)

        # Strategy 32: nonzero count scale (each cell -> KxK block, K = # non-zero)
        if rule is None:
            rule = self._try_nonzero_count_scale(task)

        # Strategy 33: stripe rotate (vertical stripes -> cycling column)
        if rule is None:
            rule = self._try_stripe_rotate(task)

        # Strategy 34: frame solid compose (tile framed rects, ignore solid)
        if rule is None:
            rule = self._try_frame_solid_compose(task)

        # Strategy 35: self tile (NxN input → N²xN² by placing copies/complement at non-zero positions)
        if rule is None:
            rule = self._try_self_tile(task)

        # Strategy 36: separator AND (grid split by separator column, AND of halves)
        if rule is None:
            rule = self._try_separator_and(task)

        # Strategy 37: checkerboard tile (HxW tiled 3x3 with alternating horizontal flip)
        if rule is None:
            rule = self._try_checkerboard_tile(task)

        # Strategy 38: point to line (colored dots expand to full-span row/column lines)
        if rule is None:
            rule = self._try_point_to_line(task)

        # Strategy 39: quadrant rotation completion (separator-split grid, missing 4th rotation)
        if rule is None:
            rule = self._try_quadrant_rotation_completion(task)

        # Strategy 40: stamp pattern (marker pixels replaced by fixed local pattern)
        if rule is None:
            rule = self._try_stamp_pattern(task)

        # Strategy 41: global color swap (cell-level 1:1 color remap)
        if rule is None:
            rule = self._try_global_color_swap(task)

        # Strategy 42: quadrant extract (separator lines -> extract shapes -> tile)
        if rule is None:
            rule = self._try_quadrant_extract(task)

        # Strategy 43: key color swap (2x2 key in corner defines pairwise color swaps)
        if rule is None:
            rule = self._try_key_color_swap(task)

        # Strategy 45: bar frame gravity (4 bars form frame, scattered cells shadow toward matching bar)
        if rule is None:
            rule = self._try_bar_frame_gravity(task)

        # Strategy 47: corner L-extension (dots extend to nearest corner in L-shape)
        if rule is None:
            rule = self._try_corner_L_extend(task)

        # Strategy 48: rotation quad tile 4x (NxN -> 4Nx4N with 2x2-repeated rotation quadrants)
        if rule is None:
            rule = self._try_rotation_quad_tile_4x(task)

        # Strategy 49: rect outline decorate (square outlines get color-2 corner marks)
        if rule is None:
            rule = self._try_rect_outline_decorate(task)

        # Strategy 50: most frequent cross color (find 4-centered crosses, output majority color)
        if rule is None:
            rule = self._try_most_frequent_cross_color(task)

        # Strategy 51: grid separator invert (0-divided grid, base<->blank swap, 5=corruption)
        if rule is None:
            rule = self._try_grid_separator_invert(task)

        # Strategy 52: zero region classify (0-cells split into edge-touching vs interior)
        if rule is None:
            rule = self._try_zero_region_classify(task)

        # Strategy 53: grid intersection vote (large gridline grid -> small output via intersection colors)
        if rule is None:
            rule = self._try_grid_intersection_vote(task)

        # Strategy 54: sparse grid compress (NxN blocks each with 1 non-zero -> compressed grid)
        if rule is None:
            rule = self._try_sparse_grid_compress(task)

        # Strategy 55: extract unique shape (dense shape amid noise -> crop bbox)
        if rule is None:
            rule = self._try_extract_unique_shape(task)

        # Strategy 56: shape match recolor (template color shapes matched to reference shapes)
        if rule is None:
            rule = self._try_shape_match_recolor(task)

        # Strategy 57: L-triomino diagonal extension (L-shapes extend diagonal from open corner)
        if rule is None:
            rule = self._try_l_triomino_extend(task)

        # Strategy 58: rectangle patch overlay (combine rectangular sub-regions)
        if rule is None:
            rule = self._try_rect_patch_overlay(task)

        # Strategy 60: recolor by enclosed holes (shapes recolored by hole count)
        if rule is None:
            rule = self._try_recolor_by_holes(task)

        # Strategy 61: stripe tile (two seed pixels define repeating stripes)
        if rule is None:
            rule = self._try_stripe_tile(task)

        # Strategy 62: diamond symmetry fill (complete symmetric lattice pattern)
        if rule is None:
            rule = self._try_diamond_symmetry_fill(task)

        # Strategy 63: complement tile (invert binary grid, tile 2x2)
        if rule is None:
            rule = self._try_complement_tile(task)

        # Strategy 64: ring color cycle (concentric frame color rotation)
        if rule is None:
            rule = self._try_ring_color_cycle(task)

        # Strategy 65: column projection tile (fill active columns, tile 2x2)
        if rule is None:
            rule = self._try_column_projection_tile(task)

        # Strategy 66: select asymmetric block (3 stacked NxN blocks, pick non-diagonal-symmetric one)
        if rule is None:
            rule = self._try_select_asymmetric_block(task)

        # Strategy 67: shape complement merge (two shapes on bg interlock to fill a rectangle)
        if rule is None:
            rule = self._try_shape_complement_merge(task)

        # Strategy 68: hub assembly (shapes with color-5 anchors assembled into 3x3 centered grid)
        if rule is None:
            rule = self._try_hub_assembly(task)

        # Strategy 69: shape pixel scale (extract shape bbox, scale each cell to NxN block)
        if rule is None:
            rule = self._try_shape_pixel_scale(task)

        # Strategy 70: quadrant color template (4 scattered pixels fill NxN template by quadrant)
        if rule is None:
            rule = self._try_quadrant_color_template(task)

        # Strategy 71: sort bars right-align (horizontal bars sorted by length, right-aligned above floor)
        if rule is None:
            rule = self._try_sort_bars_right_align(task)

        # Strategy 72: corner rect fill (4 corner markers define rectangle, fill interior with color)
        if rule is None:
            rule = self._try_corner_rect_fill(task)

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

    # ---- strategy: recolor by component size ----------------------------

    def _try_recolor_by_size(self, patterns):
        """
        Detect pattern: all objects share one source color; each connected
        component is recolored based on its size (cell count).  Components
        of the same size receive the same output color.
        """
        pair_analyses = patterns.get("pair_analyses", [])
        if not pair_analyses or not patterns.get("grid_size_preserved"):
            return None

        source_colors = set()
        for analysis in pair_analyses:
            if analysis["num_groups"] == 0:
                return None
            for g in analysis["groups"]:
                if len(g["input_colors"]) != 1 or len(g["output_colors"]) != 1:
                    return None
                source_colors.add(g["input_colors"][0])

        if len(source_colors) != 1:
            return None
        source_color = list(source_colors)[0]

        # Need at least 2 distinct sizes (otherwise color_mapping suffices)
        all_sizes = set()
        for analysis in pair_analyses:
            for g in analysis["groups"]:
                all_sizes.add(g["cell_count"])
        if len(all_sizes) < 2:
            return None

        # Build size -> color mapping; must be consistent across all pairs
        size_to_color = {}
        for analysis in pair_analyses:
            for g in analysis["groups"]:
                size = g["cell_count"]
                color = g["output_colors"][0]
                if size in size_to_color:
                    if size_to_color[size] != color:
                        return None
                else:
                    size_to_color[size] = color

        # Different sizes must map to different colors
        if len(set(size_to_color.values())) != len(size_to_color):
            return None

        return {
            "type": "recolor_by_size",
            "source_color": source_color,
            "size_to_color": {str(k): v for k, v in size_to_color.items()},
            "confidence": 0.9,
        }

    # ---- strategy: scale up (pixel doubling / tripling) -----------------

    def _try_scale_up(self, task):
        """
        Detect pattern: output is an integer scale of the input -- each
        input cell becomes an NxN block of the same color.
        """
        if task is None:
            return None

        pairs = task.example_pairs
        if not pairs:
            return None

        factors = set()
        for pair in pairs:
            g0, g1 = pair.input_grid, pair.output_grid
            if g0 is None or g1 is None:
                return None
            h0, w0 = len(g0.raw), len(g0.raw[0]) if g0.raw else 0
            h1, w1 = len(g1.raw), len(g1.raw[0]) if g1.raw else 0
            if h0 == 0 or w0 == 0:
                return None
            if h1 % h0 != 0 or w1 % w0 != 0:
                return None
            fh, fw = h1 // h0, w1 // w0
            if fh != fw or fh <= 1:
                return None
            factors.add(fh)

        if len(factors) != 1:
            return None
        factor = list(factors)[0]

        # Verify every cell maps to a uniform NxN block
        for pair in pairs:
            raw_in = pair.input_grid.raw
            raw_out = pair.output_grid.raw
            for r in range(len(raw_in)):
                for c in range(len(raw_in[0])):
                    expected = raw_in[r][c]
                    for dr in range(factor):
                        for dc in range(factor):
                            if raw_out[r * factor + dr][c * factor + dc] != expected:
                                return None

        return {
            "type": "scale_up",
            "factor": factor,
            "confidence": 1.0,
        }

    # ---- strategy: flip and stack (mirror reflection) -------------------

    def _try_flip_stack(self, task):
        """
        Detect pattern: output is the input stacked with its mirror image
        either vertically (height doubles) or horizontally (width doubles).
        """
        if task is None:
            return None

        pairs = task.example_pairs
        if not pairs:
            return None

        if self._check_flip_stack_axis(pairs, "vertical"):
            return {"type": "flip_stack", "axis": "vertical", "confidence": 1.0}
        if self._check_flip_stack_axis(pairs, "horizontal"):
            return {"type": "flip_stack", "axis": "horizontal", "confidence": 1.0}
        return None

    @staticmethod
    def _check_flip_stack_axis(pairs, axis):
        for pair in pairs:
            raw_in = pair.input_grid.raw
            raw_out = pair.output_grid.raw
            h = len(raw_in)
            w = len(raw_in[0]) if raw_in else 0
            oh = len(raw_out)
            ow = len(raw_out[0]) if raw_out else 0

            if axis == "vertical":
                if oh != 2 * h or ow != w:
                    return False
                for r in range(h):
                    for c in range(w):
                        if raw_out[r][c] != raw_in[r][c]:
                            return False
                        if raw_out[h + r][c] != raw_in[h - 1 - r][c]:
                            return False
            else:  # horizontal
                if oh != h or ow != 2 * w:
                    return False
                for r in range(h):
                    for c in range(w):
                        if raw_out[r][c] != raw_in[r][c]:
                            return False
                        if raw_out[r][w + c] != raw_in[r][w - 1 - c]:
                            return False
        return True

    # ---- strategy: concentric ring reversal ------------------------------

    def _try_ring_reversal(self, task):
        """
        Detect pattern: grid consists of concentric rectangular rings,
        output reverses the color order (outermost <-> innermost).
        """
        if task is None:
            return None
        pairs = task.example_pairs
        if not pairs:
            return None

        for pair in pairs:
            g0, g1 = pair.input_grid, pair.output_grid
            if g0 is None or g1 is None:
                return None
            if len(g0.raw) != len(g1.raw) or len(g0.raw[0]) != len(g1.raw[0]):
                return None
            in_rings = self._detect_rings(g0.raw)
            out_rings = self._detect_rings(g1.raw)
            if in_rings is None or out_rings is None:
                return None
            if len(in_rings) < 2 or len(in_rings) != len(out_rings):
                return None
            if in_rings != list(reversed(out_rings)):
                return None

        return {"type": "ring_reversal", "confidence": 1.0}

    @staticmethod
    def _detect_rings(grid):
        """Detect concentric rectangular rings. Returns list of colors outside-in, or None."""
        h = len(grid)
        w = len(grid[0]) if grid else 0
        if h == 0 or w == 0:
            return None
        colors = []
        top, left, bottom, right = 0, 0, h - 1, w - 1
        while top <= bottom and left <= right:
            color = grid[top][left]
            for c in range(left, right + 1):
                if grid[top][c] != color or grid[bottom][c] != color:
                    return None
            for r in range(top, bottom + 1):
                if grid[r][left] != color or grid[r][right] != color:
                    return None
            colors.append(color)
            top += 1
            left += 1
            bottom -= 1
            right -= 1
        return colors

    # ---- strategy: max column filter -------------------------------------

    def _try_max_column(self, task):
        """
        Detect pattern: output keeps only the column with the most non-zero
        entries and zeros out everything else. Tie-break: closest to center.
        """
        if task is None:
            return None
        pairs = task.example_pairs
        if not pairs:
            return None

        for pair in pairs:
            g0, g1 = pair.input_grid, pair.output_grid
            if g0 is None or g1 is None:
                return None
            raw_in, raw_out = g0.raw, g1.raw
            h = len(raw_in)
            w = len(raw_in[0]) if raw_in else 0
            if h != len(raw_out) or w != (len(raw_out[0]) if raw_out else 0):
                return None
            if h == 0 or w == 0:
                return None

            col_counts = [sum(1 for r in range(h) if raw_in[r][c] != 0)
                          for c in range(w)]
            max_count = max(col_counts)
            if max_count == 0:
                return None

            center = (w - 1) / 2.0
            best_col = min(
                (c for c in range(w) if col_counts[c] == max_count),
                key=lambda c: abs(c - center),
            )

            for r in range(h):
                for c in range(w):
                    if c == best_col:
                        if raw_out[r][c] != raw_in[r][c]:
                            return None
                    else:
                        if raw_out[r][c] != 0:
                            return None

        return {"type": "max_column", "confidence": 0.9}

    # ---- strategy: staircase fill ----------------------------------------

    def _try_staircase_fill(self, task):
        """
        Detect pattern: input is a single row with N colored cells from the
        left; output is W//2 rows where each row adds one more colored cell.
        """
        if task is None:
            return None
        pairs = task.example_pairs
        if not pairs:
            return None

        for pair in pairs:
            g0, g1 = pair.input_grid, pair.output_grid
            if g0 is None or g1 is None:
                return None
            raw_in, raw_out = g0.raw, g1.raw
            if len(raw_in) != 1:
                return None

            row = raw_in[0]
            w = len(row)
            if w < 2:
                return None

            # Find contiguous colored cells from the left
            color = None
            count = 0
            for c in range(w):
                if row[c] != 0:
                    if color is None:
                        color = row[c]
                    elif row[c] != color:
                        return None
                    count += 1
                else:
                    break
            if color is None or count == 0:
                return None
            # Verify no other non-zero cells after the gap
            for c in range(count, w):
                if row[c] != 0:
                    return None

            num_rows = w // 2
            if len(raw_out) != num_rows:
                return None

            for r in range(num_rows):
                fill = count + r
                for c in range(w):
                    expected = color if c < fill else 0
                    if raw_out[r][c] != expected:
                        return None

        return {"type": "staircase_fill", "confidence": 1.0}

    # ---- strategy: corner quadrant fill ----------------------------------

    def _try_corner_quadrant(self, task):
        """
        Detect pattern: rectangular blocks of a fill color with 4 diagonal
        corner markers; each quadrant of the block gets its nearest corner's
        color. Corner markers are removed.
        """
        if task is None:
            return None
        pairs = task.example_pairs
        if not pairs:
            return None

        fill_color = None

        for pair in pairs:
            g0, g1 = pair.input_grid, pair.output_grid
            if g0 is None or g1 is None:
                return None
            raw_in, raw_out = g0.raw, g1.raw
            h = len(raw_in)
            w = len(raw_in[0]) if raw_in else 0
            if h != len(raw_out) or w != (len(raw_out[0]) if raw_out else 0):
                return None

            # Identify fill color: most common non-zero color
            counts = {}
            for r in range(h):
                for c in range(w):
                    v = raw_in[r][c]
                    if v != 0:
                        counts[v] = counts.get(v, 0) + 1
            if not counts:
                return None
            fc = max(counts, key=counts.get)
            if fill_color is None:
                fill_color = fc
            elif fill_color != fc:
                return None

            blocks = self._find_fill_blocks(raw_in, fill_color)
            if not blocks:
                return None

            block_cells = set()
            corner_cells = set()

            for (min_r, max_r, min_c, max_c) in blocks:
                bh = max_r - min_r + 1
                bw = max_c - min_c + 1
                if bh % 2 != 0 or bw % 2 != 0:
                    return None

                corners = [
                    (min_r - 1, min_c - 1),
                    (min_r - 1, max_c + 1),
                    (max_r + 1, min_c - 1),
                    (max_r + 1, max_c + 1),
                ]
                for cr, cc in corners:
                    if not (0 <= cr < h and 0 <= cc < w):
                        return None
                    if raw_in[cr][cc] == 0 or raw_in[cr][cc] == fill_color:
                        return None

                tl = raw_in[corners[0][0]][corners[0][1]]
                tr = raw_in[corners[1][0]][corners[1][1]]
                bl = raw_in[corners[2][0]][corners[2][1]]
                br = raw_in[corners[3][0]][corners[3][1]]
                half_h, half_w = bh // 2, bw // 2

                for r in range(min_r, max_r + 1):
                    for c in range(min_c, max_c + 1):
                        dr, dc = r - min_r, c - min_c
                        if dr < half_h:
                            expected = tl if dc < half_w else tr
                        else:
                            expected = bl if dc < half_w else br
                        if raw_out[r][c] != expected:
                            return None
                        block_cells.add((r, c))

                for cr, cc in corners:
                    if raw_out[cr][cc] != 0:
                        return None
                    corner_cells.add((cr, cc))

            for r in range(h):
                for c in range(w):
                    if (r, c) not in block_cells and (r, c) not in corner_cells:
                        if raw_out[r][c] != raw_in[r][c]:
                            return None

        return {"type": "corner_quadrant", "fill_color": fill_color, "confidence": 1.0}

    @staticmethod
    def _find_fill_blocks(raw, fill_color):
        """Find all solid rectangular blocks of fill_color via BFS."""
        h = len(raw)
        w = len(raw[0]) if raw else 0
        visited = [[False] * w for _ in range(h)]
        blocks = []
        for r in range(h):
            for c in range(w):
                if raw[r][c] == fill_color and not visited[r][c]:
                    min_r, max_r, min_c, max_c = r, r, c, c
                    queue = [(r, c)]
                    visited[r][c] = True
                    cnt = 0
                    while queue:
                        cr, cc = queue.pop(0)
                        cnt += 1
                        min_r = min(min_r, cr)
                        max_r = max(max_r, cr)
                        min_c = min(min_c, cc)
                        max_c = max(max_c, cc)
                        for dr, dc in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                            nr, nc = cr + dr, cc + dc
                            if 0 <= nr < h and 0 <= nc < w and not visited[nr][nc] and raw[nr][nc] == fill_color:
                                visited[nr][nc] = True
                                queue.append((nr, nc))
                    expected = (max_r - min_r + 1) * (max_c - min_c + 1)
                    if cnt == expected:
                        blocks.append((min_r, max_r, min_c, max_c))
        return blocks

    # ---- strategy: fill rectangular interiors by area -------------------------

    def _try_fill_rect_interior(self, task):
        """
        Detect pattern: rectangular frames of a single border color with hollow
        interiors that get filled with a color determined by interior area.
        """
        if task is None:
            return None
        pairs = task.example_pairs
        if not pairs:
            return None

        border_color = None
        area_to_color = {}

        for pair in pairs:
            g0, g1 = pair.input_grid, pair.output_grid
            if g0 is None or g1 is None:
                return None
            raw_in, raw_out = g0.raw, g1.raw
            h = len(raw_in)
            w = len(raw_in[0]) if raw_in else 0
            if h != len(raw_out) or w != (len(raw_out[0]) if raw_out else 0):
                return None

            frames = self._find_rect_frames(raw_in, 0)
            if not frames:
                return None

            for bc, min_r, max_r, min_c, max_c in frames:
                if border_color is None:
                    border_color = bc
                elif border_color != bc:
                    return None

                int_h = max_r - min_r - 1
                int_w = max_c - min_c - 1
                if int_h <= 0 or int_w <= 0:
                    return None

                area = int_h * int_w

                # All interior cells should be one fill color in output
                fill_color = None
                valid = True
                for r in range(min_r + 1, max_r):
                    for c in range(min_c + 1, max_c):
                        if raw_in[r][c] != 0:
                            valid = False
                            break
                        oc = raw_out[r][c]
                        if fill_color is None:
                            fill_color = oc
                        elif oc != fill_color:
                            valid = False
                            break
                    if not valid:
                        break
                if not valid or fill_color is None or fill_color == 0:
                    return None

                if area in area_to_color:
                    if area_to_color[area] != fill_color:
                        return None
                else:
                    area_to_color[area] = fill_color

            # Verify all non-frame cells unchanged
            frame_cells = set()
            for bc, min_r, max_r, min_c, max_c in frames:
                for r in range(min_r, max_r + 1):
                    for c in range(min_c, max_c + 1):
                        frame_cells.add((r, c))
            for r in range(h):
                for c in range(w):
                    if (r, c) not in frame_cells:
                        if raw_out[r][c] != raw_in[r][c]:
                            return None

        if not area_to_color or border_color is None:
            return None

        return {
            "type": "fill_rect_interior",
            "border_color": border_color,
            "area_to_color": {str(k): v for k, v in area_to_color.items()},
            "confidence": 1.0,
        }

    @staticmethod
    def _find_rect_frames(raw, bg=0):
        """Find hollow rectangular frames. Returns list of (border_color, min_r, max_r, min_c, max_c)."""
        h = len(raw)
        w = len(raw[0]) if raw else 0
        frames = []

        color_cells = {}
        for r in range(h):
            for c in range(w):
                v = raw[r][c]
                if v != bg:
                    color_cells.setdefault(v, []).append((r, c))

        for color, cells in color_cells.items():
            cell_set = set(cells)
            visited = set()
            for start in cells:
                if start in visited:
                    continue
                component = []
                queue = [start]
                while queue:
                    p = queue.pop(0)
                    if p in visited:
                        continue
                    visited.add(p)
                    component.append(p)
                    cr, cc = p
                    for dr, dc in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                        nb = (cr + dr, cc + dc)
                        if nb in cell_set and nb not in visited:
                            queue.append(nb)

                if len(component) < 4:
                    continue

                min_r = min(r for r, c in component)
                max_r = max(r for r, c in component)
                min_c = min(c for r, c in component)
                max_c = max(c for r, c in component)

                if max_r - min_r < 2 or max_c - min_c < 2:
                    continue

                border_cells = set()
                for r in range(min_r, max_r + 1):
                    for c in range(min_c, max_c + 1):
                        if r == min_r or r == max_r or c == min_c or c == max_c:
                            border_cells.add((r, c))

                comp_set = set(component)
                if comp_set == border_cells:
                    interior_ok = True
                    for r in range(min_r + 1, max_r):
                        for c in range(min_c + 1, max_c):
                            if raw[r][c] != bg:
                                interior_ok = False
                                break
                        if not interior_ok:
                            break
                    if interior_ok:
                        frames.append((color, min_r, max_r, min_c, max_c))

        return frames

    # ---- strategy: connect aligned diamond shapes -----------------------------

    def _try_connect_diamonds(self, task):
        """
        Detect pattern: diamond/cross shapes (4 cells of same color in +
        pattern around empty center) connected by bridges of a fill color
        when they are adjacent on the same row or column.
        """
        if task is None:
            return None
        pairs = task.example_pairs
        if not pairs:
            return None

        diamond_color = None
        bridge_color = None

        for pair in pairs:
            g0, g1 = pair.input_grid, pair.output_grid
            if g0 is None or g1 is None:
                return None
            raw_in, raw_out = g0.raw, g1.raw
            h = len(raw_in)
            w = len(raw_in[0]) if raw_in else 0
            if h != len(raw_out) or w != (len(raw_out[0]) if raw_out else 0):
                return None

            diamonds = self._find_diamonds(raw_in)
            if len(diamonds) < 2:
                return None

            dc = diamonds[0][2]
            if diamond_color is None:
                diamond_color = dc
            elif diamond_color != dc:
                return None
            if any(d[2] != dc for d in diamonds):
                return None

            # Determine bridge color from changes
            bc = None
            for r in range(h):
                for c in range(w):
                    if raw_out[r][c] != raw_in[r][c]:
                        if bc is None:
                            bc = raw_out[r][c]
                        elif raw_out[r][c] != bc:
                            return None
            if bc is None:
                return None
            if bridge_color is None:
                bridge_color = bc
            elif bridge_color != bc:
                return None

            # Build expected output with bridges (adjacent pairs only)
            expected = [row[:] for row in raw_in]
            centers = [(d[0], d[1]) for d in diamonds]

            row_groups = {}
            col_groups = {}
            for r, c in centers:
                row_groups.setdefault(r, []).append(c)
                col_groups.setdefault(c, []).append(r)

            for r, cols in row_groups.items():
                cols_sorted = sorted(cols)
                for i in range(len(cols_sorted) - 1):
                    c1, c2 = cols_sorted[i], cols_sorted[i + 1]
                    for c in range(c1 + 2, c2 - 1):
                        expected[r][c] = bridge_color

            for c, rows in col_groups.items():
                rows_sorted = sorted(rows)
                for i in range(len(rows_sorted) - 1):
                    r1, r2 = rows_sorted[i], rows_sorted[i + 1]
                    for r in range(r1 + 2, r2 - 1):
                        expected[r][c] = bridge_color

            for r in range(h):
                for c in range(w):
                    if expected[r][c] != raw_out[r][c]:
                        return None

        return {
            "type": "connect_diamonds",
            "diamond_color": diamond_color,
            "bridge_color": bridge_color,
            "confidence": 1.0,
        }

    @staticmethod
    def _find_diamonds(raw):
        """Find diamond/cross shapes: 4 cells in + pattern around empty center."""
        h = len(raw)
        w = len(raw[0]) if raw else 0
        diamonds = []
        used = set()

        for r in range(1, h - 1):
            for c in range(1, w - 1):
                if raw[r][c] == 0 and (r, c) not in used:
                    up = raw[r - 1][c]
                    down = raw[r + 1][c]
                    left = raw[r][c - 1]
                    right = raw[r][c + 1]
                    if up != 0 and up == down == left == right:
                        # Diagonals should be background
                        if (raw[r - 1][c - 1] == 0 and raw[r - 1][c + 1] == 0 and
                                raw[r + 1][c - 1] == 0 and raw[r + 1][c + 1] == 0):
                            diamonds.append((r, c, up))
                            used.update([(r - 1, c), (r + 1, c),
                                         (r, c - 1), (r, c + 1)])

        return diamonds

    # ---- strategy: stripe zone fill -------------------------------------------

    def _try_stripe_zone_fill(self, task):
        """
        Detect pattern: grid with a vertical stripe column and horizontal
        colored stripe rows. Output expands each stripe to fill its zone,
        with intersection colors at stripe positions.
        """
        if task is None:
            return None
        pairs = task.example_pairs
        if not pairs:
            return None

        bg_color = None
        col_color = None
        int_color = None

        for pair in pairs:
            g0, g1 = pair.input_grid, pair.output_grid
            if g0 is None or g1 is None:
                return None
            raw_in, raw_out = g0.raw, g1.raw
            h = len(raw_in)
            w = len(raw_in[0]) if raw_in else 0
            if h != len(raw_out) or w != (len(raw_out[0]) if raw_out else 0):
                return None

            # Find background (most common color)
            cc = {}
            for r in range(h):
                for c in range(w):
                    v = raw_in[r][c]
                    cc[v] = cc.get(v, 0) + 1
            bg = max(cc, key=cc.get)
            if bg_color is None:
                bg_color = bg
            elif bg_color != bg:
                return None

            # Find stripe column (no background cells)
            stripe_col = self._detect_stripe_col(raw_in, h, w, bg)
            if stripe_col is None:
                return None

            # Column has exactly 2 colors: column color and intersection color
            col_vals = {}
            for r in range(h):
                v = raw_in[r][stripe_col]
                col_vals[v] = col_vals.get(v, 0) + 1
            if len(col_vals) != 2:
                return None
            local_col = max(col_vals, key=col_vals.get)
            local_int = [v for v in col_vals if v != local_col][0]

            if col_color is None:
                col_color = local_col
            elif col_color != local_col:
                return None
            if int_color is None:
                int_color = local_int
            elif int_color != local_int:
                return None

            # Find stripe rows
            stripes = []
            for r in range(h):
                if raw_in[r][stripe_col] != int_color:
                    continue
                row_vals = set(raw_in[r][c] for c in range(w) if c != stripe_col)
                if len(row_vals) == 1:
                    sc = list(row_vals)[0]
                    if sc != bg:
                        stripes.append((r, sc))
            if not stripes:
                return None

            # Verify output matches expected
            expected = self._build_stripe_zone_output(
                raw_in, h, w, bg, stripe_col, col_color, int_color, stripes
            )
            for r in range(h):
                for c in range(w):
                    if expected[r][c] != raw_out[r][c]:
                        return None

        return {
            "type": "stripe_zone_fill",
            "bg_color": bg_color,
            "col_color": col_color,
            "intersection_color": int_color,
            "confidence": 1.0,
        }

    @staticmethod
    def _detect_stripe_col(raw, h, w, bg):
        """Find the column with no background cells."""
        for c in range(w):
            if all(raw[r][c] != bg for r in range(h)):
                return c
        return None

    @staticmethod
    def _build_stripe_zone_output(raw, h, w, bg, stripe_col, col_color,
                                   intersection_color, stripes):
        """Build output for stripe zone fill."""
        output = []
        for r in range(h):
            is_stripe = any(sr == r for sr, _ in stripes)
            if is_stripe:
                row = [intersection_color] * w
                row[stripe_col] = col_color
                output.append(row)
            else:
                min_dist = h + 1
                nearest_colors = set()
                for sr, sc in stripes:
                    d = abs(r - sr)
                    if d < min_dist:
                        min_dist = d
                        nearest_colors = {sc}
                    elif d == min_dist:
                        nearest_colors.add(sc)

                if len(nearest_colors) > 1:
                    row = [intersection_color] * w
                else:
                    nc = list(nearest_colors)[0]
                    row = [nc] * w
                    row[stripe_col] = intersection_color
                output.append(row)
        return output

    # ---- strategy: path with turn signals --------------------------------

    def _try_path_turn_signals(self, task):
        """
        Detect pattern: a path drawn from a unique start cell, turning at
        signal markers. One marker color = clockwise turn, another = ccw.
        """
        if task is None:
            return None
        pairs = task.example_pairs
        if not pairs:
            return None

        # Detect path color from first pair (unique color that spreads)
        g0, g1 = pairs[0].input_grid, pairs[0].output_grid
        if g0 is None or g1 is None:
            return None
        raw_in, raw_out = g0.raw, g1.raw
        h = len(raw_in)
        w = len(raw_in[0]) if raw_in else 0
        if h != len(raw_out) or w != (len(raw_out[0]) if raw_out else 0):
            return None

        input_counts = {}
        for r in range(h):
            for c in range(w):
                v = raw_in[r][c]
                if v != 0:
                    input_counts[v] = input_counts.get(v, 0) + 1

        path_color = None
        for color, count in input_counts.items():
            if count == 1:
                oc = sum(1 for r2 in range(h) for c2 in range(w) if raw_out[r2][c2] == color)
                if oc > 1:
                    if path_color is not None:
                        return None
                    path_color = color
        if path_color is None:
            return None

        # Collect all marker colors across ALL pairs
        all_marker_colors = set()
        for pair in pairs:
            gi = pair.input_grid
            if gi is None:
                return None
            ri = gi.raw
            for r in range(len(ri)):
                for c in range(len(ri[0])):
                    v = ri[r][c]
                    if v != 0 and v != path_color:
                        all_marker_colors.add(v)

        marker_colors = sorted(all_marker_colors)
        if not marker_colors or len(marker_colors) > 2:
            return None

        if len(marker_colors) == 1:
            assignments = [(marker_colors[0], -1), (-1, marker_colors[0])]
        else:
            assignments = [(marker_colors[0], marker_colors[1]),
                           (marker_colors[1], marker_colors[0])]

        for cw_color, ccw_color in assignments:
            if self._verify_path_turn(pairs, path_color, cw_color, ccw_color):
                return {
                    "type": "path_turn_signals",
                    "path_color": path_color,
                    "cw_color": cw_color,
                    "ccw_color": ccw_color,
                    "confidence": 1.0,
                }
        return None

    def _verify_path_turn(self, pairs, path_color, cw_color, ccw_color):
        for pair in pairs:
            g0, g1 = pair.input_grid, pair.output_grid
            if g0 is None or g1 is None:
                return False
            raw_in, raw_out = g0.raw, g1.raw
            h = len(raw_in)
            w = len(raw_in[0]) if raw_in else 0
            if h != len(raw_out) or w != (len(raw_out[0]) if raw_out else 0):
                return False

            start = None
            markers = {}
            for r in range(h):
                for c in range(w):
                    v = raw_in[r][c]
                    if v == path_color:
                        start = (r, c)
                    elif v != 0:
                        markers[(r, c)] = v
            if start is None:
                return False

            expected = self._simulate_turn_path(
                h, w, start, markers, path_color, cw_color, ccw_color)
            if expected is None:
                return False
            for r in range(h):
                for c in range(w):
                    if expected[r][c] != raw_out[r][c]:
                        return False
        return True

    @staticmethod
    def _simulate_turn_path(h, w, start, markers, path_color, cw_color, ccw_color):
        """Simulate path drawing from start with turn signals."""
        DIRS = [(0, 1), (1, 0), (0, -1), (-1, 0)]  # R, D, L, U
        grid = [[0] * w for _ in range(h)]
        for (r, c), v in markers.items():
            grid[r][c] = v

        r, c = start
        grid[r][c] = path_color
        dir_idx = 0  # start RIGHT
        remaining = dict(markers)

        for _ in range(len(markers) + 1):
            dr, dc = DIRS[dir_idx]
            target = None
            nr, nc = r + dr, c + dc
            while 0 <= nr < h and 0 <= nc < w:
                if (nr, nc) in remaining:
                    target = (nr, nc)
                    break
                nr += dr
                nc += dc

            if target is not None:
                tr, tc = target
                nr, nc = r + dr, c + dc
                while (nr, nc) != (tr, tc):
                    grid[nr][nc] = path_color
                    nr += dr
                    nc += dc
                r, c = tr - dr, tc - dc
                mt = remaining.pop((tr, tc))
                if mt == cw_color:
                    dir_idx = (dir_idx + 1) % 4
                elif mt == ccw_color:
                    dir_idx = (dir_idx - 1) % 4
                else:
                    return None
            else:
                nr, nc = r + dr, c + dc
                while 0 <= nr < h and 0 <= nc < w:
                    grid[nr][nc] = path_color
                    nr += dr
                    nc += dc
                break
        return grid

    # ---- strategy: arrow slide with mirror across divider ----------------

    def _try_arrow_slide_mirror(self, task):
        """
        Detect pattern: grid split by a uniform divider row. Bottom half has
        colored dots with arrow chains; dots slide to end of chain. Same
        displacement (mirrored vertically) applied to top half dots.
        """
        if task is None:
            return None
        pairs = task.example_pairs
        if not pairs:
            return None

        divider_color = None
        bg_color = None
        dot_top_color = None
        dot_bot_color = None
        arrow_color = None

        for pair in pairs:
            g0, g1 = pair.input_grid, pair.output_grid
            if g0 is None or g1 is None:
                return None
            raw_in, raw_out = g0.raw, g1.raw
            h = len(raw_in)
            w = len(raw_in[0]) if raw_in else 0
            if h != len(raw_out) or w != (len(raw_out[0]) if raw_out else 0):
                return None

            bg_counts = {}
            for r in range(h):
                for c in range(w):
                    bg_counts[raw_in[r][c]] = bg_counts.get(raw_in[r][c], 0) + 1
            bg = max(bg_counts, key=bg_counts.get)
            if bg_color is None:
                bg_color = bg
            elif bg_color != bg:
                return None

            div_row = None
            for r in range(h):
                if len(set(raw_in[r])) == 1 and raw_in[r][0] != bg:
                    if div_row is not None:
                        return None
                    div_row = r
            if div_row is None:
                return None

            dc = raw_in[div_row][0]
            if divider_color is None:
                divider_color = dc
            elif divider_color != dc:
                return None

            top_colors = set()
            for r in range(div_row):
                for c in range(w):
                    v = raw_in[r][c]
                    if v != bg:
                        top_colors.add(v)
            bot_colors = set()
            for r in range(div_row + 1, h):
                for c in range(w):
                    v = raw_in[r][c]
                    if v != bg:
                        bot_colors.add(v)
            if len(top_colors) != 1 or len(bot_colors) != 2:
                return None

            tc = list(top_colors)[0]
            if dot_top_color is None:
                dot_top_color = tc
            elif dot_top_color != tc:
                return None

            bc_list = sorted(bot_colors)
            local_dot = None
            local_arrow = None
            for bc in bc_list:
                present = any(raw_out[r][c] == bc
                              for r in range(div_row + 1, h) for c in range(w))
                if present:
                    if local_dot is not None:
                        return None
                    local_dot = bc
                else:
                    local_arrow = bc
            if local_dot is None or local_arrow is None:
                return None

            if dot_bot_color is None:
                dot_bot_color = local_dot
            elif dot_bot_color != local_dot:
                return None
            if arrow_color is None:
                arrow_color = local_arrow
            elif arrow_color != local_arrow:
                return None

            expected = self._simulate_arrow_slide(
                raw_in, h, w, div_row, bg, dot_top_color, dot_bot_color, arrow_color)
            if expected is None:
                return None
            for r in range(h):
                for c in range(w):
                    if expected[r][c] != raw_out[r][c]:
                        return None

        return {
            "type": "arrow_slide_mirror",
            "divider_color": divider_color,
            "bg_color": bg_color,
            "dot_top_color": dot_top_color,
            "dot_bot_color": dot_bot_color,
            "arrow_color": arrow_color,
            "confidence": 1.0,
        }

    @staticmethod
    def _walk_arrow_chain(start_r, start_c, arrow_cells):
        """Walk from start along adjacent arrow cells to find chain end."""
        current = (start_r, start_c)
        prev = None
        while True:
            cr, cc = current
            found = False
            for dr, dc in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                nr, nc = cr + dr, cc + dc
                if (nr, nc) in arrow_cells and (nr, nc) != prev:
                    prev = current
                    current = (nr, nc)
                    found = True
                    break
            if not found:
                break
        return current

    @staticmethod
    def _simulate_arrow_slide(raw, h, w, div_row, bg, dot_top, dot_bot, arrow_color):
        """Simulate arrow chain sliding and mirroring."""
        output = [[bg] * w for _ in range(h)]
        for c in range(w):
            output[div_row][c] = raw[div_row][c]

        arrow_cells = set()
        bot_dots = []
        for r in range(div_row + 1, h):
            for c in range(w):
                v = raw[r][c]
                if v == dot_bot:
                    bot_dots.append((r, c))
                elif v == arrow_color:
                    arrow_cells.add((r, c))

        displacements = []
        for dr, dc in bot_dots:
            end = GeneralizeOperator._walk_arrow_chain(dr, dc, arrow_cells)
            delta = (end[0] - dr, end[1] - dc)
            displacements.append(((dr, dc), delta))

        for (dr, dc), (d_r, d_c) in displacements:
            nr, nc = dr + d_r, dc + d_c
            if 0 <= nr < h and 0 <= nc < w:
                output[nr][nc] = dot_bot

        for (dr, dc), (d_r, d_c) in displacements:
            mirror_r = 2 * div_row - dr
            new_r = mirror_r + (-d_r)
            new_c = dc + d_c
            if 0 <= new_r < h and 0 <= new_c < w:
                output[new_r][new_c] = dot_top

        return output

    # ---- strategy: quadrant shape swap -----------------------------------

    def _try_quadrant_shape_swap(self, task):
        """
        Detect pattern: grid divided into rectangular regions by separator
        rows/columns. Horizontally paired regions swap their patterns,
        with pattern color becoming the partner's background color.
        """
        if task is None:
            return None
        pairs = task.example_pairs
        if not pairs:
            return None

        sep_color = None

        for pair in pairs:
            g0, g1 = pair.input_grid, pair.output_grid
            if g0 is None or g1 is None:
                return None
            raw_in, raw_out = g0.raw, g1.raw
            h = len(raw_in)
            w = len(raw_in[0]) if raw_in else 0
            if h != len(raw_out) or w != (len(raw_out[0]) if raw_out else 0):
                return None

            result = self._parse_grid_regions(raw_in, h, w)
            if result is None:
                return None
            sc, row_ranges, col_ranges, regions = result

            if sep_color is None:
                sep_color = sc
            elif sep_color != sc:
                return None

            if len(col_ranges) % 2 != 0:
                return None

            for ri in range(len(row_ranges)):
                for ci in range(0, len(col_ranges), 2):
                    left = regions.get((ri, ci))
                    right = regions.get((ri, ci + 1))
                    if left is None or right is None:
                        return None

                    l_bg, l_pat, l_pc, l_bounds = left
                    r_bg, r_pat, r_pc, r_bounds = right

                    # Dimensions must match for pattern swap
                    if l_bounds[2] != r_bounds[2] or l_bounds[3] != r_bounds[3]:
                        return None

                    # Left output: right's pattern with color=r_bg, rest=l_bg
                    lr, lc, lh, lw = l_bounds
                    for r in range(lr, lr + lh):
                        for c in range(lc, lc + lw):
                            rel = (r - lr, c - lc)
                            expected = r_bg if rel in r_pat else l_bg
                            if raw_out[r][c] != expected:
                                return None

                    # Right output: left's pattern with color=l_bg, rest=r_bg
                    rr, rc, rh, rw = r_bounds
                    for r in range(rr, rr + rh):
                        for c in range(rc, rc + rw):
                            rel = (r - rr, c - rc)
                            expected = l_bg if rel in l_pat else r_bg
                            if raw_out[r][c] != expected:
                                return None

            # Separator cells unchanged
            for r in range(h):
                for c in range(w):
                    if raw_in[r][c] == sc and raw_out[r][c] != sc:
                        return None

        return {"type": "quadrant_shape_swap", "sep_color": sep_color, "confidence": 1.0}

    @staticmethod
    def _parse_grid_regions(raw, h, w):
        """Parse grid into rectangular regions separated by uniform rows/cols."""
        # Find separator color: forms both complete rows and complete columns
        row_sep = set()
        for r in range(h):
            vals = set(raw[r])
            if len(vals) == 1:
                row_sep.add(raw[r][0])

        col_sep = set()
        for c in range(w):
            vals = set(raw[r][c] for r in range(h))
            if len(vals) == 1:
                col_sep.add(raw[0][c])

        candidates = row_sep & col_sep
        if not candidates:
            return None
        sep_color = min(candidates)

        # Find contiguous non-separator row ranges
        row_ranges = []
        start = None
        for r in range(h):
            is_sep = all(raw[r][c] == sep_color for c in range(w))
            if not is_sep:
                if start is None:
                    start = r
            else:
                if start is not None:
                    row_ranges.append((start, r))
                    start = None
        if start is not None:
            row_ranges.append((start, h))

        col_ranges = []
        start = None
        for c in range(w):
            is_sep = all(raw[r][c] == sep_color for r in range(h))
            if not is_sep:
                if start is None:
                    start = c
            else:
                if start is not None:
                    col_ranges.append((start, c))
                    start = None
        if start is not None:
            col_ranges.append((start, w))

        if not row_ranges or not col_ranges:
            return None

        regions = {}
        for ri, (r_start, r_end) in enumerate(row_ranges):
            for ci, (c_start, c_end) in enumerate(col_ranges):
                counts = {}
                for r in range(r_start, r_end):
                    for c in range(c_start, c_end):
                        v = raw[r][c]
                        if v != sep_color:
                            counts[v] = counts.get(v, 0) + 1
                if not counts:
                    return None
                bg = max(counts, key=counts.get)

                pattern = set()
                pattern_color = None
                for r in range(r_start, r_end):
                    for c in range(c_start, c_end):
                        v = raw[r][c]
                        if v != bg and v != sep_color:
                            pattern.add((r - r_start, c - c_start))
                            if pattern_color is None:
                                pattern_color = v
                            elif v != pattern_color:
                                return None

                rh = r_end - r_start
                rw = c_end - c_start
                regions[(ri, ci)] = (bg, pattern, pattern_color,
                                     (r_start, c_start, rh, rw))

        return (sep_color, row_ranges, col_ranges, regions)


    # ---- strategy: cross border projection ---------------------------------

    def _try_cross_border_project(self, task):
        """
        Detect pattern: cross/arrow shapes made of structural color with a
        unique center marker. Each cross has a 'missing arm' direction.
        The center color projects every 2 cells toward the grid edge in that
        direction, then fills the entire border row/column. Corners where
        two border fills meet become 0.
        """
        if task is None:
            return None
        pairs = task.example_pairs
        if not pairs:
            return None

        for pair in pairs:
            g0, g1 = pair.input_grid, pair.output_grid
            if g0 is None or g1 is None:
                return None
            raw_in, raw_out = g0.raw, g1.raw
            h = len(raw_in)
            w = len(raw_in[0]) if raw_in else 0
            if h != len(raw_out) or w != (len(raw_out[0]) if raw_out else 0):
                return None

            bg = self._most_common_color(raw_in, h, w)
            crosses = self._find_arrow_crosses(raw_in, h, w, bg)
            if not crosses:
                return None

            predicted = self._build_cross_border_output(raw_in, h, w, crosses)
            for r in range(h):
                for c in range(w):
                    if predicted[r][c] != raw_out[r][c]:
                        return None

        return {"type": "cross_border_project", "confidence": 1.0}

    @staticmethod
    def _most_common_color(raw, h, w):
        counts = {}
        for r in range(h):
            for c in range(w):
                v = raw[r][c]
                counts[v] = counts.get(v, 0) + 1
        return max(counts, key=counts.get)

    @staticmethod
    def _find_arrow_crosses(raw, h, w, bg):
        """Find cross/arrow shapes: structural color body + single center marker."""
        non_bg = set()
        for r in range(h):
            for c in range(w):
                if raw[r][c] != bg:
                    non_bg.add((r, c))

        visited = set()
        components = []
        for pos in non_bg:
            if pos in visited:
                continue
            comp = []
            queue = [pos]
            while queue:
                p = queue.pop(0)
                if p in visited:
                    continue
                visited.add(p)
                comp.append(p)
                pr, pc = p
                for dr, dc in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                    nb = (pr + dr, pc + dc)
                    if nb in non_bg and nb not in visited:
                        queue.append(nb)
            components.append(comp)

        crosses = []
        for comp in components:
            color_counts = {}
            for r, c in comp:
                v = raw[r][c]
                color_counts[v] = color_counts.get(v, 0) + 1
            if len(color_counts) < 2:
                continue
            structural = max(color_counts, key=color_counts.get)

            markers = [(r, c, raw[r][c]) for r, c in comp if raw[r][c] != structural]
            if len(markers) != 1:
                continue

            cr, cc, center_color = markers[0]
            comp_set = set(comp)
            arms = {}
            for direction, (dr, dc) in [("up", (-1, 0)), ("down", (1, 0)),
                                         ("left", (0, -1)), ("right", (0, 1))]:
                length = 0
                nr, nc = cr + dr, cc + dc
                while (nr, nc) in comp_set and raw[nr][nc] == structural:
                    length += 1
                    nr += dr
                    nc += dc
                arms[direction] = length

            min_arm = min(arms.values())
            missing_dirs = [d for d, l in arms.items() if l == min_arm]
            if len(missing_dirs) != 1:
                continue

            crosses.append({
                "center": (cr, cc),
                "center_color": center_color,
                "missing_dir": missing_dirs[0],
            })

        return crosses

    @staticmethod
    def _build_cross_border_output(raw_in, h, w, crosses):
        """Build output by projecting center colors to borders."""
        output = [row[:] for row in raw_in]
        dir_vec = {"up": (-1, 0), "down": (1, 0), "left": (0, -1), "right": (0, 1)}
        border_map = {"up": ("row", 0), "down": ("row", h - 1),
                      "left": ("col", 0), "right": ("col", w - 1)}

        border_fills = {}
        for cross in crosses:
            cr, cc = cross["center"]
            color = cross["center_color"]
            direction = cross["missing_dir"]
            dr, dc = dir_vec[direction]

            # Project dots every 2 cells from center toward border
            nr, nc = cr + 2 * dr, cc + 2 * dc
            while 0 <= nr < h and 0 <= nc < w:
                output[nr][nc] = color
                nr += 2 * dr
                nc += 2 * dc

            kind, idx = border_map[direction]
            border_fills[(kind, idx)] = color

        # Fill border rows/columns
        for (kind, idx), color in border_fills.items():
            if kind == "row":
                for c in range(w):
                    output[idx][c] = color
            else:
                for r in range(h):
                    output[r][idx] = color

        # Corners where two border fills meet -> 0
        border_rows = {idx for (kind, idx), _ in border_fills.items() if kind == "row"}
        border_cols = {idx for (kind, idx), _ in border_fills.items() if kind == "col"}
        for r in border_rows:
            for c in border_cols:
                output[r][c] = 0

        return output

    # ---- strategy: block slide split ----------------------------------------

    def _try_block_slide_split(self, task):
        """
        Detect pattern: three single-colored blocks in a line. The middle
        block slides through one outer block (which splits in the
        perpendicular axis) all the way to the grid boundary. The other
        outer block stays unchanged.
        """
        if task is None:
            return None
        pairs = task.example_pairs
        if not pairs:
            return None

        for pair in pairs:
            g0, g1 = pair.input_grid, pair.output_grid
            if g0 is None or g1 is None:
                return None
            raw_in, raw_out = g0.raw, g1.raw
            h = len(raw_in)
            w = len(raw_in[0]) if raw_in else 0
            if h != len(raw_out) or w != (len(raw_out[0]) if raw_out else 0):
                return None

            bg = self._most_common_color(raw_in, h, w)
            result = self._analyze_three_blocks(raw_in, h, w, bg)
            if result is None:
                return None

            blocks, axis, middle_idx, split_idx, stay_idx = result
            predicted = self._build_block_slide_output(
                h, w, bg, blocks, axis, middle_idx, split_idx, stay_idx)
            for r in range(h):
                for c in range(w):
                    if predicted[r][c] != raw_out[r][c]:
                        return None

        return {"type": "block_slide_split", "confidence": 1.0}

    @staticmethod
    def _analyze_three_blocks(raw, h, w, bg):
        """Find 3 single-colored blocks (grouped by color) and determine roles."""
        # Group non-bg cells by color (blocks may be touching)
        color_cells = {}
        for r in range(h):
            for c in range(w):
                v = raw[r][c]
                if v != bg:
                    color_cells.setdefault(v, []).append((r, c))

        if len(color_cells) != 3:
            return None

        blocks = []
        for color, cells in color_cells.items():
            rows = [r for r, c in cells]
            cols = [c for r, c in cells]
            blocks.append({
                "cells": set(cells),
                "color": color,
                "bbox": (min(rows), min(cols),
                         max(rows) - min(rows) + 1,
                         max(cols) - min(cols) + 1),
                "center_r": sum(rows) / len(rows),
                "center_c": sum(cols) / len(cols),
            })

        row_spread = max(b["center_r"] for b in blocks) - min(b["center_r"] for b in blocks)
        col_spread = max(b["center_c"] for b in blocks) - min(b["center_c"] for b in blocks)

        if row_spread >= col_spread:
            axis = "vertical"
            sorted_idx = sorted(range(3), key=lambda i: blocks[i]["center_r"])
        else:
            axis = "horizontal"
            sorted_idx = sorted(range(3), key=lambda i: blocks[i]["center_c"])

        middle_idx = sorted_idx[1]
        outer_indices = [sorted_idx[0], sorted_idx[2]]
        middle = blocks[middle_idx]

        mid_r, mid_c, mid_h, mid_w = middle["bbox"]
        if len(middle["cells"]) != mid_h * mid_w:
            return None

        split_candidates = []
        stay_candidates = []
        for oi in outer_indices:
            outer = blocks[oi]
            _, _, bh, bw = outer["bbox"]
            is_rect = (bh * bw == len(outer["cells"]))
            if axis == "vertical":
                can_split = is_rect and bw > mid_w
            else:
                can_split = is_rect and bh > mid_h
            if can_split:
                split_candidates.append(oi)
            else:
                stay_candidates.append(oi)

        if len(split_candidates) != 1 or len(stay_candidates) != 1:
            return None

        return blocks, axis, middle_idx, split_candidates[0], stay_candidates[0]

    @staticmethod
    def _build_block_slide_output(h, w, bg, blocks, axis, middle_idx, split_idx, stay_idx):
        """Build output: stay block unchanged, split block splits, middle slides to edge."""
        output = [[bg] * w for _ in range(h)]
        middle = blocks[middle_idx]
        split_b = blocks[split_idx]
        stay_b = blocks[stay_idx]

        # 1. Place stay block unchanged
        for r, c in stay_b["cells"]:
            output[r][c] = stay_b["color"]

        # 2. Place split block halves (shifted outward in perpendicular axis)
        sb_r, sb_c, sb_h, sb_w = split_b["bbox"]
        mid_r, mid_c, mid_h, mid_w = middle["bbox"]

        if axis == "vertical":
            shift = mid_w // 2
            col_center = sb_c + sb_w // 2
            for r, c in split_b["cells"]:
                if c < col_center:
                    nc = c - shift
                else:
                    nc = c + shift
                if 0 <= nc < w:
                    output[r][nc] = split_b["color"]
        else:
            shift = mid_h // 2
            row_center = sb_r + sb_h // 2
            for r, c in split_b["cells"]:
                if r < row_center:
                    nr = r - shift
                else:
                    nr = r + shift
                if 0 <= nr < h:
                    output[nr][c] = split_b["color"]

        # 3. Place middle block at grid boundary (toward split block)
        if axis == "vertical":
            if split_b["center_r"] < middle["center_r"]:
                new_min_r = 0
            else:
                new_min_r = h - mid_h
            for r, c in middle["cells"]:
                nr = r - mid_r + new_min_r
                if 0 <= nr < h:
                    output[nr][c] = middle["color"]
        else:
            if split_b["center_c"] < middle["center_c"]:
                new_min_c = 0
            else:
                new_min_c = w - mid_w
            for r, c in middle["cells"]:
                nc = c - mid_c + new_min_c
                if 0 <= nc < w:
                    output[r][nc] = middle["color"]

        return output

    # ---- strategy: grid zigzag ---------------------------------------------

    def _try_grid_zigzag(self, task):
        """
        Detect pattern: a rectangular grid shape (single non-bg color) whose
        rows oscillate horizontally with a zigzag pattern. From the bottom
        row upward, offsets cycle: 0, -1, 0, +1, 0, -1, 0, +1, ...
        """
        if task is None:
            return None
        pairs = task.example_pairs
        if not pairs:
            return None

        for pair in pairs:
            g0, g1 = pair.input_grid, pair.output_grid
            if g0 is None or g1 is None:
                return None
            raw_in, raw_out = g0.raw, g1.raw
            h = len(raw_in)
            w = len(raw_in[0]) if raw_in else 0
            if h != len(raw_out) or w != (len(raw_out[0]) if raw_out else 0):
                return None

            bg = self._most_common_color(raw_in, h, w)
            non_bg_colors = set()
            grid_rows = set()
            for r in range(h):
                for c in range(w):
                    if raw_in[r][c] != bg:
                        non_bg_colors.add(raw_in[r][c])
                        grid_rows.add(r)
            if len(non_bg_colors) != 1 or not grid_rows:
                return None

            min_r = min(grid_rows)
            max_r = max(grid_rows)
            if max_r - min_r < 2:
                return None

            shifts = [0, -1, 0, 1]
            predicted = [row[:] for row in raw_in]
            for i, r in enumerate(range(max_r, min_r - 1, -1)):
                s = shifts[i % 4]
                if s == 0:
                    continue
                new_row = [bg] * w
                for c in range(w):
                    src = c - s
                    if 0 <= src < w:
                        new_row[c] = raw_in[r][src]
                predicted[r] = new_row

            for r in range(h):
                for c in range(w):
                    if predicted[r][c] != raw_out[r][c]:
                        return None

        return {"type": "grid_zigzag", "confidence": 1.0}

    # ---- strategy: gravity fall --------------------------------------------

    def _try_gravity_fall(self, task):
        """
        Detect pattern: objects of one color fall toward a border/wall
        of another color as rigid bodies, stopping with a 1-cell gap.
        Colors may differ per example — brute-force all assignments.
        Category: gravity/physics puzzles with border walls.
        """
        if task is None:
            return None
        pairs = task.example_pairs
        if not pairs:
            return None

        from collections import Counter
        for pair in pairs:
            raw_in = pair.input_grid.raw
            raw_out = pair.output_grid.raw
            H = len(raw_in)
            W = len(raw_in[0]) if raw_in else 0
            if H != len(raw_out) or W != (len(raw_out[0]) if raw_out else 0):
                return None

            color_counts = Counter()
            for r in range(H):
                for c in range(W):
                    color_counts[raw_in[r][c]] += 1
            if len(color_counts) < 3:
                return None

            # Brute-force: try all (bg, border) assignments
            colors = list(color_counts.keys())
            found = False
            for bg in colors:
                for border in colors:
                    if border == bg:
                        continue
                    obj_colors = set(colors) - {bg, border}
                    if not obj_colors:
                        continue
                    predicted = self._compute_gravity_fall(
                        raw_in, bg, border, obj_colors)
                    if predicted == raw_out:
                        found = True
                        break
                if found:
                    break
            if not found:
                return None

        return {"type": "gravity_fall", "confidence": 0.9}

    @staticmethod
    def _identify_gravity_colors(raw):
        """Identify bg, border, obj from input using edge-sides heuristic."""
        from collections import Counter
        H = len(raw)
        W = len(raw[0]) if raw else 0
        color_counts = Counter()
        for r in range(H):
            for c in range(W):
                color_counts[raw[r][c]] += 1
        if len(color_counts) < 3:
            return None

        bg = color_counts.most_common(1)[0][0]
        remaining = set(color_counts.keys()) - {bg}

        def edge_sides(color):
            sides = set()
            for c in range(W):
                if raw[0][c] == color:
                    sides.add('top')
                if raw[H - 1][c] == color:
                    sides.add('bottom')
            for r in range(H):
                if raw[r][0] == color:
                    sides.add('left')
                if raw[r][W - 1] == color:
                    sides.add('right')
            return len(sides)

        border = max(remaining, key=lambda c: (edge_sides(c), color_counts[c]))
        obj_colors = remaining - {border}
        if not obj_colors or edge_sides(border) == 0:
            return None
        return bg, border, obj_colors

    @staticmethod
    def _compute_gravity_fall(raw, bg, border_color, obj_colors):
        """Apply gravity to all object components, shifting them toward border."""
        H = len(raw)
        W = len(raw[0]) if raw else 0

        # Find all object cells
        obj_cells = set()
        for r in range(H):
            for c in range(W):
                if raw[r][c] in obj_colors:
                    obj_cells.add((r, c))
        if not obj_cells:
            return [row[:] for row in raw]

        # Connected components
        visited = set()
        components = []
        for cell in sorted(obj_cells):
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
                for dr, dc in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                    nb = (p[0] + dr, p[1] + dc)
                    if nb in obj_cells and nb not in visited:
                        queue.append(nb)
            components.append(comp)

        # Sort: bottom-most component first (settles first)
        components.sort(key=lambda comp: -max(r for r, c in comp))

        # Build output with bg + border only
        output = [[bg] * W for _ in range(H)]
        border_cells = set()
        for r in range(H):
            for c in range(W):
                if raw[r][c] == border_color:
                    output[r][c] = border_color
                    border_cells.add((r, c))
        placed_cells = set()

        for comp in components:
            cols_in_comp = set(c for _, c in comp)
            min_shift = H  # large default

            for col in cols_in_comp:
                bottom_row = max(r for r, c in comp if c == col)
                # Scan down to find first obstacle (border or placed object)
                obstacle_row = H
                is_border = True
                for scan_r in range(bottom_row + 1, H):
                    if (scan_r, col) in border_cells:
                        obstacle_row = scan_r
                        is_border = True
                        break
                    if (scan_r, col) in placed_cells:
                        obstacle_row = scan_r
                        is_border = False
                        break
                # 1-cell gap before border, 0-cell gap before other objects
                gap = 2 if is_border else 1
                shift = obstacle_row - bottom_row - gap
                if shift < 0:
                    shift = 0
                min_shift = min(min_shift, shift)

            for r, c in comp:
                new_r = r + min_shift
                if 0 <= new_r < H:
                    output[new_r][c] = raw[r][c]
                    placed_cells.add((new_r, c))

        return output

    # ---- strategy: count diamond -------------------------------------------

    def _try_count_diamond(self, task):
        """
        Detect pattern: scattered dots of exactly 2 non-bg colors.
        Count each color -> rectangle dims (w=max, h=min) at bottom-left.
        Rectangle filled with color 2, V/diamond outline in color 4.
        Output grid may be larger than input (max dims across examples).
        Category: counting-to-geometry puzzles.
        """
        if task is None:
            return None
        pairs = task.example_pairs
        if not pairs:
            return None

        from collections import Counter

        # Output dim = max across all training inputs
        max_dim = 0
        for pair in pairs:
            ri = pair.input_grid.raw
            max_dim = max(max_dim, len(ri), len(ri[0]) if ri else 0)

        for pair in pairs:
            raw_in = pair.input_grid.raw
            raw_out = pair.output_grid.raw
            H_in = len(raw_in)
            W_in = len(raw_in[0]) if raw_in else 0
            H_out = len(raw_out)
            W_out = len(raw_out[0]) if raw_out else 0

            if H_out != max_dim or W_out != max_dim:
                return None

            color_counts = Counter()
            for r in range(H_in):
                for c in range(W_in):
                    color_counts[raw_in[r][c]] += 1

            bg = color_counts.most_common(1)[0][0]
            non_bg = {c: cnt for c, cnt in color_counts.items() if c != bg}
            if len(non_bg) != 2:
                return None

            counts = sorted(non_bg.values())
            h_rect = counts[0]
            w_rect = counts[1]

            expected = self._build_count_diamond(max_dim, max_dim, bg, w_rect, h_rect)
            if expected != raw_out:
                return None

        return {"type": "count_diamond", "output_dim": max_dim, "confidence": 0.95}

    @staticmethod
    def _build_count_diamond(H, W, bg, w, h):
        """Build output grid with V/diamond pattern at bottom-left."""
        if h > H or w > W:
            return None
        output = [[bg] * W for _ in range(H)]
        max_d = (w - 1) // 2

        # Distance sequence (bottom-up): starts at max_d, decreases to 0,
        # then bounces back (even width: d=0 repeats once).
        distances = []
        for i in range(h):
            if i <= max_d:
                d = max_d - i
            else:
                extra = i - max_d
                if w % 2 == 0:
                    d = extra - 1
                else:
                    d = extra
            distances.append(d)

        for i, dist in enumerate(distances):
            row = H - 1 - i
            # Fill row with color 2
            for c in range(w):
                output[row][c] = 2
            # Place 4s on the diagonals
            if w % 2 == 0:
                cl = w // 2 - 1 - dist
                cr = w // 2 + dist
                if 0 <= cl < w:
                    output[row][cl] = 4
                if 0 <= cr < w:
                    output[row][cr] = 4
            else:
                center = w // 2
                if dist == 0:
                    output[row][center] = 4
                else:
                    if 0 <= center - dist < w:
                        output[row][center - dist] = 4
                    if 0 <= center + dist < w:
                        output[row][center + dist] = 4

        return output

    # ---- strategy: anchor template placement --------------------------------

    def _try_anchor_template_place(self, task):
        """
        Detect pattern: input has template shapes (connected multi-color objects)
        and scattered single pixels (anchors). Output removes templates and
        reconstructs them at scattered anchor positions with rotation/reflection.
        Category: template+anchor reassembly tasks.
        """
        if task is None:
            return None
        pairs = task.example_pairs
        if not pairs:
            return None

        for pair in pairs:
            g0, g1 = pair.input_grid, pair.output_grid
            if g0 is None or g1 is None:
                return None
            if len(g0.raw) != len(g1.raw) or len(g0.raw[0]) != len(g1.raw[0]):
                return None
            result = _anchor_template_predict(g0.raw)
            if result is None or result != g1.raw:
                return None

        return {"type": "anchor_template_place", "confidence": 1.0}

    # ---- strategy: block count gravity --------------------------------------

    def _try_block_count_gravity(self, task):
        """
        Detect pattern: large grid with 3x3 hollow square blocks arranged in
        rows/cols, a divider line of 1s on one edge, two spatial zones.
        Output is a small grid where each row/column shows zone block counts
        packed toward the divider.
        Category: block grid summary with gravity packing.
        """
        if task is None:
            return None
        pairs = task.example_pairs
        if not pairs:
            return None

        for pair in pairs:
            g0, g1 = pair.input_grid, pair.output_grid
            if g0 is None or g1 is None:
                return None
            result = _block_gravity_predict(g0.raw)
            if result is None or result != g1.raw:
                return None

        return {"type": "block_count_gravity", "confidence": 1.0}

    # ---- strategy: cross/diagonal decorator around isolated pixels ------

    def _try_cross_decorator(self, task):
        """
        Detect: isolated single-color pixels on a background grid.
        Some colors get cross (+) decorations, others get diagonal (×)
        decorations with a specific color.  Remaining colors stay unchanged.
        Category: marker decoration.
        """
        if task is None:
            return None
        pairs = task.example_pairs
        if not pairs:
            return None

        CROSS = [(-1, 0), (1, 0), (0, -1), (0, 1)]
        DIAG = [(-1, -1), (-1, 1), (1, -1), (1, 1)]

        # Learn decoration rules from first pair
        g0, g1 = pairs[0].input_grid, pairs[0].output_grid
        if g0 is None or g1 is None:
            return None
        raw0, raw1 = g0.raw, g1.raw
        h, w = len(raw0), len(raw0[0])
        if len(raw1) != h or len(raw1[0]) != w:
            return None

        # All non-zero cells must be isolated single pixels
        pixels = []
        for r in range(h):
            for c in range(w):
                if raw0[r][c] != 0:
                    pixels.append((r, c, raw0[r][c]))
        if not pixels:
            return None

        # For each color, determine decoration type from first occurrence
        deco_map = {}
        for r, c, col in pixels:
            if col in deco_map:
                continue
            found = False
            for pat_name, offsets in [("cross", CROSS), ("diagonal", DIAG)]:
                deco_color = None
                ok = True
                checked = 0
                for dr, dc in offsets:
                    nr, nc = r + dr, c + dc
                    if 0 <= nr < h and 0 <= nc < w and raw0[nr][nc] == 0:
                        val = raw1[nr][nc]
                        if val == 0:
                            ok = False
                            break
                        if deco_color is None:
                            deco_color = val
                        elif val != deco_color:
                            ok = False
                            break
                        checked += 1
                if ok and deco_color is not None and checked > 0:
                    deco_map[col] = (pat_name, deco_color)
                    found = True
                    break
            if not found:
                deco_map[col] = ("none", 0)

        if not any(d[0] != "none" for d in deco_map.values()):
            return None

        # Validate: build predicted output and compare for ALL pairs
        for pair in pairs:
            g0, g1 = pair.input_grid, pair.output_grid
            if g0 is None or g1 is None:
                return None
            ri, ro = g0.raw, g1.raw
            ph, pw = len(ri), len(ri[0])
            if len(ro) != ph or len(ro[0]) != pw:
                return None
            pred = [row[:] for row in ri]
            for r2 in range(ph):
                for c2 in range(pw):
                    col = ri[r2][c2]
                    if col != 0 and col in deco_map:
                        pat, dcol = deco_map[col]
                        if pat == "cross":
                            offsets = CROSS
                        elif pat == "diagonal":
                            offsets = DIAG
                        else:
                            continue
                        for dr, dc in offsets:
                            nr, nc = r2 + dr, c2 + dc
                            if 0 <= nr < ph and 0 <= nc < pw and pred[nr][nc] == 0:
                                pred[nr][nc] = dcol
            if pred != ro:
                return None

        return {
            "type": "cross_decorator",
            "deco_map": {str(k): list(v) for k, v in deco_map.items()},
            "confidence": 1.0,
        }

    # ---- strategy: 2x2 point-symmetric tiling ----------------------------

    def _try_tile_mirror(self, task):
        """
        Detect: output dimensions are exactly 2x input dimensions.
        Output is a 2x2 tiling with point symmetry:
          top-left = 180° rotation, top-right = vertical flip,
          bottom-left = horizontal flip, bottom-right = original.
        Category: symmetry tiling / grid doubling.
        """
        if task is None:
            return None
        pairs = task.example_pairs
        if not pairs:
            return None

        for pair in pairs:
            g0, g1 = pair.input_grid, pair.output_grid
            if g0 is None or g1 is None:
                return None
            ri, ro = g0.raw, g1.raw
            h, w = len(ri), len(ri[0])
            oh, ow = len(ro), len(ro[0])
            if oh != 2 * h or ow != 2 * w:
                return None

            rot180 = [row[::-1] for row in ri[::-1]]
            vflip = ri[::-1]
            hflip = [row[::-1] for row in ri]

            for r in range(h):
                for c in range(w):
                    if ro[r][c] != rot180[r][c]:
                        return None
                    if ro[r][w + c] != vflip[r][c]:
                        return None
                    if ro[h + r][c] != hflip[r][c]:
                        return None
                    if ro[h + r][w + c] != ri[r][c]:
                        return None

        return {"type": "tile_mirror", "confidence": 1.0}

    # ---- strategy: count marker color inside frame -----------------------

    def _try_count_inside_frame(self, task):
        """
        Detect: input has a rectangular frame of 1s.  A marker color (non-0,
        non-1) is scattered inside and outside the frame.  Output is a fixed
        3x3 grid with the marker color filled left-to-right, top-to-bottom,
        count = number of marker cells INSIDE the frame interior.
        Category: count-and-encode / frame extraction.
        """
        if task is None:
            return None
        pairs = task.example_pairs
        if not pairs:
            return None

        for pair in pairs:
            g0, g1 = pair.input_grid, pair.output_grid
            if g0 is None or g1 is None:
                return None
            ri, ro = g0.raw, g1.raw
            oh, ow = len(ro), len(ro[0])
            if oh != 3 or ow != 3:
                return None

            h, w = len(ri), len(ri[0])
            # Find rectangular frame of 1s
            frame = self._find_one_frame(ri)
            if frame is None:
                return None
            r1, c1, r2, c2 = frame

            # Identify marker color (non-0, non-1 in grid)
            marker = None
            for r in range(h):
                for c in range(w):
                    v = ri[r][c]
                    if v != 0 and v != 1:
                        if marker is None:
                            marker = v
                        elif v != marker:
                            return None
            if marker is None:
                return None

            # Count marker cells strictly inside the frame
            count = 0
            for r in range(r1 + 1, r2):
                for c in range(c1 + 1, c2):
                    if ri[r][c] == marker:
                        count += 1

            # Verify output: first `count` cells = marker, rest = 0
            for idx in range(9):
                rr, cc = divmod(idx, 3)
                expected = marker if idx < count else 0
                if ro[rr][cc] != expected:
                    return None

        return {"type": "count_inside_frame", "confidence": 1.0}

    def _find_one_frame(self, raw):
        """Find a single rectangular frame made of 1s in the grid.
        Returns (r1, c1, r2, c2) for the bounding box of the frame."""
        h, w = len(raw), len(raw[0])
        ones = [(r, c) for r in range(h) for c in range(w) if raw[r][c] == 1]
        if not ones:
            return None
        r1 = min(r for r, c in ones)
        r2 = max(r for r, c in ones)
        c1 = min(c for r, c in ones)
        c2 = max(c for r, c in ones)
        # Verify top/bottom rows and left/right columns are all 1s
        for c in range(c1, c2 + 1):
            if raw[r1][c] != 1 or raw[r2][c] != 1:
                return None
        for r in range(r1, r2 + 1):
            if raw[r][c1] != 1 or raw[r][c2] != 1:
                return None
        return (r1, c1, r2, c2)

    # ---- strategy: flood fill interior of closed boundary regions --------

    def _try_flood_fill_interior(self, task):
        """
        Detect: grid has regions bounded by a boundary color (e.g. 2).
        Interior 0-cells that cannot be reached from the grid edge without
        crossing a boundary cell are filled with a fill color (e.g. 1).
        Category: flood fill / enclosed region detection.
        """
        if task is None:
            return None
        pairs = task.example_pairs
        if not pairs:
            return None

        boundary_color = None
        fill_color = None

        for pair in pairs:
            g0, g1 = pair.input_grid, pair.output_grid
            if g0 is None or g1 is None:
                return None
            ri, ro = g0.raw, g1.raw
            h, w = len(ri), len(ri[0])
            oh, ow = len(ro), len(ro[0])
            if h != oh or w != ow:
                return None

            # Find cells that changed from 0 to something
            bc = None
            fc = None
            for r in range(h):
                for c in range(w):
                    if ri[r][c] != ro[r][c]:
                        if ri[r][c] != 0:
                            return None  # only 0s should change
                        if fc is None:
                            fc = ro[r][c]
                        elif ro[r][c] != fc:
                            return None

            if fc is None:
                return None  # no changes

            # Determine boundary color: the non-0, non-fill color
            colors = set()
            for r in range(h):
                for c in range(w):
                    if ri[r][c] != 0:
                        colors.add(ri[r][c])
            colors.discard(fc)
            if len(colors) != 1:
                return None
            bc = colors.pop()

            if boundary_color is None:
                boundary_color = bc
                fill_color = fc
            elif bc != boundary_color or fc != fill_color:
                return None

            # Verify: flood fill from edges through non-boundary cells
            predicted = self._compute_flood_fill(ri, boundary_color, fill_color)
            if predicted != ro:
                return None

        return {
            "type": "flood_fill_interior",
            "boundary_color": boundary_color,
            "fill_color": fill_color,
            "confidence": 1.0,
        }

    def _compute_flood_fill(self, raw, boundary_color, fill_color):
        """Flood fill from edges: 0-cells reachable from edge without crossing
        boundary stay 0; unreachable 0-cells become fill_color."""
        h, w = len(raw), len(raw[0])
        reachable = [[False] * w for _ in range(h)]
        queue = []
        # Seed from all edge cells that are not the boundary color
        for r in range(h):
            for c in range(w):
                if (r == 0 or r == h - 1 or c == 0 or c == w - 1):
                    if raw[r][c] != boundary_color and not reachable[r][c]:
                        reachable[r][c] = True
                        queue.append((r, c))
        while queue:
            r, c = queue.pop(0)
            for dr, dc in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                nr, nc = r + dr, c + dc
                if 0 <= nr < h and 0 <= nc < w and not reachable[nr][nc]:
                    if raw[nr][nc] != boundary_color:
                        reachable[nr][nc] = True
                        queue.append((nr, nc))
        result = [row[:] for row in raw]
        for r in range(h):
            for c in range(w):
                if raw[r][c] == 0 and not reachable[r][c]:
                    result[r][c] = fill_color
        return result

    # ---- strategy: rotation quad tile (0°, 90°CCW, 180°, 90°CW) ---------

    def _try_rotation_quad_tile(self, task):
        """
        Detect: output is 2x the input dimensions.  The four quadrants are
        the input rotated by 0° (TL), 90° CCW (TR), 180° (BL), 90° CW (BR).
        Category: rotation tiling / symmetry expansion.
        """
        if task is None:
            return None
        pairs = task.example_pairs
        if not pairs:
            return None

        for pair in pairs:
            g0, g1 = pair.input_grid, pair.output_grid
            if g0 is None or g1 is None:
                return None
            ri, ro = g0.raw, g1.raw
            h, w = len(ri), len(ri[0])
            oh, ow = len(ro), len(ro[0])
            if oh != 2 * h or ow != 2 * w:
                return None

            # Build the four rotations
            # 90° CCW: new[i][j] = old[j][N-1-i] where N = width for cols
            rot90ccw = [[ri[c][h_idx] for c in range(w)] for h_idx in range(h - 1, -1, -1)]
            # Wait, need to be careful with non-square grids
            # For 90° CCW of HxW grid → WxH grid
            # new[i][j] = old[j][W-1-i], shape is (W, H)
            rot90ccw = [[ri[j][w - 1 - i] for j in range(h)] for i in range(w)]
            # 180°: new[i][j] = old[H-1-i][W-1-j]
            rot180 = [[ri[h - 1 - i][w - 1 - j] for j in range(w)] for i in range(h)]
            # 90° CW: new[i][j] = old[H-1-j][i], shape is (W, H)
            rot90cw = [[ri[h - 1 - j][i] for j in range(h)] for i in range(w)]

            # For 2x tiling to work, rotated shapes must match original dims
            # This only works for square grids (h == w)
            if h != w:
                return None

            # Verify quadrants
            for r in range(h):
                for c in range(w):
                    if ro[r][c] != ri[r][c]:             # TL = original
                        return None
                    if ro[r][w + c] != rot90ccw[r][c]:    # TR = 90° CCW
                        return None
                    if ro[h + r][c] != rot180[r][c]:      # BL = 180°
                        return None
                    if ro[h + r][w + c] != rot90cw[r][c]: # BR = 90° CW
                        return None

        return {"type": "rotation_quad_tile", "confidence": 1.0}

    # ---- strategy: boolean NOR of two grid sections ----------------------

    def _try_mask_nor(self, task):
        """
        Detect: input has two equal-sized sections separated by a uniform-
        color divider row.  Output cell = result_color where BOTH sections
        have 0 (NOR), else 0.
        Category: boolean grid operations / set difference.
        """
        if task is None:
            return None
        pairs = task.example_pairs
        if not pairs:
            return None

        result_color = None

        for pair in pairs:
            g0, g1 = pair.input_grid, pair.output_grid
            if g0 is None or g1 is None:
                return None
            ri, ro = g0.raw, g1.raw
            h, w = len(ri), len(ri[0])
            oh, ow = len(ro), len(ro[0])

            # Find divider row: uniform non-zero row that splits grid into
            # two equal halves whose height matches the output height
            div_row = None
            for r in range(h):
                vals = set(ri[r])
                if len(vals) == 1 and ri[r][0] != 0:
                    t = ri[:r]
                    b = ri[r + 1:]
                    if len(t) == len(b) and len(t) == oh and w == ow:
                        div_row = r
                        break
            if div_row is None:
                return None

            top = ri[:div_row]
            bottom = ri[div_row + 1:]

            # Determine result color from output
            rc = None
            for r in range(oh):
                for c in range(ow):
                    if ro[r][c] != 0:
                        if rc is None:
                            rc = ro[r][c]
                        elif ro[r][c] != rc:
                            return None
            if rc is None:
                return None
            if result_color is None:
                result_color = rc
            elif rc != result_color:
                return None

            # Verify NOR logic
            for r in range(oh):
                for c in range(ow):
                    expected = result_color if (top[r][c] == 0 and bottom[r][c] == 0) else 0
                    if ro[r][c] != expected:
                        return None

        return {
            "type": "mask_nor",
            "result_color": result_color,
            "confidence": 1.0,
        }

    # ---- strategy: diagonal line extension from 2x2 block ----------------

    def _try_diagonal_extend(self, task):
        """
        Detect: a 2x2 block of one non-zero color with 1+ single pixels
        diagonally adjacent to its corners.  Each tail pixel is extended
        along the same diagonal direction until hitting the grid edge.
        Category: directional line continuation / diagonal propagation.
        """
        if task is None:
            return None
        pairs = task.example_pairs
        if not pairs:
            return None

        for pair in pairs:
            g0, g1 = pair.input_grid, pair.output_grid
            if g0 is None or g1 is None:
                return None
            ri, ro = g0.raw, g1.raw
            h, w = len(ri), len(ri[0])
            if len(ro) != h or len(ro[0]) != w:
                return None

            # Collect non-zero cells and ensure single color
            cells = []
            colors = set()
            for r in range(h):
                for c in range(w):
                    if ri[r][c] != 0:
                        cells.append((r, c))
                        colors.add(ri[r][c])
            if len(colors) != 1 or len(cells) < 5:
                return None
            color = next(iter(colors))

            # Find a 2x2 block
            block = None
            for r in range(h - 1):
                for c in range(w - 1):
                    if (ri[r][c] == color and ri[r][c + 1] == color and
                            ri[r + 1][c] == color and ri[r + 1][c + 1] == color):
                        block = (r, c)
                        break
                if block:
                    break
            if block is None:
                return None

            br, bc = block
            block_cells = {(br, bc), (br, bc + 1), (br + 1, bc), (br + 1, bc + 1)}

            # Diagonal corners map to directions
            corners = {
                (br - 1, bc - 1): (-1, -1),
                (br - 1, bc + 2): (-1, 1),
                (br + 2, bc - 1): (1, -1),
                (br + 2, bc + 2): (1, 1),
            }

            tails = [(r, c) for r, c in cells if (r, c) not in block_cells]
            if not tails:
                return None
            for tr, tc in tails:
                if (tr, tc) not in corners:
                    return None

            # Build predicted output
            predicted = [row[:] for row in ri]
            for tr, tc in tails:
                dr, dc = corners[(tr, tc)]
                nr, nc = tr + dr, tc + dc
                while 0 <= nr < h and 0 <= nc < w:
                    predicted[nr][nc] = color
                    nr += dr
                    nc += dc

            if predicted != ro:
                return None

        return {"type": "diagonal_extend", "confidence": 1.0}

    # ---- strategy: 2x2 core quadrant fill --------------------------------

    def _try_core_quadrant_fill(self, task):
        """
        Detect: a single 2x2 block of 4 distinct non-zero colors in an
        otherwise empty grid.  Each of the 4 surrounding quadrants gets a
        2x2 fill (clipped to grid) of the diagonally opposite core color.
        Category: color reflection / quadrant projection.
        """
        if task is None:
            return None
        pairs = task.example_pairs
        if not pairs:
            return None

        for pair in pairs:
            g0, g1 = pair.input_grid, pair.output_grid
            if g0 is None or g1 is None:
                return None
            ri, ro = g0.raw, g1.raw
            h, w = len(ri), len(ri[0])
            if len(ro) != h or len(ro[0]) != w:
                return None

            # Find the unique 2x2 block of 4 distinct non-zero colors
            block = None
            for r in range(h - 1):
                for c in range(w - 1):
                    vals = [ri[r][c], ri[r][c + 1], ri[r + 1][c], ri[r + 1][c + 1]]
                    if all(v != 0 for v in vals) and len(set(vals)) == 4:
                        block = (r, c)
                        break
                if block:
                    break
            if block is None:
                return None

            # Verify only 4 non-zero cells in input
            nz = sum(1 for r in range(h) for c in range(w) if ri[r][c] != 0)
            if nz != 4:
                return None

            br, bc = block
            core_tl = ri[br][bc]
            core_tr = ri[br][bc + 1]
            core_bl = ri[br + 1][bc]
            core_br = ri[br + 1][bc + 1]

            # Build predicted output
            predicted = [[0] * w for _ in range(h)]
            predicted[br][bc] = core_tl
            predicted[br][bc + 1] = core_tr
            predicted[br + 1][bc] = core_bl
            predicted[br + 1][bc + 1] = core_br

            # TL quadrant fill with core_br (diag opposite)
            for r in range(max(0, br - 2), br):
                for c in range(max(0, bc - 2), bc):
                    predicted[r][c] = core_br
            # TR quadrant fill with core_bl
            for r in range(max(0, br - 2), br):
                for c in range(bc + 2, min(w, bc + 4)):
                    predicted[r][c] = core_bl
            # BL quadrant fill with core_tr
            for r in range(br + 2, min(h, br + 4)):
                for c in range(max(0, bc - 2), bc):
                    predicted[r][c] = core_tr
            # BR quadrant fill with core_tl
            for r in range(br + 2, min(h, br + 4)):
                for c in range(bc + 2, min(w, bc + 4)):
                    predicted[r][c] = core_tl

            if predicted != ro:
                return None

        return {"type": "core_quadrant_fill", "confidence": 1.0}

    # ---- strategy: noise removal -- keep rectangular blocks only ----------

    def _try_noise_remove_rect(self, task):
        """
        Detect: single non-zero color forms solid rectangular blocks plus
        scattered isolated pixels (noise).  Output removes all pixels that
        are not part of any 2x2+ solid block of the same color.
        Category: noise removal / rectangular component filtering.
        """
        if task is None:
            return None
        pairs = task.example_pairs
        if not pairs:
            return None

        for pair in pairs:
            g0, g1 = pair.input_grid, pair.output_grid
            if g0 is None or g1 is None:
                return None
            ri, ro = g0.raw, g1.raw
            h, w = len(ri), len(ri[0])
            if len(ro) != h or len(ro[0]) != w:
                return None

            # Single non-zero color
            colors = set()
            for r in range(h):
                for c in range(w):
                    if ri[r][c] != 0:
                        colors.add(ri[r][c])
            if len(colors) != 1:
                return None

            # Keep cells that belong to at least one 2x2 block
            keep = set()
            for r in range(h - 1):
                for c in range(w - 1):
                    v = ri[r][c]
                    if (v != 0 and ri[r][c + 1] == v and
                            ri[r + 1][c] == v and ri[r + 1][c + 1] == v):
                        keep.add((r, c))
                        keep.add((r, c + 1))
                        keep.add((r + 1, c))
                        keep.add((r + 1, c + 1))

            # Need at least one rectangle and at least one removed pixel
            removed = [(r, c) for r in range(h) for c in range(w)
                        if ri[r][c] != 0 and (r, c) not in keep]
            if not keep or not removed:
                return None

            # Verify output
            predicted = [[0] * w for _ in range(h)]
            for r, c in keep:
                predicted[r][c] = ri[r][c]
            if predicted != ro:
                return None

        return {"type": "noise_remove_rect", "confidence": 1.0}

    # ---- strategy: frame color swap (extract rect, swap 2 colors) --------

    def _try_frame_color_swap(self, task):
        """
        Detect pattern: a rectangular block of exactly two non-zero colors
        on a zero background.  Output = extracted block with the two colors
        swapped.
        """
        if task is None:
            return None
        pairs = task.example_pairs
        if not pairs:
            return None

        for pair in pairs:
            ri = pair.input_grid.raw
            ro = pair.output_grid.raw
            h, w = len(ri), len(ri[0])
            oh, ow = len(ro), len(ro[0])

            # Bounding box of non-zero cells
            min_r, max_r, min_c, max_c = h, -1, w, -1
            for r in range(h):
                for c in range(w):
                    if ri[r][c] != 0:
                        min_r = min(min_r, r)
                        max_r = max(max_r, r)
                        min_c = min(min_c, c)
                        max_c = max(max_c, c)
            if max_r == -1:
                return None

            block = [ri[r][min_c:max_c + 1] for r in range(min_r, max_r + 1)]
            bh, bw = len(block), len(block[0])

            if oh != bh or ow != bw:
                return None

            # Exactly two colors in block, all cells non-zero
            colors = set()
            for row in block:
                for v in row:
                    if v == 0:
                        return None
                    colors.add(v)
            if len(colors) != 2:
                return None

            c1, c2 = sorted(colors)

            # Swap colors and verify
            expected = []
            for row in block:
                expected.append([c2 if v == c1 else c1 for v in row])
            if expected != ro:
                return None

        return {"type": "frame_color_swap", "confidence": 0.95}

    # ---- strategy: pattern tile fill (tile pattern upward) ---------------

    def _try_pattern_tile_fill(self, task):
        """
        Detect pattern: top portion of grid is uniform background; bottom
        portion has a multi-row pattern.  Output tiles the pattern upward
        to fill the entire grid.
        """
        if task is None:
            return None
        pairs = task.example_pairs
        if not pairs:
            return None

        for pair in pairs:
            ri = pair.input_grid.raw
            ro = pair.output_grid.raw
            h, w = len(ri), len(ri[0])
            if len(ro) != h or len(ro[0]) != w:
                return None

            # Background = value of top-left cell; entire first row must match
            bg = ri[0][0]
            if not all(ri[0][c] == bg for c in range(w)):
                return None

            # Find pattern start (first row with any non-bg cell)
            pattern_start = None
            for r in range(h):
                if any(ri[r][c] != bg for c in range(w)):
                    pattern_start = r
                    break
            if pattern_start is None or pattern_start == 0:
                return None

            # All rows before pattern_start must be pure bg
            for r in range(pattern_start):
                if any(ri[r][c] != bg for c in range(w)):
                    return None

            ph = h - pattern_start
            pattern = [ri[r][:] for r in range(pattern_start, h)]

            # Verify output is pattern tiled
            for r in range(h):
                idx = (r - pattern_start) % ph
                if ro[r] != pattern[idx]:
                    return None

        return {"type": "pattern_tile_fill", "confidence": 0.95}

    # ---- strategy: template color remap (block + key pairs) --------------

    def _try_template_color_remap(self, task):
        """
        Detect pattern: a rectangular block (all non-zero) plus scattered
        2-cell key-value pairs on a zero background.  Each pair [a, b]
        (raster order) defines mapping b -> a.  Output = extracted block
        with colors remapped.
        """
        if task is None:
            return None
        pairs = task.example_pairs
        if not pairs:
            return None

        for pair in pairs:
            ri = pair.input_grid.raw
            ro = pair.output_grid.raw
            h, w = len(ri), len(ri[0])
            oh, ow = len(ro), len(ro[0])

            # Find connected components of non-zero cells (4-connected)
            visited = [[False] * w for _ in range(h)]
            components = []
            for r in range(h):
                for c in range(w):
                    if ri[r][c] != 0 and not visited[r][c]:
                        comp = []
                        queue = [(r, c)]
                        visited[r][c] = True
                        while queue:
                            cr, cc = queue.pop(0)
                            comp.append((cr, cc))
                            for dr, dc in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                                nr, nc = cr + dr, cc + dc
                                if (0 <= nr < h and 0 <= nc < w
                                        and not visited[nr][nc]
                                        and ri[nr][nc] != 0):
                                    visited[nr][nc] = True
                                    queue.append((nr, nc))
                        components.append(comp)

            if len(components) < 2:
                return None

            # Largest component = block; must be a filled rectangle
            components.sort(key=len, reverse=True)
            block_comp = components[0]
            br1 = min(r for r, c in block_comp)
            br2 = max(r for r, c in block_comp)
            bc1 = min(c for r, c in block_comp)
            bc2 = max(c for r, c in block_comp)
            bh, bw = br2 - br1 + 1, bc2 - bc1 + 1
            if len(block_comp) != bh * bw:
                return None

            if oh != bh or ow != bw:
                return None

            block = [ri[r][bc1:bc2 + 1] for r in range(br1, br2 + 1)]

            # Remaining components must be 2-cell key pairs
            if len(components) < 2:
                return None
            key_pairs = []
            for comp in components[1:]:
                if len(comp) != 2:
                    return None
                (r1, c1), (r2, c2) = comp
                key_pairs.append((ri[r1][c1], ri[r2][c2]))

            # Determine mapping: figure out old vs new via block membership
            block_colors = set()
            for row in block:
                for v in row:
                    block_colors.add(v)

            color_map = {}
            for a, b in key_pairs:
                a_in = a in block_colors
                b_in = b in block_colors
                if b_in and not a_in:
                    color_map[b] = a
                elif a_in and not b_in:
                    color_map[a] = b
                else:
                    # Fallback: raster-order convention (b -> a)
                    color_map[b] = a

            # Apply mapping to block and verify
            expected = []
            for row in block:
                expected.append([color_map.get(v, v) for v in row])
            if expected != ro:
                return None

        return {"type": "template_color_remap", "confidence": 0.95}

    # ---- strategy: marker ray fill ----------------------------------------

    def _try_marker_ray_fill(self, task):
        """
        Detect pattern: isolated non-zero marker pixels on a zero background.
        Each marker fills rightward to the grid edge, then fills downward
        along the right-edge column until the next marker's row (or grid bottom).
        """
        if task is None:
            return None
        pairs = task.example_pairs
        if not pairs:
            return None

        for pair in pairs:
            ri = pair.input_grid.raw
            ro = pair.output_grid.raw
            h, w = len(ri), len(ri[0])
            oh, ow = len(ro), len(ro[0])
            if h != oh or w != ow:
                return None

            # Collect non-zero markers (must be isolated single pixels)
            markers = []
            for r in range(h):
                for c in range(w):
                    if ri[r][c] != 0:
                        markers.append((r, c, ri[r][c]))
            if not markers:
                return None

            # Check they are isolated (no two adjacent)
            mset = {(r, c) for r, c, _ in markers}
            for r, c, _ in markers:
                for dr, dc in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                    if (r + dr, c + dc) in mset:
                        return None

            # Sort markers by row
            markers.sort(key=lambda m: m[0])

            # Build expected output
            expected = [[0] * w for _ in range(h)]
            for idx, (mr, mc, color) in enumerate(markers):
                # Fill right from marker to right edge
                for c in range(mc, w):
                    expected[mr][c] = color
                # Fill down right-edge column from marker_row+1
                # until next marker's row - 1 (or bottom)
                if idx + 1 < len(markers):
                    end_row = markers[idx + 1][0] - 1
                else:
                    end_row = h - 1
                for r in range(mr + 1, end_row + 1):
                    expected[r][w - 1] = color

            if expected != ro:
                return None

        return {"type": "marker_ray_fill", "confidence": 0.95}

    # ---- strategy: crop bounding box --------------------------------------

    def _try_crop_bbox(self, task):
        """
        Detect pattern: the output is the bounding box of all non-background
        pixels in the input, with the background color replaced by 0.
        Background = most common color in input.
        """
        if task is None:
            return None
        pairs = task.example_pairs
        if not pairs:
            return None

        bg_color = None
        for pair in pairs:
            ri = pair.input_grid.raw
            ro = pair.output_grid.raw
            h, w = len(ri), len(ri[0])
            oh, ow = len(ro), len(ro[0])

            # Output must be smaller than input
            if oh >= h and ow >= w:
                return None

            # Determine background color (most common)
            freq = {}
            for r in range(h):
                for c in range(w):
                    v = ri[r][c]
                    freq[v] = freq.get(v, 0) + 1
            local_bg = max(freq, key=freq.get)

            if bg_color is None:
                bg_color = local_bg
            elif bg_color != local_bg:
                return None

            # Find bounding box of non-bg pixels
            non_bg = [(r, c) for r in range(h) for c in range(w)
                       if ri[r][c] != bg_color]
            if not non_bg:
                return None
            r1 = min(r for r, c in non_bg)
            r2 = max(r for r, c in non_bg)
            c1 = min(c for r, c in non_bg)
            c2 = max(c for r, c in non_bg)
            bh, bw = r2 - r1 + 1, c2 - c1 + 1

            if bh != oh or bw != ow:
                return None

            # Extract region, replace bg with 0
            expected = []
            for r in range(r1, r2 + 1):
                row = []
                for c in range(c1, c2 + 1):
                    v = ri[r][c]
                    row.append(0 if v == bg_color else v)
                expected.append(row)

            if expected != ro:
                return None

        return {"type": "crop_bbox", "bg_color": bg_color, "confidence": 0.95}

    # ---- strategy: binary grid XOR ----------------------------------------

    def _try_binary_grid_xor(self, task):
        """
        Detect pattern: input grid has a separator row of uniform non-zero
        color splitting it into two equal halves.  Each half is binary
        (0 vs color_A / 0 vs color_B).  Output = XOR of the two binary
        masks, with 1s mapped to a result color (typically 3).
        """
        if task is None:
            return None
        pairs = task.example_pairs
        if not pairs:
            return None

        result_color = None
        for pair in pairs:
            ri = pair.input_grid.raw
            ro = pair.output_grid.raw
            h, w = len(ri), len(ri[0])
            oh, ow = len(ro), len(ro[0])

            # Find separator row (all cells same non-zero value)
            sep_row = None
            sep_val = None
            for r in range(h):
                vals = set(ri[r])
                if len(vals) == 1 and 0 not in vals:
                    sep_row = r
                    sep_val = vals.pop()
                    break
            if sep_row is None:
                return None

            # Split into top and bottom halves
            top = ri[:sep_row]
            bot = ri[sep_row + 1:]
            th, bh_ = len(top), len(bot)
            if th != bh_ or th != oh or w != ow:
                return None

            # Identify the non-zero color in each half
            top_colors = {v for row in top for v in row if v != 0}
            bot_colors = {v for row in bot for v in row if v != 0}
            if len(top_colors) != 1 or len(bot_colors) != 1:
                return None
            color_a = top_colors.pop()
            color_b = bot_colors.pop()

            # Build binary masks and XOR
            out_colors = {v for row in ro for v in row if v != 0}
            if len(out_colors) != 1:
                return None
            local_result = out_colors.pop()
            if result_color is None:
                result_color = local_result
            elif result_color != local_result:
                return None

            expected = []
            for r in range(th):
                row = []
                for c in range(w):
                    a_set = (top[r][c] == color_a)
                    b_set = (bot[r][c] == color_b)
                    row.append(result_color if (a_set != b_set) else 0)
                expected.append(row)

            if expected != ro:
                return None

        return {"type": "binary_grid_xor", "result_color": result_color,
                "confidence": 0.95}


    # ---- strategy: nonzero count scale ------------------------------------

    def _try_nonzero_count_scale(self, task):
        """
        Detect pattern: output is a scaled version of the input where the
        scale factor equals the number of non-zero cells.  Each input cell
        becomes a KxK block of its color in the output.
        """
        if task is None:
            return None
        pairs = task.example_pairs
        if not pairs:
            return None

        for pair in pairs:
            g0, g1 = pair.input_grid, pair.output_grid
            if g0 is None or g1 is None:
                return None
            r0, r1 = g0.raw, g1.raw
            h0 = len(r0)
            w0 = len(r0[0]) if r0 else 0
            h1 = len(r1)
            w1 = len(r1[0]) if r1 else 0
            if h0 == 0 or w0 == 0:
                return None

            # Count non-zero cells
            nz = sum(1 for row in r0 for v in row if v != 0)
            if nz <= 1:
                return None

            # Check scale factor matches nz
            if h1 != h0 * nz or w1 != w0 * nz:
                return None

            # Verify each cell maps to a uniform block
            for r in range(h0):
                for c in range(w0):
                    expected = r0[r][c]
                    for dr in range(nz):
                        for dc in range(nz):
                            if r1[r * nz + dr][c * nz + dc] != expected:
                                return None

        return {
            "type": "nonzero_count_scale",
            "confidence": 1.0,
        }

    # ---- strategy: stripe rotate -----------------------------------------

    def _try_stripe_rotate(self, task):
        """
        Detect pattern: input has vertical stripes of uniform color on the
        right side and a marker (single non-zero color) in the left column.
        Output collapses the stripes into a single cycling column, each color
        repeating for the marker-height rows.
        """
        if task is None:
            return None
        pairs = task.example_pairs
        if not pairs:
            return None

        for pair in pairs:
            ri = pair.input_grid.raw
            ro = pair.output_grid.raw
            h = len(ri)
            w = len(ri[0]) if ri else 0
            oh = len(ro)
            ow = len(ro[0]) if ro else 0
            if h != oh or w != ow:
                return None

            # Find stripe columns on the right: each column all same non-zero
            stripe_colors = []
            stripe_start = None
            for c in range(w - 1, -1, -1):
                col_vals = [ri[r][c] for r in range(h)]
                unique = set(col_vals)
                if len(unique) == 1 and 0 not in unique:
                    if stripe_start is None:
                        stripe_start = c
                    stripe_colors.append(col_vals[0])
                else:
                    if stripe_start is not None:
                        break
            if not stripe_colors:
                return None
            stripe_colors.reverse()  # left-to-right order
            num_stripes = len(stripe_colors)

            # Find marker: non-zero cells in the leftmost column(s)
            marker_color = None
            marker_height = 0
            for r in range(h):
                if ri[r][0] != 0:
                    if marker_color is None:
                        marker_color = ri[r][0]
                    elif ri[r][0] != marker_color:
                        return None
                    marker_height += 1
            if marker_color is None or marker_height == 0:
                return None
            # Marker must not be a stripe color
            if marker_color in stripe_colors:
                return None

            # Output column position
            out_col = w - num_stripes - 1

            # Build expected output
            expected = [[0] * w for _ in range(h)]
            for r in range(h):
                if ri[r][0] == marker_color:
                    expected[r][0] = marker_color
            for r in range(h):
                cidx = (r // marker_height) % num_stripes
                expected[r][out_col] = stripe_colors[cidx]

            if expected != ro:
                return None

        return {
            "type": "stripe_rotate",
            "confidence": 1.0,
        }

    # ---- strategy: frame solid compose -----------------------------------

    def _try_frame_solid_compose(self, task):
        """
        Detect pattern: grid has same-sized colored rectangles on a black
        background.  Some are hollow frames (border colored, interior 0),
        others are solid.  Output tiles only the frames in spatial order.
        """
        if task is None:
            return None
        pairs = task.example_pairs
        if not pairs:
            return None

        for pair in pairs:
            ri = pair.input_grid.raw
            ro = pair.output_grid.raw
            h = len(ri)
            w = len(ri[0]) if ri else 0

            # Find colored rectangular objects
            rects = self._find_colored_rects(ri, 0)
            if len(rects) < 2:
                return None

            # All rects must be the same size
            sizes = set((r["h"], r["w"]) for r in rects)
            if len(sizes) != 1:
                return None
            rh, rw = sizes.pop()
            if rh < 3 or rw < 3:
                # Too small to have a meaningful interior
                # Could be solid only; allow size 4 or above
                pass

            # Classify: frame (has 0 interior) vs solid
            frames = []
            for rect in rects:
                is_frame = False
                for r in range(rect["r"] + 1, rect["r"] + rect["h"] - 1):
                    for c in range(rect["c"] + 1, rect["c"] + rect["w"] - 1):
                        if ri[r][c] == 0:
                            is_frame = True
                            break
                    if is_frame:
                        break
                if is_frame:
                    frames.append(rect)

            if not frames:
                return None

            # Determine tiling direction from frame positions
            row_spread = max(f["r"] for f in frames) - min(f["r"] for f in frames)
            col_spread = max(f["c"] for f in frames) - min(f["c"] for f in frames)

            if col_spread >= row_spread:
                # Horizontal: sort by column
                frames.sort(key=lambda f: f["c"])
                exp_h = rh
                exp_w = rw * len(frames)
            else:
                # Vertical: sort by row
                frames.sort(key=lambda f: f["r"])
                exp_h = rh * len(frames)
                exp_w = rw

            oh = len(ro)
            ow = len(ro[0]) if ro else 0
            if oh != exp_h or ow != exp_w:
                return None

            # Build expected output
            expected = [[0] * exp_w for _ in range(exp_h)]
            for fi, f in enumerate(frames):
                for r in range(rh):
                    for c in range(rw):
                        if col_spread >= row_spread:
                            expected[r][fi * rw + c] = ri[f["r"] + r][f["c"] + c]
                        else:
                            expected[fi * rh + r][c] = ri[f["r"] + r][f["c"] + c]

            if expected != ro:
                return None

        return {
            "type": "frame_solid_compose",
            "confidence": 1.0,
        }

    # ---- strategy: self tile (NxN -> N²xN²) ------------------------------

    def _try_self_tile(self, task):
        """
        Detect: NxN input with one non-zero color.  Output is (N*N)x(N*N)
        grid divided into NxN blocks.  Where input cell is non-zero, the
        block contains either a COPY of the input or the COMPLEMENT (swap
        0 and the color).  Where input cell is 0, block is all zeros.
        Category: fractal self-reference / self-tiling.
        """
        if task is None:
            return None
        pairs = task.example_pairs
        if not pairs:
            return None

        mode = None  # "copy" or "complement"
        for pair in pairs:
            ri = pair.input_grid.raw
            ro = pair.output_grid.raw
            h, w = len(ri), len(ri[0])
            oh, ow = len(ro), len(ro[0])

            # Must be square input and output = N² x N²
            if h != w or oh != h * h or ow != w * w:
                return None
            n = h

            # Must have exactly one non-zero color
            colors = {v for row in ri for v in row if v != 0}
            if len(colors) != 1:
                return None
            color = colors.pop()

            # Build the expected tile for copy and complement
            tile_copy = [row[:] for row in ri]
            tile_comp = [[color if v == 0 else 0 for v in row] for row in ri]
            zero_tile = [[0] * n for _ in range(n)]

            # Check each NxN block
            local_mode = None
            for br in range(n):
                for bc in range(n):
                    block = [ro[br * n + r][bc * n: bc * n + n] for r in range(n)]
                    if ri[br][bc] == 0:
                        if block != zero_tile:
                            return None
                    else:
                        if block == tile_copy:
                            if local_mode is None:
                                local_mode = "copy"
                            elif local_mode != "copy":
                                return None
                        elif block == tile_comp:
                            if local_mode is None:
                                local_mode = "complement"
                            elif local_mode != "complement":
                                return None
                        else:
                            return None

            if local_mode is None:
                return None
            if mode is None:
                mode = local_mode
            elif mode != local_mode:
                return None

        return {"type": "self_tile", "mode": mode, "confidence": 1.0}

    # ---- strategy: separator AND (column separator) ----------------------

    def _try_separator_and(self, task):
        """
        Detect: input grid has a separator COLUMN of uniform non-zero
        color splitting it into two equal halves (left and right).  Each
        half is binary (0 vs non-zero).  Output = AND of the two binary
        masks (cells where both halves are non-zero), with a result color.
        Category: binary comparison / mask intersection.
        """
        if task is None:
            return None
        pairs = task.example_pairs
        if not pairs:
            return None

        result_color = None
        for pair in pairs:
            ri = pair.input_grid.raw
            ro = pair.output_grid.raw
            h, w = len(ri), len(ri[0])
            oh, ow = len(ro), len(ro[0])

            # Find separator column (all cells same non-zero value)
            sep_col = None
            for c in range(w):
                vals = set(ri[r][c] for r in range(h))
                if len(vals) == 1 and 0 not in vals:
                    sep_col = c
                    break
            if sep_col is None:
                return None

            left = [row[:sep_col] for row in ri]
            right = [row[sep_col + 1:] for row in ri]
            lw = len(left[0]) if left else 0
            rw_ = len(right[0]) if right else 0
            if lw != rw_ or lw != ow or h != oh:
                return None

            # Determine result color from output
            out_colors = {v for row in ro for v in row if v != 0}
            if len(out_colors) > 1:
                return None
            if len(out_colors) == 0:
                # All zero output is possible; just need to check AND is empty
                local_result = None
            else:
                local_result = out_colors.pop()

            # Build expected AND output
            expected = []
            for r in range(h):
                row = []
                for c in range(lw):
                    a_set = left[r][c] != 0
                    b_set = right[r][c] != 0
                    if a_set and b_set:
                        row.append(local_result if local_result else 0)
                    else:
                        row.append(0)
                expected.append(row)

            if expected != ro:
                return None

            if local_result is not None:
                if result_color is None:
                    result_color = local_result
                elif result_color != local_result:
                    return None

        if result_color is None:
            return None

        return {"type": "separator_and", "result_color": result_color,
                "confidence": 0.95}

    # ---- strategy: checkerboard tile (HxW -> 3H x 3W) -------------------

    def _try_checkerboard_tile(self, task):
        """
        Detect: output is exactly 3x the input dimensions.  The output is
        a 3x3 tiling of the input where even tile-rows use the input as-is
        and odd tile-rows use a horizontally-flipped version.  Both are
        repeated 3 times across the width.
        Category: tiling with alternating reflection.
        """
        if task is None:
            return None
        pairs = task.example_pairs
        if not pairs:
            return None

        for pair in pairs:
            ri = pair.input_grid.raw
            ro = pair.output_grid.raw
            h, w = len(ri), len(ri[0])
            oh, ow = len(ro), len(ro[0])

            if oh != 3 * h or ow != 3 * w:
                return None

            hflip = [row[::-1] for row in ri]

            for tr in range(3):  # tile row
                tile = ri if tr % 2 == 0 else hflip
                for tc in range(3):  # tile col
                    for r in range(h):
                        for c in range(w):
                            if ro[tr * h + r][tc * w + c] != tile[r][c]:
                                return None

        return {"type": "checkerboard_tile", "confidence": 1.0}

    # ---- strategy 38: point to line ----------------------------------------

    def _try_point_to_line(self, task):
        """
        Detect: each non-bg pixel in the input expands to a full-span line.
        Some colors become horizontal lines (fill the row), others become
        vertical lines (fill the column).  At intersections, one axis wins.
        Category: color-conditioned point-to-line projection.
        """
        if task is None:
            return None
        pairs = task.example_pairs
        if not pairs:
            return None

        # Determine background color (most common in first input)
        ri0 = pairs[0].input_grid.raw
        from collections import Counter
        flat = [v for row in ri0 for v in row]
        bg = Counter(flat).most_common(1)[0][0]

        # Collect color -> axis mapping from all pairs
        # For each non-bg pixel, count how many cells in its row vs column
        # match that color. Higher coverage indicates the axis.
        h_colors = set()  # colors that fill rows (horizontal)
        v_colors = set()  # colors that fill columns (vertical)
        all_colors = set()

        for pair in pairs:
            ri = pair.input_grid.raw
            ro = pair.output_grid.raw
            h = len(ri)
            w = len(ri[0])
            oh = len(ro)
            ow = len(ro[0])
            if oh != h or ow != w:
                return None

            for r in range(h):
                for c in range(w):
                    clr = ri[r][c]
                    if clr != bg:
                        all_colors.add(clr)

        if not all_colors:
            return None

        # For each color, determine axis by checking first pair
        pair0 = pairs[0]
        ri = pair0.input_grid.raw
        ro = pair0.output_grid.raw
        h = len(ri)
        w = len(ri[0])

        for clr in all_colors:
            # Find a seed of this color
            seed_r = seed_c = None
            for r in range(h):
                for c in range(w):
                    if ri[r][c] == clr:
                        seed_r, seed_c = r, c
                        break
                if seed_r is not None:
                    break
            if seed_r is None:
                continue

            # Count how many cells in this row/col match this color
            row_count = sum(1 for cc in range(w) if ro[seed_r][cc] == clr)
            col_count = sum(1 for rr in range(h) if ro[rr][seed_c] == clr)

            if row_count > col_count:
                h_colors.add(clr)
            elif col_count > row_count:
                v_colors.add(clr)
            elif row_count == w:
                h_colors.add(clr)
            elif col_count == h:
                v_colors.add(clr)
            else:
                return None

        if not h_colors and not v_colors:
            return None

        if h_colors & v_colors:
            return None

        # Verify: reconstruct output for all pairs
        for pair in pairs:
            ri = pair.input_grid.raw
            ro = pair.output_grid.raw
            h = len(ri)
            w = len(ri[0])

            # Collect seeds
            seeds = []
            for r in range(h):
                for c in range(w):
                    clr = ri[r][c]
                    if clr != bg:
                        seeds.append((r, c, clr))

            # Build predicted output: vertical first, then horizontal overwrites
            pred = [[bg] * w for _ in range(h)]
            # Draw vertical lines first
            for r, c, clr in seeds:
                if clr in v_colors:
                    for rr in range(h):
                        pred[rr][c] = clr
            # Draw horizontal lines on top (overwrite at intersections)
            for r, c, clr in seeds:
                if clr in h_colors:
                    for cc in range(w):
                        pred[r][cc] = clr

            if pred != ro:
                return None

        return {
            "type": "point_to_line",
            "confidence": 1.0,
            "bg": bg,
            "h_colors": sorted(h_colors),
            "v_colors": sorted(v_colors),
        }

    # ---- strategy 39: quadrant rotation completion -------------------------

    def _try_quadrant_rotation_completion(self, task):
        """
        Detect: grid split by zero-separator row and column into 4 quadrants.
        One quadrant is a solid marker (uniform non-0 color). The other 3 form
        a 90-degree rotation cycle. Output = the missing 4th rotation.
        Category: rotational symmetry completion.
        """
        if task is None:
            return None
        pairs = task.example_pairs
        if not pairs:
            return None

        def find_separator(grid):
            """Find the separator row and column (all zeros)."""
            h = len(grid)
            w = len(grid[0])
            sep_r = None
            sep_c = None
            for r in range(h):
                if all(grid[r][c] == 0 for c in range(w)):
                    sep_r = r
                    break
            for c in range(w):
                if all(grid[r][c] == 0 for r in range(h)):
                    sep_c = c
                    break
            return sep_r, sep_c

        def extract_quadrants(grid, sep_r, sep_c):
            """Extract the 4 quadrants around the separator."""
            tl = [row[:sep_c] for row in grid[:sep_r]]
            tr = [row[sep_c + 1:] for row in grid[:sep_r]]
            bl = [row[:sep_c] for row in grid[sep_r + 1:]]
            br = [row[sep_c + 1:] for row in grid[sep_r + 1:]]
            return tl, tr, bl, br

        def is_uniform(quad):
            """Check if a quadrant is all the same non-zero value."""
            if not quad or not quad[0]:
                return False
            v = quad[0][0]
            if v == 0:
                return False
            return all(quad[r][c] == v for r in range(len(quad)) for c in range(len(quad[0])))

        def rot90cw(grid):
            """Rotate a 2D list 90 degrees clockwise."""
            h = len(grid)
            w = len(grid[0]) if grid else 0
            return [[grid[h - 1 - r][c] for r in range(h)] for c in range(w)]

        for pair in pairs:
            ri = pair.input_grid.raw
            ro_expected = pair.output_grid.raw
            sep_r, sep_c = find_separator(ri)
            if sep_r is None or sep_c is None:
                return None

            tl, tr, bl, br = extract_quadrants(ri, sep_r, sep_c)

            # All quadrants must be same size
            sizes = [(len(q), len(q[0]) if q else 0) for q in [tl, tr, bl, br]]
            if len(set(sizes)) != 1:
                return None

            # Find which quadrant is the marker
            quads = [tl, tr, bl, br]
            marker_idx = None
            for i, q in enumerate(quads):
                if is_uniform(q):
                    marker_idx = i
                    break

            if marker_idx is None:
                return None

            # The 3 data quadrants in rotation order: TL(0°) -> TR(90°) -> BL(180°) -> BR(270°)
            # Actually the spatial order is: TL -> TR -> BR -> BL for clockwise,
            # but based on analysis: A(TL)->B(TR)->C(BL)->D(BR) = 0->90->180->270
            # So the rotation chain is TL -> TR -> BL -> BR
            # Missing one = rot90cw of its predecessor in chain
            chain = [0, 1, 2, 3]  # TL, TR, BL, BR
            pred_in_chain = {0: 3, 1: 0, 2: 1, 3: 2}  # predecessor

            pred_idx = pred_in_chain[marker_idx]
            expected_output = rot90cw(quads[pred_idx])

            # Verify against actual output
            if expected_output != ro_expected:
                # Try alternate chain: TL -> TR -> BR -> BL
                chain2_pred = {0: 3, 1: 0, 2: 3, 3: 1}
                # Actually let's just try: output = rot90cw of each non-marker quad
                found = False
                for src_idx in range(4):
                    if src_idx == marker_idx:
                        continue
                    candidate = rot90cw(quads[src_idx])
                    if candidate == ro_expected:
                        found = True
                        break
                if not found:
                    return None

        return {
            "type": "quadrant_rotation_completion",
            "confidence": 1.0,
        }

    # ---- strategy 40: stamp pattern ----------------------------------------

    def _try_stamp_pattern(self, task):
        """
        Detect: isolated marker pixels in input. In output, each marker is
        replaced by a fixed small pattern (stamp/kernel) centered on the
        marker position. The marker pixel itself may be cleared.
        Category: single-pixel marker expansion to fixed local pattern.
        """
        if task is None:
            return None
        pairs = task.example_pairs
        if not pairs:
            return None

        # Determine background (most common value in first input)
        from collections import Counter
        ri0 = pairs[0].input_grid.raw
        flat = [v for row in ri0 for v in row]
        bg = Counter(flat).most_common(1)[0][0]

        # Find marker color: the non-bg pixels in input (should be isolated single pixels)
        # All markers should be same color across all pairs
        marker_color = None
        for pair in pairs:
            ri = pair.input_grid.raw
            h, w = len(ri), len(ri[0])
            for r in range(h):
                for c in range(w):
                    if ri[r][c] != bg:
                        if marker_color is None:
                            marker_color = ri[r][c]
                        elif ri[r][c] != marker_color:
                            return None  # Multiple non-bg colors; not a simple stamp task

        if marker_color is None:
            return None

        # From first pair, learn the stamp pattern
        pair0 = pairs[0]
        ri = pair0.input_grid.raw
        ro = pair0.output_grid.raw
        h, w = len(ri), len(ri[0])
        oh, ow = len(ro), len(ro[0])
        if oh != h or ow != w:
            return None

        # Find first marker position
        markers = []
        for r in range(h):
            for c in range(w):
                if ri[r][c] == marker_color:
                    markers.append((r, c))

        if not markers:
            return None

        # Use first marker to extract the stamp (offsets from marker center)
        mr, mc = markers[0]
        # Determine stamp radius by scanning the output around this marker
        # Find all non-bg output cells that are close to this marker
        # (and not closer to any other marker)
        stamp_offsets = {}  # (dr, dc) -> color
        max_radius = min(h, w) // 2
        for dr in range(-max_radius, max_radius + 1):
            for dc in range(-max_radius, max_radius + 1):
                nr, nc = mr + dr, mc + dc
                if 0 <= nr < h and 0 <= nc < w:
                    val = ro[nr][nc]
                    if val != bg:
                        # Check this cell isn't closer to another marker
                        closest = min(markers, key=lambda m: abs(m[0] - nr) + abs(m[1] - nc))
                        if closest == (mr, mc):
                            stamp_offsets[(dr, dc)] = val

        if not stamp_offsets:
            return None

        # Verify the stamp works for ALL markers in ALL pairs
        for pair in pairs:
            ri = pair.input_grid.raw
            ro = pair.output_grid.raw
            h, w = len(ri), len(ri[0])

            pair_markers = [(r, c) for r in range(h) for c in range(w) if ri[r][c] == marker_color]

            # Build predicted output
            pred = [[bg] * w for _ in range(h)]
            for pmr, pmc in pair_markers:
                for (dr, dc), clr in stamp_offsets.items():
                    nr, nc = pmr + dr, pmc + dc
                    if 0 <= nr < h and 0 <= nc < w:
                        pred[nr][nc] = clr

            if pred != ro:
                return None

        return {
            "type": "stamp_pattern",
            "confidence": 1.0,
            "bg": bg,
            "marker_color": marker_color,
            "stamp_offsets": {f"{dr},{dc}": clr for (dr, dc), clr in stamp_offsets.items()},
        }

    def _find_colored_rects(self, grid, bg=0):
        """Find all solid or framed rectangular blocks of one color on bg."""
        h = len(grid)
        w = len(grid[0]) if grid else 0
        visited = [[False] * w for _ in range(h)]
        rects = []

        for r in range(h):
            for c in range(w):
                if grid[r][c] != bg and not visited[r][c]:
                    color = grid[r][c]
                    # Find extent of this colored rectangle (border color)
                    # Scan right for width
                    cw = 0
                    while c + cw < w and grid[r][c + cw] == color:
                        cw += 1
                    # Scan down for height
                    ch = 0
                    ok = True
                    while r + ch < h and ok:
                        if grid[r + ch][c] == color:
                            ch += 1
                        else:
                            ok = False
                    # Check this forms a valid rect (at least border is colored)
                    if ch >= 2 and cw >= 2:
                        # Verify top and bottom rows are all this color
                        top_ok = all(grid[r][c + j] == color for j in range(cw))
                        bot_ok = all(grid[r + ch - 1][c + j] == color for j in range(cw))
                        left_ok = all(grid[r + i][c] == color for i in range(ch))
                        right_ok = all(grid[r + i][c + cw - 1] == color for i in range(ch))
                        if top_ok and bot_ok and left_ok and right_ok:
                            # Interior must be either all-color (solid) or has bg (frame)
                            interior_ok = True
                            for ir in range(r + 1, r + ch - 1):
                                for ic in range(c + 1, c + cw - 1):
                                    v = grid[ir][ic]
                                    if v != color and v != bg:
                                        interior_ok = False
                                        break
                                if not interior_ok:
                                    break
                            if interior_ok:
                                rects.append({"r": r, "c": c, "h": ch, "w": cw, "color": color})
                                for ir in range(r, r + ch):
                                    for ic in range(c, c + cw):
                                        visited[ir][ic] = True
                                continue
                    # Mark this cell visited even if not a rectangle
                    visited[r][c] = True

        return rects

    # ---- strategy: global color swap (cell-level 1:1 remap) ---------------

    def _try_global_color_swap(self, task):
        """
        Detect: every cell's color maps to exactly one output color (1:1 remap).
        Works at cell level, not group level, so handles grids where all cells
        change and form one big connected component.
        Category: global color substitution, color permutation, fixed swap tables.
        """
        if task is None:
            return None
        pairs = task.example_pairs
        if not pairs:
            return None

        # Grid sizes must be preserved
        for pair in pairs:
            ri, ro = pair.input_grid.raw, pair.output_grid.raw
            if len(ri) != len(ro):
                return None
            if (len(ri[0]) if ri else 0) != (len(ro[0]) if ro else 0):
                return None

        # Build per-cell color mapping across all pairs
        mapping = {}
        for pair in pairs:
            ri, ro = pair.input_grid.raw, pair.output_grid.raw
            for r in range(len(ri)):
                for c in range(len(ri[0])):
                    ic, oc = ri[r][c], ro[r][c]
                    if ic in mapping:
                        if mapping[ic] != oc:
                            return None  # inconsistent
                    else:
                        mapping[ic] = oc

        # Must actually change something (not identity)
        if all(k == v for k, v in mapping.items()):
            return None

        # Verify: applying the mapping reproduces all outputs exactly
        for pair in pairs:
            ri, ro = pair.input_grid.raw, pair.output_grid.raw
            for r in range(len(ri)):
                for c in range(len(ri[0])):
                    if mapping.get(ri[r][c], ri[r][c]) != ro[r][c]:
                        return None

        return {
            "type": "global_color_swap",
            "mapping": {str(k): v for k, v in mapping.items()},
            "confidence": 0.85,
        }

    # ---- strategy: quadrant extract (separator lines -> tile shapes) -------

    def _try_quadrant_extract(self, task):
        """
        Detect: input grid divided into quadrants by a full-span horizontal row
        and vertical column of the same non-zero color (separator). Sep color may
        vary per pair. Each quadrant has one small shape. Output tiles them 2x2.
        Category: separator-based quadrant extraction and reassembly.
        """
        if task is None:
            return None
        pairs = task.example_pairs
        if not pairs:
            return None

        def find_separators(raw):
            """Find separator row and column (full-span row/col of same non-zero color)."""
            h = len(raw)
            w = len(raw[0]) if raw else 0
            sr, sc, sclr = None, None, None
            for r in range(h):
                vals = set(raw[r])
                if len(vals) == 1 and 0 not in vals:
                    sr = r
                    sclr = raw[r][0]
                    break
            if sr is None or sclr is None:
                return None, None, None
            for c in range(w):
                if all(raw[r][c] == sclr for r in range(h)):
                    sc = c
                    break
            return sr, sc, sclr

        def extract_shape(raw, r_start, r_end, c_start, c_end, sep_clr):
            """Extract tight bounding box of non-zero non-sep cells in a region."""
            cells = []
            for r in range(r_start, r_end):
                for c in range(c_start, c_end):
                    if raw[r][c] != 0 and raw[r][c] != sep_clr:
                        cells.append((r - r_start, c - c_start, raw[r][c]))
            if not cells:
                return None
            min_r = min(r for r, c, v in cells)
            max_r = max(r for r, c, v in cells)
            min_c = min(c for r, c, v in cells)
            max_c = max(c for r, c, v in cells)
            sh = max_r - min_r + 1
            sw = max_c - min_c + 1
            shape = [[0] * sw for _ in range(sh)]
            for r, c, v in cells:
                shape[r - min_r][c - min_c] = v
            return shape

        shape_h = None
        shape_w = None
        for pair in pairs:
            ri = pair.input_grid.raw
            ro = pair.output_grid.raw
            h, w = len(ri), len(ri[0]) if ri else 0

            sr, sc, sclr = find_separators(ri)
            if sr is None or sc is None:
                return None

            quads = [
                extract_shape(ri, 0, sr, 0, sc, sclr),
                extract_shape(ri, 0, sr, sc + 1, w, sclr),
                extract_shape(ri, sr + 1, h, 0, sc, sclr),
                extract_shape(ri, sr + 1, h, sc + 1, w, sclr),
            ]

            if any(q is None for q in quads):
                return None

            shapes_h = set(len(q) for q in quads)
            shapes_w = set(len(q[0]) for q in quads)
            if len(shapes_h) != 1 or len(shapes_w) != 1:
                return None

            qh, qw = len(quads[0]), len(quads[0][0])
            if shape_h is None:
                shape_h = qh
                shape_w = qw
            elif qh != shape_h or qw != shape_w:
                return None

            # Verify output = 2x2 tile of extracted shapes
            oh, ow = len(ro), len(ro[0]) if ro else 0
            if oh != shape_h * 2 or ow != shape_w * 2:
                return None

            expected = [[0] * (shape_w * 2) for _ in range(shape_h * 2)]
            for qi, (dr, dc) in enumerate([(0, 0), (0, shape_w), (shape_h, 0), (shape_h, shape_w)]):
                for r in range(shape_h):
                    for c in range(shape_w):
                        expected[dr + r][dc + c] = quads[qi][r][c]
            if expected != ro:
                return None

        return {
            "type": "quadrant_extract",
            "shape_h": shape_h,
            "shape_w": shape_w,
            "confidence": 0.9,
        }

    # ---- strategy: key color swap (2x2 key defines pairwise swaps) ---------

    def _try_key_color_swap(self, task):
        """
        Detect: a 2x2 key block in the top-left corner defines color swap pairs.
        Key = [[A, B], [C, D]]. Swap rule: A<->B, C<->D applied to all non-bg
        cells outside the key. Grid size is preserved; only colors change.
        Category: key-driven color permutation / lookup-table recoloring.
        """
        if task is None:
            return None
        pairs = task.example_pairs
        if not pairs:
            return None

        for pair in pairs:
            ri, ro = pair.input_grid.raw, pair.output_grid.raw
            h, w = len(ri), len(ri[0]) if ri else 0
            oh, ow = len(ro), len(ro[0]) if ro else 0
            if h != oh or w != ow or h < 3 or w < 3:
                return None

            # Check 2x2 key exists (4 distinct non-zero colors)
            a, b, c, d = ri[0][0], ri[0][1], ri[1][0], ri[1][1]
            if len({a, b, c, d}) != 4:
                return None
            if 0 in {a, b, c, d}:
                return None

            # Key must be preserved in output
            if ro[0][0] != a or ro[0][1] != b or ro[1][0] != c or ro[1][1] != d:
                return None

            # Build swap mapping: A<->B, C<->D
            swap = {a: b, b: a, c: d, d: c}

            # Verify: every non-zero cell outside key is swapped correctly
            for r in range(h):
                for col in range(w):
                    # Skip the 2x2 key area
                    if r < 2 and col < 2:
                        continue
                    iv = ri[r][col]
                    ov = ro[r][col]
                    if iv == 0:
                        if ov != 0:
                            return None
                    else:
                        if swap.get(iv, iv) != ov:
                            return None

        return {
            "type": "key_color_swap",
            "confidence": 0.9,
        }


    # ---- strategy: mirror symmetric recolor --------------------------------

    def _try_mirror_symmetric_recolor(self, task):
        """
        Detect: grid has one non-zero color (e.g. 5) on background 0. For each
        row, cells whose mirror partner about the grid center also has the same
        color are recolored to a new color (e.g. 1). Unpaired cells stay.
        Category: bilateral symmetry detection / selective recoloring.
        """
        if task is None:
            return None
        pairs = task.example_pairs
        if not pairs:
            return None

        for pair in pairs:
            ri, ro = pair.input_grid.raw, pair.output_grid.raw
            h, w = len(ri), len(ri[0]) if ri else 0
            oh, ow = len(ro), len(ro[0]) if ro else 0
            if h != oh or w != ow:
                return None

        # Detect: input has exactly one non-zero color, output has that + one new
        first_in = pairs[0].input_grid.raw
        first_out = pairs[0].output_grid.raw
        h, w = len(first_in), len(first_in[0])

        in_colors = set()
        for row in first_in:
            for v in row:
                if v != 0:
                    in_colors.add(v)
        if len(in_colors) != 1:
            return None
        src_color = in_colors.pop()

        out_colors = set()
        for row in first_out:
            for v in row:
                if v != 0 and v != src_color:
                    out_colors.add(v)
        if len(out_colors) != 1:
            return None
        dst_color = out_colors.pop()

        # Verify all pairs: symmetric cells -> dst_color, asymmetric -> stay
        for pair in pairs:
            ri, ro = pair.input_grid.raw, pair.output_grid.raw
            h, w = len(ri), len(ri[0])
            for r in range(h):
                for c in range(w):
                    iv = ri[r][c]
                    ov = ro[r][c]
                    mirror_c = w - 1 - c
                    if iv == src_color:
                        has_mirror = ri[r][mirror_c] == src_color
                        if has_mirror:
                            if ov != dst_color:
                                return None
                        else:
                            if ov != src_color:
                                return None
                    else:
                        if ov != iv:
                            return None

        return {
            "type": "mirror_symmetric_recolor",
            "src_color": src_color,
            "dst_color": dst_color,
            "confidence": 0.95,
        }

    # ---- strategy: bar frame gravity -----------------------------------------

    def _try_bar_frame_gravity(self, task):
        """
        Detect: grid has 4 colored bars (2 vertical full-height, 2 horizontal
        full-width) forming a frame. Scattered cells of one bar's color appear
        inside the center section. Output = center section with bars as border,
        scattered cells cast shadows toward the matching bar.
        Category: frame extraction with directional gravity / shadow projection.
        """
        if task is None:
            return None
        pairs = task.example_pairs
        if not pairs:
            return None

        rule_info = None
        for pair in pairs:
            ri = pair.input_grid.raw
            ro = pair.output_grid.raw
            h, w = len(ri), len(ri[0]) if ri else 0

            info = self._detect_bar_frame(ri, h, w)
            if info is None:
                return None

            # Verify output matches
            predicted = self._apply_bar_frame_gravity_raw(info, ri, h, w)
            if predicted is None or predicted != ro:
                return None

            if rule_info is None:
                rule_info = info

        return {
            "type": "bar_frame_gravity",
            "confidence": 0.95,
        }

    def _detect_bar_frame(self, grid, h, w):
        """Find 4 bars (2 vertical, 2 horizontal) and the gravity direction."""
        # Find vertical bars: columns where most cells are one non-zero color
        vcols = []
        for c in range(w):
            counts = {}
            for r in range(h):
                v = grid[r][c]
                if v != 0:
                    counts[v] = counts.get(v, 0) + 1
            if counts:
                dominant = max(counts, key=counts.get)
                # Allow a few cells with different colors (from bar intersections)
                if counts[dominant] >= h - 6:
                    vcols.append((c, dominant))

        # Find horizontal bars: rows where most cells are one non-zero color
        hrows = []
        for r in range(h):
            counts = {}
            for c in range(w):
                v = grid[r][c]
                if v != 0:
                    counts[v] = counts.get(v, 0) + 1
            if counts:
                dominant = max(counts, key=counts.get)
                if counts[dominant] >= w - 6:
                    hrows.append((r, dominant))

        if len(vcols) < 2 or len(hrows) < 2:
            return None

        # Take leftmost and rightmost vertical bars
        vcols.sort()
        left_col, left_color = vcols[0]
        right_col, right_color = vcols[-1]
        if left_col >= right_col or left_color == right_color:
            return None

        # Take topmost and bottommost horizontal bars
        hrows.sort()
        top_row, top_color = hrows[0]
        bot_row, bot_color = hrows[-1]
        if top_row >= bot_row or top_color == bot_color:
            return None

        # All 4 bar colors must be distinct
        bar_colors = {left_color, right_color, top_color, bot_color}
        if len(bar_colors) != 4:
            return None

        # Center section
        cr0, cr1 = top_row + 1, bot_row - 1
        cc0, cc1 = left_col + 1, right_col - 1
        if cr0 > cr1 or cc0 > cc1:
            return None

        # Find scattered color in center section (must match one bar)
        scattered = set()
        for r in range(cr0, cr1 + 1):
            for c in range(cc0, cc1 + 1):
                v = grid[r][c]
                if v != 0 and v in bar_colors:
                    scattered.add(v)

        if len(scattered) != 1:
            return None
        scat_color = scattered.pop()

        # Determine gravity direction
        if scat_color == top_color:
            direction = "up"
        elif scat_color == bot_color:
            direction = "down"
        elif scat_color == left_color:
            direction = "left"
        elif scat_color == right_color:
            direction = "right"
        else:
            return None

        return {
            "left_col": left_col, "left_color": left_color,
            "right_col": right_col, "right_color": right_color,
            "top_row": top_row, "top_color": top_color,
            "bot_row": bot_row, "bot_color": bot_color,
            "cr0": cr0, "cr1": cr1, "cc0": cc0, "cc1": cc1,
            "scat_color": scat_color, "direction": direction,
        }

    def _apply_bar_frame_gravity_raw(self, info, grid, h, w):
        """Build the output grid for bar_frame_gravity."""
        cr0, cr1 = info["cr0"], info["cr1"]
        cc0, cc1 = info["cc0"], info["cc1"]
        ch = cr1 - cr0 + 1
        cw = cc1 - cc0 + 1
        direction = info["direction"]
        scat_color = info["scat_color"]
        left_color = info["left_color"]
        right_color = info["right_color"]
        top_color = info["top_color"]
        bot_color = info["bot_color"]

        # Extract center section
        center = []
        for r in range(cr0, cr1 + 1):
            row = []
            for c in range(cc0, cc1 + 1):
                v = grid[r][c]
                row.append(v if v == scat_color else 0)
            center.append(row)

        # Apply shadow/gravity: fill from the cell farthest from the gravity
        # bar all the way to the bar edge
        shadow = [[0] * cw for _ in range(ch)]
        if direction == "down":
            # Shadow extends from topmost (min row) scattered cell down to bottom
            for c in range(cw):
                top_most = ch
                for r in range(ch):
                    if center[r][c] == scat_color:
                        top_most = min(top_most, r)
                if top_most < ch:
                    for r in range(top_most, ch):
                        shadow[r][c] = scat_color
        elif direction == "up":
            # Shadow extends from bottommost (max row) scattered cell up to top
            for c in range(cw):
                bot_most = -1
                for r in range(ch):
                    if center[r][c] == scat_color:
                        bot_most = max(bot_most, r)
                if bot_most >= 0:
                    for r in range(0, bot_most + 1):
                        shadow[r][c] = scat_color
        elif direction == "right":
            # Shadow extends from leftmost (min col) scattered cell right to edge
            for r in range(ch):
                left_most = cw
                for c in range(cw):
                    if center[r][c] == scat_color:
                        left_most = min(left_most, c)
                if left_most < cw:
                    for c in range(left_most, cw):
                        shadow[r][c] = scat_color
        elif direction == "left":
            # Shadow extends from rightmost (max col) scattered cell left to edge
            for r in range(ch):
                right_most = -1
                for c in range(cw):
                    if center[r][c] == scat_color:
                        right_most = max(right_most, c)
                if right_most >= 0:
                    for c in range(0, right_most + 1):
                        shadow[r][c] = scat_color

        # Build output with border
        out_h = ch + 2
        out_w = cw + 2
        output = [[0] * out_w for _ in range(out_h)]

        # Fill border: horizontal bars first, then vertical bars overwrite edges
        for c in range(out_w):
            output[0][c] = top_color
            output[out_h - 1][c] = bot_color
        for r in range(out_h):
            output[r][0] = left_color
            output[r][out_w - 1] = right_color

        # Corners come from bar intersections in the original grid
        left_col = info["left_col"]
        right_col = info["right_col"]
        top_row = info["top_row"]
        bot_row = info["bot_row"]
        output[0][0] = grid[top_row][left_col]
        output[0][out_w - 1] = grid[top_row][right_col]
        output[out_h - 1][0] = grid[bot_row][left_col]
        output[out_h - 1][out_w - 1] = grid[bot_row][right_col]

        # Fill interior with shadow
        for r in range(ch):
            for c in range(cw):
                output[r + 1][c + 1] = shadow[r][c]

        return output

    # ---- strategy: cross center mark -----------------------------------------

    def _try_cross_center_mark(self, task):
        """
        Detect: background color with scattered 1-pixel pairs (adjacent horizontal
        or vertical). Some sets of 4 pairs form a cross pattern equidistant from
        a center cell. That center gets marked with color 4.
        Category: geometric crosshair detection / center marking.
        """
        if task is None:
            return None
        pairs = task.example_pairs
        if not pairs:
            return None

        # Check all pairs: same grid size, only background and one foreground color
        bg = None
        fg = None
        mark_color = None
        for pair in pairs:
            ri, ro = pair.input_grid.raw, pair.output_grid.raw
            h, w = len(ri), len(ri[0]) if ri else 0
            oh, ow = len(ro), len(ro[0]) if ro else 0
            if h != oh or w != ow:
                return None

            in_colors = set()
            for row in ri:
                for v in row:
                    in_colors.add(v)
            out_only = set()
            for r in range(h):
                for c in range(w):
                    if ro[r][c] != ri[r][c]:
                        out_only.add(ro[r][c])

            if len(in_colors) != 2:
                return None
            if len(out_only) != 1:
                return None

            # bg is the most common, fg is the less common
            counts = {}
            for row in ri:
                for v in row:
                    counts[v] = counts.get(v, 0) + 1
            sorted_colors = sorted(counts, key=counts.get, reverse=True)
            this_bg = sorted_colors[0]
            this_fg = sorted_colors[1]
            this_mark = out_only.pop()

            if bg is None:
                bg, fg, mark_color = this_bg, this_fg, this_mark
            elif this_bg != bg or this_fg != fg or this_mark != mark_color:
                return None

        # Verify the cross-center rule on all pairs
        for pair in pairs:
            ri, ro = pair.input_grid.raw, pair.output_grid.raw
            h, w = len(ri), len(ri[0])

            predicted = self._compute_cross_centers(ri, h, w, bg, fg, mark_color)
            if predicted != ro:
                return None

        return {
            "type": "cross_center_mark",
            "bg": bg,
            "fg": fg,
            "mark_color": mark_color,
            "confidence": 0.95,
        }

    def _compute_cross_centers(self, grid, h, w, bg, fg, mark_color):
        """Find cross centers and produce the marked output."""
        raw = grid if isinstance(grid, list) else grid.raw

        # Find all fg-pairs (adjacent horizontal or vertical)
        h_pairs = set()  # horizontal pairs: (r, min_c)
        v_pairs = set()  # vertical pairs: (min_r, c)
        for r in range(h):
            for c in range(w):
                if raw[r][c] == fg:
                    # horizontal pair
                    if c + 1 < w and raw[r][c + 1] == fg:
                        h_pairs.add((r, c))
                    # vertical pair
                    if r + 1 < h and raw[r + 1][c] == fg:
                        v_pairs.add((r, c))

        # Index pairs by row (for h_pairs) and column (for v_pairs)
        h_by_row = {}
        for (r, c) in h_pairs:
            h_by_row.setdefault(r, []).append(c)
        v_by_col = {}
        for (r, c) in v_pairs:
            v_by_col.setdefault(c, []).append(r)

        output = [row[:] for row in raw]

        # For each cell that is background, check cross condition
        for r in range(h):
            for c in range(w):
                if raw[r][c] != bg:
                    continue

                # Check all distances d from 1 up
                found = False
                for d in range(1, max(h, w)):
                    # Need vertical pair above: pair at (r-d, c) means
                    # v_pair starts at r-d, so (r-d, c) in v_pairs
                    # Actually: pair at (r-d-1, c) and (r-d, c), so start = r-d-1
                    has_above = c in v_by_col and (r - d - 1) in set(v_by_col[c])
                    if not has_above:
                        continue

                    # Vertical pair below: starts at (r+d, c)
                    has_below = c in v_by_col and (r + d) in set(v_by_col[c])
                    if not has_below:
                        continue

                    # Horizontal pair left: pair at row r, starting at (r, c-d-1)
                    has_left = r in h_by_row and (c - d - 1) in set(h_by_row[r])
                    if not has_left:
                        continue

                    # Horizontal pair right: starts at (r, c+d)
                    has_right = r in h_by_row and (c + d) in set(h_by_row[r])
                    if not has_right:
                        continue

                    output[r][c] = mark_color
                    found = True
                    break

        return output

    # ---- strategy 47: corner L-extension ---------------------------------

    def _try_corner_L_extend(self, task):
        """
        Detect: sparse colored dots on a background grid. Each dot extends
        its color to the nearest grid corner in an L-shape (row arm + column
        arm toward that corner).
        Category: directional point-to-edge expansion.
        """
        if task is None:
            return None
        pairs = task.example_pairs
        if not pairs:
            return None

        from collections import Counter

        ri0 = pairs[0].input_grid.raw
        flat = [v for row in ri0 for v in row]
        bg = Counter(flat).most_common(1)[0][0]

        for pair in pairs:
            ri, ro = pair.input_grid.raw, pair.output_grid.raw
            h, w = len(ri), len(ri[0])
            oh, ow = len(ro), len(ro[0])
            if h != oh or w != ow:
                return None

            # Collect non-bg dots
            dots = []
            for r in range(h):
                for c in range(w):
                    if ri[r][c] != bg:
                        dots.append((r, c, ri[r][c]))

            if not dots:
                return None

            # All dots must be isolated (no non-bg 4-neighbor)
            non_bg = set((r, c) for r, c, _ in dots)
            for r, c, _ in dots:
                for dr, dc in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                    if (r + dr, c + dc) in non_bg:
                        return None

            # Build predicted output
            pred = [[bg] * w for _ in range(h)]
            for r, c, color in dots:
                # Find nearest corner by Manhattan distance
                corners = [
                    (r + c, 'TL'),
                    (r + (w - 1 - c), 'TR'),
                    ((h - 1 - r) + c, 'BL'),
                    ((h - 1 - r) + (w - 1 - c), 'BR'),
                ]
                corners.sort(key=lambda x: x[0])
                _, nearest = corners[0]

                if nearest == 'TL':
                    for cc in range(0, c + 1):
                        pred[r][cc] = color
                    for rr in range(0, r):
                        pred[rr][c] = color
                elif nearest == 'TR':
                    for cc in range(c, w):
                        pred[r][cc] = color
                    for rr in range(0, r):
                        pred[rr][c] = color
                elif nearest == 'BL':
                    for cc in range(0, c + 1):
                        pred[r][cc] = color
                    for rr in range(r + 1, h):
                        pred[rr][c] = color
                elif nearest == 'BR':
                    for cc in range(c, w):
                        pred[r][cc] = color
                    for rr in range(r + 1, h):
                        pred[rr][c] = color

            if pred != ro:
                return None

        return {"type": "corner_L_extend", "bg": bg, "confidence": 1.0}

    # ---- strategy 48: rotation quad tile 4x ------------------------------

    def _try_rotation_quad_tile_4x(self, task):
        """
        Detect: NxN input -> 4Nx4N output. The output is a 4x4 arrangement
        of NxN tiles grouped into 2x2 quadrants, each quadrant a different
        rotation: TL=180°, TR=90°CW, BL=90°CCW, BR=0° (identity).
        Category: rotation-symmetry tiling / kaleidoscope expansion.
        """
        if task is None:
            return None
        pairs = task.example_pairs
        if not pairs:
            return None

        for pair in pairs:
            g0, g1 = pair.input_grid, pair.output_grid
            if g0 is None or g1 is None:
                return None
            ri, ro = g0.raw, g1.raw
            h, w = len(ri), len(ri[0])
            oh, ow = len(ro), len(ro[0])
            if h != w:
                return None
            if oh != 4 * h or ow != 4 * w:
                return None

            n = h
            # Build rotations
            rot0 = ri
            rot180 = [[ri[n - 1 - r][n - 1 - c] for c in range(n)] for r in range(n)]
            rot_cw = [[ri[n - 1 - c][r] for c in range(n)] for r in range(n)]
            rot_ccw = [[ri[c][n - 1 - r] for c in range(n)] for r in range(n)]

            # Quadrant mapping: TL=180°, TR=CW, BL=CCW, BR=0°
            quads = {
                (0, 0): rot180, (0, 1): rot180, (1, 0): rot180, (1, 1): rot180,
                (0, 2): rot_cw, (0, 3): rot_cw, (1, 2): rot_cw, (1, 3): rot_cw,
                (2, 0): rot_ccw, (2, 1): rot_ccw, (3, 0): rot_ccw, (3, 1): rot_ccw,
                (2, 2): rot0, (2, 3): rot0, (3, 2): rot0, (3, 3): rot0,
            }

            for tr in range(4):
                for tc in range(4):
                    tile = quads[(tr, tc)]
                    for r in range(n):
                        for c in range(n):
                            if ro[tr * n + r][tc * n + c] != tile[r][c]:
                                return None

        return {"type": "rotation_quad_tile_4x", "confidence": 1.0}

    # ---- strategy 49: rectangle outline decorate -------------------------

    def _try_rect_outline_decorate(self, task):
        """
        Detect: background with shapes of a foreground color. Square-shaped
        outlines (closed rectangle borders where H==W, border 1-cell wide,
        interior is bg) get color-2 marks extending from each corner.
        Category: geometric shape classification + corner marking.
        """
        if task is None:
            return None
        pairs = task.example_pairs
        if not pairs:
            return None

        from collections import Counter

        ri0 = pairs[0].input_grid.raw
        flat = [v for row in ri0 for v in row]
        bg = Counter(flat).most_common(1)[0][0]

        mark_color = None

        for pair in pairs:
            ri, ro = pair.input_grid.raw, pair.output_grid.raw
            h, w = len(ri), len(ri[0])
            oh, ow = len(ro), len(ro[0])
            if h != oh or w != ow:
                return None

            # Determine mark color from changed cells
            mc = set()
            for r in range(h):
                for c in range(w):
                    if ro[r][c] != ri[r][c]:
                        mc.add(ro[r][c])
            if len(mc) != 1:
                return None
            this_mark = mc.pop()
            if mark_color is None:
                mark_color = this_mark
            elif this_mark != mark_color:
                return None

            pred = self._compute_rect_outline_decorate(ri, h, w, bg, mark_color)
            if pred != ro:
                return None

        return {
            "type": "rect_outline_decorate",
            "bg": bg,
            "mark_color": mark_color,
            "confidence": 0.95,
        }

    def _compute_rect_outline_decorate(self, grid, h, w, bg, mark_color):
        """Find square outline components and add corner marks."""
        raw = grid if isinstance(grid, list) else grid.raw
        output = [row[:] for row in raw]

        # Find connected components of non-bg cells
        visited = [[False] * w for _ in range(h)]
        for r in range(h):
            for c in range(w):
                if raw[r][c] == bg or visited[r][c]:
                    continue
                # BFS to find component
                color = raw[r][c]
                comp = []
                queue = [(r, c)]
                visited[r][c] = True
                while queue:
                    cr, cc = queue.pop(0)
                    comp.append((cr, cc))
                    for dr, dc in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                        nr, nc = cr + dr, cc + dc
                        if 0 <= nr < h and 0 <= nc < w and not visited[nr][nc] and raw[nr][nc] == color:
                            visited[nr][nc] = True
                            queue.append((nr, nc))

                # Check if component forms a square outline
                if len(comp) < 4:
                    continue
                comp_set = set(comp)
                min_r = min(r for r, c in comp)
                max_r = max(r for r, c in comp)
                min_c = min(c for r, c in comp)
                max_c = max(c for r, c in comp)
                bh = max_r - min_r + 1
                bw = max_c - min_c + 1
                if bh != bw or bh < 2:
                    continue

                # Check that border cells are all present
                border = set()
                for rr in range(min_r, max_r + 1):
                    for cc in range(min_c, max_c + 1):
                        if rr == min_r or rr == max_r or cc == min_c or cc == max_c:
                            border.add((rr, cc))

                if not border.issubset(comp_set):
                    continue

                # Check that interior is bg (if interior exists)
                interior_ok = True
                for rr in range(min_r + 1, max_r):
                    for cc in range(min_c + 1, max_c):
                        if (rr, cc) in comp_set:
                            interior_ok = False
                            break
                    if not interior_ok:
                        break
                if not interior_ok:
                    continue

                # Component equals border (no extra cells outside border)
                if comp_set != border:
                    continue

                # It's a valid square outline — add corner marks
                # Each corner gets two marks: one extending the vertical edge,
                # one extending the horizontal edge (NOT the diagonal)
                corners = [
                    (min_r, min_c, -1, -1),  # TL: up and left
                    (min_r, max_c, -1, 1),   # TR: up and right
                    (max_r, min_c, 1, -1),   # BL: down and left
                    (max_r, max_c, 1, 1),    # BR: down and right
                ]
                for cr, cc, dr, dc in corners:
                    # Extend vertical edge direction
                    nr, nc = cr + dr, cc
                    if 0 <= nr < h and 0 <= nc < w:
                        output[nr][nc] = mark_color
                    # Extend horizontal edge direction
                    nr2, nc2 = cr, cc + dc
                    if 0 <= nr2 < h and 0 <= nc2 < w:
                        output[nr2][nc2] = mark_color

        return output

    # ---- strategy 50: most frequent cross color --------------------------

    def _try_most_frequent_cross_color(self, task):
        """
        Detect: large grid with several cross-shaped patterns (color X above,
        below, left, right of a center cell with value 4). Output is 1x1 grid
        containing the color X that appears in the most crosses.
        Category: cross pattern counting / majority vote.
        """
        if task is None:
            return None
        pairs = task.example_pairs
        if not pairs:
            return None

        center_val = 4  # the center of each cross is always 4

        for pair in pairs:
            ri, ro = pair.input_grid.raw, pair.output_grid.raw
            # Output must be 1x1
            if len(ro) != 1 or len(ro[0]) != 1:
                return None

            h, w = len(ri), len(ri[0])

            # Find crosses: cell with value 4 surrounded by same-color
            # orthogonal neighbors
            cross_colors = []
            for r in range(1, h - 1):
                for c in range(1, w - 1):
                    if ri[r][c] != center_val:
                        continue
                    up, down, left, right = ri[r - 1][c], ri[r + 1][c], ri[r][c - 1], ri[r][c + 1]
                    if up == down == left == right and up != center_val:
                        cross_colors.append(up)

            if not cross_colors:
                return None

            # Most frequent color
            from collections import Counter
            counts = Counter(cross_colors)
            majority = counts.most_common(1)[0][0]

            if ro[0][0] != majority:
                return None

        return {"type": "most_frequent_cross_color", "confidence": 1.0}

    # ---- strategy 51: grid separator invert --------------------------------

    def _try_grid_separator_invert(self, task):
        """
        Detect: grid divided by 0-separator rows/cols into equal-sized
        quadrants. A base pattern tiles some quadrants, others are blank
        (all minority color). 5s mark corruption. Output inverts:
        base -> all-majority, blank -> base, separators cleaned.
        Category: grid partition inversion with noise.
        """
        if task is None:
            return None
        pairs = task.example_pairs
        if not pairs:
            return None

        for pair in pairs:
            ri, ro = pair.input_grid.raw, pair.output_grid.raw
            h, w = len(ri), len(ri[0]) if ri else 0
            if h != len(ro) or w != (len(ro[0]) if ro else 0):
                return None

            result = self._verify_sep_invert(ri, ro, h, w)
            if result is None:
                return None

        return {"type": "grid_separator_invert", "confidence": 0.95}

    def _verify_sep_invert(self, ri, ro, h, w):
        """Verify one input/output pair matches separator-invert pattern."""
        sep_rows = [r for r in range(h)
                    if all(ri[r][c] in (0, 5) for c in range(w))]
        sep_cols = [c for c in range(w)
                    if all(ri[r][c] in (0, 5) for r in range(h))]
        if not sep_rows or not sep_cols:
            return None

        row_bounds = self._sep_bounds(sep_rows, h)
        col_bounds = self._sep_bounds(sep_cols, w)
        if len(row_bounds) < 2 or len(col_bounds) < 2:
            return None

        qh = row_bounds[0][1] - row_bounds[0][0]
        qw = col_bounds[0][1] - col_bounds[0][0]
        if qh < 1 or qw < 1:
            return None
        if any(b - a != qh for a, b in row_bounds):
            return None
        if any(b - a != qw for a, b in col_bounds):
            return None

        quads_in = self._extract_quads(ri, row_bounds, col_bounds, qh, qw)
        quads_out = self._extract_quads(ro, row_bounds, col_bounds, qh, qw)

        # Find clean base pattern (no 5, not uniform)
        base = None
        for qrow in quads_in:
            for q in qrow:
                if any(q[r][c] == 5 for r in range(qh) for c in range(qw)):
                    continue
                colors = set(q[r][c] for r in range(qh) for c in range(qw))
                if len(colors) > 1:
                    if base is None:
                        base = [row[:] for row in q]
                    elif q != base:
                        return None
        if base is None:
            return None

        cc = {}
        for r in range(qh):
            for c in range(qw):
                cc[base[r][c]] = cc.get(base[r][c], 0) + 1
        sc = sorted(cc, key=cc.get, reverse=True)
        if len(sc) < 2:
            return None
        maj, mnr = sc[0], sc[1]

        all_maj = [[maj] * qw for _ in range(qh)]

        for qi in range(len(row_bounds)):
            for qj in range(len(col_bounds)):
                q = quads_in[qi][qj]
                qtype = self._classify_quad(q, base, mnr, qh, qw)
                if qtype is None:
                    return None
                expected = all_maj if qtype == 'base' else base
                if quads_out[qi][qj] != expected:
                    return None

        for sr in sep_rows:
            if any(ro[sr][c] != 0 for c in range(w)):
                return None
        for sc_v in sep_cols:
            if any(ro[r][sc_v] != 0 for r in range(h)):
                return None

        return True

    @staticmethod
    def _sep_bounds(seps, size):
        """Convert separator indices to (start, end) bounds for quadrants."""
        bounds = []
        prev = 0
        for s in seps:
            if s > prev:
                bounds.append((prev, s))
            prev = s + 1
        if prev < size:
            bounds.append((prev, size))
        return bounds

    @staticmethod
    def _extract_quads(grid, row_bounds, col_bounds, qh, qw):
        """Extract 2D list of quadrant sub-grids."""
        result = []
        for rs, re in row_bounds:
            row_q = []
            for cs, ce in col_bounds:
                q = [grid[r][cs:ce] for r in range(rs, re)]
                row_q.append(q)
            result.append(row_q)
        return result

    @staticmethod
    def _classify_quad(q, base, minority, qh, qw):
        """Classify a quadrant as 'base' or 'blank'. Returns None on failure."""
        base_ok = True
        blank_ok = True
        for r in range(qh):
            for c in range(qw):
                v = q[r][c]
                if v == 5:
                    continue
                if v != base[r][c]:
                    base_ok = False
                if v != minority:
                    blank_ok = False
        if blank_ok:
            return 'blank'
        if base_ok:
            return 'base'
        return None


    # ---- strategy: zero region classify (edge-touching vs interior 0-regions) ----

    def _try_zero_region_classify(self, task):
        """
        Detect: non-zero cells (walls) stay unchanged. 0-cells are classified
        into two groups by 4-connected flood fill: those whose connected
        component touches the grid edge get one color, fully-enclosed 0-regions
        get a different color.
        Category: boundary / interior region classification.
        """
        if task is None:
            return None
        pairs = task.example_pairs
        if not pairs:
            return None

        exterior_color = None
        interior_color = None

        for pair in pairs:
            g0, g1 = pair.input_grid, pair.output_grid
            if g0 is None or g1 is None:
                return None
            ri, ro = g0.raw, g1.raw
            h, w = len(ri), len(ri[0])
            if h != len(ro) or w != (len(ro[0]) if ro else 0):
                return None

            # Non-zero cells must be unchanged
            for r in range(h):
                for c in range(w):
                    if ri[r][c] != 0 and ri[r][c] != ro[r][c]:
                        return None

            # All 0-cells must change to something
            changed_colors = set()
            for r in range(h):
                for c in range(w):
                    if ri[r][c] == 0:
                        if ro[r][c] == 0:
                            return None  # 0-cell stayed 0 — not this pattern
                        changed_colors.add(ro[r][c])

            if len(changed_colors) != 2:
                return None

            # Find connected components of 0-cells
            visited = [[False] * w for _ in range(h)]
            components = []
            for sr in range(h):
                for sc in range(w):
                    if ri[sr][sc] == 0 and not visited[sr][sc]:
                        comp = []
                        touches_edge = False
                        queue = [(sr, sc)]
                        visited[sr][sc] = True
                        while queue:
                            cr, cc = queue.pop(0)
                            comp.append((cr, cc))
                            if cr == 0 or cr == h - 1 or cc == 0 or cc == w - 1:
                                touches_edge = True
                            for dr, dc in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                                nr, nc = cr + dr, cc + dc
                                if 0 <= nr < h and 0 <= nc < w and not visited[nr][nc] and ri[nr][nc] == 0:
                                    visited[nr][nc] = True
                                    queue.append((nr, nc))
                        components.append((comp, touches_edge))

            # Determine which color goes to edge-touching vs interior
            ec, ic = None, None
            for comp, touches_edge in components:
                out_color = ro[comp[0][0]][comp[0][1]]
                # Verify all cells in component have the same output color
                if not all(ro[r][c] == out_color for r, c in comp):
                    return None
                if touches_edge:
                    if ec is None:
                        ec = out_color
                    elif ec != out_color:
                        return None
                else:
                    if ic is None:
                        ic = out_color
                    elif ic != out_color:
                        return None

            if ec is None or ic is None:
                return None

            if exterior_color is None:
                exterior_color = ec
                interior_color = ic
            elif ec != exterior_color or ic != interior_color:
                return None

        return {
            "type": "zero_region_classify",
            "exterior_color": exterior_color,
            "interior_color": interior_color,
            "confidence": 1.0,
        }

    # ---- strategy: grid intersection vote (large separator grid -> small output) ----

    def _try_grid_intersection_vote(self, task):
        """
        Detect: large input grid with separator rows/cols (all same non-0 color)
        forming a regular lattice. At grid-line intersections, some cells have
        special (non-separator) colors forming two rectangular blocks in a 4x4
        intersection sub-grid. Output is 3x3: each cell is colored if all 4
        bounding intersection corners share the same color, else 0.
        Category: grid-line intersection analysis / voting.
        """
        if task is None:
            return None
        pairs = task.example_pairs
        if not pairs:
            return None

        for pair in pairs:
            g0, g1 = pair.input_grid, pair.output_grid
            if g0 is None or g1 is None:
                return None
            ro = g1.raw
            if len(ro) != 3 or len(ro[0]) != 3:
                return None
            predicted = self._compute_grid_intersection_vote(g0.raw)
            if predicted is None or predicted != ro:
                return None

        return {"type": "grid_intersection_vote", "confidence": 1.0}

    def _compute_grid_intersection_vote(self, raw):
        """Compute 3x3 output from grid-line intersection colors."""
        h = len(raw)
        w = len(raw[0]) if raw else 0
        if h < 5 or w < 5:
            return None

        bg = 0

        # Find grid-line rows: rows with NO background (0) cells
        grid_rows = [r for r in range(h) if all(raw[r][c] != bg for c in range(w))]
        grid_cols = [c for c in range(w) if all(raw[r][c] != bg for r in range(h))]

        if len(grid_rows) < 4 or len(grid_cols) < 4:
            return None

        # Determine separator color: most common color on grid lines
        from collections import Counter
        color_counts = Counter()
        for r in grid_rows:
            for c in range(w):
                color_counts[raw[r][c]] += 1
        for c in grid_cols:
            for r in range(h):
                color_counts[raw[r][c]] += 1
        sep_color = color_counts.most_common(1)[0][0]

        # Find intersections with non-separator colors
        special = {}
        for r in grid_rows:
            for c in grid_cols:
                v = raw[r][c]
                if v != sep_color:
                    ri_idx = grid_rows.index(r)
                    ci_idx = grid_cols.index(c)
                    special[(ri_idx, ci_idx)] = v

        if not special:
            return None

        # Find bounding box of special intersections
        min_ri = min(k[0] for k in special)
        max_ri = max(k[0] for k in special)
        min_ci = min(k[1] for k in special)
        max_ci = max(k[1] for k in special)

        # Must span a 4x4 region of intersection indices
        if max_ri - min_ri != 3 or max_ci - min_ci != 3:
            return None

        # Build 4x4 mini-grid of intersection colors
        mini = [[0] * 4 for _ in range(4)]
        for (ri, ci), v in special.items():
            mini[ri - min_ri][ci - min_ci] = v

        # Map to 3x3 output: each cell gets color if all 4 bounding corners agree
        output = [[0] * 3 for _ in range(3)]
        for r in range(3):
            for c in range(3):
                tl = mini[r][c]
                tr = mini[r][c + 1]
                bl = mini[r + 1][c]
                br = mini[r + 1][c + 1]
                if tl != 0 and tl == tr == bl == br:
                    output[r][c] = tl

        return output

    # ---- strategy: sparse grid compress -----------------------------------

    def _try_sparse_grid_compress(self, task):
        """
        Detect: input grid divides evenly into blocks, each block has exactly
        one non-zero cell.  Output is the compressed grid of those values.
        Category: block-based spatial compression / sparse-to-dense.
        """
        pairs = task.train_pairs if hasattr(task, 'train_pairs') else task.example_pairs
        if not pairs:
            return None

        block_h = block_w = None
        for pair in pairs:
            ig = pair.input_grid.raw
            og = pair.output_grid.raw
            ih, iw = len(ig), len(ig[0])
            oh, ow = len(og), len(og[0])
            if oh == 0 or ow == 0:
                return None
            if ih % oh != 0 or iw % ow != 0:
                return None
            bh = ih // oh
            bw = iw // ow
            if bh < 2 or bw < 2:
                return None
            if block_h is None:
                block_h, block_w = bh, bw
            # Each block must have exactly one non-zero cell matching output
            for br in range(oh):
                for bc in range(ow):
                    nz_val = None
                    nz_count = 0
                    for r in range(br * bh, (br + 1) * bh):
                        for c in range(bc * bw, (bc + 1) * bw):
                            if ig[r][c] != 0:
                                nz_count += 1
                                nz_val = ig[r][c]
                    if nz_count != 1 or nz_val != og[br][bc]:
                        return None

        return {"type": "sparse_grid_compress", "confidence": 1.0}

    # ---- strategy: extract unique shape -----------------------------------

    def _try_extract_unique_shape(self, task):
        """
        Detect: large grid with scattered noise pixels of several colors plus
        one small dense shape of a unique color.  Output = bounding box of
        that shape (only shape-color cells kept, rest 0).
        Category: noise filtering / dense object extraction.
        """
        pairs = task.train_pairs if hasattr(task, 'train_pairs') else task.example_pairs
        if not pairs:
            return None

        for pair in pairs:
            ig = pair.input_grid.raw
            og = pair.output_grid.raw
            ih, iw = len(ig), len(ig[0])
            oh, ow = len(og), len(og[0])
            # Output must be strictly smaller
            if oh >= ih or ow >= iw:
                return None
            # Output colors (besides 0) must be a single color
            out_colors = set()
            for row in og:
                for v in row:
                    if v != 0:
                        out_colors.add(v)
            if len(out_colors) != 1:
                return None
            sc = out_colors.pop()
            # Find bounding box of sc in input
            min_r, max_r = ih, -1
            min_c, max_c = iw, -1
            for r in range(ih):
                for c in range(iw):
                    if ig[r][c] == sc:
                        if r < min_r:
                            min_r = r
                        if r > max_r:
                            max_r = r
                        if c < min_c:
                            min_c = c
                        if c > max_c:
                            max_c = c
            if max_r < 0:
                return None
            bbox_h = max_r - min_r + 1
            bbox_w = max_c - min_c + 1
            if bbox_h != oh or bbox_w != ow:
                return None
            # Extract bbox keeping only shape color
            for dr in range(oh):
                for dc in range(ow):
                    v = ig[min_r + dr][min_c + dc]
                    expected = sc if v == sc else 0
                    if og[dr][dc] != expected:
                        return None

        return {"type": "extract_unique_shape", "confidence": 1.0}

    # ---- strategy: shape match recolor ------------------------------------

    @staticmethod
    def _normalize_component(cells):
        """Normalize a list of (r,c) positions to origin-relative frozenset."""
        if not cells:
            return frozenset()
        min_r = min(r for r, c in cells)
        min_c = min(c for r, c in cells)
        return frozenset((r - min_r, c - min_c) for r, c in cells)

    @staticmethod
    def _color_components(raw, color):
        """Find 4-connected components of a specific color. Returns list of [(r,c),...]."""
        h = len(raw)
        w = len(raw[0]) if raw else 0
        visited = set()
        comps = []
        for r in range(h):
            for c in range(w):
                if raw[r][c] != color or (r, c) in visited:
                    continue
                comp = []
                queue = [(r, c)]
                while queue:
                    cr, cc = queue.pop(0)
                    if (cr, cc) in visited:
                        continue
                    visited.add((cr, cc))
                    comp.append((cr, cc))
                    for dr, dc in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                        nr, nc = cr + dr, cc + dc
                        if 0 <= nr < h and 0 <= nc < w and (nr, nc) not in visited and raw[nr][nc] == color:
                            queue.append((nr, nc))
                comps.append(comp)
        return comps

    def _try_shape_match_recolor(self, task):
        """
        Detect: one 'template color' has shapes that match the forms of
        non-template colored shapes.  Each template shape gets recolored to
        the color of its form-matching reference shape.  Reference shapes
        are unchanged.
        Category: shape matching / template recoloring.
        """
        pairs = task.train_pairs if hasattr(task, 'train_pairs') else task.example_pairs
        if not pairs:
            return None

        template_color = None
        for pair in pairs:
            ig = pair.input_grid.raw
            og = pair.output_grid.raw
            ih, iw = len(ig), len(ig[0])
            oh, ow = len(og), len(og[0])
            if ih != oh or iw != ow:
                return None
            # Find changed cells
            in_colors_changed = set()
            for r in range(ih):
                for c in range(iw):
                    if ig[r][c] != og[r][c]:
                        in_colors_changed.add(ig[r][c])
            if not in_colors_changed:
                return None
            if len(in_colors_changed) != 1:
                return None
            tc = in_colors_changed.pop()
            if tc == 0:
                return None
            if template_color is None:
                template_color = tc
            elif template_color != tc:
                return None

        # Validate shape matching for all pairs
        for pair in pairs:
            ig = pair.input_grid.raw
            og = pair.output_grid.raw
            # Template components
            t_comps = self._color_components(ig, template_color)
            if not t_comps:
                return None
            # Reference colors
            ref_colors = set()
            for row in ig:
                for v in row:
                    if v != 0 and v != template_color:
                        ref_colors.add(v)
            # Build shape -> color map from references
            shape_to_color = {}
            for rc in ref_colors:
                for comp in self._color_components(ig, rc):
                    shape = self._normalize_component(comp)
                    shape_to_color[shape] = rc
            # Each template must match a reference and output must be that color
            for comp in t_comps:
                shape = self._normalize_component(comp)
                if shape not in shape_to_color:
                    return None
                expected = shape_to_color[shape]
                for r, c in comp:
                    if og[r][c] != expected:
                        return None
            # Reference shapes must be unchanged
            for r in range(len(ig)):
                for c in range(len(ig[0])):
                    if ig[r][c] != template_color and ig[r][c] != 0:
                        if og[r][c] != ig[r][c]:
                            return None

        return {"type": "shape_match_recolor", "template_color": template_color, "confidence": 1.0}

    # ---- strategy: L-triomino diagonal extension ---------------------------

    def _try_l_triomino_extend(self, task):
        """
        Detect: L-shaped triominoes (3 cells in a 2x2 bbox) on zero background.
        The missing corner of each triomino's 2x2 bbox is identified, and a
        diagonal line extends from that corner outward until the grid edge.
        Category: directional diagonal extension from L-shaped objects.
        """
        if task is None:
            return None
        pairs = task.example_pairs
        if not pairs:
            return None

        for pair in pairs:
            g0, g1 = pair.input_grid, pair.output_grid
            if g0 is None or g1 is None:
                return None
            ri, ro = g0.raw, g1.raw
            h, w = len(ri), len(ri[0])
            if len(ro) != h or len(ro[0]) != w:
                return None

            # Collect non-zero cells; must be single color
            cells = []
            colors = set()
            for r in range(h):
                for c in range(w):
                    if ri[r][c] != 0:
                        cells.append((r, c))
                        colors.add(ri[r][c])
            if len(colors) != 1 or len(cells) < 3:
                return None
            color = next(iter(colors))
            cell_set = set(cells)

            # Group by 8-connectivity
            used = set()
            triominoes = []
            for sr, sc in cells:
                if (sr, sc) in used:
                    continue
                group = []
                queue = [(sr, sc)]
                while queue:
                    cr, cc = queue.pop(0)
                    if (cr, cc) in used:
                        continue
                    used.add((cr, cc))
                    group.append((cr, cc))
                    for dr in [-1, 0, 1]:
                        for dc in [-1, 0, 1]:
                            if dr == 0 and dc == 0:
                                continue
                            nr, nc = cr + dr, cc + dc
                            if (nr, nc) not in used and (nr, nc) in cell_set:
                                queue.append((nr, nc))
                triominoes.append(group)

            # Each group must be exactly 3 cells in a 2x2 bbox
            for tri in triominoes:
                if len(tri) != 3:
                    return None
                rows = [r for r, c in tri]
                cols = [c for r, c in tri]
                if max(rows) - min(rows) != 1 or max(cols) - min(cols) != 1:
                    return None

            if not triominoes:
                return None

            # Build predicted output
            predicted = [row[:] for row in ri]
            for tri in triominoes:
                rows = [r for r, c in tri]
                cols = [c for r, c in tri]
                min_r, max_r = min(rows), max(rows)
                min_c, max_c = min(cols), max(cols)
                tri_set = set(tri)
                missing = None
                for r in [min_r, max_r]:
                    for c in [min_c, max_c]:
                        if (r, c) not in tri_set:
                            missing = (r, c)
                            break
                    if missing:
                        break
                if missing is None:
                    return None

                center_r = (min_r + max_r) / 2.0
                center_c = (min_c + max_c) / 2.0
                dr = 1 if missing[0] > center_r else -1
                dc = 1 if missing[1] > center_c else -1
                nr, nc = missing[0] + dr, missing[1] + dc
                while 0 <= nr < h and 0 <= nc < w:
                    predicted[nr][nc] = color
                    nr += dr
                    nc += dc

            if predicted != ro:
                return None

        return {"type": "l_triomino_extend", "confidence": 1.0}

    # ---- strategy: rectangle patch overlay --------------------------------

    def _try_rect_patch_overlay(self, task):
        """
        Detect: grid with uniform background containing rectangular 0-filled
        regions.  Each region may have some colored (non-0, non-bg) cells.
        Output = overlay/union of all region patches into one combined grid.
        Category: composite pattern assembly from rectangular patches.
        """
        if task is None:
            return None
        pairs = task.example_pairs
        if not pairs:
            return None

        for pair in pairs:
            g0, g1 = pair.input_grid, pair.output_grid
            if g0 is None or g1 is None:
                return None
            ri, ro = g0.raw, g1.raw
            h, w = len(ri), len(ri[0])
            oh, ow = len(ro), len(ro[0])
            if oh >= h or ow >= w:
                return None

            # Background = most frequent color on the border
            from collections import Counter
            border = ri[0] + ri[-1] + [ri[r][0] for r in range(h)] + [ri[r][-1] for r in range(h)]
            bg = Counter(border).most_common(1)[0][0]

            # Find connected regions of non-bg cells (4-connected BFS)
            visited = [[False] * w for _ in range(h)]
            regions = []
            for sr in range(h):
                for sc in range(w):
                    if ri[sr][sc] != bg and not visited[sr][sc]:
                        queue = [(sr, sc)]
                        reg_cells = []
                        while queue:
                            cr, cc = queue.pop(0)
                            if not (0 <= cr < h and 0 <= cc < w):
                                continue
                            if visited[cr][cc] or ri[cr][cc] == bg:
                                continue
                            visited[cr][cc] = True
                            reg_cells.append((cr, cc))
                            for dr, dc in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                                queue.append((cr + dr, cc + dc))
                        if reg_cells:
                            rmin = min(r for r, c in reg_cells)
                            rmax = max(r for r, c in reg_cells)
                            cmin = min(c for r, c in reg_cells)
                            cmax = max(c for r, c in reg_cells)
                            regions.append((rmin, cmin, rmax - rmin + 1, cmax - cmin + 1))

            if len(regions) < 2:
                return None

            # All regions must share the same dimensions
            rh, rw = regions[0][2], regions[0][3]
            if rh != oh or rw != ow:
                return None
            for reg in regions:
                if reg[2] != rh or reg[3] != rw:
                    return None

            # Overlay: take non-0 cells from each region
            overlay = [[0] * rw for _ in range(rh)]
            for rmin, cmin, _, _ in regions:
                for lr in range(rh):
                    for lc in range(rw):
                        val = ri[rmin + lr][cmin + lc]
                        if val != 0 and val != bg:
                            overlay[lr][lc] = val

            if overlay != ro:
                return None

        return {"type": "rect_patch_overlay", "confidence": 1.0}

    # ---- strategy: pair diagonal reflect ----------------------------------

    def _try_pair_diagonal_reflect(self, task):
        """
        Detect: pairs of same-color blocks arranged diagonally on a zero bg.
        Anti-diagonal reflections are placed with color 8, extended one
        block-step outward from the bounding box of each pair.
        Category: diagonal symmetry extension / anti-diagonal reflection.
        """
        if task is None:
            return None
        pairs = task.example_pairs
        if not pairs:
            return None

        for pair in pairs:
            g0, g1 = pair.input_grid, pair.output_grid
            if g0 is None or g1 is None:
                return None
            ri, ro = g0.raw, g1.raw
            h, w = len(ri), len(ri[0])
            if len(ro) != h or len(ro[0]) != w:
                return None

            # Collect non-zero cells (the colored blocks)
            cells = []
            colors = set()
            for r in range(h):
                for c in range(w):
                    if ri[r][c] != 0:
                        cells.append((r, c))
                        colors.add(ri[r][c])
            if len(colors) != 1 or len(cells) < 2:
                return None
            color = next(iter(colors))
            cell_set = set(cells)

            # Group by 8-connectivity
            used = set()
            groups = []
            for sr, sc in cells:
                if (sr, sc) in used:
                    continue
                group = []
                queue = [(sr, sc)]
                while queue:
                    cr, cc = queue.pop(0)
                    if (cr, cc) in used:
                        continue
                    used.add((cr, cc))
                    group.append((cr, cc))
                    for dr in [-1, 0, 1]:
                        for dc in [-1, 0, 1]:
                            if dr == 0 and dc == 0:
                                continue
                            nr, nc = cr + dr, cc + dc
                            if (nr, nc) not in used and (nr, nc) in cell_set:
                                queue.append((nr, nc))
                groups.append(group)

            # Process each 8-connected group
            predicted = [row[:] for row in ri]
            for group in groups:
                rows = [r for r, c in group]
                cols = [c for r, c in group]
                min_r, max_r = min(rows), max(rows)
                min_c, max_c = min(cols), max(cols)
                H = max_r - min_r + 1
                W = max_c - min_c + 1
                if H != W or H % 2 != 0 or H < 2:
                    return None
                S = H // 2

                # Count cells in each quadrant
                full = S * S
                tl = sum(1 for r, c in group if r < min_r + S and c < min_c + S)
                tr = sum(1 for r, c in group if r < min_r + S and c >= min_c + S)
                bl = sum(1 for r, c in group if r >= min_r + S and c < min_c + S)
                br = sum(1 for r, c in group if r >= min_r + S and c >= min_c + S)

                if tl == full and br == full and tr == 0 and bl == 0:
                    # "\" occupied, extend anti-diagonal "/"
                    extensions = [
                        (min_r, min_c + S, -S, S),       # top-right -> up-right
                        (min_r + S, min_c, S, -S),       # bottom-left -> down-left
                    ]
                elif tr == full and bl == full and tl == 0 and br == 0:
                    # "/" occupied, extend anti-diagonal "\"
                    extensions = [
                        (min_r, min_c, -S, -S),           # top-left -> up-left
                        (min_r + S, min_c + S, S, S),     # bottom-right -> down-right
                    ]
                else:
                    return None

                for quad_r, quad_c, dr, dc in extensions:
                    ext_r = quad_r + dr
                    ext_c = quad_c + dc
                    for r_off in range(S):
                        for c_off in range(S):
                            nr = ext_r + r_off
                            nc = ext_c + c_off
                            if 0 <= nr < h and 0 <= nc < w:
                                predicted[nr][nc] = 8

            if predicted != ro:
                return None

        return {"type": "pair_diagonal_reflect", "confidence": 1.0}

    # ---- strategy 60: recolor by enclosed holes ----------------------------

    def _try_recolor_by_holes(self, task):
        """
        Detect: all non-bg connected components are a single color (e.g. 8).
        Each component is recolored based on the number of enclosed holes
        (connected regions of bg completely surrounded by the component).
        Mapping: 1 hole -> 1, 2 holes -> 3, 3 holes -> 2, 4 holes -> 4.
        Category: shape classification by topology (hole count).
        """
        if task is None:
            return None
        pairs = task.example_pairs
        if not pairs:
            return None

        from collections import Counter

        def _get_connected_components(grid, h, w, target_color):
            """Find connected components of target_color using flood fill."""
            visited = [[False] * w for _ in range(h)]
            components = []
            for r in range(h):
                for c in range(w):
                    if grid[r][c] == target_color and not visited[r][c]:
                        comp = []
                        stack = [(r, c)]
                        visited[r][c] = True
                        while stack:
                            cr, cc = stack.pop()
                            comp.append((cr, cc))
                            for dr, dc in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                                nr, nc = cr + dr, cc + dc
                                if 0 <= nr < h and 0 <= nc < w and not visited[nr][nc] and grid[nr][nc] == target_color:
                                    visited[nr][nc] = True
                                    stack.append((nr, nc))
                        components.append(set(comp))
            return components

        def _count_enclosed_holes(grid, h, w, comp_cells):
            """Count enclosed hole regions (bg cells fully surrounded by comp)."""
            # Flood fill from all boundary bg cells to find external bg
            external = set()
            stack = []
            for r in range(h):
                for c in range(w):
                    if (r == 0 or r == h - 1 or c == 0 or c == w - 1):
                        if (r, c) not in comp_cells and grid[r][c] not in comp_cells:
                            if (r, c) not in external:
                                external.add((r, c))
                                stack.append((r, c))
            # Also add any cell not in the component that's on the boundary
            for r in range(h):
                for c in [0, w - 1]:
                    if (r, c) not in comp_cells and (r, c) not in external:
                        external.add((r, c))
                        stack.append((r, c))
            for c in range(w):
                for r in [0, h - 1]:
                    if (r, c) not in comp_cells and (r, c) not in external:
                        external.add((r, c))
                        stack.append((r, c))

            while stack:
                cr, cc = stack.pop()
                for dr, dc in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                    nr, nc = cr + dr, cc + dc
                    if 0 <= nr < h and 0 <= nc < w and (nr, nc) not in comp_cells and (nr, nc) not in external:
                        external.add((nr, nc))
                        stack.append((nr, nc))

            # Internal bg cells = not in comp and not external
            internal = set()
            for r in range(h):
                for c in range(w):
                    if (r, c) not in comp_cells and (r, c) not in external:
                        internal.add((r, c))

            # Count connected groups of internal cells
            visited = set()
            hole_count = 0
            for cell in internal:
                if cell not in visited:
                    hole_count += 1
                    q = [cell]
                    visited.add(cell)
                    while q:
                        cr, cc = q.pop()
                        for dr, dc in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                            nr, nc = cr + dr, cc + dc
                            if (nr, nc) in internal and (nr, nc) not in visited:
                                visited.add((nr, nc))
                                q.append((nr, nc))
            return hole_count

        # Detect: all non-bg cells are a single color
        ri0 = pairs[0].input_grid.raw
        flat = [v for row in ri0 for v in row]
        bg = Counter(flat).most_common(1)[0][0]
        non_bg_colors = set(v for v in flat if v != bg)
        if len(non_bg_colors) != 1:
            return None
        shape_color = non_bg_colors.pop()

        # Build hole_count -> output_color mapping from examples
        hole_to_color = {}
        for pair in pairs:
            ri = pair.input_grid.raw
            ro = pair.output_grid.raw
            h = len(ri)
            w = len(ri[0])
            if len(ro) != h or len(ro[0]) != w:
                return None

            # Check all non-bg cells in input are shape_color
            for r in range(h):
                for c in range(w):
                    if ri[r][c] != bg and ri[r][c] != shape_color:
                        return None

            comps = _get_connected_components(ri, h, w, shape_color)
            if not comps:
                return None

            for comp in comps:
                holes = _count_enclosed_holes(ri, h, w, comp)
                # Find output color for this component
                sample_r, sample_c = next(iter(comp))
                out_color = ro[sample_r][sample_c]
                if out_color == bg or out_color == shape_color:
                    return None

                if holes in hole_to_color:
                    if hole_to_color[holes] != out_color:
                        return None
                else:
                    hole_to_color[holes] = out_color

            # Verify: all component cells map correctly
            for comp in comps:
                holes = _count_enclosed_holes(ri, h, w, comp)
                expected_color = hole_to_color.get(holes)
                if expected_color is None:
                    return None
                for r, c in comp:
                    if ro[r][c] != expected_color:
                        return None

            # Verify: bg cells stay bg
            for r in range(h):
                for c in range(w):
                    if ri[r][c] == bg and ro[r][c] != bg:
                        return None

        if not hole_to_color:
            return None

        return {
            "type": "recolor_by_holes",
            "confidence": 1.0,
            "bg": bg,
            "shape_color": shape_color,
            "hole_to_color": hole_to_color,
        }

    # ---- strategy 61: stripe tile ------------------------------------------

    def _try_stripe_tile(self, task):
        """
        Detect: exactly two non-bg pixels in the input. They define repeating
        stripes (vertical columns or horizontal rows) that tile to the grid edge.
        The axis with the smaller non-zero gap determines stripe direction.
        Category: seed-pixel repeating stripe/line patterns.
        """
        if task is None:
            return None
        pairs = task.example_pairs
        if not pairs:
            return None

        from collections import Counter

        for pair in pairs:
            ri = pair.input_grid.raw
            ro = pair.output_grid.raw
            h = len(ri)
            w = len(ri[0])
            if len(ro) != h or len(ro[0]) != w:
                return None

            # Find exactly 2 non-zero pixels
            seeds = []
            bg = 0
            for r in range(h):
                for c in range(w):
                    if ri[r][c] != bg:
                        seeds.append((r, c, ri[r][c]))
            if len(seeds) != 2:
                return None

            r1, c1, clr1 = seeds[0]
            r2, c2, clr2 = seeds[1]

            row_gap = abs(r2 - r1)
            col_gap = abs(c2 - c1)

            if row_gap == 0 and col_gap == 0:
                return None

            # Determine axis: smaller non-zero gap wins
            if col_gap == 0:
                axis = "row"
            elif row_gap == 0:
                axis = "col"
            elif col_gap <= row_gap:
                axis = "col"
            else:
                axis = "row"

            # Build predicted output
            pred = [[bg] * w for _ in range(h)]
            if axis == "col":
                # Vertical stripes at columns
                start_col = min(c1, c2)
                gap = col_gap
                # Order colors by column position
                if c1 < c2:
                    colors = [clr1, clr2]
                else:
                    colors = [clr2, clr1]
                col = start_col
                ci = 0
                while col < w:
                    for r in range(h):
                        pred[r][col] = colors[ci % 2]
                    col += gap
                    ci += 1
            else:
                # Horizontal stripes at rows
                start_row = min(r1, r2)
                gap = row_gap
                if r1 < r2:
                    colors = [clr1, clr2]
                else:
                    colors = [clr2, clr1]
                row = start_row
                ri_idx = 0
                while row < h:
                    for c in range(w):
                        pred[row][c] = colors[ri_idx % 2]
                    row += gap
                    ri_idx += 1

            if pred != ro:
                return None

        return {
            "type": "stripe_tile",
            "confidence": 1.0,
        }

    # ---- strategy 62: diamond symmetry fill --------------------------------

    def _try_diamond_symmetry_fill(self, task):
        """
        Detect: a partially-drawn diamond/lattice pattern on a bg grid.
        The output completes the pattern using 4-fold rotational symmetry
        (90 degree rotations) around the pattern's center.
        Category: symmetric pattern completion (checkerboard lattice).
        """
        if task is None:
            return None
        pairs = task.example_pairs
        if not pairs:
            return None

        for pair in pairs:
            ri = pair.input_grid.raw
            ro = pair.output_grid.raw
            h = len(ri)
            w = len(ri[0])
            if len(ro) != h or len(ro[0]) != w:
                return None

            # Find all non-zero cells in input
            nz_cells = []
            for r in range(h):
                for c in range(w):
                    if ri[r][c] != 0:
                        nz_cells.append((r, c))

            if len(nz_cells) < 3:
                return None

            # Find bounding box of non-zero region
            min_r = min(r for r, c in nz_cells)
            max_r = max(r for r, c in nz_cells)
            min_c = min(c for r, c in nz_cells)
            max_c = max(c for r, c in nz_cells)

            # Center of symmetry (may be half-integer)
            center_r = (min_r + max_r) / 2.0
            center_c = (min_c + max_c) / 2.0

            # Build the full pattern via 4-fold rotation (0, 90, 180, 270 degrees)
            pred = [[0] * w for _ in range(h)]

            # Place original cells
            for r in range(h):
                for c in range(w):
                    if ri[r][c] != 0:
                        pred[r][c] = ri[r][c]

            # For each non-zero cell, generate all 4 rotations around center
            for r, c in nz_cells:
                color = ri[r][c]
                dr = r - center_r
                dc = c - center_c

                # 4 rotations: (dr,dc), (dc,-dr), (-dr,-dc), (-dc,dr)
                rotations = [
                    (dr, dc),       # 0 degrees (original)
                    (dc, -dr),      # 90 CW
                    (-dr, -dc),     # 180
                    (-dc, dr),      # 270 CW
                ]
                for rdr, rdc in rotations:
                    nr = center_r + rdr
                    nc = center_c + rdc
                    # Round to nearest int
                    nri = int(nr + 0.5) if nr >= 0 else int(nr - 0.5)
                    nci = int(nc + 0.5) if nc >= 0 else int(nc - 0.5)
                    if 0 <= nri < h and 0 <= nci < w and pred[nri][nci] == 0:
                        pred[nri][nci] = color

            if pred != ro:
                return None

        return {
            "type": "diamond_symmetry_fill",
            "confidence": 1.0,
        }

    # ---- strategy: complement tile ----------------------------------------

    def _try_complement_tile(self, task):
        """
        Detect: output = inverted input (swap 0 and non-zero color) tiled 2x2.
        Category: complement tiling — binary grids where 0↔color swap + tile.
        """
        for pair in task.example_pairs:
            ri = pair.input.contents
            ro = pair.output.contents
            ih, iw = len(ri), len(ri[0])
            oh, ow = len(ro), len(ro[0])
            if oh != ih * 2 or ow != iw * 2:
                return None
            # Find the single non-zero color
            colors = set()
            for row in ri:
                for c in row:
                    if c != 0:
                        colors.add(c)
            if len(colors) != 1:
                return None
            color = list(colors)[0]
            # Build inverted grid
            inv = []
            for row in ri:
                inv.append([0 if c == color else color for c in row])
            # Check tiling
            for r in range(oh):
                for c in range(ow):
                    if ro[r][c] != inv[r % ih][c % iw]:
                        return None
        return {
            "type": "complement_tile",
            "confidence": 1.0,
        }

    # ---- strategy: ring color cycle ----------------------------------------

    def _try_ring_color_cycle(self, task):
        """
        Detect: concentric rectangular frames where colors cycle inward.
        Each unique ring color maps to the previous ring's color (cyclically).
        Category: nested frame color rotation.
        """
        for pair in task.example_pairs:
            ri = pair.input.contents
            ro = pair.output.contents
            ih, iw = len(ri), len(ri[0])
            oh, ow = len(ro), len(ro[0])
            if ih != oh or iw != ow:
                return None
            # Extract ring colors (concentric rectangles)
            ring_colors = []
            max_rings = min(ih, iw) // 2 + (1 if min(ih, iw) % 2 else 0)
            for d in range(max_rings):
                # Sample from border of ring d
                if d < ih - d and d < iw - d:
                    color = ri[d][d]
                    # Verify this ring is uniform
                    uniform = True
                    # top edge
                    for c in range(d, iw - d):
                        if ri[d][c] != color:
                            uniform = False
                            break
                    # bottom edge
                    if uniform and ih - 1 - d > d:
                        for c in range(d, iw - d):
                            if ri[ih - 1 - d][c] != color:
                                uniform = False
                                break
                    # left edge
                    if uniform:
                        for r in range(d, ih - d):
                            if ri[r][d] != color:
                                uniform = False
                                break
                    # right edge
                    if uniform and iw - 1 - d > d:
                        for r in range(d, ih - d):
                            if ri[r][iw - 1 - d] != color:
                                uniform = False
                                break
                    if not uniform:
                        return None
                    ring_colors.append(color)
            if len(ring_colors) < 2:
                return None
            # Build unique color list (order of first appearance from outside)
            unique = []
            seen = set()
            for c in ring_colors:
                if c not in seen:
                    unique.append(c)
                    seen.add(c)
            if len(unique) < 2:
                return None
            # Build cyclic mapping: each color maps to the previous unique color
            mapping = {}
            for i, c in enumerate(unique):
                mapping[c] = unique[(i - 1) % len(unique)]
            # Verify against output
            for r in range(ih):
                for c in range(iw):
                    expected = mapping.get(ri[r][c], ri[r][c])
                    if ro[r][c] != expected:
                        return None
        return {
            "type": "ring_color_cycle",
            "confidence": 1.0,
        }

    # ---- strategy: column projection tile ----------------------------------

    def _try_column_projection_tile(self, task):
        """
        Detect: columns containing non-zero cells get 0→fill_color replacement,
        then result is tiled 2x2. Category: column projection tiling.
        """
        for pair in task.example_pairs:
            ri = pair.input.contents
            ro = pair.output.contents
            ih, iw = len(ri), len(ri[0])
            oh, ow = len(ro), len(ro[0])
            if oh != ih * 2 or ow != iw * 2:
                return None
            # Find non-zero color
            nz_colors = set()
            for row in ri:
                for c in row:
                    if c != 0:
                        nz_colors.add(c)
            if len(nz_colors) != 1:
                return None
            nz_color = list(nz_colors)[0]
            # Identify active columns (columns with non-zero)
            active_cols = set()
            for c in range(iw):
                for r in range(ih):
                    if ri[r][c] != 0:
                        active_cols.add(c)
                        break
            # Determine fill color from output
            fill_color = None
            for c in active_cols:
                for r in range(ih):
                    if ri[r][c] == 0:
                        fill_color = ro[r][c]
                        break
                if fill_color is not None:
                    break
            if fill_color is None:
                return None
            # Build expected transformed grid
            transformed = []
            for r in range(ih):
                row = []
                for c in range(iw):
                    if ri[r][c] != 0:
                        row.append(ri[r][c])
                    elif c in active_cols:
                        row.append(fill_color)
                    else:
                        row.append(0)
                transformed.append(row)
            # Check 2x2 tiling
            for r in range(oh):
                for c in range(ow):
                    if ro[r][c] != transformed[r % ih][c % iw]:
                        return None
        return {
            "type": "column_projection_tile",
            "fill_color": fill_color,
            "confidence": 1.0,
        }

    # ---- strategy 66: select asymmetric block ----------------------------

    def _try_select_asymmetric_block(self, task):
        """
        Detect: input is K*N x N, divided into K equal NxN blocks stacked vertically.
        Two blocks are symmetric about the main diagonal (transpose == original),
        one is not. Output = the asymmetric block.
        Category: block selection by symmetry property.
        """
        if task is None:
            return None
        pairs = task.example_pairs
        if not pairs:
            return None

        for pair in pairs:
            ri = pair.input_grid.raw
            ro = pair.output_grid.raw
            h, w = len(ri), len(ri[0])
            oh, ow = len(ro), len(ro[0])

            # Must have square blocks: width = N, height = K*N
            if w == 0 or h % w != 0:
                return None
            n = w
            k = h // n
            if k < 3:
                return None
            if oh != n or ow != n:
                return None

            # Extract blocks
            blocks = []
            for b in range(k):
                block = [ri[b * n + r][:] for r in range(n)]
                blocks.append(block)

            # Check diagonal symmetry for each block
            def is_diag_symmetric(block):
                sz = len(block)
                for r in range(sz):
                    for c in range(sz):
                        if block[r][c] != block[c][r]:
                            return False
                return True

            sym_flags = [is_diag_symmetric(b) for b in blocks]
            asym_indices = [i for i, s in enumerate(sym_flags) if not s]
            sym_indices = [i for i, s in enumerate(sym_flags) if s]

            # Exactly one asymmetric block
            if len(asym_indices) != 1:
                return None

            # Verify output matches
            if blocks[asym_indices[0]] != ro:
                return None

        return {"type": "select_asymmetric_block", "confidence": 1.0}

    # ---- strategy 67: shape complement merge -----------------------------

    def _try_shape_complement_merge(self, task):
        """
        Detect: input is a grid (usually 10x10) with background 0 and exactly
        two colored objects. The objects are complementary halves of a rectangle.
        Output = the rectangle with both shapes interlocked.
        Category: shape complement / jigsaw merge.
        """
        if task is None:
            return None
        pairs = task.example_pairs
        if not pairs:
            return None

        for pair in pairs:
            ri = pair.input_grid.raw
            ro = pair.output_grid.raw
            h, w = len(ri), len(ri[0])
            oh, ow = len(ro), len(ro[0])

            # Find non-zero cells grouped by color
            color_cells = {}
            for r in range(h):
                for c in range(w):
                    v = ri[r][c]
                    if v != 0:
                        color_cells.setdefault(v, []).append((r, c))

            if len(color_cells) != 2:
                return None

            colors = list(color_cells.keys())
            cells_a = color_cells[colors[0]]
            cells_b = color_cells[colors[1]]

            # Normalize each shape to relative coordinates
            def normalize(cells):
                min_r = min(r for r, c in cells)
                min_c = min(c for r, c in cells)
                return frozenset((r - min_r, c - min_c) for r, c in cells)

            norm_a = normalize(cells_a)
            norm_b = normalize(cells_b)

            # Try all offsets to interlock them into a rectangle
            merged = self._try_merge_shapes(norm_a, norm_b, colors[0], colors[1], oh, ow)
            if merged is None:
                return None

            if merged != ro:
                return None

        return {"type": "shape_complement_merge", "confidence": 1.0}

    def _try_merge_shapes(self, norm_a, norm_b, color_a, color_b, target_h, target_w):
        """Try all offsets to merge two shapes into a target_h x target_w rectangle."""
        total_cells = target_h * target_w
        if len(norm_a) + len(norm_b) != total_cells:
            return None

        # For each possible offset of shape_b relative to shape_a,
        # check if they tile the rectangle
        a_set = set(norm_a)
        b_set = set(norm_b)

        # Get bounding extents
        max_ra = max(r for r, c in a_set)
        max_ca = max(c for r, c in a_set)
        max_rb = max(r for r, c in b_set)
        max_cb = max(c for r, c in b_set)

        for dr in range(-max_rb, target_h):
            for dc in range(-max_cb, target_w):
                shifted_b = frozenset((r + dr, c + dc) for r, c in b_set)
                union = a_set | shifted_b
                # Check no overlap
                if len(union) != len(a_set) + len(shifted_b):
                    continue
                # Check it fills the rectangle exactly
                expected = frozenset((r, c) for r in range(target_h) for c in range(target_w))
                if union == expected:
                    grid = [[0] * target_w for _ in range(target_h)]
                    for r, c in a_set:
                        grid[r][c] = color_a
                    for r, c in shifted_b:
                        grid[r][c] = color_b
                    return grid

        # Also try with shapes swapped (a shifted, b at origin)
        for dr in range(-max_ra, target_h):
            for dc in range(-max_ca, target_w):
                shifted_a = frozenset((r + dr, c + dc) for r, c in a_set)
                union = shifted_a | b_set
                if len(union) != len(shifted_a) + len(b_set):
                    continue
                expected = frozenset((r, c) for r in range(target_h) for c in range(target_w))
                if union == expected:
                    grid = [[0] * target_w for _ in range(target_h)]
                    for r, c in shifted_a:
                        grid[r][c] = color_a
                    for r, c in b_set:
                        grid[r][c] = color_b
                    return grid
        return None

    # ---- strategy 68: hub assembly ---------------------------------------

    def _try_hub_assembly(self, task):
        """
        Detect: input grid has several small colored shapes, each adjacent to
        a color-5 anchor cell. Output is a small grid (usually 3x3) with 5 at
        the center, and each shape placed at its relative offset from its anchor.
        Category: anchor-based shape assembly.
        """
        if task is None:
            return None
        pairs = task.example_pairs
        if not pairs:
            return None

        hub_color = 5  # the anchor/connector color

        for pair in pairs:
            ri = pair.input_grid.raw
            ro = pair.output_grid.raw
            h, w = len(ri), len(ri[0])
            oh, ow = len(ro), len(ro[0])

            # Collect hub cells and non-hub non-zero cells
            hub_cells = []
            shape_cells = {}  # color -> list of (r, c)
            for r in range(h):
                for c in range(w):
                    v = ri[r][c]
                    if v == 0:
                        continue
                    if v == hub_color:
                        hub_cells.append((r, c))
                    else:
                        shape_cells.setdefault(v, []).append((r, c))

            if not hub_cells or not shape_cells:
                return None

            # For each non-hub shape, find its nearest adjacent hub cell
            # A hub is "adjacent" if any cell in the shape is 4-connected to it
            def find_adjacent_hub(cells, hubs):
                for hr, hc in hubs:
                    for sr, sc in cells:
                        if abs(hr - sr) + abs(hc - sc) == 1:
                            return (hr, hc)
                # Also allow diagonal adjacency
                for hr, hc in hubs:
                    for sr, sc in cells:
                        if abs(hr - sr) <= 1 and abs(hc - sc) <= 1 and (hr, hc) != (sr, sc):
                            return (hr, hc)
                return None

            # Determine output center (where hub_color goes)
            # Find hub_color in output
            hub_out_pos = None
            for r in range(oh):
                for c in range(ow):
                    if ro[r][c] == hub_color:
                        hub_out_pos = (r, c)
                        break
                if hub_out_pos is not None:
                    break

            if hub_out_pos is None:
                # Hub might not appear in output — check if shapes tile without it
                return None

            cr, cc = hub_out_pos

            # Build expected output
            expected = [[0] * ow for _ in range(oh)]
            expected[cr][cc] = hub_color

            used_hubs = set()
            for color, cells in shape_cells.items():
                hub_pos = find_adjacent_hub(cells, [h for h in hub_cells if h not in used_hubs])
                if hub_pos is None:
                    # try any hub
                    hub_pos = find_adjacent_hub(cells, hub_cells)
                if hub_pos is None:
                    return None
                used_hubs.add(hub_pos)
                hr, hc = hub_pos
                for sr, sc in cells:
                    dr, dc = sr - hr, sc - hc
                    out_r, out_c = cr + dr, cc + dc
                    if out_r < 0 or out_r >= oh or out_c < 0 or out_c >= ow:
                        return None
                    expected[out_r][out_c] = color

            if expected != ro:
                return None

        return {"type": "hub_assembly", "hub_color": hub_color, "confidence": 1.0}

    # ---- strategy 69: shape pixel scale ----------------------------------

    def _try_shape_pixel_scale(self, task):
        """
        Detect: input contains a single non-zero shape on a zero background.
        Output is the shape's bounding box with each cell scaled by an integer
        factor (each cell → NxN block). The output dimensions = bbox * factor.
        Category: shape extraction + pixel magnification.
        """
        if task is None:
            return None
        pairs = task.example_pairs
        if not pairs:
            return None

        factor = None
        for pair in pairs:
            ri = pair.input_grid.raw
            ro = pair.output_grid.raw
            ih, iw = len(ri), len(ri[0])
            oh, ow = len(ro), len(ro[0])

            # Find bounding box of non-zero cells in input
            min_r, max_r, min_c, max_c = ih, -1, iw, -1
            for r in range(ih):
                for c in range(iw):
                    if ri[r][c] != 0:
                        min_r = min(min_r, r)
                        max_r = max(max_r, r)
                        min_c = min(min_c, c)
                        max_c = max(max_c, c)
            if max_r < 0:
                return None

            bbox_h = max_r - min_r + 1
            bbox_w = max_c - min_c + 1
            if bbox_h == 0 or bbox_w == 0:
                return None

            # Determine scale factor
            if oh % bbox_h != 0 or ow % bbox_w != 0:
                return None
            fh = oh // bbox_h
            fw = ow // bbox_w
            if fh != fw or fh < 2:
                return None

            if factor is None:
                factor = fh
            elif factor != fh:
                return None

            # Verify output matches scaled shape
            for r in range(bbox_h):
                for c in range(bbox_w):
                    val = ri[min_r + r][min_c + c]
                    for dr in range(factor):
                        for dc in range(factor):
                            if ro[r * factor + dr][c * factor + dc] != val:
                                return None

        return {"type": "shape_pixel_scale", "factor": factor, "confidence": 1.0}

    # ---- strategy 70: quadrant color template ----------------------------

    def _try_quadrant_color_template(self, task):
        """
        Detect: input has an NxN block of a 'template' color and N*N single
        pixels of other colors scattered around. Each pixel's quadrant position
        relative to the template center determines which template cell it fills.
        Output = same-size grid, all zeros except the template block now has
        the scattered pixel colors placed by their quadrant.
        Category: spatial assignment to template.
        """
        if task is None:
            return None
        pairs = task.example_pairs
        if not pairs:
            return None

        template_color = None
        block_size = None

        for pair in pairs:
            ri = pair.input_grid.raw
            ro = pair.output_grid.raw
            ih, iw = len(ri), len(ri[0])
            oh, ow = len(ro), len(ro[0])

            if ih != oh or iw != ow:
                return None

            # Find connected non-zero components
            comps = _find_nonzero_components(ri)
            if not comps:
                return None

            # Find the block (multi-cell single-color rectangle)
            block_comp = None
            singles = []
            for comp in comps:
                if len(comp) > 1:
                    colors = set(v for _, _, v in comp)
                    if len(colors) != 1:
                        return None
                    if block_comp is not None:
                        return None  # multiple multi-cell components
                    block_comp = comp
                else:
                    singles.append(comp[0])

            if block_comp is None or not singles:
                return None

            bc = block_comp[0][2]  # template color
            if template_color is None:
                template_color = bc
            elif template_color != bc:
                return None

            # Get block bounding box
            brs = [r for r, c, v in block_comp]
            bcs = [c for r, c, v in block_comp]
            br0, br1 = min(brs), max(brs)
            bc0, bc1 = min(bcs), max(bcs)
            bh = br1 - br0 + 1
            bw = bc1 - bc0 + 1

            # Must be a filled rectangle
            if len(block_comp) != bh * bw:
                return None
            if bh != bw:
                return None  # square block

            if block_size is None:
                block_size = bh
            elif block_size != bh:
                return None

            n = block_size
            if len(singles) != n * n:
                return None

            # Block center
            center_r = (br0 + br1) / 2.0
            center_c = (bc0 + bc1) / 2.0

            # Assign each single pixel to a block cell by quadrant
            # Sort singles by (row relative to center, col relative to center)
            # The pixel above-left of center → top-left cell, etc.
            # Classify: row < center_r → top rows, row > center_r → bottom rows
            above = sorted([(r, c, v) for r, c, v in singles if r < center_r],
                           key=lambda x: (x[0], x[1]))
            below = sorted([(r, c, v) for r, c, v in singles if r > center_r],
                           key=lambda x: (x[0], x[1]))
            at_center = [(r, c, v) for r, c, v in singles
                         if abs(r - center_r) < 0.5]

            # For 2x2 block: need exactly 2 above, 2 below (by row relative to center)
            # For NxN: more complex — use sorting approach
            # Assign by sorting: left of center → left col, right → right col
            left_pixels = sorted([(r, c, v) for r, c, v in singles if c < center_c],
                                 key=lambda x: (x[0], x[1]))
            right_pixels = sorted([(r, c, v) for r, c, v in singles if c > center_c],
                                  key=lambda x: (x[0], x[1]))

            if len(left_pixels) != n or len(right_pixels) != n:
                return None

            # Build expected output
            expected = [[0] * iw for _ in range(ih)]
            for i in range(n):
                expected[br0 + i][bc0] = left_pixels[i][2]
                expected[br0 + i][bc1] = right_pixels[i][2]

            if expected != ro:
                return None

        return {"type": "quadrant_color_template", "template_color": template_color,
                "block_size": block_size, "confidence": 1.0}

    # ---- strategy 71: sort bars right-align ------------------------------

    def _try_sort_bars_right_align(self, task):
        """
        Detect: input has several horizontal bars of different colors/lengths
        scattered across rows, plus one full-width 'floor' bar at the bottom.
        Output: all non-floor bars sorted by length (ascending top-to-bottom),
        right-aligned, stacked just above the floor row.
        Category: sorting + gravity + alignment.
        """
        if task is None:
            return None
        pairs = task.example_pairs
        if not pairs:
            return None

        for pair in pairs:
            ri = pair.input_grid.raw
            ro = pair.output_grid.raw
            ih, iw = len(ri), len(ri[0])
            oh, ow = len(ro), len(ro[0])

            if ih != oh or iw != ow:
                return None

            # Extract bars: each row's contiguous non-zero run
            bars = []  # (length, color, original_row)
            floor_row = None
            for r in range(ih):
                nonzero = [(c, ri[r][c]) for c in range(iw) if ri[r][c] != 0]
                if not nonzero:
                    continue
                # Check all same color
                colors = set(v for _, v in nonzero)
                if len(colors) != 1:
                    return None
                color = nonzero[0][1]
                length = len(nonzero)

                if length == iw:
                    # Full-width floor bar
                    if floor_row is not None:
                        return None  # multiple floors
                    floor_row = (r, color)
                else:
                    bars.append((length, color))

            if floor_row is None or not bars:
                return None

            floor_r, floor_color = floor_row

            # Sort bars by length ascending
            bars_sorted = sorted(bars, key=lambda x: x[0])

            # Build expected output: bars right-aligned, stacked above floor
            expected = [[0] * iw for _ in range(ih)]
            # Place floor
            expected[floor_r] = [floor_color] * iw

            # Place bars from bottom (just above floor) to top
            row = floor_r - 1
            for length, color in reversed(bars_sorted):
                if row < 0:
                    return None
                for c in range(iw - length, iw):
                    expected[row][c] = color
                row -= 1

            if expected != ro:
                return None

        return {"type": "sort_bars_right_align", "confidence": 1.0}

    # ---- strategy 72: corner rect fill -----------------------------------

    def _try_corner_rect_fill(self, task):
        """
        Detect: input has groups of 4 corner-marker pixels forming rectangles.
        Output fills the interior between each set of 4 corners with a specific
        color (typically 2), keeping corner markers in place.
        Category: corner detection + interior fill.
        """
        if task is None:
            return None
        pairs = task.example_pairs
        if not pairs:
            return None

        fill_color = None
        marker_color = None

        for pair in pairs:
            ri = pair.input_grid.raw
            ro = pair.output_grid.raw
            ih, iw = len(ri), len(ri[0])
            oh, ow = len(ro), len(ro[0])

            if ih != oh or iw != ow:
                return None

            # Find all non-zero pixels in input (all should be same color = marker)
            markers = []
            for r in range(ih):
                for c in range(iw):
                    if ri[r][c] != 0:
                        markers.append((r, c, ri[r][c]))

            if not markers:
                return None

            mc = set(v for _, _, v in markers)
            if len(mc) != 1:
                return None
            mc = markers[0][2]

            if marker_color is None:
                marker_color = mc
            elif marker_color != mc:
                return None

            # Find what color was added in output
            added_color = None
            for r in range(ih):
                for c in range(iw):
                    if ro[r][c] != 0 and ri[r][c] == 0:
                        if added_color is None:
                            added_color = ro[r][c]
                        elif added_color != ro[r][c]:
                            return None

            if added_color is None:
                return None
            if fill_color is None:
                fill_color = added_color
            elif fill_color != added_color:
                return None

            # Group markers into rectangle sets
            # Each set has 4 corners: (r1,c1), (r1,c2), (r2,c1), (r2,c2)
            positions = [(r, c) for r, c, _ in markers]
            rows = sorted(set(r for r, c in positions))
            cols = sorted(set(c for r, c in positions))

            # Find all valid rectangles from the marker positions
            pos_set = set(positions)
            used = set()
            rects = []

            for i, r1 in enumerate(rows):
                for j, r2 in enumerate(rows):
                    if r2 <= r1:
                        continue
                    for k, c1 in enumerate(cols):
                        for l, c2 in enumerate(cols):
                            if c2 <= c1:
                                continue
                            corners = {(r1, c1), (r1, c2), (r2, c1), (r2, c2)}
                            if corners.issubset(pos_set) and not corners.intersection(used):
                                rects.append((r1, r2, c1, c2))
                                used.update(corners)

            if not rects or used != pos_set:
                return None

            # Build expected output: input + fill interior of each rect
            expected = [row[:] for row in ri]
            for r1, r2, c1, c2 in rects:
                for r in range(r1 + 1, r2):
                    for c in range(c1 + 1, c2):
                        expected[r][c] = fill_color
                # Markers stay as-is (already in expected from ri copy)

            if expected != ro:
                return None

        return {"type": "corner_rect_fill", "marker_color": marker_color,
                "fill_color": fill_color, "confidence": 1.0}


    # ---- strategy 73: dot expand band ------------------------------------

    @staticmethod
    def _detect_bands_horizontal(raw, h, w):
        """Try to detect horizontal color bands. Returns list of (r_start, r_end, color) or None."""
        bands = []
        r = 0
        while r < h:
            row_colors = set(raw[r][c] for c in range(w) if raw[r][c] != 0)
            if len(row_colors) != 1:
                return None
            band_color = row_colors.pop()
            r_end = r
            while r_end < h:
                rc = set(raw[r_end][c] for c in range(w) if raw[r_end][c] != 0)
                if len(rc) != 1 or rc.pop() != band_color:
                    break
                r_end += 1
            bands.append((r, r_end, band_color))
            r = r_end
        return bands if len(bands) >= 2 else None

    @staticmethod
    def _detect_bands_vertical(raw, h, w):
        """Try to detect vertical color bands. Returns list of (c_start, c_end, color) or None."""
        bands = []
        c = 0
        while c < w:
            col_colors = set(raw[r][c] for r in range(h) if raw[r][c] != 0)
            if len(col_colors) != 1:
                return None
            band_color = col_colors.pop()
            c_end = c
            while c_end < w:
                cc = set(raw[r][c_end] for r in range(h) if raw[r][c_end] != 0)
                if len(cc) != 1 or cc.pop() != band_color:
                    break
                c_end += 1
            bands.append((c, c_end, band_color))
            c = c_end
        return bands if len(bands) >= 2 else None

    @staticmethod
    def _check_dot_expand(ri, ro, h, w, h_bands, v_bands):
        """Check if dot-expand matches for either orientation. Returns True if matched."""
        if h_bands is not None:
            expected = [row[:] for row in ri]
            has_dots = False
            for r_start, r_end, band_color in h_bands:
                zero_cols = set()
                for rr in range(r_start, r_end):
                    for cc in range(w):
                        if ri[rr][cc] == 0:
                            zero_cols.add(cc)
                            has_dots = True
                for zc in zero_cols:
                    for rr in range(r_start, r_end):
                        expected[rr][zc] = 0
            if has_dots and expected == ro:
                return True

        if v_bands is not None:
            expected = [row[:] for row in ri]
            has_dots = False
            for c_start, c_end, band_color in v_bands:
                zero_rows = set()
                for cc in range(c_start, c_end):
                    for rr in range(h):
                        if ri[rr][cc] == 0:
                            zero_rows.add(rr)
                            has_dots = True
                for zr in zero_rows:
                    for cc in range(c_start, c_end):
                        expected[zr][cc] = 0
            if has_dots and expected == ro:
                return True

        return False

    def _try_dot_expand_band(self, task):
        """
        Detect: grid divided into horizontal or vertical bands of uniform color.
        Each band has zero or more 0-dots. In the output, each dot expands
        to a full column (horizontal bands) or full row (vertical bands)
        spanning the entire band. Orientation detected per pair.
        Category: dot-to-line expansion within color zones.
        """
        if task is None:
            return None
        pairs = task.example_pairs
        if not pairs:
            return None

        for pair in pairs:
            ri = pair.input_grid.raw
            ro = pair.output_grid.raw
            h, w = len(ri), len(ri[0])
            if len(ro) != h or len(ro[0]) != w:
                return None

            h_bands = self._detect_bands_horizontal(ri, h, w)
            v_bands = self._detect_bands_vertical(ri, h, w)

            if not self._check_dot_expand(ri, ro, h, w, h_bands, v_bands):
                return None

        return {"type": "dot_expand_band", "confidence": 1.0}

    # ---- strategy 74: fill square holes ----------------------------------

    def _try_fill_square_holes(self, task):
        """
        Detect: grid has rectangular frames of color 5 with interior holes.
        Only holes whose interior forms a perfect square get filled with
        color 2. Non-square or irregular holes are left unchanged.
        Category: geometric property classification + fill.
        """
        if task is None:
            return None
        pairs = task.example_pairs
        if not pairs:
            return None

        for pair in pairs:
            ri = pair.input_grid.raw
            ro = pair.output_grid.raw
            h, w = len(ri), len(ri[0])
            if len(ro) != h or len(ro[0]) != w:
                return None

            # Find connected components of color 5
            visited = [[False] * w for _ in range(h)]
            frames = []
            for r in range(h):
                for c in range(w):
                    if ri[r][c] == 5 and not visited[r][c]:
                        # BFS to find component
                        comp = []
                        queue = [(r, c)]
                        visited[r][c] = True
                        while queue:
                            cr, cc = queue.pop(0)
                            comp.append((cr, cc))
                            for dr, dc in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                                nr, nc = cr + dr, cc + dc
                                if 0 <= nr < h and 0 <= nc < w and not visited[nr][nc] and ri[nr][nc] == 5:
                                    visited[nr][nc] = True
                                    queue.append((nr, nc))
                        frames.append(comp)

            if not frames:
                return None

            # For each frame, find enclosed 0-cells (flood fill from outside to find non-enclosed)
            expected = [row[:] for row in ri]
            found_any_frame = False

            for comp in frames:
                comp_set = set(comp)
                # Bounding box
                min_r = min(r for r, c in comp)
                max_r = max(r for r, c in comp)
                min_c = min(c for r, c in comp)
                max_c = max(c for r, c in comp)

                # Find interior 0-cells: cells within bbox that are 0 and NOT reachable
                # from outside the component without crossing a 5
                interior_zeros = []
                for rr in range(min_r, max_r + 1):
                    for cc in range(min_c, max_c + 1):
                        if ri[rr][cc] == 0 and (rr, cc) not in comp_set:
                            interior_zeros.append((rr, cc))

                if not interior_zeros:
                    continue

                # Verify these are truly enclosed: flood fill from the 0-cells and check
                # they don't escape the bounding box of the frame
                iz_set = set(interior_zeros)
                # Check they form a contiguous group and don't touch outside
                enclosed = True
                for rr, cc in interior_zeros:
                    for dr, dc in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                        nr, nc = rr + dr, cc + dc
                        if not (0 <= nr < h and 0 <= nc < w):
                            enclosed = False
                            break
                        if (nr, nc) not in comp_set and (nr, nc) not in iz_set:
                            enclosed = False
                            break
                    if not enclosed:
                        break

                if not enclosed:
                    continue

                found_any_frame = True

                # Check if interior forms a perfect square
                iz_rows = set(r for r, c in interior_zeros)
                iz_cols = set(c for r, c in interior_zeros)
                iz_h = max(iz_rows) - min(iz_rows) + 1
                iz_w = max(iz_cols) - min(iz_cols) + 1

                is_rect = (len(interior_zeros) == iz_h * iz_w)
                is_square = is_rect and (iz_h == iz_w)

                if is_square:
                    for rr, cc in interior_zeros:
                        expected[rr][cc] = 2

            if not found_any_frame:
                return None

            if expected != ro:
                return None

        return {"type": "fill_square_holes", "confidence": 1.0}

    # ---- strategy 75: column staircase shadow ----------------------------

    def _try_column_staircase_shadow(self, task):
        """
        Detect: grid has a vertical column of color 5 starting near the top.
        Left side fills with 8 in a staircase triangle, right side fills
        with 6 in a smaller staircase. The 8-triangle extends below the
        column; the 6-triangle stays within the column rows.
        Category: geometric shadow / staircase generation from line.
        """
        if task is None:
            return None
        pairs = task.example_pairs
        if not pairs:
            return None

        for pair in pairs:
            ri = pair.input_grid.raw
            ro = pair.output_grid.raw
            h, w = len(ri), len(ri[0])
            if len(ro) != h or len(ro[0]) != w:
                return None

            # Find the vertical column of 5: a single column where consecutive rows are 5
            col_pos = None
            col_start = None
            col_height = None
            for c in range(w):
                runs = []
                r = 0
                while r < h:
                    if ri[r][c] == 5:
                        start = r
                        while r < h and ri[r][c] == 5:
                            r += 1
                        runs.append((start, r - start))
                    else:
                        r += 1
                if len(runs) == 1 and runs[0][1] >= 2:
                    if col_pos is not None:
                        return None  # Multiple columns of 5
                    col_pos = c
                    col_start, col_height = runs[0]

            if col_pos is None or col_start != 0:
                return None

            # Verify rest of input is 0
            for r in range(h):
                for c in range(w):
                    if c == col_pos and r < col_height:
                        continue
                    if ri[r][c] != 0:
                        return None

            # Build expected output
            expected = [[0] * w for _ in range(h)]
            # Place the 5 column
            for r in range(col_height):
                expected[r][col_pos] = 5

            # Left side: 8 triangle
            # left_width(r) = col_pos - max(0, floor((r - col_height) / 2))
            for r in range(h):
                lw = col_pos - max(0, (r - col_height) // 2) if (r - col_height) >= 0 else col_pos
                # More precisely: lw = col_pos when r < col_height,
                # else col_pos - floor((r - col_height) / 2)
                if r < col_height:
                    lw = col_pos
                else:
                    lw = col_pos - (r - col_height) // 2
                lw = max(0, lw)
                for c in range(lw):
                    expected[r][c] = 8

            # Right side: 6 triangle (only within column rows)
            # right_width(r) = floor((col_height - r - 1) / 2) for r < col_height
            for r in range(col_height):
                rw = (col_height - r - 1) // 2
                rw = min(rw, w - col_pos - 1)
                for c in range(1, rw + 1):
                    if col_pos + c < w:
                        expected[r][col_pos + c] = 6

            if expected != ro:
                return None

        return {"type": "column_staircase_shadow", "confidence": 1.0}


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
        if rule_type == "recolor_by_size":
            return self._apply_recolor_by_size(rule, input_grid)
        if rule_type == "scale_up":
            return self._apply_scale_up(rule, input_grid)
        if rule_type == "flip_stack":
            return self._apply_flip_stack(rule, input_grid)
        if rule_type == "ring_reversal":
            return self._apply_ring_reversal(rule, input_grid)
        if rule_type == "max_column":
            return self._apply_max_column(rule, input_grid)
        if rule_type == "staircase_fill":
            return self._apply_staircase_fill(rule, input_grid)
        if rule_type == "corner_quadrant":
            return self._apply_corner_quadrant(rule, input_grid)
        if rule_type == "fill_rect_interior":
            return self._apply_fill_rect_interior(rule, input_grid)
        if rule_type == "connect_diamonds":
            return self._apply_connect_diamonds(rule, input_grid)
        if rule_type == "stripe_zone_fill":
            return self._apply_stripe_zone_fill(rule, input_grid)
        if rule_type == "path_turn_signals":
            return self._apply_path_turn_signals(rule, input_grid)
        if rule_type == "arrow_slide_mirror":
            return self._apply_arrow_slide_mirror(rule, input_grid)
        if rule_type == "quadrant_shape_swap":
            return self._apply_quadrant_shape_swap(rule, input_grid)
        if rule_type == "cross_border_project":
            return self._apply_cross_border_project(rule, input_grid)
        if rule_type == "grid_zigzag":
            return self._apply_grid_zigzag(rule, input_grid)
        if rule_type == "block_slide_split":
            return self._apply_block_slide_split(rule, input_grid)
        if rule_type == "gravity_fall":
            return self._apply_gravity_fall(rule, input_grid)
        if rule_type == "count_diamond":
            return self._apply_count_diamond(rule, input_grid)
        if rule_type == "anchor_template_place":
            return self._apply_anchor_template_place(rule, input_grid)
        if rule_type == "block_count_gravity":
            return self._apply_block_count_gravity(rule, input_grid)
        if rule_type == "cross_decorator":
            return self._apply_cross_decorator(rule, input_grid)
        if rule_type == "tile_mirror":
            return self._apply_tile_mirror(rule, input_grid)
        if rule_type == "mask_nor":
            return self._apply_mask_nor(rule, input_grid)
        if rule_type == "count_inside_frame":
            return self._apply_count_inside_frame(rule, input_grid)
        if rule_type == "flood_fill_interior":
            return self._apply_flood_fill_interior(rule, input_grid)
        if rule_type == "rotation_quad_tile":
            return self._apply_rotation_quad_tile(rule, input_grid)
        if rule_type == "diagonal_extend":
            return self._apply_diagonal_extend(rule, input_grid)
        if rule_type == "core_quadrant_fill":
            return self._apply_core_quadrant_fill(rule, input_grid)
        if rule_type == "noise_remove_rect":
            return self._apply_noise_remove_rect(rule, input_grid)
        if rule_type == "frame_color_swap":
            return self._apply_frame_color_swap(rule, input_grid)
        if rule_type == "pattern_tile_fill":
            return self._apply_pattern_tile_fill(rule, input_grid)
        if rule_type == "template_color_remap":
            return self._apply_template_color_remap(rule, input_grid)
        if rule_type == "marker_ray_fill":
            return self._apply_marker_ray_fill(rule, input_grid)
        if rule_type == "crop_bbox":
            return self._apply_crop_bbox(rule, input_grid)
        if rule_type == "binary_grid_xor":
            return self._apply_binary_grid_xor(rule, input_grid)
        if rule_type == "nonzero_count_scale":
            return self._apply_nonzero_count_scale(rule, input_grid)
        if rule_type == "stripe_rotate":
            return self._apply_stripe_rotate(rule, input_grid)
        if rule_type == "frame_solid_compose":
            return self._apply_frame_solid_compose(rule, input_grid)
        if rule_type == "self_tile":
            return self._apply_self_tile(rule, input_grid)
        if rule_type == "separator_and":
            return self._apply_separator_and(rule, input_grid)
        if rule_type == "checkerboard_tile":
            return self._apply_checkerboard_tile(rule, input_grid)
        if rule_type == "point_to_line":
            return self._apply_point_to_line(rule, input_grid)
        if rule_type == "quadrant_rotation_completion":
            return self._apply_quadrant_rotation_completion(rule, input_grid)
        if rule_type == "stamp_pattern":
            return self._apply_stamp_pattern(rule, input_grid)
        if rule_type == "global_color_swap":
            return self._apply_global_color_swap(rule, input_grid)
        if rule_type == "quadrant_extract":
            return self._apply_quadrant_extract(rule, input_grid)
        if rule_type == "key_color_swap":
            return self._apply_key_color_swap(rule, input_grid)
        if rule_type == "mirror_symmetric_recolor":
            return self._apply_mirror_symmetric_recolor(rule, input_grid)
        if rule_type == "bar_frame_gravity":
            return self._apply_bar_frame_gravity(rule, input_grid)
        if rule_type == "cross_center_mark":
            return self._apply_cross_center_mark(rule, input_grid)
        if rule_type == "corner_L_extend":
            return self._apply_corner_L_extend(rule, input_grid)
        if rule_type == "rotation_quad_tile_4x":
            return self._apply_rotation_quad_tile_4x(rule, input_grid)
        if rule_type == "rect_outline_decorate":
            return self._apply_rect_outline_decorate(rule, input_grid)
        if rule_type == "most_frequent_cross_color":
            return self._apply_most_frequent_cross_color(rule, input_grid)
        if rule_type == "grid_separator_invert":
            return self._apply_grid_separator_invert(rule, input_grid)
        if rule_type == "zero_region_classify":
            return self._apply_zero_region_classify(rule, input_grid)
        if rule_type == "grid_intersection_vote":
            return self._apply_grid_intersection_vote(rule, input_grid)
        if rule_type == "sparse_grid_compress":
            return self._apply_sparse_grid_compress(rule, input_grid)
        if rule_type == "extract_unique_shape":
            return self._apply_extract_unique_shape(rule, input_grid)
        if rule_type == "shape_match_recolor":
            return self._apply_shape_match_recolor(rule, input_grid)
        if rule_type == "l_triomino_extend":
            return self._apply_l_triomino_extend(rule, input_grid)
        if rule_type == "rect_patch_overlay":
            return self._apply_rect_patch_overlay(rule, input_grid)
        if rule_type == "pair_diagonal_reflect":
            return self._apply_pair_diagonal_reflect(rule, input_grid)
        if rule_type == "recolor_by_holes":
            return self._apply_recolor_by_holes(rule, input_grid)
        if rule_type == "stripe_tile":
            return self._apply_stripe_tile(rule, input_grid)
        if rule_type == "diamond_symmetry_fill":
            return self._apply_diamond_symmetry_fill(rule, input_grid)
        if rule_type == "complement_tile":
            return self._apply_complement_tile(rule, input_grid)
        if rule_type == "ring_color_cycle":
            return self._apply_ring_color_cycle(rule, input_grid)
        if rule_type == "column_projection_tile":
            return self._apply_column_projection_tile(rule, input_grid)
        if rule_type == "select_asymmetric_block":
            return self._apply_select_asymmetric_block(rule, input_grid)
        if rule_type == "shape_complement_merge":
            return self._apply_shape_complement_merge(rule, input_grid)
        if rule_type == "hub_assembly":
            return self._apply_hub_assembly(rule, input_grid)
        if rule_type == "shape_pixel_scale":
            return self._apply_shape_pixel_scale(rule, input_grid)
        if rule_type == "quadrant_color_template":
            return self._apply_quadrant_color_template(rule, input_grid)
        if rule_type == "sort_bars_right_align":
            return self._apply_sort_bars_right_align(rule, input_grid)
        if rule_type == "corner_rect_fill":
            return self._apply_corner_rect_fill(rule, input_grid)
        if rule_type == "dot_expand_band":
            return self._apply_dot_expand_band(rule, input_grid)
        if rule_type == "fill_square_holes":
            return self._apply_fill_square_holes(rule, input_grid)
        if rule_type == "column_staircase_shadow":
            return self._apply_column_staircase_shadow(rule, input_grid)
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

    def _apply_recolor_by_size(self, rule, input_grid):
        raw = input_grid.raw
        source_color = rule["source_color"]
        size_to_color = {int(k): v for k, v in rule["size_to_color"].items()}

        height = len(raw)
        width = len(raw[0]) if raw else 0

        target_cells = [
            (r, c)
            for r in range(height)
            for c in range(width)
            if raw[r][c] == source_color
        ]
        if not target_cells:
            return [row[:] for row in raw]

        groups = self._group_positions(target_cells)
        output = [row[:] for row in raw]

        for group in groups:
            size = len(group)
            color = size_to_color.get(size)
            if color is None:
                # Nearest known size as fallback
                known = sorted(size_to_color.keys())
                closest = min(known, key=lambda s: abs(s - size))
                color = size_to_color[closest]
            for r, c in group:
                output[r][c] = color
        return output

    def _apply_scale_up(self, rule, input_grid):
        raw = input_grid.raw
        factor = rule["factor"]
        output = []
        for row in raw:
            new_row = []
            for cell in row:
                new_row.extend([cell] * factor)
            for _ in range(factor):
                output.append(new_row[:])
        return output

    def _apply_flip_stack(self, rule, input_grid):
        raw = input_grid.raw
        axis = rule["axis"]
        if axis == "vertical":
            return [row[:] for row in raw] + [row[:] for row in reversed(raw)]
        if axis == "horizontal":
            return [row + row[::-1] for row in raw]
        return [row[:] for row in raw]

    def _apply_ring_reversal(self, rule, input_grid):
        raw = input_grid.raw
        rings = GeneralizeOperator._detect_rings(raw)
        if rings is None:
            return [row[:] for row in raw]
        reversed_colors = list(reversed(rings))
        h, w = len(raw), len(raw[0]) if raw else 0
        output = [row[:] for row in raw]
        top, left, bottom, right = 0, 0, h - 1, w - 1
        idx = 0
        while top <= bottom and left <= right:
            nc = reversed_colors[idx]
            for c in range(left, right + 1):
                output[top][c] = nc
                output[bottom][c] = nc
            for r in range(top, bottom + 1):
                output[r][left] = nc
                output[r][right] = nc
            top += 1; left += 1; bottom -= 1; right -= 1
            idx += 1
        return output

    def _apply_max_column(self, rule, input_grid):
        raw = input_grid.raw
        h, w = len(raw), len(raw[0]) if raw else 0
        col_counts = [sum(1 for r in range(h) if raw[r][c] != 0)
                      for c in range(w)]
        max_count = max(col_counts) if col_counts else 0
        if max_count == 0:
            return [row[:] for row in raw]
        center = (w - 1) / 2.0
        best_col = min(
            (c for c in range(w) if col_counts[c] == max_count),
            key=lambda c: abs(c - center),
        )
        output = []
        for r in range(h):
            row = [0] * w
            row[best_col] = raw[r][best_col]
            output.append(row)
        return output

    def _apply_staircase_fill(self, rule, input_grid):
        raw = input_grid.raw
        if len(raw) != 1:
            return [row[:] for row in raw]
        row = raw[0]
        w = len(row)
        color, count = None, 0
        for c in range(w):
            if row[c] != 0:
                if color is None:
                    color = row[c]
                count += 1
            else:
                break
        if color is None:
            return [row[:] for row in raw]
        num_rows = w // 2
        output = []
        for r in range(num_rows):
            fill = count + r
            output.append([color] * min(fill, w) + [0] * max(0, w - fill))
        return output

    def _apply_corner_quadrant(self, rule, input_grid):
        raw = input_grid.raw
        fill_color = rule.get("fill_color", 5)
        h, w = len(raw), len(raw[0]) if raw else 0
        output = [row[:] for row in raw]
        blocks = GeneralizeOperator._find_fill_blocks(raw, fill_color)
        for min_r, max_r, min_c, max_c in blocks:
            bh, bw = max_r - min_r + 1, max_c - min_c + 1
            if bh % 2 != 0 or bw % 2 != 0:
                continue
            corners = [
                (min_r - 1, min_c - 1), (min_r - 1, max_c + 1),
                (max_r + 1, min_c - 1), (max_r + 1, max_c + 1),
            ]
            valid = all(0 <= cr < h and 0 <= cc < w and raw[cr][cc] != 0
                        for cr, cc in corners)
            if not valid:
                continue
            tl = raw[corners[0][0]][corners[0][1]]
            tr = raw[corners[1][0]][corners[1][1]]
            bl = raw[corners[2][0]][corners[2][1]]
            br = raw[corners[3][0]][corners[3][1]]
            half_h, half_w = bh // 2, bw // 2
            for r in range(min_r, max_r + 1):
                for c in range(min_c, max_c + 1):
                    dr, dc = r - min_r, c - min_c
                    if dr < half_h:
                        output[r][c] = tl if dc < half_w else tr
                    else:
                        output[r][c] = bl if dc < half_w else br
            for cr, cc in corners:
                output[cr][cc] = 0
        return output

    def _apply_fill_rect_interior(self, rule, input_grid):
        raw = input_grid.raw
        border_color = rule["border_color"]
        area_to_color = {int(k): v for k, v in rule["area_to_color"].items()}

        output = [row[:] for row in raw]
        frames = GeneralizeOperator._find_rect_frames(raw, bg=0)

        for fc, min_r, max_r, min_c, max_c in frames:
            if fc != border_color:
                continue
            int_h = max_r - min_r - 1
            int_w = max_c - min_c - 1
            if int_h <= 0 or int_w <= 0:
                continue
            area = int_h * int_w
            fill = area_to_color.get(area)
            if fill is None:
                continue
            for r in range(min_r + 1, max_r):
                for c in range(min_c + 1, max_c):
                    output[r][c] = fill

        return output

    def _apply_connect_diamonds(self, rule, input_grid):
        raw = input_grid.raw
        bridge_color = rule["bridge_color"]

        output = [row[:] for row in raw]
        diamonds = GeneralizeOperator._find_diamonds(raw)
        centers = [(d[0], d[1]) for d in diamonds]

        row_groups = {}
        col_groups = {}
        for r, c in centers:
            row_groups.setdefault(r, []).append(c)
            col_groups.setdefault(c, []).append(r)

        for r, cols in row_groups.items():
            cols_sorted = sorted(cols)
            for i in range(len(cols_sorted) - 1):
                c1, c2 = cols_sorted[i], cols_sorted[i + 1]
                for c in range(c1 + 2, c2 - 1):
                    output[r][c] = bridge_color

        for c, rows in col_groups.items():
            rows_sorted = sorted(rows)
            for i in range(len(rows_sorted) - 1):
                r1, r2 = rows_sorted[i], rows_sorted[i + 1]
                for r in range(r1 + 2, r2 - 1):
                    output[r][c] = bridge_color

        return output

    def _apply_stripe_zone_fill(self, rule, input_grid):
        raw = input_grid.raw
        h = len(raw)
        w = len(raw[0]) if raw else 0
        bg = rule["bg_color"]
        col_color = rule["col_color"]
        int_color = rule["intersection_color"]

        stripe_col = GeneralizeOperator._detect_stripe_col(raw, h, w, bg)
        if stripe_col is None:
            return [row[:] for row in raw]

        stripes = []
        for r in range(h):
            if raw[r][stripe_col] == int_color:
                row_vals = set(raw[r][c] for c in range(w) if c != stripe_col)
                if len(row_vals) == 1:
                    sc = list(row_vals)[0]
                    if sc != bg:
                        stripes.append((r, sc))

        if not stripes:
            return [row[:] for row in raw]

        return GeneralizeOperator._build_stripe_zone_output(
            raw, h, w, bg, stripe_col, col_color, int_color, stripes
        )

    def _apply_path_turn_signals(self, rule, input_grid):
        raw = input_grid.raw
        h = len(raw)
        w = len(raw[0]) if raw else 0
        path_color = rule["path_color"]
        cw_color = rule["cw_color"]
        ccw_color = rule["ccw_color"]

        start = None
        markers = {}
        for r in range(h):
            for c in range(w):
                v = raw[r][c]
                if v == path_color:
                    start = (r, c)
                elif v != 0:
                    markers[(r, c)] = v
        if start is None:
            return [row[:] for row in raw]

        result = GeneralizeOperator._simulate_turn_path(
            h, w, start, markers, path_color, cw_color, ccw_color)
        return result if result is not None else [row[:] for row in raw]

    def _apply_arrow_slide_mirror(self, rule, input_grid):
        raw = input_grid.raw
        h = len(raw)
        w = len(raw[0]) if raw else 0
        bg = rule["bg_color"]
        divider_color = rule["divider_color"]
        dot_top = rule["dot_top_color"]
        dot_bot = rule["dot_bot_color"]
        arrow_color = rule["arrow_color"]

        div_row = None
        for r in range(h):
            if all(raw[r][c] == divider_color for c in range(w)):
                div_row = r
                break
        if div_row is None:
            return [row[:] for row in raw]

        return GeneralizeOperator._simulate_arrow_slide(
            raw, h, w, div_row, bg, dot_top, dot_bot, arrow_color)

    def _apply_quadrant_shape_swap(self, rule, input_grid):
        raw = input_grid.raw
        h = len(raw)
        w = len(raw[0]) if raw else 0
        sep_color = rule["sep_color"]

        result = GeneralizeOperator._parse_grid_regions(raw, h, w)
        if result is None:
            return [row[:] for row in raw]
        sc, row_ranges, col_ranges, regions = result
        if sc != sep_color:
            return [row[:] for row in raw]

        output = [row[:] for row in raw]

        for ri in range(len(row_ranges)):
            for ci in range(0, len(col_ranges), 2):
                if ci + 1 >= len(col_ranges):
                    break
                left = regions.get((ri, ci))
                right = regions.get((ri, ci + 1))
                if left is None or right is None:
                    continue

                l_bg, l_pat, l_pc, l_bounds = left
                r_bg, r_pat, r_pc, r_bounds = right

                lr, lc, lh, lw = l_bounds
                for r in range(lr, lr + lh):
                    for c in range(lc, lc + lw):
                        rel = (r - lr, c - lc)
                        output[r][c] = r_bg if rel in r_pat else l_bg

                rr, rc, rh, rw = r_bounds
                for r in range(rr, rr + rh):
                    for c in range(rc, rc + rw):
                        rel = (r - rr, c - rc)
                        output[r][c] = l_bg if rel in l_pat else r_bg

        return output

    def _apply_cross_border_project(self, rule, input_grid):
        raw = input_grid.raw
        h = len(raw)
        w = len(raw[0]) if raw else 0
        bg = GeneralizeOperator._most_common_color(raw, h, w)
        crosses = GeneralizeOperator._find_arrow_crosses(raw, h, w, bg)
        if not crosses:
            return [row[:] for row in raw]
        return GeneralizeOperator._build_cross_border_output(raw, h, w, crosses)

    def _apply_grid_zigzag(self, rule, input_grid):
        raw = input_grid.raw
        h = len(raw)
        w = len(raw[0]) if raw else 0
        bg = GeneralizeOperator._most_common_color(raw, h, w)
        grid_rows = [r for r in range(h) if any(raw[r][c] != bg for c in range(w))]
        if not grid_rows:
            return [row[:] for row in raw]
        min_r, max_r = min(grid_rows), max(grid_rows)
        shifts = [0, -1, 0, 1]
        output = [row[:] for row in raw]
        for i, r in enumerate(range(max_r, min_r - 1, -1)):
            s = shifts[i % 4]
            if s == 0:
                continue
            new_row = [bg] * w
            for c in range(w):
                src = c - s
                if 0 <= src < w:
                    new_row[c] = raw[r][src]
            output[r] = new_row
        return output

    def _apply_block_slide_split(self, rule, input_grid):
        raw = input_grid.raw
        h = len(raw)
        w = len(raw[0]) if raw else 0
        bg = GeneralizeOperator._most_common_color(raw, h, w)
        result = GeneralizeOperator._analyze_three_blocks(raw, h, w, bg)
        if result is None:
            return [row[:] for row in raw]
        blocks, axis, middle_idx, split_idx, stay_idx = result
        return GeneralizeOperator._build_block_slide_output(
            h, w, bg, blocks, axis, middle_idx, split_idx, stay_idx)

    def _apply_gravity_fall(self, rule, input_grid):
        raw = input_grid.raw
        colors = GeneralizeOperator._identify_gravity_colors(raw)
        if colors is None:
            return [row[:] for row in raw]
        bg, border_color, obj_colors = colors
        return GeneralizeOperator._compute_gravity_fall(
            raw, bg, border_color, obj_colors)

    def _apply_count_diamond(self, rule, input_grid):
        raw = input_grid.raw
        H = len(raw)
        W = len(raw[0]) if raw else 0
        from collections import Counter
        color_counts = Counter()
        for r in range(H):
            for c in range(W):
                color_counts[raw[r][c]] += 1
        bg = color_counts.most_common(1)[0][0]
        non_bg = {c: cnt for c, cnt in color_counts.items() if c != bg}
        if len(non_bg) != 2:
            return [row[:] for row in raw]
        counts = sorted(non_bg.values())
        h_rect = counts[0]
        w_rect = counts[1]
        out_dim = max(rule.get("output_dim", max(H, W)), H, W)
        if w_rect > out_dim or h_rect > out_dim:
            return [row[:] for row in raw]
        return GeneralizeOperator._build_count_diamond(
            out_dim, out_dim, bg, w_rect, h_rect)

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

    def _apply_anchor_template_place(self, rule, input_grid):
        return _anchor_template_predict(input_grid.raw)

    def _apply_block_count_gravity(self, rule, input_grid):
        return _block_gravity_predict(input_grid.raw)

    def _apply_cross_decorator(self, rule, input_grid):
        CROSS = [(-1, 0), (1, 0), (0, -1), (0, 1)]
        DIAG = [(-1, -1), (-1, 1), (1, -1), (1, 1)]
        raw = input_grid.raw
        h, w = len(raw), len(raw[0])
        result = [row[:] for row in raw]
        deco_map = {}
        for k, v in rule["deco_map"].items():
            deco_map[int(k)] = (v[0], v[1])
        for r in range(h):
            for c in range(w):
                col = raw[r][c]
                if col != 0 and col in deco_map:
                    pat, dcol = deco_map[col]
                    if pat == "cross":
                        offsets = CROSS
                    elif pat == "diagonal":
                        offsets = DIAG
                    else:
                        continue
                    for dr, dc in offsets:
                        nr, nc = r + dr, c + dc
                        if 0 <= nr < h and 0 <= nc < w and result[nr][nc] == 0:
                            result[nr][nc] = dcol
        return result

    def _apply_tile_mirror(self, rule, input_grid):
        raw = input_grid.raw
        h, w = len(raw), len(raw[0])
        rot180 = [row[::-1] for row in raw[::-1]]
        vflip = raw[::-1]
        hflip = [row[::-1] for row in raw]
        result = [[0] * (2 * w) for _ in range(2 * h)]
        for r in range(h):
            for c in range(w):
                result[r][c] = rot180[r][c]
                result[r][w + c] = vflip[r][c]
                result[h + r][c] = hflip[r][c]
                result[h + r][w + c] = raw[r][c]
        return result

    def _apply_count_inside_frame(self, rule, input_grid):
        raw = input_grid.raw
        h, w = len(raw), len(raw[0])
        # Find frame of 1s
        ones = [(r, c) for r in range(h) for c in range(w) if raw[r][c] == 1]
        if not ones:
            return None
        r1 = min(r for r, c in ones)
        r2 = max(r for r, c in ones)
        c1 = min(c for r, c in ones)
        c2 = max(c for r, c in ones)
        # Find marker color
        marker = None
        for r in range(h):
            for c in range(w):
                v = raw[r][c]
                if v != 0 and v != 1:
                    marker = v
                    break
            if marker is not None:
                break
        if marker is None:
            return None
        # Count marker inside frame
        count = 0
        for r in range(r1 + 1, r2):
            for c in range(c1 + 1, c2):
                if raw[r][c] == marker:
                    count += 1
        # Build 3x3 output
        result = [[0] * 3 for _ in range(3)]
        for idx in range(min(count, 9)):
            rr, cc = divmod(idx, 3)
            result[rr][cc] = marker
        return result

    def _apply_flood_fill_interior(self, rule, input_grid):
        raw = input_grid.raw
        bc = rule["boundary_color"]
        fc = rule["fill_color"]
        h, w = len(raw), len(raw[0])
        reachable = [[False] * w for _ in range(h)]
        queue = []
        for r in range(h):
            for c in range(w):
                if (r == 0 or r == h - 1 or c == 0 or c == w - 1):
                    if raw[r][c] != bc and not reachable[r][c]:
                        reachable[r][c] = True
                        queue.append((r, c))
        while queue:
            r, c = queue.pop(0)
            for dr, dc in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                nr, nc = r + dr, c + dc
                if 0 <= nr < h and 0 <= nc < w and not reachable[nr][nc]:
                    if raw[nr][nc] != bc:
                        reachable[nr][nc] = True
                        queue.append((nr, nc))
        result = [row[:] for row in raw]
        for r in range(h):
            for c in range(w):
                if raw[r][c] == 0 and not reachable[r][c]:
                    result[r][c] = fc
        return result

    def _apply_rotation_quad_tile(self, rule, input_grid):
        raw = input_grid.raw
        h, w = len(raw), len(raw[0])
        if h != w:
            return None
        rot90ccw = [[raw[j][w - 1 - i] for j in range(h)] for i in range(w)]
        rot180 = [[raw[h - 1 - i][w - 1 - j] for j in range(w)] for i in range(h)]
        rot90cw = [[raw[h - 1 - j][i] for j in range(h)] for i in range(w)]
        result = [[0] * (2 * w) for _ in range(2 * h)]
        for r in range(h):
            for c in range(w):
                result[r][c] = raw[r][c]
                result[r][w + c] = rot90ccw[r][c]
                result[h + r][c] = rot180[r][c]
                result[h + r][w + c] = rot90cw[r][c]
        return result

    def _apply_mask_nor(self, rule, input_grid):
        raw = input_grid.raw
        h, w = len(raw), len(raw[0])
        rc = rule["result_color"]
        div_row = None
        for r in range(h):
            vals = set(raw[r])
            if len(vals) == 1 and raw[r][0] != 0:
                t = raw[:r]
                b = raw[r + 1:]
                if len(t) == len(b) and len(t) > 0:
                    div_row = r
                    break
        if div_row is None:
            return None
        top = raw[:div_row]
        bottom = raw[div_row + 1:]
        oh = len(top)
        result = [[0] * w for _ in range(oh)]
        for r in range(oh):
            for c in range(w):
                if top[r][c] == 0 and bottom[r][c] == 0:
                    result[r][c] = rc
        return result

    def _apply_diagonal_extend(self, rule, input_grid):
        raw = input_grid.raw
        h, w = len(raw), len(raw[0])
        color = None
        for r in range(h):
            for c in range(w):
                if raw[r][c] != 0:
                    color = raw[r][c]
                    break
            if color:
                break
        if color is None:
            return None
        block = None
        for r in range(h - 1):
            for c in range(w - 1):
                if (raw[r][c] == color and raw[r][c + 1] == color and
                        raw[r + 1][c] == color and raw[r + 1][c + 1] == color):
                    block = (r, c)
                    break
            if block:
                break
        if block is None:
            return None
        br, bc = block
        block_cells = {(br, bc), (br, bc + 1), (br + 1, bc), (br + 1, bc + 1)}
        corners = {
            (br - 1, bc - 1): (-1, -1),
            (br - 1, bc + 2): (-1, 1),
            (br + 2, bc - 1): (1, -1),
            (br + 2, bc + 2): (1, 1),
        }
        result = [row[:] for row in raw]
        for r in range(h):
            for c in range(w):
                if raw[r][c] == color and (r, c) not in block_cells:
                    if (r, c) in corners:
                        dr, dc = corners[(r, c)]
                        nr, nc = r + dr, c + dc
                        while 0 <= nr < h and 0 <= nc < w:
                            result[nr][nc] = color
                            nr += dr
                            nc += dc
        return result

    def _apply_core_quadrant_fill(self, rule, input_grid):
        raw = input_grid.raw
        h, w = len(raw), len(raw[0])
        block = None
        for r in range(h - 1):
            for c in range(w - 1):
                vals = [raw[r][c], raw[r][c + 1], raw[r + 1][c], raw[r + 1][c + 1]]
                if all(v != 0 for v in vals) and len(set(vals)) == 4:
                    block = (r, c)
                    break
            if block:
                break
        if block is None:
            return None
        br, bc = block
        core_tl = raw[br][bc]
        core_tr = raw[br][bc + 1]
        core_bl = raw[br + 1][bc]
        core_br = raw[br + 1][bc + 1]
        result = [[0] * w for _ in range(h)]
        result[br][bc] = core_tl
        result[br][bc + 1] = core_tr
        result[br + 1][bc] = core_bl
        result[br + 1][bc + 1] = core_br
        for r in range(max(0, br - 2), br):
            for c in range(max(0, bc - 2), bc):
                result[r][c] = core_br
        for r in range(max(0, br - 2), br):
            for c in range(bc + 2, min(w, bc + 4)):
                result[r][c] = core_bl
        for r in range(br + 2, min(h, br + 4)):
            for c in range(max(0, bc - 2), bc):
                result[r][c] = core_tr
        for r in range(br + 2, min(h, br + 4)):
            for c in range(bc + 2, min(w, bc + 4)):
                result[r][c] = core_tl
        return result

    def _apply_noise_remove_rect(self, rule, input_grid):
        raw = input_grid.raw
        h, w = len(raw), len(raw[0])
        keep = set()
        for r in range(h - 1):
            for c in range(w - 1):
                v = raw[r][c]
                if (v != 0 and raw[r][c + 1] == v and
                        raw[r + 1][c] == v and raw[r + 1][c + 1] == v):
                    keep.add((r, c))
                    keep.add((r, c + 1))
                    keep.add((r + 1, c))
                    keep.add((r + 1, c + 1))
        result = [[0] * w for _ in range(h)]
        for r, c in keep:
            result[r][c] = raw[r][c]
        return result

    def _apply_frame_color_swap(self, rule, input_grid):
        raw = input_grid.raw
        h, w = len(raw), len(raw[0])

        # Bounding box of non-zero cells
        min_r, max_r, min_c, max_c = h, -1, w, -1
        for r in range(h):
            for c in range(w):
                if raw[r][c] != 0:
                    min_r = min(min_r, r)
                    max_r = max(max_r, r)
                    min_c = min(min_c, c)
                    max_c = max(max_c, c)
        if max_r == -1:
            return None

        block = [raw[r][min_c:max_c + 1] for r in range(min_r, max_r + 1)]

        colors = set()
        for row in block:
            for v in row:
                colors.add(v)
        colors.discard(0)
        if len(colors) != 2:
            return None

        c1, c2 = sorted(colors)
        return [[c2 if v == c1 else c1 for v in row] for row in block]

    def _apply_pattern_tile_fill(self, rule, input_grid):
        raw = input_grid.raw
        h, w = len(raw), len(raw[0])

        bg = raw[0][0]
        pattern_start = None
        for r in range(h):
            if any(raw[r][c] != bg for c in range(w)):
                pattern_start = r
                break
        if pattern_start is None or pattern_start == 0:
            return [row[:] for row in raw]

        ph = h - pattern_start
        pattern = [raw[r][:] for r in range(pattern_start, h)]

        result = []
        for r in range(h):
            idx = (r - pattern_start) % ph
            result.append(pattern[idx][:])
        return result

    def _apply_template_color_remap(self, rule, input_grid):
        raw = input_grid.raw
        h, w = len(raw), len(raw[0])

        # Find connected components of non-zero cells
        visited = [[False] * w for _ in range(h)]
        components = []
        for r in range(h):
            for c in range(w):
                if raw[r][c] != 0 and not visited[r][c]:
                    comp = []
                    queue = [(r, c)]
                    visited[r][c] = True
                    while queue:
                        cr, cc = queue.pop(0)
                        comp.append((cr, cc))
                        for dr, dc in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                            nr, nc = cr + dr, cc + dc
                            if (0 <= nr < h and 0 <= nc < w
                                    and not visited[nr][nc]
                                    and raw[nr][nc] != 0):
                                visited[nr][nc] = True
                                queue.append((nr, nc))
                    components.append(comp)

        if len(components) < 2:
            return None

        components.sort(key=len, reverse=True)
        block_comp = components[0]
        br1 = min(r for r, c in block_comp)
        br2 = max(r for r, c in block_comp)
        bc1 = min(c for r, c in block_comp)
        bc2 = max(c for r, c in block_comp)
        bh, bw = br2 - br1 + 1, bc2 - bc1 + 1
        if len(block_comp) != bh * bw:
            return None

        block = [raw[r][bc1:bc2 + 1] for r in range(br1, br2 + 1)]

        # Collect block colors
        block_colors = set()
        for row in block:
            for v in row:
                block_colors.add(v)

        # Extract key pairs
        color_map = {}
        for comp in components[1:]:
            if len(comp) != 2:
                continue
            (r1, c1), (r2, c2) = comp
            a, b = raw[r1][c1], raw[r2][c2]
            a_in = a in block_colors
            b_in = b in block_colors
            if b_in and not a_in:
                color_map[b] = a
            elif a_in and not b_in:
                color_map[a] = b
            else:
                color_map[b] = a

        return [[color_map.get(v, v) for v in row] for row in block]

    def _apply_marker_ray_fill(self, rule, input_grid):
        raw = input_grid.raw
        h = len(raw)
        w = len(raw[0]) if raw else 0

        # Collect non-zero markers
        markers = []
        for r in range(h):
            for c in range(w):
                if raw[r][c] != 0:
                    markers.append((r, c, raw[r][c]))
        if not markers:
            return [row[:] for row in raw]

        markers.sort(key=lambda m: m[0])

        output = [[0] * w for _ in range(h)]
        for idx, (mr, mc, color) in enumerate(markers):
            # Fill right from marker to right edge
            for c in range(mc, w):
                output[mr][c] = color
            # Fill down right-edge column
            if idx + 1 < len(markers):
                end_row = markers[idx + 1][0] - 1
            else:
                end_row = h - 1
            for r in range(mr + 1, end_row + 1):
                output[r][w - 1] = color

        return output

    def _apply_crop_bbox(self, rule, input_grid):
        raw = input_grid.raw
        h = len(raw)
        w = len(raw[0]) if raw else 0
        bg = rule.get("bg_color", 0)

        # Find bounding box of non-bg pixels
        non_bg = [(r, c) for r in range(h) for c in range(w)
                   if raw[r][c] != bg]
        if not non_bg:
            return [[0]]
        r1 = min(r for r, c in non_bg)
        r2 = max(r for r, c in non_bg)
        c1 = min(c for r, c in non_bg)
        c2 = max(c for r, c in non_bg)

        output = []
        for r in range(r1, r2 + 1):
            row = []
            for c in range(c1, c2 + 1):
                v = raw[r][c]
                row.append(0 if v == bg else v)
            output.append(row)
        return output

    def _apply_binary_grid_xor(self, rule, input_grid):
        raw = input_grid.raw
        h = len(raw)
        w = len(raw[0]) if raw else 0
        result_color = rule.get("result_color", 3)

        # Find separator row
        sep_row = None
        for r in range(h):
            vals = set(raw[r])
            if len(vals) == 1 and 0 not in vals:
                sep_row = r
                break
        if sep_row is None:
            return None

        top = raw[:sep_row]
        bot = raw[sep_row + 1:]
        th = len(top)
        if th == 0 or th != len(bot):
            return None

        # Identify non-zero colors
        top_colors = {v for row in top for v in row if v != 0}
        bot_colors = {v for row in bot for v in row if v != 0}
        color_a = top_colors.pop() if top_colors else 1
        color_b = bot_colors.pop() if bot_colors else 2

        output = []
        for r in range(th):
            row = []
            for c in range(w):
                a_set = (top[r][c] == color_a)
                b_set = (bot[r][c] == color_b)
                row.append(result_color if (a_set != b_set) else 0)
            output.append(row)
        return output

    def _apply_nonzero_count_scale(self, rule, input_grid):
        raw = input_grid.raw
        h = len(raw)
        w = len(raw[0]) if raw else 0
        nz = sum(1 for row in raw for v in row if v != 0)
        if nz <= 0:
            return None
        output = []
        for r in range(h):
            for _dr in range(nz):
                row = []
                for c in range(w):
                    for _dc in range(nz):
                        row.append(raw[r][c])
                output.append(row)
        return output

    def _apply_stripe_rotate(self, rule, input_grid):
        raw = input_grid.raw
        h = len(raw)
        w = len(raw[0]) if raw else 0

        # Find stripe columns on the right
        stripe_colors = []
        for c in range(w - 1, -1, -1):
            col_vals = [raw[r][c] for r in range(h)]
            unique = set(col_vals)
            if len(unique) == 1 and 0 not in unique:
                stripe_colors.append(col_vals[0])
            else:
                break
        if not stripe_colors:
            return None
        stripe_colors.reverse()
        num_stripes = len(stripe_colors)

        # Find marker height
        marker_color = None
        marker_height = 0
        for r in range(h):
            if raw[r][0] != 0:
                if marker_color is None:
                    marker_color = raw[r][0]
                marker_height += 1
        if marker_height == 0:
            return None

        out_col = w - num_stripes - 1

        output = [[0] * w for _ in range(h)]
        for r in range(h):
            if raw[r][0] == marker_color:
                output[r][0] = marker_color
        for r in range(h):
            cidx = (r // marker_height) % num_stripes
            output[r][out_col] = stripe_colors[cidx]
        return output

    def _apply_frame_solid_compose(self, rule, input_grid):
        raw = input_grid.raw
        h = len(raw)
        w = len(raw[0]) if raw else 0

        # Reuse the rect-finding helper from GeneralizeOperator
        rects = self._find_colored_rects_raw(raw, 0)
        if len(rects) < 2:
            return None

        sizes = set((r["h"], r["w"]) for r in rects)
        if len(sizes) != 1:
            return None
        rh, rw = sizes.pop()

        # Classify frames vs solids
        frames = []
        for rect in rects:
            is_frame = False
            for r in range(rect["r"] + 1, rect["r"] + rect["h"] - 1):
                for c in range(rect["c"] + 1, rect["c"] + rect["w"] - 1):
                    if raw[r][c] == 0:
                        is_frame = True
                        break
                if is_frame:
                    break
            if is_frame:
                frames.append(rect)

        if not frames:
            return None

        row_spread = max(f["r"] for f in frames) - min(f["r"] for f in frames)
        col_spread = max(f["c"] for f in frames) - min(f["c"] for f in frames)

        if col_spread >= row_spread:
            frames.sort(key=lambda f: f["c"])
            out_h = rh
            out_w = rw * len(frames)
        else:
            frames.sort(key=lambda f: f["r"])
            out_h = rh * len(frames)
            out_w = rw

        output = [[0] * out_w for _ in range(out_h)]
        for fi, f in enumerate(frames):
            for r in range(rh):
                for c in range(rw):
                    if col_spread >= row_spread:
                        output[r][fi * rw + c] = raw[f["r"] + r][f["c"] + c]
                    else:
                        output[fi * rh + r][c] = raw[f["r"] + r][f["c"] + c]
        return output

    def _apply_self_tile(self, rule, input_grid):
        raw = input_grid.raw
        n = len(raw)
        w = len(raw[0]) if raw else 0
        if n != w or n == 0:
            return None
        colors = {v for row in raw for v in row if v != 0}
        if len(colors) != 1:
            return None
        color = colors.pop()
        mode = rule.get("mode", "copy")

        if mode == "copy":
            tile = [row[:] for row in raw]
        else:
            tile = [[color if v == 0 else 0 for v in row] for row in raw]
        zero_tile = [[0] * n for _ in range(n)]

        out_size = n * n
        output = [[0] * out_size for _ in range(out_size)]
        for br in range(n):
            for bc in range(n):
                t = tile if raw[br][bc] != 0 else zero_tile
                for r in range(n):
                    for c in range(n):
                        output[br * n + r][bc * n + c] = t[r][c]
        return output

    def _apply_separator_and(self, rule, input_grid):
        raw = input_grid.raw
        h, w = len(raw), len(raw[0]) if raw else (0, 0)
        if h == 0 or w < 3:
            return None
        result_color = rule["result_color"]

        # Find separator column
        sep_col = None
        for c in range(w):
            vals = set(raw[r][c] for r in range(h))
            if len(vals) == 1 and 0 not in vals:
                sep_col = c
                break
        if sep_col is None:
            return None

        left = [row[:sep_col] for row in raw]
        right = [row[sep_col + 1:] for row in raw]
        lw = len(left[0]) if left else 0
        rw_ = len(right[0]) if right else 0
        if lw == 0 or lw != rw_:
            return None

        output = []
        for r in range(h):
            row = []
            for c in range(lw):
                if left[r][c] != 0 and right[r][c] != 0:
                    row.append(result_color)
                else:
                    row.append(0)
            output.append(row)
        return output

    def _apply_checkerboard_tile(self, rule, input_grid):
        raw = input_grid.raw
        h, w = len(raw), len(raw[0])
        hflip = [row[::-1] for row in raw]

        output = [[0] * (3 * w) for _ in range(3 * h)]
        for tr in range(3):
            tile = raw if tr % 2 == 0 else hflip
            for tc in range(3):
                for r in range(h):
                    for c in range(w):
                        output[tr * h + r][tc * w + c] = tile[r][c]
        return output

    # ---- apply: point_to_line ----------------------------------------------

    def _apply_point_to_line(self, rule, input_grid):
        raw = input_grid.raw
        h = len(raw)
        w = len(raw[0]) if raw else 0
        bg = rule["bg"]
        h_colors = set(rule["h_colors"])
        v_colors = set(rule["v_colors"])

        seeds = []
        for r in range(h):
            for c in range(w):
                clr = raw[r][c]
                if clr != bg:
                    seeds.append((r, c, clr))

        output = [[bg] * w for _ in range(h)]
        # Vertical lines first
        for r, c, clr in seeds:
            if clr in v_colors:
                for rr in range(h):
                    output[rr][c] = clr
        # Horizontal lines on top (overwrite at intersections)
        for r, c, clr in seeds:
            if clr in h_colors:
                for cc in range(w):
                    output[r][cc] = clr
        return output

    # ---- apply: quadrant_rotation_completion --------------------------------

    def _apply_quadrant_rotation_completion(self, rule, input_grid):
        raw = input_grid.raw
        h = len(raw)
        w = len(raw[0]) if raw else 0

        # Find separator row and column
        sep_r = sep_c = None
        for r in range(h):
            if all(raw[r][c] == 0 for c in range(w)):
                sep_r = r
                break
        for c in range(w):
            if all(raw[r][c] == 0 for r in range(h)):
                sep_c = c
                break
        if sep_r is None or sep_c is None:
            return [row[:] for row in raw]

        # Extract quadrants
        tl = [row[:sep_c] for row in raw[:sep_r]]
        tr = [row[sep_c + 1:] for row in raw[:sep_r]]
        bl = [row[:sep_c] for row in raw[sep_r + 1:]]
        br = [row[sep_c + 1:] for row in raw[sep_r + 1:]]

        def is_uniform(quad):
            if not quad or not quad[0]:
                return False
            v = quad[0][0]
            if v == 0:
                return False
            return all(quad[r][c] == v for r in range(len(quad)) for c in range(len(quad[0])))

        def rot90cw(grid):
            gh = len(grid)
            gw = len(grid[0]) if grid else 0
            return [[grid[gh - 1 - r][c] for r in range(gh)] for c in range(gw)]

        quads = [tl, tr, bl, br]
        marker_idx = None
        for i, q in enumerate(quads):
            if is_uniform(q):
                marker_idx = i
                break
        if marker_idx is None:
            return [row[:] for row in raw]

        # Try rot90cw of each non-marker quad to find the right source
        # The rotation chain: TL->TR->BL->BR, so predecessor map
        pred_map = {0: 3, 1: 0, 2: 1, 3: 2}
        result = rot90cw(quads[pred_map[marker_idx]])
        return result

    # ---- apply: stamp_pattern -----------------------------------------------

    def _apply_stamp_pattern(self, rule, input_grid):
        raw = input_grid.raw
        h = len(raw)
        w = len(raw[0]) if raw else 0
        bg = rule["bg"]
        marker_color = rule["marker_color"]
        stamp_offsets = {}
        for key, clr in rule["stamp_offsets"].items():
            dr, dc = map(int, key.split(","))
            stamp_offsets[(dr, dc)] = clr

        markers = [(r, c) for r in range(h) for c in range(w) if raw[r][c] == marker_color]

        output = [[bg] * w for _ in range(h)]
        for mr, mc in markers:
            for (dr, dc), clr in stamp_offsets.items():
                nr, nc = mr + dr, mc + dc
                if 0 <= nr < h and 0 <= nc < w:
                    output[nr][nc] = clr
        return output

    def _apply_global_color_swap(self, rule, input_grid):
        raw = input_grid.raw
        mapping = {int(k): v for k, v in rule["mapping"].items()}
        return [[mapping.get(cell, cell) for cell in row] for row in raw]

    def _apply_quadrant_extract(self, rule, input_grid):
        raw = input_grid.raw
        h = len(raw)
        w = len(raw[0]) if raw else 0
        shape_h = rule["shape_h"]
        shape_w = rule["shape_w"]

        # Find separator row and column dynamically
        sep_row = None
        sep_color = None
        for r in range(h):
            vals = set(raw[r])
            if len(vals) == 1 and 0 not in vals:
                sep_row = r
                sep_color = raw[r][0]
                break
        if sep_row is None:
            return [row[:] for row in raw]

        sep_col = None
        for c in range(w):
            if all(raw[r][c] == sep_color for r in range(h)):
                sep_col = c
                break
        if sep_col is None:
            return [row[:] for row in raw]

        def extract_shape(r_start, r_end, c_start, c_end):
            cells = []
            for r in range(r_start, r_end):
                for c in range(c_start, c_end):
                    if raw[r][c] != 0 and raw[r][c] != sep_color:
                        cells.append((r - r_start, c - c_start, raw[r][c]))
            if not cells:
                return [[0] * shape_w for _ in range(shape_h)]
            min_r = min(r for r, c, v in cells)
            min_c = min(c for r, c, v in cells)
            shape = [[0] * shape_w for _ in range(shape_h)]
            for r, c, v in cells:
                nr, nc = r - min_r, c - min_c
                if 0 <= nr < shape_h and 0 <= nc < shape_w:
                    shape[nr][nc] = v
            return shape

        quads = [
            extract_shape(0, sep_row, 0, sep_col),
            extract_shape(0, sep_row, sep_col + 1, w),
            extract_shape(sep_row + 1, h, 0, sep_col),
            extract_shape(sep_row + 1, h, sep_col + 1, w),
        ]

        output = [[0] * (shape_w * 2) for _ in range(shape_h * 2)]
        for qi, (dr, dc) in enumerate([(0, 0), (0, shape_w), (shape_h, 0), (shape_h, shape_w)]):
            for r in range(shape_h):
                for c in range(shape_w):
                    output[dr + r][dc + c] = quads[qi][r][c]
        return output

    def _apply_key_color_swap(self, rule, input_grid):
        raw = input_grid.raw
        h = len(raw)
        w = len(raw[0]) if raw else 0
        a, b, c, d = raw[0][0], raw[0][1], raw[1][0], raw[1][1]
        swap = {a: b, b: a, c: d, d: c}
        output = [row[:] for row in raw]
        for r in range(h):
            for col in range(w):
                if r < 2 and col < 2:
                    continue
                v = raw[r][col]
                if v != 0:
                    output[r][col] = swap.get(v, v)
        return output

    def _apply_mirror_symmetric_recolor(self, rule, input_grid):
        raw = input_grid.raw
        h = len(raw)
        w = len(raw[0]) if raw else 0
        src = rule["src_color"]
        dst = rule["dst_color"]
        output = [row[:] for row in raw]
        for r in range(h):
            for c in range(w):
                if raw[r][c] == src:
                    mirror_c = w - 1 - c
                    if raw[r][mirror_c] == src:
                        output[r][c] = dst
        return output

    def _apply_bar_frame_gravity(self, rule, input_grid):
        raw = input_grid.raw
        h = len(raw)
        w = len(raw[0]) if raw else 0
        gen = GeneralizeOperator()
        info = gen._detect_bar_frame(raw, h, w)
        if info is None:
            return [row[:] for row in raw]
        return gen._apply_bar_frame_gravity_raw(info, raw, h, w)

    def _apply_cross_center_mark(self, rule, input_grid):
        raw = input_grid.raw
        h = len(raw)
        w = len(raw[0]) if raw else 0
        bg = rule["bg"]
        fg = rule["fg"]
        mark_color = rule["mark_color"]
        gen = GeneralizeOperator()
        return gen._compute_cross_centers(raw, h, w, bg, fg, mark_color)

    def _apply_corner_L_extend(self, rule, input_grid):
        raw = input_grid.raw
        h = len(raw)
        w = len(raw[0]) if raw else 0
        bg = rule["bg"]
        output = [[bg] * w for _ in range(h)]
        dots = []
        for r in range(h):
            for c in range(w):
                if raw[r][c] != bg:
                    dots.append((r, c, raw[r][c]))
        for r, c, color in dots:
            corners = [
                (r + c, 'TL'),
                (r + (w - 1 - c), 'TR'),
                ((h - 1 - r) + c, 'BL'),
                ((h - 1 - r) + (w - 1 - c), 'BR'),
            ]
            corners.sort(key=lambda x: x[0])
            _, nearest = corners[0]
            if nearest == 'TL':
                for cc in range(0, c + 1):
                    output[r][cc] = color
                for rr in range(0, r):
                    output[rr][c] = color
            elif nearest == 'TR':
                for cc in range(c, w):
                    output[r][cc] = color
                for rr in range(0, r):
                    output[rr][c] = color
            elif nearest == 'BL':
                for cc in range(0, c + 1):
                    output[r][cc] = color
                for rr in range(r + 1, h):
                    output[rr][c] = color
            elif nearest == 'BR':
                for cc in range(c, w):
                    output[r][cc] = color
                for rr in range(r + 1, h):
                    output[rr][c] = color
        return output

    def _apply_rotation_quad_tile_4x(self, rule, input_grid):
        raw = input_grid.raw
        n = len(raw)
        if n != len(raw[0]):
            return None
        rot0 = raw
        rot180 = [[raw[n - 1 - r][n - 1 - c] for c in range(n)] for r in range(n)]
        rot_cw = [[raw[n - 1 - c][r] for c in range(n)] for r in range(n)]
        rot_ccw = [[raw[c][n - 1 - r] for c in range(n)] for r in range(n)]
        quads = {
            (0, 0): rot180, (0, 1): rot180, (1, 0): rot180, (1, 1): rot180,
            (0, 2): rot_cw, (0, 3): rot_cw, (1, 2): rot_cw, (1, 3): rot_cw,
            (2, 0): rot_ccw, (2, 1): rot_ccw, (3, 0): rot_ccw, (3, 1): rot_ccw,
            (2, 2): rot0, (2, 3): rot0, (3, 2): rot0, (3, 3): rot0,
        }
        result = [[0] * (4 * n) for _ in range(4 * n)]
        for tr in range(4):
            for tc in range(4):
                tile = quads[(tr, tc)]
                for r in range(n):
                    for c in range(n):
                        result[tr * n + r][tc * n + c] = tile[r][c]
        return result

    def _apply_rect_outline_decorate(self, rule, input_grid):
        raw = input_grid.raw
        h = len(raw)
        w = len(raw[0]) if raw else 0
        bg = rule["bg"]
        mark_color = rule["mark_color"]
        gen = GeneralizeOperator()
        return gen._compute_rect_outline_decorate(raw, h, w, bg, mark_color)

    def _apply_most_frequent_cross_color(self, rule, input_grid):
        raw = input_grid.raw
        h = len(raw)
        w = len(raw[0]) if raw else 0
        center_val = 4
        from collections import Counter
        cross_colors = []
        for r in range(1, h - 1):
            for c in range(1, w - 1):
                if raw[r][c] != center_val:
                    continue
                up, down, left, right = raw[r - 1][c], raw[r + 1][c], raw[r][c - 1], raw[r][c + 1]
                if up == down == left == right and up != center_val:
                    cross_colors.append(up)
        if not cross_colors:
            return None
        counts = Counter(cross_colors)
        majority = counts.most_common(1)[0][0]
        return [[majority]]

    def _apply_grid_separator_invert(self, rule, input_grid):
        raw = input_grid.raw
        h = len(raw)
        w = len(raw[0]) if raw else 0

        # Find separator rows/cols (cells in {0, 5})
        sep_rows = [r for r in range(h)
                    if all(raw[r][c] in (0, 5) for c in range(w))]
        sep_cols = [c for c in range(w)
                    if all(raw[r][c] in (0, 5) for r in range(h))]
        if not sep_rows or not sep_cols:
            return None

        row_bounds = GeneralizeOperator._sep_bounds(sep_rows, h)
        col_bounds = GeneralizeOperator._sep_bounds(sep_cols, w)
        if len(row_bounds) < 2 or len(col_bounds) < 2:
            return None

        qh = row_bounds[0][1] - row_bounds[0][0]
        qw = col_bounds[0][1] - col_bounds[0][0]

        quads = GeneralizeOperator._extract_quads(raw, row_bounds, col_bounds, qh, qw)

        # Find clean base pattern from this grid
        base = None
        for qrow in quads:
            for q in qrow:
                if any(q[r][c] == 5 for r in range(qh) for c in range(qw)):
                    continue
                colors = set(q[r][c] for r in range(qh) for c in range(qw))
                if len(colors) > 1:
                    if base is None:
                        base = [row[:] for row in q]
        if base is None:
            return None

        cc = {}
        for r in range(qh):
            for c in range(qw):
                cc[base[r][c]] = cc.get(base[r][c], 0) + 1
        sc = sorted(cc, key=cc.get, reverse=True)
        if len(sc) < 2:
            return None
        maj, mnr = sc[0], sc[1]

        all_maj = [[maj] * qw for _ in range(qh)]
        output = [[0] * w for _ in range(h)]

        for rs, re in row_bounds:
            for cs, ce in col_bounds:
                q = [raw[r][cs:ce] for r in range(rs, re)]
                qtype = GeneralizeOperator._classify_quad(q, base, mnr, qh, qw)
                fill = all_maj if qtype == 'base' else base
                for r in range(qh):
                    for c in range(qw):
                        output[rs + r][cs + c] = fill[r][c]

        return output

    def _apply_zero_region_classify(self, rule, input_grid):
        raw = input_grid.raw
        h = len(raw)
        w = len(raw[0]) if raw else 0
        ec = rule["exterior_color"]
        ic = rule["interior_color"]

        # Find connected components of 0-cells
        visited = [[False] * w for _ in range(h)]
        components = []
        for sr in range(h):
            for sc in range(w):
                if raw[sr][sc] == 0 and not visited[sr][sc]:
                    comp = []
                    touches_edge = False
                    queue = [(sr, sc)]
                    visited[sr][sc] = True
                    while queue:
                        cr, cc = queue.pop(0)
                        comp.append((cr, cc))
                        if cr == 0 or cr == h - 1 or cc == 0 or cc == w - 1:
                            touches_edge = True
                        for dr, dc in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                            nr, nc = cr + dr, cc + dc
                            if 0 <= nr < h and 0 <= nc < w and not visited[nr][nc] and raw[nr][nc] == 0:
                                visited[nr][nc] = True
                                queue.append((nr, nc))
                    components.append((comp, touches_edge))

        result = [row[:] for row in raw]
        for comp, touches_edge in components:
            color = ec if touches_edge else ic
            for r, c in comp:
                result[r][c] = color
        return result

    def _apply_grid_intersection_vote(self, rule, input_grid):
        return GeneralizeOperator._compute_grid_intersection_vote(None, input_grid.raw)

    def _apply_sparse_grid_compress(self, rule, input_grid):
        raw = input_grid.raw
        h = len(raw)
        w = len(raw[0]) if raw else 0
        # Count non-zero cells to infer output dimensions
        nz_positions = []
        for r in range(h):
            for c in range(w):
                if raw[r][c] != 0:
                    nz_positions.append((r, c))
        if not nz_positions:
            return None
        # Try all divisor pairs for block size
        for bh in range(2, h + 1):
            if h % bh != 0:
                continue
            for bw in range(2, w + 1):
                if w % bw != 0:
                    continue
                oh = h // bh
                ow = w // bw
                ok = True
                result = [[0] * ow for _ in range(oh)]
                for br in range(oh):
                    for bc in range(ow):
                        nz_val = None
                        nz_count = 0
                        for r in range(br * bh, (br + 1) * bh):
                            for c in range(bc * bw, (bc + 1) * bw):
                                if raw[r][c] != 0:
                                    nz_count += 1
                                    nz_val = raw[r][c]
                        if nz_count != 1:
                            ok = False
                            break
                        result[br][bc] = nz_val
                    if not ok:
                        break
                if ok:
                    return result
        return None

    def _apply_extract_unique_shape(self, rule, input_grid):
        raw = input_grid.raw
        h = len(raw)
        w = len(raw[0]) if raw else 0
        # Gather cells per color
        color_cells = {}
        for r in range(h):
            for c in range(w):
                v = raw[r][c]
                if v != 0:
                    color_cells.setdefault(v, []).append((r, c))
        # Find color with smallest bounding box area (>= 2 cells)
        best_color = None
        best_area = float('inf')
        best_bbox = None
        for color, cells in color_cells.items():
            if len(cells) < 2:
                continue
            min_r = min(r for r, _ in cells)
            max_r = max(r for r, _ in cells)
            min_c = min(c for _, c in cells)
            max_c = max(c for _, c in cells)
            area = (max_r - min_r + 1) * (max_c - min_c + 1)
            if area < best_area:
                best_area = area
                best_color = color
                best_bbox = (min_r, max_r, min_c, max_c)
        if best_color is None or best_bbox is None:
            return None
        min_r, max_r, min_c, max_c = best_bbox
        result = []
        for r in range(min_r, max_r + 1):
            row = []
            for c in range(min_c, max_c + 1):
                row.append(best_color if raw[r][c] == best_color else 0)
            result.append(row)
        return result

    def _apply_shape_match_recolor(self, rule, input_grid):
        raw = input_grid.raw
        h = len(raw)
        w = len(raw[0]) if raw else 0
        tc = rule["template_color"]
        output = [row[:] for row in raw]
        # Find template components
        t_comps = GeneralizeOperator._color_components(raw, tc)
        # Find reference colors and their shapes
        ref_colors = set()
        for row in raw:
            for v in row:
                if v != 0 and v != tc:
                    ref_colors.add(v)
        shape_to_color = {}
        for rc in ref_colors:
            for comp in GeneralizeOperator._color_components(raw, rc):
                shape = GeneralizeOperator._normalize_component(comp)
                shape_to_color[shape] = rc
        # Recolor each template to its matching reference
        for comp in t_comps:
            shape = GeneralizeOperator._normalize_component(comp)
            new_color = shape_to_color.get(shape)
            if new_color is not None:
                for r, c in comp:
                    output[r][c] = new_color
        return output

    def _apply_l_triomino_extend(self, rule, input_grid):
        try:
            return self._apply_l_triomino_extend_impl(rule, input_grid)
        except Exception:
            return [row[:] for row in input_grid.raw]

    def _apply_l_triomino_extend_impl(self, rule, input_grid):
        raw = input_grid.raw
        h = len(raw)
        w = len(raw[0]) if raw else 0
        cells = []
        color = None
        for r in range(h):
            for c in range(w):
                if raw[r][c] != 0:
                    cells.append((r, c))
                    color = raw[r][c]
        if not cells or color is None:
            return [row[:] for row in raw]
        cell_set = set(cells)
        used = set()
        triominoes = []
        for sr, sc in cells:
            if (sr, sc) in used:
                continue
            group = []
            queue = [(sr, sc)]
            while queue:
                cr, cc = queue.pop(0)
                if (cr, cc) in used:
                    continue
                used.add((cr, cc))
                group.append((cr, cc))
                for dr in [-1, 0, 1]:
                    for dc in [-1, 0, 1]:
                        if dr == 0 and dc == 0:
                            continue
                        nr, nc = cr + dr, cc + dc
                        if (nr, nc) not in used and (nr, nc) in cell_set:
                            queue.append((nr, nc))
            triominoes.append(group)
        output = [row[:] for row in raw]
        for tri in triominoes:
            if len(tri) != 3:
                continue
            rows = [r for r, c in tri]
            cols = [c for r, c in tri]
            min_r, max_r = min(rows), max(rows)
            min_c, max_c = min(cols), max(cols)
            if max_r - min_r != 1 or max_c - min_c != 1:
                continue
            tri_set = set(tri)
            missing = None
            for r in [min_r, max_r]:
                for c in [min_c, max_c]:
                    if (r, c) not in tri_set:
                        missing = (r, c)
                        break
                if missing:
                    break
            if missing is None:
                continue
            center_r = (min_r + max_r) / 2.0
            center_c = (min_c + max_c) / 2.0
            dr = 1 if missing[0] > center_r else -1
            dc = 1 if missing[1] > center_c else -1
            nr, nc = missing[0] + dr, missing[1] + dc
            while 0 <= nr < h and 0 <= nc < w:
                output[nr][nc] = color
                nr += dr
                nc += dc
        return output

    def _apply_rect_patch_overlay(self, rule, input_grid):
        try:
            raw = input_grid.raw
            h = len(raw)
            w = len(raw[0]) if raw else 0
            from collections import Counter
            border = raw[0] + raw[-1] + [raw[r][0] for r in range(h)] + [raw[r][-1] for r in range(h)]
            bg = Counter(border).most_common(1)[0][0]
            visited = [[False] * w for _ in range(h)]
            regions = []
            for sr in range(h):
                for sc in range(w):
                    if raw[sr][sc] != bg and not visited[sr][sc]:
                        queue = [(sr, sc)]
                        reg_cells = []
                        while queue:
                            cr, cc = queue.pop(0)
                            if not (0 <= cr < h and 0 <= cc < w):
                                continue
                            if visited[cr][cc] or raw[cr][cc] == bg:
                                continue
                            visited[cr][cc] = True
                            reg_cells.append((cr, cc))
                            for dr, dc in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                                queue.append((cr + dr, cc + dc))
                        if reg_cells:
                            rmin = min(r for r, c in reg_cells)
                            cmin = min(c for r, c in reg_cells)
                            rmax = max(r for r, c in reg_cells)
                            cmax = max(c for r, c in reg_cells)
                            regions.append((rmin, cmin, rmax - rmin + 1, cmax - cmin + 1))
            if not regions:
                return [row[:] for row in raw]
            rh, rw = regions[0][2], regions[0][3]
            overlay = [[0] * rw for _ in range(rh)]
            for rmin, cmin, _, _ in regions:
                for lr in range(rh):
                    for lc in range(rw):
                        r_idx, c_idx = rmin + lr, cmin + lc
                        if 0 <= r_idx < h and 0 <= c_idx < w:
                            val = raw[r_idx][c_idx]
                            if val != 0 and val != bg:
                                overlay[lr][lc] = val
            return overlay
        except Exception:
            return [row[:] for row in input_grid.raw]

    def _apply_pair_diagonal_reflect(self, rule, input_grid):
        try:
            return self._apply_pair_diagonal_reflect_impl(rule, input_grid)
        except Exception:
            return [row[:] for row in input_grid.raw]

    def _apply_pair_diagonal_reflect_impl(self, rule, input_grid):
        raw = input_grid.raw
        h = len(raw)
        w = len(raw[0]) if raw else 0
        cells = []
        color = None
        for r in range(h):
            for c in range(w):
                if raw[r][c] != 0:
                    cells.append((r, c))
                    color = raw[r][c]
        if not cells or color is None:
            return [row[:] for row in raw]
        cell_set = set(cells)
        used = set()
        groups = []
        for sr, sc in cells:
            if (sr, sc) in used:
                continue
            group = []
            queue = [(sr, sc)]
            while queue:
                cr, cc = queue.pop(0)
                if (cr, cc) in used:
                    continue
                used.add((cr, cc))
                group.append((cr, cc))
                for dr in [-1, 0, 1]:
                    for dc in [-1, 0, 1]:
                        if dr == 0 and dc == 0:
                            continue
                        nr, nc = cr + dr, cc + dc
                        if (nr, nc) not in used and (nr, nc) in cell_set:
                            queue.append((nr, nc))
            groups.append(group)
        output = [row[:] for row in raw]
        for group in groups:
            rows = [r for r, c in group]
            cols = [c for r, c in group]
            min_r, max_r = min(rows), max(rows)
            min_c, max_c = min(cols), max(cols)
            H = max_r - min_r + 1
            W = max_c - min_c + 1
            if H != W or H % 2 != 0 or H < 2:
                continue
            S = H // 2
            full = S * S
            tl = sum(1 for r, c in group if r < min_r + S and c < min_c + S)
            tr = sum(1 for r, c in group if r < min_r + S and c >= min_c + S)
            bl = sum(1 for r, c in group if r >= min_r + S and c < min_c + S)
            br = sum(1 for r, c in group if r >= min_r + S and c >= min_c + S)
            if tl == full and br == full and tr == 0 and bl == 0:
                extensions = [
                    (min_r, min_c + S, -S, S),
                    (min_r + S, min_c, S, -S),
                ]
            elif tr == full and bl == full and tl == 0 and br == 0:
                extensions = [
                    (min_r, min_c, -S, -S),
                    (min_r + S, min_c + S, S, S),
                ]
            else:
                continue
            for quad_r, quad_c, dr, dc in extensions:
                ext_r = quad_r + dr
                ext_c = quad_c + dc
                for r_off in range(S):
                    for c_off in range(S):
                        nr = ext_r + r_off
                        nc = ext_c + c_off
                        if 0 <= nr < h and 0 <= nc < w:
                            output[nr][nc] = 8
        return output

    def _find_colored_rects_raw(self, grid, bg=0):
        """Find all solid or framed rectangular blocks of one color on bg."""
        h = len(grid)
        w = len(grid[0]) if grid else 0
        visited = [[False] * w for _ in range(h)]
        rects = []

        for r in range(h):
            for c in range(w):
                if grid[r][c] != bg and not visited[r][c]:
                    color = grid[r][c]
                    cw = 0
                    while c + cw < w and grid[r][c + cw] == color:
                        cw += 1
                    ch = 0
                    ok = True
                    while r + ch < h and ok:
                        if grid[r + ch][c] == color:
                            ch += 1
                        else:
                            ok = False
                    if ch >= 2 and cw >= 2:
                        top_ok = all(grid[r][c + j] == color for j in range(cw))
                        bot_ok = all(grid[r + ch - 1][c + j] == color for j in range(cw))
                        left_ok = all(grid[r + i][c] == color for i in range(ch))
                        right_ok = all(grid[r + i][c + cw - 1] == color for i in range(ch))
                        if top_ok and bot_ok and left_ok and right_ok:
                            interior_ok = True
                            for ir in range(r + 1, r + ch - 1):
                                for ic in range(c + 1, c + cw - 1):
                                    v = grid[ir][ic]
                                    if v != color and v != bg:
                                        interior_ok = False
                                        break
                                if not interior_ok:
                                    break
                            if interior_ok:
                                rects.append({"r": r, "c": c, "h": ch, "w": cw, "color": color})
                                for ir in range(r, r + ch):
                                    for ic in range(c, c + cw):
                                        visited[ir][ic] = True
                                continue
                    visited[r][c] = True

        return rects

    # ---- apply: recolor_by_holes -------------------------------------------

    def _apply_recolor_by_holes(self, rule, input_grid):
        raw = input_grid.raw
        h = len(raw)
        w = len(raw[0]) if raw else 0
        bg = rule.get("bg", 0)
        shape_color = rule.get("shape_color", 8)
        hole_to_color = rule.get("hole_to_color", {})
        # Convert string keys back to int (JSON serialization)
        htc = {int(k): v for k, v in hole_to_color.items()}

        def _get_components(grid, h, w, target):
            visited = [[False] * w for _ in range(h)]
            comps = []
            for r in range(h):
                for c in range(w):
                    if grid[r][c] == target and not visited[r][c]:
                        comp = set()
                        stack = [(r, c)]
                        visited[r][c] = True
                        while stack:
                            cr, cc = stack.pop()
                            comp.add((cr, cc))
                            for dr, dc in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                                nr, nc = cr + dr, cc + dc
                                if 0 <= nr < h and 0 <= nc < w and not visited[nr][nc] and grid[nr][nc] == target:
                                    visited[nr][nc] = True
                                    stack.append((nr, nc))
                        comps.append(comp)
            return comps

        def _count_holes(grid, h, w, comp_cells):
            external = set()
            stack = []
            for r in range(h):
                for c in range(w):
                    if (r == 0 or r == h - 1 or c == 0 or c == w - 1):
                        if (r, c) not in comp_cells:
                            if (r, c) not in external:
                                external.add((r, c))
                                stack.append((r, c))
            while stack:
                cr, cc = stack.pop()
                for dr, dc in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                    nr, nc = cr + dr, cc + dc
                    if 0 <= nr < h and 0 <= nc < w and (nr, nc) not in comp_cells and (nr, nc) not in external:
                        external.add((nr, nc))
                        stack.append((nr, nc))
            internal = set()
            for r in range(h):
                for c in range(w):
                    if (r, c) not in comp_cells and (r, c) not in external:
                        internal.add((r, c))
            visited = set()
            count = 0
            for cell in internal:
                if cell not in visited:
                    count += 1
                    q = [cell]
                    visited.add(cell)
                    while q:
                        cr, cc = q.pop()
                        for dr, dc in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                            nr, nc = cr + dr, cc + dc
                            if (nr, nc) in internal and (nr, nc) not in visited:
                                visited.add((nr, nc))
                                q.append((nr, nc))
            return count

        output = [[bg] * w for _ in range(h)]
        comps = _get_components(raw, h, w, shape_color)
        for comp in comps:
            holes = _count_holes(raw, h, w, comp)
            color = htc.get(holes, shape_color)
            for r, c in comp:
                output[r][c] = color
        return output

    # ---- apply: stripe_tile ------------------------------------------------

    def _apply_stripe_tile(self, rule, input_grid):
        raw = input_grid.raw
        h = len(raw)
        w = len(raw[0]) if raw else 0

        # Find exactly 2 non-zero pixels
        seeds = []
        bg = 0
        for r in range(h):
            for c in range(w):
                if raw[r][c] != bg:
                    seeds.append((r, c, raw[r][c]))
        if len(seeds) != 2:
            return [row[:] for row in raw]

        r1, c1, clr1 = seeds[0]
        r2, c2, clr2 = seeds[1]

        row_gap = abs(r2 - r1)
        col_gap = abs(c2 - c1)

        if row_gap == 0 and col_gap == 0:
            return [row[:] for row in raw]

        if col_gap == 0:
            axis = "row"
        elif row_gap == 0:
            axis = "col"
        elif col_gap <= row_gap:
            axis = "col"
        else:
            axis = "row"

        pred = [[bg] * w for _ in range(h)]
        if axis == "col":
            start_col = min(c1, c2)
            gap = col_gap
            colors = [clr1, clr2] if c1 < c2 else [clr2, clr1]
            col = start_col
            ci = 0
            while col < w:
                for r in range(h):
                    pred[r][col] = colors[ci % 2]
                col += gap
                ci += 1
        else:
            start_row = min(r1, r2)
            gap = row_gap
            colors = [clr1, clr2] if r1 < r2 else [clr2, clr1]
            row = start_row
            ri_idx = 0
            while row < h:
                for c in range(w):
                    pred[row][c] = colors[ri_idx % 2]
                row += gap
                ri_idx += 1
        return pred

    # ---- apply: diamond_symmetry_fill --------------------------------------

    def _apply_diamond_symmetry_fill(self, rule, input_grid):
        raw = input_grid.raw
        h = len(raw)
        w = len(raw[0]) if raw else 0

        # Find all non-zero cells
        nz_cells = []
        for r in range(h):
            for c in range(w):
                if raw[r][c] != 0:
                    nz_cells.append((r, c))

        if not nz_cells:
            return [row[:] for row in raw]

        min_r = min(r for r, c in nz_cells)
        max_r = max(r for r, c in nz_cells)
        min_c = min(c for r, c in nz_cells)
        max_c = max(c for r, c in nz_cells)

        center_r = (min_r + max_r) / 2.0
        center_c = (min_c + max_c) / 2.0

        pred = [row[:] for row in raw]

        for r, c in nz_cells:
            color = raw[r][c]
            dr = r - center_r
            dc = c - center_c

            rotations = [
                (dr, dc),
                (dc, -dr),
                (-dr, -dc),
                (-dc, dr),
            ]
            for rdr, rdc in rotations:
                nr = center_r + rdr
                nc = center_c + rdc
                nri = int(nr + 0.5) if nr >= 0 else int(nr - 0.5)
                nci = int(nc + 0.5) if nc >= 0 else int(nc - 0.5)
                if 0 <= nri < h and 0 <= nci < w and pred[nri][nci] == 0:
                    pred[nri][nci] = color

        return pred

    # ---- apply: complement_tile --------------------------------------------

    def _apply_complement_tile(self, rule, input_grid):
        raw = input_grid.raw
        ih = len(raw)
        iw = len(raw[0]) if raw else 0
        # Find the non-zero color
        color = 0
        for row in raw:
            for c in row:
                if c != 0:
                    color = c
                    break
            if color != 0:
                break
        # Build inverted grid
        inv = []
        for row in raw:
            inv.append([0 if c == color else color for c in row])
        # Tile 2x2
        oh, ow = ih * 2, iw * 2
        out = []
        for r in range(oh):
            out.append([inv[r % ih][c % iw] for c in range(ow)])
        return out

    # ---- apply: ring_color_cycle -------------------------------------------

    def _apply_ring_color_cycle(self, rule, input_grid):
        raw = input_grid.raw
        ih = len(raw)
        iw = len(raw[0]) if raw else 0
        # Extract ring colors from outside in
        ring_colors = []
        max_rings = min(ih, iw) // 2 + (1 if min(ih, iw) % 2 else 0)
        for d in range(max_rings):
            if d < ih - d and d < iw - d:
                ring_colors.append(raw[d][d])
        # Build unique color list
        unique = []
        seen = set()
        for c in ring_colors:
            if c not in seen:
                unique.append(c)
                seen.add(c)
        # Build cyclic mapping
        mapping = {}
        for i, c in enumerate(unique):
            mapping[c] = unique[(i - 1) % len(unique)]
        # Apply mapping
        out = []
        for r in range(ih):
            out.append([mapping.get(raw[r][c], raw[r][c]) for c in range(iw)])
        return out

    # ---- apply: column_projection_tile -------------------------------------

    def _apply_column_projection_tile(self, rule, input_grid):
        raw = input_grid.raw
        ih = len(raw)
        iw = len(raw[0]) if raw else 0
        fill_color = rule.get("fill_color", 8)
        # Identify active columns
        active_cols = set()
        for c in range(iw):
            for r in range(ih):
                if raw[r][c] != 0:
                    active_cols.add(c)
                    break
        # Build transformed grid
        transformed = []
        for r in range(ih):
            row = []
            for c in range(iw):
                if raw[r][c] != 0:
                    row.append(raw[r][c])
                elif c in active_cols:
                    row.append(fill_color)
                else:
                    row.append(0)
            transformed.append(row)
        # Tile 2x2
        oh, ow = ih * 2, iw * 2
        out = []
        for r in range(oh):
            out.append([transformed[r % ih][c % iw] for c in range(ow)])
        return out

    # ---- apply: select asymmetric block ----------------------------------

    def _apply_select_asymmetric_block(self, rule, input_grid):
        raw = input_grid.raw
        h = len(raw)
        w = len(raw[0]) if raw else 0
        if w == 0 or h % w != 0:
            return None
        n = w
        k = h // n
        if k < 3:
            return None

        for b in range(k):
            block = [raw[b * n + r][:] for r in range(n)]
            # Check if NOT symmetric about main diagonal
            is_sym = True
            for r in range(n):
                for c in range(n):
                    if block[r][c] != block[c][r]:
                        is_sym = False
                        break
                if not is_sym:
                    break
            if not is_sym:
                return block
        # Shouldn't reach here, but fallback
        return [raw[r][:] for r in range(n)]

    # ---- apply: shape complement merge -----------------------------------

    def _apply_shape_complement_merge(self, rule, input_grid):
        raw = input_grid.raw
        h = len(raw)
        w = len(raw[0]) if raw else 0

        # Find non-zero cells grouped by color
        color_cells = {}
        for r in range(h):
            for c in range(w):
                v = raw[r][c]
                if v != 0:
                    color_cells.setdefault(v, []).append((r, c))

        if len(color_cells) != 2:
            return None

        colors = list(color_cells.keys())
        cells_a = color_cells[colors[0]]
        cells_b = color_cells[colors[1]]

        def normalize(cells):
            min_r = min(r for r, c in cells)
            min_c = min(c for r, c in cells)
            return frozenset((r - min_r, c - min_c) for r, c in cells)

        norm_a = normalize(cells_a)
        norm_b = normalize(cells_b)
        total = len(norm_a) + len(norm_b)

        # Try all possible rectangle dimensions
        for rect_h in range(1, total + 1):
            if total % rect_h != 0:
                continue
            rect_w = total // rect_h
            result = self._merge_into_rect(norm_a, norm_b, colors[0], colors[1], rect_h, rect_w)
            if result is not None:
                return result
        return None

    def _merge_into_rect(self, norm_a, norm_b, color_a, color_b, target_h, target_w):
        """Try all offsets to merge two shapes into a target_h x target_w rectangle."""
        a_set = set(norm_a)
        b_set = set(norm_b)
        max_ra = max(r for r, c in a_set) if a_set else 0
        max_ca = max(c for r, c in a_set) if a_set else 0
        max_rb = max(r for r, c in b_set) if b_set else 0
        max_cb = max(c for r, c in b_set) if b_set else 0
        expected = frozenset((r, c) for r in range(target_h) for c in range(target_w))

        for dr in range(-max_rb, target_h):
            for dc in range(-max_cb, target_w):
                shifted_b = frozenset((r + dr, c + dc) for r, c in b_set)
                union = a_set | shifted_b
                if len(union) != len(a_set) + len(shifted_b):
                    continue
                if union == expected:
                    grid = [[0] * target_w for _ in range(target_h)]
                    for r, c in a_set:
                        grid[r][c] = color_a
                    for r, c in shifted_b:
                        grid[r][c] = color_b
                    return grid

        for dr in range(-max_ra, target_h):
            for dc in range(-max_ca, target_w):
                shifted_a = frozenset((r + dr, c + dc) for r, c in a_set)
                union = shifted_a | b_set
                if len(union) != len(shifted_a) + len(b_set):
                    continue
                if union == expected:
                    grid = [[0] * target_w for _ in range(target_h)]
                    for r, c in shifted_a:
                        grid[r][c] = color_a
                    for r, c in b_set:
                        grid[r][c] = color_b
                    return grid
        return None

    # ---- apply: hub assembly ---------------------------------------------

    def _apply_hub_assembly(self, rule, input_grid):
        raw = input_grid.raw
        h = len(raw)
        w = len(raw[0]) if raw else 0
        hub_color = rule.get("hub_color", 5)

        # Collect hub cells and shape cells
        hub_cells = []
        shape_cells = {}
        for r in range(h):
            for c in range(w):
                v = raw[r][c]
                if v == 0:
                    continue
                if v == hub_color:
                    hub_cells.append((r, c))
                else:
                    shape_cells.setdefault(v, []).append((r, c))

        if not hub_cells or not shape_cells:
            return None

        def find_adjacent_hub(cells, hubs):
            for hr, hc in hubs:
                for sr, sc in cells:
                    if abs(hr - sr) + abs(hc - sc) == 1:
                        return (hr, hc)
            for hr, hc in hubs:
                for sr, sc in cells:
                    if abs(hr - sr) <= 1 and abs(hc - sc) <= 1 and (hr, hc) != (sr, sc):
                        return (hr, hc)
            return None

        # Build all relative placements to determine output size
        placements = {}  # (dr, dc) -> color
        used_hubs = set()
        for color, cells in shape_cells.items():
            hub_pos = find_adjacent_hub(cells, [hp for hp in hub_cells if hp not in used_hubs])
            if hub_pos is None:
                hub_pos = find_adjacent_hub(cells, hub_cells)
            if hub_pos is None:
                return None
            used_hubs.add(hub_pos)
            hr, hc = hub_pos
            for sr, sc in cells:
                placements[(sr - hr, sc - hc)] = color

        # Determine output bounds
        all_offsets = list(placements.keys()) + [(0, 0)]
        min_dr = min(dr for dr, dc in all_offsets)
        max_dr = max(dr for dr, dc in all_offsets)
        min_dc = min(dc for dr, dc in all_offsets)
        max_dc = max(dc for dr, dc in all_offsets)

        oh = max_dr - min_dr + 1
        ow = max_dc - min_dc + 1

        grid = [[0] * ow for _ in range(oh)]
        grid[0 - min_dr][0 - min_dc] = hub_color
        for (dr, dc), color in placements.items():
            grid[dr - min_dr][dc - min_dc] = color
        return grid

    def _apply_shape_pixel_scale(self, rule, input_grid):
        """Extract non-zero shape bbox and scale each cell by factor."""
        raw = input_grid.raw
        h = len(raw)
        w = len(raw[0]) if raw else 0
        factor = rule.get("factor", 2)

        # Find bounding box
        min_r, max_r, min_c, max_c = h, -1, w, -1
        for r in range(h):
            for c in range(w):
                if raw[r][c] != 0:
                    min_r = min(min_r, r)
                    max_r = max(max_r, r)
                    min_c = min(min_c, c)
                    max_c = max(max_c, c)
        if max_r < 0:
            return None

        bbox_h = max_r - min_r + 1
        bbox_w = max_c - min_c + 1
        oh = bbox_h * factor
        ow = bbox_w * factor

        grid = [[0] * ow for _ in range(oh)]
        for r in range(bbox_h):
            for c in range(bbox_w):
                val = raw[min_r + r][min_c + c]
                for dr in range(factor):
                    for dc in range(factor):
                        grid[r * factor + dr][c * factor + dc] = val
        return grid

    def _apply_quadrant_color_template(self, rule, input_grid):
        """Scattered pixels fill template block by quadrant position."""
        raw = input_grid.raw
        h = len(raw)
        w = len(raw[0]) if raw else 0
        template_color = rule.get("template_color", 8)
        n = rule.get("block_size", 2)

        comps = _find_nonzero_components(raw)
        block_comp = None
        singles = []
        for comp in comps:
            if len(comp) > 1:
                block_comp = comp
            else:
                singles.append(comp[0])

        if block_comp is None or not singles:
            return None

        brs = [r for r, c, v in block_comp]
        bcs = [c for r, c, v in block_comp]
        br0, br1 = min(brs), max(brs)
        bc0, bc1 = min(bcs), max(bcs)
        center_r = (br0 + br1) / 2.0
        center_c = (bc0 + bc1) / 2.0

        left_pixels = sorted([(r, c, v) for r, c, v in singles if c < center_c],
                             key=lambda x: (x[0], x[1]))
        right_pixels = sorted([(r, c, v) for r, c, v in singles if c > center_c],
                              key=lambda x: (x[0], x[1]))

        grid = [[0] * w for _ in range(h)]
        for i in range(min(n, len(left_pixels))):
            grid[br0 + i][bc0] = left_pixels[i][2]
        for i in range(min(n, len(right_pixels))):
            grid[br0 + i][bc1] = right_pixels[i][2]
        return grid

    def _apply_sort_bars_right_align(self, rule, input_grid):
        """Sort horizontal bars by length, right-align above floor."""
        raw = input_grid.raw
        h = len(raw)
        w = len(raw[0]) if raw else 0

        bars = []
        floor_row = None
        floor_color = None
        for r in range(h):
            nonzero = [(c, raw[r][c]) for c in range(w) if raw[r][c] != 0]
            if not nonzero:
                continue
            color = nonzero[0][1]
            length = len(nonzero)
            if length == w:
                floor_row = r
                floor_color = color
            else:
                bars.append((length, color))

        if floor_row is None:
            return None

        bars_sorted = sorted(bars, key=lambda x: x[0])
        grid = [[0] * w for _ in range(h)]
        grid[floor_row] = [floor_color] * w

        row = floor_row - 1
        for length, color in reversed(bars_sorted):
            if row < 0:
                break
            for c in range(w - length, w):
                grid[row][c] = color
            row -= 1
        return grid

    def _apply_corner_rect_fill(self, rule, input_grid):
        """Fill interior of rectangles defined by 4 corner markers."""
        raw = input_grid.raw
        h = len(raw)
        w = len(raw[0]) if raw else 0
        marker_color = rule.get("marker_color", 4)
        fill_color = rule.get("fill_color", 2)

        positions = []
        for r in range(h):
            for c in range(w):
                if raw[r][c] == marker_color:
                    positions.append((r, c))

        pos_set = set(positions)
        rows = sorted(set(r for r, c in positions))
        cols = sorted(set(c for r, c in positions))

        used = set()
        rects = []
        for i, r1 in enumerate(rows):
            for j, r2 in enumerate(rows):
                if r2 <= r1:
                    continue
                for k, c1 in enumerate(cols):
                    for l, c2 in enumerate(cols):
                        if c2 <= c1:
                            continue
                        corners = {(r1, c1), (r1, c2), (r2, c1), (r2, c2)}
                        if corners.issubset(pos_set) and not corners.intersection(used):
                            rects.append((r1, r2, c1, c2))
                            used.update(corners)

        grid = [row[:] for row in raw]
        for r1, r2, c1, c2 in rects:
            for r in range(r1 + 1, r2):
                for c in range(c1 + 1, c2):
                    grid[r][c] = fill_color
        return grid

    # ---- apply: dot expand band ------------------------------------------

    def _apply_dot_expand_band(self, rule, input_grid):
        """Expand 0-dots in each color band to full column/row stripes.
        Auto-detects orientation (horizontal or vertical) from the input grid."""
        raw = input_grid.raw
        h = len(raw)
        w = len(raw[0]) if raw else 0
        grid = [row[:] for row in raw]

        # Try horizontal bands
        h_bands = GeneralizeOperator._detect_bands_horizontal(raw, h, w)
        if h_bands is not None:
            for r_start, r_end, band_color in h_bands:
                zero_cols = set()
                for rr in range(r_start, r_end):
                    for cc in range(w):
                        if raw[rr][cc] == 0:
                            zero_cols.add(cc)
                for zc in zero_cols:
                    for rr in range(r_start, r_end):
                        grid[rr][zc] = 0
            return grid

        # Try vertical bands
        v_bands = GeneralizeOperator._detect_bands_vertical(raw, h, w)
        if v_bands is not None:
            for c_start, c_end, band_color in v_bands:
                zero_rows = set()
                for cc in range(c_start, c_end):
                    for rr in range(h):
                        if raw[rr][cc] == 0:
                            zero_rows.add(rr)
                for zr in zero_rows:
                    for cc in range(c_start, c_end):
                        grid[zr][cc] = 0
            return grid

        return grid

    # ---- apply: fill square holes ----------------------------------------

    def _apply_fill_square_holes(self, rule, input_grid):
        """Fill interior of rectangular 5-frames with 2, but only if the hole is a perfect square."""
        raw = input_grid.raw
        h = len(raw)
        w = len(raw[0]) if raw else 0
        grid = [row[:] for row in raw]

        visited = [[False] * w for _ in range(h)]
        for r in range(h):
            for c in range(w):
                if raw[r][c] == 5 and not visited[r][c]:
                    comp = []
                    queue = [(r, c)]
                    visited[r][c] = True
                    while queue:
                        cr, cc = queue.pop(0)
                        comp.append((cr, cc))
                        for dr, dc in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                            nr, nc = cr + dr, cc + dc
                            if 0 <= nr < h and 0 <= nc < w and not visited[nr][nc] and raw[nr][nc] == 5:
                                visited[nr][nc] = True
                                queue.append((nr, nc))

                    comp_set = set(comp)
                    min_r = min(rr for rr, cc in comp)
                    max_r = max(rr for rr, cc in comp)
                    min_c = min(cc for rr, cc in comp)
                    max_c = max(cc for rr, cc in comp)

                    # Find interior 0-cells
                    interior_zeros = []
                    for rr in range(min_r, max_r + 1):
                        for cc in range(min_c, max_c + 1):
                            if raw[rr][cc] == 0 and (rr, cc) not in comp_set:
                                interior_zeros.append((rr, cc))

                    if not interior_zeros:
                        continue

                    # Verify enclosed
                    iz_set = set(interior_zeros)
                    enclosed = True
                    for rr, cc in interior_zeros:
                        for dr, dc in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                            nr, nc = rr + dr, cc + dc
                            if not (0 <= nr < h and 0 <= nc < w):
                                enclosed = False
                                break
                            if (nr, nc) not in comp_set and (nr, nc) not in iz_set:
                                enclosed = False
                                break
                        if not enclosed:
                            break

                    if not enclosed:
                        continue

                    # Check if square
                    iz_rows = set(rr for rr, cc in interior_zeros)
                    iz_cols = set(cc for rr, cc in interior_zeros)
                    iz_h = max(iz_rows) - min(iz_rows) + 1
                    iz_w = max(iz_cols) - min(iz_cols) + 1
                    is_rect = (len(interior_zeros) == iz_h * iz_w)
                    is_square = is_rect and (iz_h == iz_w)

                    if is_square:
                        for rr, cc in interior_zeros:
                            grid[rr][cc] = 2

        return grid

    # ---- apply: column staircase shadow ----------------------------------

    def _apply_column_staircase_shadow(self, rule, input_grid):
        """Generate 8-left / 6-right staircase shadow from vertical 5-column."""
        raw = input_grid.raw
        h = len(raw)
        w = len(raw[0]) if raw else 0

        # Find column of 5
        col_pos = None
        col_height = 0
        for c in range(w):
            cnt = 0
            for r in range(h):
                if raw[r][c] == 5:
                    cnt += 1
                else:
                    break
            if cnt >= 2:
                col_pos = c
                col_height = cnt
                break

        if col_pos is None:
            return [row[:] for row in raw]

        grid = [[0] * w for _ in range(h)]
        # Place column
        for r in range(col_height):
            grid[r][col_pos] = 5

        # Left 8-triangle
        for r in range(h):
            if r < col_height:
                lw = col_pos
            else:
                lw = col_pos - (r - col_height) // 2
            lw = max(0, lw)
            for c in range(lw):
                grid[r][c] = 8

        # Right 6-triangle
        for r in range(col_height):
            rw = (col_height - r - 1) // 2
            rw = min(rw, w - col_pos - 1)
            for c in range(1, rw + 1):
                if col_pos + c < w:
                    grid[r][col_pos + c] = 6

        return grid


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
