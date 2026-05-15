"""
input_output_dimensions_equal_and_constant_across_pairs -- match tasks
where there exists a single (H, W) tuple such that EVERY training pair's
input grid AND output grid have exactly those dimensions.

Recognition vocabulary axis: the dimensional analogue of iter 991's
``input_output_palette_equal_and_constant_across_pairs``. It is the
conjunction of:

  * iter 22 ``input_dimensions_constant``  -- all input ``(H, W)``
    tuples are equal across pairs.
  * iter 20 ``output_dimensions_constant`` -- all output ``(H, W)``
    tuples are equal across pairs.
  * iter 1  ``grid_size_preserved``        -- per-pair, output
    dimensions equal input dimensions (``size_match`` True
    everywhere).

The three together pin a single shared ``(H, W)`` tuple across the
entire task; equivalently, ``(input_height, input_width) ==
(output_height, output_width) == (H, W)`` for every pair, with a
single ``(H, W)`` across pairs.

Why a separate conjunction matcher rather than re-running three:

  * The matcher contract (``docs/RULE_FORMAT.md`` section 4) is
    name-keyed recognition vocabulary; a future ``translate_to_schema``
    emission branch (``agent/memory.py``) that needs the "fixed grid
    shape preserved by every pair" precondition would otherwise have
    to encode the three-way AND inline in every gate. Naming the
    conjunction as a single registry entry lets the emission branch
    read a single ``condition.type`` and lets stored rules carry the
    tightest single-name precondition rather than a three-name
    conjunction the schema currently has no syntax to express
    (rule schema section 1 stores a single ``condition.type`` string).

  * This is the same pattern iter 991 used on the palette axis
    (naming the conjunction-handle of iter 185 / iter 989 / iter 990
    as ``input_output_palette_equal_and_constant_across_pairs``) and
    iter 333 used when naming ``bijective_color_mapping`` as the
    conjunction-handle of iter 8 AND iter 332. The conjunction has
    new semantic content -- "a single grid shape is preserved by
    every pair" -- that no individual conjunct asserts on its own
    (iter 22 permits the output dims to differ; iter 20 permits the
    input dims to differ; iter 1 permits each pair's shared shape
    to differ from every other pair's). Only the conjunction names
    the "fixed-grid-shape-across-all-grids" precondition under which
    a rule's stored coord-set args (e.g. ``coloring(selection=...,
    color=K)`` with literal coords) are guaranteed in-bounds for the
    test input AND output.

Why this matters for ARBOR's intended ruleset:

  * Same-grid rules (the frozen ``coloring`` DSL primitive with
    literal coord lists) need a recognition gate that proves the
    rule's stored coords are valid for both the input and output
    grid of every training pair AND of any test input that satisfies
    the same gate. The three conjuncts together provide that proof;
    any one alone would over-fire. iter 22 alone allows the output
    shape to differ from the rule's literal coord list shape; iter
    20 alone allows the input shape to differ; iter 1 alone allows
    the shared shape to vary across pairs.

  * Anti-unification across two pair-specific same-grid programs
    needs a recognition handle to gate the lifted rule on exactly
    the precondition that justifies it. The conjunction-handle is
    the tightest single name for "grid shape is task-invariant",
    which is the weakest precondition under which an abstract
    same-grid rule lifts safely.

  * For future emission branches in ``translate_to_schema``, the gate
    ``"input_output_dimensions_equal_and_constant_across_pairs" in
    fired`` is strictly tighter than any two-of-three conjunction
    (and the three-of-three conjunction inlined into a branch would
    be more fragile than a single name).

Mutual containment / co-fire table (universal-over-pairs semantics):

  * ``input_dimensions_constant`` (iter 22) -- strictly implied. The
    conjunction firing means every input ``(H, W)`` equals the
    shared ``(H, W)``, which is exactly iter 22's claim. The
    converse does NOT hold: iter 22 fires on tasks whose input dims
    are constant but output dims differ from input dims (e.g. a
    tile-style task with constant 3x3 inputs and constant 9x9
    outputs).

  * ``output_dimensions_constant`` (iter 20) -- strictly implied.
    Same logic.

  * ``grid_size_preserved`` (iter 1) -- strictly implied. The
    conjunction firing means every pair's output dims equal its own
    input dims (both equal ``(H, W)``). The converse does NOT hold:
    iter 1 fires per-pair, allowing the shared shape to differ
    across pairs (pair 0 input==output==3x3, pair 1 input==output==
    5x5); this matcher rejects on the cross-pair variation.

  * ``identity_transformation`` (iter 13) -- zero changes per pair
    AND every pair's ``size_match`` True. Identity implies per-pair
    input dims == output dims (i.e. iter 1's claim), but says nothing
    about cross-pair dimensional constancy. INDEPENDENT in one
    direction: identity does NOT imply this matcher (pair 0 identity
    on 3x3, pair 1 identity on 5x5 -- iter 13 fires, this matcher
    rejects). This matcher does NOT imply identity (any per-pair
    same-grid transformation on a constant shape -- recolour,
    permutation -- satisfies this matcher but is not identity).

  * ``grid_size_changed`` (iter 17) -- requires at least one pair to
    have ``size_match`` False. MUTUALLY EXCLUSIVE with this matcher:
    if any pair has output dims != input dims, iter 1 rejects and
    so does this matcher's per-pair equality check; if every pair
    has output dims == input dims, iter 17 rejects on every pair
    being False, so the disjunction does not fire.

  * ``input_dimensions_square`` (iter 25 / similar) -- requires H ==
    W on every input pair. INDEPENDENT: a constant non-square shape
    (e.g. every grid 3x5) satisfies this matcher but iter
    input_dimensions_square rejects; a per-pair-varying square shape
    (pair 0 3x3, pair 1 5x5) satisfies iter input_dimensions_square
    but this matcher rejects on cross-pair variation.

  * ``output_dimensions_square`` (iter analogous) -- symmetric.
    INDEPENDENT.

  * ``input_output_palette_equal_and_constant_across_pairs`` (iter
    991) -- the palette-axis analogue of this matcher on the
    (dimensional, palette) quadrant. INDEPENDENT: a fixed-shape task
    may have a fixed or varying palette; a fixed-palette task may
    have a fixed or varying shape. They co-fire on the tightest
    "shape AND colour vocabulary are both task-invariant" gate, the
    strongest known cross-pair stability gate the recognition
    vocabulary currently offers.

  * ``output_dimensions_multiple_of_input`` (iter analogous) -- when
    this matcher fires, output dims equal input dims per pair, so
    the multiplier is trivially 1 per pair. The multiple-of-input
    matcher permits any constant multiplier; this matcher implies
    the multiple-of-input matcher in the k=1 case. The converse
    fails on any non-unit multiplier.

Params:
  (none) -- the detected ``(H, W)`` tuple is data carried in a
  future rule's stored coord list / dimensional ``args``, not in
  ``condition.params``. The matcher is a pure existence/uniqueness
  check on the conjunction of the three named conjuncts. Future
  params (e.g. min_dimension) are deliberately deferred until an
  emission branch needs them.

Returns True iff:
  - ``patterns`` is a dict, AND
  - ``patterns["pair_analyses"]`` is a non-empty list, AND
  - every analysis is a dict, AND
  - every analysis has an ``input_height`` value that is a strict
    positive integer (not bool, ``>= 1``), AND
  - every analysis has an ``input_width`` value with the same
    contract, AND
  - every analysis has an ``output_height`` value with the same
    contract, AND
  - every analysis has an ``output_width`` value with the same
    contract, AND
  - for every analysis: ``(input_height, input_width) ==
    (output_height, output_width)``, AND
  - all ``(input_height, input_width)`` tuples across analyses are
    bit-identical (equivalently, all output tuples are too --
    follows from per-pair equality and input-side constancy).

Why strict positive-int (not bool, ``>= 1``) on every dimension
field: mirrors iters 17 / 20 / 22 -- a missing or non-positive
dimension is upstream extractor breakage, not evidence that
dimensions are constant. Strict comparison forecloses bool-is-int
subclass false positives and degenerate ``height = 0`` empty grid
false positives. The bool-rejection is the same posture as
``agent/memory.py:validate_rule`` on integer fields (V1 explicitly
rejects ``isinstance(x, bool)``).

Why fail-closed on missing dimension fields: the matcher's contract
is ``deterministic and side-effect-free`` (docs/RULE_FORMAT.md
section 4); a missing dimension field is upstream extractor
breakage. iter 19/20 added the fields to ``_analyze_pair`` so a
pre-iter-20 patterns dict will lack them and the matcher will
correctly fail closed there, preserving backwards compatibility
with any cached patterns.

Why fail-closed on empty ``pair_analyses`` (mirroring iters 20 /
22 / 991): universal-over-pairs with a vacuously-true empty case
would let an empty patterns dict fire the gate, which is the wrong
default. The matcher requires at least one pair to assert the
"shape is task-invariant" claim has any content at all.

No companion-touch required: iters 19 / 20 already emit
``input_height`` / ``input_width`` / ``output_height`` /
``output_width`` from ``_analyze_pair``. F8 inert (no
``agent/active_operators.py`` diff in this iter).
"""

from __future__ import annotations

from agent.conditions import register


def _is_strict_positive_int(x) -> bool:
    """A dimension field must be a strict positive int (not bool).
    iter 17 / 20 / 22 strict-type posture."""
    return isinstance(x, int) and not isinstance(x, bool) and x >= 1


@register("input_output_dimensions_equal_and_constant_across_pairs")
def match(patterns: dict, params: dict) -> bool:
    if not isinstance(patterns, dict):
        return False
    pair_analyses = patterns.get("pair_analyses")
    if not isinstance(pair_analyses, list) or not pair_analyses:
        return False

    observed: tuple[int, int] | None = None
    for analysis in pair_analyses:
        if not isinstance(analysis, dict):
            return False
        ih = analysis.get("input_height")
        iw = analysis.get("input_width")
        oh = analysis.get("output_height")
        ow = analysis.get("output_width")
        if not _is_strict_positive_int(ih):
            return False
        if not _is_strict_positive_int(iw):
            return False
        if not _is_strict_positive_int(oh):
            return False
        if not _is_strict_positive_int(ow):
            return False
        if (ih, iw) != (oh, ow):
            return False
        if observed is None:
            observed = (ih, iw)
        elif observed != (ih, iw):
            return False
    return observed is not None
