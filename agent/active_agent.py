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
from agent import goal as goal_module
from agent.flow_trace import slice1_flow_steps
from agent.conditions.descent_path import slice1_descent_record
from agent.compare_scheduler import build_patterns, pair_grid_counts


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
        (step_000…) followed by the submitted prediction (final step). The trace
        also carries the §3 flow's observability triple, value-agnostic and
        answer-neutral: module A's hierarchical descent path
        (``slice1_descent_record``), module B's goal evolution
        (``_slice1_goal_record``), and module C's comparison-flow form
        (``slice1_flow_steps``) — so every episode records *how* the solve
        approached its answer (criterion 3), not just the answer.
        """
        grid_steps = []
        for pair in task.test_pairs:
            if pair.input_grid is not None:
                grid_steps.append(pair.input_grid.raw)
        if predicted:
            grid_steps.append(predicted)
        trace = list(trace or [])
        # The §3 hierarchical descent *path* (module A), value-agnostic: the
        # TASK→PAIR→GRID walk depth-entered-by-necessity (P1), terminal level
        # flagged. The spine of the raw-prose flow — recorded first so the episode
        # reads top-down (descend → form goal → run comparisons).
        trace.append(slice1_descent_record(task))
        goal_record = self._slice1_goal_record(task, predicted)
        if goal_record is not None:
            trace.append(goal_record)
        # The §3 comparison-flow *form* (module C), value-agnostic: which of the
        # PAIR/Intra/Inter recognition steps the solve traversed, decisive one
        # flagged. Records criterion-3 (접근성) alongside the goal walk — both
        # observability, neither alters the answer.
        trace.append(slice1_flow_steps(build_patterns(task)))
        write_episode(
            self.episodic_memory_root,
            task.task_hex,
            predicted=predicted,
            info=self.last_solve_info,
            trace=trace,
            grid_steps=grid_steps,
        )

    def _slice1_goal_record(self, task, predicted):
        """Build the §3 module-B goal trace for this solve (value-agnostic).

        The raw prose easy000a flow (``docs/arbor_context/arbor-flow-three-task-
        description.md``) forms a goal from the PAIR-level grid-count comparison
        — the test pair is missing its output grid, so the goal is *construct
        that grid* — and evolves it at GRID level into "determine {size, color,
        contents}". This drives module B (``agent/goal.py`` GoalStack) on the
        *live* task each solve(), so a previously-dormant intended module now
        executes on real data and every episode shows the §3 goal-basis of its
        answer (CLAUDE.md §7 / SLICE_1_LOOP.md §3 lines 104, 122).

        Value-agnostic (SLICE_1_LOOP.md §9 / P7): driven only by the structural
        grid-count census (counts, never a colour/coordinate), so easy000a (red)
        and easy000a2 (green) yield byte-identical goal trees. Returns ``None``
        when no output needs constructing (no deficient test pair) — module B has
        nothing to form.

        Each schema leaf "determine Gx.<prop>" is marked solved on its own
        *comparison basis*, not on the answer alone: a prediction must have been
        produced AND the decisive role-aligned Inter-Grid comparison of the
        example outputs must be COMM on that property (the ``all_outputs_comm``
        matcher restricted to a single property — the same module-E recognition
        the slow path fires). This operationalises P3/P4 in the goal trace
        (정답에는 근거가 있어야 하고, 근거는 비교의 결과에서 나온다 —
        SLICE_1_LOOP.md §3 lines 121-126: size/color/contents COMM → that leaf
        is determined): a property the comparison did *not* settle stays open
        even when an answer was emitted, so the trace localises which properties
        actually have a comparison basis rather than blanket-solving them because
        an answer appeared. A failed solve (no prediction) leaves every leaf open.
        """
        census = pair_grid_counts(task)
        stack = goal_module.build_goalstack_from_census(census)
        if stack is None:
            return None
        # Ground each schema leaf in its comparison basis (P3/P4) — but only once
        # an answer was emitted; a failed solve leaves every leaf open (honest
        # failure trace). The goal walk + comparison grounding both live in module
        # B (agent/goal.py) now; this method only decides *whether* to ground
        # (an episode-recording concern) and formats the trace record.
        if predicted:
            goal_module.mark_schema_leaves_by_comparison(stack, build_patterns(task))
        return {
            "phase": "goal_evolution",
            "module": "B",
            "satisfied": stack.is_satisfied(),
            "goal": stack.to_json(),
        }

    def _reuse_rule(self, rule, entry, task):
        """Fast-path reuse of one stored rule on `task`. Returns predicted grids
        or None when the rule does not apply.

        The only stored rule family in Slice 1 is the **task-level recognition**
        rule (``copy_common_output``): the answer is *constructed* from the whole
        task, not produced by a per-grid transform, so it cannot be verified by
        re-applying it to a single example input. It is verified through its
        stored recognition condition (CLAUDE.md §5.2: the fast path matches
        patterns against ``rule['condition']``) and constructed via the *same*
        code the slow path uses — so reuse and discovery share one route, not two.

        There is deliberately no second, per-grid "apply a transform to every
        test input" reuse branch. That branch belonged to the retired
        ``color_mapping`` / ``recolor_*`` detector family (CLAUDE.md §5.1) and
        dispatched through ``PredictOperator._apply_rule`` — the wrong mechanism
        for *discovered* transform rules, which CLAUDE.md §6.2 routes through
        ``apply_DSL`` resolving ``action.dsl`` via the rule's
        ``anti_unification_trace`` (the data layer), not a hand-coded applier.
        An unrecognised rule type therefore yields ``None`` (fall to the slow
        path) rather than a guessed transform.
        """
        if rule.get("type") == "copy_common_output":
            return self._reuse_copy_common_output(entry, task)
        return None

    def _reuse_copy_common_output(self, entry, task):
        """Reuse a stored copy-common-output rule (value-agnostic).

        Recognition is the plain CLAUDE.md §5.2 fast path: match the precomputed
        patterns against the rule's *own* ``condition`` by dispatching its
        ``condition.type`` (now the self-describing ``copy_common_output_applies``
        composite — PAIR ``test_output_missing`` ∧ GRID ``all_outputs_comm``).
        The rule's condition fully describes *when* it fires, so the fast path no
        longer re-supplies the PAIR precondition the slow path's recogniser
        already names — reuse and discovery resolve the identical matcher with no
        wrapping. Construction reuses ``PredictOperator``'s common example output
        materialised bottom-up through the two frozen DSL primitives. No
        comparison route or literal is re-derived here.
        """
        condition = entry.get("condition") or {}
        ctype = condition.get("type")
        if not ctype:
            return None

        patterns = build_patterns(task)
        params = dict(condition.get("params") or {})
        params.setdefault("min_evidence", condition.get("min_evidence", 1))
        if not conditions.match(ctype, patterns, params):
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
