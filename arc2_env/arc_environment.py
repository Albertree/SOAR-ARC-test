"""
ARCEnvironment — ARC 벤치마크 실행 환경.
태스크 제공, 채점(pixel-exact match), 시간 예산, 실행 트레이스를 관리한다.

에이전트는 Task 객체(ARCKG 노드)를 받아 solve()를 호출한다.
SOAR가 유일한 solver이므로 SolverAgent 등 별도 fallback은 없다.
"""

import json
import time
from pathlib import Path

from managers.arc_manager import ARCManager

DEFAULT_MAX_ATTEMPTS_PER_TASK = 3


def _grids_equal(a: list, b: list) -> bool:
    """두 그리드(list[list[int]])가 pixel-exact로 같은지 비교."""
    if a is b:
        return True
    if len(a) != len(b):
        return False
    for row_a, row_b in zip(a, b):
        if len(row_a) != len(row_b) or row_a != row_b:
            return False
    return True


class ARCEnvironment:
    """
    에이전트에게 Task 객체를 제공하고, 제출된 answer를 채점하며,
    시간 예산과 trace를 관리하는 평가 환경.

    MUST NOT: solve 로직을 여기에 포함하지 마.
              에이전트 인스턴스를 여기서 생성하지 마.
    """

    def __init__(
        self,
        task_list: list = None,
        time_budget_sec: float = None,
        enable_trace: bool = True,
        max_attempts_per_task: int = DEFAULT_MAX_ATTEMPTS_PER_TASK,
    ):
        """
        Args:
            task_list: None이면 data/ 전체 태스크. list[str]이면 hex 코드 목록.
            time_budget_sec: 에피소드 전체 시간 제한(초). None이면 무제한.
            enable_trace: step마다 trace 기록 여부.
            max_attempts_per_task: 태스크당 최대 제출 횟수(agent.can_retry와 연동).
        """
        self._time_budget_sec = time_budget_sec
        self._enable_trace = enable_trace
        self._max_attempts_per_task = max_attempts_per_task
        self._trace: list = []
        self._episode_start_time = None

        # task 순서 결정
        if task_list is None:
            index_to_hex, _ = ARCManager._build_task_mapping()
            self._task_ids = [index_to_hex[i] for i in sorted(index_to_hex)]
        else:
            self._task_ids = list(task_list)

        self._current_index: int = -1
        self._current_task = None      # Task 객체 (ARCKG 노드)
        self._done: bool = True
        self._episode_task_ids: list = []
        self._attempts_left: int = 0   # 현재 태스크 남은 제출 횟수

    # ──────────────────────────────────────────
    # Public API
    # ──────────────────────────────────────────

    def reset(self, task_list: list = None):
        """
        새 에피소드 시작. 첫 번째 Task 객체를 반환한다.

        Args:
            task_list: 이번 에피소드에만 쓸 hex 코드 목록. None이면 생성자 목록 사용.

        Returns:
            첫 번째 Task 객체 (없으면 None).
        """
        self._episode_task_ids = list(task_list) if task_list is not None else list(self._task_ids)
        self._current_index = -1
        self._current_task = None
        self._trace = []
        self._done = not self._episode_task_ids
        self._episode_start_time = time.perf_counter()

        if self._done:
            return None
        return self._advance_to_next_task()

    def get_task(self):
        """현재 Task 객체 반환. 에피소드가 끝났으면 None."""
        return self._current_task

    def get_current_task_id(self):
        """현재 태스크의 hex 코드. 없으면 None."""
        return self._current_task.task_hex if self._current_task else None

    def step(self, answer: list) -> tuple:
        """
        에이전트의 answer를 채점한다.

        Args:
            answer: test pair 순서대로 출력 그리드 목록. 각 원소는 list[list[int]].

        Returns:
            (reward, next_task, done, info)
            - reward: 1.0 = 전부 정답, 0.0 = 하나라도 오답.
            - next_task: 다음 Task 객체. can_retry면 현재 Task.
            - done: 에피소드 종료 여부.
            - info: {"correct_per_pair": [bool,...], "attempts_left": int, "can_retry": bool}
        """
        info = {"correct_per_pair": [], "attempts_left": 0, "can_retry": False}
        if self._current_task is None:
            return 0.0, None, True, info

        # answer 정규화
        if not isinstance(answer, list):
            answer = [answer]
        if answer and isinstance(answer[0], (list, tuple)):
            if answer[0] and not isinstance(answer[0][0], (list, tuple)):
                answer = [answer]

        test_pairs = self._current_task.test_pairs
        n = len(test_pairs)

        correct_per_pair = []
        if len(answer) != n:
            reward = 0.0
            correct_per_pair = [False] * n
        else:
            for i, test_pair in enumerate(test_pairs):
                gt = self._get_ground_truth(test_pair)
                ok = _grids_equal(answer[i], gt)
                correct_per_pair.append(ok)
            reward = 1.0 if all(correct_per_pair) else 0.0

        self._attempts_left -= 1
        info["correct_per_pair"] = correct_per_pair
        info["attempts_left"] = self._attempts_left

        if self._enable_trace:
            self._trace.append({
                "task_id": self.get_current_task_id(),
                "reward": reward,
                "correct_per_pair": correct_per_pair,
                "attempts_left": self._attempts_left,
                "elapsed_sec": time.perf_counter() - self._episode_start_time
                               if self._episode_start_time else None,
            })

        # 시간 예산 초과 체크
        if self._time_budget_exceeded():
            self._done = True
            return reward, None, True, info

        if reward >= 1.0:
            next_task = self._advance_to_next_task()
            return reward, next_task, self._done, info

        # 재시도 가능 여부: attempts_left AND agent.can_retry 모두 필요
        if self._attempts_left > 0:
            info["can_retry"] = True
            return reward, self._current_task, False, info

        # 시도 소진 → 다음 태스크로
        next_task = self._advance_to_next_task()
        return reward, next_task, self._done, info

    def run_benchmark(self, agent, n: int = None) -> dict:
        """
        agent.solve(task)를 반복 호출해 벤치마크를 실행한다.

        Args:
            agent: .solve(task) → list[list[list[int]]], .can_retry → bool 인터페이스.
            n: 최대 수행 태스크 수. None이면 전부.

        Returns:
            {"correct": int, "total": int, "results": list, "trace": list}
        """
        episode_list = self._task_ids[:n] if n is not None else self._task_ids
        if not episode_list:
            return {"correct": 0, "total": 0, "results": [], "trace": []}

        self.reset(task_list=episode_list)
        results = []
        correct = 0

        while not self._done:
            task = self.get_task()
            if task is None:
                break

            task_id = self.get_current_task_id()
            num_submissions = 0
            reward = 0.0
            info = {}

            while True:
                answer = agent.solve(task)
                reward, next_task, done, info = self.step(answer)
                num_submissions += 1

                if reward >= 1.0:
                    correct += 1
                    break

                if not info.get("can_retry"):
                    break
                if not getattr(agent, "can_retry", False):
                    self._advance_to_next_task()
                    break

                task = self.get_task()
                if task is None:
                    break

            if hasattr(agent, "update_memory"):
                agent.update_memory(reward)

            results.append({
                "task_id": task_id,
                "reward": reward,
                "num_submissions": num_submissions,
                "attempts_left": info.get("attempts_left", 0),
            })

        return {
            "correct": correct,
            "total": len(results),
            "results": results,
            "trace": list(self._trace),
        }

    def run_single_task(self, task_id: str, agent=None) -> tuple:
        """
        단일 태스크 실행.

        Returns:
            (reward, info)
        """
        self.reset(task_list=[task_id])
        task = self.get_task()
        if task is None:
            return 0.0, {"task_id": task_id, "error": "task not found", "correct": False}

        if agent is None:
            return 0.0, {
                "task_id": task_id,
                "task": task,
                "num_test_pairs": len(task.test_pairs),
            }

        reward = 0.0
        info = {}
        num_submissions = 0

        while True:
            answer = agent.solve(task)
            reward, next_task, done, info = self.step(answer)
            num_submissions += 1

            if reward >= 1.0:
                break
            if not info.get("can_retry"):
                break
            if not getattr(agent, "can_retry", False):
                break
            task = self.get_task()
            if task is None:
                break

        if hasattr(agent, "update_memory"):
            agent.update_memory(reward)

        return reward, {
            "task_id": task_id,
            "correct": reward >= 1.0,
            "reward": reward,
            "num_submissions": num_submissions,
            "trace": self.get_trace(),
        }

    def get_trace(self) -> list:
        """현재 에피소드 trace 반환."""
        return list(self._trace)

    def save_trace(self, path) -> None:
        """trace를 JSON 파일로 저장."""
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(self._trace, f, indent=2, ensure_ascii=False)

    # ──────────────────────────────────────────
    # Internal helpers
    # ──────────────────────────────────────────

    def _advance_to_next_task(self):
        """다음 태스크로 이동하고 Task 객체 반환."""
        if self._time_budget_exceeded():
            self._done = True
            return None

        self._current_index += 1
        if self._current_index >= len(self._episode_task_ids):
            self._done = True
            self._current_task = None
            return None

        task_id = self._episode_task_ids[self._current_index]
        try:
            self._current_task = ARCManager.from_hex_code(task_id)
            self._attempts_left = self._max_attempts_per_task
            return self._current_task
        except (FileNotFoundError, Exception):
            return self._advance_to_next_task()

    def _get_ground_truth(self, test_pair) -> list:
        """test pair의 정답 그리드를 list[list[int]]로 반환."""
        grid = test_pair.output_grid
        if hasattr(grid, "view"):
            return grid.view
        return grid

    def _time_budget_exceeded(self) -> bool:
        if self._time_budget_sec is None or self._episode_start_time is None:
            return False
        return time.perf_counter() - self._episode_start_time >= self._time_budget_sec
