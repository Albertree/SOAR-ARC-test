"""
change_count_per_group_constant_across_pairs -- match tasks where every
change group in every example pair has the **same** ``cell_count``
integer K, across all groups in all pairs. The single integer K is the
per-group cardinality the rule's apply-time selection must reproduce;
the matcher does not pin a specific K, only its constancy across
*every* group in every pair.

Recognition vocabulary axis: ``selection-shape / per-group cell-count
constancy``. This is the per-group projection of the cross-pair
cardinality lineage iter 32 (``change_count_constant_across_pairs``,
total cells across groups in a pair) and iter 39
(``change_group_count_constant_across_pairs``, number of groups in a
pair) sit on. Where iter 32 pins the per-pair *total* and iter 39 pins
the per-pair *group count*, this matcher pins the per-group
*cardinality* — a strictly finer-grained property that is orthogonal
to both.

Refinement / orthogonality summary (universal-over-pairs semantics):

  * Iter 13 (``identity_transformation``) — every pair has zero groups.
    This matcher REJECTS the no-group case (fail-closed clause below)
    to keep its territory disjoint from iter 13 by construction.
    Mirrors iter 32 / 39's empty-group rejection.
  * Iter 23 (``single_change_group_per_pair``) — every pair has
    exactly one group. INDEPENDENT of this matcher: iter 23 fires
    with varying single-group cell counts (pair 0 group of 2 cells,
    pair 1 group of 5 cells); this matcher fires when every group
    has the same K (e.g. every pair has two groups of 3 cells each).
    CAN co-fire (every pair has exactly one group AND that group has
    the same K cells).
  * Iter 24 (``single_cell_change_per_pair``) — STRICT REFINEMENT of
    this matcher (pins K == 1, AND num_groups == 1 per pair): every
    pair has exactly one group of one cell ⟹ every group has the
    same K == 1.
  * Iter 26 (``multi_cell_change_group_per_pair``) — pins num_groups
    == 1 per pair AND cell_count >= 2 per pair. NOT a refinement in
    either direction: iter 26 fires with varying single-group cell
    counts across pairs (pair 0 has 2 cells, pair 1 has 5 cells);
    this matcher rejects. CAN co-fire (single group per pair with
    the same K >= 2 across pairs).
  * Iter 28 (``multi_group_per_pair``) — pins num_groups >= 2 per
    pair. NOT a refinement either way: iter 28 fires with varying
    per-group cell counts; this matcher requires constant K
    everywhere. CAN co-fire.
  * Iter 32 (``change_count_constant_across_pairs``) — STRICT
    REFINEMENT IMPLIED: if every group in every pair has cell_count
    K AND num_groups is constant N per pair, then the per-pair total
    is N*K everywhere, i.e. iter 32 fires. BUT this matcher alone
    does NOT pin num_groups across pairs, so this matcher ⟹̸ iter 32
    in general (pair 0 has 2 groups of 3 cells = 6 total, pair 1 has
    3 groups of 3 cells = 9 total: this matcher fires, iter 32
    rejects). INDEPENDENT in both directions; CAN co-fire when both
    K and num_groups are constant.
  * Iter 39 (``change_group_count_constant_across_pairs``) — pins
    num_groups across pairs without constraining per-group cell
    counts. NOT a refinement either way: iter 39 fires when the
    group count is the same N but cell counts vary (pair 0 has
    groups [2, 5], pair 1 has groups [3, 4]: iter 39 fires, this
    matcher rejects). CAN co-fire when both N and K are constant.
  * Iter 10 (``sequential_recoloring``) — requires same non-zero
    num_groups N per pair AND per-pair outputs form a contiguous
    range. Independent of per-group cell-count constancy.
  * Iter 1 (``grid_size_preserved``) / iter 33
    (``output_dimensions_multiple_of_input``) -- orthogonal
    dimensional axis. CAN co-fire.
  * Every palette- / colour-content matcher (iters 14 / 15 / 18 / 19
    / 34 / 35 / 36 / 37 / 38 / 40 / 184–192) -- orthogonal: those
    inspect colours; this matcher inspects per-group cell counts.

Why this matters for ARBOR's intended ruleset:

  * "Each group is exactly N cells" rule family: rules whose
    apply-time selection paints exactly K cells per blob, with K
    constant across pairs (e.g. "paint every detected dot",
    "fill every 2x2 block"). The recognition-side prerequisite is
    a named handle for "per-group cell count is the same integer
    K across every group across every pair." Without it, anti-
    unification (CLAUDE.md §8) has no ``condition.type`` to attach
    a per-group-cardinality generalisation variable to.
  * Sits on a sub-axis DISTINCT from the palette axis that iters
    184–192 populated. The change-cell axes had a cross-pair
    total-cell-count handle (iter 32) and a cross-pair group-count
    handle (iter 39) but no cross-pair PER-GROUP-cardinality handle.
    This matcher fills that gap.

Params:
  (none) -- pure cross-pair / cross-group constancy check on the
  derived integer ``analysis["groups"][j]["cell_count"]`` that
  ``_analyze_pair`` has emitted since iter 1.

Returns True iff:
  - ``patterns`` is a dict, AND
  - ``patterns["pair_analyses"]`` is a non-empty list, AND
  - every analysis is a dict, AND
  - every analysis has a non-empty ``groups`` list (identity-
    territory rejection), AND
  - every group is a dict with a strict-positive-int ``cell_count``
    (bool subclass rejected per the iter-13 / 17 / 18 / 19 / 20 /
    22 / 23 / 24 / 26 / 28 / 30 / 32 / 33 / 34 / 35 / 36 / 37 / 38 /
    39 strict-type posture), AND
  - every group's ``cell_count`` is bit-identical to the first
    group's cell_count.

Why fail-closed on empty / no-group / malformed (same posture as
iters 30 / 32 / 33 / 34 / 35 / 36 / 37 / 38 / 39 / 184–192): a
missing or zero-group pair is upstream extractor breakage or
identity-territory; a constancy claim with zero observations is
meaningless and would double-cover iter 13.

Why strict bool-subclass rejection on ``cell_count``: ``cell_count``
is semantically an integer count, not a Boolean. Strict-type matchers
across the registry reject ``True`` / ``False`` on integer fields;
this matcher upholds the same posture for type-strictness consistency.

No companion-touch required: ``cell_count`` has been emitted per
group since iter 1 (``_analyze_pair`` in ``agent/active_operators.py``);
this iter is a pure matcher addition with no
``agent/active_operators.py`` diff. F8 inert.
"""

from __future__ import annotations

from agent.conditions import register


@register("change_count_per_group_constant_across_pairs")
def match(patterns: dict, params: dict) -> bool:
    if not isinstance(patterns, dict):
        return False
    pair_analyses = patterns.get("pair_analyses")
    if not isinstance(pair_analyses, list) or not pair_analyses:
        return False

    canonical_cell_count: int | None = None

    for analysis in pair_analyses:
        if not isinstance(analysis, dict):
            return False
        groups = analysis.get("groups")
        if not isinstance(groups, list) or not groups:
            return False
        for group in groups:
            if not isinstance(group, dict):
                return False
            cc = group.get("cell_count")
            if not isinstance(cc, int) or isinstance(cc, bool):
                return False
            if cc < 1:
                return False
            if canonical_cell_count is None:
                canonical_cell_count = cc
            elif canonical_cell_count != cc:
                return False

    return canonical_cell_count is not None
