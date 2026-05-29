"""
copy_common_output_applies — the single Slice-1 copy-common-output recogniser.

Before this matcher, the two-step recognition the easy000a / easy000a2 mechanism
leans on (SLICE_1_LOOP.md §3) was **hand-inlined identically in two places**: the
slow path (``GeneralizeOperator._recognizes_copy_common_output``) and the fast
path (``ActiveSoarAgent._reuse_copy_common_output``) each computed the same
``test_output_missing`` ∧ ``all_outputs_comm`` conjunction. That duplicated the
*recognition of one mechanism* across two modules — the uniformity smell
SLICE_1_LOOP.md §8 criterion 2 names (같은 종류 작업이 같은 모듈로). This matcher is
that conjunction, named once, so discovery and reuse recognise the mechanism
through one routine:

  1. test_output_missing (PAIR level): the test pair carries input only, so its
     output must be *constructed* (arbor-flow easy000a paragraph; §3 PAIR step).
  2. schema_goal_satisfied (GRID level): module B's schema goal "construct Gx" is
     satisfied property-by-property — each of {size, color, contents} has a
     comparison basis (the role-aligned Inter-Grid comparison of the example
     outputs is COMM on that property), so the test output is that common G1 —
     copied, not computed (§3 ②, the deciding comparison).

The GRID half used to recompute ``all_outputs_comm`` directly here, independently
of the goal module B records each solve. Iter 47 routes it through
``schema_goal_satisfied`` instead, so the answer is recognised *because the goal
of constructing Gx is satisfied* (SLICE_1_LOOP.md §3 lines 121-126 — 정답에는
근거가 있어야 하고, 근거는 비교의 결과에서 나온다), not by a standalone all-COMM check
that never touched the goal. This is the wiring half of module B: a previously
passive episode-trace artifact now participates in the live recognition.

This matcher *is* the self-describing ``condition.type`` of the stored
copy-common-output rule (``procedural_memory/rule_003.json``), so both routes
that recognise the mechanism resolve it the same way: the slow path
(``GeneralizeOperator``) calls it by name, and the fast path
(``ActiveSoarAgent._reuse_copy_common_output``) dispatches the rule's own
``condition.type`` — which now *is* this composite (CLAUDE.md §5.2: the fast
path matches patterns against the rule's condition, no wrapping). Both therefore
make module B participate in the live solve through one route.

Strictly **value-agnostic** (SLICE_1_LOOP.md §9 / P7): both sub-matchers read
only COMM/DIFF verdicts and structural grid counts, never a colour or coordinate
value. It therefore fires identically for easy000a (fixed red output) and
easy000a2 (fixed green output) and can never hard-code an answer.
"""

from agent import conditions
from agent.conditions import register


@register("copy_common_output_applies")
def match(patterns: dict, params: dict) -> bool:
    """True iff the Slice-1 copy-common-output mechanism applies.

    patterns: must carry both ``pair_grid_counts`` (PAIR census, for
      test_output_missing *and* module B's value goal) and
      ``output_grid_comparisons`` (Inter-Grid receipts, for the GRID-level
      schema-goal grounding). Both ``compare_scheduler.build_patterns`` and
      ``patterns_from_cycle_receipts`` supply these, so the matcher works on the
      fast-path and slow-path patterns alike.
    params:
      min_evidence : minimum example evidence for the PAIR ``test_output_missing``
                     trigger (default 1). The GRID half is grounded by module B
                     at its own per-property evidence level.
    """
    if not patterns:
        return False
    min_evidence = params.get("min_evidence", 1)

    if not conditions.match("test_output_missing", patterns,
                            {"min_evidence": min_evidence}):
        return False
    return conditions.match("schema_goal_satisfied", patterns, {})
