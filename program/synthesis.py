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
# Dihedral coordinate maps (the symmetry group of the square)
# ======================================================================
#
# The eight geometric transforms ARC keeps asking for — flip / rotate /
# transpose — are NOT new transformation primitives (F3 forbids that). Each is a
# *coordinate remap* fed to the frozen ``coloring`` primitive: a cell of colour
# ``v`` at input ``(r, c)`` is painted at output ``D(r, c)`` in the **same**
# colour (value-agnostic — the transform never touches the value). This is the
# §2.5-1 discipline verbatim ("flip_h = source 각 셀에 coloring((r, W-1-c),
# color) — 좌표 변환식"): a new transformation is two frozen primitives + a
# coordinate expression, discovered by SEARCH here, not written into the DSL.
#
# ``swaps`` marks the four transforms whose output dims are the input dims
# transposed (the canvas is ``in_w × in_h``, not ``in_h × in_w``). The single
# ``dihedral`` step consults this flag to size its own canvas, so swap and
# non-swap maps share one program skeleton and lift into one rule.
_DIHEDRAL = {
    "flip_h":        (lambda r, c, ih, iw: (r, iw - 1 - c),        False),
    "flip_v":        (lambda r, c, ih, iw: (ih - 1 - r, c),        False),
    "rot180":        (lambda r, c, ih, iw: (ih - 1 - r, iw - 1 - c), False),
    "transpose":     (lambda r, c, ih, iw: (c, r),                 True),
    "rot90":         (lambda r, c, ih, iw: (c, ih - 1 - r),        True),
    "rot270":        (lambda r, c, ih, iw: (iw - 1 - c, r),        True),
    "antitranspose": (lambda r, c, ih, iw: (iw - 1 - c, ih - 1 - r), True),
}

# The eight dihedral *grids* (identity + the seven maps above), used both to fit
# and to render the ``tile`` schema below. Returns a new grid (a permutation of
# the input's cells under the named map), or ``None`` for an unknown name. Pure
# coordinate relabelling — composes nothing but cell moves, so a ``tile`` step
# built from these stays inside the two frozen primitives (§2.5-1, F3-safe).
_TILE_XFORMS = ("identity",) + tuple(_DIHEDRAL)


def _dihedral_grid(name, grid):
    """Apply the named dihedral transform to ``grid`` and return a fresh grid
    (``None`` for an unknown name). ``identity`` copies; the others relabel each
    cell's coordinate via ``_DIHEDRAL`` (dims swap for the transpose/rotate maps).
    Every output cell is written (the map is a bijection), so the fill value is
    irrelevant."""
    if name == "identity":
        return [row[:] for row in grid]
    spec = _DIHEDRAL.get(name)
    if spec is None:
        return None
    remap, swaps = spec
    ih = len(grid)
    iw = len(grid[0]) if grid else 0
    oh, ow = (iw, ih) if swaps else (ih, iw)
    out = [[0] * ow for _ in range(oh)]
    for r in range(ih):
        for c in range(iw):
            nr, nc = remap(r, c, ih, iw)
            out[nr][nc] = grid[r][c]
    return out


# ======================================================================
# Symmetry completion (fill background holes from the grid's own symmetry)
# ======================================================================
#
# A "symmetry completion" output has the *same dims* as the input and equals the
# input with its background cells filled in from the grid's own dihedral
# symmetries — the classic ARC "the picture is symmetric but part of it is
# missing (a background hole); restore it" task (496994bd / 9ddd00f0 / 5751f35e).
#
# The *reason* (P3/P4) is a COMM result: the visible (non-background) part of the
# grid already obeys a set of dihedral symmetries — for every transform ``S`` in
# the set, ``S(grid)`` agrees with ``grid`` on every cell where *both* are
# non-background (background cells are unknown holes, exempt from the check). A
# hole is then filled with the colour its symmetric counterpart shows. This
# composes ONLY the two frozen primitives: it copies the input and paints each
# resolved hole in its counterpart's colour (``coloring``); it never invents a
# value (§2.5-1, F3-safe). The transform is value-agnostic — the symmetry set is
# *read from the grid's structure*, never a literal — so it is the §2.5-2b case
# where the AU "hole" is a selector grounded in the comparison.
#
# The fitted symmetry set is a per-task structural constant (a ``const`` leaf, the
# intersection of the per-pair consistent sets), so two completion tasks with
# *different* symmetry sets share the ONE skeleton ``[("symfill", ("const", ?v))]``
# and lift via ``unify()`` into a single ``covers>1`` rule (R3 — P1·P2·P3 rise
# together). It reads the fixed input throughout, so a set fitted on the train
# pairs restores the test input unchanged (P5).

_SYM_NAMES = ("flip_h", "flip_v", "rot180",
              "transpose", "rot90", "rot270", "antitranspose")


def _consistent_syms(grid, bg):
    """The dihedral transforms whose image has the *same dims* as ``grid`` and
    agrees with it on every cell where both are non-background — i.e. the
    symmetries the *visible* part of the grid already obeys (background cells are
    unknown holes, exempt). Value-agnostic: derived from the grid, never a
    literal. Returns a sorted tuple of transform names."""
    ih = len(grid)
    iw = len(grid[0]) if grid else 0
    out = []
    for name in _SYM_NAMES:
        im = _dihedral_grid(name, grid)
        if im is None or len(im) != ih or (im and len(im[0]) != iw):
            continue  # a dims-swapping map on a non-square grid cannot align
        ok = True
        for r in range(ih):
            for c in range(iw):
                a, b = grid[r][c], im[r][c]
                if a != bg and b != bg and a != b:
                    ok = False
                    break
            if not ok:
                break
        if ok:
            out.append(name)
    return tuple(sorted(out))


def _symfill_grid(grid, bg, syms):
    """Return a fresh grid: ``grid`` with each background cell filled from the
    first transform in ``syms`` whose image holds a non-background value there
    (symmetry completion). Cells with no symmetric counterpart stay background."""
    ih = len(grid)
    iw = len(grid[0]) if grid else 0
    images = [_dihedral_grid(n, grid) for n in syms]
    out = [row[:] for row in grid]
    for r in range(ih):
        for c in range(iw):
            if out[r][c] != bg:
                continue
            for im in images:
                if im is not None and im[r][c] != bg:
                    out[r][c] = im[r][c]
                    break
    return out


# ======================================================================
# Fractal self-tile conditions (the per-macro-cell selector)
# ======================================================================
#
# A "fractal" output is the input *self-tiled*: an ``ih × iw`` macro grid whose
# macro-cell ``(R, C)`` is either a full copy of the input or a blank
# (background) block, decided by a predicate on the input cell ``(R, C)``. The
# transform composes only the two frozen primitives (``make_grid`` + per-cell
# ``coloring``) — it is the §2.5-2b case where the AU "hole" is filled by a
# *selector grounded in the comparison*: which macro-cells get a copy is named by
# a condition on the cell value, not by a literal coordinate list. The condition
# vocabulary is a small *searched* family of value-agnostic selectors, so adding
# to it grows the recognition (selection) vocabulary, not the frozen
# transformation set (F3-safe; this lives in ``program/``/``agent/``, not
# ``DSL/``):
#
#   * ``nonbg`` / ``isbg`` — key on the background (cell ≠ bg / cell == bg);
#   * ``most`` / ``least`` — key on the *unique* most-/least-frequent
#     non-background colour of THIS grid (a frequency selector: the distinguished
#     colour varies per grid, so it is value-agnostic, never a literal — copy the
#     tile wherever the cell holds that colour);
#   * ``all`` — copy every macro-cell (the unconditional self-tile).
#
# Each entry is a *predicate maker* ``(grid, bg) -> (v -> bool) | None``; it
# returns ``None`` to decline on an input where the selector does not resolve
# (e.g. a frequency-keyed colour that is tied or absent), so the candidate is
# simply discarded rather than guessing. ``synthesize_task`` keeps the first
# condition whose program reproduces every pair, exactly as it picks a dihedral
# map. The frequency-keyed members fold real ARC self-tiles (27f8ce4f /
# c3e719e8 / ad7e01d0 "copy where most-frequent colour", 48f8583b "least",
# ccd554ac "always") into the same ``[("fractal", ("const", ?v))]`` skeleton, so
# they lift via ``unify()`` into one ``covers>1`` rule (R3).


def _distinguished_color(grid, bg, which):
    """The *unique* most-/least-frequent NON-background colour of ``grid``, or
    ``None`` if there is none or the extreme is tied (ambiguous → the fractal
    candidate declines on this input rather than guessing). Value-agnostic: the
    colour is read from the grid's own frequencies, never a literal."""
    counts = {}
    for row in grid:
        for v in row:
            if v != bg:
                counts[v] = counts.get(v, 0) + 1
    if not counts:
        return None
    target = max(counts.values()) if which == "most" else min(counts.values())
    winners = [c for c, n in counts.items() if n == target]
    return winners[0] if len(winners) == 1 else None


def _color_eq(color):
    """Predicate ``v == color`` (copy-where-cell-is-``color``), or ``None`` to
    decline when ``color`` did not resolve."""
    if color is None:
        return None
    return lambda v: v == color


_FRACTAL_CONDS = {
    "nonbg": lambda grid, bg: (lambda v: v != bg),
    "isbg":  lambda grid, bg: (lambda v: v == bg),
    "most":  lambda grid, bg: _color_eq(_distinguished_color(grid, bg, "most")),
    "least": lambda grid, bg: _color_eq(_distinguished_color(grid, bg, "least")),
    "all":   lambda grid, bg: (lambda v: True),
}


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
        elif kind == "dihedral":
            # A whole-grid flip / rotate / transpose, expressed as ONE
            # structure-agnostic step that *composes only the two frozen
            # primitives*: it makes the correctly-sized output canvas
            # (``make_grid`` — dims swapped for the dims-swapping maps) and then
            # paints every non-bg input cell, in its own colour, at its remapped
            # position (``coloring``). The transform is a coordinate expression,
            # never a new primitive (§2.5-1, F3-safe). Folding the canvas into
            # this single step is what lets *all eight* maps share ONE program
            # skeleton ``[("dihedral", ("const", ?v))]`` — so swap and non-swap
            # maps lift into a *single* ``covers>1`` rule rather than two
            # separate families (the canvas-dim divergence no longer splits the
            # skeleton). The selection reads the fixed input grid (``env``), so it
            # never cascades off the running canvas and transfers unchanged to the
            # test input (P5).
            _, name_expr = step
            name = _eval(name_expr, env)
            spec = _DIHEDRAL.get(name)
            if spec is None:
                raise _Unevaluable(f"unknown dihedral transform: {name!r}")
            remap, swaps = spec
            ih = len(env["grid"])
            iw = len(env["grid"][0]) if env["grid"] else 0
            bg = env["bg"]
            oh, ow = (iw, ih) if swaps else (ih, iw)
            cur = apply_DSL("make_grid", height=oh, width=ow, color=bg)
            for r, row in enumerate(env["grid"]):
                for c, v in enumerate(row):
                    if v == bg:
                        continue
                    cur = apply_DSL(
                        "coloring", cur,
                        selection=remap(r, c, ih, iw), color=v)
        elif kind == "scale":
            # Pixel scaling (block upsample): every input cell becomes an
            # ``rh × rw`` block of its OWN colour. Like ``dihedral`` it is a
            # purely positional, value-agnostic coordinate expression composing
            # ONLY the two frozen primitives — it makes a canvas ``rh·in_h ×
            # rw·in_w`` (``make_grid``) and paints each cell's block at
            # ``(r·rh, c·rw)`` (``coloring``). The transform never inspects a
            # value, so a program fitted on the train pairs (factors are shared
            # constants, §6.2 data) runs unchanged on the test input (P5: dims
            # come from the input grid). Every cell is painted — including the
            # background — so the result equals the block-upsample exactly,
            # without depending on background detection.
            _, h_expr, w_expr = step
            rh = _eval(h_expr, env)
            rw = _eval(w_expr, env)
            grid = env["grid"]
            ih = len(grid)
            iw = len(grid[0]) if grid else 0
            cur = apply_DSL("make_grid", height=ih * rh, width=iw * rw, color=0)
            for r, row in enumerate(grid):
                for c, v in enumerate(row):
                    block = [(r * rh + dr, c * rw + dc)
                             for dr in range(rh) for dc in range(rw)]
                    cur = apply_DSL("coloring", cur, selection=block, color=v)
        elif kind == "fractal":
            # Fractal self-tile: the output is an ``ih × iw`` macro grid of
            # ``ih × iw`` tiles, where macro-cell ``(R, C)`` is a full copy of the
            # input iff the input cell ``(R, C)`` satisfies the carried condition,
            # else a blank (background) block. Like ``dihedral``/``scale`` it
            # composes ONLY the two frozen primitives — it makes the ``ih² × iw²``
            # canvas (``make_grid``) and paints each selected tile cell in its
            # own input colour (``coloring``). The transform is value-agnostic in
            # the *tile* (the copy never recolours) and selects macro-cells by a
            # predicate on the input value vs background (§2.5-2b: the variable —
            # which cells get a copy — is filled by a selector grounded in the
            # cell↔background comparison, not a literal). Reads the fixed input
            # (``env``) throughout, so it transfers unchanged to the test input
            # (P5).
            _, cond_expr = step
            cond_name = _eval(cond_expr, env)
            make_pred = _FRACTAL_CONDS.get(cond_name)
            if make_pred is None:
                raise _Unevaluable(f"unknown fractal condition: {cond_name!r}")
            grid = env["grid"]
            bg = env["bg"]
            pred = make_pred(grid, bg)
            if pred is None:
                raise _Unevaluable(
                    f"fractal condition {cond_name!r} does not resolve on this "
                    "input (e.g. a tied/absent frequency-keyed colour)")
            ih = len(grid)
            iw = len(grid[0]) if grid else 0
            cur = apply_DSL("make_grid", height=ih * ih, width=iw * iw, color=bg)
            for R in range(ih):
                for C in range(iw):
                    if not pred(grid[R][C]):
                        continue
                    for r in range(ih):
                        for c in range(iw):
                            cur = apply_DSL(
                                "coloring", cur,
                                selection=(R * ih + r, C * iw + c),
                                color=grid[r][c])
        elif kind == "tile":
            # Dihedral tiling: the output is a ``k × m`` macro grid whose block
            # ``(i, j)`` is a *dihedral transform* of the whole input (identity /
            # flip / rotate / transpose), the per-block map carried in the fitted
            # ``pattern`` matrix. Like ``dihedral``/``scale``/``fractal`` it
            # composes ONLY the two frozen primitives — it makes the ``k·ih ×
            # m·iw`` canvas (``make_grid``) and paints each block's transformed
            # cells in their own input colour (``coloring``). The transform is
            # purely positional (value-agnostic: a copy never recolours); the only
            # per-task content is the *arrangement* of mirror/rotate copies, a
            # const ``pattern`` leaf — so two tiling tasks with divergent
            # ``(k, m, pattern)`` share the SAME one-step skeleton
            # ``[("tile", ("const",?v), ("const",?v), ("const",?v))]`` and lift via
            # ``unify()`` into a single ``covers>1`` rule (R3). Reads the fixed
            # input (``env``) throughout, so it transfers unchanged to the test
            # input (P5).
            _, k_expr, m_expr, pat_expr = step
            k = _eval(k_expr, env)
            m = _eval(m_expr, env)
            pattern = _eval(pat_expr, env)
            grid = env["grid"]
            bg = env["bg"]
            ih = len(grid)
            iw = len(grid[0]) if grid else 0
            cur = apply_DSL("make_grid", height=ih * k, width=iw * m, color=bg)
            for i in range(k):
                for j in range(m):
                    name = pattern[i][j]
                    tg = _dihedral_grid(name, grid)
                    if tg is None or len(tg) != ih or (tg and len(tg[0]) != iw):
                        # A dims-swapping transform on a non-square input cannot
                        # fill an ih×iw block — decline rather than misplace cells.
                        raise _Unevaluable(
                            f"tile block transform {name!r} does not fit an "
                            f"{ih}x{iw} block")
                    for r in range(ih):
                        for c in range(iw):
                            v = tg[r][c]
                            if v == bg:
                                continue
                            cur = apply_DSL(
                                "coloring", cur,
                                selection=(i * ih + r, j * iw + c), color=v)
        elif kind == "symfill":
            # Symmetry completion: copy the input and fill each background hole
            # from the colour its symmetric counterpart shows, under the carried
            # set of dihedral symmetries (a value-agnostic structural const,
            # ``("flip_h", "rot180", …)``). Composes ONLY the two frozen
            # primitives — ``cur`` is already a copy of the input, and each
            # resolved hole is painted via ``coloring`` in its counterpart's own
            # colour (never a literal: §2.5-1, F3-safe). The symmetry set is read
            # from the grid's structure (the COMM "the visible part obeys S"), so
            # the rule says *why* a hole takes its value (P3/P4), and a set fitted
            # on the train pairs restores the test input unchanged (P5). Two
            # completion tasks with divergent symmetry sets share the one-step
            # skeleton ``[("symfill", ("const", ?v))]`` and lift via ``unify()``
            # into one ``covers>1`` rule (R3).
            _, syms_expr = step
            syms = _eval(syms_expr, env)
            grid = env["grid"]
            bg = env["bg"]
            filled = _symfill_grid(grid, bg, syms)
            for r, row in enumerate(grid):
                for c, v in enumerate(row):
                    if filled[r][c] != v:
                        cur = apply_DSL(
                            "coloring", cur,
                            selection=(r, c), color=filled[r][c])
        elif kind == "recolor_map":
            # Global colour substitution: a shape-preserved, cell-wise recolour
            # under one colour map ``from -> to`` shared across every pair (the
            # reason — P3/P4 — is the COMM "the same colour always becomes the
            # same colour"). The WHOLE map is carried as ONE structure-agnostic
            # const leaf (a list of ``[from, to]`` pairs), exactly the way
            # ``tile``/``fractal``/``symfill`` carry their per-task data — so a
            # task that changes one colour and a task that changes three share the
            # SAME one-step skeleton ``[("recolor_map", ("const", ?v))]`` and lift
            # via ``unify()`` into one ``covers>1`` rule (R3), instead of
            # fragmenting into an arity-keyed rule per changed-colour count (the
            # 168-rule accretion failure, §2.5-3/4). Composes ONLY the frozen
            # ``coloring`` primitive — one ``coloring`` per pair, each selecting
            # the FIXED input's cells of that colour (``env``, not the running
            # canvas), so a colour used as both a source and a target never
            # cascades and the program transfers unchanged to the test input (P5).
            _, map_expr = step
            cmap = _eval(map_expr, env)
            grid = env["grid"]
            for frm, to in cmap:
                sel = [(r, c) for r, row in enumerate(grid)
                       for c, v in enumerate(row) if v == frm]
                if sel:
                    cur = apply_DSL("coloring", cur, selection=sel, color=to)
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
    # same colour always becomes the same colour"). Expressed as ONE
    # ``recolor_map`` step carrying the whole map as a single const leaf (a tuple
    # of ``(from, to)`` pairs), composed from the frozen ``coloring`` primitive at
    # run time. Distinct colours may map to distinct colours, so this is the
    # general case no single-colour `object_recolor` family fits — and, because
    # the entire map lives in ONE const leaf, a task that changes one colour and a
    # task that changes three share the SAME ``[("recolor_map", ("const", ?v))]``
    # skeleton and lift via `unify()` into one covers>1 rule (R3), rather than
    # fragmenting into a separate covers=1 rule per changed-colour count (the
    # arity-keyed accretion that minted rule-per-task, §2.5-3/4). The selections
    # read the fixed input, so map order is irrelevant.
    prog = _fit_color_map(pairs)
    if prog is not None:
        yield prog

    # --- Schema 5: dihedral geometric transform ----------------------------
    # A whole-grid flip / rotate / transpose. Each candidate is a single
    # ``dihedral`` step carrying a fixed coordinate map (`_DIHEDRAL`);
    # `synthesize_task` keeps the first whose map reproduces every pair. The
    # step composes only the two frozen primitives (it makes its own
    # correctly-sized canvas, dims swapped for the dims-swapping maps, then
    # paints). The transform is value-agnostic (only a cell's position changes),
    # so *every* map — flip, rotate, transpose alike — shares the SAME one-step
    # skeleton ``[("dihedral", ("const", ?v))]`` and they all lift via `unify()`
    # into a *single* ``covers>1`` rule whose map leaf is a ``?v`` (R3 —
    # P1·P2·P3 rise together; the canvas-dim difference between swap and non-swap
    # maps lives inside the step, so it no longer splits the skeleton into two
    # families).
    for name in _DIHEDRAL:
        yield [("dihedral", ("const", name))]

    # --- Schema 6: pixel scaling (block upsample) --------------------------
    # The output is the input with every cell blown up to an ``rh × rw`` block,
    # when a single integer factor pair holds across *every* train pair (the
    # reason — P3/P4 — is the COMM result "output dims are always the same
    # integer multiple of input dims"). One ``scale`` step carries the fitted
    # factors as ``const`` leaves; being a pure ``[("scale", ("const",?),
    # ("const",?))]`` skeleton, two scale tasks with different factors lift via
    # ``unify()`` into one ``covers>1`` rule (R3 — P1·P2·P3 rise together), the
    # same way the dihedral maps do. The step composes only the two frozen
    # primitives (§2.5-1, F3-safe).
    sc = _fit_scale(pairs)
    if sc is not None:
        yield [("scale", ("const", sc[0]), ("const", sc[1]))]

    # --- Schema 7: fractal self-tile ---------------------------------------
    # When every pair's output dims are exactly ``(ih², iw²)``, the output may be
    # the input self-tiled: a macro grid of input-copies gated by a per-cell
    # condition — copy where the cell is non-background (007bbfb7 / 5b6cbef5),
    # where it holds the most-/least-frequent colour (27f8ce4f / c3e719e8 /
    # ad7e01d0 / 48f8583b), or unconditionally (ccd554ac). All are value-agnostic
    # frequency/background selectors (`_FRACTAL_CONDS`), never literal colours.
    # Yield one candidate per condition in the searched vocabulary;
    # ``synthesize_task`` keeps the first whose program reproduces every pair (the
    # same select-by-search discipline as the dihedral maps). Being a pure
    # ``[("fractal", ("const", ?v))]`` skeleton, two fractal tasks with divergent
    # conditions lift via ``unify()`` into one ``covers>1`` rule (R3).
    if _is_fractal_dims(pairs):
        for name in _FRACTAL_CONDS:
            yield [("fractal", ("const", name))]

    # --- Schema 8: dihedral tiling ----------------------------------------
    # The output is a ``k × m`` macro grid of dihedral copies of the input —
    # plain replication, mirror-tiling, or rotation-tiling (the kaleidoscope
    # family: 0c786b71, 46442a0e, 7fe24cdd, …). The reason — P3/P4 — is the COMM
    # result "every ih×iw block of the output is some rigid transform of the
    # input". `_fit_tile` resolves the shared factor pair and the per-block
    # transform arrangement directly (a fit, not an 8^(k·m) enumeration), and
    # declines when no consistent arrangement exists. Being a pure
    # ``[("tile", ("const",?),("const",?),("const",?))]`` skeleton, two tiling
    # tasks with divergent arrangements lift via ``unify()`` into one
    # ``covers>1`` rule (R3 — P1·P2·P3 rise together). Yielded last so a simpler
    # schema (scale, fractal) wins when a task fits both.
    tile = _fit_tile(pairs)
    if tile is not None:
        yield tile

    # --- Schema 9: symmetry completion -------------------------------------
    # Same-dims output that is the input with its background holes restored from
    # the grid's own dihedral symmetry (496994bd / 9ddd00f0 / 5751f35e). The
    # reason — P3/P4 — is the COMM "the visible part obeys symmetry set S";
    # ``_fit_symfill`` reads S off the train inputs (the intersection of the
    # per-pair consistent sets) as a value-agnostic structural const, never a
    # literal. Being a pure ``[("symfill", ("const", ?v))]`` skeleton, two
    # completion tasks with divergent symmetry sets lift via ``unify()`` into one
    # ``covers>1`` rule (R3). Yielded last so a simpler same-dims schema (identity,
    # colour-map) wins when a task fits both.
    symfill = _fit_symfill(pairs)
    if symfill is not None:
        yield symfill


def _is_fractal_dims(pairs):
    """True iff every pair's output dims are exactly ``(ih·ih, iw·iw)`` — the
    self-tile shape the fractal schema expresses. A cheap structural gate so the
    fractal candidates are only offered when they can possibly fit."""
    for p in pairs:
        gin, gout = p["input"], p["output"]
        ih = len(gin)
        iw = len(gin[0]) if gin else 0
        if ih == 0 or iw == 0:
            return False
        oh = len(gout)
        ow = len(gout[0]) if gout else 0
        if oh != ih * ih or ow != iw * iw:
            return False
    return True


def _fit_scale(pairs):
    """Return ``(rh, rw)`` integer scale factors if every pair's output is the
    input upsampled by one shared factor pair (at least one factor > 1), else
    ``None``. The factors are value-agnostic constants shared across all pairs,
    so the program transfers to the test input (P5)."""
    rhs, rws = set(), set()
    for p in pairs:
        gin, gout = p["input"], p["output"]
        ih = len(gin)
        iw = len(gin[0]) if gin else 0
        oh = len(gout)
        ow = len(gout[0]) if gout else 0
        if ih == 0 or iw == 0 or oh % ih or ow % iw:
            return None
        rhs.add(oh // ih)
        rws.add(ow // iw)
    if len(rhs) != 1 or len(rws) != 1:
        return None
    rh, rw = rhs.pop(), rws.pop()
    if rh < 1 or rw < 1 or (rh == 1 and rw == 1):
        return None
    return (rh, rw)


def _fit_tile(pairs):
    """Return a one-step ``tile`` program if every pair's output is a ``k × m``
    macro grid of *dihedral copies* of its input, else ``None``.

    The factor pair ``(k, m)`` must be shared across all pairs (value-agnostic,
    read from the dims). For each block position the fitter intersects, across
    pairs, the set of dihedral transforms whose grid equals that block — a direct
    *fit* (8 transforms per block), not an enumeration of the ``8^(k·m)``
    arrangements. If every position keeps at least one consistent transform, the
    arrangement is realised as a ``pattern`` matrix (deterministic pick where a
    symmetric block admits several). The literal here is purely *positional* (an
    arrangement of mirror/rotate copies, never a colour), so two tiling tasks
    lift via ``unify()`` into one ``covers>1`` rule (§2.5-3)."""
    ks, ms = set(), set()
    for p in pairs:
        gin, gout = p["input"], p["output"]
        ih = len(gin)
        iw = len(gin[0]) if gin else 0
        oh = len(gout)
        ow = len(gout[0]) if gout else 0
        if ih == 0 or iw == 0 or oh % ih or ow % iw:
            return None
        ks.add(oh // ih)
        ms.add(ow // iw)
    if len(ks) != 1 or len(ms) != 1:
        return None
    k, m = ks.pop(), ms.pop()
    if k * m <= 1:
        return None  # a single block is just the identity / dihedral schema
    valid = [[set(_TILE_XFORMS) for _ in range(m)] for _ in range(k)]
    for p in pairs:
        gin, gout = p["input"], p["output"]
        ih = len(gin)
        iw = len(gin[0]) if gin else 0
        xforms = {nm: _dihedral_grid(nm, gin) for nm in _TILE_XFORMS}
        for i in range(k):
            for j in range(m):
                blk = [row[j * iw:(j + 1) * iw]
                       for row in gout[i * ih:(i + 1) * ih]]
                keep = {nm for nm in valid[i][j] if xforms[nm] == blk}
                if not keep:
                    return None
                valid[i][j] = keep
    pattern = tuple(
        tuple(sorted(valid[i][j])[0] for j in range(m)) for i in range(k))
    return [("tile", ("const", k), ("const", m), ("const", pattern))]


def _fit_symfill(pairs):
    """Return a one-step ``symfill`` program if every pair's output is the input
    with its background holes restored from a shared dihedral symmetry set, else
    ``None``.

    Each pair must be same-dims. The task symmetry set is the *intersection*
    across pairs of each input's consistent transforms (``_consistent_syms``) — a
    value-agnostic structural const read from the grids, never a literal. The set
    is accepted only if completing every input under it reproduces that pair's
    output *and* actually changes at least one input (an all-identity fill is the
    identity schema, already yielded). The const symmetry set is the per-task
    leaf, so two completion tasks with divergent sets lift via ``unify()`` into one
    ``covers>1`` rule (§2.5-3)."""
    inter = None
    for p in pairs:
        gin, gout = p["input"], p["output"]
        if len(gin) != len(gout):
            return None
        ih = len(gin)
        iw = len(gin[0]) if gin else 0
        if ih == 0 or iw == 0 or len(gout[0]) != iw:
            return None
        bg = background_of(gin)
        cs = set(_consistent_syms(gin, bg))
        inter = cs if inter is None else (inter & cs)
        if not inter:
            return None
    syms = tuple(sorted(inter))
    changed = False
    for p in pairs:
        gin = p["input"]
        bg = background_of(gin)
        filled = _symfill_grid(gin, bg, syms)
        if filled != p["output"]:
            return None
        if filled != gin:
            changed = True
    if not changed:
        return None
    return [("symfill", ("const", syms))]


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
    # Carry the whole map as ONE const leaf (a tuple of ``(from, to)`` pairs), so
    # every colour-substitution task — whatever its changed-colour count — shares
    # the single ``[("recolor_map", ("const", ?v))]`` skeleton and lifts via
    # ``unify()`` into one ``covers>1`` rule, instead of one rule per arity.
    pairs_leaf = tuple((c, cmap[c]) for c in changed)
    return [("recolor_map", ("const", pairs_leaf))]


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
