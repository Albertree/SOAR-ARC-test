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
