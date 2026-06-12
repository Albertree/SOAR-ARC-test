"""
Tests for R1's grid-*resize* object move (BACKLOG_LOOP §3 R1, easy000i): a single
object moved onto a constant-sized output canvas whose dimensions *differ* from
the input (6×6 in → constant 5×5 out) must (a) be recognised by the matcher
value-agnostically (size NOT preserved, output dims + target constant), and
(b) lift into the same `place_object` abstraction as the
target/offset/corner readings (R3) — raising covers, not spawning a fifth family.
"""

from agent import memory
from agent.conditions import match as match_condition
from agent.dsl_expr.render import render_object_at
from agent.dsl_expr.selection import analyze_object_move
from program import anti_unification


class _Grid:
    def __init__(self, raw):
        self.raw = raw


class _Pair:
    def __init__(self, gin, gout):
        self.input_grid = _Grid(gin)
        self.output_grid = _Grid(gout)


def _easy000i_pairs():
    # single pixel on a 6x6 input -> top-left (0,0) of a constant 5x5 output.
    p1 = _Pair(
        [[0, 0, 0, 0, 0, 0],
         [0, 2, 0, 0, 0, 0],
         [0, 0, 0, 0, 0, 0],
         [0, 0, 0, 0, 0, 0],
         [0, 0, 0, 0, 0, 0],
         [0, 0, 0, 0, 0, 0]],
        [[2, 0, 0, 0, 0],
         [0, 0, 0, 0, 0],
         [0, 0, 0, 0, 0],
         [0, 0, 0, 0, 0],
         [0, 0, 0, 0, 0]],
    )
    p2 = _Pair(
        [[0, 0, 0, 0, 0, 0],
         [0, 0, 0, 0, 1, 0],
         [0, 0, 0, 0, 0, 0],
         [0, 0, 0, 0, 0, 0],
         [0, 0, 0, 0, 0, 0],
         [0, 0, 0, 0, 0, 0]],
        [[1, 0, 0, 0, 0],
         [0, 0, 0, 0, 0],
         [0, 0, 0, 0, 0],
         [0, 0, 0, 0, 0],
         [0, 0, 0, 0, 0]],
    )
    return [p1, p2]


def test_analyze_surfaces_constant_output_dims_when_resized():
    move = analyze_object_move(_easy000i_pairs())
    assert move["size_preserved_all"] is False
    assert move["output_dims"] == [5, 5]
    assert move["constant_target"] == [0, 0]


def test_matcher_fires_on_resize_and_size_preserving_siblings_abstain():
    patterns = {"object_move": analyze_object_move(_easy000i_pairs())}
    assert match_condition("object_resize_target", patterns, {"min_evidence": 2})
    # the three size-preserving matchers must NOT claim a resized family
    assert not match_condition("object_constant_target", patterns, {"min_evidence": 2})
    assert not match_condition("object_constant_offset", patterns, {"min_evidence": 2})
    assert not match_condition("object_corner_target", patterns, {"min_evidence": 2})


def test_resize_matcher_abstains_when_size_preserved():
    # same-size move (constant target on a same-size canvas) is NOT a resize.
    p = _Pair(
        [[0, 0, 0], [0, 2, 0], [0, 0, 0]],
        [[2, 0, 0], [0, 0, 0], [0, 0, 0]],
    )
    p2 = _Pair(
        [[0, 0, 0], [0, 0, 1], [0, 0, 0]],
        [[1, 0, 0], [0, 0, 0], [0, 0, 0]],
    )
    patterns = {"object_move": analyze_object_move([p, p2])}
    assert not match_condition("object_resize_target", patterns, {"min_evidence": 2})


def test_render_places_object_on_resized_canvas():
    # test pixel 4 at (4,2) on 6x6 -> (0,0) on a 5x5 canvas (value-agnostic).
    out = render_object_at(5, 5, 0, [(4, 2, 4)], (0, 0))
    assert len(out) == 5 and len(out[0]) == 5
    assert out[0][0] == 4
    assert sum(cell for row in out for cell in row) == 4


def test_resize_reading_lifts_into_place_object(tmp_path):
    root = str(tmp_path)

    def _target_rule():
        return {
            "condition": {"type": "object_constant_target",
                          "params": {"min_evidence": 2}, "min_evidence": 2},
            "action": {"dsl": "place_object_constant", "args": {}},
            "concept": "move_object_to_constant_target",
            "category": "object_move",
        }

    def _resize_rule():
        return {
            "condition": {"type": "object_resize_target",
                          "params": {"min_evidence": 2}, "min_evidence": 2},
            "action": {"dsl": "place_object_resize", "args": {}},
            "concept": "move_object_onto_resized_canvas",
            "category": "object_move",
        }

    # Lift the target family, then introduce a resize move on a new task: it must
    # fold into the same abstraction (re-lift), not spawn a fifth rule.
    memory.save_rule_to_ltm(_target_rule(), "easy000c", root)
    memory.save_rule_to_ltm(_target_rule(), "easy000d", root)
    memory.save_rule_to_ltm(_resize_rule(), "easy000i", root)

    rules = memory.load_all_rules(root)
    assert len(rules) == 1
    abstract = rules[0]
    assert abstract["action"]["dsl"] == "place_object"
    assert "constant_resize" in abstract["action"]["args"]["readings"]
    assert sorted(abstract["covers"]) == ["easy000c", "easy000d", "easy000i"]
    assert abstract["anti_unification_trace"]

    # Idempotent: re-discovering the resize move just absorbs into covers.
    memory.save_rule_to_ltm(_resize_rule(), "easy000i2", root)
    rules2 = memory.load_all_rules(root)
    assert len(rules2) == 1
    assert "easy000i2" in rules2[0]["covers"]


def test_unify_lifts_four_readings():
    def _rule(ctype, dsl):
        return {
            "condition": {"type": ctype,
                          "params": {"min_evidence": 2}, "min_evidence": 2},
            "action": {"dsl": dsl, "args": {}},
            "category": "object_move",
        }

    res = anti_unification.unify([
        _rule("object_constant_target", "place_object_constant"),
        _rule("object_constant_offset", "place_object_relative"),
        _rule("object_corner_target", "place_object_corner"),
        _rule("object_resize_target", "place_object_resize"),
    ])
    assert res is not None and res.is_more_general()
    assert sorted(res.abstract_rule["action"]["args"]["readings"]) == [
        "constant_corner", "constant_offset", "constant_resize", "constant_target",
    ]
