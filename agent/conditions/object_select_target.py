"""
object_select_target — R1's multi-object *selection* move matcher
(BACKLOG_LOOP.md R1 / §2.5-2b, the `madeup`-phase "multi-object selection"
concept).

The four object_move siblings (constant_target/offset/corner/resize) all gate on
`single_object_all`: the grid holds exactly one object, so "the object" needs no
selector. This matcher fires for the converse, higher case — several objects are
present and the rule keeps exactly *one* of them, chosen by a learned selector
(`max_size`/`min_size`/`unique_color`/`unique_shape`/`border_object`) that
consistently picks the object whose shape+colour survive into the (single) output
object, placed at one shared target. The selector may key on an intrinsic feature
(size/colour/shape) or on a *grid-relative relation* (`border_object`: the object
touching the canvas edge) — the matcher is selector-agnostic, gating only on the
fact that *some* named selector is consistent across pairs.

The selector is the §2.5-2b "selection-lift": instead of a literal coordinate or a
bare `unique`, the object is *selected* by a learned criterion, so the resulting
program shares a skeleton with the single-object placements and lifts into the same
`place_object` abstraction (R3) rather than spawning a per-task rule.

It stays inert on the single-object easy_a family (multi_object_all is False
there), keeping the readings disjoint. Reads the `object_select_move` signal
surfaced by ExtractPatternOperator (computed by
agent/dsl_expr/selection.analyze_object_select_move).
"""

from agent.conditions import register


@register("object_select_target")
def object_select_target(patterns: dict, params: dict | None = None) -> bool:
    """True iff every example holds several objects, the rule keeps exactly one
    (its shape+colour preserved into the single output object), a single named
    selector picks that object in every pair, and all examples place it by one
    shared placement reading — a constant absolute target *or* a constant
    displacement of the selected object — on a same-size canvas, with enough
    evidence.

    The placement reading mirrors the single-object family (§2.5 structural
    unification): a `constant_target` (selected object anchored at one fixed cell)
    or a `constant_offset` (selected object displaced by one fixed vector while the
    absolute anchor varies). Gating on *either* closes the asymmetry where the
    selection path could only express a fixed-cell placement.

    `params.min_evidence` (default 2) guards against committing to a selector from
    a single pair — one example cannot establish that a criterion is *consistent*.
    """
    if not isinstance(patterns, dict):
        return False
    params = params or {}
    min_evidence = params.get("min_evidence", 2)

    sel = patterns.get("object_select_move")
    if not isinstance(sel, dict):
        return False
    if not sel.get("multi_object_all"):
        return False
    # First selection reading keeps the canvas size fixed (same-size placement);
    # resized selection is a later sibling.
    if not sel.get("size_preserved_all"):
        return False
    if sel.get("constant_target") is None and sel.get("constant_offset") is None:
        return False
    if sel.get("selector") is None:
        return False
    return len(sel.get("per_pair") or []) >= min_evidence
