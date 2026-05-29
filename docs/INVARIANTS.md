# ARBOR Invariants

This document defines the **automated boundary** between "developing ARBOR the
way the user intends" and "regressing it." It is consumed by `run_loop.sh` (via
`scripts/check_invariants.sh`) at the end of every iteration. Violation of any
**forbidden signal** triggers `git revert HEAD` automatically; an iteration
that triggers none of them but improves at least one **positive signal** is
considered progress.

The single ultimate goal of ARBOR development:

> Build an agent whose **knowledge grows and whose problems get solved in the
> way the user intends** — relational, symbolic, bottom-up, self-extending.
> Solving more ARC tasks is *evidence*, not the goal. A solver that solves
> 1000 tasks by hand-coding 1000 detectors is failure, not success.

`CLAUDE.md` defines *what* the system is. This file defines *what it must
never become*, and *what counts as progress*.

---

## 1. Forbidden Signals (auto-revert on hit)

A violation here zeroes the iteration's reward, regardless of how many
deliverables passed. `scripts/check_invariants.sh` encodes each as a runnable
check.

### F1 — Frozen files modified

Any diff against `main` (or the prior commit, for non-`main` branches) touching:

- `data/`
- `agent/cycle.py`
- `agent/wm.py`
- `ARCKG/task.py`, `ARCKG/pair.py`, `ARCKG/grid.py`, `ARCKG/object.py`, `ARCKG/pixel.py`

These define the SOAR cycle and the 5-level node identity contract. Changing
them is an architecture change, not a session task.

Check: `git diff <base> -- data/ agent/cycle.py agent/wm.py ARCKG/task.py ARCKG/pair.py ARCKG/grid.py ARCKG/object.py ARCKG/pixel.py | wc -l` must be `0`.

### F2 — New `_try_*` or `_apply_*` method

The `_try_<name>` / `_apply_<name>` family in `agent/active_operators.py` is
**closed**. Bug-fixes inside an existing method are allowed; *new* methods are
not. Each new `_try_*` is a hand-coded special case — the very pattern that
produced 168 sub-coverage rules in `test13-eval`.

The correct response to a missing category is anti-unification or a new
*matcher* (in `agent/conditions/`), not a new `_try_*`.

Check: `git diff <base> -- agent/active_operators.py | grep -E "^\+\s*def _(try|apply)_"` must print nothing.

### F3 — Hand-coded DSL primitive added

The hand-coded DSL primitive set is **frozen at exactly two**:

- `coloring(selection, color)` — paint cells.
- `make_grid(height, width, color)` — produce a fresh canvas.

Every other transformation (move, rotate, flip, copy, scale, …) is a
*composition* of these two and must be **discovered by ARBOR at runtime**, not
written by a human/LLM. New static primitives in
`procedural_memory/DSL/*.py` are forbidden.

This is the boundary between *hand-coded* and *self-discovered*:

- ❌ **Hand-coded** — a new `@DSL.register("rotate")` decorator, or a new
  function under `procedural_memory/DSL/` that is not `coloring` /
  `make_grid`. Appears in `git diff` of a Python file.
- ✅ **Self-discovered** — a new abstract rule produced by
  `program/anti_unification.unify()`, persisted as data in
  `procedural_memory/rule_NNN.json` with `anti_unification_trace` set. No
  Python diff. `apply_DSL` dispatches discovered rules from the data layer at
  runtime.

Check: `git diff <base> -- procedural_memory/DSL/*.py | grep -E "^\+(@|\s+@).*register" | grep -vE 'register\("(coloring|make_grid)"\)'` must print nothing.

### F4 — Rule saved without `condition` key

A rule is a `{condition, action}` pair (CLAUDE.md §3.2, docs/RULE_FORMAT.md).
A rule lacking `condition` cannot be looked up by ARBOR's fast path — it
becomes dead memory. The 168-rule failure mode.

Check: any new `procedural_memory/rule_*.json` file at iter-end must pass
`agent/memory.py:validate_rule()`. The checker imports `validate_rule` and
runs it on every modified file under `procedural_memory/`.

### F5 — Detection results in `semantic_memory/`

`semantic_memory/` holds **declarative** ARCKG nodes only — TASK/PAIR/GRID/
OBJECT/PIXEL plus their compare edges. Transformed grids (`TF_GRID`),
intermediate working memory, and any per-attempt artifact belong in
`episodic_memory/`. Mixing them collapses the static/dynamic separation that
defines ARBOR.

Check: no path under `semantic_memory/` may contain `TF_` or `tf_grid` in its
basename.

### F6 — Auto-grown `--limit` or task pool

`run_loop.sh` already had `*** 100% score! Growing task pool ***`. That
broke reproducibility by silently changing the evaluation condition mid-run.
No script may *automatically* increase its task budget. The user controls the
budget via CLI flags only.

Check: `git diff <base> -- run_loop.sh run_pipeline.sh run_learn.py run_1ktasks.py | grep -E "TASKS_PER_SESSION\s*=\s*\(.*\*"` and similar auto-growth patterns must print nothing.

### F7 — `RuleSchemaError` swallowed

A `try/except` that catches `RuleSchemaError` without re-raising or logging
silently lets invalid rules survive. Equivalent to no validation at all.

Check: `git diff <base> -- agent/ scripts/ procedural_memory/ | grep -B1 -A3 "except.*RuleSchemaError" | grep -E "pass|continue" | grep -v "raise"` must print nothing (i.e., every `except RuleSchemaError` is followed by `raise` or an explicit log+re-raise).

### F8 — Score-chasing edit to active_operators.py without anti-unification touch

If a single iter modifies `agent/active_operators.py` *and* does **not** also
touch (`agent/memory.py` OR `program/anti_unification.py` OR
`agent/conditions/`), it is almost certainly the old "hand-tune the
generalizer" pattern. Allowed exceptions:
- Pure deletions / refactors that *remove* code (net negative line count).
- Doc/comment-only changes.

Check: if `git diff <base> --numstat -- agent/active_operators.py` shows net
positive additions, then `git diff <base> --name-only` must also include at
least one of `agent/memory.py`, `program/anti_unification.py`, or any file
under `agent/conditions/`.

---

## 2. Positive Signals (progress indicators)

An iteration that violates no forbidden signal but also improves **none** of
these is "neutral" — the loop logs it and continues, but flags N consecutive
neutrals to surface stagnation. Improving even one is enough.

These are computed *before* and *after* the iter, and the delta is recorded
in the iter's commit message.

### P1 — Rule coverage (`solved_tasks / total_rules`)

The Chollet-style skill-acquisition efficiency. Goes up when:
- An existing rule's `covers` list grows (a rule absorbs another task).
- Two rules merge into one via anti-unification (denominator down).
- A new task is solved via a rule already in memory (numerator up).

Goes down when a fresh rule is created per task (the 168-rule failure mode).

Measure: scan `procedural_memory/rule_*.json`, sum `len(covers)` for
numerator (de-duplicated by task), count files for denominator.

### P2 — Mean `covers` length per rule

Per-rule generality. A monotone proxy for "the rule abstracts well."
Anti-unification should drive this up; hand-coding drives it down (or holds it
at 1).

### P3 — Fraction of rules with non-null `anti_unification_trace`

What fraction of saved rules have been *generalized* vs being source-only?
Climbing fraction = anti-unification is actually wired and firing.

### P4 — Episodic memory entries

`episodic_memory/` was empty across 1k runs. Every `solve()` invocation —
pass or fail — should write one `attempt_NNN/` folder. The count increasing
linearly with attempts means the episodic writer is alive.

### P5 — Distinct `condition.type` values registered

How many *patterns* the system can recognize (not how many one-off detectors).
This is `len(CONDITION_REGISTRY)` from `agent/conditions/__init__.py`. Adding
a matcher is allowed (this is *recognition* vocabulary, not transformation
vocabulary).

### P6 — Net code removed from `agent/active_operators.py`

Anti-unification doing its job means `_try_*` / `_apply_*` get *deleted*, not
extended. Net negative line count on `active_operators.py` over time is the
strongest single signal of architectural progress.

---

## 3. Stagnation Signal (informational, not auto-revert)

If `N >= 3` consecutive iterations produce zero positive-signal improvement
without any forbidden-signal trip, `run_loop.sh` writes a `STAGNATION` notice
to `logs/session_log.md` and surfaces it on stdout. The loop keeps running —
this is *information for the user*, not an auto-revert. Possible causes:

- The "smallest next step" is genuinely hard (e.g., wiring anti-unification
  through `save_rule`).
- The probe set is too narrow to expose new gaps.
- The agent is doing scaffolding work whose payoff lands in a later iter.

---

## 4. Measurement Implementation

`scripts/check_invariants.sh` is the single entry point. Two modes:

```bash
# Pre-iter snapshot — writes baseline metrics to a tempfile.
./scripts/check_invariants.sh --snapshot logs/_invariant_snapshot.json

# Post-iter check — diffs against baseline, prints a verdict.
#   exit 0  → clean (no forbidden hit; one or more positive deltas ≥ 0)
#   exit 1  → forbidden signal tripped (caller should git revert)
#   exit 2  → neutral (no forbidden, no positive improvement)
./scripts/check_invariants.sh --check logs/_invariant_snapshot.json
```

The `<base>` for forbidden-signal diffs is the commit hash captured at
snapshot time (HEAD before Claude ran). The post-check diffs against that
hash, *not* against `main`, so iters compose correctly.

---

## 5. Cross-references

| Concern | Source |
|---------|--------|
| Why `{condition, action}` separation | `CLAUDE.md §3.2`, `docs/RULE_FORMAT.md` |
| Why DSL is frozen at 2 primitives | Wiki `[[arbor]]` + raw note `claude-탑다운과-바텀업-개발-방식의-확장-원리-2026-04-25.md` lines 1131, 1146 — "deliberately *under*-equip the system so transformations get *discovered*" |
| `_try_*` / `_apply_*` closure | `CLAUDE.md §5.1` |
| Anti-unification integration point | `CLAUDE.md §8`, wiki `[[anti-unification]]` |
| Score-chasing diagnosis (the reason this file exists) | Wiki `[[arbor]]` 진단 #1, #2, #5; `[[arbor-modules]] §9` |
