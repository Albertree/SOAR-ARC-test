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
from agent.active_operators import PredictOperator, ExtractPatternOperator
from agent.conditions import match as match_condition
from agent.memory import (
    load_all_rules, save_rule, save_rule_to_ltm, increment_reuse_count, record_cover,
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
        stored_rules = load_all_rules(self.procedural_memory_root)
        # The descriptor fit (ExtractPattern) depends only on the task, not on the
        # rule, so compute it at most once and share it across the descriptor rules.
        descriptor_patterns = None
        for entry in stored_rules:
            rule = entry.get("rule", {})
            if rule.get("type") == "identity":
                continue  # skip identity fallback rules
            # R5 fast-path reuse (BACKLOG_LOOP.md R5). The learned families
            # (constant_output / object_motion / object_recolor) are *abstract*:
            # their argument expressions are holes (`?v`) filled from the example
            # comparison, so the input-grid-only `_apply_rule` declines them and
            # they used to be re-derived on the slow path every time (Reused: 0).
            # `_reuse_descriptor_rule` instead re-fits the stored rule's holes from
            # *this* task's own examples (§2.5-2b) and reuses the abstraction.
            if rule.get("type") in self._DESCRIPTOR_RULE_TYPES:
                if descriptor_patterns is None:
                    descriptor_patterns = self._fit_descriptor_patterns(task)
                predicted = self._reuse_descriptor_rule(rule, task, descriptor_patterns)
            elif self._rule_matches_examples(rule, task):
                predicted = self._apply_rule_to_tests(rule, task)
            else:
                predicted = None
            if predicted:
                increment_reuse_count(entry)
                # The reused rule just handled a task it was not yet credited
                # for — record it in covers so coverage (P1/P2) stays honest.
                record_cover(entry, task.task_hex)
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
            # Sanctioned save path: canonical {condition, action} rules sharing a
            # skeleton are anti-unified into one covers>1 rule (CLAUDE.md §8 /
            # BACKLOG_LOOP R3); legacy rules fall back to the exact-equivalence
            # covers-merge inside save_rule.
            save_rule(
                active_rules[0], task.task_hex,
                self.procedural_memory_root,
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

    # ---- R5 fast-path reuse of fitted-argument rules --------------------

    #: rule types whose action arguments are *expressions fitted from the
    #: example comparison* (BACKLOG_LOOP.md R0/R1, §2.5-2b) rather than literals
    #: carried on the rule. These cannot be applied from a single input grid —
    #: their holes must be re-fitted from the new task's own examples — so they
    #: go through `_reuse_descriptor_rule` instead of `_apply_rule`.
    _DESCRIPTOR_RULE_TYPES = ("constant_output", "object_motion", "object_recolor")

    @staticmethod
    def _fit_descriptor_patterns(task) -> dict:
        """Run ExtractPattern on `task` standalone to fit the argument expressions
        (output_invariant / object_motion / object_recolor) that the descriptor
        rules' holes are filled from. Depends only on the task, so the fast path
        computes it once and shares it across the descriptor rules."""
        wm = WorkingMemory()
        reset_wm_snapshot(wm)
        inject_arc_task(task, wm)
        ExtractPatternOperator().effect(wm)
        return wm.s1.get("patterns") or {}

    def _reuse_descriptor_rule(self, rule, task, patterns) -> list:
        """Reuse a stored *abstract* rule (constant_output / object_motion /
        object_recolor) on a new task — the Fast path of BACKLOG_LOOP.md R5.

        `patterns` is the descriptor fit for `task` (`_fit_descriptor_patterns`).
        The stored rule names a recognition condition and an action whose argument
        expressions are holes filled per task from the example comparison (§2.5-2b).
        Reuse therefore means: (1) the holes are re-fitted from *this* task's own
        example pairs (the same ExtractPattern fit the slow path uses); (2) require
        the rule's own condition matcher to fire on the fitted patterns — the stored
        abstraction must actually recognise this task; (3) gate on the fitted rule
        reproducing **every** example output exactly, so a superficial match that
        renders wrong is rejected rather than trusted; only then (4) render the test
        inputs. Returns the per-test predicted grids, or None to decline (the slow
        path then runs as before). Nothing here is value-specific to a task: the
        same stored rule re-fits to whatever this task's comparison yields, which is
        exactly value-agnostic reuse rather than literal replay."""
        cond = rule.get("condition") or {}
        cname = cond.get("type")
        if not cname:
            return None

        # (2) The stored abstraction must recognise this task. Use the rule's own
        # learned condition params (e.g. constant_output's min_evidence floor).
        if not match_condition(cname, patterns, cond.get("params") or {}):
            return None

        # (3) Build the per-input renderer for this rule type from the fitted
        # descriptors, then verify it reproduces every example output exactly.
        render = self._descriptor_renderer(rule.get("type"), patterns)
        if render is None:
            return None
        for pair in task.example_pairs:
            if pair.input_grid is None or pair.output_grid is None:
                continue
            if render(pair.input_grid) != pair.output_grid.raw:
                return None  # superficial match — decline, let the slow path run

        # (4) Reproduction held on every example → render the test inputs.
        grids = []
        for test_pair in task.test_pairs:
            if test_pair.input_grid is None:
                return None
            out = render(test_pair.input_grid)
            if out is None:
                return None
            grids.append(out)
        return grids or None

    @staticmethod
    def _descriptor_renderer(rule_type, patterns):
        """Return a `grid -> raw|None` renderer that instantiates `rule_type`'s
        fitted argument expressions (read from `patterns`) on a given input grid,
        reusing PredictOperator's existing make_grid+coloring renderers (CLAUDE.md
        §6.2) — no new transformation is introduced here. Returns None when the
        required descriptors were not fitted, so the caller declines."""
        if rule_type == "constant_output":
            inv = patterns.get("output_invariant") or {}
            if not inv.get("all_equal"):
                return None
            common = inv.get("common_output")
            if common is None:
                return None
            # The common output is constant — the input grid is irrelevant, but the
            # renderer keeps the uniform `grid -> raw` signature for the gate above.
            return lambda _g: PredictOperator._render_common_output(common)
        if rule_type == "object_motion":
            m = patterns.get("object_motion") or {}
            if m.get("target") is None:
                return None
            return lambda g: PredictOperator._render_object_motion(
                g, m.get("target"), m.get("out_shape"),
                m.get("selector"), m.get("scene"),
            )
        if rule_type == "object_recolor":
            r = patterns.get("object_recolor") or {}
            if r.get("selector") is None or r.get("source") is None:
                return None
            return lambda g: PredictOperator._render_object_recolor(
                g, r.get("selector"), r.get("source"),
            )
        return None

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
