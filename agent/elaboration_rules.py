"""
elaboration_rules — Elaboration rules for SOAR Production Memory.

[SOAR MANDATORY] The Elaborate phase runs first in every cycle.
                 Elaborator applies rules repeatedly until fixed-point.
                 ElaborationRule interface (condition -> derive) is SOAR protocol.

[DESIGN FREE] What derived facts to create (entire rule content).
              Names and values of derived facts.
              List of rules to register with Elaborator.

Pipeline state machine (all state lives in wm.s1, flags derived into wm.active):
  1. current-task ^ !comparison-agenda         -> needs_target_selection
  2. pending-comparisons non-empty             -> has_pending_comparison
  3. agenda ^ !pending ^ comparisons ^ !patterns -> ready_for_pattern_extraction
  4. patterns ^ !active-rules                  -> ready_for_generalization
  5. active-rules ^ !predictions               -> ready_for_prediction
  6. predictions for all test pairs            -> all_outputs_found
"""


class ElaborationRule:
    """
    [SOAR MANDATORY] Elaboration rule interface.
                     When condition(wm) -> True, derive(wm) returns a derived fact dict.
    [DESIGN FREE] Content of condition, content of derive (defined by concrete rule classes).
    MUST NOT: Do not modify WM -- only return derived fact dict.
    """

    def __init__(self, name: str):
        self.name = name

    def condition(self, wm) -> bool:
        """[DESIGN FREE] Firing condition. WM modification prohibited."""
        raise NotImplementedError(
            f"{self.__class__.__name__}.condition() must be implemented."
        )

    def derive(self, wm) -> dict:
        """
        [DESIGN FREE] Return derived fact dict. Format: {fact_name: value}
        MUST NOT: Do not return empty dict.
        """
        raise NotImplementedError(
            f"{self.__class__.__name__}.derive() must be implemented."
        )


class Elaborator:
    """
    [SOAR MANDATORY] Engine that repeatedly applies a list of ElaborationRules until fixed-point.
                     Initializes and fills wm.active["elaborated"].
    [DESIGN FREE] List of rules to register (determined in build_elaborator).
    MUST NOT: Force termination when MAX_ITERATIONS is exceeded (infinite loop prevention).
    """

    MAX_ITERATIONS: int = 20

    def __init__(self, rules: list):
        self._rules = rules

    def run(self, wm):
        """
        [SOAR MANDATORY] Fixed-point iteration engine -- called every cycle.
        """
        iterations = 0
        while iterations < self.MAX_ITERATIONS:
            iterations += 1
            changed = False

            state = wm.active

            # --- i-support style handling: if task disappears from input-link,
            #     current-task that depended on it is also automatically removed. ---
            io = state.get("io") or {}
            in_link = io.get("input-link") or {}
            if "task" not in in_link and "current-task" in state:
                del state["current-task"]
                changed = True

            # --- Apply each rule (add/update derived facts) ---
            for rule in self._rules:
                try:
                    if not rule.condition(wm):
                        continue
                    delta = rule.derive(wm)
                except NotImplementedError:
                    # Skip rules that are not yet implemented.
                    continue
                if not delta:
                    continue
                for key, value in delta.items():
                    # Do not treat as a change if the value is the same.
                    if key in state and state[key] == value:
                        continue
                    state[key] = value
                    changed = True

            if not changed:
                break


# ------------------------------------------------------------------ #
# Concrete ElaborationRule implementations -- all [DESIGN FREE]
# ------------------------------------------------------------------ #


class InputTaskToStateRule(ElaborationRule):
    """
    SOAR rule:
      sp { elaborate*input*task
        (state <s> ^io.input-link <in>)
        (<in> ^task <t>)
      -->
        (<s> ^current-task <t>)
      }
    """

    def condition(self, wm) -> bool:
        state = wm.active
        io = state.get("io") or {}
        in_link = io.get("input-link") or {}
        has_task = "task" in in_link
        has_current = "current-task" in state
        return bool(has_task and not has_current)

    def derive(self, wm) -> dict:
        state = wm.active
        io = state.get("io") or {}
        in_link = io.get("input-link") or {}
        task_val = in_link.get("task")
        if task_val is None:
            return {}
        return {"current-task": task_val}


class NeedsTargetSelectionRule(ElaborationRule):
    """
    Fires in S2 when S1 has a current-task but no comparison-agenda yet.
    This means the pipeline hasn't started -- we need to select comparison targets.
    """

    def condition(self, wm) -> bool:
        if wm.depth == 0:
            return False
        s1 = wm.s1
        return bool(s1.get("current-task")) and not s1.get("comparison-agenda")

    def derive(self, wm) -> dict:
        return {"needs_target_selection": True}


class HasPendingComparisonRule(ElaborationRule):
    """
    Fires in S2 when S1 has pending comparisons waiting to be executed.
    """

    def condition(self, wm) -> bool:
        if wm.depth == 0:
            return False
        pending = wm.s1.get("pending-comparisons")
        return isinstance(pending, list) and len(pending) > 0

    def derive(self, wm) -> dict:
        return {"has_pending_comparison": True}


class ReadyForPatternExtractionRule(ElaborationRule):
    """
    Fires in S2 when all comparisons are done (agenda set, pending empty,
    results exist) but patterns haven't been extracted yet.
    """

    def condition(self, wm) -> bool:
        if wm.depth == 0:
            return False
        s1 = wm.s1
        agenda = s1.get("comparison-agenda")
        pending = s1.get("pending-comparisons")
        comparisons = s1.get("comparisons")
        patterns = s1.get("patterns")
        return (
            isinstance(agenda, list) and len(agenda) > 0
            and isinstance(pending, list) and len(pending) == 0
            and isinstance(comparisons, dict) and len(comparisons) > 0
            and not patterns
        )

    def derive(self, wm) -> dict:
        return {"ready_for_pattern_extraction": True}


class ReadyForGeneralizationRule(ElaborationRule):
    """
    Fires in S2 when patterns have been extracted but no rules created yet.
    """

    def condition(self, wm) -> bool:
        if wm.depth == 0:
            return False
        s1 = wm.s1
        patterns = s1.get("patterns")
        active_rules = s1.get("active-rules")
        return isinstance(patterns, dict) and bool(patterns) and not active_rules

    def derive(self, wm) -> dict:
        return {"ready_for_generalization": True}


class ReadyForPredictionRule(ElaborationRule):
    """
    Fires in S2 when rules exist but predictions haven't been made yet.
    """

    def condition(self, wm) -> bool:
        if wm.depth == 0:
            return False
        s1 = wm.s1
        active_rules = s1.get("active-rules")
        if not active_rules:
            return False
        predictions = s1.get("predictions")
        if isinstance(predictions, dict) and len(predictions) > 0:
            return False
        return True

    def derive(self, wm) -> dict:
        return {"ready_for_prediction": True}


class AllOutputsFoundRule(ElaborationRule):
    """
    Fires in S2 when predictions exist for every test pair.
    """

    def condition(self, wm) -> bool:
        if wm.depth == 0:
            return False
        s1 = wm.s1
        predictions = s1.get("predictions")
        if not isinstance(predictions, dict) or not predictions:
            return False
        task = wm.task
        if task is None:
            return False
        for i in range(len(task.test_pairs)):
            if f"test_{i}" not in predictions:
                return False
        return True

    def derive(self, wm) -> dict:
        return {"all_outputs_found": True}


class ReadyForDescentRule(ElaborationRule):
    """
    Fires in S2 when GRID-level generalize produced identity with a low partial score,
    suggesting structural mismatch (not just wrong parameters).
    Double guard: focus != GRID OR descent_count >= 1 → does NOT fire.
    """

    def condition(self, wm) -> bool:
        if wm.depth == 0:
            return False
        s1 = wm.s1
        active_rules = s1.get("active-rules")
        if not active_rules or active_rules[0].get("type") != "identity":
            return False
        if (s1.get("focus") or {}).get("level") != "GRID":
            return False
        if s1.get("descent_count", 0) >= 1:
            return False
        if s1.get("g2_constant_output"):
            return False
        try:
            from procedural_memory.base_rules._concept_engine import _last_failure_diagnostics
            nm = (_last_failure_diagnostics.get("best_near_miss")
                  if _last_failure_diagnostics else None)
            best_score = nm.get("partial_score", 0.0) if nm else 0.0
            if best_score >= 0.9:
                return False
        except Exception:
            pass
        task = wm.task
        if task is None:
            return False
        return any(
            len(pair.input_grid.objects or []) > 0
            for pair in task.example_pairs
            if pair.input_grid is not None
        )

    def derive(self, wm) -> dict:
        return {"ready_for_descent": True}


def build_elaborator() -> Elaborator:
    """
    [DESIGN FREE] Which ElaborationRules to register.
                   Created at ActiveSoarAgent.solve() call time.
    """
    rules = [
        InputTaskToStateRule("elaborate_input_task"),
        NeedsTargetSelectionRule("needs_target_selection"),
        HasPendingComparisonRule("has_pending_comparison"),
        ReadyForPatternExtractionRule("ready_for_pattern_extraction"),
        ReadyForGeneralizationRule("ready_for_generalization"),
        ReadyForPredictionRule("ready_for_prediction"),
        AllOutputsFoundRule("all_outputs_found"),
        ReadyForDescentRule("ready_for_descent"),
    ]
    return Elaborator(rules)
