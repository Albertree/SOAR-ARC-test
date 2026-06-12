"""
Tests for the *non-square* canvas-sizing axis (R1 / §2.1 "grid size = f(object
property)", the h ≠ w case).

The scalar canvas-sizing readings (test_size_grid.py / test_count_grid.py) each
size a *square* — one value reused for both axes. This pins the smaller step into
a *non-square* output: a single named *rectangular* reading (`bbox_extent`) that
yields the object's bounding box ``(h, w)`` at once. Treating the pair as one named
value lets it fold into the *same* `size_to_grid` family (one more value the
dimension variable ranges over, like `object_count`) rather than spawning a new
family — covers rises while the rule count holds (§2.5-4). These tests pin: the
rect reading is value-agnostic; the analysis learns `bbox_extent` on a non-square
task; square tasks are untouched (still resolve to their scalar reading); it stays
disjoint from the move tasks; the matcher fires; and the render reproduces the
expected `h × w` rectangle off the test object.
"""

import json
import os

from agent.dsl_expr.selection import (
    analyze_object_size_grid,
    bbox_extent_of,
    bbox_height_of,
    bbox_width_of,
    objects_of,
    unique_object,
    RECT_DIM_VOCAB,
)
from agent.dsl_expr.render import render_solid_rect
from agent.conditions import match as match_condition
from agent.active_operators import PredictOperator

RECT_TASK_PATH = os.path.join(
    "data", "ARC_madeup", "madeup_bbox_extent_to_rect.json")
RECT_B_TASK_PATH = os.path.join(
    "data", "ARC_madeup", "madeup_bbox_extent_to_rect_b.json")
SIZE_TASK_PATH = os.path.join("data", "ARC_madeup", "madeup_size_to_square.json")
BBOXH_TASK_PATH = os.path.join(
    "data", "ARC_madeup", "madeup_bbox_height_to_square.json")
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


# ---- rectangular property reading ------------------------------------------

def test_bbox_extent_reads_pair():
    """`bbox_extent_of` returns the object's (height, width) — distinct values for
    a non-square L-shape, and its components equal the named scalar readings."""
    grid = [
        [5, 0, 0, 0],
        [5, 5, 5, 0],   # bbox 2 x 3 L-shape
    ]
    obj = unique_object(grid)
    assert bbox_extent_of(obj) == (2, 3)
    assert bbox_height_of(obj) == 2
    assert bbox_width_of(obj) == 3
    assert "bbox_extent" in RECT_DIM_VOCAB


# ---- analysis --------------------------------------------------------------

def test_analyze_learns_bbox_extent():
    """A non-square task whose output is the object's bbox extent resolves to the
    `bbox_extent` reading, grounded by the cross-pair (h, w) COMM."""
    analysis = analyze_object_size_grid(_Task(_load(RECT_TASK_PATH)).example_pairs)
    assert analysis["dim_property"] == "bbox_extent"
    assert analysis["selector"] is None
    assert analysis["solid_output_all"]
    assert analysis["color_preserved_all"]
    # genuinely non-square: every output has h != w
    for p in analysis["per_pair"]:
        assert not p["out_square"]


def test_analyze_learns_bbox_extent_variant():
    """A second, differently-shaped/coloured non-square task also resolves to
    `bbox_extent` — the reading is value-agnostic (covers 2, §2.5-3)."""
    analysis = analyze_object_size_grid(
        _Task(_load(RECT_B_TASK_PATH)).example_pairs)
    assert analysis["dim_property"] == "bbox_extent"


def test_square_tasks_keep_scalar_reading():
    """Dropping the global square requirement must NOT perturb the square tasks:
    the scalar paths re-impose squareness, so each still resolves to its scalar
    reading rather than to `bbox_extent`."""
    assert analyze_object_size_grid(
        _Task(_load(SIZE_TASK_PATH)).example_pairs)["dim_property"] == "object_size"
    assert analyze_object_size_grid(
        _Task(_load(BBOXH_TASK_PATH)).example_pairs)["dim_property"] == "bbox_height"
    assert analyze_object_size_grid(
        _Task(_load(COUNT_TASK_PATH)).example_pairs)["dim_property"] == "object_count"


def test_analyze_inert_on_move_task():
    analysis = analyze_object_size_grid(_Task(_load(MOVE_TASK_PATH)).example_pairs)
    assert analysis["dim_property"] is None


# ---- matcher ---------------------------------------------------------------

def test_matcher_fires_on_rect_task():
    patterns = {"object_size_grid": analyze_object_size_grid(
        _Task(_load(RECT_TASK_PATH)).example_pairs)}
    assert match_condition("object_size_grid", patterns, {"min_evidence": 2})


def test_matcher_inert_on_move_task():
    patterns = {"object_size_grid": analyze_object_size_grid(
        _Task(_load(MOVE_TASK_PATH)).example_pairs)}
    assert not match_condition("object_size_grid", patterns, {"min_evidence": 2})


# ---- render ----------------------------------------------------------------

def test_render_solid_rect_shape():
    g = render_solid_rect(2, 4, 7)
    assert g == [[7, 7, 7, 7], [7, 7, 7, 7]]
    # degenerate dims yield an empty canvas, never a crash
    assert render_solid_rect(0, 3, 7) == []


# ---- end-to-end render -----------------------------------------------------

def test_end_to_end_predicts_rectangle():
    for path in (RECT_TASK_PATH, RECT_B_TASK_PATH):
        task = _Task(_load(path))
        grids = PredictOperator._place_size_grid_grids(task)
        assert 0 in grids
        expected = task.test_pairs[0].output_grid.raw
        assert grids[0] == expected, f"{path}: {grids[0]} != {expected}"
        # the prediction is genuinely non-square
        assert len(grids[0]) != len(grids[0][0])
