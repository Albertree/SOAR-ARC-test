"""
test_live_descent_wiring — module A's HierarchicalDescent is wired into the
*live* SOAR cycle (iter 41).

Iter 40 implemented ``DescendOperator.effect`` but left it dormant — nothing
proposed it, so no real solve descended. This iter adds the wiring half the
SLICE_1_LOOP.md §4 module-A row names (``NeedsDescendRule``): a ``needs_descent``
elaboration flag + a ``DescendRule`` proposer, with ``NeedsTargetSelectionRule``
gated on ``descent-complete`` so the §3 order (descend TASK→PAIR→GRID, *then*
schedule comparisons) is performed by an operator on the live solve.

These tests assert the wiring fires on the real cycle, is value-agnostic
(easy000a red / easy000a2 green descend identically), gates target-selection
correctly, and is answer-preserving (both tasks still solve via the slow path).
Self-runs (pytest absent here).
"""

import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from managers.arc_manager import ARCManager
from agent.wm import WorkingMemory
from agent.cycle import run_cycle
from agent.elaboration_rules import build_elaborator, NeedsDescentRule
from agent.rules import build_proposer, DescendRule
from agent.io import inject_arc_task
from agent.active_agent import ActiveSoarAgent


def _load(tid):
    return ARCManager("data").load_task(tid)


def _run_slow(task):
    wm = WorkingMemory()
    inject_arc_task(task, wm)
    res = run_cycle(
        wm, build_elaborator(), build_proposer(),
        max_steps=50, stop_on_goal=True, log_wm=False,
    )
    return wm, res


# ---- registration ----------------------------------------------------------

def test_descend_rule_registered_in_proposer():
    names = [r.name for r in build_proposer()._rules]
    assert "rule_descend" in names
    # descend must precede target selection in the proposer order
    assert names.index("rule_descend") < names.index("rule_select_target")


def test_needs_descent_rule_registered_in_elaborator():
    names = [r.name for r in build_elaborator()._rules]
    assert "needs_descent" in names
    assert names.index("needs_descent") < names.index("needs_target_selection")


# ---- the descent fires on the live cycle -----------------------------------

def test_live_cycle_descends_to_grid():
    wm, res = _run_slow(_load("easy000a"))
    assert res["goal_satisfied"] is True
    assert wm.s1.get("descent-complete") is True
    assert wm.s1.get("focus-level") == "grid"
    path = wm.s1.get("descent-path")
    assert path["descend_from"] == ["task", "pair"]
    assert path["terminal"] == "grid"
    # the agenda is still scheduled *after* the descent (target selection ran)
    assert len(wm.s1.get("comparison-agenda") or []) > 0


def test_descent_is_value_agnostic():
    wm_a, _ = _run_slow(_load("easy000a"))
    wm_b, _ = _run_slow(_load("easy000a2"))
    # red vs green: byte-identical descent itinerary (no colour/coord influence)
    assert wm_a.s1.get("descent-path") == wm_b.s1.get("descent-path")
    assert wm_a.s1.get("focus-level") == wm_b.s1.get("focus-level") == "grid"


# ---- the gate: target selection only after descent --------------------------

class _GateWM:
    """Minimal WM stand-in to exercise the elaboration gate directly."""

    def __init__(self, s1, depth=1):
        self.s1 = s1
        self.depth = depth


def test_target_selection_gated_until_descent_complete():
    from agent.elaboration_rules import NeedsTargetSelectionRule
    nd = NeedsDescentRule("needs_descent")
    nt = NeedsTargetSelectionRule("needs_target_selection")

    # Before descent: needs_descent fires, target-selection does not.
    pre = _GateWM({"current-task": "T"})
    assert nd.condition(pre) is True
    assert nt.condition(pre) is False

    # After descent: target-selection fires, needs_descent stops (runs once).
    post = _GateWM({"current-task": "T", "descent-complete": True})
    assert nd.condition(post) is False
    assert nt.condition(post) is True

    # Once the agenda is scheduled, neither re-fires.
    done = _GateWM({"current-task": "T", "descent-complete": True,
                    "comparison-agenda": [1]})
    assert nd.condition(done) is False
    assert nt.condition(done) is False


def test_descend_rule_proposes_only_on_flag():
    dr = DescendRule()
    class _AW:
        def __init__(self, active, depth=1):
            self.active = active
            self.depth = depth
    assert dr.condition(_AW({"needs_descent": True})) is True
    assert dr.condition(_AW({})) is False
    assert dr.condition(_AW({"needs_descent": True}, depth=0)) is False


# ---- answer-preserving ------------------------------------------------------

def test_slow_path_still_solves_both():
    for tid in ("easy000a", "easy000a2"):
        task = _load(tid)
        agent = ActiveSoarAgent(
            procedural_memory_root=tempfile.mkdtemp(),
            episodic_memory_root=tempfile.mkdtemp(),
        )
        pred = agent.solve(task)
        assert agent.last_solve_info["method"] == "pipeline"
        assert agent.last_solve_info["rule_type"] == "copy_common_output"
        assert pred and pred[0] == task.test_pairs[0].output.contents


if __name__ == "__main__":
    funcs = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    failed = 0
    for fn in funcs:
        try:
            fn()
            print(f"PASS {fn.__name__}")
        except AssertionError as e:
            failed += 1
            print(f"FAIL {fn.__name__}: {e}")
        except Exception as e:
            failed += 1
            print(f"ERROR {fn.__name__}: {type(e).__name__}: {e}")
    print(f"\n{len(funcs) - failed}/{len(funcs)} passed")
    sys.exit(1 if failed else 0)
