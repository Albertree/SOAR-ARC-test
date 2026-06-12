"""
memory — SOAR procedural memory (rule storage and retrieval).

Each rule is stored as a JSON file in procedural_memory/:
  procedural_memory/rule_001.json
  procedural_memory/rule_002.json
  ...

Rule schema:
  {
    "id":          <int>          — unique sequential ID,
    "concept":     "<str>"        — short human-readable name (e.g. "swap_two_colors"),
    "category":    "<str>"        — color_transform | spatial_transform |
                                    geometric_transform | fill_transform | other,
    "rule":        { ... }        — the actual rule parameters used by PredictOperator,
    "covers":      ["<task_id>"]  — all tasks this rule has successfully handled,
    "source_task": "<task_id>"    — task that first triggered discovery of this rule,
    "created_at":  "<ISO>"        — creation timestamp,
    "times_reused": <int>         — how often the fast-path reused this rule
  }

Design goal: FEW, GENERAL rules — not many specific ones.
When a new rule is equivalent to an existing one, the existing rule's
"covers" list is extended rather than creating a duplicate file.
"""

import json
import os
from datetime import datetime

from program import anti_unification

PROCEDURAL_MEMORY_ROOT = "procedural_memory"

#: The DSL name of the abstract object-move rule produced by anti-unification.
#: Concrete object-move rules (place_object_constant / place_object_relative)
#: are absorbed by an abstract place_object rule whose `readings` include their
#: reading — keeping the lift stable across runs (no churn).
_ABSTRACT_PLACE_OBJECT_DSL = "place_object"


class RuleSchemaError(Exception):
    """A rule violated the canonical {condition, action} schema on save/load.

    Raised (never swallowed — INVARIANTS F7) so an invalid rule fails loudly
    rather than becoming dead memory (the F4 / 168-rule failure mode)."""


# ======================================================================
# Validation
# ======================================================================

def validate_rule(entry: dict) -> None:
    """Raise RuleSchemaError unless `entry` is a canonical {condition, action} rule.

    Structural validation only (CLAUDE.md §3.2, docs/RULE_FORMAT.md): both halves
    present and well-formed, and a non-empty covers list. Task-id *format* is not
    enforced here — the supplied beginner suite uses ids like `easy000a`.
    """
    if not isinstance(entry, dict):
        raise RuleSchemaError(f"rule is not an object: {type(entry).__name__}")
    cond = entry.get("condition")
    act = entry.get("action")
    if not isinstance(cond, dict) or not cond:
        raise RuleSchemaError("rule missing non-empty 'condition'")
    if not isinstance(act, dict) or not act:
        raise RuleSchemaError("rule missing non-empty 'action'")
    if not cond.get("type"):
        raise RuleSchemaError("condition missing 'type'")
    if "params" not in cond:
        raise RuleSchemaError("condition missing 'params'")
    if not isinstance(cond.get("min_evidence"), int):
        raise RuleSchemaError("condition missing integer 'min_evidence'")
    if not act.get("dsl"):
        raise RuleSchemaError("action missing 'dsl'")
    if "args" not in act:
        raise RuleSchemaError("action missing 'args'")
    covers = entry.get("covers")
    if not isinstance(covers, list) or not covers:
        raise RuleSchemaError("rule missing non-empty 'covers'")


def _is_canonical(rule: dict) -> bool:
    """True if `rule` is already in {condition, action} form (not the legacy
    `{type, ...}` shape)."""
    return isinstance(rule, dict) and "condition" in rule and "action" in rule


# ======================================================================
# Public API
# ======================================================================

def save_rule_to_ltm(rule: dict, task_hex: str,
                     procedural_memory_root: str = PROCEDURAL_MEMORY_ROOT) -> str:
    """
    Save a learned rule to procedural_memory.

    Canonical `{condition, action}` rules (CLAUDE.md §3.2) are persisted in the
    canonical schema and validated before write; an equivalent canonical rule
    (same condition.type + action) absorbs the new task into its `covers` list
    instead of spawning a duplicate (the P1/P2 generalization direction). Legacy
    `{type, ...}` rules keep the old `{rule: ...}` envelope for backward compat.

    Returns the file path of the saved (or updated) rule.
    """
    os.makedirs(procedural_memory_root, exist_ok=True)

    if _is_canonical(rule):
        return _save_canonical_rule(rule, task_hex, procedural_memory_root)

    existing = sorted(
        f for f in os.listdir(procedural_memory_root)
        if f.startswith("rule_") and f.endswith(".json")
    )

    # Check for equivalent rule — update covers instead of duplicating
    for fname in existing:
        path = os.path.join(procedural_memory_root, fname)
        try:
            with open(path, "r") as fh:
                stored = json.load(fh)
            if _rules_equivalent(stored.get("rule", {}), rule):
                covers = stored.get("covers", [stored.get("source_task", "")])
                if task_hex not in covers:
                    covers.append(task_hex)
                    stored["covers"] = covers
                    with open(path, "w") as fh:
                        json.dump(stored, fh, indent=2)
                return path
        except (json.JSONDecodeError, IOError):
            continue

    # New rule — assign next ID and build full entry
    next_id = _next_rule_id(existing)
    entry = {
        "id": next_id,
        "concept": _infer_concept(rule),
        "category": _infer_category(rule),
        "rule": rule,
        "covers": [task_hex],
        "source_task": task_hex,
        "created_at": datetime.now().isoformat(),
        "times_reused": 0,
    }

    filename = f"rule_{next_id:03d}.json"
    path = os.path.join(procedural_memory_root, filename)
    with open(path, "w") as fh:
        json.dump(entry, fh, indent=2)

    return path


def _save_canonical_rule(rule: dict, task_hex: str,
                         procedural_memory_root: str) -> str:
    """Persist a {condition, action} rule, merging into an equivalent existing
    rule's covers when one is found."""
    existing = sorted(
        f for f in os.listdir(procedural_memory_root)
        if f.startswith("rule_") and f.endswith(".json")
    )

    for fname in existing:
        path = os.path.join(procedural_memory_root, fname)
        try:
            with open(path, "r") as fh:
                stored = json.load(fh)
        except (json.JSONDecodeError, IOError):
            continue
        # An abstract lift rule (R3) absorbs a concrete rule whose argument value
        # (object-move reading / size-grid dimension property) it already ranges
        # over — so re-discovering the concrete rule on a later run merges its
        # task into the abstraction rather than re-spawning the source (no churn,
        # the lift stays stable).
        if _abstract_absorbs(stored, rule):
            covers = stored.get("covers", [])
            if task_hex not in covers:
                covers.append(task_hex)
                stored["covers"] = covers
                validate_rule(stored)
                with open(path, "w") as fh:
                    json.dump(stored, fh, indent=2)
            return path
        if _canonical_equivalent(stored, rule):
            covers = stored.get("covers", [])
            if task_hex not in covers:
                covers.append(task_hex)
                stored["covers"] = covers
                validate_rule(stored)
                with open(path, "w") as fh:
                    json.dump(stored, fh, indent=2)
            _consolidate_all(procedural_memory_root)
            return path

    next_id = _next_rule_id(existing)
    cond = rule["condition"]
    act = rule["action"]
    entry = {
        "id": next_id,
        "concept": rule.get("concept") or cond.get("type", "rule"),
        "category": rule.get("category") or cond.get("type", "other"),
        "condition": {
            "type": cond.get("type"),
            "params": cond.get("params", {}),
            "min_evidence": cond.get("min_evidence", 2),
        },
        "action": {
            "dsl": act.get("dsl"),
            "args": act.get("args", {}),
        },
        "covers": [task_hex],
        "source_task": task_hex,
        "anti_unification_trace": None,
        "created_at": datetime.now().isoformat(),
        "times_reused": 0,
    }
    validate_rule(entry)

    filename = f"rule_{next_id:03d}.json"
    path = os.path.join(procedural_memory_root, filename)
    with open(path, "w") as fh:
        json.dump(entry, fh, indent=2)
    # A freshly-created rule may complete a liftable pair with an existing
    # sibling — attempt the R3 lift now (CLAUDE.md §8 single call site).
    _consolidate_all(procedural_memory_root)
    return path


def _canonical_equivalent(stored: dict, rule: dict) -> bool:
    """Two canonical rules are equivalent when their condition.type and action
    (dsl + args) match — i.e. the same recognition→transformation skeleton."""
    if not _is_canonical(stored):
        return False
    sc, rc = stored.get("condition", {}), rule.get("condition", {})
    sa, ra = stored.get("action", {}), rule.get("action", {})
    return (
        sc.get("type") == rc.get("type")
        and sa.get("dsl") == ra.get("dsl")
        and _norm_dict(sa.get("args", {})) == _norm_dict(ra.get("args", {}))
    )


# ======================================================================
# Anti-unification (R3) — the single permitted call site (CLAUDE.md §8)
# ======================================================================

def _abstract_absorbs(stored: dict, rule: dict) -> bool:
    """True if `stored` is an abstract lift rule whose ranged-over values already
    include the concrete `rule`'s lifted argument (object-move reading or
    size-grid dimension property) — so the concrete rule is subsumed and merely
    adds its task to the abstraction's covers (no re-spawn, the lift stays
    stable)."""
    if not _is_canonical(stored) or not _is_canonical(rule):
        return False
    fam = anti_unification.family_for_rule(rule)
    if fam is None:
        return False
    key = fam["key"](rule)
    if key is None:
        return False
    if stored.get("category") != fam["category"]:
        return False
    sargs = stored.get("action", {}).get("args", {})
    if fam["list_key"] not in sargs:           # stored is not the abstraction
        return False
    return key in anti_unification.abstract_values(stored, fam)


def save_rule(new_rule: dict, source_task: str, related_rules: list):
    """The ONLY function permitted to invoke anti_unification.unify (CLAUDE.md §8).

    Given a newly-saved canonical rule and the related rules sharing its category,
    attempt to lift them into one abstract rule. Returns the AntiUnifyResult when
    a more-general abstraction was found, else None — the caller leaves the input
    rules unchanged on None (the NoCommonSkeleton failure mode)."""
    if not related_rules:
        return None
    result = anti_unification.unify(list(related_rules) + [new_rule])
    if result is not None and result.is_more_general():
        return result
    return None


def _consolidate_all(procedural_memory_root: str) -> None:
    """Attempt the R3 lift for every liftable family (CLAUDE.md §8). Each family
    is folded independently through the single AU call site save_rule()→unify()."""
    for fam in anti_unification.LIFT_FAMILIES:
        _consolidate_family(procedural_memory_root, fam)


def _consolidate_family(procedural_memory_root: str, fam: dict) -> None:
    """Lift one liftable family into a single abstract rule (BACKLOG_LOOP R3).

    Family-generic over `anti_unification.LIFT_FAMILIES`: ``object_move`` collapses
    the placement readings into ``place_object``; ``object_size_grid`` collapses
    the canvas-sizing dimension properties (object_size, bbox_height, …) into one
    ``size_to_grid`` rule. Two cases, both routed through the single AU call site:

    (a) **first lift** — ≥2 standalone concrete rules with *distinct* lifted
        values (e.g. constant_target + constant_offset, or object_size +
        bbox_height) collapse into one abstraction.
    (b) **re-lift** — an existing abstraction plus a standalone concrete carrying
        a value the abstraction does not yet range over is folded in.

    On success, writes the abstract rule into the lowest-id family file
    (covers = union), records the anti_unification_trace, and removes the now
    subsumed siblings. Idempotent: once every family value lives in the
    abstraction, re-discovered concretes are absorbed at save time so a re-run
    finds no standalone concrete and no-ops (the §2.5-4 direction — rule count
    falls while covers rises)."""
    rules = []
    for fname in sorted(os.listdir(procedural_memory_root)):
        if not (fname.startswith("rule_") and fname.endswith(".json")):
            continue
        path = os.path.join(procedural_memory_root, fname)
        try:
            with open(path, "r") as fh:
                r = json.load(fh)
        except (json.JSONDecodeError, IOError):
            continue
        r["_path"] = path
        rules.append(r)

    family = [r for r in rules if r.get("category") == fam["category"]]
    concrete = [r for r in family if fam["key"](r) is not None]
    abstract = [r for r in family
                if fam["list_key"] in r.get("action", {}).get("args", {})]
    if not concrete:
        return  # nothing un-lifted to fold

    # Every value the family spans: those already lifted into an abstraction plus
    # those carried by standalone concrete rules.
    abstract_vals = set()
    for a in abstract:
        abstract_vals |= set(anti_unification.abstract_values(a, fam))
    concrete_vals = {fam["key"](r) for r in concrete}
    all_vals = abstract_vals | concrete_vals
    if len(all_vals) < 2:
        return  # not enough distinct values to generalise

    # Synthesize one concrete rule per distinct value so unify (the single AU
    # call site) lifts the whole family uniformly, whether a value comes from a
    # standalone concrete rule or an existing abstraction's ranged-over list.
    synth = [fam["synth"](v) for v in sorted(all_vals)]
    result = save_rule(synth[-1], "", synth[:-1])
    if result is None:
        return

    # Deterministic host: lowest-id family file. covers = union over the family.
    family.sort(key=lambda r: r.get("id", 0))
    host = family[0]
    covers = []
    for r in family:
        for t in r.get("covers", []):
            if t not in covers:
                covers.append(t)

    source_task = host.get("source_task") or (covers[0] if covers else "")
    trace_path = result.write_trace(source_task)

    abstract_rule = dict(result.abstract_rule)
    entry = {
        "id": host.get("id", _next_rule_id(
            [os.path.basename(r["_path"]) for r in rules])),
        "concept": abstract_rule.get("concept", fam["concept"]),
        "category": abstract_rule.get("category", fam["category"]),
        "condition": abstract_rule["condition"],
        "action": abstract_rule["action"],
        "covers": covers,
        "source_task": source_task,
        "anti_unification_trace": trace_path,
        "created_at": host.get("created_at", datetime.now().isoformat()),
        "times_reused": 0,
    }
    validate_rule(entry)

    with open(host["_path"], "w") as fh:
        json.dump(entry, fh, indent=2)
    for r in family[1:]:
        try:
            os.remove(r["_path"])
        except OSError:
            pass


def _next_rule_id(existing) -> int:
    """Next monotonic id: max existing id + 1 (never reuses a deleted id)."""
    max_id = 0
    for fname in existing:
        try:
            n = int(fname[len("rule_"):-len(".json")])
            max_id = max(max_id, n)
        except ValueError:
            continue
    return max_id + 1


def load_all_rules(procedural_memory_root: str = PROCEDURAL_MEMORY_ROOT) -> list:
    """
    Load all stored rules. Returns list of entry dicts sorted by
    times_reused descending so the most-proven rules are tried first.
    """
    if not os.path.isdir(procedural_memory_root):
        return []

    rules = []
    for fname in sorted(os.listdir(procedural_memory_root)):
        if not (fname.startswith("rule_") and fname.endswith(".json")):
            continue
        path = os.path.join(procedural_memory_root, fname)
        try:
            with open(path, "r") as fh:
                entry = json.load(fh)
            entry["_path"] = path
            rules.append(entry)
        except (json.JSONDecodeError, IOError):
            continue

    rules.sort(key=lambda e: e.get("times_reused", 0), reverse=True)
    return rules


def increment_reuse_count(entry: dict) -> None:
    """Increment times_reused for a stored rule and persist the change."""
    path = entry.get("_path")
    if not path or not os.path.exists(path):
        return
    try:
        with open(path, "r") as fh:
            data = json.load(fh)
        data["times_reused"] = data.get("times_reused", 0) + 1
        with open(path, "w") as fh:
            json.dump(data, fh, indent=2)
    except (json.JSONDecodeError, IOError):
        pass


def load_rules_from_ltm(task_hex: str,
                        semantic_memory_root: str = "semantic_memory") -> list:
    """Legacy interface — task_hex unused, loads all rules."""
    return load_all_rules()


def chunk_from_substate(substate: dict) -> dict:
    """Placeholder — extract rule from resolved substate."""
    return {}


# ======================================================================
# Internal helpers
# ======================================================================

def _rules_equivalent(a: dict, b: dict) -> bool:
    """
    Return True if two rules produce identical transformations.

    Keys in JSON are always strings; keys produced by the pipeline may be
    integers. Both sides are normalised to string keys before comparison.
    """
    if a.get("type") != b.get("type"):
        return False

    t = a.get("type")

    if t == "color_mapping":
        return _norm_mapping(a.get("mapping")) == _norm_mapping(b.get("mapping"))

    if t == "recolor_sequential":
        return (
            a.get("sort_key") == b.get("sort_key")
            and a.get("start_color") == b.get("start_color")
            and sorted(a.get("source_colors") or []) == sorted(b.get("source_colors") or [])
        )

    # For all other types compare the full rule dicts after key normalisation
    return _norm_dict(a) == _norm_dict(b)


def _norm_mapping(mapping) -> dict:
    """Normalise a color mapping to {str: int} regardless of source key type."""
    if not mapping:
        return {}
    return {str(k): int(v) for k, v in mapping.items()}


def _norm_dict(d: dict) -> dict:
    """Recursively normalise all dict keys to strings."""
    if not isinstance(d, dict):
        return d
    return {str(k): _norm_dict(v) for k, v in d.items()}


def _infer_concept(rule: dict) -> str:
    """Derive a short concept name from the rule type and parameters."""
    t = rule.get("type", "unknown")
    if t == "color_mapping":
        m = rule.get("mapping", {})
        if len(m) == 2:
            return "swap_two_colors"
        if len(m) == 1:
            return "remap_one_color"
        return "color_remap"
    if t == "recolor_sequential":
        return "recolor_objects_sequentially"
    if t == "identity":
        return "identity"
    # For custom types added by Claude, use the type name directly
    return t.replace("_", " ").strip()


def _infer_category(rule: dict) -> str:
    """Assign a high-level category based on rule type."""
    t = rule.get("type", "")
    if any(k in t for k in ("color", "recolor", "remap", "palette")):
        return "color_transform"
    if any(k in t for k in ("move", "shift", "translate", "gravity", "relocate", "slide")):
        return "spatial_transform"
    if any(k in t for k in ("scale", "flip", "rotate", "mirror", "reflect")):
        return "geometric_transform"
    if any(k in t for k in ("fill", "border", "enclosed", "flood")):
        return "fill_transform"
    return "other"
