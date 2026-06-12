"""
object_corner_target — R1's grid-relative-move recognition matcher
(BACKLOG_LOOP.md R1, the easy000g next-gap from iter 5).

Third sibling of object_constant_target / object_constant_offset. Those fire when
the *absolute* output anchor or the *displacement* is shared across examples;
this one fires when neither is — but every example lands the single object flush
into the **same grid corner** (the cross-pair COMM on a *grid-relative* position
reading). easy000g moves the object to the bottom-right corner of canvases of
different sizes: target (3,3) on 4×4, (2,4) on 3×5 — no constant absolute anchor
and no constant offset, yet always the bottom-right corner.

The answer stays value-agnostic in the object's color and source position; the
only learned argument is *which* corner, recomputed against each test grid's own
size at predict time (so it transfers across grid sizes — the property a literal
target cannot have).

It abstains when the absolute target or the offset is itself constant (the
sibling matchers claim those first), keeping the three move readings disjoint.
Size must be preserved so the same-canvas corner placement is well-defined; the
grid-resize variant (easy000i) is left for a later rung.

Reads the `object_move` signal surfaced by ExtractPatternOperator (computed by
agent/dsl_expr/selection.analyze_object_move).
"""

from agent.conditions import register


@register("object_corner_target")
def object_corner_target(patterns: dict, params: dict | None = None) -> bool:
    """True iff every example is a single object moved (color+shape+size kept)
    flush into one shared grid corner, with enough evidence and no constant
    absolute target/offset (which the sibling matchers claim first).

    `params.min_evidence` (default 2) guards against firing on a single pair —
    one example cannot establish that the corner is *constant*.
    """
    if not isinstance(patterns, dict):
        return False
    params = params or {}
    min_evidence = params.get("min_evidence", 2)

    move = patterns.get("object_move")
    if not isinstance(move, dict):
        return False
    if move.get("constant_corner") is None:
        return False
    if move.get("constant_target") is not None:
        return False
    if move.get("constant_offset") is not None:
        return False
    if not (move.get("single_object_all")
            and move.get("color_preserved_all")
            and move.get("shape_preserved_all")
            and move.get("size_preserved_all")):
        return False
    return len(move.get("per_pair") or []) >= min_evidence
