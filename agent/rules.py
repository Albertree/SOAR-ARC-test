"""
rules — Propose rules for SOAR Production Memory.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
[SOAR MANDATORY] ProductionRule interface (condition + propose).
                 Proposer is the engine that iterates all rules to collect candidates.

[DESIGN FREE] Which operator to propose for which WM state (entire rule content).
              Conditions in condition, operator returned by propose.
              List of rules to register with Proposer.
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""

from agent.active_operators import (
    SolveTaskOperator,
    SubstateProgressOperator,
    SelectTargetOperator,
    CompareOperator,
    ExtractPatternOperator,
    GeneralizeOperator,
    DescendOperator,
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


# ── Concrete ProductionRule implementations — all [DESIGN FREE] ─────────


class SolveTaskRule(ProductionRule):
    """
    Proposes solve-task when S1 has ^current-task and no ^operator yet.
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


class SubstateNoChangeProgressRule(ProductionRule):
    """
    After an operator no-change impasse opens in S2+, proposes a minimal concrete
    operator that can write a result to the superstate (S1).
    (To be replaced/branched with compare/collect in the future)
    """

    def __init__(self):
        super().__init__("rule_substate_no_change_progress")

    def condition(self, wm) -> bool:
        if wm.depth == 0:
            return False
        a = wm.active
        return (
            a.get("impasse") == "no-change"
            and a.get("attribute") == "operator"
            and "operator" not in a
        )

    def propose(self, wm):
        return SubstateProgressOperator()


class SelectTargetRule(ProductionRule):
    """[DESIGN FREE] elaborated["needs_target_selection"] → SelectTargetOperator."""

    def __init__(self):
        super().__init__("rule_select_target")

    def condition(self, wm) -> bool:
        raise NotImplementedError("SelectTargetRule.condition() not implemented.")

    def propose(self, wm):
        return SelectTargetOperator()


class CompareRule(ProductionRule):
    """[DESIGN FREE] elaborated["has_pending_comparison"] → CompareOperator."""

    def __init__(self):
        super().__init__("rule_compare")

    def condition(self, wm) -> bool:
        raise NotImplementedError("CompareRule.condition() not implemented.")

    def propose(self, wm):
        return CompareOperator()


class ExtractPatternRule(ProductionRule):
    """[DESIGN FREE] elaborated["ready_for_pattern_extraction"] → ExtractPatternOperator."""

    def __init__(self):
        super().__init__("rule_extract_pattern")

    def condition(self, wm) -> bool:
        raise NotImplementedError("ExtractPatternRule.condition() not implemented.")

    def propose(self, wm):
        return ExtractPatternOperator()


class GeneralizeRule(ProductionRule):
    """[DESIGN FREE] elaborated["ready_for_generalization"] → GeneralizeOperator."""

    def __init__(self):
        super().__init__("rule_generalize")

    def condition(self, wm) -> bool:
        raise NotImplementedError("GeneralizeRule.condition() not implemented.")

    def propose(self, wm):
        return GeneralizeOperator()


class PredictRule(ProductionRule):
    """[DESIGN FREE] elaborated["ready_for_prediction"] → PredictOperator."""

    def __init__(self):
        super().__init__("rule_predict")

    def condition(self, wm) -> bool:
        raise NotImplementedError("PredictRule.condition() not implemented.")

    def propose(self, wm):
        return PredictOperator()


class SubmitRule(ProductionRule):
    """[DESIGN FREE] elaborated["all_outputs_found"] → SubmitOperator."""

    def __init__(self):
        super().__init__("rule_submit")

    def condition(self, wm) -> bool:
        raise NotImplementedError("SubmitRule.condition() not implemented.")

    def propose(self, wm):
        return SubmitOperator()


class VerifyRule(ProductionRule):
    """
    [DESIGN FREE] ProductionRule for the verify operation.

    Corresponds to the cognitive-level verify(predicted_output, constraints),
    and proposes VerifyOperator when high-level constraint evaluation such as
    elaborated["all_outputs_found"] is complete.

    In the default design, it uses the same firing condition as SubmitRule,
    but the constraint check can be further refined later if needed.
    """

    def __init__(self):
        super().__init__("rule_verify")

    def condition(self, wm) -> bool:
        """[DESIGN FREE] Currently assumes the same flag as SubmitRule."""
        raise NotImplementedError("VerifyRule.condition() not implemented.")

    def propose(self, wm):
        return VerifyOperator()


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
        SubstateNoChangeProgressRule(),
        # compare: SelectTarget + Compare
        SelectTargetRule(),
        CompareRule(),
        # collect
        ExtractPatternRule(),
        # generalize
        GeneralizeRule(),
        # descend (DescendRule to be added after elaboration design is complete)
        # predict
        PredictRule(),
        # verify
        SubmitRule(),
        VerifyRule(),
    ]
    return Proposer(rules)
