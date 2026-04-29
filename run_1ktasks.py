"""
Batch evaluation script — runs all training tasks with the current rule state.

Evaluation only: stored rules are applied, new rules discovered by the pipeline
are NOT saved. This gives a clean snapshot of the current procedural memory.

Usage:
    python run_1ktasks.py
    python run_1ktasks.py --data-dir data/ARC_AGI/training
    python run_1ktasks.py --timeout 30 --output results.json
    python run_1ktasks.py --max-tasks 50
"""

import sys
import os
import json
import time
import argparse
import signal
from pathlib import Path
from datetime import datetime


TRAINING_DIR = "data/ARC_AGI/training"
DEFAULT_TIMEOUT = 60   # seconds per task (0 = no timeout)
MAX_STEPS = 500


# ── timeout helper (Unix only) ────────────────────────────────────────────────

class TimeoutError(BaseException):
    pass


def _timeout_handler(signum, frame):
    raise TimeoutError()


def run_with_timeout(fn, seconds):
    """Run fn() with a per-task wall-clock timeout (SIGALRM, Unix only)."""
    if seconds <= 0 or not hasattr(signal, "SIGALRM"):
        return fn()
    signal.signal(signal.SIGALRM, _timeout_handler)
    signal.alarm(seconds)
    try:
        return fn()
    finally:
        signal.alarm(0)


# ── result helpers ─────────────────────────────────────────────────────────────

def _load_answer(task):
    answers = []
    for pair in task.test_pairs:
        if hasattr(pair, "output") and pair.output is not None:
            answers.append(pair.output.contents)
    return answers if answers else None


def _check_correct(predicted, answer):
    if predicted is None or answer is None:
        return False
    if predicted and not isinstance(predicted[0], list):
        predicted = [predicted]
    if len(predicted) != len(answer):
        return False
    return all(p == a for p, a in zip(predicted, answer))


# ── eval-only solver (no rule saving) ─────────────────────────────────────────

def _solve_eval_only(agent, task):
    """
    Solve one task using stored rules + SOAR pipeline, but never save new rules.
    Patches out the save step so procedural memory stays unchanged.
    """
    import agent.memory as mem_module

    original_save = mem_module.save_rule_to_ltm

    def _no_save(*args, **kwargs):
        return None

    mem_module.save_rule_to_ltm = _no_save
    try:
        return agent.solve(task)
    finally:
        mem_module.save_rule_to_ltm = original_save


# ── main ───────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Eval-only batch run over all training tasks (no rule saving)"
    )
    parser.add_argument("--data-dir", default=TRAINING_DIR,
                        help=f"Path to task JSON directory (default: {TRAINING_DIR})")
    parser.add_argument("--timeout", type=int, default=DEFAULT_TIMEOUT,
                        help="Per-task timeout in seconds (0 = unlimited, default: 60)")
    parser.add_argument("--output", default=None,
                        help="Save per-task results to a JSON file (optional)")
    parser.add_argument("--max-tasks", type=int, default=0,
                        help="Stop after N tasks (0 = all)")
    args = parser.parse_args()

    data_dir = Path(args.data_dir)
    if not data_dir.exists():
        print(f"[!] Data directory not found: {data_dir}")
        sys.exit(1)

    task_files = sorted(data_dir.glob("*.json"))
    if args.max_tasks > 0:
        task_files = task_files[: args.max_tasks]

    total = len(task_files)
    print(f"=== run_1ktasks (eval-only): {total} tasks from {data_dir} ===")
    print(f"    timeout={args.timeout}s  max_steps={MAX_STEPS}  no rule saving")
    print(f"    started at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

    from managers.arc_manager import ARCManager
    from agent.active_agent import ActiveSoarAgent

    manager = ARCManager(data_root="data", semantic_memory_root="semantic_memory")
    agent = ActiveSoarAgent(max_steps=MAX_STEPS)

    n_correct = 0
    n_incorrect = 0
    n_error = 0
    n_timeout = 0
    per_task_results = []

    start_all = time.time()

    for idx, task_file in enumerate(task_files, 1):
        task_hex = task_file.stem
        t0 = time.time()
        status = "error"
        correct = False
        method = "none"
        rule_type = "none"
        err_msg = ""

        try:
            task = manager.load_task(task_hex)
            answer = _load_answer(task)

            def _solve():
                return _solve_eval_only(agent, task)

            predicted = run_with_timeout(_solve, args.timeout)
            correct = _check_correct(predicted, answer)
            method = agent.last_solve_info.get("method", "none")
            rule_type = agent.last_solve_info.get("rule_type", "none")
            status = "correct" if correct else "incorrect"

            if correct:
                n_correct += 1
            else:
                n_incorrect += 1

        except TimeoutError:
            status = "timeout"
            n_timeout += 1
            err_msg = f"exceeded {args.timeout}s"

        except Exception as e:
            status = "error"
            n_error += 1
            err_msg = str(e)

        elapsed = time.time() - t0
        acc_so_far = n_correct / idx * 100
        mark = "O" if status == "correct" else ("T" if status == "timeout" else ("E" if status == "error" else "X"))

        print(
            f"[{idx:4d}/{total}] {mark}  {task_hex}  "
            f"({elapsed:5.1f}s)  method={method:<14}  rule={rule_type:<20}  "
            f"acc={acc_so_far:.1f}%"
            + (f"  [{err_msg}]" if err_msg else "")
        )

        per_task_results.append({
            "task_hex": task_hex,
            "status": status,
            "correct": correct,
            "method": method,
            "rule_type": rule_type,
            "elapsed_s": round(elapsed, 2),
            "error": err_msg,
        })

    # ── final summary ──────────────────────────────────────────────────────────
    total_elapsed = time.time() - start_all
    accuracy = n_correct / total * 100 if total else 0.0

    print("\n" + "=" * 60)
    print(f"TOTAL TASKS : {total}")
    print(f"CORRECT     : {n_correct}  ({accuracy:.2f}%)")
    print(f"INCORRECT   : {n_incorrect}")
    print(f"TIMEOUT     : {n_timeout}")
    print(f"ERROR       : {n_error}")
    print(f"ELAPSED     : {total_elapsed:.1f}s  ({total_elapsed/total:.1f}s/task avg)")
    print("=" * 60)

    method_counts: dict[str, int] = {}
    for r in per_task_results:
        method_counts[r["method"]] = method_counts.get(r["method"], 0) + 1
    print("\nMethod breakdown:")
    for m, cnt in sorted(method_counts.items(), key=lambda x: -x[1]):
        print(f"  {m:<20} {cnt:4d}")

    if args.output:
        out_path = Path(args.output)
        report = {
            "timestamp": datetime.now().isoformat(),
            "data_dir": str(data_dir),
            "eval_only": True,
            "total": total,
            "correct": n_correct,
            "incorrect": n_incorrect,
            "timeout": n_timeout,
            "error": n_error,
            "accuracy_pct": round(accuracy, 4),
            "elapsed_s": round(total_elapsed, 1),
            "tasks": per_task_results,
        }
        out_path.write_text(json.dumps(report, indent=2))
        print(f"\n[*] Results saved to {out_path}")

    sys.exit(0 if n_error == 0 and n_timeout == 0 else 1)


if __name__ == "__main__":
    main()
