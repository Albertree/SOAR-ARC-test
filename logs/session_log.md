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
