"""
output_colors_disjoint_from_input_colors_per_group -- match tasks where
EVERY change group of EVERY example pair satisfies
``set(group["input_colors"]) & set(group["output_colors"]) == empty
set``: no group's output side reuses ANY colour from its own input
side. Every per-group recolour introduces only colours fresh to that
blob; nothing of the blob's input palette survives onto its own output
side.

Recognition vocabulary axis: per-group projection of iter 186
(``output_palette_disjoint_from_input``), which checks the WHOLE-GRID
output palette is disjoint from the WHOLE-GRID input palette per pair.
Iter 186 collapses every pair's two grids into two palettes and
demands ``set(output_palette) & set(input_palette) == empty set``;
this matcher demands the analogous disjointness relation HOLDS PER
BLOB. The two projections decouple:

  * Iter 186 fires while this matcher fires by construction (per-group
    disjointness universal-over-groups implies per-pair UNION of group
    output palettes is disjoint from per-pair UNION of group input
    palettes; with whole-grid palettes being supersets of those unions
    the implication does NOT hold in general -- a pair where every
    changed-group output is disjoint from its own input but the
    whole-grid output palette happens to share a colour with the
    whole-grid input palette via unchanged background pixels could
    fire this matcher and reject iter 186; conversely a per-blob colour
    swap would fire whole-grid disjointness's NEGATION -- both palettes
    contain {1, 2} -- yet rejects iter 186 anyway). The two projections
    are INDEPENDENT in both directions.
  * Iter 186 fires while this matcher rejects: pair 0 has two groups,
    group A with input_colors=[1] / output_colors=[3], group B with
    input_colors=[3] / output_colors=[1]. The whole-grid input palette
    is {1, 3} and the whole-grid output palette is {1, 3}; iter 186
    REJECTS (intersection is {1, 3}). Wait -- this isn't a witness for
    iter 186 firing while this matcher rejects. The actual witness:
    pair 0 has one group with input_colors=[1] / output_colors=[2] AND
    a whole-grid background colour 1 unchanged outside the group. The
    per-group output={2} is disjoint from per-group input={1} (this
    matcher fires); but whole-grid input_palette={1, BG} and whole-grid
    output_palette={2, BG} may still intersect on BG (iter 186 rejects).
    Iter 186 inspects the whole grid; this matcher inspects only the
    change groups.

Closes the per-group palette-relation sub-axis -- the four-cell
partition output-subset-of-input (iter 200) / output-equals-input
(iter 201) / input-subset-of-output (iter 202) / output-disjoint-from-
input (this matcher). With this matcher landing, every cell of the
2x2 cross-product of {output ⊆ input, output ⊇ input} is named at the
per-group scope:

  * (output ⊆ input) ∧ (output ⊇ input)  =  per-group equality (iter 201)
  * (output ⊆ input) ∧ NOT (output ⊇ input)  =  per-group strict erasure
    (iter 200 fires; iter 202 rejects)
  * NOT (output ⊆ input) ∧ (output ⊇ input)  =  per-group strict
    expansion (iter 202 fires; iter 200 rejects)
  * NOT (output ⊆ input) ∧ NOT (output ⊇ input)  =  partial overlap
    OR fully disjoint -- THIS MATCHER's territory is the strictly
    stronger fully-disjoint cell of that residual quadrant.

The four cells together name the entire per-group palette-relation
sub-axis.

Strict refinement / orthogonality summary (universal-over-groups-and-
pairs semantics):

  * Iter 13 (``identity_transformation``) -- every pair has zero
    change groups. This matcher REJECTS the no-group case (fail-
    closed clause below) to keep its territory disjoint from iter 13
    by construction. Mirrors iter 32 / 35 / 37 / 39 / 193 / 195 /
    196 / 197 / 198 / 199 / 200 / 201 / 202 empty-group rejection.
  * Iter 14 (``input_color_uniform``) -- pins every group's
    ``input_colors`` to a single colour AND that colour identical
    across all groups in all pairs. Independent of disjointness in
    general: with single-colour input groups, the disjointness claim
    reduces to "every group's output_colors does NOT contain that
    single input colour". CAN co-fire when every group's output is
    fresh (does not contain the uniform input colour).
  * Iter 18 (``output_color_uniform``) -- pins every group's
    ``output_colors`` to a single colour AND that colour identical
    across all groups in all pairs. Independent in general; CAN co-
    fire when every group's input does NOT contain that single output
    colour.
  * Iter 184 (``output_palette_subset_of_input``) -- whole-grid
    output palette subset of whole-grid input palette per pair. THIS
    MATCHER CAN STILL FIRE alongside iter 184 only on the empty-output
    palette degenerate case; on any non-empty per-group output, per-
    group disjointness implies the union of per-group outputs is
    disjoint from the union of per-group inputs, so the whole-grid
    output (a superset of the union of per-group outputs) intersected
    with the whole-grid input (a superset of the union of per-group
    inputs) is at most the unchanged-background intersection; iter
    184's whole-grid SUBSET requires the whole-grid output to be
    contained in the whole-grid input, which is NOT in general
    satisfied when per-group outputs are fresh. The two are
    INDEPENDENT in general; co-fire only on the empty-output-per-
    group corner (which this matcher rejects via the cell-count
    requirement).
  * Iter 185 (``output_palette_equals_input``) -- whole-grid strict
    equality. Independent of per-group disjointness; co-fire only on
    the per-blob-swap-with-aligned-whole-grid-palettes corner (where
    this matcher REJECTS -- per-group sets are NOT disjoint on a swap;
    they are equal each other). Strictly: equality is a refinement of
    subset (iter 184), and per-group disjointness with non-empty
    per-group outputs makes whole-grid output intersect whole-grid
    input only via unchanged background, which is not in general
    sufficient for whole-grid equality. Independent in general.
  * Iter 186 (``output_palette_disjoint_from_input``) -- whole-grid
    version of THIS matcher. INDEPENDENT in both directions (see
    paragraph above).
  * Iter 187 (``input_palette_subset_of_output``) -- whole-grid
    input palette subset of whole-grid output palette per pair. THIS
    MATCHER CAN STILL FIRE alongside iter 187 only on the empty-input-
    palette degenerate case (rejected via cell-count). Generally
    independent.
  * Iter 195 / 196 / 197 -- per-group cardinality matchers on
    input / output / product. NOT in a refinement relation; CAN co-
    fire on patterns where both pin (e.g. K_in == K_out == 1 with
    fresh output colour per group fires both this matcher AND iter
    195 ∧ iter 196 ∧ iter 197).
  * Iter 194 / 198 / 199 -- colour-translation sub-axis. A
    translation by k != 0 has output disjoint from input per group;
    THIS MATCHER FIRES on every iter-199-fires cell EXCEPT k == 0.
    Co-fire is the entire iter-199 territory minus the k == 0 cell.
  * Iter 200 (``output_colors_subset_of_input_colors_per_group``) --
    per-group output ⊆ per-group input. MUTUALLY EXCLUSIVE on non-
    empty per-group outputs (a non-empty output cannot be both
    subset of AND disjoint from a non-empty input). The cell-count
    requirement makes per-group outputs non-empty by construction;
    therefore mutual exclusion holds universally over this matcher's
    domain.
  * Iter 201 (``output_colors_equals_input_colors_per_group``) --
    per-group equality. STRICTLY MUTUALLY EXCLUSIVE on non-empty
    per-group palettes (equality forbids disjointness when both
    sides are non-empty).
  * Iter 202 (``input_colors_subset_of_output_colors_per_group``) --
    per-group input ⊆ per-group output. MUTUALLY EXCLUSIVE on non-
    empty per-group inputs (a non-empty input cannot be both subset
    of AND disjoint from a non-empty output). The cell-count
    requirement makes per-group inputs non-empty by construction;
    therefore mutual exclusion holds universally over this matcher's
    domain.
  * Iter 35 / 36 (``change_input_colors_constant_across_pairs`` /
    ``change_output_colors_constant_across_pairs``) -- per-pair
    input / output colour SET bit-identity. Independent.
  * Iter 8 (``consistent_color_mapping``) -- per-pair (C -> K) is a
    function on changed cells. INDEPENDENT in general; this matcher
    constrains where K lives (in the complement of the group's input
    set), iter 8 constrains how C maps. CAN co-fire when every (C, K)
    the function maps satisfies K not in input set per group (e.g.
    every per-blob recolour goes to a fresh colour).
  * Every cell- / position- / dimension-axis matcher (iters 1 / 17 /
    19 / 20 / 22 / 23 / 24 / 26 / 28 / 32 / 33 / 38 / 39 / 40 / 41 /
    42 / 182 / 183) -- orthogonal to per-group palette content.

Why this matters for ARBOR's intended ruleset:

  * "Per-blob canvas-rewrite / fresh-recolour" rule family -- rules
    whose action recolours every cell of a change group to a colour
    NOT present in that group's input cells (a per-blob foreground-
    erase + relabel layer). Iter 186's whole-grid version cannot
    distinguish "every blob's output is fresh" from "the whole-grid
    output palette happens to be disjoint from the whole-grid input
    palette via background bleed-through"; this matcher names the
    strictly stronger per-blob version that is the precondition for
    per-blob canvas-rewrite rules. Anti-unification (CLAUDE.md
    section 8) would attach a per-group canvas-rewrite generalisation
    variable to this matcher's fired-gate.
  * Closes the iter-202-named next-gap last-listed candidate on the
    per-group palette-relation sub-axis. With iter 200 (subset) /
    iter 201 (equality) / iter 202 (dual subset) / this iter
    (disjoint), the four cells of the per-group palette-relation
    sub-axis are now all named.

Params:
  (none) -- pure per-group disjointness check, universal over groups
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
    ... / 200 / 201 / 202 strict-type posture), AND
  - for every group, ``set(input_colors) & set(output_colors) ==
    empty set``.

Why fail-closed on empty / no-group / malformed (same posture as
iters 14 / 30 / 32 / 33 / 34 / 35 / 36 / 37 / 38 / 39 / 184-202): a
missing or zero-group pair is upstream extractor breakage or
identity-territory; a disjointness claim with zero observations would
double-cover iter 13.

Why ``input_colors`` and ``output_colors`` both required non-empty
lists per group (``len >= 1``): a connected change group has at
least one cell; each cell has both an input colour and an output
colour; the per-group ``input_colors`` / ``output_colors`` fields
are the sorted sets of those colours, which are non-empty for any
non-empty group. A zero-length colour list is an extractor contract
violation, not a valid empty-set disjoint case.

Why strict per-colour validation (bool rejected, range checked):
``input_colors`` / ``output_colors`` carry small ints in [0, 9]; the
matcher performs the same strict-type gating as iter 14 / 18 / 19 /
34 / 35 / 36 / 37 / 38 / 184-202 to keep contract violations from
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


@register("output_colors_disjoint_from_input_colors_per_group")
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
            if set(input_colors) & set(output_colors):
                return False
    return True
