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
