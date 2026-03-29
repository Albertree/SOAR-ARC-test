"""quadrant_shape_swap — grid divided by 0-separators into cell pairs; horizontal pairs swap shapes, recolored with source bg."""

RULE_TYPE = "quadrant_shape_swap"
CATEGORY = "structure"


def _find_separators(grid):
    """Find separator rows and columns (all zeros)."""
    h = len(grid)
    w = len(grid[0]) if grid else 0

    sep_rows = set()
    for r in range(h):
        if all(grid[r][c] == 0 for c in range(w)):
            sep_rows.add(r)

    sep_cols = set()
    for c in range(w):
        if all(grid[r][c] == 0 for r in range(h)):
            sep_cols.add(c)

    return sep_rows, sep_cols


def _get_cell_ranges(sep_set, total):
    """Get ranges of non-separator regions."""
    ranges = []
    start = None
    for i in range(total):
        if i in sep_set:
            if start is not None:
                ranges.append((start, i - 1))
                start = None
        else:
            if start is None:
                start = i
    if start is not None:
        ranges.append((start, total - 1))
    return ranges


def _extract_shape(grid, r1, r2, c1, c2):
    """Extract shape info from a cell region. Returns (bg_color, shape_positions_relative)."""
    counts = {}
    for r in range(r1, r2 + 1):
        for c in range(c1, c2 + 1):
            v = grid[r][c]
            counts[v] = counts.get(v, 0) + 1

    if not counts:
        return None, []

    bg = max(counts, key=counts.get)

    positions = []
    for r in range(r1, r2 + 1):
        for c in range(c1, c2 + 1):
            if grid[r][c] != bg:
                positions.append((r - r1, c - c1))

    return bg, positions


def try_rule(patterns, task):
    """Detect: 0-separator grid with horizontal cell pairs that swap shapes."""
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

        sep_rows, sep_cols = _find_separators(inp)
        if not sep_cols:
            return None

        row_ranges = _get_cell_ranges(sep_rows, h)
        col_ranges = _get_cell_ranges(sep_cols, w)

        if len(col_ranges) != 2:
            return None

        if len(row_ranges) < 2:
            return None

        c1_l, c2_l = col_ranges[0]
        c1_r, c2_r = col_ranges[1]

        if (c2_l - c1_l) != (c2_r - c1_r):
            return None

        for rr in row_ranges:
            r1, r2 = rr

            bg_l, pos_l = _extract_shape(inp, r1, r2, c1_l, c2_l)
            bg_r, pos_r = _extract_shape(inp, r1, r2, c1_r, c2_r)

            if bg_l is None or bg_r is None:
                return None

            # Build expected output cells
            cell_h = r2 - r1 + 1
            cell_w = c2_l - c1_l + 1

            # Left cell expected
            exp_l = [[bg_l] * cell_w for _ in range(cell_h)]
            # Right cell expected
            exp_r = [[bg_r] * cell_w for _ in range(cell_h)]

            if bg_l != bg_r:
                for dr, dc in pos_r:
                    exp_l[dr][dc] = bg_r
                for dr, dc in pos_l:
                    exp_r[dr][dc] = bg_l

            # Verify left cell
            for dr in range(cell_h):
                for dc in range(cell_w):
                    if out[r1 + dr][c1_l + dc] != exp_l[dr][dc]:
                        return None
            # Verify right cell
            for dr in range(cell_h):
                for dc in range(cell_w):
                    if out[r1 + dr][c1_r + dc] != exp_r[dr][dc]:
                        return None

    return {
        "type": RULE_TYPE,
        "confidence": 1.0,
    }


def apply_rule(rule, input_grid):
    """Swap shapes between horizontal cell pairs, recoloring with source bg."""
    raw = input_grid.raw
    h = len(raw)
    w = len(raw[0]) if raw else 0

    sep_rows, sep_cols = _find_separators(raw)
    if not sep_cols:
        return None

    row_ranges = _get_cell_ranges(sep_rows, h)
    col_ranges = _get_cell_ranges(sep_cols, w)

    if len(col_ranges) != 2:
        return None

    output = [row[:] for row in raw]

    c1_l, c2_l = col_ranges[0]
    c1_r, c2_r = col_ranges[1]

    for rr in row_ranges:
        r1, r2 = rr

        bg_l, pos_l = _extract_shape(raw, r1, r2, c1_l, c2_l)
        bg_r, pos_r = _extract_shape(raw, r1, r2, c1_r, c2_r)

        if bg_l is None or bg_r is None:
            return None

        # Clear both cells to their bg
        for r in range(r1, r2 + 1):
            for c in range(c1_l, c2_l + 1):
                output[r][c] = bg_l
            for c in range(c1_r, c2_r + 1):
                output[r][c] = bg_r

        if bg_l != bg_r:
            # Place right's shape in left, colored as bg_r
            for dr, dc in pos_r:
                output[r1 + dr][c1_l + dc] = bg_r
            # Place left's shape in right, colored as bg_l
            for dr, dc in pos_l:
                output[r1 + dr][c1_r + dc] = bg_l

    return output
