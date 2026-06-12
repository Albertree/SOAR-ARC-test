"""
make_grid — one of the two (and only two) hand-coded transformation primitives.

    make_grid(height, width, color) -> grid

Produces a fresh `height × width` canvas filled with `color`. This is the
"create a blank background" half of the frozen transformation vocabulary; every
richer construction (paint a shape onto a background, etc.) is a *composition*
of this with `coloring`, discovered at runtime — never a third primitive
(CLAUDE.md §6.1, INVARIANTS F3).
"""


def make_grid(height: int, width: int, color: int) -> list:
    """Return a fresh height×width grid (list of lists) filled with `color`."""
    return [[color for _ in range(width)] for _ in range(height)]
