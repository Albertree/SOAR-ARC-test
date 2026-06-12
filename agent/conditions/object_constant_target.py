"""
object_constant_target — R1's recognition matcher (BACKLOG_LOOP.md R1).

Fires when, across every example pair, a *single* foreground object is moved —
color and shape preserved (the per-pair COMM), only position differs (the DIFF)
— to the **same** output anchor (the cross-pair COMM on the output position),
on a same-size canvas. This is the object-level lift of R0's COMM-copy: the
answer is value-agnostic in both the object's color and its source position; the
only learned argument is the constant target, recomputed at predict time.

It recognizes the constant-target move family value-agnostically: easy000c (→
(5,5)), easy000d (→ (1,2)), easy000h (→ (4,4)) all satisfy it, so a single rule
covers them (one module, many targets — the §2.5-3/4 generalization direction).
It deliberately abstains on the *relative*/corner/resize variants (easy000e/f/g/i)
whose output anchor is not constant across pairs — those need R3 lifting or a
relation expression, not this matcher.

Reads the `object_move` signal surfaced by ExtractPatternOperator (computed by
agent/dsl_expr/selection.analyze_object_move).
"""

from agent.conditions import register


@register("object_constant_target")
def object_constant_target(patterns: dict, params: dict | None = None) -> bool:
    """True iff every example is a single object moved (color+shape kept, size
    preserved) to one shared output anchor, with enough evidence.

    `params.min_evidence` (default 2) guards against firing on a single pair —
    one example cannot establish that the target is *constant*.
    """
    if not isinstance(patterns, dict):
        return False
    params = params or {}
    min_evidence = params.get("min_evidence", 2)

    move = patterns.get("object_move")
    if not isinstance(move, dict):
        return False
    if move.get("constant_target") is None:
        return False
    if not (move.get("single_object_all")
            and move.get("color_preserved_all")
            and move.get("shape_preserved_all")
            and move.get("size_preserved_all")):
        return False
    return len(move.get("per_pair") or []) >= min_evidence
