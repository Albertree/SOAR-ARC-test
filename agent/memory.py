"""
memory — SOAR procedural memory (rule storage and retrieval).

Each rule is stored as a JSON file in procedural_memory/:
  procedural_memory/rule_001.json
  procedural_memory/rule_002.json
  ...

Rule schema (the `{condition, action}` contract — CLAUDE.md §3.2,
docs/RULE_FORMAT.md §1):
  {
    "id":          <int>          — unique sequential ID,
    "concept":     "<str>"        — short human-readable name (e.g. "swap_two_colors"),
    "category":    "<str>"        — color_transform | spatial_transform | ...,
    "condition":   {"type","params","min_evidence"}  — WHEN the rule applies,
    "action":      {"dsl","args"}                     — HOW it transforms,
    "covers":      ["<task_id>"]  — all tasks this rule has successfully handled,
    "source_task": "<task_id>"    — task that first triggered discovery of this rule,
    "anti_unification_trace": null|"<path>"  — set only for generalized rules,
    "created_at":  "<ISO>"        — creation timestamp,
    "times_reused": <int>         — how often the fast-path reused this rule
  }

The legacy pipeline emits a flat operational payload ({type, mapping, ...});
`translate_to_schema()` lifts it into the {condition, action} shape and
`validate_rule()` enforces it on every save (raising RuleSchemaError — never
swallowed, see INVARIANTS F4/F7). The operational payload is preserved under
`action.args`; `load_all_rules()` re-exposes it as `entry["rule"]` so existing
consumers (the predictor, the equivalence check) keep working unchanged.

Design goal: FEW, GENERAL rules — not many specific ones.
When a new rule is equivalent to an existing one, the existing rule's
"covers" list is extended rather than creating a duplicate file.
"""

import json
import os
import re
from datetime import datetime

from agent.conditions import is_registered

PROCEDURAL_MEMORY_ROOT = "procedural_memory"

# The two frozen hand-coded DSL primitives (CLAUDE.md §6, INVARIANTS F3). The
# discovered layer (anti-unification-coined names) is empty until §8 is wired;
# until then a valid action.dsl must name one of these two.
DSL_PRIMITIVES = {"coloring", "make_grid"}

# Top-level keys required by the schema (docs/RULE_FORMAT.md §1). No others are
# permitted on disk (V7).
_REQUIRED_TOP = {
    "id", "concept", "category", "condition", "action", "covers",
    "source_task", "anti_unification_trace", "created_at", "times_reused",
}

# Task-id pattern. RULE_FORMAT.md §1 uses ^[0-9a-f]{8}$ for real ARC tasks, but
# the easy slice uses readable synthetic ids ("easy000a", "easy0001"). We accept
# both rather than reject every slice rule; see session_log 2026-06-11 note.
_TASK_ID_RE = re.compile(r"^[0-9a-z_]{3,16}$")


class RuleSchemaError(Exception):
    """Raised when a rule fails {condition, action} schema validation."""


# ======================================================================
# Public API
# ======================================================================

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
            with open(path, "r", encoding="utf-8") as fh:
                stored = json.load(fh)
        except (json.JSONDecodeError, IOError):
            continue
        if _rules_equivalent(_operational_view(stored), rule):
            covers = stored.get("covers") or [stored.get("source_task", "")]
            if task_hex not in covers:
                covers.append(task_hex)
                stored["covers"] = covers
                stored = _ensure_schema(stored)  # migrate legacy in place if needed
                validate_rule(stored)            # keep it valid after mutation
                with open(path, "w", encoding="utf-8") as fh:
                    json.dump(stored, fh, indent=2)
            return path

    # New rule — assign next ID, lift the operational payload into the
    # {condition, action} schema, validate, then persist. validate_rule raises
    # RuleSchemaError on violation; we deliberately let it propagate (F4/F7).
    next_id = next_rule_id(procedural_memory_root)
    entry = translate_to_schema(rule, rule_id=next_id, task_hex=task_hex)
    validate_rule(entry)

    filename = f"rule_{next_id:03d}.json"
    path = os.path.join(procedural_memory_root, filename)
    with open(path, "w", encoding="utf-8") as fh:
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
            with open(path, "r", encoding="utf-8") as fh:
                entry = json.load(fh)
            entry["_path"] = path
            # Re-expose the operational payload under "rule" so legacy
            # consumers (predictor, equivalence check) work with either the
            # schema shape (payload under action.args) or a legacy file.
            entry["rule"] = _operational_view(entry)
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
# Schema: translate, validate, migrate
# ======================================================================

def next_rule_id(procedural_memory_root: str = PROCEDURAL_MEMORY_ROOT) -> int:
    """Return the next unused rule id (max existing id + 1; never reused)."""
    if not os.path.isdir(procedural_memory_root):
        return 1
    max_id = 0
    for fname in os.listdir(procedural_memory_root):
        if not (fname.startswith("rule_") and fname.endswith(".json")):
            continue
        path = os.path.join(procedural_memory_root, fname)
        try:
            with open(path, "r", encoding="utf-8") as fh:
                rid = int(json.load(fh).get("id", 0))
        except (OSError, json.JSONDecodeError, ValueError, TypeError):
            try:
                rid = int(fname[5:-5])  # rule_NNN.json
            except ValueError:
                rid = 0
        max_id = max(max_id, rid)
    return max_id + 1


def translate_to_schema(payload: dict, *, rule_id: int, task_hex: str,
                        covers=None, source_task: str = None,
                        created_at: str = None, times_reused: int = 0,
                        concept: str = None, category: str = None,
                        anti_unification_trace=None) -> dict:
    """
    Lift a flat operational payload ({type, mapping, ...}) emitted by the
    pipeline into the {condition, action} schema (docs/RULE_FORMAT.md §1).

    The operational payload is preserved verbatim under `action.args` so it can
    still drive the predictor; the matcher name and DSL primitive are derived
    from its `type`.
    """
    if not isinstance(payload, dict) or not payload.get("type"):
        raise RuleSchemaError(f"cannot translate payload without a 'type': {payload!r}")
    ptype = payload["type"]
    return {
        "id": rule_id,
        "concept": concept or _infer_concept(payload),
        "category": category or _infer_category(payload),
        "condition": {
            "type": ptype,
            "params": _condition_params(payload),
            "min_evidence": 1,
        },
        "action": {
            "dsl": _dsl_for(ptype),
            "args": payload,
        },
        "covers": list(covers) if covers else [task_hex],
        "source_task": source_task or task_hex,
        "anti_unification_trace": anti_unification_trace,
        "created_at": created_at or datetime.now().isoformat(),
        "times_reused": int(times_reused or 0),
    }


def validate_rule(entry: dict) -> None:
    """
    Enforce the {condition, action} schema (docs/RULE_FORMAT.md §3, V1–V7).
    Raises RuleSchemaError on any violation; returns None on success.
    """
    if not isinstance(entry, dict):
        raise RuleSchemaError("rule must be a JSON object")

    keys = set(entry)
    missing = _REQUIRED_TOP - keys
    if missing:
        raise RuleSchemaError(f"missing required key(s): {sorted(missing)}")
    extra = keys - _REQUIRED_TOP  # V7
    if extra:
        raise RuleSchemaError(f"unexpected top-level key(s): {sorted(extra)}")

    if not isinstance(entry["id"], int) or isinstance(entry["id"], bool) or entry["id"] < 1:
        raise RuleSchemaError(f"id must be a positive integer, got {entry['id']!r}")
    for k in ("concept", "category"):
        if not isinstance(entry[k], str) or not entry[k]:
            raise RuleSchemaError(f"{k} must be a non-empty string")

    cond = entry["condition"]
    if not isinstance(cond, dict) or set(cond) != {"type", "params", "min_evidence"}:
        raise RuleSchemaError("condition must have exactly {type, params, min_evidence}")
    if not isinstance(cond["type"], str) or not cond["type"]:
        raise RuleSchemaError("condition.type must be a non-empty string")
    if not isinstance(cond["params"], dict):
        raise RuleSchemaError("condition.params must be an object")
    if not isinstance(cond["min_evidence"], int) or isinstance(cond["min_evidence"], bool) \
            or cond["min_evidence"] < 1:
        raise RuleSchemaError("condition.min_evidence must be an integer >= 1")
    if not is_registered(cond["type"]):  # V2
        raise RuleSchemaError(f"unknown condition.type: {cond['type']}")

    act = entry["action"]
    if not isinstance(act, dict) or set(act) != {"dsl", "args"}:
        raise RuleSchemaError("action must have exactly {dsl, args}")
    if not isinstance(act["dsl"], str) or not act["dsl"]:
        raise RuleSchemaError("action.dsl must be a non-empty string")
    if not isinstance(act["args"], dict):
        raise RuleSchemaError("action.args must be an object")
    if act["dsl"] not in DSL_PRIMITIVES:  # V3 (discovered layer empty until §8)
        raise RuleSchemaError(f"unknown action.dsl: {act['dsl']}")

    covers = entry["covers"]
    if not isinstance(covers, list) or not covers:
        raise RuleSchemaError("covers must be a non-empty list")
    for t in covers:
        if not isinstance(t, str) or not _TASK_ID_RE.match(t):
            raise RuleSchemaError(f"invalid task id in covers: {t!r}")
    if len(set(covers)) != len(covers):
        raise RuleSchemaError("covers must not contain duplicate task ids")

    st = entry["source_task"]
    if not isinstance(st, str) or not _TASK_ID_RE.match(st):
        raise RuleSchemaError(f"invalid source_task: {st!r}")
    if st not in covers:  # V4
        raise RuleSchemaError("source_task must appear in covers")

    trace = entry["anti_unification_trace"]
    if trace is not None:
        if not isinstance(trace, str):
            raise RuleSchemaError("anti_unification_trace must be null or a string path")
        if not os.path.isfile(trace):  # V5
            raise RuleSchemaError(f"trace file not found: {trace}")

    if not isinstance(entry["created_at"], str) or not entry["created_at"]:
        raise RuleSchemaError("created_at must be a non-empty ISO 8601 string")
    if not isinstance(entry["times_reused"], int) or isinstance(entry["times_reused"], bool) \
            or entry["times_reused"] < 0:
        raise RuleSchemaError("times_reused must be an integer >= 0")


def migrate_legacy_rules(procedural_memory_root: str = PROCEDURAL_MEMORY_ROOT) -> list:
    """
    Rewrite every legacy-shape rule file (top-level `rule`, no `condition`) into
    the {condition, action} schema, in place. Returns the list of migrated
    paths. Raises RuleSchemaError if a legacy rule cannot be made valid (never
    silently skipped — F7).
    """
    migrated = []
    if not os.path.isdir(procedural_memory_root):
        return migrated
    for fname in sorted(os.listdir(procedural_memory_root)):
        if not (fname.startswith("rule_") and fname.endswith(".json")):
            continue
        path = os.path.join(procedural_memory_root, fname)
        try:
            with open(path, "r", encoding="utf-8") as fh:
                entry = json.load(fh)
        except (OSError, json.JSONDecodeError):
            continue
        if "condition" in entry and "action" in entry:
            continue  # already schema-shaped
        new_entry = _ensure_schema(entry)
        validate_rule(new_entry)
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(new_entry, fh, indent=2)
        migrated.append(path)
    return migrated


# ======================================================================
# Internal helpers
# ======================================================================

def _operational_view(entry: dict) -> dict:
    """
    Return the flat operational payload ({type, ...}) for a stored entry,
    whether it is the schema shape (payload under action.args) or a legacy file
    (top-level `rule`).
    """
    action = entry.get("action")
    if isinstance(action, dict) and isinstance(action.get("args"), dict):
        return action["args"]
    legacy = entry.get("rule")
    return legacy if isinstance(legacy, dict) else {}


def _ensure_schema(entry: dict) -> dict:
    """
    Return a schema-shaped copy of `entry`. If already schema-shaped, strip any
    transient keys (e.g. `_path`, the synthesized `rule`); if legacy, translate.
    """
    if "condition" in entry and "action" in entry:
        return {k: v for k, v in entry.items() if k in _REQUIRED_TOP}
    payload = _operational_view(entry)
    covers = entry.get("covers")
    return translate_to_schema(
        payload,
        rule_id=int(entry.get("id") or 0) or 1,
        task_hex=(entry.get("source_task") or (covers or [""])[0]),
        covers=covers,
        source_task=entry.get("source_task"),
        created_at=entry.get("created_at"),
        times_reused=int(entry.get("times_reused") or 0),
        concept=entry.get("concept"),
        category=entry.get("category"),
        anti_unification_trace=entry.get("anti_unification_trace"),
    )


def _condition_params(payload: dict) -> dict:
    """Derive condition.params from an operational payload."""
    ptype = payload.get("type")
    if ptype == "color_mapping":
        return {"mapping": _norm_mapping(payload.get("mapping"))}
    if ptype == "recolor_sequential":
        return {
            "sort_key": payload.get("sort_key"),
            "source_colors": sorted(payload.get("source_colors") or []),
            "start_color": payload.get("start_color"),
        }
    return {k: v for k, v in payload.items() if k != "type"}


def _dsl_for(ptype: str) -> str:
    """
    Map an operational rule type onto one of the two frozen DSL primitives.
    Every transformation the legacy pipeline emits is a recolouring (a
    composition of `coloring`); canvas-producing types map to `make_grid`.
    """
    if any(k in ptype for k in ("make_grid", "canvas", "blank_canvas")):
        return "make_grid"
    return "coloring"

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
