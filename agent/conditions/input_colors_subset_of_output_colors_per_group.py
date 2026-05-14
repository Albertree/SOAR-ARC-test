"""
input_colors_subset_of_output_colors_per_group -- match tasks where
EVERY change group of EVERY example pair satisfies
``set(group["input_colors"]) <= set(group["output_colors"])``: every
colour appearing on a group's input side also appears somewhere on
that same group's output side -- no group erases a colour from its
own active palette. The transformation may *add* fresh colours per
group but never *drops* one from the group's input palette.

Recognition vocabulary axis: per-group projection of iter 187
(``input_palette_subset_of_output``), which checks the WHOLE-GRID
input palette is a subset of the WHOLE-GRID output palette per pair.
Iter 187 collapses every pair's two grids into two palettes and
demands ``set(input_palette) <= set(output_palette)``; this matcher
demands the analogous subset relation HOLDS PER BLOB. The two
projections decouple:

  * Iter 187 fires while this matcher rejects: pair 0 has two groups,
    group A with input_colors=[1] / output_colors=[2], group B with
    input_colors=[2] / output_colors=[1]. The whole-grid input
    palette is {1, 2} which is a subset of the whole-grid output
    palette {1, 2}; iter 187 fires. But group A's input colour 1 is
    NOT in group A's output colour set {2}; this matcher rejects.
    (Same per-blob-swap witness as iter 200's per-group projection
    of iter 184 -- the swap decouples whole-grid containment from
    per-group containment in BOTH directions.)
  * This matcher fires while iter 187 may also fire: per-group subset
    universal-over-groups implies the per-pair UNION of group input
    palettes is a subset of the per-pair UNION of group output
    palettes (subset is preserved under union); the per-pair UNION
    of group output palettes is itself a subset of the whole-grid
    output palette. With ``input_palette`` defined as the set of
    colours present in the input grid -- a superset of the union of
    group input palettes (input may also contain unchanged pixels) --
    the implication does NOT hold in general: a pair where every
    changed-group input is a subset of its own output but the input
    grid happens to contain a colour absent from the output grid
    (an unchanged background colour erased nowhere) would fire this
    matcher and reject iter 187. Iter 187 inspects the whole grid;
    this matcher inspects only the change groups. The two projections
    are INDEPENDENT in both directions.

Symmetric dual of iter 200 (``output_colors_subset_of_input_colors_
per_group``): iter 200 names "every group's output palette is
contained in its input palette" (the precondition for per-blob
erasure / permutation rule families); this matcher names "every
group's input palette is contained in its output palette" (the
precondition for per-blob palette-expansion / overlay rule families).
The two are independent in general -- both fire on per-group
equality (the iter 201 cell, which is their intersection on a single
pair); only this matcher fires on per-group palette-expansion
(output strictly grows over input); only iter 200 fires on per-group
erasure (output strictly drops a colour); neither fires on the per-
blob swap or partial-overlap cases. The intersection of this matcher
AND iter 200 is iter 201 (per-group equality); the union of this
matcher AND iter 200 admits proper-superset, proper-subset, and
equality.

Strict refinement / orthogonality summary (universal-over-groups-and-
pairs semantics):

  * Iter 13 (``identity_transformation``) -- every pair has zero
    change groups. This matcher REJECTS the no-group case (fail-
    closed clause below) to keep its territory disjoint from iter 13
    by construction. Mirrors iter 32 / 35 / 37 / 39 / 193 / 195 /
    196 / 197 / 198 / 199 / 200 / 201 empty-group rejection.
  * Iter 14 (``input_color_uniform``) -- pins every group's
    ``input_colors`` to a single colour AND that colour identical
    across all groups in all pairs. Independent of subset relation:
    with single-colour input groups, the subset claim reduces to
    "every group's output_colors contains that single input colour".
    CAN co-fire when every group's output contains the uniform input
    colour.
  * Iter 18 (``output_color_uniform``) -- pins every group's
    ``output_colors`` to a single colour AND that colour identical
    across all groups in all pairs. Independent in general; CAN co-
    fire when every group's input is contained in that single output
    colour, i.e. every group's input is the same single colour as
    the uniform output (the iter 14 ∧ iter 18 cell at the per-group
    scope).
  * Iter 184 (``output_palette_subset_of_input``) -- whole-grid
    output palette subset of whole-grid input palette per pair. The
    DUAL DIRECTION at the whole-grid scope. INDEPENDENT of this
    matcher in general; co-fires only at the equality cell (per-
    group palette equality + whole-grid palette equality, which is
    the iter 185 cell at the corresponding scope).
  * Iter 185 (``output_palette_equals_input``) -- whole-grid strict
    equality. Independent of per-group subset relation; CAN co-fire
    on patterns where both pin.
  * Iter 186 (``output_palette_disjoint_from_input``) -- whole-grid
    output disjoint from input. THIS MATCHER REJECTS iter 186's
    territory by construction: a per-group output disjoint from
    per-group input contradicts ``input ⊆ output`` (the per-group
    intersection would be empty, but ``input ⊆ output`` requires it
    to be ``input`` itself, which is non-empty per the cell-count
    requirement).
  * Iter 187 (``input_palette_subset_of_output``) -- whole-grid
    version of THIS matcher. INDEPENDENT in both directions (see
    paragraph above).
  * Iter 195 / 196 / 197 -- per-group cardinality matchers on
    input / output / product. NOT in a refinement relation; CAN co-
    fire on patterns where both pin. ``|input| <= |output|`` is
    implied by ``input ⊆ output`` on a single group, but the
    across-pair constancy claim in iters 195 / 196 / 197 is NOT
    implied by per-group subset.
  * Iter 194 / 198 / 199 -- colour-translation sub-axis. A
    translation by k != 0 has output disjoint from input per group;
    this matcher rejects k != 0 translations (per-group input is
    NOT contained in a disjoint per-group output). Co-fire only on
    the k == 0 cell (the iter 201 equality cell at the corresponding
    scope).
  * Iter 200 (``output_colors_subset_of_input_colors_per_group``) --
    SYMMETRIC DUAL. INDEPENDENT in general; co-fire iff both hold,
    i.e. per-group equality, which is iter 201
    (``output_colors_equals_input_colors_per_group``). On any per-
    group palette where the two sides differ, exactly one of {iter
    200, this matcher} fires (or neither -- partial overlap / per-
    blob swap / fully disjoint).
  * Iter 201 (``output_colors_equals_input_colors_per_group``) --
    per-group equality. STRICT REFINEMENT in BOTH directions: iter
    201 strictly implies this matcher AND strictly implies iter 200
    (equality ⇒ subset in either direction). The converse does NOT
    hold (per-group palette-expansion witness: input=[1] /
    output=[1, 2] fires this matcher and rejects iter 201).
  * Iter 35 / 36 (``change_input_colors_constant_across_pairs`` /
    ``change_output_colors_constant_across_pairs``) -- per-pair
    input / output colour SET bit-identity. Independent.
  * Iter 8 (``consistent_color_mapping``) -- per-pair (C -> K) is a
    function on changed cells. INDEPENDENT in general; this matcher
    constrains where the per-group input C lives (it must be in the
    group's output set), iter 8 constrains how C maps. CAN co-fire
    when every per-group input colour is also a per-group output
    colour (e.g. an identity / palette-expansion on each blob).
  * Every cell- / position- / dimension-axis matcher (iters 1 / 17 /
    19 / 20 / 22 / 23 / 24 / 26 / 28 / 32 / 33 / 38 / 39 / 40 / 41 /
    42 / 182 / 183) -- orthogonal to per-group palette content.

Why this matters for ARBOR's intended ruleset:

  * "Per-blob palette-expansion / overlay" rule family -- rules
    whose action keeps every per-blob input colour in the per-blob
    output AND adds fresh colours per blob (annotation / labelling /
    border / overlay layers painted in fresh colours per blob).
    Iter 187's whole-grid version cannot distinguish "every blob's
    palette is preserved" from "some blob preserves its palette
    while another blob erases a colour that happens to still exist
    somewhere else in the output grid"; this matcher names the
    strictly stronger per-blob version that is the precondition for
    per-blob palette-expansion rules. Anti-unification
    (CLAUDE.md section 8) would attach a per-group palette-expansion
    generalisation variable to this matcher's fired-gate.
  * Closes the iter-201-named next-gap first-listed candidate on the
    per-group palette-relation sub-axis (named also by iter 200's
    next-gap as the second-listed candidate / symmetric dual of iter
    200 on the same sub-axis). The pending sibling matcher on the
    same sub-axis (named by iter 200 / 201's next-gap) is
    ``output_colors_disjoint_from_input_colors_per_group`` (the
    iter-186 per-group projection -- the off-diagonal cell that
    closes the four-cell partition of the sub-axis).

Params:
  (none) -- pure per-group subset check, universal over groups and
  pairs.

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
    ... / 199 / 200 / 201 strict-type posture), AND
  - for every group, ``set(input_colors) <= set(output_colors)``.

Why fail-closed on empty / no-group / malformed (same posture as
iters 14 / 30 / 32 / 33 / 34 / 35 / 36 / 37 / 38 / 39 / 184-201): a
missing or zero-group pair is upstream extractor breakage or
identity-territory; a subset claim with zero observations would
double-cover iter 13.

Why ``input_colors`` and ``output_colors`` both required non-empty
lists per group (``len >= 1``): a connected change group has at
least one cell; each cell has both an input colour and an output
colour; the per-group ``input_colors`` / ``output_colors`` fields
are the sorted sets of those colours, which are non-empty for any
non-empty group. A zero-length colour list is an extractor contract
violation, not a valid empty-set subset case.

Why strict per-colour validation (bool rejected, range checked):
``input_colors`` / ``output_colors`` carry small ints in [0, 9]; the
matcher performs the same strict-type gating as iter 14 / 18 / 19 /
34 / 35 / 36 / 37 / 38 / 184-201 to keep contract violations from
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


@register("input_colors_subset_of_output_colors_per_group")
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
            if not set(input_colors).issubset(set(output_colors)):
                return False
    return True
