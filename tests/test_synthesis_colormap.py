"""
Tests for the synthesizer's global colour-substitution schema (Schema 4,
program/synthesis.py) and the merge-key fix that keeps it a distinct
covers>1 family from the resize schema (agent/memory.py).

A global colour map is the general case no single-colour `object_recolor`
family fits: several distinct colours each map to a different colour. Expressed
as one `coloring(cells_with_color(c), f(c))` step per changed colour, two such
tasks with divergent maps lift via unify() into one rule with covers=2 (R3).
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
    # one coloring step per changed colour (2->3, 4->5), background 0 untouched.
    assert prog == [
        ("coloring", ("cells_with_color", ("const", 2)), ("const", 3)),
        ("coloring", ("cells_with_color", ("const", 4)), ("const", 5)),
    ]


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
    colormap = [["coloring", ["cells_with_color", ["const", 2]], ["const", 3]]]
    assert _program_skeleton(resize) != _program_skeleton(colormap)


def test_program_skeleton_unifies_colormaps_differing_only_in_constants():
    a = [["coloring", ["cells_with_color", ["const", 2]], ["const", 3]],
         ["coloring", ["cells_with_color", ["const", 4]], ["const", 5]]]
    b = [["coloring", ["cells_with_color", ["const", 1]], ["const", 6]],
         ["coloring", ["cells_with_color", ["const", 8]], ["const", 7]]]
    assert _program_skeleton(a) == _program_skeleton(b)


def _synth_rule(program):
    return {
        "type": "synthesized_program",
        "condition": {"type": "synthesized_program",
                      "params": {"program": program, "min_evidence": 1}},
        "action": {"dsl": "run_program", "args": {"program": program}},
    }


def test_two_colormaps_fold_into_one_rule_with_trace():
    """Two colour-map tasks with divergent maps -> one rule, covers=2, trace —
    and a resize rule present in the same store is NOT contaminated."""
    tmp = tempfile.mkdtemp()
    epi = tempfile.mkdtemp()
    try:
        # A pre-existing (generalised) resize rule shares the coarse
        # (synthesized_program, run_program) skeleton — it must not absorb the
        # colour-map tasks.
        resize = _synth_rule([["make_grid", ["const", "?v1"], ["const", "?v2"],
                               ["bg"]], ["paint_objects", ["all_objects"]]])
        save_rule(resize, "resize_x", tmp, epi)

        a = _synth_rule([["coloring", ["cells_with_color", ["const", 2]],
                          ["const", 3]]])
        b = _synth_rule([["coloring", ["cells_with_color", ["const", 1]],
                          ["const", 6]]])
        save_rule(a, "cm_a", tmp, epi)
        save_rule(b, "cm_b", tmp, epi)

        rules = [json.load(open(os.path.join(tmp, f)))
                 for f in sorted(os.listdir(tmp))]
        by_cov = {tuple(sorted(r["covers"])): r for r in rules}
        # resize untouched
        assert ("resize_x",) in by_cov
        # the two colour-maps folded into one covers=2 rule with a trace
        cm = by_cov.get(("cm_a", "cm_b"))
        assert cm is not None, [r["covers"] for r in rules]
        assert cm.get("anti_unification_trace")
        # 3 distinct rule files, not the colour-maps swallowed by resize
        assert len(rules) == 2
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
        shutil.rmtree(epi, ignore_errors=True)
