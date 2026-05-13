"""
tests/test_recognized_conditions.py — exercise the iter-11 applier
``agent.conditions.recognized_conditions``.

Runs without pytest:

    python tests/test_recognized_conditions.py

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

from agent.conditions import (  # noqa: E402
    CONDITION_REGISTRY,
    recognized_conditions,
)


# Patterns shapes that the three registered matchers will fire on (as of
# iter 10). These mirror the dicts ``ExtractPatternOperator`` produces in
# ``agent/active_operators.py``.

def _patterns_all_three_fire() -> dict:
    """A patterns dict that satisfies:
      * grid_size_preserved — top-level flag + per-pair size_match
      * consistent_color_mapping — every input color maps to exactly one
        output color (uses three distinct input colors so 0→3, 1→4, 2→5
        is a well-defined 1:1 mapping rather than a 0→{3,4,5} collision)
      * sequential_recoloring — three groups per pair, outputs form the
        contiguous range [3,4,5] ordered by top_row
    """
    return {
        "grid_size_preserved": True,
        "pair_analyses": [
            {
                "size_match": True,
                "num_groups": 3,
                "groups": [
                    {"input_colors": [0], "output_colors": [3],
                     "top_row": 0, "top_col": 0},
                    {"input_colors": [1], "output_colors": [4],
                     "top_row": 1, "top_col": 0},
                    {"input_colors": [2], "output_colors": [5],
                     "top_row": 2, "top_col": 0},
                ],
            },
            {
                "size_match": True,
                "num_groups": 3,
                "groups": [
                    {"input_colors": [0], "output_colors": [3],
                     "top_row": 0, "top_col": 0},
                    {"input_colors": [1], "output_colors": [4],
                     "top_row": 1, "top_col": 0},
                    {"input_colors": [2], "output_colors": [5],
                     "top_row": 2, "top_col": 0},
                ],
            },
        ],
    }


def _patterns_identity_pairs() -> dict:
    """Patterns whose every pair has zero changes AND matching
    dimensions. Fires both ``grid_size_preserved`` (dimensions match)
    AND ``identity_transformation`` (zero changes per pair) — they are
    layered preconditions, not competitors. The colour-mapping and
    sequential-recoloring matchers do NOT fire here (no change groups
    means no mapping to recognise)."""
    return {
        "grid_size_preserved": True,
        "pair_analyses": [
            {"size_match": True, "num_groups": 0, "groups": []},
            {"size_match": True, "num_groups": 0, "groups": []},
        ],
    }


def _patterns_color_mapping_only() -> dict:
    """consistent_color_mapping fires; grid_size_preserved does NOT
    (top-level flag is False), and sequential_recoloring does NOT
    (outputs [3, 7] are not a contiguous range)."""
    return {
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


# ──────────────────────────────────────────────────────────────────────────
# Tests.
# ──────────────────────────────────────────────────────────────────────────

def test_helper_is_importable_from_package_root() -> None:
    import agent.conditions as mod
    assert hasattr(mod, "recognized_conditions"), (
        "recognized_conditions not exported from agent.conditions"
    )
    assert callable(mod.recognized_conditions)


def test_registry_contents_after_helper_load() -> None:
    # The applier must not register itself or pull in anything beyond
    # the matcher modules under ``agent/conditions/``. As of iter 18
    # there are six such modules; tightening the assertion to ``==``
    # keeps a stray @register import from sneaking into the package.
    assert set(CONDITION_REGISTRY.keys()) == {
        "grid_size_preserved",
        "consistent_color_mapping",
        "sequential_recoloring",
        "identity_transformation",
        "grid_size_changed",
        "output_color_uniform",
    }, f"unexpected registry contents: {sorted(CONDITION_REGISTRY)}"


def test_all_three_matchers_fire_on_compatible_patterns() -> None:
    fired = recognized_conditions(_patterns_all_three_fire())
    assert set(fired) == {
        "grid_size_preserved",
        "consistent_color_mapping",
        "sequential_recoloring",
    }, f"expected all three to fire, got {fired}"


def test_identity_pairs_fire_both_grid_size_and_identity_matchers() -> None:
    # Zero-change pairs with matching dimensions fire BOTH the iter-1
    # dimensional precondition AND the iter-13 identity matcher; the
    # colour-mapping / sequential-recoloring matchers do not (they need
    # at least one changed group to recognise a mapping or sequence).
    fired = set(recognized_conditions(_patterns_identity_pairs()))
    assert fired == {"grid_size_preserved", "identity_transformation"}, (
        f"expected grid_size_preserved + identity_transformation, got "
        f"{sorted(fired)}"
    )


def test_color_mapping_fires_without_grid_size_preserved() -> None:
    fired = recognized_conditions(_patterns_color_mapping_only())
    assert "consistent_color_mapping" in fired, (
        "consistent_color_mapping must be dimension-agnostic"
    )
    assert "grid_size_preserved" not in fired, (
        "grid_size_preserved must not fire when flag is False"
    )
    assert "sequential_recoloring" not in fired, (
        "non-contiguous outputs must not fire sequential_recoloring"
    )


def test_returns_registry_insertion_order() -> None:
    expected_order = [n for n in CONDITION_REGISTRY.keys()
                      if n in {"grid_size_preserved",
                               "consistent_color_mapping",
                               "sequential_recoloring",
                               "identity_transformation"}]
    fired = recognized_conditions(_patterns_all_three_fire())
    fired_in_expected = [n for n in fired if n in expected_order]
    assert fired_in_expected == [n for n in expected_order if n in fired], (
        f"order mismatch: registry says {expected_order}, applier says {fired}"
    )


def test_empty_patterns_dict_fires_nothing() -> None:
    assert recognized_conditions({}) == []


def test_returns_empty_on_non_dict_patterns() -> None:
    assert recognized_conditions(None) == []        # type: ignore[arg-type]
    assert recognized_conditions([]) == []          # type: ignore[arg-type]
    assert recognized_conditions("oops") == []      # type: ignore[arg-type]
    assert recognized_conditions(42) == []          # type: ignore[arg-type]


def test_returns_list_type_for_downstream_consumers() -> None:
    fired = recognized_conditions(_patterns_all_three_fire())
    assert isinstance(fired, list), f"expected list, got {type(fired).__name__}"


def test_params_per_type_argument_is_forwarded() -> None:
    # None of the iter-1/8/10 matchers consume params today, but the API
    # must thread the argument through so a future parameterised matcher
    # gets its dict. Stand up a sentinel matcher that *requires* a
    # specific param, register it temporarily, and check the applier
    # passes the param through.
    seen: dict = {}

    def _sentinel(patterns: dict, params: dict) -> bool:
        seen["params"] = params
        return params.get("magic") == "xyz"

    name = "__iter11_sentinel_pass_through__"
    assert name not in CONDITION_REGISTRY
    CONDITION_REGISTRY[name] = _sentinel
    try:
        fired = recognized_conditions(
            _patterns_all_three_fire(),
            params_per_type={name: {"magic": "xyz"}},
        )
        assert name in fired, "sentinel should fire when params match"
        assert seen.get("params") == {"magic": "xyz"}, (
            f"applier did not forward params: got {seen.get('params')!r}"
        )
    finally:
        del CONDITION_REGISTRY[name]


def test_params_per_type_missing_entry_defaults_to_empty_dict() -> None:
    # A matcher registered in the registry but with no entry in
    # ``params_per_type`` must receive ``{}``, not crash. Confirm with a
    # sentinel that records what it received.
    seen: list = []

    def _sentinel(patterns: dict, params: dict) -> bool:
        seen.append(params)
        return False

    name = "__iter11_sentinel_default_params__"
    CONDITION_REGISTRY[name] = _sentinel
    try:
        recognized_conditions(_patterns_all_three_fire(), params_per_type={})
        assert seen == [{}], f"expected default {{}}, got {seen}"
    finally:
        del CONDITION_REGISTRY[name]


def test_non_dict_params_per_type_entry_falls_back_to_empty_dict() -> None:
    seen: list = []

    def _sentinel(patterns: dict, params: dict) -> bool:
        seen.append(params)
        return False

    name = "__iter11_sentinel_bad_params__"
    CONDITION_REGISTRY[name] = _sentinel
    try:
        recognized_conditions(
            _patterns_all_three_fire(),
            params_per_type={name: "not-a-dict"},  # type: ignore[dict-item]
        )
        assert seen == [{}], f"expected {{}} fallback, got {seen}"
    finally:
        del CONDITION_REGISTRY[name]


def test_non_dict_params_per_type_top_level_defaults_to_empty() -> None:
    # If the whole ``params_per_type`` argument is something other than a
    # dict (None / list / int), the applier still runs and every matcher
    # sees ``{}``.
    fired_none = recognized_conditions(_patterns_all_three_fire(),
                                       params_per_type=None)
    fired_list = recognized_conditions(_patterns_all_three_fire(),
                                       params_per_type=[])  # type: ignore[arg-type]
    fired_int = recognized_conditions(_patterns_all_three_fire(),
                                      params_per_type=42)  # type: ignore[arg-type]
    assert fired_none == fired_list == fired_int, (
        f"non-dict params_per_type did not normalise to empty: "
        f"{fired_none} {fired_list} {fired_int}"
    )


def test_is_side_effect_free_on_inputs() -> None:
    patterns = _patterns_all_three_fire()
    params = {"grid_size_preserved": {"unused": 1}}
    before_patterns = copy.deepcopy(patterns)
    before_params = copy.deepcopy(params)
    recognized_conditions(patterns, params_per_type=params)
    assert patterns == before_patterns, "applier mutated patterns"
    assert params == before_params, "applier mutated params_per_type"


def test_does_not_swallow_matcher_exceptions() -> None:
    # docs/RULE_FORMAT.md §4 says matchers must return False on malformed
    # input, never raise. The applier therefore must not paper over a
    # raising matcher — that would silently corrupt the recognition
    # output and mirror F7 (swallowed RuleSchemaError) in spirit.
    def _boom(patterns: dict, params: dict) -> bool:
        raise RuntimeError("matcher contract violation")

    name = "__iter11_boom__"
    CONDITION_REGISTRY[name] = _boom
    try:
        raised = False
        try:
            recognized_conditions(_patterns_all_three_fire())
        except RuntimeError:
            raised = True
        assert raised, "applier silently swallowed RuntimeError"
    finally:
        del CONDITION_REGISTRY[name]


def test_is_deterministic_across_repeat_calls() -> None:
    patterns = _patterns_all_three_fire()
    runs = [tuple(recognized_conditions(patterns)) for _ in range(5)]
    assert len(set(runs)) == 1, f"non-deterministic outputs: {set(runs)}"


def test_registry_is_not_modified_during_application() -> None:
    snapshot_keys = list(CONDITION_REGISTRY.keys())
    snapshot_values = list(CONDITION_REGISTRY.values())
    recognized_conditions(_patterns_all_three_fire())
    assert list(CONDITION_REGISTRY.keys()) == snapshot_keys, (
        "registry keys changed after applier call"
    )
    assert list(CONDITION_REGISTRY.values()) == snapshot_values, (
        "registry values changed after applier call"
    )


def test_returns_only_matchers_whose_match_is_strictly_true() -> None:
    # A matcher returning truthy-but-not-True (e.g. 1, "yes") must NOT
    # fire — the matcher contract is bool, not truthiness.
    def _truthy_not_true(patterns: dict, params: dict):
        return 1  # truthy, but `is True` is False

    name = "__iter11_truthy_not_true__"
    CONDITION_REGISTRY[name] = _truthy_not_true
    try:
        fired = recognized_conditions(_patterns_all_three_fire())
        assert name not in fired, (
            "applier accepted truthy non-bool; contract is `is True`"
        )
    finally:
        del CONDITION_REGISTRY[name]


# ──────────────────────────────────────────────────────────────────────────
# Driver.
# ──────────────────────────────────────────────────────────────────────────

def _run_all() -> int:
    tests = [
        test_helper_is_importable_from_package_root,
        test_registry_contents_after_helper_load,
        test_all_three_matchers_fire_on_compatible_patterns,
        test_identity_pairs_fire_both_grid_size_and_identity_matchers,
        test_color_mapping_fires_without_grid_size_preserved,
        test_returns_registry_insertion_order,
        test_empty_patterns_dict_fires_nothing,
        test_returns_empty_on_non_dict_patterns,
        test_returns_list_type_for_downstream_consumers,
        test_params_per_type_argument_is_forwarded,
        test_params_per_type_missing_entry_defaults_to_empty_dict,
        test_non_dict_params_per_type_entry_falls_back_to_empty_dict,
        test_non_dict_params_per_type_top_level_defaults_to_empty,
        test_is_side_effect_free_on_inputs,
        test_does_not_swallow_matcher_exceptions,
        test_is_deterministic_across_repeat_calls,
        test_registry_is_not_modified_during_application,
        test_returns_only_matchers_whose_match_is_strictly_true,
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
        print("\nall recognized_conditions tests passed.")
    else:
        print(f"\n{rc} test(s) failed.")
    sys.exit(0 if rc == 0 else 1)
