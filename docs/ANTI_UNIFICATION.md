# Anti-Unification

This document specifies the anti-unification module
(`program/anti_unification.py`), which produces abstract rules by finding the
most-specific common skeleton across a set of input rules and lifting positions
where they disagree into generalization variables.

Anti-unification is the **only** mechanism in ARBOR by which new
transformational vocabulary may grow. The hand-coded DSL is closed at two
primitives (`coloring`, `make_grid`); every other transformation must emerge
as a discovered composition produced by `unify()`. See `CLAUDE.md §6.2`,
`CLAUDE.md §8`, and `docs/INVARIANTS.md §1 F3`.

---

## 1. Public API

```python
from program.anti_unification import unify, UnifyResult, NoCommonSkeleton

result = unify(rules)              # raises NoCommonSkeleton on skeleton mismatch
if result.is_more_general():
    abstract_rule = result.abstract_rule
    trace_path    = result.trace_path        # non-null, file exists on disk
```

### 1.1 `unify(rules, *, episodic_memory_root="episodic_memory") -> UnifyResult`

Compute the anti-unification of two or more rules sharing the same structural
skeleton, returning an `UnifyResult` whose `abstract_rule` is the
most-specific common generalization.

Inputs:

- `rules` — a non-empty list of rule dicts. Each rule **must** conform to the
  `docs/RULE_FORMAT.md` §1 schema. Length must be ≥ 2; a single rule has
  nothing to anti-unify against.
- `episodic_memory_root` — root directory under which the trace JSON is
  written. The default `"episodic_memory"` is the canonical location;
  tests may pass a tmpdir.

Output: `UnifyResult` (see §1.2) with:

- `abstract_rule` — a fresh rule dict whose `condition.params` and
  `action.args` have all positions where the inputs disagree lifted to
  generalization variables (`?v1`, `?v2`, …). The skeleton fields
  (`condition.type`, `action.dsl`) are guaranteed identical across inputs
  and copied through. `covers` is the union of all inputs' covers,
  de-duplicated while preserving first-seen order.
- `trace_path` — relative path (with forward slashes) to a freshly-written
  JSON trace under `<episodic_memory_root>/<source_task>/anti_unification/au_NNN.json`,
  where `<source_task>` is the source task of the last input rule (the
  "new_rule" in `CLAUDE.md §8` vocabulary). `None` if the rules are
  identical at the schema level (no substitutions needed) — in which case
  no trace is written, since there is nothing to record.
- `substitutions` — a `{dotted_field_path: variable_name}` map, e.g.
  `{"action.args.color": "?v1"}`, listing exactly which positions were
  lifted.

Raises `NoCommonSkeleton` if:

- `rules` has fewer than 2 entries, OR
- the inputs disagree on `condition.type`, OR
- the inputs disagree on `action.dsl`.

A skeleton mismatch is not bridgeable at this level — bridging primitive
boundaries requires *object-level lifting*, which is a separate concern
(`CLAUDE.md §8` failure modes; wiki `[[object-level-lifting]]`).

### 1.2 `UnifyResult`

```python
@dataclass
class UnifyResult:
    abstract_rule: dict
    trace_path: str | None
    substitutions: dict[str, str]

    def is_more_general(self) -> bool:
        """True iff ≥ 1 position was lifted (substitutions is non-empty).
        When False, the inputs are already structurally identical and the
        caller should merge their `covers` lists rather than save a new
        rule."""
```

### 1.3 `NoCommonSkeleton`

A subclass of `ValueError`. Carries a human-readable message describing the
mismatch (e.g. `"input rules disagree on action.dsl: ['coloring', 'make_grid']"`).

---

## 2. Algorithm

Anti-unification proceeds positionally over the structural fields of the
input rules:

1. **Skeleton check.** All inputs must share the same `condition.type` and
   `action.dsl`. Otherwise `NoCommonSkeleton`.
2. **Field-wise anti-unification.** For each key in `condition.params` and
   each key in `action.args`:
   - If every input has the key with equal values, the abstract rule keeps
     that shared value (deep-copied for container types so no aliasing
     leaks across rules).
   - Otherwise, the position is replaced by a fresh variable `?vN`.
   - A key present in some but not all inputs is treated as a disagreement
     and is replaced by a fresh variable.
3. **`min_evidence`.** The largest input `min_evidence` wins. The abstract
   rule must be at least as conservative as the strictest input.
4. **`covers`.** Union, de-duplicated while preserving first-seen order.
5. **Template fields.** `concept`, `category`, `source_task`, `id` are
   copied from the *last* input rule (the "new_rule" in §8 vocabulary).
   The caller decides whether to keep or reassign `id` before persisting.
6. **`times_reused`.** Reset to 0; the abstract rule is a new artifact.
7. **`created_at`.** ISO 8601 timestamp at unify time.
8. **`anti_unification_trace`.** Path to the trace JSON written in step 9,
   or `None` if no positions were lifted.
9. **Trace JSON.** Written to
   `<episodic_memory_root>/<source_task>/anti_unification/au_NNN.json`,
   where `NNN` is the next sequence number in that directory. The
   abstract rule's `anti_unification_trace` field carries this path
   (with forward slashes so it matches the `docs/RULE_FORMAT.md` §1 V5
   regex on every platform). Skipped entirely when no substitutions were
   produced.

This implementation handles the leaf case — anti-unifying value positions
that compare via `==`. Recursive anti-unification of nested terms
(`coloring(coloring(grid, …), …)` style compositions, term-tree alignment
DP) is **out of scope for this iter**. When the inputs' `action.args`
contain nested containers and the containers compare equal everywhere,
they are preserved; when they differ they are lifted as a single variable.

---

## 3. Trace JSON Shape

The trace file is the *audit log* of one unification. It records which
inputs were combined, what skeleton matched, and which positions were
lifted. The shape is intentionally small — it is a forensic record, not a
re-runnable program.

```json
{
  "input_rules": [
    {"id": 7,  "source_task": "00576224"},
    {"id": 12, "source_task": "007bbfb7"}
  ],
  "skeleton": {
    "condition_type": "grid_size_preserved",
    "action_dsl":     "coloring"
  },
  "substitutions": {
    "action.args.color":    "?v1",
    "action.args.selection": "?v2"
  },
  "var_count":   2,
  "created_at": "2026-05-13T19:00:00.000000"
}
```

Fields:

| Field | Meaning |
|-------|---------|
| `input_rules` | List of `{id, source_task}` for each input rule, in the order passed to `unify()`. |
| `skeleton.condition_type` | The shared `condition.type` of all inputs. |
| `skeleton.action_dsl`     | The shared `action.dsl` of all inputs. |
| `substitutions` | Map from dotted field path to the variable name introduced at that position. Empty maps are not persisted — `is_more_general() == False` skips trace creation entirely. |
| `var_count` | Total number of fresh variables introduced. Equals `len(substitutions)`. |
| `created_at` | ISO 8601 timestamp at unify time. |

The trace file is **immutable** once written. A re-run that produces the
same abstraction creates a new `au_NNN.json` rather than overwriting an
existing one — the sequence number monotonically increases.

---

## 4. Integration Point (forthcoming)

`CLAUDE.md §8` names `agent/memory.py:save_rule()` as the *only* permitted
call site for `unify()`. The wiring has not yet landed; this iter
stands up `unify()` itself. The next iter wires `save_rule()` to:

1. Look up rules in the same `category` as the candidate.
2. If ≥ 1 found, call `unify(related + [new_rule])`.
3. If the result `is_more_general()`, replace `new_rule` with
   `result.abstract_rule` and set `anti_unification_trace = result.trace_path`.
4. Validate the (possibly abstract) rule against the §1 schema (V1–V7 in
   `docs/RULE_FORMAT.md` §3) and write it to disk.

If `unify()` raises `NoCommonSkeleton`, the caller leaves `new_rule`
unchanged and saves it as a source rule.

---

## 5. Cross-references

| Concern | Source |
|---------|--------|
| Why anti-unification is the only growth mechanism | `CLAUDE.md §6.2`, `docs/INVARIANTS.md §1 F3` |
| Call-site contract (`save_rule`) | `CLAUDE.md §8` |
| Trace path regex (`^episodic_memory/.+/anti_unification/.+\.json$`) | `docs/RULE_FORMAT.md §1` (V5) |
| Object-level lifting (when skeleton mismatch is structural) | wiki `[[object-level-lifting]]` |
