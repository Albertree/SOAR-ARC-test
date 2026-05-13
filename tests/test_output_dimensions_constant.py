"""
tests/test_output_dimensions_constant.py -- exercise the iter-20 matcher
``agent.conditions.output_dimensions_constant``.

Runs without pytest:

    python tests/test_output_dimensions_constant.py

Dependency-free, same runner style as iters 1 / 8 / 10 / 13 / 17 / 18 /
19.
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


MATCHER_NAME = "output_dimensions_constant"


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


def _analysis(*, output_height, output_width,
              input_height=None, input_width=None,
              groups=None, size_match=None):
    if input_height is None:
        input_height = output_height
    if input_width is None:
        input_width = output_width
    if groups is None:
        groups = []
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


# ──────────────────────────────────────────────────────────────────────────
# Tests.
# ──────────────────────────────────────────────────────────────────────────

def test_registered_in_global_registry() -> None:
    assert MATCHER_NAME in CONDITION_REGISTRY, (
        f"{MATCHER_NAME!r} not registered; got {sorted(CONDITION_REGISTRY)}"
    )


def test_previous_matchers_still_registered() -> None:
    # Adjacent invariant -- iter 20 must not displace iters 1 / 8 / 10 /
    # 13 / 17 / 18 / 19.
    for prior in ("grid_size_preserved", "consistent_color_mapping",
                  "sequential_recoloring", "identity_transformation",
                  "grid_size_changed", "output_color_uniform",
                  "input_color_uniform"):
        assert prior in CONDITION_REGISTRY, (
            f"prior matcher {prior!r} missing after iter-20 addition"
        )


def test_eight_distinct_matchers_registered() -> None:
    # P5 unit-monotone counter -- there must be at least 8 entries now.
    assert len(CONDITION_REGISTRY) >= 8, (
        f"expected at least 8 entries, got {len(CONDITION_REGISTRY)}: "
        f"{sorted(CONDITION_REGISTRY)}"
    )


def test_matcher_is_callable() -> None:
    fn = _matcher()
    assert callable(fn), f"registered entry is not callable: {fn!r}"


def test_returns_true_on_single_pair() -> None:
    # A single pair trivially has constant output dimensions (the set
    # has one element). This is a degenerate but correct positive --
    # min_evidence guards against single-pair over-confidence at the
    # rule layer, not at the matcher layer.
    patterns = {"pair_analyses": [_analysis(output_height=9, output_width=9)]}
    assert _matcher()(patterns, {}) is True


def test_returns_true_on_multi_pair_same_dims() -> None:
    patterns = {"pair_analyses": [
        _analysis(output_height=9, output_width=9),
        _analysis(output_height=9, output_width=9),
        _analysis(output_height=9, output_width=9),
    ]}
    assert _matcher()(patterns, {}) is True


def test_returns_true_when_input_dims_vary_but_output_constant() -> None:
    # The key iter-20 case: a tile-style transformation where every
    # input is different but every output is the same (H, W). The
    # matcher inspects output dimensions, not input dimensions; this
    # case must fire.
    patterns = {"pair_analyses": [
        _analysis(input_height=3, input_width=3,
                  output_height=9, output_width=9),
        _analysis(input_height=4, input_width=5,
                  output_height=9, output_width=9),
    ]}
    assert _matcher()(patterns, {}) is True


def test_returns_false_on_varying_output_height() -> None:
    patterns = {"pair_analyses": [
        _analysis(output_height=9, output_width=9),
        _analysis(output_height=12, output_width=9),
    ]}
    assert _matcher()(patterns, {}) is False


def test_returns_false_on_varying_output_width() -> None:
    patterns = {"pair_analyses": [
        _analysis(output_height=9, output_width=9),
        _analysis(output_height=9, output_width=12),
    ]}
    assert _matcher()(patterns, {}) is False


def test_returns_false_on_varying_both_dims() -> None:
    # Each pair has its own (H, W) tuple. Even if the H or W matches
    # for some pair, the combined tuple must be globally constant.
    patterns = {"pair_analyses": [
        _analysis(output_height=3, output_width=3),
        _analysis(output_height=5, output_width=5),
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


def test_returns_false_on_missing_output_height() -> None:
    # The dimension fields were added in iter 20; a patterns dict from
    # a pre-iter-20 cache or a malformed extractor must fail-closed.
    analysis_missing = {
        "total_changes": 0,
        "num_groups": 0,
        "groups": [],
        "size_match": True,
        # output_height missing
        "output_width": 9,
    }
    assert _matcher()({"pair_analyses": [analysis_missing]}, {}) is False


def test_returns_false_on_missing_output_width() -> None:
    analysis_missing = {
        "total_changes": 0,
        "num_groups": 0,
        "groups": [],
        "size_match": True,
        "output_height": 9,
        # output_width missing
    }
    assert _matcher()({"pair_analyses": [analysis_missing]}, {}) is False


def test_returns_false_on_non_int_output_dims() -> None:
    for bad in (3.0, "9", None, [9], {"v": 9}):
        analysis = _analysis(output_height=9, output_width=9)
        analysis["output_height"] = bad
        assert _matcher()({"pair_analyses": [analysis]}, {}) is False, (
            f"output_height={bad!r} ({type(bad).__name__}) should fail-closed"
        )
        analysis = _analysis(output_height=9, output_width=9)
        analysis["output_width"] = bad
        assert _matcher()({"pair_analyses": [analysis]}, {}) is False, (
            f"output_width={bad!r} ({type(bad).__name__}) should fail-closed"
        )


def test_returns_false_on_bool_output_dims() -> None:
    # bool is a subclass of int in Python. Strict-type matchers (iters
    # 13 / 17 / 18 / 19 / 20 and validate_rule V1) reject it -- the
    # field is semantically an integer count, not a Boolean flag.
    analysis = _analysis(output_height=9, output_width=9)
    analysis["output_height"] = True  # truthy, but Boolean-typed
    assert _matcher()({"pair_analyses": [analysis]}, {}) is False
    analysis = _analysis(output_height=9, output_width=9)
    analysis["output_width"] = False
    assert _matcher()({"pair_analyses": [analysis]}, {}) is False


def test_returns_false_on_zero_or_negative_output_dims() -> None:
    # Output dimensions are strict positive ints. 0 (empty grid) and
    # negatives are upstream extractor errors, not "uniform output
    # dimensions".
    for bad in (0, -1, -100):
        analysis = _analysis(output_height=9, output_width=9)
        analysis["output_height"] = bad
        assert _matcher()({"pair_analyses": [analysis]}, {}) is False, (
            f"output_height={bad} should fail-closed"
        )
        analysis = _analysis(output_height=9, output_width=9)
        analysis["output_width"] = bad
        assert _matcher()({"pair_analyses": [analysis]}, {}) is False, (
            f"output_width={bad} should fail-closed"
        )


def test_returns_false_when_one_pair_missing_dims_others_ok() -> None:
    # Mixed: pair 0 carries the iter-20 fields, pair 1 does not. The
    # matcher cannot conclude "constant" from partial data -- fail
    # closed.
    good = _analysis(output_height=9, output_width=9)
    bad = {
        "total_changes": 0,
        "num_groups": 0,
        "groups": [],
        "size_match": True,
    }
    assert _matcher()({"pair_analyses": [good, bad]}, {}) is False
    assert _matcher()({"pair_analyses": [bad, good]}, {}) is False


def test_is_side_effect_free_on_inputs() -> None:
    patterns = {"pair_analyses": [
        _analysis(output_height=9, output_width=9),
        _analysis(output_height=9, output_width=9),
    ]}
    params = {"unused": 1}
    before_p = copy.deepcopy(patterns)
    before_q = copy.deepcopy(params)
    _matcher()(patterns, params)
    assert patterns == before_p, "matcher mutated patterns"
    assert params == before_q, "matcher mutated params"


def test_is_deterministic_across_repeats() -> None:
    patterns = {"pair_analyses": [
        _analysis(output_height=9, output_width=9),
        _analysis(output_height=9, output_width=9),
    ]}
    results = [_matcher()(patterns, {}) for _ in range(5)]
    assert len(set(results)) == 1, f"non-deterministic outputs: {results}"


def test_co_fires_with_grid_size_changed_on_tile_style_task() -> None:
    # A tile-style task: every pair has input != output dimensions
    # (grid_size_changed fires) AND every pair has the same output
    # dimensions (output_dimensions_constant fires). Together they
    # are the precondition for a constant-size make_grid rule.
    patterns = {
        "grid_size_preserved": False,
        "pair_analyses": [
            _analysis(input_height=3, input_width=3,
                      output_height=9, output_width=9),
            _analysis(input_height=3, input_width=3,
                      output_height=9, output_width=9),
        ],
    }
    gsc = CONDITION_REGISTRY["grid_size_changed"]
    assert _matcher()(patterns, {}) is True
    assert gsc(patterns, {}) is True, (
        "grid_size_changed must still fire on the same patterns dict"
    )


def test_can_co_fire_with_grid_size_preserved() -> None:
    # A same-size task where every pair shares the same dimensions:
    # grid_size_preserved fires (per-pair size_match is True) AND
    # output_dimensions_constant fires (every pair's output dim is the
    # same). They are NOT mutually exclusive; they recognise different
    # axes of the task.
    patterns = {
        "grid_size_preserved": True,
        "pair_analyses": [
            _analysis(input_height=4, input_width=4,
                      output_height=4, output_width=4),
            _analysis(input_height=4, input_width=4,
                      output_height=4, output_width=4),
        ],
    }
    gsp = CONDITION_REGISTRY["grid_size_preserved"]
    assert _matcher()(patterns, {}) is True
    assert gsp(patterns, {}) is True, (
        "grid_size_preserved must still fire on the same patterns dict"
    )


def test_orthogonal_to_output_color_uniform() -> None:
    # output_color_uniform inspects change-group output colours, this
    # matcher inspects output grid dimensions. They CAN co-fire on a
    # uniform-paint task with constant output dims, OR fire
    # independently. Verify both axes are independent on a single
    # patterns dict.
    patterns = {
        "grid_size_preserved": False,
        "pair_analyses": [
            {
                "total_changes": 1,
                "num_groups": 1,
                "groups": [_group([0], [3])],
                "size_match": False,
                "input_height": 3, "input_width": 3,
                "output_height": 9, "output_width": 9,
            },
            {
                "total_changes": 1,
                "num_groups": 1,
                "groups": [_group([1], [3])],
                "size_match": False,
                "input_height": 3, "input_width": 3,
                "output_height": 9, "output_width": 9,
            },
        ],
    }
    ocu = CONDITION_REGISTRY["output_color_uniform"]
    assert _matcher()(patterns, {}) is True
    assert ocu(patterns, {}) is True


def test_orthogonal_to_output_color_uniform_independent_failure() -> None:
    # output dims constant, but per-pair output colours differ (so
    # output_color_uniform fails). The two axes are genuinely
    # independent.
    patterns = {
        "pair_analyses": [
            {
                "total_changes": 1,
                "num_groups": 1,
                "groups": [_group([0], [3])],
                "size_match": False,
                "input_height": 3, "input_width": 3,
                "output_height": 9, "output_width": 9,
            },
            {
                "total_changes": 1,
                "num_groups": 1,
                "groups": [_group([0], [7])],
                "size_match": False,
                "input_height": 3, "input_width": 3,
                "output_height": 9, "output_width": 9,
            },
        ],
    }
    ocu = CONDITION_REGISTRY["output_color_uniform"]
    assert _matcher()(patterns, {}) is True
    assert ocu(patterns, {}) is False, (
        "output_color_uniform must NOT fire when per-pair output colours "
        "differ -- the axes are independent"
    )


def test_identity_pairs_co_fire_with_output_dimensions_constant() -> None:
    # An identity task (every pair has zero changes and matching
    # dims) trivially has constant output dimensions across pairs IF
    # every pair shares the same dims. They are NOT mutually
    # exclusive; identity_transformation does not forbid the
    # additional constant-output-dims property.
    patterns = {
        "grid_size_preserved": True,
        "pair_analyses": [
            _analysis(output_height=5, output_width=5,
                      input_height=5, input_width=5,
                      groups=[]),
            _analysis(output_height=5, output_width=5,
                      input_height=5, input_width=5,
                      groups=[]),
        ],
    }
    identity = CONDITION_REGISTRY["identity_transformation"]
    assert _matcher()(patterns, {}) is True
    assert identity(patterns, {}) is True, (
        "identity_transformation must still fire alongside "
        "output_dimensions_constant; the axes are independent"
    )


def test_end_to_end_agreement_with_extract_pattern_shape() -> None:
    # The shape ExtractPatternOperator._analyze_pair emits in iter 20:
    # carries output_height / output_width / input_height /
    # input_width alongside size_match. Verify the matcher accepts a
    # patterns dict assembled with the live operator's output shape.
    from agent.active_operators import ExtractPatternOperator  # noqa: E402

    op = ExtractPatternOperator()

    class _Grid:
        def __init__(self, raw):
            self.raw = raw

    raw_in = [[0, 0, 0], [0, 0, 0], [0, 0, 0]]
    raw_out = [[0] * 9 for _ in range(9)]
    analysis_a = op._analyze_pair(_Grid(raw_in), _Grid(raw_out))
    analysis_b = op._analyze_pair(_Grid(raw_in), _Grid(raw_out))
    patterns = {"pair_analyses": [analysis_a, analysis_b]}
    assert _matcher()(patterns, {}) is True, (
        "matcher must accept the live _analyze_pair output shape"
    )


def test_returned_value_is_boolean_not_truthy() -> None:
    # Mirrors the strict-`is True` contract from recognized_conditions:
    # downstream consumers filter on `match(...) is True` exactly.
    patterns_pos = {"pair_analyses": [
        _analysis(output_height=9, output_width=9),
        _analysis(output_height=9, output_width=9),
    ]}
    patterns_neg = {"pair_analyses": [
        _analysis(output_height=9, output_width=9),
        _analysis(output_height=12, output_width=9),
    ]}
    pos = _matcher()(patterns_pos, {})
    neg = _matcher()(patterns_neg, {})
    assert pos is True, f"expected literal True, got {pos!r}"
    assert neg is False, f"expected literal False, got {neg!r}"


# ──────────────────────────────────────────────────────────────────────────
# Driver.
# ──────────────────────────────────────────────────────────────────────────

def _run_all() -> int:
    tests = [
        test_registered_in_global_registry,
        test_previous_matchers_still_registered,
        test_eight_distinct_matchers_registered,
        test_matcher_is_callable,
        test_returns_true_on_single_pair,
        test_returns_true_on_multi_pair_same_dims,
        test_returns_true_when_input_dims_vary_but_output_constant,
        test_returns_false_on_varying_output_height,
        test_returns_false_on_varying_output_width,
        test_returns_false_on_varying_both_dims,
        test_returns_false_on_empty_pair_analyses,
        test_returns_false_on_missing_pair_analyses,
        test_returns_false_on_non_dict_patterns,
        test_returns_false_on_non_list_pair_analyses,
        test_returns_false_on_malformed_analysis_entry,
        test_returns_false_on_missing_output_height,
        test_returns_false_on_missing_output_width,
        test_returns_false_on_non_int_output_dims,
        test_returns_false_on_bool_output_dims,
        test_returns_false_on_zero_or_negative_output_dims,
        test_returns_false_when_one_pair_missing_dims_others_ok,
        test_is_side_effect_free_on_inputs,
        test_is_deterministic_across_repeats,
        test_co_fires_with_grid_size_changed_on_tile_style_task,
        test_can_co_fire_with_grid_size_preserved,
        test_orthogonal_to_output_color_uniform,
        test_orthogonal_to_output_color_uniform_independent_failure,
        test_identity_pairs_co_fire_with_output_dimensions_constant,
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
