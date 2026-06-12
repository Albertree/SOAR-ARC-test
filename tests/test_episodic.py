"""
Tests for the episodic-memory writer (ARBOR LTM store #3, CLAUDE.md §3.3).

R2 contract: *every* `solve()` invocation — fast-path reuse, slow-path
discovery, or abstain — writes exactly one `episodic_memory/<task>/attempt_NNN/`
folder containing `trace.json`, `metadata.json`, and `grids/step_NNN.json`. An
empty (or frozen) `episodic_memory/` after a run means the writer was bypassed,
which is the INVARIANTS-P4 failure mode.

The writer source (`agent/episodic.py`) was lost at the test31 clean-start node
(only an orphaned `.pyc` survived, and nothing imported it — so the count stood
frozen at 247 stale entries while fresh solves wrote nothing). This file locks
the reconstructed writer *and* its wiring into the solve loop:
  1. `_next_attempt_index` allocates fresh, monotonically-accumulating indices.
  2. `write_attempt` lays down the §3.3 folder shape with faithful content.
  3. `ActiveSoarAgent.solve()` writes exactly one attempt per call, and the
     metadata reflects the *actual* path taken (stored_rule vs pipeline) — not
     the stale "identity" the orphaned data recorded for already-solved tasks.
"""
import os
import sys
import json
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agent import episodic


# ── helpers ────────────────────────────────────────────────────────────
def _load_task(task_path, data_root="data"):
    from managers.arc_manager import ARCManager
    with tempfile.TemporaryDirectory() as tmp:
        return ARCManager(data_root=data_root,
                          semantic_memory_root=tmp).load_task(task_path)


def _minimal_payload():
    trace = {"task": "t", "granularity": "summary", "path": "pipeline",
             "rule_type": "identity", "rule_source": None,
             "steps_taken": 3, "goal_satisfied": True}
    metadata = {"task": "t", "method": "pipeline", "rule_type": "identity",
                "outcome": "prediction-produced", "submission_index": 1,
                "anti_unification_invocations": 0}
    grids = [("test0-input", [[0, 1], [2, 3]]), ("predicted", [[1, 1], [1, 1]])]
    return trace, metadata, grids


# ── 1. _next_attempt_index ─────────────────────────────────────────────
def test_next_index_zero_when_absent():
    with tempfile.TemporaryDirectory() as tmp:
        assert episodic._next_attempt_index(os.path.join(tmp, "nope")) == 0


def test_next_index_accumulates():
    with tempfile.TemporaryDirectory() as tmp:
        os.makedirs(os.path.join(tmp, "attempt_000"))
        os.makedirs(os.path.join(tmp, "attempt_001"))
        os.makedirs(os.path.join(tmp, "not_an_attempt"))
        assert episodic._next_attempt_index(tmp) == 2


# ── 2. write_attempt: §3.3 folder shape ────────────────────────────────
def test_write_attempt_lays_down_schema():
    trace, metadata, grids = _minimal_payload()
    with tempfile.TemporaryDirectory() as tmp:
        path = episodic.write_attempt("t", trace=trace, metadata=metadata,
                                      grids=grids, episodic_root=tmp)
        assert path.endswith(os.path.join("t", "attempt_000"))
        assert os.path.isfile(os.path.join(path, "trace.json"))
        assert os.path.isfile(os.path.join(path, "metadata.json"))
        assert os.path.isfile(os.path.join(path, "grids", "step_000.json"))
        assert os.path.isfile(os.path.join(path, "grids", "step_001.json"))

        with open(os.path.join(path, "metadata.json")) as fh:
            assert json.load(fh)["method"] == "pipeline"
        with open(os.path.join(path, "grids", "step_000.json")) as fh:
            step = json.load(fh)
            assert step["label"] == "test0-input"
            assert step["grid"] == [[0, 1], [2, 3]]


def test_write_attempt_accumulates_fresh_index():
    trace, metadata, grids = _minimal_payload()
    with tempfile.TemporaryDirectory() as tmp:
        p0 = episodic.write_attempt("t", trace=trace, metadata=metadata,
                                    grids=grids, episodic_root=tmp)
        p1 = episodic.write_attempt("t", trace=trace, metadata=metadata,
                                    grids=grids, episodic_root=tmp)
        assert p0.endswith("attempt_000")
        assert p1.endswith("attempt_001")  # second solve does not overwrite


# ── 3. wired into solve(): exactly one attempt, faithful metadata ──────
def test_solve_writes_exactly_one_attempt_with_true_method():
    """A reused stored rule must record method=stored_rule (not the stale
    'identity' the orphaned writer left on already-solved tasks)."""
    from agent.active_agent import ActiveSoarAgent

    cwd = os.getcwd()
    with tempfile.TemporaryDirectory() as ep_root, \
            tempfile.TemporaryDirectory() as pm_root:
        # A concrete constant-output rule that easy0001 reuses on the fast path.
        rule = {
            "id": 1, "concept": "copy_common_output", "category": "constant_output",
            "condition": {"type": "constant_output", "params": {}, "min_evidence": 2},
            "action": {"dsl": "copy_common_output", "args": {}},
            "covers": ["easy0001"], "source_task": "easy0001",
            "anti_unification_trace": None,
            "created_at": "2026-06-12T00:00:00", "times_reused": 0,
        }
        with open(os.path.join(pm_root, "rule_001.json"), "w") as fh:
            json.dump(rule, fh)

        task = _load_task("ARC_easy/easy0001")
        agent = ActiveSoarAgent(procedural_memory_root=pm_root)
        # write_attempt resolves its default `episodic_root` relative to cwd;
        # chdir into a temp root so the test never touches the repo store.
        try:
            os.chdir(ep_root)
            agent.solve(task)
        finally:
            os.chdir(cwd)

        task_dir = os.path.join(ep_root, "episodic_memory", "easy0001")
        attempts = [d for d in os.listdir(task_dir) if d.startswith("attempt_")]
        assert attempts == ["attempt_000"]  # exactly one
        with open(os.path.join(task_dir, "attempt_000", "metadata.json")) as fh:
            md = json.load(fh)
        assert md["method"] == "stored_rule"
        assert md["rule_type"] == "constant_output"
        assert md["outcome"] == "prediction-produced"
