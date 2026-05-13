"""
change_positions_constant_across_pairs -- match tasks where the unioned
set of changed cell coordinates is bit-identical across every example
pair.

Recognition vocabulary axis: ``position-content`` (cross-pair coord-set
constancy on the change-cells of each pair). The iter-23 / 24 / 26 / 28
sequence carved up the per-pair group-count axis (0 / 1 / >=2) and the
single-group cell-count sub-axis (==1 / >=2); none of those matchers
inspect *where* the changes occur, only how many groups and how many
cells per group. This matcher is the simplest entry on the position-
content axis: a Boolean on "the changed-cell coord set is the same
across pairs", regardless of how the cells partition into groups.

Why this matters for the schema:

  * The iter-25 (``paint_single_cell``) / iter-27 (``paint_blob``) /
    iter-29 (``paint_blobs``) emission branches all store
    ``action.args.selection`` as a literal coord list (or single coord
    for iter 25). For such a rule to generalise across training pairs,
    the SAME coord list must reproduce every pair's changed cells --
    i.e. the cross-pair changed-coord *set* must be constant. The three
    defensive helpers ``_extract_single_cell_paint_args`` /
    ``_extract_multi_cell_paint_args`` / ``_extract_multi_blob_paint_args``
    in ``agent/memory.py`` ALL contain a private cross-pair equality
    check on the canonical coord tuple; that check is the same
    predicate three times over. This matcher surfaces that predicate
    once, as named recognition vocabulary the registry can return
    via ``recognized_conditions``.
  * Naming the precondition has three immediate benefits:
      1. The per-attempt ``fired_conditions`` list (written by
         ``_record_attempt`` to every ``episodic_memory/<task>/attempt_NNN
         /metadata.json`` since iter 12) gains a directly inspectable
         signal for "this task's changed coords are pinned across pairs"
         -- the precondition the three existing emission branches need.
      2. A future translate_to_schema emission iter can gate on the
         named matcher instead of repeating the defensive cross-pair
         check inside each ``_extract_*_paint_args`` helper -- the same
         "recognition vocabulary ahead of emission" posture iter 22's
         "Next gap" log named for the selection-shape axis, now applied
         to the position-content axis.
      3. Anti-unification across the three sibling ``coloring`` rules
         (single-cell, multi-cell single-blob, multi-blob) currently
         cannot bridge their ``condition.type`` skeletons (cardinality
         labels differ); naming a single position-content matcher that
         fires across ALL three regimes provides a SHARED
         ``condition.type`` candidate that a future translate_to_schema
         iter could use instead of the cardinality-specific labels --
         widening the anti-unification skeleton-match domain for the
         first time since the three branches landed.

The position-content axis is orthogonal to:

  * The dimensional axis (``grid_size_preserved`` /
    ``grid_size_changed`` / ``output_dimensions_constant`` /
    ``input_dimensions_constant``) -- those inspect grid shape, not
    coord content.
  * The colour-content axis (``output_color_uniform`` /
    ``input_color_uniform`` / ``consistent_color_mapping`` /
    ``sequential_recoloring``) -- those inspect change-group colour
    fields, not coord content.
  * The group-count axis (``identity_transformation`` /
    ``single_change_group_per_pair`` / ``multi_group_per_pair``) --
    those inspect ``num_groups``, not coord content. This matcher can
    co-fire with any of single / multi-group as long as the unioned
    coord sets agree across pairs; it strictly cannot co-fire with
    iter 13's identity (zero groups means empty union, which this
    matcher rejects to avoid vacuous truth -- see below).
  * The cell-count sub-axis (``single_cell_change_per_pair`` /
    ``multi_cell_change_group_per_pair``) -- those inspect
    ``cell_count``, not coord content. Both can co-fire with this
    matcher when their respective cardinality conditions hold AND the
    coords align across pairs.

Relation to existing matchers:

  * ``identity_transformation`` (iter 13) -- requires every pair's
    ``num_groups == 0``; the unioned changed-coord set is empty.
    This matcher REJECTS the empty-union case (see ``min_evidence
    = 1`` posture, below): if there are no changed coords at all,
    "constant changed coords" is vacuously true and would
    misleadingly cover an identity task whose recognition territory
    is already named by iter 13. STRICTLY mutually exclusive in
    practice.
  * ``single_cell_change_per_pair`` (iter 24) -- requires
    ``num_groups == 1`` AND ``cell_count == 1`` per pair. The
    iter-25 emission helper ``_extract_single_cell_paint_args`` ALSO
    requires the single ``(top_row, top_col)`` to be bit-identical
    across pairs; that cross-pair equality check IS the predicate
    this matcher names. CAN co-fire when the single cell's coord is
    the same on every pair (the emission-iter-25 case).
  * ``multi_cell_change_group_per_pair`` (iter 26) -- requires
    ``num_groups == 1`` AND ``cell_count >= 2`` per pair. The
    iter-27 emission helper ``_extract_multi_cell_paint_args``'s
    cross-pair canonical-positions check IS the predicate this
    matcher names, lifted to multi-cell single-blob territory.
  * ``multi_group_per_pair`` (iter 28) -- requires
    ``num_groups >= 2`` per pair. The iter-29 emission helper
    ``_extract_multi_blob_paint_args``'s cross-pair canonical-
    positions check IS the predicate this matcher names, lifted to
    multi-blob territory (unioned over all blobs in each pair).
  * ``single_change_group_per_pair`` (iter 23) -- requires
    ``num_groups == 1`` per pair. CAN co-fire when the single
    group's full position set is constant across pairs (a strict
    refinement of iter 23's cardinality-only contract).
  * ``output_color_uniform`` (iter 18) and ``input_color_uniform``
    (iter 19) -- orthogonal (colour vs position). CAN co-fire when
    both the colour and the coord-set are pinned across pairs --
    the simplest possible literal-coord-list paint-rule recognition
    stack ("paint these specific cells with this specific colour"
    where both halves are training-pinned).

Params:
  (none) -- the matcher inspects ``patterns["pair_analyses"][i][
  "groups"][j]["positions"]``, which carries the row-major-sorted
  list of ``(row, col)`` tuples per group emitted by iter 27's
  ``_analyze_pair`` extension. The matcher unions across all groups
  of each pair into a canonical tuple and compares cross-pair
  equality.

Returns True iff:
  - ``patterns`` is a dict, AND
  - ``patterns["pair_analyses"]`` is a non-empty list, AND
  - every analysis is a dict, AND
  - every analysis carries a list-typed ``groups`` field, AND
  - every group is a dict with a strict-positive-int ``cell_count``
    (bool rejected per ``validate_rule`` V1 posture) AND a list-typed
    ``positions`` field whose length equals ``cell_count``, AND
  - every position is a 2-element ``(list, tuple)`` of
    strict-non-negative-int (not bool) row / col, AND
  - the unioned coord set per pair (over all groups in that pair)
    is non-empty, AND
  - the unioned coord set has no duplicates (i.e. no two blobs
    share a cell -- that would indicate corrupt connectivity), AND
  - the canonical sorted tuple of the unioned coord set is
    bit-identical across every pair.

Why fail-closed on empty unions: a patterns dict where every pair
has zero changed cells (the identity case) has empty unions that
are vacuously equal across pairs. Allowing that to fire here would
double-cover iter 13's ``identity_transformation`` territory under
a name that promises "the changed-coord SET is pinned" -- but there
is no changed-coord set to pin. The matcher names a non-trivial
precondition; the strict refusal mirrors iter 18 / 19's strict
refusal of zero-group pairs on the colour axis.

Why strict bool-subclass rejection on ``cell_count`` / coord entries:
both fields are semantically integer counts / coordinates, not
Booleans. Strict-type matchers (iters 13 / 17 / 18 / 19 / 20 / 22 /
23 / 24 / 26 / 28 and ``validate_rule`` V1) reject ``True`` /
``False`` on integer fields. The matcher upholds the same posture
to keep the recognition vocabulary's type-strictness consistent
across the registry.

Why fail-closed on length mismatch between ``positions`` and
``cell_count``: ``_analyze_pair`` emits these two fields in lockstep
(``cell_count = len(group_cells)`` and ``positions = sorted(
positions)``). A mismatch is upstream extractor breakage, not
evidence the precondition holds. The fail-closed posture preserves
the matcher's contract that a missing or malformed dependency is
NOT silent True.

Why duplicate-coord rejection inside a pair's union: iters 26 / 28
emission helpers strictly reject ``len(set(canon_tuple)) !=
len(canon_tuple)`` because that would indicate two blobs share a
cell -- the connectivity computation is internally corrupt. This
matcher upholds the same rejection.

Why a self-contained predicate rather than a refinement-by-call of
iter 23 / 26 / 28: matchers are independent predicates in the
registry (``docs/RULE_FORMAT.md`` section 4). Composing them at
use-site (via ``recognized_conditions`` and a conjunction of names
in a future composite-precondition step) is the canonical pattern;
inlining group-count cardinality here would couple registry entries
in a non-introspectable way. The matcher implements its position-
content check explicitly so ``CONDITION_REGISTRY[
"change_positions_constant_across_pairs"]`` is a single self-
contained predicate, the same shape as every other matcher.

No ``_analyze_pair`` change this iter: the ``positions`` field has
been emitted per group since iter 27, so the matcher uses existing
data on a new axis. The companion-touch question under F8 is
therefore inert -- this iter has no ``agent/active_operators.py``
change at all.
"""

from __future__ import annotations

from agent.conditions import register


@register("change_positions_constant_across_pairs")
def match(patterns: dict, params: dict) -> bool:
    if not isinstance(patterns, dict):
        return False
    pair_analyses = patterns.get("pair_analyses")
    if not isinstance(pair_analyses, list) or not pair_analyses:
        return False

    canonical: tuple | None = None

    for analysis in pair_analyses:
        if not isinstance(analysis, dict):
            return False
        groups = analysis.get("groups")
        if not isinstance(groups, list):
            return False

        union: list = []
        for group in groups:
            if not isinstance(group, dict):
                return False
            cell_count = group.get("cell_count")
            if not isinstance(cell_count, int) or isinstance(cell_count, bool):
                return False
            if cell_count < 1:
                return False
            raw_positions = group.get("positions")
            if not isinstance(raw_positions, list):
                return False
            if len(raw_positions) != cell_count:
                return False
            for p in raw_positions:
                if not isinstance(p, (list, tuple)) or len(p) != 2:
                    return False
                r, c = p[0], p[1]
                if not isinstance(r, int) or isinstance(r, bool) or r < 0:
                    return False
                if not isinstance(c, int) or isinstance(c, bool) or c < 0:
                    return False
                union.append((r, c))

        canon_tuple = tuple(sorted(union))
        if not canon_tuple:
            return False
        if len(set(canon_tuple)) != len(canon_tuple):
            return False
        if canonical is None:
            canonical = canon_tuple
        elif canonical != canon_tuple:
            return False

    return canonical is not None
