"""
anti_unification — lift two or more rules sharing a structural skeleton into a
single abstract rule, replacing the positions where they disagree with
generalization variables (``?v1``, ``?v2`` …).

This is the **only** mechanism in ARBOR by which transformational vocabulary
may grow (the hand-coded DSL is frozen at ``coloring`` / ``make_grid`` — see
``CLAUDE.md §6.2`` and ``docs/INVARIANTS.md §1 F3``). The public contract is
specified in full in ``docs/ANTI_UNIFICATION.md``; this module implements the
**leaf case** of that spec (§2): value positions that compare via ``==``.
Recursive anti-unification of nested term trees (``coloring(coloring(…), …)``
compositions, term-tree alignment DP) is intentionally out of scope here — when
two inputs' container args differ they are lifted as a single variable.

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

    Keys are unioned in first-seen order. A key whose value is equal across
    *all* inputs keeps that value (deep-copied so no aliasing leaks between
    rules); any other key — differing values, or present in only some inputs —
    is lifted to a fresh ``?vN`` variable recorded in ``substitutions`` under
    ``<prefix>.<key>``.
    """
    out: dict = {}
    keys = []
    for d in dicts:
        for k in (d or {}):
            if k not in keys:
                keys.append(k)

    for key in keys:
        values = [(d or {}).get(key, _MISSING) for d in dicts]
        first = values[0]
        agree = first is not _MISSING and all(v == first for v in values[1:])
        if agree:
            out[key] = copy.deepcopy(first)
        else:
            var_counter[0] += 1
            var = f"?v{var_counter[0]}"
            out[key] = var
            substitutions[f"{prefix}.{key}"] = var
    return out


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
