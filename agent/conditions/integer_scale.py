"""
integer_scale — the *applicability* matcher for the constant-factor block-upscale
action (BACKLOG_LOOP.md R6 "training escalation": a general mechanism applied to
real ARC-AGI-2 training tasks, not a per-task detector).

A family of ARC tasks enlarges a grid by a constant integer factor: each input
cell becomes a `kh x kw` block of that same colour, so the output is the input
"zoomed in" by `(kh, kw)` with no other change. The existing families cannot
express this — every one of them either keeps the grid's shape
(`constant_output` needs identical outputs, `color_map` is an in-place per-colour
recolor, `recolor_extreme_object` recolors one object) or moves a *single* object
(`single_object_move_*` gate on `all_single`). None recognise a whole-grid
enlargement.

The factor is itself a comparison result (P3/P4): comparing each pair's input and
output dimensions yields `(kh, kw) = (out_h / in_h, out_w / in_w)`, and verifying
`out[R][C] == in[R // kh][C // kw]` confirms the enlargement is a pure block
tiling. When that factor is the *same* across every example pair (a COMM over the
pairs) and is a genuine enlargement (not the identity `(1, 1)`), the task is an
integer upscale. One value-agnostic `integer_scale` rule then covers the whole
family: the factor is re-derived from each task's own examples at apply time,
never stored as a literal (§2.5-3), so a *single* rule generalises to unseen
upscale tasks rather than one detector per task.

This is recognition-vocabulary growth (P5), the dimension CLAUDE.md §6.3
blesses; it introduces no new way of *doing* a transformation (the enlargement is
the frozen `make_grid` canvas painted by the frozen `coloring` per block).

Reads the `integer_scale` signal `ExtractPatternOperator` surfaces:

    patterns["integer_scale"] = {
        "consistent":     bool,            # one (kh, kw) >= (1,1), != (1,1), is a
                                            #   pure block upscale of every pair
        "factor":         (int, int)|None, # the derived (kh, kw) (None if not consistent)
        "evidence_count": int,
    }

When the pairs disagree on the factor, change shape non-divisibly, or merely keep
shape, the producer leaves `consistent` False, so this matcher returns False and
cannot misfire on the recolor / move / constant-output families — it stays
dormant there.
"""

from agent.conditions import register


@register("integer_scale")
def integer_scale(patterns: dict, params: dict | None = None) -> bool:
    """True iff every example pair is the same constant integer block-upscale of
    its input by one factor `(kh, kw)` that genuinely enlarges the grid.

    `params.min_evidence` (default 2) guards against firing on a single example —
    one pair cannot establish "the factor is always this" as a rule.
    """
    if not isinstance(patterns, dict):
        return False
    params = params or {}
    min_evidence = params.get("min_evidence", 2)

    sig = patterns.get("integer_scale")
    if not isinstance(sig, dict):
        return False
    if sig.get("evidence_count", 0) < min_evidence:
        return False
    return bool(sig.get("consistent") and sig.get("factor"))
