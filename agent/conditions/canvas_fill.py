"""
canvas_fill — the solid-canvas colour-fill recognition matcher (BACKLOG_LOOP.md
R1 / §2.5-2b colour reading).

Fires when, across every example pair, the output is a *solid* canvas at the
input's own size whose single colour is a learned *colour reading* of the input
(`COLOR_READING_VOCAB`, seed `most_frequent_color`) — the cross-pair COMM on the
colour DIFF expressed not as a literal but as a reading. This is the colour
analogue of `object_size_grid` (a solid canvas sized by a learned object
property): here the *colour* is the learned argument and the size is the input's
own. It recognises the "fill the grid with its dominant colour" family
(ARC-AGI-2 5582e5ca) that `color_remap` structurally cannot — there the same
source colour maps to a different fill in different pairs, so the colour map is
not a function and `color_remap` abstains.

The learned argument is the *reading* (`most_frequent_color(in)`), recomputed at
predict time off each test input, so the rule stays value-agnostic in the actual
fill colour and one condition-bearing rule covers the family. Reads the
``canvas_fill`` signal surfaced by ExtractPatternOperator (computed by
agent/dsl_expr/selection.analyze_canvas_fill).
"""

from agent.conditions import register


@register("canvas_fill")
def canvas_fill(patterns: dict, params: dict | None = None) -> bool:
    """True iff every example output is a same-size solid canvas whose colour is a
    consistent learned colour-reading of the input, with enough evidence.

    ``params.min_evidence`` (default 2) guards against firing on a single pair —
    one example cannot establish that the *reading* (not the literal colour) is
    what is constant across the family.
    """
    if not isinstance(patterns, dict):
        return False
    params = params or {}
    min_evidence = params.get("min_evidence", 2)

    sig = patterns.get("canvas_fill")
    if not isinstance(sig, dict):
        return False
    if not sig.get("consistent"):
        return False
    if not sig.get("fill_reading"):
        return False
    return sig.get("evidence", 0) >= min_evidence
