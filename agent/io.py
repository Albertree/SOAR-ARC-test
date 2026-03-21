"""
io — SOAR I/O 링크 관리 모듈.

SOAR 관점:
  - 아키텍처가 0th decision cycle에 S1과 ^io 뼈대를 만든다.
  - 매 execution cycle 시작 시 환경의 input function이 호출되어
    환경 상태(여기서는 ARC task)를 WM의 ^io ^input-link 아래에 WME로 추가한다.
  - output-link는 에이전트가 환경으로 내보낼 행동/결과를 기록하는 채널이다.

이 프로젝트에서는 WM을 파이썬 dict로 표현하고 있으므로,
input-link 아래에 task를 직렬화한 구조를 넣는다.
"""

from __future__ import annotations


def inject_arc_task(task, wm) -> None:
    """
    ARC task를 wm.s1['io']['input-link'] 아래에 주입한다.

    주입 위치(개념):
      (S1 ^io I1)
      (I1 ^input-link I2)
      (I2 ^task T1 ...)

    구현에서는 input-link dict에 task 요약/격자 내용을 넣는다.
    """
    io = wm.s1.get("io")
    if not isinstance(io, dict) or "input-link" not in io:
        raise ValueError("WM에 io/input-link 구조가 없습니다.")

    in_link = io["input-link"]
    # SOAR 스타일: input-link에는 우선 task를 가리키는 심볼만 올린다.
    # 세부 example/test 구조는 이후 production/elaboration 단계에서
    # current-task를 따라가거나 별도 input function으로 확장한다.
    in_link["task"] = task.task_hex
    wm.register_wme("input-link", "task", task.task_hex)


def clear_input_link(wm) -> None:
    """^input-link 아래의 내용을 비운다 (다음 execution cycle 입력 갱신용)."""
    io = wm.s1.get("io")
    if not isinstance(io, dict) or "input-link" not in io:
        raise ValueError("WM에 io/input-link 구조가 없습니다.")
    io["input-link"].clear()


def clear_output_link(wm) -> None:
    """^output-link 아래의 내용을 비운다 (환경에 반영 후 초기화)."""
    io = wm.s1.get("io")
    if not isinstance(io, dict) or "output-link" not in io:
        raise ValueError("WM에 io/output-link 구조가 없습니다.")
    io["output-link"].clear()

