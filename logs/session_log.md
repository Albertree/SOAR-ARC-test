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

---
## Learning Loop -- 2026-05-13 17:43

- Split: None, Tasks: 3
- Correct: 0 / 3 (0.0%)
- Rules: 0 -> 0 (+0 learned)
- Stored rule hits: 0
- Time: 6s
- Log: logs/learn_20260513_174313.log

---
## Iter 3 -- 2026-05-13 -- branch test20

**Diagnosis**: The probe again solved 0/3 and saved 0 rules — same surface as
iters 1-2. Behind that, iter 2 stood up `save_rule()` + `validate_rule()` with
V3 ("unknown action.dsl") guarding writes, but the DSL primitive registry was
empty (no `procedural_memory/DSL/` package existed), so V3 unconditionally
rejected every rule. Iter 2's "Next gap" called out exactly this prerequisite.
Smallest defensible step: bootstrap the DSL package with the two permitted
hand-coded primitives (`coloring`, `make_grid`) plus the
`DSL_REGISTRY`/`apply_DSL` dispatcher — closed at two, the rest must be
discovered. No touch to `active_operators.py` or `memory.py`.

**Change**:
- `procedural_memory/DSL/__init__.py` (new) -- transitively imports `apply`,
  `coloring`, `make_grid` so registrations fire at first use.
- `procedural_memory/DSL/apply.py` (new) -- `DSL_REGISTRY`, the `register`
  decorator (rejects re-binding to a different callable; idempotent on same
  callable), and `apply_DSL(name, grid=None, **kwargs)` dispatcher with the
  `grid=None` path for grid-producing primitives like `make_grid`.
- `procedural_memory/DSL/coloring.py` (new) -- `coloring(grid, selection, color)`.
  Accepts a single coord or a list of coords; validates color in `0..9 ∪ {13}`
  (the wiki's transparent/erase sentinel); rejects bool-as-int; pure (deep-copies
  rows); raises `ValueError` on OOB or malformed selection.
- `procedural_memory/DSL/make_grid.py` (new) -- `make_grid(height, width, color)`.
  Strict positive-int / color validation; returns a fresh nested list with
  independent rows (no shared references).
- `tests/test_dsl.py` (new) -- 17 dependency-free cases covering: registry holds
  exactly {coloring, make_grid}; coloring single/list coords, transparent 13,
  invalid colors (incl. bool), OOB rejection, malformed-selection rejection,
  empty-selection identity, purity, bad-grid rejection; make_grid happy path,
  row independence, transparent 13, validation of all three args; `apply_DSL`
  dispatch for both primitives plus unknown-name `KeyError`.
- `.gitignore` -- added a re-include exception for `procedural_memory/DSL/` and
  `procedural_memory/DSL/*.py` so the DSL **source** is tracked while the
  learned `rule_NNN.json` data files remain ignored.
- `docs/RULE_FORMAT.md` §5 -- DSL registry table now lists `coloring` and
  `make_grid` with their implementation paths and the explicit closure note.
- `docs/RULE_FORMAT.md` §7 -- implementation status table refreshed: DSL
  package marked bootstrapped (iter 3); V3 note updated to "admits `coloring`
  and `make_grid`"; `tests/test_dsl.py` row added.

**Probe before**: score=0/3, rules=0, covers_mean=0.0
**Probe after** : (not re-run -- this iter does not affect the solve path; it
unlocks V3 so a future iter that calls `save_rule()` for a `coloring`/`make_grid`
action can finally produce a schema-compliant rule file).

**Invariants**:
- forbidden = none. Manually verified each (the `python3` MS Store stub
  prevents `scripts/check_invariants.sh` from running — same blocker as iters
  1-2). F1: 0 lines in frozen-file diff. F2: no new `_try_*`/`_apply_*` def.
  F3: the only `^\+.*@.*register\(` lines in the staged DSL diff are
  `@register("coloring")` and `@register("make_grid")` — both filtered by the
  checker's allow-list regex. (One docstring in `apply.py` initially mentioned
  the literal `@register(...)` shape and tripped the grep; rewritten to
  English-only and re-verified.) F4: no `rule_*.json` files exist. F5: no new
  paths under `semantic_memory/`. F6: no edits to `run_loop.sh` /
  `run_pipeline.sh` / `run_learn.py` / `run_1ktasks.py`. F7: no `try/except
  RuleSchemaError` added or modified. F8: `agent/active_operators.py`
  untouched.
- positives: P1 0.0 → 0.0, P2 0.0 → 0.0, P3 0.0 → 0.0, P4 0 → 0, P5 1 → 1,
  P6 unchanged. **Genuinely neutral on auto-measured signals** — this is
  scaffolding work: V3 was the gate that kept P1/P2/P3 stuck at zero; it now
  admits two primitive names. The next iter that wires a real `save_rule()`
  call site or generalizes a `coloring`-based rule pays out the deltas.
- `tests/test_dsl.py`: 17/17 OK locally. `tests/test_save_rule.py`: 10/10
  still OK (the `test_v3_when_dsl_registry_empty` case still passes because
  its rule uses `action.dsl="stub_for_test"`, which is in neither the real
  registry nor the test stub — V3 fires with the same `unknown action.dsl`
  message).

**Infra note (unchanged from iters 1-2)**: `scripts/check_invariants.sh` calls
`python3`, which on this Windows host is the MS Store stub (prints "Python",
exits 49). Snapshot at `logs/_invariant_snapshot.json` is 0 bytes. Replacing
`python3` → `python` in that script remains the mechanical fix, intentionally
deferred so this iter stays scoped to the DSL bootstrap.

**Next gap (note for future iter)**: With V3 now admitting `coloring` and
`make_grid`, two parallel candidates again share "smallest defensible":
  1. Fix the `python3` → `python` invocation in `scripts/check_invariants.sh`
     so the automated invariant check actually runs on this host. Pure
     plumbing; ~1 line edit; unblocks every future iter's auto-verification.
  2. Wire `program/anti_unification.py:unify()` into
     `agent/memory.py:save_rule()` per CLAUDE.md §8. Currently `unify()` is a
     stub and `save_rule()` never calls it, so P3 (`anti_unification_trace`
     fraction) can never move. The integration is small (≤20 LOC at the call
     site) but it needs a real `unify()` body or a placeholder that emits the
     trace shape from `docs/ANTI_UNIFICATION.md` (which doesn't exist yet).
The infra fix (1) is genuinely smaller and unblocks measurement.

---
## Learning Loop -- 2026-05-13 18:08

- Split: None, Tasks: 3
- Correct: 0 / 3 (0.0%)
- Rules: 0 -> 0 (+0 learned)
- Stored rule hits: 0
- Time: 7s
- Log: logs/learn_20260513_180819.log

---
## Iter 4 -- 2026-05-13 -- branch test20

**Diagnosis**: Iters 1-3 all flagged the same infra blocker: `scripts/check_invariants.sh`
hardcoded `python3`, which on this Windows host is the Microsoft Store stub
(exits rc=49 without executing, garbles the script's exit accounting). The
snapshot file at `logs/_invariant_snapshot.json` was 0 bytes for three iters
straight, and the loop driver kept tagging each commit `[ERROR_49]` because its
post-check verdict was unreachable. With the measurement system silently dead,
no future iter could *honestly* report positive-signal deltas — every Δ would
collapse to the baseline regardless of work done. Iter 3's "Next gap" called
this out explicitly and ranked it ahead of wiring anti-unification, because
the fix is mechanical and unblocks all subsequent verification. Smallest
defensible step: make `scripts/check_invariants.sh` actually run end-to-end
on this host.

**Change**:
- `scripts/check_invariants.sh` -- (a) detect a working Python interpreter into
  `$PYTHON_BIN` (honours caller-pinned override; tries `python3` then `python`;
  validates each candidate with `-c "import sys"` so the MS Store stub is
  rejected by its rc=49). Replaced every hardcoded `python3` invocation with
  `"$PYTHON_BIN"` (4 sites: `compute_metrics` heredoc, BASE_HEAD extraction,
  F4 inner check, post-check positive-delta heredoc).
- `scripts/check_invariants.sh` -- (b) added `encoding="utf-8"` to every
  `open()` in the embedded Python (compute_metrics reads
  `agent/conditions/__init__.py` and `agent/conditions/*.py` which contain
  UTF-8 em-dashes/section-signs; on a Korean-locale Windows host `open()`
  defaults to cp949 and raised `UnicodeDecodeError` silently swallowed by the
  outer `2>/dev/null`). Both compute heredocs plus the F4 inner check now
  open files as UTF-8 explicitly.
- `scripts/check_invariants.sh` -- (c) call `sys.stdout.reconfigure(encoding="utf-8")`
  in both heredocs so the human-readable output (Δ, ↑, ↓, ·, →) renders
  without cp949 mojibake.
- `scripts/check_invariants.sh` -- (d) hardened `--snapshot` mode: propagate
  `compute_metrics`'s exit code instead of unconditionally `exit 0`, and
  refuse to leave a 0-byte snapshot on disk. Post-check heredoc surfaces a
  non-zero exit from the recompute subprocess instead of silently treating an
  empty stdout as `{}`.
- `scripts/check_invariants.sh` -- (e) made the P5 snapshot and recompute
  paths agree on the matcher-count regex. Snapshot previously summed
  `@register(` plus `CONDITION_REGISTRY\[['"]` which double-counted the
  docstring example on line 30 of `agent/conditions/__init__.py`; the
  recompute path used only `@register(`. After the fix, both paths use only
  `@register(`. P5 is now consistently 1 on the current tree (one matcher
  registered: `grid_size_preserved`). An unchanged repo no longer registers
  as P5: -1.

**Probe before**: score=0/3, rules=0, covers_mean=0.0  (loop's iter-4 probe;
identical to iters 1-3 since the slow path is still unwired).
**Probe after** : (not re-run -- this iter does not affect the solve path; it
unblocks the verification *measurement* that runs after every future iter).

**Invariants**:
- forbidden = none. Verified via the now-working checker against base HEAD
  `e65cd282` (iter 3): F1 0-line diff in frozen-file paths; F2 no `+def _try_`
  / `+def _apply_`; F3 untouched DSL Python; F4 no rule files exist; F5 no
  `semantic_memory/.*[Tt][Ff]_` paths added; F6 no edits to `run_loop.sh` /
  `run_pipeline.sh` / `run_learn.py` / `run_1ktasks.py`; F7 no `except
  RuleSchemaError` changes; F8 `agent/active_operators.py` untouched
  (numstat 0/0). The checker itself now runs cleanly end-to-end (exit 0 for
  snapshot, exit 2 for check on unchanged metrics) instead of exiting 49.
- positives: P1 0.0 → 0.0, P2 0.0 → 0.0, P3 0.0 → 0.0, P4 0 → 0, P5 1 → 1,
  P6 600 → 600. **Neutral on auto-measured signals** — this is pure
  measurement infra. The payoff is that every *subsequent* iter's
  positive-delta accounting will now be real instead of stuck-at-zero by a
  broken interpreter. There is no honest P1–P6 delta to claim for fixing the
  ruler; the ruler's correctness is a precondition for future Δ claims, not
  itself a Δ.
- `tests/test_save_rule.py`: 10/10 OK. `tests/test_dsl.py`: 17/17 OK. (Both
  ran via direct `python tests/test_X.py` since pytest is unavailable in this
  env; matches the dependency-free runner iters 2-3 stood up.)

**Infra note (resolved by this iter)**: The `python3` MS Store stub blocker
flagged in iters 1-3 is gone — `scripts/check_invariants.sh --snapshot`
produces a valid JSON snapshot on this host, and `--check` against an
unchanged-state baseline exits 2 (NEUTRAL) cleanly.

**Next gap (note for future iter)**: With measurement unblocked, the next
smallest-defensible step is to wire `program/anti_unification.py:unify()`
into `agent/memory.py:save_rule()` per CLAUDE.md §8. `unify()` is currently
a stub and `save_rule()` never calls it, so P3 (`anti_unification_trace`
fraction) is structurally pinned at 0 even when rules exist. The integration
itself is small (≤20 LOC at the call site) but needs either a real `unify()`
body or a minimal placeholder that emits the trace shape documented in
(still-to-be-written) `docs/ANTI_UNIFICATION.md`. Parallel candidate of
similar size: migrate `agent/active_agent.py`'s import from
`save_rule_to_ltm` to `save_rule` so the schema-aware writer actually fires
on the solve path — but that one has more surface area in the call site,
making the anti-unification wiring slightly smaller.

---
## Learning Loop -- 2026-05-13 18:15

- Split: None, Tasks: 3
- Correct: 0 / 3 (0.0%)
- Rules: 0 -> 0 (+0 learned)
- Stored rule hits: 0
- Time: 7s
- Log: logs/learn_20260513_181454.log

---
## Iter 5 -- 2026-05-13 -- branch test20

**Diagnosis**: Probe is 0/3, rules=0 — same surface as iters 1-4 because the
slow path's *generalization* step is still wholly absent. `program/anti_unification.py`
on this branch holds only stale stubs of an older API (`anti_unify_pair_programs`,
`anti_unify_terms`, …) that all `pass`, and `program/__init__.py` has a
latent broken import (`from program.anti_unification import anti_unify` — that
name doesn't exist, so the moment anything tries `import program` it
`ImportError`s; verified locally). CLAUDE.md §8 names a completely different
public API (`unify()` returning `UnifyResult | NoCommonSkeleton`) that no code
currently provides. Iter 4's "Next gap" called this out as the next smallest
defensible step. Iter 5 stands up the §8 API itself with documentation and
tests; the actual wiring into `save_rule()` is the natural follow-up.

**Change**:
- `program/anti_unification.py` -- full rewrite. New public surface: `unify(rules,
  *, episodic_memory_root="episodic_memory")` returning `UnifyResult`;
  `NoCommonSkeleton(ValueError)`. Skeleton check on `(condition.type,
  action.dsl)`; positional anti-unification over `condition.params` and
  `action.args` with fresh `?vN` variables for disagreements; `min_evidence`
  takes the strictest input; `covers` union preserves first-seen order;
  abstract_rule's container fields are JSON-deep-copied so callers cannot
  alias inputs through it. When `≥ 1` position is lifted, writes a trace
  JSON to `<root>/<source_task>/anti_unification/au_NNN.json` (forward-slash
  path normalisation so V5's regex matches on Windows too) and sets the
  abstract rule's `anti_unification_trace` to that path. When identical,
  no trace is written and `is_more_general()` returns False. Stub functions
  removed (they implemented an incompatible older API and were unused — Grep
  confirmed: only `program/__init__.py` itself referenced any of them).
- `program/__init__.py` -- replaced the broken `from program.anti_unification
  import anti_unify` with `from program.anti_unification import
  NoCommonSkeleton, UnifyResult, unify`. `__all__` updated. `from program
  import unify` now works.
- `docs/ANTI_UNIFICATION.md` (new) -- specifies the §1 public API, §2
  algorithm steps, §3 trace JSON shape with field semantics table, §4 the
  forthcoming `save_rule()` integration contract, §5 cross-refs. Trace
  immutability and sequence-number monotonicity called out explicitly.
- `tests/test_unify.py` (new, dependency-free runner like the other
  `tests/test_*.py`) -- 14 cases: `NoCommonSkeleton` on <2 inputs, non-list,
  condition.type mismatch, action.dsl mismatch; identical rules produce no
  trace and no substitutions but still merge covers; single-position lifting;
  two-position lifting gets two distinct variables; three-rule partial
  agreement; `min_evidence` strictest-wins; covers union dedup with
  first-seen ordering; key present in some-not-all inputs is lifted; abstract
  rule does not alias inputs (mutating the shared `selection` list via
  abstract_rule must not leak back); V5-regex compliance when the canonical
  `episodic_memory/` root is used; trace sequence number monotonically
  increments within the same destination directory.
- `docs/RULE_FORMAT.md` §7 -- implementation-status row for `unify()`
  flipped from "stub only" to "implemented (iter 5)" with a one-line
  contract pointer to `docs/ANTI_UNIFICATION.md`; `tests/test_unify.py`
  row added.

**Probe before**: score=0/3, rules=0, covers_mean=0.0
**Probe after** : (not re-run -- this iter does not affect the solve path; the
unify primitive is in place but `save_rule()` does not call it yet, so the
slow path's discovered rules still flow through the legacy writer. Wiring
that is iter 6's territory.)

**Invariants** (checker run end-to-end via fixed `scripts/check_invariants.sh`
against base HEAD `0dc497b1` — iter 4):
- forbidden = none. F1: 0-line diff in frozen-file paths (`data/`,
  `agent/cycle.py`, `agent/wm.py`, `ARCKG/{task,pair,grid,object,pixel}.py`).
  F2: no `+def _try_` / `+def _apply_` in `agent/active_operators.py`. F3:
  `procedural_memory/DSL/*.py` untouched. F4: no `rule_*.json` files exist.
  F5: no `semantic_memory/.*[Tt][Ff]_` paths added. F6: no edits to
  `run_loop.sh` / `run_pipeline.sh` / `run_learn.py` / `run_1ktasks.py`. F7:
  no `except RuleSchemaError` lines added or modified. F8: `agent/active_operators.py`
  numstat 0/0 (untouched), so the "grew without companion" clause cannot fire.
- positives: P1 0.0 → 0.0, P2 0.0 → 0.0, P3 0.0 → 0.0, P4 0 → 0, P5 1 → 1,
  P6 600 → 600. **Neutral on auto-measured signals** — checker exits 2 as
  expected. This is scaffolding: P3 is structurally pinned at 0/0 until at
  least one rule exists, and rule existence requires the (next-iter) wiring
  of `save_rule()` through `unify()`. The payoff lands in iter 6.
- All three test suites pass on this host: `tests/test_unify.py` 14/14,
  `tests/test_save_rule.py` 10/10, `tests/test_dsl.py` 17/17. The
  `program` package now imports cleanly (`from program import unify,
  UnifyResult, NoCommonSkeleton` — previously raised `ImportError` due to
  the stale `anti_unify` reference).

**Next gap (note for future iter)**: Wire `program.anti_unification.unify()`
into `agent/memory.py:save_rule()` per CLAUDE.md §8. The required call-site
logic is now small: extend `save_rule()` with an optional `related_rules`
parameter; when non-empty, call `unify(related_rules + [rule])`; if it
returns an `UnifyResult` with `is_more_general()`, replace `rule` with
`result.abstract_rule` (and let V5 confirm the trace file the unify call
just wrote). When `unify()` raises `NoCommonSkeleton`, persist `rule`
unchanged. This is the iter that finally moves P3 above zero — but only
when at least two same-skeleton rules already exist, so iter 6 should also
add a smoke test that constructs two valid rules via `save_rule` and
verifies the second call produces an abstract rule with a non-null trace.

---
## Learning Loop -- 2026-05-13 18:23

- Split: None, Tasks: 3
- Correct: 0 / 3 (0.0%)
- Rules: 0 -> 0 (+0 learned)
- Stored rule hits: 0
- Time: 7s
- Log: logs/learn_20260513_182300.log

---
## Iter 6 -- 2026-05-13 -- branch test20

**Diagnosis**: Probe is 0/3, rules=0 — same surface as iters 1-5. Behind that,
iter 5 stood up `program.anti_unification.unify()` with its full §1 contract
and 14 passing tests, but `agent/memory.py:save_rule()` still does not call
it. CLAUDE.md §8 names `save_rule()` as the *only* permitted call site for
`unify()`, so until that wiring exists, P3 (anti_unification_trace fraction)
is structurally pinned at zero regardless of what the slow path discovers.
Iter 5's "Next gap" called for exactly this wiring as the smallest defensible
follow-up. Smallest step: extend `save_rule()` with an optional
`related_rules` kwarg + the §8 control flow, leave `active_agent.py`
unrewired (call-site migration is a separate iter).

**Change**:
- `agent/memory.py` — `save_rule()` now takes `related_rules: Iterable[dict] |
  None = None`. When non-empty, it locally imports
  `program.anti_unification.{unify, NoCommonSkeleton}`, calls
  `unify(list(related_rules) + [rule])`, and substitutes `result.abstract_rule`
  for `rule` when `is_more_general()`. `NoCommonSkeleton` is caught silently
  (it is `ValueError`, not `RuleSchemaError`, so F7's "swallowed
  RuleSchemaError" clause does not engage). The trace file `unify` already
  wrote is what lets the subsequent V5 check pass on the abstract rule's
  `anti_unification_trace`. Default behavior (no kwarg / empty kwarg) is
  bit-identical to iter 5 — verified by a test that monkey-patches
  `unify` to a tripwire and asserts it is never called.
- `tests/test_save_rule.py` — four new cases bringing the suite to 14:
  (1) no-related → unify untouched; (2) more-general → abstract rule written
  with covers-union and a real on-disk trace file matching V5; (3)
  `NoCommonSkeleton` (dsl mismatch) → new rule persisted unchanged;
  (4) identical inputs → `is_more_general() is False`, new rule persisted
  unchanged (no swap, no trace). All four use `_TEST_DSL_REGISTRY` so V3
  doesn't gate them out before AU is even reached.
- `docs/RULE_FORMAT.md` §7 — `save_rule()` row notes AU wiring landed in
  iter 6 with the F7-safety call-out; `unify()` row updated from
  "integration deferred" to "wired in iter 6"; `tests/test_save_rule.py`
  row notes the 4 added cases.
- `docs/ANTI_UNIFICATION.md` §4 — section retitled "Integration Point
  (wired in iter 6)" with the actual code snippet, behavior summary,
  and the explicit list of follow-up work (auto-archive of source rules,
  `load_related(category)` helper, `active_agent.py` migration).

**Probe before**: score=0/3, rules=0, covers_mean=0.0  (loop's iter-6 probe)
**Probe after** : (not re-run — wiring does not touch the solve path; the
slow path's rule writes still flow through `save_rule_to_ltm` legacy until
`active_agent.py` migrates).

**Invariants** (checker run end-to-end against base HEAD `14a166d3` — iter 5):
- forbidden = none. F1: 0-line diff against frozen-file paths. F2: no
  `+def _try_` / `+def _apply_` in `agent/active_operators.py`. F3: no
  `procedural_memory/DSL/*.py` diff at all. F4: still no `rule_*.json`
  files on disk. F5: no `semantic_memory/.*[Tt][Ff]_` paths added. F6:
  no edits to `run_loop.sh` / `run_pipeline.sh` / `run_learn.py` /
  `run_1ktasks.py`. F7: the new `except NoCommonSkeleton` clause does not
  catch `RuleSchemaError` and the only `RuleSchemaError` interactions in
  this diff are `raise` sites (untouched). F8: `agent/active_operators.py`
  numstat 0/0 (untouched), so the "grew without companion" clause cannot
  fire.
- positives: P1 0.0 → 0.0, P2 0.0 → 0.0, P3 0.0 → 0.0, P4 0 → 0, P5 1 → 1,
  P6 600 → 600. **Neutral on auto-measured signals** — checker exits 2 as
  expected. P3 is structurally pinned at 0/0 until at least one rule
  exists on disk, and rule existence requires `active_agent.py` to call
  the new wiring. The payoff lands the first time the solve path
  discovers two rules sharing a `(condition.type, action.dsl)` skeleton.
- All three test suites pass on this host: `tests/test_save_rule.py`
  14/14 (was 10/10 in iter 5), `tests/test_unify.py` 14/14,
  `tests/test_dsl.py` 17/17.

**Next gap (note for future iter)**: Two natural follow-ups now that the
§8 call site exists.
  1. Add a small `load_related(category, procedural_memory_root)` helper
     in `agent/memory.py` that returns existing rules sharing the
     candidate's category. This is the retrieval step `save_rule` is
     currently silent about — without it, every caller has to load
     `procedural_memory/` themselves before invoking AU. Pure read-only
     plumbing; ~10 LOC.
  2. Migrate `agent/active_agent.py`'s rule-save call site from
     `save_rule_to_ltm()` to `save_rule()`, supplying the §1 schema
     fields (condition/action/anti_unification_trace/...) from the
     pipeline's discovered rule. This is the iter that finally moves
     P1/P2/P3 above zero — but it has the most surface area in the call
     site (the pipeline currently emits the legacy `{type, mapping, ...}`
     shape, so a small translation layer is also needed). The retrieval
     helper from (1) is its natural prerequisite, making (1) genuinely
     smaller.

Either is defensible as iter 7's smallest step. (1) is the cleanest pure
prerequisite; (2) has the larger payoff but more code surface.

> STAGNATION at iter 6 — 3 consecutive neutral iters.

---
## Learning Loop -- 2026-05-13 18:28

- Split: None, Tasks: 3
- Correct: 0 / 3 (0.0%)
- Rules: 0 -> 0 (+0 learned)
- Stored rule hits: 0
- Time: 7s
- Log: logs/learn_20260513_182757.log

---
## Iter 7 -- 2026-05-13 -- branch test20

**Diagnosis**: Probe is 0/3, rules=0 — same surface as iters 1-6. Iter 6 wired
`program.anti_unification.unify()` into `agent/memory.py:save_rule()` via an
optional `related_rules` kwarg, but the *retrieval* side is still implicit:
every prospective caller has to scan `procedural_memory/` itself and filter
out legacy/malformed rules before invoking `save_rule`. Without a canonical
read helper, the next iter that migrates `agent/active_agent.py` would have
to inline that logic, and the temptation to skip the legacy-shape filter is
exactly the bug pattern that produced the 168-rule failure mode. Iter 6's
"Next gap" called this out as the smallest defensible follow-up. Smallest
step: add `load_related(category)` as pure read-only plumbing in
`agent/memory.py`, with tests, no call-site rewire.

**Change**:
- `agent/memory.py` — added `load_related(category, *,
  procedural_memory_root=PROCEDURAL_MEMORY_ROOT)`. Scans the directory,
  parses each `rule_NNN.json`, returns those whose `category` matches and
  which carry a dict-shaped `{condition, action}` block with the keys
  `unify()` reads (`condition.type`, `action.dsl`). Legacy rules (no
  `condition`/`action`), parse errors, non-JSON garbage, and non-rule
  filenames are silently skipped — `validate_rule` is intentionally NOT
  invoked because V6 (id collision against an existing file) would always
  fire for rules read back from disk. Bad-category input (empty string,
  non-string) short-circuits to `[]`. ~30 LOC including the docstring;
  signature matches `save_rule`'s kwarg name (`procedural_memory_root`).
- `tests/test_load_related.py` (new, dependency-free runner like the
  other `tests/test_*.py`) — 11 cases covering: (1) category filtering
  with mixed-category files, (2) legacy-shape rejection (top-level `rule`
  key, no `condition`/`action`), (3) malformed action (non-dict),
  (4) malformed condition (missing `type`), (5) non-JSON file tolerance,
  (6) non-rule-filename ignore (`README.md`, `rule_001.bak`), (7) empty
  directory → `[]`, (8) missing directory → `[]`, (9) bad-category input
  (`""`, `None`, `42`) → `[]`, (10) read-only contract (directory listing
  before/after is identical), (11) end-to-end smoke that pipes
  `load_related` output directly into `program.anti_unification.unify()`
  inside a sandbox chdir — asserts the result `is_more_general()`, proving
  the returned rule shape is the shape `unify` actually consumes.
- `docs/RULE_FORMAT.md` §7 — added a row for `load_related()` describing
  the contract, the deliberate non-use of `validate_rule` (V6 reason), and
  the legacy-skip behavior. Added a row for `tests/test_load_related.py`
  describing the 11 cases.

**Probe before**: score=0/3, rules=0, covers_mean=0.0
**Probe after** : (not re-run — pure read-side plumbing; does not affect
the solve path. Payoff lands when `active_agent.py` is migrated to call
`load_related(rule["category"])` ahead of `save_rule(rule,
related_rules=...)`.)

**Invariants** (checker run end-to-end against base HEAD `a87227b0` —
iter 6):
- forbidden = none. F1: 0-line diff against frozen-file paths (`data/`,
  `agent/cycle.py`, `agent/wm.py`, `ARCKG/{task,pair,grid,object,pixel}.py`).
  F2: no `+def _try_` / `+def _apply_` in `agent/active_operators.py`.
  F3: no `procedural_memory/DSL/*.py` diff at all (the new function is in
  `agent/memory.py`, not the DSL package). F4: still no `rule_*.json`
  files on disk. F5: no `semantic_memory/.*[Tt][Ff]_` paths added. F6:
  no edits to `run_loop.sh` / `run_pipeline.sh` / `run_learn.py` /
  `run_1ktasks.py`. F7: no `except RuleSchemaError` added or modified
  (the new function catches `OSError, json.JSONDecodeError` for the read
  path — neither is `RuleSchemaError`, so F7 does not engage). F8:
  `agent/active_operators.py` numstat 0/0 (untouched), so the "grew
  without companion" clause cannot fire.
- positives: P1 0.0 → 0.0, P2 0.0 → 0.0, P3 0.0 → 0.0, P4 0 → 0,
  P5 1 → 1, P6 600 → 600. **Neutral on auto-measured signals** —
  checker exits 2 as expected. This is read-side plumbing that has no
  observable effect on rule coverage, mean covers, AU-trace fraction,
  episodic count, condition-matcher count, or active-operators line
  count. The pure prerequisite character of the change is exactly why
  iter 6 called it the smaller of the two follow-ups: it does not earn
  a Δ this iter, but the moment the call-site migration lands, it is
  *the* function that decides whether AU is actually invoked or
  silently skipped.
- All four test suites pass: `tests/test_load_related.py` 11/11 (new),
  `tests/test_save_rule.py` 14/14, `tests/test_unify.py` 14/14,
  `tests/test_dsl.py` 17/17.

**Stagnation note**: This is the 4th consecutive NEUTRAL iter (iters 4-7
all `Δ=+0` across P1-P6). The cause matches `INVARIANTS.md §3` cause #3:
"the agent is doing scaffolding work whose payoff lands in a later iter".
The architecture pipeline P5→V3→`save_rule`→`unify`→`load_related` has
been built bottom-up across iters 1-7 with no rule ever actually written
to disk, because the call-site rewire in `active_agent.py` is the final
gate. That rewire is now the smallest gap that genuinely moves a
positive signal — every prerequisite below it is in place.

**Next gap (note for future iter)**: Migrate `agent/active_agent.py`'s
rule-save call site from `save_rule_to_ltm()` to `save_rule()`, using
`load_related(rule["category"])` to populate `related_rules`. This is
the iter that finally writes a schema-compliant rule file to
`procedural_memory/`, moving P1/P2 above zero (and P3 above zero as
soon as a second rule with the same category lands). The translation
layer is the surface-area concern: the pipeline currently emits the
legacy `{type, mapping, ...}` shape, so the call site must (a) infer
`condition.type` from the discovered pattern (e.g. `grid_size_preserved`
if dims match across all training pairs), (b) infer `action.dsl` from
the transformation kind (today: only `coloring` and `make_grid` are
admissible, so non-coloring/non-canvas rules cannot yet be persisted —
this is correct-by-construction and surfaces exactly which categories
need DSL-discovered abstractions next). Recommended: do it task-by-task
behind a small `_translate_to_schema(legacy_rule, task_hex)` helper in
`agent/active_agent.py` so the translation logic is auditable.
