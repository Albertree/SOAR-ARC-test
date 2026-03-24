"""
ActiveSoarAgent — Main SOAR agent.
Implements the agent.solve(task) interface for ARCEnvironment.
"""

from agent.wm import WorkingMemory
from agent.cycle import run_cycle
from agent.elaboration_rules import build_elaborator
from agent.rules import build_proposer
from agent.memory import load_rules_from_ltm, chunk_from_substate, save_rule_to_ltm
from agent.agent_common import build_wm_from_task, goal_satisfied, answers_from_wm
from agent.wm_logger import reset_wm_snapshot


class ActiveSoarAgent:
    """
    [SOAR MANDATORY] There must be an agent wrapper that runs the SOAR cycle.
    [DESIGN FREE] solve() call limit (can_retry), LTM load method,
                  chunking callback connection method.
    MUST NOT: Do not use a separate solver like ARCSolver as fallback.
              solve() 1 call = 1 submission.
    """

    def __init__(self, semantic_memory_root: str = "semantic_memory"):
        """[DESIGN FREE] semantic_memory_root path, submission count counter."""
        self.semantic_memory_root = semantic_memory_root
        self._submission_count: int = 0
        self._current_task_hex: str = None

    def solve(self, task) -> list:
        """
        [SOAR MANDATORY] The cycle execution flow itself (WM initialization → run_cycle → result extraction).
        [DESIGN FREE] LTM rule preloading method, max_steps value.

        Flow:
          1. Reset _submission_count if new task
          2. Call reset_wm_snapshot()  ← Reset diff state at each task boundary
          3. Create WorkingMemory
          4. build_wm_from_task(task, wm)
          5. Load LTM rules → Initialize wm.s1["active_rules"]
          6. elaborator = build_elaborator()
          7. proposer   = build_proposer()
          8. run_cycle(wm, elaborator, proposer, max_steps=50)
          9. answers = answers_from_wm(wm)
          10. _submission_count += 1
          11. return answers
        """
        reset_wm_snapshot()
        raise NotImplementedError("ActiveSoarAgent.solve() not implemented yet.")

    def on_substate_resolved(self, substate: dict, task_hex: str):
        """
        [SOAR MANDATORY] Triggers chunking when subgoal is resolved.
        [DESIGN FREE] How to store the chunk result.
        MUST NOT: Do not call directly inside the solve loop — cycle.py calls this.
        """
        raise NotImplementedError("ActiveSoarAgent.on_substate_resolved() not implemented.")

    @property
    def can_retry(self) -> bool:
        """[DESIGN FREE] Maximum submission count (currently 3). Per-task counter."""
        return self._submission_count < 3
