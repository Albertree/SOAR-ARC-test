"""
Tests for the constant_output *consume* path (iter 6): recognition →
make_grid+coloring materialisation → prediction.

The recognition half (agent/conditions/constant_output.py) and the DSL
substrate (procedural_memory/DSL/) already existed; this verifies the bridge
that was missing — GeneralizeOperator emitting a value-agnostic program and
PredictOperator executing it via apply_DSL.
"""

import json
import os

from agent.dsl_compose import build_constant_output_program
from agent.active_operators import PredictOperator


# --- grid -> make_grid+coloring decomposition -------------------------------

def test_program_rebuilds_grid_exactly():
    grid = [
        [0, 0, 0, 0, 0, 0],
        [0, 0, 0, 0, 0, 0],
        [0, 0, 0, 0, 0, 0],
        [0, 0, 0, 0, 0, 0],
        [0, 0, 0, 0, 0, 0],
        [0, 0, 0, 0, 0, 2],
    ]
    program = build_constant_output_program(grid)
    # make_grid canvas + one coloring overlay for the single non-bg colour (2).
    assert program[0]["dsl"] == "make_grid"
    assert program[0]["args"] == {"height": 6, "width": 6, "color": 0}
    assert any(s["dsl"] == "coloring" and s["args"]["color"] == 2 for s in program)
    rebuilt = PredictOperator._run_dsl_program(program)
    assert rebuilt == grid


def test_program_is_value_agnostic():
    """A different common grid yields a different program — no literal baked in."""
    grid = [[3, 0], [0, 0]]
    program = build_constant_output_program(grid)
    rebuilt = PredictOperator._run_dsl_program(program)
    assert rebuilt == grid
    # background is the modal colour (0), the painted colour is whatever's there
    assert program[0]["args"]["color"] == 0
    assert any(s["dsl"] == "coloring" and s["args"]["color"] == 3 for s in program)


def test_multi_color_grid_one_overlay_per_color():
    grid = [[5, 6], [6, 5]]  # tie on count -> bg is smallest (5)
    program = build_constant_output_program(grid)
    assert program[0]["args"]["color"] == 5
    coloring_colors = sorted(s["args"]["color"] for s in program if s["dsl"] == "coloring")
    assert coloring_colors == [6]
    assert PredictOperator._run_dsl_program(program) == grid


def test_empty_or_ragged_grid_returns_none():
    assert build_constant_output_program([]) is None
    assert build_constant_output_program([[1, 2], [3]]) is None


# --- end-to-end: predictor applies a constant_output rule -------------------

def test_predict_applies_constant_output_rule():
    common = [
        [0, 0, 0, 0, 0, 0],
        [0, 0, 0, 0, 0, 0],
        [0, 0, 0, 0, 0, 0],
        [0, 0, 0, 0, 0, 0],
        [0, 0, 0, 0, 0, 0],
        [0, 0, 0, 0, 0, 2],
    ]
    rule = {
        "type": "constant_output",
        "dsl_program": build_constant_output_program(common),
        "confidence": 1.0,
    }

    class _G:
        raw = [[4 if (r, c) == (4, 2) else 0 for c in range(6)] for r in range(6)]

    out = PredictOperator()._apply_rule(rule, _G())
    # Output is the common grid regardless of the (different) test input.
    assert out == common


def test_real_easy000a_program_matches_test_output():
    path = os.path.join("data", "ARC_easy_a", "easy000a.json")
    if not os.path.isfile(path):
        return  # dataset not present in this checkout
    task = json.load(open(path))
    common = task["train"][0]["output"]
    program = build_constant_output_program(common)
    assert PredictOperator._run_dsl_program(program) == task["test"][0]["output"]
