"""
program_synthesis — the Slow-path *per-pair program producer* (modules F/G).

This is the first wired substrate slice of the **Slow-path program synthesizer**
that iters 20–22 (`logs/session_log.md`) and `arbor-modules.md` (Gap rows F/G)
converge on as the dominant remaining frontier. The producer side of arbor.md
진단 #4 is now fully canonical (every `GeneralizeOperator` family emits a
condition-bearing rule), but a task that *no* family recognizes falls straight to
the `identity` fallback and is unsolved: there is **no general path** that, for an
unrecognized pair, emits a concrete `coloring`/`make_grid` program so that
``program/anti_unification.anti_unify_pair_programs`` could lift ≥2 such programs
into one ``covers>1`` rule.

This module fills the *producer* half of that link, and nothing else:

    synthesize_pair_program(input, output) -> [ {"dsl", "args"}, ... ]
    run_program(program, input)            -> grid
    program_reproduces(program, in, out)   -> bool

Design boundaries (deliberate — keep the slice small and defensible):

* **Off the live path.** No operator, predictor, or `save_rule()` site imports
  this yet. Wiring it as the `identity`-fallback replacement (handing 2+
  pair-programs to ``save_rule() → unify()``) is a *later* slice — doing it here
  would risk the mastered easy_a/madeup regression guards and solve no new task
  this iter (the synthesizer chain only pays off once binding + object-level
  lifting land — `synthesizer_frontier` memory). So this iter adds the producer
  with a round-trip grounding test only.

* **Overfit material, by design (§2.5-3).** The emitted program is a *literal*
  reproduction of one pair — the per-pair overfit program BACKLOG_LOOP §2.5-3
  blesses **as anti-unification input material**, never as a standalone permanent
  rule. The cells are still raw coordinates here; lifting them to object-level
  selectors (``cells_of(select(objects, predicate))``, §2.5-2b / R1) so the
  skeleton actually generalizes is the explicitly-larger *next* slice, not this
  one. This producer's only contract is faithful reproduction.

* **Bottoms out in the two frozen primitives (F3).** Every line is a
  ``make_grid`` or ``coloring`` call dispatched through
  ``procedural_memory.DSL.apply.apply_DSL`` — no third transformation is
  introduced. Cells are grouped by target colour so a program carries one
  ``coloring`` line per output colour (a first scrap of structure over a flat
  per-cell dump), but the transformation vocabulary stays frozen at two.
"""

from collections import Counter

from procedural_memory.DSL.apply import apply_DSL
from agent.dsl_expr.selection import objects_of, SELECTOR_VOCAB


def _dims(grid):
    return len(grid), (len(grid[0]) if grid else 0)


def _same_size(a, b):
    return _dims(a) == _dims(b)


def _cells_by_color(grid, skip_color=None):
    """Map output colour -> row-major list of [r, c] cells, optionally skipping
    one background colour. Deterministic: colours and cells are emitted in sorted
    / row-major order so two runs (and two pairs) produce comparable programs."""
    groups = {}
    for r, row in enumerate(grid):
        for c, val in enumerate(row):
            if skip_color is not None and val == skip_color:
                continue
            groups.setdefault(val, []).append([r, c])
    return groups


def _coloring_lines(groups):
    """One ``coloring`` line per colour (ascending), painting that colour's
    cells. Empty groups produce no line."""
    lines = []
    for color in sorted(groups):
        cells = groups[color]
        if cells:
            lines.append({"dsl": "coloring",
                          "args": {"selection": cells, "color": color}})
    return lines


def synthesize_pair_program(input_grid, output_grid):
    """Emit a literal program that reproduces ``output_grid`` from ``input_grid``.

    Two cases, both bottoming out in the frozen primitives:

    * **same size** — paint only the cells that differ, grouped by their output
      colour (the input is the starting canvas). An unchanged pair yields the
      empty program ``[]`` (``run_program`` then returns the input verbatim).
    * **different size** — open a fresh ``make_grid`` canvas filled with the
      output's most-common colour (the background), then paint every non-background
      cell, grouped by colour.

    Returns a list of ``{"dsl", "args"}`` program lines. The result is *overfit
    material* for ``anti_unify_pair_programs`` (§2.5-3), not a saveable rule.
    """
    if not output_grid or not output_grid[0]:
        return []

    if _same_size(input_grid, output_grid):
        changed = {}
        for r, (irow, orow) in enumerate(zip(input_grid, output_grid)):
            for c, (iv, ov) in enumerate(zip(irow, orow)):
                if iv != ov:
                    changed.setdefault(ov, []).append([r, c])
        return _coloring_lines(changed)

    # Resize: a fresh canvas + painted foreground.
    h, w = _dims(output_grid)
    flat = [v for row in output_grid for v in row]
    background = Counter(flat).most_common(1)[0][0]
    program = [{"dsl": "make_grid",
                "args": {"height": h, "width": w, "color": background}}]
    program.extend(_coloring_lines(_cells_by_color(output_grid, skip_color=background)))
    return program


# ---------------------------------------------------------------------------
# Object-level recolor producer (the §2.5-2b / R1 *liftable* pair program)
# ---------------------------------------------------------------------------
#
# `synthesize_pair_program` above emits a *raw-cell* program: its `coloring`
# selection is a literal list of coordinates. That program reproduces its pair
# faithfully, but it is the wall iter22/23 named (memory `synthesizer_frontier`,
# wall (a)): two raw-cell programs from different tasks share **no** liftable
# skeleton — anti-unification sees two unrelated coordinate lists and collapses
# the *whole selection* into one variable, so the COMM ("which object is
# recolored") is lost and the lift degrades to a literal again (the 168-rule
# failure, BACKLOG_LOOP §2.5-2).
#
# This producer closes that wall for the *recolor* case — the one that "lifts
# cleanly and avoids the open-question origins" (iter23 Next-gap): the object is
# not displaced (no target/origin ambiguity → no `arbor-open-questions` design
# decision), only repainted. Instead of literal cells, the `coloring` selection
# is an **object-level selection expression** ``{"select": <selector-name>}`` —
# the §2.5-2b lift: "the object", named by a selector (`unique` / `max_size` /
# `unique_color` / …), not by its coordinates. Two such programs that name the
# object the *same* way share that expression as common skeleton, so
# anti-unification lifts only the *differing* colour to a variable while the
# selector survives — the first object-level pair program whose lift is
# meaningful. Still off the live path and overfit material for AU (§2.5-3), like
# the raw-cell producer; binding the lifted colour at predict time (§2.5-2b) and
# wiring as the `identity`-fallback remain the explicitly-later, easy_a-guarded
# slices.

def _recolor_selectors():
    """Selector vocabulary for *naming* the recolored object, in deterministic
    trial order. ``unique`` is the degenerate single-object selector; the rest
    (``SELECTOR_VOCAB``) pick one object among many by a named criterion. Each
    yields ``(name, fn(objects, grid) -> object | None)``."""
    yield "unique", lambda objs, grid: objs[0] if len(objs) == 1 else None
    for name, fn in SELECTOR_VOCAB.items():
        yield name, fn


def _cells_set(obj):
    return {tuple(cell) for cell in obj["cells"]}


def _name_selector(objs, grid, target):
    """The first selector that *unambiguously* names ``target`` among ``objs``,
    or None. The selector is the §2.5-2b lifted argument — discovered, not
    assumed; returning None keeps the producer honest when no named criterion
    singles the recolored object out."""
    target_cells = _cells_set(target)
    for name, fn in _recolor_selectors():
        chosen = fn(objs, grid)
        if chosen is not None and _cells_set(chosen) == target_cells:
            return name
    return None


def synthesize_object_recolor_program(input_grid, output_grid):
    """Emit an *object-level* program for a same-size single-object recolor, or
    None when the pair is not one.

    A recolor pair here is: same size, the changed cells are exactly the cells of
    **one** input foreground object, and they all change to a single new colour.
    The emitted program is one ``coloring`` line whose selection is the
    object-level expression ``{"select": <selector-name>}`` (not literal cells)
    and whose colour is the new colour. Returns None (caller falls back to the
    raw-cell `synthesize_pair_program`) when the pair is not a clean object
    recolor or no selector names the object unambiguously.
    """
    if not output_grid or not output_grid[0] or not _same_size(input_grid, output_grid):
        return None

    changed = set()
    new_colors = set()
    for r, (irow, orow) in enumerate(zip(input_grid, output_grid)):
        for c, (iv, ov) in enumerate(zip(irow, orow)):
            if iv != ov:
                changed.add((r, c))
                new_colors.add(ov)
    if not changed or len(new_colors) != 1:
        return None
    new_color = next(iter(new_colors))

    objs = objects_of(input_grid)
    target = next((o for o in objs if _cells_set(o) == changed), None)
    if target is None:
        return None

    selector = _name_selector(objs, input_grid, target)
    if selector is None:
        return None

    return [{"dsl": "coloring",
             "args": {"selection": {"select": selector}, "color": new_color}}]


def _resolve_selection(selection, grid):
    """Resolve a `coloring` selection against the running grid.

    A literal coordinate list passes through unchanged (the raw-cell producer's
    output). An object-level selection expression ``{"select": <name>}`` is
    resolved by running the named selector over the grid's objects and returning
    its cells (or ``[]`` when the selector declines — coloring then paints
    nothing, a faithful no-op rather than a crash)."""
    if isinstance(selection, dict) and "select" in selection:
        objs = objects_of(grid)
        for name, fn in _recolor_selectors():
            if name == selection["select"]:
                chosen = fn(objs, grid)
                return [list(cell) for cell in chosen["cells"]] if chosen else []
        return []
    return selection


def run_program(program, input_grid):
    """Execute a synthesized program line-by-line through the frozen DSL.

    ``make_grid`` ignores the incoming grid (fresh canvas); ``coloring`` paints
    the running grid. A `coloring` line's selection is first resolved via
    :func:`_resolve_selection`, so both raw-cell and object-level (``{"select":
    …}``) selections execute through the same frozen primitive. Returns the final
    grid; the input is never mutated.
    """
    grid = [row[:] for row in input_grid]
    for line in program:
        args = dict(line.get("args", {}))
        if "selection" in args:
            args["selection"] = _resolve_selection(args["selection"], grid)
        grid = apply_DSL(line["dsl"], grid, **args)
    return grid


def program_reproduces(program, input_grid, output_grid):
    """True iff running ``program`` on ``input_grid`` yields ``output_grid``."""
    return run_program(program, input_grid) == output_grid
