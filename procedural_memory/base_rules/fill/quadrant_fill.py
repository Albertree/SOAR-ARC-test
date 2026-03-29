"""quadrant_fill -- solid rectangle of filler color with 4 diagonal corner markers;
each quadrant of the rectangle is filled with its nearest corner marker's color.

Pattern: A solid rectangle of one filler color (e.g. 5) sits on a bg=0 grid.
At each of the 4 diagonal corners (1 cell outside the rectangle), there is a
single non-bg pixel — the corner marker. In the output, the filler rectangle is
replaced: each quadrant is filled with the color of its nearest corner marker,
and the corner markers are removed.

Multiple such rectangles can appear in one grid (test case shows this).
"""

from procedural_memory.base_rules._helpers import find_components, bounding_box

RULE_TYPE = "quadrant_fill"
CATEGORY = "fill"


def _bg(grid):
    counts = {}
    for row in grid:
        for v in row:
            counts[v] = counts.get(v, 0) + 1
    return max(counts, key=counts.get)


def _find_filler_rects(grid, filler_color, bg):
    """Find solid rectangles of filler_color.
    Returns list of (top, left, bottom, right)."""
    comps = find_components(grid, filler_color)
    rects = []
    for comp in comps:
        min_r, max_r, min_c, max_c = bounding_box(comp)
        bh = max_r - min_r + 1
        bw = max_c - min_c + 1
        if len(comp) != bh * bw:
            continue  # not a solid rectangle
        rects.append((min_r, min_c, max_r, max_c))
    return rects


def _get_corner_markers(grid, top, left, bottom, right, bg, filler_color):
    """Get the 4 diagonal corner markers: TL, TR, BL, BR.
    Returns dict or None if not exactly 4 valid corners."""
    h = len(grid)
    w = len(grid[0]) if grid else 0
    corners = {}
    positions = {
        "TL": (top - 1, left - 1),
        "TR": (top - 1, right + 1),
        "BL": (bottom + 1, left - 1),
        "BR": (bottom + 1, right + 1),
    }
    for name, (r, c) in positions.items():
        if 0 <= r < h and 0 <= c < w:
            v = grid[r][c]
            if v != bg and v != filler_color:
                corners[name] = (r, c, v)
        else:
            return None
    if len(corners) != 4:
        return None
    return corners


def try_rule(patterns, task):
    """Detect: solid filler rectangles with 4 diagonal corner markers → quadrant fill."""
    if not patterns.get("grid_size_preserved"):
        return None

    filler_color = None

    for pair in task.example_pairs:
        raw_in = pair.input_grid.raw
        raw_out = pair.output_grid.raw
        bg = _bg(raw_in)

        # Find candidate filler color (non-bg color forming solid rectangles)
        color_counts = {}
        for row in raw_in:
            for v in row:
                if v != bg:
                    color_counts[v] = color_counts.get(v, 0) + 1

        found = False
        for fc in sorted(color_counts, key=color_counts.get, reverse=True):
            rects = _find_filler_rects(raw_in, fc, bg)
            if not rects:
                continue

            all_valid = True
            for (top, left, bottom, right) in rects:
                corners = _get_corner_markers(raw_in, top, left, bottom, right, bg, fc)
                if corners is None:
                    all_valid = False
                    break

                # Verify output: rectangle filled with quadrant colors, corners removed
                rect_h = bottom - top + 1
                rect_w = right - left + 1
                mid_r = top + rect_h // 2
                mid_c = left + rect_w // 2

                # Check quadrant filling in output
                for r in range(top, bottom + 1):
                    for c in range(left, right + 1):
                        if r < mid_r:
                            corner = "TL" if c < mid_c else "TR"
                        else:
                            corner = "BL" if c < mid_c else "BR"
                        expected = corners[corner][2]
                        if raw_out[r][c] != expected:
                            all_valid = False
                            break
                    if not all_valid:
                        break

                # Check corner markers removed in output
                if all_valid:
                    for name, (cr, cc, cv) in corners.items():
                        if raw_out[cr][cc] != bg:
                            all_valid = False
                            break

            if all_valid and rects:
                if filler_color is not None and filler_color != fc:
                    return None
                filler_color = fc
                found = True
                break

        if not found:
            return None

    return {
        "type": RULE_TYPE,
        "filler_color": filler_color,
        "confidence": 1.0,
    }


def apply_rule(rule, input_grid):
    """Apply quadrant_fill: replace each filler rectangle with corner-colored quadrants."""
    raw = input_grid.raw
    filler_color = rule["filler_color"]
    bg = _bg(raw)

    output = [row[:] for row in raw]
    rects = _find_filler_rects(raw, filler_color, bg)

    for (top, left, bottom, right) in rects:
        corners = _get_corner_markers(raw, top, left, bottom, right, bg, filler_color)
        if corners is None:
            continue

        rect_h = bottom - top + 1
        rect_w = right - left + 1
        mid_r = top + rect_h // 2
        mid_c = left + rect_w // 2

        # Fill quadrants
        for r in range(top, bottom + 1):
            for c in range(left, right + 1):
                if r < mid_r:
                    corner = "TL" if c < mid_c else "TR"
                else:
                    corner = "BL" if c < mid_c else "BR"
                output[r][c] = corners[corner][2]

        # Remove corner markers
        for name, (cr, cc, cv) in corners.items():
            output[cr][cc] = bg

    return output
