"""
output_group_palette_constant_across_pairs -- match tasks where EVERY
change group of EVERY example pair carries the same
``frozenset(group["output_colors"])``: a single canonical set of output
colours, fixed across every change blob across every pair.

Recognition vocabulary axis: the per-group projection of iter 990's
whole-grid ``output_palette_constant_across_pairs``, and the output-
side dual of iter 994's ``input_group_palette_constant_across_pairs``.
Where iter 990 asserts cross-pair set equality of the *whole-grid*
output palette, this matcher asserts cross-pair AND cross-group set
equality of the per-group *change-cell* output palette -- the colours
that the cells of each connected change blob become after the
transformation. The four cells of the (input, output) x (whole-grid,
per-group) cross-pair-set-constancy quadrant are now jointly named:
iter 989 (whole-grid input), iter 990 (whole-grid output), iter 994
(per-group input), this iter (per-group output).

Why a separate matcher rather than parameterising iter 994 or iter 990:

  * The matcher contract (``docs/RULE_FORMAT.md`` section 4) is
    name-keyed recognition vocabulary; the rule's stored
    ``condition.type`` is the recognition handle's name, not a
    name+params tuple. Each cell of the (whole-grid, per-group) x
    (input, output) x cross-pair-set-constancy recognition grid
    deserves its own handle, the same way iter 989 / 990 named the
    whole-grid (input / output) cells as separate slots from the
    derived-aggregate ``constant_across_pairs`` matchers, and iter
    994 named the per-group / input-side cell. The per-group /
    output-side cross-pair set-equality cell has had no named handle
    since iter 1 introduced ``group["output_colors"]``; this matcher
    names it.

  * Existing per-group ``constant_across_pairs`` matchers all target
    derived integer aggregates of the per-group output-colour list:
      - iter 196 (``change_output_color_count_per_group_constant_across_pairs``)
        names cross-pair constancy of ``len(output_colors)`` -- the
        cardinality, not the set itself. Two pairs with per-group
        ``output_colors`` of ``[0, 1]`` and ``[2, 3]`` both have
        cardinality 2 -- iter 196 fires, this matcher rejects.
      - iter 207 / 208 / iter ``change_palette_union_count_per_group_constant_across_pairs``
        name cross-pair constancy of derived intersection / symmetric-
        difference / union *cardinality* mixing input and output --
        all distinct fields, all cardinality not set.
    None of these assert per-group SET equality of the raw
    ``output_colors`` field across pairs. This matcher names that
    cell.

  * The per-pair ``change_output_colors_constant_across_pairs`` matcher
    (iter 36) projects each pair's per-group ``output_colors[0]``
    values into a per-pair frozenset and asserts cross-pair set
    equality of THAT projection. Iter 36 requires
    ``len(output_colors) == 1`` per group (single-colour blob); this
    matcher allows any size and asserts per-group set bit-identity
    across all groups in all pairs. The two are on different sub-axes
    (per-pair aggregation vs per-group set identity); INDEPENDENT in
    general -- see refinement-table entry below.

Why this matters for ARBOR's intended ruleset:

  * "Fixed-vocabulary per-blob recolour" rule family (output side):
    rules whose per-blob action assumes every output blob lands in
    the same fixed colour vocabulary (e.g. "every change blob in
    every pair has its cells rewritten to {2, 3} from whatever input
    they started as"). Anti-unification (CLAUDE.md section 8) needs
    this gate to safely lift a literal per-blob output palette into
    a constant generalisation variable rather than a per-pair /
    per-group variable.

  * For an abstract rule whose ``action`` references a literal blob-
    output-palette set from training (e.g.
    ``coloring(selection=blob_cells, color=K)`` where K is drawn
    from a literal set ``{C1, C2}``), this matcher is the minimal
    precondition under which that literal set is even meaningful
    for the test pair's blobs.

  * Co-firing with iter 990 (``output_palette_constant_across_pairs``)
    is the tightest per-blob-AND-whole-grid output-vocabulary
    stability gate: not only does every pair's whole-grid output
    palette match, but every blob within every pair targets the
    same subset of output colours. The conjunction names a tighter
    recogniser than either alone.

  * Co-firing with iter 994 (``input_group_palette_constant_across_pairs``)
    is the tightest per-blob input-AND-output vocabulary stability
    gate -- both sides of every change blob draw from a fixed
    palette across all training data. The conjunction is the
    minimal precondition stack for a per-blob recolour rule whose
    ``action.args`` literally encode both the source and destination
    colour sets from training.

Mutual containment / co-fire table (universal-over-pairs / -groups
semantics):

  * Iter 13 (``identity_transformation``) -- every pair has zero
    groups. This matcher REJECTS the no-group case (fail-closed
    clause below) to keep its territory disjoint from iter 13 by
    construction. Mirrors iter 32 / 35 / 36 / 37 / 39 / 193 / 195 /
    196 / 197 / 198 / 199 / 200 / 201 / 202 / 203 / 204 / 205 /
    206 / 207 / 208 / iter ``change_palette_union_count_per_group_constant_across_pairs``
    / iter 994 empty-group rejection.

  * Iter 990 (``output_palette_constant_across_pairs``) -- whole-grid
    projection. NOT in a refinement relation either way. A task can
    fire this matcher while iter 990 rejects (every change blob
    ends in outputs ``{0, 1}`` across pairs, but the surrounding
    non-change background varies: pair 0 background ``{2}``, pair 1
    background ``{3}``, so whole-grid output palettes ``{0, 1, 2}``
    and ``{0, 1, 3}`` differ -- iter 990 rejects, this matcher
    fires). Conversely a task can fire iter 990 while this matcher
    rejects (whole-grid output palette ``{0, 1, 2}`` across both
    pairs, but pair 0 has a blob with outputs ``{0, 1}`` while
    pair 1 has a blob with outputs ``{1, 2}`` -- both whole-grid
    sets equal ``{0, 1, 2}`` but per-group sets differ -- iter 990
    fires, this matcher rejects). CAN co-fire on tasks where both
    scopes are stable.

  * Iter 994 (``input_group_palette_constant_across_pairs``) --
    input-side per-group sibling. Orthogonal axis (input vs output);
    INDEPENDENT in both directions. CAN co-fire when both input and
    output per-blob palettes are pinned; either can fire alone.

  * Iter 196 (``change_output_color_count_per_group_constant_across_pairs``)
    -- per-group ``len(output_colors)`` constancy. Strict
    implication: this matcher implies iter 196 (equal sets have
    equal cardinality), the converse fails (constant cardinality
    with varying set: two blobs with outputs ``{0, 1}`` and
    ``{2, 3}`` both have size 2).

  * Iter 36 (``change_output_colors_constant_across_pairs``) -- per-
    pair aggregated frozenset of per-group ``output_colors[0]``
    values, requiring single-colour blobs (``len(output_colors) ==
    1``). NOT in a refinement relation either way:
      - this matcher with multi-colour blobs (``len(output_colors)
        >= 2``) rejects iter 36's single-colour-blob precondition --
        this matcher fires, iter 36 rejects.
      - iter 36 fires on multi-blob tasks where per-pair {blob
        outputs} sets match across pairs but the per-group identity
        of which blob has which colour varies: pair 0 has blobs
        {0}, {1}, {2}; pair 1 has blobs {1}, {0}, {2} -- per-pair
        sets {0, 1, 2} both equal, iter 36 fires; this matcher
        requires EVERY group to share the same set, but the
        canonical observed is {0} (first group of pair 0), and
        pair 1's first group has set {1} != {0} -- this matcher
        rejects.

  * Iter 18 (``output_color_uniform``) -- every group across every
    pair has ``len(output_colors) == 1`` with the SAME single
    colour C. Strict implication: iter 18 implies this matcher
    (a single shared singleton set {C} is bit-identical per group
    across pairs). Converse fails on multi-colour-blob cases or
    cardinality > 1.

  * Iter 14 (``input_color_uniform``) -- input-side dual of iter
    18. Independent of this matcher's output-side scope; INDEPENDENT.

  * Iter 207 (``change_palette_intersection_count_per_group_constant_across_pairs``)
    / iter 208 (``change_palette_symmetric_difference_count_per_group_constant_across_pairs``)
    / iter ``change_palette_union_count_per_group_constant_across_pairs``
    -- per-group derived cardinalities mixing input and output
    colours. Different fields (output vs derived); NOT in a
    refinement relation. CAN co-fire, CAN each fire alone.

  * Iter 35 (``change_input_colors_constant_across_pairs``) / iter
    195 (``change_input_color_count_per_group_constant_across_pairs``)
    -- input-side siblings. Independent of this matcher's output-
    side scope; INDEPENDENT.

  * Iter 989 (``input_palette_constant_across_pairs``) / iter 991 /
    iter 992 / iter 993 (whole-grid input palette / palette
    conjunction / dimensions conjunction / both conjunction) -- all
    whole-grid scope. NOT in a refinement relation with this per-
    group / output-side cell.

  * Iter 8 (``consistent_color_mapping``) / iter 332
    (``inverse_consistent_color_mapping``) / iter 333
    (``bijective_color_mapping``) -- per-pair function shape on the
    (input -> output) mapping over changed cells. INDEPENDENT.

  * Every dimensional / position / cell-count axis matcher
    (iters 1 / 17 / 19 / 20 / 22 / 23 / 24 / 26 / 28 / 32 / 33 /
    38 / 39 / 40 / 41 / 42 / 182 / 183 / 991 / 992 / 993) --
    orthogonal to per-group colour content.

Params:
  (none) -- pure cross-pair / cross-group SET-equality check on the
  per-group ``output_colors`` field. The detected canonical palette
  is data carried in a future rule's stored args, not in
  ``condition.params``.

Returns True iff:
  - ``patterns`` is a dict, AND
  - ``patterns["pair_analyses"]`` is a non-empty list, AND
  - every analysis is a dict, AND
  - every analysis has a non-empty ``groups`` list (identity-
    territory rejection), AND
  - every group is a dict with a list-typed ``output_colors`` field
    of length >= 1, AND
  - every entry of every group's ``output_colors`` is a strict int
    in ``range(10)`` (bool rejected per iter-13 / 14 / ... / 207 /
    208 / iter ``change_palette_union_count_per_group_constant_across_pairs``
    / iter 994 strict-type posture), AND
  - the ``frozenset(output_colors)`` is bit-identical for every
    group of every analysis (compared as frozensets so internal
    list order does not affect the verdict).

Why strict-list-of-non-bool-ints-in-[0,9]: ARC colours are integers
in ``range(10)``; the matcher performs the same strict-type gating
as iter 14 / 18 / 19 / 34 / 35 / 36 / 37 / 38 / 184-208 /
``change_palette_union_count_per_group_constant_across_pairs`` /
iter 994 to keep contract violations from silently passing.

Why fail-closed on empty / no-group: a patterns dict where every
pair has zero groups (the identity case) has empty per-group
collections that are vacuously equal across groups. Allowing that
to fire here would double-cover iter 13's ``identity_transformation``
territory under a name that promises "every blob shares an output
palette" -- but there are no blobs to pin. The strict refusal
mirrors the standard per-group-matcher posture (iter 195 / 196 /
197 / 200 / 201 / 202 / 203 / 204 / 205 / 206 / 207 / 208 / iter
``change_palette_union_count_per_group_constant_across_pairs`` /
iter 994).

Why ``output_colors`` required non-empty per group (``len >= 1``):
a connected change group has at least one cell; that cell has an
output colour; the per-group ``output_colors`` field is the sorted
non-empty set of those colours by the iter-1 extractor contract. A
zero-length colour list is an extractor contract violation, not a
valid empty-set case.

No companion-touch required: ``output_colors`` has been emitted
per group since iter 1 (``_analyze_pair`` in ``agent/active_operators.py``);
this iter is a pure matcher addition with no
``agent/active_operators.py`` diff. F8 inert.
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


@register("output_group_palette_constant_across_pairs")
def match(patterns: dict, params: dict) -> bool:
    if not isinstance(patterns, dict):
        return False
    pair_analyses = patterns.get("pair_analyses")
    if not isinstance(pair_analyses, list) or not pair_analyses:
        return False

    canonical: frozenset | None = None

    for analysis in pair_analyses:
        if not isinstance(analysis, dict):
            return False
        groups = analysis.get("groups")
        if not isinstance(groups, list) or not groups:
            return False
        for group in groups:
            if not isinstance(group, dict):
                return False
            output_colors = group.get("output_colors")
            if not _is_color_list(output_colors):
                return False
            current = frozenset(output_colors)
            if canonical is None:
                canonical = current
            elif canonical != current:
                return False

    return canonical is not None
