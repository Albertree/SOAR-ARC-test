"""
ActiveSoarAgent — Main SOAR agent with memory-based learning.

Solve flow:
  1. Load stored rules from procedural_memory
  2. Try each stored rule against example pairs (fast path)
  3. If a stored rule works → apply to test input, return
  4. If none work → run full SOAR pipeline (slow path)
  5. If pipeline discovers a new rule → save to procedural_memory
"""

from agent.wm import WorkingMemory
from agent.cycle import run_cycle
from agent.elaboration_rules import build_elaborator
from agent.rules import build_proposer
from agent.io import inject_arc_task
from agent.active_operators import PredictOperator
from agent.memory import (
    load_all_rules, save_rule, increment_reuse_count, applicable_rule,
    _has_unresolved_var,
)
from agent.wm_logger import reset_wm_snapshot


class ActiveSoarAgent:
    """
    SOAR agent that accumulates knowledge across tasks.
    Each solve() call checks stored rules first, then falls back to the pipeline.
    New rules are saved after successful pipeline discoveries.
    """

    def __init__(self, semantic_memory_root: str = "semantic_memory",
                 procedural_memory_root: str = "procedural_memory",
                 max_steps: int = 50):
        self.semantic_memory_root = semantic_memory_root
        self.procedural_memory_root = procedural_memory_root
        self.max_steps = max_steps
        self._submission_count: int = 0
        self._current_task_hex: str = None
        self._predictor = PredictOperator()

        # Stats for logging
        self.last_solve_info = {}

    def solve(self, task) -> list:
        """
        Solve one task. Returns list of predicted grids (one per test pair).
        Tries stored rules first, then full pipeline.
        """
        if self._current_task_hex != task.task_hex:
            self._current_task_hex = task.task_hex
            self._submission_count = 0

        self.last_solve_info = {
            "task_hex": task.task_hex,
            "method": "none",
            "rule_type": "none",
            "steps": 0,
            "rule_source": None,
        }

        # --- Fast path: try stored rules ---
        # `applicable_rule` bridges the persisted {condition, action} schema to a
        # PredictOperator-applicable prediction-rule (stamping the dispatch
        # `type`); it returns None for unknown recipes and for abstract rules
        # whose anti-unification variable is unresolved (those fall through to the
        # slow path rather than reuse a false match). The render helpers read the
        # current task off the predictor, so seed it before replay.
        self._predictor._task = task
        stored_rules = load_all_rules(self.procedural_memory_root)
        # Prefer a *concrete* rule over a runtime-resolved abstraction. When both
        # reproduce the examples (a genuine ambiguity — e.g. a constant-output
        # task is also consistent with "move the single object to a fixed cell"),
        # the rule that needed a `?v` hole *filled* to fit is the weaker
        # commitment; the fully-determined reading wins. This is Occam, and P1
        # (descend to the object-level filling only when a grid-level rule does
        # not already explain the task). Stable sort keeps the load order
        # (times_reused desc) within each group.
        stored_rules.sort(
            key=lambda e: _has_unresolved_var((e.get("action") or {}).get("args")))
        for entry in stored_rules:
            rule = applicable_rule(entry)
            if rule is None:
                continue
            if self._rule_matches_examples(rule, task):
                predicted = self._apply_rule_to_tests(rule, task)
                if predicted:
                    increment_reuse_count(entry)
                    self.last_solve_info.update({
                        "method": "stored_rule",
                        "rule_type": rule.get("type", "unknown"),
                        "rule_source": entry.get("source_task"),
                    })
                    self._submission_count += 1
                    return predicted

        # --- Slow path: full SOAR pipeline ---
        wm = WorkingMemory()
        reset_wm_snapshot(wm)
        inject_arc_task(task, wm)

        elaborator = build_elaborator()
        proposer = build_proposer()

        result = run_cycle(
            wm, elaborator, proposer,
            max_steps=self.max_steps,
            stop_on_goal=True,
            log_wm=False,
        )

        predicted = self._extract_prediction(wm)

        active_rules = wm.s1.get("active-rules")
        rule_type = "none"
        if active_rules and isinstance(active_rules, list):
            rule_type = active_rules[0].get("type", "none")

        self.last_solve_info.update({
            "method": "pipeline",
            "rule_type": rule_type,
            "steps": result["steps_taken"],
        })

        # --- Learn: persist only a valid {condition, action} rule ---
        # The pipeline emits either a {condition, action} rule (e.g. R0's
        # constant_output) or an identity fallback. Only the former is learned;
        # identity / condition-less results are not written, so no dead,
        # condition-less memory accumulates (INVARIANTS F4). save_rule validates
        # and raises RuleSchemaError on a malformed rule rather than swallowing
        # it (F7).
        if active_rules:
            rule = active_rules[0]
            if rule.get("condition") and rule.get("action"):
                save_rule(
                    rule, task.task_hex,
                    procedural_memory_root=self.procedural_memory_root,
                )

        self._submission_count += 1
        return predicted

    # ---- helpers --------------------------------------------------------

    def _rule_matches_examples(self, rule, task) -> bool:
        """Check if a rule produces correct output for ALL example pairs."""
        for pair in task.example_pairs:
            if pair.input_grid is None or pair.output_grid is None:
                continue
            predicted = self._predictor._apply_rule(rule, pair.input_grid)
            if predicted is None or predicted != pair.output_grid.raw:
                return False
        return True

    def _apply_rule_to_tests(self, rule, task) -> list:
        """Apply a rule to all test inputs. Returns list of predicted grids."""
        grids = []
        for test_pair in task.test_pairs:
            if test_pair.input_grid is None:
                return None
            predicted = self._predictor._apply_rule(rule, test_pair.input_grid)
            if predicted is None:
                return None
            grids.append(predicted)
        return grids

    @staticmethod
    def _extract_prediction(wm) -> list:
        """Extract predicted grids from WM output-link."""
        try:
            s1 = wm.s1.get("S1")
            if not s1:
                return None
            output_link_id = s1.get("output-link")
            if not output_link_id:
                return None
            output_node = wm.s1.get(output_link_id)
            if not output_node:
                return None
            return output_node.get("predicted-grid")
        except Exception:
            return None

    @property
    def can_retry(self) -> bool:
        return self._submission_count < 3
