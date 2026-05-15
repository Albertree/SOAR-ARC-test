"""
tests/test_input_output_palette_equal_at_both_scopes_and_scope_aligned_and_constant_across_pairs.py
-- exercise the iter-999 matcher
``agent.conditions.input_output_palette_equal_at_both_scopes_and_scope_aligned_and_constant_across_pairs``
(new in this iter).

Pins the matcher's contract per the docstring of
``agent/conditions/input_output_palette_equal_at_both_scopes_and_scope_aligned_and_constant_across_pairs.py``:
the strict refinement of iter 997 with the additional ``S_whole == S_blob``
clause. Fires iff iter 997 fires AND the canonical whole-grid palette
equals the canonical per-blob palette.

Runs without pytest:

    python tests/test_input_output_palette_equal_at_both_scopes_and_scope_aligned_and_constant_across_pairs.py

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


MATCHER_NAME = (
    "input_output_palette_equal_at_both_scopes_and_scope_aligned_and_constant_across_pairs"
)
ITER_997_HANDLE = (
    "input_output_group_palette_and_whole_grid_palette_equal_and_constant_across_pairs"
)
ITER_991_HANDLE = "input_output_palette_equal_and_constant_across_pairs"
ITER_996_HANDLE = "input_output_group_palette_equal_and_constant_across_pairs"


def _matcher():
    return CONDITION_REGISTRY[MATCHER_NAME]


def _group(palette, **overrides):
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
    if groups and input_palette is None:
        union = set()
        for g in groups:
            union.update(g.get("input_colors", []))
        input_palette = sorted(union) if union else [0]
    elif input_palette is None:
        input_palette = [0, 1]
    if output_palette is None:
        output_palette = list(input_palette)
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


def test_p5_at_least_93() -> None:
    # Iter-999 brings the registry to >= 93 (P5 monotone). The probe
    # baseline was P5 = 92 after iter 998.
    assert len(CONDITION_REGISTRY) >= 93, (
        f"expected >= 93 matchers post-iter-999; got {len(CONDITION_REGISTRY)}"
    )


def test_named_parent_present() -> None:
    # The matcher dispatches through iter 997; if that handle goes
    # missing the iter is mis-staged.
    assert ITER_997_HANDLE in CONDITION_REGISTRY, (
        f"missing iter-997 parent {ITER_997_HANDLE!r}"
    )
    assert ITER_991_HANDLE in CONDITION_REGISTRY
    assert ITER_996_HANDLE in CONDITION_REGISTRY


# ──────────────────────────────────────────────────────────────────────────
# Positive cases (S_whole == S_blob).
# ──────────────────────────────────────────────────────────────────────────

def test_single_pair_single_group_scope_aligned_fires() -> None:
    # Whole-grid input/output = per-blob input/output = {0, 1}.
    patterns = {
        "pair_analyses": [
            _pair([_group([0, 1])], input_palette=[0, 1],
                  output_palette=[0, 1]),
        ],
    }
    assert _matcher()(patterns, {}) is True


def test_two_pairs_scope_aligned_fires() -> None:
    patterns = {
        "pair_analyses": [
            _pair([_group([0, 1])], input_palette=[0, 1],
                  output_palette=[0, 1]),
            _pair([_group([0, 1])], input_palette=[0, 1],
                  output_palette=[0, 1]),
        ],
    }
    assert _matcher()(patterns, {}) is True


def test_three_pairs_scope_aligned_fires() -> None:
    patterns = {
        "pair_analyses": [
            _pair([_group([7, 8])], input_palette=[7, 8],
                  output_palette=[7, 8]),
            _pair([_group([7, 8])], input_palette=[7, 8],
                  output_palette=[7, 8]),
            _pair([_group([7, 8])], input_palette=[7, 8],
                  output_palette=[7, 8]),
        ],
    }
    assert _matcher()(patterns, {}) is True


def test_multiple_groups_scope_aligned_fires() -> None:
    # Two blobs per pair, each with per-blob palette = whole-grid
    # palette = {0, 1}.
    patterns = {
        "pair_analyses": [
            _pair([_group([0, 1]), _group([0, 1])],
                  input_palette=[0, 1], output_palette=[0, 1]),
            _pair([_group([0, 1])], input_palette=[0, 1],
                  output_palette=[0, 1]),
        ],
    }
    assert _matcher()(patterns, {}) is True


def test_singleton_palette_scope_aligned_fires() -> None:
    patterns = {
        "pair_analyses": [
            _pair([_group([5])], input_palette=[5], output_palette=[5]),
            _pair([_group([5])], input_palette=[5], output_palette=[5]),
        ],
    }
    assert _matcher()(patterns, {}) is True


def test_set_equal_different_list_order_fires() -> None:
    # frozenset equality is order-insensitive on every conjunct AND on
    # the new scope-alignment clause.
    patterns = {
        "pair_analyses": [
            _pair([_group([0, 1, 2],
                          input_colors=[2, 0, 1],
                          output_colors=[1, 2, 0])],
                  input_palette=[1, 0, 2], output_palette=[2, 1, 0]),
            _pair([_group([0, 1, 2],
                          input_colors=[1, 0, 2],
                          output_colors=[0, 2, 1])],
                  input_palette=[0, 2, 1], output_palette=[1, 0, 2]),
        ],
    }
    assert _matcher()(patterns, {}) is True


# ──────────────────────────────────────────────────────────────────────────
# The discriminating case: iter 997 fires but S_whole != S_blob.
#
# This is the new semantic content this iter introduces. Iter 997
# (=iter 991 AND iter 996) is satisfied on these fixtures but the
# canonical whole-grid palette is a strict superset of the canonical
# per-blob palette. The new "scope-aligned" clause rejects.
# ──────────────────────────────────────────────────────────────────────────

def test_iter_997_fires_but_scope_unaligned_rejects_superset_whole_grid() -> None:
    # Whole-grid palette {0, 1, 2} constant across pairs (iter 991
    # fires); per-blob palette {0, 1} constant across blobs / pairs
    # (iter 996 fires); so iter 997 fires -- but S_whole = {0,1,2}
    # != S_blob = {0,1}, so this matcher rejects.
    patterns = {
        "pair_analyses": [
            _pair([_group([0, 1])], input_palette=[0, 1, 2],
                  output_palette=[0, 1, 2]),
            _pair([_group([0, 1])], input_palette=[0, 1, 2],
                  output_palette=[0, 1, 2]),
        ],
    }
    # Sanity: confirm iter 997 fires on the same fixture.
    iter_997 = CONDITION_REGISTRY[ITER_997_HANDLE]
    assert iter_997(patterns, {}) is True
    # The new clause rejects.
    assert _matcher()(patterns, {}) is False


def test_iter_997_fires_but_scope_unaligned_rejects_singleton_blob_in_pair_palette() -> None:
    # Whole-grid {3, 4} constant, per-blob {3} constant -- iter 997
    # fires, S_whole = {3,4} != S_blob = {3}, this matcher rejects.
    patterns = {
        "pair_analyses": [
            _pair([_group([3])], input_palette=[3, 4],
                  output_palette=[3, 4]),
            _pair([_group([3])], input_palette=[3, 4],
                  output_palette=[3, 4]),
        ],
    }
    iter_997 = CONDITION_REGISTRY[ITER_997_HANDLE]
    assert iter_997(patterns, {}) is True
    assert _matcher()(patterns, {}) is False


def test_iter_997_fires_but_scope_unaligned_three_pairs_rejects() -> None:
    patterns = {
        "pair_analyses": [
            _pair([_group([0, 1])], input_palette=[0, 1, 9],
                  output_palette=[0, 1, 9]),
            _pair([_group([0, 1])], input_palette=[0, 1, 9],
                  output_palette=[0, 1, 9]),
            _pair([_group([0, 1])], input_palette=[0, 1, 9],
                  output_palette=[0, 1, 9]),
        ],
    }
    iter_997 = CONDITION_REGISTRY[ITER_997_HANDLE]
    assert iter_997(patterns, {}) is True
    assert _matcher()(patterns, {}) is False


# ──────────────────────────────────────────────────────────────────────────
# Negative cases inherited from iter 997 rejection.
# ──────────────────────────────────────────────────────────────────────────

def test_whole_grid_cross_pair_variation_rejects() -> None:
    # Iter 991 rejects -> iter 997 rejects -> this rejects.
    patterns = {
        "pair_analyses": [
            _pair([_group([0, 1])], input_palette=[0, 1, 2],
                  output_palette=[0, 1, 2]),
            _pair([_group([0, 1])], input_palette=[0, 1, 3],
                  output_palette=[0, 1, 3]),
        ],
    }
    assert _matcher()(patterns, {}) is False


def test_whole_grid_per_pair_input_output_mismatch_rejects() -> None:
    # Iter 991 rejects on per-pair input != output -> iter 997 rejects.
    patterns = {
        "pair_analyses": [
            _pair([_group([0, 1])], input_palette=[0, 1],
                  output_palette=[0, 1, 2]),
        ],
    }
    assert _matcher()(patterns, {}) is False


def test_per_group_cross_pair_variation_rejects() -> None:
    # Iter 996 rejects on per-blob set varying across pairs -> iter
    # 997 rejects -> this rejects.
    patterns = {
        "pair_analyses": [
            _pair([_group([0, 1])], input_palette=[0, 1, 2],
                  output_palette=[0, 1, 2]),
            _pair([_group([1, 2])], input_palette=[0, 1, 2],
                  output_palette=[0, 1, 2]),
        ],
    }
    assert _matcher()(patterns, {}) is False


def test_per_group_cross_side_mismatch_rejects() -> None:
    # input_colors != output_colors per group -> iter 996 rejects.
    patterns = {
        "pair_analyses": [
            _pair([_group([0, 1],
                          input_colors=[0, 1], output_colors=[2, 3])],
                  input_palette=[0, 1, 2, 3],
                  output_palette=[0, 1, 2, 3]),
        ],
    }
    assert _matcher()(patterns, {}) is False


def test_identity_territory_rejects() -> None:
    # Empty groups -> iter 996 rejects -> iter 997 rejects.
    patterns = {
        "pair_analyses": [
            _pair([], input_palette=[0, 1], output_palette=[0, 1],
                  total_changes=0),
            _pair([], input_palette=[0, 1], output_palette=[0, 1],
                  total_changes=0),
        ],
    }
    assert _matcher()(patterns, {}) is False


# ──────────────────────────────────────────────────────────────────────────
# Fail-closed paths (malformed input).
# ──────────────────────────────────────────────────────────────────────────

def test_empty_patterns_rejects() -> None:
    assert _matcher()({}, {}) is False


def test_non_dict_patterns_rejects() -> None:
    assert _matcher()(None, {}) is False
    assert _matcher()([], {}) is False
    assert _matcher()("not a dict", {}) is False
    assert _matcher()(42, {}) is False


def test_missing_pair_analyses_rejects() -> None:
    assert _matcher()({"other": []}, {}) is False


def test_non_list_pair_analyses_rejects() -> None:
    assert _matcher()({"pair_analyses": "not a list"}, {}) is False
    assert _matcher()({"pair_analyses": None}, {}) is False


def test_empty_pair_analyses_rejects() -> None:
    assert _matcher()({"pair_analyses": []}, {}) is False


def test_non_dict_pair_analysis_rejects() -> None:
    assert _matcher()({"pair_analyses": ["not a dict"]}, {}) is False


def test_missing_input_palette_rejects() -> None:
    # iter 991 rejects on missing input_palette.
    pair = _pair([_group([0, 1])], input_palette=[0, 1],
                 output_palette=[0, 1])
    del pair["input_palette"]
    assert _matcher()({"pair_analyses": [pair]}, {}) is False


def test_missing_output_palette_rejects() -> None:
    pair = _pair([_group([0, 1])], input_palette=[0, 1],
                 output_palette=[0, 1])
    del pair["output_palette"]
    assert _matcher()({"pair_analyses": [pair]}, {}) is False


def test_missing_groups_rejects() -> None:
    pair = _pair([_group([0, 1])], input_palette=[0, 1],
                 output_palette=[0, 1])
    del pair["groups"]
    assert _matcher()({"pair_analyses": [pair]}, {}) is False


def test_bool_in_palette_rejects() -> None:
    # iter 991 rejects bool entries (strict-type posture).
    patterns = {
        "pair_analyses": [
            _pair([_group([0, 1])], input_palette=[True, 1],
                  output_palette=[0, 1]),
        ],
    }
    assert _matcher()(patterns, {}) is False


def test_bool_in_group_colors_rejects() -> None:
    # iter 996 rejects bool entries.
    patterns = {
        "pair_analyses": [
            _pair([_group([0, 1],
                          input_colors=[True, 1],
                          output_colors=[0, 1])],
                  input_palette=[0, 1], output_palette=[0, 1]),
        ],
    }
    assert _matcher()(patterns, {}) is False


def test_out_of_range_color_in_group_rejects() -> None:
    # iter 996 rejects colours outside [0, 9].
    patterns = {
        "pair_analyses": [
            _pair([_group([0, 1],
                          input_colors=[0, 10],
                          output_colors=[0, 1])],
                  input_palette=[0, 1], output_palette=[0, 1]),
        ],
    }
    assert _matcher()(patterns, {}) is False


# ──────────────────────────────────────────────────────────────────────────
# Behavioural contract.
# ──────────────────────────────────────────────────────────────────────────

def test_side_effect_free() -> None:
    patterns = {
        "pair_analyses": [
            _pair([_group([0, 1])], input_palette=[0, 1],
                  output_palette=[0, 1]),
        ],
    }
    snapshot = copy.deepcopy(patterns)
    _matcher()(patterns, {})
    assert patterns == snapshot, (
        "matcher mutated its patterns argument; required to be side-effect-free"
    )


def test_deterministic_across_repeats() -> None:
    patterns = {
        "pair_analyses": [
            _pair([_group([0, 1])], input_palette=[0, 1],
                  output_palette=[0, 1]),
        ],
    }
    first = _matcher()(patterns, {})
    for _ in range(5):
        assert _matcher()(patterns, {}) == first


def test_literal_boolean_return() -> None:
    patterns = {
        "pair_analyses": [
            _pair([_group([0, 1])], input_palette=[0, 1],
                  output_palette=[0, 1]),
        ],
    }
    result = _matcher()(patterns, {})
    assert result is True
    rejected = _matcher()({}, {})
    assert rejected is False


def test_params_ignored() -> None:
    patterns = {
        "pair_analyses": [
            _pair([_group([0, 1])], input_palette=[0, 1],
                  output_palette=[0, 1]),
        ],
    }
    for params in [{}, {"foo": "bar"}, {"min_evidence": 5}, None]:
        # The matcher accepts only dict params per registry contract;
        # the matcher's body passes {} to its inner dispatch so a
        # caller-supplied params is intentionally ignored.
        if isinstance(params, dict):
            assert _matcher()(patterns, params) is True


# ──────────────────────────────────────────────────────────────────────────
# Conjunction / refinement relationships.
# ──────────────────────────────────────────────────────────────────────────

def test_strict_implication_of_iter_997_on_aligned_fixture() -> None:
    patterns = {
        "pair_analyses": [
            _pair([_group([0, 1])], input_palette=[0, 1],
                  output_palette=[0, 1]),
            _pair([_group([0, 1])], input_palette=[0, 1],
                  output_palette=[0, 1]),
        ],
    }
    iter_997 = CONDITION_REGISTRY[ITER_997_HANDLE]
    assert _matcher()(patterns, {}) is True
    assert iter_997(patterns, {}) is True


def test_converse_fails_iter_997_fires_alone() -> None:
    # Iter 997 fires (whole-grid + per-blob each constant) but
    # S_whole != S_blob -- the converse of strict implication.
    patterns = {
        "pair_analyses": [
            _pair([_group([0, 1])], input_palette=[0, 1, 2],
                  output_palette=[0, 1, 2]),
            _pair([_group([0, 1])], input_palette=[0, 1, 2],
                  output_palette=[0, 1, 2]),
        ],
    }
    iter_997 = CONDITION_REGISTRY[ITER_997_HANDLE]
    assert iter_997(patterns, {}) is True
    assert _matcher()(patterns, {}) is False


def test_strict_implication_of_iter_991() -> None:
    patterns = {
        "pair_analyses": [
            _pair([_group([0, 1])], input_palette=[0, 1],
                  output_palette=[0, 1]),
        ],
    }
    iter_991 = CONDITION_REGISTRY[ITER_991_HANDLE]
    assert _matcher()(patterns, {}) is True
    assert iter_991(patterns, {}) is True


def test_strict_implication_of_iter_996() -> None:
    patterns = {
        "pair_analyses": [
            _pair([_group([0, 1])], input_palette=[0, 1],
                  output_palette=[0, 1]),
        ],
    }
    iter_996 = CONDITION_REGISTRY[ITER_996_HANDLE]
    assert _matcher()(patterns, {}) is True
    assert iter_996(patterns, {}) is True


def test_transitive_implication_of_underlying_palette_conjuncts() -> None:
    # When this matcher fires, every underlying single-axis cross-
    # pair-set-constancy palette matcher (iter 185, 989, 990, 994,
    # 995, 195, 196) strictly implied via iter 991 / 996 / 997 should
    # also fire on the same fixture.
    underlying = [
        "output_palette_equals_input",
        "input_palette_constant_across_pairs",
        "output_palette_constant_across_pairs",
        "input_group_palette_constant_across_pairs",
        "output_group_palette_constant_across_pairs",
        "change_input_color_count_per_group_constant_across_pairs",
        "change_output_color_count_per_group_constant_across_pairs",
    ]
    patterns = {
        "pair_analyses": [
            _pair([_group([0, 1])], input_palette=[0, 1],
                  output_palette=[0, 1]),
            _pair([_group([0, 1])], input_palette=[0, 1],
                  output_palette=[0, 1]),
        ],
    }
    assert _matcher()(patterns, {}) is True
    for name in underlying:
        if name not in CONDITION_REGISTRY:
            continue
        matcher = CONDITION_REGISTRY[name]
        assert matcher(patterns, {}) is True, (
            f"transitive implication failed: {name!r} did not fire on "
            f"aligned-fixture even though iter-999 matcher did"
        )


# ──────────────────────────────────────────────────────────────────────────
# recognized_conditions end-to-end inclusion / exclusion.
# ──────────────────────────────────────────────────────────────────────────

def test_recognized_conditions_includes_on_aligned_fixture() -> None:
    from agent.conditions import recognized_conditions
    patterns = {
        "pair_analyses": [
            _pair([_group([0, 1])], input_palette=[0, 1],
                  output_palette=[0, 1]),
            _pair([_group([0, 1])], input_palette=[0, 1],
                  output_palette=[0, 1]),
        ],
    }
    fired = recognized_conditions(patterns)
    assert MATCHER_NAME in fired, (
        f"{MATCHER_NAME!r} must fire on a scope-aligned fixture; "
        f"got {fired!r}"
    )


def test_recognized_conditions_excludes_on_scope_unaligned_fixture() -> None:
    from agent.conditions import recognized_conditions
    patterns = {
        "pair_analyses": [
            _pair([_group([0, 1])], input_palette=[0, 1, 2],
                  output_palette=[0, 1, 2]),
            _pair([_group([0, 1])], input_palette=[0, 1, 2],
                  output_palette=[0, 1, 2]),
        ],
    }
    fired = recognized_conditions(patterns)
    assert MATCHER_NAME not in fired, (
        f"{MATCHER_NAME!r} must NOT fire when S_whole != S_blob; "
        f"got {fired!r}"
    )
    # But iter 997 should still fire on the same fixture -- this is
    # exactly the new semantic content this iter adds beyond iter 997.
    assert ITER_997_HANDLE in fired, (
        f"iter-997 handle must still fire on this fixture; got {fired!r}"
    )


def test_recognized_conditions_excludes_on_identity_territory() -> None:
    from agent.conditions import recognized_conditions
    patterns = {
        "pair_analyses": [
            _pair([], total_changes=0),
            _pair([], total_changes=0),
        ],
    }
    fired = recognized_conditions(patterns)
    assert MATCHER_NAME not in fired


def test_does_not_displace_adjacent_iter_matchers() -> None:
    expected = {
        "input_palette_constant_across_pairs",
        "output_palette_constant_across_pairs",
        "input_output_palette_equal_and_constant_across_pairs",
        "input_output_dimensions_equal_and_constant_across_pairs",
        "input_output_dimensions_and_palette_equal_and_constant_across_pairs",
        "input_group_palette_constant_across_pairs",
        "output_group_palette_constant_across_pairs",
        "input_output_group_palette_equal_and_constant_across_pairs",
        "input_output_group_palette_and_whole_grid_palette_equal_and_constant_across_pairs",
        "input_output_group_palette_and_whole_grid_palette_and_dimensions_equal_and_constant_across_pairs",
        "identity_transformation",
        "output_palette_equals_input",
        "grid_size_changed",
    }
    missing = expected - set(CONDITION_REGISTRY)
    assert not missing, (
        f"adjacent matchers missing post-iter-999: {missing!r}"
    )


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
