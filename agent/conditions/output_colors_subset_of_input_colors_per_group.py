"""
output_colors_subset_of_input_colors_per_group -- match tasks where
EVERY change group of EVERY example pair satisfies
``set(group["output_colors"]) <= set(group["input_colors"])``: no
group introduces a colour on its output side that isn't already
present somewhere on its own input side.

Recognition vocabulary axis: per-group projection of iter 184
(``output_palette_subset_of_input``), which checks the WHOLE-GRID
output palette is a subset of the WHOLE-GRID input palette per pair.
Iter 184 collapses every pair's two grids into two palettes and
demands ``set(output_palette) <= set(input_palette)``; this matcher
demands the analogous subset relation HOLDS PER BLOB. The two
projections decouple:

  * Iter 184 fires while this matcher rejects: pair 0 has two groups,
    group A with input_colors=[1] / output_colors=[2], group B with
    input_colors=[2] / output_colors=[1]. The whole-grid output
    palette is {1, 2} which is a subset of the whole-grid input
    palette {1, 2}; iter 184 fires. But group A's output colour 2 is
    NOT in group A's input colour set {1}; this matcher rejects.
  * This matcher fires while iter 184 fires by construction:
    per-group subset universal-over-groups implies the per-pair
    UNION of group output palettes is a subset of the per-pair UNION
    of group input palettes (subset is preserved under union); the
    per-pair UNION of group input palettes is itself a subset of the
    whole-grid input palette. With ``output_palette`` defined as the
    set of colours present in the output grid -- a superset of the
    union of group output palettes (output may also contain unchanged
    pixels) -- the implication does NOT hold in general: a pair
    where every changed-group output is a subset of its own input
    but the output grid happens to introduce a fresh whole-grid
    colour somewhere else would fire this matcher and reject iter
    184. Iter 184 inspects the whole grid; this matcher inspects only
    the change groups. The two projections are INDEPENDENT in both
    directions.

Strict refinement / orthogonality summary (universal-over-groups-and-
pairs semantics):

  * Iter 13 (``identity_transformation``) -- every pair has zero
    change groups. This matcher REJECTS the no-group case (fail-
    closed clause below) to keep its territory disjoint from iter 13
    by construction. Mirrors iter 32 / 35 / 37 / 39 / 193 / 195 /
    196 / 197 / 198 / 199 empty-group rejection.
  * Iter 14 (``input_color_uniform``) -- pins every group's
    ``input_colors`` to a single colour AND that colour identical
    across all groups in all pairs. Independent of subset relation:
    with single-colour input groups, the subset claim reduces to
    "every group's output_colors is contained in a one-element set",
    i.e. every group's output is the same single colour. iter 14
    does NOT pin this; CAN co-fire when the output happens to be the
    same single colour as the input on every group.
  * Iter 18 (``output_color_uniform``) -- pins every group's
    ``output_colors`` to a single colour AND that colour identical
    across all groups in all pairs. Independent in general; CAN co-
    fire when every group's output single-colour is also one of its
    input colours.
  * Iter 184 (``output_palette_subset_of_input``) -- whole-grid
    output palette subset of whole-grid input palette per pair.
    INDEPENDENT in both directions (see paragraph above).
  * Iter 185 (``output_palette_equals_input``) -- strict equality at
    the whole-grid scope. INDEPENDENT of per-group subset relation.
  * Iter 195 / 196 / 197 -- per-group cardinality matchers on
    input / output / product. NOT in a refinement relation; CAN co-
    fire on patterns where both pin.
  * Iter 194 / 198 / 199 -- colour-translation sub-axis. INDEPENDENT
    in general; a translation by k != 0 has output disjoint from
    input per group (this matcher rejects k != 0 translations) so
    co-fire only when k == 0 globally / per-pair / per-group (which
    is iter 185's k==0 cell at the corresponding scope).
  * Iter 35 / 36 (``change_input_colors_constant_across_pairs`` /
    ``change_output_colors_constant_across_pairs``) -- per-pair
    input / output colour SET bit-identity. Independent.
  * Iter 8 (``consistent_color_mapping``) -- per-pair (C -> K) is a
    function on changed cells. INDEPENDENT in general; this matcher
    constrains where K lives (in the group's input set), iter 8
    constrains how C maps. CAN co-fire when K happens to be in the
    input set for every (C, K) the function maps.
  * Every cell- / position- / dimension-axis matcher (iters 1 / 17 /
    19 / 20 / 22 / 23 / 24 / 26 / 28 / 32 / 33 / 38 / 39 / 40 / 41 /
    42 / 182 / 183) -- orthogonal to per-group palette content.

Why this matters for ARBOR's intended ruleset:

  * "Per-blob recolour confined to the blob's own input palette"
    rule family -- rules whose action recolours cells within a
    change group using only colours that already appear in that
    group's input cells (a per-blob permutation on the blob's active
    palette). Iter 184's whole-grid version cannot distinguish
    "every blob recolours from its own palette" from "some blob
    introduces a fresh colour that happens to already exist somewhere
    else in the input grid"; this matcher names the strictly stronger
    per-blob version that is the precondition for per-blob permutation
    rules. Anti-unification (CLAUDE.md section 8) would attach a
    per-group permutation generalisation variable to this matcher's
    fired-gate.
  * Opens the per-group palette-relation sub-axis named in iter
    199's next-gap. The output_colors_equals_input_colors_per_group
    matcher (the iter 185 per-group projection) would sit alongside
    this matcher as the equality cell on the same sub-axis; the
    input_colors_subset_of_output_colors_per_group matcher (the
    iter 187 per-group projection) would sit alongside as the dual.

Params:
  (none) -- pure per-group subset check, universal over groups and
  pairs.

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
    ... / 195 / 196 / 197 / 198 / 199 strict-type posture), AND
  - for every group, ``set(output_colors) <= set(input_colors)``.

Why fail-closed on empty / no-group / malformed (same posture as
iters 14 / 30 / 32 / 33 / 34 / 35 / 36 / 37 / 38 / 39 / 184-199): a
missing or zero-group pair is upstream extractor breakage or
identity-territory; a subset claim with zero observations would
double-cover iter 13.

Why ``input_colors`` and ``output_colors`` both required non-empty
lists per group (``len >= 1``): a connected change group has at
least one cell; each cell has both an input colour and an output
colour; the per-group ``input_colors`` / ``output_colors`` fields
are the sorted sets of those colours, which are non-empty for any
non-empty group. A zero-length colour list is an extractor contract
violation, not a valid empty-set subset case.

Why strict per-colour validation (bool rejected, range checked):
``input_colors`` / ``output_colors`` carry small ints in [0, 9]; the
matcher performs the same strict-type gating as iter 14 / 18 / 19 /
34 / 35 / 36 / 37 / 38 / 184-199 to keep contract violations from
silently passing.

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


@register("output_colors_subset_of_input_colors_per_group")
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
            if not set(output_colors).issubset(set(input_colors)):
                return False
    return True
