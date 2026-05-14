"""
palette_intersection_count_constant_across_pairs -- match tasks where
the size of the intersection between the input palette and the output
palette is the same integer on every example pair:
``len(set(input_palette) & set(output_palette))`` is constant across
all pairs.

Recognition vocabulary axis: cross-pair constancy on the MAGNITUDE of
recolour PRESERVATION. The palette-axis matchers added at iters 184 /
185 / 186 / 187 (set-containment direction: subset / equality /
disjoint / inverse subset) and iters 188 / 189 (cardinality direction
strict ``>`` and ``<``, with iter 185 the ``==`` cell) carved up the
per-pair *shape* of the palette pair. Iter 190
(palette_symmetric_difference_constant_across_pairs) opened the
cross-pair-constancy sub-axis on the symmetric-difference SIZE -- the
number of distinct colours that *change membership* between input and
output. This matcher names the dual cross-pair invariant on the
**common palette size**: the number of distinct colours that *appear
in both* input and output is the same integer in every training pair,
regardless of which specific colours those are.

Why a separate matcher rather than parameterising iter 190 or any of
iters 184 / 185 / 186 / 187 / 188 / 189 with an intersection-size
value:

  * The matcher contract (docs/RULE_FORMAT.md §4) is name-keyed
    recognition vocabulary; the rule's stored ``condition.type`` is
    the recognition handle's name, not a name+params tuple. Iter 190
    pins the magnitude of *change*; this matcher pins the magnitude
    of *preservation*. They are duals on the per-pair palette-pair
    decomposition |A| + |B| = |A ∪ B| + |A ∩ B|, where iter 190
    locks |A △ B| = |A ∪ B| - |A ∩ B| and this matcher locks
    |A ∩ B|. Constancy of one does not imply constancy of the other;
    they need distinct recognition handles.
  * Iter 186 (output ∩ input == ∅) fires iff intersection == 0 on
    every pair, which is a constant. STRICT IMPLICATION:
    iter 186 ⇒ this matcher (with canonical value 0). The reverse
    does not hold: a task where every pair has intersection size 2
    fires this matcher but not iter 186.
  * Iter 185 (equality) fires iff input palette == output palette
    per pair. The intersection size then equals |input palette| =
    |output palette| of THAT pair. Constancy of the intersection
    size therefore requires constancy of the palette size across
    pairs -- a strictly stronger condition than iter 185 alone.
    INDEPENDENT: iter 185 can fire without this matcher (equal
    palettes of varying sizes across pairs) and this matcher can
    fire without iter 185 (constant intersection size with non-equal
    palettes per pair).
  * Iter 184 (output ⊆ input): intersection equals output palette
    per pair. Constancy of intersection size is constancy of
    |output palette| -- a strict refinement: iter 184 imposes
    set-containment direction per pair WITHOUT pinning the output-
    palette-size across pairs.
  * Iter 187 (input ⊆ output): intersection equals input palette
    per pair. Mirror of iter 184 -- INDEPENDENT in the same way.
  * Iter 190 (|A △ B| constant): on the same cross-pair-constancy
    sub-axis as this matcher, but on the DUAL derived integer.
    Independent: can co-fire (|Δ| == 2 AND |∩| == 1 on every pair)
    and can each fire alone.

Why this matters for ARBOR's intended ruleset:

  * "Magnitude-of-preservation-constant" rule family: rules whose
    action keeps exactly N distinct colours fixed on every training
    pair (regardless of which colours they are). Examples:
      - "fully replace palette" tasks (|∩| == 0 -- no colour
        survives; the precondition for iter 186 plus a constant
        replacement size).
      - "keep one anchor colour" tasks (|∩| == 1 -- exactly one
        colour appears in both input and output per pair; named
        anchor pattern).
      - "background-preserving" tasks (|∩| == 1 or 2 -- background
        and possibly a sentinel colour survive each pair).
      - "swap-style" tasks (|∩| == |input| - k where k is the swap
        size; constancy of |∩| picks out a fixed-arity swap).
    The conjunction of this matcher with iter 184 / 187 names a
    sharper recogniser: e.g. (this matcher AND iter 184 AND
    |∩| == 1) names "every pair preserves exactly one input colour
    that also appears in the output, and drops the rest".
  * Cross-pair constancy on the intersection-size axis is the
    precondition for anti-unification (CLAUDE.md §8) to lift a per-
    pair preserved-palette size into a constant generalisation
    variable. Without this matcher the cross-pair palette-
    preservation regularity has no named recognition handle to
    attach a future ``condition.type`` to.

Mutual containment / co-fire table (universal-over-pairs semantics):

  * Iter 13 (``identity_transformation``) -- output equals input per
    pair, so intersection = input palette = output palette of that
    pair, with size |input palette| of that pair. Identity does NOT
    strictly imply this matcher (identity with varying palette
    sizes across pairs has varying intersection size). INDEPENDENT:
    identity AND constant input-palette-size co-fire; identity with
    varying palette sizes fires iter 13 but not this matcher; this
    matcher with non-identity pairs fires alone.
  * Iter 184 (``output_palette_subset_of_input``) -- intersection ==
    output palette per pair. Independent: co-fires when output
    palette size is constant; iter 184 alone fires when output ⊆
    input per pair but |output| varies.
  * Iter 185 (``output_palette_equals_input``) -- intersection ==
    input palette == output palette per pair. INDEPENDENT (see
    above).
  * Iter 186 (``output_palette_disjoint_from_input``) -- intersection
    == ∅ per pair, size 0, constant. STRICT IMPLICATION:
    iter 186 ⇒ this matcher (canonical value 0). Reverse does not
    hold.
  * Iter 187 (``input_palette_subset_of_output``) -- intersection ==
    input palette per pair. Independent (mirror of iter 184).
  * Iter 188 (``output_palette_count_exceeds_input_palette_count``) /
    iter 189 (``input_palette_count_exceeds_output_palette_count``)
    -- strict cardinality direction per pair. INDEPENDENT of
    intersection-size constancy: e.g. (iter 188 AND |∩| == 1 every
    pair) co-fires; (iter 188 with varying |∩|) iter-188-alone.
  * Iter 190 (``palette_symmetric_difference_constant_across_pairs``)
    -- the dual on the symmetric-difference SIZE. INDEPENDENT: can
    co-fire (constant |Δ| AND constant |∩|, e.g. both palettes
    constant) and can each fire alone.
  * Iter 14 (``input_color_uniform``) / iter 15
    (``output_color_uniform``) -- inspect the *changed cells'*
    source / target uniformity. Orthogonal to the whole-grid
    palette-∩-size axis.
  * Iter 8 (``consistent_color_mapping``) -- per-pair (C -> K) is a
    function on changed cells. Independent of cross-pair palette
    ∩-size constancy.
  * Iters 30 / 33 / 34 / 35 / 36 / 37 / 38 / 39 / 40 / 42 -- cross-
    pair constancy matchers on the CHANGE-CELL axes. Same cross-
    pair-constancy sub-axis as this matcher and iter 190, but on
    the change-cell fields rather than on the whole-grid palette
    fields.
  * Every cell- / group- / position- / dimension- / shape-regularity
    matcher (iters 1 / 17 / 18 / 19 / 20 / 22 / 33 / 38 / 39 / 40 /
    41 / 42 / 182 / 183) is orthogonal.

Why fail-closed on empty / malformed (same posture as iters 184 /
185 / 186 / 187 / 188 / 189 / 190): a missing or non-list palette is
upstream extractor breakage, not evidence the precondition holds.
Universal-over-pairs (with cross-pair constancy) on an empty
pair_analyses list would vacuously fire the gate, which is the wrong
default -- a constancy claim with zero observations is meaningless.

Why strict-list-of-non-bool-ints (mirroring iters 184 / 185 / 186 /
187 / 188 / 189 / 190): Python bools are an ``int`` subclass; the
iter-182 / 183 / 184 / 185 / 186 / 187 / 188 / 189 / 190 dimensional /
palette matchers all reject them to keep the recognition layer from
accepting placeholder sentinels. Empty palettes are admissible at the
type level (a zero-area grid would emit an empty palette; upstream
guard belongs at the extractor).

Edge cases:

  * A single pair trivially satisfies cross-pair constancy (one
    observation can take only one value). The matcher fires on
    single-pair tasks AS LONG AS that one pair is well-typed --
    consistent with iters 30 / 33 / 34 / 35 / 36 / 37 / 38 / 39 / 40
    / 42 / 190.
  * Both palettes empty on every pair: |∩| == 0 on every pair,
    constant. The matcher fires. This is the degenerate-palette case
    (zero-area grids); consistent with iter 190's equally-permissive
    empty-empty posture (two empty palettes have empty intersection).
  * Mixed degenerate / non-degenerate pairs: pair 0 has both
    palettes empty (|∩| == 0), pair 1 has any non-zero intersection.
    The matcher does NOT fire (the two |∩| values differ).

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
  - the integer ``len(set(input_palette) & set(output_palette))`` is
    bit-identical across every analysis.

No companion-touch required: iter 184 already emits ``input_palette``
and ``output_palette`` from ``_analyze_pair``; this iter is a pure
matcher addition with no ``agent/active_operators.py`` diff.
"""

from __future__ import annotations

from agent.conditions import register


def _is_palette_list(x) -> bool:
    """A palette field must be a list of non-bool ints. Empty is
    admissible at the type level (the intersection-size gate
    handles the degenerate empty case)."""
    if not isinstance(x, list):
        return False
    for v in x:
        if not isinstance(v, int) or isinstance(v, bool):
            return False
    return True


@register("palette_intersection_count_constant_across_pairs")
def match(patterns: dict, params: dict) -> bool:
    if not isinstance(patterns, dict):
        return False
    pair_analyses = patterns.get("pair_analyses")
    if not isinstance(pair_analyses, list) or not pair_analyses:
        return False

    canonical_intersection: int | None = None

    for analysis in pair_analyses:
        if not isinstance(analysis, dict):
            return False
        ip = analysis.get("input_palette")
        op = analysis.get("output_palette")
        if not _is_palette_list(ip):
            return False
        if not _is_palette_list(op):
            return False
        intersection_size = len(set(ip) & set(op))
        if canonical_intersection is None:
            canonical_intersection = intersection_size
        elif canonical_intersection != intersection_size:
            return False

    return canonical_intersection is not None
