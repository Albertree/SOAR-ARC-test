"""
elaboration_rules — Elaboration rules for SOAR Production Memory.

[SOAR MANDATORY] The Elaborate phase runs first in every cycle.
                 Elaborator applies rules repeatedly until fixed-point.
                 ElaborationRule interface (condition -> derive) is SOAR protocol.

[DESIGN FREE] What derived facts to create (entire rule content).
              Names and values of derived facts.
              List of rules to register with Elaborator.

Pipeline state machine (all state lives in wm.s1, flags derived into wm.active):
  0. current-task ^ !descent-complete ^ !agenda -> needs_descent          (module A)
  1. current-task ^ descent-complete ^ !agenda  -> needs_target_selection
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


def _descent_warranted_here(wm) -> bool:
    """P1 gate for module A's descent trigger: does the *current focus level*
    warrant a descent, per the recognition vocabulary (``descent_warranted``)?

    This is the wiring RULE_FORMAT.md §4 flagged as deferred — the descent-trigger
    matchers (``descent_warranted`` → ``nothing_to_compare`` / ``needs_descend``)
    were registered as a *library* but the live trigger gated on the bare
    ``descent-complete`` flag, never consulting them. Consulting them here makes
    the descent *necessity-driven* (P1) rather than unconditional: the trigger
    descends because a value-agnostic matcher recognises the level offers nothing
    to compare (or holds an unresolvable goal), not because a flag is unset.

    At the trigger point the flow is at the top of the descent (no comparisons
    scheduled yet), so the only evidence in hand is the structural sibling census
    (``level_sibling_counts``). At the TASK level that census has one task node, so
    ``nothing_to_compare`` fires and descent is warranted — the §3 ``[TASK level]``
    step ("형제 TASK 없음 → 비교 자연 skip → descend"). Value-agnostic: the census is
    counts only, so easy000a (red) and easy000a2 (green) gate identically.

    Fail-open: when no loaded task is reachable (e.g. a minimal WM stub), the
    census cannot be built, so the structural gate in ``NeedsDescentRule`` stands
    alone and the §3 descent still begins. This is *not* a swallowed validation
    error (it builds no rule and raises nothing); it is the absence of evidence to
    refine the gate with.
    """
    task = getattr(wm, "task", None)
    if task is None:
        return True
    from agent.compare_scheduler import level_sibling_counts
    from agent import conditions

    census = level_sibling_counts(task)
    level = wm.s1.get("focus-level") or "task"
    return conditions.match(
        "descent_warranted",
        {"level_sibling_counts": census},
        {"level": level},
    )


class NeedsDescentRule(ElaborationRule):
    """Module A (HierarchicalDescentController) trigger, fires in S2.

    Fires when S1 has a current-task but the hierarchical descent has not yet
    run (no ``descent-complete`` flag) and no comparison agenda exists, *and* the
    recognition vocabulary confirms the current focus level warrants a descent
    (``_descent_warranted_here`` → ``descent_warranted``). The matcher gate makes
    the descent necessity-driven (P1): the flow descends because the level offers
    nothing to compare / holds an unresolvable goal, not merely because a flag is
    unset — closing the "registered but unconsumed by the live trigger" gap
    RULE_FORMAT.md §4 named.

    This sequences module A *before* target selection: the §3 flow descends
    TASK→PAIR→GRID to the level that can resolve the goal, and only then schedules
    the level-appropriate comparisons. Self-terminating — once ``DescendOperator``
    writes ``descent-complete`` to S1 this stops firing and
    ``NeedsTargetSelectionRule`` takes over, so the level walk runs exactly once
    (no descend↔select loop on the Slice-1 tasks, which always terminate at GRID).
    """

    def condition(self, wm) -> bool:
        if wm.depth == 0:
            return False
        s1 = wm.s1
        if not (
            bool(s1.get("current-task"))
            and not s1.get("comparison-agenda")
            and not s1.get("descent-complete")
        ):
            return False
        return _descent_warranted_here(wm)

    def derive(self, wm) -> dict:
        return {"needs_descent": True}


class NeedsTargetSelectionRule(ElaborationRule):
    """
    Fires in S2 when S1 has a current-task but no comparison-agenda yet, *and*
    module A's hierarchical descent has already run (``descent-complete``). The
    descent gate makes the §3 order explicit on the live solve: descend to the
    resolving level first, then select comparison targets there.
    """

    def condition(self, wm) -> bool:
        if wm.depth == 0:
            return False
        s1 = wm.s1
        return (
            bool(s1.get("current-task"))
            and not s1.get("comparison-agenda")
            and bool(s1.get("descent-complete"))
        )

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


def build_elaborator() -> Elaborator:
    """
    [DESIGN FREE] Which ElaborationRules to register.
                   Created at ActiveSoarAgent.solve() call time.
    """
    rules = [
        InputTaskToStateRule("elaborate_input_task"),
        NeedsDescentRule("needs_descent"),
        NeedsTargetSelectionRule("needs_target_selection"),
        HasPendingComparisonRule("has_pending_comparison"),
        ReadyForPatternExtractionRule("ready_for_pattern_extraction"),
        ReadyForGeneralizationRule("ready_for_generalization"),
        ReadyForPredictionRule("ready_for_prediction"),
        AllOutputsFoundRule("all_outputs_found"),
    ]
    return Elaborator(rules)
