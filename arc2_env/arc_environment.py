"""
ARCEnvironment — ARC benchmark execution environment.
Manages task provisioning, scoring (pixel-exact match), time budget, and execution traces.

The agent receives a Task object (ARCKG node) and calls solve().
Since SOAR is the only solver, there is no separate fallback such as SolverAgent.
"""

import json
import time
from pathlib import Path

from managers.arc_manager import ARCManager

DEFAULT_MAX_ATTEMPTS_PER_TASK = 3


def _grids_equal(a: list, b: list) -> bool:
    """Compare whether two grids (list[list[int]]) are pixel-exact equal."""
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
    An evaluation environment that provides Task objects to the agent,
    scores submitted answers, and manages time budget and traces.

    MUST NOT: Do not include solve logic here.
              Do not create agent instances here.
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
            task_list: If None, all tasks in data/. If list[str], a list of hex codes.
            time_budget_sec: Time limit in seconds for the entire episode. None means unlimited.
            enable_trace: Whether to record traces at each step.
            max_attempts_per_task: Maximum number of submissions per task (linked with agent.can_retry).
        """
        self._time_budget_sec = time_budget_sec
        self._enable_trace = enable_trace
        self._max_attempts_per_task = max_attempts_per_task
        self._trace: list = []
        self._episode_start_time = None

        # determine task order
        if task_list is None:
            index_to_hex, _ = ARCManager._build_task_mapping()
            self._task_ids = [index_to_hex[i] for i in sorted(index_to_hex)]
        else:
            self._task_ids = list(task_list)

        self._current_index: int = -1
        self._current_task = None      # Task object (ARCKG node)
        self._done: bool = True
        self._episode_task_ids: list = []
        self._attempts_left: int = 0   # remaining submission count for current task

    # ──────────────────────────────────────────
    # Public API
    # ──────────────────────────────────────────

    def reset(self, task_list: list = None):
        """
        Start a new episode. Returns the first Task object.

        Args:
            task_list: List of hex codes to use only for this episode. None uses the constructor list.

        Returns:
            The first Task object (None if empty).
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
        """Return the current Task object. None if the episode has ended."""
        return self._current_task

    def get_current_task_id(self):
        """Hex code of the current task. None if no current task."""
        return self._current_task.task_hex if self._current_task else None

    def step(self, answer: list) -> tuple:
        """
        Score the agent's answer.

        Args:
            answer: List of output grids in test pair order. Each element is list[list[int]].

        Returns:
            (reward, next_task, done, info)
            - reward: 1.0 = all correct, 0.0 = at least one incorrect.
            - next_task: Next Task object. Current Task if can_retry.
            - done: Whether the episode has ended.
            - info: {"correct_per_pair": [bool,...], "attempts_left": int, "can_retry": bool}
        """
        info = {"correct_per_pair": [], "attempts_left": 0, "can_retry": False}
        if self._current_task is None:
            return 0.0, None, True, info

        # normalize answer
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

        # check time budget exceeded
        if self._time_budget_exceeded():
            self._done = True
            return reward, None, True, info

        if reward >= 1.0:
            next_task = self._advance_to_next_task()
            return reward, next_task, self._done, info

        # retry eligibility: both attempts_left AND agent.can_retry are required
        if self._attempts_left > 0:
            info["can_retry"] = True
            return reward, self._current_task, False, info

        # attempts exhausted -> move to next task
        next_task = self._advance_to_next_task()
        return reward, next_task, self._done, info

    def run_benchmark(self, agent, n: int = None) -> dict:
        """
        Run the benchmark by repeatedly calling agent.solve(task).

        Args:
            agent: Interface with .solve(task) -> list[list[list[int]]], .can_retry -> bool.
            n: Maximum number of tasks to run. None means all.

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
        Run a single task.

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
        """Return the current episode trace."""
        return list(self._trace)

    def save_trace(self, path) -> None:
        """Save the trace as a JSON file."""
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(self._trace, f, indent=2, ensure_ascii=False)

    # ──────────────────────────────────────────
    # Internal helpers
    # ──────────────────────────────────────────

    def _advance_to_next_task(self):
        """Advance to the next task and return the Task object."""
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
        """Return the ground truth grid of a test pair as list[list[int]]."""
        grid = test_pair.output_grid
        if hasattr(grid, "view"):
            return grid.view
        return grid

    def _time_budget_exceeded(self) -> bool:
        if self._time_budget_sec is None or self._episode_start_time is None:
            return False
        return time.perf_counter() - self._episode_start_time >= self._time_budget_sec
