"""
output_palette_proper_subset_of_input_palette -- match tasks where
EVERY example pair satisfies, on the whole-grid palettes,
``set(output_palette) < set(input_palette)``: the whole-grid output
palette is contained in the whole-grid input palette AND strictly
smaller (at least one input colour is dropped on the output side).

Recognition vocabulary axis: whole-grid "strict-erasure" cell of the
whole-grid palette-relation sub-axis. Iter 184
(``output_palette_subset_of_input``) admits the equality cell
(output set == input set per pair), making iter 184's territory the
DISJUNCTION of whole-grid equality (iter 185) AND whole-grid strict
erasure (this matcher). The two are mutually exclusive on non-empty
input palettes; together they partition iter 184's territory.

This matcher is the whole-grid projection of iter 204
(``output_colors_proper_subset_of_input_colors_per_group``), in the
same way that iter 184 is the whole-grid projection of iter 200, iter
185 is the whole-grid projection of iter 201, iter 186 is the whole-
grid projection of iter 203, iter 187 is the whole-grid projection of
iter 202, and iter 210 is the whole-grid projection of iter 206. The
two scopes (whole-grid and per-group) are NOT in a refinement relation
in general: a task can satisfy the whole-grid strict-erasure
precondition while having per-group relations of every shape (some
groups equal, some disjoint, etc.), and a task can satisfy the per-
group strict-erasure precondition while the whole-grid palettes are
equal (when per-group erased colours are restored elsewhere in the
grid).

Closure of the whole-grid palette-relation sub-axis (refinement
level): iter 210 closed the equality/subset/disjoint/partial-overlap
five-cell partition on the non-empty-palette domain. This matcher
opens the strict-refinement axis under iter 184: with iter 185
(equality) and this matcher (strict erasure), iter 184's territory
splits into two disjoint sub-cells. The dual matcher
``input_palette_proper_subset_of_output_palette`` (whole-grid version
of iter 205, naming the whole-grid strict-expansion cell under iter
187) is the natural sibling on the same refinement axis.

This matcher carves out the strict-erasure cell -- the cell where
every pair drops at least one of its input colours and introduces no
fresh ones at the whole-grid scope. Anti-unification (CLAUDE.md
section 8) would attach a WHOLE-GRID ERASURE generalisation variable
to this matcher's fired-gate (e.g. a rule that erases a specific
colour across the whole grid, leaving other colours untouched),
distinct from the whole-grid permutation rule family attached to iter
185's fired-gate and the per-blob erasure rule family attached to
iter 204's fired-gate.

Strict refinement of iter 184 (``output_palette_subset_of_input``):
per-pair proper subset is the strict refinement of per-pair subset
EXCLUDING the equality cell. Strict implication: this matcher fires
=> iter 184 fires (proper subset implies subset universally). The
converse does NOT hold: ip = op = [1] fires iter 184 (equality is a
subset) but rejects this matcher (output set NOT strictly smaller
than input set).

Strict mutual exclusion with iter 185 (``output_palette_equals_
input``) on every input pattern: per-pair equality forbids strict
proper subset by construction (set equality is incompatible with one
set being strictly smaller). The strict-erasure cell (this matcher)
and the equality cell (iter 185) are the two disjoint sub-cells of
iter 184's territory; their union recovers iter 184's fired-gate.

Decoupling with iter 187 (``input_palette_subset_of_output``): iter
187 requires input ⊆ output per pair; this matcher requires output ⊂
input per pair. The intersection requires output ⊂ input AND input ⊆
output, which is impossible on non-empty sets (output ⊂ input means
at least one input colour is absent from output; input ⊆ output means
every input colour is present in output -- contradiction). The two
matchers are strictly mutually exclusive on the non-empty-input
domain.

Decoupling with iter 186 (``output_palette_disjoint_from_input``):
iter 186 requires input ∩ output == ∅ per pair; this matcher requires
output ⊂ input per pair, which by definition requires output ⊆ input.
With non-empty output, output ⊂ input AND input ∩ output == ∅ are
incompatible (a non-empty subset of a non-empty set has non-empty
intersection with that set). The two matchers are strictly mutually
exclusive on the non-empty-output domain. With empty output AND non-
empty input, this matcher fires (empty set is a strict proper subset
of any non-empty set) AND iter 186 also fires (empty intersection
with anything). The two CAN co-fire on the empty-output-with-non-
empty-input cell.

Decoupling with iter 210 (``output_palette_partial_overlap_with_
input_palette``): iter 210 requires NOT (output ⊆ input) per pair;
this matcher requires output ⊊ input per pair, which implies output ⊆
input. STRICTLY MUTUALLY EXCLUSIVE.

Why a distinct matcher rather than parameterising iter 184 with a
``strict: True`` flag (mirroring the iter-185 / iter-184 separation
rationale and the iter 204 / iter 200 separation rationale): the
matcher contract (docs/RULE_FORMAT.md §4) is name-keyed recognition
vocabulary; the rule's stored ``condition.type`` is the recognition
handle's name, not a name+params tuple. The strict-erasure
precondition gates a DIFFERENT rule family than the equality-tolerant
subset precondition (erasure rules vs permutation-or-erasure rules);
keeping them in separate registry slots lets anti-unification attach
the right gate per rule family.

Strict refinement / orthogonality summary (universal-over-pairs
semantics, whole-grid scope):

  * Iter 13 (``identity_transformation``) -- zero changed cells; the
    output palette is necessarily equal to the input palette, so iter
    185 fires and THIS MATCHER REJECTS (strict mutual exclusion with
    iter 185).
  * Iter 14 (``input_color_uniform``) -- pins the changed cells'
    source colour to a single colour; says nothing about whole-grid
    palette membership. INDEPENDENT.
  * Iter 18 (``output_color_uniform``) -- pins the changed cells'
    target colour to a single colour; says nothing about whole-grid
    palette containment. INDEPENDENT.
  * Iter 184 (``output_palette_subset_of_input``) -- THIS MATCHER
    STRICTLY IMPLIES ITER 184. The converse does NOT hold (per-pair
    equality fires iter 184 but rejects this matcher).
  * Iter 185 (``output_palette_equals_input``) -- STRICTLY MUTUALLY
    EXCLUSIVE with this matcher on every input pattern (set equality
    forbids strict proper subset by construction). The strict-erasure
    cell (this matcher) and the equality cell (iter 185) jointly
    partition iter 184's territory.
  * Iter 186 (``output_palette_disjoint_from_input``) -- decoupled
    above. Co-fire only on the empty-output cell.
  * Iter 187 (``input_palette_subset_of_output``) -- STRICTLY
    MUTUALLY EXCLUSIVE on non-empty input domain (proven above).
  * Iter 188 (``output_palette_count_exceeds_input_palette_count``)
    -- strict |output| > |input|. STRICTLY MUTUALLY EXCLUSIVE with
    this matcher (proper subset implies |output| < |input| on non-
    empty inputs; strict-greater is the opposite direction).
  * Iter 189 (``input_palette_count_exceeds_output_palette_count``)
    -- strict |input| > |output|. STRICT IMPLICATION: this matcher
    fires (with non-empty input) => iter 189 fires (proper subset
    forces |output| < |input| on non-empty inputs). The converse
    does NOT hold (|input| > |output| with disjoint palettes fires
    iter 189 but not this matcher).
  * Iter 190 (``palette_symmetric_difference_constant_across_pairs``)
    -- cross-pair |A △ B| constancy. INDEPENDENT in general; CAN co-
    fire when every pair carries the same |A △ B| AND every pair
    satisfies the strict-erasure cell.
  * Iter 191 (``palette_intersection_count_constant_across_pairs``)
    -- cross-pair |A ∩ B| constancy. INDEPENDENT in general; CAN
    co-fire when |A ∩ B| (= |B| for proper subset) is constant across
    pairs.
  * Iter 45 (``palette_union_count_constant_across_pairs``) -- cross-
    pair |A ∪ B| constancy. INDEPENDENT in general; CAN co-fire when
    |A ∪ B| (= |A| for proper subset) is constant across pairs.
  * Iter 204 (``output_colors_proper_subset_of_input_colors_per_
    group``) -- per-group strict-erasure cell. INDEPENDENT in general
    (whole-grid and per-group scopes are NOT in a refinement
    relation, as explained above). CAN co-fire on tasks where both
    scopes carry the same strict-erasure shape.
  * Iter 210 (``output_palette_partial_overlap_with_input_palette``)
    -- whole-grid partial-overlap residual cell. STRICTLY MUTUALLY
    EXCLUSIVE with this matcher (decoupled above).
  * Iter 8 (``consistent_color_mapping``) -- per-pair (C -> K) is a
    function on changed cells. INDEPENDENT in general.
  * Every cell- / position- / dimension-axis matcher (iters 1 / 17 /
    19 / 20 / 22 / 23 / 24 / 26 / 28 / 32 / 33 / 38 / 39 / 40 / 41 /
    42 / 182 / 183) -- orthogonal to whole-grid palette content.

Why this matters for ARBOR's intended ruleset:

  * "Whole-grid strict-erasure" rule family -- rules whose action
    DROPS at least one colour from the whole-grid input palette and
    introduces no fresh colour (e.g. a rule that erases a specific
    marker colour across the whole grid, leaving every other colour
    untouched). Iter 184's territory cannot distinguish "the output
    palette is strictly smaller" from "the output palette is
    identical"; this matcher names the strictly stronger strict-
    erasure cell that is the precondition for whole-grid erasure
    rule families.
  * Iter 185 names the whole-grid PERMUTATION rule family
    precondition (equality territory); this matcher names the whole-
    grid ERASURE rule family precondition (proper-subset territory).
    The two matchers together cover iter 184's territory
    disjunctively, and each names a distinct rule family the gate
    can attach to.
  * Closes the iter-210-named first-listed next-gap candidate on the
    strict-refinement axis of the whole-grid palette-relation sub-
    axis. The pending sibling matcher on the same refinement axis
    (named by iter 210's next-gap) is
    ``input_palette_proper_subset_of_output_palette`` (the iter-187
    strict-refinement projection, naming the whole-grid strict-
    expansion cell).

Params:
  (none) -- pure per-pair strict-proper-subset check, universal over
  pairs on the whole-grid palettes.

Returns True iff:
  - ``patterns`` is a dict, AND
  - ``patterns["pair_analyses"]`` is a non-empty list, AND
  - every analysis is a dict, AND
  - every analysis has an ``input_palette`` value that is a list of
    non-bool ints (mirroring iter 184 / 185 / 186 / 187 / 190 / 191 /
    210 whole-grid posture; empty admissible at the type level, the
    semantic gate rejects empty inputs by the proper-subset
    requirement), AND
  - every analysis has an ``output_palette`` value with the same
    contract, AND
  - for every analysis,
    ``set(output_palette) < set(input_palette)`` (proper-subset:
    ``set(output_palette) <= set(input_palette)`` AND
    ``set(output_palette) != set(input_palette)``).

Why fail-closed on empty / missing / malformed (same posture as iters
184 / 185 / 186 / 187 / 190 / 191 / 210): a missing or non-list
palette is upstream extractor breakage, not evidence the precondition
holds. Universal-over-pairs semantics with a vacuously-true empty
case would let an empty patterns dict fire the gate, which is the
wrong default -- a strict-erasure claim with zero observations is
meaningless.

Why strict-list-of-non-bool-ints (not range-checked): mirrors the
iter 184 / 185 / 186 / 187 / 190 / 191 / 210 whole-grid posture --
``_analyze_pair`` emission is unfiltered, so we tolerate any int
value (including the iter-180 erase sentinel ``13``) and let the
upstream extractor handle range validation. The per-group iter 204
applies a stricter [0, 9] gate because the per-group fields are
extracted from the change-cell positions, not the raw grids; the
whole-grid fields here are the raw grid palettes.

No companion-touch required: ``input_palette`` and ``output_palette``
have been emitted per pair_analysis since iter 184; this iter is a
pure matcher addition with no ``agent/active_operators.py`` diff.
F8 inert.
"""

from __future__ import annotations

from agent.conditions import register


def _is_palette_list(x) -> bool:
    """A palette field must be a list of non-bool ints. Empty is
    admissible at the type level (the semantic gate's proper-subset
    requirement rejects empty input palettes)."""
    if not isinstance(x, list):
        return False
    for v in x:
        if not isinstance(v, int) or isinstance(v, bool):
            return False
    return True


@register("output_palette_proper_subset_of_input_palette")
def match(patterns: dict, params: dict) -> bool:
    if not isinstance(patterns, dict):
        return False
    pair_analyses = patterns.get("pair_analyses")
    if not isinstance(pair_analyses, list) or not pair_analyses:
        return False

    for analysis in pair_analyses:
        if not isinstance(analysis, dict):
            return False
        ip = analysis.get("input_palette")
        op = analysis.get("output_palette")
        if not _is_palette_list(ip):
            return False
        if not _is_palette_list(op):
            return False
        if not (set(op) < set(ip)):
            return False
    return True
