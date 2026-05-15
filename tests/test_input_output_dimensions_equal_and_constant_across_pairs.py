"""
tests/test_input_output_dimensions_equal_and_constant_across_pairs.py
-- exercise the iter-992 matcher
``agent.conditions.input_output_dimensions_equal_and_constant_across_pairs``
(new in this iter).

Pins the matcher's contract per the docstring of
``agent/conditions/input_output_dimensions_equal_and_constant_across_pairs.py``:
there exists a single ``(H, W)`` tuple such that every pair's input grid
AND output grid have exactly those dimensions, on a non-empty
``pair_analyses`` list with each dimension field shaped as a strict
positive int.

Conjunction handle for the three pre-existing conjuncts (iter 22
input-side dim constancy, iter 20 output-side dim constancy, iter 1
per-pair size match). The discriminating-axis tests verify that the new
matcher fires iff all three of those fire.

Dimensional dual of iter 991's
``input_output_palette_equal_and_constant_across_pairs``; mirrors that
file's structure so future readers can pair-read them.

Runs without pytest:

    python tests/test_input_output_dimensions_equal_and_constant_across_pairs.py

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


MATCHER_NAME = "input_output_dimensions_equal_and_constant_across_pairs"


def _matcher():
    return CONDITION_REGISTRY[MATCHER_NAME]


def _pair(input_height=3, input_width=3, output_height=None,
          output_width=None, **overrides):
    """A pair_analysis shaped like ExtractPatternOperator's output
    (iter-184 schema, with the dim fields).

    By default ``output_height`` mirrors ``input_height`` and
    ``output_width`` mirrors ``input_width`` so the per-pair size-match
    conjunct (iter 1) is satisfied unless explicitly overridden.
    """
    if output_height is None:
        output_height = input_height
    if output_width is None:
        output_width = input_width
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
        "input_palette": [0],
        "output_palette": [0],
    }
    base.update(overrides)
    return base


def _patterns(*pairs, **top_overrides):
    """A patterns dict honouring iter 1's top-level
    ``grid_size_preserved`` flag (set True iff every pair's
    size_match is True). The conjunction matcher reads only per-pair
    fields, but the registry helper that exercises
    ``grid_size_preserved`` (iter 1) reads the top-level flag, so we
    keep it in sync with the pair_analyses for the discriminating-
    axis tests below."""
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


def test_p5_at_least_86() -> None:
    # Iter-992 brings the registry to >= 86 (P5 monotone). The probe
    # baseline was P5 = 85 after iter 991.
    assert len(CONDITION_REGISTRY) >= 86, (
        f"expected >= 86 matchers post-iter-992; got {len(CONDITION_REGISTRY)}"
    )


# ──────────────────────────────────────────────────────────────────────────
# Positive cases.
# ──────────────────────────────────────────────────────────────────────────

def test_single_pair_with_equal_dims_fires() -> None:
    patterns = _patterns(_pair(3, 3))
    assert _matcher()(patterns, {}) is True


def test_two_pairs_same_dims_input_equal_output_fires() -> None:
    patterns = _patterns(_pair(3, 3), _pair(3, 3))
    assert _matcher()(patterns, {}) is True


def test_non_square_constant_dims_fires() -> None:
    # H != W is fine -- the matcher does NOT require squareness.
    patterns = _patterns(_pair(3, 5), _pair(3, 5))
    assert _matcher()(patterns, {}) is True


def test_singleton_1x1_dims_fires() -> None:
    patterns = _patterns(_pair(1, 1), _pair(1, 1))
    assert _matcher()(patterns, {}) is True


def test_three_pairs_all_same_dims_fires() -> None:
    patterns = _patterns(_pair(7, 9), _pair(7, 9), _pair(7, 9))
    assert _matcher()(patterns, {}) is True


def test_large_dims_fires() -> None:
    patterns = _patterns(_pair(30, 30), _pair(30, 30))
    assert _matcher()(patterns, {}) is True


# ──────────────────────────────────────────────────────────────────────────
# Negative cases (per-pair size equality violated).
# ──────────────────────────────────────────────────────────────────────────

def test_per_pair_input_neq_output_rejects() -> None:
    # iter-1 conjunct fails on the first pair: input dims != output dims.
    patterns = _patterns(
        _pair(3, 3, output_height=5, output_width=5),
        _pair(3, 3),
    )
    assert _matcher()(patterns, {}) is False


def test_per_pair_height_mismatch_rejects() -> None:
    # input_height != output_height on every pair (constant cross-pair
    # but per-pair non-equal -- iter 1 fails everywhere).
    patterns = _patterns(
        _pair(3, 5, output_height=5),
        _pair(3, 5, output_height=5),
    )
    assert _matcher()(patterns, {}) is False


def test_per_pair_width_mismatch_rejects() -> None:
    # Same, on the width axis.
    patterns = _patterns(
        _pair(3, 5, output_width=3),
        _pair(3, 5, output_width=3),
    )
    assert _matcher()(patterns, {}) is False


def test_per_pair_tile_style_dims_rejects() -> None:
    # Tile-style: constant 3x3 inputs and constant 9x9 outputs.
    # iter 22 fires, iter 20 fires, iter 1 fails -- conjunction rejects.
    patterns = _patterns(
        _pair(3, 3, output_height=9, output_width=9),
        _pair(3, 3, output_height=9, output_width=9),
    )
    assert _matcher()(patterns, {}) is False


# ──────────────────────────────────────────────────────────────────────────
# Negative cases (cross-pair constancy violated).
# ──────────────────────────────────────────────────────────────────────────

def test_input_constancy_violated_rejects() -> None:
    # Each pair has input == output dims (iter 1 fires per-pair), but
    # the shared per-pair shape differs across pairs.
    patterns = _patterns(
        _pair(3, 3),
        _pair(5, 5),
    )
    assert _matcher()(patterns, {}) is False


def test_output_constancy_violated_rejects() -> None:
    # Same as above with non-square shapes -- both iter 22 and iter 20
    # fail; iter 1 fires per-pair.
    patterns = _patterns(
        _pair(3, 5),
        _pair(7, 9),
    )
    assert _matcher()(patterns, {}) is False


def test_one_offending_pair_fails_the_gate() -> None:
    # Universal-over-pairs: one mismatched pair fails the whole task.
    patterns = _patterns(
        _pair(3, 3),
        _pair(3, 3),
        _pair(3, 4),  # offending pair (per-pair NO, also cross-pair NO)
        _pair(3, 3),
    )
    assert _matcher()(patterns, {}) is False


def test_height_varies_across_pairs_rejects() -> None:
    # Height-only variation, width constant.
    patterns = _patterns(
        _pair(3, 5),
        _pair(7, 5),
    )
    assert _matcher()(patterns, {}) is False


def test_width_varies_across_pairs_rejects() -> None:
    # Width-only variation, height constant.
    patterns = _patterns(
        _pair(3, 5),
        _pair(3, 7),
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


def test_missing_input_height_rejects() -> None:
    analysis = _pair(3, 3)
    del analysis["input_height"]
    patterns = {"pair_analyses": [analysis]}
    assert _matcher()(patterns, {}) is False


def test_missing_input_width_rejects() -> None:
    analysis = _pair(3, 3)
    del analysis["input_width"]
    patterns = {"pair_analyses": [analysis]}
    assert _matcher()(patterns, {}) is False


def test_missing_output_height_rejects() -> None:
    analysis = _pair(3, 3)
    del analysis["output_height"]
    patterns = {"pair_analyses": [analysis]}
    assert _matcher()(patterns, {}) is False


def test_missing_output_width_rejects() -> None:
    analysis = _pair(3, 3)
    del analysis["output_width"]
    patterns = {"pair_analyses": [analysis]}
    assert _matcher()(patterns, {}) is False


def test_non_int_input_height_rejects() -> None:
    for bad in (None, "3", 3.0, [3], {3}, (3,)):
        analysis = _pair(3, 3)
        analysis["input_height"] = bad
        patterns = {"pair_analyses": [analysis]}
        assert _matcher()(patterns, {}) is False, (
            f"input_height={bad!r} should not fire"
        )


def test_non_int_output_width_rejects() -> None:
    for bad in (None, "3", 3.0, [3], {3}, (3,)):
        analysis = _pair(3, 3)
        analysis["output_width"] = bad
        patterns = {"pair_analyses": [analysis]}
        assert _matcher()(patterns, {}) is False, (
            f"output_width={bad!r} should not fire"
        )


def test_bool_input_height_rejects() -> None:
    # Python bool is an int subclass; matcher must reject explicitly.
    analysis = _pair(3, 3)
    analysis["input_height"] = True
    patterns = {"pair_analyses": [analysis]}
    assert _matcher()(patterns, {}) is False


def test_bool_output_height_rejects() -> None:
    analysis = _pair(3, 3)
    analysis["output_height"] = True
    patterns = {"pair_analyses": [analysis]}
    assert _matcher()(patterns, {}) is False


def test_zero_height_rejects() -> None:
    # Degenerate empty grid -- strict positive comparison rejects.
    analysis = _pair(3, 3)
    analysis["input_height"] = 0
    patterns = {"pair_analyses": [analysis]}
    assert _matcher()(patterns, {}) is False


def test_negative_height_rejects() -> None:
    analysis = _pair(3, 3)
    analysis["output_height"] = -1
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


def test_ignores_palette_fields() -> None:
    # Palette fields are orthogonal -- arbitrary palette values must
    # not change the verdict.
    p1 = _pair(3, 3, input_palette=[7, 8, 9], output_palette=[0])
    p2 = _pair(3, 3, input_palette=[], output_palette=[1, 2])
    patterns = _patterns(p1, p2)
    assert _matcher()(patterns, {}) is True


# ──────────────────────────────────────────────────────────────────────────
# Conjunction relationships -- the three named conjuncts.
# ──────────────────────────────────────────────────────────────────────────

def test_fires_iff_all_three_conjuncts_fire() -> None:
    # Discriminating-axis test. The matcher must agree with the literal
    # conjunction of iter 1 (grid_size_preserved), iter 22
    # (input_dimensions_constant), and iter 20
    # (output_dimensions_constant) on every cell of the truth table
    # the fixture vocabulary can realise.
    gsp = CONDITION_REGISTRY["grid_size_preserved"]
    idc = CONDITION_REGISTRY["input_dimensions_constant"]
    odc = CONDITION_REGISTRY["output_dimensions_constant"]

    cases = [
        # All three fire -- conjunction fires.
        _patterns(_pair(3, 3), _pair(3, 3)),
        # All three fire (singleton 1x1).
        _patterns(_pair(1, 1), _pair(1, 1)),
        # iter 1 fails per-pair (input dims != output dims) -- rejects.
        _patterns(
            _pair(3, 3, output_height=5, output_width=5),
            _pair(3, 3, output_height=5, output_width=5),
        ),
        # iter 22 fails (input varies) -- conjunction rejects. iter 20
        # also fails because output mirrors input.
        _patterns(
            _pair(3, 3),
            _pair(5, 5),
        ),
        # iter 1 fires per-pair but iter 22 fails -- per-pair shapes
        # equal within a pair but differ across pairs.
        _patterns(
            _pair(3, 5),
            _pair(7, 9),
        ),
    ]
    for p in cases:
        m = _matcher()(p, {})
        expected = (
            gsp(p, {}) is True
            and idc(p, {}) is True
            and odc(p, {}) is True
        )
        assert m is expected, (
            f"matcher disagrees with literal conjunction on {p!r}: "
            f"matcher={m!r}, expected={expected!r}"
        )


def test_strictly_implies_each_conjunct() -> None:
    # When this matcher fires, each individual conjunct must also fire.
    gsp = CONDITION_REGISTRY["grid_size_preserved"]
    idc = CONDITION_REGISTRY["input_dimensions_constant"]
    odc = CONDITION_REGISTRY["output_dimensions_constant"]

    patterns = _patterns(_pair(3, 5), _pair(3, 5))
    assert _matcher()(patterns, {}) is True
    assert gsp(patterns, {}) is True, "iter-1 conjunct must hold"
    assert idc(patterns, {}) is True, "iter-22 conjunct must hold"
    assert odc(patterns, {}) is True, "iter-20 conjunct must hold"


def test_converse_fails_iter_1_alone_does_not_imply() -> None:
    # iter 1 fires per-pair; cross-pair shape can vary. This matcher
    # rejects on cross-pair variation even when iter 1 is universally
    # satisfied.
    gsp = CONDITION_REGISTRY["grid_size_preserved"]
    patterns = _patterns(_pair(3, 3), _pair(5, 5))
    assert gsp(patterns, {}) is True
    assert _matcher()(patterns, {}) is False


def test_converse_fails_iter_22_20_alone_do_not_imply() -> None:
    # iter 22 AND iter 20 can both fire while per-pair input != output
    # (the tile-style case: constant 3x3 inputs, constant 9x9 outputs).
    idc = CONDITION_REGISTRY["input_dimensions_constant"]
    odc = CONDITION_REGISTRY["output_dimensions_constant"]
    patterns = _patterns(
        _pair(3, 3, output_height=9, output_width=9),
        _pair(3, 3, output_height=9, output_width=9),
    )
    assert idc(patterns, {}) is True
    assert odc(patterns, {}) is True
    assert _matcher()(patterns, {}) is False


# ──────────────────────────────────────────────────────────────────────────
# Sibling-matcher relationships.
# ──────────────────────────────────────────────────────────────────────────

def test_independent_from_identity_transformation() -> None:
    # Identity says every pair internally preserves; says nothing about
    # cross-pair shape equality. INDEPENDENT.
    identity = CONDITION_REGISTRY["identity_transformation"]

    # Identity fires but shape varies across pairs -- this matcher
    # rejects, identity accepts.
    p1 = _patterns(_pair(3, 3), _pair(5, 5))
    assert identity(p1, {}) is True
    assert _matcher()(p1, {}) is False

    # Identity fires AND shape constant -- both fire.
    p2 = _patterns(_pair(3, 3), _pair(3, 3))
    assert identity(p2, {}) is True
    assert _matcher()(p2, {}) is True

    # This matcher fires on a per-pair-non-identity (constant shape with
    # changes inside) -- identity REJECTS because the per-pair change
    # group list is non-empty.
    _group = {"input_colors": [0], "output_colors": [1],
              "positions": [(0, 0)], "top_row": 0, "top_col": 0}
    p3 = _patterns(
        _pair(3, 3, num_groups=1, total_changes=1, groups=[dict(_group)]),
        _pair(3, 3, num_groups=1, total_changes=1, groups=[dict(_group)]),
    )
    assert identity(p3, {}) is False
    assert _matcher()(p3, {}) is True


def test_independent_from_input_palette_constant_across_pairs() -> None:
    # Dimensional axis vs palette axis -- independent.
    ipc = CONDITION_REGISTRY["input_palette_constant_across_pairs"]

    # Both fire.
    p_both = _patterns(_pair(3, 3), _pair(3, 3))
    assert _matcher()(p_both, {}) is True and ipc(p_both, {}) is True

    # Only this matcher: same dims, different input palette.
    p_dim_only = _patterns(
        _pair(3, 3, input_palette=[0, 1, 2], output_palette=[0, 1, 2]),
        _pair(3, 3, input_palette=[3, 4, 5], output_palette=[3, 4, 5]),
    )
    assert _matcher()(p_dim_only, {}) is True
    assert ipc(p_dim_only, {}) is False

    # Only iter 989: same input palette, different dims.
    p_pal_only = _patterns(
        _pair(3, 3, input_palette=[0, 1, 2]),
        _pair(5, 5, input_palette=[0, 1, 2]),
    )
    assert _matcher()(p_pal_only, {}) is False
    assert ipc(p_pal_only, {}) is True


def test_mutually_exclusive_with_grid_size_changed() -> None:
    # grid_size_changed requires at least one pair with size_match
    # False. This matcher's per-pair equality check makes it reject
    # that case; conversely if every pair has size_match True,
    # grid_size_changed rejects on no offending pair. The two are
    # mutually exclusive over the patterns space.
    gsc = CONDITION_REGISTRY["grid_size_changed"]

    # Case A: dims constant and equal -- this fires, gsc rejects.
    pA = _patterns(_pair(3, 3), _pair(3, 3))
    assert _matcher()(pA, {}) is True
    assert gsc(pA, {}) is False

    # Case B: at least one pair changes size -- this rejects, gsc fires.
    pB = _patterns(
        _pair(3, 3, output_height=9, output_width=9),
        _pair(3, 3, output_height=9, output_width=9),
    )
    assert _matcher()(pB, {}) is False
    assert gsc(pB, {}) is True


def test_independent_from_input_output_palette_conjunction() -> None:
    # Dimensional conjunction vs palette conjunction (iter 991).
    # INDEPENDENT on the (dimensions, palette) quadrant.
    iopc = CONDITION_REGISTRY[
        "input_output_palette_equal_and_constant_across_pairs"
    ]

    # Both fire: fixed shape AND fixed palette.
    p_both = _patterns(
        _pair(3, 3, input_palette=[0, 1], output_palette=[0, 1]),
        _pair(3, 3, input_palette=[0, 1], output_palette=[0, 1]),
    )
    assert _matcher()(p_both, {}) is True
    assert iopc(p_both, {}) is True

    # Only this matcher: fixed shape, varying palette.
    p_dim_only = _patterns(
        _pair(3, 3, input_palette=[0, 1], output_palette=[0, 1]),
        _pair(3, 3, input_palette=[2, 3], output_palette=[2, 3]),
    )
    assert _matcher()(p_dim_only, {}) is True
    assert iopc(p_dim_only, {}) is False

    # Only iter 991: varying shape, fixed palette.
    p_pal_only = _patterns(
        _pair(3, 3, input_palette=[0, 1], output_palette=[0, 1]),
        _pair(5, 5, input_palette=[0, 1], output_palette=[0, 1]),
    )
    assert _matcher()(p_pal_only, {}) is False
    assert iopc(p_pal_only, {}) is True


def test_recognized_conditions_includes_this_matcher() -> None:
    from agent.conditions import recognized_conditions
    patterns = _patterns(_pair(3, 3), _pair(3, 3))
    fired = recognized_conditions(patterns)
    assert MATCHER_NAME in fired, (
        f"{MATCHER_NAME!r} did not fire on a clearly fixed-shape "
        f"patterns dict; got {fired!r}"
    )


def test_recognized_conditions_excludes_on_per_pair_size_mismatch() -> None:
    from agent.conditions import recognized_conditions
    patterns = _patterns(
        _pair(3, 3, output_height=9, output_width=9),
        _pair(3, 3, output_height=9, output_width=9),
    )
    fired = recognized_conditions(patterns)
    assert MATCHER_NAME not in fired, (
        f"{MATCHER_NAME!r} must NOT fire on per-pair shape inequality; "
        f"got {fired!r}"
    )


def test_recognized_conditions_excludes_on_cross_pair_size_mismatch() -> None:
    from agent.conditions import recognized_conditions
    patterns = _patterns(_pair(3, 3), _pair(5, 5))
    fired = recognized_conditions(patterns)
    assert MATCHER_NAME not in fired, (
        f"{MATCHER_NAME!r} must NOT fire on cross-pair shape variation; "
        f"got {fired!r}"
    )


def test_does_not_displace_adjacent_iter_matchers() -> None:
    # Adjacent-iter non-displacement: every iter-1/13/20/22/991 matcher
    # remains in the registry alongside this new one.
    expected = {
        "grid_size_preserved",
        "identity_transformation",
        "input_dimensions_constant",
        "output_dimensions_constant",
        "input_palette_constant_across_pairs",
        "output_palette_constant_across_pairs",
        "input_output_palette_equal_and_constant_across_pairs",
    }
    missing = expected - set(CONDITION_REGISTRY)
    assert not missing, (
        f"adjacent matchers missing post-iter-992: {missing!r}"
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
