"""
io — SOAR I/O link management module.

SOAR perspective:
  - The architecture creates S1 and the ^io skeleton in the 0th decision cycle.
  - At the start of each execution cycle, the environment's input function is called
    to add the environment state (here, ARC task) as WMEs under WM's ^io ^input-link.
  - output-link is the channel where the agent records actions/results to send to the environment.

In this project, WM is represented as Python dicts, so a serialized structure
of the task is placed under input-link.
"""

from __future__ import annotations


def inject_arc_task(task, wm) -> None:
    """
    Injects an ARC task under wm.s1['io']['input-link'].

    Injection location (conceptual):
      (S1 ^io I1)
      (I1 ^input-link I2)
      (I2 ^task T1 ...)

    In the implementation, task summary/grid content is placed in the input-link dict.
    """
    io = wm.s1.get("io")
    if not isinstance(io, dict) or "input-link" not in io:
        raise ValueError("io/input-link structure does not exist in WM.")

    in_link = io["input-link"]
    # SOAR style: only a symbol pointing to the task is placed on input-link first.
    # Detailed example/test structure is extended later in the production/elaboration phase
    # by following current-task or through a separate input function.
    in_link["task"] = task.task_hex
    wm.register_wme("input-link", "task", task.task_hex)
    # Store full task object for operator access
    wm.task = task


def clear_input_link(wm) -> None:
    """Clears the contents under ^input-link (for next execution cycle input refresh)."""
    io = wm.s1.get("io")
    if not isinstance(io, dict) or "input-link" not in io:
        raise ValueError("io/input-link structure does not exist in WM.")
    io["input-link"].clear()


def clear_output_link(wm) -> None:
    """Clears the contents under ^output-link (reset after reflecting to environment)."""
    io = wm.s1.get("io")
    if not isinstance(io, dict) or "output-link" not in io:
        raise ValueError("io/output-link structure does not exist in WM.")
    io["output-link"].clear()
