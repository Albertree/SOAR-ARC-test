"""
scale_transform — whole-grid scale / replicate matcher (BACKLOG_LOOP.md §2.5-1's
worked example on the scale axis: a block-upscale / tiling is the frozen
`coloring` primitive applied at a *replicated coordinate* on a `make_grid` canvas,
not a new primitive).

Fires when a replication mode from `agent/dsl_expr/selection.SCALE_VOCAB` ("block"
upscale / "tile") plus a per-pair factor reproduces *every* example output from its
input exactly, with the factor not the identity (a genuine scale, not a copy). The
factor is either a *cross-pair constant* `(kh, kw)` or — the §2.5-2b factor-axis
lift — a property *read off each input* (`factor_expr`, e.g. distinct-colour count
or grid side); the matcher fires in both cases (it keys on `valid_all` + `mode`,
which the analyzer sets either way). The (mode, factor) is the lifted *argument* —
value-, colour- and content-agnostic — so one value-agnostic rule covers the whole
scale family rather than one literal rule per task (the §2.5-3/4 "covers, not
accretion" shape). Reads the `scale_transform` signal surfaced by
ExtractPatternOperator (computed by
agent/dsl_expr/selection.analyze_scale_transform), which already verified the
mode+factor against the COMM between predicted and actual outputs (P3/P4: grounded
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
    single pair — one pair cannot establish whether the factor is *constant* across
    the family or a value *read off each input* (the §2.5-2b factor-axis lift); the
    analyzer needs ≥2 pairs (and, for the property read, a genuinely *varying*
    factor) to tell the two apart.
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
