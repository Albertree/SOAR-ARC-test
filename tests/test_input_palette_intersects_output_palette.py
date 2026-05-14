"""
tests/test_input_palette_intersects_output_palette.py -- exercise the
iter-331 matcher
``agent.conditions.input_palette_intersects_output_palette``.

Pins the matcher's contract per
``agent/conditions/input_palette_intersects_output_palette.py``
docstring: every pair satisfies
``set(input_palette) & set(output_palette) != empty set``
on a non-empty ``pair_analyses`` list with both palettes shaped as
lists of non-bool ints. The whole-grid ANCHOR-PRESERVATION
precondition; the whole-grid analogue of iter 329's per-group
matcher.

Runs without pytest:

    python tests/test_input_palette_intersects_output_palette.py

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


MATCHER_NAME = "input_palette_intersects_output_palette"


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
# Positive cases -- the four sub-cells whose union is the territory
# of this matcher (equality, strict-erasure, strict-expansion, partial-
# overlap), plus orthogonal-axis fixtures.
# ──────────────────────────────────────────────────────────────────────────

def test_returns_true_on_palette_equality() -> None:
    # Equality (iter-185 territory): A == B implies non-empty
    # intersection (on non-empty palettes). Strict implication.
    patterns = {"pair_analyses": [_pair([0, 1, 2], [0, 1, 2])]}
    assert _matcher()(patterns, {}) is True


def test_returns_true_on_strict_output_subset_of_input() -> None:
    # Strict B ⊊ A (iter 184 ∧ ¬iter 185 territory): non-empty subset
    # implies non-empty intersection. Strict implication.
    patterns = {"pair_analyses": [_pair([0, 1, 2], [0, 1])]}
    assert _matcher()(patterns, {}) is True


def test_returns_true_on_strict_input_subset_of_output() -> None:
    # Strict A ⊊ B (iter 187 ∧ ¬iter 185 territory): non-empty subset
    # implies non-empty intersection. Strict implication.
    patterns = {"pair_analyses": [_pair([0, 1], [0, 1, 2])]}
    assert _matcher()(patterns, {}) is True


def test_returns_true_on_partial_overlap() -> None:
    # Partial-overlap territory: non-empty intersection with neither
    # side contained. Strict implication.
    patterns = {"pair_analyses": [_pair([0, 1, 2], [2, 3, 4])]}
    assert _matcher()(patterns, {}) is True


def test_returns_true_on_single_color_shared() -> None:
    # Minimal positive: a single shared colour suffices.
    patterns = {"pair_analyses": [_pair([0, 5, 7], [7, 8, 9])]}
    assert _matcher()(patterns, {}) is True


def test_returns_true_across_multiple_pairs_with_different_overlap_shapes() -> None:
    # Per-pair anchor preservation with different overlap shapes per
    # pair: equality, strict-erasure, strict-expansion, partial-
    # overlap. Universal-over-pairs semantic is satisfied.
    patterns = {
        "pair_analyses": [
            _pair([0, 1, 2], [0, 1, 2]),       # equality (shared: {0,1,2})
            _pair([3, 4, 5], [3, 4]),          # strict-erasure (shared: {3,4})
            _pair([6, 7], [6, 7, 8]),          # strict-expansion (shared: {6,7})
            _pair([0, 1, 2], [2, 3, 4]),       # partial-overlap (shared: {2})
        ],
    }
    assert _matcher()(patterns, {}) is True


def test_returns_true_with_duplicate_colours_in_palette_lists() -> None:
    # Palettes are lists, not sets; the matcher set-ifies them.
    # Duplicate entries on either side must not affect the verdict.
    patterns = {"pair_analyses": [_pair([0, 0, 1, 2, 2], [2, 2, 3])]}
    assert _matcher()(patterns, {}) is True


# ──────────────────────────────────────────────────────────────────────────
# Negative cases -- iter-186 disjoint territory and degenerate inputs.
# ──────────────────────────────────────────────────────────────────────────

def test_returns_false_when_palettes_are_disjoint() -> None:
    # Disjoint (iter-186 territory): empty intersection; anchor-
    # preservation requires non-empty intersection. STRICT mutual
    # exclusion on the non-empty-palette domain.
    patterns = {"pair_analyses": [_pair([0, 1, 2], [3, 4, 5])]}
    assert _matcher()(patterns, {}) is False


def test_returns_false_when_any_pair_is_disjoint() -> None:
    # Universal-over-pairs semantic: a single disjoint pair fails the
    # whole task.
    patterns = {
        "pair_analyses": [
            _pair([0, 1, 2], [2, 3, 4]),   # partial-overlap pair
            _pair([0, 1], [5, 6]),         # disjoint pair -- offending
            _pair([5, 6], [6, 7]),         # partial-overlap pair
        ],
    }
    assert _matcher()(patterns, {}) is False


def test_returns_false_on_empty_pair_analyses() -> None:
    # Fail-closed on empty input -- consistent with every other
    # matcher's posture (iters 1 / 13 / 17 / 20 / 22 / 33 / 182 / 183
    # / 184 / 185 / 186 / 187 / partial-overlap).
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
            _pair([0, 1, 2], [2, 3, 4]),
            "not-a-dict",
            _pair([5, 6], [6, 7]),
        ],
    }
    assert _matcher()(patterns, {}) is False


# ──────────────────────────────────────────────────────────────────────────
# Strict-type-gate cases (mirror iter 184 / 185 / 186 / 187 / partial-
# overlap whole-grid palette posture).
# ──────────────────────────────────────────────────────────────────────────

def test_returns_false_when_input_palette_missing() -> None:
    analysis = _pair([0, 1, 2], [2, 3, 4])
    del analysis["input_palette"]
    patterns = {"pair_analyses": [analysis]}
    assert _matcher()(patterns, {}) is False


def test_returns_false_when_output_palette_missing() -> None:
    analysis = _pair([0, 1, 2], [2, 3, 4])
    del analysis["output_palette"]
    patterns = {"pair_analyses": [analysis]}
    assert _matcher()(patterns, {}) is False


def test_returns_false_when_input_palette_is_not_list() -> None:
    for bad in (None, 42, "oops", {"a": 1}, (0, 1, 2), True, {0, 1, 2}):
        analysis = _pair([0, 1, 2], [2, 3, 4])
        analysis["input_palette"] = bad
        patterns = {"pair_analyses": [analysis]}
        assert _matcher()(patterns, {}) is False, (
            f"input_palette={bad!r} should not fire"
        )


def test_returns_false_when_output_palette_is_not_list() -> None:
    for bad in (None, 42, "oops", {"a": 1}, (2, 3, 4), True, {2, 3, 4}):
        analysis = _pair([0, 1, 2], [2, 3, 4])
        analysis["output_palette"] = bad
        patterns = {"pair_analyses": [analysis]}
        assert _matcher()(patterns, {}) is False, (
            f"output_palette={bad!r} should not fire"
        )


def test_returns_false_when_input_palette_contains_bool() -> None:
    # Python bools are an int subclass; strict gate must reject them
    # (same posture as the iter-182 / 183 dimensional matchers and
    # the iter 184 / 185 / 186 / 187 / partial-overlap palette
    # matchers).
    analysis = _pair([0, 1, 2], [2, 3, 4])
    analysis["input_palette"] = [0, True, 2]
    patterns = {"pair_analyses": [analysis]}
    assert _matcher()(patterns, {}) is False


def test_returns_false_when_output_palette_contains_bool() -> None:
    analysis = _pair([0, 1, 2], [2, 3, 4])
    analysis["output_palette"] = [False, 3, 4]
    patterns = {"pair_analyses": [analysis]}
    assert _matcher()(patterns, {}) is False


def test_returns_false_when_palette_contains_non_int() -> None:
    analysis = _pair([0, 1, 2], [2, 3, 4])
    analysis["input_palette"] = [0, "1", 2]
    patterns = {"pair_analyses": [analysis]}
    assert _matcher()(patterns, {}) is False

    analysis2 = _pair([0, 1, 2], [2, 3, 4])
    analysis2["output_palette"] = [2.0, 3.0, 4.0]
    patterns2 = {"pair_analyses": [analysis2]}
    assert _matcher()(patterns2, {}) is False


def test_returns_false_when_input_palette_empty() -> None:
    # Empty palette has empty intersection with anything; the
    # non-empty-intersection semantic gate rejects.
    patterns = {"pair_analyses": [_pair([], [2, 3])]}
    assert _matcher()(patterns, {}) is False


def test_returns_false_when_output_palette_empty() -> None:
    patterns = {"pair_analyses": [_pair([0, 1], [])]}
    assert _matcher()(patterns, {}) is False


# ──────────────────────────────────────────────────────────────────────────
# Behavioural-contract cases.
# ──────────────────────────────────────────────────────────────────────────

def test_is_side_effect_free_on_inputs() -> None:
    patterns = {
        "pair_analyses": [
            _pair([0, 1, 2], [2, 3, 4]),
            _pair([5, 6], [6, 7, 8]),
        ],
    }
    params = {"unused": 1}
    before_p = copy.deepcopy(patterns)
    before_q = copy.deepcopy(params)
    _matcher()(patterns, params)
    assert patterns == before_p, "matcher mutated patterns"
    assert params == before_q, "matcher mutated params"


def test_is_deterministic_across_repeats() -> None:
    patterns = {"pair_analyses": [_pair([0, 1, 2], [2, 3, 4])]}
    results = [_matcher()(patterns, {}) for _ in range(5)]
    assert len(set(results)) == 1, f"non-deterministic outputs: {results}"


def test_returned_value_is_boolean_not_truthy() -> None:
    # recognized_conditions filters on ``match(...) is True`` exactly,
    # so the matcher must return literal Booleans.
    out_true = _matcher()({"pair_analyses": [_pair([0, 1, 2], [2, 3, 4])]}, {})
    out_false = _matcher()({"pair_analyses": [_pair([0, 1, 2], [3, 4, 5])]}, {})
    assert out_true is True, f"expected literal True, got {out_true!r}"
    assert out_false is False, f"expected literal False, got {out_false!r}"


def test_params_ignored() -> None:
    # The matcher takes no params; any params dict must produce the
    # same verdict as ``{}``.
    patterns = {"pair_analyses": [_pair([0, 1, 2], [2, 3, 4])]}
    assert _matcher()(patterns, {}) is True
    assert _matcher()(patterns, {"magic": 1}) is True
    assert _matcher()(patterns, {"empty": True}) is True


def test_tolerates_erase_sentinel_13_in_palette() -> None:
    # The whole-grid posture (iter 184 / 185 / 186 / 187 / partial-
    # overlap) tolerates any int value -- including the iter-180
    # erase sentinel 13 -- since the upstream extractor handles range
    # validation. The non-empty-intersection semantic gate must still
    # apply.
    patterns = {"pair_analyses": [_pair([0, 13], [13, 1])]}
    assert _matcher()(patterns, {}) is True


def test_ignores_per_group_color_lists() -> None:
    # The matcher reads ONLY ``input_palette`` / ``output_palette``.
    # Per-group ``input_colors`` / ``output_colors`` on the change
    # cells are a different axis -- the matcher must ignore them.
    # Set per-group palettes to a strictly-disjoint shape: this would
    # cause iter 329 to reject, but this matcher must still fire on
    # the whole-grid intersection.
    analysis = _pair(
        [0, 1, 2], [2, 3, 4],
        groups=[{
            "input_colors": [0, 0, 0],
            "output_colors": [9, 9, 9],
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
    analysis = _pair([0, 1, 2], [2, 3, 4], input_height=7, input_width=9,
                     output_height=2, output_width=3, size_match=False)
    patterns = {"pair_analyses": [analysis]}
    assert _matcher()(patterns, {}) is True


# ──────────────────────────────────────────────────────────────────────────
# Orthogonality / mutual-exclusion matrix against existing axes.
# ──────────────────────────────────────────────────────────────────────────

def test_strict_implication_by_output_palette_equals_input() -> None:
    # iter 185 (equality) STRICTLY IMPLIES this matcher on the
    # non-empty-palette domain: equal non-empty sets have non-empty
    # intersection. The converse does not hold (partial-overlap fires
    # this matcher without firing iter 185).
    eq = CONDITION_REGISTRY["output_palette_equals_input"]

    # equality fires -- this matcher also fires.
    p1 = {"pair_analyses": [_pair([0, 1, 2], [0, 1, 2])]}
    assert _matcher()(p1, {}) is True and eq(p1, {}) is True

    # partial-overlap fires this matcher -- iter 185 does not.
    p2 = {"pair_analyses": [_pair([0, 1, 2], [2, 3, 4])]}
    assert _matcher()(p2, {}) is True and eq(p2, {}) is False


def test_strict_implication_by_output_palette_subset_of_input() -> None:
    # iter 184 STRICTLY IMPLIES this matcher on the non-empty-output-
    # palette domain (non-empty B ⊆ A has non-empty intersection with
    # A). The converse does not hold (disjoint A and B fail iter 184
    # AND this matcher; partial-overlap fires this matcher without
    # iter 184).
    sub = CONDITION_REGISTRY["output_palette_subset_of_input"]

    # iter 184 fires (strict B ⊊ A) -- this matcher also fires.
    p1 = {"pair_analyses": [_pair([0, 1, 2], [0, 1])]}
    assert _matcher()(p1, {}) is True and sub(p1, {}) is True

    # partial-overlap fires this matcher -- iter 184 does not.
    p2 = {"pair_analyses": [_pair([0, 1, 2], [2, 3, 4])]}
    assert _matcher()(p2, {}) is True and sub(p2, {}) is False


def test_strict_implication_by_input_palette_subset_of_output() -> None:
    # iter 187 STRICTLY IMPLIES this matcher on the non-empty-input-
    # palette domain.
    sub = CONDITION_REGISTRY["input_palette_subset_of_output"]

    # iter 187 fires (strict A ⊊ B) -- this matcher also fires.
    p1 = {"pair_analyses": [_pair([0, 1], [0, 1, 2])]}
    assert _matcher()(p1, {}) is True and sub(p1, {}) is True

    # partial-overlap fires this matcher -- iter 187 does not.
    p2 = {"pair_analyses": [_pair([0, 1, 2], [2, 3, 4])]}
    assert _matcher()(p2, {}) is True and sub(p2, {}) is False


def test_strict_implication_by_output_palette_partial_overlap() -> None:
    # ``output_palette_partial_overlap_with_input_palette`` STRICTLY
    # IMPLIES this matcher (its first clause is non-empty
    # intersection). The converse does not hold (equality / subset /
    # superset fire this matcher without firing partial-overlap).
    po = CONDITION_REGISTRY["output_palette_partial_overlap_with_input_palette"]

    # partial-overlap fires -- this matcher also fires.
    p1 = {"pair_analyses": [_pair([0, 1, 2], [2, 3, 4])]}
    assert _matcher()(p1, {}) is True and po(p1, {}) is True

    # equality fires this matcher -- partial-overlap does not.
    p2 = {"pair_analyses": [_pair([0, 1, 2], [0, 1, 2])]}
    assert _matcher()(p2, {}) is True and po(p2, {}) is False


def test_mutually_exclusive_with_output_palette_disjoint_from_input() -> None:
    # iter 186 (disjoint) is STRICTLY MUTUALLY EXCLUSIVE with this
    # matcher on the non-empty-palette domain (empty intersection vs
    # non-empty intersection). The exact partitioner cut.
    disj = CONDITION_REGISTRY["output_palette_disjoint_from_input"]

    # this matcher fires -- iter 186 does not.
    p1 = {"pair_analyses": [_pair([0, 1, 2], [2, 3, 4])]}
    assert _matcher()(p1, {}) is True and disj(p1, {}) is False

    # iter 186 fires -- this matcher does not.
    p2 = {"pair_analyses": [_pair([0, 1, 2], [3, 4, 5])]}
    assert _matcher()(p2, {}) is False and disj(p2, {}) is True


def test_independent_from_per_group_anchor_preservation() -> None:
    # Iter 329 (per-group anchor preservation) is INDEPENDENT from
    # this matcher (whole-grid scope). Build two fixtures that prove
    # the two truth values can vary independently.
    per_group = CONDITION_REGISTRY["change_palette_intersection_nonempty_per_group"]

    # Whole-grid palettes share a colour (background "0"), but the
    # per-group change-cell palettes are strictly disjoint within
    # each blob. iter 329 REJECTS, this matcher FIRES.
    p1 = {
        "pair_analyses": [
            _pair(
                [0, 1, 2], [0, 3, 4],
                num_groups=1, total_changes=2,
                groups=[{
                    "input_colors": [1, 2],
                    "output_colors": [3, 4],
                    "positions": [(0, 1), (1, 1)],
                    "top_row": 0, "top_col": 1, "cell_count": 2,
                }],
            ),
        ],
    }
    assert _matcher()(p1, {}) is True and per_group(p1, {}) is False

    # Whole-grid palettes are strictly disjoint (no shared colour),
    # but the per-group input AND output colour-list share a colour
    # within the changed cells via overlapping list contents. This
    # demonstrates the orthogonality: a per-group claim with shared
    # input AND output cells does not imply whole-grid overlap.
    p2 = {
        "pair_analyses": [
            _pair(
                [0, 1], [2, 3],
                num_groups=1, total_changes=1,
                groups=[{
                    "input_colors": [5],
                    "output_colors": [5],
                    "positions": [(0, 0)],
                    "top_row": 0, "top_col": 0, "cell_count": 1,
                }],
            ),
        ],
    }
    # This fixture is artificial -- whole-grid {0,1}∩{2,3}=∅ -- so
    # this matcher REJECTS while per-group's intersection on
    # group-internal lists {5}∩{5}={5} fires iter 329.
    assert _matcher()(p2, {}) is False and per_group(p2, {}) is True


def test_strict_implication_by_identity_transformation() -> None:
    # Identity tasks have zero changed cells AND palettes equal per
    # pair; identity therefore STRICTLY IMPLIES this matcher
    # (whenever input_palette is non-empty).
    ident = CONDITION_REGISTRY["identity_transformation"]

    # identity + non-empty palette: both fire.
    p1 = {
        "pair_analyses": [
            _pair([0, 1, 2], [0, 1, 2], total_changes=0, num_groups=0,
                  groups=[]),
        ],
    }
    assert _matcher()(p1, {}) is True and ident(p1, {}) is True

    # non-identity (changed cells) but anchored: this matcher fires,
    # identity does not.
    p2 = {
        "pair_analyses": [
            _pair(
                [0, 1, 2], [0, 3, 4],
                total_changes=2, num_groups=1,
                groups=[{
                    "input_colors": [1, 2], "output_colors": [3, 4],
                    "positions": [(0, 1), (1, 1)],
                    "top_row": 0, "top_col": 1, "cell_count": 2,
                }],
            ),
        ],
    }
    assert _matcher()(p2, {}) is True and ident(p2, {}) is False


def test_orthogonal_to_grid_size_preserved() -> None:
    # Whole-grid palette intersection-nonempty is orthogonal to the
    # per-pair input==output dim axis.
    gsp = CONDITION_REGISTRY["grid_size_preserved"]

    # intersect + preserved -- both fire
    p1 = {
        "grid_size_preserved": True,
        "pair_analyses": [_pair([0, 1, 2], [2, 3, 4])],
    }
    assert _matcher()(p1, {}) is True and gsp(p1, {}) is True

    # intersect + changed -- only this matcher fires
    p2 = {
        "grid_size_preserved": False,
        "pair_analyses": [
            _pair([0, 1, 2], [2, 3, 4], output_height=6, output_width=6,
                  size_match=False),
        ],
    }
    assert _matcher()(p2, {}) is True and gsp(p2, {}) is False

    # disjoint + preserved -- only preserved fires
    p3 = {
        "grid_size_preserved": True,
        "pair_analyses": [_pair([0, 1], [2, 3])],
    }
    assert _matcher()(p3, {}) is False and gsp(p3, {}) is True


def test_recognized_conditions_includes_intersects() -> None:
    from agent.conditions import recognized_conditions
    patterns = {"pair_analyses": [_pair([0, 1, 2], [2, 3, 4])]}
    fired = recognized_conditions(patterns)
    assert MATCHER_NAME in fired, (
        f"{MATCHER_NAME!r} did not fire on a clearly-overlapping "
        f"patterns dict; got {fired!r}"
    )


def test_recognized_conditions_excludes_intersects_on_disjoint() -> None:
    # Strict mutual-exclusion witness: on a disjoint fixture, iter
    # 186 fires AND this matcher is EXCLUDED -- not a co-fire cell.
    from agent.conditions import recognized_conditions
    patterns = {"pair_analyses": [_pair([0, 1, 2], [3, 4, 5])]}
    fired = recognized_conditions(patterns)
    assert MATCHER_NAME not in fired, (
        f"{MATCHER_NAME!r} fired on a disjoint fixture; got {fired!r}"
    )
    assert "output_palette_disjoint_from_input" in fired, (
        f"iter 186 did not fire on a disjoint fixture; got {fired!r}"
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
