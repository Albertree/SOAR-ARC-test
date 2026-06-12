"""
single_object_move_fixed_target — R1's *applicability* matcher for the
fixed-cell filling of the `place_object` action (BACKLOG_LOOP.md R1, §2.5-2b).

`single_object_move` recognises the move *family* — a single foreground object
relocates, colour and shape preserved. But recognising "an object moves" does
not yet say *where* it lands: the `place_object` action carries a target
**variable**, and §2.5-2b is explicit that an abstraction with a hole is
*incomplete until the hole has a filling rule*. This matcher is the first such
filling rule's precondition: it fires only when the object lands on the **same
cell across every example pair** (the COMM of the example-output positions) and
the output grid keeps the input grid's size. Under that condition the target is
derivable value-agnostically — `target = position_of(unique(objects_of(G1)))`,
constant across pairs — so `place_object` can be instantiated and rendered via
the two frozen primitives.

This is a *general* recognition predicate, not a per-task detector: it fires on
any task whose moving object always lands on one fixed cell (easy000c/d/h), and
declines the relative-displacement (e/f), relative-corner (g) and resized (i)
members — those need different fillings, each a future matcher of the same
shape, and ultimately the variable R3's anti-unification abstracts. Adding it is
recognition vocabulary growth (P5), the dimension CLAUDE.md §6.3 blesses; it
introduces no new way of *doing* a transformation.

Reads the `object_transition` signal surfaced by ExtractPatternOperator:

    patterns["object_transition"] = {
        ...,                          # all_single / color_preserved / ... (the base move family)
        "target_constant":   bool,    # every G1 object at the same (row, col)
        "target_cell":       (r, c),  # that cell, or None
        "outsize_preserved": bool,    # every pair: output grid size == input grid size
    }
"""

from agent.conditions import register


@register("single_object_move_fixed_target")
def single_object_move_fixed_target(patterns: dict, params: dict | None = None) -> bool:
    """True iff every example pair relocates a single colour/shape-preserved
    object onto the *same* fixed cell, with the grid size preserved.

    `params.min_evidence` (default 2) guards against firing on a single example —
    one pair cannot establish "the object always lands on this cell" as the rule.
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
        and transition.get("target_constant")
        and transition.get("outsize_preserved")
    )
