"""
input_palette_count_exceeds_output_palette_count -- match tasks where
every example pair has strictly more distinct colours in its input
palette than in its output palette: ``len(set(input_palette)) >
len(set(output_palette))`` on every pair.

Recognition vocabulary axis: the mirror ``<`` cell of the cardinality-
direction projection of the whole-grid colour palette axis. Iter 188
named the ``|output| > |input|`` cell (strict expansion); this matcher
names the dual ``|input| > |output|`` cell (strict erasure). Together
with iter 185 (equality, ``|output| == |input|``) these three matchers
populate the full 1x3 cardinality-direction trichotomy ``<`` / ``==`` /
``>`` on the same palette fields iter 184 introduced.

Why a separate matcher rather than parameterising iter 184 (output ⊆
input) with a count comparator:

  * The matcher contract (docs/RULE_FORMAT.md §4) is name-keyed
    recognition vocabulary; the rule's stored ``condition.type`` is
    the recognition handle's name, not a name+params tuple. Adding a
    "strict_size" flag onto iter 184 would entangle two distinct
    preconditions under one registry slot, which the iter-34..42
    family explicitly avoided with separate matchers per axis
    projection. Cardinality direction is its own axis, orthogonal to
    set-containment direction (the iter-188 reasoning, applied to the
    mirror cell).
  * iter 184 fires on palette-equality (every output colour appears in
    the input, no input colour erased) AND on palette-erasure (every
    output colour appears in the input, at least one input colour
    dropped). The two cases differ on the cardinality direction:
      - equality: ``|input| == |output|``
      - erasure : ``|input| >  |output|``
    iter 184 does NOT distinguish them; this matcher does. The
    conjunction (iter 184 AND this matcher) is the named recognition
    handle for *strict* palette erasure, i.e. ``input ⊋ output`` --
    a different transformation family from pure palette-equality
    (permutation / identity) which the iter-184/185/186/187 cells
    alone cannot ringfence.
  * Symmetrically, iter 187 (input ⊆ output) fires on equality AND
    on expansion (output ⊋ input). The two cases differ on cardinality
    direction: equality has ``|input| == |output|``; expansion has
    ``|input| <  |output|``. This matcher (input count exceeds output
    count) is therefore *mutually exclusive* with iter 187 on any
    well-typed palette pair (a strict-erasure pair cannot
    simultaneously be an expansion or equality pair). With iter 188
    (the ``>`` cell) this matcher (the ``<`` cell, named ``input ...
    exceeds ... output`` to read like the inequality) names the dual
    direction on the bidirectional axis ``|output| - |input|`` < 0 vs
    > 0 vs = 0.

Why this matters for ARBOR's intended ruleset:

  * Two canonical task families this gate ringfences strictly:
      - "strict palette-erasure" tasks where the output keeps a strict
        subset of input colours and drops at least one. The conjunction
        (iter 184 AND this matcher) is the named precondition; iter
        184 alone over-fires on equality / permutation cases.
      - "extraction / projection" tasks where the transformation drops
        background or noise colours and keeps only a salient subset
        (e.g. extract foreground objects, keep one colour, drop a
        bordering colour). These are well-typed only when the output's
        cardinality is strictly less than the input's. iter 184 alone
        does not name the "colour dropped" precondition; this matcher
        does.
  * For an abstract rule whose action removes colour(s) -- e.g. a
    future ``coloring(grid, derived_selection, kept_colour)`` whose
    action erases everything except a colour determined by the
    cardinality drop -- requires the named cardinality-direction
    precondition. The matcher's name is what a rule's stored
    ``condition.type`` would declare to gate that action correctly.

Mutual containment / co-fire table (universal-over-pairs semantics):

  * Iter 13 (``identity_transformation``) -- input palette equals
    output palette per pair, so ``|input| == |output|`` per pair, so
    ``|input| > |output|`` is FALSE on every pair. STRICTLY mutually
    exclusive with this matcher (on the universal-over-pairs gate,
    identity ⇒ NOT this matcher).
  * Iter 184 (``output_palette_subset_of_input``) -- output ⊆ input
    is necessary but NOT sufficient for strict palette erasure. The
    two co-fire iff output ⊊ input (strict subset = subset AND
    cardinality strictly lesser). iter 184 implies neither this
    matcher (palette equality fires iter 184 but not this) nor its
    negation (palette equality fires iter 184 and ``|input| ==
    |output|``). NOT in a refinement relation either direction; their
    *conjunction* is the strict-erasure handle.
  * Iter 185 (``output_palette_equals_input``) -- equality means
    ``|input| == |output|``, so ``|input| > |output|`` is FALSE.
    STRICTLY mutually exclusive.
  * Iter 186 (``output_palette_disjoint_from_input``) -- disjoint
    palettes on non-empty input/output have ``|input ∩ output| == 0``;
    their cardinalities are independent. This matcher and iter 186
    CAN co-fire (e.g. canvas-rewrite where every output colour is
    fresh AND there are fewer output colours than input colours) AND
    can disagree (e.g. canvas-rewrite where the output has more
    distinct colours than the input). NOT in a refinement relation
    either direction.
  * Iter 187 (``input_palette_subset_of_output``) -- input ⊆ output
    means ``|input| <= |output|`` per pair, so ``|input| > |output|``
    is FALSE on every pair. STRICTLY mutually exclusive on
    well-typed (finite) palettes.
  * Iter 188 (``output_palette_count_exceeds_input_palette_count``) --
    iter 188 fires iff ``|output| > |input|`` per pair; this matcher
    fires iff ``|input| > |output|`` per pair. On a single well-typed
    pair the two are STRICTLY mutually exclusive (only one strict
    direction can hold). On a multi-pair task each direction is
    universal-over-pairs, so they remain mutually exclusive (one
    cannot hold on every pair AND its strict reverse hold on every
    pair). The pair (iter 188, this matcher, iter 185) populates the
    ``<`` / ``==`` / ``>`` trichotomy on the cardinality-direction
    sub-axis exhaustively.
  * Iter 14 (``input_color_uniform``) / iter 15
    (``output_color_uniform``) -- inspect the *changed cells'* source
    / target uniformity. Orthogonal to whole-grid palette cardinality
    direction.
  * Iter 8 (``consistent_color_mapping``) -- per-pair (C -> K) is a
    function on changed cells. Independent: a strict-palette-erasure
    task can be functional (each dropped colour determined) or not.
  * Every cell- / group- / position- / dimension- / shape-regularity
    matcher (iters 1 / 17 / 18 / 19 / 20 / 22 / 33 / 38 / 39 / 40 /
    41 / 42 / 182 / 183) is orthogonal to the whole-grid palette
    cardinality direction axis.

Why fail-closed on empty / malformed (same posture as iters 184 /
185 / 186 / 187 / 188): a missing or non-list palette is upstream
extractor breakage, not evidence the precondition holds. Universal-
over-pairs with a vacuously-true empty case would let an empty
patterns dict fire the gate, which is the wrong default.

Why strict-list-of-non-bool-ints (mirroring iters 184 / 185 / 186 /
187 / 188): Python bools are an ``int`` subclass; the iter-182 / 183
/ 184 / 185 / 186 / 187 / 188 dimensional / palette matchers all
reject them to keep the recognition layer from accepting placeholder
sentinels. Empty lists are admissible at the type level (the per-pair
set will have cardinality 0); the strict-inequality gate then rejects
the degenerate ``0 > 0`` case naturally.

Why the strict ``>`` rather than ``>=``: the ``>=`` direction is
already covered by iter 184 (output ⊆ input ⇒ ``|output| <= |input|``)
in the set-containment-aware form. The named transformation family
this matcher gates is "the input has STRICTLY more distinct colours"
-- the ``==`` case is iter-185 equality territory and a different
rule family (permutation / identity). The strictness is load-bearing:
a future strict-erasure rule needs to NOT fire on equality cases.

Note on the empty-output-palette degenerate case: a pair whose output
palette is empty (zero-area output grid) and input palette is
non-empty trivially satisfies ``|input| > |output| == 0``. This
matcher will fire on that pair. The upstream extractor is responsible
for non-zero-area outputs; the matcher's posture is to honour what is
emitted rather than re-check upstream invariants (consistent with
iters 184 / 185 / 186 / 187 / 188 on the empty-palette edge cases).

Params:
  (none) -- pure per-pair cardinality comparison.

Returns True iff:
  - ``patterns`` is a dict, AND
  - ``patterns["pair_analyses"]`` is a non-empty list, AND
  - every analysis is a dict, AND
  - every analysis has an ``input_palette`` value that is a list of
    non-bool ints, AND
  - every analysis has an ``output_palette`` value with the same
    contract, AND
  - for every analysis: ``len(set(input_palette)) >
    len(set(output_palette))``.

No companion-touch required: iter 184 already emits ``input_palette``
and ``output_palette`` from ``_analyze_pair``; this iter is a pure
matcher addition with no ``agent/active_operators.py`` diff.
"""

from __future__ import annotations

from agent.conditions import register


def _is_palette_list(x) -> bool:
    """A palette field must be a list of non-bool ints. Empty is
    admissible at the type level (the cardinality gate handles the
    degenerate case)."""
    if not isinstance(x, list):
        return False
    for v in x:
        if not isinstance(v, int) or isinstance(v, bool):
            return False
    return True


@register("input_palette_count_exceeds_output_palette_count")
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
        if not (len(set(ip)) > len(set(op))):
            return False
    return True
