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
asked to "improve ARC score." Each iter you:

0. **Advance the active capability ladder** — the active governing doc
   (`docs/BACKLOG_LOOP.md`) defines a *capability ladder* (rungs R0..R6), not a
   single-task box. Identify the **lowest unproven rung** and the probe/target
   task(s) that exercise it, and **observe whether the system solves them *the
   way the user intends*** —
   judged by the **four observation criteria** (1: works, 2: uniformity of
   *modules* [the produced program may be overfit], 3: approaches the answer,
   4: search sanity), **NOT by score**. The probe output in your context is a
   microscope for this, not a target to maximize.
1. **Diagnose** the smallest gap between *how it solves now* and *how the user
   intends it to solve* (per the slice doc's sequence + criteria).
2. **Fill** the smallest such gap with the smallest defensible change.
3. **Verify** that the change did not trip any forbidden signal in
   `docs/INVARIANTS.md §1`, and improved at least one positive signal in §2.

"Smallest" means: if the gap can be split into two, do the smaller half. The
loop will keep running — there is always a next iter.

### 2.1 Three phases: `easy_a` → `madeup` → `training`

The loop walks a **three-phase development curriculum**; the probe header in
your context tells you which phase you are in. The phase is managed by
`run_loop.sh` (state file `logs/_phase_state.json`), **not** by you — never edit
that file to skip ahead. (The old user-authored `data/ARC_easy/` slice was
*retired*: some of its tasks were ill-posed — identical inputs mapped to
different outputs — so it is no longer a probe. The supplied beginner suite is
now `data/ARC_easy_a/` alone.)

- **`easy_a` phase** (default). The probe and your target are *all* of
  `data/ARC_easy_a/`. Goal: make the agent solve them *the way the user intends*
  (the four observation criteria above), not by score. The `easy000c–i` tasks
  need object/G0 analysis (ladder rung **R1**, `docs/BACKLOG_LOOP.md`). The
  graduation milestone is **all of `data/ARC_easy_a/` solved 100%** for K
  consecutive iters; the loop then switches to `madeup` automatically.

- **`madeup` phase**. Now the loop builds its **own beginner curriculum**. You
  *author* minimal ARC-style tasks under `data/ARC_madeup/` (the one F1-exempt
  corner of `data/`), each isolating **one concept the structure does not yet
  handle**, and then make the **structure itself** solve them — by expressing
  that task's specific rule through the existing mechanisms, *without expanding
  the concept vocabulary and without hand-coding a detector* (F2/F3). Concepts
  to climb, roughly one per task, easy variant → harder variant:

  - an object whose **size ≠ 1** (not a single pixel);
  - a grid with **object count ≠ 1** (more than one object);
  - **multi-object selection** — several objects present and *which one* the
    rule acts on is the crux (the selector is the real content);
  - the **grid size changes** between input and output;
  - input and output **grid sizes are not equal** to each other;
  - the **grid size is a function of an object's property/feature** (e.g. output
    height = count or size of some object);
  - the example pairs are **not exactly 2** (one pair, or three+).

  The point is the *selector / argument expression* (`unique`, `argmax`,
  `filter`, `position-of`, `size-of`, …) that lets the structure name what a
  task acts on — this is exactly the §2.5 "lift the selection" work, climbed on
  tasks you design to expose it. Author the smallest task you expect to **fail**;
  a task you can already pass teaches nothing. easy_a stays as a regression
  guard. The loop graduates to `training` only once the structure handles a
  reasonable spread of these concepts **unaided** — i.e. running the structure
  alone (no architectural concept-expansion that iter) solves the authored
  tasks by expressing each one's specific rule. That is the user's bar:
  *concept-free, structure-only, task-specific-rule* competence.

- **`training` phase**. The probe now samples real ARC tasks
  (`data/ARC_AGI/training/`, `--split training`). The job is to **make
  competence *grow* onto harder, unseen tasks by extending the system, not by
  hand-coding per-task detectors**. Prioritize gaps whose fix is *general* — a
  new `compare` capability, a new condition matcher, a property/relation/util
  primitive, or (the prize) getting `anti_unification.unify()` to fire and lift
  two task-specific programs into one rule with `covers` > 1. A training task
  you solve by a mechanism that also helps the *next* unseen task is real
  progress; one you solve by a bespoke `_try_*`-style special case is the
  documented failure mode (see `arbor.md` 진단 #1/#2/#5) and trips the forbidden
  signals.

Regression rule: a later-phase iter must not break an earlier phase's probe.
The loop keeps `easy_a` (and, once past it, `madeup`) as regression guards; if
either drops below 100%, fixing that regression *is* this iter's gap.

### 2.2 Challenge escalation & honest termination

This loop has run for hundreds of iters. The failure to avoid is **spinning** —
emitting near-duplicate, cosmetic, or trivially-reshuffling commits that look
like progress but move the system nowhere. That is worse than doing nothing.
The rule for this project: **every commit must close a real gap, or the iter
makes no commit at all** (§5 already blesses the no-op iter).

The phase you are in (§2.1) tells you *where* to look for that gap:

1. **`madeup` phase — author your own beginner curriculum (the core work
   here).** Once `easy_a` is mastered, do **not** keep polishing it. Write a
   minimal ARC-style task under `data/ARC_madeup/` (standard
   `{"train":[…],"test":[…]}` JSON — see `data/ARC_madeup/README.md`) that
   isolates **one** of the §2.1 concepts the structure cannot yet express (object
   size≠1, object count≠1, multi-object selection, grid resize, unequal in/out
   sizes, size↔object-property, pairs≠2), then make the **structure** solve it —
   by lifting the right *selector / argument expression* (§2.5), **not** by
   hand-coding a detector and **not** by inventing a new concept the task happens
   to need. Author the smallest task you expect to *fail*; a challenge you can
   already solve teaches nothing. Build a small ladder (easy variant → harder
   variant) and climb it: `python run_learn.py --task-dir data/ARC_madeup/`.
   `data/ARC_madeup/` is the **one exempt corner** of frozen `data/` (F1 excludes
   it); tasks there are tracked and pushed, so they persist. The graduation bar
   is the structure handling a reasonable spread of these *unaided* (§2.1).

2. **`training` phase — take on ARC-AGI-2 tasks the agent fails.**
   `data/ARC_AGI/` is ARC-AGI-2 (1000 training / 120 evaluation). The probe
   samples it; you may also run any slice yourself:
   `python run_learn.py --split training --limit N --shuffle --seed 42`. Pick one
   the agent fails *for a reason you can name*, and close that underlying
   capability gap so the fix generalizes. When a supplied training task surfaces
   no fresh gap, fall back to authoring a `data/ARC_madeup/` task (as in 1) that
   exposes the next one.

3. **Generalize across what is already solved.** Two task-specific programs that
   share a skeleton are an invitation for `anti_unification.unify()` to lift
   them into one rule with `covers` > 1. Driving rule coverage up is always real
   work, in any phase.

You are **not** required to solve every task — ARC is not fully solvable by this
early agent, and that is expected. The bar is *honest motion*: each iter either
closes a nameable gap or sets up a sharper test of one. Manufacturing busywork
(authoring a challenge you can already pass, or re-touching solved tasks) is the
same spinning failure in disguise — don't.

**Honest termination.** If you assess that the system is **sufficiently
developed** — i.e. there is no longer a nameable gap you can close *and* you
cannot author a defensible new challenge that exposes one — then the right move
is to **stop the loop**, not to spin. Signal this by writing
`logs/_LOOP_COMPLETE.md` containing:

- a dated, evidence-backed argument that development has converged (what the
  agent can now do the intended way; which positive signals plateaued; what you
  tried to challenge it with and why nothing surfaced a real gap),
- the rule-coverage figure and the easy_a / madeup / training standings,
- the honest remaining limitations (so the user can decide whether to lift the
  bar).

`run_loop.sh` checks for that file at the top of each iter and ends the loop
cleanly when it is present (the user resumes by deleting it). Write it only when
it is *true*; a premature completion file is itself a meaningless artifact.
Reserve it for genuine convergence — when in doubt, escalate (1–3) instead.

---

## 3. Procedure (do in order)

### Step 1 — Read the situation

Read these, in this order, every iter. **Do not skim and do not work from
summaries** — the design intent lives in the *detail* of the user's own prose.
If an iter is short on time, read *less code*, not less of this context.

**A. The active target**

1. **`docs/BACKLOG_LOOP.md`** — the **active governing doc** (a capability
   ladder, not a single-task slice box; it replaces the old
   `docs/SLICE_N_LOOP.md`). THIS IS YOUR CONCRETE TARGET FOR THIS ITER: the
   rung ladder (R0..R6), which rung is lowest-unproven, the 7 design
   principles, the guardrails that remain vs. those lifted, and how a rung is
   proven + the loop auto-climbs (no human gate). (The retired
   `SLICE_1_LOOP.md` has been removed; its R0 work is summarized in the ladder.)

**B. The ARBOR design originals — `docs/arbor_context/` (the mirrored wiki).**
This directory is the user's full-detail specification of how ARBOR is meant to
*work*, copied verbatim from the design wiki. It is **frozen / read-only**
(editing it trips F1) — you read it every iter so progress bends toward the
intended system, not toward a convenient local optimum. Read **all** of it:

2. `docs/arbor_context/arbor.md` — the **canonical project page**: the single
   ultimate goal, the architecture table, Fast/Slow path, the 6 diagnosed
   failures (why 400+ iters produced little), and the "next tasks" backlog.
   *Start here — it frames everything else.*
3. `docs/arbor_context/arbor-flow-three-task-description.md` — the user's **raw
   prose** walking through easy000a / easy000b / 08ed6ac7 step by step. This is
   the most important document: it is *how the user intends the agent to solve*.
   Read it in full; do not compress it.
4. `docs/arbor_context/arbor-execution-trace.md` — the 11 modules + spec-gap
   table derived from that prose. The **Gap** notes are unfilled holes.
5. `docs/arbor_context/arbor-modules.md` — module inventory (intent ↔ code
   state). Its **Gap** column is the canonical list of what is missing.
6. `docs/arbor_context/arbor-soar-memory-mapping.md` and
   `docs/arbor_context/arbor-memory-contents.md` — the **2026-05-31 inflection**:
   ARBOR's "semantic memory" is a misnomer for *persisted Working Memory*;
   these define *what actually goes in each of the four memories*. If anything
   here conflicts with an older statement in `CLAUDE.md §3`, **these pages are
   the newer intent** — note the conflict in your log rather than regressing.
7. `docs/arbor_context/arbor-dsl-taxonomy.md` — the DSL 4-way split
   (transformation frozen at 2; property/relation/util hand-coding *allowed*).
8. `docs/arbor_context/arbor-open-questions.md` — the 11 unresolved questions
   (the user's explicit "(아직 모르겠어)" — do not silently invent answers; if
   your gap touches one, surface it).
9. `docs/arbor_context/arbor-signals.md` and
   `docs/arbor_context/arbor-prompt-spec.md` — the reward-signal rationale and
   the prompt blueprint behind this very file.
10. `docs/arbor_context/arckg-wm-design.md` — WM region design.

**C. The operating rules**

11. `CLAUDE.md` — architecture invariants (frozen files, operator pipeline,
    memory schema). Authoritative for *unchangeable* facts; where §B's newer
    pages refine it, §B wins on *intent* but CLAUDE.md's frozen contracts still
    bind the code.
12. `docs/INVARIANTS.md` — what is forbidden / what counts as progress.
13. `docs/RULE_FORMAT.md` — current rule schema.
14. The output of the probe run that `run_loop.sh` just executed (in the
    prompt context as `${PROBE_OUTPUT}` — see Step 2). The loop may be in the
    **easy_a**, **madeup**, or **training** phase (§2.1); the probe header states
    which and the exact command it ran. Treat the probe as a *microscope*, not a
    target. You may also run any slice yourself —
    `python run_learn.py --task-dir data/ARC_easy_a` (easy_a),
    `--task-dir data/ARC_madeup/` (madeup), or `--split training` (training).

### Step 2 — Diagnose one gap

The phase-appropriate probe (`run_learn.py --task-dir data/ARC_easy_a` in the
easy_a phase, `--task-dir data/ARC_madeup/` in madeup, or `--split training
--limit 3 --shuffle --seed <fixed>` in training) ran *before* you were invoked.
Its output is in `${PROBE_OUTPUT}`. The probe is **not** a score to maximize —
it is a microscope. Use it to surface *where* the system is blind. Failure
patterns to look for:

- The agent solved 0 of the probe — Slow path is producing no rules at all.
  Likely cause: `extract_pattern`, `generalize`, or `save_rule` is unwired.
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
- **Spin.** Do not emit a near-duplicate, cosmetic, or trivially-reshuffling
  commit just to have committed something this iter. If the current phase's
  probe is mastered and no nameable gap surfaces, you must either *escalate* the
  challenge (§2.2: author the next `data/ARC_madeup/` task that exposes a gap, or
  in the training phase take on a failing ARC-AGI-2 task), make a real no-op iter
  (§5), or — when
  development has genuinely converged — end the loop honestly (§2.2,
  `logs/_LOOP_COMPLETE.md`). Repeating the same low-value change is the single
  behavior this project most wants gone.

---

## 5. When in doubt

If you cannot find a smallest-step gap that satisfies §3 without tripping a
forbidden signal, the correct iter output is:

1. **First try to escalate, not idle** (§2.2). If `easy_a` is mastered, author
   the next `data/ARC_madeup/` task that exposes a real gap (the `madeup` phase's
   core work); in the `training` phase, take on a failing ARC-AGI-2 task — that
   is usually where the next defensible step is.
2. If escalation also yields no defensible step *and* you judge development has
   converged, write `logs/_LOOP_COMPLETE.md` per §2.2 to end the loop honestly.
3. Otherwise, append a `Iter <N>: no defensible step found — analysis only`
   entry to `logs/session_log.md` with your reasoning, commit nothing, and exit
   cleanly.

A no-op iter is correct behavior, not failure. The loop will continue. A
*wrong* commit is worse than a *no* commit, because it pollutes the
positive-signal baseline. A *repeated* commit (spinning) is worse still.
