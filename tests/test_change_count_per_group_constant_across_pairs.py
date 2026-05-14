"""
tests/test_change_count_per_group_constant_across_pairs.py -- exercise
the iter-193 matcher
``agent.conditions.change_count_per_group_constant_across_pairs``
(new in this iter).

Pins the matcher's contract per the module docstring: every change
group in every example pair has the SAME ``cell_count`` integer K,
where K is determined by the first observed group. The matcher does
not pin a specific K, only the cross-pair / cross-group constancy of
that single derived integer.

Sits on the per-group cell-count constancy sub-axis, orthogonal to
the cross-pair *total*-cell-count axis (iter 32) and the cross-pair
*group-count* axis (iter 39). Strictly refined by iter 24
(``single_cell_change_per_pair``, which pins K == 1 AND num_groups
== 1 per pair).

Runs without pytest:

    python tests/test_change_count_per_group_constant_across_pairs.py

Dependency-free, same runner style as the other tests under ``tests/``.
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


MATCHER_NAME = "change_count_per_group_constant_across_pairs"


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


def _analysis(*, groups, input_height=4, input_width=4,
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


# ──────────────────────────────────────────────────────────────────────────
# Smoke / membership tests.
# ──────────────────────────────────────────────────────────────────────────

def test_registered_in_global_registry() -> None:
    assert MATCHER_NAME in CONDITION_REGISTRY, (
        f"{MATCHER_NAME!r} not registered; got {sorted(CONDITION_REGISTRY)}"
    )


def test_matcher_is_callable() -> None:
    fn = _matcher()
    assert callable(fn), f"registered entry is not callable: {fn!r}"


# ──────────────────────────────────────────────────────────────────────────
# Positive cases — constant per-group cell count across all groups, all pairs.
# ──────────────────────────────────────────────────────────────────────────

def test_returns_true_on_single_pair_single_one_cell_group() -> None:
    patterns = {"pair_analyses": [
        _analysis(groups=[_group(positions=[(1, 1)])]),
    ]}
    assert _matcher()(patterns, {}) is True


def test_returns_true_on_two_pairs_K_equals_one() -> None:
    # Every pair has one group of one cell (K == 1).
    patterns = {"pair_analyses": [
        _analysis(groups=[_group(positions=[(0, 0)])]),
        _analysis(groups=[_group(positions=[(2, 2)])]),
    ]}
    assert _matcher()(patterns, {}) is True


def test_returns_true_on_K_equals_two_two_groups_per_pair() -> None:
    # Every group is exactly 2 cells; every pair has 2 groups.
    patterns = {"pair_analyses": [
        _analysis(groups=[
            _group(positions=[(0, 0), (0, 1)]),
            _group(positions=[(2, 2), (2, 3)]),
        ]),
        _analysis(groups=[
            _group(positions=[(1, 0), (1, 1)]),
            _group(positions=[(3, 2), (3, 3)]),
        ]),
    ]}
    assert _matcher()(patterns, {}) is True


def test_returns_true_on_K_equals_five_single_group_per_pair() -> None:
    patterns = {"pair_analyses": [
        _analysis(
            groups=[_group(positions=[(0, 0), (0, 1), (0, 2), (0, 3), (1, 0)])]
        ),
        _analysis(
            groups=[_group(positions=[(2, 0), (2, 1), (2, 2), (2, 3), (3, 0)])]
        ),
    ]}
    assert _matcher()(patterns, {}) is True


def test_returns_true_on_three_pairs_varying_num_groups_same_K() -> None:
    # Per-group K constancy does NOT require num_groups constancy. Pair 0
    # has 1 group, pair 1 has 2 groups, pair 2 has 3 groups — all groups
    # are 2 cells. This matcher fires; iter 39 (group-count constancy)
    # rejects.
    patterns = {"pair_analyses": [
        _analysis(groups=[_group(positions=[(0, 0), (0, 1)])]),
        _analysis(groups=[
            _group(positions=[(0, 0), (0, 1)]),
            _group(positions=[(2, 0), (2, 1)]),
        ]),
        _analysis(groups=[
            _group(positions=[(0, 0), (0, 1)]),
            _group(positions=[(2, 0), (2, 1)]),
            _group(positions=[(3, 2), (3, 3)]),
        ]),
    ]}
    assert _matcher()(patterns, {}) is True


def test_returns_true_on_single_pair_multiple_groups_same_K() -> None:
    patterns = {"pair_analyses": [
        _analysis(groups=[
            _group(positions=[(0, 0), (0, 1), (0, 2)]),
            _group(positions=[(2, 0), (2, 1), (2, 2)]),
            _group(positions=[(3, 0), (3, 1), (3, 2)]),
        ]),
    ]}
    assert _matcher()(patterns, {}) is True


# ──────────────────────────────────────────────────────────────────────────
# Negative cases.
# ──────────────────────────────────────────────────────────────────────────

def test_returns_false_when_K_varies_across_pairs() -> None:
    # Pair 0's only group is 1 cell; pair 1's only group is 2 cells.
    patterns = {"pair_analyses": [
        _analysis(groups=[_group(positions=[(0, 0)])]),
        _analysis(groups=[_group(positions=[(2, 2), (2, 3)])]),
    ]}
    assert _matcher()(patterns, {}) is False


def test_returns_false_when_K_varies_within_a_pair() -> None:
    # Pair 0 has two groups: one of 1 cell, one of 2 cells. The matcher
    # demands every group in every pair has the same K, so this fails
    # on the first pair alone.
    patterns = {"pair_analyses": [
        _analysis(groups=[
            _group(positions=[(0, 0)]),
            _group(positions=[(2, 2), (2, 3)]),
        ]),
    ]}
    assert _matcher()(patterns, {}) is False


def test_returns_false_when_K_varies_across_groups_in_later_pair() -> None:
    # Pair 0 is well-formed (K == 2 throughout); pair 1 introduces a
    # K-violating group (a 3-cell blob alongside a 2-cell blob).
    patterns = {"pair_analyses": [
        _analysis(groups=[
            _group(positions=[(0, 0), (0, 1)]),
            _group(positions=[(2, 2), (2, 3)]),
        ]),
        _analysis(groups=[
            _group(positions=[(0, 0), (0, 1)]),
            _group(positions=[(2, 0), (2, 1), (2, 2)]),
        ]),
    ]}
    assert _matcher()(patterns, {}) is False


def test_returns_false_on_identity_all_zero_groups() -> None:
    # Identity territory (iter 13). The matcher's fail-closed clause on
    # empty groups keeps its territory disjoint from iter 13.
    patterns = {"pair_analyses": [
        _analysis(groups=[]),
        _analysis(groups=[]),
    ]}
    assert _matcher()(patterns, {}) is False


def test_returns_false_when_one_pair_has_zero_groups() -> None:
    # The empty-groups rejection is per-pair, not just universal: a
    # mixed identity / non-identity task is also disqualified.
    patterns = {"pair_analyses": [
        _analysis(groups=[_group(positions=[(0, 0)])]),
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


# ──────────────────────────────────────────────────────────────────────────
# Strict-type gates on ``groups`` / ``cell_count``.
# ──────────────────────────────────────────────────────────────────────────

def test_returns_false_on_missing_groups_field() -> None:
    # An analysis dict without ``groups`` cannot satisfy the contract.
    analysis_bad = {
        "size_match": True,
        "total_changes": 1,
        "num_groups": 1,
        "input_height": 3, "input_width": 3,
        "output_height": 3, "output_width": 3,
        # groups intentionally missing
    }
    assert _matcher()({"pair_analyses": [analysis_bad]}, {}) is False


def test_returns_false_on_non_list_groups() -> None:
    for bad in (None, "string", 42, {"k": "v"}):
        analysis_bad = {
            "size_match": True,
            "total_changes": 1,
            "num_groups": 1,
            "input_height": 3, "input_width": 3,
            "output_height": 3, "output_width": 3,
            "groups": bad,
        }
        assert _matcher()({"pair_analyses": [analysis_bad]}, {}) is False, (
            f"groups={bad!r} should fail-closed"
        )


def test_returns_false_on_non_dict_group_entry() -> None:
    for bad in (None, "string", 42, [1, 2]):
        analysis_bad = _analysis(groups=[])
        analysis_bad["groups"] = [bad]
        assert _matcher()({"pair_analyses": [analysis_bad]}, {}) is False, (
            f"group entry {bad!r} should fail-closed"
        )


def test_returns_false_on_missing_cell_count() -> None:
    group_bad = {
        "input_colors": [0], "output_colors": [3],
        "top_row": 0, "top_col": 0,
        "positions": [(0, 0)],
        # cell_count intentionally missing
    }
    analysis_bad = _analysis(groups=[])
    analysis_bad["groups"] = [group_bad]
    assert _matcher()({"pair_analyses": [analysis_bad]}, {}) is False


def test_returns_false_on_bool_cell_count() -> None:
    for bad in (True, False):
        group_bad = {
            "input_colors": [0], "output_colors": [3],
            "top_row": 0, "top_col": 0,
            "positions": [(0, 0)],
            "cell_count": bad,
        }
        analysis_bad = _analysis(groups=[])
        analysis_bad["groups"] = [group_bad]
        assert _matcher()({"pair_analyses": [analysis_bad]}, {}) is False, (
            f"cell_count={bad!r} (bool) should fail-closed"
        )


def test_returns_false_on_zero_cell_count() -> None:
    # cell_count < 1 is rejected (a zero-cell group is not a group).
    group_bad = {
        "input_colors": [0], "output_colors": [3],
        "top_row": 0, "top_col": 0,
        "positions": [],
        "cell_count": 0,
    }
    analysis_bad = _analysis(groups=[])
    analysis_bad["groups"] = [group_bad]
    assert _matcher()({"pair_analyses": [analysis_bad]}, {}) is False


def test_returns_false_on_negative_cell_count() -> None:
    group_bad = {
        "input_colors": [0], "output_colors": [3],
        "top_row": 0, "top_col": 0,
        "positions": [(0, 0)],
        "cell_count": -1,
    }
    analysis_bad = _analysis(groups=[])
    analysis_bad["groups"] = [group_bad]
    assert _matcher()({"pair_analyses": [analysis_bad]}, {}) is False


def test_returns_false_on_non_int_cell_count() -> None:
    for bad in (0.5, "1", None, [1]):
        group_bad = {
            "input_colors": [0], "output_colors": [3],
            "top_row": 0, "top_col": 0,
            "positions": [(0, 0)],
            "cell_count": bad,
        }
        analysis_bad = _analysis(groups=[])
        analysis_bad["groups"] = [group_bad]
        assert _matcher()({"pair_analyses": [analysis_bad]}, {}) is False, (
            f"cell_count={bad!r} ({type(bad).__name__}) should fail-closed"
        )


def test_returns_false_on_second_pair_malformed() -> None:
    # Pair 0 is well-formed (K = 1); pair 1 has a malformed group.
    pair0 = _analysis(groups=[_group(positions=[(0, 0)])])
    pair1_bad = _analysis(groups=[])
    pair1_bad["groups"] = ["not-a-dict"]
    assert _matcher()({"pair_analyses": [pair0, pair1_bad]}, {}) is False


# ──────────────────────────────────────────────────────────────────────────
# Behavioural contract: side-effect-free, deterministic, strict bool.
# ──────────────────────────────────────────────────────────────────────────

def test_is_side_effect_free_on_inputs() -> None:
    patterns = {"pair_analyses": [
        _analysis(groups=[
            _group(positions=[(0, 0), (0, 1)]),
            _group(positions=[(2, 2), (2, 3)]),
        ]),
        _analysis(groups=[_group(positions=[(1, 1), (1, 2)])]),
    ]}
    params = {"unused": 1}
    before_p = copy.deepcopy(patterns)
    before_q = copy.deepcopy(params)
    _matcher()(patterns, params)
    assert patterns == before_p, "matcher mutated patterns"
    assert params == before_q, "matcher mutated params"


def test_is_deterministic_across_repeats() -> None:
    patterns = {"pair_analyses": [
        _analysis(groups=[_group(positions=[(1, 1), (1, 2)])]),
        _analysis(groups=[_group(positions=[(2, 2), (2, 3)])]),
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
        _analysis(groups=[_group(positions=[(2, 2), (2, 3)])]),
    ]}
    pos = _matcher()(pos_pat, {})
    neg = _matcher()(neg_pat, {})
    assert pos is True, f"expected literal True, got {pos!r}"
    assert neg is False, f"expected literal False, got {neg!r}"


def test_params_argument_ignored() -> None:
    # The matcher consumes no params; an arbitrary params dict must not
    # change the outcome.
    patterns = {"pair_analyses": [
        _analysis(groups=[_group(positions=[(0, 0)])]),
        _analysis(groups=[_group(positions=[(2, 2)])]),
    ]}
    assert _matcher()(patterns, {}) is True
    assert _matcher()(patterns, {"target": 99}) is True
    assert _matcher()(patterns, {"K": 7, "junk": [1, 2]}) is True


# ──────────────────────────────────────────────────────────────────────────
# Orthogonality / refinement against neighbouring matchers.
# ──────────────────────────────────────────────────────────────────────────

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


def test_iter_24_refinement_implication_holds() -> None:
    # iter 24 (single_cell_change_per_pair) pins K == 1 AND num_groups
    # == 1 per pair. That STRICTLY refines this matcher (K == 1
    # everywhere ⟹ K is constant).
    patterns = {"pair_analyses": [
        _analysis(groups=[_group(positions=[(0, 0)])]),
        _analysis(groups=[_group(positions=[(2, 2)])]),
    ]}
    iter24 = CONDITION_REGISTRY["single_cell_change_per_pair"]
    assert iter24(patterns, {}) is True
    assert _matcher()(patterns, {}) is True


def test_iter_24_refinement_strict_one_direction() -> None:
    # Converse fails: K == 2 everywhere (this matcher fires) but iter 24
    # rejects (requires K == 1).
    patterns = {"pair_analyses": [
        _analysis(groups=[_group(positions=[(0, 0), (0, 1)])]),
        _analysis(groups=[_group(positions=[(2, 2), (2, 3)])]),
    ]}
    iter24 = CONDITION_REGISTRY["single_cell_change_per_pair"]
    assert iter24(patterns, {}) is False
    assert _matcher()(patterns, {}) is True


def test_iter_26_independence_iter_26_alone() -> None:
    # iter 26 (multi_cell_change_group_per_pair) fires on single-group
    # pairs with cell_count >= 2 — does NOT pin K cross-pair. Pair 0 has
    # a 2-cell group; pair 1 has a 3-cell group: iter 26 fires; this
    # matcher rejects.
    patterns = {"pair_analyses": [
        _analysis(groups=[_group(positions=[(0, 0), (0, 1)])]),
        _analysis(groups=[_group(positions=[(2, 0), (2, 1), (2, 2)])]),
    ]}
    iter26 = CONDITION_REGISTRY["multi_cell_change_group_per_pair"]
    assert iter26(patterns, {}) is True
    assert _matcher()(patterns, {}) is False


def test_iter_26_co_fires_with_constant_K_at_least_two() -> None:
    # When iter 26 fires AND K is constant (>= 2) across pairs, both
    # fire.
    patterns = {"pair_analyses": [
        _analysis(groups=[_group(positions=[(0, 0), (0, 1)])]),
        _analysis(groups=[_group(positions=[(2, 0), (2, 1)])]),
    ]}
    iter26 = CONDITION_REGISTRY["multi_cell_change_group_per_pair"]
    assert iter26(patterns, {}) is True
    assert _matcher()(patterns, {}) is True


def test_iter_28_independence_iter_28_alone() -> None:
    # iter 28 (multi_group_per_pair) fires when num_groups >= 2 per
    # pair, regardless of per-group cell counts. With varying K in
    # such a pair, this matcher rejects.
    patterns = {"pair_analyses": [
        _analysis(groups=[
            _group(positions=[(0, 0)]),
            _group(positions=[(2, 2), (2, 3)]),
        ]),
        _analysis(groups=[
            _group(positions=[(0, 0)]),
            _group(positions=[(2, 2), (2, 3)]),
        ]),
    ]}
    iter28 = CONDITION_REGISTRY["multi_group_per_pair"]
    assert iter28(patterns, {}) is True
    assert _matcher()(patterns, {}) is False


def test_iter_28_co_fires_with_constant_K() -> None:
    # iter 28 (num_groups >= 2 per pair) AND constant K across all
    # groups/pairs co-fire.
    patterns = {"pair_analyses": [
        _analysis(groups=[
            _group(positions=[(0, 0)]),
            _group(positions=[(2, 2)]),
        ]),
        _analysis(groups=[
            _group(positions=[(1, 1)]),
            _group(positions=[(3, 3)]),
        ]),
    ]}
    iter28 = CONDITION_REGISTRY["multi_group_per_pair"]
    assert iter28(patterns, {}) is True
    assert _matcher()(patterns, {}) is True


def test_independent_of_change_count_total_iter_32_alone() -> None:
    # iter 32 (change_count_constant_across_pairs) pins the per-pair
    # SUM, not the per-group cell count. Pair 0 has one 2-cell blob;
    # pair 1 has two 1-cell blobs: SUM is 2 on both (iter 32 fires),
    # but per-group K is 2 then 1 (this matcher rejects).
    patterns = {"pair_analyses": [
        _analysis(groups=[_group(positions=[(0, 0), (0, 1)])]),
        _analysis(groups=[
            _group(positions=[(2, 2)]),
            _group(positions=[(3, 3)]),
        ]),
    ]}
    iter32 = CONDITION_REGISTRY["change_count_constant_across_pairs"]
    assert iter32(patterns, {}) is True
    assert _matcher()(patterns, {}) is False


def test_independent_of_change_count_total_this_matcher_alone() -> None:
    # Per-group K constant (K == 2) but per-pair TOTAL varies (4 vs 6):
    # this matcher fires, iter 32 rejects.
    patterns = {"pair_analyses": [
        _analysis(groups=[
            _group(positions=[(0, 0), (0, 1)]),
            _group(positions=[(2, 2), (2, 3)]),
        ]),
        _analysis(groups=[
            _group(positions=[(0, 0), (0, 1)]),
            _group(positions=[(2, 0), (2, 1)]),
            _group(positions=[(3, 2), (3, 3)]),
        ]),
    ]}
    iter32 = CONDITION_REGISTRY["change_count_constant_across_pairs"]
    assert _matcher()(patterns, {}) is True
    assert iter32(patterns, {}) is False


def test_independent_of_group_count_iter_39_alone() -> None:
    # iter 39 (change_group_count_constant_across_pairs) pins num_groups,
    # not per-group K. Same group count (1) per pair but different K:
    # iter 39 fires, this matcher rejects.
    patterns = {"pair_analyses": [
        _analysis(groups=[_group(positions=[(0, 0)])]),
        _analysis(groups=[_group(positions=[(2, 2), (2, 3)])]),
    ]}
    iter39 = CONDITION_REGISTRY["change_group_count_constant_across_pairs"]
    assert iter39(patterns, {}) is True
    assert _matcher()(patterns, {}) is False


def test_independent_of_group_count_this_matcher_alone() -> None:
    # Per-group K constant but num_groups varies (1 vs 2): this matcher
    # fires, iter 39 rejects.
    patterns = {"pair_analyses": [
        _analysis(groups=[_group(positions=[(0, 0), (0, 1)])]),
        _analysis(groups=[
            _group(positions=[(0, 0), (0, 1)]),
            _group(positions=[(2, 2), (2, 3)]),
        ]),
    ]}
    iter39 = CONDITION_REGISTRY["change_group_count_constant_across_pairs"]
    assert _matcher()(patterns, {}) is True
    assert iter39(patterns, {}) is False


def test_co_fires_with_grid_size_preserved() -> None:
    # Orthogonal axes: grid_size_preserved is a dimensional flag, this
    # matcher inspects per-group cell counts. CAN co-fire.
    patterns = {
        "grid_size_preserved": True,
        "pair_analyses": [
            _analysis(groups=[_group(positions=[(0, 0)])]),
            _analysis(groups=[_group(positions=[(2, 2)])]),
        ],
    }
    iter1 = CONDITION_REGISTRY["grid_size_preserved"]
    assert iter1(patterns, {}) is True
    assert _matcher()(patterns, {}) is True


# ──────────────────────────────────────────────────────────────────────────
# Recognized-conditions wiring.
# ──────────────────────────────────────────────────────────────────────────

def test_recognized_conditions_includes_matcher_on_constant_K() -> None:
    from agent.conditions import recognized_conditions
    patterns = {
        "pair_analyses": [
            _analysis(groups=[_group(positions=[(0, 0)])]),
            _analysis(groups=[_group(positions=[(2, 2)])]),
        ],
    }
    fired = recognized_conditions(patterns)
    assert MATCHER_NAME in fired, (
        f"{MATCHER_NAME!r} did not fire on constant-K=1 patterns dict; "
        f"got {fired!r}"
    )


def test_recognized_conditions_excludes_on_varying_K() -> None:
    from agent.conditions import recognized_conditions
    patterns = {
        "pair_analyses": [
            _analysis(groups=[_group(positions=[(0, 0)])]),
            _analysis(groups=[_group(positions=[(2, 2), (2, 3)])]),
        ],
    }
    fired = recognized_conditions(patterns)
    assert MATCHER_NAME not in fired, (
        f"{MATCHER_NAME!r} must NOT fire on varying-K patterns; got "
        f"{fired!r}"
    )


def test_recognized_conditions_fires_alongside_iter32_when_compatible() -> None:
    # K constant (==2) AND num_groups constant (==1) ⟹ per-pair total
    # also constant (==2), so iter 32 fires together with this matcher.
    from agent.conditions import recognized_conditions
    patterns = {
        "pair_analyses": [
            _analysis(groups=[_group(positions=[(0, 0), (0, 1)])]),
            _analysis(groups=[_group(positions=[(2, 2), (2, 3)])]),
        ],
    }
    fired = recognized_conditions(patterns)
    assert "change_count_constant_across_pairs" in fired
    assert "change_group_count_constant_across_pairs" in fired
    assert MATCHER_NAME in fired


# ──────────────────────────────────────────────────────────────────────────
# Test runner (dependency-free, same style as the other tests).
# ──────────────────────────────────────────────────────────────────────────

def _run() -> int:
    tests = [
        (name, fn) for name, fn in globals().items()
        if name.startswith("test_") and callable(fn)
    ]
    failed = 0
    for name, fn in tests:
        try:
            fn()
            print(f"  OK   {name}")
        except AssertionError as e:
            failed += 1
            print(f"  FAIL {name}: {e}")
            traceback.print_exc()
        except Exception as e:  # pragma: no cover -- defensive
            failed += 1
            print(f"  ERR  {name}: {e!r}")
            traceback.print_exc()
    print(f"\n{len(tests) - failed}/{len(tests)} passed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(_run())
