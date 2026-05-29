"""
nothing_to_compare — recognise module A's *no-goal* descent trigger.

This is the second of module A's (HierarchicalDescentController) recognition
matchers for Slice 1. ``docs/arbor_context/arbor-execution-trace.md`` module A
names the descent trigger as a disjunction:

    Trigger: (n_at_level == 1 ∨ all_results == COMM trivial ∨ DIFF 결과를
              완화할 actionable DSL 부재) ∧ current_goal 달성 불가

The iter-34 `needs_descend` matcher covers the right conjunct's central case —
*a goal is present but this level cannot resolve it* (the PAIR→GRID descent).
This matcher covers the **first disjunct, ``n_at_level == 1``**, which is a
*distinct trigger shape*: there is **no goal yet** — the level is blocked simply
because there is *nothing to compare* there.

Grounding in the raw prose (``arbor-flow-three-task-description.md``, easy000a
paragraph) and SLICE_1_LOOP.md §3's ``[TASK level]`` step:

    task.property = pair-count (example=2, test=1) 확인
    형제 TASK 없음 → Inter 비교 대상 0 → 비교 자연 skip (P1: 비교할 게 없음)
    → descend (PAIR 로)

The working memory holds a single loaded task with no sibling tasks, so the TASK
level has only one node — pairwise comparison (P6: 2-at-a-time) is impossible,
there is nothing to compare, and the flow descends to PAIR *before* any goal can
form. That is the necessity-driven descent of P1 in its earliest, goal-free
form: depth is entered because the current level offers no work, not because a
goal went unresolved.

Distinct from `needs_descend`:
  · `needs_descend`      — goal present, level can't resolve it (right conjunct).
  · `nothing_to_compare` — fewer than 2 siblings here, so no comparison (hence no
                           goal) can even begin (first disjunct, n_at_level==1).

Strictly **value-agnostic** (SLICE_1_LOOP.md §9 / P7): it reads only a structural
sibling *count*, never a colour, coordinate, or property *value*, so it fires
identically for easy000a and easy000a2. Produced by
`agent/compare_scheduler.py:level_sibling_counts()`.
"""

from agent.conditions import register


@register("nothing_to_compare")
def match(patterns: dict, params: dict) -> bool:
    """True iff the current level has too few siblings to compare → descend.

    patterns:
      level_sibling_counts : {"task": int, "pair": int, ...} — structural census
                             of how many sibling nodes sit at each level for
                             pairwise comparison (value-agnostic counts only).
    params:
      level          : which level's count to inspect (default ``"task"`` — the
                       §3 ``[TASK level]`` n_at_level==1 step).
      min_to_compare : minimum siblings needed for a pairwise comparison
                       (default 2; P6 is strictly 2-at-a-time, so < 2 means
                       nothing to compare).

    Semantics (P1 — necessity-driven descent, goal-free form):
      · count >= min_to_compare → False (the level has siblings to compare;
        descend would be wasted depth).
      · count <  min_to_compare → True  (nothing to compare here; the next
        comparison can only happen a level deeper, so descend).

    Fail-closed on anything malformed (missing census / non-int count). The
    count key is configurable so the same recogniser serves any level whose
    sibling census is exposed.
    """
    census = patterns.get("level_sibling_counts")
    if not isinstance(census, dict):
        return False

    level = params.get("level", "task")
    min_to_compare = params.get("min_to_compare", 2)

    count = census.get(level)
    if not isinstance(count, int) or isinstance(count, bool):
        return False

    return count < min_to_compare
