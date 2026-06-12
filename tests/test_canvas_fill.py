"""
Tests for the solid-canvas colour-fill family (BACKLOG_LOOP.md R1 / §2.5-2b
colour reading): the output is a solid canvas at the input's own size whose colour
is a learned grid colour-reading (`most_frequent_color`).

Grounded on the *real* ARC-AGI-2 training task 5582e5ca ("fill the grid with its
dominant colour"), which the agent failed before this family (rule=identity) and
which `color_remap` structurally cannot express (the same source colour maps to a
different fill across pairs → the map is not a function → it abstains). The colour
analogue of `object_size_grid`: a single frozen `make_grid` fill whose *colour
argument* is the lift, read off the test input (P5).
"""

import glob
import json
import os

from agent.conditions import CONDITION_REGISTRY, match as match_condition
from agent.dsl_expr.selection import (
    analyze_canvas_fill,
    most_frequent_color,
    COLOR_READING_VOCAB,
)
from agent.active_operators import GeneralizeOperator, CANVAS_FILL_DSL

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _load_task(task_id):
    matches = glob.glob(os.path.join(ROOT, "data", "**", f"{task_id}.json"),
                        recursive=True)
    assert matches, f"task {task_id} not found under data/"
    with open(matches[0]) as fh:
        return json.load(fh)


class _G:
    def __init__(self, raw):
        self.raw = raw


class _Pair:
    def __init__(self, inp, out):
        self.input_grid = _G(inp)
        self.output_grid = _G(out)


def _pairs(rows):
    return [_Pair(i, o) for i, o in rows]


# ---- the colour reading ----------------------------------------------------

def test_most_frequent_color_reading():
    assert most_frequent_color([[4, 4, 8], [6, 6, 3], [3, 0, 4]]) == 4
    # tie -> smallest colour (deterministic)
    assert most_frequent_color([[1, 2], [2, 1]]) == 1
    assert "most_frequent_color" in COLOR_READING_VOCAB


# ---- analyzer reading ------------------------------------------------------

def test_analyze_canvas_fill_learns_reading_on_real_task():
    task = _load_task("5582e5ca")
    pairs = _pairs([(p["input"], p["output"]) for p in task["train"]])
    sig = analyze_canvas_fill(pairs)
    assert sig["fill_reading"] == "most_frequent_color"
    assert sig["consistent"] is True
    assert sig["evidence"] == len(task["train"])


def test_analyze_canvas_fill_declines_on_non_solid_output():
    # output is not a single colour -> not a canvas fill
    pairs = _pairs([
        ([[2, 2], [2, 2]], [[2, 3], [2, 2]]),
        ([[5, 5], [5, 5]], [[5, 1], [5, 5]]),
    ])
    sig = analyze_canvas_fill(pairs)
    assert sig["fill_reading"] is None
    assert sig["consistent"] is False


def test_analyze_canvas_fill_declines_on_resize():
    # solid output but different size from the input -> not this family (the seed
    # restricts to the input's own size; a resized variant is a later step)
    pairs = _pairs([
        ([[4, 4, 8], [4, 6, 6]], [[4, 4], [4, 4]]),
        ([[9, 9, 1], [9, 8, 8]], [[9, 9], [9, 9]]),
    ])
    sig = analyze_canvas_fill(pairs)
    assert sig["fill_reading"] is None


def test_analyze_canvas_fill_declines_when_reading_inconsistent():
    # solid same-size fill, but the fill colour is NOT the input's most-frequent
    # colour in pair 2 -> no reading reproduces it -> abstain (honest)
    pairs = _pairs([
        ([[4, 4, 8], [6, 6, 3], [3, 0, 4]], [[4, 4, 4], [4, 4, 4], [4, 4, 4]]),
        ([[9, 9, 1], [9, 8, 8], [1, 2, 2]], [[5, 5, 5], [5, 5, 5], [5, 5, 5]]),
    ])
    sig = analyze_canvas_fill(pairs)
    assert sig["fill_reading"] is None


# ---- matcher (P5) ----------------------------------------------------------

def test_canvas_fill_matcher_registered():
    assert "canvas_fill" in CONDITION_REGISTRY


def test_canvas_fill_matcher_honours_min_evidence():
    task = _load_task("5582e5ca")
    pairs = _pairs([(p["input"], p["output"]) for p in task["train"]])
    patterns = {"canvas_fill": analyze_canvas_fill(pairs)}
    assert match_condition("canvas_fill", patterns, {"min_evidence": 2}) is True
    # one example can't establish the family is constant
    assert match_condition("canvas_fill", patterns, {"min_evidence": 99}) is False


# ---- generalize emits a canonical (condition-bearing) rule -----------------

def test_generalize_emits_canonical_canvas_fill_rule():
    task = _load_task("5582e5ca")
    pairs = _pairs([(p["input"], p["output"]) for p in task["train"]])
    patterns = {"canvas_fill": analyze_canvas_fill(pairs)}
    op = GeneralizeOperator()
    rule = op._canvas_fill_rule(patterns)
    assert rule is not None
    # canonical {condition, action} shape, NOT a legacy {type: ...} envelope
    assert "type" not in rule
    assert rule["condition"]["type"] == "canvas_fill"
    assert rule["action"]["dsl"] == CANVAS_FILL_DSL
    assert rule["action"]["args"]["fill_reading"] == "most_frequent_color"
    assert rule["category"] == "canvas_fill"


def test_canvas_fill_rule_none_when_not_a_fill():
    pairs = _pairs([
        ([[2, 2], [2, 2]], [[2, 3], [2, 2]]),
        ([[5, 5], [5, 5]], [[5, 1], [5, 5]]),
    ])
    patterns = {"canvas_fill": analyze_canvas_fill(pairs)}
    op = GeneralizeOperator()
    assert op._canvas_fill_rule(patterns) is None


# ---- end-to-end predict on the real task -----------------------------------

def test_canvas_fill_predicts_real_task_test_pair():
    """The whole point: recompute the reading from the examples and apply it to the
    *test* input (its own size and dominant colour, P5) — reproducing 5582e5ca's
    held-out test output exactly, via the frozen make_grid primitive."""
    task = _load_task("5582e5ca")

    class _Task:
        example_pairs = _pairs([(p["input"], p["output"]) for p in task["train"]])
        test_pairs = _pairs([(p["input"], p["output"]) for p in task["test"]])

    from agent.active_operators import PredictOperator
    out = PredictOperator._canvas_fill_grids(_Task())
    assert 0 in out
    expected = task["test"][0]["output"]
    assert out[0] == expected
