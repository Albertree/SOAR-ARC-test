"""
Tests for the synthesizer's cell-gravity schema (Schema 15, program/synthesis.py).

Every non-background cell slides along one direction until blocked by the grid
edge or a settled cell, per line, preserving order within the line — the recurring
ARC "everything falls / piles to one side" family. The direction is the whole
per-task content carried in ONE `gravity` const leaf (the settled grid is composed
from the two frozen primitives `make_grid` + `coloring` at run time), so a
fall-down task and a fall-up task share the SAME one-step skeleton
``[("gravity", ("const", ?v))]`` and lift via unify() into one covers>1 rule (R3),
never a rule per direction (BACKLOG_LOOP §2.5-3/4).
"""

from program.synthesis import (
    run_program, synthesize_task, _fit_gravity,
)
from agent.memory import _program_skeleton


# --- gravity down: cells fall to the bottom of each column -------------------

def test_fit_gravity_down():
    pairs = [
        {"input":  [[5, 0, 6], [0, 0, 0], [0, 6, 0]],
         "output": [[0, 0, 0], [0, 0, 0], [5, 6, 6]]},
        {"input":  [[3, 0, 0], [0, 4, 0], [0, 0, 0]],
         "output": [[0, 0, 0], [0, 0, 0], [3, 4, 0]]},
    ]
    prog = _fit_gravity(pairs)
    assert prog is not None
    assert prog[0][0] == "gravity"
    assert prog[0][1][1] == "down"
    for p in pairs:
        assert run_program(prog, p["input"]) == p["output"]


# --- gravity up: cells rise to the top, stacking order preserved -------------

def test_fit_gravity_up_preserves_order():
    # Two stacked cells in a column fall *up*; the one nearer the top stays on top.
    pairs = [
        {"input":  [[0, 0], [5, 0], [6, 0]],
         "output": [[5, 0], [6, 0], [0, 0]]},
        {"input":  [[0, 7], [0, 0], [0, 8]],
         "output": [[0, 7], [0, 8], [0, 0]]},
    ]
    prog = _fit_gravity(pairs)
    assert prog is not None
    assert prog[0][1][1] == "up"
    for p in pairs:
        assert run_program(prog, p["input"]) == p["output"]


# --- gravity left/right ------------------------------------------------------

def test_fit_gravity_right():
    pairs = [
        {"input":  [[5, 0, 6], [0, 3, 0]],
         "output": [[0, 5, 6], [0, 0, 3]]},
    ]
    prog = _fit_gravity(pairs)
    assert prog is not None
    assert prog[0][1][1] == "right"
    for p in pairs:
        assert run_program(prog, p["input"]) == p["output"]


# --- an already-settled grid is NOT a gravity task (identity owns it) ---------

def test_settled_grid_is_not_gravity():
    # Output equals input -> no direction changes anything -> declines.
    pairs = [{"input": [[0, 0], [5, 6]], "output": [[0, 0], [5, 6]]}]
    assert _fit_gravity(pairs) is None


# --- two divergent-direction tasks share ONE skeleton (lift into covers>1) ----

def test_down_and_up_tasks_share_skeleton():
    down = [
        {"input":  [[5, 0], [0, 0]],
         "output": [[0, 0], [5, 0]]},
    ]
    up = [
        {"input":  [[0, 0], [0, 6]],
         "output": [[0, 6], [0, 0]]},
    ]
    a = _fit_gravity(down)
    b = _fit_gravity(up)
    assert a is not None and b is not None
    # Different fitted direction leaves, but the SAME structural skeleton.
    assert a[0][1][1] != b[0][1][1]
    assert _program_skeleton(a) == _program_skeleton(b)


# --- reachable through the full search, and only when it actually fits --------

def test_synthesize_task_finds_gravity():
    pairs = [
        {"input":  [[5, 0, 6], [0, 0, 0], [0, 6, 0]],
         "output": [[0, 0, 0], [0, 0, 0], [5, 6, 6]]},
        {"input":  [[3, 0, 0], [0, 4, 0], [0, 0, 0]],
         "output": [[0, 0, 0], [0, 0, 0], [3, 4, 0]]},
    ]
    prog = synthesize_task(pairs)
    assert prog is not None
    assert prog[0][0] == "gravity"
