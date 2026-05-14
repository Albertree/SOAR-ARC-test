"""
tests/test_output_palette_disjoint_from_input.py -- exercise the
iter-186 matcher ``agent.conditions.output_palette_disjoint_from_input``
(new in this iter).

Pins the matcher's contract per
``agent/conditions/output_palette_disjoint_from_input.py`` docstring:
every pair's ``set(output_palette) & set(input_palette) == empty`` on
a non-empty ``pair_analyses`` list with both palettes shaped as lists
of non-bool ints. The dual of iter-184's subset matcher and the third
slot on the whole-grid colour palette axis (alongside iter 185's
equality matcher).

Runs without pytest:

    python tests/test_output_palette_disjoint_from_input.py

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


MATCHER_NAME = "output_palette_disjoint_from_input"


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

def test_returns_true_when_palettes_are_fully_disjoint() -> None:
    # The canonical positive case: every output colour is fresh.
    patterns = {"pair_analyses": [_pair([0, 1, 2], [3, 4, 5])]}
    assert _matcher()(patterns, {}) is True


def test_returns_true_on_single_color_disjoint_grids() -> None:
    # Input monochrome with colour 0, output monochrome with colour 5
    # -- disjoint singletons are still disjoint.
    patterns = {"pair_analyses": [_pair([0], [5])]}
    assert _matcher()(patterns, {}) is True


def test_returns_true_when_palettes_disjoint_with_duplicates() -> None:
    # The contract is set-disjointness, so duplicates within a single
    # list do not change the set and must not break the gate.
    patterns = {"pair_analyses": [_pair([0, 0, 1], [3, 3, 4, 4])]}
    assert _matcher()(patterns, {}) is True


def test_returns_true_across_multiple_pairs_all_disjoint() -> None:
    # Per-pair disjointness is independent across pairs; varying
    # palettes are allowed as long as each pair satisfies the gate.
    patterns = {
        "pair_analyses": [
            _pair([0, 1], [2, 3]),
            _pair([4], [5, 6]),
            _pair([7, 8], [9]),
        ],
    }
    assert _matcher()(patterns, {}) is True


def test_returns_true_when_output_palette_empty() -> None:
    # Empty output palette: set-disjointness holds vacuously
    # (empty & anything == empty). Mirrors iter 184 / 185's empty-
    # palette posture.
    patterns = {"pair_analyses": [_pair([0, 1, 2], [])]}
    assert _matcher()(patterns, {}) is True


def test_returns_true_when_input_palette_empty() -> None:
    # Empty input palette: same vacuous truth on the other side.
    patterns = {"pair_analyses": [_pair([], [3, 4])]}
    assert _matcher()(patterns, {}) is True


def test_returns_true_when_both_palettes_empty() -> None:
    # Vacuously disjoint on both sides.
    patterns = {"pair_analyses": [_pair([], [])]}
    assert _matcher()(patterns, {}) is True


# ──────────────────────────────────────────────────────────────────────────
# Negative cases.
# ──────────────────────────────────────────────────────────────────────────

def test_returns_false_on_single_shared_color() -> None:
    # A single shared colour breaks the gate, even when most of the
    # palette is fresh.
    patterns = {"pair_analyses": [_pair([0, 1, 2], [2, 3, 4])]}
    assert _matcher()(patterns, {}) is False


def test_returns_false_on_palette_equality() -> None:
    # Iter-185's equality case -- mutually exclusive with disjoint on
    # any non-empty palette.
    patterns = {"pair_analyses": [_pair([0, 1, 2], [0, 1, 2])]}
    assert _matcher()(patterns, {}) is False


def test_returns_false_on_palette_subset() -> None:
    # Iter-184's subset case -- mutually exclusive with disjoint on
    # any non-empty output palette.
    patterns = {"pair_analyses": [_pair([0, 1, 2], [0, 1])]}
    assert _matcher()(patterns, {}) is False


def test_returns_false_on_palette_superset() -> None:
    # The output palette strictly contains the input palette -- not
    # disjoint because the input colours appear on the output side.
    patterns = {"pair_analyses": [_pair([0, 1], [0, 1, 2, 3])]}
    assert _matcher()(patterns, {}) is False


def test_returns_false_on_palette_partial_overlap() -> None:
    # Partial overlap (one shared, one fresh on each side) -- breaks
    # disjointness because the intersection is non-empty.
    patterns = {"pair_analyses": [_pair([0, 1, 2], [1, 3, 4])]}
    assert _matcher()(patterns, {}) is False


def test_returns_false_when_any_pair_fails_the_gate() -> None:
    # Universal-over-pairs semantic: a single failing pair fails the
    # whole task.
    patterns = {
        "pair_analyses": [
            _pair([0, 1], [2, 3]),
            _pair([4, 5], [5, 6]),  # offending pair (shares 5)
            _pair([7], [8]),
        ],
    }
    assert _matcher()(patterns, {}) is False


def test_returns_false_on_empty_pair_analyses() -> None:
    # Fail-closed on empty input -- consistent with every other
    # matcher's posture (iters 1 / 13 / 17 / 20 / 22 / 33 / 182 / 183 /
    # 184 / 185).
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
            _pair([0, 1], [2, 3]),
            "not-a-dict",
            _pair([4, 5], [6, 7]),
        ],
    }
    assert _matcher()(patterns, {}) is False


# ──────────────────────────────────────────────────────────────────────────
# Strict-type-gate cases.
# ──────────────────────────────────────────────────────────────────────────

def test_returns_false_when_input_palette_missing() -> None:
    analysis = _pair([0, 1], [2, 3])
    del analysis["input_palette"]
    patterns = {"pair_analyses": [analysis]}
    assert _matcher()(patterns, {}) is False


def test_returns_false_when_output_palette_missing() -> None:
    analysis = _pair([0, 1], [2, 3])
    del analysis["output_palette"]
    patterns = {"pair_analyses": [analysis]}
    assert _matcher()(patterns, {}) is False


def test_returns_false_when_input_palette_is_not_list() -> None:
    for bad in (None, 42, "oops", {"a": 1}, (0, 1), True, {0, 1}):
        analysis = _pair([0, 1], [2, 3])
        analysis["input_palette"] = bad
        patterns = {"pair_analyses": [analysis]}
        assert _matcher()(patterns, {}) is False, (
            f"input_palette={bad!r} should not fire"
        )


def test_returns_false_when_output_palette_is_not_list() -> None:
    for bad in (None, 42, "oops", {"a": 1}, (0, 1), True, {0, 1}):
        analysis = _pair([0, 1], [2, 3])
        analysis["output_palette"] = bad
        patterns = {"pair_analyses": [analysis]}
        assert _matcher()(patterns, {}) is False, (
            f"output_palette={bad!r} should not fire"
        )


def test_returns_false_when_input_palette_contains_bool() -> None:
    # Python bools are an int subclass; strict gate must reject them
    # (same posture as iter-182 / 183 dimensional matchers and the
    # iter-184 / 185 palette matchers).
    analysis = _pair([0, 1], [2, 3])
    analysis["input_palette"] = [0, True, 2]
    patterns = {"pair_analyses": [analysis]}
    assert _matcher()(patterns, {}) is False


def test_returns_false_when_output_palette_contains_bool() -> None:
    analysis = _pair([0, 1], [2, 3])
    analysis["output_palette"] = [False, 3]
    patterns = {"pair_analyses": [analysis]}
    assert _matcher()(patterns, {}) is False


def test_returns_false_when_palette_contains_non_int() -> None:
    analysis = _pair([0, 1], [2, 3])
    analysis["input_palette"] = [0, "1", 2]
    patterns = {"pair_analyses": [analysis]}
    assert _matcher()(patterns, {}) is False

    analysis2 = _pair([0, 1], [2, 3])
    analysis2["output_palette"] = [3.0, 4.0]
    patterns2 = {"pair_analyses": [analysis2]}
    assert _matcher()(patterns2, {}) is False


# ──────────────────────────────────────────────────────────────────────────
# Behavioural-contract cases.
# ──────────────────────────────────────────────────────────────────────────

def test_is_side_effect_free_on_inputs() -> None:
    patterns = {
        "pair_analyses": [
            _pair([0, 1, 2], [3, 4, 5]),
            _pair([6], [7, 8]),
        ],
    }
    params = {"unused": 1}
    before_p = copy.deepcopy(patterns)
    before_q = copy.deepcopy(params)
    _matcher()(patterns, params)
    assert patterns == before_p, "matcher mutated patterns"
    assert params == before_q, "matcher mutated params"


def test_is_deterministic_across_repeats() -> None:
    patterns = {"pair_analyses": [_pair([0, 1, 2], [3, 4, 5])]}
    results = [_matcher()(patterns, {}) for _ in range(5)]
    assert len(set(results)) == 1, f"non-deterministic outputs: {results}"


def test_returned_value_is_boolean_not_truthy() -> None:
    # recognized_conditions filters on ``match(...) is True`` exactly,
    # so the matcher must return literal Booleans.
    out_true = _matcher()({"pair_analyses": [_pair([0, 1], [2, 3])]}, {})
    out_false = _matcher()({"pair_analyses": [_pair([0, 1], [1, 2])]}, {})
    assert out_true is True, f"expected literal True, got {out_true!r}"
    assert out_false is False, f"expected literal False, got {out_false!r}"


def test_ignores_per_group_color_lists() -> None:
    # The matcher reads ONLY ``input_palette`` / ``output_palette``.
    # Per-group ``input_colors`` / ``output_colors`` on the change
    # cells are a different axis -- the matcher must ignore them.
    analysis = _pair(
        [0, 1, 2], [3, 4, 5],
        groups=[{
            "input_colors": [0, 0, 0],
            "output_colors": [3, 3, 3],
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
    analysis = _pair([0, 1], [2, 3], input_height=7, input_width=9,
                     output_height=2, output_width=3, size_match=False)
    patterns = {"pair_analyses": [analysis]}
    assert _matcher()(patterns, {}) is True


# ──────────────────────────────────────────────────────────────────────────
# Orthogonality / co-fire matrix against the palette-axis siblings.
# ──────────────────────────────────────────────────────────────────────────

def test_mutually_exclusive_with_identity_on_nonempty_palette() -> None:
    # Iter 13 implies output palette equals input palette per pair --
    # the OPPOSITE of disjoint on any non-empty palette. They must not
    # co-fire on a non-empty identity case.
    identity = CONDITION_REGISTRY["identity_transformation"]
    identity_pair = _pair([0, 1, 2], [0, 1, 2])
    patterns = {
        "grid_size_preserved": True,
        "pair_analyses": [identity_pair],
    }
    assert identity(patterns, {}) is True
    assert _matcher()(patterns, {}) is False


def test_mutually_exclusive_with_subset_on_nonempty_output() -> None:
    # Subset and disjoint are mutually exclusive on any non-empty
    # output palette -- a non-empty output palette cannot be
    # simultaneously contained in and disjoint from the input palette.
    subset = CONDITION_REGISTRY["output_palette_subset_of_input"]

    # disjoint fires, subset does NOT
    p_disjoint = {"pair_analyses": [_pair([0, 1, 2], [3, 4, 5])]}
    assert _matcher()(p_disjoint, {}) is True
    assert subset(p_disjoint, {}) is False

    # subset fires, disjoint does NOT
    p_subset = {"pair_analyses": [_pair([0, 1, 2], [0, 1])]}
    assert subset(p_subset, {}) is True
    assert _matcher()(p_subset, {}) is False


def test_mutually_exclusive_with_equality_on_nonempty_palette() -> None:
    # Equality ⇒ subset, so equality and disjoint are also mutually
    # exclusive on any non-empty palette (transitively from iter 184
    # via iter 185).
    equality = CONDITION_REGISTRY["output_palette_equals_input"]

    # disjoint fires, equality does NOT
    p_disjoint = {"pair_analyses": [_pair([0, 1, 2], [3, 4, 5])]}
    assert _matcher()(p_disjoint, {}) is True
    assert equality(p_disjoint, {}) is False

    # equality fires, disjoint does NOT
    p_equality = {"pair_analyses": [_pair([0, 1, 2], [2, 0, 1])]}
    assert equality(p_equality, {}) is True
    assert _matcher()(p_equality, {}) is False


def test_subset_and_disjoint_co_fire_only_on_empty_output() -> None:
    # The only joint co-fire of subset AND disjoint is when the
    # output palette is empty (vacuously contained in AND disjoint
    # from any input palette).
    subset = CONDITION_REGISTRY["output_palette_subset_of_input"]
    patterns = {"pair_analyses": [_pair([0, 1, 2], [])]}
    assert subset(patterns, {}) is True
    assert _matcher()(patterns, {}) is True


def test_orthogonal_to_grid_size_preserved() -> None:
    # Whole-grid palette disjointness is orthogonal to the per-pair
    # input==output dim axis (the four-cell 2x2 co-fire table).
    gsp = CONDITION_REGISTRY["grid_size_preserved"]

    # disjoint + preserved -- both fire
    p1 = {
        "grid_size_preserved": True,
        "pair_analyses": [_pair([0, 1, 2], [3, 4, 5])],
    }
    assert _matcher()(p1, {}) is True and gsp(p1, {}) is True

    # disjoint + changed -- only disjoint fires
    p2 = {
        "grid_size_preserved": False,
        "pair_analyses": [
            _pair([0, 1, 2], [3, 4, 5], output_height=6, output_width=6,
                  size_match=False),
        ],
    }
    assert _matcher()(p2, {}) is True and gsp(p2, {}) is False

    # not-disjoint + preserved -- only preserved fires
    p3 = {
        "grid_size_preserved": True,
        "pair_analyses": [_pair([0, 1, 2], [0, 4, 5])],
    }
    assert _matcher()(p3, {}) is False and gsp(p3, {}) is True

    # not-disjoint + changed -- neither fires
    p4 = {
        "grid_size_preserved": False,
        "pair_analyses": [
            _pair([0, 1, 2], [0, 4, 5], output_height=6, output_width=6,
                  size_match=False),
        ],
    }
    assert _matcher()(p4, {}) is False and gsp(p4, {}) is False


def test_orthogonal_to_input_color_uniform() -> None:
    # iter 14 inspects change-cells' input colour uniformity. The
    # whole-grid palette disjointness axis is INDEPENDENT.
    icu = CONDITION_REGISTRY["input_color_uniform"]

    # disjoint fires AND icu fires (single change-cell source colour,
    # output palette fully fresh).
    analysis = _pair(
        [0, 5], [3, 4],
        groups=[{
            "input_colors": [5],
            "output_colors": [3],
            "positions": [(0, 0)],
            "top_row": 0, "top_col": 0,
            "cell_count": 1,
        }],
        num_groups=1, total_changes=1,
    )
    p1 = {"pair_analyses": [analysis]}
    assert _matcher()(p1, {}) is True and icu(p1, {}) is True

    # disjoint fires but icu does NOT (no change cells means iter 14
    # is vacuously False per its docstring: requires len(groups) >=
    # 1).
    p2 = {"pair_analyses": [_pair([0, 1], [2, 3])]}
    assert _matcher()(p2, {}) is True and icu(p2, {}) is False


def test_recognized_conditions_includes_output_palette_disjoint() -> None:
    from agent.conditions import recognized_conditions
    patterns = {"pair_analyses": [_pair([0, 1, 2], [3, 4, 5])]}
    fired = recognized_conditions(patterns)
    assert MATCHER_NAME in fired, (
        f"{MATCHER_NAME!r} did not fire on a clearly-disjoint patterns "
        f"dict; got {fired!r}"
    )
    # And the iter-184 subset matcher must NOT also fire (mutual
    # exclusion on a non-empty output palette).
    assert "output_palette_subset_of_input" not in fired, (
        "subset matcher must NOT co-fire on a disjoint, non-empty "
        "output palette"
    )
    # And iter-185 equality must NOT fire either.
    assert "output_palette_equals_input" not in fired, (
        "equality matcher must NOT co-fire on a disjoint, non-empty "
        "output palette"
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
