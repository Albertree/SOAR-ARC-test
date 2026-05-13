"""
tests/test_change_count_constant_across_pairs.py -- exercise the
iter-32 matcher ``agent.conditions.change_count_constant_across_pairs``.

Runs without pytest:

    python tests/test_change_count_constant_across_pairs.py

Dependency-free, same runner style as iters
1 / 8 / 10 / 13 / 17 / 18 / 19 / 20 / 22 / 23 / 24 / 26 / 28 / 30.

The matcher is on a new axis (change-cardinality): it names "the total
number of changed cells (summed across all groups in a pair) is
bit-identical across every pair". Strictly weaker than iter 30's
``change_positions_constant_across_pairs`` (positions-constant ⟹
count-constant, but not the converse). Names the recognition
precondition for any future rule whose action affects a constant
number of cells via a position-DERIVING predicate.
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


MATCHER_NAME = "change_count_constant_across_pairs"


def _matcher():
    return CONDITION_REGISTRY[MATCHER_NAME]


def _group(*, positions, in_colors=(0,), out_colors=(3,)):
    """Build a group analysis dict matching ``_analyze_pair``'s emit shape.

    Positions are accepted for parity with iter 30's test fixtures so the
    co-fire tests below can reuse the same building blocks, but this
    matcher inspects only ``cell_count`` -- positions are not required.
    """
    sorted_positions = sorted(tuple(p) for p in positions)
    if sorted_positions:
        top_row = min(r for r, _ in sorted_positions)
        top_col = min(c for _, c in sorted_positions)
    else:
        top_row = 0
        top_col = 0
    return {
        "input_colors": list(in_colors),
        "output_colors": list(out_colors),
        "top_row": top_row,
        "top_col": top_col,
        "cell_count": len(sorted_positions),
        "positions": sorted_positions,
    }


def _analysis(*, groups, input_height=3, input_width=3,
              output_height=None, output_width=None, size_match=None):
    if output_height is None:
        output_height = input_height
    if output_width is None:
        output_width = input_width
    if size_match is None:
        size_match = (input_height == output_height
                      and input_width == output_width)
    return {
        "total_changes": sum(g.get("cell_count", 0) for g in groups),
        "num_groups": len(groups),
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
    # Adjacent invariant -- iter 32 must not displace iters
    # 1 / 8 / 10 / 13 / 17 / 18 / 19 / 20 / 22 / 23 / 24 / 26 / 28 / 30.
    for prior in ("grid_size_preserved", "consistent_color_mapping",
                  "sequential_recoloring", "identity_transformation",
                  "grid_size_changed", "output_color_uniform",
                  "input_color_uniform", "output_dimensions_constant",
                  "input_dimensions_constant",
                  "single_change_group_per_pair",
                  "single_cell_change_per_pair",
                  "multi_cell_change_group_per_pair",
                  "multi_group_per_pair",
                  "change_positions_constant_across_pairs"):
        assert prior in CONDITION_REGISTRY, (
            f"prior matcher {prior!r} missing after iter-32 addition"
        )


def test_at_least_fifteen_distinct_matchers_registered() -> None:
    # P5 unit-monotone counter -- iter 32 lifts the count from 14 to 15.
    assert len(CONDITION_REGISTRY) >= 15, (
        f"expected at least 15 entries, got {len(CONDITION_REGISTRY)}: "
        f"{sorted(CONDITION_REGISTRY)}"
    )


def test_matcher_is_callable() -> None:
    fn = _matcher()
    assert callable(fn), f"registered entry is not callable: {fn!r}"


def test_returns_true_on_single_pair_single_cell() -> None:
    patterns = {"pair_analyses": [
        _analysis(groups=[_group(positions=[(1, 1)])]),
    ]}
    assert _matcher()(patterns, {}) is True


def test_returns_true_on_two_pairs_same_total_same_positions() -> None:
    # Iter 25 / 27 / 29 happy-path territory: positions match too.
    # Co-firing with iter 30 is verified explicitly below.
    patterns = {"pair_analyses": [
        _analysis(groups=[_group(positions=[(0, 0)])]),
        _analysis(groups=[_group(positions=[(0, 0)])]),
    ]}
    assert _matcher()(patterns, {}) is True


def test_returns_true_on_two_pairs_same_total_different_positions() -> None:
    # The territory iter 30 does NOT cover but this matcher does:
    # pair 0 changes (0, 0), pair 1 changes (2, 2). Both have count
    # 1, but positions differ. This matcher fires; iter 30 does not.
    patterns = {"pair_analyses": [
        _analysis(groups=[_group(positions=[(0, 0)])]),
        _analysis(groups=[_group(positions=[(2, 2)])]),
    ]}
    assert _matcher()(patterns, {}) is True
    iter30 = CONDITION_REGISTRY["change_positions_constant_across_pairs"]
    assert iter30(patterns, {}) is False, (
        "iter 30 should not fire when positions differ -- "
        "the territory iter 32 covers exclusively"
    )


def test_returns_true_when_group_partition_differs_but_total_matches() -> None:
    # Pair 0: two single-cell blobs (total 2). Pair 1: one two-cell blob
    # (total 2). Group counts differ (2 vs 1), but total matches.
    # iter 23 ('single_change_group_per_pair') does NOT fire on pair 0;
    # iter 28 ('multi_group_per_pair') does NOT fire on pair 1; this
    # matcher fires on both.
    patterns = {"pair_analyses": [
        _analysis(groups=[
            _group(positions=[(0, 0)]),
            _group(positions=[(1, 1)]),
        ]),
        _analysis(groups=[_group(positions=[(2, 2), (2, 3)])]),
    ]}
    assert _matcher()(patterns, {}) is True
    iter23 = CONDITION_REGISTRY["single_change_group_per_pair"]
    iter28 = CONDITION_REGISTRY["multi_group_per_pair"]
    assert iter23(patterns, {}) is False, (
        "iter 23 requires num_groups == 1 on every pair"
    )
    assert iter28(patterns, {}) is False, (
        "iter 28 requires num_groups >= 2 on every pair"
    )


def test_returns_true_on_multi_blob_constant_total() -> None:
    # Two pairs, each with two blobs summing to 3 cells; positions vary.
    patterns = {"pair_analyses": [
        _analysis(groups=[
            _group(positions=[(0, 0), (0, 1)]),
            _group(positions=[(2, 2)]),
        ]),
        _analysis(groups=[
            _group(positions=[(1, 0)]),
            _group(positions=[(2, 1), (2, 2)]),
        ]),
    ]}
    assert _matcher()(patterns, {}) is True


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
    # Identity case: per-pair total is 0. The matcher rejects
    # vacuously-true matches to keep its territory disjoint from
    # iter 13's identity_transformation.
    patterns = {"pair_analyses": [
        _analysis(groups=[]),
        _analysis(groups=[]),
    ]}
    assert _matcher()(patterns, {}) is False


def test_returns_false_when_one_pair_has_no_changes() -> None:
    # Pair 0 has total 1; pair 1 has total 0 (no groups). Strict reject.
    patterns = {"pair_analyses": [
        _analysis(groups=[_group(positions=[(0, 0)])]),
        _analysis(groups=[]),
    ]}
    assert _matcher()(patterns, {}) is False


def test_returns_false_when_totals_differ_across_pairs() -> None:
    # Pair 0: total 1. Pair 1: total 2. Distinct totals -- reject.
    patterns = {"pair_analyses": [
        _analysis(groups=[_group(positions=[(0, 0)])]),
        _analysis(groups=[_group(positions=[(0, 0), (0, 1)])]),
    ]}
    assert _matcher()(patterns, {}) is False


def test_returns_false_when_totals_differ_via_multi_blob() -> None:
    # Pair 0: two blobs (1 + 1 = 2). Pair 1: two blobs (2 + 1 = 3).
    patterns = {"pair_analyses": [
        _analysis(groups=[
            _group(positions=[(0, 0)]),
            _group(positions=[(2, 2)]),
        ]),
        _analysis(groups=[
            _group(positions=[(0, 0), (0, 1)]),
            _group(positions=[(2, 2)]),
        ]),
    ]}
    assert _matcher()(patterns, {}) is False


def test_returns_false_on_missing_cell_count() -> None:
    group_bad = {
        "input_colors": [0], "output_colors": [3],
        "top_row": 0, "top_col": 0,
        # cell_count intentionally missing
        "positions": [(0, 0)],
    }
    patterns = {"pair_analyses": [_analysis(groups=[group_bad])]}
    assert _matcher()(patterns, {}) is False


def test_returns_false_on_bool_cell_count() -> None:
    # Bool is an int subclass. Strict-type matchers (iters 13 / 17 /
    # 18 / 19 / 20 / 22 / 23 / 24 / 26 / 28 / 30 and validate_rule V1)
    # reject it. Mirror posture.
    for bad in (True, False):
        group_bad = {
            "input_colors": [0], "output_colors": [3],
            "top_row": 0, "top_col": 0, "cell_count": bad,
            "positions": [(0, 0)],
        }
        patterns = {"pair_analyses": [_analysis(groups=[group_bad])]}
        assert _matcher()(patterns, {}) is False, (
            f"cell_count={bad!r} (bool) should fail-closed"
        )


def test_returns_false_on_zero_cell_count() -> None:
    group_bad = {
        "input_colors": [0], "output_colors": [3],
        "top_row": 0, "top_col": 0, "cell_count": 0,
        "positions": [],
    }
    patterns = {"pair_analyses": [_analysis(groups=[group_bad])]}
    assert _matcher()(patterns, {}) is False


def test_returns_false_on_negative_cell_count() -> None:
    group_bad = {
        "input_colors": [0], "output_colors": [3],
        "top_row": 0, "top_col": 0, "cell_count": -1,
        "positions": [],
    }
    patterns = {"pair_analyses": [_analysis(groups=[group_bad])]}
    assert _matcher()(patterns, {}) is False


def test_returns_false_on_non_int_cell_count() -> None:
    # Bypass _analysis (which would crash on non-int cell_count when it
    # computes total_changes) by hand-rolling the pair_analysis dict.
    for bad in (0.5, "1", None, [1]):
        group_bad = {
            "input_colors": [0], "output_colors": [3],
            "top_row": 0, "top_col": 0, "cell_count": bad,
            "positions": [(0, 0)],
        }
        analysis = {
            "num_groups": 1,
            "groups": [group_bad],
            "size_match": True,
            "input_height": 3, "input_width": 3,
            "output_height": 3, "output_width": 3,
        }
        patterns = {"pair_analyses": [analysis]}
        assert _matcher()(patterns, {}) is False, (
            f"cell_count={bad!r} ({type(bad).__name__}) should fail-closed"
        )


def test_returns_false_on_non_list_groups() -> None:
    analysis = _analysis(groups=[_group(positions=[(0, 0)])])
    analysis["groups"] = "not a list"
    patterns = {"pair_analyses": [analysis]}
    assert _matcher()(patterns, {}) is False


def test_returns_false_on_non_dict_group_entry() -> None:
    analysis = _analysis(groups=[_group(positions=[(0, 0)])])
    analysis["groups"] = ["not a dict"]
    patterns = {"pair_analyses": [analysis]}
    assert _matcher()(patterns, {}) is False


def test_is_side_effect_free_on_inputs() -> None:
    patterns = {"pair_analyses": [
        _analysis(groups=[_group(positions=[(0, 0), (0, 1)])]),
        _analysis(groups=[_group(positions=[(1, 0), (1, 1)])]),
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


# ----- mutual-exclusion / refinement-chain tests --------------------

def test_mutually_exclusive_with_identity_transformation() -> None:
    # identity requires num_groups == 0 (total 0); this matcher rejects
    # total-zero. No patterns dict can fire both.
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


def test_iter_30_refinement_one_direction() -> None:
    # iter 30 (positions-constant) IMPLIES iter 32 (count-constant).
    # Any patterns that fires iter 30 must also fire this matcher.
    patterns = {"pair_analyses": [
        _analysis(groups=[_group(positions=[(0, 0), (0, 1), (1, 0)])]),
        _analysis(groups=[_group(positions=[(0, 0), (0, 1), (1, 0)])]),
    ]}
    iter30 = CONDITION_REGISTRY["change_positions_constant_across_pairs"]
    assert iter30(patterns, {}) is True
    assert _matcher()(patterns, {}) is True


def test_iter_30_refinement_strict() -> None:
    # The converse does NOT hold: a patterns dict can fire this matcher
    # (count-constant) without firing iter 30 (positions-constant).
    # Pair 0 changes (0,0); pair 1 changes (1,1). Both totals are 1.
    patterns = {"pair_analyses": [
        _analysis(groups=[_group(positions=[(0, 0)])]),
        _analysis(groups=[_group(positions=[(1, 1)])]),
    ]}
    iter30 = CONDITION_REGISTRY["change_positions_constant_across_pairs"]
    assert _matcher()(patterns, {}) is True
    assert iter30(patterns, {}) is False


# ----- co-fire tests ------------------------------------------------

def test_can_co_fire_with_single_cell_change_per_pair() -> None:
    # Both single-cell pairs trivially have total 1. Even when positions
    # differ, this matcher fires alongside iter 24.
    patterns = {"pair_analyses": [
        _analysis(groups=[_group(positions=[(0, 1)])]),
        _analysis(groups=[_group(positions=[(2, 2)])]),
    ]}
    iter24 = CONDITION_REGISTRY["single_cell_change_per_pair"]
    assert iter24(patterns, {}) is True
    assert _matcher()(patterns, {}) is True


def test_can_co_fire_with_multi_cell_change_group_per_pair() -> None:
    # Both pairs have a single blob of 3 cells -- iter 26 fires; total
    # is 3 on both -- this matcher fires.
    patterns = {"pair_analyses": [
        _analysis(groups=[_group(positions=[(0, 0), (0, 1), (1, 0)])]),
        _analysis(groups=[_group(positions=[(1, 1), (1, 2), (2, 1)])]),
    ]}
    iter26 = CONDITION_REGISTRY["multi_cell_change_group_per_pair"]
    assert iter26(patterns, {}) is True
    assert _matcher()(patterns, {}) is True


def test_can_co_fire_with_multi_group_per_pair() -> None:
    # Both pairs have two single-cell blobs (total 2) at different
    # positions. iter 28 fires; this matcher fires.
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


def test_can_co_fire_with_single_change_group_per_pair() -> None:
    # Both pairs have one group of the same cell count.
    patterns = {"pair_analyses": [
        _analysis(groups=[_group(positions=[(0, 0), (0, 1)])]),
        _analysis(groups=[_group(positions=[(1, 1), (2, 2)])]),
    ]}
    iter23 = CONDITION_REGISTRY["single_change_group_per_pair"]
    assert iter23(patterns, {}) is True
    assert _matcher()(patterns, {}) is True


def test_can_co_fire_with_output_color_uniform() -> None:
    # Cardinality axis is orthogonal to the colour-content axis.
    patterns = {"pair_analyses": [
        _analysis(groups=[_group(positions=[(0, 0)], out_colors=(7,))]),
        _analysis(groups=[_group(positions=[(2, 2)], out_colors=(7,))]),
    ]}
    ocu = CONDITION_REGISTRY["output_color_uniform"]
    assert ocu(patterns, {}) is True
    assert _matcher()(patterns, {}) is True


def test_can_co_fire_with_input_color_uniform() -> None:
    patterns = {"pair_analyses": [
        _analysis(groups=[_group(positions=[(0, 0)],
                                 in_colors=(2,), out_colors=(3,))]),
        _analysis(groups=[_group(positions=[(1, 1)],
                                 in_colors=(2,), out_colors=(4,))]),
    ]}
    icu = CONDITION_REGISTRY["input_color_uniform"]
    assert icu(patterns, {}) is True
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
    # Cardinality matcher cares only about per-pair total cell counts.
    # It CAN fire on dimension-changed pairs.
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
    # The shape ExtractPatternOperator._analyze_pair emits on two
    # 3x3 grids each with a single-cell change at distinct positions.
    # iter 30 should reject (positions differ); iter 32 should fire
    # (totals both 1).
    from agent.active_operators import ExtractPatternOperator  # noqa: E402

    op = ExtractPatternOperator()

    class _Grid:
        def __init__(self, raw):
            self.raw = raw
            self.height = len(raw)
            self.width = len(raw[0]) if raw else 0

    raw_in = [[0, 0, 0], [0, 0, 0], [0, 0, 0]]
    raw_out_a = [[3, 0, 0], [0, 0, 0], [0, 0, 0]]   # changes (0, 0)
    raw_out_b = [[0, 0, 0], [0, 0, 0], [0, 0, 3]]   # changes (2, 2)
    analysis_a = op._analyze_pair(_Grid(raw_in), _Grid(raw_out_a))
    analysis_b = op._analyze_pair(_Grid(raw_in), _Grid(raw_out_b))
    patterns = {"pair_analyses": [analysis_a, analysis_b]}
    iter30 = CONDITION_REGISTRY["change_positions_constant_across_pairs"]
    assert iter30(patterns, {}) is False
    assert _matcher()(patterns, {}) is True


def test_end_to_end_disagreement_when_totals_differ() -> None:
    # Two pairs change different counts of cells -- both matchers reject.
    from agent.active_operators import ExtractPatternOperator  # noqa: E402

    op = ExtractPatternOperator()

    class _Grid:
        def __init__(self, raw):
            self.raw = raw
            self.height = len(raw)
            self.width = len(raw[0]) if raw else 0

    raw_in = [[0, 0, 0], [0, 0, 0], [0, 0, 0]]
    raw_out_a = [[3, 0, 0], [0, 0, 0], [0, 0, 0]]   # 1 change
    raw_out_b = [[3, 3, 0], [0, 0, 0], [0, 0, 0]]   # 2 changes
    analysis_a = op._analyze_pair(_Grid(raw_in), _Grid(raw_out_a))
    analysis_b = op._analyze_pair(_Grid(raw_in), _Grid(raw_out_b))
    patterns = {"pair_analyses": [analysis_a, analysis_b]}
    assert _matcher()(patterns, {}) is False


def test_returned_value_is_boolean_not_truthy() -> None:
    pos_pat = {"pair_analyses": [
        _analysis(groups=[_group(positions=[(1, 1)])]),
        _analysis(groups=[_group(positions=[(2, 2)])]),
    ]}
    neg_pat = {"pair_analyses": [
        _analysis(groups=[_group(positions=[(0, 0)])]),
        _analysis(groups=[_group(positions=[(0, 0), (0, 1)])]),
    ]}
    pos = _matcher()(pos_pat, {})
    neg = _matcher()(neg_pat, {})
    assert pos is True, f"expected literal True, got {pos!r}"
    assert neg is False, f"expected literal False, got {neg!r}"


# ----------------------------------------------------------------------
# Driver.
# ----------------------------------------------------------------------

def _run_all() -> int:
    tests = [
        test_registered_in_global_registry,
        test_previous_matchers_still_registered,
        test_at_least_fifteen_distinct_matchers_registered,
        test_matcher_is_callable,
        test_returns_true_on_single_pair_single_cell,
        test_returns_true_on_two_pairs_same_total_same_positions,
        test_returns_true_on_two_pairs_same_total_different_positions,
        test_returns_true_when_group_partition_differs_but_total_matches,
        test_returns_true_on_multi_blob_constant_total,
        test_returns_false_on_empty_pair_analyses,
        test_returns_false_on_missing_pair_analyses,
        test_returns_false_on_non_dict_patterns,
        test_returns_false_on_non_list_pair_analyses,
        test_returns_false_on_malformed_analysis_entry,
        test_returns_false_when_every_pair_has_zero_groups,
        test_returns_false_when_one_pair_has_no_changes,
        test_returns_false_when_totals_differ_across_pairs,
        test_returns_false_when_totals_differ_via_multi_blob,
        test_returns_false_on_missing_cell_count,
        test_returns_false_on_bool_cell_count,
        test_returns_false_on_zero_cell_count,
        test_returns_false_on_negative_cell_count,
        test_returns_false_on_non_int_cell_count,
        test_returns_false_on_non_list_groups,
        test_returns_false_on_non_dict_group_entry,
        test_is_side_effect_free_on_inputs,
        test_is_deterministic_across_repeats,
        test_mutually_exclusive_with_identity_transformation,
        test_iter_30_refinement_one_direction,
        test_iter_30_refinement_strict,
        test_can_co_fire_with_single_cell_change_per_pair,
        test_can_co_fire_with_multi_cell_change_group_per_pair,
        test_can_co_fire_with_multi_group_per_pair,
        test_can_co_fire_with_single_change_group_per_pair,
        test_can_co_fire_with_output_color_uniform,
        test_can_co_fire_with_input_color_uniform,
        test_can_co_fire_with_grid_size_preserved,
        test_does_not_require_grid_size_preserved,
        test_end_to_end_agreement_with_extract_pattern_shape,
        test_end_to_end_disagreement_when_totals_differ,
        test_returned_value_is_boolean_not_truthy,
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
    n = _run_all()
    sys.exit(1 if n else 0)
