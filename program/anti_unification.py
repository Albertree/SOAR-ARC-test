"""
anti_unification — lift two or more rules sharing a structural skeleton into a
single abstract rule, replacing the positions where they disagree with
generalization variables (``?v1``, ``?v2`` …).

This is the **only** mechanism in ARBOR by which transformational vocabulary
may grow (the hand-coded DSL is frozen at ``coloring`` / ``make_grid`` — see
``CLAUDE.md §6.2`` and ``docs/INVARIANTS.md §1 F3``). The public contract is
specified in full in ``docs/ANTI_UNIFICATION.md``; this module implements the
**leaf case** of that spec (§2) plus a **recursive descent into nested sequence
terms**. A value position whose inputs are *sequences of equal length* (the
synthesized-program term trees of modules F/G — a program is a list of step
tuples, each ``(primitive, *expr)``) is anti-unified element-wise so that only the
leaf positions where the inputs disagree become ``?vN`` variables and the shared
skeleton is preserved (e.g. two object-reconstruction resizes that differ only in
the fitted output dim lift to ``[make_grid([const, ?v1], [const, ?v2], [bg]),
paint_objects([all_objects])]``, not to a single opaque ``?v`` over the whole
program). Positions that are *dicts*, sequences of unequal length, or scalars are
still lifted whole — recursive descent into dict-valued descriptors (object_motion
``target`` dicts) is intentionally kept at the leaf grain so the family rules'
abstractions are unchanged.

Call site: ``CLAUDE.md §8`` names ``agent/memory.py:save_rule()`` as the *only*
permitted caller of :func:`unify`.
"""

import copy
import json
import os
from dataclasses import dataclass
from datetime import datetime

_MISSING = object()


class NoCommonSkeleton(ValueError):
    """Raised when the input rules cannot be anti-unified at this level.

    The inputs disagree on a *skeleton* field (``condition.type`` or
    ``action.dsl``), or fewer than two rules were supplied. Bridging a
    skeleton mismatch requires object-level lifting, a separate concern
    (``CLAUDE.md §8`` failure modes; wiki ``[[object-level-lifting]]``).
    """


@dataclass
class UnifyResult:
    """Result of one :func:`unify` call (``docs/ANTI_UNIFICATION.md §1.2``)."""

    abstract_rule: dict
    trace_path: "str | None"
    substitutions: dict

    def is_more_general(self) -> bool:
        """True iff ≥ 1 position was lifted to a variable.

        When False the inputs are already structurally identical and the
        caller should merge their ``covers`` lists rather than persist a new
        rule.
        """
        return bool(self.substitutions)


def unify(rules, *, episodic_memory_root: str = "episodic_memory") -> UnifyResult:
    """Anti-unify two or more rules sharing the same structural skeleton.

    See ``docs/ANTI_UNIFICATION.md §1.1`` for the full contract. Briefly:
    all inputs must agree on ``condition.type`` and ``action.dsl``; each
    ``condition.params`` / ``action.args`` position where they agree is kept
    (deep-copied), and each position where they disagree — or that is absent
    from some input — is lifted to a fresh ``?vN`` variable. A forensic trace
    JSON is written under
    ``<episodic_memory_root>/<source_task>/anti_unification/au_NNN.json`` iff
    at least one position was lifted.

    Raises :class:`NoCommonSkeleton` on a skeleton mismatch or fewer than two
    inputs.
    """
    rules = list(rules)
    if len(rules) < 2:
        raise NoCommonSkeleton(
            f"unify needs >= 2 rules to anti-unify, got {len(rules)}"
        )

    cond_types = [r["condition"]["type"] for r in rules]
    if len(set(cond_types)) > 1:
        raise NoCommonSkeleton(
            f"input rules disagree on condition.type: {sorted(set(cond_types))}"
        )
    dsls = [r["action"]["dsl"] for r in rules]
    if len(set(dsls)) > 1:
        raise NoCommonSkeleton(
            f"input rules disagree on action.dsl: {sorted(set(dsls))}"
        )

    cond_type = cond_types[0]
    dsl = dsls[0]

    var_counter = [0]  # mutable counter shared across both field groups
    substitutions: dict = {}

    abstract_params = _anti_unify_fields(
        [r["condition"].get("params", {}) for r in rules],
        "condition.params", var_counter, substitutions,
    )
    abstract_args = _anti_unify_fields(
        [r["action"].get("args", {}) for r in rules],
        "action.args", var_counter, substitutions,
    )

    min_evidence = max(
        (r["condition"].get("min_evidence", 1) for r in rules), default=1
    )
    covers = _union_preserve_order(r.get("covers", []) for r in rules)

    last = rules[-1]
    source_task = last.get("source_task", "")

    trace_path = None
    if substitutions:
        trace_path = _write_trace(
            rules, cond_type, dsl, substitutions,
            episodic_memory_root, source_task,
        )

    abstract_rule = {
        "id": last.get("id"),
        "concept": last.get("concept", ""),
        "category": last.get("category", ""),
        "condition": {
            "type": cond_type,
            "params": abstract_params,
            "min_evidence": min_evidence,
        },
        "action": {
            "dsl": dsl,
            "args": abstract_args,
        },
        "covers": covers,
        "source_task": source_task,
        "anti_unification_trace": trace_path,
        "created_at": datetime.now().isoformat(),
        "times_reused": 0,
    }

    return UnifyResult(
        abstract_rule=abstract_rule,
        trace_path=trace_path,
        substitutions=substitutions,
    )


# Back-compat alias: the historical public name in ``program/__init__.py``.
anti_unify = unify


# ======================================================================
# Internal helpers
# ======================================================================

def _anti_unify_fields(dicts, prefix, var_counter, substitutions) -> dict:
    """Field-wise anti-unification over a list of same-role dicts.

    Keys are unioned in first-seen order. Each key's values across the inputs are
    handed to :func:`_anti_unify_value`, which keeps a position the inputs agree
    on, descends into nested sequence terms, and lifts genuine leaf disagreements
    to a fresh ``?vN`` variable recorded in ``substitutions`` under the position
    path (``<prefix>.<key>`` for a leaf, ``…[i]`` deeper for sequence elements).
    """
    out: dict = {}
    keys = []
    for d in dicts:
        for k in (d or {}):
            if k not in keys:
                keys.append(k)

    for key in keys:
        values = [(d or {}).get(key, _MISSING) for d in dicts]
        out[key] = _anti_unify_value(
            values, f"{prefix}.{key}", var_counter, substitutions
        )
    return out


def _anti_unify_value(values, prefix, var_counter, substitutions):
    """Anti-unify one structural position (a list of same-position values across
    the input rules) into either a kept concrete value, a nested list with ``?vN``
    holes, or a single ``?vN`` variable.

    * A position absent from some input (``_MISSING``) is lifted whole.
    * A position the inputs *agree* on (list/tuple round-trip insensitive) keeps a
      deep copy of the value — no aliasing leaks between rules.
    * A position whose inputs are all sequences of *equal, non-zero length* is
      descended into element-wise, preserving the shared skeleton and lifting only
      the disagreeing leaves (the synthesized-program term-tree case).
    * Anything else (scalars, dicts, ragged/short sequences) is lifted whole.
    """
    if any(v is _MISSING for v in values):
        return _fresh_var(prefix, var_counter, substitutions)

    norm_first = _normalize(values[0])
    if all(_normalize(v) == norm_first for v in values[1:]):
        return copy.deepcopy(norm_first)

    if (all(isinstance(v, (list, tuple)) for v in values)
            and len({len(v) for v in values}) == 1
            and len(values[0]) > 0):
        n = len(values[0])
        return [
            _anti_unify_value(
                [v[i] for v in values], f"{prefix}[{i}]",
                var_counter, substitutions,
            )
            for i in range(n)
        ]

    return _fresh_var(prefix, var_counter, substitutions)


def _fresh_var(prefix, var_counter, substitutions) -> str:
    """Mint the next ``?vN`` variable, record it under ``prefix``, and return it."""
    var_counter[0] += 1
    var = f"?v{var_counter[0]}"
    substitutions[prefix] = var
    return var


def _normalize(v):
    """Recursively render tuples as lists (and copy dicts) so a value that was a
    tuple in memory compares equal to the same value once JSON round-tripped it to
    a list — synthesized programs are tuples when first built, lists when reloaded
    from a stored rule."""
    if isinstance(v, dict):
        return {k: _normalize(x) for k, x in v.items()}
    if isinstance(v, (list, tuple)):
        return [_normalize(e) for e in v]
    return v


def _union_preserve_order(lists) -> list:
    """Flatten an iterable of lists into a de-duplicated, first-seen-order list."""
    out = []
    for lst in lists:
        for item in (lst or []):
            if item not in out:
                out.append(item)
    return out


def _write_trace(rules, cond_type, dsl, substitutions,
                 episodic_memory_root, source_task) -> str:
    """Write the immutable forensic trace JSON and return its forward-slash path.

    Shape per ``docs/ANTI_UNIFICATION.md §3``. The sequence number ``NNN``
    monotonically increases; a re-run that produces the same abstraction
    creates a new ``au_NNN.json`` rather than overwriting one.
    """
    trace_dir = os.path.join(episodic_memory_root, source_task, "anti_unification")
    os.makedirs(trace_dir, exist_ok=True)

    existing = [
        f for f in os.listdir(trace_dir)
        if f.startswith("au_") and f.endswith(".json")
    ]
    seq = len(existing) + 1
    fname = f"au_{seq:03d}.json"

    trace = {
        "input_rules": [
            {"id": r.get("id"), "source_task": r.get("source_task")}
            for r in rules
        ],
        "skeleton": {
            "condition_type": cond_type,
            "action_dsl": dsl,
        },
        "substitutions": substitutions,
        "var_count": len(substitutions),
        "created_at": datetime.now().isoformat(),
    }

    with open(os.path.join(trace_dir, fname), "w") as fh:
        json.dump(trace, fh, indent=2)

    # Stored path uses forward slashes so it matches the docs/RULE_FORMAT.md §1
    # V5 regex on every platform.
    return "/".join([episodic_memory_root, source_task, "anti_unification", fname])
