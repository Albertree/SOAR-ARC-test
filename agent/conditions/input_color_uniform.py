"""
input_color_uniform -- match tasks where every changed cell across every
example pair STARTED as the SAME single input colour.

This is the input-side dual of iter-18's ``output_color_uniform``. Where
iter-18 names the precondition under which ``coloring``'s ``color``
argument collapses to a constant (the K in ``coloring(grid, selection,
K)``), this matcher names the precondition under which the *selection*
side becomes determinable from the test input alone via a single rule
of the form "wherever the input has colour C". Concretely, the
``selection`` for ``coloring(grid, selection, K)`` can be derived at
apply time as ``[(r, c) for r, row in enumerate(grid) for c, val in
enumerate(row) if val == C]`` -- C being a constant fixed by training.

Why this matters for the schema:

  * The frozen ``coloring`` DSL primitive (``procedural_memory/DSL/
    coloring.py``) takes a *literal* list of ``(row, col)`` coords as
    its ``selection`` argument. A schema rule storing literal training
    coords would fail to generalise to a test input of a different
    size or layout -- the iter-16 obstacle that has been gating
    ``translate_to_schema`` from minting non-identity ``coloring`` rules.
  * For a task that fires BOTH ``input_color_uniform`` AND
    ``output_color_uniform``, the rule shape "paint every cell of
    colour C with colour K" is fully determined by two constants. A
    future iter that wires this through ``translate_to_schema`` can
    represent the selection via a derived predicate (e.g. a new schema
    extension ``args = {"selection_where_input": C, "color": K}``) or
    by lifting ``coloring``'s ``selection`` argument's interpretation
    via anti-unification -- recognition vocabulary ahead of rule
    emission, the iter-1/8/10/13/17/18 pattern.

Relation to existing matchers:

  * ``output_color_uniform`` (iter 18) -- the OUTPUT-side dual. They
    can co-fire (the simplest uniform-paint case: every cell of colour
    C gets repainted to colour K) or independently (input uniform but
    outputs vary by position; output uniform but inputs vary).
  * ``consistent_color_mapping`` (iter 8) -- when ``input_color_uniform``
    fires, the single input colour C may map to one or more output
    colours; ``consistent_color_mapping`` further requires C to map to
    exactly one output. So whenever
    ``input_color_uniform AND consistent_color_mapping`` both fire,
    the resulting (C, K) pair is determined. ``input_color_uniform``
    alone does NOT imply ``consistent_color_mapping`` (C could map to
    multiple outputs depending on position).
  * ``sequential_recoloring`` (iter 10) -- can co-fire with
    ``input_color_uniform`` (e.g. all input cells are colour 0 and they
    are recoloured 3, 4, 5 based on position). The sequence is on the
    OUTPUT side; ``input_color_uniform`` makes no claim about output
    cardinality. They are orthogonal.
  * ``identity_transformation`` (iter 13) -- requires zero changed
    cells. ``input_color_uniform`` requires at least one. They are
    mutually exclusive.
  * Orthogonal to the dimensional axis (``grid_size_preserved`` /
    ``grid_size_changed``): a uniform-input task can happen on a
    same-size grid (paint colour-C cells some new colour) OR on a
    dimension-changed grid (the overlap region's change groups all
    started as colour C even if the output is bigger).

Params:
  (none) -- the detected colour C is data carried in
  ``action.args``, not in ``condition.params``. The matcher is a pure
  existence/uniqueness check on the input side.

Returns True iff:
  - ``patterns`` is a dict, AND
  - ``patterns["pair_analyses"]`` is a non-empty list, AND
  - every analysis is a dict, AND
  - every analysis has at least one change group
    (``len(groups) >= 1``), AND
  - every group has exactly one entry in its ``input_colors`` list
    (``len(input_colors) == 1``), AND
  - all single input colours across all groups in all pairs are
    bit-identical (``len(set(observed)) == 1``).

Why non-empty groups required: with zero change groups the input
colour set is empty and "uniform single colour" is vacuously true --
but that case is identity (no cell was repainted from anything), which
has its own iter-13 matcher. Failing closed here keeps the two matchers
strictly mutually exclusive, mirroring iter-18's symmetric posture on
the output side.

Why strict bit-identity rather than set-of-one collapse: the input
colour is read as the FIRST (and only) entry of ``input_colors``; the
field is a sorted list of small ints emitted by
``ExtractPatternOperator._analyze_pair`` (the standard shape). Strict
equality across pairs forecloses "every pair starts FROM SOME single
colour but they differ" -- e.g. pair 0 paints over red, pair 1 paints
over blue -- which is NOT a uniform-input task. Such a case still
fires ``consistent_color_mapping`` (per-input mapping) but specifically
not ``input_color_uniform``.

Why fail-closed on malformed groups: the matcher's contract is
``deterministic and side-effect-free`` (docs/RULE_FORMAT.md §4); a
missing or non-list ``input_colors`` is upstream extractor breakage,
not evidence that the precondition holds.
"""

from __future__ import annotations

from agent.conditions import register


@register("input_color_uniform")
def match(patterns: dict, params: dict) -> bool:
    if not isinstance(patterns, dict):
        return False
    pair_analyses = patterns.get("pair_analyses")
    if not isinstance(pair_analyses, list) or not pair_analyses:
        return False

    observed_input_colors = set()
    for analysis in pair_analyses:
        if not isinstance(analysis, dict):
            return False
        groups = analysis.get("groups")
        if not isinstance(groups, list) or len(groups) == 0:
            return False
        for group in groups:
            if not isinstance(group, dict):
                return False
            in_colors = group.get("input_colors")
            if not isinstance(in_colors, list) or len(in_colors) != 1:
                return False
            observed_input_colors.add(in_colors[0])
            if len(observed_input_colors) > 1:
                return False
    return len(observed_input_colors) == 1
