"""
input_palette_subset_of_output -- match tasks where every example
pair's input palette is fully preserved in its output palette: every
colour that appears in the input grid also appears somewhere in the
output grid. The transformation may *add* fresh colours but never
*erases* a colour from the active palette.

This is the symmetric *input-side* mirror of iter 184's
``output_palette_subset_of_input`` -- the next-gap slot explicitly
named in iter 186's next-gap note. Same whole-grid colour palette
axis opened by iter 184 and developed by iters 185 / 186; this iter
completes the symmetric four-cell partition by adding the dual of
iter 184's containment direction.

Why a distinct matcher rather than re-using iter 184 with swapped
fields:

  * The matcher contract (docs/RULE_FORMAT.md §4) is name-keyed
    recognition vocabulary; the rule's stored ``condition.type`` is
    the recognition handle's name, not a name+params tuple. Each
    direction of palette containment is a distinct precondition: the
    rule whose stored gate is "every input colour survives" reads
    differently from the rule whose stored gate is "no fresh colour
    is introduced", even though both are named "subset" set-
    theoretically.
  * Iter 184 (``output_palette_subset_of_input``) fires on rules
    whose action *erases* colours (drop a colour from the palette,
    e.g. "remove every red cell"). The dual rule -- whose action
    *adds* colours without erasing any (canvas-rewrite-with-overlay,
    foreground-paint, palette-expansion) -- is what *this* matcher's
    gate justifies. Anti-unification, when later co-firing two
    pair-specific programs that both preserve the input palette and
    add fresh paint, needs the input-side handle to gate the abstract
    rule on *exactly* the precondition that justifies it.

Recognition vocabulary axis: same ``whole-grid colour palette`` axis
opened by iter 184. The four slots now span the (input ⊆ output,
output ⊆ input) 2x2 partition:

  * ``output_palette_subset_of_input`` (iter 184) -- output ⊆ input
    only; fires on erasure / permutation / identity.
  * ``output_palette_equals_input`` (iter 185) -- both directions
    hold; fires on permutation and identity. Strictly stronger than
    either single-direction gate; equality ⇔ subset AND this matcher.
  * ``output_palette_disjoint_from_input`` (iter 186) -- the off-
    diagonal cell; output ∩ input = empty. Fires on canvas-rewrite
    / foreground-erase.
  * ``input_palette_subset_of_output`` (this iter, 187) -- input ⊆
    output only; fires on canvas-rewrite-with-overlay /
    palette-expansion / identity.

Why this matters for ARBOR's intended ruleset:

  * Two canonical task families this gate ringfences:
      - "canvas-rewrite-with-overlay" tasks where the input grid is
        preserved (every input colour still appears somewhere in the
        output) and additional output cells use fresh colours.
      - "palette-expansion" tasks where the output grid keeps every
        input colour and adds at least one fresh colour (e.g. a
        bordering / annotation / labelling layer painted in a new
        colour).
  * Both families are well-typed *only* when input_palette ⊆
    output_palette across the training set. Naming the precondition
    makes the rule's stored gate representable:
    ``condition.type = "input_palette_subset_of_output"`` is the
    recognition handle the rule's stored precondition would declare.
    Recognition vocabulary ahead of emission, the
    iter-1/8/10/13/17/18/19/20/22/23/24/26/28/30/32/33/35/37/38/39/
    40/41/42/182/183/184/185/186 pattern.

Mutual containment / co-fire table (universal-over-pairs semantics):

  * Iter 13 (``identity_transformation``) -- output palette equals
    input palette per pair, which implies input palette ⊆ output
    palette. Strict implication: identity ⇒ this matcher. The
    converse does not hold (a non-identity palette-expansion rule
    fires this matcher but not identity).
  * Iter 184 (``output_palette_subset_of_input``) -- the dual
    direction. The two single-direction gates co-fire iff both hold,
    i.e. output ⊆ input AND input ⊆ output ⇔ output == input ⇔
    iter 185 (equality) fires. On any palette where the two sides
    differ, exactly one of {iter 184, this matcher} fires (or
    neither -- partial overlap / disjoint).
  * Iter 185 (``output_palette_equals_input``) -- equality is the
    intersection of iter 184 and this matcher. Strict implication:
    equality ⇒ this matcher. The converse does not hold (palette-
    expansion fires this matcher but not equality).
  * Iter 186 (``output_palette_disjoint_from_input``) -- disjoint
    plus input ⊆ output ⇒ input ⊆ output AND input ∩ output =
    empty ⇒ input is empty. The two matchers co-fire only on
    degenerate zero-area-input cases.
  * Iter 14 (``input_color_uniform``) / iter 15
    (``output_color_uniform``) -- inspect the *changed cells'* source
    / target uniformity. Orthogonal to whole-grid palette containment.
  * Iter 8 (``consistent_color_mapping``) -- per-pair (C -> K) is a
    function on changed cells. A palette-expansion task where the
    expansion is functional (each fresh colour determined by where
    it appears) co-fires with this matcher; a pure-overlay task with
    no changed cells fires only iter 13.
  * Every cell- / group- / position- / dimension- / shape-regularity
    matcher (iters 1 / 17 / 18 / 19 / 20 / 22 / 33 / 38 / 39 / 40 /
    41 / 42 / 182 / 183) is orthogonal to the whole-grid palette
    containment axis.

Why a distinct matcher rather than ``params={"side": "input"}`` on
iter 184: the matcher contract (docs/RULE_FORMAT.md §4) is name-
keyed recognition vocabulary; the rule's stored ``condition.type`` is
the recognition handle's name, not a name+params tuple. Adding a
side-selector boolean param would entangle two distinct preconditions
under one registry slot, which the iter-34..42 family explicitly
avoided (separate matchers per axis projection).

Params:
  (none) -- pure set-subset check on per-pair palettes.

Returns True iff:
  - ``patterns`` is a dict, AND
  - ``patterns["pair_analyses"]`` is a non-empty list, AND
  - every analysis is a dict, AND
  - every analysis has an ``input_palette`` value that is a list of
    non-bool ints, AND
  - every analysis has an ``output_palette`` value with the same
    contract, AND
  - for every analysis: ``set(input_palette) <= set(output_palette)``.

Why fail-closed on empty / malformed (same posture as iters 184 /
185 / 186): a missing or non-list palette is upstream extractor
breakage, not evidence the precondition holds. Universal-over-pairs
with a vacuously-true empty case would let an empty patterns dict
fire the gate, which is the wrong default.

Why strict-list-of-non-bool-ints (mirroring iters 184 / 185 / 186):
Python bools are an ``int`` subclass; the iter-182 / 183 / 184 /
185 / 186 dimensional / palette matchers all reject them to keep the
recognition layer from accepting placeholder sentinels. Empty lists
are admissible (a zero-area grid would emit an empty palette; the
upstream guard is at the extractor, not here -- subset holds
vacuously when the input palette is empty).

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


@register("input_palette_subset_of_output")
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
        if not set(ip).issubset(set(op)):
            return False
    return True
