"""
apply — dispatcher over the two frozen transformation primitives.

The static transformation vocabulary is frozen at exactly two primitives
(CLAUDE.md §6, docs/INVARIANTS.md F3): `make_grid` and `coloring`. Every other
transformation is a *composition* of these two, discovered at runtime — never a
third hand-coded primitive. This module is the single dispatch point.

    apply_DSL(name, grid=None, **kwargs) -> grid

`make_grid` builds a canvas from scratch (its `grid` argument is unused);
`coloring` paints onto an existing grid. The dispatcher hides that asymmetry so
callers can treat both uniformly.
"""

#: name -> primitive callable. Populated by the @register decorator below as the
#: primitive modules are imported at the bottom of this file.
_DSL_REGISTRY: dict = {}


def register(name: str):
    """Decorator: register a transformation primitive under `name`.

    Duplicate names are an error — two primitives claiming one transformation
    slot is a bug, not an override. NOTE: only `make_grid` and `coloring` may
    ever be registered (F3); adding a third trips the invariant checker.
    """
    def _decorator(fn):
        if name in _DSL_REGISTRY:
            raise ValueError(f"duplicate DSL primitive registered: {name!r}")
        _DSL_REGISTRY[name] = fn
        return fn
    return _decorator


def apply_DSL(name: str, grid=None, **kwargs):
    """Apply transformation primitive `name`. Raises KeyError for an unknown
    primitive so a rule referencing a non-existent transformation fails loudly
    rather than silently producing nothing."""
    fn = _DSL_REGISTRY.get(name)
    if fn is None:
        raise KeyError(f"unknown DSL primitive: {name!r}")
    if name == "make_grid":
        # make_grid creates a canvas from scratch — it takes no input grid.
        return fn(**kwargs)
    return fn(grid, **kwargs)


# Import the primitive modules so their @register runs on package import. Kept at
# the bottom so `register` is defined before the modules reference it.
from procedural_memory.DSL import make_grid as _make_grid_mod  # noqa: E402,F401
from procedural_memory.DSL import coloring as _coloring_mod    # noqa: E402,F401
