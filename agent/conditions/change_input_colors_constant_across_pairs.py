"""
change_input_colors_constant_across_pairs -- match tasks where the SET of
input colours involved in the per-pair change groups is bit-identical
across every example pair.

Recognition vocabulary axis: ``colour-content / cross-pair input-set
constancy``. This is the *input-side projection* of iter 34's
``change_colors_constant_across_pairs`` (which inspects the full
``(input_colour, output_colour)`` set) -- iter 35 inspects only the
``input_colour`` projection of that set on a per-pair basis.

Relation to ``change_colors_constant_across_pairs`` (iter 34) -- iter 35
is strictly weaker:

    iter 34 ⟹ iter 35    (per-pair ``(ic, oc)`` set bit-identical ⟹
                          projecting on the first coordinate gives
                          bit-identical per-pair sets too)

    iter 35 ⟹̸ iter 34    (per-pair input sets can be bit-identical
                          while the per-pair output sets differ -- e.g.
                          pair 0 maps {1 → 2}, pair 1 maps {1 → 3};
                          per-pair input set is {1} on both, but
                          per-pair full set differs -- iter 35 fires,
                          iter 34 rejects)

Relation to ``input_color_uniform`` (iter 19) -- iter 35 is strictly
weaker:

    iter 19 ⟹ iter 35    (every group across every pair shares one
                          single input colour C ⟹ each pair's input
                          set is {C}, bit-identical across pairs)

    iter 35 ⟹̸ iter 19    (per-pair sets can be bit-identical with
                          cardinality > 1 -- e.g. pair 0 inputs
                          {1, 2}, pair 1 inputs {1, 2}; iter 19's
                          ``len(union) == 1`` clause rejects, iter 35
                          fires; the multi-input-colour-per-pair
                          recognition territory iter 19 does NOT name)

So iter 35 strictly weakens BOTH iter 34 (on the output-side
information dropped) AND iter 19 (on the cross-pair uniformity vs
cross-pair set-constancy distinction).

Why this matters for the schema:

  * Iter 19's matcher fires only when the entire union collapses to a
    single colour C. The natural strict weakening -- "every pair
    involves the SAME set of input colours, possibly more than one" --
    is the precondition for a recolour rule whose action stores a
    literal input-colour list AND a derived selection predicate
    (``where input has one of {C_1, ..., C_k}``). Without this matcher
    the multi-input-colour cross-pair-set-constant territory iter 19
    cannot name has no recognition handle.
  * Iter 34's matcher names cross-pair constancy of the FULL
    ``(input, output)`` mapping set. When the output side varies but
    the input side is pinned, iter 34 rejects (correctly: the
    ``(ic, oc)`` set is not identical) but iter 35 still fires
    (correctly: the input-colour set IS identical). That territory --
    "the input colours involved are pinned across pairs, but the
    output choice varies" -- is the recognition precondition for a
    future derived-selection rule where the selection is determined
    by training-pinned input colours and the colour is determined by
    a downstream branch (e.g. position-conditional output).
  * Cross-axis completion: iter 35 sits as the input-side projection
    on the cross-pair set-constancy axis that iter 34 introduced on
    the full ``(ic, oc)`` axis. A companion output-side projection
    matcher (deferred to a future iter) would complete the
    input/output × projection symmetry on the cross-pair set-
    constancy axis, mirroring the iter-18 / iter-19 input/output
    symmetric completion on the uniformity sub-axis.

Relation to ``consistent_color_mapping`` (iter 8) -- INDEPENDENT in
both directions:

  * iter 8 fires alone: pair 0 maps {1 → 2}, pair 1 maps {3 → 4}. The
    unioned mapping {1 → 2, 3 → 4} is functional (iter 8 fires).
    Per-pair input sets {1} vs {3} differ (iter 35 rejects).
  * iter 35 fires alone: pair 0 maps {1 → 2}, pair 1 maps {1 → 3}.
    Per-pair input sets {1} vs {1} are identical (iter 35 fires).
    Unioned mapping {1 → {2, 3}} is non-functional (iter 8 rejects).
  * Both fire: pair 0 maps {1 → 2}, pair 1 maps {1 → 2}. Per-pair
    input sets {1} bit-identical; unioned mapping {1 → 2} functional.
  * Neither: pair 0 maps {1 → 2}, pair 1 maps {1 → 3, 5 → 6}.
    Per-pair input sets {1} vs {1, 5} differ (iter 35 rejects).
    Unioned mapping {1 → {2, 3}, 5 → 6} non-functional (iter 8 rejects).

So iter 35 is NOT in a refinement relation with iter 8 either way --
they cover orthogonal sub-axes of the colour-content recognition
territory, the same way iter 19 is independent of iter 8.

The cross-pair input-set constancy axis is orthogonal to:

  * The position-content axis
    (``change_positions_constant_across_pairs``, iter 30) -- positions
    vs input colours are independent content axes. CAN co-fire.
  * The cardinality axis
    (``change_count_constant_across_pairs``, iter 32) -- counts vs
    input colours are independent. CAN co-fire.
  * The dimensional axes (``grid_size_preserved`` /
    ``grid_size_changed`` / ``output_dimensions_constant`` /
    ``input_dimensions_constant`` /
    ``output_dimensions_multiple_of_input``) -- those inspect grid
    shape, not colour content. Orthogonal.
  * The group-count axis (``identity_transformation`` /
    ``single_change_group_per_pair`` / ``multi_group_per_pair``) --
    those inspect ``num_groups``, not colour content. Orthogonal.
  * The cell-count sub-axis (``single_cell_change_per_pair`` /
    ``multi_cell_change_group_per_pair``) -- those inspect per-group
    ``cell_count`` under ``num_groups == 1``, not colour content.
    Orthogonal.

Relation to ``sequential_recoloring`` (iter 10) -- orthogonal: iter 10
inspects the OUTPUT side's contiguous-range property, this matcher
inspects the INPUT side's cross-pair set constancy. CAN co-fire (a
constant-input multi-group recolour with contiguous outputs per pair)
or fire independently.

Relation to ``output_color_uniform`` (iter 18) -- orthogonal: iter 18
inspects the OUTPUT side's cross-all-groups uniformity, this matcher
inspects the INPUT side's cross-pair set constancy. CAN co-fire (the
simplest "paint cells of these input colours with this constant K"
recognition stack) or fire independently.

Params:
  (none) -- the matcher inspects
  ``patterns["pair_analyses"][i]["groups"][j]["input_colors"]``, the
  per-group sorted list of unique input colour values emitted by
  ``_analyze_pair`` since iter 1. For each group, the matcher requires
  ``len(input_colors) == 1`` (the group's input colour is unambiguous);
  the per-group ``input_colors[0]`` is then collected into a frozenset
  over all groups in a pair, and the per-pair frozenset is compared
  cross-pair for equality.

Why per-group ``len(input_colors) == 1`` is required: when a single
connected blob spans multiple input colours (rare in ARC but
possible), the "input colour" of that group is ill-defined -- there is
no single ``ic`` to project onto. Falling back to including ALL the
group's input colours in the per-pair set would silently over-count
and risk false positives under cross-pair comparison. The matcher
fail-closes on multi-input-colour groups instead, mirroring iter 18 /
19 / 34's strict per-group ``len == 1`` posture.

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
  - the per-pair frozenset of group-level ``input_colors[0]`` values
    is non-empty (the identity-territory rejection clause), AND
  - the per-pair frozenset is bit-identical across every pair.

Why fail-closed on empty per-pair sets: a patterns dict where every
pair has zero groups (the identity case) has empty per-pair sets that
are vacuously equal across pairs. Allowing that to fire here would
double-cover iter 13's ``identity_transformation`` territory under a
name that promises "the set of input colours involved is pinned" --
but there are no input colours to pin. The matcher names a
non-trivial precondition; the strict refusal mirrors iter 30's
empty-union rejection on the position axis, iter 32's
per-pair-total-zero rejection on the cardinality axis, iter 18 / 19's
strict refusal of zero-group pairs on the colour axis, and iter 34's
per-pair empty-set rejection on the full colour-pair axis.

Why strict integer-in-range(10) on colours: ARC colours are integers
in 0..9 (the ``coloring`` primitive additionally accepts the ``13``
transparency sentinel, but ``_analyze_pair`` only emits colours
observed in the actual grids, which are 0..9). A missing or
out-of-range colour is upstream extractor breakage, not evidence the
precondition holds. Strict comparison forecloses bool-subclass false
positives (``True``/``False`` would otherwise compare equal to
``1``/``0``) and out-of-range integers, mirroring iter 18 / 19 / 34's
strict colour-set posture.

Why a self-contained predicate rather than a composition of
``input_color_uniform`` + a cross-pair set check: matchers are
independent predicates in the registry (``docs/RULE_FORMAT.md``
section 4). Composing them at use-site (via ``recognized_conditions``
and a conjunction of names in a future composite-precondition step)
is the canonical pattern; inlining an iter-19 call here would couple
registry entries in a non-introspectable way. The matcher implements
its cross-pair set check explicitly so
``CONDITION_REGISTRY["change_input_colors_constant_across_pairs"]`` is
a single self-contained predicate, the same shape as every other
matcher.

No ``_analyze_pair`` change this iter: the ``input_colors`` field has
been emitted per group since iter 1, so the matcher uses existing
data on a new axis. The companion-touch question under F8 is
therefore inert -- this iter has no ``agent/active_operators.py``
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


@register("change_input_colors_constant_across_pairs")
def match(patterns: dict, params: dict) -> bool:
    if not isinstance(patterns, dict):
        return False
    pair_analyses = patterns.get("pair_analyses")
    if not isinstance(pair_analyses, list) or not pair_analyses:
        return False

    canonical: frozenset | None = None

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

        if not pair_input_colors:
            return False
        pair_set = frozenset(pair_input_colors)
        if canonical is None:
            canonical = pair_set
        elif canonical != pair_set:
            return False

    return canonical is not None
