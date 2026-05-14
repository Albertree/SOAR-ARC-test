"""
singleton_recolor_nonidentity_unanchored_function_shaped -- match tasks
where every group of every example pair has BOTH
``len(set(input_colors)) == 1`` AND ``len(set(output_colors)) == 1`` AND
``set(input_colors) != set(output_colors)`` AND ``len(observed_input_
colors) > 1`` (NOT cross-group identity on the INPUT side) AND
``len(observed_output_colors) > 1`` (NOT cross-group identity on the
OUTPUT side) AND a strict function-shape constraint on the (C_g, K_g)
cross-product: every distinct per-group C_g (input singleton) maps to
exactly one K_g (output singleton) across all groups and pairs.

The strict refinement of iter 223 (``singleton_recolor_nonidentity_
unanchored``) at the function-shape sub-cell -- the iter-8 ^ iter-223
cofire cell. Names the precondition for the rule family "whole-task
per-group strict-recolour with a function-shaped colour-mapping table".

Recognition vocabulary axis: the function-shape sub-cell of iter 223's
(F, F) "neither anchored" territory on iter 218's 2x2 cross-group-
identity product axis. Iter 223 names the (F, F) cell of that 2x2
axis -- both sides per-group, with |observed_input| > 1 AND
|observed_output| > 1. Within iter 223's territory the (C_g, K_g)
cross-product can be either:

  * Function-shaped (every distinct C_g maps to exactly one K_g across
    all observations). The iter-8 ^ iter-223 cofire cell. THIS matcher.
    The simplest rule shape on the (F, F) cell that admits anti-
    unification of the (C_g, K_g) substitution into a deterministic
    colour-mapping table -- the per-group C_g -> K_g mapping is a
    function and can be persisted as a finite table.
  * Non-function-shaped (some C_g maps to multiple K_g's). The
    strict-complement sub-cell -- requires per-group input context
    beyond the (C_g, K_g) mapping table (e.g., the group's position,
    shape, index, palette) to disambiguate. Companion candidate (xv)
    from iter 223's "Next gap"; not landed by this iter.

The two cells together partition iter 223's territory exhaustively
along the function-shape sub-axis. This iter names the function-shape
cell; the non-function-shape cell remains the closest-fitting sibling
for the next iter.

This matcher names the precondition for the rule family "whole-task
non-identity recolour with per-group input source C_g and per-group
output target K_g, both varying across groups, with the (C_g, K_g)
mapping function-shaped" -- rules whose action is "paint every
singleton blob of per-group input colour C_g with the per-group target
K_g, where C_g != K_g on every group, both C_g and K_g vary across
groups, AND the C_g -> K_g mapping is a deterministic function".
Iter 223 admits both function-shaped and non-function-shaped rule
families on the (F, F) cell; this matcher names only the function-
shaped sub-family. The function-shape constraint is what makes the
mapping anti-unifiable into a single rule shared across the groups --
without it, the per-group (C_g, K_g) substitution would require
per-group context beyond the bare (C_g) input.

Strict relations to iter 223 (the immediate parent):

  * Iter 223 (``singleton_recolor_nonidentity_unanchored``): STRICT
    REFINEMENT. This matcher fires => iter 223 fires (per-group |ic|
    == |oc| == 1 AND per-group ic != oc AND |observed_input| > 1 AND
    |observed_output| > 1 are all preconditions). The converse fails
    on any iter-223 task whose (C_g, K_g) cross-product is non-
    function-shaped (some C_g maps to multiple K_g's). That sub-cell
    is the companion (xv) territory.

Strict relations to iter 8 (``consistent_color_mapping``):

  * Iter 8: STRICT REFINEMENT. Iter 8 demands the global ic -> oc
    cross-product be function-shaped on the union of all pairs' groups
    (the "function shape" property: every observed input colour has
    exactly one observed output colour). This matcher additionally
    requires the iter-223 territory (per-group singleton row AND
    per-group ic != oc AND both-sides-per-group). The converse fails
    on any iter-8 task that is NOT on the per-group singleton row
    OR has cross-group identity on either side (iter 220 / 221 / 222
    territory) OR has any per-group ic == oc.

Strict relations to iter 218 / iter 220 / iter 221 / iter 222 (the
grandparents on iter 218's 2x2 axis):

  * Iter 218 (``singleton_recolor_nonidentity_per_group``): STRICT
    REFINEMENT (via iter 223).
  * Iter 220 (``singleton_recolor_nonidentity``): STRICT MUTUAL
    EXCLUSION. Iter 220 demands cross-group identity on BOTH sides;
    this matcher (via iter 223) demands non-identity on BOTH sides.
    Disjoint by both anchor splits.
  * Iter 221 (``singleton_recolor_nonidentity_input_anchored``):
    STRICT MUTUAL EXCLUSION. Iter 221 demands cross-group identity on
    the INPUT side; this matcher demands non-identity on the INPUT
    side. Disjoint by the input-anchor split.
  * Iter 222 (``singleton_recolor_nonidentity_output_anchored``):
    STRICT MUTUAL EXCLUSION. Iter 222 demands cross-group identity on
    the OUTPUT side; this matcher demands non-identity on the OUTPUT
    side. Disjoint by the output-anchor split.

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
    (one-element-codomain).
  * Iter 214 (``input_color_uniform_per_group``): STRICTLY IMPLIED.
    This matcher demands per-group |ic| == 1.

Strict relation to iter 10 (``sequential_recoloring``): INDEPENDENT in
general; co-fires on the contiguous-range sub-cell of this matcher's
territory. The iter-10 canonical fixture (ic=[0]/oc=[3], ic=[1]/oc=[4],
ic=[2]/oc=[5]) is function-shaped (0 -> 3, 1 -> 4, 2 -> 5) AND
contiguous-range on the output side. So iter 10 co-fires on the
iter-10 canonical fixture (the DISTINGUISHING co-fire witness).
Outside the contiguous-range sub-cell iter 10 rejects (e.g., a
function-shaped non-contiguous mapping like 3 -> 0, 5 -> 7).

Strict relation to iter 13 (``identity_transformation``): STRICT
MUTUAL EXCLUSION (iter 13 fires iff every pair has zero change
groups; this matcher requires at least two distinct C_g AND two
distinct K_g values witnessed).

Strict relations to iter 195 / 196 / 197 (per-group cardinality
matchers): STRICTLY IMPLIED at K_in == K_out == K_prod == 1 (same
as iter 223).

Strict relations to iter 198 / iter 199 (palette-shift constancy):
INDEPENDENT in general; co-fires only on the within-pair-constant-
shift sub-cell (same posture as iter 223 -- this matcher does not
constrain per-pair k_g constancy).

Strict relation to iter 201 (``output_colors_equals_input_colors_per_
group``): STRICT MUTUAL EXCLUSION (this matcher forces per-group ic
!= oc, hence per-group set(ic) != set(oc)).

Strict relation to iter 203 (``output_colors_disjoint_from_input_
colors_per_group``): STRICTLY IMPLIED (on the singleton row with ic
!= oc, the two 1-element sets are always disjoint).

Why a distinct matcher rather than just AND-ing iter 223 with iter 8
at the rule level: the matcher contract (docs/RULE_FORMAT.md §4) is
name-keyed recognition vocabulary; the rule's stored ``condition.type``
is the recognition handle's name, not a Boolean composition tree. A
rule whose precondition is "per-group |ic| == |oc| == 1 AND per-group
ic != oc AND |observed_input| > 1 AND |observed_output| > 1 AND
function-shaped (C_g, K_g) cross-product" gates a DIFFERENT rule
family (anti-unifiable to a deterministic colour-mapping table) than
iter 223 alone (admitting both function-shaped and non-function-shaped
sub-cells). Keeping the conjunction as a separate registry slot lets
anti-unification (CLAUDE.md §8) attach the right gate per rule family
-- specifically the gate for rules whose action is a finite C_g -> K_g
mapping table -- without rediscovering the iter 223 ^ iter 8
intersection from the rule's stored action shape.

Why a distinct matcher rather than parameterising iter 223 with a
``function_shaped: True`` flag: the matcher contract is name-keyed
recognition vocabulary; the rule's stored ``condition.type`` is the
recognition handle's name, not a name+params tuple. The function-
shape sub-cell of iter 223 is structurally identifiable as a strict
refinement (the iter-8 ^ iter-223 cofire cell) -- it is a recognition
handle in its own right (the simplest sub-cell of iter 223 that
admits anti-unification into a deterministic colour-mapping table),
not a Boolean parameter of the (F, F) per-group recolour axis.

Why this matters as the function-shape SPLIT of iter 223's territory:
iter 223 closes iter 218's 2x2 cross-group-identity axis at the (F,
F) cell -- "neither anchored", both sides per-group. The natural next
sub-axis on the (F, F) cell is the function-shape split: does the
per-group (C_g, K_g) mapping form a function, or does some C_g map
to multiple K_g's? Function-shape is the cleanest split because it
exactly separates the rules anti-unification can express as a finite
mapping table (this matcher's cell) from those that require
additional per-group context (the companion candidate (xv) cell). The
two cells together name the iter-8 cofire / non-cofire split on iter
223's territory at two disjoint cells -- the function-shape sub-axis.

Strict refinement / orthogonality summary (universal-over-groups-and-
pairs semantics, per-group |ic| == |oc| == 1 AND ic != oc AND
|observed_input_colors| > 1 AND |observed_output_colors| > 1 AND
the (C_g, K_g) cross-product is function-shaped):

  * Iter 223 (``singleton_recolor_nonidentity_unanchored``) -- STRICT
    REFINEMENT (this matcher additionally requires function-shape).
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
  * Iter 8 (``consistent_color_mapping``) -- STRICT REFINEMENT (iter
    8 demands function-shape globally; this matcher additionally
    requires the iter-223 territory).
  * Iter 13 (``identity_transformation``) -- STRICT MUTUAL EXCLUSION.
  * Iter 10 (``sequential_recoloring``) -- INDEPENDENT (co-fires on
    the contiguous-range sub-cell of this matcher's territory; the
    DISTINGUISHING co-fire witness includes the iter-10 canonical
    fixture).
  * Iter 195 / 196 / 197 -- STRICTLY IMPLIED at K_in == K_out ==
    K_prod == 1.
  * Iter 198 / 199 (palette-shift constancy) -- INDEPENDENT
    (co-fires only on the within-pair-constant-shift sub-cell).
  * Iter 201 (``output_colors_equals_input_colors_per_group``) --
    STRICT MUTUAL EXCLUSION.
  * Iter 203 (``output_colors_disjoint_from_input_colors_per_group``)
    -- STRICTLY IMPLIED.
  * Iter 213 / 214 -- STRICTLY IMPLIED.
  * Iter 200 / 202 / 204 / 205 / 206 (per-group palette-relation
    cells) -- STRICTLY MUTUALLY EXCLUSIVE with this matcher on the
    |ic| == |oc| == 1 row.
  * Every cell- / position- / dimension-axis matcher -- orthogonal
    to per-group singleton input-per-group / output-per-group
    function-shaped strict-recolour.

Why this matters for ARBOR's intended ruleset:

  * "Function-shaped input-per-group / output-per-group strict-
    recolour" rule family -- rules whose action is "paint every
    singleton blob of per-group input colour C_g with the per-group
    target K_g, where C_g != K_g per group, both C_g and K_g vary
    across groups, AND the C_g -> K_g mapping is a deterministic
    function". The cleanest sub-cell of iter 223 that admits anti-
    unification of the (C_g, K_g) substitution into a finite mapping
    table -- the substitution is a single function expression, not
    one per group. The building block from which more complex
    function-shaped recolour rules (e.g., "the function table itself
    depends on the input's palette / dimensions / index") generalise.
    This matcher names the precondition for that rule family in a
    single registry slot, so anti-unification can attach the right
    gate to rules of this shape without having to rediscover the
    iter 223 ^ iter 8 intersection each time.
  * Closes the iter-223-named candidate (xiv): "the function-shape
    sub-axis SPLIT of iter 223's (F, F) territory: a single matcher
    pinning |ic| == |oc| == 1 AND per-group ic != oc AND
    |observed_input| > 1 AND |observed_output| > 1 AND a strict
    function-shape constraint on the (C_g, K_g) cross-product".

Params:
  (none) -- pure per-group function-shaped recolour check, universal
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
    int in ``range(10)`` (bool rejected per the iter-14 / 18 / 200-206
    / 213-223 strict-type posture), AND
  - for every group, ``len(set(input_colors)) == 1`` AND
    ``len(set(output_colors)) == 1`` AND
    ``set(input_colors) != set(output_colors)``, AND
  - ``len(observed_input_colors) > 1`` (NOT cross-group identity on
    the INPUT side), AND
  - ``len(observed_output_colors) > 1`` (NOT cross-group identity on
    the OUTPUT side), AND
  - the (C_g, K_g) cross-product is FUNCTION-SHAPED: every distinct
    C_g maps to exactly one K_g across all observed groups and pairs.

Why fail-closed on empty / no-group / malformed (same posture as
iter 8 / 13 / 14 / 18 / 30-39 / 184-223): a missing or zero-group
pair is upstream extractor breakage or iter 13's no-blob-identity
territory; a whole-task function-shaped input-per-group / output-
per-group strict-recolour claim with zero observations is meaning-
less, AND admitting it would collapse this matcher's territory into
iter 13's.

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


@register("singleton_recolor_nonidentity_unanchored_function_shaped")
def match(patterns: dict, params: dict) -> bool:
    if not isinstance(patterns, dict):
        return False
    pair_analyses = patterns.get("pair_analyses")
    if not isinstance(pair_analyses, list) or not pair_analyses:
        return False

    observed_input_colors: set = set()
    observed_output_colors: set = set()
    color_map: dict = {}
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
            mapped = color_map.get(ic_val)
            if mapped is None:
                color_map[ic_val] = oc_val
            elif mapped != oc_val:
                return False
            observed_input_colors |= ic_set
            observed_output_colors |= oc_set
    if len(observed_input_colors) <= 1:
        return False
    if len(observed_output_colors) <= 1:
        return False
    return True
