"""
Tests for agent/program_synthesis.py — the Slow-path per-pair program producer.

Grounded on *real* pairs (easy000c same-size, easy000i resize) so the round-trip
is proven against data, not a toy. The producer's only contract here is faithful
reproduction of a pair through the two frozen primitives; the producer→consumer
link into ``anti_unify_pair_programs`` is exercised but its *lift quality* is
deliberately not asserted (object-level lifting is a later slice — see the module
docstring / `synthesizer_frontier`).
"""

import glob
import json
import os

import pytest

from agent.program_synthesis import (
    synthesize_pair_program,
    run_program,
    program_reproduces,
)
from program.anti_unification import anti_unify_pair_programs

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _load_task(task_id):
    matches = glob.glob(os.path.join(ROOT, "data", "**", f"{task_id}.json"),
                        recursive=True)
    assert matches, f"task {task_id} not found under data/"
    with open(matches[0]) as fh:
        return json.load(fh)


# ---- round-trip reproduction on real pairs --------------------------------

def test_reproduces_same_size_pair_easy000c():
    task = _load_task("easy000c")
    for pair in task["train"]:
        program = synthesize_pair_program(pair["input"], pair["output"])
        assert program_reproduces(program, pair["input"], pair["output"])


def test_reproduces_resize_pair_easy000i():
    task = _load_task("easy000i")
    for pair in task["train"]:
        ig, og = pair["input"], pair["output"]
        # genuine resize fixture
        assert (len(ig), len(ig[0])) != (len(og), len(og[0]))
        program = synthesize_pair_program(ig, og)
        assert program[0]["dsl"] == "make_grid"
        assert program_reproduces(program, ig, og)


# ---- producer shape contracts ---------------------------------------------

def test_identity_pair_yields_empty_program():
    grid = [[1, 2], [3, 4]]
    assert synthesize_pair_program(grid, grid) == []
    # empty program is a faithful no-op
    assert run_program([], grid) == grid


def test_same_size_program_is_coloring_only():
    inp = [[0, 0], [0, 0]]
    out = [[0, 5], [3, 0]]
    program = synthesize_pair_program(inp, out)
    assert all(line["dsl"] == "coloring" for line in program)
    assert program_reproduces(program, inp, out)


def test_same_size_one_line_per_changed_color():
    # two cells -> colour 5, one cell -> colour 3: exactly two coloring lines
    inp = [[0, 0, 0], [0, 0, 0]]
    out = [[5, 5, 0], [3, 0, 0]]
    program = synthesize_pair_program(inp, out)
    assert len(program) == 2
    colors = sorted(line["args"]["color"] for line in program)
    assert colors == [3, 5]
    # lines are deterministic (ascending colour)
    assert [line["args"]["color"] for line in program] == [3, 5]


def test_resize_canvas_uses_output_background():
    inp = [[7]]
    out = [[2, 2, 2], [2, 9, 2]]  # background 2 (5 of 6), one 9
    program = synthesize_pair_program(inp, out)
    head = program[0]
    assert head["dsl"] == "make_grid"
    assert head["args"] == {"height": 2, "width": 3, "color": 2}
    # only the non-background cell is painted
    assert [l["args"]["color"] for l in program[1:]] == [9]
    assert program_reproduces(program, inp, out)


def test_run_program_does_not_mutate_input():
    inp = [[0, 0], [0, 0]]
    snapshot = [row[:] for row in inp]
    out = [[1, 0], [0, 0]]
    program = synthesize_pair_program(inp, out)
    run_program(program, inp)
    assert inp == snapshot


# ---- producer -> consumer link (anti_unify_pair_programs) ------------------

def test_two_pair_programs_feed_anti_unification():
    """≥2 synthesized programs flow into ``anti_unify_pair_programs`` without
    error and yield a program (lift *quality* is a later object-level slice)."""
    task = _load_task("easy000c")
    programs = [synthesize_pair_program(p["input"], p["output"])
                for p in task["train"][:2]]
    assert len(programs) == 2
    lifted = anti_unify_pair_programs(programs)
    assert isinstance(lifted, list)
    # the skeleton is preserved: same number of coloring lines across the pair
    assert len(lifted) == len(programs[0])
