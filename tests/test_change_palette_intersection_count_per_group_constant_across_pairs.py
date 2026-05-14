"""
tests/test_change_palette_intersection_count_per_group_constant_across_pairs.py
-- exercise the iter-207 matcher
``agent.conditions.change_palette_intersection_count_per_group_constant_across_pairs``
(new in this iter).

Pins the matcher's contract per the module docstring: every change
group in every example pair has the SAME derived integer
``len(set(input_colors) & set(output_colors))``, with that single
integer K determined by the first observed group. The matcher does
not pin a specific K, only the cross-pair / cross-group constancy of
that single derived integer; the COLOURS themselves are free.

Sits on the per-group intersection-cardinality sub-axis -- the
per-group projection of iter 44 (``palette_intersection_count_
constant_across_pairs``, whole-grid |A ∩ B|) and the dual of iter
195 / 196 / 197 (per-group |ic| / |oc| / |ic| * |oc| handles).
Strictly implied by iter 203 (per-group disjoint, K==0). Independent
of iters 200 / 201 / 202 / 204 / 205 / 206 in general.

Runs without pytest:

    python tests/test_change_palette_intersection_count_per_group_constant_across_pairs.py

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


MATCHER_NAME = (
    "change_palette_intersection_count_per_group_constant_across_pairs"
)


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
# Positive cases -- constant per-group |ic ∩ oc| across groups / pairs.
# ──────────────────────────────────────────────────────────────────────────

def test_returns_true_on_single_pair_single_group_K_equals_zero() -> None:
    # |{1} ∩ {2}| == 0.
    patterns = {"pair_analyses": [
        _analysis(groups=[_group(input_colors=[1], output_colors=[2])]),
    ]}
    assert _matcher()(patterns, {}) is True


def test_returns_true_on_single_pair_single_group_K_equals_one() -> None:
    # |{1, 2} ∩ {2, 3}| == 1.
    patterns = {"pair_analyses": [
        _analysis(groups=[_group(input_colors=[1, 2], output_colors=[2, 3])]),
    ]}
    assert _matcher()(patterns, {}) is True


def test_returns_true_on_single_pair_single_group_K_equals_two() -> None:
    # |{1, 2, 3} ∩ {2, 3, 4}| == 2.
    patterns = {"pair_analyses": [
        _analysis(groups=[_group(
            input_colors=[1, 2, 3],
            output_colors=[2, 3, 4],
        )]),
    ]}
    assert _matcher()(patterns, {}) is True


def test_returns_true_on_two_pairs_K_constant_equals_one() -> None:
    patterns = {"pair_analyses": [
        _analysis(groups=[_group(input_colors=[1, 2], output_colors=[2, 3])]),
        _analysis(groups=[_group(input_colors=[4, 5], output_colors=[5, 6])]),
    ]}
    assert _matcher()(patterns, {}) is True


def test_returns_true_on_multi_group_per_pair_all_K_one() -> None:
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


def test_returns_true_on_three_pairs_K_constant_equals_zero() -> None:
    # Per-group disjoint everywhere -- iter 203 fires, this matcher
    # fires with K==0.
    patterns = {"pair_analyses": [
        _analysis(groups=[_group(input_colors=[1, 2], output_colors=[3, 4])]),
        _analysis(groups=[_group(input_colors=[5, 6], output_colors=[7, 8])]),
        _analysis(groups=[_group(input_colors=[0, 9], output_colors=[7, 8])]),
    ]}
    assert _matcher()(patterns, {}) is True


def test_returns_true_when_per_group_equality_with_constant_palette_size() -> None:
    # Per-group equality with constant |ic| == |oc| == 2 across groups:
    # iter 201 fires, |ic ∩ oc| == 2 on every group, constant.
    patterns = {"pair_analyses": [
        _analysis(groups=[_group(input_colors=[1, 2], output_colors=[1, 2])]),
        _analysis(groups=[_group(input_colors=[5, 6], output_colors=[5, 6])]),
    ]}
    assert _matcher()(patterns, {}) is True


def test_returns_true_on_color_zero_in_intersection() -> None:
    # Colour 0 valid; |{0, 1} ∩ {0, 2}| == 1 across both pairs.
    patterns = {"pair_analyses": [
        _analysis(groups=[_group(input_colors=[0, 1], output_colors=[0, 2])]),
        _analysis(groups=[_group(input_colors=[0, 5], output_colors=[0, 7])]),
    ]}
    assert _matcher()(patterns, {}) is True


def test_returns_true_on_color_nine_in_intersection() -> None:
    # Colour 9 valid; |{8, 9} ∩ {7, 9}| == 1 across both pairs.
    patterns = {"pair_analyses": [
        _analysis(groups=[_group(input_colors=[8, 9], output_colors=[7, 9])]),
        _analysis(groups=[_group(input_colors=[1, 9], output_colors=[2, 9])]),
    ]}
    assert _matcher()(patterns, {}) is True


def test_returns_true_on_varying_num_groups_per_pair_all_K_one() -> None:
    patterns = {"pair_analyses": [
        _analysis(groups=[_group(input_colors=[1, 2], output_colors=[2, 3])]),
        _analysis(groups=[
            _group(input_colors=[2, 3], output_colors=[3, 4]),
            _group(input_colors=[4, 5], output_colors=[5, 6]),
        ]),
        _analysis(groups=[
            _group(input_colors=[5, 6, 7], output_colors=[7, 8, 0]),
            _group(input_colors=[1, 8], output_colors=[8, 9]),
            _group(input_colors=[0, 1], output_colors=[1, 2]),
        ]),
    ]}
    assert _matcher()(patterns, {}) is True


def test_returns_true_when_single_pair_single_group_with_arbitrary_K() -> None:
    # Single observation trivially constant.
    patterns = {"pair_analyses": [
        _analysis(groups=[_group(
            input_colors=[0, 1, 2, 3, 4],
            output_colors=[3, 4, 5, 6, 7],
        )]),
    ]}
    assert _matcher()(patterns, {}) is True


# ──────────────────────────────────────────────────────────────────────────
# Negative cases -- per-group |ic ∩ oc| varies.
# ──────────────────────────────────────────────────────────────────────────

def test_returns_false_when_K_varies_across_groups_within_a_pair() -> None:
    # Group 0: |{1, 2} ∩ {2, 3}| == 1.
    # Group 1: |{1, 2} ∩ {3, 4}| == 0.  K varies; reject.
    patterns = {"pair_analyses": [
        _analysis(groups=[
            _group(input_colors=[1, 2], output_colors=[2, 3]),
            _group(input_colors=[1, 2], output_colors=[3, 4]),
        ]),
    ]}
    assert _matcher()(patterns, {}) is False


def test_returns_false_when_K_varies_across_pairs() -> None:
    # Pair 0 group: |∩| == 1; pair 1 group: |∩| == 2. Reject.
    patterns = {"pair_analyses": [
        _analysis(groups=[_group(input_colors=[1, 2], output_colors=[2, 3])]),
        _analysis(groups=[_group(
            input_colors=[1, 2, 3], output_colors=[1, 2, 4],
        )]),
    ]}
    assert _matcher()(patterns, {}) is False


def test_returns_false_when_one_group_in_one_pair_breaks_constancy() -> None:
    # Three of four groups have |∩| == 1; fourth has |∩| == 2.
    patterns = {"pair_analyses": [
        _analysis(groups=[
            _group(input_colors=[1, 2], output_colors=[2, 3]),
            _group(input_colors=[4, 5], output_colors=[5, 6]),
        ]),
        _analysis(groups=[
            _group(input_colors=[6, 7], output_colors=[7, 8]),
            _group(input_colors=[0, 1, 2], output_colors=[1, 2, 3]),
        ]),
    ]}
    assert _matcher()(patterns, {}) is False


def test_returns_false_when_first_group_is_K_zero_and_rest_K_one() -> None:
    # Canonical-K-from-first-group: K_canon == 0; subsequent K == 1 must
    # reject.
    patterns = {"pair_analyses": [
        _analysis(groups=[
            _group(input_colors=[1], output_colors=[2]),
            _group(input_colors=[2, 3], output_colors=[3, 4]),
        ]),
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
        _analysis(groups=[
            _group(input_colors=[1, 2], output_colors=[2, 3]),
            _group(input_colors=[1, 2], output_colors=[3, 4]),
        ]),
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
    # The matcher operates on per-group ``input_colors`` /
    # ``output_colors`` only; whole-grid palette fields on the analysis
    # dict must be irrelevant.
    patterns = {"pair_analyses": [
        _analysis(
            groups=[_group(input_colors=[1, 2], output_colors=[2, 3])],
            input_palette=[1, 2, 3, 4, 5, 6, 7, 8, 9],
            output_palette=[0],
        ),
    ]}
    assert _matcher()(patterns, {}) is True


# ──────────────────────────────────────────────────────────────────────────
# Orthogonality / refinement / co-fire matrix.
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


def test_iter203_strictly_implies_this_matcher_canonical_K_zero() -> None:
    # Iter 203 (per-group disjoint) fires ⇒ |ic ∩ oc| == 0 on every
    # group; constant K==0 ⇒ this matcher fires too. STRICT IMPLICATION
    # in the direction iter 203 ⇒ this matcher.
    disjoint_pat = {"pair_analyses": [
        _analysis(groups=[_group(input_colors=[1, 2], output_colors=[3, 4])]),
        _analysis(groups=[_group(input_colors=[5, 6], output_colors=[7, 8])]),
    ]}
    iter203 = CONDITION_REGISTRY[
        "output_colors_disjoint_from_input_colors_per_group"
    ]
    assert iter203(disjoint_pat, {}) is True
    assert _matcher()(disjoint_pat, {}) is True


def test_iter203_reverse_does_not_hold_constant_K_one() -> None:
    # This matcher fires with K==1 on partial-overlap pairs; iter 203
    # (disjoint) MUST reject.
    overlap_pat = {"pair_analyses": [
        _analysis(groups=[_group(input_colors=[1, 2], output_colors=[2, 3])]),
        _analysis(groups=[_group(input_colors=[4, 5], output_colors=[5, 6])]),
    ]}
    iter203 = CONDITION_REGISTRY[
        "output_colors_disjoint_from_input_colors_per_group"
    ]
    assert _matcher()(overlap_pat, {}) is True
    assert iter203(overlap_pat, {}) is False


def test_independent_of_iter201_when_palette_size_varies() -> None:
    # Per-group equality with VARYING |ic| (== |oc|) across groups:
    # iter 201 fires (each group is self-equal), but |ic ∩ oc| varies
    # (group 0: |∩|==1; group 1: |∩|==2). This matcher REJECTS.
    patterns = {"pair_analyses": [
        _analysis(groups=[
            _group(input_colors=[1], output_colors=[1]),
            _group(input_colors=[5, 6], output_colors=[5, 6]),
        ]),
    ]}
    iter201 = CONDITION_REGISTRY[
        "output_colors_equals_input_colors_per_group"
    ]
    assert iter201(patterns, {}) is True
    assert _matcher()(patterns, {}) is False


def test_independent_of_iter200_when_oc_size_varies() -> None:
    # Per-group oc ⊆ ic with VARYING |oc|: iter 200 fires; |ic ∩ oc|
    # == |oc| varies. This matcher REJECTS.
    patterns = {"pair_analyses": [
        _analysis(groups=[
            _group(input_colors=[1, 2], output_colors=[1]),
            _group(input_colors=[3, 4, 5], output_colors=[3, 4]),
        ]),
    ]}
    iter200 = CONDITION_REGISTRY[
        "output_colors_subset_of_input_colors_per_group"
    ]
    assert iter200(patterns, {}) is True
    assert _matcher()(patterns, {}) is False


def test_independent_of_iter202_when_ic_size_varies() -> None:
    # Per-group ic ⊆ oc with VARYING |ic|: iter 202 fires; |ic ∩ oc|
    # == |ic| varies. This matcher REJECTS.
    patterns = {"pair_analyses": [
        _analysis(groups=[
            _group(input_colors=[1], output_colors=[1, 2]),
            _group(input_colors=[3, 4], output_colors=[3, 4, 5]),
        ]),
    ]}
    iter202 = CONDITION_REGISTRY[
        "input_colors_subset_of_output_colors_per_group"
    ]
    assert iter202(patterns, {}) is True
    assert _matcher()(patterns, {}) is False


def test_independent_of_iter206_when_intersection_size_varies() -> None:
    # Per-group partial-overlap with VARYING |ic ∩ oc|: iter 206 fires
    # (each group is partial-overlap), but the intersection cardinality
    # varies. This matcher REJECTS.
    patterns = {"pair_analyses": [
        _analysis(groups=[
            _group(input_colors=[1, 2], output_colors=[2, 3]),
            _group(input_colors=[4, 5, 6], output_colors=[5, 6, 7]),
        ]),
    ]}
    iter206 = CONDITION_REGISTRY[
        "output_colors_partial_overlap_with_input_colors_per_group"
    ]
    assert iter206(patterns, {}) is True
    assert _matcher()(patterns, {}) is False


def test_co_fires_with_iter206_when_intersection_size_constant() -> None:
    # Per-group partial-overlap with CONSTANT |ic ∩ oc| == 1 across
    # every group. Both iter 206 AND this matcher fire.
    patterns = {"pair_analyses": [
        _analysis(groups=[
            _group(input_colors=[1, 2], output_colors=[2, 3]),
            _group(input_colors=[4, 5], output_colors=[5, 6]),
        ]),
    ]}
    iter206 = CONDITION_REGISTRY[
        "output_colors_partial_overlap_with_input_colors_per_group"
    ]
    assert iter206(patterns, {}) is True
    assert _matcher()(patterns, {}) is True


def test_independent_of_iter44_whole_grid_intersection() -> None:
    # Whole-grid |A ∩ B| constant across pairs (iter 44) but per-group
    # |ic ∩ oc| varies within a pair: iter 44 fires; this matcher
    # REJECTS. Demonstrates the per-group projection is decoupled from
    # the whole-grid projection on the within-pair direction.
    patterns = {"pair_analyses": [
        _analysis(
            groups=[
                _group(input_colors=[1, 2], output_colors=[2, 3]),
                _group(input_colors=[1, 2], output_colors=[3, 4]),
            ],
            input_palette=[1, 2],
            output_palette=[2, 3, 4],
        ),
        _analysis(
            groups=[
                _group(input_colors=[1, 2], output_colors=[2, 3]),
                _group(input_colors=[1, 2], output_colors=[3, 4]),
            ],
            input_palette=[1, 2],
            output_palette=[2, 3, 4],
        ),
    ]}
    iter44 = CONDITION_REGISTRY["palette_intersection_count_constant_across_pairs"]
    assert iter44(patterns, {}) is True  # whole-grid |∩| == 1 on both
    assert _matcher()(patterns, {}) is False  # per-group |∩| varies


def test_independent_of_iter195_when_intersection_size_varies() -> None:
    # Per-group |ic| constant (iter 195 fires) but |ic ∩ oc| varies.
    patterns = {"pair_analyses": [
        _analysis(groups=[
            _group(input_colors=[1, 2], output_colors=[2, 3]),
            _group(input_colors=[4, 5], output_colors=[6, 7]),
        ]),
    ]}
    iter195 = CONDITION_REGISTRY[
        "change_input_color_count_per_group_constant_across_pairs"
    ]
    assert iter195(patterns, {}) is True  # |ic| == 2 on every group
    assert _matcher()(patterns, {}) is False  # |∩| varies (1, 0)


def test_co_fires_with_iter195_when_both_axes_constant() -> None:
    # Per-group |ic| == 2 AND per-group |∩| == 1 on every group.
    patterns = {"pair_analyses": [
        _analysis(groups=[
            _group(input_colors=[1, 2], output_colors=[2, 3]),
            _group(input_colors=[4, 5], output_colors=[5, 6]),
        ]),
    ]}
    iter195 = CONDITION_REGISTRY[
        "change_input_color_count_per_group_constant_across_pairs"
    ]
    assert iter195(patterns, {}) is True
    assert _matcher()(patterns, {}) is True


def test_independent_of_iter14_with_singleton_input_and_mixed_intersection() -> None:
    # Iter 14 (input_color_uniform) pins per-group |ic| == 1 + same
    # colour. With ic == {c}, |ic ∩ oc| ∈ {0, 1}. Mixed (group 0:
    # 1 ∈ oc; group 1: 1 not ∈ oc) ⇒ iter 14 fires, this matcher
    # rejects.
    patterns = {"pair_analyses": [
        _analysis(groups=[
            _group(input_colors=[1], output_colors=[1, 2]),
            _group(input_colors=[1], output_colors=[3, 4]),
        ]),
    ]}
    iter14 = CONDITION_REGISTRY["input_color_uniform"]
    assert iter14(patterns, {}) is True
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

def test_recognized_conditions_includes_matcher_on_constant_K_partial_overlap() -> None:
    from agent.conditions import recognized_conditions
    patterns = {
        "pair_analyses": [
            _analysis(groups=[
                _group(input_colors=[1, 2], output_colors=[2, 3]),
                _group(input_colors=[4, 5], output_colors=[5, 6]),
            ]),
        ],
    }
    fired = recognized_conditions(patterns)
    assert MATCHER_NAME in fired, (
        f"{MATCHER_NAME!r} did not fire on per-group constant |∩|==1; "
        f"got {fired!r}"
    )


def test_recognized_conditions_excludes_on_varying_intersection_size() -> None:
    from agent.conditions import recognized_conditions
    patterns = {
        "pair_analyses": [
            _analysis(groups=[
                _group(input_colors=[1, 2], output_colors=[2, 3]),
                _group(input_colors=[4, 5, 6], output_colors=[5, 6, 7]),
            ]),
        ],
    }
    fired = recognized_conditions(patterns)
    assert MATCHER_NAME not in fired, (
        f"{MATCHER_NAME!r} must NOT fire on per-group |∩|-varying "
        f"patterns; got {fired!r}"
    )


def test_recognized_conditions_includes_on_per_group_disjoint_K_zero() -> None:
    # On the per-group disjoint cell (iter 203 fires), this matcher
    # MUST fire with K == 0 (strict implication).
    from agent.conditions import recognized_conditions
    patterns = {
        "pair_analyses": [
            _analysis(groups=[_group(input_colors=[1, 2], output_colors=[3, 4])]),
        ],
    }
    fired = recognized_conditions(patterns)
    assert "output_colors_disjoint_from_input_colors_per_group" in fired
    assert MATCHER_NAME in fired, (
        "strict implication: iter 203 fires ⇒ this matcher must fire"
    )


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
