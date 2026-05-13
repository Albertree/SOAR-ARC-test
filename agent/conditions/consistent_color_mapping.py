"""
consistent_color_mapping — match tasks where every changed cell's input
color maps to a single, unambiguous output color across all example pairs.

This is the recognition counterpart to the pipeline's `_try_color_mapping`
strategy: the detector there returns a rule iff every observed input
color in the changed-cell groups appears with exactly one output color.
The matcher surfaces that same precondition as a named entry in the
condition registry, so once anti-unification produces a `coloring`-based
composition that encodes such a remap, the resulting §1-schema rule can
declare ``condition.type = "consistent_color_mapping"``.

Distinct from `grid_size_preserved`:
  * `grid_size_preserved` is a dimensional precondition (input.h×w ==
    output.h×w). It says nothing about color content.
  * `consistent_color_mapping` is a color-content precondition. It only
    inspects color values in changed-cell groups and is dimension-agnostic
    (though in practice most tasks satisfying it also satisfy the size
    precondition, the matcher does *not* require it — that coupling
    belongs in the rule's choice of `min_evidence` or in a separate
    matcher).

Params:
  (none) — the detected mapping is data carried in `action.args`, not in
  `condition.params`. The matcher is a pure existence/uniqueness check.

Returns True iff:
  - `patterns["pair_analyses"]` is a non-empty list, AND
  - At least one (input_color, output_color) pair is observed in some
    group, AND
  - Every observed input color has exactly one observed output color
    across the union of all pairs' groups.

Empty changed-cell sets (identity-like pairs with zero change groups)
return False — there is no mapping to recognise, and an identity case is
properly handled by a separate matcher (TBD), not by misreporting this
one.
"""

from agent.conditions import register


@register("consistent_color_mapping")
def match(patterns: dict, params: dict) -> bool:
    if not isinstance(patterns, dict):
        return False
    pair_analyses = patterns.get("pair_analyses") or []
    if not pair_analyses:
        return False

    color_map: dict = {}
    for analysis in pair_analyses:
        if not isinstance(analysis, dict):
            return False
        groups = analysis.get("groups") or []
        for g in groups:
            if not isinstance(g, dict):
                return False
            input_colors = g.get("input_colors") or []
            output_colors = g.get("output_colors") or []
            for ic in input_colors:
                for oc in output_colors:
                    color_map.setdefault(ic, set()).add(oc)

    if not color_map:
        return False
    return all(len(v) == 1 for v in color_map.values())
