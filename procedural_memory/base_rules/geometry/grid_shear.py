"""grid_shear — grid/rectangle structure with rows cyclically shifted left/right."""

RULE_TYPE = "grid_shear"
CATEGORY = "geometry"


def _find_grid_structure(grid):
    """Find the single non-bg color forming a grid and its row range.

    Returns (grid_color, top_row, bottom_row) or (None, None, None).
    """
    h = len(grid)
    w = len(grid[0]) if grid else 0
    bg = 0

    colors = set()
    for r in range(h):
        for c in range(w):
            if grid[r][c] != bg:
                colors.add(grid[r][c])

    if len(colors) != 1:
        return None, None, None

    grid_color = colors.pop()

    top_row = None
    bottom_row = None
    for r in range(h):
        if any(grid[r][c] == grid_color for c in range(w)):
            if top_row is None:
                top_row = r
            bottom_row = r

    if top_row is None:
        return None, None, None

    return grid_color, top_row, bottom_row


def _compute_shift(d, N):
    """Compute horizontal shift for row at distance d from top of grid."""
    cycle = [-1, 0, 1, 0]
    p = (2 - N) % 4
    return cycle[(d + p) % 4]


def try_rule(patterns, task):
    """Detect: grid structure with rows cyclically shifted left/right."""
    pairs = task.example_pairs
    if not pairs:
        return None

    for pair in pairs:
        inp = pair.input_grid.raw
        out = pair.output_grid.raw

        if len(inp) != len(out) or len(inp[0]) != len(out[0]):
            return None

        h = len(inp)
        w = len(inp[0])

        gc, top, bot = _find_grid_structure(inp)
        if gc is None:
            return None

        N = bot - top + 1
        if N < 3:
            return None

        # Verify the output matches the shifted grid
        for r in range(h):
            for c in range(w):
                if r < top or r > bot:
                    if out[r][c] != 0:
                        return None
                else:
                    d = r - top
                    shift = _compute_shift(d, N)
                    src_c = c - shift
                    expected = inp[r][src_c] if 0 <= src_c < w else 0
                    if out[r][c] != expected:
                        return None

    return {
        "type": RULE_TYPE,
        "confidence": 1.0,
    }


def apply_rule(rule, input_grid):
    """Shift each row of the grid structure by the cyclic offset."""
    raw = input_grid.raw
    h = len(raw)
    w = len(raw[0]) if raw else 0

    gc, top, bot = _find_grid_structure(raw)
    if gc is None:
        return None

    N = bot - top + 1
    output = [[0] * w for _ in range(h)]

    for r in range(h):
        if r < top or r > bot:
            output[r] = raw[r][:]
        else:
            d = r - top
            shift = _compute_shift(d, N)
            for c in range(w):
                src_c = c - shift
                if 0 <= src_c < w:
                    output[r][c] = raw[r][src_c]

    return output
