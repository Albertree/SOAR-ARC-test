"""
palette_symmetric_difference_constant_across_pairs -- match tasks where
the size of the symmetric difference between the input palette and the
output palette is the same integer on every example pair:
``len(set(input_palette) ^ set(output_palette))`` is constant across
all pairs.

Recognition vocabulary axis: cross-pair constancy on the MAGNITUDE of
recolour. The palette-axis matchers added at iters 184 / 185 / 186 /
187 (set-containment direction: subset / equality / disjoint / inverse
subset) and iters 188 / 189 (cardinality direction strict ``>`` and
``<``, with iter 185 the ``==`` cell) carved up the per-pair *shape*
of the palette pair. This matcher names the orthogonal **cross-pair
invariant** on the symmetric-difference SIZE: the number of distinct
colours that *change membership* between input and output is the same
integer in every training pair, regardless of which specific colours
those are.

Why a separate matcher rather than parameterising any of iters 184 /
185 / 186 / 187 / 188 / 189 with a Δ-size value:

  * The matcher contract (docs/RULE_FORMAT.md §4) is name-keyed
    recognition vocabulary; the rule's stored ``condition.type`` is
    the recognition handle's name, not a name+params tuple. None of
    iters 184 / 185 / 186 / 187 / 188 / 189 makes a cross-pair
    constancy claim -- they are all per-pair set-membership /
    cardinality predicates universally over the pairs. This matcher
    is the first palette-axis entry on the *cross-pair-constancy*
    sub-axis, mirroring the iter-30 / 33 / 34 / 35 / 36 / 37 / 38 /
    39 / 40 / 42 family which sit on a cross-pair-constancy sub-axis
    of the change-cell axes.
  * Iter 185 (equality) fires iff |Δ| == 0 on every pair, so iter
    185 strictly implies this matcher (with constant value 0). The
    reverse does not hold: a task where every pair has |Δ| == 2 (one
    colour dropped, one added) fires this matcher but not iter 185.
    The matcher is therefore a strict relaxation of iter 185 on the
    "magnitude of palette change" sub-axis.
  * Iter 184 (output ⊆ input), iter 187 (input ⊆ output): each pair's
    Δ size equals the cardinality of the OTHER half of the
    inclusion (|input \\ output| and |output \\ input| respectively,
    since one half is empty under the inclusion). Constancy of that
    cardinality across pairs is a strict refinement: iters 184 / 187
    impose set-containment direction per pair WITHOUT imposing
    constancy of the drop / addition count across pairs.
  * Iter 186 (disjoint): each pair's Δ size equals
    |set(input)| + |set(output)|. Constancy of the SUM across pairs
    is a strict refinement: iter 186 imposes disjointness per pair
    WITHOUT imposing palette-size constancy across pairs.

Why this matters for ARBOR's intended ruleset:

  * "Magnitude-of-recolour-constant" rule family: rules whose action
    changes exactly N distinct colours on every training pair
    (regardless of which colours change). Examples:
      - "swap two colours" tasks (|Δ| == 0 on every pair only if the
        swap is on the SAME palette; |Δ| > 0 if the swap introduces
        fresh colours -- but the magnitude is constant).
      - "add a marker colour" tasks (|Δ| == 1 -- exactly one fresh
        output colour per pair).
      - "drop the noise colour" tasks (|Δ| == 1 -- exactly one input
        colour erased per pair).
      - "two-colour-change" tasks (|Δ| == 2 -- one in, one out, or
        two in / two out, etc.).
    The conjunction of this matcher with one of iters 184 / 187 / 186
    names a more refined transformation family: e.g. (this matcher
    AND iter 187 AND |Δ| == 1) names "exactly one fresh output
    colour added per pair". The matcher's own job is to pin the
    constancy; the specific magnitude is data that a future
    emission-side branch reads off ``patterns["pair_analyses"]``.
  * Cross-pair constancy on a palette axis is the precondition for
    anti-unification (CLAUDE.md §8) to lift a per-pair Δ size into a
    constant generalisation variable. Without this matcher the
    cross-pair palette-magnitude regularity has no named recognition
    handle to attach a future ``condition.type`` to.

Mutual containment / co-fire table (universal-over-pairs semantics):

  * Iter 13 (``identity_transformation``) -- input palette equals
    output palette per pair, so |Δ| == 0 on every pair; that is a
    constant. Identity ⇒ this matcher (strict implication on the
    universal-over-pairs gate). Reverse does NOT hold: this matcher
    fires whenever |Δ| is constant, not only when |Δ| == 0.
  * Iter 184 (``output_palette_subset_of_input``) -- output ⊆ input
    per pair forces |output \\ input| == 0 per pair, so |Δ| ==
    |input \\ output| per pair. Constancy of |Δ| across pairs is
    independent of subset-direction constancy per pair -- the
    matcher and iter 184 CAN co-fire (e.g. every pair drops exactly
    one input colour) and can disagree (e.g. one pair drops one
    colour, another pair drops two). NOT in a refinement relation
    either direction.
  * Iter 185 (``output_palette_equals_input``) -- equality means
    |Δ| == 0 per pair; that is constant (0). STRICT IMPLICATION:
    iter 185 ⇒ this matcher (with canonical value 0). The reverse
    does not hold (this matcher fires on any constant value).
  * Iter 186 (``output_palette_disjoint_from_input``) -- disjoint
    per pair gives |Δ| == |set(input)| + |set(output)| per pair.
    Constancy of the sum is a strict refinement: iter 186 imposes
    disjointness per pair WITHOUT pinning the cross-pair sum.
  * Iter 187 (``input_palette_subset_of_output``) -- mirror of iter
    184: per-pair |Δ| == |output \\ input|. Constancy is orthogonal.
  * Iter 188 (``output_palette_count_exceeds_input_palette_count``) /
    iter 189 (``input_palette_count_exceeds_output_palette_count``)
    -- strict cardinality direction per pair (|output| - |input| > 0
    on every pair / < 0 on every pair). Independent of |Δ|
    constancy: e.g. a task with |output| - |input| == 1 on every
    pair (always one net addition) fires iter 188 AND this matcher
    (with canonical |Δ| == 1 or any other constant); a task with
    |output| - |input| > 0 on every pair but varying magnitudes
    (pair 0: +1, pair 1: +3) fires iter 188 but NOT this matcher.
  * Iter 14 (``input_color_uniform``) / iter 15
    (``output_color_uniform``) -- inspect the *changed cells'*
    source / target uniformity. Orthogonal to the whole-grid
    palette-Δ-size axis.
  * Iter 8 (``consistent_color_mapping``) -- per-pair (C -> K) is a
    function on changed cells. Independent of cross-pair palette
    Δ-size constancy.
  * Iters 30 / 33 / 34 / 35 / 36 / 37 / 38 / 39 / 40 / 42 -- cross-
    pair constancy matchers on the CHANGE-CELL axes (positions,
    count, colour pairs, group count, etc.). Same cross-pair-
    constancy sub-axis as this matcher, but on the change-cell
    fields rather than on the whole-grid palette fields. The two
    families together carve cross-pair constancy across both axes
    of the iter-1 / 184 split.
  * Every cell- / group- / position- / dimension- / shape-regularity
    matcher (iters 1 / 17 / 18 / 19 / 20 / 22 / 33 / 38 / 39 / 40 /
    41 / 42 / 182 / 183) is orthogonal.

Why fail-closed on empty / malformed (same posture as iters 184 /
185 / 186 / 187 / 188 / 189): a missing or non-list palette is
upstream extractor breakage, not evidence the precondition holds.
Universal-over-pairs (with cross-pair constancy) on an empty
pair_analyses list would vacuously fire the gate, which is the wrong
default -- a constancy claim with zero observations is meaningless.

Why strict-list-of-non-bool-ints (mirroring iters 184 / 185 / 186 /
187 / 188 / 189): Python bools are an ``int`` subclass; the iter-
182 / 183 / 184 / 185 / 186 / 187 / 188 / 189 dimensional / palette
matchers all reject them to keep the recognition layer from
accepting placeholder sentinels. Empty palettes are admissible at
the type level (a zero-area grid would emit an empty palette;
upstream guard belongs at the extractor).

Edge cases:

  * A single pair trivially satisfies cross-pair constancy (one
    observation can take only one value). The matcher fires on
    single-pair tasks AS LONG AS that one pair is well-typed --
    consistent with the iter-30 / 33 / 34 / 35 / 36 / 37 / 38 / 39 /
    40 / 42 family which all fire on single-pair tasks.
  * Both palettes empty on every pair: |Δ| == 0 on every pair, which
    is constant. The matcher fires. This is the degenerate-palette
    case (zero-area grids); consistent with iter 185's equally-
    permissive empty-empty posture (two empty palettes are equal).
  * Mixed degenerate / non-degenerate pairs: pair 0 has both
    palettes empty (|Δ| == 0), pair 1 has any non-zero |Δ|. The
    matcher does NOT fire (the two |Δ| values differ).

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
  - the integer ``len(set(input_palette) ^ set(output_palette))`` is
    bit-identical across every analysis.

No companion-touch required: iter 184 already emits ``input_palette``
and ``output_palette`` from ``_analyze_pair``; this iter is a pure
matcher addition with no ``agent/active_operators.py`` diff.
"""

from __future__ import annotations

from agent.conditions import register


def _is_palette_list(x) -> bool:
    """A palette field must be a list of non-bool ints. Empty is
    admissible at the type level (the symmetric-difference gate
    handles the degenerate empty case)."""
    if not isinstance(x, list):
        return False
    for v in x:
        if not isinstance(v, int) or isinstance(v, bool):
            return False
    return True


@register("palette_symmetric_difference_constant_across_pairs")
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
        ip = analysis.get("input_palette")
        op = analysis.get("output_palette")
        if not _is_palette_list(ip):
            return False
        if not _is_palette_list(op):
            return False
        delta = len(set(ip) ^ set(op))
        if canonical_delta is None:
            canonical_delta = delta
        elif canonical_delta != delta:
            return False

    return canonical_delta is not None
