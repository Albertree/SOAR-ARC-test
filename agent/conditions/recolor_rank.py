"""
recolor_rank — the rank-based sequential-recolor family's recognition matcher
(BACKLOG_LOOP.md R1 / §2.5-2b ranking selector / arbor-dsl-taxonomy recolor).

Fires when, across every example pair, a same-size grid's changed cells form ``k``
single-coloured connected groups that are repainted to a *contiguous run* of
colours (``start, start+1, …``), and the *same* position key (`top_row` /
`top_col`) orders the groups into that run in every pair. The learned argument is a
``rank-by(position)`` selector (`argsort` in the §2.5 selection vocabulary) — the
sibling of the 1:1 colour map ``color_remap`` keys on, and distinct from the
constant maps/targets the other families carry (R4-adjacent: a derived ordinal
property). This is the canonical, condition-bearing replacement for the legacy
condition-less ``_try_recolor_sequential`` detector (arbor.md 진단 #4: a
dropped-condition rule is an anti-unification dead-end). The selector is recomputed
at predict time, so the rule stays value-agnostic in the absolute colours,
positions and group count, and two such rules lift under anti-unification (R3).

Reads the ``recolor_rank`` signal surfaced by ExtractPatternOperator (computed by
agent/dsl_expr/selection.analyze_recolor_rank).
"""

from agent.conditions import register


@register("recolor_rank")
def recolor_rank(patterns: dict, params: dict | None = None) -> bool:
    """True iff every example is a same-size rank-based sequential recolor with a
    consistent ordering key and enough evidence.

    ``params.min_evidence`` (default 2) guards against firing on a single pair —
    one example cannot establish that the *same* ordering key holds across the
    family.
    """
    if not isinstance(patterns, dict):
        return False
    params = params or {}
    min_evidence = params.get("min_evidence", 2)

    sig = patterns.get("recolor_rank")
    if not isinstance(sig, dict):
        return False
    if sig.get("sort_key") is None:
        return False
    return sig.get("evidence", 0) >= min_evidence
