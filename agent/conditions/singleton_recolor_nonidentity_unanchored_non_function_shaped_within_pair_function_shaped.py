"""
singleton_recolor_nonidentity_unanchored_non_function_shaped_within_
pair_function_shaped -- match tasks where every group of every example
pair has BOTH ``len(set(input_colors)) == 1`` AND ``len(set(output_
colors)) == 1`` AND ``set(input_colors) != set(output_colors)`` AND
``len(observed_input_colors) > 1`` (NOT cross-group identity on the
INPUT side) AND ``len(observed_output_colors) > 1`` (NOT cross-group
identity on the OUTPUT side) AND the GLOBAL (C_g, K_g) cross-product
is NON-function-shaped (some distinct per-group C_g maps to MULTIPLE
distinct K_g values across the union of all groups across all pairs)
AND for every individual pair, the PER-PAIR (C_g, K_g) cross-product
is FUNCTION-shaped (within that pair alone, every distinct C_g maps to
exactly one K_g across the pair's own groups).

The strict refinement of iter 225 (``singleton_recolor_nonidentity_
unanchored_non_function_shaped``) at the within-pair function-shape
sub-cell. The "function-shape WITHIN each pair, but inconsistent
ACROSS pairs" sub-cell named by iter 225's "Next gap" candidate
(xvi).

Recognition vocabulary axis: the per-pair function-shape sub-cell of
iter 225's non-function-shape territory. Iter 225 names the (F, F)
"neither anchored" non-function-shape territory globally; within that
territory the per-pair (C_g, K_g) cross-product can be either:

  * FUNCTION-shaped within each pair (every C_g sees exactly one K_g
    within each pair's own groups). The global non-function-shape
    arises ONLY across pairs (some C_g sees K_g_1 in pair 1 and
    K_g_2 != K_g_1 in pair 2). THIS matcher.
  * NON-FUNCTION-shaped within at least one pair (some C_g sees
    multiple K_g's within a single pair's own groups). The
    strict-complement sub-cell -- companion candidate (xvii).

The two cells together partition iter 225's territory exhaustively
along the within-pair function-shape sub-axis. This matcher names
the within-pair function-shape cell; (xvii) names the within-pair
non-function-shape cell.

This matcher names the precondition for the rule family "whole-task
strict-recolour function-shaped within each pair but mapping-table-
varying across pairs" -- rules where each pair admits a per-pair
finite mapping table on the (C_g, K_g) substitution, but the task
as a whole does not have a single global mapping table because the
K_g target varies across pairs. The simplest sub-cell of iter 225's
territory that admits PER-PAIR anti-unification of the (C_g, K_g)
substitution (each pair's mapping table is a function), but blocks
GLOBAL anti-unification (no single global function table covers
every pair).

Strict relations to iter 225 (the immediate parent):

  * Iter 225 (``singleton_recolor_nonidentity_unanchored_non_function_
    shaped``): STRICT REFINEMENT. This matcher fires => iter 225
    fires (the GLOBAL non-function-shape claim is a precondition).
    The converse fails on any iter-225 task where some pair has
    WITHIN-pair non-function-shape (companion (xvii) territory).

Strict relations to iter 224 (the function-shape sibling on iter 223's
function-shape sub-axis):

  * Iter 224 (``singleton_recolor_nonidentity_unanchored_function_
    shaped``): STRICT MUTUAL EXCLUSION (via iter 225's strict
    mutual exclusion with iter 224 on iter 223's territory).

Strict relations to iter 223 (the grandparent):

  * Iter 223 (``singleton_recolor_nonidentity_unanchored``): STRICT
    REFINEMENT (via iter 225).

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
degenerate sub-cells.

Strict relation to iter 13 (``identity_transformation``): STRICT
MUTUAL EXCLUSION (iter 13 demands zero changes per pair).

Strict relations to iter 195 / 196 / 197 (per-group cardinality
matchers): STRICTLY IMPLIED at K_in == K_out == K_prod == 1 (same
as iter 225 -- per-group |ic| == |oc| == 1 forces K=1 on every
axis).

Strict relations to iter 198 / iter 199 (palette-shift constancy):
INDEPENDENT in general. iter 198 / 199 demand a single constant
shift k = K_g - C_g across all groups (and across all pairs for
iter 199). This matcher's territory can co-fire with iter 198 if
the within-pair shift is constant (e.g., pair 1: 3 -> 0, 5 -> 2
gives constant shift -3 within pair 1) AND iter 199 if that same
constant shift extends across all pairs -- but then the C_g -> K_g
mapping is determined by the shift alone, so the global mapping is
a function, contradicting iter 225 / this matcher's territory.
Hence iter 198 / 199 typically REJECT on this matcher's territory.

Strict relation to iter 201 (``output_colors_equals_input_colors_
per_group``): STRICT MUTUAL EXCLUSION (per-group ic != oc forces
per-group set(ic) != set(oc)).

Strict relation to iter 203 (``output_colors_disjoint_from_input_
colors_per_group``): STRICTLY IMPLIED (singleton row with ic != oc
forces disjoint sets per group).

Why a distinct matcher rather than parameterising iter 225 with a
``per_pair_function_shaped: True`` flag: the matcher contract
(docs/RULE_FORMAT.md §4) is name-keyed recognition vocabulary; the
rule's stored ``condition.type`` is the recognition handle's name,
not a name+params tuple. The within-pair function-shape sub-cell of
iter 225 is structurally identifiable in its own right -- it names
a rule family (per-pair mapping tables that vary across pairs) that
admits PER-PAIR anti-unification but blocks GLOBAL anti-unification,
distinguishing it from iter 225's companion (xvii) territory which
admits NEITHER. Keeping the conjunction as a separate registry slot
lets anti-unification (CLAUDE.md §8) attach the right gate per
rule family -- specifically the gate for rules whose action expression
emits a per-pair mapping table -- without rediscovering the iter 225
^ within-pair-function-shape intersection from the rule's stored
action shape.

Why this matters as the within-pair function-shape sub-cell of iter
225's territory: the within-pair function-shape claim is the
operational precondition that anti-unification can collapse the
per-pair (C_g, K_g) substitution into a per-pair finite mapping
table. The companion (xvii) sub-cell (within-pair non-function-shape)
blocks even the per-pair table collapse -- requiring per-group
context within each pair. Naming this sub-cell at a disjoint
recognition handle lets anti-unification know in advance that the
per-pair mapping-table action shape is admissible, without having
to scan each pair's per-group records to discover the within-pair
function-shape ad-hoc.

Strict refinement / orthogonality summary (universal-over-groups-
and-pairs semantics; per-group |ic| == |oc| == 1 AND ic != oc AND
|observed_input| > 1 AND |observed_output| > 1 AND GLOBAL non-
function-shape AND per-pair WITHIN-pair function-shape):

  * Iter 225 (``singleton_recolor_nonidentity_unanchored_non_function_
    shaped``) -- STRICT REFINEMENT (this matcher additionally
    requires per-pair within-pair function-shape).
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
    (typically REJECTS).
  * Iter 201 -- STRICT MUTUAL EXCLUSION.
  * Iter 203 -- STRICTLY IMPLIED.
  * Iter 213 -- STRICTLY IMPLIED.
  * Iter 214 -- STRICTLY IMPLIED.
  * Every cell- / position- / dimension-axis matcher -- orthogonal.

Why this matters for ARBOR's intended ruleset:

  * "Function-shaped-per-pair / non-function-shaped-globally strict-
    recolour" rule family -- rules whose action is "for each pair,
    apply the per-pair function table C -> K_pair derived from the
    pair's own observed singletons; the global task has no single
    mapping table because the per-pair tables differ". The simplest
    sub-cell of iter 225's territory where anti-unification can
    still collapse the per-pair (C_g, K_g) substitution into a
    finite mapping table -- one table per pair, abstracted into a
    family of tables indexed by the pair. The companion (xvii)
    territory (within-pair non-function-shape) blocks even the
    per-pair table collapse, requiring per-group context within
    each pair to disambiguate K_g.
  * Closes the iter-225-named candidate (xvi): "the per-pair
    function-shape sub-axis on iter 225's non-function-shape
    territory: a single matcher pinning iter 225 territory AND
    additionally requiring that EVERY pair (taken alone) is
    function-shaped within its own groups, with non-function-shape
    arising only across the union of pairs (the 'function-shape
    WITHIN each pair, but inconsistent ACROSS pairs' sub-cell)".

Params:
  (none) -- pure per-pair function-shape check on iter 225's
  territory, universal over groups and pairs.

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
    / 200-206 / 213-225 strict-type posture), AND
  - for every group, ``len(set(input_colors)) == 1`` AND
    ``len(set(output_colors)) == 1`` AND
    ``set(input_colors) != set(output_colors)``, AND
  - ``len(observed_input_colors) > 1`` AND
    ``len(observed_output_colors) > 1`` (iter 223 (F, F) territory),
    AND
  - within EACH pair taken alone, the (C_g, K_g) cross-product
    restricted to that pair's groups is FUNCTION-shaped (every
    distinct C_g sees exactly one K_g within that pair), AND
  - the GLOBAL (C_g, K_g) cross-product across the union of all
    pairs' groups is NON-FUNCTION-shaped (some C_g sees >= 2
    distinct K_g values across the union -- iter 225 territory).

Why fail-closed on empty / no-group / malformed (same posture as
iter 8 / 13 / 14 / 18 / 30-39 / 184-225): a missing or zero-group
pair is upstream extractor breakage or iter 13's no-blob-identity
territory; a within-pair-function-shaped / across-pair-inconsistent
strict-recolour claim with zero observations is meaningless, AND
admitting it would collapse this matcher's territory into iter
13's.

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
    "within_pair_function_shaped"
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
    # multiple distinct K_g values across the union.
    global_c_to_k: dict = {}
    for analysis in pair_analyses:
        if not isinstance(analysis, dict):
            return False
        groups = analysis.get("groups")
        if not isinstance(groups, list) or not groups:
            return False
        # Per-pair C_g -> K_g map. Within-pair function-shape iff every
        # distinct C_g in this pair sees exactly one K_g.
        pair_c_to_k: dict = {}
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
                # Within-pair non-function-shape: companion (xvii)
                # territory; this matcher rejects.
                return False
            ks = global_c_to_k.setdefault(ic_val, set())
            ks.add(oc_val)
            observed_input_colors |= ic_set
            observed_output_colors |= oc_set
    if len(observed_input_colors) <= 1:
        return False
    if len(observed_output_colors) <= 1:
        return False
    # Global non-function-shape: some C_g sees multiple distinct K_g's
    # across the union of all pairs' groups.
    for ks in global_c_to_k.values():
        if len(ks) > 1:
            return True
    return False
