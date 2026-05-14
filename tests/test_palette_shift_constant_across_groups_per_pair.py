"""
tests/test_palette_shift_constant_across_groups_per_pair.py --
exercise the iter-198 matcher
``agent.conditions.palette_shift_constant_across_groups_per_pair``.

Pins the matcher's contract per
``agent/conditions/palette_shift_constant_across_groups_per_pair.py``
docstring: per-pair-per-group projection of iter 194's whole-grid
colour-translation axis. The per-pair shift integer ``k_P`` must be
bit-identical across every change group in that pair; ``k_P`` may
vary across pairs (the across-pair constancy of this shift is named
by the future cross-pair matcher and is NOT a precondition here).

Runs without pytest:

    python tests/test_palette_shift_constant_across_groups_per_pair.py

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


MATCHER_NAME = "palette_shift_constant_across_groups_per_pair"


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
# Positive cases.
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
    # One pair, two groups, both with k == 2.
    patterns = {
        "pair_analyses": [
            _pair([
                _group([0, 1], [2, 3]),
                _group([4, 5], [6, 7]),
            ]),
        ],
    }
    assert _matcher()(patterns, {}) is True


def test_returns_true_on_two_pairs_each_with_constant_shift_same_k() -> None:
    # Two pairs, each with constant shift, and the per-pair k coincides.
    # This is the cell where this matcher AND iter 194 (whole-grid
    # cross-pair shift) both fire in the per-group projection sense.
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


def test_returns_true_on_two_pairs_with_DIFFERENT_per_pair_shifts() -> None:
    # The key distinction from iter 194: per-pair k may differ across
    # pairs. Pair 0 has k_P == 2 for every group; pair 1 has k_P == 5
    # for every group. Both pairs satisfy the per-pair, across-groups
    # claim; iter 194 (cross-pair whole-grid) would reject this.
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
    assert _matcher()(patterns, {}) is True


def test_returns_true_on_single_group_pair_singleton_constancy() -> None:
    # Singleton groups (cell_count == 1 with one input colour and one
    # output colour) trivially satisfy the per-group shift definition.
    patterns = {
        "pair_analyses": [
            _pair([
                _group([7], [9]),       # k = 2
                _group([3], [5]),       # k = 2
            ]),
        ],
    }
    assert _matcher()(patterns, {}) is True


def test_returns_true_with_duplicates_in_per_group_colors() -> None:
    # Shift is defined on sorted-unique. Duplicates must not affect the
    # verdict (the matcher re-derives via sorted(set(...)) for
    # robustness against a future extractor regression).
    patterns = {
        "pair_analyses": [
            _pair([
                _group([0, 0, 1, 1, 2], [2, 2, 3, 3, 4]),  # k == 2
                _group([5, 5, 6], [7, 7, 8]),               # k == 2
            ]),
        ],
    }
    assert _matcher()(patterns, {}) is True


def test_returns_true_when_groups_have_different_cardinalities_but_same_k() -> None:
    # The per-group cardinality may differ across groups within a pair
    # (group 0 spans 1 colour, group 1 spans 2 colours), as long as the
    # per-group shift coincides.
    patterns = {
        "pair_analyses": [
            _pair([
                _group([3], [5]),             # k = 2 (cardinality 1)
                _group([0, 1], [2, 3]),       # k = 2 (cardinality 2)
            ]),
        ],
    }
    assert _matcher()(patterns, {}) is True


# ──────────────────────────────────────────────────────────────────────────
# Negative cases — per-group shift undefined / inconsistent.
# ──────────────────────────────────────────────────────────────────────────

def test_returns_false_when_within_pair_shifts_differ() -> None:
    # Pair 0 has group 0 at k == 2 and group 1 at k == 3 -- per-pair
    # k_P does NOT exist. Reject.
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
    # but a different shift. Must reject even when first group is
    # well-formed.
    patterns = {
        "pair_analyses": [
            _pair([
                _group([0, 1], [2, 3]),       # k = 2
                _group([0, 1], [3, 5]),       # not a uniform shift (shifts 3 and 4)
            ]),
        ],
    }
    assert _matcher()(patterns, {}) is False


def test_returns_false_when_only_second_pair_violates() -> None:
    # First pair satisfies per-pair constancy; second pair has within-
    # pair shift inconsistency.
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
    # iter 195 / 196 / 197 empty-groups rejection.
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
    # A non-empty group always has at least one cell, so input_colors
    # has length >= 1. An empty list is an extractor contract
    # violation -- fail-closed.
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
            _pair([_group([4, 5], [9, 10] if False else [7, 8])]),  # k=3
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
        {"pair_analyses": [_pair([
            _group([0, 1], [2, 3]),
            _group([4, 5], [7, 8]),
        ])]},
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
# Orthogonality / co-fire matrix.
# ──────────────────────────────────────────────────────────────────────────

def test_iter194_does_not_imply_this_matcher() -> None:
    # Iter 194 (whole-grid cross-pair shift) can fire while this
    # matcher rejects: whole-grid input_palette/output_palette can
    # share a constant shift while per-group shifts within a pair
    # disagree. Construct: pair 0 has whole-grid {0,1} -> {2,3}
    # (whole shift k=2), but groups split as {0}->{2} (k=2) and
    # {1}->{3} (k=2) so the per-group shifts coincide. To force the
    # per-group disagreement, swap one group to {0}->{3} (k=3) and
    # the other to {1}->{2} (k=1): whole-grid palette is still
    # {0,1}->{2,3} (shift k=2), but per-group shifts are 3 and 1.
    iter194 = CONDITION_REGISTRY["palette_shift_constant_across_pairs"]
    p = _pair(
        [_group([0], [3]), _group([1], [2])],
        input_palette=[0, 1],
        output_palette=[2, 3],
    )
    patterns = {"pair_analyses": [p]}
    assert iter194(patterns, {}) is True
    assert _matcher()(patterns, {}) is False


def test_this_matcher_fires_without_iter194() -> None:
    # The reverse direction: per-pair shifts are constant within each
    # pair but differ across pairs (k_P = 2 on pair 0, k_P = 5 on
    # pair 1). Iter 194 requires whole-grid shift constant cross-pair
    # -- rejects when whole-grid shifts differ.
    iter194 = CONDITION_REGISTRY["palette_shift_constant_across_pairs"]
    patterns = {
        "pair_analyses": [
            _pair(
                [_group([0, 1], [2, 3]), _group([4], [6])],  # k = 2
                input_palette=[0, 1, 4],
                output_palette=[2, 3, 6],
            ),
            _pair(
                [_group([0, 1], [5, 6])],                    # k = 5
                input_palette=[0, 1],
                output_palette=[5, 6],
            ),
        ],
    }
    assert iter194(patterns, {}) is False
    assert _matcher()(patterns, {}) is True


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
    # input colour shared across all groups in all pairs. With a
    # consistent per-pair output mapping that yields a constant per-
    # group shift, both matchers fire.
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

def test_recognized_conditions_includes_matcher_on_constant_per_pair_shift() -> None:
    from agent.conditions import recognized_conditions
    patterns = {
        "pair_analyses": [
            _pair([_group([0, 1], [2, 3]), _group([4], [6])]),
            _pair([_group([1], [6])]),
        ],
    }
    fired = recognized_conditions(patterns)
    assert MATCHER_NAME in fired, (
        f"{MATCHER_NAME!r} did not fire on per-pair-constant shift patterns; "
        f"got {fired!r}"
    )


def test_recognized_conditions_excludes_on_within_pair_disagreement() -> None:
    from agent.conditions import recognized_conditions
    patterns = {
        "pair_analyses": [
            _pair([
                _group([0, 1], [2, 3]),       # k = 2
                _group([4, 5], [7, 8]),       # k = 3
            ]),
        ],
    }
    fired = recognized_conditions(patterns)
    assert MATCHER_NAME not in fired, (
        f"{MATCHER_NAME!r} must NOT fire when per-pair shifts disagree "
        f"across groups; got {fired!r}"
    )


def test_recognized_conditions_fires_alongside_iter195_on_compatible_input() -> None:
    # Iter 195 (change_input_color_count_per_group_constant_across_pairs)
    # pins per-group |input_colors| constancy cross-pair. With single-
    # colour groups (|input_colors| == 1 on every group) AND a
    # consistent per-pair shift, both fire.
    from agent.conditions import recognized_conditions
    patterns = {
        "pair_analyses": [
            _pair([_group([3], [5])]),       # k = 2
            _pair([_group([1], [6])]),       # k = 5 (per-pair k differs)
        ],
    }
    fired = recognized_conditions(patterns)
    assert (
        "change_input_color_count_per_group_constant_across_pairs"
        in fired
    )
    assert MATCHER_NAME in fired, (
        f"{MATCHER_NAME!r} must fire on single-colour-per-group with "
        f"per-pair shift constancy; got {fired!r}"
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
