"""
tests/test_palette_shift_constant_across_groups_and_pairs.py --
exercise the iter-199 matcher
``agent.conditions.palette_shift_constant_across_groups_and_pairs``.

Pins the matcher's contract per
``agent/conditions/palette_shift_constant_across_groups_and_pairs.py``
docstring: strict cross-pair refinement of iter 198. The per-group
shift integer ``k_G`` must be bit-identical across every change
group of every pair (one global ``k`` shared by every group of every
pair). Iter 198 fires when k_P is constant within each pair (per-
pair k_P may differ across pairs); this matcher requires the global
k to be shared across every group of every pair.

Runs without pytest:

    python tests/test_palette_shift_constant_across_groups_and_pairs.py

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


MATCHER_NAME = "palette_shift_constant_across_groups_and_pairs"


def _matcher():
    return CONDITION_REGISTRY[MATCHER_NAME]


def _group(input_colors, output_colors, **overrides):
    """A change-group dict shaped like ``_analyze_pair``'s output."""
    base = {
        "input_colors": list(input_colors),
        "output_colors": list(output_colors),
        "positions": [(0, 0)],
        "top_row": 0,
        "top_col": 0,
        "cell_count": 1,
    }
    base.update(overrides)
    return base


def _pair(groups, **overrides):
    """A pair_analysis dict with a list of change groups."""
    base = {
        "input_height": 3,
        "input_width": 3,
        "output_height": 3,
        "output_width": 3,
        "size_match": True,
        "total_changes": sum(g.get("cell_count", 1) for g in groups),
        "num_groups": len(groups),
        "groups": list(groups),
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
# Positive cases — every group of every pair shares one global k.
# ──────────────────────────────────────────────────────────────────────────

def test_returns_true_on_single_pair_single_group_zero_shift() -> None:
    # One pair, one group, k == 0 (identity per group).
    patterns = {
        "pair_analyses": [
            _pair([_group([0, 1, 2], [0, 1, 2])]),
        ],
    }
    assert _matcher()(patterns, {}) is True


def test_returns_true_on_single_pair_single_group_positive_shift() -> None:
    # One pair, one group, k == 2.
    patterns = {
        "pair_analyses": [
            _pair([_group([1, 2, 3], [3, 4, 5])]),
        ],
    }
    assert _matcher()(patterns, {}) is True


def test_returns_true_on_single_pair_single_group_negative_shift() -> None:
    # One pair, one group, k == -1.
    patterns = {
        "pair_analyses": [
            _pair([_group([2, 3, 4], [1, 2, 3])]),
        ],
    }
    assert _matcher()(patterns, {}) is True


def test_returns_true_on_single_pair_two_groups_same_shift() -> None:
    # One pair, two groups, both with k == 2. The within-pair leg
    # iter 198 also passes; this matcher also fires because there's
    # only one pair and the per-pair k_P == 2 is trivially global.
    patterns = {
        "pair_analyses": [
            _pair([
                _group([0, 1], [2, 3]),
                _group([4, 5], [6, 7]),
            ]),
        ],
    }
    assert _matcher()(patterns, {}) is True


def test_returns_true_on_two_pairs_with_global_k() -> None:
    # Two pairs, every group across both pairs at k == 2. Iter 198
    # also fires (within-pair k_P == 2 on both pairs); this matcher
    # additionally pins the global k constancy.
    patterns = {
        "pair_analyses": [
            _pair([
                _group([0, 1], [2, 3]),
                _group([4], [6]),
            ]),
            _pair([
                _group([1, 2, 3], [3, 4, 5]),
            ]),
        ],
    }
    assert _matcher()(patterns, {}) is True


def test_returns_true_on_three_pairs_with_global_k() -> None:
    # Three pairs, every group at k == 1.
    patterns = {
        "pair_analyses": [
            _pair([_group([0, 1], [1, 2])]),
            _pair([_group([3], [4]), _group([5, 6], [6, 7])]),
            _pair([_group([8], [9])]),
        ],
    }
    assert _matcher()(patterns, {}) is True


def test_returns_true_on_global_zero_shift() -> None:
    # Every group's input equals its output -- global k == 0.
    patterns = {
        "pair_analyses": [
            _pair([_group([0, 1], [0, 1]), _group([4], [4])]),
            _pair([_group([2, 3], [2, 3])]),
        ],
    }
    assert _matcher()(patterns, {}) is True


def test_returns_true_on_global_negative_shift() -> None:
    # Every group's output equals its input shifted by -2.
    patterns = {
        "pair_analyses": [
            _pair([_group([2, 3], [0, 1]), _group([4, 5], [2, 3])]),
            _pair([_group([7], [5])]),
        ],
    }
    assert _matcher()(patterns, {}) is True


def test_returns_true_with_duplicates_in_per_group_colors() -> None:
    # Shift is defined on sorted-unique. Duplicates must not affect the
    # verdict (the matcher re-derives via sorted(set(...))).
    patterns = {
        "pair_analyses": [
            _pair([
                _group([0, 0, 1, 1, 2], [2, 2, 3, 3, 4]),  # k == 2
                _group([5, 5, 6], [7, 7, 8]),               # k == 2
            ]),
            _pair([_group([3, 3], [5, 5])]),                # k == 2
        ],
    }
    assert _matcher()(patterns, {}) is True


def test_returns_true_when_groups_have_different_cardinalities_but_same_k() -> None:
    # The per-group cardinality may differ across groups (and across
    # pairs), as long as the per-group shift coincides.
    patterns = {
        "pair_analyses": [
            _pair([
                _group([3], [5]),             # k = 2 (cardinality 1)
                _group([0, 1], [2, 3]),       # k = 2 (cardinality 2)
            ]),
            _pair([
                _group([4, 5, 6], [6, 7, 8]),  # k = 2 (cardinality 3)
            ]),
        ],
    }
    assert _matcher()(patterns, {}) is True


# ──────────────────────────────────────────────────────────────────────────
# Negative cases — per-pair k_P differs across pairs (iter 198 fires).
# ──────────────────────────────────────────────────────────────────────────

def test_returns_false_when_per_pair_k_differs_across_pairs() -> None:
    # The key distinction from iter 198: per-pair k_P is constant
    # within each pair, but k_P differs across pairs. Iter 198 fires;
    # this matcher rejects.
    patterns = {
        "pair_analyses": [
            _pair([
                _group([0, 1], [2, 3]),       # k = 2
                _group([4, 5], [6, 7]),       # k = 2
            ]),
            _pair([
                _group([0, 1], [5, 6]),       # k = 5
                _group([2], [7]),             # k = 5
            ]),
        ],
    }
    assert _matcher()(patterns, {}) is False


def test_returns_false_when_only_second_pair_has_different_k() -> None:
    # Pair 0 has every group at k = 2; pair 1 has every group at k = 3.
    patterns = {
        "pair_analyses": [
            _pair([_group([0, 1], [2, 3])]),       # k = 2
            _pair([_group([0, 1], [3, 4])]),       # k = 3
        ],
    }
    assert _matcher()(patterns, {}) is False


def test_returns_false_on_singleton_groups_with_differing_global_k() -> None:
    # Two pairs each with one singleton group, but the two singletons
    # disagree on the shift.
    patterns = {
        "pair_analyses": [
            _pair([_group([7], [9])]),       # k = 2
            _pair([_group([3], [4])]),       # k = 1
        ],
    }
    assert _matcher()(patterns, {}) is False


# ──────────────────────────────────────────────────────────────────────────
# Negative cases — per-group shift undefined / inconsistent within a pair.
# ──────────────────────────────────────────────────────────────────────────

def test_returns_false_when_within_pair_shifts_differ() -> None:
    # Pair 0 has group 0 at k == 2 and group 1 at k == 3 -- per-pair
    # constancy already fails. Reject.
    patterns = {
        "pair_analyses": [
            _pair([
                _group([0, 1], [2, 3]),       # k = 2
                _group([4, 5], [7, 8]),       # k = 3
            ]),
        ],
    }
    assert _matcher()(patterns, {}) is False


def test_returns_false_when_shift_undefined_within_a_group() -> None:
    # A single group where sorted output is not a uniform shift of
    # sorted input. {0, 1, 2} -> {0, 2, 4}: shifts 0, 1, 2.
    patterns = {
        "pair_analyses": [
            _pair([_group([0, 1, 2], [0, 2, 4])]),
        ],
    }
    assert _matcher()(patterns, {}) is False


def test_returns_false_on_cardinality_mismatch_within_a_group() -> None:
    # |input_colors| != |output_colors| within a group -- shift undefined.
    patterns = {
        "pair_analyses": [
            _pair([_group([0, 1, 2], [3, 4])]),
        ],
    }
    assert _matcher()(patterns, {}) is False


def test_returns_false_when_only_second_group_in_pair_violates() -> None:
    # First group anchors k_P; second group has the same cardinality
    # but a different shift. Must reject.
    patterns = {
        "pair_analyses": [
            _pair([
                _group([0, 1], [2, 3]),       # k = 2
                _group([0, 1], [3, 5]),       # not a uniform shift
            ]),
        ],
    }
    assert _matcher()(patterns, {}) is False


def test_returns_false_when_only_second_pair_within_pair_disagrees() -> None:
    # First pair is consistent (k = 2 on both groups); second pair's
    # groups disagree within the pair.
    patterns = {
        "pair_analyses": [
            _pair([
                _group([0, 1], [2, 3]),       # k = 2
                _group([4], [6]),             # k = 2
            ]),
            _pair([
                _group([0, 1], [2, 3]),       # k = 2
                _group([4], [9]),             # k = 5
            ]),
        ],
    }
    assert _matcher()(patterns, {}) is False


# ──────────────────────────────────────────────────────────────────────────
# Negative cases — empty / malformed / identity-territory.
# ──────────────────────────────────────────────────────────────────────────

def test_returns_false_on_no_groups_in_any_pair() -> None:
    # Identity-territory: every pair has zero change groups. Mirror of
    # iter 195 / 196 / 197 / 198 empty-groups rejection.
    patterns = {
        "pair_analyses": [
            _pair([]),
            _pair([]),
        ],
    }
    assert _matcher()(patterns, {}) is False


def test_returns_false_on_no_groups_in_first_pair() -> None:
    # Mixed: first pair has zero groups; second pair has constant shift.
    # The per-pair quantifier ranges over every pair, including the
    # zero-group one, which is fail-closed.
    patterns = {
        "pair_analyses": [
            _pair([]),
            _pair([_group([0, 1], [2, 3])]),
        ],
    }
    assert _matcher()(patterns, {}) is False


def test_returns_false_on_empty_pair_analyses() -> None:
    patterns = {"pair_analyses": []}
    assert _matcher()(patterns, {}) is False


def test_returns_false_on_missing_pair_analyses() -> None:
    patterns = {}
    assert _matcher()(patterns, {}) is False


def test_returns_false_on_non_list_pair_analyses() -> None:
    for bad in (None, 42, "oops", {"a": 1}, (), True):
        patterns = {"pair_analyses": bad}
        assert _matcher()(patterns, {}) is False, (
            f"pair_analyses={bad!r} should not fire"
        )


def test_returns_false_on_non_dict_patterns() -> None:
    assert _matcher()(None, {}) is False         # type: ignore[arg-type]
    assert _matcher()([], {}) is False           # type: ignore[arg-type]
    assert _matcher()("oops", {}) is False       # type: ignore[arg-type]
    assert _matcher()(42, {}) is False           # type: ignore[arg-type]


def test_returns_false_when_any_analysis_is_not_dict() -> None:
    patterns = {
        "pair_analyses": [
            _pair([_group([0, 1], [2, 3])]),
            "not-a-dict",
        ],
    }
    assert _matcher()(patterns, {}) is False


def test_returns_false_when_groups_is_not_list() -> None:
    for bad in (None, 42, "oops", {"a": 1}, (), True):
        patterns = {"pair_analyses": [{"groups": bad}]}
        assert _matcher()(patterns, {}) is False, (
            f"groups={bad!r} should not fire"
        )


def test_returns_false_when_any_group_is_not_dict() -> None:
    patterns = {
        "pair_analyses": [
            _pair([_group([0], [2])])
            | {"groups": [_group([0], [2]), "not-a-group"]},
        ],
    }
    assert _matcher()(patterns, {}) is False


# ──────────────────────────────────────────────────────────────────────────
# Strict-type-gate cases on per-group colour lists.
# ──────────────────────────────────────────────────────────────────────────

def test_returns_false_when_input_colors_missing() -> None:
    g = _group([0, 1], [2, 3])
    del g["input_colors"]
    patterns = {"pair_analyses": [_pair([g])]}
    assert _matcher()(patterns, {}) is False


def test_returns_false_when_output_colors_missing() -> None:
    g = _group([0, 1], [2, 3])
    del g["output_colors"]
    patterns = {"pair_analyses": [_pair([g])]}
    assert _matcher()(patterns, {}) is False


def test_returns_false_when_input_colors_is_not_list() -> None:
    for bad in (None, 42, "oops", {"a": 1}, (0, 1), True, {0, 1}):
        g = _group([0, 1], [2, 3])
        g["input_colors"] = bad
        patterns = {"pair_analyses": [_pair([g])]}
        assert _matcher()(patterns, {}) is False, (
            f"input_colors={bad!r} should not fire"
        )


def test_returns_false_when_output_colors_is_not_list() -> None:
    for bad in (None, 42, "oops", {"a": 1}, (0, 1), True, {0, 1}):
        g = _group([0, 1], [2, 3])
        g["output_colors"] = bad
        patterns = {"pair_analyses": [_pair([g])]}
        assert _matcher()(patterns, {}) is False, (
            f"output_colors={bad!r} should not fire"
        )


def test_returns_false_when_input_colors_is_empty() -> None:
    patterns = {"pair_analyses": [_pair([_group([], [2])])]}
    assert _matcher()(patterns, {}) is False


def test_returns_false_when_output_colors_is_empty() -> None:
    patterns = {"pair_analyses": [_pair([_group([0], [])])]}
    assert _matcher()(patterns, {}) is False


def test_returns_false_when_input_colors_contains_bool() -> None:
    g = _group([0, 1], [2, 3])
    g["input_colors"] = [0, True]
    patterns = {"pair_analyses": [_pair([g])]}
    assert _matcher()(patterns, {}) is False


def test_returns_false_when_output_colors_contains_bool() -> None:
    g = _group([0, 1], [2, 3])
    g["output_colors"] = [False, 3]
    patterns = {"pair_analyses": [_pair([g])]}
    assert _matcher()(patterns, {}) is False


def test_returns_false_when_colors_contain_non_int() -> None:
    g1 = _group([0, 1], [2, 3])
    g1["input_colors"] = [0, "1"]
    patterns1 = {"pair_analyses": [_pair([g1])]}
    assert _matcher()(patterns1, {}) is False

    g2 = _group([0, 1], [2, 3])
    g2["output_colors"] = [0.0]
    patterns2 = {"pair_analyses": [_pair([g2])]}
    assert _matcher()(patterns2, {}) is False


def test_returns_false_on_out_of_range_color() -> None:
    g = _group([0], [2])
    g["input_colors"] = [10]
    patterns = {"pair_analyses": [_pair([g])]}
    assert _matcher()(patterns, {}) is False

    g2 = _group([0], [2])
    g2["output_colors"] = [-1]
    patterns2 = {"pair_analyses": [_pair([g2])]}
    assert _matcher()(patterns2, {}) is False


# ──────────────────────────────────────────────────────────────────────────
# Behavioural-contract cases.
# ──────────────────────────────────────────────────────────────────────────

def test_is_side_effect_free_on_inputs() -> None:
    patterns = {
        "pair_analyses": [
            _pair([
                _group([0, 1], [2, 3]),
                _group([4], [6]),
            ]),
            _pair([_group([7], [9])]),
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
            _pair([_group([0, 1], [2, 3])]),
            _pair([_group([4, 5], [6, 7])]),
        ],
    }
    results = [_matcher()(patterns, {}) for _ in range(5)]
    assert len(set(results)) == 1, f"non-deterministic outputs: {results}"


def test_returned_value_is_boolean_not_truthy() -> None:
    # recognized_conditions filters on ``match(...) is True`` exactly,
    # so the matcher must return literal Booleans.
    out_true = _matcher()(
        {"pair_analyses": [_pair([_group([0, 1], [2, 3])])]},
        {},
    )
    out_false = _matcher()(
        {"pair_analyses": [
            _pair([_group([0, 1], [2, 3])]),       # k = 2
            _pair([_group([0, 1], [3, 4])]),       # k = 3
        ]},
        {},
    )
    assert out_true is True, f"expected literal True, got {out_true!r}"
    assert out_false is False, f"expected literal False, got {out_false!r}"


def test_ignores_whole_grid_palette_fields() -> None:
    # The matcher reads ONLY per-group ``input_colors`` /
    # ``output_colors``. Whole-grid ``input_palette`` / ``output_palette``
    # are a different axis -- the matcher must ignore them.
    p = _pair(
        [_group([0, 1], [2, 3]), _group([4], [6])],
        input_palette=[0, 1, 4, 9],
        output_palette=[2, 3, 6, 9],
    )
    patterns = {"pair_analyses": [p]}
    assert _matcher()(patterns, {}) is True


def test_ignores_dimensional_fields() -> None:
    # Dimensional fields are orthogonal -- arbitrary dim combinations
    # must not affect the matcher's verdict.
    p = _pair(
        [_group([0, 1], [2, 3]), _group([4], [6])],
        input_height=7, input_width=9, output_height=2, output_width=3,
        size_match=False,
    )
    patterns = {"pair_analyses": [p]}
    assert _matcher()(patterns, {}) is True


# ──────────────────────────────────────────────────────────────────────────
# Orthogonality / refinement matrix.
# ──────────────────────────────────────────────────────────────────────────

def test_this_matcher_strictly_implies_iter198() -> None:
    # Wherever this matcher fires, iter 198 also fires (a globally-
    # constant per-group shift is constant within every pair). Witness
    # this on a two-pair, multi-group task with global k = 2.
    iter198 = CONDITION_REGISTRY["palette_shift_constant_across_groups_per_pair"]
    patterns = {
        "pair_analyses": [
            _pair([_group([0, 1], [2, 3]), _group([4], [6])]),
            _pair([_group([5], [7]), _group([1, 2], [3, 4])]),
        ],
    }
    assert _matcher()(patterns, {}) is True
    assert iter198(patterns, {}) is True


def test_iter198_does_not_imply_this_matcher() -> None:
    # The strict-refinement witness: a task with per-pair k_P constant
    # within each pair but differing across pairs fires iter 198 and
    # rejects this matcher.
    iter198 = CONDITION_REGISTRY["palette_shift_constant_across_groups_per_pair"]
    patterns = {
        "pair_analyses": [
            _pair([
                _group([0, 1], [2, 3]),       # k_G = 2
                _group([4], [6]),             # k_G = 2
            ]),
            _pair([
                _group([0, 1], [5, 6]),       # k_G = 5
                _group([2], [7]),             # k_G = 5
            ]),
        ],
    }
    assert iter198(patterns, {}) is True
    assert _matcher()(patterns, {}) is False


def test_iter194_does_not_imply_this_matcher() -> None:
    # Iter 194 (whole-grid cross-pair shift) can fire while this
    # matcher rejects: whole-grid input_palette/output_palette can
    # share a constant shift while per-group shifts disagree (within
    # a pair or globally).
    iter194 = CONDITION_REGISTRY["palette_shift_constant_across_pairs"]
    p = _pair(
        [_group([0], [3]), _group([1], [2])],
        input_palette=[0, 1],
        output_palette=[2, 3],
    )
    patterns = {"pair_analyses": [p]}
    assert iter194(patterns, {}) is True
    assert _matcher()(patterns, {}) is False


def test_this_matcher_does_not_imply_iter194() -> None:
    # The reverse direction: per-group shifts can be globally constant
    # while whole-grid sorted palettes differ across pairs. Construct
    # a task where pair 0 has groups {0}->{2} and {1}->{3} (k=2 global,
    # whole-grid {0,1}->{2,3}), and pair 1 has groups {4}->{6} and
    # {5}->{7} (k=2 global, whole-grid {4,5}->{6,7}). Whole-grid
    # sorted-shift is k=2 on both pairs -- iter 194 also fires. So
    # construct a more delicate disagreement: pair 0 has groups
    # {0}->{2} (k=2), pair 1 has groups {3}->{5} (k=2) but
    # input_palette claims something non-shift. The simplest path:
    # the matcher reads only per-group colors and ignores the whole-
    # grid palette, so a per-group globally-constant shift can pair
    # with a deliberately mis-shaped whole-grid palette where iter
    # 194 rejects (palette cardinality mismatch).
    iter194 = CONDITION_REGISTRY["palette_shift_constant_across_pairs"]
    patterns = {
        "pair_analyses": [
            _pair(
                [_group([0], [2])],
                input_palette=[0, 1, 9],     # extra bg colour 9 keeps cardinality matched
                output_palette=[2, 3, 9],
            ),
            _pair(
                [_group([4], [6])],
                input_palette=[4, 5],        # cardinality 2 -- mismatch with pair 0's 3
                output_palette=[6, 7],
            ),
        ],
    }
    # Both pairs have per-group shift k=2; this matcher fires. Iter 194
    # has a per-pair shift k=2 on each pair (lengths 3 and 2 each
    # internally consistent); but those per-pair k's coincide at k=2
    # in this construction. To force iter 194 rejection, pick differing
    # whole-grid per-pair shifts:
    patterns = {
        "pair_analyses": [
            _pair(
                [_group([0], [2])],          # k_G = 2
                input_palette=[0, 1],
                output_palette=[2, 3],       # whole-grid shift = 2
            ),
            _pair(
                [_group([4], [6])],          # k_G = 2
                input_palette=[4, 5],
                output_palette=[7, 8],       # whole-grid shift = 3 (differs from pair 0's 2)
            ),
        ],
    }
    assert _matcher()(patterns, {}) is True
    assert iter194(patterns, {}) is False


def test_identity_does_not_co_fire_with_this_matcher() -> None:
    # iter 13 (identity_transformation) requires zero changes per pair
    # -- empty groups. This matcher rejects empty groups. MUTUALLY
    # EXCLUSIVE.
    identity = CONDITION_REGISTRY["identity_transformation"]
    patterns = {
        "grid_size_preserved": True,
        "pair_analyses": [
            {"size_match": True, "num_groups": 0, "groups": []},
            {"size_match": True, "num_groups": 0, "groups": []},
        ],
    }
    assert identity(patterns, {}) is True
    assert _matcher()(patterns, {}) is False


def test_co_fires_with_input_color_uniform_on_uniform_per_group() -> None:
    # iter 14 (input_color_uniform) pins every group to a single
    # input colour shared across all groups in all pairs. With single-
    # colour groups all having the same input colour AND a consistent
    # output mapping that yields a globally-constant per-group shift,
    # both matchers fire.
    icu = CONDITION_REGISTRY["input_color_uniform"]
    p = _pair([
        _group([3], [5], positions=[(0, 0)], top_row=0, top_col=0,
               cell_count=1),
        _group([3], [5], positions=[(1, 0)], top_row=1, top_col=0,
               cell_count=1),
    ])
    patterns = {"pair_analyses": [p]}
    assert icu(patterns, {}) is True
    assert _matcher()(patterns, {}) is True


def test_orthogonal_to_grid_size_preserved() -> None:
    gsp = CONDITION_REGISTRY["grid_size_preserved"]

    # this matcher fires AND gsp fires
    p1 = {
        "grid_size_preserved": True,
        "pair_analyses": [_pair([_group([0, 1], [2, 3])])],
    }
    assert _matcher()(p1, {}) is True and gsp(p1, {}) is True

    # this matcher fires AND gsp does NOT
    p2 = {
        "grid_size_preserved": False,
        "pair_analyses": [
            _pair([_group([0, 1], [2, 3])],
                  output_height=6, output_width=6, size_match=False),
        ],
    }
    assert _matcher()(p2, {}) is True and gsp(p2, {}) is False


# ──────────────────────────────────────────────────────────────────────────
# recognized_conditions wiring.
# ──────────────────────────────────────────────────────────────────────────

def test_recognized_conditions_includes_matcher_on_global_constant_shift() -> None:
    from agent.conditions import recognized_conditions
    patterns = {
        "pair_analyses": [
            _pair([_group([0, 1], [2, 3]), _group([4], [6])]),  # k = 2
            _pair([_group([1], [3])]),                            # k = 2
        ],
    }
    fired = recognized_conditions(patterns)
    assert MATCHER_NAME in fired, (
        f"{MATCHER_NAME!r} did not fire on globally-constant shift patterns; "
        f"got {fired!r}"
    )


def test_recognized_conditions_excludes_on_per_pair_k_difference() -> None:
    # Strict refinement of iter 198: iter 198 fires when within-pair
    # shifts agree (even if across-pair k_P differ); this matcher
    # rejects exactly those patterns.
    from agent.conditions import recognized_conditions
    patterns = {
        "pair_analyses": [
            _pair([_group([0, 1], [2, 3])]),       # k = 2
            _pair([_group([0, 1], [5, 6])]),       # k = 5
        ],
    }
    fired = recognized_conditions(patterns)
    assert (
        "palette_shift_constant_across_groups_per_pair" in fired
    ), "iter 198 should fire on per-pair-constant-but-across-pair-differing k"
    assert MATCHER_NAME not in fired, (
        f"{MATCHER_NAME!r} must NOT fire when per-pair k_P differs across "
        f"pairs; got {fired!r}"
    )


def test_recognized_conditions_co_fires_with_iter198_on_global_shift() -> None:
    # When this matcher fires, iter 198 must also fire (strict-
    # refinement direction).
    from agent.conditions import recognized_conditions
    patterns = {
        "pair_analyses": [
            _pair([_group([3], [5]), _group([1, 2], [3, 4])]),   # k = 2
            _pair([_group([7], [9])]),                             # k = 2
        ],
    }
    fired = recognized_conditions(patterns)
    assert "palette_shift_constant_across_groups_per_pair" in fired
    assert MATCHER_NAME in fired, (
        f"{MATCHER_NAME!r} must co-fire alongside iter 198 on globally-"
        f"constant shift; got {fired!r}"
    )


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
