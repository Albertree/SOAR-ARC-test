"""
Tests for R4's *application* wiring generalised across the size-extreme direction
(BACKLOG_LOOP.md R4 "2nd-order / ranking relation" + R3 lift): the `object_ranking`
producer, the `recolor_extreme` rule builder, its renderer, and the
anti-unification lift that folds the "recolor largest" and "recolor smallest"
families into one `covers>1` abstraction.

Iter 13 added the substrate; iter 14 wired the largest-only application; this pins
the direction generalization:
  * signal      — ExtractPatternOperator surfaces the direction-aware
                  object_ranking dict (extreme_direction max *and* min), and
                  declines on the single-object easy path (no misfire).
  * end-to-end  — the pipeline renders the correct recolored grid via the frozen
                  `coloring` primitive, value-agnostically, for the largest *and*
                  smallest families (different color/grid).
  * R3 lift     — save_rule / unify fold the two concrete instances (extreme=max,
                  extreme=min) into one `recolor_extreme` rule whose `extreme` is a
                  `?vN` variable, covers>1, with an anti_unification_trace.
"""

import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agent.conditions import match  # noqa: E402


# ── helpers: load a real task and run the mini-pipeline ────────────────
def _load_task(task_path, data_root="data"):
    from managers.arc_manager import ARCManager
    with tempfile.TemporaryDirectory() as tmp:
        return ARCManager(data_root=data_root,
                          semantic_memory_root=tmp).load_task(task_path)


def _run_pipeline(task):
    from agent.wm import WorkingMemory
    from agent.active_operators import (
        ExtractPatternOperator, GeneralizeOperator, PredictOperator,
    )
    wm = WorkingMemory()
    wm.task = task
    ExtractPatternOperator().effect(wm)
    GeneralizeOperator().effect(wm)
    PredictOperator().effect(wm)
    return wm.s1["patterns"], wm


# ── signal: real ExtractPatternOperator output ────────────────────────
def test_signal_object_ranking_on_largest_recolor():
    patterns = _run_pipeline(_load_task("ARC_madeup/largest_recolor"))[0]
    rank = patterns["object_ranking"]
    assert rank["multi_object"] is True
    assert rank["select_extreme"] is True
    assert rank["recolor_constant"] is True
    assert rank["recolor_color"] == 4
    assert rank["extreme_direction"] == "max"
    assert rank["others_unchanged"] is True
    assert rank["evidence_count"] == 3
    assert match("recolor_extreme_object", patterns) is True


def test_signal_object_ranking_on_smallest_recolor():
    # The mirror family: the single *smallest* object is recolored. The same one
    # matcher fires; the producer discovers extreme_direction="min".
    patterns = _run_pipeline(_load_task("ARC_madeup/smallest_recolor"))[0]
    rank = patterns["object_ranking"]
    assert rank["multi_object"] is True
    assert rank["select_extreme"] is True
    assert rank["recolor_constant"] is True
    assert rank["recolor_color"] == 7
    assert rank["extreme_direction"] == "min"
    assert rank["others_unchanged"] is True
    assert match("recolor_extreme_object", patterns) is True


def test_signal_object_ranking_on_variant_color_grid():
    # A different color (2->8) and grid: the same value-agnostic signal holds.
    patterns = _run_pipeline(_load_task("ARC_madeup/largest_recolor_b"))[0]
    rank = patterns["object_ranking"]
    assert rank["multi_object"] is True
    assert rank["recolor_constant"] is True
    assert rank["recolor_color"] == 8
    assert rank["extreme_direction"] == "max"
    assert match("recolor_extreme_object", patterns) is True


def test_signal_declines_on_single_object_easy_task():
    # easy000c is a single-object move: multi_object is False, so the ranking
    # matcher stays dormant and cannot misfire on the easy/easy_a path.
    patterns = _run_pipeline(_load_task("ARC_easy_a/easy000c"))[0]
    rank = patterns["object_ranking"]
    assert rank["multi_object"] is False
    assert rank["select_extreme"] is False
    assert rank["extreme_direction"] is None
    assert match("recolor_extreme_object", patterns) is False


# ── end-to-end: pipeline renders the correct recolored grid ───────────
def test_pipeline_solves_recolor_extreme_both_directions():
    cases = [
        ("largest_recolor", "max"),
        ("largest_recolor_b", "max"),
        ("smallest_recolor", "min"),
    ]
    for name, direction in cases:
        task = _load_task(f"ARC_madeup/{name}")
        _, wm = _run_pipeline(task)
        rule = wm.s1["active-rules"][0]
        assert rule["type"] == "recolor_extreme", name
        # The only arg is the discovered direction; the color is NOT stored.
        assert (rule.get("action") or {}).get("args") == {"extreme": direction}, name
        preds = wm.s1.get("predictions") or {}
        assert "test_0" in preds, name
        expected = task.test_pairs[0].output_grid.raw
        assert preds["test_0"] == expected, name


def test_renderer_recolors_only_the_extreme_object():
    # largest: exactly the 6 cells of the 2x3 largest object change, all to 4.
    task = _load_task("ARC_madeup/largest_recolor")
    _, wm = _run_pipeline(task)
    pred = wm.s1["predictions"]["test_0"]
    test_in = task.test_pairs[0].input_grid.raw
    changed = [
        (r, c)
        for r in range(len(test_in)) for c in range(len(test_in[0]))
        if test_in[r][c] != pred[r][c]
    ]
    assert len(changed) == 6
    assert all(pred[r][c] == 4 for r, c in changed)
    assert all(test_in[r][c] != 0 for r, c in changed)


def test_renderer_recolors_only_the_smallest_object():
    # smallest: exactly the 2 cells of the 1x2 smallest object change, all to 7.
    task = _load_task("ARC_madeup/smallest_recolor")
    _, wm = _run_pipeline(task)
    pred = wm.s1["predictions"]["test_0"]
    test_in = task.test_pairs[0].input_grid.raw
    changed = [
        (r, c)
        for r in range(len(test_in)) for c in range(len(test_in[0]))
        if test_in[r][c] != pred[r][c]
    ]
    assert len(changed) == 2
    assert all(pred[r][c] == 7 for r, c in changed)
    assert all(test_in[r][c] != 0 for r, c in changed)


# ── R3: anti-unification lifts the two directions into one rule ───────
def _built_rule(name):
    _, wm = _run_pipeline(_load_task(f"ARC_madeup/{name}"))
    return wm.s1["active-rules"][0]


def test_unify_lifts_extreme_direction_to_a_variable():
    # The two concrete instances differ ONLY in action.args.extreme — exactly the
    # position R3 generalises. unify lifts it to a `?vN` and unions the covers.
    from program.anti_unification import unify
    max_rule = dict(_built_rule("largest_recolor"))
    min_rule = dict(_built_rule("smallest_recolor"))
    max_rule["covers"] = ["largest_recolor"]
    min_rule["covers"] = ["smallest_recolor"]
    max_rule["source_task"] = "largest_recolor"
    min_rule["source_task"] = "smallest_recolor"
    with tempfile.TemporaryDirectory() as tmp:
        result = unify([max_rule, min_rule], episodic_memory_root=tmp)
    assert result.is_more_general()
    abstract = result.abstract_rule
    extreme = abstract["action"]["args"]["extreme"]
    assert isinstance(extreme, str) and extreme.startswith("?"), extreme
    assert set(abstract["covers"]) == {"largest_recolor", "smallest_recolor"}
    assert abstract["anti_unification_trace"] is not None


def test_save_rule_folds_both_families_into_one_abstraction():
    # End-to-end through the single AU call site (memory.save_rule): saving the
    # min instance when the max instance already exists lifts them into ONE rule
    # file whose extreme is a variable and whose covers spans both tasks.
    from agent import memory
    max_rule = _built_rule("largest_recolor")
    min_rule = _built_rule("smallest_recolor")
    with tempfile.TemporaryDirectory() as tmp:
        memory.save_rule(max_rule, "largest_recolor", procedural_memory_root=tmp)
        memory.save_rule(min_rule, "smallest_recolor", procedural_memory_root=tmp)
        rules = memory._load_existing_rules(tmp)
    assert len(rules) == 1, [r for _, r in rules]
    _, lifted = rules[0]
    assert lifted["action"]["dsl"] == "recolor_extreme"
    assert str(lifted["action"]["args"]["extreme"]).startswith("?")
    assert set(lifted["covers"]) == {"largest_recolor", "smallest_recolor"}
    assert lifted["anti_unification_trace"] is not None


# ── regression: renderer declines (never crashes) on a resize task ────
def _grid(raw):
    from types import SimpleNamespace
    return SimpleNamespace(raw=raw, height=len(raw), width=len(raw[0]) if raw else 0)


def _task_with_pairs(pairs):
    # Minimal stand-in task: only `example_pairs` (in/out grids) is read by the
    # renderer + its grader. Each pair is (input_raw, output_raw).
    from types import SimpleNamespace
    eps = [SimpleNamespace(input_grid=_grid(i), output_grid=_grid(o))
           for i, o in pairs]
    return SimpleNamespace(example_pairs=eps)


def test_renderer_declines_on_shape_changing_task_without_crashing():
    # A stored `recolor_extreme` abstraction (extreme=?v1) is speculatively
    # applied to a task whose example *outputs* differ in shape from their inputs
    # (a resize). The selected object's input coordinates do not exist in the
    # smaller output grid; the grader's dimension guard must make the renderer
    # decline (return None) rather than index out of bounds (the iter-16 crash on
    # ~37% of ARC-AGI-2 training tasks). Asserts no exception *and* a clean None.
    from agent.active_operators import PredictOperator
    # 3x3 multi-object inputs, 2x2 outputs (shape changes input->output).
    pairs = [
        ([[1, 1, 0], [0, 0, 0], [0, 0, 2]], [[3, 3], [3, 3]]),
        ([[0, 5, 5], [0, 0, 0], [4, 0, 0]], [[3, 3], [3, 3]]),
    ]
    task = _task_with_pairs(pairs)
    rule = {"action": {"dsl": "recolor_extreme", "args": {"extreme": "?v1"}}}
    test_in = _grid([[1, 1, 0], [0, 0, 0], [0, 0, 2]])
    op = PredictOperator()
    op._task = task
    # Must not raise IndexError; must decline because no direction explains the
    # (shape-mismatched) examples.
    assert op._render_recolor_extreme(rule, task, test_in) is None


def test_lifted_rule_is_replayable_via_runtime_resolution():
    # The lifted abstraction's `extreme` hole is `_RUNTIME_RESOLVABLE`, so the fast
    # path admits it (it is filled at render time by example-grounded selection,
    # not a stored literal) — the §2.5-2b "selection completes the AU product".
    from agent import memory
    abstract = {
        "condition": {"type": "recolor_extreme_object", "params": {"min_evidence": 2}},
        "action": {"dsl": "recolor_extreme", "args": {"extreme": "?v1"}},
        "anti_unification_trace": "episodic_memory/x/anti_unification/au_001.json",
    }
    replay = memory.applicable_rule(abstract)
    assert replay is not None
    assert replay["type"] == "recolor_extreme"
