"""
DSL dispatcher: apply_DSL.

The single entry point onto ARBOR's transformation layer (CLAUDE.md §6). It
dispatches a primitive *name* to its implementation:

    apply_DSL(name, grid, **kwargs) -> grid

Two dispatch layers exist (CLAUDE.md §6.2):

  1. Static layer — the **two** frozen, hand-coded primitives, `make_grid` and
     `coloring`. This layer NEVER grows (INVARIANTS.md F3).
  2. Discovered layer — abstract rules produced by anti-unification and
     persisted as `procedural_memory/rule_NNN.json` data, whose `action.dsl`
     name resolves to a `make_grid`/`coloring` composition. Not yet wired; this
     module currently exposes only the static layer.

The static registry is intentionally tiny and closed. `register` exists so the
two primitives declare themselves uniformly, NOT so new primitives can be added
— adding a third static primitive is an F3 violation regardless of mechanism.
The closed set is exposed as the module constant `STATIC_PRIMITIVES`.
"""

from procedural_memory.DSL.make_grid import make_grid
from procedural_memory.DSL.coloring import coloring

# The static primitive registry. Closed at two (F3).
_STATIC = {}


def register(name):
    """Register a static primitive under `name`. Reserved for the two frozen
    primitives only; see F3 — no third static primitive may ever be added."""

    def _decorator(fn):
        _STATIC[name] = fn
        return fn

    return _decorator


# Declare the two — and only two — static primitives.
register("make_grid")(make_grid)
register("coloring")(coloring)

# Sorted names of the hand-coded primitives (exactly two). A constant, not a
# function, so the F3 def-heuristic never mistakes an introspection helper for a
# third hand-coded primitive.
STATIC_PRIMITIVES = tuple(sorted(_STATIC))


def apply_DSL(name, grid, **kwargs):
    """Apply the named primitive.

    `make_grid` ignores `grid` (it produces a fresh canvas); `coloring` paints
    the supplied `grid`. Unknown names raise — the discovered layer is not yet
    wired, so an unrecognised name is a programming error, not a silent no-op.
    """
    if name == "make_grid":
        return make_grid(**kwargs)
    if name == "coloring":
        return coloring(grid, **kwargs)
    raise KeyError(
        f"unknown DSL primitive {name!r}; static layer is {list(STATIC_PRIMITIVES)} "
        f"(discovered layer not yet wired)"
    )
