"""
change_output_colors_constant_across_pairs -- match tasks where the SET
of output colours produced in the per-pair change groups is bit-identical
across every example pair.

Recognition vocabulary axis: ``colour-content / cross-pair output-set
constancy``. This is the *output-side projection* of iter 34's
``change_colors_constant_across_pairs`` (which inspects the full
``(input_colour, output_colour)`` set) -- iter 36 inspects only the
``output_colour`` projection of that set on a per-pair basis. The
output-side mirror of iter 35's input-side projection
``change_input_colors_constant_across_pairs``.

Relation to ``change_colors_constant_across_pairs`` (iter 34) -- iter 36
is strictly weaker:

    iter 34 ⟹ iter 36    (per-pair ``(ic, oc)`` set bit-identical ⟹
                          projecting on the second coordinate gives
                          bit-identical per-pair sets too)

    iter 36 ⟹̸ iter 34    (per-pair output sets can be bit-identical
                          while the per-pair input sets differ -- e.g.
                          pair 0 maps {1 → 5}, pair 1 maps {2 → 5};
                          per-pair output set is {5} on both, but
                          per-pair full set differs -- iter 36 fires,
                          iter 34 rejects)

Relation to ``output_color_uniform`` (iter 18) -- iter 36 is strictly
weaker:

    iter 18 ⟹ iter 36    (every group across every pair shares one
                          single output colour K ⟹ each pair's output
                          set is {K}, bit-identical across pairs)

    iter 36 ⟹̸ iter 18    (per-pair sets can be bit-identical with
                          cardinality > 1 -- e.g. pair 0 outputs
                          {2, 3}, pair 1 outputs {2, 3}; iter 18's
                          single-output-across-all-groups clause
                          rejects, iter 36 fires; the
                          multi-output-colour-per-pair recognition
                          territory iter 18 does NOT name)

So iter 36 strictly weakens BOTH iter 34 (on the input-side
information dropped) AND iter 18 (on the cross-pair uniformity vs
cross-pair set-constancy distinction). Iter 36 is the OUTPUT-side
mirror of iter 35: iter 35 names the input-projection on the
cross-pair set-constancy axis (strict refinement of iter 19), iter 36
names the output-projection on the same axis (strict refinement of
iter 18). Together they complete the input/output × projection
symmetry on the cross-pair set-constancy axis, mirroring the iter-18 /
iter-19 input/output symmetric completion on the uniformity sub-axis.

Why this matters for the schema:

  * Iter 18's matcher fires only when the entire union of output
    colours collapses to a single colour K. The natural strict
    weakening -- "every pair produces the SAME set of output colours,
    possibly more than one" -- is the precondition for a recolour rule
    whose action stores a literal output-colour list AND a selection
    predicate keyed on position / structure rather than on output
    colour. Without this matcher the multi-output-colour cross-pair-
    set-constant territory iter 18 cannot name has no recognition
    handle.
  * Iter 34's matcher names cross-pair constancy of the FULL
    ``(input, output)`` mapping set. When the input side varies but
    the output side is pinned, iter 34 rejects (correctly: the
    ``(ic, oc)`` set is not identical) but iter 36 still fires
    (correctly: the output-colour set IS identical). That territory --
    "the output colours produced are pinned across pairs, but the
    input choice varies" -- is the recognition precondition for a
    future derived-rule where the output palette is a training-pinned
    constant set (e.g. position-conditional output choice over a
    fixed palette) regardless of which input colours triggered each
    output.
  * Cross-axis completion: iter 36 sits as the output-side projection
    on the cross-pair set-constancy axis that iter 34 introduced on
    the full ``(ic, oc)`` axis, completing the input/output ×
    projection symmetry pair that iter 35 opened. The cross-pair
    set-constancy axis now has three named matchers in the projection
    / union sub-axes: full set (iter 34 -- ``(ic, oc)`` pair), input
    projection (iter 35 -- ``ic``), output projection (iter 36 --
    ``oc``). Symmetric to the iter-18 / iter-19 input/output
    completion on the uniformity sub-axis, the iter-22 / iter-20
    input/output completion on the dimensional axis.

Relation to ``consistent_color_mapping`` (iter 8) -- INDEPENDENT in
both directions:

  * iter 8 fires alone: pair 0 maps {1 → 2}, pair 1 maps {3 → 4}. The
    unioned mapping {1 → 2, 3 → 4} is functional (iter 8 fires).
    Per-pair output sets {2} vs {4} differ (iter 36 rejects).
  * iter 36 fires alone: pair 0 maps {1 → 2}, pair 1 maps {3 → 2}.
    Per-pair output sets {2} vs {2} are identical (iter 36 fires).
    Unioned mapping is functional (both inputs map to 2) -- iter 8
    fires here. So this specific case is "both", not "iter 36 alone".
    A true iter-36-alone case: pair 0 maps {1 → 2}, pair 1 maps
    {1 → 3} -- per-pair output sets {2} vs {3} differ (iter 36
    rejects), unioned mapping {1 → {2, 3}} non-functional (iter 8
    rejects). Looking for iter-36-fires-alone -- pair 0 maps
    {1 → 2, 3 → 5}, pair 1 maps {4 → 5, 6 → 2}. Per-pair output sets
    {2, 5} bit-identical (iter 36 fires). Unioned mapping
    {1 → 2, 3 → 5, 4 → 5, 6 → 2} -- input 1 maps to 2, input 4 maps
    to 5, etc. Each input maps to one output, so unioned mapping IS
    functional (iter 8 fires). So this is "both" too. A clean
    iter-36-fires-alone needs the unioned mapping to be
    non-functional: pair 0 maps {1 → 2, 1 → 3} is impossible
    (single group has one ic and one oc). Try pair 0 maps
    {1 → 2, 3 → 5}, pair 1 maps {1 → 5, 3 → 2}. Per-pair output sets
    {2, 5} bit-identical (iter 36 fires). Unioned mapping
    {1 → {2, 5}, 3 → {5, 2}} -- both inputs map to multiple outputs,
    non-functional (iter 8 rejects). iter 36 fires alone.
  * Both fire: pair 0 maps {1 → 2}, pair 1 maps {3 → 2}. Per-pair
    output sets {2} bit-identical; unioned mapping {1 → 2, 3 → 2}
    functional.
  * Neither: pair 0 maps {1 → 2}, pair 1 maps {3 → 4, 5 → 6}.
    Per-pair output sets {2} vs {4, 6} differ (iter 36 rejects).
    Unioned mapping functional but pair-set-non-constant.

So iter 36 is NOT in a refinement relation with iter 8 either way --
they cover orthogonal sub-axes of the colour-content recognition
territory, the same way iter 35 is independent of iter 8 on the
input side.

Relation to ``change_input_colors_constant_across_pairs`` (iter 35) --
independent on the projection-axis:

  * iter 35 fires alone: pair 0 maps {1 → 2}, pair 1 maps {1 → 3}.
    Per-pair input set {1} bit-identical (iter 35 fires); per-pair
    output set {2} vs {3} differs (iter 36 rejects).
  * iter 36 fires alone: pair 0 maps {1 → 5}, pair 1 maps {2 → 5}.
    Per-pair output set {5} bit-identical (iter 36 fires); per-pair
    input set {1} vs {2} differs (iter 35 rejects).
  * Both: pair 0 maps {1 → 5}, pair 1 maps {1 → 5}. (Iter 34 also
    fires here.)

The cross-pair output-set constancy axis is orthogonal to:

  * The position-content axis
    (``change_positions_constant_across_pairs``, iter 30) -- positions
    vs output colours are independent content axes. CAN co-fire.
  * The cardinality axis
    (``change_count_constant_across_pairs``, iter 32) -- counts vs
    output colours are independent. CAN co-fire.
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
inspects the OUTPUT side's per-pair contiguous-range property (an
ordering shape on each pair's output sequence), this matcher inspects
the OUTPUT side's cross-pair set constancy (a SET equality across
pairs). CAN co-fire (a constant-output-set multi-group recolour where
each pair's outputs form the same contiguous range) or fire
independently (per-pair contiguous outputs that differ across pairs
fire iter 10 but not iter 36; bit-identical non-contiguous outputs
fire iter 36 but not iter 10).

Relation to ``input_color_uniform`` (iter 19) -- orthogonal: iter 19
inspects the INPUT side's cross-all-groups uniformity, this matcher
inspects the OUTPUT side's cross-pair set constancy. CAN co-fire (the
simplest "paint cells of input colour C with these output colours"
recognition stack) or fire independently.

Params:
  (none) -- the matcher inspects
  ``patterns["pair_analyses"][i]["groups"][j]["output_colors"]``, the
  per-group sorted list of unique output colour values emitted by
  ``_analyze_pair`` since iter 1. For each group, the matcher requires
  ``len(output_colors) == 1`` (the group's output colour is
  unambiguous); the per-group ``output_colors[0]`` is then collected
  into a frozenset over all groups in a pair, and the per-pair
  frozenset is compared cross-pair for equality.

Why per-group ``len(output_colors) == 1`` is required: when a single
connected blob spans multiple output colours (rare in ARC but
possible), the "output colour" of that group is ill-defined -- there
is no single ``oc`` to project onto. Falling back to including ALL
the group's output colours in the per-pair set would silently
over-count and risk false positives under cross-pair comparison. The
matcher fail-closes on multi-output-colour groups instead, mirroring
iter 18 / 19 / 34 / 35's strict per-group ``len == 1`` posture.

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
  - the per-pair frozenset of group-level ``output_colors[0]`` values
    is non-empty (the identity-territory rejection clause), AND
  - the per-pair frozenset is bit-identical across every pair.

Why fail-closed on empty per-pair sets: a patterns dict where every
pair has zero groups (the identity case) has empty per-pair sets that
are vacuously equal across pairs. Allowing that to fire here would
double-cover iter 13's ``identity_transformation`` territory under a
name that promises "the set of output colours involved is pinned" --
but there are no output colours to pin. The matcher names a
non-trivial precondition; the strict refusal mirrors iter 30's
empty-union rejection on the position axis, iter 32's
per-pair-total-zero rejection on the cardinality axis, iter 18 / 19's
strict refusal of zero-group pairs on the colour axis, iter 34's
per-pair empty-set rejection on the full colour-pair axis, and iter
35's per-pair empty-set rejection on the input-projection axis.

Why strict integer-in-range(10) on colours: ARC colours are integers
in 0..9 (the ``coloring`` primitive additionally accepts the ``13``
transparency sentinel, but ``_analyze_pair`` only emits colours
observed in the actual grids, which are 0..9). A missing or
out-of-range colour is upstream extractor breakage, not evidence the
precondition holds. Strict comparison forecloses bool-subclass false
positives (``True``/``False`` would otherwise compare equal to
``1``/``0``) and out-of-range integers, mirroring iter 18 / 19 / 34 /
35's strict colour-set posture.

Why a self-contained predicate rather than a composition of
``output_color_uniform`` + a cross-pair set check: matchers are
independent predicates in the registry (``docs/RULE_FORMAT.md``
section 4). Composing them at use-site (via ``recognized_conditions``
and a conjunction of names in a future composite-precondition step)
is the canonical pattern; inlining an iter-18 call here would couple
registry entries in a non-introspectable way. The matcher implements
its cross-pair set check explicitly so
``CONDITION_REGISTRY["change_output_colors_constant_across_pairs"]``
is a single self-contained predicate, the same shape as every other
matcher.

No ``_analyze_pair`` change this iter: the ``output_colors`` field
has been emitted per group since iter 1, so the matcher uses existing
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


@register("change_output_colors_constant_across_pairs")
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

        if not pair_output_colors:
            return False
        pair_set = frozenset(pair_output_colors)
        if canonical is None:
            canonical = pair_set
        elif canonical != pair_set:
            return False

    return canonical is not None
