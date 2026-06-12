"""
episodic — the episodic-memory writer (ARBOR LTM store #3).

CLAUDE.md §3.3 contract::

    episodic_memory/
    └── {task_id}/
        └── attempt_NNN/
            ├── trace.json     ← per-attempt operator/impasse log
            ├── grids/         ← step-by-step WM grid snapshots
            │   ├── step_000.json
            │   └── step_NNN.json
            └── metadata.json  ← outcome, score, rules used, AU invocations

Every ``solve()`` invocation — success *or* failure — must produce exactly one
``attempt_NNN/`` folder (CLAUDE.md §3.3). An empty ``episodic_memory/`` after a
run means this writer was bypassed, which is an architecture violation
(INVARIANTS P4). This module is the writer; the solve loop is its sole caller
(``agent/active_agent.py``) — it must NOT be invoked from frozen
``agent/cycle.py`` (the cycle stays pure; the writer is wired around it).

The source for this module was lost at the test31 clean-start node (only stale
``.pyc`` remained, identical to the DSL primitives restored in iter 2); it is
reconstructed here faithfully to the on-disk format of the existing attempts.
"""
from __future__ import annotations

import json
import os
import re

_ATTEMPT_RE = re.compile(r"^attempt_(\d+)$")


def _next_attempt_index(task_dir: str) -> int:
    """Lowest unused ``attempt_NNN`` index in ``task_dir`` (0 if none exist)."""
    used = []
    if os.path.isdir(task_dir):
        for name in os.listdir(task_dir):
            m = _ATTEMPT_RE.match(name)
            if m:
                used.append(int(m.group(1)))
    return max(used) + 1 if used else 0


def _write_json(path: str, payload) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)


def write_attempt(task_hex: str, *, trace: dict, metadata: dict, grids,
                  episodic_root: str = "episodic_memory") -> str:
    """Write exactly one ``attempt_NNN/`` folder for one ``solve()`` invocation.

    Parameters
    ----------
    task_hex : task id → ``episodic_memory/<task_hex>/``.
    trace    : per-attempt operator/impasse summary (granularity-tagged).
    metadata : outcome, method, rule fired, AU invocations, etc.
    grids    : iterable of ``(label, 2D-int-grid)`` ordered WM grid snapshots,
               written as ``grids/step_000.json … step_NNN.json``.

    Returns the attempt folder path. Always allocates a *fresh* attempt index,
    so repeated solves of the same task accumulate (drives positive signal P4).
    """
    task_dir = os.path.join(episodic_root, str(task_hex))
    idx = _next_attempt_index(task_dir)
    attempt_dir = os.path.join(task_dir, "attempt_" + format(idx, "03d"))
    grids_dir = os.path.join(attempt_dir, "grids")
    os.makedirs(grids_dir, exist_ok=True)

    _write_json(os.path.join(attempt_dir, "trace.json"), trace)
    _write_json(os.path.join(attempt_dir, "metadata.json"), metadata)
    for step_idx, (label, grid) in enumerate(grids):
        _write_json(
            os.path.join(grids_dir, "step_" + format(step_idx, "03d") + ".json"),
            {"label": label, "grid": grid},
        )
    return attempt_dir
