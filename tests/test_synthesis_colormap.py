"""
Tests for the synthesizer's global colour-substitution schema (Schema 4,
program/synthesis.py) and the merge-key fix that keeps it a distinct
covers>1 family from the resize schema (agent/memory.py).

A global colour map is the general case no single-colour `object_recolor`
family fits: several distinct colours each map to a different colour. The whole
map is carried as ONE `recolor_map` step (a single const leaf of `(from, to)`
pairs, composed from the frozen `coloring` primitive at run time), so a task
that changes one colour and a task that changes three share the SAME one-step
skeleton and lift via unify() into one covers>1 rule (R3) — instead of
fragmenting into a separate covers=1 rule per changed-colour count (the
arity-keyed accretion that minted rule-per-task, BACKLOG_LOOP §2.5-3/4).
"""

import json
import os
import shutil
import tempfile

from program.synthesis import (
    run_program, synthesize_task, _eval, _Unevaluable, _fit_color_map,
)
from agent.memory import (
    _program_skeleton, _rule_program, _rule_skeleton, save_rule,
)


REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _load(path):
    with open(os.path.join(REPO, path)) as fh:
        return json.load(fh)


# --- cells_with_color expression reads the fixed input grid (P5) -------------

def test_cells_with_color_selects_input_cells():
    env = {"grid": [[2, 0, 4], [4, 0, 2]], "objs": [], "bg": 0}
    assert _eval(("cells_with_color", ("const", 2)), env) == [(0, 0), (1, 2)]
    assert _eval(("cells_with_color", ("const", 4)), env) == [(0, 2), (1, 0)]
    # A colour absent from the grid selects nothing (does not raise).
    assert _eval(("cells_with_color", ("const", 7)), env) == []


# --- Schema 4 search: a consistent global recolour is found ------------------

def test_synthesize_global_colormap():
    pairs = [
        {"input": [[2, 0], [0, 4]], "output": [[3, 0], [0, 5]]},
        {"input": [[4, 2], [2, 0]], "output": [[5, 3], [3, 0]]},
    ]
    prog = synthesize_task(pairs)
    assert prog is not None
    # ONE recolor_map step carrying the whole map (2->3, 4->5) as a single const
    # leaf of (from, to) pairs; background 0 untouched.
    assert prog == [("recolor_map", ("const", ((2, 3), (4, 5))))]
    # and it composes only the frozen `coloring` primitive at run time.
    for p in pairs:
        assert run_program(prog, p["input"]) == p["output"]


def test_recolor_map_of_different_arity_share_one_skeleton():
    """The headline of the single-step form: a task that changes ONE colour and a
    task that changes TWO now share the same program skeleton, so they lift into
    one family. The old per-coloring-step form gave them *different* skeletons
    (one step vs two) and fragmented the family into covers=1 rules."""
    # Two pairs so the constant-output schema cannot also match the single map.
    one = synthesize_task([
        {"input": [[6, 0]], "output": [[2, 0]]},
        {"input": [[0, 6]], "output": [[0, 2]]},
    ])
    two = synthesize_task([
        {"input": [[2, 0], [0, 4]], "output": [[3, 0], [0, 5]]},
        {"input": [[4, 2], [2, 0]], "output": [[5, 3], [3, 0]]},
    ])
    assert one == [("recolor_map", ("const", ((6, 2),)))]
    assert two == [("recolor_map", ("const", ((2, 3), (4, 5))))]
    assert _program_skeleton(one) == _program_skeleton(two)


def test_colormap_program_transfers_to_test_input():
    """A program fitted on train reproduces a held-out input (P5)."""
    task = _load("data/ARC_madeup/color_remap_a.json")
    prog = synthesize_task(task["train"])
    assert prog is not None
    for p in task["test"]:
        assert run_program(prog, p["input"]) == p["output"]


def test_colormap_declines_when_map_inconsistent():
    # colour 2 maps to 3 in pair 0 but to 5 in pair 1 -> not a global map.
    pairs = [
        {"input": [[2, 0]], "output": [[3, 0]]},
        {"input": [[2, 0]], "output": [[5, 0]]},
    ]
    assert synthesize_task(pairs) is None


def test_colormap_declines_on_shape_change():
    # output dims differ from input -> Schema 4 (cell-wise recolour) must decline
    # (some other schema may still handle it; this pins Schema 4 itself).
    pairs = [{"input": [[2, 0], [0, 4]], "output": [[3, 3], [3, 3], [3, 3]]}]
    assert _fit_color_map(pairs) is None


def test_identity_not_reported_as_colormap():
    # outputs equal inputs: identity schema wins, no spurious colour-map steps.
    pairs = [{"input": [[2, 0], [0, 4]], "output": [[2, 0], [0, 4]]}]
    assert synthesize_task(pairs) == []


# --- merge-key fix: distinct synthesizer schemas stay distinct families ------

def test_program_skeleton_separates_resize_from_colormap():
    resize = [["make_grid", ["const", 6], ["const", 6], ["bg"]],
              ["paint_objects", ["all_objects"]]]
    colormap = [["recolor_map", ["const", [[2, 3]]]]]
    assert _program_skeleton(resize) != _program_skeleton(colormap)


def test_program_skeleton_unifies_colormaps_differing_in_map_and_arity():
    # Divergent maps AND divergent changed-colour counts now share one skeleton.
    a = [["recolor_map", ["const", [[2, 3], [4, 5]]]]]
    b = [["recolor_map", ["const", [[1, 6]]]]]
    assert _program_skeleton(a) == _program_skeleton(b)


def _synth_rule(program):
    return {
        "type": "synthesized_program",
        "condition": {"type": "synthesized_program",
                      "params": {"program": program, "min_evidence": 1}},
        "action": {"dsl": "run_program", "args": {"program": program}},
    }


def test_colormaps_of_different_arity_fold_into_one_rule_with_trace():
    """Three colour-map tasks — one changing a single colour, two changing two —
    fold into ONE covers=3 rule with a trace, *across* changed-colour count. The
    old per-coloring-step form split the single-colour task into its own covers=1
    family; the single-step recolor_map form lifts them all together (the fix).
    A resize rule in the same store is NOT contaminated."""
    tmp = tempfile.mkdtemp()
    epi = tempfile.mkdtemp()
    try:
        # A pre-existing (generalised) resize rule shares the coarse
        # (synthesized_program, run_program) skeleton — it must not absorb the
        # colour-map tasks.
        resize = _synth_rule([["make_grid", ["const", "?v1"], ["const", "?v2"],
                               ["bg"]], ["paint_objects", ["all_objects"]]])
        save_rule(resize, "resize_x", tmp, epi)

        one = _synth_rule([["recolor_map", ["const", [[6, 2]]]]])
        a = _synth_rule([["recolor_map", ["const", [[2, 3], [4, 5]]]]])
        b = _synth_rule([["recolor_map", ["const", [[1, 6], [8, 7]]]]])
        save_rule(a, "cm_a", tmp, epi)
        save_rule(b, "cm_b", tmp, epi)
        save_rule(one, "cm_one", tmp, epi)  # single-colour task joins the family

        rules = [json.load(open(os.path.join(tmp, f)))
                 for f in sorted(os.listdir(tmp))]
        by_cov = {tuple(sorted(r["covers"])): r for r in rules}
        # resize untouched
        assert ("resize_x",) in by_cov
        # all three colour-maps folded into one covers=3 rule with a trace
        cm = by_cov.get(("cm_a", "cm_b", "cm_one"))
        assert cm is not None, [r["covers"] for r in rules]
        assert cm.get("anti_unification_trace")
        # 2 distinct rule files (resize + the one colour-map family)
        assert len(rules) == 2
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
        shutil.rmtree(epi, ignore_errors=True)
