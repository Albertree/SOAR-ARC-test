"""
input_dimensions_constant -- match tasks where every example pair's
input grid has the SAME (height, width) tuple.

This is the input-side dual of iter-20's ``output_dimensions_constant``.
Where iter-20 names the precondition under which the schema's two
integer arguments to ``make_grid(height, width, color)`` are
determinable from training data (H, W collapse to constants on the
output axis), this matcher names the precondition under which any
rule whose ``action`` is gated on assumed test-input dimensions can
safely apply -- the input axis on the same dimensional concern.

Why this matters for the schema:

  * The frozen ``coloring`` DSL primitive
    (``procedural_memory/DSL/coloring.py``) takes a *literal* list of
    ``(row, col)`` coords as its ``selection`` argument. A future
    schema rule storing literal training coords as ``args.selection``
    only generalises to test inputs whose dimensions match the
    training inputs' dimensions. ``input_dimensions_constant`` is the
    recognition precondition that the rule's stored coord list is
    consistent across training pairs -- a prerequisite for any
    literal-coord ``coloring`` rule that a future ``translate_to_schema``
    iter may mint without first lifting ``selection`` via
    anti-unification.
  * Combined with ``grid_size_preserved`` (iter 1), the test input's
    expected dimensions are pinned by the training set: training
    inputs all share the same (H_in, W_in), and outputs match inputs
    per-pair, so the rule's stored shape is the right shape for a
    test input that itself shares those dimensions. (A test input of
    different dimensions remains a graceful-fail at apply time via
    ``_predict_with_entry``'s OOB tolerance; the recognition matcher
    asserts the training-side invariant, not the test-side one.)
  * Together with ``output_dimensions_constant`` (iter 20), the two
    matchers form the input/output × dimension quadrant of the
    recognition vocabulary's two-axis grid (the other axis being
    input/output × colour, named by iter-18 / iter-19's
    ``output_color_uniform`` / ``input_color_uniform``). Symmetric
    completion of the recognition vocabulary on the simplest possible
    axes.

Relation to existing matchers:

  * ``output_dimensions_constant`` (iter 20) -- the OUTPUT-side dual.
    The two CAN co-fire (the typical ARC task where every pair has
    constant input dims and constant output dims, whether or not
    input == output per pair) or independently (e.g. constant input
    dims with per-pair varying output dims; or constant output dims
    with per-pair varying input dims, as on a tile-style task whose
    inputs are heterogeneous but whose canvas is always one fixed
    size). They are orthogonal on the input/output axis of the same
    dimensional concern.
  * ``grid_size_preserved`` (iter 1) -- requires per-pair
    ``size_match: True``. When ``grid_size_preserved`` AND
    ``input_dimensions_constant`` both fire, all training inputs are
    the same size AND every training output equals its input in
    size -- equivalent to ``output_dimensions_constant`` also firing
    with the same (H, W). They are NOT in a refinement relation
    either way: a task can fire ``input_dimensions_constant`` without
    ``grid_size_preserved`` (constant input dims + per-pair size
    change, e.g. tile-style with constant 3x3 inputs and 9x9 outputs),
    or fire ``grid_size_preserved`` without ``input_dimensions_constant``
    (per-pair input == output dims but the dims themselves vary
    across pairs -- the heterogeneous same-size case).
  * ``grid_size_changed`` (iter 17) -- requires at least one pair to
    have ``size_match: False``. CAN co-fire with
    ``input_dimensions_constant`` (the tile-style task: constant
    input dims, constant output dims, but output != input per pair).
    Orthogonal.
  * ``identity_transformation`` (iter 13) -- requires zero changes
    per pair AND every pair's ``size_match: True``. When
    ``identity_transformation`` fires on a task whose pairs also
    share the same input dimensions across pairs,
    ``input_dimensions_constant`` co-fires. They are NOT mutually
    exclusive; identity is the degenerate case.
  * ``output_color_uniform`` (iter 18) and ``input_color_uniform``
    (iter 19) and ``consistent_color_mapping`` (iter 8) and
    ``sequential_recoloring`` (iter 10) -- inspect change-group
    colour structure, not dimensions. Orthogonal on the
    colour/dimension axis.

Params:
  (none) -- the detected (H, W) tuple is data carried in a future
  rule's stored coord list / dimensional ``args``, not in
  ``condition.params``. The matcher is a pure existence/uniqueness
  check on the input-dimension axis.

Returns True iff:
  - ``patterns`` is a dict, AND
  - ``patterns["pair_analyses"]`` is a non-empty list, AND
  - every analysis is a dict, AND
  - every analysis has an ``input_height`` value that is a strict
    positive integer (not bool, ``>= 1``), AND
  - every analysis has an ``input_width`` value with the same
    contract, AND
  - all ``(input_height, input_width)`` tuples across analyses are
    bit-identical.

Why per-pair ``input_height`` / ``input_width`` rather than a
top-level summary: same rationale as iters 17 / 20 -- the matcher
should not piggyback on derived top-level flags; reading from the
per-pair fields keeps the recognition layer's contract on the shape
``_analyze_pair`` emits, not on a summary the slow path may forget
to compute.

Why strict positive-int (not bool, ``>= 1``): a missing or
non-positive input dimension is upstream extractor breakage, not
evidence that input dimensions are constant. Strict comparison
forecloses ``input_height = True`` (Python bool-is-int subclass) and
``input_height = 0`` (degenerate empty grid) false positives,
mirroring the strict-type postures of iters 13 / 17 / 18 / 19 / 20.
The bool-rejection is the same posture as
``agent/memory.py:validate_rule`` on integer fields (V1 explicitly
rejects ``isinstance(x, bool)``).

Why fail-closed on missing dimension fields: the matcher's contract
is ``deterministic and side-effect-free`` (docs/RULE_FORMAT.md §4);
a missing ``input_height`` is upstream extractor breakage. Iter 19
added the field to ``_analyze_pair`` alongside ``output_height`` /
``output_width``; a pre-iter-19 patterns dict will lack it and the
matcher will correctly fail closed there, preserving backwards
compatibility with any cached patterns.
"""

from __future__ import annotations

from agent.conditions import register


@register("input_dimensions_constant")
def match(patterns: dict, params: dict) -> bool:
    if not isinstance(patterns, dict):
        return False
    pair_analyses = patterns.get("pair_analyses")
    if not isinstance(pair_analyses, list) or not pair_analyses:
        return False

    observed: set[tuple[int, int]] = set()
    for analysis in pair_analyses:
        if not isinstance(analysis, dict):
            return False
        ih = analysis.get("input_height")
        iw = analysis.get("input_width")
        if not isinstance(ih, int) or isinstance(ih, bool) or ih < 1:
            return False
        if not isinstance(iw, int) or isinstance(iw, bool) or iw < 1:
            return False
        observed.add((ih, iw))
        if len(observed) > 1:
            return False
    return len(observed) == 1
