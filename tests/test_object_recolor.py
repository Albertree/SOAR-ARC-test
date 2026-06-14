"""
Tests for R1's object-level *recolour* capability (BACKLOG_LOOP.md R1, §2.5-2b):

  * the colour-source expression fitter (agent/dsl_expr.recolor.fit_color_source),
    fitted from the example comparison — never a literal colour,
  * the `object_recolor` condition matcher,
  * end-to-end: ExtractPattern -> Generalize -> Predict recolours one selected
    object in place to another object's colour, with ONE value-agnostic rule
    built only from make_grid + coloring,
  * that two recolour tasks whose (selector, source) diverge anti-unify into one
    covers=2 rule with a trace (R3), via the sanctioned save_rule path.
"""

import json
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agent.dsl_expr import (
    objects_of, fit_color_source, color_source, fit_selector,
)
from agent.conditions import match as match_condition
from agent.active_operators import (
    ExtractPatternOperator,
    GeneralizeOperator,
    PredictOperator,
)


# --- colour-source fitter --------------------------------------------------

def _objs(grid):
    return objects_of(grid)


def test_fit_color_source_largest():
    # two objects: a 4-cell colour-3 block and a 1-cell colour-4 dot; the new
    # colour (3) is the largest object's colour -> source = largest.
    g = [[3, 3, 0], [3, 3, 0], [0, 0, 4]]
    objs = _objs(g)
    assert fit_color_source([{"objects": objs, "color": 3}]) == {"kind": "largest"}


def test_fit_color_source_smallest():
    g = [[3, 3, 0], [3, 3, 0], [0, 0, 4]]
    objs = _objs(g)
    assert fit_color_source([{"objects": objs, "color": 4}]) == {"kind": "smallest"}


def test_fit_color_source_declines_when_no_object_has_color():
    g = [[3, 3, 0], [3, 3, 0], [0, 0, 4]]
    objs = _objs(g)
    # colour 9 belongs to no object -> no selector fits -> decline.
    assert fit_color_source([{"objects": objs, "color": 9}]) is None


def test_color_source_resolves_and_declines():
    g = [[3, 3, 0], [3, 3, 0], [0, 0, 4]]
    objs = _objs(g)
    assert color_source({"kind": "largest"}, objs) == 3
    assert color_source({"kind": "smallest"}, objs) == 4
    assert color_source(None, objs) is None


# --- matcher ---------------------------------------------------------------

def _rec(n=2, selector=None, source=None, **overrides):
    pair = {"recolor_ok": True, "grid_size_preserved": True}
    pair.update(overrides)
    return {"object_recolor": {
        "evidence_count": n,
        "pairs": [dict(pair) for _ in range(n)],
        "selector": selector if selector is not None else {"kind": "smallest"},
        "source": source if source is not None else {"kind": "largest"},
    }}


def test_matcher_fires():
    assert match_condition("object_recolor", _rec(2)) is True


def test_matcher_needs_min_evidence():
    assert match_condition("object_recolor", _rec(1)) is False


def test_matcher_declines_without_selector():
    p = _rec(2)
    p["object_recolor"]["selector"] = None
    assert match_condition("object_recolor", p) is False


def test_matcher_declines_without_source():
    p = _rec(2)
    p["object_recolor"]["source"] = None
    assert match_condition("object_recolor", p) is False


def test_matcher_declines_on_resize():
    p = _rec(2)
    p["object_recolor"]["pairs"][1]["grid_size_preserved"] = False
    assert match_condition("object_recolor", p) is False


# --- identify --------------------------------------------------------------

def test_identify_recolor_picks_changed_object():
    gin = [[3, 3, 0], [3, 3, 0], [0, 0, 4]]
    gout = [[3, 3, 0], [3, 3, 0], [0, 0, 3]]  # the 1-cell dot 4 -> 3
    idx, new_color = ExtractPatternOperator._identify_recolor(
        objects_of(gin), objects_of(gout)
    )
    objs = objects_of(gin)
    assert objs[idx]["size"] == 1  # the small dot was recoloured
    assert new_color == 3


def test_identify_recolor_declines_on_move():
    # cells moved, not recoloured -> no same-cell twin -> decline.
    gin = [[2, 0, 0], [0, 0, 0], [0, 0, 0]]
    gout = [[0, 0, 0], [0, 0, 0], [0, 0, 2]]
    assert ExtractPatternOperator._identify_recolor(
        objects_of(gin), objects_of(gout)
    ) == (None, None)


# --- end-to-end pipeline ---------------------------------------------------

class _Grid:
    def __init__(self, raw):
        self.raw = raw
        self.height = len(raw)
        self.width = len(raw[0]) if raw else 0
        self.node_id = id(self)


class _Pair:
    def __init__(self, inp, out):
        self.input_grid = _Grid(inp)
        self.output_grid = _Grid(out) if out is not None else None


class _Task:
    def __init__(self, train, test, name="rec"):
        self.task_hex = name
        self.example_pairs = [_Pair(i, o) for i, o in train]
        self.test_pairs = [_Pair(i, o) for i, o in test]


class _WM:
    def __init__(self, task):
        self.task = task
        self.s1 = {}


# smaller object recoloured to the larger object's colour (selector=smallest,
# source=largest). Mirror of TO_SMALLEST below.
TO_LARGEST = {
    "train": [
        ([[3, 3, 0, 0, 0], [3, 3, 0, 0, 0], [0]*5, [0]*5, [0, 0, 0, 4, 4]],
         [[3, 3, 0, 0, 0], [3, 3, 0, 0, 0], [0]*5, [0]*5, [0, 0, 0, 3, 3]]),
        ([[7, 7, 7, 0], [0, 0, 0, 0], [0, 0, 0, 0], [0, 2, 0, 0]],
         [[7, 7, 7, 0], [0, 0, 0, 0], [0, 0, 0, 0], [0, 7, 0, 0]]),
    ],
    "test": [
        ([[5, 5, 0, 0, 0], [5, 5, 0, 0, 0], [0]*5, [0]*5, [0, 0, 0, 0, 8]],
         [[5, 5, 0, 0, 0], [5, 5, 0, 0, 0], [0]*5, [0]*5, [0, 0, 0, 0, 5]]),
    ],
}

# larger object recoloured to the smaller object's colour (selector=largest,
# source=smallest).
TO_SMALLEST = {
    "train": [
        ([[3, 3, 0, 0, 0], [3, 3, 0, 0, 0], [0]*5, [0]*5, [0, 0, 0, 0, 6]],
         [[6, 6, 0, 0, 0], [6, 6, 0, 0, 0], [0]*5, [0]*5, [0, 0, 0, 0, 6]]),
        ([[7, 7, 7, 0], [0, 0, 0, 0], [0, 0, 0, 0], [0, 2, 0, 0]],
         [[2, 2, 2, 0], [0, 0, 0, 0], [0, 0, 0, 0], [0, 2, 0, 0]]),
    ],
    "test": [
        ([[5, 5, 0, 0, 0], [5, 5, 0, 0, 0], [0]*5, [0]*5, [0, 0, 0, 0, 9]],
         [[9, 9, 0, 0, 0], [9, 9, 0, 0, 0], [0]*5, [0]*5, [0, 0, 0, 0, 9]]),
    ],
}


def _solve(spec, name="rec"):
    task = _Task(spec["train"], spec["test"], name=name)
    wm = _WM(task)
    ExtractPatternOperator().effect(wm)
    GeneralizeOperator().effect(wm)
    PredictOperator().effect(wm)
    return wm, task


def _check_solved(spec, name, exp_selector, exp_source):
    wm, task = _solve(spec, name)
    rule = wm.s1["active-rules"][0]
    assert rule["type"] == "object_recolor", name
    assert "condition" in rule and "action" in rule
    args = rule["action"]["args"]
    assert args.get("selector") == exp_selector, (name, args)
    assert args.get("source") == exp_source, (name, args)
    pred = wm.s1["predictions"]["test_0"]
    assert pred == task.test_pairs[0].output_grid.raw, name
    return wm


def test_pipeline_solves_to_largest():
    _check_solved(TO_LARGEST, "to_largest",
                  {"kind": "smallest"}, {"kind": "largest"})


def test_pipeline_solves_to_smallest():
    _check_solved(TO_SMALLEST, "to_smallest",
                  {"kind": "largest"}, {"kind": "smallest"})


def test_two_recolor_tasks_anti_unify():
    """The two tasks share the (object_recolor, recolor_object) skeleton but
    diverge in (selector, source); save_rule must lift both to ?v variables via
    unify(), yielding ONE covers=2 rule with a trace (R3)."""
    from agent.memory import save_rule

    with tempfile.TemporaryDirectory() as proc_root, \
         tempfile.TemporaryDirectory() as ep_root:
        wm_a, _ = _solve(TO_LARGEST, "to_largest")
        wm_b, _ = _solve(TO_SMALLEST, "to_smallest")
        rule_a = wm_a.s1["active-rules"][0]
        rule_b = wm_b.s1["active-rules"][0]

        save_rule(rule_a, "to_largest", proc_root, ep_root)
        path = save_rule(rule_b, "to_smallest", proc_root, ep_root)

        with open(path) as fh:
            stored = json.load(fh)
        assert sorted(stored["covers"]) == ["to_largest", "to_smallest"]
        assert stored.get("anti_unification_trace")
        args = stored["action"]["args"]
        # divergent positions lifted to ?v variables
        assert str(args.get("selector")).startswith("?v")
        assert str(args.get("source")).startswith("?v")
        # exactly one rule file persisted (no accretion)
        files = [f for f in os.listdir(proc_root)
                 if f.startswith("rule_") and f.endswith(".json")]
        assert len(files) == 1
