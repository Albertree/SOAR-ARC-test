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

        # --- Fast path: try stored rules (legacy or §1-schema shape) ---
        stored_rules = load_all_rules(self.procedural_memory_root)
        for entry in stored_rules:
            if not isinstance(entry, dict):
                continue
            if self._is_identity_rule(entry):
                continue  # skip identity fallback rules (legacy or schema)
            if self._entry_matches_examples(entry, task):
                predicted = self._apply_entry_to_tests(entry, task)
                if predicted:
                    increment_reuse_count(entry)
                    self.last_solve_info.update({
                        "method": "stored_rule",
                        "rule_type": self._entry_rule_type(entry),
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

    def _is_identity_rule(self, entry) -> bool:
        """True if ``entry`` encodes a no-op identity rule (legacy or §1).

        Both rule shapes can carry an identity rule. Skipping them in the
        fast path preserves the pre-iter-16 ``rule.get("type") ==
        "identity"`` short-circuit's semantic: an identity rule "matches"
        any task whose training pairs all have input == output, but that
        is almost never the right answer for an unseen test pair. The
        skip stays until anti-unification produces a non-no-op
        identity-shaped abstraction.
        """
        if not isinstance(entry, dict):
            return False
        legacy_rule = entry.get("rule")
        if isinstance(legacy_rule, dict) and legacy_rule.get("type") == "identity":
            return True
        cond = entry.get("condition")
        if isinstance(cond, dict) and cond.get("type") == "identity_transformation":
            return True
        return False

    def _entry_rule_type(self, entry) -> str:
        """Surface a human-readable type tag for ``last_solve_info``.

        Legacy entries expose ``entry["rule"]["type"]``; schema entries
        expose ``entry["condition"]["type"]``. Falls back to ``"unknown"``
        for anything else so the field is always a string.
        """
        if not isinstance(entry, dict):
            return "unknown"
        legacy_rule = entry.get("rule")
        if isinstance(legacy_rule, dict) and isinstance(legacy_rule.get("type"), str):
            return legacy_rule["type"]
        cond = entry.get("condition")
        if isinstance(cond, dict) and isinstance(cond.get("type"), str):
            return cond["type"]
        return "unknown"

    def _entry_matches_examples(self, entry, task) -> bool:
        """True iff ``entry``'s action reproduces every example pair's
        output when applied to its input. Dispatches across legacy and
        §1-schema shapes via ``_predict_with_entry``."""
        for pair in task.example_pairs:
            if pair.input_grid is None or pair.output_grid is None:
                continue
            predicted = self._predict_with_entry(entry, pair.input_grid)
            if predicted is None or predicted != pair.output_grid.raw:
                return False
        return True

    def _apply_entry_to_tests(self, entry, task) -> list:
        """Apply ``entry``'s action to every test input. Returns a list
        of predicted grids, or ``None`` if any test pair cannot be
        predicted (preserving the all-or-nothing semantics of the
        pre-iter-16 helper)."""
        grids = []
        for test_pair in task.test_pairs:
            if test_pair.input_grid is None:
                return None
            predicted = self._predict_with_entry(entry, test_pair.input_grid)
            if predicted is None:
                return None
            grids.append(predicted)
        return grids

    def _predict_with_entry(self, entry, input_grid):
        """Dispatch rule application across legacy and §1-schema shapes.

        Schema entries (``{condition, action, ...}``) route through
        ``apply_DSL`` so iter-3's primitive layer is the sole runtime
        evaluator for §1-shaped rules — schema rules persisted by
        ``_persist_pipeline_rule`` (iter 15) can now be re-applied here
        instead of being silently ignored (the pre-iter-16 fast path
        called ``entry.get("rule", {})`` which returns ``{}`` on a
        schema entry, then ``PredictOperator._apply_rule({}, ...)``
        returned ``None``). Legacy entries continue to dispatch through
        ``PredictOperator._apply_rule``.

        Returns the predicted grid (list of lists of ints) or ``None``
        if the rule cannot be applied to this input. A primitive that
        raises ``ValueError``/``KeyError`` at apply time (e.g. OOB
        selection from a saved rule applied to a smaller grid) is
        treated as "rule does not apply here" → ``None``, matching the
        legacy applier's graceful-fail contract. ``RuleSchemaError`` is
        not caught here (it can only be raised on the save path) so F7
        stays inert.
        """
        if not isinstance(entry, dict) or input_grid is None:
            return None
        action = entry.get("action")
        if isinstance(action, dict) and isinstance(action.get("dsl"), str):
            from procedural_memory.DSL.apply import DSL_REGISTRY, apply_DSL
            dsl_name = action["dsl"]
            if dsl_name not in DSL_REGISTRY:
                return None
            args = action.get("args") if isinstance(action.get("args"), dict) else {}
            try:
                if dsl_name == "make_grid":
                    return apply_DSL("make_grid", **args)
                return apply_DSL(dsl_name, grid=input_grid.raw, **args)
            except (ValueError, KeyError, TypeError):
                return None
        # Legacy shape — preserve pre-iter-16 dispatch.
        legacy_rule = entry.get("rule") if isinstance(entry.get("rule"), dict) else {}
        return self._predictor._apply_rule(legacy_rule, input_grid)

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
