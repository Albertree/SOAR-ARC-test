"""
anti_unification — find the most-specific common skeleton across rules and
lift positions where they disagree into generalization variables.

This module implements ``CLAUDE.md §8``. The sole public entry point is
``unify(rules)``. Full contract, trace JSON shape, and integration point
are documented in ``docs/ANTI_UNIFICATION.md``.

Quick summary:

* ``UnifyResult`` — returned on a successful skeleton match.
  - ``abstract_rule``: the lifted rule dict.
  - ``trace_path``: relative path (forward slashes) to the trace JSON
    written under ``episodic_memory/<source_task>/anti_unification/``,
    or ``None`` if no positions were lifted.
  - ``substitutions``: ``{dotted_field_path: variable_name}`` map.
  - ``.is_more_general()``: True iff at least one position was lifted.

* ``NoCommonSkeleton`` — raised when inputs disagree on
  ``condition.type`` or ``action.dsl``, or when fewer than two rules
  are supplied. Caller should leave the input rules unchanged.

This iter implements the leaf-level case: positional anti-unification over
``condition.params`` and ``action.args``. Recursive term-tree alignment
(DSL composition trees) is out of scope; a future iter extends the
algorithm without breaking the public API documented above.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from datetime import datetime
from typing import Any

EPISODIC_MEMORY_ROOT = "episodic_memory"


class NoCommonSkeleton(ValueError):
    """Inputs to :func:`unify` share no common ``(condition.type, action.dsl)``
    skeleton — anti-unification at this level cannot bridge primitive
    boundaries. See ``docs/ANTI_UNIFICATION.md`` §1.1."""


@dataclass
class UnifyResult:
    """See ``docs/ANTI_UNIFICATION.md`` §1.2."""

    abstract_rule: dict
    trace_path: str | None
    substitutions: dict

    def is_more_general(self) -> bool:
        return bool(self.substitutions)


def _var_name(counter: list) -> str:
    counter[0] += 1
    return f"?v{counter[0]}"


def _all_equal(values: list) -> bool:
    first = values[0]
    return all(v == first for v in values[1:])


def _deep_copy_via_json(value: Any) -> Any:
    """Defensive copy for nested containers. The rule dicts coming into
    unify() may be aliased by callers; we don't want abstract_rule to
    share references with the inputs."""
    if isinstance(value, (dict, list)):
        return json.loads(json.dumps(value))
    return value


def _anti_unify_position(values: list, counter: list) -> Any:
    """Anti-unify a list of values at a single position. Return the shared
    value (deep-copied) if all inputs agree, else a fresh variable."""
    if _all_equal(values):
        return _deep_copy_via_json(values[0])
    return _var_name(counter)


def _anti_unify_dict(dicts: list, counter: list, path_prefix: str,
                     substitutions: dict) -> dict:
    """Element-wise anti-unify a list of dicts. Keys present in some but
    not all inputs are treated as a disagreement and lifted to a fresh
    variable. Records every lifted position in ``substitutions``."""
    out: dict = {}
    all_keys = set()
    for d in dicts:
        all_keys.update(d.keys())
    for k in sorted(all_keys):
        dotted = f"{path_prefix}.{k}"
        if all(k in d for d in dicts):
            unified = _anti_unify_position([d[k] for d in dicts], counter)
            out[k] = unified
            if isinstance(unified, str) and unified.startswith("?v"):
                substitutions[dotted] = unified
        else:
            var = _var_name(counter)
            out[k] = var
            substitutions[dotted] = var
    return out


def _next_trace_id(trace_dir: str) -> int:
    if not os.path.isdir(trace_dir):
        return 1
    existing = [
        n for n in os.listdir(trace_dir)
        if n.startswith("au_") and n.endswith(".json")
    ]
    return len(existing) + 1


def unify(rules: list, *,
          episodic_memory_root: str = EPISODIC_MEMORY_ROOT) -> UnifyResult:
    """Anti-unify a list of rules into an abstract rule.

    See ``docs/ANTI_UNIFICATION.md`` §1.1 for the full contract.
    """
    if not isinstance(rules, list) or len(rules) < 2:
        n = len(rules) if isinstance(rules, list) else "non-list"
        raise NoCommonSkeleton(f"unify requires >= 2 rules, got {n}")

    # Skeleton match: condition.type and action.dsl must agree across inputs.
    cond_types = {r.get("condition", {}).get("type") for r in rules}
    if len(cond_types) != 1 or None in cond_types:
        raise NoCommonSkeleton(
            f"input rules disagree on condition.type: "
            f"{sorted(map(repr, cond_types))}"
        )
    dsl_names = {r.get("action", {}).get("dsl") for r in rules}
    if len(dsl_names) != 1 or None in dsl_names:
        raise NoCommonSkeleton(
            f"input rules disagree on action.dsl: "
            f"{sorted(map(repr, dsl_names))}"
        )

    cond_type = next(iter(cond_types))
    dsl_name = next(iter(dsl_names))
    counter = [0]
    substitutions: dict = {}

    # Anti-unify condition.params and action.args element-wise.
    unified_params = _anti_unify_dict(
        [r["condition"]["params"] for r in rules],
        counter, "condition.params", substitutions,
    )
    unified_args = _anti_unify_dict(
        [r["action"]["args"] for r in rules],
        counter, "action.args", substitutions,
    )

    # min_evidence: the strictest input wins.
    min_ev = max(int(r["condition"].get("min_evidence", 1)) for r in rules)

    # covers: union, de-duplicated, first-seen order preserved.
    seen: set = set()
    union_covers: list = []
    for r in rules:
        for t in r.get("covers", []):
            if t not in seen:
                seen.add(t)
                union_covers.append(t)

    # Template fields come from the "new_rule" — the last input in §8 vocab.
    template = rules[-1]
    src_task = template["source_task"]

    # Trace JSON: written only if the unification produced ≥ 1 variable.
    trace_path: str | None
    if substitutions:
        trace_dir = os.path.join(
            episodic_memory_root, src_task, "anti_unification"
        )
        os.makedirs(trace_dir, exist_ok=True)
        next_id = _next_trace_id(trace_dir)
        trace_name = f"au_{next_id:03d}.json"
        # Forward-slash normalisation so the path matches V5's regex on
        # every platform, including Windows.
        trace_path = "/".join(
            [episodic_memory_root, src_task, "anti_unification", trace_name]
        )
        trace_payload = {
            "input_rules": [
                {"id": r.get("id"), "source_task": r.get("source_task")}
                for r in rules
            ],
            "skeleton": {
                "condition_type": cond_type,
                "action_dsl": dsl_name,
            },
            "substitutions": dict(substitutions),
            "var_count": counter[0],
            "created_at": datetime.now().isoformat(),
        }
        # Write through the OS-native path; trace_path string stays
        # forward-slash for the in-rule field.
        with open(os.path.join(trace_dir, trace_name), "w",
                  encoding="utf-8") as fh:
            json.dump(trace_payload, fh, indent=2)
    else:
        trace_path = None

    abstract_rule = {
        "id": template["id"],
        "concept": template.get("concept", ""),
        "category": template.get("category", ""),
        "condition": {
            "type": cond_type,
            "params": unified_params,
            "min_evidence": min_ev,
        },
        "action": {"dsl": dsl_name, "args": unified_args},
        "covers": union_covers,
        "source_task": src_task,
        "anti_unification_trace": trace_path,
        "created_at": datetime.now().isoformat(),
        "times_reused": 0,
    }

    return UnifyResult(
        abstract_rule=abstract_rule,
        trace_path=trace_path,
        substitutions=dict(substitutions),
    )
