"""
Tests for the canonical recolor family (R1 / arbor-dsl-taxonomy).

ARBOR recognised same-size 1:1 recolors only through the legacy condition-less
``_try_color_mapping`` detector, which emitted a literal ``{type: color_mapping,
mapping: {...}}`` rule. That is the arbor.md 진단 #4 failure mode (a
dropped-condition rule) and an anti-unification dead-end: a literal map shares no
liftable skeleton with another recolor. This migration replaces the producer with
the canonical path — an ``analyze_color_remap`` reading, a registered
``color_remap`` condition matcher, and a ``coloring``-composition renderer — so the
recolor family is now condition-bearing, value-agnostic in geometry, and expressed
in the two frozen primitives (BACKLOG_LOOP §2.5-1). The legacy *applier*
(``_apply_color_mapping``) is kept for backward-compat with any stored legacy rule;
only the producer is migrated.

These tests pin: the reading detects a consistent map and abstains on a
non-function / a resize; the matcher honours ``min_evidence``; the renderer paints
via ``coloring`` without chaining; the GeneralizeOperator emits a schema-canonical
``{condition, action}`` rule (not a ``{type: ...}`` envelope); and an end-to-end
solve renders the correct test grid through the pipeline.
"""

from types import SimpleNamespace

from ARCKG.grid import Grid
from ARCKG.pair import Pair
from ARCKG.task import Task

from agent.active_operators import (
    ExtractPatternOperator,
    GeneralizeOperator,
    PredictOperator,
    RECOLOR_DSL,
)
from agent.conditions import match as match_condition
from agent.dsl_expr.render import render_recolor
from agent.dsl_expr.selection import analyze_color_remap


# ── helpers ───────────────────────────────────────────────────────────────
def _pair(idx, gin, gout):
    return Pair(
        f"P{idx}",
        Grid(f"P{idx}G0", gin),
        Grid(f"P{idx}G1", gout) if gout is not None else None,
    )


def _recolor_task():
    """A clean same-size 1:1 recolor (3->4, 2->8) over varying geometry, several
    disconnected cells (not a single-object move) so geometry is not the
    invariant — the colour map is."""
    train = [
        ([[0, 3, 0],
          [0, 3, 2],
          [2, 0, 3]],
         [[0, 4, 0],
          [0, 4, 8],
          [8, 0, 4]]),
        ([[3, 0, 0, 2],
          [0, 2, 0, 3]],
         [[4, 0, 0, 8],
          [0, 8, 0, 4]]),
        ([[0, 0, 3],
          [2, 0, 0],
          [3, 2, 0],
          [0, 0, 2]],
         [[0, 0, 4],
          [8, 0, 0],
          [4, 8, 0],
          [0, 0, 8]]),
    ]
    test_in = [[3, 0, 2],
               [0, 0, 0],
               [2, 3, 0]]
    test_out = [[4, 0, 8],
                [0, 0, 0],
                [8, 4, 0]]
    examples = [_pair(i, a, b) for i, (a, b) in enumerate(train)]
    tests = [_pair(99, test_in, test_out)]
    return Task("recolor_demo", examples, tests), test_out


# ── analyze_color_remap ─────────────────────────────────────────────────────
def test_analyze_detects_consistent_map():
    task, _ = _recolor_task()
    sig = analyze_color_remap(task.example_pairs)
    assert sig["consistent"] is True
    assert sig["color_map"] == {3: 4, 2: 8}
    assert sig["evidence"] >= 2


def test_analyze_abstains_on_non_function():
    # color 3 maps to 4 in pair0 but to 5 in pair1 -> not a function -> None.
    pairs = [
        _pair(0, [[3, 0]], [[4, 0]]),
        _pair(1, [[3, 0]], [[5, 0]]),
    ]
    sig = analyze_color_remap(pairs)
    assert sig["color_map"] is None
    assert sig["consistent"] is False


def test_analyze_abstains_on_resize():
    # A grid-size change is not a recolor — the reading must decline.
    pairs = [_pair(0, [[3, 3]], [[4, 4], [4, 4]])]
    sig = analyze_color_remap(pairs)
    assert sig["color_map"] is None


def test_analyze_abstains_on_identity():
    # Nothing changes -> identity is not a recolor.
    pairs = [_pair(0, [[3, 0]], [[3, 0]]), _pair(1, [[0, 2]], [[0, 2]])]
    sig = analyze_color_remap(pairs)
    assert sig["color_map"] is None


# ── matcher ────────────────────────────────────────────────────────────────
def test_matcher_fires_with_evidence():
    task, _ = _recolor_task()
    patterns = {"color_remap": analyze_color_remap(task.example_pairs)}
    assert match_condition("color_remap", patterns, {"min_evidence": 2}) is True


def test_matcher_respects_min_evidence():
    # A single changing pair cannot establish a constant family map.
    pairs = [_pair(0, [[3, 0]], [[4, 0]])]
    patterns = {"color_remap": analyze_color_remap(pairs)}
    assert match_condition("color_remap", patterns, {"min_evidence": 2}) is False


# ── renderer: coloring composition, no chaining ─────────────────────────────
def test_render_recolor_does_not_chain():
    # {1:2, 2:3} must not turn the original 1s into 3s.
    grid = [[1, 2], [2, 1]]
    out = render_recolor(grid, {1: 2, 2: 3})
    assert out == [[2, 3], [3, 2]]


# ── GeneralizeOperator emits a canonical {condition, action} rule ───────────
def test_generalize_emits_canonical_recolor_rule():
    task, _ = _recolor_task()
    wm = SimpleNamespace(task=task, s1={})
    ExtractPatternOperator().effect(wm)
    GeneralizeOperator().effect(wm)

    rule = wm.s1["active-rules"][0]
    # Canonical schema, NOT a legacy {type: color_mapping} envelope.
    assert "type" not in rule
    assert rule["condition"]["type"] == "color_remap"
    assert rule["action"]["dsl"] == RECOLOR_DSL
    assert rule["category"] == "color_remap"
    # The map is carried with JSON-safe string keys for AU / inspection.
    assert rule["action"]["args"]["color_map"] == {"3": 4, "2": 8}


# ── end-to-end: the pipeline renders the correct test grid ──────────────────
def test_predict_renders_correct_test_grid():
    task, expected = _recolor_task()
    wm = SimpleNamespace(task=task, s1={})
    ExtractPatternOperator().effect(wm)
    GeneralizeOperator().effect(wm)
    PredictOperator().effect(wm)

    assert wm.s1["predictions"]["test_0"] == expected
