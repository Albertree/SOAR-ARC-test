"""
descent_warranted — module A's *unified* descent-trigger recogniser.

``docs/arbor_context/arbor-execution-trace.md`` module A
(HierarchicalDescentController) names the descent trigger as a **disjunction**
gated by an unmet goal:

    Trigger: (n_at_level == 1 ∨ all_results == COMM trivial ∨ DIFF 결과를
              완화할 actionable DSL 부재) ∧ current_goal 달성 불가

Iters 34/35 built the two recognisers for the disjuncts Slice 1 exercises:
  · `nothing_to_compare` — the first disjunct (``n_at_level == 1``): fewer than
    two siblings here, so no comparison (hence no goal) can even begin. The §3
    ``[TASK level]`` descent — goal-free.
  · `needs_descend`      — the right-conjunct's central case: a goal *is* present
    but this level cannot resolve it. The §3 PAIR→GRID descent.

Those are level-specific shards. What module A's `DescendOperator` actually needs
to decide is a *single* boolean: **"does the current level warrant a descent?"**
— the whole trigger disjunction evaluated at the current focus level. This
matcher is that composition: it ORs the (level-appropriate) disjuncts, so one
call answers the descend decision for whichever level the flow is on.

  · TASK level:  no goal yet, one task node → `nothing_to_compare` fires → descend.
  · PAIR level:  goal present (test output missing) but unresolvable here →
                 `needs_descend` fires → descend.
  · GRID level:  the level can answer the goal (`all_outputs_comm`) and has
                 siblings → neither disjunct fires → **no** descend. Descent is
                 therefore self-terminating at the level that resolves the goal
                 (P1: depth entered strictly by necessity, never gratuitously).

It is strictly **value-agnostic** (SLICE_1_LOOP.md §9 / P7): it delegates wholly
to the two value-agnostic sub-matchers and never reads a colour, coordinate, or
count *value* itself, so it fires identically for easy000a and easy000a2.

This is a library (recognition vocabulary, CLAUDE.md §6.3). Wiring it into
`DescendOperator.precondition`/`effect` — which edits `agent/active_operators.py`
and so adds net lines (F8) — is the next iter's smallest step, mirroring how
`agent/goal.py` and the two trigger recognisers were built library-first and
wired later.
"""

from agent.conditions import register

# The trigger disjuncts Slice 1 exercises, in the order they arise as the flow
# descends. `nothing_to_compare` is parameterised by the current level; both are
# value-agnostic.
DEFAULT_NOTHING_TO_COMPARE = "nothing_to_compare"
DEFAULT_NEEDS_DESCEND = "needs_descend"


@register("descent_warranted")
def match(patterns: dict, params: dict) -> bool:
    """True iff the current level warrants a descent (module A trigger disjunction).

    params:
      level                      : current focus level, forwarded to the
                                   ``nothing_to_compare`` disjunct so it inspects
                                   *this* level's sibling census (default
                                   ``"task"`` — the first level the §3 flow
                                   descends from).
      nothing_to_compare_params  : extra params for the ``nothing_to_compare``
                                   disjunct (``level`` is injected from ``level``
                                   above unless overridden here).
      needs_descend_params       : params for the ``needs_descend`` disjunct
                                   (defaults are its own Slice-1 settings).

    Semantics (P1 — necessity-driven descent):
      Descend iff *either* disjunct holds at the current level —
        · nothing to compare here (goal-free, < 2 siblings), OR
        · a goal is present but this level cannot resolve it.
      When neither holds (the level has siblings *and* can answer its goal),
      return False: the level is productive, so descent would be wasted depth.

    Value-agnostic and fail-closed: it consults only the two sub-matchers'
    boolean verdicts. ``conditions`` is imported lazily so the registry package
    can finish loading this module during its decorator sweep.
    """
    from agent import conditions

    level = params.get("level", "task")

    nc_params = dict(params.get("nothing_to_compare_params", {}))
    nc_params.setdefault("level", level)
    if conditions.match(DEFAULT_NOTHING_TO_COMPARE, patterns, nc_params):
        return True

    nd_params = params.get("needs_descend_params", {})
    if conditions.match(DEFAULT_NEEDS_DESCEND, patterns, nd_params):
        return True

    return False
