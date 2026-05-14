"""
tests/test_consistent_color_mapping_per_group.py -- exercise the
iter-213 matcher ``agent.conditions.consistent_color_mapping_per_group``.

Pins the matcher's contract per the docstring of
``agent/conditions/consistent_color_mapping_per_group.py``: every
group of every example pair carries a per-group function-shaped
(ic -> oc) cross-product, equivalently on set-level data
``len(set(output_colors)) == 1`` per group. Universal over groups
AND pairs; fail-closed on empty / no-group / malformed input.

Runs without pytest:

    python tests/test_consistent_color_mapping_per_group.py

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


MATCHER_NAME = "consistent_color_mapping_per_group"


def _matcher():
    return CONDITION_REGISTRY[MATCHER_NAME]


def _group(input_colors, output_colors, **overrides):
    base = {
        "input_colors": list(input_colors),
        "output_colors": list(output_colors),
        "top_row": 0,
        "top_col": 0,
        "cell_count": max(1, len(input_colors)),
    }
    base.update(overrides)
    return base


def _pair(groups, **overrides):
    base = {
        "input_height": 3,
        "input_width": 3,
        "output_height": 3,
        "output_width": 3,
        "size_match": True,
        "total_changes": sum(g.get("cell_count", 1) for g in groups),
        "num_groups": len(groups),
        "groups": list(groups),
        "input_palette": [0, 1, 2, 3],
        "output_palette": [0, 1, 2, 3],
    }
    base.update(overrides)
    return base


# --------------------------------------------------------------------------
# Smoke / membership tests.
# --------------------------------------------------------------------------

def test_registered_in_global_registry() -> None:
    assert MATCHER_NAME in CONDITION_REGISTRY, (
        f"{MATCHER_NAME!r} not registered; got {sorted(CONDITION_REGISTRY)}"
    )


def test_matcher_is_callable() -> None:
    fn = _matcher()
    assert callable(fn), f"registered entry is not callable: {fn!r}"


# --------------------------------------------------------------------------
# Positive cases.
# --------------------------------------------------------------------------

def test_returns_true_on_singleton_outputs_singleton_inputs() -> None:
    # Trivial per-group function-shape: every group has |oc| == 1.
    patterns = {"pair_analyses": [
        _pair([_group([0], [3]), _group([5], [7])]),
    ]}
    assert _matcher()(patterns, {}) is True


def test_returns_true_on_singleton_output_multi_input() -> None:
    # |ic| > 1, |oc| == 1: cross-product is {ic_i: {oc}} for every
    # ic_i -- function-shape holds (all singletons).
    patterns = {"pair_analyses": [
        _pair([_group([0, 1, 2], [7])]),
    ]}
    assert _matcher()(patterns, {}) is True


def test_returns_true_when_per_group_singletons_differ_across_groups() -> None:
    # Critical separation case from iter 18: per-group |oc| == 1 must
    # fire even when the singletons differ across groups.
    patterns = {"pair_analyses": [
        _pair([_group([0], [3]), _group([1], [4]), _group([2], [5])]),
    ]}
    assert _matcher()(patterns, {}) is True


def test_returns_true_when_per_group_singletons_differ_across_pairs() -> None:
    # Critical separation case from iter 8: per-group |oc| == 1 must
    # fire even when the SAME input colour maps to different singletons
    # in different pairs (per-group projection drops the cross-pair
    # consistency clause).
    patterns = {
        "pair_analyses": [
            _pair([_group([0], [3])]),
            _pair([_group([0], [4])]),  # same ic, different oc -- iter 8 rejects.
        ],
    }
    assert _matcher()(patterns, {}) is True


def test_returns_true_with_multipair_singleton_outputs() -> None:
    patterns = {
        "pair_analyses": [
            _pair([_group([0], [3]), _group([5], [7])]),
            _pair([_group([0], [3]), _group([5], [7])]),
        ],
    }
    assert _matcher()(patterns, {}) is True


def test_returns_true_with_duplicate_entries_in_color_lists() -> None:
    # Color lists are de-duplicated set-wise by the matcher; duplicates
    # in the list must not change the verdict (|set([3, 3])| == 1).
    patterns = {"pair_analyses": [
        _pair([_group([0, 0, 1], [3, 3])]),
    ]}
    assert _matcher()(patterns, {}) is True


# --------------------------------------------------------------------------
# Negative cases.
# --------------------------------------------------------------------------

def test_returns_false_when_any_group_has_multi_output() -> None:
    # |oc| > 1 in a group -- the cross-product binds the ic to a
    # 2-element set, function-shape fails.
    patterns = {"pair_analyses": [
        _pair([_group([0], [3, 4])]),
    ]}
    assert _matcher()(patterns, {}) is False


def test_returns_false_when_one_of_many_groups_has_multi_output() -> None:
    # Universal-over-groups semantic: a single failing group fails the
    # whole task even if other groups are well-formed.
    patterns = {"pair_analyses": [
        _pair([
            _group([0], [3]),       # singleton -- ok
            _group([1, 2], [4, 5]), # multi-output -- offending
            _group([6], [7]),       # singleton -- ok
        ]),
    ]}
    assert _matcher()(patterns, {}) is False


def test_returns_false_when_any_pair_has_offending_group() -> None:
    # Universal-over-pairs: a single failing pair fails the whole
    # task.
    patterns = {
        "pair_analyses": [
            _pair([_group([0], [3])]),
            _pair([_group([0], [3, 4])]),  # offending
            _pair([_group([0], [3])]),
        ],
    }
    assert _matcher()(patterns, {}) is False


def test_returns_false_on_empty_pair_analyses() -> None:
    assert _matcher()({"pair_analyses": []}, {}) is False


def test_returns_false_on_missing_pair_analyses_key() -> None:
    assert _matcher()({}, {}) is False


def test_returns_false_on_non_list_pair_analyses() -> None:
    for bad in (None, 42, "oops", {"a": 1}, (), True):
        assert _matcher()({"pair_analyses": bad}, {}) is False, (
            f"pair_analyses={bad!r} should not fire"
        )


def test_returns_false_on_non_dict_patterns() -> None:
    assert _matcher()(None, {}) is False         # type: ignore[arg-type]
    assert _matcher()([], {}) is False           # type: ignore[arg-type]
    assert _matcher()("oops", {}) is False       # type: ignore[arg-type]
    assert _matcher()(42, {}) is False           # type: ignore[arg-type]


def test_returns_false_when_groups_empty_on_any_pair() -> None:
    # Identity-territory rejection (mirroring iter 8 and the per-group
    # palette-relation matchers iter 200-206).
    patterns = {
        "pair_analyses": [
            _pair([_group([0], [3])]),
            _pair([], num_groups=0, total_changes=0),
        ],
    }
    assert _matcher()(patterns, {}) is False


def test_returns_false_on_missing_groups_key() -> None:
    analysis = _pair([_group([0], [3])])
    del analysis["groups"]
    patterns = {"pair_analyses": [analysis]}
    assert _matcher()(patterns, {}) is False


def test_returns_false_on_non_list_groups() -> None:
    for bad in (None, 42, "oops", {"a": 1}, (), True):
        analysis = _pair([_group([0], [3])])
        analysis["groups"] = bad
        patterns = {"pair_analyses": [analysis]}
        assert _matcher()(patterns, {}) is False, (
            f"groups={bad!r} should not fire"
        )


def test_returns_false_when_any_analysis_is_not_dict() -> None:
    patterns = {
        "pair_analyses": [
            _pair([_group([0], [3])]),
            "not-a-dict",
            _pair([_group([1], [4])]),
        ],
    }
    assert _matcher()(patterns, {}) is False


def test_returns_false_when_any_group_is_not_dict() -> None:
    analysis = _pair([_group([0], [3])])
    analysis["groups"] = [_group([0], [3]), "not-a-dict"]
    patterns = {"pair_analyses": [analysis]}
    assert _matcher()(patterns, {}) is False


# --------------------------------------------------------------------------
# Strict-type-gate cases.
# --------------------------------------------------------------------------

def test_returns_false_when_input_colors_missing() -> None:
    analysis = _pair([_group([0], [3])])
    del analysis["groups"][0]["input_colors"]
    patterns = {"pair_analyses": [analysis]}
    assert _matcher()(patterns, {}) is False


def test_returns_false_when_output_colors_missing() -> None:
    analysis = _pair([_group([0], [3])])
    del analysis["groups"][0]["output_colors"]
    patterns = {"pair_analyses": [analysis]}
    assert _matcher()(patterns, {}) is False


def test_returns_false_when_input_colors_empty() -> None:
    # Extractor contract violation: a non-empty group must have at
    # least one input colour.
    analysis = _pair([_group([0], [3])])
    analysis["groups"][0]["input_colors"] = []
    patterns = {"pair_analyses": [analysis]}
    assert _matcher()(patterns, {}) is False


def test_returns_false_when_output_colors_empty() -> None:
    analysis = _pair([_group([0], [3])])
    analysis["groups"][0]["output_colors"] = []
    patterns = {"pair_analyses": [analysis]}
    assert _matcher()(patterns, {}) is False


def test_returns_false_when_input_colors_not_list() -> None:
    for bad in (None, 42, "oops", {"a": 1}, (0,), True, {0}):
        analysis = _pair([_group([0], [3])])
        analysis["groups"][0]["input_colors"] = bad
        patterns = {"pair_analyses": [analysis]}
        assert _matcher()(patterns, {}) is False, (
            f"input_colors={bad!r} should not fire"
        )


def test_returns_false_when_output_colors_not_list() -> None:
    for bad in (None, 42, "oops", {"a": 1}, (3,), True, {3}):
        analysis = _pair([_group([0], [3])])
        analysis["groups"][0]["output_colors"] = bad
        patterns = {"pair_analyses": [analysis]}
        assert _matcher()(patterns, {}) is False, (
            f"output_colors={bad!r} should not fire"
        )


def test_returns_false_when_color_list_contains_bool() -> None:
    # bools are an int subclass; the strict-type gate rejects them
    # (same posture as iter 14 / 18 / 200-206).
    analysis = _pair([_group([0, True], [3])])
    patterns = {"pair_analyses": [analysis]}
    assert _matcher()(patterns, {}) is False

    analysis2 = _pair([_group([0], [3, False])])
    patterns2 = {"pair_analyses": [analysis2]}
    assert _matcher()(patterns2, {}) is False


def test_returns_false_when_color_list_contains_non_int() -> None:
    analysis = _pair([_group([0, "1"], [3])])
    patterns = {"pair_analyses": [analysis]}
    assert _matcher()(patterns, {}) is False

    analysis2 = _pair([_group([0], [3.0])])
    patterns2 = {"pair_analyses": [analysis2]}
    assert _matcher()(patterns2, {}) is False


def test_returns_false_when_color_out_of_range() -> None:
    # Per-group color values must be in [0, 9]; iter-180 erase
    # sentinel 13 is rejected on the per-group projection (the
    # whole-grid palette matchers tolerate it, the per-group ones do
    # not -- mirroring iter 205 / 206 strict-range gate).
    analysis = _pair([_group([0], [13])])
    patterns = {"pair_analyses": [analysis]}
    assert _matcher()(patterns, {}) is False

    analysis2 = _pair([_group([-1], [3])])
    patterns2 = {"pair_analyses": [analysis2]}
    assert _matcher()(patterns2, {}) is False


# --------------------------------------------------------------------------
# Behavioural-contract cases.
# --------------------------------------------------------------------------

def test_is_side_effect_free_on_inputs() -> None:
    patterns = {"pair_analyses": [
        _pair([_group([0], [3]), _group([5, 6], [7])]),
    ]}
    params = {"unused": 1}
    before_p = copy.deepcopy(patterns)
    before_q = copy.deepcopy(params)
    _matcher()(patterns, params)
    assert patterns == before_p, "matcher mutated patterns"
    assert params == before_q, "matcher mutated params"


def test_is_deterministic_across_repeats() -> None:
    patterns = {"pair_analyses": [_pair([_group([0], [3])])]}
    results = [_matcher()(patterns, {}) for _ in range(5)]
    assert len(set(results)) == 1, f"non-deterministic outputs: {results}"


def test_returned_value_is_boolean_not_truthy() -> None:
    # recognized_conditions filters on ``match(...) is True`` exactly,
    # so the matcher must return literal Booleans.
    out_true = _matcher()({"pair_analyses": [_pair([_group([0], [3])])]}, {})
    out_false = _matcher()({"pair_analyses": [_pair([_group([0], [3, 4])])]}, {})
    assert out_true is True, f"expected literal True, got {out_true!r}"
    assert out_false is False, f"expected literal False, got {out_false!r}"


def test_ignores_dimensional_fields() -> None:
    # Dimensional fields are orthogonal -- arbitrary dim combinations
    # must not affect the matcher's verdict.
    analysis = _pair([_group([0], [3])], input_height=7, input_width=9,
                     output_height=2, output_width=3, size_match=False)
    patterns = {"pair_analyses": [analysis]}
    assert _matcher()(patterns, {}) is True


def test_ignores_palette_fields() -> None:
    # Whole-grid palette fields are orthogonal -- this matcher only
    # inspects per-group color lists.
    analysis = _pair([_group([0], [3])],
                     input_palette=[9, 9, 9],
                     output_palette=[1, 1, 1])
    patterns = {"pair_analyses": [analysis]}
    assert _matcher()(patterns, {}) is True


# --------------------------------------------------------------------------
# Orthogonality / refinement / mutual-exclusion matrix against existing
# axes.
# --------------------------------------------------------------------------

def test_strict_implication_of_iter_8_consistent_color_mapping() -> None:
    # Strict refinement: iter 8 (whole-task function-shape) fires =>
    # this matcher fires. Converse fails on per-group function-shape
    # with cross-pair contradictions.
    iter8 = CONDITION_REGISTRY["consistent_color_mapping"]

    # Whole-task function-shape: iter 8 fires, this matcher also
    # fires.
    p1 = {"pair_analyses": [
        _pair([_group([0], [3]), _group([5], [7])]),
        _pair([_group([0], [3]), _group([5], [7])]),
    ]}
    assert iter8(p1, {}) is True and _matcher()(p1, {}) is True

    # Per-group function-shape but global contradiction: ic=0 maps to
    # oc=3 in pair 0 and oc=4 in pair 1. Iter 8 rejects (global map
    # has {0: {3, 4}}); this matcher fires (each group internally
    # singleton-output).
    p2 = {"pair_analyses": [
        _pair([_group([0], [3])]),
        _pair([_group([0], [4])]),
    ]}
    assert iter8(p2, {}) is False and _matcher()(p2, {}) is True


def test_strict_implication_of_iter_18_output_color_uniform() -> None:
    # Strict refinement: iter 18 (per-group |oc| == 1 AND singletons
    # identical across all groups) fires => this matcher fires.
    # Converse fails when singletons differ across groups.
    iter18 = CONDITION_REGISTRY["output_color_uniform"]

    # Iter 18 territory: every group has the same singleton output.
    p1 = {"pair_analyses": [
        _pair([_group([0], [3]), _group([5], [3])]),
    ]}
    assert iter18(p1, {}) is True and _matcher()(p1, {}) is True

    # Per-group singleton with varying values: this matcher fires,
    # iter 18 rejects.
    p2 = {"pair_analyses": [
        _pair([_group([0], [3]), _group([5], [7])]),
    ]}
    assert iter18(p2, {}) is False and _matcher()(p2, {}) is True


def test_mutual_exclusion_with_identity_transformation() -> None:
    ident = CONDITION_REGISTRY["identity_transformation"]
    p = {"pair_analyses": [_pair([], num_groups=0, total_changes=0)]}
    # Identity fires; this matcher rejects (no groups).
    assert ident(p, {}) is True and _matcher()(p, {}) is False


def test_strict_implication_of_sequential_recoloring() -> None:
    # Iter 10 (sequential_recoloring) fires => this matcher fires:
    # iter 10 requires per-group singleton outputs forming a
    # contiguous range, so per-group |oc| == 1 holds.
    seq = CONDITION_REGISTRY["sequential_recoloring"]
    p = {"pair_analyses": [
        _pair([_group([0], [3]), _group([1], [4]), _group([2], [5])]),
        _pair([_group([0], [3]), _group([1], [4]), _group([2], [5])]),
    ]}
    assert seq(p, {}) is True and _matcher()(p, {}) is True

    # Per-group function-shape with non-contiguous singletons: this
    # matcher fires, iter 10 rejects.
    p2 = {"pair_analyses": [
        _pair([_group([0], [3]), _group([1], [7])]),
        _pair([_group([0], [3]), _group([1], [7])]),
    ]}
    assert seq(p2, {}) is False and _matcher()(p2, {}) is True


def test_independent_of_input_color_uniform() -> None:
    # Iter 14 (per-group |ic| == 1) is orthogonal: this matcher
    # constrains the output side, iter 14 the input side. Both can
    # fire (|ic| == |oc| == 1) or only one fire.
    iter14 = CONDITION_REGISTRY["input_color_uniform"]

    # Both fire.
    p1 = {"pair_analyses": [_pair([_group([0], [3])])]}
    assert iter14(p1, {}) is True and _matcher()(p1, {}) is True

    # Iter 14 fires, this matcher rejects (|oc| > 1).
    p2 = {"pair_analyses": [_pair([_group([0], [3, 4])])]}
    assert iter14(p2, {}) is True and _matcher()(p2, {}) is False

    # This matcher fires (|oc| == 1), iter 14 rejects (|ic| > 1).
    p3 = {"pair_analyses": [_pair([_group([0, 1, 2], [3])])]}
    assert iter14(p3, {}) is False and _matcher()(p3, {}) is True


def test_independent_of_per_group_palette_equality() -> None:
    # Iter 201 (per-group equality) is orthogonal in general; this
    # matcher's |oc| == 1 gate intersects iter 201 only at |ic| ==
    # |oc| == 1 with input_colors == output_colors.
    eq = CONDITION_REGISTRY["output_colors_equals_input_colors_per_group"]

    # Both fire: equality with both singletons.
    p1 = {"pair_analyses": [_pair([_group([3], [3])])]}
    assert eq(p1, {}) is True and _matcher()(p1, {}) is True

    # Iter 201 fires, this matcher rejects (multi-element equality).
    p2 = {"pair_analyses": [_pair([_group([3, 4], [3, 4])])]}
    assert eq(p2, {}) is True and _matcher()(p2, {}) is False


def test_recognized_conditions_includes_per_group_function_shape() -> None:
    from agent.conditions import recognized_conditions
    patterns = {"pair_analyses": [
        _pair([_group([0], [3]), _group([5], [7])]),
    ]}
    fired = recognized_conditions(patterns)
    assert MATCHER_NAME in fired, (
        f"{MATCHER_NAME!r} did not fire on a per-group function-shape "
        f"patterns dict; got {fired!r}"
    )


# --------------------------------------------------------------------------
# Test runner (dependency-free, same style as the other tests).
# --------------------------------------------------------------------------

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
