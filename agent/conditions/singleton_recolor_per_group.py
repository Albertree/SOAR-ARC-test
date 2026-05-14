"""
singleton_recolor_per_group -- match tasks where EVERY change group of
EVERY example pair has BOTH ``len(set(input_colors)) == 1`` AND
``len(set(output_colors)) == 1``. The CO-FIRE conjunction of iter 213
(``consistent_color_mapping_per_group``, the per-group projection of
iter 8's forward function-shape: per-group |oc| == 1) AND iter 214
(``input_color_uniform_per_group``, the per-group projection of the
inverse function-shape: per-group |ic| == 1).

Recognition vocabulary axis: the simplest per-group bijective recolour
cell. Iter 213 names the per-group forward function-shape sub-axis
(|oc| == 1 per group, possibly with |ic| > 1); iter 214 names the
per-group inverse function-shape sub-axis (|ic| == 1 per group, possibly
with |oc| > 1). This matcher names the INTERSECTION cell where both
sides simultaneously satisfy K == 1 -- the precondition for the rule
family "per-group one-colour-in-one-colour-out rewrite", where every
change group has a single source colour C_g and a single target colour
K_g, independently chosen per group.

On set-level data (the per-group ``input_colors`` / ``output_colors``
fields, both ordered-unique-int lists), the conjunction reduces tightly
to ``len(set(input_colors)) == 1 AND len(set(output_colors)) == 1`` per
group. Equivalently, the per-group bijective recolour cell is the
|ic| == |oc| == 1 cell on the iter-197 product-cardinality axis (the
|ic| * |oc| == 1 row), which is mutually exclusive with all other
(|ic|, |oc|) cardinality cells (|ic| > 1 OR |oc| > 1 disqualifies).

This matcher names the precondition for a STRICTLY MORE SPECIFIC rule
family than iter 213 or iter 214 alone: rules whose per-group action
carries BOTH a per-group source colour C_g AND a per-group target
colour K_g, with the action shape "for each group, recolour the single
source colour C_g to the single target colour K_g within that group's
cells." Iter 213 names the precondition where the source side may be
multi-colour (the action recolours ANY of multiple per-group input
colours into a single per-group target); iter 214 names the
precondition where the target side may be multi-colour (the action
splits a single per-group source into multiple per-group targets).
This matcher names the cell where BOTH sides are pinned to singletons.

Strict relations to iter 213 / iter 214 (the immediate parents):

  * Iter 213 (``consistent_color_mapping_per_group``): STRICT
    REFINEMENT. This matcher fires => iter 213 fires (|oc| == 1 per
    group is a precondition of this matcher). The converse fails on a
    task with |ic| > 1 in some group: iter 213 fires (|oc| == 1 per
    group), this matcher rejects (|ic| > 1 in that group).
  * Iter 214 (``input_color_uniform_per_group``): STRICT REFINEMENT.
    This matcher fires => iter 214 fires (|ic| == 1 per group is a
    precondition of this matcher). The converse fails on a task with
    |oc| > 1 in some group: iter 214 fires (|ic| == 1 per group), this
    matcher rejects (|oc| > 1 in that group).

So this matcher is the STRICT CONJUNCTION (logical AND) of iter 213
and iter 214. The pair-completion of the per-group function-shape axis
closed in both directions by iters 213 + 214: those two name the
single-side cells; this matcher names the both-sides-at-once cell.

Strict relation to iter 14 (``input_color_uniform``) AND iter 18
(``output_color_uniform``) jointly: iter 14 fires AND iter 18 fires =>
this matcher fires (iter 14 strict-implies iter 214; iter 18 strict-
implies iter 213; conjunction implies conjunction). The converse fails
on a task with per-group singletons differing across groups -- this
matcher fires (per-group singleton-ness on both sides), but iter 14 /
iter 18 reject (cross-group identity required).

Strict relation to iter 8 (``consistent_color_mapping``) AND its
inverse projection iter 14 (whole-task input-uniform): the whole-task
conjunction (iter 14 ∧ iter 18) is strictly STRONGER than this matcher
(adds cross-group identity on both sides). INDEPENDENT in general
because iter 8 alone doesn't constrain the input side cardinality, and
neither does iter 14 alone constrain the output side -- only the
combination iter 14 AND iter 18 strictly implies this matcher.

Strict relation to iter 195 (``change_input_color_count_per_group_
constant_across_pairs``) AND iter 196 (``change_output_color_count_per_
group_constant_across_pairs``) jointly: iter 195 with K_in == 1 AND
iter 196 with K_out == 1 is EXACTLY this matcher's fired-gate. With
both K_in and K_out pinned to 1 across pairs, the per-group |ic| *
|oc| product is 1 (the K_prod == 1 cell of iter 197). INDEPENDENT in
general (iter 195 / iter 196 alone admit K != 1).

Strict relation to iter 197 (``change_color_mapping_count_per_group_
constant_across_pairs``): iter 197 says |ic|*|oc| per group is constant
across pairs at SOME K_prod. This matcher pins K_prod == 1 per group
(which is trivially constant across pairs). STRICT REFINEMENT of iter
197 at the K_prod == 1 cell. With K_prod == 1, the product factorisation
forces |ic| == |oc| == 1 (the only way two positive ints multiply to 1
is both equal 1), so K_prod == 1 is exactly the singleton-recolour
cell.

Strict relation to iter 198 / iter 199 (per-group palette-shift
constancy): a per-group constant shift k = oc - ic requires |ic| ==
|oc| per group. The shift-constancy gate combined with |ic| == |oc| ==
1 produces a well-defined single shift per group. INDEPENDENT in
general (iter 198 / 199 admit |ic| == |oc| > 1 cells like a 2-element
palette shifted by a constant); co-fires on the |ic| == |oc| == 1 cell.

Mutual exclusion with iter 13 (``identity_transformation``): zero
change groups per pair. This matcher REJECTS the no-group case by the
inner ``groups`` non-empty clause (mirroring iter 213 / 214 identity-
territory rejection). Strict mutual exclusion.

Mutual exclusion with cells where the per-group cardinality on EITHER
side exceeds 1: iter 215 (this matcher) REJECTS any (|ic|, |oc|) cell
with |ic| > 1 OR |oc| > 1. So it is strictly mutually exclusive with:

  * Iter 213's territory restricted to |ic| > 1 (per-group output-
    singleton with multi-colour input).
  * Iter 214's territory restricted to |oc| > 1 (per-group input-
    singleton with multi-colour output).
  * Iter 195 with K_in != 1 (any per-group input cardinality K != 1).
  * Iter 196 with K_out != 1 (any per-group output cardinality K != 1).
  * Iter 197 with K_prod != 1 (any per-group product cardinality K != 1).

Relation to iter 200-206 (per-group palette-relation cells):
INDEPENDENT in general. The palette-relation cells constrain the
RELATION between per-group input and output sets (subset / equality /
disjoint / partial overlap / strict refinements). This matcher
constrains both CARDINALITIES (== 1). The two axes can co-fire (e.g.
iter 201 equality with both sets equal to ``[3]`` fires both iter 201
and this matcher) or be mutually exclusive on specific cells (e.g.
iter 201 equality with both sets equal to ``[3, 4]`` fires iter 201
but rejects this matcher since |ic| == |oc| == 2; iter 200 disjoint
with |ic| > 1 fires iter 200 but rejects this matcher).

On the canonical iter-10 fixture (each group has ic singleton AND oc
singleton, with the per-group oc singletons forming a contiguous
range), this matcher fires (every group has |ic| == |oc| == 1). Iter
10 strict-implies this matcher on the contiguous-range refinement; the
converse fails on non-contiguous singletons.

Why a distinct matcher rather than just AND-ing iter 213 with iter 214
at the rule level: the matcher contract (docs/RULE_FORMAT.md §4) is
name-keyed recognition vocabulary; the rule's stored ``condition.type``
is the recognition handle's name, not a Boolean composition tree. A
rule whose precondition is "per-group |ic| == |oc| == 1" gates a
DIFFERENT rule family (per-group bijective singleton recolour) than
either iter 213 alone (per-group uniform-output, possibly multi-input)
or iter 214 alone (per-group uniform-input, possibly multi-output).
Keeping the conjunction as a separate registry slot lets anti-
unification attach the right gate per rule family, rather than forcing
the generaliser to discover that conjunction every time it sees a
bijective-singleton-recolour rule.

Why a distinct matcher rather than parameterising iter 197 with a
``K == 1`` flag: same rationale as iter 213 / iter 214 each got their
own slot rather than parameterising iter 196 / iter 195 with K == 1.
The K_prod == 1 cell of iter 197 is structurally identifiable as the
intersection of iter 195 K == 1 and iter 196 K == 1; it is a recognition
handle in its own right (the simplest per-group bijective-recolour
cell), not a Boolean parameter of the cardinality-constancy axis.

Strict refinement / orthogonality summary (universal-over-groups-and-
pairs semantics, per-group |ic| == |oc| == 1 scope):

  * Iter 213 (``consistent_color_mapping_per_group``) -- per-group
    |oc| == 1. STRICT REFINEMENT (this matcher additionally requires
    |ic| == 1 per group).
  * Iter 214 (``input_color_uniform_per_group``) -- per-group |ic| ==
    1. STRICT REFINEMENT (this matcher additionally requires |oc| == 1
    per group).
  * Iter 8 (``consistent_color_mapping``) -- whole-task forward
    function-shape. INDEPENDENT in general; co-fires with this matcher
    on tasks where every group has |ic| == |oc| == 1 with a globally
    consistent ic -> oc map.
  * Iter 14 ∧ iter 18 (jointly: whole-task |ic| == 1 AND |oc| == 1
    AND identity across groups): STRICTLY IMPLIES this matcher (drops
    the cross-group identity clauses).
  * Iter 13 (``identity_transformation``) -- zero change groups per
    pair. STRICT MUTUAL EXCLUSION.
  * Iter 10 (``sequential_recoloring``) -- per-group |oc| == 1 with
    singletons forming a contiguous range. INDEPENDENT in general
    (does not constrain the input side); co-fires on the iter-10
    canonical fixture where |ic| == 1 per group too.
  * Iter 195 (``change_input_color_count_per_group_constant_across_
    pairs``) -- per-group |ic| cross-pair constancy at SOME K. This
    matcher is iter 195 RESTRICTED to K == 1 (subset of its iter-214
    relation, with |oc| == 1 added).
  * Iter 196 (``change_output_color_count_per_group_constant_across_
    pairs``) -- per-group |oc| cross-pair constancy at SOME K. This
    matcher is iter 196 RESTRICTED to K == 1 (subset of its iter-213
    relation, with |ic| == 1 added).
  * Iter 197 (``change_color_mapping_count_per_group_constant_across_
    pairs``) -- per-group |ic|*|oc| cross-pair constancy at SOME
    K_prod. This matcher is iter 197 RESTRICTED to K_prod == 1 (the
    singleton-recolour cell of the product axis).
  * Iter 198 / 199 (per-group palette-shift constancy) -- requires
    |ic| == |oc| per group. INDEPENDENT in general; co-fires on the
    |ic| == |oc| == 1 cell with any shift k.
  * Iter 200-206 (per-group palette-relation cells) -- INDEPENDENT in
    general; cell-by-cell intersection at the |ic| == |oc| == 1 row.
  * Every cell- / position- / dimension-axis matcher (iters 1 / 17 /
    19 / 20 / 22 / 23 / 24 / 26 / 28 / 32 / 33 / 38 / 39 / 40 / 41 /
    42 / 182 / 183 / 184 / 185 / 186 / 187 / 188 / 189 / 190 / 191 /
    210 / 211 / 212) -- orthogonal to per-group bijective-singleton
    recolour.

Why this matters for ARBOR's intended ruleset:

  * "Per-group bijective singleton recolour" rule family -- rules
    whose per-group action carries a (C_g -> K_g) singleton pair,
    possibly varying both C_g and K_g across groups. The simplest
    per-group recolour rule shape; the building block from which more
    complex per-group multi-colour rules generalise. This matcher
    names the precondition for that rule family, in a single registry
    slot, so anti-unification can attach the right gate to rules of
    this shape without having to rediscover the |ic| == |oc| == 1
    intersection each time.
  * Closes the iter-214-named candidate (v): the CO-FIRE conjunction
    of iter 213 AND iter 214 at the per-group |ic| == |oc| == 1 cell.
    With this matcher landed, the per-group function-shape axis is
    now named at three resolutions: forward singleton (iter 213),
    inverse singleton (iter 214), AND both-side singleton (this
    matcher). The previously-implicit conjunction is now a first-class
    recognition handle.

Params:
  (none) -- pure per-group bijective-singleton-recolour check, universal
  over groups and pairs.

Returns True iff:
  - ``patterns`` is a dict, AND
  - ``patterns["pair_analyses"]`` is a non-empty list, AND
  - every analysis is a dict, AND
  - every analysis has a non-empty ``groups`` list (identity-territory
    rejection), AND
  - every group is a dict with list-typed ``input_colors`` and
    ``output_colors`` fields of length >= 1, AND
  - every entry of ``input_colors`` and ``output_colors`` is a strict
    int in ``range(10)`` (bool rejected per iter-14 / 18 / 200-206 /
    213 / 214 strict-type posture), AND
  - for every group, ``len(set(input_colors)) == 1`` AND
    ``len(set(output_colors)) == 1`` -- the per-group bijective
    singleton-recolour cell.

Why fail-closed on empty / no-group / malformed (same posture as iter
8 / 13 / 14 / 18 / 30 / 32 / 33 / 34 / 35 / 36 / 37 / 38 / 39 /
184-214): a missing or zero-group pair is upstream extractor breakage
or identity-territory; a per-group singleton-recolour claim with zero
observations is meaningless.

Why ``input_colors`` and ``output_colors`` both required non-empty
lists per group (``len >= 1``): a connected change group has at least
one cell; each cell has both an input colour and an output colour;
the per-group ``input_colors`` / ``output_colors`` fields are the
sorted unique sets of those colours, which are non-empty for any
non-empty group. A zero-length colour list is an extractor contract
violation, not a valid empty-set bijective-singleton-recolour case.

Why strict per-colour validation (bool rejected, range checked):
``input_colors`` / ``output_colors`` carry small ints in [0, 9]; the
matcher performs the same strict-type gating as iter 14 / 18 / 19 /
34 / 35 / 36 / 37 / 38 / 184-214 to keep contract violations from
silently passing.

No companion-touch required: ``input_colors`` and ``output_colors``
have been emitted per group since iter 1 (``_analyze_pair`` in
``agent/active_operators.py``); this iter is a pure matcher addition
with no ``agent/active_operators.py`` diff. F8 inert.
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


@register("singleton_recolor_per_group")
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
            if len(set(input_colors)) != 1:
                return False
            if len(set(output_colors)) != 1:
                return False
    return True
