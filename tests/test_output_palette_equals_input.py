"""
tests/test_output_palette_equals_input.py -- exercise the iter-185
matcher ``agent.conditions.output_palette_equals_input`` (new in this
iter).

Pins the matcher's contract per
``agent/conditions/output_palette_equals_input.py`` docstring: every
pair's ``set(output_palette) == set(input_palette)`` on a non-empty
``pair_analyses`` list with both palettes shaped as lists of non-bool
ints. Strict-equality companion of iter-184's subset matcher.

Runs without pytest:

    python tests/test_output_palette_equals_input.py

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


MATCHER_NAME = "output_palette_equals_input"


def _matcher():
    return CONDITION_REGISTRY[MATCHER_NAME]


def _pair(input_palette, output_palette, **overrides):
    """A pair_analysis shaped like ExtractPatternOperator's output
    (iter-184 schema, with the new palette fields)."""
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

def test_returns_true_when_palettes_are_set_equal() -> None:
    # Identity of contents -- the canonical positive case.
    patterns = {"pair_analyses": [_pair([0, 1, 2], [0, 1, 2])]}
    assert _matcher()(patterns, {}) is True


def test_returns_true_when_palettes_equal_under_reordering() -> None:
    # Set-equality, not list-equality: order does not matter.
    patterns = {"pair_analyses": [_pair([0, 1, 2], [2, 0, 1])]}
    assert _matcher()(patterns, {}) is True


def test_returns_true_when_palettes_equal_with_duplicate_entries() -> None:
    # The contract is set-equality, so duplicates within a single list
    # do not change the set and must not break the gate. (The upstream
    # extractor de-duplicates by construction, but the matcher must not
    # crash if it ever sees duplicates.)
    patterns = {"pair_analyses": [_pair([0, 1, 1, 2], [0, 0, 1, 2])]}
    assert _matcher()(patterns, {}) is True


def test_returns_true_on_single_color_grids() -> None:
    # Both grids monochrome with the same colour -- equality holds.
    patterns = {"pair_analyses": [_pair([7], [7])]}
    assert _matcher()(patterns, {}) is True


def test_returns_true_across_multiple_pairs_with_varying_palettes() -> None:
    # Per-pair equality is independent across pairs; varying palettes
    # are allowed as long as each pair satisfies the gate.
    patterns = {
        "pair_analyses": [
            _pair([0, 1], [0, 1]),
            _pair([2, 3, 4], [2, 3, 4]),
            _pair([5], [5]),
        ],
    }
    assert _matcher()(patterns, {}) is True


def test_returns_true_when_both_palettes_empty() -> None:
    # The empty set equals itself; an empty-vs-empty pair satisfies
    # set-equality vacuously. Mirrors iter-184's behaviour on an
    # empty output palette in the subset matcher.
    patterns = {"pair_analyses": [_pair([], [])]}
    assert _matcher()(patterns, {}) is True


# ──────────────────────────────────────────────────────────────────────────
# Negative cases.
# ──────────────────────────────────────────────────────────────────────────

def test_returns_false_on_strict_subset_output_drops_a_color() -> None:
    # Output drops one colour from the input palette: subset matcher
    # would fire (iter 184), but equality must NOT.
    patterns = {"pair_analyses": [_pair([0, 1, 2], [0, 1])]}
    assert _matcher()(patterns, {}) is False


def test_returns_false_on_strict_superset_output_adds_new_color() -> None:
    # A single new colour on the output side breaks equality.
    patterns = {"pair_analyses": [_pair([0, 1, 2], [0, 1, 2, 3])]}
    assert _matcher()(patterns, {}) is False


def test_returns_false_when_output_is_disjoint_from_input() -> None:
    # Fully disjoint palettes (canvas-rewrite tasks) -- the dual axis.
    patterns = {"pair_analyses": [_pair([0, 1, 2], [3, 4, 5])]}
    assert _matcher()(patterns, {}) is False


def test_returns_false_when_palettes_overlap_partially() -> None:
    # Partial overlap (one shared, one fresh on each side) -- breaks
    # both inclusion directions, so equality must fail.
    patterns = {"pair_analyses": [_pair([0, 1, 2], [1, 2, 3])]}
    assert _matcher()(patterns, {}) is False


def test_returns_false_when_any_pair_fails_the_gate() -> None:
    # Universal-over-pairs semantic: a single failing pair fails the
    # whole task.
    patterns = {
        "pair_analyses": [
            _pair([0, 1, 2], [0, 1, 2]),
            _pair([0, 1], [0, 1, 9]),  # offending pair (adds 9)
            _pair([3], [3]),
        ],
    }
    assert _matcher()(patterns, {}) is False


def test_returns_false_on_empty_pair_analyses() -> None:
    # Fail-closed on empty input -- consistent with every other
    # matcher's posture (iters 1 / 13 / 17 / 20 / 22 / 33 / 182 / 183 /
    # 184).
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
            _pair([0, 1], [0, 1]),
            "not-a-dict",
            _pair([2, 3], [2, 3]),
        ],
    }
    assert _matcher()(patterns, {}) is False


# ──────────────────────────────────────────────────────────────────────────
# Strict-type-gate cases.
# ──────────────────────────────────────────────────────────────────────────

def test_returns_false_when_input_palette_missing() -> None:
    analysis = _pair([0, 1], [0, 1])
    del analysis["input_palette"]
    patterns = {"pair_analyses": [analysis]}
    assert _matcher()(patterns, {}) is False


def test_returns_false_when_output_palette_missing() -> None:
    analysis = _pair([0, 1], [0, 1])
    del analysis["output_palette"]
    patterns = {"pair_analyses": [analysis]}
    assert _matcher()(patterns, {}) is False


def test_returns_false_when_input_palette_is_not_list() -> None:
    for bad in (None, 42, "oops", {"a": 1}, (0, 1), True, {0, 1}):
        analysis = _pair([0, 1], [0, 1])
        analysis["input_palette"] = bad
        patterns = {"pair_analyses": [analysis]}
        assert _matcher()(patterns, {}) is False, (
            f"input_palette={bad!r} should not fire"
        )


def test_returns_false_when_output_palette_is_not_list() -> None:
    for bad in (None, 42, "oops", {"a": 1}, (0, 1), True, {0, 1}):
        analysis = _pair([0, 1], [0, 1])
        analysis["output_palette"] = bad
        patterns = {"pair_analyses": [analysis]}
        assert _matcher()(patterns, {}) is False, (
            f"output_palette={bad!r} should not fire"
        )


def test_returns_false_when_input_palette_contains_bool() -> None:
    # Python bools are an int subclass; strict gate must reject them
    # (same posture as iter-182 / 183 dimensional matchers and the
    # iter-184 subset matcher).
    analysis = _pair([0, 1], [0, 1])
    analysis["input_palette"] = [0, True, 2]
    patterns = {"pair_analyses": [analysis]}
    assert _matcher()(patterns, {}) is False


def test_returns_false_when_output_palette_contains_bool() -> None:
    analysis = _pair([0, 1], [0, 1])
    analysis["output_palette"] = [False, 1]
    patterns = {"pair_analyses": [analysis]}
    assert _matcher()(patterns, {}) is False


def test_returns_false_when_palette_contains_non_int() -> None:
    analysis = _pair([0, 1], [0, 1])
    analysis["input_palette"] = [0, "1", 2]
    patterns = {"pair_analyses": [analysis]}
    assert _matcher()(patterns, {}) is False

    analysis2 = _pair([0, 1], [0, 1])
    analysis2["output_palette"] = [0.0, 1.0]
    patterns2 = {"pair_analyses": [analysis2]}
    assert _matcher()(patterns2, {}) is False


# ──────────────────────────────────────────────────────────────────────────
# Behavioural-contract cases.
# ──────────────────────────────────────────────────────────────────────────

def test_is_side_effect_free_on_inputs() -> None:
    patterns = {
        "pair_analyses": [
            _pair([0, 1, 2], [0, 1, 2]),
            _pair([3, 4], [3, 4]),
        ],
    }
    params = {"unused": 1}
    before_p = copy.deepcopy(patterns)
    before_q = copy.deepcopy(params)
    _matcher()(patterns, params)
    assert patterns == before_p, "matcher mutated patterns"
    assert params == before_q, "matcher mutated params"


def test_is_deterministic_across_repeats() -> None:
    patterns = {"pair_analyses": [_pair([0, 1, 2], [0, 1, 2])]}
    results = [_matcher()(patterns, {}) for _ in range(5)]
    assert len(set(results)) == 1, f"non-deterministic outputs: {results}"


def test_returned_value_is_boolean_not_truthy() -> None:
    # recognized_conditions filters on ``match(...) is True`` exactly,
    # so the matcher must return literal Booleans.
    out_true = _matcher()({"pair_analyses": [_pair([0, 1], [0, 1])]}, {})
    out_false = _matcher()({"pair_analyses": [_pair([0], [0, 1])]}, {})
    assert out_true is True, f"expected literal True, got {out_true!r}"
    assert out_false is False, f"expected literal False, got {out_false!r}"


def test_ignores_per_group_color_lists() -> None:
    # The matcher reads ONLY ``input_palette`` / ``output_palette``.
    # Per-group ``input_colors`` / ``output_colors`` on the change
    # cells are a different axis -- the matcher must ignore them.
    analysis = _pair(
        [0, 1, 2], [0, 1, 2],
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
    analysis = _pair([0, 1], [0, 1], input_height=7, input_width=9,
                     output_height=2, output_width=3, size_match=False)
    patterns = {"pair_analyses": [analysis]}
    assert _matcher()(patterns, {}) is True


# ──────────────────────────────────────────────────────────────────────────
# Orthogonality / co-fire matrix against existing axes.
# ──────────────────────────────────────────────────────────────────────────

def test_strict_implication_from_identity_transformation() -> None:
    # Iter 13 strict-implies this matcher: zero changed cells means
    # output palette equals input palette (the cells are unchanged).
    # Both must fire on the same patterns dict.
    identity = CONDITION_REGISTRY["identity_transformation"]
    identity_pair = _pair([0, 1, 2], [0, 1, 2])
    patterns = {
        "grid_size_preserved": True,
        "pair_analyses": [identity_pair],
    }
    assert _matcher()(patterns, {}) is True
    assert identity(patterns, {}) is True


def test_implication_from_identity_does_not_reverse() -> None:
    # A pure permutation (every red becomes blue AND every blue
    # becomes red -- palettes equal as sets, cells changed) fires
    # equality but NOT iter 13. Confirms the asymmetry: equality
    # ⇏ identity.
    identity = CONDITION_REGISTRY["identity_transformation"]
    analysis = _pair(
        [0, 1], [0, 1],
        groups=[{
            "input_colors": [0],
            "output_colors": [1],
            "positions": [(0, 0)],
            "top_row": 0, "top_col": 0,
            "cell_count": 1,
        }],
        num_groups=1, total_changes=1,
    )
    patterns = {"grid_size_preserved": True, "pair_analyses": [analysis]}
    assert _matcher()(patterns, {}) is True
    assert identity(patterns, {}) is False


def test_strict_refinement_of_subset_matcher() -> None:
    # Equality is a strict refinement of subset (iter 184). On every
    # patterns dict where equality fires, subset MUST also fire.
    subset = CONDITION_REGISTRY["output_palette_subset_of_input"]
    patterns = {
        "pair_analyses": [
            _pair([0, 1, 2], [0, 1, 2]),
            _pair([3, 4], [4, 3]),
        ],
    }
    assert _matcher()(patterns, {}) is True
    assert subset(patterns, {}) is True


def test_subset_fires_but_equality_does_not_on_erasure() -> None:
    # The asymmetry: an erasure (output drops a colour) fires subset
    # but NOT equality. This is the precise reason equality exists as
    # a separate matcher -- to gate permutation rules without
    # over-firing on erasures.
    subset = CONDITION_REGISTRY["output_palette_subset_of_input"]
    patterns = {"pair_analyses": [_pair([0, 1, 2], [0, 1])]}
    assert subset(patterns, {}) is True
    assert _matcher()(patterns, {}) is False


def test_orthogonal_to_grid_size_preserved() -> None:
    # Whole-grid palette equality is orthogonal to the per-pair
    # input==output dim axis (the four-cell 2x2 co-fire table).
    gsp = CONDITION_REGISTRY["grid_size_preserved"]

    # equal + preserved -- both fire
    p1 = {
        "grid_size_preserved": True,
        "pair_analyses": [_pair([0, 1, 2], [0, 1, 2])],
    }
    assert _matcher()(p1, {}) is True and gsp(p1, {}) is True

    # equal + changed -- only equality fires
    p2 = {
        "grid_size_preserved": False,
        "pair_analyses": [
            _pair([0, 1, 2], [0, 1, 2], output_height=6, output_width=6,
                  size_match=False),
        ],
    }
    assert _matcher()(p2, {}) is True and gsp(p2, {}) is False

    # not-equal + preserved -- only preserved fires
    p3 = {
        "grid_size_preserved": True,
        "pair_analyses": [_pair([0, 1], [0, 1, 9])],
    }
    assert _matcher()(p3, {}) is False and gsp(p3, {}) is True

    # not-equal + changed -- neither fires
    p4 = {
        "grid_size_preserved": False,
        "pair_analyses": [
            _pair([0, 1], [0, 1, 9], output_height=6, output_width=6,
                  size_match=False),
        ],
    }
    assert _matcher()(p4, {}) is False and gsp(p4, {}) is False


def test_orthogonal_to_input_color_uniform() -> None:
    # iter 14 inspects change-cells' input colour uniformity. The
    # whole-grid palette equality axis is INDEPENDENT.
    icu = CONDITION_REGISTRY["input_color_uniform"]

    # equality fires AND icu fires (one source colour, output stays
    # in the input palette -- a permutation on a single changed cell
    # only works if the source colour also appears elsewhere
    # unchanged; we construct that case here).
    analysis = _pair(
        [0, 5], [0, 5],
        groups=[{
            "input_colors": [5],
            "output_colors": [0],
            "positions": [(0, 0)],
            "top_row": 0, "top_col": 0,
            "cell_count": 1,
        }],
        num_groups=1, total_changes=1,
    )
    p1 = {"pair_analyses": [analysis]}
    assert _matcher()(p1, {}) is True and icu(p1, {}) is True

    # equality fires but icu does NOT (no change cells means iter 14
    # is vacuously False per its docstring: requires len(groups) >=
    # 1).
    p2 = {"pair_analyses": [_pair([0, 1], [0, 1])]}
    assert _matcher()(p2, {}) is True and icu(p2, {}) is False


def test_recognized_conditions_includes_output_palette_equals_input() -> None:
    from agent.conditions import recognized_conditions
    patterns = {"pair_analyses": [_pair([0, 1, 2], [2, 0, 1])]}
    fired = recognized_conditions(patterns)
    assert MATCHER_NAME in fired, (
        f"{MATCHER_NAME!r} did not fire on a clearly-equal patterns "
        f"dict; got {fired!r}"
    )
    # And the iter-184 subset matcher must also fire (strict
    # refinement -- equality implies subset).
    assert "output_palette_subset_of_input" in fired, (
        "subset matcher must co-fire on a palette-equal patterns dict"
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
