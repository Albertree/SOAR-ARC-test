"""
change_input_color_count_per_group_constant_across_pairs -- match tasks
where every change group in every example pair has the SAME number of
distinct input colours K (i.e. ``len(group["input_colors"]) == K`` for
every group across every pair, with K a single integer determined by
the first observed group).

Recognition vocabulary axis: ``colour-content / per-group input-colour
cardinality constancy``. This is the per-group projection of iter 37
(``change_input_color_count_constant_across_pairs``, which inspects
the cardinality of the per-pair UNION of group-level input colours)
and the per-group input-colour-cardinality dual of iter 193
(``change_count_per_group_constant_across_pairs``, which inspects the
per-group ``cell_count`` field).

Where iter 37 collapses each pair's groups into a per-pair set and
compares set cardinalities cross-pair, this matcher inspects every
group's own ``len(input_colors)`` and demands constancy across every
group across every pair. The two projections are not in a refinement
relation: a task where every pair has the same group count and every
group spans exactly K input colours but the per-pair UNION
cardinality differs (because pair 0's groups span overlapping colour
slices while pair 1's groups span disjoint colour slices) fires this
matcher and rejects iter 37; conversely a task where every pair's
union cardinality is the same N but groups have varying per-group K
fires iter 37 and rejects this matcher.

Refinement / orthogonality summary (universal-over-pairs / -groups
semantics):

  * Iter 13 (``identity_transformation``) -- every pair has zero
    groups. This matcher REJECTS the no-group case (fail-closed
    clause below) to keep its territory disjoint from iter 13 by
    construction. Mirrors iter 32 / 35 / 37 / 39 / 193's empty-group
    rejection.
  * Iter 14 (``input_color_uniform``) -- STRICT REFINEMENT of this
    matcher (pins K == 1 AND the single colour identical across all
    groups in all pairs): every group has ``len(input_colors) == 1``
    with the same colour ⟹ every group has the same
    ``len(input_colors)``. Converse fails: K == 2 everywhere fires
    this matcher, iter 14 rejects (it requires K == 1).
  * Iter 18 (``output_color_uniform``) -- output-side dual of iter
    14; orthogonal to this matcher (output-side vs input-side). CAN
    co-fire when both input AND output per-group cardinalities pin.
  * Iter 35 (``change_input_colors_constant_across_pairs``) --
    per-pair input-colour SET bit-identity. NOT in a refinement
    relation with this matcher in either direction: iter 35 can
    fire while per-group K varies within a pair (pair 0's group 0
    spans ``{1, 2}`` and group 1 spans ``{1}``: per-pair set is
    ``{1, 2}``; pair 1 has the same per-pair set ``{1, 2}`` even if
    its groups partition differently; iter 35 fires, this matcher
    rejects). Conversely this matcher can fire while iter 35
    rejects (per-group K == 1 everywhere but the specific colours
    differ across pairs).
  * Iter 37 (``change_input_color_count_constant_across_pairs``) --
    per-pair input-colour-set CARDINALITY constancy. NOT in a
    refinement relation either way: iter 37 fires when the per-pair
    UNION cardinality is constant; this matcher fires when every
    per-group cardinality is constant. With single-group pairs and
    constant per-group K, both fire; with multi-group pairs the two
    projections decouple. The orthogonality matrix is:
      - iter 37 alone: per-pair union cardinality N constant but
        per-group sizes vary (pair 0 has groups of size [1, 2],
        pair 1 has groups of size [3] -- per-pair union is {a, b,
        c} cardinality 3 on both if compositions align, but
        per-group sizes differ).
      - this matcher alone: per-group K constant but per-pair
        union cardinality differs (pair 0 has two K=1 groups of
        the same colour: union cardinality 1; pair 1 has two K=1
        groups of different colours: union cardinality 2).
      - both fire: e.g. every pair has one group of K=1 colours
        (union cardinality 1 on every pair, per-group K=1).
      - neither: per-group K varies AND per-pair union cardinality
        varies.
  * Iter 193 (``change_count_per_group_constant_across_pairs``) --
    per-group CELL_COUNT constancy. Sibling on the per-group
    constancy sub-axis, distinct field (cell_count vs
    len(input_colors)). NOT in a refinement relation. CAN co-fire.
  * Iter 23 (``single_change_group_per_pair``), iter 24
    (``single_cell_change_per_pair``), iter 26
    (``multi_cell_change_group_per_pair``), iter 28
    (``multi_group_per_pair``) -- those pin group-count or cell-count
    per pair; this matcher pins per-group input-colour cardinality.
    Independent on every group-count partition; CAN co-fire.
  * Iter 32 (``change_count_constant_across_pairs``) -- per-pair
    TOTAL cell count constancy. Independent.
  * Iter 39 (``change_group_count_constant_across_pairs``) --
    per-pair group-count constancy. Independent.
  * Iter 1 (``grid_size_preserved``) / iter 17
    (``grid_size_changed``) / iter 20-21 / iter 33
    (``output_dimensions_multiple_of_input``) -- dimensional axes,
    orthogonal. CAN co-fire.
  * Every palette-axis matcher (iters 184-192) -- those inspect
    whole-grid palettes; this matcher inspects per-group
    ``input_colors``. CAN co-fire.

Why this matters for ARBOR's intended ruleset:

  * "Each blob spans K input colours" rule family: rules whose
    apply-time selection is derived from per-blob input-colour
    composition (e.g. "paint every blob whose input spans exactly
    two colours"). The recognition-side prerequisite is a named
    handle for "per-group input-colour cardinality is the same K
    across every group across every pair." Without it, anti-
    unification (CLAUDE.md §8) has no ``condition.type`` to attach
    a per-group input-colour-cardinality generalisation variable to.
  * Closes the per-group input-colour-cardinality leg on the per-
    group constancy sub-axis iter 193 opened. Iter 193 named the
    per-group cell-count handle (the cardinality of the position
    set); this matcher names the per-group input-colour-cardinality
    handle (the cardinality of the input-colour set). The output-side
    symmetric handle is the natural next extension on the same sub-
    axis but is a distinct matcher.

Params:
  (none) -- pure cross-pair / cross-group constancy check on the
  derived integer ``len(group["input_colors"])`` for every group in
  every pair.

Returns True iff:
  - ``patterns`` is a dict, AND
  - ``patterns["pair_analyses"]`` is a non-empty list, AND
  - every analysis is a dict, AND
  - every analysis has a non-empty ``groups`` list (identity-
    territory rejection), AND
  - every group is a dict with a list-typed ``input_colors`` field
    whose length is at least 1 (the colour list cannot be empty;
    an empty colour list would mean the group has zero cells, an
    extractor contract violation), AND
  - every entry of ``input_colors`` is a strict int in ``range(10)``
    (bool rejected per iter-13 / 14 / 17 / 18 / 19 / 22 / 23 / 24 /
    26 / 28 / 30 / 32 / 33 / 34 / 35 / 36 / 37 / 38 / 39 / 184-193
    strict-type posture; out-of-range rejected as upstream
    extractor breakage), AND
  - every group's ``len(input_colors)`` is bit-identical to the
    first group's ``len(input_colors)``.

Why fail-closed on empty / no-group / malformed (same posture as
iters 30 / 32 / 33 / 34 / 35 / 36 / 37 / 38 / 39 / 184-193): a
missing or zero-group pair is upstream extractor breakage or
identity-territory; a constancy claim with zero observations is
meaningless and would double-cover iter 13.

Why ``input_colors`` is required to be a non-empty list per group
(``len >= 1``): a connected change group has at least one cell;
each cell has an input colour; the per-group ``input_colors`` field
is the sorted set of those colours, which is non-empty for any
non-empty group. A zero-length ``input_colors`` is an extractor
contract violation, not a valid K==0 case.

Why strict per-colour validation (bool rejected, range checked):
``input_colors`` carries small ints in [0, 9]; the matcher
performs the same strict-type gating as iter 14 / 18 / 19 / 34 /
35 / 36 / 37 / 38 / 184-192 to keep contract violations from
silently passing. The actual constancy check is on
``len(input_colors)``, not on the colours themselves, so cross-
pair colour identity is NOT required.

No companion-touch required: ``input_colors`` has been emitted
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


@register("change_input_color_count_per_group_constant_across_pairs")
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
            input_colors = group.get("input_colors")
            if not isinstance(input_colors, list) or len(input_colors) < 1:
                return False
            for ic in input_colors:
                if not _is_strict_color(ic):
                    return False
            cardinality = len(input_colors)
            if canonical_card is None:
                canonical_card = cardinality
            elif canonical_card != cardinality:
                return False

    return canonical_card is not None
