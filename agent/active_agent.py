"""
ActiveSoarAgent — 메인 SOAR 에이전트.
ARCEnvironment의 agent.solve(task) 인터페이스를 구현한다.
"""

from agent.wm import WorkingMemory
from agent.cycle import run_cycle
from agent.elaboration_rules import build_elaborator
from agent.rules import build_proposer
from agent.memory import load_rules_from_ltm, chunk_from_substate, save_rule_to_ltm
from agent.agent_common import build_wm_from_task, goal_satisfied, answers_from_wm
from agent.wm_logger import reset_wm_snapshot


class ActiveSoarAgent:
    """
    [SOAR 강제] SOAR 사이클을 실행하는 에이전트 래퍼가 있어야 한다.
    [설계 자유] solve() 호출 횟수 제한(can_retry), LTM 로드 방식,
               chunking 콜백 연결 방식.
    MUST NOT: ARCSolver 등 별도 solver를 fallback으로 사용하지 마.
              solve() 1회 = 1 제출.
    """

    def __init__(self, semantic_memory_root: str = "semantic_memory"):
        """[설계 자유] semantic_memory_root 경로, 제출 횟수 카운터."""
        self.semantic_memory_root = semantic_memory_root
        self._submission_count: int = 0
        self._current_task_hex: str = None

    def solve(self, task) -> list:
        """
        [SOAR 강제] 사이클 실행 흐름 (WM 초기화 → run_cycle → 결과 추출) 자체.
        [설계 자유] LTM rule 선로드 방식, max_steps 값.

        흐름:
          1. 새 태스크이면 _submission_count 리셋
          2. reset_wm_snapshot() 호출  ← 태스크 경계마다 diff 상태 초기화
          3. WorkingMemory 생성
          4. build_wm_from_task(task, wm)
          5. LTM rule 로드 → wm.s1["active_rules"] 초기화
          6. elaborator = build_elaborator()
          7. proposer   = build_proposer()
          8. run_cycle(wm, elaborator, proposer, max_steps=50)
          9. answers = answers_from_wm(wm)
          10. _submission_count += 1
          11. return answers
        """
        reset_wm_snapshot()
        raise NotImplementedError("ActiveSoarAgent.solve() not implemented yet.")

    def on_substate_resolved(self, substate: dict, task_hex: str):
        """
        [SOAR 강제] subgoal 해결 시 chunking 트리거.
        [설계 자유] chunk 결과를 어떻게 저장할지.
        MUST NOT: solve 루프 내부에서 직접 호출하지 마 — cycle.py가 호출.
        """
        raise NotImplementedError("ActiveSoarAgent.on_substate_resolved() not implemented.")

    @property
    def can_retry(self) -> bool:
        """[설계 자유] 최대 제출 횟수 (현재 3회). 태스크별 카운터."""
        return self._submission_count < 3
