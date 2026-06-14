"""
object_motion — R1's object-level move matcher (BACKLOG_LOOP.md R1, §2.5-2b).

Fires when every example pair moves *the single foreground object* to a
destination describable by one value-agnostic *target expression* — a corner
relation, a constant absolute position, or a constant translation — with the
object (colour + shape) and the grid size preserved. The destination is fitted
from the example comparison (`agent/dsl_expr/motion.fit_target`), not hard-coded,
so a single rule covers the whole move family (easy000c/g corner, easy000d/h
constant, easy000e/f translation) rather than one detector per variant — the R1
generalisation of R0's `constant_output`, and the antidote to the §2.5-3
accretion trap. This *replaces* the earlier corner-only `object_corner_target`
matcher: the corner is now just one of several target expressions this one
matcher recognises.

Reads the `object_motion` signal surfaced by ExtractPatternOperator::

    patterns["object_motion"] = {
        "evidence_count": int,
        "pairs": [ {
            "single_in":  bool,   # exactly one object in G0
            "single_out": bool,   # exactly one object in G1
            "color_preserved": bool,
            "size_preserved":  bool,
            "grid_size_preserved": bool,   # informational; resizes are allowed
            ... per-pair geometry (src/dst/H/W/oh/ow) ...
        }, ... ],
        "target":    {"kind": ...} | None,  # fitted target expression, or None
        "out_shape": {"kind": ...} | None,  # fitted output-shape expr, or None
    }

The grid size need not be preserved: a resizing move (easy000i, 6×6 → 5×5) is
still one object_motion as long as the output shape is itself describable by a
value-agnostic expression (`out_shape`). In-place moves fit `out_shape == same`.
"""

from agent.conditions import register


@register("object_motion")
def object_motion(patterns: dict, params: dict | None = None) -> bool:
    """True iff every example pair is a single-object move with the object
    (colour + shape) preserved AND both a target expression and an output-shape
    expression fit all pairs. The grid size itself may change — that is captured
    by the fitted output-shape expression, not required to be constant.

    `params.min_evidence` (default 2) guards against concluding either expression
    from a single pair.
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
        ):
            return False

    # Both a target expression and an output-shape expression must have been
    # fitted across the pairs; absent either, the move is not value-agnostically
    # describable and we decline rather than guess.
    return (
        motion.get("target") is not None
        and motion.get("out_shape") is not None
    )
