"""
episodic — write one ``attempt_NNN/`` folder per ``solve()`` invocation.

CLAUDE.md §3.3 mandates that *every* ``solve()`` call — success or failure —
produces exactly one ``episodic_memory/<task_id>/attempt_NNN/`` folder holding
``trace.json``, ``grids/``, and ``metadata.json``. INVARIANTS.md §2 P4 records
that this writer was silently lost ("episodic_memory/ was empty across 1k
runs"): the current ``ActiveSoarAgent.solve()`` produces no episode at all, so
the slow/fast solve path leaves no execution trace behind.

This module restores the writer **without touching the frozen cycle**
(``agent/cycle.py``). The frozen ``run_cycle`` returns only a summary
(``steps_taken`` / ``goal_satisfied``), so ``trace.json`` records the summary
the cycle exposes plus the discovered/applied rule — not a per-phase log, which
would require editing the frozen engine. ``grids/`` captures the test input
grids (``step_000``) and the submitted prediction (final step), the
input→output snapshot pair the writer can observe from outside the cycle.
"""

from __future__ import annotations

import os
import json
from datetime import datetime


def _next_attempt_index(task_dir: str) -> int:
    """Return the next ``attempt_NNN`` index (1-based) for a task folder."""
    if not os.path.isdir(task_dir):
        return 1
    highest = 0
    for name in os.listdir(task_dir):
        if not name.startswith("attempt_"):
            continue
        try:
            highest = max(highest, int(name.split("_", 1)[1]))
        except (ValueError, IndexError):
            continue
    return highest + 1


def write_episode(
    root: str,
    task_hex: str,
    *,
    predicted,
    info: dict,
    trace=None,
    grid_steps=None,
) -> str:
    """Write one ``attempt_NNN/`` folder and return its path.

    root       : episodic_memory root directory
    task_hex   : task id (becomes the per-task subfolder)
    predicted  : the solver's prediction (list of grids) or None
    info       : the agent's ``last_solve_info`` dict (method, rule_type, ...)
    trace      : list of trace records (cycle summary / stored-rule hit)
    grid_steps : ordered list of grid snapshots → step_000.json, step_001.json…
    """
    task_dir = os.path.join(root, task_hex)
    index = _next_attempt_index(task_dir)
    attempt_dir = os.path.join(task_dir, f"attempt_{index:03d}")
    grids_dir = os.path.join(attempt_dir, "grids")
    os.makedirs(grids_dir, exist_ok=True)

    metadata = {
        "task_hex": task_hex,
        "attempt_index": index,
        "outcome": "submitted" if predicted else "no_prediction",
        "created_at": datetime.now().isoformat(),
        "info": info,
    }
    with open(os.path.join(attempt_dir, "metadata.json"), "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2)

    with open(os.path.join(attempt_dir, "trace.json"), "w", encoding="utf-8") as f:
        json.dump(trace or [], f, indent=2)

    for i, grid in enumerate(grid_steps or []):
        with open(os.path.join(grids_dir, f"step_{i:03d}.json"), "w", encoding="utf-8") as f:
            json.dump(grid, f)

    return attempt_dir
