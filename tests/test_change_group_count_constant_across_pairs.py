"""
tests/test_change_group_count_constant_across_pairs.py -- exercise the
iter-39 matcher
``agent.conditions.change_group_count_constant_across_pairs``.

Runs without pytest:

    python tests/test_change_group_count_constant_across_pairs.py

Dependency-free, same runner style as iters
1 / 8 / 10 / 13 / 17 / 18 / 19 / 20 / 22 / 23 / 24 / 26 / 28 / 30 / 32
/ 33 / 34 / 35 / 36 / 37 / 38.

The matcher names the cross-pair cardinality projection of the
per-pair group-count axis (iters 23 / 28): every example pair has
the SAME non-zero ``num_groups`` value, regardless of which specific
cells those groups occupy. Strictly weaker than iter 23 (N == 1
pinned). Independent of iter 28 (which only requires N >= 2 per
pair, with no cross-pair constancy).
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


MATCHER_NAME = "change_group_count_constant_across_pairs"


def _matcher():
    return CONDITION_REGISTRY[MATCHER_NAME]


def _group(*, positions, in_colors=(0,), out_colors=(3,)):
    """Build a group analysis dict matching ``_analyze_pair``'s emit shape."""
    sorted_positions = sorted(tuple(p) for p in positions)
    if sorted_positions:
        top_row = min(r for r, _ in sorted_positions)
        top_col = min(c for _, c in sorted_positions)
    else:
        top_row = 0
        top_col = 0
    return {
        "input_colors": sorted(set(in_colors)),
        "output_colors": sorted(set(out_colors)),
        "top_row": top_row,
        "top_col": top_col,
        "cell_count": len(sorted_positions),
        "positions": sorted_positions,
    }


def _analysis(*, groups, input_height=3, input_width=3,
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


# ----------------------------------------------------------------------
# Tests.
# ----------------------------------------------------------------------

def test_registered_in_global_registry() -> None:
    assert MATCHER_NAME in CONDITION_REGISTRY, (
        f"{MATCHER_NAME!r} not registered; got {sorted(CONDITION_REGISTRY)}"
    )


def test_previous_matchers_still_registered() -> None:
    # Adjacent invariant -- iter 39 must not displace iters
    # 1 / 8 / 10 / 13 / 17 / 18 / 19 / 20 / 22 / 23 / 24 / 26 / 28 / 30
    # / 32 / 33 / 34 / 35 / 36 / 37 / 38.
    for prior in ("grid_size_preserved", "consistent_color_mapping",
                  "sequential_recoloring", "identity_transformation",
                  "grid_size_changed", "output_color_uniform",
                  "input_color_uniform", "output_dimensions_constant",
                  "input_dimensions_constant",
                  "single_change_group_per_pair",
                  "single_cell_change_per_pair",
                  "multi_cell_change_group_per_pair",
                  "multi_group_per_pair",
                  "change_positions_constant_across_pairs",
                  "change_count_constant_across_pairs",
                  "output_dimensions_multiple_of_input",
                  "change_colors_constant_across_pairs",
                  "change_input_colors_constant_across_pairs",
                  "change_output_colors_constant_across_pairs",
                  "change_input_color_count_constant_across_pairs",
                  "change_output_color_count_constant_across_pairs"):
        assert prior in CONDITION_REGISTRY, (
            f"prior matcher {prior!r} missing after iter-39 addition"
        )


def test_at_least_twentytwo_distinct_matchers_registered() -> None:
    # P5 unit-monotone counter -- iter 39 lifts the count from 21 to 22.
    assert len(CONDITION_REGISTRY) >= 22, (
        f"expected at least 22 entries, got {len(CONDITION_REGISTRY)}: "
        f"{sorted(CONDITION_REGISTRY)}"
    )


def test_matcher_is_callable() -> None:
    fn = _matcher()
    assert callable(fn), f"registered entry is not callable: {fn!r}"


def test_returns_true_on_single_pair_single_group() -> None:
    patterns = {"pair_analyses": [
        _analysis(groups=[_group(positions=[(1, 1)])]),
    ]}
    assert _matcher()(patterns, {}) is True


def test_returns_true_on_two_pairs_same_n_equals_one() -> None:
    # Both pairs have exactly 1 group -- the iter 23 territory.
    # iter 23 fires; this matcher fires (by refinement).
    patterns = {"pair_analyses": [
        _analysis(groups=[_group(positions=[(0, 0)])]),
        _analysis(groups=[_group(positions=[(2, 2)])]),
    ]}
    iter23 = CONDITION_REGISTRY["single_change_group_per_pair"]
    assert iter23(patterns, {}) is True
    assert _matcher()(patterns, {}) is True


def test_returns_true_on_two_pairs_same_n_equals_two() -> None:
    # Both pairs have exactly 2 groups -- iter 28 fires; this matcher
    # fires (constant cardinality, value 2).
    patterns = {"pair_analyses": [
        _analysis(groups=[
            _group(positions=[(0, 0)]),
            _group(positions=[(2, 2)]),
        ]),
        _analysis(groups=[
            _group(positions=[(1, 1)]),
            _group(positions=[(0, 2)]),
        ]),
    ]}
    iter28 = CONDITION_REGISTRY["multi_group_per_pair"]
    assert iter28(patterns, {}) is True
    assert _matcher()(patterns, {}) is True


def test_returns_true_on_three_pairs_same_n() -> None:
    # Three pairs, each with two groups. Cardinality 2 constant.
    patterns = {"pair_analyses": [
        _analysis(groups=[
            _group(positions=[(0, 0)]),
            _group(positions=[(2, 2)]),
        ]),
        _analysis(groups=[
            _group(positions=[(1, 0)]),
            _group(positions=[(0, 2)]),
        ]),
        _analysis(groups=[
            _group(positions=[(1, 1)]),
            _group(positions=[(2, 0)]),
        ]),
    ]}
    assert _matcher()(patterns, {}) is True


def test_returns_false_when_group_counts_differ() -> None:
    # Pair 0 has 1 group; pair 1 has 2 groups. Cardinalities differ.
    patterns = {"pair_analyses": [
        _analysis(groups=[_group(positions=[(0, 0)])]),
        _analysis(groups=[
            _group(positions=[(0, 0)]),
            _group(positions=[(2, 2)]),
        ]),
    ]}
    assert _matcher()(patterns, {}) is False


def test_returns_false_on_iter_28_pattern_with_varying_n() -> None:
    # The territory iter 28 covers but this matcher does NOT: every pair
    # has num_groups >= 2 but the specific count varies (2 vs 3).
    patterns = {"pair_analyses": [
        _analysis(groups=[
            _group(positions=[(0, 0)]),
            _group(positions=[(2, 2)]),
        ]),
        _analysis(groups=[
            _group(positions=[(0, 0)]),
            _group(positions=[(0, 2)]),
            _group(positions=[(2, 1)]),
        ]),
    ]}
    iter28 = CONDITION_REGISTRY["multi_group_per_pair"]
    assert iter28(patterns, {}) is True, (
        "iter 28 should fire: every pair has num_groups >= 2"
    )
    assert _matcher()(patterns, {}) is False, (
        "iter 39 should reject: per-pair cardinalities 2 vs 3 differ"
    )


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


def test_returns_false_when_every_pair_has_zero_groups() -> None:
    # Identity case: per-pair num_groups is 0. The matcher rejects
    # vacuously-zero matches to keep its territory disjoint from
    # iter 13's identity_transformation.
    patterns = {"pair_analyses": [
        _analysis(groups=[]),
        _analysis(groups=[]),
    ]}
    assert _matcher()(patterns, {}) is False


def test_returns_false_when_one_pair_has_zero_groups() -> None:
    # Pair 0 has num_groups=1; pair 1 has num_groups=0. The all-zero
    # rejection is unconditional on each pair, not just the union --
    # any pair with num_groups < 1 forces a False.
    patterns = {"pair_analyses": [
        _analysis(groups=[_group(positions=[(0, 0)])]),
        _analysis(groups=[]),
    ]}
    assert _matcher()(patterns, {}) is False


def test_returns_false_on_missing_num_groups() -> None:
    analysis_bad = {
        "groups": [_group(positions=[(0, 0)])],
        "size_match": True,
        "input_height": 3, "input_width": 3,
        "output_height": 3, "output_width": 3,
        # num_groups intentionally missing
    }
    assert _matcher()({"pair_analyses": [analysis_bad]}, {}) is False


def test_returns_false_on_bool_num_groups() -> None:
    # Bool is an int subclass. Strict-type matchers reject it.
    for bad in (True, False):
        analysis_bad = {
            "groups": [_group(positions=[(0, 0)])],
            "size_match": True,
            "input_height": 3, "input_width": 3,
            "output_height": 3, "output_width": 3,
            "num_groups": bad,
        }
        assert _matcher()({"pair_analyses": [analysis_bad]}, {}) is False, (
            f"num_groups={bad!r} (bool) should fail-closed"
        )


def test_returns_false_on_negative_num_groups() -> None:
    analysis_bad = {
        "groups": [],
        "size_match": True,
        "input_height": 3, "input_width": 3,
        "output_height": 3, "output_width": 3,
        "num_groups": -1,
    }
    assert _matcher()({"pair_analyses": [analysis_bad]}, {}) is False


def test_returns_false_on_non_int_num_groups() -> None:
    for bad in (0.5, "1", None, [1]):
        analysis_bad = {
            "groups": [_group(positions=[(0, 0)])],
            "size_match": True,
            "input_height": 3, "input_width": 3,
            "output_height": 3, "output_width": 3,
            "num_groups": bad,
        }
        assert _matcher()({"pair_analyses": [analysis_bad]}, {}) is False, (
            f"num_groups={bad!r} ({type(bad).__name__}) should fail-closed"
        )


def test_is_side_effect_free_on_inputs() -> None:
    patterns = {"pair_analyses": [
        _analysis(groups=[
            _group(positions=[(0, 0)]),
            _group(positions=[(2, 2)]),
        ]),
        _analysis(groups=[
            _group(positions=[(1, 1)]),
            _group(positions=[(0, 2)]),
        ]),
    ]}
    params = {"unused": 1}
    before_p = copy.deepcopy(patterns)
    before_q = copy.deepcopy(params)
    _matcher()(patterns, params)
    assert patterns == before_p, "matcher mutated patterns"
    assert params == before_q, "matcher mutated params"


def test_is_deterministic_across_repeats() -> None:
    patterns = {"pair_analyses": [
        _analysis(groups=[_group(positions=[(1, 1)])]),
        _analysis(groups=[_group(positions=[(2, 2)])]),
    ]}
    results = [_matcher()(patterns, {}) for _ in range(5)]
    assert len(set(results)) == 1, f"non-deterministic outputs: {results}"


def test_returns_strict_boolean_type() -> None:
    pos_pat = {"pair_analyses": [
        _analysis(groups=[_group(positions=[(1, 1)])]),
        _analysis(groups=[_group(positions=[(2, 2)])]),
    ]}
    neg_pat = {"pair_analyses": [
        _analysis(groups=[_group(positions=[(0, 0)])]),
        _analysis(groups=[
            _group(positions=[(0, 0)]),
            _group(positions=[(2, 2)]),
        ]),
    ]}
    pos = _matcher()(pos_pat, {})
    neg = _matcher()(neg_pat, {})
    assert pos is True, f"expected literal True, got {pos!r}"
    assert neg is False, f"expected literal False, got {neg!r}"


# ----- mutual-exclusion / refinement-chain tests --------------------

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
            _analysis(groups=[_group(positions=[(1, 1)])]),
            _analysis(groups=[_group(positions=[(2, 2)])]),
        ],
    }
    identity = CONDITION_REGISTRY["identity_transformation"]
    assert identity(identity_pat, {}) is True
    assert _matcher()(identity_pat, {}) is False
    assert identity(paint_pat, {}) is False
    assert _matcher()(paint_pat, {}) is True


def test_iter_23_refinement_implication_holds() -> None:
    # iter 23 (single_change_group_per_pair, N == 1 per pair) IMPLIES
    # this matcher: any patterns dict where every pair has num_groups
    # exactly 1 has constant cardinality (== 1) across pairs.
    patterns = {"pair_analyses": [
        _analysis(groups=[_group(positions=[(0, 0)])]),
        _analysis(groups=[_group(positions=[(2, 2)])]),
        _analysis(groups=[_group(positions=[(1, 1)])]),
    ]}
    iter23 = CONDITION_REGISTRY["single_change_group_per_pair"]
    assert iter23(patterns, {}) is True
    assert _matcher()(patterns, {}) is True


def test_iter_23_refinement_strict_one_direction() -> None:
    # The converse does NOT hold: a patterns dict can fire this matcher
    # (constant N == 2) without firing iter 23 (which requires N == 1).
    patterns = {"pair_analyses": [
        _analysis(groups=[
            _group(positions=[(0, 0)]),
            _group(positions=[(2, 2)]),
        ]),
        _analysis(groups=[
            _group(positions=[(1, 1)]),
            _group(positions=[(0, 2)]),
        ]),
    ]}
    iter23 = CONDITION_REGISTRY["single_change_group_per_pair"]
    assert _matcher()(patterns, {}) is True
    assert iter23(patterns, {}) is False


def test_iter_28_independence_iter_39_fires_alone() -> None:
    # iter 39 fires alone when every pair has the same N == 1 (iter 28
    # requires N >= 2, so iter 28 rejects).
    patterns = {"pair_analyses": [
        _analysis(groups=[_group(positions=[(0, 0)])]),
        _analysis(groups=[_group(positions=[(2, 2)])]),
    ]}
    iter28 = CONDITION_REGISTRY["multi_group_per_pair"]
    assert _matcher()(patterns, {}) is True
    assert iter28(patterns, {}) is False


def test_iter_28_independence_iter_28_fires_alone() -> None:
    # iter 28 fires alone when num_groups varies but each pair has
    # num_groups >= 2 (this matcher rejects on the variance).
    patterns = {"pair_analyses": [
        _analysis(groups=[
            _group(positions=[(0, 0)]),
            _group(positions=[(2, 2)]),
        ]),
        _analysis(groups=[
            _group(positions=[(0, 0)]),
            _group(positions=[(0, 2)]),
            _group(positions=[(2, 2)]),
        ]),
    ]}
    iter28 = CONDITION_REGISTRY["multi_group_per_pair"]
    assert iter28(patterns, {}) is True
    assert _matcher()(patterns, {}) is False


def test_iter_30_refinement_implication_holds() -> None:
    # iter 30 (positions-constant) IMPLIES this matcher: bit-identical
    # per-pair coord sets ⟹ bit-identical connected-component partition
    # ⟹ same num_groups across pairs.
    patterns = {"pair_analyses": [
        _analysis(groups=[_group(positions=[(0, 0), (0, 1), (1, 0)])]),
        _analysis(groups=[_group(positions=[(0, 0), (0, 1), (1, 0)])]),
    ]}
    iter30 = CONDITION_REGISTRY["change_positions_constant_across_pairs"]
    assert iter30(patterns, {}) is True
    assert _matcher()(patterns, {}) is True


def test_iter_30_refinement_strict_one_direction() -> None:
    # The converse does NOT hold: same group count with different
    # coords. Pair 0 changes (0, 0); pair 1 changes (2, 2). Both have
    # num_groups == 1, but positions differ.
    patterns = {"pair_analyses": [
        _analysis(groups=[_group(positions=[(0, 0)])]),
        _analysis(groups=[_group(positions=[(2, 2)])]),
    ]}
    iter30 = CONDITION_REGISTRY["change_positions_constant_across_pairs"]
    assert _matcher()(patterns, {}) is True
    assert iter30(patterns, {}) is False


def test_independent_of_change_count_constant_iter_39_fires_alone() -> None:
    # iter 39 fires when group counts are constant but cell counts
    # differ. Pair 0 has one 1-cell blob; pair 1 has one 2-cell blob.
    # Both have num_groups == 1, but total cell counts 1 vs 2.
    patterns = {"pair_analyses": [
        _analysis(groups=[_group(positions=[(0, 0)])]),
        _analysis(groups=[_group(positions=[(2, 2), (2, 3)])]),
    ]}
    iter32 = CONDITION_REGISTRY["change_count_constant_across_pairs"]
    assert _matcher()(patterns, {}) is True
    assert iter32(patterns, {}) is False


def test_independent_of_change_count_constant_iter_32_fires_alone() -> None:
    # iter 32 fires alone when total cell counts are equal but group
    # counts differ. Pair 0 has two 1-cell blobs (total 2, num_groups
    # 2); pair 1 has one 2-cell blob (total 2, num_groups 1).
    patterns = {"pair_analyses": [
        _analysis(groups=[
            _group(positions=[(0, 0)]),
            _group(positions=[(2, 2)]),
        ]),
        _analysis(groups=[_group(positions=[(0, 0), (0, 1)])]),
    ]}
    iter32 = CONDITION_REGISTRY["change_count_constant_across_pairs"]
    assert iter32(patterns, {}) is True
    assert _matcher()(patterns, {}) is False


# ----- co-fire tests ------------------------------------------------

def test_can_co_fire_with_single_cell_change_per_pair() -> None:
    # Both single-cell pairs trivially have num_groups == 1.
    patterns = {"pair_analyses": [
        _analysis(groups=[_group(positions=[(0, 1)])]),
        _analysis(groups=[_group(positions=[(2, 2)])]),
    ]}
    iter24 = CONDITION_REGISTRY["single_cell_change_per_pair"]
    assert iter24(patterns, {}) is True
    assert _matcher()(patterns, {}) is True


def test_can_co_fire_with_multi_cell_change_group_per_pair() -> None:
    # Both pairs have a single blob of 3 cells -- iter 26 fires;
    # num_groups == 1 on both -- this matcher fires.
    patterns = {"pair_analyses": [
        _analysis(groups=[_group(positions=[(0, 0), (0, 1), (1, 0)])]),
        _analysis(groups=[_group(positions=[(1, 1), (1, 2), (2, 1)])]),
    ]}
    iter26 = CONDITION_REGISTRY["multi_cell_change_group_per_pair"]
    assert iter26(patterns, {}) is True
    assert _matcher()(patterns, {}) is True


def test_can_co_fire_with_sequential_recoloring() -> None:
    # Two pairs, each with three groups producing a contiguous output
    # range. iter 10 fires; this matcher fires (constant N == 3).
    patterns = {"pair_analyses": [
        _analysis(groups=[
            _group(positions=[(0, 0)], in_colors=(0,), out_colors=(3,)),
            _group(positions=[(1, 0)], in_colors=(1,), out_colors=(4,)),
            _group(positions=[(2, 0)], in_colors=(2,), out_colors=(5,)),
        ]),
        _analysis(groups=[
            _group(positions=[(0, 0)], in_colors=(0,), out_colors=(3,)),
            _group(positions=[(1, 0)], in_colors=(1,), out_colors=(4,)),
            _group(positions=[(2, 0)], in_colors=(2,), out_colors=(5,)),
        ]),
    ]}
    iter10 = CONDITION_REGISTRY["sequential_recoloring"]
    assert iter10(patterns, {}) is True
    assert _matcher()(patterns, {}) is True


def test_can_co_fire_with_output_color_uniform() -> None:
    # Group-count axis is orthogonal to the colour-content axis.
    patterns = {"pair_analyses": [
        _analysis(groups=[_group(positions=[(0, 0)], out_colors=(7,))]),
        _analysis(groups=[_group(positions=[(2, 2)], out_colors=(7,))]),
    ]}
    ocu = CONDITION_REGISTRY["output_color_uniform"]
    assert ocu(patterns, {}) is True
    assert _matcher()(patterns, {}) is True


def test_can_co_fire_with_grid_size_preserved() -> None:
    patterns = {
        "grid_size_preserved": True,
        "pair_analyses": [
            _analysis(groups=[_group(positions=[(1, 1)])]),
            _analysis(groups=[_group(positions=[(2, 2)])]),
        ],
    }
    gsp = CONDITION_REGISTRY["grid_size_preserved"]
    assert _matcher()(patterns, {}) is True
    assert gsp(patterns, {}) is True


def test_does_not_require_grid_size_preserved() -> None:
    # Selection-shape cardinality matcher cares only about per-pair
    # num_groups. It CAN fire on dimension-changed pairs.
    patterns = {"pair_analyses": [
        _analysis(groups=[_group(positions=[(0, 0)])],
                  output_height=5, output_width=5, size_match=False),
        _analysis(groups=[_group(positions=[(2, 2)])],
                  output_height=5, output_width=5, size_match=False),
    ]}
    gsp = CONDITION_REGISTRY["grid_size_preserved"]
    assert _matcher()(patterns, {}) is True
    assert gsp(patterns, {}) is False


# ----- end-to-end with the real extractor --------------------------

def test_end_to_end_agreement_with_extract_pattern_shape() -> None:
    # Two 3x3 pairs: each pair changes one cell at distinct positions.
    # num_groups == 1 on both. iter 30 rejects (positions differ);
    # this matcher fires (constant N == 1).
    from agent.active_operators import ExtractPatternOperator  # noqa: E402

    op = ExtractPatternOperator()

    class _Grid:
        def __init__(self, raw):
            self.raw = raw
            self.height = len(raw)
            self.width = len(raw[0]) if raw else 0

    raw_in = [[0, 0, 0], [0, 0, 0], [0, 0, 0]]
    raw_out_a = [[3, 0, 0], [0, 0, 0], [0, 0, 0]]   # 1 change at (0, 0)
    raw_out_b = [[0, 0, 0], [0, 0, 0], [0, 0, 3]]   # 1 change at (2, 2)
    analysis_a = op._analyze_pair(_Grid(raw_in), _Grid(raw_out_a))
    analysis_b = op._analyze_pair(_Grid(raw_in), _Grid(raw_out_b))
    patterns = {"pair_analyses": [analysis_a, analysis_b]}
    iter30 = CONDITION_REGISTRY["change_positions_constant_across_pairs"]
    assert iter30(patterns, {}) is False
    assert _matcher()(patterns, {}) is True


def test_end_to_end_disagreement_when_n_differs() -> None:
    # Two pairs with different num_groups. This matcher rejects.
    from agent.active_operators import ExtractPatternOperator  # noqa: E402

    op = ExtractPatternOperator()

    class _Grid:
        def __init__(self, raw):
            self.raw = raw
            self.height = len(raw)
            self.width = len(raw[0]) if raw else 0

    raw_in = [[0, 0, 0], [0, 0, 0], [0, 0, 0]]
    raw_out_a = [[3, 0, 0], [0, 0, 0], [0, 0, 0]]    # 1 blob
    raw_out_b = [[3, 0, 0], [0, 0, 0], [0, 0, 3]]    # 2 disjoint blobs
    analysis_a = op._analyze_pair(_Grid(raw_in), _Grid(raw_out_a))
    analysis_b = op._analyze_pair(_Grid(raw_in), _Grid(raw_out_b))
    patterns = {"pair_analyses": [analysis_a, analysis_b]}
    assert _matcher()(patterns, {}) is False


# ----------------------------------------------------------------------
# Driver.
# ----------------------------------------------------------------------

def _run_all() -> int:
    tests = [
        test_registered_in_global_registry,
        test_previous_matchers_still_registered,
        test_at_least_twentytwo_distinct_matchers_registered,
        test_matcher_is_callable,
        test_returns_true_on_single_pair_single_group,
        test_returns_true_on_two_pairs_same_n_equals_one,
        test_returns_true_on_two_pairs_same_n_equals_two,
        test_returns_true_on_three_pairs_same_n,
        test_returns_false_when_group_counts_differ,
        test_returns_false_on_iter_28_pattern_with_varying_n,
        test_returns_false_on_empty_pair_analyses,
        test_returns_false_on_missing_pair_analyses,
        test_returns_false_on_non_dict_patterns,
        test_returns_false_on_non_list_pair_analyses,
        test_returns_false_on_malformed_analysis_entry,
        test_returns_false_when_every_pair_has_zero_groups,
        test_returns_false_when_one_pair_has_zero_groups,
        test_returns_false_on_missing_num_groups,
        test_returns_false_on_bool_num_groups,
        test_returns_false_on_negative_num_groups,
        test_returns_false_on_non_int_num_groups,
        test_is_side_effect_free_on_inputs,
        test_is_deterministic_across_repeats,
        test_returns_strict_boolean_type,
        test_mutually_exclusive_with_identity_transformation,
        test_iter_23_refinement_implication_holds,
        test_iter_23_refinement_strict_one_direction,
        test_iter_28_independence_iter_39_fires_alone,
        test_iter_28_independence_iter_28_fires_alone,
        test_iter_30_refinement_implication_holds,
        test_iter_30_refinement_strict_one_direction,
        test_independent_of_change_count_constant_iter_39_fires_alone,
        test_independent_of_change_count_constant_iter_32_fires_alone,
        test_can_co_fire_with_single_cell_change_per_pair,
        test_can_co_fire_with_multi_cell_change_group_per_pair,
        test_can_co_fire_with_sequential_recoloring,
        test_can_co_fire_with_output_color_uniform,
        test_can_co_fire_with_grid_size_preserved,
        test_does_not_require_grid_size_preserved,
        test_end_to_end_agreement_with_extract_pattern_shape,
        test_end_to_end_disagreement_when_n_differs,
    ]
    fails = 0
    for t in tests:
        try:
            t()
            print(f"  OK   {t.__name__}")
        except AssertionError as e:
            fails += 1
            print(f"  FAIL {t.__name__}: {e}")
        except Exception:
            fails += 1
            print(f"  FAIL {t.__name__}: unexpected exception")
            traceback.print_exc()
    return fails


if __name__ == "__main__":
    rc = _run_all()
    if rc == 0:
        print(f"\nall {MATCHER_NAME} tests passed.")
    else:
        print(f"\n{rc} test(s) failed.")
    sys.exit(0 if rc == 0 else 1)
