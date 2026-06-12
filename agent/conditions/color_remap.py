"""
color_remap — the recolor family's recognition matcher (BACKLOG_LOOP.md R1 /
arbor-dsl-taxonomy recolor).

Fires when, across every example pair, a same-size grid is recoloured by a single
1:1 colour map: each input colour maps to exactly one output colour everywhere (the
cross-pair COMM on the colour DIFF), and at least one colour actually changes. This
is the canonical, condition-bearing replacement for the legacy condition-less
``_try_color_mapping`` detector (arbor.md 진단 #4: a dropped-condition rule is an
anti-unification dead-end). The learned argument is the colour map, recomputed at
predict time, so the rule stays value-agnostic in geometry and one rule covers the
whole recolor family — and, sharing a colour→colour skeleton, two such rules lift
under anti-unification (R3).

Reads the ``color_remap`` signal surfaced by ExtractPatternOperator (computed by
agent/dsl_expr/selection.analyze_color_remap).
"""

from agent.conditions import register


@register("color_remap")
def color_remap(patterns: dict, params: dict | None = None) -> bool:
    """True iff every example is a same-size 1:1 colour remap (a well-defined,
    non-identity colour function) with enough evidence.

    ``params.min_evidence`` (default 2) guards against firing on a single pair —
    one example cannot establish that the map is *constant* across the family.
    """
    if not isinstance(patterns, dict):
        return False
    params = params or {}
    min_evidence = params.get("min_evidence", 2)

    sig = patterns.get("color_remap")
    if not isinstance(sig, dict):
        return False
    if not sig.get("consistent"):
        return False
    if not sig.get("color_map"):
        return False
    return sig.get("evidence", 0) >= min_evidence
