"""
render — express a concrete target grid as a `make_grid` + `coloring` composition.

This is the operational meaning of BACKLOG_LOOP §2.5-1 for R0: the COMM-copy
*action* ("the output is this fixed grid") is not a new primitive — it is the
two frozen primitives composed. We build a background canvas with `make_grid`,
then paint each non-background color with one `coloring` call. The result is
provably equal to the target, demonstrating that even "emit a constant grid"
bottoms out in the two-primitive vocabulary rather than a stored literal op.

The function is value-agnostic: it works for any target grid (easy000a's
`2`-at-(5,5) and easy000b's different fixed output alike), which is exactly the
property R0 requires (one module, many constant outputs).
"""

from collections import Counter

from procedural_memory.DSL.apply import apply_DSL


def _background_color(grid: list) -> int:
    """Pick the most frequent color as the canvas background (ties → smallest)."""
    counts = Counter(cell for row in grid for cell in row)
    if not counts:
        return 0
    most = max(counts.values())
    return min(c for c, n in counts.items() if n == most)


def render_grid_via_primitives(grid: list) -> list:
    """Rebuild `grid` from `make_grid` + per-color `coloring` calls.

    Returns a fresh grid equal to `grid`. Raises nothing for an empty grid
    (returns an empty canvas).
    """
    height = len(grid)
    width = len(grid[0]) if height else 0
    bg = _background_color(grid)

    canvas = apply_DSL("make_grid", height=height, width=width, color=bg)

    # Group the non-background cells by color, one coloring() call per color.
    by_color: dict = {}
    for r in range(height):
        for c in range(width):
            color = grid[r][c]
            if color != bg:
                by_color.setdefault(color, []).append((r, c))

    for color, cells in by_color.items():
        canvas = apply_DSL("coloring", canvas, selection=cells, color=color)

    return canvas


def render_solid_square(side: int, color: int) -> list:
    """A ``side × side`` canvas filled with ``color`` — the §2.1 "grid size is a
    function of an object's property" output expressed in the frozen primitives.

    A uniform fill bottoms out in a *single* `make_grid` call: there is no
    non-background cell, so the `coloring` half of the make_grid ∘ coloring
    composition is a no-op and is elided. The whole content of the rule lives in
    the *argument* — `side` is `size_of(unique_object(in))` and `color` is its
    colour, both read off the test input (P5) — not in any new transformation
    (§2.5-1, F3). Returns an empty canvas when ``side < 1``.
    """
    if side < 1:
        return apply_DSL("make_grid", height=0, width=0, color=color)
    return apply_DSL("make_grid", height=side, width=side, color=color)


def render_object_at(height: int, width: int, bg: int,
                     pixels: list, target: tuple) -> list:
    """Place an object (its `pixels` = list of (row, col, color)) on a fresh
    `bg` canvas with the object's top-left anchor moved to `target`.

    This is "move the object to a constant position" expressed in the two frozen
    primitives: `make_grid` lays the background, then one `coloring` call per
    color paints the translated cells (BACKLOG_LOOP §2.5-1 — a move is not a new
    primitive, it is `make_grid` ∘ `coloring` with a translated coordinate
    expression). The variable origin is G0 only (P5): `pixels`/`bg` come from the
    test input, `target` is the cross-pair COMM of the example outputs.
    """
    if not pixels:
        return apply_DSL("make_grid", height=height, width=width, color=bg)
    r0 = min(r for r, _c, _v in pixels)
    c0 = min(c for _r, c, _v in pixels)
    tr, tc = target

    canvas = apply_DSL("make_grid", height=height, width=width, color=bg)
    by_color: dict = {}
    for r, c, color in pixels:
        by_color.setdefault(color, []).append((r - r0 + tr, c - c0 + tc))
    for color, cells in by_color.items():
        canvas = apply_DSL("coloring", canvas, selection=cells, color=color)
    return canvas
