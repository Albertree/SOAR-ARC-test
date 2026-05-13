"""
tests/test_output_color_uniform.py -- exercise the iter-18 matcher
``agent.conditions.output_color_uniform``.

Runs without pytest:

    python tests/test_output_color_uniform.py

Dependency-free, same runner style as iters 1 / 8 / 10 / 13 / 17.
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


MATCHER_NAME = "output_color_uniform"


def _matcher():
    return CONDITION_REGISTRY[MATCHER_NAME]


def _group(in_colors, out_colors, top_row=0, top_col=0, cell_count=1):
    return {
        "input_colors": list(in_colors),
        "output_colors": list(out_colors),
        "top_row": top_row,
        "top_col": top_col,
        "cell_count": cell_count,
    }


def _uniform_paint_red_pair() -> dict:
    """Every change group paints output colour 3 ("red"), regardless of
    the input colour. Shape that ExtractPatternOperator._analyze_pair
    would emit for such a pair."""
    return {
        "total_changes": 2,
        "num_groups": 2,
        "groups": [
            _group([0], [3], 0, 0),
            _group([5], [3], 1, 0),
        ],
        "size_match": True,
    }


def _mixed_output_pair() -> dict:
    """Two distinct output colours -- 1:1 mapping, but NOT uniform."""
    return {
        "total_changes": 2,
        "num_groups": 2,
        "groups": [
            _group([0], [3], 0, 0),
            _group([5], [7], 1, 0),
        ],
        "size_match": True,
    }


def _identity_pair() -> dict:
    """Zero change groups -- identity territory. output_color_uniform
    must fail-closed (vacuously-true is wrong; identity has its own
    matcher)."""
    return {
        "total_changes": 0,
        "num_groups": 0,
        "groups": [],
        "size_match": True,
    }


# ──────────────────────────────────────────────────────────────────────────
# Tests.
# ──────────────────────────────────────────────────────────────────────────

def test_registered_in_global_registry() -> None:
    assert MATCHER_NAME in CONDITION_REGISTRY, (
        f"{MATCHER_NAME!r} not registered; got {sorted(CONDITION_REGISTRY)}"
    )


def test_previous_matchers_still_registered() -> None:
    # Adjacent invariant -- iter 18 must not displace iters 1 / 8 / 10 /
    # 13 / 17.
    for prior in ("grid_size_preserved", "consistent_color_mapping",
                  "sequential_recoloring", "identity_transformation",
                  "grid_size_changed"):
        assert prior in CONDITION_REGISTRY, (
            f"prior matcher {prior!r} missing after iter-18 addition"
        )


def test_six_distinct_matchers_registered() -> None:
    # P5 unit-monotone counter -- there must be at least 6 entries now.
    assert len(CONDITION_REGISTRY) >= 6, (
        f"expected at least 6 entries, got {len(CONDITION_REGISTRY)}: "
        f"{sorted(CONDITION_REGISTRY)}"
    )


def test_matcher_is_callable() -> None:
    fn = _matcher()
    assert callable(fn), f"registered entry is not callable: {fn!r}"


def test_returns_true_on_single_pair_uniform_paint() -> None:
    patterns = {"pair_analyses": [_uniform_paint_red_pair()]}
    assert _matcher()(patterns, {}) is True


def test_returns_true_on_multi_pair_uniform_paint() -> None:
    patterns = {"pair_analyses": [_uniform_paint_red_pair(),
                                  _uniform_paint_red_pair()]}
    assert _matcher()(patterns, {}) is True


def test_returns_true_for_single_group_per_pair() -> None:
    # The simplest uniform-paint case: each pair has one group, all
    # producing the same single output colour.
    patterns = {"pair_analyses": [
        {"size_match": True, "num_groups": 1,
         "groups": [_group([0], [4])]},
        {"size_match": True, "num_groups": 1,
         "groups": [_group([1], [4])]},
    ]}
    assert _matcher()(patterns, {}) is True


def test_fires_when_multiple_input_colors_collapse_to_one_output() -> None:
    # Definitive case of the iter-18 refinement: the iter-8 matcher
    # (consistent_color_mapping) would fire here too, but iter-18
    # additionally asserts that the OUTPUT side collapses to one
    # constant. Schema-wise the args become {"color": 7}, not a map.
    patterns = {"pair_analyses": [
        {"size_match": True, "num_groups": 3,
         "groups": [_group([0], [7]), _group([1], [7]), _group([2], [7])]},
        {"size_match": True, "num_groups": 3,
         "groups": [_group([0], [7]), _group([1], [7]), _group([2], [7])]},
    ]}
    assert _matcher()(patterns, {}) is True


def test_returns_false_on_two_distinct_output_colors_within_a_pair() -> None:
    patterns = {"pair_analyses": [_mixed_output_pair()]}
    assert _matcher()(patterns, {}) is False


def test_returns_false_when_output_color_differs_across_pairs() -> None:
    # Each pair has SOME single output colour, but pair 0 paints 3 and
    # pair 1 paints 7. NOT a uniform paint -- "paint with red" would not
    # be a valid generalisation.
    patterns = {"pair_analyses": [
        {"size_match": True, "num_groups": 1,
         "groups": [_group([0], [3])]},
        {"size_match": True, "num_groups": 1,
         "groups": [_group([0], [7])]},
    ]}
    assert _matcher()(patterns, {}) is False


def test_returns_false_on_zero_change_groups_per_pair() -> None:
    # Identity territory -- iter-13 matcher's job. Failing closed here
    # keeps the two matchers strictly mutually exclusive.
    patterns = {"pair_analyses": [_identity_pair(), _identity_pair()]}
    assert _matcher()(patterns, {}) is False


def test_returns_false_when_any_pair_has_zero_groups() -> None:
    # Even if one pair has a uniform paint and another has zero groups,
    # we cannot generalise -- the zero-group pair provides no evidence,
    # so we fail-closed.
    patterns = {"pair_analyses": [_uniform_paint_red_pair(),
                                  _identity_pair()]}
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


def test_returns_false_when_groups_field_missing() -> None:
    analysis_missing = {"size_match": True, "num_groups": 1}
    assert _matcher()({"pair_analyses": [analysis_missing]}, {}) is False


def test_returns_false_when_groups_field_not_list() -> None:
    analysis_bad = {"size_match": True, "num_groups": 1, "groups": "oops"}
    assert _matcher()({"pair_analyses": [analysis_bad]}, {}) is False


def test_returns_false_on_malformed_group_entry() -> None:
    analysis_bad = {"size_match": True, "num_groups": 1,
                    "groups": [None]}
    assert _matcher()({"pair_analyses": [analysis_bad]}, {}) is False


def test_returns_false_on_missing_output_colors_in_group() -> None:
    group_missing = {"input_colors": [0], "top_row": 0, "top_col": 0}
    analysis = {"size_match": True, "num_groups": 1,
                "groups": [group_missing]}
    assert _matcher()({"pair_analyses": [analysis]}, {}) is False


def test_returns_false_on_non_list_output_colors() -> None:
    group_bad = {"input_colors": [0], "output_colors": 3,
                 "top_row": 0, "top_col": 0}
    analysis = {"size_match": True, "num_groups": 1,
                "groups": [group_bad]}
    assert _matcher()({"pair_analyses": [analysis]}, {}) is False


def test_returns_false_on_multi_output_colors_in_group() -> None:
    # A single group emitting two distinct output colours is a contract
    # violation for "uniform" -- even if the cross-pair set would still
    # have cardinality one in some degenerate way.
    group_bad = {"input_colors": [0], "output_colors": [3, 5],
                 "top_row": 0, "top_col": 0}
    analysis = {"size_match": True, "num_groups": 1,
                "groups": [group_bad]}
    assert _matcher()({"pair_analyses": [analysis]}, {}) is False


def test_returns_false_on_empty_output_colors() -> None:
    # An empty output_colors list is missing data, not "uniform with
    # zero choices". Fail-closed.
    group_bad = {"input_colors": [0], "output_colors": [],
                 "top_row": 0, "top_col": 0}
    analysis = {"size_match": True, "num_groups": 1,
                "groups": [group_bad]}
    assert _matcher()({"pair_analyses": [analysis]}, {}) is False


def test_is_side_effect_free_on_inputs() -> None:
    patterns = {"pair_analyses": [_uniform_paint_red_pair(),
                                  _uniform_paint_red_pair()]}
    params = {"unused": 1}
    before_p = copy.deepcopy(patterns)
    before_q = copy.deepcopy(params)
    _matcher()(patterns, params)
    assert patterns == before_p, "matcher mutated patterns"
    assert params == before_q, "matcher mutated params"


def test_is_deterministic_across_repeats() -> None:
    patterns = {"pair_analyses": [_uniform_paint_red_pair(),
                                  _uniform_paint_red_pair()]}
    results = [_matcher()(patterns, {}) for _ in range(5)]
    assert len(set(results)) == 1, f"non-deterministic outputs: {results}"


def test_mutually_exclusive_with_identity_transformation() -> None:
    # identity_transformation requires zero change groups per pair;
    # output_color_uniform requires at least one group per pair.
    identity_patterns = {
        "grid_size_preserved": True,
        "pair_analyses": [_identity_pair(), _identity_pair()],
    }
    uniform_patterns = {
        "grid_size_preserved": True,
        "pair_analyses": [_uniform_paint_red_pair(),
                          _uniform_paint_red_pair()],
    }
    identity = CONDITION_REGISTRY["identity_transformation"]

    assert _matcher()(identity_patterns, {}) is False
    assert identity(identity_patterns, {}) is True

    assert _matcher()(uniform_patterns, {}) is True
    assert identity(uniform_patterns, {}) is False


def test_mutually_exclusive_with_sequential_recoloring() -> None:
    # sequential_recoloring requires the per-pair output colours to form
    # a contiguous integer range with cardinality >= 2. A uniform paint
    # has cardinality exactly 1, so the two are mutually exclusive on
    # any non-empty groups list.
    uniform_patterns = {
        "grid_size_preserved": True,
        "pair_analyses": [_uniform_paint_red_pair(),
                          _uniform_paint_red_pair()],
    }
    seq = CONDITION_REGISTRY["sequential_recoloring"]
    assert _matcher()(uniform_patterns, {}) is True
    assert seq(uniform_patterns, {}) is False, (
        "sequential_recoloring requires >=2 distinct contiguous outputs; "
        "a uniform paint must not fire it"
    )


def test_implies_consistent_color_mapping_when_input_groups_separate() -> None:
    # When each group has a single input colour and a single output
    # colour shared across all groups, the per-input mapping is still a
    # well-defined function (it just happens to be constant). Both
    # matchers fire -- output_color_uniform is a strict refinement.
    patterns = {
        "grid_size_preserved": True,
        "pair_analyses": [_uniform_paint_red_pair(),
                          _uniform_paint_red_pair()],
    }
    ccm = CONDITION_REGISTRY["consistent_color_mapping"]
    assert _matcher()(patterns, {}) is True
    assert ccm(patterns, {}) is True, (
        "every input colour maps to the same single output colour; "
        "consistent_color_mapping must still fire"
    )


def test_orthogonal_to_dimensional_axis() -> None:
    # output_color_uniform inspects change-group output colours, not
    # dimensions. A uniform paint where every pair has size_match=False
    # (e.g. tiling output is bigger, but the overlap region's change
    # groups all paint colour 3) must still fire this matcher --
    # orthogonal to grid_size_changed.
    patterns = {
        "grid_size_preserved": False,
        "pair_analyses": [
            {"size_match": False, "num_groups": 1,
             "groups": [_group([0], [3])]},
            {"size_match": False, "num_groups": 1,
             "groups": [_group([1], [3])]},
        ],
    }
    gsc = CONDITION_REGISTRY["grid_size_changed"]
    assert _matcher()(patterns, {}) is True, (
        "matcher must be dimension-agnostic"
    )
    assert gsc(patterns, {}) is True, (
        "grid_size_changed must still fire on the same patterns dict"
    )


def test_end_to_end_agreement_with_extract_pattern_shape() -> None:
    # The shape ExtractPatternOperator._analyze_pair emits for a
    # uniform-paint pair: sorted single-element input_colors and
    # output_colors lists per group. Sanity-check that the matcher
    # accepts the exact shape (not a fixture-only shape).
    patterns = {
        "grid_size_preserved": True,
        "pair_analyses": [
            {
                "total_changes": 2,
                "num_groups": 2,
                "groups": [
                    {"input_colors": [0], "output_colors": [4],
                     "top_row": 0, "top_col": 0, "cell_count": 1},
                    {"input_colors": [1], "output_colors": [4],
                     "top_row": 2, "top_col": 3, "cell_count": 1},
                ],
                "size_match": True,
            },
        ],
    }
    assert _matcher()(patterns, {}) is True


def test_returned_value_is_boolean_not_truthy() -> None:
    # Mirrors the strict-`is True` contract from recognized_conditions:
    # downstream consumers filter on `match(...) is True` exactly.
    pos = _matcher()({"pair_analyses": [_uniform_paint_red_pair()]}, {})
    neg = _matcher()({"pair_analyses": [_mixed_output_pair()]}, {})
    assert pos is True, f"expected literal True, got {pos!r}"
    assert neg is False, f"expected literal False, got {neg!r}"


# ──────────────────────────────────────────────────────────────────────────
# Driver.
# ──────────────────────────────────────────────────────────────────────────

def _run_all() -> int:
    tests = [
        test_registered_in_global_registry,
        test_previous_matchers_still_registered,
        test_six_distinct_matchers_registered,
        test_matcher_is_callable,
        test_returns_true_on_single_pair_uniform_paint,
        test_returns_true_on_multi_pair_uniform_paint,
        test_returns_true_for_single_group_per_pair,
        test_fires_when_multiple_input_colors_collapse_to_one_output,
        test_returns_false_on_two_distinct_output_colors_within_a_pair,
        test_returns_false_when_output_color_differs_across_pairs,
        test_returns_false_on_zero_change_groups_per_pair,
        test_returns_false_when_any_pair_has_zero_groups,
        test_returns_false_on_empty_pair_analyses,
        test_returns_false_on_missing_pair_analyses,
        test_returns_false_on_non_dict_patterns,
        test_returns_false_on_non_list_pair_analyses,
        test_returns_false_on_malformed_analysis_entry,
        test_returns_false_when_groups_field_missing,
        test_returns_false_when_groups_field_not_list,
        test_returns_false_on_malformed_group_entry,
        test_returns_false_on_missing_output_colors_in_group,
        test_returns_false_on_non_list_output_colors,
        test_returns_false_on_multi_output_colors_in_group,
        test_returns_false_on_empty_output_colors,
        test_is_side_effect_free_on_inputs,
        test_is_deterministic_across_repeats,
        test_mutually_exclusive_with_identity_transformation,
        test_mutually_exclusive_with_sequential_recoloring,
        test_implies_consistent_color_mapping_when_input_groups_separate,
        test_orthogonal_to_dimensional_axis,
        test_end_to_end_agreement_with_extract_pattern_shape,
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
