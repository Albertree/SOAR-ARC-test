"""
Tests for the `nothing_to_compare` condition matcher (agent/conditions/), the
second of module A's recognition matchers (the n_at_level==1 descent trigger,
SLICE_1_LOOP.md §3 [TASK level] / exec-trace module A).

This matcher recognises the §3 TASK-level descent: a single loaded task has no
sibling tasks, so the TASK level offers nothing to compare pairwise (P6) and the
flow must descend to PAIR *before* any goal forms — distinct from `needs_descend`
(goal present but unresolved). It is exercised against the real module-C producer
chain (compare_scheduler.level_sibling_counts) on the actual slice task shape,
not fabricated dicts.

pytest is not installed in this environment, so the file is also runnable
directly:  python tests/test_conditions_nothing_to_compare.py
"""

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ARCKG.grid import Grid
from ARCKG.pair import Pair
from agent.conditions import CONDITION_REGISTRY, match
import agent.conditions.nothing_to_compare  # noqa: F401 (ensures registration)
from agent import compare_scheduler as cs


# --- fixtures --------------------------------------------------------------

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


def _easy000a_task():
    out = ((5, 5), 2)
    return _Task(
        [_example_pair(0, ((1, 1), 2), out),
         _example_pair(1, ((1, 4), 1), out)],
        [_test_pair(2, ((4, 2), 4))],
    )


# --- tests -----------------------------------------------------------------

def test_registry_populated():
    assert "nothing_to_compare" in CONDITION_REGISTRY


def test_task_level_has_nothing_to_compare_descends():
    # TASK level: a single loaded task -> count 1 -> pairwise impossible -> descend.
    task = _easy000a_task()
    patterns = {"level_sibling_counts": cs.level_sibling_counts(task)}
    assert match("nothing_to_compare", patterns) is True  # default level == "task"


def test_pair_level_has_siblings_does_not_descend():
    # PAIR level: 3 pairs (2 examples + 1 test) -> count >= 2 -> something to
    # compare -> this descent trigger does NOT fire.
    task = _easy000a_task()
    patterns = {"level_sibling_counts": cs.level_sibling_counts(task)}
    assert match("nothing_to_compare", patterns, {"level": "pair"}) is False


def test_producer_counts_are_structural():
    task = _easy000a_task()
    census = cs.level_sibling_counts(task)
    assert census == {"task": 1, "pair": 3}


def test_value_agnostic_identical_for_a_and_a2():
    # easy000a (red output) and easy000a2 (a different fixed output, green) must
    # give the SAME TASK-level verdict -> only a structural count is consulted.
    task_a = _easy000a_task()
    task_a2 = _Task(
        [_example_pair(0, ((1, 1), 2), ((0, 0), 3)),
         _example_pair(1, ((1, 4), 1), ((0, 0), 3))],
        [_test_pair(2, ((4, 2), 4))],
    )
    pa = {"level_sibling_counts": cs.level_sibling_counts(task_a)}
    pa2 = {"level_sibling_counts": cs.level_sibling_counts(task_a2)}
    assert match("nothing_to_compare", pa) == match("nothing_to_compare", pa2) is True


def test_distinct_from_needs_descend_no_goal_required():
    # nothing_to_compare fires with NO goal-bearing pattern present at all (it
    # only needs the sibling census) -> distinct trigger shape from needs_descend,
    # which requires a goal. Here there is no pair_grid_counts census, so the
    # goal matcher test_output_missing is False, yet nothing_to_compare fires.
    task = _easy000a_task()
    patterns = {"level_sibling_counts": cs.level_sibling_counts(task)}
    assert match("test_output_missing", patterns) is False
    assert match("nothing_to_compare", patterns) is True


def test_configurable_min_to_compare():
    # With min_to_compare lowered to 1, a single-node level is "enough" -> no
    # descend; the threshold is the only knob.
    task = _easy000a_task()
    patterns = {"level_sibling_counts": cs.level_sibling_counts(task)}
    assert match("nothing_to_compare", patterns, {"min_to_compare": 1}) is False


def test_empty_or_malformed_fails_closed():
    assert match("nothing_to_compare", {}) is False
    assert match("nothing_to_compare", {"level_sibling_counts": {}}) is False
    assert match("nothing_to_compare",
                 {"level_sibling_counts": {"task": "1"}}) is False  # non-int
    assert match("nothing_to_compare",
                 {"level_sibling_counts": {"task": True}}) is False  # bool rejected
    assert match("nothing_to_compare",
                 {"level_sibling_counts": {"task": 1}}, {"level": "grid"}) is False  # missing level


def test_json_serialisable_inputs():
    task = _easy000a_task()
    patterns = {"level_sibling_counts": cs.level_sibling_counts(task)}
    json.dumps(patterns)  # must not raise
    assert match("nothing_to_compare", patterns) is True


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
