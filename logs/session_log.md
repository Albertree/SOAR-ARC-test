# SOAR-ARC Session Log

---
## Learning Loop -- 2026-05-29 18:51

- Split: None, Tasks: 2
- Correct: 0 / 2 (0.0%)
- Rules: 2 -> 2 (+0 learned)
- Stored rule hits: 0
- Time: 1s
- Log: logs/learn_20260529_185127.log

---
## Learning Loop -- 2026-05-29 19:01

- Split: None, Tasks: 2
- Correct: 0 / 2 (0.0%)
- Rules: 2 -> 2 (+0 learned)
- Stored rule hits: 0
- Time: 1s
- Log: logs/learn_20260529_190112.log

---
## Iter 1 — 2026-05-29 — branch test21

**Diagnosis**: The loop was hard-blocked: `check_invariants.sh --check` returned
VIOLATION (exit 1, F4) because the two probe-generated rules
(`procedural_memory/rule_001.json`, `rule_002.json`) carry only a bare `rule`
payload and lack the mandatory `{condition, action}` pair (CLAUDE.md §3.2,
RULE_FORMAT.md). The snapshot baseline (P1=1.0) was itself computed over these
non-compliant files, so *any* commit this iter — module D, anything — would have
been reverted. The smallest defensible step is therefore to bring procedural
memory into `{condition, action}` compliance at the source, not to build new
mechanism on top of a blocked loop. (Note: the intended Slice-1 mechanism —
compare example G1s role-aligned, all-COMM, copy the common output — is still
absent; the `color_mapping` path is solving these the wrong way. That is the
next gap, now unblocked.)

**Change**:
- `agent/memory.py`: added `_build_condition()` / `_build_action()` helpers that
  derive the canonical envelope from the internal rule payload (action.dsl is
  always a frozen primitive — `coloring` — since every transformation composes
  to coloring/make_grid, CLAUDE.md §6.1). `save_rule_to_ltm()` now emits
  `condition` + `action` + `anti_unification_trace: null` on new rules, and
  backfills them on equivalent legacy rules. The `rule` payload is retained, so
  `_rules_equivalent()` (and the PredictOperator fast path) keep working — the
  probe stays idempotent (+0 learned, no new files).
- `procedural_memory/rule_001.json`, `rule_002.json`: migrated to add
  `condition` (`consistent_color_mapping`), `action` (`coloring` + mapping
  args), and `anti_unification_trace: null`, retaining the original `rule`
  payload and `covers`.
- Module D (property/util DSL) was scoped but deferred: the F3 checker
  (`F3_DEF_OUT`) auto-reverts *any* public `def` under
  `procedural_memory/DSL/*.py` other than coloring/make_grid — so the slice doc's
  suggested location for D is a trap. D belongs under `agent/` instead. Recorded
  here for the next iter.

**Probe before**: 0/2 correct; rules 2→2; covers mean 1.0; check verdict = VIOLATION (F4).
**Probe after** : 0/2 correct; rules 2→2 (+0 learned, no new files); covers mean 1.0; check verdict = NEUTRAL (no forbidden signal).

**Invariants**: forbidden=none (F4 cleared — was tripping before this iter);
positives=P1..P6 all Δ0 (neutral). The win is structural, not metric: the loop
is unblocked and rule storage now conforms to the canonical schema.

**Next gap (note for future iter)**: Build module D (util `pairs-of/grids-of/
role-of/filter` + property `pair-count/grid-count/size/color/contents`) under
`agent/dsl/` — NOT `procedural_memory/DSL/` (F3 def-trap) — as the foundation the
scope selector (module C) and a value-agnostic PredictByAllPairCommOp need to
replace the wrong `color_mapping` path with the intended G1-COMM-copy mechanism.

---
## Learning Loop -- 2026-05-29 19:03

- Split: None, Tasks: 2
- Correct: 0 / 2 (0.0%)
- Rules: 2 -> 2 (+0 learned)
- Stored rule hits: 0
- Time: 1s
- Log: logs/learn_20260529_190314.log

---
## Iter 2 — 2026-05-29 — branch test21

**Diagnosis**: The probe solves easy000a/a2 via `color_mapping` — the *wrong*
mechanism (it maps 0→2, which paints the whole background, hence INCORRECT).
The intended Slice-1 mechanism (SLICE_1_LOOP §3/§8, raw prose easy000a
paragraph) is value-agnostic: compare all example output grids (G1)
role-aligned, and when {size, color, contents} are all-COMM, copy that common
G1 as the test answer. The system has **no recognition vocabulary** for "all
example outputs are identical" — there is no `agent/conditions/` registry at
all (P5=0). The smallest defensible step toward the intended mechanism is to
stand up that registry (module E recognition side, CLAUDE.md §6.3) plus the
first value-agnostic matcher; wiring it into compare-scheduling + a
PredictByAllPairCommOp is a larger change left for a later iter.

**Change**:
- `agent/conditions/__init__.py` (new): `CONDITION_REGISTRY`, `register`
  decorator, `match()` dispatch, lazy sibling-module loading. This is
  *recognition* vocabulary, which CLAUDE.md §6.3 explicitly permits to grow by
  hand (unlike the frozen transformation DSL).
- `agent/conditions/all_outputs_comm.py` (new): first matcher. Consumes
  ARCKG.compare() receipts between example output grids; returns True iff all
  are COMM. Strictly value-agnostic — only inspects COMM/DIFF *type*, never the
  colour/coordinate values — so it fires identically for easy000a (red) and
  easy000a2 (green) and cannot hard-code an answer (SLICE_1 §9 guardrail).
- `tests/test_conditions_all_outputs_comm.py` (new): 8 tests built from *real*
  compare() receipts on the actual slice grids (incl. value-agnostic a/a2 case
  and an easy000b-style DIFF case). pytest is absent, so the file self-runs.
  8/8 pass.
- No edit to `agent/active_operators.py` (no F8 exposure); no frozen-file edit.

**Probe before**: 0/2 correct; rules 2→2; covers mean 1.0; P5=0.
**Probe after** : 0/2 correct (mechanism not yet wired into solve); rules 2→2;
covers mean 1.0; P5=1.

**Invariants**: forbidden=none; positives=P5 Δ+1 (0→1); others Δ0. Verdict CLEAN.

**Next gap (note for future iter)**: The matcher exists but nothing produces
its input (`output_grid_comparisons`) or acts on its verdict. The next gap is
module C's scope-scheduling — emit role-aligned Inter-Grid (role==G1) example
comparisons into WM — so this matcher can gate a value-agnostic
PredictByAllPairCommOp that copies the common G1, replacing the wrong
`color_mapping` path.

---
## Learning Loop -- 2026-05-29 19:30

- Split: None, Tasks: 2
- Correct: 0 / 2 (0.0%)
- Rules: 2 -> 2 (+0 learned)
- Stored rule hits: 0
- Time: 1s
- Log: logs/learn_20260529_193015.log

---
## Iter 3 — 2026-05-29 — branch test21

**Diagnosis**: Iter 2 added the `all_outputs_comm` recognition matcher but left
it dead — nothing produces its input (`output_grid_comparisons`) and nothing
acts on its verdict (probe still emits the wrong `color_mapping` rule, 0/2).
The smallest defensible step is module C's producer: build the value-agnostic
scope selector + role-aligned Inter-Grid (role==G1) comparison so the matcher
becomes live. This is the slice's P0 priority (C+D) and is exactly iter 2's own
"Next gap" note. Building the *producer* (not the predict step) is the smaller
half — PredictByAllPairCommOp / wiring into the SOAR pipeline is left for later.

**Change**:
- `agent/compare_scheduler.py` (new): module C, Slice-1 scope. Module-D util
  wrappers (`pairs_of`/`grids_of`/`role_of`/`filter_scope`) that *expose* ARCKG
  node structure without recomputing values; a `select(anchor, level, predicate?)`
  scope selector; pairwise (P6) comparison scheduling reusing ARCKG.compare();
  `output_grid_comparisons()` (the easy000a decider), `pair_grid_count_comparisons()`,
  `pair_grid_counts()`, and `build_patterns()` that assembles the matcher input.
  Strictly value-agnostic — only schedules/compares, never reads a colour or
  coordinate value. This gives iter-2's `all_outputs_comm` matcher its producer.
- `agent/conditions/test_output_missing.py` (new matcher): the PAIR-level §3
  goal-B trigger — recognises (value-agnostically, on grid counts only) that
  examples are complete and the test pair's output must be constructed. Distinct
  from `all_outputs_comm` (GRID-level decider); together they name the two
  recognition steps Slice 1 leans on. Fail-closed on malformed/bool counts.
- `tests/test_compare_scheduler.py` (new): 14 tests on *real* ARCKG Pair/Grid
  nodes and real compare(), driving the producer end-to-end into both matchers
  (easy000a COMM-fires, easy000b-style DIFF-rejects, value-agnostic a/b agree).
  Self-runs (pytest absent). 14/14 pass; existing 8/8 still pass.
- No edit to `agent/active_operators.py`; F3 untouched (no DSL register/def —
  module D util lives in `agent/`, not `procedural_memory/DSL/*.py`, which F3's
  def-check would otherwise reject). No frozen-file edit.

NOTE (rule↔invariant tension): SLICE_1_LOOP.md §4/§6 places module D under
`procedural_memory/DSL/{property,util}/`, but INVARIANTS.md F3's def-check
rejects ANY new `def` under `procedural_memory/DSL/*.py` except coloring/
make_grid/apply_DSL. Per CLAUDE.md ("the rule is correct, the task is wrong"),
the util wrappers were placed in `agent/compare_scheduler.py` instead. Flagging
for the human; the slice doc's path for module D conflicts with F3 as written.

**Probe before**: 0/2 correct; rules 2→2; covers mean 1.0; P5=1.
**Probe after** : 0/2 correct (mechanism still not wired into the solve loop);
rules 2→2; covers mean 1.0; P5=2.

**Invariants**: forbidden=none; positives=P5 Δ+1 (1→2); others Δ0. Verdict CLEAN.

**Next gap (note for future iter)**: The recognition chain is now live but the
solve loop still ignores it. Next gap = the value-agnostic PredictByAllPairCommOp
(module K): when `all_outputs_comm` fires, copy the common example G1 to the test
output — replacing the wrong `color_mapping` path. Wiring it touches the SOAR
pipeline (likely active_operators.py → mind F8: pair with a conditions/ or
memory.py companion).

---
## Learning Loop -- 2026-05-29 19:53

- Split: None, Tasks: 2
- Correct: 0 / 2 (0.0%)
- Rules: 2 -> 2 (+0 learned)
- Stored rule hits: 0
- Time: 1s
- Log: logs/learn_20260529_195322.log

---
## Learning Loop -- 2026-05-29 20:01

- Split: None, Tasks: 2
- Correct: 0 / 2 (0.0%)
- Rules: 2 -> 2 (+0 learned)
- Stored rule hits: 0
- Time: 1s
- Log: logs/learn_20260529_200139.log

---
## Learning Loop -- 2026-05-29 20:02

- Split: None, Tasks: 2
- Correct: 2 / 2 (100.0%)
- Rules: 2 -> 3 (+1 learned)
- Stored rule hits: 0
- Time: 1s
- Log: logs/learn_20260529_200233.log

---
## Iter 4 — 2026-05-29 — branch test21

**Diagnosis**: Iters 2-3 built the recognition chain (matcher `all_outputs_comm`
+ producer `compare_scheduler.build_patterns`) but left it dead — the solve loop
still emitted the wrong `color_mapping` rule (0/2, paints the whole background).
The smallest defensible step was to *wire* that chain into the pipeline: a
value-agnostic copy-common-output path (module K / PredictByAllPairCommOp) that,
when the example outputs are all-COMM, copies the common example G1 as the test
answer — exactly the Slice-1 deciding comparison (SLICE_1_LOOP §3). This is
wiring, not new mechanism, and is iter-3's own "Next gap" note.

**Change**:
- `agent/active_operators.py`: `GeneralizeOperator` now recognizes the
  all-outputs-COMM regime *first* (via the `agent/conditions` registry fed by
  `compare_scheduler.build_patterns` — recognition vocabulary, not a hand-coded
  `_try_*`) and emits a value-agnostic `{type: copy_common_output}` rule.
  `PredictOperator` applies it by copying the task's *common example output*
  grid (read from `wm.task` at predict time — no literal in code), guarded by an
  equality re-check so a misfire degrades to no-prediction. New helpers
  `_recognizes_copy_common_output` / `_common_example_output` are NOT in the
  closed `_try_*`/`_apply_*` family (F2 clean).
- `agent/memory.py` (F8 companion + genuine): `copy_common_output` →
  `condition.type = all_outputs_comm`, `action.dsl = make_grid` (the output is a
  freshly *constructed* canvas, not an in-place recolour), and a concept label.
  Two `copy_common_output` rules are equivalent (no stored grid) so the second
  task merges into the first rule's `covers` — one general rule, two tasks.
- `tests/test_predict_copy_common_output.py` (new): 7 tests on real ARCKG nodes
  driving Generalize→Predict end-to-end, asserting the SAME code copies
  easy000a's red and easy000a2's green outputs (value-agnostic) and does NOT
  fire on varying outputs. Self-runs (pytest absent). 7/7 pass; existing 14/14 +
  8/8 still pass.
- No frozen-file edit; no DSL `def`/`register` (F3 clean).

FINDING (test_output_missing is dead on real data): iter-3's PAIR-level matcher
assumes the test pair lacks its output grid, but `ARCManager.load_task` loads
easy tasks *with* the test ground-truth output (test `grid_count == 2`), so
`test_output_missing` never fires on real loaded tasks. I therefore gate the
mechanism on the GRID-level decider `all_outputs_comm` alone (which fires
correctly, COMM 3/3 on {size,color,contents}). The PAIR-level trigger needs
either a representation that hides the test output or a count-asymmetry reframing
— flagged for a future iter.

**Probe before**: 0/2 correct; rules 2→2 (+0); via=color_mapping (wrong path); covers mean 1.0.
**Probe after** : 2/2 correct; rules 2→3 (+1); via=copy_common_output (intended path);
rule_003 covers [easy000a, easy000a2]; covers mean 1.33.

**Invariants**: forbidden=none (F1/F2/F3/F4/F8 all clear; F8 satisfied by the
`agent/memory.py` companion edit). positives=P2 Δ+0.33 (1.0→1.33, the
generalization win — one rule, two tasks). P1 Δ−0.33 (1.0→0.67) is an artifact
of the two stale `color_mapping` rules still on disk (they never match — dead but
harmless); P3/P4/P5 Δ0; P6 +84 lines (the cost of wiring). Verdict CLEAN.

**Next gap (note for future iter)**: Both Slice-1 tasks now solve via the
intended value-agnostic path, but (a) the stale `color_mapping` rule_001/002
could be pruned (would lift P1), (b) fast-path *reuse* of `copy_common_output` is
not yet wired — `_apply_rule` returns None for it (no `wm.task`), so each new
copy-task re-runs the slow path instead of a stored-rule hit; threading example
outputs into the fast path would let `times_reused` climb, and (c)
`test_output_missing` needs reframing against the loaded representation.

---
## Learning Loop -- 2026-05-29 20:04

- Split: None, Tasks: 2
- Correct: 2 / 2 (100.0%)
- Rules: 3 -> 3 (+0 learned)
- Stored rule hits: 0
- Time: 1s
- Log: logs/learn_20260529_200456.log

---
## Learning Loop -- 2026-05-29 20:08

- Split: None, Tasks: 2
- Correct: 2 / 2 (100.0%)
- Rules: 1 -> 1 (+0 learned)
- Stored rule hits: 0
- Time: 1s
- Log: logs/learn_20260529_200816.log

---
## Iter 5 — 2026-05-29T20:08 — branch test21

**Diagnosis**: Both Slice-1 tasks already solve via the intended value-agnostic
`copy_common_output` path (rule_003: condition `all_outputs_comm`, action
`make_grid`, covers [easy000a, easy000a2]). But procedural memory still carried
the two superseded per-task rules from before iter 4: `rule_001`/`rule_002`
(condition `consistent_color_mapping`, hand-coded literal `color_mapping`
e.g. `2→0,0→2,1→0` which paints the whole background — the *wrong* mechanism
diagnosed in iter 2). Each covers exactly one task, and both covered tasks are
already in rule_003's `covers`. They are the in-miniature 168-rule accretion
pattern the architecture exists to prevent (one hand-coded detector per task),
sitting dead in LTM. The smallest defensible step (iter-4 "Next gap" option a) is
to prune them, consolidating knowledge onto the single general rule — exactly
"two rules merge into one" (INVARIANTS §2 P1).

**Change**:
- Deleted `procedural_memory/rule_001.json`, `procedural_memory/rule_002.json`
  (gitignored runtime LTM, like all `rule_*.json`). No coverage lost: rule_003
  already covers both their tasks via the value-agnostic mechanism. No code
  touched — `load_all_rules` globs the directory; nothing references these by
  name.

**Probe before**: 2/2 correct; rules 3 (rule_001 color_mapping, rule_002
color_mapping, rule_003 copy_common_output); via=copy_common_output; P1=0.667,
P2=1.333.
**Probe after** : 2/2 correct; rules 1 (rule_003 only); via=copy_common_output
(unchanged — proves the deleted rules were dead); re-run learn did NOT regenerate
them (slow path emits copy_common_output, which merges into rule_003: 1→1 +0);
P1=2.0, P2=2.0.

**Invariants**: forbidden=none (F1–F8 all clear: no frozen-file edit, no
`_try_*`/`_apply_*`, no DSL `def`/`register`, rule_003 still passes
`validate_rule`, no TF_ under semantic_memory, no budget growth, no swallowed
RuleSchemaError, no active_operators.py edit). positives=P1 Δ+1.333 (0.667→2.0),
P2 Δ+0.667 (1.333→2.0); P3/P4/P5/P6 Δ0. Verdict CLEAN.

**Next gap (note for future iter)**: rule_003's `action.args` is empty `{}` —
the value-agnostic copy is done in `PredictOperator` by reading the common
example output from `wm.task` at predict time, so the rule is not yet
self-contained / fast-path reusable (`times_reused` stays 0, each task re-runs
the slow pipeline). The most glaring remaining gap is fast-path *reuse* of
copy_common_output (would lift P1 numerator via `times_reused`); separately,
`test_output_missing` is still dead because `ARCManager.load_task` loads the
test pair *with* its ground-truth output (grid_count==2), so the §3 PAIR-level
count-asymmetry trigger never fires — a representation-fidelity gap vs principle
P5 ("test has no G1").

---
## Learning Loop -- 2026-05-29 20:11

- Split: None, Tasks: 2
- Correct: 2 / 2 (100.0%)
- Rules: 1 -> 1 (+0 learned)
- Stored rule hits: 0
- Time: 1s
- Log: logs/learn_20260529_201141.log

---
## Learning Loop -- 2026-05-29 20:16

- Split: None, Tasks: 2
- Correct: 2 / 2 (100.0%)
- Rules: 1 -> 1 (+0 learned)
- Stored rule hits: 0
- Time: 1s
- Log: logs/learn_20260529_201642.log

---
## Iter 6 — 2026-05-29T20:16 — branch test21

**Diagnosis**: Both Slice-1 tasks already solve via the intended value-agnostic
`copy_common_output` path (P1/P2 maxed at 2.0 for this 2-task slice; P3 is
out-of-scope for Slice 1 — anti-unification is module H, OUT). But
`ActiveSoarAgent.solve()` writes **no episodic memory at all**: `easy000a` /
`easy000a2` had zero `attempt_NNN/` folders despite passing, and the 3012
on-disk entries are stale local artifacts from a May-13 path the current solve
loop lost. This is exactly INVARIANTS §2 P4 ("episodic_memory/ was empty across
1k runs — every solve() should write one attempt_NNN/ folder") and CLAUDE.md
§3.3. Restoring the writer is the smallest defensible step that moves a positive
signal without touching the frozen cycle, and PROMPT.md §3 explicitly permits it.

**Change**:
- `agent/episodic.py` (new): `write_episode()` + `_next_attempt_index()`. Writes
  one `attempt_NNN/` folder per solve with `metadata.json` (task_hex,
  attempt_index, outcome, created_at, info — matching the existing on-disk
  convention), `trace.json`, and `grids/step_NNN.json`. The frozen `run_cycle`
  exposes only a summary, so `trace.json` records the cycle summary + applied
  rule (no per-phase log, which would require editing the frozen engine) —
  strictly richer than the old empty `[]` traces.
- `agent/active_agent.py`: added `episodic_memory_root` ctor param (default
  `episodic_memory`) and a `_record_episode()` helper; both the fast-path
  (stored-rule hit) and slow-path (pipeline) returns now write exactly one
  episode, capturing test inputs (step_000…) + the submitted prediction (final
  step). Not frozen; no `active_operators.py` / `cycle.py` / `wm.py` edit.
- `tests/test_episodic_writer.py` (new): 22 assertions — artifact presence,
  attempt-index increment, `no_prediction` outcome, and an end-to-end check that
  real `solve()` on both slice tasks leaves one populated episode each.
  Self-runs (pytest absent). 22/22 pass; existing 8/8 + 14/14 + 7/7 still pass.

**Probe before**: 2/2 correct; rules 1→1 (+0); via=copy_common_output; P4=3012;
easy000a/a2 had **no** episodic entries.
**Probe after** : 2/2 correct; rules 1→1 (+0, idempotent); via=copy_common_output;
P4=3014; easy000a/a2 each now have `attempt_001/` with metadata+trace+grids.

**Invariants**: forbidden=none (F1 no frozen edit; F2 no `_try_*`/`_apply_*`;
F3 no DSL `def`/`register`; F4 rule_003 still valid; F5 no TF_ in
semantic_memory; F6 no budget growth; F7 no swallowed RuleSchemaError; F8 inert
— `active_operators.py` unchanged at 684 lines). positives=P4 Δ+2 (3012→3014);
P1/P2/P3/P5/P6 Δ0. Verdict CLEAN.

**Next gap (note for future iter)**: With episodic writing restored, the most
glaring remaining gaps are (a) `test_output_missing` is still dead — the loader
hands the test pair its ground-truth output (grid_count==2), so the §3 PAIR-level
count-asymmetry trigger and principle P5 ("test has no G1") are not honored by
the representation; and (b) the `copy_common_output` rule is not fast-path
reusable (`action.args` empty, prediction reads `wm.task` at predict time, so
`times_reused` stays 0). Neither is anti-unification (Slice-1 OUT).
