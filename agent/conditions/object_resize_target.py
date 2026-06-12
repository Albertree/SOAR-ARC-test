"""
object_resize_target — R1's grid-*resize* move recognition matcher
(BACKLOG_LOOP.md R1, the easy000i next-gap from iter 6).

Fourth sibling of object_constant_target / object_constant_offset /
object_corner_target. Those three all require the canvas size to be *preserved*
between input and output, so the same-canvas placement is well-defined. This one
fires for the converse case — the output grid *resizes* (its dimensions differ
from the input) — provided every example's output has the **same** dimensions
(the cross-pair COMM on the output canvas size) and the single object lands at
one shared **target** on that resized canvas.

easy000i moves a single pixel onto a constant 5×5 output canvas (from a 6×6
input) at the top-left (0,0): neither the input-sized placement matchers apply
(size is not preserved) nor is the output a constant grid (the object's colour
varies: 2, 1, 4). The learned arguments are the output dimensions and the target
anchor, both cross-pair COMMs of the example outputs; the object's colour, shape
and source position stay value-agnostic and come from each test G0 (P5).

It abstains when the size *is* preserved (the three sibling matchers claim those
families first), keeping the readings disjoint. Reads the `object_move` signal
surfaced by ExtractPatternOperator (computed by
agent/dsl_expr/selection.analyze_object_move).
"""

from agent.conditions import register


@register("object_resize_target")
def object_resize_target(patterns: dict, params: dict | None = None) -> bool:
    """True iff every example is a single object moved (color+shape kept) onto a
    constant-sized output canvas that *differs* from the input size, landing at
    one shared target, with enough evidence.

    `params.min_evidence` (default 2) guards against firing on a single pair —
    one example cannot establish that the output size and target are *constant*.
    """
    if not isinstance(patterns, dict):
        return False
    params = params or {}
    min_evidence = params.get("min_evidence", 2)

    move = patterns.get("object_move")
    if not isinstance(move, dict):
        return False
    # Resize is the converse of the size-preserving siblings: it fires only when
    # the canvas changes size, so the four readings stay disjoint.
    if move.get("size_preserved_all"):
        return False
    if move.get("output_dims") is None:
        return False
    if move.get("constant_target") is None:
        return False
    if not (move.get("single_object_all")
            and move.get("color_preserved_all")
            and move.get("shape_preserved_all")):
        return False
    return len(move.get("per_pair") or []) >= min_evidence
