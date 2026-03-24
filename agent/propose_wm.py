"""
propose_wm — Helper that writes candidate operators to WM after the Propose phase.

Role
----
- ``rules.Proposer.propose(wm)`` returns only a list of Operator instances
  **without modifying WM**.
- This module takes that list and writes it as a dict structure corresponding to
  actual WMEs into the **currently active state (``wm.active``)**
  (top-level when S1, S2, etc. for substates).

Storage format (internal)
-------------------------
- ``S1["operator"] = "O1"``  → (S1 ^operator O1)
- ``S1["O1"] = { "name": "solve-task", "task-id": <hex>, "op-preference": "+" }``
  → (O1 ^name ...) (O1 ^task-id ...) (O1 ^op-preference +)

Log output (wm_logger)
----------------------
- ``^op-preference`` is not printed separately in the O1 block,
- Instead it is merged into the S1 ``^operator`` line like Soar debug:
  ``(S1 ^operator O1 +)``
- After Select: the proposal ``(S1 ^operator O1 +)`` is **retained**, and like Soar,
  an official application WME ``(S1 ^operator O1)`` (without +) is **added**
  (internal key ``operator-application`` → displayed as ``^operator`` in the logger).
- When the state changes due to Application and the proposal rule breaks, the ``+`` line disappears.
"""

from __future__ import annotations


def _next_global_operator_id(wm) -> str:
    """Next available number among O1, O2, ... across S1 + all substates."""
    used: set[int] = set()

    def scan(d: dict) -> None:
        for k in d:
            if len(k) > 1 and k[0] == "O" and k[1:].isdigit():
                used.add(int(k[1:]))

    scan(wm.s1)
    for sub in wm._substate_stack:
        scan(sub)
    n = 1
    while n in used:
        n += 1
    return f"O{n}"


def materialize_operator_proposals(wm, candidates: list) -> None:
    """
    Records candidate operators in **wm.active**.
    Does nothing if ^operator already exists in the active state.
    """
    state = wm.active
    if not candidates or "operator" in state:
        return

    first_id = None
    for op in candidates:
        op_id = _next_global_operator_id(wm)
        if first_id is None:
            first_id = op_id
        pref = getattr(op, "proposal_preference", None)
        if pref is None:
            pref = "+"
        node: dict = {
            "name": op.name,
            "op-preference": pref,
        }
        if op.name == "solve-task" and state.get("current-task") is not None:
            node["task-id"] = state["current-task"]
        state[op_id] = node

    state["operator"] = first_id


def clear_operator_proposal_preferences(wm) -> None:
    """Removes O*'s op-preference when a proposal is withdrawn due to Application, etc. (not called during selection)."""
    state = wm.s1
    op_id = state.get("operator")
    if not op_id or not isinstance(state.get(op_id), dict):
        return
    node = state[op_id]
    if "op-preference" in node:
        del node["op-preference"]


def clear_s1_operator_slots(wm) -> None:
    """
    Removes proposal/selection/application operator WMEs from S1.
    Used when restarting the top-level cycle or returning to S1 after clearing a substate.
    """
    state = wm.s1
    for k in (
        "operator",
        "operator-application",
    ):
        state.pop(k, None)
    for k in list(state.keys()):
        if len(k) > 1 and k[0] == "O" and k[1:].isdigit():
            del state[k]


def mark_operator_selected(wm) -> None:
    """
    After Select: adds official operator augmentation to the **active state** (Soar: ^operator O1 WME without +).
    The proposal ^operator O1 + is kept as-is.
    """
    state = wm.active
    op_id = state.get("operator")
    if not op_id:
        return
    state["operator-application"] = op_id
