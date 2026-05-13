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
| *(none yet)* | —              | `procedural_memory/DSL/` to be created in upcoming session |

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

As of the creation of this document (2026-05-13, branch `test20`):

| Component | State |
|-----------|-------|
| `procedural_memory/rule_NNN.json` files (on `main`) | empty (`.gitkeep` only) |
| `procedural_memory/rule_NNN.json` files (on `test13-eval`) | 168 files, **all violate schema** (Example 6.3 shape) |
| `procedural_memory/DSL/` directory | **does not exist** on `main`; to be created |
| `agent/conditions/` directory | bootstrapped on `test20`: `CONDITION_REGISTRY` + `grid_size_preserved` matcher |
| `agent/memory.py:save_rule()` (new validator) | not implemented; existing `save_rule_to_ltm` produces legacy shape |
| `agent/memory.py:migrate_legacy_rules()` | not implemented |
| `program/anti_unification.unify()` | file exists, integration with `save_rule()` not yet wired |

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
