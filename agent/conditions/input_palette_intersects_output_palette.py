"""
input_palette_intersects_output_palette -- match tasks where EVERY
example pair satisfies, on the whole-grid palettes,
``set(input_palette) & set(output_palette) != empty set``: at least one
colour appears in both the input grid and the output grid of every
example pair. The whole-grid ANCHOR-PRESERVATION precondition.

This matcher is the whole-grid analogue of iter 329's per-group
matcher ``change_palette_intersection_nonempty_per_group``, named in
iter 330's "Next gap" note as the next iter-228-class fresh-axis
candidate:

  > the whole-grid ANCHOR-PRESERVATION matcher --
  > ``set(input_palette) & set(output_palette)`` non-empty per pair,
  > the whole-grid analogue of iter 329's per-group matcher and a
  > strict superset of iter 185 / iter 186 territory (output_palette
  > equals OR proper-subset OR proper-superset OR partial-overlap of
  > input_palette).

Recognition vocabulary axis: the whole-grid ANCHOR-PRESERVATION cell
of the whole-grid palette-relation sub-axis. Names "at least one
input colour survives into the output palette" -- the precondition
for the WHOLE-GRID anchor-preserving rule family (rules that preserve
at least one colour across the whole grid while replacing some input
colours and / or introducing fresh output colours).

Relation to the iter 184 / 185 / 186 / 187 / partial-overlap whole-
grid palette-relation partition (under the non-empty-palette domain):

  * Iter 184 (``output_palette_subset_of_input``) -- B ⊆ A per pair
    (non-strict; equality admitted).
  * Iter 185 (``output_palette_equals_input``) -- A == B per pair.
  * Iter 186 (``output_palette_disjoint_from_input``) -- A ∩ B == ∅
    per pair.
  * Iter 187 (``input_palette_subset_of_output``) -- A ⊆ B per pair
    (non-strict; equality admitted).
  * ``output_palette_partial_overlap_with_input_palette`` -- A ∩ B
    non-empty AND neither side contained in the other.

This matcher's territory is the UNION of {iter 185 equality, iter 184
\\ iter 185 strict-erasure, iter 187 \\ iter 185 strict-expansion,
partial-overlap} -- the four cells whose per-pair whole-grid input-
output intersection is non-empty. Equivalently, the STRICT COMPLEMENT
of iter 186 on the non-empty-palette domain.

Why this matters for ARBOR's intended ruleset
---------------------------------------------

The whole-grid "anchor-preserving rewrite" rule family -- rules whose
action preserves at least one colour shared between the whole-grid
input and output palettes, while replacing some input colours and / or
introducing fresh output colours. Iter 186 names its dual (whole-grid
canvas-rewrite / foreground-erase + relabel, where every output
colour is fresh); this matcher names the positive recognition handle
for the rule family where each pair retains at least one shared
colour between input and output palettes. Anti-unification
(CLAUDE.md section 8) would attach a whole-grid anchor-preservation
generalisation variable to this matcher's fired gate.

Distinct semantic handle vs the bare complement
-----------------------------------------------

While the truth value coincides with "NOT iter 186" on the non-empty-
palette domain, this matcher's purpose is to NAME the whole-grid
anchor-preservation precondition as its own recognition handle. A
rule's stored ``condition.type`` is a name, not a negation expression
(docs/RULE_FORMAT.md section 4); for anti-unification to lift a
whole-grid anchor-preservation variable onto a rule's gate, the gate
must have a positive recognition name to attach to. The same
rationale iters 185 / 186 / 187 / 329 followed when naming whole-grid
palette equality, disjointness, dual-subset, and per-group anchor-
preservation as distinct matchers rather than encoding them as
negations of pre-existing matchers.

Strict refinement / orthogonality summary (universal-over-pairs
semantics):

  * Iter 13 (``identity_transformation``) -- zero changed cells per
    pair; output palette equals input palette per pair. STRICTLY
    IMPLIES this matcher (equal non-empty palettes have non-empty
    intersection). The converse does not hold (a pure permutation
    has changed cells but equal palettes).
  * Iter 184 (``output_palette_subset_of_input``) -- B ⊆ A.
    STRICTLY IMPLIES this matcher on the non-empty-output-palette
    domain (a non-empty subset of A has non-empty intersection with
    A).
  * Iter 185 (``output_palette_equals_input``) -- A == B.
    STRICTLY IMPLIES this matcher on the non-empty-palette domain
    (equal non-empty sets have non-empty intersection).
  * Iter 186 (``output_palette_disjoint_from_input``) -- A ∩ B == ∅.
    STRICTLY MUTUALLY EXCLUSIVE on the non-empty-palette domain
    (both matchers require non-empty palettes; under that domain,
    intersection is either empty (iter 186) or non-empty (this
    matcher), never both).
  * Iter 187 (``input_palette_subset_of_output``) -- A ⊆ B.
    STRICTLY IMPLIES this matcher on the non-empty-input-palette
    domain.
  * ``output_palette_partial_overlap_with_input_palette`` -- A ∩ B
    non-empty AND neither side contained. STRICTLY IMPLIES this
    matcher (it explicitly requires non-empty intersection).
  * ``output_palette_proper_subset_of_input_palette`` -- B ⊊ A.
    STRICTLY IMPLIES this matcher.
  * ``input_palette_proper_subset_of_output_palette`` -- A ⊊ B.
    STRICTLY IMPLIES this matcher.
  * ``output_palette_is_permutation_of_input_palette`` (iter 330) --
    iter 185 ∧ changed-cell mapping bijection. STRICTLY IMPLIES this
    matcher (iter 185 strictly implies it, as above).
  * Iter 329 (``change_palette_intersection_nonempty_per_group``) --
    per-group projection of the same recognition handle. INDEPENDENT
    in general: a task can fire iter 329 (every changed-blob's input
    and output palettes overlap within the blob) while this matcher
    rejects (the whole-grid palettes have no shared colour because
    the unchanged background colours of input and output are
    different -- e.g. background black on input, background grey on
    output, with per-blob anchor preservation). Conversely a task
    can fire this matcher while iter 329 rejects (the whole-grid
    palettes overlap via shared background colour, while per-blob
    palettes are strictly disjoint within blobs).
  * Iter 14 (``input_color_uniform``) / iter 15
    (``output_color_uniform``) -- pin the changed-cell sides to a
    single colour. INDEPENDENT of whole-grid palette overlap.
  * Iter 8 (``consistent_color_mapping``) -- per-pair (C -> K) is a
    function on changed cells. INDEPENDENT in general.
  * Every cell- / position- / dimension-axis matcher (iters 1 / 17 /
    19 / 20 / 22 / 23 / 24 / 26 / 28 / 32 / 33 / 38 / 39 / 40 / 41 /
    42 / 182 / 183) -- orthogonal to whole-grid palette content.

Why a distinct matcher rather than parameterising iter 186 with a
``negate: True`` flag (mirroring the iter 185 / iter 184 separation
rationale and the iter 200 / 201 / 202 / 203 / 204 / 205 / 206
separation rationale): the matcher contract (docs/RULE_FORMAT.md §4)
is name-keyed recognition vocabulary; the rule's stored
``condition.type`` is the recognition handle's name, not a name+params
tuple. The anchor-preservation precondition gates a DIFFERENT rule
family than the canvas-rewrite precondition (whole-grid anchor-
preserving rewrite rules vs whole-grid canvas-rewrite / foreground-
erase rules); keeping the anchor-preservation cell in a separate
registry slot lets anti-unification attach the right gate per rule
family.

Params:
  (none) -- pure set-intersection-nonempty check on per-pair palettes,
  universal over pairs.

Returns True iff:
  - ``patterns`` is a dict, AND
  - ``patterns["pair_analyses"]`` is a non-empty list, AND
  - every analysis is a dict, AND
  - every analysis has an ``input_palette`` value that is a list of
    non-bool ints, AND
  - every analysis has an ``output_palette`` value with the same
    contract, AND
  - for every analysis:
    ``set(input_palette) & set(output_palette) != empty set``.

Why fail-closed on empty / missing / malformed (same posture as iters
184 / 185 / 186 / 187 / partial-overlap): a missing or non-list
palette is upstream extractor breakage, not evidence the precondition
holds. Universal-over-pairs semantics with a vacuously-true empty
case would let an empty patterns dict fire the gate, which is the
wrong default -- a non-empty-intersection claim with zero
observations is meaningless.

Why strict-list-of-non-bool-ints (not range-checked): mirrors the
iter 184 / 185 / 186 / 187 / partial-overlap whole-grid posture --
``_analyze_pair`` emission is unfiltered, so we tolerate any int
value (including the iter-180 erase sentinel ``13``) and let the
upstream extractor handle range validation. The per-group iter 329
applies a stricter [0, 9] gate because the per-group fields are
extracted from the change-cell positions, not the raw grids; the
whole-grid fields here are the raw grid palettes.

No companion-touch required: iter 184 already emits ``input_palette``
and ``output_palette`` from ``_analyze_pair``; this iter is a pure
matcher addition with no ``agent/active_operators.py`` diff.
F8 inert.
"""

from __future__ import annotations

from agent.conditions import register


def _is_palette_list(x) -> bool:
    """A palette field must be a list of non-bool ints. Empty is
    admissible at the type level (the semantic gate's non-empty-
    intersection clause rejects empty palettes)."""
    if not isinstance(x, list):
        return False
    for v in x:
        if not isinstance(v, int) or isinstance(v, bool):
            return False
    return True


@register("input_palette_intersects_output_palette")
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
        if not (set(ip) & set(op)):
            return False
    return True
