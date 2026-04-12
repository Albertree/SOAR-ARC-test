"""
ActiveSoarAgent — Main SOAR agent with memory-based learning.

Solve flow:
  1. Compute structural fingerprint of the new task
  2. Search episodic memory for similar past tasks (Case-Based Reasoning)
  3. If a similar episode is found, try its rule first
  4. Else try all stored rules from procedural_memory (flat scan)
  5. If nothing works → run full SOAR pipeline (slow path)
  6. If pipeline discovers a new rule → save to procedural + episodic memory
"""

import os

from agent.wm import WorkingMemory
from agent.cycle import run_cycle
from agent.elaboration_rules import build_elaborator
from agent.rules import build_proposer
from agent.io import inject_arc_task
from agent.active_operators import PredictOperator
from agent.memory import load_all_rules, save_rule_to_ltm, increment_reuse_count
from agent.wm_logger import reset_wm_snapshot
from agent.episodic import (
    compute_fingerprint, save_episode, build_structural_key,
    find_similar_episodes, load_episodes, extract_topology,
)
from ARCKG.comparison import compare as arckg_compare


class ActiveSoarAgent:
    """
    SOAR agent that accumulates knowledge across tasks.
    Each solve() call checks episodic memory first (CBR), then stored rules,
    then falls back to the pipeline. New rules and episodes are saved after
    successful pipeline discoveries.
    """

    def __init__(self, semantic_memory_root: str = "semantic_memory",
                 procedural_memory_root: str = "procedural_memory",
                 episodic_memory_root: str = "episodic_memory",
                 max_steps: int = 80):
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

        Retrieval order:
          1. Episodic CBR — find similar past tasks, try their rules
          2. Flat procedural scan — try all stored rules
          3. Full SOAR pipeline — run the strategy waterfall
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

        # --- Compute structural fingerprint ---
        try:
            fingerprint = compute_fingerprint(task)
        except Exception:
            fingerprint = {"task_hex": task.task_hex}

        # --- Fast path 1: Episodic CBR (similarity-based retrieval) ---
        try:
            # Build topology for structural matching
            task_topology = None
            try:
                for pair in task.example_pairs:
                    comp = arckg_compare(pair.input_grid, pair.output_grid)
                    task_topology = extract_topology(comp.get("result", {}))
                    break
            except Exception:
                pass

            similar = find_similar_episodes(
                fingerprint, topology=task_topology,
                episodic_memory_root=self.episodic_memory_root,
                threshold=0.7, max_results=5,
            )
            for episode, sim_score in similar:
                ep_rule_type = episode.get("solved_with_rule", "")
                ep_task = episode.get("fingerprint", {}).get("task_hex", "?")
                # Find the rule in procedural memory that matches this episode's rule type + source task
                stored_rules = load_all_rules(self.procedural_memory_root)
                for entry in stored_rules:
                    rule = entry.get("rule", {})
                    if rule.get("type") == "identity":
                        continue
                    if rule.get("type") != ep_rule_type:
                        continue
                    if self._rule_matches_examples(rule, task):
                        predicted = self._apply_rule_to_tests(rule, task)
                        if predicted:
                            increment_reuse_count(entry)
                            self.last_solve_info.update({
                                "method": "episodic_cbr",
                                "rule_type": rule.get("type", "unknown"),
                                "rule_source": entry.get("source_task"),
                                "cbr_similarity": round(sim_score, 3),
                                "cbr_matched_task": ep_task,
                            })
                            self._submission_count += 1
                            return predicted
        except Exception:
            pass  # episodic retrieval is optional, fall through

        # --- Fast path 2: try all stored rules (existing flat scan) ---
        stored_rules = load_all_rules(self.procedural_memory_root)
        stored_rules_scanned = 0
        for entry in stored_rules:
            rule = entry.get("rule", {})
            if rule.get("type") == "identity":
                continue  # skip identity fallback rules
            stored_rules_scanned += 1
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
        wm.s1["focus"] = {"level": "GRID", "scope": "within_pair_examples"}

        elaborator = build_elaborator()
        proposer = build_proposer()

        result = run_cycle(
            wm, elaborator, proposer,
            max_steps=self.max_steps,
            stop_on_goal=True,
            log_wm=False,
        )

        predicted = self._extract_prediction(wm)
        self.last_wm = wm

        active_rules = wm.s1.get("active-rules")
        rule_type = "none"
        if active_rules and isinstance(active_rules, list):
            rule_type = active_rules[0].get("type", "none")

        self.last_solve_info.update({
            "method": "pipeline",
            "rule_type": rule_type,
            "steps": result["steps_taken"],
            "failure_trace": wm.s1.get("generalize-diagnostics"),
            "concepts_tried": wm.s1.get("concepts-tried-count", 0),
            "stored_rules_scanned": stored_rules_scanned,
        })

        # --- Learn: save new rule + episode if pipeline discovered one ---
        if (active_rules and rule_type != "identity"
                and rule_type != "constant_output"
                and not rule_type.startswith("composition:")):
            rule_path = save_rule_to_ltm(
                active_rules[0], task.task_hex,
                self.procedural_memory_root,
            )
            # Save episode to episodic memory with structural_key
            try:
                rule_filename = os.path.basename(rule_path) if rule_path else None
                sk = build_structural_key(
                    wm, rule_type,
                    concept_id=active_rules[0].get("concept_id"),
                )
                save_episode(
                    fingerprint, rule_type,
                    rule_id=rule_filename,
                    structural_key=sk,
                    episodic_memory_root=self.episodic_memory_root,
                )
            except Exception:
                pass  # episode saving is optional

        self._submission_count += 1
        return predicted

    # ---- helpers --------------------------------------------------------

    def _rule_matches_examples(self, rule, task) -> bool:
        """Check if a rule produces correct output for ALL example pairs."""
        # New format: concept-type rule with no concrete params — re-infer
        if rule.get("type", "").startswith("concept:") and not rule.get("params"):
            concept_id = rule.get("concept_id")
            if not concept_id:
                return False
            try:
                from procedural_memory.base_rules._concept_engine import try_single_concept
                re_inferred = try_single_concept(task, concept_id)
                if re_inferred is None:
                    return False
                for pair in task.example_pairs:
                    if pair.input_grid is None or pair.output_grid is None:
                        continue
                    predicted = self._predictor._apply_rule(re_inferred, pair.input_grid)
                    if predicted is None or predicted != pair.output_grid.raw:
                        return False
                rule["_reinferred_params"] = re_inferred.get("params", {})
                return True
            except Exception:
                return False

        # Old format or non-concept: use concrete params directly
        for pair in task.example_pairs:
            if pair.input_grid is None or pair.output_grid is None:
                continue
            predicted = self._predictor._apply_rule(rule, pair.input_grid)
            if predicted is None or predicted != pair.output_grid.raw:
                return False
        return True

    def _apply_rule_to_tests(self, rule, task) -> list:
        """Apply a rule to all test inputs. Returns list of predicted grids."""
        # Consume re-inferred params stashed by _rule_matches_examples
        if rule.get("_reinferred_params") and rule.get("type", "").startswith("concept:"):
            effective_rule = {k: v for k, v in rule.items() if k != "_reinferred_params"}
            effective_rule["params"] = rule["_reinferred_params"]
        else:
            effective_rule = rule

        grids = []
        for test_pair in task.test_pairs:
            if test_pair.input_grid is None:
                return None
            predicted = self._predictor._apply_rule(effective_rule, test_pair.input_grid)
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
