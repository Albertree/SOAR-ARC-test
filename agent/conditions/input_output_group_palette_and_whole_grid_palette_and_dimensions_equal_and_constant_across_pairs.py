"""
input_output_group_palette_and_whole_grid_palette_and_dimensions_equal_and_constant_across_pairs
-- match tasks where there exists a single (H, W) tuple AND a single
whole-grid colour set S_whole AND a single per-blob colour set S_blob
such that

  * EVERY pair's input grid AND output grid have shape (H, W), AND
  * EVERY pair's whole-grid input AND output palette equals S_whole, AND
  * EVERY change blob of EVERY pair has
    ``frozenset(group["input_colors"]) == frozenset(group["output_colors"])
    == S_blob``.

That is, the entire task is pinned to a fixed shape AND a fixed
whole-grid colour vocabulary AND a fixed per-blob colour vocabulary --
the strongest stability gate ARBOR's recognition vocabulary currently
offers across BOTH axes (dimension AND palette) AND BOTH palette scopes
(whole-grid AND per-blob).

Recognition vocabulary axis: the conjunction-of-conjunctions-of-
conjunctions handle named in iter 997's "Next gap" log as candidate
(a). It is the conjunction of:

  * iter 993 ``input_output_dimensions_and_palette_equal_and_constant_across_pairs``
    -- a single (H, W) AND a single whole-grid colour vocabulary S_whole
    such that every pair's input grid AND output grid has shape (H, W)
    AND whole-grid palette equal to S_whole. Itself the conjunction of
    iter 991 (whole-grid palette across pairs) AND iter 992 (whole-grid
    dimensions across pairs).
  * iter 996 ``input_output_group_palette_equal_and_constant_across_pairs``
    -- a single per-blob colour vocabulary S_blob such that every change
    blob of every pair has the same per-blob input AND output set
    S_blob.

The two together pin a (H, W, S_whole, S_blob) quadruple across the
entire task. Equivalently this is the conjunction of iter 997
(whole-grid AND per-group palette stability) AND iter 992 (whole-grid
dimension stability); the two compositions are logically equivalent and
dispatching either way yields the same fixed point. Iter 998 dispatches
through iter 993 AND iter 996 because that decomposition matches the
two pre-existing named scope-AND-conjunction handles most cleanly --
iter 993 already names "shape AND whole-grid palette both task-
invariant", iter 996 already names "per-blob palette task-invariant",
and the iter-998 handle is exactly their AND on the recognition grid.

Why a separate conjunction-of-conjunctions-of-conjunctions matcher
rather than re-running the underlying matchers each lookup:

  * The matcher contract (``docs/RULE_FORMAT.md`` section 4) is
    name-keyed recognition vocabulary; the rule's stored
    ``condition.type`` is the recognition handle's name, not a name+
    params tuple. A future ``translate_to_schema`` emission branch
    (``agent/memory.py``) that needs the "shape AND whole-grid palette
    AND per-blob palette all task-invariant" precondition would
    otherwise have to encode the three-way AND inline in every gate.
    Naming the conjunction as a single registry entry lets the emission
    branch read a single ``condition.type`` and lets stored rules carry
    the tightest single-name precondition rather than a three-name
    conjunction the schema currently has no syntax to express (rule
    schema section 1 stores a single ``condition.type`` string).

  * This is the same conjunction-handle pattern iter 991 used to name
    the three-way whole-grid palette conjunction, iter 992 used to
    name the three-way whole-grid dimension conjunction, iter 993 used
    to AND iter 991 with iter 992 across the dim/palette axes, iter
    996 used to name the per-group palette conjunction, and iter 997
    used to AND iter 991 with iter 996 across the whole-grid/per-group
    palette scopes. This iter is the natural extension: AND iter 997
    (palette: whole-grid + per-group) with iter 992 (dimensions:
    whole-grid), or equivalently AND iter 993 (dimensions + whole-grid
    palette) with iter 996 (per-group palette). The conjunction has
    new semantic content -- "the task is pinned to a fixed shape AND
    fixed whole-grid colour vocabulary AND fixed per-blob colour
    vocabulary all at once" -- that no pairwise conjunction asserts on
    its own:

      - Iter 993 fires on tasks with fixed shape AND fixed whole-grid
        palette but says nothing about per-blob palette content. A task
        with shape ``(3, 3)`` and whole-grid palette ``{0, 1, 2}``
        constant across pairs but with per-blob input/output sets that
        vary across pairs (e.g. pair 0 has a blob with per-blob set
        ``{0, 1}``, pair 1 has a blob with per-blob set ``{1, 2}``)
        fires iter 993 but NOT iter 996, so NOT this matcher.

      - Iter 996 fires on tasks where every blob has the same canonical
        per-blob set across all blobs and pairs, but iter 996 says
        nothing about the surrounding whole-grid shape or palette. A
        task with per-blob set ``{0, 1}`` constant across pairs but with
        different whole-grid shapes (e.g. pair 0 is 3x3, pair 1 is 5x5)
        fires iter 996 but NOT iter 993, so NOT this matcher.

      - Even both iter 993 AND iter 996 firing simultaneously does NOT
        imply that S_whole == S_blob: iter 993's canonical S_whole is a
        property of the whole grid, iter 996's canonical S_blob is a
        property of just the change blobs, and the whole grid can carry
        colours that no change blob touches. The conjunction of the two
        named conjuncts (each pinning its own canonical set) is
        therefore strictly weaker than this matcher would be if it
        additionally required ``S_whole == S_blob``. However, for the
        *single-name vocabulary* purpose of this matcher -- carrying
        the tightest single-string ``condition.type`` a future emission
        branch can adopt -- naming the conjunction of iter 993 AND iter
        996 as a single registry entry is the smallest defensible step
        on the conjunction-of-conjunctions-of-conjunctions axis. The
        additional ``S_whole == S_blob`` clause is a strictly tighter
        future gate, not the goal of this iter (see iter 997's "Next
        gap" forecast log entry candidate (b)).

Why this matters for ARBOR's intended ruleset:

  * "All-axes-invariant" rule family: rules whose action assumes the
    test pair shares a literal coord list AND a literal colour AND a
    literal palette with the training pairs. Anti-unification
    (CLAUDE.md section 8) over two pair-specific programs needs a
    recognition handle to gate the lifted rule on exactly the
    precondition that justifies it -- and a coord-and-colour-literal
    rule whose stored args also assume the test input/output palette
    matches both training's whole-grid AND per-blob vocabularies needs
    a gate that covers all three axes at once.

  * For an abstract rule whose ``action`` references a single literal
    coord list (selection), a single literal colour drawn from training
    AND that colour must lie in both training's whole-grid AND per-blob
    palette vocabularies, this matcher is the weakest single-name
    precondition under which the stored literal args remain meaningful
    for the test pair on all axes.

  * For future emission branches in ``translate_to_schema``, the gate
    ``"input_output_group_palette_and_whole_grid_palette_and_dimensions_equal_and_constant_across_pairs" in fired``
    is strictly tighter than any pairwise conjunction-handle (iter 993
    OR iter 997 individually) -- and tighter than their two-of-two
    conjunction inlined into a branch (because the inline version would
    have to be re-typed at every gate; this matcher names it once).

Mutual containment / co-fire table (universal-over-pairs / -groups
semantics):

  * iter 993 (``input_output_dimensions_and_palette_equal_and_constant_across_pairs``)
    -- whole-grid (dim AND palette) conjunct. STRICTLY IMPLIED. If
    this matcher fires then iter 993 fires by dispatch. The converse
    FAILS: iter 993 fires on tasks with constant shape AND whole-grid
    palette whose per-blob palette content varies across blobs or
    pairs (those tasks reject iter 996, so they reject this matcher).

  * iter 996 (``input_output_group_palette_equal_and_constant_across_pairs``)
    -- per-blob palette conjunct. STRICTLY IMPLIED. Symmetric
    argument. The converse FAILS by a symmetric counterexample (per-
    blob palette constant across pairs but the surrounding whole-grid
    shape varies across pairs, so iter 992 rejects, so iter 993
    rejects, so this matcher rejects).

  * iter 997 (``input_output_group_palette_and_whole_grid_palette_equal_and_constant_across_pairs``)
    -- palette-axis (whole-grid AND per-group) conjunct. STRICTLY
    IMPLIED via the transitive iter 993 -> iter 991 + iter 996 chain
    (iter 997 = iter 991 AND iter 996; iter 993 strictly implies iter
    991; this matcher strictly implies iter 993 AND iter 996, so it
    strictly implies iter 991 AND iter 996, which is iter 997). The
    converse FAILS: iter 997 fires on tasks with per-pair-varying
    shapes that still share a whole-grid AND per-blob palette across
    pairs (those reject iter 992, so reject iter 993, so reject this
    matcher).

  * iter 992 (``input_output_dimensions_equal_and_constant_across_pairs``)
    -- whole-grid dimension conjunct. STRICTLY IMPLIED via iter 993.
    The converse FAILS.

  * iter 991 (``input_output_palette_equal_and_constant_across_pairs``)
    -- whole-grid palette conjunct. STRICTLY IMPLIED via iter 993.
    The converse FAILS.

  * iter 989 (``input_palette_constant_across_pairs``) / iter 990
    (``output_palette_constant_across_pairs``) -- whole-grid single-
    axis cross-pair-set-constancy cells. STRICTLY IMPLIED transitively
    via iter 991 (-> iter 993 -> this matcher). The converse FAILS in
    both directions.

  * iter 994 (``input_group_palette_constant_across_pairs``) / iter
    995 (``output_group_palette_constant_across_pairs``) -- per-group
    single-axis cross-pair-set-constancy cells. STRICTLY IMPLIED
    transitively via iter 996 (-> this matcher). The converse FAILS.

  * iter 195 (``change_input_color_count_per_group_constant_across_pairs``)
    / iter 196 (``change_output_color_count_per_group_constant_across_pairs``)
    -- per-group cardinality. STRICTLY IMPLIED transitively via iter
    994 / 995.

  * iter 185 (``output_palette_equals_input``) -- per-pair whole-
    grid palette equality. STRICTLY IMPLIED via iter 991.

  * iter 1 (``grid_size_preserved``) -- per-pair size_match. STRICTLY
    IMPLIED via iter 992. iter 20 (``output_dimensions_constant``) /
    iter 22 (``input_dimensions_constant``) -- whole-grid dimension
    single-side cells. STRICTLY IMPLIED via iter 992.

  * iter 13 (``identity_transformation``) -- INDEPENDENT in both
    directions. Identity (zero groups per pair) makes iter 996 REJECT
    by the identity-territory clause, so identity fixtures reject
    this matcher. Conversely, this matcher fires on tasks with non-
    empty per-pair group lists whose per-blob input set equals per-
    blob output set AND whose whole-grid shape/palette is task-
    invariant -- identity rejects.

  * iter 17 (``grid_size_changed``) -- MUTUALLY EXCLUSIVE (inherited
    from iter 992's mutual exclusion). If any pair has size_match
    False, iter 992 rejects, so iter 993 rejects, so this matcher
    rejects; if every pair has size_match True, iter 17 rejects.

  * Per-pair / per-group function-shape matchers (iter 8
    ``consistent_color_mapping``, iter 332
    ``inverse_consistent_color_mapping``, iter 333
    ``bijective_color_mapping``, iter 334
    ``bijective_color_mapping_per_group``, iter 335
    ``bijective_color_mapping_per_pair``) -- INDEPENDENT. These
    inspect (input -> output) mapping function-shape over changed
    cells, not set-equality content on whole-grid/per-blob scope.

  * Selection-shape / position / cell-count matchers (iter 23
    ``single_change_group_per_pair``, iter 24
    ``single_cell_change_per_pair``, iter 26
    ``multi_cell_change_group_per_pair``, iter 28
    ``multi_group_per_pair``, iter 30
    ``change_positions_constant_across_pairs``) -- INDEPENDENT
    (orthogonal axes; this matcher does not constrain group count,
    cell count, or position).

Params:
  (none) -- pure existence/uniqueness check on the conjunction of the
  two named conjunction-handles. The detected canonical
  ``(H, W, S_whole, S_blob)`` quadruple is data carried in a future
  rule's stored args, not in ``condition.params``.

Returns True iff:
  - ``input_output_dimensions_and_palette_equal_and_constant_across_pairs``
    fires on ``patterns`` (iter 993: a single ``(H, W, S_whole)`` is
    pinned across every grid of every pair), AND
  - ``input_output_group_palette_equal_and_constant_across_pairs``
    fires on ``patterns`` (iter 996: a single per-blob set S_blob is
    pinned across every group of every pair, with per-pair per-group
    ``input_colors`` set equal to ``output_colors`` set).

Why dispatch to the two named conjuncts rather than re-derive: the
matcher's contract is name-keyed recognition vocabulary; the named
conjuncts ARE the named pieces of vocabulary. Re-deriving the dim,
whole-grid palette, and per-blob palette checks inline would duplicate
iter 992 / 991 / 996 implementation detail and could drift from those
matchers' contracts over time. Dispatch keeps the conjunction-of-
conjunctions-of-conjunctions a true conjunction in code, not just in
intent. The dispatch is read-only (matchers are deterministic and
side-effect-free per docs/RULE_FORMAT.md section 4), so the composition
preserves all the fail-closed posture the named conjuncts already
enforce.

Why fail-closed on missing fields / empty / non-list / etc.: inherited
transitively from the named conjuncts (iter 993 fails closed on missing
dim/palette fields, non-list pair_analyses, empty pair_analyses, non-
bool-int contracts; iter 996 fails closed on the same plus identity-
territory zero-group rejection, missing ``input_colors`` /
``output_colors``, non-list / empty / out-of-range colour entries).
Identity fixtures therefore reject through iter 996's clause.

No companion-touch required: iters 19 / 20 / 184 already emit
``input_height`` / ``input_width`` / ``output_height`` /
``output_width`` / ``input_palette`` / ``output_palette`` from
``_analyze_pair``; iter 1 emits ``groups[i]["input_colors"]`` /
``groups[i]["output_colors"]``. F8 inert (no
``agent/active_operators.py`` diff in this iter).
"""

from __future__ import annotations

from agent.conditions import CONDITION_REGISTRY, register


_DIM_AND_WHOLE_GRID_PALETTE_CONJUNCT = (
    "input_output_dimensions_and_palette_equal_and_constant_across_pairs"
)
_PER_GROUP_PALETTE_CONJUNCT = (
    "input_output_group_palette_equal_and_constant_across_pairs"
)


@register(
    "input_output_group_palette_and_whole_grid_palette_and_dimensions_equal_and_constant_across_pairs"
)
def match(patterns: dict, params: dict) -> bool:
    dim_and_whole_grid_palette_matcher = CONDITION_REGISTRY.get(
        _DIM_AND_WHOLE_GRID_PALETTE_CONJUNCT
    )
    per_group_palette_matcher = CONDITION_REGISTRY.get(_PER_GROUP_PALETTE_CONJUNCT)
    if dim_and_whole_grid_palette_matcher is None or per_group_palette_matcher is None:
        return False
    if dim_and_whole_grid_palette_matcher(patterns, {}) is not True:
        return False
    if per_group_palette_matcher(patterns, {}) is not True:
        return False
    return True
