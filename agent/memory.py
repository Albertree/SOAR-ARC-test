"""
memory — SOAR procedural memory (rule storage and retrieval).

Each rule is stored as a JSON file in procedural_memory/:
  procedural_memory/rule_001.json
  procedural_memory/rule_002.json
  ...

Rule schema (flat {condition, action} pair — docs/RULE_FORMAT.md §3):
  {
    "id":          <int>          — unique sequential ID,
    "concept":     "<str>"        — short human-readable name (e.g. "place_object"),
    "category":    "<str>"        — grouping tag for anti-unification,
    "condition":   { "type": ..., "params": {...} }  — LHS: when the rule applies,
    "action":      { "dsl": ...,  "args": {...} }     — RHS: the recipe to replay,
    "covers":      ["<task_id>"]  — all tasks this rule has successfully handled,
    "source_task": "<task_id>"    — task that first triggered discovery of this rule,
    "anti_unification_trace": "<path>|null"  — set iff lifted across sources (§8),
    "created_at":  "<ISO>"        — creation timestamp,
    "times_reused": <int>         — how often the fast-path reused this rule
  }

Note: the rule is a flat {condition, action} dict — there is no wrapping "rule"
sub-key. The fast path reconstructs a PredictOperator-applicable rule from this
shape via `applicable_rule()` (which stamps the dispatch `type` from action.dsl).

Design goal: FEW, GENERAL rules — not many specific ones.
When a new rule is equivalent to an existing one, the existing rule's
"covers" list is extended rather than creating a duplicate file.
"""

import json
import os
from datetime import datetime

from program.anti_unification import NoCommonSkeleton, unify

PROCEDURAL_MEMORY_ROOT = "procedural_memory"

# A param/arg position absent from a rule, distinct from any real value.
_MISSING = object()


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
    When the new rule shares a *skeleton* (same condition.type + action.dsl) with
    concrete sibling rules but differs in a param/arg, `program.anti_unification.
    unify()` lifts them into one `covers>1` abstraction whose differing positions
    are variables (R3, BACKLOG_LOOP.md); the abstraction replaces the siblings.
    Once an abstraction exists, later concrete instances it *subsumes* are folded
    into its `covers` rather than re-lifted, so repeated runs converge instead of
    churning. Keeping the call site here — and only here — ensures it never
    multiplies.
    """
    cond = rule_obj.get("condition")
    act = rule_obj.get("action")
    if not cond or not act:
        raise RuleSchemaError(
            f"save_rule requires condition+action; got keys={sorted(rule_obj)}")

    os.makedirs(procedural_memory_root, exist_ok=True)
    existing = _load_existing_rules(procedural_memory_root)  # [(path, dict)]

    entry = {
        "id": len(existing) + 1,
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

    # (a) Subsumption — an already-lifted abstraction whose variables accept this
    #     concrete instance absorbs it: just grow its covers. This is what makes
    #     repeated runs converge (a concrete instance is never re-lifted once its
    #     abstraction exists), the §2.5-3 "material for R3, not a per-task literal"
    #     contract holding across passes.
    for path, stored in existing:
        if _is_abstract(stored) and _subsumes(stored, entry):
            _merge_covers(stored, entry["covers"], path)
            return path

    # (b) Exact dedup — same condition.type + action ⇒ extend covers in place.
    for path, stored in existing:
        if _condition_action_equiv(stored, rule_obj):
            covers = stored.get("covers") or [stored.get("source_task", "")]
            if task_hex not in covers:
                covers.append(task_hex)
                stored["covers"] = covers
                validate_rule(stored)
                _write_json(path, stored)
            return path

    # (c) Anti-unification (CLAUDE.md §8 — the single call site). Concrete
    #     siblings sharing this rule's skeleton but differing in a param/arg are
    #     lifted into one covers>1 abstraction; it replaces them on disk (R3).
    if related_rules is not None:
        related = [(None, r) for r in related_rules]
    else:
        related = [
            (path, stored) for path, stored in existing
            if not _is_abstract(stored)
            and _same_skeleton(stored, entry)
            and not _condition_action_equiv(stored, rule_obj)
        ]
    if related:
        try:
            au = unify([s for _, s in related] + [entry])
        except NoCommonSkeleton:
            au = None
        if au is not None and au.is_more_general():
            return _persist_abstract(
                au.abstract_rule, related, procedural_memory_root)

    # (d) New source rule.
    path = os.path.join(procedural_memory_root, f"rule_{entry['id']:03d}.json")
    _write_json(path, entry)
    return path


# ---- save_rule internals --------------------------------------------------

def _load_existing_rules(root: str):
    """Return `[(path, rule_dict)]` for every well-formed rule file, sorted by
    filename so id/path selection is deterministic."""
    out = []
    if not os.path.isdir(root):
        return out
    for fname in sorted(os.listdir(root)):
        if not (fname.startswith("rule_") and fname.endswith(".json")):
            continue
        path = os.path.join(root, fname)
        try:
            with open(path, encoding="utf-8") as fh:
                out.append((path, json.load(fh)))
        except (json.JSONDecodeError, IOError):
            continue
    return out


def _write_json(path: str, obj: dict) -> None:
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(obj, fh, indent=2)


def _is_abstract(rule: dict) -> bool:
    """An abstraction is a rule carrying an `anti_unification_trace` (it was
    produced by `unify`, so its params/args may hold `?vN` variables)."""
    return bool(rule.get("anti_unification_trace"))


def _same_skeleton(a: dict, b: dict) -> bool:
    """Two rules share a skeleton iff their condition.type and action.dsl match
    — the unifiability test of docs/ANTI_UNIFICATION.md §2."""
    ca, cb = a.get("condition") or {}, b.get("condition") or {}
    aa, ab = a.get("action") or {}, b.get("action") or {}
    return ca.get("type") == cb.get("type") and aa.get("dsl") == ab.get("dsl")


def _subsumes(abstract: dict, entry: dict) -> bool:
    """True iff `abstract` (a variable-bearing rule) generalizes the concrete
    `entry`: same skeleton, and every abstract param/arg position is either a
    `?` variable (accepts anything) or equals the entry's value."""
    if not _same_skeleton(abstract, entry):
        return False
    a_args = (abstract.get("action") or {}).get("args") or {}
    e_args = (entry.get("action") or {}).get("args") or {}
    a_par = (abstract.get("condition") or {}).get("params") or {}
    e_par = (entry.get("condition") or {}).get("params") or {}
    return _dict_subsumes(a_args, e_args) and _dict_subsumes(a_par, e_par)


def _dict_subsumes(general: dict, specific: dict) -> bool:
    for k in set(general) | set(specific):
        gv = general.get(k, _MISSING)
        if isinstance(gv, str) and gv.startswith("?"):
            continue                      # variable accepts any value (or absence)
        if k == "min_evidence":
            continue                      # generalization is at least as strict
        if gv != specific.get(k, _MISSING):
            return False
    return True


def _merge_covers(stored: dict, new_covers, path: str) -> None:
    covers = stored.get("covers") or [stored.get("source_task", "")]
    changed = False
    for t in new_covers or []:
        if t not in covers:
            covers.append(t)
            changed = True
    if changed:
        stored["covers"] = covers
        validate_rule(stored)
        _write_json(path, stored)


def _persist_abstract(abstract: dict, related, procedural_memory_root: str) -> str:
    """Write the lifted abstraction, reusing the lowest-id related rule's file
    (and id) and deleting the other now-redundant sibling files. When the
    related rules were supplied directly (no on-disk path), write a fresh file."""
    on_disk = [(p, s) for p, s in related if p is not None]
    if on_disk:
        keep_path, keep_rule = min(on_disk, key=lambda ps: ps[1].get("id", 1 << 30))
        abstract["id"] = keep_rule.get("id")
        for p, _ in on_disk:
            if p != keep_path and os.path.exists(p):
                os.remove(p)
        validate_rule(abstract)
        _write_json(keep_path, abstract)
        return keep_path
    existing = _load_existing_rules(procedural_memory_root)
    abstract["id"] = len(existing) + 1
    path = os.path.join(procedural_memory_root, f"rule_{abstract['id']:03d}.json")
    validate_rule(abstract)
    _write_json(path, abstract)
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


# A persisted rule's `action.dsl` names the *recipe* (the discovered transform);
# PredictOperator._apply_rule, however, dispatches on a top-level `type` tag (the
# WM dispatch slot the generalize operator sets at discovery time). The persisted
# {condition, action} schema (docs/RULE_FORMAT.md §3) does not carry that tag, so
# the fast path cannot replay a stored rule without bridging the two. This map is
# that bridge: one entry per *discovered recipe*, value-agnostic — NOT a per-task
# detector (the task-specific cell/colour are re-derived at apply time from the
# task's own grids, never stored). It grows only when a genuinely new recipe is
# discovered, in lockstep with the generalize operator's dispatch tags.
_DSL_TO_DISPATCH = {
    "copy_common_output": "constant_output",
    "place_object": "place_object",
    "recolor_largest": "recolor_largest",
}


def _has_unresolved_var(args: dict) -> bool:
    """True if any action arg is still an anti-unification placeholder (`?v…`)."""
    return any(isinstance(v, str) and v.startswith("?")
               for v in (args or {}).values())


# Recipes whose anti-unification variable the *render path* fills at apply time
# by bounded, example-grounded selection (agent.variable_resolution, §2.5-2b),
# mapped to the arg name(s) it can resolve. A rule whose only unresolved `?vN`
# holes are in this set is no longer "incomplete" for replay — the hole is
# filled from the examples (selection, not invention), so the fast path may
# reuse the lifted abstraction directly. Any *other* unresolved variable (an
# unknown arg, or a recipe not listed here) is still non-replayable and the slow
# path re-derives it. This is the lockstep companion to PLACE_OBJECT_FILLINGS in
# active_operators.py; both grow only when a genuinely new resolvable hole exists.
_RUNTIME_RESOLVABLE = {
    "place_object": {"target_mode"},
}


def _unresolved_vars(args: dict) -> set:
    """Names of the action args still holding a `?v…` placeholder."""
    return {k for k, v in (args or {}).items()
            if isinstance(v, str) and v.startswith("?")}


def _is_runtime_resolvable(entry: dict) -> bool:
    """True iff `entry`'s only unresolved anti-unification holes are ones the
    render path fills by example-grounded selection (`_RUNTIME_RESOLVABLE`). The
    fast path may then reuse the lifted abstraction; resolution happens at render
    time, grounded in the examples, never by storing a per-task literal."""
    action = (entry or {}).get("action") or {}
    resolvable = _RUNTIME_RESOLVABLE.get(action.get("dsl"))
    if not resolvable:
        return False
    unresolved = _unresolved_vars(action.get("args"))
    return bool(unresolved) and unresolved <= resolvable


def applicable_rule(entry: dict):
    """Reconstruct a PredictOperator-applicable prediction-rule from a persisted
    {condition, action} rule, or return None if it cannot be replayed as-is.

    This is the fast path's bridge from the on-disk schema (RULE_FORMAT §3) to the
    in-WM prediction-rule shape PredictOperator._apply_rule consumes. It copies
    the stored entry and stamps the top-level `type` dispatch tag derived from
    `action.dsl` (via `_DSL_TO_DISPATCH`).

    Returns None when either:
      (a) `action.dsl` names an unknown recipe (no dispatch tag) — nothing to
          replay; or
      (b) the action carries an unresolved anti-unification variable (a `?v…`
          placeholder, e.g. rule_002's `target_mode="?v1"`) that the render path
          *cannot* fill. An abstract rule is incomplete until its hole is filled;
          when the hole is in `_RUNTIME_RESOLVABLE` the render path fills it at
          apply time by bounded, example-grounded selection (§2.5-2b), so the
          rule **is** replayable and passes through — the fast path can reuse the
          lifted abstraction. A hole outside that set (an unknown arg, or a recipe
          with no resolver) stays non-replayable: returning None lets the slow
          path re-derive the concrete filling instead of applying a false reuse.
          Inventing a *new* filling for the hole remains the open Q-B3/Q-B4 and is
          not done here — selection over a known set is not invention.
    """
    action = (entry or {}).get("action") or {}
    dispatch = _DSL_TO_DISPATCH.get(action.get("dsl"))
    if dispatch is None:
        return None
    if _has_unresolved_var(action.get("args")) and not _is_runtime_resolvable(entry):
        return None
    rule = dict(entry)
    rule["type"] = dispatch
    return rule


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
