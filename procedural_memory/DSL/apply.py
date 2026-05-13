"""apply — DSL_REGISTRY, ``@register`` decorator, ``apply_DSL`` dispatcher.

This module owns the registry of hand-coded DSL primitives. The set is
**closed at exactly two** entries (``coloring`` and ``make_grid``); F3 in
``docs/INVARIANTS.md`` auto-reverts any commit that introduces a third
register-decorator call (other than for those two names) under
``procedural_memory/DSL/*.py``.

Discovered abstractions produced by ``program.anti_unification`` are not
re-registered here — they live as data in ``procedural_memory/rule_*.json``
with ``anti_unification_trace`` pointing at the trace that recorded their
discovery. See ``CLAUDE.md §6.2``.
"""

from __future__ import annotations

from typing import Any, Callable, Dict

DSL_REGISTRY: Dict[str, Callable[..., Any]] = {}

# Canonical ARC colour palette: the ten paintable colours (0..9) plus the
# transparent / no-paint sentinel (13). The two hand-coded primitives
# (``coloring``, ``make_grid``) reject any other value at runtime; the
# rule-emission helpers in ``agent.memory`` pre-validate against the same
# domain so a malformed rule cannot reach disk. Single source of truth
# imported by all four sites — keep them in lockstep by construction
# instead of by lockstep-edit discipline.
VALID_COLORS: frozenset[int] = frozenset(range(10)) | {13}


def register(name: str) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """Decorator: bind a primitive function to ``name`` in ``DSL_REGISTRY``.

    Re-registering the same function under the same name is a no-op (useful
    when test code reloads modules); binding a different callable under an
    existing name raises ``ValueError``.
    """
    if not isinstance(name, str) or not name:
        raise ValueError("DSL primitive name must be a non-empty string")

    def _decorate(fn: Callable[..., Any]) -> Callable[..., Any]:
        if name in DSL_REGISTRY and DSL_REGISTRY[name] is not fn:
            raise ValueError(f"DSL primitive already registered: {name!r}")
        DSL_REGISTRY[name] = fn
        return fn

    return _decorate


def apply_DSL(name: str, grid=None, **kwargs):
    """Dispatch to a registered DSL primitive.

    For grid-consuming primitives (``coloring``), pass the working canvas as
    ``grid``. For grid-producing primitives (``make_grid``), leave ``grid``
    as ``None`` and supply ``height``/``width``/``color`` via keyword.

    Raises ``KeyError`` if ``name`` is not in ``DSL_REGISTRY``.
    """
    if name not in DSL_REGISTRY:
        raise KeyError(f"unknown DSL primitive: {name!r}")
    fn = DSL_REGISTRY[name]
    if grid is None:
        return fn(**kwargs)
    return fn(grid, **kwargs)
