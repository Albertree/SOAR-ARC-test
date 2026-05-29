"""
Tests for agent/flow_trace.py — the §3 comparison-flow *form* made observable.

Before this, the three non-decisive §3 flow-step recognisers
(`pair_grid_count_majority`, `intra_pair_grids_differ`, `inputs_vary`) had no
production consumer — they fired only in their own unit tests. `slice1_flow_steps`
runs every §3 recogniser over a live `patterns` bundle and reports which steps the
comparison flow exhibited, in §3 order, flagging the single decisive one
(role==G1 all-COMM). The episode trace now appends this record so each solve shows
the *shape of its comparison flow* (criterion 3, SLICE_1_LOOP §8 — 접근성).

Decisive Slice-1 property: **value-agnosticism** (SLICE_1_LOOP §9) — the record is
built from COMM/DIFF verdicts only, so easy000a (red) and easy000a2 (green) yield
an identical flow record.

pytest is not installed here, so the file is also runnable directly:
    python tests/test_flow_trace.py
"""

import json
import os
import sys
from types import SimpleNamespace

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ARCKG.grid import Grid
from ARCKG.pair import Pair
from agent.compare_scheduler import build_patterns
from agent.flow_trace import slice1_flow_steps


# --- fixtures: Slice-1 target tasks, built from real ARCKG nodes ----------

def _grid(node_id, raw):
    return Grid(node_id, [row[:] for row in raw])


def _pair(pid, in_raw, out_raw=None):
    out = _grid(f"{pid}.G1", out_raw) if out_raw is not None else None
    return Pair(pid, _grid(f"{pid}.G0", in_raw), out)


def _fixed_output_task(task_hex, fill_color):
    """Every example output identical (`fill_color` at (5,5) on 6x6 black);
    inputs vary; test pair carries input only — the construct-the-output regime
    (easy000a / easy000a2)."""
    out = [[0] * 6 for _ in range(6)]
    out[5][5] = fill_color
    in0 = [[0] * 6 for _ in range(6)]; in0[1][1] = 2
    in1 = [[0] * 6 for _ in range(6)]; in1[1][4] = 1
    intest = [[0] * 6 for _ in range(6)]; intest[4][2] = 4
    return SimpleNamespace(
        task_hex=task_hex,
        example_pairs=[_pair("P0", in0, out), _pair("P1", in1, out)],
        test_pairs=[_pair("Pa", intest)],
    )


# --- the §3 flow form is recognised on the slice --------------------------

def test_full_slice1_flow_recognised():
    """On easy000a all four §3 steps fire: PAIR consensus+dissent, Intra-Pair
    DIFF, Inter-Grid role==G0 DIFF, and the decisive role==G1 all-COMM."""
    rec = slice1_flow_steps(build_patterns(_fixed_output_task("easy000a", 2)))
    assert rec["phase"] == "comparison_flow"
    assert rec["module"] == "C"
    by_step = {s["step"]: s for s in rec["steps"]}
    assert set(by_step) == {
        "pair_grid_count_majority", "intra_pair_grids_differ",
        "inputs_vary", "all_outputs_comm",
    }
    assert all(s["recognised"] for s in rec["steps"])
    assert rec["decisive_recognised"] is True


def test_step_order_and_single_decisive():
    """Steps are in §3 order and exactly one (the role==G1 all-COMM) is decisive."""
    rec = slice1_flow_steps(build_patterns(_fixed_output_task("easy000a", 2)))
    assert [s["step"] for s in rec["steps"]] == [
        "pair_grid_count_majority", "intra_pair_grids_differ",
        "inputs_vary", "all_outputs_comm",
    ]
    decisive = [s for s in rec["steps"] if s["decisive"]]
    assert len(decisive) == 1
    assert decisive[0]["step"] == "all_outputs_comm"
    assert decisive[0]["role"] == "G1" and decisive[0]["expect"] == "COMM"


def test_value_agnostic_red_and_green_identical():
    """easy000a (red) and easy000a2 (green) produce a byte-identical flow record —
    the record reads COMM/DIFF verdicts only, never the output colour (§9 / P7)."""
    red = slice1_flow_steps(build_patterns(_fixed_output_task("easy000a", 2)))
    green = slice1_flow_steps(build_patterns(_fixed_output_task("easy000a2", 3)))
    assert red == green


def test_record_is_json_serialisable():
    """The record is a plain symbolic dict (P7)."""
    rec = slice1_flow_steps(build_patterns(_fixed_output_task("easy000a", 2)))
    assert json.loads(json.dumps(rec)) == rec


def test_decisive_open_when_outputs_differ():
    """When the example outputs are NOT all-COMM (contents differ), the decisive
    step is not recognised — the flow form honestly reports the deciding
    comparison did not settle, while the non-decisive DIFF steps still fire."""
    out0 = [[0] * 6 for _ in range(6)]; out0[5][5] = 2
    out1 = [[0] * 6 for _ in range(6)]; out1[0][0] = 2   # same size+colour, diff contents
    in0 = [[0] * 6 for _ in range(6)]; in0[1][1] = 2
    in1 = [[0] * 6 for _ in range(6)]; in1[1][4] = 1
    intest = [[0] * 6 for _ in range(6)]; intest[4][2] = 4
    task = SimpleNamespace(
        task_hex="contents_differ",
        example_pairs=[_pair("P0", in0, out0), _pair("P1", in1, out1)],
        test_pairs=[_pair("Pa", intest)],
    )
    rec = slice1_flow_steps(build_patterns(task))
    by_step = {s["step"]: s for s in rec["steps"]}
    assert rec["decisive_recognised"] is False
    assert by_step["all_outputs_comm"]["recognised"] is False
    # the non-decisive flow steps are unaffected by the output mismatch
    assert by_step["intra_pair_grids_differ"]["recognised"] is True
    assert by_step["inputs_vary"]["recognised"] is True


def test_empty_patterns_recognises_nothing():
    """No patterns → no step recognised, no decisive step, no raise."""
    rec = slice1_flow_steps({})
    assert rec["decisive_recognised"] is False
    assert all(s["recognised"] is False for s in rec["steps"])


def _run():
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    passed = 0
    for t in tests:
        t()
        print(f"  ok  {t.__name__}")
        passed += 1
    print(f"\n{passed}/{len(tests)} flow_trace tests passed")


if __name__ == "__main__":
    _run()
