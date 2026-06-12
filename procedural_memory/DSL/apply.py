"""
apply.py — the DSL dispatcher (CLAUDE.md §6).

`apply_DSL(name, grid, **kwargs)` runs one transformation primitive. The static
layer is frozen at exactly two primitives — `make_grid` and `coloring` — and
never grows (INVARIANTS F3). Every other transformation is a *composition* of
these two, expressed as data in `procedural_memory/rule_*.json` (the discovered
layer) and replayed by stacking `apply_DSL` calls; it is never a third hand-coded
primitive.

Registration here is by explicit call (not a decorator) so the two-primitive
freeze is obvious at a glance and the F3 checker sees only `make_grid`/`coloring`.
"""

#: name -> primitive callable. Frozen at two entries (F3).
DSL_REGISTRY: dict = {}


def register(name: str, fn):
    """Bind a primitive callable under `name`. Only `make_grid`/`coloring`."""
    DSL_REGISTRY[name] = fn
    return fn


from procedural_memory.DSL.make_grid import make_grid as _make_grid
from procedural_memory.DSL.coloring import coloring as _coloring

register("make_grid", _make_grid)
register("coloring", _coloring)


def apply_DSL(name: str, grid, **kwargs):
    """Dispatch one DSL primitive by name. Raises KeyError for an unknown name
    so a rule referencing a non-existent primitive fails loudly rather than
    silently producing nothing."""
    fn = DSL_REGISTRY.get(name)
    if fn is None:
        raise KeyError(f"unknown DSL primitive: {name!r}")
    if name == "make_grid":
        return fn(kwargs["height"], kwargs["width"], kwargs["color"])
    if name == "coloring":
        return fn(grid, kwargs["selection"], kwargs["color"])
    return fn(grid, **kwargs)
