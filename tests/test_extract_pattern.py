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


# --- extract READS the cycle's comparisons (CLAUDE.md §5) ------------------

def test_consumes_cycle_intra_pair_comparisons():
    # Simulate what CompareOperator leaves in wm.s1["comparisons"]: one
    # Intra-Pair G0↔G1 receipt per example pair, keyed grid_<idx>, each a
    # {"spec": ..., "result": <receipt>} entry. extract_pattern must put those
    # exact receipts into the intra_pair_grid_comparisons key, not recompute.
    task = _fixed_output_task("easy000a", fill_color=2)
    wm = _WM(task)
    sentinel0 = {"type": "DIFF", "tag": "cycle-receipt-0"}
    sentinel1 = {"type": "DIFF", "tag": "cycle-receipt-1"}
    wm.s1["comparisons"] = {
        "grid_0": {"spec": {"pair_idx": 0}, "result": sentinel0},
        "grid_1": {"spec": {"pair_idx": 1}, "result": sentinel1},
    }
    ExtractPatternOperator().effect(wm)
    assert wm.s1["patterns"]["intra_pair_grid_comparisons"] == [sentinel0, sentinel1]


def test_consumes_cycle_output_grid_comparisons():
    # The deciding Inter-Grid role==G1 receipt the cycle's compare step produces
    # is stored under an inter_grid_output spec; extract must route it to the
    # output_grid_comparisons key, not recompute it from the task.
    task = _fixed_output_task("easy000a", fill_color=2)
    wm = _WM(task)
    decider = {"type": "COMM", "tag": "cycle-decider"}
    intra0 = {"type": "DIFF", "tag": "cycle-intra-0"}
    wm.s1["comparisons"] = {
        "grid_0": {"spec": {"type": "grid", "pair_idx": 0}, "result": intra0},
        "inter_grid_output_0": {
            "spec": {"type": "inter_grid_output"}, "result": decider},
    }
    ExtractPatternOperator().effect(wm)
    assert wm.s1["patterns"]["output_grid_comparisons"] == [decider]
    assert wm.s1["patterns"]["intra_pair_grid_comparisons"] == [intra0]


def test_consumes_cycle_input_grid_comparisons():
    # The contrast Inter-Grid role==G0 receipt the cycle produces is stored under
    # an inter_grid_input spec; extract must route it to the input_grid_comparisons
    # key (not recompute), and keep it distinct from the deciding role==G1 receipt.
    task = _fixed_output_task("easy000a", fill_color=2)
    wm = _WM(task)
    decider = {"type": "COMM", "tag": "cycle-decider"}
    contrast = {"type": "DIFF", "tag": "cycle-contrast"}
    intra0 = {"type": "DIFF", "tag": "cycle-intra-0"}
    wm.s1["comparisons"] = {
        "grid_0": {"spec": {"type": "grid", "pair_idx": 0}, "result": intra0},
        "inter_grid_output_0": {
            "spec": {"type": "inter_grid_output"}, "result": decider},
        "inter_grid_input_0": {
            "spec": {"type": "inter_grid_input"}, "result": contrast},
    }
    ExtractPatternOperator().effect(wm)
    assert wm.s1["patterns"]["input_grid_comparisons"] == [contrast]
    assert wm.s1["patterns"]["output_grid_comparisons"] == [decider]
    assert wm.s1["patterns"]["intra_pair_grid_comparisons"] == [intra0]


def test_consumes_cycle_pair_grid_count_comparisons():
    # The PAIR-level Inter-Pair grid_count receipts the cycle produces are stored
    # under inter_pair_grid_count specs; extract must route them to the
    # pair_grid_count_comparisons key (not recompute), distinct from every
    # GRID-level receipt.
    task = _fixed_output_task("easy000a", fill_color=2)
    wm = _WM(task)
    pc0 = {"type": "COMM", "tag": "cycle-paircount-0"}
    pc1 = {"type": "DIFF", "tag": "cycle-paircount-1"}
    intra0 = {"type": "DIFF", "tag": "cycle-intra-0"}
    wm.s1["comparisons"] = {
        "grid_0": {"spec": {"type": "grid", "pair_idx": 0}, "result": intra0},
        "inter_pair_grid_count_0": {
            "spec": {"type": "inter_pair_grid_count"}, "result": pc0},
        "inter_pair_grid_count_1": {
            "spec": {"type": "inter_pair_grid_count"}, "result": pc1},
    }
    ExtractPatternOperator().effect(wm)
    assert wm.s1["patterns"]["pair_grid_count_comparisons"] == [pc0, pc1]
    assert wm.s1["patterns"]["intra_pair_grid_comparisons"] == [intra0]


def test_falls_back_to_recompute_when_no_comparisons():
    # With no comparisons in the slot (e.g. operator invoked standalone), the
    # intra key is computed from the task — i.e. identical to build_patterns(task).
    task = _fixed_output_task("easy000a", fill_color=2)
    wm = _WM(task)
    ExtractPatternOperator().effect(wm)
    assert wm.s1["patterns"] == build_patterns(task)


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
