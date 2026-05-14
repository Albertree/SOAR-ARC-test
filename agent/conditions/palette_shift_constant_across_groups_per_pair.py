"""
palette_shift_constant_across_groups_per_pair -- match tasks where, on
every example pair, there exists a single integer ``k`` (which may
vary across pairs) such that every change group's
``sorted(set(output_colors))`` equals every group's
``sorted(set(input_colors))`` shifted element-wise by that same
per-pair ``k``:

    for every pair P:
        exists k_P such that, for every group G in P,
            sorted(set(G["output_colors"]))
                == [v + k_P for v in sorted(set(G["input_colors"]))]

The per-pair ``k_P`` must hold for EVERY group within that pair. The
``k_P`` of pair 0 and pair 1 may differ -- the across-pair constancy
of this shift is a strictly stronger claim and is named by a separate
matcher (iter 194's ``palette_shift_constant_across_pairs`` does the
whole-grid analogue cross-pair; the per-group cross-pair projection is
the natural follow-up matcher, deliberately deferred to a later iter).

Recognition vocabulary axis: per-pair-per-group projection of iter
194's whole-grid colour-translation sub-axis. Iter 194 inspects the
WHOLE-GRID ``input_palette`` / ``output_palette`` pair on each pair
and demands constancy of the shift ACROSS PAIRS; this matcher
inspects every change group's ``input_colors`` / ``output_colors``
pair on each pair and demands constancy of the shift ACROSS GROUPS
within each pair. The two projections decouple:

  * Iter 194 alone: whole-grid palette has a uniform shift k cross-
    pair, but the change-cells' per-group (input_colors, output_colors)
    is not a uniform shift within at least one pair (e.g. one group
    moves {1} -> {3} (k=2) while a sibling group moves {2} -> {5}
    (k=3) -- the whole-grid palette shift collapses both because
    sorted-unique whole-grid input == sorted-unique whole-grid output -
    k, but the per-group shifts disagree). This matcher rejects.
  * This matcher alone: every pair's groups share a per-pair k, but
    the k value differs across pairs (pair 0 has every group at k=2,
    pair 1 has every group at k=5). Iter 194 rejects (its k must be
    constant cross-pair); this matcher fires.
  * Both: every pair's groups share a per-pair k, AND k is identical
    across all pairs. Strict refinement of this matcher by iter 194
    (only on patterns where the per-pair k coincides with the whole-
    grid shift; on general patterns iter 194 and this matcher are
    independent because they look at different fields).
  * Neither: per-group shift varies within at least one pair AND
    whole-grid shift varies across pairs.

Refinement / orthogonality summary (per-pair, universal-over-groups
semantics):

  * Iter 13 (``identity_transformation``) -- every pair has zero
    change groups. This matcher REJECTS the no-group case (fail-
    closed clause below) to keep its territory disjoint from iter 13
    by construction. Mirrors iter 32 / 35 / 37 / 39 / 193 / 195 / 196
    / 197's empty-group rejection.
  * Iter 14 (``input_color_uniform``) -- pins every group's
    ``input_colors`` to a single colour AND that colour identical
    across all groups in all pairs. If the per-group ``input_colors``
    is a single colour and the per-group ``output_colors`` is also a
    single colour, the per-group shift k is trivially defined per
    group (output - input). Iter 14 does NOT pin the output-side
    cardinality or the per-pair shift constancy; this matcher names
    the per-pair shift constancy independently. CAN co-fire when
    every group has |input_colors| == 1 == |output_colors| AND the
    per-pair (input, output) pairs share a common k.
  * Iter 8 (``consistent_color_mapping``) -- per-pair (C -> K) is a
    function on changed cells (each input colour maps to exactly one
    output colour, possibly different functions across pairs).
    INDEPENDENT of per-group palette shift: a function may exist
    without being a translation, and a translation may exist without
    being a function in the iter-8 sense if groups overlap on a
    colour. CAN co-fire on patterns where the function happens to be
    a per-pair translation that is constant across groups within
    the pair.
  * Iter 9 (``sequential_recoloring``) -- per-pair group outputs form
    a contiguous integer range ordered by ``top_row``. INDEPENDENT
    of per-group palette shift in either direction: sequential
    recoloring constrains per-GROUP single output colour by position
    order, not the per-group input->output palette translation.
  * Iter 194 (``palette_shift_constant_across_pairs``) -- whole-grid
    shift k constant cross-pair. INDEPENDENT in general (different
    fields), refines this matcher only when the whole-grid shift
    coincides with the per-group shift and is constant cross-pair.
  * Iter 185 (``output_palette_equals_input``) -- whole-grid palette
    equality per pair (k_whole == 0 per pair). INDEPENDENT of per-
    group shift: a task can have whole-grid input palette ==
    whole-grid output palette while individual groups permute colours
    within that palette without a constant per-group shift (e.g. one
    group {1}->{2}, another group {2}->{1}; whole-grid palette is
    {1, 2} on both sides, but per-group shifts are +1 and -1 -- this
    matcher rejects).
  * Iter 184 / 186 / 187 / 188 / 189 / 190 / 191 / 192 -- whole-grid
    palette-axis matchers. INDEPENDENT in general (different fields).
  * Iter 193 (``change_count_per_group_constant_across_pairs``) --
    per-group cell-count constancy cross-pair. Same per-group sub-
    axis but distinct field (cell_count vs sorted shift). NOT in a
    refinement relation. CAN co-fire.
  * Iter 195 (``change_input_color_count_per_group_constant_across_pairs``) --
    per-group ``len(input_colors)`` constancy cross-pair. NOT in a
    refinement relation: cross-pair vs per-pair on different
    derivatives. CAN co-fire.
  * Iter 196 (``change_output_color_count_per_group_constant_across_pairs``) --
    per-group ``len(output_colors)`` constancy cross-pair. NOT in a
    refinement relation. CAN co-fire.
  * Iter 197 (``change_color_mapping_count_per_group_constant_across_pairs``) --
    per-group ``len(input_colors) * len(output_colors)`` constancy
    cross-pair. NOT in a refinement relation. CAN co-fire.
  * Iter 23 (``single_change_group_per_pair``) -- pins num_groups == 1
    per pair. With one group per pair, the per-pair shift k is
    trivially constant across the one group. STRICT REFINEMENT of
    this matcher on the "shift exists per group" precondition by
    iter 23 + per-group same-cardinality (single-group pairs are the
    degenerate case where the universal-over-groups quantifier holds
    vacuously after the first group). The reverse does not hold:
    multi-group pairs with a constant per-pair k fire this matcher,
    iter 23 rejects.
  * Iter 28 (``multi_group_per_pair``) -- pins num_groups >= 2 per
    pair. The non-trivial cell of this matcher. INDEPENDENT: a
    multi-group pair may or may not have a constant per-pair shift.
  * Every cell- / position- / dimension- / palette-axis matcher
    (iters 1 / 17 / 18 / 19 / 20 / 22 / 32 / 33 / 38 / 39 / 40 /
    41 / 42 / 182-192) -- orthogonal to per-group palette shift.

Why this matters for ARBOR's intended ruleset:

  * "Every blob shifts colours by the same amount" rule family --
    rules whose action shifts every change cell's colour within a
    blob by the same per-pair constant integer, with the shift
    constant across blobs in the pair. Per-pair (not necessarily
    per-task) constancy is the recognition-side precondition for
    anti-unification (CLAUDE.md §8) to lift the per-group shift
    integer into a per-pair generalisation variable. Without this
    matcher there is no named recognition handle for "the per-group
    shift is the same across all groups in this pair," and the per-
    pair-per-group projection of the colour-translation axis is
    structurally invisible to the slow path.
  * The cross-pair projection of this matcher (every pair's per-pair
    k is identical) is the strictly stronger claim that lifts the
    per-pair shift to a global generalisation variable. It is
    deliberately deferred to the next iter as a smallest-step
    follow-up (named in this iter's session-log entry).
  * The matcher is named on the same per-group palette axis as iters
    195 / 196 / 197 (input-cardinality / output-cardinality / (ic,
    oc) Cartesian-product cardinality per group). Where those three
    name COUNT regularities on the per-group palette pair (set
    cardinalities), this matcher names the LINEAR-ARITHMETIC
    regularity on the same per-group palette pair (the element-wise
    shift between sorted lists). They share the per-group sub-axis
    but inspect orthogonal projections.

Params:
  (none) -- pure within-pair, universal-over-groups constancy check
  on a derived integer (the per-group sorted-shift).

Returns True iff:
  - ``patterns`` is a dict, AND
  - ``patterns["pair_analyses"]`` is a non-empty list, AND
  - every analysis is a dict, AND
  - every analysis has a non-empty ``groups`` list (identity-
    territory rejection), AND
  - every group is a dict with list-typed ``input_colors`` and
    ``output_colors`` fields of length >= 1 (each list represents a
    non-empty group's colours; a zero-length colour list is an
    extractor contract violation), AND
  - every entry of ``input_colors`` and ``output_colors`` is a strict
    int in ``range(10)`` (bool rejected per iter-13 / 14 / ... /
    195 / 196 / 197 strict-type posture), AND
  - for every group, ``len(sorted(set(input_colors))) ==
    len(sorted(set(output_colors)))`` (shift defined element-wise on
    same-cardinality sorted-unique lists), AND
  - for every group, the sorted-unique output equals the sorted-
    unique input shifted element-wise by a single integer ``k_G``
    (the per-group shift is well-defined), AND
  - within each pair, every group's ``k_G`` is bit-identical (the
    per-pair shift constant ``k_P`` is well-defined and shared).

Why fail-closed on empty / no-group / cardinality-mismatch /
shift-undefined / malformed (same posture as iters 14 / 30 / 32 /
33 / 34 / 35 / 36 / 37 / 38 / 39 / 184-197): a missing or zero-
group pair is upstream extractor breakage or identity-territory;
a per-group cardinality mismatch makes the shift undefined for
that group; a non-shift palette permutation breaks the linear-
arithmetic claim. The matcher's name promises a per-pair shift
recognition with universal-over-groups semantics; vacuous or
ill-defined inputs cannot satisfy it.

Why strict per-colour validation (bool rejected, range checked):
``input_colors`` and ``output_colors`` carry small ints in [0, 9];
the matcher performs the same strict-type gating as iter 14 / 18 /
19 / 34 / 35 / 36 / 37 / 38 / 184-197 to keep contract violations
from silently passing.

Why ``sorted(set(...))`` rather than relying on the colour list
being already-sorted-unique: the upstream extractor emits sorted-
unique lists by construction, but matchers re-derive defensively
against a future extractor regression. Mirror of iter 191's and
iter 194's ``set(...)`` defensive re-derivation.

No companion-touch required: ``input_colors`` and ``output_colors``
have been emitted per group since iter 1 (``_analyze_pair`` in
``agent/active_operators.py``); this iter is a pure matcher
addition with no ``agent/active_operators.py`` diff. F8 inert.
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
    if not isinstance(x, list):
        return False
    for v in x:
        if not _is_strict_color(v):
            return False
    return True


def _per_group_shift(ip_sorted: list, op_sorted: list) -> int | None:
    """Return the single integer ``k`` such that
    ``op_sorted[i] == ip_sorted[i] + k`` for every ``i``, or ``None``
    if no such integer exists. Caller has already verified
    ``len(ip_sorted) == len(op_sorted) >= 1``.
    """
    k = op_sorted[0] - ip_sorted[0]
    for i in range(1, len(ip_sorted)):
        if op_sorted[i] - ip_sorted[i] != k:
            return None
    return k


@register("palette_shift_constant_across_groups_per_pair")
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

        canonical_k: int | None = None
        for group in groups:
            if not isinstance(group, dict):
                return False
            input_colors = group.get("input_colors")
            output_colors = group.get("output_colors")
            if not _is_color_list(input_colors) or len(input_colors) < 1:
                return False
            if not _is_color_list(output_colors) or len(output_colors) < 1:
                return False
            ip_sorted = sorted(set(input_colors))
            op_sorted = sorted(set(output_colors))
            if len(ip_sorted) != len(op_sorted):
                return False
            k = _per_group_shift(ip_sorted, op_sorted)
            if k is None:
                return False
            if canonical_k is None:
                canonical_k = k
            elif canonical_k != k:
                return False

    return True
