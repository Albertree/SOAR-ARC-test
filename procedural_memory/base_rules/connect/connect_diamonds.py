"""connect_diamonds — connect aligned diamond shapes with lines."""

RULE_TYPE = "connect_diamonds"
CATEGORY = "connect"


def _find_diamonds(grid, color):
    """Find diamond/cross shapes of given color. Returns list of (center_r, center_c)."""
    h = len(grid)
    w = len(grid[0]) if grid else 0
    diamonds = []
    for r in range(1, h - 1):
        for c in range(1, w - 1):
            if (grid[r - 1][c] == color and
                grid[r][c - 1] == color and
                grid[r][c + 1] == color and
                grid[r + 1][c] == color and
                grid[r][c] != color):
                diamonds.append((r, c))
    return diamonds


def _find_diamond_color(grid):
    """Find the color used for diamond shapes (non-bg, forms crosses)."""
    h = len(grid)
    w = len(grid[0]) if grid else 0
    counts = {}
    for r in range(h):
        for c in range(w):
            counts[grid[r][c]] = counts.get(grid[r][c], 0) + 1
    bg = max(counts, key=counts.get)
    for color in counts:
        if color == bg:
            continue
        diamonds = _find_diamonds(grid, color)
        if len(diamonds) >= 2:
            return color, bg
    return None, None


def _get_consecutive_pairs(diamonds):
    """Get pairs of consecutive diamonds along same row or column."""
    pairs = []
    # Group by row
    by_row = {}
    for r, c in diamonds:
        by_row.setdefault(r, []).append(c)
    for row, cols in by_row.items():
        cols.sort()
        for i in range(len(cols) - 1):
            pairs.append(((row, cols[i]), (row, cols[i + 1])))
    # Group by column
    by_col = {}
    for r, c in diamonds:
        by_col.setdefault(c, []).append(r)
    for col, rows in by_col.items():
        rows.sort()
        for i in range(len(rows) - 1):
            pairs.append(((rows[i], col), (rows[i + 1], col)))
    return pairs


def _draw_connections(grid, diamonds, cc):
    """Draw connector lines between consecutive aligned diamonds."""
    result = [row[:] for row in grid]
    for (r1, c1), (r2, c2) in _get_consecutive_pairs(diamonds):
        if r1 == r2:
            for c in range(c1 + 2, c2 - 1):
                result[r1][c] = cc
        elif c1 == c2:
            for r in range(r1 + 2, r2 - 1):
                result[r][c1] = cc
    return result


def try_rule(patterns, task):
    """Detect: diamond shapes connected by lines between aligned tips."""
    pairs = task.example_pairs
    if not pairs:
        return None

    if not patterns.get("grid_size_preserved"):
        return None

    connect_color = None

    for pair in pairs:
        inp = pair.input_grid.raw
        out = pair.output_grid.raw
        h = len(inp)
        w = len(inp[0]) if inp else 0

        diamond_color, bg = _find_diamond_color(inp)
        if diamond_color is None:
            return None

        diamonds = _find_diamonds(inp, diamond_color)
        if len(diamonds) < 2:
            return None

        inp_colors = set()
        out_colors = set()
        for r in range(h):
            for c in range(w):
                inp_colors.add(inp[r][c])
                out_colors.add(out[r][c])
        new_colors = out_colors - inp_colors
        if len(new_colors) != 1:
            return None
        cc = new_colors.pop()

        if connect_color is None:
            connect_color = cc
        elif connect_color != cc:
            return None

        expected = _draw_connections(inp, diamonds, cc)
        if expected != out:
            return None

    return {
        "type": RULE_TYPE,
        "diamond_color": diamond_color,
        "connect_color": connect_color,
        "confidence": 1.0,
    }


def apply_rule(rule, input_grid):
    """Connect aligned diamond shapes with lines."""
    raw = input_grid.raw
    dc = rule["diamond_color"]
    cc = rule["connect_color"]

    diamonds = _find_diamonds(raw, dc)
    if len(diamonds) < 2:
        return None

    return _draw_connections(raw, diamonds, cc)
