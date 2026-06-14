"""
coloring — one of the two frozen transformation primitives (CLAUDE.md §6, F3).

Paints a selection of cells a colour. Every "place / move / recolor an object"
transformation is expressed as a sequence of `coloring` calls whose *arguments*
(which cells, which colour) are produced by the growing selection/argument
vocabulary (`agent/`), not by new transformation primitives.
"""

from procedural_memory.DSL.apply import register

#: sentinel colour meaning "leave the cell untouched" (CLAUDE.md §6.1).
TRANSPARENT = 13


@register("coloring")
def coloring(grid, selection, color):
    """Paint `selection` with `color` on a copy of `grid`.

    `selection` is either a single `(row, col)` coordinate or an iterable of
    them. `color` is 0-9, or 13 (TRANSPARENT) for a no-op paint. Out-of-bounds
    coordinates are ignored. The input grid is not mutated.
    """
    out = [row[:] for row in grid]
    if color == TRANSPARENT:
        return out

    # Distinguish a single coord (r, c) from an iterable of coords [(r, c), ...].
    if (
        isinstance(selection, (tuple, list))
        and len(selection) == 2
        and all(isinstance(v, int) for v in selection)
    ):
        coords = [tuple(selection)]
    else:
        coords = selection

    height = len(out)
    width = len(out[0]) if height else 0
    for rc in coords:
        r, c = rc
        if 0 <= r < height and 0 <= c < width:
            out[r][c] = color
    return out
