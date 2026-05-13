"""
tests/test_grid_size_changed.py -- exercise the iter-17 matcher
``agent.conditions.grid_size_changed``.

Runs without pytest:

    python tests/test_grid_size_changed.py

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


MATCHER_NAME = "grid_size_changed"


def _matcher():
    return CONDITION_REGISTRY[MATCHER_NAME]


def _changed_pair() -> dict:
    """A pair_analysis dict shaped like ExtractPatternOperator's output for
    a pair whose input and output have different dimensions (size_match is
    the literal Boolean False)."""
    return {
        "total_changes": 0,
        "num_groups": 0,
        "groups": [],
        "size_match": False,
    }


def _preserved_pair() -> dict:
    """A pair_analysis dict for a pair whose dimensions match (size_match is
    the literal Boolean True). The matcher must NOT fire on a patterns dict
    composed only of these."""
    return {
        "total_changes": 0,
        "num_groups": 0,
        "groups": [],
        "size_match": True,
    }


def _preserved_pair_with_changes() -> dict:
    """Dimension-preserved pair that does include change groups -- still
    must NOT fire ``grid_size_changed`` because ``size_match`` is True."""
    return {
        "total_changes": 1,
        "num_groups": 1,
        "groups": [{"input_colors": [0], "output_colors": [3],
                    "top_row": 0, "top_col": 0, "cell_count": 1}],
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
    # Adjacent invariant -- this iter must not displace iters 1 / 8 / 10 / 13.
    for prior in ("grid_size_preserved", "consistent_color_mapping",
                  "sequential_recoloring", "identity_transformation"):
        assert prior in CONDITION_REGISTRY, (
            f"prior matcher {prior!r} missing after iter-17 addition"
        )


def test_five_distinct_matchers_registered() -> None:
    # P5 unit-monotone counter -- there must be at least 5 entries now.
    assert len(CONDITION_REGISTRY) >= 5, (
        f"expected at least 5 entries, got {len(CONDITION_REGISTRY)}: "
        f"{sorted(CONDITION_REGISTRY)}"
    )


def test_matcher_is_callable() -> None:
    fn = _matcher()
    assert callable(fn), f"registered entry is not callable: {fn!r}"


def test_returns_true_on_single_size_change_pair() -> None:
    patterns = {"pair_analyses": [_changed_pair()]}
    assert _matcher()(patterns, {}) is True


def test_returns_true_on_all_pairs_size_changed() -> None:
    patterns = {"pair_analyses": [_changed_pair(), _changed_pair(),
                                  _changed_pair()]}
    assert _matcher()(patterns, {}) is True


def test_returns_true_when_only_one_pair_size_changed() -> None:
    # Existential semantic: a single dimension-changed pair is enough to
    # take the whole task out of the "size preserved" regime.
    patterns = {"pair_analyses": [_preserved_pair(), _changed_pair()]}
    assert _matcher()(patterns, {}) is True


def test_returns_false_when_every_pair_size_preserved() -> None:
    patterns = {"pair_analyses": [_preserved_pair(), _preserved_pair()]}
    assert _matcher()(patterns, {}) is False


def test_returns_false_when_every_pair_size_preserved_with_changes() -> None:
    # Changed colours within preserved dimensions -- still must NOT fire.
    # Recolour-style tasks live under ``grid_size_preserved``, not under
    # this matcher.
    patterns = {"pair_analyses": [_preserved_pair_with_changes(),
                                  _preserved_pair_with_changes()]}
    assert _matcher()(patterns, {}) is False


def test_returns_false_on_empty_pair_analyses() -> None:
    assert _matcher()({"pair_analyses": []}, {}) is False


def test_returns_false_on_missing_pair_analyses() -> None:
    assert _matcher()({}, {}) is False


def test_returns_false_on_non_dict_patterns() -> None:
    assert _matcher()(None, {}) is False         # type: ignore[arg-type]
    assert _matcher()([], {}) is False           # type: ignore[arg-type]
    assert _matcher()("oops", {}) is False       # type: ignore[arg-type]
    assert _matcher()(42, {}) is False           # type: ignore[arg-type]


def test_returns_false_on_non_list_pair_analyses() -> None:
    for bad in ({"k": "v"}, "string", 0):
        assert _matcher()({"pair_analyses": bad}, {}) is False, (
            f"pair_analyses={bad!r} (non-list) should not fire"
        )


def test_returns_false_on_malformed_analysis_entry() -> None:
    # A non-dict entry in pair_analyses fails fast (mirrors
    # identity_transformation's fail-closed contract).
    assert _matcher()({"pair_analyses": [None]}, {}) is False
    assert _matcher()({"pair_analyses": ["string"]}, {}) is False
    assert _matcher()({"pair_analyses": [42]}, {}) is False


def test_returns_false_when_size_match_missing() -> None:
    # If the extractor produced an analysis without size_match, we cannot
    # assert "size changed" -- fail-closed, do not assume.
    analysis_missing = {"total_changes": 0, "num_groups": 0, "groups": []}
    patterns = {"pair_analyses": [analysis_missing]}
    assert _matcher()(patterns, {}) is False


def test_returns_false_when_size_match_is_falsy_but_not_False() -> None:
    # Strict ``is False`` on size_match -- mirrors iter 13's strict
    # ``is True`` posture on the symmetric matcher. None / 0 / "" / [] are
    # *not* a Boolean False signal; they are malformed.
    for falsy in (None, 0, "", [], {}):
        analysis = {"total_changes": 0, "num_groups": 0, "groups": [],
                    "size_match": falsy}
        patterns = {"pair_analyses": [analysis]}
        assert _matcher()(patterns, {}) is False, (
            f"size_match={falsy!r} (falsy-not-False) should not fire"
        )


def test_returns_false_when_size_match_is_truthy_but_not_True() -> None:
    # The other half of the strict-Boolean contract: ``size_match=1`` is
    # *not* True. The matcher must fail-closed there too. (One such value
    # in a single pair fails the whole patterns dict.)
    for truthy in (1, "yes", [1], {"a": 1}):
        analysis = {"total_changes": 0, "num_groups": 0, "groups": [],
                    "size_match": truthy}
        patterns = {"pair_analyses": [analysis]}
        assert _matcher()(patterns, {}) is False, (
            f"size_match={truthy!r} (truthy-not-True) should not fire"
        )


def test_is_side_effect_free_on_inputs() -> None:
    patterns = {"pair_analyses": [_changed_pair(), _preserved_pair()]}
    params = {"unused": 1}
    before_p = copy.deepcopy(patterns)
    before_q = copy.deepcopy(params)
    _matcher()(patterns, params)
    assert patterns == before_p, "matcher mutated patterns"
    assert params == before_q, "matcher mutated params"


def test_is_deterministic_across_repeats() -> None:
    patterns = {"pair_analyses": [_changed_pair(), _changed_pair()]}
    results = [_matcher()(patterns, {}) for _ in range(5)]
    assert len(set(results)) == 1, f"non-deterministic outputs: {results}"


def test_mutually_exclusive_with_grid_size_preserved() -> None:
    # The two matchers partition the dimensional axis on any non-empty,
    # well-formed pair_analyses list. A patterns dict that fires
    # grid_size_changed must NOT fire grid_size_preserved, and vice versa.
    changed_patterns = {
        "grid_size_preserved": False,
        "pair_analyses": [_changed_pair(), _changed_pair()],
    }
    preserved_patterns = {
        "grid_size_preserved": True,
        "pair_analyses": [_preserved_pair(), _preserved_pair()],
    }
    gsp = CONDITION_REGISTRY["grid_size_preserved"]

    assert _matcher()(changed_patterns, {}) is True
    assert gsp(changed_patterns, {}) is False, (
        "grid_size_preserved must not fire on a patterns dict with any "
        "size_match=False pair"
    )

    assert _matcher()(preserved_patterns, {}) is False, (
        "grid_size_changed must not fire on all-preserved patterns"
    )
    assert gsp(preserved_patterns, {}) is True


def test_mutually_exclusive_with_identity_transformation() -> None:
    # identity_transformation requires all pairs to have size_match=True
    # AND zero change groups. grid_size_changed requires at least one
    # size_match=False. They cannot co-fire.
    identity_patterns = {
        "grid_size_preserved": True,
        "pair_analyses": [
            {"size_match": True, "num_groups": 0, "groups": []},
            {"size_match": True, "num_groups": 0, "groups": []},
        ],
    }
    changed_patterns = {
        "grid_size_preserved": False,
        "pair_analyses": [_changed_pair(), _changed_pair()],
    }
    identity = CONDITION_REGISTRY["identity_transformation"]

    assert _matcher()(identity_patterns, {}) is False
    assert identity(identity_patterns, {}) is True

    assert _matcher()(changed_patterns, {}) is True
    assert identity(changed_patterns, {}) is False


def test_can_cofire_with_consistent_color_mapping() -> None:
    # Orthogonality on the colour-content axis: an existing test fixture
    # in tests/test_recognized_conditions.py drives a patterns dict where
    # every pair has size_match=False but the change groups still form a
    # consistent 1:1 colour mapping. Both matchers must fire.
    patterns = {
        "grid_size_preserved": False,
        "pair_analyses": [
            {
                "size_match": False,
                "num_groups": 2,
                "groups": [
                    {"input_colors": [0], "output_colors": [3],
                     "top_row": 0, "top_col": 0},
                    {"input_colors": [5], "output_colors": [7],
                     "top_row": 1, "top_col": 0},
                ],
            },
            {
                "size_match": False,
                "num_groups": 2,
                "groups": [
                    {"input_colors": [0], "output_colors": [3],
                     "top_row": 0, "top_col": 0},
                    {"input_colors": [5], "output_colors": [7],
                     "top_row": 1, "top_col": 0},
                ],
            },
        ],
    }
    ccm = CONDITION_REGISTRY["consistent_color_mapping"]
    assert _matcher()(patterns, {}) is True, (
        "grid_size_changed must fire when every pair has size_match=False"
    )
    assert ccm(patterns, {}) is True, (
        "consistent_color_mapping is dimension-agnostic; it must still fire"
    )


def test_end_to_end_agreement_with_extract_pattern_shape() -> None:
    # ExtractPatternOperator._analyze_pair always emits size_match as the
    # literal result of a chained dimension comparison -- a Boolean. For a
    # pair where output is taller than input AND overlap is unchanged, the
    # shape is exactly the dict below. The matcher must fire.
    overlap_match_size_mismatch = {
        "total_changes": 0,
        "num_groups": 0,
        "groups": [],
        "size_match": False,
    }
    patterns = {
        "grid_size_preserved": False,
        "pair_analyses": [overlap_match_size_mismatch,
                          overlap_match_size_mismatch],
    }
    assert _matcher()(patterns, {}) is True


def test_returned_value_is_boolean_not_truthy() -> None:
    # Mirrors the strict-`is True` contract from recognized_conditions:
    # downstream consumers in agent.conditions filter on `match(...) is
    # True` exactly, so the matcher must return bools, not truthy ints.
    patterns_change = {"pair_analyses": [_changed_pair()]}
    patterns_no_change = {"pair_analyses": [_preserved_pair()]}
    out_change = _matcher()(patterns_change, {})
    out_no_change = _matcher()(patterns_no_change, {})
    assert out_change is True, f"expected literal True, got {out_change!r}"
    assert out_no_change is False, (
        f"expected literal False, got {out_no_change!r}"
    )


# ──────────────────────────────────────────────────────────────────────────
# Driver.
# ──────────────────────────────────────────────────────────────────────────

def _run_all() -> int:
    tests = [
        test_registered_in_global_registry,
        test_previous_matchers_still_registered,
        test_five_distinct_matchers_registered,
        test_matcher_is_callable,
        test_returns_true_on_single_size_change_pair,
        test_returns_true_on_all_pairs_size_changed,
        test_returns_true_when_only_one_pair_size_changed,
        test_returns_false_when_every_pair_size_preserved,
        test_returns_false_when_every_pair_size_preserved_with_changes,
        test_returns_false_on_empty_pair_analyses,
        test_returns_false_on_missing_pair_analyses,
        test_returns_false_on_non_dict_patterns,
        test_returns_false_on_non_list_pair_analyses,
        test_returns_false_on_malformed_analysis_entry,
        test_returns_false_when_size_match_missing,
        test_returns_false_when_size_match_is_falsy_but_not_False,
        test_returns_false_when_size_match_is_truthy_but_not_True,
        test_is_side_effect_free_on_inputs,
        test_is_deterministic_across_repeats,
        test_mutually_exclusive_with_grid_size_preserved,
        test_mutually_exclusive_with_identity_transformation,
        test_can_cofire_with_consistent_color_mapping,
        test_end_to_end_agreement_with_extract_pattern_shape,
        test_returned_value_is_boolean_not_truthy,
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
