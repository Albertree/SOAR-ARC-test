"""
Tests for the synthesizer's object-level recolour-by-property schema (Schema 14,
program/synthesis.py).

Each input object is repainted in the colour a value-agnostic *property → colour*
map assigns to it — the object's cell-count (`size`) or its translation-normalised
cell signature (`shape`). The whole map rides in ONE `recolor_objects` const leaf
(composed from the frozen `coloring` primitive at run time), so a size-keyed task
and a shape-keyed task share the SAME one-step skeleton ``[("recolor_objects",
("const", ?v))]`` and lift via unify() into one covers>1 rule (R3) — the
object-level counterpart of Schema 4's cell-wise `recolor_map`, never a rule per
property/arity (BACKLOG_LOOP §2.5-3/4). An object whose property is absent from
the fitted map makes the program *decline* rather than guess (P5 honesty).
"""

from program.synthesis import (
    run_program, synthesize_task, _Unevaluable, _fit_recolor_objects,
)
from agent.memory import _program_skeleton


# --- size-keyed recolour: every object recoloured by its cell count ----------

def test_fit_recolor_by_size():
    # Two objects per grid: a 1-cell blob -> colour 3, a 3-cell blob -> colour 4.
    # The map is keyed on size, value-agnostic, fitted from the pairs.
    pairs = [
        {"input":  [[5, 0, 0], [0, 0, 6], [0, 6, 6]],
         "output": [[3, 0, 0], [0, 0, 4], [0, 4, 4]]},
        {"input":  [[0, 0, 7], [8, 8, 0], [8, 0, 0]],
         "output": [[0, 0, 3], [4, 4, 0], [4, 0, 0]]},
    ]
    prog = _fit_recolor_objects(pairs)
    assert prog is not None
    assert prog[0][0] == "recolor_objects"
    assert prog[0][1][1]["prop"] == "size"
    for p in pairs:
        assert run_program(prog, p["input"]) == p["output"]


# --- shape-keyed recolour: same size, different shape -> different colour -----

def test_fit_recolor_by_shape_when_size_ambiguous():
    # Two size-2 objects of different shape (horizontal vs vertical domino): size
    # alone cannot tell them apart (same key, conflicting colours), so the fitter
    # must fall through to the shape property.
    pairs = [
        {"input":  [[2, 2, 0, 0], [0, 0, 0, 3], [0, 0, 0, 3]],
         "output": [[5, 5, 0, 0], [0, 0, 0, 7], [0, 0, 0, 7]]},
        {"input":  [[0, 4, 4, 0], [0, 0, 0, 0], [1, 0, 0, 0], [1, 0, 0, 0]],
         "output": [[0, 5, 5, 0], [0, 0, 0, 0], [7, 0, 0, 0], [7, 0, 0, 0]]},
    ]
    prog = _fit_recolor_objects(pairs)
    assert prog is not None
    assert prog[0][1][1]["prop"] == "shape"
    for p in pairs:
        assert run_program(prog, p["input"]) == p["output"]


# --- declines (no guess) on a test object whose property is unseen (P5) -------

def test_declines_on_unseen_property_key():
    pairs = [
        {"input":  [[5, 0], [0, 6]],
         "output": [[3, 0], [0, 3]]},  # both size-1 -> colour 3
    ]
    prog = _fit_recolor_objects(pairs)
    assert prog is not None
    # A 2-cell object's size is absent from the {1: 3} map -> the step declines.
    try:
        run_program(prog, [[7, 7], [0, 0]])
        assert False, "expected _Unevaluable on unseen size key"
    except _Unevaluable:
        pass


# --- identity output is not a recolour rule ----------------------------------

def test_no_change_is_not_recolour():
    pairs = [{"input": [[5, 0], [0, 6]], "output": [[5, 0], [0, 6]]}]
    assert _fit_recolor_objects(pairs) is None


# --- two divergent recolour tasks share ONE skeleton (lift into covers>1) -----

def test_size_and_shape_tasks_share_skeleton():
    size_pairs = [
        {"input":  [[5, 0, 0], [0, 0, 6], [0, 6, 6]],
         "output": [[3, 0, 0], [0, 0, 4], [0, 4, 4]]},
        {"input":  [[0, 0, 7], [8, 8, 0], [8, 0, 0]],
         "output": [[0, 0, 3], [4, 4, 0], [4, 0, 0]]},
    ]
    shape_pairs = [
        {"input":  [[2, 2, 0, 0], [0, 0, 0, 3], [0, 0, 0, 3]],
         "output": [[5, 5, 0, 0], [0, 0, 0, 7], [0, 0, 0, 7]]},
        {"input":  [[0, 4, 4, 0], [0, 0, 0, 0], [1, 0, 0, 0], [1, 0, 0, 0]],
         "output": [[0, 5, 5, 0], [0, 0, 0, 0], [7, 0, 0, 0], [7, 0, 0, 0]]},
    ]
    a = _fit_recolor_objects(size_pairs)
    b = _fit_recolor_objects(shape_pairs)
    assert a is not None and b is not None
    # Different fitted leaves, but the SAME structural skeleton -> they anti-unify.
    assert a[0][1][1] != b[0][1][1]
    assert _program_skeleton(a) == _program_skeleton(b)


# --- a recolour task is reachable through the full search --------------------

def test_synthesize_task_finds_recolour():
    # Both objects share input colour 5, so a cell-wise `recolor_map` (Schema 4)
    # cannot fit (5 would have to map to two different colours); only the
    # *object-level* size map distinguishes them — exercising Schema 14 end-to-end.
    pairs = [
        {"input":  [[5, 0, 0], [0, 0, 5], [0, 5, 5]],
         "output": [[3, 0, 0], [0, 0, 4], [0, 4, 4]]},
        {"input":  [[0, 0, 5], [5, 5, 0], [5, 0, 0]],
         "output": [[0, 0, 3], [4, 4, 0], [4, 0, 0]]},
    ]
    prog = synthesize_task(pairs)
    assert prog is not None
    assert prog[0][0] == "recolor_objects"
    assert prog[0][1][1]["prop"] == "size"
