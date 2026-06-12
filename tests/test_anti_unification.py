"""
Tests for R3 — anti-unification (BACKLOG_LOOP.md R3, docs/ANTI_UNIFICATION.md).

Three layers:
  * unify unit   — the leaf-case algorithm: skeleton check, field-wise lifting,
                   covers union, min_evidence max, trace emission, the
                   is_more_general / NoCommonSkeleton contracts.
  * save_rule    — the single call site (CLAUDE.md §8) lifts two concrete
                   `place_object` fillings (fixed cell vs constant displacement)
                   that share a skeleton into ONE covers>1 abstraction carrying a
                   variable target_mode + an anti_unification_trace.
  * convergence  — once the abstraction exists, a later concrete instance it
                   subsumes is folded into covers, NOT re-lifted (repeated runs
                   stay at one rule — the §2.5-3 "not a per-task literal" contract
                   holding across passes).
"""

import json
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from program.anti_unification import (  # noqa: E402
    NoCommonSkeleton, UnifyResult, unify,
)
from agent import memory  # noqa: E402


# ── fixtures ──────────────────────────────────────────────────────────
def _fixed(covers=("easy000c", "easy000d"), src="easy000c"):
    return {
        "id": 2, "concept": "place_moved_object", "category": "single_object_move",
        "condition": {"type": "single_object_move", "params": {"min_evidence": 2}},
        "action": {"dsl": "place_object", "args": {}},
        "covers": list(covers), "source_task": src,
        "anti_unification_trace": None, "created_at": "2026-06-12T00:00:00",
        "times_reused": 0,
    }


def _displacement(covers=("easy000e",), src="easy000e"):
    return {
        "id": 3, "concept": "place_displaced_object", "category": "single_object_move",
        "condition": {"type": "single_object_move", "params": {"min_evidence": 2}},
        "action": {"dsl": "place_object", "args": {"target_mode": "displacement"}},
        "covers": list(covers), "source_task": src,
        "anti_unification_trace": None, "created_at": "2026-06-12T00:00:00",
        "times_reused": 0,
    }


# ── unify unit ────────────────────────────────────────────────────────
def test_unify_lifts_only_the_differing_arg():
    with tempfile.TemporaryDirectory() as ep:
        res = unify([_fixed(), _displacement()], episodic_memory_root=ep)
    assert isinstance(res, UnifyResult)
    assert res.is_more_general()
    # only target_mode differs (fixed lacks it, displacement has it) → one var.
    assert res.substitutions == {"action.args.target_mode": "?v1"}
    assert res.abstract_rule["action"]["args"]["target_mode"].startswith("?")
    # skeleton fields copied through unchanged.
    assert res.abstract_rule["condition"]["type"] == "single_object_move"
    assert res.abstract_rule["action"]["dsl"] == "place_object"


def test_unify_unions_covers_preserving_order():
    with tempfile.TemporaryDirectory() as ep:
        res = unify([_fixed(covers=("easy000c", "easy000d")),
                     _displacement(covers=("easy000e",))],
                    episodic_memory_root=ep)
    assert res.abstract_rule["covers"] == ["easy000c", "easy000d", "easy000e"]


def test_unify_keeps_max_min_evidence_and_never_lifts_it():
    a = _fixed()
    b = _displacement()
    b["condition"]["params"]["min_evidence"] = 5
    with tempfile.TemporaryDirectory() as ep:
        res = unify([a, b], episodic_memory_root=ep)
    assert res.abstract_rule["condition"]["params"]["min_evidence"] == 5
    assert "condition.params.min_evidence" not in res.substitutions


def test_unify_writes_trace_under_episodic_path():
    with tempfile.TemporaryDirectory() as ep:
        res = unify([_fixed(), _displacement()], episodic_memory_root=ep)
        assert res.trace_path is not None
        # forward-slashed, source-task scoped, matches RULE_FORMAT V5 shape.
        assert res.trace_path.endswith(".json")
        assert "/easy000e/anti_unification/" in res.trace_path
        on_disk = os.path.join(ep, "easy000e", "anti_unification", "au_001.json")
        assert os.path.exists(on_disk)
        trace = json.load(open(on_disk, encoding="utf-8"))
        assert trace["skeleton"] == {
            "condition_type": "single_object_move", "action_dsl": "place_object"}
        assert trace["var_count"] == 1


def test_unify_identical_rules_is_not_more_general_and_writes_no_trace():
    with tempfile.TemporaryDirectory() as ep:
        res = unify([_fixed(), _fixed(covers=("easy000h",), src="easy000h")],
                    episodic_memory_root=ep)
    assert not res.is_more_general()
    assert res.substitutions == {}
    assert res.trace_path is None


def test_unify_raises_on_skeleton_mismatch():
    a = _fixed()
    b = _displacement()
    b["action"]["dsl"] = "copy_common_output"   # different primitive
    with tempfile.TemporaryDirectory() as ep:
        try:
            unify([a, b], episodic_memory_root=ep)
            assert False, "expected NoCommonSkeleton"
        except NoCommonSkeleton:
            pass


def test_unify_raises_on_single_rule():
    try:
        unify([_fixed()])
        assert False, "expected NoCommonSkeleton"
    except NoCommonSkeleton:
        pass


# ── save_rule integration (the single AU call site) ───────────────────
def _write(root, rule):
    with open(os.path.join(root, f"rule_{rule['id']:03d}.json"), "w",
              encoding="utf-8") as fh:
        json.dump(rule, fh, indent=2)


def _load_all(root):
    out = []
    for f in sorted(os.listdir(root)):
        if f.startswith("rule_") and f.endswith(".json"):
            out.append(json.load(open(os.path.join(root, f), encoding="utf-8")))
    return out


def test_save_rule_lifts_two_fillings_into_one_abstract(tmp_path, monkeypatch):
    pm = tmp_path / "pm"
    pm.mkdir()
    monkeypatch.chdir(tmp_path)          # episodic trace writes under cwd
    # An existing concrete fixed-target rule on disk.
    _write(str(pm), _fixed())
    # Saving a *displacement* filling (same skeleton, differing arg) lifts.
    disp_rule = {
        "type": "place_object", "concept": "place_displaced_object",
        "category": "single_object_move",
        "condition": {"type": "single_object_move", "params": {"min_evidence": 2}},
        "action": {"dsl": "place_object", "args": {"target_mode": "displacement"}},
    }
    memory.save_rule(disp_rule, "easy000e", procedural_memory_root=str(pm))

    rules = _load_all(str(pm))
    assert len(rules) == 1, "the two fillings collapse into ONE abstraction"
    abs_rule = rules[0]
    assert abs_rule["anti_unification_trace"], "abstraction records its trace"
    assert abs_rule["action"]["args"]["target_mode"].startswith("?")
    assert set(abs_rule["covers"]) == {"easy000c", "easy000d", "easy000e"}


def test_save_rule_subsumes_instead_of_relifting(tmp_path, monkeypatch):
    pm = tmp_path / "pm"
    pm.mkdir()
    monkeypatch.chdir(tmp_path)
    _write(str(pm), _fixed())
    disp_rule = {
        "type": "place_object", "category": "single_object_move",
        "condition": {"type": "single_object_move", "params": {"min_evidence": 2}},
        "action": {"dsl": "place_object", "args": {"target_mode": "displacement"}},
    }
    memory.save_rule(disp_rule, "easy000e", procedural_memory_root=str(pm))
    # A second, *new* concrete instance of the same family must fold into the
    # abstraction's covers — not spawn a rule, not re-lift (convergence).
    fixed_rule = {
        "type": "place_object", "category": "single_object_move",
        "condition": {"type": "single_object_move", "params": {"min_evidence": 2}},
        "action": {"dsl": "place_object", "args": {}},
    }
    memory.save_rule(fixed_rule, "easy000h", procedural_memory_root=str(pm))

    rules = _load_all(str(pm))
    assert len(rules) == 1, "still ONE rule after a subsumed instance"
    assert "easy000h" in rules[0]["covers"]
    # trace count under episodic must not grow on the subsumed save.
    traces = []
    ep = tmp_path / "episodic_memory"
    if ep.exists():
        for r, _, fs in os.walk(str(ep)):
            traces += [f for f in fs if f.startswith("au_")]
    assert len(traces) == 1, "subsumption does not write a second trace"
