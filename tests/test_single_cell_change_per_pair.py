"""
tests/test_single_cell_change_per_pair.py -- exercise the iter-24
matcher ``agent.conditions.single_cell_change_per_pair``.

Runs without pytest:

    python tests/test_single_cell_change_per_pair.py

Dependency-free, same runner style as iters
1 / 8 / 10 / 13 / 17 / 18 / 19 / 20 / 22 / 23.

The matcher is a strict refinement of iter 23's
``single_change_group_per_pair``: it additionally requires the single
change group to be a single-CELL group (the simplest selection-shape on
the cell-count sub-axis of group-count). Verifies cardinality, type
strictness (bool subclass rejected on both ``num_groups`` and
``cell_count`` per ``validate_rule`` V1 posture), backwards-compatible
fail-closed on missing fields, mutual-exclusion / co-firing relations
with the other 10 registered matchers, and end-to-end agreement with
the live ``ExtractPatternOperator._analyze_pair`` output shape on a
single-cell vs multi-cell vs multi-group change region.
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


MATCHER_NAME = "single_cell_change_per_pair"


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
    # Adjacent invariant -- iter 24 must not displace iters
    # 1 / 8 / 10 / 13 / 17 / 18 / 19 / 20 / 22 / 23.
    for prior in ("grid_size_preserved", "consistent_color_mapping",
                  "sequential_recoloring", "identity_transformation",
                  "grid_size_changed", "output_color_uniform",
                  "input_color_uniform", "output_dimensions_constant",
                  "input_dimensions_constant",
                  "single_change_group_per_pair"):
        assert prior in CONDITION_REGISTRY, (
            f"prior matcher {prior!r} missing after iter-24 addition"
        )


def test_eleven_distinct_matchers_registered() -> None:
    # P5 unit-monotone counter -- there must be at least 11 entries now.
    assert len(CONDITION_REGISTRY) >= 11, (
        f"expected at least 11 entries, got {len(CONDITION_REGISTRY)}: "
        f"{sorted(CONDITION_REGISTRY)}"
    )


def test_matcher_is_callable() -> None:
    fn = _matcher()
    assert callable(fn), f"registered entry is not callable: {fn!r}"


def test_returns_true_on_single_pair_with_one_single_cell_group() -> None:
    patterns = {"pair_analyses": [
        _analysis(groups=[_group([0], [3], cell_count=1)]),
    ]}
    assert _matcher()(patterns, {}) is True


def test_returns_true_on_multi_pair_with_single_cell_groups_each() -> None:
    patterns = {"pair_analyses": [
        _analysis(groups=[_group([0], [3], cell_count=1)]),
        _analysis(groups=[_group([1], [4], cell_count=1)]),
        _analysis(groups=[_group([2], [5], cell_count=1)]),
    ]}
    assert _matcher()(patterns, {}) is True


def test_returns_false_on_single_group_multi_cell() -> None:
    # Single connected blob of 4 cells: fires iter 23's matcher but
    # NOT this one. The strict refinement boundary on the cell-count
    # sub-axis.
    patterns = {"pair_analyses": [
        _analysis(groups=[_group([0], [3], cell_count=4)]),
    ]}
    assert _matcher()(patterns, {}) is False


def test_returns_false_on_zero_groups_per_pair() -> None:
    # Identity-style patterns: every pair has zero changes. The matcher
    # must NOT fire (identity territory).
    patterns = {"pair_analyses": [
        _analysis(groups=[]),
        _analysis(groups=[]),
    ]}
    assert _matcher()(patterns, {}) is False


def test_returns_false_on_two_groups_per_pair() -> None:
    # Multi-group: cardinality 2. Different recognition territory.
    patterns = {"pair_analyses": [
        _analysis(groups=[
            _group([0], [3], cell_count=1),
            _group([1], [4], top_row=1, cell_count=1),
        ]),
    ]}
    assert _matcher()(patterns, {}) is False


def test_returns_false_on_three_groups_per_pair() -> None:
    patterns = {"pair_analyses": [
        _analysis(groups=[
            _group([0], [3], cell_count=1),
            _group([1], [4], top_row=1, cell_count=1),
            _group([2], [5], top_row=2, cell_count=1),
        ]),
    ]}
    assert _matcher()(patterns, {}) is False


def test_returns_false_on_mixed_single_and_multi_cell() -> None:
    # Pair 0 has 1 group of 1 cell, pair 1 has 1 group of 5 cells.
    # The matcher requires ALL pairs to be single-cell.
    patterns = {"pair_analyses": [
        _analysis(groups=[_group([0], [3], cell_count=1)]),
        _analysis(groups=[_group([0], [3], cell_count=5)]),
    ]}
    assert _matcher()(patterns, {}) is False


def test_returns_false_on_mixed_one_and_two_groups() -> None:
    # Strict-all-pairs contract: one pair has a different group cardinality.
    patterns = {"pair_analyses": [
        _analysis(groups=[_group([0], [3], cell_count=1)]),
        _analysis(groups=[
            _group([0], [3], cell_count=1),
            _group([1], [4], top_row=1, cell_count=1),
        ]),
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
        "groups": [_group([0], [3], cell_count=1)],
        "size_match": True,
        "input_height": 3, "input_width": 3,
        "output_height": 3, "output_width": 3,
    }
    assert _matcher()({"pair_analyses": [analysis_missing]}, {}) is False


def test_returns_false_on_non_int_num_groups() -> None:
    for bad in (1.0, "1", None, [1], {"v": 1}):
        analysis = _analysis(groups=[_group([0], [3], cell_count=1)])
        analysis["num_groups"] = bad
        assert _matcher()({"pair_analyses": [analysis]}, {}) is False, (
            f"num_groups={bad!r} ({type(bad).__name__}) should fail-closed"
        )


def test_returns_false_on_bool_num_groups() -> None:
    # bool is a subclass of int in Python. Strict-type matchers (iters
    # 13 / 17 / 18 / 19 / 20 / 22 / 23 and validate_rule V1) reject it --
    # the field is semantically an integer count, not a Boolean flag.
    analysis = _analysis(groups=[_group([0], [3], cell_count=1)])
    analysis["num_groups"] = True  # truthy and == 1, but Boolean-typed
    assert _matcher()({"pair_analyses": [analysis]}, {}) is False
    analysis = _analysis(groups=[_group([0], [3], cell_count=1)])
    analysis["num_groups"] = False  # falsy, but Boolean-typed
    assert _matcher()({"pair_analyses": [analysis]}, {}) is False


def test_returns_false_on_negative_num_groups() -> None:
    for bad in (-1, -100):
        analysis = _analysis(groups=[_group([0], [3], cell_count=1)])
        analysis["num_groups"] = bad
        assert _matcher()({"pair_analyses": [analysis]}, {}) is False, (
            f"num_groups={bad} should fail-closed"
        )


def test_returns_false_on_missing_groups_list() -> None:
    # num_groups says 1 but the groups list is missing -- upstream
    # extractor breakage; fail closed rather than guess.
    analysis = {
        "total_changes": 1,
        "num_groups": 1,
        # groups missing
        "size_match": True,
        "input_height": 3, "input_width": 3,
        "output_height": 3, "output_width": 3,
    }
    assert _matcher()({"pair_analyses": [analysis]}, {}) is False


def test_returns_false_on_non_list_groups() -> None:
    analysis = _analysis(groups=[_group([0], [3], cell_count=1)])
    analysis["groups"] = "not-a-list"
    assert _matcher()({"pair_analyses": [analysis]}, {}) is False


def test_returns_false_on_empty_groups_list_with_num_groups_one() -> None:
    # num_groups=1 says one group, but groups list is empty.
    # Inconsistent shape -- the matcher reads from groups[0], so it
    # must fail closed rather than IndexError.
    analysis = _analysis(groups=[])
    analysis["num_groups"] = 1  # falsified scalar
    assert _matcher()({"pair_analyses": [analysis]}, {}) is False


def test_returns_false_on_non_dict_group() -> None:
    analysis = _analysis(groups=[_group([0], [3], cell_count=1)])
    analysis["groups"] = [None]
    assert _matcher()({"pair_analyses": [analysis]}, {}) is False
    analysis["groups"] = ["not-a-dict"]
    assert _matcher()({"pair_analyses": [analysis]}, {}) is False


def test_returns_false_on_missing_cell_count() -> None:
    group_no_cells = {
        "input_colors": [0],
        "output_colors": [3],
        "top_row": 0,
        "top_col": 0,
        # cell_count missing
    }
    analysis = _analysis(groups=[group_no_cells])
    assert _matcher()({"pair_analyses": [analysis]}, {}) is False


def test_returns_false_on_non_int_cell_count() -> None:
    # _analysis() sums cell_counts for total_changes, which would itself
    # raise on a non-int; build the analysis dict directly to isolate
    # the matcher's behaviour from the helper.
    for bad in (1.0, "1", None, [1], {"v": 1}):
        group = _group([0], [3], cell_count=bad)  # type: ignore[arg-type]
        analysis = {
            "total_changes": 1,
            "num_groups": 1,
            "groups": [group],
            "size_match": True,
            "input_height": 3, "input_width": 3,
            "output_height": 3, "output_width": 3,
        }
        assert _matcher()({"pair_analyses": [analysis]}, {}) is False, (
            f"cell_count={bad!r} ({type(bad).__name__}) should fail-closed"
        )


def test_returns_false_on_bool_cell_count() -> None:
    # Same strict-type posture as num_groups: bool subclass rejected.
    group = _group([0], [3], cell_count=True)  # type: ignore[arg-type]
    analysis = _analysis(groups=[group])
    assert _matcher()({"pair_analyses": [analysis]}, {}) is False
    group = _group([0], [3], cell_count=False)  # type: ignore[arg-type]
    analysis = _analysis(groups=[group])
    assert _matcher()({"pair_analyses": [analysis]}, {}) is False


def test_returns_false_on_zero_cell_count() -> None:
    # cell_count == 0 is impossible from _analyze_pair (groups derive
    # from non-empty connected components) but a manually-crafted
    # patterns dict should still fail-closed.
    group = _group([0], [3], cell_count=0)
    analysis = _analysis(groups=[group])
    assert _matcher()({"pair_analyses": [analysis]}, {}) is False


def test_returns_false_when_one_pair_missing_num_groups() -> None:
    # Mixed shape: pair 0 carries num_groups, pair 1 does not.
    good = _analysis(groups=[_group([0], [3], cell_count=1)])
    bad = {
        "total_changes": 1,
        "groups": [_group([0], [3], cell_count=1)],
        "size_match": True,
        "input_height": 3, "input_width": 3,
        "output_height": 3, "output_width": 3,
    }
    assert _matcher()({"pair_analyses": [good, bad]}, {}) is False
    assert _matcher()({"pair_analyses": [bad, good]}, {}) is False


def test_is_side_effect_free_on_inputs() -> None:
    patterns = {"pair_analyses": [
        _analysis(groups=[_group([0], [3], cell_count=1)]),
        _analysis(groups=[_group([1], [4], cell_count=1)]),
    ]}
    params = {"unused": 1}
    before_p = copy.deepcopy(patterns)
    before_q = copy.deepcopy(params)
    _matcher()(patterns, params)
    assert patterns == before_p, "matcher mutated patterns"
    assert params == before_q, "matcher mutated params"


def test_is_deterministic_across_repeats() -> None:
    patterns = {"pair_analyses": [
        _analysis(groups=[_group([0], [3], cell_count=1)]),
        _analysis(groups=[_group([0], [3], cell_count=1)]),
    ]}
    results = [_matcher()(patterns, {}) for _ in range(5)]
    assert len(set(results)) == 1, f"non-deterministic outputs: {results}"


def test_mutually_exclusive_with_identity_transformation() -> None:
    # identity_transformation requires num_groups == 0 per pair;
    # this matcher requires num_groups == 1 AND cell_count == 1.
    # Strict mutual exclusion on cardinality.
    identity_pat = {
        "grid_size_preserved": True,
        "pair_analyses": [
            _analysis(groups=[]),
            _analysis(groups=[]),
        ],
    }
    single_cell_pat = {
        "grid_size_preserved": True,
        "pair_analyses": [
            _analysis(groups=[_group([0], [3], cell_count=1)]),
            _analysis(groups=[_group([0], [3], cell_count=1)]),
        ],
    }
    identity = CONDITION_REGISTRY["identity_transformation"]
    assert identity(identity_pat, {}) is True
    assert _matcher()(identity_pat, {}) is False
    assert identity(single_cell_pat, {}) is False
    assert _matcher()(single_cell_pat, {}) is True


def test_strict_refinement_of_iter23_matcher() -> None:
    # Every patterns dict that fires THIS matcher must also fire
    # single_change_group_per_pair (iter 23). The converse is NOT
    # true: a single 4-cell blob fires iter 23 but not this matcher.
    iter23 = CONDITION_REGISTRY["single_change_group_per_pair"]

    # Positive case: both fire.
    single_cell_pat = {"pair_analyses": [
        _analysis(groups=[_group([0], [3], cell_count=1)]),
    ]}
    assert iter23(single_cell_pat, {}) is True
    assert _matcher()(single_cell_pat, {}) is True

    # Counter-example case: iter 23 fires, this matcher does NOT.
    single_blob_pat = {"pair_analyses": [
        _analysis(groups=[_group([0], [3], cell_count=4)]),
    ]}
    assert iter23(single_blob_pat, {}) is True
    assert _matcher()(single_blob_pat, {}) is False


def test_can_co_fire_with_output_color_uniform() -> None:
    # Single cell per pair AND every group's output colour is the same
    # constant K. The simplest "paint a single cell at (r,c) with K"
    # rule shape's recognition preconditions all fire.
    patterns = {
        "pair_analyses": [
            _analysis(groups=[_group([0], [3], cell_count=1)]),
            _analysis(groups=[_group([1], [3], cell_count=1)]),
        ],
    }
    ocu = CONDITION_REGISTRY["output_color_uniform"]
    assert _matcher()(patterns, {}) is True
    assert ocu(patterns, {}) is True


def test_can_co_fire_with_input_color_uniform() -> None:
    # Single cell per pair AND every group's input colour is the same
    # constant C.
    patterns = {
        "pair_analyses": [
            _analysis(groups=[_group([0], [3], cell_count=1)]),
            _analysis(groups=[_group([0], [4], cell_count=1)]),
        ],
    }
    icu = CONDITION_REGISTRY["input_color_uniform"]
    assert _matcher()(patterns, {}) is True
    assert icu(patterns, {}) is True


def test_can_co_fire_with_input_dimensions_constant() -> None:
    # Single cell AND input dimensions constant across pairs -- the
    # literal-coord precondition combination (the coord (top_row,
    # top_col) extracted at emission time is in-bounds for any test
    # input of the pinned dimensions).
    patterns = {
        "pair_analyses": [
            _analysis(groups=[_group([0], [3], cell_count=1)],
                      input_height=4, input_width=4),
            _analysis(groups=[_group([1], [3], cell_count=1)],
                      input_height=4, input_width=4),
        ],
    }
    idc = CONDITION_REGISTRY["input_dimensions_constant"]
    assert _matcher()(patterns, {}) is True
    assert idc(patterns, {}) is True


def test_can_co_fire_with_grid_size_preserved() -> None:
    # Single cell on same-size pairs.
    patterns = {
        "grid_size_preserved": True,
        "pair_analyses": [
            _analysis(groups=[_group([0], [3], cell_count=1)]),
            _analysis(groups=[_group([0], [3], cell_count=1)]),
        ],
    }
    gsp = CONDITION_REGISTRY["grid_size_preserved"]
    assert _matcher()(patterns, {}) is True
    assert gsp(patterns, {}) is True


def test_does_not_require_grid_size_preserved() -> None:
    # Single cell on dimension-changed pairs: this matcher fires but
    # grid_size_preserved does not. Non-refinement on the dimensional axis.
    patterns = {
        "pair_analyses": [
            _analysis(groups=[_group([0], [3], cell_count=1)],
                      output_height=9, output_width=9,
                      size_match=False),
        ],
    }
    gsp = CONDITION_REGISTRY["grid_size_preserved"]
    assert _matcher()(patterns, {}) is True
    assert gsp(patterns, {}) is False


def test_end_to_end_agreement_with_extract_pattern_shape() -> None:
    # The shape ExtractPatternOperator._analyze_pair emits: a single
    # changed cell at (1, 1) on a 3x3 grid. num_groups should be 1
    # and the single group's cell_count should be 1.
    from agent.active_operators import ExtractPatternOperator  # noqa: E402

    op = ExtractPatternOperator()

    class _Grid:
        def __init__(self, raw):
            self.raw = raw
            self.height = len(raw)
            self.width = len(raw[0]) if raw else 0

    raw_in = [
        [0, 0, 0],
        [0, 0, 0],
        [0, 0, 0],
    ]
    raw_out = [
        [0, 0, 0],
        [0, 3, 0],
        [0, 0, 0],
    ]
    analysis = op._analyze_pair(_Grid(raw_in), _Grid(raw_out))
    assert analysis["num_groups"] == 1, (
        f"live _analyze_pair produced num_groups={analysis['num_groups']}"
    )
    assert analysis["groups"][0]["cell_count"] == 1, (
        f"live _analyze_pair produced cell_count="
        f"{analysis['groups'][0]['cell_count']}"
    )
    # And the (top_row, top_col) IS the cell's coord (1, 1) -- this is
    # the property the emission iter will rely on.
    assert analysis["groups"][0]["top_row"] == 1
    assert analysis["groups"][0]["top_col"] == 1
    patterns = {"pair_analyses": [analysis]}
    assert _matcher()(patterns, {}) is True


def test_end_to_end_disagreement_on_multi_cell_blob() -> None:
    # Live _analyze_pair on a 2x2 connected change region: num_groups
    # is 1 (single blob), but cell_count is 4. Iter 23 fires, this
    # matcher does NOT.
    from agent.active_operators import ExtractPatternOperator  # noqa: E402

    op = ExtractPatternOperator()

    class _Grid:
        def __init__(self, raw):
            self.raw = raw
            self.height = len(raw)
            self.width = len(raw[0]) if raw else 0

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
    analysis = op._analyze_pair(_Grid(raw_in), _Grid(raw_out))
    assert analysis["num_groups"] == 1
    assert analysis["groups"][0]["cell_count"] == 4
    patterns = {"pair_analyses": [analysis]}
    iter23 = CONDITION_REGISTRY["single_change_group_per_pair"]
    assert iter23(patterns, {}) is True
    assert _matcher()(patterns, {}) is False


def test_end_to_end_disagreement_on_two_blob_grid() -> None:
    # Two disjoint single-cell blobs: num_groups is 2. Neither iter 23
    # nor this matcher fires.
    from agent.active_operators import ExtractPatternOperator  # noqa: E402

    op = ExtractPatternOperator()

    class _Grid:
        def __init__(self, raw):
            self.raw = raw
            self.height = len(raw)
            self.width = len(raw[0]) if raw else 0

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
    assert analysis["num_groups"] == 2
    patterns = {"pair_analyses": [analysis]}
    iter23 = CONDITION_REGISTRY["single_change_group_per_pair"]
    assert iter23(patterns, {}) is False
    assert _matcher()(patterns, {}) is False


def test_returned_value_is_boolean_not_truthy() -> None:
    patterns_pos = {"pair_analyses": [
        _analysis(groups=[_group([0], [3], cell_count=1)]),
    ]}
    patterns_neg = {"pair_analyses": [
        _analysis(groups=[_group([0], [3], cell_count=4)]),
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
        test_eleven_distinct_matchers_registered,
        test_matcher_is_callable,
        test_returns_true_on_single_pair_with_one_single_cell_group,
        test_returns_true_on_multi_pair_with_single_cell_groups_each,
        test_returns_false_on_single_group_multi_cell,
        test_returns_false_on_zero_groups_per_pair,
        test_returns_false_on_two_groups_per_pair,
        test_returns_false_on_three_groups_per_pair,
        test_returns_false_on_mixed_single_and_multi_cell,
        test_returns_false_on_mixed_one_and_two_groups,
        test_returns_false_on_empty_pair_analyses,
        test_returns_false_on_missing_pair_analyses,
        test_returns_false_on_non_dict_patterns,
        test_returns_false_on_non_list_pair_analyses,
        test_returns_false_on_malformed_analysis_entry,
        test_returns_false_on_missing_num_groups,
        test_returns_false_on_non_int_num_groups,
        test_returns_false_on_bool_num_groups,
        test_returns_false_on_negative_num_groups,
        test_returns_false_on_missing_groups_list,
        test_returns_false_on_non_list_groups,
        test_returns_false_on_empty_groups_list_with_num_groups_one,
        test_returns_false_on_non_dict_group,
        test_returns_false_on_missing_cell_count,
        test_returns_false_on_non_int_cell_count,
        test_returns_false_on_bool_cell_count,
        test_returns_false_on_zero_cell_count,
        test_returns_false_when_one_pair_missing_num_groups,
        test_is_side_effect_free_on_inputs,
        test_is_deterministic_across_repeats,
        test_mutually_exclusive_with_identity_transformation,
        test_strict_refinement_of_iter23_matcher,
        test_can_co_fire_with_output_color_uniform,
        test_can_co_fire_with_input_color_uniform,
        test_can_co_fire_with_input_dimensions_constant,
        test_can_co_fire_with_grid_size_preserved,
        test_does_not_require_grid_size_preserved,
        test_end_to_end_agreement_with_extract_pattern_shape,
        test_end_to_end_disagreement_on_multi_cell_blob,
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
