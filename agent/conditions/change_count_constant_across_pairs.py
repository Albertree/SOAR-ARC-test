"""
change_count_constant_across_pairs -- match tasks where the total number
of changed cells (summed across every group in a pair) is bit-identical
across every example pair, regardless of *where* those cells are.

Recognition vocabulary axis: ``change-cardinality`` (cross-pair total
change-cell COUNT constancy). The iter-23 / 24 / 26 / 28 sequence
carved up the per-pair GROUP-count axis (0 / 1 / >=2) and the
single-group cell-count sub-axis (==1 / >=2); iter 30
(``change_positions_constant_across_pairs``) named the position-CONTENT
axis. This matcher is the simplest entry on the orthogonal cardinality
axis: a Boolean on "the total number of changed cells is the same
across pairs", regardless of how those cells partition into groups OR
where they live.

Relation to ``change_positions_constant_across_pairs`` (iter 30) -- the
two matchers form a refinement chain on the position vs cardinality
axes:

    positions-constant ⟹ count-constant      (same coord set → same
                                               coord count, trivially)

    count-constant ⟹̸ positions-constant     (pair 0 changes (0,0),
                                               pair 1 changes (1,1) --
                                               both have count 1 but
                                               positions differ)

So iter 30 strictly refines this matcher on the position-content axis.
The two are NOT redundant: a task with cardinality-constant changes but
varying positions (e.g. "every pair recolours exactly 4 cells but at
different coords each time") fires this matcher and NOT iter 30. That
is the territory this matcher names -- the recognition precondition
for a future rule shape whose action affects a constant number of
cells via a position-DERIVING predicate (e.g. anti-unification lifting
``coloring``'s ``selection`` to "wherever input has colour C", where
the matched cells happen to number N for each training pair).

Why this matters for the schema:

  * Iter 30's matcher pins position content -- the strict precondition
    for literal-coord ``coloring`` rules. But the natural relaxation
    -- "the action affects a CONSTANT count of cells, position derived
    from input" -- has no named precondition. This matcher names that
    precondition.
  * Without this matcher, a future emission iter that lifts
    ``coloring``'s ``selection`` semantics (the iter-19 / 22 derived-
    selection rule shape iter 31's Next gap log named as option (A))
    has no recognition-vocabulary handle for the cardinality
    invariant the action's apply-time selection must reproduce.
  * Per-attempt ``fired_conditions`` (written to
    ``episodic_memory/<task>/attempt_NNN/metadata.json`` since iter 12)
    gains a directly inspectable signal for "this task's change
    cardinality is pinned across pairs" -- one more named axis the
    instrumentation surfaces without needing a translate_to_schema
    branch to consume it. Recognition vocabulary ahead of emission,
    the same posture iters 17 / 18 / 19 / 20 / 22 / 23 / 24 / 26 / 28
    / 30 carry.

The cardinality axis is orthogonal to:

  * The dimensional axis (``grid_size_preserved`` / ``grid_size_changed``
    / ``output_dimensions_constant`` / ``input_dimensions_constant``)
    -- those inspect grid shape, not change-cardinality.
  * The colour-content axis (``output_color_uniform`` /
    ``input_color_uniform`` / ``consistent_color_mapping`` /
    ``sequential_recoloring``) -- those inspect change-group colour
    fields, not change-cardinality.
  * The position-content axis (``change_positions_constant_across_
    pairs``) -- iter 30 inspects coord SET equality; this matcher
    inspects coord COUNT equality (weaker). Refinement chain
    documented above.
  * The group-count axis (``identity_transformation`` /
    ``single_change_group_per_pair`` / ``multi_group_per_pair``) --
    those inspect ``num_groups``, not the total cell-count summed
    across groups. The total can be constant even if ``num_groups``
    varies across pairs (e.g. pair 0 of two single-cell blobs and
    pair 1 of one two-cell blob both sum to total 2). STRICTLY NOT
    a refinement of any group-count matcher.
  * The cell-count sub-axis (``single_cell_change_per_pair`` /
    ``multi_cell_change_group_per_pair``) -- those inspect per-group
    ``cell_count`` under ``num_groups == 1``; this matcher inspects
    the SUM across all groups. Both single-cell variants imply
    total == 1, which is trivially constant -- they co-fire with
    this matcher.

Relation to existing matchers (mutual-exclusion / refinement table):

  * ``identity_transformation`` (iter 13) -- requires every pair's
    ``num_groups == 0``; the total change-cell count is 0. Vacuously
    constant across pairs (0 == 0). This matcher REJECTS the
    total-zero case (see fail-closed clause below) to keep the
    territory disjoint from iter 13 by construction; the matcher
    names a NON-TRIVIAL precondition, mirroring iter 30's same
    rejection on the empty-union case. STRICTLY mutually exclusive
    in practice.
  * ``single_cell_change_per_pair`` (iter 24) -- requires
    ``num_groups == 1`` AND ``cell_count == 1`` per pair, so the
    total is 1 for every pair. CAN co-fire (trivial: 1 == 1).
  * ``multi_cell_change_group_per_pair`` (iter 26) -- requires
    ``num_groups == 1`` AND ``cell_count >= 2`` per pair. The matcher
    pins the per-group count regime but not the count's value; the
    iter-27 emission helper additionally requires the position SET
    to be constant (which implies count is constant). CAN co-fire
    when the per-pair total is constant.
  * ``multi_group_per_pair`` (iter 28) -- requires
    ``num_groups >= 2`` per pair. CAN co-fire when the per-pair
    total summed across blobs is constant -- even with varying
    ``num_groups`` (e.g. pair 0 of two single-cell blobs and pair 1
    of one two-cell blob both sum to 2).
  * ``single_change_group_per_pair`` (iter 23) -- requires
    ``num_groups == 1`` per pair. CAN co-fire when the single
    group's ``cell_count`` is constant across pairs.
  * ``change_positions_constant_across_pairs`` (iter 30) -- strict
    refinement of this matcher (positions-constant implies
    count-constant). CAN co-fire (in fact, iter 30 firing implies
    this matcher fires); the converse does not hold.
  * ``output_color_uniform`` (iter 18) and ``input_color_uniform``
    (iter 19) -- orthogonal (colour vs cardinality). CAN co-fire.
  * Dimensional matchers -- orthogonal. CAN co-fire on either
    dimensional regime.

Params:
  (none) -- the matcher inspects
  ``patterns["pair_analyses"][i]["groups"][j]["cell_count"]``,
  the strict-positive-int per-group cell count emitted by
  ``_analyze_pair`` since iter 1. Summed across all groups in each
  pair and compared cross-pair.

Returns True iff:
  - ``patterns`` is a dict, AND
  - ``patterns["pair_analyses"]`` is a non-empty list, AND
  - every analysis is a dict, AND
  - every analysis carries a list-typed ``groups`` field, AND
  - every group is a dict with a strict-positive-int ``cell_count``
    (bool rejected per ``validate_rule`` V1 posture), AND
  - the per-pair sum of ``cell_count`` across all groups is non-zero
    (the identity-territory rejection clause), AND
  - the per-pair sum is bit-identical across every pair.

Why fail-closed on total-zero: a patterns dict where every pair has
zero groups (the identity case) has a per-pair total of 0 that is
vacuously equal across pairs. Allowing that to fire here would
double-cover iter 13's ``identity_transformation`` territory under a
name that promises "the change cardinality is pinned" -- but there is
no change cardinality to pin. The matcher names a non-trivial
precondition; the strict refusal mirrors iter 30's strict refusal of
empty-union cases on the position axis, and iter 18 / 19's strict
refusal of zero-group pairs on the colour axis.

Why strict bool-subclass rejection on ``cell_count``: ``cell_count``
is semantically an integer count, not a Boolean. Strict-type matchers
(iters 13 / 17 / 18 / 19 / 20 / 22 / 23 / 24 / 26 / 28 / 30 and
``validate_rule`` V1) reject ``True`` / ``False`` on integer fields.
The matcher upholds the same posture to keep the recognition
vocabulary's type-strictness consistent across the registry.

Why a self-contained predicate rather than a refinement-by-call of
iter 30 (or iter 23 / 26 / 28): matchers are independent predicates
in the registry (``docs/RULE_FORMAT.md`` section 4). Composing them
at use-site (via ``recognized_conditions`` and a conjunction of
names in a future composite-precondition step) is the canonical
pattern; inlining a position-content check or a group-count
cardinality here would couple registry entries in a
non-introspectable way. The matcher implements its cardinality
check explicitly so ``CONDITION_REGISTRY[
"change_count_constant_across_pairs"]`` is a single self-contained
predicate, the same shape as every other matcher.

No ``_analyze_pair`` change this iter: the ``cell_count`` field has
been emitted per group since iter 1, so the matcher uses existing
data on a new axis. The companion-touch question under F8 is
therefore inert -- this iter has no ``agent/active_operators.py``
change at all.
"""

from __future__ import annotations

from agent.conditions import register


@register("change_count_constant_across_pairs")
def match(patterns: dict, params: dict) -> bool:
    if not isinstance(patterns, dict):
        return False
    pair_analyses = patterns.get("pair_analyses")
    if not isinstance(pair_analyses, list) or not pair_analyses:
        return False

    canonical_total: int | None = None

    for analysis in pair_analyses:
        if not isinstance(analysis, dict):
            return False
        groups = analysis.get("groups")
        if not isinstance(groups, list):
            return False

        pair_total = 0
        for group in groups:
            if not isinstance(group, dict):
                return False
            cell_count = group.get("cell_count")
            if not isinstance(cell_count, int) or isinstance(cell_count, bool):
                return False
            if cell_count < 1:
                return False
            pair_total += cell_count

        if pair_total == 0:
            return False
        if canonical_total is None:
            canonical_total = pair_total
        elif canonical_total != pair_total:
            return False

    return canonical_total is not None
