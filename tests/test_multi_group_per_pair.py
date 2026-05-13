"""
tests/test_multi_group_per_pair.py -- exercise the iter-28 matcher
``agent.conditions.multi_group_per_pair``.

Runs without pytest:

    python tests/test_multi_group_per_pair.py

Dependency-free, same runner style as iters
1 / 8 / 10 / 13 / 17 / 18 / 19 / 20 / 22 / 23 / 24 / 26.

The matcher is the strict disjoint partner of iters 13 / 23 on the
group-count axis: it requires every pair to have ``num_groups >= 2``.
Together with iter 13 (``num_groups == 0``) and iter 23
(``num_groups == 1``) the three matchers partition the per-pair
group-count axis into exactly three disjoint regimes. Verifies
cardinality range, type strictness (bool subclass rejected on
``num_groups`` per ``validate_rule`` V1 posture), fail-closed on
missing field, mutual-exclusion / co-firing relations with the 12
already-registered matchers, the partition invariant against iters
13 + 23, and end-to-end agreement with the live
``ExtractPatternOperator._analyze_pair`` output shape on a two-blob,
three-blob, single-blob, and zero-change region.
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


MATCHER_NAME = "multi_group_per_pair"


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
    # Adjacent invariant -- iter 28 must not displace iters
    # 1 / 8 / 10 / 13 / 17 / 18 / 19 / 20 / 22 / 23 / 24 / 26.
    for prior in ("grid_size_preserved", "consistent_color_mapping",
                  "sequential_recoloring", "identity_transformation",
                  "grid_size_changed", "output_color_uniform",
                  "input_color_uniform", "output_dimensions_constant",
                  "input_dimensions_constant",
                  "single_change_group_per_pair",
                  "single_cell_change_per_pair",
                  "multi_cell_change_group_per_pair"):
        assert prior in CONDITION_REGISTRY, (
            f"prior matcher {prior!r} missing after iter-28 addition"
        )


def test_thirteen_distinct_matchers_registered() -> None:
    # P5 unit-monotone counter -- there must be at least 13 entries now.
    assert len(CONDITION_REGISTRY) >= 13, (
        f"expected at least 13 entries, got {len(CONDITION_REGISTRY)}: "
        f"{sorted(CONDITION_REGISTRY)}"
    )


def test_matcher_is_callable() -> None:
    fn = _matcher()
    assert callable(fn), f"registered entry is not callable: {fn!r}"


def test_returns_true_on_single_pair_with_two_groups() -> None:
    patterns = {"pair_analyses": [
        _analysis(groups=[
            _group([0], [3], top_row=0, top_col=0, cell_count=1),
            _group([1], [4], top_row=2, top_col=2, cell_count=1),
        ]),
    ]}
    assert _matcher()(patterns, {}) is True


def test_returns_true_on_two_groups_boundary() -> None:
    # Strict lower bound at 2: num_groups == 2 must fire (the boundary
    # between iter 23 territory and this matcher's territory).
    patterns = {"pair_analyses": [
        _analysis(groups=[
            _group([0], [3], top_row=0, top_col=0),
            _group([1], [4], top_row=1, top_col=1),
        ]),
    ]}
    assert _matcher()(patterns, {}) is True


def test_returns_true_on_three_groups() -> None:
    patterns = {"pair_analyses": [
        _analysis(groups=[
            _group([0], [3], top_row=0, top_col=0),
            _group([1], [4], top_row=1, top_col=1),
            _group([2], [5], top_row=2, top_col=2),
        ]),
    ]}
    assert _matcher()(patterns, {}) is True


def test_returns_true_on_multi_pair_with_varying_blob_counts() -> None:
    # The matcher requires num_groups >= 2 PER PAIR, but does NOT
    # require the same N across pairs (iter 10 is the strict-equal-N
    # matcher).
    patterns = {"pair_analyses": [
        _analysis(groups=[
            _group([0], [3]), _group([1], [4]),
        ]),
        _analysis(groups=[
            _group([0], [3]), _group([1], [4]),
            _group([2], [5]), _group([6], [7]),
        ]),
        _analysis(groups=[
            _group([0], [3]), _group([1], [4]), _group([2], [5]),
        ]),
    ]}
    assert _matcher()(patterns, {}) is True


def test_returns_false_on_zero_groups_per_pair() -> None:
    # Identity-style patterns: every pair has zero changes. Iter 13
    # territory, NOT this matcher's.
    patterns = {"pair_analyses": [
        _analysis(groups=[]),
        _analysis(groups=[]),
    ]}
    assert _matcher()(patterns, {}) is False


def test_returns_false_on_single_group_per_pair() -> None:
    # Iter 23 territory, NOT this matcher's. The strict disjoint partner
    # boundary on the group-count axis.
    patterns = {"pair_analyses": [
        _analysis(groups=[_group([0], [3])]),
        _analysis(groups=[_group([0], [3])]),
    ]}
    assert _matcher()(patterns, {}) is False


def test_returns_false_on_mixed_single_and_multi_group() -> None:
    # Pair 0 has 1 group, pair 1 has 2. The matcher requires ALL pairs
    # to be multi-group (strict-all-pairs contract).
    patterns = {"pair_analyses": [
        _analysis(groups=[_group([0], [3])]),
        _analysis(groups=[_group([0], [3]), _group([1], [4])]),
    ]}
    assert _matcher()(patterns, {}) is False


def test_returns_false_on_mixed_zero_and_multi_group() -> None:
    # Pair 0 has 0 groups (identity), pair 1 has 2. Strict-all-pairs.
    patterns = {"pair_analyses": [
        _analysis(groups=[]),
        _analysis(groups=[_group([0], [3]), _group([1], [4])]),
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
        "total_changes": 2,
        # num_groups missing
        "groups": [_group([0], [3]), _group([1], [4])],
        "size_match": True,
        "input_height": 3, "input_width": 3,
        "output_height": 3, "output_width": 3,
    }
    assert _matcher()({"pair_analyses": [analysis_missing]}, {}) is False


def test_returns_false_on_non_int_num_groups() -> None:
    for bad in (2.0, "2", None, [2], {"v": 2}):
        analysis = _analysis(groups=[_group([0], [3]), _group([1], [4])])
        analysis["num_groups"] = bad
        assert _matcher()({"pair_analyses": [analysis]}, {}) is False, (
            f"num_groups={bad!r} ({type(bad).__name__}) should fail-closed"
        )


def test_returns_false_on_bool_num_groups() -> None:
    # bool is a subclass of int in Python. Strict-type matchers (iters
    # 13 / 17 / 18 / 19 / 20 / 22 / 23 / 24 / 26 and validate_rule V1)
    # reject it -- the field is semantically an integer count, not a
    # Boolean flag.
    analysis = _analysis(groups=[_group([0], [3]), _group([1], [4])])
    analysis["num_groups"] = True   # truthy and == 1
    assert _matcher()({"pair_analyses": [analysis]}, {}) is False
    analysis = _analysis(groups=[_group([0], [3]), _group([1], [4])])
    analysis["num_groups"] = False  # falsy, == 0
    assert _matcher()({"pair_analyses": [analysis]}, {}) is False


def test_returns_false_on_negative_num_groups() -> None:
    for bad in (-1, -100):
        analysis = _analysis(groups=[_group([0], [3]), _group([1], [4])])
        analysis["num_groups"] = bad
        assert _matcher()({"pair_analyses": [analysis]}, {}) is False, (
            f"num_groups={bad} should fail-closed"
        )


def test_returns_false_on_one_num_groups_exactly() -> None:
    # The strict lower bound: num_groups == 1 must NOT fire (that is
    # iter 23's territory). Boundary test on the disjoint-partner edge.
    analysis = _analysis(groups=[_group([0], [3])])
    analysis["num_groups"] = 1
    assert _matcher()({"pair_analyses": [analysis]}, {}) is False


def test_returns_false_on_zero_num_groups_exactly() -> None:
    # The other strict edge: num_groups == 0 must NOT fire (iter 13's
    # territory).
    analysis = _analysis(groups=[])
    analysis["num_groups"] = 0
    assert _matcher()({"pair_analyses": [analysis]}, {}) is False


def test_returns_false_when_one_pair_missing_num_groups() -> None:
    # Mixed shape: pair 0 carries num_groups, pair 1 does not.
    good = _analysis(groups=[_group([0], [3]), _group([1], [4])])
    bad = {
        "total_changes": 2,
        "groups": [_group([0], [3]), _group([1], [4])],
        "size_match": True,
        "input_height": 3, "input_width": 3,
        "output_height": 3, "output_width": 3,
    }
    assert _matcher()({"pair_analyses": [good, bad]}, {}) is False
    assert _matcher()({"pair_analyses": [bad, good]}, {}) is False


def test_is_side_effect_free_on_inputs() -> None:
    patterns = {"pair_analyses": [
        _analysis(groups=[_group([0], [3]), _group([1], [4])]),
        _analysis(groups=[_group([0], [3]), _group([2], [5])]),
    ]}
    params = {"unused": 1}
    before_p = copy.deepcopy(patterns)
    before_q = copy.deepcopy(params)
    _matcher()(patterns, params)
    assert patterns == before_p, "matcher mutated patterns"
    assert params == before_q, "matcher mutated params"


def test_is_deterministic_across_repeats() -> None:
    patterns = {"pair_analyses": [
        _analysis(groups=[_group([0], [3]), _group([1], [4])]),
        _analysis(groups=[_group([0], [3]), _group([1], [4])]),
    ]}
    results = [_matcher()(patterns, {}) for _ in range(5)]
    assert len(set(results)) == 1, f"non-deterministic outputs: {results}"


def test_mutually_exclusive_with_identity_transformation() -> None:
    # identity_transformation requires num_groups == 0 per pair;
    # this matcher requires num_groups >= 2. Strict mutual exclusion on
    # cardinality.
    identity_pat = {
        "grid_size_preserved": True,
        "pair_analyses": [
            _analysis(groups=[]),
            _analysis(groups=[]),
        ],
    }
    multi_pat = {
        "grid_size_preserved": True,
        "pair_analyses": [
            _analysis(groups=[_group([0], [3]), _group([1], [4])]),
            _analysis(groups=[_group([0], [3]), _group([1], [4])]),
        ],
    }
    identity = CONDITION_REGISTRY["identity_transformation"]
    assert identity(identity_pat, {}) is True
    assert _matcher()(identity_pat, {}) is False
    assert identity(multi_pat, {}) is False
    assert _matcher()(multi_pat, {}) is True


def test_strictly_disjoint_from_iter_23_matcher() -> None:
    # No patterns dict may fire BOTH this matcher AND
    # single_change_group_per_pair (iter 23). The two strictly
    # partition the >=1-group territory on the group-count axis.
    iter23 = CONDITION_REGISTRY["single_change_group_per_pair"]

    # Multi-group case: this matcher fires, iter 23 does NOT.
    multi_pat = {"pair_analyses": [
        _analysis(groups=[_group([0], [3]), _group([1], [4])]),
        _analysis(groups=[_group([0], [3]), _group([1], [4])]),
    ]}
    assert _matcher()(multi_pat, {}) is True
    assert iter23(multi_pat, {}) is False

    # Single-group case: iter 23 fires, this matcher does NOT.
    single_pat = {"pair_analyses": [
        _analysis(groups=[_group([0], [3])]),
        _analysis(groups=[_group([0], [3])]),
    ]}
    assert _matcher()(single_pat, {}) is False
    assert iter23(single_pat, {}) is True

    # Mixed (one pair single, one pair multi): NEITHER fires because
    # both require strict-all-pairs.
    mixed_pat = {"pair_analyses": [
        _analysis(groups=[_group([0], [3])]),
        _analysis(groups=[_group([0], [3]), _group([1], [4])]),
    ]}
    assert _matcher()(mixed_pat, {}) is False
    assert iter23(mixed_pat, {}) is False


def test_three_matchers_partition_group_count_axis() -> None:
    # The union of iter 13 + iter 23 + this matcher's territory equals
    # every patterns dict's group-count range, and they are pairwise
    # disjoint. Verified by case enumeration on num_groups values 0,
    # 1, 2, and 4 with strict-all-pairs.
    iter13 = CONDITION_REGISTRY["identity_transformation"]
    iter23 = CONDITION_REGISTRY["single_change_group_per_pair"]
    iter28 = _matcher()
    cases = [
        (0, []),
        (1, [_group([0], [3])]),
        (2, [_group([0], [3]), _group([1], [4])]),
        (4, [_group([0], [3]), _group([1], [4]),
             _group([2], [5]), _group([6], [7])]),
    ]
    for num_groups, groups in cases:
        patterns = {"pair_analyses": [
            _analysis(groups=groups),
        ]}
        fires_13 = iter13(patterns, {})
        fires_23 = iter23(patterns, {})
        fires_28 = iter28(patterns, {})
        # Pairwise disjoint.
        assert sum([fires_13, fires_23, fires_28]) <= 1, (
            f"non-disjoint matchers at num_groups={num_groups}: "
            f"iter13={fires_13}, iter23={fires_23}, iter28={fires_28}"
        )
        # Coverage: at least one fires for every well-formed case --
        # but only for the same-size case (iter 13 requires
        # size_match=True per pair, which the default _analysis
        # builder produces).
        assert (fires_13 or fires_23 or fires_28), (
            f"no matcher fires at num_groups={num_groups} -- partition incomplete"
        )
        # Specific expectations.
        assert fires_13 is (num_groups == 0)
        assert fires_23 is (num_groups == 1)
        assert fires_28 is (num_groups >= 2)


def test_strictly_disjoint_from_iter_24_matcher() -> None:
    # iter 24 requires num_groups == 1 AND cell_count == 1. The
    # group-count clause alone forecloses any co-firing with this
    # matcher (which requires num_groups >= 2). Iter 24 sits inside
    # iter 23's territory on the cell-count sub-axis; this matcher
    # is outside iter 23's territory entirely.
    iter24 = CONDITION_REGISTRY["single_cell_change_per_pair"]

    multi_pat = {"pair_analyses": [
        _analysis(groups=[_group([0], [3]), _group([1], [4])]),
        _analysis(groups=[_group([0], [3]), _group([1], [4])]),
    ]}
    assert _matcher()(multi_pat, {}) is True
    assert iter24(multi_pat, {}) is False


def test_strictly_disjoint_from_iter_26_matcher() -> None:
    # iter 26 requires num_groups == 1 AND cell_count >= 2. Same
    # group-count-clause argument as iter 24: the cardinality 1 vs
    # >= 2 partition forecloses co-firing.
    iter26 = CONDITION_REGISTRY["multi_cell_change_group_per_pair"]

    multi_pat = {"pair_analyses": [
        _analysis(groups=[_group([0], [3], cell_count=3),
                          _group([1], [4], cell_count=2)]),
        _analysis(groups=[_group([0], [3], cell_count=4),
                          _group([1], [4], cell_count=2)]),
    ]}
    assert _matcher()(multi_pat, {}) is True
    assert iter26(multi_pat, {}) is False

    # Iter 26 fires on single multi-cell blob; this matcher does NOT.
    single_blob_pat = {"pair_analyses": [
        _analysis(groups=[_group([0], [3], cell_count=4)]),
        _analysis(groups=[_group([0], [3], cell_count=4)]),
    ]}
    assert _matcher()(single_blob_pat, {}) is False
    assert iter26(single_blob_pat, {}) is True


def test_can_co_fire_with_output_color_uniform() -> None:
    # Multi-blob per pair AND every group's output colour is the same
    # constant K. The simplest "paint multiple blobs with uniform K"
    # recognition stack -- the future multi-blob uniform-paint
    # emission's recognition preconditions.
    patterns = {
        "pair_analyses": [
            _analysis(groups=[_group([0], [3]), _group([1], [3])]),
            _analysis(groups=[_group([0], [3]), _group([2], [3])]),
        ],
    }
    ocu = CONDITION_REGISTRY["output_color_uniform"]
    assert _matcher()(patterns, {}) is True
    assert ocu(patterns, {}) is True


def test_can_co_fire_with_input_color_uniform() -> None:
    # Multi-blob single-input-colour pairs.
    patterns = {
        "pair_analyses": [
            _analysis(groups=[_group([0], [3]), _group([0], [4])]),
            _analysis(groups=[_group([0], [5]), _group([0], [6])]),
        ],
    }
    icu = CONDITION_REGISTRY["input_color_uniform"]
    assert _matcher()(patterns, {}) is True
    assert icu(patterns, {}) is True


def test_can_co_fire_with_consistent_color_mapping() -> None:
    # Multi-blob pairs where every group's (in -> out) mapping is the
    # same 0 -> 3 across all groups in all pairs. iter 8 fires
    # because a single input maps to a single output; this matcher
    # fires because num_groups >= 2 per pair.
    patterns = {
        "pair_analyses": [
            _analysis(groups=[_group([0], [3]), _group([0], [3])]),
            _analysis(groups=[_group([0], [3]), _group([0], [3])]),
        ],
    }
    ccm = CONDITION_REGISTRY["consistent_color_mapping"]
    assert _matcher()(patterns, {}) is True
    assert ccm(patterns, {}) is True


def test_can_co_fire_with_sequential_recoloring() -> None:
    # Constant per-pair N >= 2 with contiguous output range fires
    # BOTH iter 10 and this matcher. Iter 10 sits inside the >= 2
    # territory; the two co-fire only when iter 10's stricter
    # contiguity contract is also satisfied.
    patterns = {
        "pair_analyses": [
            _analysis(groups=[
                _group([0], [3], top_row=0, top_col=0, cell_count=1),
                _group([1], [4], top_row=1, top_col=1, cell_count=1),
                _group([2], [5], top_row=2, top_col=2, cell_count=1),
            ]),
            _analysis(groups=[
                _group([0], [3], top_row=0, top_col=0, cell_count=1),
                _group([1], [4], top_row=1, top_col=1, cell_count=1),
                _group([2], [5], top_row=2, top_col=2, cell_count=1),
            ]),
        ],
    }
    sr = CONDITION_REGISTRY["sequential_recoloring"]
    assert _matcher()(patterns, {}) is True
    assert sr(patterns, {}) is True


def test_can_co_fire_with_grid_size_preserved() -> None:
    # Multi-blob on same-size pairs.
    patterns = {
        "grid_size_preserved": True,
        "pair_analyses": [
            _analysis(groups=[_group([0], [3]), _group([1], [4])]),
            _analysis(groups=[_group([0], [3]), _group([1], [4])]),
        ],
    }
    gsp = CONDITION_REGISTRY["grid_size_preserved"]
    assert _matcher()(patterns, {}) is True
    assert gsp(patterns, {}) is True


def test_does_not_require_grid_size_preserved() -> None:
    # Multi-blob on dimension-changed pairs: this matcher fires but
    # grid_size_preserved does not. Non-refinement on the dimensional
    # axis.
    patterns = {
        "pair_analyses": [
            _analysis(groups=[_group([0], [3]), _group([1], [4])],
                      output_height=9, output_width=9,
                      size_match=False),
        ],
    }
    gsp = CONDITION_REGISTRY["grid_size_preserved"]
    assert _matcher()(patterns, {}) is True
    assert gsp(patterns, {}) is False


def test_does_not_require_constant_group_count_across_pairs() -> None:
    # The matcher requires >= 2 per pair, NOT that the per-pair count
    # is constant across pairs (iter 10 is the strict-equal-N
    # matcher). A 2-blob pair next to a 4-blob pair must fire this
    # matcher but NOT iter 10 (which additionally requires same N AND
    # contiguous output range across pairs).
    patterns = {
        "pair_analyses": [
            _analysis(groups=[
                _group([0], [3]), _group([1], [4]),
            ]),
            _analysis(groups=[
                _group([0], [3]), _group([1], [4]),
                _group([2], [5]), _group([6], [7]),
            ]),
        ],
    }
    sr = CONDITION_REGISTRY["sequential_recoloring"]
    assert _matcher()(patterns, {}) is True
    assert sr(patterns, {}) is False


def test_end_to_end_agreement_with_extract_pattern_shape() -> None:
    # The shape ExtractPatternOperator._analyze_pair emits on a 3x3
    # grid with two disjoint single-cell changes: num_groups should be 2
    # and the matcher should fire.
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
    assert analysis["num_groups"] == 2, (
        f"live _analyze_pair produced num_groups={analysis['num_groups']}"
    )
    patterns = {"pair_analyses": [analysis]}
    assert _matcher()(patterns, {}) is True


def test_end_to_end_agreement_with_three_blob_grid() -> None:
    # Three disjoint single-cell changes on a 3x3 grid: num_groups
    # should be 3. The matcher fires (>=2 is satisfied).
    from agent.active_operators import ExtractPatternOperator  # noqa: E402

    op = ExtractPatternOperator()

    class _Grid:
        def __init__(self, raw):
            self.raw = raw
            self.height = len(raw)
            self.width = len(raw[0]) if raw else 0

    raw_in = [
        [0, 1, 0],
        [1, 1, 1],
        [0, 1, 0],
    ]
    raw_out = [
        [3, 1, 3],
        [1, 1, 1],
        [3, 1, 3],
    ]
    analysis = op._analyze_pair(_Grid(raw_in), _Grid(raw_out))
    # The four corners are diagonally adjacent (not 4-connected), so
    # the grouping algorithm produces 4 disjoint single-cell blobs.
    assert analysis["num_groups"] == 4, (
        f"live _analyze_pair produced num_groups={analysis['num_groups']}"
    )
    patterns = {"pair_analyses": [analysis]}
    assert _matcher()(patterns, {}) is True


def test_end_to_end_disagreement_on_single_blob_grid() -> None:
    # Live _analyze_pair on a single 1x1 change: num_groups is 1.
    # Iter 23 fires, this matcher does NOT.
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
    patterns = {"pair_analyses": [analysis]}
    iter23 = CONDITION_REGISTRY["single_change_group_per_pair"]
    assert iter23(patterns, {}) is True
    assert _matcher()(patterns, {}) is False


def test_end_to_end_disagreement_on_zero_change_grid() -> None:
    # No changes: num_groups is 0. Iter 13 fires; this matcher does NOT.
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
        _analysis(groups=[_group([0], [3]), _group([1], [4])]),
    ]}
    patterns_neg = {"pair_analyses": [
        _analysis(groups=[_group([0], [3])]),
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
        test_thirteen_distinct_matchers_registered,
        test_matcher_is_callable,
        test_returns_true_on_single_pair_with_two_groups,
        test_returns_true_on_two_groups_boundary,
        test_returns_true_on_three_groups,
        test_returns_true_on_multi_pair_with_varying_blob_counts,
        test_returns_false_on_zero_groups_per_pair,
        test_returns_false_on_single_group_per_pair,
        test_returns_false_on_mixed_single_and_multi_group,
        test_returns_false_on_mixed_zero_and_multi_group,
        test_returns_false_on_empty_pair_analyses,
        test_returns_false_on_missing_pair_analyses,
        test_returns_false_on_non_dict_patterns,
        test_returns_false_on_non_list_pair_analyses,
        test_returns_false_on_malformed_analysis_entry,
        test_returns_false_on_missing_num_groups,
        test_returns_false_on_non_int_num_groups,
        test_returns_false_on_bool_num_groups,
        test_returns_false_on_negative_num_groups,
        test_returns_false_on_one_num_groups_exactly,
        test_returns_false_on_zero_num_groups_exactly,
        test_returns_false_when_one_pair_missing_num_groups,
        test_is_side_effect_free_on_inputs,
        test_is_deterministic_across_repeats,
        test_mutually_exclusive_with_identity_transformation,
        test_strictly_disjoint_from_iter_23_matcher,
        test_three_matchers_partition_group_count_axis,
        test_strictly_disjoint_from_iter_24_matcher,
        test_strictly_disjoint_from_iter_26_matcher,
        test_can_co_fire_with_output_color_uniform,
        test_can_co_fire_with_input_color_uniform,
        test_can_co_fire_with_consistent_color_mapping,
        test_can_co_fire_with_sequential_recoloring,
        test_can_co_fire_with_grid_size_preserved,
        test_does_not_require_grid_size_preserved,
        test_does_not_require_constant_group_count_across_pairs,
        test_end_to_end_agreement_with_extract_pattern_shape,
        test_end_to_end_agreement_with_three_blob_grid,
        test_end_to_end_disagreement_on_single_blob_grid,
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
