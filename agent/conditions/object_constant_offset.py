"""
object_constant_offset — R1's relative-move recognition matcher (BACKLOG_LOOP.md
R1, the easy000e/f next-gap from iter 3).

Sibling of object_constant_target. Where that matcher fires when the *absolute*
output anchor is shared across examples (fixed-target move), this one fires when
the *displacement* ``out_pos − in_pos`` is shared across examples (fixed-offset
move): a single foreground object, color/shape/size preserved (the per-pair
COMM), moved by one constant vector (the cross-pair COMM on the relative
displacement) on a same-size canvas. The answer is value-agnostic in the
object's color and its source position; the only learned argument is the
constant offset, recomputed at predict time and added to each test object's own
anchor.

It deliberately abstains when the absolute target is itself constant
(``constant_target`` set) so the two move families stay disjoint and the
fixed-target reading takes priority — that degenerate overlap only arises when
the source anchor is also fixed, which the easy_a suite never does. It abstains
on the corner/resize variants (easy000g/i) whose offset is not constant across
pairs — those need a relation expression or grid resize, not this matcher.

Reads the `object_move` signal surfaced by ExtractPatternOperator (computed by
agent/dsl_expr/selection.analyze_object_move).
"""

from agent.conditions import register


@register("object_constant_offset")
def object_constant_offset(patterns: dict, params: dict | None = None) -> bool:
    """True iff every example is a single object moved by one shared
    displacement (color+shape kept, size preserved), with enough evidence and
    no constant absolute target (which the sibling matcher claims first).

    `params.min_evidence` (default 2) guards against firing on a single pair —
    one example cannot establish that the offset is *constant*.
    """
    if not isinstance(patterns, dict):
        return False
    params = params or {}
    min_evidence = params.get("min_evidence", 2)

    move = patterns.get("object_move")
    if not isinstance(move, dict):
        return False
    if move.get("constant_offset") is None:
        return False
    if move.get("constant_target") is not None:
        return False
    if not (move.get("single_object_all")
            and move.get("color_preserved_all")
            and move.get("shape_preserved_all")
            and move.get("size_preserved_all")):
        return False
    return len(move.get("per_pair") or []) >= min_evidence
