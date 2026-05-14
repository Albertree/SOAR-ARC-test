"""
output_palette_subset_of_input -- match tasks where every example pair's
output grid uses only colours that ALREADY appear somewhere in its input
grid (no new colour is introduced by the transformation).

Recognition vocabulary axis: ``whole-grid colour palette`` -- the
intrinsic property "the transformation does not introduce a colour
that wasn't already present". None of the existing colour matchers
names this property:

  * Iter 8 (``consistent_color_mapping``) inspects the per-pair (input
    colour C -> output colour K) function on the *changed* cells. It
    is silent about whether K is in the input palette overall (K may
    or may not also appear elsewhere in the input).
  * Iters 14 / 15 (``input_color_uniform`` / ``output_color_uniform``)
    inspect whether the changed cells share a single source / target
    colour. Whole-grid palette membership is orthogonal.
  * Iters 34 / 35 / 36 (``change_*_colors_constant_across_pairs``)
    inspect cross-pair constancy of the changed-cells' colour set.
    Whole-grid palette membership is orthogonal.
  * Every other colour matcher (iters 38 / 39 / 42, the colour-count
    matchers) constrains the changed cells' colours. The whole-grid
    palette axis is genuinely new.

So palette-subset-on-the-output-side is a NEW axis. Two related slots
in the same axis live alongside this (deferred to future smallest-step
iters): ``output_palette_equals_input`` (strict equality -- recolour-
preserving) and ``output_palette_disjoint_from_input`` (every colour
on the output is fresh -- canvas-rewrite tasks).

Why this matters for the schema:

  * A rule whose action recolours existing cells (the most common ARC
    transformation family -- "paint the red cells blue", "swap red and
    green", a permutation on the active palette) is well-typed *only*
    when ``output_palette ⊆ input_palette`` holds across the training
    set. Naming the precondition makes the rule's stored gate
    representable: ``condition.type =
    "output_palette_subset_of_input"`` is the recognition handle the
    rule's stored precondition would declare. Recognition vocabulary
    ahead of emission, the iter 1/8/10/13/17/18/19/20/22/23/24/26/28/
    30/32/33/35/37/38/39/40/41/42/182/183 pattern.
  * For an abstract rule whose action is a colour permutation
    (``coloring(grid, [cells with input colour C], permutation[C])``),
    this matcher's gate is what distinguishes "permutation on the
    active palette" from "introduce a fresh colour" -- the same
    surface action shape under two very different semantics. Without
    a recognition handle for the distinction, anti-unification could
    not later lift two co-firing rules' permutations into a single
    abstraction.

Relation to existing matchers (mutual exclusion / co-fire table):

  * ``identity_transformation`` (iter 13) -- zero changed cells; the
    output palette is necessarily a subset (in fact, equal to) the
    input palette. So iter 13 STRICTLY IMPLIES this matcher. They
    co-fire on every identity task. The converse does not hold (a
    pure recolour where every red becomes blue fires this but not
    iter 13).
  * ``input_color_uniform`` (iter 14) -- the changed cells' source
    colour is uniform; says nothing about the whole-grid palette.
    Orthogonal.
  * ``output_color_uniform`` (iter 15) -- the changed cells' target
    colour is uniform; says nothing about whether that target lies
    inside the input palette. Orthogonal.
  * ``consistent_color_mapping`` (iter 8) -- per-pair (C -> K) is a
    function; this matcher constrains K's whole-grid membership.
    Orthogonal in general; co-fire when K happens to be in the input
    palette.
  * The cell- / group- / position- / dimension- / shape-regularity
    matchers (iters 1 / 17 / 18 / 19 / 20 / 22 / 33 / 38 / 39 / 40 /
    41 / 42 / 182 / 183) are all orthogonal to the whole-grid palette
    axis.

No co-fire is forced, no co-fire is forbidden -- this is a strictly
new axis whose membership is independent of every existing matcher's
gate except for iter 13's strict-implication relationship.

Params:
  (none) -- the matcher's contract is "every pair's output palette
  is a subset of its input palette". The matcher is a pure
  set-containment check; the specific palettes' contents are data
  carried in ``patterns["pair_analyses"][i]`` and never surface to
  the matcher's caller.

Returns True iff:
  - ``patterns`` is a dict, AND
  - ``patterns["pair_analyses"]`` is a non-empty list, AND
  - every analysis is a dict, AND
  - every analysis has an ``input_palette`` value that is a list of
    ints (bool rejected, same posture as the dimensional matchers),
    AND
  - every analysis has an ``output_palette`` value with the same
    contract, AND
  - for every analysis: ``set(output_palette) ⊆ set(input_palette)``.

Why per-pair ``input_palette`` / ``output_palette`` rather than a
top-level flag: same rationale as iters 17 / 20 / 22 / 33 / 182 / 183
-- matchers should not piggyback on derived top-level flags; reading
the per-pair scalar fields keeps the recognition layer's contract on
the shape ``_analyze_pair`` emits (since iter 184), not on a summary
the slow path may forget to compute.

Why strict-list-of-ints (not bool, ints in [0, 9] not enforced): a
missing or non-list palette is upstream extractor breakage, not
evidence that subset holds. We tolerate any int value in the list
(including the iter-180 erase sentinel ``13``) because the
``_analyze_pair`` emission is unfiltered -- gating on the ARC palette
[0, 9] would re-implement validation that belongs upstream.

Why fail-closed on empty pair_analyses, malformed list, etc.: the
matcher's contract is ``deterministic and side-effect-free``
(docs/RULE_FORMAT.md §4); a missing or non-list palette is upstream
extractor breakage, not evidence the precondition holds. The
universal-over-pairs semantic with a vacuously-true empty case would
let an empty patterns dict fire the gate, which is the wrong default.

Companion-touch under F8: this iter ALSO modifies ``_analyze_pair``
in ``agent/active_operators.py`` to emit the two new
``input_palette`` / ``output_palette`` fields the matcher reads. F8's
companion-touch gate is satisfied because ``agent/conditions/`` is
also touched (this file).
"""

from __future__ import annotations

from agent.conditions import register


def _is_palette_list(x) -> bool:
    """A palette field must be a list of non-bool ints. Empty is
    admissible (a zero-area grid would emit an empty palette; the
    upstream guard is at the extractor, not here)."""
    if not isinstance(x, list):
        return False
    for v in x:
        if not isinstance(v, int) or isinstance(v, bool):
            return False
    return True


@register("output_palette_subset_of_input")
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
        if not set(op).issubset(set(ip)):
            return False
    return True
