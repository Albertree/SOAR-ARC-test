"""
tests/test_bijective_color_mapping_per_group.py -- exercise the iter-334
matcher ``agent.conditions.bijective_color_mapping_per_group``.

Pins the matcher's contract per
``agent/conditions/bijective_color_mapping_per_group.py`` docstring:
every change group of every example pair has, on its OWN per-group
palettes, BOTH forward-function-shape AND inverse-function-shape, i.e.
on set-level data ``len(set(input_colors)) == 1`` AND
``len(set(output_colors)) == 1`` per group. The named co-fire handle
of (iter 213 AND iter 214) on the per-group scope; the per-group
projection of iter 333 (``bijective_color_mapping``).

Runs without pytest:

    python tests/test_bijective_color_mapping_per_group.py

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


MATCHER_NAME = "bijective_color_mapping_per_group"


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
# Positive cases -- per-group bijection.
# ──────────────────────────────────────────────────────────────────────────

def test_returns_true_on_uniform_one_to_one_per_group() -> None:
    # Simplest per-group bijection: every group maps a single input to
    # a single output. Per-group forward {ic_g: {oc_g}} and per-group
    # inverse {oc_g: {ic_g}} are both function-shape (singleton-valued)
    # in every group of every pair.
    patterns = {
        "pair_analyses": [
            _pair([_group([0], [3])]),
            _pair([_group([1], [4])]),
        ],
    }
    assert _matcher()(patterns, {}) is True


def test_returns_true_on_multiple_singleton_groups_per_pair() -> None:
    # Iter-10 canonical fixture shape: every group has |ic| == |oc|
    # == 1 with possibly different (c_g, k_g) across groups.
    patterns = {
        "pair_analyses": [
            _pair([_group([0], [3]), _group([1], [4]), _group([2], [5])]),
            _pair([_group([0], [3]), _group([1], [4]), _group([2], [5])]),
        ],
    }
    assert _matcher()(patterns, {}) is True


def test_returns_true_on_per_group_bijection_with_global_collapse() -> None:
    # Per-group bijection (|ic| == |oc| == 1 per group) without global
    # bijection: two groups in the same pair map different inputs to the
    # SAME output (global inverse {3: {0, 1}} -- not function-shape).
    # This matcher FIRES (per-group bijection holds); iter 333 REJECTS
    # (global inverse fails). Independence witness vs iter 333.
    bij_whole = CONDITION_REGISTRY["bijective_color_mapping"]
    patterns = {
        "pair_analyses": [
            _pair([_group([0], [3]), _group([1], [3])]),
        ],
    }
    assert _matcher()(patterns, {}) is True
    assert bij_whole(patterns, {}) is False


def test_returns_true_on_per_group_bijection_with_global_expansion() -> None:
    # Per-group bijection (|ic| == |oc| == 1 per group) without global
    # bijection: two groups in the same pair map the SAME input to
    # different outputs (global forward {0: {3, 4}} -- not function-shape).
    # This matcher FIRES (per-group bijection holds); iter 333 REJECTS
    # (global forward fails). Independence witness vs iter 333.
    bij_whole = CONDITION_REGISTRY["bijective_color_mapping"]
    patterns = {
        "pair_analyses": [
            _pair([_group([0], [3]), _group([0], [4])]),
        ],
    }
    assert _matcher()(patterns, {}) is True
    assert bij_whole(patterns, {}) is False


def test_returns_true_across_pairs_with_per_group_bijection() -> None:
    # Cross-pair per-group bijection: pair 0 has one singleton group,
    # pair 1 has another singleton group. Every group has |ic| == |oc|
    # == 1; this matcher fires regardless of any cross-pair / cross-
    # group relation.
    patterns = {
        "pair_analyses": [
            _pair([_group([0], [3])]),
            _pair([_group([1], [4])]),
            _pair([_group([2], [5])]),
        ],
    }
    assert _matcher()(patterns, {}) is True


# ──────────────────────────────────────────────────────────────────────────
# Negative cases -- per-group bijection violations.
# ──────────────────────────────────────────────────────────────────────────

def test_returns_false_on_per_group_forward_expansion() -> None:
    # Mutual-exclusion witness vs iter 214: one group has ic=[0]/
    # oc=[3, 4]. Per-group |ic| == 1 (iter 214 fires). Per-group
    # forward {0: {3, 4}} -- non-function-shape. THIS matcher REJECTS
    # (per-group forward fails within the group).
    inv_per_group = CONDITION_REGISTRY["input_color_uniform_per_group"]
    patterns = {
        "pair_analyses": [
            _pair([_group([0], [3, 4])]),
        ],
    }
    assert _matcher()(patterns, {}) is False
    assert inv_per_group(patterns, {}) is True


def test_returns_false_on_per_group_inverse_collapse() -> None:
    # Mutual-exclusion witness vs iter 213: one group has ic=[0, 1]/
    # oc=[3]. Per-group forward {0: {3}, 1: {3}} -- function-shape (iter
    # 213 fires). Per-group inverse {3: {0, 1}} -- non-function-shape.
    # THIS matcher REJECTS (per-group inverse fails within the group).
    fwd_per_group = CONDITION_REGISTRY["consistent_color_mapping_per_group"]
    patterns = {
        "pair_analyses": [
            _pair([_group([0, 1], [3])]),
        ],
    }
    assert _matcher()(patterns, {}) is False
    assert fwd_per_group(patterns, {}) is True


def test_returns_false_on_per_group_neither_function() -> None:
    # Per-group forward and inverse both fail in the same group:
    # ic=[0, 1]/oc=[3, 4]. Per-group forward {0: {3, 4}, 1: {3, 4}} --
    # non-function (each input has two outputs). Per-group inverse
    # {3: {0, 1}, 4: {0, 1}} -- non-function (each output has two
    # preimages). THIS matcher REJECTS.
    patterns = {
        "pair_analyses": [
            _pair([_group([0, 1], [3, 4])]),
        ],
    }
    assert _matcher()(patterns, {}) is False


def test_returns_false_on_any_pair_with_violating_group() -> None:
    # Universal-over-pairs semantic: even one violating group rejects
    # the whole task. Pair 0 has per-group bijection (|ic|==|oc|==1);
    # pair 1 has a per-group inverse collapse. THIS matcher REJECTS.
    patterns = {
        "pair_analyses": [
            _pair([_group([0], [3])]),
            _pair([_group([0, 1], [3])]),
        ],
    }
    assert _matcher()(patterns, {}) is False


def test_returns_false_on_empty_pair_analyses() -> None:
    patterns = {"pair_analyses": []}
    assert _matcher()(patterns, {}) is False


def test_returns_false_on_missing_pair_analyses() -> None:
    assert _matcher()({}, {}) is False


def test_returns_false_on_zero_groups_per_pair() -> None:
    # Per-group claim with zero groups is meaningless; identity
    # territory is named by iter 13, not by this matcher. Strict-
    # mutual-exclusion posture mirroring iter 213 / 214 / 215 / 333.
    patterns = {"pair_analyses": [_pair([]), _pair([])]}
    assert _matcher()(patterns, {}) is False


def test_returns_false_on_pair_with_zero_groups_when_others_have_groups() -> None:
    # If ANY pair has zero groups, the universal-over-pairs gate
    # rejects, even if other pairs have valid per-group bijection.
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
        {"pair_analyses": [_pair([_group([0, 1], [3])])]},
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

def test_strict_implied_by_iter_215_singleton_recolor_per_group() -> None:
    # Iter 215 (singleton_recolor_per_group) pins per-group |ic| ==
    # |oc| == 1. On set-level data that is exactly this matcher's
    # contract. iter 215 fires <=> this matcher fires (set-level
    # equivalence; both name the per-group singleton cell).
    iter215 = CONDITION_REGISTRY["singleton_recolor_per_group"]

    # Both fire on per-group singletons.
    p_singleton = {
        "pair_analyses": [
            _pair([_group([0], [3]), _group([1], [4])]),
        ],
    }
    assert _matcher()(p_singleton, {}) is True
    assert iter215(p_singleton, {}) is True

    # Per-group |oc| > 1 rejects both.
    p_oc_expand = {
        "pair_analyses": [_pair([_group([0], [3, 4])])],
    }
    assert _matcher()(p_oc_expand, {}) is False
    assert iter215(p_oc_expand, {}) is False

    # Per-group |ic| > 1 rejects both.
    p_ic_expand = {
        "pair_analyses": [_pair([_group([0, 1], [3])])],
    }
    assert _matcher()(p_ic_expand, {}) is False
    assert iter215(p_ic_expand, {}) is False


def test_strict_implies_iter_213_forward_per_group() -> None:
    # this matcher STRICTLY IMPLIES iter 213 (per-group bijection
    # implies per-group forward function-shape). Converse fails: a
    # per-group forward-only mapping (ic=[0, 1]/oc=[3]) fires iter
    # 213 and rejects this matcher.
    fwd_per_group = CONDITION_REGISTRY["consistent_color_mapping_per_group"]

    # Per-group bijection fires both.
    p_bij = {
        "pair_analyses": [_pair([_group([0], [3])])],
    }
    assert _matcher()(p_bij, {}) is True
    assert fwd_per_group(p_bij, {}) is True

    # Per-group forward-only fires iter 213, rejects this matcher.
    p_fwd = {
        "pair_analyses": [_pair([_group([0, 1], [3])])],
    }
    assert _matcher()(p_fwd, {}) is False
    assert fwd_per_group(p_fwd, {}) is True


def test_strict_implies_iter_214_input_uniform_per_group() -> None:
    # this matcher STRICTLY IMPLIES iter 214 (per-group bijection
    # implies per-group |ic| == 1, equivalently per-group inverse
    # function-shape on set-level data). Converse fails: a per-group
    # inverse-only mapping (ic=[0]/oc=[3, 4]) fires iter 214 and
    # rejects this matcher.
    inv_per_group = CONDITION_REGISTRY["input_color_uniform_per_group"]

    # Per-group bijection fires both.
    p_bij = {
        "pair_analyses": [_pair([_group([0], [3])])],
    }
    assert _matcher()(p_bij, {}) is True
    assert inv_per_group(p_bij, {}) is True

    # Per-group inverse-only fires iter 214, rejects this matcher.
    p_inv = {
        "pair_analyses": [_pair([_group([0], [3, 4])])],
    }
    assert _matcher()(p_inv, {}) is False
    assert inv_per_group(p_inv, {}) is True


def test_independent_from_iter_333_whole_task_bijection() -> None:
    # INDEPENDENT in general: per-group bijection and whole-task
    # bijection are distinct scopes; all four cells of the {per-group
    # bijection, whole-task bijection} 2x2 product are realisable.
    bij_whole = CONDITION_REGISTRY["bijective_color_mapping"]

    # Per-group AND whole-task bijection (both fire).
    p_both = {
        "pair_analyses": [
            _pair([_group([0], [3]), _group([1], [4])]),
        ],
    }
    assert _matcher()(p_both, {}) is True
    assert bij_whole(p_both, {}) is True

    # Per-group bijection WITHOUT whole-task (collapse on shared
    # output across groups): two groups map different inputs to the
    # same output. Per-group |ic|==|oc|==1 each; global inverse not
    # function-shape.
    p_per_only = {
        "pair_analyses": [
            _pair([_group([0], [3]), _group([1], [3])]),
        ],
    }
    assert _matcher()(p_per_only, {}) is True
    assert bij_whole(p_per_only, {}) is False

    # Whole-task bijection WITHOUT per-group (a single group with
    # |ic|*|oc|>1 forced to be bijective globally is impossible because
    # the within-group cross-product immediately breaks bijection;
    # therefore the (whole-task bijection, per-group rejection) cell
    # requires a structurally different shape: a single group with
    # |ic|>1 AND |oc|>1 always breaks both. Instead the cell is
    # realised by the cross-pair / cross-group accumulation only when
    # at least one pair has zero groups -- this matcher's universal-
    # over-pairs gate rejects, while whole-task bijection can still
    # fire if other pairs contribute a valid bijection accumulation.)
    p_whole_only = {
        "pair_analyses": [
            _pair([_group([0], [3]), _group([1], [4])]),
            _pair([]),
        ],
    }
    assert _matcher()(p_whole_only, {}) is False
    assert bij_whole(p_whole_only, {}) is True

    # Neither (both reject): per-group forward expansion within a
    # single group (|oc|>1) -- per-group rejects; the within-group
    # forward expansion also makes the global forward non-function-
    # shape, so whole-task rejects too.
    p_neither = {
        "pair_analyses": [_pair([_group([0], [3, 4])])],
    }
    assert _matcher()(p_neither, {}) is False
    assert bij_whole(p_neither, {}) is False


def test_mutually_exclusive_with_identity_transformation() -> None:
    # iter 13 (identity) STRICTLY MUTUALLY EXCLUSIVE: identity has
    # zero groups, so the universal-over-groups gate rejects.
    iden = CONDITION_REGISTRY["identity_transformation"]
    patterns = {
        "pair_analyses": [
            _pair([], total_changes=0, num_groups=0),
        ],
    }
    assert _matcher()(patterns, {}) is False
    assert iden(patterns, {}) is True


def test_independent_from_palette_equality() -> None:
    # iter 185 (palette equality) is INDEPENDENT of per-group bijection.
    eq = CONDITION_REGISTRY["output_palette_equals_input"]

    # Per-group bijection AND palette equality.
    p_both = {
        "pair_analyses": [
            _pair([_group([0], [1]), _group([1], [0])],
                  input_palette=[0, 1], output_palette=[0, 1]),
        ],
    }
    assert _matcher()(p_both, {}) is True
    assert eq(p_both, {}) is True

    # Per-group bijection WITHOUT palette equality.
    p_bij_only = {
        "pair_analyses": [
            _pair([_group([0], [3]), _group([1], [4])],
                  input_palette=[0, 1, 2], output_palette=[2, 3, 4]),
        ],
    }
    assert _matcher()(p_bij_only, {}) is True
    assert eq(p_bij_only, {}) is False

    # Palette equality WITHOUT per-group bijection: a group with
    # |oc|>1 violates per-group bijection; palette equality holds.
    p_eq_only = {
        "pair_analyses": [
            _pair([_group([0], [1, 2])],
                  input_palette=[0, 1, 2], output_palette=[0, 1, 2]),
        ],
    }
    assert _matcher()(p_eq_only, {}) is False
    assert eq(p_eq_only, {}) is True


def test_does_not_swallow_per_pair_violation() -> None:
    # Universal-over-groups-and-pairs: any single violating group in
    # any pair rejects the whole task. Pair 0 is per-group bijective;
    # pair 1's first group has |oc|>1.
    patterns = {
        "pair_analyses": [
            _pair([_group([0], [3]), _group([1], [4])]),
            _pair([_group([0], [3, 5])]),
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
        f"{MATCHER_NAME} should fire on per-group singleton recolour; "
        f"got {fired}"
    )


def test_recognized_conditions_excludes_on_per_group_forward_expansion() -> None:
    from agent.conditions import recognized_conditions

    patterns = {
        "pair_analyses": [_pair([_group([0], [3, 4])])],
    }
    fired = recognized_conditions(patterns)
    assert MATCHER_NAME not in fired, (
        f"{MATCHER_NAME} should NOT fire on per-group forward expansion; "
        f"got {fired}"
    )


def test_recognized_conditions_excludes_on_per_group_inverse_collapse() -> None:
    from agent.conditions import recognized_conditions

    patterns = {
        "pair_analyses": [_pair([_group([0, 1], [3])])],
    }
    fired = recognized_conditions(patterns)
    assert MATCHER_NAME not in fired, (
        f"{MATCHER_NAME} should NOT fire on per-group inverse collapse; "
        f"got {fired}"
    )


# ──────────────────────────────────────────────────────────────────────────
# Driver.
# ──────────────────────────────────────────────────────────────────────────

def _run_all() -> int:
    tests = [
        test_registered_in_global_registry,
        test_matcher_is_callable,
        test_returns_true_on_uniform_one_to_one_per_group,
        test_returns_true_on_multiple_singleton_groups_per_pair,
        test_returns_true_on_per_group_bijection_with_global_collapse,
        test_returns_true_on_per_group_bijection_with_global_expansion,
        test_returns_true_across_pairs_with_per_group_bijection,
        test_returns_false_on_per_group_forward_expansion,
        test_returns_false_on_per_group_inverse_collapse,
        test_returns_false_on_per_group_neither_function,
        test_returns_false_on_any_pair_with_violating_group,
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
        test_strict_implied_by_iter_215_singleton_recolor_per_group,
        test_strict_implies_iter_213_forward_per_group,
        test_strict_implies_iter_214_input_uniform_per_group,
        test_independent_from_iter_333_whole_task_bijection,
        test_mutually_exclusive_with_identity_transformation,
        test_independent_from_palette_equality,
        test_does_not_swallow_per_pair_violation,
        test_recognized_conditions_includes_this_matcher_on_positive,
        test_recognized_conditions_excludes_on_per_group_forward_expansion,
        test_recognized_conditions_excludes_on_per_group_inverse_collapse,
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
        print("\nall bijective_color_mapping_per_group tests passed.")
    else:
        print(f"\n{rc} test(s) failed.")
    sys.exit(0 if rc == 0 else 1)
