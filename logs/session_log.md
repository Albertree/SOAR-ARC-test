# SOAR-ARC Session Log

---
## Learning Loop -- 2026-05-13 17:30

- Split: None, Tasks: 3
- Correct: 0 / 3 (0.0%)
- Rules: 0 -> 0 (+0 learned)
- Stored rule hits: 0
- Time: 6s
- Log: logs/learn_20260513_173043.log

---
## Iter 1 -- 2026-05-13 -- branch test20

**Diagnosis**: The probe solved 0/3 and saved 0 rules. Root cause is upstream of
solving: `agent/conditions/` does not exist, so there is no recognition
vocabulary the slow path could even attach to a rule's `condition.type`. P5
(distinct condition matchers) is 0 — the foundational scaffold for the
`{condition, action}` schema is absent. Smallest defensible step: stand up the
condition-matcher registry plus one foundational matcher, and leave
`active_operators.py` / `memory.py` untouched.

**Change**:
- `agent/conditions/__init__.py` (new) -- `CONDITION_REGISTRY` dict, `register`
  decorator, auto-import of sibling modules so `@register` runs on import.
- `agent/conditions/grid_size_preserved.py` (new) -- first matcher: returns True
  iff every example pair has matching input/output dimensions. Foundational
  precondition for any same-grid transformation rule.
- `docs/RULE_FORMAT.md` -- §4 condition registry table updated with the new
  entry; §7 implementation status updated.

**Probe before**: score=0/3, rules=0, covers_mean=0.0
**Probe after** : (not re-run -- this iter does not affect solve path)

**Invariants**: forbidden=none, positives=P5: 0 -> 1 (one matcher registered);
P1-P4, P6 unchanged. Manually verified F1-F8 all clean (frozen files
untouched; no `_try_*`/`_apply_*` added; no DSL primitive added; no rule files
saved; no TF_ artifacts; no budget auto-grow; no swallowed RuleSchemaError;
`active_operators.py` not modified).

**Infra note (next iter to address, not a commitment)**: `scripts/check_invariants.sh`
hardcodes `python3`, but on this Windows machine `python3` resolves to the
Microsoft Store stub that prints "Python" and exits 0 without running. The
pre-iter snapshot at `logs/_invariant_snapshot.json` was therefore left empty
(0 bytes) and check mode would fall through to `BASE_HEAD=HEAD~1`. Invariants
this iter were verified manually with raw `git diff` against HEAD. Replacing
`python3` with `python` (or detecting the stub) would unblock automated
checking on this host.

**Next gap (note for future iter)**: `agent/memory.py:save_rule_to_ltm()` still
writes the legacy schema (top-level `rule` field, no `condition`/`action`) --
it would trip F4 the moment any rule actually gets saved. Adding
`RuleSchemaError` plus a real `save_rule()` that emits the §3.2 schema is the
natural next smallest step now that the condition registry exists to validate
`condition.type` against.

---
## Learning Loop -- 2026-05-13 17:35

- Split: None, Tasks: 3
- Correct: 0 / 3 (0.0%)
- Rules: 0 -> 0 (+0 learned)
- Stored rule hits: 0
- Time: 6s
- Log: logs/learn_20260513_173504.log

---
## Iter 2 -- 2026-05-13 -- branch test20

**Diagnosis**: The probe again solved 0/3 and saved 0 rules. Behind that, the
slow path's terminal step -- writing a rule -- still goes through the legacy
`save_rule_to_ltm` which emits the pre-test20 schema (top-level `rule` field,
no `condition`/`action`). The moment any non-identity rule is discovered, that
write trips F4 (rule lacking `condition` key) and would auto-revert. Iter 1
explicitly flagged this as the next gap. Smallest defensible step: stand up the
schema-aware writer (`save_rule`) plus `validate_rule` + `RuleSchemaError` in
`agent/memory.py`, with tests, without rewiring `active_agent.py` (call-site
migration is a separate step).

**Change**:
- `agent/memory.py` -- added `RuleSchemaError(ValueError)`, `validate_rule()`,
  and `save_rule()`. Validator enforces V1–V7 from `docs/RULE_FORMAT.md` §3
  with no external dependencies. V2 checks `agent.conditions.CONDITION_REGISTRY`;
  V3 tries `procedural_memory.DSL.apply.DSL_REGISTRY` and falls through to an
  empty dict (so until the DSL primitives land, every persisted-rule attempt
  correctly fails V3 — correct-by-construction). Legacy `save_rule_to_ltm` and
  all other existing exports left untouched.
- `tests/__init__.py` + `tests/test_save_rule.py` -- new dependency-free test
  runner (10 cases) covering V1–V7, side-effect freedom of `validate_rule`,
  empty-DSL-registry rejection, and a happy-path round-trip that monkeypatches
  in a stub DSL registry without touching any DSL Python file (no F3 trip).
- `docs/RULE_FORMAT.md` §7 -- implementation status table refreshed: schema
  writer marked implemented (iter 2), legacy writer marked still-present, tests
  marked added.

**Probe before**: score=0/3, rules=0, covers_mean=0.0
**Probe after** : (not re-run -- this iter does not affect the solve path)

**Invariants**:
- forbidden = none (manual diff vs HEAD shows F1 = 0 lines; F2/F3/F4/F5/F6 no
  matches; F7 no `pass`/`continue` near any `except RuleSchemaError`; F8 N/A
  since `agent/active_operators.py` untouched).
- positives: P1–P6 all unchanged. No rule file exists yet, so P1/P2/P3 stay at
  zero; `agent/conditions/` registry unchanged so P5 stays at 1; episodic
  writer still unwired so P4 stays at 0; `active_operators.py` not modified so
  P6 unchanged. This is a scaffolding iter — payoff lands when a future iter
  rewires `active_agent.py` from `save_rule_to_ltm` to `save_rule`.
- `tests/test_save_rule.py` runs clean: 10/10 OK locally.

**Infra note (unchanged from iter 1)**: `scripts/check_invariants.sh` still
calls `python3` which on this Windows host resolves to the MS Store stub, so
the check exits with rc=49. Invariants this iter were verified manually with
raw `git diff`. Replacing `python3` → `python` in that script is the
mechanical fix; deferred to its own iter to keep this iter's scope scoped.

**Next gap (note for future iter)**: Two parallel candidates, both genuinely
smallest:
  1. Migrate `agent/active_agent.py`'s import from `save_rule_to_ltm` to
     `save_rule`, supplying the §1 schema fields (condition/action/
     anti_unification_trace/etc.) from the pipeline's discovered rule. This
     activates the new writer. Cannot complete cleanly until V3 has at least
     one DSL primitive to recognise.
  2. Bootstrap `procedural_memory/DSL/` with the two permitted hand-coded
     primitives (`coloring`, `make_grid`) and a `DSL_REGISTRY`/`apply_DSL`
     dispatcher. Once that exists, V3 starts admitting rules and (1) becomes
     unblocked. This is the natural prerequisite of (1).
