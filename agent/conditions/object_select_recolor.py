"""
object_select_recolor — R1's multi-object *selective recolor* matcher
(BACKLOG_LOOP.md R1 / §2.5-2b, the `madeup`-phase "multi-object selection"
concept on the recolor axis).

The recolor-axis sibling of `object_select_target` (move → recolor) and the
multi-object converse of `color_remap`. `color_remap` reads a *global* 1:1 colour
map and structurally cannot express "recolour only *one* of two same-coloured
objects" — that source colour would map to two output colours, so its map is not a
function and it abstains. This matcher fires in exactly that blind spot: several
objects are present and the rule repaints exactly *one* of them, chosen by a
learned selector (`max_size`/`min_size`/`unique_color`/`unique_shape`/
`border_object` — the shared SELECTOR_VOCAB), to a single new colour, while every
other object is left untouched.

The selector is the §2.5-2b "selection-lift": instead of a global colour rule, the
object is *selected* by a learned criterion grounded in comparison (which object's
cells changed), so the rule is value-agnostic in colour, position and the
distractors. It stays inert on single-object grids (valid_all False there) and on
global-recolor grids (a global map changes more than one object's cells), keeping
the readings disjoint. Reads the `object_select_recolor` signal surfaced by
ExtractPatternOperator (computed by
agent/dsl_expr/selection.analyze_object_select_recolor).
"""

from agent.conditions import register


@register("object_select_recolor")
def object_select_recolor(patterns: dict, params: dict | None = None) -> bool:
    """True iff every example holds several objects, exactly one is repainted to a
    single new colour (its shape and position unchanged), a single named selector
    picks that object in every pair, and the new colour is constant across pairs,
    with enough evidence.

    `params.min_evidence` (default 2) guards against committing to a selector or a
    new colour from a single pair — one example cannot establish that either is
    *consistent* across the family.
    """
    if not isinstance(patterns, dict):
        return False
    params = params or {}
    min_evidence = params.get("min_evidence", 2)

    sig = patterns.get("object_select_recolor")
    if not isinstance(sig, dict):
        return False
    if not sig.get("valid_all"):
        return False
    if sig.get("selector") is None:
        return False
    if sig.get("new_color") is None:
        return False
    return len(sig.get("per_pair") or []) >= min_evidence
