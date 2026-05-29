"""
Tests for agent/episodic.py — the per-solve() episodic writer (CLAUDE.md §3.3,
INVARIANTS.md §2 P4). Verifies that every solve() invocation leaves exactly one
attempt_NNN/ folder with the mandated trace.json / grids/ / metadata.json, that
attempt indices increment, and that the slice tasks (easy000a / easy000a2)
actually produce episodes end-to-end through ActiveSoarAgent.solve().

Self-runs (pytest is absent on this machine): `python tests/test_episodic_writer.py`.
"""

import os
import sys
import json
import shutil
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agent.episodic import write_episode, _next_attempt_index


_passed = 0
_failed = 0


def check(cond, msg):
    global _passed, _failed
    if cond:
        _passed += 1
    else:
        _failed += 1
        print(f"  FAIL: {msg}")


def test_writes_three_artifacts():
    root = tempfile.mkdtemp()
    try:
        path = write_episode(
            root, "deadbeef",
            predicted=[[[1, 2], [3, 4]]],
            info={"method": "pipeline", "rule_type": "copy_common_output"},
            trace=[{"phase": "cycle_summary", "steps_taken": 14}],
            grid_steps=[[[0, 0]], [[1, 2], [3, 4]]],
        )
        check(path.endswith("attempt_001"), "first attempt is attempt_001")
        check(os.path.isfile(os.path.join(path, "metadata.json")), "metadata.json written")
        check(os.path.isfile(os.path.join(path, "trace.json")), "trace.json written")
        check(os.path.isdir(os.path.join(path, "grids")), "grids/ dir written")
        check(os.path.isfile(os.path.join(path, "grids", "step_000.json")), "step_000 written")
        check(os.path.isfile(os.path.join(path, "grids", "step_001.json")), "step_001 written")

        with open(os.path.join(path, "metadata.json"), encoding="utf-8") as f:
            md = json.load(f)
        check(md["task_hex"] == "deadbeef", "metadata task_hex")
        check(md["attempt_index"] == 1, "metadata attempt_index")
        check(md["outcome"] == "submitted", "outcome=submitted when predicted")
        check("created_at" in md, "metadata has created_at")

        with open(os.path.join(path, "trace.json"), encoding="utf-8") as f:
            tr = json.load(f)
        check(isinstance(tr, list) and tr[0]["steps_taken"] == 14, "trace preserved")
    finally:
        shutil.rmtree(root, ignore_errors=True)


def test_attempt_index_increments():
    root = tempfile.mkdtemp()
    try:
        write_episode(root, "aaaaaaaa", predicted=[[[1]]], info={}, trace=[], grid_steps=[])
        p2 = write_episode(root, "aaaaaaaa", predicted=[[[1]]], info={}, trace=[], grid_steps=[])
        check(p2.endswith("attempt_002"), "second attempt is attempt_002")
        check(_next_attempt_index(os.path.join(root, "aaaaaaaa")) == 3, "next index is 3")
    finally:
        shutil.rmtree(root, ignore_errors=True)


def test_no_prediction_outcome():
    root = tempfile.mkdtemp()
    try:
        path = write_episode(root, "bbbbbbbb", predicted=None, info={}, trace=[], grid_steps=[])
        with open(os.path.join(path, "metadata.json"), encoding="utf-8") as f:
            md = json.load(f)
        check(md["outcome"] == "no_prediction", "outcome=no_prediction when predicted is None")
    finally:
        shutil.rmtree(root, ignore_errors=True)


def test_solve_writes_episode_end_to_end():
    """Real ActiveSoarAgent.solve() on slice tasks must leave one episode each."""
    from managers.arc_manager import ARCManager
    from agent.active_agent import ActiveSoarAgent

    ep_root = tempfile.mkdtemp()
    try:
        manager = ARCManager(data_root="data", semantic_memory_root="semantic_memory")
        agent = ActiveSoarAgent(
            semantic_memory_root="semantic_memory",
            procedural_memory_root="procedural_memory",
            episodic_memory_root=ep_root,
            max_steps=50,
        )
        for task_hex in ("easy000a", "easy000a2"):
            task = manager.load_task(task_hex)
            agent.solve(task)
            attempt = os.path.join(ep_root, task_hex, "attempt_001")
            check(os.path.isdir(attempt), f"{task_hex} produced attempt_001")
            check(os.path.isfile(os.path.join(attempt, "metadata.json")),
                  f"{task_hex} metadata.json present")
            check(os.path.isfile(os.path.join(attempt, "trace.json")),
                  f"{task_hex} trace.json present")
            with open(os.path.join(attempt, "metadata.json"), encoding="utf-8") as f:
                md = json.load(f)
            check(md["outcome"] == "submitted", f"{task_hex} submitted a prediction")
    finally:
        shutil.rmtree(ep_root, ignore_errors=True)


if __name__ == "__main__":
    test_writes_three_artifacts()
    test_attempt_index_increments()
    test_no_prediction_outcome()
    test_solve_writes_episode_end_to_end()
    print(f"\n{_passed} passed, {_failed} failed")
    sys.exit(1 if _failed else 0)
