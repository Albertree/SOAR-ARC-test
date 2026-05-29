"""
agent.conditions — the *recognition* vocabulary (condition matchers).

A condition matcher recognises *when* a (composed) transformation applies. It is
a separate dimension from the transformation DSL: the DSL is frozen at two
hand-coded primitives (`coloring` / `make_grid`, CLAUDE.md §6.1), but the
recognition vocabulary is *allowed to grow by hand* — this is how the system
learns to *notice* a pattern, not how it learns to *do* a transformation
(CLAUDE.md §6.3).

Each matcher:
  1. lives in `agent/conditions/<name>.py`,
  2. defines `match(patterns: dict, params: dict) -> bool`,
  3. is registered with the register decorator (see below),
  4. is deterministic and side-effect-free.

This module owns `CONDITION_REGISTRY` (name -> match callable) and the
register decorator. Sibling matcher modules are imported on first use so their
decorators populate the registry (P5 in docs/INVARIANTS.md counts registered
matchers — one decorator site per sibling module).
"""

import importlib
import pkgutil

# name -> match callable
CONDITION_REGISTRY: dict = {}


def register(name: str):
    """Decorator: register a `match(patterns, params)` callable under `name`."""
    def _decorator(fn):
        if name in CONDITION_REGISTRY and CONDITION_REGISTRY[name] is not fn:
            raise ValueError(f"condition matcher already registered: {name!r}")
        CONDITION_REGISTRY[name] = fn
        return fn
    return _decorator


def _load_all():
    """Import every sibling module so its @register decorators run."""
    for mod in pkgutil.iter_modules(__path__):
        if mod.name == "__init__":
            continue
        importlib.import_module(f"{__name__}.{mod.name}")


def get(name: str):
    """Return the registered matcher callable for `name`, or None."""
    if name not in CONDITION_REGISTRY:
        _load_all()
    return CONDITION_REGISTRY.get(name)


def match(name: str, patterns: dict, params: dict = None) -> bool:
    """Dispatch to the registered matcher `name`. Unknown name -> False.

    Deterministic and side-effect-free: a matcher only *recognises* a pattern;
    it never mutates working memory or touches the filesystem.
    """
    fn = get(name)
    if fn is None:
        return False
    return bool(fn(patterns or {}, params or {}))


# Populate the registry at import time so `CONDITION_REGISTRY` is complete for
# callers that introspect it directly (e.g. the slow-path generalizer).
_load_all()
