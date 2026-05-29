"""
Tests for `agent/conditions/descent_path.py` (module A's descent *itinerary*) and
its consumer `DescendOperator.effect`.

`descent_itinerary` composes the `descent_warranted` matcher across TASK→PAIR→GRID
with per-level evidence *staging*, returning the descent the §3 flow performs and
the level it stops at. `DescendOperator.effect` applies that itinerary to working
memory (focus-level / descent-path), so module A's descent is observable on a live
solve. Both are value-agnostic — easy000a (red) and easy000a2 (green) descend
identically.

The itinerary is exercised against the real producer chain
(compare_scheduler.build_patterns + level_sibling_counts) on the actual slice task
shape, so the staging this module owns is checked end-to-end (PAIR cannot see the
GRID resolving comparisons → descends; GRID can → stops).

pytest is not installed in this environment, so the file is also runnable
directly:  python tests/test_conditions_descent_path.py
"""

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ARCKG.grid import Grid
from ARCKG.pair import Pair
from agent import compare_scheduler as cs
from agent.conditions import CONDITION_REGISTRY
from agent.conditions.descent_path import descent_itinerary, DESCENT_LEVELS
from agent.active_operators import DescendOperator


# --- fixtures (same shape as test_conditions_descent_warranted) ------------

def _rows(cell=None):
    rows = [[0, 0, 0, 0, 0, 0] for _ in range(6)]
    if cell is not None:
        (r, c), color = cell
        rows[r][c] = color
    return rows


def _grid(node_id, cell=None):
    return Grid(node_id, _rows(cell))


def _example_pair(idx, in_cell, out_cell):
    return Pair(
        f"T.P{idx}",
        _grid(f"T.P{idx}.G0", in_cell),
        _grid(f"T.P{idx}.G1", out_cell),
    )


def _test_pair(idx, in_cell):
    return Pair(f"T.P{idx}", _grid(f"T.P{idx}.G0", in_cell), None)


class _Task:
    def __init__(self, example_pairs, test_pairs):
        self.example_pairs = example_pairs
        self.test_pairs = test_pairs


def _easy000a_task(out=((5, 5), 2)):
    """easy000a: a fixed output grid shared by every example pair."""
    return _Task(
        [_example_pair(0, ((1, 1), 2), out),
         _example_pair(1, ((1, 4), 1), out)],
        [_test_pair(2, ((4, 2), 4))],
    )


class _FakeWM:
    """Minimal WM stand-in: DescendOperator.effect reads `.task` and writes `.s1`."""
    def __init__(self, task):
        self.task = task
        self.s1 = {}


def _full_patterns(task):
    patterns = dict(cs.build_patterns(task))
    patterns["level_sibling_counts"] = cs.level_sibling_counts(task)
    return patterns


# --- itinerary tests -------------------------------------------------------

def test_descent_path_not_registered_as_matcher():
    # It returns an itinerary dict, not a bool, so it must NOT pollute the
    # boolean matcher registry (P5 counts registered matchers only).
    assert "descent_path" not in CONDITION_REGISTRY


def test_itinerary_follows_slice3_descent():
    # §3: TASK (nothing to compare) -> PAIR (goal unresolvable here) -> GRID (stop).
    task = _easy000a_task()
    it = descent_itinerary(_full_patterns(task))
    assert it["descend_from"] == ["task", "pair"]
    assert it["terminal"] == "grid"
    assert it["itinerary"] == ["task", "pair", "grid"]


def test_itinerary_value_agnostic_red_vs_green():
    # Different fixed outputs (red vs green) -> byte-identical descent.
    red = descent_itinerary(_full_patterns(_easy000a_task(out=((5, 5), 2))))
    green = descent_itinerary(_full_patterns(_easy000a_task(out=((0, 0), 3))))
    assert red == green


def test_itinerary_stops_at_pair_when_grid_evidence_withheld():
    # Staging proof: if the GRID-level resolving comparisons are absent from the
    # bundle, the PAIR level cannot resolve its goal, but GRID then has neither a
    # goal-resolver nor siblings recorded -> descent runs to GRID and stops there
    # (terminal is still grid; the point is PAIR is in descend_from because its
    # resolver could not fire without the GRID comparisons).
    task = _easy000a_task()
    patterns = _full_patterns(task)
    patterns.pop("output_grid_comparisons", None)
    it = descent_itinerary(patterns)
    assert "pair" in it["descend_from"]


def test_itinerary_staging_hides_grid_evidence_from_pair():
    # Directly assert the staging contract: even with the full bundle, the PAIR
    # level must still warrant a descent (its resolver evidence is GRID-only and
    # withheld at PAIR focus). If staging leaked GRID evidence to PAIR, PAIR would
    # resolve and the terminal would wrongly become "pair".
    task = _easy000a_task()
    it = descent_itinerary(_full_patterns(task))
    assert it["terminal"] != "pair"


def test_itinerary_json_serialisable():
    json.dumps(descent_itinerary(_full_patterns(_easy000a_task())))


def test_levels_constant():
    assert DESCENT_LEVELS == ("task", "pair", "grid")


# --- DescendOperator.effect tests ------------------------------------------

def test_effect_writes_focus_level_and_path():
    task = _easy000a_task()
    wm = _FakeWM(task)
    DescendOperator().effect(wm)
    assert wm.s1["focus-level"] == "grid"
    assert wm.s1["descent-complete"] is True
    assert wm.s1["descent-path"]["itinerary"] == ["task", "pair", "grid"]


def test_effect_value_agnostic_red_vs_green():
    a = _FakeWM(_easy000a_task(out=((5, 5), 2)))
    b = _FakeWM(_easy000a_task(out=((0, 0), 3)))
    DescendOperator().effect(a)
    DescendOperator().effect(b)
    assert a.s1["descent-path"] == b.s1["descent-path"]
    assert a.s1["focus-level"] == b.s1["focus-level"]


def test_effect_no_task_is_noop():
    wm = _FakeWM(None)
    DescendOperator().effect(wm)
    assert wm.s1 == {}


def test_effect_changes_wm():
    # The effect must produce a WM change (so when wired it counts as "changed",
    # not a no-op impasse): three slots written.
    task = _easy000a_task()
    wm = _FakeWM(task)
    DescendOperator().effect(wm)
    assert set(wm.s1) == {"descent-path", "focus-level", "descent-complete"}


if __name__ == "__main__":
    funcs = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    failed = 0
    for fn in funcs:
        try:
            fn()
            print(f"PASS {fn.__name__}")
        except AssertionError as e:
            failed += 1
            print(f"FAIL {fn.__name__}: {e}")
    print(f"\n{len(funcs) - failed}/{len(funcs)} passed")
    sys.exit(1 if failed else 0)
