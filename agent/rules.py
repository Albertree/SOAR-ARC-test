"""
rules -- Propose rules for SOAR Production Memory.

[SOAR MANDATORY] ProductionRule interface (condition + propose).
                 Proposer is the engine that iterates all rules to collect candidates.

[DESIGN FREE] Which operator to propose for which WM state (entire rule content).

Pipeline rules (all fire at depth > 0, in S2):
  SelectTargetRule      -> needs_target_selection flag
  CompareRule           -> has_pending_comparison flag
  ExtractPatternRule    -> ready_for_pattern_extraction flag
  GeneralizeRule        -> ready_for_generalization flag
  PredictRule           -> ready_for_prediction flag
  SubmitRule            -> all_outputs_found flag
"""

from agent.active_operators import (
    SolveTaskOperator,
    SelectTargetOperator,
    CompareOperator,
    ExtractPatternOperator,
    GeneralizeOperator,
    PredictOperator,
    SubmitOperator,
    VerifyOperator,
)


class ProductionRule:
    """
    [SOAR MANDATORY] Production Rule interface. condition + propose.
    [DESIGN FREE] condition content, operator returned by propose.
    MUST NOT: Do not modify WM in condition.
              Do not directly compute anything other than elaborated in condition.
              Do not execute operator in propose.
    """

    def __init__(self, name: str):
        self.name = name

    def condition(self, wm) -> bool:
        """[DESIGN FREE] Determine firing condition by reading only elaborated facts."""
        raise NotImplementedError(
            f"{self.__class__.__name__}.condition() must be implemented."
        )

    def propose(self, wm) -> object:
        """[DESIGN FREE] Return an Operator instance when condition is met. Must not return None."""
        raise NotImplementedError(
            f"{self.__class__.__name__}.propose() must be implemented."
        )


# ── Concrete ProductionRule implementations -- all [DESIGN FREE] ─────────


class SolveTaskRule(ProductionRule):
    """
    Proposes solve-task when S1 has ^current-task and no ^operator yet.
    Only fires at depth 0 (root state).
    """

    def __init__(self):
        super().__init__("rule_solve_task")

    def condition(self, wm) -> bool:
        if wm.depth > 0:
            return False
        state = wm.s1
        return bool(state.get("current-task")) and "operator" not in state

    def propose(self, wm):
        return SolveTaskOperator()


class SelectTargetRule(ProductionRule):
    """Proposes select_target when needs_target_selection is derived in S2."""

    def __init__(self):
        super().__init__("rule_select_target")

    def condition(self, wm) -> bool:
        if wm.depth == 0:
            return False
        return wm.active.get("needs_target_selection") is True

    def propose(self, wm):
        return SelectTargetOperator()


class CompareRule(ProductionRule):
    """Proposes compare when has_pending_comparison is derived in S2."""

    def __init__(self):
        super().__init__("rule_compare")

    def condition(self, wm) -> bool:
        if wm.depth == 0:
            return False
        return wm.active.get("has_pending_comparison") is True

    def propose(self, wm):
        return CompareOperator()


class ExtractPatternRule(ProductionRule):
    """Proposes extract_pattern when ready_for_pattern_extraction is derived in S2."""

    def __init__(self):
        super().__init__("rule_extract_pattern")

    def condition(self, wm) -> bool:
        if wm.depth == 0:
            return False
        return wm.active.get("ready_for_pattern_extraction") is True

    def propose(self, wm):
        return ExtractPatternOperator()


class GeneralizeRule(ProductionRule):
    """Proposes generalize when ready_for_generalization is derived in S2."""

    def __init__(self):
        super().__init__("rule_generalize")

    def condition(self, wm) -> bool:
        if wm.depth == 0:
            return False
        return wm.active.get("ready_for_generalization") is True

    def propose(self, wm):
        return GeneralizeOperator()


class PredictRule(ProductionRule):
    """Proposes predict when ready_for_prediction is derived in S2."""

    def __init__(self):
        super().__init__("rule_predict")

    def condition(self, wm) -> bool:
        if wm.depth == 0:
            return False
        return wm.active.get("ready_for_prediction") is True

    def propose(self, wm):
        return PredictOperator()


class SubmitRule(ProductionRule):
    """Proposes submit when all_outputs_found is derived in S2."""

    def __init__(self):
        super().__init__("rule_submit")

    def condition(self, wm) -> bool:
        if wm.depth == 0:
            return False
        return wm.active.get("all_outputs_found") is True

    def propose(self, wm):
        return SubmitOperator()


class Proposer:
    """
    [SOAR MANDATORY] Engine that iterates registered ProductionRules to collect candidates.
    [DESIGN FREE] List of rules to register (determined in build_proposer).
    MUST NOT: Do not perform selection (select) or application (apply).
    """

    def __init__(self, rules: list):
        self._rules = rules

    def propose(self, wm) -> list:
        """List of operator instances from fired rules. Rules with NotImplementedError are skipped."""
        candidates: list = []
        for rule in self._rules:
            try:
                if not rule.condition(wm):
                    continue
                op = rule.propose(wm)
            except NotImplementedError:
                continue
            if op is not None:
                candidates.append(op)
        return candidates


def build_proposer() -> Proposer:
    """[DESIGN FREE] Which ProductionRules to register. Created at ActiveSoarAgent.solve() time."""
    rules = [
        SolveTaskRule(),
        SelectTargetRule(),
        CompareRule(),
        ExtractPatternRule(),
        GeneralizeRule(),
        PredictRule(),
        SubmitRule(),
    ]
    return Proposer(rules)
