"""
output_color_uniform -- match tasks where every changed cell across every
example pair ends up painted the SAME single output colour.

This names the recognition precondition for the simplest possible
``coloring``-action rule shape: ``action = {"dsl": "coloring", "args":
{"selection": <some selection>, "color": K}}`` where ``K`` is a single
integer constant rather than a per-input-colour mapping. The frozen
``coloring`` primitive's signature (``coloring(grid, selection, color)``)
takes a *single* ``color`` argument -- when the matcher fires, that
argument's value is determinable from the data without needing
polymorphic ``args`` (the iter-16 "consistent_color_mapping needs N
coloring calls" caveat that has been gating
``translate_to_schema``'s broadening into the colour-mapping branch).

Relation to existing matchers:

  * ``consistent_color_mapping`` (iter 8) fires whenever every observed
    input colour maps to a single output colour, allowing multiple
    distinct (in, out) pairs (e.g. ``0->3, 5->7``). Schema-wise it
    requires N coloring calls for N input colours.
  * ``output_color_uniform`` (iter 18) is a *strict refinement*: it
    additionally requires the output side to collapse to a single
    constant across ALL groups in ALL pairs. Whenever
    ``output_color_uniform`` fires, ``consistent_color_mapping`` also
    fires (any input colour observed maps to the same single output
    colour, so it is still a 1:1 mapping). The converse is not true.
  * ``sequential_recoloring`` (iter 10) requires outputs to form a
    contiguous integer range with at least two distinct values. It is
    mutually exclusive with ``output_color_uniform`` (cardinality >= 2
    vs cardinality == 1 on the output side).
  * ``identity_transformation`` (iter 13) requires zero changed cells.
    ``output_color_uniform`` requires at least one. They are mutually
    exclusive.
  * Orthogonal to the dimensional axis (``grid_size_preserved`` /
    ``grid_size_changed``): a uniform repaint can happen on a same-size
    grid (paint the changed selection one colour) OR on a
    dimension-changed grid (the overlap region's change groups all
    paint the same colour, even if the output is bigger -- the matcher
    inspects change groups, not dimensions).

The point of *this* matcher rather than another generic colour matcher:
it bridges the recognition vocabulary directly to the calling
convention of the first frozen DSL primitive. ``coloring`` takes a
single ``color`` int; ``output_color_uniform`` is exactly the
precondition under which that int is determinable from training data.

Params:
  (none)

Returns True iff:
  - ``patterns`` is a dict, AND
  - ``patterns["pair_analyses"]`` is a non-empty list, AND
  - every analysis is a dict, AND
  - every analysis has at least one change group
    (``len(groups) >= 1``), AND
  - every group has exactly one entry in its ``output_colors`` list
    (``len(output_colors) == 1``), AND
  - all single output colours across all groups in all pairs are
    bit-identical (``len(set(observed)) == 1``).

Why non-empty groups required: with zero change groups the output
colour set is empty and "uniform single colour" is vacuously true --
but that case is identity, which has its own iter-13 matcher. Failing
closed here keeps the two matchers strictly mutually exclusive.

Why strict bit-identity rather than set-of-one collapse: the output
colour is read as the FIRST (and only) entry of ``output_colors``; the
field is a sorted list of small ints emitted by
``ExtractPatternOperator._analyze_pair`` (the standard shape). Strict
equality across pairs forecloses "every pair has SOME single colour
but they differ" -- e.g. pair 0 paints red, pair 1 paints blue -- which
is NOT a uniform-paint task. Such a case still fires
``consistent_color_mapping`` (per-input mapping) but specifically not
``output_color_uniform``.

Why fail-closed on malformed groups: the matcher's contract is
``deterministic and side-effect-free`` (docs/RULE_FORMAT.md §4); a
missing or non-list ``output_colors`` is upstream extractor breakage,
not evidence that the precondition holds.
"""

from __future__ import annotations

from agent.conditions import register


@register("output_color_uniform")
def match(patterns: dict, params: dict) -> bool:
    if not isinstance(patterns, dict):
        return False
    pair_analyses = patterns.get("pair_analyses")
    if not isinstance(pair_analyses, list) or not pair_analyses:
        return False

    observed_output_colors = set()
    for analysis in pair_analyses:
        if not isinstance(analysis, dict):
            return False
        groups = analysis.get("groups")
        if not isinstance(groups, list) or len(groups) == 0:
            return False
        for group in groups:
            if not isinstance(group, dict):
                return False
            out_colors = group.get("output_colors")
            if not isinstance(out_colors, list) or len(out_colors) != 1:
                return False
            observed_output_colors.add(out_colors[0])
            if len(observed_output_colors) > 1:
                return False
    return len(observed_output_colors) == 1
