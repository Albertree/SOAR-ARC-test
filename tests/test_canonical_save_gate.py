"""
Tests for the *canonical* learn-save gate (BACKLOG_LOOP R3/R5; iter20 Next-gap;
memory ``canonical_rules_never_persist``).

The learn-save gate in ``ActiveSoarAgent.solve`` validates a discovered rule with
``_rule_matches_examples``. Before this change that helper called only the legacy
``PredictOperator._apply_rule`` dispatcher, which knows just the three *legacy*
typed rules (``recolor_sequential`` / ``color_mapping`` / ``identity``) and
returns ``None`` for every canonical ``{condition, action}`` rule. So a canonical
family rule — even one that perfectly reproduces its own train pairs — silently
failed the gate and was *never saved*. A rule that never persists can never be
lifted by anti-unification (R3) nor reused by the Fast path (R5): the canonical
families were an architectural dead-end at the one site that feeds memory.

The fix routes canonical rules through the predict pipeline (the same per-family
renderers the predictor uses) so a canonical rule that reproduces its train pairs
passes the gate and persists — then absorbs into / lifts with its siblings the
intended way (no liftless ``covers=1`` accretion: a re-discovered concrete reading
is absorbed by the abstraction that already ranges over it).

These tests pin:
- the legacy ``_apply_rule`` still returns ``None`` for a canonical rule (the
  exact reason the old gate rejected it);
- the canonical gate ACCEPTS a canonical recolor rule that reproduces its train
  pairs (the unblock) and REJECTS one whose family renderer abstains;
- once it passes, ``save_rule_to_ltm`` persists a schema-valid canonical rule
  (condition + action present) into an empty store.
"""

import os
import tempfile

from types import SimpleNamespace

from agent.active_agent import ActiveSoarAgent
from agent.active_operators import RECOLOR_DSL
from agent.memory import save_rule_to_ltm, validate_rule, _is_canonical


def _grid(rows):
    return SimpleNamespace(raw=rows)


def _pair(inp, out):
    return SimpleNamespace(input_grid=_grid(inp), output_grid=_grid(out))


def _fake_task(pairs):
    return SimpleNamespace(task_hex="synthetic", example_pairs=pairs, test_pairs=pairs)


def _canonical_recolor_rule():
    """A canonical {condition, action} recolor rule (the shape GeneralizeOperator
    emits). The live map is recomputed from the examples at predict time; the
    carried copy is for self-description / AU lifting."""
    return {
        "condition": {"type": "color_remap", "params": {"min_evidence": 2},
                      "min_evidence": 2},
        "action": {"dsl": RECOLOR_DSL, "args": {"color_map": {"1": 2, "3": 4}}},
        "concept": "recolor_by_color_map",
        "category": "color_remap",
        "confidence": 1.0,
    }


# a consistent same-size 1:1 recolor (1->2, 3->4, 0 unchanged) across two pairs
_RECOLOR_PAIRS = [
    _pair([[1, 3], [0, 1]], [[2, 4], [0, 2]]),
    _pair([[3, 0], [1, 3]], [[4, 0], [2, 4]]),
]


# ── the legacy applier cannot express a canonical rule (the old gate's blind spot)
def test_legacy_apply_rule_returns_none_for_canonical_rule():
    agent = ActiveSoarAgent()
    rule = _canonical_recolor_rule()
    # This is exactly why the pre-fix gate rejected every canonical rule.
    assert agent._predictor._apply_rule(rule, _grid([[1, 3], [0, 1]])) is None


# ── the canonical gate ACCEPTS a canonical rule that reproduces its train pairs ─
def test_canonical_gate_accepts_reproducing_recolor_rule():
    agent = ActiveSoarAgent()
    rule = _canonical_recolor_rule()
    task = _fake_task(_RECOLOR_PAIRS)
    # Unblock: routed through the predict pipeline, the canonical rule reproduces.
    assert agent._rule_matches_examples(rule, task) is True
    assert agent._canonical_rule_reproduces(rule, task) is True


# ── the canonical gate REJECTS when the family renderer abstains ───────────────
def test_canonical_gate_rejects_when_renderer_abstains():
    agent = ActiveSoarAgent()
    rule = _canonical_recolor_rule()
    # An identity task is not a 1:1 non-identity recolor → analyze_color_remap
    # yields no map → the renderer abstains → the gate must say False (no false
    # positive that would persist a non-reproducing canonical rule).
    task = _fake_task([_pair([[5, 5]], [[5, 5]])])
    assert agent._rule_matches_examples(rule, task) is False


# ── once it passes, the canonical rule actually persists with a condition ──────
def test_passing_canonical_rule_persists_validly():
    rule = _canonical_recolor_rule()
    with tempfile.TemporaryDirectory() as tmp:
        path = save_rule_to_ltm(rule, "synthetic_recolor", tmp)
        assert os.path.isfile(path)
        import json
        with open(path) as fh:
            stored = json.load(fh)
        # Persisted in canonical schema (condition + action), not the legacy
        # {rule: ...} envelope — so it can enter covers and be AU-lifted.
        assert _is_canonical(stored)
        validate_rule(stored)            # raises if a required half is missing
        assert stored["condition"]["type"] == "color_remap"
        assert stored["action"]["dsl"] == RECOLOR_DSL
