"""
output_palette_disjoint_from_input -- match tasks where every example
pair's output grid uses ONLY colours that do NOT appear in its input
grid. The transformation introduces a *fresh* palette on the output
side; nothing of the input's colour content survives into the output's
palette.

This is the β slot explicitly named in iter 184's next-gap note and
reiterated in iters 184 / 185 as the canonical dual axis to the iter
184 subset matcher and the iter 185 equality matcher. Three slots on
the same ``whole-grid colour palette`` axis:

  * ``output_palette_subset_of_input`` (iter 184) -- weak gate; fires
    on erasures, permutations, and identity. Names the precondition
    "no fresh colour is introduced".
  * ``output_palette_equals_input`` (iter 185) -- strict gate; fires
    on permutations and identity, but NOT on erasures. Names the
    precondition "the active palette is preserved as a set".
  * ``output_palette_disjoint_from_input`` (this iter, 186) -- the
    dual; fires iff every output colour is fresh (none of the input's
    colours appears on the output side). Names the precondition
    "every output colour is fresh".

Why a distinct matcher rather than parameterising subset / equality:

  * The matcher contract (docs/RULE_FORMAT.md §4) is name-keyed
    recognition vocabulary; the rule's stored ``condition.type`` is
    the recognition handle's name, not a name+params tuple.
  * Subset and disjoint are *mutually exclusive on non-empty output
    palettes* -- a single colour shared between input and output
    breaks disjoint, and a single colour outside the input palette
    breaks subset. Conflating them under one parameterised entry
    would entangle two distinct preconditions under one registry slot
    (the same anti-pattern the iter-34..42 family explicitly avoided
    with separate matchers per axis projection).
  * Anti-unification later, when co-firing two pair-specific programs
    that both rewrite the entire grid to a fresh canvas (a
    foreground-erase or background-blank task), needs a recognition
    handle to gate the abstract rule on *exactly* the precondition
    that justifies it. The disjoint matcher is that handle.

Why this matters for ARBOR's intended ruleset:

  * Two canonical task families this gate ringfences:
      - "canvas-rewrite" tasks (every output colour is fresh; the
        transformation rebuilds the grid from scratch, e.g. emit a
        single-colour canvas of a colour the input never showed).
      - "foreground-erase + relabel" tasks (every input colour is
        replaced by a colour that did not appear in the input).
  * Both families are well-typed *only* when output_palette ∩
    input_palette == empty across the training set. Naming the
    precondition makes the rule's stored gate representable:
    ``condition.type = "output_palette_disjoint_from_input"`` is the
    recognition handle the rule's stored precondition would declare.
    Recognition vocabulary ahead of emission, the
    iter-1/8/10/13/17/18/19/20/22/23/24/26/28/30/32/33/35/37/38/39/
    40/41/42/182/183/184/185 pattern.
  * For an abstract rule whose action is "rewrite every cell to a
    colour that wasn't in the input" (e.g.
    ``coloring(grid, ALL_CELLS, fresh_colour)``), this matcher's gate
    is what distinguishes "fresh-canvas" from "permutation on the
    active palette" -- a different transformation family entirely.

Mutual containment / co-fire table (universal-over-pairs semantics):

  * Iter 13 (``identity_transformation``) -- output palette equals
    input palette per pair, which is the OPPOSITE of disjoint.
    Strict implication: identity ⇒ NOT disjoint (whenever the input
    palette is non-empty). Identity and disjoint are mutually
    exclusive whenever input_palette is non-empty.
  * Iter 184 (``output_palette_subset_of_input``) -- subset of the
    input palette; this matcher requires every output colour to lie
    OUTSIDE the input palette. The two are mutually exclusive whenever
    the output palette is non-empty (a non-empty output palette cannot
    be simultaneously contained in and disjoint from the input
    palette).
  * Iter 185 (``output_palette_equals_input``) -- strict subset of
    subset; equality ⇒ subset, so equality and disjoint are mutually
    exclusive whenever the output palette is non-empty (transitively
    from iter 184).
  * Iter 14 (``input_color_uniform``) / iter 15
    (``output_color_uniform``) -- inspect the *changed cells'* source
    / target uniformity. Orthogonal to whole-grid palette disjointness.
  * Iter 8 (``consistent_color_mapping``) -- per-pair (C -> K) is a
    function on changed cells. A disjoint transformation (every K is
    fresh) co-fires with this matcher iff the per-pair mapping happens
    to be functional; the two axes intersect on "every input colour
    maps to a unique fresh output colour" tasks.
  * Every cell- / group- / position- / dimension- / shape-regularity
    matcher (iters 1 / 17 / 18 / 19 / 20 / 22 / 33 / 38 / 39 / 40 /
    41 / 42 / 182 / 183) is orthogonal to the whole-grid palette
    disjointness axis.

Params:
  (none) -- pure set-disjointness check on per-pair palettes.

Returns True iff:
  - ``patterns`` is a dict, AND
  - ``patterns["pair_analyses"]`` is a non-empty list, AND
  - every analysis is a dict, AND
  - every analysis has an ``input_palette`` value that is a list of
    non-bool ints, AND
  - every analysis has an ``output_palette`` value with the same
    contract, AND
  - for every analysis: ``set(output_palette) & set(input_palette) ==
    empty set``.

Why fail-closed on empty / malformed (same posture as iters 184 /
185): a missing or non-list palette is upstream extractor breakage,
not evidence the precondition holds. Universal-over-pairs with a
vacuously-true empty case would let an empty patterns dict fire the
gate, which is the wrong default.

Why strict-list-of-non-bool-ints (mirroring iters 184 / 185): Python
bools are an ``int`` subclass; the iter-182 / 183 / 184 / 185
dimensional / palette matchers all reject them to keep the
recognition layer from accepting placeholder sentinels. Empty lists
are admissible (a zero-area grid would emit an empty palette; the
upstream guard is at the extractor, not here -- set-disjointness
holds vacuously when either palette is empty).

Note on the empty-output-palette degenerate case: a pair whose output
palette is empty (a zero-area output grid) trivially satisfies
disjointness against any input palette. This is the same posture
iter 184 and iter 185 took on empty palettes -- the upstream
extractor is responsible for non-zero-area outputs, not this matcher.

No companion-touch required: iter 184 already emits ``input_palette``
and ``output_palette`` from ``_analyze_pair``; this iter is a pure
matcher addition with no ``agent/active_operators.py`` diff.
"""

from __future__ import annotations

from agent.conditions import register


def _is_palette_list(x) -> bool:
    """A palette field must be a list of non-bool ints. Empty is
    admissible (the upstream extractor is responsible for non-empty
    palettes on non-zero-area grids)."""
    if not isinstance(x, list):
        return False
    for v in x:
        if not isinstance(v, int) or isinstance(v, bool):
            return False
    return True


@register("output_palette_disjoint_from_input")
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
        if set(op) & set(ip):
            return False
    return True
