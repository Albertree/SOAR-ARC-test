"""
Tests for R4's ranking-selection substrate (BACKLOG_LOOP.md R4 "2nd-order /
ranking relation", R1 §2.5-2b seed selector `argmax`).

Three layers, mirroring tests/test_single_object_move.py:
  * vocabulary  — `argmax`/`cells_of` on real multi-object grids: select WHICH
                  object by comparing them on a property, and read the chosen
                  object's cells as the `coloring` selection argument.
  * unit        — the `recolor_extreme_object` matcher's logic on synthetic
                  `object_ranking` dicts (its application wiring is a later rung;
                  here the recognition contract is pinned).
  * registry    — the matcher is registered, so P5 (distinct condition.type
                  values) counts it, and is dormant on the single-object easy
                  path (returns False when the `object_ranking` key is absent).
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agent.conditions import CONDITION_REGISTRY, get_matcher, match  # noqa: E402
from agent.dsl_expr import (  # noqa: E402
    arg_extreme, argmax, argmin, cells_of, most_frequent_color, objects_of, size_of,
)


# ── colour-frequency selection (the mask key for on-keyed self-tiles) ──
def test_most_frequent_color_selects_the_majority_colour():
    grid = [[8, 8, 1], [8, 6, 1], [4, 9, 6]]   # 8 occurs 3×, more than any other
    assert most_frequent_color(grid) == 8


def test_most_frequent_color_abstains_on_a_tie():
    # 4 and 5 both occur twice: "the most-frequent colour" is ambiguous → None
    # (the same determinism-over-guessing discipline argmax/unique apply, P7).
    grid = [[4, 5], [5, 4]]
    assert most_frequent_color(grid) is None


def test_most_frequent_color_empty_grid():
    assert most_frequent_color([]) is None
    assert most_frequent_color([[]]) is None


# ── seed vocabulary: ranking selection over real grids ────────────────
def _two_object_grid():
    # a size-1 object at (0,0) and a size-4 (2x2) object at rows 2-3, cols 2-3.
    return [
        [3, 0, 0, 0, 0, 0],
        [0, 0, 0, 0, 0, 0],
        [0, 0, 3, 3, 0, 0],
        [0, 0, 3, 3, 0, 0],
        [0, 0, 0, 0, 0, 0],
        [0, 0, 0, 0, 0, 0],
    ]


def test_argmax_selects_the_largest_object():
    objs = objects_of(_two_object_grid())
    assert len(objs) == 2
    largest = argmax(objs, size_of)
    assert largest is not None
    assert size_of(largest) == 4
    assert largest["position"] == (2, 2)


def test_cells_of_chosen_object_is_the_coloring_selection():
    objs = objects_of(_two_object_grid())
    cells = cells_of(argmax(objs, size_of))
    # exactly the four cells of the 2x2 block — the `selection` for `coloring`.
    assert cells == frozenset({(2, 2), (2, 3), (3, 2), (3, 3)})


def test_argmax_abstains_on_a_tie():
    # two equal-size (single-cell) objects: "the largest" is ambiguous → None,
    # the same value-agnostic discipline `unique` applies to the >1 case.
    grid = [
        [3, 0, 0],
        [0, 0, 0],
        [0, 0, 3],
    ]
    objs = objects_of(grid)
    assert len(objs) == 2
    assert argmax(objs, size_of) is None


def test_argmax_empty_and_non_list():
    assert argmax([], size_of) is None
    assert argmax(None, size_of) is None


def test_argmax_ignores_objects_without_the_property():
    # a key that is defined for one object and None for the other selects the
    # one with a defined value rather than crashing.
    objs = [{"size": 5}, {"size": None}]
    assert argmax(objs, size_of) == {"size": 5}


def test_cells_of_non_object_is_empty():
    assert cells_of(None) == frozenset()
    assert cells_of(42) == frozenset()


# ── seed vocabulary: direction-parameterised extreme selection ────────
def test_arg_extreme_max_matches_argmax():
    objs = objects_of(_two_object_grid())
    assert arg_extreme(objs, size_of, "max") == argmax(objs, size_of)
    assert size_of(arg_extreme(objs, size_of, "max")) == 4


def test_argmin_selects_the_smallest_object():
    objs = objects_of(_two_object_grid())
    smallest = argmin(objs, size_of)
    assert smallest is not None
    assert size_of(smallest) == 1            # the single-cell object at (0,0)
    assert smallest["position"] == (0, 0)
    assert smallest == arg_extreme(objs, size_of, "min")


def test_arg_extreme_abstains_on_a_tie_either_direction():
    grid = [[3, 0, 0], [0, 0, 0], [0, 0, 3]]   # two equal-size objects
    objs = objects_of(grid)
    assert arg_extreme(objs, size_of, "max") is None
    assert arg_extreme(objs, size_of, "min") is None


def test_arg_extreme_rejects_unknown_direction():
    import pytest
    with pytest.raises(ValueError):
        arg_extreme(objects_of(_two_object_grid()), size_of, "median")


# ── unit: the recolor_extreme_object matcher logic ────────────────────
def _ranking(**over):
    base = {
        "multi_object": True,
        "select_extreme": True,
        "recolor_constant": True,
        "others_unchanged": True,
        "recolor_color": 4,
        "extreme_direction": "max",
        "evidence_count": 3,
    }
    base.update(over)
    return {"object_ranking": base}


def test_matcher_fires_on_full_ranked_recolor_signal():
    assert match("recolor_extreme_object", _ranking()) is True
    # fires identically for the smallest-direction signal (one matcher, both).
    assert match("recolor_extreme_object", _ranking(extreme_direction="min")) is True


def test_matcher_declines_when_not_multi_object():
    assert match("recolor_extreme_object", _ranking(multi_object=False)) is False


def test_matcher_declines_when_selection_is_ambiguous():
    assert match("recolor_extreme_object", _ranking(select_extreme=False)) is False


def test_matcher_declines_when_others_changed():
    assert match("recolor_extreme_object", _ranking(others_unchanged=False)) is False


def test_matcher_declines_when_color_not_constant():
    assert match("recolor_extreme_object", _ranking(recolor_color=None)) is False


def test_matcher_declines_when_no_direction():
    # no size-extreme direction explained the pairs ⇒ not a ranked recolor.
    assert match("recolor_extreme_object", _ranking(extreme_direction=None)) is False


def test_matcher_respects_min_evidence():
    # one example pair cannot establish "always the size-extreme, always this color".
    assert match("recolor_extreme_object", _ranking(evidence_count=1)) is False


# ── registry: P5 counts it, dormant on the easy path ──────────────────
def test_matcher_is_registered():
    assert "recolor_extreme_object" in CONDITION_REGISTRY
    assert get_matcher("recolor_extreme_object") is not None


def test_matcher_dormant_when_signal_absent():
    # the single-object easy/easy_a tasks never surface `object_ranking`, so the
    # matcher cannot misfire there.
    assert match("recolor_extreme_object", {"object_transition": {}}) is False
    assert match("recolor_extreme_object", {}) is False
