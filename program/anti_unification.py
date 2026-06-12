"""
anti_unification — lift a set of rules sharing a structural skeleton into one
abstract rule whose points of disagreement become generalization variables.

This is the **only** mechanism by which ARBOR's transformational vocabulary may
grow (CLAUDE.md §6.2 / §8, docs/INVARIANTS.md F3): the hand-coded DSL is closed
at two primitives, so every other transformation must emerge as a discovered
composition produced by `unify()`. The public contract is specified in
`docs/ANTI_UNIFICATION.md`; this module implements the leaf case (value
positions compared via `==`). Recursive term-tree alignment of nested
`coloring`/`make_grid` compositions is future work — the original-intent stubs
below (`anti_unify_pair_programs`, …) record that design and are not yet wired.

Public API (docs/ANTI_UNIFICATION.md §1):

    from program.anti_unification import unify, UnifyResult, NoCommonSkeleton
    result = unify(rules)                 # raises NoCommonSkeleton on mismatch
    if result.is_more_general():
        rule  = result.abstract_rule
        trace = result.trace_path
"""

import copy
import glob
import json
import os
from dataclasses import dataclass, field
from datetime import datetime

# A position that is absent from a rule's params/args. Distinct from any real
# value, so "key present in some but not all inputs" is detected as disagreement
# (docs/ANTI_UNIFICATION.md §2 step 2) rather than silently matching.
_MISSING = object()

# min_evidence is anti-unified specially (§2 step 3): the strictest input wins,
# it is never lifted to a variable.
_MIN_EVIDENCE = "min_evidence"


class NoCommonSkeleton(ValueError):
    """Raised when the inputs do not share a unifiable skeleton — fewer than two
    rules, or disagreement on `condition.type` / `action.dsl`. Bridging a
    primitive boundary is object-level lifting, a separate concern (CLAUDE.md §8;
    wiki [[object-level-lifting]]) — not papered over here."""


@dataclass
class UnifyResult:
    """Outcome of one anti-unification (docs/ANTI_UNIFICATION.md §1.2)."""

    abstract_rule: dict
    trace_path: str | None
    substitutions: dict = field(default_factory=dict)

    def is_more_general(self) -> bool:
        """True iff ≥1 position was lifted. When False the inputs are already
        structurally identical and the caller should merge their `covers` lists
        rather than persist a new rule."""
        return len(self.substitutions) > 0


def unify(rules: list, *, episodic_memory_root: str = "episodic_memory") -> UnifyResult:
    """Anti-unify two or more rules sharing a skeleton into the most-specific
    common generalization (docs/ANTI_UNIFICATION.md §1.1 / §2).

    `condition.type` and `action.dsl` must be identical across inputs (they are
    the skeleton); every other key in `condition.params` and `action.args` is
    anti-unified positionally — shared values pass through, disagreements lift to
    a fresh `?vN`. `covers` is the order-preserving union; template fields are
    copied from the *last* input (the "new_rule" of CLAUDE.md §8). A trace JSON
    recording which inputs combined and which positions lifted is written under
    `<episodic_memory_root>/<source_task>/anti_unification/au_NNN.json`, unless no
    position lifted (then `trace_path` is None and nothing is written).
    """
    if not isinstance(rules, list) or len(rules) < 2:
        raise NoCommonSkeleton(
            f"unify needs >= 2 rules, got {len(rules) if isinstance(rules, list) else 'non-list'}")

    cond_types = [(_cond(r)).get("type") for r in rules]
    if len(set(cond_types)) != 1:
        raise NoCommonSkeleton(f"input rules disagree on condition.type: {cond_types}")
    dsls = [(_act(r)).get("dsl") for r in rules]
    if len(set(dsls)) != 1:
        raise NoCommonSkeleton(f"input rules disagree on action.dsl: {dsls}")

    var_counter = [0]
    substitutions: dict = {}

    params_list = [(_cond(r)).get("params") or {} for r in rules]
    args_list = [(_act(r)).get("args") or {} for r in rules]

    abstract_params = _unify_field_dicts(
        params_list, "condition.params", substitutions, var_counter)
    abstract_args = _unify_field_dicts(
        args_list, "action.args", substitutions, var_counter)

    last = rules[-1]
    covers = _union_covers(rules)
    source_task = last.get("source_task") or (covers[0] if covers else "")

    abstract = {
        "id": last.get("id"),
        "concept": last.get("concept") or (_act(last)).get("dsl"),
        "category": last.get("category") or "other",
        "condition": {
            "type": cond_types[0],
            "params": abstract_params,
        },
        "action": {
            "dsl": dsls[0],
            "args": abstract_args,
        },
        "covers": covers,
        "source_task": source_task,
        "anti_unification_trace": None,
        "created_at": datetime.now().isoformat(),
        "times_reused": 0,
    }

    trace_path = None
    if substitutions:
        trace_path = _write_trace(
            rules, cond_types[0], dsls[0], substitutions, episodic_memory_root)
        abstract["anti_unification_trace"] = trace_path

    return UnifyResult(abstract_rule=abstract, trace_path=trace_path,
                       substitutions=substitutions)


# ----------------------------------------------------------------------
# Internal helpers
# ----------------------------------------------------------------------

def _cond(rule: dict) -> dict:
    return rule.get("condition") or {}


def _act(rule: dict) -> dict:
    return rule.get("action") or {}


def _unify_field_dicts(dicts: list, prefix: str, substitutions: dict,
                       var_counter: list) -> dict:
    """Field-wise anti-unify a list of param/arg dicts (§2 step 2). Returns the
    abstract dict; records lifted positions in `substitutions` as
    `{prefix.key: ?vN}`. `min_evidence` is never lifted — the max wins (§2 step
    3)."""
    keys = []
    for d in dicts:
        for k in d:
            if k not in keys:
                keys.append(k)

    out = {}
    for k in keys:
        if k == _MIN_EVIDENCE:
            present = [d[k] for d in dicts if k in d]
            try:
                out[k] = max(present)
            except (TypeError, ValueError):
                out[k] = present[-1]
            continue
        values = [d.get(k, _MISSING) for d in dicts]
        if _all_equal(values):
            out[k] = copy.deepcopy(values[0])
        else:
            var_counter[0] += 1
            var = f"?v{var_counter[0]}"
            out[k] = var
            substitutions[f"{prefix}.{k}"] = var
    return out


def _all_equal(values: list) -> bool:
    first = values[0]
    if first is _MISSING:
        # a position missing from the first input is a disagreement unless it is
        # missing from *every* input (then the key would not be in `keys`).
        return all(v is _MISSING for v in values)
    return all((v is not _MISSING) and (v == first) for v in values)


def _union_covers(rules: list) -> list:
    seen = set()
    out = []
    for r in rules:
        for t in r.get("covers") or []:
            if t not in seen:
                seen.add(t)
                out.append(t)
    return out


def _write_trace(rules: list, cond_type: str, action_dsl: str,
                 substitutions: dict, episodic_memory_root: str) -> str:
    """Write the immutable audit trace (docs/ANTI_UNIFICATION.md §3) and return
    its forward-slash relative path. A re-run that produces the same abstraction
    allocates the next `au_NNN.json` rather than overwriting an existing one."""
    source_task = rules[-1].get("source_task") or "unknown"
    rel_dir = f"{episodic_memory_root}/{source_task}/anti_unification"
    os.makedirs(rel_dir, exist_ok=True)

    existing = glob.glob(os.path.join(rel_dir, "au_*.json"))
    next_n = len(existing) + 1
    rel_path = f"{rel_dir}/au_{next_n:03d}.json"

    trace = {
        "input_rules": [
            {"id": r.get("id"), "source_task": r.get("source_task")} for r in rules
        ],
        "skeleton": {"condition_type": cond_type, "action_dsl": action_dsl},
        "substitutions": substitutions,
        "var_count": len(substitutions),
        "created_at": datetime.now().isoformat(),
    }
    with open(rel_path, "w", encoding="utf-8") as fh:
        json.dump(trace, fh, indent=2)
    return rel_path.replace("\\", "/")


# ======================================================================
# Original-intent stubs — recursive term-tree anti-unification (future).
# Not yet wired; `unify()` above implements the leaf case used by R3.
# ======================================================================

def anti_unify_pair_programs(pair_programs: list) -> list:
    """INTENT: anti-unify flat program-line lists from multiple pairs into
    abstract `?vN`-bearing program lines (CLAUDE.md §8). Future term-tree work."""
    raise NotImplementedError("recursive program-line anti-unification is future work")
