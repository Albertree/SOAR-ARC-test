"""
symmetry_repair — occlusion-repair matcher (BACKLOG_LOOP.md §2.5-1 on the repair
axis: an occluder region hiding part of an otherwise symmetric grid is rebuilt by
the frozen `coloring` primitive applied at the occluded coordinates with the
colour read from each cell's *symmetric image* — a coordinate+colour expression,
not a new primitive).

Fires when a single occluder colour (the cross-pair COMM — the same hidden colour
in every example) plus, read off each input's own visible structure, the
symmetries that input satisfies reproduce *every* example output exactly. Two
symmetry kinds are recognized under one matcher (the analyzer records which in
`sig["mode"]`): **involution** symmetry — mirror/rotation, via
`selection.held_symmetries` — and **periodic** symmetry — translational tiling,
via `selection.held_periods` (a tiling-occlusion task is rebuilt from the tile it
lies in). The occluder colour is the lifted *argument* — value- and
content-agnostic — and the symmetry set/period is recomputed per test input (P5),
so one value-agnostic rule covers the whole symmetry-repair family (both kinds)
rather than one literal rule per task (the §2.5-3/4 "covers, not accretion"
shape). Reads the `symmetry_repair` signal surfaced by ExtractPatternOperator
(computed by agent/dsl_expr/selection.analyze_symmetry_repair), which already
verified the occluder + visible-symmetry repair against the COMM between predicted
and actual outputs (P3/P4: grounded in comparison, never assumed).

Stays inert (occluder None) whenever no single occluder + visible-symmetry repair
reproduces all pairs — in particular on every task with no change, a multi-colour
changed region, or no held symmetry — so it never perturbs the move / recolor /
sizing / geometric / scale families.
"""

from agent.conditions import register


@register("symmetry_repair")
def symmetry_repair(patterns: dict, params: dict | None = None) -> bool:
    """True iff one occluder colour + the visible symmetries reproduce every
    example output (a genuine occlusion repair) with enough evidence.

    `params.min_evidence` (default 2) guards against committing to an occluder
    from a single pair — one pair cannot establish that the colour is the
    *constant* hidden colour across the family rather than an incidental change;
    the analyzer needs ≥2 pairs to tell the two apart.
    """
    if not isinstance(patterns, dict):
        return False
    params = params or {}
    min_evidence = params.get("min_evidence", 2)

    sig = patterns.get("symmetry_repair")
    if not isinstance(sig, dict):
        return False
    if not sig.get("valid_all"):
        return False
    if sig.get("occluder") is None:
        return False
    return int(sig.get("evidence", 0)) >= min_evidence
