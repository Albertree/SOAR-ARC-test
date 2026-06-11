"""
Tests for agent/episodic.py — the episodic-memory writer (CLAUDE.md §3.3).

Verifies the on-disk contract: one attempt_NNN/ folder per call, with
trace.json + metadata.json + grids/step_NNN.json, and monotonic attempt
indexing so repeated solves accumulate (positive signal P4).

Runs standalone (no pytest required):  python tests/test_episodic.py
"""

import json
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agent.episodic import write_attempt, _next_attempt_index


def _attempt(root, task, n):
    return os.path.join(root, task, f"attempt_{n:03d}")


def test_writes_attempt_layout():
    with tempfile.TemporaryDirectory() as root:
        path = write_attempt(
            "easy000a",
            trace={"granularity": "summary", "path": "pipeline"},
            metadata={"outcome": "prediction-produced"},
            grids=[("test0-input", [[0, 1], [2, 3]]), ("predicted", [[[5]]])],
            episodic_root=root,
        )
        assert path == _attempt(root, "easy000a", 0)
        assert os.path.isfile(os.path.join(path, "trace.json"))
        assert os.path.isfile(os.path.join(path, "metadata.json"))
        assert os.path.isfile(os.path.join(path, "grids", "step_000.json"))
        assert os.path.isfile(os.path.join(path, "grids", "step_001.json"))

        with open(os.path.join(path, "grids", "step_000.json")) as f:
            step0 = json.load(f)
        assert step0 == {"label": "test0-input", "grid": [[0, 1], [2, 3]]}
        with open(os.path.join(path, "trace.json")) as f:
            assert json.load(f)["granularity"] == "summary"
    print("ok test_writes_attempt_layout")


def test_attempts_accumulate_monotonically():
    with tempfile.TemporaryDirectory() as root:
        for expect in range(3):
            p = write_attempt(
                "t1", trace={}, metadata={}, grids=[], episodic_root=root
            )
            assert p == _attempt(root, "t1", expect), (p, expect)
        # _next_attempt_index sees the three written folders → next is 3
        assert _next_attempt_index(os.path.join(root, "t1")) == 3
        # a different task starts its own counter at 0
        p = write_attempt("t2", trace={}, metadata={}, grids=[], episodic_root=root)
        assert p == _attempt(root, "t2", 0)
    print("ok test_attempts_accumulate_monotonically")


def test_next_index_empty():
    with tempfile.TemporaryDirectory() as root:
        assert _next_attempt_index(os.path.join(root, "missing")) == 0
    print("ok test_next_index_empty")


if __name__ == "__main__":
    test_writes_attempt_layout()
    test_attempts_accumulate_monotonically()
    test_next_index_empty()
    print("all episodic tests passed")
