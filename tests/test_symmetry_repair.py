"""Tests for the *symmetry-repair* family (occlusion repair via grid symmetry).

A new transformation family expressed as an *argument expression* over the frozen
`coloring` primitive (paint each occluded cell with the colour read from its
symmetric image) — F3-exempt (no new DSL primitive: the occluder colour and the
per-input symmetry set are arguments, not a new `def`). Mirrors the
geometric/scale families: a recognition vocabulary (`SYMMETRY_VOCAB` /
`held_symmetries`), an analyzer (`analyze_symmetry_repair`), a matcher
(`agent/conditions/symmetry_repair`), and a renderer (`render_symmetry_repair`)
that shares the symmetric-source map with the analyzer so they agree by
construction.

The occluder colour is the cross-pair COMM (the same hidden colour in every
example); the symmetry set is read off each input's own visible structure
(`held_symmetries`), recomputed at predict time (P5). Grounds three real ARC-AGI-2
tasks (5751f35e, 9ddd00f0 flip_h+transpose; b8825c91 flip_h) plus the madeup
concentric-ring repair task.
"""

from types import SimpleNamespace

from agent.dsl_expr.selection import (
    held_symmetries,
    apply_symmetry_repair,
    analyze_symmetry_repair,
    SYMMETRY_VOCAB,
    SYMMETRY_SRC,
    SYMMETRY_SQUARE_ONLY,
)
from agent.dsl_expr.render import render_symmetry_repair
from agent.conditions import match as match_condition


def _pair(inp, out):
    return SimpleNamespace(
        input_grid=SimpleNamespace(raw=inp),
        output_grid=SimpleNamespace(raw=out),
    )


# A flip_h-symmetric 3x5 pattern with a single-cell occluder (colour 5) on the
# left; its mirror on the right is visible, so the repair is determined.
SYM_BASE = [
    [1, 2, 0, 2, 1],
    [3, 4, 7, 4, 3],
    [1, 2, 0, 2, 1],
]


def _occlude(base, cells, occ=5):
    g = [row[:] for row in base]
    for (r, c) in cells:
        g[r][c] = occ
    return g


def test_vocab_is_five_involutions():
    assert SYMMETRY_VOCAB == [
        "flip_h", "flip_v", "rot180", "transpose", "anti_transpose"
    ]
    assert SYMMETRY_SQUARE_ONLY == {"transpose", "anti_transpose"}
    # every map is an involution: applying it twice returns the original cell.
    H = W = 4
    for name, fn in SYMMETRY_SRC.items():
        for r in range(H):
            for c in range(W):
                sr, sc = fn(r, c, H, W)
                assert fn(sr, sc, H, W) == (r, c)


def test_held_symmetries_reads_structure_modulo_occluder():
    inp = _occlude(SYM_BASE, [(1, 0)])  # occlude one cell on the left
    held = held_symmetries(inp, 5)
    # The pattern is horizontally mirror-symmetric (and 3x5 is not square, so no
    # transpose). flip_v / rot180 do NOT hold (rows 0 and 2 equal but row 1 differs
    # under vertical mirror only where it agrees — here row1 is its own v-mirror,
    # so flip_v holds too). Assert flip_h is held at minimum.
    assert "flip_h" in held
    assert "transpose" not in held  # non-square


def test_repair_fills_occluder_from_symmetric_image():
    inp = _occlude(SYM_BASE, [(1, 0), (0, 1)])
    out = apply_symmetry_repair(inp, 5, held_symmetries(inp, 5))
    assert out == SYM_BASE  # both occluded cells recovered from their mirror


def test_repair_leaves_unrecoverable_cell():
    # The centre of an odd dihedral pattern is a fixed point of every mirror; if
    # occluded it has no non-occluder image, so the repair must leave it as occ
    # rather than crash or guess.
    base = [[1, 2, 1], [2, 9, 2], [1, 2, 1]]
    inp = _occlude(base, [(1, 1)])  # occlude the centre fixed point
    out = apply_symmetry_repair(inp, 5, held_symmetries(inp, 5))
    assert out[1][1] == 5  # left as occluder, unrecovered


def test_analyzer_learns_occluder_and_reproduces():
    p0 = _occlude(SYM_BASE, [(1, 0)])
    p1 = _occlude(SYM_BASE, [(0, 3), (1, 4)])
    sig = analyze_symmetry_repair([_pair(p0, SYM_BASE), _pair(p1, SYM_BASE)])
    assert sig["valid_all"] is True
    assert sig["occluder"] == 5
    assert sig["evidence"] == 2


def test_matcher_fires_on_valid_repair():
    p0 = _occlude(SYM_BASE, [(1, 0)])
    p1 = _occlude(SYM_BASE, [(0, 3), (1, 4)])
    patterns = {
        "symmetry_repair": analyze_symmetry_repair(
            [_pair(p0, SYM_BASE), _pair(p1, SYM_BASE)])
    }
    assert match_condition("symmetry_repair", patterns, {"min_evidence": 2})


def test_analyzer_abstains_on_single_pair():
    # One pair cannot establish a *constant* occluder across the family.
    p0 = _occlude(SYM_BASE, [(1, 0)])
    sig = analyze_symmetry_repair([_pair(p0, SYM_BASE)])
    assert sig["valid_all"] is False
    assert sig["occluder"] is None


def test_analyzer_abstains_on_identity_task():
    # No change between input and output → not a repair.
    sig = analyze_symmetry_repair(
        [_pair(SYM_BASE, SYM_BASE), _pair(SYM_BASE, SYM_BASE)])
    assert sig["valid_all"] is False


def test_analyzer_abstains_on_asymmetric_grid():
    # A genuine change but no symmetry that reproduces it → inert (never perturbs
    # the recolor/move families).
    inp = [[1, 2, 3], [4, 5, 6], [7, 8, 9]]
    out = [[1, 2, 3], [4, 0, 6], [7, 8, 9]]  # 5→0, but grid is not symmetric
    sig = analyze_symmetry_repair([_pair(inp, out), _pair(inp, out)])
    assert sig["valid_all"] is False


def test_analyzer_abstains_on_multicolor_change():
    # The changed region must be a single occluder colour; a two-colour change is
    # not an occlusion (abstain).
    inp = _occlude(SYM_BASE, [(1, 0)])
    inp[0][0] = 8  # also perturb a non-occluder cell with a different colour
    base2 = [row[:] for row in SYM_BASE]
    sig = analyze_symmetry_repair([_pair(inp, base2), _pair(inp, base2)])
    assert sig["valid_all"] is False


def test_render_matches_apply():
    inp = _occlude(SYM_BASE, [(1, 0), (0, 1), (2, 3)])
    rendered = render_symmetry_repair(inp, 5)
    expected = apply_symmetry_repair(inp, 5, held_symmetries(inp, 5))
    assert rendered == expected == SYM_BASE


def test_render_inert_on_empty():
    assert render_symmetry_repair([], 5) == []
