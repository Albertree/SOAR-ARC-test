"""Tests for ``change_palette_intersection_nonempty_per_group`` -- the
per-group anchor-preservation matcher (iter 228 named-gap candidate iii).

Pins the contract: every change group of every example pair has non-empty
``set(input_colors) & set(output_colors)``; fail-closed on empty / no-
group / malformed / strict-type violations; deterministic and side-
effect-free; strict mutual exclusion with iter 203 on the non-empty-
per-group-palette domain.
"""

from __future__ import annotations

from agent.conditions import CONDITION_REGISTRY
from agent.conditions.change_palette_intersection_nonempty_per_group import (
    match,
)


_NAME = "change_palette_intersection_nonempty_per_group"


# ----------------------------------------------------------------------
# smoke / membership
# ----------------------------------------------------------------------

def test_module_imports_and_registers() -> None:
    assert _NAME in CONDITION_REGISTRY
    assert CONDITION_REGISTRY[_NAME] is match


# ----------------------------------------------------------------------
# positive cases
# ----------------------------------------------------------------------

def _pair(groups: list) -> dict:
    return {"groups": groups}


def _group(ic: list, oc: list) -> dict:
    return {"input_colors": ic, "output_colors": oc}


def test_per_group_equality_fires() -> None:
    # iter 201 territory STRICTLY IMPLIES this matcher.
    p = {"pair_analyses": [_pair([_group([1, 2], [1, 2])])]}
    assert match(p, {}) is True


def test_per_group_strict_erasure_fires() -> None:
    # iter 204 territory STRICTLY IMPLIES this matcher.
    p = {"pair_analyses": [_pair([_group([1, 2, 3], [1, 2])])]}
    assert match(p, {}) is True


def test_per_group_strict_expansion_fires() -> None:
    # iter 205 territory STRICTLY IMPLIES this matcher.
    p = {"pair_analyses": [_pair([_group([1], [1, 2, 3])])]}
    assert match(p, {}) is True


def test_per_group_partial_overlap_fires() -> None:
    # partial-overlap residual cell STRICTLY IMPLIES this matcher.
    p = {"pair_analyses": [_pair([_group([1, 2], [2, 3])])]}
    assert match(p, {}) is True


def test_multiple_pairs_all_anchored_fires() -> None:
    p = {"pair_analyses": [
        _pair([_group([1, 2], [1, 2])]),
        _pair([_group([3, 4], [4, 5])]),
    ]}
    assert match(p, {}) is True


def test_multi_group_per_pair_all_anchored_fires() -> None:
    p = {"pair_analyses": [_pair([
        _group([1, 2], [2, 3]),
        _group([4, 5], [5, 6]),
    ])]}
    assert match(p, {}) is True


def test_zero_and_nine_witness() -> None:
    p = {"pair_analyses": [_pair([_group([0, 9], [9, 5])])]}
    assert match(p, {}) is True


# ----------------------------------------------------------------------
# negative cases (truth-value rejection)
# ----------------------------------------------------------------------

def test_per_group_disjoint_rejects() -> None:
    # iter 203 territory STRICTLY MUTUALLY EXCLUSIVE with this matcher.
    p = {"pair_analyses": [_pair([_group([1, 2], [3, 4])])]}
    assert match(p, {}) is False


def test_one_group_disjoint_rejects() -> None:
    # Universal-over-groups: one disjoint group kills the matcher.
    p = {"pair_analyses": [_pair([
        _group([1, 2], [1, 2]),
        _group([3, 4], [5, 6]),
    ])]}
    assert match(p, {}) is False


def test_disjoint_in_later_pair_rejects() -> None:
    p = {"pair_analyses": [
        _pair([_group([1, 2], [1, 2])]),
        _pair([_group([3, 4], [5, 6])]),
    ]}
    assert match(p, {}) is False


def test_zero_groups_rejects() -> None:
    # Identity-territory rejection clause.
    p = {"pair_analyses": [_pair([])]}
    assert match(p, {}) is False


def test_one_pair_zero_groups_rejects() -> None:
    p = {"pair_analyses": [
        _pair([_group([1], [1])]),
        _pair([]),
    ]}
    assert match(p, {}) is False


# ----------------------------------------------------------------------
# structural rejections
# ----------------------------------------------------------------------

def test_non_dict_patterns_rejects() -> None:
    assert match("not a dict", {}) is False
    assert match(None, {}) is False
    assert match(42, {}) is False


def test_missing_pair_analyses_rejects() -> None:
    assert match({}, {}) is False


def test_empty_pair_analyses_rejects() -> None:
    assert match({"pair_analyses": []}, {}) is False


def test_non_list_pair_analyses_rejects() -> None:
    assert match({"pair_analyses": "not a list"}, {}) is False


def test_non_dict_analysis_rejects() -> None:
    assert match({"pair_analyses": ["not a dict"]}, {}) is False


def test_missing_groups_rejects() -> None:
    assert match({"pair_analyses": [{}]}, {}) is False


def test_non_list_groups_rejects() -> None:
    assert match({"pair_analyses": [{"groups": "x"}]}, {}) is False


def test_non_dict_group_rejects() -> None:
    p = {"pair_analyses": [_pair(["not a dict"])]}
    assert match(p, {}) is False


# ----------------------------------------------------------------------
# strict-type gates on input_colors / output_colors
# ----------------------------------------------------------------------

def test_missing_input_colors_rejects() -> None:
    p = {"pair_analyses": [_pair([{"output_colors": [1]}])]}
    assert match(p, {}) is False


def test_missing_output_colors_rejects() -> None:
    p = {"pair_analyses": [_pair([{"input_colors": [1]}])]}
    assert match(p, {}) is False


def test_non_list_input_colors_rejects() -> None:
    p = {"pair_analyses": [_pair([_group("x", [1])])]}
    assert match(p, {}) is False


def test_non_list_output_colors_rejects() -> None:
    p = {"pair_analyses": [_pair([_group([1], "x")])]}
    assert match(p, {}) is False


def test_empty_input_colors_rejects() -> None:
    p = {"pair_analyses": [_pair([_group([], [1])])]}
    assert match(p, {}) is False


def test_empty_output_colors_rejects() -> None:
    p = {"pair_analyses": [_pair([_group([1], [])])]}
    assert match(p, {}) is False


def test_bool_in_input_colors_rejects() -> None:
    # Bool is an int subclass; the strict-type posture rejects it.
    p = {"pair_analyses": [_pair([_group([True], [1])])]}
    assert match(p, {}) is False


def test_bool_in_output_colors_rejects() -> None:
    p = {"pair_analyses": [_pair([_group([1], [True])])]}
    assert match(p, {}) is False


def test_out_of_range_color_rejects() -> None:
    p = {"pair_analyses": [_pair([_group([1, 10], [1])])]}
    assert match(p, {}) is False


def test_non_int_color_rejects() -> None:
    p = {"pair_analyses": [_pair([_group([1, "x"], [1])])]}
    assert match(p, {}) is False


# ----------------------------------------------------------------------
# behavioural contract
# ----------------------------------------------------------------------

def test_match_is_deterministic() -> None:
    p = {"pair_analyses": [_pair([_group([1, 2], [2, 3])])]}
    a = match(p, {})
    b = match(p, {})
    assert a is b is True


def test_match_returns_literal_bool() -> None:
    p = {"pair_analyses": [_pair([_group([1, 2], [2, 3])])]}
    assert match(p, {}) is True
    p2 = {"pair_analyses": [_pair([_group([1], [2])])]}
    assert match(p2, {}) is False


def test_params_ignored() -> None:
    p = {"pair_analyses": [_pair([_group([1, 2], [2, 3])])]}
    # Arbitrary params dicts do not change behavior.
    assert match(p, {"foo": "bar"}) is True
    assert match(p, {}) is True


def test_does_not_mutate_input() -> None:
    inner = _group([1, 2], [2, 3])
    p = {"pair_analyses": [_pair([inner])]}
    before = (list(inner["input_colors"]), list(inner["output_colors"]))
    match(p, {})
    after = (list(inner["input_colors"]), list(inner["output_colors"]))
    assert before == after


# ----------------------------------------------------------------------
# orthogonality / refinement wiring (via recognized_conditions)
# ----------------------------------------------------------------------

def test_disjoint_fixture_excludes_this_matcher_but_fires_iter_203() -> None:
    from agent.conditions import recognized_conditions
    p = {"pair_analyses": [_pair([_group([1, 2], [3, 4])])]}
    fired = set(recognized_conditions(p))
    assert _NAME not in fired
    assert "output_colors_disjoint_from_input_colors_per_group" in fired


def test_equality_fixture_fires_this_matcher_and_iter_201() -> None:
    from agent.conditions import recognized_conditions
    p = {"pair_analyses": [_pair([_group([1, 2], [1, 2])])]}
    fired = set(recognized_conditions(p))
    assert _NAME in fired
    assert "output_colors_equals_input_colors_per_group" in fired
    # Mutual exclusion with iter 203 on non-empty per-group palettes.
    assert "output_colors_disjoint_from_input_colors_per_group" not in fired
