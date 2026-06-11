# `challenges/` — self-authored probe tasks

This directory is the **non-frozen** home for ARC-style tasks that the loop
(Claude, inside a `run_loop.sh` session) **authors itself** to probe a specific
capability gap. See `PROMPT.md §2.2` ("Challenge escalation & honest
termination").

Unlike `data/` (which is **frozen** — editing it trips invariant F1), files here
may be created, run, and deleted freely during a session. They are *not* part of
the official ARC dataset; they exist only to let the agent set itself a sharper,
self-made test once the supplied easy slices are mastered.

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
python run_learn.py --task-dir challenges/            # run all self-authored tasks
python run_learn.py --task-dir challenges/ --limit 1  # just the first
```

`--task-dir` loads every `*.json` here and reports a `Correct: X / N` line, the
same microscope used by the easy/training probes.

## Discipline (from PROMPT.md §2.2)

- Author a challenge to **isolate a named gap** ("does the agent generalize a
  same-color relation across pairs when sizes differ?"), not to inflate a score.
- The point is to *find work worth doing* when the supplied slices no longer
  surface a real gap — **not** to manufacture busywork. A challenge you can
  already solve teaches nothing; author the smallest one you expect to *fail*,
  then close that gap by extending the system (never by hand-coding a detector).
- Solving every challenge is **not** required. Avoiding meaningless,
  near-duplicate commits **is**.
