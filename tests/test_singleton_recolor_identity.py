"""
tests/test_singleton_recolor_identity.py -- exercise the iter-219
matcher ``agent.conditions.singleton_recolor_identity``.

Pins the matcher's contract per the docstring of
``agent/conditions/singleton_recolor_identity.py``: every group of
every example pair has BOTH ``len(set(input_colors)) == 1`` AND
``len(set(output_colors)) == 1`` AND the global C and K (cross-group
identity on both sides) are equal -- the whole-task identity-on-
singleton cell, the STRICT REFINEMENT of iter 216
(``singleton_recolor``) at the C == K sub-cell, the whole-task
projection of iter 217 (``singleton_recolor_identity_per_group``) at
the cross-group-identity cell. Universal over groups AND pairs;
fail-closed on empty / no-group / malformed input.

Runs without pytest:

    python tests/test_singleton_recolor_identity.py

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


MATCHER_NAME = "singleton_recolor_identity"


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

def test_returns_true_on_single_group_single_pair_fixed_point() -> None:
    # The trivial cell: one pair, one group, ic == oc == [C].
    patterns = {"pair_analyses": [
        _pair([_group([3], [3])]),
    ]}
    assert _matcher()(patterns, {}) is True


def test_returns_true_with_multiple_groups_same_global_fixed_point() -> None:
    # Every group has the SAME global singleton C on both sides.
    patterns = {"pair_analyses": [
        _pair([_group([3], [3]), _group([3], [3]), _group([3], [3])]),
    ]}
    assert _matcher()(patterns, {}) is True


def test_returns_true_with_multiple_pairs_same_global_fixed_point() -> None:
    patterns = {
        "pair_analyses": [
            _pair([_group([3], [3])]),
            _pair([_group([3], [3]), _group([3], [3])]),
        ],
    }
    assert _matcher()(patterns, {}) is True


def test_returns_true_with_duplicate_entries_in_color_lists() -> None:
    # Colour lists are de-duplicated set-wise by the matcher; duplicates
    # in the list must not change the verdict.
    patterns = {"pair_analyses": [
        _pair([_group([4, 4], [4, 4])]),
    ]}
    assert _matcher()(patterns, {}) is True


def test_returns_true_on_colour_zero_globally() -> None:
    # Edge: global fixed point C == 0.
    patterns = {"pair_analyses": [
        _pair([_group([0], [0]), _group([0], [0])]),
    ]}
    assert _matcher()(patterns, {}) is True


def test_returns_true_on_colour_nine_globally() -> None:
    # Edge: global fixed point C == 9 (highest valid colour).
    patterns = {"pair_analyses": [
        _pair([_group([9], [9])]),
    ]}
    assert _matcher()(patterns, {}) is True


# --------------------------------------------------------------------------
# Negative cases.
# --------------------------------------------------------------------------

def test_returns_false_on_global_non_identity_recolour() -> None:
    # KEY iter-216 mutual-exclusion witness: iter 216 (whole-task
    # singleton_recolor) fires when there is a single global C and a
    # single global K. This matcher rejects when C != K.
    patterns = {"pair_analyses": [
        _pair([_group([3], [0]), _group([3], [0])]),
    ]}
    assert _matcher()(patterns, {}) is False


def test_returns_false_when_input_singletons_differ_across_groups() -> None:
    # Per-group fixed points (ic == oc) but with C_g varying across
    # groups: iter 217 fires, this matcher rejects (cross-group identity
    # fails on the input side).
    patterns = {"pair_analyses": [
        _pair([_group([3], [3]), _group([5], [5])]),
    ]}
    assert _matcher()(patterns, {}) is False


def test_returns_false_when_input_singletons_differ_across_pairs() -> None:
    # Per-pair fixed points with different C across pairs: iter 217
    # fires, this matcher rejects on cross-pair input non-identity.
    patterns = {
        "pair_analyses": [
            _pair([_group([3], [3])]),
            _pair([_group([5], [5])]),
        ],
    }
    assert _matcher()(patterns, {}) is False


def test_returns_false_when_any_group_has_multi_input() -> None:
    patterns = {"pair_analyses": [
        _pair([_group([3, 4], [3])]),
    ]}
    assert _matcher()(patterns, {}) is False


def test_returns_false_when_any_group_has_multi_output() -> None:
    patterns = {"pair_analyses": [
        _pair([_group([3], [3, 4])]),
    ]}
    assert _matcher()(patterns, {}) is False


def test_returns_false_when_one_of_many_groups_is_recolour() -> None:
    # Universal-over-groups semantic: a single recolour group disturbs
    # cross-group identity and fails the whole task even when other
    # groups are global fixed points.
    patterns = {"pair_analyses": [
        _pair([
            _group([3], [3]),
            _group([3], [0]),   # offending recolour
            _group([3], [3]),
        ]),
    ]}
    assert _matcher()(patterns, {}) is False


def test_returns_false_when_any_pair_breaks_cross_group_identity() -> None:
    # A single failing pair fails the whole task.
    patterns = {
        "pair_analyses": [
            _pair([_group([3], [3])]),
            _pair([_group([3], [3]), _group([5], [5])]),  # offending
            _pair([_group([3], [3])]),
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
    # Identity-territory rejection: a zero-group pair collapses into
    # iter 13's no-blob-identity territory; this matcher is the
    # singleton-blob whole-task identity, disjoint by design.
    patterns = {
        "pair_analyses": [
            _pair([_group([3], [3])]),
            _pair([], num_groups=0, total_changes=0),
        ],
    }
    assert _matcher()(patterns, {}) is False


def test_returns_false_on_missing_groups_key() -> None:
    analysis = _pair([_group([3], [3])])
    del analysis["groups"]
    patterns = {"pair_analyses": [analysis]}
    assert _matcher()(patterns, {}) is False


def test_returns_false_on_non_list_groups() -> None:
    for bad in (None, 42, "oops", {"a": 1}, (), True):
        analysis = _pair([_group([3], [3])])
        analysis["groups"] = bad
        patterns = {"pair_analyses": [analysis]}
        assert _matcher()(patterns, {}) is False, (
            f"groups={bad!r} should not fire"
        )


def test_returns_false_when_any_analysis_is_not_dict() -> None:
    patterns = {
        "pair_analyses": [
            _pair([_group([3], [3])]),
            "not-a-dict",
            _pair([_group([3], [3])]),
        ],
    }
    assert _matcher()(patterns, {}) is False


def test_returns_false_when_any_group_is_not_dict() -> None:
    analysis = _pair([_group([3], [3])])
    analysis["groups"] = [_group([3], [3]), "not-a-dict"]
    patterns = {"pair_analyses": [analysis]}
    assert _matcher()(patterns, {}) is False


# --------------------------------------------------------------------------
# Strict-type-gate cases.
# --------------------------------------------------------------------------

def test_returns_false_when_input_colors_missing() -> None:
    analysis = _pair([_group([3], [3])])
    del analysis["groups"][0]["input_colors"]
    patterns = {"pair_analyses": [analysis]}
    assert _matcher()(patterns, {}) is False


def test_returns_false_when_output_colors_missing() -> None:
    analysis = _pair([_group([3], [3])])
    del analysis["groups"][0]["output_colors"]
    patterns = {"pair_analyses": [analysis]}
    assert _matcher()(patterns, {}) is False


def test_returns_false_when_input_colors_empty() -> None:
    analysis = _pair([_group([3], [3])])
    analysis["groups"][0]["input_colors"] = []
    patterns = {"pair_analyses": [analysis]}
    assert _matcher()(patterns, {}) is False


def test_returns_false_when_output_colors_empty() -> None:
    analysis = _pair([_group([3], [3])])
    analysis["groups"][0]["output_colors"] = []
    patterns = {"pair_analyses": [analysis]}
    assert _matcher()(patterns, {}) is False


def test_returns_false_when_input_colors_not_list() -> None:
    for bad in (None, 42, "oops", {"a": 1}, (3,), True, {3}):
        analysis = _pair([_group([3], [3])])
        analysis["groups"][0]["input_colors"] = bad
        patterns = {"pair_analyses": [analysis]}
        assert _matcher()(patterns, {}) is False, (
            f"input_colors={bad!r} should not fire"
        )


def test_returns_false_when_output_colors_not_list() -> None:
    for bad in (None, 42, "oops", {"a": 1}, (3,), True, {3}):
        analysis = _pair([_group([3], [3])])
        analysis["groups"][0]["output_colors"] = bad
        patterns = {"pair_analyses": [analysis]}
        assert _matcher()(patterns, {}) is False, (
            f"output_colors={bad!r} should not fire"
        )


def test_returns_false_when_color_list_contains_bool() -> None:
    # bools are an int subclass; the strict-type gate rejects them
    # (same posture as iter 14 / 18 / 200-206 / 213 / 214 / 215 / 217 /
    # 218).
    analysis = _pair([_group([True], [True])])
    patterns = {"pair_analyses": [analysis]}
    assert _matcher()(patterns, {}) is False

    analysis2 = _pair([_group([3], [False])])
    patterns2 = {"pair_analyses": [analysis2]}
    assert _matcher()(patterns2, {}) is False


def test_returns_false_when_color_list_contains_non_int() -> None:
    analysis = _pair([_group(["3"], [3])])
    patterns = {"pair_analyses": [analysis]}
    assert _matcher()(patterns, {}) is False

    analysis2 = _pair([_group([3], [3.0])])
    patterns2 = {"pair_analyses": [analysis2]}
    assert _matcher()(patterns2, {}) is False


def test_returns_false_when_color_out_of_range() -> None:
    # Per-group colour values must be in [0, 9]; the iter-180 erase
    # sentinel 13 and the < 0 / > 9 cases are rejected (same as iter
    # 215 / 217 / 218's strict-range gate).
    analysis = _pair([_group([13], [13])])
    patterns = {"pair_analyses": [analysis]}
    assert _matcher()(patterns, {}) is False

    analysis2 = _pair([_group([-1], [-1])])
    patterns2 = {"pair_analyses": [analysis2]}
    assert _matcher()(patterns2, {}) is False


# --------------------------------------------------------------------------
# Behavioural-contract cases.
# --------------------------------------------------------------------------

def test_is_side_effect_free_on_inputs() -> None:
    patterns = {"pair_analyses": [
        _pair([_group([3], [3]), _group([3], [3])]),
    ]}
    params = {"unused": 1}
    before_p = copy.deepcopy(patterns)
    before_q = copy.deepcopy(params)
    _matcher()(patterns, params)
    assert patterns == before_p, "matcher mutated patterns"
    assert params == before_q, "matcher mutated params"


def test_is_deterministic_across_repeats() -> None:
    patterns = {"pair_analyses": [_pair([_group([3], [3])])]}
    results = [_matcher()(patterns, {}) for _ in range(5)]
    assert len(set(results)) == 1, f"non-deterministic outputs: {results}"


def test_returned_value_is_boolean_not_truthy() -> None:
    # recognized_conditions filters on ``match(...) is True`` exactly,
    # so the matcher must return literal Booleans.
    out_true = _matcher()({"pair_analyses": [_pair([_group([3], [3])])]}, {})
    out_false = _matcher()({"pair_analyses": [_pair([_group([3], [0])])]}, {})
    assert out_true is True, f"expected literal True, got {out_true!r}"
    assert out_false is False, f"expected literal False, got {out_false!r}"


def test_ignores_dimensional_fields() -> None:
    # Dimensional fields are orthogonal -- arbitrary dim combinations
    # must not affect the matcher's verdict.
    analysis = _pair([_group([3], [3])], input_height=7, input_width=9,
                     output_height=2, output_width=3, size_match=False)
    patterns = {"pair_analyses": [analysis]}
    assert _matcher()(patterns, {}) is True


def test_ignores_palette_fields() -> None:
    # Whole-grid palette fields are orthogonal -- this matcher only
    # inspects per-group colour lists.
    analysis = _pair([_group([3], [3])],
                     input_palette=[9, 9, 9],
                     output_palette=[1, 1, 1])
    patterns = {"pair_analyses": [analysis]}
    assert _matcher()(patterns, {}) is True


# --------------------------------------------------------------------------
# Orthogonality / refinement / mutual-exclusion matrix against existing
# axes.
# --------------------------------------------------------------------------

def test_strict_refinement_of_iter_216_singleton_recolor() -> None:
    # Strict refinement: this matcher fires => iter 216 fires (whole-
    # task |ic| == |oc| == 1 with cross-group identity is a
    # precondition). Converse fails when iter 216 fires with C != K
    # (non-identity whole-task recolour).
    iter216 = CONDITION_REGISTRY["singleton_recolor"]

    # This matcher fires => iter 216 fires.
    p1 = {"pair_analyses": [_pair([_group([3], [3]), _group([3], [3])])]}
    assert _matcher()(p1, {}) is True and iter216(p1, {}) is True

    # Iter 216 fires, this matcher rejects: C != K globally (recolour 3 -> 0).
    p2 = {"pair_analyses": [_pair([_group([3], [0]), _group([3], [0])])]}
    assert iter216(p2, {}) is True and _matcher()(p2, {}) is False


def test_strict_refinement_of_iter_217_identity_per_group() -> None:
    # Strict refinement: this matcher fires => iter 217 fires (per-
    # group |ic| == |oc| == 1 AND per-group ic == oc on every group).
    # Converse fails when iter 217 fires with per-group fixed points
    # varying across groups (this matcher demands cross-group identity).
    iter217 = CONDITION_REGISTRY["singleton_recolor_identity_per_group"]

    # This matcher fires => iter 217 fires.
    p1 = {"pair_analyses": [_pair([_group([3], [3]), _group([3], [3])])]}
    assert _matcher()(p1, {}) is True and iter217(p1, {}) is True

    # Iter 217 fires, this matcher rejects: per-group fixed points
    # varying across groups (group A C == 3; group B C == 5).
    p2 = {"pair_analyses": [_pair([_group([3], [3]), _group([5], [5])])]}
    assert iter217(p2, {}) is True and _matcher()(p2, {}) is False


def test_strict_mutual_exclusion_with_iter_218_nonidentity_per_group() -> None:
    # KEY witness: this matcher and iter 218 are pairwise disjoint
    # named cells (iter 217 / 218 partition iter 215's territory at
    # per-group identity vs non-identity; this matcher is iter 217's
    # whole-task refinement, so it inherits the strict mutual
    # exclusion against iter 218 in the same direction).
    iter218 = CONDITION_REGISTRY["singleton_recolor_nonidentity_per_group"]

    # This matcher fires; iter 218 rejects (per-group ic == oc on every
    # group).
    p1 = {"pair_analyses": [_pair([_group([3], [3]), _group([3], [3])])]}
    assert _matcher()(p1, {}) is True and iter218(p1, {}) is False

    # Iter 218 fires; this matcher rejects (per-group ic != oc on every
    # group, which forces C != K AND fails cross-group identity unless
    # C, K are globally constant -- but iter 218 still rejects ic ==
    # oc).
    p2 = {"pair_analyses": [_pair([_group([3], [0]), _group([3], [0])])]}
    assert iter218(p2, {}) is True and _matcher()(p2, {}) is False


def test_strict_refinement_of_iter_215_singleton_recolor_per_group() -> None:
    # Iter 215 demands per-group |ic| == |oc| == 1 only; this matcher
    # additionally demands cross-group identity on both sides AND C == K.
    iter215 = CONDITION_REGISTRY["singleton_recolor_per_group"]

    # This matcher fires => iter 215 fires.
    p1 = {"pair_analyses": [_pair([_group([3], [3])])]}
    assert _matcher()(p1, {}) is True and iter215(p1, {}) is True

    # Iter 215 fires, this matcher rejects: per-group singletons vary
    # (ic = [3]/oc = [3] vs ic = [5]/oc = [5]).
    p2 = {"pair_analyses": [_pair([_group([3], [3]), _group([5], [5])])]}
    assert iter215(p2, {}) is True and _matcher()(p2, {}) is False


def test_mutual_exclusion_with_identity_transformation() -> None:
    # Iter 13 fires iff every pair has zero change groups. This matcher
    # rejects the no-group case (universal-over-groups requires >= 1
    # group). Together with iter 13 + iter 217 they form THREE disjoint
    # cells on the (#groups, cross-group-identity) lattice for the
    # singleton rows.
    ident = CONDITION_REGISTRY["identity_transformation"]
    p = {"pair_analyses": [_pair([], num_groups=0, total_changes=0)]}
    # Iter 13 fires; this matcher rejects (no groups).
    assert ident(p, {}) is True and _matcher()(p, {}) is False


def test_strict_implication_of_iter_14_and_iter_18_with_C_eq_K() -> None:
    # Iter 14 ∧ iter 18 ∧ "C == K globally" => this matcher fires.
    iter14 = CONDITION_REGISTRY["input_color_uniform"]
    iter18 = CONDITION_REGISTRY["output_color_uniform"]

    # Iter 14 AND iter 18 fire with C == K == 3: this matcher fires.
    p1 = {"pair_analyses": [_pair([_group([3], [3]), _group([3], [3])])]}
    assert (
        iter14(p1, {}) is True
        and iter18(p1, {}) is True
        and _matcher()(p1, {}) is True
    )

    # Iter 14 AND iter 18 fire with C == 3, K == 0: this matcher
    # rejects (C != K).
    p2 = {"pair_analyses": [_pair([_group([3], [0]), _group([3], [0])])]}
    assert (
        iter14(p2, {}) is True
        and iter18(p2, {}) is True
        and _matcher()(p2, {}) is False
    )

    # This matcher requires cross-group identity: per-group fixed
    # points varying across groups (iter 217 fires) make iter 14 / 18
    # reject AND this matcher reject.
    p3 = {"pair_analyses": [_pair([_group([3], [3]), _group([5], [5])])]}
    assert iter14(p3, {}) is False and _matcher()(p3, {}) is False


def test_strict_implication_of_iter_201_set_equality_per_group() -> None:
    # Iter 201 (``output_colors_equals_input_colors_per_group``) demands
    # per-group set(ic) == set(oc). Strict implication: this matcher
    # fires => iter 201 fires (with every group at ic == oc == [C],
    # per-group set-equality is trivially satisfied). Converse fails on
    # |ic| > 1 cells.
    iter201 = CONDITION_REGISTRY[
        "output_colors_equals_input_colors_per_group"
    ]

    # This matcher fires => iter 201 fires.
    p1 = {"pair_analyses": [_pair([_group([3], [3])])]}
    assert _matcher()(p1, {}) is True and iter201(p1, {}) is True

    # Iter 201 fires (multi-element equality), this matcher rejects.
    p2 = {"pair_analyses": [_pair([_group([3, 4], [3, 4])])]}
    assert iter201(p2, {}) is True and _matcher()(p2, {}) is False


def test_strict_refinement_of_iter_8_consistent_color_mapping() -> None:
    # Iter 8 says every input colour maps to a single output colour
    # globally. This matcher additionally pins both cardinalities to 1
    # AND C == K, reducing to the singleton identity map {C -> C}.
    iter8 = CONDITION_REGISTRY["consistent_color_mapping"]

    # This matcher fires => iter 8 fires.
    p1 = {"pair_analyses": [_pair([_group([3], [3])])]}
    assert _matcher()(p1, {}) is True and iter8(p1, {}) is True

    # Iter 8 fires with multi-pair function-shape, this matcher rejects.
    p2 = {"pair_analyses": [_pair([_group([0], [3]), _group([5], [7])])]}
    assert iter8(p2, {}) is True and _matcher()(p2, {}) is False


def test_strict_refinement_of_iter_197_at_K_prod_eq_1_with_C_eq_K() -> None:
    # Iter 197 says |ic|*|oc| per group is constant across pairs at
    # SOME K_prod. This matcher pins K_prod == 1 per group AND cross-
    # group identity AND C == K. Strict refinement at K_prod == 1
    # with the identity sub-cell.
    iter197 = CONDITION_REGISTRY[
        "change_color_mapping_count_per_group_constant_across_pairs"
    ]

    # This matcher fires => iter 197 fires at K_prod == 1.
    p1 = {
        "pair_analyses": [
            _pair([_group([3], [3])]),
            _pair([_group([3], [3])]),
        ],
    }
    assert _matcher()(p1, {}) is True and iter197(p1, {}) is True

    # Iter 197 fires at K_prod == 1 with C != K (iter 218's territory);
    # this matcher rejects.
    p2 = {
        "pair_analyses": [
            _pair([_group([3], [0])]),
            _pair([_group([3], [0])]),
        ],
    }
    assert iter197(p2, {}) is True and _matcher()(p2, {}) is False


def test_recognized_conditions_includes_singleton_recolor_identity() -> None:
    from agent.conditions import recognized_conditions
    patterns = {"pair_analyses": [
        _pair([_group([3], [3]), _group([3], [3])]),
    ]}
    fired = recognized_conditions(patterns)
    assert MATCHER_NAME in fired, (
        f"{MATCHER_NAME!r} did not fire on a global singleton-identity "
        f"patterns dict; got {fired!r}"
    )


def test_recognized_conditions_excludes_on_global_recolour() -> None:
    # On a whole-task non-identity recolour fixture (single global C !=
    # K), iter 216 fires but THIS matcher rejects (C == K required).
    # Iter 216 must still be in the fired list (no regression).
    from agent.conditions import recognized_conditions
    patterns = {
        "pair_analyses": [
            _pair([_group([3], [0]), _group([3], [0])]),
        ],
    }
    fired = recognized_conditions(patterns)
    assert MATCHER_NAME not in fired, (
        f"{MATCHER_NAME!r} should NOT fire on global non-identity "
        f"recolour; got {fired!r}"
    )
    # No regression on iter 216.
    assert "singleton_recolor" in fired, (
        "iter 216 regression: singleton_recolor should still fire on "
        f"global C != K recolour; got {fired!r}"
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
