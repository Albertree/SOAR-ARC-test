"""fill_by_interior_size — hollow rectangles bordered by a single color get their interior filled based on interior dimensions."""

from procedural_memory.base_rules._helpers import find_components

RULE_TYPE = "fill_by_interior_size"
CATEGORY = "fill"

# Interior side length -> fill color
_SIZE_COLOR = {1: 6, 2: 7, 3: 8}


def _find_rectangles(grid, border_color):
    """Find axis-aligned hollow rectangles made of border_color.

    Returns list of (r1, c1, r2, c2) bounding boxes whose border is
    entirely border_color and whose interior is entirely 0 (background).
    """
    h = len(grid)
    w = len(grid[0]) if grid else 0
    comps = find_components(grid, border_color)
    rects = []

    for comp in comps:
        rows = [r for r, c in comp]
        cols = [c for r, c in comp]
        r1, r2 = min(rows), max(rows)
        c1, c2 = min(cols), max(cols)

        # Must have at least 3x3 to have an interior
        if r2 - r1 < 2 or c2 - c1 < 2:
            continue

        # Check that border cells match the component exactly
        expected_border = set()
        for r in range(r1, r2 + 1):
            for c in range(c1, c2 + 1):
                if r == r1 or r == r2 or c == c1 or c == c2:
                    expected_border.add((r, c))

        if set(comp) != expected_border:
            continue

        # Check interior is all background (0)
        all_bg = True
        for r in range(r1 + 1, r2):
            for c in range(c1 + 1, c2):
                if grid[r][c] != 0:
                    all_bg = False
                    break
            if not all_bg:
                break
        if not all_bg:
            continue

        rects.append((r1, c1, r2, c2))

    return rects


def try_rule(patterns, task):
    """Detect: grid has hollow rectangles of one border color, interiors filled by size."""
    pairs = task.example_pairs
    if not pairs:
        return None

    border_color = None

    for pair in pairs:
        inp = pair.input_grid.raw
        out = pair.output_grid.raw

        if len(inp) != len(out) or len(inp[0]) != len(out[0]):
            return None

        # Find candidate border color (non-zero, non-background)
        # Try to detect: look for a color that forms rectangles
        colors_in_grid = set()
        for row in inp:
            for v in row:
                if v != 0:
                    colors_in_grid.add(v)

        if not colors_in_grid:
            return None

        # Border color should be the one forming rectangles
        found = False
        for bc in colors_in_grid:
            rects = _find_rectangles(inp, bc)
            if len(rects) >= 1:
                # Verify output fills interiors correctly
                valid = True
                for (r1, c1, r2, c2) in rects:
                    ih = r2 - r1 - 1  # interior height
                    iw = c2 - c1 - 1  # interior width
                    side = min(ih, iw)
                    fill_color = _SIZE_COLOR.get(side)
                    if fill_color is None:
                        valid = False
                        break
                    # Check output has this fill
                    for r in range(r1 + 1, r2):
                        for c in range(c1 + 1, c2):
                            if out[r][c] != fill_color:
                                valid = False
                                break
                        if not valid:
                            break
                    if not valid:
                        break

                if valid and rects:
                    if border_color is None:
                        border_color = bc
                    elif border_color != bc:
                        return None
                    found = True
                    break

        if not found:
            return None

    return {
        "type": RULE_TYPE,
        "border_color": border_color,
        "confidence": 1.0,
    }


def apply_rule(rule, input_grid):
    """Fill each hollow rectangle's interior based on its size."""
    raw = input_grid.raw
    h = len(raw)
    w = len(raw[0]) if raw else 0
    bc = rule["border_color"]

    output = [row[:] for row in raw]
    rects = _find_rectangles(raw, bc)

    for (r1, c1, r2, c2) in rects:
        ih = r2 - r1 - 1
        iw = c2 - c1 - 1
        side = min(ih, iw)
        fill_color = _SIZE_COLOR.get(side)
        if fill_color is None:
            continue
        for r in range(r1 + 1, r2):
            for c in range(c1 + 1, c2):
                output[r][c] = fill_color

    return output
