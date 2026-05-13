"""
change_colors_constant_across_pairs -- match tasks where the set of
(input_color, output_color) group-level mappings is bit-identical across
every example pair.

Recognition vocabulary axis: ``colour-content / cross-pair set
constancy``. The iter-8 / 10 / 18 / 19 colour-content matchers each
inspect a *uniformity* property of colour fields (mapping-function on
the union of all groups for iter 8; contiguous output range for
iter 10; single output colour across all groups for iter 18; single
input colour across all groups for iter 19) but NONE of them names the
property "the SET of (input_colour, output_colour) mappings is the
same on every pair". That is the strict-stronger sibling of
``consistent_color_mapping`` on the cross-pair set-constancy
sub-axis -- exactly the colour-content analogue of iter 30
(``change_positions_constant_across_pairs``, cross-pair coord SET
constancy) and iter 32 (``change_count_constant_across_pairs``,
cross-pair total count constancy). This matcher is the simplest entry
on that strict-stronger colour-content sub-axis.

Relation to ``consistent_color_mapping`` (iter 8) -- the two matchers
form a refinement chain on the union-vs-per-pair-set sub-axes of the
colour-content axis:

    colors-constant ⟹ consistent_color_mapping     (same per-pair set
                                                     of (ic, oc) on
                                                     every pair ⟹ the
                                                     union is also
                                                     functional)

    consistent_color_mapping ⟹̸ colors-constant    (pair 0 has
                                                     {(1, 2)}, pair 1
                                                     has {(1, 2),
                                                     (3, 4)} -- both
                                                     pair-level sets
                                                     are functional
                                                     and their union
                                                     is still
                                                     functional, but
                                                     the per-pair sets
                                                     differ)

So this matcher strictly refines iter 8 on the cross-pair set-constancy
sub-axis. The two are NOT redundant: a task with consistent-but-varying
per-pair mapping subsets (e.g. pair 0 maps {1->2}, pair 1 maps
{1->2, 3->4}) fires iter 8 but NOT this matcher. That is the territory
this matcher names exclusively -- the recognition precondition for a
future rule whose action stores the EXACT training-pinned set of
(input_colour, output_colour) recolour pairs.

Why this matters for the schema:

  * Iter 8's matcher only requires the union of all observed (ic, oc)
    pairs to be a function. The natural strict refinement -- "every
    pair contains the same set of recolour mappings" -- is the
    precondition for a recolour rule whose action stores a literal
    colour-pair list and applies it to every pair. Without this
    matcher, the recolour-rule shape iter 31 / 25 / 27 / 29 alluded to
    on the colour axis has no named cross-pair set-constancy
    precondition; this matcher names it.
  * Iter 30 names the cross-pair coord-set constancy on the
    position-content axis; iter 32 names the cross-pair count
    constancy on the cardinality axis. This matcher names the same
    cross-pair set-constancy shape on the colour-content axis,
    completing the three-axis set of "the X is bit-identical across
    every pair" matchers that recognition vocabulary now has on each
    of position / cardinality / colour. The cross-axis symmetry
    matches the iter-18 / 19 input-output symmetric completion on the
    uniformity sub-axis -- recognition vocabulary grows in symmetric
    pairs whenever the underlying data supports it.
  * Per-attempt ``fired_conditions`` (written to
    ``episodic_memory/<task>/attempt_NNN/metadata.json`` since iter
    12) gains a directly inspectable signal for "this task's set of
    colour-recolour pairs is pinned across pairs" -- one more named
    axis the instrumentation surfaces without needing a
    translate_to_schema branch to consume it. Recognition vocabulary
    ahead of emission, the same posture iters 17 / 18 / 19 / 20 / 22
    / 23 / 24 / 26 / 28 / 30 / 32 / 33 all carry.

The cross-pair colour-set constancy axis is orthogonal to:

  * The position-content axis
    (``change_positions_constant_across_pairs``) -- iter 30 inspects
    coord SET equality, this matcher inspects colour-pair SET
    equality. Orthogonal: a task can fire one, both, or neither.
    CAN co-fire (the simplest "paint THESE cells with THIS recolour
    map" recognition stack pinned on both content axes).
  * The cardinality axis
    (``change_count_constant_across_pairs``) -- iter 32 inspects
    coord COUNT equality, not colour content. Orthogonal: a task
    with constant colour-pair sets but varying coord counts fires
    this matcher and not iter 32 (e.g. pair 0 has one 1-cell blob
    of colour 1->2, pair 1 has one 2-cell blob of colour 1->2; both
    pairs share the SAME colour-pair set {(1, 2)} but have
    different cell counts). CAN co-fire.
  * The dimensional axes (``grid_size_preserved`` /
    ``grid_size_changed`` / ``output_dimensions_constant`` /
    ``input_dimensions_constant`` /
    ``output_dimensions_multiple_of_input``) -- those inspect grid
    shape, not colour content. Orthogonal.
  * The group-count axis (``identity_transformation`` /
    ``single_change_group_per_pair`` / ``multi_group_per_pair``) --
    those inspect ``num_groups``, not colour content. Orthogonal.
  * The cell-count sub-axis (``single_cell_change_per_pair`` /
    ``multi_cell_change_group_per_pair``) -- those inspect
    per-group ``cell_count`` under ``num_groups == 1``, not colour
    content. Orthogonal.

Relation to existing colour-content matchers (mutual-exclusion /
refinement table):

  * ``consistent_color_mapping`` (iter 8) -- this matcher strictly
    refines iter 8 on the cross-pair set-constancy axis (proved
    above): every patterns dict that fires this matcher also fires
    iter 8 (same per-pair set ⟹ functional union), but the
    converse does not hold. CAN co-fire by construction.
  * ``output_color_uniform`` (iter 18) -- requires the OUTPUT side
    to collapse to one constant across all groups in all pairs.
    Orthogonal to the cross-pair set constancy: iter 18 fires AND
    this matcher fires when the OUTPUT side is constant K AND every
    pair's set of input colours mapping to K is identical. They CAN
    co-fire (the simplest constant-output recolour) or fire
    independently.
  * ``input_color_uniform`` (iter 19) -- requires the INPUT side to
    collapse to one constant across all groups in all pairs.
    Orthogonal as above: they CAN co-fire (constant-input
    recolour with the same input colour C on every pair and the
    same output colour on every pair) or fire independently.
  * ``sequential_recoloring`` (iter 10) -- requires per-pair output
    colours to form a contiguous integer range. Orthogonal to
    cross-pair set constancy: a task with N groups per pair forming
    a contiguous output range CAN fire iter 10 AND this matcher (the
    same N-group recolour set appearing on every pair), OR fire iter
    10 alone (per-pair contiguous ranges differing across pairs --
    e.g. pair 0 has outputs {1, 2, 3}, pair 1 has outputs
    {4, 5, 6}; iter 10 fires on each pair individually, but the
    per-pair sets differ so this matcher rejects), OR fire this
    matcher alone (constant set but no contiguous-range property).
  * ``identity_transformation`` (iter 13) -- requires every pair's
    ``num_groups == 0``; the per-pair colour-pair set is empty.
    This matcher REJECTS the empty-set case (see fail-closed clause
    below) to keep the territory disjoint from iter 13 by
    construction; iter 13 names the identity territory and is the
    canonical recognition handle there. STRICTLY mutually
    exclusive in practice.

Params:
  (none) -- the matcher inspects
  ``patterns["pair_analyses"][i]["groups"][j]["input_colors"]`` and
  ``["output_colors"]``, the per-group sorted lists of unique colour
  values emitted by ``_analyze_pair`` since iter 1. For each group,
  the matcher requires ``len(input_colors) == 1`` AND
  ``len(output_colors) == 1`` (the group's colour pair is
  unambiguous); the per-group ``(input_colors[0], output_colors[0])``
  is then collected into a frozenset over all groups in a pair, and
  the per-pair frozenset is compared cross-pair for equality.

Why per-group ``len == 1`` is required: when a single connected blob
spans multiple input or output colours (rare in ARC but possible),
the "colour pair" of that group is ill-defined -- there is no single
(ic, oc) pair to collect. Falling back to the Cartesian product
``input_colors × output_colors`` would silently over-count the
group's colour content and risk false positives. The matcher
fail-closes on multi-colour groups instead, mirroring iter 18 / 19's
strict per-group ``len == 1`` posture. Multi-colour groups are
recognition territory for a different matcher (deferred -- iter 8's
``consistent_color_mapping`` already handles the multi-colour case
on the unioned mapping function, which is the natural recognition
home for that territory).

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
  - the per-pair frozenset of group-level ``(ic, oc)`` pairs is
    non-empty (the identity-territory rejection clause), AND
  - the per-pair frozenset is bit-identical across every pair.

Why fail-closed on empty per-pair sets: a patterns dict where every
pair has zero groups (the identity case) has empty per-pair sets that
are vacuously equal across pairs. Allowing that to fire here would
double-cover iter 13's ``identity_transformation`` territory under a
name that promises "the set of colour recolours is pinned" -- but
there is no recolour to pin. The matcher names a non-trivial
precondition; the strict refusal mirrors iter 30's empty-union
rejection on the position axis, iter 32's per-pair-total-zero
rejection on the cardinality axis, and iter 18 / 19's strict refusal
of zero-group pairs on the colour axis.

Why strict integer-in-range(10) on colours: ARC colours are integers
in 0..9 (the ``coloring`` primitive additionally accepts the
``13`` transparency sentinel, but ``_analyze_pair`` only emits
colours observed in the actual grids, which are 0..9). A missing or
out-of-range colour is upstream extractor breakage, not evidence the
precondition holds. Strict comparison forecloses bool-subclass
false positives (``True``/``False`` would otherwise compare equal to
``1``/``0``) and out-of-range integers, mirroring iter 18 / 19's
strict colour-set posture.

Why a self-contained predicate rather than a composition of
``consistent_color_mapping`` + a cross-pair set check: matchers are
independent predicates in the registry (``docs/RULE_FORMAT.md``
section 4). Composing them at use-site (via ``recognized_conditions``
and a conjunction of names in a future composite-precondition step)
is the canonical pattern; inlining an iter-8 call here would couple
registry entries in a non-introspectable way. The matcher implements
its cross-pair set check explicitly so
``CONDITION_REGISTRY["change_colors_constant_across_pairs"]`` is a
single self-contained predicate, the same shape as every other
matcher.

No ``_analyze_pair`` change this iter: the ``input_colors`` and
``output_colors`` fields have been emitted per group since iter 1, so
the matcher uses existing data on a new axis. The companion-touch
question under F8 is therefore inert -- this iter has no
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


@register("change_colors_constant_across_pairs")
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

        if not pair_pairs:
            return False
        pair_set = frozenset(pair_pairs)
        if canonical is None:
            canonical = pair_set
        elif canonical != pair_set:
            return False

    return canonical is not None
