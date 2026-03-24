"""
cycle — SOAR decision cycle.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
[SOAR MANDATORY] Cycle order must be Elaborate → Propose → Select → Apply.
                 Elaborate is the first phase of every cycle — cannot be skipped.
                 impasse (no candidates / failure) → substate creation — cannot be skipped.

[DESIGN FREE] max_steps value
              Subgoal content to create on impasse
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""

from __future__ import annotations

from agent.agent_common import goal_satisfied
from agent.wm_logger import print_wm_triplets
from agent.propose_wm import (
    materialize_operator_proposals,
    mark_operator_selected,
    clear_s1_operator_slots,
)
from agent.preferences import select_operator


def run_cycle(
    wm,
    elaborator,
    proposer,
    max_steps: int = 50,
    *,
    stop_on_goal: bool = True,
    log_wm: bool = True,
) -> dict:
    """
    Elaborate → Propose → Select → Apply loop.

    - S1 (depth 0): proposal, elaboration, application. If no WM change after
      abstract operator application, creates a substate (S2...) via operator no-change impasse.
    - Substate: on operator no-change impasse, ``SubstateNoChangeProgressRule`` proposes
      ``substate-progress`` → Apply writes ``^substate-resolution`` to S1, then
      substate pop + S1 operator slot cleanup.
    - Other substates with no candidates → pop + clear S1 operator slots (temporary).

    stop_on_goal: If True and S1 has a goal and goal_satisfied, terminates early.
    """
    step = 0
    while step < max_steps:
        if stop_on_goal and _s1_goal_satisfied(wm):
            break

        _elaborate(wm, elaborator)
        if log_wm:
            print_wm_triplets(wm, label="After: elaborate", step=step)

        candidates = _propose(wm, proposer)
        if log_wm:
            print_wm_triplets(wm, label="After: propose", step=step)

        selected = _select(candidates, wm)
        if log_wm:
            print_wm_triplets(wm, label="After: select", step=step)

        if selected is None:
            cont = _handle_impasse(wm, "no_candidates")
            if log_wm:
                print_wm_triplets(
                    wm, label="After: impasse(no_candidates)", step=step
                )
            if not cont:
                break
            step += 1
            continue

        apply_outcome = _apply(selected, wm)
        if log_wm:
            print_wm_triplets(
                wm,
                label=f"After: apply({selected.name})",
                step=step,
            )

        if apply_outcome == "failure":
            cont = _handle_impasse(wm, "failure")
            if log_wm:
                print_wm_triplets(wm, label="After: impasse(failure)", step=step)
            if not cont:
                break
        elif wm.depth == 0 and apply_outcome == "no_change":
            ok = wm.push_substate("no-change", "operator")
            if log_wm:
                print_wm_triplets(
                    wm, label="After: impasse(no-change)", step=step
                )
            if not ok:
                break
        elif wm.depth > 0 and apply_outcome == "changed":
            # After writing result to superstate (S1) from S2, resolve impasse: remove substate + allow S1 operator re-proposal
            wm.pop_substate()
            clear_s1_operator_slots(wm)
            if log_wm:
                print_wm_triplets(
                    wm,
                    label="After: substate resolved (result on S1)",
                    step=step,
                )

        step += 1

    return {
        "steps_taken": step,
        "goal_satisfied": bool(_s1_goal_satisfied(wm)),
    }


def _s1_goal_satisfied(wm) -> bool:
    """Checks only S1's goal even when in a substate."""
    goal = wm.s1.get("goal")
    if goal is None:
        return False
    subs = goal.get("subgoals") or {}
    if not subs:
        return True
    for _k, sg in sorted(subs.items()):
        if not isinstance(sg, dict):
            continue
        if sg.get("status") != "solved":
            return False
    return True


def _operator_id_for_name(state: dict, name: str) -> str | None:
    for k, v in state.items():
        if (
            len(k) > 1
            and k[0] == "O"
            and k[1:].isdigit()
            and isinstance(v, dict)
            and v.get("name") == name
        ):
            return k
    return None


def _elaborate(wm, elaborator) -> None:
    elaborator.run(wm)


def _propose(wm, proposer) -> list:
    candidates = proposer.propose(wm) or []
    # Soar-style: preferences are expressed only through (S1 ^operator O1 +) / (O1 ^op-preference +),
    # no separate ^proposed_ops WME is created.
    if candidates:
        materialize_operator_proposals(wm, candidates)
    return candidates


def _select(candidates: list, wm):
    sel = select_operator(candidates, wm)
    if sel is None:
        return None
    oid = _operator_id_for_name(wm.active, sel.name)
    if oid:
        wm.active["operator"] = oid
    mark_operator_selected(wm)
    return sel


def _apply(operator, wm) -> str:
    """
    Only calls operator.effect(wm). Does not write success/failure/no-change to WM.

    Return value is for cycle internal use: "failure" | "no_change" | "changed".
    No-change is determined solely by wme_records length (before and after effect).
    """
    n_before = len(wm.wme_records)
    try:
        operator.effect(wm)
    except Exception:
        return "failure"
    n_after = len(wm.wme_records)
    if n_after == n_before:
        return "no_change"
    return "changed"


def _handle_impasse(wm, trigger: str) -> bool:
    """
    True: continue cycle. False: terminate (depth limit or no candidates at top level).
    """
    if trigger == "no_candidates":
        if wm.depth > 0:
            wm.pop_substate()
            clear_s1_operator_slots(wm)
            return True
        return False

    if trigger == "failure":
        if wm.push_substate("constraint-failure", "operator"):
            return True
        return False

    return False
