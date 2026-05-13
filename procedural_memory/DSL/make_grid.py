"""make_grid — produce a fresh ``height x width`` canvas filled with ``color``.

Signature::

    make_grid(height, width, color) -> new_grid

* ``height`` — positive int (rows).
* ``width``  — positive int (columns).
* ``color``  — int in ``0..9`` (ARC palette) or ``13`` (transparent
               sentinel; same semantics as ``coloring``).

Pure: returns a fresh nested list each call; no shared row references, so
later in-place edits to one row do not propagate.

This is one of the **two** hand-coded DSL primitives ARBOR is permitted to
ship with. See ``CLAUDE.md §6.1`` and ``docs/INVARIANTS.md §1 F3``.
"""

from __future__ import annotations

from procedural_memory.DSL.apply import VALID_COLORS as _VALID_COLORS, register


@register("make_grid")
def make_grid(height, width, color):
    if not isinstance(height, int) or isinstance(height, bool) or height < 1:
        raise ValueError(f"make_grid: height must be a positive int; got {height!r}")
    if not isinstance(width, int) or isinstance(width, bool) or width < 1:
        raise ValueError(f"make_grid: width must be a positive int; got {width!r}")
    if not isinstance(color, int) or isinstance(color, bool) or color not in _VALID_COLORS:
        raise ValueError(
            f"make_grid: color must be int in 0..9 or 13 (transparent); got {color!r}"
        )
    return [[color for _ in range(width)] for _ in range(height)]
