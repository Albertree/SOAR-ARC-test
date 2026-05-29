"""
Tests for agent/conditions/descent_path.py:slice1_descent_record — module A's
§3 hierarchical descent made observable on every episode.

Module A's descent (TASK→PAIR→GRID, depth entered by necessity — P1, the spine of
the raw-prose flow) is performed live by ``DescendOperator`` on the slow path, but
the probe solves via the fast path (stored rule) where the cycle never runs, and
the episode trace recorded module B's goal walk and module C's comparison-flow form
yet never module A's descent. ``slice1_descent_record`` is the missing record: it
recomputes the itinerary the same value-agnostic way the live operator does (one
shared assembly, ``descent_itinerary_for_task``) and is appended to every episode.

Decisive Slice-1 property: **value-agnosticism** (SLICE_1_LOOP §9) — the record is
built from COMM/DIFF verdicts and structural counts only, so easy000a (red) and
easy000a2 (green) yield a byte-identical descent record.

pytest is not installed here, so the file is also runnable directly:
    python tests/test_descent_record.py
"""

import json
import os
import sys
from types import SimpleNamespace

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ARCKG.grid import Grid
from ARCKG.pair import Pair
from agent.conditions.descent_path import (
    descent_itinerary_for_task,
    slice1_descent_record,
)
from agent.active_agent import ActiveSoarAgent


# --- fixtures: Slice-1 target tasks, built from real ARCKG nodes ----------

def _grid(node_id, raw):
    return Grid(node_id, [row[:] for row in raw])


def _pair(pid, in_raw, out_raw=None):
    out = _grid(f"{pid}.G1", out_raw) if out_raw is not None else None
    return Pair(pid, _grid(f"{pid}.G0", in_raw), out)


def _fixed_output_task(task_hex, fill_color):
    """Every example output is the SAME grid (`fill_color` at (5,5) on a 6x6
    black canvas); inputs vary; the test pair carries input only."""
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


# --- the §3 descent form ---------------------------------------------------

def test_descent_record_walks_task_pair_to_grid():
    rec = slice1_descent_record(_fixed_output_task("easy000a", fill_color=2))
    assert rec["phase"] == "hierarchical_descent"
    assert rec["module"] == "A"
    # P1: the flow descends past TASK (no sibling tasks) and PAIR (cannot yet see
    # the resolving GRID comparisons), stopping at GRID where the goal resolves.
    assert rec["descend_from"] == ["task", "pair"]
    assert rec["terminal"] == "grid"
    assert rec["itinerary"] == ["task", "pair", "grid"]


def test_for_task_helper_matches_record_payload():
    """The episode record is exactly the shared assembly's itinerary, wrapped."""
    task = _fixed_output_task("easy000a", fill_color=2)
    itinerary = descent_itinerary_for_task(task)
    rec = slice1_descent_record(task)
    assert {k: rec[k] for k in itinerary} == itinerary


# --- value-agnosticism: easy000a vs easy000a2 ------------------------------

def test_descent_record_identical_across_targets():
    a = slice1_descent_record(_fixed_output_task("easy000a", fill_color=2))
    a2 = slice1_descent_record(_fixed_output_task("easy000a2", fill_color=3))
    assert a == a2          # different output colours, identical descent path


def test_descent_record_carries_no_colour_or_coordinate():
    rec = slice1_descent_record(_fixed_output_task("easy000a", fill_color=2))
    blob = json.dumps(rec)
    for banned in ("red", "green", "(5, 5)", "(0, 0)", "coord", "color"):
        assert banned not in blob


# --- JSON-serialisable (P7) ------------------------------------------------

def test_descent_record_json_serialisable():
    rec = slice1_descent_record(_fixed_output_task("easy000a", fill_color=2))
    assert json.loads(json.dumps(rec)) == rec


# --- it actually lands in the episode trace --------------------------------

def test_descent_record_present_in_episode_trace():
    import tempfile
    task = _fixed_output_task("easy000a", fill_color=2)
    agent = ActiveSoarAgent(
        procedural_memory_root=tempfile.mkdtemp(),
        episodic_memory_root=tempfile.mkdtemp(),
    )
    agent.last_solve_info = {"task_hex": task.task_hex}
    agent._record_episode(task, predicted=[[[0]]], trace=[])
    # find the most recent attempt folder and read its trace.json
    root = os.path.join(agent.episodic_memory_root, task.task_hex)
    attempts = sorted(os.listdir(root))
    with open(os.path.join(root, attempts[-1], "trace.json"), encoding="utf-8") as f:
        tr = json.load(f)
    phases = [e.get("phase") for e in tr if isinstance(e, dict)]
    # the module A+B+C observability triple is all present
    assert "hierarchical_descent" in phases   # A
    assert "goal_evolution" in phases          # B
    assert "comparison_flow" in phases         # C


if __name__ == "__main__":
    fns = [v for k, v in sorted(globals().items())
           if k.startswith("test_") and callable(v)]
    passed = 0
    for fn in fns:
        fn()
        passed += 1
        print(f"  ok  {fn.__name__}")
    print(f"\n{passed}/{len(fns)} descent-record tests passed")
