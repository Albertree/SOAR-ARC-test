"""
output_dimensions_constant -- match tasks where every example pair's
output grid has the SAME (height, width) tuple.

This names the recognition precondition for the simplest possible
``make_grid``-action rule shape: ``action = {"dsl": "make_grid", "args":
{"height": H, "width": W, "color": K}}`` where H, W, and K are all
constants determined by training data. The frozen ``make_grid``
primitive's signature (``make_grid(height, width, color)``) takes a
single ``height`` int and a single ``width`` int -- when this matcher
fires, both values are determinable from the data without needing
polymorphic ``args`` or per-pair output-size inference at apply time.

Why this matters for the schema:

  * ``grid_size_changed`` (iter 17) is the dimensional precondition
    for any rule whose ``action.dsl`` is ``make_grid`` (output is
    freshly constructed, not derived cell-by-cell). It does NOT pin
    *what* the output dimensions are -- a task whose output dimensions
    vary across pairs (e.g. output_height = 2 * input_height with
    varying input heights) still fires ``grid_size_changed`` but
    cannot be served by a ``make_grid(H, W, ...)`` rule with constant
    H, W.
  * ``output_dimensions_constant`` is the *cross-pair* refinement:
    it additionally requires every pair's output (H, W) to be
    bit-identical. This is exactly the precondition under which the
    schema's two integer arguments to ``make_grid`` are determinable
    from training without polymorphic args.
  * Combined with ``output_color_uniform`` (iter 18), the rule shape
    "produce an H×W canvas filled with K" is fully determined by
    three constants. A future iter that wires this through
    ``translate_to_schema`` can mint a non-identity ``make_grid``
    rule for the first time -- recognition vocabulary ahead of rule
    emission, the iter-1/8/10/13/17/18/19 pattern.

Relation to existing matchers:

  * ``grid_size_changed`` (iter 17) is a strict pre-precondition --
    on tasks where input == output dimensions per pair (``size_match
    is True`` everywhere), ``make_grid`` is the wrong action shape.
    The two CAN co-fire on dimension-changed tasks whose output is
    constant; they are NOT mutually exclusive on the strict refinement
    relation (a same-size, constant-size task would fire both
    ``grid_size_preserved`` and ``output_dimensions_constant``, which
    is correct: same-size tasks have trivially-constant output
    dimensions; whether ``make_grid`` is the right action shape is
    a separate dimensional axis the iter-17 matcher already names).
  * ``grid_size_preserved`` (iter 1) and ``output_dimensions_constant``
    can co-fire (same-size tasks have constant output dimensions
    equal to constant input dimensions across pairs IF every pair
    has the same input dimensions, which is the normal case but not
    universally guaranteed -- this matcher does not assume it).
  * ``identity_transformation`` (iter 13) requires zero change groups
    per pair AND every pair's ``size_match`` to be True. If every
    training pair has the same dimensions, ``output_dimensions_constant``
    also fires; they are NOT mutually exclusive (identity is the
    degenerate "constant output dims equal to constant input dims"
    case).
  * ``output_color_uniform`` (iter 18) and
    ``output_dimensions_constant`` are orthogonal on different axes:
    iter-18 inspects change-group output colours, this matcher
    inspects output grid dimensions. They CAN co-fire (uniform-paint
    on a constant-output-size task) or independently (a task with
    constant output dims but per-position varying output colours;
    or a uniform-paint task with varying output dims). Together they
    are the two-axis precondition for the simplest ``make_grid`` rule.
  * ``input_color_uniform`` (iter 19) and
    ``output_dimensions_constant`` are orthogonal -- iter-19 inspects
    change-group input colours, this matcher inspects output grid
    dimensions. The combined precondition (BOTH fire AND
    ``output_color_uniform`` fires) is the strictest known
    rule-shape gate today -- "every cell of colour C is repainted
    K" on a constant-output-size grid.
  * ``consistent_color_mapping`` (iter 8) and
    ``sequential_recoloring`` (iter 10) are orthogonal -- those
    matchers inspect change-group colour structure, not dimensions.

Params:
  (none) -- the detected (H, W) tuple is data carried in
  ``action.args`` (a future ``make_grid`` rule's ``height`` /
  ``width`` arguments), not in ``condition.params``. The matcher is
  a pure existence/uniqueness check on the output-dimension axis.

Returns True iff:
  - ``patterns`` is a dict, AND
  - ``patterns["pair_analyses"]`` is a non-empty list, AND
  - every analysis is a dict, AND
  - every analysis has an ``output_height`` value that is a strict
    positive integer (not bool, ``>= 1``), AND
  - every analysis has an ``output_width`` value with the same
    contract, AND
  - all ``(output_height, output_width)`` tuples across analyses are
    bit-identical.

Why per-pair ``output_height`` / ``output_width`` rather than a
top-level summary: same rationale as iter 17's strict-per-pair
``size_match`` -- matchers should not piggyback on derived top-level
flags; reading from the per-pair fields keeps the recognition layer's
contract on the shape ``_analyze_pair`` emits, not on a summary the
slow path may forget to compute.

Why strict positive-int (not bool, ``>= 1``): a missing or non-positive
output dimension is upstream extractor breakage, not evidence that
output dimensions are constant. Strict comparison forecloses
``output_height = True`` (Python bool-is-int subclass) and
``output_height = 0`` (degenerate empty grid) false positives,
mirroring the strict-type postures of iters 13 / 17 / 18 / 19. The
bool-rejection is the same posture as ``agent/memory.py:validate_rule``
on integer fields (V1 explicitly rejects ``isinstance(x, bool)``).

Why fail-closed on missing dimension fields: the matcher's contract
is ``deterministic and side-effect-free`` (docs/RULE_FORMAT.md §4);
a missing ``output_height`` is upstream extractor breakage (the
field was added to ``_analyze_pair`` in this iter -- a pre-iter-20
patterns dict will lack it and the matcher will correctly fail
closed there, preserving backwards compatibility with any cached
patterns).
"""

from __future__ import annotations

from agent.conditions import register


@register("output_dimensions_constant")
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
        oh = analysis.get("output_height")
        ow = analysis.get("output_width")
        if not isinstance(oh, int) or isinstance(oh, bool) or oh < 1:
            return False
        if not isinstance(ow, int) or isinstance(ow, bool) or ow < 1:
            return False
        observed.add((oh, ow))
        if len(observed) > 1:
            return False
    return len(observed) == 1
