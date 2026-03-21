"""
operators — SOAR Operator 기본 인터페이스.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
[SOAR 강제] Operator는 반드시 precondition + effect 두 요소로 구성된다.
            precondition: WM을 읽어 제안 가능 여부 판단 (WM 수정 금지).
            effect:       WM을 변경/추가한다 (cycle은 op_status 등 상태 슬롯을 쓰지 않음).

[설계 자유] 어떤 operator를 만들지, 이름, 인자, precondition 조건, effect 내용.
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""


class Operator:
    """
    [SOAR 강제] Operator 인터페이스. precondition + effect.
    [설계 자유] 구체 operator 클래스 (active_operators.py).
    """

    def __init__(self, name: str):
        """
        [설계 자유] operator 이름. PREFERENCE_ORDER의 문자열과 일치해야 한다.
        """
        self.name = name
        # 제안 단계에서 WM의 (O* ^op-preference …) 및 로거의 (S1 ^operator O* +) 병합에 쓴다.
        # Soar: + acceptable, ! require, ~ prohibit, - reject 등. None이면 기본 +.
        self.proposal_preference: str | None = None

    def precondition(self, wm) -> bool:
        """
        [SOAR 강제] precondition 인터페이스 — WM 수정 금지.
        [설계 자유] 발화 조건 내용. wm.active["elaborated"]만 참조할 것.
        """
        raise NotImplementedError(
            f"{self.__class__.__name__}.precondition() must be implemented."
        )

    def effect(self, wm):
        """
        [SOAR 강제] effect 인터페이스 — WM 변경의 본체.
        [설계 자유] WM에 무엇을 추가/변경할지.
        cycle: effect 예외 → failure 임패스; wme_records 변화 없음 → no-change 임패스.
        """
        raise NotImplementedError(
            f"{self.__class__.__name__}.effect() must be implemented."
        )
