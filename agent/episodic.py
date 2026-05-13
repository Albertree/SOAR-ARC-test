"""
agent.episodic — episodic-memory writer for SOAR ``solve()`` attempts.

CLAUDE.md §3.3 specifies that every ``solve()`` invocation — pass or fail —
produces exactly one ``episodic_memory/<task_hex>/attempt_NNN/`` folder.
An empty ``episodic_memory/`` after a probe run is therefore an architecture
violation: the writer was bypassed.

This module is the writer. It is deliberately minimal: it persists the
outcome record the caller already has in hand (``metadata.json``), creates
the ``trace.json`` and ``grids/`` placeholders the §3.3 layout names so
later iters can extend them in place without reshaping the folder, and
returns the path it just wrote.

The writer does **not** introspect ``WorkingMemory`` — that would require
reaching into frozen ``agent/wm.py``. Richer per-cycle traces are a later
iter's territory; they will land by Claude- or hook-instrumented sidecar
collection feeding into ``trace.json``, not by editing the frozen cycle.

API:

    write_attempt(task_hex, *, outcome, info, root="episodic_memory") -> str

Pure with respect to its inputs (no mutation of ``info``). The only
side-effect is filesystem writes under ``root``. Determinism is up to the
caller: ``attempt_NNN`` is assigned by scanning the directory for the
highest existing ``attempt_<int>`` and incrementing.
"""

from __future__ import annotations

import copy
import json
import os
import re
from datetime import datetime
from typing import Mapping

EPISODIC_MEMORY_ROOT = "episodic_memory"

_ATTEMPT_RE = re.compile(r"^attempt_(\d+)$")
_HEX8_RE = re.compile(r"^[0-9a-f]{8}$")


def _next_attempt_index(task_dir: str) -> int:
    """Return the next monotonic ``attempt_<n>`` index for ``task_dir``.

    Scans existing children matching ``attempt_<int>``; ignores any other
    names (including malformed ``attempt_NNN`` strings). Returns 1 for an
    empty or missing directory.
    """
    if not os.path.isdir(task_dir):
        return 1
    highest = 0
    for child in os.listdir(task_dir):
        m = _ATTEMPT_RE.match(child)
        if not m:
            continue
        try:
            n = int(m.group(1))
        except ValueError:
            continue
        if n > highest:
            highest = n
    return highest + 1


def write_attempt(task_hex: str, *,
                  outcome: str,
                  info: Mapping | None = None,
                  root: str = EPISODIC_MEMORY_ROOT) -> str:
    """Create one ``<root>/<task_hex>/attempt_<n>/`` folder with the §3.3
    layout. Returns the attempt folder's path.

    ``outcome`` is a free-form short string (e.g. ``"correct"``,
    ``"incorrect"``, ``"error"``). ``info`` is a JSON-serialisable mapping
    of arbitrary per-attempt details (rule type, step count, method, …);
    it is deep-copied before write so the caller cannot accidentally
    mutate the persisted record by mutating their dict afterwards.

    Raises ``ValueError`` on a malformed ``task_hex``. Filesystem errors
    propagate.
    """
    if not isinstance(task_hex, str) or not _HEX8_RE.match(task_hex):
        raise ValueError(
            f"task_hex must be 8 lowercase hex chars, got {task_hex!r}"
        )
    if not isinstance(outcome, str) or not outcome:
        raise ValueError("outcome must be a non-empty string")
    info_copy: dict = copy.deepcopy(dict(info)) if info else {}

    task_dir = os.path.join(root, task_hex)
    os.makedirs(task_dir, exist_ok=True)

    n = _next_attempt_index(task_dir)
    attempt_dir = os.path.join(task_dir, f"attempt_{n:03d}")
    os.makedirs(attempt_dir, exist_ok=False)

    metadata = {
        "task_hex": task_hex,
        "attempt_index": n,
        "outcome": outcome,
        "created_at": datetime.now().isoformat(),
        "info": info_copy,
    }
    with open(os.path.join(attempt_dir, "metadata.json"), "w",
              encoding="utf-8") as fh:
        json.dump(metadata, fh, indent=2, sort_keys=False)

    with open(os.path.join(attempt_dir, "trace.json"), "w",
              encoding="utf-8") as fh:
        json.dump([], fh)

    os.makedirs(os.path.join(attempt_dir, "grids"), exist_ok=True)

    return attempt_dir
