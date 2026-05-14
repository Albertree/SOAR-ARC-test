"""
singleton_recolor_nonidentity_output_anchored -- match tasks where every
group of every example pair has BOTH ``len(set(input_colors)) == 1``
AND ``len(set(output_colors)) == 1`` AND ``set(input_colors) !=
set(output_colors)`` AND all per-group oc singletons across all groups
in all pairs are bit-identical to one global K (cross-group identity on
the OUTPUT side) AND the per-group ic singletons C_g vary across groups
(NOT cross-group identity on the INPUT side -- ``|observed_input|
> 1``). The strict-disjoint complement of iter 220 (``singleton_recolor_
nonidentity``) at the (input-non-anchored, output-anchored) sub-cell of
iter 218 (``singleton_recolor_nonidentity_per_group``)'s territory; the
DUAL of iter 221 (``singleton_recolor_nonidentity_input_anchored``) at
the input/output role swap.

Recognition vocabulary axis: the input-per-group / output-anchored
non-identity sub-cell of iter 218. Iter 218 names the per-group
strict-recolour-on-singleton cell (every group has |ic| == |oc| == 1
AND ic != oc, with the per-group (C_g, K_g) pairs possibly varying
across groups). Within iter 218's territory the cross-group-identity
sub-axis has four cells:

  * (input-anchor, output-anchor) -- single global C and K, K != C.
    This is iter 220 (whole-task non-identity-on-singleton).
  * (input-anchor, output-per-group) -- single global C, K_g varying
    across groups. This is iter 221.
  * (input-per-group, output-anchor) -- C_g varying across groups,
    single global K. THIS matcher (whole-task output anchored, per-
    group input source). The DUAL of iter 221 at the input/output
    role swap.
  * (input-per-group, output-per-group) -- both C_g and K_g vary. The
    "vanilla" iter 218 cell with no cross-group identity claim.

The four cells partition iter 218's territory exhaustively at the
2x2 product axis (input-cross-group-identity, output-cross-group-
identity). Iter 220 names cell (T, T); iter 221 names cell (T, F);
this matcher names cell (F, T). The unnamed (F, F) cell -- candidate
(xiii) in iter 221's next-gap note -- remains the closest-fitting
smallest-step target for the next iter.

This matcher names the precondition for the rule family "whole-task
non-identity recolour with per-group input source C_g and single
global output target K": rules whose action is "paint every singleton
blob of per-group-determined input colour C_g with the global target
colour K, with C_g != K on every group AND C_g possibly varying
across groups". The output side collapses to a single global constant
K (one recognition handle); the input side is per-group (the C_g
determinable from the group's position / index / shape / palette of
the input). Iter 220 names the action-shape "C -> K with K != C
globally" (input also a single global constant); iter 221 names the
action-shape "C -> K_g with K_g != C per group AND K_g varying" (the
output side is per-group); this matcher names the action-shape "C_g
-> K with K != C_g per group AND C_g varying" (the input side is per-
group) -- a strictly different rule family at the action-shape
resolution.

Strict relations to iter 218 / iter 220 / iter 221 (the immediate
parents):

  * Iter 218 (``singleton_recolor_nonidentity_per_group``): STRICT
    REFINEMENT. This matcher fires => iter 218 fires (per-group |ic|
    == |oc| == 1 AND per-group ic != oc on every group is a
    precondition). The converse fails on any iter-218 task where the
    output side does NOT have cross-group identity (e.g., group A has
    ic = [3] / oc = [0]; group B has ic = [5] / oc = [7]): iter 218
    fires, this matcher rejects on the output-side cross-group
    identity failure.
  * Iter 220 (``singleton_recolor_nonidentity``): STRICT MUTUAL
    EXCLUSION. Iter 220 demands cross-group identity on BOTH sides
    (single global C AND single global K, with C != K); this matcher
    demands cross-group identity on the OUTPUT side AND NON-identity
    on the INPUT side (|observed_input| > 1). The two cells are
    pairwise disjoint by the (input-anchor) vs (input-per-group)
    split on the output-anchored row of iter 218.
  * Iter 221 (``singleton_recolor_nonidentity_input_anchored``):
    STRICT MUTUAL EXCLUSION. Iter 221 demands cross-group identity on
    the INPUT side AND non-identity on the OUTPUT side. This matcher
    demands the dual: cross-group identity on the OUTPUT side AND
    non-identity on the INPUT side. The two cells are pairwise
    disjoint by the (input-anchored, output-per-group) vs (input-
    per-group, output-anchored) split on iter 218's "exactly-one-
    side-anchored" row of the 2x2 cross-group-identity product axis.

So this matcher is the strict-disjoint complement of iter 220 within
iter 218's output-anchored sub-row AND the strict-disjoint dual of
iter 221 within iter 218's "exactly-one-side-anchored" row. The
(T, T), (T, F), (F, T) cells of the (input-cross-group-identity,
output-cross-group-identity) 2x2 product axis on iter 218 are now
named at disjoint recognition handles (iter 220 / iter 221 / this
matcher). Only the (F, F) cell remains unnamed.

Strict relations to iter 217 / iter 219:

  * Iter 217 (``singleton_recolor_identity_per_group``): STRICT MUTUAL
    EXCLUSION. Iter 217 demands per-group ic == oc on every group;
    this matcher demands per-group ic != oc on every group. The two
    are pairwise disjoint by the per-group ic == oc vs ic != oc split.
  * Iter 219 (``singleton_recolor_identity``): STRICT MUTUAL
    EXCLUSION. Iter 219 demands single global C == K (no per-group
    variation, identity-on-singleton); this matcher demands per-group
    ic != oc with C_g varying. The two are pairwise disjoint by the
    (C == K, input-anchored) vs (ic != oc, input-per-group) split.

Strict relations to iter 215 / iter 216:

  * Iter 215 (``singleton_recolor_per_group``): STRICT REFINEMENT.
    Per-group |ic| == |oc| == 1 is a precondition; this matcher
    additionally requires per-group ic != oc AND output-side cross-
    group identity AND input-side cross-group identity failure.
  * Iter 216 (``singleton_recolor``): STRICT MUTUAL EXCLUSION. Iter
    216 demands cross-group identity on BOTH sides; this matcher
    demands cross-group identity on the OUTPUT side AND NOT on the
    INPUT side. The two cells are disjoint by the input-side
    cross-group identity claim.

Strict relations to iter 14 (``input_color_uniform``) AND iter 18
(``output_color_uniform``):

  * Iter 14 (``input_color_uniform``): STRICT MUTUAL EXCLUSION. Iter
    14 demands cross-group / cross-pair input uniformity (all ic
    singletons bit-identical to one global C); this matcher demands
    |observed_input_colors| > 1. The two are pairwise disjoint by
    the input-side single-C vs multi-C split.
  * Iter 18 (``output_color_uniform``): STRICT REFINEMENT. Iter 18
    fires iff per-pair every group has |oc| == 1 AND all oc
    singletons cross-group / cross-pair bit-identical to one global
    K. This matcher additionally requires per-group |ic| == 1 AND
    per-group ic != oc AND input-side cross-group identity failure.
    Iter 18 fires => this matcher may or may not fire (iter 18 admits
    |ic| > 1 cells, or |ic| == 1 with C_g uniform = iter 220 cell, or
    |ic| == 1 with C_g == K_g per group = degenerate identity case).

Strict relation to iter 8 (``consistent_color_mapping``): STRICT
MUTUAL EXCLUSION on this matcher's distinctive territory. Iter 8
demands a function-shaped global mapping (every input colour maps to
a single output colour). When this matcher fires alone (multiple
C_g's all map to the same K within a pair), the per-pair (ic, oc)
cross-product contains {(C_g, K) : g in groups} with at least two
distinct C_g's. That is function-shaped from the input side (each
C_g maps to the single K), so iter 8 may co-fire on this matcher's
territory. Specifically: iter 8 demands a *function* shape (one input
to one output); the multi-C_g, single-K shape IS function-shaped on
each input C_g. So iter 8 co-fires with this matcher on its
distinctive territory (the dual of iter 221's relation to iter 8,
where iter 221's territory has one input C mapping to multiple K_g's,
which is NOT function-shaped). On the iter-220 sub-cell, iter 8 also
fires. So iter 8 is STRICTLY IMPLIED by this matcher, not mutually
exclusive.

Strict relation to iter 13 (``identity_transformation``): STRICT
MUTUAL EXCLUSION. Iter 13 fires iff every pair has ZERO change
groups (whole-task no-blob identity). This matcher REJECTS the no-
group case (universal-over-groups requires at least one group per
pair; additionally the cross-group identity claim has no witnesses
on an empty group list). Iter 13 occupies the (#groups == 0) cell;
this matcher requires #groups >= 1 with at least two distinct C_g
values witnessed (so effectively #groups >= 2 in at least one pair).

Strict relation to iter 213 (``consistent_color_mapping_per_group``)
AND iter 214 (``input_color_uniform_per_group``): both are STRICTLY
IMPLIED by this matcher. Iter 213 demands per-group |oc| == 1; this
matcher demands per-group |oc| == 1, so iter 213 fires. Iter 214
demands per-group |ic| == 1; this matcher demands per-group |ic| ==
1, so iter 214 fires. The converse of each fails (each is satisfied
by larger cells than this matcher's territory).

Strict relation to iter 201 (``output_colors_equals_input_colors_
per_group``): STRICT MUTUAL EXCLUSION. Iter 201 demands per-group
set(ic) == set(oc). This matcher pins per-group ic == [C_g] / oc ==
[K] with C_g != K globally, forcing per-group set(ic) != set(oc).

Strict relation to iter 203 (``output_colors_disjoint_from_input_
colors_per_group``): STRICTLY IMPLIED. Iter 203 demands per-group
set(ic) intersect set(oc) == empty. On the singleton row with ic !=
oc, the two 1-element sets are always disjoint, so iter 203 fires
whenever this matcher does. The converse fails on multi-element
disjoint cells.

Strict relation to iter 195 / 196 / 197 (per-group cardinality
matchers): this matcher implies iter 195 at K_in == 1 (input
cardinality) AND iter 196 at K_out == 1 (output cardinality) AND
iter 197 at K_prod == 1 (product). Cross-pair constancy at K == 1
is subsumed by universal-over-pairs semantics here. The converse
for each fails at K != 1.

Strict relation to iter 198 / 199 (per-group palette-shift
constancy): within-pair / global constant shift k = oc - ic at the
|ic| == |oc| cell. This matcher implies per-group shift k_g = K -
C_g, with K globally fixed but C_g varying. So per-group shifts vary
across groups (k_g != k_h for some g, h since C_g != C_h). Iter 198
demands per-pair k constant (all groups in one pair share k); iter
199 strict-refines iter 198 with cross-pair k constancy. With this
matcher firing AND C_g varying within a pair, iter 198 REJECTS;
hence iter 198 / 199 are STRICTLY MUTUALLY EXCLUSIVE with this
matcher on the within-pair C-variation territory. If C_g is constant
within each pair but varies across pairs, iter 198 fires per-pair
but iter 199 rejects; in that case this matcher fires AND iter 198
co-fires AND iter 199 rejects. So iter 199 is always STRICTLY
MUTUALLY EXCLUSIVE with this matcher; iter 198 is INDEPENDENT in
general (co-fires only on the within-pair-constant-C, cross-pair-
varying-C cell).

Strict relation to iter 10 (``sequential_recoloring``): per-group
|oc| == 1 with the per-pair oc singletons forming a contiguous
range. When this matcher fires, all per-pair oc singletons are bit-
identical to the global K (a single colour, not a multi-element
range), so iter 10 REJECTS this matcher's distinctive territory
(iter 10 requires |distinct outputs in pair| >= 2 to form a non-
trivial range). The two are STRICTLY MUTUALLY EXCLUSIVE on multi-
group pairs.

Why a distinct matcher rather than just AND-ing iter 218 with iter
18 at the rule level: the matcher contract (docs/RULE_FORMAT.md §4)
is name-keyed recognition vocabulary; the rule's stored ``condition.
type`` is the recognition handle's name, not a Boolean composition
tree. A rule whose precondition is "per-group |ic| == |oc| == 1 AND
per-group ic != oc AND output-side cross-group identity AND input-
side cross-group identity failure" gates a DIFFERENT rule family
(input-per-group / output-anchored strict recolour, where the
input source C_g depends on per-group features beyond the global
output anchor K) than iter 218 alone (per-group strict recolour
admitting both output-anchored and output-per-group cells) or iter
18 alone (whole-task output uniformity admitting any input shape).
Keeping the conjunction as a separate registry slot lets anti-
unification (CLAUDE.md §8) attach the right gate per rule family --
specifically the gate for rules whose action is "C_g -> K with K !=
C_g per group AND C_g varying across groups" -- without
rediscovering the input-per-group / output-anchor structure from
the rule's stored action shape.

Why a distinct matcher rather than parameterising iter 218 with an
``input_anchored: False, output_anchored: True`` flag: the matcher
contract is name-keyed recognition vocabulary; the rule's stored
``condition.type`` is the recognition handle's name, not a name+
params tuple. The (input-per-group, output-anchored) sub-cell of
iter 218 is structurally identifiable as the strict-disjoint
complement of iter 220 within iter 218's output-anchored row AND
the strict-disjoint dual of iter 221 within iter 218's "exactly-one-
side-anchored" row; it is a recognition handle in its own right
(the simplest input-per-group / output-anchored strict-recolour
cell), not a Boolean parameter of the per-group strict-recolour
axis.

Why this matters as the whole-task projection of iter 218 at the
output-anchored cell: with iter 220 naming the (input-anchor, output-
anchor) cell of iter 218, iter 221 naming the (input-anchor, output-
per-group) cell, and this matcher naming the (input-per-group,
output-anchor) cell, three of the four cells of the (input-cross-
group-identity, output-cross-group-identity) 2x2 product axis on
iter 218's territory are named at disjoint recognition handles. Only
the (F, F) "neither anchored" cell -- the vanilla iter 218 cell with
no cross-group identity claim -- remains unnamed as candidate
(xiii) for the next iter.

Strict refinement / orthogonality summary (universal-over-groups-
and-pairs semantics, per-group |ic| == |oc| == 1 AND ic != oc AND
output-side cross-group identity AND input-side cross-group identity
failure):

  * Iter 218 (``singleton_recolor_nonidentity_per_group``) -- STRICT
    REFINEMENT (this matcher additionally requires output-side
    cross-group identity AND input-side cross-group identity
    failure).
  * Iter 220 (``singleton_recolor_nonidentity``) -- STRICT MUTUAL
    EXCLUSION (iter 220 demands input-side cross-group identity;
    this matcher demands its failure). The two cells partition iter
    218's output-anchored row exhaustively into (input-anchored) and
    (input-per-group).
  * Iter 221 (``singleton_recolor_nonidentity_input_anchored``) --
    STRICT MUTUAL EXCLUSION (the dual: iter 221 names the (input-
    anchored, output-per-group) cell; this matcher names the
    (input-per-group, output-anchored) cell).
  * Iter 219 (``singleton_recolor_identity``) -- STRICT MUTUAL
    EXCLUSION (iter 219 demands C == K; this matcher demands per-
    group ic != oc).
  * Iter 217 (``singleton_recolor_identity_per_group``) -- STRICT
    MUTUAL EXCLUSION (iter 217 demands per-group ic == oc; this
    matcher demands per-group ic != oc).
  * Iter 216 (``singleton_recolor``) -- STRICT MUTUAL EXCLUSION
    (iter 216 demands cross-group identity on BOTH sides; this
    matcher demands NON-identity on the input side).
  * Iter 215 (``singleton_recolor_per_group``) -- STRICT REFINEMENT
    (per-group |ic| == |oc| == 1 is a precondition; cross-group
    identity on the output side AND per-group ic != oc AND input-
    side cross-group identity failure additionally required).
  * Iter 14 (``input_color_uniform``) -- STRICT MUTUAL EXCLUSION
    (iter 14 demands cross-group input uniformity; this matcher
    demands |observed_input| > 1).
  * Iter 18 (``output_color_uniform``) -- STRICT REFINEMENT (this
    matcher additionally requires per-group |ic| == 1 AND per-group
    ic != oc AND |observed_input| > 1).
  * Iter 213 / iter 214 -- STRICTLY IMPLIED.
  * Iter 8 (``consistent_color_mapping``) -- STRICTLY IMPLIED. When
    this matcher fires, multiple distinct C_g's each map to the
    single global K. That IS function-shaped (one input maps to
    exactly one output), so iter 8 fires. The dual of iter 221's
    relation to iter 8 (where iter 221's territory has one C mapping
    to multiple K_g's, violating function shape).
  * Iter 13 (``identity_transformation``) -- STRICT MUTUAL EXCLUSION
    (iter 13 occupies the #groups == 0 cell; this matcher requires
    at least two distinct C_g values witnessed).
  * Iter 10 (``sequential_recoloring``) -- STRICT MUTUAL EXCLUSION
    on multi-group pairs (iter 10 needs non-trivial output range;
    this matcher pins all outputs to single K).
  * Iter 195 / 196 / 197 (per-group cardinality matchers) --
    STRICTLY IMPLIED at K_in == K_out == K_prod == 1.
  * Iter 198 (within-pair palette-shift constancy) -- INDEPENDENT in
    general; co-fires only on the within-pair-constant-C, cross-pair-
    varying-C cell. Iter 199 (cross-pair palette-shift constancy) --
    STRICTLY MUTUALLY EXCLUSIVE (cross-pair C constancy at the
    singleton row reduces to global C constancy, iter 220's cell).
  * Iter 201 (``output_colors_equals_input_colors_per_group``) --
    STRICT MUTUAL EXCLUSION (this matcher forces per-group ic !=
    oc).
  * Iter 203 (``output_colors_disjoint_from_input_colors_per_group``)
    -- STRICTLY IMPLIED (on the singleton row, ic != oc forces ic
    intersect oc == empty).
  * Iter 200 / 202 / 204 / 205 / 206 (per-group palette-relation
    cells) -- STRICTLY MUTUALLY EXCLUSIVE with this matcher on the
    |ic| == |oc| == 1 row.
  * Every cell- / position- / dimension-axis matcher -- orthogonal
    to per-group singleton input-per-group / output-anchored strict-
    recolour.

Why this matters for ARBOR's intended ruleset:

  * "Input-per-group / output-anchored strict-recolour" rule family
    -- rules whose action is "paint every singleton blob of per-
    group-determined input colour C_g with the global target colour
    K, with C_g != K on every group AND C_g possibly varying across
    groups". The simplest non-trivial whole-task recolour shape that
    requires PER-GROUP input state with a globally-anchored output
    (rivalling iter 221's dual cell where output is per-group with
    globally-anchored input); the building block from which more
    complex input-per-group / output-anchored rules (e.g., "the C_g
    depends on the group's position / index / shape / palette of
    the input") generalise. This matcher names the precondition for
    that rule family, in a single registry slot, so anti-unification
    can attach the right gate to rules of this shape without having
    to rediscover the iter 218 ^ output-anchor ^ input-non-anchor
    intersection each time.
  * Closes the iter-221-named candidate (xii): "the dual companion
    -- the (output-anchored, input-per-group) cell, a single matcher
    pinning |ic| == |oc| == 1 AND per-group ic != oc AND cross-group
    identity on the OUTPUT side only (single global K across all
    groups, with C_g varying across groups)". With this matcher
    landed, three of the four cells of iter 218's 2x2 cross-group-
    identity axis are named (iter 220 / iter 221 / this matcher).
    Only the (F, F) "neither anchored" cell remains as candidate
    (xiii) for the next iter.

Params:
  (none) -- pure per-group input-per-group / output-anchored
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
    200-206 / 213 / 214 / 215 / 217 / 218 / 219 / 220 / 221
    strict-type posture), AND
  - for every group, ``len(set(input_colors)) == 1`` AND
    ``len(set(output_colors)) == 1`` AND
    ``set(input_colors) != set(output_colors)``, AND
  - all per-group oc singletons across all groups in all pairs are
    bit-identical to one global K (cross-group identity on the
    OUTPUT side), AND
  - the per-group ic singletons C_g vary across groups OR pairs --
    i.e. ``len(observed_input_colors) > 1`` (NOT cross-group
    identity on the INPUT side, the strict-disjoint complement of
    iter 220 within iter 218's output-anchored sub-row AND the
    strict-disjoint dual of iter 221).

Why fail-closed on empty / no-group / malformed (same posture as
iter 8 / 13 / 14 / 18 / 30 / 32 / 33 / 34 / 35 / 36 / 37 / 38 / 39 /
184-221): a missing or zero-group pair is upstream extractor
breakage or iter 13's no-blob-identity territory; a whole-task
input-per-group / output-anchored strict-recolour claim with zero
observations is meaningless, AND admitting it would collapse this
matcher's territory into iter 13's (the two are designed as disjoint
cells on the (#groups, recolour-shape) axis).

Why strict per-colour validation (bool rejected, range checked):
``input_colors`` / ``output_colors`` carry small ints in [0, 9];
the matcher performs the same strict-type gating as iter 14 / 18 /
19 / 34 / 35 / 36 / 37 / 38 / 184-221 to keep contract violations
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


@register("singleton_recolor_nonidentity_output_anchored")
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
            if len(observed_output_colors) > 1:
                return False
    return (
        len(observed_output_colors) == 1
        and len(observed_input_colors) > 1
    )
