"""
agent.dsl_expr — the *argument / selection* vocabulary (the growing LHS).

BACKLOG_LOOP.md §2.5 splits the DSL into two faces that grow at different rates:

  * **transformation (RHS / action)** — frozen forever at two primitives,
    `make_grid` and `coloring` (`procedural_memory/DSL/`, INVARIANTS F3).
  * **property / relation / util / selection (LHS / arguments)** — the vocabulary
    that *names what a transformation acts on*. This is allowed and **must** grow
    (arbor-dsl-taxonomy §3), and — to stay clear of the F3 checker, which reverts
    new `def`/`@register` under `procedural_memory/DSL/` — it lives here under
    `agent/`, not in the transformation directory (§2.5-1).

These functions are the material anti-unification (R3) lifts: a raw coordinate
`coloring([(2,3)], 4)` has no common skeleton across tasks, but the same call
written `coloring(position_of(unique_object(in)), color_of(unique_object(in)))`
does. Selection/argument expressions are what make that lift possible
(§2.5-2b). They are deterministic and side-effect-free.
"""

from agent.dsl_expr.selection import (
    background_of,
    objects_of,
    unique_object,
    select_object,
    fit_selector,
    position_of,
    bottom_right_of,
    color_of,
    cells_of,
)
from agent.dsl_expr.motion import (
    fit_target,
    fit_uniform_target,
    fit_map_all_target,
    target_position,
    fit_output_shape,
    output_shape,
    obj_origin_extent,
)
from agent.dsl_expr.recolor import (
    fit_color_source,
    color_source,
)
from agent.dsl_expr import ranking

__all__ = [
    "background_of",
    "objects_of",
    "unique_object",
    "select_object",
    "fit_selector",
    "position_of",
    "bottom_right_of",
    "color_of",
    "cells_of",
    "fit_target",
    "fit_uniform_target",
    "fit_map_all_target",
    "target_position",
    "fit_output_shape",
    "output_shape",
    "obj_origin_extent",
    "fit_color_source",
    "color_source",
    "ranking",
]
