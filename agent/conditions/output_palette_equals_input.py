"""
output_palette_equals_input -- match tasks where every example pair's
output grid uses EXACTLY the same set of colours as its input grid
(no colour is added, no colour is removed; the transformation preserves
the active palette).

This is the strict-equality companion of iter 184's
``output_palette_subset_of_input`` -- the (α) slot explicitly named in
iter 184's next-gap note. Same axis (``whole-grid colour palette``),
strictly stronger precondition.

Why a distinct matcher rather than parameterising subset:

  * Subset is the precondition for any recolour rule that may *erase*
    colours (drop a colour from the palette, e.g. "remove every red
    cell"). It tolerates output-palette ⊂ input-palette.
  * Equality is the precondition for any colour-permutation rule that
    preserves the active palette (e.g. "swap red and green", "rotate
    the palette by one position"). The bijection forbids both addition
    AND removal -- ``output_palette == input_palette`` as sets.

Stored separately so that anti-unification, when later co-firing two
permutation-shaped pair-specific programs, has a recognition handle to
gate the abstract rule on *exactly* the precondition that justifies it.
The subset matcher alone would over-fire (it also fires on erasures);
the equality matcher under-fires erasures (the right behaviour for a
permutation-typed rule).

Recognition vocabulary axis: same ``whole-grid colour palette`` axis
opened by iter 184. The two related slots in the same axis are:

  * ``output_palette_subset_of_input`` (iter 184) -- weak gate; fires
    on erasures, permutations, and identity.
  * ``output_palette_equals_input`` (this iter, 185) -- strict gate;
    fires on permutations and identity, but NOT on erasures.
  * ``output_palette_disjoint_from_input`` (deferred, β slot from
    iter 184) -- the dual; fires on canvas-rewrite / foreground-erase
    tasks where every output colour is fresh.

Mutual containment / co-fire table (universal-over-pairs semantics):

  * Iter 13 (``identity_transformation``) -- zero changed cells; the
    output grid IS the input grid, so palettes are equal per pair.
    Strict implication: identity ⇒ equality. The converse does not
    hold (a pure permutation has changed cells but equal palettes).
  * Iter 184 (``output_palette_subset_of_input``) -- weak gate.
    Strict implication: equality ⇒ subset. The converse does not
    hold (erasures fire subset but not equality).
  * Iter 14 (``input_color_uniform``) / iter 15
    (``output_color_uniform``) -- inspect the changed cells' source /
    target uniformity. Orthogonal to whole-grid palette equality.
  * Iter 8 (``consistent_color_mapping``) -- per-pair (C -> K) is a
    function on changed cells. A permutation on the active palette
    co-fires with this matcher; an erasure to a colour outside the
    palette would NOT co-fire (consistent mapping allows any K). The
    two axes intersect on permutations.
  * Every cell- / group- / position- / dimension- / shape-regularity
    matcher (iters 1 / 17 / 18 / 19 / 20 / 22 / 33 / 38 / 39 / 40 /
    41 / 42 / 182 / 183) is orthogonal to the whole-grid palette
    equality axis.

Why a distinct matcher rather than ``params={"strict": True}`` on
iter 184: the matcher contract (docs/RULE_FORMAT.md §4) is name-keyed
recognition vocabulary; the rule's stored ``condition.type`` is the
recognition handle's name, not a name+params tuple. Adding a strict-
mode boolean param would entangle two distinct preconditions under one
registry slot, which the iter-34..42 family explicitly avoided
(separate matchers per axis projection).

Params:
  (none) -- pure set-equality check on per-pair palettes.

Returns True iff:
  - ``patterns`` is a dict, AND
  - ``patterns["pair_analyses"]`` is a non-empty list, AND
  - every analysis is a dict, AND
  - every analysis has an ``input_palette`` value that is a list of
    non-bool ints, AND
  - every analysis has an ``output_palette`` value with the same
    contract, AND
  - for every analysis: ``set(output_palette) == set(input_palette)``.

Why fail-closed on empty / malformed (same posture as iter 184): a
missing or non-list palette is upstream extractor breakage, not
evidence the precondition holds. Universal-over-pairs with a
vacuously-true empty case would let an empty patterns dict fire the
gate, which is the wrong default.

Why strict-list-of-non-bool-ints (mirroring iter 184): Python bools
are an ``int`` subclass; the iter-182 / 183 / 184 dimensional /
palette matchers all reject them to keep the recognition layer from
accepting placeholder sentinels. Empty lists are admissible (a
zero-area grid would emit an empty palette; the upstream guard is at
the extractor, not here -- set-equality holds vacuously when both
palettes are empty).

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


@register("output_palette_equals_input")
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
        if set(op) != set(ip):
            return False
    return True
