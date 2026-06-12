"""
selection — the object/property/selection argument vocabulary (BACKLOG_LOOP §2.5,
R1). This is the *LHS* half that BACKLOG_LOOP §2.5-1 says must *grow*: the
material that fills the arguments of the two frozen transformation primitives.

It lives under ``agent/`` (NOT ``procedural_memory/DSL/``) precisely because it
is **not** a transformation — adding object detection / `position-of` / `color-of`
introduces no new way of *doing* a transformation, only of *naming what one acts
on*. Putting it in the frozen DSL dir would (correctly) trip F3; here it is the
allowed, encouraged property/relation/util/selection layer (CLAUDE.md §6.3 ↔
arbor-dsl-taxonomy §3; the CLAUDE.md §6.1-vs-taxonomy conflict is surfaced in the
session log per PROMPT.md Step1.C).

R1's real product is the *lift of selection* (§2.5-2b): instead of a raw literal
coordinate, an object is *selected* (`unique_object`) and *read*
(`position_of`/`color_of`), so that R3's anti-unification later has a common
skeleton to abstract. These functions are deterministic and side-effect-free.

Object detection reuses the frozen `ARCKG.hodel` port (8-connected components,
background excluded), so no new detection code is introduced here.
"""

from collections import Counter

from ARCKG.hodel import hodel_objects


# ---------------------------------------------------------------------------
# property vocabulary (read a feature off a grid / object)
# ---------------------------------------------------------------------------

def background_of(grid: list) -> int:
    """Most frequent color (ties → smallest). The canvas/background color."""
    counts = Counter(cell for row in grid for cell in row)
    if not counts:
        return 0
    most = max(counts.values())
    return min(c for c, n in counts.items() if n == most)


def position_of(obj: dict):
    """Top-left (min-row, min-col) anchor of an object."""
    return obj["position"]


def color_of(obj: dict):
    """The object's single color, or None when it is multi-colored."""
    return obj.get("color")


def size_of(obj: dict) -> int:
    """Cell count of an object."""
    return obj["size"]


def normalized_shape(obj: dict):
    """Cells translated so the top-left anchor sits at (0, 0).

    Two objects share a *shape* iff their normalized_shape sets are equal —
    position-invariant identity, used to decide "the object only moved."
    """
    r0, c0 = obj["position"]
    return frozenset((r - r0, c - c0) for (r, c) in obj["cells"])


def extent_of(obj: dict):
    """The object's bounding-box ``(height, width)`` in cells."""
    cells = obj["cells"]
    rows = [r for r, _c in cells]
    cols = [c for _r, c in cells]
    return (max(rows) - min(rows) + 1, max(cols) - min(cols) + 1)


def bbox_height_of(obj: dict) -> int:
    """The object's bounding-box height in cells — a scalar property *distinct*
    from `size_of` (cell-count) whenever the shape is not a solid column. A
    second named dimension property (`DIM_PROPERTY_VOCAB`), so the size-grid
    family carries ≥2 properties sharing one `make_grid` skeleton — the input
    anti-unification lifts into a property-parameterised `size_to_grid` rule
    (R3, §2.5-2)."""
    return extent_of(obj)[0]


def bbox_width_of(obj: dict) -> int:
    """The object's bounding-box width in cells — the column analogue of
    `bbox_height_of`. Named for symmetry / readability; `bbox_extent_of` reads
    both at once for the non-square (`h × w`) sizing reading."""
    return extent_of(obj)[1]


def bbox_extent_of(obj: dict):
    """The object's bounding box as a ``(height, width)`` *pair* — a single named
    dimension *reading* that yields two canvas dimensions at once (`RECT_DIM_VOCAB`).

    Where the scalar properties (`size_of`, `bbox_height_of`) each size a *square*
    (one value reused for both axes), this is the smallest step into a *non-square*
    output: a rectangle whose height is the object's bbox height and whose width is
    its bbox width (BACKLOG_LOOP §2.1 "grid size = f(object property)", the
    h=bbox_height / w=bbox_width case the size-grid family could not yet express).
    It composes the two frozen primitives identically (a uniform `make_grid` fill);
    only the *argument* — now an extent pair instead of a scalar — is richer
    (§2.5-1, F3-exempt). Treating the pair as **one** named reading lets it fold
    into the existing `size_to_grid` abstraction as one more value its dimension
    variable ranges over (like `object_count`), so covers rises while the rule
    count holds — without the fully-general two-independent-properties cross-product
    lift, which remains the next, larger half (§2 "do the smaller half first")."""
    return extent_of(obj)


# ---------------------------------------------------------------------------
# relation vocabulary: grid-relative position (a corner of the canvas)
# ---------------------------------------------------------------------------

#: The four grid corners, in deterministic order.
CORNERS = ("top_left", "top_right", "bottom_left", "bottom_right")


def corner_anchor(name: str, height: int, width: int,
                  obj_h: int = 1, obj_w: int = 1):
    """Top-left anchor that places an ``obj_h × obj_w`` object flush into the
    named grid corner. A *grid-relative* position expression (§2.5-1): unlike a
    literal target it is a function of the canvas size, so the same reading
    transfers across grids of different sizes (easy000g)."""
    row = 0 if name in ("top_left", "top_right") else height - obj_h
    col = 0 if name in ("top_left", "bottom_left") else width - obj_w
    return (row, col)


def corners_matching(anchor, height: int, width: int,
                     obj_h: int, obj_w: int) -> list:
    """Which corner name(s) an object's top-left ``anchor`` flush-occupies, given
    the canvas size and object extent. Usually one; a degenerate full-row/column
    object can match several, so the list is returned (caller intersects)."""
    return [
        name for name in CORNERS
        if list(corner_anchor(name, height, width, obj_h, obj_w)) == list(anchor)
    ]


# ---------------------------------------------------------------------------
# selection vocabulary (pick objects out of a grid)
# ---------------------------------------------------------------------------

def objects_of(grid: list, background: int | None = None) -> list:
    """Connected components (8-connected, background excluded), one dict each.

    Each object: ``{cells, pixels, colors, color, size, position}`` where
    ``pixels`` is the list of ``(row, col, color)`` triples (so a translated
    re-paint preserves per-cell color). Returned in a deterministic order
    (by top-left anchor) so downstream comparison is reproducible.
    """
    if background is None:
        background = background_of(grid)
    g = tuple(tuple(row) for row in grid)
    raw_objs = hodel_objects(g, univalued=False, diagonal=True, without_bg=True)

    result = []
    for obj in raw_objs:
        pixels = sorted((r, c, v) for (v, (r, c)) in obj)
        cells = [(r, c) for (r, c, _v) in pixels]
        colors = sorted({v for (_r, _c, v) in pixels})
        top = (min(r for r, c in cells), min(c for r, c in cells))
        result.append({
            "cells": cells,
            "pixels": pixels,
            "colors": colors,
            "color": colors[0] if len(colors) == 1 else None,
            "size": len(cells),
            "position": top,
        })
    result.sort(key=lambda o: o["position"])
    return result


def unique_object(grid: list, background: int | None = None):
    """The single foreground object, or None when there is not exactly one.

    `unique` in the §2.5 selection vocabulary: it lets a rule say "the object"
    without a literal coordinate, which is what makes the program liftable (R3).
    """
    objs = objects_of(grid, background)
    return objs[0] if len(objs) == 1 else None


# ---------------------------------------------------------------------------
# selection vocabulary: pick ONE object out of MANY by a property criterion
# ---------------------------------------------------------------------------
#
# This is the §2.5-2b "selection-lift" material. `unique_object` above is the
# degenerate (count==1) selector; when several objects are present, *which one*
# the rule acts on is the crux, and the selector — `argmax`/`argmin` over a
# property, or "the odd-one-out" — is the real content of the rule. These are
# util/selection functions (NOT transformations), so they belong here under
# agent/ and not in the frozen DSL dir (BACKLOG_LOOP §2.5-1, F3).
#
# Each selector returns the chosen object, or None when the choice is *not
# unambiguous* (a tie at the extreme, or no single odd-one-out). Returning None
# on ambiguity keeps a selector honest: a rule may only commit to a selector
# that names exactly one object, so the prediction stays well-defined.

def select_extreme(objects: list, key, mode: str = "max"):
    """The object whose ``key(obj)`` is maximal (``mode='max'``) or minimal
    (``mode='min'``) — `argmax`/`argmin` in the selection vocabulary. Returns
    None when more than one object ties at the extreme (ambiguous)."""
    if not objects:
        return None
    vals = [(key(o), o) for o in objects]
    best = max(v for v, _o in vals) if mode == "max" else min(v for v, _o in vals)
    winners = [o for v, o in vals if v == best]
    return winners[0] if len(winners) == 1 else None


def select_unique_color(objects: list):
    """The single object whose (single) color is shared by no other object — the
    "odd colour out". Returns None when zero or several objects qualify."""
    counts = Counter(o["color"] for o in objects if o.get("color") is not None)
    uniques = [
        o for o in objects
        if o.get("color") is not None and counts[o["color"]] == 1
    ]
    return uniques[0] if len(uniques) == 1 else None


def select_unique_shape(objects: list):
    """The single object whose (normalized) shape is shared by no other — the
    "odd shape out". The shape-axis analogue of `select_unique_color`: where that
    keys on colour, this keys on `normalized_shape` (position-invariant cell set),
    so it discriminates a task whose objects share size *and* colour but differ in
    form. Returns None when zero or several objects qualify."""
    shapes = [normalized_shape(o) for o in objects]
    counts = Counter(shapes)
    uniques = [o for o, s in zip(objects, shapes) if counts[s] == 1]
    return uniques[0] if len(uniques) == 1 else None


def touches_border(obj: dict, height: int, width: int) -> bool:
    """True iff the object occupies any cell on the grid's outer edge (top/bottom
    row or left/right column)."""
    return any(
        r == 0 or c == 0 or r == height - 1 or c == width - 1
        for (r, c) in obj["cells"]
    )


def select_border_object(objects: list, grid: list):
    """The single object that touches the grid border, when exactly one does.

    A *grid-relative* (relation) selector — the first in the vocabulary whose
    criterion is **not intrinsic** to the object considered alone: it reads the
    canvas extent (the grid) to decide whether an object sits against the border.
    That is the §2.5-1 "grid-relative position expression" axis (the placement
    side already has `corner_anchor`; this is its selection-side analogue), an
    axis the size/colour/shape selectors structurally cannot express because they
    never see the grid. Returns None when zero or several objects qualify
    (ambiguous), keeping the selector honest like the others."""
    if not grid:
        return None
    height = len(grid)
    width = len(grid[0]) if grid else 0
    on_border = [o for o in objects if touches_border(o, height, width)]
    return on_border[0] if len(on_border) == 1 else None


#: Named property-selectors, tried in this deterministic order when *learning*
#: which one a task uses (the first that consistently picks the preserved object
#: across every example pair wins). Adding a named selector grows the LHS
#: argument vocabulary — it introduces no new transformation (F3-exempt).
#:
#: Every selector takes ``(objects, grid)`` so a *grid-relative* (relation)
#: criterion can read the canvas extent. The intrinsic selectors
#: (size/colour/shape) ignore ``grid``; `border_object` uses it. `border_object`
#: is appended **last** so tasks an earlier, intrinsic selector already resolves
#: keep resolving to it (the learner takes the first consistent one). It keys on
#: a different *axis* (grid-relative position, a relation) from the intrinsic
#: selectors above, so it names objects none of them can — yet it still lifts
#: into the same `place_object` abstraction, not a new family.
SELECTOR_VOCAB = {
    "max_size": lambda objs, grid: select_extreme(objs, size_of, "max"),
    "min_size": lambda objs, grid: select_extreme(objs, size_of, "min"),
    "unique_color": lambda objs, grid: select_unique_color(objs),
    "unique_shape": lambda objs, grid: select_unique_shape(objs),
    "border_object": select_border_object,
}


def analyze_object_select_move(example_pairs: list) -> dict:
    """Multi-object *selection* move (BACKLOG_LOOP §2.5-2b, R1's real product).

    The converse of `analyze_object_move`: there the grid holds a single object,
    so "the object" needs no selector. Here several objects are present and the
    crux is *which one* the rule keeps — the §2.1 "multi-object selection"
    concept. The selector is **learned from comparison**, not invented (P3/P4):

    1. Per pair, the output holds exactly one object; the *preserved* input object
       is the one whose shape+colour survive into it (a COMM between an input
       object and the output object). That identifies, by comparison, which object
       was selected.
    2. Across pairs, find the named property-selector (`SELECTOR_VOCAB`:
       `max_size`/`min_size`/`unique_color`) that picks exactly that preserved
       object in *every* pair. That consistent selector is the lifted argument —
       value-agnostic in colour, position and the non-selected distractors.
    3. The placement is a cross-pair COMM on the selected object's move — the
       *same* readings the single-object family computes (§2.5 structural
       unification, the converse asymmetry the single-object `analyze_object_move`
       reads four ways but selection read only one): either a `constant_target`
       (every example anchors the selected object at the same absolute cell) or a
       `constant_offset` (every example displaces it by the same vector
       ``target − source`` while the absolute anchor varies). Reading the *offset*
       of the *selected* object closes the gap where a multi-object task moves its
       chosen object by a fixed displacement rather than to a fixed cell.

    A sibling of the object_move readings (it places the *selected* object via
    make_grid ∘ coloring), so it lifts into the same `place_object` abstraction
    (R3) rather than spawning a per-task family.

    Returns a symbolic dict; the `object_select_target` matcher decides firing and
    PredictOperator renders from it. Stays inert (multi_object_all=False) on the
    single-object easy_a tasks, so it never perturbs that family.
    """
    per_pair = []
    for pair in example_pairs:
        g0 = getattr(pair, "input_grid", None)
        g1 = getattr(pair, "output_grid", None)
        if g0 is None or g1 is None:
            continue
        in_objs = objects_of(g0.raw)
        out_objs = objects_of(g1.raw)
        multi = len(in_objs) >= 2 and len(out_objs) == 1
        selected = None
        target = None
        offset = None
        if multi:
            out_obj = out_objs[0]
            for o in in_objs:
                if (normalized_shape(o) == normalized_shape(out_obj)
                        and o["colors"] == out_obj["colors"]):
                    selected = o
                    break
            target = list(position_of(out_obj))
            if selected is not None:
                source = position_of(selected)
                offset = [target[0] - source[0], target[1] - source[1]]
        per_pair.append({
            "multi": multi,
            "in_objs": in_objs,
            "grid": g0.raw,
            "selected": selected,
            "target": target,
            "offset": offset,
            "size_preserved": (
                len(g0.raw) == len(g1.raw)
                and (len(g0.raw[0]) if g0.raw else 0) == (len(g1.raw[0]) if g1.raw else 0)
            ),
        })

    multi_all = bool(per_pair) and all(
        p["multi"] and p["selected"] is not None for p in per_pair)
    size_all = bool(per_pair) and all(p["size_preserved"] for p in per_pair)

    targets = [tuple(p["target"]) for p in per_pair if p["target"] is not None]
    constant_target = (
        list(targets[0])
        if targets and len(targets) == len(per_pair)
        and all(t == targets[0] for t in targets)
        else None
    )

    # Constant displacement of the *selected* object — the cross-pair COMM on the
    # relative move (mirrors analyze_object_move's constant_offset, but on the
    # chosen object). Meaningful when the absolute anchor varies pair-by-pair but
    # the move vector does not.
    offsets = [tuple(p["offset"]) for p in per_pair if p.get("offset") is not None]
    constant_offset = (
        list(offsets[0])
        if offsets and len(offsets) == len(per_pair)
        and all(o == offsets[0] for o in offsets)
        else None
    )

    # Learn the selector: the first named criterion that picks the preserved
    # object in every pair. Grounded in step 1's comparison (which object
    # survived), never assumed.
    selector = None
    if multi_all:
        for name, fn in SELECTOR_VOCAB.items():
            ok = True
            for p in per_pair:
                chosen = fn(p["in_objs"], p["grid"])
                if chosen is None or chosen["cells"] != p["selected"]["cells"]:
                    ok = False
                    break
            if ok:
                selector = name
                break

    return {
        "per_pair": per_pair,
        "multi_object_all": multi_all,
        "size_preserved_all": size_all,
        "constant_target": constant_target,
        "constant_offset": constant_offset,
        "selector": selector,
    }


# ---------------------------------------------------------------------------
# property vocabulary: scalar object features that can *size a canvas*
# ---------------------------------------------------------------------------
#
# §2.1 "the grid size is a function of an object's property" concept. The two
# placement families above keep the object's *shape* and read its *position*;
# this axis is orthogonal — the output's *dimensions* are read off a scalar
# property of an object (its cell-count, its bounding-box height, …). That makes
# the dimension argument of the frozen `make_grid` primitive a *property
# expression* (`size_of(unique_object(in))`) instead of a constant — exactly the
# §2.5-1 "argument vocabulary grows; transformation stays frozen" direction.
#
# Like SELECTOR_VOCAB, this is a named, deterministic vocabulary: the analysis
# learns *which* property reproduces the output side in every pair (grounded in
# the cross-pair COMM between the property and the output dimension, P3/P4), it
# does not assume one. Adding a property here grows the LHS argument vocabulary;
# it introduces no new transformation (F3-exempt, lives under agent/).

#: name -> fn(obj) -> int. A scalar object property usable as a canvas dimension.
#: Tried in this deterministic order when *learning* which property a task uses
#: (the first whose value reproduces the output side in every pair wins). Adding
#: a property grows the LHS argument vocabulary; it introduces no new
#: transformation (F3-exempt). Two distinct properties here are what give the
#: size-grid family ≥2 concrete rules sharing the `size_to_grid` skeleton — the
#: anti-unification lift input (R3, §2.5-2 / §2.5-4: rule count falls while covers
#: rises, the only "real progress" direction).
DIM_PROPERTY_VOCAB = {
    "object_size": size_of,
    "bbox_height": bbox_height_of,
}


# ---------------------------------------------------------------------------
# property vocabulary: a *rectangular* dimension reading (h, w) off one object
# ---------------------------------------------------------------------------
#
# The scalar `DIM_PROPERTY_VOCAB` above each size a *square* — one value reused
# for both canvas axes (`out_h == out_w`). The §2.1 concept also admits a
# *non-square* output whose height and width are read independently off the
# object. The smallest step into that is a single named reading that returns the
# whole ``(height, width)`` *pair* at once (`bbox_extent`), so the rectangle is
# named by one expression rather than two independent ones — keeping it a single
# lifted value that folds into the existing `size_to_grid` abstraction (like
# `object_count`), not a two-variable cross-product lift (the larger, deferred
# half). Each function takes one object and returns ``(h, w)``.
RECT_DIM_VOCAB = {
    "bbox_extent": bbox_extent_of,
}


# ---------------------------------------------------------------------------
# property vocabulary: scalar *grid-level* features that can size a canvas
# ---------------------------------------------------------------------------
#
# The object properties above read a scalar off *one* object — they presuppose a
# single object (`unique_object`). The §2.1 "object count ≠ 1" concept is the
# converse: the canvas dimension is a function not of any single object but of the
# *set* of objects in the grid. `object_count` is the seed — the number of
# foreground objects. It is the §2.5-2b point that *which subject* the dimension
# property reads is itself part of the lifted argument: `size_of(unique_object(in))`
# reads one object, `object_count(objects_of(in))` reads the whole set. Both bottom
# out in the same frozen `make_grid` dimension argument, so a count-sized task lifts
# into the *same* `size_to_grid` family (one more value the dimension variable
# ranges over) rather than a new family — covers rises, rule count holds (§2.5-4).
#
# Each function takes the object *list*, so it works whatever the object count is.
# Adding one grows the LHS argument vocabulary; it introduces no new transformation
# (F3-exempt, lives under agent/).

def object_count_of(objects: list) -> int:
    """Number of foreground objects in a grid — a *grid-level* scalar property
    (it reads the whole object set, not one object). Sizes a canvas when the
    output side counts the objects (§2.1 "object count ≠ 1")."""
    return len(objects)


#: name -> fn(objects) -> int. A scalar *grid-level* property usable as a canvas
#: dimension. Tried (after the per-object `DIM_PROPERTY_VOCAB`) when *learning*
#: which property a task uses. Kept separate from the object properties because
#: its subject is the object *set*, not a single object — the §2.5-2b "which
#: subject feeds the dimension argument" axis. A value learned here is just one
#: more filler of the same `size_to_grid` dimension variable (it lifts into the
#: existing family, not a new one).
GRID_DIM_PROPERTY_VOCAB = {
    "object_count": object_count_of,
}


def analyze_object_size_grid(example_pairs: list) -> dict:
    """Output canvas *sized by an object property* (BACKLOG_LOOP §2.1 / R1).

    The orthogonal axis to the object-move families: there the output keeps the
    object's shape and the readings are about *where* it lands; here the output
    is a *solid square* whose side is a **function of a scalar object property**
    and whose colour is the object's colour. The lifted argument is the property
    expression feeding `make_grid`'s dimension — `size_of(unique_object(in))` —
    not a literal, so it is value-agnostic in the object's colour, size, shape and
    position and transfers across pairs whose objects differ.

    Grounded in comparison, never assumed (P3/P4):

    1. Per pair the input holds one object; the output is a *solid* rectangle
       (single colour) — a degenerate ``make_grid``-only render (a uniform fill
       needs no ``coloring`` call).
    2. The output colour equals the object's colour in every pair (a colour COMM
       between the object and the output fill).
    3. Across pairs, find the named property (`DIM_PROPERTY_VOCAB`) whose value
       equals the output's side in *every* pair (the cross-pair COMM between the
       property and the output dimension). Only a square (``out_h == out_w``) is
       read here — the smallest, cleanest form of the concept.

    Returns a symbolic dict; the `object_size_grid` matcher (agent/conditions/)
    decides firing and PredictOperator renders from it. Stays inert (dim_property
    None / solid_output_all False) on the move families, so it never perturbs
    them.
    """
    per_pair = []
    for pair in example_pairs:
        g0 = getattr(pair, "input_grid", None)
        g1 = getattr(pair, "output_grid", None)
        if g0 is None or g1 is None:
            continue
        objs = objects_of(g0.raw)
        obj = objs[0] if len(objs) == 1 else None
        out = g1.raw or []
        out_h = len(out)
        out_w = len(out[0]) if out_h else 0
        out_colors = {cell for row in out for cell in row}
        out_solid = len(out_colors) == 1 and out_h > 0 and out_w > 0
        out_color = next(iter(out_colors)) if out_colors else None
        # Subject colour: the colour shared by *every* input object (a colour
        # COMM across the object set), which collapses to the single object's
        # colour when there is one. None when the objects disagree, so a
        # multi-colour grid never grounds a colour relation.
        all_colored = bool(objs) and all(
            o.get("color") is not None for o in objs)
        obj_colors = {o["color"] for o in objs} if all_colored else set()
        subj_color = next(iter(obj_colors)) if len(obj_colors) == 1 else None
        per_pair.append({
            "single_object": obj is not None,
            "obj_size": size_of(obj) if obj is not None else None,
            "obj_color": color_of(obj) if obj is not None else None,
            "subj_color": subj_color,
            "out_h": out_h,
            "out_w": out_w,
            "out_square": out_h == out_w and out_h > 0,
            "out_solid": out_solid,
            "out_color": out_color,
            "obj": obj,
            "objs": objs,
            "grid": g0.raw,
        })

    single_all = bool(per_pair) and all(p["single_object"] for p in per_pair)
    # A *solid* (single-colour) fill in every pair — the degenerate make_grid-only
    # render. The output need no longer be *square*: a scalar dimension reading
    # sizes a square (guarded per-pair by `out_square` below), while the
    # rectangular reading (`RECT_DIM_VOCAB`) sizes an `h × w` rectangle. Dropping
    # the square requirement here only *admits* the rectangle case; the scalar
    # paths re-impose `out_square` so an existing square task is classified exactly
    # as before.
    solid_all = bool(per_pair) and all(p["out_solid"] for p in per_pair)
    square_all = bool(per_pair) and all(p["out_square"] for p in per_pair)
    # The subject-COMM colour grounding (object-set COMM, collapsing to the single
    # object's colour). Holds for the single-object and the multi-object (count)
    # cases; for a single object subj_color == obj_color, so single-object
    # behaviour is unchanged. The *selected-object* subject grounds colour
    # differently (off the chosen object), computed during selector learning below.
    subj_color_all = bool(per_pair) and all(
        p["subj_color"] is not None and p["subj_color"] == p["out_color"]
        for p in per_pair)

    # Learn the dimension property: the first named scalar property whose value
    # equals the output side in every pair. The COMM between the property and the
    # output dimension is what *grounds* the size relation (P3/P4); it is
    # discovered, not assumed. Three subject forms are tried in order, the §2.5-2b
    # "which subject feeds the dimension argument" axis:
    #   1. the *single* object (per-object DIM_PROPERTY_VOCAB) — requires one
    #      object per pair; colour grounds on the subject COMM;
    #   2. the object *set* (grid-level GRID_DIM_PROPERTY_VOCAB, e.g. object_count)
    #      — colour grounds on the set COMM;
    #   3. a *selected* object among several (SELECTOR_VOCAB × DIM_PROPERTY_VOCAB)
    #      — the §2.1 multi-object case: the dimension is a property of *one chosen*
    #      object, so the subject is `select(...)`. This composes the two grown
    #      vocabularies (selection + dimension property): the lifted argument is
    #      `size_of(max_size(objects_of(in)))`. The selector and property are
    #      learned together (the first consistent pair across every example), and
    #      colour grounds on the *selected* object's colour — disjoint from the
    #      set COMM, which a multi-colour grid never grounds.
    # Subjects 1/2 are tried before 3 so a single-object task keeps resolving to
    # its plain object property (count there is always 1, the selector is never
    # reached); the selector path fires only when a single subject does not
    # account for the size, i.e. genuinely-multi-object tasks.
    # The first three subjects size a *square* (so they additionally require the
    # output to be square — `square_all` / the per-pair `out_square` guard). If
    # none accounts for the size, a fourth reading is tried: a *rectangular*
    # reading off the single object (`RECT_DIM_VOCAB`), whose value is the whole
    # ``(h, w)`` pair and which therefore admits a non-square output. It is tried
    # last so a square task keeps resolving to its scalar property (§2.5-2b "which
    # subject feeds the dimension argument", here extended to "and how many
    # dimensions it yields").
    dim_property = None
    selector = None
    color_all = False
    if solid_all:
        if square_all:
            for name, fn in DIM_PROPERTY_VOCAB.items():
                if all(
                    p["obj"] is not None and fn(p["obj"]) == p["out_h"]
                    for p in per_pair
                ):
                    dim_property = name
                    color_all = subj_color_all
                    break
            if dim_property is None:
                for name, fn in GRID_DIM_PROPERTY_VOCAB.items():
                    if all(fn(p["objs"]) == p["out_h"] for p in per_pair):
                        dim_property = name
                        color_all = subj_color_all
                        break
            if dim_property is None:
                for sel_name, sel_fn in SELECTOR_VOCAB.items():
                    for prop_name, prop_fn in DIM_PROPERTY_VOCAB.items():
                        ok = True
                        for p in per_pair:
                            chosen = sel_fn(p["objs"], p["grid"])
                            if (chosen is None
                                    or color_of(chosen) is None
                                    or prop_fn(chosen) != p["out_h"]
                                    or color_of(chosen) != p["out_color"]):
                                ok = False
                                break
                        if ok:
                            dim_property = prop_name
                            selector = sel_name
                            color_all = True  # off the selected object's colour
                            break
                    if selector is not None:
                        break
        if dim_property is None:
            # Rectangular reading: the canvas is the object's bbox extent
            # ``(h, w)``. Reproduces a *non-square* output (h ≠ w) that no scalar
            # square reading can. Colour grounds on the single object's colour
            # (the subject COMM), like the per-object scalar path.
            for name, fn in RECT_DIM_VOCAB.items():
                if all(
                    p["obj"] is not None
                    and tuple(fn(p["obj"])) == (p["out_h"], p["out_w"])
                    for p in per_pair
                ):
                    dim_property = name
                    color_all = subj_color_all
                    break

    return {
        "per_pair": per_pair,
        "single_object_all": single_all,
        "solid_output_all": solid_all,
        "color_preserved_all": color_all,
        "dim_property": dim_property,
        "selector": selector,
    }


# ---------------------------------------------------------------------------
# relation/analysis: did the single object simply move to a constant target?
# ---------------------------------------------------------------------------

def analyze_object_move(example_pairs: list) -> dict:
    """Per-pair object comparison + two cross-pair COMM readings on position.

    The arbor-flow easy000b path expressed symbolically: detect the single
    object in G0 and G1, observe that color and shape are preserved (COMM) while
    position differs (DIFF), then compare positions across pairs *two* ways:

    - **constant target** — every example puts the object at the *same* output
      anchor (the cross-pair COMM on the *absolute output position*). Solves the
      easy000c/d/h family.
    - **constant offset** — every example moves the object by the *same*
      displacement ``out_pos − in_pos`` (the cross-pair COMM on the *relative
      displacement*). Solves the easy000e/f family, where the absolute output
      anchor varies but the move vector does not.
    - **constant corner** — every example puts the object flush into the *same*
      grid corner (a *grid-relative* COMM: the absolute anchor varies, but it is
      always e.g. the bottom-right corner). Solves easy000g, where neither the
      absolute target nor the offset is constant but the corner is.
    - **output_dims** — every example's output grid has the *same* dimensions,
      a cross-pair COMM on the output canvas size. When that size *differs* from
      the input (size is *not* preserved), it is the learned argument that lets
      `make_grid` size a resized canvas (easy000i: 6×6 in → constant 5×5 out,
      object placed at a constant target on the resized canvas).

    These are sibling readings of the same per-pair DIFF: which one is constant
    is what distinguishes a fixed-target / fixed-offset / fixed-corner move. Grid
    size must be preserved for the same-canvas placement to be well-defined.

    Returns a symbolic dict; the matchers (agent/conditions/object_constant_target
    and object_constant_offset) decide whether they fire, and PredictOperator
    renders from it.
    """
    per_pair = []
    for pair in example_pairs:
        g0 = getattr(pair, "input_grid", None)
        g1 = getattr(pair, "output_grid", None)
        if g0 is None or g1 is None:
            continue
        in_obj = unique_object(g0.raw)
        out_obj = unique_object(g1.raw)
        single = in_obj is not None and out_obj is not None
        source = list(position_of(in_obj)) if in_obj else None
        target = list(position_of(out_obj)) if out_obj else None
        offset = (
            [target[0] - source[0], target[1] - source[1]]
            if single and source is not None and target is not None
            else None
        )
        out_corners = None
        if single and target is not None and g1.raw:
            oh, ow = extent_of(out_obj)
            out_corners = corners_matching(
                target, len(g1.raw), len(g1.raw[0]), oh, ow)
        out_dim = (
            [len(g1.raw), len(g1.raw[0]) if g1.raw else 0]
            if g1.raw is not None else None
        )
        per_pair.append({
            "single_object": single,
            "source": source,
            "target": target,
            "offset": offset,
            "out_corners": out_corners,
            "out_dim": out_dim,
            "color_preserved": bool(single and in_obj["colors"] == out_obj["colors"]),
            "shape_preserved": bool(single and normalized_shape(in_obj) == normalized_shape(out_obj)),
            "size_preserved": (
                len(g0.raw) == len(g1.raw)
                and (len(g0.raw[0]) if g0.raw else 0) == (len(g1.raw[0]) if g1.raw else 0)
            ),
        })

    single_all = bool(per_pair) and all(p["single_object"] for p in per_pair)
    color_all = bool(per_pair) and all(p["color_preserved"] for p in per_pair)
    shape_all = bool(per_pair) and all(p["shape_preserved"] for p in per_pair)
    size_all = bool(per_pair) and all(p["size_preserved"] for p in per_pair)

    targets = [tuple(p["target"]) for p in per_pair if p["target"] is not None]
    constant_target = (
        list(targets[0])
        if targets and all(t == targets[0] for t in targets)
        else None
    )

    offsets = [tuple(p["offset"]) for p in per_pair if p["offset"] is not None]
    constant_offset = (
        list(offsets[0])
        if offsets and len(offsets) == len(per_pair)
        and all(o == offsets[0] for o in offsets)
        else None
    )

    # A corner is constant only when *every* pair lands the object in some shared
    # corner — the intersection of each pair's matched corners. Deterministic
    # tie-break (sorted) keeps the chosen corner reproducible.
    corner_sets = [set(p["out_corners"]) for p in per_pair if p.get("out_corners")]
    constant_corner = None
    if corner_sets and len(corner_sets) == len(per_pair):
        common = set.intersection(*corner_sets)
        if common:
            constant_corner = sorted(common)[0]

    # Output canvas size as a cross-pair COMM. When every example's output grid
    # has the *same* dimensions, that constant size is itself a learnable argument
    # (a function of the example outputs, not of the test input) — the missing
    # piece for grids that *resize* between input and output (easy000i: 6×6 → a
    # constant 5×5). Read alongside (not instead of) size_preserved_all: the
    # resize reading is meaningful precisely when the size is *not* preserved.
    out_dims = [tuple(p["out_dim"]) for p in per_pair if p.get("out_dim")]
    output_dims = (
        list(out_dims[0])
        if out_dims and len(out_dims) == len(per_pair)
        and all(d == out_dims[0] for d in out_dims)
        else None
    )

    return {
        "per_pair": per_pair,
        "single_object_all": single_all,
        "color_preserved_all": color_all,
        "shape_preserved_all": shape_all,
        "size_preserved_all": size_all,
        "constant_target": constant_target,
        "constant_offset": constant_offset,
        "constant_corner": constant_corner,
        "output_dims": output_dims,
    }


# ---------------------------------------------------------------------------
# property vocabulary: a *colour reading* off a whole grid (the §2.5-2b colour
# hole filler)
# ---------------------------------------------------------------------------
#
# The dimension vocabularies above read a *scalar* off an object/grid to size a
# canvas. This axis is the colour analogue: a named reading that returns the
# *colour* a transformation should use, read off the input grid. It is the
# §2.5-2b "the choice that fills the variable hole comes from comparison
# (COMM/DIFF), not invention" point on the *colour* axis — the recolor families
# key the new colour on the source colour (`color_remap`) or a group's rank
# (`recolor_rank`); this keys it on a *grid-level colour property*. The seed is
# `most_frequent_color` (the grid's dominant colour), which is exactly
# `background_of`; naming it as a reading lets a transformation say "fill with the
# input's dominant colour" without a literal, so the same rule transfers across
# pairs whose dominant colour differs (the COMM is the *reading*, not the value).
#
# Like the dimension vocabularies, this is a named, deterministic vocabulary the
# analysis *learns from* (the first reading whose value reproduces the output side
# in every pair wins); it is util/property material (not a transformation), lives
# under agent/, and grows the LHS argument vocabulary (F3-exempt).

def most_frequent_color(grid: list) -> int:
    """The grid's most-frequent colour (ties → smallest) — the seed colour
    reading. Identical to `background_of`; named separately so it reads as a
    *colour argument* (`most_frequent_color(in)`) wherever a transformation needs
    a colour, not a canvas background."""
    return background_of(grid)


#: name -> fn(grid) -> int. A named *colour reading* off a whole grid, usable
#: wherever a transformation argument is a colour. Tried in this deterministic
#: order when *learning* which reading a task uses (the first whose value
#: reproduces the output colour in every pair wins). Adding one grows the LHS
#: argument vocabulary; it introduces no new transformation (F3-exempt).
COLOR_READING_VOCAB = {
    "most_frequent_color": most_frequent_color,
}


def analyze_canvas_fill(example_pairs: list) -> dict:
    """Output = a *solid canvas* (same size as input) whose fill colour is a
    learned colour-reading of the input (BACKLOG_LOOP §2.5-2b colour hole filler).

    The colour analogue of `analyze_object_size_grid`: there the output is a solid
    canvas whose *dimensions* are a learned object property; here the output is a
    solid canvas whose *colour* is a learned grid colour-reading, and the size is
    just the input's own (a size COMM). Solves the "fill the grid with its dominant
    colour" family (ARC-AGI-2 5582e5ca), which `color_remap` cannot — there every
    input colour would have to map to the one output colour, but across pairs the
    same source colour maps to different fills, so the map is not a function and
    `color_remap` abstains. The lifted argument is the *reading*
    (`most_frequent_color(in)`), not the literal fill colour, so one rule covers
    the family value-agnostically.

    Grounded in comparison, never assumed (P3/P4): every pair's output must be a
    solid single colour at the input's own size, and a named reading
    (`COLOR_READING_VOCAB`) whose value equals that output colour in *every* pair
    is discovered (the first consistent one), not chosen up front.

    Returns ``{fill_reading, consistent, evidence}``; ``fill_reading`` is None (so
    the `canvas_fill` matcher abstains) whenever any pair is not a same-size solid
    fill or no reading reproduces the colour across all pairs. The transformation
    bottoms out in a single frozen `make_grid` call (a uniform fill needs no
    `coloring`), the reading being the only argument (§2.5-1, F3).
    """
    per_pair = []
    for pair in example_pairs:
        g0 = getattr(pair, "input_grid", None)
        g1 = getattr(pair, "output_grid", None)
        if g0 is None or g1 is None:
            continue
        a = g0.raw or []
        b = g1.raw or []
        in_h = len(a)
        in_w = len(a[0]) if in_h else 0
        out_h = len(b)
        out_w = len(b[0]) if out_h else 0
        out_colors = {cell for row in b for cell in row}
        per_pair.append({
            "grid": a,
            "same_size": (in_h, in_w) == (out_h, out_w) and in_h > 0 and in_w > 0,
            "out_solid": len(out_colors) == 1 and out_h > 0 and out_w > 0,
            "out_color": next(iter(out_colors)) if len(out_colors) == 1 else None,
        })

    valid = bool(per_pair) and all(
        p["same_size"] and p["out_solid"] for p in per_pair)

    fill_reading = None
    if valid:
        for name, fn in COLOR_READING_VOCAB.items():
            if all(fn(p["grid"]) == p["out_color"] for p in per_pair):
                fill_reading = name
                break

    return {
        "fill_reading": fill_reading,
        "consistent": valid and fill_reading is not None,
        "evidence": len(per_pair),
    }


def analyze_color_remap(example_pairs: list) -> dict:
    """Cross-pair 1:1 colour-remap reading (the recolor family).

    The GRID-level (P2) relational reading of a *same-size* recolor: every cell's
    ``input_colour -> output_colour`` is recorded across all example pairs, and
    the map is well-defined only when each input colour maps to **exactly one**
    output colour everywhere — a function, the cross-pair COMM on the colour DIFF.
    Geometry is untouched, so the only learned content is the map itself, which is
    exactly the *argument expression* a `coloring(cells_of_colour(c), map[c])`
    composition consumes (BACKLOG_LOOP §2.5-1/2) — not a new transformation. Being
    a colour→colour COMM shared across pairs, two such rules lift cleanly under
    anti-unification (R3), unlike the legacy literal ``{type: color_mapping}``.

    Returns a symbolic dict ``{"color_map", "consistent", "evidence"}``; the
    ``color_remap`` matcher decides whether to fire and PredictOperator renders
    from a recomputed map (value-agnostic in geometry). ``color_map`` is None when
    the map is not a function, any pair changes grid size, or nothing changes
    (identity is not a recolor).
    """
    full = {}                 # src -> dst over *all* cells (must stay a function)
    consistent = True
    changed_pairs = 0
    for pair in example_pairs:
        g0 = getattr(pair, "input_grid", None)
        g1 = getattr(pair, "output_grid", None)
        if g0 is None or g1 is None:
            continue
        a, b = g0.raw, g1.raw
        if len(a) != len(b) or any(
            len(a[r]) != len(b[r]) for r in range(len(a))
        ):
            consistent = False
            continue
        pair_changed = False
        for r in range(len(a)):
            for c in range(len(a[r])):
                s, d = a[r][c], b[r][c]
                if s in full and full[s] != d:
                    consistent = False
                else:
                    full[s] = d
                if s != d:
                    pair_changed = True
        if pair_changed:
            changed_pairs += 1

    # Keep only the non-identity entries: colours that map to themselves are not
    # part of the recolor's content (they are the implicit identity default the
    # renderer leaves untouched).
    color_map = {s: d for s, d in full.items() if s != d}
    if not consistent or not color_map:
        color_map = None

    return {
        "color_map": color_map,
        "consistent": consistent,
        "evidence": changed_pairs,
    }


# ---------------------------------------------------------------------------
# selection vocabulary: rank-by-position (the §2.5-2b ranking selector)
# ---------------------------------------------------------------------------
#
# The recolor families split on *what names the new colour*. `analyze_color_remap`
# above keys on the source colour (a 1:1 map). This one keys on an object's
# *rank among its peers* — the changed groups are ordered by position and painted
# a contiguous sequence (1, 2, 3, …). The lifted argument is therefore a *ranking
# selector* (`rank-by(top_row)` / `rank-by(top_col)` — `argsort` in the selection
# vocabulary), distinct from the constant maps/targets/offsets the other families
# carry and the first ordinal selector here (R4-adjacent: a derived "which is
# n-th" property). It is util/selection material (not a transformation), so it
# lives here under `agent/`, not the frozen DSL dir (§2.5-1, F3).

def _changed_cell_groups(grid_in: list, grid_out: list) -> list:
    """4-connected components of the cells that differ between two equal-size
    grids. Returns a list of components, each a list of ``(row, col)``."""
    changed = [
        (r, c)
        for r in range(len(grid_in))
        for c in range(len(grid_in[r]))
        if grid_in[r][c] != grid_out[r][c]
    ]
    cell_set = set(changed)
    visited = set()
    groups = []
    for start in changed:
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
        groups.append(comp)
    return groups


#: Position keys a ranking selector may order changed groups by, in deterministic
#: trial order. The first that yields a sequential colour assignment across every
#: example pair is the learned selector.
RANK_KEYS = ("top_row", "top_col")


def analyze_recolor_rank(example_pairs: list) -> dict:
    """Cross-pair *rank-based* sequential recolor reading (the recolor-rank family).

    The sibling of `analyze_color_remap`: there the new colour is a function of the
    *source colour* (a 1:1 map); here it is a function of the changed group's
    *rank among its peers*. Per pair the changed cells form ``k`` same-coloured
    groups, each repainted to one output colour, and those output colours are a
    contiguous run (``start, start+1, …``); across pairs the *same* position key
    (`top_row` / `top_col`) orders the groups into that run. That ordering is the
    lifted argument — a `rank-by(position)` selector (§2.5-2b) — value-agnostic in
    the absolute colours, positions and group count, so two such rules share a
    skeleton and lift under anti-unification (R3), unlike the legacy literal
    ``{type: recolor_sequential}`` envelope this replaces.

    Grounded in comparison, never assumed (P3/P4): the groups come from the
    input↔output DIFF, the sequence is read off the output colours, and the
    ordering key is *discovered* (the first consistent one), not chosen up front.

    Returns ``{sort_key, start_color, source_colors, consistent, evidence}``;
    ``sort_key`` is None (so the `recolor_rank` matcher abstains) whenever any pair
    resizes, a group is not single-coloured on either side, the output colours are
    not a contiguous run, or no position key orders them consistently across pairs.
    The detection mirrors the legacy ``_try_recolor_sequential`` exactly so the
    save-gate verdict is preserved; only the *form* (canonical, condition-bearing)
    changes.
    """
    per_pair = []
    consistent = True
    for pair in example_pairs:
        g0 = getattr(pair, "input_grid", None)
        g1 = getattr(pair, "output_grid", None)
        if g0 is None or g1 is None:
            continue
        a, b = g0.raw, g1.raw
        if len(a) != len(b) or any(len(a[r]) != len(b[r]) for r in range(len(a))):
            consistent = False
            per_pair.append(None)
            continue
        groups = _changed_cell_groups(a, b)
        recs = []
        ok = True
        for comp in groups:
            in_cols = {a[r][c] for (r, c) in comp}
            out_cols = {b[r][c] for (r, c) in comp}
            if len(in_cols) != 1 or len(out_cols) != 1:
                ok = False
                break
            recs.append({
                "in_color": next(iter(in_cols)),
                "out_color": next(iter(out_cols)),
                "top_row": min(r for r, _c in comp),
                "top_col": min(c for _r, c in comp),
            })
        per_pair.append(recs if ok else None)

    sort_key = None
    start_color = None
    source_colors = []
    valid = bool(per_pair) and all(p is not None for p in per_pair)
    if valid:
        counts = {len(p) for p in per_pair}
        if len(counts) == 1 and 0 not in counts:
            for key in RANK_KEYS:
                ok_key = True
                for p in per_pair:
                    ordered = sorted(p, key=lambda g: g[key])
                    cols = [g["out_color"] for g in ordered]
                    if cols != list(range(cols[0], cols[0] + len(cols))):
                        ok_key = False
                        break
                if ok_key:
                    sort_key = key
                    break
    if sort_key is not None:
        start_color = min(g["out_color"] for g in per_pair[0])
        srcs = set()
        for p in per_pair:
            for g in p:
                srcs.add(g["in_color"])
        source_colors = sorted(srcs)

    return {
        "sort_key": sort_key,
        "start_color": start_color,
        "source_colors": source_colors,
        "consistent": consistent and sort_key is not None,
        "evidence": len([p for p in per_pair if p is not None]),
    }


# ---------------------------------------------------------------------------
# selection vocabulary: multi-object *selective* recolor (the §2.5-2b selection
# lift, on the recolor axis)
# ---------------------------------------------------------------------------
#
# This composes the two grown vocabularies the way `analyze_object_size_grid`'s
# selected-object branch does, but on the *recolor* transformation rather than
# canvas sizing. It is the recolor-axis sibling of `analyze_object_select_move`
# (move → recolor) and the multi-object converse of `analyze_color_remap`:
#
#   * `analyze_color_remap` reads a *global* 1:1 colour map — every cell of a
#     source colour is repainted. It structurally CANNOT express "recolour only
#     *one* of two same-coloured objects": that source colour would map to two
#     different output colours, so the map is not a function and color_remap
#     abstains (the matcher's own `consistent` gate). The selective recolor lives
#     exactly in that blind spot.
#   * The crux is therefore *which* object is repainted — the §2.1 "multi-object
#     selection" concept, whose content is the *selector* (`max_size`/`min_size`/
#     `unique_color`/`unique_shape`/`border_object` — the shared SELECTOR_VOCAB).
#     The selector is *learned from comparison* (which object's cells changed),
#     never assumed (P3/P4).
#
# Value-agnostic at predict: the selector and the new colour are recomputed from
# the example pairs, so the emitted rule carries empty action args and one rule
# covers the whole family (it merges by condition+action equivalence, like
# `place_object_constant`, rather than accreting one literal rule per task —
# §2.5-3/4). The transformation bottoms out in a single frozen `coloring` call
# (render.render_object_recolor); no new transformation is introduced (F3).

def analyze_object_select_recolor(example_pairs: list) -> dict:
    """Multi-object selective recolor (BACKLOG_LOOP §2.5-2b / §2.1 multi-object
    selection, R1).

    Fires for: a *same-size* grid holding several objects in which exactly **one**
    input object's cells are repainted to a single new colour, that object being
    the one a learned `SELECTOR_VOCAB` criterion consistently picks across every
    pair, and the new colour being constant across pairs (the cross-pair COMM on
    the recolored object's output colour). The selected object's *shape and
    position* are unchanged — only its colour — so this is disjoint from the move
    families (which displace) and from `color_remap` (which would repaint every
    same-coloured cell).

    Grounded in comparison, never assumed (P3/P4):

    1. Per pair, the changed cells are computed (input↔output DIFF) and must equal
       the cells of exactly one input object — *which* object was recolored,
       identified by comparison.
    2. Across pairs, the first named selector that picks that recolored object in
       *every* pair is the lifted argument (value-agnostic in colour, position and
       the non-selected distractors).
    3. The new colour is either *constant* across pairs (a cross-pair COMM) or a
       *reading* off another object — the selected object painted the colour of the
       object a learned donor selector picks (`color_reading`), used when the
       constant reading abstains. Both are recomputed at predict time, so the rule
       is value-agnostic in the actual colour; the donor is the colour-argument
       analogue of the selector lift (§2.5-2b).

    Returns a symbolic dict; the `object_select_recolor` matcher (agent/conditions/)
    decides firing and PredictOperator renders from it. Stays inert (valid_all
    False / selector None) on single-object grids and on global-recolor grids, so
    it never perturbs the other families.
    """
    per_pair = []
    for pair in example_pairs:
        g0 = getattr(pair, "input_grid", None)
        g1 = getattr(pair, "output_grid", None)
        if g0 is None or g1 is None:
            continue
        a = g0.raw or []
        b = g1.raw or []
        same = (len(a) == len(b)
                and all(len(a[r]) == len(b[r]) for r in range(len(a)))
                and len(a) > 0)
        objs = objects_of(a) if same else []
        recolored = None
        new_color = None
        ok = False
        if same and len(objs) >= 2:
            changed = {
                (r, c)
                for r in range(len(a))
                for c in range(len(a[r]))
                if a[r][c] != b[r][c]
            }
            new_cols = {b[r][c] for (r, c) in changed}
            if changed and len(new_cols) == 1:
                nc = next(iter(new_cols))
                target = next(
                    (o for o in objs if set(map(tuple, o["cells"])) == changed),
                    None,
                )
                if target is not None:
                    recolored = target
                    new_color = nc
                    ok = True
        per_pair.append({
            "ok": ok,
            "objs": objs,
            "grid": a,
            "recolored": recolored,
            "new_color": new_color,
        })

    valid = bool(per_pair) and all(p["ok"] for p in per_pair)

    # The new colour as a cross-pair COMM: the same colour in every pair, else the
    # reading is not value-agnostically learnable and the constant path abstains.
    new_colors = [p["new_color"] for p in per_pair if p["new_color"] is not None]
    constant_new_color = (
        new_colors[0]
        if valid and new_colors and all(nc == new_colors[0] for nc in new_colors)
        else None
    )

    # Learn the selector: the first named criterion that picks the recolored object
    # in every pair (grounded in step 1's comparison, never assumed).
    selector = None
    if valid:
        for name, fn in SELECTOR_VOCAB.items():
            ok_sel = True
            for p in per_pair:
                chosen = fn(p["objs"], p["grid"])
                if chosen is None or chosen["cells"] != p["recolored"]["cells"]:
                    ok_sel = False
                    break
            if ok_sel:
                selector = name
                break

    # Learn the new colour as a *reading* off another object (the §2.5-2b colour
    # hole filler on the selection axis). When the new colour is NOT constant across
    # pairs, it may still be value-agnostically determined: the selected object is
    # painted the colour of the object a *donor* selector (a different
    # `SELECTOR_VOCAB` criterion) picks. This is the colour-argument analogue of the
    # selector lift — where the selector names *which* object changes, the donor
    # names *what colour* it becomes, both read from comparison (another object's
    # colour), neither a literal (P3/P4). It is the same COMM the constant case uses
    # (the recolored object's output colour), only here that colour equals a donor
    # object's colour in every pair rather than being fixed. Learned *only* when the
    # constant reading abstains, so an existing constant-colour task is unchanged;
    # the first consistent donor wins. The donor that picks the recolored object
    # itself can never qualify (its colour is the *source*, not the new colour, so
    # the recolour would be a no-op — already excluded by `changed`), so a genuine
    # donor is always a different object.
    color_reading = None
    if valid and constant_new_color is None and selector is not None:
        for name, fn in SELECTOR_VOCAB.items():
            ok_donor = True
            for p in per_pair:
                donor = fn(p["objs"], p["grid"])
                if (donor is None
                        or color_of(donor) is None
                        or color_of(donor) != p["new_color"]):
                    ok_donor = False
                    break
            if ok_donor:
                color_reading = name
                break

    return {
        "per_pair": per_pair,
        "valid_all": valid,
        "selector": selector,
        "new_color": constant_new_color,
        "color_reading": color_reading,
    }


# ----------------------------------------------------------------------
# Geometric-transform vocabulary (BACKLOG_LOOP §2.5-1: an *argument expression*
# tree over the frozen `coloring` primitive, NOT a new transformation primitive).
#
# A flip/rotation/transpose is *not* a new DSL primitive (F3 forbids that). It is
# the frozen `coloring` primitive applied at a *transformed coordinate* — exactly
# the "rotate/flip = coloring with a coordinate-mapping expression" worked example
# in BACKLOG_LOOP §2.5-1. The whole content of such a task is which coordinate
# permutation maps input→output; that permutation is the lifted *argument*, here
# named in a small deterministic vocabulary the way SELECTOR_VOCAB names object
# selectors. Each entry is a pure coordinate bijection (input cell -> output cell)
# plus the output dimensions; recognition and render share these maps, so they can
# never disagree. `render.render_geometric_transform` composes the chosen map with
# `make_grid` + `coloring`; this module only *recognises* which one fits.
# ----------------------------------------------------------------------

#: name -> (row, col, H, W) -> (row', col') output coordinate of an input cell.
GEO_COORD = {
    "flip_h": lambda r, c, H, W: (r, W - 1 - c),
    "flip_v": lambda r, c, H, W: (H - 1 - r, c),
    "rot180": lambda r, c, H, W: (H - 1 - r, W - 1 - c),
    "transpose": lambda r, c, H, W: (c, r),
    "anti_transpose": lambda r, c, H, W: (W - 1 - c, H - 1 - r),
    "rot90": lambda r, c, H, W: (c, H - 1 - r),
    "rot270": lambda r, c, H, W: (W - 1 - c, r),
}

#: name -> (H, W) -> (H', W') output dimensions (transpose/rotations swap axes).
GEO_DIMS = {
    "flip_h": lambda H, W: (H, W),
    "flip_v": lambda H, W: (H, W),
    "rot180": lambda H, W: (H, W),
    "transpose": lambda H, W: (W, H),
    "anti_transpose": lambda H, W: (W, H),
    "rot90": lambda H, W: (W, H),
    "rot270": lambda H, W: (W, H),
}

#: deterministic recognition order (vocab order breaks ties on symmetric grids).
GEOMETRIC_VOCAB = list(GEO_COORD)


def apply_geometric(grid: list, name: str) -> list:
    """Apply the named coordinate bijection to `grid`, returning a fresh grid.

    Pure recognition helper (no frozen-primitive bookkeeping): every cell is
    relocated to its mapped coordinate. Because each `GEO_COORD` map is a
    bijection onto the `GEO_DIMS` output rectangle, every output cell is written
    exactly once. `render.render_geometric_transform` produces the identical grid
    via `make_grid` + `coloring`; they share `GEO_COORD`/`GEO_DIMS` so they agree
    by construction.
    """
    H = len(grid)
    W = len(grid[0]) if H else 0
    if name not in GEO_COORD or H == 0 or W == 0:
        return [row[:] for row in grid]
    Ho, Wo = GEO_DIMS[name](H, W)
    cm = GEO_COORD[name]
    out = [[0] * Wo for _ in range(Ho)]
    for r in range(H):
        for c in range(W):
            rr, cc = cm(r, c, H, W)
            out[rr][cc] = grid[r][c]
    return out


def analyze_geometric_transform(example_pairs: list) -> dict:
    """Whole-grid geometric transform (BACKLOG_LOOP §2.5-1 worked example).

    Fires for: a single named coordinate permutation from `GEOMETRIC_VOCAB`
    (flip_h/flip_v/rot90/rot180/rot270/transpose/anti_transpose) that reproduces
    *every* example output from its input exactly, with at least one pair where
    input ≠ output (a genuine transform, not the identity). The transform name is
    the lifted *argument* — value-, colour-, shape- and size-agnostic — recomputed
    at predict time, so one rule covers the whole family rather than one literal
    rule per task (§2.5-3/4). The transformation bottoms out in the frozen
    `coloring` primitive applied at the mapped coordinate (§2.5-1, F3): a
    flip/rotation is `coloring` with a coordinate-mapping expression, not a new
    primitive.

    Grounded in comparison, never assumed (P3/P4): a transform is admitted only if
    `apply_geometric(input, name)` equals the output for every pair — the COMM
    between the predicted and actual output grids. Returns a symbolic dict; the
    `geometric_transform` matcher (agent/conditions/) decides firing and
    PredictOperator renders from it. Stays inert (transform None) whenever no single
    map reproduces all pairs, so it never perturbs the other families.
    """
    pairs = []
    for pair in example_pairs:
        g0 = getattr(pair, "input_grid", None)
        g1 = getattr(pair, "output_grid", None)
        if g0 is None or g1 is None:
            continue
        a = g0.raw or []
        b = g1.raw or []
        if a and b:
            pairs.append((a, b))

    transform = None
    if pairs and any(a != b for a, b in pairs):
        for name in GEOMETRIC_VOCAB:
            if all(apply_geometric(a, name) == b for a, b in pairs):
                transform = name
                break

    return {
        "transform": transform,
        "valid_all": transform is not None,
        "evidence": len(pairs),
    }
