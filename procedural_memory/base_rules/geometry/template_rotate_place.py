"""template_rotate_place — connected multi-color template shapes are rotated/reflected
and placed at scattered single-pixel marker positions."""

from procedural_memory.base_rules._helpers import find_non_bg_components

RULE_TYPE = "template_rotate_place"
CATEGORY = "geometry"

# 8 rigid transformations: (a, b, c, d) means new_r = a*dr + b*dc, new_c = c*dr + d*dc
TRANSFORMS = [
    (1, 0, 0, 1),     # identity
    (0, 1, -1, 0),    # 90 CW
    (-1, 0, 0, -1),   # 180
    (0, -1, 1, 0),    # 90 CCW
    (-1, 0, 0, 1),    # reflect horizontal
    (1, 0, 0, -1),    # reflect vertical
    (0, 1, 1, 0),     # reflect main diagonal
    (0, -1, -1, 0),   # reflect anti-diagonal
]


def _apply_t(t, dr, dc):
    a, b, c, d = t
    return a * dr + b * dc, c * dr + d * dc


def _find_bg(grid):
    counts = {}
    for row in grid:
        for v in row:
            counts[v] = counts.get(v, 0) + 1
    return max(counts, key=counts.get)


def _analyze_template(grid, comp):
    """Return (anchor_color, endpoints, all_cells) or None.
    endpoints = [(color, dr, dc), ...] relative to anchor (first endpoint sorted by color).
    all_cells = [(color, dr, dc), ...] relative to anchor."""
    color_counts = {}
    for r, c in comp:
        v = grid[r][c]
        color_counts[v] = color_counts.get(v, 0) + 1

    skeleton = max(color_counts, key=color_counts.get)

    # Endpoints: non-skeleton cells, sorted by color for deterministic anchor
    ep_cells = sorted([(grid[r][c], r, c) for r, c in comp if grid[r][c] != skeleton])
    if len(ep_cells) < 2:
        return None

    anchor_color, ar, ac = ep_cells[0]
    endpoints = [(color, r - ar, c - ac) for color, r, c in ep_cells]
    all_cells = [(grid[r][c], r - ar, c - ac) for r, c in comp]

    return anchor_color, endpoints, all_cells


def _find_matching(grid, templates, markers, marker_positions, h, w):
    """Backtracking search to match templates with marker groups via rotations."""
    used = set()
    matches = []
    order = sorted(range(len(templates)), key=lambda i: -len(templates[i][1]))

    def backtrack(idx):
        if idx == len(order):
            return True

        ti = order[idx]
        anchor_color, endpoints, all_cells = templates[ti]

        for mr, mc in markers.get(anchor_color, []):
            if (mr, mc) in used:
                continue

            for T in TRANSFORMS:
                matched = {(mr, mc)}
                ok = True

                for color, dr, dc in endpoints[1:]:
                    ndr, ndc = _apply_t(T, dr, dc)
                    nr, nc = mr + ndr, mc + ndc
                    if (nr, nc) in used or (nr, nc) not in marker_positions or grid[nr][nc] != color:
                        ok = False
                        break
                    matched.add((nr, nc))

                if not ok:
                    continue

                # Compute output cells and check bounds
                output_cells = []
                in_bounds = True
                for color, dr, dc in all_cells:
                    ndr, ndc = _apply_t(T, dr, dc)
                    nr, nc = mr + ndr, mc + ndc
                    if not (0 <= nr < h and 0 <= nc < w):
                        in_bounds = False
                        break
                    output_cells.append((nr, nc, color))

                if not in_bounds:
                    continue

                old_used = used.copy()
                used.update(matched)
                matches.append((ti, output_cells))

                if backtrack(idx + 1):
                    return True

                matches.pop()
                used.clear()
                used.update(old_used)

        return False

    return matches if backtrack(0) else None


def _solve(grid):
    """Return list of (template_idx, output_cells) or None."""
    h = len(grid)
    w = len(grid[0]) if grid else 0
    bg = _find_bg(grid)
    if bg != 0:
        return None, bg, h, w

    comps = find_non_bg_components(grid, bg)

    templates_raw = [c for c in comps if len(c) > 1]
    markers_raw = [c for c in comps if len(c) == 1]

    if not templates_raw or len(markers_raw) < 2:
        return None, bg, h, w

    # Analyze templates - check all have multiple colors (skeleton + endpoints)
    templates = []
    for comp in templates_raw:
        colors = set(grid[r][c] for r, c in comp)
        if len(colors) < 2:
            return None, bg, h, w
        result = _analyze_template(grid, comp)
        if result is None:
            return None, bg, h, w
        templates.append(result)

    markers = {}
    marker_positions = set()
    for comp in markers_raw:
        r, c = comp[0]
        color = grid[r][c]
        markers.setdefault(color, []).append((r, c))
        marker_positions.add((r, c))

    matching = _find_matching(grid, templates, markers, marker_positions, h, w)
    return matching, bg, h, w


def try_rule(patterns, task):
    if not patterns.get("grid_size_preserved"):
        return None

    for pair in task.example_pairs:
        inp = pair.input_grid.raw
        out = pair.output_grid.raw

        matching, bg, h, w = _solve(inp)
        if matching is None:
            return None

        expected = [[bg] * w for _ in range(h)]
        for ti, output_cells in matching:
            for r, c, color in output_cells:
                expected[r][c] = color

        if expected != out:
            return None

    return {"type": RULE_TYPE, "confidence": 1.0}


def apply_rule(rule, input_grid):
    grid = input_grid.raw
    matching, bg, h, w = _solve(grid)
    if matching is None:
        return None

    output = [[bg] * w for _ in range(h)]
    for ti, output_cells in matching:
        for r, c, color in output_cells:
            output[r][c] = color

    return output
