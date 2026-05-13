# Rule Format Specification

This document is the **authoritative specification** of the `rule_NNN.json`
schema stored in `procedural_memory/`. It expands `CLAUDE.md §3.2` with a
formal JSON Schema, field-by-field semantics, validation rules, and migration
guidance.

A rule is the persistent unit of learned knowledge in ARBOR. A *valid* rule is
a **`{condition, action}` pair** — a manual describing exactly when and how to
apply a DSL primitive. Both halves are mandatory and validated on save.

---

## 1. JSON Schema (draft-07)

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "ARBOR Procedural Memory Rule",
  "type": "object",
  "required": [
    "id",
    "concept",
    "category",
    "condition",
    "action",
    "covers",
    "source_task",
    "anti_unification_trace",
    "created_at",
    "times_reused"
  ],
  "additionalProperties": false,
  "properties": {
    "id":       { "type": "integer", "minimum": 1 },
    "concept":  { "type": "string",  "minLength": 1 },
    "category": { "type": "string",  "minLength": 1 },

    "condition": {
      "type": "object",
      "required": ["type", "params", "min_evidence"],
      "additionalProperties": false,
      "properties": {
        "type":         { "type": "string", "minLength": 1 },
        "params":       { "type": "object" },
        "min_evidence": { "type": "integer", "minimum": 1 }
      }
    },

    "action": {
      "type": "object",
      "required": ["dsl", "args"],
      "additionalProperties": false,
      "properties": {
        "dsl":  { "type": "string", "minLength": 1 },
        "args": { "type": "object" }
      }
    },

    "covers": {
      "type": "array",
      "items": { "type": "string", "pattern": "^[0-9a-f]{8}$" },
      "minItems": 1,
      "uniqueItems": true
    },

    "source_task": {
      "type": "string",
      "pattern": "^[0-9a-f]{8}$"
    },

    "anti_unification_trace": {
      "oneOf": [
        { "type": "null" },
        { "type": "string", "pattern": "^episodic_memory/.+/anti_unification/.+\\.json$" }
      ]
    },

    "created_at":   { "type": "string", "format": "date-time" },
    "times_reused": { "type": "integer", "minimum": 0 }
  }
}
```

The schema lives canonically here. A machine-readable copy belongs at
`docs/rule_format.schema.json` once tooling is added.

---

## 2. Field Semantics

| Field | Meaning |
|-------|---------|
| `id` | Monotonic integer. Assigned by `save_rule()`, never reused on deletion. |
| `concept` | Human-readable label of the *abstract idea* the rule encodes (e.g. `"recolor_objects_by_position"`). |
| `category` | Coarse grouping tag used for retrieval and anti-unification candidacy. Two rules in the same category are candidates for unification when a new rule is added. |
| `condition.type` | Name of a pattern matcher registered in the **condition registry** (§4). The matcher decides *when* this rule applies. |
| `condition.params` | Matcher-specific parameters. Schema validated by the matcher itself, not by this document. |
| `condition.min_evidence` | Minimum number of supporting evidence units (typically training pairs) required before this rule fires. Used to suppress over-eager matches. |
| `action.dsl` | Name of a DSL primitive registered in the **DSL registry** (§5). |
| `action.args` | Argument bindings for the DSL primitive. Anti-unified rules will contain *generalization variables* here rather than concrete values. |
| `covers` | List of ARC task IDs (lowercase hex, 8 chars) this rule has successfully solved. Append-only during a session; deduplicated. |
| `source_task` | The first task that produced this rule. Stays fixed even as `covers` grows. |
| `anti_unification_trace` | `null` for *source* rules (learned from a single task). Path to a trace JSON for *abstract* rules produced by `program/anti_unification.unify()`. Documents which input rules were combined. |
| `created_at` | ISO 8601 timestamp at insertion time. |
| `times_reused` | Counter incremented each time the rule's `condition` fires on a *new* (not-in-`covers`) task and the resulting `action` produces the correct output. |

### 2.1 Anti-unification trace contract

When a rule is the product of unification, `anti_unification_trace` points to a
JSON file in:

```
episodic_memory/<task_id>/anti_unification/<trace_id>.json
```

whose shape is documented separately in `docs/ANTI_UNIFICATION.md`. The trace
records the input rules' IDs, the common skeleton, and the variable bindings
introduced by lifting.

---

## 3. Validation Rules

`agent/memory.py:save_rule()` **must** enforce all of the following before
writing to disk. Failure raises `RuleSchemaError` and the write is aborted.

| # | Check | Failure mode |
|---|-------|--------------|
| V1 | Top-level JSON validates against §1 schema | `RuleSchemaError("schema validation failed: <jsonschema message>")` |
| V2 | `condition.type` is registered in the condition registry (§4) | `RuleSchemaError("unknown condition.type: <name>")` |
| V3 | `action.dsl` is registered in the DSL registry (§5) | `RuleSchemaError("unknown action.dsl: <name>")` |
| V4 | `source_task` ∈ `covers` | `RuleSchemaError("source_task must appear in covers")` |
| V5 | If `anti_unification_trace` is non-null, the referenced file exists | `RuleSchemaError("trace file not found: <path>")` |
| V6 | `id` does not collide with an existing file in `procedural_memory/` | `RuleSchemaError("id collision: rule_<NNN>.json exists")` |
| V7 | No additional top-level keys beyond §1's `required` list | `RuleSchemaError("unexpected key: <key>")` |

Validation runs **before** the equivalence check used for `covers` extension —
an invalid candidate is never allowed to mutate an existing valid rule.

---

## 4. Condition Type Registry

The set of currently-registered `condition.type` values. Each entry points to a
matcher function returning `bool` given a `patterns` dict (the output of
`extract_pattern` in `agent/active_operators.py`).

| `condition.type` | Matcher module | Params | Status |
|------------------|----------------|--------|--------|
| `grid_size_preserved` | `agent/conditions/grid_size_preserved.py` | *(none)* | active — true iff every example pair has matching input/output dimensions |
| `consistent_color_mapping` | `agent/conditions/consistent_color_mapping.py` | *(none)* | active (iter 8) — true iff at least one (input_color → output_color) pair is observed in the changed-cell groups *and* every observed input color maps to a single output color across all example pairs. Dimension-agnostic (does not imply `grid_size_preserved`). The recognition counterpart to `_try_color_mapping` in `agent/active_operators.py` — same precondition, surfaced as named recognition vocabulary so a future `coloring`-based rule produced by anti-unification can declare it. |
| `sequential_recoloring` | `agent/conditions/sequential_recoloring.py` | *(none)* | active (iter 10) — true iff every example pair has the same non-zero number of change groups, each group has exactly one input colour and one output colour, the per-pair output colours form a contiguous integer range, and at least one of `top_row` / `top_col` orders the groups so the output colours appear in that range. Dimension-agnostic by design (does not piggyback on `grid_size_preserved`, matching iter-8's separation-of-concerns pattern). The recognition counterpart to `_try_recolor_sequential` in `agent/active_operators.py`. Stricter than `consistent_color_mapping`: it additionally asserts the outputs are a positionally-ordered contiguous range. |

Adding a new condition type:

1. Implement `match(patterns: dict, params: dict) -> bool` in
   `agent/conditions/<name>.py` (module created on first entry).
2. Register the name in `agent/conditions/__init__.py:CONDITION_REGISTRY`.
3. Document the params schema in this table.
4. Provide at least one example rule under §6 referencing it.

A condition matcher must be **deterministic** and **side-effect-free**. Random
sampling, file I/O, or stateful counters are forbidden.

---

## 5. DSL Registry

The set of currently-registered `action.dsl` primitive names. Each entry is a
function in `procedural_memory/DSL/` dispatched by `apply.py`.

| `action.dsl` | Implementation | Status |
|--------------|----------------|--------|
| `coloring`   | `procedural_memory/DSL/coloring.py` | active (iter 3) — paint a coord or list of coords with a color in `0..9` or `13` (transparent sentinel). Pure; rejects OOB / malformed selection. |
| `make_grid`  | `procedural_memory/DSL/make_grid.py` | active (iter 3) — produce a fresh `height × width` canvas filled with a color in `0..9` or `13`. Pure; rows are independent. |

**The set above is closed.** F3 in `docs/INVARIANTS.md` auto-reverts any commit
that adds a third hand-coded primitive. Further transformations must be
*discovered* by `program.anti_unification.unify()` and persisted as data in
`procedural_memory/rule_NNN.json` with `anti_unification_trace` set — see
`CLAUDE.md §6.2`.

Adding a new primitive:

1. Implement `def <name>(grid, **args) -> grid` in the appropriate file
   (`transformation.py`, `selection.py`, `util.py`, `layer.py`).
2. Register in `procedural_memory/DSL/apply.py:DSL_REGISTRY`.
3. Document the args schema in this table.
4. Provide at least one example rule under §6 referencing it.

A DSL primitive must be **pure**: given the same inputs, produce the same
output. No randomness, no global state.

---

## 6. Examples

### 6.1 Example 1 — VALID, source rule (no unification yet)

A rule learned from a single task. `anti_unification_trace` is `null` and
`covers` contains exactly the source task.

```json
{
  "id": 1,
  "concept": "fill_enclosed_region_with_marker_color",
  "category": "region_fill",

  "condition": {
    "type": "enclosed_region_present",
    "params": {
      "boundary_color": 5,
      "marker_color": "<any non-boundary, non-background>"
    },
    "min_evidence": 2
  },

  "action": {
    "dsl": "fill_region",
    "args": {
      "region": "enclosed_by(boundary_color)",
      "color": "marker_color"
    }
  },

  "covers": ["08ed6ac7"],
  "source_task": "08ed6ac7",
  "anti_unification_trace": null,
  "created_at": "2026-05-14T09:12:33.000000",
  "times_reused": 0
}
```

### 6.2 Example 2 — VALID, anti-unified abstract rule

Produced by combining two source rules in the same category. Note the
generalization variable `<sort_key>` in `action.args` — the rule now applies to
both row-ordered and column-ordered sequences.

```json
{
  "id": 17,
  "concept": "recolor_objects_in_sequence",
  "category": "sequential_recolor",

  "condition": {
    "type": "objects_sortable_by_axis",
    "params": {
      "object_color": 0,
      "axes_allowed": ["top_row", "left_col"]
    },
    "min_evidence": 2
  },

  "action": {
    "dsl": "recolor_sequential",
    "args": {
      "sort_key": "<axis_from_condition>",
      "start_color": 3,
      "step": 1,
      "source_colors": [0]
    }
  },

  "covers": ["e5790162", "a64e4611", "28e73c20"],
  "source_task": "e5790162",
  "anti_unification_trace": "episodic_memory/a64e4611/anti_unification/au_002.json",
  "created_at": "2026-05-14T10:05:11.000000",
  "times_reused": 2
}
```

### 6.3 Example 3 — INVALID, missing `condition` (the legacy bug)

The form produced by SOAR-ARC-test's `test13-eval` branch (168 such files).
`save_rule()` must **reject this on load and on save**.

```json
{
  "id": 1,
  "concept": "recolor_objects_sequentially",
  "category": "color_transform",
  "rule": {
    "type": "recolor_sequential",
    "sort_key": "top_row",
    "start_color": 3,
    "source_colors": [0],
    "confidence": 1.0
  },
  "covers": ["e5790162", "a64e4611"],
  "source_task": "e5790162",
  "created_at": "2026-04-29T07:50:25.355401",
  "times_reused": 0
}
```

Why invalid:
- V1: top-level `rule` key not in schema; `condition` and `action` absent.
- V7: legacy `rule` key is forbidden.

This format is the direct cause of the KCC2026 coverage observation
(rule coverage < 1 across 168 rules) — there is no `condition` for the agent
to query, so every task triggers a *new* rule rather than reusing one.

### 6.4 Example 4 — INVALID, unknown DSL primitive

Schema-shaped but references a primitive not in §5's registry.

```json
{
  "id": 99,
  "concept": "magic_transform",
  "category": "uncategorized",

  "condition": {
    "type": "always",
    "params": {},
    "min_evidence": 1
  },

  "action": {
    "dsl": "do_magic",
    "args": {}
  },

  "covers": ["00000000"],
  "source_task": "00000000",
  "anti_unification_trace": null,
  "created_at": "2026-05-14T11:00:00.000000",
  "times_reused": 0
}
```

Why invalid:
- V3: `action.dsl = "do_magic"` is not registered.
- (When registry is empty, **all** `action.dsl` values fail V3 — until the
  first primitive is added.)

### 6.5 Example 5 — MIGRATION from legacy to v1

The conversion path for Example 6.3 once a `condition.type` matcher for
sequential recoloring is available.

**Step 1** — Define the matcher. Add to `agent/conditions/`:
```python
# agent/conditions/objects_sortable_by_axis.py
def match(patterns: dict, params: dict) -> bool:
    objs = patterns.get("objects_per_pair", [])
    if not objs: return False
    color = params["object_color"]
    axes  = params["axes_allowed"]
    return all(
        all(o.color == color for o in pair_objs)
        and any(_sortable(pair_objs, axis) for axis in axes)
        for pair_objs in objs
    )
```
Register name `"objects_sortable_by_axis"` in `CONDITION_REGISTRY`.

**Step 2** — Define the primitive. Add to `procedural_memory/DSL/transformation.py`:
```python
def recolor_sequential(grid, sort_key, start_color, step, source_colors):
    # ... implementation ...
```
Register name `"recolor_sequential"` in `DSL_REGISTRY`.

**Step 3** — Rewrite the JSON. The legacy
```json
"rule": {"type": "recolor_sequential", "sort_key": "top_row", "start_color": 3, "source_colors": [0]}
```
becomes:
```json
"condition": {
  "type": "objects_sortable_by_axis",
  "params": {"object_color": 0, "axes_allowed": ["top_row"]},
  "min_evidence": 2
},
"action": {
  "dsl": "recolor_sequential",
  "args": {
    "sort_key": "top_row",
    "start_color": 3,
    "step": 1,
    "source_colors": [0]
  }
}
```

Run the migration through `agent/memory.py:migrate_legacy_rules()` (function
to be added in the upcoming session). It must:
- Read all `rule_NNN.json` whose top-level shape matches the legacy form.
- For each, lift the `rule` payload into `action` and synthesize a
  `condition` block by querying the matcher registry.
- If no matching condition.type exists yet, **abort migration for that rule**
  and mark it `invalid: needs_condition_matcher` in `logs/migration_log.md`.
- Re-write only on full success.

Partial / silent migration is forbidden — every rejected rule must surface in
the log so a matcher can be authored.

---

## 7. Implementation Status

As of 2026-05-13, branch `test20`:

| Component | State |
|-----------|-------|
| `procedural_memory/rule_NNN.json` files (on `main`) | empty (`.gitkeep` only) |
| `procedural_memory/rule_NNN.json` files (on `test13-eval`) | 168 files, **all violate schema** (Example 6.3 shape) |
| `procedural_memory/DSL/` directory | **bootstrapped (iter 3)** — `apply.py` (`DSL_REGISTRY` + `@register` + `apply_DSL`) plus `coloring.py` and `make_grid.py`. Two hand-coded primitives; set is closed. |
| `agent/conditions/` directory | bootstrapped on `test20`: `CONDITION_REGISTRY` + `grid_size_preserved` matcher (iter 1); `consistent_color_mapping` added in iter 8 (P5: 1 → 2); `sequential_recoloring` added in iter 10 (P5: 2 → 3); `recognized_conditions()` applier added in iter 11 (matchers go from inert vocabulary to runnable at runtime; P5 unchanged); first runtime caller wired in iter 12 — `agent/active_agent.py:solve()`'s slow path threads `wm.s1.get("patterns", {})` through `recognized_conditions(...)` and stores the result in `last_solve_info["fired_conditions"]`, so every `episodic_memory/<task_hex>/attempt_NNN/metadata.json` written via `_record_attempt()` now records *which recognition matchers fired* on each attempt — turning P4's growing folder pile into a readable per-attempt history of "what the system thinks it's looking at" without writing any rule file. |
| `agent/conditions/recognized_conditions()` | **implemented (iter 11)** — runtime applier: `recognized_conditions(patterns, params_per_type=None) -> list[str]` runs every matcher in `CONDITION_REGISTRY` against a live `patterns` dict and returns the names whose `match(...)` is strictly `True`, in registry insertion order. Non-dict `patterns` and non-dict `params_per_type` defang to `[]` / `{}`. Does **not** swallow matcher exceptions — a raising matcher is a §4 contract violation, not silent corruption (mirrors F7's spirit). The first runtime entry point that *uses* the registry outside of V2 validation; future iters can wire one call from the solve path into `last_solve_info` (episodic instrumentation) or into a rule constructor (to populate `condition.type` on a discovered rule). |
| `agent/memory.py:RuleSchemaError` | **implemented (iter 2)** — `ValueError` subclass, never caught silently per F7 |
| `agent/memory.py:validate_rule()` | **implemented (iter 2)** — enforces V1–V7; as of iter 3 V3 admits `coloring` and `make_grid` |
| `agent/memory.py:save_rule()` | **implemented (iter 2) + AU-wired (iter 6)** — schema-aware writer producing §1 shape. Accepts an optional `related_rules` kwarg; when non-empty, calls `program.anti_unification.unify(related + [rule])` and substitutes the abstract rule when `is_more_general()`. `NoCommonSkeleton` is caught silently (not a `RuleSchemaError`, F7 not engaged) and the new rule is saved as-is. This is the sole permitted call site for `unify` per `CLAUDE.md §8`. |
| `agent/memory.py:load_related()` | **implemented (iter 7)** — read-side helper for the `save_rule(rule, related_rules=...)` flow. Returns rule dicts from `procedural_memory_root` whose `category` matches the argument and which carry a `{condition, action}` block (shape-checked, not `validate_rule`'d, since V6 always fires on already-saved files). Legacy/malformed entries are silently skipped — surfacing them is the migration tool's job. Read-only; never mutates `procedural_memory/`. |
| `agent/memory.py:save_rule_to_ltm()` (legacy) | still present; emits the pre-test20 shape; sole caller is `agent/active_agent.py`. Migration to `save_rule()` deferred to a later iter |
| `agent/memory.py:migrate_legacy_rules()` | not implemented |
| `agent/episodic.py:write_attempt()` | **implemented (iter 9)** — minimal episodic writer. Lays down `episodic_memory/<task_hex>/attempt_<n>/` with `metadata.json` (task_hex, attempt_index, outcome, created_at, info), an empty `trace.json` placeholder list, and an empty `grids/` placeholder dir — the §3.3 layout that later iters can extend in place once cycle.py instrumentation lands by sidecar (frozen, must not be edited). `info` is deep-copied so the caller cannot mutate the persisted record after-the-fact. Wired into `agent/active_agent.py:solve()` at both return sites (fast-path stored-rule hit + slow-path pipeline) so every `solve()` invocation produces exactly one attempt folder (P4). |
| `program/anti_unification.unify()` | **implemented (iter 5)** — positional anti-unification over `condition.params` and `action.args`; returns `UnifyResult` with deep-copied `abstract_rule`, on-disk trace file, and `substitutions` map; raises `NoCommonSkeleton` on `(condition.type, action.dsl)` mismatch. Wired into `save_rule()` in iter 6. Full contract in `docs/ANTI_UNIFICATION.md`. |
| `tests/test_save_rule.py` | **added (iter 2) + extended (iter 6)** — 14 cases covering V1–V7 + happy path + side-effect-free check + (iter 6) four AU-wiring cases: no-related no-unify, more-general-swap with V5-passing trace, NoCommonSkeleton fallback, identical-inputs no-swap |
| `tests/test_dsl.py` | **added (iter 3)** — 17 cases covering registry contents, `coloring`/`make_grid` happy paths, validation, purity, and `apply_DSL` dispatch |
| `tests/test_unify.py` | **added (iter 5)** — 14 cases covering `NoCommonSkeleton` paths, identical-input no-trace contract, single/multi-position lifting, partial-key disagreement, `min_evidence` selection, `covers` union ordering, alias safety, V5-regex compliance, and trace-id monotonicity |
| `tests/test_load_related.py` | **added (iter 7)** — 11 cases covering category filtering, legacy-shape rejection (no `condition`/`action` block), non-JSON tolerance, non-rule-filename ignore, empty/missing directory, bad-category input, read-only contract (no disk mutation), and an end-to-end smoke that feeds `load_related` output into `unify()` |
| `tests/test_consistent_color_mapping.py` | **added (iter 8)** — 14 dependency-free cases covering registration, the iter-1 matcher non-displacement check, uniform 1:1 mapping, multi-input 1:1 mapping, conflicting outputs, empty / missing `pair_analyses`, non-dict patterns, malformed analysis/group, side-effect-free input contract, determinism across repeats, and an end-to-end agreement check against the patterns shape `_try_color_mapping` consumes |
| `tests/test_episodic.py` | **added (iter 9)** — 15 dependency-free cases covering the `EPISODIC_MEMORY_ROOT` constant matching the checker, three-artifact layout (`metadata.json` + `trace.json` + `grids/`), metadata payload shape, monotonic `attempt_NNN` indexing, recovery from external `attempt_005` mid-stream, ignoring non-`attempt_<int>` siblings, per-task-hex isolation, deep-copy of `info`, trace.json as `[]`, empty `grids/`, malformed-task_hex rejection, empty-outcome rejection, `no_prediction` round-trip, missing-root auto-create, and same-process non-overwrite (`exist_ok=False` on the inner dir keeps overwrites from being silently swallowed) |
| `tests/test_sequential_recoloring.py` | **added (iter 10)** — 20 dependency-free cases covering registration, adjacent-iter matcher non-displacement, ≥3-entry registry assertion (P5), two-pair positive case ordered by `top_row`, positive case where only `top_col` works, single-group-per-pair acceptance, non-contiguous output rejection, neither-axis-orders rejection, mismatched group counts, multi-input / multi-output group rejection, empty `pair_analyses`, pair with zero groups, non-dict patterns, malformed analysis/group, side-effect-free input contract, determinism across repeats, end-to-end agreement against `_try_recolor_sequential`'s patterns shape (positive + position-swap negative), and non-overlap with `consistent_color_mapping` (a non-contiguous functional mapping must not fire `sequential_recoloring`) |
| `tests/test_recognized_conditions.py` | **added (iter 11)** — 18 dependency-free cases covering the applier's import surface, registry-content invariance, all-three-fire on a compatible patterns dict (three distinct input colours so consistent_color_mapping's 1:1 contract holds simultaneously with sequential_recoloring's contiguous-range contract), single-matcher firing (grid_size_preserved alone on no-change pairs; consistent_color_mapping alone on dimension-changed patterns), registry-insertion order preservation, `[]` on empty / non-dict patterns, list-type return contract, `params_per_type` forwarding through a sentinel matcher (positive + missing-entry default + non-dict-entry fallback + non-dict-top-level fallback), side-effect-free contract on both arguments, non-swallowing of matcher exceptions (mirrors F7 spirit), determinism across repeats, registry non-mutation during application, and strict-`is True` (rejecting truthy-but-not-True returns) |

The first session(s) under `PROMPT.md` will be tasked with bringing this
inventory to a consistent state — see `PROMPT.md` for the current mission.

---

## 8. Cross-references

| Topic | Source |
|-------|--------|
| Why `{condition, action}` separation matters | `CLAUDE.md §3.2`, `[[arbor-modules]] §9 결함 #3` in the wiki |
| Anti-unification trace shape | `docs/ANTI_UNIFICATION.md` (to be written) |
| Migration log format | `docs/SESSION_LOG_FORMAT.md` §migration_log (to be written) |
| Validation error class location | `agent/memory.py:RuleSchemaError` |
