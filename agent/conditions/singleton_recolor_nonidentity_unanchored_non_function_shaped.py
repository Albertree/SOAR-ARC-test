"""
singleton_recolor_nonidentity_unanchored_non_function_shaped -- match
tasks where every group of every example pair has BOTH
``len(set(input_colors)) == 1`` AND ``len(set(output_colors)) == 1``
AND ``set(input_colors) != set(output_colors)`` AND
``len(observed_input_colors) > 1`` (NOT cross-group identity on the
INPUT side) AND ``len(observed_output_colors) > 1`` (NOT cross-group
identity on the OUTPUT side) AND the (C_g, K_g) cross-product is
NON-function-shaped (some distinct per-group C_g maps to MULTIPLE
distinct K_g values across the observed groups and pairs).

The strict-disjoint complement of iter 224 (``singleton_recolor_non
identity_unanchored_function_shaped``) within iter 223 (``singleton_
recolor_nonidentity_unanchored``)'s territory; closes iter 223's
function-shape sub-axis at the non-function-shape cell.

Recognition vocabulary axis: the non-function-shape sub-cell of iter
223's (F, F) "neither anchored" territory on iter 218's 2x2 cross-
group-identity product axis. Iter 223 names the (F, F) cell of that
2x2 axis -- both sides per-group, with |observed_input| > 1 AND
|observed_output| > 1. Within iter 223's territory the (C_g, K_g)
cross-product can be either:

  * Function-shaped (every distinct C_g maps to exactly one K_g
    across all observations). The iter-8 ^ iter-223 cofire cell.
    Named by iter 224.
  * Non-function-shaped (some C_g maps to multiple K_g's). The
    strict-complement sub-cell -- iter 8 REJECTS. Requires per-group
    input context beyond the (C_g, K_g) mapping table (e.g., the
    group's position, shape, index, palette) to disambiguate. THIS
    matcher.

The two cells together partition iter 223's territory exhaustively
along the function-shape sub-axis. Iter 224 names the function-shape
cell; this matcher names the non-function-shape cell. With both
landed, iter 223's function-shape sub-axis is exhaustively named at
two disjoint recognition handles.

This matcher names the precondition for the rule family "whole-task
non-identity recolour with per-group input source C_g and per-group
output target K_g, both varying across groups, with the (C_g, K_g)
mapping NON-function-shaped" -- rules whose action is "paint every
singleton blob of per-group input colour C_g with the per-group
target K_g, where C_g != K_g on every group, both C_g and K_g vary
across groups, AND the C_g -> K_g mapping is NOT a function (some
C_g sees multiple K_g's, so the K_g target must be disambiguated by
per-group context beyond bare C_g)". The strict-complement of iter
224's rule family on iter 223's territory -- rules where anti-
unification cannot collapse the (C_g, K_g) substitution into a
finite mapping table because the mapping is many-valued.

Strict relations to iter 224 (the immediate sibling on the function-
shape sub-axis):

  * Iter 224 (``singleton_recolor_nonidentity_unanchored_function_
    shaped``): STRICT MUTUAL EXCLUSION. Iter 224 demands function-
    shape on the (C_g, K_g) cross-product; this matcher demands
    non-function-shape. Disjoint by the function-shape split. The
    two together partition iter 223's territory exhaustively on
    the function-shape sub-axis.

Strict relations to iter 223 (the immediate parent):

  * Iter 223 (``singleton_recolor_nonidentity_unanchored``): STRICT
    REFINEMENT. This matcher fires => iter 223 fires (per-group |ic|
    == |oc| == 1 AND per-group ic != oc AND |observed_input| > 1
    AND |observed_output| > 1 are all preconditions). The converse
    fails on any iter-223 task whose (C_g, K_g) cross-product is
    function-shaped (iter-224 territory).

Strict relations to iter 8 (``consistent_color_mapping``):

  * Iter 8: STRICT MUTUAL EXCLUSION. Iter 8 demands the global ic
    -> oc cross-product be function-shaped on the union of all
    pairs' groups; this matcher demands NON-function-shape on the
    same cross-product. The two are pairwise disjoint by the
    function-shape split. The DUAL of iter 224's relation to iter
    8 (iter 224 is STRICT REFINEMENT of iter 8; this matcher is
    STRICT MUTUAL EXCLUSION).

Strict relations to iter 218 / iter 220 / iter 221 / iter 222 (the
grandparents on iter 218's 2x2 axis):

  * Iter 218 (``singleton_recolor_nonidentity_per_group``): STRICT
    REFINEMENT (via iter 223).
  * Iter 220 (``singleton_recolor_nonidentity``): STRICT MUTUAL
    EXCLUSION. Iter 220 demands cross-group identity on BOTH sides;
    this matcher (via iter 223) demands non-identity on BOTH sides.
    Disjoint by both anchor splits.
  * Iter 221 (``singleton_recolor_nonidentity_input_anchored``):
    STRICT MUTUAL EXCLUSION. Iter 221 demands cross-group identity
    on the INPUT side; this matcher demands non-identity on the
    INPUT side. Disjoint by the input-anchor split. Notable: iter
    221's territory is by construction non-function-shaped (one C
    maps to multiple K_g's), but it fails the |observed_input| > 1
    precondition.
  * Iter 222 (``singleton_recolor_nonidentity_output_anchored``):
    STRICT MUTUAL EXCLUSION. Iter 222 demands cross-group identity
    on the OUTPUT side; this matcher demands non-identity on the
    OUTPUT side. Disjoint by the output-anchor split.

Strict relations to iter 217 / iter 219:

  * Iter 217 (``singleton_recolor_identity_per_group``): STRICT MUTUAL
    EXCLUSION. Iter 217 demands per-group ic == oc on every group;
    this matcher demands per-group ic != oc on every group. Disjoint.
  * Iter 219 (``singleton_recolor_identity``): STRICT MUTUAL
    EXCLUSION. Iter 219 demands C == K globally; this matcher demands
    per-group ic != oc.

Strict relations to iter 215 / iter 216:

  * Iter 215 (``singleton_recolor_per_group``): STRICT REFINEMENT.
  * Iter 216 (``singleton_recolor``): STRICT MUTUAL EXCLUSION (iter
    216 demands cross-group identity on BOTH sides; this matcher
    demands NON-identity on BOTH sides).

Strict relations to iter 14 (``input_color_uniform``) AND iter 18
(``output_color_uniform``):

  * Iter 14: STRICT MUTUAL EXCLUSION (iter 14 demands cross-group
    input uniformity; this matcher demands |observed_input| > 1).
  * Iter 18: STRICT MUTUAL EXCLUSION (iter 18 demands cross-group
    output uniformity; this matcher demands |observed_output| > 1).

Strict relations to iter 213 / iter 214 / iter 215:

  * Iter 213 (``consistent_color_mapping_per_group``): STRICTLY
    IMPLIED. This matcher demands per-group |oc| == 1, which forces
    the per-group oc cross-product to be function-shaped trivially
    (one-element-codomain). Iter 213 fires per-group regardless of
    the cross-group function-shape; only the GLOBAL cross-product
    (across all groups and pairs) is non-function-shaped.
  * Iter 214 (``input_color_uniform_per_group``): STRICTLY IMPLIED.
    This matcher demands per-group |ic| == 1.

Strict relation to iter 10 (``sequential_recoloring``): STRICT MUTUAL
EXCLUSION on the iter-10 canonical fixture (ic=[0]/oc=[3], ic=[1]/
oc=[4], ic=[2]/oc=[5]) -- that fixture is function-shaped, hence in
iter-224 territory, not this matcher's. More generally iter 10
demands per-group |oc| == 1 with the per-pair oc singletons forming
a contiguous range >= 2 -- iter 10 can co-fire with this matcher
only when the function-shape failure is consistent with the
contiguous-range claim, which requires the same input C_g to map to
distinct outputs in a contiguous range across pairs -- a degenerate
sub-cell. INDEPENDENT in general.

Strict relation to iter 13 (``identity_transformation``): STRICT
MUTUAL EXCLUSION (iter 13 fires iff every pair has zero change
groups; this matcher requires at least two distinct C_g AND two
distinct K_g values witnessed, with non-function-shape demanding
at least two distinct C_g -> K_g mappings sharing a C_g).

Strict relations to iter 195 / 196 / 197 (per-group cardinality
matchers): STRICTLY IMPLIED at K_in == K_out == K_prod == 1 (same
as iter 223 / 224).

Strict relations to iter 198 / iter 199 (palette-shift constancy):
INDEPENDENT in general; non-function-shape implies the per-group
shift k_g = K_g - C_g cannot be constant across all groups (some
C_g sees multiple K_g's, hence multiple shifts share the same
C_g), so iter 198 / 199 typically REJECT on this matcher's
territory. But the per-pair within-pair shift can still be
constant in degenerate sub-cells (e.g., pair 1: (3, 0), pair 2:
(3, 7) -- non-function-shape across pairs, constant shift within
each pair). INDEPENDENT in general (typically REJECTS).

Strict relation to iter 201 (``output_colors_equals_input_colors_
per_group``): STRICT MUTUAL EXCLUSION (this matcher forces per-
group ic != oc, hence per-group set(ic) != set(oc)).

Strict relation to iter 203 (``output_colors_disjoint_from_input_
colors_per_group``): STRICTLY IMPLIED (on the singleton row with
ic != oc, the two 1-element sets are always disjoint).

Why a distinct matcher rather than the negation of iter 224 at
the rule level: the matcher contract (docs/RULE_FORMAT.md §4) is
name-keyed recognition vocabulary; the rule's stored
``condition.type`` is the recognition handle's name, not a Boolean
composition tree. A rule whose precondition is "per-group |ic| ==
|oc| == 1 AND per-group ic != oc AND |observed_input| > 1 AND
|observed_output| > 1 AND non-function-shape (C_g, K_g) cross-
product" gates a DIFFERENT rule family (rules where the (C_g, K_g)
substitution requires per-group context beyond the bare (C_g)
input) than iter 224 alone (admitting only function-shaped
mappings) or iter 223 alone (admitting both). Keeping the
conjunction as a separate registry slot lets anti-unification
(CLAUDE.md §8) attach the right gate per rule family --
specifically the gate for rules whose action must consult per-
group context (position, shape, index, palette) to determine K_g
-- without rediscovering the iter 223 ^ NOT iter 8 intersection
from the rule's stored action shape.

Why a distinct matcher rather than parameterising iter 223 with a
``function_shaped: False`` flag: the matcher contract is name-keyed
recognition vocabulary; the rule's stored ``condition.type`` is the
recognition handle's name, not a name+params tuple. The non-
function-shape sub-cell of iter 223 is structurally identifiable
as the strict-disjoint complement of iter 224 within iter 223 --
it is a recognition handle in its own right (the simplest sub-cell
of iter 223 that does NOT admit anti-unification into a
deterministic colour-mapping table), not a Boolean parameter of
the (F, F) per-group recolour axis.

Why this matters as the closing cell of iter 223's function-shape
sub-axis: with iter 224 naming the function-shape cell and this
matcher naming the non-function-shape cell, both cells of iter
223's function-shape sub-axis are named at disjoint recognition
handles. The two cells partition iter 223's territory exhaustively
on the function-shape axis -- every iter-223 task lands in exactly
one of the two named cells. This closes iter 223's function-shape
sub-axis as a fully-resolved sub-territory.

Strict refinement / orthogonality summary (universal-over-groups-
and-pairs semantics, per-group |ic| == |oc| == 1 AND ic != oc AND
|observed_input_colors| > 1 AND |observed_output_colors| > 1 AND
the (C_g, K_g) cross-product is NOT function-shaped):

  * Iter 223 (``singleton_recolor_nonidentity_unanchored``) -- STRICT
    REFINEMENT (this matcher additionally requires non-function-
    shape).
  * Iter 224 (``singleton_recolor_nonidentity_unanchored_function_
    shaped``) -- STRICT MUTUAL EXCLUSION (the function-shape split
    on iter 223's territory).
  * Iter 218 (``singleton_recolor_nonidentity_per_group``) -- STRICT
    REFINEMENT (via iter 223).
  * Iter 220 / iter 221 / iter 222 -- STRICT MUTUAL EXCLUSION (each
    demands at least one cross-group anchor; this matcher demands
    non-identity on BOTH sides).
  * Iter 219 (``singleton_recolor_identity``) -- STRICT MUTUAL
    EXCLUSION (iter 219 demands C == K).
  * Iter 217 (``singleton_recolor_identity_per_group``) -- STRICT
    MUTUAL EXCLUSION (iter 217 demands per-group ic == oc).
  * Iter 216 (``singleton_recolor``) -- STRICT MUTUAL EXCLUSION
    (iter 216 demands cross-group identity on BOTH sides).
  * Iter 215 (``singleton_recolor_per_group``) -- STRICT REFINEMENT
    (per-group |ic| == |oc| == 1 is a precondition).
  * Iter 14 (``input_color_uniform``) -- STRICT MUTUAL EXCLUSION.
  * Iter 18 (``output_color_uniform``) -- STRICT MUTUAL EXCLUSION.
  * Iter 8 (``consistent_color_mapping``) -- STRICT MUTUAL EXCLUSION
    (iter 8 demands function-shape globally; this matcher demands
    NON-function-shape).
  * Iter 13 (``identity_transformation``) -- STRICT MUTUAL EXCLUSION.
  * Iter 10 (``sequential_recoloring``) -- INDEPENDENT (typically
    REJECTS; co-fires only on degenerate sub-cells).
  * Iter 195 / 196 / 197 -- STRICTLY IMPLIED at K_in == K_out ==
    K_prod == 1.
  * Iter 198 / 199 (palette-shift constancy) -- INDEPENDENT
    (typically REJECTS since non-function-shape breaks the per-
    group shift constancy on the shared C_g entries).
  * Iter 201 (``output_colors_equals_input_colors_per_group``) --
    STRICT MUTUAL EXCLUSION.
  * Iter 203 (``output_colors_disjoint_from_input_colors_per_group``)
    -- STRICTLY IMPLIED.
  * Iter 213 / 214 -- STRICTLY IMPLIED.
  * Iter 200 / 202 / 204 / 205 / 206 (per-group palette-relation
    cells) -- STRICTLY MUTUALLY EXCLUSIVE with this matcher on the
    |ic| == |oc| == 1 row.
  * Every cell- / position- / dimension-axis matcher -- orthogonal
    to per-group singleton non-function-shape strict-recolour.

Why this matters for ARBOR's intended ruleset:

  * "Non-function-shaped input-per-group / output-per-group strict-
    recolour" rule family -- rules whose action is "paint every
    singleton blob of per-group input colour C_g with the per-group
    target K_g, where C_g != K_g per group, both C_g and K_g vary
    across groups, AND the C_g -> K_g mapping is NOT a function
    (some C_g sees multiple K_g's, so K_g must be disambiguated by
    per-group context)". The strict-complement of iter 224's rule
    family on iter 223's territory -- rules that REQUIRE per-group
    context (position / shape / index / palette / neighbourhood) to
    pick the K_g target, because the bare (C_g) input is insufficient.
    The building block from which more complex per-group context-
    dependent recolour rules generalise. This matcher names the
    precondition for that rule family in a single registry slot,
    so anti-unification can attach the right gate to rules of this
    shape -- specifically rules whose action expression includes
    a per-group context selector beyond bare (C_g) -- without
    having to rediscover the iter 223 ^ NOT iter 8 intersection
    each time.
  * Closes the iter-224-named candidate (xv): "the strict-complement
    non-function-shape sub-cell of iter 223: a single matcher
    pinning |ic| == |oc| == 1 AND per-group ic != oc AND
    |observed_input| > 1 AND |observed_output| > 1 AND the (C_g,
    K_g) cross-product is NON-function-shaped (some C_g maps to
    multiple K_g's across the observed groups and pairs)". With
    this matcher landed, both cells of iter 223's function-shape
    sub-axis are named (iter 224 / this matcher). The sub-axis is
    exhaustively partitioned on iter 223's territory.

Params:
  (none) -- pure per-group non-function-shaped recolour check,
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
    strict int in ``range(10)`` (bool rejected per the iter-14 / 18
    / 200-206 / 213-224 strict-type posture), AND
  - for every group, ``len(set(input_colors)) == 1`` AND
    ``len(set(output_colors)) == 1`` AND
    ``set(input_colors) != set(output_colors)``, AND
  - ``len(observed_input_colors) > 1`` (NOT cross-group identity on
    the INPUT side), AND
  - ``len(observed_output_colors) > 1`` (NOT cross-group identity on
    the OUTPUT side), AND
  - the (C_g, K_g) cross-product is NOT FUNCTION-SHAPED: at least
    one distinct C_g maps to >= 2 distinct K_g values across the
    observed groups and pairs.

Why fail-closed on empty / no-group / malformed (same posture as
iter 8 / 13 / 14 / 18 / 30-39 / 184-224): a missing or zero-group
pair is upstream extractor breakage or iter 13's no-blob-identity
territory; a whole-task non-function-shaped input-per-group /
output-per-group strict-recolour claim with zero observations is
meaningless, AND admitting it would collapse this matcher's
territory into iter 13's.

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


@register("singleton_recolor_nonidentity_unanchored_non_function_shaped")
def match(patterns: dict, params: dict) -> bool:
    if not isinstance(patterns, dict):
        return False
    pair_analyses = patterns.get("pair_analyses")
    if not isinstance(pair_analyses, list) or not pair_analyses:
        return False

    observed_input_colors: set = set()
    observed_output_colors: set = set()
    # Map C_g -> set of observed K_g values across the union of all
    # groups across all pairs. Non-function-shape iff any C_g sees
    # more than one distinct K_g.
    c_to_k: dict = {}
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
            (ic_val,) = ic_set
            (oc_val,) = oc_set
            ks = c_to_k.setdefault(ic_val, set())
            ks.add(oc_val)
            observed_input_colors |= ic_set
            observed_output_colors |= oc_set
    if len(observed_input_colors) <= 1:
        return False
    if len(observed_output_colors) <= 1:
        return False
    # Non-function-shape: some C_g maps to multiple K_g values.
    for ks in c_to_k.values():
        if len(ks) > 1:
            return True
    return False
