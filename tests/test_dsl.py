"""
Tests for the two hand-coded transformation DSL primitives
(`procedural_memory/DSL/`): `coloring`, `make_grid`, and the `apply_DSL`
dispatcher / `DSL_REGISTRY`.

These primitives are the *entire* hand-coded transformation vocabulary ARBOR
is permitted to ship with (CLAUDE.md §6.1, INVARIANTS.md §1 F3). Every other
transformation must be a discovered composition of these two. The final block
shows that the Slice-1 `copy_common_output` mechanism IS such a composition —
`make_grid` (black canvas) + `coloring` (paint the common object) reconstructs
both easy000a's and easy000a2's *different* fixed outputs from the SAME two
primitives, value-agnostically (no literal colour/coord in the primitives).

pytest is not installed in this environment, so the file is also runnable
directly:  python tests/test_dsl.py
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import procedural_memory.DSL  # noqa: F401  (populates DSL_REGISTRY)
from procedural_memory.DSL.apply import DSL_REGISTRY, VALID_COLORS, apply_DSL
from procedural_memory.DSL.coloring import coloring
from procedural_memory.DSL.make_grid import make_grid


_passed = 0
_failed = 0


def check(name, cond):
    global _passed, _failed
    if cond:
        _passed += 1
    else:
        _failed += 1
        print(f"  FAIL: {name}")


def expect_raises(name, fn, exc=Exception):
    global _passed, _failed
    try:
        fn()
    except exc:
        _passed += 1
        return
    except Exception as e:  # wrong exception type
        _failed += 1
        print(f"  FAIL: {name} (raised {type(e).__name__}, expected {exc.__name__})")
        return
    _failed += 1
    print(f"  FAIL: {name} (no exception raised)")


# --- registry: closed at exactly the two frozen primitives ----------------

check("registry has coloring", "coloring" in DSL_REGISTRY)
check("registry has make_grid", "make_grid" in DSL_REGISTRY)
check("registry is closed at two", set(DSL_REGISTRY) == {"coloring", "make_grid"})
check("VALID_COLORS = 0..9 + 13", VALID_COLORS == frozenset(range(10)) | {13})

# --- make_grid happy paths ------------------------------------------------

g = make_grid(3, 4, 0)
check("make_grid dims", len(g) == 3 and all(len(r) == 4 for r in g))
check("make_grid fill", all(c == 0 for r in g for c in r))
check("make_grid color 13 ok", make_grid(1, 1, 13) == [[13]])

# rows are independent (no shared references)
g2 = make_grid(2, 2, 5)
g2[0][0] = 9
check("make_grid rows independent", g2[1][0] == 5)

expect_raises("make_grid rejects h<1", lambda: make_grid(0, 3, 0), ValueError)
expect_raises("make_grid rejects w<1", lambda: make_grid(3, 0, 0), ValueError)
expect_raises("make_grid rejects bad color", lambda: make_grid(2, 2, 10), ValueError)
expect_raises("make_grid rejects bool color", lambda: make_grid(2, 2, True), ValueError)
expect_raises("make_grid rejects bool dim", lambda: make_grid(True, 2, 0), ValueError)

# --- coloring happy paths -------------------------------------------------

base = make_grid(3, 3, 0)
painted = coloring(base, (1, 1), 2)
check("coloring single coord", painted[1][1] == 2)
check("coloring leaves rest", sum(c for r in painted for c in r) == 2)
check("coloring does not mutate input", base[1][1] == 0)

multi = coloring(base, [(0, 0), (2, 2)], 4)
check("coloring list of coords", multi[0][0] == 4 and multi[2][2] == 4)
check("coloring empty selection = identity", coloring(base, [], 7) == base)
check("coloring None selection = identity", coloring(base, None, 7) == base)

expect_raises("coloring OOB raises", lambda: coloring(base, (5, 5), 2), ValueError)
expect_raises("coloring bad color raises", lambda: coloring(base, (0, 0), 11), ValueError)
expect_raises("coloring bool color raises", lambda: coloring(base, (0, 0), False), ValueError)
expect_raises("coloring bad coord raises", lambda: coloring(base, (0,), 2), ValueError)
expect_raises("coloring bad grid raises", lambda: coloring("nope", (0, 0), 2), ValueError)

# --- apply_DSL dispatch ---------------------------------------------------

check("apply_DSL make_grid", apply_DSL("make_grid", height=2, width=2, color=0) == [[0, 0], [0, 0]])
check("apply_DSL coloring", apply_DSL("coloring", grid=make_grid(2, 2, 0), selection=(0, 1), color=3)[0][1] == 3)
expect_raises("apply_DSL unknown raises", lambda: apply_DSL("rotate", grid=base), KeyError)

# --- Slice-1: copy_common_output IS a make_grid + coloring composition -----
# The SAME two primitives reconstruct two DIFFERENT fixed outputs (value-
# agnostic): easy000a = red(2) at (5,5); easy000a2 = green(3) at (0,0).

def reconstruct(height, width, bg, coord, fg):
    """make_grid(canvas) then coloring(the one object) — no literal inside."""
    canvas = apply_DSL("make_grid", height=height, width=width, color=bg)
    return apply_DSL("coloring", grid=canvas, selection=[coord], color=fg)

easy000a_out = reconstruct(6, 6, 0, (5, 5), 2)
check("easy000a output reconstructed", easy000a_out[5][5] == 2 and easy000a_out[0][0] == 0)

easy000a2_out = reconstruct(6, 6, 0, (0, 0), 3)
check("easy000a2 output reconstructed", easy000a2_out[0][0] == 3 and easy000a2_out[5][5] == 0)

check("same primitives, different outputs (value-agnostic)",
      easy000a_out != easy000a2_out)


print(f"\ntest_dsl: {_passed} passed, {_failed} failed")
sys.exit(1 if _failed else 0)
