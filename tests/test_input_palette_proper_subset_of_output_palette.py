"""
tests/test_input_palette_proper_subset_of_output_palette.py --
exercise the iter-212 matcher
``agent.conditions.input_palette_proper_subset_of_output_palette``.

Pins the matcher's contract per
``agent/conditions/input_palette_proper_subset_of_output_palette.py``
docstring: every pair satisfies
``set(input_palette) < set(output_palette)`` on a non-empty
``pair_analyses`` list with both palettes shaped as lists of non-bool
ints. The "smoke" membership / callability slots mirror the other
matcher tests so the registry-vs-test-file diff stays empty.

Runs without pytest:

    python tests/test_input_palette_proper_subset_of_output_palette.py

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


MATCHER_NAME = "input_palette_proper_subset_of_output_palette"


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

def test_returns_true_on_basic_strict_expansion() -> None:
    # ip = {0, 1}, op = {0, 1, 2}: |ip| < |op|, ip is contained in op.
    patterns = {"pair_analyses": [_pair([0, 1], [0, 1, 2])]}
    assert _matcher()(patterns, {}) is True


def test_returns_true_on_one_colour_added() -> None:
    # ip = {0, 1, 2}, op = {0, 1, 2, 3}: a single fresh colour added.
    patterns = {"pair_analyses": [_pair([0, 1, 2], [0, 1, 2, 3])]}
    assert _matcher()(patterns, {}) is True


def test_returns_true_on_empty_input_with_singleton_output() -> None:
    # Empty set is a strict proper subset of any non-empty set.
    patterns = {"pair_analyses": [_pair([], [5])]}
    assert _matcher()(patterns, {}) is True


def test_returns_true_on_multipair_strict_expansion() -> None:
    # Each pair carries a distinct strict-expansion shape; the matcher's
    # universal-over-pairs semantic admits per-pair variation.
    patterns = {
        "pair_analyses": [
            _pair([0, 1], [0, 1, 2]),
            _pair([3, 5], [3, 4, 5, 6]),
            _pair([7], [7, 8, 9]),
        ],
    }
    assert _matcher()(patterns, {}) is True


def test_returns_true_with_duplicate_colours_in_palette_lists() -> None:
    # Palettes are lists, not sets; the matcher set-ifies them.
    # Duplicate entries on either side must not affect the verdict.
    patterns = {"pair_analyses": [_pair([0, 0, 1], [0, 0, 1, 2, 2])]}
    assert _matcher()(patterns, {}) is True


# --------------------------------------------------------------------------
# Negative cases -- strict mutual exclusion with the other cells.
# --------------------------------------------------------------------------

def test_returns_false_when_output_palette_equals_input() -> None:
    # Equality (iter-185 territory): set equality forbids strict
    # proper subset.
    patterns = {"pair_analyses": [_pair([0, 1, 2], [0, 1, 2])]}
    assert _matcher()(patterns, {}) is False


def test_returns_false_when_output_palette_strict_subset_of_input() -> None:
    # Iter-211 strict-erasure territory: NOT (ip ⊆ op), so NOT (ip ⊊
    # op).
    patterns = {"pair_analyses": [_pair([0, 1, 2], [0, 1])]}
    assert _matcher()(patterns, {}) is False


def test_returns_false_on_partial_overlap() -> None:
    # Iter-210 partial-overlap territory: NOT (ip ⊆ op), so this
    # matcher rejects.
    patterns = {"pair_analyses": [_pair([0, 1, 2], [2, 3, 4])]}
    assert _matcher()(patterns, {}) is False


def test_returns_false_on_disjoint_with_nonempty_ip() -> None:
    # Disjoint with non-empty ip: NOT (ip ⊆ op), so this matcher
    # rejects. Iter-186 fires here.
    patterns = {"pair_analyses": [_pair([0, 1, 2], [3, 4, 5])]}
    assert _matcher()(patterns, {}) is False


def test_returns_false_when_output_palette_empty() -> None:
    # Empty output palette: no proper-subset relation possible with
    # any input palette (ip ⊊ ∅ has no solution since ∅ is the
    # smallest set).
    patterns = {"pair_analyses": [_pair([0, 1], [])]}
    assert _matcher()(patterns, {}) is False

    patterns2 = {"pair_analyses": [_pair([], [])]}
    assert _matcher()(patterns2, {}) is False


def test_returns_false_when_any_pair_fails_the_gate() -> None:
    # Universal-over-pairs semantic: a single failing pair fails the
    # whole task.
    patterns = {
        "pair_analyses": [
            _pair([0, 1], [0, 1, 2]),      # strict expansion
            _pair([0, 1], [0, 1]),         # equality -- offending
            _pair([3], [3, 4]),            # strict expansion
        ],
    }
    assert _matcher()(patterns, {}) is False


def test_returns_false_on_empty_pair_analyses() -> None:
    # Fail-closed on empty input -- consistent with every other
    # matcher's posture (iters 1 / 13 / 17 / 20 / 22 / 33 / 182 / 183 /
    # 184 / 185 / 186 / 187 / 210 / 211).
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
            _pair([0, 1], [0, 1, 2]),
            "not-a-dict",
            _pair([3], [3, 4]),
        ],
    }
    assert _matcher()(patterns, {}) is False


# --------------------------------------------------------------------------
# Strict-type-gate cases.
# --------------------------------------------------------------------------

def test_returns_false_when_input_palette_missing() -> None:
    analysis = _pair([0, 1], [0, 1, 2])
    del analysis["input_palette"]
    patterns = {"pair_analyses": [analysis]}
    assert _matcher()(patterns, {}) is False


def test_returns_false_when_output_palette_missing() -> None:
    analysis = _pair([0, 1], [0, 1, 2])
    del analysis["output_palette"]
    patterns = {"pair_analyses": [analysis]}
    assert _matcher()(patterns, {}) is False


def test_returns_false_when_input_palette_is_not_list() -> None:
    for bad in (None, 42, "oops", {"a": 1}, (0, 1), True, {0, 1}):
        analysis = _pair([0, 1], [0, 1, 2])
        analysis["input_palette"] = bad
        patterns = {"pair_analyses": [analysis]}
        assert _matcher()(patterns, {}) is False, (
            f"input_palette={bad!r} should not fire"
        )


def test_returns_false_when_output_palette_is_not_list() -> None:
    for bad in (None, 42, "oops", {"a": 1}, (0, 1, 2), True, {0, 1, 2}):
        analysis = _pair([0, 1], [0, 1, 2])
        analysis["output_palette"] = bad
        patterns = {"pair_analyses": [analysis]}
        assert _matcher()(patterns, {}) is False, (
            f"output_palette={bad!r} should not fire"
        )


def test_returns_false_when_input_palette_contains_bool() -> None:
    # Python bools are an int subclass; strict gate must reject them
    # (same posture as iter 184 / 185 / 186 / 187 / 210 / 211).
    analysis = _pair([0, 1], [0, 1, 2])
    analysis["input_palette"] = [0, True]
    patterns = {"pair_analyses": [analysis]}
    assert _matcher()(patterns, {}) is False


def test_returns_false_when_output_palette_contains_bool() -> None:
    analysis = _pair([0, 1], [0, 1, 2])
    analysis["output_palette"] = [False, 1, 2]
    patterns = {"pair_analyses": [analysis]}
    assert _matcher()(patterns, {}) is False


def test_returns_false_when_palette_contains_non_int() -> None:
    analysis = _pair([0, 1], [0, 1, 2])
    analysis["input_palette"] = [0, "1"]
    patterns = {"pair_analyses": [analysis]}
    assert _matcher()(patterns, {}) is False

    analysis2 = _pair([0, 1], [0, 1, 2])
    analysis2["output_palette"] = [0.0, 1.0, 2.0]
    patterns2 = {"pair_analyses": [analysis2]}
    assert _matcher()(patterns2, {}) is False


# --------------------------------------------------------------------------
# Behavioural-contract cases.
# --------------------------------------------------------------------------

def test_is_side_effect_free_on_inputs() -> None:
    patterns = {
        "pair_analyses": [
            _pair([0, 1], [0, 1, 2]),
            _pair([3], [3, 4, 5]),
        ],
    }
    params = {"unused": 1}
    before_p = copy.deepcopy(patterns)
    before_q = copy.deepcopy(params)
    _matcher()(patterns, params)
    assert patterns == before_p, "matcher mutated patterns"
    assert params == before_q, "matcher mutated params"


def test_is_deterministic_across_repeats() -> None:
    patterns = {"pair_analyses": [_pair([0, 1], [0, 1, 2])]}
    results = [_matcher()(patterns, {}) for _ in range(5)]
    assert len(set(results)) == 1, f"non-deterministic outputs: {results}"


def test_returned_value_is_boolean_not_truthy() -> None:
    # recognized_conditions filters on ``match(...) is True`` exactly,
    # so the matcher must return literal Booleans.
    out_true = _matcher()({"pair_analyses": [_pair([0, 1], [0, 1, 2])]}, {})
    out_false = _matcher()({"pair_analyses": [_pair([0, 1], [0, 1])]}, {})
    assert out_true is True, f"expected literal True, got {out_true!r}"
    assert out_false is False, f"expected literal False, got {out_false!r}"


def test_tolerates_erase_sentinel_13_in_palette() -> None:
    # Whole-grid posture (iter 184 / 185 / 186 / 187 / 190 / 191 / 210 /
    # 211) tolerates any int value -- including the iter-180 erase
    # sentinel 13. The strict-proper-subset gate must still apply.
    # ip = {0, 13}, op = {0, 1, 13}: ip ⊊ op.
    patterns = {"pair_analyses": [_pair([0, 13], [0, 1, 13])]}
    assert _matcher()(patterns, {}) is True


def test_ignores_per_group_color_lists() -> None:
    # The matcher reads ONLY ``input_palette`` / ``output_palette``.
    # Per-group ``input_colors`` / ``output_colors`` are a different
    # axis -- the matcher must ignore them.
    analysis = _pair(
        [0, 1], [0, 1, 2],
        groups=[{
            "input_colors": [9, 9, 9],
            "output_colors": [9, 9, 9],
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
    analysis = _pair([0, 1], [0, 1, 2], input_height=7, input_width=9,
                     output_height=2, output_width=3, size_match=False)
    patterns = {"pair_analyses": [analysis]}
    assert _matcher()(patterns, {}) is True


# --------------------------------------------------------------------------
# Orthogonality / refinement / mutual-exclusion matrix against existing
# axes.
# --------------------------------------------------------------------------

def test_strict_implication_of_input_palette_subset_of_output() -> None:
    # Strict refinement: this matcher fires => iter 187 fires.
    subset = CONDITION_REGISTRY["input_palette_subset_of_output"]

    # Strict expansion -- both fire.
    p1 = {"pair_analyses": [_pair([0, 1], [0, 1, 2])]}
    assert _matcher()(p1, {}) is True and subset(p1, {}) is True

    # Equality -- iter 187 fires but this matcher does not.
    p2 = {"pair_analyses": [_pair([0, 1, 2], [0, 1, 2])]}
    assert _matcher()(p2, {}) is False and subset(p2, {}) is True


def test_mutually_exclusive_with_output_palette_equals_input() -> None:
    # Iter 185 (equality) and this matcher partition iter 187's
    # territory disjunctively.
    eq = CONDITION_REGISTRY["output_palette_equals_input"]

    # Strict expansion -- this matcher fires, equality does not.
    p1 = {"pair_analyses": [_pair([0, 1], [0, 1, 2])]}
    assert _matcher()(p1, {}) is True and eq(p1, {}) is False

    # Equality -- equality fires, this matcher does not.
    p2 = {"pair_analyses": [_pair([0, 1, 2], [0, 1, 2])]}
    assert _matcher()(p2, {}) is False and eq(p2, {}) is True


def test_mutually_exclusive_with_output_palette_subset_of_input() -> None:
    # Iter 184 (output ⊆ input) and this matcher (input ⊊ output) are
    # strictly mutually exclusive on non-empty input domain.
    sub = CONDITION_REGISTRY["output_palette_subset_of_input"]

    # Strict expansion -- this matcher fires, iter 184 does not.
    p1 = {"pair_analyses": [_pair([0, 1], [0, 1, 2])]}
    assert _matcher()(p1, {}) is True and sub(p1, {}) is False

    # Strict erasure (output ⊊ input) -- iter 184 fires, this matcher
    # does not.
    p2 = {"pair_analyses": [_pair([0, 1, 2], [0, 1])]}
    assert _matcher()(p2, {}) is False and sub(p2, {}) is True


def test_mutually_exclusive_with_output_palette_proper_subset_of_input() -> None:
    # Iter 211 (output ⊊ input) is the symmetric dual; this matcher
    # is (input ⊊ output). Proper subset in opposite directions
    # simultaneously is impossible on non-empty sets.
    er = CONDITION_REGISTRY["output_palette_proper_subset_of_input_palette"]

    # Strict expansion -- this matcher fires, iter 211 does not.
    p1 = {"pair_analyses": [_pair([0, 1], [0, 1, 2])]}
    assert _matcher()(p1, {}) is True and er(p1, {}) is False

    # Strict erasure -- iter 211 fires, this matcher does not.
    p2 = {"pair_analyses": [_pair([0, 1, 2], [0, 1])]}
    assert _matcher()(p2, {}) is False and er(p2, {}) is True


def test_mutually_exclusive_with_output_palette_partial_overlap() -> None:
    # Iter 210 (partial overlap requires NOT (ip ⊆ op) AND NOT (op ⊆
    # ip)) is strictly mutually exclusive with this matcher.
    po = CONDITION_REGISTRY["output_palette_partial_overlap_with_input_palette"]

    # Strict expansion -- this matcher fires, partial overlap does
    # not.
    p1 = {"pair_analyses": [_pair([0, 1], [0, 1, 2])]}
    assert _matcher()(p1, {}) is True and po(p1, {}) is False

    # Partial overlap -- iter 210 fires, this matcher does not.
    p2 = {"pair_analyses": [_pair([0, 1, 2], [2, 3, 4])]}
    assert _matcher()(p2, {}) is False and po(p2, {}) is True


def test_strict_implication_of_output_palette_count_exceeds_input() -> None:
    # On non-empty outputs, this matcher fires => iter 188 fires
    # (proper subset forces |ip| < |op|). Reverse does NOT hold:
    # disjoint with |op| > |ip| fires iter 188 but not this matcher.
    gt = CONDITION_REGISTRY["output_palette_count_exceeds_input_palette_count"]

    # Strict expansion -- both fire.
    p1 = {"pair_analyses": [_pair([0, 1], [0, 1, 2])]}
    assert _matcher()(p1, {}) is True and gt(p1, {}) is True

    # Disjoint with |op| > |ip| -- iter 188 fires, this matcher does
    # not.
    p2 = {"pair_analyses": [_pair([0, 1], [7, 8, 9])]}
    assert _matcher()(p2, {}) is False and gt(p2, {}) is True


def test_orthogonal_to_grid_size_preserved() -> None:
    # Whole-grid palette strict-expansion is orthogonal to the per-pair
    # input==output dim axis.
    gsp = CONDITION_REGISTRY["grid_size_preserved"]

    # strict expansion + preserved -- both fire
    p1 = {
        "grid_size_preserved": True,
        "pair_analyses": [_pair([0, 1], [0, 1, 2])],
    }
    assert _matcher()(p1, {}) is True and gsp(p1, {}) is True

    # strict expansion + changed -- only this matcher fires
    p2 = {
        "grid_size_preserved": False,
        "pair_analyses": [
            _pair([0, 1], [0, 1, 2], output_height=6, output_width=6,
                  size_match=False),
        ],
    }
    assert _matcher()(p2, {}) is True and gsp(p2, {}) is False

    # equality + preserved -- only preserved fires
    p3 = {
        "grid_size_preserved": True,
        "pair_analyses": [_pair([0, 1], [0, 1])],
    }
    assert _matcher()(p3, {}) is False and gsp(p3, {}) is True


def test_recognized_conditions_includes_strict_expansion() -> None:
    from agent.conditions import recognized_conditions
    patterns = {"pair_analyses": [_pair([0, 1], [0, 1, 2])]}
    fired = recognized_conditions(patterns)
    assert MATCHER_NAME in fired, (
        f"{MATCHER_NAME!r} did not fire on a clearly-strict-expansion "
        f"patterns dict; got {fired!r}"
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
