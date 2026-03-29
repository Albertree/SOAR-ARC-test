"""connector_block_split — three single-color blocks on uniform background;
the middle (connector) block pushes through one outer block which splits."""

from procedural_memory.base_rules._helpers import find_components, bounding_box

RULE_TYPE = "connector_block_split"
CATEGORY = "structure"


def _find_bg(grid):
    counts = {}
    for row in grid:
        for v in row:
            counts[v] = counts.get(v, 0) + 1
    return max(counts, key=counts.get)


def _is_rect(cells, bb):
    min_r, max_r, min_c, max_c = bb
    return len(cells) == (max_r - min_r + 1) * (max_c - min_c + 1)


def _analyze(grid):
    """Return (bg, stack_dir, B, S, F, h, w) or None."""
    h = len(grid)
    w = len(grid[0]) if grid else 0
    bg = _find_bg(grid)

    # Find blocks: one connected component per non-bg color
    color_set = set()
    for row in grid:
        for v in row:
            if v != bg:
                color_set.add(v)

    blocks = []
    for color in sorted(color_set):
        for comp in find_components(grid, color):
            bb = bounding_box(comp)
            min_r, max_r, min_c, max_c = bb
            blocks.append({
                'color': color,
                'cells': comp,
                'bb': bb,
                'min_r': min_r, 'max_r': max_r,
                'min_c': min_c, 'max_c': max_c,
                'height': max_r - min_r + 1,
                'width': max_c - min_c + 1,
                'size': len(comp),
                'is_rect': _is_rect(comp, bb),
            })

    if len(blocks) != 3:
        return None

    # Try both stack directions
    for stack_dir in ['vertical', 'horizontal']:
        if stack_dir == 'vertical':
            ordered = sorted(blocks, key=lambda b: (b['min_r'] + b['max_r']) / 2)
            # Check perpendicular (column) overlap between adjacent pairs
            if not (max(ordered[0]['min_c'], ordered[1]['min_c']) <= min(ordered[0]['max_c'], ordered[1]['max_c'])):
                continue
            if not (max(ordered[1]['min_c'], ordered[2]['min_c']) <= min(ordered[1]['max_c'], ordered[2]['max_c'])):
                continue
        else:
            ordered = sorted(blocks, key=lambda b: (b['min_c'] + b['max_c']) / 2)
            if not (max(ordered[0]['min_r'], ordered[1]['min_r']) <= min(ordered[0]['max_r'], ordered[1]['max_r'])):
                continue
            if not (max(ordered[1]['min_r'], ordered[2]['min_r']) <= min(ordered[1]['max_r'], ordered[2]['max_r'])):
                continue

        B = ordered[1]  # Middle block = connector
        outer = [ordered[0], ordered[2]]

        if not B['is_rect']:
            continue

        # S = rectangular outer block with perpendicular extent > B's
        if stack_dir == 'vertical':
            perp_B = B['width']
            candidates = [(o, o['width']) for o in outer if o['is_rect'] and o['width'] > perp_B]
        else:
            perp_B = B['height']
            candidates = [(o, o['height']) for o in outer if o['is_rect'] and o['height'] > perp_B]

        if not candidates:
            continue

        candidates.sort(key=lambda x: x[1])
        S = candidates[0][0]
        F = outer[0] if outer[0] is not S else outer[1]

        return bg, stack_dir, B, S, F, h, w

    return None


def _compute_output(grid, bg, stack_dir, B, S, F, h, w):
    output = [[bg] * w for _ in range(h)]

    # F stays unchanged
    for r, c in F['cells']:
        output[r][c] = grid[r][c]

    s_color = S['color']
    b_color = B['color']

    if stack_dir == 'vertical':
        b_min_c, b_max_c = B['min_c'], B['max_c']

        # S halves: left grows 1 outward, right grows 1 outward
        for r in range(S['min_r'], S['max_r'] + 1):
            for c in range(max(0, S['min_c'] - 1), b_min_c):
                output[r][c] = s_color
            for c in range(b_max_c + 1, min(w, S['max_c'] + 2)):
                output[r][c] = s_color

        # B position: far side of S from F
        f_center = (F['min_r'] + F['max_r']) / 2
        s_center = (S['min_r'] + S['max_r']) / 2

        if f_center > s_center:
            # F below → B above S
            b_new_min_r = S['min_r'] - B['height']
            if b_new_min_r < 0:
                b_new_min_r = 0
        else:
            # F above → B below S
            b_new_min_r = S['max_r'] + 1
            if b_new_min_r + B['height'] > h:
                b_new_min_r = h - B['height']

        for dr in range(B['height']):
            for dc in range(B['width']):
                r = b_new_min_r + dr
                c = B['min_c'] + dc
                if 0 <= r < h and 0 <= c < w:
                    output[r][c] = b_color

    else:  # horizontal
        b_min_r, b_max_r = B['min_r'], B['max_r']

        # S halves: top grows 1 outward, bottom grows 1 outward
        for c in range(S['min_c'], S['max_c'] + 1):
            for r in range(max(0, S['min_r'] - 1), b_min_r):
                output[r][c] = s_color
            for r in range(b_max_r + 1, min(h, S['max_r'] + 2)):
                output[r][c] = s_color

        # B position
        f_center = (F['min_c'] + F['max_c']) / 2
        s_center = (S['min_c'] + S['max_c']) / 2

        if f_center > s_center:
            # F right → B left of S
            b_new_min_c = S['min_c'] - B['width']
            if b_new_min_c < 0:
                b_new_min_c = 0
        else:
            # F left → B right of S
            b_new_min_c = S['max_c'] + 1
            if b_new_min_c + B['width'] > w:
                b_new_min_c = w - B['width']

        for dr in range(B['height']):
            for dc in range(B['width']):
                r = B['min_r'] + dr
                c = b_new_min_c + dc
                if 0 <= r < h and 0 <= c < w:
                    output[r][c] = b_color

    return output


def try_rule(patterns, task):
    if not patterns.get("grid_size_preserved"):
        return None

    for pair in task.example_pairs:
        inp = pair.input_grid.raw
        out = pair.output_grid.raw

        result = _analyze(inp)
        if result is None:
            return None

        bg, stack_dir, B, S, F, h, w = result
        expected = _compute_output(inp, bg, stack_dir, B, S, F, h, w)

        if expected != out:
            return None

    return {"type": RULE_TYPE, "confidence": 1.0}


def apply_rule(rule, input_grid):
    grid = input_grid.raw
    result = _analyze(grid)
    if result is None:
        return None

    bg, stack_dir, B, S, F, h, w = result
    return _compute_output(grid, bg, stack_dir, B, S, F, h, w)
