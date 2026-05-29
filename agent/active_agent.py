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
from agent.memory import load_all_rules, save_rule_to_ltm, increment_reuse_count
from agent.wm_logger import reset_wm_snapshot
from agent.episodic import write_episode
from agent import conditions
from agent.compare_scheduler import build_patterns


class ActiveSoarAgent:
    """
    SOAR agent that accumulates knowledge across tasks.
    Each solve() call checks stored rules first, then falls back to the pipeline.
    New rules are saved after successful pipeline discoveries.
    """

    def __init__(self, semantic_memory_root: str = "semantic_memory",
                 procedural_memory_root: str = "procedural_memory",
                 episodic_memory_root: str = "episodic_memory",
                 max_steps: int = 50):
        self.semantic_memory_root = semantic_memory_root
        self.procedural_memory_root = procedural_memory_root
        self.episodic_memory_root = episodic_memory_root
        self.max_steps = max_steps
        self._submission_count: int = 0
        self._current_task_hex: str = None
        self._predictor = PredictOperator()

        # Stats for logging
        self.last_solve_info = {}

    def solve(self, task, log_wm: bool = False) -> list:
        """
        Solve one task. Returns list of predicted grids (one per test pair).
        Tries stored rules first, then full pipeline.

        log_wm: when True, the slow-path SOAR cycle prints WM triplets per phase
        (for diagnosis). The fast path (stored rules) has no cycle to log.
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
        stored_rules = load_all_rules(self.procedural_memory_root)
        for entry in stored_rules:
            rule = entry.get("rule", {})
            if rule.get("type") == "identity":
                continue  # skip identity fallback rules
            predicted = self._reuse_rule(rule, entry, task)
            if predicted:
                increment_reuse_count(entry)
                self.last_solve_info.update({
                    "method": "stored_rule",
                    "rule_type": rule.get("type", "unknown"),
                    "rule_source": entry.get("source_task"),
                })
                self._submission_count += 1
                self._record_episode(
                    task, predicted,
                    trace=[{
                        "phase": "stored_rule_hit",
                        "method": "stored_rule",
                        "rule_type": rule.get("type", "unknown"),
                        "rule_source": entry.get("source_task"),
                    }],
                )
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
            log_wm=log_wm,
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

        # --- Learn: save new rule if pipeline discovered one ---
        if active_rules and rule_type != "identity":
            save_rule_to_ltm(
                active_rules[0], task.task_hex,
                self.procedural_memory_root,
            )

        self._submission_count += 1
        self._record_episode(
            task, predicted,
            trace=[{
                "phase": "cycle_summary",
                "method": "pipeline",
                "rule_type": rule_type,
                "steps_taken": result["steps_taken"],
                "goal_satisfied": result["goal_satisfied"],
                "active_rule": active_rules[0] if active_rules else None,
            }],
        )
        return predicted

    # ---- helpers --------------------------------------------------------

    def _record_episode(self, task, predicted, trace) -> None:
        """Write one episodic attempt folder for this solve() (CLAUDE.md §3.3).

        Captured from outside the frozen cycle: the test input grids
        (step_000…) followed by the submitted prediction (final step).
        """
        grid_steps = []
        for pair in task.test_pairs:
            if pair.input_grid is not None:
                grid_steps.append(pair.input_grid.raw)
        if predicted:
            grid_steps.append(predicted)
        write_episode(
            self.episodic_memory_root,
            task.task_hex,
            predicted=predicted,
            info=self.last_solve_info,
            trace=trace,
            grid_steps=grid_steps,
        )

    def _reuse_rule(self, rule, entry, task):
        """Fast-path reuse of one stored rule on `task`. Returns predicted grids
        or None when the rule does not apply.

        Two rule families need different reuse mechanisms:

        * **Task-level recognition rules** (e.g. ``copy_common_output``): the
          answer is *constructed* from the whole task, not produced by a per-grid
          transform, so it cannot be verified by re-applying it to a single
          example input. It is verified through its stored recognition condition
          (CLAUDE.md §5.2: the fast path matches patterns against
          ``rule['condition']``) and constructed via the *same* code the slow
          path uses — so reuse and discovery share one route, not two.
        * **Grid-level transform rules** (``color_mapping`` / ``recolor_*``): a
          per-grid transform verified by reproducing every example output and
          then applied to the test inputs (the original fast-path mechanism).
        """
        if rule.get("type") == "copy_common_output":
            return self._reuse_copy_common_output(entry, task)

        if not self._rule_matches_examples(rule, task):
            return None
        return self._apply_rule_to_tests(rule, task)

    def _reuse_copy_common_output(self, entry, task):
        """Reuse a stored copy-common-output rule (value-agnostic).

        Recognition reuses the *exact* matchers the slow path's
        ``GeneralizeOperator`` fires (``test_output_missing`` +
        ``all_outputs_comm``, the latter named by the rule's own
        ``condition.type``); construction reuses ``PredictOperator``'s common
        example output materialised bottom-up through the two frozen DSL
        primitives. No comparison route or literal is re-derived here.
        """
        condition = entry.get("condition") or {}
        ctype = condition.get("type")
        if not ctype:
            return None

        patterns = build_patterns(task)
        if not conditions.match("test_output_missing", patterns,
                                {"min_evidence": 1}):
            return None
        if not conditions.match(
            ctype, patterns,
            {"min_evidence": condition.get("min_evidence", 1),
             "required_properties": ["size", "color", "contents"]},
        ):
            return None

        common = self._predictor._common_example_output(task)
        if common is None:
            return None

        from agent.memory import reconstruct_via_dsl
        grids = []
        for test_pair in task.test_pairs:
            if test_pair.input_grid is None:
                return None
            grids.append(reconstruct_via_dsl(common))
        return grids

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
