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
