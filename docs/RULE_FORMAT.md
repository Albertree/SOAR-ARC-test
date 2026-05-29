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
      "items": { "type": "string", "pattern": "^([0-9a-f]{8}|easy[0-9a-z]+)$" },
      "minItems": 1,
      "uniqueItems": true
    },

    "source_task": {
      "type": "string",
      "pattern": "^([0-9a-f]{8}|easy[0-9a-z]+)$"
    },

    "anti_unification_trace": {
      "oneOf": [
        { "type": "null" },
        { "type": "string", "pattern": "^episodic_memory/.+/anti_unification/.+\\.json$" }
      ]
    },

    "created_at":   { "type": "string", "format": "date-time" },
    "times_reused": { "type": "integer", "minimum": 0 },

    "rule": {
      "description": "Optional internal dispatch payload (e.g. {\"type\": \"copy_common_output\", \"confidence\": 1.0}). Carried *alongside* — never instead of — the canonical {condition, action} pair, and read by agent/memory.py:_rules_equivalent() / the PredictOperator fast path. It is NOT the legacy bug of §6.3: the dead-memory failure mode is a rule that has ONLY `rule` and lacks {condition, action}, not one that has both.",
      "type": "object"
    }
  }
}
```

The schema lives canonically here. A machine-readable copy belongs at
`docs/rule_format.schema.json` once tooling is added.

### 1.1 Live validator scope (reconciliation)

§1 is the **aspirational, canonical** shape. The **enforced** in-process guard
is `agent/memory.py:validate_rule()` (added iter 22), which checks the
*retrievability subset* of §1 — exactly the part whose violation produces the
dead-memory / 168-rule failure mode (§4 of `docs/INVARIANTS.md`, F4):

1. `condition` and `action` are both present, non-empty, and carry a non-empty
   string `condition.type` / `action.dsl`.
2. `condition.type` resolves in `CONDITION_REGISTRY` and `action.dsl` resolves
   in `DSL_REGISTRY` (an unresolvable name is dead memory → rejected).
3. `source_task` (when present) appears in `covers` (V4).

`validate_rule()` deliberately does **not** enforce §1's `additionalProperties:
false`, the `covers`/`source_task` string pattern, or the full `required` key
list. The live system stores two facts §1 must accommodate, not reject:

- The optional internal `rule` dispatch payload (above) sits beside the
  canonical `{condition, action}` pair on every live rule (e.g. `rule_003`).
- Slice-1 uses synthetic task ids (`easy000a`, `easy000a2`) that are not
  8-char ARC hex — hence the broadened `covers`/`source_task` pattern above.

A validator "completed" to enforce §1 *literally* (hex-only ids, no `rule`
key) would reject `rule_003` — the system's only live, working rule — and
break the fast-path equivalence check. Tighten §1 only in lockstep with the
stored representation, never ahead of it.

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
| `rule` | *Optional.* Internal dispatch payload (e.g. `{"type": "copy_common_output", "confidence": 1.0}`) carried beside — never instead of — `{condition, action}`. Read by `_rules_equivalent()` / the PredictOperator fast path. Its presence does **not** make a rule legacy/invalid; its *absence-of-{condition,action}* does (§6.3). |

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
| V7 | No additional top-level keys beyond §1's `properties` (which includes the optional internal `rule` payload — see §1.1) | `RuleSchemaError("unexpected key: <key>")` |

Validation runs **before** the equivalence check used for `covers` extension —
an invalid candidate is never allowed to mutate an existing valid rule.

The live `validate_rule()` enforces V2–V4 (the retrievability subset, §1.1); V1
(full-schema), V5, V6, and V7 are aspirational until a jsonschema dependency is
added. The `rule` payload is **permitted**, not "unexpected" — V7 forbids
*undocumented* keys, not this one.

---

## 4. Condition Type Registry

The set of currently-registered `condition.type` values. Each entry points to a
matcher function returning `bool` given a `patterns` dict (the output of
`extract_pattern` in `agent/active_operators.py`).

| `condition.type` | Matcher module | Params | Status |
|------------------|----------------|--------|--------|
| `all_outputs_comm` | `agent/conditions/all_outputs_comm.py` | `min_evidence` (int, default 1); `required_properties` (optional list of property names, e.g. `["size", "color", "contents"]`) | active — the Slice-1 **deciding** recogniser (Inter-Grid, role==G1). True iff at least `min_evidence` example-output comparison receipts are present AND **every** one is COMM (or, when `required_properties` is given, every named property's `category` entry is COMM). Consumes `patterns["output_grid_comparisons"]` — role-aligned example-G1 `ARCKG.compare()` receipts scheduled by `agent/compare_scheduler.py`. Value-agnostic (SLICE_1_LOOP.md §9): inspects only the COMM/DIFF *type*, never a colour/coordinate value, so it fires identically for easy000a (red) and easy000a2 (green) and cannot hard-code an answer. Fail-closed on a non-list payload or fewer than `min_evidence` well-formed receipts. |
| `inputs_vary` | `agent/conditions/inputs_vary.py` | `min_evidence` (int, default 1); `required_properties` (optional list) | active — the role==G0 contrast counterpart of `all_outputs_comm` (Inter-Grid, role==G0). True iff ≥ `min_evidence` example-input comparison receipts are present AND **every** one is DIFF (or every named `required_properties` entry is DIFF). Consumes `patterns["input_grid_comparisons"]`. Names "the example inputs all differ" — the contrast that justifies reading the answer off the invariant outputs rather than the varying inputs. Value-agnostic; fail-closed on a non-list payload or under-evidence. |
| `intra_pair_grids_differ` | `agent/conditions/intra_pair_grids_differ.py` | `min_evidence` (int, default 1); `required_properties` (optional list) | active — the Intra-Pair (Grid-level) flow-step recogniser (SLICE_1_LOOP.md §3 step ①). True iff ≥ `min_evidence` intra-pair G0↔G1 comparison receipts are present AND **every** one is DIFF. Consumes `patterns["intra_pair_grid_comparisons"]`. Info-poor on its own (does not say what the output should be) but the intended flow traverses it before the deciding Inter-Grid comparison. Value-agnostic; fail-closed on a non-list payload or under-evidence. |
| `pair_grid_count_majority` | `agent/conditions/pair_grid_count_majority.py` | `min_evidence` (int, default 2); `required_properties` (optional list, e.g. `["grid_count"]`) | active — the PAIR-level majority-vote recogniser (Inter-Pair, Pair-level on grid_count, pairwise per P6). True iff ≥ `min_evidence` well-formed pairwise PAIR comparison receipts show **both** consensus and dissent — at least one COMM **and** at least one DIFF. Consumes `patterns["pair_grid_count_comparisons"]`. The comparison-receipt counterpart of `test_output_missing` (same §3 fact read from pairwise verdicts rather than the raw census); neither subsumes the other. Default `min_evidence` is 2 because a consensus *and* a dissent need ≥ 2 comparisons (≥ 3 pairs). Value-agnostic; fail-closed on a non-list payload, under-evidence, or an all-COMM / all-DIFF set. |
| `test_output_missing` | `agent/conditions/test_output_missing.py` | `min_evidence` (int, default 1) | active — the PAIR-level goal-B trigger ("this is a construct-the-output task"). True iff `patterns["pair_grid_counts"]` is a `{"example_counts": [...], "test_counts": [...]}` census of plain ints with ≥ `min_evidence` example pairs, **every** example count == 2 (complete input+output) AND **every** test count == 1 (input only — its output must be constructed). Produced by `agent/compare_scheduler.py:pair_grid_counts()`. Value-agnostic (inspects only structural counts); fail-closed (bool rejected as non-int) on a non-dict census, non-int counts, or under-evidence. |
| `schema_goal_satisfied` | `agent/conditions/schema_goal_satisfied.py` | none (accepts `params` for the uniform `match(patterns, params)` signature; module B grounds each schema leaf at its own per-property evidence level) | active — module B's evolving goal made a live recognition predicate (the wiring half of `agent/goal.py`). Forms the PAIR-level value goal from the grid-count census, evolves it (Refinement → Decomposition) into the schema goal {size, color, contents} (`build_goalstack_from_census`), marks each leaf solved iff the role-aligned Inter-Grid example-output comparison is COMM on that single property (`mark_schema_leaves_by_comparison`), and returns `is_satisfied()`. So "the test output is the common example G1" is recognised *because* the goal of constructing Gx is satisfied property-by-property (SLICE_1_LOOP.md §3 lines 121-126, P3/P4), not by a standalone all-COMM check. Consumes `pair_grid_counts` + `output_grid_comparisons`. Value-agnostic; fail-closed on empty patterns or no deficient test pair. |
| `copy_common_output_applies` | `agent/conditions/copy_common_output_applies.py` | `min_evidence` (int, default 1 — for the PAIR `test_output_missing` half; the GRID half grounds at module B's own per-property evidence) | active — the single Slice-1 copy-common-output recogniser and the self-describing `condition.type` of the stored rule `procedural_memory/rule_003.json`. The conjunction `test_output_missing` (PAIR) ∧ `schema_goal_satisfied` (GRID), named once so discovery (slow-path `GeneralizeOperator`, `agent/active_operators.py:235`) and reuse (fast-path `ActiveSoarAgent._reuse_copy_common_output`) recognise the mechanism through **one** routine rather than re-inlining the conjunction in two modules (SLICE_1_LOOP.md §8 criterion 2 — 같은 종류 작업이 같은 모듈로). Value-agnostic (both sub-matchers read only COMM/DIFF verdicts and structural counts, never a colour/coordinate); fail-closed on empty patterns. |
| `nothing_to_compare` | `agent/conditions/nothing_to_compare.py` | `level` (str, default `"task"`); `min_to_compare` (int, default 2) | active — **consumed by the live descent trigger as of iter 64** (`agent/elaboration_rules.py:NeedsDescentRule` now gates on `descent_warranted` via the `_descent_warranted_here` helper, which ORs this disjunct at the focus level, alongside the `descent-complete`/`comparison-agenda` flags). Module A's *no-goal* descent trigger (the first trigger disjunct, n_at_level==1): true iff the current level has fewer than `min_to_compare` siblings, so no pairwise comparison (P6: 2-at-a-time) — hence no goal — can begin there and the flow must descend (§3 `[TASK level]` step). Consumes `level_sibling_counts` (`agent/compare_scheduler.py:level_sibling_counts()`). Value-agnostic (structural count only); fail-closed on a malformed census or non-int count. |
| `needs_descend` | `agent/conditions/needs_descend.py` | `goal_condition` (str, default `test_output_missing`); `resolving_condition` (str, default `all_outputs_comm`); `goal_params` / `resolving_params` (dicts forwarded to those sub-matchers) | active — consumed by the live descent trigger as of iter 64 via `descent_warranted` (see `nothing_to_compare`); at the pre-comparison trigger point only the sibling census is in hand, so the `nothing_to_compare` disjunct decides the live gate and this goal-vs-resolver disjunct is exercised by the descent itinerary / tests. Module A's goal-present-but-unresolvable descent trigger (the §3 PAIR→GRID descent): true iff a goal-bearing condition holds at this level AND the resolving condition does *not* yet hold, so the resolving evidence must live a level deeper. Self-terminating — once GRID-level comparisons make the resolver fire, it returns False (P1: depth entered strictly by necessity). Value-agnostic; delegates wholly to the two sub-matchers' boolean verdicts. |
| `descent_warranted` | `agent/conditions/descent_warranted.py` | `level` (str, default `"task"`, forwarded to the `nothing_to_compare` disjunct); `nothing_to_compare_params` / `needs_descend_params` (optional dicts forwarded to the disjuncts) | active — consumed by the live descent trigger as of iter 64 (`NeedsDescentRule._descent_warranted_here` calls this matcher at the focus level; see `nothing_to_compare`). Module A's *unified* descent decision: ORs the level-appropriate disjuncts `nothing_to_compare` (TASK: no goal yet) and `needs_descend` (PAIR: goal present but unresolvable here), so one call answers "does this level warrant a descent?" for whichever level the flow is on. Neither fires at GRID (siblings present *and* goal answerable), so descent self-terminates there (P1). Value-agnostic; delegates wholly to the two sub-matchers. |

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
- V1: `condition` and `action` are **absent** — this is the disqualifying
  defect (a rule the fast path cannot look up = dead memory).
- The top-level `rule` key is **not** itself the problem: a valid rule may
  carry `rule` *alongside* `{condition, action}` (see §1.1 and `rule_003`).
  This example is invalid because it has `rule` and *nothing else* to dispatch
  on — not because `rule` is present.

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

> **Reconciliation note (iter 25).** This section was rewritten to reflect the
> live branch `test21`. Its prior content described a *foreign lineage* — branch
> `test20` (iter 37) — whose recognition matchers (`grid_size_preserved`,
> `consistent_color_mapping`, `sequential_recoloring`, `output_color_uniform`,
> `input_color_uniform`, the dimension / group-count quadrant, …), `memory.py`
> functions (`save_rule` / `translate_to_schema` / `next_rule_id` /
> `_persist_pipeline_rule` / `migrate_legacy_rules`), `active_agent.py` helpers
> (`_predict_with_entry` / `_is_identity_rule` / …), and ~20 named test modules
> **do not exist on this branch**. Reading the old table would badly misdescribe
> what is implemented. The removed narrative is recoverable from git history; it
> is not reproduced here because none of it is true of `test21`. This is the
> same spec↔code reconciliation §1.1 applied to the schema, now applied to the
> status table (the gap iters 22–24 flagged).

### 7.1 Cross-branch facts (still true)

| Component | State |
|-----------|-------|
| `procedural_memory/rule_NNN.json` (on `main`) | empty (`.gitkeep` only) |
| `procedural_memory/rule_NNN.json` (on `test13-eval`) | 168 files, **all violate schema** (the §6.3 dead-memory shape — the 168-rule failure mode F4 / INVARIANTS §2 exist to prevent) |
| `procedural_memory/DSL/` | two hand-coded primitives, set closed (F3): `coloring.py`, `make_grid.py`, dispatched by `apply.py` (`DSL_REGISTRY` + `apply_DSL`) |

### 7.2 `test21` live components (verified iter 25; descent / goal / `import program` rows re-verified iter 54)

| Component | State |
|-----------|-------|
| `procedural_memory/rule_*.json` | one live rule: `rule_003.json` — `copy_common_example_output`, `condition.type = all_outputs_comm`, `action.dsl = make_grid`, plus the optional `rule` dispatch payload (§1.1); `covers = [easy000a, easy000a2]`; `times_reused > 0`. The Slice-1 working rule. |
| `agent/conditions/` (10 matchers; P5 = 10) | the Slice-1 recognition vocabulary documented in §4. Five comparison-receipt recognisers: `all_outputs_comm`, `inputs_vary`, `intra_pair_grids_differ`, `pair_grid_count_majority`, `test_output_missing`. Two **live** composites that resolve the answer: `schema_goal_satisfied` (module B's goal as a predicate) and `copy_common_output_applies` (rule_003's self-describing `condition.type`; PAIR `test_output_missing` ∧ GRID `schema_goal_satisfied`, called by the slow-path `GeneralizeOperator` and the fast path). Three module-A descent-trigger libraries: `nothing_to_compare`, `needs_descend`, `descent_warranted` — **consumed by the live descent trigger as of iter 64** (`NeedsDescentRule` now gates on `descent_warranted` via `_descent_warranted_here`, in addition to the `descent-complete`/`comparison-agenda` flags), closing the §4 "registered-but-unconsumed" gap; built library-first per CLAUDE.md §6.3, wired once the answer-preserving gate was proven. `CONDITION_REGISTRY` + `register` decorator in `__init__.py`; matchers auto-loaded on import (`descent_path.py` defines the `slice1_descent_record` helper and does **not** register, so it is not among the 10). |
| `agent/memory.py:RuleSchemaError` | `ValueError` subclass; never swallowed (F7) |
| `agent/memory.py:validate_rule()` | enforces the retrievability subset V2–V4 (§1.1, §3) |
| `agent/memory.py:save_rule_to_ltm()` | schema-aware writer. On an equivalent stored rule it extends `covers` and backfills + re-validates the `{condition, action}` pair (the iter-23 reuse-path guard); on a new rule it builds the §1 entry and validates before disk. `save_rule` is an alias (iter 22). **Anti-unification is NOT wired into this writer on `test21`** (no `unify()` call site) — contrary to the foreign §7's "AU-wired (iter 6)" claim. |
| `agent/memory.py` helpers | `load_all_rules`, `increment_reuse_count`, `load_rules_from_ltm`, `chunk_from_substate`, `reconstruct_via_dsl` (materialises a grid bottom-up through `make_grid` + `coloring`), `_rules_equivalent`, `_build_condition` / `_build_action`, `_infer_concept` / `_infer_category`. No `translate_to_schema` / `next_rule_id` / `load_related` / `migrate_legacy_rules` on this branch. |
| `agent/active_agent.py` | `solve()` = fast path (stored-rule reuse via `_reuse_rule` / `_reuse_copy_common_output`, recognition through the rule's own `condition`) then slow path (full SOAR cycle through `run_cycle`). Helpers: `_record_episode`, `_rule_matches_examples`, `_apply_rule_to_tests`, `_extract_prediction`. |
| `agent/compare_scheduler.py` | modules C + D: `select` / `filter_scope`, util (`pairs_of` / `grids_of` / `role_of`), and the Slice-1 comparison builders (`output_grid_comparisons`, `input_grid_comparisons`, `intra_pair_grid_comparisons`, `pair_grid_count_comparisons`, `pair_grid_counts`) folded into `build_patterns(task)`. |
| `agent/episodic.py:write_episode()` | minimal episodic writer; one `attempt_NNN/` per `solve()` (P4) |
| `program/anti_unification.py` | exposes `anti_unify_pair_programs()` / `anti_unify_terms()` (CLAUDE.md §8 names the entry point generically as `unify()`; the live function names differ). Present but **unwired** on `test21` — `save_rule_to_ltm` has no call site (Slice-1 does not need synthesis — SLICE_1_LOOP.md §9; modules E–J / AU are OUT until Slice 2). NB (corrected iter 54): `import program` **works** — `program/__init__.py` re-exports the four names `anti_unification.py` actually defines (`anti_unify_pair_programs` / `anti_unify_terms` / `program_lines_to_terms` / `terms_to_program_lines`); the iter-25 "re-exports a non-existent `anti_unify`, so `import program` raises" note is stale and was the latent bug a prior iter fixed (regression-guarded by `tests/test_program_package_import.py`, 12/12). |
| `agent/active_operators.py` | pipeline operators; the `_try_*` / `_apply_*` family is retired (P6). **Correction (iter 54): module A is now wired live** — `DescendOperator.effect` runs the §3 TASK→PAIR→GRID descent and writes `descent-complete` to S1, proposed by `agent/rules.py:DescendRule` on the `needs_descent` flag (`agent/elaboration_rules.py:NeedsDescentRule`) and gating `NeedsTargetSelectionRule`, so the level walk is performed by an operator on the real slow-path solve (verified: a from-empty-memory `easy000a2` solve sets `descent-complete=True`, terminal `grid`; `tests/test_live_descent_wiring.py` 7/7). It is answer-preserving for Slice 1 (descent always terminates at GRID, where target selection proceeds unchanged). **Module B** (`agent/goal.py` `GoalStack` + the two evolution rules, Refinement value→action and Decomposition action→schema) is implemented and exercised per-`solve()` in the episode trace (`ActiveSoarAgent._slice1_goal_record`, grounded in comparison evidence per P3/P4); it records the §3 goal basis but does **not** gate operator selection (not required for the answer by SLICE_1_LOOP.md §8's relaxed criteria — the one genuinely-deferred capability). The iter-25 "module A and module B remain stubs / descent not yet wired" claim is stale. |
| `tests/` (28 modules) | matcher suite `test_conditions_*` (one per recogniser, incl. `descent_path` / `descent_warranted` / `needs_descend` / `nothing_to_compare` / `copy_common_output_applies` / `schema_goal_satisfied`); module-A/B wiring `test_live_descent_wiring`, `test_descent_record`, `test_goal`, `test_active_agent_goal_trace`; `test_program_package_import`; pipeline `test_compare_scheduler`, `test_extract_pattern`, `test_flow_trace`, `test_episodic_writer`, `test_episode_bundle_threading`; DSL `test_dsl`, `test_reconstruct_via_dsl`; rule path `test_fast_path_reuse`, `test_slow_path_value_agnostic`, `test_predict_copy_common_output`, `test_validate_rule`, `test_validate_rule_reuse`. |

The current mission lives in `PROMPT.md` / `docs/SLICE_1_LOOP.md`.

---

## 8. Cross-references

| Topic | Source |
|-------|--------|
| Why `{condition, action}` separation matters | `CLAUDE.md §3.2`, `[[arbor-modules]] §9 결함 #3` in the wiki |
| Anti-unification trace shape | `docs/ANTI_UNIFICATION.md` |
| Migration log format | `docs/SESSION_LOG_FORMAT.md` §migration_log (not yet written) |
| Validation error class location | `agent/memory.py:RuleSchemaError` |
