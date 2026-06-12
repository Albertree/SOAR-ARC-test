"""
Tests for the Slow-path per-pair program synthesizer
(`agent/program_synthesis.py`, BACKLOG_LOOP.md R5 / modules F/G).

The synthesizer is the missing general solve path (iter-25 reframe): from a
single example pair's COMM/DIFF it emits an *overfit* literal `coloring`/
`make_grid` program — the anti-unification *input material* §2.5-3 blesses —
rather than routing the task into a tenth hand-built in-code family. This slice
is the pure function; the ground is the round-trip property
`run_program(synthesize_pair_program(i, o), i) == o` on **real** ARC pairs.

Layers:
  * round-trip — synthesized programs replay back to the exact output, on real
                 easy000c/d pairs and on synthetic identity / resize cases.
  * shape      — the program uses only the two frozen primitives, is value-
                 agnostic (works for any colour), and is deterministic.
  * comm/diff  — a same-shape program touches only the cells that changed (COMM
                 cells carry no step), so it edits rather than rebuilds.
"""

import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agent.program_synthesis import (  # noqa: E402
    synthesize_pair_program, run_program,
)


# ── helpers ───────────────────────────────────────────────────────────
def _load_task(task_path, data_root="data"):
    from managers.arc_manager import ARCManager
    with tempfile.TemporaryDirectory() as tmp:
        return ARCManager(data_root=data_root,
                          semantic_memory_root=tmp).load_task(task_path)


def _pairs(task):
    return [(p.input_grid.raw, p.output_grid.raw) for p in task.example_pairs]


# ── round-trip on real pairs (the ground) ─────────────────────────────
def test_round_trip_easy000c_every_pair():
    # easy000c: a single coloured pixel moves to the bottom-right corner, colour
    # preserved. Same-shape (6×6), so a DIFF program: erase the source cell,
    # paint (5,5). The program must replay back to the exact output.
    task = _load_task("ARC_easy_a/easy000c")
    for in_grid, out_grid in _pairs(task):
        program = synthesize_pair_program(in_grid, out_grid)
        assert run_program(program, in_grid) == out_grid


def test_round_trip_easy000d_every_pair():
    # A second real single-object mover (lands interior, not a corner) — a
    # different task that the *same* synthesizer handles with no special case.
    task = _load_task("ARC_easy_a/easy000d")
    for in_grid, out_grid in _pairs(task):
        program = synthesize_pair_program(in_grid, out_grid)
        assert run_program(program, in_grid) == out_grid


def test_round_trip_value_agnostic():
    # The same source→target move with a different colour synthesizes the same
    # *structure* and still round-trips — no colour is hard-coded.
    for color in (2, 1, 4, 7):
        in_grid = [[0, 0, 0], [0, color, 0], [0, 0, 0]]
        out_grid = [[0, 0, 0], [0, 0, 0], [0, 0, color]]
        program = synthesize_pair_program(in_grid, out_grid)
        assert run_program(program, in_grid) == out_grid


# ── synthetic edge cases ──────────────────────────────────────────────
def test_identity_pair_is_empty_program():
    grid = [[0, 1], [2, 3]]
    program = synthesize_pair_program(grid, grid)
    assert program == []
    assert run_program(program, grid) == grid


def test_resized_output_uses_make_grid():
    # Output is a different shape, so the program rebuilds from scratch: a
    # make_grid background then coloring for the foreground.
    in_grid = [[5, 5, 5, 5], [5, 5, 5, 5]]
    out_grid = [[0, 0], [0, 3]]            # smaller canvas, bg 0, one 3
    program = synthesize_pair_program(in_grid, out_grid)
    assert program[0]["dsl"] == "make_grid"
    assert program[0]["args"] == {"height": 2, "width": 2, "color": 0}
    assert run_program(program, in_grid) == out_grid


# ── shape: frozen primitives only, COMM/DIFF discipline ───────────────
def test_program_uses_only_frozen_primitives():
    task = _load_task("ARC_easy_a/easy000c")
    for in_grid, out_grid in _pairs(task):
        for step in synthesize_pair_program(in_grid, out_grid):
            assert step["dsl"] in ("make_grid", "coloring")


def test_same_shape_program_touches_only_changed_cells():
    # A two-cell change → coloring steps cover exactly those two cells, nothing
    # else (COMM cells carry no step — the program edits, not rebuilds).
    in_grid = [[0, 0, 0], [0, 2, 0], [0, 0, 0]]
    out_grid = [[0, 0, 0], [0, 0, 0], [0, 0, 2]]   # (1,1):2->0 and (2,2):0->2
    program = synthesize_pair_program(in_grid, out_grid)
    painted = set()
    for step in program:
        assert step["dsl"] == "coloring"           # no make_grid for same shape
        for cell in step["args"]["selection"]:
            painted.add(tuple(cell))
    assert painted == {(1, 1), (2, 2)}


def test_deterministic():
    task = _load_task("ARC_easy_a/easy000c")
    in_grid, out_grid = _pairs(task)[0]
    assert (synthesize_pair_program(in_grid, out_grid)
            == synthesize_pair_program(in_grid, out_grid))
