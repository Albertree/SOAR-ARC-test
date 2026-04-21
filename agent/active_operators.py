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

        rule = None

        # Strategy 1: path tracing between turn markers
        rule = self._try_path_trace(patterns, wm)

        # Strategy 2: diamond connection (+ shapes linked by lines)
        if rule is None:
            rule = self._try_diamond_connect(patterns, wm)

        # Strategy 3: cross-grid band fill (column axis + colored rows)
        if rule is None:
            rule = self._try_cross_grid_fill(patterns, wm)

        # Strategy 4: sequential recoloring (e.g., color objects 1, 2, 3, ...)
        if rule is None:
            rule = self._try_recolor_sequential(patterns)

        # Strategy 5: reverse concentric rectangular rings
        if rule is None:
            rule = self._try_reverse_concentric_rings(patterns, wm)

        # Strategy 6: keep only the center column
        if rule is None:
            rule = self._try_keep_center_column(patterns, wm)

        # Strategy 7: simple 1:1 color mapping
        if rule is None:
            rule = self._try_color_mapping(patterns)

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
