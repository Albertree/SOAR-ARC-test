"""
elaboration_rules — Elaboration rules for SOAR Production Memory.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
[SOAR MANDATORY] The Elaborate phase runs first in every cycle.
                 Elaborator applies rules repeatedly until fixed-point.
                 ElaborationRule interface (condition → derive) is SOAR protocol.

[DESIGN FREE] What derived facts to create (entire rule content).
              Names and values of derived facts.
              List of rules to register with Elaborator.
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""


class ElaborationRule:
    """
    [SOAR MANDATORY] Elaboration rule interface.
                     When condition(wm) → True, derive(wm) returns a derived fact dict.
    [DESIGN FREE] Content of condition, content of derive (defined by concrete rule classes).
    MUST NOT: Do not modify WM — only return derived fact dict.
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
        [SOAR MANDATORY] Fixed-point iteration engine — called every cycle.
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
# Concrete ElaborationRule implementations — all [DESIGN FREE]
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

    In this implementation:
      - When wm.s1['io']['input-link']['task'] exists and
      - wm.s1 does not yet have a 'current-task' slot,
        derive(wm) is interpreted as returning {"current-task": <task_dict>}.

    The actual method of attaching to WM is determined by the Elaborator.run implementation.
    (e.g., wm.active.update(derive_dict))
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
            # Defensive handling, though this should only be called when condition is True.
            return {}
        return {"current-task": task_val}

class NeedsTargetSelectionRule(ElaborationRule):
    """
    [DESIGN FREE] When comparison_agenda has unprocessed items and
                   pending_comparisons is empty,
                   derives elaborated["needs_target_selection"] = True.
    """

    def condition(self, wm) -> bool:
        raise NotImplementedError("NeedsTargetSelectionRule.condition() not implemented.")

    def derive(self, wm) -> dict:
        return {"needs_target_selection": True}


class HasPendingComparisonRule(ElaborationRule):
    """
    [DESIGN FREE] When there are items in the pending_comparisons queue,
                   derives elaborated["has_pending_comparison"] = True.
    """

    def condition(self, wm) -> bool:
        raise NotImplementedError("HasPendingComparisonRule.condition() not implemented.")

    def derive(self, wm) -> dict:
        return {"has_pending_comparison": True}


class AllComparisonsDoneRule(ElaborationRule):
    """
    [DESIGN FREE] When both agenda and pending are empty and
                   all required comparisons exist in relations,
                   derives elaborated["all_comparisons_done"] = True.
    """

    def condition(self, wm) -> bool:
        raise NotImplementedError("AllComparisonsDoneRule.condition() not implemented.")

    def derive(self, wm) -> dict:
        return {"all_comparisons_done": True}


class ReadyForPatternExtractionRule(ElaborationRule):
    """
    [DESIGN FREE] When all_comparisons_done == True AND
                   both invariants and diff_patterns are empty,
                   derives elaborated["ready_for_pattern_extraction"] = True.
    """

    def condition(self, wm) -> bool:
        raise NotImplementedError("ReadyForPatternExtractionRule.condition() not implemented.")

    def derive(self, wm) -> dict:
        return {"ready_for_pattern_extraction": True}


class ReadyForGeneralizationRule(ElaborationRule):
    """
    [DESIGN FREE] When both invariants and diff_patterns are populated,
                   derives elaborated["ready_for_generalization"] = True.
    """

    def condition(self, wm) -> bool:
        raise NotImplementedError("ReadyForGeneralizationRule.condition() not implemented.")

    def derive(self, wm) -> dict:
        return {"ready_for_generalization": True}


class ReadyForPredictionRule(ElaborationRule):
    """
    [DESIGN FREE] When active_rules is not empty and
                   there is at least one pending test subgoal,
                   derives elaborated["ready_for_prediction"] = True.
    """

    def condition(self, wm) -> bool:
        raise NotImplementedError("ReadyForPredictionRule.condition() not implemented.")

    def derive(self, wm) -> dict:
        return {"ready_for_prediction": True}


class AllOutputsFoundRule(ElaborationRule):
    """
    [DESIGN FREE] When all test subgoals are solved,
                   derives elaborated["all_outputs_found"] = True.
    """

    def condition(self, wm) -> bool:
        raise NotImplementedError("AllOutputsFoundRule.condition() not implemented.")

    def derive(self, wm) -> dict:
        return {"all_outputs_found": True}


def build_elaborator() -> Elaborator:
    """
    [DESIGN FREE] Which ElaborationRules to register.
                   Created at ActiveSoarAgent.solve() call time.
    """
    # Currently only the rule that pulls the input task into state is activated.
    rules = [
        InputTaskToStateRule("elaborate_input_task"),
        # NeedsTargetSelectionRule("needs_target_selection"),
        # HasPendingComparisonRule("has_pending_comparison"),
        # AllComparisonsDoneRule("all_comparisons_done"),
        # ReadyForPatternExtractionRule("ready_for_pattern_extraction"),
        # ReadyForGeneralizationRule("ready_for_generalization"),
        # ReadyForPredictionRule("ready_for_prediction"),
        # AllOutputsFoundRule("all_outputs_found"),
    ]
    return Elaborator(rules)
