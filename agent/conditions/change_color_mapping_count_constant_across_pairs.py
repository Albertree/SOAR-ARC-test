"""
change_color_mapping_count_constant_across_pairs -- match tasks where the
COUNT of distinct (input_colour, output_colour) mappings produced in the
per-pair change groups (i.e. the cardinality of the per-pair frozenset of
group-level ``(input_colors[0], output_colors[0])`` tuples) is bit-identical
across every example pair, regardless of which specific mappings those are.

Recognition vocabulary axis: ``colour-content / cross-pair colour-mapping
cardinality constancy``. This is the *cardinality projection* of iter 34's
``change_colors_constant_across_pairs`` (which inspects the per-pair
(ic, oc) SET) -- this matcher inspects only the per-pair SIZE of that
set, not its contents. It completes the cardinality-projection cadence
already on disk:

  * iter 30 (positions SET) -> iter 32 (positions COUNT)
  * iter 35 (input colours SET) -> iter 37 (input colours COUNT)
  * iter 36 (output colours SET) -> iter 38 (output colours COUNT)
  * iters 23 / 28 (group-count specific-N) -> iter 39
    ``change_group_count_constant_across_pairs`` (group COUNT constancy)
  * iter 34 ((ic, oc) SET) -> THIS MATCHER ((ic, oc) COUNT)

The remaining set-axis without a named cardinality projection is iter
34's, and this matcher fills it.

Relation to ``change_colors_constant_across_pairs`` (iter 34) -- this
matcher is strictly weaker:

    iter 34 => this matcher    (per-pair (ic, oc) set bit-identical
                                ==> per-pair set cardinality equal)

    this matcher =/=> iter 34  (per-pair set cardinalities can be
                                equal while the sets themselves differ
                                -- e.g. pair 0 has {(1, 2), (3, 4)},
                                pair 1 has {(5, 6), (7, 8)}; both
                                cardinality 2, distinct sets; this
                                matcher fires, iter 34 rejects)

So this matcher covers exclusively the territory where the *count* of
distinct (ic, oc) mappings is pinned but the specific mappings are NOT
pinned across pairs -- the recognition precondition for a future rule
whose action produces a constant number of recolour "slots" via an
anti-unification-derived predicate (e.g. anti-unification lifting the
mapping table itself to "any of N training-derived recolours", where
N is fixed but the N mappings themselves are not).

Relation to ``change_input_color_count_constant_across_pairs`` (iter 37)
-- NOT in a refinement relation in either direction:

  * iter 37 fires alone: per-pair input-colour cardinalities equal, but
    per-pair (ic, oc) cardinalities differ. E.g. pair 0 has {(1, 2)}
    (one input, one mapping), pair 1 has {(1, 2), (1, 3)} (one input,
    two mappings because input 1 maps to two different outputs in
    different cells). Per-pair input-colour set cardinality is 1 on
    both -- iter 37 fires; per-pair (ic, oc) set cardinality 1 vs 2
    -- this matcher rejects.

  * this matcher fires alone: per-pair (ic, oc) cardinalities equal,
    but per-pair input-colour cardinalities differ. E.g. pair 0 has
    {(1, 2), (3, 2)} (two inputs, two mappings, both to 2), pair 1 has
    {(1, 2), (1, 3)} (one input, two mappings, to 2 and 3). Per-pair
    (ic, oc) cardinality 2 on both -- this matcher fires; per-pair
    input-colour cardinalities 2 vs 1 -- iter 37 rejects.

  * Both fire: per-pair (ic, oc) cardinality AND per-pair input-colour
    cardinality both constant. The common case for well-behaved
    1-to-1 recolour tasks.

  * Neither fires: per-pair (ic, oc) cardinalities vary AND per-pair
    input-colour cardinalities vary.

Symmetric independence holds with
``change_output_color_count_constant_across_pairs`` (iter 38) on the
output-colour cardinality axis -- swap "input" for "output" in the
example above. The (ic, oc) cardinality is bounded below by
max(input_card, output_card) but can exceed both.

Relation to ``consistent_color_mapping`` (iter 8) -- INDEPENDENT in
both directions, on the same logic that places iter 34 independent of
iter 8 on the set axis: iter 8 inspects the unioned-mapping-function
predicate (every input colour maps to at most one output across all
groups in all pairs); this matcher inspects only per-pair (ic, oc)
set sizes, which can be unequal even when the union is functional
(see iter 34's docstring for the worked example).

Relation to ``sequential_recoloring`` (iter 10) -- orthogonal: iter
10 inspects per-pair output-side contiguous-range property; this
matcher inspects the cardinality of the per-pair (ic, oc) projection.
CAN co-fire when a pair's outputs are a contiguous range AND the
(ic, oc) cardinality is constant across pairs (e.g. iter 10's
fixture in ``_patterns_all_three_fire`` -- both pairs have the
same (ic, oc) set with cardinality 3 AND the per-pair output sets
form contiguous ranges).

Relation to ``change_count_constant_across_pairs`` (iter 32) -- NOT
in a refinement relation in either direction (positions count vs
mapping count, orthogonal axes).

Relation to ``change_group_count_constant_across_pairs`` (iter 39)
-- NOT in a refinement relation. The per-pair (ic, oc) cardinality
is bounded above by ``num_groups`` (each group contributes at most
one (ic, oc) pair) but can be strictly less when two groups share
the same (ic, oc). So group-count constancy does not imply
mapping-count constancy (different groups, same (ic, oc) collapse),
and mapping-count constancy does not imply group-count constancy
(more groups all sharing one (ic, oc) vs fewer groups each with a
distinct (ic, oc)). Orthogonal axes.

Relation to ``output_color_uniform`` (iter 18) -- iter 18 strictly
refines this matcher in a non-trivial way: when iter 18 fires every
group has the same output colour K across all groups in all pairs,
so the per-pair (ic, oc) set is ``{(ic, K) : ic in pair's input
set}``. By iter-19's reasoning on the input axis, when iter 18 fires
alone (without iter 19) the per-pair (ic, oc) cardinality equals the
per-pair input-colour cardinality. iter 18 does NOT pin that
cardinality across pairs by itself -- so the implication ``iter 18
==> this matcher`` does NOT hold in general. They are independent.

Relation to ``input_color_uniform`` (iter 19) -- symmetric to the
iter-18 analysis. Independent.

STRICTLY mutually exclusive with ``identity_transformation`` (iter
13) in practice: identity requires every pair's ``num_groups == 0``,
which makes the per-pair (ic, oc) set empty, which this matcher
rejects via the non-zero-cardinality clause to keep its territory
disjoint from iter 13 by construction. Mirrors iter 32 / 37 / 38 /
39's identity-territory rejection on their respective cardinality
axes.

Why this matters for the schema:

  * Iters 35 / 36 / 34 each have a named cardinality projection (iters
    37 / 38 / THIS MATCHER); together they form a complete grid on
    the cross-pair colour-content axis: input vs output vs combined,
    set vs cardinality. Every colour-content set-constancy matcher
    now has a named cardinality sibling.
  * Per-attempt ``fired_conditions`` (written to
    ``episodic_memory/<task>/attempt_NNN/metadata.json`` since iter
    12) gains a directly inspectable signal for "this task's number
    of distinct colour-recolour pairs is pinned across pairs" -- one
    more named axis the instrumentation surfaces without needing a
    translate_to_schema branch to consume it. Recognition vocabulary
    ahead of emission, the same posture iters 17 / 18 / 19 / 20 / 22 /
    23 / 24 / 26 / 28 / 30 / 32 / 33 / 34 / 35 / 36 / 37 / 38 / 39 all
    carry.

The cross-pair (ic, oc) cardinality axis is orthogonal to:

  * The position-content axes (``change_positions_constant_across_pairs``,
    iter 30; ``change_count_constant_across_pairs``, iter 32) --
    positions / cell counts vs colour-mapping cardinality. CAN
    co-fire.
  * The dimensional axes (``grid_size_preserved`` / ``grid_size_changed``
    / ``output_dimensions_constant`` / ``input_dimensions_constant`` /
    ``output_dimensions_multiple_of_input``) -- those inspect grid
    shape, not colour content. CAN co-fire.
  * The group-count axis (``identity_transformation`` /
    ``single_change_group_per_pair`` / ``multi_group_per_pair`` /
    ``change_group_count_constant_across_pairs``) -- those inspect
    ``num_groups``; this matcher inspects per-pair (ic, oc) set
    sizes. CAN co-fire (and frequently will, since each group
    contributes at most one (ic, oc) pair).
  * The cell-count sub-axis (``single_cell_change_per_pair`` /
    ``multi_cell_change_group_per_pair``) -- those inspect per-group
    ``cell_count`` under ``num_groups == 1``, not colour content.
    CAN co-fire.

Params:
  (none) -- the matcher inspects
  ``patterns["pair_analyses"][i]["groups"][j]["input_colors"]`` and
  ``["output_colors"]``, the per-group sorted lists of unique colour
  values emitted by ``_analyze_pair`` since iter 1. For each group,
  the matcher requires ``len(input_colors) == 1`` AND
  ``len(output_colors) == 1`` (the group's colour pair is
  unambiguous); the per-group ``(input_colors[0], output_colors[0])``
  is then collected into a frozenset over all groups in a pair, and
  the CARDINALITY of the per-pair frozenset is compared cross-pair
  for equality.

Why per-group ``len == 1`` is required: when a single connected blob
spans multiple input or output colours (rare in ARC but possible),
the "colour pair" of that group is ill-defined. The matcher
fail-closes on multi-colour groups, mirroring iter 18 / 19 / 34's
strict per-group ``len == 1`` posture.

Returns True iff:
  - ``patterns`` is a dict, AND
  - ``patterns["pair_analyses"]`` is a non-empty list, AND
  - every analysis is a dict, AND
  - every analysis carries a list-typed ``groups`` field, AND
  - every group is a dict with list-typed ``input_colors`` and
    ``output_colors`` fields, each of length exactly 1, AND
  - every colour value is a strict integer in ``range(10)`` (bool
    rejected per ``validate_rule`` V1 posture; out-of-range rejected
    as upstream extractor breakage), AND
  - the cardinality of the per-pair frozenset of group-level
    ``(ic, oc)`` pairs is at least 1 (the identity-territory rejection
    clause), AND
  - the cardinality is bit-identical across every pair.

Why fail-closed on zero per-pair cardinality: a patterns dict where
every pair has zero groups (the identity case) has empty per-pair
sets that have vacuously equal cardinality 0 across pairs. Allowing
that to fire here would double-cover iter 13's identity territory
under a name that promises "the count of distinct recolour mappings
is pinned" -- but there are no mappings to count. The matcher names
a non-trivial precondition; the strict refusal mirrors iter 32's
per-pair-total-zero rejection, iter 37 / 38 / 39's
per-pair-zero-cardinality rejection, iter 30's empty-union rejection,
and iter 18 / 19 / 34 / 35 / 36's empty-set rejection.

Why a self-contained predicate rather than a refinement-by-call of
iter 34: matchers are independent predicates in the registry
(``docs/RULE_FORMAT.md`` section 4). Composing them at use-site (via
``recognized_conditions`` and a conjunction of names in a future
composite-precondition step) is the canonical pattern; inlining an
iter-34 call here would couple registry entries in a non-introspectable
way. The matcher implements its per-pair-cardinality check explicitly
so ``CONDITION_REGISTRY[
"change_color_mapping_count_constant_across_pairs"]`` is a single
self-contained predicate, the same shape as every other matcher.

No ``_analyze_pair`` change this iter: the ``input_colors`` and
``output_colors`` fields have been emitted per group since iter 1, so
the matcher uses existing data on a new axis (the cardinality
projection of iter 34's set axis). F8 inert -- this iter has no
``agent/active_operators.py`` change at all.
"""

from __future__ import annotations

from agent.conditions import register


def _is_strict_color(x) -> bool:
    return (
        isinstance(x, int)
        and not isinstance(x, bool)
        and 0 <= x <= 9
    )


@register("change_color_mapping_count_constant_across_pairs")
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

        pair_pairs: set = set()
        for group in groups:
            if not isinstance(group, dict):
                return False
            input_colors = group.get("input_colors")
            output_colors = group.get("output_colors")
            if not isinstance(input_colors, list) or len(input_colors) != 1:
                return False
            if not isinstance(output_colors, list) or len(output_colors) != 1:
                return False
            ic = input_colors[0]
            oc = output_colors[0]
            if not _is_strict_color(ic):
                return False
            if not _is_strict_color(oc):
                return False
            pair_pairs.add((ic, oc))

        cardinality = len(pair_pairs)
        if cardinality == 0:
            return False
        if canonical_card is None:
            canonical_card = cardinality
        elif canonical_card != cardinality:
            return False

    return canonical_card is not None
