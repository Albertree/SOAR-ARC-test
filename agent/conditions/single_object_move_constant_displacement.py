"""
single_object_move_constant_displacement — R1's *constant-displacement* filling
matcher for the `place_object` action (BACKLOG_LOOP.md R1, §2.5-2b).

`single_object_move` recognises the move *family* (one foreground object
relocates, colour/shape preserved); `single_object_move_fixed_target` is the
first *filling* of `place_object`'s target hole — the object lands on the **same
cell** across every pair (easy000c/d/h). This module is the **second** filling:
the object moves by the **same displacement** Δ=(dr, dc) across every pair (the
COMM of the per-pair position DIFFs), while landing on *different* cells. That
covers the constant-offset movers (easy000e: Δ=(1,-1); easy000f: Δ=(0,1)).

Under this condition the target is derivable value-agnostically from G0 alone
(P5): `target = position_of(test object) + Δ`, with Δ the COMM of the example
pairs — so `place_object` instantiates and renders via the two frozen primitives
without ever reading the test pair's absent G1.

These two fillings (fixed cell vs constant Δ) are *disjoint* on the supplied
data — a constant landing cell forces a varying Δ and vice-versa — and they are
exactly the shape §2.5-2b/§5(R3) calls for: the same `place_object` skeleton
("select object → erase source → paint at f(target)") differing *only* in the
target function `f`. Once two such fillings coexist, `f` is the single variable
`anti_unification.unify()` (R3) will abstract into one `covers>1` rule; until
then each filling is a value-agnostic rule covering its whole subfamily, not a
per-task literal (§2.5-3). Adding this matcher is recognition-vocabulary growth
(P5, CLAUDE.md §6.3); it introduces no new way of *doing* a transformation.

Reads the `object_transition` signal surfaced by ExtractPatternOperator:

    patterns["object_transition"] = {
        ...,                          # all_single / color_preserved / ... (base move family)
        "displacement_constant": bool,    # every pair shares one (dr, dc)
        "displacement":          (dr, dc),# that displacement, or None
        "outsize_preserved":     bool,    # every pair: output grid size == input grid size
    }
"""

from agent.conditions import register


@register("single_object_move_constant_displacement")
def single_object_move_constant_displacement(patterns: dict, params: dict | None = None) -> bool:
    """True iff every example pair relocates a single colour/shape-preserved
    object by the *same* displacement Δ, with the grid size preserved.

    `params.min_evidence` (default 2) guards against firing on a single example —
    one pair cannot establish "the displacement is always Δ" as the rule.
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
        and transition.get("displacement_constant")
        and transition.get("outsize_preserved")
    )
