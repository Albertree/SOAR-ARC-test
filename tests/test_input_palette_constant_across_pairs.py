"""
tests/test_input_palette_constant_across_pairs.py -- exercise the
iter-989 matcher
``agent.conditions.input_palette_constant_across_pairs`` (new in this
iter).

Pins the matcher's contract per
``agent/conditions/input_palette_constant_across_pairs.py`` docstring:
every pair shares the same ``set(input_palette)`` on a non-empty
``pair_analyses`` list with the palette shaped as a list of non-bool
ints. Recognition vocabulary axis: the palette-axis dual of iter 22's
``input_dimensions_constant`` on the input-side cross-pair constancy
quadrant.

Runs without pytest:

    python tests/test_input_palette_constant_across_pairs.py

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


MATCHER_NAME = "input_palette_constant_across_pairs"


def _matcher():
    return CONDITION_REGISTRY[MATCHER_NAME]


def _pair(input_palette, output_palette=None, **overrides):
    """A pair_analysis shaped like ExtractPatternOperator's output
    (iter-184 schema, with the palette fields)."""
    if output_palette is None:
        output_palette = list(input_palette)
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
# Smoke / membership.
# ──────────────────────────────────────────────────────────────────────────

def test_registered_in_global_registry() -> None:
    assert MATCHER_NAME in CONDITION_REGISTRY, (
        f"{MATCHER_NAME!r} not registered; got {sorted(CONDITION_REGISTRY)}"
    )


def test_matcher_is_callable() -> None:
    fn = _matcher()
    assert callable(fn), f"registered entry is not callable: {fn!r}"


def test_p5_at_least_83() -> None:
    # This matcher brings the registry to >= 83 (P5 monotone).
    assert len(CONDITION_REGISTRY) >= 83, (
        f"expected >= 83 matchers post-iter-989; got {len(CONDITION_REGISTRY)}"
    )


# ──────────────────────────────────────────────────────────────────────────
# Positive cases.
# ──────────────────────────────────────────────────────────────────────────

def test_single_pair_always_fires() -> None:
    patterns = {"pair_analyses": [_pair([0, 1, 2])]}
    assert _matcher()(patterns, {}) is True


def test_two_pairs_same_palette_fires() -> None:
    patterns = {"pair_analyses": [_pair([0, 1, 2]), _pair([0, 1, 2])]}
    assert _matcher()(patterns, {}) is True


def test_set_equal_under_different_list_order_fires() -> None:
    # frozenset equality is order-insensitive; the verdict must hold
    # regardless of how _analyze_pair orders the list.
    patterns = {"pair_analyses": [_pair([2, 0, 1]), _pair([1, 2, 0])]}
    assert _matcher()(patterns, {}) is True


def test_set_equal_with_duplicates_fires() -> None:
    # Duplicates within either list collapse under set semantics; the
    # cross-pair check ignores them.
    patterns = {"pair_analyses": [_pair([0, 0, 1, 1]), _pair([1, 0, 1, 0])]}
    assert _matcher()(patterns, {}) is True


def test_all_empty_palettes_fires() -> None:
    # Degenerate all-empty case: every pair shares the empty palette.
    patterns = {"pair_analyses": [_pair([]), _pair([])]}
    assert _matcher()(patterns, {}) is True


def test_singleton_palette_fires() -> None:
    patterns = {"pair_analyses": [_pair([5]), _pair([5])]}
    assert _matcher()(patterns, {}) is True


def test_three_pairs_all_same_palette_fires() -> None:
    patterns = {
        "pair_analyses": [_pair([0, 1, 2]), _pair([0, 1, 2]), _pair([0, 1, 2])]
    }
    assert _matcher()(patterns, {}) is True


# ──────────────────────────────────────────────────────────────────────────
# Negative cases (palette mismatch).
# ──────────────────────────────────────────────────────────────────────────

def test_two_pairs_disjoint_palettes_rejects() -> None:
    patterns = {"pair_analyses": [_pair([0, 1, 2]), _pair([3, 4, 5])]}
    assert _matcher()(patterns, {}) is False


def test_two_pairs_partial_overlap_rejects() -> None:
    patterns = {"pair_analyses": [_pair([0, 1, 2]), _pair([0, 1, 3])]}
    assert _matcher()(patterns, {}) is False


def test_subset_relation_rejects() -> None:
    # One palette is a strict subset of the other -- not equal.
    patterns = {"pair_analyses": [_pair([0, 1]), _pair([0, 1, 2])]}
    assert _matcher()(patterns, {}) is False


def test_one_empty_one_nonempty_rejects() -> None:
    patterns = {"pair_analyses": [_pair([]), _pair([0])]}
    assert _matcher()(patterns, {}) is False


def test_one_offending_pair_fails_the_gate() -> None:
    # Universal-over-pairs: one mismatched pair fails the whole task.
    patterns = {
        "pair_analyses": [
            _pair([0, 1, 2]),
            _pair([0, 1, 2]),
            _pair([0, 1, 9]),  # offending pair
            _pair([0, 1, 2]),
        ],
    }
    assert _matcher()(patterns, {}) is False


# ──────────────────────────────────────────────────────────────────────────
# Fail-closed paths.
# ──────────────────────────────────────────────────────────────────────────

def test_empty_pair_analyses_rejects() -> None:
    patterns = {"pair_analyses": []}
    assert _matcher()(patterns, {}) is False


def test_missing_pair_analyses_rejects() -> None:
    assert _matcher()({}, {}) is False


def test_non_list_pair_analyses_rejects() -> None:
    for bad in (None, 42, "oops", {"a": 1}, (), True):
        assert _matcher()({"pair_analyses": bad}, {}) is False, (
            f"pair_analyses={bad!r} should not fire"
        )


def test_non_dict_patterns_rejects() -> None:
    for bad in (None, [], "oops", 42):
        assert _matcher()(bad, {}) is False, f"patterns={bad!r} should not fire"  # type: ignore[arg-type]


def test_non_dict_analysis_rejects() -> None:
    patterns = {
        "pair_analyses": [_pair([0, 1]), "not-a-dict", _pair([0, 1])]
    }
    assert _matcher()(patterns, {}) is False


def test_missing_input_palette_rejects() -> None:
    analysis = _pair([0, 1])
    del analysis["input_palette"]
    patterns = {"pair_analyses": [analysis]}
    assert _matcher()(patterns, {}) is False


def test_non_list_input_palette_rejects() -> None:
    for bad in (None, 42, "oops", {"a": 1}, (0, 1), True, {0, 1}):
        analysis = _pair([0, 1])
        analysis["input_palette"] = bad
        patterns = {"pair_analyses": [analysis]}
        assert _matcher()(patterns, {}) is False, (
            f"input_palette={bad!r} should not fire"
        )


def test_bool_in_input_palette_rejects() -> None:
    # Python bools are an int subclass; strict gate must reject them
    # to keep the recognition layer from accepting placeholder sentinels.
    analysis = _pair([0, 1])
    analysis["input_palette"] = [0, True]
    patterns = {"pair_analyses": [analysis]}
    assert _matcher()(patterns, {}) is False


def test_non_int_in_input_palette_rejects() -> None:
    analysis = _pair([0, 1])
    analysis["input_palette"] = [0, "1"]
    patterns = {"pair_analyses": [analysis]}
    assert _matcher()(patterns, {}) is False

    analysis2 = _pair([0, 1])
    analysis2["input_palette"] = [0.0, 1]
    patterns2 = {"pair_analyses": [analysis2]}
    assert _matcher()(patterns2, {}) is False


# ──────────────────────────────────────────────────────────────────────────
# Behavioural contract.
# ──────────────────────────────────────────────────────────────────────────

def test_side_effect_free() -> None:
    patterns = {"pair_analyses": [_pair([0, 1]), _pair([1, 0])]}
    params = {"unused": 1}
    before_p = copy.deepcopy(patterns)
    before_q = copy.deepcopy(params)
    _matcher()(patterns, params)
    assert patterns == before_p, "matcher mutated patterns"
    assert params == before_q, "matcher mutated params"


def test_deterministic_across_repeats() -> None:
    patterns = {"pair_analyses": [_pair([0, 1, 2]), _pair([0, 1, 2])]}
    results = [_matcher()(patterns, {}) for _ in range(5)]
    assert len(set(results)) == 1, f"non-deterministic: {results}"


def test_returns_literal_boolean() -> None:
    # recognized_conditions filters on ``match(...) is True`` exactly.
    out_true = _matcher()({"pair_analyses": [_pair([0, 1])]}, {})
    out_false = _matcher()({"pair_analyses": [_pair([0]), _pair([1])]}, {})
    assert out_true is True, f"expected literal True, got {out_true!r}"
    assert out_false is False, f"expected literal False, got {out_false!r}"


def test_ignores_output_palette() -> None:
    # The matcher reads ONLY ``input_palette``. Different output palettes
    # must not affect the verdict.
    patterns = {
        "pair_analyses": [
            _pair([0, 1], output_palette=[2, 3]),
            _pair([0, 1], output_palette=[4, 5]),
        ],
    }
    assert _matcher()(patterns, {}) is True


def test_ignores_dimensional_fields() -> None:
    # Dim fields are orthogonal -- arbitrary dim values must not change
    # the verdict.
    patterns = {
        "pair_analyses": [
            _pair([0, 1], input_height=7, input_width=9, output_height=2,
                  output_width=3, size_match=False),
            _pair([0, 1], input_height=2, input_width=3, output_height=2,
                  output_width=3, size_match=True),
        ],
    }
    assert _matcher()(patterns, {}) is True


# ──────────────────────────────────────────────────────────────────────────
# Sibling-matcher relationships.
# ──────────────────────────────────────────────────────────────────────────

def test_independent_from_input_dimensions_constant() -> None:
    # Iter 22's dimensional dual. Both axes (palette vs dim) are
    # independent: a task can fire either, both, or neither.
    idc = CONDITION_REGISTRY["input_dimensions_constant"]

    # Both fire: same palette AND same dims.
    p_both = {"pair_analyses": [_pair([0, 1]), _pair([0, 1])]}
    assert _matcher()(p_both, {}) is True and idc(p_both, {}) is True

    # Only this matcher: same palette, different dims.
    p_pal_only = {
        "pair_analyses": [
            _pair([0, 1], input_height=3, input_width=3),
            _pair([0, 1], input_height=5, input_width=5),
        ],
    }
    assert _matcher()(p_pal_only, {}) is True and idc(p_pal_only, {}) is False

    # Only iter 22: same dims, different palette.
    p_dim_only = {
        "pair_analyses": [
            _pair([0, 1], input_height=3, input_width=3),
            _pair([2, 3], input_height=3, input_width=3),
        ],
    }
    assert _matcher()(p_dim_only, {}) is False and idc(p_dim_only, {}) is True


def test_independent_from_identity_transformation() -> None:
    # Identity says every pair internally preserves; says nothing about
    # cross-pair palette equality.
    identity = CONDITION_REGISTRY["identity_transformation"]

    # Identity fires (zero changes, size_match True) but palettes vary.
    p1 = {
        "pair_analyses": [
            _pair([0, 1]),
            _pair([2, 3]),
        ],
    }
    assert identity(p1, {}) is True
    assert _matcher()(p1, {}) is False

    # Identity fires AND palettes match -- both fire.
    p2 = {
        "pair_analyses": [
            _pair([0, 1]),
            _pair([0, 1]),
        ],
    }
    assert identity(p2, {}) is True
    assert _matcher()(p2, {}) is True


def test_strictly_refines_palette_intersection_count_constant() -> None:
    # Constant input palette ⇒ constant per-pair palette intersection
    # count (the intersection of two equal sets has the same size as
    # either). NOT a strict implication in the other direction (per-pair
    # intersection size can be constant without the cross-pair palette
    # being equal).
    isc = CONDITION_REGISTRY["palette_intersection_count_constant_across_pairs"]

    # Same palette across pairs: this matcher fires AND iter-isc fires
    # (constant set ⇒ constant intersection cardinality).
    p_same = {"pair_analyses": [_pair([0, 1, 2]), _pair([0, 1, 2])]}
    assert _matcher()(p_same, {}) is True
    assert isc(p_same, {}) is True


def test_recognized_conditions_includes_this_matcher() -> None:
    from agent.conditions import recognized_conditions
    patterns = {"pair_analyses": [_pair([0, 1, 2]), _pair([0, 1, 2])]}
    fired = recognized_conditions(patterns)
    assert MATCHER_NAME in fired, (
        f"{MATCHER_NAME!r} did not fire on a clearly constant-palette "
        f"patterns dict; got {fired!r}"
    )


def test_recognized_conditions_excludes_on_mismatch() -> None:
    from agent.conditions import recognized_conditions
    patterns = {"pair_analyses": [_pair([0, 1]), _pair([2, 3])]}
    fired = recognized_conditions(patterns)
    assert MATCHER_NAME not in fired, (
        f"{MATCHER_NAME!r} must NOT fire on cross-pair varying palettes; "
        f"got {fired!r}"
    )


def test_does_not_displace_adjacent_iter_matchers() -> None:
    # Adjacent-iter non-displacement: every iter-22/184/185/186/187/188/
    # 189/190 matcher remains in the registry alongside this new one.
    expected = {
        "input_dimensions_constant",
        "output_palette_subset_of_input",
        "output_palette_equals_input",
        "output_palette_disjoint_from_input",
        "input_palette_subset_of_output",
        "output_palette_count_exceeds_input_palette_count",
        "input_palette_count_exceeds_output_palette_count",
        "output_palette_is_permutation_of_input_palette",
        "input_palette_count_equals_output_palette_count",
        "identity_transformation",
    }
    missing = expected - set(CONDITION_REGISTRY)
    assert not missing, f"adjacent matchers missing post-iter-989: {missing!r}"


# ──────────────────────────────────────────────────────────────────────────
# Runner.
# ──────────────────────────────────────────────────────────────────────────

def _collect_tests():
    return [
        (name, obj)
        for name, obj in globals().items()
        if name.startswith("test_") and callable(obj)
    ]


def main() -> int:
    failures = []
    tests = _collect_tests()
    for name, fn in tests:
        try:
            fn()
        except AssertionError as e:
            failures.append((name, str(e) or repr(e), traceback.format_exc()))
        except Exception as e:  # pragma: no cover -- contract assertions
            failures.append((name, f"{type(e).__name__}: {e}", traceback.format_exc()))
    total = len(tests)
    passed = total - len(failures)
    print(f"{passed}/{total} tests passed")
    for name, msg, tb in failures:
        print(f"\nFAIL {name}: {msg}\n{tb}")
    return 0 if not failures else 1


if __name__ == "__main__":
    sys.exit(main())
