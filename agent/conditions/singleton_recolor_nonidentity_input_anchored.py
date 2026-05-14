"""
singleton_recolor_nonidentity_input_anchored -- match tasks where every
group of every example pair has BOTH ``len(set(input_colors)) == 1``
AND ``len(set(output_colors)) == 1`` AND ``set(input_colors) !=
set(output_colors)`` AND all per-group ic singletons across all groups
in all pairs are bit-identical to one global C (cross-group identity on
the INPUT side) AND the per-group oc singletons K_g vary across groups
(NOT cross-group identity on the OUTPUT side -- ``|observed_output|
> 1``). The strict-disjoint complement of iter 220 (``singleton_recolor_
nonidentity``) at the (input-anchored, output-non-anchored) sub-cell of
iter 218 (``singleton_recolor_nonidentity_per_group``)'s territory.

Recognition vocabulary axis: the input-anchored / output-per-group
non-identity sub-cell of iter 218. Iter 218 names the per-group
strict-recolour-on-singleton cell (every group has |ic| == |oc| == 1
AND ic != oc, with the per-group (C_g, K_g) pairs possibly varying
across groups). Within iter 218's territory the cross-group-identity
sub-axis has four cells:

  * (input-anchor, output-anchor) -- single global C and K, K != C.
    This is iter 220 (whole-task non-identity-on-singleton).
  * (input-anchor, output-per-group) -- single global C, K_g varying
    across groups. THIS matcher (whole-task input anchored, per-group
    output target).
  * (input-per-group, output-anchor) -- C_g varying across groups,
    single global K. The dual companion (candidate (xii) in iter 220's
    next-gap note).
  * (input-per-group, output-per-group) -- both C_g and K_g vary. The
    "vanilla" iter 218 cell with no cross-group identity claim.

The four cells partition iter 218's territory exhaustively at the
2x2 product axis (input-cross-group-identity, output-cross-group-
identity). Iter 220 names cell (T, T); this matcher names cell (T, F).

This matcher names the precondition for the rule family "whole-task
non-identity recolour with single global INPUT source C and per-group
output target K_g": rules whose action is "paint every singleton blob
of input colour C with a per-group-determined target colour K_g, with
K_g != C on every group AND K_g possibly varying across groups". The
input side collapses to a single global constant C (one recognition
handle); the output side is per-group (the K_g determinable from the
group's position / index / shape / palette of the input). Iter 220
names the action-shape "C -> K with K != C globally" (output also a
single global constant); this matcher names the action-shape "C ->
K_g with K_g != C per group AND K_g varying" -- a strictly different
rule family at the action-shape resolution.

Strict relations to iter 218 / iter 220 (the immediate parents):

  * Iter 218 (``singleton_recolor_nonidentity_per_group``): STRICT
    REFINEMENT. This matcher fires => iter 218 fires (per-group |ic|
    == |oc| == 1 AND per-group ic != oc on every group is a
    precondition). The converse fails on any iter-218 task where the
    input side does NOT have cross-group identity (e.g., group A has
    ic = [3] / oc = [0]; group B has ic = [5] / oc = [7]): iter 218
    fires, this matcher rejects on the input-side cross-group identity
    failure.
  * Iter 220 (``singleton_recolor_nonidentity``): STRICT MUTUAL
    EXCLUSION. Iter 220 demands cross-group identity on BOTH sides
    (single global C AND single global K, with C != K); this matcher
    demands cross-group identity on the INPUT side AND NON-identity on
    the OUTPUT side (|observed_output| > 1). The two cells are
    pairwise disjoint by the (output-anchor) vs (output-per-group)
    split on the input-anchored row of iter 218. Within iter 218's
    territory they partition the input-anchored row exhaustively into
    iter 220 (output also anchored) and this matcher (output not
    anchored).

So this matcher is the strict-disjoint complement of iter 220 within
iter 218's input-anchored sub-row. The (T, T) and (T, F) cells of the
(input-cross-group-identity, output-cross-group-identity) 2x2 product
axis on iter 218 are now named at disjoint recognition handles.

Strict relations to iter 217 / iter 219:

  * Iter 217 (``singleton_recolor_identity_per_group``): STRICT MUTUAL
    EXCLUSION. Iter 217 demands per-group ic == oc on every group;
    this matcher demands per-group ic != oc on every group. The two
    are pairwise disjoint by the per-group ic == oc vs ic != oc split.
  * Iter 219 (``singleton_recolor_identity``): STRICT MUTUAL
    EXCLUSION. Iter 219 demands single global C == K (no per-group
    variation, identity-on-singleton); this matcher demands per-group
    ic != oc with K_g varying. The two are pairwise disjoint by the
    (C == K, output-anchored) vs (ic != oc, output-per-group) split.

Strict relations to iter 215 / iter 216:

  * Iter 215 (``singleton_recolor_per_group``): STRICT REFINEMENT.
    Per-group |ic| == |oc| == 1 is a precondition; this matcher
    additionally requires per-group ic != oc AND input-side cross-
    group identity AND output-side cross-group identity failure.
  * Iter 216 (``singleton_recolor``): STRICT MUTUAL EXCLUSION. Iter
    216 demands cross-group identity on BOTH sides; this matcher
    demands cross-group identity on the INPUT side AND NOT on the
    OUTPUT side. The two cells are disjoint by the output-side
    cross-group identity claim.

Strict relations to iter 14 (``input_color_uniform``) AND iter 18
(``output_color_uniform``):

  * Iter 14 (``input_color_uniform``): STRICT REFINEMENT. Iter 14
    fires iff per-pair every group has |ic| == 1 AND all ic
    singletons cross-group / cross-pair bit-identical to one global
    C. This matcher additionally requires per-group |oc| == 1 AND
    per-group ic != oc AND output-side cross-group identity failure.
    Iter 14 fires => this matcher may or may not fire (iter 14 admits
    |oc| > 1 cells, or |oc| == 1 with K_g uniform = iter 220 cell, or
    |oc| == 1 with C_g == K_g per group = degenerate identity case).
  * Iter 18 (``output_color_uniform``): STRICT MUTUAL EXCLUSION. Iter
    18 demands cross-group / cross-pair output uniformity (all oc
    singletons bit-identical to one global K); this matcher demands
    |observed_output_colors| > 1. The two are pairwise disjoint by
    the output-side single-K vs multi-K split.

Strict relation to iter 8 (``consistent_color_mapping``): STRICT
MUTUAL EXCLUSION on this matcher's distinctive territory. Iter 8
demands a function-shaped global mapping (every input colour maps to
a single output colour). When this matcher fires alone (C maps to
K_g varying across groups in the same pair), the per-pair (ic, oc)
cross-product contains {(C, K_g) : g in groups} with at least two
distinct K_g's, violating function-shape on input C. So iter 8
REJECTS this matcher's distinctive territory. The two cells co-fire
only on the iter-220 sub-cell (output also anchored => function-
shaped {C -> K}), which this matcher REJECTS by the disjoint cell
definition. Hence iter 8 and this matcher are STRICTLY MUTUALLY
EXCLUSIVE.

Strict relation to iter 13 (``identity_transformation``): STRICT
MUTUAL EXCLUSION. Iter 13 fires iff every pair has ZERO change
groups (whole-task no-blob identity). This matcher REJECTS the no-
group case (universal-over-groups requires at least one group per
pair; additionally the cross-group identity claim has no witnesses
on an empty group list). Iter 13 occupies the (#groups == 0) cell;
this matcher requires #groups >= 1 with at least two distinct K_g's
witnessed (so effectively #groups >= 2 in at least one pair).

Strict relation to iter 213 (``consistent_color_mapping_per_group``)
AND iter 214 (``input_color_uniform_per_group``): both are STRICTLY
IMPLIED by this matcher. Iter 213 demands per-group |oc| == 1; this
matcher demands per-group |oc| == 1, so iter 213 fires. Iter 214
demands per-group |ic| == 1; this matcher demands per-group |ic| ==
1, so iter 214 fires. The converse of each fails (each is satisfied
by larger cells than this matcher's territory).

Strict relation to iter 201 (``output_colors_equals_input_colors_
per_group``): STRICT MUTUAL EXCLUSION. Iter 201 demands per-group
set(ic) == set(oc). This matcher pins per-group ic == [C] / oc ==
[K_g] with K_g != C globally, forcing per-group set(ic) != set(oc).

Strict relation to iter 203 (``output_colors_disjoint_from_input_
colors_per_group``): STRICTLY IMPLIED. Iter 203 demands per-group
set(ic) ∩ set(oc) == ∅. On the singleton row with ic != oc, the
two 1-element sets are always disjoint, so iter 203 fires whenever
this matcher does. The converse fails on multi-element disjoint
cells.

Strict relation to iter 195 / 196 / 197 (per-group cardinality
matchers): this matcher implies iter 195 at K_in == 1 (input
cardinality) AND iter 196 at K_out == 1 (output cardinality) AND
iter 197 at K_prod == 1 (product). Cross-pair constancy at K == 1
is subsumed by universal-over-pairs semantics here. The converse
for each fails at K != 1.

Strict relation to iter 198 / 199 (per-group palette-shift
constancy): within-pair / global constant shift k = oc - ic at the
|ic| == |oc| cell. This matcher implies per-group shift k_g = K_g -
C, with C globally fixed but K_g varying. So per-group shifts vary
across groups (k_g != k_h for some g, h since K_g != K_h). Iter 198
demands per-pair k constant (all groups in one pair share k); iter
199 strict-refines iter 198 with cross-pair k constancy. With this
matcher firing AND K_g varying within a pair, iter 198 REJECTS;
hence iter 198 / 199 are STRICTLY MUTUALLY EXCLUSIVE with this
matcher on the within-pair K-variation territory. If K_g is constant
within each pair but varies across pairs, iter 198 fires per-pair
but iter 199 rejects; in that case this matcher fires AND iter 198
co-fires AND iter 199 rejects. So iter 199 is always STRICTLY
MUTUALLY EXCLUSIVE with this matcher; iter 198 is INDEPENDENT in
general (co-fires only on the within-pair-constant-K, cross-pair-
varying-K cell).

Strict relation to iter 10 (``sequential_recoloring``): per-group
|oc| == 1 with the per-pair oc singletons forming a contiguous
range. INDEPENDENT in general of this matcher: co-fires on tasks
where K_g forms a contiguous range within each pair (e.g. ic == [3]
/ oc == [0], [1], [2] forming the range [0, 1, 2]); decouples when
K_g varies non-contiguously.

Why a distinct matcher rather than just AND-ing iter 218 with iter
14 at the rule level: the matcher contract (docs/RULE_FORMAT.md §4)
is name-keyed recognition vocabulary; the rule's stored ``condition.
type`` is the recognition handle's name, not a Boolean composition
tree. A rule whose precondition is "per-group |ic| == |oc| == 1 AND
per-group ic != oc AND input-side cross-group identity AND output-
side cross-group identity failure" gates a DIFFERENT rule family
(input-anchored / per-group-output strict recolour, where the
output target K_g depends on per-group features beyond the global
input anchor C) than iter 218 alone (per-group strict recolour
admitting both input-anchored and input-per-group cells) or iter
14 alone (whole-task input uniformity admitting any output shape).
Keeping the conjunction as a separate registry slot lets anti-
unification (CLAUDE.md §8) attach the right gate per rule family --
specifically the gate for rules whose action is "C -> K_g with
K_g != C per group AND K_g varying across groups" -- without
rediscovering the input-anchor / output-per-group structure from
the rule's stored action shape.

Why a distinct matcher rather than parameterising iter 218 with an
``input_anchored: True, output_anchored: False`` flag: the matcher
contract is name-keyed recognition vocabulary; the rule's stored
``condition.type`` is the recognition handle's name, not a name+
params tuple. The (input-anchored, output-per-group) sub-cell of
iter 218 is structurally identifiable as the strict-disjoint
complement of iter 220 within iter 218's input-anchored row; it is
a recognition handle in its own right (the simplest input-anchored
/ output-per-group strict-recolour cell), not a Boolean parameter
of the per-group strict-recolour axis.

Why this matters as the whole-task projection of iter 218 at the
input-anchored cell: with iter 220 naming the (input-anchor, output-
anchor) cell of iter 218, and this matcher naming the (input-anchor,
output-per-group) cell, the input-anchored row of iter 218 closes at
two disjoint recognition handles. The four-cell product axis
(input-cross-group-identity, output-cross-group-identity) on iter
218's territory is now half-named: iter 220 fills the (T, T) cell
AND this matcher fills the (T, F) cell. The companion candidate
(xii) -- the (F, T) cell, output-anchored / input-per-group -- and
the unnamed (F, F) cell (neither anchored, "vanilla" iter 218)
remain available as next-iter targets.

Strict refinement / orthogonality summary (universal-over-groups-
and-pairs semantics, per-group |ic| == |oc| == 1 AND ic != oc AND
input-side cross-group identity AND |observed_output| > 1):

  * Iter 218 (``singleton_recolor_nonidentity_per_group``) -- STRICT
    REFINEMENT (this matcher additionally requires input-side
    cross-group identity AND output-side cross-group identity
    failure).
  * Iter 220 (``singleton_recolor_nonidentity``) -- STRICT MUTUAL
    EXCLUSION (iter 220 demands output-side cross-group identity;
    this matcher demands its failure). The two cells partition iter
    218's input-anchored row exhaustively into (output-anchored) and
    (output-per-group).
  * Iter 219 (``singleton_recolor_identity``) -- STRICT MUTUAL
    EXCLUSION (iter 219 demands C == K; this matcher demands per-
    group ic != oc).
  * Iter 217 (``singleton_recolor_identity_per_group``) -- STRICT
    MUTUAL EXCLUSION (iter 217 demands per-group ic == oc; this
    matcher demands per-group ic != oc).
  * Iter 216 (``singleton_recolor``) -- STRICT MUTUAL EXCLUSION
    (iter 216 demands cross-group identity on BOTH sides; this
    matcher demands NON-identity on the output side).
  * Iter 215 (``singleton_recolor_per_group``) -- STRICT REFINEMENT
    (per-group |ic| == |oc| == 1 is a precondition; cross-group
    identity on the input side AND per-group ic != oc AND output-
    side cross-group identity failure additionally required).
  * Iter 14 (``input_color_uniform``) -- STRICT REFINEMENT (this
    matcher additionally requires per-group |oc| == 1 AND per-group
    ic != oc AND |observed_output| > 1).
  * Iter 18 (``output_color_uniform``) -- STRICT MUTUAL EXCLUSION
    (iter 18 demands cross-group output uniformity; this matcher
    demands |observed_output| > 1).
  * Iter 213 / iter 214 -- STRICTLY IMPLIED.
  * Iter 8 (``consistent_color_mapping``) -- STRICT MUTUAL EXCLUSION.
    When this matcher fires, C maps to multiple distinct K_g values
    within at least one pair (since output-side cross-group identity
    fails). Iter 8 demands a function-shaped mapping, which this
    matcher's "C -> K_g with K_g varying" violates.
  * Iter 13 (``identity_transformation``) -- STRICT MUTUAL EXCLUSION
    (iter 13 occupies the #groups == 0 cell; this matcher requires
    at least two distinct K_g values witnessed).
  * Iter 10 (``sequential_recoloring``) -- INDEPENDENT in general;
    co-fires only when K_g forms a contiguous range within each
    pair.
  * Iter 195 / 196 / 197 (per-group cardinality matchers) --
    STRICTLY IMPLIED at K == K == K_prod == 1.
  * Iter 198 (within-pair palette-shift constancy) -- INDEPENDENT in
    general; co-fires only on the within-pair-constant-K, cross-pair-
    varying-K cell. Iter 199 (cross-pair palette-shift constancy) --
    STRICTLY MUTUALLY EXCLUSIVE (cross-pair K constancy at the
    singleton row reduces to global K constancy, iter 220's cell).
  * Iter 201 (``output_colors_equals_input_colors_per_group``) --
    STRICT MUTUAL EXCLUSION (this matcher forces per-group ic !=
    oc).
  * Iter 203 (``output_colors_disjoint_from_input_colors_per_group``)
    -- STRICTLY IMPLIED (on the singleton row, ic != oc forces ic ∩
    oc == ∅).
  * Iter 200 / 202 / 204 / 205 / 206 (per-group palette-relation
    cells) -- STRICTLY MUTUALLY EXCLUSIVE with this matcher on the
    |ic| == |oc| == 1 row.
  * Every cell- / position- / dimension-axis matcher -- orthogonal
    to per-group singleton input-anchored / output-per-group strict-
    recolour.

Why this matters for ARBOR's intended ruleset:

  * "Input-anchored / output-per-group strict-recolour" rule family
    -- rules whose action is "paint every singleton blob of input
    colour C with a per-group-determined target colour K_g, with
    K_g != C on every group AND K_g possibly varying across groups".
    The simplest non-trivial whole-task recolour shape that requires
    PER-GROUP output state (rivalling iter 220's whole-task single-
    constant output at the dual cell); the building block from
    which more complex input-anchored / output-per-group rules
    (e.g., "the K_g depends on the group's position / index / shape
    / palette of the input") generalise. This matcher names the
    precondition for that rule family, in a single registry slot,
    so anti-unification can attach the right gate to rules of this
    shape without having to rediscover the iter 218 ∧ input-anchor
    ∧ output-non-anchor intersection each time.
  * Closes the iter-220-named candidate (xi): "the whole-task
    projection of iter 218 at the CROSS-GROUP-IDENTITY-ON-INPUT-
    SIDE-ONLY cell -- a single matcher pinning |ic| == |oc| == 1
    AND cross-group identity on the INPUT side only AND per-group
    ic != oc". With this matcher landed, the input-anchored row of
    iter 218's four-cell axis (input-cross-group-identity, output-
    cross-group-identity) is named at two disjoint sub-cells: iter
    220 (both anchored) AND this matcher (input anchored, output
    per-group). The companion candidate (xii) (output anchored,
    input per-group) and the unnamed (F, F) cell remain.

Params:
  (none) -- pure per-group input-anchored / output-per-group
  singleton-strict-recolour check, universal over groups and pairs.

Returns True iff:
  - ``patterns`` is a dict, AND
  - ``patterns["pair_analyses"]`` is a non-empty list, AND
  - every analysis is a dict, AND
  - every analysis has a non-empty ``groups`` list (identity-
    territory rejection), AND
  - every group is a dict with list-typed ``input_colors`` and
    ``output_colors`` fields of length >= 1, AND
  - every entry of ``input_colors`` and ``output_colors`` is a
    strict int in ``range(10)`` (bool rejected per iter-14 / 18 /
    200-206 / 213 / 214 / 215 / 217 / 218 / 219 / 220 strict-type
    posture), AND
  - for every group, ``len(set(input_colors)) == 1`` AND
    ``len(set(output_colors)) == 1`` AND
    ``set(input_colors) != set(output_colors)``, AND
  - all per-group ic singletons across all groups in all pairs are
    bit-identical to one global C (cross-group identity on the
    INPUT side), AND
  - the per-group oc singletons K_g vary across groups OR pairs --
    i.e. ``len(observed_output_colors) > 1`` (NOT cross-group
    identity on the OUTPUT side, the strict-disjoint complement of
    iter 220 within iter 218's input-anchored sub-row).

Why fail-closed on empty / no-group / malformed (same posture as
iter 8 / 13 / 14 / 18 / 30 / 32 / 33 / 34 / 35 / 36 / 37 / 38 / 39 /
184-220): a missing or zero-group pair is upstream extractor
breakage or iter 13's no-blob-identity territory; a whole-task
input-anchored / output-per-group strict-recolour claim with zero
observations is meaningless, AND admitting it would collapse this
matcher's territory into iter 13's (the two are designed as disjoint
cells on the (#groups, recolour-shape) axis).

Why strict per-colour validation (bool rejected, range checked):
``input_colors`` / ``output_colors`` carry small ints in [0, 9];
the matcher performs the same strict-type gating as iter 14 / 18 /
19 / 34 / 35 / 36 / 37 / 38 / 184-220 to keep contract violations
from silently passing.

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
    if not isinstance(x, list) or len(x) < 1:
        return False
    for v in x:
        if not _is_strict_color(v):
            return False
    return True


@register("singleton_recolor_nonidentity_input_anchored")
def match(patterns: dict, params: dict) -> bool:
    if not isinstance(patterns, dict):
        return False
    pair_analyses = patterns.get("pair_analyses")
    if not isinstance(pair_analyses, list) or not pair_analyses:
        return False

    observed_input_colors: set = set()
    observed_output_colors: set = set()
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
            ic_set = set(input_colors)
            oc_set = set(output_colors)
            if len(ic_set) != 1:
                return False
            if len(oc_set) != 1:
                return False
            if ic_set == oc_set:
                return False
            observed_input_colors |= ic_set
            observed_output_colors |= oc_set
            if len(observed_input_colors) > 1:
                return False
    return (
        len(observed_input_colors) == 1
        and len(observed_output_colors) > 1
    )
