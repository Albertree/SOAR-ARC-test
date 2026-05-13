"""tests/test_dsl.py — exercise the two hand-coded DSL primitives.

Runs without pytest. Invoke directly::

    python tests/test_dsl.py

Exits 0 on success, non-zero on first failed assertion (with traceback).

Coverage:
  * Registry contains exactly ``{coloring, make_grid}``.
  * ``coloring`` accepts a single coord or a list of coords; honours
    ``color`` validation (0..9 or 13); is pure; rejects out-of-bounds.
  * ``make_grid`` validates ``height``/``width``/``color`` strictly and
    returns independent rows.
  * ``apply_DSL`` dispatches both primitives correctly, including the
    ``grid=None`` path for ``make_grid``.
"""

from __future__ import annotations

import os
import sys
import traceback

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

from procedural_memory.DSL.apply import DSL_REGISTRY, apply_DSL  # noqa: E402
from procedural_memory.DSL.coloring import coloring  # noqa: E402
from procedural_memory.DSL.make_grid import make_grid  # noqa: E402


def _expect_raises(label: str, exc_type, fn, *, match: str | None = None) -> None:
    try:
        fn()
    except exc_type as exc:
        if match is not None and match not in str(exc):
            raise AssertionError(
                f"{label}: expected {exc_type.__name__} matching {match!r}, got {exc!s}"
            )
        return
    raise AssertionError(f"{label}: expected {exc_type.__name__}, none raised")


# ──────────────────────────────────────────────────────────────────────────
# Registry contents.
# ──────────────────────────────────────────────────────────────────────────

def test_registry_has_exactly_two_primitives() -> None:
    names = set(DSL_REGISTRY.keys())
    assert names == {"coloring", "make_grid"}, (
        f"DSL_REGISTRY must contain exactly {{coloring, make_grid}}; got {names!r}"
    )


# ──────────────────────────────────────────────────────────────────────────
# coloring.
# ──────────────────────────────────────────────────────────────────────────

def test_coloring_single_coord() -> None:
    grid = [[0, 0], [0, 0]]
    out = coloring(grid, (0, 1), 5)
    assert out == [[0, 5], [0, 0]], f"expected one cell painted; got {out!r}"


def test_coloring_list_of_coords() -> None:
    grid = [[0, 0, 0], [0, 0, 0]]
    out = coloring(grid, [(0, 0), (1, 2)], 7)
    assert out == [[7, 0, 0], [0, 0, 7]], f"expected two cells painted; got {out!r}"


def test_coloring_transparent_sentinel_13() -> None:
    grid = [[0, 0], [0, 0]]
    out = coloring(grid, [(0, 0)], 13)
    assert out == [[13, 0], [0, 0]], f"expected 13 sentinel painted; got {out!r}"


def test_coloring_rejects_invalid_color() -> None:
    _expect_raises("color>9 not in 0..9,13", ValueError,
                   lambda: coloring([[0]], (0, 0), 10),
                   match="color must be int")
    _expect_raises("color negative", ValueError,
                   lambda: coloring([[0]], (0, 0), -1),
                   match="color must be int")
    _expect_raises("color bool", ValueError,
                   lambda: coloring([[0]], (0, 0), True),
                   match="color must be int")
    _expect_raises("color string", ValueError,
                   lambda: coloring([[0]], (0, 0), "5"),
                   match="color must be int")


def test_coloring_rejects_oob_coord() -> None:
    _expect_raises("oob row", ValueError,
                   lambda: coloring([[0, 0], [0, 0]], (5, 0), 1),
                   match="out of bounds")
    _expect_raises("oob col", ValueError,
                   lambda: coloring([[0, 0], [0, 0]], (0, 9), 1),
                   match="out of bounds")
    _expect_raises("negative coord", ValueError,
                   lambda: coloring([[0]], (-1, 0), 1),
                   match="out of bounds")


def test_coloring_rejects_malformed_selection() -> None:
    _expect_raises("string selection", ValueError,
                   lambda: coloring([[0]], "not-a-coord", 1),
                   match="selection")
    _expect_raises("3-tuple coord", ValueError,
                   lambda: coloring([[0]], (0, 0, 0), 1),
                   match="invalid coord")
    _expect_raises("non-int in coord", ValueError,
                   lambda: coloring([[0]], (0, "x"), 1),
                   match="invalid coord")


def test_coloring_empty_selection_is_identity() -> None:
    grid = [[1, 2], [3, 4]]
    out = coloring(grid, [], 9)
    assert out == [[1, 2], [3, 4]], f"empty selection should be identity; got {out!r}"
    # Pure — same shape, different object.
    assert out is not grid, "coloring must return a fresh grid even on identity"


def test_coloring_does_not_mutate_input() -> None:
    grid = [[0, 0], [0, 0]]
    snapshot = [row[:] for row in grid]
    _ = coloring(grid, (0, 0), 4)
    assert grid == snapshot, "coloring mutated its input grid"


def test_coloring_rejects_bad_grid() -> None:
    _expect_raises("grid not list", ValueError,
                   lambda: coloring("not-a-grid", (0, 0), 1),
                   match="grid must be a list")
    _expect_raises("grid row not list", ValueError,
                   lambda: coloring([(0, 0)], (0, 0), 1),
                   match="grid must be a list")


# ──────────────────────────────────────────────────────────────────────────
# make_grid.
# ──────────────────────────────────────────────────────────────────────────

def test_make_grid_happy_path() -> None:
    out = make_grid(2, 3, 4)
    assert out == [[4, 4, 4], [4, 4, 4]], f"expected 2x3 of 4s; got {out!r}"


def test_make_grid_rows_are_independent() -> None:
    out = make_grid(2, 2, 0)
    out[0][0] = 9
    assert out[1][0] == 0, "make_grid leaked shared row reference"


def test_make_grid_transparent_sentinel_13() -> None:
    out = make_grid(1, 1, 13)
    assert out == [[13]], f"expected 1x1 of 13; got {out!r}"


def test_make_grid_rejects_invalid_args() -> None:
    _expect_raises("h=0", ValueError, lambda: make_grid(0, 1, 0), match="height")
    _expect_raises("w=0", ValueError, lambda: make_grid(1, 0, 0), match="width")
    _expect_raises("h bool", ValueError, lambda: make_grid(True, 1, 0), match="height")
    _expect_raises("w bool", ValueError, lambda: make_grid(1, True, 0), match="width")
    _expect_raises("color>9", ValueError, lambda: make_grid(1, 1, 10), match="color")
    _expect_raises("color bool", ValueError, lambda: make_grid(1, 1, False), match="color")


# ──────────────────────────────────────────────────────────────────────────
# apply_DSL dispatcher.
# ──────────────────────────────────────────────────────────────────────────

def test_apply_DSL_dispatches_coloring() -> None:
    out = apply_DSL("coloring", [[0, 0], [0, 0]], selection=(1, 1), color=8)
    assert out == [[0, 0], [0, 8]], f"apply_DSL coloring path: got {out!r}"


def test_apply_DSL_dispatches_make_grid() -> None:
    out = apply_DSL("make_grid", height=2, width=2, color=3)
    assert out == [[3, 3], [3, 3]], f"apply_DSL make_grid path: got {out!r}"


def test_apply_DSL_unknown_primitive_raises_keyerror() -> None:
    _expect_raises("apply_DSL unknown", KeyError,
                   lambda: apply_DSL("rotate", [[0]]),
                   match="unknown DSL primitive")


# ──────────────────────────────────────────────────────────────────────────
# Driver.
# ──────────────────────────────────────────────────────────────────────────

def _run_all() -> int:
    tests = [
        test_registry_has_exactly_two_primitives,
        test_coloring_single_coord,
        test_coloring_list_of_coords,
        test_coloring_transparent_sentinel_13,
        test_coloring_rejects_invalid_color,
        test_coloring_rejects_oob_coord,
        test_coloring_rejects_malformed_selection,
        test_coloring_empty_selection_is_identity,
        test_coloring_does_not_mutate_input,
        test_coloring_rejects_bad_grid,
        test_make_grid_happy_path,
        test_make_grid_rows_are_independent,
        test_make_grid_transparent_sentinel_13,
        test_make_grid_rejects_invalid_args,
        test_apply_DSL_dispatches_coloring,
        test_apply_DSL_dispatches_make_grid,
        test_apply_DSL_unknown_primitive_raises_keyerror,
    ]
    fails = 0
    for t in tests:
        try:
            t()
            print(f"  OK   {t.__name__}")
        except AssertionError as e:
            fails += 1
            print(f"  FAIL {t.__name__}: {e}")
        except Exception:
            fails += 1
            print(f"  FAIL {t.__name__}: unexpected exception")
            traceback.print_exc()
    return fails


if __name__ == "__main__":
    rc = _run_all()
    if rc == 0:
        print("\nall DSL tests passed.")
    else:
        print(f"\n{rc} test(s) failed.")
    sys.exit(0 if rc == 0 else 1)
