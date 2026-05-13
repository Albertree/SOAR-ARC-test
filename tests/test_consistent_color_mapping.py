"""
tests/test_consistent_color_mapping.py — exercise the iter-8 matcher
`agent.conditions.consistent_color_mapping`.

Runs without pytest:

    python tests/test_consistent_color_mapping.py

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


MATCHER_NAME = "consistent_color_mapping"


def _matcher():
    return CONDITION_REGISTRY[MATCHER_NAME]


# ──────────────────────────────────────────────────────────────────────────
# Tests.
# ──────────────────────────────────────────────────────────────────────────

def test_registered_in_global_registry() -> None:
    assert MATCHER_NAME in CONDITION_REGISTRY, (
        f"{MATCHER_NAME!r} not registered; got {sorted(CONDITION_REGISTRY)}"
    )


def test_grid_size_preserved_still_registered() -> None:
    # Adjacent invariant — this iter must not displace the iter-1 matcher.
    assert "grid_size_preserved" in CONDITION_REGISTRY, (
        "iter-1 matcher missing after iter-8 addition"
    )


def test_returns_true_on_uniform_one_to_one_mapping() -> None:
    patterns = {
        "pair_analyses": [
            {"groups": [{"input_colors": [0], "output_colors": [3]}]},
            {"groups": [{"input_colors": [0], "output_colors": [3]}]},
        ],
    }
    assert _matcher()(patterns, {}) is True


def test_returns_true_when_multiple_input_colors_each_have_one_output() -> None:
    patterns = {
        "pair_analyses": [
            {"groups": [
                {"input_colors": [0], "output_colors": [3]},
                {"input_colors": [5], "output_colors": [7]},
            ]},
            {"groups": [
                {"input_colors": [0], "output_colors": [3]},
                {"input_colors": [5], "output_colors": [7]},
            ]},
        ],
    }
    assert _matcher()(patterns, {}) is True


def test_returns_false_when_same_input_maps_to_two_outputs() -> None:
    patterns = {
        "pair_analyses": [
            {"groups": [{"input_colors": [0], "output_colors": [3]}]},
            {"groups": [{"input_colors": [0], "output_colors": [4]}]},
        ],
    }
    assert _matcher()(patterns, {}) is False


def test_returns_false_on_empty_pair_analyses() -> None:
    assert _matcher()({"pair_analyses": []}, {}) is False


def test_returns_false_when_groups_empty_on_every_pair() -> None:
    patterns = {"pair_analyses": [{"groups": []}, {"groups": []}]}
    assert _matcher()(patterns, {}) is False


def test_returns_false_on_missing_pair_analyses_key() -> None:
    assert _matcher()({}, {}) is False


def test_returns_false_on_non_dict_patterns() -> None:
    assert _matcher()(None, {}) is False  # type: ignore[arg-type]
    assert _matcher()([], {}) is False    # type: ignore[arg-type]
    assert _matcher()(42, {}) is False    # type: ignore[arg-type]


def test_returns_false_on_malformed_analysis() -> None:
    # An entry under pair_analyses that is not a dict.
    patterns = {"pair_analyses": ["not-a-dict"]}
    assert _matcher()(patterns, {}) is False


def test_returns_false_on_malformed_group() -> None:
    patterns = {"pair_analyses": [{"groups": ["not-a-dict"]}]}
    assert _matcher()(patterns, {}) is False


def test_is_side_effect_free_on_input() -> None:
    patterns = {
        "pair_analyses": [
            {"groups": [{"input_colors": [0, 1], "output_colors": [3]}]},
            {"groups": [{"input_colors": [0, 1], "output_colors": [3]}]},
        ],
    }
    before = copy.deepcopy(patterns)
    _matcher()(patterns, {})
    assert patterns == before, "matcher mutated its input"


def test_is_deterministic_across_repeat_calls() -> None:
    patterns = {
        "pair_analyses": [
            {"groups": [{"input_colors": [0], "output_colors": [3]}]},
            {"groups": [{"input_colors": [0], "output_colors": [3]}]},
        ],
    }
    m = _matcher()
    results = {m(patterns, {}) for _ in range(5)}
    assert results == {True}, f"non-deterministic outputs: {results}"


def test_aligns_with_pipeline_try_color_mapping_precondition() -> None:
    # End-to-end agreement: when ExtractPatternOperator + try_color_mapping
    # would derive a valid mapping, this matcher returns True. Patterns
    # shape mirrors what _try_color_mapping consumes in agent/active_operators.py.
    patterns = {
        "grid_size_preserved": True,
        "pair_analyses": [
            {
                "num_groups": 1,
                "groups": [
                    {"input_colors": [2], "output_colors": [8],
                     "top_row": 0, "top_col": 0, "cell_count": 1},
                ],
            },
            {
                "num_groups": 1,
                "groups": [
                    {"input_colors": [2], "output_colors": [8],
                     "top_row": 1, "top_col": 2, "cell_count": 1},
                ],
            },
        ],
    }
    assert _matcher()(patterns, {}) is True

    # And conversely: if any input color now maps to two outputs, the
    # detector would bail (return None from _try_color_mapping); the
    # matcher must agree.
    patterns["pair_analyses"][1]["groups"][0]["output_colors"] = [9]
    assert _matcher()(patterns, {}) is False


# ──────────────────────────────────────────────────────────────────────────
# Driver.
# ──────────────────────────────────────────────────────────────────────────

def _run_all() -> int:
    tests = [
        test_registered_in_global_registry,
        test_grid_size_preserved_still_registered,
        test_returns_true_on_uniform_one_to_one_mapping,
        test_returns_true_when_multiple_input_colors_each_have_one_output,
        test_returns_false_when_same_input_maps_to_two_outputs,
        test_returns_false_on_empty_pair_analyses,
        test_returns_false_when_groups_empty_on_every_pair,
        test_returns_false_on_missing_pair_analyses_key,
        test_returns_false_on_non_dict_patterns,
        test_returns_false_on_malformed_analysis,
        test_returns_false_on_malformed_group,
        test_is_side_effect_free_on_input,
        test_is_deterministic_across_repeat_calls,
        test_aligns_with_pipeline_try_color_mapping_precondition,
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
        print("\nall consistent_color_mapping tests passed.")
    else:
        print(f"\n{rc} test(s) failed.")
    sys.exit(0 if rc == 0 else 1)
