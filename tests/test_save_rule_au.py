"""
Tests for agent/memory.py:save_rule — the sanctioned save + anti-unification
entry point (CLAUDE.md §8, BACKLOG_LOOP.md R3).

These prove that two canonical {condition, action} rules sharing a skeleton are
folded into ONE stored rule: by a plain covers-merge when their argument
expressions match, and by anti-unification (lifting the divergent position to a
?v variable, setting anti_unification_trace) when they diverge — driving
P1/P2/P3 up together instead of accreting one rule file per task.
"""

import json
import os

import pytest

from agent.memory import save_rule, load_all_rules


def _motion_rule(target_expr):
    """A canonical object_motion rule whose only divergent argument is the
    fitted target expression (the principal argument of place_object)."""
    return {
        "type": "object_motion",
        "condition": {
            "type": "object_motion",
            "params": {"min_evidence": 2},
            "min_evidence": 2,
        },
        "action": {"dsl": "place_object", "args": {"target": target_expr}},
        "confidence": 1.0,
    }


def _read(path):
    with open(path, "r") as fh:
        return json.load(fh)


def test_divergent_target_lifts_to_variable(tmp_path):
    pm = str(tmp_path / "pm")
    em = str(tmp_path / "em")

    p1 = save_rule(_motion_rule({"kind": "bottom_right"}), "taskA",
                   procedural_memory_root=pm, episodic_memory_root=em)
    # First task: a single concrete rule, no generalization yet.
    e1 = _read(p1)
    assert e1["action"]["args"]["target"] == {"kind": "bottom_right"}
    assert e1.get("anti_unification_trace") in (None, "")

    p2 = save_rule(_motion_rule({"kind": "constant", "pos": [5, 5]}), "taskB",
                   procedural_memory_root=pm, episodic_memory_root=em)

    # Same file (no second rule accreted), target lifted to a ?v variable,
    # covers unioned, trace recorded.
    assert p1 == p2
    files = [f for f in os.listdir(pm) if f.startswith("rule_")]
    assert len(files) == 1
    e2 = _read(p2)
    assert str(e2["action"]["args"]["target"]).startswith("?v")
    assert set(e2["covers"]) == {"taskA", "taskB"}
    assert e2["anti_unification_trace"]
    # The forensic trace JSON exists on disk.
    assert os.path.exists(em + os.sep + e2["anti_unification_trace"].replace("/", os.sep)) \
        or os.path.exists(os.path.join(em, *e2["anti_unification_trace"].split("/")[1:]))


def test_identical_args_plain_covers_merge(tmp_path):
    pm = str(tmp_path / "pm")
    em = str(tmp_path / "em")

    save_rule(_motion_rule({"kind": "bottom_right"}), "taskA",
              procedural_memory_root=pm, episodic_memory_root=em)
    p2 = save_rule(_motion_rule({"kind": "bottom_right"}), "taskB",
                   procedural_memory_root=pm, episodic_memory_root=em)

    files = [f for f in os.listdir(pm) if f.startswith("rule_")]
    assert len(files) == 1
    e = _read(p2)
    # Identical target → no lift, no trace, just an extended covers list.
    assert e["action"]["args"]["target"] == {"kind": "bottom_right"}
    assert set(e["covers"]) == {"taskA", "taskB"}
    assert e.get("anti_unification_trace") in (None, "")


def test_abstract_rule_absorbs_third_task_without_new_trace(tmp_path):
    pm = str(tmp_path / "pm")
    em = str(tmp_path / "em")

    save_rule(_motion_rule({"kind": "bottom_right"}), "taskA",
              procedural_memory_root=pm, episodic_memory_root=em)
    p = save_rule(_motion_rule({"kind": "constant", "pos": [5, 5]}), "taskB",
                  procedural_memory_root=pm, episodic_memory_root=em)
    trace_after_lift = _read(p)["anti_unification_trace"]
    assert trace_after_lift

    # A third divergent task is absorbed into the already-general rule with no
    # new trace and no churn (idempotency: one trace per family).
    p3 = save_rule(_motion_rule({"kind": "offset", "delta": [1, 1]}), "taskC",
                   procedural_memory_root=pm, episodic_memory_root=em)
    assert p3 == p
    e = _read(p3)
    assert set(e["covers"]) == {"taskA", "taskB", "taskC"}
    assert e["anti_unification_trace"] == trace_after_lift  # unchanged
    files = [f for f in os.listdir(pm) if f.startswith("rule_")]
    assert len(files) == 1


def test_different_skeleton_does_not_merge(tmp_path):
    pm = str(tmp_path / "pm")
    em = str(tmp_path / "em")

    save_rule(_motion_rule({"kind": "bottom_right"}), "taskA",
              procedural_memory_root=pm, episodic_memory_root=em)
    other = {
        "type": "constant_output",
        "condition": {"type": "constant_output",
                      "params": {"min_evidence": 2}, "min_evidence": 2},
        "action": {"dsl": "copy_common_output", "args": {}},
    }
    save_rule(other, "taskZ",
              procedural_memory_root=pm, episodic_memory_root=em)

    # Different (condition.type, action.dsl) skeletons → two distinct rules; AU
    # must not bridge a skeleton mismatch.
    files = sorted(f for f in os.listdir(pm) if f.startswith("rule_"))
    assert len(files) == 2


def test_legacy_rule_without_skeleton_falls_back(tmp_path):
    pm = str(tmp_path / "pm")
    em = str(tmp_path / "em")

    # color_mapping rules carry no top-level {condition, action} skeleton; they
    # must route through the exact-equivalence covers-merge, not AU.
    legacy = {"type": "color_mapping", "mapping": {1: 2}}
    p1 = save_rule(legacy, "taskA",
                   procedural_memory_root=pm, episodic_memory_root=em)
    p2 = save_rule({"type": "color_mapping", "mapping": {1: 2}}, "taskB",
                   procedural_memory_root=pm, episodic_memory_root=em)
    assert p1 == p2  # equivalent legacy rule → covers merge, no second file
    files = [f for f in os.listdir(pm) if f.startswith("rule_")]
    assert len(files) == 1
    e = _read(p2)
    assert set(e["covers"]) == {"taskA", "taskB"}
    assert e.get("anti_unification_trace") in (None, "")
