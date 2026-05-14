"""
tests/test_change_output_color_count_per_group_constant_across_pairs.py
-- exercise the iter-196 matcher
``agent.conditions.change_output_color_count_per_group_constant_across_pairs``
(new in this iter).

Pins the matcher's contract per the module docstring: every change
group in every example pair has the SAME ``len(output_colors)``
integer K, where K is determined by the first observed group. The
matcher does not pin a specific K, only the cross-pair / cross-group
constancy of that single derived integer; the COLOURS themselves are
free.

Sits on the per-group output-colour cardinality sub-axis -- the
per-group projection of iter 38 (``change_output_color_count_constant_
across_pairs``, per-pair set cardinality) and the output-side dual of
iter 195 (``change_input_color_count_per_group_constant_across_pairs``).
Strictly refined by iter 18 (``output_color_uniform``, pins K==1 AND
identical colour).

Runs without pytest:

    python tests/test_change_output_color_count_per_group_constant_across_pairs.py

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


MATCHER_NAME = "change_output_color_count_per_group_constant_across_pairs"


def _matcher():
    return CONDITION_REGISTRY[MATCHER_NAME]


def _group(*, input_colors=(0,), output_colors=(3,), positions=None):
    """Build a group analysis dict matching ``_analyze_pair``'s emit shape."""
    if positions is None:
        positions = [(0, 0)]
    sorted_positions = sorted(tuple(p) for p in positions)
    if sorted_positions:
        top_row = min(r for r, _ in sorted_positions)
        top_col = min(c for _, c in sorted_positions)
    else:
        top_row = 0
        top_col = 0
    return {
        "input_colors": sorted(set(input_colors)),
        "output_colors": sorted(set(output_colors)),
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
# Positive cases — constant per-group output-colour count across groups/pairs.
# ──────────────────────────────────────────────────────────────────────────

def test_returns_true_on_single_pair_single_K_equals_one_group() -> None:
    patterns = {"pair_analyses": [
        _analysis(groups=[_group(output_colors=[3])]),
    ]}
    assert _matcher()(patterns, {}) is True


def test_returns_true_on_two_pairs_K_equals_one_same_color() -> None:
    # Every group has one output colour and the colour is also identical
    # — strict refinement by iter 18, both fire.
    patterns = {"pair_analyses": [
        _analysis(groups=[_group(output_colors=[3])]),
        _analysis(groups=[_group(output_colors=[3])]),
    ]}
    assert _matcher()(patterns, {}) is True


def test_returns_true_on_two_pairs_K_equals_one_different_colors() -> None:
    # Every group has one output colour but the colour DIFFERS across
    # pairs. iter 18 rejects (it requires identical colour); this
    # matcher fires (only cardinality is pinned, not value).
    patterns = {"pair_analyses": [
        _analysis(groups=[_group(output_colors=[3])]),
        _analysis(groups=[_group(output_colors=[5])]),
    ]}
    assert _matcher()(patterns, {}) is True


def test_returns_true_on_two_pairs_K_equals_two() -> None:
    # Every group spans exactly 2 output colours; colours free.
    patterns = {"pair_analyses": [
        _analysis(groups=[_group(output_colors=[3, 4])]),
        _analysis(groups=[_group(output_colors=[7, 8])]),
    ]}
    assert _matcher()(patterns, {}) is True


def test_returns_true_on_K_equals_two_multiple_groups_per_pair() -> None:
    # Every group spans 2 output colours; multiple groups per pair.
    patterns = {"pair_analyses": [
        _analysis(groups=[
            _group(output_colors=[3, 4]),
            _group(output_colors=[5, 6]),
        ]),
        _analysis(groups=[
            _group(output_colors=[1, 2]),
            _group(output_colors=[7, 8]),
        ]),
    ]}
    assert _matcher()(patterns, {}) is True


def test_returns_true_on_K_equals_three_across_three_pairs() -> None:
    patterns = {"pair_analyses": [
        _analysis(groups=[_group(output_colors=[3, 4, 5])]),
        _analysis(groups=[_group(output_colors=[1, 2, 7])]),
        _analysis(groups=[_group(output_colors=[6, 8, 9])]),
    ]}
    assert _matcher()(patterns, {}) is True


def test_returns_true_on_varying_num_groups_same_K() -> None:
    # Per-group K==1 constancy does NOT require num_groups constancy.
    # Pair 0 has 1 group, pair 1 has 2 groups, pair 2 has 3 groups —
    # every group has 1 output colour. iter 39 (group-count constancy)
    # rejects.
    patterns = {"pair_analyses": [
        _analysis(groups=[_group(output_colors=[3])]),
        _analysis(groups=[
            _group(output_colors=[5]),
            _group(output_colors=[7]),
        ]),
        _analysis(groups=[
            _group(output_colors=[3]),
            _group(output_colors=[6]),
            _group(output_colors=[8]),
        ]),
    ]}
    assert _matcher()(patterns, {}) is True


# ──────────────────────────────────────────────────────────────────────────
# Negative cases.
# ──────────────────────────────────────────────────────────────────────────

def test_returns_false_when_K_varies_across_pairs() -> None:
    # Pair 0's group has 1 output colour; pair 1's group has 2.
    patterns = {"pair_analyses": [
        _analysis(groups=[_group(output_colors=[3])]),
        _analysis(groups=[_group(output_colors=[5, 6])]),
    ]}
    assert _matcher()(patterns, {}) is False


def test_returns_false_when_K_varies_within_a_pair() -> None:
    # Pair 0 has two groups: one with 1 output colour, one with 2. The
    # matcher demands every group in every pair has the same K, so this
    # fails on the first pair alone.
    patterns = {"pair_analyses": [
        _analysis(groups=[
            _group(output_colors=[3]),
            _group(output_colors=[5, 6]),
        ]),
    ]}
    assert _matcher()(patterns, {}) is False


def test_returns_false_when_K_varies_in_later_pair() -> None:
    # Pair 0 is well-formed (K==2 throughout); pair 1 introduces a
    # K-violating group (K==3 alongside K==2).
    patterns = {"pair_analyses": [
        _analysis(groups=[
            _group(output_colors=[3, 4]),
            _group(output_colors=[5, 6]),
        ]),
        _analysis(groups=[
            _group(output_colors=[1, 2]),
            _group(output_colors=[6, 7, 8]),
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
        _analysis(groups=[_group(output_colors=[3])]),
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
# Strict-type gates on ``groups`` / ``output_colors``.
# ──────────────────────────────────────────────────────────────────────────

def test_returns_false_on_missing_groups_field() -> None:
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


def test_returns_false_on_missing_output_colors() -> None:
    group_bad = {
        "input_colors": [1],
        "top_row": 0, "top_col": 0,
        "positions": [(0, 0)],
        "cell_count": 1,
        # output_colors intentionally missing
    }
    analysis_bad = _analysis(groups=[])
    analysis_bad["groups"] = [group_bad]
    assert _matcher()({"pair_analyses": [analysis_bad]}, {}) is False


def test_returns_false_on_non_list_output_colors() -> None:
    for bad in (None, 1, "1", {1: 2}, (1,)):
        group_bad = {
            "input_colors": [1],
            "output_colors": bad,
            "top_row": 0, "top_col": 0,
            "positions": [(0, 0)],
            "cell_count": 1,
        }
        analysis_bad = _analysis(groups=[])
        analysis_bad["groups"] = [group_bad]
        assert _matcher()({"pair_analyses": [analysis_bad]}, {}) is False, (
            f"output_colors={bad!r} should fail-closed"
        )


def test_returns_false_on_empty_output_colors_list() -> None:
    # An empty output_colors list is an extractor contract violation
    # (every group has at least one cell, so its output-colour set is
    # non-empty). Fail-closed mirrors the iter-14 / 18 / 19 / 195
    # strict posture.
    group_bad = {
        "input_colors": [1],
        "output_colors": [],
        "top_row": 0, "top_col": 0,
        "positions": [(0, 0)],
        "cell_count": 1,
    }
    analysis_bad = _analysis(groups=[])
    analysis_bad["groups"] = [group_bad]
    assert _matcher()({"pair_analyses": [analysis_bad]}, {}) is False


def test_returns_false_on_bool_in_output_colors() -> None:
    for bad in (True, False):
        group_bad = {
            "input_colors": [1],
            "output_colors": [bad],
            "top_row": 0, "top_col": 0,
            "positions": [(0, 0)],
            "cell_count": 1,
        }
        analysis_bad = _analysis(groups=[])
        analysis_bad["groups"] = [group_bad]
        assert _matcher()({"pair_analyses": [analysis_bad]}, {}) is False, (
            f"output_colors=[{bad!r}] (bool) should fail-closed"
        )


def test_returns_false_on_out_of_range_output_color() -> None:
    for bad in (-1, 10, 100):
        group_bad = {
            "input_colors": [1],
            "output_colors": [bad],
            "top_row": 0, "top_col": 0,
            "positions": [(0, 0)],
            "cell_count": 1,
        }
        analysis_bad = _analysis(groups=[])
        analysis_bad["groups"] = [group_bad]
        assert _matcher()({"pair_analyses": [analysis_bad]}, {}) is False, (
            f"output_colors=[{bad!r}] (out-of-range) should fail-closed"
        )


def test_returns_false_on_non_int_output_color() -> None:
    for bad in (0.5, "1", None, [1]):
        group_bad = {
            "input_colors": [1],
            "output_colors": [bad],
            "top_row": 0, "top_col": 0,
            "positions": [(0, 0)],
            "cell_count": 1,
        }
        analysis_bad = _analysis(groups=[])
        analysis_bad["groups"] = [group_bad]
        assert _matcher()({"pair_analyses": [analysis_bad]}, {}) is False, (
            f"output_colors=[{bad!r}] ({type(bad).__name__}) should fail-closed"
        )


def test_returns_false_on_second_pair_malformed() -> None:
    pair0 = _analysis(groups=[_group(output_colors=[3])])
    pair1_bad = _analysis(groups=[])
    pair1_bad["groups"] = ["not-a-dict"]
    assert _matcher()({"pair_analyses": [pair0, pair1_bad]}, {}) is False


# ──────────────────────────────────────────────────────────────────────────
# Behavioural contract: side-effect-free, deterministic, strict bool.
# ──────────────────────────────────────────────────────────────────────────

def test_is_side_effect_free_on_inputs() -> None:
    patterns = {"pair_analyses": [
        _analysis(groups=[
            _group(output_colors=[3, 4]),
            _group(output_colors=[5, 6]),
        ]),
        _analysis(groups=[_group(output_colors=[7, 8])]),
    ]}
    params = {"unused": 1}
    before_p = copy.deepcopy(patterns)
    before_q = copy.deepcopy(params)
    _matcher()(patterns, params)
    assert patterns == before_p, "matcher mutated patterns"
    assert params == before_q, "matcher mutated params"


def test_is_deterministic_across_repeats() -> None:
    patterns = {"pair_analyses": [
        _analysis(groups=[_group(output_colors=[3, 4])]),
        _analysis(groups=[_group(output_colors=[5, 6])]),
    ]}
    results = [_matcher()(patterns, {}) for _ in range(5)]
    assert len(set(results)) == 1, f"non-deterministic outputs: {results}"


def test_returns_strict_boolean_type() -> None:
    pos_pat = {"pair_analyses": [
        _analysis(groups=[_group(output_colors=[3])]),
        _analysis(groups=[_group(output_colors=[5])]),
    ]}
    neg_pat = {"pair_analyses": [
        _analysis(groups=[_group(output_colors=[3])]),
        _analysis(groups=[_group(output_colors=[5, 6])]),
    ]}
    pos = _matcher()(pos_pat, {})
    neg = _matcher()(neg_pat, {})
    assert pos is True, f"expected literal True, got {pos!r}"
    assert neg is False, f"expected literal False, got {neg!r}"


def test_params_argument_ignored() -> None:
    patterns = {"pair_analyses": [
        _analysis(groups=[_group(output_colors=[3])]),
        _analysis(groups=[_group(output_colors=[5])]),
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
            _analysis(groups=[_group(output_colors=[3])]),
            _analysis(groups=[_group(output_colors=[5])]),
        ],
    }
    identity = CONDITION_REGISTRY["identity_transformation"]
    assert identity(identity_pat, {}) is True
    assert _matcher()(identity_pat, {}) is False
    assert identity(paint_pat, {}) is False
    assert _matcher()(paint_pat, {}) is True


def test_iter_18_refinement_implication_holds() -> None:
    # iter 18 (output_color_uniform) pins K == 1 AND identical colour
    # across all groups. That STRICTLY refines this matcher (K == 1
    # everywhere ⟹ K is constant).
    patterns = {"pair_analyses": [
        _analysis(groups=[_group(output_colors=[3])]),
        _analysis(groups=[_group(output_colors=[3])]),
    ]}
    iter18 = CONDITION_REGISTRY["output_color_uniform"]
    assert iter18(patterns, {}) is True
    assert _matcher()(patterns, {}) is True


def test_iter_18_refinement_strict_one_direction() -> None:
    # Converse fails: K == 2 everywhere (this matcher fires) but iter 18
    # rejects (it requires K == 1 AND identical colour).
    patterns = {"pair_analyses": [
        _analysis(groups=[_group(output_colors=[3, 4])]),
        _analysis(groups=[_group(output_colors=[5, 6])]),
    ]}
    iter18 = CONDITION_REGISTRY["output_color_uniform"]
    assert iter18(patterns, {}) is False
    assert _matcher()(patterns, {}) is True


def test_iter_18_refinement_strict_K1_different_colors() -> None:
    # K == 1 everywhere but colours differ — iter 18 rejects (it
    # requires identical colour across pairs); this matcher fires
    # (only cardinality is pinned).
    patterns = {"pair_analyses": [
        _analysis(groups=[_group(output_colors=[3])]),
        _analysis(groups=[_group(output_colors=[5])]),
    ]}
    iter18 = CONDITION_REGISTRY["output_color_uniform"]
    assert iter18(patterns, {}) is False
    assert _matcher()(patterns, {}) is True


def test_iter_38_co_fires_with_single_color_groups() -> None:
    # Both matchers fire: every group has 1 output colour (so iter 38's
    # per-group precondition is met) AND per-pair output set cardinality
    # is constant (every pair's set has cardinality 1).
    patterns = {"pair_analyses": [
        _analysis(groups=[_group(output_colors=[3])]),
        _analysis(groups=[
            _group(output_colors=[5]),
            _group(output_colors=[5]),
        ]),
    ]}
    iter38 = CONDITION_REGISTRY["change_output_color_count_constant_across_pairs"]
    assert iter38(patterns, {}) is True
    assert _matcher()(patterns, {}) is True


def test_this_matcher_fires_alone_on_K_geq_2_groups() -> None:
    # iter 38 requires len(output_colors) == 1 per group; this matcher
    # accepts K >= 1 uniformly. With every group at K == 2, iter 38
    # rejects, this matcher fires.
    patterns = {"pair_analyses": [
        _analysis(groups=[_group(output_colors=[3, 4])]),
        _analysis(groups=[_group(output_colors=[5, 6])]),
    ]}
    iter38 = CONDITION_REGISTRY["change_output_color_count_constant_across_pairs"]
    assert iter38(patterns, {}) is False
    assert _matcher()(patterns, {}) is True


def test_iter_193_independence_iter_193_alone() -> None:
    # iter 193 (change_count_per_group_constant_across_pairs) pins
    # per-group cell_count. Per-group cell_count constant (K_cells == 2)
    # but per-group output-colour cardinality varies: iter 193 fires,
    # this matcher rejects.
    patterns = {"pair_analyses": [
        _analysis(groups=[
            _group(output_colors=[3], positions=[(0, 0), (0, 1)]),
            _group(output_colors=[5, 6], positions=[(2, 0), (2, 1)]),
        ]),
    ]}
    iter193 = CONDITION_REGISTRY["change_count_per_group_constant_across_pairs"]
    assert iter193(patterns, {}) is True
    assert _matcher()(patterns, {}) is False


def test_iter_193_independence_this_matcher_alone() -> None:
    # Per-group output-colour cardinality constant (K==1 everywhere)
    # but per-group cell_count varies (1 vs 2): this matcher fires,
    # iter 193 rejects.
    patterns = {"pair_analyses": [
        _analysis(groups=[_group(output_colors=[3], positions=[(0, 0)])]),
        _analysis(groups=[_group(output_colors=[5],
                                 positions=[(2, 0), (2, 1)])]),
    ]}
    iter193 = CONDITION_REGISTRY["change_count_per_group_constant_across_pairs"]
    assert iter193(patterns, {}) is False
    assert _matcher()(patterns, {}) is True


def test_iter_193_co_fires_when_both_constant() -> None:
    # Per-group K_colors == 1 AND per-group K_cells == 1: both fire.
    patterns = {"pair_analyses": [
        _analysis(groups=[_group(output_colors=[3], positions=[(0, 0)])]),
        _analysis(groups=[_group(output_colors=[5], positions=[(2, 2)])]),
    ]}
    iter193 = CONDITION_REGISTRY["change_count_per_group_constant_across_pairs"]
    assert iter193(patterns, {}) is True
    assert _matcher()(patterns, {}) is True


def test_iter_195_dual_co_fires_on_balanced_K() -> None:
    # Input-side dual matcher (iter 195) — orthogonal axis (input vs
    # output). Both per-group input K and output K constant at 1:
    # both fire.
    patterns = {"pair_analyses": [
        _analysis(groups=[_group(input_colors=[1], output_colors=[3])]),
        _analysis(groups=[_group(input_colors=[2], output_colors=[5])]),
    ]}
    iter195 = CONDITION_REGISTRY[
        "change_input_color_count_per_group_constant_across_pairs"
    ]
    assert iter195(patterns, {}) is True
    assert _matcher()(patterns, {}) is True


def test_iter_195_dual_fires_alone_on_input_varying_output_constant() -> None:
    # Per-group input K varies (1 vs 2) while output K is constant
    # (K == 1 everywhere). iter 195 rejects, this matcher fires.
    patterns = {"pair_analyses": [
        _analysis(groups=[_group(input_colors=[1], output_colors=[3])]),
        _analysis(groups=[_group(input_colors=[2, 4], output_colors=[5])]),
    ]}
    iter195 = CONDITION_REGISTRY[
        "change_input_color_count_per_group_constant_across_pairs"
    ]
    assert iter195(patterns, {}) is False
    assert _matcher()(patterns, {}) is True


def test_iter_195_dual_input_constant_output_varying() -> None:
    # Per-group input K constant (K == 1) while output K varies
    # (1 vs 2). iter 195 fires, this matcher rejects.
    patterns = {"pair_analyses": [
        _analysis(groups=[_group(input_colors=[1], output_colors=[3])]),
        _analysis(groups=[_group(input_colors=[2], output_colors=[5, 6])]),
    ]}
    iter195 = CONDITION_REGISTRY[
        "change_input_color_count_per_group_constant_across_pairs"
    ]
    assert iter195(patterns, {}) is True
    assert _matcher()(patterns, {}) is False


def test_iter_36_independence_this_matcher_alone() -> None:
    # Per-group K constant (K==1) but per-pair output SET differs
    # across pairs: iter 36 rejects, this matcher fires.
    patterns = {"pair_analyses": [
        _analysis(groups=[_group(output_colors=[3])]),
        _analysis(groups=[_group(output_colors=[5])]),
    ]}
    iter36 = CONDITION_REGISTRY["change_output_colors_constant_across_pairs"]
    assert iter36(patterns, {}) is False
    assert _matcher()(patterns, {}) is True


def test_co_fires_with_grid_size_preserved() -> None:
    # Orthogonal axes: grid_size_preserved is a dimensional flag, this
    # matcher inspects per-group output-colour cardinalities.
    patterns = {
        "grid_size_preserved": True,
        "pair_analyses": [
            _analysis(groups=[_group(output_colors=[3])]),
            _analysis(groups=[_group(output_colors=[5])]),
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
            _analysis(groups=[_group(output_colors=[3])]),
            _analysis(groups=[_group(output_colors=[5])]),
        ],
    }
    fired = recognized_conditions(patterns)
    assert MATCHER_NAME in fired, (
        f"{MATCHER_NAME!r} did not fire on K==1 patterns; got {fired!r}"
    )


def test_recognized_conditions_excludes_on_varying_K() -> None:
    from agent.conditions import recognized_conditions
    patterns = {
        "pair_analyses": [
            _analysis(groups=[_group(output_colors=[3])]),
            _analysis(groups=[_group(output_colors=[5, 6])]),
        ],
    }
    fired = recognized_conditions(patterns)
    assert MATCHER_NAME not in fired, (
        f"{MATCHER_NAME!r} must NOT fire on varying-K patterns; got "
        f"{fired!r}"
    )


def test_recognized_conditions_co_fires_with_iter_18_on_uniform_output() -> None:
    # When every group has K==1 output colour AND that colour is
    # identical, both iter 18 and this matcher fire.
    from agent.conditions import recognized_conditions
    patterns = {
        "pair_analyses": [
            _analysis(groups=[_group(output_colors=[3])]),
            _analysis(groups=[_group(output_colors=[3])]),
        ],
    }
    fired = recognized_conditions(patterns)
    assert "output_color_uniform" in fired
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
