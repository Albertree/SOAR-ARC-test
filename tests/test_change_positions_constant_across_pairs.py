"""
tests/test_change_positions_constant_across_pairs.py -- exercise the
iter-30 matcher ``agent.conditions.change_positions_constant_across_pairs``.

Runs without pytest:

    python tests/test_change_positions_constant_across_pairs.py

Dependency-free, same runner style as iters
1 / 8 / 10 / 13 / 17 / 18 / 19 / 20 / 22 / 23 / 24 / 26 / 28.

The matcher is on a new axis (position-content): it names "the unioned
changed-coord set is bit-identical across every pair" -- the predicate
the iter-25 / iter-27 / iter-29 emission helpers all check privately
inside their ``_extract_*_paint_args`` defensive helpers. Naming it as
named recognition vocabulary lets the per-attempt ``fired_conditions``
list expose it, lets future translate_to_schema branches gate on it,
and provides a shared ``condition.type`` candidate the three sibling
``coloring`` rules could share -- widening the anti-unification
skeleton-match domain for the first time since iter 29.
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


MATCHER_NAME = "change_positions_constant_across_pairs"


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
        "input_colors": list(in_colors),
        "output_colors": list(out_colors),
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
    # Adjacent invariant -- iter 30 must not displace iters
    # 1 / 8 / 10 / 13 / 17 / 18 / 19 / 20 / 22 / 23 / 24 / 26 / 28.
    for prior in ("grid_size_preserved", "consistent_color_mapping",
                  "sequential_recoloring", "identity_transformation",
                  "grid_size_changed", "output_color_uniform",
                  "input_color_uniform", "output_dimensions_constant",
                  "input_dimensions_constant",
                  "single_change_group_per_pair",
                  "single_cell_change_per_pair",
                  "multi_cell_change_group_per_pair",
                  "multi_group_per_pair"):
        assert prior in CONDITION_REGISTRY, (
            f"prior matcher {prior!r} missing after iter-30 addition"
        )


def test_fourteen_distinct_matchers_registered() -> None:
    # P5 unit-monotone counter -- there must be at least 14 entries now.
    assert len(CONDITION_REGISTRY) >= 14, (
        f"expected at least 14 entries, got {len(CONDITION_REGISTRY)}: "
        f"{sorted(CONDITION_REGISTRY)}"
    )


def test_matcher_is_callable() -> None:
    fn = _matcher()
    assert callable(fn), f"registered entry is not callable: {fn!r}"


def test_returns_true_on_single_pair_single_cell() -> None:
    # A trivial fixture: one pair, one single-cell blob at (1, 1).
    patterns = {"pair_analyses": [
        _analysis(groups=[_group(positions=[(1, 1)])]),
    ]}
    assert _matcher()(patterns, {}) is True


def test_returns_true_on_two_pairs_same_single_cell_coord() -> None:
    # Iter-25 happy path: every pair has the same single coord.
    patterns = {"pair_analyses": [
        _analysis(groups=[_group(positions=[(0, 0)])]),
        _analysis(groups=[_group(positions=[(0, 0)])]),
    ]}
    assert _matcher()(patterns, {}) is True


def test_returns_true_on_two_pairs_same_multi_cell_blob() -> None:
    # Iter-27 happy path: every pair has the same multi-cell blob.
    patterns = {"pair_analyses": [
        _analysis(groups=[_group(positions=[(0, 0), (0, 1), (1, 0)])]),
        _analysis(groups=[_group(positions=[(0, 0), (0, 1), (1, 0)])]),
    ]}
    assert _matcher()(patterns, {}) is True


def test_returns_true_on_two_pairs_same_multi_blob_union() -> None:
    # Iter-29 happy path: every pair has the same union of multi-blob
    # coords (blob structure may differ within a pair -- the matcher
    # cares only about the union, not the partition).
    patterns = {"pair_analyses": [
        _analysis(groups=[
            _group(positions=[(0, 0)]),
            _group(positions=[(2, 2)]),
        ]),
        _analysis(groups=[
            _group(positions=[(0, 0)]),
            _group(positions=[(2, 2)]),
        ]),
    ]}
    assert _matcher()(patterns, {}) is True


def test_returns_true_when_blob_partition_differs_but_union_matches() -> None:
    # Pair 0 has two single-cell blobs; pair 1 has one two-cell blob
    # on the same union of coords. The matcher inspects the unioned
    # coord set, not the partition into blobs.
    patterns = {"pair_analyses": [
        _analysis(groups=[
            _group(positions=[(0, 0)]),
            _group(positions=[(0, 1)]),
        ]),
        _analysis(groups=[_group(positions=[(0, 0), (0, 1)])]),
    ]}
    assert _matcher()(patterns, {}) is True


def test_returns_true_position_order_insensitive_within_group() -> None:
    # The matcher canonicalises via sorted(); the per-group ``positions``
    # list need not be pre-sorted for cross-pair equality to hold.
    patterns = {"pair_analyses": [
        _analysis(groups=[{
            "input_colors": [0], "output_colors": [3],
            "top_row": 0, "top_col": 0, "cell_count": 3,
            "positions": [(1, 0), (0, 1), (0, 0)],
        }]),
        _analysis(groups=[{
            "input_colors": [0], "output_colors": [3],
            "top_row": 0, "top_col": 0, "cell_count": 3,
            "positions": [(0, 0), (0, 1), (1, 0)],
        }]),
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
    # Identity case: the unioned coord set is empty. The matcher
    # rejects vacuously-true matches to keep its territory disjoint
    # from iter 13's identity_transformation.
    patterns = {"pair_analyses": [
        _analysis(groups=[]),
        _analysis(groups=[]),
    ]}
    assert _matcher()(patterns, {}) is False


def test_returns_false_when_one_pair_has_no_changes() -> None:
    # Mixed: pair 0 changes (0, 0), pair 1 has zero changes. Union
    # differs (1-element vs empty) -- strict reject.
    patterns = {"pair_analyses": [
        _analysis(groups=[_group(positions=[(0, 0)])]),
        _analysis(groups=[]),
    ]}
    assert _matcher()(patterns, {}) is False


def test_returns_false_when_pair_coords_differ() -> None:
    # Two pairs both change one cell, but at different coords. Iter
    # 25's emission helper would reject this via its private cross-
    # pair check; this matcher names the same predicate.
    patterns = {"pair_analyses": [
        _analysis(groups=[_group(positions=[(0, 0)])]),
        _analysis(groups=[_group(positions=[(2, 1)])]),
    ]}
    assert _matcher()(patterns, {}) is False


def test_returns_false_when_multi_blob_union_differs_across_pairs() -> None:
    # Pair 0 unions to {(0,0), (2,2)}; pair 1 unions to {(0,0), (1,1)}.
    # Matches in one coord, not in the other.
    patterns = {"pair_analyses": [
        _analysis(groups=[
            _group(positions=[(0, 0)]),
            _group(positions=[(2, 2)]),
        ]),
        _analysis(groups=[
            _group(positions=[(0, 0)]),
            _group(positions=[(1, 1)]),
        ]),
    ]}
    assert _matcher()(patterns, {}) is False


def test_returns_false_on_missing_positions_field() -> None:
    # cell_count is set but positions is missing. iter 27 emits both
    # in lockstep; a missing positions is upstream extractor breakage.
    group_no_positions = {
        "input_colors": [0], "output_colors": [3],
        "top_row": 0, "top_col": 0, "cell_count": 1,
        # positions intentionally missing
    }
    patterns = {"pair_analyses": [_analysis(groups=[group_no_positions])]}
    assert _matcher()(patterns, {}) is False


def test_returns_false_on_non_list_positions() -> None:
    group_bad = {
        "input_colors": [0], "output_colors": [3],
        "top_row": 0, "top_col": 0, "cell_count": 1,
        "positions": "(0, 0)",  # string, not list
    }
    patterns = {"pair_analyses": [_analysis(groups=[group_bad])]}
    assert _matcher()(patterns, {}) is False


def test_returns_false_on_positions_length_mismatch() -> None:
    # positions has 2 entries but cell_count says 3. iter 27 emits
    # these in lockstep; a mismatch is corrupt input.
    group_bad = {
        "input_colors": [0], "output_colors": [3],
        "top_row": 0, "top_col": 0, "cell_count": 3,
        "positions": [(0, 0), (0, 1)],
    }
    patterns = {"pair_analyses": [_analysis(groups=[group_bad])]}
    assert _matcher()(patterns, {}) is False


def test_returns_false_on_non_tuple_position_entry() -> None:
    for bad in ("00", 42, None, {"r": 0, "c": 0}):
        group_bad = {
            "input_colors": [0], "output_colors": [3],
            "top_row": 0, "top_col": 0, "cell_count": 1,
            "positions": [bad],
        }
        patterns = {"pair_analyses": [_analysis(groups=[group_bad])]}
        assert _matcher()(patterns, {}) is False, (
            f"position={bad!r} ({type(bad).__name__}) should fail-closed"
        )


def test_returns_false_on_three_element_position() -> None:
    group_bad = {
        "input_colors": [0], "output_colors": [3],
        "top_row": 0, "top_col": 0, "cell_count": 1,
        "positions": [(0, 0, 0)],
    }
    patterns = {"pair_analyses": [_analysis(groups=[group_bad])]}
    assert _matcher()(patterns, {}) is False


def test_returns_false_on_negative_position_component() -> None:
    for bad in [(-1, 0), (0, -1), (-1, -1)]:
        group_bad = {
            "input_colors": [0], "output_colors": [3],
            "top_row": 0, "top_col": 0, "cell_count": 1,
            "positions": [bad],
        }
        patterns = {"pair_analyses": [_analysis(groups=[group_bad])]}
        assert _matcher()(patterns, {}) is False, (
            f"position={bad!r} (negative) should fail-closed"
        )


def test_returns_false_on_non_int_position_component() -> None:
    for bad in [(0.5, 0), (0, "0"), (None, 0)]:
        group_bad = {
            "input_colors": [0], "output_colors": [3],
            "top_row": 0, "top_col": 0, "cell_count": 1,
            "positions": [bad],
        }
        patterns = {"pair_analyses": [_analysis(groups=[group_bad])]}
        assert _matcher()(patterns, {}) is False, (
            f"position={bad!r} (non-int) should fail-closed"
        )


def test_returns_false_on_bool_position_component() -> None:
    # bool is an int subclass. Strict-type matchers (iters 13 / 17 /
    # 18 / 19 / 20 / 22 / 23 / 24 / 26 / 28 and validate_rule V1)
    # reject it. Mirror posture.
    for bad in [(True, 0), (0, True), (False, 0), (0, False)]:
        group_bad = {
            "input_colors": [0], "output_colors": [3],
            "top_row": 0, "top_col": 0, "cell_count": 1,
            "positions": [bad],
        }
        patterns = {"pair_analyses": [_analysis(groups=[group_bad])]}
        assert _matcher()(patterns, {}) is False, (
            f"position={bad!r} (bool component) should fail-closed"
        )


def test_returns_false_on_missing_cell_count() -> None:
    group_bad = {
        "input_colors": [0], "output_colors": [3],
        "top_row": 0, "top_col": 0,
        # cell_count intentionally missing
        "positions": [(0, 0)],
    }
    patterns = {"pair_analyses": [_analysis(groups=[group_bad])]}
    assert _matcher()(patterns, {}) is False


def test_returns_false_on_bool_cell_count() -> None:
    group_bad = {
        "input_colors": [0], "output_colors": [3],
        "top_row": 0, "top_col": 0, "cell_count": True,
        "positions": [(0, 0)],
    }
    patterns = {"pair_analyses": [_analysis(groups=[group_bad])]}
    assert _matcher()(patterns, {}) is False


def test_returns_false_on_zero_cell_count() -> None:
    group_bad = {
        "input_colors": [0], "output_colors": [3],
        "top_row": 0, "top_col": 0, "cell_count": 0,
        "positions": [],
    }
    patterns = {"pair_analyses": [_analysis(groups=[group_bad])]}
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


def test_returns_false_on_duplicate_coords_across_groups_in_one_pair() -> None:
    # Two blobs in the same pair both claim (0, 0). Connectivity is
    # corrupt -- strict refusal, mirroring iters 26 / 28 emission
    # helpers' duplicate-coord rejection.
    patterns = {"pair_analyses": [
        _analysis(groups=[
            _group(positions=[(0, 0), (0, 1)]),
            _group(positions=[(0, 0), (1, 0)]),  # (0,0) shared with previous blob
        ]),
    ]}
    assert _matcher()(patterns, {}) is False


def test_is_side_effect_free_on_inputs() -> None:
    patterns = {"pair_analyses": [
        _analysis(groups=[_group(positions=[(0, 0), (0, 1)])]),
        _analysis(groups=[_group(positions=[(0, 0), (0, 1)])]),
    ]}
    params = {"unused": 1}
    before_p = copy.deepcopy(patterns)
    before_q = copy.deepcopy(params)
    _matcher()(patterns, params)
    assert patterns == before_p, "matcher mutated patterns"
    assert params == before_q, "matcher mutated params"


def test_is_deterministic_across_repeats() -> None:
    patterns = {"pair_analyses": [
        _analysis(groups=[_group(positions=[(1, 1)])]),
        _analysis(groups=[_group(positions=[(1, 1)])]),
    ]}
    results = [_matcher()(patterns, {}) for _ in range(5)]
    assert len(set(results)) == 1, f"non-deterministic outputs: {results}"


def test_mutually_exclusive_with_identity_transformation() -> None:
    # identity requires num_groups == 0 (empty union); this matcher
    # rejects empty unions. No patterns dict can fire both.
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
            _analysis(groups=[_group(positions=[(1, 1)])]),
            _analysis(groups=[_group(positions=[(1, 1)])]),
        ],
    }
    identity = CONDITION_REGISTRY["identity_transformation"]
    assert identity(identity_pat, {}) is True
    assert _matcher()(identity_pat, {}) is False
    assert identity(paint_pat, {}) is False
    assert _matcher()(paint_pat, {}) is True


def test_can_co_fire_with_single_cell_change_per_pair() -> None:
    # The iter-25 happy-path conjunction: every pair has exactly one
    # changed cell at the same coord. Both matchers fire.
    patterns = {"pair_analyses": [
        _analysis(groups=[_group(positions=[(0, 1)])]),
        _analysis(groups=[_group(positions=[(0, 1)])]),
    ]}
    iter24 = CONDITION_REGISTRY["single_cell_change_per_pair"]
    assert iter24(patterns, {}) is True
    assert _matcher()(patterns, {}) is True


def test_can_co_fire_with_multi_cell_change_group_per_pair() -> None:
    # The iter-27 happy-path conjunction: one blob per pair with the
    # same coords across pairs.
    patterns = {"pair_analyses": [
        _analysis(groups=[_group(positions=[(0, 0), (0, 1), (1, 0)])]),
        _analysis(groups=[_group(positions=[(0, 0), (0, 1), (1, 0)])]),
    ]}
    iter26 = CONDITION_REGISTRY["multi_cell_change_group_per_pair"]
    assert iter26(patterns, {}) is True
    assert _matcher()(patterns, {}) is True


def test_can_co_fire_with_multi_group_per_pair() -> None:
    # The iter-29 happy-path conjunction: multiple blobs per pair with
    # the same unioned coords across pairs.
    patterns = {"pair_analyses": [
        _analysis(groups=[
            _group(positions=[(0, 0)]),
            _group(positions=[(2, 2)]),
        ]),
        _analysis(groups=[
            _group(positions=[(0, 0)]),
            _group(positions=[(2, 2)]),
        ]),
    ]}
    iter28 = CONDITION_REGISTRY["multi_group_per_pair"]
    assert iter28(patterns, {}) is True
    assert _matcher()(patterns, {}) is True


def test_can_co_fire_with_single_change_group_per_pair() -> None:
    # Strict refinement of iter 23's cardinality-only contract: every
    # pair has exactly one group AND the group's positions match
    # across pairs.
    patterns = {"pair_analyses": [
        _analysis(groups=[_group(positions=[(0, 0), (0, 1)])]),
        _analysis(groups=[_group(positions=[(0, 0), (0, 1)])]),
    ]}
    iter23 = CONDITION_REGISTRY["single_change_group_per_pair"]
    assert iter23(patterns, {}) is True
    assert _matcher()(patterns, {}) is True


def test_can_co_fire_with_output_color_uniform() -> None:
    # Position-content axis is orthogonal to the colour-content axis.
    patterns = {"pair_analyses": [
        _analysis(groups=[_group(positions=[(0, 0)],
                                 out_colors=(7,))]),
        _analysis(groups=[_group(positions=[(0, 0)],
                                 out_colors=(7,))]),
    ]}
    ocu = CONDITION_REGISTRY["output_color_uniform"]
    assert ocu(patterns, {}) is True
    assert _matcher()(patterns, {}) is True


def test_can_co_fire_with_input_color_uniform() -> None:
    # Position-content axis is orthogonal to the colour-content axis.
    patterns = {"pair_analyses": [
        _analysis(groups=[_group(positions=[(0, 0)],
                                 in_colors=(2,), out_colors=(3,))]),
        _analysis(groups=[_group(positions=[(0, 0)],
                                 in_colors=(2,), out_colors=(4,))]),
    ]}
    icu = CONDITION_REGISTRY["input_color_uniform"]
    assert icu(patterns, {}) is True
    assert _matcher()(patterns, {}) is True


def test_can_co_fire_with_grid_size_preserved() -> None:
    # Position-content axis is orthogonal to the dimensional axis.
    patterns = {
        "grid_size_preserved": True,
        "pair_analyses": [
            _analysis(groups=[_group(positions=[(1, 1)])]),
            _analysis(groups=[_group(positions=[(1, 1)])]),
        ],
    }
    gsp = CONDITION_REGISTRY["grid_size_preserved"]
    assert _matcher()(patterns, {}) is True
    assert gsp(patterns, {}) is True


def test_does_not_require_grid_size_preserved() -> None:
    # Position-content matcher cares only about changed coords. It
    # CAN fire on dimension-changed pairs (the overlap-region changes
    # have constant coords across pairs).
    patterns = {"pair_analyses": [
        _analysis(groups=[_group(positions=[(0, 0)])],
                  output_height=5, output_width=5, size_match=False),
        _analysis(groups=[_group(positions=[(0, 0)])],
                  output_height=5, output_width=5, size_match=False),
    ]}
    gsp = CONDITION_REGISTRY["grid_size_preserved"]
    assert _matcher()(patterns, {}) is True
    assert gsp(patterns, {}) is False


def test_end_to_end_agreement_with_extract_pattern_shape() -> None:
    # The shape ExtractPatternOperator._analyze_pair emits on two
    # identical 3x3 grids with the same single-cell change: positions
    # field is populated and the matcher fires.
    from agent.active_operators import ExtractPatternOperator  # noqa: E402

    op = ExtractPatternOperator()

    class _Grid:
        def __init__(self, raw):
            self.raw = raw
            self.height = len(raw)
            self.width = len(raw[0]) if raw else 0

    raw_in = [
        [0, 0, 0],
        [0, 0, 0],
        [0, 0, 0],
    ]
    raw_out = [
        [0, 0, 0],
        [0, 3, 0],
        [0, 0, 0],
    ]
    analysis_a = op._analyze_pair(_Grid(raw_in), _Grid(raw_out))
    analysis_b = op._analyze_pair(_Grid(raw_in), _Grid(raw_out))
    patterns = {"pair_analyses": [analysis_a, analysis_b]}
    assert _matcher()(patterns, {}) is True


def test_end_to_end_disagreement_when_coords_differ() -> None:
    # Two pairs change different single cells. iter 25's emission
    # helper would refuse to mint a literal-coord rule here; this
    # matcher refuses too.
    from agent.active_operators import ExtractPatternOperator  # noqa: E402

    op = ExtractPatternOperator()

    class _Grid:
        def __init__(self, raw):
            self.raw = raw
            self.height = len(raw)
            self.width = len(raw[0]) if raw else 0

    raw_in = [[0, 0, 0], [0, 0, 0], [0, 0, 0]]
    raw_out_a = [[3, 0, 0], [0, 0, 0], [0, 0, 0]]   # changes (0, 0)
    raw_out_b = [[0, 0, 0], [0, 0, 0], [0, 0, 3]]   # changes (2, 2)
    analysis_a = op._analyze_pair(_Grid(raw_in), _Grid(raw_out_a))
    analysis_b = op._analyze_pair(_Grid(raw_in), _Grid(raw_out_b))
    patterns = {"pair_analyses": [analysis_a, analysis_b]}
    assert _matcher()(patterns, {}) is False


def test_returned_value_is_boolean_not_truthy() -> None:
    pos_pat = {"pair_analyses": [
        _analysis(groups=[_group(positions=[(1, 1)])]),
        _analysis(groups=[_group(positions=[(1, 1)])]),
    ]}
    neg_pat = {"pair_analyses": [
        _analysis(groups=[_group(positions=[(0, 0)])]),
        _analysis(groups=[_group(positions=[(2, 2)])]),
    ]}
    pos = _matcher()(pos_pat, {})
    neg = _matcher()(neg_pat, {})
    assert pos is True, f"expected literal True, got {pos!r}"
    assert neg is False, f"expected literal False, got {neg!r}"


# ----------------------------------------------------------------------
# Driver.
# ----------------------------------------------------------------------

def _run_all() -> int:
    tests = [
        test_registered_in_global_registry,
        test_previous_matchers_still_registered,
        test_fourteen_distinct_matchers_registered,
        test_matcher_is_callable,
        test_returns_true_on_single_pair_single_cell,
        test_returns_true_on_two_pairs_same_single_cell_coord,
        test_returns_true_on_two_pairs_same_multi_cell_blob,
        test_returns_true_on_two_pairs_same_multi_blob_union,
        test_returns_true_when_blob_partition_differs_but_union_matches,
        test_returns_true_position_order_insensitive_within_group,
        test_returns_false_on_empty_pair_analyses,
        test_returns_false_on_missing_pair_analyses,
        test_returns_false_on_non_dict_patterns,
        test_returns_false_on_non_list_pair_analyses,
        test_returns_false_on_malformed_analysis_entry,
        test_returns_false_when_every_pair_has_zero_groups,
        test_returns_false_when_one_pair_has_no_changes,
        test_returns_false_when_pair_coords_differ,
        test_returns_false_when_multi_blob_union_differs_across_pairs,
        test_returns_false_on_missing_positions_field,
        test_returns_false_on_non_list_positions,
        test_returns_false_on_positions_length_mismatch,
        test_returns_false_on_non_tuple_position_entry,
        test_returns_false_on_three_element_position,
        test_returns_false_on_negative_position_component,
        test_returns_false_on_non_int_position_component,
        test_returns_false_on_bool_position_component,
        test_returns_false_on_missing_cell_count,
        test_returns_false_on_bool_cell_count,
        test_returns_false_on_zero_cell_count,
        test_returns_false_on_non_list_groups,
        test_returns_false_on_non_dict_group_entry,
        test_returns_false_on_duplicate_coords_across_groups_in_one_pair,
        test_is_side_effect_free_on_inputs,
        test_is_deterministic_across_repeats,
        test_mutually_exclusive_with_identity_transformation,
        test_can_co_fire_with_single_cell_change_per_pair,
        test_can_co_fire_with_multi_cell_change_group_per_pair,
        test_can_co_fire_with_multi_group_per_pair,
        test_can_co_fire_with_single_change_group_per_pair,
        test_can_co_fire_with_output_color_uniform,
        test_can_co_fire_with_input_color_uniform,
        test_can_co_fire_with_grid_size_preserved,
        test_does_not_require_grid_size_preserved,
        test_end_to_end_agreement_with_extract_pattern_shape,
        test_end_to_end_disagreement_when_coords_differ,
        test_returned_value_is_boolean_not_truthy,
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
    n = _run_all()
    sys.exit(1 if n else 0)
