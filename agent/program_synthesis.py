"""
agent.program_synthesis — the Slow-path per-pair program *synthesizer*
(ARBOR modules F/G; `arbor.md` Fast/Slow path, BACKLOG_LOOP.md R5).

The diagnosed gap this fills (iter-25 reframe, verified against the code).
-----------------------------------------------------------------------
`agent/active_operators.py:GeneralizeOperator.effect` is a fixed
`match_condition(X) → _build_X_rule(X)` chain over a set of *pre-built in-code
families* (`_derive_color_map`, `_derive_scale_factor`, `_build_place_object_*`,
…). A task that no family recognizes falls through to the `identity` rule and is
left unsolved. So a genuinely new task *category* has nowhere to go **but** a new
in-code family — which is the `_try_*`-style accretion the project diagnoses
(it slips past the literal F2 regex, but violates `CLAUDE.md §6.2`: "the
discovered layer is *data, not code*") and is why `active_operators.py` grew from
~1280 to ~2230 lines over the run with no matching covers growth.

The missing piece is a *general Slow path*: given a single example pair's
COMM/DIFF, emit an **overfit, literal `coloring`/`make_grid` program** that
reconstructs that pair's output. Such per-pair programs are exactly the material
`BACKLOG_LOOP.md §2.5-3` blesses as anti-unification *input* — overfit is allowed
**as material**, the failure is overfit *accreted as permanent rules*. With 2+
of them in hand, `program/anti_unification.py` lifts them into one `covers>1`
data rule (the `anti_unify_pair_programs` stub there is the term-tree consumer
this program format is shaped for). That is the §6.2-intended "discovered layer
is data" path — the alternative to minting a tenth `_build_X` family.

Scope of THIS slice (deliberately small — PROMPT.md §2 "smallest half").
-----------------------------------------------------------------------
This module is the **pure synthesizer function only**, grounded by a round-trip
test on real `easy000c/d` pairs (`tests/test_program_synthesis.py`). It is
**not yet wired** into `GeneralizeOperator` as the `identity`-fallback: wiring it
so 2+ synthesized programs reach `save_rule()→unify()` is the *next* slice, kept
separate because it touches the live solve path and carries an easy_a-regression
risk that wants its own iter. A pure function verified by a real-pair round-trip
is grounded capability, not a speculative dead brick — the round-trip test is the
ground.

Program representation (P7 — symbolic dicts + json, no vectors).
-----------------------------------------------------------------------
A *program* is a flat list of step dicts, each naming one of the two frozen
primitives and its literal args::

    {"dsl": "make_grid", "args": {"height": H, "width": W, "color": bg}}
    {"dsl": "coloring",  "args": {"selection": [[r, c], ...], "color": v}}

Coordinates are plain `[row, col]` lists (json-stable) grouped one `coloring`
step per colour, emitted in ascending colour order for determinism — so a future
term-tree `unify()` aligns the same colour positions across pairs rather than
fighting step-ordering noise.

Everything here is deterministic and side-effect-free.
"""

from procedural_memory.DSL.apply import apply_DSL
from agent.dsl_expr import background_color


def _dims(grid):
    """(height, width) of a raw 2D grid; (0, 0) for an empty grid."""
    return (len(grid), len(grid[0]) if grid else 0)


def _cell_diff(input_grid, output_grid):
    """The pixel-level COMM/DIFF of two same-shape grids: a list of
    `(row, col, new_color)` for every cell whose colour changed.

    This *is* the comparison receipt at pixel granularity — COMM cells (unchanged)
    contribute no program step, only DIFF cells are repainted. That the program's
    steps come from the comparison's DIFF, not from re-emitting the whole grid, is
    the P3/P4 discipline ("the answer's steps come from the comparison result")
    expressed at the lowest level."""
    diffs = []
    for r, (in_row, out_row) in enumerate(zip(input_grid, output_grid)):
        for c, (a, b) in enumerate(zip(in_row, out_row)):
            if a != b:
                diffs.append((r, c, b))
    return diffs


def _coloring_steps(cells_by_color):
    """Turn a {color: [[r, c], ...]} map into one `coloring` step per colour,
    colours ascending for determinism (P7)."""
    return [
        {"dsl": "coloring", "args": {"selection": cells_by_color[color], "color": color}}
        for color in sorted(cells_by_color)
    ]


def synthesize_pair_program(input_grid, output_grid, comparison=None):
    """Emit a literal `coloring`/`make_grid` program reconstructing `output_grid`
    from `input_grid`. Returns a flat list of step dicts (see module docstring).

    Two synthesis modes, chosen by the coarsest COMM/DIFF — do the shapes agree?

      - **same shape → a DIFF program.** One `coloring` step per cell that
        changed, painting it to its output colour; unchanged (COMM) cells are left
        as the input carries them, so the program *edits* rather than rebuilds
        (P1: act only where needed). An identity pair yields the empty program.
      - **different shape → a from-scratch program.** `make_grid(H, W, bg)` lays
        the output background (`bg` = its most-frequent colour via
        `dsl_expr.background_color`), then one `coloring` step per non-background
        output cell. The input cannot be edited in place once the canvas resizes,
        so the output is built fresh on its own background.

    The emitted program is intentionally **overfit** — pair-specific literal cells
    and colours. That is correct here: an overfit per-pair program is
    anti-unification *input material* (`BACKLOG_LOOP.md §2.5-3`), not a rule to
    persist. Lifting a set of them into one `covers>1` rule is `unify()`'s job, not
    this function's.

    `comparison` is accepted for forward-compatibility with the ARCKG COMM/DIFF
    receipt the cycle's `compare` operator produces; the pixel diff is recomputed
    locally (it is the same information at pixel granularity) so the synthesizer is
    usable — and testable — standalone, without a full ARCKG comparison in hand."""
    if _dims(input_grid) == _dims(output_grid):
        cells_by_color = {}
        for r, c, color in _cell_diff(input_grid, output_grid):
            cells_by_color.setdefault(color, []).append([r, c])
        return _coloring_steps(cells_by_color)

    height, width = _dims(output_grid)
    bg = background_color(output_grid)
    program = [{"dsl": "make_grid", "args": {"height": height, "width": width, "color": bg}}]
    cells_by_color = {}
    for r, row in enumerate(output_grid):
        for c, color in enumerate(row):
            if color != bg:
                cells_by_color.setdefault(color, []).append([r, c])
    program.extend(_coloring_steps(cells_by_color))
    return program


def run_program(program, input_grid):
    """Replay a synthesized `program` against `input_grid` and return the produced
    grid. A `make_grid` step ignores the running grid (it builds a fresh canvas);
    a `coloring` step paints onto it. Steps dispatch through the frozen
    `apply_DSL`, so the executor introduces no new transformation vocabulary.

    This is the shared executor: the round-trip test asserts
    `run_program(synthesize_pair_program(i, o), i) == o`, and the future fast path
    will replay an instantiated rule's program the same way. Synthesis is only
    trustworthy if that round-trip holds."""
    grid = input_grid
    for step in program:
        name, args = step["dsl"], step["args"]
        if name == "make_grid":
            grid = apply_DSL("make_grid", None,
                             height=args["height"], width=args["width"], color=args["color"])
        elif name == "coloring":
            selection = [tuple(cell) for cell in args["selection"]]
            grid = apply_DSL("coloring", grid, selection=selection, color=args["color"])
        else:
            raise KeyError(f"unknown program step dsl: {name!r}")
    return grid
