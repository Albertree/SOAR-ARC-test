"""
geometric_transform — whole-grid flip / rotation / transpose matcher
(BACKLOG_LOOP.md §2.5-1's worked example: a flip/rotation is the frozen `coloring`
primitive applied at a *transformed coordinate*, not a new primitive).

Fires when a single named coordinate permutation from
`agent/dsl_expr/selection.GEOMETRIC_VOCAB` (flip_h / flip_v / rot90 / rot180 /
rot270 / transpose / anti_transpose) reproduces *every* example output from its
input exactly, with at least one pair where input ≠ output (a genuine transform,
not the identity). The transform name is the lifted *argument* — value-, colour-,
shape- and size-agnostic — so one value-agnostic rule covers the whole geometric
family rather than one literal rule per task (the §2.5-3/4 "covers, not accretion"
shape). Reads the `geometric_transform` signal surfaced by ExtractPatternOperator
(computed by agent/dsl_expr/selection.analyze_geometric_transform), which already
verified the transform against the COMM between predicted and actual outputs
(P3/P4: grounded in comparison, never assumed).

Stays inert (transform None) whenever no single coordinate map reproduces all
pairs, so it never perturbs the move / recolor / sizing families.
"""

from agent.conditions import register


@register("geometric_transform")
def geometric_transform(patterns: dict, params: dict | None = None) -> bool:
    """True iff one named coordinate permutation reproduces every example output
    from its input (a genuine non-identity transform) with enough evidence.

    `params.min_evidence` (default 2) guards against committing to a transform from
    a single pair — a lone symmetric grid can satisfy several maps at once, so one
    example cannot establish *which* permutation is the consistent rule.
    """
    if not isinstance(patterns, dict):
        return False
    params = params or {}
    min_evidence = params.get("min_evidence", 2)

    sig = patterns.get("geometric_transform")
    if not isinstance(sig, dict):
        return False
    if not sig.get("valid_all"):
        return False
    if sig.get("transform") is None:
        return False
    return int(sig.get("evidence", 0)) >= min_evidence
