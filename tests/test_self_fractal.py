"""Tests for the *self-fractal* family (the input tiled into its own foreground:
output[i·h:(i+1)·h, j·w:(j+1)·w] = input iff input[i][j] is foreground).

A new transformation family expressed as an *argument expression* over the frozen
`make_grid` + `coloring` primitives (build the tiled grid, then rebuild it via
`render_grid_via_primitives`) — F3-exempt (no new DSL primitive: the *where-to-place*
placement predicate is the argument, not a new `def tile`). Mirrors the
geometric/scale/symmetry/extract families: it adds an analyzer
(`analyze_self_fractal`), a placement expression (`self_fractal`), a matcher
(`agent/conditions/self_fractal`), and renders the tiled grid with the shared
`self_fractal` builder so recognition and rendering agree by construction.

The placement predicate is *searched* ("place at foreground", then "place at
colour == C" for each specific foreground colour — the §2.5-2b lift) and
value-agnostic, the per-test reading recomputed at predict time (P5). Grounds three
real ARC-AGI-2 tasks (007bbfb7, 5b6cbef5 via foreground; cce03e0d via colour==2)
plus the madeup self-fractal task.
"""

from types import SimpleNamespace

from agent.dsl_expr.selection import analyze_self_fractal, self_fractal
from agent.dsl_expr.render import render_grid_via_primitives
from agent.conditions import match as match_condition


def _pair(inp, out):
    return SimpleNamespace(
        input_grid=SimpleNamespace(raw=inp),
        output_grid=SimpleNamespace(raw=out),
    )


# Value-agnostic 2x2 / 3x3 fractals (different palettes, bg 0).
A_IN = [[2, 0], [0, 2]]
A_OUT = self_fractal(A_IN)
B_IN = [[0, 3, 0], [3, 3, 3], [0, 3, 0]]
B_OUT = self_fractal(B_IN)


def test_self_fractal_places_copy_at_foreground_cells():
    g = [[1, 0], [0, 1]]
    out = self_fractal(g)
    assert len(out) == 4 and len(out[0]) == 4
    # copy at (0,0) and (1,1) blocks; bg elsewhere
    assert out == [
        [1, 0, 0, 0],
        [0, 1, 0, 0],
        [0, 0, 1, 0],
        [0, 0, 0, 1],
    ]


def test_self_fractal_empty_is_none():
    assert self_fractal([]) is None
    assert self_fractal([[]]) is None


def test_analyze_learns_fractal():
    sig = analyze_self_fractal([_pair(A_IN, A_OUT), _pair(B_IN, B_OUT)])
    assert sig["valid_all"] is True
    assert sig["evidence"] == 2


def test_matcher_fires_on_fractal():
    sig = analyze_self_fractal([_pair(A_IN, A_OUT), _pair(B_IN, B_OUT)])
    assert match_condition("self_fractal", {"self_fractal": sig},
                           {"min_evidence": 2}) is True


def test_render_equals_fractal_via_primitives():
    # Rebuild the tiled grid through the frozen primitives — render ↔ mechanism agree.
    assert render_grid_via_primitives(self_fractal(B_IN)) == B_OUT


def test_abstains_on_single_pair():
    sig = analyze_self_fractal([_pair(A_IN, A_OUT)])
    assert sig["valid_all"] is False
    assert match_condition("self_fractal", {"self_fractal": sig},
                           {"min_evidence": 2}) is False


def test_inert_on_identity():
    # Same-size identity is not a fractal (no expansion) — the family abstains.
    g = [[0, 5], [5, 0]]
    sig = analyze_self_fractal([_pair(g, g), _pair(g, g)])
    assert sig["valid_all"] is False


def test_inert_on_scale():
    # A uniform 2x scale (each cell → a 2x2 block) is NOT a self-fractal placement
    # (which places the whole input, not a solid block) — the family abstains so it
    # never perturbs the scale family.
    a = [[1, 0], [0, 1]]
    scaled = [[1, 1, 0, 0], [1, 1, 0, 0], [0, 0, 1, 1], [0, 0, 1, 1]]
    sig = analyze_self_fractal([_pair(a, scaled), _pair(a, scaled)])
    assert sig["valid_all"] is False


def test_inert_on_one_by_one():
    # A 1x1 grid fractals to 1x1 (no expansion) — guarded out.
    sig = analyze_self_fractal([_pair([[3]], [[3]]), _pair([[4]], [[4]])])
    assert sig["valid_all"] is False


# --- learned colour predicate (the §2.5-2b lift: place at colour == C only) ----

# Two foreground colours {1, 2} present; copies are placed at the 2-cells ONLY,
# the 1-cells are inert background-of-the-block (cce03e0d's shape).
C_IN = [[1, 0, 2], [2, 1, 0], [0, 2, 1]]
C_OUT = self_fractal(C_IN, predicate=2)


def test_self_fractal_colour_predicate_places_only_at_that_colour():
    # 'fg' would place at both 1- and 2-cells; predicate=2 places at 2-cells only.
    assert self_fractal(C_IN, predicate=2) != self_fractal(C_IN, predicate="fg")
    # block (0,2) holds colour 2 in C_IN → a copy; block (0,0) holds colour 1 → none.
    assert C_OUT[0][6:9] == C_IN[0]            # top-right block = a copy
    assert C_OUT[0][0:3] == [0, 0, 0]          # top-left block (1-cell) = empty


def test_analyze_learns_colour_predicate():
    sig = analyze_self_fractal([_pair(C_IN, C_OUT), _pair(C_IN, C_OUT)])
    assert sig["valid_all"] is True
    assert sig["predicate"] == 2


def test_foreground_predicate_preferred_when_it_reproduces():
    # When plain foreground reproduces, "fg" is chosen first (most general), never a
    # coincidental specific colour — preserves 007bbfb7 / 5b6cbef5 behaviour.
    sig = analyze_self_fractal([_pair(A_IN, A_OUT), _pair(B_IN, B_OUT)])
    assert sig["predicate"] == "fg"


def test_colour_predicate_matcher_fires():
    sig = analyze_self_fractal([_pair(C_IN, C_OUT), _pair(C_IN, C_OUT)])
    assert match_condition("self_fractal", {"self_fractal": sig},
                           {"min_evidence": 2}) is True
