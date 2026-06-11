"""
DSL primitive: coloring.

The second (and final) hand-coded transformation primitive (CLAUDE.md §6.1,
INVARIANTS.md F3). Paints a `selection` of cells of an existing grid with a
single `color`. Together with `make_grid` it spans the whole transformation
space: anything else (move, copy, recolor, flip, …) is a *composition* of these
two that ARBOR must discover at runtime, never a new hand-coded function.

    coloring(grid, selection, color) -> grid   (new list[list[int]])

`selection` is a single `(row, col)` coordinate or an iterable of them.
`color` is an ARC colour 0-9, or `13` (transparent): a transparent paint is a
no-op overlay — the underlying cell value is left unchanged. (The alternative
"erase to background" reading of 13 is an open question, OPEN-Q; slice 1's
make_grid+coloring reconstruction path never uses 13, so the conservative
non-destructive reading is chosen here and flagged rather than invented.)

Pure: the input grid is never mutated; a deep copy is returned. Coordinates
outside the grid are ignored (out-of-bounds paint is a no-op, not an error),
so a composition can name a superset of cells safely.
"""

TRANSPARENT = 13


def _as_coords(selection):
    """Normalise `selection` to a list of `(row, col)` int pairs."""
    if selection is None:
        return []
    # A single coordinate like (r, c).
    if (
        isinstance(selection, (tuple, list))
        and len(selection) == 2
        and all(isinstance(v, int) for v in selection)
    ):
        return [(int(selection[0]), int(selection[1]))]
    # Otherwise an iterable of coordinates.
    coords = []
    for item in selection:
        if not (isinstance(item, (tuple, list)) and len(item) == 2):
            raise TypeError(f"coloring selection element must be (row, col), got {item!r}")
        coords.append((int(item[0]), int(item[1])))
    return coords


def coloring(grid, selection, color):
    """Return a copy of `grid` with `selection` painted `color`.

    Transparent (`color == 13`) leaves selected cells unchanged. Coordinates
    outside the grid bounds are silently skipped.
    """
    out = [list(row) for row in grid]
    height = len(out)
    width = len(out[0]) if out else 0

    if color == TRANSPARENT:
        return out  # transparent overlay: nothing is repainted

    for (r, c) in _as_coords(selection):
        if 0 <= r < height and 0 <= c < width:
            out[r][c] = color
    return out
