"""
Tests for the object-property *canvas-sizing* family (R1 / §2.1 "grid size is a
function of an object's property").

Covers the dimension-argument lift: the output is a solid square whose side is a
learned scalar object property (`object_size`) and whose colour is the object's
colour. The reading is value-agnostic (colour/size/shape/position) and fires only
when the output is a solid square sized by the property in every pair, staying
inert on the object-move families. The two self-authored size tasks fold into one
abstract rule (covers=2), demonstrating the abstraction generalizes rather than
accreting per task.
"""

import json
import os

from agent.dsl_expr.selection import (
    analyze_object_size_grid,
    analyze_object_move,
    DIM_PROPERTY_VOCAB,
)
from agent.dsl_expr.render import render_solid_square
from agent.conditions import match as match_condition
from agent.active_operators import PredictOperator

TASK_PATH = os.path.join("data", "ARC_madeup", "madeup_size_to_square.json")
BIG_TASK_PATH = os.path.join("data", "ARC_madeup", "madeup_size_to_square_big.json")
MOVE_TASK_PATH = os.path.join("data", "ARC_madeup", "madeup_select_largest.json")


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


def _load(path):
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


# ---- render helper ---------------------------------------------------------

def test_render_solid_square_is_make_grid_only():
    """A side×side uniform fill bottoms out in a single make_grid call."""
    grid = render_solid_square(3, 4)
    assert grid == [[4, 4, 4], [4, 4, 4], [4, 4, 4]]
    # degenerate side -> empty canvas, never a crash
    assert render_solid_square(0, 4) == []


# ---- analysis --------------------------------------------------------------

def test_analyze_learns_size_property():
    """The analysis discovers that the output side equals the object's cell-count
    in every pair, value-agnostic in colour/shape/position/grid size."""
    analysis = analyze_object_size_grid(_Task(_load(TASK_PATH)).example_pairs)
    assert analysis["single_object_all"]
    assert analysis["solid_output_all"]
    assert analysis["color_preserved_all"]
    assert analysis["dim_property"] == "object_size"


def test_analyze_big_variant_same_property():
    """The harder variant (7×7 grids, bigger objects, different colours) resolves
    to the *same* dimension property — the abstraction is value-agnostic."""
    analysis = analyze_object_size_grid(_Task(_load(BIG_TASK_PATH)).example_pairs)
    assert analysis["dim_property"] == "object_size"


def test_analyze_inert_on_move_task():
    """On a move task (output is the placed object, not a solid square sized by a
    property) the analysis abstains — disjoint from the move readings."""
    analysis = analyze_object_size_grid(_Task(_load(MOVE_TASK_PATH)).example_pairs)
    assert analysis["dim_property"] is None


# ---- matcher ---------------------------------------------------------------

def test_matcher_fires_on_size_task_only():
    patterns = {"object_size_grid": analyze_object_size_grid(
        _Task(_load(TASK_PATH)).example_pairs)}
    assert match_condition("object_size_grid", patterns, {"min_evidence": 2})

    move_patterns = {"object_size_grid": analyze_object_size_grid(
        _Task(_load(MOVE_TASK_PATH)).example_pairs)}
    assert not match_condition("object_size_grid", move_patterns, {"min_evidence": 2})


def test_matcher_needs_evidence():
    """A single pair cannot establish that a *property* (not a coincidental
    constant size) drives the output."""
    data = _load(TASK_PATH)
    one_pair = {"train": data["train"][:1], "test": data["test"]}
    patterns = {"object_size_grid": analyze_object_size_grid(
        _Task(one_pair).example_pairs)}
    assert not match_condition("object_size_grid", patterns, {"min_evidence": 2})


# ---- end-to-end render -----------------------------------------------------

def _predict(task):
    grids = PredictOperator._place_size_grid_grids(task)
    return grids


def test_end_to_end_predicts_expected_square():
    for path in (TASK_PATH, BIG_TASK_PATH):
        task = _Task(_load(path))
        grids = _predict(task)
        assert 0 in grids
        expected = task.test_pairs[0].output_grid.raw
        assert grids[0] == expected, f"{path}: {grids[0]} != {expected}"


def test_predict_empty_on_move_task():
    """The size-grid render declines (returns {}) on a move task — it does not
    crash or mis-fire on a shape it does not own."""
    assert _predict(_Task(_load(MOVE_TASK_PATH))) == {}


def test_dim_property_vocab_is_callable():
    assert "object_size" in DIM_PROPERTY_VOCAB
    obj = {"size": 5, "cells": [(0, 0)], "position": (0, 0)}
    assert DIM_PROPERTY_VOCAB["object_size"](obj) == 5
