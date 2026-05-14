"""
singleton_recolor_nonidentity_per_group -- match tasks where EVERY change
group of EVERY example pair has BOTH ``len(set(input_colors)) == 1``
AND ``len(set(output_colors)) == 1`` AND ``set(input_colors) !=
set(output_colors)`` -- i.e. each group's input AND output sides are
pinned to a singleton AND those two singletons are DIFFERENT colours.
The STRICT COMPLEMENT of iter 217 (``singleton_recolor_identity_per_
group``) within iter 215's (``singleton_recolor_per_group``) territory.

Recognition vocabulary axis: the per-group non-identity-singleton-
recolour cell. Iter 215 names the per-group bijective-singleton-
recolour cell (per-group |ic| == |oc| == 1, with the per-group source
colour C_g and target colour K_g possibly equal OR differing -- i.e.
C_g -> K_g for any K_g). Iter 217 names the per-group fixed-point-on-
singleton sub-cell where every group has K_g == C_g (the per-group
identity-on-singleton cell). This matcher names the STRICT COMPLEMENT
sub-cell where every group has K_g != C_g (the per-group TRUE-recolour
on singletons cell). Iter 217 union with this matcher = iter 215
within iter 215's territory; the two are pairwise disjoint named cells
of the iter-215 bijective-singleton-recolour axis.

This matcher names the precondition for the rule family "per-group
singleton-cells are TRUE RECOLOURS C_g -> K_g with K_g != C_g": rules
whose per-group action is a real recolour from one singleton source
to a strictly different singleton target. Iter 217 names the no-op
sub-cell (every group is the identity on its singleton); this matcher
names the action-shape-differs sub-cell (every group is a true
recolour on its singleton). Naming the two halves of iter 215 as
separate registry slots lets anti-unification gate the per-group
recolour-action family without ambiguity: the action-shape "C_g ->
K_g with K_g possibly equal to C_g" of iter 215 splits into "C_g ->
C_g" (iter 217's identity action) and "C_g -> K_g with K_g != C_g"
(this matcher's true-recolour action), each of which is a single-
shape action family.

Strict relations to iter 215 / iter 217 (the immediate parents):

  * Iter 215 (``singleton_recolor_per_group``): STRICT REFINEMENT.
    This matcher fires => iter 215 fires (per-group |ic| == |oc| ==
    1 is a precondition of this matcher). The converse fails on a
    task where some group has ic == oc as singletons: iter 215 fires
    (both sides singletons), this matcher rejects (the per-group
    singletons are not strictly different).
  * Iter 217 (``singleton_recolor_identity_per_group``): STRICT
    MUTUAL EXCLUSION. Iter 217 fires iff every group has ic == oc as
    singletons; this matcher fires iff every group has ic != oc as
    singletons. The two cells are pairwise disjoint by the per-group
    ic == oc vs ic != oc split on the iter-215 bijective-singleton
    territory. Within iter 215's territory they partition exhaustively
    iff every group across all pairs is consistently either ic == oc
    or ic != oc; otherwise BOTH this matcher AND iter 217 reject on
    the mixed-cell task (e.g. one group with ic == oc and another
    with ic != oc), demonstrating that iter 217 ∪ this matcher is a
    PROPER subset of iter 215's territory (iter 215 also fires on
    mixed-cell tasks that neither named cell admits).

So this matcher is the STRICT COMPLEMENT of iter 217 within iter
215's territory IF the per-group classification is uniform across all
groups in all pairs. The strict-complement sub-cell admits exactly
the per-group true-recolour singletons (every group is a strict
recolour C_g -> K_g with K_g != C_g, with C_g and K_g possibly
varying across groups).

Strict relation to iter 13 (``identity_transformation``): STRICT
MUTUAL EXCLUSION. Iter 13 fires iff every pair has ZERO change
groups (whole-task no-blob identity). This matcher REJECTS the no-
group case (universal-over-groups requires at least one group per
pair, mirroring iter 215 / 217 identity-territory rejection). Iter
13 is the whole-task no-blob identity (the (#groups == 0, *) cell);
iter 217 is the per-group singleton-blob identity (the (#groups >=
1, |ic| == |oc| == 1 AND ic == oc) cell); this matcher is the per-
group singleton-blob non-identity (the (#groups >= 1, |ic| == |oc|
== 1 AND ic != oc) cell). Together with iter 13 and iter 217 they
name THREE disjoint cells on the (#groups, #cells-per-group, ic-vs-
oc) lattice for the singleton rows.

Strict relation to iter 14 (``input_color_uniform``) AND iter 18
(``output_color_uniform``) jointly: iter 14 ∧ iter 18 ∧ "C != K
globally" => this matcher fires. Iter 14 fires => per-pair every
group has |ic| == 1 AND all ic singletons cross-group bit-identical
to one global C; iter 18 fires => per-pair every group has |oc| ==
1 AND all oc singletons cross-group bit-identical to one global K.
The conjunction iter 14 ∧ iter 18 fires iff |ic| == |oc| == 1 per
group AND the two global constants C, K exist. This matcher
additionally requires C != K per group (which on the iter 14 ∧ iter
18 territory reduces to "C != K globally"). So iter 14 ∧ iter 18 ∧
"C != K globally" implies this matcher; the converse fails when
per-group ic != oc cycles through different (C_g, K_g) singleton
pairs across groups (this matcher fires, iter 14 / 18 reject). The
whole-task projection of this matcher is iter 216 (``singleton_
recolor``) RESTRICTED to C != K globally.

Strict relation to iter 216 (``singleton_recolor``): INDEPENDENT in
general (decoupled on the (cross-group identity, per-group non-
identity) product axis). Iter 216 pins WHOLE-TASK |ic| == |oc| == 1
AND cross-group identity on both sides (single global C, K across
all groups in all pairs), with C possibly == K OR != K. This
matcher pins PER-GROUP |ic| == |oc| == 1 AND per-group C_g != K_g,
with the per-group (C_g, K_g) pairs possibly varying across groups.
The two matchers co-fire when |ic| == |oc| == 1 per group AND cross-
group identity AND C != K globally (the whole-task non-identity-on-
singleton cell); the two matchers decouple when:

  * Iter 216 fires alone: cross-group identity with C == K (single
    global C == K, the iter-217-canonical whole-task identity-on-
    singleton cell -- iter 216 admits BOTH identity and non-
    identity, this matcher rejects identity). This matcher rejects
    (per-group ic == oc).
  * This matcher fires alone: per-group (C_g, K_g) varying across
    groups (e.g. group A has ic=[3] oc=[0]; group B has ic=[5]
    oc=[7]). Iter 216 rejects (cross-group identity fails: input
    singletons differ across groups).

Strict relation to iter 8 (``consistent_color_mapping``): co-fires
with this matcher on patterns where every group is a per-group
true-recolour singleton AND the whole-task forward (ic -> oc) cross-
product is function-shaped. INDEPENDENT in general (iter 8 admits
per-group |ic| > 1 mappings that are function-shaped; this matcher
pins per-group |ic| == 1 with strict ic != oc). With every per-
group action being a (C_g, K_g) singleton pair, the per-pair (ic,
oc) cross-product is exactly {(C_g, K_g) : g in groups}, which is
function-shaped iff no two groups in the same pair share the same
C_g with different K_g.

Strict relation to iter 213 (``consistent_color_mapping_per_group``):
STRICT REFINEMENT (iter 213 demands per-group |oc| == 1 only; this
matcher additionally demands per-group |ic| == 1 AND per-group ic
!= oc as singletons). With every per-group |ic| == |oc| == 1 AND
ic != oc, iter 213 also fires (per-group |oc| == 1 is satisfied
trivially). The converse fails on a task with per-group |oc| == 1
but per-group |ic| > 1 (iter 213 fires; this matcher rejects).

Strict relation to iter 214 (``input_color_uniform_per_group``):
STRICT REFINEMENT (iter 214 demands per-group |ic| == 1 only; this
matcher additionally demands per-group |oc| == 1 AND per-group ic
!= oc as singletons). With every per-group |ic| == |oc| == 1 AND
ic != oc, iter 214 also fires. Converse fails on per-group |ic| ==
1 with |oc| > 1.

Strict relation to iter 195 / 196 / 197 (per-group cardinality
matchers): this matcher fires => iter 195 fires at per-group K_in
== 1 (input cardinality) AND iter 196 fires at per-group K_out ==
1 (output cardinality) AND iter 197 fires at K_prod == 1 (product).
The converse for each fails (K != 1 cells, OR K == 1 with per-
group ic == oc).

Strict relation to iter 198 / 199 (per-group palette-shift constancy):
within-pair / global constant shift k = oc - ic at the |ic| == |oc|
cell. This matcher fires => per-group shift is k != 0 on every
group (C -> K with K != C reduces to a non-zero shift). Iter 198
/ 199 strict-imply this matcher only at the |ic| == |oc| == 1
non-zero-shift cell; in general iter 198 / 199 admit k == 0 AND
|ic| == |oc| > 1 cells that fail this matcher.

Strict relation to iter 200-206 (per-group palette-relation cells):
iter 200 (subset), iter 201 (set-equality, iter-217's parent), iter
202 (input proper-subset-of-output), iter 203 (disjoint), iter 204
(output proper-subset-of-input), iter 205 (input proper-subset-of-
output strict), iter 206 (output / input partial overlap). This
matcher STRICTLY IMPLIES iter 203 (disjoint: on the singleton row
ic != oc forces ic ∩ oc == ∅, since both are 1-element sets); the
other six per-group palette-relation cells are STRICTLY MUTUALLY
EXCLUSIVE with this matcher on the |ic| == |oc| == 1 row -- iter
201 (set-equality) is mutually exclusive (would require ic == oc);
iter 200 / 202 / 204 / 205 reduce to either equality or disjoint on
the singleton row, both of which are decided already; iter 206
(partial overlap) requires both non-empty intersection AND non-
empty difference, impossible on the singleton row with disjoint
singletons.

Strict relation to iter 10 (``sequential_recoloring``): per-group
|oc| == 1 with singletons forming a contiguous range. INDEPENDENT
in general of the per-group non-identity claim. Co-fires on the
iter-10 canonical fixture (every group has |ic| == |oc| == 1 with
ic != oc, and the per-pair oc singletons form a contiguous range);
decouples when this matcher fires on non-contiguous oc singletons.

Why a distinct matcher rather than just AND-ing iter 215 with NOT
iter 217 at the rule level: the matcher contract (docs/RULE_FORMAT.
md §4) is name-keyed recognition vocabulary; the rule's stored
``condition.type`` is the recognition handle's name, not a Boolean
composition tree with negation. A rule whose precondition is "per-
group |ic| == |oc| == 1 AND ic != oc" gates a DIFFERENT rule
family (per-group true-recolour-on-singleton, the strict-recolour
on singleton blobs) than either iter 215 alone (per-group bijective-
singleton admitting BOTH identity and non-identity) or iter 217
alone (per-group identity-on-singleton, the no-op recolour). The
NOT iter 217 conjunction also forbids registry-level expression
of "per-group strict recolour" without an additional negation
primitive in the rule-condition language; keeping this matcher as
a separate registry slot lets anti-unification (CLAUDE.md section
8) attach the right gate per rule family -- specifically the gate
for rules whose per-group action is "recolour C_g to a strictly
different K_g" -- without negation primitives.

Why a distinct matcher rather than parameterising iter 215 with a
``nonidentity_only: True`` flag: the matcher contract is name-keyed
recognition vocabulary; the rule's stored ``condition.type`` is the
recognition handle's name, not a name+params tuple. The non-identity
sub-cell of iter 215 is structurally identifiable as the strict
complement of iter 217 within iter 215's territory; it is a
recognition handle in its own right (the simplest per-group true-
recolour cell), not a Boolean parameter of the bijective-singleton
axis.

Why this matters as the strict complement of iter 217 within iter
215: with iter 217 naming the per-group identity-on-singleton cell
and this matcher naming the per-group true-recolour-on-singleton
cell, the iter-215 bijective-singleton axis is now named at two
disjoint resolutions: identity (iter 217) AND non-identity (this
matcher). The previously-implicit "every blob is a STRICT recolour
on its singleton" cell is now a first-class recognition handle.

Strict refinement / orthogonality summary (universal-over-groups-
and-pairs semantics, per-group |ic| == |oc| == 1 AND ic != oc):

  * Iter 215 (``singleton_recolor_per_group``) -- per-group |ic| ==
    |oc| == 1. STRICT REFINEMENT (this matcher additionally requires
    per-group ic != oc as singletons).
  * Iter 217 (``singleton_recolor_identity_per_group``) -- per-group
    |ic| == |oc| == 1 AND ic == oc. STRICT MUTUAL EXCLUSION (this
    matcher demands ic != oc on every group; iter 217 demands ic ==
    oc on every group). Within iter 215's bijective-singleton
    territory, iter 217 and this matcher are pairwise disjoint
    named cells.
  * Iter 213 (``consistent_color_mapping_per_group``) -- per-group
    |oc| == 1. STRICT REFINEMENT (this matcher additionally
    requires per-group |ic| == 1 AND ic != oc).
  * Iter 214 (``input_color_uniform_per_group``) -- per-group |ic|
    == 1. STRICT REFINEMENT (this matcher additionally requires
    per-group |oc| == 1 AND ic != oc).
  * Iter 13 (``identity_transformation``) -- STRICT MUTUAL
    EXCLUSION. Iter 13 fires iff every pair has zero change groups;
    this matcher requires at least one change group per pair.
  * Iter 216 (``singleton_recolor``) -- INDEPENDENT in general. Co-
    fires only on cross-group-identity whole-task non-identity
    singletons (single global C != K); decouples when iter 216
    fires alone (C == K, iter-217 territory) or when this matcher
    fires alone (per-group fixed (C_g, K_g) varying across groups).
  * Iter 8 (``consistent_color_mapping``) -- INDEPENDENT in general.
    Co-fires when the per-pair (ic, oc) cross-product is function-
    shaped (no two groups in the same pair share C_g with different
    K_g).
  * Iter 10 (``sequential_recoloring``) -- INDEPENDENT in general
    (iter 10's per-group oc-range-contiguity claim is independent
    of the per-group non-identity claim); co-fires on the iter-10
    canonical fixture.
  * Iter 14 ∧ iter 18 (jointly) -- this matcher's CROSS-GROUP-
    IDENTITY refinement (drops per-group flexibility). With cross-
    group identity AND ic != oc globally, the whole-task singleton-
    true-recolour cell. STRICT IMPLICATION direction (iter 14 ∧
    iter 18 ∧ "C != K globally" implies this matcher); converse
    fails on per-group (C_g, K_g) pairs varying across groups.
  * Iter 195 / 196 / 197 (per-group cardinality matchers) -- this
    matcher implies iter 195 at K_in == 1, iter 196 at K_out == 1,
    iter 197 at K_prod == 1. Cross-pair constancy at K == 1 is
    subsumed by universal-over-pairs semantics here.
  * Iter 198 / 199 (per-group palette-shift constancy) -- this
    matcher implies per-group shift k != 0 on every group (C -> K
    with K != C). Co-fires only on the iter 198 / 199 k != 0 cell
    with |ic| == |oc| == 1.
  * Iter 201 (``output_colors_equals_input_colors_per_group``) --
    per-group set(ic) == set(oc). STRICT MUTUAL EXCLUSION (this
    matcher demands per-group ic != oc; iter 201 demands per-group
    ic == oc).
  * Iter 203 (``output_colors_disjoint_from_input_colors_per_
    group``) -- per-group set(ic) ∩ set(oc) == ∅. STRICTLY IMPLIED
    by this matcher (on the singleton row, ic != oc forces ic ∩ oc
    == ∅). Converse fails when iter 203 fires with |ic| > 1 OR
    |oc| > 1.
  * Iter 200 / 202 / 204 / 205 / 206 (per-group palette-relation
    cells) -- five other cells of the per-group palette-relation
    sub-axis. STRICTLY MUTUALLY EXCLUSIVE with this matcher on
    the |ic| == |oc| == 1 row (the only co-firing cell besides
    iter 203 is iter 200's restriction to the singleton-disjoint
    territory, which reduces to iter 203 there).
  * Every cell- / position- / dimension-axis matcher (iters 1 / 17
    / 19 / 20 / 22 / 23 / 24 / 26 / 28 / 32 / 33 / 38 / 39 / 40 /
    41 / 42 / 182 / 183 / 184 / 185 / 186 / 187 / 188 / 189 / 190
    / 191 / 210 / 211 / 212) -- orthogonal to per-group singleton-
    true-recolour.

Why this matters for ARBOR's intended ruleset:

  * "Per-group true-recolour-on-singleton" rule family -- rules
    whose per-group action is a strict recolour C_g -> K_g with K_g
    != C_g on every group's singleton. The simplest non-trivial
    per-group recolour rule shape (rivalling iter 217's per-group
    identity); the building block from which more complex per-group
    strict-recolour rules generalise. This matcher names the
    precondition for that rule family, in a single registry slot,
    so anti-unification can attach the right gate to rules of this
    shape without having to rediscover the intersection each time.
    The action-shape "C_g -> K_g" with K_g != C_g admits per-group
    parameters {C_g, K_g} but rules out the no-op identity (which
    iter 217's action-shape "C_g -> C_g" admits exclusively); the
    two action-shapes are disjoint and gate disjoint rule families.
  * Closes the iter-217-named candidate (ix): "a single matcher
    pinning per-group |ic| == |oc| == 1 AND per-group ic != oc
    (the strict complement of iter 217 within iter 215's territory,
    naming the precondition for rules whose per-group action is a
    TRUE recolour C_g -> K_g with K_g != C_g)". With this matcher
    landed, the iter-215 bijective-singleton axis is named at two
    disjoint sub-cells: identity (iter 217) AND non-identity (this
    matcher). The previously-implicit conjunction (iter 215 AND
    "per-group ic != oc") is now a first-class recognition handle.

Params:
  (none) -- pure per-group non-identity-singleton check, universal
  over groups and pairs.

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
    200-206 / 213 / 214 / 215 / 217 strict-type posture), AND
  - for every group, ``len(set(input_colors)) == 1`` AND
    ``len(set(output_colors)) == 1`` AND
    ``set(input_colors) != set(output_colors)`` -- the per-group
    non-identity-on-singleton cell.

Why fail-closed on empty / no-group / malformed (same posture as
iter 8 / 13 / 14 / 18 / 30 / 32 / 33 / 34 / 35 / 36 / 37 / 38 / 39 /
184-217): a missing or zero-group pair is upstream extractor
breakage or iter 13's no-blob-identity territory; a per-group
singleton-true-recolour claim with zero observations is
meaningless, AND admitting it would collapse this matcher's
territory into iter 13's (the two are designed as disjoint cells
on the #groups axis).

Why ``input_colors`` and ``output_colors`` both required non-empty
lists per group (``len >= 1``): a connected change group has at
least one cell; each cell has both an input colour and an output
colour; the per-group ``input_colors`` / ``output_colors`` fields
are the sorted unique sets of those colours, which are non-empty
for any non-empty group. A zero-length colour list is an
extractor contract violation, not a valid empty-set singleton-
true-recolour case.

Why strict per-colour validation (bool rejected, range checked):
``input_colors`` / ``output_colors`` carry small ints in [0, 9];
the matcher performs the same strict-type gating as iter 14 / 18 /
19 / 34 / 35 / 36 / 37 / 38 / 184-217 to keep contract violations
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


@register("singleton_recolor_nonidentity_per_group")
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
    return True
