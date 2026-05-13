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
from agent.conditions import recognized_conditions
from agent.memory import (
    load_all_rules,
    increment_reuse_count,
    load_related,
    next_rule_id,
    save_rule,
    translate_to_schema,
)
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
            "fired_conditions": [],
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
                    self._record_attempt(task.task_hex, predicted)
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
            "fired_conditions": recognized_conditions(
                wm.s1.get("patterns", {})
            ),
        })

        # --- Learn: save new rule if pipeline discovered one ---
        if active_rules:
            self._persist_pipeline_rule(
                active_rules[0], task.task_hex,
                wm.s1.get("patterns", {}),
            )

        self._submission_count += 1
        self._record_attempt(task.task_hex, predicted)
        return predicted

    # ---- helpers --------------------------------------------------------

    def _persist_pipeline_rule(self, legacy_rule, task_hex: str,
                               patterns: dict) -> str | None:
        """Iter 15 migration: post-pipeline save dispatch.

        Routes through the schema-aware writer (``save_rule``) when
        ``translate_to_schema`` returns a §1-shaped rule — currently only
        the identity legacy shape, and only when ``identity_transformation``
        actually fires on ``patterns``. Otherwise the rule is dropped: the
        non-translatable slow-path shapes (color_mapping,
        recolor_sequential) still need an anti-unification-discovered
        abstraction for ``action.dsl`` before they have a §1
        representation, and the only on-disk shape the legacy writer
        ``save_rule_to_ltm`` could produce for them is one that violates
        F4 (no ``condition`` key). Until anti-unification fills that gap,
        skipping the save is the F4-safe behavior. ``save_rule_to_ltm``
        remains in ``agent/memory.py`` for future callers but is no longer
        invoked by ``solve()``.

        Returns the path of the file written, or ``None`` if no rule was
        persisted. Lifted out of ``solve()`` so the dispatch can be
        unit-tested without driving the full SOAR cycle.
        """
        if not isinstance(legacy_rule, dict):
            return None
        schema_rule = translate_to_schema(
            legacy_rule, task_hex, patterns,
            rule_id=next_rule_id(self.procedural_memory_root),
        )
        if schema_rule is None:
            return None
        related = load_related(
            schema_rule["category"],
            procedural_memory_root=self.procedural_memory_root,
        )
        return save_rule(
            schema_rule,
            related_rules=related,
            procedural_memory_root=self.procedural_memory_root,
        )

    def _record_attempt(self, task_hex: str, predicted) -> None:
        """Persist one episodic_memory/<task_hex>/attempt_NNN/ entry per
        ``solve()`` invocation (CLAUDE.md §3.3, INVARIANTS.md P4)."""
        outcome = "submitted" if predicted is not None else "no_prediction"
        write_attempt(
            task_hex,
            outcome=outcome,
            info=dict(self.last_solve_info),
            root=self.episodic_memory_root,
        )

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
