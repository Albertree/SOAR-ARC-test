"""
Sequential learning loop — feeds tasks to the SOAR agent one by one.
The agent accumulates rules in procedural_memory across tasks.

Usage:
  python run_learn.py                        # all training tasks
  python run_learn.py --split evaluation     # evaluation tasks
  python run_learn.py --limit 100            # first 100 tasks
  python run_learn.py --log-wm              # show WM logs per task
  python run_learn.py --shuffle              # random task order
  python run_learn.py --verbose             # detailed per-task trace
"""

import os
import sys
import json
import re
import time
import random
import argparse
from datetime import datetime

from managers.arc_manager import ARCManager
from agent.active_agent import ActiveSoarAgent
from agent.memory import load_all_rules
from agent.wm_logger import save_wm_snapshot
from ARCKG.comparison import clear_comparison_cache


# ── ANSI helpers (safe for Windows Git Bash / modern terminals) ────────
_BOLD  = "\033[1m"
_DIM   = "\033[2m"
_GREEN = "\033[32m"
_RED   = "\033[31m"
_YELLOW = "\033[33m"
_CYAN  = "\033[36m"
_RESET = "\033[0m"
_BG_GREEN = "\033[42;97m"
_BG_RED   = "\033[41;97m"

_ANSI_RE = re.compile(r'\033\[[0-9;]*m')


def _safe_print(text):
    """Print with fallback for Windows encoding issues."""
    try:
        print(text, flush=True)
    except UnicodeEncodeError:
        print(text.encode("ascii", errors="replace").decode("ascii"), flush=True)


def _progress_bar(done, total, width=20):
    if total == 0:
        return "[" + "?" * width + "]"
    filled = int(width * done / total)
    return "[" + "#" * filled + "." * (width - filled) + "]"


def parse_args():
    p = argparse.ArgumentParser(description="SOAR learning loop")
    p.add_argument("--split", default="training", help="training or evaluation")
    p.add_argument("--limit", type=int, default=None, help="max tasks to run")
    p.add_argument("--shuffle", action="store_true", help="randomize task order")
    p.add_argument("--seed", type=int, default=42, help="random seed for shuffle")
    p.add_argument("--log-wm", action="store_true", help="print WM logs per task")
    p.add_argument("--viz", action="store_true", help="show input/predicted/answer grids")
    p.add_argument("--verbose", "-v", action="store_true", help="detailed per-task trace")
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
        max_steps=80,
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
    verbose = args.verbose

    def log(msg):
        """Write to log file only (plain text, no ANSI)."""
        line = f"[{datetime.now().strftime('%H:%M:%S')}] {msg}"
        log_file.write(line + "\n")
        log_file.flush()

    def display(msg):
        """Print to terminal (may include ANSI) AND write plain version to log."""
        _safe_print(msg)
        # Strip ANSI for log file
        plain = _ANSI_RE.sub('', msg)
        log_file.write(plain + "\n")
        log_file.flush()

    start_time = time.time()
    initial_rules = len(load_all_rules("procedural_memory"))

    display(f"{_CYAN}{'=' * 60}{_RESET}")
    display(f"{_BOLD}  SOAR Learning Loop{_RESET}")
    display(f"  Split: {args.split}  |  Tasks: {total}  |  Stored rules: {initial_rules}")
    display(f"  Log: {_DIM}{log_path}{_RESET}")
    display(f"{_CYAN}{'=' * 60}{_RESET}")
    display("")

    for idx, task_hex in enumerate(task_hexes):
        task_start = time.time()
        clear_comparison_cache()

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
            if method in ("stored_rule", "episodic_cbr"):
                stored_rule_hits += 1
            if method == "pipeline" and rule_type != "identity" and rule_type != "none":
                pipeline_discoveries += 1

            # ── Format the per-task line ──────────────────────────
            if is_correct:
                status_tag = f"{_BG_GREEN} OK {_RESET}"
            else:
                status_tag = f"{_BG_RED} FAIL {_RESET}"

            if method == "episodic_cbr":
                cbr_task = info.get("cbr_matched_task", "?")[:8]
                cbr_sim = info.get("cbr_similarity", 0)
                method_str = f"CBR hit ({cbr_task}, sim={cbr_sim:.2f})"
            elif method == "stored_rule":
                method_str = f"memory hit ({info.get('rule_source', '?')[:8]})"
            else:
                method_str = f"pipeline ({steps} steps)"

            # Build failure trace suffix for Type A classifier
            fail_suffix = ""
            if not is_correct:
                ft = info.get("failure_trace")
                if ft and ft.get("best_near_miss"):
                    nm = ft["best_near_miss"]
                    score_pct = nm.get("partial_score", 0) * 100
                    total_cells = nm.get("total_cells", "?")
                    wrong_cells = nm.get("wrong_cells", "?")
                    pair_idx = nm.get("pair_index", "?")
                    cid = nm.get("concept_id", "?")
                    fail_suffix = f"  validation failed ({wrong_cells}/{total_cells} cells wrong, correct={score_pct:.0f}%, pair {pair_idx}, concept {cid})"

            # Compact per-task line
            num = f"[{idx+1:>{len(str(total))}}/{total}]"
            display(f"  {num} {task_hex}  {status_tag}  {rule_type:<22s} {_DIM}{method_str}  {elapsed:.1f}s{_RESET}{fail_suffix}")

            # Save WM snapshot for failed tasks (post-mortem debugging)
            if not is_correct and getattr(agent, "last_wm", None) is not None:
                try:
                    os.makedirs("logs/wm_snapshots", exist_ok=True)
                    save_wm_snapshot(agent.last_wm, f"logs/wm_snapshots/{task_hex}.json")
                except Exception:
                    pass

            # ── Episodic solution storage (T-UPDATE-2 + T4.EPISODIC) ─────
            if is_correct:
                wm = getattr(agent, "last_wm", None)
                try:
                    sol_dir = f"episodic_memory/solutions/{task_hex}"
                    os.makedirs(sol_dir, exist_ok=True)

                    concept_id = (rule_type.replace("concept:", "")
                                  if rule_type.startswith("concept:") else None)

                    active_rules = wm.s1.get("active-rules", []) if wm else []
                    params_inferred = None
                    composition_info = None
                    if active_rules:
                        r0 = active_rules[0]
                        if r0.get("params"):
                            params_inferred = r0["params"]
                        if r0.get("type", "").startswith("composition:"):
                            composition_info = {
                                "concept_id_a": r0.get("concept_id_a"),
                                "concept_id_b": r0.get("concept_id_b"),
                            }

                    # Build retrieval keys from WM comparison results
                    retrieval_key = {}
                    second_order_key = {}
                    au_invariants_val = {}
                    if wm is not None:
                        comps = wm.s1.get("comparisons", {})
                        comp_results = [v.get("result", {}) for v in comps.values() if v.get("result")]
                        if comp_results:
                            from agent.episodic import build_retrieval_key, build_second_order_retrieval_key
                            retrieval_key = build_retrieval_key(comp_results[0])
                            if len(comp_results) >= 2:
                                second_order_key = build_second_order_retrieval_key(
                                    comp_results[0], comp_results[1]
                                )
                        # Capture AU invariants and second-order from pipeline
                        so = wm.s1.get("second_order_comparison", {})
                        if so:
                            second_order_key = {
                                "nested_category": so.get("full_category", {}),
                                "score": so.get("score", "0/0"),
                                "comm_fields": so.get("comm_fields", []),
                                "content_comm_fields": so.get("content_comm_fields", {}),
                            }
                        au_invariants_val = wm.s1.get("au_invariants", {})

                    solution = {
                        "task_hex": task_hex,
                        "session_timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
                        "solved": True,
                        "method": method,
                        "concept_id": concept_id,
                        "topology": info.get("task_topology_str"),
                        "params_inferred": params_inferred,
                        "pairs_validated": len(task.example_pairs),
                        "composition": composition_info,
                        "steps_taken": steps,
                        "time_sec": round(elapsed, 2),
                        "retrieval_key": retrieval_key,
                        "second_order_key": second_order_key,
                        "au_invariants": au_invariants_val,
                    }
                    with open(f"{sol_dir}/solution.json", "w") as f:
                        json.dump(solution, f, indent=2)

                    if concept_id:
                        with open(f"{sol_dir}/rule.json", "w") as f:
                            json.dump({"concept_id": concept_id, "params": None}, f, indent=2)

                    trace = {
                        "steps_taken": steps,
                        "method": method,
                        "concept_id": concept_id,
                        "concepts_tried": info.get("concepts_tried", 0),
                        "cbr_tier": info.get("cbr_tier"),
                        "impasses_encountered": wm.s1.get("descent_count", 0) if wm else None,
                        "inter_pair_consistent": (
                            wm.s1.get("patterns", {}).get("inter_pair_consistent")
                            if wm else None
                        ),
                    }
                    with open(f"{sol_dir}/trace.json", "w") as f:
                        json.dump(trace, f, indent=2)
                except Exception as e:
                    print(f"[WARN] Could not write episodic record for {task_hex}: {e}")

            # ── Verbose: show more detail about what happened ─────
            if verbose:
                n_ex = len(task.example_pairs)
                n_test = len(task.test_pairs)
                display(f"         {_DIM}examples={n_ex}  tests={n_test}{_RESET}")
                if method == "episodic_cbr":
                    display(f"         {_GREEN}CBR: similar to {info.get('cbr_matched_task', '?')} (sim={info.get('cbr_similarity', 0):.2f}), reused rule{_RESET}")
                elif method == "stored_rule":
                    display(f"         {_GREEN}Reused stored rule from task {info.get('rule_source', '?')}{_RESET}")
                elif method == "pipeline":
                    if rule_type == "identity":
                        display(f"         {_RED}No pattern found -- fell back to identity (copy input){_RESET}")
                    elif rule_type == "color_mapping":
                        display(f"         {_GREEN}Discovered color_mapping rule{_RESET}")
                    elif rule_type == "recolor_sequential":
                        display(f"         {_GREEN}Discovered recolor_sequential rule{_RESET}")
                    elif rule_type == "none":
                        display(f"         {_RED}Pipeline produced no rule{_RESET}")
                    else:
                        display(f"         {_YELLOW}Discovered rule type: {rule_type}{_RESET}")

            if args.viz:
                _show_viz(task, predicted, is_correct)

            # ── Running tally every 5 tasks ───────────────────────
            if (idx + 1) % 5 == 0 or idx + 1 == total:
                current_rules = len(load_all_rules("procedural_memory"))
                pct = correct_count / (idx + 1) * 100
                bar = _progress_bar(correct_count, idx + 1, 15)
                display(f"  {_CYAN}---{_RESET} {bar} {correct_count}/{idx+1} ({pct:.0f}%)  "
                        f"rules: {initial_rules}->{current_rules}  "
                        f"reused: {stored_rule_hits}  "
                        f"discovered: {pipeline_discoveries}")

        except Exception as e:
            error_count += 1
            display(f"  [{idx+1}/{total}] {task_hex}  {_BG_RED} ERR {_RESET}  {e}")

    elapsed_total = time.time() - start_time
    final_rules = len(load_all_rules("procedural_memory"))
    pct = correct_count / max(total, 1) * 100

    display("")
    display(f"{_CYAN}{'=' * 60}{_RESET}")
    display(f"{_BOLD}  SESSION RESULTS{_RESET}")
    display(f"{_CYAN}{'=' * 60}{_RESET}")
    bar = _progress_bar(correct_count, total, 30)
    display(f"  Tasks:       {total}  ({error_count} errors)")
    display(f"  Correct:     {correct_count} / {total}  ({pct:.1f}%)  {bar}")
    display(f"  Rules:       {initial_rules} -> {final_rules}  (+{final_rules - initial_rules} learned)")
    display(f"  Reused:      {stored_rule_hits} times (stored rule hit)")
    display(f"  Discovered:  {pipeline_discoveries} new rules from pipeline")
    display(f"  Time:        {elapsed_total:.0f}s  ({elapsed_total/max(total,1):.1f}s/task)")
    display(f"{_CYAN}{'=' * 60}{_RESET}")

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
