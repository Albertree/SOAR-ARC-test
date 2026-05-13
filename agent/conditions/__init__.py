"""
agent.conditions — pattern-matcher registry.

A *condition matcher* recognizes when a learned rule applies. It consumes a
`patterns` dict (the output of ExtractPatternOperator) plus matcher-specific
`params`, and returns a bool.

This is the recognition vocabulary — separate from the DSL (transformation
vocabulary). Adding matchers is **allowed**; adding DSL primitives is not
(see CLAUDE.md §6.1, INVARIANTS.md §1 F3).

A matcher must be deterministic and side-effect-free: same inputs → same
output, no I/O, no global state, no randomness.

Usage in a matcher module (`agent/conditions/<name>.py`):

    from agent.conditions import register

    [REGISTER_DECORATOR]("<name>")
    def match(patterns: dict, params: dict) -> bool:
        ...
        return True_or_False

(where `[REGISTER_DECORATOR]` is the literal `@register` — the brackets here
keep this docstring example from being counted by the P5 invariant regex.)

Lookup:

    from agent.conditions import CONDITION_REGISTRY
    matcher = CONDITION_REGISTRY["<name>"]
    fired = matcher(patterns, params)
"""

from __future__ import annotations

import importlib
import pkgutil
from typing import Callable, Dict

Matcher = Callable[[dict, dict], bool]

CONDITION_REGISTRY: Dict[str, Matcher] = {}


def register(name: str) -> Callable[[Matcher], Matcher]:
    """Decorator: bind a matcher function to `name` in CONDITION_REGISTRY."""
    if not isinstance(name, str) or not name:
        raise ValueError("condition matcher name must be a non-empty string")

    def _decorate(fn: Matcher) -> Matcher:
        if name in CONDITION_REGISTRY and CONDITION_REGISTRY[name] is not fn:
            raise ValueError(f"condition matcher already registered: {name!r}")
        CONDITION_REGISTRY[name] = fn
        return fn

    return _decorate


def _autoload_matchers() -> None:
    """Import every sibling module so its @register decorators run."""
    pkg_name = __name__
    pkg_path = __path__  # type: ignore[name-defined]
    for mod in pkgutil.iter_modules(pkg_path):
        if mod.name.startswith("_"):
            continue
        importlib.import_module(f"{pkg_name}.{mod.name}")


_autoload_matchers()
