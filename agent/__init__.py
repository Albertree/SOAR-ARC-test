"""
agent — SOAR 인지 아키텍처 패키지.

Public interface:
    ActiveSoarAgent   — 메인 에이전트 (유일한 solver, solve 진입점)
    WorkingMemory     — S1/S2 상태, 목표/연산자/지식/결과 영역
    run_cycle         — elaborate → propose → select → apply 결정 사이클
    Elaborator        — fixed-point 파생 사실 계산
    build_elaborator  — 표준 ElaborationRule 집합으로 Elaborator 생성
    build_proposer    — 표준 ProductionRule 집합으로 Proposer 생성 (태스크 파라미터 불필요)
    print_wm_triplets — WM 전체 상태를 SOAR triplet 형식으로 stdout 출력
"""

from agent.active_agent import ActiveSoarAgent
from agent.wm import WorkingMemory
from agent.cycle import run_cycle
from agent.elaboration_rules import Elaborator, build_elaborator
from agent.rules import Proposer, build_proposer
from agent.wm_logger import print_wm_triplets

__all__ = [
    "ActiveSoarAgent",
    "WorkingMemory",
    "run_cycle",
    "Elaborator",
    "build_elaborator",
    "Proposer",
    "build_proposer",
    "print_wm_triplets",
]
