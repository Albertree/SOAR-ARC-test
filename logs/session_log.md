# SOAR-ARC Session Log

---
## Iter 1 — 2026-06-11 — branch test30

**Diagnosis**: The probe's own `save_rule_to_ltm` wrote three rules
(`rule_001..003`) in the legacy `{rule:{...}}` shape with **no `condition` /
`action`** — `check_invariants.sh --check` confirmed this *already tripped F4*
("VIOLATION (caller should revert)") before I changed anything, so any commit
would auto-revert. Root cause (per `RULE_FORMAT §7` audit): `validate_rule`,
`RuleSchemaError`, the legacy→schema translator, and the `agent/conditions/`
matcher registry were all MISSING, so nothing enforced the `{condition,action}`
contract on save. This is PROMPT Step 2's "rule saved without a condition key —
save_rule is missing validation"; it is the smallest *durable* gap (deleting the
files alone spins — the writer regenerates them next probe).

**Change**:
- `agent/conditions/{__init__.py,color_mapping.py,recolor_sequential.py}` (new):
  `CONDITION_REGISTRY` + `register()`/`is_registered()`/`recognized_conditions()`
  and two deterministic, side-effect-free matchers. Gives V2 a registry and
  raises P5 0→2 (recognition vocabulary, explicitly allowed; not transformation).
- `agent/memory.py`: added `RuleSchemaError`, `validate_rule()` (V1–V7),
  `translate_to_schema()` (lifts the flat operational payload into
  `{condition,action}`, preserving it verbatim under `action.args`),
  `next_rule_id()`, `migrate_legacy_rules()`, and helpers
  `_operational_view()`/`_ensure_schema()`. Rewired `save_rule_to_ltm` to
  translate+validate before writing (RuleSchemaError propagates — never
  swallowed, F7) and `load_all_rules` to re-expose the operational payload as
  `entry["rule"]` so the predictor/equivalence check work unchanged.
- `procedural_memory/rule_001..003.json`: migrated in place to the schema; all
  pass `validate_rule`. Re-ran the learner (easy_a) end-to-end — no crash,
  dedup intact (Rules 3→3, +0 churn).
- `tests/test_rule_schema.py` (new): 8 passing tests (translate round-trip,
  V2/V3/V4/V7 rejections, save + migrate). `pytest` isn't installed here, so the
  loop's guarded `pytest tests/` collects nothing; the file also runs directly.
- `docs/RULE_FORMAT.md §7`: updated the status table (these rows now RUNS), and
  recorded a **task-id pattern reconciliation** — §1's `^[0-9a-f]{8}$` rejects
  the easy slice's readable ids (`easy000a`), so `validate_rule` accepts
  `^[0-9a-z_]{3,16}$` for now (surfaced, not silently invented).

**Probe before**: 0/3 correct; 3 rules, all legacy-shape (F4 VIOLATION); P5=0.
**Probe after** : 0/3 correct (unchanged — score is not the target); 3 rules,
all schema-valid (F4 clears); P5=2; rule coverage unchanged at 1.33.

**Invariants**: forbidden=none (check verdict CLEAN); positives=P5 +2
(0→2 condition matchers). P1/P2/P3/P4/P6 unchanged.

**Next gap (note for future iter)**: the schema spine exists but nothing *uses*
the condition matchers at solve time — the fast path is still the legacy
`load_all_rules` lookup, and `DescendOperator` / `agent/episodic.py` (P4=0) /
the `coloring`·`make_grid` DSL *code* / anti-unification all remain unbuilt.
The episodic writer (P4) is a small, self-contained next step.

---
## Learning Loop -- 2026-06-11 20:28

- Split: None, Tasks: 3
- Correct: 0 / 3 (0.0%)
- Rules: 0 -> 1 (+1 learned)
- Stored rule hits: 0
- Time: 2s
- Log: logs/learn_20260611_202827.log

---
## Learning Loop -- 2026-06-11 20:28

- Split: None, Tasks: 9
- Correct: 0 / 9 (0.0%)
- Rules: 1 -> 3 (+2 learned)
- Stored rule hits: 0
- Time: 4s
- Log: logs/learn_20260611_202829.log

---
## Learning Loop -- 2026-06-11 20:37

- Split: None, Tasks: 3
- Correct: 0 / 3 (0.0%)
- Rules: 3 -> 3 (+0 learned)
- Stored rule hits: 0
- Time: 1s
- Log: logs/learn_20260611_203706.log
