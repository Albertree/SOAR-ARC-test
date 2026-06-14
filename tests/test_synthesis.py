"""
Tests for the bounded Slow-path program synthesizer (program/synthesis.py).

These prove the general search REDISCOVERS, from the two frozen primitives only,
the program shapes the hand-coded families special-case — and that a program
synthesized from the train pairs transfers unchanged to a held-out input (the
P5 property: every variable originates in G0). They also pin the honest-miss
contract: a transformation outside the bounded grammar yields None, never a
literal per-pair overfit.
"""

import json
import os

from program.synthesis import run_program, synthesize_task


REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _load(path):
    with open(os.path.join(REPO, path)) as fh:
        return json.load(fh)


# --- run_program: the evaluator composes only make_grid + coloring -----------

def test_empty_program_is_identity():
    g = [[0, 1], [2, 0]]
    assert run_program([], g) == g


def test_make_grid_then_coloring_builds_output():
    prog = [
        ("make_grid", ("const", 2), ("const", 2), ("const", 0)),
        ("coloring", ("const", [(0, 0), (1, 1)]), ("const", 5)),
    ]
    assert run_program(prog, [[9]]) == [[5, 0], [0, 5]]


def test_paint_objects_reconstructs_input_objects():
    # A blank canvas of the input size, then every input object repainted in its
    # own colour at its own position == the input itself.
    g = [[0, 3, 0], [0, 3, 0], [7, 0, 0]]
    prog = [
        ("make_grid", ("in_h",), ("in_w",), ("bg",)),
        ("paint_objects", ("all_objects",)),
    ]
    assert run_program(prog, g) == g


# --- synthesize_task: the search finds a general program ---------------------

def test_synthesizes_identity_task():
    pairs = [
        {"input": [[1, 0], [0, 2]], "output": [[1, 0], [0, 2]]},
        {"input": [[0, 3], [4, 0]], "output": [[0, 3], [4, 0]]},
    ]
    prog = synthesize_task(pairs)
    assert prog is not None
    # Transfers to a held-out input.
    held = [[5, 5], [0, 6]]
    assert run_program(prog, held) == held


def test_synthesizes_constant_output_task_by_search():
    # easy000a is a constant-output task (all train outputs identical). The
    # synthesizer must rediscover rule_001's copy_common_output as an explicit
    # make_grid + coloring program, purely by search.
    task = _load("data/ARC_easy_a/easy000a.json")
    pairs = task["train"]
    prog = synthesize_task(pairs)
    assert prog is not None, "constant-output task should be synthesizable"
    common = pairs[0]["output"]
    # The program reproduces the common output regardless of which input it runs
    # on — including the test input (input-independent transformation).
    for p in pairs:
        assert run_program(prog, p["input"]) == common
    test_in = task["test"][0]["input"]
    assert run_program(prog, test_in) == common
    # First step must be make_grid (a fresh canvas), the rest colorings — i.e. a
    # composition of exactly the two frozen primitives, no third vocabulary.
    assert prog[0][0] == "make_grid"
    assert all(step[0] == "coloring" for step in prog[1:])


def test_synthesizes_recolor_to_blank_canvas():
    # Output = the input's objects laid on a blank (all-zero) canvas of the same
    # size. With a 0-background input this equals the input, but the program is
    # the general object-reconstruction one, not a literal copy.
    pairs = [
        {"input": [[0, 2, 0], [0, 2, 0]], "output": [[0, 2, 0], [0, 2, 0]]},
        {"input": [[6, 0, 0], [6, 0, 0]], "output": [[6, 0, 0], [6, 0, 0]]},
    ]
    prog = synthesize_task(pairs)
    assert prog is not None
    held = [[0, 0, 8], [0, 0, 8]]
    assert run_program(prog, held) == held


def test_honest_miss_on_object_move():
    # A single pixel that MOVES (corner-to-centre): outside the bounded grammar
    # (no target-fitting schema yet). The synthesizer must return None rather
    # than fabricate a literal per-pair program.
    pairs = [
        {"input": [[5, 0, 0], [0, 0, 0], [0, 0, 0]],
         "output": [[0, 0, 0], [0, 5, 0], [0, 0, 0]]},
        {"input": [[3, 0, 0], [0, 0, 0], [0, 0, 0]],
         "output": [[0, 0, 0], [0, 3, 0], [0, 0, 0]]},
    ]
    assert synthesize_task(pairs) is None


def test_no_pairs_returns_none():
    assert synthesize_task([]) is None


# --- Schema 5: dihedral geometric transform (flip / rotate / transpose) ------

def test_dihedral_flip_h_discovered_by_search():
    # A whole-grid horizontal mirror — value-agnostic, no colour changes. The
    # search must express it as a single `dihedral('flip_h')` step (a coordinate
    # expression composing the frozen `make_grid`+`coloring`, NOT a new
    # primitive) and transfer unchanged to a held-out input (P5).
    pairs = [
        {"input": [[1, 2, 0], [0, 3, 0]], "output": [[0, 2, 1], [0, 3, 0]]},
        {"input": [[4, 0, 5]], "output": [[5, 0, 4]]},
    ]
    prog = synthesize_task(pairs)
    assert prog is not None
    assert prog[0][0] == "dihedral" and prog[0][1] == ("const", "flip_h")
    held = [[7, 0, 0, 8]]
    assert run_program(prog, held) == [[8, 0, 0, 7]]


def test_dihedral_transpose_swaps_canvas_dims():
    # Transpose is a dims-swapping map: the fitted canvas must be in_w x in_h.
    pairs = [
        {"input": [[1, 2, 3], [4, 5, 6]],
         "output": [[1, 4], [2, 5], [3, 6]]},
        {"input": [[7, 8]], "output": [[7], [8]]},
    ]
    prog = synthesize_task(pairs)
    assert prog is not None
    assert prog[0][0] == "dihedral" and prog[0][1] == ("const", "transpose")
    # transfers to a held-out 1x3 -> 3x1
    assert run_program(prog, [[9, 0, 2]]) == [[9], [0], [2]]


def test_dihedral_rot180_discovered():
    pairs = [
        {"input": [[1, 0], [0, 2]], "output": [[2, 0], [0, 1]]},
        {"input": [[3, 4, 0]], "output": [[0, 4, 3]]},
    ]
    prog = synthesize_task(pairs)
    assert prog is not None and prog[0][1] == ("const", "rot180")


def test_dihedral_does_not_fire_on_non_symmetric():
    # An arbitrary recolour-and-move that is no dihedral transform must not be
    # mislabelled as one (honest miss for this schema; another schema may still
    # decline too -> None overall, never a fabricated map).
    pairs = [
        {"input": [[1, 0, 0], [0, 0, 0]], "output": [[0, 0, 0], [0, 0, 7]]},
        {"input": [[2, 0, 0], [0, 0, 0]], "output": [[0, 0, 0], [0, 0, 8]]},
    ]
    prog = synthesize_task(pairs)
    # no dihedral map reproduces this; the schema declines
    if prog is not None:
        assert prog[0][0] != "dihedral"


def test_swap_and_nonswap_dihedral_share_one_skeleton():
    # The unification payoff: a non-swap map (flip_h) and a dims-swapping map
    # (transpose) must produce the SAME program skeleton, so save_rule lifts them
    # into ONE covers>1 rule instead of two families (the canvas-dim difference
    # now lives inside the single `dihedral` step, not in a separate make_grid).
    from agent.memory import _program_skeleton
    flip = synthesize_task([
        {"input": [[1, 2, 0], [0, 3, 0]], "output": [[0, 2, 1], [0, 3, 0]]},
        {"input": [[4, 0, 5]], "output": [[5, 0, 4]]},
    ])
    transpose = synthesize_task([
        {"input": [[1, 2, 3], [4, 5, 6]], "output": [[1, 4], [2, 5], [3, 6]]},
        {"input": [[7, 8]], "output": [[7], [8]]},
    ])
    assert flip is not None and transpose is not None
    assert flip[0][1] != transpose[0][1]  # different map leaves
    assert _program_skeleton(flip) == _program_skeleton(transpose)


# --- Schema 6: pixel scaling (block upsample) --------------------------------

def test_scale_2x_discovered_by_search():
    # Every cell blown up to a 2x2 block of its own colour — a value-agnostic
    # coordinate expression composing the frozen primitives, not a new one.
    pairs = [
        {"input": [[1, 2]], "output": [[1, 1, 2, 2], [1, 1, 2, 2]]},
        {"input": [[3, 0], [0, 4]],
         "output": [[3, 3, 0, 0], [3, 3, 0, 0],
                    [0, 0, 4, 4], [0, 0, 4, 4]]},
    ]
    prog = synthesize_task(pairs)
    assert prog is not None
    assert prog[0][0] == "scale"
    assert prog[0][1] == ("const", 2) and prog[0][2] == ("const", 2)
    # transfers unchanged to a held-out input (P5)
    assert run_program(prog, [[5]]) == [[5, 5], [5, 5]]


def test_scale_non_square_factors():
    # Distinct row/col factors (rh=2, rw=3) must both be fitted.
    pairs = [
        {"input": [[7]], "output": [[7, 7, 7], [7, 7, 7]]},
        {"input": [[1, 2]],
         "output": [[1, 1, 1, 2, 2, 2], [1, 1, 1, 2, 2, 2]]},
    ]
    prog = synthesize_task(pairs)
    assert prog is not None and prog[0][0] == "scale"
    assert prog[0][1] == ("const", 2) and prog[0][2] == ("const", 3)


def test_scale_declines_on_non_integer_multiple():
    # Output dims that are not an integer multiple of the input must not be
    # mislabelled as a scale (honest miss for this schema).
    pairs = [
        {"input": [[1, 2, 3]], "output": [[1, 2, 3, 0, 0]]},
    ]
    prog = synthesize_task(pairs)
    if prog is not None:
        assert prog[0][0] != "scale"


def test_scale_factors_share_one_skeleton():
    # The unification payoff: a 2x and a 3x scale must produce the SAME program
    # skeleton (factors are the only divergent leaves), so save_rule lifts them
    # into ONE covers>1 rule rather than two families.
    # (≥2 distinct pairs each, so the constant-output schema declines and the
    # scale schema is what fires.)
    from agent.memory import _program_skeleton
    two = synthesize_task([
        {"input": [[1, 2]], "output": [[1, 1, 2, 2], [1, 1, 2, 2]]},
        {"input": [[3]], "output": [[3, 3], [3, 3]]},
    ])
    three = synthesize_task([
        {"input": [[1]], "output": [[1, 1, 1], [1, 1, 1], [1, 1, 1]]},
        {"input": [[5, 6]],
         "output": [[5, 5, 5, 6, 6, 6], [5, 5, 5, 6, 6, 6],
                    [5, 5, 5, 6, 6, 6]]},
    ])
    assert two is not None and three is not None
    assert two[0][1] != three[0][1]  # different factor leaves
    assert _program_skeleton(two) == _program_skeleton(three)
