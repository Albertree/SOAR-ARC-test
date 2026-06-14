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

The new colour is therefore an *argument expression*. Two readings, tried
most-structural first (mirroring `motion.fit_target`'s corner/offset/constant
ordering):

  1. ``color_of(select_object(inputs, source))`` — the colour of another object
     named by a value-agnostic selector (most structural; the colour is read from
     a fitted source object at predict time, so the rule needs no stored value).
  2. ``constant(c)`` — a single colour the recolour lands on in *every* example,
     fitted (not hand-coded) from the agreement of the example outputs, exactly
     as `constant_output` (R0) fits the common output grid. Used only when no
     source object carries the new colour (e.g. the target colour appears on no
     input object). Value-agnostic in the same sense `constant_output` is: the
     constant is re-fitted from each task's own examples at solve time and never
     baked into Python; it is supplied by the training examples, not the test
     input, so it does not require test G1 (P5).
"""

from agent.dsl_expr.selection import select_object, color_of, _SELECTOR_KINDS


def fit_color_source(sources):
    """Fit a value-agnostic colour source across example pairs.

    `sources` is a list of per-pair dicts ``{"objects": [...], "color": int}``
    where ``objects`` are the input objects (from `objects_of`) and ``color`` is
    the recoloured object's *new* colour. Returns a descriptor, or ``None`` if
    neither reading fits (so the matcher declines rather than guessing):

      - ``{"kind": <selector>}`` when some selector names the object whose single
        colour equals the new colour in *every* pair (tried first, most structural);
      - ``{"kind": "constant", "color": c}`` when the new colour is the same ``c``
        in every pair (the constant fallback — tried only after every selector
        fails, so a source-object reading always wins where it applies and existing
        recolour tasks are unaffected).
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
    # Fallback: the new colour is a single constant agreed across all pairs.
    colors = {s["color"] for s in sources}
    if len(colors) == 1:
        return {"kind": "constant", "color": next(iter(colors))}
    return None


def color_source(descriptor, objects):
    """Resolve a colour-source descriptor to a concrete colour for one input grid.
    For a selector descriptor, the single colour of the object it picks; for a
    ``constant`` descriptor, the fitted constant colour directly. Returns ``None``
    when a selector picks no object (or a multi-coloured one), so callers decline
    rather than crash. Inverse-paired with `fit_color_source`."""
    if not descriptor:
        return None
    if descriptor.get("kind") == "constant":
        return descriptor.get("color")
    obj = select_object(objects, descriptor)
    if obj is None:
        return None
    return color_of(obj)
