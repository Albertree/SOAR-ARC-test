"""
coloring — frozen transformation primitive #2 (CLAUDE.md §6.1, INVARIANTS F3).

Paint `selection` (a single (row, col) coordinate or an iterable of them) with
`color` on a copy of `grid`. `color == 13` is the transparent/erase sentinel
(CLAUDE.md §6.1): such cells are left untouched. This is the painting half of
the two-primitive transformation vocabulary; composing `make_grid` then one or
more `coloring` calls is how *every* other transformation is expressed.
"""

TRANSPARENT = 13


def _as_cells(selection):
    """Normalise `selection` to a list of (row, col) tuples.

    Accepts a single coordinate `(r, c)` or an iterable of coordinates. An empty
    / falsy selection paints nothing.
    """
    if not selection:
        return []
    # A bare coordinate like (2, 3) or [2, 3] — two ints, not a list of coords.
    if (
        len(selection) == 2
        and all(isinstance(v, int) for v in selection)
    ):
        return [tuple(selection)]
    return [tuple(cell) for cell in selection]


def coloring(grid: list, selection, color: int) -> list:
    """Return a copy of `grid` with every cell in `selection` set to `color`.

    Out-of-bounds coordinates are ignored (a no-op for that cell) rather than
    raising, so a selection expression that overshoots a smaller canvas degrades
    gracefully. `color == 13` (transparent) leaves selected cells unchanged.
    """
    out = [row[:] for row in grid]
    if color == TRANSPARENT:
        return out
    h = len(out)
    w = len(out[0]) if out else 0
    for r, c in _as_cells(selection):
        if 0 <= r < h and 0 <= c < w:
            out[r][c] = color
    return out
