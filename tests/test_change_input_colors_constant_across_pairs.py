"""
tests/test_change_input_colors_constant_across_pairs.py -- exercise the
iter-35 matcher
``agent.conditions.change_input_colors_constant_across_pairs``.

Runs without pytest:

    python tests/test_change_input_colors_constant_across_pairs.py

Dependency-free, same runner style as iters
1 / 8 / 10 / 13 / 17 / 18 / 19 / 20 / 22 / 23 / 24 / 26 / 28 / 30 / 32
/ 33 / 34.

The matcher is on the cross-pair INPUT-colour set-constancy axis: it
names "the SET of input colours involved in change groups is
bit-identical across every pair" -- the input-side projection of
iter 34's full ``(input, output)`` set constancy. Strictly weaker than
both iter 34 (drops the output-side information) and iter 19 (allows
multi-input-colour per-pair sets where iter 19 requires a singleton
union). Names the recognition precondition for a future derived-
selection rule whose selection is determined by training-pinned input
colours.
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


MATCHER_NAME = "change_input_colors_constant_across_pairs"


def _matcher():
    return CONDITION_REGISTRY[MATCHER_NAME]


def _group(*, positions, in_colors=(0,), out_colors=(3,)):
    """Build a group analysis dict matching ``_analyze_pair``'s emit shape.

    ``positions`` are accepted for parity with iters 30 / 32 / 34's test
    fixtures so the co-fire tests below can reuse the same building
    blocks; this matcher inspects only ``input_colors`` -- positions are
    not required.
    """
    sorted_positions = sorted(tuple(p) for p in positions)
    if sorted_positions:
        top_row = min(r for r, _ in sorted_positions)
        top_col = min(c for _, c in sorted_positions)
    else:
        top_row = 0
        top_col = 0
    return {
        "input_colors": sorted(set(in_colors)),
        "output_colors": sorted(set(out_colors)),
        "top_row": top_row,
        "top_col": top_col,
        "cell_count": len(sorted_positions),
        "positions": sorted_positions,
    }


def _analysis(*, groups, input_height=3, input_width=3,
              output_height=None, output_width=None, size_match=None):
    if output_height is None:
        output_height = input_height
    if output_width is None:
        output_width = input_width
    if size_match is None:
        size_match = (input_height == output_height
                      and input_width == output_width)
    return {
        "total_changes": sum(g.get("cell_count", 0) for g in groups),
        "num_groups": len(groups),
        "groups": list(groups),
        "size_match": size_match,
        "input_height": input_height,
        "input_width": input_width,
        "output_height": output_height,
        "output_width": output_width,
    }


# ----------------------------------------------------------------------
# Tests.
# ----------------------------------------------------------------------

def test_registered_in_global_registry() -> None:
    assert MATCHER_NAME in CONDITION_REGISTRY, (
        f"{MATCHER_NAME!r} not registered; got {sorted(CONDITION_REGISTRY)}"
    )


def test_previous_matchers_still_registered() -> None:
    # Adjacent invariant -- iter 35 must not displace iters
    # 1 / 8 / 10 / 13 / 17 / 18 / 19 / 20 / 22 / 23 / 24 / 26 / 28 / 30
    # / 32 / 33 / 34.
    for prior in ("grid_size_preserved", "consistent_color_mapping",
                  "sequential_recoloring", "identity_transformation",
                  "grid_size_changed", "output_color_uniform",
                  "input_color_uniform", "output_dimensions_constant",
                  "input_dimensions_constant",
                  "single_change_group_per_pair",
                  "single_cell_change_per_pair",
                  "multi_cell_change_group_per_pair",
                  "multi_group_per_pair",
                  "change_positions_constant_across_pairs",
                  "change_count_constant_across_pairs",
                  "output_dimensions_multiple_of_input",
                  "change_colors_constant_across_pairs"):
        assert prior in CONDITION_REGISTRY, (
            f"prior matcher {prior!r} missing after iter-35 addition"
        )


def test_at_least_eighteen_distinct_matchers_registered() -> None:
    # P5 unit-monotone counter -- iter 35 lifts the count from 17 to 18.
    assert len(CONDITION_REGISTRY) >= 18, (
        f"expected at least 18 entries, got {len(CONDITION_REGISTRY)}: "
        f"{sorted(CONDITION_REGISTRY)}"
    )


def test_matcher_is_callable() -> None:
    fn = _matcher()
    assert callable(fn), f"registered entry is not callable: {fn!r}"


def test_returns_true_on_single_pair_single_group() -> None:
    patterns = {"pair_analyses": [
        _analysis(groups=[
            _group(positions=[(1, 1)], in_colors=(1,), out_colors=(2,)),
        ]),
    ]}
    assert _matcher()(patterns, {}) is True


def test_returns_true_on_two_pairs_same_singleton_input_set() -> None:
    # Both pairs have a single group with input colour 1. Per-pair input
    # set is {1}; bit-identical across pairs.
    patterns = {"pair_analyses": [
        _analysis(groups=[
            _group(positions=[(0, 0)], in_colors=(1,), out_colors=(2,)),
        ]),
        _analysis(groups=[
            _group(positions=[(2, 2)], in_colors=(1,), out_colors=(3,)),
        ]),
    ]}
    # Output colours differ (2 vs 3); per-pair input sets identical.
    assert _matcher()(patterns, {}) is True


def test_returns_true_on_multi_group_same_input_set() -> None:
    # Per-pair input set is {1, 3} on both pairs; outputs differ within
    # each pair AND across pairs. Iter 35 still fires.
    patterns = {"pair_analyses": [
        _analysis(groups=[
            _group(positions=[(0, 0)], in_colors=(1,), out_colors=(2,)),
            _group(positions=[(2, 2)], in_colors=(3,), out_colors=(4,)),
        ]),
        _analysis(groups=[
            _group(positions=[(1, 1)], in_colors=(1,), out_colors=(7,)),
            _group(positions=[(0, 2)], in_colors=(3,), out_colors=(8,)),
        ]),
    ]}
    assert _matcher()(patterns, {}) is True


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


def test_returns_false_when_every_pair_has_zero_groups() -> None:
    # Identity case: per-pair input set is empty. The matcher rejects
    # vacuously-true matches to keep its territory disjoint from
    # iter 13's identity_transformation.
    patterns = {"pair_analyses": [
        _analysis(groups=[]),
        _analysis(groups=[]),
    ]}
    assert _matcher()(patterns, {}) is False


def test_returns_false_when_one_pair_has_no_groups() -> None:
    # Pair 0 has one input colour; pair 1 has zero groups (empty set).
    # Strict reject -- the empty-set side fails the non-empty clause.
    patterns = {"pair_analyses": [
        _analysis(groups=[
            _group(positions=[(0, 0)], in_colors=(1,), out_colors=(2,)),
        ]),
        _analysis(groups=[]),
    ]}
    assert _matcher()(patterns, {}) is False


def test_returns_false_when_input_sets_differ_across_pairs() -> None:
    # Pair 0 inputs: {1}. Pair 1 inputs: {2}. Distinct sets.
    patterns = {"pair_analyses": [
        _analysis(groups=[
            _group(positions=[(0, 0)], in_colors=(1,), out_colors=(3,)),
        ]),
        _analysis(groups=[
            _group(positions=[(0, 0)], in_colors=(2,), out_colors=(3,)),
        ]),
    ]}
    assert _matcher()(patterns, {}) is False


def test_returns_false_when_one_pair_has_extra_input_color() -> None:
    # Pair 0 inputs: {1}. Pair 1 inputs: {1, 3} -- extra colour.
    patterns = {"pair_analyses": [
        _analysis(groups=[
            _group(positions=[(0, 0)], in_colors=(1,), out_colors=(2,)),
        ]),
        _analysis(groups=[
            _group(positions=[(0, 0)], in_colors=(1,), out_colors=(2,)),
            _group(positions=[(2, 2)], in_colors=(3,), out_colors=(4,)),
        ]),
    ]}
    assert _matcher()(patterns, {}) is False


def test_returns_false_on_multi_input_colors_in_group() -> None:
    # A group with two input colours has an ill-defined input projection;
    # the matcher fail-closes (mirroring iter 18 / 19 / 34's per-group
    # cardinality-1 posture).
    group_bad = {
        "input_colors": [1, 2], "output_colors": [3],
        "top_row": 0, "top_col": 0, "cell_count": 2,
        "positions": [(0, 0), (0, 1)],
    }
    patterns = {"pair_analyses": [_analysis(groups=[group_bad])]}
    assert _matcher()(patterns, {}) is False


def test_returns_true_on_multi_output_colors_in_group() -> None:
    # Multi-output is allowed (iter 35 inspects only input_colors).
    # Verifies the matcher is indifferent to output cardinality, which
    # is the input-projection design intent.
    group_a = {
        "input_colors": [1], "output_colors": [3, 4],
        "top_row": 0, "top_col": 0, "cell_count": 2,
        "positions": [(0, 0), (0, 1)],
    }
    group_b = {
        "input_colors": [1], "output_colors": [5, 6],
        "top_row": 0, "top_col": 0, "cell_count": 2,
        "positions": [(1, 0), (1, 1)],
    }
    patterns = {"pair_analyses": [
        _analysis(groups=[group_a]),
        _analysis(groups=[group_b]),
    ]}
    # Per-pair input set is {1} on both -- iter 35 fires even though
    # output cardinalities and contents differ.
    assert _matcher()(patterns, {}) is True


def test_returns_false_on_empty_input_colors_list() -> None:
    group_bad = {
        "input_colors": [], "output_colors": [3],
        "top_row": 0, "top_col": 0, "cell_count": 1,
        "positions": [(0, 0)],
    }
    patterns = {"pair_analyses": [_analysis(groups=[group_bad])]}
    assert _matcher()(patterns, {}) is False


def test_returns_false_on_missing_input_colors() -> None:
    group_bad = {
        "output_colors": [3],
        "top_row": 0, "top_col": 0, "cell_count": 1,
        "positions": [(0, 0)],
    }
    patterns = {"pair_analyses": [_analysis(groups=[group_bad])]}
    assert _matcher()(patterns, {}) is False


def test_returns_false_on_non_list_input_colors() -> None:
    for bad in (1, "1", None, {"k": 1}):
        group_bad = {
            "input_colors": bad, "output_colors": [3],
            "top_row": 0, "top_col": 0, "cell_count": 1,
            "positions": [(0, 0)],
        }
        patterns = {"pair_analyses": [_analysis(groups=[group_bad])]}
        assert _matcher()(patterns, {}) is False, (
            f"input_colors={bad!r} (non-list) should fail-closed"
        )


def test_returns_false_on_bool_subclass_in_input_colors() -> None:
    for bad in (True, False):
        group_bad = {
            "input_colors": [bad], "output_colors": [3],
            "top_row": 0, "top_col": 0, "cell_count": 1,
            "positions": [(0, 0)],
        }
        patterns = {"pair_analyses": [_analysis(groups=[group_bad])]}
        assert _matcher()(patterns, {}) is False, (
            f"input_colors=[{bad!r}] (bool subclass) should fail-closed"
        )


def test_returns_false_on_out_of_range_input_colors() -> None:
    # ARC colours are 0..9. The matcher rejects out-of-range.
    for bad in (-1, 10, 13, 100):
        group_bad = {
            "input_colors": [bad], "output_colors": [3],
            "top_row": 0, "top_col": 0, "cell_count": 1,
            "positions": [(0, 0)],
        }
        patterns = {"pair_analyses": [_analysis(groups=[group_bad])]}
        assert _matcher()(patterns, {}) is False, (
            f"input_colors=[{bad}] (out-of-range) should fail-closed"
        )


def test_returns_false_on_non_int_input_colors() -> None:
    for bad in (0.5, "1", None, [1]):
        group_bad = {
            "input_colors": [bad], "output_colors": [3],
            "top_row": 0, "top_col": 0, "cell_count": 1,
            "positions": [(0, 0)],
        }
        patterns = {"pair_analyses": [_analysis(groups=[group_bad])]}
        assert _matcher()(patterns, {}) is False, (
            f"input_colors=[{bad!r}] (non-int) should fail-closed"
        )


def test_returns_false_on_non_list_groups() -> None:
    analysis = _analysis(groups=[_group(positions=[(0, 0)])])
    analysis["groups"] = "not a list"
    patterns = {"pair_analyses": [analysis]}
    assert _matcher()(patterns, {}) is False


def test_returns_false_on_non_dict_group_entry() -> None:
    analysis = _analysis(groups=[_group(positions=[(0, 0)])])
    analysis["groups"] = ["not a dict"]
    patterns = {"pair_analyses": [analysis]}
    assert _matcher()(patterns, {}) is False


def test_is_side_effect_free_on_inputs() -> None:
    patterns = {"pair_analyses": [
        _analysis(groups=[
            _group(positions=[(0, 0)], in_colors=(1,), out_colors=(2,)),
        ]),
        _analysis(groups=[
            _group(positions=[(1, 1)], in_colors=(1,), out_colors=(2,)),
        ]),
    ]}
    params = {"unused": 1}
    before_p = copy.deepcopy(patterns)
    before_q = copy.deepcopy(params)
    _matcher()(patterns, params)
    assert patterns == before_p, "matcher mutated patterns"
    assert params == before_q, "matcher mutated params"


def test_is_deterministic_across_repeats() -> None:
    patterns = {"pair_analyses": [
        _analysis(groups=[
            _group(positions=[(0, 0)], in_colors=(1,), out_colors=(2,)),
        ]),
        _analysis(groups=[
            _group(positions=[(2, 2)], in_colors=(1,), out_colors=(3,)),
        ]),
    ]}
    results = [_matcher()(patterns, {}) for _ in range(5)]
    assert len(set(results)) == 1, f"non-deterministic outputs: {results}"


# ----- mutual-exclusion / refinement-chain tests --------------------

def test_mutually_exclusive_with_identity_transformation() -> None:
    # identity requires num_groups == 0; this matcher rejects empty
    # per-pair sets. No patterns dict can fire both.
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
            _analysis(groups=[
                _group(positions=[(1, 1)], in_colors=(1,), out_colors=(2,)),
            ]),
            _analysis(groups=[
                _group(positions=[(2, 2)], in_colors=(1,), out_colors=(2,)),
            ]),
        ],
    }
    identity = CONDITION_REGISTRY["identity_transformation"]
    assert identity(identity_pat, {}) is True
    assert _matcher()(identity_pat, {}) is False
    assert identity(paint_pat, {}) is False
    assert _matcher()(paint_pat, {}) is True


def test_iter_34_refinement_implication_holds() -> None:
    # Strict-stronger means: whenever iter 34 fires, iter 35 also fires
    # (projecting the per-pair (ic, oc) set onto ic yields the per-pair
    # input set; constancy of the full set implies constancy of the
    # projection). Verify on a positive fixture.
    patterns = {"pair_analyses": [
        _analysis(groups=[
            _group(positions=[(0, 0)], in_colors=(1,), out_colors=(2,)),
            _group(positions=[(2, 2)], in_colors=(3,), out_colors=(4,)),
        ]),
        _analysis(groups=[
            _group(positions=[(1, 1)], in_colors=(1,), out_colors=(2,)),
            _group(positions=[(0, 2)], in_colors=(3,), out_colors=(4,)),
        ]),
    ]}
    iter34 = CONDITION_REGISTRY["change_colors_constant_across_pairs"]
    assert iter34(patterns, {}) is True
    assert _matcher()(patterns, {}) is True


def test_iter_34_refinement_strict_one_direction() -> None:
    # iter 35 fires where iter 34 does NOT: per-pair input sets are
    # constant but the (ic, oc) sets differ (output side varies).
    # Pair 0 maps 1 -> 2, pair 1 maps 1 -> 3. Per-pair input set is
    # {1} on both -- iter 35 fires. Per-pair (ic, oc) sets differ
    # ({(1, 2)} vs {(1, 3)}) -- iter 34 rejects.
    patterns = {"pair_analyses": [
        _analysis(groups=[
            _group(positions=[(0, 0)], in_colors=(1,), out_colors=(2,)),
        ]),
        _analysis(groups=[
            _group(positions=[(0, 0)], in_colors=(1,), out_colors=(3,)),
        ]),
    ]}
    iter34 = CONDITION_REGISTRY["change_colors_constant_across_pairs"]
    assert _matcher()(patterns, {}) is True
    assert iter34(patterns, {}) is False


def test_iter_19_refinement_implication_holds() -> None:
    # Strict-stronger means: whenever iter 19 (input_color_uniform)
    # fires, iter 35 fires too (singleton union ⟹ per-pair sets are
    # all {C} ⟹ bit-identical across pairs).
    patterns = {"pair_analyses": [
        _analysis(groups=[
            _group(positions=[(0, 0)], in_colors=(2,), out_colors=(3,)),
        ]),
        _analysis(groups=[
            _group(positions=[(1, 1)], in_colors=(2,), out_colors=(4,)),
        ]),
    ]}
    iter19 = CONDITION_REGISTRY["input_color_uniform"]
    assert iter19(patterns, {}) is True
    assert _matcher()(patterns, {}) is True


def test_iter_19_refinement_strict_one_direction() -> None:
    # iter 35 fires where iter 19 does NOT: per-pair input sets are
    # bit-identical with cardinality > 1, so iter 19's len(union)==1
    # clause rejects but iter 35 fires.
    patterns = {"pair_analyses": [
        _analysis(groups=[
            _group(positions=[(0, 0)], in_colors=(1,), out_colors=(2,)),
            _group(positions=[(2, 2)], in_colors=(3,), out_colors=(4,)),
        ]),
        _analysis(groups=[
            _group(positions=[(1, 1)], in_colors=(1,), out_colors=(2,)),
            _group(positions=[(0, 2)], in_colors=(3,), out_colors=(4,)),
        ]),
    ]}
    iter19 = CONDITION_REGISTRY["input_color_uniform"]
    assert _matcher()(patterns, {}) is True
    assert iter19(patterns, {}) is False


def test_independent_of_consistent_color_mapping_iter_8_fires_alone() -> None:
    # Pair 0 maps 1 -> 2, pair 1 maps 3 -> 4. Unioned mapping is
    # functional ({1->2, 3->4}); per-pair input sets {1} vs {3} differ.
    # iter 8 fires; iter 35 rejects.
    patterns = {"pair_analyses": [
        _analysis(groups=[
            _group(positions=[(0, 0)], in_colors=(1,), out_colors=(2,)),
        ]),
        _analysis(groups=[
            _group(positions=[(0, 0)], in_colors=(3,), out_colors=(4,)),
        ]),
    ]}
    iter8 = CONDITION_REGISTRY["consistent_color_mapping"]
    assert iter8(patterns, {}) is True
    assert _matcher()(patterns, {}) is False


def test_independent_of_consistent_color_mapping_iter_35_fires_alone() -> None:
    # Pair 0 maps 1 -> 2, pair 1 maps 1 -> 3. Unioned mapping
    # {1 -> {2, 3}} is non-functional -- iter 8 rejects. Per-pair
    # input set {1} bit-identical -- iter 35 fires.
    patterns = {"pair_analyses": [
        _analysis(groups=[
            _group(positions=[(0, 0)], in_colors=(1,), out_colors=(2,)),
        ]),
        _analysis(groups=[
            _group(positions=[(0, 0)], in_colors=(1,), out_colors=(3,)),
        ]),
    ]}
    iter8 = CONDITION_REGISTRY["consistent_color_mapping"]
    assert iter8(patterns, {}) is False
    assert _matcher()(patterns, {}) is True


# ----- co-fire tests ------------------------------------------------

def test_can_co_fire_with_output_color_uniform() -> None:
    # iter 18 requires output K constant. When inputs are constant {C}
    # across pairs and outputs are constant K across all groups in all
    # pairs, both fire.
    patterns = {"pair_analyses": [
        _analysis(groups=[
            _group(positions=[(0, 0)], in_colors=(1,), out_colors=(7,)),
        ]),
        _analysis(groups=[
            _group(positions=[(2, 2)], in_colors=(1,), out_colors=(7,)),
        ]),
    ]}
    ocu = CONDITION_REGISTRY["output_color_uniform"]
    assert ocu(patterns, {}) is True
    assert _matcher()(patterns, {}) is True


def test_can_co_fire_with_input_color_uniform() -> None:
    # iter 19 fires AND iter 35 fires when the per-pair set is {C}.
    patterns = {"pair_analyses": [
        _analysis(groups=[
            _group(positions=[(0, 0)], in_colors=(2,), out_colors=(3,)),
        ]),
        _analysis(groups=[
            _group(positions=[(1, 1)], in_colors=(2,), out_colors=(3,)),
        ]),
    ]}
    icu = CONDITION_REGISTRY["input_color_uniform"]
    assert icu(patterns, {}) is True
    assert _matcher()(patterns, {}) is True


def test_can_co_fire_with_change_colors_constant_across_pairs() -> None:
    # iter 34 fires ⟹ iter 35 fires. Verify explicitly.
    patterns = {"pair_analyses": [
        _analysis(groups=[
            _group(positions=[(0, 0)], in_colors=(1,), out_colors=(2,)),
        ]),
        _analysis(groups=[
            _group(positions=[(2, 2)], in_colors=(1,), out_colors=(2,)),
        ]),
    ]}
    iter34 = CONDITION_REGISTRY["change_colors_constant_across_pairs"]
    assert iter34(patterns, {}) is True
    assert _matcher()(patterns, {}) is True


def test_can_co_fire_with_change_positions_constant_across_pairs() -> None:
    # iter 30 + iter 35: positions AND input colours both bit-identical.
    patterns = {"pair_analyses": [
        _analysis(groups=[
            _group(positions=[(0, 0)], in_colors=(1,), out_colors=(2,)),
        ]),
        _analysis(groups=[
            _group(positions=[(0, 0)], in_colors=(1,), out_colors=(2,)),
        ]),
    ]}
    iter30 = CONDITION_REGISTRY["change_positions_constant_across_pairs"]
    assert iter30(patterns, {}) is True
    assert _matcher()(patterns, {}) is True


def test_can_co_fire_with_change_count_constant_across_pairs() -> None:
    # iter 32 (count-constant) + iter 35: both fire when counts AND
    # per-pair input sets agree. Positions vary so iter 30 rejects.
    patterns = {"pair_analyses": [
        _analysis(groups=[
            _group(positions=[(0, 0)], in_colors=(1,), out_colors=(2,)),
        ]),
        _analysis(groups=[
            _group(positions=[(2, 2)], in_colors=(1,), out_colors=(2,)),
        ]),
    ]}
    iter32 = CONDITION_REGISTRY["change_count_constant_across_pairs"]
    iter30 = CONDITION_REGISTRY["change_positions_constant_across_pairs"]
    assert iter32(patterns, {}) is True
    assert iter30(patterns, {}) is False
    assert _matcher()(patterns, {}) is True


def test_iter_32_orthogonality_strict() -> None:
    # iter 35 (input-set-constant) does NOT imply iter 32
    # (count-constant). Constant input sets with varying counts: pair 0
    # has one 1-cell blob 1->2; pair 1 has one 2-cell blob 1->2. The
    # per-pair input set is {1} in both -- iter 35 fires. The per-pair
    # count is 1 vs 2 -- iter 32 rejects.
    patterns = {"pair_analyses": [
        _analysis(groups=[
            _group(positions=[(0, 0)], in_colors=(1,), out_colors=(2,)),
        ]),
        _analysis(groups=[
            _group(positions=[(2, 2), (2, 3)],
                   in_colors=(1,), out_colors=(2,)),
        ]),
    ]}
    iter32 = CONDITION_REGISTRY["change_count_constant_across_pairs"]
    assert _matcher()(patterns, {}) is True
    assert iter32(patterns, {}) is False


def test_can_co_fire_with_single_cell_change_per_pair() -> None:
    # Per-pair single-cell with the same input colour.
    patterns = {"pair_analyses": [
        _analysis(groups=[
            _group(positions=[(0, 1)], in_colors=(1,), out_colors=(2,)),
        ]),
        _analysis(groups=[
            _group(positions=[(2, 2)], in_colors=(1,), out_colors=(2,)),
        ]),
    ]}
    iter24 = CONDITION_REGISTRY["single_cell_change_per_pair"]
    assert iter24(patterns, {}) is True
    assert _matcher()(patterns, {}) is True


def test_can_co_fire_with_multi_group_per_pair() -> None:
    # Two single-cell blobs per pair, sharing the same input colour
    # but with different positions across pairs.
    patterns = {"pair_analyses": [
        _analysis(groups=[
            _group(positions=[(0, 0)], in_colors=(1,), out_colors=(2,)),
            _group(positions=[(2, 2)], in_colors=(1,), out_colors=(2,)),
        ]),
        _analysis(groups=[
            _group(positions=[(1, 1)], in_colors=(1,), out_colors=(2,)),
            _group(positions=[(0, 2)], in_colors=(1,), out_colors=(2,)),
        ]),
    ]}
    iter28 = CONDITION_REGISTRY["multi_group_per_pair"]
    assert iter28(patterns, {}) is True
    assert _matcher()(patterns, {}) is True


def test_does_not_require_grid_size_preserved() -> None:
    # Colour-content matcher cares only about per-pair input-colour
    # sets. It CAN fire on dimension-changed pairs.
    patterns = {"pair_analyses": [
        _analysis(groups=[
            _group(positions=[(0, 0)], in_colors=(1,), out_colors=(2,)),
        ], output_height=5, output_width=5, size_match=False),
        _analysis(groups=[
            _group(positions=[(2, 2)], in_colors=(1,), out_colors=(2,)),
        ], output_height=5, output_width=5, size_match=False),
    ]}
    gsp = CONDITION_REGISTRY["grid_size_preserved"]
    assert _matcher()(patterns, {}) is True
    assert gsp(patterns, {}) is False


def test_orthogonal_to_dimensional_axes() -> None:
    # Co-fires with output_dimensions_constant / input_dimensions_constant
    # when the dims are constant.
    patterns = {"pair_analyses": [
        _analysis(groups=[
            _group(positions=[(0, 0)], in_colors=(1,), out_colors=(2,)),
        ]),
        _analysis(groups=[
            _group(positions=[(2, 2)], in_colors=(1,), out_colors=(2,)),
        ]),
    ]}
    odc = CONDITION_REGISTRY["output_dimensions_constant"]
    idc = CONDITION_REGISTRY["input_dimensions_constant"]
    assert odc(patterns, {}) is True
    assert idc(patterns, {}) is True
    assert _matcher()(patterns, {}) is True


# ----- end-to-end with the real extractor --------------------------

def test_end_to_end_agreement_with_extract_pattern_shape() -> None:
    # Two 3x3 pairs: each recolours one cell of colour 1 to colour 2,
    # but at different positions. iter 35 should fire (per-pair input
    # set is {1} on both); iter 34 also fires (same (1, 2) mapping);
    # iter 30 rejects (positions differ).
    from agent.active_operators import ExtractPatternOperator  # noqa: E402

    op = ExtractPatternOperator()

    class _Grid:
        def __init__(self, raw):
            self.raw = raw
            self.height = len(raw)
            self.width = len(raw[0]) if raw else 0

    raw_in = [[1, 0, 0], [0, 1, 0], [0, 0, 1]]
    raw_out_a = [[2, 0, 0], [0, 1, 0], [0, 0, 1]]   # changes (0, 0): 1->2
    raw_out_b = [[1, 0, 0], [0, 1, 0], [0, 0, 2]]   # changes (2, 2): 1->2
    analysis_a = op._analyze_pair(_Grid(raw_in), _Grid(raw_out_a))
    analysis_b = op._analyze_pair(_Grid(raw_in), _Grid(raw_out_b))
    patterns = {"pair_analyses": [analysis_a, analysis_b]}
    iter34 = CONDITION_REGISTRY["change_colors_constant_across_pairs"]
    iter30 = CONDITION_REGISTRY["change_positions_constant_across_pairs"]
    assert iter30(patterns, {}) is False
    assert iter34(patterns, {}) is True
    assert _matcher()(patterns, {}) is True


def test_end_to_end_agreement_when_only_input_projection_constant() -> None:
    # Two pairs: pair 0 maps 1->2 (one cell), pair 1 maps 1->3 (one
    # cell). Per-pair input set is {1} on both -- iter 35 fires. iter
    # 34 rejects (per-pair (ic, oc) sets {(1,2)} vs {(1,3)} differ).
    # iter 8 rejects (unioned mapping 1->{2,3} non-functional).
    from agent.active_operators import ExtractPatternOperator  # noqa: E402

    op = ExtractPatternOperator()

    class _Grid:
        def __init__(self, raw):
            self.raw = raw
            self.height = len(raw)
            self.width = len(raw[0]) if raw else 0

    raw_in = [[1, 0, 0], [0, 0, 0], [0, 0, 0]]
    raw_out_a = [[2, 0, 0], [0, 0, 0], [0, 0, 0]]   # 1 -> 2
    raw_out_b = [[3, 0, 0], [0, 0, 0], [0, 0, 0]]   # 1 -> 3
    analysis_a = op._analyze_pair(_Grid(raw_in), _Grid(raw_out_a))
    analysis_b = op._analyze_pair(_Grid(raw_in), _Grid(raw_out_b))
    patterns = {"pair_analyses": [analysis_a, analysis_b]}
    iter34 = CONDITION_REGISTRY["change_colors_constant_across_pairs"]
    iter8 = CONDITION_REGISTRY["consistent_color_mapping"]
    assert iter34(patterns, {}) is False
    assert iter8(patterns, {}) is False
    assert _matcher()(patterns, {}) is True


def test_returns_strict_boolean_type() -> None:
    patterns = {"pair_analyses": [
        _analysis(groups=[
            _group(positions=[(0, 0)], in_colors=(1,), out_colors=(2,)),
        ]),
        _analysis(groups=[
            _group(positions=[(2, 2)], in_colors=(1,), out_colors=(2,)),
        ]),
    ]}
    result_pos = _matcher()(patterns, {})
    result_neg = _matcher()({"pair_analyses": []}, {})
    assert result_pos is True, f"expected True, got {result_pos!r}"
    assert result_neg is False, f"expected False, got {result_neg!r}"


# ----------------------------------------------------------------------
# Driver.
# ----------------------------------------------------------------------

def _run_all() -> int:
    tests = [
        test_registered_in_global_registry,
        test_previous_matchers_still_registered,
        test_at_least_eighteen_distinct_matchers_registered,
        test_matcher_is_callable,
        test_returns_true_on_single_pair_single_group,
        test_returns_true_on_two_pairs_same_singleton_input_set,
        test_returns_true_on_multi_group_same_input_set,
        test_returns_false_on_empty_pair_analyses,
        test_returns_false_on_missing_pair_analyses,
        test_returns_false_on_non_dict_patterns,
        test_returns_false_on_non_list_pair_analyses,
        test_returns_false_on_malformed_analysis_entry,
        test_returns_false_when_every_pair_has_zero_groups,
        test_returns_false_when_one_pair_has_no_groups,
        test_returns_false_when_input_sets_differ_across_pairs,
        test_returns_false_when_one_pair_has_extra_input_color,
        test_returns_false_on_multi_input_colors_in_group,
        test_returns_true_on_multi_output_colors_in_group,
        test_returns_false_on_empty_input_colors_list,
        test_returns_false_on_missing_input_colors,
        test_returns_false_on_non_list_input_colors,
        test_returns_false_on_bool_subclass_in_input_colors,
        test_returns_false_on_out_of_range_input_colors,
        test_returns_false_on_non_int_input_colors,
        test_returns_false_on_non_list_groups,
        test_returns_false_on_non_dict_group_entry,
        test_is_side_effect_free_on_inputs,
        test_is_deterministic_across_repeats,
        test_mutually_exclusive_with_identity_transformation,
        test_iter_34_refinement_implication_holds,
        test_iter_34_refinement_strict_one_direction,
        test_iter_19_refinement_implication_holds,
        test_iter_19_refinement_strict_one_direction,
        test_independent_of_consistent_color_mapping_iter_8_fires_alone,
        test_independent_of_consistent_color_mapping_iter_35_fires_alone,
        test_can_co_fire_with_output_color_uniform,
        test_can_co_fire_with_input_color_uniform,
        test_can_co_fire_with_change_colors_constant_across_pairs,
        test_can_co_fire_with_change_positions_constant_across_pairs,
        test_can_co_fire_with_change_count_constant_across_pairs,
        test_iter_32_orthogonality_strict,
        test_can_co_fire_with_single_cell_change_per_pair,
        test_can_co_fire_with_multi_group_per_pair,
        test_does_not_require_grid_size_preserved,
        test_orthogonal_to_dimensional_axes,
        test_end_to_end_agreement_with_extract_pattern_shape,
        test_end_to_end_agreement_when_only_input_projection_constant,
        test_returns_strict_boolean_type,
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
        print(f"\nall {MATCHER_NAME} tests passed.")
    else:
        print(f"\n{rc} test(s) failed.")
    sys.exit(0 if rc == 0 else 1)
