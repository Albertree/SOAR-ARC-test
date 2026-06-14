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

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agent.dsl_expr import (
    objects_of, unique_object, bottom_right_of, color_of,
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


# --- matcher ---------------------------------------------------------------

def _motion(n=2, target=None, out_shape=None, **overrides):
    pair = {
        "single_in": True, "single_out": True,
        "color_preserved": True, "size_preserved": True,
        "grid_size_preserved": True,
    }
    pair.update(overrides)
    return {"object_motion": {
        "evidence_count": n,
        "pairs": [dict(pair) for _ in range(n)],
        "target": target if target is not None else {"kind": "bottom_right"},
        "out_shape": out_shape if out_shape is not None else {"kind": "same"},
    }}


def test_matcher_fires_with_target():
    assert match_condition("object_motion", _motion(2)) is True


def test_matcher_declines_without_out_shape():
    p = _motion(2)
    p["object_motion"]["out_shape"] = None
    assert match_condition("object_motion", p) is False


def test_matcher_needs_min_evidence():
    assert match_condition("object_motion", _motion(1)) is False


def test_matcher_declines_without_target():
    p = _motion(2)
    p["object_motion"]["target"] = None
    assert match_condition("object_motion", p) is False


def test_matcher_rejects_recolor():
    p = _motion(2)
    p["object_motion"]["pairs"][1]["color_preserved"] = False
    assert match_condition("object_motion", p) is False


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
    assert rule["action"]["args"] == {}, "rule must carry no literal target"
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


def test_one_rule_covers_the_whole_family():
    # corner, constant, translation AND resize tasks all resolve to the SAME rule
    # object — the covers>1 invariant (one module for the whole move family,
    # not one detector per variant; §2.5-3).
    rc = _check_solved(EASY_C, "c").s1["active-rules"][0]
    rd = _check_solved(EASY_D, "d").s1["active-rules"][0]
    re = _check_solved(EASY_E, "e").s1["active-rules"][0]
    rg = _check_solved(EASY_G, "g").s1["active-rules"][0]
    ri = _check_solved(EASY_I, "i").s1["active-rules"][0]
    assert rc == rd == re == rg == ri


if __name__ == "__main__":
    import pytest
    raise SystemExit(pytest.main([__file__, "-q"]))
