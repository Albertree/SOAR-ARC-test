"""
Tests for R1's constant-corner object move (BACKLOG_LOOP §3 R1, easy000g):
a single object moved flush into a shared *grid corner* across canvases of
different sizes must (a) be recognised by the matcher value-agnostically, and
(b) lift into the same `place_object` abstraction as the target/offset readings
(R3) — raising covers, not spawning a fourth family.
"""

from agent import memory
from agent.conditions import match as match_condition
from agent.dsl_expr.selection import (
    analyze_object_move,
    corner_anchor,
    corners_matching,
)
from program import anti_unification


class _Grid:
    def __init__(self, raw):
        self.raw = raw


class _Pair:
    def __init__(self, gin, gout):
        self.input_grid = _Grid(gin)
        self.output_grid = _Grid(gout)


def _easy000g_pairs():
    # object -> bottom-right corner, on two differently-sized canvases.
    p1 = _Pair(
        [[0, 0, 0, 0], [0, 2, 0, 0], [0, 0, 0, 0], [0, 0, 0, 0]],
        [[0, 0, 0, 0], [0, 0, 0, 0], [0, 0, 0, 0], [0, 0, 0, 2]],
    )
    p2 = _Pair(
        [[0, 0, 0, 0, 0], [0, 0, 0, 0, 1], [0, 0, 0, 0, 0]],
        [[0, 0, 0, 0, 0], [0, 0, 0, 0, 0], [0, 0, 0, 0, 1]],
    )
    return [p1, p2]


def test_corner_anchor_is_grid_relative():
    assert corner_anchor("bottom_right", 4, 4) == (3, 3)
    assert corner_anchor("bottom_right", 3, 5) == (2, 4)
    assert corner_anchor("top_left", 6, 6) == (0, 0)
    # object extent: a 2x3 object flush bottom-right of a 5x5 grid
    assert corner_anchor("bottom_right", 5, 5, 2, 3) == (3, 2)


def test_corners_matching_single():
    assert corners_matching([3, 3], 4, 4, 1, 1) == ["bottom_right"]
    assert corners_matching([0, 0], 4, 4, 1, 1) == ["top_left"]


def test_analyze_detects_constant_corner_not_target_or_offset():
    move = analyze_object_move(_easy000g_pairs())
    assert move["constant_corner"] == "bottom_right"
    # neither absolute target nor offset is constant across the two pairs
    assert move["constant_target"] is None
    assert move["constant_offset"] is None


def test_matcher_fires_on_corner_and_abstains_otherwise():
    patterns = {"object_move": analyze_object_move(_easy000g_pairs())}
    assert match_condition("object_corner_target", patterns, {"min_evidence": 2})
    # the target/offset matchers must NOT claim this family
    assert not match_condition("object_constant_target", patterns, {"min_evidence": 2})
    assert not match_condition("object_constant_offset", patterns, {"min_evidence": 2})


def test_corner_reading_lifts_into_place_object(tmp_path):
    root = str(tmp_path)

    def _corner_rule():
        return {
            "condition": {"type": "object_corner_target",
                          "params": {"min_evidence": 2}, "min_evidence": 2},
            "action": {"dsl": "place_object_corner", "args": {"corner": "bottom_right"}},
            "concept": "move_object_to_grid_corner",
            "category": "object_move",
        }

    def _target_rule():
        return {
            "condition": {"type": "object_constant_target",
                          "params": {"min_evidence": 2}, "min_evidence": 2},
            "action": {"dsl": "place_object_constant", "args": {}},
            "concept": "move_object_to_constant_target",
            "category": "object_move",
        }

    # First lift the target family, then introduce a corner move on a new task:
    # it must fold into the same abstraction (re-lift), not spawn a fourth rule.
    memory.save_rule_to_ltm(_target_rule(), "easy000c", root)
    memory.save_rule_to_ltm(_target_rule(), "easy000d", root)
    memory.save_rule_to_ltm(_corner_rule(), "easy000g", root)

    rules = memory.load_all_rules(root)
    assert len(rules) == 1
    abstract = rules[0]
    assert abstract["action"]["dsl"] == "place_object"
    assert "constant_corner" in abstract["action"]["args"]["readings"]
    assert sorted(abstract["covers"]) == ["easy000c", "easy000d", "easy000g"]
    assert abstract["anti_unification_trace"]

    # Idempotent: re-discovering the corner move just absorbs into covers.
    memory.save_rule_to_ltm(_corner_rule(), "easy000g2", root)
    rules2 = memory.load_all_rules(root)
    assert len(rules2) == 1
    assert "easy000g2" in rules2[0]["covers"]


def test_unify_lifts_three_readings():
    target = {
        "condition": {"type": "object_constant_target",
                      "params": {"min_evidence": 2}, "min_evidence": 2},
        "action": {"dsl": "place_object_constant", "args": {}},
        "category": "object_move",
    }
    offset = {
        "condition": {"type": "object_constant_offset",
                      "params": {"min_evidence": 2}, "min_evidence": 2},
        "action": {"dsl": "place_object_relative", "args": {}},
        "category": "object_move",
    }
    corner = {
        "condition": {"type": "object_corner_target",
                      "params": {"min_evidence": 2}, "min_evidence": 2},
        "action": {"dsl": "place_object_corner", "args": {}},
        "category": "object_move",
    }
    res = anti_unification.unify([target, offset, corner])
    assert res is not None and res.is_more_general()
    assert sorted(res.abstract_rule["action"]["args"]["readings"]) == [
        "constant_corner", "constant_offset", "constant_target",
    ]
