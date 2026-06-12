"""
Tests for `agent/program_binding.py` — binding an anti-unified program's `?vN`
holes to G0-origin expressions (BACKLOG_LOOP.md §2.5-2b).

The diagnosed gap (iter-28): the synthesize→AU pipeline (iters 26/27) produces a
*structurally* lifted program whose differing positions are `?vN` holes, but
those holes carry no rule for how to fill them from a test input — they are dead
unless bound to a G0-origin expression. This module binds them by the same
example-reproduction discipline `variable_resolution.resolve_variable` uses.

The ground is **real** ARC pairs, end-to-end through the actual producer
(`synthesize_pair_program`) and consumer (`anti_unify_pair_programs`):

  * easy000c — the source pixel and its colour both bind to a G0 origin, so the
               lifted program is *fully grounded* (instantiable on a test G0).
  * easy000e — the source cell + colour bind, but the *target* position (source
               moved by Δ) is a relation the seed origin set does not express, so
               it is honestly reported as unbound (not guessed).
  * precision/contract — invariant literals are never touched; a fully-literal
               program needs no binding; misaligned inputs raise.
"""

import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agent.program_synthesis import synthesize_pair_program  # noqa: E402
from program.anti_unification import anti_unify_pair_programs  # noqa: E402
from agent.program_binding import (  # noqa: E402
    bind_program_variables, program_is_fully_bound, instantiate_program,
)
from agent.program_synthesis import run_program  # noqa: E402


def _load_task(task_path, data_root="data"):
    from managers.arc_manager import ARCManager
    with tempfile.TemporaryDirectory() as tmp:
        return ARCManager(data_root=data_root,
                          semantic_memory_root=tmp).load_task(task_path)


def _pairs(task):
    return [(p.input_grid.raw, p.output_grid.raw) for p in task.example_pairs]


def _lift(task):
    """The real producer→consumer chain: synthesize each pair, anti-unify."""
    pairs = _pairs(task)
    progs = [synthesize_pair_program(i, o) for i, o in pairs]
    abstract = anti_unify_pair_programs(progs)
    inputs = [i for i, _ in pairs]
    return abstract, progs, inputs


# ── easy000c: every hole binds to a G0 origin (fully grounded) ─────────
def test_easy000c_binds_all_holes():
    abstract, progs, inputs = _lift(_load_task("ARC_easy_a/easy000c"))
    bound, unbound = bind_program_variables(abstract, progs, inputs)
    # The lift had holes (source cell + colour); after binding none remain.
    assert unbound == []
    assert program_is_fully_bound(bound)
    # Specifically: step0 erases the source object's cells; step1 paints the
    # invariant corner [[5,5]] with the source object's colour.
    assert bound[0]["args"]["selection"] == {"origin": "source_cells"}
    assert bound[0]["args"]["color"] == 0           # invariant background, untouched
    assert bound[1]["args"]["selection"] == [[5, 5]]  # invariant corner, untouched
    assert bound[1]["args"]["color"] == {"origin": "source_color"}


def test_easy000c_invariants_pass_through_unchanged():
    # The COMM positions the lift kept literal must survive binding verbatim —
    # binding only ever replaces a ?vN, never an already-grounded literal.
    abstract, progs, inputs = _lift(_load_task("ARC_easy_a/easy000c"))
    bound, _ = bind_program_variables(abstract, progs, inputs)
    for step in bound:
        for value in step["args"].values():
            assert value != "?v1" and value != "?v2"


# ── easy000e: target position is an unexpressed relation (honest decline) ─
def test_easy000e_reports_unbound_target():
    abstract, progs, inputs = _lift(_load_task("ARC_easy_a/easy000e"))
    bound, unbound = bind_program_variables(abstract, progs, inputs)
    # The source cell and colour bind; the moved-to target position does not —
    # it is source+Δ, a relation the seed origin set does not yet express.
    assert not program_is_fully_bound(bound)
    assert len(unbound) == 1
    u = unbound[0]
    assert u["arg"] == "selection" and u["step"] == 1
    # the bound holes are the source-derived ones
    assert bound[0]["args"]["selection"] == {"origin": "source_cells"}
    assert bound[1]["args"]["color"] == {"origin": "source_color"}


# ── instantiation: the bound program is executable on a test G0 ────────
# These exercise the full synthesize→AU→bind→instantiate→run chain on real
# held-out test pairs (the pair has no G1 — instantiation must read every hole
# off the test G0 alone, P5), making good on program_is_fully_bound's promise.

def _solves_via_chain(task_path):
    """True iff the fully-bound lifted program, instantiated on each held-out
    test input, reproduces that test's output. The whole chain end-to-end."""
    task = _load_task(task_path)
    abstract, progs, inputs = _lift(task)
    bound, unbound = bind_program_variables(abstract, progs, inputs)
    if unbound or not program_is_fully_bound(bound):
        return None  # not a fully-bound task — out of scope for this assertion
    for tp in task.test_pairs:
        inst = instantiate_program(bound, tp.input_grid.raw)
        if inst is None or run_program(inst, tp.input_grid.raw) != tp.output_grid.raw:
            return False
    return True


def test_fully_binding_easy_a_tasks_solve_end_to_end():
    # Every easy_a task whose lift fully binds with the *existing* origin set is
    # solved the general way: synthesize per pair → anti-unify → bind holes to G0
    # origins → instantiate on the test G0 → run. Value-agnostic across the set
    # (different cells/colours, one mechanism — observation criterion 2).
    for t in ["a", "b", "c", "d", "h", "i"]:
        assert _solves_via_chain(f"ARC_easy_a/easy000{t}") is True, t


def test_instantiate_declines_when_origin_unreadable():
    # A program bound to source_cells, instantiated on a test G0 with no unique
    # object, declines (None) rather than guessing or crashing.
    bound = [{"dsl": "coloring",
              "args": {"selection": {"origin": "source_cells"}, "color": 0}}]
    # two foreground objects → unique(objects_of(.)) is None → origin unreadable
    test_g0 = [[1, 0, 2], [0, 0, 0], [0, 0, 0]]
    assert instantiate_program(bound, test_g0) is None


def test_instantiate_resolves_descriptors_to_literals():
    # Origins resolve to concrete G0 readings; invariant literals pass through.
    bound = [
        {"dsl": "coloring", "args": {"selection": {"origin": "source_cells"}, "color": 0}},
        {"dsl": "coloring", "args": {"selection": [[5, 5]], "color": {"origin": "source_color"}}},
    ]
    test_g0 = [[0, 0, 0], [0, 7, 0], [0, 0, 0]]  # single object: cell (1,1), colour 7
    inst = instantiate_program(bound, test_g0)
    assert inst[0]["args"]["selection"] == [[1, 1]]
    assert inst[0]["args"]["color"] == 0           # invariant literal, untouched
    assert inst[1]["args"]["selection"] == [[5, 5]]  # invariant literal, untouched
    assert inst[1]["args"]["color"] == 7


def test_instantiate_rejects_unbound_program():
    # A program still carrying a ?vN hole has no test-time value to supply;
    # instantiating it would be inventing one — rejected, not silently filled.
    program = [{"dsl": "coloring", "args": {"selection": "?v1", "color": 1}}]
    try:
        instantiate_program(program, [[1]])
    except ValueError:
        pass
    else:
        raise AssertionError("expected ValueError on an unbound program")


def test_instantiate_passes_through_fully_literal_program():
    program = [{"dsl": "coloring", "args": {"selection": [[0, 0]], "color": 3}}]
    assert instantiate_program(program, [[9]]) == program


# ── precision / contract ──────────────────────────────────────────────
def test_fully_literal_program_needs_no_binding():
    # An identity-style lifted program with no holes is returned unchanged and
    # reported fully bound.
    program = [{"dsl": "coloring", "args": {"selection": [[0, 0]], "color": 1}}]
    bound, unbound = bind_program_variables(program, [program, program],
                                            [[[1]], [[1]]])
    assert unbound == []
    assert program_is_fully_bound(bound)
    assert bound == program


def test_unbindable_hole_kept_as_marker():
    # A hole whose per-pair literals match no G0 origin keeps its ?vN marker and
    # is reported unbound (no invention, no guess).
    abstract = [{"dsl": "coloring", "args": {"selection": "?v1", "color": 5}}]
    # two single-pixel inputs whose objects sit at (0,0)/(0,0) but whose literal
    # selections are arbitrary cells unrelated to any object origin
    prog_a = [{"dsl": "coloring", "args": {"selection": [[9, 9]], "color": 5}}]
    prog_b = [{"dsl": "coloring", "args": {"selection": [[8, 8]], "color": 5}}]
    inputs = [[[1, 0], [0, 0]], [[1, 0], [0, 0]]]
    bound, unbound = bind_program_variables(abstract, [prog_a, prog_b], inputs)
    assert bound[0]["args"]["selection"] == "?v1"
    assert len(unbound) == 1 and unbound[0]["var"] == "?v1"
    assert not program_is_fully_bound(bound)


def test_misaligned_inputs_raise():
    program = [{"dsl": "coloring", "args": {"selection": "?v1", "color": 1}}]
    try:
        bind_program_variables(program, [program, program], [[[1]]])
    except ValueError:
        pass
    else:
        raise AssertionError("expected ValueError on misaligned pair_inputs")
