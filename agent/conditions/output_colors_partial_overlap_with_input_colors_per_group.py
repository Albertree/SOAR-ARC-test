"""
output_colors_partial_overlap_with_input_colors_per_group -- match
tasks where EVERY change group of EVERY example pair satisfies
``set(group["input_colors"]) & set(group["output_colors"]) != empty
set`` AND ``NOT (set(input_colors) <= set(output_colors))`` AND
``NOT (set(output_colors) <= set(input_colors))``. The per-group
input palette and per-group output palette share at least one colour
(non-empty intersection), yet neither contains the other: each side
carries at least one colour absent from the other.

Recognition vocabulary axis: per-group "partial-overlap residual"
cell of the per-group palette-relation sub-axis closed by iters
200 / 201 / 202 / 203 / 204 / 205. The five preceding per-group
palette-relation cells are:

  * Iter 201 -- per-group EQUALITY: input == output per group.
  * Iter 204 -- per-group STRICT ERASURE: output ⊊ input per group
    (output ⊆ input AND output != input). Iter 200 fires alone (iter
    201 / 204 jointly partition iter 200's territory).
  * Iter 205 -- per-group STRICT EXPANSION: input ⊊ output per group
    (input ⊆ output AND input != output). Iter 202 fires alone (iter
    201 / 205 jointly partition iter 202's territory).
  * Iter 203 -- per-group DISJOINT: input ∩ output == ∅ per group.
  * THIS MATCHER -- per-group PARTIAL OVERLAP residual: intersection
    is non-empty AND neither side contains the other (each side has
    at least one colour absent from the other).

Closure of the per-group palette-relation sub-axis: the five cells
above PARTITION the universe of per-group palette-relation patterns
under the cell-count-non-empty domain (the cell-count requirement
makes every per-group input / output palette non-empty by
construction). The five-cell partition lemma:

  Let A = set(input_colors), B = set(output_colors), both non-empty.
  Exactly ONE of the following holds:
    (i)   A == B                                                  → iter 201
    (ii)  B ⊊ A          (i.e. B ⊆ A and B != A)                  → iter 204
    (iii) A ⊊ B          (i.e. A ⊆ B and A != B)                  → iter 205
    (iv)  A ∩ B == ∅                                              → iter 203
    (v)   A ∩ B != ∅ and NOT (A ⊆ B) and NOT (B ⊆ A)              → THIS MATCHER

  Proof: cases (i)-(iii) are exactly the subset/equality partition of
  the case "one side is a subset of the other"; cases (iv)-(v)
  partition the case "neither side is a subset of the other" by the
  empty-intersection / non-empty-intersection cut. The five cases
  cover the universe and are pairwise disjoint.

The universal-over-groups-and-pairs claim then partitions the
universe of patterns (under the cell-count-non-empty domain) into
five disjoint cells, one per matcher. The five matchers together
NAME every cell of this sub-axis.

This matcher's territory: the per-blob "recolour-with-shared-anchor"
cell -- rules whose action preserves at least one foreground colour
per blob (the shared colour in the intersection) while replacing
other colours and introducing fresh ones. Anti-unification
(CLAUDE.md section 8) would attach a per-blob "anchor-preserving
substitution" generalisation variable to this matcher's fired-gate
(the substitution is partial -- some colours retained, others
swapped or added per blob), distinct from the per-blob PERMUTATION
variable attached to iter 201's fired-gate (which preserves the
whole palette via colour-swap), the per-blob ERASURE variable
attached to iter 204's fired-gate (which only drops colours), the
per-blob EXPANSION variable attached to iter 205's fired-gate
(which only adds colours), and the per-blob CANVAS-REWRITE variable
attached to iter 203's fired-gate (which replaces every colour
with a fresh one).

Strict mutual exclusion with every other per-group palette-relation
cell (universal over the cell-count-non-empty domain):

  * Iter 200 (output ⊆ input per group): if iter 200 fires, then
    per-group output ⊆ input. THIS MATCHER requires NOT (output ⊆
    input) per group; the two are STRICTLY MUTUALLY EXCLUSIVE under
    universal-over-groups semantics.
  * Iter 201 (equality per group): if iter 201 fires, then per-group
    output == input, which implies output ⊆ input AND input ⊆ output.
    THIS MATCHER requires BOTH containments to fail. STRICTLY
    MUTUALLY EXCLUSIVE.
  * Iter 202 (input ⊆ output per group): symmetric to iter 200.
    STRICTLY MUTUALLY EXCLUSIVE.
  * Iter 203 (disjoint per group): iter 203 requires per-group input
    ∩ output == ∅. THIS MATCHER requires per-group input ∩ output !=
    ∅. STRICTLY MUTUALLY EXCLUSIVE.
  * Iter 204 (output ⊊ input per group): strict refinement of iter
    200. STRICTLY MUTUALLY EXCLUSIVE with this matcher (output ⊆
    input AND NOT (output ⊆ input) is a contradiction).
  * Iter 205 (input ⊊ output per group): strict refinement of iter
    202. STRICTLY MUTUALLY EXCLUSIVE with this matcher (input ⊆
    output AND NOT (input ⊆ output) is a contradiction).

Decoupling from neighbouring matchers:

  * Iter 13 (``identity_transformation``) -- every pair has zero
    change groups. This matcher REJECTS the no-group case (fail-
    closed clause below) to keep its territory disjoint from iter 13
    by construction. Mirrors iter 32 / 35 / 37 / 39 / 193 / 195 /
    196 / 197 / 198 / 199 / 200 / 201 / 202 / 203 / 204 / 205 empty-
    group rejection.
  * Iter 14 (``input_color_uniform``) -- pins every group's
    ``input_colors`` to a single colour AND that colour identical
    across all groups. With single-element per-group input set A =
    {c}, the only possible relations with non-empty per-group output
    set B are: B == {c} (equality, iter 201) / {c} ⊂ B (strict
    expansion, iter 205) / B ⊆ {c} with B == {c} (equality again) /
    B disjoint from {c} (iter 203). The partial-overlap cell
    REQUIRES NOT (A ⊆ B) -- impossible with |A| == 1 since A ⊆ B is
    equivalent to c in B, and NOT (B ⊆ A) AND c in B together
    require |B| >= 2 with B not equal to {c}; but then A = {c} ⊆ B
    contradicts NOT (A ⊆ B). Therefore iter 14 fires ⇒ this matcher
    REJECTS (strict mutual exclusion on singleton-input territory).
  * Iter 18 (``output_color_uniform``) -- symmetric singleton case
    on the OUTPUT side. By the same argument, iter 18 fires ⇒ this
    matcher REJECTS (strict mutual exclusion on singleton-output
    territory).
  * Iter 184 (``output_palette_subset_of_input``) -- whole-grid
    output palette subset of whole-grid input palette per pair.
    INDEPENDENT in general; per-group partial overlap can co-fire
    with whole-grid subset when the per-group fresh output colours
    are already present in the whole-grid input palette via other
    groups or background pixels.
  * Iter 185 (``output_palette_equals_input``) -- whole-grid strict
    equality. INDEPENDENT in general; partial-overlap per-group does
    not pin the whole-grid palette relationship.
  * Iter 186 (``output_palette_disjoint_from_input``) -- whole-grid
    disjoint. THIS MATCHER REJECTS iter-186 territory by
    construction (per-group input ∩ output != ∅ implies the union of
    per-group input colours and the union of per-group output colours
    share at least one colour; whole-grid input and whole-grid output
    therefore share that colour, contradicting iter 186). STRICT
    MUTUAL EXCLUSION.
  * Iter 187 (``input_palette_subset_of_output``) -- whole-grid
    input palette subset of whole-grid output palette per pair.
    INDEPENDENT in general; partial overlap per-group is decoupled
    from whole-grid containment.
  * Iter 194 (whole-grid colour translation cross-pair) -- a
    translation by k != 0 has whole-grid output palette disjoint
    from input palette; THIS MATCHER REJECTS k != 0 translations
    (per-group input ∩ output != ∅ requires non-empty intersection).
    The k == 0 (identity) cell triggers iter 201 -- and since iter
    201 is strictly mutually exclusive with this matcher, iter 194
    AND this matcher are universally incompatible on iter 194's
    fired-gate.
  * Iter 198 / 199 (per-group colour translation within-pair /
    globally) -- with strict same-cardinality per-group sorted-shift
    and k != 0, per-group input is disjoint from per-group output;
    this matcher rejects k != 0 translations. With k == 0, iter 201
    fires; this matcher rejects k == 0 too via mutual exclusion with
    iter 201. No co-fire territory.
  * Iter 195 / 196 / 197 -- per-group cardinality matchers on
    input / output / product. NOT in a refinement relation in
    general. The partial-overlap cell requires |A| >= 2 AND |B| >= 2
    AND |A ∩ B| >= 1 AND |A \\ B| >= 1 AND |B \\ A| >= 1 (i.e. both
    sides have at least 2 colours and they overlap partially).
  * Iter 35 / 36 (``change_input_colors_constant_across_pairs`` /
    ``change_output_colors_constant_across_pairs``) -- per-pair
    input / output colour SET bit-identity. Independent.
  * Iter 8 (``consistent_color_mapping``) -- per-pair (C -> K) is a
    function on changed cells. INDEPENDENT in general.
  * Every cell- / position- / dimension-axis matcher (iters 1 / 17 /
    19 / 20 / 22 / 23 / 24 / 26 / 28 / 32 / 33 / 38 / 39 / 40 / 41 /
    42 / 182 / 183) -- orthogonal to per-group palette content.

Why a distinct matcher rather than parameterising iters 200 / 202 /
203 with a ``partial_overlap: True`` flag (mirroring the iter-185 /
iter-184 separation rationale and iter 204 / 205's symmetric-dual
rationale): the matcher contract (docs/RULE_FORMAT.md §4) is name-
keyed recognition vocabulary; the rule's stored ``condition.type``
is the recognition handle's name, not a name+params tuple. The
partial-overlap precondition gates a DIFFERENT rule family than any
of the subset / equality / disjoint preconditions (anchor-preserving
substitution rules, distinct from permutation / erasure / expansion /
canvas-rewrite rules); keeping the partial-overlap cell in a
separate registry slot lets anti-unification attach the right gate
per rule family.

Why this matters for ARBOR's intended ruleset:

  * "Per-blob anchor-preserving substitution" rule family -- rules
    whose action preserves at least one colour per blob (the
    intersection) while replacing other colours per blob. E.g. a
    rule that preserves a foreground colour while replacing
    background colour and introducing a fresh annotation colour
    per blob. Iter 200 / 202 / 203's territories cannot express
    this cell: iter 200 forbids fresh output colours, iter 202
    forbids erased input colours, iter 203 forbids any shared
    colour at all. This matcher names the strictly stronger
    partial-overlap residual cell that is the precondition for
    per-blob anchor-preserving substitution rule families.
  * Iter 201 names the per-blob PERMUTATION rule family precondition
    (equality territory); iter 204 names the per-blob ERASURE rule
    family precondition; iter 205 names the per-blob EXPANSION rule
    family precondition; iter 203 names the per-blob CANVAS-REWRITE
    rule family precondition (disjoint territory); this matcher
    names the per-blob ANCHOR-PRESERVING-SUBSTITUTION rule family
    precondition. The five matchers together cover the entire
    universe of per-group palette-relation patterns under the cell-
    count-non-empty domain, each naming a distinct rule family the
    gate can attach to.
  * Closes the iter-205-named last-listed next-gap candidate on the
    per-group palette-relation sub-axis. With iters 200 / 201 / 202 /
    203 / 204 / 205 / this iter all landed, every cell of the per-
    group palette-relation sub-axis under the cell-count-non-empty
    domain is named, and the partition is complete.

Params:
  (none) -- pure per-group partial-overlap check, universal over
  groups and pairs.

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
    ... / 201 / 202 / 203 / 204 / 205 strict-type posture), AND
  - for every group, ``set(input_colors) & set(output_colors) != ∅``
    AND ``NOT (set(input_colors) <= set(output_colors))`` AND
    ``NOT (set(output_colors) <= set(input_colors))``.

Why fail-closed on empty / no-group / malformed (same posture as
iters 14 / 30 / 32 / 33 / 34 / 35 / 36 / 37 / 38 / 39 / 184-205): a
missing or zero-group pair is upstream extractor breakage or
identity-territory; a partial-overlap claim with zero observations
would double-cover iter 13.

Why ``input_colors`` and ``output_colors`` both required non-empty
lists per group (``len >= 1``): a connected change group has at
least one cell; each cell has both an input colour and an output
colour; the per-group ``input_colors`` / ``output_colors`` fields
are the sorted sets of those colours, which are non-empty for any
non-empty group. A zero-length colour list is an extractor contract
violation, not a valid empty-set partial-overlap case.

Why strict per-colour validation (bool rejected, range checked):
``input_colors`` / ``output_colors`` carry small ints in [0, 9]; the
matcher performs the same strict-type gating as iter 14 / 18 / 19 /
34 / 35 / 36 / 37 / 38 / 184-205 to keep contract violations from
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


@register("output_colors_partial_overlap_with_input_colors_per_group")
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
            if not (in_set & out_set):
                return False
            if in_set <= out_set:
                return False
            if out_set <= in_set:
                return False
    return True
