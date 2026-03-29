"""fill_rect_by_size — fill rectangular outlines based on interior area rank."""

RULE_TYPE = "fill_rect_by_size"
CATEGORY = "fill"


def _find_outlined_rectangles(grid, outline_color, bg_color):
    """Find rectangles outlined with outline_color whose interior is bg_color."""
    h = len(grid)
    w = len(grid[0]) if grid else 0
    visited = [[False] * w for _ in range(h)]
    rects = []

    for r in range(h):
        for c in range(w):
            if grid[r][c] == outline_color and not visited[r][c]:
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

                min_r = min(p[0] for p in component)
                max_r = max(p[0] for p in component)
                min_c = min(p[1] for p in component)
                max_c = max(p[1] for p in component)

                if max_r - min_r < 2 or max_c - min_c < 2:
                    continue

                expected = set()
                for rr in range(min_r, max_r + 1):
                    expected.add((rr, min_c))
                    expected.add((rr, max_c))
                for cc in range(min_c, max_c + 1):
                    expected.add((min_r, cc))
                    expected.add((max_r, cc))

                if set(component) != expected:
                    continue

                interior_ok = True
                for rr in range(min_r + 1, max_r):
                    for cc in range(min_c + 1, max_c):
                        if grid[rr][cc] != bg_color:
                            interior_ok = False
                            break
                    if not interior_ok:
                        break

                if interior_ok:
                    interior_area = (max_r - min_r - 1) * (max_c - min_c - 1)
                    rects.append({
                        "bounds": (min_r, min_c, max_r, max_c),
                        "interior_area": interior_area,
                    })

    return rects


def try_rule(patterns, task):
    """Detect: rectangles outlined in one color, interiors filled by area rank."""
    if not task or not task.example_pairs:
        return None

    # Need at least 2 rectangles to establish a size-based mapping
    # Try to find the outline color and background color
    outline_color = None
    bg_color = None

    for pair in task.example_pairs:
        g0 = pair.input_grid
        g1 = pair.output_grid
        if g0 is None or g1 is None:
            return None
        if g0.height != g1.height or g0.width != g1.width:
            return None

    # Try common outline/bg combos
    first_input = task.example_pairs[0].input_grid.raw
    from collections import Counter
    color_counts = Counter()
    for row in first_input:
        for v in row:
            color_counts[v] += 1

    # Background is most common, outline is second most common (among non-zero typically)
    sorted_colors = color_counts.most_common()
    if len(sorted_colors) < 2:
        return None

    bg_color = sorted_colors[0][0]
    outline_color = sorted_colors[1][0]

    # Find rectangles in first example input
    rects = _find_outlined_rectangles(first_input, outline_color, bg_color)
    if len(rects) < 2:
        return None

    # Determine area-to-color mapping from first example output
    first_output = task.example_pairs[0].output_grid.raw
    area_to_color = {}
    for rect in rects:
        min_r, min_c, max_r, max_c = rect["bounds"]
        # Read the fill color from the output interior
        fill_color = first_output[min_r + 1][min_c + 1]
        if fill_color == bg_color:
            return None  # Not filled
        area = rect["interior_area"]
        if area in area_to_color and area_to_color[area] != fill_color:
            return None  # Inconsistent
        area_to_color[area] = fill_color

    if not area_to_color:
        return None

    # Verify on all other example pairs
    for pair in task.example_pairs[1:]:
        raw_in = pair.input_grid.raw
        raw_out = pair.output_grid.raw
        pair_rects = _find_outlined_rectangles(raw_in, outline_color, bg_color)
        if len(pair_rects) < 2:
            return None

        for rect in pair_rects:
            min_r, min_c, max_r, max_c = rect["bounds"]
            fill_color = raw_out[min_r + 1][min_c + 1]
            area = rect["interior_area"]
            if area in area_to_color:
                if area_to_color[area] != fill_color:
                    return None
            else:
                area_to_color[area] = fill_color

    return {
        "type": RULE_TYPE,
        "outline_color": outline_color,
        "bg_color": bg_color,
        "area_to_color": {str(k): v for k, v in area_to_color.items()},
        "confidence": 1.0,
    }


def apply_rule(rule, input_grid):
    """Apply: find rectangles, fill interiors based on area mapping."""
    raw = input_grid.raw
    outline_color = rule["outline_color"]
    bg_color = rule["bg_color"]
    area_to_color = {int(k): v for k, v in rule["area_to_color"].items()}

    output = [row[:] for row in raw]
    rects = _find_outlined_rectangles(raw, outline_color, bg_color)

    for rect in rects:
        min_r, min_c, max_r, max_c = rect["bounds"]
        area = rect["interior_area"]
        fill_color = area_to_color.get(area)
        if fill_color is not None:
            for r in range(min_r + 1, max_r):
                for c in range(min_c + 1, max_c):
                    output[r][c] = fill_color

    return output
