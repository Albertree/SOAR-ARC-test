"""
procedural_memory.DSL — the static transformation layer.

This package holds the **two and only two** hand-coded transformation
primitives ARBOR is permitted to author (CLAUDE.md §6.1, INVARIANTS F3):

    make_grid(height, width, color) — produce a fresh canvas.
    coloring(grid, selection, color) — paint cells.

Every other transformation (move, rotate, flip, copy, scale, recolor, …) is a
*composition* of these two plus an argument/selection expression, and must be
discovered by ARBOR at runtime — never added here as a third primitive. The
invariant checker auto-reverts any new `def`/`@register` in this directory that
is not one of these two (`scripts/check_invariants.sh`, signal F3).

`apply_DSL` (in `apply.py`) is the dispatcher over this static layer.
"""
