"""
agent.conditions — the condition-matcher registry.

This package holds ARBOR's *recognition* vocabulary: the `condition.type`
names a rule may reference (CLAUDE.md §3.2 / §6.3, docs/RULE_FORMAT.md §4).
A matcher answers *when* a (composed) action applies; it never performs a
transformation, so growing this registry is allowed (unlike the frozen DSL,
F3) and is tracked by positive signal P5.

A matcher is a deterministic, side-effect-free callable:

    match(patterns: dict, params: dict) -> bool

`patterns` is the output of `extract_pattern` (the COMM/DIFF-derived dict);
`params` is the rule's `condition.params`. Register one by decorating the
matcher with `register("<name>")` (see color_mapping.py for a worked example).

`save_rule()`/`validate_rule()` (agent/memory.py, check V2) consult
`is_registered()` to reject rules whose `condition.type` is unknown.
"""

CONDITION_REGISTRY: dict = {}


def register(name: str):
    """Decorator registering a matcher under `name`. Names are unique."""
    if not name or not isinstance(name, str):
        raise ValueError(f"condition name must be a non-empty string, got {name!r}")

    def _decorator(fn):
        if name in CONDITION_REGISTRY and CONDITION_REGISTRY[name] is not fn:
            raise ValueError(f"condition.type already registered: {name!r}")
        CONDITION_REGISTRY[name] = fn
        return fn

    return _decorator


def is_registered(name: str) -> bool:
    """True if `name` is a known condition.type (used by validate_rule V2)."""
    return name in CONDITION_REGISTRY


def get_matcher(name: str):
    """Return the matcher callable for `name`, or None if unregistered."""
    return CONDITION_REGISTRY.get(name)


def registered_names() -> list:
    """Sorted list of all registered condition.type names."""
    return sorted(CONDITION_REGISTRY)


def recognized_conditions(patterns: dict) -> list:
    """
    Return the names of every registered matcher that fires on `patterns`
    with empty params. Read-side helper for the (future) schema-aware fast
    path; deterministic and side-effect-free.
    """
    fired = []
    for name in registered_names():
        try:
            if CONDITION_REGISTRY[name](patterns, {}):
                fired.append(name)
        except Exception:
            # A matcher must never crash recognition; an erroring matcher
            # simply does not fire. (Matchers are side-effect-free.)
            continue
    return fired


# Importing the matcher modules runs their @register decorators. Keep this at
# the bottom so the registry helpers above are defined first.
from agent.conditions import color_mapping as _color_mapping  # noqa: E402,F401
from agent.conditions import recolor_sequential as _recolor_sequential  # noqa: E402,F401
