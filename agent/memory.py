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


class RuleSchemaError(ValueError):
    """Raised when a rule fails the {condition, action} schema.

    A valid rule is a `{condition, action}` pair (CLAUDE.md §3.2,
    docs/RULE_FORMAT.md). A rule lacking either half is dead memory — it can
    never be looked up by the fast path — and is the 168-rule failure mode
    (INVARIANTS F4). `save_rule` raises this *before* writing; callers must let
    it propagate, never swallow it (INVARIANTS F7).
    """


# ======================================================================
# Public API
# ======================================================================


def validate_rule(entry: dict) -> None:
    """Raise `RuleSchemaError` unless `entry` carries a non-empty `condition`
    (with a `type`) and `action` (with a `dsl`). The minimal structural contract
    the F4 checker enforces on every persisted rule; kept deliberately small so
    it binds the *format*, not matcher/primitive-specific param shapes."""
    if not isinstance(entry, dict):
        raise RuleSchemaError("rule is not a dict")
    cond = entry.get("condition")
    act = entry.get("action")
    if not cond:
        raise RuleSchemaError("rule missing required 'condition'")
    if not act:
        raise RuleSchemaError("rule missing required 'action'")
    if not isinstance(cond, dict) or not cond.get("type"):
        raise RuleSchemaError("condition.type missing or empty")
    if not isinstance(act, dict) or not act.get("dsl"):
        raise RuleSchemaError("action.dsl missing or empty")


def save_rule(rule_obj: dict, task_hex: str, related_rules=None,
              procedural_memory_root: str = PROCEDURAL_MEMORY_ROOT) -> str:
    """Persist a `{condition, action}` rule — the validated successor to
    `save_rule_to_ltm` and the **only** function that writes the new schema.

    Behaviour:
      * Validates the entry (`validate_rule`) before any write; an invalid rule
        raises `RuleSchemaError` rather than landing as dead memory (F4/F7).
      * Deduplicates: when an existing rule has the *same* condition.type and
        action (dsl + args), this task is appended to its `covers` list instead
        of creating a new file. This is what lets one value-agnostic rule absorb
        a whole family (P1/P2 rise) rather than spawning one rule per task.

    It is also the designated single anti-unification call site (CLAUDE.md §8).
    The hook is marked below; AU lift across *different* skeletons is wired in
    R3 (BACKLOG_LOOP.md). Keeping the call site here — and only here — ensures it
    never multiplies.
    """
    cond = rule_obj.get("condition")
    act = rule_obj.get("action")
    if not cond or not act:
        raise RuleSchemaError(
            f"save_rule requires condition+action; got keys={sorted(rule_obj)}")

    os.makedirs(procedural_memory_root, exist_ok=True)
    existing = sorted(
        f for f in os.listdir(procedural_memory_root)
        if f.startswith("rule_") and f.endswith(".json")
    )

    # Dedup — extend covers of an equivalent rule instead of duplicating.
    for fname in existing:
        path = os.path.join(procedural_memory_root, fname)
        try:
            with open(path, encoding="utf-8") as fh:
                stored = json.load(fh)
        except (json.JSONDecodeError, IOError):
            continue
        if _condition_action_equiv(stored, rule_obj):
            covers = stored.get("covers") or [stored.get("source_task", "")]
            if task_hex not in covers:
                covers.append(task_hex)
                stored["covers"] = covers
                validate_rule(stored)
                with open(path, "w", encoding="utf-8") as fh:
                    json.dump(stored, fh, indent=2)
            return path

    # --- anti-unification hook (CLAUDE.md §8 — single call site) -------------
    # R3 wires program.anti_unification here to lift `related_rules + [rule_obj]`
    # sharing a skeleton into one covers>1 abstraction. Inert until R3: the
    # constant-output family already converges to one rule via the dedup above,
    # so there is no liftable cross-skeleton pair yet.
    _ = related_rules  # reserved for the R3 AU call

    next_id = len(existing) + 1
    entry = {
        "id": next_id,
        "concept": rule_obj.get("concept") or cond.get("type"),
        "category": rule_obj.get("category") or "other",
        "condition": cond,
        "action": act,
        "covers": [task_hex],
        "source_task": task_hex,
        "anti_unification_trace": None,
        "created_at": datetime.now().isoformat(),
        "times_reused": 0,
    }
    validate_rule(entry)
    path = os.path.join(procedural_memory_root, f"rule_{next_id:03d}.json")
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(entry, fh, indent=2)
    return path


def _condition_action_equiv(stored: dict, rule_obj: dict) -> bool:
    """True when two rules apply the same way: same condition.type and the same
    action (dsl + normalised args). Used by `save_rule` for covers-dedup."""
    cs = stored.get("condition") or {}
    cr = rule_obj.get("condition") or {}
    as_ = stored.get("action") or {}
    ar = rule_obj.get("action") or {}
    return (
        cs.get("type") == cr.get("type")
        and as_.get("dsl") == ar.get("dsl")
        and _norm_dict(as_.get("args") or {}) == _norm_dict(ar.get("args") or {})
    )

def save_rule_to_ltm(rule: dict, task_hex: str,
                     procedural_memory_root: str = PROCEDURAL_MEMORY_ROOT) -> str:
    """
    Save a learned rule to procedural_memory.

    If an equivalent rule already exists, extend its "covers" list and return
    its path — no duplicate file is created.

    Returns the file path of the saved (or updated) rule.
    """
    os.makedirs(procedural_memory_root, exist_ok=True)

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
    next_id = len(existing) + 1
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
