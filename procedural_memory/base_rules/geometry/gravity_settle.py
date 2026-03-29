"""gravity_settle — colored objects settle downward in separator-bounded cells with 1-row gap."""

from procedural_memory.base_rules._helpers import group_positions

RULE_TYPE = "gravity_settle"
CATEGORY = "geometry"


def _find_bg_across_pairs(pairs):
    """Background = most common color across ALL example pair inputs."""
    counts = {}
    for pair in pairs:
        for row in pair.input_grid.raw:
            for v in row:
                counts[v] = counts.get(v, 0) + 1
    return max(counts, key=counts.get) if counts else 0


def _find_separator_with_output(inp, out, bg):
    """Separator color: non-bg color at identical positions in input and output."""
    h = len(inp)
    w = len(inp[0])
    colors = set()
    for r in range(h):
        for c in range(w):
            if inp[r][c] != bg:
                colors.add(inp[r][c])
            if out[r][c] != bg:
                colors.add(out[r][c])

    for color in colors:
        inp_pos = set()
        out_pos = set()
        for r in range(h):
            for c in range(w):
                if inp[r][c] == color:
                    inp_pos.add((r, c))
                if out[r][c] == color:
                    out_pos.add((r, c))
        if inp_pos == out_pos and len(inp_pos) > 0:
            return color
    return None


def _find_separator_from_input(grid, bg):
    """Detect separator from input alone: most common non-bg color on last row."""
    h = len(grid)
    w = len(grid[0]) if grid else 0
    if h == 0:
        return None

    last_row_counts = {}
    for c in range(w):
        v = grid[h - 1][c]
        if v != bg:
            last_row_counts[v] = last_row_counts.get(v, 0) + 1

    if not last_row_counts:
        return None

    return max(last_row_counts, key=last_row_counts.get)


def _col_floor(grid, col, sep_color, h):
    """Lowest non-separator row in a column."""
    for r in range(h - 1, -1, -1):
        if grid[r][col] != sep_color:
            return r
    return -1


def _simulate_drop(inp, bg, sep_color):
    """Drop all object components downward. Returns the resulting grid."""
    h = len(inp)
    w = len(inp[0])

    sep_positions = set()
    obj_pixels = {}
    for r in range(h):
        for c in range(w):
            v = inp[r][c]
            if v == sep_color:
                sep_positions.add((r, c))
            elif v != bg:
                obj_pixels[(r, c)] = v

    if not obj_pixels:
        return [row[:] for row in inp]

    # Connected components of object pixels
    components = group_positions(list(obj_pixels.keys()))

    # Sort by max row descending (bottom-most components first)
    components.sort(key=lambda comp: max(r for r, c in comp), reverse=True)

    # Initial landing row per column: floor - 1 (1-row gap from separator/edge)
    landing = {}
    for c in range(w):
        f = _col_floor(inp, c, sep_color, h)
        landing[c] = f - 1  # 1-gap from floor

    # Build output
    output = [[bg] * w for _ in range(h)]
    for r, c in sep_positions:
        output[r][c] = sep_color

    for comp in components:
        col_bottom = {}
        for r, c in comp:
            if c not in col_bottom or r > col_bottom[c]:
                col_bottom[c] = r

        min_drop = None
        for c, bot in col_bottom.items():
            if c not in landing or landing[c] < 0:
                min_drop = 0
                break
            drop_c = landing[c] - bot
            if min_drop is None or drop_c < min_drop:
                min_drop = drop_c

        if min_drop is None:
            min_drop = 0
        drop = max(0, min_drop)

        for r, c in comp:
            new_r = r + drop
            if 0 <= new_r < h:
                output[new_r][c] = obj_pixels[(r, c)]

        col_top = {}
        for r, c in comp:
            new_r = r + drop
            if c not in col_top or new_r < col_top[c]:
                col_top[c] = new_r
        for c, top_r in col_top.items():
            landing[c] = top_r - 1

    return output


def try_rule(patterns, task):
    """Detect: objects settling downward in separator-bounded cells."""
    pairs = task.example_pairs
    if not pairs:
        return None

    bg = _find_bg_across_pairs(pairs)

    for pair in pairs:
        inp = pair.input_grid.raw
        out = pair.output_grid.raw

        if len(inp) != len(out) or len(inp[0]) != len(out[0]):
            return None

        sep = _find_separator_with_output(inp, out, bg)
        if sep is None:
            return None

        # Must have object pixels
        has_objects = False
        for r in range(len(inp)):
            for c in range(len(inp[0])):
                if inp[r][c] != bg and inp[r][c] != sep:
                    has_objects = True
                    break
            if has_objects:
                break
        if not has_objects:
            return None

        # Simulate and verify
        simulated = _simulate_drop(inp, bg, sep)
        if simulated != out:
            return None

    return {
        "type": RULE_TYPE,
        "bg": bg,
        "confidence": 1.0,
    }


def apply_rule(rule, input_grid):
    """Drop objects downward with 1-row gap from separator floor."""
    raw = input_grid.raw
    bg = rule["bg"]
    sep = _find_separator_from_input(raw, bg)
    if sep is None:
        return None
    return _simulate_drop(raw, bg, sep)
