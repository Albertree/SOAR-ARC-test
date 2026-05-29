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
    """Raised when a rule entry violates the {condition, action} contract.

    ARBOR's in-process guard against the *dead-memory* failure mode — a rule
    the fast path cannot look up because it lacks a well-formed, resolvable
    ``condition``/``action`` pair (CLAUDE.md §3.2; docs/RULE_FORMAT.md §3). It
    is the same boundary ``docs/INVARIANTS.md §1 F4`` enforces post-hoc by
    auto-revert, asserted here *before* the file is written so an invalid rule
    never reaches disk. Per ``INVARIANTS.md §1 F7`` this must never be silently
    swallowed: callers either let it propagate or log-and-re-raise.
    """


def validate_rule(entry: dict) -> None:
    """Validate a procedural-memory rule entry, raising on the first violation.

    Enforces CLAUDE.md §3.2's hard requirements (1-2) plus docs/RULE_FORMAT.md
    V4 — exactly the checks that keep a rule *retrievable* by the fast path:

      1. ``condition`` and ``action`` are both present, non-empty dicts, and
         carry a non-empty string ``condition.type`` / ``action.dsl``.
      2. ``condition.type`` resolves in the condition-matcher registry and
         ``action.dsl`` resolves in the DSL-primitive registry. An unresolvable
         name is dead memory (it can never fire), so it is rejected here.
      3. ``source_task`` (when present) appears in ``covers``.

    Registries are imported lazily so importing :mod:`agent.memory` never
    triggers a circular import. Deterministic and side-effect-free.
    """
    if not isinstance(entry, dict):
        raise RuleSchemaError(
            f"rule entry must be a dict, got {type(entry).__name__}"
        )

    # (1) {condition, action} pair present, non-empty, well-typed
    cond = entry.get("condition")
    if not isinstance(cond, dict) or not cond:
        raise RuleSchemaError("rule missing non-empty 'condition' (CLAUDE.md §3.2)")
    act = entry.get("action")
    if not isinstance(act, dict) or not act:
        raise RuleSchemaError("rule missing non-empty 'action' (CLAUDE.md §3.2)")

    ctype = cond.get("type")
    if not isinstance(ctype, str) or not ctype:
        raise RuleSchemaError("condition.type must be a non-empty string")
    dsl = act.get("dsl")
    if not isinstance(dsl, str) or not dsl:
        raise RuleSchemaError("action.dsl must be a non-empty string")

    # (2) referenced names must resolve in their registries, else dead memory
    from agent.conditions import get as _get_matcher
    if _get_matcher(ctype) is None:
        raise RuleSchemaError(f"unknown condition.type: {ctype!r}")
    from procedural_memory.DSL.apply import DSL_REGISTRY
    if dsl not in DSL_REGISTRY:
        raise RuleSchemaError(f"unknown action.dsl: {dsl!r}")

    # (3) source_task must appear in covers (RULE_FORMAT V4)
    covers = entry.get("covers")
    if not isinstance(covers, list) or not covers:
        raise RuleSchemaError("rule 'covers' must be a non-empty list")
    source = entry.get("source_task")
    if source is not None and source not in covers:
        raise RuleSchemaError("source_task must appear in covers")


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
                changed = False
                if task_hex not in covers:
                    covers.append(task_hex)
                    stored["covers"] = covers
                    changed = True
                # Backfill the {condition, action} pair for legacy rules that
                # predate the schema (CLAUDE.md §3.2). A bare transformation
                # payload without these keys is dead memory the fast path
                # cannot look up.
                if "condition" not in stored:
                    stored["condition"] = _build_condition(stored.get("rule", {}))
                    changed = True
                if "action" not in stored:
                    stored["action"] = _build_action(stored.get("rule", {}))
                    changed = True
                if "anti_unification_trace" not in stored:
                    stored["anti_unification_trace"] = None
                    changed = True
                if changed:
                    # Re-validate the *mutated* entry before it touches disk:
                    # the reuse/backfill write path must honour the same
                    # dead-memory guard as the new-rule path (CLAUDE.md §3.2,
                    # INVARIANTS §1 F4). Extending a stored rule whose
                    # {condition, action} pair does not resolve would just grow
                    # dead memory. RuleSchemaError is a ValueError (not a
                    # json/IO error), so the surrounding except does not catch
                    # it — it propagates, never swallowed (INVARIANTS §1 F7),
                    # and disk is untouched because the write follows.
                    validate_rule(stored)
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
        "condition": _build_condition(rule),
        "action": _build_action(rule),
        "rule": rule,
        "covers": [task_hex],
        "source_task": task_hex,
        "anti_unification_trace": None,
        "created_at": datetime.now().isoformat(),
        "times_reused": 0,
    }

    # Guard the dead-memory failure mode (CLAUDE.md §3.2, INVARIANTS §1 F4)
    # *before* the file touches disk: an entry without a resolvable
    # {condition, action} pair never gets written. RuleSchemaError propagates
    # (never swallowed — INVARIANTS §1 F7).
    validate_rule(entry)

    filename = f"rule_{next_id:03d}.json"
    path = os.path.join(procedural_memory_root, filename)
    with open(path, "w") as fh:
        json.dump(entry, fh, indent=2)

    return path


# Canonical alias: CLAUDE.md §3.2 and docs/RULE_FORMAT.md refer to the save
# entry point as ``save_rule()``. The implementation is ``save_rule_to_ltm``;
# this alias keeps the documented name resolvable without duplicating logic.
save_rule = save_rule_to_ltm


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

# A stored rule is a {condition, action} pair — a manual describing *when*
# and *how* to apply a transformation (CLAUDE.md §3.2, docs/RULE_FORMAT.md).
# The pipeline's internal rule payload only carries the "how"; these helpers
# derive the matching condition/action envelope so every saved rule is a
# valid pair the fast path can look up (and so it passes invariant F4).

# Internal rule "type" -> the documented condition.type that recognises it
# (docs/RULE_FORMAT.md §4 condition-type registry).
_CONDITION_TYPE_BY_RULE = {
    "color_mapping": "consistent_color_mapping",
    "recolor_sequential": "sequential_recoloring",
    "identity": "identity_transformation",
    # Slice-1 value-agnostic copy-common-output: the condition.type names the
    # *complete* firing mechanism (CLAUDE.md §3.2 — condition describes *when*):
    # PAIR test_output_missing ∧ GRID all_outputs_comm, composed by the single
    # ``copy_common_output_applies`` matcher. Recording only the GRID half here
    # would under-specify when the action applies and force the fast path to
    # re-supply the PAIR precondition (the non-uniformity iter 44 removed).
    "copy_common_output": "copy_common_output_applies",
}


def _build_condition(rule: dict) -> dict:
    """Derive the {type, params, min_evidence} condition for a rule payload."""
    rtype = (rule or {}).get("type", "unknown")
    ctype = _CONDITION_TYPE_BY_RULE.get(rtype, f"{rtype}_pattern")
    return {"type": ctype, "params": {}, "min_evidence": 1}


def _build_action(rule: dict) -> dict:
    """Derive the {dsl, args} action for a rule payload.

    Every transformation is a composition of the two frozen primitives
    (`coloring` / `make_grid`, CLAUDE.md §6.1), so a cell-recolouring rule's
    action.dsl is `coloring`; the rule's own parameters become the args.
    """
    rule = rule or {}
    if rule.get("type") == "copy_common_output":
        # The output is a freshly *constructed* canvas equal to the common
        # example output (a make_grid composition), not an in-place recolour.
        # Args stay empty: the grid is read from the task's example outputs at
        # apply time, keeping the rule value-agnostic (no stored literal).
        return {"dsl": "make_grid", "args": {}}
    args = {k: v for k, v in rule.items() if k not in ("type", "confidence")}
    return {"dsl": "coloring", "args": args}


def reconstruct_via_dsl(grid):
    """Materialise a concrete grid as a composition of the two frozen DSL
    primitives — ``make_grid`` then ``coloring`` — returning the rebuilt grid.

    This is how a ``copy_common_output`` action is *executed*: rather than
    copying the target grid wholesale, ARBOR constructs it bottom-up from the
    only two primitives it may ever ship with (CLAUDE.md §6.1) — a fresh canvas
    (``make_grid``) repainted one colour-class at a time (``coloring``). The
    decomposition is value-agnostic and deterministic: the modal colour (ties
    broken by smaller colour value) becomes the canvas fill — minimising the
    number of ``coloring`` calls — and every other colour's cells are painted in
    ascending colour order. The result is bit-identical to ``grid``.

    Raises ``ValueError`` if ``grid`` is not a non-empty rectangular
    list-of-lists; out-of-palette cell values propagate the primitives' own
    ``ValueError`` (not swallowed). The caller is expected to pass a well-formed
    ARC grid.
    """
    # Lazy import: keeps memory.py free of a load-time dependency on the DSL
    # package and avoids any import-order coupling.
    from procedural_memory.DSL.apply import apply_DSL

    if not isinstance(grid, list) or not grid or not all(isinstance(r, list) for r in grid):
        raise ValueError("reconstruct_via_dsl: grid must be a non-empty list of lists")
    height = len(grid)
    width = len(grid[0])
    if width == 0 or any(len(r) != width for r in grid):
        raise ValueError("reconstruct_via_dsl: grid must be rectangular and non-empty")

    # Colour histogram -> modal colour becomes the canvas fill (fewest paints).
    counts = {}
    for row in grid:
        for v in row:
            counts[v] = counts.get(v, 0) + 1
    # Most frequent colour; ties broken deterministically by smaller value.
    background = min(counts, key=lambda c: (-counts[c], c))

    canvas = apply_DSL("make_grid", height=height, width=width, color=background)

    for color in sorted(c for c in counts if c != background):
        selection = [
            (r, c)
            for r in range(height)
            for c in range(width)
            if grid[r][c] == color
        ]
        canvas = apply_DSL("coloring", grid=canvas, selection=selection, color=color)
    return canvas


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
    if t == "copy_common_output":
        return "copy_common_example_output"
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
