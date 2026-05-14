"""
tests/test_output_colors_proper_subset_of_input_colors_per_group.py --
exercise the iter-204 matcher
``agent.conditions.output_colors_proper_subset_of_input_colors_per_group``
(new in this iter).

Pins the matcher's contract per the module docstring: every change
group in every example pair satisfies
``set(group["output_colors"]) < set(group["input_colors"])`` -- output
set is contained in input set AND strictly smaller per group.

This matcher is the strict-refinement of iter 200
(``output_colors_subset_of_input_colors_per_group``) EXCLUDING the
iter-201 equality cell (per-group strict-erasure). The strict-
refinement relation is pinned by ``test_strictly_implies_iter200``
(this matcher fires -> iter 200 fires) and
``test_iter200_fires_but_this_matcher_rejects_on_per_group_equality``
(per-group equality fires iter 200 but rejects this matcher). The
strict mutual exclusion with iter 201 is pinned by
``test_mutually_exclusive_with_iter201_on_non_empty_palettes``.

Runs without pytest:

    python tests/test_output_colors_proper_subset_of_input_colors_per_group.py

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


MATCHER_NAME = "output_colors_proper_subset_of_input_colors_per_group"


def _matcher():
    return CONDITION_REGISTRY[MATCHER_NAME]


def _group(*, input_colors=(1, 2), output_colors=(1,), positions=None):
    """Build a group analysis dict matching ``_analyze_pair``'s emit shape."""
    if positions is None:
        positions = [(0, 0)]
    sorted_positions = sorted(tuple(p) for p in positions)
    if sorted_positions:
        top_row = min(r for r, _ in sorted_positions)
        top_col = min(c for _, c in sorted_positions)
    else:
        top_row = 0
        top_col = 0
    return {
        "input_colors": sorted(set(input_colors)),
        "output_colors": sorted(set(output_colors)),
        "top_row": top_row,
        "top_col": top_col,
        "cell_count": len(sorted_positions),
        "positions": sorted_positions,
    }


def _analysis(*, groups, input_height=4, input_width=4,
              output_height=None, output_width=None, size_match=None,
              num_groups=None, input_palette=None, output_palette=None):
    if output_height is None:
        output_height = input_height
    if output_width is None:
        output_width = input_width
    if size_match is None:
        size_match = (input_height == output_height
                      and input_width == output_width)
    if num_groups is None:
        num_groups = len(groups)
    analysis = {
        "total_changes": sum(g.get("cell_count", 0) for g in groups),
        "num_groups": num_groups,
        "groups": list(groups),
        "size_match": size_match,
        "input_height": input_height,
        "input_width": input_width,
        "output_height": output_height,
        "output_width": output_width,
    }
    if input_palette is not None:
        analysis["input_palette"] = list(input_palette)
    if output_palette is not None:
        analysis["output_palette"] = list(output_palette)
    return analysis


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
# Positive cases -- per-group output ⊂ per-group input strictly per group.
# ──────────────────────────────────────────────────────────────────────────

def test_returns_true_on_single_pair_single_group_proper_subset() -> None:
    # output_colors=[1] ⊂ input_colors=[1, 2]
    patterns = {"pair_analyses": [
        _analysis(groups=[_group(input_colors=[1, 2], output_colors=[1])]),
    ]}
    assert _matcher()(patterns, {}) is True


def test_returns_true_on_two_pairs_proper_subset() -> None:
    patterns = {"pair_analyses": [
        _analysis(groups=[_group(input_colors=[1, 2], output_colors=[1])]),
        _analysis(groups=[_group(input_colors=[3, 4], output_colors=[3])]),
    ]}
    assert _matcher()(patterns, {}) is True


def test_returns_true_on_multi_group_per_pair_all_proper_subset() -> None:
    patterns = {"pair_analyses": [
        _analysis(groups=[
            _group(input_colors=[1, 2, 3], output_colors=[1, 2]),
            _group(input_colors=[4, 5], output_colors=[4]),
        ]),
        _analysis(groups=[
            _group(input_colors=[5, 6, 7], output_colors=[6]),
            _group(input_colors=[8, 9], output_colors=[8]),
        ]),
    ]}
    assert _matcher()(patterns, {}) is True


def test_returns_true_on_drop_multiple_colors() -> None:
    # output=[1] ⊂ input=[1, 2, 3, 4, 5] -- drops four colours.
    patterns = {"pair_analyses": [
        _analysis(groups=[_group(input_colors=[1, 2, 3, 4, 5],
                                 output_colors=[1])]),
    ]}
    assert _matcher()(patterns, {}) is True


def test_returns_true_on_three_pairs_all_proper_subset() -> None:
    patterns = {"pair_analyses": [
        _analysis(groups=[_group(input_colors=[1, 2], output_colors=[2])]),
        _analysis(groups=[_group(input_colors=[3, 4], output_colors=[3])]),
        _analysis(groups=[_group(input_colors=[5, 6, 7], output_colors=[5])]),
    ]}
    assert _matcher()(patterns, {}) is True


def test_returns_true_on_varying_num_groups_per_pair_all_proper() -> None:
    patterns = {"pair_analyses": [
        _analysis(groups=[_group(input_colors=[1, 2], output_colors=[2])]),
        _analysis(groups=[
            _group(input_colors=[2, 3], output_colors=[2]),
            _group(input_colors=[4, 5], output_colors=[4]),
        ]),
        _analysis(groups=[
            _group(input_colors=[5, 6, 7], output_colors=[5, 6]),
            _group(input_colors=[7, 8, 9], output_colors=[7]),
            _group(input_colors=[0, 1], output_colors=[0]),
        ]),
    ]}
    assert _matcher()(patterns, {}) is True


def test_returns_true_on_color_zero_drop() -> None:
    # Colour 0 is a valid strict int; dropping it is a valid strict erasure.
    patterns = {"pair_analyses": [
        _analysis(groups=[_group(input_colors=[0, 5], output_colors=[5])]),
    ]}
    assert _matcher()(patterns, {}) is True


def test_returns_true_on_color_nine_drop() -> None:
    # Colour 9 is a valid strict int.
    patterns = {"pair_analyses": [
        _analysis(groups=[_group(input_colors=[8, 9], output_colors=[8])]),
    ]}
    assert _matcher()(patterns, {}) is True


def test_returns_true_on_full_palette_drop() -> None:
    # input=[0..9] (full palette) / output=[0..4] (half) -- proper subset.
    patterns = {"pair_analyses": [
        _analysis(groups=[_group(
            input_colors=[0, 1, 2, 3, 4, 5, 6, 7, 8, 9],
            output_colors=[0, 1, 2, 3, 4],
        )]),
    ]}
    assert _matcher()(patterns, {}) is True


# ──────────────────────────────────────────────────────────────────────────
# Negative cases -- equality / fresh colour / disjoint / palette-expansion.
# ──────────────────────────────────────────────────────────────────────────

def test_returns_false_on_per_group_equality_singleton() -> None:
    # input=[1] / output=[1] -- per-group equality (iter 201 fires). This
    # matcher MUST reject (proper subset excludes equality).
    patterns = {"pair_analyses": [
        _analysis(groups=[_group(input_colors=[1], output_colors=[1])]),
    ]}
    assert _matcher()(patterns, {}) is False


def test_returns_false_on_per_group_equality_multi_color() -> None:
    # input=[1, 2] / output=[1, 2] -- per-group equality. This matcher
    # rejects.
    patterns = {"pair_analyses": [
        _analysis(groups=[_group(input_colors=[1, 2], output_colors=[1, 2])]),
    ]}
    assert _matcher()(patterns, {}) is False


def test_returns_false_when_fresh_color_on_single_group() -> None:
    # output_colors=[2] not in input_colors=[1] -- fresh, not a subset.
    patterns = {"pair_analyses": [
        _analysis(groups=[_group(input_colors=[1], output_colors=[2])]),
    ]}
    assert _matcher()(patterns, {}) is False


def test_returns_false_when_partial_overlap_one_fresh() -> None:
    # output=[1, 3] includes 1 (in input) AND 3 (not in input). Not a
    # subset relation at all.
    patterns = {"pair_analyses": [
        _analysis(groups=[_group(input_colors=[1, 2],
                                 output_colors=[1, 3])]),
    ]}
    assert _matcher()(patterns, {}) is False


def test_returns_false_when_palette_expansion_per_group() -> None:
    # output=[1, 2] ⊋ input=[1] -- palette expansion (iter 202 fires).
    # This matcher rejects (output NOT contained in input).
    patterns = {"pair_analyses": [
        _analysis(groups=[_group(input_colors=[1], output_colors=[1, 2])]),
    ]}
    assert _matcher()(patterns, {}) is False


def test_returns_false_when_fully_disjoint() -> None:
    # input=[1, 2, 3] / output=[4, 5, 6] -- fully disjoint (iter 203
    # fires). This matcher rejects.
    patterns = {"pair_analyses": [
        _analysis(groups=[_group(input_colors=[1, 2, 3],
                                 output_colors=[4, 5, 6])]),
    ]}
    assert _matcher()(patterns, {}) is False


def test_returns_false_when_second_group_equality_in_first_pair() -> None:
    # First group OK (proper subset), second group equality -- single
    # equality group dooms the universal proper-subset claim.
    patterns = {"pair_analyses": [
        _analysis(groups=[
            _group(input_colors=[1, 2], output_colors=[1]),
            _group(input_colors=[3], output_colors=[3]),
        ]),
    ]}
    assert _matcher()(patterns, {}) is False


def test_returns_false_when_second_pair_equality() -> None:
    patterns = {"pair_analyses": [
        _analysis(groups=[_group(input_colors=[1, 2], output_colors=[1])]),
        _analysis(groups=[_group(input_colors=[3], output_colors=[3])]),
    ]}
    assert _matcher()(patterns, {}) is False


def test_returns_false_when_second_pair_palette_expansion() -> None:
    patterns = {"pair_analyses": [
        _analysis(groups=[_group(input_colors=[1, 2], output_colors=[1])]),
        _analysis(groups=[_group(input_colors=[3], output_colors=[3, 4])]),
    ]}
    assert _matcher()(patterns, {}) is False


def test_returns_false_on_identity_all_zero_groups() -> None:
    # Identity territory (iter 13). Fail-closed on empty-groups.
    patterns = {"pair_analyses": [
        _analysis(groups=[]),
        _analysis(groups=[]),
    ]}
    assert _matcher()(patterns, {}) is False


def test_returns_false_when_one_pair_has_zero_groups() -> None:
    # Mixed identity / non-identity task is disqualified.
    patterns = {"pair_analyses": [
        _analysis(groups=[_group(input_colors=[1, 2], output_colors=[1])]),
        _analysis(groups=[]),
    ]}
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
    assert _matcher()({"pair_analyses": [None]}, {}) is False
    assert _matcher()({"pair_analyses": ["string"]}, {}) is False
    assert _matcher()({"pair_analyses": [42]}, {}) is False


# ──────────────────────────────────────────────────────────────────────────
# Strict-type gates on ``groups`` / ``input_colors`` / ``output_colors``.
# ──────────────────────────────────────────────────────────────────────────

def test_returns_false_on_missing_groups_field() -> None:
    analysis_bad = {
        "size_match": True,
        "total_changes": 1,
        "num_groups": 1,
        "input_height": 3, "input_width": 3,
        "output_height": 3, "output_width": 3,
    }
    assert _matcher()({"pair_analyses": [analysis_bad]}, {}) is False


def test_returns_false_on_non_list_groups() -> None:
    for bad in (None, "string", 42, {"k": "v"}):
        analysis_bad = {
            "size_match": True,
            "total_changes": 1,
            "num_groups": 1,
            "input_height": 3, "input_width": 3,
            "output_height": 3, "output_width": 3,
            "groups": bad,
        }
        assert _matcher()({"pair_analyses": [analysis_bad]}, {}) is False, (
            f"groups={bad!r} should fail-closed"
        )


def test_returns_false_on_non_dict_group_entry() -> None:
    for bad in (None, "string", 42, [1, 2]):
        analysis_bad = _analysis(groups=[])
        analysis_bad["groups"] = [bad]
        assert _matcher()({"pair_analyses": [analysis_bad]}, {}) is False, (
            f"group entry {bad!r} should fail-closed"
        )


def test_returns_false_on_missing_input_colors() -> None:
    group_bad = {
        "output_colors": [3],
        "top_row": 0, "top_col": 0,
        "positions": [(0, 0)],
        "cell_count": 1,
    }
    analysis_bad = _analysis(groups=[])
    analysis_bad["groups"] = [group_bad]
    assert _matcher()({"pair_analyses": [analysis_bad]}, {}) is False


def test_returns_false_on_missing_output_colors() -> None:
    group_bad = {
        "input_colors": [3],
        "top_row": 0, "top_col": 0,
        "positions": [(0, 0)],
        "cell_count": 1,
    }
    analysis_bad = _analysis(groups=[])
    analysis_bad["groups"] = [group_bad]
    assert _matcher()({"pair_analyses": [analysis_bad]}, {}) is False


def test_returns_false_on_non_list_input_colors() -> None:
    for bad in (None, 1, "1", {1: 2}, (1,)):
        group_bad = {
            "input_colors": bad,
            "output_colors": [3],
            "top_row": 0, "top_col": 0,
            "positions": [(0, 0)],
            "cell_count": 1,
        }
        analysis_bad = _analysis(groups=[])
        analysis_bad["groups"] = [group_bad]
        assert _matcher()({"pair_analyses": [analysis_bad]}, {}) is False, (
            f"input_colors={bad!r} should fail-closed"
        )


def test_returns_false_on_non_list_output_colors() -> None:
    for bad in (None, 1, "1", {1: 2}, (1,)):
        group_bad = {
            "input_colors": [1],
            "output_colors": bad,
            "top_row": 0, "top_col": 0,
            "positions": [(0, 0)],
            "cell_count": 1,
        }
        analysis_bad = _analysis(groups=[])
        analysis_bad["groups"] = [group_bad]
        assert _matcher()({"pair_analyses": [analysis_bad]}, {}) is False, (
            f"output_colors={bad!r} should fail-closed"
        )


def test_returns_false_on_empty_input_colors_list() -> None:
    group_bad = {
        "input_colors": [],
        "output_colors": [3],
        "top_row": 0, "top_col": 0,
        "positions": [(0, 0)],
        "cell_count": 1,
    }
    analysis_bad = _analysis(groups=[])
    analysis_bad["groups"] = [group_bad]
    assert _matcher()({"pair_analyses": [analysis_bad]}, {}) is False


def test_returns_false_on_empty_output_colors_list() -> None:
    group_bad = {
        "input_colors": [1],
        "output_colors": [],
        "top_row": 0, "top_col": 0,
        "positions": [(0, 0)],
        "cell_count": 1,
    }
    analysis_bad = _analysis(groups=[])
    analysis_bad["groups"] = [group_bad]
    assert _matcher()({"pair_analyses": [analysis_bad]}, {}) is False


def test_returns_false_on_bool_in_input_colors() -> None:
    for bad in (True, False):
        group_bad = {
            "input_colors": [bad],
            "output_colors": [3],
            "top_row": 0, "top_col": 0,
            "positions": [(0, 0)],
            "cell_count": 1,
        }
        analysis_bad = _analysis(groups=[])
        analysis_bad["groups"] = [group_bad]
        assert _matcher()({"pair_analyses": [analysis_bad]}, {}) is False, (
            f"input_colors=[{bad!r}] (bool) should fail-closed"
        )


def test_returns_false_on_bool_in_output_colors() -> None:
    for bad in (True, False):
        group_bad = {
            "input_colors": [1],
            "output_colors": [bad],
            "top_row": 0, "top_col": 0,
            "positions": [(0, 0)],
            "cell_count": 1,
        }
        analysis_bad = _analysis(groups=[])
        analysis_bad["groups"] = [group_bad]
        assert _matcher()({"pair_analyses": [analysis_bad]}, {}) is False, (
            f"output_colors=[{bad!r}] (bool) should fail-closed"
        )


def test_returns_false_on_out_of_range_input_color() -> None:
    for bad in (-1, 10, 100):
        group_bad = {
            "input_colors": [bad],
            "output_colors": [3],
            "top_row": 0, "top_col": 0,
            "positions": [(0, 0)],
            "cell_count": 1,
        }
        analysis_bad = _analysis(groups=[])
        analysis_bad["groups"] = [group_bad]
        assert _matcher()({"pair_analyses": [analysis_bad]}, {}) is False, (
            f"input_colors=[{bad!r}] (out-of-range) should fail-closed"
        )


def test_returns_false_on_out_of_range_output_color() -> None:
    for bad in (-1, 10, 100):
        group_bad = {
            "input_colors": [1],
            "output_colors": [bad],
            "top_row": 0, "top_col": 0,
            "positions": [(0, 0)],
            "cell_count": 1,
        }
        analysis_bad = _analysis(groups=[])
        analysis_bad["groups"] = [group_bad]
        assert _matcher()({"pair_analyses": [analysis_bad]}, {}) is False, (
            f"output_colors=[{bad!r}] (out-of-range) should fail-closed"
        )


def test_returns_false_on_non_int_input_color() -> None:
    for bad in (0.5, "1", None, [1]):
        group_bad = {
            "input_colors": [bad],
            "output_colors": [3],
            "top_row": 0, "top_col": 0,
            "positions": [(0, 0)],
            "cell_count": 1,
        }
        analysis_bad = _analysis(groups=[])
        analysis_bad["groups"] = [group_bad]
        assert _matcher()({"pair_analyses": [analysis_bad]}, {}) is False, (
            f"input_colors=[{bad!r}] ({type(bad).__name__}) should fail-closed"
        )


def test_returns_false_on_non_int_output_color() -> None:
    for bad in (0.5, "1", None, [1]):
        group_bad = {
            "input_colors": [1],
            "output_colors": [bad],
            "top_row": 0, "top_col": 0,
            "positions": [(0, 0)],
            "cell_count": 1,
        }
        analysis_bad = _analysis(groups=[])
        analysis_bad["groups"] = [group_bad]
        assert _matcher()({"pair_analyses": [analysis_bad]}, {}) is False, (
            f"output_colors=[{bad!r}] ({type(bad).__name__}) should fail-closed"
        )


def test_returns_false_on_second_pair_malformed() -> None:
    pair0 = _analysis(groups=[_group(input_colors=[1, 2], output_colors=[1])])
    pair1_bad = _analysis(groups=[])
    pair1_bad["groups"] = ["not-a-dict"]
    assert _matcher()({"pair_analyses": [pair0, pair1_bad]}, {}) is False


# ──────────────────────────────────────────────────────────────────────────
# Behavioural contract: side-effect-free, deterministic, strict bool.
# ──────────────────────────────────────────────────────────────────────────

def test_is_side_effect_free_on_inputs() -> None:
    patterns = {"pair_analyses": [
        _analysis(groups=[
            _group(input_colors=[1, 2], output_colors=[1]),
            _group(input_colors=[3, 4], output_colors=[3]),
        ]),
        _analysis(groups=[_group(input_colors=[5, 6], output_colors=[5])]),
    ]}
    params = {"unused": 1}
    before_p = copy.deepcopy(patterns)
    before_q = copy.deepcopy(params)
    _matcher()(patterns, params)
    assert patterns == before_p, "matcher mutated patterns"
    assert params == before_q, "matcher mutated params"


def test_is_deterministic_across_repeats() -> None:
    patterns = {"pair_analyses": [
        _analysis(groups=[_group(input_colors=[1, 2], output_colors=[1])]),
        _analysis(groups=[_group(input_colors=[3, 4], output_colors=[3])]),
    ]}
    results = [_matcher()(patterns, {}) for _ in range(5)]
    assert len(set(results)) == 1, f"non-deterministic outputs: {results}"


def test_returns_strict_boolean_type() -> None:
    pos_pat = {"pair_analyses": [
        _analysis(groups=[_group(input_colors=[1, 2], output_colors=[1])]),
    ]}
    neg_pat = {"pair_analyses": [
        _analysis(groups=[_group(input_colors=[1], output_colors=[1])]),
    ]}
    pos = _matcher()(pos_pat, {})
    neg = _matcher()(neg_pat, {})
    assert pos is True, f"expected literal True, got {pos!r}"
    assert neg is False, f"expected literal False, got {neg!r}"


def test_params_argument_ignored() -> None:
    patterns = {"pair_analyses": [
        _analysis(groups=[_group(input_colors=[1, 2], output_colors=[1])]),
    ]}
    assert _matcher()(patterns, {}) is True
    assert _matcher()(patterns, {"target": 99}) is True
    assert _matcher()(patterns, {"K": 7, "junk": [1, 2]}) is True


def test_whole_grid_palette_fields_ignored() -> None:
    # The matcher operates on per-group ``input_colors`` / ``output_colors``
    # only; whole-grid palette fields on the analysis dict must be
    # irrelevant.
    patterns = {"pair_analyses": [
        _analysis(
            groups=[_group(input_colors=[1, 2], output_colors=[1])],
            input_palette=[1, 2, 3, 4, 5, 6, 7, 8, 9],
            output_palette=[0],
        ),
    ]}
    assert _matcher()(patterns, {}) is True


# ──────────────────────────────────────────────────────────────────────────
# Orthogonality / refinement against neighbouring matchers.
# ──────────────────────────────────────────────────────────────────────────

def test_mutually_exclusive_with_identity_transformation() -> None:
    identity_pat = {
        "grid_size_preserved": True,
        "pair_analyses": [
            _analysis(groups=[]),
            _analysis(groups=[]),
        ],
    }
    paint_pat = {
        "grid_size_preserved": True,
        "pair_analyses": [
            _analysis(groups=[_group(input_colors=[1, 2], output_colors=[1])]),
        ],
    }
    identity = CONDITION_REGISTRY["identity_transformation"]
    assert identity(identity_pat, {}) is True
    assert _matcher()(identity_pat, {}) is False
    assert identity(paint_pat, {}) is False
    assert _matcher()(paint_pat, {}) is True


def test_strictly_implies_iter200_per_group_subset() -> None:
    # The strict-refinement-from-iter-200 relation: wherever this matcher
    # fires, iter 200 fires. The implication holds universally over the
    # input domain (proper subset implies subset).
    patterns_list = [
        {"pair_analyses": [
            _analysis(groups=[_group(input_colors=[1, 2], output_colors=[1])])
        ]},
        {"pair_analyses": [
            _analysis(groups=[_group(input_colors=[1, 2, 3],
                                     output_colors=[1, 2])])
        ]},
        {"pair_analyses": [
            _analysis(groups=[
                _group(input_colors=[1, 2], output_colors=[1]),
                _group(input_colors=[3, 4], output_colors=[4]),
            ])
        ]},
    ]
    iter200 = CONDITION_REGISTRY[
        "output_colors_subset_of_input_colors_per_group"
    ]
    for patterns in patterns_list:
        if _matcher()(patterns, {}) is True:
            assert iter200(patterns, {}) is True, (
                f"this matcher fires but iter 200 does NOT on {patterns!r} -- "
                f"strict-refinement-from-iter-200 violated"
            )


def test_iter200_fires_but_this_matcher_rejects_on_per_group_equality() -> None:
    # The KEY strict-refinement witness: per-group equality. Iter 200
    # fires (equality is a subset), but this matcher rejects (equality is
    # NOT a proper subset).
    patterns = {"pair_analyses": [
        _analysis(groups=[_group(input_colors=[1, 2], output_colors=[1, 2])]),
    ]}
    iter200 = CONDITION_REGISTRY[
        "output_colors_subset_of_input_colors_per_group"
    ]
    assert iter200(patterns, {}) is True, (
        "iter 200 must fire on per-group equality (equality is a subset)"
    )
    assert _matcher()(patterns, {}) is False, (
        "this matcher must reject on per-group equality (NOT a proper subset)"
    )


def test_mutually_exclusive_with_iter201_on_non_empty_palettes() -> None:
    # Strict mutual exclusion with iter 201: set equality forbids strict
    # proper subset by construction. Verify on the equality cell (iter 201
    # fires, this matcher rejects) AND on the proper-subset cell (this
    # matcher fires, iter 201 rejects).
    equality_pat = {"pair_analyses": [
        _analysis(groups=[_group(input_colors=[1, 2], output_colors=[1, 2])]),
    ]}
    proper_subset_pat = {"pair_analyses": [
        _analysis(groups=[_group(input_colors=[1, 2], output_colors=[1])]),
    ]}
    iter201 = CONDITION_REGISTRY[
        "output_colors_equals_input_colors_per_group"
    ]
    assert iter201(equality_pat, {}) is True
    assert _matcher()(equality_pat, {}) is False
    assert iter201(proper_subset_pat, {}) is False
    assert _matcher()(proper_subset_pat, {}) is True


def test_mutually_exclusive_with_iter202_on_non_empty_palettes() -> None:
    # Strict mutual exclusion with iter 202 (input ⊆ output per group):
    # proper output ⊂ input AND input ⊆ output is impossible on non-empty
    # palettes. Verify on the palette-expansion cell (iter 202 fires,
    # this matcher rejects).
    expansion_pat = {"pair_analyses": [
        _analysis(groups=[_group(input_colors=[1], output_colors=[1, 2])]),
    ]}
    iter202 = CONDITION_REGISTRY[
        "input_colors_subset_of_output_colors_per_group"
    ]
    assert iter202(expansion_pat, {}) is True
    assert _matcher()(expansion_pat, {}) is False
    # And on the strict-erasure cell, iter 202 must reject.
    erasure_pat = {"pair_analyses": [
        _analysis(groups=[_group(input_colors=[1, 2], output_colors=[1])]),
    ]}
    assert iter202(erasure_pat, {}) is False
    assert _matcher()(erasure_pat, {}) is True


def test_mutually_exclusive_with_iter203_on_non_empty_palettes() -> None:
    # Strict mutual exclusion with iter 203 (output disjoint from input
    # per group): output ⊂ input requires non-empty intersection with
    # input, but iter 203 requires empty intersection.
    disjoint_pat = {"pair_analyses": [
        _analysis(groups=[_group(input_colors=[1, 2], output_colors=[3])]),
    ]}
    iter203 = CONDITION_REGISTRY[
        "output_colors_disjoint_from_input_colors_per_group"
    ]
    assert iter203(disjoint_pat, {}) is True
    assert _matcher()(disjoint_pat, {}) is False
    # And on the strict-erasure cell, iter 203 must reject (output is a
    # proper subset of input, so they intersect non-trivially).
    erasure_pat = {"pair_analyses": [
        _analysis(groups=[_group(input_colors=[1, 2], output_colors=[1])]),
    ]}
    assert iter203(erasure_pat, {}) is False
    assert _matcher()(erasure_pat, {}) is True


def test_iter184_decoupling_on_per_blob_swap_with_erasure_witness() -> None:
    # Iter 184 fires on whole-grid output ⊆ input even when per-group
    # outputs go OUTSIDE per-group inputs (the swap witness). This matcher
    # rejects the swap. Confirm the two are decoupled here.
    swap_patterns = {
        "pair_analyses": [
            _analysis(
                groups=[
                    _group(input_colors=[1], output_colors=[2],
                           positions=[(0, 0)]),
                    _group(input_colors=[2], output_colors=[1],
                           positions=[(2, 0)]),
                ],
                input_palette=[1, 2],
                output_palette=[1, 2],
            ),
        ],
    }
    iter184 = CONDITION_REGISTRY["output_palette_subset_of_input"]
    assert iter184(swap_patterns, {}) is True
    assert _matcher()(swap_patterns, {}) is False


def test_iter186_strictly_mutually_exclusive_with_this_matcher() -> None:
    # Per-group output ⊂ per-group input means per-group output and per-
    # group input share at least one colour (output is non-empty subset
    # of input). With non-empty per-group palettes, the whole-grid
    # output and whole-grid input share that colour -- iter 186 (whole-
    # grid disjoint) MUST reject.
    erasure_patterns = {
        "pair_analyses": [
            _analysis(
                groups=[_group(input_colors=[1, 2], output_colors=[1])],
                input_palette=[1, 2],
                output_palette=[1],
            ),
        ],
    }
    iter186 = CONDITION_REGISTRY["output_palette_disjoint_from_input"]
    assert iter186(erasure_patterns, {}) is False
    assert _matcher()(erasure_patterns, {}) is True


def test_iter14_strict_mutual_exclusion_on_singleton_input() -> None:
    # Iter 14 pins every group's input_colors to a single colour. A
    # strict proper subset of a singleton is the empty set; this
    # matcher's cell-count requirement forbids empty per-group outputs.
    # So iter 14 firing implies this matcher rejects.
    singleton_patterns = {"pair_analyses": [
        _analysis(groups=[_group(input_colors=[1], output_colors=[2])]),
        _analysis(groups=[_group(input_colors=[1], output_colors=[3])]),
    ]}
    iter14 = CONDITION_REGISTRY["input_color_uniform"]
    assert iter14(singleton_patterns, {}) is True
    assert _matcher()(singleton_patterns, {}) is False


def test_iter18_co_fires_when_output_singleton_in_input() -> None:
    # Iter 18 (output_color_uniform) pins every group's output_colors to
    # the same single colour. If that colour is in every group's input
    # AND every group's input is strictly larger, both fire.
    co_fire_patterns = {"pair_analyses": [
        _analysis(groups=[_group(input_colors=[1, 2], output_colors=[1])]),
        _analysis(groups=[_group(input_colors=[1, 3], output_colors=[1])]),
    ]}
    iter18 = CONDITION_REGISTRY["output_color_uniform"]
    assert iter18(co_fire_patterns, {}) is True
    assert _matcher()(co_fire_patterns, {}) is True


def test_iter199_globally_constant_nonzero_shift_rejects_this_matcher() -> None:
    # A globally-constant non-zero shift makes every group's output set
    # disjoint from input set (iter 199 fires); this matcher rejects (not
    # a proper subset).
    patterns = {"pair_analyses": [
        _analysis(groups=[_group(input_colors=[1], output_colors=[4])]),
        _analysis(groups=[_group(input_colors=[2], output_colors=[5])]),
    ]}
    iter199 = CONDITION_REGISTRY[
        "palette_shift_constant_across_groups_and_pairs"
    ]
    assert iter199(patterns, {}) is True
    assert _matcher()(patterns, {}) is False


def test_co_fires_with_grid_size_preserved() -> None:
    # Orthogonal axes: grid_size_preserved is a dimensional flag, this
    # matcher inspects per-group palette content.
    patterns = {
        "grid_size_preserved": True,
        "pair_analyses": [
            _analysis(groups=[_group(input_colors=[1, 2], output_colors=[1])]),
        ],
    }
    iter1 = CONDITION_REGISTRY["grid_size_preserved"]
    assert iter1(patterns, {}) is True
    assert _matcher()(patterns, {}) is True


# ──────────────────────────────────────────────────────────────────────────
# Recognized-conditions wiring.
# ──────────────────────────────────────────────────────────────────────────

def test_recognized_conditions_includes_matcher_on_strict_erasure() -> None:
    from agent.conditions import recognized_conditions
    patterns = {
        "pair_analyses": [
            _analysis(groups=[_group(input_colors=[1, 2], output_colors=[1])]),
        ],
    }
    fired = recognized_conditions(patterns)
    assert MATCHER_NAME in fired, (
        f"{MATCHER_NAME!r} did not fire on per-group strict-erasure "
        f"patterns; got {fired!r}"
    )


def test_recognized_conditions_excludes_on_per_group_equality() -> None:
    # Per-group equality fires iter 200 / 201 but NOT this matcher.
    from agent.conditions import recognized_conditions
    patterns = {
        "pair_analyses": [
            _analysis(groups=[_group(input_colors=[1, 2], output_colors=[1, 2])]),
        ],
    }
    fired = recognized_conditions(patterns)
    assert MATCHER_NAME not in fired, (
        f"{MATCHER_NAME!r} must NOT fire on per-group equality; got "
        f"{fired!r}"
    )
    assert "output_colors_subset_of_input_colors_per_group" in fired, (
        "iter 200 must still fire on per-group equality (equality is "
        "a subset)"
    )
    assert "output_colors_equals_input_colors_per_group" in fired, (
        "iter 201 must still fire on per-group equality"
    )


def test_recognized_conditions_excludes_iter201_on_strict_erasure() -> None:
    # On per-group strict erasure, iter 200 fires (subset is satisfied),
    # this matcher fires (proper subset), but iter 201 does NOT (not an
    # equality).
    from agent.conditions import recognized_conditions
    patterns = {
        "pair_analyses": [
            _analysis(groups=[_group(input_colors=[1, 2], output_colors=[1])]),
        ],
    }
    fired = recognized_conditions(patterns)
    assert MATCHER_NAME in fired
    assert "output_colors_subset_of_input_colors_per_group" in fired
    assert "output_colors_equals_input_colors_per_group" not in fired


def test_recognized_conditions_excludes_iters_202_203_on_strict_erasure() -> None:
    # Mutual exclusion at the registry-wiring level: on per-group strict
    # erasure, neither iter 202 (palette expansion) nor iter 203 (disjoint)
    # fires.
    from agent.conditions import recognized_conditions
    patterns = {
        "pair_analyses": [
            _analysis(groups=[_group(input_colors=[1, 2], output_colors=[1])]),
        ],
    }
    fired = recognized_conditions(patterns)
    assert MATCHER_NAME in fired
    assert "input_colors_subset_of_output_colors_per_group" not in fired
    assert "output_colors_disjoint_from_input_colors_per_group" not in fired


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
