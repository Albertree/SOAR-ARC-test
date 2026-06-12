"""
agent.object_synthesis — *object-level* per-pair program synthesis
(BACKLOG_LOOP.md R1 / §2.5-2b; the training frontier iter-29 named).

The gap this closes (iter-29 finding, verified against the code).
-----------------------------------------------------------------------
`agent/program_synthesis.py` synthesizes a per-pair program at **pixel**
granularity: one `coloring` step per changed cell, with the changed cells written
as a *raw literal cell-list*. That format is round-trip-correct, and the
synthesize→AU→bind→instantiate→run chain (iters 26→29) is complete for it — but
it has a structural ceiling iter-29 measured (0/120 on an ARC-AGI-2 training
sample): **the object→transform structure is destroyed at synthesis time.** When
two pairs recolour "the largest object", their changed cells differ literally, so
`anti_unify_pair_programs` lifts the whole cell-list to a `?vN` hole, and no
binder origin in the seed set recovers *why* those particular cells (which object,
chosen how). The selection has to be expressed object-relationally **before** the
lift, not reconstructed after it.

This module is the producer side of that fix. It synthesizes the recolour case as
an **object-relational** program::

    [{"dsl": "coloring",
      "args": {"selection": {"select": "argmax", "key": "size_of",
                             "from": "objects_of(in)"},
               "color": 4}}]

The `selection` is a symbolic expression tree (P7) over the seed object
vocabulary in `agent/dsl_expr` (`objects_of`, `unique`, `argmax`/`argmin` by
`size_of`, `cells_of`) — never a raw cell-list. Two such programs for "recolour
the largest" are now **literally identical** (the selector and the new colour are
the cross-pair COMM), so `anti_unify_pair_programs` keeps the selector as a COMM
literal and the lift yields a *directly instantiable* `covers>1` program with no
unbound hole — exactly the structure pixel-level synthesis loses. (Contrast: the
pixel programs for the same pairs lift the selection to a `?vN`.)

Which selector? — derived from the comparison, not guessed (P3/P4, §2.5-2b).
-----------------------------------------------------------------------
A *single* pair cannot say whether its changed object is "the largest", "the
unique", or "the one at (2,2)": all describe the same cells. The disambiguation
is the **cross-pair COMM** — the one seed selector that reproduces every pair's
changed object from that pair's input. `largest_recolor`'s three pairs agree only
on `argmax(size_of)`; `smallest_recolor`'s only on `argmin(size_of)`; a
single-object-per-pair task admits `unique` (preferred, the simplest). If no
single seed selector is consistent across all pairs, the synthesizer **declines**
(returns None) rather than pick arbitrarily — the same no-guess discipline the
selectors themselves use on a tie. This is the §2.5-2b principle made concrete:
each transformation hole's filling is *selected from the comparison evidence*, and
the evidence is what holds across the pairs.

Scope of THIS slice (PROMPT.md §2 "smallest half").
-----------------------------------------------------------------------
Only the **single-object recolour** case (same-shape pair, the changed cells are
exactly one object's cells, one constant new colour across pairs). This is the
narrowest object-level family that exercises the producer-side lift end-to-end on
real held-out data (`largest_recolor`/`smallest_recolor`, two directions, two
colours — value-agnostic). It is a *pure function plus a resolver/executor*, off
the live solve path, grounded by running the synthesized program on the held-out
**test** input and getting the answer. Moves where the new colour varies per pair
(an origin-bound hole) or the change is not a whole-object recolour are out of
scope — the synthesizer declines, surfacing the next gap honestly rather than
guessing through it.

Everything here is deterministic and side-effect-free (P7).
"""

from agent import dsl_expr
from procedural_memory.DSL.apply import apply_DSL


#: The seed selector vocabulary, in *preference order* (most general / simplest
#: first). Each entry is a symbolic selection expression over `objects_of(in)`
#: and a resolver that applies it to a concrete object list. The order decides
#: which selector wins when several are consistent across the pairs — `unique`
#: (a task with one object per grid) before the ranking selectors, so the
#: simplest true description is chosen (determinism over an arbitrary pick, P7).
#: This vocabulary *grows* (it is argument material, not a transformation — it
#: lives under `agent/`, not the frozen `procedural_memory/DSL/`, §2.5-1); adding
#: `argmax(color count)` etc. is a one-line extension here, never a new primitive.
_SEED_SELECTORS = [
    ({"select": "unique", "from": "objects_of(in)"},
     lambda objs: dsl_expr.unique(objs)),
    ({"select": "argmax", "key": "size_of", "from": "objects_of(in)"},
     lambda objs: dsl_expr.argmax(objs, dsl_expr.size_of)),
    ({"select": "argmin", "key": "size_of", "from": "objects_of(in)"},
     lambda objs: dsl_expr.argmin(objs, dsl_expr.size_of)),
]


def _norm_cells(cells):
    """A set of (row, col) tuples from any cell iterable (frozenset / list of
    [r, c] / list of (r, c)) — the comparison basis selectors are matched on."""
    return {tuple(cell) for cell in cells}


def resolve_selection(expr, grid):
    """Evaluate a symbolic selection `expr` against `grid`, returning the selected
    object's cells as a sorted list of `[row, col]` (json-stable, P7), or None
    when the selection declines (no object / ambiguous tie — the seed selectors'
    own discipline).

    The inverse of `_selection_candidates`: this is what the executor and the
    future fast path use to turn the stored object-relational selection back into
    the concrete cells handed to the frozen `coloring` primitive on a *test* grid
    — `coloring(cells_of(argmax(objects_of(test), size_of)), v)` resolved against
    the test input (never an output: P5)."""
    objs = dsl_expr.objects_of(grid)
    for selector, resolve in _SEED_SELECTORS:
        if selector == expr:
            obj = resolve(objs)
            if obj is None:
                return None
            return sorted([r, c] for (r, c) in dsl_expr.cells_of(obj))
    raise KeyError(f"unknown selection expr: {expr!r}")


def _selection_candidates(grid, cells):
    """The seed selectors (in preference order) whose selected object's cells
    equal `cells` on `grid`. Empty when no seed selector picks exactly that
    object — i.e. the change is not a whole-object recolour this vocabulary can
    name (the synthesizer then declines, an honest surface of the next gap)."""
    target = _norm_cells(cells)
    objs = dsl_expr.objects_of(grid)
    out = []
    for selector, resolve in _SEED_SELECTORS:
        obj = resolve(objs)
        if obj is not None and _norm_cells(dsl_expr.cells_of(obj)) == target:
            out.append(selector)
    return out


def _recolor_change(input_grid, output_grid):
    """If `input_grid`→`output_grid` is a same-shape, single-new-colour recolour,
    return `(changed_cells, new_color)`; else None.

    `changed_cells` is the set of (row, col) that changed; `new_color` is the sole
    colour they all became. None when the shapes differ, nothing changed, or the
    changed cells did not all become the *same* colour (a multi-colour edit is not
    a single-object recolour — out of this slice's scope)."""
    if len(input_grid) != len(output_grid):
        return None
    changed, new_colors = set(), set()
    for r, (in_row, out_row) in enumerate(zip(input_grid, output_grid)):
        if len(in_row) != len(out_row):
            return None
        for c, (a, b) in enumerate(zip(in_row, out_row)):
            if a != b:
                changed.add((r, c))
                new_colors.add(b)
    if not changed or len(new_colors) != 1:
        return None
    return changed, next(iter(new_colors))


def synthesize_object_recolor(pairs):
    """Synthesize an **object-relational** recolour program from the example
    `pairs` (a list of `(input_grid, output_grid)`), or None if the pairs are not
    a single-object recolour this seed vocabulary can name consistently.

    Returns a one-step program::

        [{"dsl": "coloring",
          "args": {"selection": <seed selector expr>, "color": <new colour>}}]

    The selector is the single seed selector consistent across *every* pair (the
    cross-pair COMM, §2.5-2b); the colour is the constant new colour. Declines
    (returns None) when:

      - any pair is not a same-shape single-new-colour recolour,
      - the new colour is not constant across the pairs (it would be an
        origin-bound hole — out of this slice's scope, surfaced not guessed),
      - no single seed selector reproduces the changed object in *every* pair
        (the change is not a uniformly-describable whole-object recolour).

    Unlike the pixel synthesizer this emits a selector, not literal cells, so two
    pairs of the same family synthesize to the *identical* program — the object
    structure survives `anti_unify_pair_programs` as a COMM literal instead of
    collapsing to an unbindable `?vN`."""
    if not pairs:
        return None

    new_colors = set()
    candidate_sets = []
    for in_grid, out_grid in pairs:
        change = _recolor_change(in_grid, out_grid)
        if change is None:
            return None
        changed_cells, new_color = change
        new_colors.add(new_color)
        candidate_sets.append(_selection_candidates(in_grid, changed_cells))

    if len(new_colors) != 1:
        return None  # per-pair colour: an origin hole, not in this slice
    new_color = next(iter(new_colors))

    # The selector is the cross-pair COMM: consistent across every pair, picked in
    # preference order so the simplest true description wins (P7 determinism).
    for selector, _ in _SEED_SELECTORS:
        if all(selector in cands for cands in candidate_sets):
            return [{"dsl": "coloring",
                     "args": {"selection": selector, "color": new_color}}]
    return None


def run_object_program(program, input_grid):
    """Replay an object-relational `program` against `input_grid`, resolving each
    selection expression on *this* grid before painting (P5: the test input, never
    an output). Returns the produced grid, or None if any selection declines on
    this grid (no matching object / tie) — the same no-guess abstention the
    selectors carry, propagated to the executor so a rule that cannot apply to a
    test input fails honestly rather than painting nothing.

    Steps dispatch through the frozen `apply_DSL`, so — like
    `program_synthesis.run_program` — this executor introduces no new
    transformation vocabulary; it only resolves the *argument* expressions the
    object-level synthesizer puts in `selection`."""
    grid = input_grid
    for step in program:
        name, args = step["dsl"], step["args"]
        if name == "coloring":
            selection = args["selection"]
            if isinstance(selection, dict):
                cells = resolve_selection(selection, grid)
                if cells is None:
                    return None
                selection = cells
            painted = [tuple(cell) for cell in selection]
            grid = apply_DSL("coloring", grid, selection=painted, color=args["color"])
        elif name == "make_grid":
            grid = apply_DSL("make_grid", None,
                             height=args["height"], width=args["width"], color=args["color"])
        else:
            raise KeyError(f"unknown program step dsl: {name!r}")
    return grid
