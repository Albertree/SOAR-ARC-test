"""
단일 태스크 실행 스크립트 — inner loop 성공 기준 판정용.
python run_task.py

성공 기준: 출력에 "CORRECT" 포함
"""

import sys
import traceback

TASK_HEX = "08ed6ac7"
MAX_STEPS = 500  # goal 달성 전까지 충분히 돌 수 있도록


def main():
    print(f"=== run_task: {TASK_HEX} ===\n")

    # 1. 태스크 로드
    print("[*] 태스크 로드...")
    try:
        from basics.viz import show_task
        from managers.arc_manager import ARCManager

        manager = ARCManager(data_root="data", semantic_memory_root="semantic_memory")
        task = manager.load_task(TASK_HEX)
        print(f"    Task: {task}")
        show_task(task)

    except Exception:
        print("[!] 태스크 로드 실패:")
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
        print("[!] WM / cycle 실패:")
        traceback.print_exc()
        _print_result(False, error=True)
        sys.exit(1)

    # 2. 결과 판정
    # wm에서 제출된 답 꺼내기
    try:
        predicted = _extract_prediction(wm)
        answer = _load_answer(task)
        correct = _check_correct(predicted, answer)
        _print_result(correct)
        sys.exit(0 if correct else 1)

    except Exception:
        print("[!] 결과 판정 실패:")
        traceback.print_exc()
        _print_result(False, error=True)
        sys.exit(1)


def _extract_prediction(wm):
    """
    WM output-link에서 예측 그리드를 꺼낸다.
    SubmitOperator가 아래 슬롯에 결과를 써야 한다:
      (S1 ^output-link O_out)
      (O_out ^predicted-grid [[...], [...], ...])
    구현 전까지는 None 반환.
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
    task 객체에서 test pair의 정답 output grid를 꺼낸다.
    test pair가 여러 개면 리스트로 반환.
    """
    answers = []
    for pair in task.test_pairs:
        if hasattr(pair, "output") and pair.output is not None:
            answers.append(pair.output.contents)
    return answers if answers else None


def _check_correct(predicted, answer):
    """
    predicted: 예측 그리드 (list[list[int]] 또는 list of them)
    answer:    정답 그리드 리스트
    완전 일치할 때만 True.
    """
    if predicted is None or answer is None:
        return False
    # 단일 그리드로 왔을 때 리스트로 감싸기
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
        print("RESULT  : ERROR (판정 불가)")
    elif correct:
        print("RESULT  : CORRECT ✅")
    else:
        print("RESULT  : INCORRECT ❌")
    print("=" * 40)


if __name__ == "__main__":
    main()