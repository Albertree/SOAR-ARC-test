"""
tests/test_episodic.py — exercise the iter-9 episodic writer
``agent.episodic.write_attempt``.

Runs without pytest:

    python tests/test_episodic.py

Dependency-free, same runner style as the other tests under ``tests/``.
"""

from __future__ import annotations

import copy
import json
import os
import shutil
import sys
import tempfile
import traceback

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

from agent.episodic import EPISODIC_MEMORY_ROOT, write_attempt  # noqa: E402


HEX = "00576224"


def _tmp() -> str:
    return tempfile.mkdtemp(prefix="episodic_test_")


# ──────────────────────────────────────────────────────────────────────────
# Tests.
# ──────────────────────────────────────────────────────────────────────────

def test_default_root_constant_is_episodic_memory() -> None:
    # P4 in scripts/check_invariants.sh walks 'episodic_memory'; if the
    # default constant drifts, the writer would land outside the directory
    # the checker measures.
    assert EPISODIC_MEMORY_ROOT == "episodic_memory"


def test_writes_attempt_folder_with_three_artifacts() -> None:
    root = _tmp()
    try:
        path = write_attempt(HEX, outcome="submitted", info={}, root=root)
        assert os.path.isdir(path)
        assert os.path.basename(path) == "attempt_001"
        assert os.path.isfile(os.path.join(path, "metadata.json"))
        assert os.path.isfile(os.path.join(path, "trace.json"))
        assert os.path.isdir(os.path.join(path, "grids"))
    finally:
        shutil.rmtree(root, ignore_errors=True)


def test_metadata_json_carries_outcome_and_info() -> None:
    root = _tmp()
    try:
        path = write_attempt(
            HEX, outcome="submitted",
            info={"method": "stored_rule", "rule_type": "identity", "steps": 0},
            root=root,
        )
        with open(os.path.join(path, "metadata.json"), encoding="utf-8") as fh:
            data = json.load(fh)
        assert data["task_hex"] == HEX
        assert data["attempt_index"] == 1
        assert data["outcome"] == "submitted"
        assert data["info"]["method"] == "stored_rule"
        assert data["info"]["rule_type"] == "identity"
        assert isinstance(data["created_at"], str) and data["created_at"]
    finally:
        shutil.rmtree(root, ignore_errors=True)


def test_attempt_index_increments_monotonically() -> None:
    root = _tmp()
    try:
        p1 = write_attempt(HEX, outcome="submitted", info={}, root=root)
        p2 = write_attempt(HEX, outcome="submitted", info={}, root=root)
        p3 = write_attempt(HEX, outcome="submitted", info={}, root=root)
        assert os.path.basename(p1) == "attempt_001"
        assert os.path.basename(p2) == "attempt_002"
        assert os.path.basename(p3) == "attempt_003"
    finally:
        shutil.rmtree(root, ignore_errors=True)


def test_attempt_index_recovers_after_external_directory() -> None:
    # Simulate a partial prior session: 005 already exists on disk.
    # The next call must take 006, not 002.
    root = _tmp()
    try:
        task_dir = os.path.join(root, HEX)
        os.makedirs(os.path.join(task_dir, "attempt_005"), exist_ok=True)
        path = write_attempt(HEX, outcome="submitted", info={}, root=root)
        assert os.path.basename(path) == "attempt_006"
    finally:
        shutil.rmtree(root, ignore_errors=True)


def test_ignores_non_attempt_siblings_when_indexing() -> None:
    root = _tmp()
    try:
        task_dir = os.path.join(root, HEX)
        os.makedirs(task_dir, exist_ok=True)
        # Junk that must not affect indexing.
        os.makedirs(os.path.join(task_dir, "notes"), exist_ok=True)
        os.makedirs(os.path.join(task_dir, "attempt_xyz"), exist_ok=True)
        path = write_attempt(HEX, outcome="submitted", info={}, root=root)
        assert os.path.basename(path) == "attempt_001"
    finally:
        shutil.rmtree(root, ignore_errors=True)


def test_isolated_per_task_hex() -> None:
    root = _tmp()
    try:
        other = "007bbfb7"
        write_attempt(HEX, outcome="submitted", info={}, root=root)
        write_attempt(HEX, outcome="submitted", info={}, root=root)
        path = write_attempt(other, outcome="submitted", info={}, root=root)
        assert os.path.basename(path) == "attempt_001"
        assert os.path.dirname(path).endswith(other)
    finally:
        shutil.rmtree(root, ignore_errors=True)


def test_info_is_deep_copied() -> None:
    root = _tmp()
    try:
        info = {"steps": 0, "nested": {"k": [1, 2, 3]}}
        path = write_attempt(HEX, outcome="submitted", info=info, root=root)
        # Mutate caller's view after the write.
        info["nested"]["k"].append(99)
        info["steps"] = 42
        with open(os.path.join(path, "metadata.json"), encoding="utf-8") as fh:
            data = json.load(fh)
        assert data["info"]["steps"] == 0
        assert data["info"]["nested"]["k"] == [1, 2, 3]
    finally:
        shutil.rmtree(root, ignore_errors=True)


def test_trace_json_starts_as_empty_list() -> None:
    # CLAUDE.md §3.3 names trace.json as a per-cycle log. Until the cycle
    # is instrumented (a later iter), the writer lays down the file as an
    # empty list — a valid JSON document the next iter can extend in place.
    root = _tmp()
    try:
        path = write_attempt(HEX, outcome="submitted", info={}, root=root)
        with open(os.path.join(path, "trace.json"), encoding="utf-8") as fh:
            assert json.load(fh) == []
    finally:
        shutil.rmtree(root, ignore_errors=True)


def test_grids_directory_is_empty() -> None:
    root = _tmp()
    try:
        path = write_attempt(HEX, outcome="submitted", info={}, root=root)
        grids = os.path.join(path, "grids")
        assert os.path.isdir(grids)
        assert os.listdir(grids) == []
    finally:
        shutil.rmtree(root, ignore_errors=True)


def test_rejects_malformed_task_hex() -> None:
    root = _tmp()
    try:
        for bad in ("", "abc", "GGGGGGGG", "00576224a", None, 123):
            try:
                write_attempt(bad, outcome="submitted", info={}, root=root)
            except ValueError:
                continue
            else:
                raise AssertionError(f"accepted malformed task_hex: {bad!r}")
    finally:
        shutil.rmtree(root, ignore_errors=True)


def test_rejects_empty_outcome() -> None:
    root = _tmp()
    try:
        for bad in ("", None):
            try:
                write_attempt(HEX, outcome=bad, info={}, root=root)
            except ValueError:
                continue
            else:
                raise AssertionError(f"accepted empty outcome: {bad!r}")
    finally:
        shutil.rmtree(root, ignore_errors=True)


def test_outcome_no_prediction_round_trip() -> None:
    # The active_agent helper passes "no_prediction" when predicted is None.
    root = _tmp()
    try:
        path = write_attempt(HEX, outcome="no_prediction", info={"x": 1},
                             root=root)
        with open(os.path.join(path, "metadata.json"), encoding="utf-8") as fh:
            data = json.load(fh)
        assert data["outcome"] == "no_prediction"
        assert data["info"] == {"x": 1}
    finally:
        shutil.rmtree(root, ignore_errors=True)


def test_creates_root_directory_if_missing() -> None:
    parent = _tmp()
    try:
        # Root does not exist yet — write_attempt must create the chain.
        root = os.path.join(parent, "deeper", "episodic_memory")
        path = write_attempt(HEX, outcome="submitted", info={}, root=root)
        assert os.path.isdir(path)
    finally:
        shutil.rmtree(parent, ignore_errors=True)


def test_concurrent_calls_do_not_overwrite() -> None:
    # If `attempt_001` already exists (from a prior call in the same
    # process), the next write must land in `attempt_002`, not error,
    # not overwrite. exist_ok=False on the inner dir keeps overwrite from
    # ever being silently swallowed.
    root = _tmp()
    try:
        p1 = write_attempt(HEX, outcome="submitted", info={"a": 1}, root=root)
        p2 = write_attempt(HEX, outcome="submitted", info={"a": 2}, root=root)
        assert p1 != p2
        with open(os.path.join(p1, "metadata.json"), encoding="utf-8") as fh:
            assert json.load(fh)["info"]["a"] == 1
        with open(os.path.join(p2, "metadata.json"), encoding="utf-8") as fh:
            assert json.load(fh)["info"]["a"] == 2
    finally:
        shutil.rmtree(root, ignore_errors=True)


# ──────────────────────────────────────────────────────────────────────────
# Driver.
# ──────────────────────────────────────────────────────────────────────────

def _run_all() -> int:
    tests = [
        test_default_root_constant_is_episodic_memory,
        test_writes_attempt_folder_with_three_artifacts,
        test_metadata_json_carries_outcome_and_info,
        test_attempt_index_increments_monotonically,
        test_attempt_index_recovers_after_external_directory,
        test_ignores_non_attempt_siblings_when_indexing,
        test_isolated_per_task_hex,
        test_info_is_deep_copied,
        test_trace_json_starts_as_empty_list,
        test_grids_directory_is_empty,
        test_rejects_malformed_task_hex,
        test_rejects_empty_outcome,
        test_outcome_no_prediction_round_trip,
        test_creates_root_directory_if_missing,
        test_concurrent_calls_do_not_overwrite,
    ]
    fails = 0
    for t in tests:
        try:
            t()
            print(f"  OK   {t.__name__}")
        except AssertionError as e:
            fails += 1
            print(f"  FAIL {t.__name__}: {e}")
        except Exception:
            fails += 1
            print(f"  FAIL {t.__name__}: unexpected exception")
            traceback.print_exc()
    return fails


if __name__ == "__main__":
    rc = _run_all()
    if rc == 0:
        print("\nall episodic writer tests passed.")
    else:
        print(f"\n{rc} test(s) failed.")
    sys.exit(0 if rc == 0 else 1)
