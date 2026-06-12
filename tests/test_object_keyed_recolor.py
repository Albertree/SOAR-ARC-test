"""
Tests for R4's object-keyed recolor capability (BACKLOG_LOOP.md R4 "2nd-order /
ranking relation", §2.5-2b): the `object_keyed_recolor` producer signal, matcher,
rule builder, renderer, and the fast-path replay bridge.

A family of ARC tasks holds a *body* object and a smaller *marker* object, and
recolors the body to **the marker's color** before erasing the marker. The fill
color is therefore a *relation read* (`color-of(marker)`) that varies per task —
the capability the constant-fill `recolor_extreme` and the positional `color_map`
families cannot express. This pins:
  * signal       — ExtractPatternOperator surfaces the relation and declines (no
                   misfire) on a single-object / constant-recolor task.
  * matcher      — fires only when every pair exhibits body←color-of(marker) +
                   marker-erased.
  * end-to-end   — the pipeline renders the recolor via the frozen `coloring`
                   primitive, value-agnostically (objects+color re-derived from the
                   examples), on the real ARC-AGI-2 training task aabf363d.
  * disjointness — recolor_extreme / color_map stay dormant on an object-keyed task
                   (constant-fill / positional-map readings do not apply).
  * reuse        — one stored value-agnostic rule is replayable, and the renderer
                   declines cleanly (None, no crash) on a non-matching task it is
                   speculatively applied to.
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


# A body object (color 2/3) and a single marker pixel (color 4/6); output
# recolors the body to the marker's color and erases the marker. The fill color
# differs across pairs (4 then 6) — a relation read, not a constant.
_BODY_A_IN = [[0, 0, 0, 0],
              [0, 2, 2, 0],
              [0, 2, 0, 0],
              [4, 0, 0, 0]]
_BODY_A_OUT = [[0, 0, 0, 0],
               [0, 4, 4, 0],
               [0, 4, 0, 0],
               [0, 0, 0, 0]]
_BODY_B_IN = [[0, 0, 0, 0],
              [0, 3, 3, 0],
              [0, 3, 0, 0],
              [6, 0, 0, 0]]
_BODY_B_OUT = [[0, 0, 0, 0],
               [0, 6, 6, 0],
               [0, 6, 0, 0],
               [0, 0, 0, 0]]


# ── signal + matcher ──────────────────────────────────────────────────
def test_signal_object_keyed_recolor_consistent():
    task = _task_with_pairs([(_BODY_A_IN, _BODY_A_OUT), (_BODY_B_IN, _BODY_B_OUT)])
    patterns = _run_pipeline(task)[0]
    sig = patterns["object_keyed_recolor"]
    assert sig["consistent"] is True
    assert sig["evidence_count"] == 2
    assert match("object_keyed_recolor", patterns) is True


def test_matcher_declines_on_constant_fill_recolor():
    # Body recolored to a *constant* color (5) that is NOT the marker's color, and
    # the marker is left untouched: this is a recolor_extreme-shaped task, not an
    # object-keyed one — the object_keyed matcher must stay dormant.
    in_a = [[2, 2, 0], [2, 0, 0], [4, 0, 0]]
    out_a = [[5, 5, 0], [5, 0, 0], [4, 0, 0]]
    in_b = [[3, 3, 3], [3, 0, 0], [6, 0, 0]]
    out_b = [[5, 5, 5], [5, 0, 0], [6, 0, 0]]
    task = _task_with_pairs([(in_a, out_a), (in_b, out_b)])
    patterns = _run_pipeline(task)[0]
    assert patterns["object_keyed_recolor"]["consistent"] is False
    assert match("object_keyed_recolor", patterns) is False


def test_matcher_declines_on_single_object_task():
    # One object only: the two-object selection abstains, so no object-keyed recolor.
    task = _task_with_pairs([
        ([[2, 2], [2, 0]], [[2, 2], [2, 0]]),
        ([[3, 0], [3, 3]], [[3, 0], [3, 3]]),
    ])
    patterns = _run_pipeline(task)[0]
    assert patterns["object_keyed_recolor"]["consistent"] is False
    assert match("object_keyed_recolor", patterns) is False


# ── end-to-end pipeline ───────────────────────────────────────────────
def test_pipeline_builds_object_keyed_recolor_rule():
    task = _task_with_pairs([(_BODY_A_IN, _BODY_A_OUT), (_BODY_B_IN, _BODY_B_OUT)])
    _, wm = _run_pipeline(task)
    rule = wm.s1["active-rules"][0]
    assert rule["type"] == "object_keyed_recolor"
    assert rule["condition"]["type"] == "object_keyed_recolor"
    assert rule["action"]["dsl"] == "object_keyed_recolor"
    assert rule["action"]["args"] == {}     # value-agnostic: relation re-derived at apply


def test_pipeline_solves_synthetic_object_keyed_task():
    # Test grid: a new body color (8) and a new marker color (7) — both differ from
    # the training colors, proving objects + color are re-derived, never stored.
    test_in = [[0, 0, 0, 0],
               [0, 8, 8, 0],
               [0, 8, 8, 0],
               [7, 0, 0, 0]]
    test_out = [[0, 0, 0, 0],
                [0, 7, 7, 0],
                [0, 7, 7, 0],
                [0, 0, 0, 0]]
    task = _task_with_pairs([(_BODY_A_IN, _BODY_A_OUT), (_BODY_B_IN, _BODY_B_OUT)],
                            test=[(test_in, test_out)])
    _, wm = _run_pipeline(task)
    rule = wm.s1["active-rules"][0]
    assert rule["type"] == "object_keyed_recolor"
    assert (wm.s1.get("predictions") or {}).get("test_0") == test_out


def test_pipeline_solves_real_training_aabf363d():
    # Real ARC-AGI-2 training task: recolor the shape to the bottom-left marker's
    # color, erase the marker. The agent returned identity before this capability.
    try:
        task = _load_task("ARC_AGI/training/aabf363d")
    except Exception:
        return  # dataset layout differs on this machine; skip gracefully
    _, wm = _run_pipeline(task)
    rule = wm.s1["active-rules"][0]
    assert rule["type"] == "object_keyed_recolor", "expected object_keyed_recolor rule"
    preds = wm.s1.get("predictions") or {}
    for i, tp in enumerate(task.test_pairs):
        if tp.output_grid is None:
            continue
        assert preds.get(f"test_{i}") == tp.output_grid.raw, f"test_{i} mismatch"


# ── speculative-apply discipline: clean decline, never crash ───────────
def test_renderer_declines_on_non_matching_task_without_crashing():
    from agent.active_operators import PredictOperator
    # A stored object_keyed_recolor rule (empty args ⇒ runtime-replayable) is tried
    # against every task on the fast path. On a task whose examples do not exhibit
    # the body←marker relation it must decline (None), not raise.
    task = _task_with_pairs([
        ([[1, 0], [3, 1]], [[2, 0], [4, 2]]),     # a positional recolor, no marker
        ([[3, 3], [0, 1]], [[4, 4], [0, 2]]),
    ])
    op = PredictOperator()
    op._task = task
    rule = {"type": "object_keyed_recolor",
            "action": {"dsl": "object_keyed_recolor", "args": {}}}
    assert op._render_object_keyed_recolor(rule, task, _grid([[1, 0], [3, 1]])) is None


def test_renderer_declines_on_ambiguous_test_grid():
    from agent.active_operators import PredictOperator
    # Examples are valid object-keyed, but the test grid has three objects (no
    # unambiguous body/marker pair) — the selection abstains, render returns None.
    task = _task_with_pairs([(_BODY_A_IN, _BODY_A_OUT), (_BODY_B_IN, _BODY_B_OUT)])
    op = PredictOperator()
    op._task = task
    rule = {"type": "object_keyed_recolor",
            "action": {"dsl": "object_keyed_recolor", "args": {}}}
    three_objs = [[8, 0, 5], [0, 0, 0], [0, 7, 0]]
    assert op._render_object_keyed_recolor(rule, task, _grid(three_objs)) is None


# ── fast-path replay bridge ───────────────────────────────────────────
def test_object_keyed_recolor_rule_is_replayable_via_dispatch():
    from agent.memory import applicable_rule
    entry = {
        "condition": {"type": "object_keyed_recolor", "params": {"min_evidence": 2}},
        "action": {"dsl": "object_keyed_recolor", "args": {}},
    }
    rule = applicable_rule(entry)
    assert rule is not None
    assert rule["type"] == "object_keyed_recolor"
