"""
palette_shift_constant_across_groups_and_pairs -- match tasks where
there is a single global integer ``k`` such that EVERY change group of
EVERY example pair satisfies ``sorted(set(output_colors))`` equals
``sorted(set(input_colors))`` shifted element-wise by that same ``k``:

    exists k such that, for every pair P and every group G in P,
        sorted(set(G["output_colors"]))
            == [v + k for v in sorted(set(G["input_colors"]))]

This is the strict cross-pair refinement of iter 198
(``palette_shift_constant_across_groups_per_pair``), which only requires
the shift to be constant ACROSS GROUPS within each pair and allows the
per-pair ``k_P`` to vary across pairs. This matcher additionally
requires that every per-pair ``k_P`` is bit-identical -- one global
``k`` shared by every group of every pair.

Recognition vocabulary axis: per-group cross-pair-and-group projection
of iter 194's whole-grid colour-translation sub-axis. The decomposition
of the colour-translation axis is now:

  * iter 194 (``palette_shift_constant_across_pairs``) -- WHOLE-GRID
    palette pair, constant k ACROSS PAIRS.
  * iter 198 (``palette_shift_constant_across_groups_per_pair``) -- PER-
    GROUP palette pair, constant k_P ACROSS GROUPS WITHIN A PAIR
    (per-pair k_P may differ across pairs).
  * This matcher -- PER-GROUP palette pair, constant k ACROSS GROUPS
    AND ACROSS PAIRS (one global k shared by every group of every
    pair). Strict refinement of iter 198.

Strict refinement / orthogonality summary (universal-over-groups-and-
pairs semantics):

  * Iter 13 (``identity_transformation``) -- every pair has zero
    change groups. This matcher REJECTS the no-group case (fail-
    closed clause below) to keep its territory disjoint from iter 13
    by construction. Mirrors iter 32 / 35 / 37 / 39 / 193 / 195 / 196
    / 197 / 198's empty-group rejection.
  * Iter 198 (``palette_shift_constant_across_groups_per_pair``) --
    STRICT REFINEMENT: this matcher implies iter 198 (a single global
    k satisfies every per-pair k_P == k by reflexivity), and iter 198
    does NOT imply this matcher (a task with k_P=2 on pair 0 and k_P=5
    on pair 1 fires iter 198, rejects this matcher).
  * Iter 194 (``palette_shift_constant_across_pairs``) -- INDEPENDENT
    in general (different fields: whole-grid palette vs per-group
    palettes). Iter 194 fires on whole-grid sorted-palette shift cross-
    pair; this matcher fires on per-group sorted-palette shift cross-
    group-and-cross-pair. The two CAN co-fire (when the whole-grid
    shift coincides with the per-group shift and is constant cross-
    pair) and CAN disagree (whole-grid shift constant cross-pair but
    per-group shifts within at least one pair disagree, or per-group
    shift constant globally but whole-grid shift varies).
  * Iter 185 (``output_palette_equals_input``) -- WHOLE-GRID palette
    equality per pair (k_whole == 0 per pair). INDEPENDENT of per-
    group shift: a task with whole-grid palette equality may have
    per-group shifts that are non-zero and constant globally (one
    group permutes {1, 2} to {3, 4} and another permutes {3, 4} to
    {1, 2}; whole-grid is {1, 2, 3, 4} on both sides but per-group
    shifts are +2 and -2 -- this matcher rejects). Conversely, a
    constant non-zero global shift gives non-equal whole-grid palettes
    -- iter 185 rejects.
  * Iter 14 (``input_color_uniform``) -- pins every group's
    ``input_colors`` to a single colour AND that colour identical
    across all groups in all pairs. With single-colour groups the
    per-group shift k_G is trivially defined per group as the
    difference between the group's single output colour and its single
    input colour. Iter 14 does NOT pin the per-group output cardinality
    or cross-group / cross-pair constancy of k_G; this matcher names
    the global constancy independently. CAN co-fire when every group
    has |input_colors| == 1 == |output_colors| AND every group's
    (input, output) pair shares a common k.
  * Iter 8 (``consistent_color_mapping``) -- per-pair (C -> K) is a
    function on changed cells. INDEPENDENT: a per-pair function may
    exist without being a translation, and a global translation may
    exist without being a function in the iter-8 sense if groups
    overlap on a colour. CAN co-fire when the function happens to be
    a translation that is constant globally.
  * Iter 9 (``sequential_recoloring``) -- per-pair group outputs form
    a contiguous integer range ordered by ``top_row``. INDEPENDENT
    of per-group palette shift in either direction.
  * Iter 184 / 186 / 187 / 188 / 189 / 190 / 191 / 192 -- whole-grid
    palette-axis matchers. INDEPENDENT in general (different fields).
  * Iter 193 (``change_count_per_group_constant_across_pairs``) --
    per-group cell-count constancy cross-pair. Same per-group sub-
    axis but distinct field (cell_count vs sorted shift). NOT in a
    refinement relation. CAN co-fire.
  * Iter 195 (``change_input_color_count_per_group_constant_across_pairs``) --
    per-group ``len(input_colors)`` constancy cross-pair. NOT in a
    refinement relation. CAN co-fire on patterns where both pin.
  * Iter 196 (``change_output_color_count_per_group_constant_across_pairs``) --
    per-group ``len(output_colors)`` constancy cross-pair. NOT in a
    refinement relation. CAN co-fire on patterns where both pin.
  * Iter 197 (``change_color_mapping_count_per_group_constant_across_pairs``) --
    per-group ``len(input_colors) * len(output_colors)`` constancy
    cross-pair. NOT in a refinement relation. CAN co-fire on patterns
    where both pin.
  * Iter 23 (``single_change_group_per_pair``) -- pins num_groups == 1
    per pair. With one group per pair, this matcher reduces to the
    per-pair-single-group-with-globally-constant-k claim. CAN co-fire.
  * Iter 28 (``multi_group_per_pair``) -- pins num_groups >= 2 per
    pair. The non-trivial cell of this matcher. CAN co-fire when the
    multi-group pairs all share a global k.
  * Every cell- / position- / dimension- / palette-axis matcher
    (iters 1 / 17 / 18 / 19 / 20 / 22 / 32 / 33 / 38 / 39 / 40 / 41 /
    42 / 182-192) -- orthogonal to per-group palette shift.

Why this matters for ARBOR's intended ruleset:

  * "Every blob shifts colours by the same global amount" rule family
    -- rules whose action shifts every change cell's colour by the
    SAME constant integer across every group of every pair. Global
    (not per-pair) constancy is the recognition-side precondition for
    anti-unification (CLAUDE.md §8) to lift the per-group shift
    integer into a TASK-LEVEL generalisation variable. Without this
    matcher, iter 198 names only the within-pair constancy; the
    globally-constant case has no named recognition handle.
  * This matcher is the natural strict refinement of iter 198 by the
    additional cross-pair constancy claim, matching the same cadence
    as iter 194 refining the within-pair-anchored whole-grid shift
    case (iter 194 fires only when the whole-grid shift is constant
    cross-pair; iter 185 is its k == 0 cell). The per-group projection
    of iter 194 needed two levels of constancy (within-pair across
    groups, and across pairs); iter 198 named the within-pair leg,
    this matcher names the conjunction.

Params:
  (none) -- pure global constancy check on a derived integer (the
  per-group sorted-shift), universal over groups and pairs.

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
    int in ``range(10)`` (bool rejected per iter-13 / 14 / ... / 195
    / 196 / 197 / 198 strict-type posture), AND
  - for every group, ``len(sorted(set(input_colors))) ==
    len(sorted(set(output_colors)))`` (shift defined element-wise on
    same-cardinality sorted-unique lists), AND
  - for every group, the sorted-unique output equals the sorted-
    unique input shifted element-wise by a single integer ``k_G``
    (the per-group shift is well-defined), AND
  - every group's ``k_G`` is bit-identical across every group of
    every pair (the global shift constant ``k`` is well-defined and
    shared by every group of every pair).

Why fail-closed on empty / no-group / cardinality-mismatch / shift-
undefined / malformed (same posture as iters 14 / 30 / 32 / 33 / 34 /
35 / 36 / 37 / 38 / 39 / 184-198): a missing or zero-group pair is
upstream extractor breakage or identity-territory; a per-group
cardinality mismatch makes the shift undefined for that group; a
non-shift palette permutation breaks the linear-arithmetic claim. The
matcher's name promises a global per-group shift recognition; vacuous
or ill-defined inputs cannot satisfy it.

Why strict per-colour validation (bool rejected, range checked):
``input_colors`` and ``output_colors`` carry small ints in [0, 9];
the matcher performs the same strict-type gating as iter 14 / 18 /
19 / 34 / 35 / 36 / 37 / 38 / 184-198 to keep contract violations
from silently passing.

Why ``sorted(set(...))`` rather than relying on the colour list
being already-sorted-unique: the upstream extractor emits sorted-
unique lists by construction, but matchers re-derive defensively
against a future extractor regression. Mirror of iter 191 / 194 /
198's defensive re-derivation.

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


@register("palette_shift_constant_across_groups_and_pairs")
def match(patterns: dict, params: dict) -> bool:
    if not isinstance(patterns, dict):
        return False
    pair_analyses = patterns.get("pair_analyses")
    if not isinstance(pair_analyses, list) or not pair_analyses:
        return False

    canonical_k: int | None = None

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

    return canonical_k is not None
