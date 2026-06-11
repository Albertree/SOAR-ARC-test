"""
DSL primitive: make_grid.

One of the **two** hand-coded transformation primitives ARBOR is ever permitted
(CLAUDE.md §6.1, INVARIANTS.md F3). Produces a fresh `height x width` canvas
filled with a single colour. Every "produce a new grid" transformation
(constant output, scaling, tiling, framing, …) is a *composition* that starts
here — the canvas — and is finished with `coloring`. The set is frozen at two:
no third primitive may ever be hand-written; richer transforms must be
*discovered* by anti-unification as compositions of these two.

    make_grid(height, width, color) -> grid   (list[list[int]])

Pure and deterministic: same args -> identical fresh grid (no shared rows).
"""


def make_grid(height, width, color):
    """Return a fresh `height x width` grid with every cell set to `color`.

    `height`/`width` must be non-negative ints; `color` is an ARC colour
    (0-9, or 13 for transparent — see `coloring`). Each row is a distinct
    list so later `coloring` of one cell never aliases another row.
    """
    if not isinstance(height, int) or not isinstance(width, int):
        raise TypeError(f"make_grid dimensions must be ints, got {height!r}x{width!r}")
    if height < 0 or width < 0:
        raise ValueError(f"make_grid dimensions must be >= 0, got {height}x{width}")
    return [[color for _ in range(width)] for _ in range(height)]
