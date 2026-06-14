"""
Tests for the synthesizer's property-keyed enclosed-region fill schema (Schema 17,
program/synthesis.py).

This is the size-keyed generalisation of Schema 16 (``enclosed_fill``): each
interior background pocket is repainted in the colour a value-agnostic
``size → colour`` map assigns to it (its cell-count), for the ARC family where
pockets of *different* sizes take *different* fill colours — which the
single-colour ``enclosed_fill`` cannot express. It is to ``enclosed_fill`` what
``recolor_objects`` is to a flat recolour. The map is the whole per-task content
carried in ONE const leaf, so two size-keyed-fill tasks with divergent maps share
the SAME one-step skeleton ``[("enclosed_fill_by", ("const", ?v))]`` and lift via
unify() into one covers>1 rule (R3), never a rule per task (BACKLOG_LOOP §2.5-3/4).
"""

import pytest

from program.synthesis import (
    run_program, synthesize_task, _fit_enclosed_fill_by, _fit_enclosed_fill,
    _pocket_components, _Unevaluable,
)
from agent.memory import _program_skeleton


# --- the pocket partition: one component per separate interior hole ------------

def test_pocket_components_splits_separate_holes():
    # Two 1-cell holes sealed by the same colour-3 wall, separated by a wall column.
    grid = [
        [3, 3, 3, 3, 3],
        [3, 0, 3, 0, 3],
        [3, 3, 3, 3, 3],
    ]
    comps = _pocket_components(grid, 0)
    assert sorted(len(c) for c in comps) == [1, 1]
    assert {tuple(c[0]) for c in comps} == {(1, 1), (1, 3)}


# --- fit a size -> colour map (different sizes, different colours) -------------

def test_fit_size_keyed_fill():
    # One pair with a 1-cell pocket (-> colour 6) and a 2x2 4-cell pocket (-> 7).
    pairs = [
        {"input":  [[3, 3, 3, 0, 3, 3, 3, 3],
                    [3, 0, 3, 0, 3, 0, 0, 3],
                    [3, 3, 3, 0, 3, 0, 0, 3],
                    [0, 0, 0, 0, 3, 3, 3, 3]],
         "output": [[3, 3, 3, 0, 3, 3, 3, 3],
                    [3, 6, 3, 0, 3, 7, 7, 3],
                    [3, 3, 3, 0, 3, 7, 7, 3],
                    [0, 0, 0, 0, 3, 3, 3, 3]]},
    ]
    prog = _fit_enclosed_fill_by(pairs)
    assert prog is not None
    assert prog[0][0] == "enclosed_fill_by"
    spec = prog[0][1][1]
    assert spec["prop"] == "size"
    assert dict(spec["map"]) == {1: 6, 4: 7}
    for p in pairs:
        assert run_program(prog, p["input"]) == p["output"]


# --- a SINGLE fill colour is owned by enclosed_fill, not this schema ----------

def test_single_colour_declines_so_const_owns_it():
    # Both pockets become colour 4 -> only one distinct fill colour, so the
    # property-keyed fitter declines (the simpler enclosed_fill owns it).
    pairs = [
        {"input":  [[3, 3, 3, 3, 3, 3, 3],
                    [3, 0, 3, 3, 0, 0, 3],
                    [3, 3, 3, 3, 0, 0, 3],
                    [3, 3, 3, 3, 3, 3, 3]],
         "output": [[3, 3, 3, 3, 3, 3, 3],
                    [3, 4, 3, 3, 4, 4, 3],
                    [3, 3, 3, 3, 4, 4, 3],
                    [3, 3, 3, 3, 3, 3, 3]]},
    ]
    assert _fit_enclosed_fill_by(pairs) is None
    assert _fit_enclosed_fill(pairs) is not None


# --- a non-deterministic map (same size -> two colours) declines --------------

def test_inconsistent_size_map_declines():
    pairs = [
        {"input":  [[3, 3, 3, 3, 3, 3, 3],
                    [3, 0, 3, 3, 0, 3, 3],
                    [3, 3, 3, 3, 3, 3, 3]],
         "output": [[3, 3, 3, 3, 3, 3, 3],
                    [3, 5, 3, 3, 7, 3, 3],
                    [3, 3, 3, 3, 3, 3, 3]]},
    ]
    # Both pockets have size 1 but map to 5 and 7 -> not a function -> declines.
    assert _fit_enclosed_fill_by(pairs) is None


# --- two divergent maps share ONE skeleton (lift into covers>1) ---------------

def test_two_maps_share_skeleton():
    task_a = [
        {"input":  [[3, 3, 3, 0, 3, 3, 3, 3],
                    [3, 0, 3, 0, 3, 0, 0, 3],
                    [3, 3, 3, 0, 3, 0, 0, 3],
                    [0, 0, 0, 0, 3, 3, 3, 3]],
         "output": [[3, 3, 3, 0, 3, 3, 3, 3],
                    [3, 6, 3, 0, 3, 7, 7, 3],
                    [3, 3, 3, 0, 3, 7, 7, 3],
                    [0, 0, 0, 0, 3, 3, 3, 3]]},
    ]
    task_b = [
        {"input":  [[2, 2, 2, 0, 2, 2, 2, 2],
                    [2, 0, 2, 0, 2, 0, 0, 2],
                    [2, 2, 2, 0, 2, 0, 0, 2],
                    [0, 0, 0, 0, 2, 2, 2, 2]],
         "output": [[2, 2, 2, 0, 2, 2, 2, 2],
                    [2, 1, 2, 0, 2, 8, 8, 2],
                    [2, 2, 2, 0, 2, 8, 8, 2],
                    [0, 0, 0, 0, 2, 2, 2, 2]]},
    ]
    a = _fit_enclosed_fill_by(task_a)
    b = _fit_enclosed_fill_by(task_b)
    assert a is not None and b is not None
    assert a[0][1][1] != b[0][1][1]                 # different fitted maps
    assert _program_skeleton(a) == _program_skeleton(b)   # same skeleton -> lifts


# --- an unseen pocket size makes the program DECLINE, never guess -------------

def test_unseen_size_declines_not_crash():
    pairs = [
        {"input":  [[3, 3, 3], [3, 0, 3], [3, 3, 3]],
         "output": [[3, 3, 3], [3, 6, 3], [3, 3, 3]]},
        {"input":  [[3, 3, 3, 3], [3, 0, 0, 3], [3, 3, 3, 3]],
         "output": [[3, 3, 3, 3], [3, 7, 7, 3], [3, 3, 3, 3]]},
    ]
    prog = _fit_enclosed_fill_by(pairs)
    assert prog is not None
    # A grid with a 3x1 (size-3) pocket — a size never seen in train.
    unseen = [[3, 3, 3, 3, 3], [3, 0, 0, 0, 3], [3, 3, 3, 3, 3]]
    with pytest.raises(_Unevaluable):
        run_program(prog, unseen)


# --- reachable through the full search; const enclosed_fill kept simpler ------

# A 6x9 grid with two sealed boxes: a 1-cell hole (left) and a 2x2 hole (right).
_TWO_BOX_IN = [
    [0, 0, 0, 0, 0, 0, 0, 0, 0],
    [0, 3, 3, 3, 0, 3, 3, 3, 3],
    [0, 3, 0, 3, 0, 3, 0, 0, 3],
    [0, 3, 3, 3, 0, 3, 0, 0, 3],
    [0, 0, 0, 0, 0, 3, 3, 3, 3],
    [0, 0, 0, 0, 0, 0, 0, 0, 0],
]


def _filled(small, big):
    """``_TWO_BOX_IN`` with the size-1 hole painted ``small`` and the 2x2 hole ``big``."""
    g = [row[:] for row in _TWO_BOX_IN]
    g[2][2] = small
    for r in (2, 3):
        for c in (6, 7):
            g[r][c] = big
    return g


def test_synthesize_prefers_const_for_single_colour():
    # Two pairs (so a const reconstruction cannot overfit), both filling every
    # pocket with the SAME colour 4 -> the simpler const enclosed_fill must own it.
    pairs = [
        {"input": _TWO_BOX_IN, "output": _filled(4, 4)},
        {"input":  [[3, 3, 3], [3, 0, 3], [3, 3, 3]],
         "output": [[3, 3, 3], [3, 4, 3], [3, 3, 3]]},
    ]
    prog = synthesize_task(pairs)
    assert prog is not None
    assert prog[0][0] == "enclosed_fill"   # single colour -> const schema wins


def test_synthesize_finds_size_keyed_fill():
    # Two pairs with the same size->colour map {1:6, 4:7}; a const reconstruction
    # cannot reproduce both, so the size-keyed schema is the one that fits.
    pairs = [
        {"input": _TWO_BOX_IN, "output": _filled(6, 7)},
        {"input":  [[3, 3, 3, 3], [3, 0, 0, 3], [3, 0, 0, 3], [3, 3, 3, 3]],
         "output": [[3, 3, 3, 3], [3, 7, 7, 3], [3, 7, 7, 3], [3, 3, 3, 3]]},
    ]
    prog = synthesize_task(pairs)
    assert prog is not None
    assert prog[0][0] == "enclosed_fill_by"
