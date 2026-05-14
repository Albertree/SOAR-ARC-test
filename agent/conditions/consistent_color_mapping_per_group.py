"""
consistent_color_mapping_per_group -- match tasks where EVERY change
group of EVERY example pair satisfies, on its own per-group palettes,
the same function-shape gate as iter 8 (``consistent_color_mapping``)
applied at the per-group projection: within each group, every input
colour observed in that group must map to exactly one output colour
observed in that group.

Recognition vocabulary axis: per-group projection of the iter-8
function-shape sub-axis. Iter 8 unions the (ic, oc) cross-product
across ALL groups across ALL pairs, then checks that the resulting
``{ic -> set(oc)}`` map is function-shaped (every entry singleton).
This matcher rebuilds the cross-product PER GROUP and checks the
function-shape PER GROUP, independent of any cross-group / cross-pair
consistency.

On set-level data (the per-group ``input_colors`` / ``output_colors``
fields, both ordered-unique-int lists), the per-group function-shape
gate reduces to a tight set-level claim: for every group,
``len(set(output_colors)) == 1``. The per-group cross-product
``{ic: set(output_colors) for ic in input_colors}`` is function-shaped
iff each ``ic`` is bound to a singleton ``oc`` set -- which on set-
level data happens exactly when the group's ``output_colors`` set has
cardinality 1 (every ``ic`` then maps trivially to the same single
``oc``). Empty per-group ``input_colors`` is rejected as an extractor
contract violation (mirroring iter 14 / 18 / 200 / 201 / 202 / 203 /
204 / 205 / 206 strict-type posture).

This matcher names the precondition for a DIFFERENT rule family than
iter 8's whole-task function-shape: rules whose action selects a per-
group target output colour (potentially varying across groups) and
applies it uniformly within that group. Iter 8 names the precondition
for rules whose action carries a SINGLE global (C -> K) function;
this matcher names the precondition for rules whose action carries
INDEPENDENT per-group choices of ``K_g``.

Strict relation to iter 8 (``consistent_color_mapping``): iter 8 is a
strict refinement -- iter 8 fires => this matcher fires. Proof: if
the global ``{ic -> set(oc)}`` map across all groups has only
singleton entries, then any restriction of that map to a single
group's domain also has only singleton entries. The converse does NOT
hold: a task with group 1 = (ic=[0], oc=[3]) and group 2 = (ic=[0],
oc=[4]) has per-group function-shape on each group (|oc| == 1 in
both), but the global map ``{0: {3, 4}}`` is NOT function-shaped, so
iter 8 rejects.

Strict relation to iter 18 (``output_color_uniform``): iter 18 is a
strict refinement -- iter 18 fires => this matcher fires. Iter 18
requires every group's ``output_colors`` to be a singleton AND every
group's singleton to be bit-identical across all groups in all pairs.
This matcher requires only the per-group singleton-ness, NOT the
cross-group identity. So iter 18 => this matcher (strict implication);
the converse fails on a task with group 1 ``output_colors=[3]`` and
group 2 ``output_colors=[4]`` -- this matcher fires (each group has
singleton output), iter 18 rejects (singletons differ across groups).

Strict relation to iter 196 (``change_output_color_count_per_group_
constant_across_pairs``): iter 196 says |output_colors| per group is
constant across pairs (the per-group output cardinality K_P is the
same across pairs). This matcher additionally pins that cardinality
to == 1 per group. Iter 196 with K_P == 1 is EXACTLY this matcher's
fired-gate under the constant-across-pairs scope. With cross-pair
constancy admitted, this matcher implies iter 196 with K == 1; iter
196 with K == 1 implies this matcher (per-group |oc| == 1 holds on
every pair). With K != 1, iter 196 fires but this matcher rejects.
So this matcher is iter 196 restricted to K == 1. STRICT REFINEMENT
of iter 196 on the K==1 cell.

Mutual exclusion with iter 13 (``identity_transformation``): zero
change groups per pair. This matcher REJECTS the no-group case by the
inner ``groups`` non-empty clause (mirroring iter 8's identity-
territory rejection). Strict mutual exclusion.

Relation to iter 14 (``input_color_uniform``): iter 14 pins every
group's ``input_colors`` to a single colour. INDEPENDENT in general:
iter 14 constrains the input side, this matcher constrains the
output side. Both CAN fire on a task where every group has both
``input_colors`` and ``output_colors`` of cardinality 1 (possibly
different per group).

Relation to iter 10 (``sequential_recoloring``): iter 10 requires
outputs across groups to form a contiguous integer range with at
least two distinct values. Iter 10's witness has every group's
``output_colors`` == [c_g] with c_g taking each value in a
contiguous range. So iter 10 fires => every group has |oc| == 1 (the
per-group singleton is part of the range) => this matcher fires.
Strict implication: iter 10 => this matcher. The converse fails:
this matcher fires with group output singletons that do NOT form a
contiguous range (e.g. [3] and [7]) but iter 10 rejects.

Relation to iter 200-206 (per-group palette-relation cells):
INDEPENDENT in general. The palette-relation cells constrain the
RELATION between per-group input and output sets (subset / equality /
disjoint / partial overlap / strict refinements). This matcher
constrains the OUTPUT-SET CARDINALITY (== 1). The two axes can co-
fire (e.g. iter 201 equality with both sets equal to ``[3]`` fires
both iter 201 and this matcher) or be mutually exclusive on specific
cells (e.g. iter 201 equality with both sets equal to ``[3, 4]``
fires iter 201 but rejects this matcher since |oc| == 2).

Relation to iter 195 (``change_input_color_count_per_group_constant_
across_pairs``): orthogonal -- iter 195 constrains the per-group
input cardinality across pairs; this matcher constrains the per-
group output cardinality at 1. INDEPENDENT.

Relation to iter 197 (``change_color_mapping_count_per_group_
constant_across_pairs``): iter 197 constrains the per-group product
cardinality |ic| * |oc| across pairs. With this matcher firing,
|oc| == 1 per group, so the product simplifies to |ic|. Iter 197
requires cross-pair constancy of the product; with |oc| == 1, the
product reduces to |ic|, so iter 197's constraint becomes "per-group
|ic| constant across pairs" -- which is exactly iter 195. INDEPENDENT
in general (this matcher does NOT pin |ic|).

Relation to iter 198 / 199 (per-group palette-shift constancy): a
per-group same-cardinality shift requires |ic| == |oc| per group. If
this matcher fires (|oc| == 1 per group), iter 198 / 199 fire only
when |ic| == 1 per group as well (the K==1-input-cardinality cell of
iter 198 / 199). INDEPENDENT in general.

Why a distinct matcher rather than parameterising iter 196 with a
``K == 1`` flag: the matcher contract (docs/RULE_FORMAT.md §4) is
name-keyed recognition vocabulary; the rule's stored
``condition.type`` is the recognition handle's name, not a name+params
tuple. The per-group function-shape precondition gates a DIFFERENT
rule family (per-group uniform-output recolour, possibly varying K_g
across groups) than the cross-pair K-constancy precondition of iter
196 (per-group |oc| constant across pairs at SOME value, possibly
K != 1). Keeping them in separate registry slots lets anti-
unification attach the right gate per rule family.

Why a distinct matcher rather than parameterising iter 8 with a
``per_group: True`` flag: same rationale as above. The whole-task
function-shape (iter 8) and the per-group function-shape (this
matcher) gate fundamentally different rule shapes: iter 8 gates a
single shared (C -> K) function across the whole task; this matcher
gates per-group choices.

Strict refinement / orthogonality summary (universal-over-groups-and-
pairs semantics, per-group function-shape scope):

  * Iter 8 (``consistent_color_mapping``) -- whole-task function-
    shape. STRICTLY IMPLIES this matcher (whole-task function-shape
    implies per-group function-shape, by restriction). Converse fails.
  * Iter 13 (``identity_transformation``) -- zero change groups per
    pair. STRICT MUTUAL EXCLUSION (this matcher requires every pair
    to have non-empty groups).
  * Iter 14 (``input_color_uniform``) -- pins per-group |ic| == 1.
    INDEPENDENT.
  * Iter 18 (``output_color_uniform``) -- pins per-group |oc| == 1
    AND singleton identity across groups. STRICTLY IMPLIES this
    matcher (this matcher drops the cross-group identity clause).
  * Iter 10 (``sequential_recoloring``) -- per-group |oc| == 1 with
    singletons forming a contiguous range. STRICTLY IMPLIES this
    matcher. Converse fails on non-contiguous singletons.
  * Iter 195 (``change_input_color_count_per_group_constant_across_
    pairs``) -- per-group |ic| cross-pair constancy. INDEPENDENT.
  * Iter 196 (``change_output_color_count_per_group_constant_across_
    pairs``) -- per-group |oc| cross-pair constancy at SOME value K.
    This matcher is iter 196 RESTRICTED to K == 1 (every group has
    |oc| == 1, which is trivially constant across pairs). STRICT
    REFINEMENT.
  * Iter 197 (``change_color_mapping_count_per_group_constant_across_
    pairs``) -- per-group |ic|*|oc| cross-pair constancy. INDEPENDENT.
  * Iter 198 / 199 (per-group palette-shift constancy) -- requires
    |ic| == |oc| per group. INDEPENDENT in general; co-fires on the
    |ic| == |oc| == 1 cell.
  * Iter 200-206 (per-group palette-relation cells) -- INDEPENDENT in
    general. Detailed cell-by-cell co-fire above.
  * Every cell- / position- / dimension-axis matcher (iters 1 / 17 /
    19 / 20 / 22 / 23 / 24 / 26 / 28 / 32 / 33 / 38 / 39 / 40 / 41 /
    42 / 182 / 183 / 184 / 185 / 186 / 187 / 188 / 189 / 190 / 191 /
    210 / 211 / 212) -- orthogonal to per-group output-cardinality.

Why this matters for ARBOR's intended ruleset:

  * "Per-group uniform-output recolour" rule family -- rules whose
    action paints each changed group with its own per-group target
    colour K_g. Iter 18 names the GLOBAL-uniform sub-cell (all K_g
    equal); this matcher names the strictly weaker per-group-uniform
    parent cell that admits varying K_g across groups (each group
    independently uniform). Iter 8 (``consistent_color_mapping``)
    names the function-shape sub-cell where K_g is determined by the
    group's input colour (C -> K mapping); this matcher admits
    K_g determined by ANY per-group property (position, size,
    cardinality, ...), not just the input colour.
  * Closes the iter-209-named, iter-212-renamed first-listed candidate
    on the consistent-color-mapping per-group projection axis -- the
    smallest defensible step that opens a NEW sub-axis (per-group
    function-shape), distinct from the strict-refinement axis closed
    at iter 211 + iter 212.

Params:
  (none) -- pure per-group function-shape check, universal over
  groups and pairs.

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
    202 / 203 / 204 / 205 / 206 strict-type posture), AND
  - for every group, the cross-product ``{ic: set(output_colors) for
    ic in input_colors}`` has function-shape -- every binding's value
    is a singleton (equivalently on set-level data:
    ``len(set(output_colors)) == 1``).

Why fail-closed on empty / no-group / malformed (same posture as iter
8 / 13 / 14 / 18 / 30 / 32 / 33 / 34 / 35 / 36 / 37 / 38 / 39 /
184-212): a missing or zero-group pair is upstream extractor breakage
or identity-territory; a per-group function-shape claim with zero
observations is meaningless.

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
34 / 35 / 36 / 37 / 38 / 184-212 to keep contract violations from
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


@register("consistent_color_mapping_per_group")
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
            color_map: dict = {}
            for ic in input_colors:
                for oc in output_colors:
                    color_map.setdefault(ic, set()).add(oc)
            if not color_map:
                return False
            if not all(len(v) == 1 for v in color_map.values()):
                return False
    return True
