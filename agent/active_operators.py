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
