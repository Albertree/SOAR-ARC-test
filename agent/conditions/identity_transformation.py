"""
identity_transformation -- match tasks where every example pair's output
is bit-identical to its input (zero changed cells and matching grid
dimensions).

This closes the explicit "(TBD)" note in
``agent/conditions/consistent_color_mapping.py``: that matcher's docstring
states that empty changed-cell sets must be rejected by it and *handled
by a separate matcher* so identity is not silently misclassified as a
degenerate colour mapping. ``identity_transformation`` is that separate
matcher.

This is the recognition counterpart to the pipeline's fallback identity
rule in ``agent/active_operators.py:GeneralizeOperator.effect`` -- when
no other strategy succeeds, the operator emits
``{"type": "identity", "confidence": 0.0}``. Surfacing the precondition
as named recognition vocabulary lets a future ``coloring``-based rule
produced by anti-unification (one that is a no-op composition, e.g.
``coloring(selection=[], color=anything)``) declare
``condition.type = "identity_transformation"`` without re-deriving the
detector by hand.

Distinct from ``grid_size_preserved`` (iter 1):
  * ``grid_size_preserved`` is a dimensional precondition only -- it
    fires whenever input and output have the same shape, regardless of
    whether any cells changed.
  * ``identity_transformation`` is strictly stricter: same shape AND
    zero changed cells. It implies ``grid_size_preserved`` per pair
    (each ``size_match`` is True), but the inverse does not hold.

Distinct from ``consistent_color_mapping`` (iter 8) and
``sequential_recoloring`` (iter 10):
  * Both of those require at least one changed cell to recognise a
    mapping/sequence. ``identity_transformation`` requires zero changed
    cells. They are mutually exclusive on any single ``patterns`` dict.

Params:
  (none)

Returns True iff:
  - ``patterns["pair_analyses"]`` is a non-empty list, AND
  - every analysis is a dict with ``size_match: True``, AND
  - every analysis has zero change groups
    (``groups`` is a list of length 0).

Why ``size_match`` per pair (not the top-level ``grid_size_preserved``
flag): ``ExtractPatternOperator._analyze_pair`` only diffs the
overlapping ``min(h_in, h_out) x min(w_in, w_out)`` region. If input is
3x3 and output is 5x5 and the overlap matches, ``len(groups) == 0`` even
though the grids are NOT identical. Requiring ``size_match: True``
per-pair forecloses that false positive without coupling to the
top-level flag (which iter 8 established matchers should not piggyback
on).
"""

from __future__ import annotations

from agent.conditions import register


@register("identity_transformation")
def match(patterns: dict, params: dict) -> bool:
    if not isinstance(patterns, dict):
        return False
    pair_analyses = patterns.get("pair_analyses") or []
    if not pair_analyses:
        return False
    for analysis in pair_analyses:
        if not isinstance(analysis, dict):
            return False
        if analysis.get("size_match", False) is not True:
            return False
        groups = analysis.get("groups")
        if not isinstance(groups, list):
            return False
        if len(groups) != 0:
            return False
    return True
