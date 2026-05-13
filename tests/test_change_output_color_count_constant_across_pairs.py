"""
tests/test_change_output_color_count_constant_across_pairs.py -- exercise
the iter-38 matcher
``agent.conditions.change_output_color_count_constant_across_pairs``.

Runs without pytest:

    python tests/test_change_output_color_count_constant_across_pairs.py

Dependency-free, same runner style as iters
1 / 8 / 10 / 13 / 17 / 18 / 19 / 20 / 22 / 23 / 24 / 26 / 28 / 30 / 32
/ 33 / 34 / 35 / 36 / 37.

The matcher is on the colour-content cross-pair output-colour CARDINALITY
axis: per-pair count of distinct output colours produced in the change
groups is bit-identical across every pair, regardless of which specific
colours. Strictly weaker than iter 36 (set bit-identical implies
cardinality equal, but not vice versa). The iter-32-to-iter-30
cardinality projection pattern applied to iter 36's output-colour set
axis. Symmetric output-side mirror of iter 37 on the input axis: this
file is the structural mirror of
``tests/test_change_input_color_count_constant_across_pairs.py`` with
``input_colors`` <-> ``output_colors`` swapped and the cross-matcher
references (iter 35 <-> iter 36, iter 19 <-> iter 18, etc.) flipped to
the output-side counterparts named in the matcher's docstring.

The matcher's docstring explicitly draws every cross-matcher relation
this test exercises:

  * iter 18 (``output_color_uniform``) ==> iter 36 ==> iter 38 (strict
    refinement chain through the output set axis)
  * iter 34 ==> iter 36 ==> iter 38 (the joint (ic, oc) set chain
    projects to output-cardinality via iter 36)
  * iter 37 (``change_input_color_count_constant_across_pairs``)
    INDEPENDENT in both directions (the orthogonal-axis projection
    sibling)
  * iter 32 (``change_count_constant_across_pairs``) INDEPENDENT
    (cell-count vs output-cardinality axes)
  * identity_transformation (iter 13) STRICTLY MUTUALLY EXCLUSIVE
    in practice (the zero-cardinality refusal clause)
  * Dimension-agnostic (CAN co-fire with grid_size_changed /
    output_dimensions_constant / input_dimensions_constant) -- the
    colour-content axis does not depend on shape.
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


MATCHER_NAME = "change_output_color_count_constant_across_pairs"


def _matcher():
    return CONDITION_REGISTRY[MATCHER_NAME]


def _group(*, positions, in_colors=(1,), out_colors=(2,)):
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
    # Every matcher up to and including iter 37 -- iter 38 must coexist.
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
                  "change_input_color_count_constant_across_pairs"):
        assert prior in CONDITION_REGISTRY, (
            f"prior matcher {prior!r} missing after iter-38 addition"
        )


def test_at_least_twenty_one_distinct_matchers_registered() -> None:
    # P5 unit-monotone counter -- iter 38 lifts the count from 20 to 21.
    assert len(CONDITION_REGISTRY) >= 21, (
        f"expected at least 21 entries, got {len(CONDITION_REGISTRY)}: "
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


def test_returns_true_on_two_pairs_same_cardinality_same_colours() -> None:
    # Both pairs cardinality 1 with the SAME colour {2}. Iter 36 fires
    # too; iter 38 fires (weaker condition).
    patterns = {"pair_analyses": [
        _analysis(groups=[
            _group(positions=[(0, 0)], in_colors=(1,), out_colors=(2,)),
        ]),
        _analysis(groups=[
            _group(positions=[(2, 2)], in_colors=(3,), out_colors=(2,)),
        ]),
    ]}
    assert _matcher()(patterns, {}) is True


def test_returns_true_on_two_pairs_same_cardinality_distinct_colours() -> None:
    # The iter-38-exclusive territory: both pairs cardinality 2 but the
    # specific output colours differ. iter 36 rejects (sets differ);
    # iter 38 fires (cardinalities equal).
    patterns = {"pair_analyses": [
        _analysis(groups=[
            _group(positions=[(0, 0)], in_colors=(1,), out_colors=(2,)),
            _group(positions=[(2, 2)], in_colors=(1,), out_colors=(3,)),
        ]),
        _analysis(groups=[
            _group(positions=[(1, 1)], in_colors=(1,), out_colors=(4,)),
            _group(positions=[(0, 2)], in_colors=(1,), out_colors=(5,)),
        ]),
    ]}
    iter36 = CONDITION_REGISTRY["change_output_colors_constant_across_pairs"]
    assert iter36(patterns, {}) is False
    assert _matcher()(patterns, {}) is True


def test_returns_false_when_cardinalities_differ_across_pairs() -> None:
    # Pair 0 has cardinality 1 (just {2}); pair 1 has cardinality 2
    # ({2, 3}). Cardinalities 1 vs 2 differ.
    patterns = {"pair_analyses": [
        _analysis(groups=[
            _group(positions=[(0, 0)], in_colors=(1,), out_colors=(2,)),
        ]),
        _analysis(groups=[
            _group(positions=[(0, 0)], in_colors=(1,), out_colors=(2,)),
            _group(positions=[(2, 2)], in_colors=(1,), out_colors=(3,)),
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
    # Identity case: per-pair output set is empty (cardinality 0). The
    # matcher rejects vacuously-zero cardinality matches to keep its
    # territory disjoint from iter 13's identity_transformation.
    patterns = {"pair_analyses": [
        _analysis(groups=[]),
        _analysis(groups=[]),
    ]}
    assert _matcher()(patterns, {}) is False


def test_returns_false_when_one_pair_has_no_groups() -> None:
    # Pair 0 has cardinality 1; pair 1 has cardinality 0. Strict
    # reject -- iter 38 requires cardinality >= 1 on EVERY pair.
    patterns = {"pair_analyses": [
        _analysis(groups=[
            _group(positions=[(0, 0)], in_colors=(1,), out_colors=(2,)),
        ]),
        _analysis(groups=[]),
    ]}
    assert _matcher()(patterns, {}) is False


def test_returns_false_on_multi_output_colors_in_group() -> None:
    # A group with two output colours has an ill-defined output
    # projection; the matcher fail-closes mirroring iter 18 / 19 / 34
    # / 35 / 36 / 37's per-group cardinality-1 posture.
    group_bad = {
        "input_colors": [1], "output_colors": [3, 4],
        "top_row": 0, "top_col": 0, "cell_count": 2,
        "positions": [(0, 0), (0, 1)],
    }
    patterns = {"pair_analyses": [_analysis(groups=[group_bad])]}
    assert _matcher()(patterns, {}) is False


def test_returns_true_on_multi_input_colors_in_group() -> None:
    # Multi-input is allowed: iter 38 inspects only output_colors
    # cardinality, symmetric to iter 36's output-projection design and
    # iter 37's input-projection design (which allows multi-output).
    group_a = {
        "input_colors": [1, 2], "output_colors": [3],
        "top_row": 0, "top_col": 0, "cell_count": 2,
        "positions": [(0, 0), (0, 1)],
    }
    group_b = {
        "input_colors": [4, 5], "output_colors": [3],
        "top_row": 0, "top_col": 0, "cell_count": 2,
        "positions": [(1, 0), (1, 1)],
    }
    patterns = {"pair_analyses": [
        _analysis(groups=[group_a]),
        _analysis(groups=[group_b]),
    ]}
    assert _matcher()(patterns, {}) is True


def test_returns_false_on_empty_output_colors_list() -> None:
    group_bad = {
        "input_colors": [1], "output_colors": [],
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


def test_returns_false_on_bool_subclass_in_output_colors() -> None:
    for bad in (True, False):
        group_bad = {
            "input_colors": [1], "output_colors": [bad],
            "top_row": 0, "top_col": 0, "cell_count": 1,
            "positions": [(0, 0)],
        }
        patterns = {"pair_analyses": [_analysis(groups=[group_bad])]}
        assert _matcher()(patterns, {}) is False, (
            f"output_colors=[{bad!r}] (bool subclass) should fail-closed"
        )


def test_returns_false_on_out_of_range_output_colors() -> None:
    # The matcher accepts 0..9 only; iter 18's per-group palette check
    # rejects 13 (transparent sentinel) here -- the matcher inspects raw
    # output colour and uses ``_is_strict_color`` which pins to 0..9.
    for bad in (-1, 10, 13, 100):
        group_bad = {
            "input_colors": [1], "output_colors": [bad],
            "top_row": 0, "top_col": 0, "cell_count": 1,
            "positions": [(0, 0)],
        }
        patterns = {"pair_analyses": [_analysis(groups=[group_bad])]}
        assert _matcher()(patterns, {}) is False, (
            f"output_colors=[{bad}] (out-of-range) should fail-closed"
        )


def test_returns_false_on_non_int_output_colors() -> None:
    for bad in (0.5, "1", None, [1]):
        group_bad = {
            "input_colors": [1], "output_colors": [bad],
            "top_row": 0, "top_col": 0, "cell_count": 1,
            "positions": [(0, 0)],
        }
        patterns = {"pair_analyses": [_analysis(groups=[group_bad])]}
        assert _matcher()(patterns, {}) is False, (
            f"output_colors=[{bad!r}] (non-int) should fail-closed"
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


def test_iter_36_refinement_implication_holds() -> None:
    # iter 36 fires ==> iter 38 fires (set bit-identical implies same
    # cardinality). Verify on a positive fixture.
    patterns = {"pair_analyses": [
        _analysis(groups=[
            _group(positions=[(0, 0)], in_colors=(1,), out_colors=(2,)),
            _group(positions=[(2, 2)], in_colors=(3,), out_colors=(4,)),
        ]),
        _analysis(groups=[
            _group(positions=[(1, 1)], in_colors=(7,), out_colors=(2,)),
            _group(positions=[(0, 2)], in_colors=(8,), out_colors=(4,)),
        ]),
    ]}
    iter36 = CONDITION_REGISTRY["change_output_colors_constant_across_pairs"]
    assert iter36(patterns, {}) is True
    assert _matcher()(patterns, {}) is True


def test_iter_36_refinement_strict_one_direction() -> None:
    # iter 38 fires where iter 36 does NOT: per-pair output-colour
    # cardinalities are equal but the SETS differ -- pair 0 outputs
    # {2, 3}, pair 1 outputs {4, 5}; both cardinality 2.
    patterns = {"pair_analyses": [
        _analysis(groups=[
            _group(positions=[(0, 0)], in_colors=(1,), out_colors=(2,)),
            _group(positions=[(2, 2)], in_colors=(1,), out_colors=(3,)),
        ]),
        _analysis(groups=[
            _group(positions=[(0, 0)], in_colors=(1,), out_colors=(4,)),
            _group(positions=[(2, 2)], in_colors=(1,), out_colors=(5,)),
        ]),
    ]}
    iter36 = CONDITION_REGISTRY["change_output_colors_constant_across_pairs"]
    assert _matcher()(patterns, {}) is True
    assert iter36(patterns, {}) is False


def test_iter_18_refinement_implication_holds() -> None:
    # iter 18 fires ==> iter 36 fires ==> iter 38 fires.
    patterns = {"pair_analyses": [
        _analysis(groups=[
            _group(positions=[(0, 0)], in_colors=(2,), out_colors=(3,)),
        ]),
        _analysis(groups=[
            _group(positions=[(1, 1)], in_colors=(4,), out_colors=(3,)),
        ]),
    ]}
    iter18 = CONDITION_REGISTRY["output_color_uniform"]
    assert iter18(patterns, {}) is True
    assert _matcher()(patterns, {}) is True


def test_iter_34_refinement_implication_holds() -> None:
    # iter 34 fires ==> iter 36 fires ==> iter 38 fires.
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


def test_independent_of_change_count_constant_iter_38_fires_alone() -> None:
    # iter 38 fires when output-colour cardinalities are equal but cell
    # counts differ. Pair 0 has one 1-cell blob; pair 1 has one 2-cell
    # blob. Both have output set {2}, cardinality 1.
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


def test_independent_of_change_count_constant_iter_32_fires_alone() -> None:
    # iter 32 fires when per-pair cell counts are equal but output-colour
    # cardinalities differ. Pair 0 has one 2-cell blob of output colour 5
    # (cardinality 1, cell count 2); pair 1 has two 1-cell blobs of
    # output colours 5 and 7 (cardinality 2, cell count 2). Same shape
    # as the docstring's worked iter-32-fires-alone fixture.
    patterns = {"pair_analyses": [
        _analysis(groups=[
            _group(positions=[(0, 0), (0, 1)],
                   in_colors=(1,), out_colors=(5,)),
        ]),
        _analysis(groups=[
            _group(positions=[(0, 0)], in_colors=(1,), out_colors=(5,)),
            _group(positions=[(2, 2)], in_colors=(1,), out_colors=(7,)),
        ]),
    ]}
    iter32 = CONDITION_REGISTRY["change_count_constant_across_pairs"]
    assert iter32(patterns, {}) is True
    assert _matcher()(patterns, {}) is False


def test_can_co_fire_with_change_count_constant_across_pairs() -> None:
    # Both fire when per-pair output cardinality AND per-pair cell count
    # both constant.
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


def test_can_co_fire_with_input_color_uniform() -> None:
    # Input K constant AND per-pair output cardinality constant -- the
    # output-side mirror of iter-37's "iter 19 co-fires" case.
    patterns = {"pair_analyses": [
        _analysis(groups=[
            _group(positions=[(0, 0)], in_colors=(7,), out_colors=(2,)),
        ]),
        _analysis(groups=[
            _group(positions=[(2, 2)], in_colors=(7,), out_colors=(3,)),
        ]),
    ]}
    icu = CONDITION_REGISTRY["input_color_uniform"]
    assert icu(patterns, {}) is True
    assert _matcher()(patterns, {}) is True


def test_iter_37_independence_iter_38_fires_alone() -> None:
    # iter 38 fires alone (per the docstring worked example): pair 0 has
    # one group ``1 -> 2`` (input card 1, output card 1); pair 1 has two
    # groups ``1 -> 2`` and ``3 -> 2`` -- per-pair input set ``{1}`` vs
    # ``{1, 3}`` cardinality differs, iter 37 rejects; per-pair output
    # set ``{2}`` on both, iter 38 fires.
    patterns = {"pair_analyses": [
        _analysis(groups=[
            _group(positions=[(0, 0)], in_colors=(1,), out_colors=(2,)),
        ]),
        _analysis(groups=[
            _group(positions=[(0, 0)], in_colors=(1,), out_colors=(2,)),
            _group(positions=[(2, 2)], in_colors=(3,), out_colors=(2,)),
        ]),
    ]}
    iter37 = CONDITION_REGISTRY[
        "change_input_color_count_constant_across_pairs"
    ]
    assert _matcher()(patterns, {}) is True
    assert iter37(patterns, {}) is False


def test_iter_37_independence_iter_37_fires_alone() -> None:
    # iter 37 fires alone (per the docstring worked example): pair 0 has
    # one group ``1 -> 2`` (input card 1, output card 1); pair 1 has two
    # groups ``1 -> 2`` and ``1 -> 3`` -- per-pair input set ``{1}`` on
    # both (iter 37 fires); per-pair output set ``{2}`` vs ``{2, 3}``
    # cardinality differs (iter 38 rejects).
    patterns = {"pair_analyses": [
        _analysis(groups=[
            _group(positions=[(0, 0)], in_colors=(1,), out_colors=(2,)),
        ]),
        _analysis(groups=[
            _group(positions=[(0, 0)], in_colors=(1,), out_colors=(2,)),
            _group(positions=[(2, 2)], in_colors=(1,), out_colors=(3,)),
        ]),
    ]}
    iter37 = CONDITION_REGISTRY[
        "change_input_color_count_constant_across_pairs"
    ]
    assert iter37(patterns, {}) is True
    assert _matcher()(patterns, {}) is False


def test_iter_37_and_iter_38_can_co_fire() -> None:
    # The docstring's "Both" territory: pair 0 has one group ``1 -> 2``
    # (input card 1, output card 1); pair 1 has one group ``3 -> 4``
    # (input card 1, output card 1). Iter 35 / 36 reject (sets differ);
    # iter 37 + iter 38 both fire.
    patterns = {"pair_analyses": [
        _analysis(groups=[
            _group(positions=[(0, 0)], in_colors=(1,), out_colors=(2,)),
        ]),
        _analysis(groups=[
            _group(positions=[(2, 2)], in_colors=(3,), out_colors=(4,)),
        ]),
    ]}
    iter35 = CONDITION_REGISTRY["change_input_colors_constant_across_pairs"]
    iter36 = CONDITION_REGISTRY["change_output_colors_constant_across_pairs"]
    iter37 = CONDITION_REGISTRY[
        "change_input_color_count_constant_across_pairs"
    ]
    assert iter35(patterns, {}) is False
    assert iter36(patterns, {}) is False
    assert iter37(patterns, {}) is True
    assert _matcher()(patterns, {}) is True


def test_can_co_fire_with_multi_group_per_pair() -> None:
    # Multi-group with the same per-pair output cardinality (2 colours
    # per pair) across pairs but different specific output colours.
    patterns = {"pair_analyses": [
        _analysis(groups=[
            _group(positions=[(0, 0)], in_colors=(1,), out_colors=(2,)),
            _group(positions=[(2, 2)], in_colors=(1,), out_colors=(3,)),
        ]),
        _analysis(groups=[
            _group(positions=[(1, 1)], in_colors=(1,), out_colors=(5,)),
            _group(positions=[(0, 2)], in_colors=(1,), out_colors=(7,)),
        ]),
    ]}
    iter28 = CONDITION_REGISTRY["multi_group_per_pair"]
    iter36 = CONDITION_REGISTRY["change_output_colors_constant_across_pairs"]
    assert iter28(patterns, {}) is True
    assert iter36(patterns, {}) is False
    assert _matcher()(patterns, {}) is True


def test_does_not_require_grid_size_preserved() -> None:
    # Colour-content matcher cares only about per-pair output-colour
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


def test_strict_mutual_exclusion_with_identity_in_practice() -> None:
    # An identity patterns dict has per-pair output cardinality 0, which
    # iter 38 rejects via the non-zero clause -- so no patterns dict
    # can fire both. This mirrors iter 32 / 30 / 37's identity rejection.
    identity_pat = {"pair_analyses": [
        _analysis(groups=[]),
        _analysis(groups=[]),
    ]}
    identity = CONDITION_REGISTRY["identity_transformation"]
    assert identity(identity_pat, {}) is True
    assert _matcher()(identity_pat, {}) is False


# ----- end-to-end with the real extractor --------------------------

def test_end_to_end_agreement_with_extract_pattern_shape() -> None:
    # Two 3x3 pairs: each pair recolours one cell of input colour 1 to
    # output colour 2. Per-pair output cardinality 1 on both. iter 38
    # should fire; iter 36 also fires (output set {2} bit-identical);
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
    iter36 = CONDITION_REGISTRY["change_output_colors_constant_across_pairs"]
    iter30 = CONDITION_REGISTRY["change_positions_constant_across_pairs"]
    assert iter30(patterns, {}) is False
    assert iter36(patterns, {}) is True
    assert _matcher()(patterns, {}) is True


def test_end_to_end_agreement_when_only_cardinality_constant() -> None:
    # The iter-38-exclusive end-to-end case: two 3x3 pairs with
    # cardinality 1 output sets but DIFFERENT output colours. Iter 36
    # rejects ({2} vs {7} differ); iter 38 fires.
    from agent.active_operators import ExtractPatternOperator  # noqa: E402

    op = ExtractPatternOperator()

    class _Grid:
        def __init__(self, raw):
            self.raw = raw
            self.height = len(raw)
            self.width = len(raw[0]) if raw else 0

    raw_in_a = [[1, 0, 0], [0, 0, 0], [0, 0, 0]]
    raw_out_a = [[2, 0, 0], [0, 0, 0], [0, 0, 0]]   # 1 -> 2
    raw_in_b = [[1, 0, 0], [0, 0, 0], [0, 0, 0]]
    raw_out_b = [[7, 0, 0], [0, 0, 0], [0, 0, 0]]   # 1 -> 7
    analysis_a = op._analyze_pair(_Grid(raw_in_a), _Grid(raw_out_a))
    analysis_b = op._analyze_pair(_Grid(raw_in_b), _Grid(raw_out_b))
    patterns = {"pair_analyses": [analysis_a, analysis_b]}
    iter36 = CONDITION_REGISTRY["change_output_colors_constant_across_pairs"]
    assert iter36(patterns, {}) is False
    assert _matcher()(patterns, {}) is True


# ──────────────────────────────────────────────────────────────────────────
# Driver.
# ──────────────────────────────────────────────────────────────────────────

def _run_all() -> int:
    tests = [
        test_registered_in_global_registry,
        test_previous_matchers_still_registered,
        test_at_least_twenty_one_distinct_matchers_registered,
        test_matcher_is_callable,
        test_returns_true_on_single_pair_single_group,
        test_returns_true_on_two_pairs_same_cardinality_same_colours,
        test_returns_true_on_two_pairs_same_cardinality_distinct_colours,
        test_returns_false_when_cardinalities_differ_across_pairs,
        test_returns_false_on_empty_pair_analyses,
        test_returns_false_on_missing_pair_analyses,
        test_returns_false_on_non_dict_patterns,
        test_returns_false_on_non_list_pair_analyses,
        test_returns_false_on_malformed_analysis_entry,
        test_returns_false_when_every_pair_has_zero_groups,
        test_returns_false_when_one_pair_has_no_groups,
        test_returns_false_on_multi_output_colors_in_group,
        test_returns_true_on_multi_input_colors_in_group,
        test_returns_false_on_empty_output_colors_list,
        test_returns_false_on_missing_output_colors,
        test_returns_false_on_non_list_output_colors,
        test_returns_false_on_bool_subclass_in_output_colors,
        test_returns_false_on_out_of_range_output_colors,
        test_returns_false_on_non_int_output_colors,
        test_returns_false_on_non_list_groups,
        test_returns_false_on_non_dict_group_entry,
        test_is_side_effect_free_on_inputs,
        test_is_deterministic_across_repeats,
        test_returns_strict_boolean_type,
        test_mutually_exclusive_with_identity_transformation,
        test_iter_36_refinement_implication_holds,
        test_iter_36_refinement_strict_one_direction,
        test_iter_18_refinement_implication_holds,
        test_iter_34_refinement_implication_holds,
        test_independent_of_change_count_constant_iter_38_fires_alone,
        test_independent_of_change_count_constant_iter_32_fires_alone,
        test_can_co_fire_with_change_count_constant_across_pairs,
        test_can_co_fire_with_input_color_uniform,
        test_iter_37_independence_iter_38_fires_alone,
        test_iter_37_independence_iter_37_fires_alone,
        test_iter_37_and_iter_38_can_co_fire,
        test_can_co_fire_with_multi_group_per_pair,
        test_does_not_require_grid_size_preserved,
        test_strict_mutual_exclusion_with_identity_in_practice,
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
