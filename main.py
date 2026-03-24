"""
Single entry point for the entire system.
ARCEnvironment init → ActiveSoarAgent init → env.run_benchmark(agent) execution.

MUST NOT: Do not put any solve logic here. Only the environment loop should be here.
"""

from arc2_env.arc_environment import ARCEnvironment
from agent.active_agent import ActiveSoarAgent


def main():
    env = ARCEnvironment(
        task_list=None,          # None means all tasks in data/
        time_budget_sec=300,
        max_attempts_per_task=3,
    )
    agent = ActiveSoarAgent(semantic_memory_root="semantic_memory")

    results = env.run_benchmark(agent)
    print(f"correct: {results['correct']} / {results['total']}")


if __name__ == "__main__":
    main()
