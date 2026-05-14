"""
change_color_mapping_count_per_group_constant_across_pairs -- match
tasks where every change group in every example pair has the SAME
per-group ``(ic, oc)`` Cartesian-product cardinality

    K = len(group["input_colors"]) * len(group["output_colors"])

across every group across every pair, with K a single integer
determined by the first observed group.

Recognition vocabulary axis: ``colour-content / per-group (ic, oc)
Cartesian-product cardinality constancy``. This is the per-group
projection of iter 40
(``change_color_mapping_count_constant_across_pairs``, which inspects
the cardinality of the per-pair frozenset of group-level
``(input_colors[0], output_colors[0])`` tuples under a strict
``len == 1`` precondition) and the per-group product-cardinality
sibling of iter 195 (``change_input_color_count_per_group_constant_
across_pairs``, per-group input-cardinality) / iter 196
(``change_output_color_count_per_group_constant_across_pairs``,
per-group output-cardinality).

Where iter 40 collapses each pair's groups into a per-pair (ic, oc)
SET (one tuple per group under its strict ``len == 1`` precondition)
and compares set cardinalities cross-pair, this matcher inspects each
individual group's ``len(input_colors) * len(output_colors)`` product
-- the cardinality of the group's per-cell (ic, oc) Cartesian-product
upper bound -- and demands constancy across every group across every
pair, regardless of how many input or output colours each group
individually spans. The two projections are not in a refinement
relation: a task where every group has the same per-group K (= input
× output product) but the per-pair (ic, oc) set cardinalities differ
fires this matcher and may reject iter 40 (e.g. iter 40's strict
``len == 1`` precondition is violated when a group has K_in == 2);
conversely a task where every per-pair (ic, oc) set has the same
cardinality N while per-group K varies fires iter 40 and rejects this
matcher.

Refinement / orthogonality summary (universal-over-pairs / -groups
semantics):

  * Iter 13 (``identity_transformation``) -- every pair has zero
    groups. This matcher REJECTS the no-group case (fail-closed
    clause below) to keep its territory disjoint from iter 13 by
    construction. Mirrors iter 32 / 35 / 37 / 39 / 193 / 195 / 196's
    empty-group rejection.
  * Iter 14 (``input_color_uniform``) AND iter 18
    (``output_color_uniform``) -- pin K_in == 1 AND K_out == 1
    (plus identical colour) across all groups in all pairs. Both
    together STRICTLY IMPLY this matcher (1 * 1 == 1 constant).
    Either alone does not (input or output cardinality could vary
    on the other side).
  * Iter 35 / 36 (``change_input_colors_constant_across_pairs`` /
    ``change_output_colors_constant_across_pairs``) -- per-pair
    input / output colour SET bit-identity. Independent: per-pair
    SET bit-identity says nothing about per-group cardinalities
    individually.
  * Iter 37 / 38 (``change_input_color_count_constant_across_pairs``
    / ``change_output_color_count_constant_across_pairs``) --
    per-pair UNION input / output cardinality constancy. Independent:
    per-pair union cardinality can equal across pairs while per-group
    K varies, and vice versa (per-group K constant while per-pair
    union differs because of cross-pair colour overlap differences).
  * Iter 40 (``change_color_mapping_count_constant_across_pairs``) --
    per-pair (ic, oc) SET cardinality. Iter 40 requires every group
    to have ``len(input_colors) == 1`` AND ``len(output_colors) == 1``;
    under that precondition each group contributes one (ic, oc) tuple
    and the per-pair set cardinality is at most the group count. NOT
    in a refinement relation either way:
      - iter 40 alone: every group has K_in == K_out == 1 (so per-
        group product K == 1 constant -- this matcher fires alongside),
        but per-pair (ic, oc) set cardinality varies. Wait: per-group
        K == 1 constant ⟹ this matcher fires. So whenever iter 40
        fires (under its len-1 precondition), this matcher also fires
        with K == 1. Iter 40 alone (without this matcher) is then
        unreachable -- the implication ``iter 40 ⟹ this matcher
        (K == 1)`` holds, but the converse fails (this matcher with
        K >= 2 rejects iter 40's len-1 precondition).
      - this matcher alone: per-group K constant at K >= 2 (e.g. one
        group has input ``[1]`` output ``[3, 4]`` K == 2, another
        has input ``[2, 5]`` output ``[6]`` K == 2). Iter 40 rejects
        (its len-1 precondition fails on at least one group).
      - both fire: every group has K_in == K_out == 1 AND per-pair
        (ic, oc) set cardinality is constant -- the iter-40
        territory under its len-1 precondition.
  * Iter 195 (``change_input_color_count_per_group_constant_across_
    pairs``) -- per-group ``len(input_colors)`` constancy.
    Independent: per-group input cardinality constant ⟹̸ per-group
    product constant (output side can still vary). Conversely
    per-group product constant ⟹̸ per-group input cardinality
    constant (e.g. K_in == 1 K_out == 2 in pair 0, K_in == 2
    K_out == 1 in pair 1 -- product 2 constant, but per-group
    K_in varies). When BOTH iter 195 AND iter 196 fire (per-group
    K_in == constant AND per-group K_out == constant), this matcher
    fires (product of two per-group constants is per-group
    constant). The converse does not hold (this matcher can fire
    with both factors varying as long as their product is
    constant).
  * Iter 196 (``change_output_color_count_per_group_constant_across_
    pairs``) -- per-group ``len(output_colors)`` constancy.
    Symmetric to iter 195 above. CAN co-fire with iter 195 ⟹ this
    matcher fires.
  * Iter 193 (``change_count_per_group_constant_across_pairs``) --
    per-group CELL_COUNT constancy. Sibling on the per-group
    constancy sub-axis, distinct field (cell_count vs
    len(input_colors) * len(output_colors)). NOT in a refinement
    relation. CAN co-fire.
  * Iter 23 (``single_change_group_per_pair``), iter 24
    (``single_cell_change_per_pair``), iter 26
    (``multi_cell_change_group_per_pair``), iter 28
    (``multi_group_per_pair``) -- those pin group-count or cell-count
    per pair; this matcher pins per-group product cardinality.
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
    ``input_colors`` and ``output_colors``. CAN co-fire.

Why this matters for ARBOR's intended ruleset:

  * "Each blob has the same (ic, oc) Cartesian-product cardinality"
    rule family: rules whose apply-time selection / colouring is
    derived from the size of a per-blob colour-mapping product
    (e.g. "paint every blob whose input-colour count times
    output-colour count equals K"). The recognition-side
    prerequisite is a named handle for the cross-group constancy
    of that derived integer. Without it, anti-unification (CLAUDE.md
    §8) has no ``condition.type`` to attach a per-group
    Cartesian-product-cardinality generalisation variable to.
  * Closes the per-group product-cardinality leg of the per-group
    cardinality sub-axis iter 193 / 195 / 196 opened. Iter 193
    named the per-group cell-count handle; iter 195 named the
    per-group input-colour-cardinality handle; iter 196 named the
    per-group output-colour-cardinality handle; this matcher names
    the per-group input-output Cartesian-product handle. The four
    handles together cover the four natural per-group cardinality
    derivations (positions / inputs / outputs / mapping product).
  * The product cardinality is a genuinely independent invariant
    from iter 195 / iter 196: a task where per-group K_in varies
    inversely with K_out so that K_in * K_out is constant fires
    this matcher and rejects both iter 195 and iter 196. This is
    not the conjunction of iter 195 AND iter 196 but a strictly
    weaker (and therefore more permissive) regularity.

Why the Cartesian product rather than the actual (ic, oc) cell set:
the extractor (``_analyze_pair`` in ``agent/active_operators.py``)
emits per-group ``input_colors`` (sorted set of input colours over
the group's cells) and ``output_colors`` (sorted set of output
colours over the group's cells), but NOT the per-cell (ic, oc)
pairs. The Cartesian product ``input_colors × output_colors`` is
an upper bound on the actual (ic, oc) set in the group, with
cardinality ``len(input_colors) * len(output_colors)``. The matcher
checks constancy of this upper bound; deriving the actual per-cell
set would require an extractor change (companion-touch, deferrable
to a larger-than-smallest-step iter). Using the Cartesian product
is the smallest-defensible recognition handle on existing data.

Params:
  (none) -- pure cross-pair / cross-group constancy check on the
  derived integer ``len(input_colors) * len(output_colors)`` for
  every group in every pair.

Returns True iff:
  - ``patterns`` is a dict, AND
  - ``patterns["pair_analyses"]`` is a non-empty list, AND
  - every analysis is a dict, AND
  - every analysis has a non-empty ``groups`` list (identity-
    territory rejection), AND
  - every group is a dict with list-typed ``input_colors`` and
    ``output_colors`` fields, each of length at least 1 (a colour
    list cannot be empty; an empty colour list would mean the
    group has zero cells on that side, an extractor contract
    violation), AND
  - every entry of ``input_colors`` and ``output_colors`` is a
    strict int in ``range(10)`` (bool rejected per iter-13 / 14 /
    17 / 18 / 19 / 22 / 23 / 24 / 26 / 28 / 30 / 32 / 33 / 34 / 35
    / 36 / 37 / 38 / 39 / 184-196 strict-type posture; out-of-range
    rejected as upstream extractor breakage), AND
  - every group's ``len(input_colors) * len(output_colors)`` is
    bit-identical to the first group's product.

Why fail-closed on empty / no-group / malformed (same posture as
iters 30 / 32 / 33 / 34 / 35 / 36 / 37 / 38 / 39 / 184-196): a
missing or zero-group pair is upstream extractor breakage or
identity-territory; a constancy claim with zero observations is
meaningless and would double-cover iter 13.

Why ``input_colors`` and ``output_colors`` are required to be
non-empty lists per group (``len >= 1``): a connected change group
has at least one cell; each cell has both an input and an output
colour; the per-group ``input_colors`` / ``output_colors`` fields
are the sorted sets of those colours, which are non-empty for any
non-empty group. A zero-length colour list is an extractor contract
violation, not a valid K == 0 case.

Why strict per-colour validation (bool rejected, range checked):
``input_colors`` / ``output_colors`` carry small ints in [0, 9];
the matcher performs the same strict-type gating as iter 14 / 18 /
19 / 34 / 35 / 36 / 37 / 38 / 184-196 to keep contract violations
from silently passing. The actual constancy check is on the
product of cardinalities, not on the colours themselves, so
cross-pair colour identity is NOT required.

No companion-touch required: ``input_colors`` and ``output_colors``
have both been emitted per group since iter 1 (``_analyze_pair``
in ``agent/active_operators.py``); this iter is a pure matcher
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


@register("change_color_mapping_count_per_group_constant_across_pairs")
def match(patterns: dict, params: dict) -> bool:
    if not isinstance(patterns, dict):
        return False
    pair_analyses = patterns.get("pair_analyses")
    if not isinstance(pair_analyses, list) or not pair_analyses:
        return False

    canonical_product: int | None = None

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
            output_colors = group.get("output_colors")
            if not isinstance(input_colors, list) or len(input_colors) < 1:
                return False
            if not isinstance(output_colors, list) or len(output_colors) < 1:
                return False
            for ic in input_colors:
                if not _is_strict_color(ic):
                    return False
            for oc in output_colors:
                if not _is_strict_color(oc):
                    return False
            product = len(input_colors) * len(output_colors)
            if canonical_product is None:
                canonical_product = product
            elif canonical_product != product:
                return False

    return canonical_product is not None
