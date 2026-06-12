"""
agent.conditions — the condition-matcher registry (recognition vocabulary).

A *condition matcher* answers the question "does this pattern hold?" — it is the
LHS half of a `{condition, action}` rule (CLAUDE.md §3.2, docs/RULE_FORMAT.md §4).
Matchers are how ARBOR's *recognition* vocabulary grows. This is a separate
dimension from the *transformation* DSL (which is frozen at two primitives,
`coloring`/`make_grid` — see CLAUDE.md §6, INVARIANTS F3): adding a matcher
introduces no new way of *doing* a transformation, only of *recognizing when*
one applies. Adding matchers here is explicitly allowed (CLAUDE.md §6.3,
PROMPT.md Step 3); the positive signal P5 counts registered matchers.

Contract (RULE_FORMAT §4): each matcher is

    match(patterns: dict, params: dict | None) -> bool

deterministic and side-effect-free. `patterns` is the dict produced by
`ExtractPatternOperator` (agent/active_operators.py); `params` is the rule's
`condition.params` (with an optional `min_evidence`).

Matchers live in sibling modules (`agent/conditions/<name>.py`) and self-register
via the register decorator. They are auto-imported on package load so
`CONDITION_REGISTRY` is populated by simply importing `agent.conditions`.
"""

import importlib
import os
import pkgutil

#: name -> matcher callable
CONDITION_REGISTRY: dict = {}


def register(name: str):
    """Decorator: register a matcher under `name`. Duplicate names are an error
    (two matchers claiming the same recognition slot is a bug, not an override)."""
    def _decorator(fn):
        if name in CONDITION_REGISTRY:
            raise ValueError(f"duplicate condition matcher registered: {name!r}")
        CONDITION_REGISTRY[name] = fn
        return fn
    return _decorator


def get_matcher(name: str):
    """Return the matcher registered under `name`, or None if unknown."""
    return CONDITION_REGISTRY.get(name)


def match(name: str, patterns: dict, params: dict | None = None) -> bool:
    """Run a registered matcher by name. Raises KeyError for an unknown name so
    a rule referencing a non-existent `condition.type` fails loudly (RULE_FORMAT
    V2), rather than silently never firing."""
    fn = CONDITION_REGISTRY.get(name)
    if fn is None:
        raise KeyError(f"unknown condition.type: {name!r}")
    return bool(fn(patterns, params))


def _autoload_matchers() -> None:
    """Import every sibling module so its `@register` runs on package import."""
    package_dir = os.path.dirname(__file__)
    for mod in pkgutil.iter_modules([package_dir]):
        if mod.name == "__init__":
            continue
        importlib.import_module(f"{__name__}.{mod.name}")


_autoload_matchers()
