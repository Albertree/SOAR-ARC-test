"""
scale_transform — whole-grid scale / replicate matcher (BACKLOG_LOOP.md §2.5-1's
worked example on the scale axis: a block-upscale / tiling is the frozen
`coloring` primitive applied at a *replicated coordinate* on a `make_grid` canvas,
not a new primitive).

Fires when a single constant integer factor `(kh, kw)` and replication mode from
`agent/dsl_expr/selection.SCALE_VOCAB` ("block" upscale / "tile") reproduces
*every* example output from its input exactly, with the factor not the identity
`(1, 1)` (a genuine scale, not a copy). The (mode, kh, kw) triple is the lifted
*argument* — value-, colour- and content-agnostic — so one value-agnostic rule
covers the whole scale family rather than one literal rule per task (the §2.5-3/4
"covers, not accretion" shape). Reads the `scale_transform` signal surfaced by
ExtractPatternOperator (computed by
agent/dsl_expr/selection.analyze_scale_transform), which already verified the
factor+mode against the COMM between predicted and actual outputs (P3/P4: grounded
in comparison, never assumed).

Stays inert (mode None) whenever no single constant factor+mode reproduces all
pairs — in particular on every same-size task — so it never perturbs the move /
recolor / sizing / geometric families.
"""

from agent.conditions import register


@register("scale_transform")
def scale_transform(patterns: dict, params: dict | None = None) -> bool:
    """True iff one constant factor + replication mode reproduces every example
    output from its input (a genuine non-identity scale) with enough evidence.

    `params.min_evidence` (default 2) guards against committing to a factor from a
    single pair — one pair cannot establish that the factor is *constant* across
    the family rather than a value read off that input (the §2.5-2b factor-reading
    case, which this constant-factor reading deliberately abstains on).
    """
    if not isinstance(patterns, dict):
        return False
    params = params or {}
    min_evidence = params.get("min_evidence", 2)

    sig = patterns.get("scale_transform")
    if not isinstance(sig, dict):
        return False
    if not sig.get("valid_all"):
        return False
    if sig.get("mode") is None:
        return False
    return int(sig.get("evidence", 0)) >= min_evidence
