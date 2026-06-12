# `data/ARC_madeup/` — self-authored probe tasks

This directory is the **self-authored task area** for ARC-style tasks that the
loop (Claude, inside a `run_loop.sh` session) **invents itself** to probe a
specific capability gap. See `PROMPT.md §2.2` ("Challenge escalation & honest
termination").

**This is the `madeup` phase curriculum** (`PROMPT.md §2.1`). After mastering
`data/ARC_easy_a/`, the loop graduates here and authors a small ladder of
beginner tasks, each isolating **one** concept the structure cannot yet express,
then makes the structure solve it *unaided* (no concept expansion, no hand-coded
detector — F2/F3). Concepts to climb, roughly one per task:

- an object whose **size ≠ 1** (not a single pixel);
- a grid with **object count ≠ 1**;
- **multi-object selection** — which of several objects the rule acts on is the crux;
- the **grid size changes** between input and output;
- input and output **grid sizes are not equal**;
- the **grid size is a function of an object's property** (e.g. output size = object count);
- the example pairs are **not exactly 2** (one, or three+).

The loop graduates to the `training` phase only once the structure handles a
reasonable spread of these (≥ `MADEUP_MIN_TASKS`, default 7) at 100% for K
consecutive iters, with `easy_a` still clean.

## Freeze status — the one writable corner of `data/`

`data/` is **frozen** (invariant F1): the supplied datasets (`ARC_easy`,
`ARC_easy_a`, `ARC_AGI`) are read-only and editing them auto-reverts the iter.
**`data/ARC_madeup/` is the sole exemption** — `scripts/check_invariants.sh`
excludes this path from the F1 check, so the loop may create, run, and delete
tasks here freely. Because `data/` is git-tracked, tasks you author here are
**committed and pushed** like the rest of the dataset (they persist).

Do not put anything but self-authored tasks here, and never edit the supplied
datasets to route around the freeze.

## Format

Each task is one `.json` file in standard ARC shape:

```json
{
  "train": [ { "input": [[...]], "output": [[...]] }, ... ],
  "test":  [ { "input": [[...]], "output": [[...]] } ]
}
```

## Running them

```bash
python run_learn.py --task-dir data/ARC_madeup/            # run all self-authored tasks
python run_learn.py --task-dir data/ARC_madeup/ --limit 1  # just the first
```

`--task-dir` loads every `*.json` here and reports a `Correct: X / N` line, the
same microscope used by the easy/training probes.

## Discipline (from PROMPT.md §2.2)

- Author a task to **isolate a named gap** ("does the agent generalize a
  same-color relation across pairs when sizes differ?"), not to inflate a score.
- The point is to *find work worth doing* when the supplied slices no longer
  surface a real gap — **not** to manufacture busywork. A task you can already
  solve teaches nothing; author the smallest one you expect to *fail*, then
  close that gap by extending the system (never by hand-coding a detector).
- Solving every task is **not** required. Avoiding meaningless, near-duplicate
  commits **is**.
