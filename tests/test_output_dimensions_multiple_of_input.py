"""
tests/test_output_dimensions_multiple_of_input.py -- exercise the
iter-33 matcher ``agent.conditions.output_dimensions_multiple_of_input``.

Runs without pytest:

    python tests/test_output_dimensions_multiple_of_input.py

Dependency-free, same runner style as iters
1 / 8 / 10 / 13 / 17 / 18 / 19 / 20 / 22 / 23 / 24 / 26 / 28 / 30 / 32.

The matcher is on a new axis (relational-dimensional): it names
"every example pair's output dimensions are a positive integer
multiple of its input dimensions, with a single (k_h, k_w) scale
ratio constant across all pairs and (k_h, k_w) != (1, 1)". Strictly
disjoint from ``grid_size_preserved`` (iter 1) by the (1, 1)
exclusion; orthogonal to ``input_dimensions_constant`` (iter 22) and
``output_dimensions_constant`` (iter 20). Names the recognition
precondition for tile/scale rule shapes (the probe tasks 00576224
and 007bbfb7 both fire this matcher with (k_h, k_w) = (3, 3)).
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


MATCHER_NAME = "output_dimensions_multiple_of_input"


def _matcher():
    return CONDITION_REGISTRY[MATCHER_NAME]


def _analysis(*, input_height, input_width, output_height, output_width,
              groups=()):
    return {
        "total_changes": sum(g.get("cell_count", 0) for g in groups),
        "num_groups": len(groups),
        "groups": list(groups),
        "size_match": (input_height == output_height
                       and input_width == output_width),
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
    # Adjacent invariant -- iter 33 must not displace iters
    # 1 / 8 / 10 / 13 / 17 / 18 / 19 / 20 / 22 / 23 / 24 / 26 / 28 / 30 / 32.
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
                  "change_count_constant_across_pairs"):
        assert prior in CONDITION_REGISTRY, (
            f"prior matcher {prior!r} missing after iter-33 addition"
        )


def test_at_least_sixteen_distinct_matchers_registered() -> None:
    # P5 unit-monotone counter -- iter 33 lifts the count from 15 to 16.
    assert len(CONDITION_REGISTRY) >= 16, (
        f"expected at least 16 entries, got {len(CONDITION_REGISTRY)}: "
        f"{sorted(CONDITION_REGISTRY)}"
    )


def test_matcher_is_callable() -> None:
    fn = _matcher()
    assert callable(fn), f"registered entry is not callable: {fn!r}"


# ----- happy-path tests ---------------------------------------------

def test_returns_true_on_two_pairs_scale_3() -> None:
    # The 00576224 / 007bbfb7 probe-task shape: identical scale of 3.
    patterns = {"pair_analyses": [
        _analysis(input_height=2, input_width=2,
                  output_height=6, output_width=6),
        _analysis(input_height=2, input_width=2,
                  output_height=6, output_width=6),
    ]}
    assert _matcher()(patterns, {}) is True


def test_returns_true_on_tile_style_varying_inputs() -> None:
    # The exclusively-iter-33 territory: same scale ratio, but inputs
    # and outputs both VARY across pairs.
    # ``input_dimensions_constant`` does NOT fire (2x2 vs 3x3),
    # ``output_dimensions_constant`` does NOT fire (6x6 vs 9x9), yet
    # the scale ratio (3, 3) is constant.
    patterns = {"pair_analyses": [
        _analysis(input_height=2, input_width=2,
                  output_height=6, output_width=6),
        _analysis(input_height=3, input_width=3,
                  output_height=9, output_width=9),
    ]}
    assert _matcher()(patterns, {}) is True
    idc = CONDITION_REGISTRY["input_dimensions_constant"]
    odc = CONDITION_REGISTRY["output_dimensions_constant"]
    assert idc(patterns, {}) is False, (
        "input_dimensions_constant should not fire when inputs vary"
    )
    assert odc(patterns, {}) is False, (
        "output_dimensions_constant should not fire when outputs vary"
    )


def test_returns_true_on_asymmetric_scale() -> None:
    # Independent scale factors on the two axes.
    patterns = {"pair_analyses": [
        _analysis(input_height=2, input_width=3,
                  output_height=4, output_width=9),
        _analysis(input_height=2, input_width=3,
                  output_height=4, output_width=9),
    ]}
    assert _matcher()(patterns, {}) is True


def test_returns_true_on_single_pair_scale_2() -> None:
    patterns = {"pair_analyses": [
        _analysis(input_height=5, input_width=5,
                  output_height=10, output_width=10),
    ]}
    assert _matcher()(patterns, {}) is True


def test_returns_true_on_one_axis_only_scaled() -> None:
    # (k_h, k_w) = (1, 2): horizontal scaling only. Not (1, 1), so fires.
    patterns = {"pair_analyses": [
        _analysis(input_height=3, input_width=4,
                  output_height=3, output_width=8),
        _analysis(input_height=3, input_width=4,
                  output_height=3, output_width=8),
    ]}
    assert _matcher()(patterns, {}) is True


# ----- negative tests -----------------------------------------------

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


def test_returns_false_on_identity_ratio_only() -> None:
    # (k_h, k_w) == (1, 1) for every pair -- the iter-1 / iter-13 regime.
    # The matcher EXPLICITLY rejects this to keep its territory disjoint
    # from grid_size_preserved.
    patterns = {"pair_analyses": [
        _analysis(input_height=3, input_width=3,
                  output_height=3, output_width=3),
        _analysis(input_height=3, input_width=3,
                  output_height=3, output_width=3),
    ]}
    assert _matcher()(patterns, {}) is False


def test_returns_false_on_non_integer_multiple_height() -> None:
    # output_height = 4, input_height = 3 -- not a multiple.
    patterns = {"pair_analyses": [
        _analysis(input_height=3, input_width=3,
                  output_height=4, output_width=9),
    ]}
    assert _matcher()(patterns, {}) is False


def test_returns_false_on_non_integer_multiple_width() -> None:
    patterns = {"pair_analyses": [
        _analysis(input_height=3, input_width=3,
                  output_height=9, output_width=4),
    ]}
    assert _matcher()(patterns, {}) is False


def test_returns_false_on_smaller_output() -> None:
    # output_height < input_height -- not a positive-integer multiple.
    patterns = {"pair_analyses": [
        _analysis(input_height=6, input_width=6,
                  output_height=2, output_width=2),
    ]}
    assert _matcher()(patterns, {}) is False


def test_returns_false_when_scale_ratio_varies_across_pairs() -> None:
    # Pair 0 has scale (3, 3); pair 1 has scale (2, 2). Both are
    # valid integer multiples per-pair, but the ratio is not constant.
    patterns = {"pair_analyses": [
        _analysis(input_height=2, input_width=2,
                  output_height=6, output_width=6),
        _analysis(input_height=3, input_width=3,
                  output_height=6, output_width=6),
    ]}
    assert _matcher()(patterns, {}) is False


def test_returns_false_when_h_and_w_scales_differ_inconsistently() -> None:
    # Pair 0 has scale (2, 3); pair 1 has scale (3, 2). Both pairs
    # are integer multiples per-axis, but the (k_h, k_w) tuple is
    # not constant.
    patterns = {"pair_analyses": [
        _analysis(input_height=2, input_width=3,
                  output_height=4, output_width=9),
        _analysis(input_height=2, input_width=3,
                  output_height=6, output_width=6),
    ]}
    assert _matcher()(patterns, {}) is False


def test_returns_false_on_mixed_identity_and_scale_per_pair() -> None:
    # Pair 0 has scale (1, 1) (size-preserved); pair 1 has scale (2, 2).
    # The matcher requires the constant ratio AND that it is not (1, 1).
    # Since the ratios differ, return False.
    patterns = {"pair_analyses": [
        _analysis(input_height=4, input_width=4,
                  output_height=4, output_width=4),
        _analysis(input_height=4, input_width=4,
                  output_height=8, output_width=8),
    ]}
    assert _matcher()(patterns, {}) is False


# ----- strict-type tests --------------------------------------------

def test_returns_false_on_missing_dimension_fields() -> None:
    for missing in ("input_height", "input_width",
                    "output_height", "output_width"):
        analysis = _analysis(input_height=3, input_width=3,
                             output_height=6, output_width=6)
        del analysis[missing]
        patterns = {"pair_analyses": [analysis]}
        assert _matcher()(patterns, {}) is False, (
            f"missing {missing!r} should fail-closed"
        )


def test_returns_false_on_bool_dimension_field() -> None:
    # Bool is an int subclass. Strict-type matchers reject it.
    for fld in ("input_height", "input_width",
                "output_height", "output_width"):
        for bad in (True, False):
            analysis = _analysis(input_height=3, input_width=3,
                                 output_height=6, output_width=6)
            analysis[fld] = bad
            patterns = {"pair_analyses": [analysis]}
            assert _matcher()(patterns, {}) is False, (
                f"{fld}={bad!r} (bool) should fail-closed"
            )


def test_returns_false_on_zero_dimension_field() -> None:
    for fld in ("input_height", "input_width",
                "output_height", "output_width"):
        analysis = _analysis(input_height=3, input_width=3,
                             output_height=6, output_width=6)
        analysis[fld] = 0
        patterns = {"pair_analyses": [analysis]}
        assert _matcher()(patterns, {}) is False, (
            f"{fld}=0 should fail-closed"
        )


def test_returns_false_on_negative_dimension_field() -> None:
    for fld in ("input_height", "input_width",
                "output_height", "output_width"):
        analysis = _analysis(input_height=3, input_width=3,
                             output_height=6, output_width=6)
        analysis[fld] = -1
        patterns = {"pair_analyses": [analysis]}
        assert _matcher()(patterns, {}) is False, (
            f"{fld}=-1 should fail-closed"
        )


def test_returns_false_on_non_int_dimension_field() -> None:
    for fld in ("input_height", "input_width",
                "output_height", "output_width"):
        for bad in (0.5, "3", None, [3]):
            analysis = _analysis(input_height=3, input_width=3,
                                 output_height=6, output_width=6)
            analysis[fld] = bad
            patterns = {"pair_analyses": [analysis]}
            assert _matcher()(patterns, {}) is False, (
                f"{fld}={bad!r} ({type(bad).__name__}) should fail-closed"
            )


# ----- determinism / side-effect tests ------------------------------

def test_is_side_effect_free_on_inputs() -> None:
    patterns = {"pair_analyses": [
        _analysis(input_height=2, input_width=2,
                  output_height=6, output_width=6),
        _analysis(input_height=3, input_width=3,
                  output_height=9, output_width=9),
    ]}
    params = {"unused": 1}
    before_p = copy.deepcopy(patterns)
    before_q = copy.deepcopy(params)
    _matcher()(patterns, params)
    assert patterns == before_p, "matcher mutated patterns"
    assert params == before_q, "matcher mutated params"


def test_is_deterministic_across_repeats() -> None:
    patterns = {"pair_analyses": [
        _analysis(input_height=2, input_width=2,
                  output_height=6, output_width=6),
        _analysis(input_height=3, input_width=3,
                  output_height=9, output_width=9),
    ]}
    results = [_matcher()(patterns, {}) for _ in range(5)]
    assert len(set(results)) == 1, f"non-deterministic outputs: {results}"


# ----- mutual-exclusion / refinement tests --------------------------

def test_mutually_exclusive_with_grid_size_preserved() -> None:
    # When this matcher fires, (k_h, k_w) != (1, 1), so every pair
    # has dim change, so grid_size_preserved does NOT fire. Conversely,
    # when grid_size_preserved fires (per-pair in == out, i.e.
    # (k_h, k_w) == (1, 1) per pair), this matcher rejects on the
    # (1, 1) exclusion clause.
    scale_pat = {
        "grid_size_preserved": False,
        "pair_analyses": [
            _analysis(input_height=2, input_width=2,
                      output_height=6, output_width=6),
            _analysis(input_height=2, input_width=2,
                      output_height=6, output_width=6),
        ],
    }
    identity_pat = {
        "grid_size_preserved": True,
        "pair_analyses": [
            _analysis(input_height=3, input_width=3,
                      output_height=3, output_width=3),
            _analysis(input_height=3, input_width=3,
                      output_height=3, output_width=3),
        ],
    }
    gsp = CONDITION_REGISTRY["grid_size_preserved"]
    assert _matcher()(scale_pat, {}) is True
    assert gsp(scale_pat, {}) is False
    assert _matcher()(identity_pat, {}) is False
    assert gsp(identity_pat, {}) is True


def test_mutually_exclusive_with_identity_transformation() -> None:
    # identity_transformation requires every pair's size_match True
    # AND num_groups == 0 -- the dimensional precondition is (1, 1).
    # No patterns dict can fire both matchers.
    identity_pat = {
        "grid_size_preserved": True,
        "pair_analyses": [
            _analysis(input_height=3, input_width=3,
                      output_height=3, output_width=3),
            _analysis(input_height=3, input_width=3,
                      output_height=3, output_width=3),
        ],
    }
    identity = CONDITION_REGISTRY["identity_transformation"]
    assert identity(identity_pat, {}) is True
    assert _matcher()(identity_pat, {}) is False


def test_co_fires_with_grid_size_changed() -> None:
    # When this matcher fires, every pair has dim change, so
    # grid_size_changed (iter 17, "at least one pair has size change")
    # also fires.
    patterns = {"pair_analyses": [
        _analysis(input_height=2, input_width=2,
                  output_height=6, output_width=6),
        _analysis(input_height=3, input_width=3,
                  output_height=9, output_width=9),
    ]}
    gsc = CONDITION_REGISTRY["grid_size_changed"]
    assert _matcher()(patterns, {}) is True
    assert gsc(patterns, {}) is True


def test_grid_size_changed_does_not_imply_this_matcher() -> None:
    # The converse direction: grid_size_changed fires on tasks with
    # non-integer dimension changes, but this matcher does not.
    patterns = {"pair_analyses": [
        _analysis(input_height=3, input_width=3,
                  output_height=4, output_width=4),
    ]}
    gsc = CONDITION_REGISTRY["grid_size_changed"]
    assert gsc(patterns, {}) is True
    assert _matcher()(patterns, {}) is False


def test_can_co_fire_with_input_dimensions_constant() -> None:
    # Constant 2x2 inputs across pairs, all scaled to constant 6x6
    # outputs. Both this matcher AND input_dimensions_constant fire.
    patterns = {"pair_analyses": [
        _analysis(input_height=2, input_width=2,
                  output_height=6, output_width=6),
        _analysis(input_height=2, input_width=2,
                  output_height=6, output_width=6),
    ]}
    idc = CONDITION_REGISTRY["input_dimensions_constant"]
    assert _matcher()(patterns, {}) is True
    assert idc(patterns, {}) is True


def test_can_co_fire_with_output_dimensions_constant() -> None:
    patterns = {"pair_analyses": [
        _analysis(input_height=2, input_width=2,
                  output_height=6, output_width=6),
        _analysis(input_height=2, input_width=2,
                  output_height=6, output_width=6),
    ]}
    odc = CONDITION_REGISTRY["output_dimensions_constant"]
    assert _matcher()(patterns, {}) is True
    assert odc(patterns, {}) is True


def test_fires_without_input_or_output_dimensions_constant() -> None:
    # The exclusively-iter-33 territory: same scale ratio across pairs,
    # but neither the inputs nor the outputs are individually constant.
    patterns = {"pair_analyses": [
        _analysis(input_height=2, input_width=2,
                  output_height=6, output_width=6),
        _analysis(input_height=3, input_width=3,
                  output_height=9, output_width=9),
    ]}
    idc = CONDITION_REGISTRY["input_dimensions_constant"]
    odc = CONDITION_REGISTRY["output_dimensions_constant"]
    assert _matcher()(patterns, {}) is True
    assert idc(patterns, {}) is False
    assert odc(patterns, {}) is False


# ----- end-to-end with the real extractor --------------------------

def test_end_to_end_agreement_with_extract_pattern_shape() -> None:
    # The shape ExtractPatternOperator._analyze_pair emits on a
    # 2x2 -> 6x6 tile (matches probe task 00576224's dimensions).
    from agent.active_operators import ExtractPatternOperator  # noqa: E402

    op = ExtractPatternOperator()

    class _Grid:
        def __init__(self, raw):
            self.raw = raw
            self.height = len(raw)
            self.width = len(raw[0]) if raw else 0

    raw_in = [[1, 2], [3, 4]]
    # An arbitrary 6x6 output filled with 0; the matcher cares about
    # dimensions only, not contents.
    raw_out = [[0] * 6 for _ in range(6)]
    analysis = op._analyze_pair(_Grid(raw_in), _Grid(raw_out))
    patterns = {"pair_analyses": [analysis, copy.deepcopy(analysis)]}
    assert _matcher()(patterns, {}) is True


def test_end_to_end_rejects_non_integer_scale() -> None:
    from agent.active_operators import ExtractPatternOperator  # noqa: E402

    op = ExtractPatternOperator()

    class _Grid:
        def __init__(self, raw):
            self.raw = raw
            self.height = len(raw)
            self.width = len(raw[0]) if raw else 0

    raw_in = [[0, 0, 0], [0, 0, 0], [0, 0, 0]]
    raw_out = [[0] * 4 for _ in range(4)]
    analysis = op._analyze_pair(_Grid(raw_in), _Grid(raw_out))
    patterns = {"pair_analyses": [analysis]}
    assert _matcher()(patterns, {}) is False


def test_returned_value_is_boolean_not_truthy() -> None:
    pos_pat = {"pair_analyses": [
        _analysis(input_height=2, input_width=2,
                  output_height=6, output_width=6),
    ]}
    neg_pat = {"pair_analyses": [
        _analysis(input_height=3, input_width=3,
                  output_height=3, output_width=3),
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
        test_at_least_sixteen_distinct_matchers_registered,
        test_matcher_is_callable,
        test_returns_true_on_two_pairs_scale_3,
        test_returns_true_on_tile_style_varying_inputs,
        test_returns_true_on_asymmetric_scale,
        test_returns_true_on_single_pair_scale_2,
        test_returns_true_on_one_axis_only_scaled,
        test_returns_false_on_empty_pair_analyses,
        test_returns_false_on_missing_pair_analyses,
        test_returns_false_on_non_dict_patterns,
        test_returns_false_on_non_list_pair_analyses,
        test_returns_false_on_malformed_analysis_entry,
        test_returns_false_on_identity_ratio_only,
        test_returns_false_on_non_integer_multiple_height,
        test_returns_false_on_non_integer_multiple_width,
        test_returns_false_on_smaller_output,
        test_returns_false_when_scale_ratio_varies_across_pairs,
        test_returns_false_when_h_and_w_scales_differ_inconsistently,
        test_returns_false_on_mixed_identity_and_scale_per_pair,
        test_returns_false_on_missing_dimension_fields,
        test_returns_false_on_bool_dimension_field,
        test_returns_false_on_zero_dimension_field,
        test_returns_false_on_negative_dimension_field,
        test_returns_false_on_non_int_dimension_field,
        test_is_side_effect_free_on_inputs,
        test_is_deterministic_across_repeats,
        test_mutually_exclusive_with_grid_size_preserved,
        test_mutually_exclusive_with_identity_transformation,
        test_co_fires_with_grid_size_changed,
        test_grid_size_changed_does_not_imply_this_matcher,
        test_can_co_fire_with_input_dimensions_constant,
        test_can_co_fire_with_output_dimensions_constant,
        test_fires_without_input_or_output_dimensions_constant,
        test_end_to_end_agreement_with_extract_pattern_shape,
        test_end_to_end_rejects_non_integer_scale,
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
