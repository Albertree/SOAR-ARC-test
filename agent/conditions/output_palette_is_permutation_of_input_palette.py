"""
output_palette_is_permutation_of_input_palette -- match tasks whose
whole-grid output palette is a *permutation* of the whole-grid input
palette: every pair preserves the palette as a set (iter 185 condition)
AND the accumulated changed-cell colour mapping is a BIJECTION (iter 8
condition AND its strict refinement: injectivity).

Recognition vocabulary axis: iter 329's "Next gap" candidate (ii) -- the
whole-grid OUTPUT-PALETTE-IS-A-PERMUTATION-OF-INPUT-PALETTE matcher,
"refining iter 185 + iter 8 by adding INJECTIVITY of the
consistent_color_mapping". Injectivity is a genuinely fresh axis: no
existing matcher inspects the *inverse* relation of the changed-cell
colour mapping. The named handle is the precondition for the rule
family that anti-unification (CLAUDE.md section 8) would identify as
"palette permutation" (e.g. colour-swap, colour-cycle, palette-rotation).

Why this matters for ARBOR's intended ruleset
---------------------------------------------

The "palette permutation" rule family -- rules whose action is the
application of a fixed bijection ``pi : palette -> palette`` to every
cell of the input grid. ARC tasks that fit this shape include simple
colour-swap puzzles (every red <-> every blue, with all other colours
untouched), three-cycle puzzles (red -> green -> blue -> red), and any
permutation thereof. Anti-unification, presented with two pair-specific
``coloring``-based programs that each encode a different cycle of the
same bijection across distinct change groups, would generalise to a
single abstract rule parameterised by the permutation itself -- and the
condition gate for that abstract rule must be the precondition that
PERMITS such a bijection: palette preserved (set-equality per pair) AND
the changed-cell mapping admits an inverse (injective).

Why a distinct matcher rather than co-firing iter 185 with iter 8
-----------------------------------------------------------------

The (iter 185 AND iter 8) co-fire set is STRICTLY LARGER than the
permutation cell. A task where two distinct input colours within change
groups both map to the SAME output colour (a "merge" or "collapse"
recolour) co-fires iter 185 (palette equal on the WHOLE grid via
unchanged cells) and iter 8 (every input colour has one output target
-- function-shape holds), but is NOT a palette permutation -- the
mapping is non-injective, so no inverse exists, so no single bijection
on the palette can describe the rule. The injectivity refinement is
the strict gate that excludes such collapse-recolour tasks.

Equivalently, on the (iter 185 AND iter 8) co-fire domain:
  * Injectivity holds -> palette permutation (this matcher fires).
  * Injectivity fails -> palette-preserving merge / collapse recolour
    (this matcher REJECTS).

The two cells partition the (iter 185 AND iter 8) co-fire territory,
mirroring how iters 200-205 partition the per-group palette-relation
universe.

Why a distinct matcher rather than ``params={"injective": True}`` on
iter 8: the matcher contract (docs/RULE_FORMAT.md section 4) is
name-keyed recognition vocabulary; the rule's stored ``condition.type``
is the recognition handle's name, not a name+params tuple. Adding a
strict-mode boolean param would entangle two distinct preconditions
under one registry slot, which the iters 184-205 / 329 families
explicitly avoided.

Strict refinement / orthogonality summary (per-pair palette-equality
gate, plus cross-pair bijection check on accumulated change-group
observations):

  * Iter 8 (``consistent_color_mapping``) -- function-shape on changed-
    cell mapping. STRICT IMPLICATION: this matcher implies iter 8 (a
    bijection IS a function; the converse does not hold -- a
    non-injective function fires iter 8 but rejects this matcher).
  * Iter 185 (``output_palette_equals_input``) -- whole-grid palette
    equality. STRICT IMPLICATION: this matcher implies iter 185 (the
    permutation precondition includes per-pair palette equality; the
    converse does not hold -- a task with palette equal per pair but
    no changes, or with a non-injective change mapping, fires iter 185
    and rejects this matcher).
  * Iter 13 (``identity_transformation``) -- zero changed cells per
    pair. STRICTLY MUTUALLY EXCLUSIVE: identity has no observations,
    so the accumulated colour mapping is empty, so this matcher
    REJECTS (matching iter 8's empty-evidence rejection). Identity
    fires iter 185 but not this matcher -- the asymmetry that motivates
    permutation as a distinct handle from palette-equal.
  * Iter 184 (``output_palette_subset_of_input``) -- weak whole-grid
    gate. STRICT IMPLICATION: this matcher implies iter 184 (palette
    equality implies subset, and permutation implies palette equality).
  * Iter 186 (``output_palette_disjoint_from_input``) -- canvas-rewrite
    territory. STRICTLY MUTUALLY EXCLUSIVE: per-pair palette equality
    requires non-empty intersection (when palettes are non-empty), but
    disjointness requires empty intersection. On non-empty-palette
    inputs the two matchers cannot co-fire.
  * Iter 14 (``input_color_uniform``) / iter 18
    (``output_color_uniform``) -- pin changed-cell sides to a single
    colour. INDEPENDENT in general: a 2-cycle (red <-> blue) fires
    neither (input colours differ across cells); a 1-cycle plus other
    fixed points has changed cells all sharing one input colour but
    output colour also one -- co-fires both.
  * Iter 329 (``change_palette_intersection_nonempty_per_group``) --
    per-group anchor-preservation. INDEPENDENT: a 2-cycle that
    rewrites every cell in each blob (no anchor preserved per blob)
    REJECTS iter 329 but fires this matcher; an anchored recolour
    where one input colour stays and another shifts WITHIN A BLOB
    fires iter 329 but typically rejects this matcher (the mapping is
    not bijective across the task because the anchor colour appears
    on both sides of the per-group mapping without a reciprocal).
  * Every cell- / position- / dimension- / shape-regularity matcher
    (iters 1 / 17 / 19 / 20 / 22 / 28 / 33 / 38 / 39 / 40 / 41 / 42 /
    182 / 183) -- orthogonal to the colour-bijection axis.

Params:
  (none) -- pure gate: per-pair set-equality on palettes plus
  accumulated bijection check on change-group observations.

Returns True iff:
  - ``patterns`` is a dict, AND
  - ``patterns["pair_analyses"]`` is a non-empty list, AND
  - every analysis is a dict, AND
  - every analysis has an ``input_palette`` value that is a list of
    non-bool ints, AND
  - every analysis has an ``output_palette`` value with the same
    contract, AND
  - for every analysis: ``set(output_palette) == set(input_palette)``
    (iter 185 condition), AND
  - the accumulated ``input_color -> output_color`` relation across
    all change groups of all pairs is NON-EMPTY (iter 8 evidence
    requirement), AND
  - every observed input colour maps to EXACTLY ONE output colour
    (iter 8 function condition), AND
  - every observed output colour is mapped from EXACTLY ONE input
    colour (the INJECTIVITY refinement, the new axis).

Why fail-closed on empty / malformed (mirroring iters 8 / 184 / 185 /
329 postures): a missing or zero-pair / zero-group / non-list field
is upstream extractor breakage; a vacuously-true empty-evidence claim
would double-cover iter 13's identity territory.

Why strict-list-of-non-bool-ints (mirroring iter 185 palette gate +
iter 329 colour-list gate): Python bools are an ``int`` subclass; the
strict-type posture rejects them to keep the recognition layer from
accepting placeholder sentinels.

No companion-touch required: ``input_palette`` / ``output_palette``
(iter 184) and ``input_colors`` / ``output_colors`` (iter 1) have
been emitted from ``_analyze_pair`` since their respective iters;
this iter is a pure matcher addition with no
``agent/active_operators.py`` diff. F8 inert.
"""

from __future__ import annotations

from agent.conditions import register


def _is_palette_list(x) -> bool:
    """A whole-grid palette field must be a list of non-bool ints.
    Empty is admissible (mirrors iter 185's posture on zero-area grids
    -- the upstream extractor is responsible for non-empty palettes on
    non-zero-area inputs)."""
    if not isinstance(x, list):
        return False
    for v in x:
        if not isinstance(v, int) or isinstance(v, bool):
            return False
    return True


def _is_strict_color(x) -> bool:
    return (
        isinstance(x, int)
        and not isinstance(x, bool)
        and 0 <= x <= 9
    )


def _is_color_list(x) -> bool:
    """A per-group change-cell colour list must be a non-empty list of
    strict 0..9 ints (mirrors iter 329's strict-type posture; a change
    group with zero colours on either side is upstream breakage)."""
    if not isinstance(x, list) or len(x) < 1:
        return False
    for v in x:
        if not _is_strict_color(v):
            return False
    return True


@register("output_palette_is_permutation_of_input_palette")
def match(patterns: dict, params: dict) -> bool:
    if not isinstance(patterns, dict):
        return False
    pair_analyses = patterns.get("pair_analyses")
    if not isinstance(pair_analyses, list) or not pair_analyses:
        return False

    forward: dict = {}
    inverse: dict = {}

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

        groups = analysis.get("groups")
        if not isinstance(groups, list):
            return False
        for g in groups:
            if not isinstance(g, dict):
                return False
            input_colors = g.get("input_colors")
            output_colors = g.get("output_colors")
            if not _is_color_list(input_colors):
                return False
            if not _is_color_list(output_colors):
                return False
            for ic in input_colors:
                for oc in output_colors:
                    forward.setdefault(ic, set()).add(oc)
                    inverse.setdefault(oc, set()).add(ic)

    if not forward:
        return False
    if not all(len(v) == 1 for v in forward.values()):
        return False
    if not all(len(v) == 1 for v in inverse.values()):
        return False
    return True
