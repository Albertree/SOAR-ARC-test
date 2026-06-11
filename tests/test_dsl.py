"""
Tests for the static DSL layer: the two frozen primitives `make_grid` /
`coloring` and the `apply_DSL` dispatcher (CLAUDE.md §6).

Locks:
  1. make_grid produces a correct, independently-rowed canvas; rejects bad dims.
  2. coloring paints (single coord + coord list), is pure, clamps OOB, and
     treats colour 13 as a transparent no-op.
  3. apply_DSL dispatches both primitives and rejects unknown names; the static
     registry is exactly {coloring, make_grid} (F3 — frozen at two).
  4. Composition: make_grid + coloring reconstructs easy0001's constant output
     grid. This is the exact recipe a later iter's PredictByAllPairCommOp will
     materialise once the `constant_output` recognition is wired to predict.

Run directly: `python tests/test_dsl.py`.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from procedural_memory.DSL import make_grid, coloring, apply_DSL, STATIC_PRIMITIVES


def test_make_grid_basic():
    g = make_grid(2, 3, 0)
    assert g == [[0, 0, 0], [0, 0, 0]]
    # rows are independent objects (painting one must not alias another)
    g[0][0] = 7
    assert g[1][0] == 0
    print("ok test_make_grid_basic")


def test_make_grid_rejects_bad_dims():
    for bad in [(-1, 3, 0), (2, -1, 0)]:
        try:
            make_grid(*bad)
        except ValueError:
            pass
        else:
            raise AssertionError(f"expected ValueError for {bad}")
    try:
        make_grid(2.0, 3, 0)
    except TypeError:
        pass
    else:
        raise AssertionError("expected TypeError for non-int dim")
    print("ok test_make_grid_rejects_bad_dims")


def test_coloring_single_and_list():
    base = make_grid(3, 3, 0)
    one = coloring(base, (1, 1), 5)
    assert one[1][1] == 5 and sum(sum(r) for r in one) == 5
    # input grid is never mutated
    assert base[1][1] == 0
    many = coloring(base, [(0, 0), (2, 2)], 4)
    assert many[0][0] == 4 and many[2][2] == 4 and many[1][1] == 0
    print("ok test_coloring_single_and_list")


def test_coloring_oob_and_transparent():
    base = make_grid(2, 2, 0)
    # out-of-bounds coords are silently skipped, not an error
    assert coloring(base, [(5, 5), (0, 0)], 3) == [[3, 0], [0, 0]]
    # colour 13 (transparent) repaints nothing
    assert coloring([[1, 2], [3, 4]], [(0, 0), (1, 1)], 13) == [[1, 2], [3, 4]]
    print("ok test_coloring_oob_and_transparent")


def test_apply_dsl_dispatch_and_closure():
    assert list(STATIC_PRIMITIVES) == ["coloring", "make_grid"]  # F3: frozen at two
    g = apply_DSL("make_grid", None, height=1, width=2, color=9)
    assert g == [[9, 9]]
    painted = apply_DSL("coloring", g, selection=(0, 0), color=1)
    assert painted == [[1, 9]]
    try:
        apply_DSL("rotate", g, k=1)
    except KeyError:
        pass
    else:
        raise AssertionError("apply_DSL must reject unknown primitives")
    print("ok test_apply_dsl_dispatch_and_closure")


def test_compose_reconstructs_constant_output():
    """make_grid + coloring rebuilds easy0001's output grid (6x6, (5,5)=2)."""
    expected = [[0] * 6 for _ in range(6)]
    expected[5][5] = 2
    # The intended recipe: fresh background canvas, then paint the differing
    # cells. Value-agnostic — the (5,5)/2 here come from the data, not literals
    # baked into the DSL.
    canvas = apply_DSL("make_grid", None, height=6, width=6, color=0)
    rebuilt = apply_DSL("coloring", canvas, selection=[(5, 5)], color=2)
    assert rebuilt == expected
    print("ok test_compose_reconstructs_constant_output")


if __name__ == "__main__":
    test_make_grid_basic()
    test_make_grid_rejects_bad_dims()
    test_coloring_single_and_list()
    test_coloring_oob_and_transparent()
    test_apply_dsl_dispatch_and_closure()
    test_compose_reconstructs_constant_output()
    print("all DSL tests passed")
