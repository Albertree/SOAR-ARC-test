"""
Tests for the canonical rank-based recolor family (R1 / §2.5-2b ranking selector).

ARBOR recognised rank-based sequential recolors (changed groups painted a
contiguous colour run ordered by position) only through the legacy condition-less
``_try_recolor_sequential`` detector, which emitted a literal ``{type:
recolor_sequential, ...}`` rule. That is the arbor.md 진단 #4 failure mode (a
dropped-condition rule) and an anti-unification dead-end: a literal envelope shares
no liftable skeleton with another recolor. This migration replaces the producer
with the canonical path — an ``analyze_recolor_rank`` reading, a registered
``recolor_rank`` condition matcher, and a ``coloring``-composition renderer
(``render_recolor_rank``) — so the family is now condition-bearing, value-agnostic
in the absolute colours/positions, and expressed in the two frozen primitives
(BACKLOG_LOOP §2.5-1). The learned argument is a ``rank-by(position)`` selector,
the first ordinal selector in the vocabulary (R4-adjacent). The legacy *applier*
(``_apply_recolor_sequential``) is kept for backward-compat; only the producer is
migrated, mirroring iter20's color_remap work.

These tests pin: the reading detects a consistent ordering key and abstains on a
non-sequential run / a multi-colour group / a resize; the matcher honours
``min_evidence``; the renderer paints via ``coloring`` and leaves non-source cells
untouched; the GeneralizeOperator emits a schema-canonical ``{condition, action}``
rule (not a ``{type: ...}`` envelope); and an end-to-end solve renders the correct
test grid through the pipeline.
"""

from types import SimpleNamespace

from ARCKG.grid import Grid
from ARCKG.pair import Pair
from ARCKG.task import Task

from agent.active_operators import (
    ExtractPatternOperator,
    GeneralizeOperator,
    PredictOperator,
    RECOLOR_RANK_DSL,
)
from agent.conditions import match as match_condition
from agent.dsl_expr.render import render_recolor_rank
from agent.dsl_expr.selection import analyze_recolor_rank


# ── helpers ───────────────────────────────────────────────────────────────
def _pair(idx, gin, gout):
    return Pair(
        f"P{idx}",
        Grid(f"P{idx}G0", gin),
        Grid(f"P{idx}G1", gout) if gout is not None else None,
    )


def _rank_task():
    """A clean rank-by-top_row recolor: source colour 5 in 3 disconnected cells per
    grid, repainted 1,2,3 in row order over varying geometry. top_col is *not*
    consistent across pairs, so the learned key is uniquely top_row."""
    train = [
        ([[5, 0, 0, 0, 0],
          [0, 0, 0, 0, 0],
          [0, 0, 5, 0, 0],
          [0, 0, 0, 0, 0],
          [0, 0, 0, 0, 5]],
         [[1, 0, 0, 0, 0],
          [0, 0, 0, 0, 0],
          [0, 0, 2, 0, 0],
          [0, 0, 0, 0, 0],
          [0, 0, 0, 0, 3]]),
        ([[0, 0, 0, 0, 5],
          [0, 0, 0, 0, 0],
          [5, 0, 0, 0, 0],
          [0, 0, 0, 5, 0],
          [0, 0, 0, 0, 0]],
         [[0, 0, 0, 0, 1],
          [0, 0, 0, 0, 0],
          [2, 0, 0, 0, 0],
          [0, 0, 0, 3, 0],
          [0, 0, 0, 0, 0]]),
    ]
    test_in = [[0, 0, 0, 0, 0],
               [0, 5, 0, 0, 0],
               [0, 0, 0, 0, 0],
               [5, 0, 0, 0, 0],
               [0, 0, 0, 0, 5]]
    test_out = [[0, 0, 0, 0, 0],
                [0, 1, 0, 0, 0],
                [0, 0, 0, 0, 0],
                [2, 0, 0, 0, 0],
                [0, 0, 0, 0, 3]]
    examples = [_pair(i, a, b) for i, (a, b) in enumerate(train)]
    tests = [_pair(99, test_in, test_out)]
    return Task("rank_demo", examples, tests), test_out


# ── analyze_recolor_rank ────────────────────────────────────────────────────
def test_analyze_detects_consistent_rank():
    task, _ = _rank_task()
    sig = analyze_recolor_rank(task.example_pairs)
    assert sig["sort_key"] == "top_row"
    assert sig["start_color"] == 1
    assert sig["source_colors"] == [5]
    assert sig["consistent"] is True
    assert sig["evidence"] >= 2


def test_analyze_abstains_on_non_sequential():
    # output colours 1 and 3 are not a contiguous run -> no rank reading.
    pairs = [
        _pair(0, [[5, 0, 5]], [[1, 0, 3]]),
        _pair(1, [[5, 0, 5]], [[1, 0, 3]]),
    ]
    sig = analyze_recolor_rank(pairs)
    assert sig["sort_key"] is None


def test_analyze_abstains_on_multicolor_group():
    # one connected group spanning two source colours is not single-coloured.
    pairs = [
        _pair(0, [[5, 6]], [[1, 2]]),
        _pair(1, [[5, 6]], [[1, 2]]),
    ]
    sig = analyze_recolor_rank(pairs)
    # the two cells are 4-adjacent -> one group with two input colours -> abstain.
    assert sig["sort_key"] is None


def test_analyze_abstains_on_resize():
    pairs = [_pair(0, [[5, 5]], [[1, 1], [2, 2]])]
    sig = analyze_recolor_rank(pairs)
    assert sig["sort_key"] is None


def test_analyze_abstains_on_mismatched_group_count():
    # 1 group in pair0, 2 groups in pair1 -> no family-constant rank reading.
    pairs = [
        _pair(0, [[5, 0, 0]], [[1, 0, 0]]),
        _pair(1, [[5, 0, 5]], [[1, 0, 2]]),
    ]
    sig = analyze_recolor_rank(pairs)
    assert sig["sort_key"] is None


# ── matcher ──────────────────────────────────────────────────────────────────
def test_matcher_fires_with_evidence():
    task, _ = _rank_task()
    patterns = {"recolor_rank": analyze_recolor_rank(task.example_pairs)}
    assert match_condition("recolor_rank", patterns, {"min_evidence": 2}) is True


def test_matcher_respects_min_evidence():
    # a single pair cannot establish a family-constant ordering key.
    pairs = [_pair(0, [[5, 0, 0], [0, 0, 0], [0, 0, 5]],
                    [[1, 0, 0], [0, 0, 0], [0, 0, 2]])]
    patterns = {"recolor_rank": analyze_recolor_rank(pairs)}
    assert match_condition("recolor_rank", patterns, {"min_evidence": 2}) is False


# ── renderer: coloring composition, non-source cells untouched ───────────────
def test_render_recolor_rank_paints_by_rank():
    grid = [[5, 0, 0],
            [0, 0, 0],
            [0, 0, 5]]
    out = render_recolor_rank(grid, "top_row", 1, [5])
    assert out == [[1, 0, 0],
                   [0, 0, 0],
                   [0, 0, 2]]


def test_render_leaves_non_source_cells():
    # a non-source colour (7) in the grid must be preserved verbatim.
    grid = [[5, 7],
            [0, 5]]
    out = render_recolor_rank(grid, "top_row", 1, [5])
    assert out == [[1, 7],
                   [0, 2]]


# ── GeneralizeOperator emits a canonical {condition, action} rule ───────────
def test_generalize_emits_canonical_rank_rule():
    task, _ = _rank_task()
    wm = SimpleNamespace(task=task, s1={})
    ExtractPatternOperator().effect(wm)
    GeneralizeOperator().effect(wm)

    rule = wm.s1["active-rules"][0]
    # Canonical schema, NOT a legacy {type: recolor_sequential} envelope.
    assert "type" not in rule
    assert rule["condition"]["type"] == "recolor_rank"
    assert rule["action"]["dsl"] == RECOLOR_RANK_DSL
    assert rule["category"] == "recolor_rank"
    assert rule["action"]["args"]["sort_key"] == "top_row"
    assert rule["action"]["args"]["source_colors"] == [5]


# ── end-to-end: the pipeline renders the correct test grid ──────────────────
def test_predict_renders_correct_test_grid():
    task, expected = _rank_task()
    wm = SimpleNamespace(task=task, s1={})
    ExtractPatternOperator().effect(wm)
    GeneralizeOperator().effect(wm)
    PredictOperator().effect(wm)

    assert wm.s1["predictions"]["test_0"] == expected
