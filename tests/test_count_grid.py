"""
Tests for the *grid-level* canvas-sizing axis (R1 / §2.1 "object count ≠ 1").

The converse subject of the per-object canvas-sizing family (test_size_grid.py):
there the side is a scalar of *one* object (`object_size`/`bbox_height`); here it
is a scalar of the object *set* (`object_count`). This is the §2.5-2b point that
*which subject* feeds the dimension argument is itself part of the lifted variable
— so a count-sized task folds into the *same* `size_to_grid` family (one more
value the dimension variable ranges over), not a new family. These tests pin:
the analysis learns `object_count` on multi-object tasks; it stays disjoint from
the single-object size tasks and the move tasks; and the render reproduces the
expected solid square reading count + shared colour off the test grid.
"""

import json
import os

from agent.dsl_expr.selection import (
    analyze_object_size_grid,
    object_count_of,
    objects_of,
    GRID_DIM_PROPERTY_VOCAB,
)
from agent.conditions import match as match_condition
from agent.active_operators import PredictOperator

COUNT_TASK_PATH = os.path.join("data", "ARC_madeup", "madeup_count_to_square.json")
COUNT_B_TASK_PATH = os.path.join(
    "data", "ARC_madeup", "madeup_count_to_square_b.json")
SIZE_TASK_PATH = os.path.join("data", "ARC_madeup", "madeup_size_to_square.json")
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


# ---- grid-level property ---------------------------------------------------

def test_object_count_of_counts_objects():
    grid = [
        [3, 0, 0, 0, 0, 0, 3],
        [0, 0, 0, 0, 0, 0, 0],
        [0, 0, 0, 3, 0, 0, 0],
    ]
    assert object_count_of(objects_of(grid)) == 3
    assert "object_count" in GRID_DIM_PROPERTY_VOCAB


# ---- analysis --------------------------------------------------------------

def test_analyze_learns_count_property():
    """A multi-object task whose output side counts the objects resolves to the
    grid-level `object_count` property, grounded by the cross-pair COMM."""
    analysis = analyze_object_size_grid(_Task(_load(COUNT_TASK_PATH)).example_pairs)
    assert analysis["dim_property"] == "object_count"
    assert analysis["solid_output_all"]
    assert analysis["color_preserved_all"]
    # multi-object: it is NOT the single-object branch
    assert not analysis["single_object_all"]


def test_analyze_count_variant_size_neq_count():
    """The harder variant uses multi-cell objects (size ≠ count) so the property
    cannot be a per-object size — it still resolves to `object_count`."""
    analysis = analyze_object_size_grid(
        _Task(_load(COUNT_B_TASK_PATH)).example_pairs)
    assert analysis["dim_property"] == "object_count"


def test_single_object_task_keeps_object_property():
    """Adding the grid-level fallback must not perturb the single-object tasks:
    `object_count` there is always 1 and never matches a side > 1, so the object
    property still wins."""
    analysis = analyze_object_size_grid(_Task(_load(SIZE_TASK_PATH)).example_pairs)
    assert analysis["dim_property"] == "object_size"


def test_analyze_inert_on_move_task():
    analysis = analyze_object_size_grid(_Task(_load(MOVE_TASK_PATH)).example_pairs)
    assert analysis["dim_property"] is None


# ---- matcher ---------------------------------------------------------------

def test_matcher_fires_on_count_task():
    patterns = {"object_size_grid": analyze_object_size_grid(
        _Task(_load(COUNT_TASK_PATH)).example_pairs)}
    assert match_condition("object_size_grid", patterns, {"min_evidence": 2})


def test_matcher_inert_on_move_task():
    patterns = {"object_size_grid": analyze_object_size_grid(
        _Task(_load(MOVE_TASK_PATH)).example_pairs)}
    assert not match_condition("object_size_grid", patterns, {"min_evidence": 2})


# ---- end-to-end render -----------------------------------------------------

def test_end_to_end_predicts_count_square():
    for path in (COUNT_TASK_PATH, COUNT_B_TASK_PATH):
        task = _Task(_load(path))
        grids = PredictOperator._place_size_grid_grids(task)
        assert 0 in grids
        expected = task.test_pairs[0].output_grid.raw
        assert grids[0] == expected, f"{path}: {grids[0]} != {expected}"
