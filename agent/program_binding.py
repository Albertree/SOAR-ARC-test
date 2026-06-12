"""
agent.program_binding — bind an anti-unified program's `?vN` holes to G0-origin
expressions (BACKLOG_LOOP.md R1 / §2.5-2b; the §6.2 "discovered layer is data"
path's missing completion step).

The diagnosed gap this fills (iter-28, verified empirically against the code).
-----------------------------------------------------------------------
`agent/program_synthesis.py:synthesize_pair_program` emits an overfit, literal
`coloring`/`make_grid` program per example pair, and
`program/anti_unification.py:anti_unify_pair_programs` lifts 2+ of them into one
abstract program whose differing arg positions become `?vN` variables. Running
that producer→consumer pair on real data shows it works *structurally* but leaves
a **semantically incomplete** product. For `easy000c` the lift is::

    [ {"dsl": "coloring", "args": {"selection": "?v1",     "color": 0}},
      {"dsl": "coloring", "args": {"selection": [[5, 5]],  "color": "?v2"}} ]

The invariant corner target `[[5, 5]]` survives as a literal (the COMM — good),
but `?v1` (the source cell to erase) and `?v2` (the colour to paint) are **holes
with no rule for how to fill them from a test input**. Persisting such a program
as a `covers>1` rule would produce something *uninstantiable* on a test G0: at
apply time the test pair has no G1, so the holes cannot be read off the answer
(P5). This is exactly the §2.5-2b problem — "the AU product is incomplete; each
hole's *filling* must be grounded in the comparison (P3/P4), and selected, not
invented." Until the holes carry a G0-origin expression, the lifted abstraction
is dead memory, and wiring synthesis→AU→persist (the iter-27 next-gap) would
actively regress by minting uninstantiable rules.

What this module does (the missing link, deliberately small).
-----------------------------------------------------------------------
Given the abstract program, the per-pair programs it was lifted from, and the
per-pair *input* grids, bind each `?vN` to a G0-origin expression drawn from the
already-existing seed vocabulary in `agent/dsl_expr` (`unique`, `objects_of`,
`cells_of`, `color_of`) — choosing, over a **bounded, ordered candidate set**,
the first origin that **reproduces every pair's literal value from that pair's
input**. That criterion is the same example-reproduction discipline
`agent/variable_resolution.py:resolve_variable` uses to fill a family rule's
`target_mode` hole; here it fills a *synthesized program's* hole instead, so the
two are complementary, not duplicate (one selects a mode, this selects an origin
expression). A hole no candidate reproduces is left as its `?vN` marker — the
program is then correctly *not* fully grounded (the caller must not persist it as
self-applying), which honestly surfaces the next missing origin (e.g. a moved
object's *target* position is `source + Δ`, a relation the seed set does not yet
express — see `easy000e`).

This module **invents no new origin**: like `variable_resolution`, it only
*selects* among a fixed set of known G0 readings. Coining a brand-new
derive-expression for a hole (e.g. "target == source offset by the COMM Δ") is
the open question Q-B3/Q-B4 (`arbor-open-questions.md`) and stays out of scope.

This grows the **argument/selection** vocabulary under `agent/` (BACKLOG_LOOP.md
§2.5-1), not the frozen transformation DSL — it adds no `def` to
`procedural_memory/DSL/` (F3 N/A) and does not touch `active_operators.py`
(F8 N/A). Everything here is deterministic and side-effect-free (P7).
"""

from agent.dsl_expr import objects_of, unique, cells_of, color_of


def _is_var(value) -> bool:
    """True iff `value` is an anti-unification hole marker (`?vN`)."""
    return isinstance(value, str) and value.startswith("?v")


def _norm_cells(value):
    """Normalize a `selection` value (list of `[r, c]`, or any iterable of
    `(r, c)`) to a sorted list of `[r, c]`, so two cell sets compare equal
    regardless of emission order. None on a non-cell value."""
    if value is None:
        return None
    try:
        return sorted([list(cell) for cell in value])
    except (TypeError, ValueError):
        return None


# ---- G0-origin candidate expressions (the seed selection set, §2.5-2b) ------
# Each origin reads a value from a *single input grid* using only the existing
# agent/dsl_expr vocabulary. The set is intentionally small and ordered: the
# first origin that reproduces every pair's literal wins (determinism, P7). It
# grows here under agent/ as new selections become necessary — never in the
# frozen transformation DSL.

def _origin_source_cells(input_grid):
    """`cells_of(unique(objects_of(in)))` — the cells of the input's sole
    foreground object, normalized. None when the input has no unique object."""
    obj = unique(objects_of(input_grid))
    if obj is None:
        return None
    return _norm_cells(cells_of(obj))


def _origin_source_color(input_grid):
    """`color_of(unique(objects_of(in)))` — the colour of the input's sole
    foreground object. None when there is no unique (single-coloured) object."""
    obj = unique(objects_of(input_grid))
    if obj is None:
        return None
    return color_of(obj)


# Per-arg-kind candidate origins + the comparator that normalizes a literal to
# the origin's value space. `selection` holes compare as cell sets; `color`
# holes compare as plain ints.
_ARG_ORIGINS = {
    "selection": ([("source_cells", _origin_source_cells)], _norm_cells),
    "color": ([("source_color", _origin_source_color)], lambda v: v),
}


def _bind_one(arg_key, literals, pair_inputs):
    """Return the origin name whose expression reproduces every `literals[i]`
    from `pair_inputs[i]`, or None if no bounded candidate matches (or the arg
    kind has no candidate set). `literals` are the per-pair literal values that
    occupied this hole in the synthesized programs."""
    candidates_norm = _ARG_ORIGINS.get(arg_key)
    if candidates_norm is None:
        return None
    candidates, norm = candidates_norm
    for name, origin in candidates:
        produced = [origin(g) for g in pair_inputs]
        if any(p is None for p in produced):
            continue
        if all(produced[i] == norm(literals[i]) for i in range(len(literals))):
            return name
    return None


def bind_program_variables(abstract_program, pair_programs, pair_inputs):
    """Bind the `?vN` holes of `abstract_program` to G0-origin expressions.

    Args:
        abstract_program: the lifted program from
            `program.anti_unification.anti_unify_pair_programs` — a flat list of
            `{"dsl", "args"}` steps in which some arg values are `?vN` markers.
        pair_programs: the per-pair synthesized programs it was lifted from (same
            length / skeleton), supplying each hole's literal value per pair.
        pair_inputs: the raw input grid of each example pair, in the same order
            as `pair_programs`. The origin expressions read from *these inputs*
            (G0), never from an output (P5).

    Returns `(bound_program, unbound)`:
        bound_program: a deep-equal copy of `abstract_program` in which every
            hole a candidate origin reproduced is replaced by a symbolic origin
            descriptor `{"origin": "<name>"}` (P7 — a json-stable dict naming
            *how to fill the hole from G0*, not a literal value). Holes no
            candidate reproduced keep their `?vN` marker.
        unbound: a list of `{"step", "arg", "var"}` dicts, one per hole left
            unbound — the honest surface of which origins are still missing.

    A program with empty `unbound` is **fully grounded**: every hole carries a
    G0 reading, so it can be instantiated on a test input without its absent G1
    (the precondition for persisting it as a self-applying `covers>1` rule). The
    selection is grounded in example-reproduction (P3/P4), never invented; an arg
    whose origin is unknown is reported, not guessed."""
    if not isinstance(pair_programs, list) or len(pair_programs) < 1:
        raise ValueError("bind_program_variables needs >= 1 pair program")
    if len(pair_inputs) != len(pair_programs):
        raise ValueError("pair_inputs and pair_programs must align 1:1")

    bound = []
    unbound = []
    for s, step in enumerate(abstract_program):
        new_args = {}
        for key, value in (step.get("args") or {}).items():
            if not _is_var(value):
                new_args[key] = value
                continue
            literals = [pair_programs[i][s]["args"].get(key) for i in range(len(pair_programs))]
            origin = _bind_one(key, literals, pair_inputs)
            if origin is None:
                new_args[key] = value
                unbound.append({"step": s, "arg": key, "var": value})
            else:
                new_args[key] = {"origin": origin}
        bound.append({"dsl": step.get("dsl"), "args": new_args})
    return bound, unbound


def _resolve_origin(descriptor, grid):
    """Read the value a `{"origin": <name>}` descriptor names off a single grid
    (a test G0). Returns the literal value, or None when the origin cannot be read
    from this grid (e.g. `source_cells` on a grid with no unique object) — an
    honest decline, never a guessed value. The origin set is exactly the one
    `bind_program_variables` can emit; an unknown name returns None rather than
    inventing a reading (a new origin is grown in :data:`_ARG_ORIGINS` first, not
    here)."""
    name = descriptor.get("origin")
    if name == "source_cells":
        cells = _origin_source_cells(grid)
        return None if cells is None else [list(cell) for cell in cells]
    if name == "source_color":
        return _origin_source_color(grid)
    return None


def instantiate_program(bound_program, test_input):
    """Instantiate a fully-bound program on a test input, making good on
    :func:`program_is_fully_bound`'s promise that such a program is "instantiable
    on a test G0".

    `bound_program` is the output of :func:`bind_program_variables`: a flat list
    of `{"dsl", "args"}` steps whose arg values are either invariant literals or
    `{"origin": <name>}` G0-reading descriptors. This walks the program and
    replaces every descriptor with the value its origin reads off `test_input`
    (the test pair's G0 — never an output, P5), returning a *literal*
    `coloring`/`make_grid` program ready to run through
    `agent.program_synthesis.run_program`. The synthesize→AU→bind→**instantiate**
    chain is then end-to-end executable on a test input that has no G1.

    Returns the instantiated program, or **None** if any origin cannot be read
    from `test_input` (the program does not apply to this test — an honest decline,
    consistent with the binder's no-guess discipline). Raises `ValueError` if the
    program still carries a `?vN` hole (it was never fully bound, so there is no
    test-time value to supply — instantiating it would be inventing one)."""
    instantiated = []
    for step in bound_program:
        new_args = {}
        for key, value in (step.get("args") or {}).items():
            if _is_var(value):
                raise ValueError(
                    f"cannot instantiate unbound hole {value!r}; bind it first")
            if isinstance(value, dict) and "origin" in value:
                resolved = _resolve_origin(value, test_input)
                if resolved is None:
                    return None
                new_args[key] = resolved
            else:
                new_args[key] = value
        instantiated.append({"dsl": step.get("dsl"), "args": new_args})
    return instantiated


def program_is_fully_bound(bound_program) -> bool:
    """True iff `bound_program` (from :func:`bind_program_variables`) carries no
    remaining `?vN` hole — every position is either an invariant literal or a
    `{"origin": ...}` G0 expression, so the program is instantiable on a test
    input. The negation of "still has unbound holes" — the gate a caller checks
    before treating a lifted program as self-applying."""
    def _has_var(value) -> bool:
        if _is_var(value):
            return True
        if isinstance(value, dict):
            return any(_has_var(v) for v in value.values())
        if isinstance(value, (list, tuple)):
            return any(_has_var(v) for v in value)
        return False

    return not any(_has_var(step.get("args") or {}) for step in bound_program)
