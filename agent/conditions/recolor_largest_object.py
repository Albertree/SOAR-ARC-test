"""
recolor_largest_object — R4's *applicability* matcher for the size-ranked
recolor action (BACKLOG_LOOP.md R4 "2nd-order / ranking relation", R1 §2.5-2b
seed selector `argmax`).

The `single_object_move_*` matchers all gate on `all_single` — exactly one
foreground object, selected by `unique(objects_of(G))`. The moment a grid holds
*several* objects, `unique` returns None and the whole object pathway goes dark.
The missing capability is *ranking selection*: picking **which** of several
objects to act on by comparing them to each other on a property — the
agent-side expression of R4's edge-of-edge relation, and the seed selector
`argmax` R1's §2.5-2b names but the substrate had not yet grown. Its absence is
exactly the "selection 재료의 부재" taxonomy §4 diagnoses as the root of the
168-rule accretion failure: with no way to *select*, an abstraction's hole can
only be filled by a per-task literal.

This matcher recognises the smallest task family that *needs* that selector: a
grid of multiple objects where the output equals the input except the **single
size-maximal object** is recolored to one constant color, every other cell left
untouched. Recognising it does not yet *do* it — the action (render via the
frozen `coloring` on `cells_of(argmax(objects_of(G0), size_of))`) is the next
rung's wiring. This is recognition-vocabulary growth (P5), the dimension
CLAUDE.md §6.3 blesses; it introduces no new way of *doing* a transformation.

Reads the `object_ranking` signal `ExtractPatternOperator` surfaces (the
producer of this dict is the application half of this rung, wired next):

    patterns["object_ranking"] = {
        "multi_object":     bool,   # every pair: >1 foreground object in G0
        "select_extreme":   bool,   # every pair: argmax(objects_of(G0), size_of) is well-defined
                                     #             (a single, untied size-maximal object)
        "recolor_constant": bool,   # every pair: output == input except the selected object recolored
        "recolor_color":    int,    # the fill color, constant across pairs (None if it varies)
        "others_unchanged": bool,   # every pair: all non-selected cells identical input->output
        "evidence_count":   int,
    }

Until that producer exists the key is absent, so this matcher returns False and
cannot misfire on the single-object easy/easy_a tasks — it is dormant
recognition vocabulary with a defined contract, not a live change to the solver.
"""

from agent.conditions import register


@register("recolor_largest_object")
def recolor_largest_object(patterns: dict, params: dict | None = None) -> bool:
    """True iff every example pair recolors the single size-maximal object of a
    multi-object grid to one constant color, leaving all other cells unchanged.

    `params.min_evidence` (default 2) guards against firing on a single example —
    one pair cannot establish "always the largest, always this color" as a rule.
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
    )
