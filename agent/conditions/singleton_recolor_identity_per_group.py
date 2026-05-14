"""
singleton_recolor_identity_per_group -- match tasks where EVERY change
group of EVERY example pair has BOTH ``len(set(input_colors)) == 1``
AND ``len(set(output_colors)) == 1`` AND ``set(input_colors) ==
set(output_colors)`` -- i.e. each group's input side AND output side
are pinned to a singleton AND those two singletons are the SAME colour.
The CO-FIRE conjunction of iter 215 (``singleton_recolor_per_group``,
the per-group |ic| == |oc| == 1 cell) AND iter 201 (``output_colors_
equals_input_colors_per_group``, the per-group set-equality cell).

Recognition vocabulary axis: the per-group fixed-point-on-singleton
cell. Iter 215 names the per-group bijective-singleton-recolour cell
(per-group |ic| == |oc| == 1, with the per-group source colour C_g and
target colour K_g possibly differing -- i.e. C_g -> K_g for some
K_g, where K_g may or may not equal C_g). Iter 201 names the per-
group set-equality cell (per-group ``set(ic) == set(oc)``, with the
per-group |ic| = |oc| possibly any value >= 1). This matcher names
the INTERSECTION cell where BOTH constraints simultaneously hold: per-
group |ic| == |oc| == 1 AND per-group ic == oc. With both singletons
pinned and the two singletons set-equal, the per-group action is
forced to the no-op identity on the singleton (C_g -> C_g, with the
per-group fixed point C_g).

This matcher names the precondition for the rule family "per-group
singleton-cells are FIXED POINTS of the recolour": rules whose per-
group action is the no-op identity on every group's single source
colour. The whole-task analogue (zero change groups) is iter 13
(``identity_transformation``); this matcher is its per-group singleton
analogue (every change group is itself an identity on its singleton).

Strict relations to iter 215 / iter 201 (the immediate parents):

  * Iter 215 (``singleton_recolor_per_group``): STRICT REFINEMENT.
    This matcher fires => iter 215 fires (per-group |ic| == |oc| ==
    1 is a precondition of this matcher). The converse fails on a
    task with |ic| == |oc| == 1 per group but with ic != oc in some
    group: iter 215 fires (both sides are singletons), this matcher
    rejects (the singletons differ, i.e. it's a non-identity per-
    group recolour like C -> K with K != C).
  * Iter 201 (``output_colors_equals_input_colors_per_group``):
    STRICT REFINEMENT. This matcher fires => iter 201 fires (per-
    group ``set(ic) == set(oc)`` is a precondition of this matcher).
    The converse fails on a task with per-group set-equality but with
    |ic| > 1 in some group: iter 201 fires (e.g. ic = oc = [3, 4]),
    this matcher rejects (cardinality > 1).

So this matcher is the STRICT CONJUNCTION (logical AND) of iter 215
and iter 201. The pair-completion of the per-group bijective-
singleton-recolour axis closed at the fixed-point cell: iter 215
names the bijective-singleton cell admitting C_g -> K_g for any K_g
(including K_g != C_g); iter 201 names the per-group set-equality
cell admitting any cardinality. This matcher names the cell where
BOTH constraints pin simultaneously -- the per-group singleton
fixed-point cell.

Strict relation to iter 13 (``identity_transformation``): STRICT
MUTUAL EXCLUSION. Iter 13 fires iff every pair has ZERO change
groups (whole-task identity, no-blob case). This matcher REJECTS the
no-group case (universal-over-groups requires at least one group per
pair, mirroring iter 215 / 201 / 213 / 214 identity-territory
rejection). Iter 13 is the whole-task no-blob identity; this matcher
is the per-group singleton-blob identity. The two are the two
disjoint identity-rule-family preconditions on the (#groups, #cells-
per-group) lattice: iter 13 occupies the (0, *) row; this matcher
occupies the (>=1, 1) per-group cell where every group is itself an
identity on its singleton. Together with iter 13 they name the two
disjoint identity-rule-family preconditions; with this matcher landed
they form a complete two-cell axis where the per-group rule-action
is the identity (rather than a true recolour C -> K with K != C).

Strict relation to iter 14 (``input_color_uniform``) AND iter 18
(``output_color_uniform``) jointly: iter 14 ∧ iter 18 ∧ "every per-
group ic equals the corresponding per-group oc as singletons" => this
matcher fires. Iter 14 fires => per-pair every group has |ic| == 1
AND all ic singletons cross-group bit-identical to one global C; iter
18 fires => per-pair every group has |oc| == 1 AND all oc singletons
cross-group bit-identical to one global K. The conjunction iter 14
∧ iter 18 fires iff |ic| == |oc| == 1 per group AND the two global
constants C, K exist. This matcher additionally requires C == K
per group (which on the iter 14 ∧ iter 18 territory reduces to "C ==
K globally"). So iter 14 ∧ iter 18 ∧ "C == K" implies this matcher;
the converse fails when per-group ic == oc cycles through different
singleton colours across groups (this matcher fires, iter 14 / 18
reject). With C == K globally on the iter 14 ∧ iter 18 territory,
the whole-task recolour shape is C -> C -- the iter 13-canonical
identity expressed as a one-singleton recolour. This is the WHOLE-
TASK cell of iter 216 (``singleton_recolor``) projected onto the
identity row; iter 216 admits C != K, this matcher's whole-task
projection pins C == K.

Strict relation to iter 216 (``singleton_recolor``): INDEPENDENT in
general (decoupled on the (cross-group identity, per-group fixed-
point) product axis). Iter 216 pins WHOLE-TASK |ic| == |oc| == 1 AND
cross-group identity on both sides (single global C, K across all
groups in all pairs), with C possibly != K. This matcher pins PER-
GROUP |ic| == |oc| == 1 AND per-group C_g == K_g, with the per-
group fixed points C_g possibly varying across groups. The two
matchers co-fire when |ic| == |oc| == 1 per group AND cross-group
identity AND C == K (the whole-task identity-on-singleton cell);
the two matchers decouple when:

  * Iter 216 fires alone: cross-group identity with C != K (single
    global C, single global K, with K != C; e.g. every group is
    recoloured 3 -> 0). This matcher rejects (per-group ic != oc).
  * This matcher fires alone: per-group fixed points with C_g
    varying across groups (e.g. group A has ic = oc = [3]; group B
    has ic = oc = [5]). Iter 216 rejects (cross-group identity
    fails: input singletons differ across groups).

Strict relation to iter 8 (``consistent_color_mapping``): co-fires
with this matcher on patterns where every group is a per-group
fixed-point singleton AND the whole-task forward (ic -> oc) cross-
product is function-shaped. INDEPENDENT in general (iter 8 admits
per-group |ic| > 1 mappings that are function-shaped; this matcher
pins per-group |ic| == 1 with the per-group fixed point). With every
per-group action being ic = oc = [C_g] singletons, the per-pair
(ic, oc) cross-product is exactly {(C_g, C_g) : g in groups},
which is trivially function-shaped (forward C_g -> C_g for each g).
So this matcher fires => the per-pair (ic, oc) cross-product is
function-shaped, which co-fires with iter 8.

Strict relation to iter 213 (``consistent_color_mapping_per_group``):
STRICT REFINEMENT (iter 213 demands per-group |oc| == 1 only; this
matcher additionally demands per-group |ic| == 1 AND per-group ic ==
oc as singletons). With every per-group |ic| == |oc| == 1 AND ic ==
oc, iter 213 also fires (per-group |oc| == 1 is satisfied trivially).
The converse fails on a task with per-group |oc| == 1 but per-group
|ic| > 1 (iter 213 fires; this matcher rejects).

Strict relation to iter 214 (``input_color_uniform_per_group``):
STRICT REFINEMENT (iter 214 demands per-group |ic| == 1 only; this
matcher additionally demands per-group |oc| == 1 AND per-group ic ==
oc as singletons). With every per-group |ic| == |oc| == 1 AND ic ==
oc, iter 214 also fires. Converse fails on per-group |ic| == 1 with
|oc| > 1.

Strict relation to iter 195 / 196 / 197 (per-group cardinality
matchers): this matcher fires => iter 195 fires at per-group K_in
== 1 (input cardinality) AND iter 196 fires at per-group K_out == 1
(output cardinality) AND iter 197 fires at K_prod == 1 (product).
The converse for each fails (K != 1 cells). INDEPENDENT cross-pair
constancy claims in iter 195 / 196 / 197 are subsumed here by
universal-over-pairs semantics (per-group K_in == 1 AND K_out == 1
on every pair => K_in / K_out / K_prod constants across pairs at 1).

Strict relation to iter 198 / 199 (per-group palette-shift constancy):
within-pair / global constant shift k = oc - ic at the |ic| == |oc|
cell. This matcher fires => per-group shift is k == 0 on every group
(C -> C reduces to a zero shift). Iter 198 / 199 strict-imply this
matcher only at the k == 0 cell with |ic| == |oc| == 1 (the trivial
zero-shift singleton); in general iter 198 / 199 admit k != 0 and
|ic| == |oc| > 1 cells that fail this matcher.

Strict relation to iter 200-206 (per-group palette-relation cells):
iter 200 (subset), iter 201 (set-equality, the immediate parent),
iter 202 (input proper-subset-of-output), iter 203 (disjoint), iter
204 (output proper-subset-of-input), iter 205 (input proper-subset-
of-output strict), iter 206 (output / input partial overlap). This
matcher STRICTLY IMPLIES iter 201 (set-equality is the precondition);
the other six per-group palette-relation cells are STRICTLY MUTUALLY
EXCLUSIVE with this matcher on the |ic| == |oc| == 1 row -- on the
singleton row, the seven palette-relation cells reduce to only two
that admit a consistent assignment: equality (ic == oc) and disjoint
(ic != oc). This matcher is the equality cell on the singleton row;
iter 203 restricted to the |ic| == |oc| == 1 row is the disjoint
cell on the singleton row.

Strict relation to iter 10 (``sequential_recoloring``): per-group
|oc| == 1 with singletons forming a contiguous range. With per-group
ic == oc as singletons, the per-group oc singletons trivially co-
form whatever range the per-group ic singletons form; iter 10 fires
iff the per-group oc range is contiguous, which is INDEPENDENT of
this matcher's per-group fixed-point claim. The two matchers co-
fire on tasks like ic = oc = [3] in group A, [4] in group B, [5] in
group C (the per-group fixed points form a contiguous range);
decouple on non-contiguous fixed points (this matcher fires; iter 10
rejects on non-contiguous singletons).

Why a distinct matcher rather than just AND-ing iter 215 with iter
201 at the rule level: the matcher contract (docs/RULE_FORMAT.md §4)
is name-keyed recognition vocabulary; the rule's stored ``condition.
type`` is the recognition handle's name, not a Boolean composition
tree. A rule whose precondition is "per-group |ic| == |oc| == 1 AND
ic == oc" gates a DIFFERENT rule family (per-group identity-on-
singleton, the no-op recolour on singleton blobs) than either iter
215 alone (per-group bijective-singleton with possibly K != C) or
iter 201 alone (per-group set-equality with possibly |ic| > 1).
Keeping the conjunction as a separate registry slot lets anti-
unification (CLAUDE.md section 8) attach the right gate per rule
family -- specifically the gate for rules whose per-group action is
"do nothing within this group" -- without having to rediscover the
intersection from the rule's stored action shape.

Why a distinct matcher rather than parameterising iter 215 with a
``identity_only: True`` flag (mirroring the iter-215 / iter-216
parameterless-cell precedent): the matcher contract is name-keyed
recognition vocabulary; the rule's stored ``condition.type`` is the
recognition handle's name, not a name+params tuple. The fixed-point
cell of iter 215 is structurally identifiable as the intersection of
iter 215 (bijective-singleton) and iter 201 (set-equality); it is a
recognition handle in its own right (the simplest per-group identity-
rule cell), not a Boolean parameter of the bijective-singleton axis.

Why this matters as the per-group projection of iter 13's identity
territory: iter 13 names the no-blob identity (zero change groups,
i.e. the whole task is unchanged). This matcher names the per-group
singleton-blob identity (every change group exists with a singleton
ic == oc, i.e. every blob is a no-op on its singleton). The two
identity-rule-family preconditions occupy disjoint cells on the
(#groups, #cells-per-group) lattice:

  * (#groups == 0, *)  -- iter 13's territory (no-blob identity).
  * (#groups >= 1, per-group |ic| == |oc| == 1 AND ic == oc) -- this
    matcher's territory (per-group singleton-blob identity).
  * (#groups >= 1, per-group |ic| == |oc| == 1 AND ic != oc) -- iter
    215 minus this matcher's territory (per-group bijective-singleton
    non-identity recolour, e.g. C -> K with K != C).
  * (#groups >= 1, per-group |ic| > 1 OR |oc| > 1) -- non-singleton
    per-group recolour territory.

With this matcher landed, the identity-rule-family axis is now named
at two resolutions: whole-task no-blob (iter 13) AND per-group
singleton-blob (this matcher). The previously-implicit "every blob
is a singleton fixed point" cell is now a first-class recognition
handle.

Strict refinement / orthogonality summary (universal-over-groups-
and-pairs semantics, per-group |ic| == |oc| == 1 AND ic == oc):

  * Iter 215 (``singleton_recolor_per_group``) -- per-group |ic| ==
    |oc| == 1. STRICT REFINEMENT (this matcher additionally requires
    per-group ic == oc as singletons).
  * Iter 201 (``output_colors_equals_input_colors_per_group``) --
    per-group set(ic) == set(oc). STRICT REFINEMENT (this matcher
    additionally requires per-group |ic| == |oc| == 1).
  * Iter 213 (``consistent_color_mapping_per_group``) -- per-group
    |oc| == 1. STRICT REFINEMENT (this matcher additionally requires
    per-group |ic| == 1 AND ic == oc).
  * Iter 214 (``input_color_uniform_per_group``) -- per-group |ic|
    == 1. STRICT REFINEMENT (this matcher additionally requires
    per-group |oc| == 1 AND ic == oc).
  * Iter 13 (``identity_transformation``) -- STRICT MUTUAL EXCLUSION.
    Together with this matcher they form a complete two-cell
    identity-rule-family axis (no-blob identity AND per-group
    singleton-blob identity); the two cells are disjoint by the
    #groups == 0 vs >= 1 split.
  * Iter 216 (``singleton_recolor``) -- INDEPENDENT in general.
    Co-fires only on cross-group-identity whole-task fixed-point
    singletons (i.e. iter 13's complement at |ic| == |oc| == 1 AND
    C == K); decouples when iter 216 fires alone (C != K) or when
    this matcher fires alone (cross-group identity fails).
  * Iter 8 (``consistent_color_mapping``) -- this matcher fires =>
    the per-pair (ic, oc) cross-product is function-shaped at every
    group (trivially, every group is its own (C_g, C_g) singleton).
    INDEPENDENT in general (iter 8 admits per-group |ic| > 1).
  * Iter 10 (``sequential_recoloring``) -- INDEPENDENT in general
    (iter 10's per-group oc-range-contiguity claim is independent of
    the per-group fixed-point claim).
  * Iter 14 ∧ iter 18 (jointly) -- this matcher's CROSS-GROUP-
    IDENTITY refinement (drops per-group flexibility). With cross-
    group identity AND ic == oc globally, the whole-task singleton-
    fixed-point cell. STRICT REFINEMENT direction (iter 14 ∧ iter 18
    ∧ "C == K globally" implies this matcher); converse fails on
    per-group fixed points varying across groups.
  * Iter 195 / 196 / 197 (per-group cardinality matchers) -- this
    matcher implies iter 195 at K_in == 1, iter 196 at K_out == 1,
    iter 197 at K_prod == 1. Cross-pair constancy at K == 1 is
    subsumed by universal-over-pairs semantics here.
  * Iter 198 / 199 (per-group palette-shift constancy) -- this
    matcher implies per-group shift k == 0 on every group. Co-fires
    only on the iter 198 / 199 k == 0 cell with |ic| == |oc| == 1.
  * Iter 200 / 202 / 203 / 204 / 205 / 206 (per-group palette-
    relation cells) -- six other cells of the per-group palette-
    relation sub-axis. STRICTLY MUTUALLY EXCLUSIVE with this matcher
    on the |ic| == |oc| == 1 row (the only co-firing cell is iter
    201, the immediate parent). Iter 200's territory restricted to
    proper-subset disqualifies (ic != oc); iter 203's disjoint
    territory disqualifies (ic ∩ oc != ∅ for singletons forces ic ==
    oc); etc.
  * Every cell- / position- / dimension-axis matcher (iters 1 / 17 /
    19 / 20 / 22 / 23 / 24 / 26 / 28 / 32 / 33 / 38 / 39 / 40 / 41 /
    42 / 182 / 183 / 184 / 185 / 186 / 187 / 188 / 189 / 190 / 191 /
    210 / 211 / 212) -- orthogonal to per-group singleton-fixed-
    point.

Why this matters for ARBOR's intended ruleset:

  * "Per-group singleton-blob identity" rule family -- rules whose
    per-group action is the no-op identity on every group's singleton.
    The simplest non-trivial per-group rule shape (rivalling iter
    13's no-blob identity); the building block from which more
    complex per-group identity-preserving rules (e.g. "preserve the
    singleton blob's colour AND modify everything else") generalise.
    This matcher names the precondition for that rule family, in a
    single registry slot, so anti-unification can attach the right
    gate to rules of this shape without having to rediscover the
    intersection each time.
  * Closes the iter-216-named candidate (vii): "a single matcher
    pinning iter 215 AND iter 201 jointly -- per-group |ic| == |oc|
    == 1 with per-group ic == oc (the per-group fixed-point-on-
    singleton cell, naming the precondition for rules whose per-
    group action is the no-op recolour identity on singleton
    groups)". With this matcher landed, the per-group bijective-
    singleton-recolour axis is named at two resolutions: any C -> K
    per group (iter 215) AND identity C -> C per group (this matcher);
    the per-group palette-relation axis is named at two resolutions
    on the singleton row: ic == oc singleton (this matcher) AND ic
    != oc singleton (iter 215 minus this matcher). The previously-
    implicit conjunction is now a first-class recognition handle.

Params:
  (none) -- pure per-group singleton-fixed-point check, universal
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
    200-206 / 213 / 214 / 215 strict-type posture), AND
  - for every group, ``len(set(input_colors)) == 1`` AND
    ``len(set(output_colors)) == 1`` AND
    ``set(input_colors) == set(output_colors)`` -- the per-group
    singleton fixed-point cell.

Why fail-closed on empty / no-group / malformed (same posture as
iter 8 / 13 / 14 / 18 / 30 / 32 / 33 / 34 / 35 / 36 / 37 / 38 / 39 /
184-216): a missing or zero-group pair is upstream extractor
breakage or iter 13's no-blob-identity territory; a per-group
singleton-fixed-point claim with zero observations is meaningless,
AND admitting it would collapse this matcher's territory into iter
13's (the two are designed as disjoint cells on the #groups axis).

Why ``input_colors`` and ``output_colors`` both required non-empty
lists per group (``len >= 1``): a connected change group has at
least one cell; each cell has both an input colour and an output
colour; the per-group ``input_colors`` / ``output_colors`` fields
are the sorted unique sets of those colours, which are non-empty
for any non-empty group. A zero-length colour list is an extractor
contract violation, not a valid empty-set singleton-fixed-point
case.

Why strict per-colour validation (bool rejected, range checked):
``input_colors`` / ``output_colors`` carry small ints in [0, 9];
the matcher performs the same strict-type gating as iter 14 / 18 /
19 / 34 / 35 / 36 / 37 / 38 / 184-216 to keep contract violations
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


@register("singleton_recolor_identity_per_group")
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
            if ic_set != oc_set:
                return False
    return True
