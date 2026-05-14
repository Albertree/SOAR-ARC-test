"""
singleton_recolor_nonidentity_unanchored_non_function_shaped_within_
pair_non_function_shaped_universal -- match tasks where every group
of every example pair has BOTH ``len(set(input_colors)) == 1`` AND
``len(set(output_colors)) == 1`` AND ``set(input_colors) != set(
output_colors)`` AND ``len(observed_input_colors) > 1`` (NOT cross-
group identity on the INPUT side) AND ``len(observed_output_colors)
> 1`` (NOT cross-group identity on the OUTPUT side) AND the GLOBAL
(C_g, K_g) cross-product is NON-function-shaped (some distinct per-
group C_g maps to MULTIPLE distinct K_g values across the union of
all groups across all pairs -- iter 225 territory) AND EVERY pair
has WITHIN-pair NON-function-shape (some C_g sees >= 2 distinct K_g
values within EACH pair's OWN groups -- the strict refinement of
iter 227's existential ``at least one pair`` claim at the universal
``every pair`` sub-cell).

The strict refinement of iter 227 (``singleton_recolor_nonidentity_
unanchored_non_function_shaped_within_pair_non_function_shaped``) at
the UNIVERSAL-quantifier sub-cell within iter 227's territory. The
"every pair has within-pair non-function-shape" sub-cell named by
iter 227's "Next gap" candidate (xviii).

Recognition vocabulary axis: the universal-pair sub-cell of iter
227's existential within-pair non-function-shape territory. Iter 227
names "AT LEAST ONE pair has within-pair non-function-shape" (the
strict-disjoint complement of iter 226 within iter 225's territory);
within iter 227's territory the universal-pair sub-axis splits into:

  * UNIVERSAL: every pair has within-pair non-function-shape (some
    C_g sees >= 2 distinct K_g values within EACH pair's own
    groups). THIS matcher. The most-restrictive sub-cell of iter
    227 where no pair admits even the per-pair finite mapping table
    abstraction; every pair requires per-group context to
    disambiguate K_g.
  * EXISTENTIAL-BUT-NOT-UNIVERSAL: at least one pair has within-
    pair non-function-shape AND at least one pair has within-pair
    function-shape (the mixed-shape-across-pairs cell). Companion
    candidate (xix); iter 227 fires AND this matcher rejects on
    that cell.

The two cells together partition iter 227's territory exhaustively
along the universal-pair within-pair non-function-shape sub-axis.
This matcher names the universal cell; companion candidate (xix)
names the existential-but-not-universal cell.

This matcher names the precondition for the rule family "whole-task
strict-recolour where every pair has within-pair non-function-shape,
blocking the per-pair finite mapping table abstraction in every
pair" -- rules that require per-group context within each pair to
disambiguate K_g, with NO pair admitting even the per-pair table
abstraction. The maximally-restrictive sub-cell of iter 227's
territory: blocks the global mapping table abstraction (iter 224 /
iter 8 sub-cell), the per-pair mapping table abstraction (iter 226
sub-cell), AND the mixed-shape sub-cell (companion (xix)).

Strict relations to iter 227 (the immediate parent):

  * Iter 227 (``singleton_recolor_nonidentity_unanchored_non_function_
    shaped_within_pair_non_function_shaped``): STRICT REFINEMENT.
    This matcher fires => iter 227 fires (universal-pair within-
    pair non-function-shape strictly implies at-least-one-pair
    within-pair non-function-shape). The converse fails on the
    mixed-shape sub-cell (some pair within-pair function-shape AND
    some pair within-pair non-function-shape -- iter 227 fires,
    this matcher rejects).

Strict relations to iter 226 (the strict-disjoint sibling on iter
225's within-pair function-shape sub-axis):

  * Iter 226 (``singleton_recolor_nonidentity_unanchored_non_function_
    shaped_within_pair_function_shaped``): STRICT MUTUAL EXCLUSION.
    Iter 226 demands every pair within-pair FUNCTION-shape; this
    matcher demands every pair within-pair NON-function-shape. By
    definition disjoint via iter 227.

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
degenerate sub-cells (e.g. a single-pair fixture whose within-pair
non-function-shape collisions happen to land on a contiguous range,
though iter 10 also requires per-pair-distinct outputs which
typically conflict with within-pair non-function-shape).

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
matcher's territory has within-pair non-function-shape on every
pair: some C_g sees multiple K_g's within each pair. If a constant
per-pair shift held, every C_g would map to exactly one K_g within
the pair (a function determined by the shift), so iter 198 would
force within-pair function-shape, contradicting this matcher's
territory. Hence iter 198 / 199 REJECT on this matcher's territory.

Strict relation to iter 201 (``output_colors_equals_input_colors_
per_group``): STRICT MUTUAL EXCLUSION (per-group ic != oc forces
per-group set(ic) != set(oc)).

Strict relation to iter 203 (``output_colors_disjoint_from_input_
colors_per_group``): STRICTLY IMPLIED (singleton row with ic != oc
forces disjoint sets per group).

Why a distinct matcher rather than parameterising iter 227 with a
``universal_quantifier: True`` flag: the matcher contract
(docs/RULE_FORMAT.md §4) is name-keyed recognition vocabulary; the
rule's stored ``condition.type`` is the recognition handle's name,
not a name+params tuple. The universal-pair sub-cell of iter 227 is
structurally identifiable in its own right -- it names the rule
family where EVERY pair blocks the per-pair finite mapping table
abstraction (in contrast to the mixed-shape cell, where SOME pairs
admit per-pair table collapse and others do not). Keeping the
conjunction as a separate registry slot lets anti-unification
(CLAUDE.md §8) attach the right gate per rule family -- specifically
the gate for rules whose action expression must consult per-group
context within EVERY pair to disambiguate K_g -- without
rediscovering the iter 227 ^ universal-quantifier intersection from
the rule's stored action shape.

Why this matters as the universal-pair sub-cell of iter 227's
territory: the universal-pair within-pair non-function-shape claim
is the operational barrier that blocks per-pair finite mapping
table abstraction on EVERY pair, not merely on some pairs. The
mixed-shape cell (companion (xix)) admits per-pair table abstraction
on a strict subset of pairs (the function-shape pairs); this
matcher's cell admits per-pair table abstraction on NO pair.
Naming this sub-cell at a disjoint recognition handle lets anti-
unification know in advance that the per-pair mapping-table action
shape is NOT admissible on any pair, requiring per-group context on
every pair -- without having to scan each pair's per-group records
to discover the universal within-pair non-function-shape ad-hoc.

Strict refinement / orthogonality summary (universal-over-groups-
and-pairs semantics; per-group |ic| == |oc| == 1 AND ic != oc AND
|observed_input| > 1 AND |observed_output| > 1 AND GLOBAL non-
function-shape AND per-pair WITHIN-pair non-function-shape on
EVERY pair):

  * Iter 227 (``singleton_recolor_nonidentity_unanchored_non_function_
    shaped_within_pair_non_function_shaped``) -- STRICT REFINEMENT
    (this matcher additionally requires within-pair non-function-
    shape on EVERY pair, not just at least one).
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
    function-shape).
  * Iter 201 -- STRICT MUTUAL EXCLUSION.
  * Iter 203 -- STRICTLY IMPLIED.
  * Iter 213 -- STRICTLY IMPLIED.
  * Iter 214 -- STRICTLY IMPLIED.
  * Every cell- / position- / dimension-axis matcher -- orthogonal.

Why this matters for ARBOR's intended ruleset:

  * "Universal within-pair non-function-shape strict-recolour" rule
    family -- rules whose action must consult per-group context
    within EVERY pair (position, shape, group index, neighbouring
    colours, ...) to disambiguate the K_g target, because the bare
    (C_g) input does not uniquely determine K_g even within a
    single pair on any pair. The maximally-restrictive sub-cell of
    iter 227's territory: blocks the global mapping table
    abstraction (iter 224 / iter 8 sub-cell), the per-pair mapping
    table abstraction (iter 226 sub-cell), AND the mixed-shape
    sub-cell (companion (xix)). The natural escalation cell where
    anti-unification must reach for per-group features beyond C_g
    on every pair (the per-group features available in the patterns
    dict: top_row, top_col, cell_count, group index within pair,
    ...).
  * Closes the iter-227-named candidate (xviii): "a single matcher
    pinning iter 227 territory AND additionally requiring that
    EVERY pair has WITHIN-pair non-function-shape (some C_g in
    EACH pair sees >= 2 distinct K_g values within that pair's own
    groups)". With this matcher landed, iter 227's universal-pair
    sub-axis is named at a disjoint recognition handle; the
    companion mixed-shape cell (candidate (xix)) becomes the
    natural strict-complement sibling for the next iter.

Params:
  (none) -- pure per-pair within-pair non-function-shape universal
  check on iter 227's territory, universal over groups and pairs.

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
    / 200-206 / 213-227 strict-type posture), AND
  - for every group, ``len(set(input_colors)) == 1`` AND
    ``len(set(output_colors)) == 1`` AND
    ``set(input_colors) != set(output_colors)``, AND
  - ``len(observed_input_colors) > 1`` AND
    ``len(observed_output_colors) > 1`` (iter 223 (F, F) territory),
    AND
  - the GLOBAL (C_g, K_g) cross-product across the union of all
    pairs' groups is NON-FUNCTION-shaped (some C_g sees >= 2
    distinct K_g values across the union -- iter 225 territory --
    strictly implied by the per-pair universal claim below; checked
    explicitly for parity with iter 225 / 226 / 227 contracts),
    AND
  - EVERY pair has WITHIN-pair NON-function-shape (some C_g in EACH
    pair sees >= 2 distinct K_g values within the pair's own groups
    -- the strict refinement of iter 227's existential claim at
    the universal-quantifier sub-cell).

Why fail-closed on empty / no-group / malformed (same posture as
iter 8 / 13 / 14 / 18 / 30-39 / 184-227): a missing or zero-group
pair is upstream extractor breakage or iter 13's no-blob-identity
territory; a universal-within-pair-non-function-shaped strict-
recolour claim with zero observations is meaningless, AND admitting
it would collapse this matcher's territory into iter 13's.

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
    "within_pair_non_function_shaped_universal"
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
    # precondition; strictly implied by the per-pair universal claim
    # below but checked explicitly).
    global_c_to_k: dict = {}
    for analysis in pair_analyses:
        if not isinstance(analysis, dict):
            return False
        groups = analysis.get("groups")
        if not isinstance(groups, list) or not groups:
            return False
        # Per-pair C_g -> K_g map. Within-pair non-function-shape iff
        # some distinct C_g in this pair sees >= 2 distinct K_g values.
        pair_c_to_k: dict = {}
        # True iff THIS pair has within-pair non-function-shape. The
        # universal claim demands every pair satisfy this.
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
                # Within-pair non-function-shape on THIS pair. Mark
                # and continue scanning so the iter 225 preconditions
                # (observed cardinality, per-group / strict-type
                # structural gates) are still checked over every
                # remaining group / pair.
                this_pair_non_function = True
            ks = global_c_to_k.setdefault(ic_val, set())
            ks.add(oc_val)
            observed_input_colors |= ic_set
            observed_output_colors |= oc_set
        # The universal claim: EVERY pair must have within-pair non-
        # function-shape. A pair that is within-pair function-shape
        # disqualifies the whole task on this matcher's territory
        # (contrast iter 227, which fires existentially on at-least-
        # one such pair).
        if not this_pair_non_function:
            return False
    if len(observed_input_colors) <= 1:
        return False
    if len(observed_output_colors) <= 1:
        return False
    # Global non-function-shape: some C_g sees multiple distinct K_g's
    # across the union of all pairs' groups (iter 225 precondition).
    # Strictly implied by universal within-pair non-function-shape
    # (within-pair non-function-shape on any pair already forces
    # global non-function-shape on the union); checked explicitly for
    # parity with the iter 225 / 226 / 227 contract and to keep this
    # matcher self-contained.
    for ks in global_c_to_k.values():
        if len(ks) > 1:
            return True
    return False
