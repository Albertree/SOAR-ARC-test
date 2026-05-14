"""
singleton_recolor_nonidentity -- match tasks where every changed cell
across every example pair started as the SAME single input colour C
AND ended as the SAME single output colour K AND C != K. The STRICT
COMPLEMENT of iter 219 (``singleton_recolor_identity``) within iter
216's (``singleton_recolor``) territory. The whole-task projection of
iter 218 (``singleton_recolor_nonidentity_per_group``) at the cross-
group-identity-on-both-sides cell. Equivalently, the strict CONJUNCTION
of iter 14 (``input_color_uniform``) AND iter 18 (``output_color_
uniform``) AND "C != K globally".

Recognition vocabulary axis: the whole-task non-identity-on-singleton
cell. Iter 216 names the whole-task bijective-singleton-recolour cell
(whole-task |ic| == |oc| == 1 with single global C and single global K
across all groups in all pairs, with C possibly == K OR != K). Iter
218 names the per-group sub-cell of iter 215 where every group has
K_g != C_g (the per-group strict-recolour-on-singleton cell). This
matcher names the whole-task analogue: the iter-216 sub-cell where
the single global C differs from the single global K (C != K). With
C != K globally on the iter 216 territory the whole-task recolour
shape reduces to "C -> K with K != C" -- the simplest non-trivial
whole-task strict-recolour-on-singleton shape.

This matcher names the precondition for the rule family "whole-task
strict-recolour expressed as a global singleton recolour C -> K with
K != C": rules whose action is the strict recolour of the global
singleton C onto the strictly different global singleton K, with
two global constants (C, K) determinable from training. Iter 219
names the whole-task singleton-blob identity cell (one global fixed
point C); this matcher names its strict complement -- the whole-task
singleton-blob strict-recolour cell (one global source C != one
global target K). Together iter 219 + this matcher partition iter
216's bijective-singleton territory at the (C == K) vs (C != K)
binary -- the iter 216 axis is now named at two disjoint sub-cells.

Strict relations to iter 216 / iter 218 (the immediate parents):

  * Iter 216 (``singleton_recolor``): STRICT REFINEMENT. This matcher
    fires => iter 216 fires (whole-task |ic| == |oc| == 1 with cross-
    group identity is a precondition of this matcher). The converse
    fails on a task where iter 216 fires with C == K (every group
    recoloured C -> C globally): iter 216 fires (whole-task bijective
    singleton), this matcher rejects (the two singletons are equal,
    iter 219's territory).
  * Iter 218 (``singleton_recolor_nonidentity_per_group``): STRICT
    REFINEMENT. This matcher fires => iter 218 fires (per-group |ic|
    == |oc| == 1 AND per-group ic != oc on every group is a
    precondition: when cross-group identity holds with C != K, every
    group has ic == [C] AND oc == [K] with C != K, satisfying per-
    group ic != oc trivially). The converse fails on a task where
    iter 218 fires with per-group (C_g, K_g) varying across groups
    (e.g. group A has ic = [3] / oc = [0]; group B has ic = [5] /
    oc = [7]): iter 218 fires, this matcher rejects (cross-group
    identity fails: input singletons differ across groups).

So this matcher is the STRICT CONJUNCTION of iter 216 (whole-task
bijective singleton with cross-group identity) AND iter 218 (per-
group ic != oc). The pair-completion of the whole-task bijective-
singleton-recolour axis (iter 216) closed at the non-identity sub-
cell: iter 216 admits both C == K and C != K; this matcher pins
C != K. With this matcher landed, the iter-216 axis is named at two
disjoint sub-cells: identity C == K (iter 219) AND non-identity
C != K (this matcher) -- the previously-implicit conjunction (iter
216 AND "C != K globally") is now a first-class recognition handle.

Strict relations to iter 14 (``input_color_uniform``) AND iter 18
(``output_color_uniform``) jointly: iter 14 ∧ iter 18 ∧ "C != K
globally" => this matcher fires. Iter 14 fires => per-pair every
group has |ic| == 1 AND all ic singletons cross-group bit-identical
to one global C; iter 18 fires => per-pair every group has |oc| == 1
AND all oc singletons cross-group bit-identical to one global K. The
conjunction iter 14 ∧ iter 18 fires iff |ic| == |oc| == 1 per group
AND the two global constants C, K exist (the iter-216 territory).
This matcher additionally requires C != K, which on the iter 14 ∧
iter 18 territory pins the whole-task recolour shape to C -> K with
K != C. The converse fails when per-group fixed points C_g, K_g vary
across groups (iter 218 fires, this matcher rejects on cross-group
identity failure).

Strict relation to iter 13 (``identity_transformation``): STRICT
MUTUAL EXCLUSION. Iter 13 fires iff every pair has ZERO change
groups (whole-task no-blob identity). This matcher REJECTS the no-
group case (universal-over-groups requires at least one group per
pair, mirroring iter 216 / 218 / 219 identity-territory rejection).
Iter 13 occupies the whole-task no-blob identity cell on the
identity-rule-family axis; this matcher is the whole-task strict-
recolour singleton cell -- a NON-identity rule cell, distinguishing
the strict-recolour territory from iter 13's no-op territory. The
two are pairwise disjoint by the (#groups == 0, no recolour) vs
(#groups >= 1, strict singleton recolour) split.

Strict relation to iter 219 (``singleton_recolor_identity``): STRICT
MUTUAL EXCLUSION. Iter 219 fires iff whole-task |ic| == |oc| == 1
with cross-group identity AND C == K; this matcher fires iff whole-
task |ic| == |oc| == 1 with cross-group identity AND C != K. The two
cells are pairwise disjoint by the (C == K) vs (C != K) split on the
iter-216 bijective-singleton territory. Within iter 216's territory
they partition exhaustively: every iter-216-firing task lands in
EXACTLY ONE of {iter 219, this matcher} (since iter 216 already pins
the two global constants C and K, and exactly one of C == K or
C != K holds). The two-cell pair (iter 219, this matcher) closes the
iter-216 axis at the action-shape resolution, paralleling iter 217 +
iter 218 at the per-group resolution.

Strict relation to iter 215 (``singleton_recolor_per_group``):
STRICT REFINEMENT. This matcher fires => iter 215 fires (per-group
|ic| == |oc| == 1 is satisfied trivially when cross-group identity
holds at |ic| == |oc| == 1). The converse fails on iter-215
territory with per-group singletons varying across groups (this
matcher demands cross-group identity AND C != K; iter 215 admits
neither constraint).

Strict relation to iter 217 (``singleton_recolor_identity_per_group``):
STRICT MUTUAL EXCLUSION. Iter 217 fires iff every group has ic == oc
as singletons; this matcher fires iff every group has ic = [C] and
oc = [K] as singletons with C != K (i.e. ic != oc on every group).
The two are mutually exclusive by the per-group ic == oc vs ic != oc
split on the iter-215 bijective-singleton territory; this matcher
forces the per-group "ic != oc" half by demanding C != K globally on
the cross-group-identity sub-cell.

Strict relation to iter 213 (``consistent_color_mapping_per_group``)
AND iter 214 (``input_color_uniform_per_group``): both are STRICTLY
IMPLIED by this matcher (this matcher => iter 215 => iter 213, iter
214). The converse of each fails.

Strict relation to iter 8 (``consistent_color_mapping``): STRICT
REFINEMENT. Iter 8 says every input colour maps to a single output
colour globally (forward function-shape). This matcher additionally
requires only ONE input colour AND only ONE output colour across the
whole task AND those two are NOT equal. With iter 14 firing (single
global C), iter 8 reduces to "C maps to exactly one output K"; with
iter 18 firing (single global K), the implied global mapping is the
singleton map {C -> K}; with C != K the singleton map is a strict
recolour (the identity map restricted to {C} fails -- it would map
C -> C, not C -> K). So this matcher fires => iter 8 fires (the
singleton map {C -> K} is trivially function-shaped). The converse
fails when iter 8 fires with multiple distinct (in, out) pairs.

Strict relation to iter 201 (``output_colors_equals_input_colors_per_
group``): STRICT MUTUAL EXCLUSION. Iter 201 demands per-group
set(ic) == set(oc). This matcher pins per-group ic == [C] and oc ==
[K] with C != K globally, so per-group set(ic) != set(oc) on every
group. The two cells are disjoint on the |ic| == |oc| == 1 row.

Strict relation to iter 10 (``sequential_recoloring``): per-group
|oc| == 1 with singletons forming a contiguous integer range. With
this matcher firing (every group has ic == [C] and oc == [K] with
C != K), the per-pair oc list has length == 1 (one distinct value
K), which is trivially a length-1 "range". So iter 10 fires on the
degenerate length-1 cell; INDEPENDENT in general (iter 10 admits
length >= 2 ranges that this matcher rejects).

Strict relation to iter 195 / 196 / 197 (per-group cardinality
matchers): this matcher implies iter 195 at K_in == 1 (input
cardinality) AND iter 196 at K_out == 1 (output cardinality) AND
iter 197 at K_prod == 1 (product). The converse for each fails at
K != 1.

Strict relation to iter 198 / 199 (per-group palette-shift
constancy): within-pair / global constant shift k = oc - ic at the
|ic| == |oc| cell. This matcher fires => per-group shift k = K - C
!= 0 on every group (C -> K with K != C reduces to a non-zero
shift). Iter 199 strict-implies this matcher only at the k != 0
cell with |ic| == |oc| == 1 AND cross-group identity; in general
iter 198 / 199 admit k == 0 cells that fail this matcher.

Strict relation to iter 200-206 (per-group palette-relation cells):
on the singleton row with ic != oc (this matcher's territory), iter
203 (per-group palette-disjoint) STRICTLY FIRES (singleton sets
{C} ∩ {K} == ∅ when C != K). The other six per-group palette-
relation cells are STRICTLY MUTUALLY EXCLUSIVE with this matcher on
the |ic| == |oc| == 1 row -- iter 201 (set-equality) would require
ic == oc; iter 200 / 202 / 204 / 205 reduce to either equality or
disjoint on the singleton row; iter 206 (partial overlap) requires
both non-empty intersection AND non-empty difference, impossible on
the singleton row with disjoint singletons.

Why a distinct matcher rather than just AND-ing iter 216 with "C !=
K" at the rule level: the matcher contract (docs/RULE_FORMAT.md §4)
is name-keyed recognition vocabulary; the rule's stored ``condition.
type`` is the recognition handle's name, not a Boolean composition
tree with inequality predicates over rule parameters. A rule whose
precondition is "single global recolour C -> K with K != C" gates a
DIFFERENT rule family (whole-task strict-recolour-on-singleton, a
real recolour expressed via the change-group structure) than iter
216 alone (whole-task bijective singleton admitting both C == K and
C != K) or iter 219 alone (whole-task identity-on-singleton, the
no-op recolour). Keeping the conjunction as a separate registry slot
lets anti-unification (CLAUDE.md §8) attach the right gate per rule
family -- specifically the gate for rules whose action is "strict
recolour, expressed as the singleton recolour C -> K with K != C" --
without rediscovering the C != K predicate from the rule's stored
action shape.

Why a distinct matcher rather than parameterising iter 216 with a
``nonidentity_only: True`` flag: the matcher contract is name-keyed
recognition vocabulary; the rule's stored ``condition.type`` is the
recognition handle's name, not a name+params tuple. The non-identity
sub-cell of iter 216 is structurally identifiable as the intersection
of iter 216 (whole-task bijective singleton) and the additional C !=
K predicate; it is a recognition handle in its own right (the
simplest whole-task strict-recolour cell), not a Boolean parameter
of the bijective-singleton axis.

Why this matters as the whole-task projection of iter 218: iter 218
names the per-group strict-recolour-on-singleton cell (per-group ic
!= oc with per-group (C_g, K_g) pairs possibly varying across
groups). This matcher names the whole-task strict-recolour-on-
singleton cell (one global source C and one global target K across
all groups in all pairs, with C != K). The two are co-located on the
non-identity-rule-family axis but at different resolutions:

  * (per-group, per-group (C_g, K_g) possibly varying)          -- iter 218 (per-group strict
                                                                     recolour).
  * (whole-task, single global C, single global K, C != K)      -- THIS matcher (whole-task
                                                                     strict recolour).
  * (per-group, per-group ic == oc)                              -- iter 217 (per-group identity).
  * (whole-task, single global C == K)                           -- iter 219 (whole-task identity).

With this matcher landed, the four-cell product axis (per-group /
whole-task) x (identity / non-identity) on iter 215 / 216's
bijective-singleton territory closes:

  * iter 217 -- (per-group, identity).
  * iter 218 -- (per-group, non-identity).
  * iter 219 -- (whole-task, identity).
  * THIS matcher -- (whole-task, non-identity).

Strict refinement / orthogonality summary (universal-over-groups-
and-pairs semantics, whole-task |ic| == |oc| == 1 + cross-group
identity + C != K):

  * Iter 216 (``singleton_recolor``) -- STRICT REFINEMENT (this
    matcher additionally requires C != K).
  * Iter 218 (``singleton_recolor_nonidentity_per_group``) -- STRICT
    REFINEMENT (this matcher additionally requires cross-group
    identity on both sides; iter 218 admits per-group (C_g, K_g)
    varying across groups).
  * Iter 219 (``singleton_recolor_identity``) -- STRICT MUTUAL
    EXCLUSION. Iter 219 fires iff whole-task |ic| == |oc| == 1 with
    cross-group identity AND C == K; this matcher fires iff whole-
    task |ic| == |oc| == 1 with cross-group identity AND C != K.
    The two cells partition iter 216's territory exhaustively at
    the (C == K) vs (C != K) split.
  * Iter 14 (``input_color_uniform``) -- STRICT REFINEMENT (this
    matcher additionally requires the output side to collapse to a
    strictly different singleton).
  * Iter 18 (``output_color_uniform``) -- STRICT REFINEMENT (this
    matcher additionally requires the input side to collapse to a
    strictly different singleton).
  * Iter 215 (``singleton_recolor_per_group``) -- STRICT
    REFINEMENT (per-group |ic| == |oc| == 1 is a precondition;
    cross-group identity AND C != K is additionally required).
  * Iter 217 (``singleton_recolor_identity_per_group``) -- STRICT
    MUTUAL EXCLUSION (iter 217 demands per-group ic == oc; this
    matcher's per-group ic = [C], oc = [K] with C != K forces per-
    group ic != oc).
  * Iter 213 / iter 214 -- STRICTLY IMPLIED.
  * Iter 8 (``consistent_color_mapping``) -- STRICT REFINEMENT
    (the implied global mapping is the singleton map {C -> K} with
    K != C).
  * Iter 13 (``identity_transformation``) -- STRICT MUTUAL
    EXCLUSION. Iter 13 occupies the (#groups == 0) cell; this
    matcher requires at least one change group per pair.
  * Iter 10 (``sequential_recoloring``) -- INDEPENDENT in general;
    co-fires only on the degenerate length-1-range cell that
    coincides with this matcher's territory.
  * Iter 195 / 196 / 197 (per-group cardinality matchers) --
    STRICTLY IMPLIED at K == K == K_prod == 1. Cross-pair
    constancy at K == 1 is subsumed by universal-over-pairs
    semantics here.
  * Iter 198 / 199 (per-group palette-shift constancy) -- this
    matcher implies per-group shift k = K - C != 0 on every group
    (C -> K with K != C reduces to a non-zero shift). Co-fires only
    on the iter 198 / 199 k != 0 cell with |ic| == |oc| == 1 AND
    cross-group identity.
  * Iter 201 (``output_colors_equals_input_colors_per_group``) --
    STRICT MUTUAL EXCLUSION (this matcher demands per-group ic !=
    oc; iter 201 demands per-group ic == oc).
  * Iter 203 (``output_colors_disjoint_from_input_colors_per_
    group``) -- STRICTLY IMPLIED by this matcher (on the singleton
    row, ic != oc forces ic ∩ oc == ∅). Converse fails when iter
    203 fires with |ic| > 1 OR |oc| > 1.
  * Iter 200 / 202 / 204 / 205 / 206 (per-group palette-relation
    cells) -- STRICTLY MUTUALLY EXCLUSIVE with this matcher on
    the |ic| == |oc| == 1 row.
  * Every cell- / position- / dimension-axis matcher -- orthogonal
    to whole-task singleton strict-recolour.

Why this matters for ARBOR's intended ruleset:

  * "Whole-task strict-recolour-on-singleton" rule family -- rules
    whose action is the strict singleton recolour C -> K with K !=
    C, with two global constants C, K determinable from training.
    The simplest non-trivial whole-task recolour shape (rivalling
    iter 219's whole-task identity-on-singleton at the dual cell);
    the building block from which more complex global strict-
    recolour rules (e.g. "recolour the global singleton AND modify
    everything else") generalise. This matcher names the precondition
    for that rule family, in a single registry slot, so anti-
    unification can attach the right gate to rules of this shape
    without having to rediscover the iter 216 ∧ "C != K" intersection
    each time.
  * Closes the iter-219-named candidate (x): "the whole-task NON-
    IDENTITY-on-singleton cell, a single matcher pinning |ic| ==
    |oc| == 1 AND cross-group identity on both sides AND C != K
    globally (the strict complement of iter 219 within iter 216's
    territory, the whole-task projection of iter 218 at the cross-
    group-identity cell)". With this matcher landed, the iter-216
    bijective-singleton-recolour axis is named at two disjoint sub-
    cells (identity / non-identity), paralleling iter 217 / iter
    218 exactly at the whole-task scope; the four-cell product axis
    (per-group / whole-task) x (identity / non-identity) closes at
    iter 217 + iter 218 + iter 219 + this matcher.

Params:
  (none) -- pure whole-task global singleton-strict-recolour check,
  universal over groups and pairs.

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
    200-206 / 213 / 214 / 215 / 217 / 218 / 219 strict-type
    posture), AND
  - for every group, ``len(set(input_colors)) == 1`` AND
    ``len(set(output_colors)) == 1``, AND
  - all single input colours across all groups in all pairs are
    bit-identical to one global C, AND
  - all single output colours across all groups in all pairs are
    bit-identical to one global K, AND
  - C != K (the whole-task strict-recolour sub-cell of iter 216).

Why fail-closed on empty / no-group / malformed (same posture as
iter 8 / 13 / 14 / 18 / 30 / 32 / 33 / 34 / 35 / 36 / 37 / 38 / 39 /
184-219): a missing or zero-group pair is upstream extractor
breakage or iter 13's no-blob-identity territory; a whole-task
single-global-strict-recolour claim with zero observations is
meaningless, AND admitting it would collapse this matcher's
territory into iter 13's (the two are designed as disjoint cells
on the (#groups, recolour-shape) axis).

Why ``input_colors`` and ``output_colors`` both required non-empty
lists per group (``len >= 1``): a connected change group has at
least one cell; each cell has both an input colour and an output
colour; the per-group ``input_colors`` / ``output_colors`` fields
are the sorted unique sets of those colours, which are non-empty
for any non-empty group.

Why strict per-colour validation (bool rejected, range checked):
``input_colors`` / ``output_colors`` carry small ints in [0, 9];
the matcher performs the same strict-type gating as iter 14 / 18 /
19 / 34 / 35 / 36 / 37 / 38 / 184-219 to keep contract violations
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


@register("singleton_recolor_nonidentity")
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
            observed_input_colors |= ic_set
            observed_output_colors |= oc_set
            if len(observed_input_colors) > 1:
                return False
            if len(observed_output_colors) > 1:
                return False
    return (
        len(observed_input_colors) == 1
        and len(observed_output_colors) == 1
        and observed_input_colors != observed_output_colors
    )
