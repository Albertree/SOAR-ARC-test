"""
tests/test_inverse_consistent_color_mapping_per_pair.py -- exercise the
matcher ``agent.conditions.inverse_consistent_color_mapping_per_pair``.

Pins the matcher's contract per
``agent/conditions/inverse_consistent_color_mapping_per_pair.py`` docstring:
every example pair has, on its OWN per-pair accumulated changed-cell
INVERSE colour relation (unioned across all groups of that pair),
function-shape (every output colour maps from exactly one input colour
within that pair). The per-pair projection of iter 332
(``inverse_consistent_color_mapping``), sitting between iter 332 (whole-
task scope) and iter 214 (``input_color_uniform_per_group``, per-group
scope on the inverse axis) on the inverse function-shape scope axis. The
strict relaxation of iter 335 (``bijective_color_mapping_per_pair``) by
dropping the per-pair forward clause.

Runs without pytest:

    python tests/test_inverse_consistent_color_mapping_per_pair.py

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


MATCHER_NAME = "inverse_consistent_color_mapping_per_pair"


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
# Positive cases -- per-pair inverse function-shape.
# ──────────────────────────────────────────────────────────────────────────

def test_returns_true_on_single_pair_single_group_singleton() -> None:
    # Simplest per-pair inverse function-shape: one pair with one
    # singleton group. Per-pair inverse {3: {0}} is function-shape.
    patterns = {
        "pair_analyses": [
            _pair([_group([0], [3])]),
        ],
    }
    assert _matcher()(patterns, {}) is True


def test_returns_true_on_canonical_iter10_fixture() -> None:
    # The iter-10 canonical fixture: each pair has three singleton
    # groups ic=[0]/oc=[3], ic=[1]/oc=[4], ic=[2]/oc=[5]. Per-pair
    # inverse {3:{0}, 4:{1}, 5:{2}} function-shape. Both pairs
    # accumulate the same function-shape inverse independently.
    patterns = {
        "pair_analyses": [
            _pair([_group([0], [3]), _group([1], [4]), _group([2], [5])]),
            _pair([_group([0], [3]), _group([1], [4]), _group([2], [5])]),
        ],
    }
    assert _matcher()(patterns, {}) is True


def test_returns_true_on_per_pair_inverse_with_cross_pair_drift() -> None:
    # Strict-relaxation witness vs iter 332: pair 0 has ic=[3]/oc=[0];
    # pair 1 has ic=[4]/oc=[0]. Each pair has its own per-pair inverse
    # function-shape. Global inverse {0: {3, 4}} -- NOT function-shape;
    # iter 332 REJECTS. THIS matcher FIRES.
    iter332 = CONDITION_REGISTRY["inverse_consistent_color_mapping"]
    patterns = {
        "pair_analyses": [
            _pair([_group([3], [0])]),
            _pair([_group([4], [0])]),
        ],
    }
    assert _matcher()(patterns, {}) is True
    assert iter332(patterns, {}) is False


def test_returns_true_on_per_pair_forward_collapse() -> None:
    # Strict-relaxation witness vs iter 335: one pair with two groups
    # ic=[0]/oc=[3] and ic=[0]/oc=[4]. Per-pair inverse {3: {0}, 4: {0}}
    # function-shape -- THIS matcher FIRES. Per-pair forward {0: {3, 4}}
    # NOT function-shape -- iter 335 REJECTS.
    bij_per_pair = CONDITION_REGISTRY["bijective_color_mapping_per_pair"]
    patterns = {
        "pair_analyses": [
            _pair([_group([0], [3]), _group([0], [4])]),
        ],
    }
    assert _matcher()(patterns, {}) is True
    assert bij_per_pair(patterns, {}) is False


def test_returns_true_on_per_pair_inverse_with_distinct_palettes() -> None:
    # Per-pair inverse function-shape holds when each pair's
    # accumulated inverse dict is function-shape, regardless of palette
    # constraints. Pair 0: ic=[3]/oc=[0], ic=[4]/oc=[1]. Pair 1:
    # ic=[5]/oc=[2], ic=[7]/oc=[6]. Different per-pair inverses.
    patterns = {
        "pair_analyses": [
            _pair([_group([3], [0]), _group([4], [1])]),
            _pair([_group([5], [2]), _group([7], [6])]),
        ],
    }
    assert _matcher()(patterns, {}) is True


# ──────────────────────────────────────────────────────────────────────────
# Negative cases -- per-pair inverse function-shape violations.
# ──────────────────────────────────────────────────────────────────────────

def test_returns_false_on_per_pair_inverse_collapse_across_groups() -> None:
    # Mutual-exclusion witness vs iter 214 (per-group inverse, set-level
    # equivalent to |ic|==1 per group): one pair with two groups
    # ic=[0]/oc=[3] and ic=[1]/oc=[3]. Per-group inverse function-shape
    # holds in each (|ic| == 1 each). Per-pair inverse {3: {0, 1}}
    # -- NOT function-shape. THIS matcher REJECTS. Iter 214 FIRES.
    iter214 = CONDITION_REGISTRY["input_color_uniform_per_group"]
    patterns = {
        "pair_analyses": [
            _pair([_group([0], [3]), _group([1], [3])]),
        ],
    }
    assert _matcher()(patterns, {}) is False
    assert iter214(patterns, {}) is True


def test_returns_false_on_per_pair_within_group_inverse_collapse() -> None:
    # Single group with |ic|>1: ic=[0, 1]/oc=[3]. Per-pair inverse
    # {3: {0, 1}} -- NOT function-shape. THIS matcher REJECTS.
    patterns = {
        "pair_analyses": [
            _pair([_group([0, 1], [3])]),
        ],
    }
    assert _matcher()(patterns, {}) is False


def test_returns_false_on_any_pair_with_violating_groups() -> None:
    # Universal-over-pairs semantic: even one violating pair rejects
    # the whole task. Pair 0 has per-pair inverse function-shape;
    # pair 1 has a per-pair inverse collapse.
    patterns = {
        "pair_analyses": [
            _pair([_group([3], [0]), _group([4], [1])]),
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
    # 334 / 335 / 336.
    patterns = {"pair_analyses": [_pair([]), _pair([])]}
    assert _matcher()(patterns, {}) is False


def test_returns_false_on_pair_with_zero_groups_when_others_have_groups() -> None:
    # If ANY pair has zero groups, the universal-over-pairs gate
    # rejects, even if other pairs have valid per-pair inverse.
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

def test_strict_implied_by_iter_332_whole_task_inverse() -> None:
    # Iter 332 (whole-task inverse function-shape) STRICTLY IMPLIES this
    # matcher: whole-task inverse function-shape means the global
    # inverse dict is function-shape; the restriction to any single
    # pair's subset of (oc, ic) bindings is therefore also function-
    # shape (a subset of a function is a function). Converse fails on
    # cross-pair drift: each pair inverse function-shape, global non-
    # function-shape.
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

    # Per-pair inverse WITHOUT whole-task inverse: cross-pair drift.
    p_per_pair_only = {
        "pair_analyses": [
            _pair([_group([3], [0])]),
            _pair([_group([4], [0])]),
        ],
    }
    assert _matcher()(p_per_pair_only, {}) is True
    assert iter332(p_per_pair_only, {}) is False

    # Whole-task inverse without per-pair (cell: pair with zero
    # groups). One pair contributes a function-shape inverse
    # accumulation; the other has zero groups -- universal-over-pairs
    # gate rejects this matcher, while whole-task accumulation still
    # gives a function-shape global dict (only the non-empty pair
    # contributes).
    p_whole_only = {
        "pair_analyses": [
            _pair([_group([0], [3]), _group([1], [4])]),
            _pair([]),
        ],
    }
    assert _matcher()(p_whole_only, {}) is False
    assert iter332(p_whole_only, {}) is True

    # Neither (both reject): per-pair inverse collapse.
    p_neither = {
        "pair_analyses": [_pair([_group([0, 1], [3])])],
    }
    assert _matcher()(p_neither, {}) is False
    assert iter332(p_neither, {}) is False


def test_strict_implies_iter_214_per_group_inverse() -> None:
    # This matcher STRICTLY IMPLIES iter 214
    # (``input_color_uniform_per_group``, the per-group inverse
    # function-shape on set-level data): per-pair inverse function-shape
    # means within any single group the inverse image is a subset of the
    # per-pair singletons -- per-group inverse function-shape holds.
    # Converse fails on per-pair inverse collapse across groups: two
    # singleton groups in the same pair with shared output.
    iter214 = CONDITION_REGISTRY["input_color_uniform_per_group"]

    # Per-pair inverse fires both.
    p_inv = {
        "pair_analyses": [_pair([_group([3], [0]), _group([4], [1])])],
    }
    assert _matcher()(p_inv, {}) is True
    assert iter214(p_inv, {}) is True

    # Per-pair inverse collapse fires iter 214, rejects this matcher.
    p_collapse = {
        "pair_analyses": [_pair([_group([0], [3]), _group([1], [3])])],
    }
    assert _matcher()(p_collapse, {}) is False
    assert iter214(p_collapse, {}) is True

    # Per-group inverse violation (within-group |ic|>1) rejects both.
    p_within = {
        "pair_analyses": [_pair([_group([0, 1], [3])])],
    }
    assert _matcher()(p_within, {}) is False
    assert iter214(p_within, {}) is False


def test_strict_implied_by_iter_335_per_pair_bijection() -> None:
    # Iter 335 (per-pair bijection: per-pair forward AND inverse
    # function-shape) STRICTLY IMPLIES this matcher: per-pair forward
    # AND inverse function-shape implies per-pair inverse function-
    # shape. Converse fails on per-pair forward-only violation: a
    # pair with two singleton groups mapping the same input to
    # different outputs.
    bij_per_pair = CONDITION_REGISTRY["bijective_color_mapping_per_pair"]

    # Both fire on the iter-10 canonical fixture.
    p_both = {
        "pair_analyses": [
            _pair([_group([0], [3]), _group([1], [4])]),
            _pair([_group([0], [3]), _group([1], [4])]),
        ],
    }
    assert _matcher()(p_both, {}) is True
    assert bij_per_pair(p_both, {}) is True

    # Per-pair inverse WITHOUT per-pair bijection: per-pair forward
    # expansion. Pair with two groups ic=[0]/oc=[3] and ic=[0]/oc=[4].
    # Per-pair inverse {3: {0}, 4: {0}} function-shape (this matcher
    # fires). Per-pair forward {0: {3, 4}} not function-shape (iter
    # 335 rejects).
    p_inv_only = {
        "pair_analyses": [
            _pair([_group([0], [3]), _group([0], [4])]),
        ],
    }
    assert _matcher()(p_inv_only, {}) is True
    assert bij_per_pair(p_inv_only, {}) is False

    # Neither (both reject): per-pair inverse collapse.
    p_neither = {
        "pair_analyses": [_pair([_group([0, 1], [3])])],
    }
    assert _matcher()(p_neither, {}) is False
    assert bij_per_pair(p_neither, {}) is False


def test_strict_implied_by_iter_333_whole_task_bijection() -> None:
    # Iter 333 (whole-task bijection) STRICTLY IMPLIES this matcher
    # via the chain iter 333 -> iter 332 -> this matcher. Converse
    # fails on per-pair forward collapse: this matcher fires; iter 333
    # rejects via its forward clause.
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

    # Per-pair inverse WITHOUT whole-task bijection: per-pair forward
    # collapse breaks whole-task bijection while preserving per-pair
    # inverse.
    p_inv_only = {
        "pair_analyses": [
            _pair([_group([0], [3]), _group([0], [4])]),
        ],
    }
    assert _matcher()(p_inv_only, {}) is True
    assert bij_whole(p_inv_only, {}) is False


def test_independent_from_iter_8_whole_task_forward() -> None:
    # Iter 8 (whole-task forward function-shape) is INDEPENDENT of this
    # matcher in general. All four cells of the 2x2 are realisable:
    iter8 = CONDITION_REGISTRY["consistent_color_mapping"]

    # Both fire: iter-10 canonical fixture (per-pair inverse AND
    # consistent global forward).
    p_both = {
        "pair_analyses": [
            _pair([_group([0], [3]), _group([1], [4])]),
            _pair([_group([0], [3]), _group([1], [4])]),
        ],
    }
    assert _matcher()(p_both, {}) is True
    assert iter8(p_both, {}) is True

    # iter 8 only: pair with two groups ic=[0]/oc=[3] and ic=[1]/
    # oc=[3]. Global forward {0: {3}, 1: {3}} function-shape (iter 8
    # fires). Per-pair inverse {3: {0, 1}} not function-shape (this
    # matcher rejects).
    p_iter8 = {
        "pair_analyses": [
            _pair([_group([0], [3]), _group([1], [3])]),
        ],
    }
    assert _matcher()(p_iter8, {}) is False
    assert iter8(p_iter8, {}) is True

    # this-matcher only: pair with two groups ic=[0]/oc=[3] and
    # ic=[0]/oc=[4]. Per-pair inverse {3: {0}, 4: {0}} function-shape
    # (this matcher fires). Global forward {0: {3, 4}} not function-
    # shape (iter 8 rejects).
    p_this = {
        "pair_analyses": [
            _pair([_group([0], [3]), _group([0], [4])]),
        ],
    }
    assert _matcher()(p_this, {}) is True
    assert iter8(p_this, {}) is False


def test_independent_from_iter_336_per_pair_forward() -> None:
    # Iter 336 (per-pair forward function-shape) is INDEPENDENT of this
    # matcher in general. All four cells of the 2x2 are realisable:
    iter336 = CONDITION_REGISTRY["consistent_color_mapping_per_pair"]

    # Both fire: per-pair bijection cell -- iter-10 canonical singleton
    # groups.
    p_both = {
        "pair_analyses": [
            _pair([_group([0], [3]), _group([1], [4])]),
        ],
    }
    assert _matcher()(p_both, {}) is True
    assert iter336(p_both, {}) is True

    # iter 336 only: per-pair forward function-shape but per-pair
    # inverse collapse. Two groups ic=[0]/oc=[3] and ic=[1]/oc=[3].
    p_iter336 = {
        "pair_analyses": [
            _pair([_group([0], [3]), _group([1], [3])]),
        ],
    }
    assert _matcher()(p_iter336, {}) is False
    assert iter336(p_iter336, {}) is True

    # this-matcher only: per-pair inverse function-shape but per-pair
    # forward collapse. Two groups ic=[0]/oc=[3] and ic=[0]/oc=[4].
    p_this = {
        "pair_analyses": [
            _pair([_group([0], [3]), _group([0], [4])]),
        ],
    }
    assert _matcher()(p_this, {}) is True
    assert iter336(p_this, {}) is False


def test_independent_from_iter_215_singleton_per_group() -> None:
    # Iter 215 (per-group |ic| == |oc| == 1) is INDEPENDENT of this
    # matcher in general. Examples spanning the 2x2 product:
    iter215 = CONDITION_REGISTRY["singleton_recolor_per_group"]

    # Both fire on per-group singletons that also satisfy per-pair
    # inverse function-shape.
    p_both = {
        "pair_analyses": [
            _pair([_group([0], [3]), _group([1], [4])]),
        ],
    }
    assert _matcher()(p_both, {}) is True
    assert iter215(p_both, {}) is True

    # iter 215 only: per-pair inverse collapse across singleton
    # groups. Per-group singletons hold; per-pair inverse {3: {0, 1}}
    # rejects this matcher.
    p_iter215 = {
        "pair_analyses": [
            _pair([_group([0], [3]), _group([1], [3])]),
        ],
    }
    assert _matcher()(p_iter215, {}) is False
    assert iter215(p_iter215, {}) is True

    # this-matcher only: within-group |oc|>1 with shared input. Per-
    # pair inverse {3: {0}, 4: {0}} function-shape (this matcher
    # fires). Per-group |oc|=2 in the single group (iter 215 rejects).
    p_this = {
        "pair_analyses": [
            _pair([_group([0], [3, 4])]),
        ],
    }
    assert _matcher()(p_this, {}) is True
    assert iter215(p_this, {}) is False


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
    # iter 185 (palette equality) is INDEPENDENT of per-pair inverse
    # function-shape. Examples:
    eq = CONDITION_REGISTRY["output_palette_equals_input"]

    # Per-pair inverse AND palette equality (palette permutation
    # within each pair).
    p_both = {
        "pair_analyses": [
            _pair([_group([0], [1]), _group([1], [0])],
                  input_palette=[0, 1], output_palette=[0, 1]),
        ],
    }
    assert _matcher()(p_both, {}) is True
    assert eq(p_both, {}) is True

    # Per-pair inverse WITHOUT palette equality.
    p_inv_only = {
        "pair_analyses": [
            _pair([_group([0], [3]), _group([1], [4])],
                  input_palette=[0, 1, 2], output_palette=[2, 3, 4]),
        ],
    }
    assert _matcher()(p_inv_only, {}) is True
    assert eq(p_inv_only, {}) is False

    # Palette equality WITHOUT per-pair inverse function-shape.
    p_eq_only = {
        "pair_analyses": [
            _pair([_group([1, 2], [0])],
                  input_palette=[0, 1, 2], output_palette=[0, 1, 2]),
        ],
    }
    assert _matcher()(p_eq_only, {}) is False
    assert eq(p_eq_only, {}) is True


def test_does_not_swallow_per_pair_violation() -> None:
    # Universal-over-pairs: any single violating pair rejects the
    # whole task. Pair 0 has per-pair inverse function-shape; pair 1
    # has a per-pair inverse collapse.
    patterns = {
        "pair_analyses": [
            _pair([_group([3], [0]), _group([4], [1])]),
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
        f"{MATCHER_NAME} should fire on per-pair singleton inverse; "
        f"got {fired}"
    )


def test_recognized_conditions_excludes_on_per_pair_inverse_collapse() -> None:
    from agent.conditions import recognized_conditions

    patterns = {
        "pair_analyses": [_pair([_group([0], [3]), _group([1], [3])])],
    }
    fired = recognized_conditions(patterns)
    assert MATCHER_NAME not in fired, (
        f"{MATCHER_NAME} should NOT fire on per-pair inverse collapse; "
        f"got {fired}"
    )


def test_recognized_conditions_excludes_on_within_group_inverse_collapse() -> None:
    from agent.conditions import recognized_conditions

    patterns = {
        "pair_analyses": [_pair([_group([0, 1], [3])])],
    }
    fired = recognized_conditions(patterns)
    assert MATCHER_NAME not in fired, (
        f"{MATCHER_NAME} should NOT fire on within-group inverse collapse; "
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
        test_returns_true_on_per_pair_inverse_with_cross_pair_drift,
        test_returns_true_on_per_pair_forward_collapse,
        test_returns_true_on_per_pair_inverse_with_distinct_palettes,
        test_returns_false_on_per_pair_inverse_collapse_across_groups,
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
        test_strict_implied_by_iter_332_whole_task_inverse,
        test_strict_implies_iter_214_per_group_inverse,
        test_strict_implied_by_iter_335_per_pair_bijection,
        test_strict_implied_by_iter_333_whole_task_bijection,
        test_independent_from_iter_8_whole_task_forward,
        test_independent_from_iter_336_per_pair_forward,
        test_independent_from_iter_215_singleton_per_group,
        test_mutually_exclusive_with_identity_transformation,
        test_independent_from_palette_equality,
        test_does_not_swallow_per_pair_violation,
        test_recognized_conditions_includes_this_matcher_on_positive,
        test_recognized_conditions_excludes_on_per_pair_inverse_collapse,
        test_recognized_conditions_excludes_on_within_group_inverse_collapse,
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
        print("\nall inverse_consistent_color_mapping_per_pair tests passed.")
    else:
        print(f"\n{rc} test(s) failed.")
    sys.exit(0 if rc == 0 else 1)
