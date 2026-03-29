"""quadrant_fill — rectangle of filler color with 4 diagonal corner markers; replace filler with quadrant colors."""

from procedural_memory.base_rules._helpers import find_components

RULE_TYPE = "quadrant_fill"
CATEGORY = "fill"


def _find_filler_rects(grid, filler_color):
    """Find all solid rectangles of filler_color using connected components.

    Returns list of (r1, c1, r2, c2) for each rectangular component.
    """
    comps = find_components(grid, filler_color)
    rects = []
    for comp in comps:
        rows = [r for r, c in comp]
        cols = [c for r, c in comp]
        r1, r2 = min(rows), max(rows)
        c1, c2 = min(cols), max(cols)
        expected = (r2 - r1 + 1) * (c2 - c1 + 1)
        if len(comp) == expected and expected >= 4:
            rects.append((r1, c1, r2, c2))
    return rects


def _find_corners(grid, filler_color, r1, c1, r2, c2):
    """Find 4 corner markers at diagonal positions outside the filler rectangle."""
    h = len(grid)
    w = len(grid[0]) if grid else 0
    corners = {}
    positions = [
        ('top_left', r1 - 1, c1 - 1),
        ('top_right', r1 - 1, c2 + 1),
        ('bottom_left', r2 + 1, c1 - 1),
        ('bottom_right', r2 + 1, c2 + 1),
    ]
    for key, cr, cc in positions:
        if 0 <= cr < h and 0 <= cc < w:
            v = grid[cr][cc]
            if v != 0 and v != filler_color:
                corners[key] = v
    if len(corners) == 4:
        return corners
    return None


def _detect_filler_color(grid):
    """Detect which color is the filler (forms solid rectangles with corner markers)."""
    h = len(grid)
    w = len(grid[0]) if grid else 0
    colors = set()
    for r in range(h):
        for c in range(w):
            if grid[r][c] != 0:
                colors.add(grid[r][c])

    for fc in colors:
        rects = _find_filler_rects(grid, fc)
        if rects:
            # Check at least one has valid corners
            for rect in rects:
                if _find_corners(grid, fc, *rect) is not None:
                    return fc
    return None


def try_rule(patterns, task):
    """Detect: solid rectangle(s) of filler color with 4 corner markers replaced by quadrant colors."""
    pairs = task.example_pairs
    if not pairs:
        return None

    filler_color = None

    for pair in pairs:
        inp = pair.input_grid.raw
        out = pair.output_grid.raw

        if len(inp) != len(out) or len(inp[0]) != len(out[0]):
            return None

        fc = _detect_filler_color(inp)
        if fc is None:
            return None

        if filler_color is None:
            filler_color = fc
        elif filler_color != fc:
            return None

        rects = _find_filler_rects(inp, fc)
        if not rects:
            return None

        for (r1, c1, r2, c2) in rects:
            corners = _find_corners(inp, fc, r1, c1, r2, c2)
            if corners is None:
                return None

            rect_h = r2 - r1 + 1
            rect_w = c2 - c1 + 1
            mid_r = r1 + rect_h // 2
            mid_c = c1 + rect_w // 2

            for r in range(r1, r2 + 1):
                for c in range(c1, c2 + 1):
                    if r < mid_r:
                        expected = corners['top_left'] if c < mid_c else corners['top_right']
                    else:
                        expected = corners['bottom_left'] if c < mid_c else corners['bottom_right']
                    if out[r][c] != expected:
                        return None

            # Verify corner positions are cleared in output
            for key, cr, cc in [('top_left', r1 - 1, c1 - 1), ('top_right', r1 - 1, c2 + 1),
                                ('bottom_left', r2 + 1, c1 - 1), ('bottom_right', r2 + 1, c2 + 1)]:
                if 0 <= cr < len(out) and 0 <= cc < len(out[0]):
                    if out[cr][cc] != 0:
                        return None

    return {
        "type": RULE_TYPE,
        "filler_color": filler_color,
        "confidence": 1.0,
    }


def apply_rule(rule, input_grid):
    """Replace filler rectangle(s) with quadrant colors, clear corner markers."""
    raw = input_grid.raw
    h = len(raw)
    w = len(raw[0]) if raw else 0
    fc = rule["filler_color"]

    output = [row[:] for row in raw]
    rects = _find_filler_rects(raw, fc)

    for (r1, c1, r2, c2) in rects:
        corners = _find_corners(raw, fc, r1, c1, r2, c2)
        if corners is None:
            return None

        rect_h = r2 - r1 + 1
        rect_w = c2 - c1 + 1
        mid_r = r1 + rect_h // 2
        mid_c = c1 + rect_w // 2

        for r in range(r1, r2 + 1):
            for c in range(c1, c2 + 1):
                if r < mid_r:
                    output[r][c] = corners['top_left'] if c < mid_c else corners['top_right']
                else:
                    output[r][c] = corners['bottom_left'] if c < mid_c else corners['bottom_right']

        # Clear corner markers
        for key, cr, cc in [('top_left', r1 - 1, c1 - 1), ('top_right', r1 - 1, c2 + 1),
                            ('bottom_left', r2 + 1, c1 - 1), ('bottom_right', r2 + 1, c2 + 1)]:
            if 0 <= cr < h and 0 <= cc < w:
                output[cr][cc] = 0

    return output
