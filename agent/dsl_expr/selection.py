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
    solid_all = bool(per_pair) and all(
        p["out_solid"] and p["out_square"] for p in per_pair)
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
    dim_property = None
    selector = None
    color_all = False
    if solid_all:
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
                        color_all = True  # grounded on the selected object's colour
                        break
                if selector is not None:
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
