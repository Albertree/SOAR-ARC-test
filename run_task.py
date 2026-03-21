"""
단일 태스크 실행 스크립트 — 에러 추적용.
python run_task.py
"""

import sys
import traceback


TASK_HEX = "08ed6ac7"


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

        # 2-1. 초기 WM 뼈대 덤프 (Soar 0th cycle 직전 상태)
        reset_wm_snapshot(wm)
        print_wm_triplets(wm, label="Initial WM (before input)", step=0)

        # 2-2. 환경 input function: task를 input-link로 주입
        inject_arc_task(task, wm)
        print_wm_triplets(wm, label="After input-link injection (before cycle)", step=0)

        elaborator = build_elaborator()
        proposer = build_proposer()
        # S1에 goal이 없으면 stop_on_goal은 사실상 무시됨(_s1_goal_satisfied가 False).
        out = run_cycle(
            wm,
            elaborator,
            proposer,
            max_steps=2,
            stop_on_goal=True,
            log_wm=True,
        )
        print(f"\n[cycle] {out}")
    except Exception:
        print("[!] WM / cycle 실패:")
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
