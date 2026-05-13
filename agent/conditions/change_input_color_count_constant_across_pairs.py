"""
change_input_color_count_constant_across_pairs -- match tasks where the
COUNT of distinct input colours involved in the per-pair change groups
(i.e. the cardinality of the per-pair frozenset of group-level
``input_colors[0]`` values) is bit-identical across every example pair,
regardless of which specific input colours those are.

Recognition vocabulary axis: ``colour-content / cross-pair input-colour
cardinality constancy``. This is the *cardinality projection* of iter 35's
``change_input_colors_constant_across_pairs`` (which inspects the
per-pair input-colour SET) -- iter 37 inspects only the per-pair SIZE
of that set, not its contents. Analogous to iter 32's relation to
iter 30 on the position-content axis: iter 30 names cross-pair coord
SET constancy; iter 32 names cross-pair total-cell-COUNT constancy.

Relation to ``change_input_colors_constant_across_pairs`` (iter 35) --
iter 37 is strictly weaker:

    iter 35 ⟹ iter 37    (per-pair input set bit-identical ⟹ per-pair
                          input-set cardinality equal)

    iter 37 ⟹̸ iter 35    (per-pair input-set cardinalities can be
                          equal while the sets themselves differ --
                          e.g. pair 0 inputs ``{1, 2}``, pair 1 inputs
                          ``{3, 4}``; both cardinality 2, distinct
                          sets; iter 37 fires, iter 35 rejects)

So iter 37 covers exclusively the territory where the *count* of
distinct input colours involved is pinned but the specific colours
are NOT pinned across pairs -- the recognition precondition for a
future rule whose action affects a constant number of input-colour
"slots" via a colour-DERIVING predicate (e.g. anti-unification lifting
``coloring``'s ``selection`` to "wherever input has any of N
training-derived colours", where N is fixed but the N colours
themselves are not). The cardinality side of iter 35's set-side
precondition.

Relation to ``input_color_uniform`` (iter 19) -- iter 37 is strictly
weaker (by the iter-35 chain: iter 19 ⟹ iter 35 ⟹ iter 37). Iter 19
fires only when every pair's input set is the single-element ``{C}``
for the same C across pairs; iter 37 fires whenever every pair's
input set has the same cardinality, regardless of contents or value.

Relation to ``change_colors_constant_across_pairs`` (iter 34) --
iter 37 is strictly weaker (by the iter-35 chain: iter 34 ⟹ iter 35
⟹ iter 37). Iter 34 fires only when per-pair full ``(ic, oc)`` sets
are bit-identical; iter 37 fires whenever the cardinality of the
per-pair input-colour projection is equal.

Relation to ``change_count_constant_across_pairs`` (iter 32) -- NOT
in a refinement relation in either direction:

  * iter 32 fires alone: a task where every pair changes the SAME
    number of cells but the involved input-colour SETS have different
    cardinalities. E.g. pair 0 has one 2-cell blob 1->5 (input-colour
    set ``{1}`` cardinality 1, cell count 2); pair 1 has two 1-cell
    blobs of input colours 1 and 3 (input-colour set ``{1, 3}``
    cardinality 2, cell count 2). Per-pair cell count constant (2 on
    both) -- iter 32 fires; per-pair input-colour-set cardinality
    1 vs 2 -- iter 37 rejects.

  * iter 37 fires alone: a task where every pair's per-pair input
    colours have the same cardinality but the per-pair cell counts
    differ. E.g. pair 0 has one 1-cell blob of colour 1 (input set
    ``{1}`` cardinality 1, cell count 1); pair 1 has one 2-cell blob
    of colour 1 (input set ``{1}`` cardinality 1, cell count 2).
    Per-pair input-colour cardinality 1 on both -- iter 37 fires;
    per-pair cell count 1 vs 2 -- iter 32 rejects.

  * Both fire: per-pair input cardinality AND per-pair cell count
    both constant (e.g. every pair has one 1-cell blob of one input
    colour, regardless of position).

  * Neither: per-pair input cardinality varies AND per-pair cell
    count varies.

The cross-pair input-colour cardinality axis is orthogonal to:

  * The position-content axis (``change_positions_constant_across_pairs``,
    iter 30; ``change_count_constant_across_pairs``, iter 32) --
    positions / cell-counts vs input-colour cardinalities. CAN
    co-fire.
  * The cross-pair output-colour set / cardinality axes (iter 36 and a
    future iter 38) -- input vs output projections. CAN co-fire.
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

Relation to ``consistent_color_mapping`` (iter 8) -- independent in both
directions, on the same logic that places iter 35 independent of iter
8: the unioned-mapping-function predicate inspects (in, out) pair
structure; this matcher inspects only per-pair input-colour set sizes.

Relation to ``sequential_recoloring`` (iter 10) -- orthogonal: iter 10
inspects per-pair output-side contiguous-range property; this matcher
inspects the per-pair input-side cardinality. CAN co-fire.

STRICTLY mutually exclusive with ``identity_transformation`` (iter 13)
in practice: identity requires every pair's ``num_groups == 0``, which
makes the per-pair input-colour set empty, which this matcher rejects
via the non-zero-cardinality clause to keep its territory disjoint
from iter 13 by construction. Mirrors iter 32's per-pair-total-zero
rejection on the cardinality axis, iter 18 / 19 / 34 / 35 / 36's
empty-set rejection on the colour axis, and iter 30's empty-union
rejection on the position axis.

Params:
  (none) -- the matcher inspects
  ``patterns["pair_analyses"][i]["groups"][j]["input_colors"]``, the
  per-group sorted list of unique input colour values emitted by
  ``_analyze_pair`` since iter 1. For each group, the matcher requires
  ``len(input_colors) == 1`` (the group's input colour is unambiguous)
  to keep the projection well-defined; the per-group
  ``input_colors[0]`` is then collected into a frozenset over all
  groups in a pair, and the CARDINALITY of the per-pair frozenset is
  compared cross-pair for equality.

Why per-group ``len(input_colors) == 1`` is required: when a single
connected blob spans multiple input colours (rare in ARC but
possible), the "input colour" of that group is ill-defined -- there
is no single ``ic`` to project onto. The matcher fail-closes on
multi-input-colour groups, mirroring iter 18 / 19 / 34 / 35 / 36's
strict per-group ``len == 1`` posture.

Returns True iff:
  - ``patterns`` is a dict, AND
  - ``patterns["pair_analyses"]`` is a non-empty list, AND
  - every analysis is a dict, AND
  - every analysis carries a list-typed ``groups`` field, AND
  - every group is a dict with a list-typed ``input_colors`` field of
    length exactly 1, AND
  - every group's ``input_colors[0]`` is a strict integer in
    ``range(10)`` (bool rejected per ``validate_rule`` V1 posture;
    out-of-range rejected as upstream extractor breakage), AND
  - the cardinality of the per-pair frozenset of group-level
    ``input_colors[0]`` values is at least 1 (the identity-territory
    rejection clause), AND
  - the cardinality is bit-identical across every pair.

Why fail-closed on zero per-pair cardinality: a patterns dict where
every pair has zero groups (the identity case) has empty per-pair
sets that have vacuously equal cardinality 0 across pairs. Allowing
that to fire here would double-cover iter 13's identity territory
under a name that promises "the count of involved input colours is
pinned" -- but there are no input colours to count. The matcher
names a non-trivial precondition; the strict refusal mirrors iter
32's per-pair-total-zero rejection, iter 18 / 19 / 34 / 35 / 36's
empty-set rejection, and iter 30's empty-union rejection.

Why a self-contained predicate rather than a refinement-by-call of
iter 35: matchers are independent predicates in the registry
(``docs/RULE_FORMAT.md`` section 4). Composing them at use-site (via
``recognized_conditions`` and a conjunction of names in a future
composite-precondition step) is the canonical pattern; inlining an
iter-35 call here would couple registry entries in a non-introspectable
way. The matcher implements its per-pair-cardinality check explicitly
so ``CONDITION_REGISTRY[
"change_input_color_count_constant_across_pairs"]`` is a single
self-contained predicate, the same shape as every other matcher.

No ``_analyze_pair`` change this iter: the ``input_colors`` field has
been emitted per group since iter 1, so the matcher uses existing
data on a new axis (the cardinality projection of iter 35's set
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


@register("change_input_color_count_constant_across_pairs")
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

        pair_input_colors: set = set()
        for group in groups:
            if not isinstance(group, dict):
                return False
            input_colors = group.get("input_colors")
            if not isinstance(input_colors, list) or len(input_colors) != 1:
                return False
            ic = input_colors[0]
            if not _is_strict_color(ic):
                return False
            pair_input_colors.add(ic)

        cardinality = len(pair_input_colors)
        if cardinality == 0:
            return False
        if canonical_card is None:
            canonical_card = cardinality
        elif canonical_card != cardinality:
            return False

    return canonical_card is not None
