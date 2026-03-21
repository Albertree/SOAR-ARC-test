"""
cycle — SOAR 결정 사이클.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
[SOAR 강제] 사이클 순서는 반드시 Elaborate → Propose → Select → Apply.
            Elaborate는 매 사이클 첫 단계 — 생략 불가.
            impasse(후보 없음 / failure) → substate 생성 — 생략 불가.

[설계 자유] max_steps 값
            impasse 시 생성할 subgoal 내용
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
    Elaborate → Propose → Select → Apply 루프.

    - S1(깊이 0): 제안·구체화·적용. 추상 오퍼레이터 적용 후 WM 변화가 없으면
      operator no-change 임패스로 서브스테이트(S2…) 생성.
    - 서브스테이트: operator no-change 임패스 시 ``SubstateNoChangeProgressRule`` 이
      ``substate-progress`` 를 제안 → Apply 로 S1에 ``^substate-resolution`` 기록 후
      substate pop + S1 오퍼레이터 슬롯 정리.
    - 그 외 서브스테이트에서 후보 없음 → pop + S1 오퍼 슬롯 비우기 (임시).

    stop_on_goal: True이고 S1에 goal이 있으며 goal_satisfied이면 조기 종료.
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
            # S2에서 상위(S1)에 result를 쓴 뒤 임패스 해소: substate 제거 + S1 오퍼 재제안 가능
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
    """서브스테이트에 있어도 S1의 goal만 본다."""
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
    # Soar-style: preferences는 (S1 ^operator O1 +) / (O1 ^op-preference +)만 통해 표현하고,
    # 별도의 ^proposed_ops WME는 만들지 않는다.
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
    operator.effect(wm)만 호출한다. WM에는 성공/실패/무변화를 쓰지 않는다.

    반환값은 사이클 내부용: \"failure\" | \"no_change\" | \"changed\".
    무변화 판단은 wme_records 길이( effect 전후 )로만 한다.
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
    True: 사이클 계속. False: 종료(깊이 한계 또는 최상위에서 후보 없음).
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
