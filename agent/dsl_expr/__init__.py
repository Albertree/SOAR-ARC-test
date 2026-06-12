"""
agent.dsl_expr — seed object-expression vocabulary (property / selection).

This is the *argument-expression* material of BACKLOG_LOOP.md R1 / §2.5: the
property and selection functions that read an object's color / size / position
and that *select* which object a transformation acts on. It is **deliberately
separate** from the transformation DSL.

  - transformation (action / RHS) = `make_grid` + `coloring`, frozen at two,
    lives in `procedural_memory/DSL/` (INVARIANTS F3).
  - property / selection (argument / LHS) = this package, allowed to *grow*,
    lives under `agent/` — **not** `procedural_memory/DSL/`.

Why this location: BACKLOG_LOOP.md §2.5-1 records a standing conflict between
`CLAUDE.md §6.1` ("no new `def` under `procedural_memory/DSL/`") and
`arbor-dsl-taxonomy §3` ("property/relation/util hand-coding is allowed and
should grow"). The resolution the ladder prescribes — and that this package
implements — is: honor the frozen transformation contract (two primitives in
`DSL/`) while growing the argument vocabulary here in `agent/`, where the F3
checker (`procedural_memory/DSL/*.py` only) does not apply. This is surfaced in
the iter session log, not silently chosen.

Why it matters (BACKLOG_LOOP.md §2.5-2b): a moving object must be *selected*
(`unique` / later `argmax` / `filter`) and *read* (`position_of` / `color_of`)
so its coordinate and color become argument expressions like
`position_of(unique(objects_of(G0)))` rather than raw literals. Only lifted that
way can R3's `anti_unification.unify()` find a common skeleton across pairs —
raw `coloring([(5,5)], 2)` literals differ per task and never unify (the
168-rule failure, taxonomy §4). This package is the substrate for that lift.

Everything here is deterministic and side-effect-free (P7: symbolic dicts only,
no vectors/embeddings).
"""

from ARCKG.hodel import hodel_objects

#: Canonical foreground interpretation used by `objects_of`. One stable reading
#: (same-color 4-connected components, background = most frequent color) so the
#: vocabulary is deterministic. Other interpretations (diagonal, multi-color)
#: are available through hodel directly but are not the default selection basis.
_FOREGROUND = dict(univalued=True, diagonal=False, without_bg=True)


def objects_of(grid) -> list:
    """Return the canonical foreground objects of `grid` as symbolic dicts.

    `grid` is a raw 2D list/tuple of color ints. Each returned object is::

        {
          "cells":    frozenset[(row, col)],   # absolute coordinates
          "colors":   frozenset[int],          # colors present in the object
          "color":    int | None,              # the sole color, or None if mixed
          "size":     int,                     # number of cells
          "position": (row_min, col_min),      # top-left of the bounding box
        }

    Objects are returned sorted by `position` for determinism. Background (the
    most frequent color) is excluded — these are the *things on* the grid.
    """
    gg = tuple(tuple(row) for row in grid)
    if not gg or not gg[0]:
        return []

    result = []
    for obj_fs in hodel_objects(gg, **_FOREGROUND):
        cells = frozenset((r, c) for _, (r, c) in obj_fs)
        colors = frozenset(color for color, _ in obj_fs)
        rows = [r for r, _ in cells]
        cols = [c for _, c in cells]
        result.append({
            "cells": cells,
            "colors": colors,
            "color": next(iter(colors)) if len(colors) == 1 else None,
            "size": len(cells),
            "position": (min(rows), min(cols)),
        })

    result.sort(key=lambda o: o["position"])
    return result


def unique(objs):
    """Selection: return the sole object when there is exactly one, else None.

    This is the simplest selection function (BACKLOG_LOOP.md §2.5-2b). It is how
    a single-object task picks *which* object to read/move without a literal —
    the seed from which richer selectors (`argmax(_, size_of)`, `filter`) grow.
    """
    if isinstance(objs, list) and len(objs) == 1:
        return objs[0]
    return None


def color_of(obj):
    """Property: the object's sole color, or None if it is multi-colored."""
    if not isinstance(obj, dict):
        return None
    return obj.get("color")


def size_of(obj):
    """Property: the object's cell count (its size)."""
    if not isinstance(obj, dict):
        return None
    return obj.get("size")


def position_of(obj):
    """Property: the object's top-left bounding-box coordinate (row, col)."""
    if not isinstance(obj, dict):
        return None
    return obj.get("position")
