"""
tests/test_singleton_recolor_nonidentity_unanchored.py -- exercise
the iter-223 matcher
``agent.conditions.singleton_recolor_nonidentity_unanchored``.

Pins the matcher's contract per the docstring of
``agent/conditions/singleton_recolor_nonidentity_unanchored.py``:
every group of every example pair has BOTH
``len(set(input_colors)) == 1`` AND
``len(set(output_colors)) == 1`` AND
``set(input_colors) != set(output_colors)`` AND
``len(observed_input_colors) > 1`` (NOT cross-group identity on
the INPUT side) AND
``len(observed_output_colors) > 1`` (NOT cross-group identity on
the OUTPUT side -- the strict-disjoint complement of iter 220 /
iter 221 / iter 222 within iter 218's territory; closes the 2x2
cross-group-identity product axis at the (F, F) cell).

Universal over groups AND pairs; fail-closed on empty / no-group /
malformed input.

Runs without pytest:

    python tests/test_singleton_recolor_nonidentity_unanchored.py

Dependency-free, same runner style as the other tests under
``tests/``.
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


MATCHER_NAME = "singleton_recolor_nonidentity_unanchored"


def _matcher():
    return CONDITION_REGISTRY[MATCHER_NAME]


def _group(input_colors, output_colors, **overrides):
    base = {
        "input_colors": list(input_colors),
        "output_colors": list(output_colors),
        "top_row": 0,
        "top_col": 0,
        "cell_count": max(1, len(input_colors)),
    }
    base.update(overrides)
    return base


def _pair(groups, **overrides):
    base = {
        "input_height": 3,
        "input_width": 3,
        "output_height": 3,
        "output_width": 3,
        "size_match": True,
        "total_changes": sum(g.get("cell_count", 1) for g in groups),
        "num_groups": len(groups),
        "groups": list(groups),
        "input_palette": [0, 1, 2, 3],
        "output_palette": [0, 1, 2, 3],
    }
    base.update(overrides)
    return base


# --------------------------------------------------------------------------
# Smoke / membership tests.
# --------------------------------------------------------------------------

def test_registered_in_global_registry() -> None:
    assert MATCHER_NAME in CONDITION_REGISTRY, (
        f"{MATCHER_NAME!r} not registered; got {sorted(CONDITION_REGISTRY)}"
    )


def test_matcher_is_callable() -> None:
    fn = _matcher()
    assert callable(fn), f"registered entry is not callable: {fn!r}"


# --------------------------------------------------------------------------
# Positive cases.
# --------------------------------------------------------------------------

def test_returns_true_on_canonical_unanchored_function_shaped() -> None:
    # The canonical (F, F) cell: single pair, two groups, distinct
    # C_g's AND distinct K_g's (function-shaped sub-cell: 3 -> 0,
    # 5 -> 7).
    patterns = {"pair_analyses": [
        _pair([_group([3], [0]), _group([5], [7])]),
    ]}
    assert _matcher()(patterns, {}) is True


def test_returns_true_on_iter_10_canonical_fixture() -> None:
    # The iter-10 canonical fixture (3 groups per pair, ic=[0]/oc=[3],
    # ic=[1]/oc=[4], ic=[2]/oc=[5]) -- cross-group identity fails on
    # BOTH sides (observed_input={0,1,2}, observed_output={3,4,5}).
    # This is the DISTINGUISHING fixture vs iter 220 / 221 / 222
    # where one or both sides are anchored at a single value.
    patterns = {"pair_analyses": [
        _pair([_group([0], [3]), _group([1], [4]), _group([2], [5])]),
    ]}
    assert _matcher()(patterns, {}) is True


def test_returns_true_with_three_groups_three_distinct_C_and_K() -> None:
    patterns = {"pair_analyses": [
        _pair([_group([3], [0]), _group([7], [1]), _group([5], [2])]),
    ]}
    assert _matcher()(patterns, {}) is True


def test_returns_true_with_non_function_shape_C_to_multiple_K() -> None:
    # Non-function-shaped sub-cell: C=3 maps to BOTH K=0 and K=7.
    # This matcher still fires (per-group ic != oc on every group;
    # |observed_input| = {3, 5} > 1; |observed_output| = {0, 7} > 1).
    # Iter 8 would REJECT this fixture -- DISTINGUISHING witness vs
    # the function-shaped sub-cell.
    patterns = {"pair_analyses": [
        _pair([_group([3], [0]), _group([3], [7]), _group([5], [7])]),
    ]}
    assert _matcher()(patterns, {}) is True


def test_returns_true_with_C_K_varying_across_pairs() -> None:
    # Multi-pair: per-pair contributions vary, but observed_input
    # and observed_output both exceed 1 across the union.
    patterns = {
        "pair_analyses": [
            _pair([_group([3], [0]), _group([5], [7])]),
            _pair([_group([1], [4])]),
        ],
    }
    assert _matcher()(patterns, {}) is True


def test_returns_true_with_duplicate_entries_in_color_lists() -> None:
    # Colour lists are de-duplicated set-wise by the matcher;
    # duplicates in the list must not change the verdict.
    patterns = {"pair_analyses": [
        _pair([_group([4, 4], [7, 7]), _group([2], [1])]),
    ]}
    assert _matcher()(patterns, {}) is True


def test_returns_true_on_color_zero_and_nine_witnesses() -> None:
    # Edge: C=0 and K=9 (boundary colours) both witnessed.
    patterns = {"pair_analyses": [
        _pair([_group([0], [3]), _group([9], [4])]),
    ]}
    assert _matcher()(patterns, {}) is True


# --------------------------------------------------------------------------
# Negative cases.
# --------------------------------------------------------------------------

def test_returns_false_on_iter_220_territory_both_anchored() -> None:
    # KEY iter-220 mutual-exclusion witness: iter 220 demands cross-
    # group identity on BOTH sides. This matcher demands NON-identity
    # on BOTH sides. Disjoint.
    patterns = {"pair_analyses": [
        _pair([_group([3], [0]), _group([3], [0])]),
    ]}
    assert _matcher()(patterns, {}) is False


def test_returns_false_on_iter_221_territory_input_anchored() -> None:
    # KEY iter-221 mutual-exclusion witness: iter 221 demands input-
    # side cross-group identity AND output-side cross-group identity
    # failure. This matcher demands NON-identity on BOTH sides.
    # Disjoint on the input-anchor split.
    patterns = {"pair_analyses": [
        _pair([_group([3], [0]), _group([3], [7])]),
    ]}
    assert _matcher()(patterns, {}) is False


def test_returns_false_on_iter_222_territory_output_anchored() -> None:
    # KEY iter-222 mutual-exclusion witness: iter 222 demands output-
    # side cross-group identity AND input-side cross-group identity
    # failure. This matcher demands NON-identity on BOTH sides.
    # Disjoint on the output-anchor split.
    patterns = {"pair_analyses": [
        _pair([_group([3], [0]), _group([7], [0])]),
    ]}
    assert _matcher()(patterns, {}) is False


def test_returns_false_on_global_identity_C_eq_K() -> None:
    # KEY iter-219 mutual-exclusion witness: iter 219 fires when C ==
    # K globally. This matcher rejects (per-group ic != oc fails).
    patterns = {"pair_analyses": [
        _pair([_group([3], [3]), _group([3], [3])]),
    ]}
    assert _matcher()(patterns, {}) is False


def test_returns_false_when_single_group_only() -> None:
    # A single group means |observed_input| == 1 AND
    # |observed_output| == 1 -- this matcher rejects on both anchor
    # checks (it occupies the cell where BOTH sides have >1 distinct
    # value witnessed).
    patterns = {"pair_analyses": [_pair([_group([3], [0])])]}
    assert _matcher()(patterns, {}) is False


def test_returns_false_when_only_input_side_varies() -> None:
    # |observed_input| = {3, 5} > 1 but |observed_output| = {0} == 1
    # -- this is iter-222 territory, not this matcher's. Rejected on
    # the output-anchor check.
    patterns = {"pair_analyses": [
        _pair([_group([3], [0]), _group([5], [0])]),
    ]}
    assert _matcher()(patterns, {}) is False


def test_returns_false_when_only_output_side_varies() -> None:
    # |observed_input| = {3} == 1 but |observed_output| = {0, 7} > 1
    # -- this is iter-221 territory, not this matcher's. Rejected on
    # the input-anchor check.
    patterns = {"pair_analyses": [
        _pair([_group([3], [0]), _group([3], [7])]),
    ]}
    assert _matcher()(patterns, {}) is False


def test_returns_false_when_any_group_has_multi_input() -> None:
    patterns = {"pair_analyses": [
        _pair([_group([3, 4], [0]), _group([7], [1])]),
    ]}
    assert _matcher()(patterns, {}) is False


def test_returns_false_when_any_group_has_multi_output() -> None:
    patterns = {"pair_analyses": [
        _pair([_group([3], [0, 4]), _group([7], [1])]),
    ]}
    assert _matcher()(patterns, {}) is False


def test_returns_false_when_one_of_many_groups_is_identity() -> None:
    # Universal-over-groups semantic: a single identity group (ic ==
    # oc) violates the per-group ic != oc demand on that group.
    patterns = {"pair_analyses": [
        _pair([
            _group([3], [0]),
            _group([5], [5]),   # offending identity (ic == oc == [5])
            _group([7], [1]),
        ]),
    ]}
    assert _matcher()(patterns, {}) is False


def test_returns_false_on_empty_pair_analyses() -> None:
    assert _matcher()({"pair_analyses": []}, {}) is False


def test_returns_false_on_missing_pair_analyses_key() -> None:
    assert _matcher()({}, {}) is False


def test_returns_false_on_non_list_pair_analyses() -> None:
    for bad in (None, 42, "oops", {"a": 1}, (), True):
        assert _matcher()({"pair_analyses": bad}, {}) is False, (
            f"pair_analyses={bad!r} should not fire"
        )


def test_returns_false_on_non_dict_patterns() -> None:
    assert _matcher()(None, {}) is False         # type: ignore[arg-type]
    assert _matcher()([], {}) is False           # type: ignore[arg-type]
    assert _matcher()("oops", {}) is False       # type: ignore[arg-type]
    assert _matcher()(42, {}) is False           # type: ignore[arg-type]


def test_returns_false_when_groups_empty_on_any_pair() -> None:
    # Identity-territory rejection: a zero-group pair collapses into
    # iter 13's no-blob-identity territory; this matcher is the
    # singleton-blob input-per-group / output-per-group strict-
    # recolour cell, disjoint by design.
    patterns = {
        "pair_analyses": [
            _pair([_group([3], [0]), _group([5], [7])]),
            _pair([], num_groups=0, total_changes=0),
        ],
    }
    assert _matcher()(patterns, {}) is False


def test_returns_false_on_missing_groups_key() -> None:
    analysis = _pair([_group([3], [0]), _group([5], [7])])
    del analysis["groups"]
    patterns = {"pair_analyses": [analysis]}
    assert _matcher()(patterns, {}) is False


def test_returns_false_on_non_list_groups() -> None:
    for bad in (None, 42, "oops", {"a": 1}, (), True):
        analysis = _pair([_group([3], [0]), _group([5], [7])])
        analysis["groups"] = bad
        patterns = {"pair_analyses": [analysis]}
        assert _matcher()(patterns, {}) is False, (
            f"groups={bad!r} should not fire"
        )


def test_returns_false_when_any_analysis_is_not_dict() -> None:
    patterns = {
        "pair_analyses": [
            _pair([_group([3], [0]), _group([5], [7])]),
            "not-a-dict",
            _pair([_group([3], [0]), _group([5], [7])]),
        ],
    }
    assert _matcher()(patterns, {}) is False


def test_returns_false_when_any_group_is_not_dict() -> None:
    analysis = _pair([_group([3], [0]), _group([5], [7])])
    analysis["groups"] = [_group([3], [0]), "not-a-dict"]
    patterns = {"pair_analyses": [analysis]}
    assert _matcher()(patterns, {}) is False


# --------------------------------------------------------------------------
# Strict-type-gate cases.
# --------------------------------------------------------------------------

def test_returns_false_when_input_colors_missing() -> None:
    analysis = _pair([_group([3], [0]), _group([5], [7])])
    del analysis["groups"][0]["input_colors"]
    patterns = {"pair_analyses": [analysis]}
    assert _matcher()(patterns, {}) is False


def test_returns_false_when_output_colors_missing() -> None:
    analysis = _pair([_group([3], [0]), _group([5], [7])])
    del analysis["groups"][0]["output_colors"]
    patterns = {"pair_analyses": [analysis]}
    assert _matcher()(patterns, {}) is False


def test_returns_false_when_input_colors_empty() -> None:
    analysis = _pair([_group([3], [0]), _group([5], [7])])
    analysis["groups"][0]["input_colors"] = []
    patterns = {"pair_analyses": [analysis]}
    assert _matcher()(patterns, {}) is False


def test_returns_false_when_output_colors_empty() -> None:
    analysis = _pair([_group([3], [0]), _group([5], [7])])
    analysis["groups"][0]["output_colors"] = []
    patterns = {"pair_analyses": [analysis]}
    assert _matcher()(patterns, {}) is False


def test_returns_false_when_input_colors_not_list() -> None:
    for bad in (None, 42, "oops", {"a": 1}, (3,), True, {3}):
        analysis = _pair([_group([3], [0]), _group([5], [7])])
        analysis["groups"][0]["input_colors"] = bad
        patterns = {"pair_analyses": [analysis]}
        assert _matcher()(patterns, {}) is False, (
            f"input_colors={bad!r} should not fire"
        )


def test_returns_false_when_output_colors_not_list() -> None:
    for bad in (None, 42, "oops", {"a": 1}, (3,), True, {3}):
        analysis = _pair([_group([3], [0]), _group([5], [7])])
        analysis["groups"][0]["output_colors"] = bad
        patterns = {"pair_analyses": [analysis]}
        assert _matcher()(patterns, {}) is False, (
            f"output_colors={bad!r} should not fire"
        )


def test_returns_false_when_color_list_contains_bool() -> None:
    # bools are an int subclass; the strict-type gate rejects them
    # (same posture as iter 14 / 18 / 200-206 / 213 / 214 / 215 / 217 /
    # 218 / 219 / 220 / 221 / 222).
    analysis = _pair([_group([True], [False]), _group([5], [7])])
    patterns = {"pair_analyses": [analysis]}
    assert _matcher()(patterns, {}) is False

    analysis2 = _pair([_group([3], [False]), _group([5], [7])])
    patterns2 = {"pair_analyses": [analysis2]}
    assert _matcher()(patterns2, {}) is False


def test_returns_false_when_color_list_contains_non_int() -> None:
    analysis = _pair([_group(["3"], [0]), _group([5], [7])])
    patterns = {"pair_analyses": [analysis]}
    assert _matcher()(patterns, {}) is False

    analysis2 = _pair([_group([3], [0.0]), _group([5], [7])])
    patterns2 = {"pair_analyses": [analysis2]}
    assert _matcher()(patterns2, {}) is False


def test_returns_false_when_color_out_of_range() -> None:
    # Per-group colour values must be in [0, 9]; the iter-180 erase
    # sentinel 13 and the < 0 / > 9 cases are rejected (same as iter
    # 215 / 217 / 218 / 219 / 220 / 221 / 222's strict-range gate).
    analysis = _pair([_group([13], [0]), _group([5], [7])])
    patterns = {"pair_analyses": [analysis]}
    assert _matcher()(patterns, {}) is False

    analysis2 = _pair([_group([-1], [0]), _group([5], [7])])
    patterns2 = {"pair_analyses": [analysis2]}
    assert _matcher()(patterns2, {}) is False


# --------------------------------------------------------------------------
# Behavioural-contract cases.
# --------------------------------------------------------------------------

def test_is_side_effect_free_on_inputs() -> None:
    patterns = {"pair_analyses": [
        _pair([_group([3], [0]), _group([5], [7])]),
    ]}
    params = {"unused": 1}
    before_p = copy.deepcopy(patterns)
    before_q = copy.deepcopy(params)
    _matcher()(patterns, params)
    assert patterns == before_p, "matcher mutated patterns"
    assert params == before_q, "matcher mutated params"


def test_is_deterministic_across_repeats() -> None:
    patterns = {"pair_analyses": [
        _pair([_group([3], [0]), _group([5], [7])]),
    ]}
    results = [_matcher()(patterns, {}) for _ in range(5)]
    assert len(set(results)) == 1, f"non-deterministic outputs: {results}"


def test_returned_value_is_boolean_not_truthy() -> None:
    # recognized_conditions filters on ``match(...) is True`` exactly,
    # so the matcher must return literal Booleans.
    out_true = _matcher()(
        {"pair_analyses": [_pair([_group([3], [0]), _group([5], [7])])]}, {}
    )
    out_false = _matcher()(
        {"pair_analyses": [_pair([_group([3], [0]), _group([3], [0])])]}, {}
    )
    assert out_true is True, f"expected literal True, got {out_true!r}"
    assert out_false is False, f"expected literal False, got {out_false!r}"


def test_ignores_dimensional_fields() -> None:
    # Dimensional fields are orthogonal -- arbitrary dim combinations
    # must not affect the matcher's verdict.
    analysis = _pair([_group([3], [0]), _group([5], [7])],
                     input_height=7, input_width=9,
                     output_height=2, output_width=3, size_match=False)
    patterns = {"pair_analyses": [analysis]}
    assert _matcher()(patterns, {}) is True


def test_ignores_palette_fields() -> None:
    # Whole-grid palette fields are orthogonal -- this matcher only
    # inspects per-group colour lists.
    analysis = _pair([_group([3], [0]), _group([5], [7])],
                     input_palette=[9, 9, 9],
                     output_palette=[1, 1, 1])
    patterns = {"pair_analyses": [analysis]}
    assert _matcher()(patterns, {}) is True


# --------------------------------------------------------------------------
# Orthogonality / refinement / mutual-exclusion matrix against existing
# axes.
# --------------------------------------------------------------------------

def test_strict_refinement_of_iter_218_nonidentity_per_group() -> None:
    # Strict refinement: this matcher fires => iter 218 fires (per-
    # group |ic| == |oc| == 1 AND per-group ic != oc on every group).
    # Converse fails when iter 218 fires WITH cross-group identity on
    # either side (iter 220 / 221 / 222 territory).
    iter218 = CONDITION_REGISTRY["singleton_recolor_nonidentity_per_group"]

    # This matcher fires => iter 218 fires.
    p1 = {"pair_analyses": [_pair([_group([3], [0]), _group([5], [7])])]}
    assert _matcher()(p1, {}) is True and iter218(p1, {}) is True

    # Iter 218 fires (iter 220 cell), this matcher rejects.
    p2 = {"pair_analyses": [_pair([_group([3], [0]), _group([3], [0])])]}
    assert iter218(p2, {}) is True and _matcher()(p2, {}) is False


def test_strict_mutual_exclusion_with_iter_220_both_anchored() -> None:
    # KEY witness: this matcher and iter 220 are pairwise disjoint
    # named cells on the (T, T) vs (F, F) corners of iter 218's 2x2
    # cross-group-identity axis.
    iter220 = CONDITION_REGISTRY["singleton_recolor_nonidentity"]

    # This matcher fires; iter 220 rejects.
    p1 = {"pair_analyses": [_pair([_group([3], [0]), _group([5], [7])])]}
    assert _matcher()(p1, {}) is True and iter220(p1, {}) is False

    # Iter 220 fires; this matcher rejects.
    p2 = {"pair_analyses": [_pair([_group([3], [0]), _group([3], [0])])]}
    assert iter220(p2, {}) is True and _matcher()(p2, {}) is False


def test_strict_mutual_exclusion_with_iter_221_input_anchored() -> None:
    # KEY iter-221 mutual-exclusion witness: iter 221 names (input-
    # anchored, output-per-group); this matcher names (input-per-group,
    # output-per-group). Disjoint by the input-anchor split.
    iter221 = CONDITION_REGISTRY["singleton_recolor_nonidentity_input_anchored"]

    # This matcher fires; iter 221 rejects.
    p1 = {"pair_analyses": [_pair([_group([3], [0]), _group([5], [7])])]}
    assert _matcher()(p1, {}) is True and iter221(p1, {}) is False

    # Iter 221 fires; this matcher rejects.
    p2 = {"pair_analyses": [_pair([_group([3], [0]), _group([3], [7])])]}
    assert iter221(p2, {}) is True and _matcher()(p2, {}) is False


def test_strict_mutual_exclusion_with_iter_222_output_anchored() -> None:
    # KEY iter-222 mutual-exclusion witness: iter 222 names (input-
    # per-group, output-anchored); this matcher names (input-per-group,
    # output-per-group). Disjoint by the output-anchor split.
    iter222 = CONDITION_REGISTRY["singleton_recolor_nonidentity_output_anchored"]

    # This matcher fires; iter 222 rejects.
    p1 = {"pair_analyses": [_pair([_group([3], [0]), _group([5], [7])])]}
    assert _matcher()(p1, {}) is True and iter222(p1, {}) is False

    # Iter 222 fires; this matcher rejects.
    p2 = {"pair_analyses": [_pair([_group([3], [0]), _group([7], [0])])]}
    assert iter222(p2, {}) is True and _matcher()(p2, {}) is False


def test_strict_mutual_exclusion_with_iter_219_identity() -> None:
    # Iter 219 demands C == K globally; this matcher demands per-
    # group ic != oc. The two are pairwise disjoint.
    iter219 = CONDITION_REGISTRY["singleton_recolor_identity"]

    # This matcher fires; iter 219 rejects.
    p1 = {"pair_analyses": [_pair([_group([3], [0]), _group([5], [7])])]}
    assert _matcher()(p1, {}) is True and iter219(p1, {}) is False

    # Iter 219 fires; this matcher rejects.
    p2 = {"pair_analyses": [_pair([_group([3], [3]), _group([3], [3])])]}
    assert iter219(p2, {}) is True and _matcher()(p2, {}) is False


def test_strict_mutual_exclusion_with_iter_217_identity_per_group() -> None:
    # Iter 217 demands per-group ic == oc on every group; this matcher
    # forces per-group ic != oc on every group. Disjoint.
    iter217 = CONDITION_REGISTRY["singleton_recolor_identity_per_group"]

    # This matcher fires; iter 217 rejects.
    p1 = {"pair_analyses": [_pair([_group([3], [0]), _group([5], [7])])]}
    assert _matcher()(p1, {}) is True and iter217(p1, {}) is False

    # Iter 217 fires; this matcher rejects.
    p2 = {"pair_analyses": [_pair([_group([3], [3]), _group([5], [5])])]}
    assert iter217(p2, {}) is True and _matcher()(p2, {}) is False


def test_strict_mutual_exclusion_with_iter_216_both_anchored() -> None:
    # Iter 216 demands cross-group identity on BOTH sides. This
    # matcher demands NON-identity on BOTH sides. Disjoint.
    iter216 = CONDITION_REGISTRY["singleton_recolor"]

    # This matcher fires; iter 216 rejects.
    p1 = {"pair_analyses": [_pair([_group([3], [0]), _group([5], [7])])]}
    assert _matcher()(p1, {}) is True and iter216(p1, {}) is False

    # Iter 216 fires (C == K globally is allowed by iter 216); this
    # matcher rejects.
    p2 = {"pair_analyses": [_pair([_group([3], [3]), _group([3], [3])])]}
    assert iter216(p2, {}) is True and _matcher()(p2, {}) is False


def test_strict_refinement_of_iter_215_singleton_recolor_per_group() -> None:
    # Iter 215 demands per-group |ic| == |oc| == 1 only; this matcher
    # additionally demands per-group ic != oc AND
    # |observed_input| > 1 AND |observed_output| > 1.
    iter215 = CONDITION_REGISTRY["singleton_recolor_per_group"]

    # This matcher fires => iter 215 fires.
    p1 = {"pair_analyses": [_pair([_group([3], [0]), _group([5], [7])])]}
    assert _matcher()(p1, {}) is True and iter215(p1, {}) is True

    # Iter 215 fires (per-group |ic| == |oc| == 1), this matcher
    # rejects (per-group ic == oc on some group).
    p2 = {"pair_analyses": [_pair([_group([3], [0]), _group([3], [3])])]}
    assert iter215(p2, {}) is True and _matcher()(p2, {}) is False


def test_strict_mutual_exclusion_with_iter_14_input_color_uniform() -> None:
    # Iter 14 demands cross-group / cross-pair input uniformity;
    # this matcher demands |observed_input| > 1. Disjoint.
    iter14 = CONDITION_REGISTRY["input_color_uniform"]

    # This matcher fires; iter 14 rejects.
    p1 = {"pair_analyses": [_pair([_group([3], [0]), _group([5], [7])])]}
    assert _matcher()(p1, {}) is True and iter14(p1, {}) is False

    # Iter 14 fires (input globally uniform C); this matcher rejects.
    p2 = {"pair_analyses": [_pair([_group([3], [0]), _group([3], [7])])]}
    assert iter14(p2, {}) is True and _matcher()(p2, {}) is False


def test_strict_mutual_exclusion_with_iter_18_output_color_uniform() -> None:
    # Iter 18 demands cross-group / cross-pair output uniformity;
    # this matcher demands |observed_output| > 1. Disjoint. Note this
    # is the DUAL of the iter-14 relation; the previous iter (iter
    # 222) had STRICT REFINEMENT of iter 18 (since iter 222 demanded
    # output-side anchor); this matcher demands output-side NOT
    # anchored, hence DISJOINT.
    iter18 = CONDITION_REGISTRY["output_color_uniform"]

    # This matcher fires; iter 18 rejects.
    p1 = {"pair_analyses": [_pair([_group([3], [0]), _group([5], [7])])]}
    assert _matcher()(p1, {}) is True and iter18(p1, {}) is False

    # Iter 18 fires (output globally uniform K); this matcher rejects.
    p2 = {"pair_analyses": [_pair([_group([3], [0]), _group([5], [0])])]}
    assert iter18(p2, {}) is True and _matcher()(p2, {}) is False


def test_mutual_exclusion_with_identity_transformation() -> None:
    # Iter 13 fires iff every pair has zero change groups. This
    # matcher rejects the no-group case. Disjoint by design.
    ident = CONDITION_REGISTRY["identity_transformation"]
    p = {"pair_analyses": [_pair([], num_groups=0, total_changes=0)]}
    assert ident(p, {}) is True and _matcher()(p, {}) is False


def test_independent_of_iter_8_consistent_color_mapping() -> None:
    # Iter 8 demands a function-shaped global mapping (every input
    # colour maps to exactly one output colour). This matcher's
    # territory admits both function-shaped and non-function-shaped
    # sub-cells.
    iter8 = CONDITION_REGISTRY["consistent_color_mapping"]

    # Function-shaped sub-cell: this matcher fires AND iter 8 fires.
    p1 = {"pair_analyses": [_pair([_group([3], [0]), _group([5], [7])])]}
    assert _matcher()(p1, {}) is True and iter8(p1, {}) is True

    # Non-function-shaped sub-cell: this matcher fires AND iter 8
    # rejects (C=3 maps to both 0 and 7).
    p2 = {"pair_analyses": [
        _pair([_group([3], [0]), _group([3], [7]), _group([5], [7])]),
    ]}
    assert _matcher()(p2, {}) is True and iter8(p2, {}) is False


def test_strict_implication_of_iter_203_disjoint_per_group() -> None:
    # Iter 203 demands per-group set(ic) intersect set(oc) == empty.
    # Strict implication: this matcher fires => iter 203 fires (per-
    # group ic = [C_g] / oc = [K_g] with C_g != K_g; on the singleton
    # row this forces ic intersect oc == empty).
    iter203 = CONDITION_REGISTRY[
        "output_colors_disjoint_from_input_colors_per_group"
    ]

    # This matcher fires => iter 203 fires.
    p1 = {"pair_analyses": [_pair([_group([3], [0]), _group([5], [7])])]}
    assert _matcher()(p1, {}) is True and iter203(p1, {}) is True

    # Iter 203 fires (multi-element disjoint), this matcher rejects.
    p2 = {"pair_analyses": [_pair([_group([3, 4], [0, 1])])]}
    assert iter203(p2, {}) is True and _matcher()(p2, {}) is False


def test_strict_mutual_exclusion_with_iter_201_set_equality_per_group() -> None:
    # Iter 201 demands per-group set(ic) == set(oc). This matcher
    # pins per-group ic == [C_g] / oc == [K_g] with C_g != K_g per
    # group, forcing per-group set(ic) != set(oc). Disjoint.
    iter201 = CONDITION_REGISTRY[
        "output_colors_equals_input_colors_per_group"
    ]

    # This matcher fires; iter 201 rejects.
    p1 = {"pair_analyses": [_pair([_group([3], [0]), _group([5], [7])])]}
    assert _matcher()(p1, {}) is True and iter201(p1, {}) is False

    # Iter 201 fires (per-group ic == oc); this matcher rejects.
    p2 = {"pair_analyses": [_pair([_group([3], [3])])]}
    assert iter201(p2, {}) is True and _matcher()(p2, {}) is False


def test_strict_refinement_of_iter_213_consistent_color_mapping_per_group() -> None:
    # Iter 213 demands per-group |oc| == 1 only. This matcher
    # additionally requires per-group |ic| == 1 AND per-group ic !=
    # oc AND |observed_input| > 1 AND |observed_output| > 1.
    iter213 = CONDITION_REGISTRY["consistent_color_mapping_per_group"]

    # This matcher fires => iter 213 fires.
    p1 = {"pair_analyses": [_pair([_group([3], [0]), _group([5], [7])])]}
    assert _matcher()(p1, {}) is True and iter213(p1, {}) is True

    # Iter 213 fires with per-group |ic| > 1; this matcher rejects.
    p2 = {"pair_analyses": [_pair([_group([3, 4], [0]), _group([3, 4], [7])])]}
    assert iter213(p2, {}) is True and _matcher()(p2, {}) is False


def test_strict_refinement_of_iter_214_input_color_uniform_per_group() -> None:
    # Iter 214 demands per-group |ic| == 1 only. This matcher
    # additionally requires per-group |oc| == 1 AND per-group ic !=
    # oc AND |observed_input| > 1 AND |observed_output| > 1.
    iter214 = CONDITION_REGISTRY["input_color_uniform_per_group"]

    # This matcher fires => iter 214 fires.
    p1 = {"pair_analyses": [_pair([_group([3], [0]), _group([5], [7])])]}
    assert _matcher()(p1, {}) is True and iter214(p1, {}) is True

    # Iter 214 fires with per-group |oc| > 1; this matcher rejects.
    p2 = {"pair_analyses": [_pair([_group([3], [0, 4]), _group([3], [7, 1])])]}
    assert iter214(p2, {}) is True and _matcher()(p2, {}) is False


def test_strict_refinement_of_iter_197_at_K_prod_eq_1() -> None:
    # Iter 197 demands |ic|*|oc| per group constant across pairs at
    # SOME K_prod. This matcher pins K_prod == 1 per group AND
    # additionally requires the input-per-group / output-per-group
    # strict-recolour shape.
    iter197 = CONDITION_REGISTRY[
        "change_color_mapping_count_per_group_constant_across_pairs"
    ]

    # This matcher fires => iter 197 fires at K_prod == 1.
    p1 = {
        "pair_analyses": [
            _pair([_group([3], [0]), _group([5], [7])]),
            _pair([_group([3], [0]), _group([5], [7])]),
        ],
    }
    assert _matcher()(p1, {}) is True and iter197(p1, {}) is True

    # Iter 197 fires at K_prod == 1 with iter-220 territory (input
    # anchored); this matcher rejects.
    p2 = {
        "pair_analyses": [
            _pair([_group([3], [0])]),
            _pair([_group([3], [0])]),
        ],
    }
    assert iter197(p2, {}) is True and _matcher()(p2, {}) is False


def test_recognized_conditions_includes_matcher_on_iter_10_fixture() -> None:
    # DISTINGUISHING test vs iter 220 / 221 / 222: the iter-10
    # canonical fixture (ic=[0]/oc=[3], ic=[1]/oc=[4], ic=[2]/oc=[5])
    # has |observed_input|=3 > 1 AND |observed_output|=3 > 1 -- this
    # matcher FIRES on this fixture (unlike iters 220 / 221 / 222
    # which all reject).
    from agent.conditions import recognized_conditions
    patterns = {"pair_analyses": [
        _pair([_group([0], [3]), _group([1], [4]), _group([2], [5])]),
    ]}
    fired = recognized_conditions(patterns)
    assert MATCHER_NAME in fired, (
        f"{MATCHER_NAME!r} did not fire on the iter-10 canonical "
        f"fixture (both-sides-vary); got {fired!r}"
    )
    # iter 218 must still co-fire (this matcher is a strict refinement).
    assert "singleton_recolor_nonidentity_per_group" in fired, (
        "iter 218 regression: must still co-fire on this matcher's "
        f"territory; got {fired!r}"
    )
    # iter 220 / 221 / 222 must NOT fire (disjoint cells).
    for sibling in (
        "singleton_recolor_nonidentity",
        "singleton_recolor_nonidentity_input_anchored",
        "singleton_recolor_nonidentity_output_anchored",
    ):
        assert sibling not in fired, (
            f"{sibling!r} should not fire on the (F, F) cell; got "
            f"{fired!r}"
        )


def test_recognized_conditions_excludes_on_iter_220_territory() -> None:
    # On a whole-task non-identity-on-singleton fixture (single
    # global C and K with C != K), iter 220 fires but this matcher
    # rejects (BOTH-side cross-group identity).
    from agent.conditions import recognized_conditions
    patterns = {
        "pair_analyses": [
            _pair([_group([3], [0]), _group([3], [0])]),
        ],
    }
    fired = recognized_conditions(patterns)
    assert MATCHER_NAME not in fired, (
        f"{MATCHER_NAME!r} should NOT fire on iter-220 territory; "
        f"got {fired!r}"
    )
    # No regression on iter 220.
    assert "singleton_recolor_nonidentity" in fired, (
        "iter 220 regression: singleton_recolor_nonidentity should "
        f"still fire on global C != K non-identity; got {fired!r}"
    )


# --------------------------------------------------------------------------
# Test runner (dependency-free, same style as the other tests).
# --------------------------------------------------------------------------

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
