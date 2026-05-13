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
