"""
input_color_uniform_per_group -- match tasks where EVERY change group of
EVERY example pair has ``len(set(input_colors)) == 1``. The per-group
projection of iter 14 (``input_color_uniform``), dropping iter 14's
cross-group identity clause.

Recognition vocabulary axis: per-group projection of the INVERSE
function-shape sub-axis. Iter 213 (``consistent_color_mapping_per_group``)
is the per-group projection of iter 8's forward function-shape -- on
set-level data, ``len(set(output_colors)) == 1`` per group. This matcher
is the symmetric DUAL on the input side: the per-group projection of
the inverse function-shape, where every output colour observed in the
group maps backwards to exactly one input colour. On set-level data
(the per-group ``input_colors`` / ``output_colors`` fields, both ordered-
unique-int lists), the per-group inverse-function-shape gate reduces
tightly to ``len(set(input_colors)) == 1`` per group: the inverse cross-
product ``{oc: set(input_colors) for oc in output_colors}`` is function-
shaped iff each ``oc`` is bound to a singleton ``ic`` set, which on
set-level data happens exactly when the group's ``input_colors`` set
has cardinality 1.

This matcher names the precondition for a DIFFERENT rule family than
iter 14's whole-task input-uniform: rules whose action selects a per-
group source-colour predicate (potentially varying across groups) and
operates on the cells of that single source colour within the group.
Iter 14 names the precondition for rules whose action carries a
SINGLE global source colour C; this matcher names the precondition
for rules whose action carries INDEPENDENT per-group choices of
``C_g``.

Strict relation to iter 14 (``input_color_uniform``): iter 14 is a
strict refinement -- iter 14 fires => this matcher fires. Iter 14
requires every group's ``input_colors`` to be a singleton AND every
group's singleton to be bit-identical across all groups in all pairs.
This matcher requires only the per-group singleton-ness, NOT the
cross-group identity. So iter 14 => this matcher (strict implication);
the converse fails on a task with group 1 ``input_colors=[3]`` and
group 2 ``input_colors=[4]`` -- this matcher fires (each group has
singleton input), iter 14 rejects (singletons differ across groups).

Strict relation to iter 195 (``change_input_color_count_per_group_
constant_across_pairs``): iter 195 says |input_colors| per group is
constant across pairs (the per-group input cardinality K_P is the
same across pairs). This matcher additionally pins that cardinality
to == 1 per group. Iter 195 with K_P == 1 is EXACTLY this matcher's
fired-gate under the constant-across-pairs scope. With cross-pair
constancy admitted, this matcher implies iter 195 with K == 1; iter
195 with K == 1 implies this matcher (per-group |ic| == 1 holds on
every pair). With K != 1, iter 195 fires but this matcher rejects.
So this matcher is iter 195 restricted to K == 1. STRICT REFINEMENT
of iter 195 on the K==1 cell.

Mutual exclusion with iter 13 (``identity_transformation``): zero
change groups per pair. This matcher REJECTS the no-group case by the
inner ``groups`` non-empty clause (mirroring iter 213's identity-
territory rejection). Strict mutual exclusion.

Relation to iter 213 (``consistent_color_mapping_per_group``): the
SYMMETRIC DUAL on the output side. iter 213 pins per-group |oc| == 1;
this matcher pins per-group |ic| == 1. INDEPENDENT in general: both
constrain a different side of the per-group palette. Both CAN fire
on a task where every group has |ic| == |oc| == 1 (the simplest per-
group recolour cell), possibly different per group.

Relation to iter 8 (``consistent_color_mapping``): iter 8 is a
whole-task function-shape (forward: ic -> set(oc) globally function-
shaped). INDEPENDENT in general: iter 8 constrains the forward side
across the whole task; this matcher constrains the inverse side per
group. They can co-fire (e.g. every group has both |ic| == 1 and
|oc| == 1 with a consistent global ic -> oc mapping, like the iter-10
fixture where ic=0->3, ic=1->4, ic=2->5 across all pairs) or only one
fire. On the iter-10 fixture both fire.

Relation to iter 18 (``output_color_uniform``): independent in general
-- iter 18 constrains the output side globally; this matcher constrains
the input side per group. Both can fire on tasks where every group has
|ic| == 1 (this matcher) AND every group has |oc| == 1 with the same
output singleton across all groups (iter 18).

Relation to iter 10 (``sequential_recoloring``): iter 10 requires per-
group |oc| == 1 with the singletons forming a contiguous range. It
does NOT directly constrain the input side; INDEPENDENT in general.
On the iter-10 canonical fixture (each group has ic singleton and
distinct oc forming a range), this matcher fires too because each
group has |ic| == 1. But iter 10 can fire on a task where some group
has |ic| > 1 (e.g. ic=[0, 1] -> oc=[3]), in which case this matcher
rejects.

Relation to iter 200-206 (per-group palette-relation cells):
INDEPENDENT in general. The palette-relation cells constrain the
RELATION between per-group input and output sets (subset / equality /
disjoint / partial overlap / strict refinements). This matcher
constrains the INPUT-SET CARDINALITY (== 1). The two axes can co-
fire (e.g. iter 201 equality with both sets equal to ``[3]`` fires
both iter 201 and this matcher) or be mutually exclusive on specific
cells (e.g. iter 201 equality with both sets equal to ``[3, 4]``
fires iter 201 but rejects this matcher since |ic| == 2).

Relation to iter 196 (``change_output_color_count_per_group_constant_
across_pairs``): orthogonal -- iter 196 constrains the per-group
output cardinality across pairs; this matcher constrains the per-
group input cardinality at 1. INDEPENDENT.

Relation to iter 197 (``change_color_mapping_count_per_group_
constant_across_pairs``): iter 197 constrains the per-group product
cardinality |ic| * |oc| across pairs. With this matcher firing,
|ic| == 1 per group, so the product simplifies to |oc|. Iter 197
requires cross-pair constancy of the product; with |ic| == 1, the
product reduces to |oc|, so iter 197's constraint becomes "per-group
|oc| constant across pairs" -- which is exactly iter 196. INDEPENDENT
in general (this matcher does NOT pin |oc|).

Relation to iter 198 / 199 (per-group palette-shift constancy): a
per-group same-cardinality shift requires |ic| == |oc| per group. If
this matcher fires (|ic| == 1 per group), iter 198 / 199 fire only
when |oc| == 1 per group as well (the K==1-input-cardinality cell of
iter 198 / 199). INDEPENDENT in general.

Why a distinct matcher rather than parameterising iter 195 with a
``K == 1`` flag: the matcher contract (docs/RULE_FORMAT.md §4) is
name-keyed recognition vocabulary; the rule's stored
``condition.type`` is the recognition handle's name, not a name+params
tuple. The per-group input-uniform precondition gates a DIFFERENT
rule family (per-group source-colour selection, possibly varying C_g
across groups) than the cross-pair K-constancy precondition of iter
195 (per-group |ic| constant across pairs at SOME value, possibly
K != 1). Keeping them in separate registry slots lets anti-
unification attach the right gate per rule family.

Why a distinct matcher rather than parameterising iter 14 with a
``per_group: True`` flag: same rationale as above. The whole-task
input-uniform (iter 14) and the per-group input-uniform (this
matcher) gate fundamentally different rule shapes: iter 14 gates a
single shared source colour C across the whole task; this matcher
gates per-group choices.

Strict refinement / orthogonality summary (universal-over-groups-and-
pairs semantics, per-group inverse-function-shape scope):

  * Iter 14 (``input_color_uniform``) -- whole-task input-uniform.
    STRICTLY IMPLIES this matcher (drops the cross-group identity).
    Converse fails when per-group singletons differ across groups.
  * Iter 13 (``identity_transformation``) -- zero change groups per
    pair. STRICT MUTUAL EXCLUSION (this matcher requires every pair
    to have non-empty groups).
  * Iter 18 (``output_color_uniform``) -- pins per-group |oc| == 1
    AND singleton identity across groups. INDEPENDENT (orthogonal
    sides).
  * Iter 213 (``consistent_color_mapping_per_group``) -- per-group
    |oc| == 1, dropping cross-group identity from iter 18. SYMMETRIC
    DUAL on the output side. INDEPENDENT in general.
  * Iter 8 (``consistent_color_mapping``) -- whole-task forward
    function-shape. INDEPENDENT in general.
  * Iter 10 (``sequential_recoloring``) -- per-group |oc| == 1 with
    singletons forming a contiguous range. INDEPENDENT (constrains
    the output side); on the iter-10 canonical fixture both fire
    because each group has |ic| == 1 too.
  * Iter 195 (``change_input_color_count_per_group_constant_across_
    pairs``) -- per-group |ic| cross-pair constancy at SOME value K.
    This matcher is iter 195 RESTRICTED to K == 1 (every group has
    |ic| == 1, which is trivially constant across pairs). STRICT
    REFINEMENT.
  * Iter 196 (``change_output_color_count_per_group_constant_across_
    pairs``) -- per-group |oc| cross-pair constancy. INDEPENDENT.
  * Iter 197 (``change_color_mapping_count_per_group_constant_across_
    pairs``) -- per-group |ic|*|oc| cross-pair constancy. INDEPENDENT.
  * Iter 198 / 199 (per-group palette-shift constancy) -- requires
    |ic| == |oc| per group. INDEPENDENT in general; co-fires on the
    |ic| == |oc| == 1 cell.
  * Iter 200-206 (per-group palette-relation cells) -- INDEPENDENT in
    general.
  * Every cell- / position- / dimension-axis matcher (iters 1 / 17 /
    19 / 20 / 22 / 23 / 24 / 26 / 28 / 32 / 33 / 38 / 39 / 40 / 41 /
    42 / 182 / 183 / 184 / 185 / 186 / 187 / 188 / 189 / 190 / 191 /
    210 / 211 / 212) -- orthogonal to per-group input-cardinality.

Why this matters for ARBOR's intended ruleset:

  * "Per-group uniform-input recolour" rule family -- rules whose
    action paints, within each group, the cells of a single source
    colour C_g (possibly varying across groups) with a per-group
    target colour. Iter 14 names the GLOBAL-uniform-input sub-cell
    (all C_g equal); this matcher names the strictly weaker per-
    group-uniform-input parent cell that admits varying C_g across
    groups (each group independently uniform on the input side).
  * Closes the iter-213-named candidate (iv): the per-group input-
    uniform cell, the symmetric DUAL of iter 18's per-group output-
    uniform-singleton claim landed at iter 213. With this matcher
    landed, the per-group function-shape axis is closed at the
    forward direction (iter 213) AND the inverse direction (this
    matcher).

Params:
  (none) -- pure per-group inverse-function-shape check, universal
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
    int in ``range(10)`` (bool rejected per iter-14 / 18 / 200 / 201 /
    202 / 203 / 204 / 205 / 206 / 213 strict-type posture), AND
  - for every group, the inverse cross-product ``{oc: set(input_
    colors) for oc in output_colors}`` has function-shape -- every
    binding's value is a singleton (equivalently on set-level data:
    ``len(set(input_colors)) == 1``).

Why fail-closed on empty / no-group / malformed: a missing or zero-
group pair is upstream extractor breakage or identity-territory; a
per-group inverse-function-shape claim with zero observations is
meaningless. Same posture as iter 8 / 13 / 14 / 18 / 30 / 32 / 33 /
34 / 35 / 36 / 37 / 38 / 39 / 184-213.

Why ``input_colors`` and ``output_colors`` both required non-empty
lists per group (``len >= 1``): a connected change group has at least
one cell; each cell has both an input colour and an output colour;
the per-group ``input_colors`` / ``output_colors`` fields are the
sorted unique sets of those colours, which are non-empty for any
non-empty group. A zero-length colour list is an extractor contract
violation, not a valid empty-set function-shape case.

Why strict per-colour validation (bool rejected, range checked):
``input_colors`` / ``output_colors`` carry small ints in [0, 9]; the
matcher performs the same strict-type gating as iter 14 / 18 / 19 /
34 / 35 / 36 / 37 / 38 / 184-213 to keep contract violations from
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


@register("input_color_uniform_per_group")
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
            inverse_map: dict = {}
            for oc in output_colors:
                for ic in input_colors:
                    inverse_map.setdefault(oc, set()).add(ic)
            if not inverse_map:
                return False
            if not all(len(v) == 1 for v in inverse_map.values()):
                return False
    return True
