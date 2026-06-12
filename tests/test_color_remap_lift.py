"""
Tests for R3 anti-unification on the **color_remap** family (BACKLOG_LOOP §2.5-3/4,
CLAUDE.md §8).

The recolor family is value-agnostic at predict (the 1:1 colour map is recomputed
from the example pairs), so the literal map carried in a concrete rule's args is
pure self-description. Left un-lifted, every recolor task accretes its own
``covers=1`` rule — the 168-rule failure mode. These tests pin that two (or more)
concrete ``recolor_map`` rules with *different* literal maps lift into one abstract
rule (``color_map`` -> ``?v0``, ``covers`` = union, with an
``anti_unification_trace``), and that the lift is stable across re-saves.
"""

import os

from program import anti_unification
from agent import memory


def _concrete_remap_rule(color_map):
    return {
        "condition": {"type": "color_remap",
                      "params": {"min_evidence": 2}, "min_evidence": 2},
        "action": {"dsl": "recolor_map", "args": {"color_map": dict(color_map)}},
        "concept": "recolor_by_color_map",
        "category": "color_remap",
    }


def test_unify_lifts_two_recolor_maps():
    res = anti_unification.unify([
        _concrete_remap_rule({6: 2}),
        _concrete_remap_rule({7: 5}),
    ])
    assert res is not None
    assert res.is_more_general()
    ar = res.abstract_rule
    assert ar["action"]["dsl"] == "recolor_map"
    # the differing literal map became a variable ranging over both canon forms
    assert ar["action"]["args"]["color_map"].startswith("?v")
    assert sorted(ar["action"]["args"]["color_maps"]) == ["6>2", "7>5"]
    assert ar["condition"]["type"] == "color_remap"


def test_unify_declines_recolor_vs_unrelated():
    other = {
        "condition": {"type": "constant_output", "params": {}, "min_evidence": 2},
        "action": {"dsl": "copy_common_output", "args": {}},
        "category": "constant_output",
    }
    assert anti_unification.unify([_concrete_remap_rule({6: 2}), other]) is None


def test_save_consolidates_recolor_family_and_is_stable(tmp_path):
    root = str(tmp_path)
    # Four real-shaped recolor tasks, each a *different* literal map (as the four
    # ARC-AGI-2 training tasks that surfaced this gap are).
    memory.save_rule_to_ltm(_concrete_remap_rule({3: 4, 1: 5}), "0d3d703e", root)
    memory.save_rule_to_ltm(_concrete_remap_rule({6: 2}), "b1948b0a", root)
    memory.save_rule_to_ltm(_concrete_remap_rule({7: 5}), "c8f0f002", root)
    memory.save_rule_to_ltm(_concrete_remap_rule({8: 5, 5: 8}), "d511f180", root)

    rules = memory.load_all_rules(root)
    # Exactly one rule — the abstract lift — covering all four tasks (no accretion).
    assert len(rules) == 1
    abstract = rules[0]
    assert abstract["action"]["dsl"] == "recolor_map"
    assert abstract["action"]["args"]["color_map"].startswith("?v")
    assert sorted(abstract["covers"]) == [
        "0d3d703e", "b1948b0a", "c8f0f002", "d511f180"]
    assert abstract["anti_unification_trace"]
    assert os.path.exists(abstract["anti_unification_trace"])

    # Re-discovering a concrete recolor map already in range must merge (absorb),
    # not re-spawn a source rule.
    memory.save_rule_to_ltm(_concrete_remap_rule({6: 2}), "dup6to2", root)
    rules2 = memory.load_all_rules(root)
    assert len(rules2) == 1
    assert "dup6to2" in rules2[0]["covers"]

    # A genuinely new recolor map folds into the *same* abstraction (covers up,
    # rule count flat — §2.5-4), not a fresh per-task literal rule.
    memory.save_rule_to_ltm(_concrete_remap_rule({1: 9}), "newmap", root)
    rules3 = memory.load_all_rules(root)
    assert len(rules3) == 1
    assert "newmap" in rules3[0]["covers"]
    assert "1>9" in rules3[0]["action"]["args"]["color_maps"]


def test_abstract_recolor_rule_passes_validation():
    res = anti_unification.unify([
        _concrete_remap_rule({6: 2}),
        _concrete_remap_rule({7: 5}),
    ])
    entry = dict(res.abstract_rule)
    entry["covers"] = ["b1948b0a", "c8f0f002"]
    memory.validate_rule(entry)  # must not raise
