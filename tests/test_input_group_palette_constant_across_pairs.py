"""
tests/test_input_group_palette_constant_across_pairs.py -- exercise
the iter-994 matcher
``agent.conditions.input_group_palette_constant_across_pairs`` (new in
this iter).

Pins the matcher's contract per
``agent/conditions/input_group_palette_constant_across_pairs.py``
docstring: every change group of every example pair shares the same
``frozenset(group["input_colors"])`` on a non-empty ``pair_analyses``
list with non-empty per-pair ``groups`` lists and strict per-colour
typing (int in ``range(10)``, bool rejected). Recognition vocabulary
axis: the per-group projection of iter 989's whole-grid
``input_palette_constant_across_pairs`` on the input-side cross-pair-
set-constancy x per-group-scope cell.

Runs without pytest:

    python tests/test_input_group_palette_constant_across_pairs.py

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


MATCHER_NAME = "input_group_palette_constant_across_pairs"


def _matcher():
    return CONDITION_REGISTRY[MATCHER_NAME]


def _group(input_colors, output_colors=None, **overrides):
    """A group_analysis shaped like ``_analyze_pair``'s emit (iter-1
    schema). ``output_colors`` defaults to a distinct singleton so the
    matcher cannot accidentally read output state."""
    if output_colors is None:
        output_colors = [9]
    base = {
        "input_colors": list(input_colors),
        "output_colors": list(output_colors),
        "top_row": 0,
        "top_col": 0,
        "cell_count": max(len(input_colors), 1),
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


def test_p5_at_least_88() -> None:
    # This matcher brings the registry to >= 88 (P5 monotone).
    assert len(CONDITION_REGISTRY) >= 88, (
        f"expected >= 88 matchers post-iter-994; got {len(CONDITION_REGISTRY)}"
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
    # frozenset equality is order-insensitive.
    patterns = {
        "pair_analyses": [
            _pair([_group([2, 0, 1])]),
            _pair([_group([1, 2, 0])]),
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
# Negative cases (palette mismatch).
# ──────────────────────────────────────────────────────────────────────────

def test_two_pairs_disjoint_group_palettes_rejects() -> None:
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
    # One per-group palette is a strict subset of the other -- not equal.
    patterns = {
        "pair_analyses": [
            _pair([_group([0, 1])]),
            _pair([_group([0, 1, 2])]),
        ],
    }
    assert _matcher()(patterns, {}) is False


def test_within_pair_group_palette_mismatch_rejects() -> None:
    # Per-group set equality is required ACROSS GROUPS too, not only
    # across pairs. Two groups in the same pair with different palettes
    # fail the gate even if the multiset of palettes across pairs is
    # symmetric.
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
            _pair([_group([0, 1]), _group([0, 9])]),  # offending group
        ],
    }
    assert _matcher()(patterns, {}) is False


def test_same_cardinality_different_set_rejects() -> None:
    # Iter 195's territory (constant cardinality, varying set): this
    # matcher must reject.
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
    # ``identity_transformation`` by construction (mirrors iter
    # 195/196/197/207/208 per-group posture).
    patterns = {"pair_analyses": [_pair([])]}
    assert _matcher()(patterns, {}) is False


def test_one_pair_has_no_groups_rejects() -> None:
    # Even if other pairs have consistent group palettes, an identity
    # pair fails the gate.
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


def test_non_list_input_colors_rejects() -> None:
    for bad in (None, 42, "oops", {"a": 1}, (0, 1), True, {0, 1}):
        g = _group([0, 1])
        g["input_colors"] = bad
        patterns = {"pair_analyses": [_pair([g])]}
        assert _matcher()(patterns, {}) is False, (
            f"input_colors={bad!r} should not fire"
        )


def test_empty_input_colors_list_rejects() -> None:
    # An empty per-group input_colors list is an extractor contract
    # violation (a connected change group always has >= 1 cell with a
    # non-null input colour).
    g = _group([0, 1])
    g["input_colors"] = []
    patterns = {"pair_analyses": [_pair([g])]}
    assert _matcher()(patterns, {}) is False


def test_bool_in_input_colors_rejects() -> None:
    # Python bools are an int subclass; strict gate must reject them.
    g = _group([0, 1])
    g["input_colors"] = [0, True]
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


def test_out_of_range_color_rejects() -> None:
    # ARC colours live in [0, 9]; strict bound must reject sentinels
    # (e.g. 13 transparency or negative values) in the recognition
    # input -- ``_analyze_pair`` only emits grid-observed colours, so
    # an out-of-range entry is upstream extractor breakage.
    for bad in (-1, 10, 13, 100):
        g = _group([0, 1])
        g["input_colors"] = [0, bad]
        patterns = {"pair_analyses": [_pair([g])]}
        assert _matcher()(patterns, {}) is False, (
            f"out-of-range colour {bad!r} should not fire"
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


def test_ignores_output_colors() -> None:
    # The matcher reads ONLY per-group ``input_colors``. Different
    # output_colors must not affect the verdict.
    patterns = {
        "pair_analyses": [
            _pair([_group([0, 1], output_colors=[2])]),
            _pair([_group([0, 1], output_colors=[3])]),
        ],
    }
    assert _matcher()(patterns, {}) is True


def test_ignores_whole_grid_palette_fields() -> None:
    # The matcher reads per-group input_colors only; arbitrary
    # whole-grid ``input_palette`` / ``output_palette`` must not
    # change the verdict (distinguishing this matcher from iter 989).
    patterns = {
        "pair_analyses": [
            _pair([_group([0, 1])], input_palette=[0, 1, 2, 3, 4],
                  output_palette=[0, 1, 9]),
            _pair([_group([0, 1])], input_palette=[5, 6, 7, 8, 9],
                  output_palette=[0]),
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
# Sibling-matcher relationships.
# ──────────────────────────────────────────────────────────────────────────

def test_strict_implication_of_per_group_input_color_count() -> None:
    # Iter 195: per-group |input_colors| constancy. STRICT IMPLICATION:
    # this matcher implies iter 195 (equal sets have equal cardinality).
    iter195 = CONDITION_REGISTRY[
        "change_input_color_count_per_group_constant_across_pairs"
    ]

    # Same set across all groups: both fire.
    p_both = {
        "pair_analyses": [
            _pair([_group([0, 1])]),
            _pair([_group([0, 1]), _group([0, 1])]),
        ],
    }
    assert _matcher()(p_both, {}) is True
    assert iter195(p_both, {}) is True

    # Constant cardinality 2 with varying sets: iter 195 fires,
    # this matcher rejects.
    p_card_only = {
        "pair_analyses": [
            _pair([_group([0, 1])]),
            _pair([_group([2, 3])]),
        ],
    }
    assert _matcher()(p_card_only, {}) is False
    assert iter195(p_card_only, {}) is True


def test_independent_from_whole_grid_input_palette_constant() -> None:
    # Iter 989: whole-grid input palette cross-pair constancy. NOT in
    # a refinement relation either way.
    iter989 = CONDITION_REGISTRY["input_palette_constant_across_pairs"]

    # This matcher fires, iter 989 rejects: every change blob uses
    # ``{0, 1}`` across both pairs, but the surrounding background
    # makes the whole-grid input palette differ.
    p_group_only = {
        "pair_analyses": [
            _pair([_group([0, 1])], input_palette=[0, 1, 2]),
            _pair([_group([0, 1])], input_palette=[0, 1, 3]),
        ],
    }
    assert _matcher()(p_group_only, {}) is True
    assert iter989(p_group_only, {}) is False

    # Iter 989 fires, this matcher rejects: whole-grid palette equal
    # across pairs, but per-group ``input_colors`` differs.
    p_whole_only = {
        "pair_analyses": [
            _pair([_group([0, 1])], input_palette=[0, 1, 2]),
            _pair([_group([1, 2])], input_palette=[0, 1, 2]),
        ],
    }
    assert _matcher()(p_whole_only, {}) is False
    assert iter989(p_whole_only, {}) is True


def test_independent_from_identity_transformation() -> None:
    # Identity says zero groups per pair AND size_match; this matcher
    # rejects zero-group pairs by construction (identity-territory
    # rejection).
    identity = CONDITION_REGISTRY["identity_transformation"]

    p_identity = {
        "pair_analyses": [
            _pair([], total_changes=0),
            _pair([], total_changes=0),
        ],
    }
    assert identity(p_identity, {}) is True
    assert _matcher()(p_identity, {}) is False


def test_independent_from_change_input_colors_constant_across_pairs() -> None:
    # Iter 35: per-pair-aggregated set of single-colour-blob input
    # colours. NOT in a refinement relation either way.
    iter35 = CONDITION_REGISTRY["change_input_colors_constant_across_pairs"]

    # This matcher fires with multi-colour blobs (``len >= 2``) --
    # iter 35 rejects (requires ``len == 1``).
    p_multi = {
        "pair_analyses": [
            _pair([_group([0, 1])]),
            _pair([_group([0, 1])]),
        ],
    }
    assert _matcher()(p_multi, {}) is True
    assert iter35(p_multi, {}) is False

    # Iter 35 fires on a multi-blob task where per-pair {blob inputs}
    # sets match but the per-group identity varies. This matcher
    # rejects because the canonical per-group set is {0} (first
    # group of pair 0) and pair 1's first group has {1}.
    p_iter35_only = {
        "pair_analyses": [
            _pair([_group([0]), _group([1]), _group([2])]),
            _pair([_group([1]), _group([0]), _group([2])]),
        ],
    }
    assert _matcher()(p_iter35_only, {}) is False
    assert iter35(p_iter35_only, {}) is True


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
        f"palette patterns dict; got {fired!r}"
    )


def test_recognized_conditions_excludes_on_mismatch() -> None:
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
        "change_input_color_count_per_group_constant_across_pairs",
        "change_input_colors_constant_across_pairs",
        "identity_transformation",
        "input_color_uniform",
    }
    missing = expected - set(CONDITION_REGISTRY)
    assert not missing, f"adjacent matchers missing post-iter-994: {missing!r}"


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
