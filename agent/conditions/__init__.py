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
from typing import Callable, Dict, List, Optional

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


def recognized_conditions(patterns: dict,
                          params_per_type: Optional[Dict[str, dict]] = None
                          ) -> List[str]:
    """Run every registered matcher against ``patterns`` and return the
    names of those that fire, in CONDITION_REGISTRY insertion order.

    This is the runtime applier for the recognition vocabulary built across
    iters 1/8/10. Until now the registry has been read only by V2 inside
    ``agent.memory.validate_rule`` (a *static* schema check on persisted
    rules) — there has been no entry point that *runs* matchers against
    a live ``patterns`` dict. Without that entry point matchers are inert
    vocabulary; with it, future iters can wire the same call from the
    slow-path solve into either ``last_solve_info`` (for episodic
    instrumentation) or a rule constructor (to populate
    ``condition.type`` on a discovered rule).

    Parameters
    ----------
    patterns
        The ``patterns`` dict emitted by ``ExtractPatternOperator`` in
        ``agent/active_operators.py``. Non-dict input yields ``[]``.
    params_per_type
        Optional mapping ``condition.type -> params dict`` used as the
        second positional argument to each matcher. Entries missing or
        non-dict default to ``{}`` to match the matchers' params-free
        signature today. The argument exists so a future caller that
        wants to drive parameterised matchers (e.g. boundary-color
        scans) does not need a separate API.

    Returns
    -------
    list[str]
        Names of matchers whose ``match(patterns, params) is True``,
        ordered by registry insertion order (deterministic in CPython
        3.7+).

    Notes
    -----
    * Pure read; never mutates ``patterns`` or the registry.
    * Per the matcher contract (``docs/RULE_FORMAT.md §4`` —
      "deterministic and side-effect-free"), matchers are expected
      to *return* ``False`` on malformed input rather than raise.
      This applier therefore does not swallow exceptions — a raising
      matcher is a contract violation, not silent corruption (F7).
    """
    if not isinstance(patterns, dict):
        return []
    if not isinstance(params_per_type, dict):
        params_per_type = {}
    fired: List[str] = []
    for name, matcher in CONDITION_REGISTRY.items():
        params = params_per_type.get(name, {})
        if not isinstance(params, dict):
            params = {}
        if matcher(patterns, params) is True:
            fired.append(name)
    return fired


def _autoload_matchers() -> None:
    """Import every sibling module so its @register decorators run."""
    pkg_name = __name__
    pkg_path = __path__  # type: ignore[name-defined]
    for mod in pkgutil.iter_modules(pkg_path):
        if mod.name.startswith("_"):
            continue
        importlib.import_module(f"{pkg_name}.{mod.name}")


_autoload_matchers()
