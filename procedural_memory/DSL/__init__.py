"""
procedural_memory.DSL — the frozen transformation layer.

Exactly two hand-coded primitives, forever: `make_grid` and `coloring`
(CLAUDE.md §6.1, INVARIANTS F3). All richer transformations are compositions of
these two, discovered at runtime and stored as data in
`procedural_memory/rule_*.json` — never a third primitive added here.
"""

from procedural_memory.DSL.apply import apply_DSL, DSL_REGISTRY  # noqa: F401
