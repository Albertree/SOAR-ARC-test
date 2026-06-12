"""
recolor_extreme_object — R4's *applicability* matcher for the size-ranked
recolor action (BACKLOG_LOOP.md R4 "2nd-order / ranking relation", R1 §2.5-2b
seed selector `argmax`/`argmin`).

The `single_object_move_*` matchers all gate on `all_single` — exactly one
foreground object, selected by `unique(objects_of(G))`. The moment a grid holds
*several* objects, `unique` returns None and the whole object pathway goes dark.
The missing capability is *ranking selection*: picking **which** of several
objects to act on by comparing them to each other on a property — the
agent-side expression of R4's edge-of-edge relation, and the seed selector
`argmax`/`argmin` R1's §2.5-2b names. Its absence is exactly the "selection
재료의 부재" taxonomy §4 diagnoses as the root of the 168-rule accretion
failure: with no way to *select*, an abstraction's hole can only be filled by a
per-task literal.

This matcher recognises the smallest task family that *needs* that selector: a
grid of multiple objects where the output equals the input except the **single
size-extreme object** is recolored to one constant color, every other cell left
untouched. *Extreme* is direction-parameterised (largest **or** smallest): the
`object_ranking` producer chooses the direction (`extreme_direction` ∈
{"max","min"}) that explains the examples, and R3's anti-unification lifts that
direction into a `?vN` variable so one `recolor_extreme` rule covers both the
"recolor the largest" and "recolor the smallest" families (the genuine
generalization, not a second per-task detector — §2.5-3/4). This is recognition-
vocabulary growth (P5), the dimension CLAUDE.md §6.3 blesses; it introduces no
new way of *doing* a transformation.

Reads the `object_ranking` signal `ExtractPatternOperator` surfaces:

    patterns["object_ranking"] = {
        "multi_object":     bool,   # every pair: >1 foreground object in G0
        "select_extreme":   bool,   # every pair: arg_extreme(objects_of(G0), size_of,
                                     #             extreme_direction) is well-defined
                                     #             (a single, untied size-extreme object)
        "recolor_constant": bool,   # every pair: output == input except the selected object recolored
        "recolor_color":    int,    # the fill color, constant across pairs (None if it varies)
        "extreme_direction":"max"|"min"|None,  # which size extreme the examples agree on
        "others_unchanged": bool,   # every pair: all non-selected cells identical input->output
        "evidence_count":   int,
    }

When no direction explains every pair the producer leaves the recolor flags
False, so this matcher returns False and cannot misfire on the single-object
easy/easy_a tasks — it stays dormant there.
"""

from agent.conditions import register


@register("recolor_extreme_object")
def recolor_extreme_object(patterns: dict, params: dict | None = None) -> bool:
    """True iff every example pair recolors the single size-extreme object
    (largest *or* smallest, consistently) of a multi-object grid to one constant
    color, leaving all other cells unchanged.

    `params.min_evidence` (default 2) guards against firing on a single example —
    one pair cannot establish "always the size-extreme, always this color" as a
    rule.
    """
    if not isinstance(patterns, dict):
        return False
    params = params or {}
    min_evidence = params.get("min_evidence", 2)

    ranking = patterns.get("object_ranking")
    if not isinstance(ranking, dict):
        return False
    if ranking.get("evidence_count", 0) < min_evidence:
        return False
    return bool(
        ranking.get("multi_object")
        and ranking.get("select_extreme")
        and ranking.get("recolor_constant")
        and ranking.get("others_unchanged")
        and ranking.get("recolor_color") is not None
        and ranking.get("extreme_direction") in ("max", "min")
    )
