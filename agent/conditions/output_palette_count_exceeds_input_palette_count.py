"""
output_palette_count_exceeds_input_palette_count -- match tasks where
every example pair has strictly more distinct colours in its output
palette than in its input palette: ``len(set(output_palette)) >
len(set(input_palette))`` on every pair.

Recognition vocabulary axis: cardinality projection of the whole-grid
colour palette axis opened by iter 184 and developed by iters 185 /
186 / 187. The four palette-CONTAINMENT slots (iter 184 output ⊆
input; iter 185 equality; iter 186 disjoint; iter 187 input ⊆ output)
name *set-membership* preconditions on the palette pair; this matcher
names a *cardinality-direction* precondition, the (δ) slot explicitly
listed in iter 187's next-gap note alongside (γ) symmetric-difference
constancy and (ε) palette-shift constancy.

Why a separate matcher rather than parameterising iter 187 (input ⊆
output) with a count comparator:

  * The matcher contract (docs/RULE_FORMAT.md §4) is name-keyed
    recognition vocabulary; the rule's stored ``condition.type`` is
    the recognition handle's name, not a name+params tuple. Adding a
    "strict_size" flag onto iter 187 would entangle two distinct
    preconditions under one registry slot, which the iter-34..42
    family explicitly avoided with separate matchers per axis
    projection. Cardinality direction is its own axis, orthogonal to
    set-containment direction.
  * iter 187 fires on palette-equality (every input colour survives,
    no fresh colour added) AND on palette-expansion (every input
    colour survives, at least one fresh colour added). The two cases
    differ on the cardinality direction:
      - equality: ``|output| == |input|``
      - expansion: ``|output| >  |input|``
    iter 187 does NOT distinguish them; this matcher does. The
    conjunction (iter 187 AND this matcher) is the named recognition
    handle for *strict* palette expansion, i.e. ``input ⊊ output`` --
    a different transformation family from pure palette-equality
    (permutation / identity) which the iter-184/185/186/187 cells
    alone cannot ringfence.
  * Symmetrically, iter 184 (output ⊆ input) fires on equality AND
    on erasure (input ⊋ output). The two cases differ on cardinality
    direction: equality has ``|output| == |input|``; erasure has
    ``|output| <  |input|``. This matcher (output count exceeds
    input count) is therefore *mutually exclusive* with iter 184 on
    any well-typed palette pair (a strict-expansion pair cannot
    simultaneously be an erasure or equality pair). The bidirectional
    axis ``|output| - |input| > 0`` vs ``< 0`` vs ``= 0`` is the
    cardinality-direction trichotomy on the same fields iter 184
    introduced; this matcher names the ``> 0`` cell.

Why this matters for ARBOR's intended ruleset:

  * Two canonical task families this gate ringfences strictly:
      - "strict palette-expansion" tasks where the output keeps every
        input colour AND adds at least one fresh colour. The
        conjunction (iter 187 AND this matcher) is the named
        precondition; iter 187 alone over-fires on equality /
        permutation cases.
      - "annotation / labelling overlay" tasks where the transformation
        layers fresh paint on top of the preserved input (e.g. a
        bordering colour, a marker colour). These are well-typed only
        when the output's cardinality exceeds the input's. iter 187
        alone does not name the "fresh colour added" precondition;
        this matcher does (it is *implied by* having at least one
        output colour outside the input palette).
  * For an abstract rule whose action adds new colour(s) -- e.g. a
    future ``coloring(grid, derived_selection, fresh_colour)`` whose
    ``fresh_colour`` is determined by the cardinality jump --
    requires the named cardinality-direction precondition. The
    matcher's name is what a rule's stored ``condition.type`` would
    declare to gate that action correctly.

Mutual containment / co-fire table (universal-over-pairs semantics):

  * Iter 13 (``identity_transformation``) -- output palette equals
    input palette per pair, so ``|output| == |input|`` per pair, so
    ``|output| > |input|`` is FALSE on every pair. STRICTLY mutually
    exclusive with this matcher (on the universal-over-pairs gate,
    identity ⇒ NOT this matcher).
  * Iter 184 (``output_palette_subset_of_input``) -- output ⊆ input
    means ``|output| <= |input|`` per pair, so ``|output| > |input|``
    is FALSE on every pair. STRICTLY mutually exclusive on
    well-typed (finite) palettes.
  * Iter 185 (``output_palette_equals_input``) -- equality means
    ``|output| == |input|``, so ``|output| > |input|`` is FALSE.
    STRICTLY mutually exclusive.
  * Iter 186 (``output_palette_disjoint_from_input``) -- disjoint
    palettes on non-empty input/output have ``|input ∩ output| == 0``;
    their cardinalities are independent. This matcher and iter 186
    CAN co-fire (e.g. canvas-rewrite where every output colour is
    fresh AND there are more output colours than input colours) AND
    can disagree (e.g. canvas-rewrite where the output has fewer
    distinct colours than the input). NOT in a refinement relation
    either direction.
  * Iter 187 (``input_palette_subset_of_output``) -- input ⊆ output
    is necessary but NOT sufficient for strict palette expansion. The
    two co-fire iff input ⊊ output (strict subset = subset AND
    cardinality strictly greater). iter 187 implies neither this
    matcher (palette equality fires iter 187 but not this) nor its
    negation (palette equality fires iter 187 and ``|output| ==
    |input|``). NOT in a refinement relation either direction; their
    *conjunction* is the strict-expansion handle.
  * Iter 14 (``input_color_uniform``) / iter 15
    (``output_color_uniform``) -- inspect the *changed cells'* source
    / target uniformity. Orthogonal to whole-grid palette cardinality
    direction.
  * Iter 8 (``consistent_color_mapping``) -- per-pair (C -> K) is a
    function on changed cells. Independent: a strict-palette-expansion
    task can be functional (each fresh colour determined) or not.
  * Every cell- / group- / position- / dimension- / shape-regularity
    matcher (iters 1 / 17 / 18 / 19 / 20 / 22 / 33 / 38 / 39 / 40 /
    41 / 42 / 182 / 183) is orthogonal to the whole-grid palette
    cardinality direction axis.

Why fail-closed on empty / malformed (same posture as iters 184 /
185 / 186 / 187): a missing or non-list palette is upstream extractor
breakage, not evidence the precondition holds. Universal-over-pairs
with a vacuously-true empty case would let an empty patterns dict
fire the gate, which is the wrong default.

Why strict-list-of-non-bool-ints (mirroring iters 184 / 185 / 186 /
187): Python bools are an ``int`` subclass; the iter-182 / 183 / 184
/ 185 / 186 / 187 dimensional / palette matchers all reject them to
keep the recognition layer from accepting placeholder sentinels.
Empty lists are admissible at the type level (the per-pair set will
have cardinality 0); the strict-inequality gate then rejects the
degenerate ``0 > 0`` case naturally.

Why the strict ``>`` rather than ``>=``: the ``>=`` direction is
already covered by iter 187 (input ⊆ output ⇒ ``|input| <= |output|``)
in the set-containment-aware form. The named transformation family
this matcher gates is "the output has STRICTLY more distinct
colours" -- the ``==`` case is iter-185 equality territory and a
different rule family (permutation / identity). The strictness is
load-bearing: a future strict-expansion rule needs to NOT fire on
equality cases.

Note on the empty-input-palette degenerate case: a pair whose input
palette is empty (zero-area input grid) and output palette is
non-empty trivially satisfies ``|output| > |input| == 0``. This
matcher will fire on that pair. The upstream extractor is responsible
for non-zero-area inputs; the matcher's posture is to honour what is
emitted rather than re-check upstream invariants (consistent with
iters 184 / 185 / 186 / 187 on the empty-palette edge cases).

Params:
  (none) -- pure per-pair cardinality comparison.

Returns True iff:
  - ``patterns`` is a dict, AND
  - ``patterns["pair_analyses"]`` is a non-empty list, AND
  - every analysis is a dict, AND
  - every analysis has an ``input_palette`` value that is a list of
    non-bool ints, AND
  - every analysis has an ``output_palette`` value with the same
    contract, AND
  - for every analysis: ``len(set(output_palette)) >
    len(set(input_palette))``.

No companion-touch required: iter 184 already emits ``input_palette``
and ``output_palette`` from ``_analyze_pair``; this iter is a pure
matcher addition with no ``agent/active_operators.py`` diff.
"""

from __future__ import annotations

from agent.conditions import register


def _is_palette_list(x) -> bool:
    """A palette field must be a list of non-bool ints. Empty is
    admissible at the type level (the cardinality gate handles the
    degenerate case)."""
    if not isinstance(x, list):
        return False
    for v in x:
        if not isinstance(v, int) or isinstance(v, bool):
            return False
    return True


@register("output_palette_count_exceeds_input_palette_count")
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
        if not (len(set(op)) > len(set(ip))):
            return False
    return True
