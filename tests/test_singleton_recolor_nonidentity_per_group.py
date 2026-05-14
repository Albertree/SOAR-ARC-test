"""
tests/test_singleton_recolor_nonidentity_per_group.py -- exercise the
iter-218 matcher ``agent.conditions.singleton_recolor_nonidentity_per_
group``.

Pins the matcher's contract per the docstring of
``agent/conditions/singleton_recolor_nonidentity_per_group.py``: every
group of every example pair has BOTH ``len(set(input_colors)) == 1``
AND ``len(set(output_colors)) == 1`` AND ``set(input_colors) !=
set(output_colors)`` -- the per-group non-identity-on-singleton cell,
the STRICT COMPLEMENT of iter 217 (``singleton_recolor_identity_per_
group``) within iter 215's (``singleton_recolor_per_group``)
territory. Universal over groups AND pairs; fail-closed on empty /
no-group / malformed input.

Runs without pytest:

    python tests/test_singleton_recolor_nonidentity_per_group.py

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


MATCHER_NAME = "singleton_recolor_nonidentity_per_group"


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

def test_returns_true_on_per_group_singleton_true_recolour() -> None:
    # Trivial cell: every group has ic != oc as singletons.
    patterns = {"pair_analyses": [
        _pair([_group([3], [0]), _group([5], [7])]),
    ]}
    assert _matcher()(patterns, {}) is True


def test_returns_true_when_recolours_differ_across_groups() -> None:
    # Per-group (C_g, K_g) pairs may vary across groups (drops cross-
    # group identity that iter 14 ∧ iter 18 would demand).
    patterns = {"pair_analyses": [
        _pair([_group([3], [0]), _group([5], [7]), _group([1], [2])]),
    ]}
    assert _matcher()(patterns, {}) is True


def test_returns_true_when_recolours_differ_across_pairs() -> None:
    # Per-group (C_g, K_g) pairs may vary across pairs too.
    patterns = {
        "pair_analyses": [
            _pair([_group([3], [0])]),
            _pair([_group([7], [9])]),
        ],
    }
    assert _matcher()(patterns, {}) is True


def test_returns_true_with_multipair_recolour_groups() -> None:
    patterns = {
        "pair_analyses": [
            _pair([_group([3], [0]), _group([7], [2])]),
            _pair([_group([3], [0]), _group([7], [2])]),
        ],
    }
    assert _matcher()(patterns, {}) is True


def test_returns_true_with_duplicate_entries_in_color_lists() -> None:
    # Color lists are de-duplicated set-wise by the matcher; duplicates
    # in the list must not change the verdict.
    patterns = {"pair_analyses": [
        _pair([_group([3, 3], [4, 4])]),
    ]}
    assert _matcher()(patterns, {}) is True


def test_returns_true_on_colour_zero_to_nine() -> None:
    # Edge: source 0, target 9 (lowest -> highest valid colour).
    patterns = {"pair_analyses": [
        _pair([_group([0], [9])]),
    ]}
    assert _matcher()(patterns, {}) is True


def test_returns_true_on_colour_nine_to_zero() -> None:
    # Edge: source 9, target 0 (highest -> lowest valid colour).
    patterns = {"pair_analyses": [
        _pair([_group([9], [0])]),
    ]}
    assert _matcher()(patterns, {}) is True


def test_returns_true_with_single_group_single_pair() -> None:
    patterns = {"pair_analyses": [
        _pair([_group([4], [5])]),
    ]}
    assert _matcher()(patterns, {}) is True


# --------------------------------------------------------------------------
# Negative cases.
# --------------------------------------------------------------------------

def test_returns_false_when_any_group_singleton_is_fixed_point() -> None:
    # KEY strict-mutual-exclusion witness vs iter 217: ic = [3], oc = [3].
    # Iter 217 fires (both sides equal singletons); this matcher rejects
    # (the singletons are equal -- not a true recolour).
    patterns = {"pair_analyses": [
        _pair([_group([3], [3])]),
    ]}
    assert _matcher()(patterns, {}) is False


def test_returns_false_when_any_group_has_multi_input() -> None:
    # |ic| > 1 fails regardless of |oc|.
    patterns = {"pair_analyses": [
        _pair([_group([0, 1], [3])]),
    ]}
    assert _matcher()(patterns, {}) is False


def test_returns_false_when_any_group_has_multi_output() -> None:
    # |oc| > 1 fails regardless of |ic|.
    patterns = {"pair_analyses": [
        _pair([_group([0], [3, 4])]),
    ]}
    assert _matcher()(patterns, {}) is False


def test_returns_false_when_any_group_has_both_multi_unequal() -> None:
    # |ic| > 1 AND |oc| > 1 with ic != oc: fails on cardinality alone.
    patterns = {"pair_analyses": [
        _pair([_group([0, 1], [3, 4])]),
    ]}
    assert _matcher()(patterns, {}) is False


def test_returns_false_when_any_group_has_both_multi_equal() -> None:
    # Multi-element ic == oc: iter 201 fires (set-equality on multi
    # cardinality); this matcher rejects (cardinality > 1).
    patterns = {"pair_analyses": [
        _pair([_group([3, 4], [3, 4])]),
    ]}
    assert _matcher()(patterns, {}) is False


def test_returns_false_when_one_of_many_groups_is_fixed_point() -> None:
    # Universal-over-groups semantic: a single fixed-point group
    # fails the whole task even if other groups are true recolours.
    patterns = {"pair_analyses": [
        _pair([
            _group([0], [1]),       # true recolour -- ok
            _group([3], [3]),       # fixed point -- offending
            _group([5], [6]),       # true recolour -- ok
        ]),
    ]}
    assert _matcher()(patterns, {}) is False


def test_returns_false_when_one_of_many_groups_violates_cardinality() -> None:
    patterns = {"pair_analyses": [
        _pair([
            _group([0], [1]),       # true recolour -- ok
            _group([3, 4], [5, 6]), # multi-unequal -- offending
            _group([7], [8]),       # true recolour -- ok
        ]),
    ]}
    assert _matcher()(patterns, {}) is False


def test_returns_false_when_any_pair_has_offending_group() -> None:
    # Universal-over-pairs: a single failing pair fails the whole
    # task.
    patterns = {
        "pair_analyses": [
            _pair([_group([3], [0])]),
            _pair([_group([3], [3])]),  # offending fixed-point
            _pair([_group([3], [0])]),
        ],
    }
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
    # Identity-territory rejection (mirroring iter 13 / 215 / 217
    # rejection -- this matcher is the per-group complement of iter
    # 13's no-blob identity, designed disjoint on the #groups axis).
    patterns = {
        "pair_analyses": [
            _pair([_group([0], [1])]),
            _pair([], num_groups=0, total_changes=0),
        ],
    }
    assert _matcher()(patterns, {}) is False


def test_returns_false_on_missing_groups_key() -> None:
    analysis = _pair([_group([0], [1])])
    del analysis["groups"]
    patterns = {"pair_analyses": [analysis]}
    assert _matcher()(patterns, {}) is False


def test_returns_false_on_non_list_groups() -> None:
    for bad in (None, 42, "oops", {"a": 1}, (), True):
        analysis = _pair([_group([0], [1])])
        analysis["groups"] = bad
        patterns = {"pair_analyses": [analysis]}
        assert _matcher()(patterns, {}) is False, (
            f"groups={bad!r} should not fire"
        )


def test_returns_false_when_any_analysis_is_not_dict() -> None:
    patterns = {
        "pair_analyses": [
            _pair([_group([0], [1])]),
            "not-a-dict",
            _pair([_group([1], [2])]),
        ],
    }
    assert _matcher()(patterns, {}) is False


def test_returns_false_when_any_group_is_not_dict() -> None:
    analysis = _pair([_group([0], [1])])
    analysis["groups"] = [_group([0], [1]), "not-a-dict"]
    patterns = {"pair_analyses": [analysis]}
    assert _matcher()(patterns, {}) is False


# --------------------------------------------------------------------------
# Strict-type-gate cases.
# --------------------------------------------------------------------------

def test_returns_false_when_input_colors_missing() -> None:
    analysis = _pair([_group([0], [1])])
    del analysis["groups"][0]["input_colors"]
    patterns = {"pair_analyses": [analysis]}
    assert _matcher()(patterns, {}) is False


def test_returns_false_when_output_colors_missing() -> None:
    analysis = _pair([_group([0], [1])])
    del analysis["groups"][0]["output_colors"]
    patterns = {"pair_analyses": [analysis]}
    assert _matcher()(patterns, {}) is False


def test_returns_false_when_input_colors_empty() -> None:
    analysis = _pair([_group([0], [1])])
    analysis["groups"][0]["input_colors"] = []
    patterns = {"pair_analyses": [analysis]}
    assert _matcher()(patterns, {}) is False


def test_returns_false_when_output_colors_empty() -> None:
    analysis = _pair([_group([0], [1])])
    analysis["groups"][0]["output_colors"] = []
    patterns = {"pair_analyses": [analysis]}
    assert _matcher()(patterns, {}) is False


def test_returns_false_when_input_colors_not_list() -> None:
    for bad in (None, 42, "oops", {"a": 1}, (0,), True, {0}):
        analysis = _pair([_group([0], [1])])
        analysis["groups"][0]["input_colors"] = bad
        patterns = {"pair_analyses": [analysis]}
        assert _matcher()(patterns, {}) is False, (
            f"input_colors={bad!r} should not fire"
        )


def test_returns_false_when_output_colors_not_list() -> None:
    for bad in (None, 42, "oops", {"a": 1}, (3,), True, {3}):
        analysis = _pair([_group([0], [1])])
        analysis["groups"][0]["output_colors"] = bad
        patterns = {"pair_analyses": [analysis]}
        assert _matcher()(patterns, {}) is False, (
            f"output_colors={bad!r} should not fire"
        )


def test_returns_false_when_color_list_contains_bool() -> None:
    # bools are an int subclass; the strict-type gate rejects them
    # (same posture as iter 14 / 18 / 200-206 / 213 / 214 / 215 / 217).
    analysis = _pair([_group([True], [3])])
    patterns = {"pair_analyses": [analysis]}
    assert _matcher()(patterns, {}) is False

    analysis2 = _pair([_group([3], [False])])
    patterns2 = {"pair_analyses": [analysis2]}
    assert _matcher()(patterns2, {}) is False


def test_returns_false_when_color_list_contains_non_int() -> None:
    analysis = _pair([_group(["3"], [4])])
    patterns = {"pair_analyses": [analysis]}
    assert _matcher()(patterns, {}) is False

    analysis2 = _pair([_group([3], [4.0])])
    patterns2 = {"pair_analyses": [analysis2]}
    assert _matcher()(patterns2, {}) is False


def test_returns_false_when_color_out_of_range() -> None:
    # Per-group color values must be in [0, 9]; iter-180 erase
    # sentinel 13 is rejected on the per-group projection (same as
    # iter 215 / 217's strict-range gate).
    analysis = _pair([_group([13], [4])])
    patterns = {"pair_analyses": [analysis]}
    assert _matcher()(patterns, {}) is False

    analysis2 = _pair([_group([-1], [4])])
    patterns2 = {"pair_analyses": [analysis2]}
    assert _matcher()(patterns2, {}) is False


# --------------------------------------------------------------------------
# Behavioural-contract cases.
# --------------------------------------------------------------------------

def test_is_side_effect_free_on_inputs() -> None:
    patterns = {"pair_analyses": [
        _pair([_group([0], [1]), _group([5], [6])]),
    ]}
    params = {"unused": 1}
    before_p = copy.deepcopy(patterns)
    before_q = copy.deepcopy(params)
    _matcher()(patterns, params)
    assert patterns == before_p, "matcher mutated patterns"
    assert params == before_q, "matcher mutated params"


def test_is_deterministic_across_repeats() -> None:
    patterns = {"pair_analyses": [_pair([_group([3], [0])])]}
    results = [_matcher()(patterns, {}) for _ in range(5)]
    assert len(set(results)) == 1, f"non-deterministic outputs: {results}"


def test_returned_value_is_boolean_not_truthy() -> None:
    # recognized_conditions filters on ``match(...) is True`` exactly,
    # so the matcher must return literal Booleans.
    out_true = _matcher()({"pair_analyses": [_pair([_group([0], [1])])]}, {})
    out_false = _matcher()({"pair_analyses": [_pair([_group([0], [0])])]}, {})
    assert out_true is True, f"expected literal True, got {out_true!r}"
    assert out_false is False, f"expected literal False, got {out_false!r}"


def test_ignores_dimensional_fields() -> None:
    # Dimensional fields are orthogonal -- arbitrary dim combinations
    # must not affect the matcher's verdict.
    analysis = _pair([_group([0], [1])], input_height=7, input_width=9,
                     output_height=2, output_width=3, size_match=False)
    patterns = {"pair_analyses": [analysis]}
    assert _matcher()(patterns, {}) is True


def test_ignores_palette_fields() -> None:
    # Whole-grid palette fields are orthogonal -- this matcher only
    # inspects per-group color lists.
    analysis = _pair([_group([0], [1])],
                     input_palette=[9, 9, 9],
                     output_palette=[1, 1, 1])
    patterns = {"pair_analyses": [analysis]}
    assert _matcher()(patterns, {}) is True


# --------------------------------------------------------------------------
# Orthogonality / refinement / mutual-exclusion matrix against existing
# axes.
# --------------------------------------------------------------------------

def test_strict_refinement_of_iter_215_singleton_recolor_per_group() -> None:
    # Strict refinement: this matcher fires => iter 215 fires (per-
    # group |ic| == |oc| == 1 is a precondition). Converse fails when
    # the per-group singletons are equal (iter 215 still fires; this
    # matcher rejects).
    iter215 = CONDITION_REGISTRY["singleton_recolor_per_group"]

    # This matcher fires => iter 215 fires.
    p1 = {"pair_analyses": [_pair([_group([3], [0])])]}
    assert _matcher()(p1, {}) is True and iter215(p1, {}) is True

    # Iter 215 fires, this matcher rejects: ic == oc as singletons.
    p2 = {"pair_analyses": [_pair([_group([3], [3])])]}
    assert iter215(p2, {}) is True and _matcher()(p2, {}) is False


def test_strict_mutual_exclusion_with_iter_217_identity_per_group() -> None:
    # KEY witness: this matcher and iter 217 are pairwise disjoint
    # named cells of the iter-215 bijective-singleton-recolour axis.
    # Iter 217 demands per-group ic == oc; this matcher demands
    # per-group ic != oc.
    iter217 = CONDITION_REGISTRY["singleton_recolor_identity_per_group"]

    # This matcher fires; iter 217 rejects (per-group ic != oc).
    p1 = {"pair_analyses": [_pair([_group([3], [0])])]}
    assert _matcher()(p1, {}) is True and iter217(p1, {}) is False

    # Iter 217 fires; this matcher rejects (per-group ic == oc).
    p2 = {"pair_analyses": [_pair([_group([3], [3])])]}
    assert iter217(p2, {}) is True and _matcher()(p2, {}) is False

    # Mixed-cell task: neither named cell fires (iter 215 still does).
    # One group is a fixed point, another is a true recolour.
    iter215 = CONDITION_REGISTRY["singleton_recolor_per_group"]
    p3 = {"pair_analyses": [
        _pair([_group([3], [3]), _group([5], [6])]),
    ]}
    assert iter215(p3, {}) is True
    assert iter217(p3, {}) is False
    assert _matcher()(p3, {}) is False


def test_strict_refinement_of_iter_213_consistent_color_mapping_per_group() -> None:
    # Iter 213 (``consistent_color_mapping_per_group``) demands per-
    # group |oc| == 1 only; this matcher additionally demands per-
    # group |ic| == 1 AND ic != oc. Strict refinement.
    iter213 = CONDITION_REGISTRY["consistent_color_mapping_per_group"]

    # This matcher fires => iter 213 fires.
    p1 = {"pair_analyses": [_pair([_group([3], [0])])]}
    assert _matcher()(p1, {}) is True and iter213(p1, {}) is True

    # Iter 213 fires, this matcher rejects: per-group |ic| > 1.
    p2 = {"pair_analyses": [_pair([_group([0, 1], [3])])]}
    assert iter213(p2, {}) is True and _matcher()(p2, {}) is False


def test_strict_refinement_of_iter_214_input_color_uniform_per_group() -> None:
    # Iter 214 (``input_color_uniform_per_group``) demands per-group
    # |ic| == 1 only; this matcher additionally demands per-group
    # |oc| == 1 AND ic != oc. Strict refinement.
    iter214 = CONDITION_REGISTRY["input_color_uniform_per_group"]

    # This matcher fires => iter 214 fires.
    p1 = {"pair_analyses": [_pair([_group([3], [0])])]}
    assert _matcher()(p1, {}) is True and iter214(p1, {}) is True

    # Iter 214 fires, this matcher rejects: per-group |oc| > 1.
    p2 = {"pair_analyses": [_pair([_group([3], [0, 1])])]}
    assert iter214(p2, {}) is True and _matcher()(p2, {}) is False


def test_mutual_exclusion_with_identity_transformation() -> None:
    # Iter 13 fires iff every pair has zero change groups. This
    # matcher rejects the no-group case (universal-over-groups
    # requires >= 1 group). Together with iter 13 + iter 217 they
    # form THREE disjoint cells on the (#groups, ic-vs-oc) lattice
    # for the singleton rows.
    ident = CONDITION_REGISTRY["identity_transformation"]
    p = {"pair_analyses": [_pair([], num_groups=0, total_changes=0)]}
    # Identity fires; this matcher rejects (no groups).
    assert ident(p, {}) is True and _matcher()(p, {}) is False


def test_independent_of_iter_216_singleton_recolor() -> None:
    # Iter 216 (``singleton_recolor``) pins WHOLE-TASK |ic| == |oc|
    # == 1 with cross-group identity (single global C, K, possibly
    # == or != to each other). This matcher pins PER-GROUP |ic| ==
    # |oc| == 1 AND per-group C_g != K_g (no cross-group identity
    # required). Decoupling in both directions:
    iter216 = CONDITION_REGISTRY["singleton_recolor"]

    # Iter 216 fires, this matcher rejects: cross-group identity
    # with C == K (every group is fixed point at colour 3).
    p1 = {"pair_analyses": [
        _pair([_group([3], [3]), _group([3], [3])]),
    ]}
    assert iter216(p1, {}) is True and _matcher()(p1, {}) is False

    # This matcher fires, iter 216 rejects: per-group (C_g, K_g)
    # vary across groups.
    p2 = {"pair_analyses": [
        _pair([_group([3], [0]), _group([5], [7])]),
    ]}
    assert iter216(p2, {}) is False and _matcher()(p2, {}) is True

    # Co-fire cell: cross-group identity AND C != K globally
    # (every group is recoloured 3 -> 0).
    p3 = {"pair_analyses": [
        _pair([_group([3], [0]), _group([3], [0])]),
    ]}
    assert iter216(p3, {}) is True and _matcher()(p3, {}) is True


def test_strict_implication_of_iter_14_and_iter_18_with_C_neq_K_globally() -> None:
    # Iter 14 (whole-task |ic| == 1 + cross-group identity) AND
    # iter 18 (whole-task |oc| == 1 + cross-group identity) JOINTLY
    # fire with C != K globally => this matcher fires. Converse
    # fails when per-group (C_g, K_g) varies across groups (this
    # matcher fires, iter 14 / 18 reject).
    iter14 = CONDITION_REGISTRY["input_color_uniform"]
    iter18 = CONDITION_REGISTRY["output_color_uniform"]

    # Iter 14 AND iter 18 fire with C == 3, K == 0: this matcher fires.
    p1 = {"pair_analyses": [
        _pair([_group([3], [0]), _group([3], [0])]),
    ]}
    assert (
        iter14(p1, {}) is True
        and iter18(p1, {}) is True
        and _matcher()(p1, {}) is True
    )

    # This matcher fires (per-group recolours), iter 14 rejects
    # (input singletons differ across groups).
    p2 = {"pair_analyses": [
        _pair([_group([3], [0]), _group([5], [7])]),
    ]}
    assert iter14(p2, {}) is False and _matcher()(p2, {}) is True


def test_strict_implication_of_iter_203_disjoint_per_group() -> None:
    # Iter 203 (``output_colors_disjoint_from_input_colors_per_
    # group``) demands per-group set(ic) ∩ set(oc) == ∅. On the
    # singleton row, ic != oc with |ic| == |oc| == 1 forces ic ∩ oc
    # == ∅. Strict implication: this matcher fires => iter 203
    # fires. Converse fails on iter-203 territory with |ic| > 1.
    iter203 = CONDITION_REGISTRY[
        "output_colors_disjoint_from_input_colors_per_group"
    ]

    # This matcher fires => iter 203 fires.
    p1 = {"pair_analyses": [_pair([_group([3], [0])])]}
    assert _matcher()(p1, {}) is True and iter203(p1, {}) is True

    # Iter 203 fires (multi-element disjoint), this matcher rejects.
    p2 = {"pair_analyses": [_pair([_group([0, 1], [3, 4])])]}
    assert iter203(p2, {}) is True and _matcher()(p2, {}) is False


def test_strict_mutual_exclusion_with_iter_201_set_equality_per_group() -> None:
    # Iter 201 (``output_colors_equals_input_colors_per_group``)
    # demands per-group set(ic) == set(oc); this matcher demands
    # per-group set(ic) != set(oc). Strict mutual exclusion (on
    # well-formed singleton-shaped tasks neither admits the other's
    # cells -- iter 201's equality cell vs this matcher's strict-
    # inequality cell on the singleton row).
    iter201 = CONDITION_REGISTRY[
        "output_colors_equals_input_colors_per_group"
    ]

    # This matcher fires, iter 201 rejects (per-group ic != oc).
    p1 = {"pair_analyses": [_pair([_group([3], [0])])]}
    assert _matcher()(p1, {}) is True and iter201(p1, {}) is False

    # Iter 201 fires (multi-element equality), this matcher rejects
    # (per-group |ic| > 1).
    p2 = {"pair_analyses": [_pair([_group([3, 4], [3, 4])])]}
    assert iter201(p2, {}) is True and _matcher()(p2, {}) is False


def test_strict_refinement_of_iter_197_at_K_prod_eq_1() -> None:
    # Iter 197 says |ic|*|oc| per group is constant across pairs at
    # SOME K_prod. This matcher pins K_prod == 1 per group AND the
    # per-group strict ic != oc. Strict refinement of iter 197 at
    # the K_prod == 1 cell with the non-identity sub-cell.
    iter197 = CONDITION_REGISTRY[
        "change_color_mapping_count_per_group_constant_across_pairs"
    ]

    # This matcher fires => iter 197 fires at K_prod == 1.
    p1 = {"pair_analyses": [
        _pair([_group([3], [0])]),
        _pair([_group([5], [7])]),
    ]}
    assert _matcher()(p1, {}) is True and iter197(p1, {}) is True

    # Iter 197 fires at K_prod == 1 with C == K (iter 217's
    # territory); this matcher rejects.
    p2 = {"pair_analyses": [
        _pair([_group([3], [3])]),
        _pair([_group([5], [5])]),
    ]}
    assert iter197(p2, {}) is True and _matcher()(p2, {}) is False


def test_independent_of_iter_10_sequential_recoloring() -> None:
    # Iter 10 (per-group |oc| == 1 with singletons forming a
    # contiguous range) is INDEPENDENT of the per-group strict-
    # recolour claim. Co-fire / decouple witnesses:
    iter10 = CONDITION_REGISTRY["sequential_recoloring"]

    # Co-fire: the iter-10 canonical fixture (ic = [0]/[1]/[2],
    # oc = [3]/[4]/[5]) has per-group |ic| == |oc| == 1 with ic
    # != oc on every group, AND the oc singletons form a contiguous
    # range. Both fire.
    p1 = {
        "pair_analyses": [
            _pair([_group([0], [3]), _group([1], [4]), _group([2], [5])]),
            _pair([_group([0], [3]), _group([1], [4]), _group([2], [5])]),
        ],
    }
    assert iter10(p1, {}) is True and _matcher()(p1, {}) is True

    # This matcher fires, iter 10 rejects: per-group oc singletons
    # do not form a contiguous range (0, 7 -- not contiguous).
    p2 = {"pair_analyses": [
        _pair([_group([3], [0]), _group([5], [7])]),
    ]}
    assert iter10(p2, {}) is False and _matcher()(p2, {}) is True


def test_recognized_conditions_includes_singleton_recolor_nonidentity_per_group() -> None:
    from agent.conditions import recognized_conditions
    patterns = {"pair_analyses": [
        _pair([_group([3], [0]), _group([5], [7])]),
    ]}
    fired = recognized_conditions(patterns)
    assert MATCHER_NAME in fired, (
        f"{MATCHER_NAME!r} did not fire on a per-group non-identity-"
        f"singleton patterns dict; got {fired!r}"
    )


def test_recognized_conditions_excludes_on_fixed_point_singleton() -> None:
    # On a per-group fixed-point fixture (ic = oc per group), iter
    # 217 fires (per-group identity) but THIS matcher rejects (per-
    # group ic != oc required). Iter 217 must still be in the fired
    # list (no regression).
    from agent.conditions import recognized_conditions
    patterns = {
        "pair_analyses": [
            _pair([_group([3], [3]), _group([5], [5]), _group([7], [7])]),
        ],
    }
    fired = recognized_conditions(patterns)
    assert MATCHER_NAME not in fired, (
        f"{MATCHER_NAME!r} should NOT fire on fixed-point singletons; "
        f"got {fired!r}"
    )
    # No regression on iter 217.
    assert "singleton_recolor_identity_per_group" in fired, (
        "iter 217 regression: singleton_recolor_identity_per_group should "
        f"still fire on per-group fixed points; got {fired!r}"
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
