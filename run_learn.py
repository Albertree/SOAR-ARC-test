"""
Sequential learning loop — feeds tasks to the SOAR agent one by one.
The agent accumulates rules in procedural_memory across tasks.

Usage:
  python run_learn.py                        # all training tasks
  python run_learn.py --split evaluation     # evaluation tasks
  python run_learn.py --limit 100            # first 100 tasks
  python run_learn.py --log-wm              # show WM logs per task
  python run_learn.py --shuffle              # random task order
"""

import os
import sys
import json
import time
import random
import argparse
from datetime import datetime

from managers.arc_manager import ARCManager
from agent.active_agent import ActiveSoarAgent
from agent.memory import load_all_rules


def parse_args():
    p = argparse.ArgumentParser(description="SOAR learning loop")
    p.add_argument("--split", default="training", help="training or evaluation")
    p.add_argument("--limit", type=int, default=None, help="max tasks to run")
    p.add_argument("--shuffle", action="store_true", help="randomize task order")
    p.add_argument("--seed", type=int, default=42, help="random seed for shuffle")
    p.add_argument("--log-wm", action="store_true", help="print WM logs per task")
    p.add_argument("--viz", action="store_true", help="show input/predicted/answer grids")
    return p.parse_args()


def get_task_list(split, data_root="data"):
    """Get sorted list of task hex codes for a split."""
    split_dir = os.path.join(data_root, "ARC_AGI", split)
    if not os.path.isdir(split_dir):
        print(f"[!] Directory not found: {split_dir}")
        sys.exit(1)
    return sorted(f.replace(".json", "") for f in os.listdir(split_dir) if f.endswith(".json"))


def check_correct(predicted, task):
    """Check if predicted grids match the ground truth."""
    if predicted is None:
        return False
    answers = []
    for pair in task.test_pairs:
        if hasattr(pair, "output") and pair.output is not None:
            answers.append(pair.output.contents)
    if not answers:
        return False
    pred = predicted
    if pred and not isinstance(pred[0], list):
        pred = [pred]
    if len(pred) != len(answers):
        return False
    return all(p == a for p, a in zip(pred, answers))


def _show_viz(task, predicted, is_correct):
    """Show input, predicted, and ground truth grids side by side."""
    from basics.viz import _print_side_by_side

    for i, pair in enumerate(task.test_pairs):
        grids = [pair.input_grid.raw]
        labels = ["input"]

        if predicted is not None:
            pred = predicted if isinstance(predicted[0], list) else [predicted]
            if i < len(pred):
                grids.append(pred[i])
                labels.append("predicted")

        if hasattr(pair, "output") and pair.output is not None:
            grids.append(pair.output.contents)
            labels.append("answer")

        tag = "MATCH" if is_correct else "MISMATCH"
        print(f"  {'  |  '.join(labels)}  << {tag}")
        _print_side_by_side(grids, gap=6)
    print()


def main():
    args = parse_args()

    manager = ARCManager(data_root="data", semantic_memory_root="semantic_memory")
    agent = ActiveSoarAgent(
        semantic_memory_root="semantic_memory",
        procedural_memory_root="procedural_memory",
        max_steps=50,
    )

    task_hexes = get_task_list(args.split)
    if args.shuffle:
        random.seed(args.seed)
        random.shuffle(task_hexes)
    if args.limit is not None:
        task_hexes = task_hexes[:args.limit]

    total = len(task_hexes)
    correct_count = 0
    error_count = 0
    stored_rule_hits = 0
    pipeline_discoveries = 0

    # Log file
    os.makedirs("logs", exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_path = f"logs/learn_{timestamp}.log"
    log_file = open(log_path, "w")

    def log(msg):
        line = f"[{datetime.now().strftime('%H:%M:%S')}] {msg}"
        print(line)
        log_file.write(line + "\n")
        log_file.flush()

    start_time = time.time()
    initial_rules = len(load_all_rules("procedural_memory"))

    log(f"=== SOAR Learning Loop ===")
    log(f"Split: {args.split} | Tasks: {total} | Stored rules: {initial_rules}")
    log(f"Log: {log_path}")
    log("")

    for idx, task_hex in enumerate(task_hexes):
        task_start = time.time()

        try:
            task = manager.load_task(task_hex)
            predicted = agent.solve(task)
            is_correct = check_correct(predicted, task)
            elapsed = time.time() - task_start

            info = agent.last_solve_info
            method = info.get("method", "?")
            rule_type = info.get("rule_type", "?")
            steps = info.get("steps", 0)

            if is_correct:
                correct_count += 1
            if method == "stored_rule":
                stored_rule_hits += 1
            if method == "pipeline" and rule_type != "identity" and rule_type != "none":
                pipeline_discoveries += 1

            status = "CORRECT" if is_correct else "INCORRECT"
            method_str = f"stored({info.get('rule_source', '?')})" if method == "stored_rule" else f"pipeline(steps={steps})"

            log(f"[{idx+1}/{total}] {task_hex}: {status}  rule={rule_type}  via={method_str}  ({elapsed:.1f}s)")

            if args.viz:
                _show_viz(task, predicted, is_correct)

        except Exception as e:
            error_count += 1
            log(f"[{idx+1}/{total}] {task_hex}: ERROR ({e})")

    elapsed_total = time.time() - start_time
    final_rules = len(load_all_rules("procedural_memory"))

    log("")
    log("=" * 55)
    log(f"Tasks:       {total}  ({error_count} errors)")
    log(f"Correct:     {correct_count} / {total}  ({correct_count/max(total,1)*100:.1f}%)")
    log(f"Rules:       {initial_rules} -> {final_rules}  (+{final_rules - initial_rules} learned)")
    log(f"Reused:      {stored_rule_hits} times (stored rule hit)")
    log(f"Discovered:  {pipeline_discoveries} new rules from pipeline")
    log(f"Time:        {elapsed_total:.0f}s  ({elapsed_total/max(total,1):.1f}s/task)")
    log("=" * 55)

    log_file.close()

    # Write summary to session_log.md
    session_log_path = "logs/session_log.md"
    with open(session_log_path, "a") as f:
        f.write(f"\n---\n## Learning Loop -- {datetime.now().strftime('%Y-%m-%d %H:%M')}\n\n")
        f.write(f"- Split: {args.split}, Tasks: {total}\n")
        f.write(f"- Correct: {correct_count} / {total} ({correct_count/max(total,1)*100:.1f}%)\n")
        f.write(f"- Rules: {initial_rules} -> {final_rules} (+{final_rules - initial_rules} learned)\n")
        f.write(f"- Stored rule hits: {stored_rule_hits}\n")
        f.write(f"- Time: {elapsed_total:.0f}s\n")
        f.write(f"- Log: {log_path}\n")


if __name__ == "__main__":
    main()
