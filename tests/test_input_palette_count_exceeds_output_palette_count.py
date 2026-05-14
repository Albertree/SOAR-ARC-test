"""
tests/test_input_palette_count_exceeds_output_palette_count.py --
exercise the iter-189 matcher
``agent.conditions.input_palette_count_exceeds_output_palette_count``
(new in this iter).

Pins the matcher's contract per
``agent/conditions/input_palette_count_exceeds_output_palette_count.py``
docstring: every pair satisfies ``len(set(input_palette)) >
len(set(output_palette))`` on a non-empty ``pair_analyses`` list with
both palettes shaped as lists of non-bool ints. The mirror ``<`` cell
of the cardinality-direction sub-axis opened by iter 188 (which named
the ``>`` cell); together with iter 185 (equality) the trio populates
the ``<`` / ``==`` / ``>`` trichotomy exhaustively on the same fields
iter 184 introduced.

Runs without pytest:

    python tests/test_input_palette_count_exceeds_output_palette_count.py

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


MATCHER_NAME = "input_palette_count_exceeds_output_palette_count"


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

def test_returns_true_on_strict_erasure_by_one() -> None:
    # The canonical positive case: output ⊊ input, input has exactly
    # one extra distinct colour over the output.
    patterns = {"pair_analyses": [_pair([0, 1, 2], [0, 1])]}
    assert _matcher()(patterns, {}) is True


def test_returns_true_on_strict_erasure_by_many() -> None:
    # Input palette much larger than output.
    patterns = {"pair_analyses": [_pair([1, 2, 3, 4, 5], [0])]}
    assert _matcher()(patterns, {}) is True


def test_returns_true_when_palettes_are_disjoint_but_input_larger() -> None:
    # Disjoint palettes co-firing with the reverse cardinality
    # direction: input ∩ output = empty AND |input| > |output|.
    patterns = {"pair_analyses": [_pair([3, 4, 5], [0, 1])]}
    assert _matcher()(patterns, {}) is True


def test_returns_true_with_duplicates_in_palettes() -> None:
    # The contract is on the cardinality of the SET; duplicates within
    # either list must not change the verdict.
    patterns = {"pair_analyses": [_pair([2, 2, 3, 3, 4, 4], [0, 0, 1, 1])]}
    assert _matcher()(patterns, {}) is True


def test_returns_true_when_output_empty_input_nonempty() -> None:
    # N > 0 for any N >= 1. The empty-output edge case fires.
    patterns = {"pair_analyses": [_pair([3, 4], [])]}
    assert _matcher()(patterns, {}) is True


def test_returns_true_across_multiple_pairs_all_satisfy() -> None:
    # Per-pair check is independent across pairs; each can have its
    # own palette as long as the strict cardinality gate holds.
    patterns = {
        "pair_analyses": [
            _pair([0, 1], [0]),
            _pair([3, 4, 5], [3, 4]),
            _pair([6, 7, 8, 9, 0], [6, 7, 8]),
        ],
    }
    assert _matcher()(patterns, {}) is True


# ──────────────────────────────────────────────────────────────────────────
# Negative cases.
# ──────────────────────────────────────────────────────────────────────────

def test_returns_false_on_palette_equality() -> None:
    # Equality has |input| == |output|; strict ``>`` rejects equality.
    patterns = {"pair_analyses": [_pair([0, 1, 2], [0, 1, 2])]}
    assert _matcher()(patterns, {}) is False


def test_returns_false_on_palette_permutation() -> None:
    # Permutation preserves cardinality; the strict gate rejects it.
    patterns = {"pair_analyses": [_pair([0, 1, 2], [2, 0, 1])]}
    assert _matcher()(patterns, {}) is False


def test_returns_false_on_palette_expansion() -> None:
    # Expansion has |input| < |output|; rejection (the iter-188 case).
    patterns = {"pair_analyses": [_pair([0, 1], [0, 1, 2])]}
    assert _matcher()(patterns, {}) is False


def test_returns_false_when_both_palettes_empty() -> None:
    # 0 > 0 is False; degenerate empty-empty case rejected.
    patterns = {"pair_analyses": [_pair([], [])]}
    assert _matcher()(patterns, {}) is False


def test_returns_false_when_input_empty_output_nonempty() -> None:
    # 0 > N where N >= 1 is False.
    patterns = {"pair_analyses": [_pair([], [0, 1])]}
    assert _matcher()(patterns, {}) is False


def test_returns_false_when_cardinality_equal_with_distinct_palettes() -> None:
    # Same cardinality on disjoint palettes still fails the strict gate.
    patterns = {"pair_analyses": [_pair([0, 1, 2], [3, 4, 5])]}
    assert _matcher()(patterns, {}) is False


def test_returns_false_when_any_pair_fails_the_gate() -> None:
    # Universal-over-pairs semantic: one failing pair fails the task.
    patterns = {
        "pair_analyses": [
            _pair([0, 1], [0]),
            _pair([3, 4], [3, 4, 5]),  # offending pair (expansion)
            _pair([6, 7, 8], [6, 7]),
        ],
    }
    assert _matcher()(patterns, {}) is False


def test_returns_false_on_empty_pair_analyses() -> None:
    # Fail-closed on empty input -- consistent with every other
    # matcher's posture.
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
            _pair([0, 1], [0]),
            "not-a-dict",
            _pair([3, 4], [3]),
        ],
    }
    assert _matcher()(patterns, {}) is False


# ──────────────────────────────────────────────────────────────────────────
# Strict-type-gate cases.
# ──────────────────────────────────────────────────────────────────────────

def test_returns_false_when_input_palette_missing() -> None:
    analysis = _pair([0, 1], [0])
    del analysis["input_palette"]
    patterns = {"pair_analyses": [analysis]}
    assert _matcher()(patterns, {}) is False


def test_returns_false_when_output_palette_missing() -> None:
    analysis = _pair([0, 1], [0])
    del analysis["output_palette"]
    patterns = {"pair_analyses": [analysis]}
    assert _matcher()(patterns, {}) is False


def test_returns_false_when_input_palette_is_not_list() -> None:
    for bad in (None, 42, "oops", {"a": 1}, (0, 1), True, {0, 1}):
        analysis = _pair([0, 1], [0])
        analysis["input_palette"] = bad
        patterns = {"pair_analyses": [analysis]}
        assert _matcher()(patterns, {}) is False, (
            f"input_palette={bad!r} should not fire"
        )


def test_returns_false_when_output_palette_is_not_list() -> None:
    for bad in (None, 42, "oops", {"a": 1}, (0, 1), True, {0, 1}):
        analysis = _pair([0, 1], [0])
        analysis["output_palette"] = bad
        patterns = {"pair_analyses": [analysis]}
        assert _matcher()(patterns, {}) is False, (
            f"output_palette={bad!r} should not fire"
        )


def test_returns_false_when_input_palette_contains_bool() -> None:
    # Python bools are an int subclass; strict gate must reject them.
    analysis = _pair([0, 1], [0])
    analysis["input_palette"] = [0, True]
    patterns = {"pair_analyses": [analysis]}
    assert _matcher()(patterns, {}) is False


def test_returns_false_when_output_palette_contains_bool() -> None:
    analysis = _pair([0, 1], [0])
    analysis["output_palette"] = [False]
    patterns = {"pair_analyses": [analysis]}
    assert _matcher()(patterns, {}) is False


def test_returns_false_when_palette_contains_non_int() -> None:
    analysis = _pair([0, 1], [0])
    analysis["input_palette"] = [0, "1"]
    patterns = {"pair_analyses": [analysis]}
    assert _matcher()(patterns, {}) is False

    analysis2 = _pair([0, 1], [0])
    analysis2["output_palette"] = [0.0]
    patterns2 = {"pair_analyses": [analysis2]}
    assert _matcher()(patterns2, {}) is False


# ──────────────────────────────────────────────────────────────────────────
# Behavioural-contract cases.
# ──────────────────────────────────────────────────────────────────────────

def test_is_side_effect_free_on_inputs() -> None:
    patterns = {
        "pair_analyses": [
            _pair([0, 1], [0]),
            _pair([3, 4], [3]),
        ],
    }
    params = {"unused": 1}
    before_p = copy.deepcopy(patterns)
    before_q = copy.deepcopy(params)
    _matcher()(patterns, params)
    assert patterns == before_p, "matcher mutated patterns"
    assert params == before_q, "matcher mutated params"


def test_is_deterministic_across_repeats() -> None:
    patterns = {"pair_analyses": [_pair([0, 1], [0])]}
    results = [_matcher()(patterns, {}) for _ in range(5)]
    assert len(set(results)) == 1, f"non-deterministic outputs: {results}"


def test_returned_value_is_boolean_not_truthy() -> None:
    # recognized_conditions filters on ``match(...) is True`` exactly,
    # so the matcher must return literal Booleans.
    out_true = _matcher()({"pair_analyses": [_pair([0, 1], [0])]}, {})
    out_false = _matcher()({"pair_analyses": [_pair([0], [0, 1])]}, {})
    assert out_true is True, f"expected literal True, got {out_true!r}"
    assert out_false is False, f"expected literal False, got {out_false!r}"


def test_ignores_per_group_color_lists() -> None:
    # The matcher reads ONLY ``input_palette`` / ``output_palette``.
    # Per-group ``input_colors`` / ``output_colors`` on the change
    # cells are a different axis -- the matcher must ignore them.
    analysis = _pair(
        [0, 1, 2], [0, 1],
        groups=[{
            "input_colors": [9, 9],  # not in either whole-grid palette
            "output_colors": [8, 8],
            "positions": [(0, 0)],
            "top_row": 0, "top_col": 0,
            "cell_count": 1,
        }],
        num_groups=1, total_changes=1,
    )
    patterns = {"pair_analyses": [analysis]}
    assert _matcher()(patterns, {}) is True


def test_ignores_dimensional_fields() -> None:
    # Dimensional fields are orthogonal -- arbitrary dim combinations
    # must not affect the matcher's verdict.
    analysis = _pair([0, 1, 2], [0, 1], input_height=7, input_width=9,
                     output_height=2, output_width=3, size_match=False)
    patterns = {"pair_analyses": [analysis]}
    assert _matcher()(patterns, {}) is True


# ──────────────────────────────────────────────────────────────────────────
# Orthogonality / co-fire matrix against the palette-axis siblings.
# ──────────────────────────────────────────────────────────────────────────

def test_mutually_exclusive_with_identity_transformation() -> None:
    # Identity has output palette equal to input palette per pair, so
    # cardinalities match: ``|input| > |output|`` is False on every
    # pair. Strict mutual exclusion on the universal-over-pairs gate.
    identity = CONDITION_REGISTRY["identity_transformation"]
    patterns = {
        "grid_size_preserved": True,
        "pair_analyses": [_pair([0, 1, 2], [0, 1, 2])],
    }
    assert identity(patterns, {}) is True
    assert _matcher()(patterns, {}) is False


def test_co_fires_with_iter184_subset_on_strict_erasure() -> None:
    # iter 184 (output ⊆ input) AND this matcher together name the
    # strict-erasure handle: output ⊊ input. Both fire here.
    iter184 = CONDITION_REGISTRY["output_palette_subset_of_input"]
    patterns = {"pair_analyses": [_pair([0, 1, 2, 3], [0, 1])]}
    assert iter184(patterns, {}) is True
    assert _matcher()(patterns, {}) is True


def test_iter184_alone_on_palette_equality() -> None:
    # iter 184 fires on equality; this matcher does NOT (strict ``>``
    # excludes equality). The conjunction (iter 184 AND this matcher)
    # is the named strict-erasure handle -- iter 184 alone over-fires
    # on equality / permutation cases.
    iter184 = CONDITION_REGISTRY["output_palette_subset_of_input"]
    patterns = {"pair_analyses": [_pair([0, 1, 2], [0, 1, 2])]}
    assert iter184(patterns, {}) is True
    assert _matcher()(patterns, {}) is False


def test_mutually_exclusive_with_iter185_equality() -> None:
    # Equality has |input| == |output|; strict ``>`` rejects.
    equality = CONDITION_REGISTRY["output_palette_equals_input"]
    p_eq = {"pair_analyses": [_pair([0, 1, 2], [0, 1, 2])]}
    assert equality(p_eq, {}) is True
    assert _matcher()(p_eq, {}) is False


def test_co_fires_with_iter186_disjoint_when_input_larger() -> None:
    # Disjoint + input-larger: canvas-rewrite with strictly more
    # distinct input colours than output. Both fire.
    disjoint = CONDITION_REGISTRY["output_palette_disjoint_from_input"]
    patterns = {"pair_analyses": [_pair([3, 4, 5], [0, 1])]}
    assert disjoint(patterns, {}) is True
    assert _matcher()(patterns, {}) is True


def test_iter186_disjoint_alone_when_input_not_larger() -> None:
    # Disjoint but input cardinality <= output cardinality: iter 186
    # fires; this matcher does not. Demonstrates non-refinement
    # relation between this matcher and iter 186.
    disjoint = CONDITION_REGISTRY["output_palette_disjoint_from_input"]

    # |input| < |output|, disjoint
    p1 = {"pair_analyses": [_pair([4], [0, 1, 2])]}
    assert disjoint(p1, {}) is True
    assert _matcher()(p1, {}) is False

    # |input| == |output|, disjoint
    p2 = {"pair_analyses": [_pair([0, 1], [3, 4])]}
    assert disjoint(p2, {}) is True
    assert _matcher()(p2, {}) is False


def test_mutually_exclusive_with_iter187_input_subset() -> None:
    # Input ⊆ output ⇒ |input| <= |output|; strict ``>`` is False.
    iter187 = CONDITION_REGISTRY["input_palette_subset_of_output"]

    # Expansion: iter 187 fires, this matcher does not.
    p_exp = {"pair_analyses": [_pair([0, 1], [0, 1, 2])]}
    assert iter187(p_exp, {}) is True
    assert _matcher()(p_exp, {}) is False

    # Equality: iter 187 fires, this matcher does not.
    p_eq = {"pair_analyses": [_pair([0, 1, 2], [0, 1, 2])]}
    assert iter187(p_eq, {}) is True
    assert _matcher()(p_eq, {}) is False


def test_mutually_exclusive_with_iter188_strict_expansion() -> None:
    # The two strict-cardinality directions on the same axis cannot
    # both hold on the same pair. The (iter 188, this matcher, iter
    # 185) triple is the < / == / > trichotomy on the cardinality-
    # direction sub-axis exhaustively.
    iter188 = CONDITION_REGISTRY["output_palette_count_exceeds_input_palette_count"]

    # Strict expansion: iter 188 fires, this matcher does not.
    p_exp = {"pair_analyses": [_pair([0, 1], [0, 1, 2])]}
    assert iter188(p_exp, {}) is True
    assert _matcher()(p_exp, {}) is False

    # Strict erasure: this matcher fires, iter 188 does not.
    p_erase = {"pair_analyses": [_pair([0, 1, 2], [0, 1])]}
    assert iter188(p_erase, {}) is False
    assert _matcher()(p_erase, {}) is True

    # Equality: neither strict direction fires.
    p_eq = {"pair_analyses": [_pair([0, 1, 2], [0, 1, 2])]}
    assert iter188(p_eq, {}) is False
    assert _matcher()(p_eq, {}) is False


def test_orthogonal_to_grid_size_preserved() -> None:
    # Whole-grid palette cardinality direction is orthogonal to the
    # per-pair input==output dim axis (the four-cell 2x2 co-fire table).
    gsp = CONDITION_REGISTRY["grid_size_preserved"]

    # erasure + preserved -- both fire
    p1 = {
        "grid_size_preserved": True,
        "pair_analyses": [_pair([0, 1, 2], [0, 1])],
    }
    assert _matcher()(p1, {}) is True and gsp(p1, {}) is True

    # erasure + changed -- only this matcher fires
    p2 = {
        "grid_size_preserved": False,
        "pair_analyses": [
            _pair([0, 1, 2], [0, 1], output_height=6, output_width=6,
                  size_match=False),
        ],
    }
    assert _matcher()(p2, {}) is True and gsp(p2, {}) is False

    # not-erasure + preserved -- only preserved fires
    p3 = {
        "grid_size_preserved": True,
        "pair_analyses": [_pair([0, 1], [0, 1, 2])],
    }
    assert _matcher()(p3, {}) is False and gsp(p3, {}) is True

    # not-erasure + changed -- neither fires
    p4 = {
        "grid_size_preserved": False,
        "pair_analyses": [
            _pair([0, 1], [0, 1, 2], output_height=6, output_width=6,
                  size_match=False),
        ],
    }
    assert _matcher()(p4, {}) is False and gsp(p4, {}) is False


def test_orthogonal_to_input_color_uniform() -> None:
    # iter 14 inspects change-cells' input colour uniformity. The
    # whole-grid palette cardinality direction axis is INDEPENDENT.
    icu = CONDITION_REGISTRY["input_color_uniform"]

    # this matcher fires AND icu fires (single change-cell source
    # colour, palette strictly erased).
    analysis = _pair(
        [0, 5, 3], [0, 5],
        groups=[{
            "input_colors": [3],
            "output_colors": [5],
            "positions": [(0, 0)],
            "top_row": 0, "top_col": 0,
            "cell_count": 1,
        }],
        num_groups=1, total_changes=1,
    )
    p1 = {"pair_analyses": [analysis]}
    assert _matcher()(p1, {}) is True and icu(p1, {}) is True

    # this matcher fires but icu does NOT (no change cells means
    # iter 14 is vacuously False per its docstring).
    p2 = {"pair_analyses": [_pair([0, 1, 2], [0, 1])]}
    assert _matcher()(p2, {}) is True and icu(p2, {}) is False


def test_recognized_conditions_includes_count_exceeds() -> None:
    from agent.conditions import recognized_conditions
    # Strict-erasure case: this matcher fires AND iter-184 fires;
    # iter-185 / 186 / 187 / 188 do not.
    patterns = {"pair_analyses": [_pair([0, 1, 2, 3], [0, 1])]}
    fired = recognized_conditions(patterns)
    assert MATCHER_NAME in fired, (
        f"{MATCHER_NAME!r} did not fire on a clearly strict-erasure "
        f"patterns dict; got {fired!r}"
    )
    assert "output_palette_subset_of_input" in fired, (
        "iter-184 must co-fire on strict-erasure (it's the output-side "
        "set-containment gate)"
    )
    assert "output_palette_equals_input" not in fired
    assert "output_palette_disjoint_from_input" not in fired
    assert "input_palette_subset_of_output" not in fired
    assert "output_palette_count_exceeds_input_palette_count" not in fired


def test_recognized_conditions_excludes_on_equality() -> None:
    # Equality fires iter 184 / 185 / 187 but NOT this matcher (the
    # strict-cardinality gate). Demonstrates the named distinction
    # between equality and strict-erasure.
    from agent.conditions import recognized_conditions
    patterns = {"pair_analyses": [_pair([0, 1, 2], [0, 1, 2])]}
    fired = recognized_conditions(patterns)
    assert "output_palette_subset_of_input" in fired
    assert "output_palette_equals_input" in fired
    assert "input_palette_subset_of_output" in fired
    assert MATCHER_NAME not in fired, (
        f"{MATCHER_NAME!r} must NOT fire on palette equality (strict ``>`` "
        f"excludes equality); got {fired!r}"
    )
    assert "output_palette_count_exceeds_input_palette_count" not in fired


def test_recognized_conditions_excludes_on_strict_expansion() -> None:
    # Strict expansion fires iter 187 + iter 188 but NOT this matcher;
    # demonstrates the named distinction between the two strict
    # directions of the cardinality-direction sub-axis.
    from agent.conditions import recognized_conditions
    patterns = {"pair_analyses": [_pair([0, 1], [0, 1, 2, 3])]}
    fired = recognized_conditions(patterns)
    assert "input_palette_subset_of_output" in fired
    assert "output_palette_count_exceeds_input_palette_count" in fired
    assert MATCHER_NAME not in fired, (
        f"{MATCHER_NAME!r} must NOT fire on strict palette expansion "
        f"(the dual strict direction); got {fired!r}"
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
