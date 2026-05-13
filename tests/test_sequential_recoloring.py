"""
tests/test_sequential_recoloring.py — exercise the iter-10 matcher
`agent.conditions.sequential_recoloring`.

Runs without pytest:

    python tests/test_sequential_recoloring.py

Dependency-free, same runner style as the other tests under `tests/`.
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


MATCHER_NAME = "sequential_recoloring"


def _matcher():
    return CONDITION_REGISTRY[MATCHER_NAME]


def _group(input_color: int, output_color: int,
           top_row: int = 0, top_col: int = 0,
           cell_count: int = 1) -> dict:
    """Build a minimal group dict matching the ExtractPatternOperator shape."""
    return {
        "input_colors": [input_color],
        "output_colors": [output_color],
        "top_row": top_row,
        "top_col": top_col,
        "cell_count": cell_count,
    }


def _pair(groups: list) -> dict:
    return {"num_groups": len(groups), "groups": groups}


# ──────────────────────────────────────────────────────────────────────────
# Tests.
# ──────────────────────────────────────────────────────────────────────────

def test_registered_in_global_registry() -> None:
    assert MATCHER_NAME in CONDITION_REGISTRY, (
        f"{MATCHER_NAME!r} not registered; got {sorted(CONDITION_REGISTRY)}"
    )


def test_previous_matchers_still_registered() -> None:
    # Adjacent invariant — this iter must not displace iters 1 and 8.
    assert "grid_size_preserved" in CONDITION_REGISTRY, (
        "iter-1 matcher missing after iter-10 addition"
    )
    assert "consistent_color_mapping" in CONDITION_REGISTRY, (
        "iter-8 matcher missing after iter-10 addition"
    )


def test_three_distinct_matchers_registered() -> None:
    # P5 unit-monotone counter — there must be at least 3 entries now.
    assert len(CONDITION_REGISTRY) >= 3, (
        f"expected at least 3 entries, got {len(CONDITION_REGISTRY)}: "
        f"{sorted(CONDITION_REGISTRY)}"
    )


def test_returns_true_on_two_pair_sequence_sorted_by_top_row() -> None:
    # Two pairs, each with two groups whose output colours sort to (1, 2)
    # by top_row. Mirrors the canonical recolor-by-position case.
    patterns = {
        "pair_analyses": [
            _pair([
                _group(0, 1, top_row=0, top_col=5),
                _group(0, 2, top_row=4, top_col=1),
            ]),
            _pair([
                _group(0, 1, top_row=1, top_col=2),
                _group(0, 2, top_row=3, top_col=0),
            ]),
        ],
    }
    assert _matcher()(patterns, {}) is True


def test_returns_true_when_only_top_col_axis_works() -> None:
    # Output sequence emerges from top_col ordering, not top_row.
    patterns = {
        "pair_analyses": [
            _pair([
                _group(0, 5, top_row=2, top_col=0),
                _group(0, 6, top_row=0, top_col=3),
                _group(0, 7, top_row=1, top_col=6),
            ]),
            _pair([
                _group(0, 5, top_row=4, top_col=1),
                _group(0, 6, top_row=2, top_col=4),
                _group(0, 7, top_row=3, top_col=8),
            ]),
        ],
    }
    assert _matcher()(patterns, {}) is True


def test_returns_true_on_single_group_per_pair() -> None:
    # A single group → trivially-contiguous 1-element sequence, consistent
    # with _try_recolor_sequential's behaviour on 1-group pairs.
    patterns = {
        "pair_analyses": [
            _pair([_group(0, 4)]),
            _pair([_group(0, 4)]),
        ],
    }
    assert _matcher()(patterns, {}) is True


def test_returns_false_on_non_contiguous_outputs() -> None:
    # Output colours are [1, 3] — not contiguous (missing 2).
    patterns = {
        "pair_analyses": [
            _pair([
                _group(0, 1, top_row=0),
                _group(0, 3, top_row=2),
            ]),
            _pair([
                _group(0, 1, top_row=1),
                _group(0, 3, top_row=4),
            ]),
        ],
    }
    assert _matcher()(patterns, {}) is False


def test_returns_false_when_neither_axis_orders_pair_correctly() -> None:
    # Output sequence (1, 2) but neither top_row nor top_col puts them in
    # that order — pair 0 has the higher colour at the *earlier* row AND
    # earlier col.
    patterns = {
        "pair_analyses": [
            _pair([
                _group(0, 2, top_row=0, top_col=0),
                _group(0, 1, top_row=5, top_col=5),
            ]),
            _pair([
                _group(0, 1, top_row=0, top_col=0),
                _group(0, 2, top_row=5, top_col=5),
            ]),
        ],
    }
    assert _matcher()(patterns, {}) is False


def test_returns_false_on_mismatched_group_counts() -> None:
    patterns = {
        "pair_analyses": [
            _pair([_group(0, 1, top_row=0), _group(0, 2, top_row=2)]),
            _pair([_group(0, 1, top_row=0)]),  # only one group here
        ],
    }
    assert _matcher()(patterns, {}) is False


def test_returns_false_on_multi_color_group() -> None:
    # A group with two input colours violates the precondition.
    patterns = {
        "pair_analyses": [
            _pair([
                {"input_colors": [0, 1], "output_colors": [3],
                 "top_row": 0, "top_col": 0, "cell_count": 1},
            ]),
            _pair([_group(0, 3)]),
        ],
    }
    assert _matcher()(patterns, {}) is False


def test_returns_false_on_multi_output_group() -> None:
    patterns = {
        "pair_analyses": [
            _pair([
                {"input_colors": [0], "output_colors": [3, 4],
                 "top_row": 0, "top_col": 0, "cell_count": 1},
            ]),
            _pair([_group(0, 3)]),
        ],
    }
    assert _matcher()(patterns, {}) is False


def test_returns_false_on_empty_pair_analyses() -> None:
    assert _matcher()({"pair_analyses": []}, {}) is False


def test_returns_false_on_pair_with_zero_groups() -> None:
    patterns = {
        "pair_analyses": [
            _pair([_group(0, 1, top_row=0)]),
            _pair([]),  # zero groups
        ],
    }
    assert _matcher()(patterns, {}) is False


def test_returns_false_on_non_dict_patterns() -> None:
    assert _matcher()(None, {}) is False  # type: ignore[arg-type]
    assert _matcher()([], {}) is False    # type: ignore[arg-type]
    assert _matcher()("nope", {}) is False  # type: ignore[arg-type]


def test_returns_false_on_malformed_analysis() -> None:
    patterns = {"pair_analyses": ["not-a-dict"]}
    assert _matcher()(patterns, {}) is False


def test_returns_false_on_malformed_group() -> None:
    patterns = {"pair_analyses": [{"groups": ["not-a-dict"]}]}
    assert _matcher()(patterns, {}) is False


def test_is_side_effect_free_on_input() -> None:
    patterns = {
        "pair_analyses": [
            _pair([
                _group(0, 1, top_row=0),
                _group(0, 2, top_row=3),
            ]),
            _pair([
                _group(0, 1, top_row=1),
                _group(0, 2, top_row=4),
            ]),
        ],
    }
    before = copy.deepcopy(patterns)
    _matcher()(patterns, {})
    assert patterns == before, "matcher mutated its input"


def test_is_deterministic_across_repeat_calls() -> None:
    patterns = {
        "pair_analyses": [
            _pair([
                _group(0, 1, top_row=0),
                _group(0, 2, top_row=3),
            ]),
            _pair([
                _group(0, 1, top_row=1),
                _group(0, 2, top_row=4),
            ]),
        ],
    }
    m = _matcher()
    results = {m(patterns, {}) for _ in range(5)}
    assert results == {True}, f"non-deterministic outputs: {results}"


def test_aligns_with_pipeline_try_recolor_sequential_precondition() -> None:
    # End-to-end agreement with the patterns shape `_try_recolor_sequential`
    # consumes in `agent/active_operators.py`. The detector accepts the
    # positive case below and bails on the negative one — matcher must agree.
    positive = {
        "grid_size_preserved": True,
        "pair_analyses": [
            {
                "num_groups": 3,
                "groups": [
                    _group(0, 1, top_row=0, top_col=0),
                    _group(0, 2, top_row=2, top_col=0),
                    _group(0, 3, top_row=4, top_col=0),
                ],
            },
            {
                "num_groups": 3,
                "groups": [
                    _group(0, 1, top_row=1, top_col=1),
                    _group(0, 2, top_row=3, top_col=1),
                    _group(0, 3, top_row=5, top_col=1),
                ],
            },
        ],
    }
    assert _matcher()(positive, {}) is True

    # Swap two output colours so the contiguous-range constraint still
    # holds but the position-based ordering breaks. The detector returns
    # None on this — matcher must too.
    negative = copy.deepcopy(positive)
    negative["pair_analyses"][0]["groups"][0]["output_colors"] = [3]
    negative["pair_analyses"][0]["groups"][2]["output_colors"] = [1]
    assert _matcher()(negative, {}) is False


def test_does_not_fire_on_consistent_color_mapping_only_case() -> None:
    # A pair where each input colour maps to one output colour but the
    # outputs are *not* a contiguous integer range. iter-8's matcher
    # would return True; iter-10's must return False.
    patterns = {
        "pair_analyses": [
            _pair([
                _group(0, 7, top_row=0),
                _group(5, 9, top_row=2),
            ]),
            _pair([
                _group(0, 7, top_row=1),
                _group(5, 9, top_row=3),
            ]),
        ],
    }
    assert _matcher()(patterns, {}) is False


# ──────────────────────────────────────────────────────────────────────────
# Driver.
# ──────────────────────────────────────────────────────────────────────────

def _run_all() -> int:
    tests = [
        test_registered_in_global_registry,
        test_previous_matchers_still_registered,
        test_three_distinct_matchers_registered,
        test_returns_true_on_two_pair_sequence_sorted_by_top_row,
        test_returns_true_when_only_top_col_axis_works,
        test_returns_true_on_single_group_per_pair,
        test_returns_false_on_non_contiguous_outputs,
        test_returns_false_when_neither_axis_orders_pair_correctly,
        test_returns_false_on_mismatched_group_counts,
        test_returns_false_on_multi_color_group,
        test_returns_false_on_multi_output_group,
        test_returns_false_on_empty_pair_analyses,
        test_returns_false_on_pair_with_zero_groups,
        test_returns_false_on_non_dict_patterns,
        test_returns_false_on_malformed_analysis,
        test_returns_false_on_malformed_group,
        test_is_side_effect_free_on_input,
        test_is_deterministic_across_repeat_calls,
        test_aligns_with_pipeline_try_recolor_sequential_precondition,
        test_does_not_fire_on_consistent_color_mapping_only_case,
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
    rc = _run_all()
    if rc == 0:
        print("\nall sequential_recoloring tests passed.")
    else:
        print(f"\n{rc} test(s) failed.")
    sys.exit(0 if rc == 0 else 1)
