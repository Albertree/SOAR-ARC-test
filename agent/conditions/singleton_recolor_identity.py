"""
singleton_recolor_identity -- match tasks where every changed cell
across every example pair started as the SAME single input colour C
AND ended as the SAME single output colour K AND C == K. The STRICT
REFINEMENT of iter 216 (``singleton_recolor``) at the "C == K globally"
sub-cell. The whole-task projection of iter 217 (``singleton_recolor_
identity_per_group``) at the cross-group-identity-on-both-sides cell.
Equivalently, the strict CONJUNCTION of iter 14 (``input_color_
uniform``) AND iter 18 (``output_color_uniform``) AND "C == K
globally".

Recognition vocabulary axis: the simplest whole-task identity-on-
singleton cell. Iter 216 names the whole-task bijective-singleton-
recolour cell (whole-task |ic| == |oc| == 1 with single global C and
single global K across all groups in all pairs, with C possibly == K
OR != K). Iter 217 names the per-group sub-cell of iter 215 where
every group has K_g == C_g (the per-group identity-on-singleton
cell). This matcher names the whole-task analogue: the iter-216
sub-cell where the single global C equals the single global K (C ==
K). With C == K globally on the iter 216 territory the whole-task
recolour shape reduces to "C -> C" -- the iter-13-canonical no-blob
identity expressed as a single global one-singleton recolour on the
change groups.

This matcher names the precondition for the rule family "whole-task
identity expressed as a global singleton recolour C -> C": rules
whose action is the no-op recolour of the global singleton C onto
itself, with one global fixed point C determinable from training as
a constant. Iter 13 names the whole-task no-blob identity (zero
change groups); iter 217 names the per-group singleton-blob identity
(every change group is itself an identity on its per-group
singleton); this matcher names the whole-task singleton-blob identity
(every change group exists with the same global singleton C and the
same global singleton K, AND C == K -- i.e. one global fixed point
across all groups in all pairs). Together with iter 13 and iter 217
they name THREE disjoint identity-rule-family preconditions on the
(#groups, cross-group-identity) lattice for the singleton rows:

  * (#groups == 0, *)                                          -- iter 13 (no-blob identity).
  * (#groups >= 1, per-group |ic| == |oc| == 1 AND per-group   -- iter 217 (per-group singleton-blob
    ic == oc, NO cross-group identity required)                   identity, with per-group fixed
                                                                  points C_g possibly varying).
  * (#groups >= 1, whole-task |ic| == |oc| == 1 AND C == K     -- THIS matcher (whole-task singleton-
    globally with cross-group identity on both sides)             blob identity, with one global
                                                                  fixed point C).

Strict relations to iter 216 / iter 217 (the immediate parents):

  * Iter 216 (``singleton_recolor``): STRICT REFINEMENT. This matcher
    fires => iter 216 fires (whole-task |ic| == |oc| == 1 with cross-
    group identity is a precondition of this matcher). The converse
    fails on a task where iter 216 fires with C != K (e.g. every
    group recoloured 3 -> 0): iter 216 fires (whole-task bijective
    singleton), this matcher rejects (the two singletons differ).
  * Iter 217 (``singleton_recolor_identity_per_group``): STRICT
    REFINEMENT. This matcher fires => iter 217 fires (per-group |ic|
    == |oc| == 1 AND per-group ic == oc on every group is a
    precondition: when cross-group identity holds with C == K, every
    group trivially satisfies per-group ic == oc == [C]). The
    converse fails on a task where iter 217 fires with per-group
    fixed points varying across groups (e.g. group A has ic = oc =
    [3]; group B has ic = oc = [5]): iter 217 fires, this matcher
    rejects (cross-group identity fails: input singletons differ
    across groups).

So this matcher is the STRICT CONJUNCTION of iter 216 (whole-task
bijective singleton with cross-group identity) AND iter 217 (per-
group ic == oc). The pair-completion of the whole-task bijective-
singleton-recolour axis (iter 216) closed at the identity sub-cell:
iter 216 admits both C == K and C != K; this matcher pins C == K.
With this matcher landed, the iter-216 axis is named at two disjoint
sub-cells: identity C == K (this matcher) AND non-identity C != K
(iter 216 minus this matcher; the strict-recolour-on-singleton
whole-task cell, the closest-fitting sibling candidate freshly
opened by this iter).

Strict relations to iter 14 (``input_color_uniform``) AND iter 18
(``output_color_uniform``) jointly: iter 14 ∧ iter 18 ∧ "C == K
globally" => this matcher fires. Iter 14 fires => per-pair every
group has |ic| == 1 AND all ic singletons cross-group bit-identical
to one global C; iter 18 fires => per-pair every group has |oc| == 1
AND all oc singletons cross-group bit-identical to one global K. The
conjunction iter 14 ∧ iter 18 fires iff |ic| == |oc| == 1 per group
AND the two global constants C, K exist (the iter-216 territory).
This matcher additionally requires C == K, which on the iter 14 ∧
iter 18 territory pins the whole-task recolour shape to C -> C. The
converse fails when per-group fixed points C_g vary across groups
(iter 217 fires, this matcher rejects on cross-group identity
failure).

Strict relation to iter 13 (``identity_transformation``): STRICT
MUTUAL EXCLUSION. Iter 13 fires iff every pair has ZERO change
groups (whole-task no-blob identity). This matcher REJECTS the no-
group case (universal-over-groups requires at least one group per
pair, mirroring iter 216 / 217's identity-territory rejection). Iter
13 is the whole-task no-blob identity; this matcher is the whole-
task singleton-blob identity. The two are disjoint identity-rule-
family preconditions on the #groups axis: iter 13 occupies the
(#groups == 0, *) row; this matcher occupies the (#groups >= 1, |ic|
== |oc| == 1 cross-group AND C == K) cell.

Strict relation to iter 215 (``singleton_recolor_per_group``):
STRICT REFINEMENT. This matcher fires => iter 215 fires (per-group
|ic| == |oc| == 1 is satisfied trivially when cross-group identity
holds at |ic| == |oc| == 1). The converse fails on iter-215
territory with per-group singletons varying across groups (this
matcher demands cross-group identity AND C == K; iter 215 admits
neither constraint).

Strict relation to iter 213 (``consistent_color_mapping_per_group``)
AND iter 214 (``input_color_uniform_per_group``): both are STRICTLY
IMPLIED by this matcher (this matcher => iter 215 => iter 213, iter
214). The converse of each fails.

Strict relation to iter 8 (``consistent_color_mapping``): STRICT
REFINEMENT. Iter 8 says every input colour maps to a single output
colour globally (forward function-shape). This matcher additionally
requires only ONE input colour AND only ONE output colour across the
whole task AND those two are equal. With iter 14 firing (single
global C), iter 8 reduces to "C maps to exactly one output K"; with
iter 18 firing (single global K), the implied global mapping is the
singleton map {C -> K}; with C == K the singleton map degenerates to
{C -> C} (the identity restricted to {C}). So this matcher fires =>
iter 8 fires (the singleton map {C -> C} is trivially function-
shaped). The converse fails when iter 8 fires with multiple distinct
(in, out) pairs.

Strict relation to iter 201 (``output_colors_equals_input_colors_per_
group``): STRICTLY IMPLIED. With every per-group ic == oc == [C] as
singletons (the iter 217 territory restricted to cross-group
identity), per-group set(ic) == set(oc) holds trivially. The
converse fails when iter 201 fires with |ic| > 1 (this matcher
rejects).

Strict relation to iter 10 (``sequential_recoloring``): per-group
|oc| == 1 with singletons forming a contiguous integer range. With
this matcher firing (every group has ic == oc == [C]), the per-pair
oc list has length == 1 (one distinct value C), which is trivially a
length-1 "range". So iter 10 fires on the degenerate length-1 cell;
INDEPENDENT in general (iter 10 admits length >= 2 ranges that this
matcher rejects).

Strict relation to iter 195 / 196 / 197 (per-group cardinality
matchers): this matcher implies iter 195 at K_in == 1 (input
cardinality) AND iter 196 at K_out == 1 (output cardinality) AND
iter 197 at K_prod == 1 (product). The converse for each fails at
K != 1.

Strict relation to iter 198 / 199 (per-group palette-shift
constancy): within-pair / global constant shift k = oc - ic at the
|ic| == |oc| cell. This matcher fires => per-group shift k == 0 on
every group (C -> C). Iter 199 strict-implies this matcher only at
the k == 0 cell with |ic| == |oc| == 1 AND cross-group identity; in
general iter 198 / 199 admit k != 0 cells that fail this matcher.

Strict relation to iter 200-206 (per-group palette-relation cells):
this matcher STRICTLY IMPLIES iter 201 (per-group set-equality, the
strict-implication direction described above). The other six per-
group palette-relation cells are STRICTLY MUTUALLY EXCLUSIVE with
this matcher on the |ic| == |oc| == 1 row -- on the singleton row
with ic == oc, only iter 201 admits.

Why a distinct matcher rather than just AND-ing iter 216 with "C ==
K" at the rule level: the matcher contract (docs/RULE_FORMAT.md §4)
is name-keyed recognition vocabulary; the rule's stored ``condition.
type`` is the recognition handle's name, not a Boolean composition
tree with equality predicates over rule parameters. A rule whose
precondition is "single global recolour C -> C" gates a DIFFERENT
rule family (whole-task identity-on-singleton, the no-op recolour
expressed via the change-group structure) than iter 216 alone
(whole-task bijective singleton admitting both C == K and C != K).
Keeping the conjunction as a separate registry slot lets anti-
unification (CLAUDE.md §8) attach the right gate per rule family --
specifically the gate for rules whose action is "do nothing,
expressed as the singleton recolour C -> C" -- without rediscovering
the C == K predicate from the rule's stored action shape.

Why a distinct matcher rather than parameterising iter 216 with an
``identity_only: True`` flag: the matcher contract is name-keyed
recognition vocabulary; the rule's stored ``condition.type`` is the
recognition handle's name, not a name+params tuple. The identity
sub-cell of iter 216 is structurally identifiable as the intersection
of iter 216 (whole-task bijective singleton) and the additional C ==
K predicate; it is a recognition handle in its own right (the
simplest whole-task singleton-blob identity-rule cell), not a
Boolean parameter of the bijective-singleton axis.

Why this matters as the whole-task projection of iter 217: iter 217
names the per-group singleton-blob identity cell (per-group ic == oc
with per-group fixed points possibly varying across groups). This
matcher names the whole-task singleton-blob identity cell (one
global fixed point C across all groups in all pairs). The two are
co-located on the identity-rule-family axis but at different
resolutions:

  * (per-group, per-group fixed point possibly varying)         -- iter 217 (per-group identity).
  * (whole-task, single global fixed point C)                   -- THIS matcher (whole-task identity).
  * (per-group, no constraint on per-group fixed-point matching) -- iter 215 (per-group bijective
                                                                     singleton, admits both ident-
                                                                     ity and non-identity).
  * (whole-task, no constraint on C vs K)                       -- iter 216 (whole-task bijective
                                                                     singleton, admits both C == K
                                                                     and C != K).

With this matcher landed, the identity sub-cell of iter 216 is a
first-class recognition handle, parallel to iter 217 being the
identity sub-cell of iter 215.

Strict refinement / orthogonality summary (universal-over-groups-
and-pairs semantics, whole-task |ic| == |oc| == 1 + cross-group
identity + C == K):

  * Iter 216 (``singleton_recolor``) -- STRICT REFINEMENT (this
    matcher additionally requires C == K).
  * Iter 217 (``singleton_recolor_identity_per_group``) -- STRICT
    REFINEMENT (this matcher additionally requires cross-group
    identity on both sides; iter 217 admits per-group fixed points
    varying across groups).
  * Iter 218 (``singleton_recolor_nonidentity_per_group``) --
    STRICT MUTUAL EXCLUSION. Iter 218 fires iff every group has
    ic != oc as singletons; this matcher fires iff every group has
    ic == oc == [C] as singletons with the global fixed point C.
    Pairwise disjoint named cells.
  * Iter 14 (``input_color_uniform``) -- STRICT REFINEMENT (this
    matcher additionally requires the output side to collapse to
    the SAME singleton).
  * Iter 18 (``output_color_uniform``) -- STRICT REFINEMENT (this
    matcher additionally requires the input side to collapse to
    the SAME singleton).
  * Iter 215 (``singleton_recolor_per_group``) -- STRICT
    REFINEMENT (per-group |ic| == |oc| == 1 is a precondition;
    cross-group identity AND C == K is additionally required).
  * Iter 213 / iter 214 -- STRICTLY IMPLIED.
  * Iter 8 (``consistent_color_mapping``) -- STRICT REFINEMENT
    (the implied global mapping is the singleton map {C -> C}).
  * Iter 13 (``identity_transformation``) -- STRICT MUTUAL
    EXCLUSION. Together with iter 13 (and with iter 217 at the
    per-group resolution) they form THREE disjoint identity-rule-
    family preconditions on the (#groups, cross-group-identity)
    lattice.
  * Iter 10 (``sequential_recoloring``) -- INDEPENDENT in general;
    co-fires only on the degenerate length-1-range cell that
    coincides with this matcher's territory.
  * Iter 195 / 196 / 197 (per-group cardinality matchers) --
    STRICTLY IMPLIED at K == K == K_prod == 1. Cross-pair
    constancy at K == 1 is subsumed by universal-over-pairs
    semantics here.
  * Iter 198 / 199 (per-group palette-shift constancy) -- this
    matcher implies per-group shift k == 0 on every group (C -> C
    reduces to a zero shift). Co-fires only on the iter 198 / 199
    k == 0 cell with |ic| == |oc| == 1 AND cross-group identity.
  * Iter 201 (``output_colors_equals_input_colors_per_group``) --
    STRICTLY IMPLIED (per-group ic == oc on every group). The
    converse fails on |ic| > 1 cells.
  * Iter 200 / 202 / 203 / 204 / 205 / 206 (per-group palette-
    relation cells) -- STRICTLY MUTUALLY EXCLUSIVE with this
    matcher on the |ic| == |oc| == 1 row.
  * Every cell- / position- / dimension-axis matcher -- orthogonal
    to whole-task singleton identity.

Why this matters for ARBOR's intended ruleset:

  * "Whole-task identity-on-singleton" rule family -- rules whose
    action is the no-op singleton recolour C -> C with one global
    fixed point C determinable from training as a constant. The
    simplest rule shape on the identity-rule-family axis at the
    whole-task scope (rivalling iter 13's no-blob identity at the
    #groups == 0 cell); the building block from which more
    complex global identity-preserving rules (e.g. "preserve the
    global singleton AND modify everything else") generalise.
    This matcher names the precondition for that rule family, in
    a single registry slot, so anti-unification can attach the
    right gate to rules of this shape without having to
    rediscover the iter 216 ∧ "C == K" intersection each time.
  * Closes the iter-218-named candidate (viii): "the whole-task
    projection of iter 217 at the iter 216 ∧ 'C == K globally'
    cell -- a single matcher pinning |ic| == |oc| == 1 AND cross-
    group identity on both sides AND C == K globally". With this
    matcher landed, the iter-216 whole-task bijective-singleton-
    recolour axis is named at two disjoint sub-cells: identity
    C == K (this matcher) AND non-identity C != K (iter 216 minus
    this matcher; the iter-218-named candidate (x) at the whole-
    task scope, the closest-fitting sibling candidate freshly
    opened by this iter and the natural next iter's target). The
    previously-implicit conjunction (iter 216 AND "C == K
    globally") is now a first-class recognition handle.

Params:
  (none) -- pure whole-task global singleton-identity check,
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
    200-206 / 213 / 214 / 215 / 217 / 218 strict-type posture),
    AND
  - for every group, ``len(set(input_colors)) == 1`` AND
    ``len(set(output_colors)) == 1``, AND
  - all single input colours across all groups in all pairs are
    bit-identical to one global C, AND
  - all single output colours across all groups in all pairs are
    bit-identical to one global K, AND
  - C == K (the whole-task fixed-point sub-cell of iter 216).

Why fail-closed on empty / no-group / malformed (same posture as
iter 8 / 13 / 14 / 18 / 30 / 32 / 33 / 34 / 35 / 36 / 37 / 38 / 39 /
184-218): a missing or zero-group pair is upstream extractor
breakage or iter 13's no-blob-identity territory; a whole-task
single-global-identity claim with zero observations is meaningless,
AND admitting it would collapse this matcher's territory into iter
13's (the two are designed as disjoint cells on the #groups axis).

Why ``input_colors`` and ``output_colors`` both required non-empty
lists per group (``len >= 1``): a connected change group has at
least one cell; each cell has both an input colour and an output
colour; the per-group ``input_colors`` / ``output_colors`` fields
are the sorted unique sets of those colours, which are non-empty
for any non-empty group.

Why strict per-colour validation (bool rejected, range checked):
``input_colors`` / ``output_colors`` carry small ints in [0, 9];
the matcher performs the same strict-type gating as iter 14 / 18 /
19 / 34 / 35 / 36 / 37 / 38 / 184-218 to keep contract violations
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


@register("singleton_recolor_identity")
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
        and observed_input_colors == observed_output_colors
    )
