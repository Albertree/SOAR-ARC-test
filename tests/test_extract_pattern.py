"""
Tests for ExtractPatternOperator's Slice-1 contract (iter 27).

ExtractPatternOperator used to run a hand-written cell-level diff
(``_analyze_pair`` / ``_group_changes``) — a relic of the retired
``_try_*`` / ``color_mapping`` lineage (CLAUDE.md §5.1) whose ``pair_analyses``
output fed nothing once recognition moved to the value-agnostic
compare-scheduler matchers. Iter 27 removed that dead machinery: the operator
now emits the real Slice-1 ``patterns`` — the module-C/D comparison receipts
(``agent/compare_scheduler.build_patterns``) the §3 flow produces.

These tests pin the new contract:
  1. ``wm.s1["patterns"]`` is exactly the ``build_patterns(task)`` dict — the
     five Slice-1 comparison-receipt keys, no ``pair_analyses`` /
     ``grid_size_preserved`` cell-diff residue.
  2. The slot is a non-empty dict, so the ``ready_for_generalization``
     elaboration rule still fires and the cycle still advances to generalize.
  3. The emitted patterns drive the matchers the same way build_patterns does
     directly (the operator adds no transformation, only exposes the receipts) —
     so the all-outputs-COMM regime is still recognisable, value-agnostically,
     for both the red and green fixed-output tasks.

pytest is not installed here, so the file is also runnable directly:
    python tests/test_extract_pattern.py
"""

import os
import sys
from types import SimpleNamespace

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ARCKG.grid import Grid
from ARCKG.pair import Pair
from agent.active_operators import ExtractPatternOperator
from agent import conditions
from agent.compare_scheduler import build_patterns


# --- fixtures: Slice-1 fixed-output tasks, built from real ARCKG nodes ----

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
    """Every example output is the SAME grid: `fill_color` at (5,5) on a 6x6
    black canvas. Inputs vary; the output is input-independent (easy000a-style).
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
    )


class _WM:
    """Minimal WM stand-in: just .task and .s1 (the slots the operator reads)."""

    def __init__(self, task):
        self.task = task
        self.s1 = {}


_SLICE1_KEYS = {
    "output_grid_comparisons",
    "input_grid_comparisons",
    "intra_pair_grid_comparisons",
    "pair_grid_count_comparisons",
    "pair_grid_counts",
}


# --- the operator emits the real module-C patterns ------------------------

def test_emits_build_patterns_dict():
    task = _fixed_output_task("easy000a", fill_color=2)
    wm = _WM(task)
    ExtractPatternOperator().effect(wm)
    assert wm.s1["patterns"] == build_patterns(task)


def test_patterns_has_exactly_slice1_keys():
    task = _fixed_output_task("easy000a", fill_color=2)
    wm = _WM(task)
    ExtractPatternOperator().effect(wm)
    assert set(wm.s1["patterns"].keys()) == _SLICE1_KEYS


def test_no_dead_celldiff_residue():
    # The retired cell-diff keys must be gone — the slot is now comparison
    # receipts, not a connected-component analysis.
    task = _fixed_output_task("easy000a", fill_color=2)
    wm = _WM(task)
    ExtractPatternOperator().effect(wm)
    assert "pair_analyses" not in wm.s1["patterns"]
    assert "grid_size_preserved" not in wm.s1["patterns"]


def test_patterns_is_nonempty_dict_for_cycle_progress():
    # ready_for_generalization fires iff patterns is a truthy dict.
    task = _fixed_output_task("easy000a", fill_color=2)
    wm = _WM(task)
    ExtractPatternOperator().effect(wm)
    assert isinstance(wm.s1["patterns"], dict) and bool(wm.s1["patterns"])


def test_no_effect_without_task():
    wm = SimpleNamespace(task=None, s1={})
    ExtractPatternOperator().effect(wm)
    assert "patterns" not in wm.s1


# --- the emitted patterns still drive recognition, value-agnostically -----

def _recognises_copy_common(patterns):
    if not conditions.match("test_output_missing", patterns, {"min_evidence": 1}):
        return False
    return bool(conditions.match(
        "all_outputs_comm", patterns,
        {"min_evidence": 1, "required_properties": ["size", "color", "contents"]},
    ))


def test_emitted_patterns_recognise_copy_common_red():
    task = _fixed_output_task("easy000a", fill_color=2)
    wm = _WM(task)
    ExtractPatternOperator().effect(wm)
    assert _recognises_copy_common(wm.s1["patterns"])


def test_emitted_patterns_recognise_copy_common_green_same_code():
    # Different fixed output, identical operator -> no literal in the code path.
    task = _fixed_output_task("easy000a2", fill_color=3)
    wm = _WM(task)
    ExtractPatternOperator().effect(wm)
    assert _recognises_copy_common(wm.s1["patterns"])


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
