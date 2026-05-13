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


_VALID_DSL_COLORS = frozenset(range(10)) | {13}


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
    * ``{"type": "identity", ...}`` + ``identity_transformation`` fires →
      ``condition.type = "identity_transformation"``,
      ``action.dsl = "coloring"`` with ``args = {"selection": [], "color":
      0}`` (no-op composition — ``coloring(grid, [], 0)`` returns an
      identity copy of ``grid``). The matcher gate ensures the rule's
      stored precondition is empirically supported by the source task.

    * ``{"type": "identity", ...}`` + ``grid_size_changed`` +
      ``output_dimensions_constant`` + ``output_color_uniform`` all fire
      (iter 21) → ``condition.type = "output_dimensions_constant"``,
      ``action.dsl = "make_grid"`` with ``args = {"height": H, "width": W,
      "color": K}``. H and W come from any pair's ``output_height`` /
      ``output_width`` (the iter-20 matcher guarantees they are constant
      across pairs); K comes from any change group's ``output_colors[0]``
      (the iter-18 matcher guarantees it is constant across all groups in
      all pairs). The slow path's hand-coded matchers never recognise the
      ``make_grid``-style task — they fall through to the identity
      fallback — so the upgrade from "identity stored" to "make_grid
      stored" is purely a function of the recognition vocabulary catching
      up to the data, with no new ``_try_*`` strategy and no new DSL
      primitive (F2 / F3 inert). The chosen ``condition.type``
      (``output_dimensions_constant``) is the strictest of the three
      gating matchers and the one that directly pins ``action.args``'s H,
      W; iter 17's docstring named ``grid_size_changed`` as the eventual
      gate for ``make_grid`` rules, but ``output_dimensions_constant`` is a
      strict refinement (it implies dimension constancy across pairs, the
      property the saved (H, W) constants depend on), so it is the more
      informative label for this specific rule shape. The iter-18 +
      iter-20 conjunction is the recognition-side dual of iter-18's
      ``output_color_uniform`` naming "K is determinable" — together they
      pin all three constants in ``args`` to named preconditions, closing
      the iter-16 polymorphic-args obstacle for ``make_grid``'s argument
      list.

    * ``{"type": "identity", ...}`` + ``single_cell_change_per_pair`` +
      ``output_color_uniform`` + ``input_dimensions_constant`` +
      ``grid_size_preserved`` all fire (iter 25) →
      ``condition.type = "single_cell_change_per_pair"``,
      ``action.dsl = "coloring"`` with
      ``args = {"selection": [[r, c]], "color": K}``. The (r, c) coord
      is the first pair's single group's ``(top_row, top_col)`` — for a
      single-cell group the bounding box collapses to 1×1, so those two
      fields ARE the cell's literal coord. K comes from any change
      group's ``output_colors[0]`` (iter-18 pins it constant across all
      groups in all pairs). The defensive helper
      ``_extract_single_cell_paint_args`` ALSO verifies the coord is
      identical across all training pairs — the four matchers pin
      cardinality (one cell per pair), colour (uniform K), input
      dimension stability, and per-pair input==output shape, but they
      do NOT pin the coord's position across pairs; a stored
      literal-coord rule only generalises when training pairs share
      the same (r, c). The chosen ``condition.type``
      (``single_cell_change_per_pair``) is the strictest of the four
      gating matchers and the one that directly pins the selection's
      cardinality + shape; the other three matchers contribute to
      determining the action's args without naming a new label. STRICT
      mutual exclusion with the iter-14 identity branch is guaranteed
      by ``single_cell_change_per_pair`` requiring ``num_groups == 1``
      while ``identity_transformation`` requires ``num_groups == 0``,
      so the iter-25 branch is reachable only when iter 14's matcher
      gate is closed (no explicit NOT check required). STRICT mutual
      exclusion with the iter-21 make_grid branch is guaranteed by
      ``grid_size_preserved`` (this iter, per-pair size_match True)
      versus ``grid_size_changed`` (iter 21, existential per-pair
      size_match False) being exact partitioners of the dimensional
      axis on any non-empty pair_analyses. The new ``concept`` /
      ``category`` labels are ``paint_single_cell`` /
      ``color_transform`` (the latter matches ``_infer_category``'s
      colour-bucket pattern). Second non-identity rule shape any iter
      has been able to mint without anti-unification or polymorphic
      args — closes the iter-16 polymorphic-args obstacle on the
      ``coloring`` argument list because the selection list, the
      colour, and the canvas shape are all fixed by training data.

    * ``{"type": "identity", ...}`` + ``multi_group_per_pair`` +
      ``output_color_uniform`` + ``input_dimensions_constant`` +
      ``grid_size_preserved`` all fire (iter 29) →
      ``condition.type = "multi_group_per_pair"``, ``action.dsl =
      "coloring"`` with ``args = {"selection": [[r1, c1], ..., [rM, cM]],
      "color": K}``. The selection is the row-major-sorted union of every
      blob's ``positions`` field across the first pair's groups (each
      group is one connected change region; iter 28's matcher gates
      ``num_groups >= 2`` per pair, so M is the total cell count summed
      across all blobs). K comes from any group's ``output_colors[0]``.
      The defensive helper ``_extract_multi_blob_paint_args`` ALSO
      verifies the unioned position SET is bit-identical across all
      training pairs — iter 28's matcher pins the cardinality regime
      (≥ 2 blobs per pair) and iter 18 pins the colour, but neither
      pins the blobs' coord set across pairs; a stored literal-coord-
      list rule only generalises when training pairs share the same
      multi-blob layout. STRICT mutual exclusion with the iter-14
      identity branch (cardinality 0 vs cardinality ≥ 2), the iter-25
      single-cell branch and the iter-27 multi-cell single-blob branch
      (those require ``num_groups == 1``, this requires
      ``num_groups >= 2``), and the iter-21 make_grid branch
      (``grid_size_preserved`` partitions against ``grid_size_changed``)
      — see iter 28's matcher docstring for the three-way partition
      proof on the group-count axis. The new ``concept`` / ``category``
      labels are ``paint_blobs`` / ``color_transform`` (pluralised
      counterpart to iter 27's ``paint_blob``). Fourth non-identity
      rule shape any iter has been able to mint without anti-unification
      or polymorphic args, and the FIRST to consume the multi-blob
      recognition territory iter 23's "Next gap" log named as the
      deferred axis after iter 23's single-blob territory was carved
      up by iters 24 / 26 / 25 / 27. With four sibling rules now
      potentially sharing the ``(*, coloring)`` skeleton on disk —
      single-cell (iter 25), multi-cell single-blob (iter 27),
      multi-blob (this iter), plus the identity no-op — the input
      preconditions for anti-unification to actually do work
      (multiple ``coloring``-action rules with different selection
      cardinalities) exist for the first time. That makes lifting
      ``selection`` into a variable an immediate next step rather
      than a hypothetical one, as iter 28's "Next gap" log named
      ("the largest unfilled gap remains P3").

    * ``{"type": "identity", ...}`` + ``multi_cell_change_group_per_pair``
      + ``output_color_uniform`` + ``input_dimensions_constant`` +
      ``grid_size_preserved`` all fire (iter 27) →
      ``condition.type = "multi_cell_change_group_per_pair"``,
      ``action.dsl = "coloring"`` with
      ``args = {"selection": [[r1, c1], ..., [rN, cN]], "color": K}``.
      The coord list is the first pair's single group's ``positions``
      field (iter 27's ``_analyze_pair`` extension), serialized in
      row-major sorted order. K comes from any change group's
      ``output_colors[0]``. The defensive helper
      ``_extract_multi_cell_paint_args`` ALSO verifies the position
      SET is identical across all training pairs — the four matchers
      pin cardinality range (one blob, 2+ cells per pair), colour
      (uniform K), input dimension stability, and per-pair input==output
      shape, but they do NOT pin the blob's coord set across pairs;
      a stored literal-coord-list rule only generalises when training
      pairs share the same blob. The chosen ``condition.type``
      (``multi_cell_change_group_per_pair``) is the strictest of the
      four gating matchers and the one that pins the selection's
      cardinality range; the other three matchers contribute to
      determining the action's args without naming a new label. STRICT
      mutual exclusion with the iter-25 single-cell branch is
      guaranteed by iter-26's matcher requiring ``cell_count >= 2``
      while iter-24's matcher requires ``cell_count == 1`` — the two
      matchers are exact partitioners of iter 23's single-group
      territory on the cell-count axis. STRICT mutual exclusion with
      the iter-14 identity branch (cardinality 0 vs 1+) and the
      iter-21 make_grid branch (grid_size_preserved vs
      grid_size_changed) holds by the same logic as iter 25. The new
      ``concept`` / ``category`` labels are ``paint_blob`` /
      ``color_transform``. Third non-identity rule shape any iter has
      been able to mint without anti-unification or polymorphic args
      — closes the iter-16 polymorphic-args obstacle on the
      ``coloring`` argument list at the multi-cell cardinality, with
      the same literal-coord-list shape iter 25 proved at the
      cardinality-1 case.

    Non-translatable shapes return ``None`` deliberately — a caller that
    wants to attempt a save must check the return value and fall back to
    the legacy writer (or skip the save). ``color_mapping`` and
    ``recolor_sequential`` shapes still require an anti-unification-
    discovered abstraction for their ``action.dsl``, deferred to a later
    iter.
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

    # V2 gate: the recognition matchers must actually fire on the patterns
    # the source task produced. This keeps the translator honest — it cannot
    # mint a condition.type that the live recognizer would reject.
    from agent.conditions import recognized_conditions  # local import
    fired = recognized_conditions(patterns)

    pair_analyses = patterns.get("pair_analyses") or []
    if not isinstance(pair_analyses, list):
        pair_analyses = []
    min_evidence = max(1, len(pair_analyses))

    created_at = now if isinstance(now, str) and now else datetime.utcnow().isoformat()

    if "identity_transformation" in fired:
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

    # Iter 21: make_grid(H, W, K) branch. Gated on the conjunction of three
    # named recognition preconditions named across iters 17 / 18 / 20.
    if ("grid_size_changed" in fired
            and "output_dimensions_constant" in fired
            and "output_color_uniform" in fired):
        h_w_k = _extract_make_grid_args(pair_analyses)
        if h_w_k is None:
            return None
        h, w, k = h_w_k
        return {
            "id": rule_id,
            "concept": "make_constant_grid",
            "category": "geometric_transform",
            "condition": {
                "type": "output_dimensions_constant",
                "params": {},
                "min_evidence": min_evidence,
            },
            "action": {
                "dsl": "make_grid",
                "args": {"height": h, "width": w, "color": k},
            },
            "covers": [task_hex],
            "source_task": task_hex,
            "anti_unification_trace": None,
            "created_at": created_at,
            "times_reused": 0,
        }

    # Iter 25: single-cell uniform-paint branch. Gated on the conjunction
    # of four named recognition preconditions across iters 1 / 18 / 22 / 24.
    # STRICTLY mutually exclusive with the iter-14 identity branch
    # (single_cell_change_per_pair requires num_groups == 1, identity
    # requires num_groups == 0) and with the iter-21 make_grid branch
    # (grid_size_preserved partitions against grid_size_changed), so the
    # order of branches above is incidental — any patterns dict that fires
    # one cannot fire the others.
    if ("single_cell_change_per_pair" in fired
            and "output_color_uniform" in fired
            and "input_dimensions_constant" in fired
            and "grid_size_preserved" in fired):
        coord_color = _extract_single_cell_paint_args(pair_analyses)
        if coord_color is None:
            return None
        (r, c), k = coord_color
        return {
            "id": rule_id,
            "concept": "paint_single_cell",
            "category": "color_transform",
            "condition": {
                "type": "single_cell_change_per_pair",
                "params": {},
                "min_evidence": min_evidence,
            },
            "action": {
                "dsl": "coloring",
                "args": {"selection": [[r, c]], "color": k},
            },
            "covers": [task_hex],
            "source_task": task_hex,
            "anti_unification_trace": None,
            "created_at": created_at,
            "times_reused": 0,
        }

    # Iter 27: multi-cell single-blob uniform-paint branch. Gated on the
    # conjunction of four named recognition preconditions across iters
    # 1 / 18 / 22 / 26. STRICTLY mutually exclusive with the iter-25
    # single-cell branch above (multi_cell_change_group_per_pair requires
    # cell_count >= 2 while single_cell_change_per_pair requires
    # cell_count == 1, an exact partition of iter 23's single-group
    # territory on the cell-count axis — see iter 26's matcher
    # docstring). STRICTLY mutually exclusive with the iter-14 identity
    # branch (multi_cell requires num_groups == 1, identity requires
    # num_groups == 0) and with the iter-21 make_grid branch
    # (grid_size_preserved partitions against grid_size_changed), so the
    # order of branches above is incidental.
    #
    # The selection list comes from the (iter 27) ``positions`` field
    # ExtractPatternOperator._analyze_pair now emits per group — a
    # row-major-sorted list of the blob's coords. The defensive helper
    # ``_extract_multi_cell_paint_args`` ALSO verifies the position SET
    # is bit-identical across all training pairs — the four matchers
    # pin cardinality range (one blob with 2+ cells per pair), colour
    # (uniform K), input dimension stability, and per-pair input==output
    # shape, but they do NOT pin the blob's coord set across pairs; a
    # stored literal-coord-list rule only generalises when training
    # pairs share the same blob position. K comes from any group's
    # ``output_colors[0]`` (iter-18 pins it constant). Third
    # non-identity rule shape any iter has been able to mint without
    # anti-unification or polymorphic args.
    if ("multi_cell_change_group_per_pair" in fired
            and "output_color_uniform" in fired
            and "input_dimensions_constant" in fired
            and "grid_size_preserved" in fired):
        positions_color = _extract_multi_cell_paint_args(pair_analyses)
        if positions_color is None:
            return None
        positions, k = positions_color
        return {
            "id": rule_id,
            "concept": "paint_blob",
            "category": "color_transform",
            "condition": {
                "type": "multi_cell_change_group_per_pair",
                "params": {},
                "min_evidence": min_evidence,
            },
            "action": {
                "dsl": "coloring",
                "args": {
                    "selection": [[r, c] for (r, c) in positions],
                    "color": k,
                },
            },
            "covers": [task_hex],
            "source_task": task_hex,
            "anti_unification_trace": None,
            "created_at": created_at,
            "times_reused": 0,
        }

    # Iter 29: multi-blob uniform-paint branch. Gated on the conjunction
    # of four named recognition preconditions across iters 1 / 18 / 22 / 28.
    # STRICTLY mutually exclusive with the iter-14 identity branch
    # (multi_group_per_pair requires num_groups >= 2 vs identity's
    # num_groups == 0), the iter-25 single-cell branch and the iter-27
    # multi-cell single-blob branch (both require num_groups == 1), and
    # the iter-21 make_grid branch (grid_size_preserved partitions against
    # grid_size_changed) — so the branch order above is incidental.
    if ("multi_group_per_pair" in fired
            and "output_color_uniform" in fired
            and "input_dimensions_constant" in fired
            and "grid_size_preserved" in fired):
        positions_color = _extract_multi_blob_paint_args(pair_analyses)
        if positions_color is None:
            return None
        positions, k = positions_color
        return {
            "id": rule_id,
            "concept": "paint_blobs",
            "category": "color_transform",
            "condition": {
                "type": "multi_group_per_pair",
                "params": {},
                "min_evidence": min_evidence,
            },
            "action": {
                "dsl": "coloring",
                "args": {
                    "selection": [[r, c] for (r, c) in positions],
                    "color": k,
                },
            },
            "covers": [task_hex],
            "source_task": task_hex,
            "anti_unification_trace": None,
            "created_at": created_at,
            "times_reused": 0,
        }

    return None


def _extract_make_grid_args(pair_analyses: list) -> tuple | None:
    """Pull constant (height, width, color) out of a make_grid-shape
    patterns dict. Returns ``None`` if any value cannot be extracted
    cleanly. Callers must already have confirmed the iter-17/18/20
    matcher conjunction fired; this helper is defensive re-extraction
    only, so a transient extractor anomaly cannot mint a malformed
    rule that ``validate_rule`` would happily save but ``apply_DSL``
    would later reject."""
    if not pair_analyses:
        return None
    first = pair_analyses[0]
    if not isinstance(first, dict):
        return None
    h = first.get("output_height")
    w = first.get("output_width")
    if not isinstance(h, int) or isinstance(h, bool) or h < 1:
        return None
    if not isinstance(w, int) or isinstance(w, bool) or w < 1:
        return None
    for analysis in pair_analyses:
        if not isinstance(analysis, dict):
            continue
        groups = analysis.get("groups")
        if not isinstance(groups, list):
            continue
        for group in groups:
            if not isinstance(group, dict):
                continue
            colors = group.get("output_colors")
            if not isinstance(colors, list) or len(colors) < 1:
                continue
            candidate = colors[0]
            if isinstance(candidate, int) and not isinstance(candidate, bool):
                if candidate in _VALID_DSL_COLORS:
                    return (h, w, candidate)
                return None
    return None


def _extract_single_cell_paint_args(pair_analyses: list) -> tuple | None:
    """Pull a ((row, col), color) tuple out of a single-cell-paint patterns
    dict. Returns ``None`` if any value cannot be extracted cleanly or if
    the cell coord differs across training pairs.

    Callers must already have confirmed the iter 1 / 18 / 22 / 24 matcher
    conjunction (``single_cell_change_per_pair`` AND
    ``output_color_uniform`` AND ``input_dimensions_constant`` AND
    ``grid_size_preserved``) fired; this helper is defensive
    re-extraction. Two checks the matcher conjunction does NOT enforce:

      * ``(top_row, top_col)`` is bit-identical across pairs. The
        ``single_cell_change_per_pair`` matcher pins cardinality (one
        cell per pair) but not position; a stored literal-coord rule
        only generalises when training pairs share the same coord.
        ``input_dimensions_constant`` makes the *domain* of a stored
        coord safe (the test input's dims match training), but not the
        coord itself — a task where pair 0 changes (0, 0) and pair 1
        changes (2, 1) fires every matcher in the conjunction yet does
        not have a single literal coord that abstracts all training
        pairs. Such tasks are deferred to a future iter that extracts
        the coord via an input-side predicate (e.g. anti-unification
        lifting position to "wherever input has colour C").
      * ``output_colors[0]`` is in the ``coloring`` primitive's valid
        colour set (``range(10) | {13}``). ``output_color_uniform``
        pins the value as constant across all groups in all pairs but
        does not check the colour palette domain; foreclosing here
        prevents a malformed rule that ``validate_rule`` would happily
        save but ``coloring`` would later reject.

    Mirror posture: ``_extract_make_grid_args`` performs the same
    defensive re-extraction for the iter-21 branch's (H, W, K).
    """
    if not pair_analyses:
        return None
    coord: tuple | None = None
    color: int | None = None
    for analysis in pair_analyses:
        if not isinstance(analysis, dict):
            return None
        groups = analysis.get("groups")
        if not isinstance(groups, list) or len(groups) != 1:
            return None
        group = groups[0]
        if not isinstance(group, dict):
            return None
        r = group.get("top_row")
        c = group.get("top_col")
        if not isinstance(r, int) or isinstance(r, bool) or r < 0:
            return None
        if not isinstance(c, int) or isinstance(c, bool) or c < 0:
            return None
        out_colors = group.get("output_colors")
        if not isinstance(out_colors, list) or len(out_colors) != 1:
            return None
        candidate = out_colors[0]
        if not isinstance(candidate, int) or isinstance(candidate, bool):
            return None
        if candidate not in _VALID_DSL_COLORS:
            return None
        if coord is None:
            coord = (r, c)
        elif coord != (r, c):
            return None
        if color is None:
            color = candidate
        elif color != candidate:
            return None
    if coord is None or color is None:
        return None
    return (coord, color)


def _extract_multi_cell_paint_args(pair_analyses: list) -> tuple | None:
    """Pull a ``(positions_list, color)`` tuple out of a multi-cell-paint
    patterns dict. Returns ``None`` if any value cannot be extracted
    cleanly or if the blob's position set differs across training pairs.

    Callers must already have confirmed the iter 1 / 18 / 22 / 26 matcher
    conjunction (``multi_cell_change_group_per_pair`` AND
    ``output_color_uniform`` AND ``input_dimensions_constant`` AND
    ``grid_size_preserved``) fired; this helper is defensive
    re-extraction. Three checks the matcher conjunction does NOT enforce:

      * The blob's full coord set is bit-identical across pairs. The
        ``multi_cell_change_group_per_pair`` matcher pins cardinality
        range (one blob, 2+ cells) but not position. A stored
        literal-coord-list rule only generalises when training pairs
        share the same blob; a task where pair 0's blob is
        {(0,0),(0,1)} and pair 1's is {(2,1),(2,2)} fires every
        matcher in the conjunction yet does not have a single literal
        coord list that abstracts all training pairs. Such tasks are
        deferred to a future iter that extracts the selection via an
        input-side predicate (e.g. anti-unification lifting position
        to "wherever input has colour C").
      * The ``positions`` list emitted by ``_analyze_pair`` has the
        expected shape and contains ``cell_count`` valid coord tuples,
        each with strict-non-negative-int (not bool) row / col.
      * ``output_colors[0]`` is in the ``coloring`` primitive's valid
        colour set (``range(10) | {13}``). ``output_color_uniform``
        pins the value as constant across all groups in all pairs
        but does not check the colour palette domain; foreclosing
        here prevents a malformed rule that ``validate_rule`` would
        happily save but ``coloring`` would later reject.

    Returns the canonical positions as a sorted list of
    ``(row, col)`` tuples so the caller can serialize it deterministically
    into the rule's ``action.args.selection`` field.

    Mirror posture: ``_extract_single_cell_paint_args`` performs the same
    defensive re-extraction for the iter-25 branch's ((r, c), K), and
    ``_extract_make_grid_args`` for the iter-21 branch's (H, W, K).
    """
    if not pair_analyses:
        return None
    canonical_positions: tuple | None = None
    color: int | None = None
    for analysis in pair_analyses:
        if not isinstance(analysis, dict):
            return None
        groups = analysis.get("groups")
        if not isinstance(groups, list) or len(groups) != 1:
            return None
        group = groups[0]
        if not isinstance(group, dict):
            return None
        cell_count = group.get("cell_count")
        if not isinstance(cell_count, int) or isinstance(cell_count, bool):
            return None
        if cell_count < 2:
            return None
        raw_positions = group.get("positions")
        if not isinstance(raw_positions, list) or len(raw_positions) != cell_count:
            return None
        canon_coords = []
        for p in raw_positions:
            if not isinstance(p, (list, tuple)) or len(p) != 2:
                return None
            r, c = p[0], p[1]
            if not isinstance(r, int) or isinstance(r, bool) or r < 0:
                return None
            if not isinstance(c, int) or isinstance(c, bool) or c < 0:
                return None
            canon_coords.append((r, c))
        # Sort to make cross-pair comparison order-independent, and to
        # produce a stable serialization for the rule's selection arg.
        canon_tuple = tuple(sorted(canon_coords))
        if len(set(canon_tuple)) != cell_count:
            return None  # duplicate coords inside a single blob — corrupt input
        out_colors = group.get("output_colors")
        if not isinstance(out_colors, list) or len(out_colors) != 1:
            return None
        candidate = out_colors[0]
        if not isinstance(candidate, int) or isinstance(candidate, bool):
            return None
        if candidate not in _VALID_DSL_COLORS:
            return None
        if canonical_positions is None:
            canonical_positions = canon_tuple
        elif canonical_positions != canon_tuple:
            return None
        if color is None:
            color = candidate
        elif color != candidate:
            return None
    if canonical_positions is None or color is None:
        return None
    return (list(canonical_positions), color)


def _extract_multi_blob_paint_args(pair_analyses: list) -> tuple | None:
    """Pull a ``(positions_list, color)`` tuple out of a multi-blob-paint
    patterns dict. Returns ``None`` if any value cannot be extracted
    cleanly or if the unioned blob position set differs across training
    pairs.

    Callers must already have confirmed the iter 1 / 18 / 22 / 28 matcher
    conjunction (``multi_group_per_pair`` AND ``output_color_uniform``
    AND ``input_dimensions_constant`` AND ``grid_size_preserved``) fired;
    this helper is defensive re-extraction. Four checks the matcher
    conjunction does NOT enforce:

      * The unioned position set across every blob is bit-identical
        across pairs. The ``multi_group_per_pair`` matcher pins the
        per-pair cardinality regime (``num_groups >= 2``) but not the
        blobs' coord set; a stored literal-coord-list rule only
        generalises when training pairs share the same multi-blob
        layout. A task where pair 0's blobs are {(0,0),(0,1)} and
        {(2,2)} and pair 1's are {(2,1),(2,2)} and {(0,0)} would fire
        every matcher in the conjunction yet has no single literal
        coord list abstracting both pairs (and the unions differ:
        {(0,0),(0,1),(2,2)} vs {(2,1),(2,2),(0,0)}). Such tasks are
        deferred to a future iter that extracts the selection via an
        input-side predicate (e.g. anti-unification lifting position
        to "wherever input has colour C").
      * Every blob carries a ``positions`` list whose length matches
        its ``cell_count``, with strict-non-negative-int (not bool)
        row / col on every entry. Iter 27's ``_analyze_pair``
        extension is the source.
      * The unioned coord set has no duplicates across blobs (two
        blobs sharing a cell would mean the connectivity computation
        is internally corrupt — strict refusal rather than silent
        deduplication).
      * ``output_colors[0]`` is in the ``coloring`` primitive's valid
        colour set (``range(10) | {13}``). ``output_color_uniform``
        pins the value as constant across all groups in all pairs but
        does not check the colour palette domain; foreclosing here
        prevents a malformed rule that ``validate_rule`` would happily
        save but ``coloring`` would later reject.

    Returns the canonical positions as a sorted list of ``(row, col)``
    tuples so the caller can serialize it deterministically into the
    rule's ``action.args.selection`` field — the same row-major-sorted
    shape iter 25 / iter 27 produce.

    Mirror posture: ``_extract_multi_cell_paint_args`` performs the same
    defensive re-extraction for the iter-27 single-blob branch's
    ((positions, K)), ``_extract_single_cell_paint_args`` for the iter-25
    branch's ((r, c), K), and ``_extract_make_grid_args`` for the
    iter-21 branch's (H, W, K).
    """
    if not pair_analyses:
        return None
    canonical_positions: tuple | None = None
    color: int | None = None
    for analysis in pair_analyses:
        if not isinstance(analysis, dict):
            return None
        groups = analysis.get("groups")
        if not isinstance(groups, list) or len(groups) < 2:
            return None
        union_coords: list = []
        for group in groups:
            if not isinstance(group, dict):
                return None
            cell_count = group.get("cell_count")
            if not isinstance(cell_count, int) or isinstance(cell_count, bool):
                return None
            if cell_count < 1:
                return None
            raw_positions = group.get("positions")
            if not isinstance(raw_positions, list) or len(raw_positions) != cell_count:
                return None
            for p in raw_positions:
                if not isinstance(p, (list, tuple)) or len(p) != 2:
                    return None
                r, c = p[0], p[1]
                if not isinstance(r, int) or isinstance(r, bool) or r < 0:
                    return None
                if not isinstance(c, int) or isinstance(c, bool) or c < 0:
                    return None
                union_coords.append((r, c))
            out_colors = group.get("output_colors")
            if not isinstance(out_colors, list) or len(out_colors) != 1:
                return None
            candidate = out_colors[0]
            if not isinstance(candidate, int) or isinstance(candidate, bool):
                return None
            if candidate not in _VALID_DSL_COLORS:
                return None
            if color is None:
                color = candidate
            elif color != candidate:
                return None
        canon_tuple = tuple(sorted(union_coords))
        if len(set(canon_tuple)) != len(canon_tuple):
            # Two blobs share a cell — connectivity computation is corrupt;
            # refuse rather than silently de-duplicate.
            return None
        if canonical_positions is None:
            canonical_positions = canon_tuple
        elif canonical_positions != canon_tuple:
            return None
    if canonical_positions is None or color is None:
        return None
    return (list(canonical_positions), color)


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
