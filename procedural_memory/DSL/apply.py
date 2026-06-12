"""
apply_DSL — dispatcher over the static transformation layer (CLAUDE.md §6).

Two layers exist conceptually (CLAUDE.md §6.2):
  1. Static layer  — the two frozen primitives `make_grid` / `coloring`,
                     dispatched here.
  2. Discovered layer — abstract rules persisted as data in
                     `procedural_memory/rule_*.json`, each resolving to a
                     `make_grid`/`coloring` *composition*. That layer grows
                     organically via anti-unification, never by new code here.

This module implements the static layer only. The static layer never grows
beyond the two primitives below (INVARIANTS F3).
"""

from procedural_memory.DSL.make_grid import make_grid
from procedural_memory.DSL.coloring import coloring

#: the entire frozen transformation vocabulary
_STATIC_PRIMITIVES = {
    "make_grid": make_grid,
    "coloring": coloring,
}


def apply_DSL(name: str, grid=None, **kwargs):
    """Apply a static DSL primitive by name.

    `make_grid` ignores `grid` (it creates a fresh canvas); `coloring` takes the
    grid as its first argument. Unknown names raise `KeyError` loudly rather
    than silently no-op'ing — a rule referencing a non-existent primitive is a
    bug, not a transformation.
    """
    fn = _STATIC_PRIMITIVES.get(name)
    if fn is None:
        raise KeyError(f"unknown DSL primitive: {name!r}")
    if name == "make_grid":
        return fn(**kwargs)
    return fn(grid, **kwargs)
