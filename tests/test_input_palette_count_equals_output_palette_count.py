"""
tests/test_input_palette_count_equals_output_palette_count.py --
exercise the iter-972 matcher
``agent.conditions.input_palette_count_equals_output_palette_count``
(new in this iter).

Pins the matcher's contract per
``agent/conditions/input_palette_count_equals_output_palette_count.py``
docstring: every pair satisfies ``len(set(input_palette)) ==
len(set(output_palette))`` on a non-empty ``pair_analyses`` list with
both palettes shaped as lists of non-bool ints. The missing ``== 0``
cell of the cardinality-direction trichotomy opened by iter 188
(``< 0`` -- ``output_palette_count_exceeds_input_palette_count``) and
iter 189 (``> 0`` -- ``input_palette_count_exceeds_output_palette_
count``). Strictly weaker than iter 185 (``output_palette_equals_
input``, set equality) -- this matcher fires on disjoint-but-equal-
size palettes which iter 185 rejects.

Runs without pytest:

    python tests/test_input_palette_count_equals_output_palette_count.py

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


MATCHER_NAME = "input_palette_count_equals_output_palette_count"


def _matcher():
    return CONDITION_REGISTRY[MATCHER_NAME]


def _pair(input_palette, output_palette, **overrides):
    """A pair_analysis shaped like ExtractPatternOperator's output
    (iter-184 schema, with the palette fields)."""
    base = {
        "input_height": 3,
        "input_width": 3,
        "output_height": 3,
        "output_width": 3,
        "size_match": True,
        "total_changes": 0,
        "num_groups": 0,
        "groups": [],
        "input_palette": list(input_palette),
        "output_palette": list(output_palette),
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
# Positive cases.
# ──────────────────────────────────────────────────────────────────────────

def test_returns_true_on_set_equal_palettes() -> None:
    # Canonical positive: same colours, same count.
    patterns = {"pair_analyses": [_pair([0, 1, 2], [0, 1, 2])]}
    assert _matcher()(patterns, {}) is True


def test_returns_true_on_permutation_palettes() -> None:
    # Same colours in different order -- still same cardinality.
    patterns = {"pair_analyses": [_pair([0, 1, 2], [2, 0, 1])]}
    assert _matcher()(patterns, {}) is True


def test_returns_true_on_disjoint_equal_size_palettes() -> None:
    # The witness that proves this matcher is strictly weaker than
    # iter 185 (set equality): disjoint palettes with equal sizes
    # fire this matcher but iter 185 rejects.
    patterns = {"pair_analyses": [_pair([0, 1, 2], [3, 4, 5])]}
    assert _matcher()(patterns, {}) is True


def test_returns_true_on_partial_overlap_equal_size() -> None:
    # Partial overlap, equal cardinalities -- this matcher fires.
    patterns = {"pair_analyses": [_pair([0, 1, 2], [1, 2, 3])]}
    assert _matcher()(patterns, {}) is True


def test_returns_true_with_duplicates_in_palettes() -> None:
    # The contract is on the cardinality of the SET; duplicates within
    # either list must not change the verdict.
    patterns = {"pair_analyses": [_pair([2, 2, 3, 3, 4, 4], [0, 0, 1, 1, 5, 5])]}
    assert _matcher()(patterns, {}) is True


def test_returns_true_when_both_palettes_empty() -> None:
    # Degenerate ``0 == 0`` case: empty palettes on both sides fire.
    # Matches the empty-edge posture of iters 184 / 185 / 186 / 187 /
    # 188 / 189.
    patterns = {"pair_analyses": [_pair([], [])]}
    assert _matcher()(patterns, {}) is True


def test_returns_true_on_singleton_palettes() -> None:
    # |input| == |output| == 1 (both uniform-colour grids).
    patterns = {"pair_analyses": [_pair([0], [5])]}
    assert _matcher()(patterns, {}) is True


def test_returns_true_across_multiple_pairs_all_satisfy() -> None:
    # Per-pair check is independent across pairs; each can have its
    # own palette as long as cardinalities equal within each pair.
    patterns = {
        "pair_analyses": [
            _pair([0, 1], [3, 4]),
            _pair([3, 4, 5], [6, 7, 8]),
            _pair([0], [9]),
        ],
    }
    assert _matcher()(patterns, {}) is True


# ──────────────────────────────────────────────────────────────────────────
# Negative cases.
# ──────────────────────────────────────────────────────────────────────────

def test_returns_false_on_strict_erasure() -> None:
    # |input| > |output| -- iter 189 territory.
    patterns = {"pair_analyses": [_pair([0, 1, 2], [0, 1])]}
    assert _matcher()(patterns, {}) is False


def test_returns_false_on_strict_expansion() -> None:
    # |input| < |output| -- iter 188 territory.
    patterns = {"pair_analyses": [_pair([0, 1], [0, 1, 2])]}
    assert _matcher()(patterns, {}) is False


def test_returns_false_on_strict_erasure_disjoint() -> None:
    # |input| > |output| with disjoint palettes -- strict ``>``
    # still rejects the equality cell.
    patterns = {"pair_analyses": [_pair([3, 4, 5], [0, 1])]}
    assert _matcher()(patterns, {}) is False


def test_returns_false_on_strict_expansion_disjoint() -> None:
    # |input| < |output| with disjoint palettes -- strict ``<``
    # still rejects the equality cell.
    patterns = {"pair_analyses": [_pair([0, 1], [3, 4, 5])]}
    assert _matcher()(patterns, {}) is False


def test_returns_false_when_input_empty_output_nonempty() -> None:
    # 0 != N where N >= 1.
    patterns = {"pair_analyses": [_pair([], [0, 1])]}
    assert _matcher()(patterns, {}) is False


def test_returns_false_when_output_empty_input_nonempty() -> None:
    # N != 0 where N >= 1.
    patterns = {"pair_analyses": [_pair([0, 1], [])]}
    assert _matcher()(patterns, {}) is False


def test_returns_false_when_any_pair_fails_the_gate() -> None:
    # Universal-over-pairs semantic: one failing pair fails the task.
    patterns = {
        "pair_analyses": [
            _pair([0, 1, 2], [3, 4, 5]),
            _pair([3, 4], [3, 4, 5]),  # offending pair (expansion)
            _pair([6, 7, 8], [9, 0, 1]),
        ],
    }
    assert _matcher()(patterns, {}) is False


def test_returns_false_on_empty_pair_analyses() -> None:
    # Fail-closed on empty input -- consistent with every other
    # matcher's posture.
    patterns = {"pair_analyses": []}
    assert _matcher()(patterns, {}) is False


def test_returns_false_on_missing_pair_analyses() -> None:
    patterns = {}
    assert _matcher()(patterns, {}) is False


def test_returns_false_on_non_list_pair_analyses() -> None:
    for bad in (None, 42, "oops", {"a": 1}, (), True):
        patterns = {"pair_analyses": bad}
        assert _matcher()(patterns, {}) is False, (
            f"pair_analyses={bad!r} should not fire"
        )


def test_returns_false_on_non_dict_patterns() -> None:
    assert _matcher()(None, {}) is False         # type: ignore[arg-type]
    assert _matcher()([], {}) is False           # type: ignore[arg-type]
    assert _matcher()("oops", {}) is False       # type: ignore[arg-type]
    assert _matcher()(42, {}) is False           # type: ignore[arg-type]


def test_returns_false_when_any_analysis_is_not_dict() -> None:
    patterns = {
        "pair_analyses": [
            _pair([0, 1], [3, 4]),
            "not-a-dict",
            _pair([3, 4], [5, 6]),
        ],
    }
    assert _matcher()(patterns, {}) is False


# ──────────────────────────────────────────────────────────────────────────
# Strict-type-gate cases.
# ──────────────────────────────────────────────────────────────────────────

def test_returns_false_when_input_palette_missing() -> None:
    analysis = _pair([0, 1], [3, 4])
    del analysis["input_palette"]
    patterns = {"pair_analyses": [analysis]}
    assert _matcher()(patterns, {}) is False


def test_returns_false_when_output_palette_missing() -> None:
    analysis = _pair([0, 1], [3, 4])
    del analysis["output_palette"]
    patterns = {"pair_analyses": [analysis]}
    assert _matcher()(patterns, {}) is False


def test_returns_false_when_input_palette_is_not_list() -> None:
    for bad in (None, 42, "oops", {"a": 1}, (0, 1), True, {0, 1}):
        analysis = _pair([0, 1], [3, 4])
        analysis["input_palette"] = bad
        patterns = {"pair_analyses": [analysis]}
        assert _matcher()(patterns, {}) is False, (
            f"input_palette={bad!r} should not fire"
        )


def test_returns_false_when_output_palette_is_not_list() -> None:
    for bad in (None, 42, "oops", {"a": 1}, (0, 1), True, {0, 1}):
        analysis = _pair([0, 1], [3, 4])
        analysis["output_palette"] = bad
        patterns = {"pair_analyses": [analysis]}
        assert _matcher()(patterns, {}) is False, (
            f"output_palette={bad!r} should not fire"
        )


def test_returns_false_when_input_palette_contains_bool() -> None:
    # Python bools are an int subclass; strict gate must reject them.
    analysis = _pair([0, 1], [3, 4])
    analysis["input_palette"] = [0, True]
    patterns = {"pair_analyses": [analysis]}
    assert _matcher()(patterns, {}) is False


def test_returns_false_when_output_palette_contains_bool() -> None:
    analysis = _pair([0, 1], [3, 4])
    analysis["output_palette"] = [False, 5]
    patterns = {"pair_analyses": [analysis]}
    assert _matcher()(patterns, {}) is False


def test_returns_false_when_palette_contains_non_int() -> None:
    analysis = _pair([0, 1], [3, 4])
    analysis["input_palette"] = [0, "1"]
    patterns = {"pair_analyses": [analysis]}
    assert _matcher()(patterns, {}) is False

    analysis2 = _pair([0, 1], [3, 4])
    analysis2["output_palette"] = [0.0]
    patterns2 = {"pair_analyses": [analysis2]}
    assert _matcher()(patterns2, {}) is False


# ──────────────────────────────────────────────────────────────────────────
# Behavioural-contract cases.
# ──────────────────────────────────────────────────────────────────────────

def test_is_side_effect_free_on_inputs() -> None:
    patterns = {
        "pair_analyses": [
            _pair([0, 1], [3, 4]),
            _pair([3, 4], [5, 6]),
        ],
    }
    params = {"unused": 1}
    before_p = copy.deepcopy(patterns)
    before_q = copy.deepcopy(params)
    _matcher()(patterns, params)
    assert patterns == before_p, "matcher mutated patterns"
    assert params == before_q, "matcher mutated params"


def test_is_deterministic_across_repeats() -> None:
    patterns = {"pair_analyses": [_pair([0, 1], [3, 4])]}
    results = [_matcher()(patterns, {}) for _ in range(5)]
    assert len(set(results)) == 1, f"non-deterministic outputs: {results}"


def test_returned_value_is_boolean_not_truthy() -> None:
    # recognized_conditions filters on ``match(...) is True`` exactly,
    # so the matcher must return literal Booleans.
    out_true = _matcher()({"pair_analyses": [_pair([0, 1], [3, 4])]}, {})
    out_false = _matcher()({"pair_analyses": [_pair([0], [0, 1])]}, {})
    assert out_true is True, f"expected literal True, got {out_true!r}"
    assert out_false is False, f"expected literal False, got {out_false!r}"


def test_ignores_per_group_color_lists() -> None:
    # The matcher reads ONLY ``input_palette`` / ``output_palette``.
    # Per-group ``input_colors`` / ``output_colors`` on the change
    # cells are a different axis -- the matcher must ignore them.
    analysis = _pair(
        [0, 1, 2], [3, 4, 5],
        groups=[{
            "input_colors": [9, 9],  # not in either whole-grid palette
            "output_colors": [8, 8],
            "positions": [(0, 0)],
            "top_row": 0, "top_col": 0,
            "cell_count": 1,
        }],
        num_groups=1, total_changes=1,
    )
    patterns = {"pair_analyses": [analysis]}
    assert _matcher()(patterns, {}) is True


def test_ignores_dimensional_fields() -> None:
    # Dimensional fields are orthogonal -- arbitrary dim combinations
    # must not affect the matcher's verdict.
    analysis = _pair([0, 1, 2], [3, 4, 5], input_height=7, input_width=9,
                     output_height=2, output_width=3, size_match=False)
    patterns = {"pair_analyses": [analysis]}
    assert _matcher()(patterns, {}) is True


# ──────────────────────────────────────────────────────────────────────────
# Strict-implication / mutual-exclusion / orthogonality against siblings.
# ──────────────────────────────────────────────────────────────────────────

def test_strictly_implied_by_identity_transformation() -> None:
    # Identity has output palette equal to input palette per pair, so
    # cardinalities match. STRICT IMPLICATION: identity ⇒ this matcher.
    identity = CONDITION_REGISTRY["identity_transformation"]
    patterns = {
        "grid_size_preserved": True,
        "pair_analyses": [_pair([0, 1, 2], [0, 1, 2])],
    }
    assert identity(patterns, {}) is True
    assert _matcher()(patterns, {}) is True


def test_strictly_implied_by_iter185_set_equality() -> None:
    # Set equality implies cardinality equality. iter 185 fires ⇒
    # this matcher fires. Converse fails on disjoint-but-equal-size.
    iter185 = CONDITION_REGISTRY["output_palette_equals_input"]
    # iter 185 fires and this matcher fires.
    p_set_eq = {"pair_analyses": [_pair([0, 1, 2], [0, 1, 2])]}
    assert iter185(p_set_eq, {}) is True
    assert _matcher()(p_set_eq, {}) is True
    # Disjoint-but-equal-size: this matcher fires, iter 185 rejects.
    p_disjoint_eq = {"pair_analyses": [_pair([0, 1, 2], [3, 4, 5])]}
    assert iter185(p_disjoint_eq, {}) is False
    assert _matcher()(p_disjoint_eq, {}) is True


def test_strict_refinement_witness_against_iter190_permutation() -> None:
    # iter 190 (output_palette_is_permutation_of_input_palette) requires
    # set equality AND a bijective change-cell mapping (CLAUDE.md §8
    # vocabulary). Set equality alone ⇒ cardinality equality, so iter
    # 190 ⇒ this matcher. The converse fails because cardinality
    # equality does NOT imply set equality. Witness the disjoint-but-
    # equal-size fixture (which fires this matcher but rejects iter 190
    # for lack of set equality), confirming the strict-refinement
    # direction without needing a full bijection fixture for iter 190.
    iter190 = CONDITION_REGISTRY["output_palette_is_permutation_of_input_palette"]
    p_disjoint_eq = {"pair_analyses": [_pair([0, 1, 2], [3, 4, 5])]}
    assert iter190(p_disjoint_eq, {}) is False
    assert _matcher()(p_disjoint_eq, {}) is True


def test_mutually_exclusive_with_iter188_strict_expansion() -> None:
    # |output| > |input| is the strict-expansion direction; the
    # equality cell cannot fire when the strict ``>`` cell fires.
    iter188 = CONDITION_REGISTRY["output_palette_count_exceeds_input_palette_count"]

    # Strict expansion: iter 188 fires, this matcher does not.
    p_exp = {"pair_analyses": [_pair([0, 1], [0, 1, 2])]}
    assert iter188(p_exp, {}) is True
    assert _matcher()(p_exp, {}) is False

    # Equality: this matcher fires, iter 188 does not.
    p_eq = {"pair_analyses": [_pair([0, 1, 2], [3, 4, 5])]}
    assert iter188(p_eq, {}) is False
    assert _matcher()(p_eq, {}) is True


def test_mutually_exclusive_with_iter189_strict_erasure() -> None:
    # |input| > |output| is the strict-erasure direction; the equality
    # cell cannot fire when the strict ``>`` cell (in the other
    # direction) fires.
    iter189 = CONDITION_REGISTRY["input_palette_count_exceeds_output_palette_count"]

    # Strict erasure: iter 189 fires, this matcher does not.
    p_erase = {"pair_analyses": [_pair([0, 1, 2], [0, 1])]}
    assert iter189(p_erase, {}) is True
    assert _matcher()(p_erase, {}) is False

    # Equality: this matcher fires, iter 189 does not.
    p_eq = {"pair_analyses": [_pair([0, 1, 2], [3, 4, 5])]}
    assert iter189(p_eq, {}) is False
    assert _matcher()(p_eq, {}) is True


def test_iter188_iter189_this_matcher_form_a_trichotomy() -> None:
    # Pinned property: on any well-typed pair, exactly one of the three
    # cardinality-direction cells fires (or none if no pairs).
    iter188 = CONDITION_REGISTRY["output_palette_count_exceeds_input_palette_count"]
    iter189 = CONDITION_REGISTRY["input_palette_count_exceeds_output_palette_count"]
    fixtures = [
        # (input_palette, output_palette, who_fires)
        ([0, 1], [0, 1, 2], "iter188"),       # strict expansion
        ([0, 1, 2], [0, 1], "iter189"),       # strict erasure
        ([0, 1, 2], [0, 1, 2], "equality"),   # set equality
        ([0, 1, 2], [3, 4, 5], "equality"),   # disjoint equal-size
        ([0, 1], [3, 4], "equality"),         # disjoint equal-size, smaller
        ([0], [], "iter189"),                 # empty output side
        ([], [0], "iter188"),                 # empty input side
        ([], [], "equality"),                 # both empty
    ]
    for ip, op, expected in fixtures:
        patterns = {"pair_analyses": [_pair(ip, op)]}
        fires = {
            "iter188": iter188(patterns, {}),
            "iter189": iter189(patterns, {}),
            "equality": _matcher()(patterns, {}),
        }
        # Exactly one of the three fires per pair.
        firing = [k for k, v in fires.items() if v]
        assert len(firing) == 1, (
            f"trichotomy violation on (ip={ip!r}, op={op!r}): "
            f"fired={firing!r}"
        )
        assert firing[0] == expected, (
            f"wrong cell fired on (ip={ip!r}, op={op!r}): "
            f"got {firing[0]!r}, expected {expected!r}"
        )


def test_orthogonal_to_iter186_disjoint() -> None:
    # iter 186 (output_palette_disjoint_from_input) is INDEPENDENT.
    # Disjoint palettes can have equal or unequal cardinalities.
    iter186 = CONDITION_REGISTRY["output_palette_disjoint_from_input"]

    # disjoint AND equal-size -- both fire (witness for refining iter 185).
    p_both = {"pair_analyses": [_pair([0, 1, 2], [3, 4, 5])]}
    assert iter186(p_both, {}) is True
    assert _matcher()(p_both, {}) is True

    # disjoint AND unequal-size -- iter 186 fires, this matcher rejects.
    p_186_only = {"pair_analyses": [_pair([0, 1], [3, 4, 5])]}
    assert iter186(p_186_only, {}) is True
    assert _matcher()(p_186_only, {}) is False

    # not disjoint AND equal-size -- this matcher fires, iter 186 rejects.
    p_eq_only = {"pair_analyses": [_pair([0, 1, 2], [0, 1, 2])]}
    assert iter186(p_eq_only, {}) is False
    assert _matcher()(p_eq_only, {}) is True


def test_orthogonal_to_grid_size_preserved() -> None:
    # Whole-grid palette cardinality equality is orthogonal to per-pair
    # input==output dim axis (the four-cell 2x2 co-fire table).
    gsp = CONDITION_REGISTRY["grid_size_preserved"]

    # equality + preserved -- both fire
    p1 = {
        "grid_size_preserved": True,
        "pair_analyses": [_pair([0, 1, 2], [3, 4, 5])],
    }
    assert _matcher()(p1, {}) is True and gsp(p1, {}) is True

    # equality + changed -- only this matcher fires
    p2 = {
        "grid_size_preserved": False,
        "pair_analyses": [
            _pair([0, 1, 2], [3, 4, 5], output_height=6, output_width=6,
                  size_match=False),
        ],
    }
    assert _matcher()(p2, {}) is True and gsp(p2, {}) is False

    # not-equality + preserved -- only preserved fires
    p3 = {
        "grid_size_preserved": True,
        "pair_analyses": [_pair([0, 1], [0, 1, 2])],
    }
    assert _matcher()(p3, {}) is False and gsp(p3, {}) is True

    # not-equality + changed -- neither fires
    p4 = {
        "grid_size_preserved": False,
        "pair_analyses": [
            _pair([0, 1], [0, 1, 2], output_height=6, output_width=6,
                  size_match=False),
        ],
    }
    assert _matcher()(p4, {}) is False and gsp(p4, {}) is False


def test_orthogonal_to_input_color_uniform() -> None:
    # iter 14 inspects change-cells' input colour uniformity. The
    # whole-grid palette cardinality-equality axis is INDEPENDENT.
    icu = CONDITION_REGISTRY["input_color_uniform"]

    # this matcher fires AND icu fires (single change-cell source
    # colour, palette cardinality preserved).
    analysis = _pair(
        [0, 5, 3], [0, 5, 8],
        groups=[{
            "input_colors": [3],
            "output_colors": [8],
            "positions": [(0, 0)],
            "top_row": 0, "top_col": 0,
            "cell_count": 1,
        }],
        num_groups=1, total_changes=1,
    )
    p1 = {"pair_analyses": [analysis]}
    assert _matcher()(p1, {}) is True and icu(p1, {}) is True

    # this matcher fires but icu does NOT (no change cells means
    # iter 14 is vacuously False per its docstring).
    p2 = {"pair_analyses": [_pair([0, 1, 2], [3, 4, 5])]}
    assert _matcher()(p2, {}) is True and icu(p2, {}) is False


def test_recognized_conditions_includes_count_equals() -> None:
    from agent.conditions import recognized_conditions
    # Disjoint-but-equal-size: this matcher fires AND iter-186 fires;
    # iter-185 / 188 / 189 do not.
    patterns = {"pair_analyses": [_pair([0, 1, 2], [3, 4, 5])]}
    fired = recognized_conditions(patterns)
    assert MATCHER_NAME in fired, (
        f"{MATCHER_NAME!r} did not fire on a clearly disjoint-equal-size "
        f"patterns dict; got {fired!r}"
    )
    assert "output_palette_disjoint_from_input" in fired, (
        "iter-186 must co-fire on disjoint palettes (it's the disjointness "
        "set-relation gate)"
    )
    assert "output_palette_equals_input" not in fired
    assert "output_palette_count_exceeds_input_palette_count" not in fired
    assert "input_palette_count_exceeds_output_palette_count" not in fired


def test_recognized_conditions_excludes_on_strict_expansion() -> None:
    # Strict expansion fires iter 187 + iter 188 but NOT this matcher
    # (strict ``<`` excludes the equality cell).
    from agent.conditions import recognized_conditions
    patterns = {"pair_analyses": [_pair([0, 1], [0, 1, 2, 3])]}
    fired = recognized_conditions(patterns)
    assert "input_palette_subset_of_output" in fired
    assert "output_palette_count_exceeds_input_palette_count" in fired
    assert MATCHER_NAME not in fired, (
        f"{MATCHER_NAME!r} must NOT fire on strict palette expansion "
        f"(the strict ``<`` cell excludes equality); got {fired!r}"
    )


def test_recognized_conditions_excludes_on_strict_erasure() -> None:
    # Strict erasure fires iter 184 + iter 189 but NOT this matcher
    # (strict ``>`` excludes the equality cell).
    from agent.conditions import recognized_conditions
    patterns = {"pair_analyses": [_pair([0, 1, 2, 3], [0, 1])]}
    fired = recognized_conditions(patterns)
    assert "output_palette_subset_of_input" in fired
    assert "input_palette_count_exceeds_output_palette_count" in fired
    assert MATCHER_NAME not in fired, (
        f"{MATCHER_NAME!r} must NOT fire on strict palette erasure "
        f"(the strict ``>`` cell excludes equality); got {fired!r}"
    )


# ──────────────────────────────────────────────────────────────────────────
# Test runner (dependency-free, same style as the other tests).
# ──────────────────────────────────────────────────────────────────────────

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
