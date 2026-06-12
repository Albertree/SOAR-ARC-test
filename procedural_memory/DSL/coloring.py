"""
coloring — one of the two (and only two) hand-coded transformation primitives.

    coloring(grid, selection, color) -> grid

Paints `selection` (a single (row, col) coord, or an iterable of coords) with
`color` and returns a new grid (the input is not mutated). Together with
`make_grid` this is the entire frozen transformation vocabulary: move, copy,
recolor, flip, … are all *compositions* of these two with argument expressions,
discovered at runtime (CLAUDE.md §6.1, INVARIANTS F3, BACKLOG_LOOP §2.5).
"""


def coloring(grid: list, selection, color: int) -> list:
    """Return a copy of `grid` with `selection` painted `color`.

    `selection` is either a single (row, col) pair or an iterable of them. Cells
    outside the grid are ignored so callers need not bounds-check first.
    """
    out = [row[:] for row in grid]
    if not selection:
        return out

    # Single (r, c) coord vs. an iterable of coords.
    first = selection[0]
    cells = selection if isinstance(first, (tuple, list)) else [selection]

    height = len(out)
    width = len(out[0]) if out else 0
    for cell in cells:
        r, c = cell
        if 0 <= r < height and 0 <= c < width:
            out[r][c] = color
    return out
