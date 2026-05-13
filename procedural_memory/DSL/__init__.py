"""procedural_memory.DSL — the hand-coded DSL primitive package.

Hand-coded primitives are **closed at exactly two**:

  * ``coloring(grid, selection, color)`` — paint selected cells.
  * ``make_grid(height, width, color)`` — produce a fresh canvas.

Every other transformation (move, rotate, flip, copy, scale, fill_region, …)
must be **discovered by ARBOR at runtime** via ``program.anti_unification`` —
not written by a human/LLM. This is the operational meaning of "Bottom-up
Organized Rules" in ARBOR. See ``CLAUDE.md §6.1`` and ``docs/INVARIANTS.md
§1 F3``.

Module layout:

  - ``apply.py``       — ``DSL_REGISTRY``, ``@register`` decorator, ``apply_DSL``.
  - ``coloring.py``    — the ``coloring`` primitive.
  - ``make_grid.py``   — the ``make_grid`` primitive.

Importing this package transitively imports both primitive modules so their
``@register`` decorators fire and ``DSL_REGISTRY`` is populated by the time
any consumer (e.g. ``agent.memory.validate_rule``) inspects it.
"""

from __future__ import annotations

from procedural_memory.DSL import apply  # noqa: F401
from procedural_memory.DSL import coloring  # noqa: F401
from procedural_memory.DSL import make_grid  # noqa: F401
