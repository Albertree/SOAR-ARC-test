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
from agent.dsl_expr.selection import (
    objects_of, background_of, color_of, select_object)


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
# Two-panel boolean combine (the cell-wise logic family)
# ======================================================================
#
# A huge, recurring ARC family: the input is *two equal panels* (separated by a
# uniform full row/column, or split at the even midpoint), and the output — half
# the input's size — is the **cell-wise boolean combination** of the panels'
# *occupancy* (a cell counts as "on" iff it is non-background), painted in ONE
# fixed colour on a blank canvas. The reason (P3/P4) is a COMM result: the same
# on/off pattern of the two panels always yields the same output cell — e.g.
# "paint where BOTH panels are on" (and), "where EITHER is" (or), "where exactly
# one is" (xor), "where NEITHER is" (nor), …
#
# Like ``dihedral``/``fractal``/``tile`` it composes ONLY the two frozen
# primitives (``make_grid`` for the half-size canvas, ``coloring`` for the cells
# the predicate selects) — it adds no transformation vocabulary (§2.5-1, F3-safe).
# The per-task content is just the triple ``(axis, op, colour)``: the split
# orientation, the boolean predicate, and the paint colour, all *read from the
# example comparison* (the colour is the output's unique non-bg colour, never a
# literal coordinate). Carried as ONE ``const`` leaf, two combine tasks with
# divergent triples share the SAME one-step skeleton ``[("boolcombine",
# ("const", ?v))]`` and lift via ``unify()`` into one ``covers>1`` rule (R3 —
# P1·P2·P3 rise together), exactly as ``recolor_map`` carries its whole colour
# map in one leaf. Reads the fixed input throughout, so a triple fitted on the
# train pairs combines the test input unchanged (P5).
#
# The occupancy binarisation (on == non-bg) is what makes the predicate
# value-agnostic: the two panels may use *different* colours and the output a
# *third*, yet the same logical rule applies — so this is genuinely a new
# *general* capability, not a per-task recolour.

_BOOL_OPS = {
    "and":   lambda a, b: a and b,
    "or":    lambda a, b: a or b,
    "xor":   lambda a, b: a != b,
    "nand":  lambda a, b: not (a and b),
    "nor":   lambda a, b: not (a or b),
    "xnor":  lambda a, b: a == b,
    "lonly": lambda a, b: a and not b,
    "ronly": lambda a, b: b and not a,
}

# Colour-*preserving* two-panel merges. Where the boolean ops above binarise the
# panels (on == non-bg) and paint a single fixed colour, these read each panel
# cell's *actual* colour and carry it through — the recurring "overlay / stack the
# two panels" family (7b7f7511, e98196ab) where the output keeps the panels' own
# colours rather than a third paint colour. Each is a pure function of
# ``(a, b, bg)`` (the two panel cells and the background), so it is value-agnostic
# exactly like the boolean predicates: the panels may use different colours and
# the same logical overlay still applies. The carried spec stays the same 3-tuple
# ``(axis, op, color)`` — ``color`` is unused (``None``) for a merge op since the
# colour comes from the panels — so a boolean-combine task and a colour-merge task
# share the SAME one-step skeleton ``[("boolcombine", ("const", ?v))]`` and lift
# via ``unify()`` into the SAME ``covers>1`` rule (R3), folding into the existing
# boolcombine family rather than minting a separate one (§2.5-3/4).
_MERGE_OPS = {
    "A_over_B":  lambda a, b, bg: a if a != bg else b,
    "B_over_A":  lambda a, b, bg: b if b != bg else a,
    "keep_equal": lambda a, b, bg: a if a == b else bg,
    "xor_one":   lambda a, b, bg: (a if a != bg else b)
                 if (a != bg) != (b != bg) else bg,
}


def _split_for_axis(grid, axis):
    """Split ``grid`` into its two equal panels along ``axis`` (``"v"`` =
    side-by-side, ``"h"`` = stacked), or ``None`` if it does not split.

    For an *odd*-length axis the middle row/column must be a uniform separator
    line (excluded from both panels); for an *even*-length axis the grid is split
    at the midpoint (no separator). Purely structural — never inspects a colour —
    so the same split is recovered on the test input (P5).

    ``axis == "auto"`` resolves the orientation *structurally per grid* via
    ``_auto_split_axis`` (the split axis is selected, not carried as a literal),
    so a task whose split axis varies across pairs still applies one program."""
    if axis == "auto":
        resolved = _auto_split_axis(grid)
        if resolved is None:
            return None
        return _split_for_axis(grid, resolved)
    H = len(grid)
    W = len(grid[0]) if grid else 0
    if axis == "v":
        if W % 2 == 1:
            sc = W // 2
            if len({grid[r][sc] for r in range(H)}) != 1:
                return None
            return ([row[:sc] for row in grid], [row[sc + 1:] for row in grid])
        if W >= 2:
            return ([row[:W // 2] for row in grid], [row[W // 2:] for row in grid])
        return None
    if axis == "h":
        if H % 2 == 1:
            sr = H // 2
            if len(set(grid[sr])) != 1:
                return None
            return (grid[:sr], grid[sr + 1:])
        if H >= 2:
            return (grid[:H // 2], grid[H // 2:])
        return None
    return None


def _has_separator(grid, axis):
    """True iff ``grid`` splits along ``axis`` *because of* a uniform separator
    line (the odd-length case) — a strong structural cue for which orientation a
    two-panel grid is divided along."""
    H = len(grid)
    W = len(grid[0]) if grid else 0
    if axis == "v":
        return W % 2 == 1 and _split_for_axis(grid, "v") is not None
    if axis == "h":
        return H % 2 == 1 and _split_for_axis(grid, "h") is not None
    return False


def _auto_split_axis(grid):
    """Structurally select the split orientation of a two-panel grid, reading
    only the input's shape/content (value-agnostic, P5).

    The unique axis that admits an equal-panel split wins outright. When *both*
    axes admit an even-midpoint split (an ambiguous square-ish grid), prefer the
    axis carrying a uniform separator line, then the axis whose two halves are
    *identical* to each other (the recurring "duplicated panels" structure);
    decline (``None``) if still ambiguous. This lets a boolcombine whose split
    axis *varies across pairs* fit with the axis lifted to the ``"auto"``
    selector instead of a per-task literal."""
    cands = [ax for ax in ("v", "h") if _split_for_axis(grid, ax) is not None]
    if not cands:
        return None
    if len(cands) == 1:
        return cands[0]
    sep = [ax for ax in cands if _has_separator(grid, ax)]
    if len(sep) == 1:
        return sep[0]
    eq = [ax for ax in cands
          if (lambda ab: ab[0] == ab[1])(_split_for_axis(grid, ax))]
    if len(eq) == 1:
        return eq[0]
    return None


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
        elif kind == "boolcombine":
            # Two-panel boolean combine: split the input into its two equal
            # panels along the carried axis, then paint — on a fresh half-size
            # canvas — every cell where the boolean predicate over the panels'
            # occupancy (cell != bg) holds, in the carried colour. Composes ONLY
            # the two frozen primitives (``make_grid`` + ``coloring``); the
            # predicate and colour are a value-agnostic const leaf read from the
            # example comparison, so two combine tasks lift into one ``covers>1``
            # rule (R3). Reads the fixed input (``env``), so it transfers
            # unchanged to the test input (P5).
            _, spec_expr = step
            axis, op, color = _eval(spec_expr, env)
            pred = _BOOL_OPS.get(op)
            merge = _MERGE_OPS.get(op)
            if pred is None and merge is None:
                raise _Unevaluable(f"unknown boolean combine op: {op!r}")
            grid = env["grid"]
            bg = env["bg"]
            panels = _split_for_axis(grid, axis)
            if panels is None:
                raise _Unevaluable(
                    f"input does not split into two {axis!r} panels")
            A, B = panels
            h = len(A)
            w = len(A[0]) if A else 0
            if (len(B), len(B[0]) if B else 0) != (h, w):
                raise _Unevaluable("boolcombine panels are not equal-sized")
            cur = apply_DSL("make_grid", height=h, width=w, color=bg)
            if pred is not None:
                # Boolean mask: paint the predicate-selected cells one fixed colour.
                on = [(r, c) for r in range(h) for c in range(w)
                      if pred(A[r][c] != bg, B[r][c] != bg)]
                if on:
                    cur = apply_DSL("coloring", cur, selection=on, color=color)
            else:
                # Colour-preserving merge: each output cell keeps the panel colour
                # the merge fn returns. Group cells by resulting colour so the
                # canvas is filled with one ``coloring`` per colour (the two frozen
                # primitives only — §2.5-1, F3-safe), exactly like Schema 2.
                by_color = {}
                for r in range(h):
                    for c in range(w):
                        v = merge(A[r][c], B[r][c], bg)
                        if v != bg:
                            by_color.setdefault(v, []).append((r, c))
                for col in sorted(by_color):
                    cur = apply_DSL("coloring", cur, selection=by_color[col],
                                    color=col)
        elif kind == "connect":
            # Connect the dots: for each colour, every two same-colour markers that
            # are aligned in a row or column get the background gap between them
            # filled in — drawing the straight segment that joins them. The carried
            # spec is the line colour: ``"same"`` paints the segment in each pair's
            # OWN marker colour (the colour read from the markers, never a literal —
            # value-agnostic), or a fixed colour int paints every segment that one
            # colour. Composes ONLY the frozen ``coloring`` primitive (``cur`` is
            # already a copy of the input; each gap cell is painted), so it adds no
            # transformation vocabulary (§2.5-1, F3-safe). Marker positions and the
            # "is this cell a background gap" test are read from the FIXED input
            # (``env``), never the running canvas, so a segment never cascades off a
            # freshly-drawn cell and the program transfers unchanged to the test
            # input (P5). The reason (P3/P4) is a COMM result: two markers of the
            # same colour sharing a row/column are joined. Carried as ONE ``const``
            # leaf, an own-colour task and a fixed-colour task share the SAME
            # one-step skeleton ``[("connect", ("const", ?v))]`` and lift via
            # ``unify()`` into one ``covers>1`` rule (R3 — P1·P2·P3 rise together).
            _, spec_expr = step
            spec = _eval(spec_expr, env)
            grid = env["grid"]
            bg = env["bg"]
            H = len(grid)
            W = len(grid[0]) if grid else 0
            by_color = {}
            for r in range(H):
                for c in range(W):
                    v = grid[r][c]
                    if v != bg:
                        by_color.setdefault(v, []).append((r, c))
            for col, cells in by_color.items():
                line = col if spec == "same" else spec
                for i in range(len(cells)):
                    r1, c1 = cells[i]
                    for j in range(i + 1, len(cells)):
                        r2, c2 = cells[j]
                        if r1 == r2:
                            seg = [(r1, c) for c in range(min(c1, c2) + 1,
                                                          max(c1, c2))
                                   if grid[r1][c] == bg]
                        elif c1 == c2:
                            seg = [(r, c1) for r in range(min(r1, r2) + 1,
                                                          max(r1, r2))
                                   if grid[r][c1] == bg]
                        else:
                            continue
                        if seg:
                            cur = apply_DSL(
                                "coloring", cur, selection=seg, color=line)
        elif kind == "crop":
            # Crop to a sub-rectangle: the output is the bounding box of a region
            # *named by a value-agnostic selector* — the whole non-background
            # content, or the colour-aware object the selector picks (the largest /
            # smallest / unique-colour / unique-size region). The selector is a pure
            # function of the FIXED input (``env``), never a per-pair literal
            # coordinate, so a selector fitted on the train pairs crops the test
            # input unchanged (P5) — this is the §2.5-2b discipline: which region to
            # keep is named by a structural selector grounded in the comparison
            # (COMM/DIFF), not a stored box. Composes ONLY the two frozen primitives
            # — it makes the cropped-size canvas (``make_grid``) and paints each
            # non-background cell of the region at its translated position
            # (``coloring``) — so it adds no transformation vocabulary (§2.5-1,
            # F3-safe). Carried as ONE ``const`` leaf, two crop tasks with divergent
            # selectors share the SAME one-step skeleton ``[("crop", ("const",
            # ?v))]`` and lift via ``unify()`` into one ``covers>1`` rule (R3 —
            # P1·P2·P3 rise together).
            _, sel_expr = step
            selector = _eval(sel_expr, env)
            grid = env["grid"]
            bg = env["bg"]
            box = _crop_bbox(grid, bg, selector)
            if box is None:
                raise _Unevaluable(
                    f"crop selector {selector!r} names no region on this input")
            r0, c0, r1, c1 = box
            cur = apply_DSL(
                "make_grid", height=r1 - r0 + 1, width=c1 - c0 + 1, color=bg)
            for r in range(r0, r1 + 1):
                for c in range(c0, c1 + 1):
                    v = grid[r][c]
                    if v != bg:
                        cur = apply_DSL(
                            "coloring", cur, selection=(r - r0, c - c0), color=v)
        elif kind == "recolor_objects":
            # Object-level recolour by a value-agnostic *property → colour* map: each
            # input object is repainted (its cells kept fixed) in the colour the map
            # assigns to that object's structural property — its cell-count (`size`),
            # its translation-normalised cell signature (`shape`), or its dense
            # size-`rank` within the grid (the ordinal that transfers to test sizes
            # unseen in train). The reason — P3/P4 — is the COMM "an object with this
            # property always becomes this colour"; `_fit_recolor_objects` reads the
            # property and the map off the train pairs (the property chosen by
            # SEARCH: size, then shape, then rank) and declines when none reproduces
            # every pair. The WHOLE map is ONE
            # structure-agnostic const leaf (a list of ``[key, colour]`` pairs),
            # exactly the way ``recolor_map`` carries its colour map — so a task
            # keyed on size and a task keyed on shape (or differing in arity) share
            # the SAME one-step skeleton ``[("recolor_objects", ("const", ?v))]`` and
            # lift via ``unify()`` into one ``covers>1`` rule (R3 — P1·P2·P3 rise
            # together), instead of fragmenting into a rule per property/arity (the
            # §2.5-3/4 accretion trap). This is the §2.5-2b "the selection is the
            # real content" step at the property level — the per-task content is the
            # fitted map, reusing the R1 object vocabulary, not a stored coordinate
            # program. Composes ONLY the frozen ``coloring`` primitive (one
            # ``coloring`` per object). Reads objects of the FIXED input (``env``),
            # so it transfers unchanged to the test input (P5); an object whose
            # property is absent from the fitted map makes the step *decline*
            # (``_Unevaluable``) rather than guess (memory:
            # runtime_resolvable_speculative_apply — renderers decline, not crash).
            _, spec_expr = step
            spec = _eval(spec_expr, env)
            prop = spec["prop"]
            cmap = {_canon_key(k): v for k, v in spec["map"]}
            grid = env["grid"]
            bg = env["bg"]
            objs = objects_of(grid, bg)
            for obj, k in zip(objs, _obj_keys(objs, prop)):
                if k not in cmap:
                    raise _Unevaluable(
                        f"recolor_objects: object property {k!r} not in fitted map")
                cur = apply_DSL(
                    "coloring", cur, selection=sorted(obj["cells"]), color=cmap[k])
        elif kind == "gravity":
            # Cell gravity: every non-background cell slides along one direction
            # until it is blocked by the grid edge or a cell already settled, per
            # line (a column for up/down, a row for left/right), preserving the
            # cells' order within that line. The recurring ARC "let everything fall
            # / pile to one side" family. The reason — P3/P4 — is the COMM-DIFF
            # observation that within each line the same multiset of coloured cells
            # appears, only compacted against one edge; ``_fit_gravity`` reads which
            # of the four directions reproduces every pair (chosen by SEARCH) and
            # declines when none does. The direction is the WHOLE per-task content,
            # carried as ONE const leaf — so a fall-down task and a fall-up task
            # share the SAME one-step skeleton ``[("gravity", ("const", ?v))]`` and
            # lift via ``unify()`` into one ``covers>1`` rule (R3 — P1·P2·P3 rise
            # together), never a rule per direction (§2.5-3/4). Composes ONLY the two
            # frozen primitives: it makes a blank canvas (``make_grid``) and paints
            # each settled cell in its own colour (``coloring``), so it adds no
            # transformation vocabulary (§2.5-1, F3-safe). Reads the cells of the
            # FIXED input (``env``), so the same program settles the test input
            # unchanged (P5).
            _, dir_expr = step
            direction = _eval(dir_expr, env)
            grid = env["grid"]
            bg = env["bg"]
            H = len(grid)
            W = len(grid[0]) if H else 0
            cur = apply_DSL("make_grid", height=H, width=W, color=bg)
            if direction in ("down", "up"):
                for c in range(W):
                    vals = [grid[r][c] for r in range(H) if grid[r][c] != bg]
                    rows = (range(H - len(vals), H) if direction == "down"
                            else range(0, len(vals)))
                    for r, v in zip(rows, vals):
                        cur = apply_DSL("coloring", cur, selection=(r, c), color=v)
            elif direction in ("left", "right"):
                for r in range(H):
                    vals = [grid[r][c] for c in range(W) if grid[r][c] != bg]
                    cols = (range(W - len(vals), W) if direction == "right"
                            else range(0, len(vals)))
                    for c, v in zip(cols, vals):
                        cur = apply_DSL("coloring", cur, selection=(r, c), color=v)
            else:
                raise _Unevaluable(f"unknown gravity direction: {direction!r}")
        elif kind == "compose":
            # Two-stage composition: run a *stage-1* sub-program (a structural
            # reduction of the input — crop to a selected region, or a dihedral
            # re-orientation) to produce an intermediate grid, then **re-root the
            # environment to that intermediate** so the remaining steps treat it
            # as their input. This is the only step that re-roots ``env``; every
            # other step reads the original input (P5), which is exactly why a
            # genuine spatial-then-spatial composition (crop-then-tile,
            # rotate-then-X) needs this wrapper rather than threading ``cur``.
            #
            # The intermediate is itself produced by ``run_program`` from the two
            # frozen primitives (the stage-1 sub-program is a ``crop``/``dihedral``
            # step), so composition adds NO transformation vocabulary (§2.5-1,
            # F3-safe). Because the stage-1 reduction is a pure, value-agnostic
            # function of the input, the re-rooted environment is reproduced
            # unchanged on the test input (P5). Carried as the head step with the
            # stage-1 sub-program in its leaf, two tasks sharing the same
            # (stage-1-shape, stage-2-schema) skeleton lift via ``unify()`` into one
            # ``covers>1`` rule (R3 — ``agent/memory.py:_program_skeleton`` collapses
            # the fitted const leaves on both stages).
            _, pre = step
            inter = run_program(pre, env["grid"])
            env = {
                "grid": inter,
                "objs": objects_of(inter),
                "bg": background_of(inter),
            }
            cur = [row[:] for row in inter]
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

    # --- Schema 10: two-panel boolean combine ------------------------------
    # The input is two equal panels (separated by a uniform row/col or split at
    # the even midpoint) and the output — half the size — is their cell-wise
    # boolean combination (and / or / xor / nor / …) painted in one fixed colour
    # (0520fde7, 99b1bc43, 34b99a2b, 1b2d62fb, … — a large recurring ARC family).
    # The reason — P3/P4 — is the COMM "the same on/off pattern of the two panels
    # always yields the same output cell". ``_fit_boolcombine`` resolves the
    # shared ``(axis, op, colour)`` triple directly and declines when no
    # consistent one exists. Being a pure ``[("boolcombine", ("const", ?v))]``
    # skeleton, two combine tasks with divergent triples lift via ``unify()`` into
    # one ``covers>1`` rule (R3). Yielded last so a simpler same-or-smaller-dims
    # schema wins when a task somehow fits both.
    boolcombine = _fit_boolcombine(pairs)
    if boolcombine is not None:
        yield boolcombine

    # --- Schema 11: connect the dots --------------------------------------
    # Same-dims output that is the input with aligned same-colour marker pairs
    # joined by straight segments — the recurring ARC "connect the dots / draw the
    # lines between matching cells" family (070dd51e, 22168020, ded97339; and the
    # fixed-line-colour variants dbc1a6ce, aa18de87). The reason — P3/P4 — is the
    # COMM "two markers of the same colour sharing a row/column are joined".
    # ``_fit_connect`` resolves the shared line-colour spec (``"same"`` = the
    # marker's own colour, or a fixed colour) directly and declines when none
    # reproduces every pair. Being a pure ``[("connect", ("const", ?v))]``
    # skeleton, an own-colour task and a fixed-colour task lift via ``unify()``
    # into one ``covers>1`` rule (R3 — P1·P2·P3 rise together). Yielded last so a
    # simpler same-dims schema (identity, colour-map, symfill) wins when a task
    # somehow fits both.
    connect = _fit_connect(pairs)
    if connect is not None:
        yield connect

    # --- Schema 12: crop to a selected sub-region --------------------------
    # The output is a contiguous sub-rectangle of the input — the bounding box of
    # a region *named by a value-agnostic selector*: all non-background content, or
    # the colour-aware object the selector picks (largest / smallest / unique-colour
    # / unique-size). The recurring ARC "extract the relevant part" family
    # (1cf80156 content-crop; 39a8645d / a87f7484 / be94b721 pick-an-object). The
    # reason — P3/P4 — is a COMM/DIFF result naming *which* region the output keeps;
    # ``_fit_crop`` resolves the shared selector directly (the selector is a pure
    # function of the input, so it transfers to the test input unchanged, P5) and
    # declines when none reproduces every pair. This is the §2.5-2b "selection is
    # the real content" step: the per-task content lives in the selector, reusing
    # the R1 object-selection vocabulary, not in a stored coordinate box. Being a
    # pure ``[("crop", ("const", ?v))]`` skeleton, two crop tasks with divergent
    # selectors lift via ``unify()`` into one ``covers>1`` rule (R3 — P1·P2·P3 rise
    # together). Yielded last so a same-dims schema wins when a task somehow fits
    # both.
    crop = _fit_crop(pairs)
    if crop is not None:
        yield crop

    # --- Schema 14: object-level recolour by property ----------------------
    # Same-dims output that is the input with each object repainted in the colour a
    # value-agnostic *property → colour* map assigns to it — the recurring ARC
    # "colour each shape by its size / its form" family (e.g. recolour every object
    # by how many cells it has, or by its shape). The reason — P3/P4 — is the COMM
    # "an object with this property always becomes this colour"; `_fit_recolor_objects`
    # reads the property (size, then shape) and the map off the train pairs and
    # declines when none reproduces every pair. This is the object-level counterpart
    # of Schema 4's cell-wise ``recolor_map`` (a colour map there, a property map
    # here): both carry the whole map as ONE const leaf, so a size-keyed task and a
    # shape-keyed task share the pure ``[("recolor_objects", ("const", ?v))]``
    # skeleton and lift via ``unify()`` into one ``covers>1`` rule (R3 — P1·P2·P3
    # rise together), never a rule per property/arity (§2.5-3/4). Yielded last so a
    # simpler same-dims schema (identity, cell-wise colour-map, symfill, connect)
    # wins when a task fits both.
    recolor_objects = _fit_recolor_objects(pairs)
    if recolor_objects is not None:
        yield recolor_objects

    # --- Schema 15: cell gravity -------------------------------------------
    # Same-dims output that is the input with every non-background cell slid to one
    # edge per line (a column for up/down, a row for left/right), preserving order
    # within the line — the recurring ARC "everything falls / piles to one side"
    # family. The reason — P3/P4 — is the COMM-DIFF "within each line the same
    # coloured cells appear, only compacted against one edge"; `_fit_gravity` reads
    # which of the four directions reproduces every pair (chosen by SEARCH) and
    # declines when none does. The direction is the whole per-task content carried
    # as ONE const leaf, so a fall-down task and a fall-up task share the pure
    # ``[("gravity", ("const", ?v))]`` skeleton and lift via ``unify()`` into one
    # ``covers>1`` rule (R3 — P1·P2·P3 rise together), never a rule per direction
    # (§2.5-3/4). Yielded last so a simpler same-dims schema wins when a task fits
    # both (a settled grid is owned by identity).
    gravity = _fit_gravity(pairs)
    if gravity is not None:
        yield gravity


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


def _fit_boolcombine(pairs):
    """Return a one-step ``boolcombine`` program if every pair's output is the
    cell-wise boolean combination of the input's two equal panels (split by a
    uniform separator row/col or at the even midpoint), painted in one fixed
    colour, else ``None``.

    The ``(axis, op, colour)`` triple must be shared across *all* pairs — fitted
    by intersecting, per pair, the triples that reproduce that output exactly.
    The candidate colour is the output's unique non-background colour (read from
    the comparison, never a literal), so a uniform-background output (no cells to
    paint) has no combine to fit. Because the whole triple lives in ONE const
    leaf, two combine tasks with divergent triples share the SAME one-step
    skeleton ``[("boolcombine", ("const", ?v))]`` and lift via ``unify()`` into
    one ``covers>1`` rule (R3 — §2.5-3).

    Two passes. Pass 1 fits a *single shared* axis (the original behaviour —
    preserves every existing solve). Pass 2 is the fallback for a task whose
    split orientation *varies across pairs* (e.g. duplicated panels stacked
    vertically in one pair, side-by-side in another): the axis is lifted to the
    structural selector ``"auto"`` (resolved per input by ``_auto_split_axis``),
    so only the ``(op, colour)`` pair must be shared. Both passes carry the whole
    triple in ONE const leaf, so divergent fits still share the boolcombine
    skeleton and lift via ``unify()``."""

    def _axis_candidates(gin, gout, axis):
        """The ``(axis, op, colour)`` triples that reproduce ``gout`` exactly by
        combining ``gin``'s two ``axis`` panels — empty if the axis does not
        split or the panel size mismatches the output."""
        bg = background_of(gin)
        oh = len(gout)
        ow = len(gout[0]) if gout else 0
        panels = _split_for_axis(gin, axis)
        if panels is None:
            return set()
        A, B = panels
        h = len(A)
        w = len(A[0]) if A else 0
        if (h, w) != (oh, ow) or (len(B), len(B[0]) if B else 0) != (h, w):
            return set()
        found = set()
        out_colors = {gout[r][c] for r in range(h) for c in range(w)
                      if gout[r][c] != bg}
        # Boolean ops require a single output paint colour (the binarised
        # predicate is value-agnostic; the colour is read from the comparison).
        if len(out_colors) == 1:
            (color,) = tuple(out_colors)
            for op, pred in _BOOL_OPS.items():
                if all(gout[r][c] == (color if pred(A[r][c] != bg, B[r][c] != bg)
                                      else bg)
                       for r in range(h) for c in range(w)):
                    found.add((axis, op, color))
        # Colour-preserving merges read the panels' own colours (output may be
        # multi-colour). ``color`` is unused for a merge op, carried as ``None``
        # so the spec stays a 3-tuple sharing the boolcombine skeleton.
        for op, fn in _MERGE_OPS.items():
            if all(gout[r][c] == fn(A[r][c], B[r][c], bg)
                   for r in range(h) for c in range(w)):
                found.add((axis, op, None))
        return found

    # Pass 1 — single shared axis (original behaviour).
    inter = None
    for p in pairs:
        local = (_axis_candidates(p["input"], p["output"], "v")
                 | _axis_candidates(p["input"], p["output"], "h"))
        inter = local if inter is None else (inter & local)
        if not inter:
            break
    if inter:
        # ``color`` is ``None`` for merge ops, so sort with a None-safe key (a
        # merge op and a boolean op never both reproduce the same
        # multi/single-colour output, so this only orders ties within one
        # family; the lift is skeleton-identical either way).
        axis, op, color = sorted(
            inter, key=lambda t: (t[0], t[1], -1 if t[2] is None else t[2]))[0]
        return [("boolcombine", ("const", (axis, op, color)))]

    # Pass 2 — varying axis: select it structurally per input, share only (op, colour).
    inter2 = None
    for p in pairs:
        ax = _auto_split_axis(p["input"])
        if ax is None:
            return None
        local = {(op, color) for (_, op, color)
                 in _axis_candidates(p["input"], p["output"], ax)}
        inter2 = local if inter2 is None else (inter2 & local)
        if not inter2:
            return None
    op, color = sorted(
        inter2, key=lambda t: (t[0], -1 if t[1] is None else t[1]))[0]
    return [("boolcombine", ("const", ("auto", op, color)))]


def _connect_grid(grid, bg, spec):
    """Return a fresh grid: ``grid`` with every aligned same-colour marker pair
    joined by filling the background gap between them, in line colour ``spec``
    (``"same"`` = each pair's own marker colour, else a fixed colour int). Reads
    marker positions and the gap test from ``grid`` (the fixed input), so the fill
    is order-independent and value-agnostic."""
    H = len(grid)
    W = len(grid[0]) if grid else 0
    out = [row[:] for row in grid]
    by_color = {}
    for r in range(H):
        for c in range(W):
            v = grid[r][c]
            if v != bg:
                by_color.setdefault(v, []).append((r, c))
    for col, cells in by_color.items():
        line = col if spec == "same" else spec
        for i in range(len(cells)):
            r1, c1 = cells[i]
            for j in range(i + 1, len(cells)):
                r2, c2 = cells[j]
                if r1 == r2:
                    for c in range(min(c1, c2) + 1, max(c1, c2)):
                        if grid[r1][c] == bg:
                            out[r1][c] = line
                elif c1 == c2:
                    for r in range(min(r1, r2) + 1, max(r1, r2)):
                        if grid[r][c1] == bg:
                            out[r][c1] = line
    return out


def _fit_connect(pairs):
    """Return a one-step ``connect`` program if every pair's output is the input
    with aligned same-colour marker pairs joined by straight segments, painted in
    one shared line-colour spec, else ``None``.

    Each pair must be same-dims. The candidate specs are ``"same"`` (segment in the
    pair's own marker colour) and each fixed colour 0–9; the task spec is the
    *intersection* across pairs of the specs that reproduce that output exactly. A
    spec is accepted only if it actually changes at least one input (an all-no-op
    connect is the identity schema, already yielded). Carried as ONE ``const`` leaf
    so an own-colour task and a fixed-colour task lift via ``unify()`` into one
    ``covers>1`` rule (§2.5-3). ``"same"`` is preferred when several specs fit (the
    most value-agnostic), then the smallest fixed colour."""
    candidates = ["same"] + list(range(10))
    inter = None
    for p in pairs:
        gin, gout = p["input"], p["output"]
        if len(gin) != len(gout):
            return None
        if gin and (len(gin[0]) != len(gout[0])):
            return None
        bg = background_of(gin)
        local = set()
        for spec in candidates:
            if _connect_grid(gin, bg, spec) == gout:
                local.add(spec)
        inter = local if inter is None else (inter & local)
        if not inter:
            return None
    # Require the fit to actually draw something on at least one pair.
    changed = False
    for p in pairs:
        gin = p["input"]
        bg = background_of(gin)
        if any(_connect_grid(gin, bg, s) != gin for s in inter):
            changed = True
            break
    if not changed:
        return None

    def _rank(s):
        return (0, -1) if s == "same" else (1, s)

    spec = sorted(inter, key=_rank)[0]
    return [("connect", ("const", spec))]


# ======================================================================
# Crop to a selected sub-region (object-level selection — R1 / §2.5-2b)
# ======================================================================
#
# A "crop" output is a contiguous sub-rectangle of the input: the bounding box of
# a region *named by a value-agnostic selector*. The per-task content is the
# selector — which region to keep — exactly the §2.5-2b "selection is the real
# content" frontier: the choice is grounded in the example comparison, computed
# from the input alone (P5), never a stored coordinate box. The selector
# vocabulary reuses the object-level selection vocabulary already grown for R1
# (``agent/dsl_expr/selection.select_object``): on the *colour-aware* objects
# (``same_color=True`` — each maximal same-colour region a distinct object), the
# largest / smallest / unique-colour (``odd_color``) / unique-size region; plus
# ``content``, the bounding box of *all* non-background cells (no object model).
# All are pure functions of the input, so a selector fitted on the train pairs
# transfers unchanged to the test input.

_CROP_SELECTORS = ("content", "largest", "smallest", "odd_color", "unique_size")


def _crop_bbox(grid, bg, selector):
    """Bounding box ``(r0, c0, r1, c1)`` of the region ``selector`` names on
    ``grid``, or ``None`` when it does not resolve (empty grid, or a selector that
    declines — e.g. a tied size extreme). ``content`` is the box of all
    non-background cells; every other selector is an object-selection ``kind``
    resolved over the colour-aware objects (``select_object``)."""
    if selector == "content":
        cells = [(r, c) for r, row in enumerate(grid)
                 for c, v in enumerate(row) if v != bg]
        if not cells:
            return None
        rs = [r for r, _c in cells]
        cs = [c for _r, c in cells]
        return (min(rs), min(cs), max(rs), max(cs))
    objs = objects_of(grid, bg, same_color=True)
    obj = select_object(objs, {"kind": selector})
    if obj is None:
        return None
    return obj["bbox"]


def _crop_region(grid, bg, selector):
    """The cropped sub-grid ``selector`` names on ``grid`` (a fresh grid), or
    ``None`` when the selector does not resolve. Used by the fitter to test
    reproduction; ``run_program``'s ``crop`` step renders the same region from the
    two frozen primitives."""
    box = _crop_bbox(grid, bg, selector)
    if box is None:
        return None
    r0, c0, r1, c1 = box
    return [row[c0:c1 + 1] for row in grid[r0:r1 + 1]]


def _fit_crop(pairs):
    """Return a one-step ``crop`` program if every pair's output is the input
    cropped to one shared, value-agnostic selector's bounding box, else ``None``.

    The task selector is the *intersection* across pairs of the selectors that
    reproduce that output exactly. A selector is accepted only if it actually crops
    (the region is smaller than the input on at least one pair — a whole-grid crop
    is the identity schema, already yielded). Carried as ONE ``const`` leaf so two
    crop tasks with divergent selectors share the SAME one-step skeleton and lift
    via ``unify()`` into one ``covers>1`` rule (§2.5-3). The selectors are tried
    most-structural first (``content``, then the size extremes, then the
    odd-one-out criteria), mirroring the other fitters."""
    inter = None
    for p in pairs:
        gin, gout = p["input"], p["output"]
        bg = background_of(gin)
        local = {s for s in _CROP_SELECTORS
                 if _crop_region(gin, bg, s) == gout}
        inter = local if inter is None else (inter & local)
        if not inter:
            return None
    # Require the fit to actually shrink at least one input (else it's identity).
    changed = False
    for p in pairs:
        gin = p["input"]
        bg = background_of(gin)
        if any(_crop_region(gin, bg, s) != gin for s in inter):
            changed = True
            break
    if not changed:
        return None
    selector = sorted(inter, key=_CROP_SELECTORS.index)[0]
    return [("crop", ("const", selector))]


# The object properties an object-level recolour may key on, tried in order:
# ``size`` (cell count — one key per distinct size) and ``shape`` (the finer
# translation-normalised cell signature, used when same-size objects must take
# different colours), both *literal per-object* keys, before ``rank`` — the
# object's dense size-rank within its own grid (largest = 1). Rank is an *ordinal*
# selector: where a literal size/shape key declines on a test object whose
# absolute value was never seen in train (the literal-key non-transfer that costs
# most object-recolour covers), a rank key still resolves because ranks are small
# relative integers re-derived per grid (BACKLOG_LOOP §2.5-2b — lift the literal
# selector into a relative one that transfers to unseen keys). Tried *last* so it
# only takes a task the literal keys cannot fit deterministically (zero regression
# to the size/shape fits); the canonical 08ed6ac7 — where the same literal bar
# height carries different colours across pairs, so size is non-deterministic — is
# fit by rank. All three are pure functions of the input objects (the R1
# vocabulary), never a stored coordinate.
_RECOLOR_PROPS = ("size", "shape", "rank")


def _obj_key(obj, prop):
    """The value-agnostic property key an object recolour maps on. ``size`` → the
    object's cell count (an int); ``shape`` → its cells normalised to the bbox
    origin (a translation-invariant, hashable signature). Returns ``None`` for an
    unknown property name."""
    if prop == "size":
        return obj["size"]
    if prop == "shape":
        cells = obj["cells"]
        if not cells:
            return ()
        r0 = min(r for r, _c in cells)
        c0 = min(c for _r, c in cells)
        return tuple(sorted((r - r0, c - c0) for r, c in cells))
    return None


def _obj_keys(objs, prop):
    """The property keys for a whole object set, returned aligned with ``objs``.

    ``size`` and ``shape`` are *per-object* (delegated to `_obj_key`), so each key
    depends only on its own object. ``rank`` is *relative* — an object's dense
    size-rank within its own grid (largest object → 1, next distinct size → 2, …,
    ties sharing a rank) — which is why it is computed for the set at once: it reads
    every object's size. Rank is an ordinal selector that transfers to a test grid
    whose absolute sizes were never seen in train (BACKLOG_LOOP §2.5-2b), where a
    literal `size`/`shape` key would decline. Returns ``None`` entries for an
    unknown property name (mirroring `_obj_key`)."""
    if prop == "rank":
        sizes = sorted({obj["size"] for obj in objs}, reverse=True)
        rank_of = {s: i + 1 for i, s in enumerate(sizes)}
        return [rank_of[obj["size"]] for obj in objs]
    return [_obj_key(obj, prop) for obj in objs]


def _canon_key(k):
    """Canonicalise a stored map key to the same hashable form `_obj_key`
    produces, so a key serialised through JSON (tuples become lists) still matches
    a freshly-computed object key. Ints pass through; nested lists/tuples become
    tuples-of-tuples."""
    if isinstance(k, (list, tuple)):
        return tuple(_canon_key(x) for x in k)
    return k


def _fit_recolor_objects(pairs):
    """Fit an object-level recolour: every object is repainted in the colour a
    value-agnostic *property → colour* map assigns to it. Tries each property in
    `_RECOLOR_PROPS` (literal size, then shape, then the ordinal `rank`), building
    the map across all pairs and
    requiring it to be deterministic (no key → two colours) and every object to be
    recoloured *uniformly* (a single output colour over its cells); declines (tries
    the next property, then ``None``) otherwise. The map is carried as ONE const
    leaf, so two recolour tasks — keyed on size vs shape, or differing in the
    number of distinct keys — share the SAME one-step skeleton ``[("recolor_objects",
    ("const", ?v))]`` and lift via ``unify()`` into one ``covers>1`` rule (R3).

    Returns the one-step program, or ``None``. The final `_reproduces` gate keeps
    the fit honest: a map that does not reproduce every pair exactly (e.g. a
    background cell would change) is rejected rather than approximated."""
    for prop in _RECOLOR_PROPS:
        mapping = {}
        ok = True
        changed = False
        for p in pairs:
            gin, gout = p["input"], p["output"]
            if len(gin) != len(gout) or (
                    gin and len(gin[0]) != len(gout[0] if gout else [])):
                ok = False
                break
            bg = background_of(gin)
            objs = objects_of(gin, bg)
            if not objs:
                ok = False
                break
            keys = _obj_keys(objs, prop)
            for obj, k in zip(objs, keys):
                cols = {gout[r][c] for (r, c) in obj["cells"]}
                if len(cols) != 1:
                    ok = False
                    break
                newc = next(iter(cols))
                if k in mapping and mapping[k] != newc:
                    ok = False
                    break
                mapping[k] = newc
                if any(gin[r][c] != newc for (r, c) in obj["cells"]):
                    changed = True
            if not ok:
                break
        if not (ok and changed):
            continue
        spec = {
            "prop": prop,
            "map": [[list(k) if isinstance(k, tuple) else k, v]
                    for k, v in sorted(mapping.items(), key=lambda kv: repr(kv[0]))],
        }
        prog = [("recolor_objects", ("const", spec))]
        if _reproduces(prog, pairs):
            return prog
    return None


# The four gravity directions a `_fit_gravity` search tries, in a fixed order so
# the fit is deterministic. Each is carried as a single const leaf, so two gravity
# tasks differing only in direction share the same one-step skeleton and lift via
# `unify()` into one covers>1 rule (R3).
_GRAVITY_DIRS = ("down", "up", "left", "right")


def _fit_gravity(pairs):
    """Fit a cell-gravity: every non-background cell slides along one direction
    until blocked by the grid edge or a settled cell, per line, preserving order
    within the line. Tries each direction in `_GRAVITY_DIRS` and returns the
    one-step program ``[("gravity", ("const", direction))]`` for the first that
    reproduces **every** pair exactly, or ``None``.

    Requires same input/output dims and at least one pair where the output differs
    from the input (so a grid already settled — where gravity is a no-op — is not
    mis-claimed as a gravity task; the simpler identity schema owns that). The
    direction is the whole per-task content carried as ONE const leaf, so divergent
    directions lift via ``unify()`` into one ``covers>1`` rule (R3 — P1·P2·P3 rise
    together), never a rule per direction (§2.5-3/4). The final `_reproduces` gate
    keeps the fit honest — a direction that does not reproduce a pair exactly is
    rejected, not approximated."""
    for direction in _GRAVITY_DIRS:
        ok = True
        changed = False
        for p in pairs:
            gin, gout = p["input"], p["output"]
            if len(gin) != len(gout) or (
                    gin and len(gin[0]) != len(gout[0] if gout else [])):
                ok = False
                break
            if gin != gout:
                changed = True
        if not (ok and changed):
            continue
        prog = [("gravity", ("const", direction))]
        if _reproduces(prog, pairs):
            return prog
    return None


def _reproduces(prog, pairs):
    """True iff ``prog`` reproduces every pair's output from its input (declining
    — not crashing — on an input where a step does not resolve)."""
    for p in pairs:
        try:
            if run_program(prog, p["input"]) != p["output"]:
                return False
        except _Unevaluable:
            return False
    return True


# The stage-1 reductions a composition may prepend: crop to a selected region, or
# a dihedral re-orientation. Each is an existing single-step schema (so it is
# value-agnostic and already composes only the two frozen primitives); used here
# as a *preprocessing* stage whose intermediate grid is re-fitted by the
# single-step search. Bounded and small (so the composed search stays cheap), and
# every entry is a structural input transform, never a per-pair literal.
_STAGE1_REDUCTIONS = (
    tuple([("crop", ("const", s))] for s in _CROP_SELECTORS)
    + tuple([("dihedral", ("const", n))] for n in _DIHEDRAL)
)


def _synthesize_composed(pairs):
    """Two-step fallback: when no single-step schema reproduces the task, try a
    *structural stage-1 reduction* (crop / dihedral) followed by a re-fit of the
    single-step search on the transformed pairs (``[("compose", pre)] + post``).

    This is the spatial-then-spatial composition lever: it amplifies every
    existing schema by letting it apply after the input is cropped to its content
    (or a selected object) or re-oriented — the recurring ARC "find the relevant
    sub-grid, then transform it" family. Only reached as a fallback, so it cannot
    change any single-step solve (zero regression). The identity stage-2 is
    skipped (stage-1-alone is already its own ``crop``/``dihedral`` schema), so a
    composed program always does genuine work in *both* stages."""
    for pre in _STAGE1_REDUCTIONS:
        try:
            inter = [run_program(pre, p["input"]) for p in pairs]
        except _Unevaluable:
            continue
        pairs2 = [{"input": inter[i], "output": pairs[i]["output"]}
                  for i in range(len(pairs))]
        for post in _candidate_programs(pairs2):
            if not post:
                continue  # identity stage-2 ⇒ stage-1 alone, already a schema
            composed = [("compose", pre)] + list(post)
            if _reproduces(composed, pairs):
                return composed
    return None


def synthesize_task(pairs):
    """Search for one program reproducing **every** train pair's output from its
    input. Returns the program (a list of steps) or ``None``.

    ``pairs`` is a list of ``{"input": grid, "output": grid}`` dicts (the
    standard ARC train slice). The returned program is value-agnostic (every
    argument resolves from an input grid), so it applies unchanged to the test
    input. A ``None`` result is honest: the bounded search found no general
    program — it never falls back to a literal per-pair fit.

    A single-step schema is tried first; only when none fits does the bounded
    two-step composition fallback run (``_synthesize_composed``), so the
    composition can never displace a simpler single-step solve.
    """
    if not pairs:
        return None
    for prog in _candidate_programs(pairs):
        if _reproduces(prog, pairs):
            return prog
    return _synthesize_composed(pairs)
