"""
input_output_palette_equal_at_both_scopes_and_scope_aligned_and_constant_across_pairs
-- match tasks where there exists a SINGLE colour set S such that

  * EVERY pair's whole-grid input AND output palette equals S, AND
  * EVERY change blob of EVERY pair has
    ``frozenset(group["input_colors"]) == frozenset(group["output_colors"])
    == S``.

That is, ``S_whole == S_blob`` -- the canonical whole-grid palette and
the canonical per-blob palette are NOT two separate canonical sets
that happen to each be constant, but ONE shared set that pins both
scopes simultaneously.

Recognition vocabulary axis: the strict refinement of iter 997
``input_output_group_palette_and_whole_grid_palette_equal_and_constant_across_pairs``,
adding the ``S_whole == S_blob`` clause iter 997's docstring (lines
79-94) explicitly named as "a strictly tighter future gate" and iter
998's "Next gap" log named as candidate (b) -- "the smallest defensible
next conjunction-handle step that introduces new semantic content
(rather than just AND-ing pre-existing handles)".

Why a separate matcher rather than relying on iter 997 alone:

  * Iter 997 fires when iter 991 fires AND iter 996 fires, but each
    of those names its own canonical set: iter 991 pins ``S_whole``
    (the unique frozenset shared by every pair's whole-grid input
    palette AND output palette), iter 996 pins ``S_blob`` (the unique
    frozenset shared by every change blob's input_colors AND
    output_colors across every group of every pair). Nothing in
    either conjunct -- nor in their pairwise AND -- forces ``S_whole``
    to equal ``S_blob``. A task whose whole-grid palette is
    ``{0, 1, 2}`` constant across pairs but whose every change blob
    has per-blob palette ``{0, 1}`` constant across pairs fires iter
    997 (both conjuncts fire) but ``S_whole = {0, 1, 2}`` and
    ``S_blob = {0, 1}`` differ; this matcher REJECTS that task.

  * The "scope-aligned" clause has new semantic content: it asserts
    the change blobs collectively span the entire whole-grid palette
    (no background colour exists outside the blobs' palette) AND the
    whole grid contains no colour outside the per-blob vocabulary.
    Equivalently, every cell of every grid (whether inside a change
    blob or not) draws from the SAME single canonical set. For an
    abstract rule whose ``action`` references a literal colour set
    that must hold both at the whole-grid AND the per-blob scope as
    the SAME set (not two separate sets that happen each to be
    constant), this matcher is the minimal recognition gate.

  * Naming the strictly-tighter gate as a single registry entry
    follows the standard pattern: rule schema section 1 stores a
    single ``condition.type`` string; a future
    ``translate_to_schema`` emission branch in ``agent/memory.py``
    that needs the "scope-aligned palette is task-invariant"
    precondition reads a single ``condition.type`` rather than
    encoding the iter-997 firing AND the cross-scope set equality
    inline at every gate. This is the same single-name-for-strictly-
    tighter-gate posture iter 991 / 992 / 993 / 996 / 997 / 998 took.

  * Iter 998 (``input_output_group_palette_and_whole_grid_palette_and_dimensions_equal_and_constant_across_pairs``)
    AND's iter 993 with iter 996 across the dim+palette x whole-grid
    +per-group axes but introduces no new semantic content beyond AND
    of existing handles. This iter introduces the genuinely new
    "scope-aligned" clause -- the next axis on the palette-stability
    refinement lattice after the AND-of-existing-handles axis
    saturates (iter 998's "Next gap" forecast).

Why this matters for ARBOR's intended ruleset:

  * "Background-free palette permutation" rule family: a permutation
    on a fixed colour vocabulary where every cell of the grid (not
    just change cells) lies in the permutation's domain. Anti-
    unification (CLAUDE.md section 8) needs this gate to lift a
    literal permutation into a single-set generalisation variable
    rather than two separate variables, AND to know the rule's
    action covers the entire grid rather than only blob cells.

  * For an abstract rule whose ``action`` references a single
    canonical colour set drawn from training AND that set must be
    the SAME at both scopes (not just constant at each scope
    independently), this matcher is the weakest single-name
    precondition.

  * For future emission branches in ``translate_to_schema``, the
    gate ``"input_output_palette_equal_at_both_scopes_and_scope_aligned_and_constant_across_pairs"
    in fired`` is strictly tighter than iter 997's gate, and strictly
    tighter than the inline AND of iter 991 + iter 996 + a hand-written
    cross-scope equality check.

Mutual containment / co-fire table (universal-over-pairs / -groups
semantics):

  * iter 997 (``input_output_group_palette_and_whole_grid_palette_equal_and_constant_across_pairs``)
    -- the immediate parent. STRICTLY IMPLIED. If this matcher fires
    with canonical S then iter 997 fires with S_whole = S_blob = S.
    The converse FAILS: iter 997 fires on the whole-grid-{0,1,2} /
    per-blob-{0,1} fixture above, this matcher rejects.

  * iter 991 (``input_output_palette_equal_and_constant_across_pairs``)
    -- whole-grid conjunct. STRICTLY IMPLIED via iter 997. Converse
    FAILS in two directions: iter 991 fires on (whole-grid stable,
    per-blob varying) fixtures (iter 996 rejects -> iter 997 rejects
    -> this rejects); iter 991 fires on (whole-grid stable but
    S_whole != S_blob even when both stable) fixtures (this matcher's
    new clause rejects).

  * iter 996 (``input_output_group_palette_equal_and_constant_across_pairs``)
    -- per-group conjunct. STRICTLY IMPLIED via iter 997 symmetrically.
    Converse FAILS by the symmetric counterexamples.

  * iter 989 (``input_palette_constant_across_pairs``) / iter 990
    (``output_palette_constant_across_pairs``) -- whole-grid single-
    axis cross-pair-set-constancy cells. STRICTLY IMPLIED via iter
    991 transitively.

  * iter 994 (``input_group_palette_constant_across_pairs``) / iter
    995 (``output_group_palette_constant_across_pairs``) -- per-group
    single-axis cross-pair-set-constancy cells. STRICTLY IMPLIED via
    iter 996 transitively.

  * iter 195 / 196 -- per-group cardinality. STRICTLY IMPLIED via
    iter 994 / 995 -> iter 996.

  * iter 185 (``output_palette_equals_input``) -- per-pair whole-grid
    palette equality. STRICTLY IMPLIED via iter 991.

  * iter 998 (``input_output_group_palette_and_whole_grid_palette_and_dimensions_equal_and_constant_across_pairs``)
    -- INDEPENDENT. Iter 998 adds a dimensional clause this matcher
    does not require; this matcher adds the scope-alignment clause
    iter 998 does not require. Both can co-fire on a task that
    pins all three of dimensions, scope-aligned palette, AND per-blob
    palette to a single canonical (H, W, S) -- the strictest possible
    joint stability gate ARBOR's current vocabulary expresses.

  * iter 993 (``input_output_dimensions_and_palette_equal_and_constant_across_pairs``)
    -- dimensional + whole-grid palette AND. INDEPENDENT: iter 993
    asserts shape stability but says nothing about per-blob palette
    or scope alignment; this matcher asserts scope alignment but
    says nothing about shape.

  * iter 992 (``input_output_dimensions_equal_and_constant_across_pairs``)
    / iter 1 / iter 17 / iter 19 / iter 20 / iter 22 / iter 23 /
    iter 24 / iter 26 / iter 28 / iter 32 / iter 33 / iter 38 / iter
    39 / iter 40 / iter 41 / iter 42 / iter 182 / iter 183 -- the
    dimensional / position / cell-count axis matchers. INDEPENDENT
    (orthogonal axis).

  * iter 13 (``identity_transformation``) -- zero groups per pair.
    INDEPENDENT in both directions. Identity fixtures REJECT through
    iter 996's identity-territory clause (inherited via iter 997).
    Conversely, this matcher fires on non-empty-blob fixtures with
    scope-aligned palette, which iter 13 rejects.

  * iter 17 (``grid_size_changed``) -- INDEPENDENT (orthogonal axis;
    this matcher does not constrain shape).

  * iter 8 (``consistent_color_mapping``) / iter 332
    (``inverse_consistent_color_mapping``) / iter 333
    (``bijective_color_mapping``) -- per-pair function shape on the
    (input -> output) mapping over changed cells. INDEPENDENT of
    set-equality + scope-alignment content.

  * iter ``output_colors_equals_input_colors_per_group`` -- per-pair-
    per-group set equality without cross-pair / cross-group constancy
    AND without whole-grid palette constraint. STRICTLY IMPLIED by
    this matcher; the converse FAILS.

  * iter ``output_palette_is_permutation_of_input_palette`` -- per-
    pair whole-grid input-output set equality. STRICTLY IMPLIED via
    iter 185 (this matcher fires -> iter 191's per-pair set equality
    holds; the permutation-shape claim is the equivalent statement).

Params:
  (none) -- pure existence/uniqueness check on the conjunction of
  iter 997 AND the new scope-alignment clause. The detected
  canonical scope-aligned palette S is data carried in a future
  rule's stored args, not in ``condition.params``.

Returns True iff:
  - ``input_output_group_palette_and_whole_grid_palette_equal_and_constant_across_pairs``
    fires on ``patterns`` (iter 997: a single S_whole pinned across
    every grid's whole-grid input AND output palette, AND a single
    S_blob pinned across every change blob's per-blob input AND
    output colour set), AND
  - the canonical S_whole (derivable from any pair's input_palette)
    equals the canonical S_blob (derivable from any group's
    input_colors), as frozenset values.

Why dispatch to iter 997 first rather than re-derive: iter 997 IS the
already-named recognition handle that pins S_whole and S_blob
individually. Re-deriving the whole-grid and per-group checks inline
would duplicate iter 991 / 996 implementation detail and could drift
from those matchers' contracts over time. The dispatch is read-only
(matchers are deterministic and side-effect-free per
docs/RULE_FORMAT.md section 4), so the composition preserves all the
fail-closed posture the named conjuncts already enforce -- and the
additional scope-alignment clause then operates on data the named
conjuncts have already proven canonical.

Why fail-closed on missing fields / empty / non-list / etc.: inherited
transitively from iter 997 -> iter 991 + iter 996. Identity fixtures
reject through iter 996's identity-territory clause. Empty-palette
edge case: iter 996 rejects empty per-blob colour lists (extractor
contract violation), so this matcher inherits that rejection. The
all-empty whole-grid palette case from iter 991 cannot co-occur with
a non-empty per-blob clause from iter 996 (a non-empty per-blob set
implies the whole-grid palette contains at least those colours), so
the scope-alignment clause is well-defined whenever iter 997 fires.

No companion-touch required: iter 184 already emits ``input_palette``
/ ``output_palette`` and iter 1 already emits
``groups[i]["input_colors"]`` / ``groups[i]["output_colors"]`` from
``_analyze_pair``. F8 inert (no ``agent/active_operators.py`` diff in
this iter).
"""

from __future__ import annotations

from agent.conditions import CONDITION_REGISTRY, register


_ITER_997_HANDLE = (
    "input_output_group_palette_and_whole_grid_palette_equal_and_constant_across_pairs"
)


@register(
    "input_output_palette_equal_at_both_scopes_and_scope_aligned_and_constant_across_pairs"
)
def match(patterns: dict, params: dict) -> bool:
    iter_997_matcher = CONDITION_REGISTRY.get(_ITER_997_HANDLE)
    if iter_997_matcher is None:
        return False
    if iter_997_matcher(patterns, {}) is not True:
        return False

    # Iter 997 firing guarantees: pair_analyses is a non-empty list of
    # dicts, each pair has a list-of-non-bool-ints input_palette AND a
    # non-empty groups list whose every group has a list-of-strict-
    # colours input_colors of length >= 1. The defensive shape guards
    # below are belt-and-braces: a None / non-list / missing-field
    # patterns dict that bypasses iter 997 would not be a valid input
    # to begin with, but matchers are required to return False rather
    # than raise (docs/RULE_FORMAT.md section 4).
    if not isinstance(patterns, dict):
        return False
    pair_analyses = patterns.get("pair_analyses")
    if not isinstance(pair_analyses, list) or not pair_analyses:
        return False
    first_pair = pair_analyses[0]
    if not isinstance(first_pair, dict):
        return False
    whole_grid_palette = first_pair.get("input_palette")
    if not isinstance(whole_grid_palette, list):
        return False
    groups = first_pair.get("groups")
    if not isinstance(groups, list) or not groups:
        return False
    first_group = groups[0]
    if not isinstance(first_group, dict):
        return False
    per_blob_palette = first_group.get("input_colors")
    if not isinstance(per_blob_palette, list):
        return False

    s_whole = frozenset(whole_grid_palette)
    s_blob = frozenset(per_blob_palette)
    return s_whole == s_blob
