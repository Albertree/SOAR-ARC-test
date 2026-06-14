"""
Tests for the synthesizer's symmetry / occlusion-repair schema (Schema 18,
program/synthesis.py).

The input is a symmetric picture (mirror / rotation / periodic tiling) with one
solid block of a single *mask* colour hiding part of it; the output restores each
hidden cell from its symmetric counterpart on the still-visible support. The whole
symmetry spec (mask colour + the valid dihedral ops / axis periods) is carried in
ONE const leaf, so two symmetry-repair tasks with divergent masks/symmetries share
the SAME one-step skeleton ``[("symmetry_repair", ("const", ?v))]`` and lift via
unify() into one covers>1 rule (R3), never a rule per symmetry (BACKLOG_LOOP
§2.5-3/4). The fill paints only the frozen ``coloring`` primitive (F3-safe) and
*declines* — never guesses — on a masked cell with no unmasked symmetric source.
"""

import pytest

from program.synthesis import (
    run_program, synthesize_task, _fit_symmetry_repair, _symmetry_partners,
    _Unevaluable,
)
from agent.memory import _program_skeleton


# --- fit a horizontal-mirror occlusion repair ---------------------------------

def test_fit_mirror_repair():
    # 2x4 grid, symmetric left<->right; a single colour-5 block hides one cell,
    # restored from its mirror partner.
    pairs = [
        {"input":  [[1, 2, 2, 1],
                    [3, 5, 4, 3]],
         "output": [[1, 2, 2, 1],
                    [3, 4, 4, 3]]},
    ]
    prog = _fit_symmetry_repair(pairs)
    assert prog is not None
    assert prog[0][0] == "symmetry_repair"
    spec = prog[0][1][1]
    assert spec["mask"] == 5
    assert "hmir" in spec["dih"]
    assert run_program(prog, pairs[0]["input"]) == pairs[0]["output"]


# --- fit a periodic (translational) occlusion repair --------------------------

def test_fit_periodic_repair():
    # Horizontally period-2 picture; a colour-5 cell is restored from the period.
    pairs = [
        {"input":  [[1, 2, 1, 2, 1, 2],
                    [3, 4, 3, 5, 3, 4],
                    [1, 2, 1, 2, 1, 2]],
         "output": [[1, 2, 1, 2, 1, 2],
                    [3, 4, 3, 4, 3, 4],
                    [1, 2, 1, 2, 1, 2]]},
    ]
    prog = _fit_symmetry_repair(pairs)
    assert prog is not None
    spec = prog[0][1][1]
    assert spec["mask"] == 5
    assert spec["ph"] == 2
    assert run_program(prog, pairs[0]["input"]) == pairs[0]["output"]


# --- a multi-colour change is not a clean occlusion -> declines ---------------

def test_multi_colour_change_declines():
    # Two changed cells of *different* input colours -> no single mask colour.
    pairs = [
        {"input":  [[1, 2, 2, 1],
                    [5, 3, 3, 6]],
         "output": [[1, 2, 2, 1],
                    [3, 3, 3, 3]]},
    ]
    assert _fit_symmetry_repair(pairs) is None


# --- two divergent specs share ONE skeleton (lift into covers>1) --------------

def test_two_specs_share_skeleton():
    task_a = [
        {"input":  [[1, 2, 2, 1],
                    [3, 5, 4, 3]],
         "output": [[1, 2, 2, 1],
                    [3, 4, 4, 3]]},
    ]
    task_b = [  # vertical mirror, different mask colour
        {"input":  [[1, 3],
                    [2, 4],
                    [2, 7],
                    [1, 3]],
         "output": [[1, 3],
                    [2, 4],
                    [2, 4],
                    [1, 3]]},
    ]
    a = _fit_symmetry_repair(task_a)
    b = _fit_symmetry_repair(task_b)
    assert a is not None and b is not None
    assert a[0][1][1] != b[0][1][1]                       # different fitted specs
    assert _program_skeleton(a) == _program_skeleton(b)   # same skeleton -> lifts


# --- a masked cell with no unmasked source DECLINES, never guesses ------------

def test_no_unmasked_source_declines_not_crash():
    pairs = [
        {"input":  [[1, 2, 2, 1],
                    [3, 5, 4, 3]],
         "output": [[1, 2, 2, 1],
                    [3, 4, 4, 3]]},
    ]
    prog = _fit_symmetry_repair(pairs)
    assert prog is not None
    # Both mirror-paired cells masked -> neither has an unmasked source.
    unseen = [[5, 2, 2, 5]]
    with pytest.raises(_Unevaluable):
        run_program(prog, unseen)


# --- the partner helper enumerates in-bounds dihedral + periodic counterparts -

def test_symmetry_partners_in_bounds():
    spec = {"mask": 5, "dih": ["hmir"], "pv": None, "ph": 2}
    parts = _symmetry_partners(1, 3, 3, 6, spec)
    assert (1, 2) in parts            # hmir of (1,3) on a width-6 grid
    assert (1, 1) in parts            # one period (-2) left
    assert (1, 5) in parts            # one period (+2) right
    assert all(0 <= r < 3 and 0 <= c < 6 for (r, c) in parts)


# --- reachable through the full search; a clean symmetric grid stays identity -

def test_synthesize_finds_symmetry_repair():
    # Two pairs sharing a mask colour but DIFFERENT hidden content, so a cell-wise
    # colour map cannot reproduce both (5 -> 4 vs 5 -> 9) -> symmetry_repair fits.
    pairs = [
        {"input":  [[1, 2, 2, 1],
                    [3, 5, 4, 3]],
         "output": [[1, 2, 2, 1],
                    [3, 4, 4, 3]]},
        {"input":  [[7, 8, 8, 7],
                    [6, 5, 9, 6]],
         "output": [[7, 8, 8, 7],
                    [6, 9, 9, 6]]},
    ]
    prog = synthesize_task(pairs)
    assert prog is not None
    assert prog[0][0] == "symmetry_repair"
    for p in pairs:
        assert run_program(prog, p["input"]) == p["output"]


def test_unoccluded_symmetric_grid_owned_by_identity():
    # No change at all -> the symmetry-repair fitter has no mask and declines; the
    # simpler identity schema owns it (symmetry_repair must not hijack it).
    pairs = [
        {"input":  [[1, 2, 2, 1], [3, 4, 4, 3]],
         "output": [[1, 2, 2, 1], [3, 4, 4, 3]]},
    ]
    assert _fit_symmetry_repair(pairs) is None
    prog = synthesize_task(pairs)
    assert prog is not None
    # identity is the empty program; in any case symmetry_repair must not own it
    assert prog == [] or prog[0][0] != "symmetry_repair"
