"""
Tests for the Slice-1 value-agnostic copy-common-output mechanism wired into
the SOAR pipeline operators (iter 4).

This is the step that makes the iter-2 `all_outputs_comm` matcher + iter-3
`agent/compare_scheduler.py` producer actually *act*: GeneralizeOperator
recognises the all-outputs-COMM regime (via the recognition registry, not a
hand-coded detector) and emits a `copy_common_output` rule; PredictOperator
applies it by copying the task's common example output grid.

The decisive property is **value-agnosticism** (SLICE_1_LOOP.md §9): the same
operators produce easy000a's fixed output (red) and easy000a2's *different*
fixed output (green) without any literal in the code — they copy whatever the
common example output is. A task whose outputs differ across pairs must NOT
trigger the mechanism.

pytest is not installed here, so the file is also runnable directly:
    python tests/test_predict_copy_common_output.py
"""

import os
import sys
from types import SimpleNamespace

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ARCKG.grid import Grid
from ARCKG.pair import Pair
from agent.active_operators import GeneralizeOperator, PredictOperator


# --- fixtures: Slice-1 target tasks, built from real ARCKG nodes ----------

def _grid(node_id, raw):
    return Grid(node_id, [row[:] for row in raw])


def _pair(pid, in_raw, out_raw=None):
    out = _grid(f"{pid}.G1", out_raw) if out_raw is not None else None
    return Pair(pid, _grid(f"{pid}.G0", in_raw), out)


def _task(task_hex, example_pairs, test_pairs):
    return SimpleNamespace(
        task_hex=task_hex,
        example_pairs=example_pairs,
        test_pairs=test_pairs,
    )


def _fixed_output_task(task_hex, fill_color):
    """A task whose every example output is the SAME grid: `fill_color` at
    (5,5) on a 6x6 black canvas. Inputs vary; the output is input-independent.
    """
    out = [[0] * 6 for _ in range(6)]
    out[5][5] = fill_color
    in0 = [[0] * 6 for _ in range(6)]; in0[1][1] = 2
    in1 = [[0] * 6 for _ in range(6)]; in1[1][4] = 1
    intest = [[0] * 6 for _ in range(6)]; intest[4][2] = 4
    return _task(
        task_hex,
        [_pair("T.P0", in0, out), _pair("T.P1", in1, out)],
        [_pair("T.Pa", intest)],
    ), out


def _varying_output_task():
    """easy000b-style: outputs differ across pairs (not a copy task)."""
    out0 = [[0] * 6 for _ in range(6)]; out0[5][5] = 2
    out1 = [[0] * 6 for _ in range(6)]; out1[5][5] = 1
    in0 = [[0] * 6 for _ in range(6)]; in0[1][1] = 2
    in1 = [[0] * 6 for _ in range(6)]; in1[1][4] = 1
    intest = [[0] * 6 for _ in range(6)]; intest[4][2] = 4
    return _task(
        "easy000b",
        [_pair("T.P0", in0, out0), _pair("T.P1", in1, out1)],
        [_pair("T.Pa", intest)],
    )


class _WM:
    """Minimal WM stand-in: just .task and .s1 (the slots the operators read)."""

    def __init__(self, task):
        self.task = task
        self.s1 = {}


def _run_generalize_then_predict(task):
    wm = _WM(task)
    # ExtractPatternOperator would normally fill this; a non-empty dict is all
    # GeneralizeOperator.effect needs to not early-return.
    wm.s1["patterns"] = {"pair_analyses": [], "grid_size_preserved": True}
    GeneralizeOperator().effect(wm)
    PredictOperator().effect(wm)
    return wm


# --- GeneralizeOperator recognises the copy-common-output regime ----------

def test_generalize_emits_copy_common_output_for_fixed_output_task():
    task, _ = _fixed_output_task("easy000a", fill_color=2)
    wm = _WM(task)
    wm.s1["patterns"] = {"pair_analyses": [], "grid_size_preserved": True}
    GeneralizeOperator().effect(wm)
    rules = wm.s1.get("active-rules")
    assert rules and rules[0]["type"] == "copy_common_output"


def test_generalize_does_not_emit_for_varying_outputs():
    # Outputs differ across pairs -> all_outputs_comm fails -> fall through.
    task = _varying_output_task()
    wm = _WM(task)
    wm.s1["patterns"] = {"pair_analyses": [], "grid_size_preserved": True}
    GeneralizeOperator().effect(wm)
    rules = wm.s1.get("active-rules")
    assert rules and rules[0]["type"] != "copy_common_output"


# --- PredictOperator copies the common output (value-agnostic) ------------

def test_predict_copies_common_output_red():
    task, out = _fixed_output_task("easy000a", fill_color=2)
    wm = _run_generalize_then_predict(task)
    assert wm.s1["predictions"]["test_0"] == out


def test_predict_copies_common_output_green_same_code():
    # Different fixed output, identical mechanism -> no hard-coded literal.
    task, out = _fixed_output_task("easy000a2", fill_color=3)
    wm = _run_generalize_then_predict(task)
    assert wm.s1["predictions"]["test_0"] == out
    # And it really is the green grid, distinct from the red case.
    assert wm.s1["predictions"]["test_0"][5][5] == 3


def test_value_agnostic_red_and_green_differ():
    _, red = _fixed_output_task("easy000a", fill_color=2)
    _, green = _fixed_output_task("easy000a2", fill_color=3)
    assert red != green  # guards against any accidental literal sharing


# --- helper: common-output extraction guards ------------------------------

def test_common_example_output_none_when_outputs_differ():
    task = _varying_output_task()
    assert PredictOperator._common_example_output(task) is None


def test_common_example_output_returns_shared_grid():
    task, out = _fixed_output_task("easy000a", fill_color=2)
    assert PredictOperator._common_example_output(task) == out


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
        except Exception as e:  # noqa: BLE001 — surface unexpected errors too
            failed += 1
            print(f"ERROR {fn.__name__}: {type(e).__name__}: {e}")
    print(f"\n{len(funcs) - failed}/{len(funcs)} passed")
    sys.exit(1 if failed else 0)
