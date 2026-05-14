"""
singleton_recolor_nonidentity_unanchored -- match tasks where every
group of every example pair has BOTH ``len(set(input_colors)) == 1``
AND ``len(set(output_colors)) == 1`` AND ``set(input_colors) !=
set(output_colors)`` AND the per-group ic singletons C_g vary across
groups (NOT cross-group identity on the INPUT side --
``|observed_input_colors| > 1``) AND the per-group oc singletons K_g
vary across groups (NOT cross-group identity on the OUTPUT side --
``|observed_output_colors| > 1``). The strict-disjoint complement of
iter 220 (``singleton_recolor_nonidentity``), iter 221 (``singleton_
recolor_nonidentity_input_anchored``), AND iter 222 (``singleton_
recolor_nonidentity_output_anchored``) within iter 218 (``singleton_
recolor_nonidentity_per_group``)'s territory; closes iter 218's
(input-cross-group-identity, output-cross-group-identity) 2x2 product
axis at the (F, F) "neither anchored" cell.

Recognition vocabulary axis: the input-per-group / output-per-group
non-identity cell of iter 218. Iter 218 names the per-group strict-
recolour-on-singleton cell (every group has |ic| == |oc| == 1 AND ic
!= oc, with the per-group (C_g, K_g) pairs possibly varying across
groups). Within iter 218's territory the cross-group-identity
sub-axis has four cells:

  * (input-anchor, output-anchor) -- single global C and K, K != C.
    This is iter 220 (whole-task non-identity-on-singleton).
  * (input-anchor, output-per-group) -- single global C, K_g varying
    across groups. This is iter 221.
  * (input-per-group, output-anchor) -- C_g varying across groups,
    single global K. This is iter 222.
  * (input-per-group, output-per-group) -- both C_g and K_g vary.
    THIS matcher (whole-task neither-anchored, both-sides-per-group).
    The "vanilla" iter 218 cell with no cross-group identity claim.

The four cells partition iter 218's territory exhaustively at the
2x2 product axis (input-cross-group-identity, output-cross-group-
identity). Iter 220 names cell (T, T); iter 221 names cell (T, F);
iter 222 names cell (F, T); this matcher names cell (F, F). With
this matcher landed, the 2x2 axis is now exhaustively named at four
disjoint recognition handles -- iter 218's territory is fully
covered on the cross-group-identity axis.

This matcher names the precondition for the rule family "whole-task
non-identity recolour with per-group input source C_g and per-group
output target K_g, both varying across groups": rules whose action
is "paint every singleton blob of per-group-determined input colour
C_g with the per-group-determined target colour K_g, with C_g !=
K_g on every group AND both C_g and K_g possibly varying across
groups". Neither side collapses to a single global constant; both
the input and the output sides are per-group (determinable from
the group's position / index / shape / palette / identity in the
input). Iter 220 names the action-shape "C -> K with K != C
globally"; iter 221 names "C -> K_g with K_g != C per group AND K_g
varying"; iter 222 names "C_g -> K with K != C_g per group AND C_g
varying"; this matcher names the action-shape "C_g -> K_g with
K_g != C_g per group AND both C_g and K_g varying" -- a strictly
different rule family at the action-shape resolution. The vanilla
iter-218 per-group recolour rule family.

Strict relations to iter 218 / iter 220 / iter 221 / iter 222 (the
immediate parents):

  * Iter 218 (``singleton_recolor_nonidentity_per_group``): STRICT
    REFINEMENT. This matcher fires => iter 218 fires (per-group |ic|
    == |oc| == 1 AND per-group ic != oc on every group is a
    precondition). The converse fails on any iter-218 task where
    EITHER the input side OR the output side has cross-group
    identity (iter 220 / iter 221 / iter 222 territory).
  * Iter 220 (``singleton_recolor_nonidentity``): STRICT MUTUAL
    EXCLUSION. Iter 220 demands cross-group identity on BOTH sides
    (single global C AND single global K, with C != K); this matcher
    demands non-identity on BOTH sides (|observed_input| > 1 AND
    |observed_output| > 1). The two cells are pairwise disjoint by
    the (input-anchor) and (output-anchor) splits on iter 218's
    territory.
  * Iter 221 (``singleton_recolor_nonidentity_input_anchored``):
    STRICT MUTUAL EXCLUSION. Iter 221 demands cross-group identity
    on the INPUT side AND non-identity on the OUTPUT side. This
    matcher demands non-identity on BOTH sides. Disjoint by the
    (input-anchor) split.
  * Iter 222 (``singleton_recolor_nonidentity_output_anchored``):
    STRICT MUTUAL EXCLUSION. Iter 222 demands cross-group identity
    on the OUTPUT side AND non-identity on the INPUT side. This
    matcher demands non-identity on BOTH sides. Disjoint by the
    (output-anchor) split.

So this matcher is the strict-disjoint complement of iter 220 / iter
221 / iter 222 within iter 218's territory, closing the (input-
cross-group-identity, output-cross-group-identity) 2x2 product axis
at the (F, F) cell. With four cells named at disjoint recognition
handles (iter 220 / iter 221 / iter 222 / this matcher), iter 218's
2x2 axis is exhaustively partitioned -- the four cells cover iter
218's territory completely with no overlap.

Strict relations to iter 217 / iter 219:

  * Iter 217 (``singleton_recolor_identity_per_group``): STRICT MUTUAL
    EXCLUSION. Iter 217 demands per-group ic == oc on every group;
    this matcher demands per-group ic != oc on every group. The two
    are pairwise disjoint by the per-group ic == oc vs ic != oc split.
  * Iter 219 (``singleton_recolor_identity``): STRICT MUTUAL
    EXCLUSION. Iter 219 demands single global C == K (no per-group
    variation, identity-on-singleton); this matcher demands per-group
    ic != oc with BOTH C_g AND K_g varying. The two are pairwise
    disjoint by the (C == K, both anchored) vs (ic != oc, both
    per-group) split.

Strict relations to iter 215 / iter 216:

  * Iter 215 (``singleton_recolor_per_group``): STRICT REFINEMENT.
    Per-group |ic| == |oc| == 1 is a precondition; this matcher
    additionally requires per-group ic != oc AND |observed_input| > 1
    AND |observed_output| > 1.
  * Iter 216 (``singleton_recolor``): STRICT MUTUAL EXCLUSION. Iter
    216 demands cross-group identity on BOTH sides; this matcher
    demands NON-identity on BOTH sides. Disjoint by both anchor
    splits.

Strict relations to iter 14 (``input_color_uniform``) AND iter 18
(``output_color_uniform``):

  * Iter 14 (``input_color_uniform``): STRICT MUTUAL EXCLUSION. Iter
    14 demands cross-group / cross-pair input uniformity (all ic
    singletons bit-identical to one global C); this matcher demands
    |observed_input_colors| > 1. The two are pairwise disjoint by
    the input-side single-C vs multi-C split.
  * Iter 18 (``output_color_uniform``): STRICT MUTUAL EXCLUSION.
    Iter 18 demands cross-group / cross-pair output uniformity (all
    oc singletons bit-identical to one global K); this matcher
    demands |observed_output_colors| > 1. The two are pairwise
    disjoint by the output-side single-K vs multi-K split. Note
    this is DUAL to the iter-14 mutual-exclusion (iter 222 was
    STRICT REFINEMENT of iter 18 because iter 222 demanded output
    anchored; this matcher demands output NOT anchored, hence
    DISJOINT).

Strict relation to iter 8 (``consistent_color_mapping``): INDEPENDENT
in general. Iter 8 demands a function-shaped global mapping (every
input colour maps to a single output colour). This matcher's
territory admits both function-shaped and non-function-shaped
sub-cells:

  * Function-shaped sub-cell: ic=[3]/oc=[0], ic=[5]/oc=[7] (each
    distinct C maps to exactly one K). Iter 8 co-fires.
  * Non-function-shaped sub-cell: ic=[3]/oc=[0], ic=[3]/oc=[7],
    ic=[5]/oc=[7] (C=3 maps to both 0 and 7). Iter 8 REJECTS, this
    matcher still fires (|observed_input| = {3, 5} > 1 AND
    |observed_output| = {0, 7} > 1).

So iter 8 is INDEPENDENT in general (co-fires on the function-shaped
sub-cell of this matcher's territory; the converse also holds: iter
8 can fire on iter 220 / 221 / 222 territories too).

Strict relation to iter 13 (``identity_transformation``): STRICT
MUTUAL EXCLUSION. Iter 13 fires iff every pair has ZERO change
groups (whole-task no-blob identity). This matcher REJECTS the
no-group case (universal-over-groups requires at least one group
per pair; additionally |observed_input| > 1 AND |observed_output|
> 1 requires at least two distinct values witnessed on each side,
hence effectively #groups >= 2 in at least one pair).

Strict relation to iter 213 (``consistent_color_mapping_per_group``)
AND iter 214 (``input_color_uniform_per_group``): both are STRICTLY
IMPLIED by this matcher. Iter 213 demands per-group |oc| == 1; this
matcher demands per-group |oc| == 1, so iter 213 fires. Iter 214
demands per-group |ic| == 1; this matcher demands per-group |ic|
== 1, so iter 214 fires. The converse of each fails (each is
satisfied by larger cells than this matcher's territory).

Strict relation to iter 201 (``output_colors_equals_input_colors_
per_group``): STRICT MUTUAL EXCLUSION. Iter 201 demands per-group
set(ic) == set(oc). This matcher pins per-group ic == [C_g] / oc ==
[K_g] with C_g != K_g per group, forcing per-group set(ic) !=
set(oc).

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
constancy): per-pair palette-shift constancy is independent of this
matcher in general. This matcher pins per-group shift k_g = K_g -
C_g, with both C_g AND K_g varying across groups. The per-pair
shifts k_g may or may not be constant across groups within a pair:

  * Iter 198 co-fires when per-pair k_g is constant across groups
    within each pair (e.g., (C_g, K_g) = (0, 3), (1, 4), (2, 5) all
    share k = 3 within the pair).
  * Iter 198 REJECTS when per-pair k_g varies within a pair (e.g.,
    (C_g, K_g) = (3, 0), (5, 7) have k = -3, 2 -- not constant).

So iter 198 is INDEPENDENT in general (co-fires only on the
within-pair-constant-shift sub-cell). Iter 199 strict-refines iter
198 with cross-pair k constancy. The relation is INDEPENDENT for
iter 199 too (co-fires only on the within-pair-AND-cross-pair-
constant-shift sub-cell of this matcher's territory).

Strict relation to iter 10 (``sequential_recoloring``): co-fires
on the contiguous-range sub-cell of this matcher's territory.
Iter 10 demands per-group |oc| == 1 with the per-pair oc singletons
forming a contiguous range of size >= 2. When this matcher fires,
|observed_output| > 1 -- so iter 10 may co-fire when the per-pair
oc singletons happen to form a contiguous range (e.g., the iter-10
canonical fixture: oc singletons 3, 4, 5 form a contiguous range of
size 3). Iter 10 REJECTS otherwise (non-contiguous range). So iter
10 is INDEPENDENT in general (co-fires on the contiguous-range
sub-cell; rejects elsewhere). In particular, iter 10 co-fires with
this matcher on the iter-10 canonical fixture (the DISTINGUISHING
co-fire witness vs iter 220 / 221 / 222 where iter 10 cannot fire
because output is anchored at a single K, not a non-trivial range).

Why a distinct matcher rather than just AND-ing iter 218 with iter
14-mutex AND iter 18-mutex at the rule level: the matcher contract
(docs/RULE_FORMAT.md §4) is name-keyed recognition vocabulary; the
rule's stored ``condition.type`` is the recognition handle's name,
not a Boolean composition tree. A rule whose precondition is "per-
group |ic| == |oc| == 1 AND per-group ic != oc AND input-side
cross-group identity failure AND output-side cross-group identity
failure" gates a DIFFERENT rule family (input-per-group / output-
per-group strict recolour, the vanilla iter-218 cell where neither
side anchors a single global constant; the C_g AND K_g BOTH depend
on per-group features) than iter 218 alone (per-group strict
recolour admitting any combination of anchored / per-group on each
side). Keeping the conjunction as a separate registry slot lets
anti-unification (CLAUDE.md §8) attach the right gate per rule
family -- specifically the gate for rules whose action is "C_g ->
K_g with K_g != C_g per group AND both C_g and K_g varying across
groups" -- without rediscovering the input-per-group / output-per-
group structure from the rule's stored action shape.

Why a distinct matcher rather than parameterising iter 218 with an
``input_anchored: False, output_anchored: False`` flag: the matcher
contract is name-keyed recognition vocabulary; the rule's stored
``condition.type`` is the recognition handle's name, not a name+
params tuple. The (input-per-group, output-per-group) sub-cell of
iter 218 is structurally identifiable as the strict-disjoint
complement of iter 220 / iter 221 / iter 222 within iter 218's
territory -- the closing fourth cell of the 2x2 cross-group-
identity product axis; it is a recognition handle in its own right
(the "vanilla" per-group / per-group strict-recolour cell, the most
general non-anchored sub-cell of iter 218), not a Boolean parameter
of the per-group strict-recolour axis.

Why this matters as the closing cell of iter 218's 2x2 axis: with
iter 220 naming the (T, T) cell, iter 221 naming the (T, F) cell,
iter 222 naming the (F, T) cell, and this matcher naming the (F, F)
cell, all four cells of the (input-cross-group-identity, output-
cross-group-identity) 2x2 product axis on iter 218's territory are
named at disjoint recognition handles. The four cells partition
iter 218's territory exhaustively -- every iter-218 task lands in
exactly one of the four named cells. This closes the 2x2 axis as a
fully-resolved sub-territory of iter 218; further refinement on
iter 218 must move to a different sub-axis (e.g., function-shape,
palette-shift constancy, contiguous-range output).

Strict refinement / orthogonality summary (universal-over-groups-
and-pairs semantics, per-group |ic| == |oc| == 1 AND ic != oc AND
|observed_input_colors| > 1 AND |observed_output_colors| > 1):

  * Iter 218 (``singleton_recolor_nonidentity_per_group``) -- STRICT
    REFINEMENT (this matcher additionally requires
    |observed_input| > 1 AND |observed_output| > 1).
  * Iter 220 (``singleton_recolor_nonidentity``) -- STRICT MUTUAL
    EXCLUSION (iter 220 demands cross-group identity on BOTH sides;
    this matcher demands NON-identity on BOTH sides).
  * Iter 221 (``singleton_recolor_nonidentity_input_anchored``) --
    STRICT MUTUAL EXCLUSION (iter 221 demands input-side anchor;
    this matcher demands input-side failure).
  * Iter 222 (``singleton_recolor_nonidentity_output_anchored``) --
    STRICT MUTUAL EXCLUSION (iter 222 demands output-side anchor;
    this matcher demands output-side failure).
  * Iter 219 (``singleton_recolor_identity``) -- STRICT MUTUAL
    EXCLUSION (iter 219 demands C == K; this matcher demands per-
    group ic != oc).
  * Iter 217 (``singleton_recolor_identity_per_group``) -- STRICT
    MUTUAL EXCLUSION (iter 217 demands per-group ic == oc; this
    matcher demands per-group ic != oc).
  * Iter 216 (``singleton_recolor``) -- STRICT MUTUAL EXCLUSION
    (iter 216 demands cross-group identity on BOTH sides; this
    matcher demands NON-identity on BOTH sides).
  * Iter 215 (``singleton_recolor_per_group``) -- STRICT REFINEMENT
    (per-group |ic| == |oc| == 1 is a precondition; per-group ic !=
    oc AND |observed_input| > 1 AND |observed_output| > 1
    additionally required).
  * Iter 14 (``input_color_uniform``) -- STRICT MUTUAL EXCLUSION
    (iter 14 demands cross-group input uniformity; this matcher
    demands |observed_input| > 1).
  * Iter 18 (``output_color_uniform``) -- STRICT MUTUAL EXCLUSION
    (iter 18 demands cross-group output uniformity; this matcher
    demands |observed_output| > 1).
  * Iter 213 / iter 214 -- STRICTLY IMPLIED.
  * Iter 8 (``consistent_color_mapping``) -- INDEPENDENT (co-fires
    on the function-shaped sub-cell of this matcher's territory).
  * Iter 13 (``identity_transformation``) -- STRICT MUTUAL EXCLUSION
    (iter 13 occupies the #groups == 0 cell; this matcher requires
    at least two distinct C_g AND two distinct K_g values
    witnessed).
  * Iter 10 (``sequential_recoloring``) -- INDEPENDENT (co-fires on
    the contiguous-range sub-cell of this matcher's territory; the
    DISTINGUISHING co-fire witness vs iter 220 / 221 / 222 where
    iter 10 cannot co-fire because output side is anchored).
  * Iter 195 / 196 / 197 (per-group cardinality matchers) --
    STRICTLY IMPLIED at K_in == K_out == K_prod == 1.
  * Iter 198 / 199 (palette-shift constancy) -- INDEPENDENT
    (co-fires only on the within-pair-constant-shift sub-cell).
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
    to per-group singleton input-per-group / output-per-group
    strict-recolour.

Why this matters for ARBOR's intended ruleset:

  * "Input-per-group / output-per-group strict-recolour" rule family
    -- rules whose action is "paint every singleton blob of per-
    group-determined input colour C_g with the per-group-determined
    target colour K_g, with C_g != K_g on every group AND both C_g
    and K_g possibly varying across groups". The most general non-
    anchored whole-task recolour shape on the singleton row; the
    "vanilla" iter-218 cell with no cross-group identity claim on
    either side. The building block from which more complex per-
    group recolour rules (e.g., "the (C_g, K_g) pair depends on the
    group's position / index / shape / palette / identity in the
    input, with no global anchor on either side") generalise. This
    matcher names the precondition for that rule family, in a
    single registry slot, so anti-unification can attach the right
    gate to rules of this shape without having to rediscover the
    iter 218 ^ input-non-anchor ^ output-non-anchor intersection
    each time.
  * Closes the iter-222-named candidate (xiii): "the (F, F) 'neither
    anchored' cell, a single matcher pinning |ic| == |oc| == 1 AND
    per-group ic != oc AND ``len(observed_input_colors) > 1`` AND
    ``len(observed_output_colors) > 1`` (the strict refinement of
    iter 218 at the cell where BOTH cross-group identity claims
    fail; the vanilla iter 218 cell with no anchor on either side)".
    With this matcher landed, all four cells of iter 218's 2x2
    cross-group-identity axis are named (iter 220 / iter 221 / iter
    222 / this matcher). The 2x2 axis is exhaustively partitioned
    on iter 218's territory.

Params:
  (none) -- pure per-group input-per-group / output-per-group
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
    200-206 / 213 / 214 / 215 / 217 / 218 / 219 / 220 / 221 / 222
    strict-type posture), AND
  - for every group, ``len(set(input_colors)) == 1`` AND
    ``len(set(output_colors)) == 1`` AND
    ``set(input_colors) != set(output_colors)``, AND
  - the per-group ic singletons C_g vary across groups OR pairs --
    i.e. ``len(observed_input_colors) > 1`` (NOT cross-group
    identity on the INPUT side), AND
  - the per-group oc singletons K_g vary across groups OR pairs --
    i.e. ``len(observed_output_colors) > 1`` (NOT cross-group
    identity on the OUTPUT side -- the strict-disjoint complement
    of iter 220 / iter 221 / iter 222 within iter 218's territory).

Why fail-closed on empty / no-group / malformed (same posture as
iter 8 / 13 / 14 / 18 / 30 / 32 / 33 / 34 / 35 / 36 / 37 / 38 / 39 /
184-222): a missing or zero-group pair is upstream extractor
breakage or iter 13's no-blob-identity territory; a whole-task
input-per-group / output-per-group strict-recolour claim with zero
observations is meaningless, AND admitting it would collapse this
matcher's territory into iter 13's (the two are designed as
disjoint cells on the (#groups, recolour-shape) axis).

Why strict per-colour validation (bool rejected, range checked):
``input_colors`` / ``output_colors`` carry small ints in [0, 9];
the matcher performs the same strict-type gating as iter 14 / 18 /
19 / 34 / 35 / 36 / 37 / 38 / 184-222 to keep contract violations
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


@register("singleton_recolor_nonidentity_unanchored")
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
    return (
        len(observed_input_colors) > 1
        and len(observed_output_colors) > 1
    )
