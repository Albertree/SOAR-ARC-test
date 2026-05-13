"""
tests/test_change_color_mapping_count_constant_across_pairs.py -- exercise
the iter-40 matcher
``agent.conditions.change_color_mapping_count_constant_across_pairs``.

Runs without pytest:

    python tests/test_change_color_mapping_count_constant_across_pairs.py

Dependency-free, same runner style as iters
1 / 8 / 10 / 13 / 17 / 18 / 19 / 20 / 22 / 23 / 24 / 26 / 28 / 30 / 32 /
33 / 34 / 35 / 36 / 37 / 38 / 39.

The matcher is on the colour-content cross-pair (ic, oc) CARDINALITY
axis: per-pair count of distinct (input_colour, output_colour) mappings
is bit-identical across every pair, regardless of which specific
mappings. Strictly weaker than iter 34 (set bit-identical implies
cardinality equal, but not vice versa). The iter-32-to-iter-30
cardinality-projection pattern applied to iter 34's (ic, oc) set axis.
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


MATCHER_NAME = "change_color_mapping_count_constant_across_pairs"


def _matcher():
    return CONDITION_REGISTRY[MATCHER_NAME]


def _group(*, positions, in_colors=(0,), out_colors=(3,)):
    """Build a group analysis dict matching ``_analyze_pair``'s emit shape."""
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
                  "change_colors_constant_across_pairs",
                  "change_input_colors_constant_across_pairs",
                  "change_output_colors_constant_across_pairs",
                  "change_input_color_count_constant_across_pairs",
                  "change_output_color_count_constant_across_pairs",
                  "change_group_count_constant_across_pairs"):
        assert prior in CONDITION_REGISTRY, (
            f"prior matcher {prior!r} missing after iter-40 addition"
        )


def test_at_least_twenty_three_distinct_matchers_registered() -> None:
    # P5 unit-monotone counter -- iter 40 lifts the count from 22 to 23.
    assert len(CONDITION_REGISTRY) >= 23, (
        f"expected at least 23 entries, got {len(CONDITION_REGISTRY)}: "
        f"{sorted(CONDITION_REGISTRY)}"
    )


def test_matcher_is_callable() -> None:
    fn = _matcher()
    assert callable(fn), f"registered entry is not callable: {fn!r}"


def test_returns_true_on_single_pair_single_group() -> None:
    # One pair with one group -- cardinality 1, trivially constant.
    patterns = {"pair_analyses": [
        _analysis(groups=[
            _group(positions=[(1, 1)], in_colors=(1,), out_colors=(2,)),
        ]),
    ]}
    assert _matcher()(patterns, {}) is True


def test_returns_true_on_two_pairs_same_cardinality_same_mappings() -> None:
    # Both pairs cardinality 1 with the SAME mapping (1, 2). Iter 34
    # also fires; this matcher fires (weaker condition).
    patterns = {"pair_analyses": [
        _analysis(groups=[
            _group(positions=[(0, 0)], in_colors=(1,), out_colors=(2,)),
        ]),
        _analysis(groups=[
            _group(positions=[(2, 2)], in_colors=(1,), out_colors=(2,)),
        ]),
    ]}
    assert _matcher()(patterns, {}) is True


def test_returns_true_on_two_pairs_same_cardinality_distinct_mappings() -> None:
    # The iter-40-exclusive territory: both pairs cardinality 2 but the
    # specific (ic, oc) pairs differ. iter 34 rejects (sets differ);
    # this matcher fires (cardinalities equal).
    patterns = {"pair_analyses": [
        _analysis(groups=[
            _group(positions=[(0, 0)], in_colors=(1,), out_colors=(2,)),
            _group(positions=[(2, 2)], in_colors=(3,), out_colors=(4,)),
        ]),
        _analysis(groups=[
            _group(positions=[(1, 1)], in_colors=(5,), out_colors=(6,)),
            _group(positions=[(0, 2)], in_colors=(7,), out_colors=(8,)),
        ]),
    ]}
    iter34 = CONDITION_REGISTRY["change_colors_constant_across_pairs"]
    assert iter34(patterns, {}) is False
    assert _matcher()(patterns, {}) is True


def test_returns_false_when_cardinalities_differ_across_pairs() -> None:
    # Pair 0 cardinality 1 ({(1, 2)}); pair 1 cardinality 2
    # ({(1, 2), (3, 4)}). Cardinalities 1 vs 2 differ.
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
    # Identity case: per-pair (ic, oc) set is empty (cardinality 0).
    # The matcher rejects vacuously-zero cardinality matches to keep
    # its territory disjoint from iter 13's identity_transformation.
    patterns = {"pair_analyses": [
        _analysis(groups=[]),
        _analysis(groups=[]),
    ]}
    assert _matcher()(patterns, {}) is False


def test_returns_false_when_one_pair_has_no_groups() -> None:
    # Pair 0 cardinality 1; pair 1 cardinality 0. Strict reject --
    # cardinality >= 1 required on EVERY pair.
    patterns = {"pair_analyses": [
        _analysis(groups=[
            _group(positions=[(0, 0)], in_colors=(1,), out_colors=(2,)),
        ]),
        _analysis(groups=[]),
    ]}
    assert _matcher()(patterns, {}) is False


def test_returns_false_on_multi_input_colors_in_group() -> None:
    # A group with two input colours has an ill-defined (ic, oc) pair;
    # the matcher fail-closes mirroring iter 18 / 19 / 34's per-group
    # cardinality-1 posture.
    group_bad = {
        "input_colors": [1, 2], "output_colors": [3],
        "top_row": 0, "top_col": 0, "cell_count": 2,
        "positions": [(0, 0), (0, 1)],
    }
    patterns = {"pair_analyses": [_analysis(groups=[group_bad])]}
    assert _matcher()(patterns, {}) is False


def test_returns_false_on_multi_output_colors_in_group() -> None:
    # A group with two output colours is symmetrically ill-defined.
    # Unlike iter 37 (which only inspects input_colors and allows
    # multi-output groups), this matcher inspects the FULL (ic, oc)
    # pair so multi-output groups must fail-close.
    group_bad = {
        "input_colors": [1], "output_colors": [3, 4],
        "top_row": 0, "top_col": 0, "cell_count": 2,
        "positions": [(0, 0), (0, 1)],
    }
    patterns = {"pair_analyses": [_analysis(groups=[group_bad])]}
    assert _matcher()(patterns, {}) is False


def test_returns_false_on_empty_input_colors_list() -> None:
    group_bad = {
        "input_colors": [], "output_colors": [3],
        "top_row": 0, "top_col": 0, "cell_count": 1,
        "positions": [(0, 0)],
    }
    patterns = {"pair_analyses": [_analysis(groups=[group_bad])]}
    assert _matcher()(patterns, {}) is False


def test_returns_false_on_empty_output_colors_list() -> None:
    group_bad = {
        "input_colors": [1], "output_colors": [],
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


def test_returns_false_on_missing_output_colors() -> None:
    group_bad = {
        "input_colors": [1],
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


def test_returns_false_on_non_list_output_colors() -> None:
    for bad in (1, "1", None, {"k": 1}):
        group_bad = {
            "input_colors": [1], "output_colors": bad,
            "top_row": 0, "top_col": 0, "cell_count": 1,
            "positions": [(0, 0)],
        }
        patterns = {"pair_analyses": [_analysis(groups=[group_bad])]}
        assert _matcher()(patterns, {}) is False, (
            f"output_colors={bad!r} (non-list) should fail-closed"
        )


def test_returns_false_on_bool_subclass_in_colors() -> None:
    for bad in (True, False):
        # Both sides tested.
        group_bad_in = {
            "input_colors": [bad], "output_colors": [3],
            "top_row": 0, "top_col": 0, "cell_count": 1,
            "positions": [(0, 0)],
        }
        group_bad_out = {
            "input_colors": [1], "output_colors": [bad],
            "top_row": 0, "top_col": 0, "cell_count": 1,
            "positions": [(0, 0)],
        }
        for bad_group in (group_bad_in, group_bad_out):
            patterns = {"pair_analyses": [_analysis(groups=[bad_group])]}
            assert _matcher()(patterns, {}) is False, (
                f"bool subclass {bad!r} in colours should fail-closed"
            )


def test_returns_false_on_out_of_range_colors() -> None:
    for bad in (-1, 10, 13, 100):
        group_bad_in = {
            "input_colors": [bad], "output_colors": [3],
            "top_row": 0, "top_col": 0, "cell_count": 1,
            "positions": [(0, 0)],
        }
        group_bad_out = {
            "input_colors": [1], "output_colors": [bad],
            "top_row": 0, "top_col": 0, "cell_count": 1,
            "positions": [(0, 0)],
        }
        for bad_group in (group_bad_in, group_bad_out):
            patterns = {"pair_analyses": [_analysis(groups=[bad_group])]}
            assert _matcher()(patterns, {}) is False, (
                f"out-of-range colour {bad} should fail-closed"
            )


def test_returns_false_on_non_int_colors() -> None:
    for bad in (0.5, "1", None, [1]):
        group_bad_in = {
            "input_colors": [bad], "output_colors": [3],
            "top_row": 0, "top_col": 0, "cell_count": 1,
            "positions": [(0, 0)],
        }
        group_bad_out = {
            "input_colors": [1], "output_colors": [bad],
            "top_row": 0, "top_col": 0, "cell_count": 1,
            "positions": [(0, 0)],
        }
        for bad_group in (group_bad_in, group_bad_out):
            patterns = {"pair_analyses": [_analysis(groups=[bad_group])]}
            assert _matcher()(patterns, {}) is False, (
                f"non-int colour {bad!r} should fail-closed"
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
            _group(positions=[(2, 2)], in_colors=(3,), out_colors=(4,)),
        ]),
    ]}
    results = [_matcher()(patterns, {}) for _ in range(5)]
    assert len(set(results)) == 1, f"non-deterministic outputs: {results}"


def test_returns_strict_boolean_type() -> None:
    patterns = {"pair_analyses": [
        _analysis(groups=[
            _group(positions=[(0, 0)], in_colors=(1,), out_colors=(2,)),
        ]),
        _analysis(groups=[
            _group(positions=[(2, 2)], in_colors=(1,), out_colors=(2,)),
        ]),
    ]}
    result = _matcher()(patterns, {})
    assert result is True or result is False, (
        f"matcher did not return strict bool: {result!r} "
        f"(type {type(result).__name__})"
    )


# ----- mutual-exclusion / refinement-chain tests --------------------

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
    # iter 34 fires => this matcher fires (set bit-identical implies
    # same cardinality). Verify on a positive fixture.
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
    # This matcher fires where iter 34 does NOT: per-pair (ic, oc)
    # cardinalities are equal but the SETS differ -- pair 0 has
    # {(1, 2), (3, 4)}, pair 1 has {(5, 6), (7, 8)}; both cardinality 2.
    patterns = {"pair_analyses": [
        _analysis(groups=[
            _group(positions=[(0, 0)], in_colors=(1,), out_colors=(2,)),
            _group(positions=[(2, 2)], in_colors=(3,), out_colors=(4,)),
        ]),
        _analysis(groups=[
            _group(positions=[(0, 0)], in_colors=(5,), out_colors=(6,)),
            _group(positions=[(2, 2)], in_colors=(7,), out_colors=(8,)),
        ]),
    ]}
    iter34 = CONDITION_REGISTRY["change_colors_constant_across_pairs"]
    assert _matcher()(patterns, {}) is True
    assert iter34(patterns, {}) is False


def test_independent_of_iter_37_iter_40_fires_alone() -> None:
    # This matcher fires where iter 37 does NOT: per-pair (ic, oc)
    # cardinalities equal but per-pair input-colour cardinalities
    # differ. Pair 0 has {(1, 2), (3, 2)} (two inputs, two mappings,
    # both to 2); pair 1 has {(1, 2), (1, 3)} (one input, two
    # mappings, to 2 and 3). Per-pair (ic, oc) cardinality 2 on both
    # (this matcher fires); per-pair input cardinalities 2 vs 1 (iter
    # 37 rejects).
    patterns = {"pair_analyses": [
        _analysis(groups=[
            _group(positions=[(0, 0)], in_colors=(1,), out_colors=(2,)),
            _group(positions=[(2, 2)], in_colors=(3,), out_colors=(2,)),
        ]),
        _analysis(groups=[
            _group(positions=[(0, 0)], in_colors=(1,), out_colors=(2,)),
            _group(positions=[(2, 2)], in_colors=(1,), out_colors=(3,)),
        ]),
    ]}
    iter37 = CONDITION_REGISTRY["change_input_color_count_constant_across_pairs"]
    assert _matcher()(patterns, {}) is True
    assert iter37(patterns, {}) is False


def test_independent_of_iter_37_iter_37_fires_alone() -> None:
    # iter 37 fires where this matcher does NOT: per-pair input-colour
    # cardinalities equal but per-pair (ic, oc) cardinalities differ.
    # Pair 0 has {(1, 2)} (one input, one mapping); pair 1 has
    # {(1, 2), (1, 3)} (one input, two mappings).
    patterns = {"pair_analyses": [
        _analysis(groups=[
            _group(positions=[(0, 0)], in_colors=(1,), out_colors=(2,)),
        ]),
        _analysis(groups=[
            _group(positions=[(0, 0)], in_colors=(1,), out_colors=(2,)),
            _group(positions=[(2, 2)], in_colors=(1,), out_colors=(3,)),
        ]),
    ]}
    iter37 = CONDITION_REGISTRY["change_input_color_count_constant_across_pairs"]
    assert iter37(patterns, {}) is True
    assert _matcher()(patterns, {}) is False


def test_independent_of_iter_38_iter_40_fires_alone() -> None:
    # Symmetric to iter-37 test on the output side. This matcher fires
    # where iter 38 does NOT: per-pair (ic, oc) cardinalities equal
    # but per-pair output-colour cardinalities differ. Pair 0 has
    # {(2, 1), (2, 3)} (one output direction... wait, two outputs);
    # pair 1 has {(1, 2), (3, 2)} (one output, two inputs).
    patterns = {"pair_analyses": [
        _analysis(groups=[
            _group(positions=[(0, 0)], in_colors=(2,), out_colors=(1,)),
            _group(positions=[(2, 2)], in_colors=(2,), out_colors=(3,)),
        ]),
        _analysis(groups=[
            _group(positions=[(0, 0)], in_colors=(1,), out_colors=(2,)),
            _group(positions=[(2, 2)], in_colors=(3,), out_colors=(2,)),
        ]),
    ]}
    iter38 = CONDITION_REGISTRY["change_output_color_count_constant_across_pairs"]
    assert _matcher()(patterns, {}) is True
    assert iter38(patterns, {}) is False


def test_independent_of_iter_39_iter_40_fires_alone() -> None:
    # This matcher fires where iter 39 does NOT: per-pair (ic, oc)
    # cardinalities equal but per-pair group counts differ. Pair 0
    # has two groups sharing one (ic, oc) {(1, 2)} (cardinality 1,
    # num_groups 2); pair 1 has one group of (1, 2) (cardinality 1,
    # num_groups 1).
    patterns = {"pair_analyses": [
        _analysis(groups=[
            _group(positions=[(0, 0)], in_colors=(1,), out_colors=(2,)),
            _group(positions=[(2, 2)], in_colors=(1,), out_colors=(2,)),
        ]),
        _analysis(groups=[
            _group(positions=[(1, 1)], in_colors=(1,), out_colors=(2,)),
        ]),
    ]}
    iter39 = CONDITION_REGISTRY["change_group_count_constant_across_pairs"]
    assert _matcher()(patterns, {}) is True
    assert iter39(patterns, {}) is False


def test_independent_of_iter_39_iter_39_fires_alone() -> None:
    # iter 39 fires where this matcher does NOT: per-pair group counts
    # equal but per-pair (ic, oc) cardinalities differ. Pair 0 has two
    # groups sharing one (ic, oc) {(1, 2)} (cardinality 1, num_groups
    # 2); pair 1 has two groups with distinct mappings
    # {(1, 2), (3, 4)} (cardinality 2, num_groups 2).
    patterns = {"pair_analyses": [
        _analysis(groups=[
            _group(positions=[(0, 0)], in_colors=(1,), out_colors=(2,)),
            _group(positions=[(2, 2)], in_colors=(1,), out_colors=(2,)),
        ]),
        _analysis(groups=[
            _group(positions=[(0, 0)], in_colors=(1,), out_colors=(2,)),
            _group(positions=[(2, 2)], in_colors=(3,), out_colors=(4,)),
        ]),
    ]}
    iter39 = CONDITION_REGISTRY["change_group_count_constant_across_pairs"]
    assert iter39(patterns, {}) is True
    assert _matcher()(patterns, {}) is False


def test_can_co_fire_with_change_count_constant_across_pairs() -> None:
    # Both fire when per-pair (ic, oc) cardinality AND per-pair cell
    # count both constant.
    patterns = {"pair_analyses": [
        _analysis(groups=[
            _group(positions=[(0, 0)], in_colors=(1,), out_colors=(2,)),
        ]),
        _analysis(groups=[
            _group(positions=[(2, 2)], in_colors=(1,), out_colors=(2,)),
        ]),
    ]}
    iter32 = CONDITION_REGISTRY["change_count_constant_across_pairs"]
    assert iter32(patterns, {}) is True
    assert _matcher()(patterns, {}) is True


def test_can_co_fire_with_output_color_uniform() -> None:
    # Output K constant AND per-pair (ic, oc) cardinality constant.
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


def test_can_co_fire_with_multi_group_per_pair() -> None:
    # Multi-group with the same per-pair (ic, oc) cardinality (2
    # mappings per pair) across pairs.
    patterns = {"pair_analyses": [
        _analysis(groups=[
            _group(positions=[(0, 0)], in_colors=(1,), out_colors=(2,)),
            _group(positions=[(2, 2)], in_colors=(3,), out_colors=(2,)),
        ]),
        _analysis(groups=[
            _group(positions=[(1, 1)], in_colors=(5,), out_colors=(2,)),
            _group(positions=[(0, 2)], in_colors=(7,), out_colors=(2,)),
        ]),
    ]}
    iter28 = CONDITION_REGISTRY["multi_group_per_pair"]
    iter34 = CONDITION_REGISTRY["change_colors_constant_across_pairs"]
    assert iter28(patterns, {}) is True
    assert iter34(patterns, {}) is False
    assert _matcher()(patterns, {}) is True


def test_does_not_require_grid_size_preserved() -> None:
    # Colour-content matcher cares only about per-pair (ic, oc)
    # cardinality. CAN fire on dimension-changed pairs.
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


# ----- end-to-end with the real extractor --------------------------

def test_end_to_end_agreement_with_extract_pattern_shape() -> None:
    # Two 3x3 pairs: each pair recolours one cell of input colour 1 to
    # output colour 2. Per-pair (ic, oc) set = {(1, 2)} on both pairs
    # (cardinality 1). This matcher fires; iter 34 also fires (same
    # set); iter 30 rejects (positions differ).
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


def test_end_to_end_agreement_when_only_cardinality_constant() -> None:
    # The iter-40-exclusive end-to-end case: two 3x3 pairs with
    # cardinality-1 (ic, oc) sets but DIFFERENT mappings. Iter 34
    # rejects ({(1, 5)} vs {(7, 5)} differ); this matcher fires.
    from agent.active_operators import ExtractPatternOperator  # noqa: E402

    op = ExtractPatternOperator()

    class _Grid:
        def __init__(self, raw):
            self.raw = raw
            self.height = len(raw)
            self.width = len(raw[0]) if raw else 0

    raw_in_a = [[1, 0, 0], [0, 0, 0], [0, 0, 0]]
    raw_out_a = [[5, 0, 0], [0, 0, 0], [0, 0, 0]]   # mapping (1, 5)
    raw_in_b = [[7, 0, 0], [0, 0, 0], [0, 0, 0]]
    raw_out_b = [[2, 0, 0], [0, 0, 0], [0, 0, 0]]   # mapping (7, 2)
    analysis_a = op._analyze_pair(_Grid(raw_in_a), _Grid(raw_out_a))
    analysis_b = op._analyze_pair(_Grid(raw_in_b), _Grid(raw_out_b))
    patterns = {"pair_analyses": [analysis_a, analysis_b]}
    iter34 = CONDITION_REGISTRY["change_colors_constant_across_pairs"]
    assert iter34(patterns, {}) is False
    assert _matcher()(patterns, {}) is True


# ----------------------------------------------------------------------
# Driver.
# ----------------------------------------------------------------------

def _run_all() -> int:
    tests = [
        test_registered_in_global_registry,
        test_previous_matchers_still_registered,
        test_at_least_twenty_three_distinct_matchers_registered,
        test_matcher_is_callable,
        test_returns_true_on_single_pair_single_group,
        test_returns_true_on_two_pairs_same_cardinality_same_mappings,
        test_returns_true_on_two_pairs_same_cardinality_distinct_mappings,
        test_returns_false_when_cardinalities_differ_across_pairs,
        test_returns_false_on_empty_pair_analyses,
        test_returns_false_on_missing_pair_analyses,
        test_returns_false_on_non_dict_patterns,
        test_returns_false_on_non_list_pair_analyses,
        test_returns_false_on_malformed_analysis_entry,
        test_returns_false_when_every_pair_has_zero_groups,
        test_returns_false_when_one_pair_has_no_groups,
        test_returns_false_on_multi_input_colors_in_group,
        test_returns_false_on_multi_output_colors_in_group,
        test_returns_false_on_empty_input_colors_list,
        test_returns_false_on_empty_output_colors_list,
        test_returns_false_on_missing_input_colors,
        test_returns_false_on_missing_output_colors,
        test_returns_false_on_non_list_input_colors,
        test_returns_false_on_non_list_output_colors,
        test_returns_false_on_bool_subclass_in_colors,
        test_returns_false_on_out_of_range_colors,
        test_returns_false_on_non_int_colors,
        test_returns_false_on_non_list_groups,
        test_returns_false_on_non_dict_group_entry,
        test_is_side_effect_free_on_inputs,
        test_is_deterministic_across_repeats,
        test_returns_strict_boolean_type,
        test_mutually_exclusive_with_identity_transformation,
        test_iter_34_refinement_implication_holds,
        test_iter_34_refinement_strict_one_direction,
        test_independent_of_iter_37_iter_40_fires_alone,
        test_independent_of_iter_37_iter_37_fires_alone,
        test_independent_of_iter_38_iter_40_fires_alone,
        test_independent_of_iter_39_iter_40_fires_alone,
        test_independent_of_iter_39_iter_39_fires_alone,
        test_can_co_fire_with_change_count_constant_across_pairs,
        test_can_co_fire_with_output_color_uniform,
        test_can_co_fire_with_multi_group_per_pair,
        test_does_not_require_grid_size_preserved,
        test_end_to_end_agreement_with_extract_pattern_shape,
        test_end_to_end_agreement_when_only_cardinality_constant,
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
