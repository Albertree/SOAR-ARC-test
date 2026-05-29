"""Tests for the *reuse/backfill* write path of save_rule_to_ltm.

Iter 22 added validate_rule to the *new-rule* branch of save_rule_to_ltm, but
the equivalence branch — which extends a matched rule's `covers` and backfills
its {condition, action} pair before re-writing it — bypassed the guard. A
stored rule whose pair does not resolve (legacy / dead memory) could thus be
extended and re-persisted without ever being validated (CLAUDE.md §3.2,
INVARIANTS §1 F4). This iter routes that write path through validate_rule too.

These tests lock that:
  1. Extending a *valid* equivalent rule still works (no false positive).
  2. Extending a *dead-memory* equivalent rule raises RuleSchemaError and
     leaves the on-disk file untouched (fail-closed; F7 — not swallowed).

Standalone runner (no pytest dependency):
    python tests/test_validate_rule_reuse.py
"""

import json
import os
import sys
import tempfile

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from agent.memory import RuleSchemaError, save_rule_to_ltm


def _assert_raises(fn, needle=None):
    try:
        fn()
    except RuleSchemaError as e:
        if needle is not None:
            assert needle in str(e), f"expected {needle!r} in {e!r}"
        return
    raise AssertionError("expected RuleSchemaError, none raised")


def _write_rule(root, entry):
    os.makedirs(root, exist_ok=True)
    path = os.path.join(root, "rule_001.json")
    with open(path, "w") as fh:
        json.dump(entry, fh, indent=2)
    return path


def _valid_stored():
    """A valid, already-on-disk copy_common_output rule (the rule_003 shape)."""
    return {
        "id": 1,
        "concept": "copy_common_example_output",
        "category": "other",
        "condition": {"type": "all_outputs_comm", "params": {}, "min_evidence": 1},
        "action": {"dsl": "make_grid", "args": {}},
        "rule": {"type": "copy_common_output", "confidence": 1.0},
        "covers": ["easy000a"],
        "source_task": "easy000a",
        "anti_unification_trace": None,
        "created_at": "2026-05-29T20:02:33.463388",
        "times_reused": 0,
    }


def _dead_stored():
    """A stored rule whose condition.type does NOT resolve in the live
    registry (the legacy dead-memory shape): consistent_color_mapping is not
    one of this branch's five registered matchers."""
    return {
        "id": 1,
        "concept": "swap_two_colors",
        "category": "color_transform",
        "condition": {"type": "consistent_color_mapping", "params": {}, "min_evidence": 1},
        "action": {"dsl": "coloring", "args": {"mapping": {"2": 0}}},
        "rule": {"type": "color_mapping", "mapping": {"2": 0}},
        "covers": ["deadbeef"],
        "source_task": "deadbeef",
        "anti_unification_trace": None,
        "created_at": "2026-05-13T09:00:00.000000",
        "times_reused": 0,
    }


# --- (1) extending a valid equivalent rule still works --------------------

def test_reuse_valid_rule_extends_covers():
    with tempfile.TemporaryDirectory() as d:
        path = _write_rule(d, _valid_stored())
        # An equivalent copy_common_output rule for a *new* task.
        out = save_rule_to_ltm(
            {"type": "copy_common_output", "confidence": 1.0},
            "easy000a2",
            procedural_memory_root=d,
        )
        assert out == path, "should extend the existing file, not create a new one"
        with open(path) as fh:
            stored = json.load(fh)
        assert "easy000a2" in stored["covers"], "covers should be extended"
        assert sorted(stored["covers"]) == ["easy000a", "easy000a2"]
        # still exactly one rule file (no duplicate)
        assert [f for f in os.listdir(d) if f.startswith("rule_")] == ["rule_001.json"]


def test_reuse_valid_rule_idempotent_when_task_present():
    # Re-saving for a task already in covers writes nothing new and does not raise.
    with tempfile.TemporaryDirectory() as d:
        path = _write_rule(d, _valid_stored())
        before = open(path).read()
        save_rule_to_ltm(
            {"type": "copy_common_output", "confidence": 1.0},
            "easy000a",  # already in covers
            procedural_memory_root=d,
        )
        assert open(path).read() == before, "no change expected for known task"


# --- (2) extending a dead-memory rule fails closed ------------------------

def test_reuse_dead_memory_rule_raises_and_does_not_mutate():
    with tempfile.TemporaryDirectory() as d:
        path = _write_rule(d, _dead_stored())
        before = open(path).read()
        # An equivalent color_mapping payload for a new task would normally
        # extend covers; the mutated entry must now be validated and rejected.
        _assert_raises(
            lambda: save_rule_to_ltm(
                {"type": "color_mapping", "mapping": {"2": 0}},
                "feedface",
                procedural_memory_root=d,
            ),
            "unknown condition.type",
        )
        assert open(path).read() == before, "dead rule must not be mutated on disk"


def test_reuse_backfilled_rule_validated():
    # A legacy stored rule lacking the {condition, action} pair gets it
    # backfilled in the reuse branch. If the backfilled condition resolves
    # (copy_common_output -> all_outputs_comm), the extend succeeds and the
    # written entry carries a valid pair.
    with tempfile.TemporaryDirectory() as d:
        legacy = {
            "id": 1,
            "rule": {"type": "copy_common_output", "confidence": 1.0},
            "covers": ["easy000a"],
            "source_task": "easy000a",
            "created_at": "2026-05-13T09:00:00.000000",
            "times_reused": 0,
        }
        path = _write_rule(d, legacy)
        save_rule_to_ltm(
            {"type": "copy_common_output", "confidence": 1.0},
            "easy000a2",
            procedural_memory_root=d,
        )
        with open(path) as fh:
            stored = json.load(fh)
        assert stored["condition"]["type"] == "all_outputs_comm", "condition backfilled"
        assert stored["action"]["dsl"] == "make_grid", "action backfilled"
        assert "easy000a2" in stored["covers"]


if __name__ == "__main__":
    funcs = [v for k, v in sorted(globals().items())
             if k.startswith("test_") and callable(v)]
    failed = 0
    for fn in funcs:
        try:
            fn()
            print(f"PASS {fn.__name__}")
        except AssertionError as e:
            failed += 1
            print(f"FAIL {fn.__name__}: {e}")
        except Exception as e:  # noqa: BLE001 — surface unexpected errors loudly
            failed += 1
            print(f"ERROR {fn.__name__}: {type(e).__name__}: {e}")
    print(f"\n{len(funcs) - failed}/{len(funcs)} passed")
    sys.exit(1 if failed else 0)
