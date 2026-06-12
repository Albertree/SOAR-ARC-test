"""
self_fractal — self-similar fractal-placement matcher (BACKLOG_LOOP.md §2.5-1 on
the size-expanding axis: the output is the input tiled into an (h·h)×(w·w) canvas
with a copy of the input placed at each of its own foreground cells, drawn by the
frozen `coloring` primitive on a `make_grid` canvas — a *where-to-place*
selection expression, not a new `tile`/`fractal` primitive).

Fires when, in *every* example, placing a copy of the input at each non-background
cell of the input reproduces the output exactly (verified by
agent/dsl_expr/selection.analyze_self_fractal against the COMM between predicted
and actual outputs — P3/P4, grounded in comparison, never assumed), with ≥2 pairs
and a genuine expansion (output strictly larger than input). The placement
predicate ("the cell is foreground") is fixed and value-agnostic, recomputed off
each test input's own background at predict time (P5), so one rule covers the
whole fractal family rather than one literal rule per task (the §2.5-3/4 "covers,
not accretion" shape).

Stays inert (valid_all False) whenever the fractal does not reproduce all pairs —
in particular on every same-size task and every non-h²×w² output — so it never
perturbs the move / recolor / sizing / geometric / scale / symmetry-repair /
extract families.
"""

from agent.conditions import register


@register("self_fractal")
def self_fractal(patterns: dict, params: dict | None = None) -> bool:
    """True iff the self-fractal placement reproduces every example output (a
    genuine size-expanding fractal) with enough evidence.

    `params.min_evidence` (default 2) guards against committing to the fractal
    from a single pair — one pair cannot establish that the placement predicate
    holds across the family rather than coincidentally fitting once.
    """
    if not isinstance(patterns, dict):
        return False
    params = params or {}
    min_evidence = params.get("min_evidence", 2)

    sig = patterns.get("self_fractal")
    if not isinstance(sig, dict):
        return False
    if not sig.get("valid_all"):
        return False
    return int(sig.get("evidence", 0)) >= min_evidence
