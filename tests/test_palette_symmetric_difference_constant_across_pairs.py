"""
tests/test_palette_symmetric_difference_constant_across_pairs.py --
exercise the iter-190 matcher
``agent.conditions.palette_symmetric_difference_constant_across_pairs``
(new in this iter).

Pins the matcher's contract per
``agent/conditions/palette_symmetric_difference_constant_across_pairs.py``
docstring: every pair's
``len(set(input_palette) ^ set(output_palette))`` is bit-identical
across pairs on a non-empty ``pair_analyses`` list with both palettes
shaped as lists of non-bool ints. First entry on the **cross-pair-
constancy** sub-axis of the palette axis (iters 184 / 185 / 186 / 187
named set-containment direction per pair; iters 188 / 189 / 185 named
cardinality direction per pair; this matcher names *constancy of the
recolour-magnitude integer* across pairs).

Runs without pytest:

    python tests/test_palette_symmetric_difference_constant_across_pairs.py

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


MATCHER_NAME = "palette_symmetric_difference_constant_across_pairs"


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

def test_returns_true_on_single_pair_trivial_constancy() -> None:
    # A single pair is trivially "constant" (one observation, one
    # value). Matches the iter-30 / 33 / 34 / 35 / 36 / 37 / 38 / 39 /
    # 40 / 42 family posture: cross-pair constancy fires on single-
    # pair tasks as long as the one pair is well-typed.
    patterns = {"pair_analyses": [_pair([0, 1, 2], [0, 3])]}
    assert _matcher()(patterns, {}) is True


def test_returns_true_when_delta_is_zero_on_every_pair() -> None:
    # Palette-equality on every pair forces |Δ| == 0 per pair. The
    # cross-pair constancy holds with canonical value 0. Iter 185
    # ⇒ this matcher (strict implication on the universal-over-pairs
    # gate).
    patterns = {
        "pair_analyses": [
            _pair([0, 1, 2], [0, 1, 2]),
            _pair([3, 4], [3, 4]),
            _pair([5], [5]),
        ],
    }
    assert _matcher()(patterns, {}) is True


def test_returns_true_when_delta_is_one_on_every_pair() -> None:
    # The "exactly one fresh colour added per pair" pattern.
    patterns = {
        "pair_analyses": [
            _pair([0, 1], [0, 1, 2]),
            _pair([3, 4], [3, 4, 5]),
        ],
    }
    assert _matcher()(patterns, {}) is True


def test_returns_true_when_delta_is_two_on_every_pair() -> None:
    # Could be 1 in + 1 out OR 2 in OR 2 out -- the matcher pins only
    # the magnitude, not the direction.
    patterns = {
        "pair_analyses": [
            _pair([0, 1, 2], [0, 1, 3]),       # 1 dropped (2), 1 added (3)
            _pair([4, 5, 6], [4, 7, 8]),       # 2 dropped (5,6), 2 added (7,8)? no — |Δ|=4
        ],
    }
    # Recompute: pair 0 has set({0,1,2}) ^ set({0,1,3}) = {2, 3} → 2.
    # pair 1 has set({4,5,6}) ^ set({4,7,8}) = {5,6,7,8} → 4. So these
    # do NOT match. Adjust pair 1 to a |Δ| == 2 case.
    patterns = {
        "pair_analyses": [
            _pair([0, 1, 2], [0, 1, 3]),       # |Δ| = 2
            _pair([4, 5, 6], [4, 5, 7]),       # |Δ| = 2
            _pair([8, 9], [0, 1]),             # |Δ| = 4 — not constant, see below
        ],
    }
    # The above third pair has |Δ| == 4; the matcher must NOT fire.
    assert _matcher()(patterns, {}) is False
    # And the right two-pair fixture:
    patterns_ok = {
        "pair_analyses": [
            _pair([0, 1, 2], [0, 1, 3]),
            _pair([4, 5, 6], [4, 5, 7]),
        ],
    }
    assert _matcher()(patterns_ok, {}) is True


def test_returns_true_with_duplicates_in_palettes() -> None:
    # Δ size is computed on SETS; duplicates in either list must not
    # affect the verdict.
    patterns = {
        "pair_analyses": [
            _pair([0, 0, 1, 1, 2], [0, 0, 1, 1, 3]),  # set({0,1,2}) ^ set({0,1,3}) = {2,3} → 2
            _pair([4, 5, 5, 6], [4, 4, 5, 7]),        # set({4,5,6}) ^ set({4,5,7}) = {6,7} → 2
        ],
    }
    assert _matcher()(patterns, {}) is True


def test_returns_true_when_both_palettes_empty_on_every_pair() -> None:
    # Degenerate empty-empty case: |Δ| == 0 on every pair → constant.
    # The matcher fires. The upstream extractor is responsible for
    # non-degenerate grids; honour what is emitted.
    patterns = {
        "pair_analyses": [
            _pair([], []),
            _pair([], []),
        ],
    }
    assert _matcher()(patterns, {}) is True


def test_returns_true_on_disjoint_palettes_with_constant_total() -> None:
    # Disjoint palettes per pair give |Δ| == |input| + |output| per
    # pair. Cross-pair constancy holds iff |input| + |output| is
    # constant.
    patterns = {
        "pair_analyses": [
            _pair([0, 1], [2, 3, 4]),        # |Δ| = 5
            _pair([5, 6, 7], [8, 9]),        # |Δ| = 5
            _pair([0, 8], [1, 2, 9]),        # |Δ| = 5
        ],
    }
    assert _matcher()(patterns, {}) is True


# ──────────────────────────────────────────────────────────────────────────
# Negative cases.
# ──────────────────────────────────────────────────────────────────────────

def test_returns_false_when_delta_varies_across_pairs() -> None:
    # Pair 0: |Δ| = 0 (equality). Pair 1: |Δ| = 1 (one added). Not
    # constant.
    patterns = {
        "pair_analyses": [
            _pair([0, 1], [0, 1]),
            _pair([3, 4], [3, 4, 5]),
        ],
    }
    assert _matcher()(patterns, {}) is False


def test_returns_false_when_one_pair_has_extra_drop() -> None:
    # Pair 0 drops one. Pair 1 drops two. Different |Δ|.
    patterns = {
        "pair_analyses": [
            _pair([0, 1, 2], [0, 1]),
            _pair([3, 4, 5, 6], [3, 4]),
        ],
    }
    assert _matcher()(patterns, {}) is False


def test_returns_false_on_mixed_empty_and_non_empty_pairs() -> None:
    # Pair 0: both empty → |Δ| = 0. Pair 1: |Δ| ≥ 1.
    patterns = {
        "pair_analyses": [
            _pair([], []),
            _pair([0], [1]),
        ],
    }
    assert _matcher()(patterns, {}) is False


def test_returns_false_on_empty_pair_analyses() -> None:
    # Fail-closed on empty input -- a constancy claim with zero
    # observations is meaningless.
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
            _pair([0, 1], [0, 2]),
            "not-a-dict",
            _pair([3, 4], [3, 5]),
        ],
    }
    assert _matcher()(patterns, {}) is False


# ──────────────────────────────────────────────────────────────────────────
# Strict-type-gate cases.
# ──────────────────────────────────────────────────────────────────────────

def test_returns_false_when_input_palette_missing() -> None:
    analysis = _pair([0, 1], [0, 2])
    del analysis["input_palette"]
    patterns = {"pair_analyses": [analysis]}
    assert _matcher()(patterns, {}) is False


def test_returns_false_when_output_palette_missing() -> None:
    analysis = _pair([0, 1], [0, 2])
    del analysis["output_palette"]
    patterns = {"pair_analyses": [analysis]}
    assert _matcher()(patterns, {}) is False


def test_returns_false_when_input_palette_is_not_list() -> None:
    for bad in (None, 42, "oops", {"a": 1}, (0, 1), True, {0, 1}):
        analysis = _pair([0, 1], [0, 2])
        analysis["input_palette"] = bad
        patterns = {"pair_analyses": [analysis]}
        assert _matcher()(patterns, {}) is False, (
            f"input_palette={bad!r} should not fire"
        )


def test_returns_false_when_output_palette_is_not_list() -> None:
    for bad in (None, 42, "oops", {"a": 1}, (0, 1), True, {0, 1}):
        analysis = _pair([0, 1], [0, 2])
        analysis["output_palette"] = bad
        patterns = {"pair_analyses": [analysis]}
        assert _matcher()(patterns, {}) is False, (
            f"output_palette={bad!r} should not fire"
        )


def test_returns_false_when_input_palette_contains_bool() -> None:
    analysis = _pair([0, 1], [0, 2])
    analysis["input_palette"] = [0, True]
    patterns = {"pair_analyses": [analysis]}
    assert _matcher()(patterns, {}) is False


def test_returns_false_when_output_palette_contains_bool() -> None:
    analysis = _pair([0, 1], [0, 2])
    analysis["output_palette"] = [False]
    patterns = {"pair_analyses": [analysis]}
    assert _matcher()(patterns, {}) is False


def test_returns_false_when_palette_contains_non_int() -> None:
    analysis = _pair([0, 1], [0, 2])
    analysis["input_palette"] = [0, "1"]
    patterns = {"pair_analyses": [analysis]}
    assert _matcher()(patterns, {}) is False

    analysis2 = _pair([0, 1], [0, 2])
    analysis2["output_palette"] = [0.0]
    patterns2 = {"pair_analyses": [analysis2]}
    assert _matcher()(patterns2, {}) is False


def test_returns_false_when_second_pair_has_malformed_palette() -> None:
    # First pair is fine; second pair has a malformed palette. The
    # matcher must fail-closed without silently treating it as a
    # match.
    bad = _pair([3, 4], [3, 5])
    bad["input_palette"] = None
    patterns = {"pair_analyses": [_pair([0, 1], [0, 2]), bad]}
    assert _matcher()(patterns, {}) is False


# ──────────────────────────────────────────────────────────────────────────
# Behavioural-contract cases.
# ──────────────────────────────────────────────────────────────────────────

def test_is_side_effect_free_on_inputs() -> None:
    patterns = {
        "pair_analyses": [
            _pair([0, 1], [0, 2]),
            _pair([3, 4], [3, 5]),
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
        "pair_analyses": [
            _pair([0, 1], [0, 2]),
            _pair([3, 4], [3, 5]),
        ],
    }
    results = [_matcher()(patterns, {}) for _ in range(5)]
    assert len(set(results)) == 1, f"non-deterministic outputs: {results}"


def test_returned_value_is_boolean_not_truthy() -> None:
    # recognized_conditions filters on ``match(...) is True`` exactly,
    # so the matcher must return literal Booleans.
    out_true = _matcher()(
        {"pair_analyses": [_pair([0, 1], [0, 2]), _pair([3, 4], [3, 5])]},
        {},
    )
    out_false = _matcher()(
        {"pair_analyses": [_pair([0, 1], [0, 2, 3]), _pair([3, 4, 5], [3])]},
        {},
    )
    assert out_true is True, f"expected literal True, got {out_true!r}"
    assert out_false is False, f"expected literal False, got {out_false!r}"


def test_ignores_per_group_color_lists() -> None:
    # The matcher reads ONLY ``input_palette`` / ``output_palette``.
    # Per-group ``input_colors`` / ``output_colors`` on the change
    # cells are a different axis -- the matcher must ignore them.
    p0 = _pair(
        [0, 1, 2], [0, 1, 3],
        groups=[{
            "input_colors": [9, 9],  # not in either whole-grid palette
            "output_colors": [8, 8],
            "positions": [(0, 0)],
            "top_row": 0, "top_col": 0,
            "cell_count": 1,
        }],
        num_groups=1, total_changes=1,
    )
    p1 = _pair(
        [4, 5, 6], [4, 5, 7],
        groups=[{
            "input_colors": [9, 9],
            "output_colors": [8, 8],
            "positions": [(0, 0)],
            "top_row": 0, "top_col": 0,
            "cell_count": 1,
        }],
        num_groups=1, total_changes=1,
    )
    patterns = {"pair_analyses": [p0, p1]}
    assert _matcher()(patterns, {}) is True


def test_ignores_dimensional_fields() -> None:
    # Dimensional fields are orthogonal -- arbitrary dim combinations
    # must not affect the matcher's verdict.
    p0 = _pair(
        [0, 1, 2], [0, 1, 3],
        input_height=7, input_width=9, output_height=2, output_width=3,
        size_match=False,
    )
    p1 = _pair(
        [4, 5, 6], [4, 5, 7],
        input_height=1, input_width=1, output_height=8, output_width=8,
        size_match=False,
    )
    patterns = {"pair_analyses": [p0, p1]}
    assert _matcher()(patterns, {}) is True


# ──────────────────────────────────────────────────────────────────────────
# Orthogonality / co-fire matrix against the palette-axis siblings.
# ──────────────────────────────────────────────────────────────────────────

def test_identity_strictly_implies_this_matcher() -> None:
    # Identity has output palette equal to input palette per pair, so
    # |Δ| == 0 on every pair, constant. Iter 13 ⇒ this matcher
    # (strict implication on the universal-over-pairs gate).
    identity = CONDITION_REGISTRY["identity_transformation"]
    patterns = {
        "grid_size_preserved": True,
        "pair_analyses": [
            _pair([0, 1, 2], [0, 1, 2]),
            _pair([3, 4], [3, 4]),
        ],
    }
    assert identity(patterns, {}) is True
    assert _matcher()(patterns, {}) is True


def test_iter185_strictly_implies_this_matcher() -> None:
    # Iter 185 (palette equality) ⇒ |Δ| == 0 on every pair, constant.
    # Strict implication: iter 185 ⇒ this matcher.
    iter185 = CONDITION_REGISTRY["output_palette_equals_input"]
    patterns = {
        "pair_analyses": [
            _pair([0, 1, 2], [0, 1, 2]),
            _pair([3, 4, 5], [3, 4, 5]),
            _pair([6, 7], [6, 7]),
        ],
    }
    assert iter185(patterns, {}) is True
    assert _matcher()(patterns, {}) is True


def test_this_matcher_fires_without_iter185() -> None:
    # The reverse of the previous test does NOT hold: this matcher
    # fires on any constant |Δ|, not only on |Δ| == 0. Iter 185 fires
    # only on |Δ| == 0.
    iter185 = CONDITION_REGISTRY["output_palette_equals_input"]
    patterns = {
        "pair_analyses": [
            _pair([0, 1], [0, 1, 2]),
            _pair([3, 4], [3, 4, 5]),
        ],
    }
    assert iter185(patterns, {}) is False
    assert _matcher()(patterns, {}) is True


def test_independent_of_iter184_subset() -> None:
    # Iter 184 (output ⊆ input) and this matcher are independent: can
    # co-fire AND can disagree.
    iter184 = CONDITION_REGISTRY["output_palette_subset_of_input"]

    # Co-fire: every pair drops exactly one input colour. iter 184
    # fires (output ⊆ input on every pair); |Δ| == 1 on every pair
    # → this matcher fires.
    p_cofire = {
        "pair_analyses": [
            _pair([0, 1, 2], [0, 1]),
            _pair([3, 4, 5], [3, 4]),
        ],
    }
    assert iter184(p_cofire, {}) is True
    assert _matcher()(p_cofire, {}) is True

    # iter 184 fires alone: subset per pair but varying |Δ|.
    p_184_only = {
        "pair_analyses": [
            _pair([0, 1, 2], [0, 1]),      # |Δ| = 1
            _pair([3, 4, 5, 6], [3]),      # |Δ| = 3
        ],
    }
    assert iter184(p_184_only, {}) is True
    assert _matcher()(p_184_only, {}) is False


def test_independent_of_iter186_disjoint() -> None:
    # Iter 186 (disjoint) and this matcher are independent.
    iter186 = CONDITION_REGISTRY["output_palette_disjoint_from_input"]

    # Co-fire: disjoint per pair AND |input| + |output| constant.
    p_cofire = {
        "pair_analyses": [
            _pair([0, 1], [2, 3]),         # |Δ| = 4
            _pair([4, 5], [6, 7]),         # |Δ| = 4
        ],
    }
    assert iter186(p_cofire, {}) is True
    assert _matcher()(p_cofire, {}) is True

    # iter 186 alone: disjoint per pair but varying total palette size.
    p_186_only = {
        "pair_analyses": [
            _pair([0], [1, 2]),            # |Δ| = 3
            _pair([3, 4], [5, 6, 7]),      # |Δ| = 5
        ],
    }
    assert iter186(p_186_only, {}) is True
    assert _matcher()(p_186_only, {}) is False


def test_independent_of_iter187_input_subset() -> None:
    iter187 = CONDITION_REGISTRY["input_palette_subset_of_output"]

    # Co-fire: input ⊆ output per pair AND |Δ| constant (one fresh
    # colour added per pair).
    p_cofire = {
        "pair_analyses": [
            _pair([0, 1], [0, 1, 2]),      # |Δ| = 1
            _pair([3, 4], [3, 4, 5]),      # |Δ| = 1
        ],
    }
    assert iter187(p_cofire, {}) is True
    assert _matcher()(p_cofire, {}) is True

    # iter 187 alone: input ⊆ output per pair but varying additions.
    p_187_only = {
        "pair_analyses": [
            _pair([0, 1], [0, 1, 2]),         # |Δ| = 1
            _pair([3, 4], [3, 4, 5, 6, 7]),   # |Δ| = 3
        ],
    }
    assert iter187(p_187_only, {}) is True
    assert _matcher()(p_187_only, {}) is False


def test_independent_of_iter188_strict_expansion() -> None:
    iter188 = CONDITION_REGISTRY[
        "output_palette_count_exceeds_input_palette_count"
    ]

    # Co-fire: strict expansion per pair AND |Δ| constant.
    p_cofire = {
        "pair_analyses": [
            _pair([0, 1], [0, 1, 2]),      # |Δ| = 1, |out|>|in|
            _pair([3, 4], [3, 4, 5]),      # |Δ| = 1, |out|>|in|
        ],
    }
    assert iter188(p_cofire, {}) is True
    assert _matcher()(p_cofire, {}) is True

    # iter 188 alone: strict expansion per pair but varying |Δ|.
    p_188_only = {
        "pair_analyses": [
            _pair([0, 1], [0, 1, 2]),               # |Δ| = 1
            _pair([3, 4], [3, 4, 5, 6, 7, 8]),      # |Δ| = 4
        ],
    }
    assert iter188(p_188_only, {}) is True
    assert _matcher()(p_188_only, {}) is False


def test_independent_of_iter189_strict_erasure() -> None:
    iter189 = CONDITION_REGISTRY[
        "input_palette_count_exceeds_output_palette_count"
    ]

    # Co-fire: strict erasure per pair AND |Δ| constant.
    p_cofire = {
        "pair_analyses": [
            _pair([0, 1, 2], [0, 1]),      # |Δ| = 1, |in|>|out|
            _pair([3, 4, 5], [3, 4]),      # |Δ| = 1, |in|>|out|
        ],
    }
    assert iter189(p_cofire, {}) is True
    assert _matcher()(p_cofire, {}) is True

    # iter 189 alone: strict erasure per pair but varying |Δ|.
    p_189_only = {
        "pair_analyses": [
            _pair([0, 1, 2], [0, 1]),                # |Δ| = 1
            _pair([3, 4, 5, 6, 7], [3]),             # |Δ| = 4
        ],
    }
    assert iter189(p_189_only, {}) is True
    assert _matcher()(p_189_only, {}) is False


def test_orthogonal_to_grid_size_preserved() -> None:
    # The whole-grid palette Δ-size constancy axis is orthogonal to
    # the per-pair input==output dim axis (the four-cell 2x2 co-fire
    # table).
    gsp = CONDITION_REGISTRY["grid_size_preserved"]

    # constant + preserved
    p1 = {
        "grid_size_preserved": True,
        "pair_analyses": [
            _pair([0, 1], [0, 1, 2]),
            _pair([3, 4], [3, 4, 5]),
        ],
    }
    assert _matcher()(p1, {}) is True and gsp(p1, {}) is True

    # constant + changed
    p2 = {
        "grid_size_preserved": False,
        "pair_analyses": [
            _pair([0, 1], [0, 1, 2], output_height=6, output_width=6,
                  size_match=False),
            _pair([3, 4], [3, 4, 5], output_height=6, output_width=6,
                  size_match=False),
        ],
    }
    assert _matcher()(p2, {}) is True and gsp(p2, {}) is False

    # not-constant + preserved
    p3 = {
        "grid_size_preserved": True,
        "pair_analyses": [
            _pair([0, 1], [0, 1, 2]),
            _pair([3, 4], [3, 4, 5, 6]),
        ],
    }
    assert _matcher()(p3, {}) is False and gsp(p3, {}) is True

    # not-constant + changed
    p4 = {
        "grid_size_preserved": False,
        "pair_analyses": [
            _pair([0, 1], [0, 1, 2], output_height=6, output_width=6,
                  size_match=False),
            _pair([3, 4], [3, 4, 5, 6], output_height=6, output_width=6,
                  size_match=False),
        ],
    }
    assert _matcher()(p4, {}) is False and gsp(p4, {}) is False


def test_orthogonal_to_input_color_uniform() -> None:
    # iter 14 inspects change-cells' input colour uniformity. The
    # whole-grid palette Δ-size constancy axis is INDEPENDENT.
    icu = CONDITION_REGISTRY["input_color_uniform"]

    # this matcher fires AND icu fires
    # Both pairs change colour 7 (icu requires a single uniform source
    # colour across every change-group cell on every pair). Both pairs
    # have |Δ| = 2 on the whole-grid palette (so this matcher fires).
    p0 = _pair(
        [0, 5, 7], [0, 5, 9],
        groups=[{
            "input_colors": [7],
            "output_colors": [9],
            "positions": [(0, 0)],
            "top_row": 0, "top_col": 0,
            "cell_count": 1,
        }],
        num_groups=1, total_changes=1,
    )
    p1 = _pair(
        [0, 6, 7], [0, 6, 8],
        groups=[{
            "input_colors": [7],
            "output_colors": [8],
            "positions": [(0, 0)],
            "top_row": 0, "top_col": 0,
            "cell_count": 1,
        }],
        num_groups=1, total_changes=1,
    )
    p_both = {"pair_analyses": [p0, p1]}
    assert _matcher()(p_both, {}) is True and icu(p_both, {}) is True

    # this matcher fires but icu does NOT (no change cells)
    p_no_changes = {
        "pair_analyses": [
            _pair([0, 1], [0, 1]),
            _pair([3, 4], [3, 4]),
        ],
    }
    assert _matcher()(p_no_changes, {}) is True
    assert icu(p_no_changes, {}) is False


# ──────────────────────────────────────────────────────────────────────────
# recognized_conditions wiring.
# ──────────────────────────────────────────────────────────────────────────

def test_recognized_conditions_includes_matcher_on_constant_delta() -> None:
    from agent.conditions import recognized_conditions
    # Each pair adds exactly one fresh output colour: iter 187 fires,
    # iter 188 fires, this matcher fires (|Δ| == 1 on every pair).
    patterns = {
        "pair_analyses": [
            _pair([0, 1], [0, 1, 2]),
            _pair([3, 4], [3, 4, 5]),
        ],
    }
    fired = recognized_conditions(patterns)
    assert MATCHER_NAME in fired, (
        f"{MATCHER_NAME!r} did not fire on constant-|Δ|=1 patterns dict; "
        f"got {fired!r}"
    )
    assert "input_palette_subset_of_output" in fired
    assert "output_palette_count_exceeds_input_palette_count" in fired


def test_recognized_conditions_excludes_on_varying_delta() -> None:
    from agent.conditions import recognized_conditions
    # iter 187 fires on both pairs (input ⊆ output), iter 188 fires
    # on both pairs (strict expansion), but |Δ| varies (1 vs 3) so
    # this matcher does NOT fire.
    patterns = {
        "pair_analyses": [
            _pair([0, 1], [0, 1, 2]),               # |Δ| = 1
            _pair([3, 4], [3, 4, 5, 6, 7]),         # |Δ| = 3
        ],
    }
    fired = recognized_conditions(patterns)
    assert "input_palette_subset_of_output" in fired
    assert "output_palette_count_exceeds_input_palette_count" in fired
    assert MATCHER_NAME not in fired, (
        f"{MATCHER_NAME!r} must NOT fire on varying-|Δ| patterns; got "
        f"{fired!r}"
    )


def test_recognized_conditions_fires_alongside_iter185_on_equality() -> None:
    # Iter 185 ⇒ this matcher (strict implication on |Δ| == 0).
    from agent.conditions import recognized_conditions
    patterns = {
        "pair_analyses": [
            _pair([0, 1, 2], [0, 1, 2]),
            _pair([3, 4], [3, 4]),
        ],
    }
    fired = recognized_conditions(patterns)
    assert "output_palette_equals_input" in fired
    assert MATCHER_NAME in fired, (
        f"{MATCHER_NAME!r} must fire on palette-equality (|Δ|==0 constant); "
        f"got {fired!r}"
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
