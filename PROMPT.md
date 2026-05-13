# ARBOR — Iter Mission

> Architecture invariants: `CLAUDE.md`.
> Rule schema: `docs/RULE_FORMAT.md`.
> Forbidden/positive signals: `docs/INVARIANTS.md` — **read this every iter**.
> This file is *iter-agnostic* — it fires unchanged on every `run_loop.sh` cycle.

---

## 1. The single ultimate goal

> Build an agent whose knowledge grows and whose problems get solved
> **in the way the user intends** — relational, symbolic, bottom-up,
> self-extending.

Solving more ARC tasks is *evidence*, never the goal. A solver that solves
1000 tasks by accreting 1000 hand-coded detectors is failure. There is no
"this session's mission" beyond this single goal — every iter advances the
same goal.

---

## 2. What this iter is for

One iter = one **smallest concrete step** toward the goal above. You are not
asked to "improve ARC score." You are asked to:

1. **Diagnose** what is missing right now between the current code and the
   intended system.
2. **Fill** the smallest such gap with the smallest defensible change.
3. **Verify** that the change did not trip any forbidden signal in
   `docs/INVARIANTS.md §1`, and improved at least one positive signal in §2.

"Smallest" means: if the gap can be split into two, do the smaller half. The
loop will keep running — there is always a next iter.

---

## 3. Procedure (do in order)

### Step 1 — Read the situation

Read these, in this order, every iter:

1. `CLAUDE.md` — architecture invariants (frozen files, operator pipeline,
   memory schema).
2. `docs/INVARIANTS.md` — what is forbidden / what counts as progress.
3. `docs/RULE_FORMAT.md` — current rule schema.
4. The output of the probe run that `run_loop.sh` just executed (it is in
   the prompt context as `${PROBE_OUTPUT}` — see Step 2).
5. The wiki module map at `~/Desktop/wiki/wiki/arbor-modules.md` if it
   exists — its **Gap** column is the canonical list of unfilled holes.

### Step 2 — Diagnose one gap

The probe (`run_learn.py --limit 3 --shuffle --seed <fixed>`) ran *before*
you were invoked. Its output is in `${PROBE_OUTPUT}`. The probe is **not** a
score to maximize — it is a microscope. Use it to surface *where* the system
is blind. Failure patterns to look for:

- The agent solved 0/3 — Slow path is producing no rules at all. Likely
  cause: `extract_pattern`, `generalize`, or `save_rule` is unwired.
- The agent solved some but `procedural_memory/rule_*.json` count grew
  faster than `solved` count — `_try_*` accretion happening; anti-unification
  not firing.
- `episodic_memory/` is still empty — episodic writer never gets called from
  the cycle.
- A rule got saved without a `condition` key — `save_rule` is missing
  validation.

Cross-reference with `arbor-modules.md` if available — it has explicit Gap
notes per module. Pick **one** gap. Smallest one defensible as a single
commit.

Write a 2–3 sentence diagnosis to the top of your session-log entry (Step 5).

### Step 3 — Fill it

Allowed:

- Create new files under `agent/conditions/`, `agent/`, `program/`, `tests/`,
  `docs/`, `scripts/`.
- Add new functions to `agent/memory.py`, `program/anti_unification.py`.
- Add `coloring(selection, color)` and `make_grid(height, width, color)` to
  `procedural_memory/DSL/` if they are not yet there. **These are the only
  two hand-coded primitives that may ever exist.** No third primitive,
  ever, by hand.
- Add condition matchers under `agent/conditions/<name>.py` and register
  them in `agent/conditions/__init__.py:CONDITION_REGISTRY`.
- Wire anti-unification into `agent/memory.py:save_rule()` as specified in
  `CLAUDE.md §8`.
- Wire the episodic writer into the solve loop (without modifying frozen
  `agent/cycle.py`).
- Migrate / delete rules under `procedural_memory/` that violate the schema.
- Refactor `agent/active_operators.py` to *remove* `_try_*` / `_apply_*`
  methods that are superseded by anti-unification.

Forbidden (auto-revert — see `INVARIANTS.md §1` for the exact checks):

- Modify any frozen file (`data/`, `agent/cycle.py`, `agent/wm.py`,
  `ARCKG/*.py` node classes).
- Add a new `_try_<name>` or `_apply_<name>` method.
- Add a hand-coded DSL primitive other than `coloring` / `make_grid`.
- Save a rule without a `condition` key.
- Write `TF_GRID` anywhere under `semantic_memory/`.
- Auto-grow `--limit` or task pool.
- Silently swallow `RuleSchemaError`.
- Edit `agent/active_operators.py` to add code without also touching
  `agent/memory.py`, `program/anti_unification.py`, or `agent/conditions/`.

### Step 4 — Verify

Run the tests and the invariant checker locally before declaring the iter
done. The loop will run them again, but catching a violation yourself saves
a revert.

```bash
pytest tests/ -q                     # if any tests exist
./scripts/check_invariants.sh --check logs/_invariant_snapshot.json
```

If invariants fail: roll back your change (`git checkout -- <files>`) and
either fix it or commit nothing. Do not paper over a violation by deleting
the check.

### Step 5 — Log

Append to `logs/session_log.md`:

```markdown
## Iter <N> — <ISO 8601> — branch <name>

**Diagnosis**: <2–3 sentences. What gap did you pick? Why is it the smallest
defensible step right now?>

**Change**: <bulleted list of files touched and why>

**Probe before**: <one line — score, rule count, covers mean>
**Probe after** : <same metrics>

**Invariants**: forbidden=<none|F1..F8>, positives=<P1..P6 deltas>

**Next gap (note for future iter)**: <one sentence — what's now the most
glaring unfilled gap. Do not commit to a plan; just observe.>
```

The "Next gap" line is **information for the next iter to read**, not a
commitment. Each iter re-diagnoses from scratch.

---

## 4. What to never do

- Treat ARC score as the reward function. Score is a probe; the reward is in
  `INVARIANTS.md §2`.
- Add a new "category" of `_try_*` to handle a failing task. The mechanism
  for handling a new category is **anti-unification**, not a new detector.
- Hand-code a `rotate`/`move`/`flip` primitive because the agent "can't find
  it on its own yet." If anti-unification cannot discover it from the data,
  the missing piece is in anti-unification or in `compare` — not in the DSL.
- Hide validation failures behind broad `try/except` blocks.
- Plan multi-iter missions in this PROMPT.md. There are no future-session
  promises here; just the current iter's smallest step.

---

## 5. When in doubt

If you cannot find a smallest-step gap that satisfies §3 without tripping a
forbidden signal, the correct iter output is:

1. Append a `Iter <N>: no defensible step found — analysis only` entry to
   `logs/session_log.md` with your reasoning.
2. Commit nothing.
3. Exit cleanly.

A no-op iter is correct behavior, not failure. The loop will continue. A
*wrong* commit is worse than a *no* commit, because it pollutes the
positive-signal baseline.
