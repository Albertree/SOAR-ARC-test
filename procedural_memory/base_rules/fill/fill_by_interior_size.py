"""fill_by_interior_size -- hollow rectangles bordered by a single color get
interiors filled with a color determined by interior area.

Pattern: multiple hollow rectangles of border_color on bg=0. Each rectangle's
interior (the 0-cells inside the border) is filled with a color based on
the interior dimensions: area -> color mapping is learned from examples.

Category: fill tasks where interior dimensions determine fill color.
"""

from procedural_memory.base_rules._helpers import find_components, bounding_box

RULE_TYPE = "fill_by_interior_size"
CATEGORY = "fill"


def _bg(grid):
    counts = {}
    for row in grid:
        for v in row:
            counts[v] = counts.get(v, 0) + 1
    return max(counts, key=counts.get)


def _find_hollow_rects(grid, border_color, bg):
    """Find hollow rectangles made of border_color.
    Returns list of (top, left, bottom, right, interior_h, interior_w)."""
    h = len(grid)
    w = len(grid[0]) if grid else 0
    comps = find_components(grid, border_color)
    rects = []
    for comp in comps:
        min_r, max_r, min_c, max_c = bounding_box(comp)
        bh = max_r - min_r + 1
        bw = max_c - min_c + 1
        if bh < 3 or bw < 3:
            continue
        # Check that border cells form a hollow rectangle
        expected_border = set()
        for r in range(min_r, max_r + 1):
            for c in range(min_c, max_c + 1):
                if r == min_r or r == max_r or c == min_c or c == max_c:
                    expected_border.add((r, c))
        if set(comp) != expected_border:
            continue
        int_h = bh - 2
        int_w = bw - 2
        rects.append((min_r, min_c, max_r, max_c, int_h, int_w))
    return rects


def try_rule(patterns, task):
    """Detect: hollow rectangles of one border color, interiors filled by area."""
    if not patterns.get("grid_size_preserved"):
        return None

    border_color = None
    area_to_color = {}

    for pair in task.example_pairs:
        raw_in = pair.input_grid.raw
        raw_out = pair.output_grid.raw
        bg = _bg(raw_in)

        # Find the border color (non-bg color that forms rectangles)
        non_bg_colors = set()
        for row in raw_in:
            for v in row:
                if v != bg:
                    non_bg_colors.add(v)

        if not non_bg_colors:
            return None

        # Try each non-bg color as border color
        found = False
        for bc in non_bg_colors:
            rects = _find_hollow_rects(raw_in, bc, bg)
            if len(rects) < 2:
                continue
            if border_color is not None and border_color != bc:
                return None

            # Check that interiors are filled in output
            valid = True
            for (top, left, bottom, right, int_h, int_w) in rects:
                area = int_h * int_w
                # Get fill color from output
                fill_color = raw_out[top + 1][left + 1]
                if fill_color == bg or fill_color == bc:
                    valid = False
                    break
                # Check all interior cells have same fill color
                for r in range(top + 1, bottom):
                    for c in range(left + 1, right):
                        if raw_out[r][c] != fill_color:
                            valid = False
                            break
                    if not valid:
                        break
                if not valid:
                    break
                # Check area -> color consistency
                if area in area_to_color and area_to_color[area] != fill_color:
                    valid = False
                    break
                area_to_color[area] = fill_color

            if valid:
                border_color = bc
                found = True
                break

        if not found:
            return None

    if not area_to_color:
        return None

    return {
        "type": RULE_TYPE,
        "border_color": border_color,
        "area_to_color": {str(k): v for k, v in area_to_color.items()},
        "confidence": 1.0,
    }


def apply_rule(rule, input_grid):
    """Apply fill_by_interior_size: fill each hollow rectangle's interior."""
    raw = input_grid.raw
    border_color = rule["border_color"]
    area_to_color = {int(k): v for k, v in rule["area_to_color"].items()}
    bg = _bg(raw)

    output = [row[:] for row in raw]
    rects = _find_hollow_rects(raw, border_color, bg)

    for (top, left, bottom, right, int_h, int_w) in rects:
        area = int_h * int_w
        fill_color = area_to_color.get(area)
        if fill_color is None:
            continue
        for r in range(top + 1, bottom):
            for c in range(left + 1, right):
                output[r][c] = fill_color

    return output
