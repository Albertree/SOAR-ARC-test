"""
grid_size_changed -- match tasks where at least one example pair has
input and output of differing dimensions.

This is the dimensional precondition that complements ``grid_size_preserved``
(iter 1). Together they partition the dimensional axis of the recognition
vocabulary:

  * ``grid_size_preserved`` -- every example pair has matching input/output
    dimensions. Precondition for any rule whose ``action.dsl`` is
    ``coloring`` (modify-in-place semantics).
  * ``grid_size_changed`` -- at least one example pair has differing
    dimensions. Precondition for any rule whose ``action.dsl`` is
    ``make_grid`` (output is freshly constructed, not derived from the
    input cell-by-cell).

The two matchers map cleanly onto the two frozen DSL primitives
(``coloring`` and ``make_grid``); this is why dimensional recognition is
worth splitting into two named matchers rather than relying on the
top-level ``grid_size_preserved`` flag plus its negation in the slow path.

The matcher is the recognition counterpart to the slow path's eventual
``make_grid``-emitting rule discovery -- not yet wired (``GeneralizeOperator``
currently falls back to identity when neither ``_try_recolor_sequential``
nor ``_try_color_mapping`` succeeds), but a future iter that extends the
generaliser to emit ``make_grid``-based rules will be able to declare
``condition.type = "grid_size_changed"`` without inventing a fresh
detector. Surfacing the precondition as named vocabulary now keeps the
recognition layer ahead of the rule-emission layer -- the opposite of the
test13-eval failure mode where rules accreted without preconditions.

Distinct from ``grid_size_preserved``:
  * ``grid_size_preserved`` requires every pair's ``size_match`` to be True.
  * ``grid_size_changed`` requires at least one pair's ``size_match`` to be
    the literal ``False`` (strict identity, mirroring
    ``identity_transformation``'s strict ``is True`` contract for the
    inverse direction).
  * The two are mutually exclusive on any non-empty ``pair_analyses`` list
    where every entry carries a Boolean ``size_match`` field -- exactly the
    shape ``ExtractPatternOperator._analyze_pair`` produces.

Distinct from ``identity_transformation`` (iter 13):
  * ``identity_transformation`` requires every pair's ``size_match`` to be
    True AND zero change groups. It is a strict refinement of
    ``grid_size_preserved`` on the dimensional axis.
  * ``grid_size_changed`` requires at least one pair's ``size_match`` to be
    False. It is the dimensional negation -- mutually exclusive with
    ``identity_transformation`` (the latter requires all-True).

Orthogonal to ``consistent_color_mapping`` (iter 8) and
``sequential_recoloring`` (iter 10): those matchers inspect change-group
colours, not dimensions. A patterns dict where some pair has
``size_match: False`` while the overlap region still exhibits a consistent
colour mapping can fire both ``grid_size_changed`` and
``consistent_color_mapping`` simultaneously -- they recognise different
axes of the same task.

Params:
  (none)

Returns True iff:
  - ``patterns["pair_analyses"]`` is a non-empty list, AND
  - every entry is a dict (defensive -- malformed entries fail-closed,
    mirroring ``identity_transformation``'s contract), AND
  - at least one entry has ``size_match is False`` (strict identity, not
    truthy/falsy coercion).

Why per-pair ``size_match`` rather than the top-level
``grid_size_preserved`` flag: iter 8 established that matchers should not
piggyback on upstream flags (the dimensional precondition belongs to its
own matcher), and iter 13's ``identity_transformation`` reinforced this by
requiring per-pair signals. Reading from per-pair ``size_match`` keeps the
recognition layer's contract on the shape ``_analyze_pair`` emits, not on
a derived top-level summary the slow path may forget to flip.

Why strict ``is False`` rather than ``not size_match``: a missing or
malformed ``size_match`` field is *not* evidence of a dimension change --
it is evidence of an upstream extractor bug. Strict comparison forecloses
"defaults-to-changed" false positives, mirroring iter 13's strict ``is
True`` posture on the symmetric matcher.
"""

from __future__ import annotations

from agent.conditions import register


@register("grid_size_changed")
def match(patterns: dict, params: dict) -> bool:
    if not isinstance(patterns, dict):
        return False
    pair_analyses = patterns.get("pair_analyses") or []
    if not isinstance(pair_analyses, list) or not pair_analyses:
        return False
    saw_change = False
    for analysis in pair_analyses:
        if not isinstance(analysis, dict):
            return False
        sm = analysis.get("size_match")
        if sm is False:
            saw_change = True
        elif sm is not True:
            # Missing or non-Boolean -- malformed; fail-closed.
            return False
    return saw_change
