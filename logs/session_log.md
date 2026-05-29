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
