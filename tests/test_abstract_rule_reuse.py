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
def test_reuse_abstains_on_move_task():
    """easy000c is an object-move task; the size_to_grid matcher abstains, so the
    abstraction does not reuse (the Slow path solves it instead)."""
    task = _load("ARC_easy_a/easy000c")
    agent = ActiveSoarAgent()

    # _reuse_abstract_rule must decline every stored rule for this task.
    from agent.memory import load_all_rules
    for entry in load_all_rules(agent.procedural_memory_root):
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


def test_reuse_table_targets_size_grid_only_for_now():
    """This slice scopes abstract reuse to the size_to_grid family (the simplest
    abstraction). The activation table records exactly that family."""
    agent = ActiveSoarAgent()
    assert set(agent._abstract_reuse) == {SIZE_GRID_DSL}
    cond_type, _patterns_fn, _render_fn = agent._abstract_reuse[SIZE_GRID_DSL]
    assert cond_type == "object_size_grid"
