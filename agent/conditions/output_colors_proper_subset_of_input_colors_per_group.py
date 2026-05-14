"""
output_colors_proper_subset_of_input_colors_per_group -- match tasks
where EVERY change group of EVERY example pair satisfies
``set(group["output_colors"]) < set(group["input_colors"])``: every
group's output side uses a STRICT proper subset of its own input
side -- output set is contained in input set AND strictly smaller
(at least one input colour is dropped on the output side per group).

Recognition vocabulary axis: per-group strict-erasure cell of the
per-group palette-relation sub-axis closed by iters 200 / 201 / 202 /
203. Iter 200 (``output_colors_subset_of_input_colors_per_group``)
admits the equality cell (output set == input set per group), making
iter 200's territory the DISJUNCTION of per-group equality (iter 201)
AND per-group strict erasure (this matcher). The two are mutually
exclusive on non-empty per-group palettes; together they partition
iter 200's territory.

This matcher carves out the strict-erasure cell -- the cell where
every group drops at least one of its input colours and introduces no
fresh ones. Anti-unification (CLAUDE.md section 8) would attach a
per-blob ERASURE generalisation variable to this matcher's fired-gate
(e.g. a rule that erases a specific colour from every changed blob,
leaving the remaining blob colours untouched), distinct from the
per-blob permutation rule family attached to iter 201's fired-gate.

Strict refinement of iter 200 (``output_colors_subset_of_input_
colors_per_group``): per-group proper subset is the strict refinement
of per-group subset EXCLUDING the equality cell. Strict implication:
this matcher fires ⇒ iter 200 fires (proper subset implies subset
universally). The converse does NOT hold: per-group input_colors=
[1] / output_colors=[1] fires iter 200 (equality is a subset) but
rejects this matcher (output set NOT strictly smaller than input set).

Strict mutual exclusion with iter 201 (``output_colors_equals_input_
colors_per_group``) on every input pattern: per-group equality
forbids strict-proper-subset by construction (set equality on non-
empty sets is incompatible with one set being strictly smaller).
The strict-proper-subset cell and the equality cell are the two
disjoint sub-cells of iter 200's territory; their union recovers
iter 200's fired-gate.

Decoupling with iter 202 (``input_colors_subset_of_output_colors_
per_group``): iter 202 requires input ⊆ output per group; this
matcher requires output ⊂ input per group. The intersection requires
output ⊂ input AND input ⊆ output, which is impossible on non-empty
sets (output ⊂ input means at least one input colour is absent from
output; input ⊆ output means every input colour is present in
output -- contradiction). The two matchers are strictly mutually
exclusive on the cell-count-non-empty domain.

Decoupling with iter 203 (``output_colors_disjoint_from_input_colors_
per_group``): iter 203 requires input ∩ output == ∅ per group; this
matcher requires output ⊂ input per group, which by definition
requires output ⊆ input. With non-empty per-group outputs, output ⊂
input AND input ∩ output == ∅ are incompatible (a non-empty subset
of a non-empty set has non-empty intersection with that set). The
two matchers are strictly mutually exclusive on the cell-count-non-
empty domain.

Why a distinct matcher rather than parameterising iter 200 with a
``strict: True`` flag (mirroring the iter-185 / iter-184 separation
rationale): the matcher contract (docs/RULE_FORMAT.md §4) is name-
keyed recognition vocabulary; the rule's stored ``condition.type``
is the recognition handle's name, not a name+params tuple. The
strict-erasure precondition gates a DIFFERENT rule family than the
equality-tolerant subset precondition (erasure rules vs permutation-
or-erasure rules); keeping them in separate registry slots lets
anti-unification attach the right gate per rule family.

Strict refinement / orthogonality summary (universal-over-groups-and-
pairs semantics):

  * Iter 13 (``identity_transformation``) -- every pair has zero
    change groups. This matcher REJECTS the no-group case (fail-
    closed clause below) to keep its territory disjoint from iter 13
    by construction. Mirrors iter 32 / 35 / 37 / 39 / 193 / 195 /
    196 / 197 / 198 / 199 / 200 / 201 / 202 / 203 empty-group
    rejection.
  * Iter 14 (``input_color_uniform``) -- pins every group's
    ``input_colors`` to a single colour. With single-colour input
    groups, a strict proper subset of a singleton is the empty set;
    this matcher's cell-count requirement rejects empty per-group
    outputs, so the two CANNOT co-fire when iter 14's territory is
    a singleton. Iter 14 fires ⇒ this matcher REJECTS (strict mutual
    exclusion on singleton-input territory).
  * Iter 18 (``output_color_uniform``) -- pins every group's
    ``output_colors`` to a single colour AND that colour identical
    across all groups. Independent of strict-subset in general; CAN
    co-fire when every group's output single-colour is one of its
    input colours AND the input palette is strictly larger than the
    output palette (i.e. every group's input has at least 2 colours).
  * Iter 184 (``output_palette_subset_of_input``) -- whole-grid
    output palette subset of whole-grid input palette per pair.
    INDEPENDENT in general; iter 184 inspects the whole grid, this
    matcher inspects only the change groups. CAN co-fire when
    per-group strict-erasure aligns with whole-grid subset.
  * Iter 185 (``output_palette_equals_input``) -- whole-grid strict
    equality. INDEPENDENT in general; per-group strict-erasure
    leaves at least one input colour absent from each group's
    output, but the whole-grid output palette may still equal the
    whole-grid input palette via unchanged background pixels or via
    other groups' inputs. CAN co-fire on patterns where the per-
    group erased colours are restored elsewhere in the whole-grid
    palette.
  * Iter 186 (``output_palette_disjoint_from_input``) -- whole-grid
    disjoint. THIS MATCHER REJECTS iter-186 territory by
    construction (per-group output ⊂ per-group input means per-group
    output ⊆ per-group input, so per-group output AND per-group input
    share at least one colour; whole-grid output and whole-grid input
    therefore share that colour, contradicting iter 186).
  * Iter 187 (``input_palette_subset_of_output``) -- whole-grid
    input palette subset of whole-grid output palette per pair.
    INDEPENDENT in general; with per-group strict-erasure, the
    whole-grid output may still cover the whole-grid input via
    unchanged background pixels.
  * Iter 200 (``output_colors_subset_of_input_colors_per_group``) --
    per-group subset. THIS MATCHER STRICTLY IMPLIES ITER 200 (proper
    subset implies subset universally). The converse does NOT hold
    (per-group equality fires iter 200 but rejects this matcher).
  * Iter 201 (``output_colors_equals_input_colors_per_group``) --
    per-group equality. STRICTLY MUTUALLY EXCLUSIVE with this matcher
    on every input pattern (set equality forbids strict proper subset
    by construction). The strict-erasure cell (this matcher) and the
    equality cell (iter 201) jointly partition iter 200's territory.
  * Iter 202 (``input_colors_subset_of_output_colors_per_group``) --
    per-group dual subset. STRICTLY MUTUALLY EXCLUSIVE with this
    matcher on non-empty per-group outputs (proven above).
  * Iter 203 (``output_colors_disjoint_from_input_colors_per_group``)
    -- per-group disjoint. STRICTLY MUTUALLY EXCLUSIVE with this
    matcher on non-empty per-group outputs (proven above).
  * Iter 195 / 196 / 197 -- per-group cardinality matchers on
    input / output / product. NOT in a refinement relation in
    general. Iter 196 (per-group output cardinality) plus
    cardinality-strict-less-than-input cardinality is a
    near-precondition for this matcher firing; the matchers are
    INDEPENDENT in the universal-over-pairs scope (across-pair
    constancy claims in iter 195 / 196 / 197 are NOT implied by
    per-group strict-subset).
  * Iter 194 (whole-grid colour translation cross-pair) -- a
    translation by k != 0 has whole-grid output palette disjoint
    from input palette; THIS MATCHER REJECTS any k != 0 translation
    by construction (per-group output ⊂ input requires non-empty
    intersection). Co-fire only on the k == 0 (identity) cell, but
    iter 201 also fires on k == 0 -- so this matcher rejects k == 0
    too via mutual exclusion with iter 201. No co-fire territory.
  * Iter 198 / 199 (per-group colour translation within-pair /
    globally) -- with strict same-cardinality per-group sorted-shift
    and k != 0, the per-group output set is disjoint from the per-
    group input set; this matcher rejects k != 0 translations. With
    k == 0, iter 201 (per-group equality) fires; this matcher
    rejects k == 0 via mutual exclusion with iter 201. No co-fire
    territory.
  * Iter 35 / 36 (``change_input_colors_constant_across_pairs`` /
    ``change_output_colors_constant_across_pairs``) -- per-pair
    input / output colour SET bit-identity. Independent.
  * Iter 8 (``consistent_color_mapping``) -- per-pair (C -> K) is a
    function on changed cells. INDEPENDENT in general; this matcher
    constrains where K lives (in the group's input set) AND that at
    least one input colour is unmapped per group, iter 8 constrains
    how C maps. CAN co-fire when every (C, K) the function maps
    satisfies K in input set per group AND at least one input colour
    per group is dropped.
  * Every cell- / position- / dimension-axis matcher (iters 1 / 17 /
    19 / 20 / 22 / 23 / 24 / 26 / 28 / 32 / 33 / 38 / 39 / 40 / 41 /
    42 / 182 / 183) -- orthogonal to per-group palette content.

Why this matters for ARBOR's intended ruleset:

  * "Per-blob strict-erasure" rule family -- rules whose action
    DROPS at least one colour from every changed blob's input
    palette and introduces no fresh colour (e.g. a rule that erases
    a specific marker colour from every annotated region, leaving
    other region colours untouched). Iter 200's whole-territory
    version cannot distinguish "every blob is strictly smaller in
    palette" from "every blob is identical in palette"; this
    matcher names the strictly stronger strict-erasure cell that is
    the precondition for per-blob erasure rule families.
  * Iter 201 names the per-blob PERMUTATION rule family precondition
    (equality territory); this matcher names the per-blob ERASURE
    rule family precondition (proper-subset territory). The two
    matchers together cover iter 200's territory disjunctively, and
    each names a distinct rule family the gate can attach to.
  * Closes the iter-203-named first-listed next-gap candidate on the
    strict-refinement axis of the per-group palette-relation sub-
    axis. The pending sibling matcher on the same refinement axis
    (named by iter 203's next-gap) is
    ``input_colors_proper_subset_of_output_colors_per_group`` (the
    iter-202 strict-refinement projection, naming the per-blob
    strict-expansion cell).

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
    ... / 201 / 202 / 203 strict-type posture), AND
  - for every group, ``set(output_colors) < set(input_colors)``
    (i.e. ``set(output_colors) <= set(input_colors)`` AND
    ``set(output_colors) != set(input_colors)``).

Why fail-closed on empty / no-group / malformed (same posture as
iters 14 / 30 / 32 / 33 / 34 / 35 / 36 / 37 / 38 / 39 / 184-203): a
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
34 / 35 / 36 / 37 / 38 / 184-203 to keep contract violations from
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


@register("output_colors_proper_subset_of_input_colors_per_group")
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
            out_set = set(output_colors)
            in_set = set(input_colors)
            if not (out_set < in_set):
                return False
    return True
