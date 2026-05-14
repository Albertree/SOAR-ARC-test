"""
tests/test_output_colors_partial_overlap_with_input_colors_per_group.py
-- exercise the iter-206 matcher
``agent.conditions.output_colors_partial_overlap_with_input_colors_per_group``
(new in this iter).

Pins the matcher's contract per the module docstring: every change
group in every example pair satisfies
``set(group["input_colors"]) & set(group["output_colors"]) != ∅`` AND
``NOT (set(input_colors) <= set(output_colors))`` AND ``NOT (set(
output_colors) <= set(input_colors))`` -- per-group palettes
intersect but neither contains the other.

This matcher is the residual cell of the per-group palette-relation
sub-axis closed by iters 200 / 201 / 202 / 203 / 204 / 205. It is
strictly mutually exclusive with every other per-group palette-
relation matcher (iters 200 / 201 / 202 / 203 / 204 / 205) on the
cell-count-non-empty domain. The strict mutual exclusion relations
are pinned by the ``test_mutually_exclusive_with_iter*`` cells
below.

Runs without pytest:

    python tests/test_output_colors_partial_overlap_with_input_colors_per_group.py

Dependency-free, same runner style as the other tests under ``tests/``.
"""

from __future__ import annotations

import copy
import os
import sys
import traceback

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

from agent.conditions import CONDITION_REGISTRY  # noqa: E402


MATCHER_NAME = "output_colors_partial_overlap_with_input_colors_per_group"


def _matcher():
    return CONDITION_REGISTRY[MATCHER_NAME]


def _group(*, input_colors=(1, 2), output_colors=(2, 3), positions=None):
    """Build a group analysis dict matching ``_analyze_pair``'s emit shape."""
    if positions is None:
        positions = [(0, 0)]
    sorted_positions = sorted(tuple(p) for p in positions)
    if sorted_positions:
        top_row = min(r for r, _ in sorted_positions)
        top_col = min(c for _, c in sorted_positions)
    else:
        top_row = 0
        top_col = 0
    return {
        "input_colors": sorted(set(input_colors)),
        "output_colors": sorted(set(output_colors)),
        "top_row": top_row,
        "top_col": top_col,
        "cell_count": len(sorted_positions),
        "positions": sorted_positions,
    }


def _analysis(*, groups, input_height=4, input_width=4,
              output_height=None, output_width=None, size_match=None,
              num_groups=None, input_palette=None, output_palette=None):
    if output_height is None:
        output_height = input_height
    if output_width is None:
        output_width = input_width
    if size_match is None:
        size_match = (input_height == output_height
                      and input_width == output_width)
    if num_groups is None:
        num_groups = len(groups)
    analysis = {
        "total_changes": sum(g.get("cell_count", 0) for g in groups),
        "num_groups": num_groups,
        "groups": list(groups),
        "size_match": size_match,
        "input_height": input_height,
        "input_width": input_width,
        "output_height": output_height,
        "output_width": output_width,
    }
    if input_palette is not None:
        analysis["input_palette"] = list(input_palette)
    if output_palette is not None:
        analysis["output_palette"] = list(output_palette)
    return analysis


# ──────────────────────────────────────────────────────────────────────────
# Smoke / membership tests.
# ──────────────────────────────────────────────────────────────────────────

def test_registered_in_global_registry() -> None:
    assert MATCHER_NAME in CONDITION_REGISTRY, (
        f"{MATCHER_NAME!r} not registered; got {sorted(CONDITION_REGISTRY)}"
    )


def test_matcher_is_callable() -> None:
    fn = _matcher()
    assert callable(fn), f"registered entry is not callable: {fn!r}"


# ──────────────────────────────────────────────────────────────────────────
# Positive cases -- per-group partial overlap strictly per group.
# ──────────────────────────────────────────────────────────────────────────

def test_returns_true_on_single_pair_single_group_partial_overlap() -> None:
    # input={1, 2} / output={2, 3} -- intersect on {2}, neither
    # contains the other.
    patterns = {"pair_analyses": [
        _analysis(groups=[_group(input_colors=[1, 2], output_colors=[2, 3])]),
    ]}
    assert _matcher()(patterns, {}) is True


def test_returns_true_on_two_pairs_partial_overlap() -> None:
    patterns = {"pair_analyses": [
        _analysis(groups=[_group(input_colors=[1, 2], output_colors=[2, 3])]),
        _analysis(groups=[_group(input_colors=[3, 4], output_colors=[4, 5])]),
    ]}
    assert _matcher()(patterns, {}) is True


def test_returns_true_on_multi_group_per_pair_all_partial_overlap() -> None:
    patterns = {"pair_analyses": [
        _analysis(groups=[
            _group(input_colors=[1, 2], output_colors=[2, 3]),
            _group(input_colors=[4, 5], output_colors=[5, 6]),
        ]),
        _analysis(groups=[
            _group(input_colors=[6, 7], output_colors=[7, 8]),
            _group(input_colors=[8, 9], output_colors=[9, 0]),
        ]),
    ]}
    assert _matcher()(patterns, {}) is True


def test_returns_true_on_large_intersection_with_partial_overlap() -> None:
    # input={1, 2, 3, 4} / output={3, 4, 5, 6} -- intersection {3, 4},
    # input has {1, 2} not in output, output has {5, 6} not in input.
    patterns = {"pair_analyses": [
        _analysis(groups=[_group(
            input_colors=[1, 2, 3, 4],
            output_colors=[3, 4, 5, 6],
        )]),
    ]}
    assert _matcher()(patterns, {}) is True


def test_returns_true_on_three_pairs_all_partial_overlap() -> None:
    patterns = {"pair_analyses": [
        _analysis(groups=[_group(input_colors=[1, 2], output_colors=[2, 3])]),
        _analysis(groups=[_group(input_colors=[3, 4], output_colors=[4, 5])]),
        _analysis(groups=[_group(input_colors=[5, 6], output_colors=[6, 7])]),
    ]}
    assert _matcher()(patterns, {}) is True


def test_returns_true_on_varying_num_groups_per_pair_all_partial() -> None:
    patterns = {"pair_analyses": [
        _analysis(groups=[_group(input_colors=[1, 2], output_colors=[2, 3])]),
        _analysis(groups=[
            _group(input_colors=[2, 3], output_colors=[3, 4]),
            _group(input_colors=[4, 5], output_colors=[5, 6]),
        ]),
        _analysis(groups=[
            _group(input_colors=[5, 6, 7], output_colors=[6, 7, 8]),
            _group(input_colors=[7, 8], output_colors=[8, 9]),
            _group(input_colors=[0, 1], output_colors=[1, 2]),
        ]),
    ]}
    assert _matcher()(patterns, {}) is True


def test_returns_true_on_color_zero_in_intersection() -> None:
    # Colour 0 is a valid strict int and can be the shared anchor.
    patterns = {"pair_analyses": [
        _analysis(groups=[_group(input_colors=[0, 5], output_colors=[0, 7])]),
    ]}
    assert _matcher()(patterns, {}) is True


def test_returns_true_on_color_nine_in_intersection() -> None:
    # Colour 9 is a valid strict int and can be the shared anchor.
    patterns = {"pair_analyses": [
        _analysis(groups=[_group(input_colors=[8, 9], output_colors=[7, 9])]),
    ]}
    assert _matcher()(patterns, {}) is True


def test_returns_true_on_minimum_size_partial_overlap() -> None:
    # Minimum-size case: |A| == 2, |B| == 2, |A ∩ B| == 1.
    patterns = {"pair_analyses": [
        _analysis(groups=[_group(input_colors=[1, 2], output_colors=[1, 3])]),
    ]}
    assert _matcher()(patterns, {}) is True


# ──────────────────────────────────────────────────────────────────────────
# Negative cases -- equality / subset / superset / disjoint.
# ──────────────────────────────────────────────────────────────────────────

def test_returns_false_on_per_group_equality_singleton() -> None:
    # input=[1] / output=[1] -- per-group equality (iter 201 fires).
    # Partial overlap REQUIRES neither containment direction; equality
    # implies BOTH. Reject.
    patterns = {"pair_analyses": [
        _analysis(groups=[_group(input_colors=[1], output_colors=[1])]),
    ]}
    assert _matcher()(patterns, {}) is False


def test_returns_false_on_per_group_equality_multi_color() -> None:
    # input=[1, 2] / output=[1, 2] -- per-group equality.
    patterns = {"pair_analyses": [
        _analysis(groups=[_group(input_colors=[1, 2], output_colors=[1, 2])]),
    ]}
    assert _matcher()(patterns, {}) is False


def test_returns_false_on_per_group_strict_erasure() -> None:
    # input=[1, 2] ⊋ output=[1] -- strict erasure (iter 204 fires).
    # Partial overlap REQUIRES output NOT ⊆ input; iter 204 fires
    # implies output ⊆ input. Reject.
    patterns = {"pair_analyses": [
        _analysis(groups=[_group(input_colors=[1, 2], output_colors=[1])]),
    ]}
    assert _matcher()(patterns, {}) is False


def test_returns_false_on_per_group_strict_expansion() -> None:
    # input=[1] ⊊ output=[1, 2] -- strict expansion (iter 205 fires).
    # Partial overlap REQUIRES input NOT ⊆ output; iter 205 fires
    # implies input ⊆ output. Reject.
    patterns = {"pair_analyses": [
        _analysis(groups=[_group(input_colors=[1], output_colors=[1, 2])]),
    ]}
    assert _matcher()(patterns, {}) is False


def test_returns_false_on_per_group_disjoint() -> None:
    # input=[1, 2] / output=[3, 4] -- fully disjoint (iter 203 fires).
    # Partial overlap REQUIRES non-empty intersection; iter 203 fires
    # implies empty intersection. Reject.
    patterns = {"pair_analyses": [
        _analysis(groups=[_group(input_colors=[1, 2], output_colors=[3, 4])]),
    ]}
    assert _matcher()(patterns, {}) is False


def test_returns_false_on_singleton_disjoint() -> None:
    # input=[1] / output=[2] -- minimal disjoint case.
    patterns = {"pair_analyses": [
        _analysis(groups=[_group(input_colors=[1], output_colors=[2])]),
    ]}
    assert _matcher()(patterns, {}) is False


def test_returns_false_when_second_group_is_equality() -> None:
    # First group OK (partial overlap), second group equality -- one
    # non-partial group dooms the universal claim.
    patterns = {"pair_analyses": [
        _analysis(groups=[
            _group(input_colors=[1, 2], output_colors=[2, 3]),
            _group(input_colors=[5], output_colors=[5]),
        ]),
    ]}
    assert _matcher()(patterns, {}) is False


def test_returns_false_when_second_group_is_strict_subset() -> None:
    patterns = {"pair_analyses": [
        _analysis(groups=[
            _group(input_colors=[1, 2], output_colors=[2, 3]),
            _group(input_colors=[5], output_colors=[5, 6]),
        ]),
    ]}
    assert _matcher()(patterns, {}) is False


def test_returns_false_when_second_group_is_disjoint() -> None:
    patterns = {"pair_analyses": [
        _analysis(groups=[
            _group(input_colors=[1, 2], output_colors=[2, 3]),
            _group(input_colors=[5], output_colors=[6]),
        ]),
    ]}
    assert _matcher()(patterns, {}) is False


def test_returns_false_when_second_pair_equality() -> None:
    patterns = {"pair_analyses": [
        _analysis(groups=[_group(input_colors=[1, 2], output_colors=[2, 3])]),
        _analysis(groups=[_group(input_colors=[3], output_colors=[3])]),
    ]}
    assert _matcher()(patterns, {}) is False


def test_returns_false_when_second_pair_disjoint() -> None:
    patterns = {"pair_analyses": [
        _analysis(groups=[_group(input_colors=[1, 2], output_colors=[2, 3])]),
        _analysis(groups=[_group(input_colors=[4, 5], output_colors=[6, 7])]),
    ]}
    assert _matcher()(patterns, {}) is False


def test_returns_false_on_identity_all_zero_groups() -> None:
    # Identity territory (iter 13). Fail-closed on empty-groups.
    patterns = {"pair_analyses": [
        _analysis(groups=[]),
        _analysis(groups=[]),
    ]}
    assert _matcher()(patterns, {}) is False


def test_returns_false_when_one_pair_has_zero_groups() -> None:
    # Mixed identity / non-identity task is disqualified.
    patterns = {"pair_analyses": [
        _analysis(groups=[_group(input_colors=[1, 2], output_colors=[2, 3])]),
        _analysis(groups=[]),
    ]}
    assert _matcher()(patterns, {}) is False


def test_returns_false_on_empty_pair_analyses() -> None:
    assert _matcher()({"pair_analyses": []}, {}) is False


def test_returns_false_on_missing_pair_analyses() -> None:
    assert _matcher()({}, {}) is False


def test_returns_false_on_non_dict_patterns() -> None:
    assert _matcher()(None, {}) is False         # type: ignore[arg-type]
    assert _matcher()([], {}) is False           # type: ignore[arg-type]
    assert _matcher()("oops", {}) is False       # type: ignore[arg-type]
    assert _matcher()(42, {}) is False           # type: ignore[arg-type]


def test_returns_false_on_non_list_pair_analyses() -> None:
    for bad in ({"k": "v"}, "string", 0):
        assert _matcher()({"pair_analyses": bad}, {}) is False, (
            f"pair_analyses={bad!r} (non-list) should not fire"
        )


def test_returns_false_on_malformed_analysis_entry() -> None:
    assert _matcher()({"pair_analyses": [None]}, {}) is False
    assert _matcher()({"pair_analyses": ["string"]}, {}) is False
    assert _matcher()({"pair_analyses": [42]}, {}) is False


# ──────────────────────────────────────────────────────────────────────────
# Strict-type gates on ``groups`` / ``input_colors`` / ``output_colors``.
# ──────────────────────────────────────────────────────────────────────────

def test_returns_false_on_missing_groups_field() -> None:
    analysis_bad = {
        "size_match": True,
        "total_changes": 1,
        "num_groups": 1,
        "input_height": 3, "input_width": 3,
        "output_height": 3, "output_width": 3,
    }
    assert _matcher()({"pair_analyses": [analysis_bad]}, {}) is False


def test_returns_false_on_non_list_groups() -> None:
    for bad in (None, "string", 42, {"k": "v"}):
        analysis_bad = {
            "size_match": True,
            "total_changes": 1,
            "num_groups": 1,
            "input_height": 3, "input_width": 3,
            "output_height": 3, "output_width": 3,
            "groups": bad,
        }
        assert _matcher()({"pair_analyses": [analysis_bad]}, {}) is False, (
            f"groups={bad!r} should fail-closed"
        )


def test_returns_false_on_non_dict_group_entry() -> None:
    for bad in (None, "string", 42, [1, 2]):
        analysis_bad = _analysis(groups=[])
        analysis_bad["groups"] = [bad]
        assert _matcher()({"pair_analyses": [analysis_bad]}, {}) is False, (
            f"group entry {bad!r} should fail-closed"
        )


def test_returns_false_on_missing_input_colors() -> None:
    group_bad = {
        "output_colors": [2, 3],
        "top_row": 0, "top_col": 0,
        "positions": [(0, 0)],
        "cell_count": 1,
    }
    analysis_bad = _analysis(groups=[])
    analysis_bad["groups"] = [group_bad]
    assert _matcher()({"pair_analyses": [analysis_bad]}, {}) is False


def test_returns_false_on_missing_output_colors() -> None:
    group_bad = {
        "input_colors": [1, 2],
        "top_row": 0, "top_col": 0,
        "positions": [(0, 0)],
        "cell_count": 1,
    }
    analysis_bad = _analysis(groups=[])
    analysis_bad["groups"] = [group_bad]
    assert _matcher()({"pair_analyses": [analysis_bad]}, {}) is False


def test_returns_false_on_non_list_input_colors() -> None:
    for bad in (None, 1, "1", {1: 2}, (1,)):
        group_bad = {
            "input_colors": bad,
            "output_colors": [2, 3],
            "top_row": 0, "top_col": 0,
            "positions": [(0, 0)],
            "cell_count": 1,
        }
        analysis_bad = _analysis(groups=[])
        analysis_bad["groups"] = [group_bad]
        assert _matcher()({"pair_analyses": [analysis_bad]}, {}) is False, (
            f"input_colors={bad!r} should fail-closed"
        )


def test_returns_false_on_non_list_output_colors() -> None:
    for bad in (None, 1, "1", {1: 2}, (1,)):
        group_bad = {
            "input_colors": [1, 2],
            "output_colors": bad,
            "top_row": 0, "top_col": 0,
            "positions": [(0, 0)],
            "cell_count": 1,
        }
        analysis_bad = _analysis(groups=[])
        analysis_bad["groups"] = [group_bad]
        assert _matcher()({"pair_analyses": [analysis_bad]}, {}) is False, (
            f"output_colors={bad!r} should fail-closed"
        )


def test_returns_false_on_empty_input_colors_list() -> None:
    group_bad = {
        "input_colors": [],
        "output_colors": [2, 3],
        "top_row": 0, "top_col": 0,
        "positions": [(0, 0)],
        "cell_count": 1,
    }
    analysis_bad = _analysis(groups=[])
    analysis_bad["groups"] = [group_bad]
    assert _matcher()({"pair_analyses": [analysis_bad]}, {}) is False


def test_returns_false_on_empty_output_colors_list() -> None:
    group_bad = {
        "input_colors": [1, 2],
        "output_colors": [],
        "top_row": 0, "top_col": 0,
        "positions": [(0, 0)],
        "cell_count": 1,
    }
    analysis_bad = _analysis(groups=[])
    analysis_bad["groups"] = [group_bad]
    assert _matcher()({"pair_analyses": [analysis_bad]}, {}) is False


def test_returns_false_on_bool_in_input_colors() -> None:
    for bad in (True, False):
        group_bad = {
            "input_colors": [bad, 2],
            "output_colors": [2, 3],
            "top_row": 0, "top_col": 0,
            "positions": [(0, 0)],
            "cell_count": 1,
        }
        analysis_bad = _analysis(groups=[])
        analysis_bad["groups"] = [group_bad]
        assert _matcher()({"pair_analyses": [analysis_bad]}, {}) is False, (
            f"input_colors=[{bad!r}, ...] (bool) should fail-closed"
        )


def test_returns_false_on_bool_in_output_colors() -> None:
    for bad in (True, False):
        group_bad = {
            "input_colors": [1, 2],
            "output_colors": [bad, 3],
            "top_row": 0, "top_col": 0,
            "positions": [(0, 0)],
            "cell_count": 1,
        }
        analysis_bad = _analysis(groups=[])
        analysis_bad["groups"] = [group_bad]
        assert _matcher()({"pair_analyses": [analysis_bad]}, {}) is False, (
            f"output_colors=[{bad!r}, ...] (bool) should fail-closed"
        )


def test_returns_false_on_out_of_range_input_color() -> None:
    for bad in (-1, 10, 100):
        group_bad = {
            "input_colors": [bad, 2],
            "output_colors": [2, 3],
            "top_row": 0, "top_col": 0,
            "positions": [(0, 0)],
            "cell_count": 1,
        }
        analysis_bad = _analysis(groups=[])
        analysis_bad["groups"] = [group_bad]
        assert _matcher()({"pair_analyses": [analysis_bad]}, {}) is False, (
            f"input_colors=[{bad!r}, ...] (out-of-range) should fail-closed"
        )


def test_returns_false_on_out_of_range_output_color() -> None:
    for bad in (-1, 10, 100):
        group_bad = {
            "input_colors": [1, 2],
            "output_colors": [bad, 3],
            "top_row": 0, "top_col": 0,
            "positions": [(0, 0)],
            "cell_count": 1,
        }
        analysis_bad = _analysis(groups=[])
        analysis_bad["groups"] = [group_bad]
        assert _matcher()({"pair_analyses": [analysis_bad]}, {}) is False, (
            f"output_colors=[{bad!r}, ...] (out-of-range) should fail-closed"
        )


def test_returns_false_on_non_int_input_color() -> None:
    for bad in (0.5, "1", None, [1]):
        group_bad = {
            "input_colors": [bad, 2],
            "output_colors": [2, 3],
            "top_row": 0, "top_col": 0,
            "positions": [(0, 0)],
            "cell_count": 1,
        }
        analysis_bad = _analysis(groups=[])
        analysis_bad["groups"] = [group_bad]
        assert _matcher()({"pair_analyses": [analysis_bad]}, {}) is False, (
            f"input_colors=[{bad!r}, ...] ({type(bad).__name__}) should fail-closed"
        )


def test_returns_false_on_non_int_output_color() -> None:
    for bad in (0.5, "1", None, [1]):
        group_bad = {
            "input_colors": [1, 2],
            "output_colors": [bad, 3],
            "top_row": 0, "top_col": 0,
            "positions": [(0, 0)],
            "cell_count": 1,
        }
        analysis_bad = _analysis(groups=[])
        analysis_bad["groups"] = [group_bad]
        assert _matcher()({"pair_analyses": [analysis_bad]}, {}) is False, (
            f"output_colors=[{bad!r}, ...] ({type(bad).__name__}) should fail-closed"
        )


def test_returns_false_on_second_pair_malformed() -> None:
    pair0 = _analysis(groups=[_group(input_colors=[1, 2], output_colors=[2, 3])])
    pair1_bad = _analysis(groups=[])
    pair1_bad["groups"] = ["not-a-dict"]
    assert _matcher()({"pair_analyses": [pair0, pair1_bad]}, {}) is False


# ──────────────────────────────────────────────────────────────────────────
# Behavioural contract: side-effect-free, deterministic, strict bool.
# ──────────────────────────────────────────────────────────────────────────

def test_is_side_effect_free_on_inputs() -> None:
    patterns = {"pair_analyses": [
        _analysis(groups=[
            _group(input_colors=[1, 2], output_colors=[2, 3]),
            _group(input_colors=[3, 4], output_colors=[4, 5]),
        ]),
        _analysis(groups=[_group(input_colors=[5, 6], output_colors=[6, 7])]),
    ]}
    params = {"unused": 1}
    before_p = copy.deepcopy(patterns)
    before_q = copy.deepcopy(params)
    _matcher()(patterns, params)
    assert patterns == before_p, "matcher mutated patterns"
    assert params == before_q, "matcher mutated params"


def test_is_deterministic_across_repeats() -> None:
    patterns = {"pair_analyses": [
        _analysis(groups=[_group(input_colors=[1, 2], output_colors=[2, 3])]),
        _analysis(groups=[_group(input_colors=[3, 4], output_colors=[4, 5])]),
    ]}
    results = [_matcher()(patterns, {}) for _ in range(5)]
    assert len(set(results)) == 1, f"non-deterministic outputs: {results}"


def test_returns_strict_boolean_type() -> None:
    pos_pat = {"pair_analyses": [
        _analysis(groups=[_group(input_colors=[1, 2], output_colors=[2, 3])]),
    ]}
    neg_pat = {"pair_analyses": [
        _analysis(groups=[_group(input_colors=[1], output_colors=[1])]),
    ]}
    pos = _matcher()(pos_pat, {})
    neg = _matcher()(neg_pat, {})
    assert pos is True, f"expected literal True, got {pos!r}"
    assert neg is False, f"expected literal False, got {neg!r}"


def test_params_argument_ignored() -> None:
    patterns = {"pair_analyses": [
        _analysis(groups=[_group(input_colors=[1, 2], output_colors=[2, 3])]),
    ]}
    assert _matcher()(patterns, {}) is True
    assert _matcher()(patterns, {"target": 99}) is True
    assert _matcher()(patterns, {"K": 7, "junk": [1, 2]}) is True


def test_whole_grid_palette_fields_ignored() -> None:
    # The matcher operates on per-group ``input_colors`` / ``output_colors``
    # only; whole-grid palette fields on the analysis dict must be
    # irrelevant.
    patterns = {"pair_analyses": [
        _analysis(
            groups=[_group(input_colors=[1, 2], output_colors=[2, 3])],
            input_palette=[1, 2, 3, 4, 5, 6, 7, 8, 9],
            output_palette=[0],
        ),
    ]}
    assert _matcher()(patterns, {}) is True


# ──────────────────────────────────────────────────────────────────────────
# Orthogonality / strict-mutual-exclusion against neighbouring matchers.
# ──────────────────────────────────────────────────────────────────────────

def test_mutually_exclusive_with_identity_transformation() -> None:
    identity_pat = {
        "grid_size_preserved": True,
        "pair_analyses": [
            _analysis(groups=[]),
            _analysis(groups=[]),
        ],
    }
    paint_pat = {
        "grid_size_preserved": True,
        "pair_analyses": [
            _analysis(groups=[_group(input_colors=[1, 2], output_colors=[2, 3])]),
        ],
    }
    identity = CONDITION_REGISTRY["identity_transformation"]
    assert identity(identity_pat, {}) is True
    assert _matcher()(identity_pat, {}) is False
    assert identity(paint_pat, {}) is False
    assert _matcher()(paint_pat, {}) is True


def test_mutually_exclusive_with_iter200_on_non_empty_palettes() -> None:
    # Iter 200 (output ⊆ input per group) fires; this matcher requires
    # NOT (output ⊆ input) per group. Strict mutual exclusion.
    erasure_pat = {"pair_analyses": [
        _analysis(groups=[_group(input_colors=[1, 2], output_colors=[1])]),
    ]}
    iter200 = CONDITION_REGISTRY[
        "output_colors_subset_of_input_colors_per_group"
    ]
    assert iter200(erasure_pat, {}) is True
    assert _matcher()(erasure_pat, {}) is False
    overlap_pat = {"pair_analyses": [
        _analysis(groups=[_group(input_colors=[1, 2], output_colors=[2, 3])]),
    ]}
    assert iter200(overlap_pat, {}) is False
    assert _matcher()(overlap_pat, {}) is True


def test_mutually_exclusive_with_iter201_on_non_empty_palettes() -> None:
    # Iter 201 (equality per group) fires; this matcher requires BOTH
    # containments to fail, but equality implies both. Strict mutual
    # exclusion.
    equality_pat = {"pair_analyses": [
        _analysis(groups=[_group(input_colors=[1, 2], output_colors=[1, 2])]),
    ]}
    iter201 = CONDITION_REGISTRY[
        "output_colors_equals_input_colors_per_group"
    ]
    assert iter201(equality_pat, {}) is True
    assert _matcher()(equality_pat, {}) is False
    overlap_pat = {"pair_analyses": [
        _analysis(groups=[_group(input_colors=[1, 2], output_colors=[2, 3])]),
    ]}
    assert iter201(overlap_pat, {}) is False
    assert _matcher()(overlap_pat, {}) is True


def test_mutually_exclusive_with_iter202_on_non_empty_palettes() -> None:
    # Iter 202 (input ⊆ output per group) fires; this matcher requires
    # NOT (input ⊆ output) per group. Strict mutual exclusion.
    expansion_pat = {"pair_analyses": [
        _analysis(groups=[_group(input_colors=[1], output_colors=[1, 2])]),
    ]}
    iter202 = CONDITION_REGISTRY[
        "input_colors_subset_of_output_colors_per_group"
    ]
    assert iter202(expansion_pat, {}) is True
    assert _matcher()(expansion_pat, {}) is False
    overlap_pat = {"pair_analyses": [
        _analysis(groups=[_group(input_colors=[1, 2], output_colors=[2, 3])]),
    ]}
    assert iter202(overlap_pat, {}) is False
    assert _matcher()(overlap_pat, {}) is True


def test_mutually_exclusive_with_iter203_on_non_empty_palettes() -> None:
    # Iter 203 (disjoint per group) fires; this matcher requires non-
    # empty intersection per group. Strict mutual exclusion.
    disjoint_pat = {"pair_analyses": [
        _analysis(groups=[_group(input_colors=[1, 2], output_colors=[3, 4])]),
    ]}
    iter203 = CONDITION_REGISTRY[
        "output_colors_disjoint_from_input_colors_per_group"
    ]
    assert iter203(disjoint_pat, {}) is True
    assert _matcher()(disjoint_pat, {}) is False
    overlap_pat = {"pair_analyses": [
        _analysis(groups=[_group(input_colors=[1, 2], output_colors=[2, 3])]),
    ]}
    assert iter203(overlap_pat, {}) is False
    assert _matcher()(overlap_pat, {}) is True


def test_mutually_exclusive_with_iter204_on_non_empty_palettes() -> None:
    # Iter 204 (output ⊊ input per group) is the strict-erasure refinement
    # of iter 200. Strict mutual exclusion with this matcher (output ⊊
    # input implies output ⊆ input; this matcher requires NOT (output ⊆
    # input)).
    strict_erasure_pat = {"pair_analyses": [
        _analysis(groups=[_group(input_colors=[1, 2], output_colors=[1])]),
    ]}
    iter204 = CONDITION_REGISTRY[
        "output_colors_proper_subset_of_input_colors_per_group"
    ]
    assert iter204(strict_erasure_pat, {}) is True
    assert _matcher()(strict_erasure_pat, {}) is False
    overlap_pat = {"pair_analyses": [
        _analysis(groups=[_group(input_colors=[1, 2], output_colors=[2, 3])]),
    ]}
    assert iter204(overlap_pat, {}) is False
    assert _matcher()(overlap_pat, {}) is True


def test_mutually_exclusive_with_iter205_on_non_empty_palettes() -> None:
    # Iter 205 (input ⊊ output per group) is the strict-expansion
    # refinement of iter 202. Strict mutual exclusion with this matcher
    # (input ⊊ output implies input ⊆ output; this matcher requires
    # NOT (input ⊆ output)).
    strict_expansion_pat = {"pair_analyses": [
        _analysis(groups=[_group(input_colors=[1], output_colors=[1, 2])]),
    ]}
    iter205 = CONDITION_REGISTRY[
        "input_colors_proper_subset_of_output_colors_per_group"
    ]
    assert iter205(strict_expansion_pat, {}) is True
    assert _matcher()(strict_expansion_pat, {}) is False
    overlap_pat = {"pair_analyses": [
        _analysis(groups=[_group(input_colors=[1, 2], output_colors=[2, 3])]),
    ]}
    assert iter205(overlap_pat, {}) is False
    assert _matcher()(overlap_pat, {}) is True


def test_iter186_strictly_mutually_exclusive_with_this_matcher() -> None:
    # Per-group input ∩ output != ∅ implies the whole-grid input palette
    # and whole-grid output palette share at least one colour (the per-
    # group intersection colour) -- iter 186 (whole-grid disjoint) MUST
    # reject.
    overlap_patterns = {
        "pair_analyses": [
            _analysis(
                groups=[_group(input_colors=[1, 2], output_colors=[2, 3])],
                input_palette=[1, 2],
                output_palette=[2, 3],
            ),
        ],
    }
    iter186 = CONDITION_REGISTRY["output_palette_disjoint_from_input"]
    assert iter186(overlap_patterns, {}) is False
    assert _matcher()(overlap_patterns, {}) is True


def test_iter14_strict_mutual_exclusion_on_singleton_input() -> None:
    # Iter 14 (input_color_uniform) pins every group's input_colors to
    # a single colour. With |A| == 1, NOT (A ⊆ B) requires A ∩ B == ∅,
    # so partial overlap (which requires A ∩ B != ∅) is impossible.
    singleton_patterns = {"pair_analyses": [
        _analysis(groups=[_group(input_colors=[1], output_colors=[2])]),
        _analysis(groups=[_group(input_colors=[1], output_colors=[3])]),
    ]}
    iter14 = CONDITION_REGISTRY["input_color_uniform"]
    assert iter14(singleton_patterns, {}) is True
    assert _matcher()(singleton_patterns, {}) is False


def test_iter18_strict_mutual_exclusion_on_singleton_output() -> None:
    # Iter 18 (output_color_uniform) pins every group's output_colors to
    # the same single colour. With |B| == 1, NOT (B ⊆ A) requires B ∩ A
    # == ∅, so partial overlap is impossible. Note iter 18 requires the
    # single output colour to be IDENTICAL across all groups -- both
    # groups below share output_colors=[1].
    singleton_output_patterns = {"pair_analyses": [
        _analysis(groups=[_group(input_colors=[2], output_colors=[1])]),
        _analysis(groups=[_group(input_colors=[3], output_colors=[1])]),
    ]}
    iter18 = CONDITION_REGISTRY["output_color_uniform"]
    assert iter18(singleton_output_patterns, {}) is True
    assert _matcher()(singleton_output_patterns, {}) is False


def test_iter199_globally_constant_nonzero_shift_rejects_this_matcher() -> None:
    # A globally-constant non-zero shift makes every group's output set
    # disjoint from input set (iter 199 fires); this matcher rejects
    # (intersection empty, not partial overlap).
    patterns = {"pair_analyses": [
        _analysis(groups=[_group(input_colors=[1], output_colors=[4])]),
        _analysis(groups=[_group(input_colors=[2], output_colors=[5])]),
    ]}
    iter199 = CONDITION_REGISTRY[
        "palette_shift_constant_across_groups_and_pairs"
    ]
    assert iter199(patterns, {}) is True
    assert _matcher()(patterns, {}) is False


def test_co_fires_with_grid_size_preserved() -> None:
    # Orthogonal axes: grid_size_preserved is a dimensional flag, this
    # matcher inspects per-group palette content.
    patterns = {
        "grid_size_preserved": True,
        "pair_analyses": [
            _analysis(groups=[_group(input_colors=[1, 2], output_colors=[2, 3])]),
        ],
    }
    iter1 = CONDITION_REGISTRY["grid_size_preserved"]
    assert iter1(patterns, {}) is True
    assert _matcher()(patterns, {}) is True


# ──────────────────────────────────────────────────────────────────────────
# Recognized-conditions wiring.
# ──────────────────────────────────────────────────────────────────────────

def test_recognized_conditions_includes_matcher_on_partial_overlap() -> None:
    from agent.conditions import recognized_conditions
    patterns = {
        "pair_analyses": [
            _analysis(groups=[_group(input_colors=[1, 2], output_colors=[2, 3])]),
        ],
    }
    fired = recognized_conditions(patterns)
    assert MATCHER_NAME in fired, (
        f"{MATCHER_NAME!r} did not fire on per-group partial-overlap "
        f"patterns; got {fired!r}"
    )


def test_recognized_conditions_excludes_on_per_group_equality() -> None:
    # Per-group equality fires iters 200 / 201 / 202 but NOT this matcher.
    from agent.conditions import recognized_conditions
    patterns = {
        "pair_analyses": [
            _analysis(groups=[_group(input_colors=[1, 2], output_colors=[1, 2])]),
        ],
    }
    fired = recognized_conditions(patterns)
    assert MATCHER_NAME not in fired, (
        f"{MATCHER_NAME!r} must NOT fire on per-group equality; got "
        f"{fired!r}"
    )
    assert "output_colors_equals_input_colors_per_group" in fired, (
        "iter 201 must still fire on per-group equality"
    )


def test_recognized_conditions_excludes_other_per_group_palette_relation_matchers_on_overlap() -> None:
    # On the partial-overlap cell, this matcher fires and ALL other
    # per-group palette-relation matchers (iters 200 / 201 / 202 / 203 /
    # 204 / 205) MUST reject. This is the residual-cell-of-the-partition
    # wiring check.
    from agent.conditions import recognized_conditions
    patterns = {
        "pair_analyses": [
            _analysis(groups=[_group(input_colors=[1, 2], output_colors=[2, 3])]),
        ],
    }
    fired = recognized_conditions(patterns)
    assert MATCHER_NAME in fired
    assert "output_colors_subset_of_input_colors_per_group" not in fired
    assert "output_colors_equals_input_colors_per_group" not in fired
    assert "input_colors_subset_of_output_colors_per_group" not in fired
    assert "output_colors_disjoint_from_input_colors_per_group" not in fired
    assert "output_colors_proper_subset_of_input_colors_per_group" not in fired
    assert "input_colors_proper_subset_of_output_colors_per_group" not in fired


def test_recognized_conditions_excludes_this_matcher_on_disjoint() -> None:
    # The symmetric wiring check: on a per-group disjoint pattern, iter
    # 203 fires; this matcher MUST reject.
    from agent.conditions import recognized_conditions
    patterns = {
        "pair_analyses": [
            _analysis(groups=[_group(input_colors=[1, 2], output_colors=[3, 4])]),
        ],
    }
    fired = recognized_conditions(patterns)
    assert "output_colors_disjoint_from_input_colors_per_group" in fired
    assert MATCHER_NAME not in fired


# ──────────────────────────────────────────────────────────────────────────
# Test runner (dependency-free, same style as the other tests).
# ──────────────────────────────────────────────────────────────────────────

def _run() -> int:
    tests = [
        (name, fn) for name, fn in globals().items()
        if name.startswith("test_") and callable(fn)
    ]
    failed = 0
    for name, fn in tests:
        try:
            fn()
            print(f"  OK   {name}")
        except AssertionError as e:
            failed += 1
            print(f"  FAIL {name}: {e}")
            traceback.print_exc()
        except Exception as e:  # pragma: no cover -- defensive
            failed += 1
            print(f"  ERR  {name}: {e!r}")
            traceback.print_exc()
    print(f"\n{len(tests) - failed}/{len(tests)} passed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(_run())
