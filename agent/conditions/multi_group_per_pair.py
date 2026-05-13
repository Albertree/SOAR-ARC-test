"""
multi_group_per_pair -- match tasks where every example pair has STRICTLY
MORE THAN ONE connected change group (``num_groups >= 2``).

Recognition vocabulary axis: ``selection-shape`` (group-count). Strict
disjoint partner of iter 23's ``single_change_group_per_pair`` and strict
disjoint partner of iter 13's ``identity_transformation`` on the group-
count axis. Together with iters 13 / 23 the three matchers now partition
the per-pair group-count axis into the exact three regimes that the
selection-shape axis cares about:

  * ``num_groups == 0``      -> iter 13 (``identity_transformation``)
  * ``num_groups == 1``      -> iter 23 (``single_change_group_per_pair``)
  * ``num_groups >= 2``      -> THIS iter (``multi_group_per_pair``)

The three matchers are pairwise strictly mutually exclusive on any
non-empty ``pair_analyses`` list; their union (the disjunction) covers
every well-formed patterns dict. No patterns dict fires more than one of
the three. (Iters 24 / 26 sit on the cell-count sub-axis *under* iter
23's territory and are orthogonal to this matcher.)

Why this matters for the schema (the iter-27 "Next gap" log named this):

  * Iter 27's "Next gap" log explicitly named the multi-blob territory
    as the next emission frontier: "extend the recognition axis with a
    ``multi_group_per_pair`` matcher (``num_groups >= 2`` per pair --
    the simplest entry on the deferred multi-blob axis from iter 23's
    territory), then write the emission branch that consumes it." The
    matcher is the smaller half of that two-step plan; the emission
    branch is the next-iter step. The iter-23 / iter-24 / iter-26
    sequence and the iter-25 / iter-27 emission cadence establish the
    pattern of landing a matcher first, then its emission consumer
    one iter later.
  * Once an emission branch consumes this matcher, the rule shape
    "paint multiple disjoint blobs per pair with colour K" becomes
    expressible without any new DSL primitive: a single ``coloring``
    call with ``selection = blob_1_positions ++ blob_2_positions ++ ...
    ++ blob_N_positions`` and ``color = K`` (gated on
    ``output_color_uniform`` for K constancy). That action shape is
    the natural multi-blob analogue of iter 27's multi-cell single-
    blob branch, and it composes the frozen ``coloring`` primitive
    as data -- no F3 hand-coded primitive growth.
  * For tasks where each blob receives a *different* colour, a single
    ``coloring`` call no longer suffices and an anti-unification-
    discovered abstraction (multi-call composition) is the natural
    representation. That branch is a future-iter step beyond this
    one. This matcher names only the precondition that distinguishes
    single-blob from multi-blob territory; it does not commit to
    either of the two emission paths.

Relation to existing matchers:

  * ``identity_transformation`` (iter 13) -- requires every pair's
    ``num_groups == 0``; this matcher requires every pair's
    ``num_groups >= 2``. STRICTLY mutually exclusive (cardinality 0 vs
    cardinality >= 2).
  * ``single_change_group_per_pair`` (iter 23) -- requires every
    pair's ``num_groups == 1``; this matcher requires every pair's
    ``num_groups >= 2``. STRICTLY mutually exclusive (cardinality 1
    vs cardinality >= 2). Iter 23 and this matcher are the two
    partners that, together with iter 13, partition the per-pair
    group-count axis into three non-overlapping regimes.
  * ``single_cell_change_per_pair`` (iter 24) -- requires
    ``num_groups == 1`` AND ``cell_count == 1``. STRICTLY mutually
    exclusive with this matcher on the group-count axis alone (1 vs
    >= 2); the cell-count sub-axis is irrelevant once group-count
    differs.
  * ``multi_cell_change_group_per_pair`` (iter 26) -- requires
    ``num_groups == 1`` AND ``cell_count >= 2``. STRICTLY mutually
    exclusive with this matcher on the group-count axis (1 vs >= 2).
    Despite both matchers's names containing "multi-", they recognise
    orthogonal sub-axes: iter 26 is the multi-CELL single-blob case;
    this matcher is the multi-BLOB case (cell counts unrestricted).
  * ``output_color_uniform`` (iter 18) -- inspects change-group
    output colour content. CAN co-fire when every blob across every
    pair receives the same constant K (the simplest "paint multiple
    blobs with uniform K" recognition stack). Names the colour-pin
    side of the future multi-blob uniform-paint emission.
  * ``input_color_uniform`` (iter 19) -- inspects change-group input
    colours. CAN co-fire when every blob across every pair starts
    from the same constant colour.
  * ``consistent_color_mapping`` (iter 8) -- inspects (in, out)
    colour pairs across all groups. CAN co-fire on multi-blob pairs
    where the same input -> output mapping holds across every blob;
    can ALSO fire alone when blob count varies but per-cell mapping
    holds (orthogonal axes).
  * ``sequential_recoloring`` (iter 10) -- requires every pair to
    have the SAME non-zero number of groups N and the per-group
    output colours to form a contiguous integer range. Iter 10's
    interesting territory is N >= 2 (a multi-element sequence), so
    iter 10 CAN co-fire with this matcher when the per-pair group
    count is constant >= 2 and the outputs form a contiguous range.
    But iter 10 imposes a stricter cardinality (constant N across
    pairs) where this matcher only requires N >= 2 per pair, so they
    are NOT in a refinement relation either way: a task with pair 0
    of 2 blobs and pair 1 of 3 blobs (both uniform-output) fires this
    matcher but not iter 10. The two matchers recognise orthogonal
    sub-aspects of the multi-blob territory.
  * ``grid_size_preserved`` / ``grid_size_changed`` /
    ``output_dimensions_constant`` / ``input_dimensions_constant``
    -- dimensional axis, orthogonal to group-count axis.

Params:
  (none) -- the matcher is a pure cardinality range check on a
  scalar field. The chosen multi-blob selection (the per-pair list
  of all blob coords) is data the future rule's ``action.args`` will
  carry once the emission branch lands, not a matcher parameter.

Returns True iff:
  - ``patterns`` is a dict, AND
  - ``patterns["pair_analyses"]`` is a non-empty list, AND
  - every analysis is a dict, AND
  - every analysis carries a strict-positive-int ``num_groups``
    (not bool) with value ``>= 2``.

Why strict ``num_groups >= 2`` (not ``> 1`` open-ended phrasing): the
matcher names a SPECIFIC selection-shape sub-axis -- "two or more
connected change regions per pair" -- as the strict disjoint partner of
iter 23's "exactly one connected region per pair". Strict-positive-int
(not bool) on ``num_groups`` mirrors iter 23's posture; the lower bound
2 (not 1) is what makes this matcher disjoint from iter 23.

Why strict bool-subclass rejection on ``num_groups``: ``num_groups``
is semantically an integer count, not a Boolean. Strict comparison
forecloses ``num_groups = True`` (Python bool is an int subclass)
false positives, mirroring iters 13 / 17 / 18 / 19 / 20 / 22 / 23 /
24 / 26's strict-type postures and ``validate_rule`` V1's
``isinstance(x, bool)`` rejection on integer fields.

Why fail-closed on missing ``num_groups``: the matcher's contract is
``deterministic and side-effect-free`` (docs/RULE_FORMAT.md section 4);
a missing ``num_groups`` is upstream extractor breakage, not evidence
that the precondition holds. ``ExtractPatternOperator._analyze_pair``
has emitted ``num_groups`` since iter 1, so any current patterns dict
will carry it; the fail-closed posture preserves backwards
compatibility with any cached or partially-constructed patterns dict
the recognizer may be asked to evaluate.

Why a self-contained predicate rather than a refinement-by-call of
iter 23's negation: matchers are independent predicates in the
registry (docs/RULE_FORMAT.md section 4). Composing them at use-site
(via ``recognized_conditions`` and a conjunction of names in a future
composite-precondition step) is the canonical pattern; inlining iter
23's negation here would couple registry entries in a non-
introspectable way. The matcher implements its cardinality check
explicitly so that ``CONDITION_REGISTRY["multi_group_per_pair"]`` is
a single self-contained predicate, the same shape as every other
matcher.

No ``_analyze_pair`` change this iter: ``num_groups`` has been emitted
per pair since iter 1, so the matcher uses existing data on a stricter
cardinality gate. The companion-touch question under F8 is therefore
inert -- this iter has no ``agent/active_operators.py`` change at all.
"""

from __future__ import annotations

from agent.conditions import register


@register("multi_group_per_pair")
def match(patterns: dict, params: dict) -> bool:
    if not isinstance(patterns, dict):
        return False
    pair_analyses = patterns.get("pair_analyses")
    if not isinstance(pair_analyses, list) or not pair_analyses:
        return False

    for analysis in pair_analyses:
        if not isinstance(analysis, dict):
            return False
        n = analysis.get("num_groups")
        if not isinstance(n, int) or isinstance(n, bool):
            return False
        if n < 2:
            return False
    return True
