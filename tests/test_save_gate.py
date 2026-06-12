"""
Tests for the train-reproduction save gate (BACKLOG_LOOP §2.5-3/4, F2 spirit).

A pipeline run on a *hard, unsolved* training task still emits a best-effort
non-identity guess (``recolor_sequential`` / ``color_mapping`` / …). Before this
gate, ``ActiveSoarAgent.solve`` persisted that guess as a rule whenever it was
merely non-identity — so a 0%-correct probe spawned condition-less, ``covers=1``
rules that reproduce neither train nor test. Those are not legitimate
anti-unification *material* (an overfit program is material only when it actually
reproduces its own train pairs, §2.5-3); they only accrete and can never be
lifted (the 168-rule failure mode, §2.5-4).

The gate: a discovered rule is saved only when it reproduces *every* train
example it was derived from. The check uses train reproduction — available at
solve time — never test correctness, so it is honest, not score-gaming.

These tests pin:
- a discovered rule that does NOT reproduce its train pairs is rejected by the
  gate and therefore not persisted (the empty-procedural_memory probe leaves no
  junk rule);
- a discovered rule that DOES reproduce its train pairs still passes the gate.
"""

import os
import tempfile

from types import SimpleNamespace

from managers.arc_manager import ARCManager
from agent.active_agent import ActiveSoarAgent
from agent.active_operators import RECOLOR_DSL


def _color_remap_rule(color_map):
    """A canonical ``{condition, action}`` color_remap rule — the live shape the
    save gate now receives (the legacy ``{type: color_mapping}`` envelope and its
    ``_apply_color_mapping`` applier were removed once this canonical family
    superseded them, INVARIANTS P6 / §5.1). The gate recomputes the map from the
    examples, so the carried args are only self-description."""
    return {
        "condition": {"type": "color_remap", "params": {}, "min_evidence": 2},
        "action": {"dsl": RECOLOR_DSL,
                   "args": {"color_map": {str(k): v for k, v in color_map.items()}}},
    }


def _load(task_id):
    with tempfile.TemporaryDirectory() as tmp:
        return ARCManager(semantic_memory_root=tmp).load_task(task_id)


def _grid(rows):
    return SimpleNamespace(raw=rows)


def _pair(inp, out):
    return SimpleNamespace(input_grid=_grid(inp), output_grid=_grid(out))


def _fake_task(pairs):
    return SimpleNamespace(example_pairs=pairs, test_pairs=pairs)


# ── the gate rejects a rule that does not reproduce its train pairs ────────
def test_gate_rejects_non_reproducing_rule():
    agent = ActiveSoarAgent()
    # a canonical color_remap rule against a *resize* pair — the recolor family
    # abstains on a size change, so it reproduces nothing and the gate rejects it.
    rule = _color_remap_rule({0: 1})
    task = _fake_task([_pair([[0, 0]], [[1]])])
    assert agent._rule_matches_examples(rule, task) is False


# ── the gate accepts a rule that reproduces its train pairs ────────────────
def test_gate_accepts_reproducing_rule():
    agent = ActiveSoarAgent()
    # a canonical color_remap rule against a clean 0->1 recolor: the gate recomputes
    # the map from the example and renders it back, reproducing the train output.
    rule = _color_remap_rule({0: 1})
    task = _fake_task([_pair([[0, 0]], [[1, 1]])])
    assert agent._rule_matches_examples(rule, task) is True


# ── solving a hard, unsolved training task persists no junk rule ───────────
def test_unsolved_training_task_saves_no_rule():
    # e5790162 previously spawned a non-reproducing recolor_sequential rule.
    task = _load("e5790162")
    with tempfile.TemporaryDirectory() as tmp:
        agent = ActiveSoarAgent(procedural_memory_root=tmp)
        agent.solve(task)
        saved = [f for f in os.listdir(tmp)
                 if f.startswith("rule_") and f.endswith(".json")]
        assert saved == [], f"gate let a non-reproducing rule through: {saved}"
