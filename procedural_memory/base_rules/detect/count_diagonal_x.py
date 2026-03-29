"""count_diagonal_x — count two scattered colors, draw X-diagonal pattern in bottom-left rectangle."""

RULE_TYPE = "count_diagonal_x"
CATEGORY = "detect"


def _get_bg_and_colors(grid):
    """Return (bg_color, {color: count}) for non-bg colors."""
    h = len(grid)
    w = len(grid[0]) if grid else 0
    counts = {}
    for r in range(h):
        for c in range(w):
            counts[grid[r][c]] = counts.get(grid[r][c], 0) + 1
    bg = max(counts, key=counts.get)
    non_bg = {c: n for c, n in counts.items() if c != bg}
    return bg, non_bg


def _are_all_isolated(grid, color, bg):
    """Check that all cells of 'color' are isolated (no same-color neighbor)."""
    h = len(grid)
    w = len(grid[0]) if grid else 0
    for r in range(h):
        for c in range(w):
            if grid[r][c] != color:
                continue
            for dr, dc in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                nr, nc = r + dr, c + dc
                if 0 <= nr < h and 0 <= nc < w and grid[nr][nc] == color:
                    return False
    return True


def try_rule(patterns, task):
    """Detect: two non-bg scattered colors whose counts become W and H of a diagonal-X rectangle."""
    pairs = task.example_pairs
    if not pairs:
        return None

    bg_color = None

    for pair in pairs:
        inp = pair.input_grid.raw
        out = pair.output_grid.raw

        bg, non_bg = _get_bg_and_colors(inp)
        if len(non_bg) != 2:
            return None

        if bg_color is None:
            bg_color = bg
        elif bg_color != bg:
            return None

        colors = sorted(non_bg.keys(), key=lambda c: non_bg[c])
        h_count = non_bg[colors[0]]  # smaller count = height
        w_count = non_bg[colors[1]]  # larger count = width

        # Both colors should be isolated single pixels
        for c in colors:
            if not _are_all_isolated(inp, c, bg):
                return None

        # Verify output structure: 16x16, bottom-left H*W filled with 2 and 4
        oh = len(out)
        ow = len(out[0]) if out else 0
        if oh != 16 or ow != 16:
            return None

        # Check output colors are only bg, 2, and 4
        out_colors = set()
        for row in out:
            out_colors.update(row)
        if not out_colors <= {bg, 2, 4}:
            return None

        # Verify the diagonal pattern in bottom-left rectangle
        start_row = oh - h_count
        for pr in range(h_count):
            out_r = start_row + pr
            t = h_count - 1 - pr  # distance from bottom
            left_col = t
            right_col = (w_count - 1) - t
            for c in range(w_count):
                expected = 4 if (c == left_col or c == right_col) else 2
                if out[out_r][c] != expected:
                    return None
            # Rest of row should be background
            for c in range(w_count, ow):
                if out[out_r][c] != bg:
                    return None

        # Top rows should be all background
        for r in range(start_row):
            for c in range(ow):
                if out[r][c] != bg:
                    return None

    return {
        "type": RULE_TYPE,
        "bg": bg_color,
        "confidence": 1.0,
    }


def apply_rule(rule, input_grid):
    """Count the two non-bg colors, draw X-diagonal pattern."""
    raw = input_grid.raw
    bg = rule["bg"]

    _, non_bg = _get_bg_and_colors(raw)
    if len(non_bg) != 2:
        return None

    counts = sorted(non_bg.values())
    h_count = counts[0]  # smaller = height
    w_count = counts[1]  # larger = width

    # Create 16x16 output filled with background
    out_size = 16
    output = [[bg] * out_size for _ in range(out_size)]

    # Fill bottom-left rectangle with 2
    start_row = out_size - h_count
    for r in range(h_count):
        for c in range(w_count):
            output[start_row + r][c] = 2

    # Draw X-diagonals with 4
    for pr in range(h_count):
        out_r = start_row + pr
        t = h_count - 1 - pr  # distance from bottom
        left_col = t
        right_col = (w_count - 1) - t
        output[out_r][left_col] = 4
        output[out_r][right_col] = 4

    return output
