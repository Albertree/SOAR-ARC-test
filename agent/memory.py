"""
memory — SOAR procedural memory (rule storage and retrieval).

Two write paths coexist here:

  * Legacy (``save_rule_to_ltm``): the historical writer used by
    ``agent/active_agent.py``. Emits the pre-test20 schema with a top-level
    ``rule`` payload and no ``condition``/``action`` keys. Retained only so
    the existing call site keeps compiling; any file it produces will fail
    the F4 invariant if it is left on disk at iter-end.

  * Schema-aware (``save_rule``): the canonical writer specified in
    ``docs/RULE_FORMAT.md`` §1. Enforces validation rules V1–V7 from §3
    via ``validate_rule()`` and raises ``RuleSchemaError`` on any
    violation. This is the only path that may persist rules into
    ``procedural_memory/`` going forward; call-site migration happens in a
    later iter.

Design goal: FEW, GENERAL rules — not many specific ones. When a new rule
is equivalent to an existing one, the existing rule's ``covers`` list is
extended rather than creating a duplicate file.
"""

from __future__ import annotations

import json
import os
import re
from datetime import datetime
from typing import Iterable

PROCEDURAL_MEMORY_ROOT = "procedural_memory"

# ======================================================================
# Schema-aware path — see docs/RULE_FORMAT.md
# ======================================================================

_HEX8_RE = re.compile(r"^[0-9a-f]{8}$")
_AU_TRACE_RE = re.compile(r"^episodic_memory/.+/anti_unification/.+\.json$")

# Exactly the keys listed in docs/RULE_FORMAT.md §1 "required".
_REQUIRED_TOP_LEVEL_KEYS = (
    "id",
    "concept",
    "category",
    "condition",
    "action",
    "covers",
    "source_task",
    "anti_unification_trace",
    "created_at",
    "times_reused",
)

_REQUIRED_CONDITION_KEYS = ("type", "params", "min_evidence")
_REQUIRED_ACTION_KEYS = ("dsl", "args")


class RuleSchemaError(ValueError):
    """Raised by ``validate_rule`` / ``save_rule`` when a candidate rule does
    not conform to ``docs/RULE_FORMAT.md`` §1 + §3. Callers must propagate
    or log-then-re-raise; silently swallowing this exception is an F7
    invariant violation (see ``docs/INVARIANTS.md`` §1 F7)."""


def _condition_registry() -> dict:
    """Lazy import to avoid a hard dependency at module load."""
    from agent.conditions import CONDITION_REGISTRY  # local import
    return CONDITION_REGISTRY


def _dsl_registry() -> dict:
    """Return the DSL primitive registry if available, else an empty dict.

    The DSL package (``procedural_memory/DSL/``) is bootstrapped in a later
    iter; until then every ``action.dsl`` value fails V3, which is
    correct-by-construction — no rule may be persisted until at least one
    DSL primitive is registered.
    """
    try:
        from procedural_memory.DSL.apply import DSL_REGISTRY  # type: ignore
    except Exception:
        return {}
    return DSL_REGISTRY


def validate_rule(rule: dict, *,
                  procedural_memory_root: str = PROCEDURAL_MEMORY_ROOT) -> None:
    """Enforce V1–V7 from ``docs/RULE_FORMAT.md`` §3. Raises
    ``RuleSchemaError`` on any failure; returns ``None`` on success."""
    if not isinstance(rule, dict):
        raise RuleSchemaError("schema validation failed: rule is not a JSON object")

    # V1 — required top-level keys present, types correct, no extras.
    missing = [k for k in _REQUIRED_TOP_LEVEL_KEYS if k not in rule]
    if missing:
        raise RuleSchemaError(
            f"schema validation failed: missing required key(s) {missing}"
        )
    # V7 — no unexpected top-level keys.
    extras = [k for k in rule.keys() if k not in _REQUIRED_TOP_LEVEL_KEYS]
    if extras:
        raise RuleSchemaError(f"unexpected key: {extras[0]}")

    if not isinstance(rule["id"], int) or isinstance(rule["id"], bool) or rule["id"] < 1:
        raise RuleSchemaError("schema validation failed: id must be a positive integer")
    if not isinstance(rule["concept"], str) or not rule["concept"]:
        raise RuleSchemaError("schema validation failed: concept must be non-empty string")
    if not isinstance(rule["category"], str) or not rule["category"]:
        raise RuleSchemaError("schema validation failed: category must be non-empty string")

    cond = rule["condition"]
    if not isinstance(cond, dict):
        raise RuleSchemaError("schema validation failed: condition must be an object")
    cond_missing = [k for k in _REQUIRED_CONDITION_KEYS if k not in cond]
    if cond_missing:
        raise RuleSchemaError(
            f"schema validation failed: condition missing {cond_missing}"
        )
    cond_extras = [k for k in cond.keys() if k not in _REQUIRED_CONDITION_KEYS]
    if cond_extras:
        raise RuleSchemaError(f"unexpected key: condition.{cond_extras[0]}")
    if not isinstance(cond["type"], str) or not cond["type"]:
        raise RuleSchemaError("schema validation failed: condition.type must be non-empty string")
    if not isinstance(cond["params"], dict):
        raise RuleSchemaError("schema validation failed: condition.params must be an object")
    if (not isinstance(cond["min_evidence"], int) or isinstance(cond["min_evidence"], bool)
            or cond["min_evidence"] < 1):
        raise RuleSchemaError(
            "schema validation failed: condition.min_evidence must be integer ≥ 1"
        )

    act = rule["action"]
    if not isinstance(act, dict):
        raise RuleSchemaError("schema validation failed: action must be an object")
    act_missing = [k for k in _REQUIRED_ACTION_KEYS if k not in act]
    if act_missing:
        raise RuleSchemaError(
            f"schema validation failed: action missing {act_missing}"
        )
    act_extras = [k for k in act.keys() if k not in _REQUIRED_ACTION_KEYS]
    if act_extras:
        raise RuleSchemaError(f"unexpected key: action.{act_extras[0]}")
    if not isinstance(act["dsl"], str) or not act["dsl"]:
        raise RuleSchemaError("schema validation failed: action.dsl must be non-empty string")
    if not isinstance(act["args"], dict):
        raise RuleSchemaError("schema validation failed: action.args must be an object")

    covers = rule["covers"]
    if not isinstance(covers, list) or not covers:
        raise RuleSchemaError("schema validation failed: covers must be non-empty list")
    if len(set(covers)) != len(covers):
        raise RuleSchemaError("schema validation failed: covers entries must be unique")
    for t in covers:
        if not (isinstance(t, str) and _HEX8_RE.match(t)):
            raise RuleSchemaError(
                f"schema validation failed: covers entry {t!r} not 8-hex-char task id"
            )

    src = rule["source_task"]
    if not (isinstance(src, str) and _HEX8_RE.match(src)):
        raise RuleSchemaError(
            "schema validation failed: source_task must be 8-hex-char task id"
        )

    trace = rule["anti_unification_trace"]
    if trace is not None:
        if not (isinstance(trace, str) and _AU_TRACE_RE.match(trace)):
            raise RuleSchemaError(
                "schema validation failed: anti_unification_trace must be null or "
                "match ^episodic_memory/.+/anti_unification/.+\\.json$"
            )

    if not isinstance(rule["created_at"], str) or not rule["created_at"]:
        raise RuleSchemaError("schema validation failed: created_at must be non-empty string")
    if (not isinstance(rule["times_reused"], int)
            or isinstance(rule["times_reused"], bool)
            or rule["times_reused"] < 0):
        raise RuleSchemaError(
            "schema validation failed: times_reused must be non-negative integer"
        )

    # V2 — condition.type registered.
    cond_registry = _condition_registry()
    if cond["type"] not in cond_registry:
        raise RuleSchemaError(f"unknown condition.type: {cond['type']}")

    # V3 — action.dsl registered. Empty registry until DSL primitives land.
    dsl_registry = _dsl_registry()
    if act["dsl"] not in dsl_registry:
        raise RuleSchemaError(f"unknown action.dsl: {act['dsl']}")

    # V4 — source_task ∈ covers.
    if src not in covers:
        raise RuleSchemaError("source_task must appear in covers")

    # V5 — anti_unification_trace path exists if non-null.
    if trace is not None and not os.path.isfile(trace):
        raise RuleSchemaError(f"trace file not found: {trace}")

    # V6 — id collision check against existing files.
    target_name = f"rule_{int(rule['id']):03d}.json"
    target_path = os.path.join(procedural_memory_root, target_name)
    if os.path.exists(target_path):
        raise RuleSchemaError(f"id collision: {target_name} exists")


def next_rule_id(procedural_memory_root: str = PROCEDURAL_MEMORY_ROOT) -> int:
    """Return the next unused integer id for a new ``rule_NNN.json`` file
    under ``procedural_memory_root``. Returns 1 when the directory is
    missing or contains no rule files.

    Read-only. Intended as the id source for the
    ``translate_to_schema(..., rule_id=next_rule_id(...))`` →
    ``save_rule(...)`` flow in ``agent/active_agent.py``. Picking
    ``max(used) + 1`` (rather than ``len(files) + 1``) keeps ids monotonic
    even after legacy rules have been deleted from disk, satisfying V6 by
    construction.

    Filenames whose ``NNN`` segment does not parse as an integer are
    ignored — the convention enforced by ``save_rule`` is the three-digit
    zero-padded form, but any positive integer width is tolerated here so
    a future migration that emits four-digit ids does not silently collide.
    """
    if not os.path.isdir(procedural_memory_root):
        return 1
    used: set[int] = set()
    for fname in os.listdir(procedural_memory_root):
        if not (fname.startswith("rule_") and fname.endswith(".json")):
            continue
        stem = fname[len("rule_"):-len(".json")]
        try:
            value = int(stem)
        except ValueError:
            continue
        if value >= 1:
            used.add(value)
    return max(used, default=0) + 1


def load_related(category: str, *,
                 procedural_memory_root: str = PROCEDURAL_MEMORY_ROOT) -> list:
    """Return schema-compliant rules in ``procedural_memory_root`` whose
    ``category`` equals the argument. Intended as the read step before
    ``save_rule(rule, related_rules=...)`` per ``CLAUDE.md §8``:

        related = load_related(rule["category"])
        save_rule(rule, related_rules=related)

    Read-only. Files that fail to parse, lack ``{condition, action,
    category}`` keys, or whose category does not match are silently
    skipped — legacy rules (no ``condition``/``action`` block) therefore
    never reach ``unify()`` through this path. Surfacing such files is
    the migration tool's job, not the retrieval helper's.

    ``validate_rule`` is intentionally NOT invoked: it enforces V6 (id
    collision against an existing file on disk), which always fires for
    rules read back from disk. The lightweight shape check below is the
    minimum needed to keep ``unify()`` from crashing on malformed input.
    """
    if not isinstance(category, str) or not category:
        return []
    if not os.path.isdir(procedural_memory_root):
        return []
    out: list = []
    for fname in sorted(os.listdir(procedural_memory_root)):
        if not (fname.startswith("rule_") and fname.endswith(".json")):
            continue
        path = os.path.join(procedural_memory_root, fname)
        try:
            with open(path, encoding="utf-8") as fh:
                rule = json.load(fh)
        except (OSError, json.JSONDecodeError):
            continue
        if not isinstance(rule, dict):
            continue
        if rule.get("category") != category:
            continue
        cond = rule.get("condition")
        act = rule.get("action")
        if not isinstance(cond, dict) or not isinstance(act, dict):
            continue
        if not isinstance(cond.get("type"), str) or not isinstance(act.get("dsl"), str):
            continue
        out.append(rule)
    return out


def translate_to_schema(legacy_rule: dict, task_hex: str, patterns: dict, *,
                        rule_id: int,
                        now: str | None = None) -> dict | None:
    """Lift a legacy pipeline rule into the §1 ``{condition, action}`` shape.

    This is the bridge function between the slow-path output of
    ``GeneralizeOperator`` (legacy shapes like ``{"type": "identity", ...}``
    or ``{"type": "color_mapping", "mapping": {...}, ...}``) and the
    schema-aware ``save_rule()`` writer. The legacy writer
    ``save_rule_to_ltm()`` still embeds the legacy dict under a top-level
    ``rule`` key — files it produces would trip F4 (rule lacking
    ``condition``). ``translate_to_schema`` is the lossless converter that a
    future ``active_agent.py`` migration will call before invoking
    ``save_rule``.

    Pure function: no file I/O, no registry mutation. ``recognized_conditions``
    is read-only by contract.

    Returns
    -------
    dict | None
        A candidate §1-compliant rule (caller must still pass it through
        ``validate_rule`` / ``save_rule``), or ``None`` if no translation
        is currently defined for ``legacy_rule["type"]`` AND the
        recognition-vocabulary precondition.

    Currently translated shapes
    ---------------------------
    * ``{"type": "identity", ...}`` → ``condition.type =
      "identity_transformation"`` (requires the matcher to fire on
      ``patterns`` — gate ensures the rule's stored precondition is
      empirically supported by the source task), ``action.dsl = "coloring"``
      with ``args = {"selection": [], "color": 0}`` (no-op
      composition — ``coloring(grid, [], 0)`` returns an identity copy of
      ``grid``). This is the only legacy shape whose ``action.dsl`` reduces
      to a registered DSL primitive without pair-specific program
      synthesis; ``color_mapping`` and ``recolor_sequential`` require an
      anti-unification-discovered abstraction, deferred to a later iter.

    Non-translatable shapes return ``None`` deliberately — a caller that
    wants to attempt a save must check the return value and fall back to
    the legacy writer (or skip the save).
    """
    if not isinstance(legacy_rule, dict):
        return None
    legacy_type = legacy_rule.get("type")
    if not isinstance(legacy_type, str) or not legacy_type:
        return None
    if not isinstance(task_hex, str) or not _HEX8_RE.match(task_hex):
        return None
    if not isinstance(rule_id, int) or isinstance(rule_id, bool) or rule_id < 1:
        return None
    if not isinstance(patterns, dict):
        patterns = {}

    if legacy_type != "identity":
        return None

    # V2 gate: the recognition matcher must actually fire on the patterns
    # the source task produced. This keeps the translator honest — it cannot
    # mint a condition.type that the live recognizer would reject.
    from agent.conditions import recognized_conditions  # local import
    fired = recognized_conditions(patterns)
    if "identity_transformation" not in fired:
        return None

    pair_analyses = patterns.get("pair_analyses") or []
    min_evidence = max(1, len(pair_analyses) if isinstance(pair_analyses, list) else 1)

    created_at = now if isinstance(now, str) and now else datetime.utcnow().isoformat()

    return {
        "id": rule_id,
        "concept": _infer_concept(legacy_rule),
        "category": _infer_category(legacy_rule),
        "condition": {
            "type": "identity_transformation",
            "params": {},
            "min_evidence": min_evidence,
        },
        "action": {
            "dsl": "coloring",
            "args": {"selection": [], "color": 0},
        },
        "covers": [task_hex],
        "source_task": task_hex,
        "anti_unification_trace": None,
        "created_at": created_at,
        "times_reused": 0,
    }


def save_rule(rule: dict, *,
              related_rules: Iterable[dict] | None = None,
              procedural_memory_root: str = PROCEDURAL_MEMORY_ROOT) -> str:
    """Validate ``rule`` against the §1+§3 schema, then write it to
    ``procedural_memory/rule_<id>.json``. Returns the file path. Raises
    ``RuleSchemaError`` if validation fails — caller must not swallow.

    When ``related_rules`` is a non-empty iterable, ``save_rule`` is the
    sole permitted call site for ``program.anti_unification.unify`` per
    ``CLAUDE.md §8``. It calls ``unify(list(related_rules) + [rule])``;
    if the result ``is_more_general()`` the abstract rule replaces
    ``rule`` and its already-written trace file satisfies V5. If
    ``unify`` raises ``NoCommonSkeleton`` the inputs share no
    ``(condition.type, action.dsl)`` skeleton and ``rule`` is persisted
    unchanged. The non-RuleSchemaError caught here does not engage F7."""
    os.makedirs(procedural_memory_root, exist_ok=True)

    related = list(related_rules) if related_rules else []
    if related:
        # Local import — keeps agent.memory loadable even if the program
        # package is unavailable in some narrow test environments.
        from program.anti_unification import NoCommonSkeleton, unify
        try:
            au_result = unify(related + [rule])
        except NoCommonSkeleton:
            au_result = None
        if au_result is not None and au_result.is_more_general():
            rule = au_result.abstract_rule

    validate_rule(rule, procedural_memory_root=procedural_memory_root)

    target_name = f"rule_{int(rule['id']):03d}.json"
    target_path = os.path.join(procedural_memory_root, target_name)
    with open(target_path, "w", encoding="utf-8") as fh:
        json.dump(rule, fh, indent=2, sort_keys=False)
    return target_path


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
