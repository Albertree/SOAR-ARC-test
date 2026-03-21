"""
전체 시스템의 단일 진입점.
ARCEnvironment 초기화 → ActiveSoarAgent 초기화 → env.run_benchmark(agent) 실행.

MUST NOT: 어떤 solve 로직도 여기에 두지 마. 환경 루프만 있어야 한다.
"""

from arc2_env.arc_environment import ARCEnvironment
from agent.active_agent import ActiveSoarAgent


def main():
    env = ARCEnvironment(
        task_list=None,          # None이면 data/ 전체 태스크
        time_budget_sec=300,
        max_attempts_per_task=3,
    )
    agent = ActiveSoarAgent(semantic_memory_root="semantic_memory")

    results = env.run_benchmark(agent)
    print(f"correct: {results['correct']} / {results['total']}")


if __name__ == "__main__":
    main()
