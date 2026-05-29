"""
Tests for module B (agent/goal.py GoalStack) firing in the *live* solve path
via ActiveSoarAgent._slice1_goal_record (iter 38).

Before this iter the GoalStack library was fully built + tested (tests/test_goal.py)
but never instantiated during an actual solve() — dormant intended vocabulary.
This wires it into the episode the agent records every solve(), so the §3 flow's
goal-basis (PAIR: "construct the test pair's missing output" → GRID:
"determine {size, color, contents}") is attached to the answer.

The decisive Slice-1 property is **value-agnosticism** (SLICE_1_LOOP.md §9): the
goal trace is built from the structural grid-count census only, so the two
targets — easy000a (red output) and easy000a2 (green output) — must produce
byte-identical goal trees. A test asserts exactly that, and that the recorded
trace carries no colour/coordinate vocabulary.

pytest is not installed here, so the file is also runnable directly:
    python tests/test_active_agent_goal_trace.py
"""

import json
import os
import sys
from types import SimpleNamespace

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ARCKG.grid import Grid
from ARCKG.pair import Pair
from agent.active_agent import ActiveSoarAgent


# --- fixtures: Slice-1 target tasks, built from real ARCKG nodes ----------

def _grid(node_id, raw):
    return Grid(node_id, [row[:] for row in raw])


def _pair(pid, in_raw, out_raw=None):
    out = _grid(f"{pid}.G1", out_raw) if out_raw is not None else None
    return Pair(pid, _grid(f"{pid}.G0", in_raw), out)


def _fixed_output_task(task_hex, fill_color):
    """Every example output is the SAME grid (`fill_color` at (5,5) on a 6x6
    black canvas); inputs vary; the test pair carries input only — the
    construct-the-output regime."""
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


def _agent():
    return ActiveSoarAgent()


# --- module B fires on the live task --------------------------------------

def test_goal_record_forms_full_chain_when_output_constructed():
    task = _fixed_output_task("easy000a", fill_color=2)
    rec = _agent()._slice1_goal_record(task, predicted=[[[0]]])
    assert rec is not None
    assert rec["phase"] == "goal_evolution"
    assert rec["module"] == "B"
    # value -> action -> schema, with the two prior forms in history
    goal = rec["goal"]
    assert goal["current"]["kind"] == "schema"
    assert set(goal["current"]["subgoals"]) == {"size", "color", "contents"}
    assert [g["kind"] for g in goal["history"]] == ["value", "action"]
    # a produced prediction satisfies every schema leaf
    assert rec["satisfied"] is True


def test_goal_record_left_open_when_no_prediction():
    task = _fixed_output_task("easy000a", fill_color=2)
    rec = _agent()._slice1_goal_record(task, predicted=None)
    assert rec is not None
    # the construct-output goal is formed but unsatisfied (honest failure trace)
    assert rec["satisfied"] is False
    for child in rec["goal"]["current"]["subgoals"].values():
        assert child["status"] == "open"


def test_goal_record_none_when_no_deficient_test_pair():
    # test pair already complete (has an output) -> nothing to construct
    out = [[0] * 6 for _ in range(6)]; out[5][5] = 2
    task = SimpleNamespace(
        task_hex="complete",
        example_pairs=[_pair("P0", [[0]], out)],
        test_pairs=[_pair("Pa", [[0]], out)],
    )
    assert _agent()._slice1_goal_record(task, predicted=[[[0]]]) is None


# --- value-agnosticism: easy000a vs easy000a2 ------------------------------

def test_goal_record_identical_across_targets():
    a = _agent()._slice1_goal_record(
        _fixed_output_task("easy000a", fill_color=2), predicted=[[[0]]])
    a2 = _agent()._slice1_goal_record(
        _fixed_output_task("easy000a2", fill_color=3), predicted=[[[0]]])
    assert a == a2          # different output colours, identical goal tree


def test_goal_record_carries_no_colour_or_coordinate():
    rec = _agent()._slice1_goal_record(
        _fixed_output_task("easy000a", fill_color=2), predicted=[[[0]]])
    blob = json.dumps(rec)
    for banned in ("red", "green", "(5, 5)", "(0, 0)", "coord"):
        assert banned not in blob


if __name__ == "__main__":
    fns = [v for k, v in sorted(globals().items())
           if k.startswith("test_") and callable(v)]
    passed = 0
    for fn in fns:
        fn()
        passed += 1
        print(f"  ok  {fn.__name__}")
    print(f"\n{passed}/{len(fns)} active-agent goal-trace tests passed")
