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
        example_pairs = self._collect_example_pairs(task)

        rule = None

        # Strategy 1: sequential recoloring (e.g., color objects 1, 2, 3, ...)
        rule = self._try_recolor_sequential(patterns)

        # Strategy 2: bounding-box fill — fill bg cells within bbox of fg color
        if rule is None:
            rule = self._try_bbox_fill(example_pairs)

        # Strategy 3: horizontal mirror recolor — recolor cells whose
        #   horizontal-mirror partner has the same color
        if rule is None:
            rule = self._try_axis_mirror_recolor(example_pairs)

        # Strategy 4: integer upscale — each input cell becomes a kxk block
        if rule is None:
            rule = self._try_integer_upscale(example_pairs)

        # Strategy 5: stack with mirror — output = concat(input, flip(input))
        if rule is None:
            rule = self._try_stack_with_mirror(example_pairs)

        # Strategy 6: rectangle interior fill — hollow rect borders get interior
        #   filled with a color determined by interior dimensions
        if rule is None:
            rule = self._try_rect_interior_fill(example_pairs)

        # Strategy 7: staircase extend right — 1-row input becomes a triangular
        #   stack of rows where each row's prefix grows by one cell
        if rule is None:
            rule = self._try_staircase_extend_right(example_pairs)

        # Strategy 8: simple 1:1 color mapping
        if rule is None:
            rule = self._try_color_mapping(patterns)

        # Fallback: identity (copy input as output)
        if rule is None:
            rule = {"type": "identity", "confidence": 0.0}

        wm.s1["active-rules"] = [rule]

    @staticmethod
    def _collect_example_pairs(task):
        """Return list of (raw_input, raw_output) tuples for example pairs."""
        if task is None:
            return []
        out = []
        for pair in task.example_pairs:
            g0, g1 = pair.input_grid, pair.output_grid
            if g0 is None or g1 is None:
                continue
            out.append((g0.raw, g1.raw))
        return out

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

    # ---- strategy: bounding-box fill ------------------------------------

    def _try_bbox_fill(self, example_pairs):
        """
        Detect: same grid size; output equals input except every background
        cell within the bounding box of the foreground color has been
        recolored to a single marker color (a color not present in input).
        """
        if not example_pairs:
            return None

        marker = None
        bg_color = None
        fg_color = None

        for raw_in, raw_out in example_pairs:
            h, w = len(raw_in), len(raw_in[0]) if raw_in else 0
            if h != len(raw_out) or w != len(raw_out[0] if raw_out else []):
                return None

            in_colors = {c for row in raw_in for c in row}
            out_colors = {c for row in raw_out for c in row}
            new_colors = out_colors - in_colors
            if len(new_colors) != 1:
                return None
            m = next(iter(new_colors))

            # Background = most-frequent color in input
            counts = {}
            for row in raw_in:
                for c in row:
                    counts[c] = counts.get(c, 0) + 1
            bg = max(counts, key=counts.get)

            # Foreground = the other input color (must be exactly two)
            fg_set = {c for c in in_colors if c != bg}
            if len(fg_set) != 1:
                return None
            fg = next(iter(fg_set))

            # Compute bbox of foreground in input
            rows = [r for r in range(h) for c in range(w) if raw_in[r][c] == fg]
            cols = [c for r in range(h) for c in range(w) if raw_in[r][c] == fg]
            if not rows:
                return None
            r0, r1 = min(rows), max(rows)
            c0, c1 = min(cols), max(cols)

            # Verify: inside bbox, bg→marker, fg→fg; outside bbox unchanged
            for r in range(h):
                for c in range(w):
                    inside = r0 <= r <= r1 and c0 <= c <= c1
                    if inside and raw_in[r][c] == bg:
                        if raw_out[r][c] != m:
                            return None
                    else:
                        if raw_out[r][c] != raw_in[r][c]:
                            return None

            if marker is None:
                marker, bg_color, fg_color = m, bg, fg
            elif (m, bg, fg) != (marker, bg_color, fg_color):
                return None

        return {
            "type": "bbox_fill",
            "marker": marker,
            "background": bg_color,
            "foreground": fg_color,
            "confidence": 1.0,
        }

    # ---- strategy: axis mirror recolor ----------------------------------

    def _try_axis_mirror_recolor(self, example_pairs):
        """
        Detect: same grid size, exactly one new color in output (marker).
        For some axis (horizontal/vertical), every changed cell is the
        original foreground color and its mirror partner along that axis
        also has the original foreground color in the input.
        Unchanged cells are those without a same-color mirror partner.
        """
        if not example_pairs:
            return None

        for axis in ("horizontal", "vertical"):
            params = self._check_mirror_axis(example_pairs, axis)
            if params is not None:
                return {
                    "type": "axis_mirror_recolor",
                    "axis": axis,
                    "marker": params["marker"],
                    "foreground": params["foreground"],
                    "confidence": 1.0,
                }
        return None

    @staticmethod
    def _check_mirror_axis(example_pairs, axis):
        marker = None
        fg = None
        had_change = False

        for raw_in, raw_out in example_pairs:
            h = len(raw_in)
            w = len(raw_in[0]) if raw_in else 0
            if h != len(raw_out) or (w and w != len(raw_out[0])):
                return None

            new_colors = (
                {c for row in raw_out for c in row}
                - {c for row in raw_in for c in row}
            )
            if len(new_colors) != 1:
                return None
            m = next(iter(new_colors))

            for r in range(h):
                for c in range(w):
                    if axis == "horizontal":
                        rr, cc = r, w - 1 - c
                    else:
                        rr, cc = h - 1 - r, c
                    in_v = raw_in[r][c]
                    out_v = raw_out[r][c]
                    mirror_v = raw_in[rr][cc]
                    if out_v == in_v:
                        # If this cell HAS a same-color mirror partner of
                        # a non-bg color, the rule would have flipped it.
                        # We require: not changed → no same-color partner
                        # OR cell is on the axis and equals itself (trivial).
                        if (r, c) != (rr, cc) and in_v == mirror_v and in_v != 0:
                            # only allow when in_v is the background
                            # (but bg already excluded by != 0 check is rough);
                            # we'll defer to fg check below.
                            pass
                        continue
                    # Changed: must change FROM some fg TO marker, with mirror
                    # partner also equal to fg in the input.
                    if out_v != m:
                        return None
                    if in_v == 0:
                        # background-cells turning into marker — not this rule
                        return None
                    if mirror_v != in_v:
                        return None
                    if fg is None:
                        fg = in_v
                    elif fg != in_v:
                        return None
                    had_change = True

            if marker is None:
                marker = m
            elif marker != m:
                return None

        if not had_change or fg is None:
            return None

        # Final sanity: re-apply rule and confirm exact match.
        for raw_in, raw_out in example_pairs:
            h = len(raw_in)
            w = len(raw_in[0]) if raw_in else 0
            for r in range(h):
                for c in range(w):
                    if axis == "horizontal":
                        rr, cc = r, w - 1 - c
                    else:
                        rr, cc = h - 1 - r, c
                    expected = raw_in[r][c]
                    if (raw_in[r][c] == fg
                            and (r, c) != (rr, cc)
                            and raw_in[rr][cc] == fg):
                        expected = marker
                    if raw_out[r][c] != expected:
                        return None

        return {"marker": marker, "foreground": fg}

    # ---- strategy: integer upscale --------------------------------------

    def _try_integer_upscale(self, example_pairs):
        """
        Detect: output dimensions are k * input dimensions (same k for both
        height and width, and the same k across all examples). Each input
        cell at (r, c) becomes a kxk block at rows [k*r, k*r+k) and cols
        [k*c, k*c+k) in the output, all filled with the same color.
        """
        if not example_pairs:
            return None

        factor = None
        for raw_in, raw_out in example_pairs:
            ih = len(raw_in)
            iw = len(raw_in[0]) if raw_in else 0
            oh = len(raw_out)
            ow = len(raw_out[0]) if raw_out else 0
            if ih == 0 or iw == 0 or oh == 0 or ow == 0:
                return None
            if oh % ih != 0 or ow % iw != 0:
                return None
            kh, kw = oh // ih, ow // iw
            if kh != kw or kh < 2:
                return None
            if factor is None:
                factor = kh
            elif factor != kh:
                return None
            for r in range(ih):
                for c in range(iw):
                    v = raw_in[r][c]
                    for dr in range(factor):
                        for dc in range(factor):
                            if raw_out[r * factor + dr][c * factor + dc] != v:
                                return None

        if factor is None:
            return None
        return {"type": "integer_upscale", "factor": factor, "confidence": 1.0}

    # ---- strategy: stack with mirror ------------------------------------

    def _try_stack_with_mirror(self, example_pairs):
        """
        Detect: output = concatenation of input and a flipped copy of input
        along one axis. Tries four configurations:
          - direction=vertical,   order=input_first  (rows: input, vflip(input))
          - direction=vertical,   order=flip_first   (rows: vflip(input), input)
          - direction=horizontal, order=input_first  (cols: input, hflip(input))
          - direction=horizontal, order=flip_first   (cols: hflip(input), input)
        The same configuration must hold across every example.
        """
        if not example_pairs:
            return None

        configs = [
            ("vertical", "input_first"),
            ("vertical", "flip_first"),
            ("horizontal", "input_first"),
            ("horizontal", "flip_first"),
        ]

        for direction, order in configs:
            ok = True
            for raw_in, raw_out in example_pairs:
                if not self._check_stack_mirror(raw_in, raw_out, direction, order):
                    ok = False
                    break
            if ok:
                return {
                    "type": "stack_with_mirror",
                    "direction": direction,
                    "order": order,
                    "confidence": 1.0,
                }
        return None

    @staticmethod
    def _check_stack_mirror(raw_in, raw_out, direction, order):
        ih = len(raw_in)
        iw = len(raw_in[0]) if raw_in else 0
        oh = len(raw_out)
        ow = len(raw_out[0]) if raw_out else 0
        if ih == 0 or iw == 0:
            return False

        if direction == "vertical":
            if ow != iw or oh != 2 * ih:
                return False
            flipped = list(reversed(raw_in))
            top = raw_in if order == "input_first" else flipped
            bot = flipped if order == "input_first" else raw_in
            for r in range(ih):
                if list(raw_out[r]) != list(top[r]):
                    return False
                if list(raw_out[ih + r]) != list(bot[r]):
                    return False
            return True
        else:  # horizontal
            if oh != ih or ow != 2 * iw:
                return False
            flipped = [list(reversed(row)) for row in raw_in]
            left = raw_in if order == "input_first" else flipped
            right = flipped if order == "input_first" else raw_in
            for r in range(ih):
                if list(raw_out[r][:iw]) != list(left[r]):
                    return False
                if list(raw_out[r][iw:]) != list(right[r]):
                    return False
            return True

    # ---- strategy: rectangle interior fill ------------------------------

    def _try_rect_interior_fill(self, example_pairs):
        """
        Detect: same grid size; input contains hollow rectangular borders of a
        single foreground color on a background; output equals input except
        each hollow rect's interior is filled with a color determined by the
        rect's interior dimensions. Map (interior_h, interior_w) -> fill_color
        is learned from training and applied to test rectangles.
        """
        if not example_pairs:
            return None

        size_to_fill = {}
        bg_color = None
        border_color = None

        for raw_in, raw_out in example_pairs:
            h = len(raw_in)
            w = len(raw_in[0]) if raw_in else 0
            if h == 0 or w == 0:
                return None
            if h != len(raw_out) or w != (len(raw_out[0]) if raw_out else 0):
                return None

            # Background = most-frequent color in input
            counts = {}
            for row in raw_in:
                for c in row:
                    counts[c] = counts.get(c, 0) + 1
            bg = max(counts, key=counts.get)

            # Foreground colors = everything else; require exactly one
            fg_set = {c for c in counts if c != bg}
            if len(fg_set) != 1:
                return None
            fg = next(iter(fg_set))

            if bg_color is None:
                bg_color, border_color = bg, fg
            elif (bg_color, border_color) != (bg, fg):
                return None

            rects = self._find_hollow_rects(raw_in, fg, bg)
            if not rects:
                return None

            # Build expected output: copy input, fill each rect interior
            # with the color present in raw_out at the interior cells.
            for (r0, c0, r1, c1) in rects:
                ih_int = r1 - r0 - 1
                iw_int = c1 - c0 - 1
                if ih_int < 1 or iw_int < 1:
                    return None
                fill = raw_out[r0 + 1][c0 + 1]
                # Interior must be uniform fill color in output
                for r in range(r0 + 1, r1):
                    for c in range(c0 + 1, c1):
                        if raw_out[r][c] != fill:
                            return None
                key = (ih_int, iw_int)
                if key in size_to_fill and size_to_fill[key] != fill:
                    return None
                size_to_fill[key] = fill

            # Verify all non-interior cells are unchanged
            interior_cells = set()
            for (r0, c0, r1, c1) in rects:
                for r in range(r0 + 1, r1):
                    for c in range(c0 + 1, c1):
                        interior_cells.add((r, c))
            for r in range(h):
                for c in range(w):
                    if (r, c) in interior_cells:
                        continue
                    if raw_in[r][c] != raw_out[r][c]:
                        return None

        if not size_to_fill:
            return None
        return {
            "type": "rect_interior_fill",
            "background": bg_color,
            "border": border_color,
            "size_to_fill": {f"{k[0]}x{k[1]}": v for k, v in size_to_fill.items()},
            "confidence": 1.0,
        }

    @staticmethod
    def _find_hollow_rects(raw, fg, bg):
        """Find all hollow rectangles of color fg with interior color bg.
        Returns list of (r0, c0, r1, c1) bounding boxes."""
        h = len(raw)
        w = len(raw[0]) if raw else 0

        # Find connected components of fg cells (4-connected)
        visited = [[False] * w for _ in range(h)]
        rects = []

        for r in range(h):
            for c in range(w):
                if raw[r][c] != fg or visited[r][c]:
                    continue
                # BFS
                comp = []
                queue = [(r, c)]
                while queue:
                    rr, cc = queue.pop(0)
                    if rr < 0 or rr >= h or cc < 0 or cc >= w:
                        continue
                    if visited[rr][cc] or raw[rr][cc] != fg:
                        continue
                    visited[rr][cc] = True
                    comp.append((rr, cc))
                    for dr, dc in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                        queue.append((rr + dr, cc + dc))

                if not comp:
                    continue
                rs = [p[0] for p in comp]
                cs = [p[1] for p in comp]
                r0, r1 = min(rs), max(rs)
                c0, c1 = min(cs), max(cs)
                width = c1 - c0 + 1
                height = r1 - r0 + 1
                if width < 3 or height < 3:
                    continue
                # Check border is all fg
                comp_set = set(comp)
                ok = True
                for cc in range(c0, c1 + 1):
                    if (r0, cc) not in comp_set or (r1, cc) not in comp_set:
                        ok = False
                        break
                if ok:
                    for rr in range(r0, r1 + 1):
                        if (rr, c0) not in comp_set or (rr, c1) not in comp_set:
                            ok = False
                            break
                if not ok:
                    continue
                # Check interior is all bg
                for rr in range(r0 + 1, r1):
                    for cc in range(c0 + 1, c1):
                        if raw[rr][cc] != bg:
                            ok = False
                            break
                    if not ok:
                        break
                # Component must be exactly the border (no extra fg cells)
                expected_border_size = 2 * (height + width) - 4
                if ok and len(comp) == expected_border_size:
                    rects.append((r0, c0, r1, c1))
        return rects

    # ---- strategy: staircase extend right -------------------------------

    def _try_staircase_extend_right(self, example_pairs):
        """
        Detect: every input is exactly one row of width w; output has
        oh = w // 2 rows and width w. Row 0 of the output equals the input;
        each subsequent row extends the colored prefix by one cell to the
        right (one more cell of the same fg color, rest background).
        """
        if not example_pairs:
            return None

        for raw_in, raw_out in example_pairs:
            if len(raw_in) != 1:
                return None
            w = len(raw_in[0])
            if w < 2:
                return None
            oh = len(raw_out)
            if oh != w // 2 or oh < 1:
                return None
            for row in raw_out:
                if len(row) != w:
                    return None

            # The prefix color (fg) is the leftmost cell; the rest must be a
            # single different background color.
            row0 = list(raw_in[0])
            distinct = set(row0)
            if len(distinct) != 2:
                return None
            fg = row0[0]
            bg = next(v for v in distinct if v != fg)

            n = 0
            while n < w and row0[n] == fg:
                n += 1
            if n == 0 or any(v != bg for v in row0[n:]):
                return None

            # Verify each output row
            for i in range(oh):
                expected = [fg] * (n + i) + [bg] * (w - n - i)
                if list(raw_out[i]) != expected:
                    return None

        return {"type": "staircase_extend_right", "confidence": 1.0}


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
        if rule_type == "bbox_fill":
            return self._apply_bbox_fill(rule, input_grid)
        if rule_type == "axis_mirror_recolor":
            return self._apply_axis_mirror_recolor(rule, input_grid)
        if rule_type == "integer_upscale":
            return self._apply_integer_upscale(rule, input_grid)
        if rule_type == "stack_with_mirror":
            return self._apply_stack_with_mirror(rule, input_grid)
        if rule_type == "rect_interior_fill":
            return self._apply_rect_interior_fill(rule, input_grid)
        if rule_type == "staircase_extend_right":
            return self._apply_staircase_extend_right(rule, input_grid)
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

    def _apply_bbox_fill(self, rule, input_grid):
        raw = input_grid.raw
        h = len(raw)
        w = len(raw[0]) if raw else 0
        marker = rule.get("marker")
        fg = rule.get("foreground")
        bg = rule.get("background")
        if marker is None or fg is None or bg is None:
            return None

        rows = [r for r in range(h) for c in range(w) if raw[r][c] == fg]
        cols = [c for r in range(h) for c in range(w) if raw[r][c] == fg]
        if not rows:
            return [row[:] for row in raw]
        r0, r1 = min(rows), max(rows)
        c0, c1 = min(cols), max(cols)

        out = [row[:] for row in raw]
        for r in range(r0, r1 + 1):
            for c in range(c0, c1 + 1):
                if out[r][c] == bg:
                    out[r][c] = marker
        return out

    def _apply_axis_mirror_recolor(self, rule, input_grid):
        raw = input_grid.raw
        h = len(raw)
        w = len(raw[0]) if raw else 0
        marker = rule.get("marker")
        fg = rule.get("foreground")
        axis = rule.get("axis", "horizontal")
        if marker is None or fg is None:
            return None

        out = [row[:] for row in raw]
        for r in range(h):
            for c in range(w):
                if raw[r][c] != fg:
                    continue
                if axis == "horizontal":
                    rr, cc = r, w - 1 - c
                else:
                    rr, cc = h - 1 - r, c
                if (r, c) == (rr, cc):
                    continue
                if raw[rr][cc] == fg:
                    out[r][c] = marker
        return out

    def _apply_integer_upscale(self, rule, input_grid):
        raw = input_grid.raw
        k = rule.get("factor")
        if not isinstance(k, int) or k < 2:
            return None
        out = []
        for row in raw:
            new_row = []
            for v in row:
                new_row.extend([v] * k)
            for _ in range(k):
                out.append(new_row[:])
        return out

    def _apply_stack_with_mirror(self, rule, input_grid):
        raw = input_grid.raw
        direction = rule.get("direction")
        order = rule.get("order")
        if direction not in ("vertical", "horizontal"):
            return None
        if order not in ("input_first", "flip_first"):
            return None

        if direction == "vertical":
            flipped = list(reversed([row[:] for row in raw]))
            top = [row[:] for row in raw] if order == "input_first" else flipped
            bot = flipped if order == "input_first" else [row[:] for row in raw]
            return [r[:] for r in top] + [r[:] for r in bot]
        else:
            flipped = [list(reversed(row)) for row in raw]
            left = [row[:] for row in raw] if order == "input_first" else flipped
            right = flipped if order == "input_first" else [row[:] for row in raw]
            return [list(left[r]) + list(right[r]) for r in range(len(raw))]

    def _apply_rect_interior_fill(self, rule, input_grid):
        raw = input_grid.raw
        h = len(raw)
        w = len(raw[0]) if raw else 0
        bg = rule.get("background")
        fg = rule.get("border")
        size_to_fill_raw = rule.get("size_to_fill") or {}
        if bg is None or fg is None:
            return None
        size_to_fill = {}
        for k, v in size_to_fill_raw.items():
            try:
                a, b = k.split("x")
                size_to_fill[(int(a), int(b))] = v
            except ValueError:
                continue

        rects = GeneralizeOperator._find_hollow_rects(raw, fg, bg)
        out = [row[:] for row in raw]
        for (r0, c0, r1, c1) in rects:
            ih = r1 - r0 - 1
            iw = c1 - c0 - 1
            fill = size_to_fill.get((ih, iw))
            if fill is None:
                continue
            for r in range(r0 + 1, r1):
                for c in range(c0 + 1, c1):
                    out[r][c] = fill
        return out

    def _apply_staircase_extend_right(self, rule, input_grid):
        raw = input_grid.raw
        if len(raw) != 1:
            return None
        row0 = list(raw[0])
        w = len(row0)
        if w < 2:
            return None
        distinct = set(row0)
        if len(distinct) != 2:
            return None
        fg = row0[0]
        bg = next(v for v in distinct if v != fg)
        n = 0
        while n < w and row0[n] == fg:
            n += 1
        if n == 0 or any(v != bg for v in row0[n:]):
            return None
        oh = w // 2
        out = []
        for i in range(oh):
            cells = [fg] * (n + i) + [bg] * (w - n - i)
            out.append(cells)
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
