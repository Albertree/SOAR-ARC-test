"""
Tests for the `copy_common_output_applies` condition matcher (agent/conditions/).

This matcher is the single Slice-1 copy-common-output recogniser: the PAIR-level
`test_output_missing` ∧ GRID-level `all_outputs_comm` conjunction, named once so
the slow path (GeneralizeOperator) and the fast path (rule reuse) share one
routine instead of each hand-inlining it (SLICE_1_LOOP.md §3, §8 criterion 2).

It is exercised against *real* patterns built by compare_scheduler.build_patterns
from real ARCKG nodes, so it sees the actual receipt/census shapes the live
solve produces — and the value-agnostic guarantee (SLICE_1_LOOP.md §9) is
checked by firing on easy000a (red) and easy000a2 (green) identically and NOT on
an easy000b-style differing-output task.

pytest is not installed here, so the file is also runnable directly:
    python tests/test_conditions_copy_common_output_applies.py
"""

import os
import sys
from types import SimpleNamespace

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ARCKG.grid import Grid
from ARCKG.pair import Pair
from agent.conditions import CONDITION_REGISTRY, match
from agent.compare_scheduler import build_patterns
import agent.conditions.copy_common_output_applies  # noqa: F401  (registration)


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
    """Every example output is the same grid: fill_color at (5,5) on 6x6 black;
    test pair carries input only (its output must be constructed)."""
    out = [[0] * 6 for _ in range(6)]; out[5][5] = fill_color
    in0 = [[0] * 6 for _ in range(6)]; in0[1][1] = 2
    in1 = [[0] * 6 for _ in range(6)]; in1[1][4] = 1
    intest = [[0] * 6 for _ in range(6)]; intest[4][2] = 4
    return _task(task_hex,
                 [_pair("T.P0", in0, out), _pair("T.P1", in1, out)],
                 [_pair("T.Pa", intest)])


def _varying_output_task():
    """easy000b-style: outputs differ across pairs (not a copy task)."""
    out0 = [[0] * 6 for _ in range(6)]; out0[5][5] = 2
    out1 = [[0] * 6 for _ in range(6)]; out1[5][5] = 1
    in0 = [[0] * 6 for _ in range(6)]; in0[1][1] = 2
    in1 = [[0] * 6 for _ in range(6)]; in1[1][4] = 1
    intest = [[0] * 6 for _ in range(6)]; intest[4][2] = 4
    return _task("easy000b",
                 [_pair("T.P0", in0, out0), _pair("T.P1", in1, out1)],
                 [_pair("T.Pa", intest)])


def _complete_test_task():
    """A task whose test pair ALSO has an output (grid_count 2) — there is
    nothing to construct, so the PAIR-level trigger must fail."""
    out = [[0] * 6 for _ in range(6)]; out[5][5] = 2
    in0 = [[0] * 6 for _ in range(6)]; in0[1][1] = 2
    in1 = [[0] * 6 for _ in range(6)]; in1[1][4] = 1
    intest = [[0] * 6 for _ in range(6)]; intest[4][2] = 4
    return _task("complete",
                 [_pair("T.P0", in0, out), _pair("T.P1", in1, out)],
                 [_pair("T.Pa", intest, out)])


def test_registry_populated():
    assert "copy_common_output_applies" in CONDITION_REGISTRY


def test_fires_on_fixed_output_red():
    patterns = build_patterns(_fixed_output_task("easy000a", 2))
    assert match("copy_common_output_applies", patterns, {"min_evidence": 1})


def test_value_agnostic_red_and_green_identical():
    red = build_patterns(_fixed_output_task("easy000a", 2))
    green = build_patterns(_fixed_output_task("easy000a2", 3))
    assert match("copy_common_output_applies", red, {"min_evidence": 1})
    assert match("copy_common_output_applies", green, {"min_evidence": 1})


def test_does_not_fire_on_varying_outputs():
    # GRID half (all_outputs_comm) fails -> whole conjunction false.
    patterns = build_patterns(_varying_output_task())
    assert not match("copy_common_output_applies", patterns, {"min_evidence": 1})


def test_does_not_fire_when_test_output_present():
    # PAIR half (test_output_missing) fails -> whole conjunction false, even
    # though every example output is identical.
    patterns = build_patterns(_complete_test_task())
    assert not match("copy_common_output_applies", patterns, {"min_evidence": 1})


def test_grid_matcher_param_overrides_default():
    # The fast path drives the GRID half from the stored rule's condition.type;
    # passing the explicit default name must behave like the default.
    patterns = build_patterns(_fixed_output_task("easy000a", 2))
    assert match("copy_common_output_applies", patterns,
                 {"grid_matcher": "all_outputs_comm", "min_evidence": 1})


def test_empty_patterns_fail_closed():
    assert not match("copy_common_output_applies", {}, {"min_evidence": 1})


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
