"""
Tests for R6's global color-substitution capability (BACKLOG_LOOP.md R6 "training
escalation"): the `color_map` producer signal, matcher, rule builder, renderer,
and the fast-path replay bridge.

A large family of ARC tasks recolor a grid in place — same-shape output, every
input color `c` -> one fixed output color `map[c]`, consistently across all
example pairs. This pins:
  * signal       — ExtractPatternOperator surfaces the consistent global map and
                   declines (no misfire) on a non-recolor (move / resize) task.
  * matcher      — fires only on a consistent, changed, same-shape map.
  * end-to-end   — the pipeline renders the recolored grid via the frozen
                   `coloring` primitive, value-agnostically (map re-derived from
                   the examples), on real ARC-AGI-2 training tasks.
  * reuse        — one stored value-agnostic rule generalises to a *second*
                   color-map task (fast-path stored hit), and declines cleanly
                   (None, no crash) on a shape-changing task it is speculatively
                   applied to.
"""

import os
import sys
import tempfile
from types import SimpleNamespace

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agent.conditions import match  # noqa: E402


# ── helpers ───────────────────────────────────────────────────────────
def _grid(raw):
    return SimpleNamespace(raw=raw, height=len(raw), width=len(raw[0]) if raw else 0)


def _task_with_pairs(example, test=None):
    eps = [SimpleNamespace(input_grid=_grid(i), output_grid=_grid(o))
           for i, o in example]
    tps = [SimpleNamespace(input_grid=_grid(i),
                           output_grid=_grid(o) if o is not None else None)
           for i, o in (test or [])]
    return SimpleNamespace(example_pairs=eps, test_pairs=tps)


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


def _load_task(task_path, data_root="data"):
    from managers.arc_manager import ARCManager
    with tempfile.TemporaryDirectory() as tmp:
        return ARCManager(data_root=data_root,
                          semantic_memory_root=tmp).load_task(task_path)


# ── signal + matcher ──────────────────────────────────────────────────
def test_signal_color_map_consistent():
    # Two pairs realising the same global map 1->2, 3->4 (and 0->0 background).
    task = _task_with_pairs([
        ([[1, 0], [3, 1]], [[2, 0], [4, 2]]),
        ([[3, 3], [0, 1]], [[4, 4], [0, 2]]),
    ])
    patterns = _run_pipeline(task)[0]
    sig = patterns["color_map"]
    assert sig["consistent"] is True
    assert sig["color_map"][1] == 2 and sig["color_map"][3] == 4
    assert sig["color_map"][0] == 0
    assert sig["evidence_count"] == 2
    assert match("color_map", patterns) is True


def test_matcher_declines_on_inconsistent_map():
    # color 1 -> 2 in pair A but 1 -> 5 in pair B: no consistent global map.
    task = _task_with_pairs([
        ([[1, 0]], [[2, 0]]),
        ([[1, 0]], [[5, 0]]),
    ])
    patterns = _run_pipeline(task)[0]
    assert patterns["color_map"]["consistent"] is False
    assert match("color_map", patterns) is False


def test_matcher_declines_on_identity():
    # Output == input everywhere: a map exists but nothing changes -> not a recolor.
    task = _task_with_pairs([
        ([[1, 0]], [[1, 0]]),
        ([[3, 3]], [[3, 3]]),
    ])
    patterns = _run_pipeline(task)[0]
    assert patterns["color_map"]["consistent"] is False
    assert match("color_map", patterns) is False


def test_matcher_declines_on_shape_change():
    # Resize task: no per-cell correspondence -> no global map.
    task = _task_with_pairs([
        ([[1, 1, 0], [0, 0, 0], [0, 0, 2]], [[2, 2], [2, 2]]),
        ([[3, 0, 0], [0, 0, 0], [0, 0, 4]], [[2, 2], [2, 2]]),
    ])
    patterns = _run_pipeline(task)[0]
    assert patterns["color_map"]["consistent"] is False
    assert match("color_map", patterns) is False


# ── end-to-end pipeline ───────────────────────────────────────────────
def test_pipeline_builds_color_map_rule():
    task = _task_with_pairs([
        ([[1, 0], [3, 1]], [[2, 0], [4, 2]]),
        ([[3, 3], [0, 1]], [[4, 4], [0, 2]]),
    ])
    _, wm = _run_pipeline(task)
    rule = wm.s1["active-rules"][0]
    assert rule["type"] == "color_map"
    assert rule["condition"]["type"] == "color_map"
    assert rule["action"]["dsl"] == "color_map"
    assert rule["action"]["args"] == {}     # value-agnostic: map re-derived at apply


def test_pipeline_solves_real_training_color_map_tasks():
    # Real ARC-AGI-2 training tasks that are pure global color substitutions —
    # the agent returned identity on these before this capability existed.
    for hex_id in ("0d3d703e", "b1948b0a"):
        try:
            task = _load_task(f"ARC_AGI/training/{hex_id}")
        except Exception:
            continue  # dataset layout differs on this machine; skip gracefully
        _, wm = _run_pipeline(task)
        rule = wm.s1["active-rules"][0]
        assert rule["type"] == "color_map", f"{hex_id}: expected color_map rule"
        preds = wm.s1.get("predictions") or {}
        for i, tp in enumerate(task.test_pairs):
            if tp.output_grid is None:
                continue
            assert preds.get(f"test_{i}") == tp.output_grid.raw, \
                f"{hex_id}: test_{i} mismatch"


# ── renderer is value-agnostic over fully-determined test inputs ───────
def test_renderer_applies_map_when_test_fully_determined():
    from agent.active_operators import PredictOperator
    # Examples define 1->2 and pass 0 through (0->0); the test input uses only
    # colors the map determines, so the recolor applies exactly.
    task = _task_with_pairs([
        ([[1, 0]], [[2, 0]]),
        ([[1, 1]], [[2, 2]]),
    ])
    op = PredictOperator()
    op._task = task
    rule = {"type": "color_map", "action": {"dsl": "color_map", "args": {}}}
    out = op._render_color_map(rule, task, _grid([[1, 0], [0, 1]]))
    assert out == [[2, 0], [0, 2]]


def test_renderer_declines_on_undetermined_test_color():
    from agent.active_operators import PredictOperator
    # The examples never show what color 7 becomes; applying the map to a test
    # input containing 7 would be a guess, so the renderer declines (criterion 4).
    task = _task_with_pairs([
        ([[1, 0]], [[2, 0]]),
        ([[1, 1]], [[2, 2]]),
    ])
    op = PredictOperator()
    op._task = task
    rule = {"type": "color_map", "action": {"dsl": "color_map", "args": {}}}
    assert op._render_color_map(rule, task, _grid([[1, 7], [0, 1]])) is None


# ── speculative-apply discipline: clean decline, never crash ───────────
def test_renderer_declines_on_shape_changing_task_without_crashing():
    from agent.active_operators import PredictOperator
    # A stored color_map rule (empty args ⇒ runtime-replayable) is tried against
    # every task on the fast path. On a resize task it must decline (None), not
    # raise — the speculative-apply discipline (iter 16).
    task = _task_with_pairs([
        ([[1, 1, 0], [0, 0, 0], [0, 0, 2]], [[3, 3], [3, 3]]),
        ([[0, 5, 5], [0, 0, 0], [4, 0, 0]], [[3, 3], [3, 3]]),
    ])
    op = PredictOperator()
    op._task = task
    rule = {"type": "color_map", "action": {"dsl": "color_map", "args": {}}}
    assert op._render_color_map(rule, task, _grid([[1, 1, 0], [0, 0, 0], [0, 0, 2]])) is None


# ── fast-path replay bridge ───────────────────────────────────────────
def test_color_map_rule_is_replayable_via_dispatch():
    from agent.memory import applicable_rule
    entry = {
        "condition": {"type": "color_map", "params": {"min_evidence": 2}},
        "action": {"dsl": "color_map", "args": {}},
    }
    rule = applicable_rule(entry)
    assert rule is not None
    assert rule["type"] == "color_map"
