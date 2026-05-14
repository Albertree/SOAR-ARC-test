"""
output_palette_constant_across_pairs -- match tasks where every example
pair has the SAME set of distinct output-grid colours.

Recognition vocabulary axis: the output-side dual of iter 989's
``input_palette_constant_across_pairs``. Where iter 989 names the
precondition under which the test's *input* palette is pinned by
training (every training pair shares the same ``set(input_palette)``),
this matcher names the precondition under which the *output* palette
is pinned by training (every training pair shares the same
``set(output_palette)``). Together they complete the across-pair set-
equality quadrant on the (input, output) × (dimensional, palette) ×
(across-pair-constancy) grid that iter 22 / iter 20 / iter 989 / this
iter populate.

Why a separate matcher rather than parameterising iter 989:

  * The matcher contract (``docs/RULE_FORMAT.md`` §4) is name-keyed
    recognition vocabulary; the rule's stored ``condition.type`` is
    the recognition handle's name, not a name+params tuple. Each cell
    of the recognition grid deserves its own handle, the same way
    iter 17/20 named ``grid_size_changed`` / ``output_dimensions_
    constant`` as separate slots from iter 1's ``grid_size_preserved``
    / iter 22's ``input_dimensions_constant``. The cross-pair-constant-
    output-palette cell has had no named handle since iter 184
    introduced the ``output_palette`` field; this matcher names it.

  * Existing ``constant_across_pairs`` matchers all target derived
    aggregates (intersection size, union size, symmetric-difference
    size, shift offset). None of them assert SET equality of the
    raw whole-grid output palette across pairs. The intersection-count
    matcher is the closest neighbour; it co-fires whenever this
    matcher fires (a constant palette has constant intersection
    cardinality), but the converse fails: two pairs with palettes
    ``{0,1,2}`` and ``{0,1,3}`` share intersection size 3 yet have
    different palettes -- the count matcher fires, this matcher
    rejects.

Why this matters for ARBOR's intended ruleset:

  * Palette-coded tasks where the output always uses a fixed colour
    vocabulary (e.g. "0 background, 1 frame, 2 highlight" across all
    pairs) need a recognition gate that distinguishes them from
    tasks whose output colour vocabulary varies per pair. A future
    emission branch that stores a fixed-vocabulary output substitution
    table as ``action.args`` needs this precondition to safely
    generalise.

  * For an abstract rule whose ``action`` references a literal colour
    constant from training (e.g. ``coloring(..., color=K)`` where K
    is one of the output palette colours), this matcher is the
    minimal precondition under which K is meaningful for the test
    output as a member of a fixed vocabulary across all pairs.

  * Co-firing with ``output_dimensions_constant`` (iter 20) is the
    symmetric "all training outputs are isomorphic in size and
    colour vocabulary" gate -- the tightest output-side stability
    a recognition rule can declare before lifting via anti-unification.
    The conjunction is currently emission-less but is the right
    precondition stack for future output-anchored rules.

Mutual containment / co-fire table (universal-over-pairs semantics):

  * ``input_palette_constant_across_pairs`` (iter 989) -- same-axis
    input-side dual. INDEPENDENT: a task can fire either, both, or
    neither. The "both fire" cell is the tightest cross-pair palette
    stability gate; "only input" fires on a task that adds a varying
    colour on the output side; "only output" fires on a task that
    collapses varying input colours into a constant output palette
    (the simplest example: paint everything with colour K across
    pairs, with pair 0 input ``{0,1}`` and pair 1 input ``{2,3}``).

  * ``output_dimensions_constant`` (iter 20) -- same-axis dual on
    the dimensional concern (output-side, across-pair). INDEPENDENT:
    a task can have constant output dimensions with varying output
    palettes (a 3x3 output task where pair 0 emits ``{0,1}`` and pair
    1 emits ``{2,3}``), or varying output dimensions with constant
    output palette. They co-fire on the tightest output-side
    stability gate.

  * ``identity_transformation`` (iter 13) -- zero changes per pair AND
    every pair's ``size_match: True``. Identity has output palette
    equal to input palette per pair, but says nothing about whether
    output palettes match ACROSS pairs. INDEPENDENT: an identity task
    can have output ``[0,1]`` in pair 0 and output ``[2,3]`` in pair
    1 (each pair is internally identity) and this matcher rejects.

  * ``output_palette_equals_input`` (iter 185) -- per-pair set
    equality INPUT==OUTPUT, not cross-pair output==output.
    INDEPENDENT: a task can fire iter 185 (each pair preserves
    palette) with varying palettes across pairs (pair 0 ``{0,1}``,
    pair 1 ``{2,3}``, each preserved) -- iter 185 fires per-pair,
    this matcher rejects on the cross-pair varying output palette.

  * ``palette_intersection_count_constant_across_pairs`` -- a constant
    output palette gives constant per-pair input-output intersection
    cardinality only if combined with iter 989's input-side gate;
    on its own the implication is in a different direction. The
    two matchers live on different axes (count vs set identity);
    overlap is data-dependent, not by construction.

  * ``palette_shift_constant_across_pairs`` -- a constant shift offset
    across pairs. INDEPENDENT: a constant output palette can have any
    shift (or no defined shift); a constant shift can hold over
    varying palettes.

Params:
  (none) -- the detected palette set is data carried in a future
  rule's stored args, not in ``condition.params``. The matcher is a
  pure existence/uniqueness check on the output-palette axis.

Returns True iff:
  - ``patterns`` is a dict, AND
  - ``patterns["pair_analyses"]`` is a non-empty list, AND
  - every analysis is a dict, AND
  - every analysis has an ``output_palette`` value that is a list of
    non-bool ints, AND
  - all ``set(output_palette)`` across analyses are bit-identical
    (compared as frozensets so internal list order does not affect
    the verdict -- though ``_analyze_pair`` already emits the list
    sorted, this matcher does not rely on that for its verdict).

Why strict-list-of-non-bool-ints: Python bools are an ``int``
subclass; the iter-184..190 palette matchers all reject them to keep
the recognition layer from accepting placeholder sentinels. Iter 989
took the same posture on its input-side mirror.

Why fail-closed on empty / missing: the matcher's contract is
``deterministic and side-effect-free``; a missing ``output_palette``
is upstream extractor breakage (iter 184 added the field). Universal-
over-pairs with a vacuously-true empty case would let an empty
patterns dict fire the gate, which is the wrong default.

Empty-palette degenerate case: a pair with an empty output palette
(zero-area output grid) carries the empty set; multiple pairs with
empty outputs all share that set and this matcher fires. The upstream
extractor is responsible for non-zero-area outputs.

No companion-touch required: iter 184 already emits ``output_palette``
from ``_analyze_pair``. F8 inert (no ``agent/active_operators.py``
diff in this iter).
"""

from __future__ import annotations

from agent.conditions import register


def _is_palette_list(x) -> bool:
    """A palette field must be a list of non-bool ints. Empty is
    admissible at the type level (the cross-pair equality check
    handles the degenerate ``all-empty`` case)."""
    if not isinstance(x, list):
        return False
    for v in x:
        if not isinstance(v, int) or isinstance(v, bool):
            return False
    return True


@register("output_palette_constant_across_pairs")
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
        op = analysis.get("output_palette")
        if not _is_palette_list(op):
            return False
        current = frozenset(op)
        if observed is None:
            observed = current
        elif observed != current:
            return False
    return observed is not None
