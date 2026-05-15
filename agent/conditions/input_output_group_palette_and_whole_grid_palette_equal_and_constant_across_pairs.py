"""
input_output_group_palette_and_whole_grid_palette_equal_and_constant_across_pairs
-- match tasks where there exists a single colour set S such that

  * EVERY pair's whole-grid input AND output palette equals S, AND
  * EVERY change blob of EVERY pair has
    ``frozenset(group["input_colors"]) == frozenset(group["output_colors"])
    == S``.

That is, S is simultaneously the canonical whole-grid palette AND the
canonical per-blob palette across the entire task.

Recognition vocabulary axis: the conjunction-of-conjunctions handle
named in iter 996's "Next gap" log as candidate (a). It is the
conjunction of:

  * iter 991 ``input_output_palette_equal_and_constant_across_pairs``
    -- a single colour set S such that every pair's whole-grid input
    AND output palette equals S.
  * iter 996 ``input_output_group_palette_equal_and_constant_across_pairs``
    -- a single colour set S such that every change blob of every pair
    has the same per-blob input AND output set S.

The two together pin a single shared colour vocabulary S across BOTH
the whole-grid scope AND the per-blob scope -- the strongest known
palette-stability gate ARBOR's recognition vocabulary can currently
express on the palette axis. This is the within-axis (palette only)
per-group AND whole-grid conjunction analogue of iter 993's between-
axis (dimension AND palette) whole-grid conjunction.

Why a separate conjunction-of-conjunctions matcher rather than
re-running iter 991 AND iter 996:

  * The matcher contract (``docs/RULE_FORMAT.md`` section 4) is
    name-keyed recognition vocabulary; the rule's stored
    ``condition.type`` is the recognition handle's name, not a
    name+params tuple. A future ``translate_to_schema`` emission
    branch (``agent/memory.py``) that needs the "palette is task-
    invariant on BOTH whole-grid and per-blob scopes" precondition
    would otherwise have to encode the two-way AND (iter 991 fires,
    iter 996 fires) inline in every gate. Naming the conjunction as a
    single registry entry lets the emission branch read a single
    ``condition.type`` and lets stored rules carry the tightest
    single-name precondition rather than a two-name conjunction the
    schema currently has no syntax to express (rule schema section 1
    stores a single ``condition.type`` string).

  * This is the same conjunction-handle pattern iter 991 used to name
    the three-way whole-grid palette conjunction, iter 992 used to
    name the three-way whole-grid dimension conjunction, iter 993
    used to AND iter 991 with iter 992 across the dim/palette axes,
    iter 996 used to name the per-group palette conjunction, and
    iter 333 used when naming ``bijective_color_mapping`` as the
    conjunction of iter 8 AND iter 332. The conjunction has new
    semantic content -- "the canonical whole-grid palette and the
    canonical per-blob palette are the SAME single colour set across
    every grid AND every blob of every pair" -- that neither named
    conjunct asserts on its own:

      - Iter 991 fires on tasks whose whole-grid input AND output
        palettes equal a canonical set S_whole across pairs, but iter
        991 says nothing about the per-blob colour content. A task
        with whole-grid palette ``{0, 1, 2}`` constant on both sides
        across pairs but with per-blob input/output sets that vary
        across pairs (e.g. pair 0 has a blob with per-blob set
        ``{0, 1}``, pair 1 has a blob with per-blob set ``{1, 2}``)
        fires iter 991 but NOT iter 996, so NOT this matcher.

      - Iter 996 fires on tasks where every blob has the same
        canonical per-blob set S_blob across all blobs and pairs, but
        iter 996 says nothing about the surrounding whole-grid
        palette. A task with per-blob set ``{0, 1}`` constant on
        every blob across pairs but with different whole-grid
        backgrounds (e.g. pair 0 background ``{2}``, pair 1
        background ``{3}``; whole-grid input/output palettes
        ``{0, 1, 2}`` and ``{0, 1, 3}`` differ across pairs) fires
        iter 996 but NOT iter 991, so NOT this matcher.

      - Even both iter 991 AND iter 996 firing simultaneously does
        NOT imply that S_whole == S_blob: iter 991's canonical set is
        a property of the whole grid, iter 996's canonical set is a
        property of just the change blobs, and the whole grid can
        carry colours that no change blob touches. The conjunction
        of the two named conjuncts (each pinning its own canonical
        set) is therefore strictly weaker than this matcher would be
        if it additionally required ``S_whole == S_blob``. However,
        for the *single-name vocabulary* purpose of this matcher --
        carrying the tightest single-string ``condition.type`` a
        future emission branch can adopt -- naming the conjunction
        of the two pre-existing named conjuncts as a single registry
        entry is the smallest defensible step on the conjunction-of-
        conjunctions axis. The additional ``S_whole == S_blob``
        clause is a strictly tighter future gate, not the goal of
        this iter (see "Next gap" forecast in iter 996's log entry).

Why this matters for ARBOR's intended ruleset:

  * "Vocabulary-preserved-on-both-scopes per-blob recolour" rule
    family: rules whose per-blob action keeps the per-blob palette
    bounded by the task-wide vocabulary AND whose surrounding grid
    keeps the same task-wide vocabulary too. Anti-unification
    (CLAUDE.md section 8) needs this gate to lift a literal shared
    palette into a single constant generalisation variable that
    pins both the whole-grid AND the per-blob scope, rather than
    two separate variables S_whole and S_blob.

  * For an abstract rule whose ``action`` references a single literal
    colour set drawn from training AND that set must hold on both
    the whole-grid AND the per-blob scope, this matcher is the
    weakest single-name precondition under which the stored literal
    set is meaningful for the test pair on both scopes.

  * For future emission branches in ``translate_to_schema``, the gate
    ``"input_output_group_palette_and_whole_grid_palette_equal_and_constant_across_pairs" in fired``
    is strictly tighter than either iter 991 OR iter 996 individually
    -- and tighter than their two-of-two conjunction inlined into a
    branch (because the inline version would have to be re-typed at
    every gate; this matcher names it once).

Mutual containment / co-fire table (universal-over-pairs / -groups
semantics):

  * iter 991 (``input_output_palette_equal_and_constant_across_pairs``)
    -- whole-grid conjunct. STRICTLY IMPLIED. If this matcher fires
    then iter 991 fires by dispatch. The converse FAILS: iter 991
    fires on tasks with constant whole-grid palette whose per-blob
    palette content varies across blobs or pairs (those tasks
    reject iter 996, so they reject this matcher).

  * iter 996 (``input_output_group_palette_equal_and_constant_across_pairs``)
    -- per-blob conjunct. STRICTLY IMPLIED. Symmetric argument.
    The converse FAILS by a symmetric counterexample (constant per-
    blob palette across pairs but the surrounding whole-grid palette
    varies across pairs).

  * iter 989 (``input_palette_constant_across_pairs``) / iter 990
    (``output_palette_constant_across_pairs``) -- whole-grid single-
    axis cross-pair-set-constancy cells. STRICTLY IMPLIED via iter
    991. The converse FAILS in both directions.

  * iter 994 (``input_group_palette_constant_across_pairs``) / iter
    995 (``output_group_palette_constant_across_pairs``) -- per-group
    single-axis cross-pair-set-constancy cells. STRICTLY IMPLIED via
    iter 996. The converse FAILS.

  * iter 195 (``change_input_color_count_per_group_constant_across_pairs``)
    / iter 196 (``change_output_color_count_per_group_constant_across_pairs``)
    -- per-group cardinality. STRICTLY IMPLIED via iter 994 / 995
    transitively through iter 996.

  * iter 185 (``output_palette_equals_input``) -- per-pair whole-
    grid palette equality. STRICTLY IMPLIED via iter 991.

  * iter 1 (``grid_size_preserved``) / iter 20
    (``output_dimensions_constant``) / iter 22
    (``input_dimensions_constant``) / iter 992 / iter 993 -- the
    dimensional axis. INDEPENDENT (orthogonal axis).

  * iter 13 (``identity_transformation``) -- INDEPENDENT in both
    directions. Identity (zero groups per pair) makes iter 996
    REJECT by the identity-territory clause, so identity fixtures
    reject this matcher. Conversely, this matcher fires on tasks
    with non-empty per-pair group lists whose per-blob input set
    equals per-blob output set -- identity rejects.

  * iter ``output_colors_equals_input_colors_per_group`` -- asserts
    per-pair-per-group set equality but says nothing about cross-
    pair / cross-group constancy AND says nothing about whole-grid
    palette. This matcher additionally requires that single shared
    set be bit-identical across every blob across every pair AND
    that the whole-grid palette is also constant across pairs.
    STRICTLY IMPLIED in only the whole-task-constant direction
    (this matcher fires => sibling fires); the converse fails.

  * iter 8 (``consistent_color_mapping``) / iter 332
    (``inverse_consistent_color_mapping``) / iter 333
    (``bijective_color_mapping``) -- per-pair function shape on the
    (input -> output) mapping over changed cells. INDEPENDENT of
    set-equality content.

  * Every dimensional / position / cell-count axis matcher (iters
    1 / 17 / 19 / 20 / 22 / 23 / 24 / 26 / 28 / 32 / 33 / 38 / 39 /
    40 / 41 / 42 / 182 / 183 / 991 / 992 / 993) -- INDEPENDENT
    (orthogonal axis; the conjunction does not constrain shape).

Params:
  (none) -- pure existence/uniqueness check on the conjunction of the
  two named conjunction-handles. The detected canonical palette(s)
  are data carried in a future rule's stored args, not in
  ``condition.params``.

Returns True iff:
  - ``input_output_palette_equal_and_constant_across_pairs`` fires
    on ``patterns`` (iter 991: every pair's whole-grid input AND
    output palette equals a single shared S_whole across pairs), AND
  - ``input_output_group_palette_equal_and_constant_across_pairs``
    fires on ``patterns`` (iter 996: every change blob has the same
    per-blob input AND output set S_blob across blobs and pairs).

Why dispatch to the two named conjuncts rather than re-derive: the
matcher's contract is name-keyed recognition vocabulary; the named
conjuncts ARE the named pieces of vocabulary. Re-deriving the
whole-grid and per-group checks inline would duplicate iter 991 /
996 implementation detail and could drift from those matchers'
contracts over time. Dispatch keeps the conjunction-of-conjunctions
a true conjunction in code, not just in intent. The dispatch is
read-only (matchers are deterministic and side-effect-free per
docs/RULE_FORMAT.md section 4), so the composition preserves all
the fail-closed posture the named conjuncts already enforce.

Why fail-closed on missing fields / empty / non-list / etc.:
inherited transitively from the named conjuncts (iter 991 fails
closed on missing palette fields, non-list pair_analyses, empty
pair_analyses, non-bool-int contracts; iter 996 fails closed on the
same plus identity-territory zero-group rejection, missing
``input_colors`` / ``output_colors``, non-list / empty / out-of-
range colour entries). Identity fixtures therefore reject through
iter 996's clause.

No companion-touch required: iter 184 already emits
``input_palette`` / ``output_palette`` and iter 1 already emits
``groups[i]["input_colors"]`` / ``groups[i]["output_colors"]`` from
``_analyze_pair``. F8 inert (no ``agent/active_operators.py`` diff
in this iter).
"""

from __future__ import annotations

from agent.conditions import CONDITION_REGISTRY, register


_WHOLE_GRID_CONJUNCT = "input_output_palette_equal_and_constant_across_pairs"
_PER_GROUP_CONJUNCT = "input_output_group_palette_equal_and_constant_across_pairs"


@register(
    "input_output_group_palette_and_whole_grid_palette_equal_and_constant_across_pairs"
)
def match(patterns: dict, params: dict) -> bool:
    whole_grid_matcher = CONDITION_REGISTRY.get(_WHOLE_GRID_CONJUNCT)
    per_group_matcher = CONDITION_REGISTRY.get(_PER_GROUP_CONJUNCT)
    if whole_grid_matcher is None or per_group_matcher is None:
        return False
    if whole_grid_matcher(patterns, {}) is not True:
        return False
    if per_group_matcher(patterns, {}) is not True:
        return False
    return True
