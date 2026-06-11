"""
Tests for the `constant_output` recognition path (iter 3).

Locks two things:
  1. The `constant_output` matcher fires iff every Inter-Grid (role==G1)
     comparison is COMM, and is value-agnostic (no literal colour/coord).
  2. SelectTargetOperator schedules that Inter-Grid comparison and
     ExtractPatternOperator surfaces its verdict into patterns, so on
     easy000a (all outputs identical) the matcher recognises the task.

Run directly: `python tests/test_constant_output.py`.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agent.conditions import get_matcher, registered_names


def test_matcher_registered():
    assert "constant_output" in registered_names()
    print("ok test_matcher_registered")


def test_matcher_fires_only_on_all_comm():
    m = get_matcher("constant_output")
    assert m({"inter_output": {"count": 1, "all_comm": True}}, {}) is True
    assert m({"inter_output": {"count": 3, "all_comm": True}}, {}) is True
    # any DIFF among the comparisons → no constant output
    assert m({"inter_output": {"count": 1, "all_comm": False}}, {}) is False
    # no comparison evidence at all → cannot assert constancy
    assert m({"inter_output": {"count": 0, "all_comm": False}}, {}) is False
    # robust to missing / empty patterns (matchers never crash)
    assert m({}, {}) is False
    assert m(None, {}) is False
    print("ok test_matcher_fires_only_on_all_comm")


def test_easy000a_recognized_end_to_end():
    """The decisive Inter-Grid role==G1 comparison runs and is recognised."""
    from managers.arc_manager import ARCManager
    from agent.active_operators import (
        SelectTargetOperator, CompareOperator, ExtractPatternOperator,
    )
    from agent.wm import WorkingMemory
    from agent.io import inject_arc_task
    from agent.wm_logger import reset_wm_snapshot

    mgr = ARCManager(data_root="data", semantic_memory_root="semantic_memory")
    task = mgr.load_task("ARC_easy_a/easy000a.json")
    wm = WorkingMemory()
    reset_wm_snapshot(wm)
    inject_arc_task(task, wm)

    SelectTargetOperator().effect(wm)
    types = [s["type"] for s in wm.s1.get("pending-comparisons")]
    assert "inter_output" in types, types  # module C scheduled the new compare

    cmp = CompareOperator()
    guard = 0
    while wm.s1.get("pending-comparisons") and guard < 64:
        cmp.effect(wm)
        guard += 1

    io = wm.s1["comparisons"]["inter_output_0"]["result"]["result"]
    assert io["type"] == "COMM", io  # the two outputs are identical (contents too)

    ExtractPatternOperator().effect(wm)
    info = wm.s1["patterns"]["inter_output"]
    assert info["count"] >= 1 and info["all_comm"] is True, info
    assert get_matcher("constant_output")(wm.s1["patterns"], {}) is True
    print("ok test_easy000a_recognized_end_to_end")


if __name__ == "__main__":
    test_matcher_registered()
    test_matcher_fires_only_on_all_comm()
    test_easy000a_recognized_end_to_end()
    print("all constant_output tests passed")
