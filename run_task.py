"""
Single task execution script — for inner loop success criteria evaluation.
python run_task.py

Success criteria: output contains "CORRECT"
"""

import sys
import traceback

TASK_HEX = "08ed6ac7"
MAX_STEPS = 500  # Allow enough iterations until goal is achieved


def main():
    print(f"=== run_task: {TASK_HEX} ===\n")

    # 1. Load task
    print("[*] Loading task...")
    try:
        from basics.viz import show_task
        from managers.arc_manager import ARCManager

        manager = ARCManager(data_root="data", semantic_memory_root="semantic_memory")
        task = manager.load_task(TASK_HEX)
        print(f"    Task: {task}")
        show_task(task)

    except Exception:
        print("[!] Task loading failed:")
        traceback.print_exc()
        sys.exit(1)

    print("\n[*] WM + SOAR cycle (Elaborate → Propose → Select → Apply)...")
    try:
        from agent.wm import WorkingMemory
        from agent.wm_logger import print_wm_triplets, reset_wm_snapshot
        from agent.io import inject_arc_task
        from agent.elaboration_rules import build_elaborator
        from agent.rules import build_proposer
        from agent.cycle import run_cycle

        wm = WorkingMemory()

        reset_wm_snapshot(wm)
        print_wm_triplets(wm, label="Initial WM (before input)", step=0)

        inject_arc_task(task, wm)
        print_wm_triplets(wm, label="After input-link injection (before cycle)", step=0)

        elaborator = build_elaborator()
        proposer = build_proposer()

        out = run_cycle(
            wm,
            elaborator,
            proposer,
            max_steps=MAX_STEPS,
            stop_on_goal=True,
            log_wm=True,
        )
        print(f"\n[cycle] {out}")

    except Exception:
        print("[!] WM / cycle failed:")
        traceback.print_exc()
        _print_result(False, error=True)
        sys.exit(1)

    # 2. Result evaluation
    # Extract submitted answer from wm
    try:
        predicted = _extract_prediction(wm)
        answer = _load_answer(task)
        correct = _check_correct(predicted, answer)
        _print_result(correct)
        sys.exit(0 if correct else 1)

    except Exception:
        print("[!] Result evaluation failed:")
        traceback.print_exc()
        _print_result(False, error=True)
        sys.exit(1)


def _extract_prediction(wm):
    """
    Extract the predicted grid from the WM output-link.
    SubmitOperator must write the result to the following slots:
      (S1 ^output-link O_out)
      (O_out ^predicted-grid [[...], [...], ...])
    Returns None until implemented.
    """
    try:
        s1 = wm.get("S1")
        output_link_id = s1.get("output-link")
        if not output_link_id:
            return None
        output_node = wm.get(output_link_id)
        if not output_node:
            return None
        return output_node.get("predicted-grid")
    except Exception:
        return None


def _load_answer(task):
    """
    Extract the correct output grid from the task object's test pairs.
    Returns a list if there are multiple test pairs.
    """
    answers = []
    for pair in task.test_pairs:
        if hasattr(pair, "output") and pair.output is not None:
            answers.append(pair.output.contents)
    return answers if answers else None


def _check_correct(predicted, answer):
    """
    predicted: predicted grid (list[list[int]] or list of them)
    answer:    list of correct grids
    Returns True only on exact match.
    """
    if predicted is None or answer is None:
        return False
    # Wrap in a list if a single grid was provided
    if predicted and not isinstance(predicted[0], list):
        predicted = [predicted]
    if len(predicted) != len(answer):
        return False
    for pred, ans in zip(predicted, answer):
        if pred != ans:
            return False
    return True


def _print_result(correct: bool, error: bool = False):
    print("\n" + "=" * 40)
    if error:
        print("RESULT  : ERROR (unable to evaluate)")
    elif correct:
        print("RESULT  : CORRECT ✅")
    else:
        print("RESULT  : INCORRECT ❌")
    print("=" * 40)


if __name__ == "__main__":
    main()