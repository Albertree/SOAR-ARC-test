"""
Tests for program-line anti-unification
(`program/anti_unification.py:anti_unify_pair_programs`, BACKLOG_LOOP.md
R3/§2.5-3, modules F/G).

This is the *consumer* for the per-pair programs that
`agent/program_synthesis.py` synthesizes (iter-26 → iter-27). The two halves
compose into the §6.2-intended Slow path: synthesize an overfit literal program
per example pair, then lift 2+ of them that share a skeleton into one abstract
`covers>1` program whose differing positions are `?vN` variables — the
alternative to minting a tenth hand-built in-code family.

The ground is a *real* lift: the two easy000c train pairs (a single coloured
pixel relocated to the fixed corner (5,5)) synthesize to programs that share a
skeleton; anti-unifying them must preserve the invariant corner target and lift
exactly the source cell and the colour.
"""

import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agent.program_synthesis import synthesize_pair_program  # noqa: E402
from program.anti_unification import (  # noqa: E402
    anti_unify_pair_programs, program_is_more_general, NoCommonSkeleton,
)


# ── helpers ───────────────────────────────────────────────────────────
def _load_task(task_path, data_root="data"):
    from managers.arc_manager import ARCManager
    with tempfile.TemporaryDirectory() as tmp:
        return ARCManager(data_root=data_root,
                          semantic_memory_root=tmp).load_task(task_path)


def _pairs(task):
    return [(p.input_grid.raw, p.output_grid.raw) for p in task.example_pairs]


# ── the ground: a real lift on easy000c ───────────────────────────────
def test_easy000c_pairs_lift_to_one_abstract_program():
    # easy000c: a single coloured pixel moves to the fixed corner (5,5). Each
    # train pair synthesizes to a 2-step DIFF program — erase the source cell to
    # background, paint (5,5) the colour. Anti-unifying the two pairs must keep
    # the invariant corner target [[5,5]] literal and lift the *source* cell (and
    # the colour, which differs across pairs) to ?vN.
    task = _load_task("ARC_easy_a/easy000c")
    programs = [synthesize_pair_program(i, o) for i, o in _pairs(task)]
    abstract = anti_unify_pair_programs(programs)

    # skeleton preserved: same shape, all coloring steps
    assert len(abstract) == len(programs[0])
    assert all(step["dsl"] == "coloring" for step in abstract)
    # it genuinely generalized (covers > 1 worth of pairs)
    assert program_is_more_general(abstract)

    # the fixed corner target survives as a literal somewhere; the moving source
    # selection is lifted to a variable.
    selections = [step["args"]["selection"] for step in abstract]
    assert [[5, 5]] in selections                    # invariant corner kept literal
    assert any(isinstance(s, str) and s.startswith("?v")
               for s in selections)                  # source cell lifted


# ── controlled precision cases ────────────────────────────────────────
def test_lifts_only_the_differing_position():
    # Two from-scratch programs identical but for the make_grid background colour:
    # only that colour lifts; height/width/everything else passes through.
    prog_a = [{"dsl": "make_grid", "args": {"height": 2, "width": 2, "color": 0}},
              {"dsl": "coloring", "args": {"selection": [[1, 1]], "color": 3}}]
    prog_b = [{"dsl": "make_grid", "args": {"height": 2, "width": 2, "color": 5}},
              {"dsl": "coloring", "args": {"selection": [[1, 1]], "color": 3}}]
    abstract = anti_unify_pair_programs([prog_a, prog_b])

    assert abstract[0]["dsl"] == "make_grid"
    assert abstract[0]["args"]["height"] == 2        # COMM — literal
    assert abstract[0]["args"]["width"] == 2         # COMM — literal
    assert str(abstract[0]["args"]["color"]).startswith("?v")   # DIFF — lifted
    assert abstract[1]["args"]["selection"] == [[1, 1]]         # COMM — literal
    assert abstract[1]["args"]["color"] == 3                    # COMM — literal
    assert program_is_more_general(abstract)


def test_identical_programs_lift_nothing():
    prog = [{"dsl": "coloring", "args": {"selection": [[0, 0]], "color": 4}}]
    abstract = anti_unify_pair_programs([prog, prog])
    assert abstract == prog
    assert not program_is_more_general(abstract)


def test_differing_step_count_raises():
    short = [{"dsl": "coloring", "args": {"selection": [[0, 0]], "color": 1}}]
    long = short + [{"dsl": "coloring", "args": {"selection": [[1, 1]], "color": 2}}]
    try:
        anti_unify_pair_programs([short, long])
        assert False, "expected NoCommonSkeleton"
    except NoCommonSkeleton:
        pass


def test_dsl_mismatch_at_a_step_raises():
    prog_a = [{"dsl": "make_grid", "args": {"height": 2, "width": 2, "color": 0}}]
    prog_b = [{"dsl": "coloring", "args": {"selection": [[0, 0]], "color": 0}}]
    try:
        anti_unify_pair_programs([prog_a, prog_b])
        assert False, "expected NoCommonSkeleton"
    except NoCommonSkeleton:
        pass


def test_fewer_than_two_programs_raises():
    prog = [{"dsl": "coloring", "args": {"selection": [[0, 0]], "color": 1}}]
    try:
        anti_unify_pair_programs([prog])
        assert False, "expected NoCommonSkeleton"
    except NoCommonSkeleton:
        pass


def test_three_programs_share_one_variable_per_position():
    # Three pairs, same skeleton, the painted colour differs across all three:
    # the colour lifts to a single ?vN, the (constant) selection stays literal.
    progs = [[{"dsl": "coloring", "args": {"selection": [[2, 2]], "color": c}}]
             for c in (1, 2, 3)]
    abstract = anti_unify_pair_programs(progs)
    assert abstract[0]["args"]["selection"] == [[2, 2]]
    assert str(abstract[0]["args"]["color"]).startswith("?v")
    assert program_is_more_general(abstract)
