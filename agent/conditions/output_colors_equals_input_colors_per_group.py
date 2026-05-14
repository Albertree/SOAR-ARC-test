"""
output_colors_equals_input_colors_per_group -- match tasks where
EVERY change group of EVERY example pair satisfies
``set(group["output_colors"]) == set(group["input_colors"])``: every
group's output side uses EXACTLY the same colour set as its own input
side -- no colour is added, no colour is removed at the per-group
scope.

Recognition vocabulary axis: per-group projection of iter 185
(``output_palette_equals_input``), which checks the WHOLE-GRID output
palette is set-equal to the WHOLE-GRID input palette per pair. Iter
185 collapses every pair's two grids into two palettes and demands
``set(output_palette) == set(input_palette)``; this matcher demands
the analogous strict-equality relation HOLDS PER BLOB. The two
projections decouple:

  * Iter 185 fires while this matcher rejects: pair 0 has two groups,
    group A with input_colors=[1] / output_colors=[2], group B with
    input_colors=[2] / output_colors=[1]. The whole-grid output
    palette is {1, 2} which equals the whole-grid input palette
    {1, 2}; iter 185 fires. But group A's output colour set {2} is
    NOT equal to group A's input colour set {1}; this matcher
    rejects. (Same per-blob-swap witness as iter 200's per-group-
    subset projection of iter 184.)
  * This matcher fires while iter 185 may fire: per-group equality
    universal-over-groups implies the per-pair UNION of group output
    palettes equals the per-pair UNION of group input palettes
    (set-equality is preserved under union). For grid_size_preserved
    tasks where every cell outside the change groups is unchanged
    (so contributes the same colour to whole-grid input and output),
    iter 185 follows by construction. The matcher itself does not
    enforce that structural relationship (it operates on dict input
    patterns), so the strict implication holds only on self-
    consistent patterns; the test suite pins the natural direction
    (per-group equality co-fires with iter 185 on self-consistent
    patterns) AND the decoupling witness (iter 185 fires alone on
    the per-blob swap).

Strict refinement of iter 200 (``output_colors_subset_of_input_
colors_per_group``): per-group equality is the strict refinement of
per-group subset. Strict implication: this matcher fires ⇒ iter 200
fires (set equality implies subset universally). The converse does
NOT hold: per-group input_colors=[1,2] / output_colors=[1] fires
iter 200 (proper subset) but rejects this matcher (output set strict
subset of input set).

Why a distinct matcher rather than parameterising iter 200 with a
``strict: True`` flag (mirroring the iter-185 / iter-184 separation
rationale): the matcher contract (docs/RULE_FORMAT.md §4) is name-
keyed recognition vocabulary; the rule's stored ``condition.type``
is the recognition handle's name, not a name+params tuple. The
strict-equality precondition gates different rule families than the
subset precondition (permutation rules vs erasure-tolerant rules);
keeping them in separate registry slots lets anti-unification attach
the right gate per rule family.

Strict refinement / orthogonality summary (universal-over-groups-and-
pairs semantics):

  * Iter 13 (``identity_transformation``) -- every pair has zero
    change groups. This matcher REJECTS the no-group case (fail-
    closed clause below) to keep its territory disjoint from iter 13
    by construction. Mirrors iter 32 / 35 / 37 / 39 / 193 / 195 /
    196 / 197 / 198 / 199 / 200 empty-group rejection.
  * Iter 14 (``input_color_uniform``) -- pins every group's
    ``input_colors`` to a single colour AND that colour identical
    across all groups in all pairs. With single-colour input groups,
    per-group equality reduces to ``output_colors == input_colors``
    being the same singleton, i.e. iter 14 + every group's output is
    that same single colour. CAN co-fire; the matchers are
    independent in general.
  * Iter 18 (``output_color_uniform``) -- symmetric to iter 14.
    Independent in general; CAN co-fire when every group's output
    single-colour equals every group's input single-colour and that
    colour is identical across all groups.
  * Iter 184 (``output_palette_subset_of_input``) -- whole-grid
    subset relation. INDEPENDENT in both directions: iter 184 fires
    on the per-blob swap (whole-grid output ⊆ input) but this matcher
    rejects (per-group output != per-group input); this matcher
    could fire on a pair where every group is palette-equal but the
    background contains a colour absent from the input grid (the
    matcher operates on input patterns and does not synthesise the
    whole-grid palette).
  * Iter 185 (``output_palette_equals_input``) -- whole-grid strict
    equality. INDEPENDENT in both directions (see paragraph above).
  * Iter 200 (``output_colors_subset_of_input_colors_per_group``) --
    per-group subset. THIS MATCHER STRICTLY IMPLIES ITER 200
    (set-equality is strict refinement of subset). The converse does
    NOT hold (proper-subset witness).
  * Iter 195 / 196 / 197 -- per-group cardinality matchers on
    input / output / product. NOT in a refinement relation in
    general; CAN co-fire on patterns where both pin. Iter 197's
    cardinality product ``|input_colors| * |output_colors|`` does
    NOT imply this matcher (cardinality-product constancy across
    pairs is compatible with arbitrary palette content); this matcher
    DOES imply iter 195 ∧ iter 196 ∧ iter 197 strictly on a single
    pair (set equality forces same cardinality), but the across-pair
    constancy claims in iter 195 / 196 / 197 are NOT implied by
    per-group equality (per-pair |input_colors| can differ across
    pairs while still being palette-equal per group within each
    pair); the matchers are therefore INDEPENDENT in the universal-
    over-pairs scope.
  * Iter 194 (whole-grid colour translation cross-pair) -- a
    translation by k != 0 has whole-grid output palette disjoint
    from input palette; THIS MATCHER REJECTS any k != 0 translation
    by construction. Co-fire only on the k == 0 (identity) cell.
  * Iter 198 / 199 (per-group colour translation within-pair /
    globally) -- with strict same-cardinality per-group sorted-shift
    and k != 0, the per-group output set is disjoint from the per-
    group input set; this matcher rejects k != 0 translations. Co-
    fire only on the global k == 0 cell, which is itself the per-
    group identity precondition (every group is an identity on its
    palette).
  * Iter 35 / 36 (``change_input_colors_constant_across_pairs`` /
    ``change_output_colors_constant_across_pairs``) -- per-pair
    input / output colour SET bit-identity across pairs. Independent.
  * Iter 8 (``consistent_color_mapping``) -- per-pair (C -> K) is a
    function on changed cells. A permutation on the active palette
    co-fires with this matcher; an erasure to a colour outside the
    palette does NOT co-fire (the erased target would violate per-
    group equality if it's outside the source palette). The two
    axes intersect on per-blob permutations.
  * Every cell- / position- / dimension-axis matcher (iters 1 / 17 /
    19 / 20 / 22 / 23 / 24 / 26 / 28 / 32 / 33 / 38 / 39 / 40 / 41 /
    42 / 182 / 183) -- orthogonal to per-group palette content.

Why this matters for ARBOR's intended ruleset:

  * "Per-blob permutation on the blob's own palette" rule family --
    rules whose action permutes cells within a change group using
    EXACTLY the colours that already appear in that group's input
    cells (a bijection on the blob's active palette). Iter 185's
    whole-grid version cannot distinguish "every blob is a
    permutation on its own palette" from "the whole-grid palette
    is preserved but some blob exchanges colours with another blob";
    this matcher names the strictly stronger per-blob version that
    is the precondition for per-blob permutation rules.
  * Strictly stronger than iter 200's per-group subset gate:
    iter 200 admits erasures (output strictly drops a colour); this
    matcher rejects erasures (output set strictly == input set).
    Anti-unification (CLAUDE.md section 8) would attach the per-blob
    permutation generalisation variable to this matcher's fired-gate
    rather than iter 200's, gating out erasure-shaped rule families.
  * Closes the iter-200-named next-gap first-listed candidate on the
    per-group palette-relation sub-axis. The pending sibling
    matchers on the same sub-axis (named by iter 200's next-gap) are
    ``input_colors_subset_of_output_colors_per_group`` (the iter-187
    per-group projection) and ``output_colors_disjoint_from_input_
    colors_per_group`` (the iter-186 per-group projection).

Params:
  (none) -- pure per-group set-equality check, universal over groups
  and pairs.

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
    ... / 198 / 199 / 200 strict-type posture), AND
  - for every group, ``set(output_colors) == set(input_colors)``.

Why fail-closed on empty / no-group / malformed (same posture as
iters 14 / 30 / 32 / 33 / 34 / 35 / 36 / 37 / 38 / 39 / 184-200): a
missing or zero-group pair is upstream extractor breakage or
identity-territory; an equality claim with zero observations would
double-cover iter 13.

Why ``input_colors`` and ``output_colors`` both required non-empty
lists per group (``len >= 1``): a connected change group has at
least one cell; each cell has both an input colour and an output
colour; the per-group ``input_colors`` / ``output_colors`` fields
are the sorted sets of those colours, which are non-empty for any
non-empty group. A zero-length colour list is an extractor contract
violation, not a valid empty-set equality case.

Why strict per-colour validation (bool rejected, range checked):
``input_colors`` / ``output_colors`` carry small ints in [0, 9]; the
matcher performs the same strict-type gating as iter 14 / 18 / 19 /
34 / 35 / 36 / 37 / 38 / 184-200 to keep contract violations from
silently passing.

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


@register("output_colors_equals_input_colors_per_group")
def match(patterns: dict, params: dict) -> bool:
    if not isinstance(patterns, dict):
        return False
    pair_analyses = patterns.get("pair_analyses")
    if not isinstance(pair_analyses, list) or not pair_analyses:
        return False

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
            if set(output_colors) != set(input_colors):
                return False
    return True
