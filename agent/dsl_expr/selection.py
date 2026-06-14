"""
selection — seed object / selection vocabulary for R1 (BACKLOG_LOOP.md R1).

The smallest set of *argument expressions* needed to talk about "the object in a
grid": detect objects, pick the unique one, read its position / colour / extent.
This is the util+property seed set the ladder calls for (`objects_of`, `unique`,
`position-of`, `color-of`). It is consumed by the object-level condition matchers
(`agent/conditions/object_*`) and by the prediction renderer, which expresses an
object move as `make_grid` + `coloring` whose *arguments* come from here.

Background convention (test32 `background_convention_fix`): colour **0 is the
canvas / background**, canonically — not "the most frequent colour". Keying on
most-frequent flips foreground/background on grids where 0 is sparse, so the
canonical canvas colour is fixed at 0 here. An object is a 4-connected component
of non-background cells (colours may differ within it).
"""


def background_of(grid) -> int:
    """The canonical canvas colour. Fixed at 0 (the ARC empty cell)."""
    return 0


def cells_of(grid, bg: int = 0):
    """All `(row, col, color)` triples whose colour is not the background."""
    out = []
    for r, row in enumerate(grid):
        for c, v in enumerate(row):
            if v != bg:
                out.append((r, c, v))
    return out


def objects_of(grid, bg: int = 0) -> list:
    """4-connected components of non-background cells.

    Returns a list of objects, each a dict:
        {
          "cells":     frozenset[(row, col)],
          "pixels":    {(row, col): color},
          "color_set": sorted list of distinct colours in the object,
          "size":      cell count,
          "bbox":      (row_min, col_min, row_max, col_max),
        }
    Cells of differing colour are grouped together if 4-adjacent (a "blob"); the
    move tasks this seeds are single-colour, but grouping stays colour-agnostic
    so the same vocabulary serves multi-colour objects later.
    """
    pixels = {(r, c): v for (r, c, v) in cells_of(grid, bg)}
    visited = set()
    objects = []

    for start in pixels:
        if start in visited:
            continue
        comp = []
        queue = [start]
        while queue:
            p = queue.pop(0)
            if p in visited or p not in pixels:
                continue
            visited.add(p)
            comp.append(p)
            r, c = p
            for dr, dc in ((-1, 0), (1, 0), (0, -1), (0, 1)):
                nb = (r + dr, c + dc)
                if nb in pixels and nb not in visited:
                    queue.append(nb)

        comp_pixels = {p: pixels[p] for p in comp}
        rows = [r for r, _ in comp]
        cols = [c for _, c in comp]
        objects.append({
            "cells": frozenset(comp),
            "pixels": comp_pixels,
            "color_set": sorted(set(comp_pixels.values())),
            "size": len(comp),
            "bbox": (min(rows), min(cols), max(rows), max(cols)),
        })

    # Stable order: top-left first, so callers comparing across grids are
    # deterministic regardless of dict iteration order.
    objects.sort(key=lambda o: (o["bbox"][0], o["bbox"][1]))
    return objects


def unique_object(objects):
    """The single object if there is exactly one, else None.

    `unique` is the simplest selection expression (§2.5-2b): it commits the
    program to "the one object" without a task-specific literal.
    """
    if isinstance(objects, list) and len(objects) == 1:
        return objects[0]
    return None


def position_of(obj):
    """Top-left `(row, col)` of the object's bounding box."""
    if not obj:
        return None
    r0, c0, _r1, _c1 = obj["bbox"]
    return (r0, c0)


def bottom_right_of(obj):
    """Bottom-right `(row, col)` of the object's bounding box."""
    if not obj:
        return None
    _r0, _c0, r1, c1 = obj["bbox"]
    return (r1, c1)


def color_of(obj):
    """The object's single colour, or None if it is multi-coloured."""
    if not obj:
        return None
    cs = obj["color_set"]
    return cs[0] if len(cs) == 1 else None
