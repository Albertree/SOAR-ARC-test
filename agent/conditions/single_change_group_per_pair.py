"""
single_change_group_per_pair -- match tasks where every example pair has
EXACTLY ONE connected change group.

Recognition vocabulary axis: ``selection-shape`` (group count). The
iter-17 / iter-18 / iter-19 / iter-20 / iter-22 sequence completed the
input/output x colour/dimension quadrant on the simplest possible axes
(``grid_size_changed`` / ``output_color_uniform`` / ``input_color_uniform``
/ ``output_dimensions_constant`` / ``input_dimensions_constant``). Iter
22's "Next gap" log explicitly named the next axes as ``selection-shape
recognition, group-count recognition, position recognition matchers``.
This matcher is the simplest entry in the group-count axis: a Boolean
on the per-pair group cardinality field that ``_analyze_pair`` already
emits (``num_groups``).

Why this matters for the schema:

  * The frozen ``coloring`` DSL primitive
    (``procedural_memory/DSL/coloring.py``) takes a literal selection
    (a coord or list of coords). The simplest rule shape that uses
    ``coloring`` non-trivially is "paint THIS connected region with
    colour K" -- one group, one paint call. Without a precondition
    that pins "exactly one group" the schema cannot yet describe how
    many ``coloring`` calls an action needs (the iter-16
    polymorphic-args obstacle on selection multiplicity, distinct
    from the colour-multiplicity obstacle iter-18 closed).
  * Together with ``output_color_uniform`` (iter 18) the rule shape
    "paint a single blob region with colour K" has its colour pinned
    by iter-18 and its blob-count pinned by this matcher. The blob's
    coords still need either a literal-coord representation gated on
    ``input_dimensions_constant`` (iter 22) or an anti-unification-
    discovered selection abstraction -- but the group-count side of
    the rule shape's vocabulary is now named.
  * Together with ``input_color_uniform`` (iter 19) the rule shape
    "select where input had colour C (which forms one blob)" pins
    the input-side selection's connectivity property. A single
    connected blob of one colour is a much simpler selection
    description than a multi-blob mapping; this matcher is the
    precondition that distinguishes the two.

Relation to existing matchers:

  * ``identity_transformation`` (iter 13) -- requires ``num_groups ==
    0`` per pair. This matcher requires ``num_groups == 1`` per pair.
    They are STRICTLY mutually exclusive (cardinality 0 vs
    cardinality 1).
  * ``output_color_uniform`` (iter 18) and ``input_color_uniform``
    (iter 19) -- inspect change-group colour content, not group
    count. They CAN co-fire with this matcher (the simplest "paint a
    single blob with colour K" case) OR fire independently (multi-
    blob uniform-paint fires iter-18 but not this; single-blob with
    multi-colour fires this but not iter-18). Orthogonal axes.
  * ``consistent_color_mapping`` (iter 8) -- inspects (in, out)
    colour pairs across all groups. CAN co-fire when the single
    group's input/output colours form a 1:1 mapping. Orthogonal.
  * ``sequential_recoloring`` (iter 10) -- requires every pair to
    have the SAME non-zero number of groups N, and the per-group
    output colours form a contiguous integer range. Iter 10 is
    primarily interesting at N >= 2 (the sequence is meaningful);
    technically it can also fire at N == 1 (a trivial single-element
    range), in which case both matchers fire on the same patterns
    dict. They are NOT strictly mutually exclusive but they are also
    not in a refinement relation -- iter 10 may fire at N >= 2 where
    this matcher does not, and this matcher may fire at N == 1 with
    non-contiguous-range colours where iter 10 does not.
  * ``grid_size_preserved`` / ``grid_size_changed`` / ``output_color_uniform``
    / ``input_color_uniform`` / ``input_dimensions_constant`` /
    ``output_dimensions_constant`` -- inspect dimensions or colour
    content, not group count. Orthogonal on the structural axis.

Params:
  (none) -- the matcher is a pure cardinality check; the chosen
  selection (the single group's coords) is data the rule's
  ``action.args`` will carry, not a matcher parameter.

Returns True iff:
  - ``patterns`` is a dict, AND
  - ``patterns["pair_analyses"]`` is a non-empty list, AND
  - every analysis is a dict, AND
  - every analysis carries a strict-positive-int ``num_groups`` value
    (not bool, ``>= 1``), AND
  - every analysis has ``num_groups == 1``.

Why strict ``num_groups == 1`` (not ``>= 1``): the matcher names a
SPECIFIC shape -- "exactly one connected region of change per pair" --
not a generic "at least one." A multi-group pair is a different
recognition territory (group-count >= 2 matchers, deferred) and
must NOT fire this matcher. Iter 22's "Next gap" log distinguished
single-blob from multi-blob recognition as separate axes; this matcher
sits on the single-blob side.

Why strict bool-subclass rejection on ``num_groups``: ``num_groups``
is semantically an integer count, not a Boolean. Strict comparison
forecloses ``num_groups = True`` (Python bool is an int subclass)
false positives, mirroring iter 13 / 17 / 18 / 19 / 20 / 22's
strict-type postures and `validate_rule` V1's
``isinstance(x, bool)`` rejection on integer fields.

Why fail-closed on missing ``num_groups``: the matcher's contract is
``deterministic and side-effect-free`` (docs/RULE_FORMAT.md section 4);
a missing ``num_groups`` is upstream extractor breakage, not evidence
that the precondition holds. ``ExtractPatternOperator._analyze_pair``
has emitted ``num_groups`` since iter 1, so any current patterns dict
will carry it; the fail-closed posture preserves backwards
compatibility with any cached or partially-constructed patterns dict
the recognizer may be asked to evaluate.

Why ``num_groups`` rather than ``len(groups)``: the matcher should
not piggyback on ``groups``'s element count. ``num_groups`` is the
canonical scalar count field of the patterns shape; ``groups`` is a
parallel list of per-group analyses. The two are emitted together by
``_analyze_pair`` and are always consistent there, but a future
caller assembling a patterns dict by hand could conceivably carry
``num_groups`` without re-iterating ``groups``. Reading the scalar
keeps the matcher decoupled from the list shape.
"""

from __future__ import annotations

from agent.conditions import register


@register("single_change_group_per_pair")
def match(patterns: dict, params: dict) -> bool:
    if not isinstance(patterns, dict):
        return False
    pair_analyses = patterns.get("pair_analyses")
    if not isinstance(pair_analyses, list) or not pair_analyses:
        return False

    for analysis in pair_analyses:
        if not isinstance(analysis, dict):
            return False
        n = analysis.get("num_groups")
        if not isinstance(n, int) or isinstance(n, bool):
            return False
        if n != 1:
            return False
    return True
