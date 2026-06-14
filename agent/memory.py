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

    # Canonical {condition, action} surfacing (CLAUDE.md §3.2, docs/RULE_FORMAT.md,
    # INVARIANTS F4). When the discovered rule carries a condition/action pair,
    # persist them at the top level so the saved file is a valid {condition,
    # action} manual — looked up by the fast path, not dead memory. Rules that
    # still lack a condition (legacy color_mapping etc.) are left as-is; they are
    # the un-lifted material that R3 anti-unification is meant to retire.
    if isinstance(rule, dict) and "condition" in rule and "action" in rule:
        entry["condition"] = rule["condition"]
        entry["action"] = rule["action"]

    filename = f"rule_{next_id:03d}.json"
    path = os.path.join(procedural_memory_root, filename)
    with open(path, "w") as fh:
        json.dump(entry, fh, indent=2)

    return path


def save_rule(rule: dict, task_hex: str,
              procedural_memory_root: str = PROCEDURAL_MEMORY_ROOT,
              episodic_memory_root: str = "episodic_memory") -> str:
    """Sanctioned save + anti-unification entry point (``CLAUDE.md §8``).

    This is the **only** function permitted to call
    ``program.anti_unification.unify()``.

    A *canonical* rule carries a ``{condition, action}`` skeleton — the pair
    ``(condition.type, action.dsl)``. When a newly-learned canonical rule shares
    its skeleton with an already-stored rule, the two are folded into that single
    rule instead of accreting a second file:

    * **identical argument expressions** → a plain ``covers`` merge (same rule,
      another task);
    * **divergent argument expressions** (e.g. a move family whose ``target`` is
      a corner in one task and a constant in another) → :func:`unify` lifts the
      divergent position to a ``?v`` variable, writes a forensic
      ``anti_unification_trace``, and the stored rule is rewritten as the one
      more-general rule with ``covers`` unioned.

    This is the mechanism by which task-specific programs converge to
    ``covers > 1`` abstractions (P1·P2·P3 rising together — ``BACKLOG_LOOP.md
    §2.5-3/4``) rather than one detector per variant (the 168-rule failure).

    Legacy rules without a canonical skeleton (e.g. ``color_mapping``) fall back
    to :func:`save_rule_to_ltm`'s exact-equivalence covers-merge unchanged.

    Returns the file path of the saved (or updated) rule.
    """
    skeleton = _rule_skeleton(rule)
    if skeleton is None:
        return save_rule_to_ltm(rule, task_hex, procedural_memory_root)

    os.makedirs(procedural_memory_root, exist_ok=True)
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
        if _rule_skeleton(stored) != skeleton:
            continue
        return _absorb_or_lift(
            path, stored, rule, task_hex, episodic_memory_root
        )

    # No same-skeleton rule yet — store as a fresh canonical rule.
    return save_rule_to_ltm(rule, task_hex, procedural_memory_root)


def _absorb_or_lift(path: str, stored: dict, rule: dict, task_hex: str,
                    episodic_memory_root: str) -> str:
    """Fold `rule` (a new same-skeleton rule for `task_hex`) into the `stored`
    entry at `path` — by covers-merge or by anti-unification — and persist."""
    covers = stored.get("covers", [stored.get("source_task", "")])

    # Already-generalised: the divergent positions are ``?v`` variables, so a new
    # same-skeleton task is simply absorbed into covers. No re-lift, no new trace
    # — keeps the operation idempotent across re-runs (one trace per family).
    if stored.get("anti_unification_trace"):
        if task_hex and task_hex not in covers:
            covers.append(task_hex)
            stored["covers"] = covers
            _write_json(path, stored)
        return path

    stored_view = _entry_to_view(stored)
    new_view = _rule_to_view(rule, task_hex)

    same_params = (
        stored_view["condition"].get("params", {})
        == new_view["condition"].get("params", {})
    )
    same_args = (
        stored_view["action"].get("args", {})
        == new_view["action"].get("args", {})
    )
    if same_params and same_args:
        # Concrete rule, identical argument expressions → plain covers merge.
        if task_hex and task_hex not in covers:
            covers.append(task_hex)
            stored["covers"] = covers
            _write_json(path, stored)
        return path

    # Genuine divergence → anti-unify the two concrete rules into one whose
    # divergent argument positions become ``?v`` variables (R3). unify() is the
    # single sanctioned generalization mechanism (CLAUDE.md §8); it writes the
    # forensic trace and returns the union of covers.
    from program.anti_unification import unify

    res = unify([stored_view, new_view],
                episodic_memory_root=episodic_memory_root)
    abstract = res.abstract_rule
    stored["condition"] = abstract["condition"]
    stored["action"] = abstract["action"]
    stored["covers"] = abstract["covers"]
    stored["anti_unification_trace"] = abstract.get("anti_unification_trace")
    inner = stored.get("rule")
    if isinstance(inner, dict):
        inner["condition"] = abstract["condition"]
        inner["action"] = abstract["action"]
    _write_json(path, stored)
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


def record_cover(entry: dict, task_hex: str) -> None:
    """Record that a stored rule successfully handled `task_hex` (fast-path
    reuse). `covers` means "all tasks this rule has handled" (see module
    docstring); a reused rule that solves a *new* task must extend its covers,
    or the coverage signal (P1/P2) silently undercounts genuine generalization.
    This is the reuse-side analogue of save_rule_to_ltm's slow-path covers merge.
    """
    path = entry.get("_path")
    if not path or not os.path.exists(path):
        return
    try:
        with open(path, "r") as fh:
            data = json.load(fh)
        covers = data.get("covers", [data.get("source_task", "")])
        if task_hex and task_hex not in covers:
            covers.append(task_hex)
            data["covers"] = covers
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

def _write_json(path: str, data: dict) -> None:
    """Persist `data` as indented JSON to `path`."""
    with open(path, "w") as fh:
        json.dump(data, fh, indent=2)


def _rule_skeleton(rule_or_entry: dict):
    """Return the canonical skeleton ``(condition.type, action.dsl)`` for a
    ``{condition, action}`` rule/entry, or ``None`` if it lacks one (legacy
    rules such as ``color_mapping`` that carry no top-level condition/action)."""
    if not isinstance(rule_or_entry, dict):
        return None
    cond = rule_or_entry.get("condition")
    act = rule_or_entry.get("action")
    if isinstance(cond, dict) and isinstance(act, dict):
        ctype = cond.get("type")
        dsl = act.get("dsl")
        if ctype is not None and dsl is not None:
            return (ctype, dsl)
    return None


def _entry_to_view(entry: dict) -> dict:
    """Project a stored entry onto the dict shape :func:`unify` consumes."""
    return {
        "id": entry.get("id"),
        "concept": entry.get("concept", ""),
        "category": entry.get("category", ""),
        "condition": entry.get("condition") or {},
        "action": entry.get("action") or {},
        "covers": entry.get("covers", [entry.get("source_task", "")]),
        "source_task": entry.get("source_task", ""),
    }


def _rule_to_view(rule: dict, task_hex: str) -> dict:
    """Project a freshly-learned rule (for `task_hex`) onto the unify() shape."""
    return {
        "id": None,
        "concept": _infer_concept(rule),
        "category": _infer_category(rule),
        "condition": rule.get("condition") or {},
        "action": rule.get("action") or {},
        "covers": [task_hex],
        "source_task": task_hex,
    }


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
