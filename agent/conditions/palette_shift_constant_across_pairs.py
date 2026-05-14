"""
palette_shift_constant_across_pairs -- match tasks where there is a
single integer ``k`` such that, on every example pair, the sorted
output palette equals the sorted input palette shifted element-wise by
``k``:

    sorted(set(output_palette)) == [v + k for v in sorted(set(input_palette))]

The same ``k`` must hold across every pair.

Recognition vocabulary axis: cross-pair constancy on the
**colour-translation** sub-axis of the whole-grid palette pair. The
palette-axis matchers added at iters 184 / 185 / 186 / 187 (set-
containment direction: subset / equality / disjoint / inverse subset),
iters 188 / 189 (cardinality direction strict ``>`` and ``<``, with
iter 185 the ``==`` cell), and iters 190 / 191 / 192 (cross-pair
magnitude constancy on |Δ| / |∩| / |∪|) all decompose the palette pair
along *set-relation* or *magnitude* sub-axes. This matcher opens the
distinct **linear-arithmetic** sub-axis: the colour-translation `k`
that maps input palette to output palette element-wise, when both are
viewed as sorted lists of equal length.

Why a separate matcher rather than parameterising any of iters 184 /
185 / 186 / 187 / 188 / 189 / 190 / 191 / 192:

  * The matcher contract (docs/RULE_FORMAT.md §4) is name-keyed
    recognition vocabulary; the rule's stored ``condition.type`` is
    the recognition handle's name, not a name+params tuple. None of
    iters 184–192 makes a linear-arithmetic claim between the two
    palettes -- they are all set-relation predicates (containment,
    disjointness) or magnitude predicates (counts, |Δ|, |∩|, |∪|).
    This matcher is the first palette-axis entry on the *element-wise
    linear-shift* sub-axis, opening a colour-permutation recognition
    handle distinct from the existing set-cardinality and set-relation
    handles.
  * Iter 185 (equality) is exactly the ``k == 0`` cell of this
    matcher's sub-axis. STRICT IMPLICATION: iter 185 ⇒ this matcher
    (with canonical value ``k == 0``). Reverse does not hold: a task
    where every pair maps {1, 2, 3} → {3, 4, 5} fires this matcher
    with ``k == 2`` but rejects iter 185.
  * Iter 192 (|∪| constant): the union sizes |A ∪ B| can be constant
    across pairs without the shift being defined (e.g. swap-style
    re-colourings where output is a permutation of input with no
    constant element-wise offset). INDEPENDENT.

Why this matters for ARBOR's intended ruleset:

  * "Colour-translation" rule family: rules whose action shifts every
    grid cell's colour by the same constant integer (modulo the
    valid-colour range). Examples:
      - "increment every colour by 1" tasks (every colour C becomes
        C+1; ``k == 1``).
      - "decrement every colour by some K" tasks (mirror, ``k < 0``).
      - "consistent recolour preserving order" tasks where the input
        palette has a natural ordering (sorted) and the output palette
        is a sorted offset.
    The conjunction with iter 185 names the trivial ``k == 0`` cell
    (palette-identity); with non-zero ``k`` it names a colour-
    translation rule distinct from all existing palette-axis named
    families.
  * Cross-pair constancy on the linear-shift axis is the precondition
    for anti-unification (CLAUDE.md §8) to lift the per-pair shift
    integer into a constant generalisation variable. Without this
    matcher the cross-pair palette-translation regularity has no
    named recognition handle to attach a future ``condition.type`` to.
  * The "canonical-order convention" worry the iter-192 / 193 next-
    gap notes flagged is resolved here by relying on the upstream
    extractor's invariant: ``input_palette`` / ``output_palette`` are
    emitted by ``ExtractPatternOperator._analyze_pair`` as
    ``sorted(set(...))`` (ascending integer order). The shift `k` is
    therefore defined unambiguously when the two sorted lists have
    the same length; no extra convention is introduced here.

Mutual containment / co-fire table (universal-over-pairs semantics):

  * Iter 13 (``identity_transformation``) -- output equals input per
    pair, so the per-pair palette pair is identical; ``k == 0`` per
    pair, constant. STRICT IMPLICATION: iter 13 ⇒ this matcher
    (canonical ``k == 0``). Reverse does NOT hold: a task with a
    constant non-zero ``k`` (e.g. uniform increment by 2) rejects
    iter 13.
  * Iter 184 (``output_palette_subset_of_input``) -- output ⊆ input
    per pair. For the shift to be defined, |input| == |output|; iter
    184 with strict subset (some colour dropped) would have |output|
    < |input|, so this matcher does NOT fire. Iter 184 with equality
    (output == input as sets) -- the iter-185 case -- is the only
    overlap, and it fires this matcher with ``k == 0``. So iter 184
    \\ iter 185 (strict subset) and this matcher are MUTUALLY
    EXCLUSIVE on the universal-over-pairs gate when any pair has
    strict subset.
  * Iter 185 (``output_palette_equals_input``) -- equality per pair
    forces ``k == 0`` per pair. STRICT IMPLICATION: iter 185 ⇒ this
    matcher.
  * Iter 186 (``output_palette_disjoint_from_input``) -- intersection
    empty per pair. The shift ``k`` can still be defined when the two
    sorted palettes have the same length and the disjointness comes
    from a uniform offset (e.g. input {0, 1, 2}, output {3, 4, 5},
    ``k == 3``). Iter 186 AND this matcher CAN CO-FIRE.
  * Iter 187 (``input_palette_subset_of_output``) -- input ⊆ output
    per pair. Mirror of iter 184: strict subset forces |input| <
    |output| → this matcher does NOT fire. Only the equality cell
    (iter 185) overlaps.
  * Iter 188 (``output_palette_count_exceeds_input_palette_count``) /
    iter 189 (``input_palette_count_exceeds_output_palette_count``)
    -- strict cardinality direction per pair. Strict inequality
    forces |input| != |output| → this matcher does NOT fire. MUTUALLY
    EXCLUSIVE.
  * Iter 190 (``palette_symmetric_difference_constant_across_pairs``)
    -- when a constant shift ``k`` holds with |input| == |output| ==
    N, the |Δ| equals 2N if k != 0 and 0 if k == 0. Constancy of |Δ|
    follows from constancy of N + constancy of k. So this matcher
    AND a constant-cardinality task IMPLY constancy of |Δ|. NOT a
    strict refinement in the matcher-only sense (this matcher allows
    pair-to-pair varying |input| only if k were still defined --
    impossible without same-cardinality), but in practice constancy
    of palette size + constant k ⇒ constant |Δ|.
  * Iter 191 (``palette_intersection_count_constant_across_pairs``)
    -- constancy of |∩|. With constant ``k`` and constant |input| ==
    |output| == N: |∩| = N when k == 0, 0 when |k| >= N (full
    disjointness), and intermediate otherwise (a sorted-and-shifted
    list intersects itself by ``N - |k|`` when contiguous integer
    inputs). Independent in the general case; can co-fire when both
    constancies hold.
  * Iter 192 (``palette_union_count_constant_across_pairs``) --
    constancy of |∪|. Independent in the general case; can co-fire.
  * Iter 14 (``input_color_uniform``) / iter 15
    (``output_color_uniform``) -- inspect the *changed cells'*
    source / target uniformity. Orthogonal to the whole-grid
    palette-shift axis.
  * Iter 8 (``consistent_color_mapping``) -- per-pair (C -> K) is a
    function on changed cells. INDEPENDENT of whole-grid palette
    shift; can co-fire when both fire (consistent mapping with a
    uniform shift) and disagree.
  * Iters 30 / 33 / 34 / 35 / 36 / 37 / 38 / 39 / 40 / 42 / 193 --
    cross-pair constancy matchers on the CHANGE-CELL axes. Same
    cross-pair-constancy sub-axis as this matcher and iters 190 /
    191 / 192, but on the change-cell fields rather than on the
    whole-grid palette fields.
  * Every cell- / group- / position- / dimension- / shape-regularity
    matcher (iters 1 / 17 / 18 / 19 / 20 / 22 / 33 / 38 / 39 / 40 /
    41 / 42 / 182 / 183 / 193) is orthogonal.

Why fail-closed on empty / malformed (same posture as iters 184–192):
a missing or non-list palette is upstream extractor breakage, not
evidence the precondition holds. Universal-over-pairs on an empty
``pair_analyses`` list would vacuously fire the gate, which is the
wrong default -- a constancy claim with zero observations is
meaningless.

Why fail-closed on differing palette cardinalities per pair: the shift
``k`` is defined element-wise on the sorted lists; it has no value
when the two lists have different lengths. Per-pair cardinality
mismatch makes the precondition undefined for that pair, which is
itself a NO under "every pair has a constant shift".

Why fail-closed when no pair anchors ``k``: a task where every pair has
both palettes empty has no defined shift anywhere -- the universal-
over-pairs claim "the shift is k on every pair" reduces to a vacuous
universal, but the matcher's name promises a non-trivial colour-
translation recognition. Same posture as iter 13 (``identity_
transformation``) which rejects empty pair_analyses lists, and iter
14 (``input_color_uniform``) which rejects zero-change-cell pairs.

Why strict-list-of-non-bool-ints (mirroring iters 184 / 185 / 186 /
187 / 188 / 189 / 190 / 191 / 192): Python bools are an ``int``
subclass; the iter-182–192 dimensional / palette matchers all reject
them to keep the recognition layer from accepting placeholder
sentinels. Empty palettes are admissible at the type level (a zero-
area grid would emit an empty palette; the per-pair shift-undefined
case is handled at the gate level above).

Why ``set`` then ``sorted`` rather than relying on the palette being
already-sorted-unique: the upstream extractor (iter 184) emits
``input_palette = sorted({v for row in raw_in for v in row})``, so
both fields are sorted lists of distinct integers by construction.
Re-deriving via ``sorted(set(...))`` defends against a future
extractor regression that emits duplicates or out-of-order lists --
matchers are deterministic predicates on the field's documented
contract, not on its current implementation. Mirror of iter 191's
``set(input_palette) & set(output_palette)`` defensive re-derivation.

Edge cases:

  * A single pair with non-empty same-cardinality palettes trivially
    satisfies cross-pair constancy on the derived ``k``. The matcher
    fires on single-pair tasks as long as that one pair has a defined
    ``k`` and is well-typed. Consistent with iters 30 / 33 / 34 / 35
    / 36 / 37 / 38 / 39 / 40 / 42 / 190 / 191 / 192 / 193 firing on
    single-pair tasks.
  * Both palettes empty on every pair: no pair anchors ``k``; the
    matcher does NOT fire (universal-over-pairs claim is vacuous, but
    the name promises a non-trivial shift recognition). Distinct from
    iters 190 / 191 / 192's empty-empty acceptance because those
    matchers' derived integer (|Δ| / |∩| / |∪|) is well-defined on
    empty palettes (zero), whereas a shift is not.
  * Mixed empty / non-empty pairs: if at least one pair has same-
    cardinality non-empty palettes that anchor a defined ``k``, and
    every other pair either matches that ``k`` OR has matched-empty
    palettes (no constraint contributed), the matcher fires. If any
    pair has |input| != |output|, the matcher fails. Empty-empty
    pairs contribute no constraint and do not anchor ``k`` by
    themselves.
  * The shift ``k`` is an arbitrary integer, including negative. The
    matcher pins constancy of ``k`` across pairs, not its sign or
    magnitude (the value itself is data carried in a future
    ``action.args``, not in ``condition.params``).

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
  - for every pair, ``len(set(input_palette)) ==
    len(set(output_palette))``, AND
  - for every pair, the sorted-unique output equals the sorted-unique
    input shifted element-wise by a single integer ``k`` (the per-pair
    shift is well-defined), AND
  - the per-pair ``k`` is bit-identical across every pair that
    anchors it (non-empty pairs); empty-empty pairs contribute no
    constraint, AND
  - at least one pair anchors ``k`` (no all-empty-empty task fires).

No companion-touch required: iter 184 already emits ``input_palette``
and ``output_palette`` from ``_analyze_pair``; this iter is a pure
matcher addition with no ``agent/active_operators.py`` diff. F8
inert.
"""

from __future__ import annotations

from agent.conditions import register


def _is_palette_list(x) -> bool:
    """A palette field must be a list of non-bool ints. Empty is
    admissible at the type level (the per-pair shift-defined gate
    above handles the degenerate empty case)."""
    if not isinstance(x, list):
        return False
    for v in x:
        if not isinstance(v, int) or isinstance(v, bool):
            return False
    return True


def _per_pair_shift(ip_sorted: list, op_sorted: list) -> int | None:
    """Return the single integer ``k`` such that ``op_sorted[i] ==
    ip_sorted[i] + k`` for every ``i``, or ``None`` if no such
    integer exists.

    Caller has already verified ``len(ip_sorted) == len(op_sorted) >=
    1``.
    """
    k = op_sorted[0] - ip_sorted[0]
    for i in range(1, len(ip_sorted)):
        if op_sorted[i] - ip_sorted[i] != k:
            return None
    return k


@register("palette_shift_constant_across_pairs")
def match(patterns: dict, params: dict) -> bool:
    if not isinstance(patterns, dict):
        return False
    pair_analyses = patterns.get("pair_analyses")
    if not isinstance(pair_analyses, list) or not pair_analyses:
        return False

    canonical_k: int | None = None
    anchored: bool = False

    for analysis in pair_analyses:
        if not isinstance(analysis, dict):
            return False
        ip = analysis.get("input_palette")
        op = analysis.get("output_palette")
        if not _is_palette_list(ip):
            return False
        if not _is_palette_list(op):
            return False
        ip_sorted = sorted(set(ip))
        op_sorted = sorted(set(op))
        if len(ip_sorted) != len(op_sorted):
            return False
        if len(ip_sorted) == 0:
            # Both empty: shift undefined for this pair. Contributes no
            # constraint; do not anchor ``k`` from it.
            continue
        k = _per_pair_shift(ip_sorted, op_sorted)
        if k is None:
            return False
        if not anchored:
            canonical_k = k
            anchored = True
        elif canonical_k != k:
            return False

    return anchored
