"""
Tests for the ARC_easy 4x4 benchmark family (easy0001..easy0016), the user's
own systematically-structured probe matrix. Rows vary the *input* (identical /
colour-varying / position-varying / both); columns vary the *output rule*
(constant grid / move-to-corner / move-to-edge / property-scaled target).

This file pins two things the iter-9 microscope surfaced (logs/session_log.md):

1. **Generalization, not accretion (P1/P2).** The R1 `place_object` abstraction
   built for the easy_a c..i family also covers the easy-slice members whose
   rule is "relocate the single object onto a constant cell, colour preserved"
   — easy0006 and easy0014. They are solved by the *same module* with no new
   rule and no per-task detector (BACKLOG_LOOP.md §2.5-3/4): one general rule
   absorbing more of the family is exactly what P1 measures.

2. **Abstention on ill-posed examples (P3: reasons over values).** easy0002,
   easy0003 and easy0004 are *non-functional*: their two training pairs have
   **identical inputs mapping to different outputs** (e.g. easy0002:
   2@(1,1)->2@(5,5) and 2@(1,1)->1@(5,5)). No deterministic symbolic rule can
   exist, so the agent must NOT fabricate one — it correctly falls through to
   identity (abstains). This test locks that behaviour so a future iter does
   not "solve" them by guessing, which would be the score-chasing failure the
   whole project forbids.

Note (open question, deliberately NOT tested as solvable): the *functional*
failing members — easy0007/0008/0010/0011/0015/0016 — need the target cell or
output colour derived as a **relation on the moving object's property** (e.g.
easy0008: target == (2*colour, 2*colour)). That is variable-origin derivation,
arbor-open-questions Q-B3/Q-B4 + the §2.5-2b "AU product is incomplete until the
variable is filled" gap. Per BACKLOG_LOOP.md §5 the loop holds that rung and
surfaces the question rather than inventing an answer; these tasks are expected
to abstain (identity) until that mechanism is designed.
"""

import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def _load_task(task_path, data_root="data"):
    from managers.arc_manager import ARCManager
    with tempfile.TemporaryDirectory() as tmp:
        return ARCManager(data_root=data_root,
                          semantic_memory_root=tmp).load_task(task_path)


def _run_pipeline(task):
    """Extract -> Generalize -> Predict on a fresh WM; return the active rule
    and whether the prediction matches the known test output."""
    from agent.wm import WorkingMemory
    from agent.active_operators import (
        ExtractPatternOperator, GeneralizeOperator, PredictOperator,
    )
    wm = WorkingMemory()
    wm.task = task
    ExtractPatternOperator().effect(wm)
    GeneralizeOperator().effect(wm)
    PredictOperator().effect(wm)
    rule = wm.s1["active-rules"][0]
    preds = wm.s1.get("predictions") or {}
    expected = task.test_pairs[0].output_grid.raw
    return rule, (preds.get("test_0") == expected)


# ── 1. generalization: place_object absorbs easy0006 / easy0014 ────────
def test_place_object_solves_easy_slice_movers():
    # "Relocate single object to a constant cell, colour preserved" — the same
    # fixed-target filling that solves easy_a c/d/h, now applied to two members
    # of the easy slice. Same module, no new rule (P1/P2 grow via covers).
    for name in ["0006", "0014"]:
        rule, correct = _run_pipeline(_load_task(f"ARC_easy/easy{name}"))
        assert rule["type"] == "place_object", name
        assert correct is True, name


# ── 2. abstention: contradictory examples => identity, never a guess ────
def test_abstains_on_contradictory_examples():
    # Identical inputs -> different outputs across training pairs. No function
    # exists; the agent must abstain (identity), not fabricate a rule (P3/P4).
    for name in ["0002", "0003", "0004"]:
        rule, correct = _run_pipeline(_load_task(f"ARC_easy/easy{name}"))
        assert rule["type"] == "identity", name
        # And it must NOT accidentally produce the correct grid by guessing.
        assert correct is False, name


# ── 3. variable-origin gap is held, not invented (open Q-B3/Q-B4) ──────
def test_property_relation_targets_abstain_pending_open_question():
    # easy0007/0008: target / colour is a relation on the object's property
    # (variable origin). Until that mechanism is designed (it touches an open
    # design question), the agent abstains rather than overfitting a 2-point
    # relation. Locking this prevents a premature, score-chasing "fix".
    for name in ["0007", "0008"]:
        rule, _ = _run_pipeline(_load_task(f"ARC_easy/easy{name}"))
        assert rule["type"] == "identity", name
