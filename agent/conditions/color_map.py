"""
color_map — R6's *applicability* matcher for the global color-substitution
action (BACKLOG_LOOP.md R6 "training escalation": a general mechanism applied to
real ARC-AGI-2 training tasks, not a per-task detector).

A large family of ARC tasks recolor a grid in place: the output has the *same
shape* as the input and every cell of input color `c` becomes one fixed output
color `map[c]`, the same way in every example pair. The existing families cannot
express this — `constant_output` requires identical outputs, the
`single_object_move_*` matchers gate on a single moving object, and
`recolor_extreme_object` recolors exactly one (size-ranked) object. None
recognise a *global* per-color substitution.

The substitution is itself a comparison result (P3/P4): comparing each pair's
corresponding cells yields, per input color, the single output color it always
becomes — a COMM over the example pairs. When that per-color map is *consistent*
across every pair (no input color maps to two different output colors) and at
least one color actually changes, the task is a global recolor. One
value-agnostic `color_map` rule then covers the whole family: the map is
re-derived from each task's own examples at apply time, never stored as a literal
(§2.5-3), so a *single* rule generalises to unseen recolor tasks rather than
one detector per task.

This is recognition-vocabulary growth (P5), the dimension CLAUDE.md §6.3
blesses; it introduces no new way of *doing* a transformation (the recolor is
the frozen `coloring` primitive applied per source-color group).

Reads the `color_map` signal `ExtractPatternOperator` surfaces:

    patterns["color_map"] = {
        "consistent":     bool,        # the per-color map holds across every pair
                                        #   (same shape in/out, no color->two-colors)
        "color_map":      {int: int},  # the derived input->output color map (None if not consistent)
        "evidence_count": int,
    }

When the pairs change shape or a color maps inconsistently the producer leaves
`consistent` False, so this matcher returns False and cannot misfire on the
move / constant-output / recolor-extreme families (each of which breaks global
map consistency) — it stays dormant there.
"""

from agent.conditions import register


@register("color_map")
def color_map(patterns: dict, params: dict | None = None) -> bool:
    """True iff every example pair is the same shape and realises one consistent
    global input->output color substitution with at least one color changed.

    `params.min_evidence` (default 2) guards against firing on a single example —
    one pair cannot establish "this color always becomes that color" as a rule.
    """
    if not isinstance(patterns, dict):
        return False
    params = params or {}
    min_evidence = params.get("min_evidence", 2)

    sig = patterns.get("color_map")
    if not isinstance(sig, dict):
        return False
    if sig.get("evidence_count", 0) < min_evidence:
        return False
    return bool(sig.get("consistent") and sig.get("color_map"))
