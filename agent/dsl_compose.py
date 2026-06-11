"""
dsl_compose — build DSL *programs* (compositions of the two frozen primitives)
that reconstruct a target grid.

This is the bridge between *recognition* (a condition matcher fired) and
*action* (materialise the answer). CLAUDE.md §6 freezes the hand-coded
transformation vocabulary at exactly two primitives — `make_grid` and
`coloring` — and requires every other transformation to be a *composition* of
those two. This module constructs one such composition: given a concrete target
grid, it emits the `make_grid` + `coloring` recipe that rebuilds it.

The recipe is plain JSON-serialisable data (a list of `{dsl, args}` steps), so
it can ride inside a rule's `action` and later be executed by `apply_DSL`
(PredictOperator). It is **value-agnostic**: every dimension, background colour
and painted coordinate is read from the supplied grid — no literal answer is
baked in (slice doc §9 guardrail). The same routine rebuilds *any* grid, so it
is a general module, not a per-task special case (observation criterion 2).

It is the recognition half, in `agent/conditions/constant_output.py`, that
decides *when* this composition is the right answer; this module only says
*how* to materialise a given grid as make_grid+coloring.
"""

from collections import Counter


def _background_color(grid) -> int:
    """The most frequent colour in `grid` — the canvas `make_grid` starts from.

    Choosing the modal colour minimises the number of `coloring` overlays the
    composition needs (every non-background colour costs one paint step). Ties
    resolve to the smallest colour index for determinism.
    """
    counts = Counter(cell for row in grid for cell in row)
    if not counts:
        return 0
    most = max(counts.values())
    return min(c for c, n in counts.items() if n == most)


def build_constant_output_program(grid) -> list:
    """Return a make_grid+coloring program that reconstructs `grid`.

    Shape::

        [
          {"dsl": "make_grid", "args": {"height": H, "width": W, "color": bg}},
          {"dsl": "coloring",  "args": {"selection": [[r, c], ...], "color": k}},
          ... one coloring step per non-background colour k ...
        ]

    Coordinates are lists (not tuples) so the program survives a JSON round-trip
    unchanged; `coloring` accepts either. Returns ``None`` for an empty/ragged
    grid (nothing defensible to build). Pure and deterministic.
    """
    if not grid or not isinstance(grid, list) or not grid[0]:
        return None

    height = len(grid)
    width = len(grid[0])
    if any(len(row) != width for row in grid):
        return None  # ragged grid — refuse rather than guess

    bg = _background_color(grid)

    program = [
        {"dsl": "make_grid", "args": {"height": height, "width": width, "color": bg}},
    ]

    # One coloring overlay per non-background colour, painting exactly the cells
    # that hold it. Colours are sorted for a deterministic program.
    cells_by_color = {}
    for r, row in enumerate(grid):
        for c, val in enumerate(row):
            if val == bg:
                continue
            cells_by_color.setdefault(val, []).append([r, c])

    for color in sorted(cells_by_color):
        program.append({
            "dsl": "coloring",
            "args": {"selection": cells_by_color[color], "color": color},
        })

    return program
