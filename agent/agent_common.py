"""
agent_common — Common utilities for WM initialization, termination condition checks, and answer extraction.
"""


def build_wm_from_task(task, wm) -> None:
    """
    Reflects task into WM. Does not create comparison agenda, relations, elaborated, etc.
    Only directly sets goal, subgoals, focus, and operator state.
    """
    wm.task = task
    goal = wm.s1["goal"]
    n_test = len(task.test_pairs)
    n_ex = len(task.example_pairs)

    goal["type"] = "solve_arc_task"
    goal["task_hex"] = task.task_hex
    goal["description"] = (
        f"ARC task {task.task_hex}: infer rule from {n_ex} example pair(s), "
        f"predict output for {n_test} test input(s)."
    )
    goal["phase"] = "analyze_examples"
    goal["subgoals"] = {}
    for i, pair in enumerate(task.test_pairs):
        goal["subgoals"][f"test_{i}"] = {
            "status": "pending",
            "pair_node_id": pair.node_id,
            "input_grid": pair.input_grid,
            "output": None,
        }

    wm.s1["focus"] = {
        "level": "GRID",
        "scope": "within_pair_examples",
    }


def goal_satisfied(wm) -> bool:
    goal = wm.active.get("goal") or {}
    subs = goal.get("subgoals") or {}
    if not subs:
        return True
    for _k, sg in sorted(subs.items()):
        if not isinstance(sg, dict):
            continue
        if sg.get("status") != "solved":
            return False
    return True


def answers_from_wm(wm) -> list | None:
    found = wm.active.get("found") or {}
    goal = wm.active.get("goal") or {}
    subs = goal.get("subgoals") or {}
    if not subs:
        return None

    def _test_order(k: str) -> int:
        if k.startswith("test_"):
            try:
                return int(k.split("_", 1)[1])
            except (ValueError, IndexError):
                return 0
        return 0

    keys = sorted(subs.keys(), key=_test_order)
    out = []
    for k in keys:
        out.append(found.get(k))
    if all(v is None for v in out):
        return None
    return out
