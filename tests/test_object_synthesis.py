"""
Tests for the *object-level* per-pair synthesizer
(`agent/object_synthesis.py`, BACKLOG_LOOP.md R1 / §2.5-2b — the training
frontier iter-29 named).

The pixel synthesizer (`agent/program_synthesis.py`) is round-trip-correct but
destroys object structure: two pairs that recolour "the largest object" have
*different* literal cell-lists, so the lift collapses the selection to an
unbindable `?vN`. This module synthesizes the selection **object-relationally**
(`argmax(objects_of(in), size_of)`) so the selector is the cross-pair COMM and
survives the lift as a literal — a directly instantiable `covers>1` program.

The ground is the strongest available: synthesize from the *train* pairs and run
the result on the **held-out test input**, asserting it equals the held-out test
output — and do it for both directions / colours (largest→4, smallest→7) with the
*same* mechanism (criterion 2: module uniformity, value-agnostic). Plus the
precise frontier proof: through the *existing* `anti_unify_pair_programs`
consumer, the object-level programs lift with the selector kept literal, whereas
the pixel programs for the same pairs lift the selection to a `?vN`.
"""

import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agent.object_synthesis import (  # noqa: E402
    synthesize_object_recolor, run_object_program, resolve_selection,
    _selection_candidates,
)
from agent.program_synthesis import synthesize_pair_program  # noqa: E402
from program.anti_unification import (  # noqa: E402
    anti_unify_pair_programs, program_is_more_general,
)


# ── helpers ───────────────────────────────────────────────────────────
def _load_task(task_path, data_root="data"):
    from managers.arc_manager import ARCManager
    with tempfile.TemporaryDirectory() as tmp:
        return ARCManager(data_root=data_root,
                          semantic_memory_root=tmp).load_task(task_path)


def _train_pairs(task):
    return [(p.input_grid.raw, p.output_grid.raw) for p in task.example_pairs]


def _test_pair(task):
    tp = task.test_pairs[0]
    return tp.input_grid.raw, tp.output_grid.raw


# ── the ground: solve the held-out test, both directions, same mechanism ──
def test_largest_recolor_solves_held_out_test():
    # argmax(size_of) is the cross-pair COMM; new colour 4 is constant. The
    # synthesized object program, run on the *test* input, must equal the test
    # output — the whole producer→executor path on real held-out data.
    task = _load_task("ARC_madeup/largest_recolor")
    program = synthesize_object_recolor(_train_pairs(task))
    assert program is not None
    assert program[0]["args"]["selection"] == {
        "select": "argmax", "key": "size_of", "from": "objects_of(in)"}
    assert program[0]["args"]["color"] == 4
    test_in, test_out = _test_pair(task)
    assert run_object_program(program, test_in) == test_out


def test_smallest_recolor_solves_held_out_test_same_mechanism():
    # The *same* synthesizer, no special case: the only cross-pair-consistent
    # selector is now argmin(size_of) and the colour 7 — derived from the pairs,
    # not hard-coded. Value-agnostic across direction and colour (criterion 2).
    task = _load_task("ARC_madeup/smallest_recolor")
    program = synthesize_object_recolor(_train_pairs(task))
    assert program is not None
    assert program[0]["args"]["selection"] == {
        "select": "argmin", "key": "size_of", "from": "objects_of(in)"}
    assert program[0]["args"]["color"] == 7
    test_in, test_out = _test_pair(task)
    assert run_object_program(program, test_in) == test_out


# ── the frontier proof: object structure survives the lift ────────────
def test_object_level_lift_keeps_selector_literal():
    # The two largest_recolor train-pair programs are *identical* (selector and
    # colour are the cross-pair COMM), so anti_unify_pair_programs keeps the
    # selector a literal and introduces NO variable — a fully-bound covers>1
    # program, directly runnable. This is the structure pixel-level synthesis
    # cannot preserve (next test).
    task = _load_task("ARC_madeup/largest_recolor")
    pairs = _train_pairs(task)
    progs = [synthesize_object_recolor([p]) for p in pairs]
    assert all(p is not None for p in progs)
    lifted = anti_unify_pair_programs([p for p in progs])
    assert not program_is_more_general(lifted)  # no ?vN hole
    assert lifted[0]["args"]["selection"] == {
        "select": "argmax", "key": "size_of", "from": "objects_of(in)"}


def test_pixel_level_lift_loses_selection_to_a_hole():
    # The contrast that names the gap: the *pixel* synthesizer's programs for the
    # same pairs differ in their literal cell-lists, so the lift collapses the
    # selection to a ?vN variable — exactly the structure loss the object-level
    # synthesizer avoids.
    task = _load_task("ARC_madeup/largest_recolor")
    pairs = _train_pairs(task)
    progs = [synthesize_pair_program(i, o) for i, o in pairs]
    lifted = anti_unify_pair_programs(progs)
    assert program_is_more_general(lifted)  # selection lifted to ?vN


# ── selection vocabulary ──────────────────────────────────────────────
def test_resolve_selection_round_trips_candidates():
    # Every selector _selection_candidates proposes for a changed object resolves
    # back to exactly that object's cells (producer/executor symmetry).
    task = _load_task("ARC_madeup/largest_recolor")
    in_grid, out_grid = _train_pairs(task)[0]
    from agent.object_synthesis import _recolor_change
    changed, _ = _recolor_change(in_grid, out_grid)
    cands = _selection_candidates(in_grid, changed)
    assert cands  # at least argmax(size_of)
    target = sorted([r, c] for (r, c) in changed)
    for sel in cands:
        assert resolve_selection(sel, in_grid) == target


def test_single_object_per_pair_prefers_unique():
    # When each pair has exactly one object, `unique` is consistent and wins by
    # preference order (the simplest true description), even though argmax/argmin
    # would also fit a lone object.
    pairs = [
        ([[0, 0, 0], [0, 5, 0], [0, 0, 0]], [[0, 0, 0], [0, 8, 0], [0, 0, 0]]),
        ([[5, 0, 0], [0, 0, 0], [0, 0, 0]], [[8, 0, 0], [0, 0, 0], [0, 0, 0]]),
    ]
    program = synthesize_object_recolor(pairs)
    assert program is not None
    assert program[0]["args"]["selection"]["select"] == "unique"
    assert program[0]["args"]["color"] == 8


# ── honest declines (no guessing) ─────────────────────────────────────
def test_declines_when_no_selector_consistent_across_pairs():
    # Pair 1 recolours the *largest*, pair 2 the *smallest* — no single seed
    # selector reproduces both, so the synthesizer declines rather than guess.
    pairs = [
        # pair 1: largest (2x2) recoloured
        ([[3, 3, 0], [3, 3, 0], [0, 0, 3]], [[4, 4, 0], [4, 4, 0], [0, 0, 3]]),
        # pair 2: smallest (single) recoloured
        ([[3, 3, 0], [3, 3, 0], [0, 0, 3]], [[3, 3, 0], [3, 3, 0], [0, 0, 4]]),
    ]
    assert synthesize_object_recolor(pairs) is None


def test_declines_when_new_color_varies_per_pair():
    # Same selector but the new colour differs per pair → an origin-bound hole,
    # out of this slice's scope. Decline (surfaced, not guessed).
    pairs = [
        ([[0, 0, 0], [0, 5, 0], [0, 0, 0]], [[0, 0, 0], [0, 4, 0], [0, 0, 0]]),
        ([[0, 0, 0], [0, 5, 0], [0, 0, 0]], [[0, 0, 0], [0, 7, 0], [0, 0, 0]]),
    ]
    assert synthesize_object_recolor(pairs) is None


def test_declines_when_change_is_not_whole_object_recolor():
    # Only part of an object changes — not a whole-object recolour the seed
    # selectors can name. Decline.
    pairs = [
        ([[3, 3], [3, 3]], [[4, 3], [3, 3]]),
        ([[3, 3], [3, 3]], [[4, 3], [3, 3]]),
    ]
    assert synthesize_object_recolor(pairs) is None


def test_run_object_program_declines_on_unresolvable_grid():
    # A program keyed on `unique`, run on a grid with several objects, resolves
    # to None (the selector abstains) → the executor returns None, not a wrong
    # paint.
    program = [{"dsl": "coloring",
                "args": {"selection": {"select": "unique", "from": "objects_of(in)"},
                         "color": 8}}]
    multi = [[3, 0, 3], [0, 0, 0], [3, 0, 0]]
    assert run_object_program(program, multi) is None
