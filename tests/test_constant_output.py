"""
Tests for R0's recognition substrate: the condition-matcher registry and the
`constant_output` matcher (BACKLOG_LOOP.md R0).

Two layers:
  * unit       — the matcher's logic on synthetic `patterns` dicts.
  * integration— the matcher fed by the REAL `output_invariant` signal that
                 ExtractPatternOperator surfaces for an actual constant-output
                 task (easy0001), proving matcher and pipeline agree on schema.
"""

import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agent.conditions import CONDITION_REGISTRY, get_matcher, match  # noqa: E402


# ── registry ──────────────────────────────────────────────────────────
def test_matcher_is_registered():
    assert "constant_output" in CONDITION_REGISTRY
    assert get_matcher("constant_output") is not None


def test_unknown_matcher_raises():
    try:
        match("no_such_matcher", {})
    except KeyError:
        return
    assert False, "expected KeyError for unknown condition.type"


# ── unit: matcher logic on synthetic patterns ─────────────────────────
def test_fires_when_outputs_all_equal():
    patterns = {"output_invariant": {
        "all_equal": True, "evidence_count": 2, "common_output": [[0, 2]]}}
    assert match("constant_output", patterns, {"min_evidence": 2}) is True


def test_rejects_varying_outputs():
    patterns = {"output_invariant": {
        "all_equal": False, "evidence_count": 3, "common_output": None}}
    assert match("constant_output", patterns) is False


def test_rejects_insufficient_evidence():
    patterns = {"output_invariant": {
        "all_equal": True, "evidence_count": 1, "common_output": [[0]]}}
    assert match("constant_output", patterns, {"min_evidence": 2}) is False


def test_rejects_missing_signal():
    assert match("constant_output", {"grid_size_preserved": True}) is False
    assert match("constant_output", None) is False


# ── integration: real ExtractPatternOperator output ───────────────────
def test_extract_pattern_surfaces_output_invariant_on_constant_task():
    from managers.arc_manager import ARCManager
    from agent.wm import WorkingMemory
    from agent.active_operators import ExtractPatternOperator

    with tempfile.TemporaryDirectory() as tmp:
        task = ARCManager(semantic_memory_root=tmp).load_task("easy000a")

    wm = WorkingMemory()
    wm.task = task
    ExtractPatternOperator().effect(wm)

    inv = wm.s1["patterns"]["output_invariant"]
    # easy000a's every training output is the same grid (a 2 at (5,5)).
    assert inv["all_equal"] is True
    assert inv["evidence_count"] >= 2
    assert inv["common_output"] is not None
    # ...and the matcher recognizes it from the real signal.
    assert match("constant_output", wm.s1["patterns"]) is True
