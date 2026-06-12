"""
Tests for the whole-grid geometric-transform family (BACKLOG_LOOP.md R1 /
§2.5-1 worked example): the input grid flipped / rotated / transposed by a single
learned coordinate permutation.

A flip/rotation is NOT a new DSL primitive (F3 forbids that) — it is the frozen
`coloring` primitive applied at a *transformed coordinate*, exactly the
"rotate/flip = coloring with a coordinate-mapping expression" worked example in
BACKLOG_LOOP §2.5-1. The transform name is the lifted *argument*, value-/colour-/
shape-/size-agnostic, so ONE rule covers the whole family.

Grounded on *real* ARC-AGI-2 training tasks the agent failed before this family
(rule=identity): 67a3c6ac (flip_h), 68b16354 (flip_v), 74dd1130 / 9dfd6313
(transpose), 3c9b0459 / 6150a2bd (rot180), ed36ccf7 (rot270) — all merge into a
single covers>1 rule (one recognition→transformation skeleton, many tasks), the
§2.5-3/4 "covers, not accretion" shape.
"""

import glob
import json
import os

from agent.conditions import CONDITION_REGISTRY, match as match_condition
from agent.dsl_expr.selection import (
    analyze_geometric_transform,
    apply_geometric,
    GEO_COORD,
    GEO_DIMS,
    GEOMETRIC_VOCAB,
)
from agent.dsl_expr.render import render_geometric_transform
from agent.active_operators import (
    GeneralizeOperator,
    PredictOperator,
    GEOMETRIC_TRANSFORM_DSL,
)

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _load_task(task_id):
    matches = glob.glob(os.path.join(ROOT, "data", "**", f"{task_id}.json"),
                        recursive=True)
    assert matches, f"task {task_id} not found under data/"
    with open(matches[0]) as fh:
        return json.load(fh)


class _G:
    def __init__(self, raw):
        self.raw = raw


class _Pair:
    def __init__(self, inp, out):
        self.input_grid = _G(inp)
        self.output_grid = _G(out)


def _pairs(rows):
    return [_Pair(i, o) for i, o in rows]


# the real tasks and the transform each should learn
REAL = {
    "67a3c6ac": "flip_h",
    "68b16354": "flip_v",
    "74dd1130": "transpose",
    "9dfd6313": "transpose",
    "3c9b0459": "rot180",
    "6150a2bd": "rot180",
    "ed36ccf7": "rot270",
}


# ---- the coordinate vocabulary --------------------------------------------

def test_vocab_maps_are_self_consistent_bijections():
    # every GEO_COORD map must be a bijection onto the GEO_DIMS rectangle, so
    # render (make_grid + coloring) and apply_geometric agree by construction.
    for name in GEOMETRIC_VOCAB:
        H, W = 3, 4
        Ho, Wo = GEO_DIMS[name](H, W)
        seen = set()
        for r in range(H):
            for c in range(W):
                rr, cc = GEO_COORD[name](r, c, H, W)
                assert 0 <= rr < Ho and 0 <= cc < Wo, name
                seen.add((rr, cc))
        assert len(seen) == H * W, name  # no collisions -> bijection


def test_render_equals_apply_geometric():
    grid = [[1, 2, 0], [0, 3, 4]]
    for name in GEOMETRIC_VOCAB:
        assert render_geometric_transform(grid, name) == apply_geometric(grid, name), name


# ---- analyzer reading ------------------------------------------------------

def test_analyze_learns_correct_transform_on_real_tasks():
    for tid, expected in REAL.items():
        task = _load_task(tid)
        pairs = _pairs([(p["input"], p["output"]) for p in task["train"]])
        sig = analyze_geometric_transform(pairs)
        assert sig["valid_all"] is True, tid
        assert sig["transform"] == expected, (tid, sig["transform"])
        assert sig["evidence"] == len(task["train"])


def test_analyze_declines_on_identity():
    # input == output everywhere -> no genuine transform (would be the identity)
    pairs = _pairs([
        ([[1, 2], [3, 4]], [[1, 2], [3, 4]]),
        ([[5, 6], [7, 8]], [[5, 6], [7, 8]]),
    ])
    sig = analyze_geometric_transform(pairs)
    assert sig["transform"] is None
    assert sig["valid_all"] is False


def test_analyze_declines_when_no_single_map_fits_all_pairs():
    # pair 1 is a flip_h, pair 2 is a flip_v -> no one permutation covers both
    pairs = _pairs([
        ([[1, 2], [3, 4]], [[2, 1], [4, 3]]),   # flip_h
        ([[1, 2], [3, 4]], [[3, 4], [1, 2]]),   # flip_v
    ])
    sig = analyze_geometric_transform(pairs)
    assert sig["transform"] is None


# ---- matcher (P5) ----------------------------------------------------------

def test_geometric_matcher_registered():
    assert "geometric_transform" in CONDITION_REGISTRY


def test_geometric_matcher_honours_min_evidence():
    task = _load_task("3c9b0459")
    pairs = _pairs([(p["input"], p["output"]) for p in task["train"]])
    patterns = {"geometric_transform": analyze_geometric_transform(pairs)}
    assert match_condition("geometric_transform", patterns, {"min_evidence": 2}) is True
    # one example can't establish *which* permutation is the consistent rule
    assert match_condition("geometric_transform", patterns, {"min_evidence": 99}) is False


# ---- generalize emits a canonical, value-agnostic (mergeable) rule ---------

def test_generalize_emits_canonical_geometric_rule():
    task = _load_task("67a3c6ac")
    pairs = _pairs([(p["input"], p["output"]) for p in task["train"]])
    patterns = {"geometric_transform": analyze_geometric_transform(pairs)}
    op = GeneralizeOperator()
    rule = op._geometric_transform_rule(patterns)
    assert rule is not None
    assert "type" not in rule  # canonical {condition, action}, not a legacy envelope
    assert rule["condition"]["type"] == "geometric_transform"
    assert rule["action"]["dsl"] == GEOMETRIC_TRANSFORM_DSL
    # EMPTY args: the transform is recomputed at predict, so all geometric tasks
    # merge by condition+action equivalence into ONE rule (covers>1), not one
    # literal rule per task.
    assert rule["action"]["args"] == {}
    assert rule["category"] == "geometric_transform"


def test_generalize_rule_identical_across_different_transforms():
    # a flip_h task and a rot180 task must emit the SAME canonical rule (so they
    # merge) — the transform is an argument recomputed at predict, not baked in.
    op = GeneralizeOperator()
    r1 = op._geometric_transform_rule(
        {"geometric_transform": analyze_geometric_transform(
            _pairs([(p["input"], p["output"])
                    for p in _load_task("67a3c6ac")["train"]]))})
    r2 = op._geometric_transform_rule(
        {"geometric_transform": analyze_geometric_transform(
            _pairs([(p["input"], p["output"])
                    for p in _load_task("3c9b0459")["train"]]))})
    assert r1["action"] == r2["action"]
    assert r1["condition"]["type"] == r2["condition"]["type"]


def test_geometric_rule_none_when_not_a_transform():
    pairs = _pairs([
        ([[1, 2], [3, 4]], [[1, 2], [3, 4]]),
        ([[5, 6], [7, 8]], [[5, 6], [7, 8]]),
    ])
    patterns = {"geometric_transform": analyze_geometric_transform(pairs)}
    op = GeneralizeOperator()
    assert op._geometric_transform_rule(patterns) is None


# ---- end-to-end predict on the real tasks ----------------------------------

def test_geometric_predicts_real_task_test_pairs():
    """Recompute the permutation from the examples and apply it to each held-out
    test input (P5), reproducing the real task's test output exactly via the
    frozen make_grid + coloring composition."""
    for tid in REAL:
        task = _load_task(tid)

        class _Task:
            example_pairs = _pairs([(p["input"], p["output"]) for p in task["train"]])
            test_pairs = _pairs([(p["input"], p["output"]) for p in task["test"]])

        out = PredictOperator._geometric_transform_grids(_Task())
        for i, tp in enumerate(task["test"]):
            assert out.get(i) == tp["output"], tid
