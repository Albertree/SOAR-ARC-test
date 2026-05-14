"""
tests/test_singleton_recolor.py -- exercise the iter-216 matcher
``agent.conditions.singleton_recolor``.

Pins the matcher's contract per the docstring of
``agent/conditions/singleton_recolor.py``: every group of every example
pair has ``len(input_colors) == 1`` AND ``len(output_colors) == 1``,
AND all single input colours across all groups in all pairs are bit-
identical, AND all single output colours across all groups in all
pairs are bit-identical -- the simplest single-global-recolour cell,
the STRICT CONJUNCTION of iter 14 (``input_color_uniform``) AND iter
18 (``output_color_uniform``). Universal over groups AND pairs; fail-
closed on empty / no-group / malformed input.

Runs without pytest:

    python tests/test_singleton_recolor.py

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


MATCHER_NAME = "singleton_recolor"


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

def test_returns_true_on_canonical_global_recolor() -> None:
    # The simplest single-global-recolour cell: every group has the
    # same single input C and same single output K.
    patterns = {"pair_analyses": [
        _pair([_group([0], [3]), _group([0], [3])]),
    ]}
    assert _matcher()(patterns, {}) is True


def test_returns_true_multipair_same_global_C_K() -> None:
    # Cross-pair identity: C and K must be the same across all pairs.
    patterns = {"pair_analyses": [
        _pair([_group([0], [3])]),
        _pair([_group([0], [3]), _group([0], [3])]),
        _pair([_group([0], [3])]),
    ]}
    assert _matcher()(patterns, {}) is True


def test_returns_true_when_C_equals_K_singleton() -> None:
    # The |ic| == |oc| == 1 cell admits the "no-change" case (C == K),
    # e.g. groups recolour 3 -> 3 globally. Iter 201 (per-group
    # equality) fires too; this matcher does not care -- it just
    # requires both sides to be global singletons.
    patterns = {"pair_analyses": [
        _pair([_group([3], [3]), _group([3], [3])]),
    ]}
    assert _matcher()(patterns, {}) is True


def test_returns_true_on_single_group_single_pair() -> None:
    patterns = {"pair_analyses": [_pair([_group([7], [2])])]}
    assert _matcher()(patterns, {}) is True


# --------------------------------------------------------------------------
# Negative cases.
# --------------------------------------------------------------------------

def test_returns_false_when_input_singletons_differ_across_groups() -> None:
    # Per-group singletons differ across groups on the input side:
    # iter 215 fires, this matcher rejects (cross-group identity on
    # the input side required).
    patterns = {"pair_analyses": [
        _pair([_group([3], [0]), _group([5], [0])]),
    ]}
    assert _matcher()(patterns, {}) is False


def test_returns_false_when_output_singletons_differ_across_groups() -> None:
    patterns = {"pair_analyses": [
        _pair([_group([3], [0]), _group([3], [1])]),
    ]}
    assert _matcher()(patterns, {}) is False


def test_returns_false_when_singletons_differ_across_pairs() -> None:
    # Cross-pair identity required: pair 0 paints 0 -> 3, pair 1 paints
    # 1 -> 4. Iter 215 fires (per-group bijective singleton), this
    # matcher rejects (global C and K not bit-identical across pairs).
    patterns = {"pair_analyses": [
        _pair([_group([0], [3])]),
        _pair([_group([1], [4])]),
    ]}
    assert _matcher()(patterns, {}) is False


def test_returns_false_when_any_group_has_multi_input() -> None:
    # |ic| > 1 in any group fails regardless of |oc|.
    patterns = {"pair_analyses": [
        _pair([_group([0, 1], [3])]),
    ]}
    assert _matcher()(patterns, {}) is False


def test_returns_false_when_any_group_has_multi_output() -> None:
    # |oc| > 1 in any group fails regardless of |ic|.
    patterns = {"pair_analyses": [
        _pair([_group([0], [3, 4])]),
    ]}
    assert _matcher()(patterns, {}) is False


def test_returns_false_when_one_of_many_groups_violates() -> None:
    # Universal-over-groups semantic: a single failing group fails the
    # whole task even if other groups are well-formed.
    patterns = {"pair_analyses": [
        _pair([
            _group([0], [3]),       # singleton -- ok
            _group([1, 2], [3]),    # multi-input -- offending
            _group([0], [3]),       # singleton -- ok
        ]),
    ]}
    assert _matcher()(patterns, {}) is False


def test_returns_false_when_duplicate_entries_in_color_list() -> None:
    # Inherits iter 14 / iter 18's ``len() == 1`` posture (not
    # ``len(set()) == 1``): duplicate-entry lists are extractor
    # contract violations and must be rejected. This is a deliberate
    # divergence from iter 215's set-level posture -- see the docstring
    # of ``singleton_recolor.py`` for the rationale.
    patterns = {"pair_analyses": [_pair([_group([3, 3], [0])])]}
    assert _matcher()(patterns, {}) is False

    patterns2 = {"pair_analyses": [_pair([_group([3], [0, 0])])]}
    assert _matcher()(patterns2, {}) is False


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
    # Identity-territory rejection (mirroring iter 14 / 18 and iter 215).
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
            _pair([_group([0], [3])]),
        ],
    }
    assert _matcher()(patterns, {}) is False


def test_returns_false_when_any_group_is_not_dict() -> None:
    analysis = _pair([_group([0], [3])])
    analysis["groups"] = [_group([0], [3]), "not-a-dict"]
    patterns = {"pair_analyses": [analysis]}
    assert _matcher()(patterns, {}) is False


# --------------------------------------------------------------------------
# Strict-type-gate cases (inherited from iter 14 / iter 18 posture).
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
    for bad in (None, 42, "oops", {"a": 1}, (0,), {0}):
        analysis = _pair([_group([0], [3])])
        analysis["groups"][0]["input_colors"] = bad
        patterns = {"pair_analyses": [analysis]}
        assert _matcher()(patterns, {}) is False, (
            f"input_colors={bad!r} should not fire"
        )


def test_returns_false_when_output_colors_not_list() -> None:
    for bad in (None, 42, "oops", {"a": 1}, (3,), {3}):
        analysis = _pair([_group([0], [3])])
        analysis["groups"][0]["output_colors"] = bad
        patterns = {"pair_analyses": [analysis]}
        assert _matcher()(patterns, {}) is False, (
            f"output_colors={bad!r} should not fire"
        )


# --------------------------------------------------------------------------
# Behavioural-contract cases.
# --------------------------------------------------------------------------

def test_is_side_effect_free_on_inputs() -> None:
    patterns = {"pair_analyses": [
        _pair([_group([0], [3]), _group([0], [3])]),
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
    out_false = _matcher()({"pair_analyses": [_pair([_group([0, 1], [3])])]}, {})
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

def test_strict_refinement_of_iter_14_input_color_uniform() -> None:
    # Strict refinement: this matcher fires => iter 14 fires (the
    # whole-task input singleton-and-identity claim is a precondition
    # of this matcher). Converse fails when output side is multi-
    # colour (iter 14 fires, this matcher rejects).
    iter14 = CONDITION_REGISTRY["input_color_uniform"]

    # This matcher fires => iter 14 fires.
    p1 = {"pair_analyses": [_pair([_group([0], [3])])]}
    assert _matcher()(p1, {}) is True and iter14(p1, {}) is True

    # Iter 14 fires (input singleton-and-identity), this matcher
    # rejects (output side has two distinct singletons across groups).
    p2 = {"pair_analyses": [
        _pair([_group([0], [3]), _group([0], [4])]),
    ]}
    assert iter14(p2, {}) is True and _matcher()(p2, {}) is False


def test_strict_refinement_of_iter_18_output_color_uniform() -> None:
    # Strict refinement: this matcher fires => iter 18 fires (the
    # whole-task output singleton-and-identity claim is a precondition
    # of this matcher). Converse fails when input side is multi-
    # colour (iter 18 fires, this matcher rejects).
    iter18 = CONDITION_REGISTRY["output_color_uniform"]

    # This matcher fires => iter 18 fires.
    p1 = {"pair_analyses": [_pair([_group([0], [3])])]}
    assert _matcher()(p1, {}) is True and iter18(p1, {}) is True

    # Iter 18 fires (output singleton-and-identity), this matcher
    # rejects (input side has two distinct singletons across groups).
    p2 = {"pair_analyses": [
        _pair([_group([0], [3]), _group([1], [3])]),
    ]}
    assert iter18(p2, {}) is True and _matcher()(p2, {}) is False


def test_strict_refinement_of_iter_215_singleton_recolor_per_group() -> None:
    # Strict refinement: this matcher fires => iter 215 fires (per-
    # group |ic| == |oc| == 1 is a precondition of the whole-task
    # version). Converse fails when per-group singletons differ
    # across groups (iter 215 fires, this matcher rejects).
    iter215 = CONDITION_REGISTRY["singleton_recolor_per_group"]

    # This matcher fires => iter 215 fires.
    p1 = {"pair_analyses": [_pair([_group([0], [3]), _group([0], [3])])]}
    assert _matcher()(p1, {}) is True and iter215(p1, {}) is True

    # Iter 215 fires (per-group bijective singleton), this matcher
    # rejects (singletons differ across groups -- no cross-group
    # identity).
    p2 = {"pair_analyses": [
        _pair([_group([3], [0]), _group([4], [1])]),
    ]}
    assert iter215(p2, {}) is True and _matcher()(p2, {}) is False


def test_iter_14_AND_iter_18_jointly_equivalent_to_this_matcher() -> None:
    # The whole-task projection is EXACTLY the conjunction of iter 14
    # and iter 18: on every well-formed input, this matcher fires iff
    # iter 14 fires AND iter 18 fires.
    iter14 = CONDITION_REGISTRY["input_color_uniform"]
    iter18 = CONDITION_REGISTRY["output_color_uniform"]

    cases = [
        # Both fire => this matcher fires.
        {"pair_analyses": [_pair([_group([0], [3]), _group([0], [3])])]},
        # iter 14 fires, iter 18 rejects => this matcher rejects.
        {"pair_analyses": [_pair([_group([0], [3]), _group([0], [4])])]},
        # iter 18 fires, iter 14 rejects => this matcher rejects.
        {"pair_analyses": [_pair([_group([0], [3]), _group([1], [3])])]},
        # neither fires => this matcher rejects.
        {"pair_analyses": [_pair([_group([0, 1], [3, 4])])]},
    ]
    for case in cases:
        v14 = iter14(case, {})
        v18 = iter18(case, {})
        vme = _matcher()(case, {})
        assert vme is (v14 and v18), (
            f"conjunction equivalence failed on {case!r}: "
            f"iter14={v14}, iter18={v18}, this={vme}"
        )


def test_strict_refinement_of_iter_8_consistent_color_mapping() -> None:
    # Strict refinement: this matcher fires => iter 8 fires (singleton
    # map {C -> K} is trivially function-shaped). Converse fails on a
    # multi-pair forward function-shape (e.g. 0 -> 3, 5 -> 7).
    iter8 = CONDITION_REGISTRY["consistent_color_mapping"]

    # This matcher fires => iter 8 fires.
    p1 = {"pair_analyses": [_pair([_group([0], [3])])]}
    assert _matcher()(p1, {}) is True and iter8(p1, {}) is True

    # Iter 8 fires (forward function-shape), this matcher rejects
    # (multiple distinct (in, out) pairs).
    p2 = {"pair_analyses": [_pair([_group([0], [3]), _group([5], [7])])]}
    assert iter8(p2, {}) is True and _matcher()(p2, {}) is False


def test_mutual_exclusion_with_identity_transformation() -> None:
    ident = CONDITION_REGISTRY["identity_transformation"]
    p = {"pair_analyses": [_pair([], num_groups=0, total_changes=0)]}
    # Identity fires; this matcher rejects (no groups).
    assert ident(p, {}) is True and _matcher()(p, {}) is False


def test_mutual_exclusion_with_iter_10_multi_output() -> None:
    # Iter 10 (sequential_recoloring) requires per-group |oc| == 1
    # with the singletons forming a contiguous range. With >= 2
    # distinct outputs (length-2+ range), iter 10 fires but this
    # matcher rejects.
    iter10 = CONDITION_REGISTRY["sequential_recoloring"]

    # Length-3 contiguous range: iter 10 fires, this matcher rejects
    # (output singletons differ across groups).
    p = {"pair_analyses": [
        _pair([_group([0], [3]), _group([1], [4]), _group([2], [5])]),
        _pair([_group([0], [3]), _group([1], [4]), _group([2], [5])]),
    ]}
    assert iter10(p, {}) is True and _matcher()(p, {}) is False


def test_recognized_conditions_includes_singleton_recolor() -> None:
    from agent.conditions import recognized_conditions
    patterns = {"pair_analyses": [
        _pair([_group([0], [3]), _group([0], [3])]),
    ]}
    fired = recognized_conditions(patterns)
    assert MATCHER_NAME in fired, (
        f"{MATCHER_NAME!r} did not fire on a single-global-recolour "
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
