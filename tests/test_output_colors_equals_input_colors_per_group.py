"""
tests/test_output_colors_equals_input_colors_per_group.py -- exercise
the iter-201 matcher
``agent.conditions.output_colors_equals_input_colors_per_group``
(new in this iter).

Pins the matcher's contract per the module docstring: every change
group in every example pair satisfies
``set(group["output_colors"]) == set(group["input_colors"])``. The
matcher is the per-group projection of iter 185
(``output_palette_equals_input``, whole-grid scope) AND the strict
refinement of iter 200 (``output_colors_subset_of_input_colors_per_
group``, per-group subset). Key witnesses pinned below:

  * Strict-refinement witness: per-group proper subset (input=[1,2],
    output=[1]) fires iter 200 but rejects this matcher.
  * Decoupling witness: per-blob swap (group A {1}->{2}, group B
    {2}->{1}) fires iter 185 but rejects this matcher (per-group
    sets disagree).

Runs without pytest:

    python tests/test_output_colors_equals_input_colors_per_group.py

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


MATCHER_NAME = "output_colors_equals_input_colors_per_group"


def _matcher():
    return CONDITION_REGISTRY[MATCHER_NAME]


def _group(*, input_colors=(1,), output_colors=(1,), positions=None):
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
# Positive cases -- per-group output set == per-group input set universally.
# ──────────────────────────────────────────────────────────────────────────

def test_returns_true_on_single_pair_single_group_equal_singleton() -> None:
    patterns = {"pair_analyses": [
        _analysis(groups=[_group(input_colors=[1], output_colors=[1])]),
    ]}
    assert _matcher()(patterns, {}) is True


def test_returns_true_on_single_pair_single_group_equal_pair() -> None:
    patterns = {"pair_analyses": [
        _analysis(groups=[_group(input_colors=[1, 2],
                                 output_colors=[1, 2])]),
    ]}
    assert _matcher()(patterns, {}) is True


def test_returns_true_on_two_pairs_equal_palette_K1() -> None:
    patterns = {"pair_analyses": [
        _analysis(groups=[_group(input_colors=[1], output_colors=[1])]),
        _analysis(groups=[_group(input_colors=[2], output_colors=[2])]),
    ]}
    assert _matcher()(patterns, {}) is True


def test_returns_true_on_multi_group_per_pair_all_equal() -> None:
    patterns = {"pair_analyses": [
        _analysis(groups=[
            _group(input_colors=[1, 2], output_colors=[1, 2]),
            _group(input_colors=[3, 4], output_colors=[3, 4]),
        ]),
        _analysis(groups=[
            _group(input_colors=[5, 6, 7], output_colors=[5, 6, 7]),
            _group(input_colors=[8, 9], output_colors=[8, 9]),
        ]),
    ]}
    assert _matcher()(patterns, {}) is True


def test_returns_true_on_three_pairs_all_per_group_equal() -> None:
    patterns = {"pair_analyses": [
        _analysis(groups=[_group(input_colors=[1, 2], output_colors=[1, 2])]),
        _analysis(groups=[_group(input_colors=[3, 4], output_colors=[3, 4])]),
        _analysis(groups=[_group(input_colors=[5, 6], output_colors=[5, 6])]),
    ]}
    assert _matcher()(patterns, {}) is True


def test_returns_true_on_varying_num_groups_per_pair_all_equal() -> None:
    patterns = {"pair_analyses": [
        _analysis(groups=[_group(input_colors=[1], output_colors=[1])]),
        _analysis(groups=[
            _group(input_colors=[2, 3], output_colors=[2, 3]),
            _group(input_colors=[4], output_colors=[4]),
        ]),
        _analysis(groups=[
            _group(input_colors=[5, 6], output_colors=[5, 6]),
            _group(input_colors=[7, 8, 9], output_colors=[7, 8, 9]),
            _group(input_colors=[0, 1], output_colors=[0, 1]),
        ]),
    ]}
    assert _matcher()(patterns, {}) is True


def test_returns_true_on_color_zero_equal() -> None:
    # Colour 0 (background) is a valid in-range strict int.
    patterns = {"pair_analyses": [
        _analysis(groups=[_group(input_colors=[0, 5], output_colors=[0, 5])]),
    ]}
    assert _matcher()(patterns, {}) is True


def test_returns_true_on_color_nine_equal() -> None:
    # Colour 9 (high-end) is a valid in-range strict int.
    patterns = {"pair_analyses": [
        _analysis(groups=[_group(input_colors=[8, 9], output_colors=[8, 9])]),
    ]}
    assert _matcher()(patterns, {}) is True


def test_returns_true_on_full_palette_equal_per_group() -> None:
    # Full 10-colour palette per group, equal per group.
    full = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9]
    patterns = {"pair_analyses": [
        _analysis(groups=[_group(input_colors=full, output_colors=full)]),
    ]}
    assert _matcher()(patterns, {}) is True


# ──────────────────────────────────────────────────────────────────────────
# Negative cases -- per-group sets disagree.
# ──────────────────────────────────────────────────────────────────────────

def test_returns_false_on_per_group_proper_subset_iter200_witness() -> None:
    # The KEY strict-refinement witness vs iter 200: per-group proper
    # subset fires iter 200 but rejects THIS matcher (output set
    # strict subset of input set).
    patterns = {"pair_analyses": [
        _analysis(groups=[_group(input_colors=[1, 2], output_colors=[1])]),
    ]}
    assert _matcher()(patterns, {}) is False


def test_returns_false_when_fresh_color_on_single_group() -> None:
    # output_colors=[2] != input_colors=[1].
    patterns = {"pair_analyses": [
        _analysis(groups=[_group(input_colors=[1], output_colors=[2])]),
    ]}
    assert _matcher()(patterns, {}) is False


def test_returns_false_when_partial_overlap_one_fresh() -> None:
    # output_colors=[1, 3] overlaps input_colors=[1, 2] but introduces 3.
    patterns = {"pair_analyses": [
        _analysis(groups=[_group(input_colors=[1, 2],
                                 output_colors=[1, 3])]),
    ]}
    assert _matcher()(patterns, {}) is False


def test_returns_false_when_second_group_violates_in_first_pair() -> None:
    # First group OK, second group has set inequality.
    patterns = {"pair_analyses": [
        _analysis(groups=[
            _group(input_colors=[1], output_colors=[1]),
            _group(input_colors=[2], output_colors=[3]),
        ]),
    ]}
    assert _matcher()(patterns, {}) is False


def test_returns_false_when_second_pair_violates() -> None:
    patterns = {"pair_analyses": [
        _analysis(groups=[_group(input_colors=[1, 2], output_colors=[1, 2])]),
        _analysis(groups=[_group(input_colors=[3], output_colors=[4])]),
    ]}
    assert _matcher()(patterns, {}) is False


def test_returns_false_when_one_group_fully_disjoint() -> None:
    # input=[1,2,3] / output=[4,5,6] -- fully disjoint per group.
    patterns = {"pair_analyses": [
        _analysis(groups=[_group(input_colors=[1, 2, 3],
                                 output_colors=[4, 5, 6])]),
    ]}
    assert _matcher()(patterns, {}) is False


def test_returns_false_on_output_strictly_grows_palette() -> None:
    # input=[1] / output=[1, 2] -- output is strict superset (would
    # fire input_colors_subset_of_output_colors_per_group, deferred
    # iter-200 next-gap), rejects this matcher.
    patterns = {"pair_analyses": [
        _analysis(groups=[_group(input_colors=[1], output_colors=[1, 2])]),
    ]}
    assert _matcher()(patterns, {}) is False


def test_returns_false_on_identity_all_zero_groups() -> None:
    # Identity territory (iter 13). Fail-closed on empty-groups keeps
    # disjoint from iter 13 by construction.
    patterns = {"pair_analyses": [
        _analysis(groups=[]),
        _analysis(groups=[]),
    ]}
    assert _matcher()(patterns, {}) is False


def test_returns_false_when_one_pair_has_zero_groups() -> None:
    # Mixed identity / non-identity task is also disqualified.
    patterns = {"pair_analyses": [
        _analysis(groups=[_group(input_colors=[1], output_colors=[1])]),
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
    pair0 = _analysis(groups=[_group(input_colors=[1], output_colors=[1])])
    pair1_bad = _analysis(groups=[])
    pair1_bad["groups"] = ["not-a-dict"]
    assert _matcher()({"pair_analyses": [pair0, pair1_bad]}, {}) is False


# ──────────────────────────────────────────────────────────────────────────
# Behavioural contract: side-effect-free, deterministic, strict bool.
# ──────────────────────────────────────────────────────────────────────────

def test_is_side_effect_free_on_inputs() -> None:
    patterns = {"pair_analyses": [
        _analysis(groups=[
            _group(input_colors=[1, 2], output_colors=[1, 2]),
            _group(input_colors=[3, 4], output_colors=[3, 4]),
        ]),
        _analysis(groups=[_group(input_colors=[5, 6], output_colors=[5, 6])]),
    ]}
    params = {"unused": 1}
    before_p = copy.deepcopy(patterns)
    before_q = copy.deepcopy(params)
    _matcher()(patterns, params)
    assert patterns == before_p, "matcher mutated patterns"
    assert params == before_q, "matcher mutated params"


def test_is_deterministic_across_repeats() -> None:
    patterns = {"pair_analyses": [
        _analysis(groups=[_group(input_colors=[1, 2], output_colors=[1, 2])]),
        _analysis(groups=[_group(input_colors=[3, 4], output_colors=[3, 4])]),
    ]}
    results = [_matcher()(patterns, {}) for _ in range(5)]
    assert len(set(results)) == 1, f"non-deterministic outputs: {results}"


def test_returns_strict_boolean_type() -> None:
    pos_pat = {"pair_analyses": [
        _analysis(groups=[_group(input_colors=[1], output_colors=[1])]),
    ]}
    neg_pat = {"pair_analyses": [
        _analysis(groups=[_group(input_colors=[1], output_colors=[2])]),
    ]}
    pos = _matcher()(pos_pat, {})
    neg = _matcher()(neg_pat, {})
    assert pos is True, f"expected literal True, got {pos!r}"
    assert neg is False, f"expected literal False, got {neg!r}"


def test_params_argument_ignored() -> None:
    patterns = {"pair_analyses": [
        _analysis(groups=[_group(input_colors=[1, 2], output_colors=[1, 2])]),
    ]}
    assert _matcher()(patterns, {}) is True
    assert _matcher()(patterns, {"target": 99}) is True
    assert _matcher()(patterns, {"K": 7, "junk": [1, 2]}) is True


def test_whole_grid_palette_fields_ignored() -> None:
    # The matcher inspects only per-group input/output colour sets;
    # the whole-grid input_palette / output_palette fields on the
    # analysis dict have no effect on this matcher's decision.
    patterns = {"pair_analyses": [
        _analysis(
            groups=[_group(input_colors=[1, 2], output_colors=[1, 2])],
            input_palette=[1, 2, 7, 8],  # whole-grid noise
            output_palette=[1, 2, 9],   # whole-grid noise
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
    permute_pat = {
        "grid_size_preserved": True,
        "pair_analyses": [
            _analysis(groups=[_group(input_colors=[1, 2],
                                     output_colors=[1, 2])]),
        ],
    }
    identity = CONDITION_REGISTRY["identity_transformation"]
    assert identity(identity_pat, {}) is True
    assert _matcher()(identity_pat, {}) is False
    assert identity(permute_pat, {}) is False
    assert _matcher()(permute_pat, {}) is True


def test_strictly_implies_iter200_per_group_subset() -> None:
    # Per-group equality strictly implies per-group subset
    # (set-equality is the strict refinement of subset).
    patterns = {"pair_analyses": [
        _analysis(groups=[
            _group(input_colors=[1, 2], output_colors=[1, 2]),
            _group(input_colors=[3], output_colors=[3]),
        ]),
        _analysis(groups=[_group(input_colors=[5, 6, 7],
                                 output_colors=[5, 6, 7])]),
    ]}
    iter200 = CONDITION_REGISTRY[
        "output_colors_subset_of_input_colors_per_group"
    ]
    assert _matcher()(patterns, {}) is True
    assert iter200(patterns, {}) is True, (
        "iter 200 must fire wherever this matcher fires (strict refinement)"
    )


def test_iter200_fires_but_this_matcher_rejects_on_proper_subset() -> None:
    # The KEY strict-refinement witness: per-group proper subset.
    # input=[1, 2] / output=[1] satisfies subset but NOT equality.
    patterns = {"pair_analyses": [
        _analysis(groups=[_group(input_colors=[1, 2], output_colors=[1])]),
    ]}
    iter200 = CONDITION_REGISTRY[
        "output_colors_subset_of_input_colors_per_group"
    ]
    assert iter200(patterns, {}) is True, (
        "iter 200 fires on proper subset"
    )
    assert _matcher()(patterns, {}) is False, (
        "this matcher must reject on proper subset (output != input)"
    )


def test_iter185_fires_but_this_matcher_rejects_on_per_group_swap() -> None:
    # The KEY structural-distinction witness vs iter 185 (whole-grid):
    # a per-blob colour swap.
    #   pair 0 group A: input=[1] -> output=[2]
    #   pair 0 group B: input=[2] -> output=[1]
    # Whole-grid input_palette = {1, 2}; whole-grid output_palette =
    # {1, 2}; iter 185 fires. But group A's output {2} != group A's
    # input {1}, so this matcher rejects.
    patterns = {
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
    iter185 = CONDITION_REGISTRY["output_palette_equals_input"]
    assert iter185(patterns, {}) is True, (
        "iter 185 must fire on whole-grid output == input"
    )
    assert _matcher()(patterns, {}) is False, (
        "this matcher must reject on per-group colour swap"
    )


def test_co_fires_with_iter185_on_aligned_palettes() -> None:
    # Per-group equality AND whole-grid output_palette == input_palette
    # per pair. Both fire.
    patterns = {
        "pair_analyses": [
            _analysis(
                groups=[_group(input_colors=[1, 2], output_colors=[1, 2])],
                input_palette=[1, 2],
                output_palette=[1, 2],
            ),
            _analysis(
                groups=[_group(input_colors=[3], output_colors=[3])],
                input_palette=[3],
                output_palette=[3],
            ),
        ],
    }
    iter185 = CONDITION_REGISTRY["output_palette_equals_input"]
    assert iter185(patterns, {}) is True
    assert _matcher()(patterns, {}) is True


def test_co_fires_with_iter184_on_aligned_palettes() -> None:
    # Per-group equality implies per-group subset, which implies
    # whole-grid subset on self-consistent patterns.
    patterns = {
        "pair_analyses": [
            _analysis(
                groups=[_group(input_colors=[1, 2], output_colors=[1, 2])],
                input_palette=[1, 2],
                output_palette=[1, 2],
            ),
        ],
    }
    iter184 = CONDITION_REGISTRY["output_palette_subset_of_input"]
    assert iter184(patterns, {}) is True
    assert _matcher()(patterns, {}) is True


def test_iter14_uniform_input_co_fire_when_output_same_color() -> None:
    # iter 14 (input_color_uniform) pins every group's input_colors to
    # the same single colour; this matcher requires output set == input
    # set per group, so the output must also be that same single colour.
    # Both fire.
    patterns = {"pair_analyses": [
        _analysis(groups=[_group(input_colors=[1], output_colors=[1])]),
        _analysis(groups=[_group(input_colors=[1], output_colors=[1])]),
    ]}
    iter14 = CONDITION_REGISTRY["input_color_uniform"]
    assert iter14(patterns, {}) is True
    assert _matcher()(patterns, {}) is True


def test_iter14_fires_but_this_matcher_rejects_on_uniform_input_fresh_output() -> None:
    # iter 14 fires (input_colors=[1] uniform) but output_colors=[2]
    # is fresh per group -- this matcher rejects.
    patterns = {"pair_analyses": [
        _analysis(groups=[_group(input_colors=[1], output_colors=[2])]),
        _analysis(groups=[_group(input_colors=[1], output_colors=[2])]),
    ]}
    iter14 = CONDITION_REGISTRY["input_color_uniform"]
    assert iter14(patterns, {}) is True
    assert _matcher()(patterns, {}) is False


def test_iter195_co_fires_when_K_equal_and_palettes_equal() -> None:
    # iter 195 pins per-group input cardinality constant across pairs;
    # this matcher pins per-group output set == input set. With per-
    # group K_in == 2 and per-group output == input universally, both
    # fire.
    patterns = {"pair_analyses": [
        _analysis(groups=[_group(input_colors=[1, 2], output_colors=[1, 2])]),
        _analysis(groups=[_group(input_colors=[3, 4], output_colors=[3, 4])]),
    ]}
    iter195 = CONDITION_REGISTRY[
        "change_input_color_count_per_group_constant_across_pairs"
    ]
    assert iter195(patterns, {}) is True
    assert _matcher()(patterns, {}) is True


def test_iter195_fires_but_this_matcher_rejects_when_output_fresh() -> None:
    # Per-group K_in == 1 uniform (iter 195 fires) but per-group
    # output is fresh (this matcher rejects).
    patterns = {"pair_analyses": [
        _analysis(groups=[_group(input_colors=[1], output_colors=[2])]),
        _analysis(groups=[_group(input_colors=[3], output_colors=[4])]),
    ]}
    iter195 = CONDITION_REGISTRY[
        "change_input_color_count_per_group_constant_across_pairs"
    ]
    assert iter195(patterns, {}) is True
    assert _matcher()(patterns, {}) is False


def test_iter199_globally_constant_nonzero_shift_rejects_this_matcher() -> None:
    # A globally-constant non-zero shift (iter 199 fires) makes every
    # group's output set disjoint from its input set. This matcher
    # rejects.
    patterns = {"pair_analyses": [
        _analysis(groups=[_group(input_colors=[1], output_colors=[4])]),
        _analysis(groups=[_group(input_colors=[2], output_colors=[5])]),
    ]}
    iter199 = CONDITION_REGISTRY[
        "palette_shift_constant_across_groups_and_pairs"
    ]
    assert iter199(patterns, {}) is True
    assert _matcher()(patterns, {}) is False


def test_iter199_zero_shift_co_fires_with_this_matcher() -> None:
    # The k == 0 cell of iter 199 (every group's input == output,
    # cardinality-1 per group, single global k=0) is the only iter-199
    # cell that co-fires with this matcher.
    patterns = {"pair_analyses": [
        _analysis(groups=[_group(input_colors=[1], output_colors=[1])]),
        _analysis(groups=[_group(input_colors=[2], output_colors=[2])]),
    ]}
    iter199 = CONDITION_REGISTRY[
        "palette_shift_constant_across_groups_and_pairs"
    ]
    assert iter199(patterns, {}) is True
    assert _matcher()(patterns, {}) is True


def test_co_fires_with_grid_size_preserved() -> None:
    # Orthogonal axes: grid_size_preserved is a dimensional flag, this
    # matcher inspects per-group palette content.
    patterns = {
        "grid_size_preserved": True,
        "pair_analyses": [
            _analysis(groups=[_group(input_colors=[1, 2],
                                     output_colors=[1, 2])]),
        ],
    }
    iter1 = CONDITION_REGISTRY["grid_size_preserved"]
    assert iter1(patterns, {}) is True
    assert _matcher()(patterns, {}) is True


# ──────────────────────────────────────────────────────────────────────────
# Recognized-conditions wiring.
# ──────────────────────────────────────────────────────────────────────────

def test_recognized_conditions_includes_matcher_on_per_group_equality() -> None:
    from agent.conditions import recognized_conditions
    patterns = {
        "pair_analyses": [
            _analysis(groups=[_group(input_colors=[1, 2],
                                     output_colors=[1, 2])]),
        ],
    }
    fired = recognized_conditions(patterns)
    assert MATCHER_NAME in fired, (
        f"{MATCHER_NAME!r} did not fire on per-group equality patterns; "
        f"got {fired!r}"
    )


def test_recognized_conditions_excludes_on_per_group_violation() -> None:
    from agent.conditions import recognized_conditions
    patterns = {
        "pair_analyses": [
            _analysis(groups=[_group(input_colors=[1], output_colors=[2])]),
        ],
    }
    fired = recognized_conditions(patterns)
    assert MATCHER_NAME not in fired, (
        f"{MATCHER_NAME!r} must NOT fire on per-group violation; got "
        f"{fired!r}"
    )


def test_recognized_conditions_excludes_on_proper_subset() -> None:
    # The strict-refinement witness vs iter 200 also applies at the
    # registry-wiring level: iter 200 fires, this matcher does not.
    from agent.conditions import recognized_conditions
    patterns = {
        "pair_analyses": [
            _analysis(groups=[_group(input_colors=[1, 2],
                                     output_colors=[1])]),
        ],
    }
    fired = recognized_conditions(patterns)
    assert "output_colors_subset_of_input_colors_per_group" in fired
    assert MATCHER_NAME not in fired, (
        f"{MATCHER_NAME!r} must NOT fire on proper subset; got {fired!r}"
    )


def test_recognized_conditions_co_fires_with_iter200_on_equality() -> None:
    # Where THIS matcher fires, iter 200 must also fire.
    from agent.conditions import recognized_conditions
    patterns = {
        "pair_analyses": [
            _analysis(groups=[_group(input_colors=[1, 2],
                                     output_colors=[1, 2])]),
            _analysis(groups=[_group(input_colors=[3],
                                     output_colors=[3])]),
        ],
    }
    fired = recognized_conditions(patterns)
    assert MATCHER_NAME in fired
    assert "output_colors_subset_of_input_colors_per_group" in fired, (
        "iter 200 must also fire wherever this matcher fires"
    )


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
