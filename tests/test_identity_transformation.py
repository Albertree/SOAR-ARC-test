"""
tests/test_identity_transformation.py -- exercise the iter-13 matcher
``agent.conditions.identity_transformation``.

Runs without pytest:

    python tests/test_identity_transformation.py

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


MATCHER_NAME = "identity_transformation"


def _matcher():
    return CONDITION_REGISTRY[MATCHER_NAME]


def _identity_pair() -> dict:
    """Minimal analysis dict matching ExtractPatternOperator's shape for a
    pair whose input and output are bit-identical."""
    return {
        "total_changes": 0,
        "num_groups": 0,
        "groups": [],
        "size_match": True,
    }


# ──────────────────────────────────────────────────────────────────────────
# Tests.
# ──────────────────────────────────────────────────────────────────────────

def test_registered_in_global_registry() -> None:
    assert MATCHER_NAME in CONDITION_REGISTRY, (
        f"{MATCHER_NAME!r} not registered; got {sorted(CONDITION_REGISTRY)}"
    )


def test_previous_matchers_still_registered() -> None:
    # Adjacent invariant — this iter must not displace iters 1 / 8 / 10.
    assert "grid_size_preserved" in CONDITION_REGISTRY, (
        "iter-1 matcher missing after iter-13 addition"
    )
    assert "consistent_color_mapping" in CONDITION_REGISTRY, (
        "iter-8 matcher missing after iter-13 addition"
    )
    assert "sequential_recoloring" in CONDITION_REGISTRY, (
        "iter-10 matcher missing after iter-13 addition"
    )


def test_four_distinct_matchers_registered() -> None:
    # P5 unit-monotone counter — there must be at least 4 entries now.
    assert len(CONDITION_REGISTRY) >= 4, (
        f"expected at least 4 entries, got {len(CONDITION_REGISTRY)}: "
        f"{sorted(CONDITION_REGISTRY)}"
    )


def test_matcher_is_callable() -> None:
    fn = _matcher()
    assert callable(fn), f"registered entry is not callable: {fn!r}"


def test_returns_true_on_single_identity_pair() -> None:
    patterns = {"pair_analyses": [_identity_pair()]}
    assert _matcher()(patterns, {}) is True


def test_returns_true_on_multiple_identity_pairs() -> None:
    patterns = {"pair_analyses": [_identity_pair(), _identity_pair(),
                                  _identity_pair()]}
    assert _matcher()(patterns, {}) is True


def test_returns_false_when_any_pair_has_changes() -> None:
    # All but one pair are identity; one has a single change group. The
    # matcher must reject the entire patterns dict — identity is an
    # all-pairs property.
    changed_pair = {
        "total_changes": 1,
        "num_groups": 1,
        "groups": [{"input_colors": [0], "output_colors": [3],
                    "top_row": 0, "top_col": 0, "cell_count": 1}],
        "size_match": True,
    }
    patterns = {"pair_analyses": [_identity_pair(), changed_pair]}
    assert _matcher()(patterns, {}) is False


def test_returns_false_when_any_pair_has_size_mismatch() -> None:
    # The overlap is unchanged (zero groups) but dimensions differ.
    # ExtractPatternOperator's diff only iterates min(h,w), so an
    # all-zeros 3x3 input vs an all-zeros 5x5 output would yield
    # len(groups) == 0 with size_match == False. That is NOT identity
    # — output has cells not present in input — and the matcher must
    # reject it.
    overlap_match_size_mismatch = {
        "total_changes": 0,
        "num_groups": 0,
        "groups": [],
        "size_match": False,
    }
    patterns = {"pair_analyses": [overlap_match_size_mismatch]}
    assert _matcher()(patterns, {}) is False


def test_returns_false_when_size_match_is_truthy_but_not_true() -> None:
    # Strict `is True` on size_match — mirrors the recognised_conditions
    # contract that matchers reject truthy-but-not-True returns.
    for truthy in (1, "yes", [1], {"a": 1}):
        analysis = {
            "total_changes": 0,
            "num_groups": 0,
            "groups": [],
            "size_match": truthy,
        }
        patterns = {"pair_analyses": [analysis]}
        assert _matcher()(patterns, {}) is False, (
            f"size_match={truthy!r} (truthy-not-True) should not fire"
        )


def test_returns_false_on_empty_pair_analyses() -> None:
    assert _matcher()({"pair_analyses": []}, {}) is False


def test_returns_false_on_missing_pair_analyses() -> None:
    assert _matcher()({}, {}) is False


def test_returns_false_on_non_dict_patterns() -> None:
    assert _matcher()(None, {}) is False         # type: ignore[arg-type]
    assert _matcher()([], {}) is False           # type: ignore[arg-type]
    assert _matcher()("oops", {}) is False       # type: ignore[arg-type]
    assert _matcher()(42, {}) is False           # type: ignore[arg-type]


def test_returns_false_on_malformed_analysis_entry() -> None:
    # A non-dict entry in pair_analyses fails fast.
    assert _matcher()({"pair_analyses": [None]}, {}) is False
    assert _matcher()({"pair_analyses": ["string"]}, {}) is False
    assert _matcher()({"pair_analyses": [42]}, {}) is False


def test_returns_false_when_groups_field_missing() -> None:
    # Defensive: if `groups` is absent (or non-list) the matcher cannot
    # confirm "zero changes" — it must reject, not assume.
    analysis_missing_groups = {"size_match": True, "num_groups": 0}
    patterns = {"pair_analyses": [analysis_missing_groups]}
    assert _matcher()(patterns, {}) is False


def test_returns_false_when_groups_is_non_list() -> None:
    for bad in (None, "x", 0, {"k": "v"}):
        analysis = {"size_match": True, "groups": bad}
        patterns = {"pair_analyses": [analysis]}
        assert _matcher()(patterns, {}) is False, (
            f"groups={bad!r} (non-list) should not fire"
        )


def test_returns_false_when_groups_non_empty_even_if_size_matches() -> None:
    # Any change group disqualifies, even if size_match is True.
    analysis = {
        "size_match": True,
        "groups": [{"input_colors": [0], "output_colors": [0],
                    "top_row": 0, "top_col": 0, "cell_count": 1}],
    }
    patterns = {"pair_analyses": [analysis]}
    assert _matcher()(patterns, {}) is False


def test_is_side_effect_free_on_inputs() -> None:
    patterns = {"pair_analyses": [_identity_pair(), _identity_pair()]}
    params = {"unused": 1}
    before_p = copy.deepcopy(patterns)
    before_q = copy.deepcopy(params)
    _matcher()(patterns, params)
    assert patterns == before_p, "matcher mutated patterns"
    assert params == before_q, "matcher mutated params"


def test_is_deterministic_across_repeats() -> None:
    patterns = {"pair_analyses": [_identity_pair(), _identity_pair()]}
    results = [_matcher()(patterns, {}) for _ in range(5)]
    assert len(set(results)) == 1, f"non-deterministic outputs: {results}"


def test_mutually_exclusive_with_consistent_color_mapping() -> None:
    # An all-identity patterns dict must fire identity_transformation and
    # NOT consistent_color_mapping. Iter 8's matcher explicitly returns
    # False on empty changed-cell sets — this test enforces the split.
    patterns = {"pair_analyses": [_identity_pair(), _identity_pair()]}
    assert _matcher()(patterns, {}) is True
    ccm = CONDITION_REGISTRY["consistent_color_mapping"]
    assert ccm(patterns, {}) is False, (
        "consistent_color_mapping must defer to identity_transformation "
        "on zero-change patterns (per its iter-8 docstring TBD note)"
    )


def test_mutually_exclusive_with_sequential_recoloring() -> None:
    # Identity must NOT fire sequential_recoloring either — iter 10's
    # matcher requires non-zero groups per pair.
    patterns = {"pair_analyses": [_identity_pair(), _identity_pair()]}
    assert _matcher()(patterns, {}) is True
    sr = CONDITION_REGISTRY["sequential_recoloring"]
    assert sr(patterns, {}) is False, (
        "sequential_recoloring must not fire on all-identity patterns "
        "— it requires non-zero groups per pair"
    )


def test_co_fires_with_grid_size_preserved_on_identity_patterns() -> None:
    # Identity implies dimension preservation by construction (per-pair
    # size_match == True). grid_size_preserved fires when the top-level
    # flag is True AND every per-pair size_match is True. So an
    # identity-shaped patterns dict that also sets the top-level flag
    # must fire BOTH matchers — they are layered, not competitive.
    patterns = {
        "grid_size_preserved": True,
        "pair_analyses": [_identity_pair(), _identity_pair()],
    }
    assert _matcher()(patterns, {}) is True
    gsp = CONDITION_REGISTRY["grid_size_preserved"]
    assert gsp(patterns, {}) is True, (
        "grid_size_preserved must still fire on identity patterns — "
        "identity is a strict refinement, not a replacement"
    )


def test_end_to_end_agreement_with_extract_pattern_shape() -> None:
    # The shape produced by ExtractPatternOperator for a pair where
    # input == output (cell-for-cell) is _analyze_pair returning
    # {"total_changes": 0, "num_groups": 0, "groups": [], "size_match": True}.
    # Construct that exact shape and confirm the matcher fires.
    pair_from_extract_pattern_for_identity = {
        "total_changes": 0,
        "num_groups": 0,
        "groups": [],
        "size_match": True,
    }
    patterns = {
        "grid_size_preserved": True,
        "pair_analyses": [pair_from_extract_pattern_for_identity,
                          pair_from_extract_pattern_for_identity],
    }
    assert _matcher()(patterns, {}) is True


# ──────────────────────────────────────────────────────────────────────────
# Driver.
# ──────────────────────────────────────────────────────────────────────────

def _run_all() -> int:
    tests = [
        test_registered_in_global_registry,
        test_previous_matchers_still_registered,
        test_four_distinct_matchers_registered,
        test_matcher_is_callable,
        test_returns_true_on_single_identity_pair,
        test_returns_true_on_multiple_identity_pairs,
        test_returns_false_when_any_pair_has_changes,
        test_returns_false_when_any_pair_has_size_mismatch,
        test_returns_false_when_size_match_is_truthy_but_not_true,
        test_returns_false_on_empty_pair_analyses,
        test_returns_false_on_missing_pair_analyses,
        test_returns_false_on_non_dict_patterns,
        test_returns_false_on_malformed_analysis_entry,
        test_returns_false_when_groups_field_missing,
        test_returns_false_when_groups_is_non_list,
        test_returns_false_when_groups_non_empty_even_if_size_matches,
        test_is_side_effect_free_on_inputs,
        test_is_deterministic_across_repeats,
        test_mutually_exclusive_with_consistent_color_mapping,
        test_mutually_exclusive_with_sequential_recoloring,
        test_co_fires_with_grid_size_preserved_on_identity_patterns,
        test_end_to_end_agreement_with_extract_pattern_shape,
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
    n = _run_all()
    sys.exit(1 if n else 0)
