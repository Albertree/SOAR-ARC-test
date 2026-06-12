"""
Tests for R1's *constant-displacement* filling (BACKLOG_LOOP.md R1, §2.5-2b):
the `single_object_move_constant_displacement` matcher and the displacement
branch of the `place_object` action, wired end-to-end through Generalize →
Predict.

This is the **second** filling of `place_object`'s target hole — the object
moves by one constant Δ across every pair (easy000e/f), landing on *different*
cells. It shares the exact `place_object` skeleton of the fixed-target filling
(test_place_object.py); only the target *function* differs (carried in
`action.args.target_mode`). The two fillings are disjoint on the supplied data,
which is what makes them the clean R3 anti-unification input.

Layers:
  * registry    — the new matcher self-registers (P5).
  * unit        — the matcher fires only on a *constant* Δ with size preserved,
                  and is disjoint from the fixed-target matcher.
  * signal      — ExtractPatternOperator surfaces displacement_constant /
                  displacement correctly across the real easy000c–i family.
  * end-to-end  — the pipeline renders the correct moved grid for e/f via the
                  two frozen primitives, value-agnostically.
"""

import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agent.conditions import CONDITION_REGISTRY, get_matcher, match  # noqa: E402


# ── registry ──────────────────────────────────────────────────────────
def test_displacement_matcher_is_registered():
    assert "single_object_move_constant_displacement" in CONDITION_REGISTRY
    assert get_matcher("single_object_move_constant_displacement") is not None


# ── unit: matcher logic on synthetic patterns ─────────────────────────
def _transition(**kw):
    base = {
        "all_single": True, "color_preserved": True, "shape_preserved": True,
        "moved": True, "target_constant": False, "target_cell": None,
        "displacement_constant": True, "displacement": (1, -1),
        "outsize_preserved": True, "evidence_count": 2,
    }
    base.update(kw)
    return {"object_transition": base}


def test_fires_on_constant_displacement_same_size():
    assert match("single_object_move_constant_displacement", _transition()) is True


def test_rejects_when_displacement_not_constant():
    assert match("single_object_move_constant_displacement",
                 _transition(displacement_constant=False, displacement=None)) is False


def test_rejects_when_size_not_preserved():
    assert match("single_object_move_constant_displacement",
                 _transition(outsize_preserved=False)) is False


def test_rejects_when_base_move_conditions_fail():
    assert match("single_object_move_constant_displacement",
                 _transition(color_preserved=False)) is False
    assert match("single_object_move_constant_displacement",
                 _transition(moved=False)) is False


def test_rejects_insufficient_evidence():
    assert match("single_object_move_constant_displacement",
                 _transition(evidence_count=1), {"min_evidence": 2}) is False


def test_fillings_are_disjoint():
    # A constant landing cell (fixed-target) implies a varying Δ, and vice-versa.
    fixed = {"object_transition": {
        "all_single": True, "color_preserved": True, "shape_preserved": True,
        "moved": True, "target_constant": True, "target_cell": (5, 5),
        "displacement_constant": False, "displacement": None,
        "outsize_preserved": True, "evidence_count": 2,
    }}
    assert match("single_object_move_fixed_target", fixed) is True
    assert match("single_object_move_constant_displacement", fixed) is False
    # And the displacement default-pattern is declined by the fixed matcher.
    assert match("single_object_move_fixed_target", _transition()) is False
    assert match("single_object_move_constant_displacement", _transition()) is True


# ── helpers ───────────────────────────────────────────────────────────
def _load_task(task_path, data_root="data"):
    from managers.arc_manager import ARCManager
    with tempfile.TemporaryDirectory() as tmp:
        return ARCManager(data_root=data_root,
                          semantic_memory_root=tmp).load_task(task_path)


def _run_pipeline(task):
    from agent.wm import WorkingMemory
    from agent.active_operators import (
        ExtractPatternOperator, GeneralizeOperator, PredictOperator,
    )
    wm = WorkingMemory()
    wm.task = task
    ExtractPatternOperator().effect(wm)
    GeneralizeOperator().effect(wm)
    PredictOperator().effect(wm)
    return wm.s1["patterns"], wm


# ── signal: real ExtractPatternOperator output ────────────────────────
def test_signal_constant_displacement_on_ef():
    # e: Δ=(1,-1); f: Δ=(0,1) — constant across pairs, size preserved, but the
    # landing cell differs (so the fixed-target matcher declines them).
    for name in ["e", "f"]:
        patterns = _run_pipeline(_load_task(f"ARC_easy_a/easy000{name}"))[0]
        trans = patterns["object_transition"]
        assert trans["displacement_constant"] is True, name
        assert trans["displacement"] is not None, name
        assert trans["target_constant"] is False, name
        assert match("single_object_move_constant_displacement", patterns) is True, name
        assert match("single_object_move_fixed_target", patterns) is False, name


def test_signal_declines_fixed_and_resized():
    # c/d/h: constant landing cell → Δ varies → displacement matcher declines.
    for name in ["c", "d", "h"]:
        patterns = _run_pipeline(_load_task(f"ARC_easy_a/easy000{name}"))[0]
        assert patterns["object_transition"]["displacement_constant"] is False, name
        assert match("single_object_move_constant_displacement", patterns) is False, name
    # g: relative corner — Δ varies with grid size. i: resized.
    for name in ["g", "i"]:
        patterns = _run_pipeline(_load_task(f"ARC_easy_a/easy000{name}"))[0]
        assert match("single_object_move_constant_displacement", patterns) is False, name


# ── end-to-end: pipeline renders the correct moved grid ───────────────
def test_pipeline_solves_ef_correctly():
    for name in ["e", "f"]:
        task = _load_task(f"ARC_easy_a/easy000{name}")
        _, wm = _run_pipeline(task)
        rule = wm.s1["active-rules"][0]
        assert rule["type"] == "place_object", name
        assert rule["action"]["args"].get("target_mode") == "displacement", name
        preds = wm.s1.get("predictions") or {}
        assert "test_0" in preds, name
        expected = task.test_pairs[0].output_grid.raw
        assert preds["test_0"] == expected, name
