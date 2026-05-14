"""
tests/test_inverse_consistent_color_mapping.py -- exercise the iter-332
matcher ``agent.conditions.inverse_consistent_color_mapping``.

Pins the matcher's contract per
``agent/conditions/inverse_consistent_color_mapping.py`` docstring:
every observed output colour in change-cell groups maps from exactly
one input colour across all pairs, with a non-empty accumulated
inverse mapping. The strict symmetric dual of iter 8
(``consistent_color_mapping``) on the inverse-function-shape axis.

Runs without pytest:

    python tests/test_inverse_consistent_color_mapping.py

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


MATCHER_NAME = "inverse_consistent_color_mapping"


def _matcher():
    return CONDITION_REGISTRY[MATCHER_NAME]


def _group(ic, oc, **overrides):
    base = {
        "input_colors": list(ic),
        "output_colors": list(oc),
        "positions": [(0, 0)],
        "top_row": 0,
        "top_col": 0,
        "cell_count": 1,
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
        "input_palette": [0, 1, 2],
        "output_palette": [0, 1, 2],
        "groups": list(groups),
        "num_groups": len(groups),
        "total_changes": sum(g.get("cell_count", 1) for g in groups),
    }
    base.update(overrides)
    return base


# ──────────────────────────────────────────────────────────────────────────
# Smoke / membership tests.
# ──────────────────────────────────────────────────────────────────────────

def test_registered_in_global_registry() -> None:
    assert MATCHER_NAME in CONDITION_REGISTRY, (
        f"{MATCHER_NAME!r} not registered; got {sorted(CONDITION_REGISTRY)}"
    )


def test_matcher_is_callable() -> None:
    fn = _matcher()
    assert callable(fn), f"registered entry is not callable: {fn!r}"


# ──────────────────────────────────────────────────────────────────────────
# Positive cases -- inverse function-shape on the accumulated change-cell
# mapping.
# ──────────────────────────────────────────────────────────────────────────

def test_returns_true_on_uniform_one_to_one_mapping() -> None:
    # Bijection (forward AND inverse function-shape): every output
    # comes from exactly one input. Both iter 8 and this matcher fire.
    patterns = {
        "pair_analyses": [
            _pair([_group([0], [3])]),
            _pair([_group([0], [3])]),
        ],
    }
    assert _matcher()(patterns, {}) is True


def test_returns_true_on_multiple_distinct_one_to_one_pairs() -> None:
    patterns = {
        "pair_analyses": [
            _pair([_group([0], [3]), _group([1], [4])]),
            _pair([_group([0], [3]), _group([1], [4])]),
        ],
    }
    assert _matcher()(patterns, {}) is True


def test_returns_true_when_forward_is_one_to_many_but_inverse_is_function() -> None:
    # Mutual-exclusion witness vs iter 8: forward is NOT function
    # (input 0 maps to BOTH 3 and 4), but inverse IS function (each
    # output has a unique input). THIS matcher fires; iter 8 rejects.
    fwd = CONDITION_REGISTRY["consistent_color_mapping"]
    patterns = {
        "pair_analyses": [
            _pair([_group([0], [3, 4])]),
            _pair([_group([0], [3, 4])]),
        ],
    }
    assert _matcher()(patterns, {}) is True
    assert fwd(patterns, {}) is False


def test_returns_true_across_pairs_when_inverse_is_function_globally() -> None:
    # Forward across pairs is one-to-many on input 0 (maps to {3} in
    # pair 0 and {4} in pair 1), but inverse is one-to-one (3 only
    # comes from 0; 4 only comes from 0). Wait -- inverse({3}) = {0},
    # inverse({4}) = {0} -- inverse IS function-shape (each output has
    # ONE input preimage). THIS matcher fires; iter 8 rejects.
    fwd = CONDITION_REGISTRY["consistent_color_mapping"]
    patterns = {
        "pair_analyses": [
            _pair([_group([0], [3])]),
            _pair([_group([0], [4])]),
        ],
    }
    assert _matcher()(patterns, {}) is True
    assert fwd(patterns, {}) is False


def test_returns_true_on_palette_permutation_witness() -> None:
    # Bijection + palette equality (iter 330's territory). Strict-
    # implication: iter 330 fires => this matcher fires.
    perm = CONDITION_REGISTRY["output_palette_is_permutation_of_input_palette"]
    patterns = {
        "pair_analyses": [
            _pair([_group([0], [1]), _group([1], [0])],
                  input_palette=[0, 1], output_palette=[0, 1]),
            _pair([_group([0], [1]), _group([1], [0])],
                  input_palette=[0, 1], output_palette=[0, 1]),
        ],
    }
    assert _matcher()(patterns, {}) is True
    assert perm(patterns, {}) is True


# ──────────────────────────────────────────────────────────────────────────
# Negative cases -- inverse-function-shape violations.
# ──────────────────────────────────────────────────────────────────────────

def test_returns_false_when_two_inputs_map_to_same_output() -> None:
    # Inverse violation: output 3 has two distinct input preimages
    # ({0, 1}). This is the inverse non-function-shape cell -- iter 8
    # may still fire (each input has one output) but THIS matcher
    # rejects. Co-witness: iter 8 IS function on this fixture.
    fwd = CONDITION_REGISTRY["consistent_color_mapping"]
    patterns = {
        "pair_analyses": [
            _pair([_group([0], [3]), _group([1], [3])]),
            _pair([_group([0], [3]), _group([1], [3])]),
        ],
    }
    assert _matcher()(patterns, {}) is False
    assert fwd(patterns, {}) is True


def test_returns_false_when_collapse_across_pairs() -> None:
    # Inverse collapse across pairs: pair 0 has input 0 -> output 3,
    # pair 1 has input 1 -> output 3. The same output 3 has preimages
    # {0, 1}. Inverse rejects.
    patterns = {
        "pair_analyses": [
            _pair([_group([0], [3])]),
            _pair([_group([1], [3])]),
        ],
    }
    assert _matcher()(patterns, {}) is False


def test_returns_false_on_empty_pair_analyses() -> None:
    patterns = {"pair_analyses": []}
    assert _matcher()(patterns, {}) is False


def test_returns_false_on_missing_pair_analyses() -> None:
    assert _matcher()({}, {}) is False


def test_returns_false_on_zero_groups_per_pair() -> None:
    # No observations -> empty inverse mapping -> empty-evidence
    # rejection (mirrors iter 8 posture; identity territory is handled
    # by iter 13).
    patterns = {"pair_analyses": [_pair([]), _pair([])]}
    assert _matcher()(patterns, {}) is False


def test_returns_false_on_non_dict_patterns() -> None:
    assert _matcher()(None, {}) is False         # type: ignore[arg-type]
    assert _matcher()([], {}) is False           # type: ignore[arg-type]
    assert _matcher()("oops", {}) is False       # type: ignore[arg-type]
    assert _matcher()(42, {}) is False           # type: ignore[arg-type]


def test_returns_false_on_non_list_pair_analyses() -> None:
    for bad in (None, 42, "oops", {"a": 1}, (), True):
        patterns = {"pair_analyses": bad}
        assert _matcher()(patterns, {}) is False, (
            f"pair_analyses={bad!r} should not fire"
        )


def test_returns_false_when_analysis_is_not_dict() -> None:
    patterns = {"pair_analyses": ["not-a-dict"]}
    assert _matcher()(patterns, {}) is False


def test_returns_false_when_groups_field_is_not_list() -> None:
    for bad in (None, 42, "oops", {"a": 1}, (), True):
        patterns = {"pair_analyses": [{"groups": bad}]}
        assert _matcher()(patterns, {}) is False, (
            f"groups={bad!r} should not fire"
        )


def test_returns_false_when_group_is_not_dict() -> None:
    patterns = {"pair_analyses": [{"groups": ["not-a-dict"]}]}
    assert _matcher()(patterns, {}) is False


# ──────────────────────────────────────────────────────────────────────────
# Strict-type-gate cases.
# ──────────────────────────────────────────────────────────────────────────

def test_returns_false_when_input_colors_missing() -> None:
    g = _group([0], [3])
    del g["input_colors"]
    patterns = {"pair_analyses": [_pair([g])]}
    assert _matcher()(patterns, {}) is False


def test_returns_false_when_output_colors_missing() -> None:
    g = _group([0], [3])
    del g["output_colors"]
    patterns = {"pair_analyses": [_pair([g])]}
    assert _matcher()(patterns, {}) is False


def test_returns_false_when_input_colors_is_not_list() -> None:
    for bad in (None, 42, "oops", {"a": 1}, (0,), True):
        g = _group([0], [3])
        g["input_colors"] = bad
        patterns = {"pair_analyses": [_pair([g])]}
        assert _matcher()(patterns, {}) is False, (
            f"input_colors={bad!r} should not fire"
        )


def test_returns_false_when_output_colors_is_not_list() -> None:
    for bad in (None, 42, "oops", {"a": 1}, (3,), True):
        g = _group([0], [3])
        g["output_colors"] = bad
        patterns = {"pair_analyses": [_pair([g])]}
        assert _matcher()(patterns, {}) is False, (
            f"output_colors={bad!r} should not fire"
        )


def test_returns_false_when_input_colors_empty() -> None:
    g = _group([0], [3])
    g["input_colors"] = []
    patterns = {"pair_analyses": [_pair([g])]}
    assert _matcher()(patterns, {}) is False


def test_returns_false_when_output_colors_empty() -> None:
    g = _group([0], [3])
    g["output_colors"] = []
    patterns = {"pair_analyses": [_pair([g])]}
    assert _matcher()(patterns, {}) is False


def test_returns_false_when_input_colors_contains_bool() -> None:
    g = _group([0], [3])
    g["input_colors"] = [0, True]
    patterns = {"pair_analyses": [_pair([g])]}
    assert _matcher()(patterns, {}) is False


def test_returns_false_when_output_colors_contains_bool() -> None:
    g = _group([0], [3])
    g["output_colors"] = [3, False]
    patterns = {"pair_analyses": [_pair([g])]}
    assert _matcher()(patterns, {}) is False


def test_returns_false_on_out_of_range_color() -> None:
    g = _group([0], [3])
    g["output_colors"] = [3, 10]
    patterns = {"pair_analyses": [_pair([g])]}
    assert _matcher()(patterns, {}) is False

    g2 = _group([0], [3])
    g2["input_colors"] = [-1, 0]
    patterns2 = {"pair_analyses": [_pair([g2])]}
    assert _matcher()(patterns2, {}) is False


def test_returns_false_on_non_int_color() -> None:
    g = _group([0], [3])
    g["output_colors"] = [3, "4"]
    patterns = {"pair_analyses": [_pair([g])]}
    assert _matcher()(patterns, {}) is False

    g2 = _group([0], [3])
    g2["input_colors"] = [0.0, 1.0]
    patterns2 = {"pair_analyses": [_pair([g2])]}
    assert _matcher()(patterns2, {}) is False


# ──────────────────────────────────────────────────────────────────────────
# Behavioural-contract cases.
# ──────────────────────────────────────────────────────────────────────────

def test_is_side_effect_free_on_inputs() -> None:
    patterns = {
        "pair_analyses": [
            _pair([_group([0], [3]), _group([1], [4])]),
            _pair([_group([0], [3]), _group([1], [4])]),
        ],
    }
    params = {"unused": 1}
    before_p = copy.deepcopy(patterns)
    before_q = copy.deepcopy(params)
    _matcher()(patterns, params)
    assert patterns == before_p, "matcher mutated patterns"
    assert params == before_q, "matcher mutated params"


def test_is_deterministic_across_repeats() -> None:
    patterns = {
        "pair_analyses": [_pair([_group([0], [3])])],
    }
    results = [_matcher()(patterns, {}) for _ in range(5)]
    assert len(set(results)) == 1, f"non-deterministic outputs: {results}"


def test_returned_value_is_boolean_not_truthy() -> None:
    # recognized_conditions filters on ``match(...) is True`` exactly.
    out_true = _matcher()({"pair_analyses": [_pair([_group([0], [3])])]}, {})
    out_false = _matcher()(
        {"pair_analyses": [_pair([_group([0], [3]), _group([1], [3])])]},
        {},
    )
    assert out_true is True, f"expected literal True, got {out_true!r}"
    assert out_false is False, f"expected literal False, got {out_false!r}"


def test_params_ignored() -> None:
    patterns = {"pair_analyses": [_pair([_group([0], [3])])]}
    assert _matcher()(patterns, {}) is True
    assert _matcher()(patterns, {"magic": 1}) is True
    assert _matcher()(patterns, {"empty": True}) is True


# ──────────────────────────────────────────────────────────────────────────
# Orthogonality / mutual-exclusion matrix against existing axes.
# ──────────────────────────────────────────────────────────────────────────

def test_strict_implication_by_palette_permutation() -> None:
    # iter 330 (palette permutation) STRICTLY IMPLIES this matcher
    # (its third clause is exactly inverse function-shape). The
    # converse does NOT hold: a task with inverse function-shape but
    # palette inequality fires this matcher and rejects iter 330.
    perm = CONDITION_REGISTRY["output_palette_is_permutation_of_input_palette"]

    # iter 330 fires (palette-equal 2-cycle swap) -- this matcher fires.
    p1 = {
        "pair_analyses": [
            _pair([_group([0], [1]), _group([1], [0])],
                  input_palette=[0, 1], output_palette=[0, 1]),
        ],
    }
    assert _matcher()(p1, {}) is True and perm(p1, {}) is True

    # Inverse function-shape with palette inequality -- this matcher
    # fires, iter 330 REJECTS.
    p2 = {
        "pair_analyses": [
            _pair([_group([0], [3]), _group([1], [4])],
                  input_palette=[0, 1, 2], output_palette=[2, 3, 4]),
        ],
    }
    assert _matcher()(p2, {}) is True and perm(p2, {}) is False


def test_independent_from_forward_consistent_color_mapping() -> None:
    # iter 8 (forward) is INDEPENDENT from this matcher. Build the
    # four cells of the 2x2 cross-product:
    fwd = CONDITION_REGISTRY["consistent_color_mapping"]

    # Both fire (bijection cell): 0 -> 3, 1 -> 4.
    p_both = {
        "pair_analyses": [
            _pair([_group([0], [3]), _group([1], [4])]),
        ],
    }
    assert _matcher()(p_both, {}) is True and fwd(p_both, {}) is True

    # Forward only (collapse): 0 -> 3, 1 -> 3. iter 8 fires
    # (each input has one output); inverse REJECTS (output 3 has two
    # preimages).
    p_fwd_only = {
        "pair_analyses": [
            _pair([_group([0], [3]), _group([1], [3])]),
        ],
    }
    assert _matcher()(p_fwd_only, {}) is False and fwd(p_fwd_only, {}) is True

    # Inverse only (expansion): 0 -> {3, 4}. iter 8 REJECTS (input 0
    # has two outputs); inverse fires (each of 3, 4 has unique
    # preimage {0}).
    p_inv_only = {
        "pair_analyses": [
            _pair([_group([0], [3, 4])]),
        ],
    }
    assert _matcher()(p_inv_only, {}) is True and fwd(p_inv_only, {}) is False

    # Neither fires: 0 -> {3, 4}, 1 -> 3. Forward: input 0 has two
    # outputs (fwd rejects). Inverse: output 3 has two preimages
    # {0, 1} (this rejects). Both reject.
    p_neither = {
        "pair_analyses": [
            _pair([_group([0], [3, 4]), _group([1], [3])]),
        ],
    }
    assert _matcher()(p_neither, {}) is False and fwd(p_neither, {}) is False


def test_mutually_exclusive_with_identity_transformation() -> None:
    # iter 13 (identity) STRICTLY MUTUALLY EXCLUSIVE: identity has
    # zero changed cells, so the accumulated inverse mapping is empty,
    # so this matcher REJECTS (mirroring iter 8's empty-evidence
    # rejection).
    iden = CONDITION_REGISTRY["identity_transformation"]
    patterns = {
        "pair_analyses": [
            _pair([], total_changes=0, num_groups=0),
        ],
    }
    assert _matcher()(patterns, {}) is False and iden(patterns, {}) is True


def test_independent_from_palette_equality() -> None:
    # iter 185 (palette equality) is INDEPENDENT. Build two witnesses.
    eq = CONDITION_REGISTRY["output_palette_equals_input"]

    # Palette equality WITHOUT inverse function-shape (collapse with
    # palette-preserving unchanged cells). Palettes [0, 1, 2] on both
    # sides; changes 0 -> 1 and 2 -> 1. Inverse: {1: {0, 2}}. iter 185
    # fires; this matcher REJECTS.
    p1 = {
        "pair_analyses": [
            _pair([_group([0], [1]), _group([2], [1])],
                  input_palette=[0, 1, 2], output_palette=[0, 1, 2]),
        ],
    }
    assert _matcher()(p1, {}) is False and eq(p1, {}) is True

    # Inverse function-shape WITHOUT palette equality (expansion with
    # fresh output colours). Input palette [0, 1, 2]; output palette
    # [3, 4, 5, 6]; changes 0 -> {3, 4}. Inverse: {3: {0}, 4: {0}} --
    # function-shape. iter 185 REJECTS; this matcher fires.
    p2 = {
        "pair_analyses": [
            _pair([_group([0], [3, 4])],
                  input_palette=[0, 1, 2], output_palette=[3, 4, 5, 6]),
        ],
    }
    assert _matcher()(p2, {}) is True and eq(p2, {}) is False


def test_does_not_swallow_per_pair_inverse_violation() -> None:
    # Universal-over-accumulated-mapping semantic: if ANY observation
    # adds a second preimage to ANY output, the matcher rejects.
    # First pair is clean; second pair adds 1 -> 3 (collapsing into 0
    # -> 3 from pair 0).
    patterns = {
        "pair_analyses": [
            _pair([_group([0], [3])]),
            _pair([_group([1], [3])]),
        ],
    }
    assert _matcher()(patterns, {}) is False


# ──────────────────────────────────────────────────────────────────────────
# Recognised-conditions wiring -- one positive and one negative witness
# via the applier so the matcher is reachable from the registry side.
# ──────────────────────────────────────────────────────────────────────────

def test_recognized_conditions_includes_this_matcher_on_positive() -> None:
    from agent.conditions import recognized_conditions

    patterns = {
        "pair_analyses": [_pair([_group([0], [3])])],
    }
    fired = recognized_conditions(patterns)
    assert MATCHER_NAME in fired, (
        f"{MATCHER_NAME} should fire on uniform 1-to-1 mapping; got {fired}"
    )


def test_recognized_conditions_excludes_on_collapse() -> None:
    from agent.conditions import recognized_conditions

    patterns = {
        "pair_analyses": [
            _pair([_group([0], [3]), _group([1], [3])]),
        ],
    }
    fired = recognized_conditions(patterns)
    assert MATCHER_NAME not in fired, (
        f"{MATCHER_NAME} should NOT fire on collapse; got {fired}"
    )


# ──────────────────────────────────────────────────────────────────────────
# Driver.
# ──────────────────────────────────────────────────────────────────────────

def _run_all() -> int:
    tests = [
        test_registered_in_global_registry,
        test_matcher_is_callable,
        test_returns_true_on_uniform_one_to_one_mapping,
        test_returns_true_on_multiple_distinct_one_to_one_pairs,
        test_returns_true_when_forward_is_one_to_many_but_inverse_is_function,
        test_returns_true_across_pairs_when_inverse_is_function_globally,
        test_returns_true_on_palette_permutation_witness,
        test_returns_false_when_two_inputs_map_to_same_output,
        test_returns_false_when_collapse_across_pairs,
        test_returns_false_on_empty_pair_analyses,
        test_returns_false_on_missing_pair_analyses,
        test_returns_false_on_zero_groups_per_pair,
        test_returns_false_on_non_dict_patterns,
        test_returns_false_on_non_list_pair_analyses,
        test_returns_false_when_analysis_is_not_dict,
        test_returns_false_when_groups_field_is_not_list,
        test_returns_false_when_group_is_not_dict,
        test_returns_false_when_input_colors_missing,
        test_returns_false_when_output_colors_missing,
        test_returns_false_when_input_colors_is_not_list,
        test_returns_false_when_output_colors_is_not_list,
        test_returns_false_when_input_colors_empty,
        test_returns_false_when_output_colors_empty,
        test_returns_false_when_input_colors_contains_bool,
        test_returns_false_when_output_colors_contains_bool,
        test_returns_false_on_out_of_range_color,
        test_returns_false_on_non_int_color,
        test_is_side_effect_free_on_inputs,
        test_is_deterministic_across_repeats,
        test_returned_value_is_boolean_not_truthy,
        test_params_ignored,
        test_strict_implication_by_palette_permutation,
        test_independent_from_forward_consistent_color_mapping,
        test_mutually_exclusive_with_identity_transformation,
        test_independent_from_palette_equality,
        test_does_not_swallow_per_pair_inverse_violation,
        test_recognized_conditions_includes_this_matcher_on_positive,
        test_recognized_conditions_excludes_on_collapse,
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
        print("\nall inverse_consistent_color_mapping tests passed.")
    else:
        print(f"\n{rc} test(s) failed.")
    sys.exit(0 if rc == 0 else 1)
