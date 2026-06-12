"""
Tests for R6's fractal self-tile capability (BACKLOG_LOOP.md R6 "training
escalation"): the `self_tile` producer signal, matcher, rule builder, renderer,
and the fast-path replay bridge.

A family of ARC tasks expands a `H x W` grid into a `H*H x W*W` grid by self
reference: the output is `H x W` macro-blocks of size `H x W`, and block `(r, c)`
is a copy of the whole input where `input[r][c]` is live, or the empty colour
where it is off, consistently across all example pairs. This pins:
  * signal       — ExtractPatternOperator surfaces the consistent empty colour and
                   declines (no misfire) on a non-self-tile / inconsistent task.
  * matcher      — fires only on a consistent masked self-tile.
  * disjointness — declines on a constant-factor *solid* upscale (that is the
                   `integer_scale` family, not a self-tile).
  * end-to-end   — the pipeline renders the tiled grid via the two frozen
                   primitives (`make_grid` ∘ `coloring`), value-agnostically (the
                   empty colour re-derived from the examples), on real ARC-AGI-2
                   training tasks (007bbfb7, 5b6cbef5).
  * reuse        — one stored value-agnostic rule generalises across the family
                   (fast-path stored hit), and declines cleanly (None, no crash)
                   on a same-shape task it is speculatively applied to.
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


def _self_tile(raw, empty):
    """Reference fractal self-tile used to build synthetic example outputs: block
    (r, c) is a copy of the input where input[r][c] != empty, else all-empty."""
    H, W = len(raw), len(raw[0])
    out = [[empty] * (W * W) for _ in range(H * H)]
    for r in range(H):
        for c in range(W):
            if raw[r][c] == empty:
                continue
            for a in range(H):
                for b in range(W):
                    out[r * H + a][c * W + b] = raw[a][b]
    return out


def _solid_upscale(raw, kh, kw):
    """Reference *solid* block upscale (the integer_scale family) — used as a
    negative: a self-tile matcher must decline on it."""
    return [[raw[R // kh][C // kw]
             for C in range(len(raw[0]) * kw)]
            for R in range(len(raw) * kh)]


# ── signal + matcher ──────────────────────────────────────────────────
def test_signal_self_tile_consistent():
    # Two pairs, both a masked self-tile with empty colour 0.
    a = [[0, 1], [1, 0]]
    b = [[2, 0], [2, 2]]
    task = _task_with_pairs([(a, _self_tile(a, 0)), (b, _self_tile(b, 0))])
    patterns = _run_pipeline(task)[0]
    sig = patterns["self_tile"]
    assert sig["consistent"] is True
    assert sig["empty"] == 0
    assert sig["evidence_count"] == 2
    assert match("self_tile", patterns) is True


def test_signal_derives_nonzero_empty_colour():
    # The empty colour is derived, not assumed to be 0: here the mask's off-value
    # is 5, consistently across both pairs.
    a = [[5, 3], [3, 5]]
    b = [[4, 4], [5, 4]]
    task = _task_with_pairs([(a, _self_tile(a, 5)), (b, _self_tile(b, 5))])
    patterns = _run_pipeline(task)[0]
    assert patterns["self_tile"]["empty"] == 5
    assert match("self_tile", patterns) is True


def test_matcher_declines_on_inconsistent_empty():
    # Pair A masks on 0, pair B masks on 9: no single COMM empty colour.
    a = [[0, 1], [1, 0]]
    b = [[9, 2], [2, 9]]
    task = _task_with_pairs([(a, _self_tile(a, 0)), (b, _self_tile(b, 9))])
    patterns = _run_pipeline(task)[0]
    assert patterns["self_tile"]["consistent"] is False
    assert match("self_tile", patterns) is False


def test_matcher_declines_on_same_shape():
    # Same-shape recolor: not an H*H × W*W self-tile.
    task = _task_with_pairs([
        ([[1, 0]], [[2, 0]]),
        ([[3, 3]], [[4, 4]]),
    ])
    patterns = _run_pipeline(task)[0]
    assert patterns["self_tile"]["consistent"] is False
    assert match("self_tile", patterns) is False


def test_matcher_declines_on_solid_upscale():
    # A constant-factor *solid* block upscale is the integer_scale family, not a
    # self-tile (its blocks are solids, not copies of the input). The self_tile
    # matcher must decline so the two families stay disjoint.
    a = [[1, 2], [3, 4]]
    b = [[5, 6], [7, 8]]
    task = _task_with_pairs([(a, _solid_upscale(a, 2, 2)), (b, _solid_upscale(b, 2, 2))])
    patterns = _run_pipeline(task)[0]
    assert patterns["self_tile"]["consistent"] is False
    assert match("self_tile", patterns) is False
    # ...and integer_scale claims it instead.
    assert match("integer_scale", patterns) is True


# ── end-to-end pipeline ───────────────────────────────────────────────
def test_pipeline_builds_self_tile_rule():
    a = [[0, 1], [1, 0]]
    b = [[2, 0], [2, 2]]
    task = _task_with_pairs([(a, _self_tile(a, 0)), (b, _self_tile(b, 0))])
    _, wm = _run_pipeline(task)
    rule = wm.s1["active-rules"][0]
    assert rule["type"] == "self_tile"
    assert rule["condition"]["type"] == "self_tile"
    assert rule["action"]["dsl"] == "self_tile"
    assert rule["action"]["args"] == {}     # value-agnostic: empty re-derived at apply


def test_pipeline_solves_synthetic_self_tile_with_fresh_colors():
    # The rule is re-derived per task: a test grid with colours unseen in the
    # examples still tiles correctly (the empty colour, not literal cells, is what
    # the rule carries).
    a = [[0, 1], [1, 0]]
    b = [[2, 0], [2, 2]]
    test_in = [[0, 7], [8, 0]]
    task = _task_with_pairs(
        [(a, _self_tile(a, 0)), (b, _self_tile(b, 0))],
        test=[(test_in, _self_tile(test_in, 0))],
    )
    _, wm = _run_pipeline(task)
    preds = wm.s1.get("predictions") or {}
    assert preds.get("test_0") == _self_tile(test_in, 0)


def test_pipeline_solves_real_training_self_tile_tasks():
    # Real ARC-AGI-2 training tasks that are fractal self-tiles — the agent
    # returned identity on these before this capability.
    solved = 0
    for hex_id in ("007bbfb7", "5b6cbef5"):
        try:
            task = _load_task(f"ARC_AGI/training/{hex_id}")
        except Exception:
            continue  # dataset layout differs on this machine; skip gracefully
        _, wm = _run_pipeline(task)
        rule = wm.s1["active-rules"][0]
        assert rule["type"] == "self_tile", f"{hex_id}: expected self_tile rule"
        preds = wm.s1.get("predictions") or {}
        for i, tp in enumerate(task.test_pairs):
            if tp.output_grid is None:
                continue
            assert preds.get(f"test_{i}") == tp.output_grid.raw, \
                f"{hex_id}: test_{i} mismatch"
        solved += 1
    if os.path.isdir("data/ARC_AGI/training"):
        assert solved >= 1


# ── renderer is value-agnostic, composes the two frozen primitives ─────
def test_renderer_tiles_via_make_grid_and_coloring():
    from agent.active_operators import PredictOperator
    a = [[0, 1], [1, 0]]
    b = [[2, 0], [2, 2]]
    task = _task_with_pairs([(a, _self_tile(a, 0)), (b, _self_tile(b, 0))])
    op = PredictOperator()
    op._task = task
    rule = {"type": "self_tile", "action": {"dsl": "self_tile", "args": {}}}
    test_in = [[0, 5], [6, 0]]
    assert op._render_self_tile(rule, task, _grid(test_in)) == _self_tile(test_in, 0)


# ── speculative-apply discipline: clean decline, never crash ───────────
def test_renderer_declines_on_same_shape_task_without_crashing():
    from agent.active_operators import PredictOperator
    # A stored self_tile rule (empty args ⇒ runtime-replayable) is tried against
    # every task on the fast path. On a same-shape (non-self-tile) task it must
    # decline (None), not raise — the speculative-apply discipline (iter 16).
    task = _task_with_pairs([
        ([[1, 0]], [[2, 0]]),
        ([[3, 3]], [[4, 4]]),
    ])
    op = PredictOperator()
    op._task = task
    rule = {"type": "self_tile", "action": {"dsl": "self_tile", "args": {}}}
    assert op._render_self_tile(rule, task, _grid([[1, 0]])) is None


# ── fast-path replay bridge ───────────────────────────────────────────
def test_self_tile_rule_is_replayable_via_dispatch():
    from agent.memory import applicable_rule
    entry = {
        "condition": {"type": "self_tile", "params": {"min_evidence": 2}},
        "action": {"dsl": "self_tile", "args": {}},
    }
    rule = applicable_rule(entry)
    assert rule is not None
    assert rule["type"] == "self_tile"
