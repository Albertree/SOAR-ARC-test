"""
Tests for R5 fast-path reuse (BACKLOG_LOOP.md R5) — `ActiveSoarAgent`'s reuse of
a stored *abstract* rule on a new task.

The learned families (constant_output / object_motion / object_recolor) carry
*holes* (argument expressions like `?v`) filled per task from the example
comparison (§2.5-2b). The input-grid-only `_apply_rule` declines them, so before
this they were always re-derived on the slow path (Reused: 0). The reuse path
re-fits the holes from the *new* task's own examples, requires the rule's own
condition matcher to fire, gates on the fitted rule reproducing every example
output exactly, and only then renders the test inputs — value-agnostic reuse, not
literal replay.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agent.active_agent import ActiveSoarAgent


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
    def __init__(self, train, test, name="reuse_task"):
        self.task_hex = name
        self.example_pairs = [_Pair(i, o) for i, o in train]
        self.test_pairs = [_Pair(i, o) for i, o in test]


def _motion_rule(min_evidence=1):
    return {
        "type": "object_motion",
        "condition": {"type": "object_motion",
                      "params": {"min_evidence": min_evidence}},
        "action": {"dsl": "place_object", "args": {"target": "?v1"}},
    }


def _constant_rule(min_evidence=2):
    return {
        "type": "constant_output",
        "condition": {"type": "constant_output",
                      "params": {"min_evidence": min_evidence}},
        "action": {"dsl": "copy_common_output", "args": {}},
    }


# easy000c-style: single object -> bottom-right corner of a 6x6 grid.
MOVE_TASK = _Task(
    train=[
        ([[0]*6, [0, 2, 0, 0, 0, 0], [0]*6, [0]*6, [0]*6, [0]*6],
         [[0]*6, [0]*6, [0]*6, [0]*6, [0]*6, [0, 0, 0, 0, 0, 2]]),
        ([[0]*6, [0, 0, 0, 0, 1, 0], [0]*6, [0]*6, [0]*6, [0]*6],
         [[0]*6, [0]*6, [0]*6, [0]*6, [0]*6, [0, 0, 0, 0, 0, 1]]),
    ],
    test=[
        ([[0]*6, [0]*6, [0]*6, [0]*6, [0, 0, 4, 0, 0, 0], [0]*6],
         [[0]*6, [0]*6, [0]*6, [0]*6, [0]*6, [0, 0, 0, 0, 0, 4]]),
    ],
    name="move",
)

# all example outputs identical -> the constant-output family.
CONST_TASK = _Task(
    train=[
        ([[1, 0], [0, 0]], [[0, 0], [0, 7]]),
        ([[0, 3], [0, 0]], [[0, 0], [0, 7]]),
    ],
    test=[
        ([[0, 0], [5, 0]], [[0, 0], [0, 7]]),
    ],
    name="const",
)


def _agent():
    return ActiveSoarAgent()


def test_reuse_object_motion_returns_test_prediction():
    agent = _agent()
    patterns = agent._fit_descriptor_patterns(MOVE_TASK)
    out = agent._reuse_descriptor_rule(_motion_rule(), MOVE_TASK, patterns)
    assert out is not None
    assert out == [MOVE_TASK.test_pairs[0].output_grid.raw]


def test_reuse_constant_output_returns_common_grid():
    agent = _agent()
    patterns = agent._fit_descriptor_patterns(CONST_TASK)
    out = agent._reuse_descriptor_rule(_constant_rule(), CONST_TASK, patterns)
    assert out is not None
    assert out == [CONST_TASK.test_pairs[0].output_grid.raw]


def test_motion_rule_declines_constant_task():
    # offered a constant-output task, the object_motion matcher does not fire
    # (no consistent object move), so reuse declines rather than mis-rendering.
    agent = _agent()
    patterns = agent._fit_descriptor_patterns(CONST_TASK)
    assert agent._reuse_descriptor_rule(_motion_rule(), CONST_TASK, patterns) is None


def test_constant_rule_declines_move_task():
    # offered a move task (example outputs all differ), the constant_output
    # matcher does not fire, so reuse declines.
    agent = _agent()
    patterns = agent._fit_descriptor_patterns(MOVE_TASK)
    assert agent._reuse_descriptor_rule(_constant_rule(), MOVE_TASK, patterns) is None


def test_single_pair_constant_rule_declines_under_min_evidence_two():
    # one example pair cannot justify *constancy* (constant_output floor is 2),
    # so a single-pair constant task declines reuse — the §2.1 pairs-≠-2 asymmetry.
    one_pair = _Task(
        train=[([[1, 0], [0, 0]], [[0, 0], [0, 7]])],
        test=[([[0, 0], [5, 0]], [[0, 0], [0, 7]])],
        name="const_one",
    )
    agent = _agent()
    patterns = agent._fit_descriptor_patterns(one_pair)
    assert agent._reuse_descriptor_rule(_constant_rule(), one_pair, patterns) is None


def test_descriptor_renderer_unknown_type_returns_none():
    assert ActiveSoarAgent._descriptor_renderer("nope", {}) is None
