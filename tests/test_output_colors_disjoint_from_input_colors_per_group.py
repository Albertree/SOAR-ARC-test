"""
tests/test_output_colors_disjoint_from_input_colors_per_group.py --
exercise the iter-203 matcher
``agent.conditions.output_colors_disjoint_from_input_colors_per_group``
(new in this iter).

Pins the matcher's contract per the module docstring: every change
group in every example pair satisfies
``set(group["input_colors"]) & set(group["output_colors"]) == empty
set``. The matcher is the per-group projection of iter 186
(``output_palette_disjoint_from_input``, whole-grid scope) AND closes
the four-cell partition of the per-group palette-relation sub-axis
opened by iter 200 (output ⊆ input) / iter 201 (output == input) /
iter 202 (input ⊆ output) / this matcher (output ∩ input == ∅). Key
witnesses pinned below:

  * Decoupling vs iter 186 witness: per-group disjoint with whole-grid
    intersection (background bleed-through). The per-group output is
    fresh; the whole-grid palettes still intersect on unchanged
    background.
  * Mutual-exclusion witnesses: per-group equality (iter 201 fires)
    rejects this matcher; per-group erasure (iter 200 fires) rejects
    this matcher; per-group palette-expansion (iter 202 fires) rejects
    this matcher.
  * Partial-overlap rejection: input=[1,2] / output=[2,3] -- neither
    iter 200 nor iter 202 nor this matcher fires.

Runs without pytest:

    python tests/test_output_colors_disjoint_from_input_colors_per_group.py

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


MATCHER_NAME = "output_colors_disjoint_from_input_colors_per_group"


def _matcher():
    return CONDITION_REGISTRY[MATCHER_NAME]


def _group(*, input_colors=(1,), output_colors=(2,), positions=None):
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
# Positive cases -- per-group input ∩ output == ∅ universally.
# ──────────────────────────────────────────────────────────────────────────

def test_returns_true_on_single_pair_single_group_disjoint_singleton() -> None:
    patterns = {"pair_analyses": [
        _analysis(groups=[_group(input_colors=[1], output_colors=[2])]),
    ]}
    assert _matcher()(patterns, {}) is True


def test_returns_true_on_single_pair_single_group_disjoint_multi() -> None:
    patterns = {"pair_analyses": [
        _analysis(groups=[_group(input_colors=[1, 2], output_colors=[3, 4])]),
    ]}
    assert _matcher()(patterns, {}) is True


def test_returns_true_on_two_pairs_disjoint_palette_K1() -> None:
    patterns = {"pair_analyses": [
        _analysis(groups=[_group(input_colors=[1], output_colors=[2])]),
        _analysis(groups=[_group(input_colors=[3], output_colors=[4])]),
    ]}
    assert _matcher()(patterns, {}) is True


def test_returns_true_on_multi_group_per_pair_all_disjoint() -> None:
    patterns = {"pair_analyses": [
        _analysis(groups=[
            _group(input_colors=[1], output_colors=[2]),
            _group(input_colors=[3, 4], output_colors=[5, 6]),
        ]),
        _analysis(groups=[
            _group(input_colors=[7], output_colors=[8, 9]),
            _group(input_colors=[0], output_colors=[1, 2]),
        ]),
    ]}
    assert _matcher()(patterns, {}) is True


def test_returns_true_on_three_pairs_all_per_group_disjoint() -> None:
    patterns = {"pair_analyses": [
        _analysis(groups=[_group(input_colors=[1], output_colors=[2])]),
        _analysis(groups=[_group(input_colors=[3, 4], output_colors=[5, 6])]),
        _analysis(groups=[_group(input_colors=[7], output_colors=[8, 9])]),
    ]}
    assert _matcher()(patterns, {}) is True


def test_returns_true_on_varying_num_groups_per_pair_all_disjoint() -> None:
    patterns = {"pair_analyses": [
        _analysis(groups=[_group(input_colors=[1], output_colors=[2])]),
        _analysis(groups=[
            _group(input_colors=[3], output_colors=[4]),
            _group(input_colors=[5], output_colors=[6, 7]),
        ]),
        _analysis(groups=[
            _group(input_colors=[8], output_colors=[9]),
            _group(input_colors=[0], output_colors=[1]),
            _group(input_colors=[2, 3], output_colors=[4, 5]),
        ]),
    ]}
    assert _matcher()(patterns, {}) is True


def test_returns_true_on_per_blob_swap_iter186_decoupling_witness() -> None:
    # The KEY structural-distinction witness vs iter 186 (whole-grid):
    # a per-blob colour swap. Wait -- a swap is NOT per-group-disjoint
    # (group A: input={1} output={2} is disjoint, but group B: input={2}
    # output={1} is also disjoint; both per-group sets are disjoint
    # PER-GROUP). Whole-grid input_palette={1,2}, output_palette={1,2};
    # iter 186 REJECTS (whole-grid intersection is {1,2}, non-empty).
    # This matcher FIRES (per-group disjointness holds for both groups
    # individually). A clean witness: this matcher fires while iter 186
    # rejects.
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
    assert _matcher()(patterns, {}) is True


def test_returns_true_on_color_zero_disjoint() -> None:
    # Colour 0 (background) is a valid in-range strict int.
    patterns = {"pair_analyses": [
        _analysis(groups=[_group(input_colors=[0], output_colors=[5])]),
    ]}
    assert _matcher()(patterns, {}) is True


def test_returns_true_on_color_nine_disjoint() -> None:
    # Colour 9 (high-end) is a valid in-range strict int.
    patterns = {"pair_analyses": [
        _analysis(groups=[_group(input_colors=[9], output_colors=[8])]),
    ]}
    assert _matcher()(patterns, {}) is True


def test_returns_true_on_full_palette_split() -> None:
    # Maximal palettes that remain disjoint per group.
    patterns = {"pair_analyses": [
        _analysis(groups=[_group(input_colors=[0, 1, 2, 3, 4],
                                 output_colors=[5, 6, 7, 8, 9])]),
    ]}
    assert _matcher()(patterns, {}) is True


# ──────────────────────────────────────────────────────────────────────────
# Negative cases -- per-group input ∩ output != ∅.
# ──────────────────────────────────────────────────────────────────────────

def test_returns_false_when_single_overlap_on_singleton() -> None:
    # input_colors=[1], output_colors=[1] -- intersection {1}.
    # The KEY mutual-exclusion witness vs iter 201: per-group equality
    # rejects this matcher.
    patterns = {"pair_analyses": [
        _analysis(groups=[_group(input_colors=[1], output_colors=[1])]),
    ]}
    assert _matcher()(patterns, {}) is False


def test_returns_false_on_per_group_equality_iter201_witness() -> None:
    # The KEY mutual-exclusion witness vs iter 201: per-group equality
    # is the strongest non-disjoint case.
    patterns = {"pair_analyses": [
        _analysis(groups=[_group(input_colors=[1, 2], output_colors=[1, 2])]),
    ]}
    iter201 = CONDITION_REGISTRY[
        "output_colors_equals_input_colors_per_group"
    ]
    assert iter201(patterns, {}) is True
    assert _matcher()(patterns, {}) is False


def test_returns_false_on_per_group_erasure_iter200_witness() -> None:
    # The KEY mutual-exclusion witness vs iter 200: per-group erasure
    # has non-empty per-group output ⊆ non-empty per-group input.
    patterns = {"pair_analyses": [
        _analysis(groups=[_group(input_colors=[1, 2], output_colors=[1])]),
    ]}
    iter200 = CONDITION_REGISTRY[
        "output_colors_subset_of_input_colors_per_group"
    ]
    assert iter200(patterns, {}) is True
    assert _matcher()(patterns, {}) is False


def test_returns_false_on_per_group_expansion_iter202_witness() -> None:
    # The KEY mutual-exclusion witness vs iter 202: per-group palette-
    # expansion has non-empty per-group input ⊆ non-empty per-group
    # output.
    patterns = {"pair_analyses": [
        _analysis(groups=[_group(input_colors=[1], output_colors=[1, 2])]),
    ]}
    iter202 = CONDITION_REGISTRY[
        "input_colors_subset_of_output_colors_per_group"
    ]
    assert iter202(patterns, {}) is True
    assert _matcher()(patterns, {}) is False


def test_returns_false_on_partial_overlap_residual_quadrant() -> None:
    # input=[1, 2] / output=[2, 3] -- partial overlap on {2}. Neither
    # iter 200 nor iter 202 fires; this matcher rejects on the
    # non-empty intersection.
    patterns = {"pair_analyses": [
        _analysis(groups=[_group(input_colors=[1, 2], output_colors=[2, 3])]),
    ]}
    iter200 = CONDITION_REGISTRY[
        "output_colors_subset_of_input_colors_per_group"
    ]
    iter202 = CONDITION_REGISTRY[
        "input_colors_subset_of_output_colors_per_group"
    ]
    assert iter200(patterns, {}) is False
    assert iter202(patterns, {}) is False
    assert _matcher()(patterns, {}) is False


def test_returns_false_when_second_group_violates_in_first_pair() -> None:
    # First group disjoint, second group overlaps.
    patterns = {"pair_analyses": [
        _analysis(groups=[
            _group(input_colors=[1], output_colors=[2]),
            _group(input_colors=[3], output_colors=[3]),
        ]),
    ]}
    assert _matcher()(patterns, {}) is False


def test_returns_false_when_second_pair_violates() -> None:
    patterns = {"pair_analyses": [
        _analysis(groups=[_group(input_colors=[1], output_colors=[2])]),
        _analysis(groups=[_group(input_colors=[3], output_colors=[3])]),
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
        _analysis(groups=[_group(input_colors=[1], output_colors=[2])]),
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
    pair0 = _analysis(groups=[_group(input_colors=[1], output_colors=[2])])
    pair1_bad = _analysis(groups=[])
    pair1_bad["groups"] = ["not-a-dict"]
    assert _matcher()({"pair_analyses": [pair0, pair1_bad]}, {}) is False


# ──────────────────────────────────────────────────────────────────────────
# Behavioural contract: side-effect-free, deterministic, strict bool.
# ──────────────────────────────────────────────────────────────────────────

def test_is_side_effect_free_on_inputs() -> None:
    patterns = {"pair_analyses": [
        _analysis(groups=[
            _group(input_colors=[1], output_colors=[2]),
            _group(input_colors=[3], output_colors=[4]),
        ]),
        _analysis(groups=[_group(input_colors=[5], output_colors=[6])]),
    ]}
    params = {"unused": 1}
    before_p = copy.deepcopy(patterns)
    before_q = copy.deepcopy(params)
    _matcher()(patterns, params)
    assert patterns == before_p, "matcher mutated patterns"
    assert params == before_q, "matcher mutated params"


def test_is_deterministic_across_repeats() -> None:
    patterns = {"pair_analyses": [
        _analysis(groups=[_group(input_colors=[1], output_colors=[2])]),
        _analysis(groups=[_group(input_colors=[3], output_colors=[4])]),
    ]}
    results = [_matcher()(patterns, {}) for _ in range(5)]
    assert len(set(results)) == 1, f"non-deterministic outputs: {results}"


def test_returns_strict_boolean_type() -> None:
    pos_pat = {"pair_analyses": [
        _analysis(groups=[_group(input_colors=[1], output_colors=[2])]),
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
        _analysis(groups=[_group(input_colors=[1], output_colors=[2])]),
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
            groups=[_group(input_colors=[1], output_colors=[2])],
            input_palette=[1, 7, 8],  # whole-grid noise (note: 7, 8 absent
                                       # from any group's input/output, but
                                       # the matcher ignores whole-grid fields)
            output_palette=[2, 1, 9],  # contains 1 (an input colour) -- the
                                        # whole-grid intersection is non-empty
                                        # but per-group disjointness still holds
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
    disjoint_pat = {
        "grid_size_preserved": True,
        "pair_analyses": [
            _analysis(groups=[_group(input_colors=[1], output_colors=[2])]),
        ],
    }
    identity = CONDITION_REGISTRY["identity_transformation"]
    assert identity(identity_pat, {}) is True
    assert _matcher()(identity_pat, {}) is False
    assert identity(disjoint_pat, {}) is False
    assert _matcher()(disjoint_pat, {}) is True


def test_mutually_exclusive_with_iter200_on_per_group_outputs() -> None:
    # Iter 200 (output ⊆ input) and this matcher (output ∩ input == ∅)
    # are mutually exclusive on non-empty per-group outputs (which the
    # cell-count requirement guarantees in this matcher's domain). On
    # the same disjoint-witness pattern, iter 200 rejects (output ⊄
    # input) and this matcher fires.
    patterns = {"pair_analyses": [
        _analysis(groups=[_group(input_colors=[1], output_colors=[2])]),
    ]}
    iter200 = CONDITION_REGISTRY[
        "output_colors_subset_of_input_colors_per_group"
    ]
    assert iter200(patterns, {}) is False
    assert _matcher()(patterns, {}) is True


def test_mutually_exclusive_with_iter201_on_non_empty_palettes() -> None:
    # Iter 201 (output == input) and this matcher are strictly mutually
    # exclusive on non-empty per-group palettes. Demonstrate both
    # directions: equality witness fires iter 201, rejects this matcher;
    # disjoint witness rejects iter 201, fires this matcher.
    eq_pat = {"pair_analyses": [
        _analysis(groups=[_group(input_colors=[1], output_colors=[1])]),
    ]}
    disj_pat = {"pair_analyses": [
        _analysis(groups=[_group(input_colors=[1], output_colors=[2])]),
    ]}
    iter201 = CONDITION_REGISTRY[
        "output_colors_equals_input_colors_per_group"
    ]
    assert iter201(eq_pat, {}) is True
    assert _matcher()(eq_pat, {}) is False
    assert iter201(disj_pat, {}) is False
    assert _matcher()(disj_pat, {}) is True


def test_mutually_exclusive_with_iter202_on_per_group_inputs() -> None:
    # Iter 202 (input ⊆ output) and this matcher are mutually exclusive
    # on non-empty per-group inputs. On the disjoint-witness pattern,
    # iter 202 rejects (input ⊄ output) and this matcher fires.
    patterns = {"pair_analyses": [
        _analysis(groups=[_group(input_colors=[1], output_colors=[2])]),
    ]}
    iter202 = CONDITION_REGISTRY[
        "input_colors_subset_of_output_colors_per_group"
    ]
    assert iter202(patterns, {}) is False
    assert _matcher()(patterns, {}) is True


def test_iter186_rejects_but_this_matcher_fires_on_per_blob_swap() -> None:
    # The KEY structural-distinction witness vs iter 186 (whole-grid):
    # a per-blob colour swap. Per-group A: input={1} output={2}
    # disjoint. Per-group B: input={2} output={1} disjoint. Per-group
    # disjointness universal -> this matcher fires. Whole-grid
    # input_palette={1, 2}, whole-grid output_palette={1, 2}; whole-
    # grid intersection = {1, 2} non-empty -> iter 186 rejects.
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
    iter186 = CONDITION_REGISTRY["output_palette_disjoint_from_input"]
    assert iter186(patterns, {}) is False, (
        "iter 186 must reject whole-grid output ∩ input != ∅"
    )
    assert _matcher()(patterns, {}) is True, (
        "this matcher must fire on per-blob swap (per-group disjointness)"
    )


def test_iter186_fires_but_this_matcher_rejects_on_partial_overlap() -> None:
    # Witness: per-group palettes overlap (rejecting this matcher) but
    # whole-grid palettes are disjoint (firing iter 186). Construct a
    # single-group pair where the per-group input AND per-group output
    # share a colour, AND the whole-grid palettes are disjoint -- not
    # possible in general because per-group sets are subsets of the
    # whole-grid sets. The cleanest witness is the inverse: any
    # per-group-overlap pattern necessarily has whole-grid overlap;
    # so iter 186 rejects whenever per-group overlap exists. The
    # decoupling is one-sided: this matcher CAN fire while iter 186
    # rejects (per-blob swap above), but iter 186 firing implies this
    # matcher fires (whole-grid disjointness implies per-group
    # disjointness, since per-group sets are subsets of whole-grid
    # sets). Rather than a synthetic decoupling-other-direction, this
    # test pins the implication: aligned per-group + whole-grid
    # disjoint. Both fire.
    patterns = {
        "pair_analyses": [
            _analysis(
                groups=[_group(input_colors=[1], output_colors=[2])],
                input_palette=[1],
                output_palette=[2],
            ),
        ],
    }
    iter186 = CONDITION_REGISTRY["output_palette_disjoint_from_input"]
    assert iter186(patterns, {}) is True, (
        "iter 186 must fire on whole-grid disjoint palettes"
    )
    assert _matcher()(patterns, {}) is True, (
        "this matcher must fire when per-group palettes are also disjoint"
    )


def test_co_fires_with_iter186_on_aligned_disjoint_palettes() -> None:
    # Per-group disjointness AND whole-grid disjointness aligned per
    # pair: both fire.
    patterns = {
        "pair_analyses": [
            _analysis(
                groups=[_group(input_colors=[1], output_colors=[2])],
                input_palette=[1],
                output_palette=[2],
            ),
            _analysis(
                groups=[_group(input_colors=[3], output_colors=[4])],
                input_palette=[3],
                output_palette=[4],
            ),
        ],
    }
    iter186 = CONDITION_REGISTRY["output_palette_disjoint_from_input"]
    assert iter186(patterns, {}) is True
    assert _matcher()(patterns, {}) is True


def test_iter14_uniform_input_co_fire_when_output_disjoint() -> None:
    # iter 14 (input_color_uniform) pins every group's input_colors
    # to the same single colour; this matcher requires per-group
    # output ∩ input == ∅, so the output must NOT contain that single
    # colour per group. Both fire on uniform fresh-output patterns.
    patterns = {"pair_analyses": [
        _analysis(groups=[_group(input_colors=[1], output_colors=[2])]),
        _analysis(groups=[_group(input_colors=[1], output_colors=[3])]),
    ]}
    iter14 = CONDITION_REGISTRY["input_color_uniform"]
    assert iter14(patterns, {}) is True
    assert _matcher()(patterns, {}) is True


def test_iter14_fires_but_this_matcher_rejects_on_uniform_input_overlap() -> None:
    # iter 14 fires (input_colors=[1] uniform) but output_colors=[1, 2]
    # contains 1 per group -- this matcher rejects.
    patterns = {"pair_analyses": [
        _analysis(groups=[_group(input_colors=[1], output_colors=[1, 2])]),
        _analysis(groups=[_group(input_colors=[1], output_colors=[1, 3])]),
    ]}
    iter14 = CONDITION_REGISTRY["input_color_uniform"]
    assert iter14(patterns, {}) is True
    assert _matcher()(patterns, {}) is False


def test_iter196_co_fires_when_K_out_constant_and_palettes_disjoint() -> None:
    # iter 196 pins per-group output cardinality constant across pairs;
    # this matcher pins per-group output ∩ input == ∅. With K_out == 1
    # across pairs AND every group's output disjoint from input, both
    # fire.
    patterns = {"pair_analyses": [
        _analysis(groups=[_group(input_colors=[1], output_colors=[2])]),
        _analysis(groups=[_group(input_colors=[3], output_colors=[4])]),
    ]}
    iter196 = CONDITION_REGISTRY[
        "change_output_color_count_per_group_constant_across_pairs"
    ]
    assert iter196(patterns, {}) is True
    assert _matcher()(patterns, {}) is True


def test_iter196_fires_but_this_matcher_rejects_when_output_overlaps() -> None:
    # Per-group K_out == 1 uniform (iter 196 fires) but per-group
    # output equal to input (this matcher rejects).
    patterns = {"pair_analyses": [
        _analysis(groups=[_group(input_colors=[1], output_colors=[1])]),
        _analysis(groups=[_group(input_colors=[2], output_colors=[2])]),
    ]}
    iter196 = CONDITION_REGISTRY[
        "change_output_color_count_per_group_constant_across_pairs"
    ]
    assert iter196(patterns, {}) is True
    assert _matcher()(patterns, {}) is False


def test_iter199_globally_constant_nonzero_shift_co_fires() -> None:
    # A globally-constant non-zero shift (iter 199 fires) makes every
    # group's output set disjoint from its input set. This matcher
    # FIRES on every iter-199 cell except k == 0.
    patterns = {"pair_analyses": [
        _analysis(groups=[_group(input_colors=[1], output_colors=[4])]),
        _analysis(groups=[_group(input_colors=[2], output_colors=[5])]),
    ]}
    iter199 = CONDITION_REGISTRY[
        "palette_shift_constant_across_groups_and_pairs"
    ]
    assert iter199(patterns, {}) is True
    assert _matcher()(patterns, {}) is True


def test_iter199_zero_shift_rejects_this_matcher() -> None:
    # The k == 0 cell of iter 199 (every group's input == output,
    # cardinality-1 per group, single global k=0) is the only iter-199
    # cell that REJECTS this matcher.
    patterns = {"pair_analyses": [
        _analysis(groups=[_group(input_colors=[1], output_colors=[1])]),
        _analysis(groups=[_group(input_colors=[2], output_colors=[2])]),
    ]}
    iter199 = CONDITION_REGISTRY[
        "palette_shift_constant_across_groups_and_pairs"
    ]
    assert iter199(patterns, {}) is True
    assert _matcher()(patterns, {}) is False


def test_co_fires_with_grid_size_preserved() -> None:
    # Orthogonal axes: grid_size_preserved is a dimensional flag,
    # this matcher inspects per-group palette content.
    patterns = {
        "grid_size_preserved": True,
        "pair_analyses": [
            _analysis(groups=[_group(input_colors=[1], output_colors=[2])]),
        ],
    }
    iter1 = CONDITION_REGISTRY["grid_size_preserved"]
    assert iter1(patterns, {}) is True
    assert _matcher()(patterns, {}) is True


# ──────────────────────────────────────────────────────────────────────────
# Recognized-conditions wiring.
# ──────────────────────────────────────────────────────────────────────────

def test_recognized_conditions_includes_matcher_on_per_group_disjoint() -> None:
    from agent.conditions import recognized_conditions
    patterns = {
        "pair_analyses": [
            _analysis(groups=[_group(input_colors=[1], output_colors=[2])]),
        ],
    }
    fired = recognized_conditions(patterns)
    assert MATCHER_NAME in fired, (
        f"{MATCHER_NAME!r} did not fire on per-group disjoint patterns; "
        f"got {fired!r}"
    )


def test_recognized_conditions_excludes_on_per_group_overlap() -> None:
    from agent.conditions import recognized_conditions
    patterns = {
        "pair_analyses": [
            _analysis(groups=[_group(input_colors=[1, 2],
                                     output_colors=[2, 3])]),
        ],
    }
    fired = recognized_conditions(patterns)
    assert MATCHER_NAME not in fired, (
        f"{MATCHER_NAME!r} must NOT fire on per-group overlap; "
        f"got {fired!r}"
    )


def test_recognized_conditions_excludes_on_equality_iter201_fires() -> None:
    # The mutual-exclusion witness at the registry-wiring level: per-
    # group equality fires iter 201 but rejects this matcher.
    from agent.conditions import recognized_conditions
    patterns = {
        "pair_analyses": [
            _analysis(groups=[_group(input_colors=[1, 2],
                                     output_colors=[1, 2])]),
        ],
    }
    fired = recognized_conditions(patterns)
    assert "output_colors_equals_input_colors_per_group" in fired
    assert MATCHER_NAME not in fired, (
        f"{MATCHER_NAME!r} must NOT fire on per-group equality; "
        f"got {fired!r}"
    )


def test_recognized_conditions_excludes_iters_200_201_202_on_disjoint() -> None:
    # Per-group disjoint fires THIS matcher and excludes iter 200,
    # iter 201, AND iter 202 (all three sub-axis matchers reject the
    # disjoint cell of the four-cell partition).
    from agent.conditions import recognized_conditions
    patterns = {
        "pair_analyses": [
            _analysis(groups=[_group(input_colors=[1], output_colors=[2])]),
        ],
    }
    fired = recognized_conditions(patterns)
    assert MATCHER_NAME in fired
    assert "output_colors_subset_of_input_colors_per_group" not in fired, (
        "iter 200 must NOT fire on per-group disjoint (output ⊄ input)"
    )
    assert "output_colors_equals_input_colors_per_group" not in fired, (
        "iter 201 must NOT fire on per-group disjoint (output != input)"
    )
    assert "input_colors_subset_of_output_colors_per_group" not in fired, (
        "iter 202 must NOT fire on per-group disjoint (input ⊄ output)"
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
