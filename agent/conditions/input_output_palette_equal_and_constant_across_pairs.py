"""
input_output_palette_equal_and_constant_across_pairs -- match tasks
where there exists a single colour set S such that EVERY training
pair's input palette AND output palette are both equal to S.

Recognition vocabulary axis: the conjunction-handle named in iter
990's "Next gap" log as candidate (a). It is the conjunction of:

  * iter 989 ``input_palette_constant_across_pairs``  -- all input
    palettes are equal as sets across pairs.
  * iter 990 ``output_palette_constant_across_pairs`` -- all output
    palettes are equal as sets across pairs.
  * iter 185 ``output_palette_equals_input``          -- per-pair,
    output palette equals input palette as sets.

The three together pin a single shared palette S across the entire
task; equivalently, ``set(input_palette) == set(output_palette) == S``
for every pair, with a single S across pairs.

Why a separate conjunction matcher rather than re-running three:

  * The matcher contract (``docs/RULE_FORMAT.md`` section 4) is
    name-keyed recognition vocabulary; a future ``translate_to_schema``
    emission branch (``agent/memory.py``) that needs the "fixed colour
    vocabulary preserved by every pair" precondition would otherwise
    have to encode the three-way AND inline in every gate. Naming the
    conjunction as a single registry entry lets the emission branch
    read a single ``condition.type`` and lets stored rules carry the
    tightest single-name precondition rather than a three-name
    conjunction the schema currently has no syntax to express
    (rule schema section 1 stores a single ``condition.type`` string).

  * This is the same pattern iter 333 used when naming
    ``bijective_color_mapping`` as the conjunction-handle of iter 8
    (consistency) AND iter 332 (inverse consistency). The conjunction
    has new semantic content -- "a single palette is preserved by every
    pair" -- that no individual conjunct asserts on its own (iter 989
    permits the output palette to differ; iter 990 permits the input
    palette to differ; iter 185 permits each pair's palette to differ
    from every other pair's). Only the conjunction names the
    "fixed-vocabulary-across-all-grids" precondition under which a
    rule's stored literal-colour args (e.g. ``coloring(..., color=K)``)
    are guaranteed meaningful for the test input AND output.

Why this matters for ARBOR's intended ruleset:

  * Permutation-typed rules whose ``action.dsl`` references one of the
    palette colours need a recognition gate that proves the colour is
    a member of a fixed vocabulary shared by every input AND output
    grid. The three conjuncts together provide that proof; any one
    alone would over-fire.

  * Anti-unification across two pair-specific permutation programs
    needs a recognition handle to gate the lifted rule on exactly the
    precondition that justifies it. The conjunction-handle is the
    tightest single name for "palette is task-invariant", which is the
    weakest precondition under which an abstract palette-permutation
    rule lifts safely.

  * For future emission branches in ``translate_to_schema``, the gate
    ``"input_output_palette_equal_and_constant_across_pairs" in fired``
    is strictly tighter than any two-of-three conjunction (and the
    three-of-three conjunction inlined into a branch would be more
    fragile than a single name).

Mutual containment / co-fire table (universal-over-pairs semantics):

  * ``input_palette_constant_across_pairs`` (iter 989) -- strictly
    implied. The conjunction firing means every input palette equals
    S, which is exactly iter 989's claim. The converse does NOT hold:
    iter 989 fires on tasks whose input palettes are constant but
    output palettes differ from input palettes.

  * ``output_palette_constant_across_pairs`` (iter 990) -- strictly
    implied. Same logic.

  * ``output_palette_equals_input`` (iter 185) -- strictly implied.
    The conjunction firing means every pair's output palette equals
    its own input palette (both equal S). The converse does NOT hold:
    iter 185 fires per-pair, allowing the shared palette to differ
    across pairs (pair 0 input==output=={0,1}, pair 1 input==output==
    {2,3}); this matcher rejects on the cross-pair variation.

  * ``identity_transformation`` (iter 13) -- zero changes per pair.
    Identity implies per-pair input palette == output palette, but
    says nothing about cross-pair palette constancy. INDEPENDENT in
    one direction: identity does NOT imply this matcher (pair 0
    identity on {0,1}, pair 1 identity on {2,3} -- iter 13 fires,
    this matcher rejects). This matcher does NOT imply identity (a
    pure palette permutation on a constant palette satisfies this
    matcher but is not identity).

  * ``output_palette_is_permutation_of_input_palette`` (iter that
    named the per-pair permutation gate) -- the strict-equality
    twin per pair; this matcher is the cross-pair extension. If
    iter-185's per-pair set equality holds AND palettes are constant
    across pairs, then every pair is a permutation on the same fixed
    palette S. The two matchers co-fire on permutation-on-fixed-
    palette tasks; the permutation matcher fires on tasks with
    per-pair palette equality but cross-pair variation (this matcher
    rejects those).

  * ``output_dimensions_constant`` (iter 20) -- a dimensional concern
    on the output side. INDEPENDENT: a fixed-palette task may have
    constant or varying output dimensions. They co-fire on the
    tightest "all training outputs are isomorphic in size AND
    colour vocabulary AND match input vocabulary" gate.

  * ``input_dimensions_constant`` (iter 22) -- symmetric to the above
    on the input dimensional axis. INDEPENDENT.

  * ``palette_intersection_count_constant_across_pairs`` -- a constant
    palette implies a constant per-pair (input-output) intersection
    cardinality, but the converse fails. This matcher strictly
    implies the intersection count matcher; the converse does not
    hold.

  * ``palette_symmetric_difference_constant_across_pairs`` -- when
    this matcher fires, every pair has symmetric difference of size
    0 (input palette == output palette per pair AND palette is
    constant across pairs). The symmetric-difference-constant matcher
    permits any constant non-zero size, so this matcher strictly
    implies the symmetric-difference-constant matcher when symmetric
    difference happens to be 0 across pairs (which is always the case
    when this matcher fires).

  * ``palette_shift_constant_across_pairs`` -- shift offset constant.
    This matcher fires when shift is 0 across pairs (identical
    palettes implies zero shift). The shift matcher permits any
    constant shift, so this matcher implies the shift-constant
    matcher in the 0-shift case; the converse fails on any non-zero
    constant shift.

Params:
  (none) -- pure existence/uniqueness check on the conjunction of
  the three named conjuncts. Future params (e.g. min_palette_size)
  are deliberately deferred until an emission branch needs them.

Returns True iff:
  - ``patterns`` is a dict, AND
  - ``patterns["pair_analyses"]`` is a non-empty list, AND
  - every analysis is a dict, AND
  - every analysis has an ``input_palette`` value that is a list of
    non-bool ints, AND
  - every analysis has an ``output_palette`` value with the same
    contract, AND
  - for every analysis: ``set(output_palette) == set(input_palette)``,
    AND
  - all ``frozenset(input_palette)`` values across analyses are
    bit-identical (equivalently, all output palettes are too --
    follows from per-pair equality and input-side constancy).

Why strict-list-of-non-bool-ints (mirroring iters 184/185/989/990):
Python bools are an ``int`` subclass; the palette matchers all reject
them to keep the recognition layer from accepting placeholder
sentinels.

Why fail-closed on empty / missing (mirroring iters 184/185/989/990):
a missing palette field is upstream extractor breakage. Universal-
over-pairs with a vacuously-true empty case would let an empty
patterns dict fire the gate, which is the wrong default.

Empty-palette degenerate case: a pair with empty input AND empty
output palette satisfies per-pair equality (both empty); multiple
pairs with all-empty palettes satisfy cross-pair constancy too.
The matcher fires in that degenerate case, matching the posture
iters 989 / 990 took on their respective single-axis cells.

No companion-touch required: iter 184 already emits ``input_palette``
and ``output_palette`` from ``_analyze_pair``. F8 inert (no
``agent/active_operators.py`` diff in this iter).
"""

from __future__ import annotations

from agent.conditions import register


def _is_palette_list(x) -> bool:
    """A palette field must be a list of non-bool ints. Empty is
    admissible at the type level (the per-pair equality and cross-
    pair constancy checks handle the all-empty degenerate case)."""
    if not isinstance(x, list):
        return False
    for v in x:
        if not isinstance(v, int) or isinstance(v, bool):
            return False
    return True


@register("input_output_palette_equal_and_constant_across_pairs")
def match(patterns: dict, params: dict) -> bool:
    if not isinstance(patterns, dict):
        return False
    pair_analyses = patterns.get("pair_analyses")
    if not isinstance(pair_analyses, list) or not pair_analyses:
        return False

    observed: frozenset | None = None
    for analysis in pair_analyses:
        if not isinstance(analysis, dict):
            return False
        ip = analysis.get("input_palette")
        op = analysis.get("output_palette")
        if not _is_palette_list(ip):
            return False
        if not _is_palette_list(op):
            return False
        ip_set = frozenset(ip)
        op_set = frozenset(op)
        if ip_set != op_set:
            return False
        if observed is None:
            observed = ip_set
        elif observed != ip_set:
            return False
    return observed is not None
