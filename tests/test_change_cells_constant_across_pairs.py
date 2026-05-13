"""
tests/test_change_cells_constant_across_pairs.py -- exercise the iter-41
matcher ``agent.conditions.change_cells_constant_across_pairs``.

Runs without pytest:

    python tests/test_change_cells_constant_across_pairs.py

Dependency-free, same runner style as iters
1 / 8 / 10 / 13 / 17 / 18 / 19 / 20 / 22 / 23 / 24 / 26 / 28 / 30 / 32 /
33 / 34 / 35 / 36 / 37 / 38 / 39 / 40.

The matcher is on the cell-tuple-content axis: per-pair set of
``(row, col, input_colour, output_colour)`` tuples (the flat union over
all change groups of a pair) is bit-identical across every pair.
STRICT REFINEMENT of iter 30 (position set) AND iter 34 ((ic, oc) set):
this matcher fires => iter 30 fires AND iter 34 fires, but not vice
versa (the (r, c) -> (ic, oc) assignment can permute while the
marginals match -- the worked counter-example in the matcher
docstring).
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


MATCHER_NAME = "change_cells_constant_across_pairs"


def _matcher():
    return CONDITION_REGISTRY[MATCHER_NAME]


def _group(*, positions, in_colors=(0,), out_colors=(3,)):
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
                  "change_group_count_constant_across_pairs",
                  "change_color_mapping_count_constant_across_pairs"):
        assert prior in CONDITION_REGISTRY, (
            f"prior matcher {prior!r} missing after iter-41 addition"
        )


def test_at_least_twenty_four_distinct_matchers_registered() -> None:
    # P5 unit-monotone counter -- iter 41 lifts the count from 23 to 24.
    assert len(CONDITION_REGISTRY) >= 24, (
        f"expected at least 24 entries, got {len(CONDITION_REGISTRY)}: "
        f"{sorted(CONDITION_REGISTRY)}"
    )


def test_matcher_is_callable() -> None:
    fn = _matcher()
    assert callable(fn), f"registered entry is not callable: {fn!r}"


# ----- positive fixtures -------------------------------------------------

def test_returns_true_on_single_pair_single_group() -> None:
    # One pair with one cell -- per-pair cell-tuple set has 1 entry,
    # trivially "constant" across the one pair.
    patterns = {"pair_analyses": [
        _analysis(groups=[
            _group(positions=[(1, 1)], in_colors=(1,), out_colors=(2,)),
        ]),
    ]}
    assert _matcher()(patterns, {}) is True


def test_returns_true_on_two_pairs_identical_per_cell() -> None:
    # Two pairs with bit-identical (r, c, ic, oc) sets {(0, 0, 1, 2)}.
    patterns = {"pair_analyses": [
        _analysis(groups=[
            _group(positions=[(0, 0)], in_colors=(1,), out_colors=(2,)),
        ]),
        _analysis(groups=[
            _group(positions=[(0, 0)], in_colors=(1,), out_colors=(2,)),
        ]),
    ]}
    assert _matcher()(patterns, {}) is True


def test_returns_true_on_multi_cell_identical_per_cell() -> None:
    # Both pairs have the same 2-cell set {(0, 0, 1, 2), (1, 1, 3, 4)}.
    patterns = {"pair_analyses": [
        _analysis(groups=[
            _group(positions=[(0, 0)], in_colors=(1,), out_colors=(2,)),
            _group(positions=[(1, 1)], in_colors=(3,), out_colors=(4,)),
        ]),
        _analysis(groups=[
            _group(positions=[(0, 0)], in_colors=(1,), out_colors=(2,)),
            _group(positions=[(1, 1)], in_colors=(3,), out_colors=(4,)),
        ]),
    ]}
    assert _matcher()(patterns, {}) is True


def test_returns_true_on_same_blob_with_uniform_colors() -> None:
    # A 2-cell blob with uniform input 1 and uniform output 2. Both pairs
    # have the same blob.
    patterns = {"pair_analyses": [
        _analysis(groups=[
            _group(positions=[(0, 0), (0, 1)], in_colors=(1,), out_colors=(2,)),
        ]),
        _analysis(groups=[
            _group(positions=[(0, 0), (0, 1)], in_colors=(1,), out_colors=(2,)),
        ]),
    ]}
    assert _matcher()(patterns, {}) is True


# ----- the iter-41 strict-refinement counter-example --------------------

def test_returns_false_when_positions_and_mappings_match_but_assignment_permutes() -> None:
    """The defining counter-example: position SET and (ic, oc) SET both
    bit-identical across pairs, but the per-cell ASSIGNMENT differs.
    Iter 30 fires, iter 34 fires, this matcher rejects.

    Pair 0: (0, 0): 1->2, (1, 1): 3->4    cell-tuple set
            {(0, 0, 1, 2), (1, 1, 3, 4)}
    Pair 1: (0, 0): 3->4, (1, 1): 1->2    cell-tuple set
            {(0, 0, 3, 4), (1, 1, 1, 2)}
    """
    patterns = {"pair_analyses": [
        _analysis(groups=[
            _group(positions=[(0, 0)], in_colors=(1,), out_colors=(2,)),
            _group(positions=[(1, 1)], in_colors=(3,), out_colors=(4,)),
        ]),
        _analysis(groups=[
            _group(positions=[(0, 0)], in_colors=(3,), out_colors=(4,)),
            _group(positions=[(1, 1)], in_colors=(1,), out_colors=(2,)),
        ]),
    ]}
    iter30 = CONDITION_REGISTRY["change_positions_constant_across_pairs"]
    iter34 = CONDITION_REGISTRY["change_colors_constant_across_pairs"]
    assert iter30(patterns, {}) is True
    assert iter34(patterns, {}) is True
    assert _matcher()(patterns, {}) is False


# ----- negative fixtures -------------------------------------------------

def test_returns_false_when_positions_differ() -> None:
    # Same (ic, oc) on both pairs but at different positions.
    patterns = {"pair_analyses": [
        _analysis(groups=[
            _group(positions=[(0, 0)], in_colors=(1,), out_colors=(2,)),
        ]),
        _analysis(groups=[
            _group(positions=[(2, 2)], in_colors=(1,), out_colors=(2,)),
        ]),
    ]}
    assert _matcher()(patterns, {}) is False


def test_returns_false_when_mappings_differ_at_same_positions() -> None:
    # Same positions on both pairs but different (ic, oc).
    patterns = {"pair_analyses": [
        _analysis(groups=[
            _group(positions=[(0, 0)], in_colors=(1,), out_colors=(2,)),
        ]),
        _analysis(groups=[
            _group(positions=[(0, 0)], in_colors=(3,), out_colors=(4,)),
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
    # Identity case: per-pair cell-tuple set is empty. The matcher
    # rejects vacuously-empty matches to keep its territory disjoint
    # from iter 13's identity_transformation.
    patterns = {"pair_analyses": [
        _analysis(groups=[]),
        _analysis(groups=[]),
    ]}
    assert _matcher()(patterns, {}) is False


def test_returns_false_when_one_pair_has_no_groups() -> None:
    # Pair 0 has changes; pair 1 has none. Strict reject -- non-empty
    # required on every pair.
    patterns = {"pair_analyses": [
        _analysis(groups=[
            _group(positions=[(0, 0)], in_colors=(1,), out_colors=(2,)),
        ]),
        _analysis(groups=[]),
    ]}
    assert _matcher()(patterns, {}) is False


def test_returns_false_on_multi_input_colors_in_group() -> None:
    # A group with two input colours has an ill-defined (ic, oc) pair.
    group_bad = {
        "input_colors": [1, 2], "output_colors": [3],
        "top_row": 0, "top_col": 0, "cell_count": 2,
        "positions": [(0, 0), (0, 1)],
    }
    patterns = {"pair_analyses": [_analysis(groups=[group_bad])]}
    assert _matcher()(patterns, {}) is False


def test_returns_false_on_multi_output_colors_in_group() -> None:
    group_bad = {
        "input_colors": [1], "output_colors": [3, 4],
        "top_row": 0, "top_col": 0, "cell_count": 2,
        "positions": [(0, 0), (0, 1)],
    }
    patterns = {"pair_analyses": [_analysis(groups=[group_bad])]}
    assert _matcher()(patterns, {}) is False


def test_returns_false_on_empty_colors_lists() -> None:
    for field in ("input_colors", "output_colors"):
        group_bad = {
            "input_colors": [1], "output_colors": [3],
            "top_row": 0, "top_col": 0, "cell_count": 1,
            "positions": [(0, 0)],
        }
        group_bad[field] = []
        patterns = {"pair_analyses": [_analysis(groups=[group_bad])]}
        assert _matcher()(patterns, {}) is False, (
            f"empty {field} should fail-closed"
        )


def test_returns_false_on_missing_colors_lists() -> None:
    for field in ("input_colors", "output_colors"):
        group_bad = {
            "input_colors": [1], "output_colors": [3],
            "top_row": 0, "top_col": 0, "cell_count": 1,
            "positions": [(0, 0)],
        }
        del group_bad[field]
        patterns = {"pair_analyses": [_analysis(groups=[group_bad])]}
        assert _matcher()(patterns, {}) is False, (
            f"missing {field} should fail-closed"
        )


def test_returns_false_on_bool_subclass_in_colors() -> None:
    for bad in (True, False):
        for field in ("input_colors", "output_colors"):
            group_bad = {
                "input_colors": [1], "output_colors": [3],
                "top_row": 0, "top_col": 0, "cell_count": 1,
                "positions": [(0, 0)],
            }
            group_bad[field] = [bad]
            patterns = {"pair_analyses": [_analysis(groups=[group_bad])]}
            assert _matcher()(patterns, {}) is False, (
                f"bool {bad!r} in {field} should fail-closed"
            )


def test_returns_false_on_out_of_range_colors() -> None:
    for bad in (-1, 10, 13, 100):
        for field in ("input_colors", "output_colors"):
            group_bad = {
                "input_colors": [1], "output_colors": [3],
                "top_row": 0, "top_col": 0, "cell_count": 1,
                "positions": [(0, 0)],
            }
            group_bad[field] = [bad]
            patterns = {"pair_analyses": [_analysis(groups=[group_bad])]}
            assert _matcher()(patterns, {}) is False, (
                f"out-of-range colour {bad} in {field} should fail-closed"
            )


def test_returns_false_on_missing_positions_field() -> None:
    group_bad = {
        "input_colors": [1], "output_colors": [3],
        "top_row": 0, "top_col": 0, "cell_count": 1,
    }
    patterns = {"pair_analyses": [_analysis(groups=[group_bad])]}
    assert _matcher()(patterns, {}) is False


def test_returns_false_on_non_list_positions() -> None:
    for bad in ("string", 42, None, {"k": "v"}):
        group_bad = {
            "input_colors": [1], "output_colors": [3],
            "top_row": 0, "top_col": 0, "cell_count": 1,
            "positions": bad,
        }
        patterns = {"pair_analyses": [_analysis(groups=[group_bad])]}
        assert _matcher()(patterns, {}) is False, (
            f"positions={bad!r} (non-list) should fail-closed"
        )


def test_returns_false_on_position_cell_count_mismatch() -> None:
    # cell_count claims 2, positions has 1 entry. Lockstep violation.
    group_bad = {
        "input_colors": [1], "output_colors": [3],
        "top_row": 0, "top_col": 0, "cell_count": 2,
        "positions": [(0, 0)],
    }
    patterns = {"pair_analyses": [_analysis(groups=[group_bad])]}
    assert _matcher()(patterns, {}) is False


def test_returns_false_on_bool_cell_count() -> None:
    group_bad = {
        "input_colors": [1], "output_colors": [3],
        "top_row": 0, "top_col": 0, "cell_count": True,
        "positions": [(0, 0)],
    }
    patterns = {"pair_analyses": [_analysis(groups=[group_bad])]}
    assert _matcher()(patterns, {}) is False


def test_returns_false_on_zero_cell_count() -> None:
    group_bad = {
        "input_colors": [1], "output_colors": [3],
        "top_row": 0, "top_col": 0, "cell_count": 0,
        "positions": [],
    }
    patterns = {"pair_analyses": [_analysis(groups=[group_bad])]}
    assert _matcher()(patterns, {}) is False


def test_returns_false_on_malformed_position_entry() -> None:
    # Length != 2.
    group_bad = {
        "input_colors": [1], "output_colors": [3],
        "top_row": 0, "top_col": 0, "cell_count": 1,
        "positions": [(0, 0, 0)],
    }
    patterns = {"pair_analyses": [_analysis(groups=[group_bad])]}
    assert _matcher()(patterns, {}) is False


def test_returns_false_on_negative_coordinates() -> None:
    for bad in (-1, -100):
        group_bad = {
            "input_colors": [1], "output_colors": [3],
            "top_row": bad, "top_col": 0, "cell_count": 1,
            "positions": [(bad, 0)],
        }
        patterns = {"pair_analyses": [_analysis(groups=[group_bad])]}
        assert _matcher()(patterns, {}) is False, (
            f"negative coord {bad} should fail-closed"
        )


def test_returns_false_on_bool_subclass_in_coordinates() -> None:
    for bad in (True, False):
        group_bad = {
            "input_colors": [1], "output_colors": [3],
            "top_row": 0, "top_col": 0, "cell_count": 1,
            "positions": [(bad, 0)],
        }
        patterns = {"pair_analyses": [_analysis(groups=[group_bad])]}
        assert _matcher()(patterns, {}) is False, (
            f"bool coord {bad!r} should fail-closed"
        )


def test_returns_false_on_duplicate_coord_across_groups() -> None:
    # Two blobs in same pair claim cell (0, 0). Corrupt connectivity.
    patterns = {"pair_analyses": [
        _analysis(groups=[
            _group(positions=[(0, 0)], in_colors=(1,), out_colors=(2,)),
            _group(positions=[(0, 0)], in_colors=(3,), out_colors=(4,)),
        ]),
    ]}
    assert _matcher()(patterns, {}) is False


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


# ----- side-effect / determinism / type guarantees -----------------------

def test_is_side_effect_free_on_inputs() -> None:
    patterns = {"pair_analyses": [
        _analysis(groups=[
            _group(positions=[(0, 0)], in_colors=(1,), out_colors=(2,)),
        ]),
        _analysis(groups=[
            _group(positions=[(0, 0)], in_colors=(1,), out_colors=(2,)),
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
            _group(positions=[(0, 0)], in_colors=(1,), out_colors=(2,)),
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
            _group(positions=[(0, 0)], in_colors=(1,), out_colors=(2,)),
        ]),
    ]}
    result = _matcher()(patterns, {})
    assert result is True or result is False, (
        f"matcher did not return strict bool: {result!r} "
        f"(type {type(result).__name__})"
    )


# ----- mutual-exclusion / refinement-chain tests -------------------------

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
                _group(positions=[(1, 1)], in_colors=(1,), out_colors=(2,)),
            ]),
        ],
    }
    identity = CONDITION_REGISTRY["identity_transformation"]
    assert identity(identity_pat, {}) is True
    assert _matcher()(identity_pat, {}) is False
    assert identity(paint_pat, {}) is False
    assert _matcher()(paint_pat, {}) is True


def test_strict_refinement_of_iter_30_implication_holds() -> None:
    # this matcher fires => iter 30 fires (per-cell set bit-identity
    # implies position SET bit-identity).
    patterns = {"pair_analyses": [
        _analysis(groups=[
            _group(positions=[(0, 0)], in_colors=(1,), out_colors=(2,)),
            _group(positions=[(2, 2)], in_colors=(3,), out_colors=(4,)),
        ]),
        _analysis(groups=[
            _group(positions=[(0, 0)], in_colors=(1,), out_colors=(2,)),
            _group(positions=[(2, 2)], in_colors=(3,), out_colors=(4,)),
        ]),
    ]}
    iter30 = CONDITION_REGISTRY["change_positions_constant_across_pairs"]
    assert _matcher()(patterns, {}) is True
    assert iter30(patterns, {}) is True


def test_strict_refinement_of_iter_34_implication_holds() -> None:
    # this matcher fires => iter 34 fires (per-cell set bit-identity
    # implies per-pair (ic, oc) SET bit-identity).
    patterns = {"pair_analyses": [
        _analysis(groups=[
            _group(positions=[(0, 0)], in_colors=(1,), out_colors=(2,)),
        ]),
        _analysis(groups=[
            _group(positions=[(0, 0)], in_colors=(1,), out_colors=(2,)),
        ]),
    ]}
    iter34 = CONDITION_REGISTRY["change_colors_constant_across_pairs"]
    assert _matcher()(patterns, {}) is True
    assert iter34(patterns, {}) is True


def test_strict_refinement_of_iter_30_strict_one_direction() -> None:
    # iter 30 fires where this matcher does NOT: positions match but
    # mappings at those positions differ.
    patterns = {"pair_analyses": [
        _analysis(groups=[
            _group(positions=[(0, 0)], in_colors=(1,), out_colors=(2,)),
        ]),
        _analysis(groups=[
            _group(positions=[(0, 0)], in_colors=(3,), out_colors=(4,)),
        ]),
    ]}
    iter30 = CONDITION_REGISTRY["change_positions_constant_across_pairs"]
    assert iter30(patterns, {}) is True
    assert _matcher()(patterns, {}) is False


def test_strict_refinement_of_iter_34_strict_one_direction() -> None:
    # iter 34 fires where this matcher does NOT: (ic, oc) sets match
    # but positions differ.
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
    assert _matcher()(patterns, {}) is False


def test_orthogonal_to_iter_39_group_count_axis() -> None:
    # Group partition can differ while per-cell set matches. Pair 0 has
    # one 2-cell blob {1->2 at (0,0), (0,1)}; pair 1 has two 1-cell
    # blobs {1->2 at (0,0), 1->2 at (0,1)}. Per-cell set
    # {(0, 0, 1, 2), (0, 1, 1, 2)} identical; group counts 1 vs 2.
    patterns = {"pair_analyses": [
        _analysis(groups=[
            _group(positions=[(0, 0), (0, 1)],
                   in_colors=(1,), out_colors=(2,)),
        ]),
        _analysis(groups=[
            _group(positions=[(0, 0)], in_colors=(1,), out_colors=(2,)),
            _group(positions=[(0, 1)], in_colors=(1,), out_colors=(2,)),
        ]),
    ]}
    iter39 = CONDITION_REGISTRY["change_group_count_constant_across_pairs"]
    assert _matcher()(patterns, {}) is True
    assert iter39(patterns, {}) is False


def test_co_fires_with_change_count_constant_across_pairs() -> None:
    # Per-cell bit-identity implies same per-pair cell count (set
    # equality implies cardinality equality). Iter 32 should always
    # fire when this matcher fires.
    patterns = {"pair_analyses": [
        _analysis(groups=[
            _group(positions=[(0, 0)], in_colors=(1,), out_colors=(2,)),
            _group(positions=[(2, 2)], in_colors=(3,), out_colors=(4,)),
        ]),
        _analysis(groups=[
            _group(positions=[(0, 0)], in_colors=(1,), out_colors=(2,)),
            _group(positions=[(2, 2)], in_colors=(3,), out_colors=(4,)),
        ]),
    ]}
    iter32 = CONDITION_REGISTRY["change_count_constant_across_pairs"]
    assert _matcher()(patterns, {}) is True
    assert iter32(patterns, {}) is True


def test_co_fires_with_output_color_uniform() -> None:
    # Per-cell set identical AND every cell paints the same K.
    patterns = {"pair_analyses": [
        _analysis(groups=[
            _group(positions=[(0, 0)], in_colors=(1,), out_colors=(7,)),
            _group(positions=[(1, 1)], in_colors=(3,), out_colors=(7,)),
        ]),
        _analysis(groups=[
            _group(positions=[(0, 0)], in_colors=(1,), out_colors=(7,)),
            _group(positions=[(1, 1)], in_colors=(3,), out_colors=(7,)),
        ]),
    ]}
    ocu = CONDITION_REGISTRY["output_color_uniform"]
    assert ocu(patterns, {}) is True
    assert _matcher()(patterns, {}) is True


def test_does_not_require_grid_size_preserved() -> None:
    # Cell-content matcher cares only about per-cell (r, c, ic, oc)
    # tuples. CAN fire on dimension-changed pairs as long as the cell
    # set agrees.
    patterns = {"pair_analyses": [
        _analysis(groups=[
            _group(positions=[(0, 0)], in_colors=(1,), out_colors=(2,)),
        ], output_height=5, output_width=5, size_match=False),
        _analysis(groups=[
            _group(positions=[(0, 0)], in_colors=(1,), out_colors=(2,)),
        ], output_height=7, output_width=7, size_match=False),
    ]}
    gsp = CONDITION_REGISTRY["grid_size_preserved"]
    assert _matcher()(patterns, {}) is True
    assert gsp(patterns, {}) is False


# ----- end-to-end with the real extractor --------------------------------

def test_end_to_end_agreement_with_extract_pattern_shape() -> None:
    # Two 3x3 pairs: both recolour (0, 0) from 1 to 2, no other changes.
    # The per-cell set {(0, 0, 1, 2)} is bit-identical across pairs.
    from agent.active_operators import ExtractPatternOperator  # noqa: E402

    op = ExtractPatternOperator()

    class _Grid:
        def __init__(self, raw):
            self.raw = raw
            self.height = len(raw)
            self.width = len(raw[0]) if raw else 0

    raw_in = [[1, 0, 0], [0, 0, 0], [0, 0, 0]]
    raw_out = [[2, 0, 0], [0, 0, 0], [0, 0, 0]]
    analysis_a = op._analyze_pair(_Grid(raw_in), _Grid(raw_out))
    analysis_b = op._analyze_pair(_Grid(raw_in), _Grid(raw_out))
    patterns = {"pair_analyses": [analysis_a, analysis_b]}
    iter30 = CONDITION_REGISTRY["change_positions_constant_across_pairs"]
    iter34 = CONDITION_REGISTRY["change_colors_constant_across_pairs"]
    assert iter30(patterns, {}) is True
    assert iter34(patterns, {}) is True
    assert _matcher()(patterns, {}) is True


def test_end_to_end_rejects_when_assignment_permutes() -> None:
    # Two 3x3 pairs with the position SET {(0, 0), (1, 1)} on both AND
    # (ic, oc) SET {(1, 2), (3, 4)} on both, but the (r, c) -> (ic, oc)
    # ASSIGNMENT differs. The iter-41 counter-example expressed via
    # the real extractor.
    from agent.active_operators import ExtractPatternOperator  # noqa: E402

    op = ExtractPatternOperator()

    class _Grid:
        def __init__(self, raw):
            self.raw = raw
            self.height = len(raw)
            self.width = len(raw[0]) if raw else 0

    raw_in_a = [[1, 0, 0], [0, 3, 0], [0, 0, 0]]
    raw_out_a = [[2, 0, 0], [0, 4, 0], [0, 0, 0]]  # (0,0):1->2, (1,1):3->4
    raw_in_b = [[3, 0, 0], [0, 1, 0], [0, 0, 0]]
    raw_out_b = [[4, 0, 0], [0, 2, 0], [0, 0, 0]]  # (0,0):3->4, (1,1):1->2
    analysis_a = op._analyze_pair(_Grid(raw_in_a), _Grid(raw_out_a))
    analysis_b = op._analyze_pair(_Grid(raw_in_b), _Grid(raw_out_b))
    patterns = {"pair_analyses": [analysis_a, analysis_b]}
    iter30 = CONDITION_REGISTRY["change_positions_constant_across_pairs"]
    iter34 = CONDITION_REGISTRY["change_colors_constant_across_pairs"]
    assert iter30(patterns, {}) is True
    assert iter34(patterns, {}) is True
    assert _matcher()(patterns, {}) is False


# ----------------------------------------------------------------------
# Driver.
# ----------------------------------------------------------------------

def _run_all() -> int:
    tests = [
        test_registered_in_global_registry,
        test_previous_matchers_still_registered,
        test_at_least_twenty_four_distinct_matchers_registered,
        test_matcher_is_callable,
        test_returns_true_on_single_pair_single_group,
        test_returns_true_on_two_pairs_identical_per_cell,
        test_returns_true_on_multi_cell_identical_per_cell,
        test_returns_true_on_same_blob_with_uniform_colors,
        test_returns_false_when_positions_and_mappings_match_but_assignment_permutes,
        test_returns_false_when_positions_differ,
        test_returns_false_when_mappings_differ_at_same_positions,
        test_returns_false_on_empty_pair_analyses,
        test_returns_false_on_missing_pair_analyses,
        test_returns_false_on_non_dict_patterns,
        test_returns_false_on_non_list_pair_analyses,
        test_returns_false_on_malformed_analysis_entry,
        test_returns_false_when_every_pair_has_zero_groups,
        test_returns_false_when_one_pair_has_no_groups,
        test_returns_false_on_multi_input_colors_in_group,
        test_returns_false_on_multi_output_colors_in_group,
        test_returns_false_on_empty_colors_lists,
        test_returns_false_on_missing_colors_lists,
        test_returns_false_on_bool_subclass_in_colors,
        test_returns_false_on_out_of_range_colors,
        test_returns_false_on_missing_positions_field,
        test_returns_false_on_non_list_positions,
        test_returns_false_on_position_cell_count_mismatch,
        test_returns_false_on_bool_cell_count,
        test_returns_false_on_zero_cell_count,
        test_returns_false_on_malformed_position_entry,
        test_returns_false_on_negative_coordinates,
        test_returns_false_on_bool_subclass_in_coordinates,
        test_returns_false_on_duplicate_coord_across_groups,
        test_returns_false_on_non_list_groups,
        test_returns_false_on_non_dict_group_entry,
        test_is_side_effect_free_on_inputs,
        test_is_deterministic_across_repeats,
        test_returns_strict_boolean_type,
        test_mutually_exclusive_with_identity_transformation,
        test_strict_refinement_of_iter_30_implication_holds,
        test_strict_refinement_of_iter_34_implication_holds,
        test_strict_refinement_of_iter_30_strict_one_direction,
        test_strict_refinement_of_iter_34_strict_one_direction,
        test_orthogonal_to_iter_39_group_count_axis,
        test_co_fires_with_change_count_constant_across_pairs,
        test_co_fires_with_output_color_uniform,
        test_does_not_require_grid_size_preserved,
        test_end_to_end_agreement_with_extract_pattern_shape,
        test_end_to_end_rejects_when_assignment_permutes,
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
