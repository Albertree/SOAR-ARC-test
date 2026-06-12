"""
object_keyed_recolor — R4's *applicability* matcher for the object-keyed recolor
action (BACKLOG_LOOP.md R4 "2nd-order / ranking relation", §2.5-2b).

The `recolor_extreme_object` matcher recognises recoloring the single size-extreme
object to **one constant color** — the fill is a literal the examples agree on.
The missing capability is a recolor whose fill color is *read from another object*:
a grid with a *body* object and a smaller *marker* object, where the output
recolors the body to **the marker's color** and erases the marker. The fill is
then a *relation* between two objects (`color-of(marker)`), so it varies per task
— the very thing a constant-fill rule cannot express. This is the agent-side
expression of R4's edge-of-edge relation: the answer's color has a *reason* (the
marker), not a stored value (P3/P4).

This is recognition-vocabulary growth (P5), the dimension CLAUDE.md §6.3 blesses;
it introduces no new way of *doing* a transformation (the action is the frozen
`coloring` composed over selected cells).

Reads the `object_keyed_recolor` signal `ExtractPatternOperator` surfaces:

    patterns["object_keyed_recolor"] = {
        "consistent":     bool,   # every pair: body recolored to color-of(marker),
                                  #             marker erased, others unchanged, same shape
        "evidence_count": int,
    }

The signal is computed by the module-level `_object_keyed_recolor_holds` (shared
with the renderer, module uniformity). On the single-object easy/easy_a tasks the
grids hold one object, so the two-object selection abstains and `consistent` is
False — this matcher stays dormant there and cannot misfire.
"""

from agent.conditions import register


@register("object_keyed_recolor")
def object_keyed_recolor(patterns: dict, params: dict | None = None) -> bool:
    """True iff every example pair recolors a body object to the color of a
    smaller marker object and erases the marker, leaving all other cells
    unchanged.

    `params.min_evidence` (default 2) guards against firing on a single example —
    one pair cannot establish "the body always takes the marker's color" as a
    rule.
    """
    if not isinstance(patterns, dict):
        return False
    params = params or {}
    min_evidence = params.get("min_evidence", 2)

    sig = patterns.get("object_keyed_recolor")
    if not isinstance(sig, dict):
        return False
    if sig.get("evidence_count", 0) < min_evidence:
        return False
    return bool(sig.get("consistent"))
