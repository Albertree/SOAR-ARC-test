"""
single_object_move_relative_corner — R1's *relative-corner* filling matcher for
the `place_object` action (BACKLOG_LOOP.md R1, §2.5-2b).

This is the **third** filling of `place_object`'s target hole, after
`single_object_move_fixed_target` (object lands on the same *cell*, easy000c/d/h)
and `single_object_move_constant_displacement` (object moves by a constant Δ,
easy000e/f). Here the object lands on the same *corner* of the grid across every
pair — the same anchor formula (e.g. bottom-right = (H-1, W-1)) resolving to a
*different cell* in each differently-sized grid. That covers the corner movers
whose grids differ in size (easy000g: bottom-right, 4×4 / 3×5 / 6×4).

Why it is its own filling and not the fixed-target one: a fixed landing *cell*
is constant only when the grids are the same size; when the grids differ in size
(as in easy000g) the landing cell varies, so `single_object_move_fixed_target`
correctly declines — but the *corner* is invariant. The target is still derivable
value-agnostically from the examples (P5): the common corner is the COMM of
`corners_at(position_of(output object), H, W)` across pairs, applied to the test
grid's own bounds — so `place_object` instantiates and renders via the two frozen
primitives without ever reading the test pair's absent G1, and without storing
any task's literal coordinate.

Relation to the prior two fillings: disjoint from constant-displacement on the
supplied data (a corner that tracks the grid bounds gives a varying Δ across
different-sized grids). It *overlaps* fixed-target only in the same-size case,
where a corner cell is also a constant cell (easy000c, all 6×6, lands on
(5,5)=bottom-right); that overlap is harmless because GeneralizeOperator checks
fixed-target first, so same-size corner movers route to the fixed rule and only
the genuinely size-varying case (easy000g) reaches this filling. It is the same
`place_object` skeleton ("select object → erase source → paint at f(target)")
differing *only* in the target function `f` — so once it coexists with the other
fillings, `f` is the single variable `anti_unification.unify()` (R3) abstracts;
in fact `save_rule`'s subsumption folds this filling straight into the existing
`?v1` abstraction's `covers` (no new rule — P1/P2 rise without accretion,
§2.5-4). Adding this matcher is recognition-vocabulary growth (P5, CLAUDE.md
§6.3); it introduces no new way of *doing* a transformation.

Reads the `object_transition` signal surfaced by ExtractPatternOperator:

    patterns["object_transition"] = {
        ...,                          # all_single / color_preserved / ... (base move family)
        "corner_constant": bool,      # every pair: output object on the same corner
        "corner":          str,       # that corner id (tl/tr/bl/br), or None
        "outsize_preserved": bool,    # every pair: output grid size == input grid size
    }
"""

from agent.conditions import register


@register("single_object_move_relative_corner")
def single_object_move_relative_corner(patterns: dict, params: dict | None = None) -> bool:
    """True iff every example pair relocates a single colour/shape-preserved
    object onto the *same grid corner*, with a derivable output grid size.

    The corner is resolved against each output grid's own bounds, so it stays
    invariant whether the output keeps the input's size (`outsize_preserved`,
    easy000g) **or** the output resizes to a constant size (`outsize_constant`,
    easy000i 6×6->5×5). Both readings let the render re-derive the output dims
    value-agnostically (`dsl_expr.output_dims`) and resolve the corner against
    *those* bounds; the resize is therefore the same corner filling, not a new
    one — it folds into `place_object`'s `?v1` abstraction exactly as the
    size-preserved corner did (covers grows, no new rule, §2.5-4). The size-
    varying-but-preserved case and the resized-but-constant case are the two
    disjuncts; a task with neither (output dims neither preserved nor constant)
    is not yet derivable and correctly declines.

    `params.min_evidence` (default 2) guards against firing on a single example —
    one pair cannot establish "the object always lands on corner X" as the rule.
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
        and transition.get("corner_constant")
        and (transition.get("outsize_preserved") or transition.get("outsize_constant"))
    )
