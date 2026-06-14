"""
Tests for the synthesizer's enclosed-region fill schema (Schema 16,
program/synthesis.py).

Every *enclosed* background pocket — a background region sealed off from the grid
border by an object wall — is repainted one colour, the recurring ARC "fill the
inside of each closed shape" family. The enclosed cells are a pure *selection* on
the input (a util/LHS computation), painted by the frozen ``coloring`` primitive,
so the schema adds no transformation vocabulary (F3-safe). The fill colour is the
whole per-task content carried in ONE const leaf, so a fill-yellow task and a
fill-blue task share the SAME one-step skeleton ``[("enclosed_fill", ("const",
?v))]`` and lift via unify() into one covers>1 rule (R3), never a rule per colour
(BACKLOG_LOOP §2.5-3/4).
"""

from program.synthesis import (
    run_program, synthesize_task, _fit_enclosed_fill, _enclosed_cells,
)
from agent.memory import _program_skeleton


# --- the enclosed-cell selection: only the sealed interior, never the outside ---

def test_enclosed_cells_only_interior():
    # A 5x5 ring of colour 3 around a single background centre cell.
    grid = [
        [0, 0, 0, 0, 0],
        [0, 3, 3, 3, 0],
        [0, 3, 0, 3, 0],
        [0, 3, 3, 3, 0],
        [0, 0, 0, 0, 0],
    ]
    assert _enclosed_cells(grid, 0) == {(2, 2)}


def test_enclosed_cells_open_shape_has_none():
    # A 'C' shape (right side open) seals nothing — the centre reaches the border.
    grid = [
        [3, 3, 3],
        [3, 0, 0],
        [3, 3, 3],
    ]
    assert _enclosed_cells(grid, 0) == set()


# --- fit a fill colour different from the wall colour -------------------------

def test_fit_enclosed_fill_basic():
    pairs = [
        {"input":  [[3, 3, 3], [3, 0, 3], [3, 3, 3]],
         "output": [[3, 3, 3], [3, 4, 3], [3, 3, 3]]},
        {"input":  [[0, 3, 3, 3], [0, 3, 0, 3], [0, 3, 3, 3]],
         "output": [[0, 3, 3, 3], [0, 3, 4, 3], [0, 3, 3, 3]]},
    ]
    prog = _fit_enclosed_fill(pairs)
    assert prog is not None
    assert prog[0][0] == "enclosed_fill"
    assert prog[0][1][1] == 4
    for p in pairs:
        assert run_program(prog, p["input"]) == p["output"]


# --- a hole-less task is NOT an enclosed-fill task (identity owns it) ----------

def test_no_pocket_declines():
    # No enclosed region anywhere -> declines (returns None), even though dims match.
    pairs = [{"input": [[0, 3], [3, 0]], "output": [[0, 3], [3, 0]]}]
    assert _fit_enclosed_fill(pairs) is None


# --- two divergent fill-colour tasks share ONE skeleton (lift into covers>1) ---

def test_two_fill_colours_share_skeleton():
    yellow = [
        {"input":  [[3, 3, 3], [3, 0, 3], [3, 3, 3]],
         "output": [[3, 3, 3], [3, 4, 3], [3, 3, 3]]},
    ]
    blue = [
        {"input":  [[2, 2, 2], [2, 0, 2], [2, 2, 2]],
         "output": [[2, 2, 2], [2, 1, 2], [2, 2, 2]]},
    ]
    a = _fit_enclosed_fill(yellow)
    b = _fit_enclosed_fill(blue)
    assert a is not None and b is not None
    # Different fitted colour leaves, but the SAME structural skeleton.
    assert a[0][1][1] != b[0][1][1]
    assert _program_skeleton(a) == _program_skeleton(b)


# --- reachable through the full search ----------------------------------------

def test_synthesize_task_finds_enclosed_fill():
    # Pair A is a closed box (interior pocket filled); pair B is an open 'C'
    # (right side open, nothing enclosed → output unchanged). A single marker-join
    # schema (connect) cannot satisfy both — on the open C it would still draw a
    # segment, changing the output — so only the enclosed-fill selection, which
    # paints *just* the sealed pocket, reproduces both pairs.
    pairs = [
        {"input":  [[3, 3, 3, 3], [3, 0, 0, 3], [3, 0, 0, 3], [3, 3, 3, 3]],
         "output": [[3, 3, 3, 3], [3, 4, 4, 3], [3, 4, 4, 3], [3, 3, 3, 3]]},
        {"input":  [[3, 3, 3, 3], [3, 0, 0, 0], [3, 0, 0, 0], [3, 3, 3, 3]],
         "output": [[3, 3, 3, 3], [3, 0, 0, 0], [3, 0, 0, 0], [3, 3, 3, 3]]},
    ]
    prog = synthesize_task(pairs)
    assert prog is not None
    assert prog[0][0] == "enclosed_fill"
