"""
Tests for the Fast path — reusing a stored rule instead of re-deriving it.

ARBOR's design (arbor.md Fast/Slow path) intends learned rules to be *reused*:
on a new task the agent first tries each stored {condition, action} rule and,
only if none replay, falls back to the full Slow pipeline. That is the whole
point of accumulating knowledge — the single ultimate goal is knowledge that
*grows and gets reused*.

The Fast path had silently regressed to dead code. It read `entry.get("rule")`,
a key from an *older* wrapped schema; the persisted schema is now flat
({condition, action, ...}, docs/RULE_FORMAT.md §3) with no "rule" wrapper, so
every stored rule read back as `{}` and nothing was ever reused (the probe's
"Reused: 0 times"). Two further breakages hid behind it: the flat schema has no
top-level `type` dispatch tag PredictOperator keys on, and the render helpers
read the task off the predictor, which the fast path never seeded.

This file locks the fix:
  1. `applicable_rule` bridges the on-disk schema to an applicable rule, and
     correctly *skips* unknown recipes and unresolved anti-unification variables
     that have **no** render-time resolver.
  2. A stored concrete rule is actually reused end-to-end (method=stored_rule,
     times_reused incremented), and produces the *same* output the Slow path
     would — so reuse is a speed/architecture win, never a correctness change.
  3. An abstract place_object rule whose `target_mode` is an unresolved `?v1`
     hole now **self-applies**: the render path fills the hole by bounded,
     example-grounded selection over the known fillings (§2.5-2b,
     `variable_resolution.resolve_variable`), so the lifted abstraction is reused
     directly. A hole with *no* resolver still falls through to the Slow path
     (the open Q-B3/Q-B4 "invent a new filling" case stays held, not papered
     over) — selection over a known set is not invention.
"""

import json
import os
import shutil
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


# ── helpers ────────────────────────────────────────────────────────────
def _load_task(task_path, data_root="data"):
    from managers.arc_manager import ARCManager
    with tempfile.TemporaryDirectory() as tmp:
        return ARCManager(data_root=data_root,
                          semantic_memory_root=tmp).load_task(task_path)


def _constant_output_entry():
    """A persisted, *concrete* constant-output rule (rule_001's shape)."""
    return {
        "id": 1,
        "concept": "copy_common_output",
        "category": "constant_output",
        "condition": {"type": "constant_output", "params": {}, "min_evidence": 2},
        "action": {"dsl": "copy_common_output", "args": {}},
        "covers": ["easy0001"],
        "source_task": "easy0001",
        "anti_unification_trace": None,
        "created_at": "2026-06-12T00:00:00",
        "times_reused": 0,
    }


def _abstract_place_object_entry():
    """A persisted *abstract* rule with an unresolved AU variable (rule_002)."""
    return {
        "id": 2,
        "concept": "place_displaced_object",
        "category": "single_object_move",
        "condition": {"type": "single_object_move", "params": {"min_evidence": 2}},
        "action": {"dsl": "place_object", "args": {"target_mode": "?v1"}},
        "covers": ["easy000c", "easy000e"],
        "source_task": "easy000e",
        "anti_unification_trace": "episodic_memory/easy000e/anti_unification/au_001.json",
        "created_at": "2026-06-12T00:00:00",
        "times_reused": 0,
    }


def _write_pm(entries):
    """Write entries to a fresh temp procedural_memory dir; return its path."""
    root = tempfile.mkdtemp(prefix="pm_")
    for i, e in enumerate(entries, start=1):
        with open(os.path.join(root, f"rule_{i:03d}.json"), "w") as fh:
            json.dump(e, fh, indent=2)
    return root


# ── 1. applicable_rule: the schema bridge ──────────────────────────────
def test_applicable_rule_stamps_dispatch_type():
    from agent.memory import applicable_rule
    rule = applicable_rule(_constant_output_entry())
    assert rule is not None
    assert rule["type"] == "constant_output"      # bridged from action.dsl
    assert rule["condition"]["type"] == "constant_output"  # original preserved


def test_applicable_rule_skips_unknown_recipe():
    from agent.memory import applicable_rule
    e = _constant_output_entry()
    e["action"]["dsl"] = "no_such_recipe"
    assert applicable_rule(e) is None


def test_applicable_rule_admits_runtime_resolvable_place_object():
    # The abstract place_object rule's `target_mode="?v1"` hole is filled at
    # render time by example-grounded selection, so the rule IS replayable: it
    # passes through with the dispatch type stamped (the fast path then validates
    # it against the examples before reusing it).
    from agent.memory import applicable_rule
    rule = applicable_rule(_abstract_place_object_entry())
    assert rule is not None
    assert rule["type"] == "place_object"
    # The hole is left in place — resolution happens at render time, never by
    # baking a per-task literal into the stored rule.
    assert rule["action"]["args"]["target_mode"] == "?v1"


def test_applicable_rule_skips_unresolved_var_without_resolver():
    # A hole the render path cannot fill (an unknown arg on the place_object
    # recipe) is still non-replayable — it must not be falsely reused.
    from agent.memory import applicable_rule
    e = _abstract_place_object_entry()
    e["action"]["args"] = {"mystery_arg": "?v9"}   # no resolver for this hole
    assert applicable_rule(e) is None


# ── 2. end-to-end reuse of a concrete rule ─────────────────────────────
def test_concrete_rule_is_reused_end_to_end():
    from agent.active_agent import ActiveSoarAgent
    pm = _write_pm([_constant_output_entry()])
    try:
        agent = ActiveSoarAgent(procedural_memory_root=pm)
        task = _load_task("ARC_easy/easy0001")
        predicted = agent.solve(task)
        # Reused via the fast path, not re-derived by the pipeline.
        assert agent.last_solve_info["method"] == "stored_rule"
        assert agent.last_solve_info["rule_type"] == "constant_output"
        # And it produced the correct grid.
        assert predicted[0] == task.test_pairs[0].output_grid.raw
        # times_reused was persisted back to disk.
        with open(os.path.join(pm, "rule_001.json")) as fh:
            assert json.load(fh)["times_reused"] == 1
    finally:
        shutil.rmtree(pm, ignore_errors=True)


def test_reuse_matches_slow_path_output():
    # Reuse must be behaviour-preserving: the fast-path grid equals the grid the
    # Slow pipeline produces from an empty memory.
    from agent.active_agent import ActiveSoarAgent
    task = _load_task("ARC_easy/easy0001")

    empty = tempfile.mkdtemp(prefix="pm_empty_")
    pm = _write_pm([_constant_output_entry()])
    try:
        slow = ActiveSoarAgent(procedural_memory_root=empty).solve(task)
        assert slow is not None
        agent = ActiveSoarAgent(procedural_memory_root=pm)
        fast = agent.solve(task)
        assert agent.last_solve_info["method"] == "stored_rule"
        assert fast[0] == slow[0]
    finally:
        shutil.rmtree(empty, ignore_errors=True)
        shutil.rmtree(pm, ignore_errors=True)


# ── 3. abstract rule self-applies via variable resolution ──────────────
def test_abstract_rule_self_applies_via_resolution():
    # easy000c is a fixed-target mover. With only the *abstract* (?v1) rule in
    # memory, the fast path now reuses it: the render path fills target_mode by
    # example-grounded selection ("fixed" reproduces easy000c's examples) and
    # predicts the test correctly. This is the lifted abstraction self-applying —
    # R5 reuse generalizing across the {fixed,displacement,corner} fillings via a
    # single covers>1 rule, not a per-task literal.
    from agent.active_agent import ActiveSoarAgent
    pm = _write_pm([_abstract_place_object_entry()])
    try:
        agent = ActiveSoarAgent(procedural_memory_root=pm)
        task = _load_task("ARC_easy_a/easy000c")
        predicted = agent.solve(task)
        assert agent.last_solve_info["method"] == "stored_rule"   # reused
        assert agent.last_solve_info["rule_type"] == "place_object"
        assert predicted[0] == task.test_pairs[0].output_grid.raw
        # The reuse was recorded on disk.
        with open(os.path.join(pm, "rule_001.json")) as fh:
            assert json.load(fh)["times_reused"] == 1
    finally:
        shutil.rmtree(pm, ignore_errors=True)


def test_abstract_rule_not_reused_on_nonmatching_task():
    # The example-reproduction guard prevents false reuse: easy0005 supports none
    # of the place_object fillings (no single moved object reproducing its
    # outputs), so the resolver returns None, the render yields None, and the fast
    # path declines — falling through to the Slow path rather than forcing a wrong
    # placement. (Some constant-output tasks, e.g. easy0001, genuinely *are* a
    # single object on a fixed cell and are legitimately reused; the guard's job
    # is only to refuse a filling no example supports.)
    from agent.active_agent import ActiveSoarAgent
    pm = _write_pm([_abstract_place_object_entry()])
    try:
        agent = ActiveSoarAgent(procedural_memory_root=pm)
        task = _load_task("ARC_easy/easy0005")
        predicted = agent.solve(task)
        assert agent.last_solve_info["method"] == "pipeline"   # not reused
        assert predicted is not None
    finally:
        shutil.rmtree(pm, ignore_errors=True)
