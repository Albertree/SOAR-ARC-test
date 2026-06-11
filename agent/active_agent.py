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
from agent.episodic import write_attempt


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
        stored_rules = load_all_rules(self.procedural_memory_root)
        for entry in stored_rules:
            rule = entry.get("rule", {})
            if rule.get("type") == "identity":
                continue  # skip identity fallback rules
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
                    self._record_episode(task, predicted, cycle_result=None)
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

        # --- Learn: save new rule if pipeline discovered one ---
        if active_rules and rule_type != "identity":
            save_rule_to_ltm(
                active_rules[0], task.task_hex,
                self.procedural_memory_root,
            )

        self._submission_count += 1
        self._record_episode(task, predicted, cycle_result=result)
        return predicted

    # ---- helpers --------------------------------------------------------

    def _record_episode(self, task, predicted, cycle_result=None) -> None:
        """Write one episodic ``attempt_NNN/`` folder for this solve (CLAUDE.md §3.3).

        Records only what the (non-frozen) solve boundary can *observe*: the
        path taken (fast stored-rule vs slow pipeline), the cycle summary the
        frozen ``run_cycle`` returned, the rule that fired, and before/after
        grid snapshots (each test input + the produced prediction). The trace
        is summary-level and says so (``granularity: "summary"``) — it does not
        fabricate per-cycle entries the frozen cycle never exposed.

        Episodic writing must never break a learning run; a writer failure is
        surfaced on stderr (not silently swallowed) and the prediction still
        returns.
        """
        info = self.last_solve_info
        method = info.get("method", "none")

        grids = []
        try:
            for i, tp in enumerate(getattr(task, "test_pairs", []) or []):
                ig = getattr(tp, "input_grid", None)
                raw = getattr(ig, "raw", None)
                if raw is not None:
                    grids.append((f"test{i}-input", raw))
        except Exception:
            pass
        grids.append(("predicted", predicted))

        trace = {
            "task": task.task_hex,
            "granularity": "summary",   # cycle.py frozen — no per-cycle hook (§4)
            "path": method,
            "rule_type": info.get("rule_type"),
            "rule_source": info.get("rule_source"),
            "steps_taken": info.get("steps", 0),
            "goal_satisfied": (
                bool(cycle_result.get("goal_satisfied"))
                if isinstance(cycle_result, dict) else None
            ),
        }

        metadata = {
            "task": task.task_hex,
            "method": method,
            "rule_type": info.get("rule_type"),
            "rule_source": info.get("rule_source"),
            "steps": info.get("steps", 0),
            "n_test_pairs": len(getattr(task, "test_pairs", []) or []),
            "outcome": "prediction-produced" if predicted else "no-prediction",
            "submission_index": self._submission_count,
            # Anti-unification is not yet wired into save_rule (§8); honest 0.
            "anti_unification_invocations": 0,
        }

        try:
            write_attempt(
                task.task_hex,
                trace=trace,
                metadata=metadata,
                grids=grids,
                episodic_root=self.episodic_memory_root,
            )
        except Exception as e:  # never let episodic I/O break a learning run
            import sys
            print(f"[episodic] failed to write attempt for "
                  f"{task.task_hex}: {e}", file=sys.stderr)

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
