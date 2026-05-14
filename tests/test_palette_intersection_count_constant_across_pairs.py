"""
tests/test_palette_intersection_count_constant_across_pairs.py --
exercise the iter-191 matcher
``agent.conditions.palette_intersection_count_constant_across_pairs``
(new in this iter).

Pins the matcher's contract per
``agent/conditions/palette_intersection_count_constant_across_pairs.py``
docstring: every pair's
``len(set(input_palette) & set(output_palette))`` is bit-identical
across pairs on a non-empty ``pair_analyses`` list with both palettes
shaped as lists of non-bool ints. Second entry on the **cross-pair-
constancy** sub-axis of the palette axis (iter 190 was first, on the
symmetric-difference SIZE; this matcher is the DUAL on the
intersection SIZE).

Runs without pytest:

    python tests/test_palette_intersection_count_constant_across_pairs.py

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


MATCHER_NAME = "palette_intersection_count_constant_across_pairs"


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
    # 40 / 42 / 190 family posture: cross-pair constancy fires on
    # single-pair tasks as long as the one pair is well-typed.
    patterns = {"pair_analyses": [_pair([0, 1, 2], [0, 3])]}
    assert _matcher()(patterns, {}) is True


def test_returns_true_when_intersection_is_zero_on_every_pair() -> None:
    # Disjoint palettes per pair give |∩| == 0 on every pair. The
    # cross-pair constancy holds with canonical value 0. Iter 186
    # ⇒ this matcher (strict implication on the universal-over-pairs
    # gate).
    patterns = {
        "pair_analyses": [
            _pair([0, 1], [2, 3]),
            _pair([4, 5], [6, 7]),
            _pair([8], [9]),
        ],
    }
    assert _matcher()(patterns, {}) is True


def test_returns_true_when_intersection_is_one_on_every_pair() -> None:
    # The "exactly one anchor colour preserved per pair" pattern.
    patterns = {
        "pair_analyses": [
            _pair([0, 1], [0, 2]),         # ∩ = {0} → 1
            _pair([3, 4], [3, 5]),         # ∩ = {3} → 1
        ],
    }
    assert _matcher()(patterns, {}) is True


def test_returns_true_when_intersection_is_two_on_every_pair() -> None:
    # Two anchor colours preserved per pair.
    patterns = {
        "pair_analyses": [
            _pair([0, 1, 2], [0, 1, 3]),   # ∩ = {0, 1} → 2
            _pair([4, 5, 6], [4, 5, 7]),   # ∩ = {4, 5} → 2
        ],
    }
    assert _matcher()(patterns, {}) is True


def test_returns_true_with_duplicates_in_palettes() -> None:
    # Intersection size is computed on SETS; duplicates in either
    # list must not affect the verdict.
    patterns = {
        "pair_analyses": [
            _pair([0, 0, 1, 1, 2], [0, 0, 1, 1, 3]),  # set({0,1,2}) ∩ set({0,1,3}) = {0,1} → 2
            _pair([4, 5, 5, 6], [4, 4, 5, 7]),        # set({4,5,6}) ∩ set({4,5,7}) = {4,5} → 2
        ],
    }
    assert _matcher()(patterns, {}) is True


def test_returns_true_when_both_palettes_empty_on_every_pair() -> None:
    # Degenerate empty-empty case: |∩| == 0 on every pair → constant.
    # The matcher fires. The upstream extractor is responsible for
    # non-degenerate grids; honour what is emitted.
    patterns = {
        "pair_analyses": [
            _pair([], []),
            _pair([], []),
        ],
    }
    assert _matcher()(patterns, {}) is True


def test_returns_true_on_equal_palettes_with_constant_size() -> None:
    # Iter-185-style equality on every pair (which gives |∩| ==
    # |input| per pair) co-fires with this matcher only if the
    # palette size is also constant across pairs.
    patterns = {
        "pair_analyses": [
            _pair([0, 1, 2], [0, 1, 2]),   # ∩ = {0,1,2} → 3
            _pair([3, 4, 5], [3, 4, 5]),   # ∩ = {3,4,5} → 3
        ],
    }
    assert _matcher()(patterns, {}) is True


# ──────────────────────────────────────────────────────────────────────────
# Negative cases.
# ──────────────────────────────────────────────────────────────────────────

def test_returns_false_when_intersection_varies_across_pairs() -> None:
    # Pair 0: |∩| = 0 (disjoint). Pair 1: |∩| = 1. Not constant.
    patterns = {
        "pair_analyses": [
            _pair([0, 1], [2, 3]),
            _pair([3, 4], [3, 5]),
        ],
    }
    assert _matcher()(patterns, {}) is False


def test_returns_false_when_one_pair_preserves_extra_color() -> None:
    # Pair 0 preserves one colour. Pair 1 preserves two. Different |∩|.
    patterns = {
        "pair_analyses": [
            _pair([0, 1, 2], [0, 3]),      # ∩ = {0} → 1
            _pair([4, 5, 6], [4, 5, 7]),   # ∩ = {4, 5} → 2
        ],
    }
    assert _matcher()(patterns, {}) is False


def test_returns_false_on_mixed_empty_and_non_empty_pairs() -> None:
    # Pair 0: both empty → |∩| = 0. Pair 1: |∩| ≥ 1.
    patterns = {
        "pair_analyses": [
            _pair([], []),
            _pair([0, 1], [0, 2]),         # ∩ = {0} → 1
        ],
    }
    assert _matcher()(patterns, {}) is False


def test_returns_false_on_equal_palettes_with_varying_size() -> None:
    # Iter 185 (equality) does NOT strictly imply this matcher: equal
    # palettes of varying sizes have varying intersection size.
    patterns = {
        "pair_analyses": [
            _pair([0, 1], [0, 1]),         # ∩ = {0,1} → 2
            _pair([2, 3, 4], [2, 3, 4]),   # ∩ = {2,3,4} → 3
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
        {"pair_analyses": [_pair([0, 1], [0, 2]), _pair([3, 4, 5], [3, 4, 6])]},
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

def test_iter186_strictly_implies_this_matcher() -> None:
    # Iter 186 (disjoint) ⇒ |∩| == 0 on every pair, constant. Strict
    # implication: iter 186 ⇒ this matcher (with canonical value 0).
    iter186 = CONDITION_REGISTRY["output_palette_disjoint_from_input"]
    patterns = {
        "pair_analyses": [
            _pair([0, 1], [2, 3]),
            _pair([4, 5], [6, 7]),
            _pair([8], [9]),
        ],
    }
    assert iter186(patterns, {}) is True
    assert _matcher()(patterns, {}) is True


def test_this_matcher_fires_without_iter186() -> None:
    # The reverse of the previous test does NOT hold: this matcher
    # fires on any constant |∩|, not only on |∩| == 0. Iter 186 fires
    # only on |∩| == 0.
    iter186 = CONDITION_REGISTRY["output_palette_disjoint_from_input"]
    patterns = {
        "pair_analyses": [
            _pair([0, 1], [0, 2]),         # ∩ = {0} → 1
            _pair([3, 4], [3, 5]),         # ∩ = {3} → 1
        ],
    }
    assert iter186(patterns, {}) is False
    assert _matcher()(patterns, {}) is True


def test_independent_of_iter185_equality() -> None:
    # Iter 185 (palette equality) and this matcher are INDEPENDENT.
    iter185 = CONDITION_REGISTRY["output_palette_equals_input"]

    # Co-fire: equality with constant palette size.
    p_cofire = {
        "pair_analyses": [
            _pair([0, 1, 2], [0, 1, 2]),
            _pair([3, 4, 5], [3, 4, 5]),
        ],
    }
    assert iter185(p_cofire, {}) is True
    assert _matcher()(p_cofire, {}) is True

    # iter 185 alone: equal palettes of varying sizes per pair → |∩|
    # varies across pairs.
    p_185_only = {
        "pair_analyses": [
            _pair([0, 1], [0, 1]),         # |∩| = 2
            _pair([3, 4, 5], [3, 4, 5]),   # |∩| = 3
        ],
    }
    assert iter185(p_185_only, {}) is True
    assert _matcher()(p_185_only, {}) is False


def test_independent_of_iter184_subset() -> None:
    # Iter 184 (output ⊆ input) and this matcher are independent.
    iter184 = CONDITION_REGISTRY["output_palette_subset_of_input"]

    # Co-fire: every pair has output ⊆ input AND |output| == 2.
    # (Intersection equals output palette per pair under the subset.)
    p_cofire = {
        "pair_analyses": [
            _pair([0, 1, 2], [0, 1]),      # ∩ = {0, 1} → 2
            _pair([3, 4, 5], [3, 4]),      # ∩ = {3, 4} → 2
        ],
    }
    assert iter184(p_cofire, {}) is True
    assert _matcher()(p_cofire, {}) is True

    # iter 184 alone: subset per pair but varying output-palette size.
    p_184_only = {
        "pair_analyses": [
            _pair([0, 1, 2], [0, 1]),      # ∩ = {0, 1} → 2
            _pair([3, 4, 5, 6], [3]),      # ∩ = {3} → 1
        ],
    }
    assert iter184(p_184_only, {}) is True
    assert _matcher()(p_184_only, {}) is False


def test_independent_of_iter187_input_subset() -> None:
    iter187 = CONDITION_REGISTRY["input_palette_subset_of_output"]

    # Co-fire: input ⊆ output per pair AND |input| constant.
    p_cofire = {
        "pair_analyses": [
            _pair([0, 1], [0, 1, 2]),      # ∩ = {0, 1} → 2
            _pair([3, 4], [3, 4, 5]),      # ∩ = {3, 4} → 2
        ],
    }
    assert iter187(p_cofire, {}) is True
    assert _matcher()(p_cofire, {}) is True

    # iter 187 alone: input ⊆ output per pair but varying |input|.
    p_187_only = {
        "pair_analyses": [
            _pair([0, 1], [0, 1, 2]),      # ∩ = {0, 1} → 2
            _pair([3], [3, 4, 5]),         # ∩ = {3} → 1
        ],
    }
    assert iter187(p_187_only, {}) is True
    assert _matcher()(p_187_only, {}) is False


def test_independent_of_iter188_strict_expansion() -> None:
    iter188 = CONDITION_REGISTRY[
        "output_palette_count_exceeds_input_palette_count"
    ]

    # Co-fire: strict expansion per pair AND |∩| constant.
    p_cofire = {
        "pair_analyses": [
            _pair([0, 1], [0, 1, 2]),      # ∩ = 2, |out|>|in|
            _pair([3, 4], [3, 4, 5]),      # ∩ = 2, |out|>|in|
        ],
    }
    assert iter188(p_cofire, {}) is True
    assert _matcher()(p_cofire, {}) is True

    # iter 188 alone: strict expansion per pair but varying |∩|.
    p_188_only = {
        "pair_analyses": [
            _pair([0, 1], [0, 1, 2]),                  # ∩ = 2
            _pair([3], [3, 4, 5, 6]),                  # ∩ = 1
        ],
    }
    assert iter188(p_188_only, {}) is True
    assert _matcher()(p_188_only, {}) is False


def test_independent_of_iter189_strict_erasure() -> None:
    iter189 = CONDITION_REGISTRY[
        "input_palette_count_exceeds_output_palette_count"
    ]

    # Co-fire: strict erasure per pair AND |∩| constant.
    p_cofire = {
        "pair_analyses": [
            _pair([0, 1, 2], [0, 1]),      # ∩ = 2, |in|>|out|
            _pair([3, 4, 5], [3, 4]),      # ∩ = 2, |in|>|out|
        ],
    }
    assert iter189(p_cofire, {}) is True
    assert _matcher()(p_cofire, {}) is True

    # iter 189 alone: strict erasure per pair but varying |∩|.
    p_189_only = {
        "pair_analyses": [
            _pair([0, 1, 2], [0, 1]),                  # ∩ = 2
            _pair([3, 4, 5, 6], [3]),                  # ∩ = 1
        ],
    }
    assert iter189(p_189_only, {}) is True
    assert _matcher()(p_189_only, {}) is False


def test_independent_of_iter190_symmetric_difference() -> None:
    # Iter 190 (|Δ| constant) is the DUAL on the symmetric-difference
    # SIZE. INDEPENDENT: can co-fire and can each fire alone.
    iter190 = CONDITION_REGISTRY[
        "palette_symmetric_difference_constant_across_pairs"
    ]

    # Co-fire: both palettes constant per pair → both |Δ| and |∩|
    # constant.
    p_cofire = {
        "pair_analyses": [
            _pair([0, 1, 2], [0, 1, 3]),   # |Δ| = 2, |∩| = 2
            _pair([4, 5, 6], [4, 5, 7]),   # |Δ| = 2, |∩| = 2
        ],
    }
    assert iter190(p_cofire, {}) is True
    assert _matcher()(p_cofire, {}) is True

    # iter 190 alone: |Δ| constant but |∩| varies.
    p_190_only = {
        "pair_analyses": [
            _pair([0, 1], [2, 3]),          # |Δ| = 4, |∩| = 0
            _pair([0, 1, 2], [0, 1, 3]),    # |Δ| = 2, |∩| = 2  → |Δ| varies actually
        ],
    }
    # Adjust: need |Δ| constant but |∩| varies. Try:
    #   pair 0: input {0,1}, output {0,2} → |Δ|=2, |∩|=1
    #   pair 1: input {3,4,5}, output {6,7,8} → |Δ|=6, |∩|=0
    # That has both varying. Try:
    #   pair 0: input {0,1,2}, output {0,3,4} → |Δ|={1,2,3,4}=4, |∩|={0}=1
    #   pair 1: input {5,6}, output {7,8} → |Δ|={5,6,7,8}=4, |∩|={}=0
    p_190_only = {
        "pair_analyses": [
            _pair([0, 1, 2], [0, 3, 4]),   # |Δ| = 4, |∩| = 1
            _pair([5, 6], [7, 8]),         # |Δ| = 4, |∩| = 0
        ],
    }
    assert iter190(p_190_only, {}) is True
    assert _matcher()(p_190_only, {}) is False

    # this matcher alone: |∩| constant but |Δ| varies.
    #   pair 0: input {0,1}, output {0,2} → |Δ|=2, |∩|=1
    #   pair 1: input {3,4,5}, output {3,6,7,8} → |Δ|={4,5,6,7,8}=5, |∩|=1
    p_191_only = {
        "pair_analyses": [
            _pair([0, 1], [0, 2]),               # |Δ| = 2, |∩| = 1
            _pair([3, 4, 5], [3, 6, 7, 8]),      # |Δ| = 5, |∩| = 1
        ],
    }
    assert iter190(p_191_only, {}) is False
    assert _matcher()(p_191_only, {}) is True


def test_independent_of_iter13_identity() -> None:
    # Iter 13 (identity_transformation) does NOT strictly imply this
    # matcher: identity with varying palette sizes per pair has
    # varying intersection size.
    identity = CONDITION_REGISTRY["identity_transformation"]

    # Co-fire: identity with constant palette size.
    p_cofire = {
        "grid_size_preserved": True,
        "pair_analyses": [
            _pair([0, 1, 2], [0, 1, 2]),   # |∩| = 3
            _pair([3, 4, 5], [3, 4, 5]),   # |∩| = 3
        ],
    }
    assert identity(p_cofire, {}) is True
    assert _matcher()(p_cofire, {}) is True

    # identity alone: identity with varying palette sizes.
    p_identity_only = {
        "grid_size_preserved": True,
        "pair_analyses": [
            _pair([0, 1], [0, 1]),         # |∩| = 2
            _pair([2, 3, 4], [2, 3, 4]),   # |∩| = 3
        ],
    }
    assert identity(p_identity_only, {}) is True
    assert _matcher()(p_identity_only, {}) is False


def test_orthogonal_to_grid_size_preserved() -> None:
    # The whole-grid palette ∩-size constancy axis is orthogonal to
    # the per-pair input==output dim axis (the four-cell 2x2 co-fire
    # table).
    gsp = CONDITION_REGISTRY["grid_size_preserved"]

    # constant + preserved
    p1 = {
        "grid_size_preserved": True,
        "pair_analyses": [
            _pair([0, 1], [0, 2]),
            _pair([3, 4], [3, 5]),
        ],
    }
    assert _matcher()(p1, {}) is True and gsp(p1, {}) is True

    # constant + changed
    p2 = {
        "grid_size_preserved": False,
        "pair_analyses": [
            _pair([0, 1], [0, 2], output_height=6, output_width=6,
                  size_match=False),
            _pair([3, 4], [3, 5], output_height=6, output_width=6,
                  size_match=False),
        ],
    }
    assert _matcher()(p2, {}) is True and gsp(p2, {}) is False

    # not-constant + preserved
    p3 = {
        "grid_size_preserved": True,
        "pair_analyses": [
            _pair([0, 1], [0, 2]),          # |∩| = 1
            _pair([3, 4], [3, 4, 5]),       # |∩| = 2
        ],
    }
    assert _matcher()(p3, {}) is False and gsp(p3, {}) is True

    # not-constant + changed
    p4 = {
        "grid_size_preserved": False,
        "pair_analyses": [
            _pair([0, 1], [0, 2], output_height=6, output_width=6,
                  size_match=False),
            _pair([3, 4], [3, 4, 5], output_height=6, output_width=6,
                  size_match=False),
        ],
    }
    assert _matcher()(p4, {}) is False and gsp(p4, {}) is False


def test_orthogonal_to_input_color_uniform() -> None:
    # iter 14 inspects change-cells' input colour uniformity. The
    # whole-grid palette ∩-size constancy axis is INDEPENDENT.
    icu = CONDITION_REGISTRY["input_color_uniform"]

    # this matcher fires AND icu fires
    # Both pairs change colour 7 (icu requires a single uniform source
    # colour across every change-group cell on every pair). Both pairs
    # have |∩| = 2 on the whole-grid palette (so this matcher fires).
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
            _pair([0, 1], [0, 2]),       # |∩| = 1
            _pair([3, 4], [3, 5]),       # |∩| = 1
        ],
    }
    assert _matcher()(p_no_changes, {}) is True
    assert icu(p_no_changes, {}) is False


# ──────────────────────────────────────────────────────────────────────────
# recognized_conditions wiring.
# ──────────────────────────────────────────────────────────────────────────

def test_recognized_conditions_includes_matcher_on_constant_intersection() -> None:
    from agent.conditions import recognized_conditions
    # Each pair preserves exactly one anchor colour and adds one
    # fresh output colour: iter 187 fires, iter 188 fires, this
    # matcher fires (|∩| == 1 on every pair). Iter 190 also fires
    # (|Δ| == 1 on every pair).
    patterns = {
        "pair_analyses": [
            _pair([0, 1], [0, 2]),
            _pair([3, 4], [3, 5]),
        ],
    }
    fired = recognized_conditions(patterns)
    assert MATCHER_NAME in fired, (
        f"{MATCHER_NAME!r} did not fire on constant-|∩|=1 patterns dict; "
        f"got {fired!r}"
    )
    assert "palette_symmetric_difference_constant_across_pairs" in fired


def test_recognized_conditions_excludes_on_varying_intersection() -> None:
    from agent.conditions import recognized_conditions
    # Subset per pair but varying intersection size.
    patterns = {
        "pair_analyses": [
            _pair([0, 1, 2], [0, 1]),      # |∩| = 2
            _pair([3, 4, 5, 6], [3]),      # |∩| = 1
        ],
    }
    fired = recognized_conditions(patterns)
    assert "output_palette_subset_of_input" in fired
    assert MATCHER_NAME not in fired, (
        f"{MATCHER_NAME!r} must NOT fire on varying-|∩| patterns; got "
        f"{fired!r}"
    )


def test_recognized_conditions_fires_alongside_iter186_on_disjoint() -> None:
    # Iter 186 ⇒ this matcher (strict implication on |∩| == 0).
    from agent.conditions import recognized_conditions
    patterns = {
        "pair_analyses": [
            _pair([0, 1], [2, 3]),
            _pair([4, 5], [6, 7]),
        ],
    }
    fired = recognized_conditions(patterns)
    assert "output_palette_disjoint_from_input" in fired
    assert MATCHER_NAME in fired, (
        f"{MATCHER_NAME!r} must fire on disjoint palettes (|∩|==0 constant); "
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
