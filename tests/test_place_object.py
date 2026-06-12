"""
Tests for R1's *generation* step (BACKLOG_LOOP.md R1, §2.5-2b): the
`single_object_move_fixed_target` matcher and the `place_object` action it
gates, wired end-to-end through Generalize → Predict.

Layers:
  * registry    — the new matcher self-registers (P5).
  * unit        — the matcher fires only when the object lands on a *constant*
                  cell with the grid size preserved.
  * signal      — ExtractPatternOperator surfaces target_constant / target_cell
                  / outsize_preserved correctly across the real easy000c–i
                  family (fixed-target for c/d/h, declined for e/f/g/i).
  * end-to-end  — the pipeline renders the correct moved grid for c/d/h via the
                  two frozen primitives, value-agnostically, and produces *no*
                  place_object prediction for the relative/corner/resized members
                  (their target is the variable R3 must lift, not this rung).
"""

import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agent.conditions import CONDITION_REGISTRY, get_matcher, match  # noqa: E402


# ── registry ──────────────────────────────────────────────────────────
def test_fixed_target_matcher_is_registered():
    assert "single_object_move_fixed_target" in CONDITION_REGISTRY
    assert get_matcher("single_object_move_fixed_target") is not None


# ── unit: matcher logic on synthetic patterns ─────────────────────────
def _transition(**kw):
    base = {
        "all_single": True, "color_preserved": True, "shape_preserved": True,
        "moved": True, "target_constant": True, "target_cell": (5, 5),
        "outsize_preserved": True, "evidence_count": 2,
    }
    base.update(kw)
    return {"object_transition": base}


def test_fires_on_constant_cell_same_size():
    assert match("single_object_move_fixed_target", _transition()) is True


def test_rejects_when_target_not_constant():
    assert match("single_object_move_fixed_target",
                 _transition(target_constant=False, target_cell=None)) is False


def test_rejects_when_size_not_preserved():
    assert match("single_object_move_fixed_target",
                 _transition(outsize_preserved=False)) is False


def test_rejects_when_base_move_conditions_fail():
    assert match("single_object_move_fixed_target",
                 _transition(color_preserved=False)) is False
    assert match("single_object_move_fixed_target",
                 _transition(moved=False)) is False


def test_rejects_insufficient_evidence():
    assert match("single_object_move_fixed_target",
                 _transition(evidence_count=1), {"min_evidence": 2}) is False


# ── helpers: load a real task and run the mini-pipeline ────────────────
def _load_task(task_path, data_root="data"):
    from managers.arc_manager import ARCManager
    with tempfile.TemporaryDirectory() as tmp:
        return ARCManager(data_root=data_root,
                          semantic_memory_root=tmp).load_task(task_path)


def _run_pipeline(task):
    """Extract → Generalize → Predict on a fresh WM; return (patterns, wm)."""
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
def test_signal_fixed_target_on_cdh():
    # c/d/h: the object lands on the SAME cell across pairs, grid size kept.
    for name in ["c", "d", "h"]:
        patterns = _run_pipeline(_load_task(f"ARC_easy_a/easy000{name}"))[0]
        trans = patterns["object_transition"]
        assert trans["target_constant"] is True, name
        assert trans["target_cell"] is not None, name
        assert trans["outsize_preserved"] is True, name
        assert match("single_object_move_fixed_target", patterns) is True, name


def test_signal_declines_relative_and_resized():
    # e/f: relative displacement (target differs per pair) → not constant.
    # g:   relative corner (target differs with grid size) → not constant.
    # i:   grid is resized → size not preserved.
    for name in ["e", "f", "g"]:
        patterns = _run_pipeline(_load_task(f"ARC_easy_a/easy000{name}"))[0]
        assert patterns["object_transition"]["target_constant"] is False, name
        assert match("single_object_move_fixed_target", patterns) is False, name
    patterns = _run_pipeline(_load_task("ARC_easy_a/easy000i"))[0]
    assert patterns["object_transition"]["outsize_preserved"] is False
    assert match("single_object_move_fixed_target", patterns) is False


# ── end-to-end: pipeline renders the correct moved grid ───────────────
def test_pipeline_solves_cdh_correctly():
    for name in ["c", "d", "h"]:
        task = _load_task(f"ARC_easy_a/easy000{name}")
        _, wm = _run_pipeline(task)
        rule = wm.s1["active-rules"][0]
        assert rule["type"] == "place_object", name
        preds = wm.s1.get("predictions") or {}
        assert "test_0" in preds, name
        # The predicted grid must equal the task's known test output.
        expected = task.test_pairs[0].output_grid.raw
        assert preds["test_0"] == expected, name


def test_pipeline_does_not_place_for_unsupported_members():
    # g (relative corner) / i (resized): neither the fixed-target nor the
    # constant-displacement filling applies, so place_object is not emitted
    # (identity fallback) — their target is still the R3 variable, not a fresh
    # overfit literal. (e/f are now handled by the constant-displacement filling
    # — see test_place_object_displacement.py.)
    for name in ["g", "i"]:
        _, wm = _run_pipeline(_load_task(f"ARC_easy_a/easy000{name}"))
        rule = wm.s1["active-rules"][0]
        assert rule["type"] == "identity", name
