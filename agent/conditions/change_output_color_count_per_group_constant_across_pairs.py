"""
change_output_color_count_per_group_constant_across_pairs -- match tasks
where every change group in every example pair has the SAME number of
distinct output colours K (i.e. ``len(group["output_colors"]) == K`` for
every group across every pair, with K a single integer determined by
the first observed group).

Recognition vocabulary axis: ``colour-content / per-group output-colour
cardinality constancy``. This is the per-group projection of iter 38
(``change_output_color_count_constant_across_pairs``, which inspects
the cardinality of the per-pair frozenset of group-level
``output_colors[0]`` values) and the output-side dual of iter 195
(``change_input_color_count_per_group_constant_across_pairs``, which
inspects ``len(group["input_colors"])``). It is also the per-group
output-colour-cardinality dual of iter 193
(``change_count_per_group_constant_across_pairs``, which inspects the
per-group ``cell_count`` field) -- a third named handle on the per-
group constancy sub-axis iter 193 opened.

Where iter 38 collapses each pair's groups into a per-pair output-
colour SET (assuming each group has exactly one output colour) and
compares set cardinalities cross-pair, this matcher inspects every
group's own ``len(output_colors)`` and demands constancy across every
group across every pair, regardless of how many output colours each
group spans. The two projections are not in a refinement relation: a
task where every group has the same ``len(output_colors)`` == K but
the per-pair output-colour set cardinalities differ (because pair 0's
groups span overlapping colour slices while pair 1's groups span
disjoint colour slices) fires this matcher and may reject iter 38 if
its strict per-group ``len == 1`` precondition is violated; conversely
a task where every per-pair output set has the same cardinality N
while per-group K varies fires iter 38 and rejects this matcher.

Refinement / orthogonality summary (universal-over-pairs / -groups
semantics):

  * Iter 13 (``identity_transformation``) -- every pair has zero
    groups. This matcher REJECTS the no-group case (fail-closed
    clause below) to keep its territory disjoint from iter 13 by
    construction. Mirrors iter 32 / 35 / 37 / 39 / 193 / 195's empty-
    group rejection.
  * Iter 18 (``output_color_uniform``) -- STRICT REFINEMENT of this
    matcher (pins K == 1 AND the single output colour identical
    across all groups in all pairs): every group has
    ``len(output_colors) == 1`` with the same colour ⟹ every group
    has the same ``len(output_colors)``. Converse fails: K == 2
    everywhere fires this matcher, iter 18 rejects (it requires
    K == 1).
  * Iter 14 (``input_color_uniform``) -- input-side dual of iter 18;
    orthogonal to this matcher (input-side vs output-side). CAN
    co-fire when both input AND output per-group cardinalities pin.
  * Iter 36 (``change_output_colors_constant_across_pairs``) --
    per-pair output-colour SET bit-identity. NOT in a refinement
    relation with this matcher in either direction: iter 36 can fire
    while per-group K varies within a pair (pair 0's group 0 spans
    ``{1, 2}`` and group 1 spans ``{1}``: per-pair set ``{1, 2}``;
    pair 1 has the same per-pair set ``{1, 2}`` even if its groups
    partition differently; iter 36 fires, this matcher rejects).
    Conversely this matcher can fire while iter 36 rejects (per-group
    K == 1 everywhere but the specific colours differ across pairs).
  * Iter 38 (``change_output_color_count_constant_across_pairs``) --
    per-pair output-colour-set CARDINALITY constancy. NOT in a
    refinement relation either way: iter 38 fires when the per-pair
    SET cardinality is constant AND every group has
    ``len(output_colors) == 1``; this matcher fires when every
    per-group cardinality is constant (no len-1 precondition).
    Orthogonality matrix:
      - iter 38 alone: per-pair set cardinality N constant but
        per-group K varies. Under iter 38's len-1 precondition this
        is impossible (every group is K==1 so this matcher would
        fire alongside). To get iter-38-alone we would need per-group
        K to vary while still satisfying iter 38's len-1
        precondition; this is unreachable. In practice iter 38 fires
        ⟹ every group has K==1 ⟹ this matcher fires (with K==1).
      - this matcher alone: per-group K constant at K>=2 (every
        group has K output colours). Iter 38 rejects (its len-1
        precondition fails).
      - both fire: every group has K==1 and per-pair output set
        cardinality is constant -- the iter-38 territory becomes a
        proper subset of this matcher under iter 38's precondition.
      - neither: per-group K varies AND iter 38's len-1
        precondition fails.
  * Iter 195 (``change_input_color_count_per_group_constant_across_
    pairs``) -- input-side dual on the same per-group cardinality
    axis. Orthogonal: input-side vs output-side. CAN co-fire (both
    input and output per-group cardinalities pin) or fire alone (per-
    group input cardinality varies but per-group output cardinality
    is constant, or vice versa).
  * Iter 193 (``change_count_per_group_constant_across_pairs``) --
    per-group CELL_COUNT constancy. Sibling on the per-group
    constancy sub-axis, distinct field (cell_count vs
    len(output_colors)). NOT in a refinement relation. CAN co-fire.
  * Iter 23 (``single_change_group_per_pair``), iter 24
    (``single_cell_change_per_pair``), iter 26
    (``multi_cell_change_group_per_pair``), iter 28
    (``multi_group_per_pair``) -- those pin group-count or cell-count
    per pair; this matcher pins per-group output-colour cardinality.
    Independent on every group-count partition; CAN co-fire.
  * Iter 32 (``change_count_constant_across_pairs``) -- per-pair
    TOTAL cell count constancy. Independent.
  * Iter 39 (``change_group_count_constant_across_pairs``) --
    per-pair group-count constancy. Independent.
  * Iter 1 (``grid_size_preserved``) / iter 17
    (``grid_size_changed``) / iter 20-21 / iter 33
    (``output_dimensions_multiple_of_input``) -- dimensional axes,
    orthogonal. CAN co-fire.
  * Every palette-axis matcher (iters 184-194) -- those inspect
    whole-grid palettes; this matcher inspects per-group
    ``output_colors``. CAN co-fire.

Why this matters for ARBOR's intended ruleset:

  * "Each blob produces K output colours" rule family: rules whose
    apply-time selection / colouring is derived from per-blob output-
    colour composition (e.g. "paint every blob into exactly two
    output colours"). The recognition-side prerequisite is a named
    handle for "per-group output-colour cardinality is the same K
    across every group across every pair." Without it, anti-
    unification (CLAUDE.md §8) has no ``condition.type`` to attach
    a per-group output-colour-cardinality generalisation variable to.
  * Closes the per-group output-colour-cardinality leg on the per-
    group constancy sub-axis iter 193 opened and iter 195 extended.
    Iter 193 named the per-group cell-count handle (cardinality of
    the position set); iter 195 named the per-group input-colour-
    cardinality handle (cardinality of the input-colour set); this
    matcher names the per-group OUTPUT-colour-cardinality handle
    (cardinality of the output-colour set). Iter 195 + this iter are
    duals on the per-group cardinality axis exactly as iter 14 / 18
    are duals on the per-group uniformity axis.

Params:
  (none) -- pure cross-pair / cross-group constancy check on the
  derived integer ``len(group["output_colors"])`` for every group in
  every pair.

Returns True iff:
  - ``patterns`` is a dict, AND
  - ``patterns["pair_analyses"]`` is a non-empty list, AND
  - every analysis is a dict, AND
  - every analysis has a non-empty ``groups`` list (identity-
    territory rejection), AND
  - every group is a dict with a list-typed ``output_colors`` field
    whose length is at least 1 (the colour list cannot be empty;
    an empty colour list would mean the group has zero cells, an
    extractor contract violation), AND
  - every entry of ``output_colors`` is a strict int in
    ``range(10)`` (bool rejected per iter-13 / 14 / 17 / 18 / 19 /
    22 / 23 / 24 / 26 / 28 / 30 / 32 / 33 / 34 / 35 / 36 / 37 / 38 /
    39 / 184-195 strict-type posture; out-of-range rejected as
    upstream extractor breakage), AND
  - every group's ``len(output_colors)`` is bit-identical to the
    first group's ``len(output_colors)``.

Why fail-closed on empty / no-group / malformed (same posture as
iters 30 / 32 / 33 / 34 / 35 / 36 / 37 / 38 / 39 / 184-195): a
missing or zero-group pair is upstream extractor breakage or
identity-territory; a constancy claim with zero observations is
meaningless and would double-cover iter 13.

Why ``output_colors`` is required to be a non-empty list per group
(``len >= 1``): a connected change group has at least one cell;
each cell has an output colour; the per-group ``output_colors``
field is the sorted set of those colours, which is non-empty for
any non-empty group. A zero-length ``output_colors`` is an
extractor contract violation, not a valid K==0 case.

Why strict per-colour validation (bool rejected, range checked):
``output_colors`` carries small ints in [0, 9]; the matcher
performs the same strict-type gating as iter 14 / 18 / 19 / 34 /
35 / 36 / 37 / 38 / 184-195 to keep contract violations from
silently passing. The actual constancy check is on
``len(output_colors)``, not on the colours themselves, so cross-
pair colour identity is NOT required.

No companion-touch required: ``output_colors`` has been emitted
per group since iter 1 (``_analyze_pair`` in
``agent/active_operators.py``); this iter is a pure matcher
addition with no ``agent/active_operators.py`` diff. F8 inert.
"""

from __future__ import annotations

from agent.conditions import register


def _is_strict_color(x) -> bool:
    return (
        isinstance(x, int)
        and not isinstance(x, bool)
        and 0 <= x <= 9
    )


@register("change_output_color_count_per_group_constant_across_pairs")
def match(patterns: dict, params: dict) -> bool:
    if not isinstance(patterns, dict):
        return False
    pair_analyses = patterns.get("pair_analyses")
    if not isinstance(pair_analyses, list) or not pair_analyses:
        return False

    canonical_card: int | None = None

    for analysis in pair_analyses:
        if not isinstance(analysis, dict):
            return False
        groups = analysis.get("groups")
        if not isinstance(groups, list) or not groups:
            return False
        for group in groups:
            if not isinstance(group, dict):
                return False
            output_colors = group.get("output_colors")
            if not isinstance(output_colors, list) or len(output_colors) < 1:
                return False
            for oc in output_colors:
                if not _is_strict_color(oc):
                    return False
            cardinality = len(output_colors)
            if canonical_card is None:
                canonical_card = cardinality
            elif canonical_card != cardinality:
                return False

    return canonical_card is not None
