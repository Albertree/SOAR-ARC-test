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


def render_solid_rect(height: int, width: int, color: int) -> list:
    """A ``height × width`` canvas filled with ``color`` — the non-square sibling
    of :func:`render_solid_square`.

    Same frozen-primitive bottom-out: a uniform fill is a *single* `make_grid`
    call (the `coloring` half elided, no non-background cell). The whole content
    lives in the *argument* — here ``(height, width)`` is `bbox_extent(unique_object
    (in))`, an extent *pair* read off the test object (P5) — not in any new
    transformation (§2.5-1, F3). Returns an empty canvas when either dimension < 1.
    """
    if height < 1 or width < 1:
        return apply_DSL("make_grid", height=0, width=0, color=color)
    return apply_DSL("make_grid", height=height, width=width, color=color)


def render_recolor(grid: list, color_map: dict) -> list:
    """Recolour `grid` by a 1:1 colour map, expressed in the frozen `coloring`
    primitive: one `coloring` call per remapped source colour repaints exactly
    that colour's cells to its target. Geometry is preserved (no `make_grid`
    resize); colours absent from the map keep their value (the implicit identity
    default). This is the recolor family's transformation bottoming out in
    `coloring` (BACKLOG_LOOP §2.5-1, F3) — the whole content lives in the
    *argument* (`color_map`, read off the example DIFF), not in any new primitive.

    Source cells are selected from the *original* grid each iteration (never the
    progressively-painted copy), so a map like ``{1: 2, 2: 3}`` cannot chain
    (original 1s do not become 3s).
    """
    height = len(grid)
    width = len(grid[0]) if height else 0
    out = [row[:] for row in grid]
    for src, dst in color_map.items():
        if src == dst:
            continue
        cells = [
            (r, c)
            for r in range(height)
            for c in range(width)
            if grid[r][c] == src
        ]
        if cells:
            out = apply_DSL("coloring", out, selection=cells, color=dst)
    return out


def _connected_components(cells: list) -> list:
    """4-connected components of a list of ``(row, col)`` cells."""
    cell_set = set(cells)
    visited = set()
    comps = []
    for start in cells:
        if start in visited:
            continue
        comp = []
        queue = [start]
        while queue:
            p = queue.pop()
            if p in visited or p not in cell_set:
                continue
            visited.add(p)
            comp.append(p)
            r, c = p
            for nb in ((r - 1, c), (r + 1, c), (r, c - 1), (r, c + 1)):
                if nb in cell_set and nb not in visited:
                    queue.append(nb)
        comps.append(comp)
    return comps


def render_recolor_rank(grid: list, sort_key: str, start_color: int,
                        source_colors: list) -> list:
    """Recolour `grid` by *rank*: the source-coloured cells form connected groups
    which, ordered by ``sort_key`` (`top_row` / `top_col`), are painted the
    contiguous sequence ``start_color, start_color+1, …`` — one `coloring` call per
    group.

    This is the recolor-rank family's transformation bottoming out in the frozen
    `coloring` primitive (BACKLOG_LOOP §2.5-1, F3): geometry is preserved (no
    `make_grid` resize), and the whole content lives in the *argument* — a
    `rank-by(position)` selector plus the start colour, read off the example DIFF
    (§2.5-2b), not in any new primitive. Reproduces the behaviour of the
    now-removed legacy ``_apply_recolor_sequential`` painting (groups of
    *source-coloured* cells, re-derived from the input) so the migration that
    deleted that applier preserved behaviour exactly.
    """
    height = len(grid)
    width = len(grid[0]) if height else 0
    srcs = set(source_colors)
    out = [row[:] for row in grid]
    target_cells = [
        (r, c)
        for r in range(height)
        for c in range(width)
        if grid[r][c] in srcs
    ]
    if not target_cells:
        return out

    def _key(group):
        if sort_key == "top_row":
            return min(r for r, _c in group)
        if sort_key == "top_col":
            return min(c for _r, c in group)
        return 0

    for idx, group in enumerate(sorted(_connected_components(target_cells), key=_key)):
        out = apply_DSL("coloring", out, selection=list(group), color=start_color + idx)
    return out


def render_object_recolor(grid: list, cells: list, new_color: int) -> list:
    """Repaint exactly ``cells`` (a *selected* object's cells) to ``new_color``,
    leaving the rest of ``grid`` untouched.

    This is the object-selective recolor's transformation bottoming out in the
    frozen `coloring` primitive (BACKLOG_LOOP §2.5-1, F3): a single `coloring`
    call paints the chosen object's cells; geometry is preserved (no `make_grid`
    resize), every other object kept. The whole content lives in the *argument* —
    *which* cells (the object a learned selector picks) and *what* colour (the
    cross-pair COMM on the recolored object's output colour) — not in any new
    primitive. The converse of :func:`render_recolor`: that repaints by a global
    colour map (every cell of a colour); this repaints exactly one object's cells,
    so two same-coloured objects can diverge (only the selected one changes).
    """
    out = [row[:] for row in grid]
    if cells:
        out = apply_DSL("coloring", out,
                        selection=[list(c) for c in cells], color=new_color)
    return out


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
