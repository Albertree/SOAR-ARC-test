"""
Tests for wiring the general Slow-path synthesizer onto the live pipeline
(BACKLOG_LOOP.md R5/R6, arbor-modules F/G).

The synthesizer (program/synthesis.py) was built off-line in iter25; this iter
wires it as the no-family-fired fallback in GeneralizeOperator and the
`synthesized_program` rendering path in PredictOperator, gated by the new
`synthesized_program` condition matcher. These tests prove:

* the matcher recognises a task by *outcome* (a program reproduces the examples);
* a transformation no hand-picked family recognises (a multi-object grid resize
  with no single mover) is now SOLVED via a searched, value-agnostic program, and
  the synthesized program transfers to the held-out test input;
* the synthesizer does NOT hijack tasks a family already recognises (no regression);
* two tasks with the same searched program fold into ONE rule (covers merge), not
  one rule per task — the §2.5-3 anti-accretion discipline carried to the
  synthesizer layer.
"""

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agent.active_operators import (
    ExtractPatternOperator, GeneralizeOperator, PredictOperator,
)
from agent.conditions import match as match_condition
from agent.memory import save_rule

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class _Grid:
    def __init__(self, raw):
        self.raw = [row[:] for row in raw]
        self.height = len(raw)
        self.width = len(raw[0]) if raw else 0
        self.node_id = id(self)


class _Pair:
    def __init__(self, inp, out):
        self.input_grid = _Grid(inp)
        self.output_grid = _Grid(out) if out is not None else None


class _Task:
    def __init__(self, train, test, name="t"):
        self.task_hex = name
        self.example_pairs = [_Pair(i, o) for i, o in train]
        self.test_pairs = [_Pair(i, o) for i, o in test]


class _WM:
    def __init__(self, task):
        self.task = task
        self.s1 = {}


def _load_resize_task():
    with open(os.path.join(REPO, "data/ARC_madeup/resize_keep_objects.json")) as fh:
        d = json.load(fh)
    train = [(p["input"], p["output"]) for p in d["train"]]
    test = [(p["input"], p["output"]) for p in d["test"]]
    return _Task(train, test, name="resize_keep_objects")


def _run_pipeline(task):
    """Run ExtractPattern -> Generalize -> Predict and return (rule, predictions)."""
    wm = _WM(task)
    ExtractPatternOperator().effect(wm)
    GeneralizeOperator().effect(wm)
    PredictOperator().effect(wm)
    rule = (wm.s1.get("active-rules") or [None])[0]
    return rule, wm.s1.get("predictions") or {}


# --- the matcher recognises a task by outcome --------------------------------

def test_matcher_fires_when_program_reproduces_pairs():
    pairs = [
        {"input": [[0, 0], [0, 0]], "output": [[0, 0, 0], [0, 0, 0], [0, 0, 0]]},
    ]
    prog = [("make_grid", ("const", 3), ("const", 3), ("bg",)),
            ("paint_objects", ("all_objects",))]
    patterns = {"synthesis_pairs": pairs}
    assert match_condition("synthesized_program", patterns, {"program": prog}) is True


def test_matcher_declines_wrong_program():
    pairs = [{"input": [[1]], "output": [[2]]}]
    prog = [("make_grid", ("const", 1), ("const", 1), ("bg",))]  # makes [[0]] != [[2]]
    patterns = {"synthesis_pairs": pairs}
    assert match_condition("synthesized_program", patterns, {"program": prog}) is False


def test_matcher_declines_empty_program():
    # The empty program is identity — handled by the identity fallback, never a
    # learned synthesizer rule.
    patterns = {"synthesis_pairs": [{"input": [[1]], "output": [[1]]}]}
    assert match_condition("synthesized_program", patterns, {"program": []}) is False


def test_matcher_declines_without_pairs():
    prog = [("make_grid", ("const", 1), ("const", 1), ("bg",))]
    assert match_condition("synthesized_program", {}, {"program": prog}) is False


# --- end-to-end: the resize task is solved via a synthesized program ----------

def test_resize_task_solved_by_synthesized_program():
    task = _load_resize_task()
    rule, preds = _run_pipeline(task)
    assert rule is not None and rule.get("type") == "synthesized_program"
    # canonical {condition, action} (F4) with the searched program as data
    assert rule["condition"]["type"] == "synthesized_program"
    assert rule["action"]["dsl"] == "run_program"
    assert rule["action"]["args"]["program"]  # non-empty
    # the program transfers to the held-out test input (P5)
    assert preds.get("test_0") == task.test_pairs[0].output_grid.raw


def test_synthesizer_declines_unsolvable_task():
    # A transformation outside the bounded grammar (single object shifts by one)
    # is an honest miss: no family fires AND the search finds nothing -> identity.
    task = _Task(
        train=[([[0, 0, 0], [0, 5, 0], [0, 0, 0]],
                [[0, 0, 0], [0, 0, 5], [0, 0, 0]]),
               ([[5, 0, 0], [0, 0, 0], [0, 0, 0]],
                [[0, 5, 0], [0, 0, 0], [0, 0, 0]])],
        test=[([[0, 0, 0], [0, 0, 0], [5, 0, 0]],
               [[0, 0, 0], [0, 0, 0], [0, 5, 0]])],
        name="shift",
    )
    rule, _ = _run_pipeline(task)
    # object_motion (translation) legitimately handles this; what we assert is the
    # synthesizer does not *also* claim it — recognition stays with the family.
    assert rule is not None and rule.get("type") != "synthesized_program"


# --- no hijack: families still own the tasks they recognise -------------------

def test_constant_output_not_hijacked():
    task = _Task(
        train=[([[1, 0], [0, 0]], [[0, 0], [0, 7]]),
               ([[0, 3], [0, 0]], [[0, 0], [0, 7]])],
        test=[([[0, 0], [5, 0]], [[0, 0], [0, 7]])],
        name="const",
    )
    rule, _ = _run_pipeline(task)
    assert rule is not None and rule.get("type") == "constant_output"


# --- anti-accretion: same program folds into one rule ------------------------

def _pad(g3, side=5):
    """Embed a 3x3 grid at the top-left of a `side`x`side` background canvas."""
    return [[(g3[r][c] if r < 3 and c < 3 else 0) for c in range(side)]
            for r in range(side)]


def test_two_same_program_tasks_merge(tmp_path):
    # Two distinct resize tasks (different objects, each multi-object 3x3 -> fixed
    # 5x5 keeping objects in place — so no single mover, object_motion declines)
    # synthesize the SAME program; saving both must yield ONE rule with
    # covers == 2, not two rules (§2.5-3).
    pm = str(tmp_path)
    a1 = [[3, 0, 0], [0, 0, 0], [0, 0, 4]]
    a2 = [[0, 0, 2], [0, 0, 0], [5, 0, 0]]
    b1 = [[0, 6, 0], [0, 0, 0], [7, 0, 0]]
    b2 = [[0, 0, 0], [1, 0, 0], [0, 0, 8]]
    t1 = _Task(
        train=[(a1, _pad(a1)), (a2, _pad(a2))],
        test=[([[0, 5, 0], [0, 0, 0], [9, 0, 0]], None)], name="r1",
    )
    t2 = _Task(
        train=[(b1, _pad(b1)), (b2, _pad(b2))],
        test=[([[2, 0, 0], [0, 0, 0], [0, 0, 3]], None)], name="r2",
    )
    r1, _ = _run_pipeline(t1)
    r2, _ = _run_pipeline(t2)
    assert r1["type"] == r2["type"] == "synthesized_program"
    assert r1["action"]["args"]["program"] == r2["action"]["args"]["program"]
    save_rule(r1, t1.task_hex, pm)
    save_rule(r2, t2.task_hex, pm)
    files = [f for f in os.listdir(pm) if f.startswith("rule_") and f.endswith(".json")]
    assert len(files) == 1
    with open(os.path.join(pm, files[0])) as fh:
        stored = json.load(fh)
    assert sorted(stored["covers"]) == ["r1", "r2"]
