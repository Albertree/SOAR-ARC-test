"""
tests/test_input_output_group_palette_equal_and_constant_across_pairs.py
-- exercise the iter-996 matcher
``agent.conditions.input_output_group_palette_equal_and_constant_across_pairs``
(new in this iter).

Pins the matcher's contract per
``agent/conditions/input_output_group_palette_equal_and_constant_across_pairs.py``
docstring: every change group of every example pair has
``frozenset(group["input_colors"]) == frozenset(group["output_colors"])``
AND that single shared per-group set is bit-identical across every
group across every pair. Recognition vocabulary axis: the per-group
projection of iter 991's whole-grid
``input_output_palette_equal_and_constant_across_pairs`` AND the
natural conjunction-handle of iter 994
(``input_group_palette_constant_across_pairs``) AND iter 995
(``output_group_palette_constant_across_pairs``) AND the additional
per-blob cross-side equality clause.

Runs without pytest:

    python tests/test_input_output_group_palette_equal_and_constant_across_pairs.py

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


MATCHER_NAME = "input_output_group_palette_equal_and_constant_across_pairs"


def _matcher():
    return CONDITION_REGISTRY[MATCHER_NAME]


def _group(palette, **overrides):
    """A group_analysis shaped like ``_analyze_pair``'s emit (iter-1
    schema), defaulting input_colors == output_colors == palette
    (the matcher's typical positive territory). Override individual
    fields via overrides to test negative cases."""
    base = {
        "input_colors": list(palette),
        "output_colors": list(palette),
        "top_row": 0,
        "top_col": 0,
        "cell_count": max(len(palette), 1),
        "positions": [(0, 0)],
    }
    base.update(overrides)
    return base


def _pair(groups, input_palette=None, output_palette=None, **overrides):
    """A pair_analysis with the supplied ``groups`` list and the iter-184
    palette fields. Defaults to a 3x3 size-preserving pair."""
    if input_palette is None:
        input_palette = [0, 1, 2]
    if output_palette is None:
        output_palette = [0, 1, 2]
    total_changes = sum(g.get("cell_count", 1) for g in groups)
    base = {
        "input_height": 3,
        "input_width": 3,
        "output_height": 3,
        "output_width": 3,
        "size_match": True,
        "total_changes": total_changes,
        "num_groups": len(groups),
        "groups": list(groups),
        "input_palette": list(input_palette),
        "output_palette": list(output_palette),
    }
    base.update(overrides)
    return base


# ──────────────────────────────────────────────────────────────────────────
# Smoke / membership.
# ──────────────────────────────────────────────────────────────────────────

def test_registered_in_global_registry() -> None:
    assert MATCHER_NAME in CONDITION_REGISTRY, (
        f"{MATCHER_NAME!r} not registered; got {sorted(CONDITION_REGISTRY)}"
    )


def test_matcher_is_callable() -> None:
    fn = _matcher()
    assert callable(fn), f"registered entry is not callable: {fn!r}"


def test_p5_at_least_90() -> None:
    # This matcher brings the registry to >= 90 (P5 monotone vs iter 995's
    # 89).
    assert len(CONDITION_REGISTRY) >= 90, (
        f"expected >= 90 matchers post-iter-996; got {len(CONDITION_REGISTRY)}"
    )


def test_named_conjuncts_present() -> None:
    # Pins the dependency on iter 994 and iter 995 (whose recognition
    # cells this matcher conjoins with a cross-side equality clause).
    for required in (
        "input_group_palette_constant_across_pairs",
        "output_group_palette_constant_across_pairs",
    ):
        assert required in CONDITION_REGISTRY, (
            f"required named conjunct {required!r} not registered"
        )


# ──────────────────────────────────────────────────────────────────────────
# Positive cases.
# ──────────────────────────────────────────────────────────────────────────

def test_single_pair_single_group_fires() -> None:
    patterns = {"pair_analyses": [_pair([_group([0, 1])])]}
    assert _matcher()(patterns, {}) is True


def test_single_pair_multiple_groups_same_palette_fires() -> None:
    patterns = {
        "pair_analyses": [
            _pair([_group([0, 1]), _group([0, 1]), _group([0, 1])])
        ],
    }
    assert _matcher()(patterns, {}) is True


def test_two_pairs_all_groups_same_palette_fires() -> None:
    patterns = {
        "pair_analyses": [
            _pair([_group([0, 1]), _group([0, 1])]),
            _pair([_group([0, 1])]),
        ],
    }
    assert _matcher()(patterns, {}) is True


def test_set_equal_under_different_list_order_fires() -> None:
    # frozenset equality is order-insensitive on either side.
    patterns = {
        "pair_analyses": [
            _pair([_group(
                [0, 1, 2],
                input_colors=[2, 0, 1],
                output_colors=[1, 2, 0],
            )]),
            _pair([_group(
                [0, 1, 2],
                input_colors=[1, 0, 2],
                output_colors=[0, 2, 1],
            )]),
        ],
    }
    assert _matcher()(patterns, {}) is True


def test_singleton_palette_fires() -> None:
    patterns = {
        "pair_analyses": [
            _pair([_group([5])]),
            _pair([_group([5]), _group([5])]),
        ],
    }
    assert _matcher()(patterns, {}) is True


def test_three_pairs_all_groups_same_palette_fires() -> None:
    patterns = {
        "pair_analyses": [
            _pair([_group([0, 1, 2])]),
            _pair([_group([0, 1, 2]), _group([0, 1, 2])]),
            _pair([_group([0, 1, 2])]),
        ],
    }
    assert _matcher()(patterns, {}) is True


# ──────────────────────────────────────────────────────────────────────────
# Negative cases (cross-side or cross-pair / cross-group set mismatch).
# ──────────────────────────────────────────────────────────────────────────

def test_per_group_input_neq_output_rejects() -> None:
    # The cross-side equality clause: input_colors set must equal
    # output_colors set on every group. Both sides could be constant
    # individually, but the set-equality clause must reject when
    # S_in != S_out.
    patterns = {
        "pair_analyses": [
            _pair([_group([0, 1], output_colors=[2, 3])]),
            _pair([_group([0, 1], output_colors=[2, 3])]),
        ],
    }
    assert _matcher()(patterns, {}) is False


def test_two_pairs_disjoint_group_palettes_rejects() -> None:
    # Per-group set varies across pairs.
    patterns = {
        "pair_analyses": [
            _pair([_group([0, 1])]),
            _pair([_group([2, 3])]),
        ],
    }
    assert _matcher()(patterns, {}) is False


def test_two_pairs_partial_overlap_rejects() -> None:
    patterns = {
        "pair_analyses": [
            _pair([_group([0, 1, 2])]),
            _pair([_group([0, 1, 3])]),
        ],
    }
    assert _matcher()(patterns, {}) is False


def test_subset_relation_rejects() -> None:
    patterns = {
        "pair_analyses": [
            _pair([_group([0, 1])]),
            _pair([_group([0, 1, 2])]),
        ],
    }
    assert _matcher()(patterns, {}) is False


def test_within_pair_group_palette_mismatch_rejects() -> None:
    # Per-group set equality is required ACROSS GROUPS within a pair.
    patterns = {
        "pair_analyses": [
            _pair([_group([0, 1]), _group([2, 3])]),
        ],
    }
    assert _matcher()(patterns, {}) is False


def test_one_offending_group_fails_the_gate() -> None:
    # Universal-over-groups: one mismatched group fails the whole task.
    patterns = {
        "pair_analyses": [
            _pair([_group([0, 1]), _group([0, 1])]),
            _pair([_group([0, 1]), _group([0, 1])]),
            _pair([_group([0, 1]), _group([0, 9])]),
        ],
    }
    assert _matcher()(patterns, {}) is False


def test_one_offending_group_cross_side_fails_the_gate() -> None:
    # A single offending group violating the cross-side equality
    # clause must fail the whole task.
    patterns = {
        "pair_analyses": [
            _pair([_group([0, 1]), _group([0, 1])]),
            _pair([_group([0, 1]), _group([0, 1], output_colors=[2, 3])]),
        ],
    }
    assert _matcher()(patterns, {}) is False


def test_same_cardinality_different_set_rejects() -> None:
    # Constant cardinality with varying set: iter 195 / 196 fire (per
    # iter 994 / 995 implication chain), this matcher rejects.
    patterns = {
        "pair_analyses": [
            _pair([_group([0, 1])]),
            _pair([_group([2, 3])]),
        ],
    }
    assert _matcher()(patterns, {}) is False


# ──────────────────────────────────────────────────────────────────────────
# Fail-closed paths.
# ──────────────────────────────────────────────────────────────────────────

def test_empty_pair_analyses_rejects() -> None:
    patterns = {"pair_analyses": []}
    assert _matcher()(patterns, {}) is False


def test_missing_pair_analyses_rejects() -> None:
    assert _matcher()({}, {}) is False


def test_non_list_pair_analyses_rejects() -> None:
    for bad in (None, 42, "oops", {"a": 1}, (), True):
        assert _matcher()({"pair_analyses": bad}, {}) is False, (
            f"pair_analyses={bad!r} should not fire"
        )


def test_non_dict_patterns_rejects() -> None:
    for bad in (None, [], "oops", 42):
        assert _matcher()(bad, {}) is False, f"patterns={bad!r} should not fire"  # type: ignore[arg-type]


def test_non_dict_analysis_rejects() -> None:
    patterns = {
        "pair_analyses": [_pair([_group([0, 1])]), "not-a-dict"],
    }
    assert _matcher()(patterns, {}) is False


def test_empty_groups_list_rejects_identity_territory() -> None:
    # Identity-territory rejection: zero-group pairs must not fire,
    # to keep this matcher's territory disjoint from iter 13's
    # ``identity_transformation`` by construction.
    patterns = {"pair_analyses": [_pair([])]}
    assert _matcher()(patterns, {}) is False


def test_one_pair_has_no_groups_rejects() -> None:
    patterns = {
        "pair_analyses": [
            _pair([_group([0, 1])]),
            _pair([]),
        ],
    }
    assert _matcher()(patterns, {}) is False


def test_non_list_groups_rejects() -> None:
    for bad in (None, 42, "oops", {"a": 1}, (), True):
        analysis = _pair([_group([0, 1])])
        analysis["groups"] = bad
        patterns = {"pair_analyses": [analysis]}
        assert _matcher()(patterns, {}) is False, f"groups={bad!r} should not fire"


def test_non_dict_group_rejects() -> None:
    analysis = _pair([_group([0, 1])])
    analysis["groups"] = [_group([0, 1]), "not-a-dict"]
    patterns = {"pair_analyses": [analysis]}
    assert _matcher()(patterns, {}) is False


def test_missing_input_colors_in_group_rejects() -> None:
    g = _group([0, 1])
    del g["input_colors"]
    patterns = {"pair_analyses": [_pair([g])]}
    assert _matcher()(patterns, {}) is False


def test_missing_output_colors_in_group_rejects() -> None:
    g = _group([0, 1])
    del g["output_colors"]
    patterns = {"pair_analyses": [_pair([g])]}
    assert _matcher()(patterns, {}) is False


def test_non_list_input_colors_rejects() -> None:
    for bad in (None, 42, "oops", {"a": 1}, (0, 1), True, {0, 1}):
        g = _group([0, 1])
        g["input_colors"] = bad
        patterns = {"pair_analyses": [_pair([g])]}
        assert _matcher()(patterns, {}) is False, (
            f"input_colors={bad!r} should not fire"
        )


def test_non_list_output_colors_rejects() -> None:
    for bad in (None, 42, "oops", {"a": 1}, (0, 1), True, {0, 1}):
        g = _group([0, 1])
        g["output_colors"] = bad
        patterns = {"pair_analyses": [_pair([g])]}
        assert _matcher()(patterns, {}) is False, (
            f"output_colors={bad!r} should not fire"
        )


def test_empty_input_colors_list_rejects() -> None:
    g = _group([0, 1])
    g["input_colors"] = []
    patterns = {"pair_analyses": [_pair([g])]}
    assert _matcher()(patterns, {}) is False


def test_empty_output_colors_list_rejects() -> None:
    g = _group([0, 1])
    g["output_colors"] = []
    patterns = {"pair_analyses": [_pair([g])]}
    assert _matcher()(patterns, {}) is False


def test_bool_in_input_colors_rejects() -> None:
    g = _group([0, 1])
    g["input_colors"] = [0, True]
    patterns = {"pair_analyses": [_pair([g])]}
    assert _matcher()(patterns, {}) is False


def test_bool_in_output_colors_rejects() -> None:
    g = _group([0, 1])
    g["output_colors"] = [0, True]
    patterns = {"pair_analyses": [_pair([g])]}
    assert _matcher()(patterns, {}) is False


def test_non_int_in_input_colors_rejects() -> None:
    for bad in ("1", 1.0, None, [1]):
        g = _group([0, 1])
        g["input_colors"] = [0, bad]
        patterns = {"pair_analyses": [_pair([g])]}
        assert _matcher()(patterns, {}) is False, (
            f"non-int {bad!r} in input_colors should not fire"
        )


def test_non_int_in_output_colors_rejects() -> None:
    for bad in ("1", 1.0, None, [1]):
        g = _group([0, 1])
        g["output_colors"] = [0, bad]
        patterns = {"pair_analyses": [_pair([g])]}
        assert _matcher()(patterns, {}) is False, (
            f"non-int {bad!r} in output_colors should not fire"
        )


def test_out_of_range_color_rejects_input() -> None:
    for bad in (-1, 10, 13, 100):
        g = _group([0, 1])
        g["input_colors"] = [0, bad]
        patterns = {"pair_analyses": [_pair([g])]}
        assert _matcher()(patterns, {}) is False, (
            f"out-of-range colour {bad!r} in input_colors should not fire"
        )


def test_out_of_range_color_rejects_output() -> None:
    for bad in (-1, 10, 13, 100):
        g = _group([0, 1])
        g["output_colors"] = [0, bad]
        patterns = {"pair_analyses": [_pair([g])]}
        assert _matcher()(patterns, {}) is False, (
            f"out-of-range colour {bad!r} in output_colors should not fire"
        )


# ──────────────────────────────────────────────────────────────────────────
# Behavioural contract.
# ──────────────────────────────────────────────────────────────────────────

def test_side_effect_free() -> None:
    patterns = {
        "pair_analyses": [
            _pair([_group([0, 1])]),
            _pair([_group([1, 0])]),
        ],
    }
    params = {"unused": 1}
    before_p = copy.deepcopy(patterns)
    before_q = copy.deepcopy(params)
    _matcher()(patterns, params)
    assert patterns == before_p, "matcher mutated patterns"
    assert params == before_q, "matcher mutated params"


def test_deterministic_across_repeats() -> None:
    patterns = {
        "pair_analyses": [
            _pair([_group([0, 1, 2])]),
            _pair([_group([0, 1, 2])]),
        ],
    }
    results = [_matcher()(patterns, {}) for _ in range(5)]
    assert len(set(results)) == 1, f"non-deterministic: {results}"


def test_returns_literal_boolean() -> None:
    out_true = _matcher()(
        {"pair_analyses": [_pair([_group([0, 1])])]}, {}
    )
    out_false = _matcher()(
        {"pair_analyses": [_pair([_group([0])]), _pair([_group([1])])]}, {}
    )
    assert out_true is True, f"expected literal True, got {out_true!r}"
    assert out_false is False, f"expected literal False, got {out_false!r}"


def test_ignores_whole_grid_palette_fields() -> None:
    # Per-group only; whole-grid palette fields don't change the verdict.
    patterns = {
        "pair_analyses": [
            _pair([_group([0, 1])], input_palette=[0, 1, 9],
                  output_palette=[0, 1, 2, 3, 4]),
            _pair([_group([0, 1])], input_palette=[0],
                  output_palette=[5, 6, 7, 8, 9]),
        ],
    }
    assert _matcher()(patterns, {}) is True


def test_ignores_dimensional_fields() -> None:
    patterns = {
        "pair_analyses": [
            _pair([_group([0, 1])], input_height=7, input_width=9,
                  output_height=2, output_width=3, size_match=False),
            _pair([_group([0, 1])], input_height=2, input_width=3,
                  output_height=2, output_width=3, size_match=True),
        ],
    }
    assert _matcher()(patterns, {}) is True


def test_params_ignored() -> None:
    p = {"pair_analyses": [_pair([_group([0, 1])])]}
    for params in ({}, {"x": 1}, {"foo": "bar"}, {"deep": {"nested": True}}):
        assert _matcher()(p, params) is True, (
            f"unexpected verdict shift with params={params!r}"
        )


# ──────────────────────────────────────────────────────────────────────────
# Conjunction relationships -- named conjuncts (iter 994 / 995).
# ──────────────────────────────────────────────────────────────────────────

def test_strict_implication_of_input_group_palette_constant() -> None:
    # Iter 994: input-side conjunct. STRICTLY IMPLIED.
    iter994 = CONDITION_REGISTRY["input_group_palette_constant_across_pairs"]

    # Both fire: matcher canonical S=={0,1} and per-group inputs all
    # have set {0,1}.
    p_both = {
        "pair_analyses": [
            _pair([_group([0, 1])]),
            _pair([_group([0, 1])]),
        ],
    }
    assert _matcher()(p_both, {}) is True
    assert iter994(p_both, {}) is True

    # Iter 994 fires, this matcher rejects: input sets constant across
    # pairs but output sets differ from input sets (cross-side equality
    # clause fails).
    p_in_only = {
        "pair_analyses": [
            _pair([_group([0, 1], output_colors=[2, 3])]),
            _pair([_group([0, 1], output_colors=[2, 3])]),
        ],
    }
    assert _matcher()(p_in_only, {}) is False
    assert iter994(p_in_only, {}) is True


def test_strict_implication_of_output_group_palette_constant() -> None:
    # Iter 995: output-side conjunct. STRICTLY IMPLIED by the symmetric
    # argument.
    iter995 = CONDITION_REGISTRY["output_group_palette_constant_across_pairs"]

    p_both = {
        "pair_analyses": [
            _pair([_group([0, 1])]),
            _pair([_group([0, 1])]),
        ],
    }
    assert _matcher()(p_both, {}) is True
    assert iter995(p_both, {}) is True

    # Iter 995 fires, this matcher rejects: output sets constant but
    # input sets differ.
    p_out_only = {
        "pair_analyses": [
            _pair([_group([0, 1], input_colors=[2, 3])]),
            _pair([_group([0, 1], input_colors=[2, 3])]),
        ],
    }
    assert _matcher()(p_out_only, {}) is False
    assert iter995(p_out_only, {}) is True


def test_both_conjuncts_alone_insufficient_without_cross_side_equality() -> None:
    # The (iter 994 AND iter 995) two-of-two conjunction CAN fire while
    # this matcher rejects: iter 994 fires with canonical S_in, iter 995
    # fires with canonical S_out, but S_in != S_out.
    iter994 = CONDITION_REGISTRY["input_group_palette_constant_across_pairs"]
    iter995 = CONDITION_REGISTRY["output_group_palette_constant_across_pairs"]

    p = {
        "pair_analyses": [
            _pair([_group([0, 1], output_colors=[2, 3])]),
            _pair([_group([0, 1], output_colors=[2, 3])]),
        ],
    }
    assert iter994(p, {}) is True
    assert iter995(p, {}) is True
    # Cross-side equality clause must reject because S_in={0,1} != S_out={2,3}.
    assert _matcher()(p, {}) is False


# ──────────────────────────────────────────────────────────────────────────
# Sibling-matcher relationships.
# ──────────────────────────────────────────────────────────────────────────

def test_independent_from_whole_grid_palette_conjunction() -> None:
    # Iter 991 (whole-grid input/output palette conjunction-handle):
    # NOT in a refinement relation either way.
    iter991 = CONDITION_REGISTRY[
        "input_output_palette_equal_and_constant_across_pairs"
    ]

    # This matcher fires, iter 991 rejects: per-group palette {0,1}
    # constant on both sides, but whole-grid palette varies across pairs.
    p_group_only = {
        "pair_analyses": [
            _pair([_group([0, 1])], input_palette=[0, 1, 2],
                  output_palette=[0, 1, 2]),
            _pair([_group([0, 1])], input_palette=[0, 1, 3],
                  output_palette=[0, 1, 3]),
        ],
    }
    assert _matcher()(p_group_only, {}) is True
    assert iter991(p_group_only, {}) is False

    # Iter 991 fires, this matcher rejects: whole-grid palette
    # {0,1,2} constant on both sides across pairs, but per-group sets
    # vary across pairs.
    p_whole_only = {
        "pair_analyses": [
            _pair([_group([0, 1])], input_palette=[0, 1, 2],
                  output_palette=[0, 1, 2]),
            _pair([_group([1, 2])], input_palette=[0, 1, 2],
                  output_palette=[0, 1, 2]),
        ],
    }
    assert _matcher()(p_whole_only, {}) is False
    assert iter991(p_whole_only, {}) is True


def test_independent_from_identity_transformation() -> None:
    identity = CONDITION_REGISTRY["identity_transformation"]
    p_identity = {
        "pair_analyses": [
            _pair([], total_changes=0),
            _pair([], total_changes=0),
        ],
    }
    assert identity(p_identity, {}) is True
    assert _matcher()(p_identity, {}) is False


def test_strict_implication_of_per_group_input_color_count() -> None:
    # Iter 195: per-group |input_colors| constancy. STRICTLY IMPLIED
    # (via iter 994).
    iter195 = CONDITION_REGISTRY[
        "change_input_color_count_per_group_constant_across_pairs"
    ]
    p_both = {
        "pair_analyses": [
            _pair([_group([0, 1])]),
            _pair([_group([0, 1])]),
        ],
    }
    assert _matcher()(p_both, {}) is True
    assert iter195(p_both, {}) is True


def test_strict_implication_of_per_group_output_color_count() -> None:
    # Iter 196: per-group |output_colors| constancy. STRICTLY IMPLIED
    # (via iter 995).
    iter196 = CONDITION_REGISTRY[
        "change_output_color_count_per_group_constant_across_pairs"
    ]
    p_both = {
        "pair_analyses": [
            _pair([_group([0, 1])]),
            _pair([_group([0, 1])]),
        ],
    }
    assert _matcher()(p_both, {}) is True
    assert iter196(p_both, {}) is True


def test_independent_from_output_colors_equals_input_colors_per_group() -> None:
    # ``output_colors_equals_input_colors_per_group`` asserts per-pair-per-
    # group set equality but not cross-pair / cross-group constancy.
    # This matcher additionally requires that single shared set be
    # bit-identical across every blob across every pair. So per-group
    # equality fires on the wider territory; this matcher fires on the
    # narrower (strictly tighter) one.
    sibling = CONDITION_REGISTRY[
        "output_colors_equals_input_colors_per_group"
    ]

    # Sibling fires, this matcher rejects: per-group input==output set
    # on every group of every pair, but the set varies across pairs
    # ({0,1} in pair 0, {2,3} in pair 1).
    p_sibling_only = {
        "pair_analyses": [
            _pair([_group([0, 1])]),
            _pair([_group([2, 3])]),
        ],
    }
    assert sibling(p_sibling_only, {}) is True
    assert _matcher()(p_sibling_only, {}) is False

    # Both fire on the constant-per-blob-set territory.
    p_both = {
        "pair_analyses": [
            _pair([_group([0, 1])]),
            _pair([_group([0, 1])]),
        ],
    }
    assert sibling(p_both, {}) is True
    assert _matcher()(p_both, {}) is True


def test_recognized_conditions_includes_this_matcher() -> None:
    from agent.conditions import recognized_conditions
    patterns = {
        "pair_analyses": [
            _pair([_group([0, 1])]),
            _pair([_group([0, 1])]),
        ],
    }
    fired = recognized_conditions(patterns)
    assert MATCHER_NAME in fired, (
        f"{MATCHER_NAME!r} did not fire on a clearly constant-per-group-"
        f"palette-with-cross-side-equality patterns dict; got {fired!r}"
    )


def test_recognized_conditions_excludes_on_cross_side_mismatch() -> None:
    from agent.conditions import recognized_conditions
    patterns = {
        "pair_analyses": [
            _pair([_group([0, 1], output_colors=[2, 3])]),
            _pair([_group([0, 1], output_colors=[2, 3])]),
        ],
    }
    fired = recognized_conditions(patterns)
    assert MATCHER_NAME not in fired, (
        f"{MATCHER_NAME!r} must NOT fire on per-blob input != output set; "
        f"got {fired!r}"
    )


def test_recognized_conditions_excludes_on_cross_pair_mismatch() -> None:
    from agent.conditions import recognized_conditions
    patterns = {
        "pair_analyses": [
            _pair([_group([0, 1])]),
            _pair([_group([2, 3])]),
        ],
    }
    fired = recognized_conditions(patterns)
    assert MATCHER_NAME not in fired, (
        f"{MATCHER_NAME!r} must NOT fire on cross-pair varying per-group "
        f"palettes; got {fired!r}"
    )


def test_recognized_conditions_excludes_on_identity_territory() -> None:
    from agent.conditions import recognized_conditions
    patterns = {
        "pair_analyses": [_pair([], total_changes=0), _pair([], total_changes=0)],
    }
    fired = recognized_conditions(patterns)
    assert MATCHER_NAME not in fired, (
        f"{MATCHER_NAME!r} must NOT fire on identity-territory patterns; "
        f"got {fired!r}"
    )


def test_does_not_displace_adjacent_iter_matchers() -> None:
    expected = {
        "input_palette_constant_across_pairs",
        "output_palette_constant_across_pairs",
        "input_output_palette_equal_and_constant_across_pairs",
        "input_output_dimensions_equal_and_constant_across_pairs",
        "input_output_dimensions_and_palette_equal_and_constant_across_pairs",
        "input_group_palette_constant_across_pairs",
        "output_group_palette_constant_across_pairs",
        "change_input_color_count_per_group_constant_across_pairs",
        "change_output_color_count_per_group_constant_across_pairs",
        "output_colors_equals_input_colors_per_group",
        "identity_transformation",
        "output_color_uniform",
        "input_color_uniform",
    }
    missing = expected - set(CONDITION_REGISTRY)
    assert not missing, f"adjacent matchers missing post-iter-996: {missing!r}"


# ──────────────────────────────────────────────────────────────────────────
# Runner.
# ──────────────────────────────────────────────────────────────────────────

def _collect_tests():
    return [
        (name, obj)
        for name, obj in globals().items()
        if name.startswith("test_") and callable(obj)
    ]


def main() -> int:
    failures = []
    tests = _collect_tests()
    for name, fn in tests:
        try:
            fn()
        except AssertionError as e:
            failures.append((name, str(e) or repr(e), traceback.format_exc()))
        except Exception as e:  # pragma: no cover -- contract assertions
            failures.append((name, f"{type(e).__name__}: {e}", traceback.format_exc()))
    total = len(tests)
    passed = total - len(failures)
    print(f"{passed}/{total} tests passed")
    for name, msg, tb in failures:
        print(f"\nFAIL {name}: {msg}\n{tb}")
    return 0 if not failures else 1


if __name__ == "__main__":
    sys.exit(main())
