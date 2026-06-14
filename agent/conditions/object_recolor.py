"""
object_recolor — R1's object-level *recolour* matcher (BACKLOG_LOOP.md R1,
§2.5-2b).

Fires when every example pair recolours *one selected object in place* — its
cells unchanged, its colour changed — to a colour read from *another* object,
with every other object left untouched and the grid size preserved. Both which
object is recoloured (the *selector* expression) and whose colour it takes (the
*source* expression) are value-agnostic selectors fitted from the example
comparison (`agent/dsl_expr/selection.fit_selector` + `recolor.fit_color_source`),
so a multi-object input names the acted-on object and the colour source without a
literal index or a literal colour — the §2.1 multi-object-selection concept
carried onto a recolour rather than a move.

This is the first transformation family beyond `object_motion` that is *not* a
position change: a recolour. It is recognised the intended way — one general
{condition, action} rule whose (selector, source) arguments are fitted
expressions — superseding the legacy value-keyed `_try_color_mapping` detector
(which stores a literal input->output colour map and so cannot generalise to a
held-out colour). Because the two arguments are recorded on the rule, two
recolour tasks whose (selector, source) diverge anti-unify into ONE covers>1 rule
with an `anti_unification_trace` (R3), instead of one detector per colour map.

Reads the `object_recolor` signal surfaced by ExtractPatternOperator::

    patterns["object_recolor"] = {
        "evidence_count": int,
        "pairs": [ {"recolor_ok": bool, "grid_size_preserved": bool}, ... ],
        "selector": {"kind": ...} | None,  # which object is recoloured
        "source":   {"kind": ...} | None,  # whose colour it takes
    }
"""

from agent.conditions import register


@register("object_recolor")
def object_recolor(patterns: dict, params: dict | None = None) -> bool:
    """True iff every example pair recolours one identified object in place (grid
    size preserved) AND a target *selector* and a colour *source* expression both
    fit every pair. Absent either expression the recolour is not
    value-agnostically describable and we decline rather than guess.

    `params.min_evidence` (default 2) guards against concluding any expression
    from a single pair.
    """
    if not isinstance(patterns, dict):
        return False
    params = params or {}
    min_evidence = params.get("min_evidence", 2)

    rec = patterns.get("object_recolor")
    if not isinstance(rec, dict):
        return False
    pairs = rec.get("pairs")
    if not isinstance(pairs, list) or len(pairs) < min_evidence:
        return False

    for p in pairs:
        if not isinstance(p, dict):
            return False
        if not (p.get("recolor_ok") and p.get("grid_size_preserved")):
            return False

    return rec.get("selector") is not None and rec.get("source") is not None
