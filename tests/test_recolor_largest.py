"""
Tests for R4's *application* wiring (BACKLOG_LOOP.md R4 "2nd-order / ranking
relation"): the `object_ranking` producer, the `recolor_largest` rule builder,
and its renderer, wired end-to-end through Extract → Generalize → Predict.

Iter 13 added the substrate (`argmax`/`cells_of`, the dormant
`recolor_largest_object` matcher); this pins the half that *acts* on it. Mirrors
tests/test_place_object.py:
  * signal      — ExtractPatternOperator surfaces multi_object / select_extreme /
                  recolor_constant / recolor_color / others_unchanged correctly,
                  and declines on the single-object easy path (no misfire).
  * end-to-end  — the pipeline renders the correct recolored grid via the frozen
                  `coloring` primitive, value-agnostically (color re-derived from
                  the examples), for two tasks of *different* color/grid.
"""

import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agent.conditions import match  # noqa: E402


# ── helpers: load a real task and run the mini-pipeline ────────────────
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
def test_signal_object_ranking_on_largest_recolor():
    patterns = _run_pipeline(_load_task("ARC_madeup/largest_recolor"))[0]
    rank = patterns["object_ranking"]
    assert rank["multi_object"] is True
    assert rank["select_extreme"] is True
    assert rank["recolor_constant"] is True
    assert rank["recolor_color"] == 4
    assert rank["others_unchanged"] is True
    assert rank["evidence_count"] == 3
    assert match("recolor_largest_object", patterns) is True


def test_signal_object_ranking_on_variant_color_grid():
    # A different color (2->8) and grid: the *same* value-agnostic signal holds,
    # so one rule covers both (recolor_color is re-derived, never stored).
    patterns = _run_pipeline(_load_task("ARC_madeup/largest_recolor_b"))[0]
    rank = patterns["object_ranking"]
    assert rank["multi_object"] is True
    assert rank["recolor_constant"] is True
    assert rank["recolor_color"] == 8
    assert match("recolor_largest_object", patterns) is True


def test_signal_declines_on_single_object_easy_task():
    # easy000c is a single-object move: multi_object is False, so the ranking
    # matcher stays dormant and cannot misfire on the easy/easy_a path.
    patterns = _run_pipeline(_load_task("ARC_easy_a/easy000c"))[0]
    rank = patterns["object_ranking"]
    assert rank["multi_object"] is False
    assert rank["select_extreme"] is False
    assert match("recolor_largest_object", patterns) is False


# ── end-to-end: pipeline renders the correct recolored grid ───────────
def test_pipeline_solves_largest_recolor():
    for name in ["largest_recolor", "largest_recolor_b"]:
        task = _load_task(f"ARC_madeup/{name}")
        _, wm = _run_pipeline(task)
        rule = wm.s1["active-rules"][0]
        assert rule["type"] == "recolor_largest", name
        # The action is value-agnostic: no stored color/cells in args.
        assert (rule.get("action") or {}).get("args") == {}, name
        preds = wm.s1.get("predictions") or {}
        assert "test_0" in preds, name
        expected = task.test_pairs[0].output_grid.raw
        assert preds["test_0"] == expected, name


def test_renderer_recolors_only_the_largest_object():
    # The output must equal the input except the size-maximal object's cells,
    # which take the derived color — every other cell is preserved (the recolor
    # is `coloring(input, cells_of(argmax(...)), color)`, no fresh canvas).
    task = _load_task("ARC_madeup/largest_recolor")
    _, wm = _run_pipeline(task)
    pred = wm.s1["predictions"]["test_0"]
    test_in = task.test_pairs[0].input_grid.raw
    changed = [
        (r, c)
        for r in range(len(test_in)) for c in range(len(test_in[0]))
        if test_in[r][c] != pred[r][c]
    ]
    # Exactly the 6 cells of the 2x3 largest object changed, all to color 4.
    assert len(changed) == 6
    assert all(pred[r][c] == 4 for r, c in changed)
    assert all(test_in[r][c] != 0 for r, c in changed)
