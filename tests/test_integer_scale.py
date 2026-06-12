"""
Tests for R6's integer block-upscale capability (BACKLOG_LOOP.md R6 "training
escalation"): the `integer_scale` producer signal, matcher, rule builder,
renderer, and the fast-path replay bridge.

A family of ARC tasks enlarges a grid by a constant integer factor — the output
is the input "zoomed in" by `(kh, kw)`, each input cell expanded into a `kh x kw`
block of its own colour, consistently across all example pairs. This pins:
  * signal       — ExtractPatternOperator surfaces the consistent factor and
                   declines (no misfire) on a same-shape or varying-factor task.
  * matcher      — fires only on a consistent, genuine (>1) block upscale.
  * end-to-end   — the pipeline renders the enlarged grid via the two frozen
                   primitives (`make_grid` ∘ `coloring`), value-agnostically (the
                   factor re-derived from the examples), on real ARC-AGI-2
                   training tasks.
  * reuse        — one stored value-agnostic rule generalises to a *second*
                   upscale task (fast-path stored hit), and declines cleanly
                   (None, no crash) on a same-shape task it is speculatively
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


def _upscale(raw, kh, kw):
    """Reference block-upscale used to build synthetic example outputs."""
    return [[raw[R // kh][C // kw]
             for C in range(len(raw[0]) * kw)]
            for R in range(len(raw) * kh)]


# ── signal + matcher ──────────────────────────────────────────────────
def test_signal_integer_scale_consistent():
    # Two pairs, both a pure 2x2 block upscale.
    a = [[1, 0], [0, 2]]
    b = [[3, 1], [4, 0]]
    task = _task_with_pairs([(a, _upscale(a, 2, 2)), (b, _upscale(b, 2, 2))])
    patterns = _run_pipeline(task)[0]
    sig = patterns["integer_scale"]
    assert sig["consistent"] is True
    assert sig["factor"] == (2, 2)
    assert sig["evidence_count"] == 2
    assert match("integer_scale", patterns) is True


def test_signal_supports_anisotropic_factor():
    # A genuine but non-square factor (kh != kw) is still a block upscale.
    a = [[1, 0], [0, 2]]
    b = [[3, 4], [0, 1]]
    task = _task_with_pairs([(a, _upscale(a, 1, 3)), (b, _upscale(b, 1, 3))])
    patterns = _run_pipeline(task)[0]
    assert patterns["integer_scale"]["factor"] == (1, 3)
    assert match("integer_scale", patterns) is True


def test_matcher_declines_on_same_shape():
    # Same shape in/out: factor would be (1,1), not an enlargement.
    task = _task_with_pairs([
        ([[1, 0]], [[2, 0]]),
        ([[3, 3]], [[4, 4]]),
    ])
    patterns = _run_pipeline(task)[0]
    assert patterns["integer_scale"]["consistent"] is False
    assert match("integer_scale", patterns) is False


def test_matcher_declines_on_varying_factor():
    # Pair A upscales 2x2, pair B upscales 3x3: no single constant factor.
    a = [[1, 0], [0, 2]]
    b = [[3, 1], [4, 0]]
    task = _task_with_pairs([(a, _upscale(a, 2, 2)), (b, _upscale(b, 3, 3))])
    patterns = _run_pipeline(task)[0]
    assert patterns["integer_scale"]["consistent"] is False
    assert match("integer_scale", patterns) is False


def test_matcher_declines_on_non_block_resize():
    # Output is larger by a divisible factor but is NOT a block upscale of the
    # input (the cells do not tile) — declines.
    task = _task_with_pairs([
        ([[1, 0], [0, 2]], [[1, 2, 0, 3], [4, 0, 5, 0], [0, 6, 0, 7], [8, 0, 9, 0]]),
        ([[3, 1], [4, 0]], [[1, 1, 1, 1], [2, 2, 2, 2], [3, 3, 3, 3], [4, 4, 4, 4]]),
    ])
    patterns = _run_pipeline(task)[0]
    assert patterns["integer_scale"]["consistent"] is False
    assert match("integer_scale", patterns) is False


# ── end-to-end pipeline ───────────────────────────────────────────────
def test_pipeline_builds_integer_scale_rule():
    a = [[1, 0], [0, 2]]
    b = [[3, 1], [4, 0]]
    task = _task_with_pairs([(a, _upscale(a, 2, 2)), (b, _upscale(b, 2, 2))])
    _, wm = _run_pipeline(task)
    rule = wm.s1["active-rules"][0]
    assert rule["type"] == "integer_scale"
    assert rule["condition"]["type"] == "integer_scale"
    assert rule["action"]["dsl"] == "integer_scale"
    assert rule["action"]["args"] == {}     # value-agnostic: factor re-derived at apply


def test_pipeline_solves_synthetic_upscale_with_fresh_colors():
    # The rule is re-derived per task: a test grid with colours unseen in the
    # examples still upscales correctly (factor, not literal cells, is what is
    # stored).
    a = [[1, 0], [0, 2]]
    b = [[3, 1], [4, 0]]
    test_in = [[7, 8], [9, 6]]
    task = _task_with_pairs(
        [(a, _upscale(a, 2, 2)), (b, _upscale(b, 2, 2))],
        test=[(test_in, _upscale(test_in, 2, 2))],
    )
    _, wm = _run_pipeline(task)
    preds = wm.s1.get("predictions") or {}
    assert preds.get("test_0") == _upscale(test_in, 2, 2)


def test_pipeline_solves_real_training_upscale_tasks():
    # Real ARC-AGI-2 training tasks that are pure integer block upscales — the
    # agent returned identity (size_match false) on these before this capability.
    solved = 0
    for hex_id in ("60c09cac", "9172f3a0", "c59eb873"):
        try:
            task = _load_task(f"ARC_AGI/training/{hex_id}")
        except Exception:
            continue  # dataset layout differs on this machine; skip gracefully
        _, wm = _run_pipeline(task)
        rule = wm.s1["active-rules"][0]
        assert rule["type"] == "integer_scale", f"{hex_id}: expected integer_scale rule"
        preds = wm.s1.get("predictions") or {}
        for i, tp in enumerate(task.test_pairs):
            if tp.output_grid is None:
                continue
            assert preds.get(f"test_{i}") == tp.output_grid.raw, \
                f"{hex_id}: test_{i} mismatch"
        solved += 1
    # If the dataset is present at all, at least one task must have solved.
    if os.path.isdir("data/ARC_AGI/training"):
        assert solved >= 1


# ── renderer is value-agnostic, composes the two frozen primitives ─────
def test_renderer_upscales_via_make_grid_and_coloring():
    from agent.active_operators import PredictOperator
    a = [[1, 0], [0, 2]]
    b = [[3, 1], [4, 0]]
    task = _task_with_pairs([(a, _upscale(a, 2, 2)), (b, _upscale(b, 2, 2))])
    op = PredictOperator()
    op._task = task
    rule = {"type": "integer_scale", "action": {"dsl": "integer_scale", "args": {}}}
    test_in = [[5, 0], [0, 6]]
    assert op._render_integer_scale(rule, task, _grid(test_in)) == _upscale(test_in, 2, 2)


# ── speculative-apply discipline: clean decline, never crash ───────────
def test_renderer_declines_on_same_shape_task_without_crashing():
    from agent.active_operators import PredictOperator
    # A stored integer_scale rule (empty args ⇒ runtime-replayable) is tried
    # against every task on the fast path. On a same-shape (non-scale) task it
    # must decline (None), not raise — the speculative-apply discipline (iter 16).
    task = _task_with_pairs([
        ([[1, 0]], [[2, 0]]),
        ([[3, 3]], [[4, 4]]),
    ])
    op = PredictOperator()
    op._task = task
    rule = {"type": "integer_scale", "action": {"dsl": "integer_scale", "args": {}}}
    assert op._render_integer_scale(rule, task, _grid([[1, 0]])) is None


# ── fast-path replay bridge ───────────────────────────────────────────
def test_integer_scale_rule_is_replayable_via_dispatch():
    from agent.memory import applicable_rule
    entry = {
        "condition": {"type": "integer_scale", "params": {"min_evidence": 2}},
        "action": {"dsl": "integer_scale", "args": {}},
    }
    rule = applicable_rule(entry)
    assert rule is not None
    assert rule["type"] == "integer_scale"
