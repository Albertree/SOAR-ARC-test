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
  2. all_outputs_comm (GRID level): the role-aligned Inter-Grid comparison of the
     example outputs is COMM on {size, color, contents}, so the test output is
     that common G1 — copied, not computed (§3 ②, the deciding comparison).

The GRID-level sub-matcher defaults to ``all_outputs_comm`` but is overridable
via the ``grid_matcher`` param, so the fast path can drive it from the stored
rule's own ``condition.type`` (CLAUDE.md §5.2: the fast path matches patterns
against the rule's condition) rather than a literal name.

Strictly **value-agnostic** (SLICE_1_LOOP.md §9 / P7): both sub-matchers read
only COMM/DIFF verdicts and structural grid counts, never a colour or coordinate
value. It therefore fires identically for easy000a (fixed red output) and
easy000a2 (fixed green output) and can never hard-code an answer.
"""

from agent import conditions
from agent.conditions import register

# Module-D grid schema property keys the deciding Inter-Grid comparison must be
# COMM on (ARCKG/grid.py:to_json). Property *names* only — value-agnostic.
_GRID_PROPERTIES = ("size", "color", "contents")


@register("copy_common_output_applies")
def match(patterns: dict, params: dict) -> bool:
    """True iff the Slice-1 copy-common-output mechanism applies.

    patterns: must carry both ``pair_grid_counts`` (PAIR census, for
      test_output_missing) and ``output_grid_comparisons`` (Inter-Grid receipts,
      for the GRID matcher). Both ``compare_scheduler.build_patterns`` and
      ``patterns_from_cycle_receipts`` supply these, so the matcher works on the
      fast-path and slow-path patterns alike.
    params:
      min_evidence       : minimum evidence for *both* sub-matchers (default 1).
      grid_matcher       : registered GRID-level recogniser name to compose with
                           (default ``"all_outputs_comm"``); lets the fast path
                           pass the stored rule's ``condition.type``.
      required_properties: property names the GRID matcher must each find COMM
                           (default {size, color, contents}).
    """
    if not patterns:
        return False
    min_evidence = params.get("min_evidence", 1)
    grid_matcher = params.get("grid_matcher") or "all_outputs_comm"
    required = list(params.get("required_properties") or _GRID_PROPERTIES)

    if not conditions.match("test_output_missing", patterns,
                            {"min_evidence": min_evidence}):
        return False
    return bool(
        conditions.match(
            grid_matcher, patterns,
            {"min_evidence": min_evidence, "required_properties": required},
        )
    )
