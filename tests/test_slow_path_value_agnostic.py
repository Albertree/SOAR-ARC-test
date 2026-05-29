"""
Tests for the end-to-end *slow path* (pipeline discovery) value-agnosticism
(Slice 1).

Why this file exists — a real blind spot, not redundant coverage:

  * ``test_fast_path_reuse.py`` covers reuse of a *stored* rule
    (``method == "stored_rule"``).
  * ``test_predict_copy_common_output.py`` covers the Generalize/Predict
    operators in isolation, on *synthetic* ``SimpleNamespace`` tasks with a
    hand-filled WM slot — never through ``agent.solve()`` on a real loaded task.

  Nothing exercises the full ``agent.solve()`` *slow path* (empty procedural
  memory -> SOAR pipeline discovers the rule -> ``method == "pipeline"``) on the
  real ARCKG-loaded target tasks. And the run_loop probe gives *false* confidence
  here: in its run order easy000a is solved first and stores the rule, so
  **easy000a2's own pipeline is never run** — it always rides easy000a's stored
  rule (``via=stored(easy000a)``). The only automated proof that easy000a2's
  *own* discovery is value-agnostic (produces its *different* fixed output, with
  no baked-in colour/coordinate) is this test, which forces each task through the
  pipeline from an empty memory independently.

  SLICE_1_LOOP.md §1: easy000a2 exists precisely to catch a hard-coded answer.
  That guard must cover the discovery path, not only reuse.

This adds no production code and touches no signal — it is a verification-hole
closure (observation criterion 1 "작동" + 2 "통일성": the *same* pipeline solves
both targets, no task-specific branch). Each case uses an isolated temp
procedural + episodic memory, so the repo's real stores are never mutated.

pytest is not installed here, so — like every other test in ``tests/`` — the
file is also runnable directly:
    python tests/test_slow_path_value_agnostic.py
"""

import json
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from managers.arc_manager import ARCManager
from agent.active_agent import ActiveSoarAgent
from agent.memory import validate_rule


def _manager():
    return ARCManager(data_root="data", semantic_memory_root="semantic_memory")


def _isolated_agent(workdir):
    """An agent whose procedural memory starts EMPTY (forcing the slow path) and
    whose episodic memory lives entirely inside ``workdir`` — no repo state is
    read or written."""
    pm_root = os.path.join(workdir, "procedural_memory")
    ep_root = os.path.join(workdir, "episodic_memory")
    os.makedirs(pm_root)
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


def _solve_via_pipeline(manager, workdir, task_id):
    """Solve ``task_id`` from an empty procedural memory and return
    (agent, pm_root, predicted_first_grid, task)."""
    agent, pm_root = _isolated_agent(os.path.join(workdir, task_id))
    task = manager.load_task(task_id)
    predicted = _first_grid(agent.solve(task))
    return agent, pm_root, predicted, task


# --- each target solves through its OWN pipeline (not a stored rule) ------

def test_both_targets_solve_via_pipeline_from_empty_memory():
    """With no stored rule, easy000a AND easy000a2 each reach the correct output
    through the SOAR pipeline (``method == "pipeline"``) — independently, so
    easy000a2 cannot ride easy000a's discovery (the probe's blind spot)."""
    manager = _manager()
    workdir = tempfile.mkdtemp()
    try:
        for task_id in ("easy000a", "easy000a2"):
            agent, _, predicted, task = _solve_via_pipeline(manager, workdir, task_id)

            assert agent.last_solve_info["method"] == "pipeline", task_id
            assert agent.last_solve_info["rule_type"] == "copy_common_output", task_id

            expected = _expected_output(task)
            assert expected is not None, task_id
            assert predicted == expected, task_id
    finally:
        import shutil
        shutil.rmtree(workdir, ignore_errors=True)


def test_slow_path_is_value_agnostic_red_vs_green():
    """The same pipeline discovers each task's *different* fixed output — proof
    the discovery path carries no baked-in literal."""
    manager = _manager()
    workdir = tempfile.mkdtemp()
    try:
        _, _, red, _ = _solve_via_pipeline(manager, workdir, "easy000a")
        _, _, green, _ = _solve_via_pipeline(manager, workdir, "easy000a2")
        assert red == _expected_output(manager.load_task("easy000a"))
        assert green == _expected_output(manager.load_task("easy000a2"))
        assert red != green
    finally:
        import shutil
        shutil.rmtree(workdir, ignore_errors=True)


def test_discovered_rules_are_structurally_identical():
    """The rule the pipeline writes for easy000a and the one it writes for
    easy000a2 are identical in ``condition`` and ``action`` (they differ only in
    bookkeeping: covers / source_task / created_at). A structurally identical
    rule that yields different outputs is the rule-level statement of
    value-agnosticism — the recipe is 'copy whatever the common output is', not
    'paint red at (5,5)'."""
    manager = _manager()
    workdir = tempfile.mkdtemp()
    try:
        def _discovered_rule(task_id):
            _, pm_root, _, _ = _solve_via_pipeline(manager, workdir, task_id)
            files = [f for f in os.listdir(pm_root) if f.startswith("rule_")]
            assert len(files) == 1, (task_id, files)
            with open(os.path.join(pm_root, files[0]), encoding="utf-8") as fh:
                return json.load(fh)

        ra = _discovered_rule("easy000a")
        rb = _discovered_rule("easy000a2")

        # Well-formed: a discovered rule must carry a condition (F4) and pass the
        # repo's own validator.
        validate_rule(ra)
        validate_rule(rb)
        assert "condition" in ra and "condition" in rb

        assert ra["condition"] == rb["condition"]
        assert ra["action"] == rb["action"]

        # No baked-in colour literal anywhere in the recipe (condition/action).
        recipe = json.dumps({"c": ra["condition"], "a": ra["action"]})
        for colour in ("\"color\": 2", "\"color\": 3", "(5, 5)", "(5,5)"):
            assert colour not in recipe, colour
    finally:
        import shutil
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
