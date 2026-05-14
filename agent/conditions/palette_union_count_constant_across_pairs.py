"""
palette_union_count_constant_across_pairs -- match tasks where the size
of the union of the input palette and the output palette is the same
integer on every example pair:
``len(set(input_palette) | set(output_palette))`` is constant across
all pairs.

Recognition vocabulary axis: cross-pair constancy on the MAGNITUDE of
the total palette footprint. The palette-axis matchers added at iters
184 / 185 / 186 / 187 (set-containment direction: subset / equality /
disjoint / inverse subset) and iters 188 / 189 (cardinality direction
strict ``>`` and ``<``, with iter 185 the ``==`` cell) carved up the
per-pair *shape* of the palette pair. Iters 190 / 191 opened the
cross-pair-constancy sub-axis on the symmetric-difference SIZE (iter
190) and on the intersection SIZE (iter 191). This matcher completes
the |Δ| / |∩| / |∪| triple on the same sub-axis by naming cross-pair
constancy on the **total palette footprint**: the number of distinct
colours that appear in input OR output is the same integer in every
training pair, regardless of which specific colours those are.

Why a separate matcher rather than parameterising iters 190 / 191 or
any of iters 184 / 185 / 186 / 187 / 188 / 189 with a union-size
value:

  * The matcher contract (docs/RULE_FORMAT.md §4) is name-keyed
    recognition vocabulary; the rule's stored ``condition.type`` is
    the recognition handle's name, not a name+params tuple. Iter 190
    pins the magnitude of *change*; iter 191 pins the magnitude of
    *preservation*; this matcher pins the magnitude of the *total
    palette footprint*. They sit on the same cross-pair-constancy
    sub-axis but on three distinct derived integers of the per-pair
    palette-pair decomposition |A| + |B| = |A ∪ B| + |A ∩ B|, with
    the identity |A △ B| = |A ∪ B| - |A ∩ B|. Constancy of any one
    does not imply constancy of either of the other two; pairwise
    however constancy of any two implies constancy of the third (up
    to the linear identity), so this matcher closes the triple.
  * Iter 185 (equality) fires iff input palette == output palette
    per pair. Then |∪| equals |input palette| = |output palette| of
    THAT pair. Constancy of |∪| therefore requires constancy of the
    palette size across pairs -- a strictly stronger condition than
    iter 185 alone. INDEPENDENT: iter 185 can fire without this
    matcher (equal palettes of varying sizes across pairs) and this
    matcher can fire without iter 185 (constant union size with
    non-equal palettes per pair).
  * Iter 184 (output ⊆ input): |∪| equals input palette size per
    pair. Constancy of |∪| is constancy of |input palette| -- a
    strict refinement: iter 184 imposes set-containment direction
    per pair WITHOUT pinning the input-palette-size across pairs.
  * Iter 187 (input ⊆ output): |∪| equals output palette size per
    pair. Mirror of iter 184 -- INDEPENDENT in the same way.
  * Iter 186 (disjoint): |∪| equals |input| + |output| per pair.
    Constancy of the SUM across pairs is a strict refinement: iter
    186 imposes disjointness per pair WITHOUT pinning the cross-
    pair sum.
  * Iter 190 (|Δ| constant) and iter 191 (|∩| constant) sit on the
    same cross-pair-constancy sub-axis as this matcher, but on the
    OTHER two derived integers. Pairwise INDEPENDENT: constancy of
    any one of {|Δ|, |∩|, |∪|} does NOT imply constancy of either
    of the others. (Constancy of any TWO implies constancy of the
    third by the linear identity |Δ| = |∪| - |∩|; the implication
    therefore takes a CONJUNCTION as antecedent, not a single matcher.)

Why this matters for ARBOR's intended ruleset:

  * "Total-palette-footprint-constant" rule family: rules whose
    action keeps the cardinality of the colour vocabulary fixed on
    every training pair (regardless of which colours are used).
    Examples:
      - "fixed colour vocabulary" tasks (|∪| == K for some K --
        every pair uses exactly K distinct colours in total, named
        colour-budget pattern).
      - "swap-style" tasks (|∪| == |input| -- swaps preserve the
        union; |∪| pinned across pairs requires |input| constant
        too).
      - "background + N foreground" tasks (|∪| == 1 + N per pair --
        a fixed-size palette plus background, with the same total
        across pairs).
    The conjunction of this matcher with iter 191 (|∩| constant)
    names a sharper recogniser via |Δ| = |∪| - |∩|: it ALSO pins
    |Δ| as a constant. Equivalently the conjunction of this matcher
    with iter 190 pins |∩|, and the conjunction of iters 190 and
    191 pins |∪|. The triple is closed under any-two-imply-third.
  * Cross-pair constancy on the union-size axis is the precondition
    for anti-unification (CLAUDE.md §8) to lift a per-pair total-
    palette-footprint into a constant generalisation variable.
    Without this matcher the cross-pair palette-footprint regularity
    has no named recognition handle to attach a future
    ``condition.type`` to.

Mutual containment / co-fire table (universal-over-pairs semantics):

  * Iter 13 (``identity_transformation``) -- output equals input per
    pair, so union = input palette = output palette of that pair,
    with size |input palette| of that pair. Identity does NOT
    strictly imply this matcher (identity with varying palette
    sizes across pairs has varying union size). INDEPENDENT:
    identity AND constant input-palette-size co-fire; identity with
    varying palette sizes fires iter 13 but not this matcher; this
    matcher with non-identity pairs fires alone.
  * Iter 184 (``output_palette_subset_of_input``) -- union ==
    input palette per pair. Independent: co-fires when input
    palette size is constant; iter 184 alone fires when output ⊆
    input per pair but |input| varies.
  * Iter 185 (``output_palette_equals_input``) -- union ==
    input palette == output palette per pair. INDEPENDENT (see
    above).
  * Iter 186 (``output_palette_disjoint_from_input``) -- union ==
    |input| + |output| per pair. Independent of |∪| constancy
    (e.g. one pair has |input|=2,|output|=3 → |∪|=5; another has
    |input|=1,|output|=4 → |∪|=5; iter 186 fires AND this matcher
    fires; but |input|=2,|output|=3 vs |input|=2,|output|=4 has
    iter 186 firing without this matcher).
  * Iter 187 (``input_palette_subset_of_output``) -- union ==
    output palette per pair. Mirror of iter 184: independent.
  * Iter 188 (``output_palette_count_exceeds_input_palette_count``) /
    iter 189 (``input_palette_count_exceeds_output_palette_count``)
    -- strict cardinality direction per pair. INDEPENDENT of
    union-size constancy: e.g. (iter 188 AND |∪| == 3 every pair)
    co-fires; (iter 188 with varying |∪|) iter-188-alone.
  * Iter 190 (``palette_symmetric_difference_constant_across_pairs``)
    -- the |Δ| sibling on the same cross-pair-constancy sub-axis.
    INDEPENDENT: can co-fire (e.g. constant |Δ| AND constant |∪|)
    and can each fire alone.
  * Iter 191 (``palette_intersection_count_constant_across_pairs``)
    -- the |∩| sibling on the same cross-pair-constancy sub-axis.
    INDEPENDENT in the same way.
  * Iter 14 (``input_color_uniform``) / iter 15
    (``output_color_uniform``) -- inspect the *changed cells'*
    source / target uniformity. Orthogonal to the whole-grid
    palette-∪-size axis.
  * Iter 8 (``consistent_color_mapping``) -- per-pair (C -> K) is a
    function on changed cells. Independent of cross-pair palette
    ∪-size constancy.
  * Iters 30 / 33 / 34 / 35 / 36 / 37 / 38 / 39 / 40 / 42 -- cross-
    pair constancy matchers on the CHANGE-CELL axes. Same cross-
    pair-constancy sub-axis as this matcher and iters 190 / 191,
    but on the change-cell fields rather than on the whole-grid
    palette fields.
  * Every cell- / group- / position- / dimension- / shape-regularity
    matcher (iters 1 / 17 / 18 / 19 / 20 / 22 / 33 / 38 / 39 / 40 /
    41 / 42 / 182 / 183) is orthogonal.

Why fail-closed on empty / malformed (same posture as iters 184 /
185 / 186 / 187 / 188 / 189 / 190 / 191): a missing or non-list
palette is upstream extractor breakage, not evidence the precondition
holds. Universal-over-pairs (with cross-pair constancy) on an empty
pair_analyses list would vacuously fire the gate, which is the wrong
default -- a constancy claim with zero observations is meaningless.

Why strict-list-of-non-bool-ints (mirroring iters 184 / 185 / 186 /
187 / 188 / 189 / 190 / 191): Python bools are an ``int`` subclass;
the iter-182 / 183 / 184 / 185 / 186 / 187 / 188 / 189 / 190 / 191
dimensional / palette matchers all reject them to keep the
recognition layer from accepting placeholder sentinels. Empty
palettes are admissible at the type level (a zero-area grid would
emit an empty palette; upstream guard belongs at the extractor).

Edge cases:

  * A single pair trivially satisfies cross-pair constancy (one
    observation can take only one value). The matcher fires on
    single-pair tasks AS LONG AS that one pair is well-typed --
    consistent with iters 30 / 33 / 34 / 35 / 36 / 37 / 38 / 39 / 40
    / 42 / 190 / 191.
  * Both palettes empty on every pair: |∪| == 0 on every pair,
    constant. The matcher fires. This is the degenerate-palette case
    (zero-area grids); consistent with iter 190 / 191's equally-
    permissive empty-empty posture.
  * Mixed degenerate / non-degenerate pairs: pair 0 has both
    palettes empty (|∪| == 0), pair 1 has any non-zero union. The
    matcher does NOT fire (the two |∪| values differ).

Params:
  (none) -- pure cross-pair constancy check on a derived integer.

Returns True iff:
  - ``patterns`` is a dict, AND
  - ``patterns["pair_analyses"]`` is a non-empty list, AND
  - every analysis is a dict, AND
  - every analysis has an ``input_palette`` value that is a list of
    non-bool ints, AND
  - every analysis has an ``output_palette`` value with the same
    contract, AND
  - the integer ``len(set(input_palette) | set(output_palette))`` is
    bit-identical across every analysis.

No companion-touch required: iter 184 already emits ``input_palette``
and ``output_palette`` from ``_analyze_pair``; this iter is a pure
matcher addition with no ``agent/active_operators.py`` diff.
"""

from __future__ import annotations

from agent.conditions import register


def _is_palette_list(x) -> bool:
    """A palette field must be a list of non-bool ints. Empty is
    admissible at the type level (the union-size gate handles the
    degenerate empty case)."""
    if not isinstance(x, list):
        return False
    for v in x:
        if not isinstance(v, int) or isinstance(v, bool):
            return False
    return True


@register("palette_union_count_constant_across_pairs")
def match(patterns: dict, params: dict) -> bool:
    if not isinstance(patterns, dict):
        return False
    pair_analyses = patterns.get("pair_analyses")
    if not isinstance(pair_analyses, list) or not pair_analyses:
        return False

    canonical_union: int | None = None

    for analysis in pair_analyses:
        if not isinstance(analysis, dict):
            return False
        ip = analysis.get("input_palette")
        op = analysis.get("output_palette")
        if not _is_palette_list(ip):
            return False
        if not _is_palette_list(op):
            return False
        union_size = len(set(ip) | set(op))
        if canonical_union is None:
            canonical_union = union_size
        elif canonical_union != union_size:
            return False

    return canonical_union is not None
