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

pytest is not installed here, so — like every other test in ``tests/`` — the
file is also runnable directly (no pytest fixtures / marks):
    python tests/test_fast_path_reuse.py
Each helper builds an *isolated* temp procedural_memory (so the repo's real
rule files are never mutated by the times_reused counter) and an isolated temp
episodic_memory (so the run does not litter the repo's episodic store).
"""

import json
import os
import shutil
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from managers.arc_manager import ARCManager
from agent.active_agent import ActiveSoarAgent


COPY_COMMON_RULE = {
    "id": 1,
    "concept": "copy_common_example_output",
    "category": "other",
    "condition": {"type": "copy_common_output_applies", "params": {}, "min_evidence": 1},
    "action": {"dsl": "make_grid", "args": {}},
    "rule": {"type": "copy_common_output", "confidence": 1.0},
    "covers": ["easy000a", "easy000a2"],
    "source_task": "easy000a",
    "anti_unification_trace": None,
    "created_at": "2026-01-01T00:00:00",
    "times_reused": 0,
}


def _manager():
    return ARCManager(data_root="data", semantic_memory_root="semantic_memory")


def _make_pm_root(workdir):
    """An isolated procedural_memory holding only the copy_common_output rule, so
    the test never mutates the repo's real rule files (times_reused is a counter
    written on reuse)."""
    root = os.path.join(workdir, "procedural_memory")
    os.makedirs(root)
    with open(os.path.join(root, "rule_001.json"), "w", encoding="utf-8") as fh:
        json.dump(COPY_COMMON_RULE, fh)
    return root


def _isolated_agent(workdir):
    """An agent whose procedural + episodic memory live entirely inside
    ``workdir`` — no repo state is read or written."""
    pm_root = _make_pm_root(workdir)
    ep_root = os.path.join(workdir, "episodic_memory")
    os.makedirs(ep_root)
    agent = ActiveSoarAgent(procedural_memory_root=pm_root,
                            episodic_memory_root=ep_root)
    return agent, pm_root


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


# --- both targets solve via the stored rule (not the pipeline) ------------

def test_fast_path_reuses_stored_rule():
    """Both easy000a and easy000a2 solve via the stored rule (not the
    pipeline), with the correct value-agnostic output."""
    manager = _manager()
    workdir = tempfile.mkdtemp()
    try:
        for task_id in ("easy000a", "easy000a2"):
            agent, _ = _isolated_agent(os.path.join(workdir, task_id))
            task = manager.load_task(task_id)

            predicted = agent.solve(task)

            assert agent.last_solve_info["method"] == "stored_rule", task_id
            assert agent.last_solve_info["rule_type"] == "copy_common_output", task_id

            expected = _expected_output(task)
            assert expected is not None, task_id
            assert _first_grid(predicted) == expected, task_id
    finally:
        shutil.rmtree(workdir, ignore_errors=True)


def test_reuse_is_value_agnostic():
    """The single stored rule yields *different* correct outputs for the two
    tasks — proof the reuse path carries no baked-in literal."""
    manager = _manager()
    workdir = tempfile.mkdtemp()
    try:
        agent, _ = _isolated_agent(os.path.join(workdir, "agent"))

        a = _first_grid(agent.solve(manager.load_task("easy000a")))
        a2 = _first_grid(agent.solve(manager.load_task("easy000a2")))

        assert a == _expected_output(manager.load_task("easy000a"))
        assert a2 == _expected_output(manager.load_task("easy000a2"))
        assert a != a2
    finally:
        shutil.rmtree(workdir, ignore_errors=True)


def test_reuse_does_not_create_new_rule():
    """Reuse must not re-discover: still exactly one rule file, and its
    times_reused incremented once per solve."""
    manager = _manager()
    workdir = tempfile.mkdtemp()
    try:
        agent, pm_root = _isolated_agent(os.path.join(workdir, "agent"))
        agent.solve(manager.load_task("easy000a"))
        agent.solve(manager.load_task("easy000a2"))

        rule_files = [f for f in os.listdir(pm_root) if f.startswith("rule_")]
        assert len(rule_files) == 1

        with open(os.path.join(pm_root, rule_files[0]), encoding="utf-8") as fh:
            stored = json.load(fh)
        assert stored["times_reused"] == 2
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
