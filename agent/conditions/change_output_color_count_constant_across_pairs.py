"""
change_output_color_count_constant_across_pairs -- match tasks where the
COUNT of distinct output colours produced in the per-pair change groups
(i.e. the cardinality of the per-pair frozenset of group-level
``output_colors[0]`` values) is bit-identical across every example pair,
regardless of which specific output colours those are.

Recognition vocabulary axis: ``colour-content / cross-pair output-colour
cardinality constancy``. This is the *cardinality projection* of iter 36's
``change_output_colors_constant_across_pairs`` (which inspects the
per-pair output-colour SET) -- iter 38 inspects only the per-pair SIZE
of that set, not its contents. The OUTPUT-side mirror of iter 37's
``change_input_color_count_constant_across_pairs``: iter 37 is the
cardinality projection of iter 35 on the input axis; iter 38 is the
cardinality projection of iter 36 on the output axis. Together iter 37 +
iter 38 complete the input/output × set/cardinality 2x2 grid on the
cross-pair colour-set-constancy axis (iter 34's two-coordinate axis).
The iter-32-to-iter-30 cardinality-projection pattern, applied to iter
36's output-colour set axis.

Relation to ``change_output_colors_constant_across_pairs`` (iter 36) --
iter 38 is strictly weaker:

    iter 36 ⟹ iter 38    (per-pair output set bit-identical ⟹ per-pair
                          output-set cardinality equal)

    iter 38 ⟹̸ iter 36    (per-pair output-set cardinalities can be
                          equal while the sets themselves differ --
                          e.g. pair 0 outputs ``{1, 2}``, pair 1 outputs
                          ``{3, 4}``; both cardinality 2, distinct
                          sets; iter 38 fires, iter 36 rejects)

So iter 38 covers exclusively the territory where the *count* of
distinct output colours produced is pinned but the specific colours
are NOT pinned across pairs -- the recognition precondition for a
future rule whose action produces a constant number of output-colour
"slots" via a colour-DERIVING predicate (e.g. anti-unification lifting
``coloring``'s ``color`` to "any of N training-derived output colours",
where N is fixed but the N colours themselves are not). The cardinality
side of iter 36's set-side precondition.

Relation to ``output_color_uniform`` (iter 18) -- iter 38 is strictly
weaker (by the iter-36 chain: iter 18 ⟹ iter 36 ⟹ iter 38). Iter 18
fires only when every pair's output set is the single-element ``{K}``
for the same K across pairs; iter 38 fires whenever every pair's
output set has the same cardinality, regardless of contents or value.

Relation to ``change_colors_constant_across_pairs`` (iter 34) --
iter 38 is strictly weaker (by the iter-36 chain: iter 34 ⟹ iter 36
⟹ iter 38). Iter 34 fires only when per-pair full ``(ic, oc)`` sets
are bit-identical; iter 38 fires whenever the cardinality of the
per-pair output-colour projection is equal.

Relation to ``change_input_color_count_constant_across_pairs`` (iter 37)
-- INDEPENDENT in both directions, on the projection-axis (symmetric
to iter 35-vs-iter 36 independence on the set axis):

  * iter 37 fires alone: pair 0 maps ``{1 → 2}``, pair 1 maps
    ``{1 → 3}``. Per-pair input cardinality 1 on both (iter 37 fires);
    per-pair output sets ``{2}`` vs ``{3}`` -- cardinality 1 on both
    so iter 38 ALSO fires here. To get a clean iter-37-alone case,
    need per-pair output CARDINALITIES to differ. Try pair 0 maps
    ``{1 → 2}``, pair 1 maps ``{1 → 2, 1 → 3}`` -- but a single group
    has one oc by the matcher's len==1 posture, so we need multi-group
    pair 1. Try pair 0 has one group ``1 → 2`` (input card 1, output
    card 1); pair 1 has two groups ``1 → 2`` and ``1 → 3`` -- but
    per-group input_colors=[1] would mean iter 37's per-pair input set
    is ``{1}`` (card 1) on both, AND iter 38's per-pair output set is
    ``{2}`` (card 1) on pair 0 and ``{2, 3}`` (card 2) on pair 1. Iter
    37 fires (input cards both 1), iter 38 rejects (output cards 1 vs 2).
  * iter 38 fires alone: pair 0 has one group ``1 → 2`` (input card 1,
    output card 1); pair 1 has two groups ``1 → 2`` and ``3 → 2`` --
    per-pair input set ``{1}`` (card 1) vs ``{1, 3}`` (card 2), iter 37
    rejects; per-pair output set ``{2}`` (card 1) on both, iter 38 fires.
  * Both: pair 0 has one group ``1 → 2`` (input card 1, output card 1);
    pair 1 has one group ``3 → 4`` (input card 1, output card 1). Iter
    37 fires (input cards both 1); iter 38 fires (output cards both 1).
    Iter 35 / 36 reject (sets differ). This is the iter-37-and-iter-38
    co-fire territory iter 35 / 36 cannot name.
  * Neither: per-pair input cardinality varies AND per-pair output
    cardinality varies.

Relation to ``change_count_constant_across_pairs`` (iter 32) -- NOT
in a refinement relation in either direction (symmetric to iter 37's
independence with iter 32):

  * iter 32 fires alone: a task where every pair changes the SAME
    number of cells but the involved output-colour SETS have different
    cardinalities. E.g. pair 0 has one 2-cell blob ``1 → 5`` (output
    set ``{5}`` card 1, cell count 2); pair 1 has two 1-cell blobs of
    output colours 5 and 7 (output set ``{5, 7}`` card 2, cell count
    2). Per-pair cell count constant (2 on both) -- iter 32 fires;
    per-pair output-cardinality 1 vs 2 -- iter 38 rejects.

  * iter 38 fires alone: a task where every pair's per-pair output
    colours have the same cardinality but the per-pair cell counts
    differ. E.g. pair 0 has one 1-cell blob of output 5 (card 1,
    count 1); pair 1 has one 2-cell blob of output 5 (card 1, count
    2). Per-pair output cardinality 1 on both -- iter 38 fires;
    per-pair cell count 1 vs 2 -- iter 32 rejects.

  * Both: per-pair output cardinality AND per-pair cell count both
    constant.

  * Neither: per-pair output cardinality varies AND per-pair cell
    count varies.

The cross-pair output-colour cardinality axis is orthogonal to:

  * The position-content axis (``change_positions_constant_across_pairs``,
    iter 30; ``change_count_constant_across_pairs``, iter 32) --
    positions / cell-counts vs output-colour cardinalities. CAN
    co-fire.
  * The cross-pair input-colour set / cardinality axes (iter 35,
    iter 37) -- input vs output projections. CAN co-fire.
  * The dimensional axes (``grid_size_preserved`` / ``grid_size_changed``
    / ``output_dimensions_constant`` / ``input_dimensions_constant`` /
    ``output_dimensions_multiple_of_input``) -- those inspect grid
    shape, not colour content. CAN co-fire.
  * The group-count axis (``identity_transformation`` /
    ``single_change_group_per_pair`` / ``multi_group_per_pair``) --
    those inspect ``num_groups``, not colour cardinality. CAN co-fire.
  * The cell-count sub-axis (``single_cell_change_per_pair`` /
    ``multi_cell_change_group_per_pair``) -- those inspect per-group
    ``cell_count`` under ``num_groups == 1``, not colour cardinality.
    CAN co-fire.

Relation to ``consistent_color_mapping`` (iter 8) -- independent in
both directions, on the same logic that places iter 36 independent of
iter 8: the unioned-mapping-function predicate inspects (in, out) pair
structure; this matcher inspects only per-pair output-colour set sizes.

Relation to ``sequential_recoloring`` (iter 10) -- orthogonal: iter 10
inspects per-pair output-side contiguous-range property; this matcher
inspects the per-pair output-side cardinality (a SIZE, not a SHAPE).
CAN co-fire (a constant-card multi-group recolour where each pair's
outputs form a contiguous range of the same length) or fire
independently.

STRICTLY mutually exclusive with ``identity_transformation`` (iter 13)
in practice: identity requires every pair's ``num_groups == 0``, which
makes the per-pair output-colour set empty, which this matcher rejects
via the non-zero-cardinality clause to keep its territory disjoint
from iter 13 by construction. Mirrors iter 37's identity-territory
rejection on the input-cardinality axis, iter 32's per-pair-total-zero
rejection on the cell-count axis, iter 18 / 19 / 34 / 35 / 36's
empty-set rejection on the colour axis, and iter 30's empty-union
rejection on the position axis.

Params:
  (none) -- the matcher inspects
  ``patterns["pair_analyses"][i]["groups"][j]["output_colors"]``, the
  per-group sorted list of unique output colour values emitted by
  ``_analyze_pair`` since iter 1. For each group, the matcher requires
  ``len(output_colors) == 1`` (the group's output colour is unambiguous)
  to keep the projection well-defined; the per-group
  ``output_colors[0]`` is then collected into a frozenset over all
  groups in a pair, and the CARDINALITY of the per-pair frozenset is
  compared cross-pair for equality.

Why per-group ``len(output_colors) == 1`` is required: when a single
connected blob spans multiple output colours (rare in ARC but
possible), the "output colour" of that group is ill-defined -- there
is no single ``oc`` to project onto. The matcher fail-closes on
multi-output-colour groups, mirroring iter 18 / 19 / 34 / 35 / 36 / 37's
strict per-group ``len == 1`` posture.

Returns True iff:
  - ``patterns`` is a dict, AND
  - ``patterns["pair_analyses"]`` is a non-empty list, AND
  - every analysis is a dict, AND
  - every analysis carries a list-typed ``groups`` field, AND
  - every group is a dict with a list-typed ``output_colors`` field of
    length exactly 1, AND
  - every group's ``output_colors[0]`` is a strict integer in
    ``range(10)`` (bool rejected per ``validate_rule`` V1 posture;
    out-of-range rejected as upstream extractor breakage), AND
  - the cardinality of the per-pair frozenset of group-level
    ``output_colors[0]`` values is at least 1 (the identity-territory
    rejection clause), AND
  - the cardinality is bit-identical across every pair.

Why fail-closed on zero per-pair cardinality: a patterns dict where
every pair has zero groups (the identity case) has empty per-pair
sets that have vacuously equal cardinality 0 across pairs. Allowing
that to fire here would double-cover iter 13's identity territory
under a name that promises "the count of involved output colours is
pinned" -- but there are no output colours to count. The matcher
names a non-trivial precondition; the strict refusal mirrors iter
37's per-pair-zero-cardinality rejection on the input axis, iter 32's
per-pair-total-zero rejection on the cell-count axis, iter 18 / 19 / 34
/ 35 / 36's empty-set rejection, and iter 30's empty-union rejection.

Why a self-contained predicate rather than a refinement-by-call of
iter 36: matchers are independent predicates in the registry
(``docs/RULE_FORMAT.md`` section 4). Composing them at use-site (via
``recognized_conditions`` and a conjunction of names in a future
composite-precondition step) is the canonical pattern; inlining an
iter-36 call here would couple registry entries in a non-introspectable
way. The matcher implements its per-pair-cardinality check explicitly
so ``CONDITION_REGISTRY[
"change_output_color_count_constant_across_pairs"]`` is a single
self-contained predicate, the same shape as every other matcher.

No ``_analyze_pair`` change this iter: the ``output_colors`` field has
been emitted per group since iter 1, so the matcher uses existing
data on a new axis (the cardinality projection of iter 36's set
axis). F8 inert -- this iter has no ``agent/active_operators.py``
change at all.
"""

from __future__ import annotations

from agent.conditions import register


def _is_strict_color(x) -> bool:
    return (
        isinstance(x, int)
        and not isinstance(x, bool)
        and 0 <= x <= 9
    )


@register("change_output_color_count_constant_across_pairs")
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
        if not isinstance(groups, list):
            return False

        pair_output_colors: set = set()
        for group in groups:
            if not isinstance(group, dict):
                return False
            output_colors = group.get("output_colors")
            if not isinstance(output_colors, list) or len(output_colors) != 1:
                return False
            oc = output_colors[0]
            if not _is_strict_color(oc):
                return False
            pair_output_colors.add(oc)

        cardinality = len(pair_output_colors)
        if cardinality == 0:
            return False
        if canonical_card is None:
            canonical_card = cardinality
        elif canonical_card != cardinality:
            return False

    return canonical_card is not None
