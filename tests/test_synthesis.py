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
