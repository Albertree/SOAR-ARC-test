"""
Covers-integrity guard (iter 7).

Root cause of the dead-rule accretion this iter cleaned up: the slow path in
``ActiveSoarAgent.solve`` persisted *every* non-identity rule the pipeline
produced, even when that rule did not reproduce the task's own training
examples. Those rules then claimed `covers` for tasks they solved INCORRECTLY —
the 168-sub-coverage-rule failure mode in miniature.

The fix gates the slow-path save on ``_rule_matches_examples`` (the same
criterion the fast path already uses before growing `covers`). These tests pin
the guard:

  * a task whose discovered rule does NOT reproduce its training (the
    contradictory easy0003: identical input -> different outputs) must persist
    NO rule;
  * a task that genuinely solves the intended way (constant output) must still
    persist its rule (the guard does not block legitimate generalisation).
"""

import os
import json

from managers.arc_manager import ARCManager
from agent.active_agent import ActiveSoarAgent


def _agent(tmp_path):
    return ActiveSoarAgent(
        semantic_memory_root=str(tmp_path / "sem"),
        procedural_memory_root=str(tmp_path / "proc"),
        max_steps=50,
    )


def _rule_files(root):
    if not os.path.isdir(root):
        return []
    return [f for f in os.listdir(root)
            if f.startswith("rule_") and f.endswith(".json")]


def test_non_reproducing_rule_is_not_saved(tmp_path):
    """easy0003 has contradictory training (same input, different outputs); no
    rule can reproduce it, so the slow path must mint no rule file."""
    path = os.path.join("data", "ARC_easy", "easy0003.json")
    if not os.path.isfile(path):
        return  # dataset not present in this checkout
    manager = ARCManager(data_root="data", semantic_memory_root="semantic_memory")
    agent = _agent(tmp_path)
    task = manager.load_task("ARC_easy/easy0003.json")

    agent.solve(task)

    assert _rule_files(str(tmp_path / "proc")) == [], (
        "a rule that does not reproduce its own training examples was persisted"
    )
    assert agent.last_solve_info.get("rule_saved") is False


def test_reproducing_constant_rule_is_saved(tmp_path):
    """easy000a solves the intended way (all outputs identical -> constant
    output); its rule reproduces training, so the guard must let it through."""
    path = os.path.join("data", "ARC_easy_a", "easy000a.json")
    if not os.path.isfile(path):
        return
    manager = ARCManager(data_root="data", semantic_memory_root="semantic_memory")
    agent = _agent(tmp_path)
    task = manager.load_task("ARC_easy_a/easy000a.json")

    agent.solve(task)

    files = _rule_files(str(tmp_path / "proc"))
    assert len(files) == 1, "the legitimate constant_output rule was not saved"
    saved = json.load(open(os.path.join(str(tmp_path / "proc"), files[0])))
    assert saved["condition"]["type"] == "constant_output"
    assert task.task_hex in saved["covers"]
    assert agent.last_solve_info.get("rule_saved") is True
