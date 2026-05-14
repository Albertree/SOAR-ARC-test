"""
input_colors_proper_subset_of_output_colors_per_group -- match tasks
where EVERY change group of EVERY example pair satisfies
``set(group["input_colors"]) < set(group["output_colors"])``: every
group's input side uses a STRICT proper subset of its own output
side -- input set is contained in output set AND strictly smaller
(at least one fresh output colour is added per group).

Recognition vocabulary axis: per-group strict-expansion cell of the
per-group palette-relation sub-axis closed by iters 200 / 201 / 202 /
203. Iter 202 (``input_colors_subset_of_output_colors_per_group``)
admits the equality cell (input set == output set per group), making
iter 202's territory the DISJUNCTION of per-group equality (iter 201)
AND per-group strict expansion (this matcher). The two are mutually
exclusive on non-empty per-group palettes; together they partition
iter 202's territory.

This matcher carves out the strict-expansion cell -- the cell where
every group adds at least one fresh colour to its output and drops
none of its input colours. Anti-unification (CLAUDE.md section 8)
would attach a per-blob EXPANSION generalisation variable to this
matcher's fired-gate (e.g. a rule that overlays a fresh colour onto
every changed blob, preserving the existing blob colours), distinct
from the per-blob permutation rule family attached to iter 201's
fired-gate.

Symmetric dual of iter 204 (``output_colors_proper_subset_of_input_
colors_per_group``): iter 204 is the strict-refinement of iter 200
EXCLUDING the iter-201 equality cell (per-group strict-erasure);
this matcher is the strict-refinement of iter 202 EXCLUDING the
iter-201 equality cell (per-group strict-expansion). Strict mutual
exclusion between iter 204 and this matcher: per-group output ⊂
input AND per-group input ⊂ output is impossible on non-empty sets
(both would require strict cardinality inequality in opposite
directions). The two matchers together with iter 201 cover iter 200
∪ iter 202's territory disjunctively.

Strict refinement of iter 202 (``input_colors_subset_of_output_
colors_per_group``): per-group input proper subset of output is the
strict refinement of per-group input subset of output EXCLUDING the
equality cell. Strict implication: this matcher fires ⇒ iter 202
fires (proper subset implies subset universally). The converse does
NOT hold: per-group input_colors=[1] / output_colors=[1] fires iter
202 (equality is a subset) but rejects this matcher (input set NOT
strictly smaller than output set).

Strict mutual exclusion with iter 201 (``output_colors_equals_input_
colors_per_group``) on every input pattern: per-group equality
forbids strict-proper-subset by construction (set equality on non-
empty sets is incompatible with one set being strictly smaller).
The strict-proper-subset cell and the equality cell are the two
disjoint sub-cells of iter 202's territory; their union recovers
iter 202's fired-gate.

Decoupling with iter 200 (``output_colors_subset_of_input_colors_
per_group``): iter 200 requires output ⊆ input per group; this
matcher requires input ⊂ output per group. The intersection requires
output ⊆ input AND input ⊂ output, which is impossible on non-empty
sets (input ⊂ output means at least one output colour is absent from
input; output ⊆ input means every output colour is present in
input -- contradiction). The two matchers are strictly mutually
exclusive on the cell-count-non-empty domain.

Decoupling with iter 203 (``output_colors_disjoint_from_input_colors_
per_group``): iter 203 requires input ∩ output == ∅ per group; this
matcher requires input ⊂ output per group, which by definition
requires input ⊆ output. With non-empty per-group inputs, input ⊂
output AND input ∩ output == ∅ are incompatible (a non-empty subset
of a non-empty set has non-empty intersection with that set). The
two matchers are strictly mutually exclusive on the cell-count-non-
empty domain.

Why a distinct matcher rather than parameterising iter 202 with a
``strict: True`` flag (mirroring the iter-185 / iter-184 separation
rationale and iter 204's symmetric-dual rationale): the matcher
contract (docs/RULE_FORMAT.md §4) is name-keyed recognition
vocabulary; the rule's stored ``condition.type`` is the recognition
handle's name, not a name+params tuple. The strict-expansion
precondition gates a DIFFERENT rule family than the equality-tolerant
subset precondition (expansion rules vs permutation-or-expansion
rules); keeping them in separate registry slots lets anti-unification
attach the right gate per rule family.

Strict refinement / orthogonality summary (universal-over-groups-and-
pairs semantics):

  * Iter 13 (``identity_transformation``) -- every pair has zero
    change groups. This matcher REJECTS the no-group case (fail-
    closed clause below) to keep its territory disjoint from iter 13
    by construction. Mirrors iter 32 / 35 / 37 / 39 / 193 / 195 /
    196 / 197 / 198 / 199 / 200 / 201 / 202 / 203 / 204 empty-group
    rejection.
  * Iter 14 (``input_color_uniform``) -- pins every group's
    ``input_colors`` to a single colour. With single-colour input
    groups, a strict proper subset on the INPUT side of a singleton
    is the empty set; this matcher's cell-count requirement rejects
    empty per-group inputs, so the two CANNOT co-fire when iter 14's
    territory is a singleton. Iter 14 fires ⇒ this matcher REJECTS
    (strict mutual exclusion on singleton-input territory; SYMMETRIC
    DUAL of iter 204's singleton-input rejection).
  * Iter 18 (``output_color_uniform``) -- pins every group's
    ``output_colors`` to a single colour AND that colour identical
    across all groups. With single-colour output groups, a strict
    proper subset on the OUTPUT side of a singleton is the empty
    set; this matcher's cell-count requirement rejects empty per-
    group inputs (input ⊂ singleton implies input == ∅). Iter 18
    fires ⇒ this matcher REJECTS on singleton-output territory.
  * Iter 184 (``output_palette_subset_of_input``) -- whole-grid
    output palette subset of whole-grid input palette per pair.
    THIS MATCHER REJECTS iter-184 territory on its main witness
    (per-group input ⊂ output implies per-group output set covers
    per-group input AND adds a fresh colour, so the whole-grid
    output palette has at least one fresh colour absent from the
    whole-grid input palette, contradicting iter 184). The whole-
    grid output may still be a subset via OTHER groups, but on the
    primary cell of this matcher firing (single-group pair), iter
    184 rejects.
  * Iter 185 (``output_palette_equals_input``) -- whole-grid strict
    equality. INDEPENDENT in general; per-group strict-expansion
    introduces at least one fresh colour to each group's output,
    but the whole-grid output palette may still equal the whole-
    grid input palette via unchanged background pixels or via
    other groups' outputs. CAN co-fire on patterns where the per-
    group expanded colours are already in the whole-grid input
    palette.
  * Iter 186 (``output_palette_disjoint_from_input``) -- whole-grid
    disjoint. THIS MATCHER REJECTS iter-186 territory by
    construction (per-group input ⊂ per-group output means per-group
    input ⊆ per-group output, so per-group input AND per-group output
    share at least one colour; whole-grid input and whole-grid output
    therefore share that colour, contradicting iter 186).
  * Iter 187 (``input_palette_subset_of_output``) -- whole-grid
    input palette subset of whole-grid output palette per pair.
    INDEPENDENT in general; per-group strict-expansion is the per-
    blob projection of iter 187, with strict-refinement on the
    equality cell. CAN co-fire when per-group strict-expansion
    aligns with whole-grid subset.
  * Iter 200 (``output_colors_subset_of_input_colors_per_group``) --
    per-group subset. STRICTLY MUTUALLY EXCLUSIVE with this matcher
    on non-empty per-group palettes (proven above).
  * Iter 201 (``output_colors_equals_input_colors_per_group``) --
    per-group equality. STRICTLY MUTUALLY EXCLUSIVE with this matcher
    on every input pattern (set equality forbids strict proper subset
    by construction).
  * Iter 202 (``input_colors_subset_of_output_colors_per_group``) --
    per-group dual subset. THIS MATCHER STRICTLY IMPLIES ITER 202
    (proper subset implies subset universally). The converse does
    NOT hold (per-group equality fires iter 202 but rejects this
    matcher). The strict-expansion cell (this matcher) and the
    equality cell (iter 201) jointly partition iter 202's territory.
  * Iter 203 (``output_colors_disjoint_from_input_colors_per_group``)
    -- per-group disjoint. STRICTLY MUTUALLY EXCLUSIVE with this
    matcher on non-empty per-group palettes (proven above).
  * Iter 204 (``output_colors_proper_subset_of_input_colors_per_
    group``) -- per-group strict erasure (SYMMETRIC DUAL of this
    matcher). STRICTLY MUTUALLY EXCLUSIVE on non-empty per-group
    palettes: output ⊂ input AND input ⊂ output is impossible.
  * Iter 195 / 196 / 197 -- per-group cardinality matchers on
    input / output / product. NOT in a refinement relation in
    general. Iter 196 (per-group output cardinality) plus
    cardinality-strict-greater-than-input cardinality is a
    near-precondition for this matcher firing; the matchers are
    INDEPENDENT in the universal-over-pairs scope (across-pair
    constancy claims in iter 195 / 196 / 197 are NOT implied by
    per-group strict-subset).
  * Iter 194 (whole-grid colour translation cross-pair) -- a
    translation by k != 0 has whole-grid output palette disjoint
    from input palette; THIS MATCHER REJECTS any k != 0 translation
    by construction (per-group input ⊂ output requires non-empty
    intersection). Co-fire only on the k == 0 (identity) cell, but
    iter 201 also fires on k == 0 -- so this matcher rejects k == 0
    too via mutual exclusion with iter 201. No co-fire territory.
  * Iter 198 / 199 (per-group colour translation within-pair /
    globally) -- with strict same-cardinality per-group sorted-shift
    and k != 0, the per-group input set is disjoint from the per-
    group output set; this matcher rejects k != 0 translations. With
    k == 0, iter 201 (per-group equality) fires; this matcher
    rejects k == 0 via mutual exclusion with iter 201. No co-fire
    territory.
  * Iter 35 / 36 (``change_input_colors_constant_across_pairs`` /
    ``change_output_colors_constant_across_pairs``) -- per-pair
    input / output colour SET bit-identity. Independent.
  * Iter 8 (``consistent_color_mapping``) -- per-pair (C -> K) is a
    function on changed cells. INDEPENDENT in general; this matcher
    constrains where C lives (in the group's output set) AND that at
    least one fresh output colour is unmapped-from-the-input per
    group, iter 8 constrains how C maps. CAN co-fire when every
    (C, K) the function maps satisfies C in output set per group AND
    at least one output colour per group is fresh.
  * Every cell- / position- / dimension-axis matcher (iters 1 / 17 /
    19 / 20 / 22 / 23 / 24 / 26 / 28 / 32 / 33 / 38 / 39 / 40 / 41 /
    42 / 182 / 183) -- orthogonal to per-group palette content.

Why this matters for ARBOR's intended ruleset:

  * "Per-blob strict-expansion" rule family -- rules whose action
    ADDS at least one fresh colour to every changed blob's output
    palette and drops no input colour (e.g. a rule that overlays a
    fresh annotation colour onto every changed region, leaving the
    existing region colours intact). Iter 202's whole-territory
    version cannot distinguish "every blob is strictly larger in
    palette" from "every blob is identical in palette"; this
    matcher names the strictly stronger strict-expansion cell that
    is the precondition for per-blob expansion rule families.
  * Iter 201 names the per-blob PERMUTATION rule family precondition
    (equality territory); iter 204 names the per-blob ERASURE rule
    family precondition (proper-subset territory on the output ⊂
    input side); this matcher names the per-blob EXPANSION rule
    family precondition (proper-subset territory on the input ⊂
    output side). The three matchers together cover iter 200 ∪
    iter 202's territory disjunctively, and each names a distinct
    rule family the gate can attach to.
  * Closes the iter-204-named first-listed next-gap candidate on the
    strict-refinement axis of the per-group palette-relation sub-
    axis. The pending sibling matcher on the same refinement axis
    (named by iter 204's next-gap) is
    ``output_colors_partial_overlap_with_input_colors_per_group``
    (the partial-overlap residual cell, naming the per-blob
    recolour-with-shared-anchor cell).

Params:
  (none) -- pure per-group strict-proper-subset check, universal
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
    strict int in ``range(10)`` (bool rejected per iter-13 / 14 /
    ... / 201 / 202 / 203 / 204 strict-type posture), AND
  - for every group, ``set(input_colors) < set(output_colors)``
    (i.e. ``set(input_colors) <= set(output_colors)`` AND
    ``set(input_colors) != set(output_colors)``).

Why fail-closed on empty / no-group / malformed (same posture as
iters 14 / 30 / 32 / 33 / 34 / 35 / 36 / 37 / 38 / 39 / 184-204): a
missing or zero-group pair is upstream extractor breakage or
identity-territory; a strict-subset claim with zero observations
would double-cover iter 13.

Why ``input_colors`` and ``output_colors`` both required non-empty
lists per group (``len >= 1``): a connected change group has at
least one cell; each cell has both an input colour and an output
colour; the per-group ``input_colors`` / ``output_colors`` fields
are the sorted sets of those colours, which are non-empty for any
non-empty group. A zero-length colour list is an extractor contract
violation, not a valid empty-set strict-subset case.

Why strict per-colour validation (bool rejected, range checked):
``input_colors`` / ``output_colors`` carry small ints in [0, 9]; the
matcher performs the same strict-type gating as iter 14 / 18 / 19 /
34 / 35 / 36 / 37 / 38 / 184-204 to keep contract violations from
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


@register("input_colors_proper_subset_of_output_colors_per_group")
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
            in_set = set(input_colors)
            out_set = set(output_colors)
            if not (in_set < out_set):
                return False
    return True
