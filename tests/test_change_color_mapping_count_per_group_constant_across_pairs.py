"""
tests/test_change_color_mapping_count_per_group_constant_across_pairs.py
-- exercise the iter-197 matcher
``agent.conditions.change_color_mapping_count_per_group_constant_across_pairs``
(new in this iter).

Pins the matcher's contract per the module docstring: every change
group in every example pair has the SAME per-group product
``K = len(input_colors) * len(output_colors)``, where K is determined
by the first observed group. The matcher does not pin a specific K,
only the cross-pair / cross-group constancy of that single derived
integer; the COLOURS themselves are free, and the input / output
factor cardinalities may vary inversely as long as their product is
constant.

Sits on the per-group (ic, oc) Cartesian-product cardinality sub-axis
-- the per-group projection of iter 40 (``change_color_mapping_count_
constant_across_pairs``, per-pair (ic, oc) set cardinality under a
strict ``len == 1`` precondition). Strictly implied by iters 195 ∧
196 (per-group input cardinality constant AND per-group output
cardinality constant ⟹ per-group product constant), but not the
conjunction of those two (this matcher can fire with both factors
varying as long as their product is constant).

Runs without pytest:

    python tests/test_change_color_mapping_count_per_group_constant_across_pairs.py

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


MATCHER_NAME = "change_color_mapping_count_per_group_constant_across_pairs"


def _matcher():
    return CONDITION_REGISTRY[MATCHER_NAME]


def _group(*, input_colors=(0,), output_colors=(3,), positions=None):
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
              num_groups=None):
    if output_height is None:
        output_height = input_height
    if output_width is None:
        output_width = input_width
    if size_match is None:
        size_match = (input_height == output_height
                      and input_width == output_width)
    if num_groups is None:
        num_groups = len(groups)
    return {
        "total_changes": sum(g.get("cell_count", 0) for g in groups),
        "num_groups": num_groups,
        "groups": list(groups),
        "size_match": size_match,
        "input_height": input_height,
        "input_width": input_width,
        "output_height": output_height,
        "output_width": output_width,
    }


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
# Positive cases — constant per-group (ic, oc) product across groups/pairs.
# ──────────────────────────────────────────────────────────────────────────

def test_returns_true_on_single_pair_product_one() -> None:
    # K_in == 1, K_out == 1, product == 1.
    patterns = {"pair_analyses": [
        _analysis(groups=[_group(input_colors=[1], output_colors=[3])]),
    ]}
    assert _matcher()(patterns, {}) is True


def test_returns_true_on_two_pairs_product_one_same_colours() -> None:
    patterns = {"pair_analyses": [
        _analysis(groups=[_group(input_colors=[1], output_colors=[3])]),
        _analysis(groups=[_group(input_colors=[1], output_colors=[3])]),
    ]}
    assert _matcher()(patterns, {}) is True


def test_returns_true_on_two_pairs_product_one_different_colours() -> None:
    # Colours differ per pair but product == 1 on every group.
    patterns = {"pair_analyses": [
        _analysis(groups=[_group(input_colors=[1], output_colors=[3])]),
        _analysis(groups=[_group(input_colors=[2], output_colors=[5])]),
    ]}
    assert _matcher()(patterns, {}) is True


def test_returns_true_on_product_two_K_in_one_K_out_two() -> None:
    # K_in == 1, K_out == 2, product == 2 on every group.
    patterns = {"pair_analyses": [
        _analysis(groups=[_group(input_colors=[1], output_colors=[3, 4])]),
        _analysis(groups=[_group(input_colors=[2], output_colors=[5, 6])]),
    ]}
    assert _matcher()(patterns, {}) is True


def test_returns_true_on_product_two_K_in_two_K_out_one() -> None:
    # Symmetric: K_in == 2, K_out == 1, product == 2.
    patterns = {"pair_analyses": [
        _analysis(groups=[_group(input_colors=[1, 2], output_colors=[3])]),
        _analysis(groups=[_group(input_colors=[5, 6], output_colors=[7])]),
    ]}
    assert _matcher()(patterns, {}) is True


def test_returns_true_on_product_two_factor_inversion() -> None:
    # The KEY non-trivial case: per-group K_in varies (1 vs 2) AND
    # per-group K_out varies (2 vs 1), but K_in * K_out == 2 constant.
    # Iter 195 rejects (K_in varies); iter 196 rejects (K_out varies);
    # this matcher fires.
    patterns = {"pair_analyses": [
        _analysis(groups=[_group(input_colors=[1], output_colors=[3, 4])]),
        _analysis(groups=[_group(input_colors=[2, 5], output_colors=[6])]),
    ]}
    assert _matcher()(patterns, {}) is True


def test_returns_true_on_product_four_balanced() -> None:
    # K_in == 2, K_out == 2, product == 4.
    patterns = {"pair_analyses": [
        _analysis(groups=[_group(input_colors=[1, 2], output_colors=[3, 4])]),
        _analysis(groups=[_group(input_colors=[5, 6], output_colors=[7, 8])]),
    ]}
    assert _matcher()(patterns, {}) is True


def test_returns_true_on_multi_group_per_pair_constant_product() -> None:
    patterns = {"pair_analyses": [
        _analysis(groups=[
            _group(input_colors=[1], output_colors=[3]),
            _group(input_colors=[2], output_colors=[4]),
        ]),
        _analysis(groups=[
            _group(input_colors=[5], output_colors=[6]),
            _group(input_colors=[7], output_colors=[8]),
        ]),
    ]}
    assert _matcher()(patterns, {}) is True


def test_returns_true_on_varying_num_groups_constant_product() -> None:
    # Per-group product constancy does NOT require num_groups constancy.
    patterns = {"pair_analyses": [
        _analysis(groups=[_group(input_colors=[1], output_colors=[3])]),
        _analysis(groups=[
            _group(input_colors=[2], output_colors=[5]),
            _group(input_colors=[4], output_colors=[7]),
        ]),
        _analysis(groups=[
            _group(input_colors=[1], output_colors=[8]),
            _group(input_colors=[6], output_colors=[2]),
            _group(input_colors=[9], output_colors=[0]),
        ]),
    ]}
    assert _matcher()(patterns, {}) is True


# ──────────────────────────────────────────────────────────────────────────
# Negative cases.
# ──────────────────────────────────────────────────────────────────────────

def test_returns_false_when_product_varies_across_pairs() -> None:
    # Pair 0: product 1. Pair 1: product 2.
    patterns = {"pair_analyses": [
        _analysis(groups=[_group(input_colors=[1], output_colors=[3])]),
        _analysis(groups=[_group(input_colors=[2], output_colors=[5, 6])]),
    ]}
    assert _matcher()(patterns, {}) is False


def test_returns_false_when_product_varies_within_a_pair() -> None:
    # Pair 0 has two groups: product 1 and product 2.
    patterns = {"pair_analyses": [
        _analysis(groups=[
            _group(input_colors=[1], output_colors=[3]),
            _group(input_colors=[2], output_colors=[5, 6]),
        ]),
    ]}
    assert _matcher()(patterns, {}) is False


def test_returns_false_when_product_varies_in_later_pair() -> None:
    patterns = {"pair_analyses": [
        _analysis(groups=[
            _group(input_colors=[1], output_colors=[3]),
            _group(input_colors=[2], output_colors=[4]),
        ]),
        _analysis(groups=[
            _group(input_colors=[5], output_colors=[6]),
            _group(input_colors=[7], output_colors=[8, 9]),
        ]),
    ]}
    assert _matcher()(patterns, {}) is False


def test_returns_false_on_identity_all_zero_groups() -> None:
    patterns = {"pair_analyses": [
        _analysis(groups=[]),
        _analysis(groups=[]),
    ]}
    assert _matcher()(patterns, {}) is False


def test_returns_false_when_one_pair_has_zero_groups() -> None:
    patterns = {"pair_analyses": [
        _analysis(groups=[_group(input_colors=[1], output_colors=[3])]),
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
# Strict-type gates on ``groups`` / colour lists.
# ──────────────────────────────────────────────────────────────────────────

def test_returns_false_on_missing_groups_field() -> None:
    analysis_bad = {
        "size_match": True,
        "total_changes": 1,
        "num_groups": 1,
        "input_height": 3, "input_width": 3,
        "output_height": 3, "output_width": 3,
        # groups intentionally missing
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
        "output_colors": [3],
        "top_row": 0, "top_col": 0,
        "positions": [(0, 0)],
        "cell_count": 1,
        # input_colors intentionally missing
    }
    analysis_bad = _analysis(groups=[])
    analysis_bad["groups"] = [group_bad]
    assert _matcher()({"pair_analyses": [analysis_bad]}, {}) is False


def test_returns_false_on_missing_output_colors() -> None:
    group_bad = {
        "input_colors": [1],
        "top_row": 0, "top_col": 0,
        "positions": [(0, 0)],
        "cell_count": 1,
        # output_colors intentionally missing
    }
    analysis_bad = _analysis(groups=[])
    analysis_bad["groups"] = [group_bad]
    assert _matcher()({"pair_analyses": [analysis_bad]}, {}) is False


def test_returns_false_on_non_list_input_colors() -> None:
    for bad in (None, 1, "1", {1: 2}, (1,)):
        group_bad = {
            "input_colors": bad,
            "output_colors": [3],
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
            "input_colors": [1],
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
        "output_colors": [3],
        "top_row": 0, "top_col": 0,
        "positions": [(0, 0)],
        "cell_count": 1,
    }
    analysis_bad = _analysis(groups=[])
    analysis_bad["groups"] = [group_bad]
    assert _matcher()({"pair_analyses": [analysis_bad]}, {}) is False


def test_returns_false_on_empty_output_colors_list() -> None:
    group_bad = {
        "input_colors": [1],
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
            "input_colors": [bad],
            "output_colors": [3],
            "top_row": 0, "top_col": 0,
            "positions": [(0, 0)],
            "cell_count": 1,
        }
        analysis_bad = _analysis(groups=[])
        analysis_bad["groups"] = [group_bad]
        assert _matcher()({"pair_analyses": [analysis_bad]}, {}) is False, (
            f"input_colors=[{bad!r}] (bool) should fail-closed"
        )


def test_returns_false_on_bool_in_output_colors() -> None:
    for bad in (True, False):
        group_bad = {
            "input_colors": [1],
            "output_colors": [bad],
            "top_row": 0, "top_col": 0,
            "positions": [(0, 0)],
            "cell_count": 1,
        }
        analysis_bad = _analysis(groups=[])
        analysis_bad["groups"] = [group_bad]
        assert _matcher()({"pair_analyses": [analysis_bad]}, {}) is False, (
            f"output_colors=[{bad!r}] (bool) should fail-closed"
        )


def test_returns_false_on_out_of_range_colors() -> None:
    for bad in (-1, 10, 100):
        group_bad = {
            "input_colors": [bad],
            "output_colors": [3],
            "top_row": 0, "top_col": 0,
            "positions": [(0, 0)],
            "cell_count": 1,
        }
        analysis_bad = _analysis(groups=[])
        analysis_bad["groups"] = [group_bad]
        assert _matcher()({"pair_analyses": [analysis_bad]}, {}) is False, (
            f"input_colors=[{bad!r}] (out-of-range) should fail-closed"
        )
        group_bad = {
            "input_colors": [1],
            "output_colors": [bad],
            "top_row": 0, "top_col": 0,
            "positions": [(0, 0)],
            "cell_count": 1,
        }
        analysis_bad = _analysis(groups=[])
        analysis_bad["groups"] = [group_bad]
        assert _matcher()({"pair_analyses": [analysis_bad]}, {}) is False, (
            f"output_colors=[{bad!r}] (out-of-range) should fail-closed"
        )


def test_returns_false_on_non_int_colors() -> None:
    for bad in (0.5, "1", None, [1]):
        group_bad = {
            "input_colors": [bad],
            "output_colors": [3],
            "top_row": 0, "top_col": 0,
            "positions": [(0, 0)],
            "cell_count": 1,
        }
        analysis_bad = _analysis(groups=[])
        analysis_bad["groups"] = [group_bad]
        assert _matcher()({"pair_analyses": [analysis_bad]}, {}) is False, (
            f"input_colors=[{bad!r}] ({type(bad).__name__}) should fail-closed"
        )


def test_returns_false_on_second_pair_malformed() -> None:
    pair0 = _analysis(groups=[_group(input_colors=[1], output_colors=[3])])
    pair1_bad = _analysis(groups=[])
    pair1_bad["groups"] = ["not-a-dict"]
    assert _matcher()({"pair_analyses": [pair0, pair1_bad]}, {}) is False


# ──────────────────────────────────────────────────────────────────────────
# Behavioural contract: side-effect-free, deterministic, strict bool.
# ──────────────────────────────────────────────────────────────────────────

def test_is_side_effect_free_on_inputs() -> None:
    patterns = {"pair_analyses": [
        _analysis(groups=[
            _group(input_colors=[1, 2], output_colors=[3, 4]),
            _group(input_colors=[5, 6], output_colors=[7, 8]),
        ]),
        _analysis(groups=[_group(input_colors=[9, 0],
                                 output_colors=[1, 2])]),
    ]}
    params = {"unused": 1}
    before_p = copy.deepcopy(patterns)
    before_q = copy.deepcopy(params)
    _matcher()(patterns, params)
    assert patterns == before_p, "matcher mutated patterns"
    assert params == before_q, "matcher mutated params"


def test_is_deterministic_across_repeats() -> None:
    patterns = {"pair_analyses": [
        _analysis(groups=[_group(input_colors=[1], output_colors=[3, 4])]),
        _analysis(groups=[_group(input_colors=[2, 5], output_colors=[6])]),
    ]}
    results = [_matcher()(patterns, {}) for _ in range(5)]
    assert len(set(results)) == 1, f"non-deterministic outputs: {results}"


def test_returns_strict_boolean_type() -> None:
    pos_pat = {"pair_analyses": [
        _analysis(groups=[_group(input_colors=[1], output_colors=[3])]),
        _analysis(groups=[_group(input_colors=[2], output_colors=[5])]),
    ]}
    neg_pat = {"pair_analyses": [
        _analysis(groups=[_group(input_colors=[1], output_colors=[3])]),
        _analysis(groups=[_group(input_colors=[2], output_colors=[5, 6])]),
    ]}
    pos = _matcher()(pos_pat, {})
    neg = _matcher()(neg_pat, {})
    assert pos is True, f"expected literal True, got {pos!r}"
    assert neg is False, f"expected literal False, got {neg!r}"


def test_params_argument_ignored() -> None:
    patterns = {"pair_analyses": [
        _analysis(groups=[_group(input_colors=[1], output_colors=[3])]),
        _analysis(groups=[_group(input_colors=[2], output_colors=[5])]),
    ]}
    assert _matcher()(patterns, {}) is True
    assert _matcher()(patterns, {"target": 99}) is True
    assert _matcher()(patterns, {"K": 7, "junk": [1, 2]}) is True


# ──────────────────────────────────────────────────────────────────────────
# Orthogonality / refinement against neighbouring matchers.
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
            _analysis(groups=[_group(input_colors=[1], output_colors=[3])]),
            _analysis(groups=[_group(input_colors=[2], output_colors=[5])]),
        ],
    }
    identity = CONDITION_REGISTRY["identity_transformation"]
    assert identity(identity_pat, {}) is True
    assert _matcher()(identity_pat, {}) is False
    assert identity(paint_pat, {}) is False
    assert _matcher()(paint_pat, {}) is True


def test_iter_195_and_iter_196_implication_holds() -> None:
    # When iter 195 AND iter 196 both fire (per-group K_in constant AND
    # per-group K_out constant), this matcher fires (product of two
    # per-group constants is per-group constant).
    patterns = {"pair_analyses": [
        _analysis(groups=[_group(input_colors=[1, 2], output_colors=[3, 4])]),
        _analysis(groups=[_group(input_colors=[5, 6], output_colors=[7, 8])]),
    ]}
    iter195 = CONDITION_REGISTRY[
        "change_input_color_count_per_group_constant_across_pairs"
    ]
    iter196 = CONDITION_REGISTRY[
        "change_output_color_count_per_group_constant_across_pairs"
    ]
    assert iter195(patterns, {}) is True
    assert iter196(patterns, {}) is True
    assert _matcher()(patterns, {}) is True


def test_this_matcher_fires_while_iter_195_and_iter_196_reject() -> None:
    # The KEY case: K_in varies inversely with K_out so K_in * K_out
    # stays constant. Iter 195 rejects (K_in varies 1 -> 2); iter 196
    # rejects (K_out varies 2 -> 1); this matcher fires (product == 2).
    patterns = {"pair_analyses": [
        _analysis(groups=[_group(input_colors=[1], output_colors=[3, 4])]),
        _analysis(groups=[_group(input_colors=[2, 5], output_colors=[6])]),
    ]}
    iter195 = CONDITION_REGISTRY[
        "change_input_color_count_per_group_constant_across_pairs"
    ]
    iter196 = CONDITION_REGISTRY[
        "change_output_color_count_per_group_constant_across_pairs"
    ]
    assert iter195(patterns, {}) is False
    assert iter196(patterns, {}) is False
    assert _matcher()(patterns, {}) is True


def test_iter_195_fires_alone_when_K_in_constant_K_out_varies() -> None:
    # iter 195 fires (K_in == 1 everywhere); this matcher rejects
    # (product 1 vs 2 varies because K_out varies).
    patterns = {"pair_analyses": [
        _analysis(groups=[_group(input_colors=[1], output_colors=[3])]),
        _analysis(groups=[_group(input_colors=[2], output_colors=[5, 6])]),
    ]}
    iter195 = CONDITION_REGISTRY[
        "change_input_color_count_per_group_constant_across_pairs"
    ]
    assert iter195(patterns, {}) is True
    assert _matcher()(patterns, {}) is False


def test_iter_196_fires_alone_when_K_out_constant_K_in_varies() -> None:
    # iter 196 fires (K_out == 1 everywhere); this matcher rejects
    # (product 1 vs 2 varies because K_in varies).
    patterns = {"pair_analyses": [
        _analysis(groups=[_group(input_colors=[1], output_colors=[3])]),
        _analysis(groups=[_group(input_colors=[2, 5], output_colors=[6])]),
    ]}
    iter196 = CONDITION_REGISTRY[
        "change_output_color_count_per_group_constant_across_pairs"
    ]
    assert iter196(patterns, {}) is True
    assert _matcher()(patterns, {}) is False


def test_iter_40_implication_holds_under_len1_precondition() -> None:
    # iter 40 requires every group's len(input_colors) == 1 AND
    # len(output_colors) == 1. Under that precondition every group has
    # product 1, so this matcher fires with K == 1. This iter-40-fires
    # case is verified to also fire this matcher.
    patterns = {"pair_analyses": [
        _analysis(groups=[
            _group(input_colors=[1], output_colors=[3]),
            _group(input_colors=[2], output_colors=[4]),
        ]),
        _analysis(groups=[
            _group(input_colors=[5], output_colors=[6]),
            _group(input_colors=[7], output_colors=[8]),
        ]),
    ]}
    iter40 = CONDITION_REGISTRY[
        "change_color_mapping_count_constant_across_pairs"
    ]
    assert iter40(patterns, {}) is True
    assert _matcher()(patterns, {}) is True


def test_this_matcher_fires_alone_on_product_geq_2() -> None:
    # iter 40 requires len(input_colors) == 1 per group; with K_in == 2
    # everywhere iter 40 rejects, this matcher fires (product == 2).
    patterns = {"pair_analyses": [
        _analysis(groups=[_group(input_colors=[1, 2], output_colors=[3])]),
        _analysis(groups=[_group(input_colors=[5, 6], output_colors=[7])]),
    ]}
    iter40 = CONDITION_REGISTRY[
        "change_color_mapping_count_constant_across_pairs"
    ]
    assert iter40(patterns, {}) is False
    assert _matcher()(patterns, {}) is True


def test_iter_14_and_iter_18_jointly_imply_this_matcher() -> None:
    # iter 14 (input_color_uniform) pins K_in == 1 with identical
    # colour; iter 18 (output_color_uniform) pins K_out == 1 with
    # identical colour. Both together imply per-group product 1
    # constant.
    patterns = {"pair_analyses": [
        _analysis(groups=[_group(input_colors=[1], output_colors=[3])]),
        _analysis(groups=[_group(input_colors=[1], output_colors=[3])]),
    ]}
    iter14 = CONDITION_REGISTRY["input_color_uniform"]
    iter18 = CONDITION_REGISTRY["output_color_uniform"]
    assert iter14(patterns, {}) is True
    assert iter18(patterns, {}) is True
    assert _matcher()(patterns, {}) is True


def test_iter_193_independence_iter_193_alone() -> None:
    # iter 193 pins per-group cell_count constant; this matcher pins
    # per-group product constant. Per-group cell_count constant
    # (cell_count == 2 everywhere) but per-group product varies (1 vs 2):
    # iter 193 fires, this matcher rejects.
    patterns = {"pair_analyses": [
        _analysis(groups=[
            _group(input_colors=[1], output_colors=[3],
                   positions=[(0, 0), (0, 1)]),
            _group(input_colors=[5], output_colors=[7, 8],
                   positions=[(2, 0), (2, 1)]),
        ]),
    ]}
    iter193 = CONDITION_REGISTRY[
        "change_count_per_group_constant_across_pairs"
    ]
    assert iter193(patterns, {}) is True
    assert _matcher()(patterns, {}) is False


def test_iter_193_independence_this_matcher_alone() -> None:
    # Per-group product constant but per-group cell_count varies:
    # this matcher fires, iter 193 rejects.
    patterns = {"pair_analyses": [
        _analysis(groups=[_group(input_colors=[1], output_colors=[3],
                                 positions=[(0, 0)])]),
        _analysis(groups=[_group(input_colors=[2], output_colors=[5],
                                 positions=[(2, 0), (2, 1)])]),
    ]}
    iter193 = CONDITION_REGISTRY[
        "change_count_per_group_constant_across_pairs"
    ]
    assert iter193(patterns, {}) is False
    assert _matcher()(patterns, {}) is True


def test_co_fires_with_grid_size_preserved() -> None:
    patterns = {
        "grid_size_preserved": True,
        "pair_analyses": [
            _analysis(groups=[_group(input_colors=[1], output_colors=[3])]),
            _analysis(groups=[_group(input_colors=[2], output_colors=[5])]),
        ],
    }
    iter1 = CONDITION_REGISTRY["grid_size_preserved"]
    assert iter1(patterns, {}) is True
    assert _matcher()(patterns, {}) is True


# ──────────────────────────────────────────────────────────────────────────
# Recognized-conditions wiring.
# ──────────────────────────────────────────────────────────────────────────

def test_recognized_conditions_includes_matcher_on_constant_product() -> None:
    from agent.conditions import recognized_conditions
    patterns = {
        "pair_analyses": [
            _analysis(groups=[_group(input_colors=[1], output_colors=[3])]),
            _analysis(groups=[_group(input_colors=[2], output_colors=[5])]),
        ],
    }
    fired = recognized_conditions(patterns)
    assert MATCHER_NAME in fired, (
        f"{MATCHER_NAME!r} did not fire on constant-product patterns; "
        f"got {fired!r}"
    )


def test_recognized_conditions_excludes_on_varying_product() -> None:
    from agent.conditions import recognized_conditions
    patterns = {
        "pair_analyses": [
            _analysis(groups=[_group(input_colors=[1], output_colors=[3])]),
            _analysis(groups=[_group(input_colors=[2], output_colors=[5, 6])]),
        ],
    }
    fired = recognized_conditions(patterns)
    assert MATCHER_NAME not in fired, (
        f"{MATCHER_NAME!r} must NOT fire on varying-product patterns; "
        f"got {fired!r}"
    )


def test_recognized_conditions_co_fires_with_iter_40_on_len1_groups() -> None:
    # When every group has len(input_colors) == 1 AND len(output_colors)
    # == 1 AND per-pair (ic, oc) cardinality is constant, both iter 40
    # AND this matcher fire (with K == 1).
    from agent.conditions import recognized_conditions
    patterns = {
        "pair_analyses": [
            _analysis(groups=[
                _group(input_colors=[1], output_colors=[3]),
                _group(input_colors=[2], output_colors=[4]),
            ]),
            _analysis(groups=[
                _group(input_colors=[5], output_colors=[6]),
                _group(input_colors=[7], output_colors=[8]),
            ]),
        ],
    }
    fired = recognized_conditions(patterns)
    assert "change_color_mapping_count_constant_across_pairs" in fired
    assert MATCHER_NAME in fired


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
