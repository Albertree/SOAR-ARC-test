"""arrow_ray_edge — arrow shapes fire dotted rays toward grid edges; edge row/col fills with tip color."""

RULE_TYPE = "arrow_ray_edge"
CATEGORY = "detect"


def _find_bg(grid):
    """Find background color (most frequent)."""
    counts = {}
    for row in grid:
        for v in row:
            counts[v] = counts.get(v, 0) + 1
    return max(counts, key=counts.get)


def _find_arrow_shapes(grid, bg):
    """Find arrow shapes: connected non-bg regions with 2 colors (body + 1 tip cell)."""
    h = len(grid)
    w = len(grid[0]) if grid else 0
    visited = set()
    shapes = []

    for r in range(h):
        for c in range(w):
            if grid[r][c] != bg and (r, c) not in visited:
                comp = []
                queue = [(r, c)]
                visited.add((r, c))
                while queue:
                    cr, cc = queue.pop(0)
                    comp.append((cr, cc))
                    for dr, dc in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                        nr, nc = cr + dr, cc + dc
                        if 0 <= nr < h and 0 <= nc < w and (nr, nc) not in visited and grid[nr][nc] != bg:
                            visited.add((nr, nc))
                            queue.append((nr, nc))

                color_counts = {}
                for pr, pc in comp:
                    v = grid[pr][pc]
                    color_counts[v] = color_counts.get(v, 0) + 1

                if len(color_counts) != 2:
                    continue

                sorted_colors = sorted(color_counts.items(), key=lambda x: -x[1])
                body_color = sorted_colors[0][0]
                tip_color = sorted_colors[1][0]

                if color_counts[tip_color] != 1:
                    continue

                tip_pos = None
                body_positions = []
                for pr, pc in comp:
                    if grid[pr][pc] == tip_color:
                        tip_pos = (pr, pc)
                    else:
                        body_positions.append((pr, pc))

                shapes.append({
                    'tip_color': tip_color,
                    'tip_pos': tip_pos,
                    'body_positions': body_positions,
                })

    return shapes


def _fire_direction(tip_pos, body_positions):
    """Determine fire direction (away from body centroid)."""
    if not body_positions:
        return None

    centroid_r = sum(r for r, c in body_positions) / len(body_positions)
    centroid_c = sum(c for r, c in body_positions) / len(body_positions)

    dr = tip_pos[0] - centroid_r
    dc = tip_pos[1] - centroid_c

    if abs(dr) > abs(dc):
        return (-1, 0) if dr < 0 else (1, 0)
    elif abs(dc) > abs(dr):
        return (0, -1) if dc < 0 else (0, 1)
    else:
        # Tie-break
        if dr != 0:
            return (-1, 0) if dr < 0 else (1, 0)
        return (0, -1) if dc < 0 else (0, 1)


def _compute_output(grid, shapes):
    """Compute output by firing dotted rays and filling edges."""
    h = len(grid)
    w = len(grid[0]) if grid else 0
    output = [row[:] for row in grid]

    edge_fills = {}  # 'top'/'bottom'/'left'/'right' -> tip_color

    for shape in shapes:
        tip_r, tip_c = shape['tip_pos']
        direction = _fire_direction(shape['tip_pos'], shape['body_positions'])
        if direction is None:
            continue

        dr, dc = direction
        tip_color = shape['tip_color']

        # Fire dots at even distances from tip
        dist = 1
        cr, cc = tip_r + dr, tip_c + dc
        while 0 <= cr < h and 0 <= cc < w:
            if dist % 2 == 0:
                output[cr][cc] = tip_color
            dist += 1
            cr += dr
            cc += dc

        # Record which edge was hit
        if dr == -1:
            edge_fills['top'] = tip_color
        elif dr == 1:
            edge_fills['bottom'] = tip_color
        elif dc == -1:
            edge_fills['left'] = tip_color
        elif dc == 1:
            edge_fills['right'] = tip_color

    # Fill edges
    if 'top' in edge_fills:
        for c in range(w):
            output[0][c] = edge_fills['top']
    if 'bottom' in edge_fills:
        for c in range(w):
            output[h - 1][c] = edge_fills['bottom']
    if 'left' in edge_fills:
        for r in range(h):
            output[r][0] = edge_fills['left']
    if 'right' in edge_fills:
        for r in range(h):
            output[r][w - 1] = edge_fills['right']

    # Corners where two edges meet become 0
    corners = [
        (0, 0, 'top', 'left'),
        (0, w - 1, 'top', 'right'),
        (h - 1, 0, 'bottom', 'left'),
        (h - 1, w - 1, 'bottom', 'right'),
    ]
    for r, c, e1, e2 in corners:
        if e1 in edge_fills and e2 in edge_fills:
            output[r][c] = 0

    return output


def try_rule(patterns, task):
    """Detect: arrow shapes with tips that fire dotted rays to grid edges."""
    pairs = task.example_pairs
    if not pairs:
        return None

    if not patterns.get("grid_size_preserved"):
        return None

    for pair in pairs:
        inp = pair.input_grid.raw
        out = pair.output_grid.raw
        h = len(inp)
        w = len(inp[0]) if inp else 0

        if len(out) != h or len(out[0]) != w:
            return None

        bg = _find_bg(inp)
        shapes = _find_arrow_shapes(inp, bg)

        if len(shapes) < 1:
            return None

        # Verify each shape has a valid fire direction
        for shape in shapes:
            if _fire_direction(shape['tip_pos'], shape['body_positions']) is None:
                return None

        # Compute expected output and verify
        expected = _compute_output(inp, shapes)

        if expected != out:
            return None

    return {
        "type": RULE_TYPE,
        "confidence": 1.0,
    }


def apply_rule(rule, input_grid):
    """Fire dotted rays from arrow tips to grid edges."""
    raw = input_grid.raw
    bg = _find_bg(raw)
    shapes = _find_arrow_shapes(raw, bg)

    if not shapes:
        return None

    return _compute_output(raw, shapes)
