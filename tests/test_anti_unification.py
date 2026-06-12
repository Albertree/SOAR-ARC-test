"""
Tests for R3 anti-unification (BACKLOG_LOOP §3, CLAUDE.md §8):
the two concrete object-move families must lift into one abstract place_object
rule with covers>1 and an anti_unification_trace, and the lift must be stable
(idempotent) across re-saves.
"""

import json
import os

from program import anti_unification
from agent import memory


def _concrete_target_rule():
    return {
        "condition": {"type": "object_constant_target",
                      "params": {"min_evidence": 2}, "min_evidence": 2},
        "action": {"dsl": "place_object_constant", "args": {}},
        "concept": "move_object_to_constant_target",
        "category": "object_move",
    }


def _concrete_offset_rule():
    return {
        "condition": {"type": "object_constant_offset",
                      "params": {"min_evidence": 2}, "min_evidence": 2},
        "action": {"dsl": "place_object_relative", "args": {}},
        "concept": "move_object_by_constant_offset",
        "category": "object_move",
    }


def test_unify_lifts_two_move_families():
    res = anti_unification.unify([_concrete_target_rule(), _concrete_offset_rule()])
    assert res is not None
    assert res.is_more_general()
    ar = res.abstract_rule
    assert ar["action"]["dsl"] == "place_object"
    # the differing reading became a variable ranging over both fillers
    assert ar["action"]["args"]["target"]["reading"].startswith("?v")
    assert sorted(ar["action"]["args"]["readings"]) == ["constant_offset", "constant_target"]
    assert ar["condition"]["type"] == "object_move"


def test_unify_declines_unrelated_rules():
    other = {
        "condition": {"type": "constant_output", "params": {}, "min_evidence": 2},
        "action": {"dsl": "copy_common_output", "args": {}},
        "category": "constant_output",
    }
    assert anti_unification.unify([_concrete_target_rule(), other]) is None


def test_save_consolidates_and_is_stable(tmp_path):
    root = str(tmp_path)
    # Save the two concrete families across separate tasks (as run_learn would).
    memory.save_rule_to_ltm(_concrete_target_rule(), "easy000c", root)
    memory.save_rule_to_ltm(_concrete_target_rule(), "easy000d", root)
    memory.save_rule_to_ltm(_concrete_offset_rule(), "easy000e", root)
    memory.save_rule_to_ltm(_concrete_offset_rule(), "easy000f", root)

    rules = memory.load_all_rules(root)
    # Exactly one rule, the abstract lift, covering all four tasks.
    assert len(rules) == 1
    abstract = rules[0]
    assert abstract["action"]["dsl"] == "place_object"
    assert sorted(abstract["covers"]) == ["easy000c", "easy000d", "easy000e", "easy000f"]
    assert abstract["anti_unification_trace"]
    assert os.path.exists(abstract["anti_unification_trace"])

    # Re-discovering a concrete rule must merge (absorb), not re-spawn a source.
    memory.save_rule_to_ltm(_concrete_target_rule(), "easy000h", root)
    rules2 = memory.load_all_rules(root)
    assert len(rules2) == 1
    assert "easy000h" in rules2[0]["covers"]


def test_abstract_rule_passes_validation():
    res = anti_unification.unify([_concrete_target_rule(), _concrete_offset_rule()])
    entry = dict(res.abstract_rule)
    entry["covers"] = ["easy000c", "easy000e"]
    memory.validate_rule(entry)  # must not raise
