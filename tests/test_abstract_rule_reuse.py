"""
Tests for Fast-path reuse of *abstract* (covers>1) rules (R5 / BACKLOG_LOOP
§2.5-2b).

A lifted anti-unification rule is an *incomplete* program: its action carries a
``?vN`` variable whose filler must be chosen from the *new* task's own comparison
evidence before it can run. The legacy ``_apply_rule`` dispatcher only knew the
three concrete legacy types, so the stored abstractions never fired and every
task re-derived through the Slow path (`Reused: 0`). ``ActiveSoarAgent`` now
*activates* a stored abstraction via its own ``condition`` matcher and resolves +
renders it against the task (the §2.5-2b "fill the hole from COMM, then verify"
loop). These tests pin:

- reuse fires on a size-grid task and produces the correct grid via the stored
  ``size_to_grid`` abstraction (method == "stored_rule");
- it is honest — an abstraction that does *not* reproduce every example is
  declined, so the Slow path still runs (no correctness regression);
- it stays disjoint from the move / constant-output families (the size_to_grid
  matcher abstains on easy_a, so reuse falls through there).
"""

import tempfile

from types import SimpleNamespace

from managers.arc_manager import ARCManager
from agent.active_agent import ActiveSoarAgent
from agent.active_operators import PredictOperator, SIZE_GRID_DSL


def _load(task_id):
    with tempfile.TemporaryDirectory() as tmp:
        return ARCManager(semantic_memory_root=tmp).load_task(task_id)


def _expected_outputs(task):
    return [tp.output_grid.raw for tp in task.test_pairs]


# ── the stored size_to_grid abstraction reuses on a size-grid task ────────
def test_reuse_fires_on_size_grid_task():
    """A size-grid madeup task solves via the stored abstraction (the Fast path),
    not by re-deriving a fresh rule."""
    task = _load("ARC_madeup/madeup_size_to_square")
    agent = ActiveSoarAgent()
    predicted = agent.solve(task)

    assert predicted == _expected_outputs(task)
    assert agent.last_solve_info["method"] == "stored_rule"
    # the abstraction that fired is the lifted object-size-to-square rule
    assert agent.last_solve_info["rule_type"] == "object_property_to_solid_square"


def test_reuse_fires_on_non_square_rect_task():
    """The same abstraction resolves its variable to the *rectangular* reading on
    a non-square task — one stored rule, many tasks (covers>1 reuse)."""
    task = _load("ARC_madeup/madeup_bbox_extent_to_rect")
    agent = ActiveSoarAgent()
    predicted = agent.solve(task)

    assert predicted == _expected_outputs(task)
    assert agent.last_solve_info["method"] == "stored_rule"


# ── reuse is scoped: it abstains on the move / constant families ──────────
def test_size_grid_reuse_abstains_on_move_task():
    """easy000c is an object-move task; the *size_to_grid* abstraction abstains on
    it (its object_size_grid matcher does not fire), so the families stay disjoint
    — the move is handled by the place_object abstraction, never size_to_grid."""
    task = _load("ARC_easy_a/easy000c")
    agent = ActiveSoarAgent()

    # The size_to_grid rule must decline this move task.
    from agent.memory import load_all_rules
    for entry in load_all_rules(agent.procedural_memory_root):
        if entry.get("action", {}).get("dsl") == SIZE_GRID_DSL:
            assert agent._reuse_abstract_rule(entry, task) is None


# ── honesty: the safety gate declines an abstraction that mis-grounds ─────
def test_reuse_declined_when_examples_not_reproduced():
    """``_reproduces_examples`` is the safety gate: when the render_fn cannot
    reproduce an example output, reuse is declined (so the Slow path runs and a
    reuse never converts a solvable task into a wrong answer)."""
    task = _load("ARC_madeup/madeup_size_to_square")

    # A render_fn that returns a deliberately wrong grid must fail the gate.
    bad_render = lambda t: {0: [[0]]}
    assert ActiveSoarAgent._reproduces_examples(bad_render, task) is False

    # The genuine size-grid render_fn reproduces every example.
    good_render = PredictOperator()._place_size_grid_grids
    assert ActiveSoarAgent._reproduces_examples(good_render, task) is True


def test_reuse_table_is_registry_driven_and_covers_every_lifted_family():
    """Abstract reuse is built from the data-driven ``_ABSTRACT_REUSE_REGISTRY``
    (iter 46): *every* born-general family that owns a lifted (covers>1) rule
    participates, not a hand-spelled three. The table's dsl keys equal the
    registry's, each maps to its own condition.type, and — the property that makes
    it real reuse rather than a dead table — every stored rule's ``action.dsl`` is
    present in the table (so no lifted family silently re-derives through the Slow
    path). ``copy_common_output`` is the one documented exception (no self-resolving
    renderer yet)."""
    from agent.active_agent import (
        PLACE_OBJECT_ABSTRACT_DSL,
        _ABSTRACT_REUSE_REGISTRY,
    )
    from agent.active_operators import (
        SELF_FRACTAL_DSL,
        CANVAS_FILL_DSL,
        RECOLOR_DSL,
        OBJECT_SELECT_RECOLOR_DSL,
        GEOMETRIC_TRANSFORM_DSL,
        SCALE_TRANSFORM_DSL,
        SYMMETRY_REPAIR_DSL,
        OBJECT_EXTRACT_DSL,
    )
    from agent.memory import load_all_rules

    agent = ActiveSoarAgent()
    # the table is exactly the registry's families, each keyed by its cond.type
    expected = {
        SIZE_GRID_DSL, PLACE_OBJECT_ABSTRACT_DSL, SELF_FRACTAL_DSL,
        CANVAS_FILL_DSL, RECOLOR_DSL, OBJECT_SELECT_RECOLOR_DSL,
        GEOMETRIC_TRANSFORM_DSL, SCALE_TRANSFORM_DSL, SYMMETRY_REPAIR_DSL,
        OBJECT_EXTRACT_DSL,
    }
    assert set(agent._abstract_reuse) == expected
    assert {dsl for dsl, *_ in _ABSTRACT_REUSE_REGISTRY} == expected
    for dsl, cond_type, _analyze, _render in _ABSTRACT_REUSE_REGISTRY:
        assert agent._abstract_reuse[dsl][0] == cond_type

    # every lifted family on disk is wired (except the documented copy_common_output)
    stored_dsls = {
        (e.get("action") or {}).get("dsl")
        for e in load_all_rules(agent.procedural_memory_root)
    }
    unwired = stored_dsls - expected - {"copy_common_output", None}
    assert unwired == set(), f"lifted families with no Fast-path reuse: {unwired}"


# ── the stored self_fractal abstraction reuses on a size-expanding task ───
def test_reuse_fires_on_self_fractal_task():
    """A self-fractal madeup task solves via the stored self_fractal abstraction
    (the Fast path), not by re-deriving through the Slow pipeline. This proves the
    reuse mechanism generalises to a *size-expanding* abstraction — structurally
    different from both the sizing-square and the same-size move families (R5
    done-when: a stored hit on a structurally different task)."""
    task = _load("ARC_madeup/madeup_self_fractal")
    agent = ActiveSoarAgent()
    predicted = agent.solve(task)

    assert predicted == _expected_outputs(task)
    assert agent.last_solve_info["method"] == "stored_rule"
    assert agent.last_solve_info["rule_type"] == "self_fractal"


def test_self_fractal_reuse_abstains_on_non_fractal_task():
    """A size-grid madeup task is not a fractal (no h²×w² expansion); the
    self_fractal matcher abstains, so the self_fractal abstraction declines and the
    families stay disjoint (size_to_grid reuse handles it instead)."""
    from agent.memory import load_all_rules
    from agent.active_operators import SELF_FRACTAL_DSL
    task = _load("ARC_madeup/madeup_size_to_square")
    agent = ActiveSoarAgent()
    for entry in load_all_rules(agent.procedural_memory_root):
        if entry.get("action", {}).get("dsl") == SELF_FRACTAL_DSL:
            assert agent._reuse_abstract_rule(entry, task) is None


# ── the stored place_object abstraction reuses on a move task ─────────────
def test_reuse_fires_on_constant_target_move_task():
    """easy000c is a constant-target object move. The stored place_object
    abstraction now *activates* (object_move matcher fires), resolves its ?v0
    reading-hole to constant_target from COMM, and renders — the Fast path,
    not a re-derivation. This proves cross-family reuse (a different family from
    size_to_grid, with a richer reading-resolution step)."""
    task = _load("ARC_easy_a/easy000c")
    agent = ActiveSoarAgent()
    predicted = agent.solve(task)

    assert predicted == _expected_outputs(task)
    assert agent.last_solve_info["method"] == "stored_rule"
    assert agent.last_solve_info["rule_type"] == "place_object"


def test_reuse_resolves_offset_reading_on_offset_move_task():
    """easy000e is a constant-*offset* move. The same stored place_object rule
    resolves its ?v0 hole to the *offset* reading (a different filler than
    easy000c) and renders correctly — one rule, many tasks, the variable filled
    per-task from COMM (§2.5-2b)."""
    task = _load("ARC_easy_a/easy000e")
    agent = ActiveSoarAgent()
    predicted = agent.solve(task)

    assert predicted == _expected_outputs(task)
    assert agent.last_solve_info["method"] == "stored_rule"


def test_place_object_reuse_abstains_on_size_grid_task():
    """A size-grid madeup task is not a move; the object_move matcher abstains, so
    the place_object abstraction declines (size_to_grid reuse handles it instead —
    the two families stay disjoint)."""
    from agent.memory import load_all_rules
    task = _load("ARC_madeup/madeup_size_to_square")
    agent = ActiveSoarAgent()
    for entry in load_all_rules(agent.procedural_memory_root):
        if entry.get("action", {}).get("dsl") == "place_object":
            assert agent._reuse_abstract_rule(entry, task) is None
