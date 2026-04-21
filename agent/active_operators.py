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
