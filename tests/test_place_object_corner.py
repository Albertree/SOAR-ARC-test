"""
Tests for R1's *relative-corner* filling (BACKLOG_LOOP.md R1, §2.5-2b): the
`single_object_move_relative_corner` matcher and the "corner" branch of the
`place_object` action, wired end-to-end through Generalize → Predict.

This is the **third** filling of `place_object`'s target hole — the object lands
on the same grid *corner* across every pair, resolving to a *different cell* in
each differently-sized grid (easy000g: bottom-right, 4×4 / 3×5 / 6×4). It shares
the exact `place_object` skeleton of the fixed-target and displacement fillings;
only the target *function* differs (carried in `action.args.target_mode`). All
three fillings are disjoint on the supplied data, which is what makes them the
clean R3 anti-unification input — and why `save_rule`'s subsumption folds this
filling into the existing `?v1` abstraction's covers rather than minting a rule.

Layers:
  * registry    — the new matcher self-registers (P5).
  * vocab       — `corners_at` / `corner_cell` round-trip over grid bounds.
  * unit        — the matcher fires only on a constant corner with size
                  preserved, and is disjoint from the other two fillings.
  * signal      — ExtractPatternOperator surfaces corner_constant / corner
                  correctly across the real easy000c–i family.
  * end-to-end  — the pipeline renders the correct moved grid for g via the two
                  frozen primitives, value-agnostically.
  * subsumption — a corner filling is folded into the lifted place_object
                  abstraction's covers, spawning no new rule (§2.5-4).
"""

import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agent.conditions import CONDITION_REGISTRY, get_matcher, match  # noqa: E402
from agent.dsl_expr import corners_at, corner_cell  # noqa: E402


# ── registry ──────────────────────────────────────────────────────────
def test_corner_matcher_is_registered():
    assert "single_object_move_relative_corner" in CONDITION_REGISTRY
    assert get_matcher("single_object_move_relative_corner") is not None


# ── vocab: corners_at / corner_cell ───────────────────────────────────
def test_corners_at_identifies_each_corner():
    assert corners_at((0, 0), 4, 5) == {"tl"}
    assert corners_at((0, 4), 4, 5) == {"tr"}
    assert corners_at((3, 0), 4, 5) == {"bl"}
    assert corners_at((3, 4), 4, 5) == {"br"}
    assert corners_at((1, 2), 4, 5) == set()           # interior cell, no corner


def test_corner_cell_inverts_corners_at():
    for cid in ("tl", "tr", "bl", "br"):
        for (h, w) in ((4, 4), (3, 5), (6, 4)):
            cell = corner_cell(cid, h, w)
            assert cid in corners_at(cell, h, w)
    assert corner_cell("nope", 4, 4) is None


# ── unit: matcher logic on synthetic patterns ─────────────────────────
def _transition(**kw):
    base = {
        "all_single": True, "color_preserved": True, "shape_preserved": True,
        "moved": True, "target_constant": False, "target_cell": None,
        "displacement_constant": False, "displacement": None,
        "corner_constant": True, "corner": "br",
        "outsize_preserved": True, "evidence_count": 2,
    }
    base.update(kw)
    return {"object_transition": base}


def test_fires_on_constant_corner_same_size():
    assert match("single_object_move_relative_corner", _transition()) is True


def test_rejects_when_corner_not_constant():
    assert match("single_object_move_relative_corner",
                 _transition(corner_constant=False, corner=None)) is False


def test_rejects_when_size_not_preserved():
    assert match("single_object_move_relative_corner",
                 _transition(outsize_preserved=False)) is False


def test_rejects_when_base_move_conditions_fail():
    assert match("single_object_move_relative_corner",
                 _transition(color_preserved=False)) is False
    assert match("single_object_move_relative_corner",
                 _transition(moved=False)) is False


def test_rejects_insufficient_evidence():
    assert match("single_object_move_relative_corner",
                 _transition(evidence_count=1), {"min_evidence": 2}) is False


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
def test_signal_constant_corner_on_g():
    # g: object lands on bottom-right corner across all pairs; grids differ in
    # size, so the landing *cell* varies (fixed-target declines) and the offset
    # varies (displacement declines) — only the corner is invariant.
    patterns = _run_pipeline(_load_task("ARC_easy_a/easy000g"))[0]
    trans = patterns["object_transition"]
    assert trans["corner_constant"] is True
    assert trans["corner"] == "br"
    assert trans["target_constant"] is False
    assert trans["displacement_constant"] is False
    assert match("single_object_move_relative_corner", patterns) is True
    assert match("single_object_move_fixed_target", patterns) is False
    assert match("single_object_move_constant_displacement", patterns) is False


def test_signal_declines_non_corner_movers():
    # d (lands interior, (1,2)) and h (interior (4,4)) and e/f (constant Δ,
    # interior) are not corner movers.
    for name in ["d", "e", "f", "h"]:
        patterns = _run_pipeline(_load_task(f"ARC_easy_a/easy000{name}"))[0]
        assert match("single_object_move_relative_corner", patterns) is False, name
    # i lands on a corner (top-left) but resizes the grid → declined here
    # (outsize not preserved); i belongs to a later, grid-resize capability.
    patterns = _run_pipeline(_load_task("ARC_easy_a/easy000i"))[0]
    assert patterns["object_transition"]["outsize_preserved"] is False
    assert match("single_object_move_relative_corner", patterns) is False


def test_same_size_corner_overlap_routes_to_fixed():
    # easy000c is all 6×6 and lands on (5,5) — that is BOTH the constant cell
    # (fixed-target, since the grids are the same size) AND the bottom-right
    # corner. The two fillings overlap here; the overlap is harmless because
    # GeneralizeOperator checks fixed-target *first*, so c routes to the fixed
    # rule (target_mode absent). Only g — where the grids differ in size so the
    # cell varies and fixed-target declines — reaches the corner branch.
    patterns, wm = _run_pipeline(_load_task("ARC_easy_a/easy000c"))
    assert match("single_object_move_fixed_target", patterns) is True
    assert match("single_object_move_relative_corner", patterns) is True
    rule = wm.s1["active-rules"][0]
    assert rule["type"] == "place_object"
    assert rule["action"]["args"].get("target_mode") in (None, "fixed")


# ── end-to-end: pipeline renders the correct moved grid ───────────────
def test_pipeline_solves_g_correctly():
    task = _load_task("ARC_easy_a/easy000g")
    _, wm = _run_pipeline(task)
    rule = wm.s1["active-rules"][0]
    assert rule["type"] == "place_object"
    assert rule["action"]["args"].get("target_mode") == "corner"
    preds = wm.s1.get("predictions") or {}
    assert "test_0" in preds
    expected = task.test_pairs[0].output_grid.raw
    assert preds["test_0"] == expected


# ── subsumption: corner filling folds into the place_object abstraction ─
def test_corner_filling_subsumed_by_abstraction():
    import json
    from agent.memory import save_rule

    abstraction = {
        "id": 1,
        "concept": "place_moved_object",
        "category": "single_object_move",
        "condition": {"type": "single_object_move", "params": {"min_evidence": 2}},
        "action": {"dsl": "place_object", "args": {"target_mode": "?v1"}},
        "covers": ["easy000c", "easy000e"],
        "source_task": "easy000e",
        "anti_unification_trace":
            "episodic_memory/easy000e/anti_unification/au_001.json",
        "created_at": "2026-06-12T00:00:00",
        "times_reused": 0,
    }
    corner_rule = {
        "concept": "place_cornered_object",
        "category": "single_object_move",
        "condition": {"type": "single_object_move", "params": {"min_evidence": 2}},
        "action": {"dsl": "place_object", "args": {"target_mode": "corner"}},
    }
    with tempfile.TemporaryDirectory() as root:
        with open(os.path.join(root, "rule_001.json"), "w", encoding="utf-8") as fh:
            json.dump(abstraction, fh)
        path = save_rule(corner_rule, "easy000g", procedural_memory_root=root)
        # Folded into the existing abstraction — no second rule file spawned.
        files = [f for f in os.listdir(root) if f.endswith(".json")]
        assert files == ["rule_001.json"]
        with open(path, encoding="utf-8") as fh:
            stored = json.load(fh)
        assert "easy000g" in stored["covers"]
        assert stored["action"]["args"]["target_mode"] == "?v1"   # still abstract
