# SOAR-ARC Session Log

---
## Iter 4 — 2026-06-11 — branch test30

**Diagnosis**: Iter 3 left the easy000a `constant_output` *recognition* wired
but with nothing to *consume* it, and the slice's intended consumer
(`PredictByAllPairCommOp`) materialises the common output as a `make_grid` +
`coloring` composition — yet that DSL layer did **not exist**: there was no
`procedural_memory/DSL/` directory at all, despite CLAUDE.md §6 describing
`apply_DSL` as the transformation interface. The smallest defensible half of
the consume gap is to first build the two frozen primitives + dispatcher (the
substrate the predict path will compose through); wiring predict to use them is
the deliberately separate, next-smaller half.

**Change**:
- `procedural_memory/DSL/make_grid.py` (new): `make_grid(height,width,color)` —
  fresh independently-rowed canvas; rejects negative / non-int dims.
- `procedural_memory/DSL/coloring.py` (new): `coloring(grid,selection,color)` —
  pure (deep-copies), single-coord or coord-list, clamps out-of-bounds, treats
  colour 13 as a transparent no-op. The "erase-to-background" reading of 13 is
  surfaced as an open question, not silently invented (slice §0.4 / arbor-open-
  questions): slice 1's reconstruction path never uses 13.
- `procedural_memory/DSL/apply.py` (new): `apply_DSL(name,grid,**kwargs)`
  dispatcher + a `_STATIC` registry closed at exactly the two primitives
  (CLAUDE.md §6.2). Unknown names raise (no silent no-op); discovered layer not
  yet wired.
- `procedural_memory/DSL/__init__.py` (new): package exports.
- `tests/test_dsl.py` (new): 6 tests — primitive behaviour, purity, OOB,
  transparent, dispatch + F3 closure (`static_primitives()==[coloring,
  make_grid]`), and a composition test that rebuilds easy000a's constant output
  grid via make_grid+coloring (the exact recipe next iter's predict path uses).
  All pass; constant_output(3)/rule_schema(8)/episodic(3) suites still pass.

**Probe before**: 0/3 easy, 0/9 easy_a; 3 rules; P1 cov 1.33; P5=3; aop 652.
**Probe after** : unchanged (score is not the target; no solver path touched).
DSL layer verified in isolation: make_grid+coloring reconstructs the 6×6
(5,5)=2 output exactly; dispatcher rejects a 3rd primitive name.

**Invariants**: forbidden=none (check verdict NEUTRAL, exit 2 — kept, not
reverted). F3 clean (registry frozen at two; no `@…register` other than the two
names). active_operators.py untouched → no F2/F8 exposure. positives=all Δ0
(no P1–P6 metric measures "DSL substrate now exists" — a known blind spot of
the metric set, not stagnation; this is foundational scaffolding whose payoff
lands next iter, INVARIANTS §3 cause #3). First neutral after 3 positive iters.

**Next gap (note for future iter)**: wire the consumer. `GeneralizeOperator`
should, when `constant_output` fires on `patterns`, emit a value-agnostic
`{"type":"constant_output"}` rule, and `PredictOperator` should materialise the
common example output through `apply_DSL("make_grid")` + `apply_DSL("coloring")`
— making easy000a/easy000b solve the intended way. That edit touches
active_operators.py, so it must co-touch `agent/conditions/` (e.g. a reference-
extraction companion to the matcher) to satisfy F8, and must add no new
`_try_*`/`_apply_*` method (F2).

---
## Iter 3 — 2026-06-11 — branch test30

**Diagnosis**: The comparison scheduler (module C) only schedules **Intra-Pair**
(G0↔G1) comparisons; it never performs the **Inter-Grid, role==G1** comparison
across example pairs (P0.G1↔P1.G1) that the slice doc (§3) names as easy000a's
*decisive* comparison. Because that signal is never computed, the pipeline can
only force every task into a `color_mapping`/`recolor_sequential` interpretation
— structurally unable to recognise "all outputs identical → copy the common
output", the easy000a mechanism. Filling module C's missing Inter-Grid half (the
slice's P0 priority) is the smallest foundational step toward the intended path;
wiring the predict/submit that *uses* the recognition is deliberately the next
(smaller) half.

**Change**:
- `agent/active_operators.py` `SelectTargetOperator.effect`: also schedule the
  Inter-Grid role==G1 comparison, pairwise across consecutive example outputs
  (P6), tagged `type:"inter_output"`. Reuses the existing node_lookup + ARCKG
  `compare()`; results drain before `extract_pattern`
  (`ReadyForPatternExtractionRule` gates on `pending==0`).
- `agent/active_operators.py` `ExtractPatternOperator`: new
  `_summarize_inter_output()` surfaces the COMM/DIFF verdicts from the
  comparison receipts into `patterns["inter_output"]` (P4 — recognition comes
  from a comparison result, never a re-read of the grids).
- `agent/conditions/constant_output.py` (new) + registered in
  `agent/conditions/__init__.py`: value-agnostic matcher firing iff every
  Inter-Grid role==G1 comparison is COMM (no literal colour/coord — slice §9
  guardrail). Raises recognition vocabulary P5 2→3. Co-touch satisfies F8.
- `tests/test_constant_output.py` (new): 3 tests (registration, fire-only-on-
  all-COMM + crash-safety, easy000a end-to-end recognition). All pass; existing
  rule-schema (8) and episodic (3) suites still pass.

**Probe before**: 0/3 easy, 0/9 easy_a; 3 rules; P5=2; coverage 1.33; steps=14.
**Probe after** : 0/3 easy, 0/9 easy_a (unchanged — score is not the target;
0 errors, rules 3→3 no churn); P5=3; coverage 1.33; steps=16. On easy000a the
new Inter-Grid compare returns COMM 3/3 (size·color·contents all match) and
`constant_output` fires; verified value-agnostic (fires on any all-identical
output set, e.g. easy000b/easy0001 which also have constant training outputs;
does not fire when outputs DIFF).

**Invariants**: forbidden=none (check verdict CLEAN); positives=P5 +1 (2→3),
P4 +13 (episodic writer accumulating). P1/P2/P3 unchanged; P6 −52 lines (net
additions to active_operators.py, permitted under F8 via the conditions/
co-touch).

**Next gap (note for future iter)**: recognition now exists but nothing
*consumes* it — `GeneralizeOperator`/`PredictOperator` still only emit
`color_mapping`/`recolor_sequential`. The intended easy000a solve needs a
value-agnostic predict path that, when `constant_output` holds, emits the common
G1 as the test output (the slice's `PredictByAllPairCommOp`, expressible as a
`make_grid`+`coloring` composition over the discovered common grid). The
`coloring`/`make_grid` DSL *code* and anti-unification (P3=0) remain unbuilt.

---
## Iter 2 — 2026-06-11 — branch test30

**Diagnosis**: `episodic_memory/` held only `.gitkeep` → P4=0. Per CLAUDE.md
§3.3 *every* `solve()` (pass or fail) must produce exactly one `attempt_NNN/`
folder; an empty store means the episodic writer was never built — an
architecture violation and ARBOR's third LTM store is dead. This is the
smallest *durable*, self-contained gap and the one iter 1 flagged as "next".
`agent/cycle.py` is frozen and `run_cycle` returns only a run summary, so the
writer must live at the non-frozen `solve()` boundary and record an honest
*summary-level* trace — not fabricated per-cycle entries the frozen cycle never
exposes.

**Change**:
- `agent/episodic.py` (new): `write_attempt()` — writes one `attempt_NNN/`
  folder (`trace.json` + `metadata.json` + `grids/step_NNN.json`) with
  monotonic per-task attempt indexing so repeated solves accumulate (P4).
  Trace is tagged `granularity:"summary"` and self-documents *why* (frozen
  cycle, no per-cycle hook) rather than inventing step data.
- `agent/active_agent.py`: added `episodic_memory_root` ctor param and a
  `_record_episode()` helper called before both `solve()` returns (fast
  stored-rule path + slow pipeline path). Records the observable boundary
  (path, cycle summary, rule fired, test-input + predicted grid snapshots).
  Writer failure is surfaced on stderr, never silently swallowed, and never
  breaks the learning run. No frozen file touched; `active_operators.py`
  untouched (no F8 risk).
- `tests/test_episodic.py` (new): 3 standalone tests — layout contract,
  monotonic accumulation, empty-dir indexing. All pass.

**Probe before**: 0/3 correct; 3 rules; P4=0 (episodic store empty —
architecture violation).
**Probe after** : 0/3 correct (unchanged — score is not the target); 3 rules;
P4=3 after the easy probe (12 attempts on disk after easy + easy_a). Run is
crash-free; `test_rule_schema.py` (8) still passes.

**Invariants**: forbidden=none (check verdict CLEAN); positives=P4 0→3 (+3).
P1/P2/P3/P5/P6 unchanged.

**Next gap (note for future iter)**: the schema spine (iter 1) and the episodic
writer (this iter) now exist, but the condition matchers in `agent/conditions/`
are still unused at solve time — the fast path remains the legacy
`load_all_rules` equality check, never consulting `condition.type`. Wiring the
matcher registry into the generalize/lookup path (so a saved rule's
`condition` actually gates reuse) is the next self-contained step; `coloring`/
`make_grid` DSL *code* and anti-unification (P3=0) remain unbuilt beyond that.

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

---
## Learning Loop -- 2026-06-11 20:40

- Split: None, Tasks: 3
- Correct: 0 / 3 (0.0%)
- Rules: 3 -> 3 (+0 learned)
- Stored rule hits: 0
- Time: 1s
- Log: logs/learn_20260611_204038.log

---
## Learning Loop -- 2026-06-11 20:40

- Split: None, Tasks: 9
- Correct: 0 / 9 (0.0%)
- Rules: 3 -> 3 (+0 learned)
- Stored rule hits: 0
- Time: 3s
- Log: logs/learn_20260611_204040.log

---
## Learning Loop -- 2026-06-11 20:44

- Split: None, Tasks: 3
- Correct: 0 / 3 (0.0%)
- Rules: 3 -> 3 (+0 learned)
- Stored rule hits: 0
- Time: 1s
- Log: logs/learn_20260611_204453.log

---
## Learning Loop -- 2026-06-11 20:45

- Split: None, Tasks: 9
- Correct: 0 / 9 (0.0%)
- Rules: 3 -> 3 (+0 learned)
- Stored rule hits: 0
- Time: 4s
- Log: logs/learn_20260611_204516.log

---
## Learning Loop -- 2026-06-11 20:46

- Split: None, Tasks: 3
- Correct: 0 / 3 (0.0%)
- Rules: 3 -> 3 (+0 learned)
- Stored rule hits: 0
- Time: 1s
- Log: logs/learn_20260611_204612.log

---
## Learning Loop -- 2026-06-11 20:46

- Split: None, Tasks: 9
- Correct: 0 / 9 (0.0%)
- Rules: 3 -> 3 (+0 learned)
- Stored rule hits: 0
- Time: 3s
- Log: logs/learn_20260611_204614.log

---
## Learning Loop -- 2026-06-11 20:47

- Split: None, Tasks: 1
- Correct: 0 / 1 (0.0%)
- Rules: 3 -> 3 (+0 learned)
- Stored rule hits: 0
- Time: 0s
- Log: logs/learn_20260611_204737.log

---
## Learning Loop -- 2026-06-11 20:52

- Split: None, Tasks: 3
- Correct: 0 / 3 (0.0%)
- Rules: 3 -> 3 (+0 learned)
- Stored rule hits: 0
- Time: 1s
- Log: logs/learn_20260611_205216.log

---
## Learning Loop -- 2026-06-11 20:52

- Split: None, Tasks: 9
- Correct: 0 / 9 (0.0%)
- Rules: 3 -> 3 (+0 learned)
- Stored rule hits: 0
- Time: 3s
- Log: logs/learn_20260611_205218.log

---
## Learning Loop -- 2026-06-11 20:54

- Split: None, Tasks: 3
- Correct: 0 / 3 (0.0%)
- Rules: 3 -> 3 (+0 learned)
- Stored rule hits: 0
- Time: 1s
- Log: logs/learn_20260611_205438.log

---
## Learning Loop -- 2026-06-11 20:54

- Split: None, Tasks: 9
- Correct: 0 / 9 (0.0%)
- Rules: 3 -> 3 (+0 learned)
- Stored rule hits: 0
- Time: 3s
- Log: logs/learn_20260611_205440.log
