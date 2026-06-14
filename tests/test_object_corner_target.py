"""
Tests for R1's object-level corner-move capability (BACKLOG_LOOP.md R1):

  * the seed selection vocabulary (agent/dsl_expr.selection),
  * the `object_corner_target` condition matcher,
  * end-to-end: the ExtractPattern -> Generalize -> Predict path solves
    easy000c and easy000g with one value-agnostic rule, built only from
    make_grid + coloring.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agent.dsl_expr import objects_of, unique_object, bottom_right_of, color_of
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


# --- matcher ---------------------------------------------------------------

def _corner_motion(n=2):
    pair = {
        "single_in": True, "single_out": True,
        "color_preserved": True, "size_preserved": True,
        "grid_size_preserved": True, "out_at_corner": True,
    }
    return {"object_motion": {"evidence_count": n, "pairs": [dict(pair) for _ in range(n)]}}


def test_matcher_fires_on_corner():
    assert match_condition("object_corner_target", _corner_motion(2)) is True


def test_matcher_needs_min_evidence():
    assert match_condition("object_corner_target", _corner_motion(1)) is False


def test_matcher_rejects_non_corner():
    p = _corner_motion(2)
    p["object_motion"]["pairs"][0]["out_at_corner"] = False
    assert match_condition("object_corner_target", p) is False


def test_matcher_rejects_recolor():
    p = _corner_motion(2)
    p["object_motion"]["pairs"][1]["color_preserved"] = False
    assert match_condition("object_corner_target", p) is False


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
    def __init__(self, train, test):
        self.task_hex = "test_corner"
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


def _solve(spec):
    task = _Task(spec["train"], spec["test"])
    wm = _WM(task)
    ExtractPatternOperator().effect(wm)
    GeneralizeOperator().effect(wm)
    PredictOperator().effect(wm)
    return wm, task


def test_pipeline_solves_easy_c():
    wm, task = _solve(EASY_C)
    rule = wm.s1["active-rules"][0]
    assert rule["type"] == "object_corner_target"
    assert "condition" in rule and "action" in rule
    pred = wm.s1["predictions"]["test_0"]
    assert pred == task.test_pairs[0].output_grid.raw


def test_pipeline_solves_easy_g_same_rule():
    wm_c, _ = _solve(EASY_C)
    wm_g, task_g = _solve(EASY_G)
    # Same value-agnostic rule object for both tasks (the covers>1 invariant).
    assert wm_c.s1["active-rules"][0] == wm_g.s1["active-rules"][0]
    pred = wm_g.s1["predictions"]["test_0"]
    assert pred == task_g.test_pairs[0].output_grid.raw


if __name__ == "__main__":
    import pytest
    raise SystemExit(pytest.main([__file__, "-q"]))
