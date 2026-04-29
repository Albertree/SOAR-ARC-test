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

        # Strategy 0: ricochet ray — single 'shooter' cell on a grid edge
        #   shoots a ray of its own color into the grid, ricocheting 90°
        #   off each isolated 'marker' cell. Tried first because the
        #   sequential-recolor strategy can false-positive on these tasks.
        rule = self._try_ricochet_ray(example_pairs)

        # Strategy 0b: mirror shoot anchor — divider line splits grid into
        #   top/bottom; bottom has anchor+pointer-trail objects; top has
        #   marker cells at mirror of anchors. Output: each anchor moves
        #   to far end of its pointer trail; each marker moves to mirror
        #   of new anchor position.
        if rule is None:
            rule = self._try_mirror_shoot_anchor(example_pairs)

        # Strategy 1: sequential recoloring (e.g., color objects 1, 2, 3, ...)
        if rule is None:
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

        # Strategy 8: corner quadrant fill — 4 single-cell corner markers
        #   surround a solid inner rectangle which is split into quadrants
        if rule is None:
            rule = self._try_corner_quadrant_fill(example_pairs)

        # Strategy 9: diamond connector — collinear '+'-shaped 4-cell objects
        #   are joined by lines of a marker color
        if rule is None:
            rule = self._try_diamond_connector(example_pairs)

        # Strategy 10: axis line keep — output preserves a single row or
        #   column of the input; everything else collapses to background
        if rule is None:
            rule = self._try_axis_line_keep(example_pairs)

        # Strategy 11: recolor by component size — single fg color split into
        #   connected components, each recolored by cell count
        if rule is None:
            rule = self._try_recolor_by_size(example_pairs)

        # Strategy 12: rect interior marker fill — hollow-border rectangles
        #   get interior background cells filled with a constant marker color,
        #   while pre-existing foreground cells inside are preserved
        if rule is None:
            rule = self._try_rect_interior_marker_fill(example_pairs)

        # Strategy 13: object extract + color swap — input has bg + exactly two
        #   non-background colors forming a bounded object; output is the
        #   object's bbox with the two non-bg colors swapped
        if rule is None:
            rule = self._try_object_extract_swap(example_pairs)

        # Strategy 14: keep solid rectangles — keep only foreground components
        #   that fill their bounding box solidly with both dimensions >= 2;
        #   erase scattered/non-rectangular foreground cells to background
        if rule is None:
            rule = self._try_keep_solid_rectangles(example_pairs)

        # Strategy 15: tile pattern vertical — input has all-bg top rows and
        #   a non-bg pattern at the bottom; output tiles the pattern upward
        #   anchored to the bottom of the grid
        if rule is None:
            rule = self._try_tile_pattern_vertical(example_pairs)

        # Strategy 16: diagonal tail extend — input has a solid 2x2 fg block
        #   plus 1-4 tail cells at diagonal-adjacent positions; each tail is
        #   extended in its diagonal direction until the grid edge
        if rule is None:
            rule = self._try_diagonal_tail_extend(example_pairs)

        # Strategy 17: corner diagonal 2x2 — input has a 2x2 block of 4 unique
        #   non-bg colors; output places 2x2 blocks at offsets (+/-2, +/-2)
        #   from the source's top-left, each filled with the diagonally
        #   opposite cell's color (clipped to grid bounds)
        if rule is None:
            rule = self._try_corner_diagonal_2x2(example_pairs)

        # Strategy 18: rotational quadrants 2x — square HxH input becomes
        #   2H x 2H output with TL=input, TR=rot90 CCW, BL=rot180,
        #   BR=rot90 CW
        if rule is None:
            rule = self._try_rotational_quadrants_2x(example_pairs)

        # Strategy 19: inside marker count 3x3 — input has bg + a rectangle
        #   border color + a third 'marker' color; output is 3x3 with N
        #   marker cells filled in row-major order (N = marker count
        #   strictly inside the rectangle)
        if rule is None:
            rule = self._try_inside_marker_count_3x3(example_pairs)

        # Strategy 20: corner L shoot — each isolated non-bg pixel projects
        #   an L-shape (vertical + horizontal arm) to the two grid edges
        #   meeting at its nearest Manhattan corner
        if rule is None:
            rule = self._try_corner_l_shoot(example_pairs)

        # Strategy 21: concentric ring reverse — input is concentric
        #   rectangular layers each painted in a single color; output is the
        #   same shape with the layer color order reversed
        if rule is None:
            rule = self._try_concentric_ring_reverse(example_pairs)

        # Strategy 22: square corner marker — each connected component that
        #   forms a square (h==w>=2) and is either a complete hollow border
        #   or a solid filled block gets 8 marker cells placed orthogonally
        #   adjacent to its 4 corners (just outside the bbox)
        if rule is None:
            rule = self._try_square_corner_marker(example_pairs)

        # Strategy 23: plus center marker — wherever a "+" of 8 fg cells
        #   surrounds a bg cell (offsets ±2 and ±3 on each axis), the center
        #   cell becomes a constant marker color
        if rule is None:
            rule = self._try_plus_center_marker(example_pairs)

        # Strategy 24: rotational 4-fold kaleidoscope — output is
        #   4*H by 4*W with each 2x2 tile-quadrant filled by a rotation of
        #   input tiled 2x2: BR=identity, TR=rot90CW, TL=rot180, BL=rot90CCW
        if rule is None:
            rule = self._try_rotational_4fold(example_pairs)

        # Strategy 25: cross zone fill — single main line + several
        #   perpendicular cross-lines partition the grid into zones; each
        #   background row/col gets its nearest cross-line color, main and
        #   intersect colors swap at intersections
        if rule is None:
            rule = self._try_cross_zone_fill(example_pairs)

        # Strategy 26: plus majority color — input has scattered 'marker'
        #   cells whose 4 cardinal neighbors are all the same color; output
        #   is 1x1 with the most common surrounding color
        if rule is None:
            rule = self._try_plus_majority_color(example_pairs)

        # Strategy 27: framed recolor legend — input has a 'main' multicolor
        #   bordered region plus several 2-cell pairs that act as a color
        #   recoloring legend; output is the main region's bbox recolored
        if rule is None:
            rule = self._try_framed_recolor_legend(example_pairs)

        # Strategy 28: simple 1:1 color mapping
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

    # ---- strategy: corner quadrant fill ---------------------------------

    def _try_corner_quadrant_fill(self, example_pairs):
        """
        Detect: same grid size; input has 4 single-cell 'corner markers' of
        distinct non-background colors at the 4 corners of an axis-aligned
        rectangle, plus a solid block of one other 'inner' color filling the
        cells strictly inside that rectangle. The output replaces the corners
        with background and splits the inner block into four equal quadrants
        (TL/TR/BL/BR) recolored by the corresponding corner color.
        """
        if not example_pairs:
            return None

        inner_color = None

        for raw_in, raw_out in example_pairs:
            params = self._check_corner_quadrant_fill(raw_in, raw_out)
            if params is None:
                return None
            if inner_color is None:
                inner_color = params["inner_color"]
            elif inner_color != params["inner_color"]:
                return None

        if inner_color is None:
            return None
        return {
            "type": "corner_quadrant_fill",
            "inner_color": inner_color,
            "confidence": 1.0,
        }

    @staticmethod
    def _check_corner_quadrant_fill(raw_in, raw_out):
        h = len(raw_in)
        w = len(raw_in[0]) if raw_in else 0
        if h == 0 or w == 0:
            return None
        if h != len(raw_out) or w != (len(raw_out[0]) if raw_out else 0):
            return None

        counts = {}
        for row in raw_in:
            for c in row:
                counts[c] = counts.get(c, 0) + 1
        bg = max(counts, key=counts.get)

        # Find inner color: must be one color forming one or more solid
        # rectangles, each of even side lengths >= 2, with 4 single-cell
        # 'corner markers' at the diagonal-adjacent positions.
        groups = GeneralizeOperator._find_corner_quadrant_groups(raw_in, bg)
        if not groups:
            return None
        inner = groups[0]["inner_color"]
        for g in groups:
            if g["inner_color"] != inner:
                return None

        expected = GeneralizeOperator._apply_quadrant_groups(raw_in, groups, bg)
        for r in range(h):
            for c in range(w):
                if expected[r][c] != raw_out[r][c]:
                    return None

        return {"inner_color": inner}

    @staticmethod
    def _find_corner_quadrant_groups(raw, bg):
        """Find all (inner-rect + 4 corner-marker) groups in raw.

        A group consists of: a solid rectangle filled with one non-bg color
        (the 'inner color'), with side lengths >= 2 and even, surrounded by
        4 single cells at the diagonal-adjacent positions, each a distinct
        non-bg color (and distinct from the inner color). Returns a list of
        dicts {r0,r1,c0,c1, inner_color, tl, tr, bl, br}, or empty list."""
        h = len(raw)
        w = len(raw[0]) if raw else 0

        # 4-connected components of every non-bg color
        visited = [[False] * w for _ in range(h)]
        groups = []
        for r in range(h):
            for c in range(w):
                if raw[r][c] == bg or visited[r][c]:
                    continue
                color = raw[r][c]
                comp = []
                queue = [(r, c)]
                while queue:
                    rr, cc = queue.pop()
                    if rr < 0 or rr >= h or cc < 0 or cc >= w:
                        continue
                    if visited[rr][cc] or raw[rr][cc] != color:
                        continue
                    visited[rr][cc] = True
                    comp.append((rr, cc))
                    for dr, dc in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                        queue.append((rr + dr, cc + dc))
                if len(comp) < 4:
                    continue  # skip tiny components
                rs = [p[0] for p in comp]
                cs = [p[1] for p in comp]
                r0, r1 = min(rs), max(rs)
                c0, c1 = min(cs), max(cs)
                ih = r1 - r0 + 1
                iw = c1 - c0 + 1
                if ih < 2 or iw < 2:
                    continue
                if ih % 2 != 0 or iw % 2 != 0:
                    continue
                # Must be a solid rectangle
                if len(comp) != ih * iw:
                    continue
                # Corner positions are diagonally adjacent to the rectangle
                cr0, cc0 = r0 - 1, c0 - 1
                cr1, cc1 = r0 - 1, c1 + 1
                cr2, cc2 = r1 + 1, c0 - 1
                cr3, cc3 = r1 + 1, c1 + 1
                if (cr0 < 0 or cc0 < 0 or cr3 >= h or cc3 >= w):
                    continue
                tl_v = raw[cr0][cc0]
                tr_v = raw[cr1][cc1]
                bl_v = raw[cr2][cc2]
                br_v = raw[cr3][cc3]
                corner_vals = [tl_v, tr_v, bl_v, br_v]
                if any(v == bg or v == color for v in corner_vals):
                    continue
                if len(set(corner_vals)) != 4:
                    continue
                # Each corner cell must be isolated: 4-neighbours all bg
                ok = True
                for (rr, cc) in [(cr0, cc0), (cr1, cc1), (cr2, cc2), (cr3, cc3)]:
                    for dr, dc in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                        nr, nc = rr + dr, cc + dc
                        if 0 <= nr < h and 0 <= nc < w:
                            if raw[nr][nc] != bg:
                                ok = False
                                break
                    if not ok:
                        break
                if not ok:
                    continue
                groups.append({
                    "r0": r0, "r1": r1, "c0": c0, "c1": c1,
                    "inner_color": color,
                    "tl": tl_v, "tr": tr_v, "bl": bl_v, "br": br_v,
                    "tl_pos": (cr0, cc0), "tr_pos": (cr1, cc1),
                    "bl_pos": (cr2, cc2), "br_pos": (cr3, cc3),
                })
        return groups

    @staticmethod
    def _apply_quadrant_groups(raw, groups, bg):
        out = [list(row) for row in raw]
        for g in groups:
            r0, r1, c0, c1 = g["r0"], g["r1"], g["c0"], g["c1"]
            ih = r1 - r0 + 1
            iw = c1 - c0 + 1
            hh, ww = ih // 2, iw // 2
            # Clear corner markers
            for key in ("tl_pos", "tr_pos", "bl_pos", "br_pos"):
                rr, cc = g[key]
                out[rr][cc] = bg
            # Fill quadrants of inner rect
            for r in range(r0, r1 + 1):
                for c in range(c0, c1 + 1):
                    is_top = r < r0 + hh
                    is_left = c < c0 + ww
                    if is_top and is_left:
                        out[r][c] = g["tl"]
                    elif is_top:
                        out[r][c] = g["tr"]
                    elif is_left:
                        out[r][c] = g["bl"]
                    else:
                        out[r][c] = g["br"]
        return out

    # ---- strategy: diamond connector ------------------------------------

    def _try_diamond_connector(self, example_pairs):
        """
        Detect: same grid size; input contains '+'-shaped 4-cell diamond
        markers (one foreground cell at each of N/S/E/W around a background
        center, with all 4 diagonal cells being background). Each pair of
        adjacent collinear diamonds (sharing a row or column with no other
        diamond between them on that line) is joined in the output by a
        line of a single 'connector' color filling the cells strictly
        between their inner '+' tips.
        """
        if not example_pairs:
            return None

        connector = None
        fg_color = None

        for raw_in, raw_out in example_pairs:
            h = len(raw_in)
            w = len(raw_in[0]) if raw_in else 0
            if h != len(raw_out) or w != (len(raw_out[0]) if raw_out else 0):
                return None

            in_colors = {c for row in raw_in for c in row}
            out_colors = {c for row in raw_out for c in row}
            new_colors = out_colors - in_colors
            if len(new_colors) != 1:
                return None
            marker = next(iter(new_colors))
            if connector is None:
                connector = marker
            elif connector != marker:
                return None

            counts = {}
            for row in raw_in:
                for c in row:
                    counts[c] = counts.get(c, 0) + 1
            bg = max(counts, key=counts.get)
            fg_set = in_colors - {bg}
            if len(fg_set) != 1:
                return None
            fg = next(iter(fg_set))
            if fg_color is None:
                fg_color = fg
            elif fg_color != fg:
                return None

            diamonds = self._find_diamonds(raw_in, fg, bg)
            if len(diamonds) < 2:
                return None

            expected = [list(row) for row in raw_in]
            self._draw_diamond_connectors(expected, diamonds, marker)

            for r in range(h):
                for c in range(w):
                    if expected[r][c] != raw_out[r][c]:
                        return None

        if connector is None or fg_color is None:
            return None
        return {
            "type": "diamond_connector",
            "connector": connector,
            "foreground": fg_color,
            "confidence": 1.0,
        }

    @staticmethod
    def _find_diamonds(raw, fg, bg):
        h = len(raw)
        w = len(raw[0]) if raw else 0
        centers = []
        for r in range(1, h - 1):
            for c in range(1, w - 1):
                if raw[r][c] != bg:
                    continue
                if (raw[r - 1][c] == fg and raw[r + 1][c] == fg
                        and raw[r][c - 1] == fg and raw[r][c + 1] == fg
                        and raw[r - 1][c - 1] == bg and raw[r - 1][c + 1] == bg
                        and raw[r + 1][c - 1] == bg and raw[r + 1][c + 1] == bg):
                    centers.append((r, c))
        return centers

    @staticmethod
    def _draw_diamond_connectors(grid, diamonds, marker):
        by_row = {}
        by_col = {}
        for r, c in diamonds:
            by_row.setdefault(r, []).append(c)
            by_col.setdefault(c, []).append(r)
        for r, cols in by_row.items():
            cols = sorted(cols)
            for i in range(len(cols) - 1):
                cl, cr = cols[i], cols[i + 1]
                for cc in range(cl + 2, cr - 1):
                    grid[r][cc] = marker
        for c, rows in by_col.items():
            rows = sorted(rows)
            for i in range(len(rows) - 1):
                rl, rr = rows[i], rows[i + 1]
                for rr2 in range(rl + 2, rr - 1):
                    grid[rr2][c] = marker

    # ---- strategy: axis line keep ---------------------------------------

    def _try_axis_line_keep(self, example_pairs):
        """
        Detect: same grid size; output equals input on a single 'kept' line
        (one row or one column) and equals a single background color
        everywhere else. The line position must be derivable consistently
        across all examples (e.g., always the middle row/column).
        """
        if not example_pairs:
            return None

        for axis, pos_kind in (("col", "middle"), ("row", "middle")):
            params = self._check_axis_line_keep(example_pairs, axis, pos_kind)
            if params is not None:
                return {
                    "type": "axis_line_keep",
                    "axis": axis,
                    "position": pos_kind,
                    "background": params["background"],
                    "confidence": 1.0,
                }
        return None

    @staticmethod
    def _check_axis_line_keep(example_pairs, axis, pos_kind):
        bg_color = None
        for raw_in, raw_out in example_pairs:
            h = len(raw_in)
            w = len(raw_in[0]) if raw_in else 0
            if h == 0 or w == 0:
                return None
            if h != len(raw_out) or w != (len(raw_out[0]) if raw_out else 0):
                return None
            if pos_kind == "middle":
                k = (w // 2) if axis == "col" else (h // 2)
            else:
                return None

            local_bg = None
            for r in range(h):
                for c in range(w):
                    on_line = (axis == "col" and c == k) or (axis == "row" and r == k)
                    if on_line:
                        if raw_out[r][c] != raw_in[r][c]:
                            return None
                    else:
                        if local_bg is None:
                            local_bg = raw_out[r][c]
                        elif raw_out[r][c] != local_bg:
                            return None
            if local_bg is None:
                return None
            if bg_color is None:
                bg_color = local_bg
            elif bg_color != local_bg:
                return None
        if bg_color is None:
            return None
        return {"background": bg_color}

    # ---- strategy: recolor by component size ----------------------------

    def _try_recolor_by_size(self, example_pairs):
        """
        Detect: same grid size; input has one background color and one
        foreground color; connected components of foreground cells in the
        input are each recolored uniformly in the output to a color that
        depends solely on the component's cell count. A consistent
        size -> color mapping must hold across all examples. Non-foreground
        cells are unchanged.
        """
        if not example_pairs:
            return None

        size_to_color = {}
        fg_color = None
        bg_color = None

        for raw_in, raw_out in example_pairs:
            h = len(raw_in)
            w = len(raw_in[0]) if raw_in else 0
            if h == 0 or w == 0:
                return None
            if h != len(raw_out) or w != (len(raw_out[0]) if raw_out else 0):
                return None

            counts = {}
            for row in raw_in:
                for c in row:
                    counts[c] = counts.get(c, 0) + 1
            bg_local = max(counts, key=counts.get)
            in_colors = set(counts.keys())
            fg_set = in_colors - {bg_local}
            if len(fg_set) != 1:
                return None
            fg_local = next(iter(fg_set))

            if bg_color is None:
                bg_color, fg_color = bg_local, fg_local
            elif (bg_color, fg_color) != (bg_local, fg_local):
                return None

            comps = self._find_components(raw_in, fg_local)
            if not comps:
                return None
            for comp in comps:
                out_colors = {raw_out[r][c] for (r, c) in comp}
                if len(out_colors) != 1:
                    return None
                out_c = next(iter(out_colors))
                size = len(comp)
                if size in size_to_color and size_to_color[size] != out_c:
                    return None
                size_to_color[size] = out_c

            # Non-foreground cells must be unchanged
            for r in range(h):
                for c in range(w):
                    if raw_in[r][c] != fg_local and raw_out[r][c] != raw_in[r][c]:
                        return None

        if not size_to_color or fg_color is None:
            return None
        return {
            "type": "recolor_by_size",
            "foreground": fg_color,
            "background": bg_color,
            "size_to_color": {str(k): v for k, v in size_to_color.items()},
            "confidence": 1.0,
        }

    # ---- strategy: rect interior marker fill ----------------------------

    def _try_rect_interior_marker_fill(self, example_pairs):
        """
        Detect: same grid size; one bg + one fg in input; one new color in
        output (the marker, consistent across pairs). Input contains one or
        more axis-aligned rectangles whose 4 borders are entirely fg (size
        >= 3x3). Output equals input except interior bg cells of every such
        rectangle become the marker color (existing interior fg cells stay).
        """
        if not example_pairs:
            return None

        marker = None
        fg_color = None
        bg_color = None

        for raw_in, raw_out in example_pairs:
            h = len(raw_in)
            w = len(raw_in[0]) if raw_in else 0
            if h == 0 or w == 0:
                return None
            if h != len(raw_out) or w != (len(raw_out[0]) if raw_out else 0):
                return None

            counts = {}
            for row in raw_in:
                for c in row:
                    counts[c] = counts.get(c, 0) + 1
            bg = max(counts, key=counts.get)
            in_colors = set(counts.keys())
            fg_set = in_colors - {bg}
            if len(fg_set) != 1:
                return None
            fg = next(iter(fg_set))

            new_colors = (
                {c for row in raw_out for c in row} - in_colors
            )
            if len(new_colors) != 1:
                return None
            m = next(iter(new_colors))

            if marker is None:
                marker, fg_color, bg_color = m, fg, bg
            elif (m, fg, bg) != (marker, fg_color, bg_color):
                return None

            rects = self._find_rect_borders(raw_in, fg, min_h=3, min_w=3)
            if not rects:
                return None

            interior_cells = set()
            for (r0, c0, r1, c1) in rects:
                for r in range(r0 + 1, r1):
                    for c in range(c0 + 1, c1):
                        interior_cells.add((r, c))

            for r in range(h):
                for c in range(w):
                    if (r, c) in interior_cells and raw_in[r][c] == bg:
                        if raw_out[r][c] != m:
                            return None
                    else:
                        if raw_out[r][c] != raw_in[r][c]:
                            return None

        if marker is None:
            return None
        return {
            "type": "rect_interior_marker_fill",
            "marker": marker,
            "foreground": fg_color,
            "background": bg_color,
            "confidence": 1.0,
        }

    @staticmethod
    def _find_rect_borders(raw, fg, min_h=3, min_w=3):
        """Find all axis-aligned rectangles whose 4 borders are entirely fg.
        Returns a list of (r0, c0, r1, c1)."""
        h = len(raw)
        w = len(raw[0]) if raw else 0
        rects = []
        for r0 in range(h):
            for r1 in range(r0 + min_h - 1, h):
                for c0 in range(w):
                    if raw[r0][c0] != fg or raw[r1][c0] != fg:
                        continue
                    for c1 in range(c0 + min_w - 1, w):
                        if raw[r0][c1] != fg or raw[r1][c1] != fg:
                            continue
                        if any(raw[r0][c] != fg for c in range(c0, c1 + 1)):
                            continue
                        if any(raw[r1][c] != fg for c in range(c0, c1 + 1)):
                            continue
                        if any(raw[r][c0] != fg for r in range(r0, r1 + 1)):
                            continue
                        if any(raw[r][c1] != fg for r in range(r0, r1 + 1)):
                            continue
                        rects.append((r0, c0, r1, c1))
        return rects

    # ---- strategy: object extract + color swap --------------------------

    def _try_object_extract_swap(self, example_pairs):
        """
        Detect: input has one bg color and exactly two non-bg colors A and B
        forming a single bounded object; output equals the object's bbox
        region with A and B swapped (bg cells inside the bbox stay bg). The
        specific A/B colors may differ per pair, but the swap rule is the
        same: output = swap(input bbox, A<->B).
        """
        if not example_pairs:
            return None

        for raw_in, raw_out in example_pairs:
            h_in = len(raw_in)
            w_in = len(raw_in[0]) if raw_in else 0
            h_out = len(raw_out)
            w_out = len(raw_out[0]) if raw_out else 0
            if h_in == 0 or w_in == 0 or h_out == 0 or w_out == 0:
                return None

            counts = {}
            for row in raw_in:
                for c in row:
                    counts[c] = counts.get(c, 0) + 1
            bg = max(counts, key=counts.get)
            non_bg = [c for c in counts if c != bg]
            if len(non_bg) != 2:
                return None

            rows = [r for r in range(h_in)
                    for c in range(w_in) if raw_in[r][c] != bg]
            cols = [c for r in range(h_in)
                    for c in range(w_in) if raw_in[r][c] != bg]
            if not rows:
                return None
            r0, r1 = min(rows), max(rows)
            c0, c1 = min(cols), max(cols)
            obj_h = r1 - r0 + 1
            obj_w = c1 - c0 + 1

            if h_out != obj_h or w_out != obj_w:
                return None

            a, b = non_bg
            for r in range(obj_h):
                for c in range(obj_w):
                    v = raw_in[r0 + r][c0 + c]
                    if v == a:
                        expected = b
                    elif v == b:
                        expected = a
                    else:
                        expected = v
                    if raw_out[r][c] != expected:
                        return None

        return {
            "type": "object_extract_swap",
            "confidence": 1.0,
        }

    # ---- strategy: keep solid rectangles --------------------------------

    def _try_keep_solid_rectangles(self, example_pairs):
        """
        Detect: same grid size; one bg + one fg in input; output equals input
        except foreground cells that do NOT belong to any solid 2x2+ block of
        fg cells are erased to background. A foreground cell is kept iff at
        least one of the four 2x2 windows containing it is entirely fg.
        """
        if not example_pairs:
            return None

        any_kept = False
        any_erased = False

        for raw_in, raw_out in example_pairs:
            h = len(raw_in)
            w = len(raw_in[0]) if raw_in else 0
            if h == 0 or w == 0:
                return None
            if h != len(raw_out) or w != (len(raw_out[0]) if raw_out else 0):
                return None

            counts = {}
            for row in raw_in:
                for c in row:
                    counts[c] = counts.get(c, 0) + 1
            bg = max(counts, key=counts.get)
            fg_set = set(counts.keys()) - {bg}
            if len(fg_set) != 1:
                return None
            fg = next(iter(fg_set))

            keep_cells = self._compute_solid_block_keep(raw_in, fg)

            for r in range(h):
                for c in range(w):
                    if raw_in[r][c] == fg and (r, c) not in keep_cells:
                        if raw_out[r][c] != bg:
                            return None
                        any_erased = True
                    else:
                        if raw_out[r][c] != raw_in[r][c]:
                            return None
                        if raw_in[r][c] == fg:
                            any_kept = True

        if not any_kept or not any_erased:
            return None
        return {
            "type": "keep_solid_rectangles",
            "confidence": 1.0,
        }

    @staticmethod
    def _compute_solid_block_keep(raw, fg):
        """Cells of color fg that lie in some 2x2 all-fg window."""
        h = len(raw)
        w = len(raw[0]) if raw else 0
        keep = set()
        for r in range(h - 1):
            for c in range(w - 1):
                if (raw[r][c] == fg and raw[r][c + 1] == fg
                        and raw[r + 1][c] == fg and raw[r + 1][c + 1] == fg):
                    keep.add((r, c))
                    keep.add((r, c + 1))
                    keep.add((r + 1, c))
                    keep.add((r + 1, c + 1))
        return keep

    # ---- strategy: tile pattern vertical --------------------------------

    def _try_tile_pattern_vertical(self, example_pairs):
        """
        Detect: same grid size; the top portion of the input is uniform
        background; the bottom portion contains a non-bg pattern. The output
        tiles that pattern upward anchored to the bottom of the grid:
            output[r] = pattern[(r - R) mod pattern_h]
        where R is the first row containing a non-bg cell, and pattern is
        rows R..h-1 of the input.
        """
        if not example_pairs:
            return None

        any_change = False
        for raw_in, raw_out in example_pairs:
            h = len(raw_in)
            w = len(raw_in[0]) if raw_in else 0
            if h == 0 or w == 0:
                return None
            if h != len(raw_out) or w != (len(raw_out[0]) if raw_out else 0):
                return None

            counts = {}
            for row in raw_in:
                for c in row:
                    counts[c] = counts.get(c, 0) + 1
            bg = max(counts, key=counts.get)

            first_row = None
            for r in range(h):
                if any(c != bg for c in raw_in[r]):
                    first_row = r
                    break
            if first_row is None or first_row == 0:
                return None

            # Top rows must be all bg
            for r in range(first_row):
                for c in range(w):
                    if raw_in[r][c] != bg:
                        return None

            pattern_h = h - first_row
            if pattern_h < 1:
                return None
            pattern = raw_in[first_row:]

            for r in range(h):
                expected = pattern[(r - first_row) % pattern_h]
                if list(raw_out[r]) != list(expected):
                    return None
                if r < first_row and list(raw_out[r]) != list(raw_in[r]):
                    any_change = True

        if not any_change:
            return None
        return {"type": "tile_pattern_vertical", "confidence": 1.0}

    # ---- strategy: diagonal tail extend ---------------------------------

    def _try_diagonal_tail_extend(self, example_pairs):
        """
        Detect: input has one bg color and one fg color. The fg cells form
        a single solid 2x2 block plus 0..4 'tail' cells at diagonal-adjacent
        positions to the 2x2 corners (TL: (r0-1,c0-1), TR: (r0-1,c1+1),
        BL: (r1+1,c0-1), BR: (r1+1,c1+1)). The output equals the input plus
        each tail extended in its diagonal direction one step at a time
        until the grid edge.
        """
        if not example_pairs:
            return None

        any_extension = False

        for raw_in, raw_out in example_pairs:
            h = len(raw_in)
            w = len(raw_in[0]) if raw_in else 0
            if h == 0 or w == 0:
                return None
            if h != len(raw_out) or w != (len(raw_out[0]) if raw_out else 0):
                return None

            counts = {}
            for row in raw_in:
                for c in row:
                    counts[c] = counts.get(c, 0) + 1
            bg = max(counts, key=counts.get)
            fg_set = set(counts.keys()) - {bg}
            if len(fg_set) != 1:
                return None
            fg = next(iter(fg_set))

            params = self._find_2x2_block_with_tails(raw_in, fg, bg)
            if params is None:
                return None
            r0, c0 = params["r0"], params["c0"]
            tails = params["tails"]
            if not tails:
                return None

            expected = [row[:] for row in raw_in]
            self._draw_diagonal_tails(expected, r0, c0, tails, fg)

            for r in range(h):
                for c in range(w):
                    if expected[r][c] != raw_out[r][c]:
                        return None
                    if expected[r][c] != raw_in[r][c]:
                        any_extension = True

        if not any_extension:
            return None
        return {"type": "diagonal_tail_extend", "confidence": 1.0}

    @staticmethod
    def _find_2x2_block_with_tails(raw, fg, bg):
        """Locate a unique solid 2x2 block of fg cells whose other fg cells
        are only at diagonal-adjacent corner positions. Returns
        {r0, c0, tails: [(dr, dc), ...]} or None.
        Tails are described by direction (-1,-1)/(-1,+1)/(+1,-1)/(+1,+1).
        """
        h = len(raw)
        w = len(raw[0]) if raw else 0
        # Find all 2x2 fg blocks
        blocks = []
        for r in range(h - 1):
            for c in range(w - 1):
                if (raw[r][c] == fg and raw[r][c + 1] == fg
                        and raw[r + 1][c] == fg and raw[r + 1][c + 1] == fg):
                    blocks.append((r, c))
        if len(blocks) != 1:
            return None
        r0, c0 = blocks[0]
        r1, c1 = r0 + 1, c0 + 1

        # Collect all fg positions
        fg_positions = {(r, c) for r in range(h) for c in range(w)
                        if raw[r][c] == fg}
        block_cells = {(r0, c0), (r0, c1), (r1, c0), (r1, c1)}
        tail_candidates = {
            (-1, -1): (r0 - 1, c0 - 1),
            (-1, +1): (r0 - 1, c1 + 1),
            (+1, -1): (r1 + 1, c0 - 1),
            (+1, +1): (r1 + 1, c1 + 1),
        }
        tails = []
        for direction, pos in tail_candidates.items():
            if pos in fg_positions:
                tails.append(direction)

        # All fg cells must be either the 2x2 block or a recognized tail
        recognized = set(block_cells)
        for d in tails:
            recognized.add(tail_candidates[d])
        if recognized != fg_positions:
            return None
        return {"r0": r0, "c0": c0, "tails": tails}

    @staticmethod
    def _draw_diagonal_tails(grid, r0, c0, tails, fg):
        h = len(grid)
        w = len(grid[0]) if grid else 0
        r1, c1 = r0 + 1, c0 + 1
        starts = {
            (-1, -1): (r0 - 1, c0 - 1),
            (-1, +1): (r0 - 1, c1 + 1),
            (+1, -1): (r1 + 1, c0 - 1),
            (+1, +1): (r1 + 1, c1 + 1),
        }
        for dr, dc in tails:
            sr, sc = starts[(dr, dc)]
            r, c = sr + dr, sc + dc
            while 0 <= r < h and 0 <= c < w:
                grid[r][c] = fg
                r += dr
                c += dc

    # ---- strategy: corner diagonal 2x2 ----------------------------------

    def _try_corner_diagonal_2x2(self, example_pairs):
        """
        Detect: same grid size; input has a single 2x2 axis-aligned block of
        four DISTINCT non-bg colors (TL/TR/BL/BR), with no other non-bg cells.
        Output equals input plus four 2x2 blocks placed at offsets
        (-2,-2), (-2,+2), (+2,-2), (+2,+2) from the source's TL corner. Each
        such block is filled with the source's diagonally opposite cell's
        color (TL->BR, TR->BL, BL->TR, BR->TL). Out-of-bounds cells of the
        block are simply not drawn (clipped).
        """
        if not example_pairs:
            return None

        for raw_in, raw_out in example_pairs:
            h = len(raw_in)
            w = len(raw_in[0]) if raw_in else 0
            if h == 0 or w == 0:
                return None
            if h != len(raw_out) or w != (len(raw_out[0]) if raw_out else 0):
                return None

            counts = {}
            for row in raw_in:
                for c in row:
                    counts[c] = counts.get(c, 0) + 1
            bg = max(counts, key=counts.get)

            non_bg_positions = [(r, c) for r in range(h) for c in range(w)
                                if raw_in[r][c] != bg]
            if len(non_bg_positions) != 4:
                return None
            rows = sorted({r for r, _ in non_bg_positions})
            cols = sorted({c for _, c in non_bg_positions})
            if len(rows) != 2 or len(cols) != 2:
                return None
            if rows[1] - rows[0] != 1 or cols[1] - cols[0] != 1:
                return None
            r0, c0 = rows[0], cols[0]
            r1, c1 = rows[1], cols[1]
            tl, tr, bl, br = (raw_in[r0][c0], raw_in[r0][c1],
                              raw_in[r1][c0], raw_in[r1][c1])
            if len({tl, tr, bl, br}) != 4:
                return None

            expected = [row[:] for row in raw_in]
            self._draw_corner_diagonal_blocks(expected, r0, c0,
                                              tl, tr, bl, br)
            for r in range(h):
                for c in range(w):
                    if expected[r][c] != raw_out[r][c]:
                        return None

        return {"type": "corner_diagonal_2x2", "confidence": 1.0}

    # ---- strategy: rotational quadrants 2x ------------------------------

    def _try_rotational_quadrants_2x(self, example_pairs):
        """
        Detect: square HxH input; output is 2H x 2H tiled from four
        rotations of the input as quadrants:
          TL = input          TR = rotate 90 CCW (input)
          BL = rotate 180     BR = rotate 90 CW
        """
        if not example_pairs:
            return None

        for raw_in, raw_out in example_pairs:
            h = len(raw_in)
            w = len(raw_in[0]) if raw_in else 0
            if h == 0 or w == 0 or h != w:
                return None
            oh = len(raw_out)
            ow = len(raw_out[0]) if raw_out else 0
            if oh != 2 * h or ow != 2 * w:
                return None
            expected = self._build_rotational_quadrants_2x(raw_in)
            for r in range(oh):
                for c in range(ow):
                    if expected[r][c] != raw_out[r][c]:
                        return None

        return {"type": "rotational_quadrants_2x", "confidence": 1.0}

    @staticmethod
    def _build_rotational_quadrants_2x(raw):
        h = len(raw)
        w = len(raw[0]) if raw else 0
        rot_ccw = [[raw[c][w - 1 - r] for c in range(h)] for r in range(w)]
        rot_cw = [[raw[h - 1 - c][r] for c in range(h)] for r in range(w)]
        rot_180 = [[raw[h - 1 - r][w - 1 - c] for c in range(w)]
                   for r in range(h)]
        out = [[0] * (2 * w) for _ in range(2 * h)]
        for r in range(h):
            for c in range(w):
                out[r][c] = raw[r][c]
                out[r][c + w] = rot_ccw[r][c]
                out[r + h][c] = rot_180[r][c]
                out[r + h][c + w] = rot_cw[r][c]
        return out

    # ---- strategy: inside marker count 3x3 ------------------------------

    def _try_inside_marker_count_3x3(self, example_pairs):
        """
        Detect: input has exactly 3 colors -- a background (most common),
        a 'border' color whose cells are exactly the 4 sides of one
        axis-aligned rectangle (size >= 3x3), and a 'marker' color (the
        third color). Output is always 3x3 painted with N marker cells in
        row-major order (top-left to bottom-right) where N is the count of
        marker cells strictly inside the rectangle's interior; remaining
        output cells are background. Requires 1 <= N <= 9.
        """
        if not example_pairs:
            return None

        for raw_in, raw_out in example_pairs:
            oh = len(raw_out)
            ow = len(raw_out[0]) if raw_out else 0
            if oh != 3 or ow != 3:
                return None
            params = self._inside_marker_count_3x3_params(raw_in)
            if params is None:
                return None
            bg, marker, n = params["bg"], params["marker"], params["n"]
            if not (1 <= n <= 9):
                return None
            expected = [[bg] * 3 for _ in range(3)]
            for k in range(n):
                expected[k // 3][k % 3] = marker
            for r in range(3):
                for c in range(3):
                    if expected[r][c] != raw_out[r][c]:
                        return None

        return {"type": "inside_marker_count_3x3", "confidence": 1.0}

    @staticmethod
    def _inside_marker_count_3x3_params(raw):
        h = len(raw)
        w = len(raw[0]) if raw else 0
        if h == 0 or w == 0:
            return None
        counts = {}
        for row in raw:
            for c in row:
                counts[c] = counts.get(c, 0) + 1
        if len(counts) != 3:
            return None
        bg = max(counts, key=counts.get)
        others = [c for c in counts if c != bg]

        qualifying = []
        for cand in others:
            positions = [(r, c) for r in range(h) for c in range(w)
                         if raw[r][c] == cand]
            if not positions:
                continue
            rs = [p[0] for p in positions]
            cs = [p[1] for p in positions]
            r0, r1 = min(rs), max(rs)
            c0, c1 = min(cs), max(cs)
            if r1 - r0 < 2 or c1 - c0 < 2:
                continue
            if not all((r in (r0, r1)) or (c in (c0, c1))
                       for r, c in positions):
                continue
            full = (
                all(raw[r0][c] == cand for c in range(c0, c1 + 1))
                and all(raw[r1][c] == cand for c in range(c0, c1 + 1))
                and all(raw[r][c0] == cand for r in range(r0, r1 + 1))
                and all(raw[r][c1] == cand for r in range(r0, r1 + 1))
            )
            if full:
                qualifying.append((cand, (r0, c0, r1, c1)))

        if len(qualifying) != 1:
            return None
        border, rect = qualifying[0]
        marker = next(c for c in others if c != border)
        r0, c0, r1, c1 = rect
        n = sum(
            1 for r in range(r0 + 1, r1) for c in range(c0 + 1, c1)
            if raw[r][c] == marker
        )
        return {"bg": bg, "border": border, "marker": marker, "n": n,
                "rect": rect}

    # ---- strategy: corner L shoot ---------------------------------------

    def _try_corner_l_shoot(self, example_pairs):
        """
        Detect: same grid size; input has a background (most common color)
        and one or more isolated single-cell non-bg pixels (no two non-bg
        cells are 4-adjacent). For each non-bg pixel at (r, c), the output
        draws an L-shape of that pixel's color: a vertical arm from (r, c)
        to (corner_r, c) and a horizontal arm from (r, c) to (r, corner_c),
        where (corner_r, corner_c) is the grid corner with smallest
        Manhattan distance to (r, c). All other output cells equal bg.
        """
        if not example_pairs:
            return None

        for raw_in, raw_out in example_pairs:
            h = len(raw_in)
            w = len(raw_in[0]) if raw_in else 0
            if h == 0 or w == 0:
                return None
            if h != len(raw_out) or w != (len(raw_out[0]) if raw_out else 0):
                return None
            counts = {}
            for row in raw_in:
                for c in row:
                    counts[c] = counts.get(c, 0) + 1
            bg = max(counts, key=counts.get)

            non_bg = [(r, c) for r in range(h) for c in range(w)
                      if raw_in[r][c] != bg]
            if not non_bg:
                return None
            for r, c in non_bg:
                for dr, dc in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                    nr, nc = r + dr, c + dc
                    if (0 <= nr < h and 0 <= nc < w
                            and raw_in[nr][nc] != bg):
                        return None

            expected = self._draw_corner_l_shoot(raw_in, bg)
            for r in range(h):
                for c in range(w):
                    if expected[r][c] != raw_out[r][c]:
                        return None

        return {"type": "corner_l_shoot", "confidence": 1.0}

    # ---- strategy: concentric ring reverse ------------------------------

    def _try_concentric_ring_reverse(self, example_pairs):
        """
        Detect: input is HxW (>=2 in each dim), tiled in concentric
        rectangular rings — each ring (cells where
        min(r, h-1-r, c, w-1-c) == k) painted a single uniform color.
        Output has the same shape with the per-ring colors reversed
        (innermost color becomes outermost). At least 2 distinct ring
        colors required so the transformation is non-trivial.
        """
        if not example_pairs:
            return None

        for raw_in, raw_out in example_pairs:
            h = len(raw_in)
            w = len(raw_in[0]) if raw_in else 0
            if h < 2 or w < 2:
                return None
            if h != len(raw_out) or w != (len(raw_out[0]) if raw_out else 0):
                return None
            in_layers = self._concentric_layers(raw_in)
            out_layers = self._concentric_layers(raw_out)
            if in_layers is None or out_layers is None:
                return None
            if len(set(in_layers)) < 2:
                return None
            if out_layers != list(reversed(in_layers)):
                return None

        return {"type": "concentric_ring_reverse", "confidence": 1.0}

    @staticmethod
    def _concentric_layers(raw):
        h = len(raw)
        w = len(raw[0]) if raw else 0
        if h == 0 or w == 0:
            return None
        L = (min(h, w) + 1) // 2
        layers = []
        for k in range(L):
            color = None
            for r in range(h):
                for c in range(w):
                    if min(r, h - 1 - r, c, w - 1 - c) != k:
                        continue
                    v = raw[r][c]
                    if color is None:
                        color = v
                    elif color != v:
                        return None
            if color is None:
                return None
            layers.append(color)
        return layers

    # ---- strategy: square corner marker ---------------------------------

    def _try_square_corner_marker(self, example_pairs):
        """
        Detect: same grid size; output introduces exactly one new color
        (marker), the same in every pair. For each non-background
        connected component whose bbox is a square (h == w >= 2) AND
        whose cells form either a complete hollow rectangle border or a
        solid filled square, the output places marker cells at the 8
        positions orthogonally adjacent to the 4 bbox corners (two per
        corner, one above/below and one left/right). All other cells
        match the input.
        """
        if not example_pairs:
            return None

        marker = None
        had_target = False
        for raw_in, raw_out in example_pairs:
            h = len(raw_in)
            w = len(raw_in[0]) if raw_in else 0
            if h == 0 or w == 0:
                return None
            if h != len(raw_out) or w != (len(raw_out[0]) if raw_out else 0):
                return None
            in_colors = {c for row in raw_in for c in row}
            out_colors = {c for row in raw_out for c in row}
            new_colors = out_colors - in_colors
            if len(new_colors) != 1:
                return None
            m = next(iter(new_colors))
            if marker is None:
                marker = m
            elif marker != m:
                return None
            targets = self._square_marker_targets(raw_in)
            if targets:
                had_target = True
            expected = self._draw_square_corner_markers(raw_in, targets, m)
            for r in range(h):
                for c in range(w):
                    if expected[r][c] != raw_out[r][c]:
                        return None

        if not had_target:
            return None
        return {"type": "square_corner_marker", "marker": marker,
                "confidence": 1.0}

    @staticmethod
    def _square_marker_targets(raw):
        h = len(raw)
        w = len(raw[0]) if raw else 0
        counts = {}
        for row in raw:
            for c in row:
                counts[c] = counts.get(c, 0) + 1
        bg = max(counts, key=counts.get)
        visited = [[False] * w for _ in range(h)]
        targets = []
        for r in range(h):
            for c in range(w):
                if raw[r][c] == bg or visited[r][c]:
                    continue
                color = raw[r][c]
                comp = []
                stack = [(r, c)]
                while stack:
                    rr, cc = stack.pop()
                    if rr < 0 or rr >= h or cc < 0 or cc >= w:
                        continue
                    if visited[rr][cc] or raw[rr][cc] != color:
                        continue
                    visited[rr][cc] = True
                    comp.append((rr, cc))
                    for dr, dc in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                        stack.append((rr + dr, cc + dc))
                rs = [p[0] for p in comp]
                cs = [p[1] for p in comp]
                r0, r1 = min(rs), max(rs)
                c0, c1 = min(cs), max(cs)
                ch = r1 - r0 + 1
                cw = c1 - c0 + 1
                if ch != cw or ch < 2:
                    continue
                cell_set = set(comp)
                is_solid = all(
                    (rr, cc) in cell_set
                    for rr in range(r0, r1 + 1)
                    for cc in range(c0, c1 + 1)
                )
                border = set()
                for cc in range(c0, c1 + 1):
                    border.add((r0, cc))
                    border.add((r1, cc))
                for rr in range(r0, r1 + 1):
                    border.add((rr, c0))
                    border.add((rr, c1))
                is_hollow = (cell_set == border)
                if is_solid or is_hollow:
                    targets.append((r0, c0, r1, c1))
        return targets

    @staticmethod
    def _draw_square_corner_markers(raw, targets, marker):
        h = len(raw)
        w = len(raw[0]) if raw else 0
        out = [row[:] for row in raw]
        for (r0, c0, r1, c1) in targets:
            for mr, mc in [
                (r0 - 1, c0), (r0, c0 - 1),
                (r0 - 1, c1), (r0, c1 + 1),
                (r1 + 1, c0), (r1, c0 - 1),
                (r1 + 1, c1), (r1, c1 + 1),
            ]:
                if 0 <= mr < h and 0 <= mc < w:
                    out[mr][mc] = marker
        return out

    # ---- strategy: plus center marker -----------------------------------

    def _try_plus_center_marker(self, example_pairs):
        """
        Detect: same grid size; output introduces exactly one new color
        (marker), the same in every pair. There exists a single fg color
        such that for every center (r, c) where the 8 cells at offsets
        (±2, 0), (±3, 0), (0, ±2), (0, ±3) are all fg and (r, c) is bg,
        the output places marker at (r, c). All other cells are unchanged.
        """
        if not example_pairs:
            return None

        marker = None
        fg_color = None
        had_target = False
        for raw_in, raw_out in example_pairs:
            h = len(raw_in)
            w = len(raw_in[0]) if raw_in else 0
            if h == 0 or w == 0:
                return None
            if h != len(raw_out) or w != (len(raw_out[0]) if raw_out else 0):
                return None
            in_colors = {c for row in raw_in for c in row}
            out_colors = {c for row in raw_out for c in row}
            new_colors = out_colors - in_colors
            if len(new_colors) != 1:
                return None
            m = next(iter(new_colors))
            if marker is None:
                marker = m
            elif marker != m:
                return None
            counts = {}
            for row in raw_in:
                for c in row:
                    counts[c] = counts.get(c, 0) + 1
            bg = max(counts, key=counts.get)
            non_bg = [c for c in counts if c != bg]
            if len(non_bg) != 1:
                return None
            fg = non_bg[0]
            if fg == marker:
                return None
            if fg_color is None:
                fg_color = fg
            elif fg_color != fg:
                return None
            expected = self._draw_plus_center_markers(raw_in, fg, marker)
            if not had_target:
                # check at least one center was placed in some pair
                for r in range(h):
                    for c in range(w):
                        if expected[r][c] != raw_in[r][c]:
                            had_target = True
                            break
                    if had_target:
                        break
            for r in range(h):
                for c in range(w):
                    if expected[r][c] != raw_out[r][c]:
                        return None
        if not had_target:
            return None
        return {"type": "plus_center_marker",
                "fg": fg_color, "marker": marker, "confidence": 1.0}

    @staticmethod
    def _draw_plus_center_markers(raw, fg, marker):
        h = len(raw)
        w = len(raw[0]) if raw else 0
        out = [row[:] for row in raw]
        for r in range(h):
            for c in range(w):
                if raw[r][c] == fg:
                    continue
                if r - 3 < 0 or r + 3 >= h or c - 3 < 0 or c + 3 >= w:
                    continue
                if (raw[r - 3][c] == fg and raw[r - 2][c] == fg and
                        raw[r + 2][c] == fg and raw[r + 3][c] == fg and
                        raw[r][c - 3] == fg and raw[r][c - 2] == fg and
                        raw[r][c + 2] == fg and raw[r][c + 3] == fg):
                    out[r][c] = marker
        return out

    # ---- strategy: rotational 4-fold kaleidoscope -----------------------

    def _try_rotational_4fold(self, example_pairs):
        """
        Detect: output is 4H x 4W with the input projected as four rotated
        copies, each tiled 2x2 in its own quadrant of tile-cells. Layout:
          TL (rows 0..2H, cols 0..2W) = rot180(input) tiled 2x2
          TR (rows 0..2H, cols 2W..4W) = rot90CW(input) tiled 2x2
          BL (rows 2H..4H, cols 0..2W) = rot90CCW(input) tiled 2x2
          BR (rows 2H..4H, cols 2W..4W) = input tiled 2x2
        """
        if not example_pairs:
            return None
        for raw_in, raw_out in example_pairs:
            h = len(raw_in)
            w = len(raw_in[0]) if raw_in else 0
            if h == 0 or w == 0 or h != w:
                return None
            oh = len(raw_out)
            ow = len(raw_out[0]) if raw_out else 0
            if oh != 4 * h or ow != 4 * w:
                return None
            expected = self._build_rotational_4fold(raw_in)
            if expected is None:
                return None
            for r in range(oh):
                for c in range(ow):
                    if expected[r][c] != raw_out[r][c]:
                        return None
        return {"type": "rotational_4fold", "confidence": 1.0}

    @staticmethod
    def _build_rotational_4fold(raw):
        h = len(raw)
        w = len(raw[0]) if raw else 0
        # Rotations
        rot_cw = [[raw[h - 1 - c][r] for c in range(h)] for r in range(w)]
        rot_ccw = [[raw[c][w - 1 - r] for c in range(h)] for r in range(w)]
        rot_180 = [[raw[h - 1 - r][w - 1 - c] for c in range(w)]
                   for r in range(h)]
        # Each rotated copy preserves shape (h, w) for square; for non-
        # square inputs rot_cw/rot_ccw have shape (w, h). To keep tiling
        # uniform, only support square inputs here.
        if h != w:
            return None
        out = [[0] * (4 * w) for _ in range(4 * h)]
        # Tile each rotated copy 2x2 into its quadrant
        copies = {
            (0, 0): rot_180,            # TL
            (0, 1): rot_cw,             # TR
            (1, 0): rot_ccw,            # BL
            (1, 1): [row[:] for row in raw],  # BR
        }
        for (qr, qc), g in copies.items():
            for tr in range(2):
                for tc in range(2):
                    base_r = qr * 2 * h + tr * h
                    base_c = qc * 2 * w + tc * w
                    for r in range(h):
                        for c in range(w):
                            out[base_r + r][base_c + c] = g[r][c]
        return out

    # ---- strategy: cross zone fill --------------------------------------

    def _try_cross_zone_fill(self, example_pairs):
        """
        Detect: input has a single full-length 'main' line (one row or one
        column) of a single 'main' color M plus several full-length
        cross-lines perpendicular to it. Cross-lines and the main line
        intersect at a single 'intersection' color X. Background fills the
        rest with one color B. Each cross-line has its own color C_i (along
        all cells except the intersection where it's X).

        Output: in each cross-line row (or col), the cross-color cells are
        replaced by X and the intersection cell becomes M (M and X swap at
        crosses). Each background row (or col) gets filled with the color
        of its NEAREST cross-line; ties between equally-distant cross-lines
        of different colors -> the entire row (or col) becomes X (including
        the main-line cell). The main-line cell of each background row (col)
        is X (was M).
        """
        if not example_pairs:
            return None

        # Try main-line as column then as row
        for orient in ("col", "row"):
            params = self._check_cross_zone_fill(example_pairs, orient)
            if params is not None:
                return {
                    "type": "cross_zone_fill",
                    "orientation": orient,
                    "main_color": params["main_color"],
                    "intersect_color": params["intersect_color"],
                    "background": params["background"],
                    "confidence": 1.0,
                }
        return None

    @staticmethod
    def _check_cross_zone_fill(example_pairs, orient):
        main_c = inter_c = bg_c = None
        for raw_in, raw_out in example_pairs:
            h = len(raw_in)
            w = len(raw_in[0]) if raw_in else 0
            if h == 0 or w == 0:
                return None
            if h != len(raw_out) or w != (len(raw_out[0]) if raw_out else 0):
                return None
            parsed = GeneralizeOperator._parse_cross_zone(raw_in, orient)
            if parsed is None:
                return None
            built = GeneralizeOperator._build_cross_zone(raw_in, orient,
                                                        parsed)
            if built is None:
                return None
            for r in range(h):
                for c in range(w):
                    if built[r][c] != raw_out[r][c]:
                        return None
            if main_c is None:
                main_c = parsed["main_color"]
                inter_c = parsed["intersect_color"]
                bg_c = parsed["background"]
            else:
                if (main_c != parsed["main_color"]
                        or inter_c != parsed["intersect_color"]
                        or bg_c != parsed["background"]):
                    return None
        if main_c is None:
            return None
        return {"main_color": main_c, "intersect_color": inter_c,
                "background": bg_c}

    @staticmethod
    def _parse_cross_zone(raw, orient):
        """Identify main line, intersect color, background, cross-lines."""
        h = len(raw)
        w = len(raw[0]) if raw else 0
        if h == 0 or w == 0:
            return None

        counts = {}
        for row in raw:
            for v in row:
                counts[v] = counts.get(v, 0) + 1
        bg = max(counts, key=counts.get)

        # Find the main line: a column (or row) whose cells are exactly two
        # values - main_color and intersect_color
        main_idx = None
        main_color = None
        intersect_color = None
        if orient == "col":
            for c in range(w):
                vals = [raw[r][c] for r in range(h)]
                vset = set(vals)
                if len(vset) != 2:
                    continue
                # the more frequent is the main color
                a, b = list(vset)
                ca = vals.count(a)
                cb = vals.count(b)
                if ca > cb:
                    mc, ic = a, b
                else:
                    mc, ic = b, a
                if main_idx is not None:
                    return None  # more than one candidate
                main_idx = c
                main_color = mc
                intersect_color = ic
        else:
            for r in range(h):
                vals = list(raw[r])
                vset = set(vals)
                if len(vset) != 2:
                    continue
                a, b = list(vset)
                ca = vals.count(a)
                cb = vals.count(b)
                if ca > cb:
                    mc, ic = a, b
                else:
                    mc, ic = b, a
                if main_idx is not None:
                    return None
                main_idx = r
                main_color = mc
                intersect_color = ic

        if main_idx is None:
            return None
        if main_color == bg or intersect_color == bg:
            return None

        # Find cross-line indices: rows (or cols) where main-line cell is the
        # intersect color (not main color).
        cross = {}
        if orient == "col":
            for r in range(h):
                if raw[r][main_idx] == intersect_color:
                    line_vals = [raw[r][c] for c in range(w) if c != main_idx]
                    line_set = set(line_vals)
                    if len(line_set) != 1:
                        return None
                    color = next(iter(line_set))
                    if color == bg or color == intersect_color:
                        return None
                    cross[r] = color
        else:
            for c in range(w):
                if raw[main_idx][c] == intersect_color:
                    line_vals = [raw[r][c] for r in range(h) if r != main_idx]
                    line_set = set(line_vals)
                    if len(line_set) != 1:
                        return None
                    color = next(iter(line_set))
                    if color == bg or color == intersect_color:
                        return None
                    cross[c] = color

        if not cross:
            return None

        # Background cells should equal bg
        if orient == "col":
            for r in range(h):
                if r in cross:
                    continue
                for c in range(w):
                    if c == main_idx:
                        if raw[r][c] != main_color:
                            return None
                    else:
                        if raw[r][c] != bg:
                            return None
        else:
            for c in range(w):
                if c in cross:
                    continue
                for r in range(h):
                    if r == main_idx:
                        if raw[r][c] != main_color:
                            return None
                    else:
                        if raw[r][c] != bg:
                            return None

        return {
            "main_idx": main_idx,
            "main_color": main_color,
            "intersect_color": intersect_color,
            "background": bg,
            "cross": cross,
        }

    @staticmethod
    def _build_cross_zone(raw, orient, parsed):
        h = len(raw)
        w = len(raw[0]) if raw else 0
        main_idx = parsed["main_idx"]
        mc = parsed["main_color"]
        ic = parsed["intersect_color"]
        cross = parsed["cross"]
        out = [[0] * w for _ in range(h)]
        cross_keys = sorted(cross.keys())
        if orient == "col":
            for r in range(h):
                if r in cross:
                    for c in range(w):
                        out[r][c] = mc if c == main_idx else ic
                    continue
                # find nearest cross-line(s)
                best_d = min(abs(r - k) for k in cross_keys)
                nearest = [k for k in cross_keys if abs(r - k) == best_d]
                colors = {cross[k] for k in nearest}
                if len(colors) == 1:
                    fill = next(iter(colors))
                    for c in range(w):
                        out[r][c] = ic if c == main_idx else fill
                else:
                    for c in range(w):
                        out[r][c] = ic
        else:
            for c in range(w):
                if c in cross:
                    for r in range(h):
                        out[r][c] = mc if r == main_idx else ic
                    continue
                best_d = min(abs(c - k) for k in cross_keys)
                nearest = [k for k in cross_keys if abs(c - k) == best_d]
                colors = {cross[k] for k in nearest}
                if len(colors) == 1:
                    fill = next(iter(colors))
                    for r in range(h):
                        out[r][c] = ic if r == main_idx else fill
                else:
                    for r in range(h):
                        out[r][c] = ic
        return out

    # ---- strategy: plus majority color ----------------------------------

    def _try_plus_majority_color(self, example_pairs):
        """
        Detect: output is a 1x1 grid. Input contains some 'marker' cells of
        a constant color M; each marker has its 4 cardinal neighbors all
        in-bounds and of one common color V_i. The output cell equals the
        most common V across all such markers in the input. The marker
        color and the rule are consistent across all examples.
        """
        if not example_pairs:
            return None

        # Output must be 1x1 in every example
        for _, raw_out in example_pairs:
            if len(raw_out) != 1 or not raw_out[0] or len(raw_out[0]) != 1:
                return None

        # Try each candidate marker color (intersect of input colors).
        all_colors = None
        for raw_in, _ in example_pairs:
            colors = {v for row in raw_in for v in row}
            all_colors = colors if all_colors is None else (all_colors
                                                            & colors)
        if not all_colors:
            return None

        for marker in sorted(all_colors):
            ok = True
            for raw_in, raw_out in example_pairs:
                target = raw_out[0][0]
                computed = GeneralizeOperator._plus_majority(raw_in, marker)
                if computed is None or computed != target:
                    ok = False
                    break
            if ok:
                return {
                    "type": "plus_majority_color",
                    "marker": marker,
                    "confidence": 1.0,
                }
        return None

    @staticmethod
    def _plus_majority(raw, marker):
        h = len(raw)
        w = len(raw[0]) if raw else 0
        counts = {}
        for r in range(h):
            for c in range(w):
                if raw[r][c] != marker:
                    continue
                if r - 1 < 0 or r + 1 >= h or c - 1 < 0 or c + 1 >= w:
                    continue
                u = raw[r - 1][c]
                d = raw[r + 1][c]
                l = raw[r][c - 1]
                rt = raw[r][c + 1]
                if u == d == l == rt and u != marker:
                    counts[u] = counts.get(u, 0) + 1
        if not counts:
            return None
        # Pick max count; on tie, smallest color value
        best_n = max(counts.values())
        candidates = [k for k, v in counts.items() if v == best_n]
        return min(candidates)

    # ---- strategy: framed recolor legend ---------------------------------

    def _try_framed_recolor_legend(self, example_pairs):
        """
        Detect: input has bg + a 'main' connected non-bg region (largest
        component, multiple colors) plus one or more 2-cell 'legend' pair
        components. Each pair has two distinct colors, exactly one of which
        appears inside the main region. The output is the bbox of the main
        region with each interior color X (that has a legend pair {X, Y})
        recoloured to its partner Y.

        Cell sizes outside the main and pairs are ignored (no other non-bg
        components allowed). The main region's "frame" colour (most common
        within the main) and any other non-mapped colours pass through
        unchanged. The mapping is re-derived per test input from its own
        legend pairs, so no per-task parameters need to be learned.
        """
        if not example_pairs:
            return None

        for raw_in, raw_out in example_pairs:
            result = GeneralizeOperator._apply_framed_recolor_legend(raw_in)
            if result is None:
                return None
            if len(result) != len(raw_out):
                return None
            for ra, rb in zip(result, raw_out):
                if len(ra) != len(rb):
                    return None
                for a, b in zip(ra, rb):
                    if a != b:
                        return None

        return {
            "type": "framed_recolor_legend",
            "confidence": 1.0,
        }

    @staticmethod
    def _apply_framed_recolor_legend(raw):
        """
        Apply the framed-recolor-legend transformation to a single grid.
        Returns the recolored bbox of the main region, or None if the
        structure does not match.
        """
        h = len(raw)
        w = len(raw[0]) if raw else 0
        if h == 0 or w == 0:
            return None

        counts = {}
        for row in raw:
            for v in row:
                counts[v] = counts.get(v, 0) + 1
        if len(counts) < 4:
            return None
        bg = max(counts, key=counts.get)

        # Connected components on non-bg cells (4-connected, color-agnostic).
        visited = [[False] * w for _ in range(h)]
        comps = []
        for r in range(h):
            for c in range(w):
                if visited[r][c] or raw[r][c] == bg:
                    continue
                stack = [(r, c)]
                cells = []
                while stack:
                    rr, cc = stack.pop()
                    if (rr < 0 or rr >= h or cc < 0 or cc >= w
                            or visited[rr][cc] or raw[rr][cc] == bg):
                        continue
                    visited[rr][cc] = True
                    cells.append((rr, cc))
                    stack.extend([(rr - 1, cc), (rr + 1, cc),
                                  (rr, cc - 1), (rr, cc + 1)])
                comps.append(cells)

        if len(comps) < 2:
            return None

        # Main = component with highest cell count and >=2 distinct colors.
        comps_sorted = sorted(comps, key=lambda c: -len(c))
        main = None
        for cells in comps_sorted:
            colors = {raw[r][c] for r, c in cells}
            if len(colors) >= 2:
                main = cells
                break
        if main is None:
            return None

        main_set = set(main)
        # Build legend pairs from remaining components: must be exactly 2
        # cells with 2 distinct colors.
        pairs = []
        for cells in comps:
            if cells is main:
                continue
            if len(cells) != 2:
                return None
            v1 = raw[cells[0][0]][cells[0][1]]
            v2 = raw[cells[1][0]][cells[1][1]]
            if v1 == v2:
                return None
            pairs.append((cells, v1, v2))
        if not pairs:
            return None

        # Frame color = most common color in the main region.
        main_color_counts = {}
        for r, c in main:
            v = raw[r][c]
            main_color_counts[v] = main_color_counts.get(v, 0) + 1
        frame_color = max(main_color_counts, key=main_color_counts.get)
        inner_colors = set(main_color_counts) - {frame_color}
        if not inner_colors:
            return None

        # Build color map from legend pairs.
        color_map = {}
        for _, v1, v2 in pairs:
            in1 = v1 in inner_colors
            in2 = v2 in inner_colors
            if in1 == in2:
                # Both or neither in inner → ambiguous.
                return None
            if in1:
                source, target = v1, v2
            else:
                source, target = v2, v1
            if source in color_map and color_map[source] != target:
                return None
            color_map[source] = target

        # Bounding box of main region.
        rs = [r for r, _ in main]
        cs = [c for _, c in main]
        r0, r1 = min(rs), max(rs)
        c0, c1 = min(cs), max(cs)

        out = []
        for r in range(r0, r1 + 1):
            row = []
            for c in range(c0, c1 + 1):
                v = raw[r][c]
                row.append(color_map.get(v, v))
            out.append(row)
        return out

    # ---- strategy: ricochet ray -----------------------------------------

    def _try_ricochet_ray(self, example_pairs):
        """
        Detect: same grid size; one cell is a single 'shooter' marker on a
        grid edge. Other non-bg cells are isolated 'marker' cells. Output
        equals input plus a polyline of shooter-color cells starting at the
        shooter, traveling perpendicular to its grid edge, ricocheting 90°
        off each marker (each marker color has a fixed turn direction:
        clockwise or counter-clockwise). Trail stops at the grid edge.
        """
        from itertools import product

        if not example_pairs:
            return None

        shooter_color = None
        marker_turn_constraints = {}

        for raw_in, raw_out in example_pairs:
            if not raw_in or not raw_out:
                return None
            h = len(raw_in)
            w = len(raw_in[0])
            if len(raw_out) != h or len(raw_out[0]) != w:
                return None

            counts = {}
            for row in raw_in:
                for c in row:
                    counts[c] = counts.get(c, 0) + 1
            bg = max(counts, key=counts.get)

            non_bg = [(r, c) for r in range(h) for c in range(w)
                      if raw_in[r][c] != bg]
            if len(non_bg) < 2:
                return None
            for r, c in non_bg:
                for dr, dc in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                    nr, nc = r + dr, c + dc
                    if (0 <= nr < h and 0 <= nc < w
                            and raw_in[nr][nc] != bg):
                        return None

            in_counts = {}
            out_counts = {}
            for row in raw_in:
                for c in row:
                    in_counts[c] = in_counts.get(c, 0) + 1
            for row in raw_out:
                for c in row:
                    out_counts[c] = out_counts.get(c, 0) + 1

            increased = [c for c in in_counts
                         if c != bg
                         and out_counts.get(c, 0) > in_counts.get(c, 0)]
            if len(increased) != 1:
                return None
            shooter = increased[0]

            shooter_cells = [(r, c) for r in range(h) for c in range(w)
                             if raw_in[r][c] == shooter]
            if len(shooter_cells) != 1:
                return None

            # Markers and bg→shooter rule for output
            for r in range(h):
                for c in range(w):
                    iv = raw_in[r][c]
                    ov = raw_out[r][c]
                    if iv == bg:
                        if ov not in (bg, shooter):
                            return None
                    elif iv == shooter:
                        if ov != shooter:
                            return None
                    else:
                        if ov != iv:
                            return None

            if shooter_color is None:
                shooter_color = shooter
            elif shooter_color != shooter:
                return None

            sr, sc = shooter_cells[0]
            init_dirs = []
            if sc == 0:
                init_dirs.append((0, 1))
            if sc == w - 1:
                init_dirs.append((0, -1))
            if sr == 0:
                init_dirs.append((1, 0))
            if sr == h - 1:
                init_dirs.append((-1, 0))
            if not init_dirs:
                return None

            marker_colors = sorted({raw_in[r][c] for r, c in non_bg
                                    if raw_in[r][c] != shooter})

            found = None
            for init_dir in init_dirs:
                for combo in product(["cw", "ccw"], repeat=len(marker_colors)):
                    turn_map = dict(zip(marker_colors, combo))
                    # Combine with already-known constraints
                    consistent = True
                    for k, v in turn_map.items():
                        if k in marker_turn_constraints \
                                and marker_turn_constraints[k] != v:
                            consistent = False
                            break
                    if not consistent:
                        continue
                    trail = self._trace_ricochet_ray(
                        raw_in, sr, sc, init_dir, shooter, bg, turn_map)
                    if trail is None:
                        continue
                    expected = [row[:] for row in raw_in]
                    for tr, tc in trail:
                        expected[tr][tc] = shooter
                    if expected == raw_out:
                        found = (init_dir, turn_map)
                        break
                if found is not None:
                    break

            if found is None:
                return None

            for k, v in found[1].items():
                marker_turn_constraints[k] = v

        if shooter_color is None:
            return None

        return {
            "type": "ricochet_ray",
            "shooter_color": shooter_color,
            "marker_turns": marker_turn_constraints,
            "confidence": 1.0,
        }

    @staticmethod
    def _trace_ricochet_ray(raw, sr, sc, init_dir, shooter, bg, turn_map):
        """Trace ray from (sr, sc) with starting direction init_dir.
        Ricochets 90° at each marker per turn_map. Returns list of trail
        cells (excluding shooter), or None if invalid (loop / unknown
        marker / bad path).
        """
        h = len(raw)
        w = len(raw[0]) if raw else 0

        def turn(d, way):
            dr, dc = d
            if way == "cw":
                return (dc, -dr)
            return (-dc, dr)

        trail = []
        r, c = sr, sc
        direction = init_dir
        seen_states = set()
        max_steps = h * w * 4 + 4

        for _ in range(max_steps):
            nr, nc = r + direction[0], c + direction[1]
            if not (0 <= nr < h and 0 <= nc < w):
                return trail
            v = raw[nr][nc]
            if v == bg:
                trail.append((nr, nc))
                r, c = nr, nc
                continue
            if v == shooter:
                return None
            if v not in turn_map:
                return None
            new_dir = turn(direction, turn_map[v])
            state = (r, c, new_dir)
            if state in seen_states:
                return None
            seen_states.add(state)
            direction = new_dir

        return None

    @staticmethod
    def _group_4connected(positions):
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

    # ---- strategy: mirror shoot anchor ----------------------------------

    def _try_mirror_shoot_anchor(self, example_pairs):
        """
        Detect: a full-row or full-column divider line of color D splits the
        grid into two regions. One region (the 'object' region) contains
        connected components built from exactly two foreground colors:
        anchor color A (one or more cells per component) and pointer color
        P (one or more cells per component). The other region (the 'marker'
        region) contains scattered cells of a third color M, each placed at
        the mirror (across the divider) of an A cell in the object region.

        Output: the divider stays. In the object region, each A cell moves
        to the farthest connected P cell along its trail (BFS through P
        cells); the original A and trail P cells become background. In the
        marker region, each M cell is placed at the mirror of the new A
        position; original M cells become background.
        """
        if not example_pairs:
            return None

        anchor_color = None
        pointer_color = None
        marker_color = None
        divider_color = None
        divider_axis = None  # 'row' or 'col'
        marker_side = None   # which side has markers: 'before' or 'after'

        for raw_in, raw_out in example_pairs:
            if not raw_in or not raw_out:
                return None
            h = len(raw_in)
            w = len(raw_in[0])
            if len(raw_out) != h or len(raw_out[0]) != w:
                return None

            counts = {}
            for row in raw_in:
                for c in row:
                    counts[c] = counts.get(c, 0) + 1
            bg = max(counts, key=counts.get)

            # Find divider: a full row or column of single non-bg color.
            div_row = None
            div_col = None
            div_color = None
            for r in range(h):
                vals = set(raw_in[r])
                if len(vals) == 1:
                    v = next(iter(vals))
                    if v != bg:
                        if div_row is not None:
                            # Multiple full rows; pick by uniqueness later
                            return None
                        div_row = r
                        div_color = v
            for c in range(w):
                vals = {raw_in[r][c] for r in range(h)}
                if len(vals) == 1:
                    v = next(iter(vals))
                    if v != bg:
                        if div_col is not None:
                            return None
                        # Prefer earlier-found row; only set if no row found
                        if div_row is None:
                            div_col = c
                            div_color = v
                        else:
                            return None
            if div_row is None and div_col is None:
                return None
            axis = "row" if div_row is not None else "col"

            # Identify foreground colors (excluding bg and divider).
            fg_colors = set()
            for r in range(h):
                for c in range(w):
                    v = raw_in[r][c]
                    if v != bg and v != div_color:
                        fg_colors.add(v)
            if len(fg_colors) != 3:
                return None

            # Determine which color is the marker (single-cell scattered
            # in one half) vs anchor/pointer (in the other half).
            def in_side_a(r, c):
                if axis == "row":
                    return r < div_row
                return c < div_col

            def in_side_b(r, c):
                if axis == "row":
                    return r > div_row
                return c > div_col

            colors_in_a = set()
            colors_in_b = set()
            for r in range(h):
                for c in range(w):
                    v = raw_in[r][c]
                    if v == bg or v == div_color:
                        continue
                    if in_side_a(r, c):
                        colors_in_a.add(v)
                    elif in_side_b(r, c):
                        colors_in_b.add(v)
                    else:
                        # On divider line — would only be div_color
                        return None

            if len(colors_in_a) == 1 and len(colors_in_b) == 2:
                m_color = next(iter(colors_in_a))
                obj_colors = colors_in_b
                m_side = "a"
            elif len(colors_in_b) == 1 and len(colors_in_a) == 2:
                m_color = next(iter(colors_in_b))
                obj_colors = colors_in_a
                m_side = "b"
            else:
                return None

            # Find connected components of object colors. Each must
            # contain at least one anchor cell and at least one pointer
            # cell. Need to figure out anchor vs pointer: the anchor is
            # the color whose cell positions in the input match the
            # mirror of marker cells in the marker region.

            obj_positions = []
            for r in range(h):
                for c in range(w):
                    if raw_in[r][c] in obj_colors:
                        obj_positions.append((r, c))

            comps = self._group_4connected(obj_positions)
            if not comps:
                return None

            marker_positions = sorted(
                (r, c) for r in range(h) for c in range(w)
                if raw_in[r][c] == m_color)

            def mirror(r, c):
                if axis == "row":
                    return (2 * div_row - r, c)
                return (r, 2 * div_col - c)

            # Try both candidates as the anchor color.
            obj_list = sorted(obj_colors)
            chosen_anchor = None
            for a_cand in obj_list:
                p_cand = (obj_list[0] if obj_list[1] == a_cand
                          else obj_list[1])
                # Check: input markers = mirror(input anchors)
                anchor_cells = sorted(
                    (r, c) for (r, c) in obj_positions
                    if raw_in[r][c] == a_cand)
                mirrored = sorted(mirror(r, c) for r, c in anchor_cells)
                if mirrored == marker_positions:
                    chosen_anchor = (a_cand, p_cand)
                    break

            if chosen_anchor is None:
                return None
            a_color, p_color = chosen_anchor

            # Compute output: for each anchor cell, BFS through pointers
            # to find the farthest reachable pointer cell. That's the
            # destination.
            new_anchors = []
            comp_lookup = {}
            for comp in comps:
                for cell in comp:
                    comp_lookup[cell] = comp

            for (ar, ac) in [(r, c) for (r, c) in obj_positions
                             if raw_in[r][c] == a_color]:
                comp = comp_lookup[(ar, ac)]
                comp_set = set(comp)
                # BFS through pointer cells starting from anchor;
                # the pointer cell with the max BFS distance is the
                # destination.
                visited = {(ar, ac): 0}
                queue = [(ar, ac)]
                farthest = (ar, ac)
                farthest_d = 0
                while queue:
                    r, c = queue.pop(0)
                    d = visited[(r, c)]
                    for dr, dc in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                        nb = (r + dr, c + dc)
                        if nb not in comp_set or nb in visited:
                            continue
                        if raw_in[nb[0]][nb[1]] != p_color:
                            continue
                        visited[nb] = d + 1
                        queue.append(nb)
                        if d + 1 > farthest_d:
                            farthest_d = d + 1
                            farthest = nb
                if farthest_d == 0:
                    # Anchor with no pointer trail — invalid
                    return None
                new_anchors.append(farthest)

            # Build expected output and compare
            expected = [row[:] for row in raw_in]
            # Erase all anchors, pointers, and markers
            for r in range(h):
                for c in range(w):
                    v = raw_in[r][c]
                    if v in (a_color, p_color, m_color):
                        expected[r][c] = bg
            # Place new anchors and mirrored markers
            for (nr, nc) in new_anchors:
                expected[nr][nc] = a_color
                mr, mc = mirror(nr, nc)
                if 0 <= mr < h and 0 <= mc < w:
                    expected[mr][mc] = m_color

            if expected != raw_out:
                return None

            # Lock in colors / divider across examples
            if anchor_color is None:
                anchor_color = a_color
                pointer_color = p_color
                marker_color = m_color
                divider_color = div_color
                divider_axis = axis
                marker_side = m_side
            else:
                if (anchor_color != a_color or pointer_color != p_color
                        or marker_color != m_color
                        or divider_color != div_color
                        or divider_axis != axis
                        or marker_side != m_side):
                    return None

        if anchor_color is None:
            return None
        return {
            "type": "mirror_shoot_anchor",
            "anchor_color": anchor_color,
            "pointer_color": pointer_color,
            "marker_color": marker_color,
            "divider_color": divider_color,
            "divider_axis": divider_axis,
            "marker_side": marker_side,
            "confidence": 1.0,
        }

    @staticmethod
    def _draw_corner_l_shoot(raw, bg):
        h = len(raw)
        w = len(raw[0]) if raw else 0
        out = [row[:] for row in raw]
        for r in range(h):
            for c in range(w):
                v = raw[r][c]
                if v == bg:
                    continue
                dists = (
                    r + c,                      # TL
                    r + (w - 1 - c),            # TR
                    (h - 1 - r) + c,            # BL
                    (h - 1 - r) + (w - 1 - c),  # BR
                )
                best = min(range(4), key=lambda i: dists[i])
                cr = 0 if best in (0, 1) else h - 1
                cc = 0 if best in (0, 2) else w - 1
                r0, r1 = (cr, r) if cr <= r else (r, cr)
                c0, c1 = (cc, c) if cc <= c else (c, cc)
                for rr in range(r0, r1 + 1):
                    out[rr][c] = v
                for cc2 in range(c0, c1 + 1):
                    out[r][cc2] = v
        return out

    @staticmethod
    def _draw_corner_diagonal_blocks(grid, r0, c0, tl, tr, bl, br):
        h = len(grid)
        w = len(grid[0]) if grid else 0
        # (block_top_left_offset_from_source_TL, fill_color)
        specs = [
            ((-2, -2), br),  # TL direction → opposite corner color
            ((-2, +2), bl),  # TR direction
            ((+2, -2), tr),  # BL direction
            ((+2, +2), tl),  # BR direction
        ]
        for (dr, dc), color in specs:
            br0 = r0 + dr
            bc0 = c0 + dc
            for rr in range(br0, br0 + 2):
                for cc in range(bc0, bc0 + 2):
                    if 0 <= rr < h and 0 <= cc < w:
                        grid[rr][cc] = color

    @staticmethod
    def _find_components(raw, color):
        """Return 4-connected components of `color` in `raw` as lists of (r, c)."""
        h = len(raw)
        w = len(raw[0]) if raw else 0
        visited = [[False] * w for _ in range(h)]
        comps = []
        for r in range(h):
            for c in range(w):
                if raw[r][c] != color or visited[r][c]:
                    continue
                comp = []
                queue = [(r, c)]
                while queue:
                    rr, cc = queue.pop()
                    if rr < 0 or rr >= h or cc < 0 or cc >= w:
                        continue
                    if visited[rr][cc] or raw[rr][cc] != color:
                        continue
                    visited[rr][cc] = True
                    comp.append((rr, cc))
                    for dr, dc in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                        queue.append((rr + dr, cc + dc))
                comps.append(comp)
        return comps


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
        if rule_type == "corner_quadrant_fill":
            return self._apply_corner_quadrant_fill(rule, input_grid)
        if rule_type == "diamond_connector":
            return self._apply_diamond_connector(rule, input_grid)
        if rule_type == "axis_line_keep":
            return self._apply_axis_line_keep(rule, input_grid)
        if rule_type == "recolor_by_size":
            return self._apply_recolor_by_size(rule, input_grid)
        if rule_type == "rect_interior_marker_fill":
            return self._apply_rect_interior_marker_fill(rule, input_grid)
        if rule_type == "object_extract_swap":
            return self._apply_object_extract_swap(rule, input_grid)
        if rule_type == "keep_solid_rectangles":
            return self._apply_keep_solid_rectangles(rule, input_grid)
        if rule_type == "tile_pattern_vertical":
            return self._apply_tile_pattern_vertical(rule, input_grid)
        if rule_type == "diagonal_tail_extend":
            return self._apply_diagonal_tail_extend(rule, input_grid)
        if rule_type == "corner_diagonal_2x2":
            return self._apply_corner_diagonal_2x2(rule, input_grid)
        if rule_type == "rotational_quadrants_2x":
            return self._apply_rotational_quadrants_2x(rule, input_grid)
        if rule_type == "inside_marker_count_3x3":
            return self._apply_inside_marker_count_3x3(rule, input_grid)
        if rule_type == "corner_l_shoot":
            return self._apply_corner_l_shoot(rule, input_grid)
        if rule_type == "concentric_ring_reverse":
            return self._apply_concentric_ring_reverse(rule, input_grid)
        if rule_type == "square_corner_marker":
            return self._apply_square_corner_marker(rule, input_grid)
        if rule_type == "plus_center_marker":
            return self._apply_plus_center_marker(rule, input_grid)
        if rule_type == "rotational_4fold":
            return self._apply_rotational_4fold(rule, input_grid)
        if rule_type == "cross_zone_fill":
            return self._apply_cross_zone_fill(rule, input_grid)
        if rule_type == "plus_majority_color":
            return self._apply_plus_majority_color(rule, input_grid)
        if rule_type == "ricochet_ray":
            return self._apply_ricochet_ray(rule, input_grid)
        if rule_type == "mirror_shoot_anchor":
            return self._apply_mirror_shoot_anchor(rule, input_grid)
        if rule_type == "framed_recolor_legend":
            return self._apply_framed_recolor_legend(rule, input_grid)
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

    def _apply_corner_quadrant_fill(self, rule, input_grid):
        raw = input_grid.raw
        inner_color = rule.get("inner_color")
        if inner_color is None:
            return None

        counts = {}
        for row in raw:
            for c in row:
                counts[c] = counts.get(c, 0) + 1
        bg = max(counts, key=counts.get)

        groups = GeneralizeOperator._find_corner_quadrant_groups(raw, bg)
        groups = [g for g in groups if g["inner_color"] == inner_color]
        if not groups:
            return None
        return GeneralizeOperator._apply_quadrant_groups(raw, groups, bg)

    def _apply_axis_line_keep(self, rule, input_grid):
        raw = input_grid.raw
        h = len(raw)
        w = len(raw[0]) if raw else 0
        axis = rule.get("axis")
        pos = rule.get("position")
        bg = rule.get("background")
        if axis not in ("col", "row") or pos != "middle" or bg is None:
            return None
        k = (w // 2) if axis == "col" else (h // 2)
        out = [[bg] * w for _ in range(h)]
        for r in range(h):
            for c in range(w):
                on_line = (axis == "col" and c == k) or (axis == "row" and r == k)
                if on_line:
                    out[r][c] = raw[r][c]
        return out

    def _apply_recolor_by_size(self, rule, input_grid):
        raw = input_grid.raw
        h = len(raw)
        w = len(raw[0]) if raw else 0
        fg = rule.get("foreground")
        if fg is None:
            return None
        size_to_color_raw = rule.get("size_to_color") or {}
        size_to_color = {}
        for k, v in size_to_color_raw.items():
            try:
                size_to_color[int(k)] = v
            except (TypeError, ValueError):
                continue
        out = [row[:] for row in raw]
        for comp in GeneralizeOperator._find_components(raw, fg):
            new_color = size_to_color.get(len(comp))
            if new_color is None:
                continue
            for (rr, cc) in comp:
                out[rr][cc] = new_color
        return out

    def _apply_rect_interior_marker_fill(self, rule, input_grid):
        raw = input_grid.raw
        h = len(raw)
        w = len(raw[0]) if raw else 0
        marker = rule.get("marker")
        fg = rule.get("foreground")
        bg = rule.get("background")
        if marker is None or fg is None or bg is None:
            return None
        rects = GeneralizeOperator._find_rect_borders(raw, fg, min_h=3, min_w=3)
        out = [row[:] for row in raw]
        for (r0, c0, r1, c1) in rects:
            for r in range(r0 + 1, r1):
                for c in range(c0 + 1, c1):
                    if raw[r][c] == bg:
                        out[r][c] = marker
        return out

    def _apply_object_extract_swap(self, rule, input_grid):
        raw = input_grid.raw
        h = len(raw)
        w = len(raw[0]) if raw else 0
        if h == 0 or w == 0:
            return None
        counts = {}
        for row in raw:
            for c in row:
                counts[c] = counts.get(c, 0) + 1
        bg = max(counts, key=counts.get)
        non_bg = [c for c in counts if c != bg]
        if len(non_bg) != 2:
            return None
        rows = [r for r in range(h) for c in range(w) if raw[r][c] != bg]
        cols = [c for r in range(h) for c in range(w) if raw[r][c] != bg]
        if not rows:
            return None
        r0, r1 = min(rows), max(rows)
        c0, c1 = min(cols), max(cols)
        a, b = non_bg
        out = []
        for r in range(r0, r1 + 1):
            new_row = []
            for c in range(c0, c1 + 1):
                v = raw[r][c]
                if v == a:
                    new_row.append(b)
                elif v == b:
                    new_row.append(a)
                else:
                    new_row.append(v)
            out.append(new_row)
        return out

    def _apply_keep_solid_rectangles(self, rule, input_grid):
        raw = input_grid.raw
        h = len(raw)
        w = len(raw[0]) if raw else 0
        if h == 0 or w == 0:
            return None
        counts = {}
        for row in raw:
            for c in row:
                counts[c] = counts.get(c, 0) + 1
        bg = max(counts, key=counts.get)
        fg_set = set(counts.keys()) - {bg}
        if len(fg_set) != 1:
            return None
        fg = next(iter(fg_set))
        keep = GeneralizeOperator._compute_solid_block_keep(raw, fg)
        out = [row[:] for row in raw]
        for r in range(h):
            for c in range(w):
                if raw[r][c] == fg and (r, c) not in keep:
                    out[r][c] = bg
        return out

    def _apply_tile_pattern_vertical(self, rule, input_grid):
        raw = input_grid.raw
        h = len(raw)
        w = len(raw[0]) if raw else 0
        if h == 0 or w == 0:
            return None
        counts = {}
        for row in raw:
            for c in row:
                counts[c] = counts.get(c, 0) + 1
        bg = max(counts, key=counts.get)
        first_row = None
        for r in range(h):
            if any(c != bg for c in raw[r]):
                first_row = r
                break
        if first_row is None or first_row == 0:
            return [row[:] for row in raw]
        pattern_h = h - first_row
        pattern = raw[first_row:]
        out = []
        for r in range(h):
            out.append(list(pattern[(r - first_row) % pattern_h]))
        return out

    def _apply_diagonal_tail_extend(self, rule, input_grid):
        raw = input_grid.raw
        h = len(raw)
        w = len(raw[0]) if raw else 0
        if h == 0 or w == 0:
            return None
        counts = {}
        for row in raw:
            for c in row:
                counts[c] = counts.get(c, 0) + 1
        bg = max(counts, key=counts.get)
        fg_set = set(counts.keys()) - {bg}
        if len(fg_set) != 1:
            return None
        fg = next(iter(fg_set))
        params = GeneralizeOperator._find_2x2_block_with_tails(raw, fg, bg)
        if params is None:
            return [row[:] for row in raw]
        out = [row[:] for row in raw]
        GeneralizeOperator._draw_diagonal_tails(out, params["r0"],
                                                params["c0"],
                                                params["tails"], fg)
        return out

    def _apply_corner_diagonal_2x2(self, rule, input_grid):
        raw = input_grid.raw
        h = len(raw)
        w = len(raw[0]) if raw else 0
        if h == 0 or w == 0:
            return None
        counts = {}
        for row in raw:
            for c in row:
                counts[c] = counts.get(c, 0) + 1
        bg = max(counts, key=counts.get)
        non_bg = [(r, c) for r in range(h) for c in range(w)
                  if raw[r][c] != bg]
        if len(non_bg) != 4:
            return [row[:] for row in raw]
        rows = sorted({r for r, _ in non_bg})
        cols = sorted({c for _, c in non_bg})
        if len(rows) != 2 or len(cols) != 2:
            return [row[:] for row in raw]
        if rows[1] - rows[0] != 1 or cols[1] - cols[0] != 1:
            return [row[:] for row in raw]
        r0, c0 = rows[0], cols[0]
        r1, c1 = rows[1], cols[1]
        tl, tr, bl, br = (raw[r0][c0], raw[r0][c1],
                          raw[r1][c0], raw[r1][c1])
        out = [row[:] for row in raw]
        GeneralizeOperator._draw_corner_diagonal_blocks(out, r0, c0,
                                                        tl, tr, bl, br)
        return out

    def _apply_rotational_quadrants_2x(self, rule, input_grid):
        raw = input_grid.raw
        h = len(raw)
        w = len(raw[0]) if raw else 0
        if h == 0 or w == 0 or h != w:
            return None
        return GeneralizeOperator._build_rotational_quadrants_2x(raw)

    def _apply_inside_marker_count_3x3(self, rule, input_grid):
        raw = input_grid.raw
        params = GeneralizeOperator._inside_marker_count_3x3_params(raw)
        if params is None:
            return None
        bg, marker, n = params["bg"], params["marker"], params["n"]
        n = max(0, min(9, n))
        out = [[bg] * 3 for _ in range(3)]
        for k in range(n):
            out[k // 3][k % 3] = marker
        return out

    def _apply_corner_l_shoot(self, rule, input_grid):
        raw = input_grid.raw
        h = len(raw)
        w = len(raw[0]) if raw else 0
        if h == 0 or w == 0:
            return None
        counts = {}
        for row in raw:
            for c in row:
                counts[c] = counts.get(c, 0) + 1
        bg = max(counts, key=counts.get)
        return GeneralizeOperator._draw_corner_l_shoot(raw, bg)

    def _apply_concentric_ring_reverse(self, rule, input_grid):
        raw = input_grid.raw
        h = len(raw)
        w = len(raw[0]) if raw else 0
        if h < 2 or w < 2:
            return None
        layers = GeneralizeOperator._concentric_layers(raw)
        if layers is None:
            return None
        rev = list(reversed(layers))
        out = [[0] * w for _ in range(h)]
        for r in range(h):
            for c in range(w):
                k = min(r, h - 1 - r, c, w - 1 - c)
                out[r][c] = rev[k]
        return out

    def _apply_square_corner_marker(self, rule, input_grid):
        raw = input_grid.raw
        marker = rule.get("marker")
        if marker is None:
            return None
        targets = GeneralizeOperator._square_marker_targets(raw)
        return GeneralizeOperator._draw_square_corner_markers(raw, targets,
                                                              marker)

    def _apply_plus_center_marker(self, rule, input_grid):
        raw = input_grid.raw
        fg = rule.get("fg")
        marker = rule.get("marker")
        if fg is None or marker is None:
            return None
        return GeneralizeOperator._draw_plus_center_markers(raw, fg, marker)

    def _apply_rotational_4fold(self, rule, input_grid):
        raw = input_grid.raw
        return GeneralizeOperator._build_rotational_4fold(raw)

    def _apply_cross_zone_fill(self, rule, input_grid):
        raw = input_grid.raw
        orient = rule.get("orientation")
        if orient not in ("col", "row"):
            return None
        parsed = GeneralizeOperator._parse_cross_zone(raw, orient)
        if parsed is None:
            return None
        if (parsed["main_color"] != rule.get("main_color")
                or parsed["intersect_color"] != rule.get("intersect_color")
                or parsed["background"] != rule.get("background")):
            return None
        return GeneralizeOperator._build_cross_zone(raw, orient, parsed)

    def _apply_ricochet_ray(self, rule, input_grid):
        raw = input_grid.raw
        h = len(raw)
        w = len(raw[0]) if raw else 0
        if h == 0 or w == 0:
            return None
        shooter = rule.get("shooter_color")
        turn_map = rule.get("marker_turns") or {}
        if shooter is None:
            return None

        counts = {}
        for row in raw:
            for c in row:
                counts[c] = counts.get(c, 0) + 1
        bg = max(counts, key=counts.get)

        shooter_cells = [(r, c) for r in range(h) for c in range(w)
                         if raw[r][c] == shooter]
        if len(shooter_cells) != 1:
            return None
        sr, sc = shooter_cells[0]

        init_dirs = []
        if sc == 0:
            init_dirs.append((0, 1))
        if sc == w - 1:
            init_dirs.append((0, -1))
        if sr == 0:
            init_dirs.append((1, 0))
        if sr == h - 1:
            init_dirs.append((-1, 0))
        if not init_dirs:
            return None

        # JSON loads dict keys as strings; coerce to int
        norm_turn_map = {}
        for k, v in turn_map.items():
            try:
                norm_turn_map[int(k)] = v
            except (TypeError, ValueError):
                norm_turn_map[k] = v

        for init_dir in init_dirs:
            trail = GeneralizeOperator._trace_ricochet_ray(
                raw, sr, sc, init_dir, shooter, bg, norm_turn_map)
            if trail is None:
                continue
            out = [row[:] for row in raw]
            for tr, tc in trail:
                out[tr][tc] = shooter
            return out
        return None

    def _apply_mirror_shoot_anchor(self, rule, input_grid):
        raw = input_grid.raw
        h = len(raw)
        w = len(raw[0]) if raw else 0
        if h == 0 or w == 0:
            return None
        a_color = rule.get("anchor_color")
        p_color = rule.get("pointer_color")
        m_color = rule.get("marker_color")
        div_color = rule.get("divider_color")
        axis = rule.get("divider_axis")
        if a_color is None or p_color is None or m_color is None:
            return None
        if div_color is None or axis not in ("row", "col"):
            return None

        counts = {}
        for row in raw:
            for c in row:
                counts[c] = counts.get(c, 0) + 1
        bg = max(counts, key=counts.get)

        div_row = div_col = None
        if axis == "row":
            for r in range(h):
                if all(v == div_color for v in raw[r]):
                    div_row = r
                    break
            if div_row is None:
                return None
        else:
            for c in range(w):
                if all(raw[r][c] == div_color for r in range(h)):
                    div_col = c
                    break
            if div_col is None:
                return None

        def mirror(r, c):
            if axis == "row":
                return (2 * div_row - r, c)
            return (r, 2 * div_col - c)

        obj_positions = [(r, c) for r in range(h) for c in range(w)
                         if raw[r][c] in (a_color, p_color)]
        comps = GeneralizeOperator._group_4connected(obj_positions)
        comp_lookup = {}
        for comp in comps:
            for cell in comp:
                comp_lookup[cell] = comp

        new_anchors = []
        for (ar, ac) in [(r, c) for (r, c) in obj_positions
                         if raw[r][c] == a_color]:
            comp = comp_lookup.get((ar, ac))
            if comp is None:
                continue
            comp_set = set(comp)
            visited = {(ar, ac): 0}
            queue = [(ar, ac)]
            farthest = (ar, ac)
            farthest_d = 0
            while queue:
                r, c = queue.pop(0)
                d = visited[(r, c)]
                for dr, dc in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                    nb = (r + dr, c + dc)
                    if nb not in comp_set or nb in visited:
                        continue
                    if raw[nb[0]][nb[1]] != p_color:
                        continue
                    visited[nb] = d + 1
                    queue.append(nb)
                    if d + 1 > farthest_d:
                        farthest_d = d + 1
                        farthest = nb
            if farthest_d == 0:
                continue
            new_anchors.append(farthest)

        out = [row[:] for row in raw]
        for r in range(h):
            for c in range(w):
                if out[r][c] in (a_color, p_color, m_color):
                    out[r][c] = bg
        for (nr, nc) in new_anchors:
            out[nr][nc] = a_color
            mr, mc = mirror(nr, nc)
            if 0 <= mr < h and 0 <= mc < w:
                out[mr][mc] = m_color
        return out

    def _apply_plus_majority_color(self, rule, input_grid):
        raw = input_grid.raw
        marker = rule.get("marker")
        if marker is None:
            return None
        v = GeneralizeOperator._plus_majority(raw, marker)
        if v is None:
            return None
        return [[v]]

    def _apply_framed_recolor_legend(self, rule, input_grid):
        raw = input_grid.raw
        return GeneralizeOperator._apply_framed_recolor_legend(raw)

    def _apply_diamond_connector(self, rule, input_grid):
        raw = input_grid.raw
        h = len(raw)
        w = len(raw[0]) if raw else 0
        connector = rule.get("connector")
        if connector is None:
            return None

        counts = {}
        for row in raw:
            for c in row:
                counts[c] = counts.get(c, 0) + 1
        bg = max(counts, key=counts.get)

        in_colors = {c for row in raw for c in row}
        fg_set = in_colors - {bg}
        if len(fg_set) != 1:
            return None
        fg = next(iter(fg_set))

        diamonds = GeneralizeOperator._find_diamonds(raw, fg, bg)
        out = [row[:] for row in raw]
        GeneralizeOperator._draw_diamond_connectors(out, diamonds, connector)
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
