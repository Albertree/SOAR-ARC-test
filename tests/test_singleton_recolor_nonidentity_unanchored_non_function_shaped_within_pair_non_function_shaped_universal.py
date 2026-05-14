"""
tests/test_singleton_recolor_nonidentity_unanchored_non_function_
shaped_within_pair_non_function_shaped_universal.py -- exercise the
iter-228 matcher ``agent.conditions.singleton_recolor_nonidentity_
unanchored_non_function_shaped_within_pair_non_function_shaped_
universal``.

Pins the matcher's contract per the docstring of
``agent/conditions/singleton_recolor_nonidentity_unanchored_non_
function_shaped_within_pair_non_function_shaped_universal.py``:
every group of every example pair has BOTH ``len(set(input_colors))
== 1`` AND ``len(set(output_colors)) == 1`` AND ``set(input_colors)
!= set(output_colors)`` AND ``len(observed_input_colors) > 1`` AND
``len(observed_output_colors) > 1`` (iter 223 (F, F) territory) AND
the GLOBAL (C_g, K_g) cross-product across the union of all pairs'
groups is NON-FUNCTION-shaped (some C_g sees >= 2 distinct K_g
values across the union -- iter 225 territory) AND EVERY pair has
WITHIN-pair NON-function-shape (some C_g sees >= 2 distinct K_g
values within EACH pair's own groups -- the strict refinement of
iter 227's existential claim at the universal-quantifier sub-cell).

Universal over groups; universal over pairs on the within-pair
non-function-shape claim; fail-closed on empty / no-group /
malformed input.

Runs without pytest:

    python tests/test_singleton_recolor_nonidentity_unanchored_non_function_shaped_within_pair_non_function_shaped_universal.py

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


MATCHER_NAME = (
    "singleton_recolor_nonidentity_unanchored_non_function_shaped_"
    "within_pair_non_function_shaped_universal"
)


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

def test_returns_true_on_canonical_every_pair_within_pair_collision() -> None:
    # Canonical fixture: every pair has within-pair non-function-shape.
    # Pair 1: C=3 -> {0, 7}; pair 2: C=5 -> {1, 4}. |observed_input| =
    # {3, 5} > 1; |observed_output| = {0, 1, 4, 7} > 1.
    patterns = {
        "pair_analyses": [
            _pair([_group([3], [0]), _group([3], [7])]),
            _pair([_group([5], [1]), _group([5], [4])]),
        ],
    }
    assert _matcher()(patterns, {}) is True


def test_returns_true_on_iter_225_single_pair_canonical_collision() -> None:
    # Single-pair iter-225 fixture: trivially "every pair" (the only
    # pair) has within-pair non-function-shape. C=3 -> {0, 7} within
    # the sole pair. Iter 227 and this matcher both fire (universal
    # over a single pair reduces to existential).
    patterns = {
        "pair_analyses": [
            _pair([_group([3], [0]), _group([3], [7]), _group([5], [7])]),
        ],
    }
    assert _matcher()(patterns, {}) is True


def test_returns_true_when_same_C_collides_in_every_pair() -> None:
    # Every pair has C=3 colliding within-pair (3 -> {0, 7} in pair 1;
    # 3 -> {1, 9} in pair 2). |observed_input| = {3} == 1 fails iter
    # 225 precondition -- adjust to keep input multi-valued.
    patterns = {
        "pair_analyses": [
            _pair([_group([3], [0]), _group([3], [7]), _group([5], [4])]),
            _pair([_group([3], [1]), _group([3], [9]), _group([5], [4])]),
        ],
    }
    assert _matcher()(patterns, {}) is True


def test_returns_true_when_different_C_collides_per_pair() -> None:
    # Each pair has within-pair non-function-shape on a different C:
    # pair 1: C=3 -> {0, 7}; pair 2: C=5 -> {1, 4}. The universal
    # quantifier does not require the same C to collide across pairs;
    # it requires every pair to have SOME within-pair collision.
    patterns = {
        "pair_analyses": [
            _pair([_group([3], [0]), _group([3], [7])]),
            _pair([_group([5], [1]), _group([5], [4])]),
        ],
    }
    assert _matcher()(patterns, {}) is True


def test_returns_true_with_three_pairs_each_within_pair_colliding() -> None:
    # Three pairs, each within-pair non-function-shape.
    patterns = {
        "pair_analyses": [
            _pair([_group([3], [0]), _group([3], [7])]),
            _pair([_group([5], [1]), _group([5], [4])]),
            _pair([_group([2], [6]), _group([2], [8])]),
        ],
    }
    assert _matcher()(patterns, {}) is True


def test_returns_true_with_duplicate_entries_in_color_lists() -> None:
    # Colour lists are de-duplicated set-wise; the per-pair within-pair
    # non-function-shape claim is on the unique (C, K) pairs.
    patterns = {
        "pair_analyses": [
            _pair([_group([3, 3], [0, 0]), _group([3], [7]),
                   _group([5], [4])]),
            _pair([_group([5, 5], [1, 1]), _group([5], [4])]),
        ],
    }
    assert _matcher()(patterns, {}) is True


def test_returns_true_on_color_zero_and_nine_boundary_witnesses() -> None:
    # Edge: C=0 (low boundary) collides within pair 1; C=9 (high
    # boundary) collides within pair 2.
    patterns = {
        "pair_analyses": [
            _pair([_group([0], [3]), _group([0], [9]), _group([5], [4])]),
            _pair([_group([9], [1]), _group([9], [4])]),
        ],
    }
    assert _matcher()(patterns, {}) is True


def test_returns_true_with_extra_groups_around_collision() -> None:
    # Each pair has additional non-colliding groups around the
    # within-pair collision; the universal claim only requires SOME
    # collision per pair.
    patterns = {
        "pair_analyses": [
            _pair([_group([3], [0]), _group([3], [7]), _group([5], [4])]),
            _pair([_group([2], [6]), _group([2], [8]), _group([5], [4])]),
        ],
    }
    assert _matcher()(patterns, {}) is True


# --------------------------------------------------------------------------
# Negative cases.
# --------------------------------------------------------------------------

def test_returns_false_on_mixed_shape_across_pairs() -> None:
    # KEY iter-227 strict-refinement witness: pair 1 within-pair
    # non-function-shape (C=3 -> {0, 7}); pair 2 within-pair function-
    # shape (3 -> 0, 5 -> 4). Iter 227 fires (existential); this
    # matcher REJECTS (universal demand fails on pair 2).
    patterns = {
        "pair_analyses": [
            _pair([_group([3], [0]), _group([3], [7])]),
            _pair([_group([3], [0]), _group([5], [4])]),
        ],
    }
    assert _matcher()(patterns, {}) is False


def test_returns_false_when_only_one_pair_has_collision() -> None:
    # Pair 1 within-pair non-function-shape; pair 2 within-pair
    # function-shape with multi-group. Iter 227 fires; this matcher
    # rejects.
    patterns = {
        "pair_analyses": [
            _pair([_group([3], [0]), _group([3], [7]), _group([5], [4])]),
            _pair([_group([3], [9]), _group([5], [4])]),
        ],
    }
    assert _matcher()(patterns, {}) is False


def test_returns_false_on_iter_226_canonical_fixture() -> None:
    # KEY iter-226 mutual-exclusion witness: every pair is within-pair
    # function-shape. Global non-function-shape across pairs (iter 226
    # territory); iter 227 / this matcher reject.
    patterns = {
        "pair_analyses": [
            _pair([_group([3], [0]), _group([5], [4])]),
            _pair([_group([3], [7]), _group([5], [4])]),
        ],
    }
    assert _matcher()(patterns, {}) is False


def test_returns_false_on_collision_only_across_pairs() -> None:
    # Each pair is within-pair function-shape; only across-pair
    # collision exists. Iter 226 territory; iter 227 / this matcher
    # reject.
    patterns = {
        "pair_analyses": [
            _pair([_group([3], [0])]),
            _pair([_group([3], [7])]),
        ],
    }
    assert _matcher()(patterns, {}) is False


def test_returns_false_on_iter_10_canonical_function_shape_fixture() -> None:
    # KEY iter-224 / iter-10 co-fire witness: function-shape globally
    # AND within-pair function-shape on every pair; iter 225 / 227 /
    # this matcher all reject.
    patterns = {"pair_analyses": [
        _pair([_group([0], [3]), _group([1], [4]), _group([2], [5])]),
    ]}
    assert _matcher()(patterns, {}) is False


def test_returns_false_on_global_function_shape_with_multi_pair() -> None:
    # Both pairs within-pair function-shape; union also function-shape
    # (iter 224 territory). Iter 227 / this matcher reject.
    patterns = {
        "pair_analyses": [
            _pair([_group([3], [0]), _group([5], [4])]),
            _pair([_group([3], [0]), _group([5], [4])]),
        ],
    }
    assert _matcher()(patterns, {}) is False


def test_returns_false_on_single_pair_function_shape_alone() -> None:
    # Single pair, multi-group, within-pair function-shape, |observed_
    # input| = {3, 5} > 1, |observed_output| = {0, 4} > 1. Iter 224
    # territory; iter 227 / this matcher reject.
    patterns = {
        "pair_analyses": [
            _pair([_group([3], [0]), _group([5], [4])]),
        ],
    }
    assert _matcher()(patterns, {}) is False


def test_returns_false_when_last_pair_is_within_pair_function_shape() -> None:
    # Pair 1 / pair 2 within-pair non-function-shape; pair 3 within-
    # pair function-shape. Iter 227 fires; this matcher rejects.
    patterns = {
        "pair_analyses": [
            _pair([_group([3], [0]), _group([3], [7])]),
            _pair([_group([5], [1]), _group([5], [4])]),
            _pair([_group([3], [0]), _group([5], [4])]),
        ],
    }
    assert _matcher()(patterns, {}) is False


def test_returns_false_on_iter_220_territory_both_anchored() -> None:
    # Iter 220: cross-group identity on BOTH sides; iter 225 rejects.
    patterns = {
        "pair_analyses": [
            _pair([_group([3], [0]), _group([3], [0])]),
            _pair([_group([3], [0]), _group([3], [0])]),
        ],
    }
    assert _matcher()(patterns, {}) is False


def test_returns_false_on_iter_221_territory_input_anchored() -> None:
    # Iter 221: cross-group identity on the INPUT side. The fixture
    # has within-pair non-function-shape on C=3 -> {0, 7}, but the
    # iter 225 precondition on |observed_input| > 1 fails.
    patterns = {
        "pair_analyses": [
            _pair([_group([3], [0]), _group([3], [7])]),
        ],
    }
    assert _matcher()(patterns, {}) is False


def test_returns_false_on_iter_222_territory_output_anchored() -> None:
    # Iter 222: cross-group identity on the OUTPUT side. |observed_
    # output| == 1 fails.
    patterns = {
        "pair_analyses": [
            _pair([_group([3], [0]), _group([7], [0])]),
        ],
    }
    assert _matcher()(patterns, {}) is False


def test_returns_false_on_global_identity_C_eq_K() -> None:
    # Iter 219 territory: C == K globally.
    patterns = {
        "pair_analyses": [
            _pair([_group([3], [3]), _group([3], [3])]),
        ],
    }
    assert _matcher()(patterns, {}) is False


def test_returns_false_when_single_pair_with_one_group_only() -> None:
    # Degenerate: |observed_input| == 1 AND |observed_output| == 1
    # AND no collision possible with a single group.
    patterns = {"pair_analyses": [_pair([_group([3], [0])])]}
    assert _matcher()(patterns, {}) is False


def test_returns_false_when_only_input_side_varies() -> None:
    # |observed_input| > 1 but |observed_output| == 1.
    patterns = {
        "pair_analyses": [
            _pair([_group([3], [0]), _group([5], [0])]),
            _pair([_group([3], [0])]),
        ],
    }
    assert _matcher()(patterns, {}) is False


def test_returns_false_when_only_output_side_varies() -> None:
    # |observed_input| == 1 but |observed_output| > 1.
    patterns = {
        "pair_analyses": [
            _pair([_group([3], [0])]),
            _pair([_group([3], [7])]),
        ],
    }
    assert _matcher()(patterns, {}) is False


def test_returns_false_when_any_group_has_multi_input() -> None:
    patterns = {
        "pair_analyses": [
            _pair([_group([3, 4], [0]), _group([3], [7])]),
            _pair([_group([5], [1]), _group([5], [4])]),
        ],
    }
    assert _matcher()(patterns, {}) is False


def test_returns_false_when_any_group_has_multi_output() -> None:
    patterns = {
        "pair_analyses": [
            _pair([_group([3], [0, 4]), _group([3], [7])]),
            _pair([_group([5], [1]), _group([5], [4])]),
        ],
    }
    assert _matcher()(patterns, {}) is False


def test_returns_false_when_one_group_is_identity() -> None:
    # Universal-over-groups: an identity group violates per-group ic
    # != oc on that group.
    patterns = {
        "pair_analyses": [
            _pair([_group([3], [0]), _group([3], [7]), _group([5], [5])]),
            _pair([_group([5], [1]), _group([5], [4])]),
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
    patterns = {
        "pair_analyses": [
            _pair([_group([3], [0]), _group([3], [7])]),
            _pair([], num_groups=0, total_changes=0),
        ],
    }
    assert _matcher()(patterns, {}) is False


def test_returns_false_on_missing_groups_key() -> None:
    analysis = _pair([_group([3], [0]), _group([3], [7])])
    del analysis["groups"]
    patterns = {"pair_analyses": [analysis]}
    assert _matcher()(patterns, {}) is False


def test_returns_false_on_non_list_groups() -> None:
    for bad in (None, 42, "oops", {"a": 1}, (), True):
        analysis = _pair([_group([3], [0]), _group([3], [7])])
        analysis["groups"] = bad
        patterns = {"pair_analyses": [analysis]}
        assert _matcher()(patterns, {}) is False, (
            f"groups={bad!r} should not fire"
        )


def test_returns_false_when_any_analysis_is_not_dict() -> None:
    patterns = {
        "pair_analyses": [
            _pair([_group([3], [0]), _group([3], [7])]),
            "not-a-dict",
            _pair([_group([5], [1]), _group([5], [4])]),
        ],
    }
    assert _matcher()(patterns, {}) is False


def test_returns_false_when_any_group_is_not_dict() -> None:
    analysis = _pair([_group([3], [0]), _group([3], [7])])
    analysis["groups"] = [_group([3], [0]), "not-a-dict"]
    patterns = {"pair_analyses": [analysis]}
    assert _matcher()(patterns, {}) is False


# --------------------------------------------------------------------------
# Strict-type-gate cases.
# --------------------------------------------------------------------------

def test_returns_false_when_input_colors_missing() -> None:
    analysis = _pair([_group([3], [0]), _group([3], [7])])
    del analysis["groups"][0]["input_colors"]
    patterns = {
        "pair_analyses": [
            analysis,
            _pair([_group([5], [1]), _group([5], [4])]),
        ],
    }
    assert _matcher()(patterns, {}) is False


def test_returns_false_when_output_colors_missing() -> None:
    analysis = _pair([_group([3], [0]), _group([3], [7])])
    del analysis["groups"][0]["output_colors"]
    patterns = {
        "pair_analyses": [
            analysis,
            _pair([_group([5], [1]), _group([5], [4])]),
        ],
    }
    assert _matcher()(patterns, {}) is False


def test_returns_false_when_input_colors_empty() -> None:
    analysis = _pair([_group([3], [0]), _group([3], [7])])
    analysis["groups"][0]["input_colors"] = []
    patterns = {
        "pair_analyses": [
            analysis,
            _pair([_group([5], [1]), _group([5], [4])]),
        ],
    }
    assert _matcher()(patterns, {}) is False


def test_returns_false_when_output_colors_empty() -> None:
    analysis = _pair([_group([3], [0]), _group([3], [7])])
    analysis["groups"][0]["output_colors"] = []
    patterns = {
        "pair_analyses": [
            analysis,
            _pair([_group([5], [1]), _group([5], [4])]),
        ],
    }
    assert _matcher()(patterns, {}) is False


def test_returns_false_when_input_colors_not_list() -> None:
    for bad in (None, 42, "oops", {"a": 1}, (3,), True, {3}):
        analysis = _pair([_group([3], [0]), _group([3], [7])])
        analysis["groups"][0]["input_colors"] = bad
        patterns = {
            "pair_analyses": [
                analysis,
                _pair([_group([5], [1]), _group([5], [4])]),
            ],
        }
        assert _matcher()(patterns, {}) is False, (
            f"input_colors={bad!r} should not fire"
        )


def test_returns_false_when_output_colors_not_list() -> None:
    for bad in (None, 42, "oops", {"a": 1}, (3,), True, {3}):
        analysis = _pair([_group([3], [0]), _group([3], [7])])
        analysis["groups"][0]["output_colors"] = bad
        patterns = {
            "pair_analyses": [
                analysis,
                _pair([_group([5], [1]), _group([5], [4])]),
            ],
        }
        assert _matcher()(patterns, {}) is False, (
            f"output_colors={bad!r} should not fire"
        )


def test_returns_false_when_color_list_contains_bool() -> None:
    analysis = _pair([_group([True], [False]), _group([3], [7])])
    patterns = {
        "pair_analyses": [
            analysis,
            _pair([_group([5], [1]), _group([5], [4])]),
        ],
    }
    assert _matcher()(patterns, {}) is False

    analysis2 = _pair([_group([3], [False]), _group([3], [7])])
    patterns2 = {
        "pair_analyses": [
            analysis2,
            _pair([_group([5], [1]), _group([5], [4])]),
        ],
    }
    assert _matcher()(patterns2, {}) is False


def test_returns_false_when_color_list_contains_non_int() -> None:
    analysis = _pair([_group(["3"], [0]), _group([3], [7])])
    patterns = {
        "pair_analyses": [
            analysis,
            _pair([_group([5], [1]), _group([5], [4])]),
        ],
    }
    assert _matcher()(patterns, {}) is False

    analysis2 = _pair([_group([3], [0.0]), _group([3], [7])])
    patterns2 = {
        "pair_analyses": [
            analysis2,
            _pair([_group([5], [1]), _group([5], [4])]),
        ],
    }
    assert _matcher()(patterns2, {}) is False


def test_returns_false_when_color_out_of_range() -> None:
    analysis = _pair([_group([13], [0]), _group([3], [7])])
    patterns = {
        "pair_analyses": [
            analysis,
            _pair([_group([5], [1]), _group([5], [4])]),
        ],
    }
    assert _matcher()(patterns, {}) is False

    analysis2 = _pair([_group([-1], [0]), _group([3], [7])])
    patterns2 = {
        "pair_analyses": [
            analysis2,
            _pair([_group([5], [1]), _group([5], [4])]),
        ],
    }
    assert _matcher()(patterns2, {}) is False


# --------------------------------------------------------------------------
# Behavioural-contract cases.
# --------------------------------------------------------------------------

def test_is_side_effect_free_on_inputs() -> None:
    patterns = {
        "pair_analyses": [
            _pair([_group([3], [0]), _group([3], [7])]),
            _pair([_group([5], [1]), _group([5], [4])]),
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
        "pair_analyses": [
            _pair([_group([3], [0]), _group([3], [7])]),
            _pair([_group([5], [1]), _group([5], [4])]),
        ],
    }
    results = [_matcher()(patterns, {}) for _ in range(5)]
    assert len(set(results)) == 1, f"non-deterministic outputs: {results}"


def test_returned_value_is_boolean_not_truthy() -> None:
    out_true = _matcher()(
        {
            "pair_analyses": [
                _pair([_group([3], [0]), _group([3], [7])]),
                _pair([_group([5], [1]), _group([5], [4])]),
            ],
        },
        {},
    )
    out_false = _matcher()(
        {
            "pair_analyses": [
                _pair([_group([3], [0]), _group([3], [7])]),
                _pair([_group([3], [0]), _group([5], [4])]),
            ],
        },
        {},
    )
    assert out_true is True, f"expected literal True, got {out_true!r}"
    assert out_false is False, f"expected literal False, got {out_false!r}"


def test_ignores_dimensional_fields() -> None:
    analysis_a = _pair(
        [_group([3], [0]), _group([3], [7])],
        input_height=7, input_width=9,
        output_height=2, output_width=3, size_match=False,
    )
    analysis_b = _pair(
        [_group([5], [1]), _group([5], [4])],
        input_height=4, input_width=4,
        output_height=4, output_width=4, size_match=True,
    )
    patterns = {"pair_analyses": [analysis_a, analysis_b]}
    assert _matcher()(patterns, {}) is True


def test_ignores_palette_fields() -> None:
    analysis_a = _pair(
        [_group([3], [0]), _group([3], [7])],
        input_palette=[9, 9, 9],
        output_palette=[1, 1, 1],
    )
    analysis_b = _pair(
        [_group([5], [1]), _group([5], [4])],
        input_palette=[2],
        output_palette=[2, 2],
    )
    patterns = {"pair_analyses": [analysis_a, analysis_b]}
    assert _matcher()(patterns, {}) is True


# --------------------------------------------------------------------------
# Orthogonality / refinement / mutual-exclusion matrix against existing
# axes.
# --------------------------------------------------------------------------

def test_strict_refinement_of_iter_227_within_pair_non_function_shape() -> None:
    # KEY iter-227 strict-refinement witness: this matcher fires =>
    # iter 227 fires. The converse fails on the mixed-shape sub-cell
    # (some pair within-pair function-shape AND some pair within-pair
    # non-function-shape).
    iter227 = CONDITION_REGISTRY[
        "singleton_recolor_nonidentity_unanchored_non_function_shaped_"
        "within_pair_non_function_shaped"
    ]

    # This matcher fires => iter 227 fires.
    p1 = {
        "pair_analyses": [
            _pair([_group([3], [0]), _group([3], [7])]),
            _pair([_group([5], [1]), _group([5], [4])]),
        ],
    }
    assert _matcher()(p1, {}) is True and iter227(p1, {}) is True

    # Iter 227 fires on the mixed-shape sub-cell; this matcher rejects.
    p2 = {
        "pair_analyses": [
            _pair([_group([3], [0]), _group([3], [7])]),
            _pair([_group([3], [0]), _group([5], [4])]),
        ],
    }
    assert iter227(p2, {}) is True and _matcher()(p2, {}) is False


def test_strict_mutual_exclusion_with_iter_226_within_pair_function_shaped() -> None:
    # KEY iter-226 mutual-exclusion witness: iter 226 demands every
    # pair within-pair function-shape; this matcher demands every
    # pair within-pair non-function-shape. Disjoint by definition.
    iter226 = CONDITION_REGISTRY[
        "singleton_recolor_nonidentity_unanchored_non_function_shaped_"
        "within_pair_function_shaped"
    ]

    # Iter 226 fires; this matcher rejects.
    p1 = {
        "pair_analyses": [
            _pair([_group([3], [0]), _group([5], [4])]),
            _pair([_group([3], [7]), _group([5], [4])]),
        ],
    }
    assert iter226(p1, {}) is True and _matcher()(p1, {}) is False

    # This matcher fires; iter 226 rejects.
    p2 = {
        "pair_analyses": [
            _pair([_group([3], [0]), _group([3], [7])]),
            _pair([_group([5], [1]), _group([5], [4])]),
        ],
    }
    assert _matcher()(p2, {}) is True and iter226(p2, {}) is False


def test_strict_refinement_of_iter_225_non_function_shaped() -> None:
    iter225 = CONDITION_REGISTRY[
        "singleton_recolor_nonidentity_unanchored_non_function_shaped"
    ]

    # This matcher fires => iter 225 fires.
    p1 = {
        "pair_analyses": [
            _pair([_group([3], [0]), _group([3], [7])]),
            _pair([_group([5], [1]), _group([5], [4])]),
        ],
    }
    assert _matcher()(p1, {}) is True and iter225(p1, {}) is True

    # Iter 225 fires (iter 226 within-pair function-shape territory);
    # this matcher rejects.
    p2 = {
        "pair_analyses": [
            _pair([_group([3], [0]), _group([5], [4])]),
            _pair([_group([3], [7]), _group([5], [4])]),
        ],
    }
    assert iter225(p2, {}) is True and _matcher()(p2, {}) is False


def test_strict_mutual_exclusion_with_iter_224_function_shaped() -> None:
    iter224 = CONDITION_REGISTRY[
        "singleton_recolor_nonidentity_unanchored_function_shaped"
    ]

    # This matcher fires; iter 224 rejects.
    p1 = {
        "pair_analyses": [
            _pair([_group([3], [0]), _group([3], [7])]),
            _pair([_group([5], [1]), _group([5], [4])]),
        ],
    }
    assert _matcher()(p1, {}) is True and iter224(p1, {}) is False

    # Iter 224 fires (global function-shape); this matcher rejects.
    p2 = {"pair_analyses": [_pair([_group([3], [0]), _group([5], [7])])]}
    assert iter224(p2, {}) is True and _matcher()(p2, {}) is False


def test_strict_refinement_of_iter_223_unanchored() -> None:
    iter223 = CONDITION_REGISTRY["singleton_recolor_nonidentity_unanchored"]

    # This matcher fires => iter 223 fires.
    p1 = {
        "pair_analyses": [
            _pair([_group([3], [0]), _group([3], [7])]),
            _pair([_group([5], [1]), _group([5], [4])]),
        ],
    }
    assert _matcher()(p1, {}) is True and iter223(p1, {}) is True

    # Iter 223 fires on global function-shape cell; this matcher
    # rejects.
    p2 = {"pair_analyses": [_pair([_group([3], [0]), _group([5], [7])])]}
    assert iter223(p2, {}) is True and _matcher()(p2, {}) is False


def test_strict_mutual_exclusion_with_iter_8_consistent_color_mapping() -> None:
    iter8 = CONDITION_REGISTRY["consistent_color_mapping"]

    # This matcher fires; iter 8 rejects.
    p1 = {
        "pair_analyses": [
            _pair([_group([3], [0]), _group([3], [7])]),
            _pair([_group([5], [1]), _group([5], [4])]),
        ],
    }
    assert _matcher()(p1, {}) is True and iter8(p1, {}) is False

    # Iter 8 fires on iter-220 territory; this matcher rejects.
    p2 = {"pair_analyses": [_pair([_group([3], [0]), _group([3], [0])])]}
    assert iter8(p2, {}) is True and _matcher()(p2, {}) is False


def test_strict_refinement_of_iter_218_nonidentity_per_group() -> None:
    iter218 = CONDITION_REGISTRY["singleton_recolor_nonidentity_per_group"]

    # This matcher fires => iter 218 fires.
    p1 = {
        "pair_analyses": [
            _pair([_group([3], [0]), _group([3], [7])]),
            _pair([_group([5], [1]), _group([5], [4])]),
        ],
    }
    assert _matcher()(p1, {}) is True and iter218(p1, {}) is True

    # Iter 218 fires (iter 220 cell); this matcher rejects.
    p2 = {"pair_analyses": [_pair([_group([3], [0]), _group([3], [0])])]}
    assert iter218(p2, {}) is True and _matcher()(p2, {}) is False


def test_strict_mutual_exclusion_with_iter_220_both_anchored() -> None:
    iter220 = CONDITION_REGISTRY["singleton_recolor_nonidentity"]

    # This matcher fires; iter 220 rejects.
    p1 = {
        "pair_analyses": [
            _pair([_group([3], [0]), _group([3], [7])]),
            _pair([_group([5], [1]), _group([5], [4])]),
        ],
    }
    assert _matcher()(p1, {}) is True and iter220(p1, {}) is False

    # Iter 220 fires; this matcher rejects.
    p2 = {"pair_analyses": [_pair([_group([3], [0]), _group([3], [0])])]}
    assert iter220(p2, {}) is True and _matcher()(p2, {}) is False


def test_strict_mutual_exclusion_with_iter_221_input_anchored() -> None:
    iter221 = CONDITION_REGISTRY[
        "singleton_recolor_nonidentity_input_anchored"
    ]

    # This matcher fires; iter 221 rejects.
    p1 = {
        "pair_analyses": [
            _pair([_group([3], [0]), _group([3], [7])]),
            _pair([_group([5], [1]), _group([5], [4])]),
        ],
    }
    assert _matcher()(p1, {}) is True and iter221(p1, {}) is False

    # Iter 221 fires; this matcher rejects (|observed_input| > 1
    # fails).
    p2 = {"pair_analyses": [_pair([_group([3], [0]), _group([3], [7])])]}
    assert iter221(p2, {}) is True and _matcher()(p2, {}) is False


def test_strict_mutual_exclusion_with_iter_222_output_anchored() -> None:
    iter222 = CONDITION_REGISTRY[
        "singleton_recolor_nonidentity_output_anchored"
    ]

    # This matcher fires; iter 222 rejects.
    p1 = {
        "pair_analyses": [
            _pair([_group([3], [0]), _group([3], [7])]),
            _pair([_group([5], [1]), _group([5], [4])]),
        ],
    }
    assert _matcher()(p1, {}) is True and iter222(p1, {}) is False

    # Iter 222 fires; this matcher rejects (|observed_output| > 1
    # fails).
    p2 = {"pair_analyses": [_pair([_group([3], [0]), _group([7], [0])])]}
    assert iter222(p2, {}) is True and _matcher()(p2, {}) is False


def test_strict_mutual_exclusion_with_iter_219_identity() -> None:
    iter219 = CONDITION_REGISTRY["singleton_recolor_identity"]

    # This matcher fires; iter 219 rejects.
    p1 = {
        "pair_analyses": [
            _pair([_group([3], [0]), _group([3], [7])]),
            _pair([_group([5], [1]), _group([5], [4])]),
        ],
    }
    assert _matcher()(p1, {}) is True and iter219(p1, {}) is False

    # Iter 219 fires; this matcher rejects.
    p2 = {"pair_analyses": [_pair([_group([3], [3]), _group([3], [3])])]}
    assert iter219(p2, {}) is True and _matcher()(p2, {}) is False


def test_strict_mutual_exclusion_with_iter_217_identity_per_group() -> None:
    iter217 = CONDITION_REGISTRY["singleton_recolor_identity_per_group"]

    # This matcher fires; iter 217 rejects.
    p1 = {
        "pair_analyses": [
            _pair([_group([3], [0]), _group([3], [7])]),
            _pair([_group([5], [1]), _group([5], [4])]),
        ],
    }
    assert _matcher()(p1, {}) is True and iter217(p1, {}) is False

    # Iter 217 fires; this matcher rejects.
    p2 = {"pair_analyses": [_pair([_group([3], [3]), _group([5], [5])])]}
    assert iter217(p2, {}) is True and _matcher()(p2, {}) is False


def test_strict_mutual_exclusion_with_iter_216_both_anchored() -> None:
    iter216 = CONDITION_REGISTRY["singleton_recolor"]

    # This matcher fires; iter 216 rejects.
    p1 = {
        "pair_analyses": [
            _pair([_group([3], [0]), _group([3], [7])]),
            _pair([_group([5], [1]), _group([5], [4])]),
        ],
    }
    assert _matcher()(p1, {}) is True and iter216(p1, {}) is False

    # Iter 216 fires (cross-group identity on both sides; allows C ==
    # K); this matcher rejects.
    p2 = {"pair_analyses": [_pair([_group([3], [3]), _group([3], [3])])]}
    assert iter216(p2, {}) is True and _matcher()(p2, {}) is False


def test_strict_refinement_of_iter_215_singleton_recolor_per_group() -> None:
    iter215 = CONDITION_REGISTRY["singleton_recolor_per_group"]

    # This matcher fires => iter 215 fires.
    p1 = {
        "pair_analyses": [
            _pair([_group([3], [0]), _group([3], [7])]),
            _pair([_group([5], [1]), _group([5], [4])]),
        ],
    }
    assert _matcher()(p1, {}) is True and iter215(p1, {}) is True

    # Iter 215 fires (per-group |ic| == |oc| == 1); this matcher
    # rejects on the per-group ic == oc cell.
    p2 = {"pair_analyses": [_pair([_group([3], [0]), _group([3], [3])])]}
    assert iter215(p2, {}) is True and _matcher()(p2, {}) is False


def test_strict_mutual_exclusion_with_iter_14_input_color_uniform() -> None:
    iter14 = CONDITION_REGISTRY["input_color_uniform"]

    # This matcher fires; iter 14 rejects.
    p1 = {
        "pair_analyses": [
            _pair([_group([3], [0]), _group([3], [7])]),
            _pair([_group([5], [1]), _group([5], [4])]),
        ],
    }
    assert _matcher()(p1, {}) is True and iter14(p1, {}) is False

    # Iter 14 fires (input globally uniform); this matcher rejects.
    p2 = {"pair_analyses": [_pair([_group([3], [0]), _group([3], [7])])]}
    assert iter14(p2, {}) is True and _matcher()(p2, {}) is False


def test_strict_mutual_exclusion_with_iter_18_output_color_uniform() -> None:
    iter18 = CONDITION_REGISTRY["output_color_uniform"]

    # This matcher fires; iter 18 rejects.
    p1 = {
        "pair_analyses": [
            _pair([_group([3], [0]), _group([3], [7])]),
            _pair([_group([5], [1]), _group([5], [4])]),
        ],
    }
    assert _matcher()(p1, {}) is True and iter18(p1, {}) is False

    # Iter 18 fires (output globally uniform); this matcher rejects.
    p2 = {"pair_analyses": [_pair([_group([3], [0]), _group([5], [0])])]}
    assert iter18(p2, {}) is True and _matcher()(p2, {}) is False


def test_mutual_exclusion_with_identity_transformation() -> None:
    ident = CONDITION_REGISTRY["identity_transformation"]
    p = {"pair_analyses": [_pair([], num_groups=0, total_changes=0)]}
    assert ident(p, {}) is True and _matcher()(p, {}) is False


def test_strict_implication_of_iter_213_consistent_color_mapping_per_group() -> None:
    iter213 = CONDITION_REGISTRY["consistent_color_mapping_per_group"]

    # This matcher fires => iter 213 fires (per-group |oc| == 1 forces
    # the per-group output cross-product to be function-shaped
    # trivially).
    p1 = {
        "pair_analyses": [
            _pair([_group([3], [0]), _group([3], [7])]),
            _pair([_group([5], [1]), _group([5], [4])]),
        ],
    }
    assert _matcher()(p1, {}) is True and iter213(p1, {}) is True

    # Iter 213 fires with per-group |ic| > 1; this matcher rejects.
    p2 = {"pair_analyses": [_pair([_group([3, 4], [0]), _group([3, 4], [7])])]}
    assert iter213(p2, {}) is True and _matcher()(p2, {}) is False


def test_strict_implication_of_iter_214_input_color_uniform_per_group() -> None:
    iter214 = CONDITION_REGISTRY["input_color_uniform_per_group"]

    # This matcher fires => iter 214 fires.
    p1 = {
        "pair_analyses": [
            _pair([_group([3], [0]), _group([3], [7])]),
            _pair([_group([5], [1]), _group([5], [4])]),
        ],
    }
    assert _matcher()(p1, {}) is True and iter214(p1, {}) is True

    # Iter 214 fires with per-group |oc| > 1; this matcher rejects.
    p2 = {"pair_analyses": [_pair([_group([3], [0, 4]), _group([3], [7, 1])])]}
    assert iter214(p2, {}) is True and _matcher()(p2, {}) is False


def test_strict_implication_of_iter_203_disjoint_per_group() -> None:
    iter203 = CONDITION_REGISTRY[
        "output_colors_disjoint_from_input_colors_per_group"
    ]

    # This matcher fires => iter 203 fires.
    p1 = {
        "pair_analyses": [
            _pair([_group([3], [0]), _group([3], [7])]),
            _pair([_group([5], [1]), _group([5], [4])]),
        ],
    }
    assert _matcher()(p1, {}) is True and iter203(p1, {}) is True

    # Iter 203 fires with multi-element disjoint; this matcher rejects.
    p2 = {"pair_analyses": [_pair([_group([3, 4], [0, 1])])]}
    assert iter203(p2, {}) is True and _matcher()(p2, {}) is False


def test_strict_mutual_exclusion_with_iter_201_set_equality_per_group() -> None:
    iter201 = CONDITION_REGISTRY[
        "output_colors_equals_input_colors_per_group"
    ]

    # This matcher fires; iter 201 rejects.
    p1 = {
        "pair_analyses": [
            _pair([_group([3], [0]), _group([3], [7])]),
            _pair([_group([5], [1]), _group([5], [4])]),
        ],
    }
    assert _matcher()(p1, {}) is True and iter201(p1, {}) is False

    # Iter 201 fires (per-group ic == oc); this matcher rejects.
    p2 = {"pair_analyses": [_pair([_group([3], [3])])]}
    assert iter201(p2, {}) is True and _matcher()(p2, {}) is False


def test_strict_implication_of_iter_197_at_K_prod_eq_1() -> None:
    iter197 = CONDITION_REGISTRY[
        "change_color_mapping_count_per_group_constant_across_pairs"
    ]

    # This matcher fires => iter 197 fires at K_prod == 1.
    p1 = {
        "pair_analyses": [
            _pair([_group([3], [0]), _group([3], [7])]),
            _pair([_group([5], [1]), _group([5], [4])]),
        ],
    }
    assert _matcher()(p1, {}) is True and iter197(p1, {}) is True

    # Iter 197 fires (constant K_prod==1 across pairs) on iter 220
    # territory; this matcher rejects.
    p2 = {
        "pair_analyses": [
            _pair([_group([3], [0])]),
            _pair([_group([3], [0])]),
        ],
    }
    assert iter197(p2, {}) is True and _matcher()(p2, {}) is False


def test_recognized_conditions_includes_matcher_on_universal_within_pair_non_function_shape() -> None:
    # On the universal-pair within-pair non-function-shape sub-cell of
    # iter 227, this matcher FIRES. Iter 227 must co-fire (strict
    # refinement). Iter 226 must REJECT (within-pair function-shape
    # demanded). Iter 225 must co-fire. Iter 224 must REJECT. Iter 8
    # must REJECT (global function-shape fails). Iter 223 must
    # co-fire.
    from agent.conditions import recognized_conditions
    patterns = {
        "pair_analyses": [
            _pair([_group([3], [0]), _group([3], [7])]),
            _pair([_group([5], [1]), _group([5], [4])]),
        ],
    }
    fired = recognized_conditions(patterns)
    assert MATCHER_NAME in fired, (
        f"{MATCHER_NAME!r} did not fire on the universal-pair within-"
        f"pair non-function-shape sub-cell of iter 227; got {fired!r}"
    )
    assert (
        "singleton_recolor_nonidentity_unanchored_non_function_shaped_"
        "within_pair_non_function_shaped"
        in fired
    ), (
        "iter 227 regression: must co-fire on this matcher's "
        f"territory; got {fired!r}"
    )
    assert (
        "singleton_recolor_nonidentity_unanchored_non_function_shaped"
        in fired
    ), (
        "iter 225 regression: must co-fire on this matcher's "
        f"territory; got {fired!r}"
    )
    assert "singleton_recolor_nonidentity_unanchored" in fired, (
        "iter 223 regression: must co-fire on this matcher's "
        f"territory; got {fired!r}"
    )
    assert (
        "singleton_recolor_nonidentity_unanchored_non_function_shaped_"
        "within_pair_function_shaped"
        not in fired
    ), (
        "iter 226 expectation: within-pair function-shape matcher "
        f"must NOT fire on this fixture; got {fired!r}"
    )
    assert (
        "singleton_recolor_nonidentity_unanchored_function_shaped"
        not in fired
    ), (
        "iter 224 expectation: function-shape matcher must NOT fire "
        f"(global non-function-shape); got {fired!r}"
    )
    assert "consistent_color_mapping" not in fired, (
        "iter 8 expectation: must NOT fire on the global non-function-"
        f"shape fixture; got {fired!r}"
    )


def test_recognized_conditions_excludes_on_mixed_shape_sub_cell() -> None:
    # The companion mixed-shape sub-cell of iter 227 (some pair within-
    # pair non-function-shape AND some pair within-pair function-
    # shape) is iter 227 territory. Iter 225 / iter 227 fire; iter 226
    # rejects; this matcher must NOT fire.
    from agent.conditions import recognized_conditions
    patterns = {
        "pair_analyses": [
            _pair([_group([3], [0]), _group([3], [7])]),
            _pair([_group([3], [0]), _group([5], [4])]),
        ],
    }
    fired = recognized_conditions(patterns)
    assert MATCHER_NAME not in fired, (
        f"{MATCHER_NAME!r} should NOT fire on the mixed-shape sub-"
        f"cell of iter 227; got {fired!r}"
    )
    # No regression on iter 227 / 225 / 223.
    assert (
        "singleton_recolor_nonidentity_unanchored_non_function_shaped_"
        "within_pair_non_function_shaped"
        in fired
    )
    assert (
        "singleton_recolor_nonidentity_unanchored_non_function_shaped"
        in fired
    )
    assert "singleton_recolor_nonidentity_unanchored" in fired
    # Iter 226 must reject the mixed-shape fixture (pair 1 within-
    # pair non-function-shape disqualifies iter 226's universal claim
    # on within-pair function-shape).
    assert (
        "singleton_recolor_nonidentity_unanchored_non_function_shaped_"
        "within_pair_function_shaped"
        not in fired
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
