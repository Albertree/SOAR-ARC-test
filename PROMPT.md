# SOAR-ARC — Session Mission

> This file describes the **current session task**. The unchangeable architecture
> lives in `CLAUDE.md`. The current rule schema lives in `docs/RULE_FORMAT.md`.
> Read both before starting.

---

## 1. Mission (one line)

Build the **rule-format validation infrastructure** so that future sessions
can store, load, and migrate procedural-memory rules in the schema defined by
`docs/RULE_FORMAT.md`. No ARC solving in this session — pure infrastructure.

This is the first session of branch `test20`. Future sessions will:
- (next) migrate `test13-eval`'s 168 legacy rules through the infrastructure built here,
- (later) wire anti-unification into `save_rule()`,
- (later) wire episodic-memory writer into the solve loop.

---

## 2. Session Goal (reward function)

Score-maximize is **not** the reward this session — no tasks are solved.

```
SessionReward =  ΔInfrastructure_Coverage         (primary)
              ×  (1 if architecture_invariants_held else 0)
```

- `ΔInfrastructure_Coverage` = fraction of the deliverables in §6 that pass
  their verification (§7).
- `architecture_invariants_held` = no frozen files modified, no `_try_*`
  growth, no schema bypass.

If even one invariant is violated, the session reward is **0** regardless of
how many deliverables work. Roll back via `git revert HEAD` and report in
`logs/session_log.md`.

---

## 3. Allowed Actions (whitelist)

You may **create** the following new artifacts:

| Path | Purpose |
|------|---------|
| `agent/memory.py` (additions only) | `RuleSchemaError`, `save_rule()`, `validate_rule()`, `migrate_legacy_rules()` |
| `agent/conditions/__init__.py`     | `CONDITION_REGISTRY: dict[str, Callable]` + `register()` helper |
| `agent/conditions/_example.py`     | one trivial matcher (e.g. `always_true`) so registry is exercised |
| `procedural_memory/DSL/__init__.py`| `DSL_REGISTRY: dict[str, Callable]` + `register()` helper |
| `procedural_memory/DSL/apply.py`   | `apply_DSL(name, grid, **args)` dispatcher |
| `procedural_memory/DSL/_example.py`| one trivial primitive (e.g. `identity(grid)`) so registry is exercised |
| `tests/__init__.py`                | empty |
| `tests/test_rule_format.py`        | pytest tests covering §7 |
| `docs/MIGRATION.md`                | brief notes on running `migrate_legacy_rules()` |
| `logs/session_log.md`              | append session entry per §8 |

You may **modify** the following existing artifacts:

| Path | Allowed change |
|------|----------------|
| `agent/memory.py` | Mark `save_rule_to_ltm` deprecated (raise `DeprecationWarning`, leave body intact for one cycle). Re-export `save_rule` as the new write path. |
| `requirements.txt` | Add `jsonschema` if used. Add `pytest`. |

---

## 4. Forbidden Actions (blacklist)

**Frozen files** — modifying any of these is an architecture violation that
auto-zeroes the session reward:

- `data/`
- `agent/cycle.py`
- `agent/wm.py`
- `ARCKG/*.py` node classes (`task.py`, `pair.py`, `grid.py`, `object.py`, `pixel.py`)

**Forbidden additions**:

- New `_try_<name>` method in `GeneralizeOperator` or new `_apply_<name>` in
  `PredictOperator`. The `_try_*` / `_apply_*` family is **closed**
  (`CLAUDE.md §5.1`).
- New rule.json files under `procedural_memory/` (this session writes
  *infrastructure*, not data).
- New top-level keys in the rule schema beyond those listed in
  `docs/RULE_FORMAT.md §1`.

**Forbidden patterns**:

- Auto-growing `--limit` or task pool inside any script (`CLAUDE.md`,
  `arbor-prompt-spec` constraint #6). This session has no task pool, but the
  prohibition persists.
- Hiding validation failures behind `try / except` that swallows
  `RuleSchemaError`.
- Adding optional keys with default-fill to make legacy rules pass — the
  legacy shape must be rejected, not silently upgraded inside `save_rule`.
  Upgrade happens only inside `migrate_legacy_rules()`.

---

## 5. CATEGORY Definition

Not applicable this session. Rule categories will be discussed in the next
session when 168 legacy rules are read.

---

## 6. Deliverables (must all be true at session end)

Each item below must be (a) implemented and (b) covered by at least one test
in `tests/test_rule_format.py`. Tests must be runnable via `pytest tests/`.

### D1 — `RuleSchemaError` class
- Located in `agent/memory.py`.
- Subclass of `Exception`.
- Message format: `"<check_id>: <human-readable detail>"` where `check_id` is
  one of `V1`–`V7` from `docs/RULE_FORMAT.md §3`.

### D2 — `validate_rule(rule_dict: dict) -> None`
- Located in `agent/memory.py`.
- Raises `RuleSchemaError` with the appropriate `Vn:` prefix on any of V1–V7.
- Returns `None` on success.
- Uses the registries from §6.D5–D6 to check V2 and V3.

### D3 — `save_rule(rule_dict: dict, root: str = PROCEDURAL_MEMORY_ROOT) -> str`
- Located in `agent/memory.py`.
- Calls `validate_rule()` first.
- On equivalence with an existing rule, extends `covers` (existing
  `_rules_equivalent` may be reused, but only after validation passes).
- Writes a new `rule_NNN.json` only after successful validation.
- Returns the file path of the saved or updated rule.

### D4 — `migrate_legacy_rules(root: str = PROCEDURAL_MEMORY_ROOT) -> dict`
- Located in `agent/memory.py`.
- Scans `root` for files whose top-level shape matches the legacy form
  (presence of `rule` key without `condition`/`action`).
- For each:
  - If a matcher exists in `CONDITION_REGISTRY` whose `params` schema is
    inferrable from `rule.type` + `rule.*` parameters, synthesize the
    `condition` block, lift `rule.*` into `action`, and validate the result.
  - On success, rewrite the file.
  - On failure, leave the file untouched and append a line to
    `logs/migration_log.md`:
    `<filename> | <reason: missing_matcher | unknown_dsl | other>`.
- Returns `{"migrated": int, "skipped": int, "failed_paths": list[str]}`.
- **Never** writes a partially-migrated rule. All-or-nothing per file.

### D5 — `agent/conditions/__init__.py`
- Provides `CONDITION_REGISTRY: dict[str, Callable]` and
  `register(name: str)` decorator.
- Imports `_example.py` so its single matcher (`always_true`) is registered
  on package import.

### D6 — `procedural_memory/DSL/__init__.py` + `apply.py`
- `DSL_REGISTRY: dict[str, Callable]` and `register(name: str)` decorator in
  `__init__.py`.
- `apply.py` exposes `apply_DSL(name, grid, **args) -> grid` which dispatches
  via `DSL_REGISTRY` and raises `KeyError` for unknown names.
- Imports `_example.py` so its single primitive (`identity`) is registered.

### D7 — `tests/test_rule_format.py`
Each of the following must be a named test function. All must pass.

| Test | What it checks |
|------|----------------|
| `test_v1_schema_invalid_shape` | Dict missing `condition` raises `RuleSchemaError("V1: ...")` |
| `test_v2_unknown_condition_type` | `condition.type = "nope"` raises `V2` |
| `test_v3_unknown_dsl` | `action.dsl = "nope"` raises `V3` |
| `test_v4_source_not_in_covers` | `source_task` outside `covers` raises `V4` |
| `test_v5_missing_trace_file` | Non-null `anti_unification_trace` pointing to nonexistent file raises `V5` |
| `test_v6_id_collision` | Saving with an existing `id` raises `V6` |
| `test_v7_extra_key` | Top-level extra key (`"rule": {...}`) raises `V7` |
| `test_valid_source_rule_saves` | Example 6.1 from `docs/RULE_FORMAT.md` saves successfully and round-trips |
| `test_valid_au_rule_saves` | Example 6.2 with a mock trace file saves successfully |
| `test_legacy_rule_rejected` | Example 6.3 fails `validate_rule` (V1 *and* V7) |
| `test_migrate_legacy_partial_fails_safely` | Legacy rule with no matching `condition.type` leaves file untouched, appends to `migration_log.md` |
| `test_dsl_dispatcher_unknown_raises` | `apply_DSL("missing", grid)` raises `KeyError` |
| `test_dsl_dispatcher_known_runs` | `apply_DSL("identity", grid)` returns the input grid unchanged |

---

## 7. Verification Procedure (session end)

Run, in order, from the repo root:

```bash
# 1. Tests pass
pytest tests/ -q                                    # all green, no skips

# 2. Frozen invariants
git diff main -- data/ agent/cycle.py agent/wm.py ARCKG/  | wc -l    # must print 0
git diff main -- agent/active_operators.py | grep -E "^\+\s*def _(try|apply)_"  # must print nothing

# 3. Schema bypass detection
grep -rn "save_rule_to_ltm" agent/ | grep -v "DeprecationWarning"   # only the deprecation shim
```

All three checks must pass for the session reward to be non-zero.

---

## 8. Session Log Entry (must be appended at session end)

Append the following block to `logs/session_log.md`:

```markdown
## Session <N> — <ISO 8601 timestamp> — test20

**Mission**: Rule-format infrastructure (PROMPT.md v1 of branch test20).

**Deliverables**:
- D1 RuleSchemaError: <pass | fail>
- D2 validate_rule: <pass | fail>
- D3 save_rule: <pass | fail>
- D4 migrate_legacy_rules: <pass | fail>
- D5 conditions registry: <pass | fail>
- D6 DSL registry + apply_DSL: <pass | fail>
- D7 test_rule_format.py: <N> / <M> tests passing

**Invariants**:
- Frozen files untouched: <yes | no>
- `_try_*` / `_apply_*` family unchanged: <yes | no>
- No `RuleSchemaError` swallowed: <yes | no>

**Session reward**: <ΔInfrastructure_Coverage> × <invariants_held(0|1)> = <value>

**Notes / blockers**:
<any unresolved issues, design questions, or rule-migration cases that could
 not be handled — these become input to the next Mission>
```

---

## 9. Entry Point

This Mission is **not** run via `run_loop.sh` — the infinite loop is designed
for solve-improve cycles, and this session does no solving. Run it as a single
Claude Code invocation:

```bash
cd ~/Desktop/SOAR-ARC-test
git checkout test20
claude "$(cat PROMPT.md)"
```

(The eventual update to `run_loop.sh` happens after `PROMPT.md` is stable and
becomes per-session-replaceable. See `[[arbor-prompt-spec]] §작성 순서 #5` in
the wiki.)
