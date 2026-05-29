"""
needs_descend — recognise module A's impasse-driven descent trigger.

This is the *recognition* half of module A (HierarchicalDescentController) for
Slice 1. ``docs/arbor_context/arbor-execution-trace.md`` module A names the two
halves to build:

    A. HierarchicalDescentController
       Trigger: (n_at_level == 1 ∨ all_results == COMM trivial ∨ DIFF 결과를
                 완화할 actionable DSL 부재) ∧ current_goal 달성 불가
       다음 액션: NeedsDescendRule 의 condition 구현 (5줄),
                  DescendOperator.effect (10줄)

This module is the first of those two — the ``NeedsDescendRule`` *condition*,
expressed as a registered recognition matcher (the recognition vocabulary is
allowed to grow by hand; CLAUDE.md §6.3). The ``DescendOperator.effect`` half
(where to descend, push_substate) edits ``agent/active_operators.py`` and so
rides with an anti-unification-side companion under F8 — that is a later iter's
smallest step, mirroring how module B's ``agent/goal.py`` was built library-first
in iter 33 and wired later.

Grounding in the raw prose (``arbor-flow-three-task-description.md``, easy000a
paragraph): at the PAIR level the agent compares grid_count, concludes the test
pair is missing a grid (its output), and forms goal B — *construct that missing
grid*. But "기본적으로 주어진 DSL 에는 pair.grid_count 를 올려주는 DSL 이 없어서
여기서 막혀" — neither frozen DSL primitive (``coloring`` / ``make_grid``) changes
a pair's grid_count, so the goal cannot be resolved at the PAIR level. That
impasse — *a goal is present but this level offers no resolving comparison* — is
exactly what triggers the descent to GRID ("Pair 에서 막히니까 Grid 로"). This is
principle P1 made operational: depth is entered **by necessity**, only when the
current level is blocked, never gratuitously.

The matcher recognises that impasse value-agnostically and *generically*: it
fires iff a **goal-bearing** condition is satisfied at the current level AND the
condition that would **resolve** that goal is *not* (yet) satisfiable from the
current level's patterns — so the resolving evidence must live a level deeper.
For Slice 1 the goal is ``test_output_missing`` (PAIR level: "there is a missing
output to construct") and the resolver is ``all_outputs_comm`` (GRID level: "the
output is the common example G1"). Driven with PAIR-only patterns the resolver
fails its min_evidence guard (no output-grid comparisons gathered yet) → descend;
once GRID-level comparisons are in hand the resolver fires → no further descent.
That makes descent *self-terminating* at the level that can answer the goal.

Strictly **value-agnostic** (SLICE_1_LOOP.md §9 / P7): it delegates entirely to
two value-agnostic sub-matchers and never reads a colour, coordinate, or count
*value* itself, so it fires identically for easy000a and easy000a2.

Scope note: this recogniser covers the goal-present-but-unresolved impasse (the
PAIR→GRID descent central to Slice 1's deciding flow). The other trigger disjunct
the exec-trace lists — ``n_at_level == 1`` at the TASK level ("task.property 는
이게 유일하기 때문에 … 비교할 수 없어 … 다음 단계는 깊이 들어가는거야": descend
because there is *nothing to compare*, no goal yet) — is a distinct recogniser
left for a future iter.
"""

from agent.conditions import register

# Slice-1 defaults: the PAIR-level goal and the GRID-level resolver (§3).
DEFAULT_GOAL_CONDITION = "test_output_missing"
DEFAULT_GOAL_PARAMS = {"min_evidence": 1}
DEFAULT_RESOLVING_CONDITION = "all_outputs_comm"
DEFAULT_RESOLVING_PARAMS = {
    "min_evidence": 1,
    "required_properties": ["size", "color", "contents"],
}


@register("needs_descend")
def match(patterns: dict, params: dict) -> bool:
    """True iff the current level is blocked on a goal it cannot resolve here.

    params:
      goal_condition     : name of the matcher recognising a goal-bearing
                           deficiency at this level (default
                           ``test_output_missing`` — a pair is missing its
                           output, so an output must be constructed).
      resolving_condition: name of the matcher recognising that the goal can be
                           *answered* from the current patterns (default
                           ``all_outputs_comm`` — the output is the common
                           example G1). Descent is needed precisely when this
                           does NOT yet hold.
      goal_params /
      resolving_params   : params forwarded to those sub-matchers (defaults are
                           the Slice-1 settings above).

    Semantics (P1 — necessity-driven descent):
      · No goal at this level  → return False (never descend gratuitously).
      · Goal present + already resolvable here → return False (the level can
        answer it; descend would be wasted depth — descent self-terminates).
      · Goal present + NOT resolvable here → return True (blocked; the resolving
        evidence lives a level deeper, so descend).

    Value-agnostic: it consults only the two sub-matchers' boolean verdicts,
    never an underlying value. ``conditions`` is imported lazily so the registry
    package can finish loading this module during its decorator sweep.
    """
    from agent import conditions

    goal = params.get("goal_condition", DEFAULT_GOAL_CONDITION)
    resolving = params.get("resolving_condition", DEFAULT_RESOLVING_CONDITION)
    goal_params = params.get("goal_params", DEFAULT_GOAL_PARAMS)
    resolving_params = params.get("resolving_params", DEFAULT_RESOLVING_PARAMS)

    # A goal must exist at this level for descent to be warranted.
    if not conditions.match(goal, patterns, goal_params):
        return False

    # Descend iff this level cannot yet resolve that goal.
    return not conditions.match(resolving, patterns, resolving_params)
