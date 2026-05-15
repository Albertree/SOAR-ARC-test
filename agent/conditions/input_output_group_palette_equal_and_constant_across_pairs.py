"""
input_output_group_palette_equal_and_constant_across_pairs -- match
tasks where there exists a single colour set S such that EVERY change
group of EVERY example pair has ``frozenset(group["input_colors"]) ==
frozenset(group["output_colors"]) == S``: a single canonical per-blob
palette, fixed across every change blob across every pair AND
identical between the input side and the output side of each blob.

Recognition vocabulary axis: the per-group projection of iter 991's
whole-grid ``input_output_palette_equal_and_constant_across_pairs``,
AND the natural conjunction-handle of iter 994
(``input_group_palette_constant_across_pairs``) AND iter 995
(``output_group_palette_constant_across_pairs``). This is the
strongest per-blob palette-stability gate ARBOR's current recognition
vocabulary can express, and it occupies the (per-group scope) x
(input AND output equality) cell of the (whole-grid, per-group) x
(input AND output equality) cross-pair-set-constancy recognition grid
-- the per-group dual of iter 991's whole-grid cell.

Why a separate conjunction-handle rather than re-running iter 994 AND
iter 995:

  * The matcher contract (``docs/RULE_FORMAT.md`` section 4) is
    name-keyed recognition vocabulary; the rule's stored
    ``condition.type`` is the recognition handle's name, not a
    name+params tuple. A future ``translate_to_schema`` emission
    branch (``agent/memory.py``) that needs the "per-blob input AND
    output palette together task-invariant" precondition would
    otherwise have to encode the three-way AND (iter 994 fires,
    iter 995 fires, per-group input set == per-group output set)
    inline in every gate. Naming the conjunction as a single registry
    entry lets the emission branch read a single ``condition.type``
    and lets stored rules carry the tightest single-name precondition
    rather than a multi-name conjunction the schema currently has no
    syntax to express (rule schema section 1 stores a single
    ``condition.type`` string).

  * This is the same conjunction-handle pattern iter 991 used for the
    whole-grid (input, output) palette equality, iter 992 used for
    the whole-grid (input, output) dimensional equality, iter 993
    used to AND iter 991 with iter 992, and iter 333 used when naming
    ``bijective_color_mapping`` as the conjunction of iter 8 AND iter
    332. The conjunction has new semantic content -- "the per-blob
    input set and per-blob output set are the SAME single canonical
    set across every blob of every pair" -- that neither named
    conjunct asserts on its own:

      - Iter 994 fires on tasks where every blob's input palette is
        the same canonical set S_in across pairs, but iter 994 says
        nothing about the per-blob output palette. A task with
        per-group input ``{0, 1}`` and per-group output ``{2, 3}``
        across all blobs fires iter 994 but NOT this matcher (the
        per-group input set differs from the per-group output set).

      - Iter 995 fires on tasks where every blob's output palette is
        the same canonical set S_out across pairs, but iter 995 says
        nothing about the per-blob input palette. A task with the
        symmetric pattern fires iter 995 but NOT this matcher.

      - Even both iter 994 AND iter 995 firing (S_in constant across
        all blobs AND S_out constant across all blobs) does NOT imply
        S_in == S_out: this matcher additionally requires that single
        shared input set equal that single shared output set, naming
        the strictly-stronger gate.

Why this matters for ARBOR's intended ruleset:

  * "Identity-on-vocabulary per-blob recolour" rule family: rules
    whose per-blob action preserves the palette (e.g. swap-within-
    palette, sort-within-palette, redistribute-within-palette). Anti-
    unification (CLAUDE.md section 8) needs this gate to safely lift
    a literal shared per-blob palette into a constant generalisation
    variable rather than two separate variables S_in and S_out.

  * For an abstract rule whose ``action`` references a single literal
    blob palette set from training (e.g. ``coloring(selection=blob,
    color=K)`` where K is drawn from a fixed set S that the rule
    knows holds on both the input AND the output side of every blob),
    this matcher is the minimal precondition under which that literal
    set is even meaningful for the test pair's blobs on both sides.

  * Co-firing with iter 991 (``input_output_palette_equal_and_constant_across_pairs``)
    is the tightest per-blob-AND-whole-grid input-AND-output palette
    stability gate: not only does every pair's whole-grid input AND
    output palette match the same canonical set, but every blob
    within every pair also draws its input AND output cells from that
    same set. The conjunction names a strictly tighter recogniser
    than either named conjunct alone.

  * For future emission branches in ``translate_to_schema``, the gate
    ``"input_output_group_palette_equal_and_constant_across_pairs"
    in fired`` is strictly tighter than either of iter 994 / 995
    individually -- and tighter than their two-of-two conjunction
    inlined into a branch, because this matcher also imposes the
    cross-side equality clause that the two-of-two conjunction alone
    does not.

Mutual containment / co-fire table (universal-over-pairs / -groups
semantics):

  * Iter 994 (``input_group_palette_constant_across_pairs``) -- input-
    side conjunct. STRICTLY IMPLIED. If this matcher fires with
    canonical S, then every group's input_colors set equals S, which
    is iter 994's claim. The converse FAILS: a task with per-group
    input ``{0, 1}`` and per-group output ``{2, 3}`` across all blobs
    fires iter 994 but not this matcher.

  * Iter 995 (``output_group_palette_constant_across_pairs``) --
    output-side conjunct. STRICTLY IMPLIED by the symmetric argument.
    Converse FAILS by the symmetric counterexample.

  * Iter 991 (``input_output_palette_equal_and_constant_across_pairs``)
    -- whole-grid scope conjunction-handle. NOT in a refinement
    relation either way:
      - This matcher fires, iter 991 rejects: every change blob has
        per-group input == output == ``{0, 1}`` across pairs, but the
        surrounding non-change background makes the whole-grid input
        and output palettes differ (e.g. pair 0 background ``{2}``,
        pair 1 background ``{3}``; whole-grid input/output palettes
        ``{0, 1, 2}`` and ``{0, 1, 3}`` differ -- iter 991 rejects,
        this matcher fires).
      - Iter 991 fires, this matcher rejects: whole-grid input ==
        output == ``{0, 1, 2}`` across both pairs, but pair 0 has a
        blob with per-group input ``{0, 1}`` output ``{0, 1}`` while
        pair 1 has a blob with per-group input ``{1, 2}`` output
        ``{1, 2}``. Whole-grid input/output palettes equal across
        pairs (iter 991 fires), but per-group sets differ across
        pairs (this matcher rejects).
    CAN co-fire on tasks where both scopes are stable.

  * Iter 989 (``input_palette_constant_across_pairs``) / iter 990
    (``output_palette_constant_across_pairs``) -- whole-grid single-
    axis cross-pair-set-constancy cells. INDEPENDENT (whole-grid vs
    per-group scope). NOT in a refinement relation either way.

  * Iter 993 (``input_output_dimensions_and_palette_equal_and_constant_across_pairs``)
    -- whole-grid AND'ed conjunction-of-conjunctions including iter
    991. INDEPENDENT (whole-grid scope; the dimension axis is
    orthogonal to per-group palette content).

  * Iter 195 (``change_input_color_count_per_group_constant_across_pairs``)
    -- per-group |input_colors| constancy. STRICTLY IMPLIED via iter
    994 (this matcher implies iter 994 which implies iter 195).

  * Iter 196 (``change_output_color_count_per_group_constant_across_pairs``)
    -- per-group |output_colors| constancy. STRICTLY IMPLIED via iter
    995.

  * Iter 35 (``change_input_colors_constant_across_pairs``) / iter 36
    (``change_output_colors_constant_across_pairs``) -- per-pair
    aggregated frozenset under the single-colour-blob constraint.
    NOT in a refinement relation either way (covered in iter 994 /
    995 docstrings; the same reasoning applies here).

  * Iter 14 (``input_color_uniform``) -- every group across every
    pair has ``len(input_colors) == 1`` with the SAME single colour
    C. STRICTLY IMPLIES this matcher iff iter 18
    (``output_color_uniform``) also fires with the SAME single colour
    C. Iter 14 alone does NOT imply this matcher (output side can
    differ); iter 18 alone does not either. The conjunction (iter
    14 AND iter 18 AND C_in == C_out) does strictly imply this
    matcher.

  * Iter 18 (``output_color_uniform``) -- symmetric to iter 14.

  * Iter 13 (``identity_transformation``) -- every pair has zero
    groups. This matcher REJECTS the no-group case (fail-closed
    clause below) to keep its territory disjoint from iter 13 by
    construction. Mirrors iter 32 / 35 / 36 / 37 / 39 / 193 / 195 /
    196 / 197 / 198 / 199 / 200 / 201 / 202 / 203 / 204 / 205 / 206 /
    207 / 208 / iter ``change_palette_union_count_per_group_constant_across_pairs``
    / iter 994 / iter 995 empty-group rejection.

  * Iter 207 / 208 / iter ``change_palette_union_count_per_group_constant_across_pairs``
    -- per-group derived intersection / symmetric-difference / union
    cardinality. CO-FIRES on tasks where input_colors == output_colors
    per-group (intersection cardinality == set cardinality, symmetric
    difference cardinality == 0, union cardinality == set cardinality)
    AND those derived cardinalities are constant across pairs. NOT in
    a refinement relation either way -- those matchers fire on tasks
    where intersection/symmetric-difference/union cardinalities are
    constant even though individual sets vary, which this matcher
    rejects.

  * Iter 8 (``consistent_color_mapping``) / iter 332
    (``inverse_consistent_color_mapping``) / iter 333
    (``bijective_color_mapping``) -- per-pair function shape on the
    (input -> output) mapping over changed cells. INDEPENDENT of
    set-equality content.

  * Iter ``output_colors_equals_input_colors_per_group`` -- asserts
    per-pair-per-group set equality but says nothing about cross-
    pair / cross-group constancy. This matcher additionally requires
    that single shared set be bit-identical across every blob across
    every pair (the strictly stronger gate).

  * Every dimensional / position / cell-count axis matcher (iters
    1 / 17 / 19 / 20 / 22 / 23 / 24 / 26 / 28 / 32 / 33 / 38 / 39 /
    40 / 41 / 42 / 182 / 183 / 991 / 992 / 993) -- orthogonal to per-
    group colour content.

Params:
  (none) -- pure existence/uniqueness check on the conjunction of the
  three semantic clauses (iter 994 firing, iter 995 firing, per-blob
  input set == per-blob output set). The detected canonical palette
  is data carried in a future rule's stored args, not in
  ``condition.params``.

Returns True iff:
  - ``patterns`` is a dict, AND
  - ``patterns["pair_analyses"]`` is a non-empty list, AND
  - every analysis is a dict, AND
  - every analysis has a non-empty ``groups`` list (identity-
    territory rejection), AND
  - every group is a dict with list-typed ``input_colors`` AND
    ``output_colors`` fields of length >= 1, AND
  - every entry of every group's ``input_colors`` / ``output_colors``
    is a strict int in ``range(10)`` (bool rejected per iter-13 / 14
    / ... / 207 / 208 / 994 / 995 strict-type posture), AND
  - for every group: ``frozenset(input_colors) == frozenset(output_colors)``,
    AND
  - that single shared per-group set is bit-identical across every
    group of every analysis.

Why strict-list-of-non-bool-ints-in-[0,9]: ARC colours are integers
in ``range(10)``; the matcher performs the same strict-type gating
as iter 14 / 18 / 19 / 34 / 35 / 36 / 37 / 38 / 184-208 / 994 / 995
to keep contract violations from silently passing.

Why fail-closed on empty / no-group: a patterns dict where every
pair has zero groups (the identity case) has empty per-group
collections that are vacuously equal across groups. Allowing that to
fire here would double-cover iter 13's ``identity_transformation``
territory under a name that promises "every blob shares a palette".
The strict refusal mirrors the standard per-group-matcher posture
(iter 195 / 196 / 197 / 200-208 / 994 / 995).

Why input_colors AND output_colors required non-empty per group: a
connected change group has at least one cell; that cell has an input
colour AND an output colour; the per-group fields are sorted non-empty
sets by the iter-1 extractor contract. A zero-length colour list is
an extractor contract violation, not a valid empty-set case.

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


@register("input_output_group_palette_equal_and_constant_across_pairs")
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
            input_colors = group.get("input_colors")
            output_colors = group.get("output_colors")
            if not _is_color_list(input_colors):
                return False
            if not _is_color_list(output_colors):
                return False
            ic_set = frozenset(input_colors)
            oc_set = frozenset(output_colors)
            if ic_set != oc_set:
                return False
            if canonical is None:
                canonical = ic_set
            elif canonical != ic_set:
                return False

    return canonical is not None
