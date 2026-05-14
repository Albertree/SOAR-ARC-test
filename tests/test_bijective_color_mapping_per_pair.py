"""
tests/test_bijective_color_mapping_per_pair.py -- exercise the iter-335
matcher ``agent.conditions.bijective_color_mapping_per_pair``.

Pins the matcher's contract per
``agent/conditions/bijective_color_mapping_per_pair.py`` docstring:
every example pair has, on its OWN per-pair accumulated changed-cell
colour relation (forward and inverse, unioned across all groups of
that pair), BOTH forward-function-shape AND inverse-function-shape.
The per-pair projection of iter 333 (``bijective_color_mapping``),
sitting between iter 333 (whole-task scope) and iter 334
(``bijective_color_mapping_per_group``, per-group scope) on the
bijection scope axis.

Runs without pytest:

    python tests/test_bijective_color_mapping_per_pair.py

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


MATCHER_NAME = "bijective_color_mapping_per_pair"


def _matcher():
    return CONDITION_REGISTRY[MATCHER_NAME]


def _group(ic, oc, **overrides):
    base = {
        "input_colors": list(ic),
        "output_colors": list(oc),
        "positions": [(0, 0)],
        "top_row": 0,
        "top_col": 0,
        "cell_count": 1,
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
        "input_palette": [0, 1, 2],
        "output_palette": [0, 1, 2],
        "groups": list(groups),
        "num_groups": len(groups),
        "total_changes": sum(g.get("cell_count", 1) for g in groups),
    }
    base.update(overrides)
    return base


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
# Positive cases -- per-pair bijection.
# ──────────────────────────────────────────────────────────────────────────

def test_returns_true_on_single_pair_single_group_singleton() -> None:
    # Simplest per-pair bijection: one pair with one singleton group.
    # Per-pair forward {0: {3}} and per-pair inverse {3: {0}} are both
    # function-shape.
    patterns = {
        "pair_analyses": [
            _pair([_group([0], [3])]),
        ],
    }
    assert _matcher()(patterns, {}) is True


def test_returns_true_on_canonical_iter10_fixture() -> None:
    # The iter-10 canonical fixture: each pair has three singleton
    # groups ic=[0]/oc=[3], ic=[1]/oc=[4], ic=[2]/oc=[5]. Per-pair
    # forward {0:{3}, 1:{4}, 2:{5}} function-shape; per-pair inverse
    # {3:{0}, 4:{1}, 5:{2}} function-shape. Both pairs accumulate the
    # same bijection independently.
    patterns = {
        "pair_analyses": [
            _pair([_group([0], [3]), _group([1], [4]), _group([2], [5])]),
            _pair([_group([0], [3]), _group([1], [4]), _group([2], [5])]),
        ],
    }
    assert _matcher()(patterns, {}) is True


def test_returns_true_on_per_pair_bijection_with_cross_pair_drift() -> None:
    # Strict-relaxation witness vs iter 333: pair 0 has ic=[0]/oc=[3];
    # pair 1 has ic=[0]/oc=[4]. Each pair has its own per-pair
    # bijection. Global forward {0: {3, 4}} -- NOT function-shape;
    # iter 333 REJECTS. THIS matcher FIRES.
    bij_whole = CONDITION_REGISTRY["bijective_color_mapping"]
    patterns = {
        "pair_analyses": [
            _pair([_group([0], [3])]),
            _pair([_group([0], [4])]),
        ],
    }
    assert _matcher()(patterns, {}) is True
    assert bij_whole(patterns, {}) is False


def test_returns_true_on_per_pair_bijection_with_distinct_palettes() -> None:
    # Per-pair bijection holds when each pair's accumulated forward
    # and inverse dicts are function-shape, regardless of palette
    # constraints. Pair 0: ic=[0]/oc=[3], ic=[1]/oc=[4]. Pair 1:
    # ic=[2]/oc=[5], ic=[6]/oc=[7]. Different bijections per pair.
    patterns = {
        "pair_analyses": [
            _pair([_group([0], [3]), _group([1], [4])]),
            _pair([_group([2], [5]), _group([6], [7])]),
        ],
    }
    assert _matcher()(patterns, {}) is True


def test_returns_true_on_cross_pair_swap() -> None:
    # Pair 0 swaps 0 <-> 1; pair 1 swaps the same pair. Each pair's
    # per-pair forward {0: {1}, 1: {0}} and per-pair inverse
    # {0: {1}, 1: {0}} are function-shape.
    patterns = {
        "pair_analyses": [
            _pair([_group([0], [1]), _group([1], [0])]),
            _pair([_group([0], [1]), _group([1], [0])]),
        ],
    }
    assert _matcher()(patterns, {}) is True


# ──────────────────────────────────────────────────────────────────────────
# Negative cases -- per-pair bijection violations.
# ──────────────────────────────────────────────────────────────────────────

def test_returns_false_on_per_pair_forward_collapse() -> None:
    # Mutual-exclusion witness vs iter 334: one pair with two groups
    # ic=[0]/oc=[3] and ic=[1]/oc=[3]. Per-group bijection holds in
    # each (|ic| == |oc| == 1 each). Per-pair forward {0: {3}, 1: {3}}
    # -- function-shape. Per-pair inverse {3: {0, 1}} -- NOT function-
    # shape. THIS matcher REJECTS. Iter 334 FIRES.
    bij_per_group = CONDITION_REGISTRY["bijective_color_mapping_per_group"]
    patterns = {
        "pair_analyses": [
            _pair([_group([0], [3]), _group([1], [3])]),
        ],
    }
    assert _matcher()(patterns, {}) is False
    assert bij_per_group(patterns, {}) is True


def test_returns_false_on_per_pair_forward_expansion() -> None:
    # Per-pair forward expansion: one pair with two groups
    # ic=[0]/oc=[3] and ic=[0]/oc=[4]. Per-group bijection holds in
    # each (|ic| == |oc| == 1 each). Per-pair forward {0: {3, 4}} --
    # NOT function-shape. THIS matcher REJECTS.
    patterns = {
        "pair_analyses": [
            _pair([_group([0], [3]), _group([0], [4])]),
        ],
    }
    assert _matcher()(patterns, {}) is False


def test_returns_false_on_per_pair_within_group_expansion() -> None:
    # Single group with |oc|>1: ic=[0]/oc=[3, 4]. Per-pair forward
    # {0: {3, 4}} -- NOT function-shape. THIS matcher REJECTS.
    patterns = {
        "pair_analyses": [
            _pair([_group([0], [3, 4])]),
        ],
    }
    assert _matcher()(patterns, {}) is False


def test_returns_false_on_per_pair_within_group_inverse_collapse() -> None:
    # Single group with |ic|>1: ic=[0, 1]/oc=[3]. Per-pair forward
    # {0: {3}, 1: {3}} -- function-shape. Per-pair inverse
    # {3: {0, 1}} -- NOT function-shape. THIS matcher REJECTS.
    patterns = {
        "pair_analyses": [
            _pair([_group([0, 1], [3])]),
        ],
    }
    assert _matcher()(patterns, {}) is False


def test_returns_false_on_any_pair_with_violating_groups() -> None:
    # Universal-over-pairs semantic: even one violating pair rejects
    # the whole task. Pair 0 is per-pair bijective; pair 1 has a
    # per-pair forward collapse.
    patterns = {
        "pair_analyses": [
            _pair([_group([0], [3]), _group([1], [4])]),
            _pair([_group([0], [3]), _group([1], [3])]),
        ],
    }
    assert _matcher()(patterns, {}) is False


def test_returns_false_on_empty_pair_analyses() -> None:
    patterns = {"pair_analyses": []}
    assert _matcher()(patterns, {}) is False


def test_returns_false_on_missing_pair_analyses() -> None:
    assert _matcher()({}, {}) is False


def test_returns_false_on_zero_groups_per_pair() -> None:
    # Per-pair claim with zero groups is meaningless; identity
    # territory is named by iter 13, not by this matcher. Strict-
    # mutual-exclusion posture mirroring iter 213 / 214 / 215 / 333 /
    # 334.
    patterns = {"pair_analyses": [_pair([]), _pair([])]}
    assert _matcher()(patterns, {}) is False


def test_returns_false_on_pair_with_zero_groups_when_others_have_groups() -> None:
    # If ANY pair has zero groups, the universal-over-pairs gate
    # rejects, even if other pairs have valid per-pair bijection.
    patterns = {
        "pair_analyses": [
            _pair([_group([0], [3])]),
            _pair([]),
        ],
    }
    assert _matcher()(patterns, {}) is False


# ──────────────────────────────────────────────────────────────────────────
# Structural rejections.
# ──────────────────────────────────────────────────────────────────────────

def test_returns_false_on_non_dict_patterns() -> None:
    assert _matcher()(None, {}) is False         # type: ignore[arg-type]
    assert _matcher()([], {}) is False           # type: ignore[arg-type]
    assert _matcher()("oops", {}) is False       # type: ignore[arg-type]
    assert _matcher()(42, {}) is False           # type: ignore[arg-type]


def test_returns_false_on_non_list_pair_analyses() -> None:
    for bad in (None, 42, "oops", {"a": 1}, (), True):
        patterns = {"pair_analyses": bad}
        assert _matcher()(patterns, {}) is False, (
            f"pair_analyses={bad!r} should not fire"
        )


def test_returns_false_when_analysis_is_not_dict() -> None:
    patterns = {"pair_analyses": ["not-a-dict"]}
    assert _matcher()(patterns, {}) is False


def test_returns_false_when_groups_field_is_not_list() -> None:
    for bad in (None, 42, "oops", {"a": 1}, (), True):
        patterns = {"pair_analyses": [{"groups": bad}]}
        assert _matcher()(patterns, {}) is False, (
            f"groups={bad!r} should not fire"
        )


def test_returns_false_when_group_is_not_dict() -> None:
    patterns = {"pair_analyses": [{"groups": ["not-a-dict"]}]}
    assert _matcher()(patterns, {}) is False


# ──────────────────────────────────────────────────────────────────────────
# Strict-type-gate cases.
# ──────────────────────────────────────────────────────────────────────────

def test_returns_false_when_input_colors_missing() -> None:
    g = _group([0], [3])
    del g["input_colors"]
    patterns = {"pair_analyses": [_pair([g])]}
    assert _matcher()(patterns, {}) is False


def test_returns_false_when_output_colors_missing() -> None:
    g = _group([0], [3])
    del g["output_colors"]
    patterns = {"pair_analyses": [_pair([g])]}
    assert _matcher()(patterns, {}) is False


def test_returns_false_when_input_colors_is_not_list() -> None:
    for bad in (None, 42, "oops", {"a": 1}, (0,), True):
        g = _group([0], [3])
        g["input_colors"] = bad
        patterns = {"pair_analyses": [_pair([g])]}
        assert _matcher()(patterns, {}) is False, (
            f"input_colors={bad!r} should not fire"
        )


def test_returns_false_when_output_colors_is_not_list() -> None:
    for bad in (None, 42, "oops", {"a": 1}, (3,), True):
        g = _group([0], [3])
        g["output_colors"] = bad
        patterns = {"pair_analyses": [_pair([g])]}
        assert _matcher()(patterns, {}) is False, (
            f"output_colors={bad!r} should not fire"
        )


def test_returns_false_when_input_colors_empty() -> None:
    g = _group([0], [3])
    g["input_colors"] = []
    patterns = {"pair_analyses": [_pair([g])]}
    assert _matcher()(patterns, {}) is False


def test_returns_false_when_output_colors_empty() -> None:
    g = _group([0], [3])
    g["output_colors"] = []
    patterns = {"pair_analyses": [_pair([g])]}
    assert _matcher()(patterns, {}) is False


def test_returns_false_when_input_colors_contains_bool() -> None:
    g = _group([0], [3])
    g["input_colors"] = [0, True]
    patterns = {"pair_analyses": [_pair([g])]}
    assert _matcher()(patterns, {}) is False


def test_returns_false_when_output_colors_contains_bool() -> None:
    g = _group([0], [3])
    g["output_colors"] = [3, False]
    patterns = {"pair_analyses": [_pair([g])]}
    assert _matcher()(patterns, {}) is False


def test_returns_false_on_out_of_range_color() -> None:
    g = _group([0], [3])
    g["output_colors"] = [3, 10]
    patterns = {"pair_analyses": [_pair([g])]}
    assert _matcher()(patterns, {}) is False

    g2 = _group([0], [3])
    g2["input_colors"] = [-1, 0]
    patterns2 = {"pair_analyses": [_pair([g2])]}
    assert _matcher()(patterns2, {}) is False


def test_returns_false_on_non_int_color() -> None:
    g = _group([0], [3])
    g["output_colors"] = [3, "4"]
    patterns = {"pair_analyses": [_pair([g])]}
    assert _matcher()(patterns, {}) is False

    g2 = _group([0], [3])
    g2["input_colors"] = [0.0, 1.0]
    patterns2 = {"pair_analyses": [_pair([g2])]}
    assert _matcher()(patterns2, {}) is False


# ──────────────────────────────────────────────────────────────────────────
# Behavioural-contract cases.
# ──────────────────────────────────────────────────────────────────────────

def test_is_side_effect_free_on_inputs() -> None:
    patterns = {
        "pair_analyses": [
            _pair([_group([0], [3]), _group([1], [4])]),
            _pair([_group([0], [3]), _group([1], [4])]),
        ],
    }
    params = {"unused": 1}
    before_p = copy.deepcopy(patterns)
    before_q = copy.deepcopy(params)
    _matcher()(patterns, params)
    assert patterns == before_p, "matcher mutated patterns"
    assert params == before_q, "matcher mutated params"


def test_is_deterministic_across_repeats() -> None:
    patterns = {
        "pair_analyses": [_pair([_group([0], [3])])],
    }
    results = [_matcher()(patterns, {}) for _ in range(5)]
    assert len(set(results)) == 1, f"non-deterministic outputs: {results}"


def test_returned_value_is_boolean_not_truthy() -> None:
    # recognized_conditions filters on ``match(...) is True`` exactly.
    out_true = _matcher()(
        {"pair_analyses": [_pair([_group([0], [3])])]},
        {},
    )
    out_false = _matcher()(
        {"pair_analyses": [_pair([_group([0], [3]), _group([1], [3])])]},
        {},
    )
    assert out_true is True, f"expected literal True, got {out_true!r}"
    assert out_false is False, f"expected literal False, got {out_false!r}"


def test_params_ignored() -> None:
    patterns = {"pair_analyses": [_pair([_group([0], [3])])]}
    assert _matcher()(patterns, {}) is True
    assert _matcher()(patterns, {"magic": 1}) is True
    assert _matcher()(patterns, {"empty": True}) is True


# ──────────────────────────────────────────────────────────────────────────
# Orthogonality / mutual-exclusion matrix against existing axes.
# ──────────────────────────────────────────────────────────────────────────

def test_strict_implied_by_iter_333_whole_task_bijection() -> None:
    # Iter 333 (whole-task bijection) STRICTLY IMPLIES this matcher:
    # whole-task forward function-shape means the global forward dict
    # is function-shape; the restriction to any single pair's subset
    # of (ic, oc) bindings is therefore also function-shape (a subset
    # of a function is a function). Converse fails on cross-pair
    # drift: each pair bijective, global non-function-shape.
    bij_whole = CONDITION_REGISTRY["bijective_color_mapping"]

    # Both fire on the iter-10 canonical fixture.
    p_both = {
        "pair_analyses": [
            _pair([_group([0], [3]), _group([1], [4])]),
            _pair([_group([0], [3]), _group([1], [4])]),
        ],
    }
    assert _matcher()(p_both, {}) is True
    assert bij_whole(p_both, {}) is True

    # Per-pair bijection WITHOUT whole-task: cross-pair drift.
    p_per_pair_only = {
        "pair_analyses": [
            _pair([_group([0], [3])]),
            _pair([_group([0], [4])]),
        ],
    }
    assert _matcher()(p_per_pair_only, {}) is True
    assert bij_whole(p_per_pair_only, {}) is False

    # Whole-task bijection without per-pair (cell: pair with zero
    # groups). One pair contributes a bijective accumulation; the
    # other has zero groups -- universal-over-pairs gate rejects this
    # matcher, while whole-task accumulation still gives a bijective
    # global dict (only the non-empty pair contributes).
    p_whole_only = {
        "pair_analyses": [
            _pair([_group([0], [3]), _group([1], [4])]),
            _pair([]),
        ],
    }
    assert _matcher()(p_whole_only, {}) is False
    assert bij_whole(p_whole_only, {}) is True

    # Neither (both reject): per-pair forward expansion.
    p_neither = {
        "pair_analyses": [_pair([_group([0], [3, 4])])],
    }
    assert _matcher()(p_neither, {}) is False
    assert bij_whole(p_neither, {}) is False


def test_strict_implies_iter_334_per_group_bijection() -> None:
    # This matcher STRICTLY IMPLIES iter 334 (per-group bijection):
    # per-pair forward and inverse function-shape means within any
    # single group the forward and inverse images are subsets of the
    # per-pair singletons -- per-group bijection holds. Converse fails
    # on intra-pair collapse: two singleton groups in the same pair
    # with shared output.
    bij_per_group = CONDITION_REGISTRY["bijective_color_mapping_per_group"]

    # Per-pair bijection fires both.
    p_bij = {
        "pair_analyses": [_pair([_group([0], [3]), _group([1], [4])])],
    }
    assert _matcher()(p_bij, {}) is True
    assert bij_per_group(p_bij, {}) is True

    # Intra-pair collapse fires iter 334, rejects this matcher.
    p_collapse = {
        "pair_analyses": [_pair([_group([0], [3]), _group([1], [3])])],
    }
    assert _matcher()(p_collapse, {}) is False
    assert bij_per_group(p_collapse, {}) is True

    # Per-group violation (within-group expansion) rejects both.
    p_within = {
        "pair_analyses": [_pair([_group([0], [3, 4])])],
    }
    assert _matcher()(p_within, {}) is False
    assert bij_per_group(p_within, {}) is False


def test_strict_implies_iter_215_singleton_per_group() -> None:
    # This matcher STRICTLY IMPLIES iter 215 (singleton_recolor_per_
    # group, per-group |ic| == |oc| == 1): per-pair bijection implies
    # per-group bijection implies set-level per-group singleton.
    iter215 = CONDITION_REGISTRY["singleton_recolor_per_group"]

    # Both fire on per-group singletons that also satisfy per-pair
    # bijection.
    p_bij = {
        "pair_analyses": [
            _pair([_group([0], [3]), _group([1], [4])]),
        ],
    }
    assert _matcher()(p_bij, {}) is True
    assert iter215(p_bij, {}) is True

    # Intra-pair collapse: per-group singletons hold (iter 215 fires)
    # but per-pair bijection fails (this matcher rejects). Strict-
    # relaxation witness.
    p_collapse = {
        "pair_analyses": [
            _pair([_group([0], [3]), _group([1], [3])]),
        ],
    }
    assert _matcher()(p_collapse, {}) is False
    assert iter215(p_collapse, {}) is True


def test_independent_from_iter_8_whole_task_forward() -> None:
    # Iter 8 (whole-task forward function-shape) is INDEPENDENT of
    # this matcher in general: all four cells of the {iter 8, this
    # matcher} 2x2 product are realisable.
    iter8 = CONDITION_REGISTRY["consistent_color_mapping"]

    # Both fire: iter-10 canonical fixture (per-pair bijection AND
    # consistent global forward).
    p_both = {
        "pair_analyses": [
            _pair([_group([0], [3]), _group([1], [4])]),
            _pair([_group([0], [3]), _group([1], [4])]),
        ],
    }
    assert _matcher()(p_both, {}) is True
    assert iter8(p_both, {}) is True

    # iter 8 only: pair with two singleton groups mapping different
    # inputs to the same output. Global forward {0: {3}, 1: {3}}
    # function-shape (iter 8 fires). Per-pair inverse {3: {0, 1}}
    # not function-shape (this matcher rejects).
    p_iter8 = {
        "pair_analyses": [
            _pair([_group([0], [3]), _group([1], [3])]),
        ],
    }
    assert _matcher()(p_iter8, {}) is False
    assert iter8(p_iter8, {}) is True

    # this-matcher only: cross-pair drift. Each pair bijective; global
    # forward {0: {3, 4}} not function-shape.
    p_this = {
        "pair_analyses": [
            _pair([_group([0], [3])]),
            _pair([_group([0], [4])]),
        ],
    }
    assert _matcher()(p_this, {}) is True
    assert iter8(p_this, {}) is False

    # Neither: per-pair within-group expansion. Per-pair forward
    # {0: {3, 4}} not function-shape (both reject).
    p_neither = {
        "pair_analyses": [_pair([_group([0], [3, 4])])],
    }
    assert _matcher()(p_neither, {}) is False
    assert iter8(p_neither, {}) is False


def test_independent_from_iter_332_whole_task_inverse() -> None:
    # Iter 332 (whole-task inverse function-shape) is INDEPENDENT of
    # this matcher in general (symmetric counterpart of iter 8 case).
    iter332 = CONDITION_REGISTRY["inverse_consistent_color_mapping"]

    # Both fire on the iter-10 canonical fixture.
    p_both = {
        "pair_analyses": [
            _pair([_group([0], [3]), _group([1], [4])]),
            _pair([_group([0], [3]), _group([1], [4])]),
        ],
    }
    assert _matcher()(p_both, {}) is True
    assert iter332(p_both, {}) is True

    # iter 332 only: pair with two singleton groups mapping the SAME
    # input to different outputs. Global inverse {3: {0}, 4: {0}}
    # function-shape (iter 332 fires). Per-pair forward {0: {3, 4}}
    # not function-shape (this matcher rejects).
    p_iter332 = {
        "pair_analyses": [
            _pair([_group([0], [3]), _group([0], [4])]),
        ],
    }
    assert _matcher()(p_iter332, {}) is False
    assert iter332(p_iter332, {}) is True

    # this-matcher only: cross-pair drift on the inverse side. Each
    # pair bijective; global inverse {3: {0, 1}} not function-shape.
    p_this = {
        "pair_analyses": [
            _pair([_group([0], [3])]),
            _pair([_group([1], [3])]),
        ],
    }
    assert _matcher()(p_this, {}) is True
    assert iter332(p_this, {}) is False


def test_mutually_exclusive_with_identity_transformation() -> None:
    # iter 13 (identity) STRICTLY MUTUALLY EXCLUSIVE: identity has
    # zero groups per pair, so the universal-over-pairs gate rejects.
    iden = CONDITION_REGISTRY["identity_transformation"]
    patterns = {
        "pair_analyses": [
            _pair([], total_changes=0, num_groups=0),
        ],
    }
    assert _matcher()(patterns, {}) is False
    assert iden(patterns, {}) is True


def test_independent_from_palette_equality() -> None:
    # iter 185 (palette equality) is INDEPENDENT of per-pair bijection.
    eq = CONDITION_REGISTRY["output_palette_equals_input"]

    # Per-pair bijection AND palette equality (palette permutation
    # within each pair).
    p_both = {
        "pair_analyses": [
            _pair([_group([0], [1]), _group([1], [0])],
                  input_palette=[0, 1], output_palette=[0, 1]),
        ],
    }
    assert _matcher()(p_both, {}) is True
    assert eq(p_both, {}) is True

    # Per-pair bijection WITHOUT palette equality.
    p_bij_only = {
        "pair_analyses": [
            _pair([_group([0], [3]), _group([1], [4])],
                  input_palette=[0, 1, 2], output_palette=[2, 3, 4]),
        ],
    }
    assert _matcher()(p_bij_only, {}) is True
    assert eq(p_bij_only, {}) is False

    # Palette equality WITHOUT per-pair bijection.
    p_eq_only = {
        "pair_analyses": [
            _pair([_group([0], [1, 2])],
                  input_palette=[0, 1, 2], output_palette=[0, 1, 2]),
        ],
    }
    assert _matcher()(p_eq_only, {}) is False
    assert eq(p_eq_only, {}) is True


def test_does_not_swallow_per_pair_violation() -> None:
    # Universal-over-pairs: any single violating pair rejects the
    # whole task. Pair 0 is per-pair bijective; pair 1 has a per-pair
    # forward collapse.
    patterns = {
        "pair_analyses": [
            _pair([_group([0], [3]), _group([1], [4])]),
            _pair([_group([0], [3]), _group([1], [3])]),
        ],
    }
    assert _matcher()(patterns, {}) is False


# ──────────────────────────────────────────────────────────────────────────
# Recognised-conditions wiring -- positive and exclusion witnesses via
# the applier so the matcher is reachable from the registry side.
# ──────────────────────────────────────────────────────────────────────────

def test_recognized_conditions_includes_this_matcher_on_positive() -> None:
    from agent.conditions import recognized_conditions

    patterns = {
        "pair_analyses": [_pair([_group([0], [3])])],
    }
    fired = recognized_conditions(patterns)
    assert MATCHER_NAME in fired, (
        f"{MATCHER_NAME} should fire on per-pair singleton bijection; "
        f"got {fired}"
    )


def test_recognized_conditions_excludes_on_intra_pair_collapse() -> None:
    from agent.conditions import recognized_conditions

    patterns = {
        "pair_analyses": [_pair([_group([0], [3]), _group([1], [3])])],
    }
    fired = recognized_conditions(patterns)
    assert MATCHER_NAME not in fired, (
        f"{MATCHER_NAME} should NOT fire on intra-pair collapse; "
        f"got {fired}"
    )


def test_recognized_conditions_excludes_on_per_pair_within_group_expansion() -> None:
    from agent.conditions import recognized_conditions

    patterns = {
        "pair_analyses": [_pair([_group([0], [3, 4])])],
    }
    fired = recognized_conditions(patterns)
    assert MATCHER_NAME not in fired, (
        f"{MATCHER_NAME} should NOT fire on per-pair within-group expansion; "
        f"got {fired}"
    )


# ──────────────────────────────────────────────────────────────────────────
# Driver.
# ──────────────────────────────────────────────────────────────────────────

def _run_all() -> int:
    tests = [
        test_registered_in_global_registry,
        test_matcher_is_callable,
        test_returns_true_on_single_pair_single_group_singleton,
        test_returns_true_on_canonical_iter10_fixture,
        test_returns_true_on_per_pair_bijection_with_cross_pair_drift,
        test_returns_true_on_per_pair_bijection_with_distinct_palettes,
        test_returns_true_on_cross_pair_swap,
        test_returns_false_on_per_pair_forward_collapse,
        test_returns_false_on_per_pair_forward_expansion,
        test_returns_false_on_per_pair_within_group_expansion,
        test_returns_false_on_per_pair_within_group_inverse_collapse,
        test_returns_false_on_any_pair_with_violating_groups,
        test_returns_false_on_empty_pair_analyses,
        test_returns_false_on_missing_pair_analyses,
        test_returns_false_on_zero_groups_per_pair,
        test_returns_false_on_pair_with_zero_groups_when_others_have_groups,
        test_returns_false_on_non_dict_patterns,
        test_returns_false_on_non_list_pair_analyses,
        test_returns_false_when_analysis_is_not_dict,
        test_returns_false_when_groups_field_is_not_list,
        test_returns_false_when_group_is_not_dict,
        test_returns_false_when_input_colors_missing,
        test_returns_false_when_output_colors_missing,
        test_returns_false_when_input_colors_is_not_list,
        test_returns_false_when_output_colors_is_not_list,
        test_returns_false_when_input_colors_empty,
        test_returns_false_when_output_colors_empty,
        test_returns_false_when_input_colors_contains_bool,
        test_returns_false_when_output_colors_contains_bool,
        test_returns_false_on_out_of_range_color,
        test_returns_false_on_non_int_color,
        test_is_side_effect_free_on_inputs,
        test_is_deterministic_across_repeats,
        test_returned_value_is_boolean_not_truthy,
        test_params_ignored,
        test_strict_implied_by_iter_333_whole_task_bijection,
        test_strict_implies_iter_334_per_group_bijection,
        test_strict_implies_iter_215_singleton_per_group,
        test_independent_from_iter_8_whole_task_forward,
        test_independent_from_iter_332_whole_task_inverse,
        test_mutually_exclusive_with_identity_transformation,
        test_independent_from_palette_equality,
        test_does_not_swallow_per_pair_violation,
        test_recognized_conditions_includes_this_matcher_on_positive,
        test_recognized_conditions_excludes_on_intra_pair_collapse,
        test_recognized_conditions_excludes_on_per_pair_within_group_expansion,
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
    rc = _run_all()
    if rc == 0:
        print("\nall bijective_color_mapping_per_pair tests passed.")
    else:
        print(f"\n{rc} test(s) failed.")
    sys.exit(0 if rc == 0 else 1)
