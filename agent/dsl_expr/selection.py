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


# --- multi-object selection (R1, §2.5-2b: "which object the rule acts on") ---
#
# `unique_object` is the degenerate selector — it only names an object when there
# is exactly one. The moment a grid holds several objects, *which one* a rule acts
# on becomes the crux (the §2.1 "multi-object selection" concept). That choice is
# itself an *argument expression*, fitted from the example comparison and computed
# at test time from G0 alone (P5) — never a stored literal index. The vocabulary
# below is the smallest set of input-only criteria that can name the acted-on
# object: the sole one (`unique`), a size extreme (`largest` / `smallest`), or a
# *position* extreme (`topmost` / `bottommost` / `leftmost` / `rightmost`). Size
# and position are orthogonal selection dimensions — a task whose acted-on object
# is neither the largest nor the smallest (e.g. several equal-sized blobs, the top
# one moves) can only be named positionally, which is exactly the gap the size
# selectors leave. New criteria are added here (the growing LHS), never as
# transformations (F3).

# `odd_color` (appended last) is a *property*-based selector, orthogonal to the
# size and position dimensions above: it names the object whose colour is unique
# among the objects (the odd-one-out), the only criterion that picks the acted-on
# object when several blobs are equal in size and none reaches a position extreme,
# differing only by colour.
_SELECTOR_KINDS = (
    "unique",
    "largest", "smallest",
    "topmost", "bottommost", "leftmost", "rightmost",
    "odd_color",
)

# Each position selector reads one edge of an object's bounding box; the extreme
# of that edge across the objects names the picked one. topmost/leftmost take the
# minimum (closest to the origin), bottommost/rightmost the maximum.
#   bbox = (row_min, col_min, row_max, col_max)
_POSITION_EDGE = {
    "topmost":    (0, False),  # min row_min
    "bottommost": (2, True),   # max row_max
    "leftmost":   (1, False),  # min col_min
    "rightmost":  (3, True),   # max col_max
}


def _argextreme_index(objects, want_max):
    """Index of the *unique* size-extreme object, or None on a tie / no objects.

    A tie means the criterion does not pick a single object, so it must decline
    rather than guess — the selector has to be unambiguous to be value-agnostic.
    """
    if not objects:
        return None
    sizes = [o["size"] for o in objects]
    target = max(sizes) if want_max else min(sizes)
    idxs = [i for i, s in enumerate(sizes) if s == target]
    return idxs[0] if len(idxs) == 1 else None


def _position_index(objects, edge, want_max):
    """Index of the *unique* object whose bbox `edge` is extremal, or None on a
    tie / no objects. Like `_argextreme_index` but over a bbox coordinate rather
    than size, so it declines (rather than guesses) when two objects share the
    extreme — keeping the positional selector unambiguous and value-agnostic."""
    if not objects:
        return None
    coords = [o["bbox"][edge] for o in objects]
    target = max(coords) if want_max else min(coords)
    idxs = [i for i, v in enumerate(coords) if v == target]
    return idxs[0] if len(idxs) == 1 else None


def _odd_color_index(objects):
    """Index of the object whose single colour is *unique among the objects* — it
    appears in no other object — or None when zero or several objects have a colour
    of their own (so it declines rather than guesses, like the size/position
    selectors). A multi-coloured object (no single colour) is never the odd-one-out.

    This is a property-based criterion (colour identity), orthogonal to size and
    position: it names the acted-on object when several blobs are equal in size and
    none at a position extreme, differing only by colour (§2.1 multi-object
    selection). The choice keys on within-grid colour *uniqueness*, never a literal
    colour value, so it stays value-agnostic and computable from G0 alone (P5)."""
    if not objects:
        return None
    colors = [color_of(o) for o in objects]  # single colour, or None if multi-coloured
    counts = {}
    for col in colors:
        if col is not None:
            counts[col] = counts.get(col, 0) + 1
    singletons = [
        i for i, col in enumerate(colors)
        if col is not None and counts[col] == 1
    ]
    return singletons[0] if len(singletons) == 1 else None


def _selection_index(objects, kind):
    """Index the criterion `kind` picks from `objects`, or None if it declines."""
    if kind == "unique":
        return 0 if isinstance(objects, list) and len(objects) == 1 else None
    if kind == "largest":
        return _argextreme_index(objects, want_max=True)
    if kind == "smallest":
        return _argextreme_index(objects, want_max=False)
    if kind in _POSITION_EDGE:
        edge, want_max = _POSITION_EDGE[kind]
        return _position_index(objects, edge, want_max)
    if kind == "odd_color":
        return _odd_color_index(objects)
    return None


def select_object(objects, descriptor):
    """Resolve a fitted *selector* descriptor to a single object using input-only
    criteria (§2.5-2b). Returns None when the criterion does not pick exactly one
    object, so callers decline rather than guess — keeping the choice value-agnostic
    and computable from G0 alone at test time (P5).

    Kinds (mirrors `_SELECTOR_KINDS`): ``unique`` (the sole object), ``largest`` /
    ``smallest`` (the unique size extremal object), the position extremes
    ``topmost`` / ``bottommost`` / ``leftmost`` / ``rightmost`` (the unique object
    whose bounding box reaches furthest to that edge), and ``odd_color`` (the
    object whose colour is unique among the objects — the odd-one-out).
    """
    if not descriptor or not isinstance(objects, list) or not objects:
        return None
    idx = _selection_index(objects, descriptor.get("kind"))
    return objects[idx] if idx is not None else None


def fit_selector(selections):
    """Fit a value-agnostic *selector* expression across example pairs.

    `selections` is a list of per-pair dicts ``{"objects": [...], "selected": idx}``
    where ``objects`` are the input objects (from `objects_of`) and ``selected`` is
    the index of the one the transformation acted on (identified by the caller from
    the output). Returns a descriptor naming an input-only criterion that picks the
    selected object in *every* pair, or None if none fits (so the matcher declines
    rather than guessing).

    Tried most-structural first — ``unique`` (every pair has a sole object), then
    the size extremes ``largest`` / ``smallest``, then the position extremes
    ``topmost`` / ``bottommost`` / ``leftmost`` / ``rightmost``, and finally the
    colour odd-one-out ``odd_color`` — mirroring `fit_target`'s ordering so the
    degenerate single-object case reads as ``unique`` rather than an accidental
    size/position/colour criterion, and a size-describable selection is preferred
    over a positional or colour one. A task whose acted-on object is a size extreme
    on every pair still fits ``largest`` / ``smallest`` first; only a selection that
    *no* size or position criterion explains (equal-sized blobs, none at a position
    extreme, differing only by colour) falls through to ``odd_color``.
    """
    if not selections:
        return None
    for kind in _SELECTOR_KINDS:
        if all(
            _selection_index(s["objects"], kind) == s["selected"]
            for s in selections
        ):
            return {"kind": kind}
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
