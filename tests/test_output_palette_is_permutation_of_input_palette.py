"""Tests for ``output_palette_is_permutation_of_input_palette`` -- the
whole-grid palette-permutation matcher (iter 329 named-gap candidate
ii). Pins the contract: per-pair palette set-equality (iter 185
condition) plus accumulated change-group colour-mapping bijection
(iter 8 condition AND injectivity refinement); fail-closed on empty /
malformed / strict-type violations; deterministic and side-effect-
free; strict refinement of (iter 185 AND iter 8) by the new
injectivity axis.
"""

from __future__ import annotations

import copy

from agent.conditions import CONDITION_REGISTRY
from agent.conditions.output_palette_is_permutation_of_input_palette import (
    match,
)


_NAME = "output_palette_is_permutation_of_input_palette"


def _group(ic, oc, **overrides):
    g = {
        "input_colors": list(ic),
        "output_colors": list(oc),
        "positions": [(0, 0)],
        "top_row": 0,
        "top_col": 0,
        "cell_count": 1,
    }
    g.update(overrides)
    return g


def _pair(input_palette, output_palette, groups=None, **overrides):
    base = {
        "input_height": 3,
        "input_width": 3,
        "output_height": 3,
        "output_width": 3,
        "size_match": True,
        "total_changes": 0,
        "num_groups": 0,
        "groups": list(groups) if groups else [],
        "input_palette": list(input_palette),
        "output_palette": list(output_palette),
    }
    base.update(overrides)
    return base


# ----------------------------------------------------------------------
# smoke / membership
# ----------------------------------------------------------------------

def test_module_imports_and_registers() -> None:
    assert _NAME in CONDITION_REGISTRY
    assert CONDITION_REGISTRY[_NAME] is match


def test_matcher_is_callable() -> None:
    assert callable(match)


# ----------------------------------------------------------------------
# positive cases -- canonical palette permutation shapes
# ----------------------------------------------------------------------

def test_two_cycle_swap_fires() -> None:
    # The canonical 2-cycle: red <-> blue on a palette {0, 1, 2}, with
    # 0 as a fixed point. Per-pair palette equal AND bijection on
    # changed-cell mapping (1 -> 2, 2 -> 1).
    p = {"pair_analyses": [_pair(
        [0, 1, 2], [0, 1, 2],
        groups=[
            _group([1], [2]),
            _group([2], [1]),
        ],
        num_groups=2, total_changes=2,
    )]}
    assert match(p, {}) is True


def test_three_cycle_fires() -> None:
    # A 3-cycle: 1 -> 2 -> 3 -> 1. Bijection on {1, 2, 3}.
    p = {"pair_analyses": [_pair(
        [1, 2, 3], [1, 2, 3],
        groups=[
            _group([1], [2]),
            _group([2], [3]),
            _group([3], [1]),
        ],
        num_groups=3, total_changes=3,
    )]}
    assert match(p, {}) is True


def test_two_cycle_across_multiple_pairs_fires() -> None:
    # Same bijection observed in fragments across pairs: pair 1 shows
    # only 1->2, pair 2 shows only 2->1. Together they describe the
    # full 2-cycle.
    p = {"pair_analyses": [
        _pair([0, 1, 2], [0, 1, 2], groups=[_group([1], [2])],
              num_groups=1, total_changes=1),
        _pair([0, 1, 2], [0, 1, 2], groups=[_group([2], [1])],
              num_groups=1, total_changes=1),
    ]}
    assert match(p, {}) is True


def test_full_palette_permutation_fires() -> None:
    # Palette {1, 2}; rule sends 1 -> 2 and 2 -> 1 across the whole
    # grid. No fixed points -- still a bijection.
    p = {"pair_analyses": [_pair(
        [1, 2], [1, 2],
        groups=[
            _group([1], [2]),
            _group([2], [1]),
        ],
        num_groups=2, total_changes=2,
    )]}
    assert match(p, {}) is True


def test_palette_with_zero_witness_fires() -> None:
    # Palettes that include the background colour 0 are valid.
    p = {"pair_analyses": [_pair(
        [0, 5, 9], [0, 5, 9],
        groups=[
            _group([5], [9]),
            _group([9], [5]),
        ],
        num_groups=2, total_changes=2,
    )]}
    assert match(p, {}) is True


# ----------------------------------------------------------------------
# negative cases -- iter 8 fails (function violation)
# ----------------------------------------------------------------------

def test_function_violation_rejects() -> None:
    # Same input colour 1 mapped to two different outputs across pairs
    # -- not a function, so iter 8 rejects, so this matcher must
    # reject (strict implication of iter 8 must hold).
    p = {"pair_analyses": [
        _pair([0, 1, 2], [0, 1, 2], groups=[_group([1], [2])],
              num_groups=1, total_changes=1),
        _pair([0, 1, 2], [0, 1, 2], groups=[_group([1], [0])],
              num_groups=1, total_changes=1),
    ]}
    assert match(p, {}) is False


# ----------------------------------------------------------------------
# negative cases -- iter 185 fails (palette inequality)
# ----------------------------------------------------------------------

def test_palette_subset_strict_rejects() -> None:
    # Output palette is strict subset of input (an erasure). iter 185
    # rejects, so this matcher must reject.
    p = {"pair_analyses": [_pair(
        [0, 1, 2], [0, 1],
        groups=[_group([2], [1])],
        num_groups=1, total_changes=1,
    )]}
    assert match(p, {}) is False


def test_palette_disjoint_rejects() -> None:
    # Output palette disjoint from input -- canvas rewrite. iter 185
    # rejects, so this matcher must reject.
    p = {"pair_analyses": [_pair(
        [0, 1, 2], [3, 4, 5],
        groups=[_group([0], [3])],
        num_groups=1, total_changes=1,
    )]}
    assert match(p, {}) is False


def test_palette_partial_overlap_rejects() -> None:
    p = {"pair_analyses": [_pair(
        [0, 1, 2], [1, 2, 3],
        groups=[_group([0], [3])],
        num_groups=1, total_changes=1,
    )]}
    assert match(p, {}) is False


def test_any_pair_palette_inequal_rejects() -> None:
    # Universal-over-pairs: one offending pair fails the gate.
    p = {"pair_analyses": [
        _pair([0, 1, 2], [0, 1, 2],
              groups=[_group([1], [2]), _group([2], [1])],
              num_groups=2, total_changes=2),
        _pair([0, 1, 2], [0, 1, 2, 9],
              groups=[_group([1], [9])],
              num_groups=1, total_changes=1),
    ]}
    assert match(p, {}) is False


# ----------------------------------------------------------------------
# negative cases -- iter 8 passes but INJECTIVITY fails (the new axis)
# ----------------------------------------------------------------------

def test_non_injective_collapse_rejects() -> None:
    # Two distinct input colours BOTH map to the SAME output colour.
    # iter 185 fires (palette equal as set on the whole grid via
    # unchanged background) AND iter 8 fires (every input has one
    # output), but the mapping is NOT INJECTIVE -- a "merge" /
    # "collapse" recolour. This is the precise case the injectivity
    # refinement excludes.
    p = {"pair_analyses": [_pair(
        # Whole-grid palette {0, 1, 2} on both sides via unchanged
        # background cells outside the change groups; the change
        # groups themselves show 1 -> 0 and 2 -> 0.
        [0, 1, 2], [0, 1, 2],
        groups=[
            _group([1], [0]),
            _group([2], [0]),
        ],
        num_groups=2, total_changes=2,
    )]}
    assert match(p, {}) is False


def test_non_injective_across_pairs_rejects() -> None:
    # Fragment 1: 1 -> 0; fragment 2 (in a later pair): 2 -> 0.
    # Accumulated relation is non-injective -- output 0 has two
    # preimages 1 and 2.
    p = {"pair_analyses": [
        _pair([0, 1, 2], [0, 1, 2],
              groups=[_group([1], [0])],
              num_groups=1, total_changes=1),
        _pair([0, 1, 2], [0, 1, 2],
              groups=[_group([2], [0])],
              num_groups=1, total_changes=1),
    ]}
    assert match(p, {}) is False


# ----------------------------------------------------------------------
# negative cases -- identity territory (iter 13)
# ----------------------------------------------------------------------

def test_identity_zero_groups_rejects() -> None:
    # Palette equal, but no change observations -- accumulated
    # mapping empty -- iter 8 spirit rejects, so this matcher rejects.
    # Mirrors the iter 13 mutual-exclusion that iter 8 already enforces.
    p = {"pair_analyses": [_pair([0, 1, 2], [0, 1, 2])]}
    assert match(p, {}) is False


def test_multi_pair_all_identity_rejects() -> None:
    p = {"pair_analyses": [
        _pair([0, 1, 2], [0, 1, 2]),
        _pair([0, 1, 2], [0, 1, 2]),
    ]}
    assert match(p, {}) is False


# ----------------------------------------------------------------------
# structural rejections
# ----------------------------------------------------------------------

def test_non_dict_patterns_rejects() -> None:
    for bad in (None, 42, "oops", [], 0.0, True):
        assert match(bad, {}) is False, f"patterns={bad!r} should not fire"


def test_missing_pair_analyses_rejects() -> None:
    assert match({}, {}) is False


def test_empty_pair_analyses_rejects() -> None:
    assert match({"pair_analyses": []}, {}) is False


def test_non_list_pair_analyses_rejects() -> None:
    for bad in (None, 42, "oops", {"a": 1}, (), True):
        assert match({"pair_analyses": bad}, {}) is False, (
            f"pair_analyses={bad!r} should not fire"
        )


def test_non_dict_analysis_rejects() -> None:
    p = {"pair_analyses": [
        _pair([0, 1], [0, 1], groups=[_group([0], [1]), _group([1], [0])],
              num_groups=2, total_changes=2),
        "not-a-dict",
    ]}
    assert match(p, {}) is False


def test_missing_input_palette_rejects() -> None:
    analysis = _pair([0, 1], [0, 1],
                     groups=[_group([0], [1]), _group([1], [0])],
                     num_groups=2, total_changes=2)
    del analysis["input_palette"]
    assert match({"pair_analyses": [analysis]}, {}) is False


def test_missing_output_palette_rejects() -> None:
    analysis = _pair([0, 1], [0, 1],
                     groups=[_group([0], [1]), _group([1], [0])],
                     num_groups=2, total_changes=2)
    del analysis["output_palette"]
    assert match({"pair_analyses": [analysis]}, {}) is False


def test_missing_groups_rejects() -> None:
    analysis = _pair([0, 1], [0, 1])
    del analysis["groups"]
    assert match({"pair_analyses": [analysis]}, {}) is False


def test_non_list_groups_rejects() -> None:
    p = {"pair_analyses": [_pair([0, 1], [0, 1], groups="x")]}
    p["pair_analyses"][0]["groups"] = "x"
    assert match(p, {}) is False


def test_non_dict_group_rejects() -> None:
    p = {"pair_analyses": [_pair(
        [0, 1], [0, 1],
        groups=[_group([0], [1]), "not-a-dict"],
        num_groups=2, total_changes=2,
    )]}
    assert match(p, {}) is False


# ----------------------------------------------------------------------
# strict-type gates on palette / colour-list fields
# ----------------------------------------------------------------------

def test_non_list_input_palette_rejects() -> None:
    for bad in (None, 42, "oops", {"a": 1}, (0, 1), True, {0, 1}):
        analysis = _pair([0, 1], [0, 1],
                         groups=[_group([0], [1]), _group([1], [0])],
                         num_groups=2, total_changes=2)
        analysis["input_palette"] = bad
        assert match({"pair_analyses": [analysis]}, {}) is False, (
            f"input_palette={bad!r} should not fire"
        )


def test_non_list_output_palette_rejects() -> None:
    for bad in (None, 42, "oops", {"a": 1}, (0, 1), True, {0, 1}):
        analysis = _pair([0, 1], [0, 1],
                         groups=[_group([0], [1]), _group([1], [0])],
                         num_groups=2, total_changes=2)
        analysis["output_palette"] = bad
        assert match({"pair_analyses": [analysis]}, {}) is False, (
            f"output_palette={bad!r} should not fire"
        )


def test_bool_in_input_palette_rejects() -> None:
    analysis = _pair([0, 1], [0, 1],
                     groups=[_group([0], [1]), _group([1], [0])],
                     num_groups=2, total_changes=2)
    analysis["input_palette"] = [0, True, 2]
    assert match({"pair_analyses": [analysis]}, {}) is False


def test_bool_in_output_palette_rejects() -> None:
    analysis = _pair([0, 1], [0, 1],
                     groups=[_group([0], [1]), _group([1], [0])],
                     num_groups=2, total_changes=2)
    analysis["output_palette"] = [False, 1]
    assert match({"pair_analyses": [analysis]}, {}) is False


def test_non_int_palette_rejects() -> None:
    analysis = _pair([0, 1], [0, 1],
                     groups=[_group([0], [1]), _group([1], [0])],
                     num_groups=2, total_changes=2)
    analysis["input_palette"] = [0, "1"]
    assert match({"pair_analyses": [analysis]}, {}) is False

    analysis2 = _pair([0, 1], [0, 1],
                      groups=[_group([0], [1]), _group([1], [0])],
                      num_groups=2, total_changes=2)
    analysis2["output_palette"] = [0.0, 1.0]
    assert match({"pair_analyses": [analysis2]}, {}) is False


def test_missing_input_colors_in_group_rejects() -> None:
    p = {"pair_analyses": [_pair(
        [0, 1], [0, 1],
        groups=[{"output_colors": [1]}],
        num_groups=1, total_changes=1,
    )]}
    assert match(p, {}) is False


def test_missing_output_colors_in_group_rejects() -> None:
    p = {"pair_analyses": [_pair(
        [0, 1], [0, 1],
        groups=[{"input_colors": [1]}],
        num_groups=1, total_changes=1,
    )]}
    assert match(p, {}) is False


def test_empty_input_colors_in_group_rejects() -> None:
    p = {"pair_analyses": [_pair(
        [0, 1], [0, 1],
        groups=[_group([], [1])],
        num_groups=1, total_changes=1,
    )]}
    assert match(p, {}) is False


def test_empty_output_colors_in_group_rejects() -> None:
    p = {"pair_analyses": [_pair(
        [0, 1], [0, 1],
        groups=[_group([1], [])],
        num_groups=1, total_changes=1,
    )]}
    assert match(p, {}) is False


def test_bool_in_change_colors_rejects() -> None:
    p1 = {"pair_analyses": [_pair(
        [0, 1], [0, 1],
        groups=[_group([True], [1])],
        num_groups=1, total_changes=1,
    )]}
    assert match(p1, {}) is False
    p2 = {"pair_analyses": [_pair(
        [0, 1], [0, 1],
        groups=[_group([1], [True])],
        num_groups=1, total_changes=1,
    )]}
    assert match(p2, {}) is False


def test_out_of_range_change_color_rejects() -> None:
    p = {"pair_analyses": [_pair(
        [0, 1], [0, 1],
        groups=[_group([1, 10], [1])],
        num_groups=1, total_changes=1,
    )]}
    assert match(p, {}) is False


def test_non_int_change_color_rejects() -> None:
    p = {"pair_analyses": [_pair(
        [0, 1], [0, 1],
        groups=[_group([1, "x"], [1])],
        num_groups=1, total_changes=1,
    )]}
    assert match(p, {}) is False


# ----------------------------------------------------------------------
# behavioural contract
# ----------------------------------------------------------------------

def test_match_is_deterministic() -> None:
    p = {"pair_analyses": [_pair(
        [0, 1, 2], [0, 1, 2],
        groups=[_group([1], [2]), _group([2], [1])],
        num_groups=2, total_changes=2,
    )]}
    results = [match(p, {}) for _ in range(5)]
    assert len(set(results)) == 1 and results[0] is True


def test_match_returns_literal_bool() -> None:
    p_pos = {"pair_analyses": [_pair(
        [0, 1, 2], [0, 1, 2],
        groups=[_group([1], [2]), _group([2], [1])],
        num_groups=2, total_changes=2,
    )]}
    p_neg = {"pair_analyses": [_pair(
        [0, 1, 2], [0, 1, 2],
        groups=[_group([1], [0]), _group([2], [0])],
        num_groups=2, total_changes=2,
    )]}
    assert match(p_pos, {}) is True
    assert match(p_neg, {}) is False


def test_params_ignored() -> None:
    p = {"pair_analyses": [_pair(
        [0, 1, 2], [0, 1, 2],
        groups=[_group([1], [2]), _group([2], [1])],
        num_groups=2, total_changes=2,
    )]}
    assert match(p, {}) is True
    assert match(p, {"foo": "bar"}) is True
    assert match(p, {"injective": False}) is True  # params do not gate


def test_does_not_mutate_input() -> None:
    p = {"pair_analyses": [_pair(
        [0, 1, 2], [0, 1, 2],
        groups=[_group([1], [2]), _group([2], [1])],
        num_groups=2, total_changes=2,
    )]}
    before = copy.deepcopy(p)
    match(p, {})
    assert p == before, "matcher mutated patterns"


# ----------------------------------------------------------------------
# orthogonality / refinement wiring (via recognized_conditions)
# ----------------------------------------------------------------------

def test_permutation_fixture_co_fires_iter_185_and_iter_8() -> None:
    # The strict-implication wiring: a fixture that fires this matcher
    # MUST also fire iter 185 (palette equality) AND iter 8
    # (consistent mapping). Asymmetry: the converse does not hold
    # (see the collapse-recolour fixture below).
    from agent.conditions import recognized_conditions
    p = {"pair_analyses": [_pair(
        [0, 1, 2], [0, 1, 2],
        groups=[_group([1], [2]), _group([2], [1])],
        num_groups=2, total_changes=2,
    )]}
    fired = set(recognized_conditions(p))
    assert _NAME in fired
    assert "output_palette_equals_input" in fired
    assert "consistent_color_mapping" in fired


def test_collapse_fixture_excludes_this_matcher_only() -> None:
    # The strict-refinement witness: iter 185 AND iter 8 fire, but
    # this matcher REJECTS (injectivity fails). This is the new axis
    # the matcher is named to gate.
    from agent.conditions import recognized_conditions
    p = {"pair_analyses": [_pair(
        [0, 1, 2], [0, 1, 2],
        groups=[_group([1], [0]), _group([2], [0])],
        num_groups=2, total_changes=2,
    )]}
    fired = set(recognized_conditions(p))
    assert "output_palette_equals_input" in fired
    assert "consistent_color_mapping" in fired
    assert _NAME not in fired


def test_identity_fixture_excludes_this_matcher_but_fires_iter_185() -> None:
    # iter 13 / iter 185 fire on identity; this matcher REJECTS
    # (no change-cell observations).
    from agent.conditions import recognized_conditions
    p = {
        "grid_size_preserved": True,
        "pair_analyses": [_pair([0, 1, 2], [0, 1, 2])],
    }
    fired = set(recognized_conditions(p))
    assert "identity_transformation" in fired
    assert "output_palette_equals_input" in fired
    assert _NAME not in fired


def test_erasure_fixture_excludes_this_matcher() -> None:
    # An erasure fires iter 184 (subset) but NOT iter 185 (palette
    # equality); this matcher REJECTS via iter 185's gate.
    from agent.conditions import recognized_conditions
    p = {"pair_analyses": [_pair(
        [0, 1, 2], [0, 1],
        groups=[_group([2], [1])],
        num_groups=1, total_changes=1,
    )]}
    fired = set(recognized_conditions(p))
    assert "output_palette_subset_of_input" in fired
    assert "output_palette_equals_input" not in fired
    assert _NAME not in fired
