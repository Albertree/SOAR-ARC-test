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
| `identity_transformation` | `agent/conditions/identity_transformation.py` | *(none)* | active (iter 13) — true iff `patterns["pair_analyses"]` is non-empty AND every analysis reports `size_match: True` AND zero change groups. Closes the explicit `(TBD)` note in `consistent_color_mapping.py` directing identity cases to a separate matcher rather than misreporting them as degenerate colour mappings. Strictly stricter than `grid_size_preserved` per-pair (it requires both equal dimensions AND zero changes). Mutually exclusive with `consistent_color_mapping` and `sequential_recoloring` (both require non-zero change groups). The recognition counterpart to `GeneralizeOperator`'s fallback identity rule in `agent/active_operators.py`; surfacing the precondition as named vocabulary lets a future anti-unification-produced no-op `coloring` composition declare `condition.type = "identity_transformation"` instead of synthesising a one-off detector. Requires per-pair `size_match: True` rather than the top-level `grid_size_preserved` flag — `_analyze_pair`'s diff iterates only the `min(h, w)` overlap, so a zero-group result with mismatched dimensions is NOT identity and must be rejected. |
| `grid_size_changed` | `agent/conditions/grid_size_changed.py` | *(none)* | active (iter 17) — true iff `patterns["pair_analyses"]` is a non-empty list of well-formed analyses (every entry a dict carrying a Boolean `size_match`) AND at least one analysis has `size_match is False`. The dimensional precondition that complements `grid_size_preserved` — together they partition the dimensional axis of the recognition vocabulary and map onto the two frozen DSL primitives: `grid_size_preserved` precedes `coloring` (modify-in-place), `grid_size_changed` precedes `make_grid` (output is freshly constructed, not derived from the input cell-by-cell). Strictly mutually exclusive with `grid_size_preserved` (which requires every pair's `size_match` to be True) and with `identity_transformation` (which also requires every pair's `size_match` to be True). Orthogonal to `consistent_color_mapping` and `sequential_recoloring` on the colour-content axis — both can co-fire with `grid_size_changed` when overlap-region change groups exhibit a consistent mapping despite dimension differences. Strict `is False` (not `not size_match`) on the `size_match` field, mirroring iter 13's strict-`is True` posture on the symmetric matcher: a missing or non-Boolean `size_match` is *not* a "size changed" signal but an upstream extractor bug, so the matcher fail-closes there rather than defaulting to True. Surfaces the recognition precondition the slow path needs before any future `make_grid`-emitting branch of `GeneralizeOperator` (or anti-unification discovery thereof) lands — recognition vocabulary ahead of rule emission is the opposite of the test13-eval failure mode where rules accreted without preconditions. |
| `output_color_uniform` | `agent/conditions/output_color_uniform.py` | *(none)* | active (iter 18) — true iff `patterns["pair_analyses"]` is a non-empty list, every analysis is a dict, every analysis has at least one change group, every group has exactly one entry in its `output_colors` list, and ALL single output colours observed across all groups in all pairs are bit-identical. Names the recognition precondition for the simplest possible `coloring`-action rule shape: `action = {"dsl": "coloring", "args": {"selection": <selection>, "color": K}}` where `K` is a single integer constant — exactly what the frozen `coloring` primitive's single `color` argument takes, with no polymorphic-args caveat (the iter-16 obstacle that had been gating `translate_to_schema`'s broadening into the colour-mapping branch). A *strict refinement* of `consistent_color_mapping` (iter 8): the iter-8 matcher only requires each input colour to map to *some* single output colour and allows multiple distinct (in, out) pairs; the iter-18 matcher additionally requires the output side to collapse to one constant across ALL groups in ALL pairs. Whenever `output_color_uniform` fires, `consistent_color_mapping` also fires (the constant-output case is still a 1:1 mapping). The converse is not true. Mutually exclusive with `sequential_recoloring` (iter 10) — that matcher requires outputs to form a contiguous integer range with cardinality ≥ 2; uniform-paint has cardinality exactly 1. Mutually exclusive with `identity_transformation` (iter 13) — that matcher requires zero change groups, this one requires at least one. Orthogonal to the dimensional axis (`grid_size_preserved` / `grid_size_changed`) — the matcher inspects change-group output colours, not dimensions; a uniform repaint can co-fire on either dimension. Fail-closed on zero-group pairs (vacuously-true would be wrong: that case is identity), on multi-element `output_colors` lists (per-group cardinality > 1 is not "uniform"), and on cross-pair colour disagreement (each pair painting its own single colour with the colours differing across pairs is NOT a valid uniform-paint generalisation). |
| `input_color_uniform` | `agent/conditions/input_color_uniform.py` | *(none)* | active (iter 19) — input-side dual of `output_color_uniform`. True iff `patterns["pair_analyses"]` is a non-empty list, every analysis is a dict, every analysis has at least one change group, every group has exactly one entry in its `input_colors` list, and ALL single input colours observed across all groups in all pairs are bit-identical. Names the recognition precondition under which the *selection* side of a `coloring`-action rule becomes determinable from the test input alone via a single derived predicate ("wherever the input has colour C"). C is a constant fixed by training; the literal-coord representation that `coloring`'s `selection` arg takes today does not generalise across grids of different sizes, but the recognition precondition itself is iteration-vocabulary-ahead-of-emission — a future iter that lifts `coloring`'s `selection` semantics via anti-unification (or extends the schema with a derived-selection slot) will gate emission on this matcher. Together with `output_color_uniform`, the rule shape "paint every cell of colour C with colour K" is fully determined by two constants (C from this matcher, K from iter-18), forecloses the iter-16 polymorphic-args obstacle, and pins the simplest non-identity `coloring` composition's preconditions to named vocabulary. Mutually exclusive with `identity_transformation` (iter 13) — that matcher requires zero change groups, this one requires at least one (symmetric to iter-18's mutual-exclusion posture). Orthogonal to `output_color_uniform` (independent axes): they CAN co-fire (the simplest uniform-paint case) OR fire independently (input uniform + outputs varying by position, or output uniform + inputs varying). Orthogonal to `sequential_recoloring` (iter 10) — they CAN co-fire when one input colour is recoloured sequentially across positions (the sequence is on the output side; this matcher makes no claim about output cardinality). Independent of `consistent_color_mapping` (iter 8): `input_color_uniform` requires only that the input side collapse to one constant; `consistent_color_mapping` additionally requires every observed input colour to map to a single output colour. When the single input colour C maps to multiple outputs (e.g. by position), `input_color_uniform` fires but `consistent_color_mapping` does NOT — they are NOT in a refinement relation in either direction. Orthogonal to the dimensional axis (`grid_size_preserved` / `grid_size_changed`) — the matcher inspects change-group input colours, not dimensions. Fail-closed on zero-group pairs (vacuously-true would be wrong: that case is identity), on multi-element `input_colors` lists (per-group cardinality > 1 is not "uniform"), and on cross-pair colour disagreement (each pair starting from its own single colour with the colours differing across pairs is NOT a valid uniform-input generalisation). |

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

As of 2026-05-13, branch `test20` (iter 19):

| Component | State |
|-----------|-------|
| `procedural_memory/rule_NNN.json` files (on `main`) | empty (`.gitkeep` only) |
| `procedural_memory/rule_NNN.json` files (on `test13-eval`) | 168 files, **all violate schema** (Example 6.3 shape) |
| `procedural_memory/DSL/` directory | **bootstrapped (iter 3)** — `apply.py` (`DSL_REGISTRY` + `@register` + `apply_DSL`) plus `coloring.py` and `make_grid.py`. Two hand-coded primitives; set is closed. |
| `agent/conditions/` directory | bootstrapped on `test20`: `CONDITION_REGISTRY` + `grid_size_preserved` matcher (iter 1); `consistent_color_mapping` added in iter 8 (P5: 1 → 2); `sequential_recoloring` added in iter 10 (P5: 2 → 3); `recognized_conditions()` applier added in iter 11 (matchers go from inert vocabulary to runnable at runtime; P5 unchanged); first runtime caller wired in iter 12 — `agent/active_agent.py:solve()`'s slow path threads `wm.s1.get("patterns", {})` through `recognized_conditions(...)` and stores the result in `last_solve_info["fired_conditions"]`, so every `episodic_memory/<task_hex>/attempt_NNN/metadata.json` written via `_record_attempt()` now records *which recognition matchers fired* on each attempt — turning P4's growing folder pile into a readable per-attempt history of "what the system thinks it's looking at" without writing any rule file; `identity_transformation` added in iter 13 (P5: 3 → 4) closing the explicit `(TBD)` note in `consistent_color_mapping.py` so an all-pairs-unchanged patterns shape now fires a dedicated named precondition instead of misreporting as a degenerate colour mapping or relying on the dimensional precondition alone; `grid_size_changed` added in iter 17 (P5: 4 → 5) — the dimensional negation of `grid_size_preserved` (strict `is False` on per-pair `size_match`, existential across pairs), partitioning the dimensional axis cleanly so each of the two frozen DSL primitives now has a named recognition precondition (`grid_size_preserved` → `coloring`, `grid_size_changed` → `make_grid`). The seed=42 probe tasks (00576224 / 007bbfb7 / 009d5c81) all produce `size_match=False` per pair, so iter 17 also makes the live probe set fire at least one non-trivial named matcher for the first time — `episodic_memory/<task_hex>/attempt_NNN/metadata.json` written by `_record_attempt()` now carries `fired_conditions: ["grid_size_changed"]` instead of the previously-empty list on these tasks. `output_color_uniform` added in iter 18 (P5: 5 → 6) — names the strict-refinement subset of `consistent_color_mapping` where the output side collapses to a single constant across all groups in all pairs. This is exactly the precondition under which the frozen `coloring` primitive's single-`color` argument is determinable from training data without polymorphic args (the iter-16 obstacle that has been gating `translate_to_schema` from extending beyond identity). Mutually exclusive with `sequential_recoloring` (cardinality 1 vs ≥ 2) and `identity_transformation` (≥ 1 group required vs 0 groups required); strict refinement of `consistent_color_mapping`; orthogonal to the dimensional axis (`grid_size_preserved` / `grid_size_changed`). `input_color_uniform` added in iter 19 (P5: 6 → 7) — the *input-side dual* of iter-18's `output_color_uniform`: true iff every change group's `input_colors` list collapses to one bit-identical entry across all groups in all pairs. Names the recognition precondition under which the *selection* side of a `coloring`-action rule becomes determinable from the test input alone via the derived predicate "wherever the input has colour C". Together iter-18 + iter-19 pin both sides of the simplest non-identity `coloring` rule shape ("paint every cell of colour C with colour K") to named recognition vocabulary, closing the iter-16 polymorphic-args obstacle on both axes. Mutually exclusive with `identity_transformation` (symmetric to iter-18); orthogonal to `output_color_uniform` (they CAN co-fire OR fire independently); orthogonal to `sequential_recoloring` (the output-side sequence is independent of input-side uniformity); independent of `consistent_color_mapping` in BOTH directions (when uniform C maps to multiple outputs by position, `input_color_uniform` fires but `consistent_color_mapping` does NOT — not a refinement relation either way, unlike iter-18's strict refinement); orthogonal to the dimensional axis. The matcher remains pure recognition vocabulary — no emission-side wiring this iter, the rule-emission side waits until anti-unification can lift `coloring`'s `selection` argument's interpretation beyond literal coords. |
| `tests/test_output_color_uniform.py` | **added (iter 18)** — 32 dependency-free cases covering registration, adjacent-iter matcher non-displacement (iters 1 / 8 / 10 / 13 / 17), `>= 6`-entry registry assertion (P5: 5 → 6), callable contract, single-pair / multi-pair / single-group-per-pair / multi-input-collapsing-to-one-output positive cases, rejection on two distinct output colours within a pair, rejection when the per-pair single output colour differs across pairs (each pair painting its own colour is NOT a uniform paint), rejection on zero-change-groups per pair and on mixed (some-pair-zero-some-pair-groups), empty / missing / non-list / non-dict `pair_analyses`, malformed analysis entry, missing / non-list / malformed `groups`, malformed group entry, missing / non-list / empty `output_colors` in a group, multi-element `output_colors` rejection, side-effect-free input contract, determinism across repeats, mutual exclusion with `identity_transformation` (cardinality 0 vs ≥ 1), mutual exclusion with `sequential_recoloring` (cardinality 1 vs ≥ 2), the strict-refinement claim against `consistent_color_mapping` (whenever this fires, the iter-8 matcher fires too on the same patterns dict), orthogonality with `grid_size_changed` (a uniform repaint on dimension-changed pairs co-fires both), end-to-end agreement with the `_analyze_pair` shape, and a strict-Boolean return assertion. |
| `tests/test_input_color_uniform.py` | **added (iter 19)** — 32 dependency-free cases, mirror of iter-18's test surface on the input side. Covers registration, adjacent-iter matcher non-displacement (iters 1 / 8 / 10 / 13 / 17 / 18), `>= 7`-entry registry assertion (P5: 6 → 7), callable contract, single-pair / multi-pair / single-group-per-pair positive cases, the key iter-19 lemma case (one input colour mapping to multiple outputs by position — `input_color_uniform` fires, `consistent_color_mapping` does NOT, which is exactly the precondition that distinguishes input-side uniformity from a 1:1 function), rejection on two distinct input colours within a pair, rejection when the per-pair single input colour differs across pairs (each pair starting from its own colour is NOT uniform-input), rejection on zero-change-groups per pair and on mixed (some-pair-zero-some-pair-groups), empty / missing / non-list / non-dict `pair_analyses`, malformed analysis entry, missing / non-list / malformed `groups`, malformed group entry, missing / non-list / empty `input_colors` in a group, multi-element `input_colors` rejection, side-effect-free input contract, determinism across repeats, mutual exclusion with `identity_transformation` (cardinality 0 vs ≥ 1, symmetric to iter-18), orthogonality with `output_color_uniform` (three cases: both fire / input-uniform-only / output-uniform-only), co-firing with `sequential_recoloring` (one input colour recoloured sequentially across positions — the iter-10 contract is on output-side cardinality and ordering, independent of input-side uniformity), orthogonality with `grid_size_changed` (a uniform-input task on dimension-changed pairs co-fires both), end-to-end agreement with the `_analyze_pair` shape, and a strict-Boolean return assertion. |
| `agent/conditions/recognized_conditions()` | **implemented (iter 11)** — runtime applier: `recognized_conditions(patterns, params_per_type=None) -> list[str]` runs every matcher in `CONDITION_REGISTRY` against a live `patterns` dict and returns the names whose `match(...)` is strictly `True`, in registry insertion order. Non-dict `patterns` and non-dict `params_per_type` defang to `[]` / `{}`. Does **not** swallow matcher exceptions — a raising matcher is a §4 contract violation, not silent corruption (mirrors F7's spirit). The first runtime entry point that *uses* the registry outside of V2 validation; future iters can wire one call from the solve path into `last_solve_info` (episodic instrumentation) or into a rule constructor (to populate `condition.type` on a discovered rule). |
| `agent/memory.py:RuleSchemaError` | **implemented (iter 2)** — `ValueError` subclass, never caught silently per F7 |
| `agent/memory.py:validate_rule()` | **implemented (iter 2)** — enforces V1–V7; as of iter 3 V3 admits `coloring` and `make_grid` |
| `agent/memory.py:save_rule()` | **implemented (iter 2) + AU-wired (iter 6)** — schema-aware writer producing §1 shape. Accepts an optional `related_rules` kwarg; when non-empty, calls `program.anti_unification.unify(related + [rule])` and substitutes the abstract rule when `is_more_general()`. `NoCommonSkeleton` is caught silently (not a `RuleSchemaError`, F7 not engaged) and the new rule is saved as-is. This is the sole permitted call site for `unify` per `CLAUDE.md §8`. |
| `agent/memory.py:load_related()` | **implemented (iter 7)** — read-side helper for the `save_rule(rule, related_rules=...)` flow. Returns rule dicts from `procedural_memory_root` whose `category` matches the argument and which carry a `{condition, action}` block (shape-checked, not `validate_rule`'d, since V6 always fires on already-saved files). Legacy/malformed entries are silently skipped — surfacing them is the migration tool's job. Read-only; never mutates `procedural_memory/`. |
| `agent/memory.py:save_rule_to_ltm()` (legacy) | **caller-decoupled (iter 15)** — function still present in `agent/memory.py` but is no longer invoked by `agent/active_agent.py`. The iter-15 migration replaced its sole call site with `_persist_pipeline_rule()`, which routes exclusively through the schema-aware `save_rule()` writer when `translate_to_schema()` returns a §1 rule and otherwise drops the rule. Kept on disk so a future migration tool (`migrate_legacy_rules`, still unimplemented) can read the legacy shape it once produced; no live caller remains. |
| `agent/memory.py:next_rule_id()` | **implemented (iter 15)** — read-only helper returning the next unused integer id under `procedural_memory_root` (`max(existing_ids) + 1`, default `1`). Picked over `len(files) + 1` so monotonic ids survive deletions, satisfying V6 by construction. Tolerates wider zero-padding (`rule_0042.json`) so a future migration emitting four-digit ids does not silently collide. Sole consumer is `agent/active_agent.py:_persist_pipeline_rule()`. |
| `agent/active_agent.py:_persist_pipeline_rule()` | **implemented (iter 15)** — post-pipeline save dispatch, lifted out of `solve()` so it can be unit-tested without driving the full SOAR cycle. Threads `legacy_rule`, `task_hex`, `patterns` into `translate_to_schema(rule_id=next_rule_id(...))`; on a non-`None` return, calls `save_rule(schema_rule, related_rules=load_related(category, ...), procedural_memory_root=...)`; on `None`, drops the rule (the legacy `save_rule_to_ltm` fallback was removed because its on-disk shape would trip F4 — non-translatable shapes will land once anti-unification produces a `coloring`/`make_grid` abstraction for them). Removes the previous `rule_type != "identity"` guard: identity is now translatable, so it is no longer dropped silently when `identity_transformation` fires on `patterns`. |
| `agent/active_agent.py` fast-path dispatch (`_predict_with_entry`, `_is_identity_rule`, `_entry_rule_type`, `_entry_matches_examples`, `_apply_entry_to_tests`) | **implemented (iter 16)** — closes the read-side blind spot iter-15 surfaced. Pre-iter-16, the fast-path loop in `solve()` did `entry.get("rule", {})` and dispatched the inner legacy dict through `PredictOperator._apply_rule` — a §1 schema entry has NO top-level `rule` key, so `_apply_rule({}, ...)` returned `None` and every saved schema rule was silently dropped. The iter-16 dispatch routes schema entries (those carrying a `{condition, action, ...}` block) through `apply_DSL(action.dsl, ...)` so iter-3's primitive layer is the runtime evaluator; legacy entries continue through `PredictOperator._apply_rule` for backward compatibility. Identity rules are skipped via `_is_identity_rule` across BOTH shapes (legacy `rule.type == "identity"` AND schema `condition.type == "identity_transformation"`) — the pre-iter-16 short-circuit's semantic preserved across the renaming. `_predict_with_entry` catches `(ValueError, KeyError, TypeError)` from `apply_DSL` and returns `None` so an OOB rule (e.g., a saved 5×5 selection applied to a 3×3 task) is treated as "rule does not apply here" rather than crashing the solve — matches the legacy applier's graceful-fail contract; `RuleSchemaError` is not caught (it can only be raised on the save path, F7 inert). `_entry_rule_type` populates `last_solve_info["rule_type"]` with `rule.type` (legacy) OR `condition.type` (schema) depending on shape, keeping the episodic log readable for both. The previous `_rule_matches_examples` / `_apply_rule_to_tests` helpers are RENAMED (not aliased) to their `_entry_*` counterparts; `test_pre_iter_16_helper_names_removed` asserts the old names are gone so a partial future refactor surfaces immediately. Together with iter-15's `_persist_pipeline_rule` this closes the write-side AND read-side wiring: a schema rule lands via `save_rule`, is later loaded by `load_all_rules`, and is re-applied by the fast path — schema rules are now load-bearing at runtime. |
| `agent/memory.py:translate_to_schema()` | **implemented (iter 14)** — pure converter from a legacy pipeline rule (e.g. `{"type": "identity", ...}`) plus `task_hex` plus `patterns` into a §1-compliant rule dict. Bridge between the slow path's legacy shape and `save_rule()`. Currently handles exactly one legacy shape — `{"type": "identity"}` — gated on `recognized_conditions(patterns)` actually firing `identity_transformation` (translator refuses to mint an unsupported precondition). Maps to `action.dsl = "coloring"` with `args = {"selection": [], "color": 0}` — the no-op composition iter-13 named as the only legacy shape whose `action.dsl` reduces to a registered DSL primitive without pair-specific program synthesis. `color_mapping` / `recolor_sequential` shapes return `None` until anti-unification produces a discovered abstraction (iter-13 "Next gap" option 1). Pure: no file I/O, no registry mutation, no caller-input mutation. |
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
| `tests/test_recognized_conditions.py` | **added (iter 11) + extended (iter 13)** — 18 dependency-free cases covering the applier's import surface, registry-content invariance (iter 13: tightened to the 4-name set including `identity_transformation`), all-three-fire on a compatible patterns dict (three distinct input colours so consistent_color_mapping's 1:1 contract holds simultaneously with sequential_recoloring's contiguous-range contract), per-shape matcher firing (iter 13: zero-change patterns now assert BOTH `grid_size_preserved` AND `identity_transformation` fire, layered preconditions rather than competitors; consistent_color_mapping alone on dimension-changed patterns), registry-insertion order preservation, `[]` on empty / non-dict patterns, list-type return contract, `params_per_type` forwarding through a sentinel matcher (positive + missing-entry default + non-dict-entry fallback + non-dict-top-level fallback), side-effect-free contract on both arguments, non-swallowing of matcher exceptions (mirrors F7 spirit), determinism across repeats, registry non-mutation during application, and strict-`is True` (rejecting truthy-but-not-True returns) |
| `tests/test_identity_transformation.py` | **added (iter 13)** — 22 dependency-free cases covering registration, adjacent-iter matcher non-displacement (iters 1 / 8 / 10), `>= 4`-entry registry assertion (P5), callable contract, single-pair and multi-pair positive cases, rejection when any pair has changes, rejection when any pair has `size_match: False` (the overlap-only-diff false positive), strict-`is True` on `size_match` (truthy non-bool rejected), empty / missing `pair_analyses`, non-dict patterns, malformed analysis entries, missing / non-list `groups` field, non-empty groups disqualifying even with `size_match: True`, side-effect-free input contract, determinism across repeats, mutual exclusion with `consistent_color_mapping` and `sequential_recoloring` (both require non-zero groups, so the same all-identity patterns dict that fires this matcher must NOT fire either of them), co-firing with `grid_size_preserved` (layered preconditions, not competitors), and end-to-end agreement with the `ExtractPatternOperator._analyze_pair` zero-change output shape |
| `tests/test_translate_to_schema.py` | **added (iter 14)** — 24 dependency-free cases against the live `CONDITION_REGISTRY` + `DSL_REGISTRY` (no stubs). Covers the identity happy path (translation produces a schema-compliant dict, condition.type maps to `identity_transformation`, action.dsl maps to no-op `coloring` with `args = {"selection": [], "color": 0}`, output passes `validate_rule`), covers/source_task wiring to `task_hex`, `anti_unification_trace = None` for a source rule, `times_reused = 0` initial, `min_evidence` reflects `len(pair_analyses)` with a floor of 1 (verified via the matcher gate on empty input), refusal paths (matcher does not fire, size mismatch, color_mapping and recolor_sequential legacy shapes, non-dict legacy_rule, missing / empty / non-string legacy_type, invalid 8-hex `task_hex`, invalid `rule_id` including bool subclass rejection, non-dict patterns coerced to `{}` then gated by matcher), purity (no file I/O in a tempdir), side-effect freedom on caller inputs (legacy_rule and patterns), determinism across repeats, supplied-`now` vs default UTC-now `created_at`, and concept/category inheritance from `_infer_concept` / `_infer_category` |
| `tests/test_next_rule_id.py` | **added (iter 15)** — 13 dependency-free cases covering the helper backing `_persist_pipeline_rule`'s id assignment: `1` on missing/empty directory, `max + 1` with contiguous ids, gap-tolerance with holes (the V6-by-construction property), ignoring non-rule filenames and subdirectories, ignoring non-integer / zero / negative stems, tolerance of wider zero-padding (`rule_0042.json`), int-not-bool return type, no directory mutation across repeats, determinism, and an end-to-end harmony check that the returned id corresponds to a path `save_rule` would accept (V6 inert) |
| `tests/test_persist_pipeline_rule.py` | **added (iter 15)** — 13 dependency-free cases against the live registries, exercising the dispatch in isolation from the SOAR cycle. Covers helper presence on the class, identity matcher firing → schema rule on disk that re-validates against a sibling tempdir, identity matcher rejecting → no save (the seed=42 probe set's contract — pre-iter-15 these would have been silently dropped, post-iter-15 they are still dropped but now via an explicit gate), empty patterns → no save, color_mapping legacy shape → dropped (not falling back to legacy writer — closes the F4 trap that the `--shuffle --seed 42` probe surfaces via task `e5790162`), recolor_sequential legacy shape → dropped (same F4-trap closure), monotonic id assignment across two saves into the same root, non-dict legacy_rule no-op, typeless legacy_rule → dropped, source-level assertion that the dispatch contains no `except` (mirrors F7 spirit — `save_rule` exceptions propagate), invalid 8-hex `task_hex` → dropped, side-effect freedom on caller inputs (legacy_rule and patterns dicts unchanged), and per-agent-instance `procedural_memory_root` isolation |
| `tests/test_grid_size_changed.py` | **added (iter 17)** — 24 dependency-free cases covering registration, adjacent-iter matcher non-displacement (iters 1 / 8 / 10 / 13), `>= 5`-entry registry assertion (P5: 4 → 5), callable contract, single-pair and multi-pair positive cases, the existential "at least one size-changed pair" semantic (mixed pairs fire), rejection on all-preserved pairs (with and without colour changes — the latter forecloses recolour-style patterns from misfiring this matcher), empty / missing `pair_analyses`, non-dict / non-list `pair_analyses`, malformed analysis entries, missing `size_match`, strict `is False` (truthy `1` / `"yes"` rejected, falsy `None` / `0` / `""` rejected) on both sides of the Boolean — mirroring iter 13's strict `is True` posture on the symmetric matcher, side-effect-free input contract, determinism across repeats, mutual exclusion with `grid_size_preserved` (the two partition the dimensional axis on any non-empty pair_analyses list) and with `identity_transformation` (both require all-True per-pair `size_match`), orthogonality with `consistent_color_mapping` (co-firing on the iter-11 `_patterns_color_mapping_only` fixture where every pair has `size_match=False` but the change groups still form a consistent 1:1 mapping), end-to-end agreement with the `_analyze_pair` zero-group / `size_match=False` shape (the shape the seed=42 probe tasks emit), and a strict-Boolean return assertion to keep the matcher composable with `recognized_conditions`'s `is True` filter |
| `tests/test_fast_path_schema_rule.py` | **added (iter 16)** — 28 dependency-free cases against the live `CONDITION_REGISTRY` + `DSL_REGISTRY` + `save_rule` writer (no stubs). Covers helper-surface assertions (new `_entry_*` / `_predict_with_entry` / `_is_identity_rule` / `_entry_rule_type` methods present; the pre-iter-16 `_rule_matches_examples` / `_apply_rule_to_tests` names removed); `_predict_with_entry` across both shapes (legacy identity returns input copy, legacy color_mapping still dispatches through `PredictOperator`, schema coloring paints the saved selection, schema empty-selection coloring is a no-op, schema `make_grid` omits the input grid, unknown `action.dsl` returns `None`, OOB selection returns `None` not raises, non-dict / `None` input defensive paths, entry-dict purity); `_is_identity_rule` across both shapes (legacy `rule.type == "identity"`, schema `condition.type == "identity_transformation"`, rejection of non-identity rules in both shapes, non-dict input); `_entry_rule_type` across legacy and schema (returns `rule.type` vs `condition.type`, fallback to `"unknown"` for malformed entries); `_entry_matches_examples` + `_apply_entry_to_tests` (schema rule accepts a matching pair, rejects a non-matching pair, legacy regression on a swap-pair task, pair with `None` grid is skipped, multi-test-pair prediction list, returns `None` when a test pair has no input); plus an end-to-end smoke that a non-identity schema rule saved via `save_rule` is consumed by `solve()` (`last_solve_info.method == "stored_rule"`, `times_reused` incremented on disk) — the iter-15 → iter-16 wiring proof, pre-iter-16 this rule would have been silently skipped; and that a saved schema identity rule is skipped by the fast path (not labeled `stored_rule`) so it does not over-predict identity for non-identity tasks |

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
