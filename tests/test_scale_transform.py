"""Tests for the whole-grid *scale / replicate* family.

A new transformation family expressed as an *argument expression* over the two
frozen primitives (`make_grid` + `coloring` at a replicated coordinate) — F3-exempt
(no new DSL primitive: the scale/factor are arguments, not a new `def`). Mirrors
the geometric-transform family: a recognition vocabulary (`SCALE_VOCAB`), an
analyzer (`analyze_scale_transform`), a matcher (`agent/conditions/scale_transform`),
and a renderer (`render_scale_transform`) that shares the back-map with the analyzer
so they agree by construction.

Two modes, both with output dims (H*kh, W*kw):
  - "block" — each input cell → a kh×kw solid block  (in[r//kh][c//kw])
  - "tile"  — the whole grid repeated kh×kw           (in[r%H ][c%W ])

This slice learns a *constant* factor (the cross-pair COMM); a factor read off an
input property is a separate next step, on which the analyzer deliberately abstains.
Grounds four real ARC-AGI-2 tasks (60c09cac, 9172f3a0, c59eb873 block; a416b8f3
tile) plus the madeup block-upscale task.
"""

from types import SimpleNamespace

from agent.dsl_expr.selection import (
    apply_scale,
    analyze_scale_transform,
    SCALE_VOCAB,
    SCALE_BACKMAP,
    SCALE_FACTOR_VOCAB,
)
from agent.dsl_expr.render import render_scale_transform
from agent.conditions import match as match_condition


def _pair(inp, out):
    return SimpleNamespace(
        input_grid=SimpleNamespace(raw=inp),
        output_grid=SimpleNamespace(raw=out),
    )


GRID = [[0, 3, 0], [3, 3, 0], [0, 0, 2]]


def test_vocab_has_both_modes():
    assert SCALE_VOCAB == ["block", "tile"]
    assert set(SCALE_BACKMAP) == {"block", "tile"}


def test_apply_scale_block_upscale():
    # factor (2,2) block: each cell becomes a 2x2 block.
    out = apply_scale(GRID, "block", 2, 2)
    assert len(out) == 6 and len(out[0]) == 6
    assert out[0][:2] == [0, 0]
    assert out[2][:2] == [3, 3]  # the (1,0)=3 cell's block
    assert out[4][4:] == [2, 2]  # the (2,2)=2 cell's block


def test_apply_scale_tile_repeats_whole_grid():
    out = apply_scale(GRID, "tile", 2, 2)
    assert len(out) == 6 and len(out[0]) == 6
    # the whole 3x3 grid appears unchanged in each quadrant
    assert [row[:3] for row in out[:3]] == GRID
    assert [row[3:] for row in out[:3]] == GRID
    assert [row[:3] for row in out[3:]] == GRID


def test_block_and_tile_differ_on_nonuniform_grid():
    # the two modes are genuinely distinct (not aliases)
    assert apply_scale(GRID, "block", 2, 2) != apply_scale(GRID, "tile", 2, 2)


def test_render_matches_apply_block_and_tile():
    # the renderer (make_grid + coloring) reproduces the recognition back-map
    for mode in SCALE_VOCAB:
        assert render_scale_transform(GRID, mode, 3, 3) == apply_scale(GRID, mode, 3, 3)
    # non-square factor too
    assert render_scale_transform(GRID, "tile", 1, 2) == apply_scale(GRID, "tile", 1, 2)


def test_analyzer_learns_constant_block_factor():
    # two value-different pairs that are both block x2
    p1 = _pair([[1, 0], [0, 2]], apply_scale([[1, 0], [0, 2]], "block", 2, 2))
    p2 = _pair([[0, 7, 0], [7, 7, 0]], apply_scale([[0, 7, 0], [7, 7, 0]], "block", 2, 2))
    sig = analyze_scale_transform([p1, p2])
    assert sig["valid_all"] is True
    assert sig["mode"] == "block"
    assert sig["factor"] == (2, 2)
    assert match_condition("scale_transform", {"scale_transform": sig}, {"min_evidence": 2})


def test_analyzer_learns_tile_factor():
    p1 = _pair([[3, 0], [0, 4]], apply_scale([[3, 0], [0, 4]], "tile", 1, 2))
    p2 = _pair([[5, 6]], apply_scale([[5, 6]], "tile", 1, 2))
    sig = analyze_scale_transform([p1, p2])
    assert sig["valid_all"] is True
    assert sig["mode"] == "tile"
    assert sig["factor"] == (1, 2)


def test_analyzer_abstains_on_varying_factor():
    # a factor that changes across pairs (the §2.5-2b factor-reading case) is NOT a
    # constant COMM, so this slice abstains rather than guessing.
    p1 = _pair([[1, 0], [0, 2]], apply_scale([[1, 0], [0, 2]], "block", 2, 2))
    p2 = _pair([[1, 0], [0, 2]], apply_scale([[1, 0], [0, 2]], "block", 3, 3))
    sig = analyze_scale_transform([p1, p2])
    assert sig["valid_all"] is False
    assert sig["mode"] is None


def test_analyzer_abstains_on_same_size_task():
    # a same-size recolor must never be claimed by the scale family (factor (1,1)).
    p1 = _pair([[1, 1], [2, 2]], [[3, 3], [4, 4]])
    sig = analyze_scale_transform([p1, p1])
    assert sig["valid_all"] is False
    assert sig["mode"] is None
    assert not match_condition("scale_transform", {"scale_transform": sig}, {"min_evidence": 2})


def test_analyzer_abstains_on_non_integer_ratio():
    # output not an integer multiple of input → abstain.
    p1 = _pair([[1, 1, 1]], [[1, 1, 1, 1, 1]])
    sig = analyze_scale_transform([p1, p1])
    assert sig["mode"] is None


# --- §2.5-2b factor-axis lift: factor read off an input property ------------

def test_factor_vocab_reads_distinct_color_count():
    f = SCALE_FACTOR_VOCAB["distinct_color_count"]
    assert f([[0, 3, 0], [3, 0, 8], [0, 8, 0]]) == 2   # {3, 8}
    assert f([[6, 0, 4], [0, 2, 0], [4, 0, 6]]) == 3   # {6, 4, 2}, 0 ignored


def test_factor_vocab_grid_side_square_only():
    f = SCALE_FACTOR_VOCAB["grid_side"]
    assert f([[1, 2], [3, 4]]) == 2
    assert f([[1, 2, 3]]) is None                       # non-square abstains


def test_analyzer_learns_block_factor_from_color_count():
    # factor varies per pair (2, 3) and equals the input's distinct-colour count:
    # the constant path abstains, the factor-axis lift recognises the property read.
    a1 = [[0, 3, 0], [3, 0, 8], [0, 8, 0]]              # 2 colours -> x2
    a2 = [[6, 0, 4], [0, 2, 0], [4, 0, 6]]              # 3 colours -> x3
    p1 = _pair(a1, apply_scale(a1, "block", 2, 2))
    p2 = _pair(a2, apply_scale(a2, "block", 3, 3))
    sig = analyze_scale_transform([p1, p2])
    assert sig["valid_all"] is True
    assert sig["mode"] == "block"
    assert sig["factor"] is None
    assert sig["factor_expr"] == "distinct_color_count"
    assert match_condition("scale_transform", {"scale_transform": sig}, {"min_evidence": 2})


def test_analyzer_learns_tile_factor_from_grid_side():
    # ccd554ac-shape: a square grid tiled by its own side (2x2->x2, 3x3->x3).
    a1 = [[5, 0], [0, 5]]                                # side 2 -> x2
    a2 = [[7, 0, 7], [0, 7, 0], [7, 0, 0]]              # side 3 -> x3
    p1 = _pair(a1, apply_scale(a1, "tile", 2, 2))
    p2 = _pair(a2, apply_scale(a2, "tile", 3, 3))
    sig = analyze_scale_transform([p1, p2])
    assert sig["valid_all"] is True
    assert sig["mode"] == "tile"
    assert sig["factor_expr"] == "grid_side"


def test_constant_factor_preferred_over_property():
    # when a constant factor fits, the analyzer keeps it (factor_expr stays None)
    # even though a property could coincidentally read the same value.
    a1 = [[1, 0], [0, 2]]                                # 2 colours, x2
    a2 = [[3, 0], [0, 4]]                                # 2 colours, x2
    p1 = _pair(a1, apply_scale(a1, "block", 2, 2))
    p2 = _pair(a2, apply_scale(a2, "block", 2, 2))
    sig = analyze_scale_transform([p1, p2])
    assert sig["factor"] == (2, 2)
    assert sig["factor_expr"] is None


def test_factor_axis_abstains_when_no_property_explains():
    # varying factors from *identical* inputs cannot be a property read (same input
    # -> same property -> same factor); the lift must abstain, not guess.
    a = [[1, 0], [0, 2]]
    p1 = _pair(a, apply_scale(a, "block", 2, 2))
    p2 = _pair(a, apply_scale(a, "block", 3, 3))
    sig = analyze_scale_transform([p1, p2])
    assert sig["mode"] is None
    assert sig["factor_expr"] is None


def test_render_uses_per_test_factor_from_property():
    # end-to-end through the predict path: two test inputs with different colour
    # counts must scale by *their own* count (P5: factor read off the test G0).
    from agent.active_operators import PredictOperator

    a1 = [[0, 3, 0], [3, 0, 8], [0, 8, 0]]              # 2 colours -> x2
    a2 = [[6, 0, 4], [0, 2, 0], [4, 0, 6]]              # 3 colours -> x3
    train = [
        _pair(a1, apply_scale(a1, "block", 2, 2)),
        _pair(a2, apply_scale(a2, "block", 3, 3)),
    ]
    t1 = [[9, 0], [0, 9]]                                # 1 colour  -> x1
    t2 = [[1, 0], [0, 2]]                                # 2 colours -> x2
    test = [_pair(t1, []), _pair(t2, [])]
    task = SimpleNamespace(example_pairs=train, test_pairs=test)
    grids = PredictOperator._scale_transform_grids(task)
    assert grids[0] == apply_scale(t1, "block", 1, 1)
    assert grids[1] == apply_scale(t2, "block", 2, 2)
