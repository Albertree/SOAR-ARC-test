"""
tests/test_recognized_conditions.py — exercise the iter-11 applier
``agent.conditions.recognized_conditions``.

Runs without pytest:

    python tests/test_recognized_conditions.py

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

from agent.conditions import (  # noqa: E402
    CONDITION_REGISTRY,
    recognized_conditions,
)


# Patterns shapes that the three registered matchers will fire on (as of
# iter 10). These mirror the dicts ``ExtractPatternOperator`` produces in
# ``agent/active_operators.py``.

def _patterns_all_three_fire() -> dict:
    """A patterns dict that satisfies:
      * grid_size_preserved — top-level flag + per-pair size_match
      * consistent_color_mapping — every input color maps to exactly one
        output color (uses three distinct input colors so 0→3, 1→4, 2→5
        is a well-defined 1:1 mapping rather than a 0→{3,4,5} collision)
      * sequential_recoloring — three groups per pair, outputs form the
        contiguous range [3,4,5] ordered by top_row
    """
    return {
        "grid_size_preserved": True,
        "pair_analyses": [
            {
                "size_match": True,
                "num_groups": 3,
                "groups": [
                    {"input_colors": [0], "output_colors": [3],
                     "top_row": 0, "top_col": 0},
                    {"input_colors": [1], "output_colors": [4],
                     "top_row": 1, "top_col": 0},
                    {"input_colors": [2], "output_colors": [5],
                     "top_row": 2, "top_col": 0},
                ],
            },
            {
                "size_match": True,
                "num_groups": 3,
                "groups": [
                    {"input_colors": [0], "output_colors": [3],
                     "top_row": 0, "top_col": 0},
                    {"input_colors": [1], "output_colors": [4],
                     "top_row": 1, "top_col": 0},
                    {"input_colors": [2], "output_colors": [5],
                     "top_row": 2, "top_col": 0},
                ],
            },
        ],
    }


def _patterns_identity_pairs() -> dict:
    """Patterns whose every pair has zero changes AND matching
    dimensions. Fires both ``grid_size_preserved`` (dimensions match)
    AND ``identity_transformation`` (zero changes per pair) — they are
    layered preconditions, not competitors. The colour-mapping and
    sequential-recoloring matchers do NOT fire here (no change groups
    means no mapping to recognise)."""
    return {
        "grid_size_preserved": True,
        "pair_analyses": [
            {"size_match": True, "num_groups": 0, "groups": []},
            {"size_match": True, "num_groups": 0, "groups": []},
        ],
    }


def _patterns_color_mapping_only() -> dict:
    """consistent_color_mapping fires; grid_size_preserved does NOT
    (top-level flag is False), and sequential_recoloring does NOT
    (outputs [3, 7] are not a contiguous range)."""
    return {
        "grid_size_preserved": False,
        "pair_analyses": [
            {
                "size_match": False,
                "num_groups": 2,
                "groups": [
                    {"input_colors": [0], "output_colors": [3],
                     "top_row": 0, "top_col": 0},
                    {"input_colors": [5], "output_colors": [7],
                     "top_row": 1, "top_col": 0},
                ],
            },
            {
                "size_match": False,
                "num_groups": 2,
                "groups": [
                    {"input_colors": [0], "output_colors": [3],
                     "top_row": 0, "top_col": 0},
                    {"input_colors": [5], "output_colors": [7],
                     "top_row": 1, "top_col": 0},
                ],
            },
        ],
    }


# ──────────────────────────────────────────────────────────────────────────
# Tests.
# ──────────────────────────────────────────────────────────────────────────

def test_helper_is_importable_from_package_root() -> None:
    import agent.conditions as mod
    assert hasattr(mod, "recognized_conditions"), (
        "recognized_conditions not exported from agent.conditions"
    )
    assert callable(mod.recognized_conditions)


def test_registry_contents_after_helper_load() -> None:
    # The applier must not register itself or pull in anything beyond
    # the matcher modules under ``agent/conditions/``. As of iter 226
    # there are sixty-nine such modules; tightening the assertion to
    # ``==`` keeps a stray @register import from sneaking into the
    # package.
    assert set(CONDITION_REGISTRY.keys()) == {
        "grid_size_preserved",
        "consistent_color_mapping",
        "sequential_recoloring",
        "identity_transformation",
        "grid_size_changed",
        "output_color_uniform",
        "input_color_uniform",
        "output_dimensions_constant",
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
        "change_color_mapping_count_constant_across_pairs",
        "change_cells_constant_across_pairs",
        "input_dimensions_square",
        "output_dimensions_square",
        "output_palette_subset_of_input",
        "output_palette_equals_input",
        "output_palette_disjoint_from_input",
        "input_palette_subset_of_output",
        "output_palette_count_exceeds_input_palette_count",
        "input_palette_count_exceeds_output_palette_count",
        "palette_symmetric_difference_constant_across_pairs",
        "palette_intersection_count_constant_across_pairs",
        "palette_union_count_constant_across_pairs",
        "change_count_per_group_constant_across_pairs",
        "palette_shift_constant_across_pairs",
        "change_input_color_count_per_group_constant_across_pairs",
        "change_output_color_count_per_group_constant_across_pairs",
        "change_color_mapping_count_per_group_constant_across_pairs",
        "palette_shift_constant_across_groups_per_pair",
        "palette_shift_constant_across_groups_and_pairs",
        "output_colors_subset_of_input_colors_per_group",
        "output_colors_equals_input_colors_per_group",
        "input_colors_subset_of_output_colors_per_group",
        "output_colors_disjoint_from_input_colors_per_group",
        "output_colors_proper_subset_of_input_colors_per_group",
        "input_colors_proper_subset_of_output_colors_per_group",
        "output_colors_partial_overlap_with_input_colors_per_group",
        "change_palette_intersection_count_per_group_constant_across_pairs",
        "change_palette_symmetric_difference_count_per_group_constant_across_pairs",
        "change_palette_union_count_per_group_constant_across_pairs",
        "output_palette_partial_overlap_with_input_palette",
        "output_palette_proper_subset_of_input_palette",
        "input_palette_proper_subset_of_output_palette",
        "consistent_color_mapping_per_group",
        "input_color_uniform_per_group",
        "singleton_recolor_per_group",
        "singleton_recolor",
        "singleton_recolor_identity_per_group",
        "singleton_recolor_nonidentity_per_group",
        "singleton_recolor_identity",
        "singleton_recolor_nonidentity",
        "singleton_recolor_nonidentity_input_anchored",
        "singleton_recolor_nonidentity_output_anchored",
        "singleton_recolor_nonidentity_unanchored",
        "singleton_recolor_nonidentity_unanchored_function_shaped",
        "singleton_recolor_nonidentity_unanchored_non_function_shaped",
        "singleton_recolor_nonidentity_unanchored_non_function_shaped_within_pair_function_shaped",
    }, f"unexpected registry contents: {sorted(CONDITION_REGISTRY)}"


def test_all_three_matchers_fire_on_compatible_patterns() -> None:
    # Iter 28 expanded the set: the fixture has num_groups=3 per pair,
    # so multi_group_per_pair (iter 28's matcher, true iff num_groups
    # >= 2 per pair) also legitimately fires here. Iter 34 expands it
    # again: the fixture's two pairs share an identical per-pair colour-
    # mapping set {(0, 3), (1, 4), (2, 5)}, so
    # change_colors_constant_across_pairs (iter 34's matcher) also
    # legitimately fires. Iter 35 expands it once more: iter 34 strictly
    # implies iter 35 (input-side projection of the (ic, oc) set is the
    # per-pair input set {0, 1, 2} on both pairs), so
    # change_input_colors_constant_across_pairs also fires. Iter 36
    # expands it one more time on the symmetric output-side projection:
    # iter 34 strictly implies iter 36 (output-side projection of the
    # (ic, oc) set is the per-pair output set {3, 4, 5} on both pairs),
    # so change_output_colors_constant_across_pairs also fires. Iter 37
    # expands it again on the input-cardinality sub-axis: iter 35
    # strictly implies iter 37 (set bit-identical implies same
    # cardinality; per-pair input cardinality is 3 on both pairs), so
    # change_input_color_count_constant_across_pairs also fires. Iter 38
    # completes the symmetric output-cardinality projection: iter 36
    # strictly implies iter 38 (set bit-identical implies same
    # cardinality; per-pair output cardinality is 3 on both pairs), so
    # change_output_color_count_constant_across_pairs also fires. Iter 39
    # projects the group-count axis onto its cross-pair cardinality:
    # both pairs have num_groups == 3, so
    # change_group_count_constant_across_pairs also fires. Iter 40
    # projects iter 34's (ic, oc) set axis onto its cross-pair
    # cardinality: per-pair (ic, oc) set is {(0, 3), (1, 4), (2, 5)}
    # (cardinality 3) on both pairs, so
    # change_color_mapping_count_constant_across_pairs also fires.
    # Iter 195 projects iter 37's per-pair input-colour-cardinality
    # axis onto the per-group projection: every group has
    # len(input_colors) == 1 on both pairs, so
    # change_input_color_count_per_group_constant_across_pairs also
    # fires. Iter 196 projects iter 38's per-pair output-colour-
    # cardinality axis onto the per-group projection: every group has
    # len(output_colors) == 1 on both pairs, so
    # change_output_color_count_per_group_constant_across_pairs also
    # fires. Iter 197 projects iter 40's per-pair (ic, oc) cardinality
    # axis onto the per-group projection via the Cartesian product
    # ``len(input_colors) * len(output_colors)``: every group has
    # product == 1 on both pairs, so
    # change_color_mapping_count_per_group_constant_across_pairs also
    # fires. Iter 198 projects iter 194's whole-grid colour-translation
    # axis onto the per-group projection at per-pair scope: every
    # group has |input_colors| == |output_colors| == 1 with a single
    # well-defined per-group shift, AND those per-group shifts are
    # all k=3 within each pair (groups (0,3), (1,4), (2,5) -> k=3 on
    # both pairs), so palette_shift_constant_across_groups_per_pair
    # also fires. Iter 199 strictly refines iter 198 by additionally
    # requiring the per-pair k_P to be bit-identical across pairs;
    # the fixture's per-pair k_P is k=3 on both pairs, so the global
    # k=3 is well-defined and palette_shift_constant_across_groups_
    # and_pairs also fires. Iter 203 names the per-group palette-
    # disjoint cell of the per-group palette-relation sub-axis: every
    # group in the fixture has set(input_colors) ∩ set(output_colors)
    # == ∅ ({0}∩{3}=∅, {1}∩{4}=∅, {2}∩{5}=∅), so
    # output_colors_disjoint_from_input_colors_per_group also fires
    # (the iter-200 / 201 / 202 sub-axis matchers REJECT the disjoint
    # cell -- they pin the three non-disjoint cells of the four-cell
    # partition). Iter 207 projects iter 44's whole-grid intersection-
    # cardinality axis onto the per-group projection: every group in
    # the fixture has |ic ∩ oc| == 0 ({0}∩{3}=∅, {1}∩{4}=∅, {2}∩{5}=∅)
    # on both pairs, so change_palette_intersection_count_per_group_
    # constant_across_pairs also fires (with canonical K==0; strict
    # implication of iter 203, which fires on the same fixture). Iter
    # 208 projects iter 190's whole-grid symmetric-difference
    # cardinality axis onto the per-group projection: every group in
    # the fixture has |ic △ oc| == 2 ({0}△{3}={0,3}, {1}△{4}={1,4},
    # {2}△{5}={2,5}) on both pairs, so change_palette_symmetric_
    # difference_count_per_group_constant_across_pairs also fires
    # (with canonical K==2; co-fires with iter 207 on the same fixture
    # since |ic ∩ oc| == 0 is also constant). Iter 209 projects iter
    # 45's whole-grid union-cardinality axis onto the per-group
    # projection: every group in the fixture has |ic ∪ oc| == 2
    # ({0}∪{3}={0,3}, {1}∪{4}={1,4}, {2}∪{5}={2,5}) on both pairs,
    # so change_palette_union_count_per_group_constant_across_pairs
    # also fires (with canonical K==2; the per-group cardinality
    # triple {iter 207, iter 208, iter 209} all co-fire on the same
    # fixture, witnessing |△| = |∪| - |∩| = 2 - 0 = 2 by the linear
    # identity). Iter 213 projects iter 8's whole-task function-shape
    # axis onto the per-group projection: every group in the fixture
    # has |output_colors| == 1 ({3}, {4}, {5} on each pair), so the
    # per-group ic→oc cross-product is function-shaped in every group
    # and consistent_color_mapping_per_group also fires (strict
    # implication of iter 8 holds here -- iter 8 fires on this fixture,
    # so the per-group projection necessarily does too). Iter 214
    # mirrors iter 213 on the input side: every group in the fixture
    # has |input_colors| == 1 ({0}, {1}, {2} on each pair), so the
    # per-group oc→ic inverse cross-product is function-shaped in
    # every group and input_color_uniform_per_group also fires
    # (strict refinement of iter 195 at K==1; symmetric DUAL of iter
    # 213 on the input side). Iter 215 names the CO-FIRE conjunction
    # of iter 213 AND iter 214 at the per-group |ic| == |oc| == 1 cell:
    # the iter-10 canonical fixture has every group with |ic| ==
    # |oc| == 1 (ic=[0], oc=[3]; ic=[1], oc=[4]; ic=[2], oc=[5]), so
    # singleton_recolor_per_group also fires (strict refinement of
    # both iter 213 and iter 214 on this fixture). Iter 218 names
    # the STRICT COMPLEMENT of iter 217 within iter 215's territory:
    # per-group |ic| == |oc| == 1 AND ic != oc. The iter-10 canonical
    # fixture has ic=[0]/oc=[3], ic=[1]/oc=[4], ic=[2]/oc=[5] on every
    # group of every pair -- per-group |ic| == |oc| == 1 with ic !=
    # oc -- so singleton_recolor_nonidentity_per_group also fires
    # (strict refinement of iter 215 at the non-identity sub-cell;
    # iter 217 does NOT fire on this fixture since the singletons
    # strictly differ per group). Iter 223 names the (F, F) "neither
    # anchored" cell of iter 218's 2x2 cross-group-identity axis: the
    # iter-10 canonical fixture has |observed_input| == |{0,1,2}| == 3
    # > 1 AND |observed_output| == |{3,4,5}| == 3 > 1 -- neither side
    # is cross-group-identity-anchored -- so singleton_recolor_
    # nonidentity_unanchored also fires (strict refinement of iter
    # 218 at the (F, F) cell; iters 220 / 221 / 222 do NOT fire on
    # this fixture since they each demand at least one cross-group
    # anchor). Iter 224 splits iter 223's (F, F) territory on the
    # function-shape sub-axis (the iter-8 ^ iter-223 cofire cell):
    # the iter-10 canonical fixture's per-group (C_g, K_g) mapping
    # 0 -> 3, 1 -> 4, 2 -> 5 is function-shaped, so singleton_recolor_
    # nonidentity_unanchored_function_shaped also fires (strict
    # refinement of iter 223 AND iter 8 at the cofire cell). With
    # this iter's matcher landed, the iter-10 canonical fixture now
    # witnesses the function-shape sub-cell at a distinguishing
    # recognition handle. Iter 225 names the strict-complement non-
    # function-shape sub-cell of iter 223 (singleton_recolor_non
    # identity_unanchored_non_function_shaped): the iter-10 canonical
    # fixture is function-shaped (every C_g sees exactly one K_g), so
    # iter 225's matcher REJECTS this fixture by design (its positive
    # co-fire witness requires some C_g -> multiple K_g's, which the
    # iter-10 fixture does not exhibit). The expected co-fire count
    # therefore stays at twenty-six on this fixture; the iter-225
    # matcher's positive co-fire witness lives in tests/test_singleton
    # _recolor_nonidentity_unanchored_non_function_shaped.py instead.
    # Iter 226 names the strict-refinement within-pair-function-shape
    # sub-cell of iter 225 (singleton_recolor_nonidentity_unanchored_
    # non_function_shaped_within_pair_function_shaped): it requires
    # GLOBAL non-function-shape (iter 225 precondition), which the
    # iter-10 fixture does not exhibit, so iter 226 also REJECTS
    # this fixture by design. The expected co-fire count therefore
    # stays at twenty-six on this fixture; iter 226's positive co-
    # fire witness lives in tests/test_singleton_recolor_nonidentity_
    # unanchored_non_function_shaped_within_pair_function_shaped.py
    # instead.
    # The three matchers in this test's name remain the iter-10
    # colour/dimension subset; the assertion grows with the registry
    # rather than fighting it.
    fired = recognized_conditions(_patterns_all_three_fire())
    assert set(fired) == {
        "grid_size_preserved",
        "consistent_color_mapping",
        "sequential_recoloring",
        "multi_group_per_pair",
        "change_colors_constant_across_pairs",
        "change_input_colors_constant_across_pairs",
        "change_output_colors_constant_across_pairs",
        "change_input_color_count_constant_across_pairs",
        "change_output_color_count_constant_across_pairs",
        "change_group_count_constant_across_pairs",
        "change_color_mapping_count_constant_across_pairs",
        "change_input_color_count_per_group_constant_across_pairs",
        "change_output_color_count_per_group_constant_across_pairs",
        "change_color_mapping_count_per_group_constant_across_pairs",
        "palette_shift_constant_across_groups_per_pair",
        "palette_shift_constant_across_groups_and_pairs",
        "output_colors_disjoint_from_input_colors_per_group",
        "change_palette_intersection_count_per_group_constant_across_pairs",
        "change_palette_symmetric_difference_count_per_group_constant_across_pairs",
        "change_palette_union_count_per_group_constant_across_pairs",
        "consistent_color_mapping_per_group",
        "input_color_uniform_per_group",
        "singleton_recolor_per_group",
        "singleton_recolor_nonidentity_per_group",
        "singleton_recolor_nonidentity_unanchored",
        "singleton_recolor_nonidentity_unanchored_function_shaped",
    }, f"expected the twenty-six compatible matchers to fire, got {fired}"


def test_identity_pairs_fire_both_grid_size_and_identity_matchers() -> None:
    # Zero-change pairs with matching dimensions fire BOTH the iter-1
    # dimensional precondition AND the iter-13 identity matcher; the
    # colour-mapping / sequential-recoloring matchers do not (they need
    # at least one changed group to recognise a mapping or sequence).
    fired = set(recognized_conditions(_patterns_identity_pairs()))
    assert fired == {"grid_size_preserved", "identity_transformation"}, (
        f"expected grid_size_preserved + identity_transformation, got "
        f"{sorted(fired)}"
    )


def test_color_mapping_fires_without_grid_size_preserved() -> None:
    fired = recognized_conditions(_patterns_color_mapping_only())
    assert "consistent_color_mapping" in fired, (
        "consistent_color_mapping must be dimension-agnostic"
    )
    assert "grid_size_preserved" not in fired, (
        "grid_size_preserved must not fire when flag is False"
    )
    assert "sequential_recoloring" not in fired, (
        "non-contiguous outputs must not fire sequential_recoloring"
    )


def test_returns_registry_insertion_order() -> None:
    expected_order = [n for n in CONDITION_REGISTRY.keys()
                      if n in {"grid_size_preserved",
                               "consistent_color_mapping",
                               "sequential_recoloring",
                               "identity_transformation"}]
    fired = recognized_conditions(_patterns_all_three_fire())
    fired_in_expected = [n for n in fired if n in expected_order]
    assert fired_in_expected == [n for n in expected_order if n in fired], (
        f"order mismatch: registry says {expected_order}, applier says {fired}"
    )


def test_empty_patterns_dict_fires_nothing() -> None:
    assert recognized_conditions({}) == []


def test_returns_empty_on_non_dict_patterns() -> None:
    assert recognized_conditions(None) == []        # type: ignore[arg-type]
    assert recognized_conditions([]) == []          # type: ignore[arg-type]
    assert recognized_conditions("oops") == []      # type: ignore[arg-type]
    assert recognized_conditions(42) == []          # type: ignore[arg-type]


def test_returns_list_type_for_downstream_consumers() -> None:
    fired = recognized_conditions(_patterns_all_three_fire())
    assert isinstance(fired, list), f"expected list, got {type(fired).__name__}"


def test_params_per_type_argument_is_forwarded() -> None:
    # None of the iter-1/8/10 matchers consume params today, but the API
    # must thread the argument through so a future parameterised matcher
    # gets its dict. Stand up a sentinel matcher that *requires* a
    # specific param, register it temporarily, and check the applier
    # passes the param through.
    seen: dict = {}

    def _sentinel(patterns: dict, params: dict) -> bool:
        seen["params"] = params
        return params.get("magic") == "xyz"

    name = "__iter11_sentinel_pass_through__"
    assert name not in CONDITION_REGISTRY
    CONDITION_REGISTRY[name] = _sentinel
    try:
        fired = recognized_conditions(
            _patterns_all_three_fire(),
            params_per_type={name: {"magic": "xyz"}},
        )
        assert name in fired, "sentinel should fire when params match"
        assert seen.get("params") == {"magic": "xyz"}, (
            f"applier did not forward params: got {seen.get('params')!r}"
        )
    finally:
        del CONDITION_REGISTRY[name]


def test_params_per_type_missing_entry_defaults_to_empty_dict() -> None:
    # A matcher registered in the registry but with no entry in
    # ``params_per_type`` must receive ``{}``, not crash. Confirm with a
    # sentinel that records what it received.
    seen: list = []

    def _sentinel(patterns: dict, params: dict) -> bool:
        seen.append(params)
        return False

    name = "__iter11_sentinel_default_params__"
    CONDITION_REGISTRY[name] = _sentinel
    try:
        recognized_conditions(_patterns_all_three_fire(), params_per_type={})
        assert seen == [{}], f"expected default {{}}, got {seen}"
    finally:
        del CONDITION_REGISTRY[name]


def test_non_dict_params_per_type_entry_falls_back_to_empty_dict() -> None:
    seen: list = []

    def _sentinel(patterns: dict, params: dict) -> bool:
        seen.append(params)
        return False

    name = "__iter11_sentinel_bad_params__"
    CONDITION_REGISTRY[name] = _sentinel
    try:
        recognized_conditions(
            _patterns_all_three_fire(),
            params_per_type={name: "not-a-dict"},  # type: ignore[dict-item]
        )
        assert seen == [{}], f"expected {{}} fallback, got {seen}"
    finally:
        del CONDITION_REGISTRY[name]


def test_non_dict_params_per_type_top_level_defaults_to_empty() -> None:
    # If the whole ``params_per_type`` argument is something other than a
    # dict (None / list / int), the applier still runs and every matcher
    # sees ``{}``.
    fired_none = recognized_conditions(_patterns_all_three_fire(),
                                       params_per_type=None)
    fired_list = recognized_conditions(_patterns_all_three_fire(),
                                       params_per_type=[])  # type: ignore[arg-type]
    fired_int = recognized_conditions(_patterns_all_three_fire(),
                                      params_per_type=42)  # type: ignore[arg-type]
    assert fired_none == fired_list == fired_int, (
        f"non-dict params_per_type did not normalise to empty: "
        f"{fired_none} {fired_list} {fired_int}"
    )


def test_is_side_effect_free_on_inputs() -> None:
    patterns = _patterns_all_three_fire()
    params = {"grid_size_preserved": {"unused": 1}}
    before_patterns = copy.deepcopy(patterns)
    before_params = copy.deepcopy(params)
    recognized_conditions(patterns, params_per_type=params)
    assert patterns == before_patterns, "applier mutated patterns"
    assert params == before_params, "applier mutated params_per_type"


def test_does_not_swallow_matcher_exceptions() -> None:
    # docs/RULE_FORMAT.md §4 says matchers must return False on malformed
    # input, never raise. The applier therefore must not paper over a
    # raising matcher — that would silently corrupt the recognition
    # output and mirror F7 (swallowed RuleSchemaError) in spirit.
    def _boom(patterns: dict, params: dict) -> bool:
        raise RuntimeError("matcher contract violation")

    name = "__iter11_boom__"
    CONDITION_REGISTRY[name] = _boom
    try:
        raised = False
        try:
            recognized_conditions(_patterns_all_three_fire())
        except RuntimeError:
            raised = True
        assert raised, "applier silently swallowed RuntimeError"
    finally:
        del CONDITION_REGISTRY[name]


def test_is_deterministic_across_repeat_calls() -> None:
    patterns = _patterns_all_three_fire()
    runs = [tuple(recognized_conditions(patterns)) for _ in range(5)]
    assert len(set(runs)) == 1, f"non-deterministic outputs: {set(runs)}"


def test_registry_is_not_modified_during_application() -> None:
    snapshot_keys = list(CONDITION_REGISTRY.keys())
    snapshot_values = list(CONDITION_REGISTRY.values())
    recognized_conditions(_patterns_all_three_fire())
    assert list(CONDITION_REGISTRY.keys()) == snapshot_keys, (
        "registry keys changed after applier call"
    )
    assert list(CONDITION_REGISTRY.values()) == snapshot_values, (
        "registry values changed after applier call"
    )


def test_returns_only_matchers_whose_match_is_strictly_true() -> None:
    # A matcher returning truthy-but-not-True (e.g. 1, "yes") must NOT
    # fire — the matcher contract is bool, not truthiness.
    def _truthy_not_true(patterns: dict, params: dict):
        return 1  # truthy, but `is True` is False

    name = "__iter11_truthy_not_true__"
    CONDITION_REGISTRY[name] = _truthy_not_true
    try:
        fired = recognized_conditions(_patterns_all_three_fire())
        assert name not in fired, (
            "applier accepted truthy non-bool; contract is `is True`"
        )
    finally:
        del CONDITION_REGISTRY[name]


# ──────────────────────────────────────────────────────────────────────────
# Driver.
# ──────────────────────────────────────────────────────────────────────────

def _run_all() -> int:
    tests = [
        test_helper_is_importable_from_package_root,
        test_registry_contents_after_helper_load,
        test_all_three_matchers_fire_on_compatible_patterns,
        test_identity_pairs_fire_both_grid_size_and_identity_matchers,
        test_color_mapping_fires_without_grid_size_preserved,
        test_returns_registry_insertion_order,
        test_empty_patterns_dict_fires_nothing,
        test_returns_empty_on_non_dict_patterns,
        test_returns_list_type_for_downstream_consumers,
        test_params_per_type_argument_is_forwarded,
        test_params_per_type_missing_entry_defaults_to_empty_dict,
        test_non_dict_params_per_type_entry_falls_back_to_empty_dict,
        test_non_dict_params_per_type_top_level_defaults_to_empty,
        test_is_side_effect_free_on_inputs,
        test_does_not_swallow_matcher_exceptions,
        test_is_deterministic_across_repeat_calls,
        test_registry_is_not_modified_during_application,
        test_returns_only_matchers_whose_match_is_strictly_true,
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
        print("\nall recognized_conditions tests passed.")
    else:
        print(f"\n{rc} test(s) failed.")
    sys.exit(0 if rc == 0 else 1)
