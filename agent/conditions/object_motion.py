"""
object_motion — R1's object-level move matcher (BACKLOG_LOOP.md R1, §2.5-2b).

Fires when every example pair moves *a selected foreground object* to a
destination describable by one value-agnostic *target expression* — a corner
relation, a constant absolute position, or a constant translation — with the
object (colour + shape) preserved. Which object moves is itself a fitted
*selector expression* (`agent/dsl_expr/selection.fit_selector`: unique / largest
/ smallest), so a multi-object input can name which object the rule acts on
without a literal index — the §2.1 multi-object-selection concept. The
destination is likewise fitted from the example comparison
(`agent/dsl_expr/motion.fit_target`), not hard-coded, so a single rule covers the
whole move family (easy000c/g corner, easy000d/h constant, easy000e/f translation,
plus largest/smallest-selected multi-object moves) rather than one detector per
variant — the R1 generalisation of R0's `constant_output`, and the antidote to
the §2.5-3 accretion trap. This *replaces* the earlier corner-only
`object_corner_target` matcher: the corner is now just one of several target
expressions this one matcher recognises.

Reads the `object_motion` signal surfaced by ExtractPatternOperator::

    patterns["object_motion"] = {
        "evidence_count": int,
        "pairs": [ {
            "single_out":  bool,  # exactly one object in G1 (the moved one)
            "selected_ok": bool,  # the moved object was identified in G0
            "color_preserved": bool,
            "size_preserved":  bool,
            "grid_size_preserved": bool,   # informational; resizes are allowed
            ... per-pair geometry (src/dst/H/W/oh/ow) ...
        }, ... ],
        "selector":  {"kind": ...} | None,  # fitted selector expression, or None
        "target":    {"kind": ...} | None,  # fitted target expression, or None
        "out_shape": {"kind": ...} | None,  # fitted output-shape expr, or None
    }

The grid size need not be preserved: a resizing move (easy000i, 6×6 → 5×5) is
still one object_motion as long as the output shape is itself describable by a
value-agnostic expression (`out_shape`). In-place moves fit `out_shape == same`;
an input-relative resize fits `delta`/`constant`; a *crop to the object*, whose
output size is the selected object's own bbox extent, fits `object_extent`; and an
output whose side is the *number of objects* in the input fits `object_count` —
both of the latter the §2.1 "grid size is a function of an object's feature"
concept, read at the object level and the grid level respectively. All the same
one matcher, the destination and the shape both fitted argument expressions.
"""

from agent.conditions import register


@register("object_motion")
def object_motion(patterns: dict, params: dict | None = None) -> bool:
    """True iff every example pair moves an *identified* object (colour + shape
    preserved, single object in the output) AND a selector, a target, and an
    output-shape expression all fit every pair. The input may hold several objects
    — which one moves is named by the fitted selector — and the grid size itself
    may change, captured by the fitted output-shape expression.

    `params.min_evidence` (default 2) guards against concluding any expression
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
            p.get("single_out")
            and p.get("selected_ok")
            and p.get("color_preserved")
            and p.get("size_preserved")
        ):
            return False

    # A selector, a target, and an output-shape expression must all have been
    # fitted across the pairs; absent any, the move is not value-agnostically
    # describable and we decline rather than guess.
    return (
        motion.get("selector") is not None
        and motion.get("target") is not None
        and motion.get("out_shape") is not None
    )
