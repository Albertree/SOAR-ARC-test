"""
operators — SOAR Operator base interface.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
[SOAR MANDATORY] An Operator must consist of two elements: precondition + effect.
                 precondition: reads WM to determine proposal eligibility (WM modification prohibited).
                 effect:       modifies/adds to WM (cycle does not write status slots like op_status).

[DESIGN FREE] Which operators to create, names, arguments, precondition conditions, effect content.
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""


class Operator:
    """
    [SOAR MANDATORY] Operator interface. precondition + effect.
    [DESIGN FREE] Concrete operator classes (active_operators.py).
    """

    def __init__(self, name: str):
        """
        [DESIGN FREE] Operator name. Must match the string in PREFERENCE_ORDER.
        """
        self.name = name
        # Used for (O* ^op-preference ...) in the proposal phase and (S1 ^operator O* +) merging in the logger.
        # Soar: + acceptable, ! require, ~ prohibit, - reject, etc. None defaults to +.
        self.proposal_preference: str | None = None

    def precondition(self, wm) -> bool:
        """
        [SOAR MANDATORY] precondition interface — WM modification prohibited.
        [DESIGN FREE] Firing condition content. Should reference only wm.active["elaborated"].
        """
        raise NotImplementedError(
            f"{self.__class__.__name__}.precondition() must be implemented."
        )

    def effect(self, wm):
        """
        [SOAR MANDATORY] effect interface — The body of WM modification.
        [DESIGN FREE] What to add/change in WM.
        cycle: effect exception → failure impasse; no wme_records change → no-change impasse.
        """
        raise NotImplementedError(
            f"{self.__class__.__name__}.effect() must be implemented."
        )
