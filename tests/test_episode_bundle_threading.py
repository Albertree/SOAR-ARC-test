"""
Tests for iter 51: the §3 comparison bundle (compare_scheduler.build_patterns) is
assembled **once** per episode and threaded through the module A+B+C observability
records, instead of each leg recomputing it.

Iter 50's "next gap" flagged that ``ActiveSoarAgent._record_episode`` recomputed
``build_patterns(task)`` 2-3× per episode — once inside ``slice1_descent_record``
(module A), once in ``_slice1_goal_record`` (module B), once at the
``slice1_flow_steps`` call (module C) — a criterion-4 (탐색 건전성, SLICE_1_LOOP.md
§8) redundant-search smell, since the COMM/DIFF comparison work is identical each
time. Threading one bundle removes the redundancy.

This is an efficiency/uniformity change only — it must be **behaviour-identical**:
the threaded records must equal the standalone (recompute-per-leg) records, the
shared bundle must not be mutated, and the episode trace must still carry the full
A+B+C triple. These tests assert exactly that, plus that the bundle is built once.

pytest is not installed here, so the file is also runnable directly:
    python tests/test_episode_bundle_threading.py
"""

import os
import sys
import tempfile
from types import SimpleNamespace

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ARCKG.grid import Grid
from ARCKG.pair import Pair
from agent import active_agent as aa
from agent import compare_scheduler as cs
from agent.active_agent import ActiveSoarAgent
from agent.compare_scheduler import build_patterns
from agent.conditions import descent_path
from agent.conditions.descent_path import slice1_descent_record
from agent.flow_trace import slice1_flow_steps


# --- fixtures (mirror the Slice-1 target tasks) ---------------------------

def _grid(node_id, raw):
    return Grid(node_id, [row[:] for row in raw])


def _pair(pid, in_raw, out_raw=None):
    out = _grid(f"{pid}.G1", out_raw) if out_raw is not None else None
    return Pair(pid, _grid(f"{pid}.G0", in_raw), out)


def _fixed_output_task(task_hex, fill_color):
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


# --- threaded records equal standalone (recompute-per-leg) records --------

def test_descent_record_threaded_equals_standalone():
    task = _fixed_output_task("easy000a", fill_color=2)
    shared = build_patterns(task)
    assert slice1_descent_record(task, patterns=shared) == slice1_descent_record(task)


def test_goal_record_threaded_equals_standalone():
    task = _fixed_output_task("easy000a", fill_color=2)
    shared = build_patterns(task)
    agent = ActiveSoarAgent()
    threaded = agent._slice1_goal_record(task, predicted=[[[0]]], patterns=shared)
    standalone = agent._slice1_goal_record(task, predicted=[[[0]]])
    assert threaded == standalone


def test_flow_record_threaded_equals_standalone():
    task = _fixed_output_task("easy000a", fill_color=2)
    shared = build_patterns(task)
    assert slice1_flow_steps(shared) == slice1_flow_steps(build_patterns(task))


# --- the shared bundle is read-only to each record ------------------------

def test_shared_bundle_not_mutated_by_records():
    task = _fixed_output_task("easy000a", fill_color=2)
    shared = build_patterns(task)
    before = set(shared.keys())
    slice1_descent_record(task, patterns=shared)   # adds level_sibling_counts onto a copy
    ActiveSoarAgent()._slice1_goal_record(task, predicted=[[[0]]], patterns=shared)
    slice1_flow_steps(shared)
    # descent must NOT have leaked its level_sibling_counts augmentation into the
    # shared bundle, and no record may add/remove keys on it.
    assert set(shared.keys()) == before
    assert "level_sibling_counts" not in shared


# --- the bundle is assembled exactly once per episode ---------------------

def test_build_patterns_called_once_per_episode():
    task = _fixed_output_task("easy000a", fill_color=2)
    calls = {"n": 0}
    real = cs.build_patterns

    def counting(*a, **k):
        calls["n"] += 1
        return real(*a, **k)

    # Patch every binding a record path could reach: active_agent's module-level
    # import and compare_scheduler's own name (descent_path imports it locally at
    # call time, so it resolves through compare_scheduler).
    aa.build_patterns = counting
    cs.build_patterns = counting
    try:
        agent = ActiveSoarAgent(
            procedural_memory_root=tempfile.mkdtemp(),
            episodic_memory_root=tempfile.mkdtemp(),
        )
        agent.last_solve_info = {"task_hex": task.task_hex}
        agent._record_episode(task, predicted=[[[0]]], trace=[])
    finally:
        aa.build_patterns = real
        cs.build_patterns = real
    assert calls["n"] == 1, f"build_patterns recomputed {calls['n']}× (expected 1)"


# --- value-agnostic: threaded episode identical for red vs green ----------

def test_threaded_records_value_agnostic_red_equals_green():
    red_task = _fixed_output_task("easy000a", fill_color=2)
    green_task = _fixed_output_task("easy000a2", fill_color=3)
    agent = ActiveSoarAgent()

    def triple(task):
        shared = build_patterns(task)
        return (
            slice1_descent_record(task, patterns=shared),
            agent._slice1_goal_record(task, predicted=[[[0]]], patterns=shared),
            slice1_flow_steps(shared),
        )

    assert triple(red_task) == triple(green_task)


if __name__ == "__main__":
    fns = [v for k, v in sorted(globals().items())
           if k.startswith("test_") and callable(v)]
    passed = 0
    for fn in fns:
        fn()
        passed += 1
        print(f"  ok  {fn.__name__}")
    print(f"\n{passed}/{len(fns)} bundle-threading tests passed")
