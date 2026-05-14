"""
tests/test_palette_shift_constant_across_pairs.py -- exercise the
iter-194 matcher
``agent.conditions.palette_shift_constant_across_pairs``.

Pins the matcher's contract per
``agent/conditions/palette_shift_constant_across_pairs.py`` docstring:
there exists a single integer ``k`` such that, on every pair,
``sorted(set(output_palette)) == [v + k for v in sorted(set(input_
palette))]``. First entry on the **colour-translation** sub-axis of
the whole-grid palette axis (iters 184 / 185 / 186 / 187 named set-
containment direction per pair; iters 188 / 189 / 185 named
cardinality direction per pair; iters 190 / 191 / 192 named cross-
pair magnitude constancy on |Δ| / |∩| / |∪|; this matcher names the
**linear-arithmetic translation** ``k`` between the sorted palette
lists per pair, with constancy of ``k`` across pairs).

Runs without pytest:

    python tests/test_palette_shift_constant_across_pairs.py

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


MATCHER_NAME = "palette_shift_constant_across_pairs"


def _matcher():
    return CONDITION_REGISTRY[MATCHER_NAME]


def _pair(input_palette, output_palette, **overrides):
    """A pair_analysis shaped like ExtractPatternOperator's output
    (iter-184 schema, with the palette fields)."""
    base = {
        "input_height": 3,
        "input_width": 3,
        "output_height": 3,
        "output_width": 3,
        "size_match": True,
        "total_changes": 0,
        "num_groups": 0,
        "groups": [],
        "input_palette": list(input_palette),
        "output_palette": list(output_palette),
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

def test_returns_true_on_single_pair_zero_shift() -> None:
    # Single pair with palette equality: k == 0 anchors trivially.
    patterns = {"pair_analyses": [_pair([0, 1, 2], [0, 1, 2])]}
    assert _matcher()(patterns, {}) is True


def test_returns_true_on_single_pair_positive_shift() -> None:
    # Single pair with shift k == 2: {1, 2, 3} → {3, 4, 5}.
    patterns = {"pair_analyses": [_pair([1, 2, 3], [3, 4, 5])]}
    assert _matcher()(patterns, {}) is True


def test_returns_true_on_single_pair_negative_shift() -> None:
    # Single pair with shift k == -1: {2, 3, 4} → {1, 2, 3}.
    patterns = {"pair_analyses": [_pair([2, 3, 4], [1, 2, 3])]}
    assert _matcher()(patterns, {}) is True


def test_returns_true_on_two_pairs_same_shift_k1() -> None:
    # Two pairs each with k == 1: {0, 1} → {1, 2}, {3, 4, 5} → {4, 5, 6}.
    patterns = {
        "pair_analyses": [
            _pair([0, 1], [1, 2]),
            _pair([3, 4, 5], [4, 5, 6]),
        ],
    }
    assert _matcher()(patterns, {}) is True


def test_returns_true_on_three_pairs_same_shift_k2() -> None:
    # Three pairs each with k == 2 (the canonical "increment by 2" case).
    patterns = {
        "pair_analyses": [
            _pair([0, 1, 2], [2, 3, 4]),
            _pair([5, 6], [7, 8]),
            _pair([1], [3]),
        ],
    }
    assert _matcher()(patterns, {}) is True


def test_returns_true_on_two_pairs_zero_shift() -> None:
    # Both pairs have palette equality: iter 185 ⇒ this matcher with
    # canonical k == 0.
    patterns = {
        "pair_analyses": [
            _pair([0, 1, 2], [0, 1, 2]),
            _pair([3, 4], [3, 4]),
        ],
    }
    assert _matcher()(patterns, {}) is True


def test_returns_true_with_duplicates_in_palettes() -> None:
    # Shift is defined on sorted-unique. Duplicates must not affect the
    # verdict (the matcher re-derives via sorted(set(...)) for
    # robustness against a future extractor regression).
    patterns = {
        "pair_analyses": [
            _pair([0, 0, 1, 1, 2], [2, 2, 3, 3, 4]),  # k == 2
            _pair([5, 5, 6], [7, 7, 8]),               # k == 2
        ],
    }
    assert _matcher()(patterns, {}) is True


def test_returns_true_on_one_non_empty_one_empty_pair() -> None:
    # Empty-empty pair contributes no constraint to k. The non-empty
    # pair anchors k. The matcher fires.
    patterns = {
        "pair_analyses": [
            _pair([0, 1], [2, 3]),  # anchors k == 2
            _pair([], []),          # vacuous
        ],
    }
    assert _matcher()(patterns, {}) is True


def test_returns_true_on_disjoint_constant_shift() -> None:
    # Disjoint palettes per pair (iter 186) AND same cardinality AND
    # constant shift: e.g. {0, 1, 2} → {5, 6, 7} on every pair (k == 5).
    patterns = {
        "pair_analyses": [
            _pair([0, 1, 2], [5, 6, 7]),
            _pair([3, 4], [8, 9]),
        ],
    }
    assert _matcher()(patterns, {}) is True


# ──────────────────────────────────────────────────────────────────────────
# Negative cases.
# ──────────────────────────────────────────────────────────────────────────

def test_returns_false_when_shift_undefined_within_pair() -> None:
    # A single pair where sorted output is NOT a constant shift of
    # sorted input. e.g. {0, 1, 2} → {0, 2, 4} -- shifts 0, 1, 2.
    patterns = {"pair_analyses": [_pair([0, 1, 2], [0, 2, 4])]}
    assert _matcher()(patterns, {}) is False


def test_returns_false_when_shift_varies_across_pairs() -> None:
    # Pair 0: k == 1. Pair 1: k == 2. Not constant.
    patterns = {
        "pair_analyses": [
            _pair([0, 1], [1, 2]),       # k = 1
            _pair([3, 4], [5, 6]),       # k = 2
        ],
    }
    assert _matcher()(patterns, {}) is False


def test_returns_false_on_cardinality_mismatch_within_pair() -> None:
    # If |input| != |output|, the shift is undefined for that pair --
    # fail-closed.
    patterns = {"pair_analyses": [_pair([0, 1, 2], [3, 4])]}
    assert _matcher()(patterns, {}) is False


def test_returns_false_on_cardinality_mismatch_in_later_pair() -> None:
    # First pair anchors k. Second pair has |input| != |output| -- the
    # shift is undefined there; the matcher must fail-closed, not
    # silently skip the bad pair.
    patterns = {
        "pair_analyses": [
            _pair([0, 1], [2, 3]),
            _pair([4, 5, 6], [7, 8]),
        ],
    }
    assert _matcher()(patterns, {}) is False


def test_returns_false_on_all_empty_pairs() -> None:
    # No pair anchors k. Universal-over-pairs claim is vacuous, but
    # the name promises a non-trivial shift recognition. Fail-closed.
    patterns = {
        "pair_analyses": [
            _pair([], []),
            _pair([], []),
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
            _pair([0, 1], [2, 3]),
            "not-a-dict",
            _pair([4, 5], [6, 7]),
        ],
    }
    assert _matcher()(patterns, {}) is False


# ──────────────────────────────────────────────────────────────────────────
# Strict-type-gate cases.
# ──────────────────────────────────────────────────────────────────────────

def test_returns_false_when_input_palette_missing() -> None:
    analysis = _pair([0, 1], [2, 3])
    del analysis["input_palette"]
    patterns = {"pair_analyses": [analysis]}
    assert _matcher()(patterns, {}) is False


def test_returns_false_when_output_palette_missing() -> None:
    analysis = _pair([0, 1], [2, 3])
    del analysis["output_palette"]
    patterns = {"pair_analyses": [analysis]}
    assert _matcher()(patterns, {}) is False


def test_returns_false_when_input_palette_is_not_list() -> None:
    for bad in (None, 42, "oops", {"a": 1}, (0, 1), True, {0, 1}):
        analysis = _pair([0, 1], [2, 3])
        analysis["input_palette"] = bad
        patterns = {"pair_analyses": [analysis]}
        assert _matcher()(patterns, {}) is False, (
            f"input_palette={bad!r} should not fire"
        )


def test_returns_false_when_output_palette_is_not_list() -> None:
    for bad in (None, 42, "oops", {"a": 1}, (0, 1), True, {0, 1}):
        analysis = _pair([0, 1], [2, 3])
        analysis["output_palette"] = bad
        patterns = {"pair_analyses": [analysis]}
        assert _matcher()(patterns, {}) is False, (
            f"output_palette={bad!r} should not fire"
        )


def test_returns_false_when_input_palette_contains_bool() -> None:
    analysis = _pair([0, 1], [2, 3])
    analysis["input_palette"] = [0, True]
    patterns = {"pair_analyses": [analysis]}
    assert _matcher()(patterns, {}) is False


def test_returns_false_when_output_palette_contains_bool() -> None:
    analysis = _pair([0, 1], [2, 3])
    analysis["output_palette"] = [False, 3]
    patterns = {"pair_analyses": [analysis]}
    assert _matcher()(patterns, {}) is False


def test_returns_false_when_palette_contains_non_int() -> None:
    analysis = _pair([0, 1], [2, 3])
    analysis["input_palette"] = [0, "1"]
    patterns = {"pair_analyses": [analysis]}
    assert _matcher()(patterns, {}) is False

    analysis2 = _pair([0, 1], [2, 3])
    analysis2["output_palette"] = [0.0]
    patterns2 = {"pair_analyses": [analysis2]}
    assert _matcher()(patterns2, {}) is False


def test_returns_false_when_second_pair_has_malformed_palette() -> None:
    bad = _pair([3, 4], [5, 6])
    bad["input_palette"] = None
    patterns = {"pair_analyses": [_pair([0, 1], [2, 3]), bad]}
    assert _matcher()(patterns, {}) is False


# ──────────────────────────────────────────────────────────────────────────
# Behavioural-contract cases.
# ──────────────────────────────────────────────────────────────────────────

def test_is_side_effect_free_on_inputs() -> None:
    patterns = {
        "pair_analyses": [
            _pair([0, 1], [2, 3]),
            _pair([4, 5], [6, 7]),
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
            _pair([0, 1], [2, 3]),
            _pair([4, 5], [6, 7]),
        ],
    }
    results = [_matcher()(patterns, {}) for _ in range(5)]
    assert len(set(results)) == 1, f"non-deterministic outputs: {results}"


def test_returned_value_is_boolean_not_truthy() -> None:
    # recognized_conditions filters on ``match(...) is True`` exactly,
    # so the matcher must return literal Booleans.
    out_true = _matcher()(
        {"pair_analyses": [_pair([0, 1], [2, 3]), _pair([4, 5], [6, 7])]},
        {},
    )
    out_false = _matcher()(
        {"pair_analyses": [_pair([0, 1], [2, 3]), _pair([4, 5], [4, 5])]},
        {},
    )
    assert out_true is True, f"expected literal True, got {out_true!r}"
    assert out_false is False, f"expected literal False, got {out_false!r}"


def test_ignores_per_group_color_lists() -> None:
    # The matcher reads ONLY ``input_palette`` / ``output_palette``.
    # Per-group ``input_colors`` / ``output_colors`` on change cells
    # are a different axis -- the matcher must ignore them.
    p0 = _pair(
        [0, 1, 2], [2, 3, 4],
        groups=[{
            "input_colors": [9, 9],  # not in either whole-grid palette
            "output_colors": [8, 8],
            "positions": [(0, 0)],
            "top_row": 0, "top_col": 0,
            "cell_count": 1,
        }],
        num_groups=1, total_changes=1,
    )
    p1 = _pair(
        [5, 6], [7, 8],
        groups=[{
            "input_colors": [9, 9],
            "output_colors": [8, 8],
            "positions": [(0, 0)],
            "top_row": 0, "top_col": 0,
            "cell_count": 1,
        }],
        num_groups=1, total_changes=1,
    )
    patterns = {"pair_analyses": [p0, p1]}
    assert _matcher()(patterns, {}) is True


def test_ignores_dimensional_fields() -> None:
    # Dimensional fields are orthogonal -- arbitrary dim combinations
    # must not affect the matcher's verdict.
    p0 = _pair(
        [0, 1, 2], [2, 3, 4],
        input_height=7, input_width=9, output_height=2, output_width=3,
        size_match=False,
    )
    p1 = _pair(
        [5, 6], [7, 8],
        input_height=1, input_width=1, output_height=8, output_width=8,
        size_match=False,
    )
    patterns = {"pair_analyses": [p0, p1]}
    assert _matcher()(patterns, {}) is True


# ──────────────────────────────────────────────────────────────────────────
# Orthogonality / co-fire matrix against the palette-axis siblings.
# ──────────────────────────────────────────────────────────────────────────

def test_identity_strictly_implies_this_matcher() -> None:
    # Identity has output palette equal to input palette per pair, so
    # k == 0 per pair, constant. Iter 13 ⇒ this matcher.
    identity = CONDITION_REGISTRY["identity_transformation"]
    patterns = {
        "grid_size_preserved": True,
        "pair_analyses": [
            _pair([0, 1, 2], [0, 1, 2]),
            _pair([3, 4], [3, 4]),
        ],
    }
    assert identity(patterns, {}) is True
    assert _matcher()(patterns, {}) is True


def test_iter185_strictly_implies_this_matcher() -> None:
    # Iter 185 (palette equality) ⇒ k == 0 on every pair, constant.
    # Strict implication: iter 185 ⇒ this matcher.
    iter185 = CONDITION_REGISTRY["output_palette_equals_input"]
    patterns = {
        "pair_analyses": [
            _pair([0, 1, 2], [0, 1, 2]),
            _pair([3, 4, 5], [3, 4, 5]),
            _pair([6, 7], [6, 7]),
        ],
    }
    assert iter185(patterns, {}) is True
    assert _matcher()(patterns, {}) is True


def test_this_matcher_fires_without_iter185() -> None:
    # The reverse of the previous test does NOT hold: this matcher
    # fires on any constant non-zero k, not only on k == 0. Iter 185
    # fires only on k == 0.
    iter185 = CONDITION_REGISTRY["output_palette_equals_input"]
    patterns = {
        "pair_analyses": [
            _pair([0, 1], [2, 3]),
            _pair([4, 5], [6, 7]),
        ],
    }
    assert iter185(patterns, {}) is False
    assert _matcher()(patterns, {}) is True


def test_mutually_exclusive_with_iter188_strict_expansion() -> None:
    # Iter 188 (strict expansion) requires |output| > |input| per pair
    # -- different cardinality. This matcher requires |output| ==
    # |input| per pair. MUTUALLY EXCLUSIVE on iter-188 firing pairs.
    iter188 = CONDITION_REGISTRY[
        "output_palette_count_exceeds_input_palette_count"
    ]
    patterns = {
        "pair_analyses": [
            _pair([0, 1], [0, 1, 2]),
            _pair([3, 4], [3, 4, 5]),
        ],
    }
    assert iter188(patterns, {}) is True
    assert _matcher()(patterns, {}) is False


def test_mutually_exclusive_with_iter189_strict_erasure() -> None:
    # Mirror of the iter-188 case: |input| > |output| per pair.
    iter189 = CONDITION_REGISTRY[
        "input_palette_count_exceeds_output_palette_count"
    ]
    patterns = {
        "pair_analyses": [
            _pair([0, 1, 2], [0, 1]),
            _pair([3, 4, 5], [3, 4]),
        ],
    }
    assert iter189(patterns, {}) is True
    assert _matcher()(patterns, {}) is False


def test_can_co_fire_with_iter186_disjoint() -> None:
    # Iter 186 (disjoint per pair) AND same cardinality AND constant
    # shift k can co-fire: e.g. {0, 1} → {5, 6} (k == 5, disjoint)
    # on every pair.
    iter186 = CONDITION_REGISTRY["output_palette_disjoint_from_input"]
    patterns = {
        "pair_analyses": [
            _pair([0, 1], [5, 6]),       # disjoint, k == 5
            _pair([2, 3], [7, 8]),       # disjoint, k == 5
        ],
    }
    assert iter186(patterns, {}) is True
    assert _matcher()(patterns, {}) is True


def test_iter186_alone_when_disjoint_with_varying_shift() -> None:
    # Iter 186 fires (disjoint per pair) but shift varies (k != const).
    iter186 = CONDITION_REGISTRY["output_palette_disjoint_from_input"]
    patterns = {
        "pair_analyses": [
            _pair([0, 1], [5, 6]),       # disjoint, k == 5
            _pair([2, 3], [9, 8]),       # set form: {2,3} → {8,9}; k == 6
        ],
    }
    assert iter186(patterns, {}) is True
    assert _matcher()(patterns, {}) is False


def test_orthogonal_to_grid_size_preserved() -> None:
    # The whole-grid palette-shift axis is orthogonal to the per-pair
    # input==output dim axis (the four-cell 2x2 co-fire table).
    gsp = CONDITION_REGISTRY["grid_size_preserved"]

    # constant shift + preserved
    p1 = {
        "grid_size_preserved": True,
        "pair_analyses": [
            _pair([0, 1], [2, 3]),
            _pair([4, 5], [6, 7]),
        ],
    }
    assert _matcher()(p1, {}) is True and gsp(p1, {}) is True

    # constant shift + changed dimensions
    p2 = {
        "grid_size_preserved": False,
        "pair_analyses": [
            _pair([0, 1], [2, 3], output_height=6, output_width=6,
                  size_match=False),
            _pair([4, 5], [6, 7], output_height=6, output_width=6,
                  size_match=False),
        ],
    }
    assert _matcher()(p2, {}) is True and gsp(p2, {}) is False

    # not-constant shift + preserved
    p3 = {
        "grid_size_preserved": True,
        "pair_analyses": [
            _pair([0, 1], [2, 3]),       # k = 2
            _pair([4, 5], [7, 8]),       # k = 3
        ],
    }
    assert _matcher()(p3, {}) is False and gsp(p3, {}) is True

    # not-constant shift + changed
    p4 = {
        "grid_size_preserved": False,
        "pair_analyses": [
            _pair([0, 1], [2, 3], output_height=6, output_width=6,
                  size_match=False),
            _pair([4, 5], [7, 8], output_height=6, output_width=6,
                  size_match=False),
        ],
    }
    assert _matcher()(p4, {}) is False and gsp(p4, {}) is False


def test_orthogonal_to_input_color_uniform() -> None:
    # Iter 14 inspects change-cells' input-colour uniformity. The
    # whole-grid palette-shift axis is INDEPENDENT.
    icu = CONDITION_REGISTRY["input_color_uniform"]

    # this matcher fires AND icu fires
    p0 = _pair(
        [0, 5, 7], [2, 7, 9],          # k = 2 on sorted-unique
        groups=[{
            "input_colors": [7],
            "output_colors": [9],
            "positions": [(0, 0)],
            "top_row": 0, "top_col": 0,
            "cell_count": 1,
        }],
        num_groups=1, total_changes=1,
    )
    p1 = _pair(
        [0, 6, 7], [2, 8, 9],          # k = 2 on sorted-unique
        groups=[{
            "input_colors": [7],
            "output_colors": [9],
            "positions": [(0, 0)],
            "top_row": 0, "top_col": 0,
            "cell_count": 1,
        }],
        num_groups=1, total_changes=1,
    )
    p_both = {"pair_analyses": [p0, p1]}
    assert _matcher()(p_both, {}) is True and icu(p_both, {}) is True

    # this matcher fires but icu does NOT (no change cells)
    p_no_changes = {
        "pair_analyses": [
            _pair([0, 1], [2, 3]),
            _pair([4, 5], [6, 7]),
        ],
    }
    assert _matcher()(p_no_changes, {}) is True
    assert icu(p_no_changes, {}) is False


# ──────────────────────────────────────────────────────────────────────────
# recognized_conditions wiring.
# ──────────────────────────────────────────────────────────────────────────

def test_recognized_conditions_includes_matcher_on_constant_shift() -> None:
    from agent.conditions import recognized_conditions
    patterns = {
        "pair_analyses": [
            _pair([0, 1], [2, 3]),
            _pair([4, 5], [6, 7]),
        ],
    }
    fired = recognized_conditions(patterns)
    assert MATCHER_NAME in fired, (
        f"{MATCHER_NAME!r} did not fire on constant-k=2 patterns dict; "
        f"got {fired!r}"
    )


def test_recognized_conditions_excludes_on_varying_shift() -> None:
    from agent.conditions import recognized_conditions
    patterns = {
        "pair_analyses": [
            _pair([0, 1], [2, 3]),       # k = 2
            _pair([4, 5], [7, 8]),       # k = 3
        ],
    }
    fired = recognized_conditions(patterns)
    assert MATCHER_NAME not in fired, (
        f"{MATCHER_NAME!r} must NOT fire on varying-k patterns; got "
        f"{fired!r}"
    )


def test_recognized_conditions_fires_alongside_iter185_on_equality() -> None:
    # Iter 185 ⇒ this matcher (strict implication on k == 0).
    from agent.conditions import recognized_conditions
    patterns = {
        "pair_analyses": [
            _pair([0, 1, 2], [0, 1, 2]),
            _pair([3, 4], [3, 4]),
        ],
    }
    fired = recognized_conditions(patterns)
    assert "output_palette_equals_input" in fired
    assert MATCHER_NAME in fired, (
        f"{MATCHER_NAME!r} must fire on palette-equality (k==0 constant); "
        f"got {fired!r}"
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
