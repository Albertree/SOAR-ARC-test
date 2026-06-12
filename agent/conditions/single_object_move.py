"""
single_object_move — R1's recognition matcher (BACKLOG_LOOP.md R1).

Fires when every example pair has exactly one foreground object in both input
and output, the object's color and shape are preserved, and only its position
changes. This is the symbolic COMM/DIFF of the move family: COMM on color and
size, DIFF on position — the object is *relocated*, not transformed.

It recognizes the easy000c–i family value-agnostically: a single 1×1 (or larger)
object that moves to a fixed cell (c–f), to a relative corner (g, h), or across a
resized grid (i). One matcher covers them all; the differing target position is
not part of recognition — it is derived later, at apply time, from each task's
own object positions (the lift R3 unifies, §2.5-2b). No per-task literal, no
hand-coded detector.

Reads the `object_transition` signal surfaced by ExtractPatternOperator, which
selects the object via the seed vocabulary `unique(objects_of(G))` and reads it
via `color_of`/`size_of`/`position_of`:

    patterns["object_transition"] = {
        "all_single":      bool,   # one fg object in every G0 and G1
        "color_preserved": bool,   # color_of(G0) == color_of(G1) every pair
        "shape_preserved": bool,   # size_of(G0)  == size_of(G1)  every pair
        "moved":           bool,   # position changed every pair
        "evidence_count":  int,
    }
"""

from agent.conditions import register


@register("single_object_move")
def single_object_move(patterns: dict, params: dict | None = None) -> bool:
    """True iff every example pair relocates a single color/shape-preserved object.

    `params.min_evidence` (default 2) guards against firing on a single example —
    one pair cannot establish that "the object always moves" is the rule.
    """
    if not isinstance(patterns, dict):
        return False
    params = params or {}
    min_evidence = params.get("min_evidence", 2)

    transition = patterns.get("object_transition")
    if not isinstance(transition, dict):
        return False
    if transition.get("evidence_count", 0) < min_evidence:
        return False
    return bool(
        transition.get("all_single")
        and transition.get("color_preserved")
        and transition.get("shape_preserved")
        and transition.get("moved")
    )
