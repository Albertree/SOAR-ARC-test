"""
Tests for the `descent_warranted` condition matcher (agent/conditions/), module
A's *unified* descent-trigger recogniser (the exec-trace trigger disjunction
evaluated at the current focus level).

`descent_warranted` is the single "does this level warrant a descent?" decision
that module A's DescendOperator will consult. It ORs the two level-appropriate
disjuncts Slice 1 exercises — `nothing_to_compare` (TASK level, goal-free) and
`needs_descend` (PAIR level, goal present but unresolvable) — and returns False
once the level can resolve its goal (GRID level), so descent self-terminates.

It is exercised against the real module-C producer chain
(compare_scheduler.level_sibling_counts / pair_grid_counts) on the actual slice
task shape, with the GRID-level resolving evidence supplied as explicit COMM
receipts (kept literal so the test does not depend on ARCKG.compare internals).

pytest is not installed in this environment, so the file is also runnable
directly:  python tests/test_conditions_descent_warranted.py
"""

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ARCKG.grid import Grid
from ARCKG.pair import Pair
from agent.conditions import CONDITION_REGISTRY, match
import agent.conditions.descent_warranted  # noqa: F401 (ensures registration)
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


def _easy000a_task(out=((5, 5), 2)):
    return _Task(
        [_example_pair(0, ((1, 1), 2), out),
         _example_pair(1, ((1, 4), 1), out)],
        [_test_pair(2, ((4, 2), 4))],
    )


def _comm_receipt():
    """A role-aligned Inter-Grid output receipt that is COMM on every Slice-1
    grid property — the GRID-level resolving evidence (kept literal so the test
    does not depend on ARCKG.compare's exact category shape)."""
    return {
        "type": "COMM",
        "score": "3/3",
        "category": {p: {"type": "COMM"} for p in ("size", "color", "contents")},
    }


def _task_level_patterns(task):
    """What is known at the TASK level: only the sibling census (no goal yet)."""
    return {"level_sibling_counts": cs.level_sibling_counts(task)}


def _pair_level_patterns(task):
    """PAIR level: a goal forms (test output missing) but the resolving GRID
    comparisons have not been gathered yet → unresolvable here."""
    return {
        "level_sibling_counts": cs.level_sibling_counts(task),
        "pair_grid_counts": cs.pair_grid_counts(task),
    }


def _grid_level_patterns(task):
    """GRID level: the resolving evidence is in hand (all example outputs COMM),
    so the goal can be answered here."""
    p = _pair_level_patterns(task)
    p["output_grid_comparisons"] = [_comm_receipt()]
    return p


# --- tests -----------------------------------------------------------------

def test_registry_populated():
    assert "descent_warranted" in CONDITION_REGISTRY


def test_task_level_warrants_descent_goal_free():
    # TASK level: one task node, no goal -> nothing_to_compare disjunct fires.
    task = _easy000a_task()
    assert match("descent_warranted", _task_level_patterns(task)) is True


def test_pair_level_warrants_descent_via_needs_descend():
    # PAIR level: 3 sibling pairs (so nothing_to_compare is False) but a goal is
    # present and unresolvable here -> needs_descend disjunct fires.
    task = _easy000a_task()
    patterns = _pair_level_patterns(task)
    # The nothing_to_compare disjunct must NOT be the reason here:
    assert match("nothing_to_compare", patterns, {"level": "pair"}) is False
    assert match("descent_warranted", patterns, {"level": "pair"}) is True


def test_grid_level_resolves_no_descent():
    # GRID level: siblings present AND the goal is resolvable (all outputs COMM)
    # -> neither disjunct fires -> descent self-terminates.
    task = _easy000a_task()
    patterns = _grid_level_patterns(task)
    assert match("needs_descend", patterns) is False
    assert match("descent_warranted", patterns, {"level": "grid"}) is False


def test_descends_through_all_three_levels_in_order():
    # The whole §3 descent chain answered by one matcher: descend, descend, stop.
    task = _easy000a_task()
    assert match("descent_warranted", _task_level_patterns(task)) is True
    assert match("descent_warranted", _pair_level_patterns(task),
                 {"level": "pair"}) is True
    assert match("descent_warranted", _grid_level_patterns(task),
                 {"level": "grid"}) is False


def test_value_agnostic_identical_for_a_and_a2():
    # easy000a (red output) and easy000a2 (a different fixed output, green) must
    # give the SAME verdict at every level -> only structure is consulted.
    task_a = _easy000a_task(out=((5, 5), 2))
    task_a2 = _easy000a_task(out=((0, 0), 3))
    for level, builder in (("task", _task_level_patterns),
                           ("pair", _pair_level_patterns),
                           ("grid", _grid_level_patterns)):
        va = match("descent_warranted", builder(task_a), {"level": level})
        va2 = match("descent_warranted", builder(task_a2), {"level": level})
        assert va == va2


def test_either_disjunct_alone_suffices():
    # nothing_to_compare alone (no goal pattern) -> warranted.
    task = _easy000a_task()
    only_census = {"level_sibling_counts": cs.level_sibling_counts(task)}
    assert match("test_output_missing", only_census) is False  # no goal pattern
    assert match("descent_warranted", only_census) is True     # still warranted
    # needs_descend alone (goal present, unresolvable; no census key for "pair"
    # below threshold) -> warranted.
    only_goal = {"pair_grid_counts": cs.pair_grid_counts(task)}
    assert match("nothing_to_compare", only_goal, {"level": "pair"}) is False
    assert match("descent_warranted", only_goal, {"level": "pair"}) is True


def test_empty_or_malformed_fails_closed():
    # No patterns at all -> no disjunct can fire -> not warranted.
    assert match("descent_warranted", {}) is False
    assert match("descent_warranted", {"level_sibling_counts": {}}) is False
    # An unknown level with siblings present everywhere -> nothing_to_compare
    # fails closed (missing level), no goal -> not warranted.
    task = _easy000a_task()
    assert match("descent_warranted", _task_level_patterns(task),
                 {"level": "object"}) is False


def test_configurable_subparams_forwarded():
    # Lowering nothing_to_compare's min_to_compare to 1 makes the one-node TASK
    # level "enough" -> that disjunct no longer fires; with no goal either, not
    # warranted.
    task = _easy000a_task()
    patterns = _task_level_patterns(task)
    assert match("descent_warranted", patterns,
                 {"nothing_to_compare_params": {"min_to_compare": 1}}) is False


def test_json_serialisable_inputs():
    task = _easy000a_task()
    for builder in (_task_level_patterns, _pair_level_patterns, _grid_level_patterns):
        json.dumps(builder(task))  # must not raise


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
