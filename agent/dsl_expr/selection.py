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


def objects_of(grid, bg: int = 0, same_color: bool = False) -> list:
    """4-connected components of non-background cells.

    Returns a list of objects, each a dict:
        {
          "cells":     frozenset[(row, col)],
          "pixels":    {(row, col): color},
          "color_set": sorted list of distinct colours in the object,
          "size":      cell count,
          "bbox":      (row_min, col_min, row_max, col_max),
        }
    With the default ``same_color=False`` cells of differing colour are grouped
    together if 4-adjacent (a "blob") — colour-agnostic, so the same vocabulary
    serves multi-colour objects. With ``same_color=True`` a component only grows
    across cells of the *same* colour, so two adjacent regions of different colour
    are distinct objects (the orthogonal colour-aware reading). The flag is an
    additive selection dimension — callers that name "the largest *same-coloured*
    region" pass ``same_color=True``; the default behaviour is unchanged (zero
    regression).
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
                if (nb in pixels and nb not in visited
                        and (not same_color or pixels[nb] == pixels[p])):
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
#
# `odd_shape` is a fourth, orthogonal selection dimension (shape identity). It
# names the object whose *shape* — its cells normalised to the bbox origin, so a
# translation-invariant signature — is unique among the objects. It is the only
# criterion that picks the acted-on object when several blobs are equal in size
# AND colour and none reaches a position extreme, differing only in shape (e.g.
# three identical I-trominoes and one L-tromino). Appended last so size, position
# and colour selectors still win when they apply (zero regression).
#
# `second_largest` / `second_smallest` are *ranked* size selectors — the first
# criteria that name a member which is neither the extreme nor the odd one out.
# `largest`/`smallest` pick rank 1 by size; these pick rank 2 (the n-th by size,
# the smallest useful rank beyond the extreme), via the answered Q-C3 ranking
# utils (`agent/dsl_expr/ranking.nth_by_desc` / `nth_by_asc`). They are the only
# criteria that pick the acted-on object when it is the middle of three strictly
# size-ordered objects — neither the biggest (`largest`) nor the smallest
# (`smallest`), no colour/shape odd-one-out, and at no position extreme. Appended
# LAST so every extreme / position / odd-one-out selector still wins when it
# applies (zero regression); a ranked pick only claims a selection nothing earlier
# explains.
# `unique_size` (appended last) is a *size*-identity odd-one-out, orthogonal to
# the size *extremes* (`largest`/`smallest`) and to the colour / shape odd-one-out:
# it names the object whose cell count is unique among the objects — appears in no
# other object — the only criterion that picks the acted-on object when several
# blobs share sizes and exactly one stands alone by size, yet it is neither the
# biggest nor the smallest (e.g. two size-3 blobs, two size-5 blobs, one size-4).
# Keys on within-grid size *uniqueness*, never a literal size, so it stays
# value-agnostic and computable from G0 alone (P5). Appended last so every
# extreme / position / colour / shape selector still wins when it applies (zero
# regression).
_SELECTOR_KINDS = (
    "unique",
    "largest", "smallest",
    "topmost", "bottommost", "leftmost", "rightmost",
    "odd_color",
    "odd_shape",
    "second_largest",
    "second_smallest",
    "unique_size",
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


def _size(obj):
    """The object's cell count — the key the size selectors rank on."""
    return obj["size"]


def _index_of(objects, item):
    """The position of `item` in `objects` by *identity*, or None. Identity (not
    ``==``) so two value-equal object dicts are never confused."""
    if item is None:
        return None
    for i, o in enumerate(objects):
        if o is item:
            return i
    return None


def _argextreme_index(objects, want_max):
    """Index of the *unique* size-extreme object, or None on a tie / no objects.

    A tie means the criterion does not pick a single object, so it must decline
    rather than guess — the selector has to be unambiguous to be value-agnostic.
    Delegates to the registered ranking utils (`ranking.argmax` / `argmin`, the
    rank-1 special case) so every size selector shares one tie-aware backing
    vocabulary (Q-C3, §2.5-1) rather than re-implementing the extreme.
    """
    from agent.dsl_expr import ranking
    pick = ranking.argmax(objects, _size) if want_max else ranking.argmin(objects, _size)
    return _index_of(objects, pick)


def _nth_size_index(objects, n, from_top):
    """Index of the unique object at size rank `n` (1-based) — counted from the
    largest when `from_top`, else from the smallest — or None when that rank is
    tied / absent. The *ranked* selector beyond the extreme (Q-C3 `nth_by_desc` /
    `nth_by_asc`); declines on a tie like the extreme selectors, keeping the pick
    value-agnostic."""
    from agent.dsl_expr import ranking
    pick = (
        ranking.nth_by_desc(objects, _size, n) if from_top
        else ranking.nth_by_asc(objects, _size, n)
    )
    return _index_of(objects, pick)


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


def _shape_signature(obj):
    """The object's shape as a translation-invariant signature: its cells
    normalised so the bbox top-left is the origin. Two objects have the *same
    shape* iff their signatures are equal, regardless of where they sit in the
    grid (and regardless of colour — shape is a separate dimension)."""
    cells = obj.get("cells")
    if not cells:
        return frozenset()
    r0 = min(r for r, _c in cells)
    c0 = min(c for _r, c in cells)
    return frozenset((r - r0, c - c0) for r, c in cells)


def _odd_shape_index(objects):
    """Index of the object whose *shape* is unique among the objects — its
    normalised cell signature matches no other object — or None when zero or
    several objects have a shape of their own (so it declines rather than guesses,
    like the size/position/colour selectors).

    This is a structure-based criterion (shape identity), orthogonal to size,
    position and colour: it names the acted-on object when several blobs are equal
    in size and colour and none is at a position extreme, differing only in shape
    (§2.1 multi-object selection). The choice keys on within-grid shape
    *uniqueness*, never a literal shape, so it stays value-agnostic and computable
    from G0 alone (P5)."""
    if not objects:
        return None
    sigs = [_shape_signature(o) for o in objects]
    counts = {}
    for sig in sigs:
        counts[sig] = counts.get(sig, 0) + 1
    singletons = [i for i, sig in enumerate(sigs) if counts[sig] == 1]
    return singletons[0] if len(singletons) == 1 else None


def _unique_size_index(objects):
    """Index of the object whose *size* (cell count) is unique among the objects —
    no other object has that size — or None when zero or several objects have a
    size of their own (so it declines rather than guesses, like the colour / shape
    odd-one-out). Keys on within-grid size uniqueness, never a literal size, so it
    stays value-agnostic and computable from G0 alone (P5)."""
    if not objects:
        return None
    counts = {}
    for o in objects:
        counts[o["size"]] = counts.get(o["size"], 0) + 1
    singletons = [i for i, o in enumerate(objects) if counts[o["size"]] == 1]
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
    if kind == "odd_shape":
        return _odd_shape_index(objects)
    if kind == "second_largest":
        return _nth_size_index(objects, 2, from_top=True)
    if kind == "second_smallest":
        return _nth_size_index(objects, 2, from_top=False)
    if kind == "unique_size":
        return _unique_size_index(objects)
    return None


def select_object(objects, descriptor):
    """Resolve a fitted *selector* descriptor to a single object using input-only
    criteria (§2.5-2b). Returns None when the criterion does not pick exactly one
    object, so callers decline rather than guess — keeping the choice value-agnostic
    and computable from G0 alone at test time (P5).

    Kinds (mirrors `_SELECTOR_KINDS`): ``unique`` (the sole object), ``largest`` /
    ``smallest`` (the unique size extremal object), the position extremes
    ``topmost`` / ``bottommost`` / ``leftmost`` / ``rightmost`` (the unique object
    whose bounding box reaches furthest to that edge), ``odd_color`` (the object
    whose colour is unique among the objects — the odd-one-out), ``odd_shape``
    (the object whose shape is unique among the objects), and the *ranked* size
    selectors ``second_largest`` / ``second_smallest`` (the unique object at size
    rank 2 from the top / bottom — neither the extreme nor an odd-one-out).
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
    ``topmost`` / ``bottommost`` / ``leftmost`` / ``rightmost``, then the colour
    odd-one-out ``odd_color``, the shape odd-one-out ``odd_shape``, and finally the
    *ranked* size selectors ``second_largest`` / ``second_smallest`` — mirroring
    `fit_target`'s ordering so the degenerate single-object case reads as ``unique``
    rather than an accidental criterion, and an extreme / odd-one-out selection is
    preferred over a ranked one. A task whose acted-on object is a size extreme on
    every pair still fits ``largest`` / ``smallest`` first; only a selection that
    *no* extreme, position or odd-one-out criterion explains — the middle of three
    strictly size-ordered objects, at no position extreme, with all colours and
    shapes distinct — falls through to the ranked ``second_largest`` /
    ``second_smallest``.
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


# --- multi-object move bijection (map-all gravity, BACKLOG_LOOP R1 "next gap") ---
#
# A multi-object move ("all objects fall" / gravity) must first match each *input*
# object to the *output* object it became, before any uniform displacement can be
# fitted — and the match has to be value-agnostic. The most-constrained reading is
# by the (colour-set + size + shape) a move preserves; it is unambiguous whenever
# the objects differ in any of those. But *identical* objects falling (the common
# gravity case) share that whole key, so it cannot say which fell where. A fall
# along one axis preserves the object's *other* bbox coordinate, which
# disambiguates: a vertical fall keeps each object's column (bbox left edge), a
# horizontal one keeps its row (bbox top edge). So the strategies, most-constrained
# first, add that preserved coordinate to the key. The caller
# (`ExtractPatternOperator._fit_map_all`) tries them in order and keeps the first
# whose resulting motions fit ONE uniform target — so ``identity`` still wins for
# distinct objects (zero regression) and an axis strategy only claims an
# identical-object scene ``identity`` cannot resolve.

def _motion_key_base(obj):
    """The (colour-set, size, shape) a colour-preserving move keeps invariant."""
    return (tuple(obj["color_set"]), obj["size"], _shape_signature(obj))


# Key functions per strategy: ``identity`` matches by the move-invariant base;
# ``vertical`` also pins the column (bbox left edge) a vertical fall preserves;
# ``horizontal`` also pins the row (bbox top edge) a horizontal fall preserves.
_MOTION_BIJECTION_KEYS = {
    "identity":   lambda o: _motion_key_base(o),
    "vertical":   lambda o: _motion_key_base(o) + (o["bbox"][1],),
    "horizontal": lambda o: _motion_key_base(o) + (o["bbox"][0],),
}

# Most-constrained-first order the caller iterates over.
MOTION_BIJECTION_STRATEGIES = ("identity", "vertical", "horizontal")


def _bijection_by_key(objs_in, objs_out, key_fn):
    """One-to-one match of input→output objects under `key_fn`, or None when the
    key does not pick exactly one unused output object for some input object (an
    ambiguous or partial match → decline rather than guess)."""
    if len(objs_in) != len(objs_out):
        return None
    used = set()
    pairs = []
    for oi in objs_in:
        ki = key_fn(oi)
        cands = [
            j for j, oj in enumerate(objs_out)
            if j not in used and key_fn(oj) == ki
        ]
        if len(cands) != 1:
            return None
        used.add(cands[0])
        pairs.append((oi, objs_out[cands[0]]))
    return pairs


def motion_bijection(objs_in, objs_out, strategy):
    """Bijection input→output objects under one matching `strategy`, or None.

    ``identity`` matches by the (colour-set + size + shape) a move preserves — the
    unambiguous reading. ``vertical`` additionally requires each object's column
    (bbox left edge) preserved, the disambiguator for identical objects falling
    straight down; ``horizontal`` requires the row (top edge) preserved, for
    identical objects sliding sideways. Returns the list of ``(input_obj,
    output_obj)`` pairs, or None when the strategy yields no clean bijection."""
    key_fn = _MOTION_BIJECTION_KEYS.get(strategy)
    if key_fn is None:
        return None
    return _bijection_by_key(objs_in, objs_out, key_fn)


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
