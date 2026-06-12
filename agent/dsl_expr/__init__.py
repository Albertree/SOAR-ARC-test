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


#: The four grid corners, each named by a stable id and expressed as a pair of
#: (row, col) *anchors* over the grid bounds — "min" → 0, "max" → dim-1. Keeping
#: the corner as an anchor formula (not a concrete cell) is what makes it
#: value-agnostic: the same `br` ("max","max") resolves to a *different* cell in
#: every differently-sized grid, so a corner-landing rule covers a whole family
#: without storing any task's literal coordinate (BACKLOG_LOOP.md §2.5-2b).
_CORNER_ANCHORS = {
    "tl": ("min", "min"),
    "tr": ("min", "max"),
    "bl": ("max", "min"),
    "br": ("max", "max"),
}


def _anchor_value(anchor, extent):
    """Resolve an anchor ("min"/"max") to a coordinate in a 0..extent-1 axis."""
    return 0 if anchor == "min" else extent - 1


def corner_cell(corner_id, height, width):
    """Util: the (row, col) of `corner_id` (tl/tr/bl/br) in a height×width grid.

    The inverse of `corners_at`: given a corner id and concrete grid bounds,
    resolve the anchor formula to the actual cell. None for an unknown id."""
    anchors = _CORNER_ANCHORS.get(corner_id)
    if anchors is None:
        return None
    return (_anchor_value(anchors[0], height), _anchor_value(anchors[1], width))


def output_dims(pair_dims, test_in_dims):
    """Relation: derive the test output grid's (height, width) from how the
    example pairs' output dimensions relate to their input dimensions.

    `pair_dims` is a list of `((in_h, in_w), (out_h, out_w))` for each example
    pair; `test_in_dims` is the test input's `(height, width)`. The derivation is
    value-agnostic — it reads only the COMM/DIFF of the example dims (P3/P4), not
    any task's literal size. Two relations are recognized, the more general one
    first:

      - **size-preserved**: every output equals its own input → the test output
        tracks the test input (return `test_in_dims`). This is the relation
        "out == in" and holds even when the grids differ in size across pairs
        (easy000g: 4×4 / 3×5 / 6×4) where *no single dimension* is constant.
      - **constant output size**: every output shares one `(h, w)` → that
        constant is the test output size (return it), even when the inputs differ
        (easy000i: 6×6 inputs collapse to 5×5 outputs).

    Returns None when neither relation holds — the resize is not yet derivable, so
    no guess is made (the caller falls back to identity). The two relations agree
    when the inputs are also constant, so size-preserved is checked first as the
    more general reading. This is argument material (a relation between input and
    output grid bounds), so it lives here under `agent/`, not in the frozen
    `procedural_memory/DSL/` (BACKLOG_LOOP.md §2.5-1)."""
    if not pair_dims:
        return None
    if all(ind == outd for ind, outd in pair_dims):
        return test_in_dims
    out_set = {outd for _, outd in pair_dims}
    if len(out_set) == 1:
        return next(iter(out_set))
    return None


def corners_at(pos, height, width):
    """Relation: the set of corner ids (tl/tr/bl/br) whose cell coincides with
    `pos` in a height×width grid.

    A relation between an object's position and the grid bounds (BACKLOG_LOOP.md
    §2.5-1 relation/util vocabulary — argument material, *not* a transformation,
    so it lives here under `agent/`, not in the frozen `procedural_memory/DSL/`).
    Returns a (possibly empty) set so callers can intersect it across pairs to
    find the *common* corner — the value-agnostic COMM the corner-filling rule
    keys on. Empty when `pos` sits on no corner."""
    if not pos:
        return set()
    r, c = pos
    return {
        cid
        for cid, anchors in _CORNER_ANCHORS.items()
        if r == _anchor_value(anchors[0], height) and c == _anchor_value(anchors[1], width)
    }
