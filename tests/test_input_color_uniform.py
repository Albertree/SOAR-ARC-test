"""
tests/test_input_color_uniform.py -- exercise the iter-19 matcher
``agent.conditions.input_color_uniform``.

Runs without pytest:

    python tests/test_input_color_uniform.py

Dependency-free, same runner style as iters 1 / 8 / 10 / 13 / 17 / 18.
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


MATCHER_NAME = "input_color_uniform"


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


def _uniform_input_pair() -> dict:
    """Every change group's input cells are colour 0 ("background to
    something"). Output colours vary by position. The shape
    ExtractPatternOperator._analyze_pair would emit for such a pair."""
    return {
        "total_changes": 2,
        "num_groups": 2,
        "groups": [
            _group([0], [3], 0, 0),
            _group([0], [5], 1, 0),
        ],
        "size_match": True,
    }


def _uniform_input_uniform_output_pair() -> dict:
    """Both input AND output collapse to a single colour each --
    the simplest "paint colour C cells with K" shape. Both
    input_color_uniform AND output_color_uniform fire."""
    return {
        "total_changes": 2,
        "num_groups": 2,
        "groups": [
            _group([0], [3], 0, 0),
            _group([0], [3], 1, 0),
        ],
        "size_match": True,
    }


def _mixed_input_pair() -> dict:
    """Two distinct input colours -- NOT uniform on the input side."""
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
    """Zero change groups -- identity territory. input_color_uniform
    must fail-closed (vacuously-true is wrong; identity has its own
    matcher)."""
    return {
        "total_changes": 0,
        "num_groups": 0,
        "groups": [],
        "size_match": True,
    }


# --------------------------------------------------------------------------
# Tests.
# --------------------------------------------------------------------------

def test_registered_in_global_registry() -> None:
    assert MATCHER_NAME in CONDITION_REGISTRY, (
        f"{MATCHER_NAME!r} not registered; got {sorted(CONDITION_REGISTRY)}"
    )


def test_previous_matchers_still_registered() -> None:
    # Adjacent invariant -- iter 19 must not displace iters 1 / 8 / 10 /
    # 13 / 17 / 18.
    for prior in ("grid_size_preserved", "consistent_color_mapping",
                  "sequential_recoloring", "identity_transformation",
                  "grid_size_changed", "output_color_uniform"):
        assert prior in CONDITION_REGISTRY, (
            f"prior matcher {prior!r} missing after iter-19 addition"
        )


def test_seven_distinct_matchers_registered() -> None:
    # P5 unit-monotone counter -- there must be at least 7 entries now.
    assert len(CONDITION_REGISTRY) >= 7, (
        f"expected at least 7 entries, got {len(CONDITION_REGISTRY)}: "
        f"{sorted(CONDITION_REGISTRY)}"
    )


def test_matcher_is_callable() -> None:
    fn = _matcher()
    assert callable(fn), f"registered entry is not callable: {fn!r}"


def test_returns_true_on_single_pair_uniform_input() -> None:
    patterns = {"pair_analyses": [_uniform_input_pair()]}
    assert _matcher()(patterns, {}) is True


def test_returns_true_on_multi_pair_uniform_input() -> None:
    patterns = {"pair_analyses": [_uniform_input_pair(),
                                  _uniform_input_pair()]}
    assert _matcher()(patterns, {}) is True


def test_returns_true_for_single_group_per_pair() -> None:
    # The simplest uniform-input case: each pair has one group, all
    # starting from the same single input colour.
    patterns = {"pair_analyses": [
        {"size_match": True, "num_groups": 1,
         "groups": [_group([0], [4])]},
        {"size_match": True, "num_groups": 1,
         "groups": [_group([0], [7])]},
    ]}
    assert _matcher()(patterns, {}) is True


def test_fires_when_uniform_input_maps_to_multiple_outputs() -> None:
    # Definitive iter-19 case that distinguishes input-side uniformity
    # from consistent_color_mapping: one input colour, multiple output
    # colours (e.g. recoloured by position). consistent_color_mapping
    # would fire if-and-only-if the per-cell mapping is a function;
    # here a single colour 0 maps to {3, 5} so it is NOT a function and
    # consistent_color_mapping must NOT fire. But input_color_uniform
    # should still fire -- the INPUT side is uniform.
    patterns = {"pair_analyses": [
        {"size_match": True, "num_groups": 3,
         "groups": [_group([0], [3]), _group([0], [4]), _group([0], [5])]},
        {"size_match": True, "num_groups": 3,
         "groups": [_group([0], [3]), _group([0], [4]), _group([0], [5])]},
    ]}
    assert _matcher()(patterns, {}) is True
    ccm = CONDITION_REGISTRY["consistent_color_mapping"]
    assert ccm(patterns, {}) is False, (
        "0 -> {3, 4, 5} is not a function; consistent_color_mapping must NOT fire"
    )


def test_returns_false_on_two_distinct_input_colors_within_a_pair() -> None:
    patterns = {"pair_analyses": [_mixed_input_pair()]}
    assert _matcher()(patterns, {}) is False


def test_returns_false_when_input_color_differs_across_pairs() -> None:
    # Each pair has SOME single input colour, but pair 0 paints OVER 0
    # and pair 1 paints OVER 5. NOT a uniform-input task --
    # "paint cells of colour 0" would not generalise to pair 1.
    patterns = {"pair_analyses": [
        {"size_match": True, "num_groups": 1,
         "groups": [_group([0], [3])]},
        {"size_match": True, "num_groups": 1,
         "groups": [_group([5], [3])]},
    ]}
    assert _matcher()(patterns, {}) is False


def test_returns_false_on_zero_change_groups_per_pair() -> None:
    # Identity territory -- iter-13 matcher's job. Failing closed here
    # keeps the two matchers strictly mutually exclusive, mirroring
    # iter-18's symmetric posture on the output side.
    patterns = {"pair_analyses": [_identity_pair(), _identity_pair()]}
    assert _matcher()(patterns, {}) is False


def test_returns_false_when_any_pair_has_zero_groups() -> None:
    # Even if one pair has a uniform input and another has zero groups,
    # we cannot generalise -- the zero-group pair provides no evidence,
    # so we fail-closed.
    patterns = {"pair_analyses": [_uniform_input_pair(),
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


def test_returns_false_on_missing_input_colors_in_group() -> None:
    group_missing = {"output_colors": [3], "top_row": 0, "top_col": 0}
    analysis = {"size_match": True, "num_groups": 1,
                "groups": [group_missing]}
    assert _matcher()({"pair_analyses": [analysis]}, {}) is False


def test_returns_false_on_non_list_input_colors() -> None:
    group_bad = {"input_colors": 0, "output_colors": [3],
                 "top_row": 0, "top_col": 0}
    analysis = {"size_match": True, "num_groups": 1,
                "groups": [group_bad]}
    assert _matcher()({"pair_analyses": [analysis]}, {}) is False


def test_returns_false_on_multi_input_colors_in_group() -> None:
    # A single group spanning two distinct input colours is a contract
    # violation for "uniform" -- even if the cross-pair set would still
    # have cardinality one in some degenerate way.
    group_bad = {"input_colors": [0, 5], "output_colors": [3],
                 "top_row": 0, "top_col": 0}
    analysis = {"size_match": True, "num_groups": 1,
                "groups": [group_bad]}
    assert _matcher()({"pair_analyses": [analysis]}, {}) is False


def test_returns_false_on_empty_input_colors() -> None:
    # An empty input_colors list is missing data, not "uniform with
    # zero choices". Fail-closed.
    group_bad = {"input_colors": [], "output_colors": [3],
                 "top_row": 0, "top_col": 0}
    analysis = {"size_match": True, "num_groups": 1,
                "groups": [group_bad]}
    assert _matcher()({"pair_analyses": [analysis]}, {}) is False


def test_is_side_effect_free_on_inputs() -> None:
    patterns = {"pair_analyses": [_uniform_input_pair(),
                                  _uniform_input_pair()]}
    params = {"unused": 1}
    before_p = copy.deepcopy(patterns)
    before_q = copy.deepcopy(params)
    _matcher()(patterns, params)
    assert patterns == before_p, "matcher mutated patterns"
    assert params == before_q, "matcher mutated params"


def test_is_deterministic_across_repeats() -> None:
    patterns = {"pair_analyses": [_uniform_input_pair(),
                                  _uniform_input_pair()]}
    results = [_matcher()(patterns, {}) for _ in range(5)]
    assert len(set(results)) == 1, f"non-deterministic outputs: {results}"


def test_mutually_exclusive_with_identity_transformation() -> None:
    # identity_transformation requires zero change groups per pair;
    # input_color_uniform requires at least one group per pair. They
    # are mutually exclusive on any patterns dict, mirroring iter-18's
    # symmetric posture on the output side.
    identity_patterns = {
        "grid_size_preserved": True,
        "pair_analyses": [_identity_pair(), _identity_pair()],
    }
    uniform_patterns = {
        "grid_size_preserved": True,
        "pair_analyses": [_uniform_input_pair(),
                          _uniform_input_pair()],
    }
    identity = CONDITION_REGISTRY["identity_transformation"]

    assert _matcher()(identity_patterns, {}) is False
    assert identity(identity_patterns, {}) is True

    assert _matcher()(uniform_patterns, {}) is True
    assert identity(uniform_patterns, {}) is False


def test_orthogonal_to_output_color_uniform() -> None:
    # Independent axes: the input-side dual of iter-18. They CAN
    # co-fire (the simplest "paint colour C cells with K" shape) AND
    # they CAN fire independently. Concretely:
    #
    #   * input uniform + output uniform: paint colour-0 cells with K
    #     (both axes collapsed).
    #   * input uniform + output varying (this test's iter-19 lemma):
    #     a one-to-many mapping driven by position. iter-19 fires;
    #     iter-18 does NOT.
    #   * input varying + output uniform: iter-18 fires; iter-19 does
    #     NOT.
    output_uniform = CONDITION_REGISTRY["output_color_uniform"]

    # case 1: both fire
    both_patterns = {
        "grid_size_preserved": True,
        "pair_analyses": [_uniform_input_uniform_output_pair(),
                          _uniform_input_uniform_output_pair()],
    }
    assert _matcher()(both_patterns, {}) is True
    assert output_uniform(both_patterns, {}) is True

    # case 2: input uniform, output varying
    input_only = {
        "grid_size_preserved": True,
        "pair_analyses": [_uniform_input_pair(),
                          _uniform_input_pair()],
    }
    assert _matcher()(input_only, {}) is True
    assert output_uniform(input_only, {}) is False

    # case 3: output uniform, input varying
    output_only = {
        "grid_size_preserved": True,
        "pair_analyses": [
            {"size_match": True, "num_groups": 2,
             "groups": [_group([0], [3]), _group([5], [3])]},
            {"size_match": True, "num_groups": 2,
             "groups": [_group([0], [3]), _group([5], [3])]},
        ],
    }
    assert _matcher()(output_only, {}) is False
    assert output_uniform(output_only, {}) is True


def test_can_co_fire_with_sequential_recoloring() -> None:
    # All input cells are colour 0; outputs form the contiguous range
    # [3, 4, 5] ordered by top_row. sequential_recoloring fires (its
    # contract is about output-side cardinality and ordering, not
    # input-side); input_color_uniform also fires (input side is one
    # constant). Orthogonal axes.
    patterns = {
        "grid_size_preserved": True,
        "pair_analyses": [
            {"size_match": True, "num_groups": 3,
             "groups": [
                 _group([0], [3], top_row=0),
                 _group([0], [4], top_row=1),
                 _group([0], [5], top_row=2),
             ]},
            {"size_match": True, "num_groups": 3,
             "groups": [
                 _group([0], [3], top_row=0),
                 _group([0], [4], top_row=1),
                 _group([0], [5], top_row=2),
             ]},
        ],
    }
    seq = CONDITION_REGISTRY["sequential_recoloring"]
    assert _matcher()(patterns, {}) is True
    assert seq(patterns, {}) is True, (
        "sequential_recoloring should still fire on the same patterns dict; "
        "input-side uniformity does not preclude output-side sequencing"
    )


def test_orthogonal_to_dimensional_axis() -> None:
    # input_color_uniform inspects change-group input colours, not
    # dimensions. A uniform-input task where every pair has
    # size_match=False (e.g. tiling output is bigger, but the overlap
    # region's change groups all start from colour 0) must still fire
    # this matcher -- orthogonal to grid_size_changed.
    patterns = {
        "grid_size_preserved": False,
        "pair_analyses": [
            {"size_match": False, "num_groups": 1,
             "groups": [_group([0], [3])]},
            {"size_match": False, "num_groups": 1,
             "groups": [_group([0], [5])]},
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
    # uniform-input pair: sorted single-element input_colors and
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
                    {"input_colors": [0], "output_colors": [5],
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
    pos = _matcher()({"pair_analyses": [_uniform_input_pair()]}, {})
    neg = _matcher()({"pair_analyses": [_mixed_input_pair()]}, {})
    assert pos is True, f"expected literal True, got {pos!r}"
    assert neg is False, f"expected literal False, got {neg!r}"


# --------------------------------------------------------------------------
# Driver.
# --------------------------------------------------------------------------

def _run_all() -> int:
    tests = [
        test_registered_in_global_registry,
        test_previous_matchers_still_registered,
        test_seven_distinct_matchers_registered,
        test_matcher_is_callable,
        test_returns_true_on_single_pair_uniform_input,
        test_returns_true_on_multi_pair_uniform_input,
        test_returns_true_for_single_group_per_pair,
        test_fires_when_uniform_input_maps_to_multiple_outputs,
        test_returns_false_on_two_distinct_input_colors_within_a_pair,
        test_returns_false_when_input_color_differs_across_pairs,
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
        test_returns_false_on_missing_input_colors_in_group,
        test_returns_false_on_non_list_input_colors,
        test_returns_false_on_multi_input_colors_in_group,
        test_returns_false_on_empty_input_colors,
        test_is_side_effect_free_on_inputs,
        test_is_deterministic_across_repeats,
        test_mutually_exclusive_with_identity_transformation,
        test_orthogonal_to_output_color_uniform,
        test_can_co_fire_with_sequential_recoloring,
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
