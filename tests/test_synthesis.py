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


def test_fractal_self_tile_discovered_by_search():
    # Output is the input self-tiled: an ih×iw macro grid whose macro-cell (R,C)
    # is a copy of the input iff the cell is non-background, else a blank block.
    # The selector ("which macro-cells get a copy") is found by search, not
    # hand-coded — the §2.5-2b "fill the variable by a grounded selector" case.
    pairs = [
        {"input": [[0, 1], [1, 0]],
         "output": [[0, 0, 0, 1],
                    [0, 0, 1, 0],
                    [0, 1, 0, 0],
                    [1, 0, 0, 0]]},
        {"input": [[2, 0], [2, 2]],
         "output": [[2, 0, 0, 0],
                    [2, 2, 0, 0],
                    [2, 0, 2, 0],
                    [2, 2, 2, 2]]},
    ]
    prog = synthesize_task(pairs)
    assert prog is not None
    assert prog[0][0] == "fractal"
    assert prog[0][1] == ("const", "nonbg")
    # transfers unchanged to a held-out input of a different size (P5)
    assert run_program(prog, [[5]]) == [[5]]
    assert run_program(prog, [[0, 0], [0, 0]]) == [[0, 0, 0, 0]] * 4


def test_fractal_declines_on_non_square_macro():
    # Output dims that are not exactly (ih², iw²) must not be read as a fractal.
    pairs = [
        {"input": [[1, 2]], "output": [[1, 1, 2, 2], [1, 1, 2, 2]]},  # this is a scale
    ]
    prog = synthesize_task(pairs)
    if prog is not None:
        assert prog[0][0] != "fractal"


def test_fractal_conditions_share_one_skeleton():
    # Two fractal tasks with divergent conditions (copy-where-nonbg vs
    # copy-where-bg) produce the SAME program skeleton (only the condition leaf
    # differs), so save_rule lifts them into ONE covers>1 rule rather than two
    # families. (≥2 distinct pairs each so the constant-output schema declines.)
    from agent.memory import _program_skeleton
    nonbg = synthesize_task([
        {"input": [[0, 1], [1, 0]],
         "output": [[0, 0, 0, 1], [0, 0, 1, 0], [0, 1, 0, 0], [1, 0, 0, 0]]},
        {"input": [[1, 0], [0, 1]],
         "output": [[1, 0, 0, 0], [0, 1, 0, 0], [0, 0, 1, 0], [0, 0, 0, 1]]},
    ])
    isbg = synthesize_task([
        {"input": [[0, 1], [1, 1]],
         "output": [[0, 1, 0, 0], [1, 1, 0, 0], [0, 0, 0, 0], [0, 0, 0, 0]]},
        {"input": [[1, 1], [1, 0]],
         "output": [[0, 0, 0, 0], [0, 0, 0, 0], [0, 0, 1, 1], [0, 0, 1, 0]]},
    ])
    assert nonbg is not None and isbg is not None
    assert nonbg[0][1] != isbg[0][1]  # different condition leaves
    assert _program_skeleton(nonbg) == _program_skeleton(isbg)


def test_fractal_copy_where_most_frequent_colour():
    # Copy the tile where the cell holds the UNIQUE most-frequent non-background
    # colour of THIS grid — a frequency selector, value-agnostic (the
    # distinguished colour varies per grid). Two pairs whose most-frequent colour
    # differs (3 then 2) are reproduced by the SAME `most` condition.
    pairs = [
        {"input": [[3, 1], [3, 0]],            # most-freq non-bg = 3
         "output": [[3, 1, 0, 0],
                    [3, 0, 0, 0],
                    [3, 1, 0, 0],
                    [3, 0, 0, 0]]},
        {"input": [[2, 2], [2, 5]],            # most-freq non-bg = 2
         "output": [[2, 2, 2, 2],
                    [2, 5, 2, 5],
                    [2, 2, 0, 0],
                    [2, 5, 0, 0]]},
    ]
    prog = synthesize_task(pairs)
    assert prog is not None and prog[0][0] == "fractal"
    assert prog[0][1] == ("const", "most")


def test_fractal_copy_where_least_frequent_colour():
    # The least-frequent non-background colour names the copied tiles. (bg=0 is
    # present so "least" is distinct from "nonbg"; two distinct pairs so the
    # constant-output schema declines.)
    pairs = [
        {"input": [[0, 1], [7, 7]],            # bg 0; least non-bg = 1 → (0,1)
         "output": [[0, 0, 0, 1],
                    [0, 0, 7, 7],
                    [0, 0, 0, 0],
                    [0, 0, 0, 0]]},
        {"input": [[7, 0], [1, 7]],            # bg 0; least non-bg = 1 → (1,0)
         "output": [[0, 0, 0, 0],
                    [0, 0, 0, 0],
                    [7, 0, 0, 0],
                    [1, 7, 0, 0]]},
    ]
    prog = synthesize_task(pairs)
    assert prog is not None and prog[0][0] == "fractal"
    assert prog[0][1] == ("const", "least")


def test_fractal_all_unconditional_self_tile():
    # Every macro-cell is a copy (the unconditional self-tile, even the bg=0
    # cells — so "all" is distinct from "nonbg"). Two distinct pairs so the
    # constant-output schema declines.
    pairs = [
        {"input": [[2, 0], [0, 2]],
         "output": [[2, 0, 2, 0],
                    [0, 2, 0, 2],
                    [2, 0, 2, 0],
                    [0, 2, 0, 2]]},
        {"input": [[5, 0], [5, 5]],
         "output": [[5, 0, 5, 0],
                    [5, 5, 5, 5],
                    [5, 0, 5, 0],
                    [5, 5, 5, 5]]},
    ]
    prog = synthesize_task(pairs)
    assert prog is not None and prog[0][0] == "fractal"
    assert prog[0][1] == ("const", "all")


def test_fractal_frequency_conditions_share_skeleton_with_nonbg():
    # most/least/all all share the one fractal skeleton, so a divergent-condition
    # task lifts into the SAME covers>1 rule via unify() (R3) — not a new family.
    from agent.memory import _program_skeleton
    base = [("fractal", ("const", "nonbg"))]
    for cond in ("most", "least", "all", "isbg"):
        variant = [("fractal", ("const", cond))]
        assert _program_skeleton(variant) == _program_skeleton(base)


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


# --- Schema 8: dihedral tiling (replication / mirror / rotation tiling) -------

def test_tile_plain_replication_discovered():
    # Output is a 2x2 macro grid of identical input copies. The input is 2x3 so
    # the output dims (4x6) are NOT (ih², iw²) — the fractal schema cannot fire,
    # and the search expresses it as one `tile` step of all-identity blocks.
    pairs = [
        {"input": [[1, 2, 0], [3, 4, 5]],
         "output": [[1, 2, 0, 1, 2, 0], [3, 4, 5, 3, 4, 5],
                    [1, 2, 0, 1, 2, 0], [3, 4, 5, 3, 4, 5]]},
        {"input": [[5, 0, 6], [0, 6, 1]],
         "output": [[5, 0, 6, 5, 0, 6], [0, 6, 1, 0, 6, 1],
                    [5, 0, 6, 5, 0, 6], [0, 6, 1, 0, 6, 1]]},
    ]
    prog = synthesize_task(pairs)
    assert prog is not None and prog[0][0] == "tile"
    k, m, pat = prog[0][1][1], prog[0][2][1], prog[0][3][1]
    assert (k, m) == (2, 2)
    assert all(name == "identity" for row in pat for name in row)
    for p in pairs:
        assert run_program(prog, p["input"]) == p["output"]


def test_tile_mirror_arrangement_discovered():
    # The kaleidoscope family: top-left identity, top-right horizontal mirror,
    # bottom-left vertical mirror, bottom-right 180° — a value-agnostic rigid
    # arrangement, never a colour literal.
    g = [[1, 2], [3, 4]]
    out = [[1, 2, 2, 1],
           [3, 4, 4, 3],
           [3, 4, 4, 3],
           [1, 2, 2, 1]]
    g2 = [[7, 8], [9, 5]]
    out2 = [[7, 8, 8, 7],
            [9, 5, 5, 9],
            [9, 5, 5, 9],
            [7, 8, 8, 7]]
    prog = synthesize_task([{"input": g, "output": out},
                            {"input": g2, "output": out2}])
    assert prog is not None and prog[0][0] == "tile"
    pat = prog[0][3][1]
    assert pat[0][0] == "identity" and pat[0][1] == "flip_h"
    assert pat[1][0] == "flip_v" and pat[1][1] == "rot180"
    for inp, o in [(g, out), (g2, out2)]:
        assert run_program(prog, inp) == o


def test_tile_declines_on_non_multiple_dims():
    # Output dims that are not an integer multiple of the input dims are not a
    # tiling — the schema must decline (here a same-size recolour).
    pairs = [
        {"input": [[1, 2], [3, 4]], "output": [[2, 1], [4, 3]]},
        {"input": [[5, 6], [7, 8]], "output": [[6, 5], [8, 7]]},
    ]
    prog = synthesize_task(pairs)
    if prog:
        assert prog[0][0] != "tile"


def test_tile_arrangements_share_one_skeleton():
    # The unification payoff: a 2x2 mirror tiling and a 1x2 plain tiling must
    # produce the SAME program skeleton (k/m/pattern are the only divergent
    # leaves), so save_rule lifts them into ONE covers>1 rule (R3) rather than
    # accreting one rule per arrangement.
    from agent.memory import _program_skeleton
    mirror = synthesize_task([
        {"input": [[1, 2], [3, 4]],
         "output": [[1, 2, 2, 1], [3, 4, 4, 3],
                    [3, 4, 4, 3], [1, 2, 2, 1]]},
        {"input": [[7, 8], [9, 5]],
         "output": [[7, 8, 8, 7], [9, 5, 5, 9],
                    [9, 5, 5, 9], [7, 8, 8, 7]]},
    ])
    plain = synthesize_task([
        {"input": [[1, 2], [3, 4]],
         "output": [[1, 2, 1, 2], [3, 4, 3, 4]]},
        {"input": [[5, 0], [0, 6]],
         "output": [[5, 0, 5, 0], [0, 6, 0, 6]]},
    ])
    assert mirror is not None and plain is not None
    assert mirror[0][0] == "tile" and plain[0][0] == "tile"
    assert mirror[0][3][1] != plain[0][3][1]  # different arrangements
    assert _program_skeleton(mirror) == _program_skeleton(plain)


# --- Schema 9: symmetry completion -------------------------------------------

def test_symfill_restores_vertical_mirror_hole():
    # Same-dims output = the input with its background holes filled from the
    # grid's own symmetry. Here the visible top is mirrored to fill the bg bottom
    # (vertical symmetry). The symmetry set is read from the grid, not hand-coded.
    pairs = [
        {"input":  [[4, 4], [3, 5], [0, 0], [0, 0]],
         "output": [[4, 4], [3, 5], [3, 5], [4, 4]]},
        {"input":  [[7, 1], [2, 2], [0, 0], [0, 0]],
         "output": [[7, 1], [2, 2], [2, 2], [7, 1]]},
    ]
    prog = synthesize_task(pairs)
    assert prog is not None and prog[0][0] == "symfill"
    assert "flip_v" in prog[0][1][1]
    # transfers unchanged to a held-out input (P5)
    assert run_program(prog, [[9, 8], [6, 6], [0, 0], [0, 0]]) == \
        [[9, 8], [6, 6], [6, 6], [9, 8]]


def test_symfill_declines_when_not_symmetry_completion():
    # A same-dims edit that is NOT a symmetry completion (an arbitrary recolour of
    # a cell) must not be read as symfill — the fitted symmetry set would not
    # reproduce the output, so the schema declines (and a colour-map schema may
    # claim it instead).
    pairs = [
        {"input":  [[1, 2], [3, 4]],
         "output": [[1, 2], [3, 9]]},
        {"input":  [[5, 6], [7, 8]],
         "output": [[5, 6], [7, 9]]},
    ]
    prog = synthesize_task(pairs)
    if prog is not None:
        assert prog[0][0] != "symfill"


def test_symfill_sets_share_one_skeleton():
    # Two completion tasks with DIFFERENT symmetry sets produce the same one-step
    # skeleton (only the const set leaf differs), so save_rule lifts them into ONE
    # covers>1 rule rather than two families (R3 — P1·P2·P3 rise together).
    from agent.memory import _program_skeleton
    vmirror = synthesize_task([
        {"input":  [[4, 4], [3, 5], [0, 0], [0, 0]],
         "output": [[4, 4], [3, 5], [3, 5], [4, 4]]},
        {"input":  [[7, 1], [2, 2], [0, 0], [0, 0]],
         "output": [[7, 1], [2, 2], [2, 2], [7, 1]]},
    ])
    hmirror = synthesize_task([
        {"input":  [[4, 3, 0, 0], [5, 2, 0, 0]],
         "output": [[4, 3, 3, 4], [5, 2, 2, 5]]},
        {"input":  [[7, 1, 0, 0], [8, 6, 0, 0]],
         "output": [[7, 1, 1, 7], [8, 6, 6, 8]]},
    ])
    assert vmirror is not None and hmirror is not None
    assert vmirror[0][0] == "symfill" and hmirror[0][0] == "symfill"
    assert vmirror[0][1] != hmirror[0][1]  # different symmetry sets
    assert _program_skeleton(vmirror) == _program_skeleton(hmirror)


# --- Schema 10: two-panel boolean combine ------------------------------------

def test_boolcombine_and_two_vertical_panels():
    # Two equal panels separated by a uniform column; output = paint (colour 2)
    # where BOTH panels are non-background (the `and` combine). Composes only
    # make_grid + coloring, and the program transfers to a held-out input.
    pairs = [
        {"input":  [[1, 0, 5, 0, 1], [0, 1, 5, 1, 1]],
         "output": [[0, 0], [0, 2]]},
        {"input":  [[1, 1, 5, 0, 1], [0, 0, 5, 0, 0]],
         "output": [[0, 2], [0, 0]]},
    ]
    prog = synthesize_task(pairs)
    assert prog is not None and prog[0][0] == "boolcombine"
    # held-out input: left&right both on only at (0,0)
    held = [[1, 0, 5, 1, 0], [0, 0, 5, 1, 1]]
    assert run_program(prog, held) == [[2, 0], [0, 0]]


def test_boolcombine_xor_horizontal_panels():
    # Two stacked panels separated by a uniform row; output = paint where EXACTLY
    # ONE panel is on (xor). The paint colour (3) differs from both panels'
    # colours — the combine is value-agnostic (occupancy, not colour).
    pairs = [
        {"input":  [[1, 0], [0, 1], [4, 4], [0, 2], [0, 2]],
         "output": [[1, 1], [0, 0]]},
        {"input":  [[2, 2], [0, 0], [4, 4], [0, 2], [2, 0]],
         "output": [[1, 0], [1, 0]]},
    ]
    # colour fitted from the outputs: pair0 paints colour 1, pair1 paints colour 1
    prog = synthesize_task(pairs)
    assert prog is not None and prog[0][0] == "boolcombine"
    axis, op, color = prog[0][1][1]
    assert axis == "h" and op == "xor"


def test_boolcombine_declines_non_panel_task():
    # A same-dims recolour is not a two-panel combine (its output is not half the
    # input), so the boolcombine schema must not claim it.
    pairs = [
        {"input": [[1, 1], [1, 1]], "output": [[2, 2], [2, 2]]},
        {"input": [[3, 3], [3, 3]], "output": [[2, 2], [2, 2]]},
    ]
    prog = synthesize_task(pairs)
    if prog is not None:
        assert prog[0][0] != "boolcombine"


def test_boolcombine_colour_preserving_merge():
    # Two stacked panels; output = overlay A over B keeping each panel's OWN
    # colour (not a third fixed paint colour). The merge is value-agnostic — it
    # reads the panel cells' colours — and shares the boolcombine skeleton so it
    # folds into the same family rather than minting a new one.
    pairs = [
        {"input":  [[3, 0], [0, 7], [4, 4], [0, 5], [6, 0]],
         "output": [[3, 5], [6, 7]]},
        {"input":  [[0, 2], [8, 0], [4, 4], [1, 0], [0, 9]],
         "output": [[1, 2], [8, 9]]},
    ]
    prog = synthesize_task(pairs)
    assert prog is not None and prog[0][0] == "boolcombine"
    axis, op, color = prog[0][1][1]
    assert op in ("A_over_B", "B_over_A") and color is None
    # held-out: overlay keeps each non-bg colour through to the result
    held = [[2, 0], [0, 3], [4, 4], [0, 8], [5, 0]]
    assert run_program(prog, held) == [[2, 8], [5, 3]]


def test_boolcombine_auto_axis_varies_across_pairs():
    # A task whose split orientation VARIES across pairs (duplicated panels
    # side-by-side in one pair, stacked in another): no single shared axis exists,
    # so the axis is lifted to the structural selector "auto" — resolved per input
    # — and only the (op, colour) pair is shared. Models 7b7f7511. The fitter is
    # exercised directly because such "duplicated panels" grids are also reachable
    # by earlier object-based schemas; the point under test is that _fit_boolcombine
    # still fits via the auto axis when the per-pair axes diverge.
    from program.synthesis import _fit_boolcombine
    pairs = [
        # 2x4, two identical 2x2 panels side-by-side -> keep one (v split)
        {"input":  [[1, 2, 1, 2], [3, 4, 3, 4]],
         "output": [[1, 2], [3, 4]]},
        # 4x2, two identical 2x2 panels stacked -> keep one (h split)
        {"input":  [[5, 6], [7, 8], [5, 6], [7, 8]],
         "output": [[5, 6], [7, 8]]},
    ]
    prog = _fit_boolcombine(pairs)
    assert prog is not None and prog[0][0] == "boolcombine"
    axis, op, color = prog[0][1][1]
    assert axis == "auto"
    # held-out: a stacked-panel input is split structurally along the right axis
    held = [[9, 1], [2, 3], [9, 1], [2, 3]]
    assert run_program(prog, held) == [[9, 1], [2, 3]]


def test_boolcombine_tasks_share_one_skeleton():
    # Two combine tasks with DIFFERENT (axis, op, colour) triples produce the same
    # one-step skeleton (only the const triple leaf differs), so save_rule lifts
    # them into ONE covers>1 rule rather than two families (R3).
    from agent.memory import _program_skeleton
    and_v = synthesize_task([
        {"input":  [[1, 0, 5, 0, 1], [0, 1, 5, 1, 1]],
         "output": [[0, 0], [0, 2]]},
        {"input":  [[1, 1, 5, 0, 1], [0, 0, 5, 0, 0]],
         "output": [[0, 2], [0, 0]]},
    ])
    or_h = synthesize_task([
        {"input":  [[1, 0], [0, 0], [4, 4], [0, 2], [0, 0]],
         "output": [[7, 7], [0, 0]]},
        {"input":  [[0, 0], [2, 0], [4, 4], [0, 0], [2, 2]],
         "output": [[0, 0], [7, 7]]},
    ])
    assert and_v is not None and or_h is not None
    assert and_v[0][0] == "boolcombine" and or_h[0][0] == "boolcombine"
    assert and_v[0][1] != or_h[0][1]  # different triples
    assert _program_skeleton(and_v) == _program_skeleton(or_h)


def test_connect_same_colour_markers_in_own_colour():
    # Two markers of the same colour aligned in a row/column are joined by filling
    # the background gap between them, in the marker's OWN colour. Composes only
    # `coloring`, and the program transfers to a held-out input.
    pairs = [
        {"input":  [[0, 0, 0, 0, 0],
                    [3, 0, 0, 0, 3],
                    [0, 0, 0, 0, 0]],
         "output": [[0, 0, 0, 0, 0],
                    [3, 3, 3, 3, 3],
                    [0, 0, 0, 0, 0]]},
        {"input":  [[2, 0, 0],
                    [0, 0, 0],
                    [2, 0, 0]],
         "output": [[2, 0, 0],
                    [2, 0, 0],
                    [2, 0, 0]]},
    ]
    prog = synthesize_task(pairs)
    assert prog is not None and prog[0][0] == "connect"
    assert prog[0][1] == ("const", "same")
    held = [[0, 0, 0, 0],
            [4, 0, 0, 4],
            [0, 0, 0, 0]]
    assert run_program(prog, held) == [[0, 0, 0, 0],
                                       [4, 4, 4, 4],
                                       [0, 0, 0, 0]]


def test_connect_fixed_line_colour():
    # The joining segment is painted in a FIXED colour (here 5) distinct from the
    # markers' colour — the line-colour spec is the per-task const leaf. The
    # second row's background stays 0, so this is NOT a global recolour (only the
    # gap between aligned markers is filled).
    pairs = [
        {"input":  [[3, 0, 0, 0, 3],
                    [0, 0, 0, 0, 0]],
         "output": [[3, 5, 5, 5, 3],
                    [0, 0, 0, 0, 0]]},
        {"input":  [[8, 0, 0, 8],
                    [0, 0, 0, 0]],
         "output": [[8, 5, 5, 8],
                    [0, 0, 0, 0]]},
    ]
    prog = synthesize_task(pairs)
    assert prog is not None and prog[0][0] == "connect"
    assert prog[0][1] == ("const", 5)


def test_connect_declines_when_no_alignment():
    # Markers that share neither a row nor a column have nothing to join, so the
    # connect schema must not fabricate a segment (honest miss / identity).
    pairs = [
        {"input":  [[3, 0, 0], [0, 0, 0], [0, 0, 2]],
         "output": [[3, 0, 0], [0, 0, 0], [0, 0, 2]]},
    ]
    prog = synthesize_task(pairs)
    if prog:
        assert prog[0][0] != "connect"


def test_connect_tasks_share_one_skeleton():
    # An own-colour connect and a fixed-colour connect produce the SAME one-step
    # skeleton (only the const line-colour leaf differs), so save_rule lifts them
    # into ONE covers>1 rule rather than two families (R3).
    from agent.memory import _program_skeleton
    same = synthesize_task([
        {"input":  [[3, 0, 0, 3]], "output": [[3, 3, 3, 3]]},
        {"input":  [[2, 0, 2]],    "output": [[2, 2, 2]]},
    ])
    fixed = synthesize_task([
        {"input":  [[3, 0, 0, 0, 3], [0, 0, 0, 0, 0]],
         "output": [[3, 5, 5, 5, 3], [0, 0, 0, 0, 0]]},
        {"input":  [[8, 0, 0, 8], [0, 0, 0, 0]],
         "output": [[8, 5, 5, 8], [0, 0, 0, 0]]},
    ])
    assert same is not None and fixed is not None
    assert same[0][0] == "connect" and fixed[0][0] == "connect"
    assert same[0][1] != fixed[0][1]  # different line-colour leaves
    assert _program_skeleton(same) == _program_skeleton(fixed)


def test_crop_content_bounding_box():
    # The output is the bounding box of all non-background content, discovered by
    # the value-agnostic `content` selector — and the same selector crops a
    # held-out input unchanged (P5).
    pairs = [
        {"input":  [[0, 0, 0, 0],
                    [0, 3, 3, 0],
                    [0, 3, 3, 0],
                    [0, 0, 0, 0]],
         "output": [[3, 3], [3, 3]]},
        {"input":  [[0, 0, 0],
                    [0, 7, 0],
                    [0, 0, 0]],
         "output": [[7]]},
    ]
    prog = synthesize_task(pairs)
    assert prog == [("crop", ("const", "content"))]
    held = [[0, 0, 0, 0, 0],
            [0, 0, 5, 5, 0],
            [0, 0, 0, 0, 0]]
    assert run_program(prog, held) == [[5, 5]]


def test_crop_to_largest_colour_aware_object():
    # Two same-colour regions of different size; the output is the bounding box of
    # the LARGER one. The selector reads colour-aware objects (`same_color`), so a
    # 2x2 red block beats a single blue cell — value-agnostic, never a literal box.
    pairs = [
        {"input":  [[2, 0, 0, 0],
                    [0, 0, 4, 4],
                    [0, 0, 4, 4]],
         "output": [[4, 4], [4, 4]]},
        {"input":  [[0, 0, 8],
                    [3, 3, 0],
                    [3, 3, 0]],
         "output": [[3, 3], [3, 3]]},
    ]
    prog = synthesize_task(pairs)
    assert prog == [("crop", ("const", "largest"))]


def test_crop_declines_when_output_not_a_subgrid():
    # An output that is not any bounding-box crop of the input → the crop schema
    # declines (the search reports an honest miss, never a literal fit).
    pairs = [
        {"input":  [[1, 2], [3, 4]],
         "output": [[9, 9], [9, 9]]},
    ]
    prog = synthesize_task(pairs)
    assert prog is None or prog[0][0] != "crop"


def test_crop_selectors_share_one_skeleton():
    # A content-crop and an object-selected crop produce the SAME one-step
    # skeleton (only the const selector leaf differs), so save_rule lifts them into
    # ONE covers>1 rule rather than a family per selector (R3).
    from agent.memory import _program_skeleton
    content = synthesize_task([
        {"input": [[0, 0, 0], [0, 6, 0], [0, 0, 0]], "output": [[6]]},
        {"input": [[0, 0], [0, 9]], "output": [[9]]},
    ])
    largest = synthesize_task([
        {"input":  [[2, 0, 0, 0],
                    [0, 0, 4, 4],
                    [0, 0, 4, 4]],
         "output": [[4, 4], [4, 4]]},
        {"input":  [[0, 0, 8],
                    [3, 3, 0],
                    [3, 3, 0]],
         "output": [[3, 3], [3, 3]]},
    ])
    assert content is not None and largest is not None
    assert content[0][0] == "crop" and largest[0][0] == "crop"
    assert content[0][1] != largest[0][1]  # different selector leaves
    assert _program_skeleton(content) == _program_skeleton(largest)
