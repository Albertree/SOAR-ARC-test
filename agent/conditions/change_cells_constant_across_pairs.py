"""
change_cells_constant_across_pairs -- match tasks where the unioned set of
per-cell ``(row, col, input_colour, output_colour)`` tuples is bit-identical
across every example pair.

Recognition vocabulary axis: ``cell-tuple content`` (cross-pair constancy of
the per-cell transformation, fusing the position-content axis and the
colour-content axis into a single strictest predicate). The iter-30 /
iter-34 set-axis matchers each pin one projection of the change-cells of a
pair (iter 30 = the position SET; iter 34 = the per-group (ic, oc) SET);
their CONJUNCTION does NOT imply per-cell tuple constancy because the
(r, c) -> (ic, oc) ASSIGNMENT can permute across pairs while the marginals
match.

Worked counter-example (position SET and (ic, oc) SET both constant, this
matcher rejects):

    Pair 0:                  Pair 1:
      (0, 0): 1 -> 2           (0, 0): 3 -> 4
      (1, 1): 3 -> 4           (1, 1): 1 -> 2

Position set on both pairs: ``{(0, 0), (1, 1)}`` -- iter 30 fires.
(ic, oc) set on both pairs: ``{(1, 2), (3, 4)}`` -- iter 34 fires.
Per-cell tuple set on pair 0: ``{(0, 0, 1, 2), (1, 1, 3, 4)}``.
Per-cell tuple set on pair 1: ``{(0, 0, 3, 4), (1, 1, 1, 2)}``.
These per-cell sets DIFFER -- this matcher rejects.

Why this matters for the schema:

  * The iter-25 (``paint_single_cell``) / iter-27 (``paint_blob``) /
    iter-29 (``paint_blobs``) emission branches all gate on
    ``change_positions_constant_across_pairs`` (iter 30) AND
    ``output_color_uniform`` (iter 18). Together those name the position
    set and the constant K. They do NOT name the input-side per-cell
    invariant. For the canonical paint-uniform-K case, that gap is
    fine -- the action ignores IC. But for a future colour-dependent
    paint rule whose action would be "paint (r, c) with the same output
    colour the training pair uses at (r, c)", the precondition for that
    rule to be unambiguously determinable from the training data is
    per-cell tuple constancy: every pair agrees not just on which cells
    change, not just on what (ic, oc) mappings occur, but on which
    SPECIFIC mapping happens at each SPECIFIC cell. This matcher names
    that precondition.
  * Recognition vocabulary ahead of emission, the iter
    1 / 8 / 10 / 13 / 17 / 18 / 19 / 20 / 22 / 23 / 24 / 26 / 28 / 30 /
    32 / 33 / 34 / 35 / 36 / 37 / 38 / 39 / 40 pattern. Naming the
    strictest cell-content precondition surfaces a directly-inspectable
    signal in the per-attempt ``fired_conditions`` list (written by
    ``_record_attempt`` to every ``episodic_memory/<task>/attempt_NNN
    /metadata.json`` since iter 12) for "this task's training data
    fully determines a per-cell paint rule" -- one more named axis the
    instrumentation surfaces without needing a translate_to_schema
    branch to consume it.
  * A future translate_to_schema emission branch for the
    colour-dependent-paint rule shape (action paints each cell with an
    output colour drawn from a training-derived (r, c) -> oc lookup
    table) has no named recognition handle for the cross-pair per-cell
    invariant the action's apply-time lookup must reproduce until this
    matcher lands. The two existing position-axis matchers (set, count)
    and the two existing colour-axis matchers (set, count, plus the
    (ic, oc) cardinality and the input/output projections) jointly
    cover the marginals but leave the JOINT distribution unnamed.

The cell-tuple-content axis is a strict refinement of:

  * ``change_positions_constant_across_pairs`` (iter 30) -- this matcher
    fires ==> iter 30 fires (projecting the (r, c, ic, oc) tuple set to
    its first two coordinates is set-monotone: ``{(r, c) : (r, c, ic, oc)
    in T}`` is determined by T, and equal T's project to equal position
    sets). The converse does NOT hold (see worked counter-example
    above). STRICT REFINEMENT.
  * ``change_colors_constant_across_pairs`` (iter 34) -- per-cell tuple
    constancy implies per-cell (ic, oc) constancy, which implies per-pair
    (ic, oc) SET constancy (the iter-34 axis): when the per-cell map
    is identical, the unioned set of (ic, oc) tuples across all groups in
    a pair is also identical across pairs (every (r, c, ic, oc) entry
    projects to one (ic, oc) entry; equal per-cell sets project to equal
    (ic, oc) sets). STRICT REFINEMENT -- the converse does NOT hold.
  * ``change_count_constant_across_pairs`` (iter 32) -- equal per-cell
    sets have equal cardinalities, so this matcher implies iter 32.
    STRICT REFINEMENT.
  * ``change_color_mapping_count_constant_across_pairs`` (iter 40) --
    equal (ic, oc) sets have equal cardinalities, so this matcher
    implies iter 40 (via the iter-34 implication chain). STRICT
    REFINEMENT.
  * ``change_input_colors_constant_across_pairs`` (iter 35) --
    equal per-cell sets project to equal per-pair input-colour sets.
    STRICT REFINEMENT.
  * ``change_output_colors_constant_across_pairs`` (iter 36) -- ditto
    on the output projection. STRICT REFINEMENT.
  * ``change_input_color_count_constant_across_pairs`` (iter 37) and
    ``change_output_color_count_constant_across_pairs`` (iter 38) -- via
    the iter-35 / iter-36 chains.
  * ``change_group_count_constant_across_pairs`` (iter 39) -- NOT in a
    refinement relation. The per-cell tuple set is a flat union over
    groups -- different group partitions can produce the same flat
    tuple set. So this matcher does NOT imply iter 39, and iter 39 does
    NOT imply this matcher. ORTHOGONAL on the group-count axis.

Relation to ``identity_transformation`` (iter 13) -- STRICTLY mutually
exclusive: identity requires every pair's ``num_groups == 0``, so the
unioned cell-tuple set is empty, which this matcher rejects via the
non-empty-union clause to keep its territory disjoint from iter 13 by
construction. Mirrors iters 30 / 32 / 37 / 38 / 39 / 40's
identity-territory rejection on their respective axes.

The cell-tuple-content axis is orthogonal to:

  * The dimensional axes (``grid_size_preserved`` / ``grid_size_changed``
    / ``output_dimensions_constant`` / ``input_dimensions_constant`` /
    ``output_dimensions_multiple_of_input``) -- those inspect grid shape,
    not cell content. CAN co-fire.
  * The group-count axis (``identity_transformation`` /
    ``single_change_group_per_pair`` / ``multi_group_per_pair`` /
    ``change_group_count_constant_across_pairs``) -- those inspect
    ``num_groups``, not cell content. CAN co-fire (different group
    partitions can yield the same cell-tuple set; constant per-pair
    group counts are neither necessary nor sufficient for per-cell
    constancy).
  * The cell-count sub-axis (``single_cell_change_per_pair`` /
    ``multi_cell_change_group_per_pair``) -- those inspect per-group
    ``cell_count`` under ``num_groups == 1``, not cell content. CAN
    co-fire.
  * The colour-uniformity axes (``output_color_uniform`` /
    ``input_color_uniform``) -- those inspect per-cell colour
    cardinality, not the per-cell mapping. CAN co-fire.
  * ``consistent_color_mapping`` (iter 8) and ``sequential_recoloring``
    (iter 10) -- those inspect colour content per pair / per output
    side; this matcher inspects the per-pair JOINT (r, c, ic, oc) set
    across pairs. CAN co-fire.

Params:
  (none) -- the matcher inspects
  ``patterns["pair_analyses"][i]["groups"][j]["positions"]``,
  ``["input_colors"]``, and ``["output_colors"]``. Positions field has
  been emitted per group since iter 27 (``_analyze_pair`` extension);
  input_colors / output_colors have been emitted per group since iter
  1. The matcher requires ``len(input_colors) == 1`` AND
  ``len(output_colors) == 1`` per group (else the group's (ic, oc) pair
  is ill-defined -- mirrors iter 18 / 19 / 34 / 40's strict per-group
  ``len == 1`` posture); under that constraint every cell in the group
  has its (ic, oc) determined by the group's two scalars. The matcher
  then builds the per-pair set
  ``{(r, c, input_colors[0], output_colors[0]) : for each group, for each
  (r, c) in positions}`` and compares the canonical sorted tuple of that
  set across pairs for bit-identity.

Why per-group ``len == 1`` is required: when a single connected blob
spans multiple input or output colours (rare in ARC but possible), the
"colour pair" of that group is ill-defined and the per-cell (ic, oc)
cannot be extracted from the group's two-list summary alone (the
per-cell record needed for that would be a per-cell ``(input_color,
output_color)`` list, which ``_analyze_pair`` does NOT emit at the
group level). The matcher fail-closes on multi-colour groups, mirroring
iter 18 / 19 / 34 / 40's strict per-group ``len == 1`` posture. A
future ``_analyze_pair`` extension that emits per-cell colour records
would let this matcher relax that restriction -- deferred.

Why per-position cell_count consistency check: ``_analyze_pair`` emits
``cell_count = len(group_cells)`` and ``positions = sorted(positions)``
in lockstep (iter 27). A mismatch is upstream extractor breakage, not
evidence the precondition holds. The fail-closed posture preserves
the matcher's contract that a missing or malformed dependency is
NOT silent True. Mirrors iter 30's same posture.

Why duplicate-coord rejection inside a pair's union: per-cell tuple
constancy assumes a well-formed mapping (each cell appears at most
once in a pair). Iters 26 / 28 emission helpers strictly reject
``len(set(canon_tuple)) != len(canon_tuple)`` because that would
indicate two blobs share a cell -- the connectivity computation is
internally corrupt. This matcher upholds the same rejection.

Returns True iff:
  - ``patterns`` is a dict, AND
  - ``patterns["pair_analyses"]`` is a non-empty list, AND
  - every analysis is a dict, AND
  - every analysis carries a list-typed ``groups`` field, AND
  - every group is a dict with list-typed ``positions``, ``input_colors``,
    ``output_colors`` fields, AND
  - every group's ``input_colors`` has length exactly 1, AND
  - every group's ``output_colors`` has length exactly 1, AND
  - every colour value is a strict integer in ``range(10)`` (bool
    rejected per ``validate_rule`` V1 posture), AND
  - every group's ``cell_count`` is a strict positive int (bool
    rejected, ``>= 1``), AND
  - every group's ``positions`` list has length exactly ``cell_count``,
    AND
  - every position is a 2-element list/tuple of strict non-negative
    ints (bool rejected), AND
  - the per-pair flat union of all ``(r, c, ic, oc)`` tuples (over all
    groups in that pair) is non-empty, AND
  - the per-pair flat union has no duplicate (r, c) coords (no two
    blobs share a cell), AND
  - the canonical sorted tuple of the per-pair union is bit-identical
    across every pair.

Why fail-closed on empty per-pair union: a patterns dict where every
pair has zero changed cells (the identity case) has empty unions that
are vacuously equal across pairs. Allowing that to fire here would
double-cover iter 13's ``identity_transformation`` territory under
a name that promises "the per-cell transformation is pinned" -- but
there is no per-cell transformation to pin. The matcher names a
non-trivial precondition; the strict refusal mirrors iter 30's
empty-union rejection on the position axis, iter 32 / 37 / 38 / 39 /
40's per-pair-zero-cardinality rejection on the cardinality axes,
and iter 18 / 19 / 34 / 35 / 36's empty-set rejection.

Why strict bool-subclass rejection on integer fields: every integer
field in the patterns dict (``cell_count``, coord components, colour
values) is semantically an integer count / coordinate / colour, not
a Boolean. Strict-type matchers across the registry (iters 13 / 17 /
18 / 19 / 20 / 22 / 23 / 24 / 26 / 28 / 30 / 32 / 33 / 34 / 35 / 36 /
37 / 38 / 39 / 40 and ``validate_rule`` V1) reject ``True`` /
``False`` on integer fields. The matcher upholds the same posture
to keep the recognition vocabulary's type-strictness consistent
across the registry.

Why a self-contained predicate rather than a refinement-by-call of
iter 30 + iter 34: matchers are independent predicates in the
registry (``docs/RULE_FORMAT.md`` section 4). Composing them at
use-site (via ``recognized_conditions`` and a conjunction of names
in a future composite-precondition step) is the canonical pattern;
inlining iter-30 + iter-34 calls here would couple registry entries
in a non-introspectable way -- worse, it would be INSUFFICIENT, since
this matcher is a STRICT refinement of their conjunction (see the
worked counter-example above where both iter 30 and iter 34 fire
but the per-cell sets differ). The matcher implements its per-cell
union-and-equality check explicitly so ``CONDITION_REGISTRY[
"change_cells_constant_across_pairs"]`` is a single self-contained
predicate, the same shape as every other matcher.

No ``_analyze_pair`` change this iter: the ``positions`` /
``input_colors`` / ``output_colors`` / ``cell_count`` fields have all
been emitted per group since iter 27 (positions) or iter 1 (the
others), so the matcher uses existing data on a new axis (the JOINT
position-and-colour cell-tuple axis). F8 inert -- this iter has no
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


def _is_strict_non_negative_int(x) -> bool:
    return (
        isinstance(x, int)
        and not isinstance(x, bool)
        and x >= 0
    )


def _is_strict_positive_int(x) -> bool:
    return (
        isinstance(x, int)
        and not isinstance(x, bool)
        and x >= 1
    )


@register("change_cells_constant_across_pairs")
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

        per_pair_tuples: list = []
        per_pair_coords: set = set()
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
            cell_count = group.get("cell_count")
            if not _is_strict_positive_int(cell_count):
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
                if not _is_strict_non_negative_int(r):
                    return False
                if not _is_strict_non_negative_int(c):
                    return False
                if (r, c) in per_pair_coords:
                    # two blobs share a cell -- corrupt connectivity
                    return False
                per_pair_coords.add((r, c))
                per_pair_tuples.append((r, c, ic, oc))

        if not per_pair_tuples:
            # identity-territory rejection
            return False

        canon_tuple = tuple(sorted(per_pair_tuples))
        if canonical is None:
            canonical = canon_tuple
        elif canonical != canon_tuple:
            return False

    return canonical is not None
