"""
input_palette_proper_subset_of_output_palette -- match tasks where
EVERY example pair satisfies, on the whole-grid palettes,
``set(input_palette) < set(output_palette)``: the whole-grid input
palette is contained in the whole-grid output palette AND strictly
smaller (at least one fresh output colour is added that is absent
from the input side).

Recognition vocabulary axis: whole-grid "strict-expansion" cell of
the whole-grid palette-relation sub-axis. Iter 187
(``input_palette_subset_of_output``) admits the equality cell
(input set == output set per pair), making iter 187's territory the
DISJUNCTION of whole-grid equality (iter 185) AND whole-grid strict
expansion (this matcher). The two are mutually exclusive on non-
empty input palettes; together they partition iter 187's territory.

This matcher is the whole-grid projection of iter 205
(``input_colors_proper_subset_of_output_colors_per_group``), in the
same way that iter 184 is the whole-grid projection of iter 200, iter
185 is the whole-grid projection of iter 201, iter 186 is the whole-
grid projection of iter 203, iter 187 is the whole-grid projection of
iter 202, iter 210 is the whole-grid projection of iter 206, and iter
211 is the whole-grid projection of iter 204. The two scopes (whole-
grid and per-group) are NOT in a refinement relation in general: a
task can satisfy the whole-grid strict-expansion precondition while
having per-group relations of every shape (some groups equal, some
disjoint, etc.), and a task can satisfy the per-group strict-
expansion precondition while the whole-grid palettes are equal (when
per-group added colours are already present elsewhere in the input
grid outside the changed cells).

Closure of the whole-grid palette-relation sub-axis (refinement
level): iter 210 closed the equality/subset/disjoint/partial-overlap
five-cell partition on the non-empty-palette domain. Iter 211 opened
the strict-refinement axis under iter 184 (strict-erasure cell). This
matcher closes the symmetric strict-refinement axis under iter 187:
with iter 185 (equality) and this matcher (strict expansion), iter
187's territory splits into two disjoint sub-cells. With iters 211
and this matcher both landed, the whole-grid strict-refinement axis
is FULLY CLOSED -- both iter 184 and iter 187 are partitioned into
equality + their respective strict refinements.

This matcher carves out the strict-expansion cell -- the cell where
every pair adds at least one fresh output colour and erases none of
its input colours at the whole-grid scope. Anti-unification
(CLAUDE.md section 8) would attach a WHOLE-GRID EXPANSION
generalisation variable to this matcher's fired-gate (e.g. a rule
that overlays a fresh annotation colour across the whole grid,
preserving every existing input colour), distinct from the whole-grid
permutation rule family attached to iter 185's fired-gate, the whole-
grid erasure rule family attached to iter 211's fired-gate, and the
per-blob expansion rule family attached to iter 205's fired-gate.

Strict refinement of iter 187 (``input_palette_subset_of_output``):
per-pair proper subset is the strict refinement of per-pair subset
EXCLUDING the equality cell. Strict implication: this matcher fires
=> iter 187 fires (proper subset implies subset universally). The
converse does NOT hold: ip = op = [1] fires iter 187 (equality is a
subset) but rejects this matcher (input set NOT strictly smaller
than output set).

Strict mutual exclusion with iter 185 (``output_palette_equals_
input``) on every input pattern: per-pair equality forbids strict
proper subset by construction (set equality is incompatible with one
set being strictly smaller). The strict-expansion cell (this
matcher) and the equality cell (iter 185) are the two disjoint sub-
cells of iter 187's territory; their union recovers iter 187's
fired-gate.

Symmetric dual of iter 211 (``output_palette_proper_subset_of_input_
palette``): iter 211 carves out the strict-erasure cell (output ⊊
input) under iter 184; this matcher carves out the strict-expansion
cell (input ⊊ output) under iter 187. The two are strictly mutually
exclusive on non-empty palettes: output ⊊ input AND input ⊊ output
would require strict cardinality inequality in opposite directions
simultaneously, which is impossible.

Decoupling with iter 184 (``output_palette_subset_of_input``): iter
184 requires output ⊆ input per pair; this matcher requires input ⊊
output per pair, which by definition requires input ⊆ output. The
intersection requires output ⊆ input AND input ⊊ output, which on
non-empty sets forces equality of cardinality (output ⊆ input gives
|output| ≤ |input|; input ⊊ output gives |input| < |output|; chaining
gives |output| ≤ |input| < |output|, contradiction). STRICTLY
MUTUALLY EXCLUSIVE on non-empty input domain.

Decoupling with iter 186 (``output_palette_disjoint_from_input``):
iter 186 requires input ∩ output == ∅ per pair; this matcher requires
input ⊊ output per pair, which by definition requires input ⊆
output. With non-empty input, input ⊊ output AND input ∩ output ==
∅ are incompatible (a non-empty subset of a non-empty set has non-
empty intersection with that set). The two matchers are strictly
mutually exclusive on the non-empty-input domain. With empty input
AND non-empty output, this matcher fires (empty set is a strict
proper subset of any non-empty set) AND iter 186 also fires (empty
intersection with anything). The two CAN co-fire on the empty-input-
with-non-empty-output cell.

Decoupling with iter 210 (``output_palette_partial_overlap_with_
input_palette``): iter 210 requires NOT (input ⊆ output) per pair
AND NOT (output ⊆ input) per pair; this matcher requires input ⊊
output per pair, which implies input ⊆ output. STRICTLY MUTUALLY
EXCLUSIVE.

Why a distinct matcher rather than parameterising iter 187 with a
``strict: True`` flag (mirroring the iter-185 / iter-184 separation
rationale and the iter 211 / iter 184 separation rationale): the
matcher contract (docs/RULE_FORMAT.md §4) is name-keyed recognition
vocabulary; the rule's stored ``condition.type`` is the recognition
handle's name, not a name+params tuple. The strict-expansion
precondition gates a DIFFERENT rule family than the equality-tolerant
subset precondition (expansion / annotation rules vs permutation-or-
expansion rules); keeping them in separate registry slots lets anti-
unification attach the right gate per rule family.

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
  * Iter 184 (``output_palette_subset_of_input``) -- STRICTLY
    MUTUALLY EXCLUSIVE with this matcher on non-empty input domain
    (proven above).
  * Iter 185 (``output_palette_equals_input``) -- STRICTLY MUTUALLY
    EXCLUSIVE with this matcher on every input pattern (set equality
    forbids strict proper subset by construction). The strict-
    expansion cell (this matcher) and the equality cell (iter 185)
    jointly partition iter 187's territory.
  * Iter 186 (``output_palette_disjoint_from_input``) -- decoupled
    above. Co-fire only on the empty-input cell.
  * Iter 187 (``input_palette_subset_of_output``) -- THIS MATCHER
    STRICTLY IMPLIES ITER 187. The converse does NOT hold (per-pair
    equality fires iter 187 but rejects this matcher).
  * Iter 188 (``output_palette_count_exceeds_input_palette_count``)
    -- strict |output| > |input|. STRICT IMPLICATION: this matcher
    fires (with non-empty input or non-empty output) => iter 188
    fires (proper subset forces |input| < |output| on non-empty
    outputs). The converse does NOT hold (|output| > |input| with
    disjoint palettes fires iter 188 but not this matcher).
  * Iter 189 (``input_palette_count_exceeds_output_palette_count``)
    -- strict |input| > |output|. STRICTLY MUTUALLY EXCLUSIVE with
    this matcher (proper subset implies |input| < |output| on non-
    empty outputs; strict-greater is the opposite direction).
  * Iter 190 (``palette_symmetric_difference_constant_across_pairs``)
    -- cross-pair |A △ B| constancy. INDEPENDENT in general; CAN co-
    fire when every pair carries the same |A △ B| AND every pair
    satisfies the strict-expansion cell.
  * Iter 191 (``palette_intersection_count_constant_across_pairs``)
    -- cross-pair |A ∩ B| constancy. INDEPENDENT in general; CAN
    co-fire when |A ∩ B| (= |A| for proper subset of input into
    output) is constant across pairs.
  * Iter 45 (``palette_union_count_constant_across_pairs``) -- cross-
    pair |A ∪ B| constancy. INDEPENDENT in general; CAN co-fire when
    |A ∪ B| (= |B| for proper subset of input into output) is
    constant across pairs.
  * Iter 205 (``input_colors_proper_subset_of_output_colors_per_
    group``) -- per-group strict-expansion cell. INDEPENDENT in
    general (whole-grid and per-group scopes are NOT in a refinement
    relation, as explained above). CAN co-fire on tasks where both
    scopes carry the same strict-expansion shape.
  * Iter 210 (``output_palette_partial_overlap_with_input_palette``)
    -- whole-grid partial-overlap residual cell. STRICTLY MUTUALLY
    EXCLUSIVE with this matcher (decoupled above).
  * Iter 211 (``output_palette_proper_subset_of_input_palette``) --
    SYMMETRIC DUAL: whole-grid strict-erasure cell. STRICTLY MUTUALLY
    EXCLUSIVE with this matcher on non-empty palettes (proper subset
    in opposite directions simultaneously is impossible).
  * Iter 8 (``consistent_color_mapping``) -- per-pair (C -> K) is a
    function on changed cells. INDEPENDENT in general.
  * Every cell- / position- / dimension-axis matcher (iters 1 / 17 /
    19 / 20 / 22 / 23 / 24 / 26 / 28 / 32 / 33 / 38 / 39 / 40 / 41 /
    42 / 182 / 183) -- orthogonal to whole-grid palette content.

Why this matters for ARBOR's intended ruleset:

  * "Whole-grid strict-expansion" rule family -- rules whose action
    ADDS at least one colour to the whole-grid output palette and
    erases none from the input (e.g. a rule that paints a fresh
    annotation/border/marker colour onto the grid, leaving every
    existing input colour untouched). Iter 187's territory cannot
    distinguish "the output palette is strictly larger" from "the
    output palette is identical"; this matcher names the strictly
    stronger strict-expansion cell that is the precondition for
    whole-grid expansion rule families.
  * Iter 185 names the whole-grid PERMUTATION rule family
    precondition (equality territory); iter 211 names the whole-grid
    ERASURE rule family precondition (proper-subset-output-of-input
    territory); this matcher names the whole-grid EXPANSION rule
    family precondition (proper-subset-input-of-output territory).
    The three matchers (185 / 211 / this) together partition the
    iter 184 ∪ iter 187 territory into three disjoint cells (output
    erasure / equality / output expansion), and each names a distinct
    rule family the gate can attach to.
  * Closes the iter-211-named first-listed next-gap candidate on the
    same strict-refinement axis: iter 211 named this matcher (the
    iter-187 strict-refinement projection, naming the whole-grid
    strict-expansion cell) as the natural sibling on the same
    refinement axis. With this matcher landed, the whole-grid strict-
    refinement axis is FULLY CLOSED.

Params:
  (none) -- pure per-pair strict-proper-subset check, universal over
  pairs on the whole-grid palettes.

Returns True iff:
  - ``patterns`` is a dict, AND
  - ``patterns["pair_analyses"]`` is a non-empty list, AND
  - every analysis is a dict, AND
  - every analysis has an ``input_palette`` value that is a list of
    non-bool ints (mirroring iter 184 / 185 / 186 / 187 / 190 / 191 /
    210 / 211 whole-grid posture; empty admissible at the type level,
    the semantic gate rejects empty outputs by the proper-subset
    requirement), AND
  - every analysis has an ``output_palette`` value with the same
    contract, AND
  - for every analysis,
    ``set(input_palette) < set(output_palette)`` (proper-subset:
    ``set(input_palette) <= set(output_palette)`` AND
    ``set(input_palette) != set(output_palette)``).

Why fail-closed on empty / missing / malformed (same posture as iters
184 / 185 / 186 / 187 / 190 / 191 / 210 / 211): a missing or non-list
palette is upstream extractor breakage, not evidence the precondition
holds. Universal-over-pairs semantics with a vacuously-true empty
case would let an empty patterns dict fire the gate, which is the
wrong default -- a strict-expansion claim with zero observations is
meaningless.

Why strict-list-of-non-bool-ints (not range-checked): mirrors the
iter 184 / 185 / 186 / 187 / 190 / 191 / 210 / 211 whole-grid posture
-- ``_analyze_pair`` emission is unfiltered, so we tolerate any int
value (including the iter-180 erase sentinel ``13``) and let the
upstream extractor handle range validation. The per-group iter 205
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
    requirement rejects empty output palettes)."""
    if not isinstance(x, list):
        return False
    for v in x:
        if not isinstance(v, int) or isinstance(v, bool):
            return False
    return True


@register("input_palette_proper_subset_of_output_palette")
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
        if not (set(ip) < set(op)):
            return False
    return True
