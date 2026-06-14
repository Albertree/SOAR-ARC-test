"""
make_grid — one of the two frozen transformation primitives (CLAUDE.md §6, F3).

Produces a fresh canvas. This is the *base* of every output-construction
program: a discovered transformation that resizes or rebuilds a grid starts from
`make_grid` and then layers `coloring` calls on top.
"""

from procedural_memory.DSL.apply import register


@register("make_grid")
def make_grid(height, width, color=0):
    """Return a fresh `height` × `width` grid filled with `color` (0-9)."""
    h = int(height)
    w = int(width)
    return [[color for _ in range(w)] for _ in range(h)]
