"""
tests/test_multi_cell_change_group_per_pair.py -- exercise the iter-26
matcher ``agent.conditions.multi_cell_change_group_per_pair``.

Runs without pytest:

    python tests/test_multi_cell_change_group_per_pair.py

Dependency-free, same runner style as iters
1 / 8 / 10 / 13 / 17 / 18 / 19 / 20 / 22 / 23 / 24.

The matcher is a strict refinement of iter 23's
``single_change_group_per_pair`` AND the strict disjoint PARTNER of
iter 24's ``single_cell_change_per_pair``: it requires every pair to
have exactly one change group AND that group to have cell_count >= 2.
Together with iter 24, the two matchers partition iter 23's territory
on the cell-count axis with no overlap. Verifies cardinality range,
type strictness (bool subclass rejected on both ``num_groups`` and
``cell_count`` per ``validate_rule`` V1 posture), backwards-compatible
fail-closed on missing fields, mutual-exclusion / co-firing relations
with the 11 already-registered matchers, the strict-disjoint-from-iter-24
invariant, and end-to-end agreement with the live
``ExtractPatternOperator._analyze_pair`` output shape on a multi-cell
blob, single-cell point, two-blob, and zero-change region.
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


MATCHER_NAME = "multi_cell_change_group_per_pair"


def _matcher():
    return CONDITION_REGISTRY[MATCHER_NAME]


def _group(in_colors, out_colors, top_row=0, top_col=0, cell_count=4):
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
    # Adjacent invariant -- iter 26 must not displace iters
    # 1 / 8 / 10 / 13 / 17 / 18 / 19 / 20 / 22 / 23 / 24.
    for prior in ("grid_size_preserved", "consistent_color_mapping",
                  "sequential_recoloring", "identity_transformation",
                  "grid_size_changed", "output_color_uniform",
                  "input_color_uniform", "output_dimensions_constant",
                  "input_dimensions_constant",
                  "single_change_group_per_pair",
                  "single_cell_change_per_pair"):
        assert prior in CONDITION_REGISTRY, (
            f"prior matcher {prior!r} missing after iter-26 addition"
        )


def test_twelve_distinct_matchers_registered() -> None:
    # P5 unit-monotone counter -- there must be at least 12 entries now.
    assert len(CONDITION_REGISTRY) >= 12, (
        f"expected at least 12 entries, got {len(CONDITION_REGISTRY)}: "
        f"{sorted(CONDITION_REGISTRY)}"
    )


def test_matcher_is_callable() -> None:
    fn = _matcher()
    assert callable(fn), f"registered entry is not callable: {fn!r}"


def test_returns_true_on_single_pair_with_multi_cell_group() -> None:
    patterns = {"pair_analyses": [
        _analysis(groups=[_group([0], [3], cell_count=4)]),
    ]}
    assert _matcher()(patterns, {}) is True


def test_returns_true_on_two_cell_group() -> None:
    # Strict lower bound at 2: cell_count == 2 must fire (the boundary
    # between iter 24 territory and this matcher's territory).
    patterns = {"pair_analyses": [
        _analysis(groups=[_group([0], [3], cell_count=2)]),
    ]}
    assert _matcher()(patterns, {}) is True


def test_returns_true_on_multi_pair_with_multi_cell_groups_each() -> None:
    patterns = {"pair_analyses": [
        _analysis(groups=[_group([0], [3], cell_count=3)]),
        _analysis(groups=[_group([1], [4], cell_count=5)]),
        _analysis(groups=[_group([2], [5], cell_count=2)]),
    ]}
    assert _matcher()(patterns, {}) is True


def test_returns_false_on_single_group_single_cell() -> None:
    # Single cell single group: iter 24's territory, NOT this matcher's.
    # The strict-disjoint-partner boundary.
    patterns = {"pair_analyses": [
        _analysis(groups=[_group([0], [3], cell_count=1)]),
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
    # Multi-group: cardinality 2. Different recognition territory
    # (deferred multi-blob axis).
    patterns = {"pair_analyses": [
        _analysis(groups=[
            _group([0], [3], cell_count=4),
            _group([1], [4], top_row=1, cell_count=3),
        ]),
    ]}
    assert _matcher()(patterns, {}) is False


def test_returns_false_on_three_groups_per_pair() -> None:
    patterns = {"pair_analyses": [
        _analysis(groups=[
            _group([0], [3], cell_count=2),
            _group([1], [4], top_row=1, cell_count=2),
            _group([2], [5], top_row=2, cell_count=2),
        ]),
    ]}
    assert _matcher()(patterns, {}) is False


def test_returns_false_on_mixed_single_and_multi_cell() -> None:
    # Pair 0 has 1 group of 1 cell, pair 1 has 1 group of 5 cells.
    # The matcher requires ALL pairs to be multi-cell.
    patterns = {"pair_analyses": [
        _analysis(groups=[_group([0], [3], cell_count=1)]),
        _analysis(groups=[_group([0], [3], cell_count=5)]),
    ]}
    assert _matcher()(patterns, {}) is False


def test_returns_false_on_mixed_one_and_two_groups() -> None:
    # Strict-all-pairs contract: one pair has a different group cardinality.
    patterns = {"pair_analyses": [
        _analysis(groups=[_group([0], [3], cell_count=4)]),
        _analysis(groups=[
            _group([0], [3], cell_count=4),
            _group([1], [4], top_row=1, cell_count=2),
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
        "total_changes": 4,
        # num_groups missing
        "groups": [_group([0], [3], cell_count=4)],
        "size_match": True,
        "input_height": 3, "input_width": 3,
        "output_height": 3, "output_width": 3,
    }
    assert _matcher()({"pair_analyses": [analysis_missing]}, {}) is False


def test_returns_false_on_non_int_num_groups() -> None:
    for bad in (1.0, "1", None, [1], {"v": 1}):
        analysis = _analysis(groups=[_group([0], [3], cell_count=4)])
        analysis["num_groups"] = bad
        assert _matcher()({"pair_analyses": [analysis]}, {}) is False, (
            f"num_groups={bad!r} ({type(bad).__name__}) should fail-closed"
        )


def test_returns_false_on_bool_num_groups() -> None:
    # bool is a subclass of int in Python. Strict-type matchers (iters
    # 13 / 17 / 18 / 19 / 20 / 22 / 23 / 24 and validate_rule V1)
    # reject it -- the field is semantically an integer count, not a
    # Boolean flag.
    analysis = _analysis(groups=[_group([0], [3], cell_count=4)])
    analysis["num_groups"] = True  # truthy and == 1, but Boolean-typed
    assert _matcher()({"pair_analyses": [analysis]}, {}) is False
    analysis = _analysis(groups=[_group([0], [3], cell_count=4)])
    analysis["num_groups"] = False  # falsy, but Boolean-typed
    assert _matcher()({"pair_analyses": [analysis]}, {}) is False


def test_returns_false_on_negative_num_groups() -> None:
    for bad in (-1, -100):
        analysis = _analysis(groups=[_group([0], [3], cell_count=4)])
        analysis["num_groups"] = bad
        assert _matcher()({"pair_analyses": [analysis]}, {}) is False, (
            f"num_groups={bad} should fail-closed"
        )


def test_returns_false_on_missing_groups_list() -> None:
    # num_groups says 1 but the groups list is missing -- upstream
    # extractor breakage; fail closed rather than guess.
    analysis = {
        "total_changes": 4,
        "num_groups": 1,
        # groups missing
        "size_match": True,
        "input_height": 3, "input_width": 3,
        "output_height": 3, "output_width": 3,
    }
    assert _matcher()({"pair_analyses": [analysis]}, {}) is False


def test_returns_false_on_non_list_groups() -> None:
    analysis = _analysis(groups=[_group([0], [3], cell_count=4)])
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
    analysis = _analysis(groups=[_group([0], [3], cell_count=4)])
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
    analysis["num_groups"] = 1
    assert _matcher()({"pair_analyses": [analysis]}, {}) is False


def test_returns_false_on_non_int_cell_count() -> None:
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
    analysis["num_groups"] = 1
    assert _matcher()({"pair_analyses": [analysis]}, {}) is False
    group = _group([0], [3], cell_count=False)  # type: ignore[arg-type]
    analysis = _analysis(groups=[group])
    analysis["num_groups"] = 1
    assert _matcher()({"pair_analyses": [analysis]}, {}) is False


def test_returns_false_on_zero_cell_count() -> None:
    # cell_count == 0 is impossible from _analyze_pair (groups derive
    # from non-empty connected components) but a manually-crafted
    # patterns dict should still fail-closed.
    group = _group([0], [3], cell_count=0)
    analysis = _analysis(groups=[group])
    analysis["num_groups"] = 1
    assert _matcher()({"pair_analyses": [analysis]}, {}) is False


def test_returns_false_on_negative_cell_count() -> None:
    # Defensive: cell_count < 2 with negative value also fails closed.
    group = _group([0], [3], cell_count=-3)
    analysis = _analysis(groups=[group])
    analysis["num_groups"] = 1
    assert _matcher()({"pair_analyses": [analysis]}, {}) is False


def test_returns_false_when_one_pair_missing_num_groups() -> None:
    # Mixed shape: pair 0 carries num_groups, pair 1 does not.
    good = _analysis(groups=[_group([0], [3], cell_count=4)])
    bad = {
        "total_changes": 4,
        "groups": [_group([0], [3], cell_count=4)],
        "size_match": True,
        "input_height": 3, "input_width": 3,
        "output_height": 3, "output_width": 3,
    }
    assert _matcher()({"pair_analyses": [good, bad]}, {}) is False
    assert _matcher()({"pair_analyses": [bad, good]}, {}) is False


def test_is_side_effect_free_on_inputs() -> None:
    patterns = {"pair_analyses": [
        _analysis(groups=[_group([0], [3], cell_count=4)]),
        _analysis(groups=[_group([1], [4], cell_count=3)]),
    ]}
    params = {"unused": 1}
    before_p = copy.deepcopy(patterns)
    before_q = copy.deepcopy(params)
    _matcher()(patterns, params)
    assert patterns == before_p, "matcher mutated patterns"
    assert params == before_q, "matcher mutated params"


def test_is_deterministic_across_repeats() -> None:
    patterns = {"pair_analyses": [
        _analysis(groups=[_group([0], [3], cell_count=4)]),
        _analysis(groups=[_group([0], [3], cell_count=4)]),
    ]}
    results = [_matcher()(patterns, {}) for _ in range(5)]
    assert len(set(results)) == 1, f"non-deterministic outputs: {results}"


def test_mutually_exclusive_with_identity_transformation() -> None:
    # identity_transformation requires num_groups == 0 per pair;
    # this matcher requires num_groups == 1 AND cell_count >= 2.
    # Strict mutual exclusion on cardinality.
    identity_pat = {
        "grid_size_preserved": True,
        "pair_analyses": [
            _analysis(groups=[]),
            _analysis(groups=[]),
        ],
    }
    multi_cell_pat = {
        "grid_size_preserved": True,
        "pair_analyses": [
            _analysis(groups=[_group([0], [3], cell_count=4)]),
            _analysis(groups=[_group([0], [3], cell_count=4)]),
        ],
    }
    identity = CONDITION_REGISTRY["identity_transformation"]
    assert identity(identity_pat, {}) is True
    assert _matcher()(identity_pat, {}) is False
    assert identity(multi_cell_pat, {}) is False
    assert _matcher()(multi_cell_pat, {}) is True


def test_strictly_disjoint_from_iter_24_matcher() -> None:
    # No patterns dict may fire BOTH this matcher AND
    # single_cell_change_per_pair (iter 24). The two strictly partition
    # iter 23's territory on the cell-count axis.
    iter24 = CONDITION_REGISTRY["single_cell_change_per_pair"]

    # Multi-cell case: this matcher fires, iter 24 does NOT.
    multi_cell_pat = {"pair_analyses": [
        _analysis(groups=[_group([0], [3], cell_count=4)]),
        _analysis(groups=[_group([0], [3], cell_count=2)]),
    ]}
    assert _matcher()(multi_cell_pat, {}) is True
    assert iter24(multi_cell_pat, {}) is False

    # Single-cell case: iter 24 fires, this matcher does NOT.
    single_cell_pat = {"pair_analyses": [
        _analysis(groups=[_group([0], [3], cell_count=1)]),
        _analysis(groups=[_group([0], [3], cell_count=1)]),
    ]}
    assert _matcher()(single_cell_pat, {}) is False
    assert iter24(single_cell_pat, {}) is True

    # Mixed (one pair single-cell, one pair multi-cell): NEITHER fires
    # because both require strict-all-pairs.
    mixed_pat = {"pair_analyses": [
        _analysis(groups=[_group([0], [3], cell_count=1)]),
        _analysis(groups=[_group([0], [3], cell_count=4)]),
    ]}
    assert _matcher()(mixed_pat, {}) is False
    assert iter24(mixed_pat, {}) is False


def test_strict_refinement_of_iter23_matcher() -> None:
    # Every patterns dict that fires THIS matcher must also fire
    # single_change_group_per_pair (iter 23). The converse is NOT
    # true: a single 1-cell group fires iter 23 but not this matcher
    # (that case is iter 24's territory).
    iter23 = CONDITION_REGISTRY["single_change_group_per_pair"]

    # Positive case: both fire.
    multi_cell_pat = {"pair_analyses": [
        _analysis(groups=[_group([0], [3], cell_count=4)]),
    ]}
    assert iter23(multi_cell_pat, {}) is True
    assert _matcher()(multi_cell_pat, {}) is True

    # Counter-example case: iter 23 fires, this matcher does NOT.
    single_cell_pat = {"pair_analyses": [
        _analysis(groups=[_group([0], [3], cell_count=1)]),
    ]}
    assert iter23(single_cell_pat, {}) is True
    assert _matcher()(single_cell_pat, {}) is False


def test_iter24_plus_this_partition_iter23() -> None:
    # The union of this matcher's territory and iter 24's territory
    # equals iter 23's territory exactly. Verified by case enumeration
    # on cell_count values 1, 2, and 4 with num_groups == 1.
    iter23 = CONDITION_REGISTRY["single_change_group_per_pair"]
    iter24 = CONDITION_REGISTRY["single_cell_change_per_pair"]
    iter26 = _matcher()
    for cell_count in (1, 2, 4):
        patterns = {"pair_analyses": [
            _analysis(groups=[_group([0], [3], cell_count=cell_count)]),
        ]}
        # iter 23 fires for any of these (num_groups == 1).
        assert iter23(patterns, {}) is True, (
            f"iter 23 should fire on cell_count={cell_count}"
        )
        # Exactly ONE of iter 24 / iter 26 fires.
        fires_24 = iter24(patterns, {})
        fires_26 = iter26(patterns, {})
        assert fires_24 != fires_26, (
            f"iter 24 / iter 26 are not disjoint on cell_count={cell_count}: "
            f"iter24={fires_24}, iter26={fires_26}"
        )
        # And iter 24 fires iff cell_count == 1.
        assert fires_24 is (cell_count == 1)


def test_can_co_fire_with_output_color_uniform() -> None:
    # Multi-cell blob per pair AND every group's output colour is the
    # same constant K. The simplest "paint a single blob with K" rule
    # shape's recognition preconditions.
    patterns = {
        "pair_analyses": [
            _analysis(groups=[_group([0], [3], cell_count=4)]),
            _analysis(groups=[_group([1], [3], cell_count=3)]),
        ],
    }
    ocu = CONDITION_REGISTRY["output_color_uniform"]
    assert _matcher()(patterns, {}) is True
    assert ocu(patterns, {}) is True


def test_can_co_fire_with_input_color_uniform() -> None:
    # Multi-cell single-colour blob per pair.
    patterns = {
        "pair_analyses": [
            _analysis(groups=[_group([0], [3], cell_count=4)]),
            _analysis(groups=[_group([0], [4], cell_count=5)]),
        ],
    }
    icu = CONDITION_REGISTRY["input_color_uniform"]
    assert _matcher()(patterns, {}) is True
    assert icu(patterns, {}) is True


def test_can_co_fire_with_input_dimensions_constant() -> None:
    # Multi-cell blob AND input dimensions constant across pairs.
    patterns = {
        "pair_analyses": [
            _analysis(groups=[_group([0], [3], cell_count=4)],
                      input_height=5, input_width=5),
            _analysis(groups=[_group([1], [3], cell_count=4)],
                      input_height=5, input_width=5),
        ],
    }
    idc = CONDITION_REGISTRY["input_dimensions_constant"]
    assert _matcher()(patterns, {}) is True
    assert idc(patterns, {}) is True


def test_can_co_fire_with_grid_size_preserved() -> None:
    # Multi-cell blob on same-size pairs (the iter-25-deferred Option 2
    # recognition precondition stack).
    patterns = {
        "grid_size_preserved": True,
        "pair_analyses": [
            _analysis(groups=[_group([0], [3], cell_count=4)]),
            _analysis(groups=[_group([0], [3], cell_count=4)]),
        ],
    }
    gsp = CONDITION_REGISTRY["grid_size_preserved"]
    assert _matcher()(patterns, {}) is True
    assert gsp(patterns, {}) is True


def test_does_not_require_grid_size_preserved() -> None:
    # Multi-cell blob on dimension-changed pairs: this matcher fires
    # but grid_size_preserved does not. Non-refinement on the
    # dimensional axis.
    patterns = {
        "pair_analyses": [
            _analysis(groups=[_group([0], [3], cell_count=4)],
                      output_height=9, output_width=9,
                      size_match=False),
        ],
    }
    gsp = CONDITION_REGISTRY["grid_size_preserved"]
    assert _matcher()(patterns, {}) is True
    assert gsp(patterns, {}) is False


def test_end_to_end_agreement_with_extract_pattern_shape() -> None:
    # The shape ExtractPatternOperator._analyze_pair emits on a 2x2
    # connected change region on a 3x3 grid: num_groups should be 1
    # and the single group's cell_count should be 4.
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
    assert analysis["num_groups"] == 1, (
        f"live _analyze_pair produced num_groups={analysis['num_groups']}"
    )
    assert analysis["groups"][0]["cell_count"] == 4, (
        f"live _analyze_pair produced cell_count="
        f"{analysis['groups'][0]['cell_count']}"
    )
    patterns = {"pair_analyses": [analysis]}
    assert _matcher()(patterns, {}) is True


def test_end_to_end_disagreement_on_single_cell_point() -> None:
    # Live _analyze_pair on a single 1x1 change: num_groups is 1 but
    # cell_count is 1. Iter 24 fires, this matcher does NOT.
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
    assert analysis["num_groups"] == 1
    assert analysis["groups"][0]["cell_count"] == 1
    patterns = {"pair_analyses": [analysis]}
    iter24 = CONDITION_REGISTRY["single_cell_change_per_pair"]
    assert iter24(patterns, {}) is True
    assert _matcher()(patterns, {}) is False


def test_end_to_end_disagreement_on_two_blob_grid() -> None:
    # Two disjoint single-cell blobs: num_groups is 2. Neither iter 24
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
    assert _matcher()(patterns, {}) is False


def test_end_to_end_disagreement_on_zero_change_grid() -> None:
    # No changes: num_groups is 0. Neither iter 24 nor this matcher
    # fires (identity territory).
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
        [0, 0, 0],
        [0, 0, 0],
    ]
    analysis = op._analyze_pair(_Grid(raw_in), _Grid(raw_out))
    assert analysis["num_groups"] == 0
    patterns = {"pair_analyses": [analysis]}
    assert _matcher()(patterns, {}) is False


def test_returned_value_is_boolean_not_truthy() -> None:
    patterns_pos = {"pair_analyses": [
        _analysis(groups=[_group([0], [3], cell_count=4)]),
    ]}
    patterns_neg = {"pair_analyses": [
        _analysis(groups=[_group([0], [3], cell_count=1)]),
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
        test_twelve_distinct_matchers_registered,
        test_matcher_is_callable,
        test_returns_true_on_single_pair_with_multi_cell_group,
        test_returns_true_on_two_cell_group,
        test_returns_true_on_multi_pair_with_multi_cell_groups_each,
        test_returns_false_on_single_group_single_cell,
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
        test_returns_false_on_negative_cell_count,
        test_returns_false_when_one_pair_missing_num_groups,
        test_is_side_effect_free_on_inputs,
        test_is_deterministic_across_repeats,
        test_mutually_exclusive_with_identity_transformation,
        test_strictly_disjoint_from_iter_24_matcher,
        test_strict_refinement_of_iter23_matcher,
        test_iter24_plus_this_partition_iter23,
        test_can_co_fire_with_output_color_uniform,
        test_can_co_fire_with_input_color_uniform,
        test_can_co_fire_with_input_dimensions_constant,
        test_can_co_fire_with_grid_size_preserved,
        test_does_not_require_grid_size_preserved,
        test_end_to_end_agreement_with_extract_pattern_shape,
        test_end_to_end_disagreement_on_single_cell_point,
        test_end_to_end_disagreement_on_two_blob_grid,
        test_end_to_end_disagreement_on_zero_change_grid,
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
