"""
tests/test_singleton_recolor_nonidentity_unanchored_function_shaped.py
-- exercise the iter-224 matcher ``agent.conditions.singleton_recolor_
nonidentity_unanchored_function_shaped``.

Pins the matcher's contract per the docstring of
``agent/conditions/singleton_recolor_nonidentity_unanchored_function_
shaped.py``: every group of every example pair has BOTH
``len(set(input_colors)) == 1`` AND
``len(set(output_colors)) == 1`` AND
``set(input_colors) != set(output_colors)`` AND
``len(observed_input_colors) > 1`` (NOT cross-group identity on
the INPUT side) AND
``len(observed_output_colors) > 1`` (NOT cross-group identity on
the OUTPUT side) AND the (C_g, K_g) cross-product is FUNCTION-SHAPED
(every distinct C_g maps to exactly one K_g across all groups and
pairs -- the iter-8 ^ iter-223 cofire cell).

Universal over groups AND pairs; fail-closed on empty / no-group /
malformed input.

Runs without pytest:

    python tests/test_singleton_recolor_nonidentity_unanchored_function_shaped.py

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


MATCHER_NAME = "singleton_recolor_nonidentity_unanchored_function_shaped"


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

def test_returns_true_on_canonical_function_shaped() -> None:
    # The canonical function-shape sub-cell of iter 223: single pair,
    # two groups, distinct C_g's AND distinct K_g's (3 -> 0, 5 -> 7).
    patterns = {"pair_analyses": [
        _pair([_group([3], [0]), _group([5], [7])]),
    ]}
    assert _matcher()(patterns, {}) is True


def test_returns_true_on_iter_10_canonical_fixture() -> None:
    # The iter-10 canonical fixture (3 groups per pair, ic=[0]/oc=[3],
    # ic=[1]/oc=[4], ic=[2]/oc=[5]) is function-shaped (0 -> 3, 1 -> 4,
    # 2 -> 5). This is the DISTINGUISHING co-fire witness vs the
    # non-function-shaped sub-cell.
    patterns = {"pair_analyses": [
        _pair([_group([0], [3]), _group([1], [4]), _group([2], [5])]),
    ]}
    assert _matcher()(patterns, {}) is True


def test_returns_true_with_three_groups_three_distinct_C_and_K() -> None:
    patterns = {"pair_analyses": [
        _pair([_group([3], [0]), _group([7], [1]), _group([5], [2])]),
    ]}
    assert _matcher()(patterns, {}) is True


def test_returns_true_when_same_mapping_repeats_across_groups() -> None:
    # Function-shape allows repeated (C_g, K_g) pairs (3 -> 0 twice;
    # 5 -> 7 once). The constraint is "every C_g maps to exactly one
    # K_g", not "every C_g is distinct".
    patterns = {"pair_analyses": [
        _pair([_group([3], [0]), _group([3], [0]), _group([5], [7])]),
    ]}
    assert _matcher()(patterns, {}) is True


def test_returns_true_with_C_K_function_shaped_across_pairs() -> None:
    # Multi-pair: per-pair contributions vary, but the global C_g ->
    # K_g mapping is function-shaped across the union (3 -> 0; 5 -> 7;
    # 1 -> 4).
    patterns = {
        "pair_analyses": [
            _pair([_group([3], [0]), _group([5], [7])]),
            _pair([_group([1], [4])]),
        ],
    }
    assert _matcher()(patterns, {}) is True


def test_returns_true_with_duplicate_entries_in_color_lists() -> None:
    # Colour lists are de-duplicated set-wise by the matcher; duplicates
    # in the list must not change the verdict.
    patterns = {"pair_analyses": [
        _pair([_group([4, 4], [7, 7]), _group([2], [1])]),
    ]}
    assert _matcher()(patterns, {}) is True


def test_returns_true_on_color_zero_and_nine_witnesses() -> None:
    # Edge: C=0 and K=9 (boundary colours) both witnessed; function-
    # shaped (0 -> 3, 9 -> 4).
    patterns = {"pair_analyses": [
        _pair([_group([0], [3]), _group([9], [4])]),
    ]}
    assert _matcher()(patterns, {}) is True


def test_returns_true_when_function_shape_via_cross_pair_consistency() -> None:
    # Pair 1: 3 -> 0. Pair 2: 3 -> 0 (consistent), 5 -> 7. Global
    # function-shape holds (3 -> 0 in both pairs; 5 -> 7 newly).
    patterns = {
        "pair_analyses": [
            _pair([_group([3], [0])]),
            _pair([_group([3], [0]), _group([5], [7])]),
        ],
    }
    # But this fails iter 223's |observed_input| > 1 on a single pair --
    # we need BOTH sides > 1 across the union. {3, 5} > 1 AND {0, 7} > 1.
    assert _matcher()(patterns, {}) is True


# --------------------------------------------------------------------------
# Negative cases.
# --------------------------------------------------------------------------

def test_returns_false_on_non_function_shape_C_to_multiple_K() -> None:
    # KEY iter-8 mutual-exclusion witness: C=3 maps to BOTH K=0 and
    # K=7 across the groups. This matcher REJECTS (function-shape
    # fails). The COMPANION (xv) cell -- the strict-complement of
    # this matcher within iter 223. Iter 223 still fires.
    patterns = {"pair_analyses": [
        _pair([_group([3], [0]), _group([3], [7]), _group([5], [7])]),
    ]}
    assert _matcher()(patterns, {}) is False


def test_returns_false_on_non_function_shape_across_pairs() -> None:
    # Pair 1: 3 -> 0. Pair 2: 3 -> 7 (inconsistent). Function-shape
    # fails on the union (C=3 maps to both 0 and 7).
    patterns = {
        "pair_analyses": [
            _pair([_group([3], [0]), _group([5], [4])]),
            _pair([_group([3], [7]), _group([5], [4])]),
        ],
    }
    assert _matcher()(patterns, {}) is False


def test_returns_false_on_iter_220_territory_both_anchored() -> None:
    # KEY iter-220 mutual-exclusion witness: iter 220 demands cross-
    # group identity on BOTH sides; this matcher (via iter 223)
    # demands NON-identity on BOTH sides.
    patterns = {"pair_analyses": [
        _pair([_group([3], [0]), _group([3], [0])]),
    ]}
    assert _matcher()(patterns, {}) is False


def test_returns_false_on_iter_221_territory_input_anchored() -> None:
    # Iter 221 demands input-side cross-group identity; this matcher
    # demands NON-identity on the INPUT side.
    patterns = {"pair_analyses": [
        _pair([_group([3], [0]), _group([3], [7])]),
    ]}
    assert _matcher()(patterns, {}) is False


def test_returns_false_on_iter_222_territory_output_anchored() -> None:
    # Iter 222 demands output-side cross-group identity; this matcher
    # demands NON-identity on the OUTPUT side.
    patterns = {"pair_analyses": [
        _pair([_group([3], [0]), _group([7], [0])]),
    ]}
    assert _matcher()(patterns, {}) is False


def test_returns_false_on_global_identity_C_eq_K() -> None:
    # Iter 219 territory: C == K globally. This matcher rejects (per-
    # group ic != oc fails).
    patterns = {"pair_analyses": [
        _pair([_group([3], [3]), _group([3], [3])]),
    ]}
    assert _matcher()(patterns, {}) is False


def test_returns_false_when_single_group_only() -> None:
    # A single group means |observed_input| == 1 AND |observed_output|
    # == 1 -- this matcher rejects on both anchor checks.
    patterns = {"pair_analyses": [_pair([_group([3], [0])])]}
    assert _matcher()(patterns, {}) is False


def test_returns_false_when_only_input_side_varies() -> None:
    # |observed_input| = {3, 5} > 1 but |observed_output| = {0} == 1
    # -- this is iter-222 territory, not this matcher's.
    patterns = {"pair_analyses": [
        _pair([_group([3], [0]), _group([5], [0])]),
    ]}
    assert _matcher()(patterns, {}) is False


def test_returns_false_when_only_output_side_varies() -> None:
    # |observed_input| = {3} == 1 but |observed_output| = {0, 7} > 1
    # -- this is iter-221 territory, not this matcher's. (Also fails
    # function-shape: C=3 -> both 0 and 7.)
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
    # Universal-over-groups: a single identity group (ic == oc) violates
    # per-group ic != oc on that group.
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
    # iter 13's no-blob-identity territory; disjoint by design.
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
    # (same posture as iter 14 / 18 / 200-223).
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
    # sentinel 13 and the < 0 / > 9 cases are rejected.
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
        {"pair_analyses": [_pair([_group([3], [0]), _group([3], [7])])]}, {}
    )
    assert out_true is True, f"expected literal True, got {out_true!r}"
    assert out_false is False, f"expected literal False, got {out_false!r}"


def test_ignores_dimensional_fields() -> None:
    analysis = _pair([_group([3], [0]), _group([5], [7])],
                     input_height=7, input_width=9,
                     output_height=2, output_width=3, size_match=False)
    patterns = {"pair_analyses": [analysis]}
    assert _matcher()(patterns, {}) is True


def test_ignores_palette_fields() -> None:
    analysis = _pair([_group([3], [0]), _group([5], [7])],
                     input_palette=[9, 9, 9],
                     output_palette=[1, 1, 1])
    patterns = {"pair_analyses": [analysis]}
    assert _matcher()(patterns, {}) is True


# --------------------------------------------------------------------------
# Orthogonality / refinement / mutual-exclusion matrix against existing
# axes.
# --------------------------------------------------------------------------

def test_strict_refinement_of_iter_223_unanchored() -> None:
    # KEY iter-223 strict-refinement witness: this matcher fires =>
    # iter 223 fires. The converse fails on the non-function-shape
    # sub-cell of iter 223 (companion candidate (xv) territory).
    iter223 = CONDITION_REGISTRY["singleton_recolor_nonidentity_unanchored"]

    # This matcher fires => iter 223 fires.
    p1 = {"pair_analyses": [_pair([_group([3], [0]), _group([5], [7])])]}
    assert _matcher()(p1, {}) is True and iter223(p1, {}) is True

    # Iter 223 fires (non-function-shape sub-cell); this matcher rejects.
    p2 = {"pair_analyses": [
        _pair([_group([3], [0]), _group([3], [7]), _group([5], [7])]),
    ]}
    assert iter223(p2, {}) is True and _matcher()(p2, {}) is False


def test_strict_refinement_of_iter_8_consistent_color_mapping() -> None:
    # KEY iter-8 strict-refinement witness: this matcher fires =>
    # iter 8 fires (function-shape is a precondition). The converse
    # fails when iter 8 fires outside iter 223's territory (e.g.,
    # iter 220 / 221 / 222 anchored cells; or non-singleton-row cells).
    iter8 = CONDITION_REGISTRY["consistent_color_mapping"]

    # This matcher fires => iter 8 fires.
    p1 = {"pair_analyses": [_pair([_group([3], [0]), _group([5], [7])])]}
    assert _matcher()(p1, {}) is True and iter8(p1, {}) is True

    # Iter 8 fires on iter-220 territory; this matcher rejects
    # (cross-group identity on both sides violates the (F, F) gate).
    p2 = {"pair_analyses": [_pair([_group([3], [0]), _group([3], [0])])]}
    assert iter8(p2, {}) is True and _matcher()(p2, {}) is False


def test_strict_refinement_of_iter_218_nonidentity_per_group() -> None:
    iter218 = CONDITION_REGISTRY["singleton_recolor_nonidentity_per_group"]

    # This matcher fires => iter 218 fires.
    p1 = {"pair_analyses": [_pair([_group([3], [0]), _group([5], [7])])]}
    assert _matcher()(p1, {}) is True and iter218(p1, {}) is True

    # Iter 218 fires (iter 220 cell), this matcher rejects.
    p2 = {"pair_analyses": [_pair([_group([3], [0]), _group([3], [0])])]}
    assert iter218(p2, {}) is True and _matcher()(p2, {}) is False


def test_strict_mutual_exclusion_with_iter_220_both_anchored() -> None:
    iter220 = CONDITION_REGISTRY["singleton_recolor_nonidentity"]

    # This matcher fires; iter 220 rejects.
    p1 = {"pair_analyses": [_pair([_group([3], [0]), _group([5], [7])])]}
    assert _matcher()(p1, {}) is True and iter220(p1, {}) is False

    # Iter 220 fires; this matcher rejects.
    p2 = {"pair_analyses": [_pair([_group([3], [0]), _group([3], [0])])]}
    assert iter220(p2, {}) is True and _matcher()(p2, {}) is False


def test_strict_mutual_exclusion_with_iter_221_input_anchored() -> None:
    iter221 = CONDITION_REGISTRY["singleton_recolor_nonidentity_input_anchored"]

    # This matcher fires; iter 221 rejects.
    p1 = {"pair_analyses": [_pair([_group([3], [0]), _group([5], [7])])]}
    assert _matcher()(p1, {}) is True and iter221(p1, {}) is False

    # Iter 221 fires; this matcher rejects.
    p2 = {"pair_analyses": [_pair([_group([3], [0]), _group([3], [7])])]}
    assert iter221(p2, {}) is True and _matcher()(p2, {}) is False


def test_strict_mutual_exclusion_with_iter_222_output_anchored() -> None:
    iter222 = CONDITION_REGISTRY["singleton_recolor_nonidentity_output_anchored"]

    # This matcher fires; iter 222 rejects.
    p1 = {"pair_analyses": [_pair([_group([3], [0]), _group([5], [7])])]}
    assert _matcher()(p1, {}) is True and iter222(p1, {}) is False

    # Iter 222 fires; this matcher rejects.
    p2 = {"pair_analyses": [_pair([_group([3], [0]), _group([7], [0])])]}
    assert iter222(p2, {}) is True and _matcher()(p2, {}) is False


def test_strict_mutual_exclusion_with_iter_219_identity() -> None:
    iter219 = CONDITION_REGISTRY["singleton_recolor_identity"]

    # This matcher fires; iter 219 rejects.
    p1 = {"pair_analyses": [_pair([_group([3], [0]), _group([5], [7])])]}
    assert _matcher()(p1, {}) is True and iter219(p1, {}) is False

    # Iter 219 fires; this matcher rejects.
    p2 = {"pair_analyses": [_pair([_group([3], [3]), _group([3], [3])])]}
    assert iter219(p2, {}) is True and _matcher()(p2, {}) is False


def test_strict_mutual_exclusion_with_iter_217_identity_per_group() -> None:
    iter217 = CONDITION_REGISTRY["singleton_recolor_identity_per_group"]

    # This matcher fires; iter 217 rejects.
    p1 = {"pair_analyses": [_pair([_group([3], [0]), _group([5], [7])])]}
    assert _matcher()(p1, {}) is True and iter217(p1, {}) is False

    # Iter 217 fires; this matcher rejects.
    p2 = {"pair_analyses": [_pair([_group([3], [3]), _group([5], [5])])]}
    assert iter217(p2, {}) is True and _matcher()(p2, {}) is False


def test_strict_mutual_exclusion_with_iter_216_both_anchored() -> None:
    iter216 = CONDITION_REGISTRY["singleton_recolor"]

    # This matcher fires; iter 216 rejects.
    p1 = {"pair_analyses": [_pair([_group([3], [0]), _group([5], [7])])]}
    assert _matcher()(p1, {}) is True and iter216(p1, {}) is False

    # Iter 216 fires (C == K globally is allowed by iter 216); this
    # matcher rejects.
    p2 = {"pair_analyses": [_pair([_group([3], [3]), _group([3], [3])])]}
    assert iter216(p2, {}) is True and _matcher()(p2, {}) is False


def test_strict_refinement_of_iter_215_singleton_recolor_per_group() -> None:
    iter215 = CONDITION_REGISTRY["singleton_recolor_per_group"]

    # This matcher fires => iter 215 fires.
    p1 = {"pair_analyses": [_pair([_group([3], [0]), _group([5], [7])])]}
    assert _matcher()(p1, {}) is True and iter215(p1, {}) is True

    # Iter 215 fires (per-group |ic| == |oc| == 1), this matcher
    # rejects (per-group ic == oc on some group).
    p2 = {"pair_analyses": [_pair([_group([3], [0]), _group([3], [3])])]}
    assert iter215(p2, {}) is True and _matcher()(p2, {}) is False


def test_strict_mutual_exclusion_with_iter_14_input_color_uniform() -> None:
    iter14 = CONDITION_REGISTRY["input_color_uniform"]

    # This matcher fires; iter 14 rejects.
    p1 = {"pair_analyses": [_pair([_group([3], [0]), _group([5], [7])])]}
    assert _matcher()(p1, {}) is True and iter14(p1, {}) is False

    # Iter 14 fires (input globally uniform C); this matcher rejects.
    p2 = {"pair_analyses": [_pair([_group([3], [0]), _group([3], [7])])]}
    assert iter14(p2, {}) is True and _matcher()(p2, {}) is False


def test_strict_mutual_exclusion_with_iter_18_output_color_uniform() -> None:
    iter18 = CONDITION_REGISTRY["output_color_uniform"]

    # This matcher fires; iter 18 rejects.
    p1 = {"pair_analyses": [_pair([_group([3], [0]), _group([5], [7])])]}
    assert _matcher()(p1, {}) is True and iter18(p1, {}) is False

    # Iter 18 fires (output globally uniform K); this matcher rejects.
    p2 = {"pair_analyses": [_pair([_group([3], [0]), _group([5], [0])])]}
    assert iter18(p2, {}) is True and _matcher()(p2, {}) is False


def test_mutual_exclusion_with_identity_transformation() -> None:
    ident = CONDITION_REGISTRY["identity_transformation"]
    p = {"pair_analyses": [_pair([], num_groups=0, total_changes=0)]}
    assert ident(p, {}) is True and _matcher()(p, {}) is False


def test_strict_implication_of_iter_203_disjoint_per_group() -> None:
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
    iter213 = CONDITION_REGISTRY["consistent_color_mapping_per_group"]

    # This matcher fires => iter 213 fires.
    p1 = {"pair_analyses": [_pair([_group([3], [0]), _group([5], [7])])]}
    assert _matcher()(p1, {}) is True and iter213(p1, {}) is True

    # Iter 213 fires with per-group |ic| > 1; this matcher rejects.
    p2 = {"pair_analyses": [_pair([_group([3, 4], [0]), _group([3, 4], [7])])]}
    assert iter213(p2, {}) is True and _matcher()(p2, {}) is False


def test_strict_refinement_of_iter_214_input_color_uniform_per_group() -> None:
    iter214 = CONDITION_REGISTRY["input_color_uniform_per_group"]

    # This matcher fires => iter 214 fires.
    p1 = {"pair_analyses": [_pair([_group([3], [0]), _group([5], [7])])]}
    assert _matcher()(p1, {}) is True and iter214(p1, {}) is True

    # Iter 214 fires with per-group |oc| > 1; this matcher rejects.
    p2 = {"pair_analyses": [_pair([_group([3], [0, 4]), _group([3], [7, 1])])]}
    assert iter214(p2, {}) is True and _matcher()(p2, {}) is False


def test_strict_refinement_of_iter_197_at_K_prod_eq_1() -> None:
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

    # Iter 197 fires at K_prod == 1 with iter-220 territory; this
    # matcher rejects.
    p2 = {
        "pair_analyses": [
            _pair([_group([3], [0])]),
            _pair([_group([3], [0])]),
        ],
    }
    assert iter197(p2, {}) is True and _matcher()(p2, {}) is False


def test_recognized_conditions_includes_matcher_on_iter_10_fixture() -> None:
    # The iter-10 canonical fixture (ic=[0]/oc=[3], ic=[1]/oc=[4],
    # ic=[2]/oc=[5]) is function-shaped (0 -> 3, 1 -> 4, 2 -> 5) AND
    # in iter 223's (F, F) territory. This matcher FIRES.
    from agent.conditions import recognized_conditions
    patterns = {"pair_analyses": [
        _pair([_group([0], [3]), _group([1], [4]), _group([2], [5])]),
    ]}
    fired = recognized_conditions(patterns)
    assert MATCHER_NAME in fired, (
        f"{MATCHER_NAME!r} did not fire on the iter-10 canonical "
        f"fixture (function-shaped (F, F)); got {fired!r}"
    )
    # Iter 223 must still co-fire (this matcher is a strict refinement).
    assert "singleton_recolor_nonidentity_unanchored" in fired, (
        "iter 223 regression: must still co-fire on this matcher's "
        f"territory; got {fired!r}"
    )
    # Iter 8 must co-fire (function-shape on iter-10 fixture).
    assert "consistent_color_mapping" in fired, (
        "iter 8 regression: must co-fire on the function-shaped sub-"
        f"cell; got {fired!r}"
    )


def test_recognized_conditions_excludes_on_non_function_shape() -> None:
    # On the non-function-shape sub-cell of iter 223 (C=3 -> both 0
    # and 7), iter 223 still fires but this matcher rejects.
    from agent.conditions import recognized_conditions
    patterns = {"pair_analyses": [
        _pair([_group([3], [0]), _group([3], [7]), _group([5], [7])]),
    ]}
    fired = recognized_conditions(patterns)
    assert MATCHER_NAME not in fired, (
        f"{MATCHER_NAME!r} should NOT fire on the non-function-shape "
        f"sub-cell of iter 223; got {fired!r}"
    )
    # No regression on iter 223.
    assert "singleton_recolor_nonidentity_unanchored" in fired, (
        "iter 223 regression: singleton_recolor_nonidentity_unanchored "
        f"should still fire on the non-function-shape sub-cell; got "
        f"{fired!r}"
    )
    # Iter 8 rejects (function-shape fails globally).
    assert "consistent_color_mapping" not in fired, (
        "iter 8 expectation: consistent_color_mapping must reject the "
        f"non-function-shape fixture; got {fired!r}"
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
