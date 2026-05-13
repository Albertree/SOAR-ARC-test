"""
tests/test_single_change_group_per_pair.py -- exercise the iter-23
matcher ``agent.conditions.single_change_group_per_pair``.

Runs without pytest:

    python tests/test_single_change_group_per_pair.py

Dependency-free, same runner style as iters
1 / 8 / 10 / 13 / 17 / 18 / 19 / 20 / 22.
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


MATCHER_NAME = "single_change_group_per_pair"


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
        "total_changes": sum(g.get("cell_count", 1) for g in groups),
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
    # Adjacent invariant -- iter 23 must not displace iters
    # 1 / 8 / 10 / 13 / 17 / 18 / 19 / 20 / 22.
    for prior in ("grid_size_preserved", "consistent_color_mapping",
                  "sequential_recoloring", "identity_transformation",
                  "grid_size_changed", "output_color_uniform",
                  "input_color_uniform", "output_dimensions_constant",
                  "input_dimensions_constant"):
        assert prior in CONDITION_REGISTRY, (
            f"prior matcher {prior!r} missing after iter-23 addition"
        )


def test_ten_distinct_matchers_registered() -> None:
    # P5 unit-monotone counter -- there must be at least 10 entries now.
    assert len(CONDITION_REGISTRY) >= 10, (
        f"expected at least 10 entries, got {len(CONDITION_REGISTRY)}: "
        f"{sorted(CONDITION_REGISTRY)}"
    )


def test_matcher_is_callable() -> None:
    fn = _matcher()
    assert callable(fn), f"registered entry is not callable: {fn!r}"


def test_returns_true_on_single_pair_with_one_group() -> None:
    patterns = {"pair_analyses": [
        _analysis(groups=[_group([0], [3])]),
    ]}
    assert _matcher()(patterns, {}) is True


def test_returns_true_on_multi_pair_with_one_group_each() -> None:
    patterns = {"pair_analyses": [
        _analysis(groups=[_group([0], [3])]),
        _analysis(groups=[_group([1], [4])]),
        _analysis(groups=[_group([2], [5])]),
    ]}
    assert _matcher()(patterns, {}) is True


def test_returns_false_on_zero_groups_per_pair() -> None:
    # Identity-style patterns: every pair has zero changes. The matcher
    # must NOT fire (this case is identity_transformation's territory,
    # cardinality 0 vs cardinality 1 strict mutual exclusion).
    patterns = {"pair_analyses": [
        _analysis(groups=[]),
        _analysis(groups=[]),
    ]}
    assert _matcher()(patterns, {}) is False


def test_returns_false_on_two_groups_per_pair() -> None:
    # Multi-group: cardinality 2. Different recognition territory.
    patterns = {"pair_analyses": [
        _analysis(groups=[
            _group([0], [3]),
            _group([1], [4], top_row=1),
        ]),
    ]}
    assert _matcher()(patterns, {}) is False


def test_returns_false_on_three_groups_per_pair() -> None:
    patterns = {"pair_analyses": [
        _analysis(groups=[
            _group([0], [3]),
            _group([1], [4], top_row=1),
            _group([2], [5], top_row=2),
        ]),
    ]}
    assert _matcher()(patterns, {}) is False


def test_returns_false_on_mixed_one_and_two_groups() -> None:
    # Pair 0 has 1 group, pair 1 has 2. The matcher requires ALL pairs
    # to have exactly 1; mixed is False.
    patterns = {"pair_analyses": [
        _analysis(groups=[_group([0], [3])]),
        _analysis(groups=[
            _group([0], [3]),
            _group([1], [4], top_row=1),
        ]),
    ]}
    assert _matcher()(patterns, {}) is False


def test_returns_false_on_mixed_one_and_zero_groups() -> None:
    # Pair 0 has 1 group, pair 1 has 0. Strict cardinality means False.
    patterns = {"pair_analyses": [
        _analysis(groups=[_group([0], [3])]),
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


def test_returns_false_on_missing_num_groups() -> None:
    analysis_missing = {
        "total_changes": 1,
        # num_groups missing
        "groups": [_group([0], [3])],
        "size_match": True,
        "input_height": 3, "input_width": 3,
        "output_height": 3, "output_width": 3,
    }
    assert _matcher()({"pair_analyses": [analysis_missing]}, {}) is False


def test_returns_false_on_non_int_num_groups() -> None:
    for bad in (1.0, "1", None, [1], {"v": 1}):
        analysis = _analysis(groups=[_group([0], [3])])
        analysis["num_groups"] = bad
        assert _matcher()({"pair_analyses": [analysis]}, {}) is False, (
            f"num_groups={bad!r} ({type(bad).__name__}) should fail-closed"
        )


def test_returns_false_on_bool_num_groups() -> None:
    # bool is a subclass of int in Python. Strict-type matchers (iters
    # 13 / 17 / 18 / 19 / 20 / 22 and validate_rule V1) reject it -- the
    # field is semantically an integer count, not a Boolean flag.
    analysis = _analysis(groups=[_group([0], [3])])
    analysis["num_groups"] = True  # truthy and == 1, but Boolean-typed
    assert _matcher()({"pair_analyses": [analysis]}, {}) is False
    analysis = _analysis(groups=[_group([0], [3])])
    analysis["num_groups"] = False  # falsy, but Boolean-typed
    assert _matcher()({"pair_analyses": [analysis]}, {}) is False


def test_returns_false_on_negative_num_groups() -> None:
    for bad in (-1, -100):
        analysis = _analysis(groups=[_group([0], [3])])
        analysis["num_groups"] = bad
        assert _matcher()({"pair_analyses": [analysis]}, {}) is False, (
            f"num_groups={bad} should fail-closed"
        )


def test_returns_false_when_one_pair_missing_num_groups() -> None:
    # Mixed shape: pair 0 carries num_groups, pair 1 does not. The
    # matcher cannot conclude "1-group everywhere" from partial data --
    # fail closed.
    good = _analysis(groups=[_group([0], [3])])
    bad = {
        "total_changes": 1,
        "groups": [_group([0], [3])],
        "size_match": True,
        "input_height": 3, "input_width": 3,
        "output_height": 3, "output_width": 3,
    }
    assert _matcher()({"pair_analyses": [good, bad]}, {}) is False
    assert _matcher()({"pair_analyses": [bad, good]}, {}) is False


def test_is_side_effect_free_on_inputs() -> None:
    patterns = {"pair_analyses": [
        _analysis(groups=[_group([0], [3])]),
        _analysis(groups=[_group([1], [4])]),
    ]}
    params = {"unused": 1}
    before_p = copy.deepcopy(patterns)
    before_q = copy.deepcopy(params)
    _matcher()(patterns, params)
    assert patterns == before_p, "matcher mutated patterns"
    assert params == before_q, "matcher mutated params"


def test_is_deterministic_across_repeats() -> None:
    patterns = {"pair_analyses": [
        _analysis(groups=[_group([0], [3])]),
        _analysis(groups=[_group([0], [3])]),
    ]}
    results = [_matcher()(patterns, {}) for _ in range(5)]
    assert len(set(results)) == 1, f"non-deterministic outputs: {results}"


def test_mutually_exclusive_with_identity_transformation() -> None:
    # identity_transformation requires num_groups == 0 per pair;
    # this matcher requires num_groups == 1. Strict mutual exclusion
    # on cardinality.
    identity_pat = {
        "grid_size_preserved": True,
        "pair_analyses": [
            _analysis(groups=[]),
            _analysis(groups=[]),
        ],
    }
    single_blob_pat = {
        "grid_size_preserved": True,
        "pair_analyses": [
            _analysis(groups=[_group([0], [3])]),
            _analysis(groups=[_group([0], [3])]),
        ],
    }
    identity = CONDITION_REGISTRY["identity_transformation"]
    assert identity(identity_pat, {}) is True
    assert _matcher()(identity_pat, {}) is False
    assert identity(single_blob_pat, {}) is False
    assert _matcher()(single_blob_pat, {}) is True


def test_can_co_fire_with_output_color_uniform() -> None:
    # Single blob per pair AND every group's output colour is the same
    # single constant. The simplest "paint a single blob with K" rule
    # shape's recognition preconditions both fire.
    patterns = {
        "pair_analyses": [
            _analysis(groups=[_group([0], [3])]),
            _analysis(groups=[_group([1], [3])]),
        ],
    }
    ocu = CONDITION_REGISTRY["output_color_uniform"]
    assert _matcher()(patterns, {}) is True
    assert ocu(patterns, {}) is True, (
        "output_color_uniform must still fire on the single-blob "
        "uniform-K patterns dict"
    )


def test_can_co_fire_with_input_color_uniform() -> None:
    # Single blob per pair AND every group's input colour is the same
    # single constant. The recognition preconditions for "where input
    # had C (which forms one blob), paint K" fire together.
    patterns = {
        "pair_analyses": [
            _analysis(groups=[_group([0], [3])]),
            _analysis(groups=[_group([0], [4])]),
        ],
    }
    icu = CONDITION_REGISTRY["input_color_uniform"]
    assert _matcher()(patterns, {}) is True
    assert icu(patterns, {}) is True


def test_can_co_fire_with_input_dimensions_constant() -> None:
    # Single blob per pair AND input dimensions constant across pairs.
    # Combined precondition for a literal-coord coloring rule that
    # pins both blob count and training-side input shape.
    patterns = {
        "pair_analyses": [
            _analysis(groups=[_group([0], [3])],
                      input_height=4, input_width=4),
            _analysis(groups=[_group([1], [3])],
                      input_height=4, input_width=4),
        ],
    }
    idc = CONDITION_REGISTRY["input_dimensions_constant"]
    assert _matcher()(patterns, {}) is True
    assert idc(patterns, {}) is True


def test_can_co_fire_with_grid_size_preserved() -> None:
    # Single blob on same-size pairs. They are orthogonal axes.
    patterns = {
        "grid_size_preserved": True,
        "pair_analyses": [
            _analysis(groups=[_group([0], [3])]),
            _analysis(groups=[_group([0], [3])]),
        ],
    }
    gsp = CONDITION_REGISTRY["grid_size_preserved"]
    assert _matcher()(patterns, {}) is True
    assert gsp(patterns, {}) is True


def test_can_co_fire_with_grid_size_changed() -> None:
    # Single blob on dimension-changed pairs. They are orthogonal axes:
    # group count is independent of whether output size differs from
    # input size.
    patterns = {
        "pair_analyses": [
            _analysis(groups=[_group([0], [3])],
                      input_height=3, input_width=3,
                      output_height=9, output_width=9,
                      size_match=False),
            _analysis(groups=[_group([1], [4])],
                      input_height=3, input_width=3,
                      output_height=9, output_width=9,
                      size_match=False),
        ],
    }
    gsc = CONDITION_REGISTRY["grid_size_changed"]
    assert _matcher()(patterns, {}) is True
    assert gsc(patterns, {}) is True


def test_does_not_imply_consistent_color_mapping() -> None:
    # A single-blob pair where the one group's single input colour
    # maps to MULTIPLE output colours: this matcher fires (one
    # group), but consistent_color_mapping does NOT (the 1:1 contract
    # iter-8 enforces requires each input to map to exactly one
    # output, and here input 0 maps to {3, 4}). Verifies the two
    # axes are independent on the group-content side.
    patterns = {
        "pair_analyses": [
            _analysis(groups=[_group([0], [3, 4])]),
        ],
    }
    ccm = CONDITION_REGISTRY["consistent_color_mapping"]
    assert _matcher()(patterns, {}) is True
    assert ccm(patterns, {}) is False, (
        "consistent_color_mapping must NOT fire when a group's single "
        "input colour maps to multiple output colours -- the iter-8 "
        "1:1 contract is broken; this matcher cares only about group "
        "count, not group content"
    )


def test_does_not_require_grid_size_preserved() -> None:
    # Single blob on dimension-changed pairs: this matcher fires but
    # grid_size_preserved does not. Demonstrates non-refinement on the
    # dimensional axis.
    patterns = {
        "pair_analyses": [
            _analysis(groups=[_group([0], [3])],
                      output_height=9, output_width=9,
                      size_match=False),
        ],
    }
    gsp = CONDITION_REGISTRY["grid_size_preserved"]
    assert _matcher()(patterns, {}) is True
    assert gsp(patterns, {}) is False


def test_end_to_end_agreement_with_extract_pattern_shape() -> None:
    # The shape ExtractPatternOperator._analyze_pair emits: carries
    # num_groups derived from the connected-components grouping of
    # changed cells. Verify the matcher accepts a patterns dict
    # assembled with the live operator's output shape.
    from agent.active_operators import ExtractPatternOperator  # noqa: E402

    op = ExtractPatternOperator()

    class _Grid:
        def __init__(self, raw):
            self.raw = raw
            self.height = len(raw)
            self.width = len(raw[0]) if raw else 0

    # 3x3 grid: a single 4-connected blob of changes at the top-left
    # 2x2 corner. Everywhere else input == output, so no extra change
    # group is generated. num_groups must be 1.
    raw_in = [
        [0, 0, 1],
        [0, 0, 1],
        [1, 1, 1],
    ]
    raw_out = [
        [3, 3, 1],
        [3, 3, 1],
        [1, 1, 1],
    ]
    analysis_a = op._analyze_pair(_Grid(raw_in), _Grid(raw_out))
    analysis_b = op._analyze_pair(_Grid(raw_in), _Grid(raw_out))
    assert analysis_a["num_groups"] == 1, (
        f"live _analyze_pair produced num_groups={analysis_a['num_groups']}; "
        f"test fixture invariant violated"
    )
    patterns = {"pair_analyses": [analysis_a, analysis_b]}
    assert _matcher()(patterns, {}) is True


def test_end_to_end_disagreement_on_two_blob_grid() -> None:
    # Verify the matcher correctly rejects a live _analyze_pair output
    # where the changes form TWO disjoint connected components.
    from agent.active_operators import ExtractPatternOperator  # noqa: E402

    op = ExtractPatternOperator()

    class _Grid:
        def __init__(self, raw):
            self.raw = raw
            self.height = len(raw)
            self.width = len(raw[0]) if raw else 0

    # 3x3 grid: two disjoint single-cell blobs (top-left, bottom-right).
    raw_in = [
        [0, 1, 1],
        [1, 1, 1],
        [1, 1, 0],
    ]
    raw_out = [
        [3, 1, 1],
        [1, 1, 1],
        [1, 1, 3],
    ]
    analysis = op._analyze_pair(_Grid(raw_in), _Grid(raw_out))
    assert analysis["num_groups"] == 2, (
        f"two-blob test fixture broken: live _analyze_pair produced "
        f"num_groups={analysis['num_groups']}"
    )
    patterns = {"pair_analyses": [analysis]}
    assert _matcher()(patterns, {}) is False


def test_returned_value_is_boolean_not_truthy() -> None:
    # Mirrors the strict-`is True` contract from recognized_conditions:
    # downstream consumers filter on `match(...) is True` exactly.
    patterns_pos = {"pair_analyses": [
        _analysis(groups=[_group([0], [3])]),
    ]}
    patterns_neg = {"pair_analyses": [
        _analysis(groups=[
            _group([0], [3]),
            _group([1], [4], top_row=1),
        ]),
    ]}
    pos = _matcher()(patterns_pos, {})
    neg = _matcher()(patterns_neg, {})
    assert pos is True, f"expected literal True, got {pos!r}"
    assert neg is False, f"expected literal False, got {neg!r}"


# ----------------------------------------------------------------------
# Driver.
# ----------------------------------------------------------------------

def _run_all() -> int:
    tests = [
        test_registered_in_global_registry,
        test_previous_matchers_still_registered,
        test_ten_distinct_matchers_registered,
        test_matcher_is_callable,
        test_returns_true_on_single_pair_with_one_group,
        test_returns_true_on_multi_pair_with_one_group_each,
        test_returns_false_on_zero_groups_per_pair,
        test_returns_false_on_two_groups_per_pair,
        test_returns_false_on_three_groups_per_pair,
        test_returns_false_on_mixed_one_and_two_groups,
        test_returns_false_on_mixed_one_and_zero_groups,
        test_returns_false_on_empty_pair_analyses,
        test_returns_false_on_missing_pair_analyses,
        test_returns_false_on_non_dict_patterns,
        test_returns_false_on_non_list_pair_analyses,
        test_returns_false_on_malformed_analysis_entry,
        test_returns_false_on_missing_num_groups,
        test_returns_false_on_non_int_num_groups,
        test_returns_false_on_bool_num_groups,
        test_returns_false_on_negative_num_groups,
        test_returns_false_when_one_pair_missing_num_groups,
        test_is_side_effect_free_on_inputs,
        test_is_deterministic_across_repeats,
        test_mutually_exclusive_with_identity_transformation,
        test_can_co_fire_with_output_color_uniform,
        test_can_co_fire_with_input_color_uniform,
        test_can_co_fire_with_input_dimensions_constant,
        test_can_co_fire_with_grid_size_preserved,
        test_can_co_fire_with_grid_size_changed,
        test_does_not_imply_consistent_color_mapping,
        test_does_not_require_grid_size_preserved,
        test_end_to_end_agreement_with_extract_pattern_shape,
        test_end_to_end_disagreement_on_two_blob_grid,
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
