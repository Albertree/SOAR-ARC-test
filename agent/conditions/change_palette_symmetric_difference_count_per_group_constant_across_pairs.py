"""
change_palette_symmetric_difference_count_per_group_constant_across_pairs
-- match tasks where EVERY change group in EVERY example pair has the
same derived integer ``len(set(group["input_colors"]) ^
set(group["output_colors"]))``, with that single integer K determined
by the first observed group. The matcher pins constancy of the
per-group "magnitude of palette change" -- the number of distinct
colours that change membership between a group's input palette and
its output palette -- across every group across every pair.

Recognition vocabulary axis: per-group "magnitude of palette change"
constancy. This is the per-group projection of iter 190
(``palette_symmetric_difference_constant_across_pairs``, which
inspects the cardinality of the whole-grid input/output palette
symmetric difference per pair and demands constancy across pairs)
and the per-group symmetric-difference-cardinality dual of iter 207
(``change_palette_intersection_count_per_group_constant_across_pairs``,
which inspects the per-group ``|ic ∩ oc|`` cardinality).

Where iter 190 collapses each pair's whole-grid input / output
palettes into a per-pair |A △ B| integer and compares cross-pair,
this matcher inspects every change group's own |ic △ oc| and
demands constancy across every group across every pair. The two
projections are not in a refinement relation: a task where every
group has |ic △ oc| = 2 but per-pair whole-grid |A △ B| varies
(because pair 0's groups share colours with each other while pair
1's groups have disjoint colour sets) fires this matcher and rejects
iter 190; conversely a task where every pair's whole-grid |A △ B|
is the same N but groups have varying per-group |ic △ oc| fires
iter 190 and rejects this matcher.

Refinement / orthogonality summary (universal-over-pairs / -groups
semantics):

  * Iter 13 (``identity_transformation``) -- every pair has zero
    groups. This matcher REJECTS the no-group case (fail-closed
    clause below) to keep its territory disjoint from iter 13 by
    construction. Mirrors iter 32 / 35 / 37 / 39 / 193 / 195 / 196 /
    197 / 198 / 199 / 200 / 201 / 202 / 203 / 204 / 205 / 206 / 207
    empty-group rejection.
  * Iter 201 (``output_colors_equals_input_colors_per_group``) --
    per-group ic == oc, |ic △ oc| == 0 on every group of every
    pair, which is constant. STRICT IMPLICATION: iter 201 ⇒ this
    matcher (canonical value K==0). Reverse does not hold: a task
    with constant per-group |ic △ oc| == 2 fires this matcher but
    rejects iter 201.
  * Iter 203 (``output_colors_disjoint_from_input_colors_per_group``)
    -- per-group ic ∩ oc == ∅, |ic △ oc| == |ic| + |oc| per group.
    Constant iff |ic| + |oc| is constant across every group across
    every pair. INDEPENDENT in general: iter 203 with varying per-
    group |ic| + |oc| (e.g. pair 0 group: |ic|=1+|oc|=1=2; pair 1
    group: |ic|=2+|oc|=2=4) fires iter 203 but rejects this matcher.
    Conversely this matcher with K == 1 partial-overlap groups fires
    alone.
  * Iter 200 (``output_colors_subset_of_input_colors_per_group``) --
    per-group oc ⊆ ic, |ic △ oc| == |ic| - |oc|. Constant iff
    |ic| - |oc| is constant across every group across every pair.
    INDEPENDENT: iter 200 with varying per-group |ic| - |oc| fires
    iter 200 but rejects this matcher.
  * Iter 202 (``input_colors_subset_of_output_colors_per_group``) --
    symmetric to iter 200: |ic △ oc| == |oc| - |ic|. INDEPENDENT.
  * Iter 204 (``output_colors_proper_subset_of_input_colors_per_group``)
    -- strict-erasure refinement of iter 200: |ic △ oc| == |ic| -
    |oc| AND |oc| < |ic|. INDEPENDENT for the same reason as iter
    200.
  * Iter 205 (``input_colors_proper_subset_of_output_colors_per_group``)
    -- strict-expansion refinement of iter 202: |ic △ oc| == |oc| -
    |ic| AND |ic| < |oc|. INDEPENDENT for the same reason as iter
    202.
  * Iter 206 (``output_colors_partial_overlap_with_input_colors_per_group``)
    -- per-group partial-overlap residual cell of the per-group
    palette-relation sub-axis. |ic ∩ oc| >= 1 on every group, with
    NOT (ic ⊆ oc) and NOT (oc ⊆ ic). |ic △ oc| varies in general
    across partial-overlap groups. INDEPENDENT: a task with partial-
    overlap groups of varying |ic △ oc| fires iter 206 but rejects
    this matcher. The natural co-fire territory is the "constant Δ
    partial-overlap" cell -- where both iter 206 fires AND |ic △
    oc| is the same K >= 2 across every group.
  * Iter 207 (``change_palette_intersection_count_per_group_constant_across_pairs``)
    -- per-group |ic ∩ oc| constancy. Sibling on the per-group
    cardinality sub-axis, distinct derived integer
    (|ic ∩ oc| vs |ic △ oc|). NOT in a refinement relation either
    way: a task where every group has |ic ∩ oc| == 1 but |ic △ oc|
    varies (e.g. group 0: ic={1,2}, oc={2,3}, |∩|=1, |△|=2; group
    1: ic={1,2,3}, oc={3,4,5}, |∩|=1, |△|=4) fires iter 207 but
    rejects this matcher. Conversely a task with constant |ic △
    oc| == 2 but varying |ic ∩ oc| (e.g. group 0: ic={1,2},
    oc={2,3}, |∩|=1, |△|=2; group 1: ic={1,2}, oc={3,4}, |∩|=0,
    |△|=2 -- both Δ=2) fires this matcher but rejects iter 207.
    CAN co-fire when both axes constant.
  * Iter 190 (``palette_symmetric_difference_constant_across_pairs``)
    -- whole-grid projection. NOT in a refinement relation either
    way: see analysis above.
  * Iter 195 (``change_input_color_count_per_group_constant_across_pairs``)
    -- per-group |ic| constancy. Sibling on the per-group constancy
    sub-axis, distinct derived integer. CAN co-fire (constant |ic|
    AND constant |ic △ oc|), CAN each fire alone.
  * Iter 196 (``change_output_color_count_per_group_constant_across_pairs``)
    -- per-group |oc| constancy. Sibling on the per-group constancy
    sub-axis, distinct derived integer. CAN co-fire, CAN each fire
    alone.
  * Iter 197 (``change_color_mapping_count_per_group_constant_across_pairs``)
    -- per-group |ic| * |oc| constancy. Sibling on the per-group
    constancy sub-axis, distinct derived integer. CAN co-fire, CAN
    each fire alone.
  * Iter 193 (``change_count_per_group_constant_across_pairs``) --
    per-group cell_count constancy. Sibling on the per-group
    constancy sub-axis, distinct field (cell_count vs the
    symmetric-difference cardinality). NOT in a refinement
    relation. CAN co-fire.
  * Iter 14 (``input_color_uniform``) -- pins per-group |ic| == 1
    AND single colour identical across groups. With |ic| == 1, the
    per-group |ic △ oc| = |ic\\oc| + |oc\\ic| depends on whether
    ic[0] ∈ oc and on |oc|. INDEPENDENT: iter 14 + every group
    having (ic[0] not in oc AND |oc| == 1) co-fires this matcher
    (K == 2 constant); iter 14 + mixed |oc| rejects this matcher.
  * Iter 18 (``output_color_uniform``) -- output-side dual of iter
    14. INDEPENDENT in the same way.
  * Iter 35 (``change_input_colors_constant_across_pairs``) /
    iter 36 (``change_output_colors_constant_across_pairs``) --
    per-pair input / output colour SET bit-identity. NOT in a
    refinement relation; CAN co-fire.
  * Iter 8 (``consistent_color_mapping``) -- per-pair (C -> K) is a
    function on changed cells. INDEPENDENT.
  * Iters 30 / 33 / 34 / 35 / 36 / 37 / 38 / 39 / 40 / 42 -- cross-
    pair constancy matchers on the change-cell axes. Same cross-
    pair-constancy sub-axis, distinct derived integers; INDEPENDENT.
  * Every cell- / position- / dimension-axis matcher (iters 1 / 17 /
    19 / 20 / 22 / 23 / 24 / 26 / 28 / 32 / 33 / 38 / 39 / 40 / 41 /
    42 / 182 / 183) -- orthogonal to per-group palette content.

Why this matters for ARBOR's intended ruleset:

  * "Per-blob Δ-cardinality-constant" rule family: rules whose
    per-blob action changes exactly K distinct colours per blob
    (regardless of which specific colours change). Examples:
      - "swap one anchor colour per blob" tasks (K == 2 constant:
        one colour dropped, one added per blob).
      - "extend each blob with one fresh colour" tasks (K == 1
        constant; co-fires with iter 205 with |oc| - |ic| == 1).
      - "erase one anchor colour per blob" tasks (K == 1 constant;
        co-fires with iter 204 with |ic| - |oc| == 1).
      - "fully replace every blob colour with a fresh one" tasks
        (K == 2 constant; co-fires with iter 203 with |ic| + |oc|
        == 2).
    The conjunction of this matcher with iter 206 names a sharper
    recogniser: e.g. (iter 206 AND this matcher with K == 2) names
    "every blob has exactly one drop and exactly one addition."
  * Cross-pair / cross-group constancy on the per-group symmetric-
    difference cardinality is the precondition for anti-unification
    (CLAUDE.md §8) to lift a per-blob Δ-cardinality into a constant
    generalisation variable at the per-group scope. Iter 190 names
    the whole-grid variant of the same handle; without this per-
    group projection, anti-unification cannot pin the per-blob
    palette-change magnitude without conflating with whole-grid
    palette change.
  * Completes the per-group cardinality sub-axis on the symmetric-
    difference direction, dual of iter 207's intersection direction.
    Iter 207 closed the per-group |ic ∩ oc| handle; this iter opens
    the per-group |ic △ oc| handle, sibling of iters 195 / 196 /
    197 / 207 on the per-group cardinality sub-axis.

Params:
  (none) -- pure cross-pair / cross-group constancy check on the
  derived integer ``len(set(input_colors) ^ set(output_colors))``
  for every group in every pair.

Returns True iff:
  - ``patterns`` is a dict, AND
  - ``patterns["pair_analyses"]`` is a non-empty list, AND
  - every analysis is a dict, AND
  - every analysis has a non-empty ``groups`` list (identity-
    territory rejection), AND
  - every group is a dict with list-typed ``input_colors`` and
    ``output_colors`` fields of length >= 1, AND
  - every entry of ``input_colors`` and ``output_colors`` is a
    strict int in ``range(10)`` (bool rejected per iter-13 / 14 /
    ... / 206 / 207 strict-type posture), AND
  - the integer ``len(set(input_colors) ^ set(output_colors))`` is
    bit-identical for every group of every analysis.

Why fail-closed on empty / no-group / malformed (same posture as
iters 14 / 30 / 32 / 33 / 34 / 35 / 36 / 37 / 38 / 39 / 184-207): a
missing or zero-group pair is upstream extractor breakage or
identity-territory; a constancy claim with zero observations is
meaningless and would double-cover iter 13.

Why ``input_colors`` and ``output_colors`` both required non-empty
lists per group (``len >= 1``): a connected change group has at
least one cell; each cell has both an input colour and an output
colour; the per-group ``input_colors`` / ``output_colors`` fields
are the sorted sets of those colours, which are non-empty for any
non-empty group. A zero-length colour list is an extractor contract
violation, not a valid empty-set case.

Why strict per-colour validation (bool rejected, range checked):
``input_colors`` / ``output_colors`` carry small ints in [0, 9]; the
matcher performs the same strict-type gating as iter 14 / 18 / 19 /
34 / 35 / 36 / 37 / 38 / 184-207 to keep contract violations from
silently passing. The actual constancy check is on
``len(set(ic) ^ set(oc))``, not on the colours themselves, so cross-
group colour identity is NOT required.

No companion-touch required: ``input_colors`` and ``output_colors``
have been emitted per group since iter 1 (``_analyze_pair`` in
``agent/active_operators.py``); this iter is a pure matcher addition
with no ``agent/active_operators.py`` diff. F8 inert.
"""

from __future__ import annotations

from agent.conditions import register


def _is_strict_color(x) -> bool:
    return (
        isinstance(x, int)
        and not isinstance(x, bool)
        and 0 <= x <= 9
    )


def _is_color_list(x) -> bool:
    if not isinstance(x, list) or len(x) < 1:
        return False
    for v in x:
        if not _is_strict_color(v):
            return False
    return True


@register("change_palette_symmetric_difference_count_per_group_constant_across_pairs")
def match(patterns: dict, params: dict) -> bool:
    if not isinstance(patterns, dict):
        return False
    pair_analyses = patterns.get("pair_analyses")
    if not isinstance(pair_analyses, list) or not pair_analyses:
        return False

    canonical_delta: int | None = None

    for analysis in pair_analyses:
        if not isinstance(analysis, dict):
            return False
        groups = analysis.get("groups")
        if not isinstance(groups, list) or not groups:
            return False
        for group in groups:
            if not isinstance(group, dict):
                return False
            input_colors = group.get("input_colors")
            output_colors = group.get("output_colors")
            if not _is_color_list(input_colors):
                return False
            if not _is_color_list(output_colors):
                return False
            delta_size = len(set(input_colors) ^ set(output_colors))
            if canonical_delta is None:
                canonical_delta = delta_size
            elif canonical_delta != delta_size:
                return False

    return canonical_delta is not None
