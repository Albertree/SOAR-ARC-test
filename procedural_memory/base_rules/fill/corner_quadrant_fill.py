"""corner_quadrant_fill — rectangle(s) of uniform color with 4 corner markers get filled by quadrants."""

from procedural_memory.base_rules._helpers import find_components

RULE_TYPE = "corner_quadrant_fill"
CATEGORY = "fill"


def _find_rect_blocks(grid, fill_color):
    """Find all solid rectangular blocks of fill_color via connected components."""
    comps = find_components(grid, fill_color)
    rects = []
    for comp in comps:
        if len(comp) < 4:
            continue
        min_r = min(p[0] for p in comp)
        max_r = max(p[0] for p in comp)
        min_c = min(p[1] for p in comp)
        max_c = max(p[1] for p in comp)
        expected = (max_r - min_r + 1) * (max_c - min_c + 1)
        if len(comp) == expected:
            rects.append((min_r, min_c, max_r, max_c))
    return rects


def _find_corner_markers(grid, bg_color, fill_color, r1, c1, r2, c2):
    """Find 4 corner marker colors at diagonal positions outside the rectangle."""
    h = len(grid)
    w = len(grid[0]) if grid else 0
    corners = {}
    for label, dr, dc in [("TL", r1 - 1, c1 - 1), ("TR", r1 - 1, c2 + 1),
                           ("BL", r2 + 1, c1 - 1), ("BR", r2 + 1, c2 + 1)]:
        if 0 <= dr < h and 0 <= dc < w:
            v = grid[dr][dc]
            if v != bg_color and v != fill_color:
                corners[label] = v
    return corners if len(corners) == 4 else None


def try_rule(patterns, task):
    """Detect: rectangle(s) with 4 corner markers, output fills quadrants with corner colors."""
    if not task or not task.example_pairs:
        return None

    for pair in task.example_pairs:
        g0 = pair.input_grid
        g1 = pair.output_grid
        if g0 is None or g1 is None:
            return None
        if g0.height != g1.height or g0.width != g1.width:
            return None

    # Determine background color (most common in first input)
    from collections import Counter
    first_raw = task.example_pairs[0].input_grid.raw
    counts = Counter()
    for row in first_raw:
        for v in row:
            counts[v] += 1
    bg_color = counts.most_common(1)[0][0]

    # Find the fill color: try second-most-common
    if len(counts) < 2:
        return None

    fill_color = None
    for color, _ in counts.most_common():
        if color == bg_color:
            continue
        # Check if this color forms at least one rectangle with corner markers
        rects = _find_rect_blocks(first_raw, color)
        if rects:
            r1, c1, r2, c2 = rects[0]
            corners = _find_corner_markers(first_raw, bg_color, color, r1, c1, r2, c2)
            if corners:
                fill_color = color
                break

    if fill_color is None:
        return None

    # Verify first example
    first_out = task.example_pairs[0].output_grid.raw
    rects = _find_rect_blocks(first_raw, fill_color)
    for r1, c1, r2, c2 in rects:
        corners = _find_corner_markers(first_raw, bg_color, fill_color, r1, c1, r2, c2)
        if corners is None:
            return None
        # Check quadrant corners in output
        if first_out[r1][c1] != corners["TL"]:
            return None
        if first_out[r1][c2] != corners["TR"]:
            return None
        if first_out[r2][c1] != corners["BL"]:
            return None
        if first_out[r2][c2] != corners["BR"]:
            return None

    # Verify all other example pairs
    for pair in task.example_pairs[1:]:
        raw_in = pair.input_grid.raw
        raw_out = pair.output_grid.raw
        p_rects = _find_rect_blocks(raw_in, fill_color)
        if not p_rects:
            return None
        for r1, c1, r2, c2 in p_rects:
            c = _find_corner_markers(raw_in, bg_color, fill_color, r1, c1, r2, c2)
            if c is None:
                return None
            if raw_out[r1][c1] != c["TL"] or raw_out[r1][c2] != c["TR"]:
                return None
            if raw_out[r2][c1] != c["BL"] or raw_out[r2][c2] != c["BR"]:
                return None

    return {
        "type": RULE_TYPE,
        "fill_color": fill_color,
        "bg_color": bg_color,
        "confidence": 1.0,
    }


def apply_rule(rule, input_grid):
    """Apply: find rectangle(s) and corners, fill quadrants, remove markers."""
    raw = input_grid.raw
    bg_color = rule["bg_color"]
    fill_color = rule["fill_color"]

    rects = _find_rect_blocks(raw, fill_color)
    if not rects:
        return None

    output = [row[:] for row in raw]
    h = len(raw)
    w = len(raw[0]) if raw else 0

    for r1, c1, r2, c2 in rects:
        corners = _find_corner_markers(raw, bg_color, fill_color, r1, c1, r2, c2)
        if corners is None:
            return None

        rect_h = r2 - r1 + 1
        rect_w = c2 - c1 + 1
        mid_r = r1 + rect_h // 2
        mid_c = c1 + rect_w // 2

        # Fill quadrants
        for r in range(r1, r2 + 1):
            for c in range(c1, c2 + 1):
                if r < mid_r and c < mid_c:
                    output[r][c] = corners["TL"]
                elif r < mid_r and c >= mid_c:
                    output[r][c] = corners["TR"]
                elif r >= mid_r and c < mid_c:
                    output[r][c] = corners["BL"]
                else:
                    output[r][c] = corners["BR"]

        # Remove corner markers
        for dr, dc in [(r1 - 1, c1 - 1), (r1 - 1, c2 + 1),
                        (r2 + 1, c1 - 1), (r2 + 1, c2 + 1)]:
            if 0 <= dr < h and 0 <= dc < w:
                output[dr][dc] = bg_color

    return output
