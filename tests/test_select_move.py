"""
Tests for the multi-object *selection* move (R1 / §2.5-2b).

Covers the selection-lift: when several objects are present, a learned property
selector (max_size/min_size/unique_color) picks the one the rule keeps, placed at
a constant target. The matcher fires only on the multi-object case and stays inert
on the single-object family; the reading lifts into the same `place_object`
abstraction rather than spawning a per-task rule.
"""

import json
import os

from agent.dsl_expr.selection import (
    analyze_object_select_move,
    analyze_object_move,
    objects_of,
    select_extreme,
    select_unique_color,
    select_unique_shape,
    size_of,
    SELECTOR_VOCAB,
)
from agent.conditions import match as match_condition
from agent.active_operators import PredictOperator

TASK_PATH = os.path.join("data", "ARC_madeup", "madeup_select_largest.json")
SHAPE_TASK_PATH = os.path.join("data", "ARC_madeup", "madeup_select_unique_shape.json")


class _G:
    def __init__(self, raw):
        self.raw = raw
        self.height = len(raw)
        self.width = len(raw[0]) if raw else 0


class _Pair:
    def __init__(self, inp, out=None):
        self.input_grid = _G(inp)
        self.output_grid = _G(out) if out is not None else None


class _Task:
    def __init__(self, data):
        self.example_pairs = [_Pair(d["input"], d["output"]) for d in data["train"]]
        self.test_pairs = [_Pair(d["input"], d.get("output")) for d in data["test"]]


def _load():
    with open(TASK_PATH, encoding="utf-8") as fh:
        return json.load(fh)


def _load_shape():
    with open(SHAPE_TASK_PATH, encoding="utf-8") as fh:
        return json.load(fh)


# ---- selection vocabulary --------------------------------------------------

def test_select_extreme_argmax_and_ties():
    objs = [{"size": 1}, {"size": 3}, {"size": 2}]
    assert select_extreme(objs, lambda o: o["size"], "max")["size"] == 3
    assert select_extreme(objs, lambda o: o["size"], "min")["size"] == 1
    # a tie at the extreme is ambiguous -> None
    tied = [{"size": 3}, {"size": 3}, {"size": 1}]
    assert select_extreme(tied, lambda o: o["size"], "max") is None


def test_select_unique_color_odd_one_out():
    objs = [{"color": 4}, {"color": 4}, {"color": 7}]
    assert select_unique_color(objs)["color"] == 7
    # all distinct -> several qualify -> ambiguous -> None
    assert select_unique_color([{"color": 1}, {"color": 2}]) is None


def test_select_unique_shape_odd_one_out():
    """The shape-axis selector keys on form, ignoring size and colour: two
    objects share a shape and one differs -> the odd-shape one is picked."""
    i_horiz_a = {"position": (0, 0), "cells": [(0, 0), (0, 1), (0, 2)]}
    i_horiz_b = {"position": (3, 0), "cells": [(3, 0), (3, 1), (3, 2)]}
    l_shape = {"position": (1, 4), "cells": [(1, 4), (2, 4), (2, 5)]}
    objs = [i_horiz_a, i_horiz_b, l_shape]
    assert select_unique_shape(objs) is l_shape
    # no singleton shape (all share) -> ambiguous -> None
    assert select_unique_shape([i_horiz_a, i_horiz_b]) is None


# ---- the analysis ----------------------------------------------------------

def test_select_move_learns_max_size_selector():
    task = _Task(_load())
    sel = analyze_object_select_move(task.example_pairs)
    assert sel["multi_object_all"] is True
    assert sel["size_preserved_all"] is True
    assert sel["constant_target"] == [0, 0]
    assert sel["selector"] == "max_size"


def test_select_move_learns_unique_shape_selector():
    """A task whose objects share size and colour but differ in form must fall
    through the size/colour selectors and be learned as `unique_shape` — the gap
    no existing selector could express."""
    task = _Task(_load_shape())
    sel = analyze_object_select_move(task.example_pairs)
    assert sel["multi_object_all"] is True
    assert sel["constant_target"] == [0, 0]
    assert sel["selector"] == "unique_shape"


def test_predict_unique_shape_places_at_target():
    """End-to-end: the structure renders the odd-shape object value-agnostically."""
    task = _Task(_load_shape())
    grids = PredictOperator._place_object_select_grids(task)
    assert grids[0] == _load_shape()["test"][0]["output"]


def test_single_object_family_inert_for_select():
    """The single-object easy_a family must NOT trip the selection analysis."""
    single = {
        "train": [
            {"input": [[0, 0], [0, 3]], "output": [[3, 0], [0, 0]]},
            {"input": [[0, 0], [5, 0]], "output": [[5, 0], [0, 0]]},
        ],
        "test": [{"input": [[0, 0], [0, 7]], "output": [[7, 0], [0, 0]]}],
    }
    task = _Task(single)
    sel = analyze_object_select_move(task.example_pairs)
    assert sel["multi_object_all"] is False
    assert sel["selector"] is None


# ---- matcher ---------------------------------------------------------------

def test_matcher_fires_on_selection_and_abstains_on_single():
    task = _Task(_load())
    patterns = {
        "object_select_move": analyze_object_select_move(task.example_pairs),
        "object_move": analyze_object_move(task.example_pairs),
    }
    assert match_condition("object_select_target", patterns, {"min_evidence": 2})
    # the single-object matchers must abstain on the multi-object task
    assert not match_condition("object_constant_target", patterns, {"min_evidence": 2})


def test_matcher_needs_two_examples():
    task = _Task(_load())
    one = _Task({"train": [_load()["train"][0]], "test": _load()["test"]})
    patterns = {"object_select_move": analyze_object_select_move(one.example_pairs)}
    assert not match_condition("object_select_target", patterns, {"min_evidence": 2})


# ---- prediction (value-agnostic render) ------------------------------------

def test_predict_selects_largest_and_places_at_target():
    task = _Task(_load())
    grids = PredictOperator._place_object_select_grids(task)
    assert 0 in grids
    expected = _load()["test"][0]["output"]
    assert grids[0] == expected
