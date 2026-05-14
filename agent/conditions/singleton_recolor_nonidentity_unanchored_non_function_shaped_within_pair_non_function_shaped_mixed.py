"""
singleton_recolor_nonidentity_unanchored_non_function_shaped_within_
pair_non_function_shaped_mixed -- match tasks where every group of
every example pair has BOTH ``len(set(input_colors)) == 1`` AND
``len(set(output_colors)) == 1`` AND ``set(input_colors) != set(
output_colors)`` AND ``len(observed_input_colors) > 1`` (NOT cross-
group identity on the INPUT side) AND ``len(observed_output_colors)
> 1`` (NOT cross-group identity on the OUTPUT side) AND the GLOBAL
(C_g, K_g) cross-product is NON-function-shaped (some distinct per-
group C_g maps to MULTIPLE distinct K_g values across the union of
all groups across all pairs -- iter 225 territory) AND SOME pair has
WITHIN-pair NON-function-shape (some C_g sees >= 2 distinct K_g
values within that pair's OWN groups -- iter 227 territory) AND
SOME pair has WITHIN-pair FUNCTION-shape (every C_g in that pair
sees exactly one K_g within that pair's OWN groups -- strict
complement of iter 228's universal-pair claim).

The strict-disjoint complement of iter 228 (``singleton_recolor_
nonidentity_unanchored_non_function_shaped_within_pair_non_function_
shaped_universal``) WITHIN iter 227's territory (``singleton_recolor_
nonidentity_unanchored_non_function_shaped_within_pair_non_function_
shaped``). The "some pair within-pair non-function-shape AND some
pair within-pair function-shape" mixed-shape-across-pairs sub-cell
named by iter 228's "Next gap" candidate (xix).

Recognition vocabulary axis: the mixed-shape sub-cell of iter 227's
existential within-pair non-function-shape territory. Iter 227 names
"AT LEAST ONE pair has within-pair non-function-shape" (the strict-
disjoint complement of iter 226 within iter 225's territory); iter
228 names "EVERY pair has within-pair non-function-shape" (universal-
pair refinement of iter 227); this matcher names the strict-disjoint
complement of iter 228 within iter 227's territory -- "SOME pair has
within-pair non-function-shape AND SOME pair has within-pair
function-shape", the mixed-shape-across-pairs cell. Within iter
227's territory the universal-pair sub-axis splits into:

  * UNIVERSAL: every pair has within-pair non-function-shape (iter
    228). The maximally-restrictive sub-cell of iter 227.
  * MIXED-SHAPE: some pair has within-pair non-function-shape AND
    some pair has within-pair function-shape. THIS matcher. The
    cell where anti-unification can collapse the (C_g, K_g)
    substitution into a per-pair finite mapping table on the
    strict subset of pairs that are within-pair function-shape,
    but requires per-group context within the remaining pairs.

The two cells together partition iter 227's territory exhaustively
along the universal-pair within-pair non-function-shape sub-axis.
Iter 228 names the universal cell; this matcher names the mixed-
shape cell.

This matcher names the precondition for the rule family "whole-task
strict-recolour where some pairs admit per-pair finite mapping table
abstraction and others do not" -- rules where anti-unification can
collapse the (C_g, K_g) substitution into a per-pair table on a
strict subset of pairs (the within-pair function-shape pairs) but
requires per-group context on the remaining pairs. The sub-cell of
iter 227's territory that admits per-pair table abstraction on SOME
but not ALL pairs.

Strict relations to iter 228 (the universal-pair sibling on iter
227's universal-pair sub-axis):

  * Iter 228 (``singleton_recolor_nonidentity_unanchored_non_function_
    shaped_within_pair_non_function_shaped_universal``): STRICT
    MUTUAL EXCLUSION. Iter 228 demands EVERY pair within-pair non-
    function-shape; this matcher demands SOME pair within-pair
    function-shape. Disjoint by definition.

Strict relations to iter 227 (the immediate parent):

  * Iter 227 (``singleton_recolor_nonidentity_unanchored_non_function_
    shaped_within_pair_non_function_shaped``): STRICT REFINEMENT.
    This matcher fires => iter 227 fires (mixed-shape strictly
    implies at-least-one-pair within-pair non-function-shape). The
    converse fails on the universal-pair sub-cell (iter 228) and
    on single-pair iter-225 fixtures where the sole pair has
    within-pair non-function-shape and there is no companion pair
    to be within-pair function-shape (iter 227 fires; this matcher
    rejects because the function-shape-pair existential fails).

Strict relations to iter 226 (the strict-disjoint sibling on iter
225's within-pair function-shape sub-axis):

  * Iter 226 (``singleton_recolor_nonidentity_unanchored_non_function_
    shaped_within_pair_function_shaped``): STRICT MUTUAL EXCLUSION.
    Iter 226 demands every pair within-pair FUNCTION-shape; this
    matcher demands at least one pair within-pair NON-function-
    shape. Disjoint via iter 227.

Strict relations to iter 225 (the grandparent):

  * Iter 225 (``singleton_recolor_nonidentity_unanchored_non_function_
    shaped``): STRICT REFINEMENT (via iter 227).

Strict relations to iter 224 (the function-shape sibling on iter 223's
function-shape sub-axis):

  * Iter 224 (``singleton_recolor_nonidentity_unanchored_function_
    shaped``): STRICT MUTUAL EXCLUSION (via iter 225 -- iter 224
    demands GLOBAL function-shape; this matcher demands GLOBAL
    non-function-shape).

Strict relations to iter 223 (the great-grandparent):

  * Iter 223 (``singleton_recolor_nonidentity_unanchored``): STRICT
    REFINEMENT.

Strict relations to iter 8 (``consistent_color_mapping``):

  * Iter 8: STRICT MUTUAL EXCLUSION (via iter 225 -- iter 8 demands
    the GLOBAL ic -> oc cross-product be function-shaped; this
    matcher demands GLOBAL non-function-shape).

Strict relations to iter 213 (``consistent_color_mapping_per_group``):

  * Iter 213: STRICTLY IMPLIED. Iter 213 demands per-GROUP function-
    shape on the |oc| == 1 row (every group has a single output
    colour); this matcher's per-group |oc| == 1 precondition forces
    iter 213 to fire trivially.

Strict relations to iter 218 / iter 220 / iter 221 / iter 222 (the
grandparents on iter 218's 2x2 cross-group-identity axis):

  * Iter 218 (``singleton_recolor_nonidentity_per_group``): STRICT
    REFINEMENT (via iter 225 / iter 223).
  * Iter 220 / iter 221 / iter 222: STRICT MUTUAL EXCLUSION (each
    demands at least one cross-group anchor; this matcher demands
    non-identity on BOTH sides via iter 225).

Strict relations to iter 217 / iter 219:

  * Iter 217 (``singleton_recolor_identity_per_group``): STRICT
    MUTUAL EXCLUSION (per-group ic != oc demanded by iter 225).
  * Iter 219 (``singleton_recolor_identity``): STRICT MUTUAL
    EXCLUSION.

Strict relations to iter 215 / iter 216:

  * Iter 215 (``singleton_recolor_per_group``): STRICT REFINEMENT.
  * Iter 216 (``singleton_recolor``): STRICT MUTUAL EXCLUSION.

Strict relations to iter 14 / iter 18:

  * Iter 14 (``input_color_uniform``): STRICT MUTUAL EXCLUSION
    (|observed_input| > 1 demanded by iter 225).
  * Iter 18 (``output_color_uniform``): STRICT MUTUAL EXCLUSION.

Strict relation to iter 10 (``sequential_recoloring``): INDEPENDENT
in general; iter 10 demands a contiguous range >= 2 on the per-pair
output singletons, which can co-fire with this matcher only on
degenerate sub-cells (iter 10 typically also requires per-pair
function-shape on the per-pair output groups, which conflicts with
the within-pair non-function-shape requirement on at least one pair
in this matcher's territory).

Strict relation to iter 13 (``identity_transformation``): STRICT
MUTUAL EXCLUSION (iter 13 demands zero changes per pair).

Strict relations to iter 195 / 196 / 197 (per-group cardinality
matchers): STRICTLY IMPLIED at K_in == K_out == K_prod == 1 (same
as iter 225 -- per-group |ic| == |oc| == 1 forces K=1 on every
axis).

Strict relations to iter 198 / iter 199 (palette-shift constancy):
INDEPENDENT in general -- typically REJECTS on this matcher's
territory. iter 198 / 199 demand a single constant shift k = K_g -
C_g across all groups (and across all pairs for iter 199). This
matcher's territory has within-pair non-function-shape on at least
one pair: some C_g in that pair sees multiple K_g's. If a constant
per-pair shift held on that pair, every C_g would map to exactly
one K_g within the pair (a function determined by the shift), so
iter 198 would force within-pair function-shape on every pair,
contradicting this matcher's at-least-one-pair non-function-shape
claim. Hence iter 198 / 199 REJECT on this matcher's territory.

Strict relation to iter 201 (``output_colors_equals_input_colors_
per_group``): STRICT MUTUAL EXCLUSION (per-group ic != oc forces
per-group set(ic) != set(oc)).

Strict relation to iter 203 (``output_colors_disjoint_from_input_
colors_per_group``): STRICTLY IMPLIED (singleton row with ic != oc
forces disjoint sets per group).

Why a distinct matcher rather than parameterising iter 227 with a
``some_pair_function_shape: True`` flag: the matcher contract
(docs/RULE_FORMAT.md §4) is name-keyed recognition vocabulary; the
rule's stored ``condition.type`` is the recognition handle's name,
not a name+params tuple. The mixed-shape sub-cell of iter 227 is
structurally identifiable in its own right -- it names the rule
family where SOME pairs admit per-pair finite mapping table
abstraction and others do not (in contrast to the universal cell
(iter 228), where NO pair admits per-pair table collapse).
Keeping the conjunction as a separate registry slot lets anti-
unification (CLAUDE.md §8) attach the right gate per rule family --
specifically the gate for rules whose action expression must
consult per-group context within a strict subset of pairs but
admits a per-pair mapping table on the remaining pairs -- without
rediscovering the iter 227 ^ some-pair-function-shape intersection
from the rule's stored action shape.

Why this matters as the mixed-shape sub-cell of iter 227's
territory: the mixed-shape claim is the operational signature of
"partial per-pair table collapsibility" -- the rule admits per-pair
table abstraction on a strict subset of pairs (the within-pair
function-shape pairs) but requires per-group context on the
remaining pairs. The universal cell (iter 228) admits per-pair
table abstraction on NO pair; this matcher's cell admits it on
SOME but not ALL pairs. Naming this sub-cell at a disjoint
recognition handle lets anti-unification know in advance that the
per-pair mapping-table action shape is admissible on a strict
subset of pairs, requiring per-group context on the complement
subset -- without having to scan each pair's per-group records to
discover the mixed-shape composition ad-hoc.

Strict refinement / orthogonality summary (universal-over-groups
semantics with mixed-pair-shape conjunction; per-group |ic| ==
|oc| == 1 AND ic != oc AND |observed_input| > 1 AND |observed_
output| > 1 AND GLOBAL non-function-shape AND SOME pair within-pair
non-function-shape AND SOME pair within-pair function-shape):

  * Iter 228 (``singleton_recolor_nonidentity_unanchored_non_function_
    shaped_within_pair_non_function_shaped_universal``) -- STRICT
    MUTUAL EXCLUSION (the universal-pair vs mixed-pair split on
    iter 227's universal-pair sub-axis).
  * Iter 227 (``singleton_recolor_nonidentity_unanchored_non_function_
    shaped_within_pair_non_function_shaped``) -- STRICT REFINEMENT
    (this matcher additionally requires within-pair function-shape
    on at least one pair, not just within-pair non-function-shape
    on at least one pair).
  * Iter 226 (``singleton_recolor_nonidentity_unanchored_non_function_
    shaped_within_pair_function_shaped``) -- STRICT MUTUAL EXCLUSION
    (the within-pair function-shape split on iter 225's territory).
  * Iter 225 (``singleton_recolor_nonidentity_unanchored_non_function_
    shaped``) -- STRICT REFINEMENT.
  * Iter 224 (``singleton_recolor_nonidentity_unanchored_function_
    shaped``) -- STRICT MUTUAL EXCLUSION (the global function-shape
    split on iter 223's territory).
  * Iter 223 (``singleton_recolor_nonidentity_unanchored``) -- STRICT
    REFINEMENT.
  * Iter 218 (``singleton_recolor_nonidentity_per_group``) -- STRICT
    REFINEMENT.
  * Iter 220 / iter 221 / iter 222 -- STRICT MUTUAL EXCLUSION (each
    demands a cross-group anchor).
  * Iter 219 -- STRICT MUTUAL EXCLUSION.
  * Iter 217 -- STRICT MUTUAL EXCLUSION.
  * Iter 216 -- STRICT MUTUAL EXCLUSION.
  * Iter 215 -- STRICT REFINEMENT.
  * Iter 14 -- STRICT MUTUAL EXCLUSION.
  * Iter 18 -- STRICT MUTUAL EXCLUSION.
  * Iter 8 -- STRICT MUTUAL EXCLUSION.
  * Iter 13 -- STRICT MUTUAL EXCLUSION.
  * Iter 10 -- INDEPENDENT (typically rejects; degenerate sub-cell
    co-fire possible).
  * Iter 195 / 196 / 197 -- STRICTLY IMPLIED at K_in == K_out ==
    K_prod == 1.
  * Iter 198 / 199 (palette-shift constancy) -- INDEPENDENT
    (typically REJECTS -- constant shift forces within-pair
    function-shape on every pair).
  * Iter 201 -- STRICT MUTUAL EXCLUSION.
  * Iter 203 -- STRICTLY IMPLIED.
  * Iter 213 -- STRICTLY IMPLIED.
  * Iter 214 -- STRICTLY IMPLIED.
  * Every cell- / position- / dimension-axis matcher -- orthogonal.

Why this matters for ARBOR's intended ruleset:

  * "Mixed-shape strict-recolour" rule family -- rules where anti-
    unification can collapse the (C_g, K_g) substitution into a
    per-pair finite mapping table on a strict subset of pairs (the
    within-pair function-shape pairs) but requires per-group
    context within the complement subset (the within-pair non-
    function-shape pairs). The mixed-shape cell of iter 227's
    territory: blocks the global mapping table abstraction (iter
    224 / iter 8 sub-cell) and the universal-pair table-blocking
    abstraction (iter 228), but admits per-pair table abstraction
    on the strict subset of within-pair function-shape pairs.
    The natural escalation cell where anti-unification must
    discover a CONDITIONAL action shape -- per-pair table on
    function-shape pairs, per-group context lookup on non-function-
    shape pairs -- not a single uniform action shape across pairs.
  * Closes the iter-228-named candidate (xix): "the strict-
    complement mixed-shape sub-cell of iter 227: a single matcher
    pinning iter 227 territory AND additionally requiring that
    SOME pair has WITHIN-pair function-shape AND SOME pair has
    WITHIN-pair non-function-shape (the mixed-shape-across-pairs
    cell -- the strict-disjoint complement of iter 228 within iter
    227's territory)". With this matcher landed, the universal-
    pair sub-axis on iter 227's territory is closed at two
    disjoint cells (iter 228 / this matcher), exhaustively
    partitioning iter 227's territory on the universal-pair sub-
    axis.

Params:
  (none) -- pure per-pair within-pair function-shape existential
  check (in addition to iter 227's existential within-pair non-
  function-shape claim).

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
    / 200-206 / 213-228 strict-type posture), AND
  - for every group, ``len(set(input_colors)) == 1`` AND
    ``len(set(output_colors)) == 1`` AND
    ``set(input_colors) != set(output_colors)``, AND
  - ``len(observed_input_colors) > 1`` AND
    ``len(observed_output_colors) > 1`` (iter 223 (F, F) territory),
    AND
  - the GLOBAL (C_g, K_g) cross-product across the union of all
    pairs' groups is NON-FUNCTION-shaped (some C_g sees >= 2
    distinct K_g values across the union -- iter 225 territory),
    AND
  - AT LEAST ONE pair has WITHIN-pair NON-function-shape (some
    C_g sees >= 2 distinct K_g values within that pair's own
    groups -- iter 227 existential claim), AND
  - AT LEAST ONE pair has WITHIN-pair FUNCTION-shape (every C_g
    in that pair sees exactly one K_g within that pair's own
    groups -- the strict-complement of iter 228's universal-pair
    claim).

Why fail-closed on empty / no-group / malformed (same posture as
iter 8 / 13 / 14 / 18 / 30-39 / 184-228): a missing or zero-group
pair is upstream extractor breakage or iter 13's no-blob-identity
territory; a mixed-shape strict-recolour claim with zero
observations is meaningless, AND admitting it would collapse this
matcher's territory into iter 13's.

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


@register(
    "singleton_recolor_nonidentity_unanchored_non_function_shaped_"
    "within_pair_non_function_shaped_mixed"
)
def match(patterns: dict, params: dict) -> bool:
    if not isinstance(patterns, dict):
        return False
    pair_analyses = patterns.get("pair_analyses")
    if not isinstance(pair_analyses, list) or not pair_analyses:
        return False

    observed_input_colors: set = set()
    observed_output_colors: set = set()
    # Global C_g -> set of observed K_g values across the union of all
    # pairs' groups. Non-function-shape globally iff some C_g sees
    # multiple distinct K_g values across the union (iter 225
    # precondition).
    global_c_to_k: dict = {}
    # True iff at least one pair has within-pair non-function-shape
    # (iter 227 existential claim).
    any_within_pair_non_function: bool = False
    # True iff at least one pair has within-pair function-shape (the
    # strict-complement of iter 228's universal-pair claim; this
    # matcher's distinguishing claim vs iter 228).
    any_within_pair_function: bool = False
    for analysis in pair_analyses:
        if not isinstance(analysis, dict):
            return False
        groups = analysis.get("groups")
        if not isinstance(groups, list) or not groups:
            return False
        # Per-pair C_g -> K_g map. Within-pair non-function-shape iff
        # some distinct C_g in this pair sees >= 2 distinct K_g values.
        pair_c_to_k: dict = {}
        this_pair_non_function: bool = False
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
            mapped = pair_c_to_k.get(ic_val)
            if mapped is None:
                pair_c_to_k[ic_val] = oc_val
            elif mapped != oc_val:
                # Within-pair non-function-shape on this pair. Mark
                # and continue scanning so the iter 225 preconditions
                # (observed cardinality, per-group / strict-type
                # structural gates) are still checked over every
                # remaining group / pair.
                this_pair_non_function = True
            ks = global_c_to_k.setdefault(ic_val, set())
            ks.add(oc_val)
            observed_input_colors |= ic_set
            observed_output_colors |= oc_set
        if this_pair_non_function:
            any_within_pair_non_function = True
        else:
            # This pair is within-pair function-shape (every C_g in
            # this pair saw exactly one K_g across the pair's groups).
            any_within_pair_function = True
    if len(observed_input_colors) <= 1:
        return False
    if len(observed_output_colors) <= 1:
        return False
    # Mixed-shape conjunction: both at-least-one-pair non-function-
    # shape (iter 227 existential claim) AND at-least-one-pair
    # function-shape (strict-complement of iter 228's universal claim).
    if not any_within_pair_non_function:
        return False
    if not any_within_pair_function:
        return False
    # Global non-function-shape: some C_g sees multiple distinct K_g's
    # across the union of all pairs' groups (iter 225 precondition).
    # Strictly implied by any_within_pair_non_function (within-pair
    # non-function-shape on any pair implies global non-function-shape
    # on the union), but checked explicitly for parity with the iter
    # 225 / 226 / 227 / 228 contract and to keep this matcher self-
    # contained.
    for ks in global_c_to_k.values():
        if len(ks) > 1:
            return True
    return False
