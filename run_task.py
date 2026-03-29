"""
Single task execution script — for inner loop success criteria evaluation.
python run_task.py                    # default regression task (08ed6ac7)
python run_task.py --task c0f76784    # run a specific task
python run_task.py --raw              # show raw WM triplets instead of narrative

Success criteria: output contains "CORRECT"
"""

import re
import sys
import argparse
import traceback

TASK_HEX = "08ed6ac7"
# TASK_HEX = "00d62c1b" #"0ca9ddb6" # "0a2355a6"


MAX_STEPS = 500  # Allow enough iterations until goal is achieved

_ANSI_RE = re.compile(r'\x1B\[[0-9;]*m')


def _strip_ansi(text):
    return _ANSI_RE.sub('', text)


def _print_grid(grid, label="", indent="    "):
    """Print a 2D grid as aligned integers."""
    if not grid:
        return
    if label:
        h, w = len(grid), len(grid[0]) if grid else 0
        print(f"{indent}{label} ({h}x{w}):")
    max_val = max(max(row) for row in grid) if grid else 0
    width = len(str(max_val))
    for row in grid:
        print(indent + " ".join(str(v).rjust(width) for v in row))


def _show_task_numeric(task):
    """Show task grids as numeric matrices (no ANSI)."""
    for i, pair in enumerate(task.example_pairs):
        print(f"\n  --- Example {i} ---")
        _print_grid(pair.input_grid.raw, "Input")
        print()
        if pair.output_grid is not None:
            _print_grid(pair.output_grid.raw, "Output")

    for i, pair in enumerate(task.test_pairs):
        print(f"\n  --- Test {i} ---")
        _print_grid(pair.input_grid.raw, "Input")


# =====================================================================
# Semantic trace wrappers — intercept elaborator/proposer to log
# a human-readable narrative without modifying cycle.py
# =====================================================================

class _TracingElaborator:
    """Wraps an Elaborator to log which flags get derived."""

    def __init__(self, elaborator, wm):
        self._inner = elaborator
        self._wm = wm

    def run(self, wm):
        # Snapshot elaborated flags before
        before = set(wm.active.keys())
        self._inner.run(wm)
        after = set(wm.active.keys())
        new_flags = after - before
        if new_flags:
            flags_str = ", ".join(sorted(new_flags))
            print(f"    Elaborate: derived [{flags_str}]")


class _TracingProposer:
    """Wraps a Proposer to log which operators get proposed."""

    def __init__(self, proposer):
        self._inner = proposer
        self._step = [0]  # mutable counter shared with trace

    def propose(self, wm):
        candidates = self._inner.propose(wm)
        if candidates:
            names = [c.name for c in candidates]
            # Wrap candidates to trace apply
            wrapped = [_TracingOperator(c, self._step) for c in candidates]
            names_str = ", ".join(names)
            depth_str = f"S{wm.depth + 1}" if wm.depth >= 0 else "?"
            print(f"  [Step {self._step[0]}] Propose: [{names_str}] (depth={wm.depth}, state={depth_str})")
            return wrapped
        else:
            print(f"  [Step {self._step[0]}] Propose: (no candidates)")
            return candidates


class _TracingOperator:
    """Wraps an operator to log what it does on apply."""

    def __init__(self, op, step_counter):
        self._op = op
        self._step = step_counter
        # Copy attributes cycle.py needs
        self.name = op.name
        self.proposal_preference = getattr(op, "proposal_preference", "+")

    def precondition(self, wm):
        return self._op.precondition(wm)

    def effect(self, wm):
        # Snapshot S1 keys before
        s1_before = set(wm.s1.keys())

        self._op.effect(wm)

        # Determine what changed
        s1_after = set(wm.s1.keys())
        new_keys = s1_after - s1_before

        step = self._step[0]
        name = self.name

        print(f"  [Step {step}] Selected: {name}")

        if name == "solve-task":
            print(f"  [Step {step}] Applied: solve-task (abstract, no WM change)")
            print(f"  [Step {step}] -> Impasse (no-change) -> creating substate S2")
        elif name == "select_target":
            agenda = wm.s1.get("comparison-agenda", [])
            pending = wm.s1.get("pending-comparisons", [])
            print(f"  [Step {step}] Applied: select_target -> queued {len(agenda)} pairs for comparison ({len(pending)} pending)")
        elif name == "compare":
            comparisons = wm.s1.get("comparisons", {})
            pending = wm.s1.get("pending-comparisons", [])
            last_key = sorted(comparisons.keys())[-1] if comparisons else "?"
            print(f"  [Step {step}] Applied: compare -> completed {last_key} ({len(pending)} remaining)")
        elif name == "extract_pattern":
            patterns = wm.s1.get("patterns", {})
            analyses = patterns.get("pair_analyses", [])
            preserved = patterns.get("grid_size_preserved", False)
            total_changes = sum(a.get("total_changes", 0) for a in analyses)
            total_groups = sum(a.get("num_groups", 0) for a in analyses)
            print(f"  [Step {step}] Applied: extract_pattern -> {len(analyses)} pairs analyzed")
            print(f"             grid_size_preserved={preserved}, total_changes={total_changes}, groups={total_groups}")
        elif name == "generalize":
            rules = wm.s1.get("active-rules", [])
            if rules:
                rule = rules[0]
                rtype = rule.get("type", "?")
                conf = rule.get("confidence", "?")
                print(f"  [Step {step}] Applied: generalize -> rule type={rtype}, confidence={conf}")
                if rtype == "color_mapping":
                    mapping = rule.get("mapping", {})
                    print(f"             mapping: {mapping}")
                elif rtype == "recolor_sequential":
                    print(f"             sort_key={rule.get('sort_key')}, start_color={rule.get('start_color')}, source_colors={rule.get('source_colors')}")
                elif rtype == "identity":
                    print(f"             (fallback: no real pattern found, copies input)")
            else:
                print(f"  [Step {step}] Applied: generalize -> no rules produced")
        elif name == "predict":
            predictions = wm.s1.get("predictions", {})
            rules = wm.s1.get("active-rules", [])
            rtype = rules[0].get("type", "?") if rules else "?"
            print(f"  [Step {step}] Applied: predict -> {len(predictions)} test output(s) via {rtype}")
        elif name == "submit":
            goal = wm.s1.get("goal", {})
            subs = goal.get("subgoals", {})
            solved = sum(1 for s in subs.values() if isinstance(s, dict) and s.get("status") == "solved")
            print(f"  [Step {step}] Applied: submit -> {solved} test(s) submitted, goal satisfied")
        else:
            if new_keys:
                print(f"  [Step {step}] Applied: {name} -> added to S1: {sorted(new_keys)}")
            else:
                print(f"  [Step {step}] Applied: {name} (no WM change)")

        if wm.depth > 0 and new_keys:
            print(f"  [Step {step}] -> Substate resolved, popping back to S1")

        self._step[0] += 1


def main():
    parser = argparse.ArgumentParser(description="Run single task regression check")
    parser.add_argument("--task", "-t", default=None, help="Task hex ID to run (default: 08ed6ac7)")
    parser.add_argument("--raw", action="store_true", help="Show raw WM triplets instead of narrative trace")
    args = parser.parse_args()

    task_hex = args.task or TASK_HEX

    print(f"=== run_task: {task_hex} ===\n")

    # 1. Load task
    print("[*] Loading task...")
    try:
        from managers.arc_manager import ARCManager

        manager = ARCManager(data_root="data", semantic_memory_root="semantic_memory")
        task = manager.load_task(task_hex)
        print(f"    Task: {task}")
        _show_task_numeric(task)

    except Exception:
        print("[!] Task loading failed:")
        traceback.print_exc()
        sys.exit(1)

    print("\n[*] SOAR cycle (Elaborate -> Propose -> Select -> Apply)...")
    print("-" * 55)
    try:
        from agent.wm import WorkingMemory
        from agent.wm_logger import print_wm_triplets, reset_wm_snapshot
        from agent.io import inject_arc_task
        from agent.elaboration_rules import build_elaborator
        from agent.rules import build_proposer
        from agent.cycle import run_cycle

        wm = WorkingMemory()
        reset_wm_snapshot(wm)
        inject_arc_task(task, wm)

        elaborator = build_elaborator()
        proposer = build_proposer()

        if args.raw:
            # Raw mode: strip ANSI but show full WM triplets
            import builtins
            _orig_print = builtins.print

            def _clean_print(*a, **kw):
                cleaned = [_strip_ansi(x) if isinstance(x, str) and '\033[' in x else x for x in a]
                _orig_print(*cleaned, **kw)

            builtins.print = _clean_print

            reset_wm_snapshot(wm)
            print_wm_triplets(wm, label="Initial WM (before input)", step=0)
            inject_arc_task(task, wm)
            print_wm_triplets(wm, label="After input-link injection (before cycle)", step=0)

            out = run_cycle(
                wm, elaborator, proposer,
                max_steps=MAX_STEPS,
                stop_on_goal=True,
                log_wm=True,
            )

            builtins.print = _orig_print
        else:
            # Narrative mode: wrap elaborator/proposer for semantic trace
            tracing_elaborator = _TracingElaborator(elaborator, wm)
            tracing_proposer = _TracingProposer(proposer)

            out = run_cycle(
                wm, tracing_elaborator, tracing_proposer,
                max_steps=MAX_STEPS,
                stop_on_goal=True,
                log_wm=False,
            )

        print("-" * 55)
        print(f"[cycle] steps={out['steps_taken']}, goal_satisfied={out['goal_satisfied']}")

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
        _show_output(task, predicted, answer, correct)
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


def _show_output(task, predicted, answer, correct):
    """Display predicted vs expected as numeric grids."""
    if predicted is None:
        print("\n[output] No prediction produced.")
        return

    # Normalize to list of grids
    pred_grids = predicted
    if pred_grids and not isinstance(pred_grids[0], list):
        pred_grids = [pred_grids]

    ans_grids = answer if answer else []

    print("\n" + "-" * 40)
    for i in range(max(len(pred_grids), len(ans_grids))):
        pred = pred_grids[i] if i < len(pred_grids) else None
        ans = ans_grids[i] if i < len(ans_grids) else None

        match_str = "MATCH" if pred == ans else "MISMATCH"
        print(f"\n  test_{i}: << {match_str}")

        if i < len(task.test_pairs):
            _print_grid(task.test_pairs[i].input_grid.raw, "Input")
        if pred is not None:
            print()
            _print_grid(pred, "Predicted")
        if ans is not None:
            print()
            _print_grid(ans, "Expected")
    print("\n" + "-" * 40)


def _print_result(correct: bool, error: bool = False):
    print("\n" + "=" * 40)
    if error:
        print("RESULT  : ERROR (unable to evaluate)")
    elif correct:
        print("RESULT  : CORRECT")
    else:
        print("RESULT  : INCORRECT")
    print("=" * 40)


if __name__ == "__main__":
    main()
