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

PROCEDURAL_MEMORY_ROOT = "procedural_memory"


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
        if _canonical_equivalent(stored, rule):
            covers = stored.get("covers", [])
            if task_hex not in covers:
                covers.append(task_hex)
                stored["covers"] = covers
                validate_rule(stored)
                with open(path, "w") as fh:
                    json.dump(stored, fh, indent=2)
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
