"""
tests/test_input_output_dimensions_and_palette_equal_and_constant_across_pairs.py
-- exercise the iter-993 matcher
``agent.conditions.input_output_dimensions_and_palette_equal_and_constant_across_pairs``
(new in this iter).

Pins the matcher's contract per the docstring of
``agent/conditions/input_output_dimensions_and_palette_equal_and_constant_across_pairs.py``:
the conjunction of iter 991's
``input_output_palette_equal_and_constant_across_pairs`` AND iter 992's
``input_output_dimensions_equal_and_constant_across_pairs``. Fires iff
both named conjuncts fire on the patterns dict.

Conjunction-of-conjunctions handle for the two pre-existing
conjunction-handles. The discriminating-axis tests verify that the new
matcher fires iff both of those fire on a non-empty pair_analyses list.

Runs without pytest:

    python tests/test_input_output_dimensions_and_palette_equal_and_constant_across_pairs.py

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
    "input_output_dimensions_and_palette_equal_and_constant_across_pairs"
)
DIM_CONJUNCT = "input_output_dimensions_equal_and_constant_across_pairs"
PAL_CONJUNCT = "input_output_palette_equal_and_constant_across_pairs"


def _matcher():
    return CONDITION_REGISTRY[MATCHER_NAME]


def _pair(input_height=3, input_width=3, output_height=None,
          output_width=None, input_palette=None, output_palette=None,
          **overrides):
    """A pair_analysis shaped like ExtractPatternOperator's output
    (iter-184 schema, with both dim and palette fields).

    By default both dims and palettes mirror their input counterparts so
    every conjunct is satisfied unless explicitly overridden.
    """
    if output_height is None:
        output_height = input_height
    if output_width is None:
        output_width = input_width
    if input_palette is None:
        input_palette = [0, 1]
    if output_palette is None:
        output_palette = list(input_palette)
    base = {
        "input_height": input_height,
        "input_width": input_width,
        "output_height": output_height,
        "output_width": output_width,
        "size_match": (
            input_height == output_height and input_width == output_width
        ),
        "grid_size_preserved": (
            input_height == output_height and input_width == output_width
        ),
        "total_changes": 0,
        "num_groups": 0,
        "groups": [],
        "input_palette": list(input_palette),
        "output_palette": list(output_palette),
    }
    base.update(overrides)
    return base


def _patterns(*pairs, **top_overrides):
    """A patterns dict carrying both the pair_analyses list and the
    top-level ``grid_size_preserved`` flag iter 1's matcher reads."""
    pairs_list = list(pairs)
    top = {
        "pair_analyses": pairs_list,
        "grid_size_preserved": all(
            bool(p.get("size_match", False)) for p in pairs_list
        ) if pairs_list else False,
    }
    top.update(top_overrides)
    return top


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


def test_p5_at_least_87() -> None:
    # Iter-993 brings the registry to >= 87 (P5 monotone). The probe
    # baseline was P5 = 86 after iter 992.
    assert len(CONDITION_REGISTRY) >= 87, (
        f"expected >= 87 matchers post-iter-993; got {len(CONDITION_REGISTRY)}"
    )


def test_named_conjuncts_present() -> None:
    # The matcher dispatches to two named registry entries; if either is
    # missing the iter is mis-staged. Pins the dependency.
    assert DIM_CONJUNCT in CONDITION_REGISTRY, (
        f"missing iter-992 conjunct {DIM_CONJUNCT!r}"
    )
    assert PAL_CONJUNCT in CONDITION_REGISTRY, (
        f"missing iter-991 conjunct {PAL_CONJUNCT!r}"
    )


# ──────────────────────────────────────────────────────────────────────────
# Positive cases.
# ──────────────────────────────────────────────────────────────────────────

def test_single_pair_fixed_shape_and_palette_fires() -> None:
    patterns = _patterns(_pair(3, 3, input_palette=[0, 1]))
    assert _matcher()(patterns, {}) is True


def test_two_pairs_same_shape_same_palette_fires() -> None:
    patterns = _patterns(
        _pair(3, 3, input_palette=[0, 1, 2]),
        _pair(3, 3, input_palette=[0, 1, 2]),
    )
    assert _matcher()(patterns, {}) is True


def test_non_square_constant_dims_and_palette_fires() -> None:
    patterns = _patterns(
        _pair(3, 5, input_palette=[7, 8]),
        _pair(3, 5, input_palette=[7, 8]),
    )
    assert _matcher()(patterns, {}) is True


def test_singleton_1x1_with_singleton_palette_fires() -> None:
    patterns = _patterns(
        _pair(1, 1, input_palette=[5]),
        _pair(1, 1, input_palette=[5]),
    )
    assert _matcher()(patterns, {}) is True


def test_three_pairs_all_same_shape_and_palette_fires() -> None:
    patterns = _patterns(
        _pair(7, 9, input_palette=[0, 1]),
        _pair(7, 9, input_palette=[0, 1]),
        _pair(7, 9, input_palette=[0, 1]),
    )
    assert _matcher()(patterns, {}) is True


def test_set_equal_different_order_palette_fires() -> None:
    # Palette equality is set semantics (frozenset) -- list order and
    # duplicates collapse.
    patterns = _patterns(
        _pair(3, 3, input_palette=[1, 2, 0], output_palette=[0, 1, 2]),
        _pair(3, 3, input_palette=[2, 0, 1], output_palette=[0, 2, 1]),
    )
    assert _matcher()(patterns, {}) is True


def test_all_empty_palettes_with_constant_shape_fires() -> None:
    # Degenerate case inherited from iter 991: empty palette is admissible
    # at the type level; per-pair / cross-pair set equality both hold.
    patterns = _patterns(
        _pair(3, 3, input_palette=[], output_palette=[]),
        _pair(3, 3, input_palette=[], output_palette=[]),
    )
    assert _matcher()(patterns, {}) is True


# ──────────────────────────────────────────────────────────────────────────
# Negative cases (dimensional conjunct fails).
# ──────────────────────────────────────────────────────────────────────────

def test_per_pair_size_mismatch_rejects() -> None:
    # iter 992 rejects on per-pair input != output dims even if palette
    # axis is clean.
    patterns = _patterns(
        _pair(3, 3, output_height=5, output_width=5,
              input_palette=[0, 1], output_palette=[0, 1]),
        _pair(3, 3, output_height=5, output_width=5,
              input_palette=[0, 1], output_palette=[0, 1]),
    )
    assert _matcher()(patterns, {}) is False


def test_cross_pair_shape_variation_rejects() -> None:
    # iter 992 rejects on cross-pair shape variation; palette axis is
    # clean (same palette across pairs).
    patterns = _patterns(
        _pair(3, 3, input_palette=[0, 1]),
        _pair(5, 5, input_palette=[0, 1]),
    )
    assert _matcher()(patterns, {}) is False


def test_tile_style_dims_rejects() -> None:
    # Constant 3x3 inputs, constant 9x9 outputs -- iter 22 + iter 20
    # individually fire but iter 992 rejects on per-pair non-equality.
    patterns = _patterns(
        _pair(3, 3, output_height=9, output_width=9),
        _pair(3, 3, output_height=9, output_width=9),
    )
    assert _matcher()(patterns, {}) is False


# ──────────────────────────────────────────────────────────────────────────
# Negative cases (palette conjunct fails).
# ──────────────────────────────────────────────────────────────────────────

def test_per_pair_palette_mismatch_rejects() -> None:
    # iter 991 rejects on per-pair input != output palette even if dim
    # axis is clean.
    patterns = _patterns(
        _pair(3, 3, input_palette=[0, 1], output_palette=[2, 3]),
        _pair(3, 3, input_palette=[0, 1], output_palette=[2, 3]),
    )
    assert _matcher()(patterns, {}) is False


def test_cross_pair_palette_variation_rejects() -> None:
    # iter 991 rejects on cross-pair palette variation; dim axis is
    # clean (same shape across pairs).
    patterns = _patterns(
        _pair(3, 3, input_palette=[0, 1]),
        _pair(3, 3, input_palette=[2, 3]),
    )
    assert _matcher()(patterns, {}) is False


def test_palette_disjoint_per_pair_rejects() -> None:
    patterns = _patterns(
        _pair(3, 3, input_palette=[0, 1], output_palette=[5, 6]),
        _pair(3, 3, input_palette=[0, 1], output_palette=[5, 6]),
    )
    assert _matcher()(patterns, {}) is False


# ──────────────────────────────────────────────────────────────────────────
# Negative cases (BOTH conjuncts fail).
# ──────────────────────────────────────────────────────────────────────────

def test_both_axes_violated_rejects() -> None:
    # Shape varies AND palette varies. Either failure alone rejects;
    # both failing rejects as well.
    patterns = _patterns(
        _pair(3, 3, input_palette=[0, 1]),
        _pair(5, 5, input_palette=[2, 3]),
    )
    assert _matcher()(patterns, {}) is False


# ──────────────────────────────────────────────────────────────────────────
# Fail-closed paths.
# ──────────────────────────────────────────────────────────────────────────

def test_empty_pair_analyses_rejects() -> None:
    assert _matcher()({"pair_analyses": []}, {}) is False


def test_missing_pair_analyses_rejects() -> None:
    assert _matcher()({}, {}) is False


def test_non_list_pair_analyses_rejects() -> None:
    for bad in (None, 42, "oops", {"a": 1}, (), True):
        assert _matcher()({"pair_analyses": bad}, {}) is False, (
            f"pair_analyses={bad!r} should not fire"
        )


def test_non_dict_patterns_rejects() -> None:
    for bad in (None, [], "oops", 42):
        assert _matcher()(bad, {}) is False, (  # type: ignore[arg-type]
            f"patterns={bad!r} should not fire"
        )


def test_non_dict_analysis_rejects() -> None:
    patterns = {
        "pair_analyses": [_pair(3, 3), "not-a-dict", _pair(3, 3)]
    }
    assert _matcher()(patterns, {}) is False


def test_missing_dimension_field_rejects() -> None:
    analysis = _pair(3, 3)
    del analysis["input_height"]
    patterns = {"pair_analyses": [analysis]}
    assert _matcher()(patterns, {}) is False


def test_missing_palette_field_rejects() -> None:
    analysis = _pair(3, 3)
    del analysis["input_palette"]
    patterns = {"pair_analyses": [analysis]}
    assert _matcher()(patterns, {}) is False


def test_non_int_dimension_rejects() -> None:
    for bad in (None, "3", 3.0, [3], {3}, (3,)):
        analysis = _pair(3, 3)
        analysis["input_height"] = bad
        patterns = {"pair_analyses": [analysis]}
        assert _matcher()(patterns, {}) is False, (
            f"input_height={bad!r} should not fire"
        )


def test_bool_dimension_rejects() -> None:
    # bool is an int subclass; iter 992's matcher rejects explicitly.
    analysis = _pair(3, 3)
    analysis["input_height"] = True
    patterns = {"pair_analyses": [analysis]}
    assert _matcher()(patterns, {}) is False


def test_bool_in_palette_rejects() -> None:
    # iter 991's strict-list-of-non-bool-ints contract.
    analysis = _pair(3, 3)
    analysis["input_palette"] = [True, 0, 1]
    patterns = {"pair_analyses": [analysis]}
    assert _matcher()(patterns, {}) is False


def test_non_int_palette_rejects() -> None:
    analysis = _pair(3, 3)
    analysis["output_palette"] = [0, "1", 2]
    patterns = {"pair_analyses": [analysis]}
    assert _matcher()(patterns, {}) is False


def test_zero_dimension_rejects() -> None:
    analysis = _pair(3, 3)
    analysis["input_height"] = 0
    patterns = {"pair_analyses": [analysis]}
    assert _matcher()(patterns, {}) is False


def test_negative_dimension_rejects() -> None:
    analysis = _pair(3, 3)
    analysis["output_width"] = -1
    patterns = {"pair_analyses": [analysis]}
    assert _matcher()(patterns, {}) is False


# ──────────────────────────────────────────────────────────────────────────
# Behavioural contract.
# ──────────────────────────────────────────────────────────────────────────

def test_side_effect_free() -> None:
    patterns = _patterns(_pair(3, 3), _pair(3, 3))
    params = {"unused": 1}
    before_p = copy.deepcopy(patterns)
    before_q = copy.deepcopy(params)
    _matcher()(patterns, params)
    assert patterns == before_p, "matcher mutated patterns"
    assert params == before_q, "matcher mutated params"


def test_deterministic_across_repeats() -> None:
    patterns = _patterns(_pair(3, 3), _pair(3, 3))
    results = [_matcher()(patterns, {}) for _ in range(5)]
    assert len(set(results)) == 1, f"non-deterministic: {results}"


def test_returns_literal_boolean() -> None:
    out_true = _matcher()(_patterns(_pair(3, 3)), {})
    out_false = _matcher()(_patterns(_pair(3, 3), _pair(5, 5)), {})
    assert out_true is True, f"expected literal True, got {out_true!r}"
    assert out_false is False, f"expected literal False, got {out_false!r}"


def test_params_ignored() -> None:
    # The matcher takes no params; arbitrary param contents must not
    # change the verdict.
    patterns = _patterns(_pair(3, 3), _pair(3, 3))
    for params in ({}, {"x": 1}, {"min_dim": 100}, {"strict": False}):
        assert _matcher()(patterns, params) is True


# ──────────────────────────────────────────────────────────────────────────
# Conjunction relationships -- the two named conjunction-handles.
# ──────────────────────────────────────────────────────────────────────────

def test_fires_iff_both_named_conjuncts_fire() -> None:
    # Discriminating-axis test. The matcher must agree with the literal
    # conjunction of iter 991 and iter 992 on every cell of the
    # (dim, palette) 2x2 truth table the fixture vocabulary realises.
    dim_m = CONDITION_REGISTRY[DIM_CONJUNCT]
    pal_m = CONDITION_REGISTRY[PAL_CONJUNCT]

    cases = [
        # (T, T) -- both fire.
        _patterns(
            _pair(3, 3, input_palette=[0, 1]),
            _pair(3, 3, input_palette=[0, 1]),
        ),
        # (T, F) -- dim fires, palette varies across pairs.
        _patterns(
            _pair(3, 3, input_palette=[0, 1]),
            _pair(3, 3, input_palette=[2, 3]),
        ),
        # (F, T) -- palette fires, shape varies across pairs.
        _patterns(
            _pair(3, 3, input_palette=[0, 1]),
            _pair(5, 5, input_palette=[0, 1]),
        ),
        # (F, F) -- neither fires.
        _patterns(
            _pair(3, 3, input_palette=[0, 1]),
            _pair(5, 5, input_palette=[2, 3]),
        ),
    ]
    for p in cases:
        m = _matcher()(p, {})
        expected = dim_m(p, {}) is True and pal_m(p, {}) is True
        assert m is expected, (
            f"matcher disagrees with literal conjunction on {p!r}: "
            f"matcher={m!r}, expected={expected!r}"
        )


def test_strictly_implies_iter_992_conjunct() -> None:
    # When this matcher fires, iter 992's conjunction-handle must
    # also fire.
    dim_m = CONDITION_REGISTRY[DIM_CONJUNCT]
    patterns = _patterns(_pair(3, 5), _pair(3, 5))
    assert _matcher()(patterns, {}) is True
    assert dim_m(patterns, {}) is True


def test_strictly_implies_iter_991_conjunct() -> None:
    # When this matcher fires, iter 991's conjunction-handle must
    # also fire.
    pal_m = CONDITION_REGISTRY[PAL_CONJUNCT]
    patterns = _patterns(
        _pair(3, 3, input_palette=[7, 8]),
        _pair(3, 3, input_palette=[7, 8]),
    )
    assert _matcher()(patterns, {}) is True
    assert pal_m(patterns, {}) is True


def test_converse_fails_dim_only() -> None:
    # iter 992 fires alone (fixed shape, varying palette); this matcher
    # rejects on the palette axis.
    dim_m = CONDITION_REGISTRY[DIM_CONJUNCT]
    patterns = _patterns(
        _pair(3, 3, input_palette=[0, 1]),
        _pair(3, 3, input_palette=[2, 3]),
    )
    assert dim_m(patterns, {}) is True
    assert _matcher()(patterns, {}) is False


def test_converse_fails_palette_only() -> None:
    # iter 991 fires alone (fixed palette, varying shape); this matcher
    # rejects on the dimensional axis.
    pal_m = CONDITION_REGISTRY[PAL_CONJUNCT]
    patterns = _patterns(
        _pair(3, 3, input_palette=[0, 1]),
        _pair(5, 5, input_palette=[0, 1]),
    )
    assert pal_m(patterns, {}) is True
    assert _matcher()(patterns, {}) is False


# ──────────────────────────────────────────────────────────────────────────
# Transitive implications -- the six underlying single-axis conjuncts.
# ──────────────────────────────────────────────────────────────────────────

def test_strictly_implies_all_six_underlying_conjuncts() -> None:
    # When this matcher fires, each of iter 1, 20, 22, 185, 989, 990
    # must also fire -- transitively through iter 991 / 992.
    underlying = [
        "grid_size_preserved",                  # iter 1
        "output_dimensions_constant",           # iter 20
        "input_dimensions_constant",            # iter 22
        "output_palette_equals_input",          # iter 185
        "input_palette_constant_across_pairs",  # iter 989
        "output_palette_constant_across_pairs", # iter 990
    ]
    patterns = _patterns(
        _pair(3, 3, input_palette=[0, 1, 2]),
        _pair(3, 3, input_palette=[0, 1, 2]),
    )
    assert _matcher()(patterns, {}) is True
    for name in underlying:
        m = CONDITION_REGISTRY[name]
        assert m(patterns, {}) is True, (
            f"transitive implication broken: {name!r} did not fire "
            f"on fixed-shape-fixed-palette fixture"
        )


# ──────────────────────────────────────────────────────────────────────────
# Sibling-matcher relationships.
# ──────────────────────────────────────────────────────────────────────────

def test_independent_from_identity_transformation() -> None:
    # Identity is INDEPENDENT in both directions.
    identity = CONDITION_REGISTRY["identity_transformation"]

    # Identity fires (zero changes per pair) but shape varies -- this
    # matcher rejects.
    p1 = _patterns(
        _pair(3, 3, input_palette=[0, 1]),
        _pair(5, 5, input_palette=[0, 1]),
    )
    assert identity(p1, {}) is True
    assert _matcher()(p1, {}) is False

    # This matcher fires on a per-pair-non-identity (constant shape +
    # palette with inner-grid changes) -- identity REJECTS because the
    # per-pair change group list is non-empty.
    _group = {"input_colors": [0], "output_colors": [1],
              "positions": [(0, 0)], "top_row": 0, "top_col": 0}
    p2 = _patterns(
        _pair(3, 3, input_palette=[0, 1], output_palette=[0, 1],
              num_groups=1, total_changes=1, groups=[dict(_group)]),
        _pair(3, 3, input_palette=[0, 1], output_palette=[0, 1],
              num_groups=1, total_changes=1, groups=[dict(_group)]),
    )
    assert identity(p2, {}) is False
    assert _matcher()(p2, {}) is True


def test_mutually_exclusive_with_grid_size_changed() -> None:
    # Inherited from iter 992's mutual exclusion.
    gsc = CONDITION_REGISTRY["grid_size_changed"]

    pA = _patterns(_pair(3, 3, input_palette=[0]),
                   _pair(3, 3, input_palette=[0]))
    assert _matcher()(pA, {}) is True
    assert gsc(pA, {}) is False

    pB = _patterns(
        _pair(3, 3, output_height=9, output_width=9),
        _pair(3, 3, output_height=9, output_width=9),
    )
    assert _matcher()(pB, {}) is False
    assert gsc(pB, {}) is True


def test_recognized_conditions_includes_this_matcher() -> None:
    from agent.conditions import recognized_conditions
    patterns = _patterns(
        _pair(3, 3, input_palette=[0, 1]),
        _pair(3, 3, input_palette=[0, 1]),
    )
    fired = recognized_conditions(patterns)
    assert MATCHER_NAME in fired, (
        f"{MATCHER_NAME!r} did not fire on a clearly fixed-shape "
        f"fixed-palette patterns dict; got {fired!r}"
    )


def test_recognized_conditions_excludes_on_shape_mismatch() -> None:
    from agent.conditions import recognized_conditions
    patterns = _patterns(
        _pair(3, 3, input_palette=[0, 1]),
        _pair(5, 5, input_palette=[0, 1]),
    )
    fired = recognized_conditions(patterns)
    assert MATCHER_NAME not in fired, (
        f"{MATCHER_NAME!r} must NOT fire on cross-pair shape variation; "
        f"got {fired!r}"
    )


def test_recognized_conditions_excludes_on_palette_mismatch() -> None:
    from agent.conditions import recognized_conditions
    patterns = _patterns(
        _pair(3, 3, input_palette=[0, 1]),
        _pair(3, 3, input_palette=[2, 3]),
    )
    fired = recognized_conditions(patterns)
    assert MATCHER_NAME not in fired, (
        f"{MATCHER_NAME!r} must NOT fire on cross-pair palette variation; "
        f"got {fired!r}"
    )


def test_does_not_displace_adjacent_iter_matchers() -> None:
    # Adjacent-iter non-displacement: every conjunct + sibling matcher
    # remains in the registry alongside this new one.
    expected = {
        "grid_size_preserved",
        "identity_transformation",
        "input_dimensions_constant",
        "output_dimensions_constant",
        "output_palette_equals_input",
        "input_palette_constant_across_pairs",
        "output_palette_constant_across_pairs",
        "input_output_palette_equal_and_constant_across_pairs",
        "input_output_dimensions_equal_and_constant_across_pairs",
    }
    missing = expected - set(CONDITION_REGISTRY)
    assert not missing, (
        f"adjacent matchers missing post-iter-993: {missing!r}"
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
