# SOAR-ARC Session Log

---
## Iter 6 — 2026-06-11 — branch test30

**Diagnosis**: Iters 3+5 built both halves of the easy000a path but left them
unconnected: the `constant_output` matcher (iter 3) recognises "all example
outputs COMM" and the make_grid/coloring DSL substrate (iter 5) can materialise
a grid, but **nothing consumed the recognition** — `GeneralizeOperator` never
consulted the condition registry, so every constant-output task fell through to
a *coincidental* `color_mapping` misfit and was scored INCORRECT. The single
smallest gap is the missing bridge — ARBOR's `PredictByAllPairCommOp` (slice doc
§3/§4): when `constant_output` fires, emit the common output as a make_grid+
coloring composition and execute it. A second, tightly-coupled half: fast-path
reuse bumped `times_reused` but never grew `covers`, so genuine generalisation
(one rule solving many tasks) stayed invisible to P1 — its own documented intent.

**Change**:
- `agent/dsl_compose.py` (new): `build_constant_output_program(grid)` — a
  general, value-agnostic grid→(make_grid + one coloring-per-colour) decomposer.
  Reads every dimension/colour/coord from the grid; no literal answer baked in
  (slice §9). Rebuilds *any* grid, so it is a module, not a per-task case.
- `agent/active_operators.py` `GeneralizeOperator`: schema-aware fast path
  (CLAUDE.md §5.2) — `recognized_conditions(patterns)`; when `constant_output`
  is among them, activate a `constant_output` rule carrying the DSL program
  (helper `_constant_output_rule`, **not** a `_try_*`). `PredictOperator`:
  `_run_dsl_program` executes a `{dsl,args}` recipe via `apply_DSL` (the §6.2
  dispatch). Neither helper is `_try_*`/`_apply_*` (F2 verified empty).
- `agent/memory.py`: schema fidelity for the new type — `_condition_params`
  `constant_output`→`{}` (recognition is param-free; the recipe is *action*),
  `_dsl_for`→`make_grid`, concept `copy_constant_output`, category
  `constant_transform`. **New `add_task_to_covers()`** (revalidates, never
  swallows RuleSchemaError) wired into `active_agent.py`'s fast path so verified
  reuse grows `covers` (P1). This is also the F8 companion edit.
- `tests/test_constant_output_solve.py` (new): 6 tests — decomposition exactness,
  value-agnosticism, multi-colour, empty/ragged guard, predictor end-to-end, and
  real easy000a. All pass; the four prior suites (constant_output, dsl, episodic,
  rule_schema) still pass.

**Probe before**: 0/3 easy, 0/9 easy_a; 3 rules; P1 1.33, P2 1.33, P4 73, P5 3, P6 652.
**Probe after** : easy000a **and** easy000b now CORRECT via `rule=constant_output`
(the intended Inter-Grid-COMM → make_grid+coloring path, *not* a hand-coded
detector); easy slice 4/16 — the four constant tasks (easy0001/0005/0009/0013)
solved by **reusing** rule_004 (one rule, 5 covered tasks). 5 rules; P1 1.40,
P2 2.00, P4 123, P5 3, P6 710. Value-agnosticism is demonstrated by rule_004
((5,5)=2) vs rule_005 (easy000b's *different* grid) coming from the **same**
module — exactly what the slice's hypothetical easy000a2 was meant to verify.

**Invariants**: forbidden=**none** (checker verdict CLEAN; F2 diff empty, F8
companion = agent/memory.py, F3 untouched). positives=**P1 +0.067, P2 +0.667,
P4 +50** (3 deltas). P3 0 (anti-unification still unbuilt); P5 unchanged; P6
−58 lines (net additions to active_operators.py, permitted under F8 via the
memory.py co-touch).

**Next gap (note for future iter)**: two distinct constant_output rules
(rule_004, rule_005) now share an identical skeleton differing only in the
target grid — this is the textbook invitation for `anti_unification.unify()`
(P3=0, still unwired) to lift them into one `copy_common_output` rule with
`covers`>1, collapsing the denominator. Separately, the stale `color_mapping`
rules (rule_001/002/003) still hold *false* coverage of constant-output tasks
they never actually solve; retiring or superseding them would further lift P1.

---
## Iter 5 — 2026-06-11 — branch test30

**Diagnosis**: The DSL *transformation substrate* CLAUDE.md §6 mandates
(`coloring`/`make_grid` + the `apply_DSL` dispatcher) is **absent** —
`procedural_memory/DSL/` holds only `__pycache__`. Iter 4 built exactly this but
the loop auto-reverted it: the F3 checker's `def`-heuristic whitelist
(`coloring|make_grid|apply_DSL|register|_`) does **not** include the
introspection helper `def static_primitives()`, so a legal commit was
false-flagged as "hand-coded DSL primitive added." This substrate is the single
item both iter-3 and iter-4 next-gap notes cite as blocking the intended
easy0001 solve (the `make_grid`+`coloring` materialisation of the common G1 that
will consume iter-3's `constant_output` recognition). Rebuilding it while fixing
the *root cause* of the false revert is the smallest defensible step — strictly
smaller than wiring predict to consume it (the next, separate half, which would
touch `active_operators.py` under F2/F8 constraints).

**Change**:
- `procedural_memory/DSL/{make_grid,coloring}.py` (new): the two — and only two
  — frozen hand-coded primitives (F3). Pure, deterministic, non-mutating;
  `coloring` clamps OOB and treats colour 13 as a transparent no-op (OPEN-Q
  flagged, not invented).
- `procedural_memory/DSL/apply.py` (new): `apply_DSL` dispatcher + a `register`
  decorator used *only* to declare the two primitives. Exposes the closed set as
  the module constant `STATIC_PRIMITIVES` — **a constant, not the
  `static_primitives()` function iter 4 used** — so the F3 `def`-heuristic can
  never again mistake an introspection helper for a third primitive. This is the
  one substantive difference from the reverted iter-4 version; it fixes the
  false-revert at its source.
- `procedural_memory/DSL/__init__.py` (new): package surface
  (`make_grid`, `coloring`, `apply_DSL`, `STATIC_PRIMITIVES`).
- `tests/test_dsl.py` (new): 6 tests — canvas independence, dim validation,
  paint purity/OOB/transparent, dispatch + frozen-at-two closure, and a
  composition test rebuilding easy0001's constant output. All pass; the
  `constant_output` (3), `rule_schema` (8), and `episodic` (3) suites still pass.

**Probe before**: 0/3 easy, 0/9 easy_a; 3 rules; P1 cov 1.33; P4=61; P5=3; P6=652.
**Probe after** : unchanged (score is not the target; no rule churn). The DSL
substrate now exists and composes the easy0001 output grid in a unit test
(value-agnostic — the 6×6/(5,5)/colour come from data, no literals baked in).

**Invariants**: forbidden=**none** (checker verdict: no F-signal tripped; F3
`def`- and `register`-heuristics both verified empty against the snapshot base).
positives=**NEUTRAL** — no P1–P6 metric measures transformation-DSL existence
(P1 cov, P2 covers, P3 au-frac, P4 episodic, P5 matchers, P6 op-lines all
unchanged). This is the `INVARIANTS.md §3` "scaffolding whose payoff lands in a
later iter" case, not a forbidden hit; a NEUTRAL verdict is not auto-reverted.

**Next gap (note for future iter)**: the substrate now exists but nothing
*consumes* it. The intended easy0001 solve needs predict to, when `constant_output`
holds, emit the common G1 via `apply_DSL("make_grid", …)` + `apply_DSL("coloring", …)`.
That must NOT be a new `_try_constant_output`/`_apply_*` in `GeneralizeOperator`
(F2); the design is the §5.2 fast-path — match `wm.s1["patterns"]` against a
saved rule's `condition.type` (the registered `constant_output` matcher) and
activate a rule whose `action.dsl` resolves to the make_grid+coloring recipe.
Anti-unification (P3=0) remains unbuilt beyond that.

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
## Learning Loop -- 2026-06-11 21:02

- Split: None, Tasks: 3
- Correct: 0 / 3 (0.0%)
- Rules: 3 -> 3 (+0 learned)
- Stored rule hits: 0
- Time: 1s
- Log: logs/learn_20260611_210204.log

---
## Learning Loop -- 2026-06-11 21:02

- Split: None, Tasks: 9
- Correct: 0 / 9 (0.0%)
- Rules: 3 -> 3 (+0 learned)
- Stored rule hits: 0
- Time: 4s
- Log: logs/learn_20260611_210206.log

---
## Learning Loop -- 2026-06-11 21:09

- Split: None, Tasks: 3
- Correct: 0 / 3 (0.0%)
- Rules: 3 -> 3 (+0 learned)
- Stored rule hits: 0
- Time: 1s
- Log: logs/learn_20260611_210908.log

---
## Learning Loop -- 2026-06-11 21:09

- Split: None, Tasks: 9
- Correct: 0 / 9 (0.0%)
- Rules: 3 -> 3 (+0 learned)
- Stored rule hits: 0
- Time: 4s
- Log: logs/learn_20260611_210910.log

---
## Learning Loop -- 2026-06-11 21:16

- Split: None, Tasks: 9
- Correct: 2 / 9 (22.2%)
- Rules: 3 -> 5 (+2 learned)
- Stored rule hits: 0
- Time: 3s
- Log: logs/learn_20260611_211609.log

---
## Learning Loop -- 2026-06-11 21:16

- Split: None, Tasks: 16
- Correct: 4 / 16 (25.0%)
- Rules: 5 -> 5 (+0 learned)
- Stored rule hits: 4
- Time: 9s
- Log: logs/learn_20260611_211621.log

---
## Learning Loop -- 2026-06-11 21:20

- Split: None, Tasks: 9
- Correct: 2 / 9 (22.2%)
- Rules: 3 -> 5 (+2 learned)
- Stored rule hits: 0
- Time: 4s
- Log: logs/learn_20260611_212021.log

---
## Learning Loop -- 2026-06-11 21:20

- Split: None, Tasks: 16
- Correct: 4 / 16 (25.0%)
- Rules: 5 -> 5 (+0 learned)
- Stored rule hits: 4
- Time: 7s
- Log: logs/learn_20260611_212025.log
