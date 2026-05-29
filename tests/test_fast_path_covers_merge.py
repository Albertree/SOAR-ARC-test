"""
Regression test for the fast-path coverage-merge gap (CLAUDE.md §3.2).

``covers`` is defined as the set of tasks a rule has *successfully handled*.
The slow-path equivalence branch of ``save_rule_to_ltm`` appends a task to
``covers`` whenever the same rule is re-derived. The fast path, however, used to
call ``increment_reuse_count(entry)`` which only bumped ``times_reused`` — so a
task solved *purely* by reusing a stored rule never entered that rule's
``covers``, and therefore never entered P1 (``solved_tasks / total_rules``), the
headline coverage metric. P1 then stayed accurate only by accident of which path
(slow vs fast) happened to fire first for a given task.

This test sets up a rule whose ``covers`` lists only ``easy000a`` and then solves
``easy000a2`` via the fast path. Before the fix, ``easy000a2`` is missing from
``covers`` (the bug). After the fix, reuse appends it — coverage accounting is
the same whether a task was discovered or reused.

Like the rest of ``tests/``, runnable directly:
    python tests/test_fast_path_covers_merge.py
Each test uses an isolated temp procedural + episodic memory so the repo's real
rule files are never mutated.
"""

import json
import os
import shutil
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from managers.arc_manager import ARCManager
from agent.active_agent import ActiveSoarAgent
from agent.memory import increment_reuse_count


# A copy_common_output rule whose covers initially lists ONLY easy000a — the
# state the repo would be in if easy000a had been discovered (slow path) and
# easy000a2 had only ever been reused (fast path).
RULE_COVERS_ONE = {
    "id": 1,
    "concept": "copy_common_example_output",
    "category": "other",
    "condition": {"type": "copy_common_output_applies", "params": {}, "min_evidence": 1},
    "action": {"dsl": "make_grid", "args": {}},
    "rule": {"type": "copy_common_output", "confidence": 1.0},
    "covers": ["easy000a"],
    "source_task": "easy000a",
    "anti_unification_trace": None,
    "created_at": "2026-01-01T00:00:00",
    "times_reused": 0,
}


def _manager():
    return ARCManager(data_root="data", semantic_memory_root="semantic_memory")


def _make_pm_root(workdir):
    root = os.path.join(workdir, "procedural_memory")
    os.makedirs(root)
    with open(os.path.join(root, "rule_001.json"), "w", encoding="utf-8") as fh:
        json.dump(RULE_COVERS_ONE, fh)
    return root


def _isolated_agent(workdir):
    pm_root = _make_pm_root(workdir)
    ep_root = os.path.join(workdir, "episodic_memory")
    os.makedirs(ep_root)
    agent = ActiveSoarAgent(procedural_memory_root=pm_root,
                            episodic_memory_root=ep_root)
    return agent, pm_root


def _stored_rule(pm_root):
    with open(os.path.join(pm_root, "rule_001.json"), encoding="utf-8") as fh:
        return json.load(fh)


# --- the fix: fast-path reuse merges the task into covers ------------------

def test_reuse_appends_task_to_covers():
    """Solving easy000a2 via the stored rule (whose covers lists only easy000a)
    must add easy000a2 to covers — reuse is a handled task (CLAUDE.md §3.2)."""
    manager = _manager()
    workdir = tempfile.mkdtemp()
    try:
        agent, pm_root = _isolated_agent(os.path.join(workdir, "agent"))

        agent.solve(manager.load_task("easy000a2"))

        assert agent.last_solve_info["method"] == "stored_rule"
        stored = _stored_rule(pm_root)
        assert "easy000a2" in stored["covers"], stored["covers"]
        assert "easy000a" in stored["covers"], stored["covers"]
        # still exactly one rule file — knowledge reused, not re-discovered
        rule_files = [f for f in os.listdir(pm_root) if f.startswith("rule_")]
        assert len(rule_files) == 1
    finally:
        shutil.rmtree(workdir, ignore_errors=True)


def test_reuse_does_not_duplicate_existing_cover():
    """Re-solving easy000a (already in covers) must not duplicate it, and the
    counter still advances once per reuse."""
    manager = _manager()
    workdir = tempfile.mkdtemp()
    try:
        agent, pm_root = _isolated_agent(os.path.join(workdir, "agent"))

        agent.solve(manager.load_task("easy000a"))
        agent.solve(manager.load_task("easy000a"))

        stored = _stored_rule(pm_root)
        assert stored["covers"].count("easy000a") == 1, stored["covers"]
        assert stored["times_reused"] == 2, stored["times_reused"]
    finally:
        shutil.rmtree(workdir, ignore_errors=True)


# --- the helper's optional-arg contract stays backward compatible ----------

def test_increment_without_task_hex_only_bumps_counter():
    """increment_reuse_count(entry) with no task_hex must keep the old contract:
    bump times_reused, leave covers untouched (no accidental coverage growth)."""
    workdir = tempfile.mkdtemp()
    try:
        pm_root = _make_pm_root(workdir)
        path = os.path.join(pm_root, "rule_001.json")
        entry = dict(RULE_COVERS_ONE)
        entry["_path"] = path

        increment_reuse_count(entry)

        with open(path, encoding="utf-8") as fh:
            stored = json.load(fh)
        assert stored["times_reused"] == 1
        assert stored["covers"] == ["easy000a"], stored["covers"]
    finally:
        shutil.rmtree(workdir, ignore_errors=True)


if __name__ == "__main__":
    funcs = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    failed = 0
    for fn in funcs:
        try:
            fn()
            print(f"PASS {fn.__name__}")
        except AssertionError as e:
            failed += 1
            print(f"FAIL {fn.__name__}: {e}")
        except Exception as e:  # noqa: BLE001 — surface unexpected errors too
            failed += 1
            print(f"ERROR {fn.__name__}: {type(e).__name__}: {e}")
    print(f"\n{len(funcs) - failed}/{len(funcs)} passed")
    sys.exit(1 if failed else 0)
