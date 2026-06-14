"""
Tests for R1's object-level move capability (BACKLOG_LOOP.md R1, §2.5-2b):

  * the seed selection vocabulary (agent/dsl_expr.selection),
  * the target-expression fitter (agent/dsl_expr.motion: corner / constant /
    translation), fitted from the example comparison — not a literal,
  * the `object_motion` condition matcher,
  * end-to-end: ExtractPattern -> Generalize -> Predict solves the whole move
    family (easy000c/g corner, easy000d/h constant, easy000e/f translation) with
    ONE value-agnostic rule, built only from make_grid + coloring.
"""

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agent.dsl_expr import (
    objects_of, unique_object, select_object, fit_selector,
    bottom_right_of, color_of,
    fit_target, target_position, fit_output_shape, output_shape,
)
from agent.conditions import match as match_condition
from agent.active_operators import (
    ExtractPatternOperator,
    GeneralizeOperator,
    PredictOperator,
)


# --- selection vocabulary --------------------------------------------------

def test_objects_of_single_pixel():
    grid = [[0, 0, 0], [0, 2, 0], [0, 0, 0]]
    objs = objects_of(grid)
    assert len(objs) == 1
    obj = unique_object(objs)
    assert obj is not None
    assert obj["size"] == 1
    assert color_of(obj) == 2
    assert bottom_right_of(obj) == (1, 1)


def test_objects_of_counts_components():
    grid = [[2, 0, 0], [0, 0, 0], [0, 0, 3]]
    objs = objects_of(grid)
    assert len(objs) == 2
    assert unique_object(objs) is None  # not unique


# --- target-expression fitter ----------------------------------------------

def _m(src, dst, H=6, W=6, oh=1, ow=1):
    return {"src": src, "dst": dst, "H": H, "W": W, "oh": oh, "ow": ow}


def test_fit_corner():
    # both objects land flush bottom-right (H-1, W-1) of their grids
    desc = fit_target([_m((1, 1), (5, 5)), _m((1, 4), (5, 5))])
    assert desc == {"kind": "bottom_right"}


def test_fit_corner_varying_grid_sizes():
    desc = fit_target([_m((1, 1), (3, 3), H=4, W=4), _m((1, 4), (2, 4), H=3, W=5)])
    assert desc == {"kind": "bottom_right"}


def test_fit_constant():
    # both land at the same absolute (1,2); deltas differ so it is not an offset
    desc = fit_target([_m((1, 1), (1, 2)), _m((1, 4), (1, 2))])
    assert desc == {"kind": "constant", "pos": [1, 2]}


def test_fit_offset():
    # constant translation (+1, -1); destinations differ so it is not constant
    desc = fit_target([_m((1, 1), (2, 0)), _m((1, 4), (2, 3))])
    assert desc == {"kind": "offset", "delta": [1, -1]}


def test_fit_none_when_inconsistent():
    assert fit_target([_m((1, 1), (2, 0)), _m((1, 4), (4, 4))]) is None


def test_target_position_roundtrip():
    obj = unique_object(objects_of([[0, 0, 0], [0, 5, 0], [0, 0, 0]]))
    assert target_position({"kind": "bottom_right"}, (3, 3), obj) == (2, 2)
    assert target_position({"kind": "offset", "delta": [1, -1]}, (3, 3), obj) == (2, 0)
    assert target_position({"kind": "constant", "pos": [0, 2]}, (3, 3), obj) == (0, 2)


# --- edge target (to_edge): the canonical gravity / fall pattern --------------

def test_fit_to_edge_bottom():
    # objects fall to the bottom edge keeping their column; start rows and columns
    # vary so neither bottom_right (column not snapped to W-ow), offset (fall
    # distance differs) nor constant (destinations differ) can explain it.
    desc = fit_target([
        _m((0, 1), (4, 1), oh=2, ow=2),
        _m((1, 3), (4, 3), oh=2, ow=2),
        _m((0, 0), (4, 0), oh=2, ow=2),
    ])
    assert desc == {"kind": "to_edge", "edge": "bottom"}


def test_fit_to_edge_each_axis():
    assert fit_target([_m((1, 2), (0, 2)), _m((3, 4), (0, 4))]) == \
        {"kind": "to_edge", "edge": "top"}
    assert fit_target([_m((1, 2), (1, 0)), _m((3, 4), (3, 0))]) == \
        {"kind": "to_edge", "edge": "left"}
    # right edge: free row kept, column flush to W-ow (=5 for ow=1, W=6)
    assert fit_target([_m((1, 2), (1, 5)), _m((3, 4), (3, 5))]) == \
        {"kind": "to_edge", "edge": "right"}


def test_fit_to_edge_loses_to_simpler_corner():
    # when the object also lands flush bottom-right, the corner reading wins:
    # to_edge is tried only after bottom_right (more structural, both axes).
    desc = fit_target([_m((1, 1), (5, 5)), _m((1, 4), (5, 5))])
    assert desc == {"kind": "bottom_right"}


def test_fit_to_edge_declines_static():
    # an unmoved object already at the bottom must not be claimed as a *fall*:
    # the `any(... moved)` guard keeps to_edge out, so the static set falls
    # through to the trivial offset reading (delta 0,0), never to_edge.
    desc = fit_target([_m((4, 1), (4, 1), oh=2, ow=2)])
    assert desc.get("kind") != "to_edge"


def test_target_position_to_edge():
    obj = unique_object(objects_of([[0, 0, 0], [0, 5, 0], [0, 0, 0]]))  # bbox (1,1)
    assert target_position({"kind": "to_edge", "edge": "bottom"}, (3, 3), obj) == (2, 1)
    assert target_position({"kind": "to_edge", "edge": "top"}, (3, 3), obj) == (0, 1)
    assert target_position({"kind": "to_edge", "edge": "left"}, (3, 3), obj) == (1, 0)
    assert target_position({"kind": "to_edge", "edge": "right"}, (3, 3), obj) == (1, 2)


# --- relational target (to_anchor): the destination is another object's position --

def _pix(r, c, color=4):
    # minimal single-pixel object dict — enough for position_of / the selectors
    return {"bbox": (r, c, r, c), "size": 1, "color_set": [color],
            "cells": frozenset([(r, c)]), "pixels": {(r, c): color}}


def _blob(r0, c0, h, w, color=2):
    # minimal h x w rectangular object dict at (r0, c0) — a larger anchor candidate
    cells = frozenset((r0 + dr, c0 + dc) for dr in range(h) for dc in range(w))
    return {"bbox": (r0, c0, r0 + h - 1, c0 + w - 1), "size": h * w,
            "color_set": [color], "cells": cells,
            "pixels": {p: color for p in cells}}


def test_fit_to_anchor():
    # Both the mover and its single anchor sit at varying positions, so neither
    # bottom_right, offset nor constant fits; the destination equals the anchor's
    # position on every pair -> the relational `to_anchor` target (§2.5-1). With a
    # single other object the fitted anchor selector is the degenerate `unique`.
    motions = [
        {"src": (0, 0), "dst": (3, 4), "H": 6, "W": 6, "oh": 2, "ow": 2,
         "others": [(3, 4)], "other_objs": [_pix(3, 4)]},
        {"src": (4, 4), "dst": (1, 1), "H": 6, "W": 6, "oh": 2, "ow": 2,
         "others": [(1, 1)], "other_objs": [_pix(1, 1)]},
    ]
    assert fit_target(motions) == {"kind": "to_anchor",
                                   "anchor": {"kind": "unique"}}


def test_fit_to_anchor_selects_among_several_others():
    # §2.5-2b lift: several other objects per pair, so naming the anchor needs a
    # *selector* over them. Here the anchor is the LARGEST other (a blob) and the
    # distractor is a single pixel; the destination equals the blob's top-left on
    # every pair, so the fitted anchor selector is `largest`.
    motions = [
        {"src": (0, 0), "dst": (3, 4), "H": 8, "W": 8, "oh": 2, "ow": 2,
         "others": [(3, 4), (7, 7)],
         "other_objs": [_blob(3, 4, 1, 3), _pix(7, 7)]},
        {"src": (6, 6), "dst": (1, 1), "H": 8, "W": 8, "oh": 2, "ow": 2,
         "others": [(1, 1), (5, 7)],
         "other_objs": [_blob(1, 1, 1, 3), _pix(5, 7)]},
    ]
    assert fit_target(motions) == {"kind": "to_anchor",
                                   "anchor": {"kind": "largest"}}


def test_fit_to_anchor_loses_to_simpler_readings():
    # to_anchor is tried LAST: when a constant also fits (every dst the same and
    # equal to the anchor), the more-structural reading wins, never to_anchor.
    motions = [
        {"src": (0, 0), "dst": (1, 1), "H": 6, "W": 6, "oh": 1, "ow": 1,
         "others": [(1, 1)]},
        {"src": (4, 4), "dst": (1, 1), "H": 6, "W": 6, "oh": 1, "ow": 1,
         "others": [(1, 1)]},
    ]
    assert fit_target(motions) == {"kind": "constant", "pos": [1, 1]}


def test_fit_to_anchor_declines_without_object_material():
    # the anchor selector needs the full other-object dicts (`other_objs`) to run
    # the selection vocabulary; with only positions (`others`) and no `other_objs`
    # it cannot fit a selector and declines rather than guessing.
    motions = [
        {"src": (0, 0), "dst": (3, 4), "H": 6, "W": 6, "oh": 2, "ow": 2,
         "others": [(3, 4), (5, 5)]},
        {"src": (4, 4), "dst": (1, 1), "H": 6, "W": 6, "oh": 2, "ow": 2,
         "others": [(1, 1), (0, 0)]},
    ]
    assert fit_target(motions) is None


def test_fit_to_anchor_declines_when_dst_matches_no_other():
    # the destination sits on no other object on some pair -> there is no anchor to
    # name, so to_anchor declines (and so does every earlier reading).
    motions = [
        {"src": (0, 0), "dst": (3, 4), "H": 8, "W": 8, "oh": 2, "ow": 2,
         "others": [(7, 7)], "other_objs": [_pix(7, 7)]},
        {"src": (6, 6), "dst": (1, 1), "H": 8, "W": 8, "oh": 2, "ow": 2,
         "others": [(5, 5)], "other_objs": [_pix(5, 5)]},
    ]
    assert fit_target(motions) is None


def test_target_position_to_anchor():
    # a 2x2 mover and one anchor pixel -> the destination is the anchor's top-left
    grid = [[3, 3, 0, 0],
            [3, 3, 0, 0],
            [0, 0, 0, 4],
            [0, 0, 0, 0]]
    objs = objects_of(grid)
    mover = max(objs, key=lambda o: o["size"])
    assert target_position({"kind": "to_anchor"}, (4, 4), mover, objs) == (2, 3)
    # declines without the object list (the fast path's input-only interface)...
    assert target_position({"kind": "to_anchor"}, (4, 4), mover) is None
    # ...and when the anchor is not uniquely determined (more than one other)
    grid2 = [[3, 3, 0, 4],
             [3, 3, 0, 0],
             [0, 0, 0, 0],
             [5, 0, 0, 0]]
    objs2 = objects_of(grid2)
    mover2 = max(objs2, key=lambda o: o["size"])
    assert target_position({"kind": "to_anchor"}, (4, 4), mover2, objs2) is None


# --- output-shape fitter ---------------------------------------------------

def _s(in_dims, out_dims):
    return {"in": in_dims, "out": out_dims}


def test_fit_output_shape_same():
    assert fit_output_shape([_s((6, 6), (6, 6)), _s((4, 5), (4, 5))]) == {"kind": "same"}


def test_fit_output_shape_delta():
    # every output is the input shrunk by (1, 1) — easy000i's resize, fitted as a
    # relation (most-structural) rather than a coincidental constant.
    assert fit_output_shape([_s((6, 6), (5, 5)), _s((6, 6), (5, 5))]) == {
        "kind": "delta", "delta": [-1, -1]
    }


def test_fit_output_shape_constant():
    # outputs are a fixed size that is NOT a constant offset from the inputs.
    assert fit_output_shape([_s((6, 6), (5, 5)), _s((4, 4), (5, 5))]) == {
        "kind": "constant", "dims": [5, 5]
    }


def test_fit_output_shape_none_when_inconsistent():
    assert fit_output_shape([_s((6, 6), (5, 5)), _s((6, 6), (4, 4))]) is None


def test_output_shape_roundtrip():
    assert output_shape({"kind": "same"}, (6, 6)) == (6, 6)
    assert output_shape({"kind": "delta", "delta": [-1, -1]}, (6, 6)) == (5, 5)
    assert output_shape({"kind": "constant", "dims": [5, 5]}, (7, 7)) == (5, 5)


def _so(in_dims, out_dims, obj_dims):
    return {"in": in_dims, "out": out_dims, "obj": obj_dims}


def test_fit_output_shape_object_extent():
    # A crop whose object differs in size across pairs: delta and constant both
    # fail, so the output size is read as the object's own bbox extent (§2.1
    # "grid size is a function of an object's feature").
    assert fit_output_shape([
        _so((5, 5), (2, 3), (2, 3)),
        _so((5, 5), (3, 2), (3, 2)),
    ]) == {"kind": "object_extent"}


def test_object_extent_loses_to_input_relative_readings():
    # When an input-relative reading also fits, it wins (most-structural-first):
    # object_extent is the last resort, never overriding `same`/`delta`/`constant`.
    same = [_so((4, 4), (4, 4), (4, 4)), _so((6, 6), (6, 6), (6, 6))]
    assert fit_output_shape(same) == {"kind": "same"}


def test_output_shape_object_extent_needs_obj():
    obj = {"bbox": (1, 1, 2, 3)}  # 2 rows × 3 cols
    assert output_shape({"kind": "object_extent"}, (5, 5), obj) == (2, 3)
    # No object supplied → decline rather than crash.
    assert output_shape({"kind": "object_extent"}, (5, 5)) is None


def _sc(in_dims, out_dims, count):
    return {"in": in_dims, "out": out_dims, "count": count}


def test_fit_output_shape_object_count():
    # Same input size both pairs but differing object counts (3, 4): the output
    # side tracks the count, which no input-relative or extent reading explains.
    assert fit_output_shape([
        _sc((5, 5), (3, 3), 3),
        _sc((5, 5), (4, 4), 4),
    ]) == {"kind": "object_count"}


def test_object_count_loses_to_input_relative_readings():
    # object_count is tried last: an input-relative reading wins when one also fits.
    same = [_sc((4, 4), (4, 4), 4), _sc((6, 6), (6, 6), 6)]
    assert fit_output_shape(same) == {"kind": "same"}


def test_fit_output_shape_object_count_declines_non_square():
    # A non-square output is not a count×count square → object_count declines.
    assert fit_output_shape([
        _sc((5, 5), (3, 4), 3),
        _sc((5, 5), (4, 5), 4),
    ]) is None


def test_output_shape_object_count_needs_count():
    assert output_shape({"kind": "object_count"}, (5, 5), None, 4) == (4, 4)
    # No count supplied → decline rather than crash.
    assert output_shape({"kind": "object_count"}, (5, 5)) is None


# --- matcher ---------------------------------------------------------------

def _motion(n=2, target=None, out_shape=None, selector=None, scene="drop",
            **overrides):
    pair = {
        "scene": scene, "selected_ok": True,
        "color_preserved": True, "size_preserved": True,
        "grid_size_preserved": True,
    }
    pair.update(overrides)
    return {"object_motion": {
        "evidence_count": n,
        "pairs": [dict(pair) for _ in range(n)],
        "selector": selector if selector is not None else {"kind": "unique"},
        "target": target if target is not None else {"kind": "bottom_right"},
        "out_shape": out_shape if out_shape is not None else {"kind": "same"},
        "scene": scene,
    }}


def test_matcher_fires_with_target():
    assert match_condition("object_motion", _motion(2)) is True


def test_matcher_declines_without_out_shape():
    p = _motion(2)
    p["object_motion"]["out_shape"] = None
    assert match_condition("object_motion", p) is False


def test_matcher_accepts_single_fully_determined_pair():
    # §2.1 "example pairs ≠ 2": a single pair from which a consistent selector +
    # target + out_shape + scene all fit is admissible evidence (floor lowered to
    # 1 for the transformation matchers — the minimal-assumption read of one
    # example). The fit functions upstream still have to produce the expressions.
    assert match_condition("object_motion", _motion(1)) is True


def test_matcher_declines_zero_pairs():
    assert match_condition("object_motion", _motion(0)) is False


def test_matcher_floor_two_still_honoured_when_requested():
    # An explicit higher floor is still respected (a caller may demand ≥2).
    assert match_condition(
        "object_motion", _motion(1), {"min_evidence": 2}
    ) is False


def test_matcher_declines_without_target():
    p = _motion(2)
    p["object_motion"]["target"] = None
    assert match_condition("object_motion", p) is False


def test_matcher_rejects_recolor():
    p = _motion(2)
    p["object_motion"]["pairs"][1]["color_preserved"] = False
    assert match_condition("object_motion", p) is False


def test_matcher_declines_without_selector():
    p = _motion(2)
    p["object_motion"]["selector"] = None
    assert match_condition("object_motion", p) is False


def test_matcher_declines_without_scene():
    # absent a fitted scene (drop/preserve), the fate of the unselected objects is
    # undetermined, so the matcher declines rather than guessing a single-object drop
    p = _motion(2)
    p["object_motion"]["scene"] = None
    assert match_condition("object_motion", p) is False


def test_matcher_fires_for_preserve_scene():
    assert match_condition("object_motion", _motion(2, scene="preserve")) is True


def test_matcher_rejects_unidentified_object():
    p = _motion(2)
    p["object_motion"]["pairs"][1]["selected_ok"] = False
    assert match_condition("object_motion", p) is False


# --- selection vocabulary (multi-object selection, §2.5-2b) -----------------

def test_select_object_unique():
    objs = objects_of([[0, 0, 0], [0, 5, 0], [0, 0, 0]])
    assert select_object(objs, {"kind": "unique"})["size"] == 1
    # with two objects, `unique` declines rather than guessing
    two = objects_of([[2, 0, 0], [0, 0, 0], [0, 0, 3]])
    assert select_object(two, {"kind": "unique"}) is None


def test_select_object_largest_and_smallest():
    # a 3-cell blob (colour 3) and a single pixel (colour 4)
    grid = [[3, 3, 0, 0], [3, 0, 0, 0], [0, 0, 0, 0], [0, 0, 0, 4]]
    objs = objects_of(grid)
    assert color_of(select_object(objs, {"kind": "largest"})) == 3
    assert color_of(select_object(objs, {"kind": "smallest"})) == 4


def test_select_object_declines_on_size_tie():
    # two single pixels: no unique size extreme, so largest/smallest decline
    grid = [[2, 0, 0], [0, 0, 0], [0, 0, 3]]
    objs = objects_of(grid)
    assert select_object(objs, {"kind": "largest"}) is None
    assert select_object(objs, {"kind": "smallest"}) is None


def test_fit_selector_prefers_unique():
    # single object per pair -> unique wins over a size criterion
    one = objects_of([[0, 0, 0], [0, 7, 0], [0, 0, 0]])
    sel = fit_selector([{"objects": one, "selected": 0},
                        {"objects": one, "selected": 0}])
    assert sel == {"kind": "unique"}


def test_fit_selector_largest():
    big = [[5, 5, 0], [5, 0, 0], [0, 0, 1]]   # blob(0) size3, pixel(1) size1
    objs = objects_of(big)
    big_idx = max(range(len(objs)), key=lambda i: objs[i]["size"])
    sel = fit_selector([{"objects": objs, "selected": big_idx},
                        {"objects": objs, "selected": big_idx}])
    assert sel == {"kind": "largest"}


def test_fit_selector_none_when_inconsistent():
    objs = objects_of([[5, 5, 0], [5, 0, 0], [0, 0, 1]])
    big_idx = max(range(len(objs)), key=lambda i: objs[i]["size"])
    small_idx = min(range(len(objs)), key=lambda i: objs[i]["size"])
    # one pair selects the big object, the other the small one -> no criterion fits
    assert fit_selector([{"objects": objs, "selected": big_idx},
                         {"objects": objs, "selected": small_idx}]) is None


def test_select_object_positional_edges():
    # one pixel in each corner-ish position; bbox edge extremes name each one
    grid = [[0, 4, 0],
            [2, 0, 3],
            [0, 5, 0]]
    objs = objects_of(grid)
    assert color_of(select_object(objs, {"kind": "topmost"})) == 4      # min row
    assert color_of(select_object(objs, {"kind": "bottommost"})) == 5   # max row
    assert color_of(select_object(objs, {"kind": "leftmost"})) == 2     # min col
    assert color_of(select_object(objs, {"kind": "rightmost"})) == 3    # max col


def test_select_object_positional_declines_on_tie():
    # two pixels share the top row -> topmost is ambiguous, so it declines
    grid = [[2, 0, 3], [0, 0, 0], [0, 5, 0]]
    objs = objects_of(grid)
    assert select_object(objs, {"kind": "topmost"}) is None


def test_fit_selector_topmost_when_size_fails():
    # The moved object is the topmost on every pair but NOT a size extreme: in the
    # first pair it is the smallest, in the second the largest, so neither size
    # criterion fits and only `topmost` survives -- the exact gap the size-only
    # vocabulary left (mirrors data/ARC_madeup/mo_select_topmost.json).
    p1 = objects_of([[4, 0, 0],        # size-1 pixel, top row 0
                     [0, 0, 0],
                     [2, 2, 2]])       # size-3 blob, top row 2
    p2 = objects_of([[5, 5, 5],        # size-3 blob, top row 0
                     [0, 0, 0],
                     [0, 0, 6]])       # size-1 pixel, top row 2
    top1 = min(range(len(p1)), key=lambda i: p1[i]["bbox"][0])
    top2 = min(range(len(p2)), key=lambda i: p2[i]["bbox"][0])
    sel = fit_selector([{"objects": p1, "selected": top1},
                        {"objects": p2, "selected": top2}])
    assert sel == {"kind": "topmost"}


def test_fit_selector_prefers_size_over_position():
    # when the moved object IS a size extreme on every pair, the size criterion is
    # tried first (more structural) so position never claims a size-describable move
    objs = objects_of([[5, 5, 0], [5, 0, 0], [0, 0, 1]])
    big_idx = max(range(len(objs)), key=lambda i: objs[i]["size"])
    sel = fit_selector([{"objects": objs, "selected": big_idx},
                        {"objects": objs, "selected": big_idx}])
    assert sel == {"kind": "largest"}


def test_select_object_odd_color():
    # three equal-size pixels, two share colour 2, one is colour 3 -> odd-one-out
    grid = [[2, 0, 0], [0, 3, 0], [2, 0, 0]]
    objs = objects_of(grid)
    assert color_of(select_object(objs, {"kind": "odd_color"})) == 3


def test_select_object_odd_color_declines_when_all_distinct():
    # every object has its own colour -> no single odd-one-out, so it declines
    grid = [[2, 0, 0], [0, 3, 0], [0, 0, 4]]
    objs = objects_of(grid)
    assert select_object(objs, {"kind": "odd_color"}) is None
    # ...and declines when no colour is unique (two of each) rather than guessing
    grid2 = [[2, 0, 3, 0], [0, 0, 0, 0], [2, 0, 0, 3]]
    objs2 = objects_of(grid2)
    assert select_object(objs2, {"kind": "odd_color"}) is None


def test_fit_selector_odd_color_when_size_and_position_fail():
    # The moved object is the colour odd-one-out on every pair but is equal in size
    # to the others and never at a position extreme, and its colour varies across
    # pairs -- so no size, position, or literal-colour criterion fits; only
    # `odd_color` survives (mirrors data/ARC_madeup/mo_select_odd_color.json).
    p1 = objects_of([[2, 0, 0, 0, 2], [0, 0, 0, 0, 0], [0, 0, 3, 0, 0],
                     [0, 0, 0, 0, 0], [2, 0, 0, 0, 0]])
    p2 = objects_of([[8, 0, 0, 0, 8], [0, 0, 0, 0, 0], [0, 0, 5, 0, 0],
                     [0, 0, 0, 0, 0], [0, 0, 0, 0, 8]])
    odd1 = next(i for i, o in enumerate(p1) if color_of(o) == 3)
    odd2 = next(i for i, o in enumerate(p2) if color_of(o) == 5)
    sel = fit_selector([{"objects": p1, "selected": odd1},
                        {"objects": p2, "selected": odd2}])
    assert sel == {"kind": "odd_color"}


def test_select_object_odd_shape():
    # three identical horizontal I-trominoes (same colour 5, same size 3) and one
    # L-tromino (the odd shape) -> the L is the shape odd-one-out.
    grid = [[5, 5, 5, 0, 5, 5, 5],
            [0, 0, 0, 0, 0, 0, 0],
            [5, 0, 0, 0, 0, 0, 0],
            [5, 5, 0, 0, 5, 5, 5]]
    objs = objects_of(grid)
    picked = select_object(objs, {"kind": "odd_shape"})
    assert picked is not None
    # the picked object is the L-tromino (the only one whose bbox is not 1x3)
    r0, c0, r1, c1 = picked["bbox"]
    assert (r1 - r0, c1 - c0) == (1, 1)


def test_select_object_odd_shape_declines_when_all_same_or_all_distinct():
    # every object the same shape -> no odd-one-out, declines.
    same = objects_of([[5, 5, 0, 5, 5], [0, 0, 0, 0, 0], [5, 5, 0, 0, 0]])
    assert select_object(same, {"kind": "odd_shape"}) is None
    # two horizontal dominoes, two vertical dominoes -> no single odd-one-out.
    pairs = objects_of([[5, 5, 0, 5, 0], [0, 0, 0, 5, 0],
                        [5, 0, 0, 0, 0], [5, 0, 0, 7, 7]])
    assert select_object(pairs, {"kind": "odd_shape"}) is None


def test_odd_shape_is_colour_agnostic():
    # shape, not colour, is what odd_shape keys on: an L of a *different* colour
    # among three I-trominoes is still the odd shape (and odd_color would also fit
    # here, but odd_shape must independently pick it).
    grid = [[5, 5, 5, 0, 5, 5, 5],
            [0, 0, 0, 0, 0, 0, 0],
            [3, 0, 0, 0, 0, 0, 0],
            [3, 3, 0, 0, 5, 5, 5]]
    objs = objects_of(grid)
    picked = select_object(objs, {"kind": "odd_shape"})
    r0, c0, r1, c1 = picked["bbox"]
    assert (r1 - r0, c1 - c0) == (1, 1)


def test_fit_selector_odd_shape_when_size_position_colour_fail():
    # The moved object is the shape odd-one-out on every pair but is equal in size
    # AND colour to the others and never at a position extreme -- so no size,
    # position, or colour criterion fits; only `odd_shape` survives (mirrors
    # data/ARC_madeup/mo_select_odd_shape.json train pairs).
    p1 = objects_of([[5, 5, 5, 0, 0, 5, 5, 5], [0, 0, 0, 0, 0, 0, 0, 0],
                     [0, 0, 0, 0, 0, 0, 0, 0], [0, 0, 0, 5, 0, 0, 0, 0],
                     [0, 0, 0, 5, 5, 0, 0, 0], [0, 0, 0, 0, 0, 0, 0, 0],
                     [0, 0, 0, 0, 0, 0, 0, 0], [5, 5, 5, 0, 0, 0, 0, 0]])
    p2 = objects_of([[0, 5, 5, 5, 0, 5, 5, 5], [0, 0, 0, 0, 0, 0, 0, 0],
                     [0, 0, 0, 0, 5, 0, 0, 0], [5, 5, 5, 0, 5, 5, 0, 0],
                     [0, 0, 0, 0, 0, 0, 0, 0], [0, 0, 0, 0, 0, 0, 0, 0],
                     [0, 0, 0, 0, 0, 0, 0, 0], [0, 0, 0, 0, 0, 0, 0, 0]])
    odd1 = _selection_index_oddshape(p1)
    odd2 = _selection_index_oddshape(p2)
    sel = fit_selector([{"objects": p1, "selected": odd1},
                        {"objects": p2, "selected": odd2}])
    assert sel == {"kind": "odd_shape"}


def test_select_object_second_largest_and_smallest():
    # three strictly size-ordered objects (sizes 4, 2, 1); the middle one is
    # neither the largest nor the smallest -> only a *ranked* selector names it.
    grid = [[2, 2, 0, 0, 0, 0],
            [2, 2, 0, 0, 0, 0],
            [0, 0, 3, 3, 0, 0],
            [0, 0, 0, 0, 0, 0],
            [0, 0, 0, 0, 0, 4]]
    objs = objects_of(grid)
    assert color_of(select_object(objs, {"kind": "second_largest"})) == 3
    # with three objects the middle is also second-from-smallest
    assert color_of(select_object(objs, {"kind": "second_smallest"})) == 3
    # ...and the extremes still go to largest/smallest, not the ranked selector
    assert color_of(select_object(objs, {"kind": "largest"})) == 2
    assert color_of(select_object(objs, {"kind": "smallest"})) == 4


def test_select_object_second_largest_declines_on_tie():
    # the second-largest *value* is shared by two objects (sizes 4, 2, 2) -> the
    # rank-2 pick is ambiguous, so it declines rather than guessing.
    grid = [[2, 2, 0, 0, 0],
            [2, 2, 0, 0, 0],
            [0, 0, 3, 3, 0],
            [0, 0, 0, 0, 0],
            [4, 4, 0, 0, 0]]
    objs = objects_of(grid)
    # sizes: 4 (block), 2 (domino), 2 (domino) -> distinct values {4,2}; rank-2
    # value is 2, held by two objects -> decline
    assert select_object(objs, {"kind": "second_largest"}) is None


def test_fit_selector_ranked_when_extremes_and_oddness_fail():
    # The moved object is the *middle* of three strictly size-ordered objects on
    # every pair, at no position extreme, with all colours and shapes distinct, and
    # its size varies across pairs -- so no extreme, position, or odd-one-out
    # criterion fits; only `second_largest` survives (mirrors
    # data/ARC_madeup/mo_second_largest.json).
    spec = json.load(open(os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "data", "ARC_madeup", "mo_second_largest.json")))
    selections = []
    for pair in spec["train"]:
        objs = objects_of(pair["input"])
        out = objects_of(pair["output"])
        sel, _o, _s, _nc = ExtractPatternOperator._identify_move(objs, out)
        selections.append({"objects": objs, "selected": sel})
    assert fit_selector(selections) == {"kind": "second_largest"}


def _load_madeup(name):
    """Load a data/ARC_madeup task into the (input, output)-tuple spec form the
    test pipeline helpers expect (the on-disk JSON uses {"input","output"} dicts)."""
    spec = json.load(open(os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "data", "ARC_madeup", name)))
    to_tuples = lambda pairs: [(p["input"], p["output"]) for p in pairs]
    return {"train": to_tuples(spec["train"]), "test": to_tuples(spec["test"])}


def test_pipeline_solves_second_largest():
    # the ranked (2nd-largest) selection task solves end-to-end via the SAME rule
    # object as the rest of the move family (no accretion; §2.5-3). Loaded from the
    # on-disk madeup task so the test and the probe exercise identical data.
    spec = _load_madeup("mo_second_largest.json")
    rr = _check_solved(spec, "second_largest").s1["active-rules"][0]
    rc = _check_solved(EASY_C, "c").s1["active-rules"][0]
    assert rr == rc


def _selection_index_oddshape(objs):
    # the L-tromino is the only object whose bbox is 2x2 (the others are 1x3)
    for i, o in enumerate(objs):
        r0, c0, r1, c1 = o["bbox"]
        if (r1 - r0, c1 - c0) == (1, 1):
            return i
    raise AssertionError("no L-tromino found")


# --- end-to-end via the real pipeline operators ----------------------------

class _Grid:
    def __init__(self, raw):
        self.raw = [row[:] for row in raw]
        self.height = len(raw)
        self.width = len(raw[0]) if raw else 0
        self.node_id = id(self)


class _Pair:
    def __init__(self, inp, out):
        self.input_grid = _Grid(inp)
        self.output_grid = _Grid(out) if out is not None else None


class _Task:
    def __init__(self, train, test, name="test_motion"):
        self.task_hex = name
        self.example_pairs = [_Pair(i, o) for i, o in train]
        self.test_pairs = [_Pair(i, o) for i, o in test]


class _WM:
    def __init__(self, task):
        self.task = task
        self.s1 = {}


# easy000c: 6x6, single object -> bottom-right (5,5)
EASY_C = {
    "train": [
        ([[0]*6, [0,2,0,0,0,0], [0]*6, [0]*6, [0]*6, [0]*6],
         [[0]*6, [0]*6, [0]*6, [0]*6, [0]*6, [0,0,0,0,0,2]]),
        ([[0]*6, [0,0,0,0,1,0], [0]*6, [0]*6, [0]*6, [0]*6],
         [[0]*6, [0]*6, [0]*6, [0]*6, [0]*6, [0,0,0,0,0,1]]),
    ],
    "test": [
        ([[0]*6, [0]*6, [0]*6, [0]*6, [0,0,4,0,0,0], [0]*6],
         [[0]*6, [0]*6, [0]*6, [0]*6, [0]*6, [0,0,0,0,0,4]]),
    ],
}

# easy000g: varying grid sizes, single object -> bottom-right (H-1, W-1)
EASY_G = {
    "train": [
        ([[0,0,0,0], [0,2,0,0], [0,0,0,0], [0,0,0,0]],
         [[0,0,0,0], [0,0,0,0], [0,0,0,0], [0,0,0,2]]),
        ([[0,0,0,0,0], [0,0,0,0,1], [0,0,0,0,0]],
         [[0,0,0,0,0], [0,0,0,0,0], [0,0,0,0,1]]),
    ],
    "test": [
        ([[0,0,0,0], [0,0,0,0], [0,0,0,0], [0,0,0,0], [0,0,4,0], [0,0,0,0]],
         [[0,0,0,0], [0,0,0,0], [0,0,0,0], [0,0,0,0], [0,0,0,0], [0,0,0,4]]),
    ],
}

# easy000d: object -> constant absolute (1,2)
EASY_D = {
    "train": [
        ([[0]*6, [0,2,0,0,0,0], [0]*6, [0]*6, [0]*6, [0]*6],
         [[0]*6, [0,0,2,0,0,0], [0]*6, [0]*6, [0]*6, [0]*6]),
        ([[0]*6, [0,0,0,0,1,0], [0]*6, [0]*6, [0]*6, [0]*6],
         [[0]*6, [0,0,1,0,0,0], [0]*6, [0]*6, [0]*6, [0]*6]),
    ],
    "test": [
        ([[0]*6, [0]*6, [0]*6, [0]*6, [0,0,4,0,0,0], [0]*6],
         [[0]*6, [0,0,4,0,0,0], [0]*6, [0]*6, [0]*6, [0]*6]),
    ],
}

# easy000i: 6x6 -> 5x5 resize, object -> top-left (0,0). Exercises the
# output-shape expression (input shrunk by (1,1)) alongside a constant target.
EASY_I = {
    "train": [
        ([[0]*6, [0,2,0,0,0,0], [0]*6, [0]*6, [0]*6, [0]*6],
         [[2,0,0,0,0], [0,0,0,0,0], [0,0,0,0,0], [0,0,0,0,0], [0,0,0,0,0]]),
        ([[0]*6, [0,0,0,0,1,0], [0]*6, [0]*6, [0]*6, [0]*6],
         [[1,0,0,0,0], [0,0,0,0,0], [0,0,0,0,0], [0,0,0,0,0], [0,0,0,0,0]]),
    ],
    "test": [
        ([[0]*6, [0]*6, [0]*6, [0]*6, [0,0,4,0,0,0], [0]*6],
         [[4,0,0,0,0], [0,0,0,0,0], [0,0,0,0,0], [0,0,0,0,0], [0,0,0,0,0]]),
    ],
}

# easy000e: object -> source + (+1, -1) translation
EASY_E = {
    "train": [
        ([[0]*6, [0,2,0,0,0,0], [0]*6, [0]*6, [0]*6, [0]*6],
         [[0]*6, [0]*6, [2,0,0,0,0,0], [0]*6, [0]*6, [0]*6]),
        ([[0]*6, [0,0,0,0,1,0], [0]*6, [0]*6, [0]*6, [0]*6],
         [[0]*6, [0]*6, [0,0,0,1,0,0], [0]*6, [0]*6, [0]*6]),
    ],
    "test": [
        ([[0]*6, [0]*6, [0]*6, [0]*6, [0,0,4,0,0,0], [0]*6],
         [[0]*6, [0]*6, [0]*6, [0]*6, [0]*6, [0,4,0,0,0,0]]),
    ],
}


# multi-object selection: two objects in, the LARGEST one moves to the
# bottom-right corner, the smaller one is dropped. The crux is *which* object
# moves — named by a fitted `largest` selector, not a literal index.
MULTI_LARGEST = {
    "train": [
        ([[3, 3, 0, 0, 0], [3, 0, 0, 0, 0], [0, 0, 0, 0, 0],
          [0, 0, 0, 4, 0], [0, 0, 0, 0, 0]],
         [[0, 0, 0, 0, 0], [0, 0, 0, 0, 0], [0, 0, 0, 0, 0],
          [0, 0, 0, 3, 3], [0, 0, 0, 3, 0]]),
        ([[2, 2, 2, 0, 0], [0, 0, 0, 0, 0], [0, 5, 0, 0, 0],
          [0, 0, 0, 0, 0], [0, 0, 0, 0, 0]],
         [[0, 0, 0, 0, 0], [0, 0, 0, 0, 0], [0, 0, 0, 0, 0],
          [0, 0, 0, 0, 0], [0, 0, 2, 2, 2]]),
    ],
    "test": [
        ([[0, 0, 0, 7, 0], [0, 0, 0, 0, 0], [6, 6, 0, 0, 0],
          [6, 0, 0, 0, 0], [0, 0, 0, 0, 0]],
         [[0, 0, 0, 0, 0], [0, 0, 0, 0, 0], [0, 0, 0, 0, 0],
          [0, 0, 0, 6, 6], [0, 0, 0, 6, 0]]),
    ],
}


def test_pipeline_solves_multi_object_largest():
    # the multi-object selection task solves end-to-end, and via the SAME rule
    # object as the single-object move family (no accretion; §2.5-3).
    rm = _check_solved(MULTI_LARGEST, "multi_largest").s1["active-rules"][0]
    rc = _check_solved(EASY_C, "c").s1["active-rules"][0]
    assert rm == rc


# multi-object selection by COLOUR identity: several equal-size objects, none at a
# position extreme, and the colour-unique one (the odd-one-out) moves to the
# bottom-right corner. Neither size, position, nor a literal colour names it — only
# the `odd_color` selector does (the §2.1 multi-object-selection concept on the
# colour dimension; mirrors data/ARC_madeup/mo_select_odd_color.json).
MULTI_ODD_COLOR = {
    "train": [
        ([[2, 0, 0, 0, 2], [0, 0, 0, 0, 0], [0, 0, 3, 0, 0],
          [0, 0, 0, 0, 0], [2, 0, 0, 0, 0]],
         [[0, 0, 0, 0, 0], [0, 0, 0, 0, 0], [0, 0, 0, 0, 0],
          [0, 0, 0, 0, 0], [0, 0, 0, 0, 3]]),
        ([[8, 0, 0, 0, 8], [0, 0, 0, 0, 0], [0, 0, 5, 0, 0],
          [0, 0, 0, 0, 0], [0, 0, 0, 0, 8]],
         [[0, 0, 0, 0, 0], [0, 0, 0, 0, 0], [0, 0, 0, 0, 0],
          [0, 0, 0, 0, 0], [0, 0, 0, 0, 5]]),
    ],
    "test": [
        ([[0, 0, 0, 0, 1], [0, 4, 0, 0, 0], [0, 0, 0, 0, 0],
          [0, 0, 0, 0, 0], [1, 0, 0, 0, 1]],
         [[0, 0, 0, 0, 0], [0, 0, 0, 0, 0], [0, 0, 0, 0, 0],
          [0, 0, 0, 0, 0], [0, 0, 0, 0, 4]]),
    ],
}


def test_pipeline_solves_multi_object_odd_color():
    # colour-selected multi-object move solves end-to-end via the SAME rule object
    # as the rest of the move family (no accretion; §2.5-3).
    ro = _check_solved(MULTI_ODD_COLOR, "multi_odd_color").s1["active-rules"][0]
    rc = _check_solved(EASY_C, "c").s1["active-rules"][0]
    assert ro == rc


# multi-object OUTPUT: two objects in, the LARGEST moves to the bottom-right
# corner while the *other* object is preserved unchanged. The output therefore
# holds TWO objects (not one) — the §2.1 multi-object-output concept. Solving it
# the intended way needs the fitted `scene = preserve` expression, not a literal.
# Mirrors data/ARC_madeup/mo_preserve_others.json.
MULTI_PRESERVE = {
    "train": [
        ([[3, 3, 0, 0, 4], [3, 0, 0, 0, 0], [0, 0, 0, 0, 0],
          [0, 0, 0, 0, 0], [0, 0, 0, 0, 0]],
         [[0, 0, 0, 0, 4], [0, 0, 0, 0, 0], [0, 0, 0, 0, 0],
          [0, 0, 0, 3, 3], [0, 0, 0, 3, 0]]),
        ([[0, 0, 0, 0, 0], [0, 2, 2, 0, 0], [0, 2, 2, 0, 0],
          [0, 0, 0, 0, 0], [7, 0, 0, 0, 0]],
         [[0, 0, 0, 0, 0], [0, 0, 0, 0, 0], [0, 0, 0, 0, 0],
          [0, 0, 0, 2, 2], [7, 0, 0, 2, 2]]),
    ],
    "test": [
        ([[0, 0, 0, 0, 8], [0, 0, 0, 0, 0], [6, 6, 0, 0, 0],
          [6, 0, 0, 0, 0], [0, 0, 0, 0, 0]],
         [[0, 0, 0, 0, 8], [0, 0, 0, 0, 0], [0, 0, 0, 0, 0],
          [0, 0, 0, 6, 6], [0, 0, 0, 6, 0]]),
    ],
}


def test_identify_move_drop():
    # a lone output object matched back to its input object -> drop scene
    objs_in = objects_of([[3, 3, 0, 0, 0], [3, 0, 0, 0, 0], [0, 0, 0, 0, 0],
                          [0, 0, 0, 4, 0], [0, 0, 0, 0, 0]])
    objs_out = objects_of([[0, 0, 0, 0, 0], [0, 0, 0, 0, 0], [0, 0, 0, 0, 0],
                           [0, 0, 0, 3, 3], [0, 0, 0, 3, 0]])
    sel, obj_out, scene, new_color = ExtractPatternOperator._identify_move(objs_in, objs_out)
    assert scene == "drop"
    assert new_color is None   # colour preserved → not a recolour
    assert color_of(objs_in[sel]) == 3   # the larger blob moved; the pixel dropped


def test_identify_move_preserve():
    # two objects in, two out: one moved (colour 3), the other (colour 4) unchanged
    objs_in = objects_of(MULTI_PRESERVE["train"][0][0])
    objs_out = objects_of(MULTI_PRESERVE["train"][0][1])
    sel, obj_out, scene, new_color = ExtractPatternOperator._identify_move(objs_in, objs_out)
    assert scene == "preserve"
    assert new_color is None   # colour preserved → not a recolour
    assert color_of(objs_in[sel]) == 3   # the blob is the one that moved
    assert color_of(obj_out) == 3


def test_identify_move_declines_on_ambiguous_preserve():
    # if NO object stays put (both moved), the preserve match is ambiguous -> decline
    objs_in = objects_of([[2, 0, 0], [0, 0, 0], [0, 0, 3]])
    objs_out = objects_of([[0, 0, 3], [0, 0, 0], [2, 0, 0]])
    sel, obj_out, scene, new_color = ExtractPatternOperator._identify_move(objs_in, objs_out)
    assert (sel, obj_out, scene, new_color) == (None, None, None, None)


def test_pipeline_solves_multi_object_preserve():
    # the multi-object-output (preserve) task solves end-to-end, and via the SAME
    # rule object as the single-object move family (no accretion; §2.5-3).
    rp = _check_solved(MULTI_PRESERVE, "multi_preserve").s1["active-rules"][0]
    rc = _check_solved(EASY_C, "c").s1["active-rules"][0]
    assert rp == rc


def _solve(spec, name="t"):
    task = _Task(spec["train"], spec["test"], name=name)
    wm = _WM(task)
    ExtractPatternOperator().effect(wm)
    GeneralizeOperator().effect(wm)
    PredictOperator().effect(wm)
    return wm, task


def _check_solved(spec, name):
    wm, task = _solve(spec, name)
    rule = wm.s1["active-rules"][0]
    assert rule["type"] == "object_motion", name
    assert "condition" in rule and "action" in rule
    # The rule carries the fitted *target expression* (corner/constant/offset),
    # a value-agnostic argument (a `{"kind": ...}` expression, never a baked
    # output grid) — recorded so save_rule can anti-unify divergent targets into
    # one covers>1 rule (R3 / §2.5-2). Predict still re-derives the concrete
    # destination from the example comparison, so solving is unchanged.
    target = rule["action"]["args"].get("target")
    assert isinstance(target, dict) and "kind" in target, name
    pred = wm.s1["predictions"]["test_0"]
    assert pred == task.test_pairs[0].output_grid.raw, name
    return wm


def test_pipeline_solves_corner_c():
    _check_solved(EASY_C, "c")


def test_pipeline_solves_constant_d():
    _check_solved(EASY_D, "d")


def test_pipeline_solves_offset_e():
    _check_solved(EASY_E, "e")


def test_pipeline_solves_resize_i():
    # the resize task (6x6 -> 5x5, object to top-left) solves via the same
    # object_motion rule — output shape is a fitted expression, not a literal.
    _check_solved(EASY_I, "i")


def test_one_rule_covers_the_whole_family(tmp_path):
    # corner, constant, translation AND resize tasks now carry *divergent* fitted
    # target expressions in WM (that divergence is exactly what anti-unification
    # lifts). The covers>1 invariant therefore holds at the STORAGE level: saving
    # them through the sanctioned save_rule converges them to ONE rule whose
    # target is a ?v variable, covers all five, and carries an
    # anti_unification_trace — not one detector per variant (R3 / §2.5-3/4).
    from agent.memory import save_rule

    pm = str(tmp_path / "pm")
    em = str(tmp_path / "em")
    for spec, name in [(EASY_C, "c"), (EASY_D, "d"), (EASY_E, "e"),
                       (EASY_G, "g"), (EASY_I, "i")]:
        rule = _check_solved(spec, name).s1["active-rules"][0]
        save_rule(rule, name, procedural_memory_root=pm, episodic_memory_root=em)

    files = [f for f in os.listdir(pm) if f.startswith("rule_")]
    assert len(files) == 1, "the whole move family must converge to one rule"
    with open(os.path.join(pm, files[0])) as fh:
        entry = json.load(fh)
    assert set(entry["covers"]) == {"c", "d", "e", "g", "i"}
    assert str(entry["action"]["args"]["target"]).startswith("?v")
    assert entry["anti_unification_trace"]


def test_pipeline_solves_to_anchor():
    # the relational-target task solves end-to-end via an object_motion rule whose
    # fitted target is the `to_anchor` expression (§2.5-1). Its single other object
    # makes the fitted anchor selector the degenerate `unique`. Loaded from the
    # on-disk madeup task so the test and the probe exercise identical data.
    spec = _load_madeup("mo_to_anchor.json")
    rule = _check_solved(spec, "to_anchor").s1["active-rules"][0]
    assert rule["action"]["args"]["target"] == {
        "kind": "to_anchor", "anchor": {"kind": "unique"}}


def test_pipeline_solves_anchor_selection():
    # §2.5-2b lift: a relational-target task with a DISTRACTOR object, so the anchor
    # must be named by a selector over the others (here the LARGEST). It solves
    # end-to-end via the same object_motion rule whose fitted target carries the
    # fitted anchor selector — naming *which* of several others is the anchor.
    spec = _load_madeup("mo_anchor_select.json")
    rule = _check_solved(spec, "anchor_select").s1["active-rules"][0]
    assert rule["action"]["args"]["target"] == {
        "kind": "to_anchor", "anchor": {"kind": "largest"}}


# ----- move ∘ recolour (translate AND change colour) -----------------------

def test_identify_move_recolor_reports_new_color():
    # a 2x2 block of colour 3 moves AND becomes colour 4: the colour-set match
    # fails (colour changed), but the colour-invariant shape match identifies it
    # and reports the new colour. This is the composition no single family handles.
    objs_in = objects_of([[3, 3, 0], [3, 3, 0], [0, 0, 0]])
    objs_out = objects_of([[0, 0, 0], [0, 4, 4], [0, 4, 4]])
    sel, obj_out, scene, new_color = ExtractPatternOperator._identify_move(
        objs_in, objs_out)
    assert scene == "drop"
    assert new_color == 4               # the move also recoloured 3 -> 4
    assert color_of(objs_in[sel]) == 3  # matched back to its input by shape, not colour


def test_object_motion_fits_constant_color_expr():
    # across the two move∘recolour pairs the new colour is a constant 4 (no input
    # object carries it), so the colour fits the `constant` source expression.
    spec = _load_madeup("mo_move_recolor.json")
    task = _Task(spec["train"], spec["test"], name="mr")
    wm = _WM(task)
    ExtractPatternOperator().effect(wm)
    motion = wm.s1["patterns"]["object_motion"]
    assert all(p["recolored"] for p in motion["pairs"])
    assert motion["color"] == {"kind": "constant", "color": 4}


def test_matcher_requires_color_expr_when_recolored():
    # the object_motion matcher must NOT fire on a recolouring move unless the new
    # colour itself fitted an expression (else it would bake a literal / guess).
    motion_no_color = {
        "pairs": [{"selected_ok": True, "size_preserved": True,
                   "color_preserved": False, "recolored": True}],
        "selector": {"kind": "unique"}, "target": {"kind": "constant", "pos": [0, 0]},
        "out_shape": {"kind": "same"}, "scene": "drop", "color": None,
    }
    assert match_condition("object_motion", {"object_motion": motion_no_color},
                           {"min_evidence": 1}) is False
    motion_with_color = dict(motion_no_color, color={"kind": "constant", "color": 4})
    assert match_condition("object_motion", {"object_motion": motion_with_color},
                           {"min_evidence": 1}) is True


def test_pipeline_solves_move_recolor():
    # the move∘recolour task solves end-to-end via the SAME object_motion rule
    # family (no new family / no accretion; §2.5-3), with the new colour carried as
    # a second fitted argument expression alongside the target.
    spec = _load_madeup("mo_move_recolor.json")
    wm = _check_solved(spec, "move_recolor")
    rule = wm.s1["active-rules"][0]
    assert rule["action"]["args"]["color"] == {"kind": "constant", "color": 4}


def test_to_anchor_converges_with_corner_family(tmp_path):
    # the relational-target task carries a target (to_anchor) that DIVERGES from the
    # corner family's (bottom_right); save_rule lifts that divergence to a ?v
    # variable, converging both into ONE covers>1 rule with an au trace — the move
    # family absorbs the relational target instead of spawning a detector (§2.5-3/4).
    from agent.memory import save_rule

    pm = str(tmp_path / "pm")
    em = str(tmp_path / "em")
    for spec, name in [(EASY_C, "c"),
                       (_load_madeup("mo_to_anchor.json"), "to_anchor")]:
        rule = _check_solved(spec, name).s1["active-rules"][0]
        save_rule(rule, name, procedural_memory_root=pm, episodic_memory_root=em)

    files = [f for f in os.listdir(pm) if f.startswith("rule_")]
    assert len(files) == 1, "the relational target must fold into the move family"
    with open(os.path.join(pm, files[0])) as fh:
        entry = json.load(fh)
    assert set(entry["covers"]) == {"c", "to_anchor"}
    assert str(entry["action"]["args"]["target"]).startswith("?v")
    assert entry["anti_unification_trace"]


# --- multi-object "map-all" gravity (select-one -> map-all, §2.5-2b) ---------
#
# Every object falls to the bottom edge keeping its column — the canonical gravity
# transform where the rule acts on *all* objects at once, not one fitted selector.
# Distinct colours per object so the input->output bijection is unambiguous.

from agent.dsl_expr import fit_uniform_target


def _g(cells, h=6, w=6):
    """Build an h×w grid from a {(r,c): colour} dict (background 0)."""
    grid = [[0] * w for _ in range(h)]
    for (r, c), v in cells.items():
        grid[r][c] = v
    return grid


def _fall(cells, h=6):
    """Drop every single-cell object to the bottom row, keeping its column."""
    return {(h - 1, c): v for (r, c), v in cells.items()}


MULTI_GRAVITY = {
    "train": [
        (_g({(0, 1): 3, (1, 4): 4}), _g(_fall({(0, 1): 3, (1, 4): 4}))),
        (_g({(1, 0): 2, (0, 3): 3, (2, 5): 4}),
         _g(_fall({(1, 0): 2, (0, 3): 3, (2, 5): 4}))),
    ],
    "test": [
        (_g({(0, 2): 7, (1, 5): 8}), _g(_fall({(0, 2): 7, (1, 5): 8}))),
    ],
}


def test_fit_uniform_target_to_edge():
    # several objects, each falling to the bottom edge keeping its column, with
    # *different* fall distances — defeats offset, fits the per-object to_edge.
    desc = fit_uniform_target([
        _m((0, 1), (5, 1)), _m((1, 4), (5, 4)), _m((2, 0), (5, 0)),
    ])
    assert desc == {"kind": "to_edge", "edge": "bottom"}


def test_fit_uniform_target_offset():
    # one uniform translation moves every object -> offset wins (most structural).
    desc = fit_uniform_target([_m((0, 1), (1, 2)), _m((2, 3), (3, 4))])
    assert desc == {"kind": "offset", "delta": [1, 1]}


def test_fit_uniform_target_declines():
    # inconsistent per-object displacement (no single offset, no single edge).
    assert fit_uniform_target([_m((0, 1), (5, 1)), _m((1, 4), (1, 4))]) is None
    # a static set (nothing moved) is not a fall.
    assert fit_uniform_target([_m((5, 1), (5, 1)), _m((5, 4), (5, 4))]) is None


def test_fit_map_all_recognises_gravity():
    task = _Task(MULTI_GRAVITY["train"], MULTI_GRAVITY["test"], name="grav")
    mapall = ExtractPatternOperator._fit_map_all(task)
    assert mapall is not None
    assert mapall["target"] == {"kind": "to_edge", "edge": "bottom"}
    assert mapall["clean"] is True


def test_fit_map_all_declines_single_object():
    # the move family the select-one path covers must never be claimed by map_all.
    task = _Task(EASY_C["train"], EASY_C["test"], name="c")
    assert ExtractPatternOperator._fit_map_all(task) is None


def test_fit_map_all_resolves_identical_by_column():
    # two *identical* objects (same colour+size+shape) in *distinct columns* falling
    # to the bottom -> the colour+size+shape ('identity') bijection is ambiguous, but
    # the column a vertical fall preserves disambiguates which fell where. Different
    # fall distances (5 and 3) defeat a uniform offset, so the per-object to_edge
    # bottom fits. Previously declined; the axis disambiguator now resolves it.
    spec_in = _g({(0, 1): 3, (2, 4): 3})
    spec_out = _g(_fall({(0, 1): 3, (2, 4): 3}))
    task = _Task([(spec_in, spec_out)], [(spec_in, spec_out)], name="ident")
    mapall = ExtractPatternOperator._fit_map_all(task)
    assert mapall is not None
    assert mapall["target"] == {"kind": "to_edge", "edge": "bottom"}
    assert mapall["clean"] is True


def test_fit_map_all_resolves_stacked_identical_by_settle():
    # two identical objects in the *same column* both fall and pile up — neither the
    # identity key nor the preserved-axis bijection can say which fell where (and the
    # pile merges them into one output blob, breaking the equal-count bijection). The
    # joint gravity-settle fallback resolves it on coloured cells: the lower object
    # reaches the floor, the upper one rests on top of it.
    spec_in = _g({(0, 2): 3, (2, 2): 3})
    spec_out = _g({(4, 2): 3, (5, 2): 3})  # they stack at the bottom
    task = _Task([(spec_in, spec_out)], [(spec_in, spec_out)], name="stacked")
    mapall = ExtractPatternOperator._fit_map_all(task)
    assert mapall is not None
    assert mapall["target"] == {"kind": "gravity_settle", "edge": "bottom"}
    assert mapall["clean"] is True


def test_simulate_gravity_settle_stacks_in_column():
    # three single cells in one column fall to the bottom and pile up in order:
    # the lowest reaches the floor, the others rest on top, each keeping its column.
    from agent.dsl_expr import objects_of, simulate_gravity_settle
    objs = objects_of(_g({(0, 2): 8, (2, 2): 2, (4, 2): 5}, h=6, w=6))
    dsts = simulate_gravity_settle(objs, 6, 6, "bottom")
    # objs are top-left-sorted: 8@(0,2), 2@(2,2), 5@(4,2)
    assert dsts == [(3, 2), (4, 2), (5, 2)]


def test_simulate_gravity_settle_independent_columns_reach_floor():
    # objects in different columns don't collide -> each reaches the floor (settle
    # reduces to the plain to_edge fall when there is no stacking).
    from agent.dsl_expr import objects_of, simulate_gravity_settle
    objs = objects_of(_g({(0, 0): 4, (1, 3): 7}, h=5, w=5))
    dsts = simulate_gravity_settle(objs, 5, 5, "bottom")
    assert dsts == [(4, 0), (4, 3)]


def test_fit_gravity_settle_picks_unique_edge():
    from agent.dsl_expr import objects_of, fit_gravity_settle
    in1 = objects_of(_g({(0, 1): 2, (2, 1): 3}))
    out1 = objects_of(_g({(3, 1): 2, (4, 1): 3}))
    per_pair = [(5, 5, in1, out1)]
    assert fit_gravity_settle(per_pair) == {"kind": "gravity_settle", "edge": "bottom"}


def test_fit_gravity_settle_declines_non_gravity():
    # a scene whose output is *not* any edge-settling of the input -> decline.
    from agent.dsl_expr import objects_of, fit_gravity_settle
    in1 = objects_of(_g({(0, 0): 2, (0, 4): 3}))
    out1 = objects_of(_g({(2, 2): 2, (3, 3): 3}))  # arbitrary, not a fall
    assert fit_gravity_settle([(5, 5, in1, out1)]) is None


def test_render_map_all_gravity_settle_roundtrip():
    # the renderer reproduces a stacking fall end-to-end via map_all_destinations.
    from agent.active_operators import PredictOperator
    g0 = _Grid(_g({(1, 3): 2, (3, 3): 4}, h=5, w=5))
    out = PredictOperator._render_map_all_motion(
        g0, {"kind": "gravity_settle", "edge": "bottom"}
    )
    assert out is not None
    assert out == _g({(3, 3): 2, (4, 3): 4}, h=5, w=5)


def test_motion_bijection_identity_distinct():
    # distinct objects -> the colour+size+shape 'identity' strategy matches them.
    from agent.dsl_expr.selection import motion_bijection
    objs_in = objects_of(_g({(0, 1): 3, (1, 4): 4}))
    objs_out = objects_of(_g({(5, 1): 3, (5, 4): 4}))
    bij = motion_bijection(objs_in, objs_out, "identity")
    assert bij is not None and len(bij) == 2
    # colour 3 input maps to colour 3 output, 4 to 4.
    assert all(color_of(oi) == color_of(oj) for oi, oj in bij)


def test_motion_bijection_identity_declines_identical():
    # identical objects -> the 'identity' key cannot tell them apart; declines.
    from agent.dsl_expr.selection import motion_bijection
    objs_in = objects_of(_g({(0, 1): 3, (2, 4): 3}))
    objs_out = objects_of(_g({(5, 1): 3, (5, 4): 3}))
    assert motion_bijection(objs_in, objs_out, "identity") is None
    # but 'vertical' (the preserved column) resolves the same scene.
    bij = motion_bijection(objs_in, objs_out, "vertical")
    assert bij is not None and len(bij) == 2
    # each input object maps to the output object in the same column.
    assert all(oi["bbox"][1] == oj["bbox"][1] for oi, oj in bij)


def test_fit_map_all_target_identical_gravity():
    # the motion-fitter resolves identical-object gravity from pre-gathered pairs.
    from agent.dsl_expr import fit_map_all_target
    objs_in = objects_of(_g({(0, 1): 3, (2, 4): 3}))
    objs_out = objects_of(_g({(5, 1): 3, (5, 4): 3}))
    desc = fit_map_all_target([(6, 6, objs_in, objs_out)])
    assert desc["target"] == {"kind": "to_edge", "edge": "bottom"}


def test_render_map_all_motion():
    g0 = _Grid(_g({(0, 2): 7, (1, 5): 8}))
    out = PredictOperator._render_map_all_motion(
        g0, {"kind": "to_edge", "edge": "bottom"}
    )
    assert out == _g(_fall({(0, 2): 7, (1, 5): 8}))


def test_pipeline_solves_multi_object_gravity():
    # the multi-object gravity task solves end-to-end via the move family's rule
    # skeleton (same type / condition / dsl as the single-object family); only the
    # fitted target diverges (a per-object `to_edge` fall vs the corner), which
    # save_rule lifts to a ?v variable (see the fold test below). No accretion.
    rg = _check_solved(MULTI_GRAVITY, "multi_gravity").s1["active-rules"][0]
    rc = _check_solved(EASY_C, "c").s1["active-rules"][0]
    assert rg["type"] == rc["type"] == "object_motion"
    assert rg["condition"] == rc["condition"]
    assert rg["action"]["dsl"] == rc["action"]["dsl"] == "place_object"
    assert rg["action"]["args"]["target"] == {"kind": "to_edge", "edge": "bottom"}


def test_map_all_gravity_folds_into_move_family(tmp_path):
    # the multi-object gravity task carries a target (to_edge) that DIVERGES from the
    # corner family's (bottom_right); save_rule lifts that divergence to a ?v
    # variable, converging both into ONE covers>1 rule — map-all gravity absorbs into
    # the move family instead of minting a separate detector (§2.5-3/4).
    from agent.memory import save_rule

    pm = str(tmp_path / "pm")
    em = str(tmp_path / "em")
    for spec, name in [(EASY_C, "c"), (MULTI_GRAVITY, "gravity")]:
        rule = _check_solved(spec, name).s1["active-rules"][0]
        save_rule(rule, name, procedural_memory_root=pm, episodic_memory_root=em)

    files = [f for f in os.listdir(pm) if f.startswith("rule_")]
    assert len(files) == 1, "map-all gravity must fold into the move family"
    with open(os.path.join(pm, files[0])) as fh:
        entry = json.load(fh)
    assert set(entry["covers"]) == {"c", "gravity"}
    assert str(entry["action"]["args"]["target"]).startswith("?v")
    assert entry["anti_unification_trace"]


if __name__ == "__main__":
    import pytest
    raise SystemExit(pytest.main([__file__, "-q"]))
