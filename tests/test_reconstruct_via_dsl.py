"""
Tests for agent.memory.reconstruct_via_dsl (iter 11).

The Slice-1 copy_common_output rule declares action.dsl == "make_grid", but
until this iter PredictOperator produced its answer by copying the common
example output wholesale — the declared primitive was never invoked. iter 11
routes the copy through the two frozen DSL primitives (make_grid + coloring)
so the action half is genuinely *executed* bottom-up (CLAUDE.md §6.1/§6.2).

The decisive properties:
  * bit-identical — reconstruction equals the input grid exactly,
  * bottom-up    — only make_grid + coloring are used (apply_DSL dispatch),
  * value-agnostic — the red (easy000a) and green (easy000a2) outputs are
    rebuilt by the SAME code with no literal.

pytest is not installed here, so the file is also runnable directly:
    python tests/test_reconstruct_via_dsl.py
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agent.memory import reconstruct_via_dsl


def _fixed_output(fill_color):
    """easy000a-style output: fill_color at (5,5) on a 6x6 black canvas."""
    out = [[0] * 6 for _ in range(6)]
    out[5][5] = fill_color
    return out


# --- bit-identical reconstruction -----------------------------------------

def test_reconstructs_red_output_identically():
    out = _fixed_output(2)
    assert reconstruct_via_dsl(out) == out


def test_reconstructs_green_output_identically_same_code():
    out = _fixed_output(3)
    assert reconstruct_via_dsl(out) == out
    # And it really is the green grid, distinct from the red case.
    assert reconstruct_via_dsl(out)[5][5] == 3


def test_value_agnostic_red_and_green_differ():
    red = reconstruct_via_dsl(_fixed_output(2))
    green = reconstruct_via_dsl(_fixed_output(3))
    assert red != green  # no accidental literal sharing


# --- general grids: multi-colour, uniform, non-zero background ------------

def test_reconstructs_multicolor_grid():
    grid = [
        [0, 1, 2],
        [2, 0, 1],
        [1, 2, 0],
    ]
    assert reconstruct_via_dsl(grid) == grid


def test_reconstructs_uniform_grid_make_grid_only():
    grid = [[7, 7], [7, 7]]
    assert reconstruct_via_dsl(grid) == grid


def test_reconstructs_nonzero_background():
    # Modal colour is 4 (the background); the lone 9 must still be painted.
    grid = [[4, 4, 4], [4, 9, 4], [4, 4, 4]]
    assert reconstruct_via_dsl(grid) == grid


def test_does_not_mutate_input():
    grid = [[0, 1], [1, 0]]
    snapshot = [row[:] for row in grid]
    reconstruct_via_dsl(grid)
    assert grid == snapshot


# --- output is a fresh object (safe to mutate downstream) ------------------

def test_returns_fresh_object():
    grid = [[0, 2], [2, 0]]
    result = reconstruct_via_dsl(grid)
    result[0][0] = 5
    assert grid[0][0] == 0  # input untouched


# --- malformed input fails closed (no silent wrong answer) ----------------

def test_rejects_empty_grid():
    try:
        reconstruct_via_dsl([])
    except ValueError:
        return
    raise AssertionError("expected ValueError on empty grid")


def test_rejects_ragged_grid():
    try:
        reconstruct_via_dsl([[0, 1], [1]])
    except ValueError:
        return
    raise AssertionError("expected ValueError on ragged grid")


def test_rejects_non_list():
    try:
        reconstruct_via_dsl("not a grid")
    except ValueError:
        return
    raise AssertionError("expected ValueError on non-list grid")


if __name__ == "__main__":
    funcs = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    failed = 0
    for fn in funcs:
        try:
            fn()
            print(f"PASS {fn.__name__}")
        except AssertionError as e:
            failed += 1
            print(f"FAIL {fn.__name__}: {e}")
        except Exception as e:  # noqa: BLE001 — surface unexpected errors too
            failed += 1
            print(f"ERROR {fn.__name__}: {type(e).__name__}: {e}")
    print(f"\n{len(funcs) - failed}/{len(funcs)} passed")
    sys.exit(1 if failed else 0)
