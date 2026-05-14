"""
input_palette_count_equals_output_palette_count -- match tasks where
every example pair has the SAME NUMBER of distinct colours in its
input palette as in its output palette: ``len(set(input_palette)) ==
len(set(output_palette))`` on every pair.

Recognition vocabulary axis: the missing ``== 0`` cell of the
cardinality-direction trichotomy ``|input| - |output|`` < 0 / == 0 / > 0
opened by iter 188 (the ``< 0`` cell, ``output_palette_count_exceeds_
input_palette_count``) and iter 189 (the ``> 0`` cell, ``input_palette_
count_exceeds_output_palette_count``). Iter 189's own docstring claims
"iter 185 (equality, ``|output| == |input|``)" populates this trichotomy
together with iter 188 and itself; the claim is technically wrong --
iter 185 (``output_palette_equals_input``) is SET equality
``set(input_palette) == set(output_palette)``, which is STRICTLY
STRONGER than cardinality equality. Two palettes can have the same
count without being equal as sets (e.g. input ``{0, 1, 2}`` and output
``{3, 4, 5}`` -- iter 185 REJECTS, this matcher FIRES). This matcher
names the actual cardinality-equality cell, completing the trichotomy
with three distinct matchers rather than the iter-189 docstring's
conflation of two semantically distinct cells under one name.

Why a separate matcher rather than parameterising iter 188 / 189 with
a relational comparator, or relying on iter 185:

  * The matcher contract (``docs/RULE_FORMAT.md`` §4) is name-keyed
    recognition vocabulary; the rule's stored ``condition.type`` is
    the recognition handle's name, not a name+params tuple. Adding a
    "relation" flag onto iter 188 / 189 would entangle three distinct
    preconditions under one registry slot, which the iter-34..42 family
    explicitly avoided with separate matchers per axis projection.
    Cardinality-direction is its own axis (with three cells: ``< 0``,
    ``== 0``, ``> 0``); each cell deserves a distinct named handle.
  * Iter 185 (``output_palette_equals_input``) is SET equality. SET
    equality strictly implies cardinality equality (two equal sets
    necessarily have the same cardinality), but cardinality equality
    does NOT imply set equality (witness the disjoint-but-equal-size
    fixture above). Naming the strictly-weaker cardinality-equality
    cell separately is the correct recognition-vocabulary posture --
    it gates *exactly* the rule family whose precondition is
    "the transformation preserves the palette count" (e.g. permutation
    rules whose forward is bijective at count level but whose set
    may shift), without over-firing on the disjoint case
    iter 185 cannot tolerate.
  * The same posture iter 213 took for the per-group forward cell,
    iter 332 took for the whole-task inverse cell, iter 333 took for
    the whole-task bijection cell, iter 334 took for the per-group
    bijection cell, iter 335 took for the per-pair bijection cell,
    iter 336 took for the per-pair forward cell, and iter 971 took
    for the per-pair inverse cell -- name the cell with a single
    handle rather than chain a conjunction at the gate site.

Why this matters for ARBOR's intended ruleset:

  * Palette-count-preserving tasks include:
      - colour permutations on a fixed palette (iter 185 case;
        iter 185 IS strictly stronger and would also fire here,
        confirming this matcher correctly subsumes it)
      - cyclic palette shifts (iter 51 case where the shift is by
        a constant offset within the colour space and the set may
        rotate to a different but equally-sized set)
      - palette substitutions that swap one colour for another
        without changing the count of distinct colours
      - canvas-rewrite tasks where the output uses the same NUMBER
        of fresh colours as the input had (iter 186 fires; iter 185
        does not; this matcher fires)
  * For an abstract rule whose action preserves palette cardinality
    -- e.g. a future palette-substitution rule whose action carries
    a per-colour substitution table whose size matches the input
    palette's size -- the named cardinality-equality precondition
    is what the rule's stored ``condition.type`` would declare. A
    permutation-shaped rule that erroneously stored
    ``output_palette_equals_input`` (iter 185) as its condition
    would under-fire on disjoint-but-equal-size cases the action
    can still handle, dropping coverage that the cardinality-only
    gate would preserve.

Mutual containment / co-fire table (universal-over-pairs semantics):

  * Iter 13 (``identity_transformation``) -- zero changed cells; the
    output grid IS the input grid, so palettes are equal per pair, so
    cardinalities are equal per pair. STRICT IMPLICATION: identity ⇒
    this matcher. Converse fails (a permutation has changed cells but
    equal cardinalities).
  * Iter 184 (``output_palette_subset_of_input``) -- output ⊆ input
    per pair. INDEPENDENT: a subset case can have ``|output| ==
    |input|`` (equality, output ⊊ input is impossible) or ``|output|
    < |input|`` (erasure). The two cases differ on whether this
    matcher fires. NOT in a refinement relation either direction;
    their conjunction (iter 184 AND this matcher) is iter 185's
    territory (output ⊆ input AND |output| == |input| ⇒ output ==
    input as sets, since a subset with equal cardinality of a finite
    superset IS the superset).
  * Iter 185 (``output_palette_equals_input``) -- set equality.
    STRICTLY IMPLIES this matcher: equal sets have equal cardinalities.
    Converse fails on disjoint-but-equal-size palettes (witness:
    input ``{0, 1, 2}``, output ``{3, 4, 5}`` -- this matcher
    FIRES, iter 185 REJECTS).
  * Iter 186 (``output_palette_disjoint_from_input``) -- disjoint
    palettes. INDEPENDENT: disjoint palettes can have equal or
    unequal cardinalities. Co-fires with this matcher iff the
    disjoint pair has equal sizes (the disjoint-but-equal-size
    witness above); rejects this matcher otherwise.
  * Iter 187 (``input_palette_subset_of_output``) -- input ⊆ output
    per pair. SYMMETRIC to iter 184 above: INDEPENDENT in general;
    their conjunction (iter 187 AND this matcher) is also iter
    185's territory (input ⊆ output AND |input| == |output| ⇒
    input == output as sets).
  * Iter 188 (``output_palette_count_exceeds_input_palette_count``)
    -- the strict ``> 0`` cell of the cardinality-direction
    trichotomy. STRICTLY MUTUALLY EXCLUSIVE with this matcher on
    every well-typed pair: a pair cannot satisfy both ``|output| >
    |input|`` and ``|output| == |input|`` simultaneously. On a
    universal-over-pairs gate the mutual exclusion lifts:
    universal-> ``|output| > |input|`` and universal-> ``|output|
    == |input|`` cannot both hold on a non-empty multi-pair task.
  * Iter 189 (``input_palette_count_exceeds_output_palette_count``)
    -- the strict ``< 0`` cell. STRICTLY MUTUALLY EXCLUSIVE with
    this matcher by the same trichotomy reasoning (with the strict
    inequality flipped).
  * Iter 190 (``output_palette_is_permutation_of_input_palette``) --
    set-permutation: output_palette is a permutation of
    input_palette. STRICTLY IMPLIES this matcher (a permutation of
    a set has the same cardinality as the original set). Converse
    fails on disjoint-but-equal-size cases (which fire this matcher
    but reject iter 190 because the sets are not equal as sets,
    let alone as permutations of each other -- a permutation of a
    set is the set itself in a different order).
  * Iter 14 (``input_color_uniform``) -- whole-input |palette| == 1.
    INDEPENDENT in general: this matcher cares about equality of
    sizes, not the specific size. iter 14 co-fires with this matcher
    iff the output is also uniform with |palette| == 1 (witness:
    canvas-rewrite where the output is a single fresh colour and
    the input was a single colour).
  * Iter 15 (``output_color_uniform``) -- symmetric: INDEPENDENT in
    general; co-fires with this matcher iff the input is also
    uniform.
  * Every cell- / group- / position- / dimension- / shape-regularity
    matcher is orthogonal to the whole-grid palette cardinality-
    direction axis.

Strict refinement summary (universal-over-pairs semantics, ⇒ direction):

  * Iter 13 (identity) ⇒ this matcher (palettes equal as sets ⇒
    palettes equal as sizes)
  * Iter 185 (set equality) ⇒ this matcher (set equality ⇒
    cardinality equality)
  * Iter 190 (permutation) ⇒ this matcher (permutation ⇒
    cardinality equality)
  * This matcher ⇏ iter 185 (witness: disjoint-but-equal-size)
  * This matcher ⇏ iter 190 (witness: disjoint-but-equal-size)

Mutual-exclusion witness with iter 188 (cardinality equality AND
NOT strict-output-greater):

  * Pair groups: input palette ``[0, 1, 2]``, output palette
    ``[3, 4, 5]``. Cardinalities equal (3 == 3); strict ``output
    > input`` FALSE. THIS matcher FIRES. Iter 188 REJECTS.

Mutual-exclusion witness with iter 189 (cardinality equality AND
NOT strict-input-greater):

  * Same fixture. Strict ``input > output`` FALSE. THIS matcher
    FIRES. Iter 189 REJECTS.

Witness for proper refinement of iter 185 (cardinality equality
without set equality):

  * Single-pair fixture: input palette ``[0, 1, 2]``, output palette
    ``[3, 4, 5]``. Cardinalities equal; sets disjoint. THIS matcher
    FIRES. Iter 185 REJECTS. Iter 190 REJECTS (a permutation
    requires set equality).

Co-fire witness with iter 185 (set equality, hence cardinality
equality):

  * Single-pair fixture: input palette ``[0, 1, 2]``, output palette
    ``[0, 1, 2]``. THIS matcher FIRES. Iter 185 FIRES.

Co-fire witness with iter 186 (disjoint AND equal-size):

  * Same as the iter-185 mutual-exclusion witness above: input
    ``[0, 1, 2]``, output ``[3, 4, 5]``. THIS matcher FIRES.
    Iter 186 FIRES (disjoint palettes). Iter 185 REJECTS.

Why fail-closed on empty / malformed (same posture as iters 184 /
185 / 186 / 187 / 188 / 189): a missing or non-list palette is
upstream extractor breakage, not evidence the precondition holds.
Universal-over-pairs with a vacuously-true empty case would let
an empty patterns dict fire the gate, which is the wrong default.

Why strict-list-of-non-bool-ints (mirroring iters 184 / 185 / 186
/ 187 / 188 / 189): Python bools are an ``int`` subclass; the
iter-182 / 183 / 184 / 185 / 186 / 187 / 188 / 189 dimensional /
palette matchers all reject them to keep the recognition layer
from accepting placeholder sentinels. Empty palette lists are
admissible at the type level (the per-pair set will have
cardinality 0); the equality gate then fires on the (0 == 0)
degenerate case naturally -- iter 189's empty-output note flags
the same degenerate case; this matcher inherits the same posture.

Why the strict ``==`` rather than parameterising as ``relation
= 'eq'``: the matcher contract is name-keyed (one matcher per
relation cell). The two existing strict cells (iter 188 ``< 0``,
iter 189 ``> 0``) are separate matchers; the equality cell
deserves a separate matcher by the same argument.

Note on the empty-palette degenerate case: a pair with both an
empty input palette and an empty output palette (zero-area grids
on both sides) trivially satisfies ``0 == 0``. This matcher will
fire on that pair. The upstream extractor is responsible for
non-zero-area outputs; the matcher's posture is to honour what
is emitted rather than re-check upstream invariants (consistent
with iters 184 / 185 / 186 / 187 / 188 / 189 on the empty-palette
edge cases).

Params:
  (none) -- pure per-pair cardinality equality check.

Returns True iff:
  - ``patterns`` is a dict, AND
  - ``patterns["pair_analyses"]`` is a non-empty list, AND
  - every analysis is a dict, AND
  - every analysis has an ``input_palette`` value that is a list of
    non-bool ints, AND
  - every analysis has an ``output_palette`` value with the same
    contract, AND
  - for every analysis: ``len(set(input_palette)) ==
    len(set(output_palette))``.

No companion-touch required: iter 184 already emits ``input_palette``
and ``output_palette`` from ``_analyze_pair``; this iter is a pure
matcher addition with no ``agent/active_operators.py`` diff. F8 inert.
"""

from __future__ import annotations

from agent.conditions import register


def _is_palette_list(x) -> bool:
    """A palette field must be a list of non-bool ints. Empty is
    admissible at the type level (the cardinality gate handles the
    degenerate ``0 == 0`` case)."""
    if not isinstance(x, list):
        return False
    for v in x:
        if not isinstance(v, int) or isinstance(v, bool):
            return False
    return True


@register("input_palette_count_equals_output_palette_count")
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
        if len(set(ip)) != len(set(op)):
            return False
    return True
