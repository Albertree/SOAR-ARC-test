"""
ActiveSoarAgent — Main SOAR agent with memory-based learning.

Solve flow:
  1. Load stored rules from procedural_memory
  2. Try each stored rule against example pairs (fast path)
  3. If a stored rule works → apply to test input, return
  4. If none work → run full SOAR pipeline (slow path)
  5. If pipeline discovers a new rule → save to procedural_memory
"""

from types import SimpleNamespace

from agent.wm import WorkingMemory
from agent.cycle import run_cycle
from agent.elaboration_rules import build_elaborator
from agent.rules import build_proposer
from agent.io import inject_arc_task
from agent.active_operators import PredictOperator, SIZE_GRID_DSL
from agent.conditions import match as match_condition
from agent.dsl_expr.selection import analyze_object_size_grid
from agent.memory import load_all_rules, save_rule_to_ltm, increment_reuse_count
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

        # --- Fast-path activation table for *abstract* (covers>1) rules (R5) ---
        # A lifted anti-unification rule is an *incomplete* program: its action
        # carries a ``?vN`` variable whose filler must be chosen from the new
        # task's own COMM before it can run (BACKLOG_LOOP §2.5-2b — "AU 결과는
        # 미완성; 변수를 채우는 선택이 선행돼야"). The legacy ``_apply_rule``
        # dispatcher only knows the three concrete legacy types, so the stored
        # abstractions never fired and every task re-derived through the Slow path
        # (`Reused: 0`). Each entry maps an abstract ``action.dsl`` to
        #   (condition.type, patterns_fn, render_fn)
        # where the condition matcher is the *activation* test (module E) and the
        # render_fn recomputes the variable from the task's examples and renders —
        # i.e. the stored rule is *reused* rather than rediscovered. Scoped to the
        # size_to_grid family for this slice (the simplest abstraction, whose
        # renderer already self-resolves its property from the pairs); place_object
        # / copy_common reuse are later, separate steps.
        self._abstract_reuse = {
            SIZE_GRID_DSL: (
                "object_size_grid",
                lambda task: {
                    "object_size_grid": analyze_object_size_grid(task.example_pairs)
                },
                self._predictor._place_size_grid_grids,
            ),
        }

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
            # Abstract (covers>1) rule reuse: activate the stored rule via its
            # condition matcher and resolve+render it on this task (R5, §2.5-2b).
            predicted = self._reuse_abstract_rule(entry, task)
            if predicted:
                increment_reuse_count(entry)
                self.last_solve_info.update({
                    "method": "stored_rule",
                    "rule_type": entry.get("concept")
                    or entry.get("action", {}).get("dsl", "abstract"),
                    "rule_source": entry.get("source_task"),
                })
                self._submission_count += 1
                return predicted

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
        return predicted

    # ---- abstract (covers>1) rule reuse — R5 / §2.5-2b -------------------

    def _reuse_abstract_rule(self, entry, task):
        """Activate a stored *abstract* rule on ``task`` and return its test
        predictions, or None when it does not apply.

        The reuse loop the legacy applier could not express (BACKLOG_LOOP §2.5-2b,
        R5): a lifted ``covers>1`` rule is a program with a *hole* (its ``?vN``
        variable). To run it on a fresh task its filler must be chosen from *this*
        task's comparison evidence, not the source task's. Steps:

        1. **Activation** — the stored rule's own ``condition`` matcher must fire on
           the task's patterns (module E: a learned rule recognises a new task).
        2. **Resolution + render** — the family's render_fn recomputes the variable
           from the task's example COMM and renders (the §2.5-2b "fill the hole from
           COMM" step). This is reuse of the *abstraction*, not Slow-path rediscovery.
        3. **Safety gate** — the resolved program must reproduce *every* example
           output exactly; otherwise we decline and the Slow path runs unchanged, so
           reuse can never turn a solved task into a wrong answer (only skip a reuse).
        """
        action = entry.get("action") or {}
        condition = entry.get("condition") or {}
        spec = self._abstract_reuse.get(action.get("dsl"))
        if spec is None:
            return None
        cond_type, patterns_fn, render_fn = spec
        if condition.get("type") != cond_type:
            return None

        # 1. Activation: the stored rule's condition matcher fires on this task.
        try:
            if not match_condition(cond_type, patterns_fn(task),
                                   condition.get("params") or {}):
                return None
        except KeyError:
            return None

        # 3. Safety gate: the resolved abstraction reproduces every example output.
        if not self._reproduces_examples(render_fn, task):
            return None

        # 2. Render the test predictions from the (now resolved) abstraction.
        grids = render_fn(task)
        predicted = []
        for i in range(len(task.test_pairs)):
            if grids.get(i) is None:
                return None
            predicted.append(grids[i])
        return predicted or None

    @staticmethod
    def _reproduces_examples(render_fn, task) -> bool:
        """True iff the abstraction renders *every* example input back to its known
        output. The render_fn learns from ``example_pairs`` and renders
        ``test_pairs``; pointing both at the example pairs makes it predict the
        examples, which we check against their actual outputs (the §2.5-2b verify
        step that keeps reuse honest)."""
        examples = list(task.example_pairs)
        if not examples:
            return False
        shim = SimpleNamespace(example_pairs=examples, test_pairs=examples)
        rendered = render_fn(shim)
        for i, pair in enumerate(examples):
            if pair.output_grid is None or rendered.get(i) != pair.output_grid.raw:
                return False
        return True

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
