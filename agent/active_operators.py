"""
active_operators — SOAR Operator implementations.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
[SOAR MANDATORY] Each operator follows the precondition + effect interface.
                 effect updates WM. cycle determines success/failure/no-change by exception/wme changes.

[DESIGN FREE] Which operators to have, names, precondition conditions, effect content.
              Compare function (compare_fn) and generalize function (generalize_fn) can be externally injected.

The operators in this module are designed to correspond to the following six cognitive-level operations.

    1. compare  (target_a, target_b, level)
    2. collect  (scope, relation_type)
    3. generalize(targets)
    4. descend  (target, from_level, to_level)
    5. predict  (test_input, rule_ref)
    6. verify   (predicted_output, constraints)

The mapping between concrete classes is as follows.

    - CompareOperator         → compare
    - ExtractPatternOperator  → collect
    - GeneralizeOperator      → generalize
    - DescendOperator         → descend
    - PredictOperator         → predict
    - SubmitOperator/VerifyOperator → verify

That is, while maintaining the SOAR-style Operator interface,
the high-level operator repertoire from the user's perspective is directly reflected.
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""

from agent.operators import Operator


class SolveTaskOperator(Operator):
    """
    [DESIGN FREE] High-level operator for solving the top-level ARC task.

    INTENT:
        - When (S1 ^current-task <hex>) exists, organizes sub-operators such as
          compare/collect/generalize/descend to solve the task.
        - At the current stage, only secures the interface (name, position) without concrete logic.

    Future:
        - precondition: When current-task exists in S1 and goal is not yet complete.
        - effect: Performs part of the solve-task pipeline during one decision cycle.
    """

    def __init__(self):
        super().__init__("solve-task")
        self.proposal_preference = "+"

    def precondition(self, wm) -> bool:
        """[DESIGN FREE] To be extended later to check S1^current-task, goal state, etc."""
        raise NotImplementedError("SolveTaskOperator.precondition() not implemented.")

    def effect(self, wm):
        """Abstract operator: intentionally no WM change.

        From the Soar perspective, solve-task only presents a high-level goal,
        and actual state changes are performed by concrete operators in sub-substates (S2...).
        Therefore, no WM modification is done here.
        """
        return


class SubstateProgressOperator(Operator):
    """
    [DESIGN FREE] Minimal result to resolve operator no-change impasse in a substate.

    Adds a short summary WME to the superstate S1, so that subsequent cycles
    reflect the change in the superstate WM. (Placeholder before full i-support retract.)
    """

    def __init__(self):
        super().__init__("substate-progress")
        self.proposal_preference = "+"

    def precondition(self, wm) -> bool:
        raise NotImplementedError(
            "SubstateProgressOperator.precondition() not implemented."
        )

    def effect(self, wm):
        attr = wm.active.get("attribute")
        wm.s1["substate-resolution"] = f"handled-no-change:{attr}"


class SelectTargetOperator(Operator):
    """
    [DESIGN FREE] The existence, precondition, and effect of this operator are all design choices.
    INTENT: (Not implemented) After selecting comparison targets, reflects pending comparison items in WM.
            Does not use dedicated dict/helpers for agenda/pending.
            Does not know the concrete comparison target types.
    MUST NOT: Do not perform the comparison itself — only queue movement.
              Do not directly reference wm.task.
    precondition: elaborated["needs_target_selection"] == True
    """

    def __init__(self):
        super().__init__("select_target")

    def precondition(self, wm) -> bool:
        """[DESIGN FREE]"""
        raise NotImplementedError("SelectTargetOperator.precondition() not implemented.")

    def effect(self, wm):
        """
        [DESIGN FREE]
        1. Select comparison targets
        2. Reflect pending comparison facts in WM (triplet)
        3. ...
        4. op_status = "success" or "failure"
        """
        raise NotImplementedError("SelectTargetOperator.effect() not implemented.")


class CompareOperator(Operator):
    """
    [DESIGN FREE] The existence, precondition, and effect of this operator are all design choices.
    INTENT: Performs one pending comparison and adds the result to WM as a triplet.
            Comparison function uses external injection (compare_fn) or default.
            CompareOperator does not know what the items are.
    MUST NOT: Do not process multiple items at once from the queue — 1 call = 1 comparison.
              Do not hardcode a specific comparison library in the class.
    precondition: elaborated["has_pending_comparison"] == True
    """

    def __init__(self, compare_fn=None):
        """
        [DESIGN FREE] compare_fn: (node_a, node_b, context) → result.
                       None uses the default comparison function.
        """
        super().__init__("compare")
        self._compare_fn = compare_fn

    def precondition(self, wm) -> bool:
        """[DESIGN FREE]"""
        raise NotImplementedError("CompareOperator.precondition() not implemented.")

    def effect(self, wm):
        """
        [DESIGN FREE]
        1. Obtain pending comparison item
        2. Call self._compare_fn(node_a, node_b, context)
        3. Reflect comparison result in WM (triplet)
        4. op_status = "success" or "failure"
        """
        raise NotImplementedError("CompareOperator.effect() not implemented.")


class ExtractPatternOperator(Operator):
    """
    [DESIGN FREE] The existence, precondition, and effect of this operator are all design choices.
    INTENT: Organizes COMM/DIFF patterns from comparison results into WM triplets.
            On failure, reflects a goal for deeper analysis in WM.
    MUST NOT: Do not implement COMM/DIFF determination logic here — only read the result's type field.
    precondition: elaborated["ready_for_pattern_extraction"] == True
    """

    def __init__(self):
        super().__init__("extract_pattern")

    def precondition(self, wm) -> bool:
        """[DESIGN FREE]"""
        raise NotImplementedError("ExtractPatternOperator.precondition() not implemented.")

    def effect(self, wm):
        """
        [DESIGN FREE]
        Serves the role corresponding to collect(scope, relation_type)
        in the compare/collect/generalize pipeline.

        1. Iterate comparison results
        2. Record COMM/DIFF as WM triplets
        4. op_status = "success" or "failure"
        """
        raise NotImplementedError("ExtractPatternOperator.effect() not implemented.")


class DescendOperator(Operator):
    """
    [DESIGN FREE] The existence, precondition, and effect of this operator are all design choices.
    INTENT: When an impasse occurs at a higher level such as GRID/OBJECT/PIXEL analysis,
            implements descend(target, from_level, to_level) by
            pulling lower-level nodes/relations into WM to enable further comparisons.

    This operation is implemented in the SOAR perspective as substate creation or
    comparison_agenda extension for impasse resolution.

    Example conceptual flow:
        - from_level analysis is insufficient → elaborated["needs_descend"] = True
        - DescendOperator.effect:
            1) wm.push_substate(...) or
            2) Reflect more granular comparison tasks in WM

    precondition: elaborated["needs_descend"] == True (design choice)
    """

    def __init__(self):
        super().__init__("descend")

    def precondition(self, wm) -> bool:
        """[DESIGN FREE]"""
        raise NotImplementedError("DescendOperator.precondition() not implemented.")

    def effect(self, wm):
        """
        [DESIGN FREE]
        1. Read current focus/impasse information to interpret from_level, to_level
        2. Add lower-level comparison tasks for target pair/objects to the agenda or
           call wm.push_substate(...) to open a subgoal if needed.
        3. op_status = "success" or "failure"
        """
        raise NotImplementedError("DescendOperator.effect() not implemented.")


class GeneralizeOperator(Operator):
    """
    [DESIGN FREE] The existence, precondition, and effect of this operator are all design choices.
    INTENT: Passes invariant/difference patterns collected in WM to a generalization function
            to generate abstract rules and add them to wm.active_rules.
            Generalization function and LTM save function use external injection or defaults.
    MUST NOT: Do not hardcode a specific generalization module in the class.
    precondition: elaborated["ready_for_generalization"] == True
    """

    def __init__(self, generalize_fn=None, save_fn=None):
        """
        [DESIGN FREE] generalize_fn: (invariants, diff_patterns) → rule dict.
                       save_fn: rule dict → LTM ref str.
                       None uses the default implementation.
        """
        super().__init__("generalize")
        self._generalize_fn = generalize_fn
        self._save_fn = save_fn

    def precondition(self, wm) -> bool:
        """[DESIGN FREE]"""
        raise NotImplementedError("GeneralizeOperator.precondition() not implemented.")

    def effect(self, wm):
        """
        [DESIGN FREE]
        1. self._generalize_fn(invariant/difference information)
        2. self._save_fn(rule) → LTM ref path
        3. Add {"ref": path, "confidence": ...} to wm.active_rules
        4. op_status = "success" or "failure"
        """
        raise NotImplementedError("GeneralizeOperator.effect() not implemented.")


class PredictOperator(Operator):
    """
    [DESIGN FREE] The existence, precondition, and effect of this operator are all design choices.
    INTENT: Applies the highest confidence rule from wm.active_rules to a pending test subgoal
            to predict output and update goal.subgoals and found.
    MUST NOT: Do not try multiple rules in parallel — single deterministic prediction.
    precondition: elaborated["ready_for_prediction"] == True
    """

    def __init__(self):
        super().__init__("predict")

    def precondition(self, wm) -> bool:
        """[DESIGN FREE]"""
        raise NotImplementedError("PredictOperator.precondition() not implemented.")

    def effect(self, wm):
        """
        [DESIGN FREE]
        1. Select one pending test subgoal
        2. Select the highest confidence rule from wm.active_rules
        3. Apply rule to test input → derive output
        4. Mark the test subgoal as solved + record in found
        5. op_status = "success" or "failure"
        """
        raise NotImplementedError("PredictOperator.effect() not implemented.")


class SubmitOperator(Operator):
    """
    [DESIGN FREE] The existence and precondition of this operator.
    [SOAR MANDATORY] There must be a final step that satisfies the goal_satisfied condition.
    INTENT: Sets op_status = "success" when elaborated["all_outputs_found"] == True.
    MUST NOT: Do not perform actual scoring — that is ARCEnvironment's responsibility.
    precondition: elaborated["all_outputs_found"] == True
    """

    def __init__(self):
        super().__init__("submit")

    def precondition(self, wm) -> bool:
        """[DESIGN FREE]"""
        raise NotImplementedError("SubmitOperator.precondition() not implemented.")

    def effect(self, wm):
        """
        [DESIGN FREE]
        Corresponds to the verify(predicted_output, constraints) step.
        When all test subgoals are resolved (elaborated["all_outputs_found"])
        and internal constraints are deemed satisfied,
        sets op_status = "success" to satisfy goal_satisfied.
        """
        raise NotImplementedError("SubmitOperator.effect() not implemented.")


class VerifyOperator(SubmitOperator):
    """
    [DESIGN FREE] Alias operator for the verify operation.

    INTENT: Implements verify(predicted_output, constraints) at the cognitive level
            using the same mechanism as SubmitOperator at the SOAR operator level,
            while expressing the pipeline more explicitly through the name difference.

    Implementation-wise, inherits SubmitOperator and uses the same precondition/effect.
    """

    def __init__(self):
        super().__init__()
        # Reset name to "verify" to allow distinction in PREFERENCE_ORDER, etc.
        self.name = "verify"
