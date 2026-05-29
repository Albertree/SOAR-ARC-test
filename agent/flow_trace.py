"""
flow_trace — module C observability: the §3 comparison-flow *form*, recorded.

SLICE_1_LOOP.md §3 lays out the comparison sequence the easy000a solve should
*pass through* — and is explicit (lines 130-133) that only the last step decides
the answer while the others are traversed "흐름상 거쳐가지만 정답엔 직접 기여 안 함"
(passed through for the flow's sake, contributing nothing to the answer):

    [PAIR]  Inter-Pair, grid-count, pairwise   -> consensus 2 + dissent 1
    [GRID]  Intra-Pair, G0↔G1                  -> DIFF (input vs output)
    [GRID]  Inter-Grid, role==G0               -> DIFF (the contrast inputs)
    [GRID]  Inter-Grid, role==G1               -> COMM on {size,color,contents}  ★ decisive

``agent/compare_scheduler.build_patterns`` already documents the one-to-one map
from each scheduled comparison family to the matcher that recognises it
(lines 379-383). Until now those recognisers had *no live consumer*: three of
them (``pair_grid_count_majority``, ``intra_pair_grids_differ``, ``inputs_vary``)
named the non-decisive §3 steps but fired only in their unit tests, while the
episode trace recorded the module-B goal walk and the answer — never *that the
solve traversed the §3 form*. Criterion 3 (SLICE_1_LOOP.md §8 — 접근성: 풀이가
정답 방향으로 간다) was therefore unobservable on the live solve.

``slice1_flow_steps`` is that consumer. It runs each §3 recogniser over the live
``patterns`` bundle and returns a symbolic record of which steps the comparison
flow exhibited, in §3 order, flagging the single decisive one. The episode trace
(``ActiveSoarAgent._record_episode``) appends it, so every solve now shows the
*shape of its comparison flow*, not just its goal evolution and final grid — the
same way ``agent/goal.py`` made module B's goal walk observable.

This records the form; it does not change the answer (the decision still flows
through ``copy_common_output_applies`` = ``test_output_missing`` ∧
``schema_goal_satisfied``). Strictly **value-agnostic** (SLICE_1_LOOP.md §9 / P7):
every recogniser reads only COMM/DIFF verdicts and structural grid counts, never
a colour or coordinate value, so easy000a (red) and easy000a2 (green) produce an
identical flow record. The result is a plain JSON-serialisable dict (P7).
"""

from __future__ import annotations


# The §3 comparison-flow steps, in the order the raw prose walks them. Each entry
# names a recognition matcher (agent/conditions/) and the params it is judged at,
# mirroring the slot->matcher map in compare_scheduler.build_patterns. ``decisive``
# marks the single step the answer actually rests on (the role==G1 all-COMM);
# the rest are traversed for the flow's sake (§3 lines 130-133).
_SLICE1_FLOW_STEPS = (
    {
        "step": "pair_grid_count_majority",
        "level": "PAIR",
        "kind": "Inter-Pair",
        "role": None,
        "expect": "consensus+dissent",
        "decisive": False,
        "params": {"min_evidence": 2},
    },
    {
        "step": "intra_pair_grids_differ",
        "level": "GRID",
        "kind": "Intra-Pair",
        "role": None,
        "expect": "DIFF",
        "decisive": False,
        "params": {"min_evidence": 1},
    },
    {
        "step": "inputs_vary",
        "level": "GRID",
        "kind": "Inter-Grid",
        "role": "G0",
        "expect": "DIFF",
        "decisive": False,
        "params": {"min_evidence": 1},
    },
    {
        "step": "all_outputs_comm",
        "level": "GRID",
        "kind": "Inter-Grid",
        "role": "G1",
        "expect": "COMM",
        "decisive": True,
        "params": {"min_evidence": 1, "required_properties": ["size", "color", "contents"]},
    },
)


def slice1_flow_steps(patterns: dict) -> dict:
    """Record which §3 comparison-flow steps the live ``patterns`` exhibit.

    patterns: an ``agent/compare_scheduler.build_patterns`` bundle — the same
      dict the recognition matchers consume. Each step's matcher reads its own
      slot (``pair_grid_count_comparisons`` / ``intra_pair_grid_comparisons`` /
      ``input_grid_comparisons`` / ``output_grid_comparisons``); a missing slot
      makes that step ``recognised: False`` rather than raising.

    Returns a symbolic, JSON-serialisable record (P7):

        {"phase": "comparison_flow", "module": "C",
         "steps": [{"step", "level", "kind", "role", "expect", "decisive",
                    "recognised"}, ...],
         "decisive_recognised": bool}

    ``decisive_recognised`` is the role==G1 all-COMM step — the one §3 says the
    answer rests on. The non-decisive steps are reported too, so the trace shows
    the *whole* flow form (criterion 3), not just the deciding comparison.

    Value-agnostic: delegates entirely to the COMM/DIFF-only recognisers.
    """
    from agent import conditions  # local: observability need not pull the
    # recognition registry in at module import time (mirrors agent/goal.py).

    steps = []
    decisive_recognised = False
    for spec in _SLICE1_FLOW_STEPS:
        recognised = bool(patterns) and conditions.match(
            spec["step"], patterns, dict(spec["params"])
        )
        if spec["decisive"]:
            decisive_recognised = recognised
        steps.append({
            "step": spec["step"],
            "level": spec["level"],
            "kind": spec["kind"],
            "role": spec["role"],
            "expect": spec["expect"],
            "decisive": spec["decisive"],
            "recognised": recognised,
        })

    return {
        "phase": "comparison_flow",
        "module": "C",
        "steps": steps,
        "decisive_recognised": decisive_recognised,
    }
