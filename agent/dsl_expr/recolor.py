"""
recolor — colour-source *expressions* for in-place object recolouring
(BACKLOG_LOOP.md R1, §2.5-2b).

A recolour keeps an object's cells fixed and changes its colour. Like every
transformation in ARBOR it is built from the two frozen primitives (make_grid +
coloring); its only free argument — the object's *new colour* — is never a
literal baked per task. It is the colour of another object named by a
value-agnostic *selector expression* (the same selection vocabulary that names
which object moves, `agent/dsl_expr/selection.py`). Fitting BOTH which object is
recoloured (the *target* selector, via `fit_selector`) and whose colour it takes
(the *source* selector, via `fit_color_source` here) from the example comparison
(P3/P4) keeps one rule covering the family, and lets two recolour tasks whose
(target, source) selectors diverge anti-unify into one covers>1 rule (R3,
`agent/memory.save_rule` -> `program.anti_unification.unify`).

The new colour is therefore an *argument expression* — `color_of(select_object(
inputs, source))` — not a stored colour value, so the rule stays value-agnostic
and computable from G0 alone at test time (P5).
"""

from agent.dsl_expr.selection import select_object, color_of, _SELECTOR_KINDS


def fit_color_source(sources):
    """Fit a value-agnostic colour-source selector across example pairs.

    `sources` is a list of per-pair dicts ``{"objects": [...], "color": int}``
    where ``objects`` are the input objects (from `objects_of`) and ``color`` is
    the recoloured object's *new* colour. Returns a selector descriptor naming the
    object whose single colour equals that new colour in *every* pair, or ``None``
    if none fits (so the matcher declines rather than guessing). Tried
    most-structural first, mirroring `fit_selector`'s ordering. Never returns a
    literal colour — the colour is always read from a fitted source object at
    predict time, keeping the rule value-agnostic and G0-computable (P5).
    """
    if not sources:
        return None
    for kind in _SELECTOR_KINDS:
        ok = True
        for s in sources:
            obj = select_object(s["objects"], {"kind": kind})
            if obj is None or color_of(obj) != s["color"]:
                ok = False
                break
        if ok:
            return {"kind": kind}
    return None


def color_source(descriptor, objects):
    """Resolve a colour-source descriptor to a concrete colour for one input grid:
    the single colour of the object the descriptor's selector picks. Returns
    ``None`` when the selector picks no object (or a multi-coloured one), so
    callers decline rather than crash. Inverse-paired with `fit_color_source`."""
    if not descriptor:
        return None
    obj = select_object(objects, descriptor)
    if obj is None:
        return None
    return color_of(obj)
