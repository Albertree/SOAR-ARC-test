"""
synthesis — bounded Slow-path program synthesizer (modules F/G substrate).

The hand-coded family matchers in ``agent/active_operators.py`` each *recognize*
ONE transformation shape and emit a ``place_object`` / ``recolor_object`` /
``copy_common_output`` rule. None of them SEARCH; a transformation outside the
recognized shapes produces no program at all. That is exactly what the training
probe shows — on real ARC, **zero** matchers fire, so the Slow path emits nothing
(``run_learn.py --split training`` → ``+0 learned``). The user's design
(``arbor.md`` Fast/Slow path; ``arbor-modules.md`` modules F/G) calls for a
general Slow-path *synthesizer*: given the example pairs of a task, SEARCH a
bounded space of programs built from the **two frozen transformation primitives**
(``make_grid``, ``coloring``) and return one program that reproduces every train
output from its input.

This module is the live Slow-path synthesizer. It searches a bounded space of
``make_grid``/``coloring`` compositions: identity, constant/common output, object
reconstruction onto a fitted canvas, and **global colour substitution** (a
shape-preserved cell-wise recolour expressed as one ``coloring(cells_with_color
(c), f(c))`` step per changed colour — the general case no single-colour
``object_recolor`` family fits). Two tasks whose searched programs share a schema
but diverge in fitted leaves are lifted by ``anti_unification.unify()`` into one
``covers>1`` rule (R3); distinct schemas stay distinct rule families
(``agent/memory.py:_program_skeleton``).

Design contract:

* A program is a list of *steps*; every step is one of the two frozen primitives.
  ``run_program`` evaluates a program against an input grid via ``apply_DSL`` — it
  adds **no** transformation vocabulary (F3): it only *composes* the two.
* A step's arguments are *expressions* resolved from the input grid at run time,
  **not** literals keyed to a single pair — except where the transformation is
  provably input-independent (the constant/common-output case, where the literal
  output *is* the reason; ``arbor`` 진단, rule_001's ``copy_common_output``). This
  is the §2.5-2 discipline: literal per-pair coordinate programs are the 168-rule
  failure mode and do not anti-unify; expression programs do.
* Because every variable originates in the input grid (P5: variables come from
  G0, test has no G1), a program synthesized from the train pairs runs unchanged
  on the held-out test input.

``synthesize_task(pairs)`` returns one program consistent across *all* train
pairs (the task program), or ``None`` when the bounded search finds none — it does
not hand-wave a literal per-pair fit, so a miss is reported honestly.
"""

from procedural_memory.DSL.apply import apply_DSL
from agent.dsl_expr.selection import objects_of, background_of, color_of


# ======================================================================
# Expression evaluation
# ======================================================================
#
# An expression is a tuple ``(op, *args)`` resolved against an ``env`` carrying
# the *input* grid and its objects. Steps build the output canvas; expressions
# always read the input (P5 — every variable originates in G0), so a program
# transfers unchanged to the test input.

class _Unevaluable(Exception):
    """Raised when an expression cannot be resolved against an input (e.g. a
    selector that names no object). The search treats it as "this candidate does
    not apply here" rather than crashing — renderers must decline, not raise
    (memory: runtime_resolvable_speculative_apply)."""


def _eval(expr, env):
    """Resolve a value expression against ``env = {"grid", "objs", "bg"}``."""
    op = expr[0]
    if op == "const":
        return expr[1]
    if op == "bg":
        return env["bg"]
    if op == "in_h":
        return len(env["grid"])
    if op == "in_w":
        return len(env["grid"][0]) if env["grid"] else 0
    if op == "all_objects":
        return env["objs"]
    if op == "cells":
        objs = _eval(expr[1], env)
        if isinstance(objs, dict):
            objs = [objs]
        out = []
        for o in objs:
            out.extend(sorted(o["cells"]))
        return out
    if op == "color_of":
        o = _eval(expr[1], env)
        if isinstance(o, list):
            raise _Unevaluable("color_of expects a single object")
        col = color_of(o)
        if col is None:
            raise _Unevaluable("object has no single colour")
        return col
    if op == "cells_with_color":
        # All input cells holding a given colour. Reads the *input* grid (env is
        # fixed to the input — P5), so a colour-substitution program transfers
        # unchanged to the test input, and `coloring` selections never cascade off
        # the running canvas (the value is read from the original input, not the
        # partially-recoloured output).
        target = _eval(expr[1], env)
        grid = env["grid"]
        return [(r, c) for r, row in enumerate(grid)
                for c, v in enumerate(row) if v == target]
    raise _Unevaluable(f"unknown expression op: {op!r}")


# ======================================================================
# Program evaluation
# ======================================================================

def contains_variable(obj) -> bool:
    """True iff ``obj`` carries an anti-unification variable (a ``?vN`` string)
    anywhere in its term tree.

    A program lifted by :func:`program.anti_unification.unify` (two synthesizer
    tasks whose programs share a skeleton but differ in a leaf — e.g. the fitted
    output dim) holds ``?vN`` holes at the divergent positions. Such an *abstract*
    program is not directly runnable: the holes are re-filled per task by
    re-synthesizing on that task's own pairs (the Slow path), so a stored abstract
    synthesizer rule must *decline* the fast path rather than try to execute a hole
    (memory: runtime_resolvable_speculative_apply — renderers decline, not crash).
    """
    if isinstance(obj, str):
        return obj.startswith("?v")
    if isinstance(obj, (list, tuple)):
        return any(contains_variable(e) for e in obj)
    if isinstance(obj, dict):
        return any(contains_variable(e) for e in obj.values())
    return False


def run_program(program, input_grid):
    """Evaluate ``program`` (a list of steps) against ``input_grid``.

    Steps run in order, each producing the next working canvas. An empty program
    is the identity. Returns the produced grid, or raises ``_Unevaluable`` if a
    step's argument expression does not resolve against this input — including the
    case of an *abstract* program still carrying ``?vN`` variables (see
    :func:`contains_variable`).
    """
    if contains_variable(program):
        raise _Unevaluable(
            "program carries unbound anti-unification variables (?v) — an abstract "
            "rule, re-synthesized per task on the Slow path, not directly runnable"
        )
    env = {
        "grid": input_grid,
        "objs": objects_of(input_grid),
        "bg": background_of(input_grid),
    }
    cur = [row[:] for row in input_grid]
    for step in program:
        kind = step[0]
        if kind == "make_grid":
            _, h_expr, w_expr, color_expr = step
            cur = apply_DSL(
                "make_grid",
                height=_eval(h_expr, env),
                width=_eval(w_expr, env),
                color=_eval(color_expr, env),
            )
        elif kind == "coloring":
            _, selection_expr, color_expr = step
            cur = apply_DSL(
                "coloring", cur,
                selection=_eval(selection_expr, env),
                color=_eval(color_expr, env),
            )
        elif kind == "paint_objects":
            # Aggregate over every input object: paint each object's cells in its
            # own colour. ONE structure-agnostic step (it does not enumerate a
            # fixed object count), so the same program is consistent across pairs
            # whose object counts differ — the property a literal per-object
            # program lacks.
            _, objset_expr = step
            objs = _eval(objset_expr, env)
            for o in objs:
                col = color_of(o)
                if col is None:
                    # Multi-colour blob: paint each cell its own colour. Still
                    # value-agnostic (colour read from the object, not a literal).
                    for (r, c), v in sorted(o["pixels"].items()):
                        cur = apply_DSL("coloring", cur, selection=(r, c), color=v)
                else:
                    cur = apply_DSL(
                        "coloring", cur, selection=sorted(o["cells"]), color=col)
        else:
            raise _Unevaluable(f"unknown step kind: {kind!r}")
    return cur


# ======================================================================
# Search
# ======================================================================

def _fit_dim(values_in, values_out):
    """Return a dim *expression* that maps each pair's input dim to its output
    dim, or ``None`` if no single expression fits all pairs.

    Tries the value-agnostic forms first (output == input dim), then a shared
    constant. This is how a resize is expressed without a per-pair literal.
    """
    if all(o == i for i, o in zip(values_in, values_out)):
        return ("in_h",) if values_in and values_out else ("const", 0)
    if len(set(values_out)) == 1:
        return ("const", values_out[0])
    return None


def _fit_dim_pair(pairs):
    """Fit ``(height_expr, width_expr)`` for the output canvas across all pairs."""
    in_h = [len(p["input"]) for p in pairs]
    in_w = [len(p["input"][0]) if p["input"] else 0 for p in pairs]
    out_h = [len(p["output"]) for p in pairs]
    out_w = [len(p["output"][0]) if p["output"] else 0 for p in pairs]

    h_expr = ("in_h",) if all(o == i for i, o in zip(in_h, out_h)) else (
        ("const", out_h[0]) if len(set(out_h)) == 1 else None)
    w_expr = ("in_w",) if all(o == i for i, o in zip(in_w, out_w)) else (
        ("const", out_w[0]) if len(set(out_w)) == 1 else None)
    return h_expr, w_expr


def _candidate_programs(pairs):
    """Yield candidate task programs (value-agnostic where the schema allows),
    derived structurally from the pairs. Each is validated against *all* pairs by
    :func:`synthesize_task` before being returned, so a candidate that does not
    generalize is simply discarded."""
    # --- Schema 1: identity -------------------------------------------------
    yield []

    h_expr, w_expr = _fit_dim_pair(pairs)

    # --- Schema 2: constant / common output --------------------------------
    # All outputs identical → the transformation is input-independent; reproduce
    # the common grid as make_grid + per-colour colorings. The literal here is
    # justified (the output does not depend on the input — rule_001's
    # copy_common_output, rediscovered as an explicit program). Reason: P3/P4 —
    # "all example outputs are equal" is the comparison result that grounds it.
    outs = [p["output"] for p in pairs]
    if all(o == outs[0] for o in outs):
        g = outs[0]
        ho, wo = len(g), (len(g[0]) if g else 0)
        prog = [("make_grid", ("const", ho), ("const", wo), ("const", 0))]
        # Group the non-zero cells by colour so each colour is one coloring step.
        by_color = {}
        for r in range(ho):
            for c in range(wo):
                v = g[r][c]
                if v != 0:
                    by_color.setdefault(v, []).append((r, c))
        for col in sorted(by_color):
            prog.append(("coloring", ("const", by_color[col]), ("const", col)))
        yield prog

    # --- Schema 3: object reconstruction onto a fitted canvas --------------
    # Rebuild every input object, in its own colour, at its own position, on a
    # blank canvas whose size is the fitted (in-dim / constant) expression. This
    # covers identity, recolour-to-background-canvas, and pad/resize-preserving
    # tasks with a single structure-agnostic program (paint_objects loops over
    # whatever objects the input has).
    if h_expr is not None and w_expr is not None:
        yield [
            ("make_grid", h_expr, w_expr, ("bg",)),
            ("paint_objects", ("all_objects",)),
        ]

    # --- Schema 4: global colour substitution ------------------------------
    # A shape-preserved, cell-wise recolour: a single colour map ``c -> f(c)``
    # holds across *every* pair (the reason — P3/P4 — is the COMM result "the
    # same colour always becomes the same colour"). Expressed as one `coloring`
    # step per *changed* colour, painting that colour's input cells in their
    # mapped colour. Distinct colours may map to distinct colours, so this is the
    # general case no single-colour `object_recolor` family fits — and, being a
    # pure (`cells_with_color`, `const`) skeleton, two such tasks with divergent
    # maps lift via `unify()` into one covers>1 rule (R3). The selections read the
    # fixed input (see `cells_with_color`), so map order is irrelevant.
    prog = _fit_color_map(pairs)
    if prog is not None:
        yield prog


def _fit_color_map(pairs):
    """Return a colour-substitution program (one `coloring` per changed colour),
    or ``None`` if the pairs are not a shape-preserved consistent recolour.

    A pair is eligible only when input and output have identical dimensions; a
    single colour map must then be consistent across *all* cells of *all* pairs.
    Only colours that actually change emit a step (an all-identity map is the
    identity schema, already yielded)."""
    cmap = {}
    for p in pairs:
        gin, gout = p["input"], p["output"]
        if len(gin) != len(gout):
            return None
        for ri, ro in zip(gin, gout):
            if len(ri) != len(ro):
                return None
            for a, b in zip(ri, ro):
                if cmap.get(a, b) != b:
                    return None  # inconsistent map → not a global recolour
                cmap[a] = b
    changed = sorted(c for c, t in cmap.items() if c != t)
    if not changed:
        return None
    return [
        ("coloring", ("cells_with_color", ("const", c)), ("const", cmap[c]))
        for c in changed
    ]


def synthesize_task(pairs):
    """Search for one program reproducing **every** train pair's output from its
    input. Returns the program (a list of steps) or ``None``.

    ``pairs`` is a list of ``{"input": grid, "output": grid}`` dicts (the
    standard ARC train slice). The returned program is value-agnostic (every
    argument resolves from an input grid), so it applies unchanged to the test
    input. A ``None`` result is honest: the bounded search found no general
    program — it never falls back to a literal per-pair fit.
    """
    if not pairs:
        return None
    for prog in _candidate_programs(pairs):
        ok = True
        for p in pairs:
            try:
                if run_program(prog, p["input"]) != p["output"]:
                    ok = False
                    break
            except _Unevaluable:
                ok = False
                break
        if ok:
            return prog
    return None
