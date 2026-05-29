"""
schema_goal_satisfied — module B's evolving goal made a live recognition predicate.

This is the *wiring* half of module B (``agent/goal.py``). Iter 46 extracted the
Slice-1 goal walk into module B as a reusable library
(``build_goalstack_from_census`` + ``mark_schema_leaves_by_comparison``) but left
it consumed only by the passive episode trace (``ActiveSoarAgent
._slice1_goal_record``). The recognition path that actually *decides the answer*
still recomputed the GRID-half ``all_outputs_comm`` on its own, independently of
the goal — so the schema goal was recorded but never *believed*.

This matcher makes the schema goal's satisfaction the GRID-level recognition
basis (SLICE_1_LOOP.md §3 lines 121-126, P3/P4 — 정답에는 근거가 있어야 하고, 근거는
비교의 결과에서 나온다). It:

  1. forms the PAIR-level value goal from the grid-count census and evolves it
     (Refinement → Decomposition) to the schema goal {size, color, contents}
     (``build_goalstack_from_census``); ``None`` (no deficient test pair) → no
     goal to satisfy → False;
  2. marks each schema leaf solved iff the role-aligned Inter-Grid comparison of
     the example outputs is COMM on that single property
     (``mark_schema_leaves_by_comparison``);
  3. returns whether the schema goal ``is_satisfied()`` — every property of the
     grid to construct has a comparison basis.

So "the test output is the common example G1" is now recognised *because the
goal of constructing Gx is satisfied property-by-property*, not by a standalone
all-COMM check that never touched the goal. ``copy_common_output_applies``
consumes this as its GRID half, so both the slow path (``GeneralizeOperator``)
and the fast path (``ActiveSoarAgent._reuse_copy_common_output``) — which both
resolve through that composite — now make module B participate in the live solve.

Strictly **value-agnostic** (SLICE_1_LOOP.md §9 / P7): module B is driven by the
structural census and ``all_outputs_comm`` reads only COMM/DIFF verdicts, never a
colour or coordinate value. It therefore fires identically for easy000a (fixed
red output) and easy000a2 (fixed green output) and can never hard-code an answer.
"""

from agent.conditions import register
from agent import goal as goal_module


@register("schema_goal_satisfied")
def match(patterns: dict, params: dict) -> bool:
    """True iff module B's schema goal is satisfied on these patterns.

    patterns: must carry ``pair_grid_counts`` (PAIR census, to form the value
      goal) and ``output_grid_comparisons`` (Inter-Grid receipts, to mark the
      schema leaves by comparison). Both ``compare_scheduler.build_patterns`` and
      ``patterns_from_cycle_receipts`` supply these, so the matcher works on the
      fast-path and slow-path patterns alike.
    params: unused here — module B grounds each schema leaf at its own evidence
      level (one COMM example-output comparison per property). Accepted for the
      uniform ``match(patterns, params)`` matcher signature.
    """
    if not patterns:
        return False
    census = patterns.get("pair_grid_counts")
    stack = goal_module.build_goalstack_from_census(census)
    if stack is None:
        return False
    goal_module.mark_schema_leaves_by_comparison(stack, patterns)
    return stack.is_satisfied()
