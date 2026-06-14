"""
object_corner_target — R1's first object-level matcher (BACKLOG_LOOP.md R1).

Fires when every example pair moves *the single foreground object* to the grid's
**bottom-right corner**, preserving the object (same colour, same shape) and the
grid size. The target position is not a literal — it is the *argument expression*
`(H-1, W-1)`, relative to each grid's own size, so one value-agnostic rule covers
tasks of different grid sizes (easy000c, 6×6 → corner; easy000g, 4×4 / 3×5 / 6×4
→ corner). This is the R1 analogue of R0's `constant_output`: a single module for
a whole family, recognized by a lifted selection, not one detector per task
(arbor-flow prose; §2.5-3).

Reads the `object_motion` signal surfaced by ExtractPatternOperator:

    patterns["object_motion"] = {
        "evidence_count": int,
        "pairs": [ {
            "single_in":       bool,   # exactly one object in G0
            "single_out":      bool,   # exactly one object in G1
            "color_preserved": bool,   # object colour unchanged G0 -> G1
            "size_preserved":  bool,   # object cell count unchanged
            "grid_size_preserved": bool,
            "out_at_corner":   bool,   # out object's bbox bottom-right == (H-1, W-1)
        }, ... ]
    }
"""

from agent.conditions import register


@register("object_corner_target")
def object_corner_target(patterns: dict, params: dict | None = None) -> bool:
    """True iff every example pair is a single-object move to the bottom-right
    corner with the object and grid size preserved.

    `params.min_evidence` (default 2) guards against concluding "always the
    corner" from a single pair.
    """
    if not isinstance(patterns, dict):
        return False
    params = params or {}
    min_evidence = params.get("min_evidence", 2)

    motion = patterns.get("object_motion")
    if not isinstance(motion, dict):
        return False
    pairs = motion.get("pairs")
    if not isinstance(pairs, list) or len(pairs) < min_evidence:
        return False

    for p in pairs:
        if not isinstance(p, dict):
            return False
        if not (
            p.get("single_in")
            and p.get("single_out")
            and p.get("color_preserved")
            and p.get("size_preserved")
            and p.get("grid_size_preserved")
            and p.get("out_at_corner")
        ):
            return False
    return True
