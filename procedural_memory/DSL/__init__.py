"""
procedural_memory.DSL — the static transformation layer.

The hand-coded transformation vocabulary is frozen at exactly TWO primitives
(CLAUDE.md §6, docs/INVARIANTS.md F3):

    make_grid(height, width, color)   — produce a fresh canvas
    coloring(grid, selection, color)  — paint cells

Every other transformation (move, rotate, flip, copy, scale, recolor, …) is a
*composition* of these two, discovered by ARBOR at runtime and persisted as
DATA (`procedural_memory/rule_NNN.json`), never as a third hand-coded primitive.
`apply.apply_DSL` is the single dispatch point over this static layer.
"""
