"""
make_grid — frozen transformation primitive #1 (CLAUDE.md §6.1, INVARIANTS F3).

Produce a fresh `height × width` grid filled with a single `color`. This is the
canvas-creation half of the two-primitive transformation vocabulary; every
"the output is a brand-new grid" transformation begins here and is then painted
by `coloring`.
"""


def make_grid(height: int, width: int, color: int) -> list:
    """Return a fresh height×width grid (list of rows) filled with `color`.

    Rows are independent lists so a subsequent `coloring` mutation of one cell
    never aliases another row.
    """
    h = int(height)
    w = int(width)
    if h < 0 or w < 0:
        raise ValueError(f"make_grid: negative dimension ({height}x{width})")
    return [[color for _ in range(w)] for _ in range(h)]
