"""
Tests for the `schema_goal_satisfied` condition matcher (agent/conditions/).

This matcher is the *wiring* half of module B (iter 47): it makes module B's
evolving schema goal — "construct Gx", decomposed over {size, color, contents} —
a live recognition predicate. It fires iff the goal is satisfied, i.e. every
schema leaf has a COMM comparison basis on the role-aligned Inter-Grid comparison
of the example outputs. `copy_common_output_applies` consumes it as its GRID half.

It is exercised against *real* patterns built by compare_scheduler.build_patterns
from real ARCKG nodes, so it sees the actual receipt/census shapes the live solve
produces — and the value-agnostic guarantee (SLICE_1_LOOP.md §9) is checked by
firing on easy000a (red) and easy000a2 (green) identically and NOT on an
easy000b-style differing-output task.

pytest is not installed here, so the file is also runnable directly:
    python tests/test_conditions_schema_goal_satisfied.py
"""

import os
import sys
from types import SimpleNamespace

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ARCKG.grid import Grid
from ARCKG.pair import Pair
from agent.conditions import CONDITION_REGISTRY, match
from agent.compare_scheduler import build_patterns
import agent.conditions.schema_goal_satisfied  # noqa: F401  (registration)


def _grid(node_id, raw):
    return Grid(node_id, [row[:] for row in raw])


def _pair(pid, in_raw, out_raw=None):
    out = _grid(f"{pid}.G1", out_raw) if out_raw is not None else None
    return Pair(pid, _grid(f"{pid}.G0", in_raw), out)


def _task(task_hex, example_pairs, test_pairs):
    return SimpleNamespace(task_hex=task_hex,
                           example_pairs=example_pairs,
                           test_pairs=test_pairs)


def _fixed_output_task(task_hex, fill_color):
    """Every example output is the same grid; test pair carries input only."""
    out = [[0] * 6 for _ in range(6)]; out[5][5] = fill_color
    in0 = [[0] * 6 for _ in range(6)]; in0[1][1] = 2
    in1 = [[0] * 6 for _ in range(6)]; in1[1][4] = 1
    intest = [[0] * 6 for _ in range(6)]; intest[4][2] = 4
    return _task(task_hex,
                 [_pair("T.P0", in0, out), _pair("T.P1", in1, out)],
                 [_pair("T.Pa", intest)])


def _varying_output_task():
    """easy000b-style: outputs differ across pairs -> no schema leaf has a COMM
    basis, so the construct-Gx goal is never satisfied."""
    out0 = [[0] * 6 for _ in range(6)]; out0[5][5] = 2
    out1 = [[0] * 6 for _ in range(6)]; out1[5][5] = 1
    in0 = [[0] * 6 for _ in range(6)]; in0[1][1] = 2
    in1 = [[0] * 6 for _ in range(6)]; in1[1][4] = 1
    intest = [[0] * 6 for _ in range(6)]; intest[4][2] = 4
    return _task("easy000b",
                 [_pair("T.P0", in0, out0), _pair("T.P1", in1, out1)],
                 [_pair("T.Pa", intest)])


def _complete_test_task():
    """Test pair already has an output -> no deficient pair, so module B forms no
    goal to satisfy."""
    out = [[0] * 6 for _ in range(6)]; out[5][5] = 2
    in0 = [[0] * 6 for _ in range(6)]; in0[1][1] = 2
    in1 = [[0] * 6 for _ in range(6)]; in1[1][4] = 1
    intest = [[0] * 6 for _ in range(6)]; intest[4][2] = 4
    return _task("complete",
                 [_pair("T.P0", in0, out), _pair("T.P1", in1, out)],
                 [_pair("T.Pa", intest, out)])


def test_registry_populated():
    assert "schema_goal_satisfied" in CONDITION_REGISTRY


def test_satisfied_on_fixed_output():
    # All three schema leaves get a COMM basis -> goal satisfied.
    patterns = build_patterns(_fixed_output_task("easy000a", 2))
    assert match("schema_goal_satisfied", patterns, {})


def test_value_agnostic_red_and_green_identical():
    red = build_patterns(_fixed_output_task("easy000a", 2))
    green = build_patterns(_fixed_output_task("easy000a2", 3))
    assert match("schema_goal_satisfied", red, {})
    assert match("schema_goal_satisfied", green, {})


def test_not_satisfied_on_varying_outputs():
    # Outputs differ -> no schema leaf has a COMM basis -> goal not satisfied.
    patterns = build_patterns(_varying_output_task())
    assert not match("schema_goal_satisfied", patterns, {})


def test_no_goal_when_nothing_to_construct():
    # Test pair complete -> module B forms no goal (build_goalstack -> None).
    patterns = build_patterns(_complete_test_task())
    assert not match("schema_goal_satisfied", patterns, {})


def test_empty_patterns_fail_closed():
    assert not match("schema_goal_satisfied", {}, {})


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
        except Exception as e:  # noqa: BLE001
            failed += 1
            print(f"ERROR {fn.__name__}: {type(e).__name__}: {e}")
    print(f"\n{len(funcs) - failed}/{len(funcs)} passed")
    sys.exit(1 if failed else 0)
