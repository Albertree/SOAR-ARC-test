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
        per_pair.append({
            "single_object": single,
            "source": source,
            "target": target,
            "offset": offset,
            "out_corners": out_corners,
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

    return {
        "per_pair": per_pair,
        "single_object_all": single_all,
        "color_preserved_all": color_all,
        "shape_preserved_all": shape_all,
        "size_preserved_all": size_all,
        "constant_target": constant_target,
        "constant_offset": constant_offset,
        "constant_corner": constant_corner,
    }
