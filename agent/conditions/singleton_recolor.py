"""
singleton_recolor -- match tasks where EVERY changed cell across every
example pair started as the SAME single input colour AND ended as the
SAME single output colour. The whole-task projection of iter 215
(``singleton_recolor_per_group``), adding cross-group identity on both
sides. Equivalently, the strict CONJUNCTION of iter 14
(``input_color_uniform``) AND iter 18 (``output_color_uniform``).

Recognition vocabulary axis: the simplest possible global recolour cell.
Iter 14 names the precondition where the input side collapses to a
single global C; iter 18 names the precondition where the output side
collapses to a single global K. This matcher names the INTERSECTION
cell where BOTH sides simultaneously collapse to global singletons --
the "single global recolour C -> K" cell, currently expressible only
as the conjunction of iter 14 AND iter 18 at the rule level. Naming
that conjunction as a first-class registry slot lets anti-unification
attach the right gate to rules whose action carries TWO global
constants (one source colour, one target colour) without rediscovering
that intersection each time.

Why a distinct matcher rather than just AND-ing iter 14 with iter 18
at the rule level: the matcher contract (docs/RULE_FORMAT.md §4) is
name-keyed recognition vocabulary; the rule's stored ``condition.type``
is the recognition handle's name, not a Boolean composition tree. A
rule whose precondition is "single global recolour C -> K" gates a
DIFFERENT rule family (global bijective singleton recolour, where the
action is ``coloring(grid, selection_where_input == C, K)`` with both
C and K fixed by training) than either iter 14 alone (global uniform
input, possibly multiple output colours per position) or iter 18
alone (global uniform output, possibly multiple input colours per
position). Keeping the conjunction as a separate registry slot lets
anti-unification attach the right gate per rule family, rather than
forcing the generaliser to discover that conjunction every time it
sees a single-global-recolour rule.

Why a distinct matcher rather than parameterising iter 215 with a
``cross_group_identity: True`` flag: same rationale as iters 213 / 214
each got their own slot rather than parameterising iter 196 / 195
with K == 1, and iter 215 got its own slot rather than parameterising
iter 197 with K_prod == 1. The whole-task conjunction (this matcher)
gates a STRICTLY MORE SPECIFIC rule family than iter 215 -- iter 215
admits per-group choices of (C_g, K_g) varying across groups; this
matcher demands a SINGLE global (C, K) pair across all groups in all
pairs. The simplest single-coloring-call recolour rule shape.

Strict relations to iter 14 / iter 18 (the immediate parents):

  * Iter 14 (``input_color_uniform``): STRICT REFINEMENT. This matcher
    fires => iter 14 fires (the whole-task input singleton-and-
    identity claim is a precondition of this matcher). The converse
    fails on a task where every changed cell starts as colour 0 but
    different cells end as different colours: iter 14 fires (input
    singleton-and-identity), this matcher rejects (output side
    multi-colour).
  * Iter 18 (``output_color_uniform``): STRICT REFINEMENT. This
    matcher fires => iter 18 fires (the whole-task output singleton-
    and-identity claim is a precondition of this matcher). The
    converse fails on a task where every changed cell ends as colour 7
    but different cells start as different colours: iter 18 fires
    (output singleton-and-identity), this matcher rejects (input side
    multi-colour).

So this matcher is the STRICT CONJUNCTION (logical AND) of iter 14 and
iter 18. The whole-task projection of iter 215's per-group bijective-
singleton cell, adding cross-group identity on both sides.

Strict relation to iter 215 (``singleton_recolor_per_group``): STRICT
REFINEMENT. This matcher fires => iter 215 fires (per-group |ic| ==
|oc| == 1 is a precondition of the whole-task version). The converse
fails on a task where per-group singletons differ across groups -- iter
215 fires (per-group singleton-ness on both sides), this matcher
rejects (cross-group identity required on both sides). Equivalently:
this matcher is iter 215 RESTRICTED to the cross-group-identity cell
on both sides.

Strict relation to iter 213 (``consistent_color_mapping_per_group``)
AND iter 214 (``input_color_uniform_per_group``): both are STRICTLY
IMPLIED by this matcher (this matcher fires => iter 215 fires => iter
213 fires AND iter 214 fires). The chain is: this matcher => iter 215
=> iter 213, iter 214. The converse of either step fails.

Strict relation to iter 8 (``consistent_color_mapping``): STRICT
REFINEMENT. Iter 8 says every input colour maps to a single output
colour globally (forward function-shape). This matcher additionally
requires only ONE input colour AND only ONE output colour across the
whole task. With iter 14 firing (single global C), iter 8 reduces to
"C maps to exactly one output K"; with iter 18 firing (single global
K), the implied global mapping is the singleton map {C -> K}. So this
matcher fires => iter 8 fires (singleton map is trivially function-
shaped). The converse fails when iter 8 fires with multiple distinct
(in, out) pairs (e.g. ``0->3, 5->7``) -- this matcher rejects.

Mutual exclusion with iter 13 (``identity_transformation``): zero
changed cells. This matcher REJECTS the no-group case by inheriting
iter 14's and iter 18's non-empty-groups clauses. Strict mutual
exclusion.

Mutual exclusion with iter 10 (``sequential_recoloring``) restricted
to its multi-output cells: iter 10 requires per-group |oc| == 1 with
the singletons forming a contiguous integer range of length >= 1.
With length == 1, the iter-10 case degenerates to a single output
colour AND single input colour per group, which is compatible with
this matcher IF the cross-group identity holds on both sides. With
length >= 2, iter 10 fires but this matcher rejects (|oc| > 1 across
the task). INDEPENDENT in general; co-fires only on the trivial
length-1 cell.

Strict relation to iter 195 (``change_input_color_count_per_group_
constant_across_pairs``) AND iter 196 (``change_output_color_count_
per_group_constant_across_pairs``): both are STRICTLY IMPLIED. With
this matcher firing, every group has |ic| == 1 (so iter 195 holds at
K == 1) AND every group has |oc| == 1 (so iter 196 holds at K == 1).
The converse of either fails on K != 1.

Strict relation to iter 197 (``change_color_mapping_count_per_group_
constant_across_pairs``): STRICT REFINEMENT at K_prod == 1 with
cross-group identity. Iter 197 says |ic|*|oc| per group is constant
across pairs at SOME K_prod. This matcher pins K_prod == 1 per group
(both factors == 1) AND additionally demands cross-group identity on
both sides. The converse fails on K_prod == 1 with per-group
singletons varying across groups (iter 215 fires; this matcher
rejects).

Strict refinement / orthogonality summary (universal-over-groups-and-
pairs semantics, whole-task |ic| == |oc| == 1 + cross-group identity
scope):

  * Iter 14 (``input_color_uniform``) -- whole-task |ic| == 1 with
    cross-group identity. STRICT REFINEMENT (this matcher additionally
    requires the output side to collapse the same way).
  * Iter 18 (``output_color_uniform``) -- whole-task |oc| == 1 with
    cross-group identity. STRICT REFINEMENT (this matcher additionally
    requires the input side to collapse the same way).
  * Iter 8 (``consistent_color_mapping``) -- whole-task forward
    function-shape. STRICT REFINEMENT (this matcher additionally
    pins both cardinalities to 1, making the function-shape a
    singleton map).
  * Iter 215 (``singleton_recolor_per_group``) -- per-group |ic| ==
    |oc| == 1, NO cross-group identity. STRICT REFINEMENT (this
    matcher additionally requires cross-group identity on both
    sides).
  * Iter 213 (``consistent_color_mapping_per_group``) -- per-group
    |oc| == 1, no cross-group identity. STRICTLY IMPLIED.
  * Iter 214 (``input_color_uniform_per_group``) -- per-group |ic| ==
    1, no cross-group identity. STRICTLY IMPLIED.
  * Iter 13 (``identity_transformation``) -- zero change groups per
    pair. STRICT MUTUAL EXCLUSION.
  * Iter 10 (``sequential_recoloring``) -- per-group |oc| == 1 with
    singletons forming a contiguous range. INDEPENDENT in general;
    co-fires only on the degenerate length-1 range cell.
  * Iter 195 / 196 / 197 (per-group cardinality cross-pair constancy)
    -- STRICTLY IMPLIED at K == K == K_prod == 1.
  * Iter 198 / 199 (per-group palette-shift constancy) -- requires
    |ic| == |oc| per group. STRICTLY IMPLIED (single global k =
    K - C, trivially constant across all groups and pairs).
  * Iter 200-206 (per-group palette-relation cells) -- INDEPENDENT
    in general; cell-by-cell intersection at the |ic| == |oc| == 1
    row.
  * Every cell- / position- / dimension-axis matcher -- orthogonal
    to global singleton recolour.

Why this matters for ARBOR's intended ruleset:

  * "Single global recolour C -> K" rule family -- the simplest
    coloring-action rule shape: a single ``coloring(grid, selection_
    where_input == C, K)`` call with both C and K determinable from
    training as global constants. This matcher names the precondition
    for that rule family, in a single registry slot, so anti-
    unification can attach the right gate to rules of this shape
    without rediscovering the iter 14 ∧ iter 18 intersection each
    time.
  * Closes the iter-215-named candidate (vi): the whole-task
    projection of iter 215 at the iter 14 AND iter 18 intersection.
    With this matcher landed, the singleton-recolour axis is now
    named at two resolutions: per-group (iter 215, with per-group
    choices varying across groups) AND whole-task (this matcher,
    with single global C and K across all groups). The previously-
    implicit iter 14 ∧ iter 18 conjunction is now a first-class
    recognition handle.

Params:
  (none) -- pure whole-task global singleton-recolour check, universal
  over groups and pairs.

Returns True iff:
  - ``patterns`` is a dict, AND
  - ``patterns["pair_analyses"]`` is a non-empty list, AND
  - every analysis is a dict, AND
  - every analysis has a non-empty ``groups`` list (identity-territory
    rejection), AND
  - every group is a dict with list-typed ``input_colors`` and
    ``output_colors`` fields, AND
  - every group has ``len(input_colors) == 1`` AND
    ``len(output_colors) == 1``, AND
  - all single input colours across all groups in all pairs are
    bit-identical, AND
  - all single output colours across all groups in all pairs are
    bit-identical.

Why fail-closed on empty / no-group / malformed: same posture as iter
14 / 18 / 215. A missing or zero-group pair is upstream extractor
breakage or identity-territory; a whole-task single-global-recolour
claim with zero observations is meaningless.

Why ``len(input_colors) == 1`` / ``len(output_colors) == 1`` rather
than the set-level ``len(set(input_colors)) == 1``: same posture as
iter 14 / iter 18 (the immediate parents) -- the matcher inherits
their first-entry semantics. The fields are sorted unique-int lists
emitted by ``ExtractPatternOperator._analyze_pair``; ``len() == 1`` on
a unique-int list is equivalent to ``len(set()) == 1`` on the raw
list, but matching iter 14 / iter 18's exact wording forecloses any
drift between the parent matchers and this conjunction.

No companion-touch required: ``input_colors`` and ``output_colors``
have been emitted per group since iter 1 (``_analyze_pair`` in
``agent/active_operators.py``); this iter is a pure matcher addition
with no ``agent/active_operators.py`` diff. F8 inert.
"""

from __future__ import annotations

from agent.conditions import register


@register("singleton_recolor")
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
        if not isinstance(groups, list) or len(groups) == 0:
            return False
        for group in groups:
            if not isinstance(group, dict):
                return False
            in_colors = group.get("input_colors")
            out_colors = group.get("output_colors")
            if not isinstance(in_colors, list) or len(in_colors) != 1:
                return False
            if not isinstance(out_colors, list) or len(out_colors) != 1:
                return False
            observed_input_colors.add(in_colors[0])
            observed_output_colors.add(out_colors[0])
            if len(observed_input_colors) > 1:
                return False
            if len(observed_output_colors) > 1:
                return False
    return (
        len(observed_input_colors) == 1
        and len(observed_output_colors) == 1
    )
