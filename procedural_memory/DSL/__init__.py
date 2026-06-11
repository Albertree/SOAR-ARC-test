"""
procedural_memory.DSL — ARBOR's transformation vocabulary.

Exactly two hand-coded primitives exist and ever will (CLAUDE.md §6.1,
INVARIANTS.md F3):

  - make_grid(height, width, color) — produce a fresh canvas.
  - coloring(grid, selection, color) — paint cells.

Every other transformation is a *discovered* composition of these two,
persisted as data (a `procedural_memory/rule_NNN.json` produced by
anti-unification), never a new hand-coded function. `apply_DSL` is the single
dispatch entry point.
"""

from procedural_memory.DSL.make_grid import make_grid
from procedural_memory.DSL.coloring import coloring
from procedural_memory.DSL.apply import apply_DSL, static_primitives

__all__ = ["make_grid", "coloring", "apply_DSL", "static_primitives"]
