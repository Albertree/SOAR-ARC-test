"""
Tests for fast-path reuse of a stored copy-common-output rule (Slice 1).

Before this path existed the stored rule was *dead memory*: ``_apply_rule`` has
no per-grid case for the task-level ``copy_common_output`` rule, so the fast
path never matched it and every solve re-derived the answer through the full
SOAR pipeline (probe: ``Reused: 0``, ``via=pipeline(steps=14)``). These tests
lock the reuse path:

  * a stored copy_common_output rule is recognised and applied on the fast path
    (method == "stored_rule"), and
  * it stays value-agnostic — the *same* stored rule solves both easy000a (fixed
    red output) and easy000a2 (fixed green output), so reuse cannot have
    hard-coded a colour/coordinate, and
  * reuse does not manufacture a new rule file (knowledge is reused, not
    re-discovered), and increments the stored rule's times_reused.
"""

import json
import os

import pytest

from managers.arc_manager import ARCManager
from agent.active_agent import ActiveSoarAgent


COPY_COMMON_RULE = {
    "id": 1,
    "concept": "copy_common_example_output",
    "category": "other",
    "condition": {"type": "all_outputs_comm", "params": {}, "min_evidence": 1},
    "action": {"dsl": "make_grid", "args": {}},
    "rule": {"type": "copy_common_output", "confidence": 1.0},
    "covers": ["easy000a", "easy000a2"],
    "source_task": "easy000a",
    "anti_unification_trace": None,
    "created_at": "2026-01-01T00:00:00",
    "times_reused": 0,
}


@pytest.fixture
def manager():
    return ARCManager(data_root="data", semantic_memory_root="semantic_memory")


@pytest.fixture
def pm_root(tmp_path):
    """An isolated procedural_memory holding only the copy_common_output rule, so
    the test never mutates the repo's real rule files (times_reused is a counter
    written on reuse)."""
    root = tmp_path / "procedural_memory"
    root.mkdir()
    (root / "rule_001.json").write_text(json.dumps(COPY_COMMON_RULE), encoding="utf-8")
    return str(root)


def _expected_output(task):
    """Ground-truth test output grid (raw) for a single-test-pair task."""
    for pair in task.test_pairs:
        if getattr(pair, "output", None) is not None:
            return pair.output.contents
    return None


def _first_grid(predicted):
    """Normalise solve()'s return (list of grids) to the first grid."""
    if predicted and isinstance(predicted[0], list) and predicted[0] \
            and isinstance(predicted[0][0], list):
        return predicted[0]
    return predicted


@pytest.mark.parametrize("task_id", ["easy000a", "easy000a2"])
def test_fast_path_reuses_stored_rule(manager, pm_root, task_id):
    """Both tasks solve via the stored rule (not the pipeline), with the correct
    value-agnostic output."""
    agent = ActiveSoarAgent(procedural_memory_root=pm_root)
    task = manager.load_task(task_id)

    predicted = agent.solve(task)

    assert agent.last_solve_info["method"] == "stored_rule"
    assert agent.last_solve_info["rule_type"] == "copy_common_output"

    expected = _expected_output(task)
    assert expected is not None
    assert _first_grid(predicted) == expected


def test_reuse_is_value_agnostic(manager, pm_root):
    """The single stored rule yields *different* correct outputs for the two
    tasks — proof the reuse path carries no baked-in literal."""
    agent = ActiveSoarAgent(procedural_memory_root=pm_root)

    a = _first_grid(agent.solve(manager.load_task("easy000a")))
    a2 = _first_grid(agent.solve(manager.load_task("easy000a2")))

    assert a == _expected_output(manager.load_task("easy000a"))
    assert a2 == _expected_output(manager.load_task("easy000a2"))
    assert a != a2


def test_reuse_does_not_create_new_rule(manager, pm_root):
    """Reuse must not re-discover: still exactly one rule file, and its
    times_reused incremented once per solve."""
    agent = ActiveSoarAgent(procedural_memory_root=pm_root)
    agent.solve(manager.load_task("easy000a"))
    agent.solve(manager.load_task("easy000a2"))

    rule_files = [f for f in os.listdir(pm_root) if f.startswith("rule_")]
    assert len(rule_files) == 1

    with open(os.path.join(pm_root, rule_files[0]), encoding="utf-8") as fh:
        stored = json.load(fh)
    assert stored["times_reused"] == 2
