"""
WorkingMemory — SOAR 작업 메모리.

SOAR의 4개 구성요소 중 하나.
  WM              ← 현재 문제 상태 전체 (이 파일)
  Production Memory ← elaboration_rules.py + rules.py
  Operators         ← operators.py + active_operators.py
  Cycle             ← cycle.py

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
[SOAR 강제] WM은 반드시 존재해야 한다.
            모든 내용은 (identifier, attribute, value) triplet으로 표현된다.
            S1(루트)/S2(서브스테이트) 계층 구조를 가진다.

비교 큐·relations·elaborated 등 전용 dict 슬롯과 그걸 채우는 WM 헬퍼는 두지 않는다.
지식은 triplet/연산자가 직접 추가하는 방식으로만 확장한다.
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

────────────────────────────────────────────────────────────────
[설계 메모 — Soar WM vs 본 클래스 필드]  (나중에 간추릴 때 참고)

개념적으로 Soar WM은 **WME 집합**뿐이며, wme_records(+ timetag)가 그 데이터에 해당한다.
파이썬 구현에서는 집합을 돌리기 위해 **매니저 역할**의 필드가 함께 붙는다.

• 반드시 유지 권장 (엔진/사이클에 필수에 가까움)
  - _timetag_seq : WME마다 고유·단조 증가 timetag 발급 (Soar 4요소)
  - _substate_stack : Impasse 시 서브스테이트 스택 — 규칙 평가 순서(상위→최근 하위)
  - wme_timetags : 집합 순회만으로는 느릴 수 있어, 슬롯별 최신 timetag 인덱스

• 리팩터링 시 제거·대체 검토 가능 (편의/캐시)
  - s1 : S1은 WME 그래프 안의 식별자일 뿐이나, “루트 포인터”로 두면 구현이 단순함.
         순수 그래프만 쓰면 entry point 검색으로 대체 가능.
  - task : WM 밖 캐시. 순수 Soar라면 input-link 등 그래프 탐색으로만 접근하도록 없앨 수 있음.

이 클래스는 “WM 데이터 집합” + “그 집합을 관리·사이클 구동”을 겸한다.
────────────────────────────────────────────────────────────────
"""

from __future__ import annotations

import copy
import itertools
from typing import Any

MAX_SUBSTATE_DEPTH: int = 2

# SOAR 스타일에서 기본적으로 보호하고 싶은 top-level 슬롯들
_RESERVED_TOP_KEYS = frozenset({"io"})


def _is_operator_id(key: str) -> bool:
    return bool(key) and key[0] == "O" and key[1:].isdigit()


class _TrackedS1(dict):
    """
    S1 최상위 키 대입 시 timetag를 남긴다.
    O1/O2… 연산자 노드 dict를 통째로 넣을 때는 하위 키마다 별도 기록한다.
    """

    __slots__ = ("_wm",)

    def __init__(self, wm: "WorkingMemory", *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._wm = wm

    def __setitem__(self, key: str, value: Any) -> None:
        super().__setitem__(key, value)
        self._wm._record_wme("S1", key, value)
        if isinstance(value, dict) and _is_operator_id(key):
            for sk, sv in value.items():
                self._wm._record_wme(key, sk, sv)


class WorkingMemory:
    """
    [SOAR 강제] WM 클래스는 반드시 존재해야 한다.
                S1/S2 계층과 triplet 접근 인터페이스(get/set)는 SOAR 프로토콜.
    """

    def __init__(self):
        # Soar timetag: WME 생성 순서대로 증가하는 정수 (로거에는 안 찍힘)
        self._timetag_seq = itertools.count(1)
        # 전체 이력 (디버거/print(wm.wme_records)용)
        self.wme_records: list[dict[str, Any]] = []
        # (identifier, attribute) -> 최신 timetag
        self.wme_timetags: dict[str, int] = {}

        self.s1 = _TrackedS1(self)
        self.s1["type"] = "state"
        self.s1["superstate"] = None
        self.s1["io"] = {
            "input-link": {},
            "output-link": {},
        }
        # 상태는 의미 기억/일화 기억 모듈과 연결될 수 있다.
        # 자세한 프로토콜은 아직 정의 전이므로 id만 placeholder로 둔다.
        self.s1["smem"] = {"id": "SM1"}
        self.s1["epmem"] = {"id": "E1"}

        self.task = None
        self._substate_stack: list = []

    def _record_wme(self, identifier: str, attribute: str, value: Any) -> int:
        """내부용: triplet에 대응하는 timetag 부여 (출력은 wm_logger에서 하지 않음)."""
        tt = next(self._timetag_seq)
        key = f"{identifier}^{attribute}"
        self.wme_timetags[key] = tt
        self.wme_records.append(
            {
                "timetag": tt,
                "identifier": identifier,
                "attribute": attribute,
                "value": value,
            }
        )
        return tt

    def register_wme(self, identifier: str, attribute: str, value: Any) -> int:
        """
        S1이 아닌 경로(예: input-link.task)에서 수동으로 timetag를 남길 때 사용.
        """
        return self._record_wme(identifier, attribute, value)

    @property
    def active(self) -> dict:
        return self._substate_stack[-1] if self._substate_stack else self.s1

    @property
    def depth(self) -> int:
        return len(self._substate_stack)

    def get(self, key: str):
        return self.active.get(key)

    def set(self, key: str, value):
        if key in _RESERVED_TOP_KEYS:
            raise ValueError(
                f"WorkingMemory.set: '{key}'는 직접 set하지 마세요."
            )
        self.active[key] = value

    def get_list(self, key: str) -> list:
        v = self.active.get(key)
        return v if isinstance(v, list) else []

    def push_substate(
        self,
        impasse_type: str,
        attribute: str,
        *,
        items: list[str] | None = None,
        non_numeric_items: list[str] | None = None,
    ) -> bool:
        """
        임패스 해소를 위한 하위 상태(Substate)를 생성한다.

        impasse_type:
            - "tie"
            - "no-change"
            - "conflict"
            - "constraint-failure"

        Soar 구조를 단순화해 따른다:
            (Sx ^type state
                ^impasse <type>
                ^choices <...>
                ^attribute <attribute>
                ^superstate Sy
                ^item ...              ; 선택적
                ^item-count N          ; 선택적
                ^non-numeric ...       ; tie일 때 선택적
                ^non-numeric-count M
                ^quiescence t
                ^reward-link Rk
                ^smem SMk
                ^epmem Ek
                ^svs SVk)
        """
        if len(self._substate_stack) >= MAX_SUBSTATE_DEPTH:
            return False

        depth = len(self._substate_stack) + 2  # S2부터 시작
        super_id = "S1" if depth == 2 else f"S{depth-1}"

        # impasse 종류별 ^choices 기본값
        if impasse_type == "tie":
            choices = "multiple"
        elif impasse_type == "conflict":
            choices = "multiple"
        elif impasse_type == "constraint-failure":
            choices = "constraint-failure"
        else:
            # 기본값: no-change 포함
            choices = "none"

        sub: dict[str, Any] = {
            "type": "state",
            "superstate": super_id,
            "impasse": impasse_type,
            "choices": choices,
            "attribute": attribute,
            "quiescence": True,
            # 모듈 링크: smem/epmem만 남기고 reward-link, svs는 생략한다.
            "smem": {"id": f"SM{depth}"},
            "epmem": {"id": f"E{depth}"},
        }

        if items:
            sub["item"] = list(items)
            sub["item-count"] = len(items)

        if non_numeric_items:
            sub["non-numeric"] = list(non_numeric_items)
            sub["non-numeric-count"] = len(non_numeric_items)

        self._substate_stack.append(sub)
        return True

    def pop_substate(self, result: Any = None) -> None:
        if not self._substate_stack:
            return
        self._substate_stack.pop()
