"""
output_palette_partial_overlap_with_input_palette -- match tasks where
EVERY example pair satisfies, on the whole-grid palettes,
``set(input_palette) & set(output_palette) != empty`` AND
``NOT (set(input_palette) <= set(output_palette))`` AND
``NOT (set(output_palette) <= set(input_palette))``. The whole-grid
input palette and the whole-grid output palette share at least one
colour (non-empty intersection), yet neither contains the other: each
side carries at least one colour absent from the other.

Recognition vocabulary axis: whole-grid "partial-overlap residual"
cell of the whole-grid palette-relation sub-axis. The four existing
whole-grid palette-relation cells are:

  * Iter 184 (``output_palette_subset_of_input``) -- B ⊆ A per pair
    (non-strict; equality admitted).
  * Iter 185 (``output_palette_equals_input``) -- A == B per pair.
  * Iter 186 (``output_palette_disjoint_from_input``) -- A ∩ B == ∅
    per pair.
  * Iter 187 (``input_palette_subset_of_output``) -- A ⊆ B per pair
    (non-strict; equality admitted).
  * THIS MATCHER -- per-pair PARTIAL OVERLAP residual: intersection
    is non-empty AND neither side contains the other (each side has
    at least one colour absent from the other).

Closure of the whole-grid palette-relation sub-axis under the
non-empty-palette domain. Let A = set(input_palette), B =
set(output_palette), both non-empty. Exactly ONE of the following
holds:

  (i)   A == B                                            → iter 185
  (ii)  B ⊊ A          (i.e. B ⊆ A and B != A)            → iter 184 ∧ ¬iter 185
  (iii) A ⊊ B          (i.e. A ⊆ B and A != B)            → iter 187 ∧ ¬iter 185
  (iv)  A ∩ B == ∅                                        → iter 186
  (v)   A ∩ B != ∅ and NOT (A ⊆ B) and NOT (B ⊆ A)        → THIS MATCHER

Proof: cases (i)-(iii) are exactly the subset/equality partition of
the case "one side is a subset of the other"; cases (iv)-(v)
partition the case "neither side is a subset of the other" by the
empty-intersection / non-empty-intersection cut. The five cases
cover the universe and are pairwise disjoint.

This matcher is the whole-grid projection of iter 206
(``output_colors_partial_overlap_with_input_colors_per_group``), in
the same way that iter 184 is the whole-grid projection of iter 200,
iter 185 is the whole-grid projection of iter 201, iter 186 is the
whole-grid projection of iter 203, and iter 187 is the whole-grid
projection of iter 202. The two scopes (whole-grid and per-group)
are NOT in a refinement relation in general: a task can satisfy the
whole-grid partial-overlap precondition while having per-group
relations of every shape (some groups equal, some disjoint, etc.),
and a task can satisfy the per-group partial-overlap precondition
while the whole-grid palettes are equal (when per-group residuals
cancel across groups).

Why a distinct matcher rather than parameterising iters 184 / 185 /
186 / 187 with a ``partial_overlap: True`` flag (mirroring the iter
185 / iter 184 separation rationale and iter 200 / 201 / 202 / 203 /
204 / 205 / 206 separation rationale): the matcher contract
(docs/RULE_FORMAT.md §4) is name-keyed recognition vocabulary; the
rule's stored ``condition.type`` is the recognition handle's name,
not a name+params tuple. The partial-overlap precondition gates a
DIFFERENT rule family than any of the subset / equality / disjoint
preconditions (whole-grid anchor-preserving rewrite rules, distinct
from whole-grid permutation / erasure / expansion / canvas-rewrite
rules); keeping the partial-overlap cell in a separate registry slot
lets anti-unification attach the right gate per rule family.

Strict mutual exclusion with every other whole-grid palette-relation
cell (universal over the non-empty-palette domain):

  * Iter 184 (``output_palette_subset_of_input``, non-strict): if
    iter 184 fires, then per-pair output ⊆ input. THIS MATCHER
    requires NOT (output ⊆ input) per pair. STRICTLY MUTUALLY
    EXCLUSIVE.
  * Iter 185 (``output_palette_equals_input``): if iter 185 fires,
    then per-pair output == input, which implies both containments.
    THIS MATCHER requires BOTH containments to fail. STRICTLY
    MUTUALLY EXCLUSIVE.
  * Iter 186 (``output_palette_disjoint_from_input``): iter 186
    requires per-pair input ∩ output == ∅. THIS MATCHER requires
    per-pair input ∩ output != ∅. STRICTLY MUTUALLY EXCLUSIVE.
  * Iter 187 (``input_palette_subset_of_output``, non-strict):
    symmetric to iter 184. STRICTLY MUTUALLY EXCLUSIVE.

Decoupling from neighbouring matchers:

  * Iter 13 (``identity_transformation``) -- on identity tasks the
    whole-grid palettes are equal, which is iter 185's territory.
    STRICTLY MUTUALLY EXCLUSIVE with this matcher via iter 185.
    The whole-grid scope therefore does not need the per-group
    empty-group rejection clause that iters 200-206 carry; an
    identity task naturally falls into iter 185 territory and is
    rejected by the partial-overlap clauses below.
  * Iter 14 (``input_color_uniform``) -- pins changed cells'
    ``input_colors`` to a single colour; whole-grid palette
    membership is orthogonal in general. INDEPENDENT.
  * Iter 18 (``output_color_uniform``) -- symmetric. INDEPENDENT.
  * Iter 188 (``output_palette_count_exceeds_input_palette_count``)
    -- strict |B| > |A|. CAN co-fire (partial overlap with |B| >
    |A|, e.g. A = {0, 1}, B = {1, 2, 3}: |∩| = 1, neither side
    contained, |B| > |A|). CAN each fire alone.
  * Iter 189 (``input_palette_count_exceeds_output_palette_count``)
    -- strict |A| > |B|. CAN co-fire (partial overlap with |A| >
    |B|). CAN each fire alone.
  * Iter 190 (``palette_symmetric_difference_constant_across_pairs``)
    -- cross-pair |A △ B| constancy. CAN co-fire (every pair has the
    same |A △ B| AND every pair is in partial-overlap territory).
    CAN each fire alone.
  * Iter 191 (``palette_intersection_count_constant_across_pairs``)
    -- cross-pair |A ∩ B| constancy. CAN co-fire. CAN each fire
    alone.
  * Iter 45 (``palette_union_count_constant_across_pairs``) --
    cross-pair |A ∪ B| constancy. CAN co-fire. CAN each fire alone.
  * Iter 206 (``output_colors_partial_overlap_with_input_colors_per_group``)
    -- per-group projection of the same residual cell. INDEPENDENT
    in general: the whole-grid and per-group palette relations are
    not in a refinement relation either way. CAN co-fire on tasks
    where both scopes carry the same partial-overlap shape.
  * Iter 8 (``consistent_color_mapping``) -- per-pair (C -> K) is a
    function on changed cells. INDEPENDENT in general.
  * Iters 30 / 33 / 34 / 35 / 36 / 37 / 38 / 39 / 40 / 42 -- cross-
    pair constancy matchers on the change-cell axes. INDEPENDENT of
    the whole-grid palette-relation cell.
  * Every cell- / position- / dimension-axis matcher (iters 1 / 17 /
    19 / 20 / 22 / 23 / 24 / 26 / 28 / 32 / 33 / 38 / 39 / 40 / 41 /
    42 / 182 / 183) -- orthogonal to whole-grid palette content.

Why this matters for ARBOR's intended ruleset:

  * "Whole-grid anchor-preserving rewrite" rule family -- rules
    whose action preserves at least one colour across the whole
    grid (the colour in the intersection) while replacing some
    input colours and introducing some fresh output colours.
    Iter 184 / 187's territories cannot express this cell: iter 184
    forbids fresh output colours, iter 187 forbids dropped input
    colours, iter 186 forbids any shared colour at all, iter 185
    forbids any palette change at all. This matcher names the
    strictly stronger partial-overlap residual cell that is the
    precondition for whole-grid anchor-preserving rewrite rule
    families.
  * Iter 185 names the whole-grid PERMUTATION rule family
    precondition (equality territory); iter 184 ∧ ¬iter 185 names
    the whole-grid ERASURE rule family precondition; iter 187 ∧
    ¬iter 185 names the whole-grid EXPANSION rule family
    precondition; iter 186 names the whole-grid CANVAS-REWRITE rule
    family precondition (disjoint territory); this matcher names
    the whole-grid ANCHOR-PRESERVING-REWRITE rule family
    precondition. The five matchers together cover the entire
    universe of whole-grid palette-relation patterns under the
    non-empty-palette domain, each naming a distinct rule family
    the gate can attach to.
  * Cross-pair / per-pair constancy on the whole-grid partial-
    overlap relation is the precondition for anti-unification
    (CLAUDE.md §8) to lift a whole-grid anchor-preserving rewrite
    into a generalisation variable at the whole-grid scope. Iter
    206 names the per-group variant of the same handle; without
    this whole-grid projection, anti-unification cannot pin the
    whole-grid anchor-preserving precondition without conflating
    with the per-group precondition.
  * Closes the whole-grid palette-relation sub-axis. With iters
    184 / 185 / 186 / 187 / this iter all landed, every cell of
    the whole-grid palette-relation sub-axis under the non-empty-
    palette domain is named, and the partition is complete (dual
    to the per-group partition closed by iter 206).

Params:
  (none) -- pure per-pair partial-overlap check, universal over
  pairs on the whole-grid palettes.

Returns True iff:
  - ``patterns`` is a dict, AND
  - ``patterns["pair_analyses"]`` is a non-empty list, AND
  - every analysis is a dict, AND
  - every analysis has an ``input_palette`` value that is a list of
    non-bool ints (mirroring iter 184 / 185 / 186 / 187 / 190 / 191
    whole-grid posture; empty admissible at the type level, the
    semantic gate below rejects empty palettes via the non-empty-
    intersection clause), AND
  - every analysis has an ``output_palette`` value with the same
    contract, AND
  - for every analysis,
    ``set(input_palette) & set(output_palette) != ∅``
    AND ``NOT (set(input_palette) <= set(output_palette))``
    AND ``NOT (set(output_palette) <= set(input_palette))``.

Why fail-closed on empty / missing / malformed (same posture as
iters 184 / 185 / 186 / 187 / 190 / 191): a missing or non-list
palette is upstream extractor breakage, not evidence the
precondition holds. Universal-over-pairs semantics with a vacuously-
true empty case would let an empty patterns dict fire the gate,
which is the wrong default -- a partial-overlap claim with zero
observations is meaningless.

Why strict-list-of-non-bool-ints (not range-checked): mirrors the
iter 184 / 185 / 186 / 187 / 190 / 191 whole-grid posture --
``_analyze_pair`` emission is unfiltered, so we tolerate any int
value (including the iter-180 erase sentinel ``13``) and let the
upstream extractor handle range validation. The per-group iter 206
applies a stricter [0, 9] gate because the per-group fields are
extracted from the change-cell positions, not the raw grids; the
whole-grid fields here are the raw grid palettes.

Why no empty-pair-analyses-list rejection at the inner level: the
per-pair semantic gate (non-empty intersection AND both non-
containment clauses) naturally rejects degenerate palettes; an
empty whole-grid input or output palette has empty intersection,
which fails the first clause. The whole-grid scope therefore does
not need the per-group empty-list rejection clause that iter 206
carries.

No companion-touch required: ``input_palette`` and ``output_palette``
have been emitted per pair_analysis since iter 184; this iter is a
pure matcher addition with no ``agent/active_operators.py`` diff.
F8 inert.
"""

from __future__ import annotations

from agent.conditions import register


def _is_palette_list(x) -> bool:
    """A palette field must be a list of non-bool ints. Empty is
    admissible at the type level (the semantic gate's non-empty-
    intersection clause rejects empty palettes)."""
    if not isinstance(x, list):
        return False
    for v in x:
        if not isinstance(v, int) or isinstance(v, bool):
            return False
    return True


@register("output_palette_partial_overlap_with_input_palette")
def match(patterns: dict, params: dict) -> bool:
    if not isinstance(patterns, dict):
        return False
    pair_analyses = patterns.get("pair_analyses")
    if not isinstance(pair_analyses, list) or not pair_analyses:
        return False

    for analysis in pair_analyses:
        if not isinstance(analysis, dict):
            return False
        ip = analysis.get("input_palette")
        op = analysis.get("output_palette")
        if not _is_palette_list(ip):
            return False
        if not _is_palette_list(op):
            return False
        in_set = set(ip)
        out_set = set(op)
        if not (in_set & out_set):
            return False
        if in_set <= out_set:
            return False
        if out_set <= in_set:
            return False
    return True
