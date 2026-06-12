"""
Tests for the *selected-object* canvas-sizing axis (R1 / §2.5-2b).

The third subject form of the canvas-sizing family. test_size_grid.py reads a
scalar off *one* object; test_count_grid.py reads a scalar off the object *set*
(`object_count`). Here several objects are present and the dimension is a scalar
of *one chosen* object — the §2.1 "multi-object selection" concept folded into the
size-grid family. This is the §2.5-2b composition of the two grown LHS
vocabularies: a `SELECTOR_VOCAB` selector names the subject and a
`DIM_PROPERTY_VOCAB` property reads its dimension, so the lifted argument is
`size_of(max_size(objects_of(in)))`. These tests pin: the analysis learns the
(selector, property) pair grounded by the cross-pair COMM; it stays disjoint from
the single-object / count / move tasks; the render reproduces the expected solid
square off the *selected* test object; and the matcher fires. Because the lift
keys only on `dim_property`, both selector tasks fold into the existing
`size_to_grid` abstraction (covers up, rule count flat) — verified by the probe.
"""

import json
import os

from agent.dsl_expr.selection import analyze_object_size_grid
from agent.conditions import match as match_condition
from agent.active_operators import PredictOperator

SELECT_TASK_PATH = os.path.join(
    "data", "ARC_madeup", "madeup_select_size_to_square.json")
SELECT_B_TASK_PATH = os.path.join(
    "data", "ARC_madeup", "madeup_select_size_to_square_b.json")
SIZE_TASK_PATH = os.path.join("data", "ARC_madeup", "madeup_size_to_square.json")
COUNT_TASK_PATH = os.path.join("data", "ARC_madeup", "madeup_count_to_square.json")
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


# ---- analysis --------------------------------------------------------------

def test_analyze_learns_selector_and_property():
    """A multi-object task whose output side = the *largest* object's cell-count
    resolves to (selector=max_size, dim_property=object_size), grounded by the
    cross-pair COMM on both the size and the selected object's colour."""
    for path in (SELECT_TASK_PATH, SELECT_B_TASK_PATH):
        analysis = analyze_object_size_grid(_Task(_load(path)).example_pairs)
        assert analysis["dim_property"] == "object_size", path
        assert analysis["selector"] == "max_size", path
        assert analysis["solid_output_all"], path
        assert analysis["color_preserved_all"], path
        # genuinely multi-object: NOT the single-object branch
        assert not analysis["single_object_all"], path


def test_single_object_task_uses_no_selector():
    """Adding the selector path must not perturb the single-object tasks: a single
    subject accounts for the size, so the selector is never reached (it stays
    None) and the plain object property still wins."""
    analysis = analyze_object_size_grid(_Task(_load(SIZE_TASK_PATH)).example_pairs)
    assert analysis["dim_property"] == "object_size"
    assert analysis["selector"] is None


def test_count_task_uses_no_selector():
    """The grid-level (object_count) subject is tried before the selector path, so
    a count-sized task keeps resolving to object_count with no selector."""
    analysis = analyze_object_size_grid(_Task(_load(COUNT_TASK_PATH)).example_pairs)
    assert analysis["dim_property"] == "object_count"
    assert analysis["selector"] is None


def test_analyze_inert_on_move_task():
    analysis = analyze_object_size_grid(_Task(_load(MOVE_TASK_PATH)).example_pairs)
    assert analysis["dim_property"] is None
    assert analysis["selector"] is None


# ---- matcher ---------------------------------------------------------------

def test_matcher_fires_on_select_task():
    patterns = {"object_size_grid": analyze_object_size_grid(
        _Task(_load(SELECT_TASK_PATH)).example_pairs)}
    assert match_condition("object_size_grid", patterns, {"min_evidence": 2})


# ---- end-to-end render -----------------------------------------------------

def test_end_to_end_predicts_selected_square():
    for path in (SELECT_TASK_PATH, SELECT_B_TASK_PATH):
        task = _Task(_load(path))
        grids = PredictOperator._place_size_grid_grids(task)
        assert 0 in grids, path
        expected = task.test_pairs[0].output_grid.raw
        assert grids[0] == expected, f"{path}: {grids[0]} != {expected}"
