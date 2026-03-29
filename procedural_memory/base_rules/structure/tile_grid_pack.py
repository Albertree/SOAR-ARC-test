"""tile_grid_pack — 30x30 grid with 3x3 hollow tiles compressed by gravity packing."""

RULE_TYPE = "tile_grid_pack"
CATEGORY = "structure"


def _find_border(grid):
    """Find the row or column of all 1s. Returns ('row'/'col', position)."""
    h, w = len(grid), len(grid[0])
    for r in range(h):
        if all(grid[r][c] == 1 for c in range(w)):
            return ('row', r)
    for c in range(w):
        if all(grid[r][c] == 1 for r in range(h)):
            return ('col', c)
    return None


def _find_tiles(grid):
    """Find all 3x3 tiles with hollow center. Returns list of (row, col, color)."""
    h, w = len(grid), len(grid[0])
    tiles = []
    for r in range(h - 2):
        for c in range(w - 2):
            if grid[r + 1][c + 1] != 0:
                continue
            border_cells = []
            for dr in range(3):
                for dc in range(3):
                    if dr == 1 and dc == 1:
                        continue
                    border_cells.append(grid[r + dr][c + dc])
            non_zero = [v for v in border_cells if v not in (0, 1)]
            if len(non_zero) != 8:
                continue
            if len(set(non_zero)) != 1:
                continue
            tiles.append((r, c, non_zero[0]))
    return tiles


def _build_tile_grid(tiles):
    """Map tiles to a 7x7 grid. Returns 7x7 list and tile offsets."""
    if not tiles:
        return None
    rows = sorted(set(r for r, c, _ in tiles))
    cols = sorted(set(c for r, c, _ in tiles))

    # Determine step (should be 4)
    if len(rows) < 2 and len(cols) < 2:
        return None

    # Find row/col offset and step
    row_offset = min(rows)
    col_offset = min(cols)

    # Build position lookup
    tile_map = {}
    for r, c, color in tiles:
        ri = round((r - row_offset) / 4)
        ci = round((c - col_offset) / 4)
        if 0 <= ri < 7 and 0 <= ci < 7:
            tile_map[(ri, ci)] = color

    grid = [[0] * 7 for _ in range(7)]
    for (ri, ci), color in tile_map.items():
        grid[ri][ci] = color
    return grid


def _pack_line(values, toward_end):
    """Pack non-zero values to one end, maintaining relative order."""
    non_zeros = [v for v in values if v != 0]
    zeros = [0] * (len(values) - len(non_zeros))
    if toward_end:
        return zeros + non_zeros
    else:
        return non_zeros + zeros


def _process(grid):
    """Full processing: find border, extract tiles, pack."""
    h, w = len(grid), len(grid[0])
    if h != 30 or w != 30:
        return None

    border = _find_border(grid)
    if border is None:
        return None

    tiles = _find_tiles(grid)
    if not tiles:
        return None

    tile_grid = _build_tile_grid(tiles)
    if tile_grid is None:
        return None

    border_type, border_pos = border

    # Separator is perpendicular to border, at position 3
    if border_type == 'row':
        # Separator is a column (col 3 in tile grid)
        # Remove col 3, process each row
        # Determine push direction: border at top(0) → push right; bottom(29) → push left
        toward_end = (border_pos == 0)

        out_h, out_w = 7, 6
        output = [[0] * out_w for _ in range(out_h)]
        for r in range(7):
            line = []
            for c in range(7):
                if c == 3:
                    continue
                line.append(tile_grid[r][c])
            packed = _pack_line(line, toward_end)
            output[r] = packed
    else:
        # Separator is a row (row 3 in tile grid)
        # Remove row 3, process each column
        # border at left(0) → push up (toward start); right(29) → push down (toward end)
        toward_end = (border_pos == 29)

        out_h, out_w = 6, 7
        output = [[0] * out_w for _ in range(out_h)]
        for c in range(7):
            line = []
            for r in range(7):
                if r == 3:
                    continue
                line.append(tile_grid[r][c])
            packed = _pack_line(line, toward_end)
            for i, val in enumerate(packed):
                output[i][c] = val

    return output


def try_rule(patterns, task):
    """Detect: 30x30 grid with 1-border and hollow tiles → packed summary."""
    pairs = task.example_pairs
    if not pairs:
        return None

    for pair in pairs:
        inp = pair.input_grid.raw
        out = pair.output_grid.raw
        h, w = len(inp), len(inp[0])

        if h != 30 or w != 30:
            return None

        result = _process(inp)
        if result is None:
            return None

        if len(result) != len(out) or len(result[0]) != len(out[0]):
            return None
        for r in range(len(out)):
            if result[r] != out[r]:
                return None

    return {"type": RULE_TYPE, "confidence": 1.0}


def apply_rule(rule, input_grid):
    """Pack the tile grid."""
    return _process(input_grid.raw)
