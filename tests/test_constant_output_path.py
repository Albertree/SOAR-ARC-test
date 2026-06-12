"""
Tests for R0's *generation → prediction → persistence* loop (BACKLOG_LOOP.md R0).

Iter 1 laid the recognition substrate (the `constant_output` matcher; tested in
test_constant_output.py). This file covers the rest of the COMM-copy path:

  * the two frozen DSL primitives (`make_grid`, `coloring`) and `apply_DSL`;
  * `render_grid_via_primitives` reproducing an arbitrary grid from those two;
  * GeneralizeOperator emitting a canonical {condition, action} rule when the
    matcher fires, and PredictOperator rendering the common output;
  * save_rule_to_ltm persisting canonical schema and *merging* two equivalent
    rules into one `covers`>1 rule (the P1/P2 generalization direction);
  * validate_rule rejecting a condition-less rule (the F4 guard).
"""

import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from procedural_memory.DSL.make_grid import make_grid  # noqa: E402
from procedural_memory.DSL.coloring import coloring  # noqa: E402
from procedural_memory.DSL.apply import apply_DSL  # noqa: E402
from agent.dsl_expr.render import render_grid_via_primitives  # noqa: E402
from agent.active_operators import GeneralizeOperator, PredictOperator  # noqa: E402
from agent import memory  # noqa: E402


# ── frozen DSL primitives ─────────────────────────────────────────────
def test_make_grid_shape_and_independence():
    g = make_grid(2, 3, 0)
    assert g == [[0, 0, 0], [0, 0, 0]]
    g[0][0] = 9
    assert g[1][0] == 0  # rows are not aliased


def test_coloring_single_and_list():
    base = make_grid(2, 2, 0)
    assert coloring(base, (0, 1), 5) == [[0, 5], [0, 0]]
    assert coloring(base, [(0, 0), (1, 1)], 3) == [[3, 0], [0, 3]]


def test_coloring_transparent_is_noop():
    base = [[1, 2], [3, 4]]
    assert coloring(base, [(0, 0)], 13) == base


def test_coloring_out_of_bounds_ignored():
    base = make_grid(1, 1, 0)
    assert coloring(base, [(5, 5)], 7) == [[0]]


def test_apply_dsl_dispatch():
    assert apply_DSL("make_grid", height=1, width=2, color=4) == [[4, 4]]
    assert apply_DSL("coloring", [[0, 0]], selection=(0, 1), color=2) == [[0, 2]]
    try:
        apply_DSL("rotate", [[0]])
    except KeyError:
        return
    assert False, "expected KeyError for unknown primitive"


# ── render: grid == make_grid + coloring composition ──────────────────
def test_render_reproduces_grid():
    target = [
        [0, 0, 0, 0, 0, 0],
        [0, 0, 0, 0, 0, 0],
        [0, 0, 0, 0, 0, 0],
        [0, 0, 0, 0, 0, 0],
        [0, 0, 0, 0, 0, 0],
        [0, 0, 0, 0, 0, 2],
    ]
    assert render_grid_via_primitives(target) == target


def test_render_multi_color():
    target = [[1, 0, 2], [0, 0, 0], [3, 3, 0]]
    assert render_grid_via_primitives(target) == target


# ── generalize: canonical rule on constant-output patterns ────────────
def _const_patterns(common):
    return {
        "pair_analyses": [],
        "grid_size_preserved": True,
        "output_invariant": {
            "all_equal": True, "evidence_count": 2, "common_output": common},
    }


def test_generalize_emits_canonical_rule():
    op = GeneralizeOperator()

    class _WM:
        def __init__(self):
            self.s1 = {"patterns": _const_patterns([[0, 2]])}

    wm = _WM()
    op.effect(wm)
    rule = wm.s1["active-rules"][0]
    assert rule["condition"]["type"] == "constant_output"
    assert rule["action"]["dsl"] == "copy_common_output"
    assert "type" not in rule  # not a legacy {type,...} rule


def test_generalize_skips_when_outputs_differ():
    op = GeneralizeOperator()
    patterns = {
        "pair_analyses": [],
        "grid_size_preserved": True,
        "output_invariant": {"all_equal": False, "evidence_count": 2},
    }

    class _WM:
        def __init__(self):
            self.s1 = {"patterns": patterns}

    wm = _WM()
    op.effect(wm)
    rule = wm.s1["active-rules"][0]
    # no constant_output rule — falls through to a legacy/ identity rule
    assert rule.get("action", {}).get("dsl") != "copy_common_output"


# ── predict: renders the common output, value-agnostically ────────────
class _Grid:
    def __init__(self, raw):
        self.raw = raw


class _Pair:
    def __init__(self, inp, out):
        self.input_grid = _Grid(inp) if inp is not None else None
        self.output_grid = _Grid(out) if out is not None else None


class _Task:
    def __init__(self, examples, tests):
        self.example_pairs = [_Pair(i, o) for i, o in examples]
        self.test_pairs = [_Pair(i, o) for i, o in tests]


def test_predict_renders_common_output():
    common = [[0, 0], [0, 7]]
    task = _Task(
        examples=[([[1, 0], [0, 0]], common), ([[0, 1], [0, 0]], common)],
        tests=[([[0, 0], [1, 0]], None)],
    )

    class _WM:
        def __init__(self, task):
            self.task = task
            self.s1 = {"active-rules": [{
                "condition": {"type": "constant_output", "params": {}, "min_evidence": 2},
                "action": {"dsl": "copy_common_output", "args": {}}}]}

    wm = _WM(task)
    PredictOperator().effect(wm)
    assert wm.s1["predictions"]["test_0"] == common


# ── persistence: canonical schema + merge → covers>1 ──────────────────
def test_save_merges_equivalent_canonical_rules():
    rule = {
        "condition": {"type": "constant_output", "params": {}, "min_evidence": 2},
        "action": {"dsl": "copy_common_output", "args": {}},
        "concept": "copy_common_output", "category": "constant_output",
    }
    with tempfile.TemporaryDirectory() as d:
        p1 = memory.save_rule_to_ltm(rule, "easy000a", d)
        p2 = memory.save_rule_to_ltm(rule, "easy000b", d)
        assert p1 == p2  # merged into the same file
        import json
        with open(p1) as fh:
            stored = json.load(fh)
        assert sorted(stored["covers"]) == ["easy000a", "easy000b"]
        assert "condition" in stored and "action" in stored


def test_validate_rule_rejects_condition_less():
    try:
        memory.validate_rule({"action": {"dsl": "x", "args": {}}, "covers": ["t"]})
    except memory.RuleSchemaError:
        return
    assert False, "expected RuleSchemaError for missing condition"
