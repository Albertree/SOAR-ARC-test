"""
tests/test_grid_size_preserved.py -- exercise the iter-1 foundational
matcher ``agent.conditions.grid_size_preserved``.

This is the oldest matcher in the registry; until iter 181 it was the
only one without a dedicated test file (a coverage gap surfaced by the
matcher-vs-test-file diff). The registry-membership smoke check in
``tests/test_recognized_conditions.py`` covered presence, but none of
the behavioural contract -- the top-level flag short-circuit, the
per-pair ``size_match`` conjunction, the fail-closed posture on
malformed inputs, the partition relationship against
``grid_size_changed`` (iter 17) and the co-fire pattern with
``identity_transformation`` (iter 13) -- was pinned anywhere.

Runs without pytest:

    python tests/test_grid_size_preserved.py

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


MATCHER_NAME = "grid_size_preserved"


def _matcher():
    return CONDITION_REGISTRY[MATCHER_NAME]


def _preserved_pair() -> dict:
    """A pair_analysis dict shaped like ExtractPatternOperator's output
    for a pair whose input and output have matching dimensions
    (size_match is the literal Boolean True)."""
    return {
        "total_changes": 0,
        "num_groups": 0,
        "groups": [],
        "size_match": True,
    }


def _changed_pair() -> dict:
    """A pair_analysis dict for a pair whose dimensions differ
    (size_match is the literal Boolean False). The matcher must NOT
    fire on a patterns dict containing any of these."""
    return {
        "total_changes": 0,
        "num_groups": 0,
        "groups": [],
        "size_match": False,
    }


def _preserved_pair_with_changes() -> dict:
    """Dimension-preserved pair that does include change groups -- the
    matcher must still fire because ``grid_size_preserved`` is
    indifferent to the colour-content axis (iter-8 separation of
    concerns: dimensional matchers do not piggyback on colour content,
    and vice versa)."""
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


def test_matcher_is_callable() -> None:
    fn = _matcher()
    assert callable(fn), f"registered entry is not callable: {fn!r}"


def test_returns_true_on_single_preserved_pair() -> None:
    patterns = {
        "grid_size_preserved": True,
        "pair_analyses": [_preserved_pair()],
    }
    assert _matcher()(patterns, {}) is True


def test_returns_true_on_all_pairs_preserved() -> None:
    patterns = {
        "grid_size_preserved": True,
        "pair_analyses": [_preserved_pair(), _preserved_pair(),
                          _preserved_pair()],
    }
    assert _matcher()(patterns, {}) is True


def test_returns_true_when_preserved_pairs_have_change_groups() -> None:
    # Recolour-style tasks live UNDER grid_size_preserved (same shape,
    # changed colours). The matcher must fire because the dimensional
    # axis is preserved; the colour-content axis is for other matchers.
    patterns = {
        "grid_size_preserved": True,
        "pair_analyses": [_preserved_pair_with_changes(),
                          _preserved_pair_with_changes()],
    }
    assert _matcher()(patterns, {}) is True


def test_returns_false_when_any_pair_size_changed() -> None:
    # Universal semantic across pairs: a single dimension-changed pair
    # takes the whole task out of the "size preserved" regime, mirroring
    # the per-pair conjunction in the matcher's contract.
    patterns = {
        "grid_size_preserved": True,
        "pair_analyses": [_preserved_pair(), _changed_pair()],
    }
    assert _matcher()(patterns, {}) is False


def test_returns_false_when_every_pair_size_changed() -> None:
    patterns = {
        "grid_size_preserved": False,
        "pair_analyses": [_changed_pair(), _changed_pair()],
    }
    assert _matcher()(patterns, {}) is False


def test_returns_false_when_top_level_flag_false() -> None:
    # The top-level flag short-circuits before the per-pair scan.
    # ExtractPatternOperator flips the flag when any pair's dimensions
    # differ, so this is the canonical "no" path.
    patterns = {
        "grid_size_preserved": False,
        "pair_analyses": [_preserved_pair(), _preserved_pair()],
    }
    assert _matcher()(patterns, {}) is False


def test_returns_false_when_top_level_flag_missing() -> None:
    # Default-False on the flag -- mirrors the fail-closed posture on
    # other dimensional matchers when the upstream extractor omits a
    # required key.
    patterns = {"pair_analyses": [_preserved_pair()]}
    assert _matcher()(patterns, {}) is False


def test_returns_false_on_empty_pair_analyses() -> None:
    # The per-pair check guards against an empty list -- without it the
    # `all(...)` over an empty iterable would vacuously return True and
    # the matcher would fire on a degenerate patterns dict.
    patterns = {"grid_size_preserved": True, "pair_analyses": []}
    assert _matcher()(patterns, {}) is False


def test_returns_false_on_missing_pair_analyses() -> None:
    patterns = {"grid_size_preserved": True}
    assert _matcher()(patterns, {}) is False


def test_returns_false_on_non_dict_patterns() -> None:
    assert _matcher()(None, {}) is False         # type: ignore[arg-type]
    assert _matcher()([], {}) is False           # type: ignore[arg-type]
    assert _matcher()("oops", {}) is False       # type: ignore[arg-type]
    assert _matcher()(42, {}) is False           # type: ignore[arg-type]


def test_returns_false_when_size_match_missing() -> None:
    # If an analysis omits size_match, we cannot assert "size preserved"
    # -- fail-closed, do not assume.
    analysis_missing = {"total_changes": 0, "num_groups": 0, "groups": []}
    patterns = {
        "grid_size_preserved": True,
        "pair_analyses": [analysis_missing],
    }
    assert _matcher()(patterns, {}) is False


def test_returns_false_when_size_match_is_falsy() -> None:
    # Any falsy size_match disqualifies the pair. The matcher is
    # documented to use ``bool(...)`` for the per-pair check (permissive
    # truthy posture), but every falsy value fails the conjunction.
    for falsy in (None, 0, "", [], {}, False):
        analysis = {"total_changes": 0, "num_groups": 0, "groups": [],
                    "size_match": falsy}
        patterns = {
            "grid_size_preserved": True,
            "pair_analyses": [analysis],
        }
        assert _matcher()(patterns, {}) is False, (
            f"size_match={falsy!r} (falsy) should not fire"
        )


def test_is_side_effect_free_on_inputs() -> None:
    patterns = {
        "grid_size_preserved": True,
        "pair_analyses": [_preserved_pair(), _changed_pair()],
    }
    params = {"unused": 1}
    before_p = copy.deepcopy(patterns)
    before_q = copy.deepcopy(params)
    _matcher()(patterns, params)
    assert patterns == before_p, "matcher mutated patterns"
    assert params == before_q, "matcher mutated params"


def test_is_deterministic_across_repeats() -> None:
    patterns = {
        "grid_size_preserved": True,
        "pair_analyses": [_preserved_pair(), _preserved_pair()],
    }
    results = [_matcher()(patterns, {}) for _ in range(5)]
    assert len(set(results)) == 1, f"non-deterministic outputs: {results}"


def test_mutually_exclusive_with_grid_size_changed() -> None:
    # The two matchers partition the dimensional axis on any non-empty,
    # well-formed pair_analyses list (test_grid_size_changed.py asserts
    # the same partition from the other side -- this test pins it from
    # the grid_size_preserved side so the contract is symmetric).
    preserved_patterns = {
        "grid_size_preserved": True,
        "pair_analyses": [_preserved_pair(), _preserved_pair()],
    }
    changed_patterns = {
        "grid_size_preserved": False,
        "pair_analyses": [_changed_pair(), _changed_pair()],
    }
    gsc = CONDITION_REGISTRY["grid_size_changed"]

    assert _matcher()(preserved_patterns, {}) is True
    assert gsc(preserved_patterns, {}) is False, (
        "grid_size_changed must not fire on all-preserved patterns"
    )

    assert _matcher()(changed_patterns, {}) is False, (
        "grid_size_preserved must not fire when any pair size_match=False"
    )
    assert gsc(changed_patterns, {}) is True


def test_can_cofire_with_identity_transformation() -> None:
    # identity_transformation is strictly stricter (same shape AND zero
    # change groups). Any patterns dict that fires identity must also
    # fire grid_size_preserved -- the implication captured in iter 13's
    # docstring.
    identity_patterns = {
        "grid_size_preserved": True,
        "pair_analyses": [
            {"size_match": True, "num_groups": 0, "groups": []},
            {"size_match": True, "num_groups": 0, "groups": []},
        ],
    }
    identity = CONDITION_REGISTRY["identity_transformation"]

    assert _matcher()(identity_patterns, {}) is True
    assert identity(identity_patterns, {}) is True, (
        "identity_transformation must fire on its canonical pattern; the "
        "co-fire is the documented strict-refinement relationship"
    )


def test_does_not_imply_identity_transformation() -> None:
    # The reverse direction does NOT hold: grid_size_preserved can fire
    # on a patterns dict with change groups, but identity_transformation
    # cannot. Documents the asymmetry of the strict-refinement
    # relationship from iter 13's docstring.
    preserved_with_changes = {
        "grid_size_preserved": True,
        "pair_analyses": [_preserved_pair_with_changes(),
                          _preserved_pair_with_changes()],
    }
    identity = CONDITION_REGISTRY["identity_transformation"]

    assert _matcher()(preserved_with_changes, {}) is True
    assert identity(preserved_with_changes, {}) is False, (
        "identity_transformation must not fire when any pair has change "
        "groups"
    )


def test_end_to_end_agreement_with_extract_pattern_shape() -> None:
    # ExtractPatternOperator._analyze_pair emits size_match as the
    # literal result of a chained dimension comparison -- always a
    # Boolean. For a pair where input and output share dimensions, the
    # shape is exactly the dict below.
    same_shape_pair = {
        "total_changes": 0,
        "num_groups": 0,
        "groups": [],
        "size_match": True,
    }
    patterns = {
        "grid_size_preserved": True,
        "pair_analyses": [same_shape_pair, same_shape_pair],
    }
    assert _matcher()(patterns, {}) is True


def test_returned_value_is_boolean_not_truthy() -> None:
    # recognized_conditions filters on ``match(...) is True`` exactly,
    # so the matcher must return literal Booleans -- not truthy ints
    # from a stray ``and``/``or`` short-circuit.
    patterns_true = {
        "grid_size_preserved": True,
        "pair_analyses": [_preserved_pair()],
    }
    patterns_false = {
        "grid_size_preserved": True,
        "pair_analyses": [_changed_pair()],
    }
    out_true = _matcher()(patterns_true, {})
    out_false = _matcher()(patterns_false, {})
    assert out_true is True, f"expected literal True, got {out_true!r}"
    assert out_false is False, f"expected literal False, got {out_false!r}"


# ──────────────────────────────────────────────────────────────────────────
# Driver.
# ──────────────────────────────────────────────────────────────────────────

def _run_all() -> int:
    tests = [
        test_registered_in_global_registry,
        test_matcher_is_callable,
        test_returns_true_on_single_preserved_pair,
        test_returns_true_on_all_pairs_preserved,
        test_returns_true_when_preserved_pairs_have_change_groups,
        test_returns_false_when_any_pair_size_changed,
        test_returns_false_when_every_pair_size_changed,
        test_returns_false_when_top_level_flag_false,
        test_returns_false_when_top_level_flag_missing,
        test_returns_false_on_empty_pair_analyses,
        test_returns_false_on_missing_pair_analyses,
        test_returns_false_on_non_dict_patterns,
        test_returns_false_when_size_match_missing,
        test_returns_false_when_size_match_is_falsy,
        test_is_side_effect_free_on_inputs,
        test_is_deterministic_across_repeats,
        test_mutually_exclusive_with_grid_size_changed,
        test_can_cofire_with_identity_transformation,
        test_does_not_imply_identity_transformation,
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
