"""
propose_wm — Propose 단계 이후, 후보 오퍼레이터를 WM에 올리는 헬퍼.

역할
----
- ``rules.Proposer.propose(wm)`` 는 **WM을 바꾸지 않고** Operator 인스턴스
  리스트만 돌려준다.
- 이 모듈은 그 리스트를 받아 **현재 활성 상태(``wm.active``)** 에 실제 WME에 대응하는 dict 구조로 써 넣는다.
  (S1일 때는 최상위, 서브스테이트일 때는 S2 등.)

저장 형태 (내부)
----------------
- ``S1["operator"] = "O1"``  → (S1 ^operator O1)
- ``S1["O1"] = { "name": "solve-task", "task-id": <hex>, "op-preference": "+" }``
  → (O1 ^name …) (O1 ^task-id …) (O1 ^op-preference +)

로그 출력 (wm_logger)
---------------------
- ``^op-preference`` 는 O1 블록에 따로 안 찍고,
- S1의 ``^operator`` 줄에 붙여 Soar 디버그처럼
  ``(S1 ^operator O1 +)`` 로 합쳐서 보여준다.
- 선택(Select) 직후: 제안 ``(S1 ^operator O1 +)`` 는 **유지**되고, Soar처럼
  공식 적용용 WME ``(S1 ^operator O1)`` (+ 없음)가 **추가**된다
  (내부 키 ``operator-application`` → 로거에서 ``^operator`` 로 표시).
- 이후 Application으로 상태가 바뀌어 제안 규칙이 깨지면 ``+`` 줄은 사라진다.
"""

from __future__ import annotations


def _next_global_operator_id(wm) -> str:
    """S1 + 모든 서브스테이트에서 O1, O2, … 중 다음 빈 번호."""
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
    후보 오퍼레이터를 **wm.active** 에 기록한다.
    이미 활성 상태에 ^operator 가 있으면 아무 것도 하지 않는다.
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
    """Application 등으로 제안이 철회될 때 O*의 op-preference 제거용 (선택 시에는 호출하지 않음)."""
    state = wm.s1
    op_id = state.get("operator")
    if not op_id or not isinstance(state.get(op_id), dict):
        return
    node = state[op_id]
    if "op-preference" in node:
        del node["op-preference"]


def clear_s1_operator_slots(wm) -> None:
    """
    S1에서 제안/선택/적용용 오퍼레이터 WME를 제거한다.
    상위 사이클을 다시 시작하거나 서브스테이트를 비운 뒤 S1로 돌아올 때 사용.
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
    Select 직후: **활성 상태**에 공식 오퍼레이터 증강 (Soar: + 없는 ^operator O1 WME 추가).
    제안용 ^operator O1 + 는 그대로 둔다.
    """
    state = wm.active
    op_id = state.get("operator")
    if not op_id:
        return
    state["operator-application"] = op_id
