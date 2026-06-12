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
    """Per-pair object comparison + the cross-pair COMM on the output position.

    The arbor-flow easy000b path expressed symbolically: detect the single
    object in G0 and G1, observe that color and shape are preserved (COMM) while
    position differs (DIFF), then compare the *output* positions across pairs.
    When every example puts the object at the *same* output anchor, that anchor
    is a constant target (the cross-pair COMM). Grid size must be preserved for
    the same-canvas placement to be well-defined.

    Returns a symbolic dict; the matcher (agent/conditions/object_constant_target)
    decides whether it fires, and PredictOperator renders from it.
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
        per_pair.append({
            "single_object": single,
            "target": list(position_of(out_obj)) if out_obj else None,
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
    constant = (
        list(targets[0])
        if targets and all(t == targets[0] for t in targets)
        else None
    )

    return {
        "per_pair": per_pair,
        "single_object_all": single_all,
        "color_preserved_all": color_all,
        "shape_preserved_all": shape_all,
        "size_preserved_all": size_all,
        "constant_target": constant,
    }
