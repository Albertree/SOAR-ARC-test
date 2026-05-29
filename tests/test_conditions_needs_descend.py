"""
Tests for the `needs_descend` condition matcher (agent/conditions/), module A's
recognition half (impasse-driven descent, SLICE_1_LOOP.md §4 / exec-trace A).

The matcher recognises the PAIR→GRID descent of easy000a: a goal-bearing
deficiency (`test_output_missing`) is present, but the goal cannot be resolved at
the current level because the resolving comparison (`all_outputs_comm`) is not
yet available — so the analysis must descend. It is exercised against *real*
ARCKG.compare() receipts (the actual receipt shape) and the real module-C
producer chain (compare_scheduler), not fabricated dicts.

pytest is not installed in this environment, so the file is also runnable
directly:  python tests/test_conditions_needs_descend.py
"""

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ARCKG.grid import Grid
from ARCKG.pair import Pair
from agent.conditions import CONDITION_REGISTRY, match
import agent.conditions.needs_descend  # noqa: F401 (ensures registration)
from agent import compare_scheduler as cs


# --- fixtures --------------------------------------------------------------

# A fixed 6x6 example output grid shared by both example pairs (so the
# role-aligned Inter-Grid comparison of the outputs is COMM): a red (2) cell at
# (5,5) on a black (0) field — easy000a's output.
def _rows(cell=None):
    rows = [[0, 0, 0, 0, 0, 0] for _ in range(6)]
    if cell is not None:
        (r, c), color = cell
        rows[r][c] = color
    return rows


def _grid(node_id, cell=None):
    return Grid(node_id, _rows(cell))


def _example_pair(idx, in_cell, out_cell):
    """Complete example pair (input + output) -> grid_count 2."""
    return Pair(
        f"T.P{idx}",
        _grid(f"T.P{idx}.G0", in_cell),
        _grid(f"T.P{idx}.G1", out_cell),
    )


def _test_pair(idx, in_cell):
    """Test pair: input only -> grid_count 1 (its output must be constructed)."""
    return Pair(f"T.P{idx}", _grid(f"T.P{idx}.G0", in_cell), None)


class _Task:
    def __init__(self, example_pairs, test_pairs):
        self.example_pairs = example_pairs
        self.test_pairs = test_pairs


def _easy000a_task():
    """Two example pairs sharing the same output, one input-only test pair."""
    out = ((5, 5), 2)  # common example output cell
    return _Task(
        [
            _example_pair(0, ((1, 1), 2), out),
            _example_pair(1, ((1, 4), 1), out),
        ],
        [_test_pair(2, ((4, 2), 4))],
    )


# --- tests -----------------------------------------------------------------

def test_registry_populated():
    assert "needs_descend" in CONDITION_REGISTRY


def test_pair_level_blocked_descends():
    # PAIR level: only the grid-count census is available (no GRID-level output
    # comparisons gathered yet), so test_output_missing holds but
    # all_outputs_comm cannot fire -> descend.
    task = _easy000a_task()
    pair_only = {"pair_grid_counts": cs.pair_grid_counts(task)}
    # sanity: the goal is present, the resolver is not
    assert match("test_output_missing", pair_only) is True
    assert match("all_outputs_comm", pair_only,
                 {"required_properties": ["size", "color", "contents"]}) is False
    assert match("needs_descend", pair_only) is True


def test_grid_level_resolvable_does_not_descend():
    # GRID level reached: the full patterns (incl. the COMM output comparisons)
    # resolve the goal, so descent self-terminates -> no further descend.
    task = _easy000a_task()
    patterns = cs.build_patterns(task)
    assert match("test_output_missing", patterns) is True
    assert match("all_outputs_comm", patterns,
                 {"required_properties": ["size", "color", "contents"]}) is True
    assert match("needs_descend", patterns) is False


def test_no_goal_does_not_descend():
    # No deficiency (every pair complete) -> no goal -> never descend gratuitously.
    task = _Task(
        [_example_pair(0, ((1, 1), 2), ((5, 5), 2)),
         _example_pair(1, ((1, 4), 1), ((5, 5), 2))],
        [_example_pair(2, ((4, 2), 4), ((5, 5), 2))],
    )
    patterns = cs.build_patterns(task)
    assert match("test_output_missing", patterns) is False
    assert match("needs_descend", patterns) is False


def test_value_agnostic_identical_for_a_and_a2():
    # easy000a (red output) and easy000a2 (a different fixed output, here green)
    # must give the SAME descent verdict at PAIR level -> no value is consulted.
    task_a = _easy000a_task()
    task_a2 = _Task(
        [_example_pair(0, ((1, 1), 2), ((0, 0), 3)),
         _example_pair(1, ((1, 4), 1), ((0, 0), 3))],
        [_test_pair(2, ((4, 2), 4))],
    )
    pair_only_a = {"pair_grid_counts": cs.pair_grid_counts(task_a)}
    pair_only_a2 = {"pair_grid_counts": cs.pair_grid_counts(task_a2)}
    assert match("needs_descend", pair_only_a) == match("needs_descend", pair_only_a2) is True
    # and identical at GRID level too
    assert (match("needs_descend", cs.build_patterns(task_a))
            == match("needs_descend", cs.build_patterns(task_a2)) is False)


def test_custom_conditions_via_params():
    # The goal/resolver are configurable: with a goal that cannot match, no
    # descent regardless of resolver.
    task = _easy000a_task()
    pair_only = {"pair_grid_counts": cs.pair_grid_counts(task)}
    assert match("needs_descend", pair_only,
                 {"goal_condition": "all_outputs_comm"}) is False  # goal absent here


def test_empty_patterns_fails_closed():
    assert match("needs_descend", {}) is False
    assert match("needs_descend", {"pair_grid_counts": {}}) is False


def test_json_serialisable_inputs():
    # The matcher only consumes plain JSON-serialisable symbolic dicts (P7).
    task = _easy000a_task()
    patterns = cs.build_patterns(task)
    json.dumps(patterns)  # must not raise
    assert match("needs_descend", patterns) is False


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
