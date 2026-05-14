"""
change_palette_intersection_nonempty_per_group -- match tasks where
EVERY change group of EVERY example pair satisfies
``set(group["input_colors"]) & set(group["output_colors"]) != empty
set``: some colour appears in both the input side and the output side
of every change group. The strict complement of iter 203
(``output_colors_disjoint_from_input_colors_per_group``) on the
non-empty-per-group-palette domain.

Recognition vocabulary axis: the iter-228 named "Next gap" candidate
(iii) -- the per-group BACKGROUND-COLOUR-PRESERVED matcher, named as
"per-group input intersect output non-empty, the precondition for
anchor-preserving rules". Where iter 203 names the strictly-fresh
recolour cell (every group's output palette is entirely new, no
colour is preserved within the blob), this matcher names the
strictly-anchored cell -- at least one colour of every group's input
appears in that group's own output. The two are exact partitioners of
the non-empty-per-group-palette domain on the per-group
input-output intersection axis.

Why this matters for ARBOR's intended ruleset
---------------------------------------------

The "anchor-preserving" rule family -- rules whose action recolours
SOME (but not all) cells of a change group, leaving at least one
input colour intact within the blob. Iter 203 names its dual (per-
blob canvas-rewrite / fresh recolour where every output colour is
new); this matcher names the precondition for the rule family where
each blob retains an anchor colour while introducing one or more new
colours alongside. Anti-unification (CLAUDE.md section 8) would
attach a per-group anchor-preservation generalisation variable to
this matcher's fired gate.

Relation to the iter 200-203 per-group palette-relation partition
-----------------------------------------------------------------

Iters 200 / 201 / 202 / 203 plus iter 200's "Next gap" partial-overlap
matcher partition the universe of per-group palette-relation patterns
(on the cell-count-non-empty domain) into five disjoint cells:

  * Iter 201 -- per-group EQUALITY: input == output per group.
  * Iter 204 -- per-group STRICT ERASURE: output proper subset of input.
  * Iter 205 -- per-group STRICT EXPANSION: input proper subset of output.
  * Iter 203 -- per-group DISJOINT: input intersect output empty.
  * Partial-overlap -- non-empty intersection AND neither side contains
    the other (named separately).

This matcher's territory is the UNION of {equality, strict-erasure,
strict-expansion, partial-overlap} -- the four cells whose per-group
input-output intersection is non-empty. Equivalently, the STRICT
COMPLEMENT of iter 203 on the non-empty-per-group-palette domain.

  * Co-fires with iter 201 / 204 / 205 / partial-overlap -- the four
    non-disjoint cells of the per-group palette-relation partition.
  * STRICTLY MUTUALLY EXCLUSIVE with iter 203 on the non-empty-per-
    group-palette domain. Both matchers require non-empty per-group
    input and output palettes; under that domain, intersection is
    either empty (iter 203) or non-empty (this matcher), never both.

Distinct semantic handle vs the bare complement
-----------------------------------------------

While the truth value coincides with "NOT iter 203" on the non-empty-
per-group-palette domain, this matcher's purpose is to NAME the
anchor-preservation precondition as its own recognition handle. A
rule's stored ``condition.type`` is a name, not a negation expression
(docs/RULE_FORMAT.md section 4); for anti-unification to lift an
anchor-preservation variable onto a rule's gate, the gate must have
a positive recognition name to attach to. The same rationale iters
185 / 186 / 187 followed when naming whole-grid palette equality,
disjointness, and dual-subset as three separate matchers rather than
encoding two of them as negations of the first.

Strict refinement / orthogonality summary (universal-over-groups-and-
pairs semantics):

  * Iter 13 (``identity_transformation``) -- zero change groups per
    pair. STRICTLY MUTUALLY EXCLUSIVE -- this matcher REJECTS the
    no-group case (fail-closed clause below). Mirrors iter 203 / 200
    / 201 / 202 empty-group rejection.
  * Iter 201 (``output_colors_equals_input_colors_per_group``) --
    per-group equality. STRICTLY IMPLIES this matcher (equal non-
    empty sets have non-empty intersection).
  * Iter 204 (``output_colors_proper_subset_of_input_colors_per_group``)
    -- per-group strict erasure. STRICTLY IMPLIES this matcher
    (proper subset on non-empty sides has non-empty intersection).
  * Iter 205 (``input_colors_proper_subset_of_output_colors_per_group``)
    -- per-group strict expansion. STRICTLY IMPLIES this matcher.
  * Iter 203 (``output_colors_disjoint_from_input_colors_per_group``)
    -- per-group disjointness. STRICTLY MUTUALLY EXCLUSIVE.
  * Iters 200 (``output_colors_subset_of_input_colors_per_group``),
    202 (``input_colors_subset_of_output_colors_per_group``) -- the
    non-strict per-group subset predicates. STRICTLY IMPLIES this
    matcher on the non-empty-per-group-palette domain (any non-empty
    side that's a subset of the other gives non-empty intersection).
  * Iter 186 (``output_palette_disjoint_from_input``) -- whole-grid
    disjointness. INDEPENDENT: a per-blob colour swap has both whole-
    grid palettes equal AND per-group intersection non-empty within
    the swap blobs; a per-blob canvas-rewrite where the unchanged
    background is shared makes whole-grid palettes intersect on
    background but per-group palettes disjoint within blobs.
  * Iter 185 (``output_palette_equals_input``) -- whole-grid equality.
    INDEPENDENT: a per-blob non-anchored recolour can fire this matcher
    rejecting (groups disjoint) while iter 185 fires via background
    bleed-through; a per-blob anchored recolour can fire this matcher
    while iter 185 rejects (background palette differs).
  * Iter 14 (``input_color_uniform``) / iter 18
    (``output_color_uniform``) -- pin the changed-cell sides to a
    single colour and that colour identical across groups. INDEPENDENT
    of intersection nonempty in general; co-fire when the uniform
    input colour equals the uniform output colour (but iter 13's
    territory takes that over), or when iter 14 fires alone with
    distinct uniform output colour per group (still anchored if the
    input colour appears elsewhere in the group's output).
  * Iter 8 (``consistent_color_mapping``) -- per-pair (C -> K) is a
    function on changed cells. INDEPENDENT: a non-anchored consistent
    recolour fires iter 8 and rejects this matcher; an anchored
    consistent recolour fires both.
  * Every cell- / position- / dimension-axis matcher (iters 1 / 17 /
    19 / 20 / 22 / 23 / 24 / 26 / 28 / 32 / 33 / 38 / 39 / 40 / 41 /
    42 / 182 / 183) -- orthogonal to per-group palette content.

Params:
  (none) -- pure per-group intersection-nonempty check, universal
  over groups and pairs.

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
    ... / 200-205 strict-type posture), AND
  - for every group, ``set(input_colors) & set(output_colors)`` is
    NON-EMPTY.

Why fail-closed on empty / no-group / malformed (same posture as
iters 13 / 14 / 30 / 32 / 33 / 34 / 35 / 36 / 37 / 38 / 39 / 184-205):
a missing or zero-group pair is upstream extractor breakage or
identity-territory; an anchor-preservation claim with zero
observations would double-cover iter 13.

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


@register("change_palette_intersection_nonempty_per_group")
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
            if not (set(input_colors) & set(output_colors)):
                return False
    return True
