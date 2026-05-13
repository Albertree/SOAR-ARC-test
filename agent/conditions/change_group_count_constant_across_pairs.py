"""
change_group_count_constant_across_pairs -- match tasks where the per-pair
``num_groups`` value (the count of connected change groups in each example
pair) is bit-identical across every example pair, regardless of which
specific cells those groups occupy or how the groups partition the changed
region.

Recognition vocabulary axis: ``selection-shape / cross-pair group-count
constancy``. This is the *cardinality-axis projection* of the per-pair
group-count predicates iter 23 (``single_change_group_per_pair``,
``num_groups == 1`` per pair) and iter 28 (``multi_group_per_pair``,
``num_groups >= 2`` per pair) sit on. Where iters 23 / 28 pin specific
cardinality regimes ("every pair has exactly 1 group", "every pair has 2
or more groups"), this matcher names the orthogonal projection: "every
pair has the SAME number of groups N, for some N >= 1 -- the specific N
is not constrained by the matcher, only its constancy across pairs".

The construction mirrors how iter 32
(``change_count_constant_across_pairs``) projects iter 30
(``change_positions_constant_across_pairs``) onto the cardinality axis
of the position-content domain; and how iter 37
(``change_input_color_count_constant_across_pairs``) projects iter 35
(``change_input_colors_constant_across_pairs``) onto the cardinality
axis of the input-colour set domain; and how iter 38
(``change_output_color_count_constant_across_pairs``) projects iter 36
onto the cardinality axis of the output-colour set domain. The
selection-shape (group-count) axis is the remaining axis that has named
specific-N matchers (iters 23 / 28) but no named cross-pair cardinality
projection. This matcher fills that gap.

Relation to ``single_change_group_per_pair`` (iter 23) -- iter 23 is a
strict refinement of this matcher (pins N == 1):

    iter 23 ⟹ this matcher    (every pair has ``num_groups == 1`` ⟹
                                every pair has the same num_groups,
                                trivially)

    this matcher ⟹̸ iter 23    (e.g. every pair has ``num_groups == 2``;
                                this matcher fires, iter 23 rejects)

Relation to ``multi_group_per_pair`` (iter 28) -- NOT a refinement in
either direction:

  * iter 28 fires alone: every pair has ``num_groups >= 2`` but the
    specific count varies (e.g. pair 0 has 2 groups, pair 1 has 3).
    iter 28 fires, this matcher rejects.
  * this matcher fires alone: every pair has ``num_groups == 1`` --
    this matcher fires, iter 28 rejects.
  * Both fire: every pair has the SAME ``num_groups >= 2`` (e.g. every
    pair has exactly 2 groups).
  * Neither fires: identity case (handled by iter 13), or num_groups
    varies AND at least one pair has fewer than 2 groups.

Relation to ``sequential_recoloring`` (iter 10) -- iter 10 strictly
refines this matcher: iter 10 requires same non-zero N across pairs
(this matcher's precondition) AND per-pair outputs forming a contiguous
integer range (additional content predicate). So iter 10 ⟹ this
matcher; the converse does not hold. Iter 10 inlined cross-pair N
constancy plus a sequence-content check; this matcher is the clean
projection of just the cardinality side, available as a separate
recognition handle for future emission branches that want the
"constant N groups per pair" precondition without iter 10's
contiguous-range requirement.

Why this matters for the schema:

  * Iters 23 / 28 / 13 partition the per-pair group-count axis into
    three regimes (0 / 1 / >= 2), but none names "every pair has the
    SAME N, whatever N is". A future emission branch that paints N
    blobs per pair with N derived from training (e.g. anti-unification
    lifting ``coloring``'s ``selection`` to "the N detected blob
    positions") has no named precondition for the cross-pair
    cardinality invariant the action's apply-time selection must
    reproduce. This matcher names that precondition.
  * Per-attempt ``fired_conditions`` (written to
    ``episodic_memory/<task>/attempt_NNN/metadata.json`` since iter 12)
    gains a directly inspectable signal for "this task's group count
    is pinned across pairs" -- one more named axis the instrumentation
    surfaces without needing a translate_to_schema branch to consume
    it. Recognition vocabulary ahead of emission, the same posture
    iters 17 / 18 / 19 / 20 / 22 / 23 / 24 / 26 / 28 / 30 / 32 / 33 /
    34 / 35 / 36 / 37 / 38 all carry.
  * Completes the cardinality-projection lineage: positions (iter
    30 -> iter 32), input colours (iter 35 -> iter 37), output colours
    (iter 36 -> iter 38), and now the selection-shape group-count axis
    (iters 23 / 28 -> this iter). Each axis now has a named handle for
    "the X is bit-identical across every pair" at the cardinality
    granularity.

The cross-pair group-count constancy axis is orthogonal to:

  * The position-content axis (``change_positions_constant_across_pairs``
    / ``change_count_constant_across_pairs``) -- those inspect coord
    sets / counts, not group counts. CAN co-fire on any combination.
    A task can have constant group count but varying positions, OR
    varying group count but constant total cell count (e.g. pair 0
    has two 1-cell blobs, pair 1 has one 2-cell blob -- both total 2
    cells but group counts 2 vs 1 differ), OR both, OR neither.
  * The colour-content axes (``output_color_uniform`` /
    ``input_color_uniform`` / ``consistent_color_mapping`` /
    ``sequential_recoloring`` / ``change_colors_constant_across_pairs``
    / iter 35 / iter 36 / iter 37 / iter 38) -- those inspect group
    colour fields, not group counts. CAN co-fire.
  * The dimensional axes (``grid_size_preserved`` /
    ``grid_size_changed`` / ``output_dimensions_constant`` /
    ``input_dimensions_constant`` /
    ``output_dimensions_multiple_of_input``) -- those inspect grid
    shape, not group counts. CAN co-fire.
  * The cell-count sub-axis (``single_cell_change_per_pair`` /
    ``multi_cell_change_group_per_pair``) -- those inspect per-group
    ``cell_count`` under ``num_groups == 1``; this matcher inspects
    the per-pair ``num_groups`` value. CAN co-fire (in fact, both
    cell-count sub-axes are layered under ``num_groups == 1`` and
    therefore CO-FIRE with this matcher pinned at N == 1).

Relation to existing matchers (mutual-exclusion / refinement table):

  * ``identity_transformation`` (iter 13) -- requires every pair's
    ``num_groups == 0``. This matcher REJECTS the all-zero case (see
    fail-closed clause below) to keep its territory disjoint from iter
    13 by construction. Mirrors iter 30's empty-union rejection on
    the position axis, iter 32's per-pair-total-zero rejection on the
    cell-count axis, iter 37 / 38's per-pair-zero-cardinality rejection
    on the colour-cardinality axes, and iter 18 / 19 / 34 / 35 / 36's
    empty-set rejection on the colour-set axes. STRICTLY mutually
    exclusive in practice.
  * ``single_change_group_per_pair`` (iter 23) -- strict refinement of
    this matcher (pins N == 1). CAN co-fire by construction: iter 23
    fires ⟹ this matcher fires.
  * ``multi_group_per_pair`` (iter 28) -- NOT a refinement in either
    direction (proved above). CAN co-fire when every pair has the
    same N >= 2.
  * ``single_cell_change_per_pair`` (iter 24) -- refines iter 23
    further (N == 1 AND cell_count == 1); refines this matcher
    transitively. CAN co-fire by construction.
  * ``multi_cell_change_group_per_pair`` (iter 26) -- refines iter 23
    further (N == 1 AND cell_count >= 2). CAN co-fire by construction.
  * ``sequential_recoloring`` (iter 10) -- strict refinement of this
    matcher (proved above). CAN co-fire by construction.
  * ``change_count_constant_across_pairs`` (iter 32) -- NOT a
    refinement in either direction. iter 32 inspects the SUM across
    groups; this matcher inspects the NUMBER of groups. Constant sum
    does not imply constant group count (e.g. pair 0 of two
    single-cell blobs and pair 1 of one two-cell blob: both sum 2 but
    group counts differ); constant group count does not imply
    constant sum (e.g. every pair has 1 group but cell counts differ).
    Orthogonal axes.
  * ``change_positions_constant_across_pairs`` (iter 30) -- iter 30
    strictly refines this matcher in a non-trivial way: bit-identical
    per-pair coord sets implies the connected-component partition is
    bit-identical (the partition is a function of the coord set
    *along with the adjacency relation it induces*, which is
    bit-identical when the coord sets are bit-identical), so
    ``num_groups`` agrees across pairs. iter 30 ⟹ this matcher.
    The converse does not hold (same group count with different
    coords). Refinement chain documented.
  * ``output_dimensions_multiple_of_input`` (iter 33) -- orthogonal
    dimensional axis. CAN co-fire.

Params:
  (none) -- the matcher inspects
  ``patterns["pair_analyses"][i]["num_groups"]``, the strict-positive-int
  per-pair group count emitted by ``_analyze_pair`` since iter 1.
  Compared cross-pair for equality, with a non-zero clause to keep
  identity territory disjoint.

Returns True iff:
  - ``patterns`` is a dict, AND
  - ``patterns["pair_analyses"]`` is a non-empty list, AND
  - every analysis is a dict, AND
  - every analysis carries a strict-positive-int ``num_groups``
    (bool rejected per ``validate_rule`` V1 posture), AND
  - every analysis's ``num_groups`` is at least 1 (the
    identity-territory rejection clause), AND
  - every analysis's ``num_groups`` is bit-identical to the first.

Why fail-closed on ``num_groups == 0``: a patterns dict where every
pair has zero groups (the identity case) has a per-pair group count of
0 that is vacuously equal across pairs. Allowing that to fire here
would double-cover iter 13's identity territory under a name that
promises "the group count is pinned" -- but there are no groups to
count. The matcher names a non-trivial precondition; the strict
refusal mirrors iter 32's per-pair-total-zero rejection, iter 37 /
38's per-pair-zero-cardinality rejection, iter 18 / 19 / 34 / 35 /
36's empty-set rejection, and iter 30's empty-union rejection.

Why strict bool-subclass rejection on ``num_groups``: ``num_groups``
is semantically an integer count, not a Boolean. Strict-type matchers
(iters 13 / 17 / 18 / 19 / 20 / 22 / 23 / 24 / 26 / 28 / 30 / 32 / 33
/ 34 / 35 / 36 / 37 / 38 and ``validate_rule`` V1) reject ``True`` /
``False`` on integer fields. The matcher upholds the same posture to
keep the recognition vocabulary's type-strictness consistent across
the registry.

Why a self-contained predicate rather than a refinement-by-call of
iters 23 / 28: matchers are independent predicates in the registry
(``docs/RULE_FORMAT.md`` section 4). Composing them at use-site (via
``recognized_conditions`` and a conjunction of names in a future
composite-precondition step) is the canonical pattern; inlining an
iter 23 / 28 disjunction here would couple registry entries in a
non-introspectable way. The matcher implements its cross-pair
cardinality check explicitly so ``CONDITION_REGISTRY[
"change_group_count_constant_across_pairs"]`` is a single
self-contained predicate, the same shape as every other matcher.

No ``_analyze_pair`` change this iter: the ``num_groups`` field has
been emitted per pair since iter 1, so the matcher uses existing data
on a new axis (the cardinality projection of iters 23 / 28's specific-N
predicates). F8 inert -- this iter has no ``agent/active_operators.py``
change at all.
"""

from __future__ import annotations

from agent.conditions import register


@register("change_group_count_constant_across_pairs")
def match(patterns: dict, params: dict) -> bool:
    if not isinstance(patterns, dict):
        return False
    pair_analyses = patterns.get("pair_analyses")
    if not isinstance(pair_analyses, list) or not pair_analyses:
        return False

    canonical_count: int | None = None

    for analysis in pair_analyses:
        if not isinstance(analysis, dict):
            return False
        n = analysis.get("num_groups")
        if not isinstance(n, int) or isinstance(n, bool):
            return False
        if n < 1:
            return False
        if canonical_count is None:
            canonical_count = n
        elif canonical_count != n:
            return False

    return canonical_count is not None
