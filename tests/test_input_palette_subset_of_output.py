"""
tests/test_input_palette_subset_of_output.py -- exercise the
iter-187 matcher ``agent.conditions.input_palette_subset_of_output``
(new in this iter).

Pins the matcher's contract per
``agent/conditions/input_palette_subset_of_output.py`` docstring:
every pair's ``set(input_palette) <= set(output_palette)`` on a
non-empty ``pair_analyses`` list with both palettes shaped as lists
of non-bool ints. The input-side mirror of iter-184's
``output_palette_subset_of_input`` and the fourth slot on the whole-
grid colour palette axis (alongside iter-185's equality matcher and
iter-186's disjoint matcher).

Runs without pytest:

    python tests/test_input_palette_subset_of_output.py

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


MATCHER_NAME = "input_palette_subset_of_output"


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

def test_returns_true_when_input_strictly_inside_output() -> None:
    # The canonical positive case: every input colour survives AND a
    # fresh output colour is added (palette-expansion).
    patterns = {"pair_analyses": [_pair([0, 1], [0, 1, 2, 3])]}
    assert _matcher()(patterns, {}) is True


def test_returns_true_on_palette_equality() -> None:
    # Equality is the special case where input ⊆ output AND output ⊆
    # input simultaneously. Strict implication: iter-185 equality ⇒
    # this matcher.
    patterns = {"pair_analyses": [_pair([0, 1, 2], [0, 1, 2])]}
    assert _matcher()(patterns, {}) is True


def test_returns_true_on_palette_permutation() -> None:
    # Permutation preserves the set; same set on both sides means
    # input ⊆ output trivially.
    patterns = {"pair_analyses": [_pair([0, 1, 2], [2, 0, 1])]}
    assert _matcher()(patterns, {}) is True


def test_returns_true_with_duplicates_in_palettes() -> None:
    # The contract is set-subset; duplicates within either list do
    # not change the set and must not break the gate.
    patterns = {"pair_analyses": [_pair([0, 0, 1], [1, 1, 0, 0, 5])]}
    assert _matcher()(patterns, {}) is True


def test_returns_true_when_single_color_input_present_in_output() -> None:
    # Input monochrome ⊆ output multi-colour, the single input colour
    # appears in the output.
    patterns = {"pair_analyses": [_pair([3], [3, 5, 7])]}
    assert _matcher()(patterns, {}) is True


def test_returns_true_across_multiple_pairs_all_satisfy() -> None:
    # Per-pair subset is independent across pairs; varying palettes
    # are allowed as long as each pair satisfies the gate.
    patterns = {
        "pair_analyses": [
            _pair([0, 1], [0, 1, 2]),
            _pair([3], [3, 4, 5]),
            _pair([6, 7], [6, 7, 8, 9]),
        ],
    }
    assert _matcher()(patterns, {}) is True


def test_returns_true_when_input_palette_empty() -> None:
    # Empty input palette: subset holds vacuously (empty ⊆ anything).
    # Mirrors iter 184 / 185 / 186's empty-palette posture.
    patterns = {"pair_analyses": [_pair([], [3, 4])]}
    assert _matcher()(patterns, {}) is True


def test_returns_true_when_both_palettes_empty() -> None:
    # Vacuously: empty ⊆ empty.
    patterns = {"pair_analyses": [_pair([], [])]}
    assert _matcher()(patterns, {}) is True


# ──────────────────────────────────────────────────────────────────────────
# Negative cases.
# ──────────────────────────────────────────────────────────────────────────

def test_returns_false_when_input_has_color_missing_from_output() -> None:
    # A single input colour absent from the output breaks the gate.
    patterns = {"pair_analyses": [_pair([0, 1, 2], [0, 1])]}
    assert _matcher()(patterns, {}) is False


def test_returns_false_on_palette_disjoint() -> None:
    # Iter-186's disjoint case -- mutually exclusive with this matcher
    # on any non-empty input palette.
    patterns = {"pair_analyses": [_pair([0, 1, 2], [3, 4, 5])]}
    assert _matcher()(patterns, {}) is False


def test_returns_false_on_palette_partial_overlap_input_side() -> None:
    # Partial overlap where some input colour is missing from the
    # output -- breaks subset.
    patterns = {"pair_analyses": [_pair([0, 1, 2], [1, 3, 4])]}
    assert _matcher()(patterns, {}) is False


def test_returns_false_when_output_palette_empty_but_input_nonempty() -> None:
    # Non-empty input ⊆ empty output is impossible.
    patterns = {"pair_analyses": [_pair([0, 1], [])]}
    assert _matcher()(patterns, {}) is False


def test_returns_false_when_any_pair_fails_the_gate() -> None:
    # Universal-over-pairs semantic: a single failing pair fails the
    # whole task.
    patterns = {
        "pair_analyses": [
            _pair([0, 1], [0, 1, 2]),
            _pair([4, 5], [4, 6]),  # offending pair (5 missing from output)
            _pair([7], [7, 8]),
        ],
    }
    assert _matcher()(patterns, {}) is False


def test_returns_false_on_empty_pair_analyses() -> None:
    # Fail-closed on empty input -- consistent with every other
    # matcher's posture (iters 1 / 13 / 17 / 20 / 22 / 33 / 182 / 183 /
    # 184 / 185 / 186).
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
            _pair([4, 5], [4, 5, 6]),
        ],
    }
    assert _matcher()(patterns, {}) is False


# ──────────────────────────────────────────────────────────────────────────
# Strict-type-gate cases.
# ──────────────────────────────────────────────────────────────────────────

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
    for bad in (None, 42, "oops", {"a": 1}, (0, 1), True, {0, 1}):
        analysis = _pair([0, 1], [0, 1, 2])
        analysis["output_palette"] = bad
        patterns = {"pair_analyses": [analysis]}
        assert _matcher()(patterns, {}) is False, (
            f"output_palette={bad!r} should not fire"
        )


def test_returns_false_when_input_palette_contains_bool() -> None:
    # Python bools are an int subclass; strict gate must reject them
    # (same posture as iter-182 / 183 dimensional matchers and the
    # iter-184 / 185 / 186 palette matchers).
    analysis = _pair([0, 1], [0, 1, 2])
    analysis["input_palette"] = [0, True, 1]
    patterns = {"pair_analyses": [analysis]}
    assert _matcher()(patterns, {}) is False


def test_returns_false_when_output_palette_contains_bool() -> None:
    analysis = _pair([0, 1], [0, 1, 2])
    analysis["output_palette"] = [False, 0, 1, 2]
    patterns = {"pair_analyses": [analysis]}
    assert _matcher()(patterns, {}) is False


def test_returns_false_when_palette_contains_non_int() -> None:
    analysis = _pair([0, 1], [0, 1, 2])
    analysis["input_palette"] = [0, "1", 2]
    patterns = {"pair_analyses": [analysis]}
    assert _matcher()(patterns, {}) is False

    analysis2 = _pair([0, 1], [0, 1, 2])
    analysis2["output_palette"] = [0.0, 1.0, 2.0]
    patterns2 = {"pair_analyses": [analysis2]}
    assert _matcher()(patterns2, {}) is False


# ──────────────────────────────────────────────────────────────────────────
# Behavioural-contract cases.
# ──────────────────────────────────────────────────────────────────────────

def test_is_side_effect_free_on_inputs() -> None:
    patterns = {
        "pair_analyses": [
            _pair([0, 1], [0, 1, 2]),
            _pair([3], [3, 4]),
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
    out_false = _matcher()({"pair_analyses": [_pair([0, 1, 2], [0, 1])]}, {})
    assert out_true is True, f"expected literal True, got {out_true!r}"
    assert out_false is False, f"expected literal False, got {out_false!r}"


def test_ignores_per_group_color_lists() -> None:
    # The matcher reads ONLY ``input_palette`` / ``output_palette``.
    # Per-group ``input_colors`` / ``output_colors`` on the change
    # cells are a different axis -- the matcher must ignore them.
    analysis = _pair(
        [0, 1], [0, 1, 2],
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
    analysis = _pair([0, 1], [0, 1, 2], input_height=7, input_width=9,
                     output_height=2, output_width=3, size_match=False)
    patterns = {"pair_analyses": [analysis]}
    assert _matcher()(patterns, {}) is True


# ──────────────────────────────────────────────────────────────────────────
# Orthogonality / co-fire matrix against the palette-axis siblings.
# ──────────────────────────────────────────────────────────────────────────

def test_co_fires_with_identity_transformation() -> None:
    # Iter 13 implies output palette equals input palette per pair,
    # which implies input ⊆ output. Strict implication: identity ⇒
    # this matcher. They MUST co-fire on a clean identity case.
    identity = CONDITION_REGISTRY["identity_transformation"]
    identity_pair = _pair([0, 1, 2], [0, 1, 2])
    patterns = {
        "grid_size_preserved": True,
        "pair_analyses": [identity_pair],
    }
    assert identity(patterns, {}) is True
    assert _matcher()(patterns, {}) is True


def test_co_fires_with_equality_strict_implication() -> None:
    # Iter 185 equality ⇒ both single-direction gates fire. They
    # MUST co-fire on a permutation case (equality fires; iter 184
    # also co-fires by symmetry; this matcher fires).
    equality = CONDITION_REGISTRY["output_palette_equals_input"]
    perm = _pair([0, 1, 2], [2, 0, 1])
    patterns = {"pair_analyses": [perm]}
    assert equality(patterns, {}) is True
    assert _matcher()(patterns, {}) is True


def test_asymmetry_against_equality_palette_expansion_case() -> None:
    # Palette-expansion fires this matcher but NOT equality
    # (output strictly contains input). The asymmetry is what
    # makes a distinct matcher slot necessary.
    equality = CONDITION_REGISTRY["output_palette_equals_input"]
    expand = _pair([0, 1], [0, 1, 2, 3])
    patterns = {"pair_analyses": [expand]}
    assert _matcher()(patterns, {}) is True
    assert equality(patterns, {}) is False


def test_asymmetry_against_iter184_subset_palette_expansion() -> None:
    # Palette-expansion (input ⊊ output) fires this matcher but NOT
    # iter-184 subset (output is NOT contained in input). The four-
    # cell partition's diagonal off-equality case.
    iter184 = CONDITION_REGISTRY["output_palette_subset_of_input"]
    expand = _pair([0, 1], [0, 1, 2, 3])
    patterns = {"pair_analyses": [expand]}
    assert _matcher()(patterns, {}) is True
    assert iter184(patterns, {}) is False


def test_asymmetry_against_iter184_erasure_case() -> None:
    # Erasure (output ⊊ input) fires iter-184 subset but NOT this
    # matcher (input is NOT contained in output -- the erased
    # colour is missing).
    iter184 = CONDITION_REGISTRY["output_palette_subset_of_input"]
    erase = _pair([0, 1, 2], [0, 1])
    patterns = {"pair_analyses": [erase]}
    assert _matcher()(patterns, {}) is False
    assert iter184(patterns, {}) is True


def test_iter184_and_this_matcher_co_fire_iff_equality_fires() -> None:
    # The two single-direction gates co-fire iff palettes are equal
    # as sets (iter-185 equality). Verify in both directions across
    # representative cases.
    iter184 = CONDITION_REGISTRY["output_palette_subset_of_input"]
    equality = CONDITION_REGISTRY["output_palette_equals_input"]

    # Equality case: all three fire.
    p_eq = {"pair_analyses": [_pair([0, 1, 2], [0, 1, 2])]}
    assert _matcher()(p_eq, {}) is True
    assert iter184(p_eq, {}) is True
    assert equality(p_eq, {}) is True

    # Permutation case (same set, reordered): all three fire.
    p_perm = {"pair_analyses": [_pair([0, 1, 2], [2, 0, 1])]}
    assert _matcher()(p_perm, {}) is True
    assert iter184(p_perm, {}) is True
    assert equality(p_perm, {}) is True

    # Erasure case: iter-184 fires, this matcher and equality do not.
    p_erase = {"pair_analyses": [_pair([0, 1, 2], [0, 1])]}
    assert _matcher()(p_erase, {}) is False
    assert iter184(p_erase, {}) is True
    assert equality(p_erase, {}) is False

    # Expansion case: this matcher fires, iter-184 and equality do not.
    p_exp = {"pair_analyses": [_pair([0, 1], [0, 1, 2])]}
    assert _matcher()(p_exp, {}) is True
    assert iter184(p_exp, {}) is False
    assert equality(p_exp, {}) is False

    # Disjoint case: neither single-direction gate fires on non-empty.
    p_disj = {"pair_analyses": [_pair([0, 1, 2], [3, 4, 5])]}
    assert _matcher()(p_disj, {}) is False
    assert iter184(p_disj, {}) is False
    assert equality(p_disj, {}) is False


def test_mutually_exclusive_with_iter186_disjoint_on_nonempty_input() -> None:
    # input ⊆ output AND output ∩ input = empty ⇒ input = empty.
    # The two matchers can only co-fire on empty-input cases. On any
    # non-empty input palette they are mutually exclusive.
    disjoint = CONDITION_REGISTRY["output_palette_disjoint_from_input"]

    # this matcher fires, disjoint does NOT (overlap is non-empty)
    p_subset = {"pair_analyses": [_pair([0, 1], [0, 1, 2, 3])]}
    assert _matcher()(p_subset, {}) is True
    assert disjoint(p_subset, {}) is False

    # disjoint fires, this matcher does NOT (non-empty input not in output)
    p_disj = {"pair_analyses": [_pair([0, 1, 2], [3, 4, 5])]}
    assert disjoint(p_disj, {}) is True
    assert _matcher()(p_disj, {}) is False


def test_co_fires_with_iter186_disjoint_only_on_empty_input() -> None:
    # The only joint co-fire of this matcher AND iter-186 disjoint
    # is when the input palette is empty (vacuously contained in AND
    # disjoint from any output palette).
    disjoint = CONDITION_REGISTRY["output_palette_disjoint_from_input"]
    patterns = {"pair_analyses": [_pair([], [3, 4, 5])]}
    assert _matcher()(patterns, {}) is True
    assert disjoint(patterns, {}) is True


def test_orthogonal_to_grid_size_preserved() -> None:
    # Whole-grid palette containment is orthogonal to the per-pair
    # input==output dim axis (the four-cell 2x2 co-fire table).
    gsp = CONDITION_REGISTRY["grid_size_preserved"]

    # subset + preserved -- both fire
    p1 = {
        "grid_size_preserved": True,
        "pair_analyses": [_pair([0, 1], [0, 1, 2])],
    }
    assert _matcher()(p1, {}) is True and gsp(p1, {}) is True

    # subset + changed -- only this matcher fires
    p2 = {
        "grid_size_preserved": False,
        "pair_analyses": [
            _pair([0, 1], [0, 1, 2], output_height=6, output_width=6,
                  size_match=False),
        ],
    }
    assert _matcher()(p2, {}) is True and gsp(p2, {}) is False

    # not-subset + preserved -- only preserved fires
    p3 = {
        "grid_size_preserved": True,
        "pair_analyses": [_pair([0, 1, 2], [0, 1])],
    }
    assert _matcher()(p3, {}) is False and gsp(p3, {}) is True

    # not-subset + changed -- neither fires
    p4 = {
        "grid_size_preserved": False,
        "pair_analyses": [
            _pair([0, 1, 2], [0, 1], output_height=6, output_width=6,
                  size_match=False),
        ],
    }
    assert _matcher()(p4, {}) is False and gsp(p4, {}) is False


def test_orthogonal_to_input_color_uniform() -> None:
    # iter 14 inspects change-cells' input colour uniformity. The
    # whole-grid palette containment axis is INDEPENDENT.
    icu = CONDITION_REGISTRY["input_color_uniform"]

    # this matcher fires AND icu fires (single change-cell source
    # colour, output palette contains every input colour and adds one
    # fresh colour).
    analysis = _pair(
        [0, 5], [0, 5, 3],
        groups=[{
            "input_colors": [5],
            "output_colors": [3],
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
    p2 = {"pair_analyses": [_pair([0, 1], [0, 1, 2])]}
    assert _matcher()(p2, {}) is True and icu(p2, {}) is False


def test_recognized_conditions_includes_input_palette_subset() -> None:
    from agent.conditions import recognized_conditions
    # Palette-expansion case: this matcher fires; iter-184 does NOT
    # (output is not contained in input); iter-185 does NOT (palettes
    # differ); iter-186 does NOT (intersection is non-empty).
    patterns = {"pair_analyses": [_pair([0, 1], [0, 1, 2, 3])]}
    fired = recognized_conditions(patterns)
    assert MATCHER_NAME in fired, (
        f"{MATCHER_NAME!r} did not fire on a clearly-expansion patterns "
        f"dict; got {fired!r}"
    )
    assert "output_palette_subset_of_input" not in fired, (
        "subset matcher must NOT co-fire on a palette-expansion case"
    )
    assert "output_palette_equals_input" not in fired, (
        "equality matcher must NOT co-fire on a palette-expansion case"
    )
    assert "output_palette_disjoint_from_input" not in fired, (
        "disjoint matcher must NOT co-fire on a palette-expansion case"
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
