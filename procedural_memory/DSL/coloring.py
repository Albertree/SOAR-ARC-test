"""coloring — paint selected cells with a color.

Signature::

    coloring(grid, selection, color) -> new_grid

* ``grid``      — list of lists of ints, the working canvas (not mutated).
* ``selection`` — either a single ``(row, col)`` coord, or a list of such
                  coords. Empty list is allowed and yields an identity copy.
* ``color``     — int in ``0..9`` (ARC palette) or ``13`` (transparent /
                  no-paint sentinel — composition layers interpret 13 as
                  "leave underlying value visible" when stacking).

Pure: returns a fresh nested list; does not mutate ``grid``. Out-of-bounds
coords raise ``ValueError`` — anti-unification is responsible for producing
in-bounds selections at this primitive layer.

This is one of the **two** hand-coded DSL primitives ARBOR is permitted to
ship with. See ``CLAUDE.md §6.1`` and ``docs/INVARIANTS.md §1 F3``.
"""

from __future__ import annotations

from procedural_memory.DSL.apply import VALID_COLORS as _VALID_COLORS, register


def _is_coord(x) -> bool:
    return (
        isinstance(x, (tuple, list))
        and len(x) == 2
        and isinstance(x[0], int) and not isinstance(x[0], bool)
        and isinstance(x[1], int) and not isinstance(x[1], bool)
    )


def _normalize_selection(selection):
    """Coerce ``selection`` into a list of ``(r, c)`` tuples.

    Accepts:
      - a single coord (tuple or list of length 2 of ints)
      - an iterable of such coords (list, tuple)
      - ``None`` or empty iterable → empty list (identity paint).
    """
    if selection is None:
        return []
    if _is_coord(selection):
        return [(int(selection[0]), int(selection[1]))]
    if not isinstance(selection, (list, tuple)):
        raise ValueError(
            f"coloring: selection must be a coord or list of coords; got {type(selection).__name__}"
        )
    coords = []
    for s in selection:
        if not _is_coord(s):
            raise ValueError(f"coloring: invalid coord in selection: {s!r}")
        coords.append((int(s[0]), int(s[1])))
    return coords


@register("coloring")
def coloring(grid, selection, color):
    if not isinstance(color, int) or isinstance(color, bool) or color not in _VALID_COLORS:
        raise ValueError(
            f"coloring: color must be int in 0..9 or 13 (transparent); got {color!r}"
        )
    if not isinstance(grid, list) or not all(isinstance(row, list) for row in grid):
        raise ValueError("coloring: grid must be a list of lists")

    height = len(grid)
    width = len(grid[0]) if height > 0 else 0

    coords = _normalize_selection(selection)
    out = [list(row) for row in grid]
    for (r, c) in coords:
        if not (0 <= r < height and 0 <= c < width):
            raise ValueError(
                f"coloring: coord ({r},{c}) out of bounds for {height}x{width} grid"
            )
        out[r][c] = color
    return out
