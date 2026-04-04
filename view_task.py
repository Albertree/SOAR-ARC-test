"""
view_task.py — Print ARC task grids as readable 2D integer matrices.

Usage:
  python view_task.py 08ed6ac7                          # by task hex ID
  python view_task.py data/ARC_AGI/training/08ed6ac7.json  # by file path
  python view_task.py 08ed6ac7 --color                  # with ANSI color blocks

Prints train and test input/output grids row-by-row so spatial
patterns are visually obvious. No solver logic is imported.
"""

import json
import os
import sys
import argparse


def load_task(task_id_or_path):
    """Load task JSON from hex ID or file path."""
    if os.path.isfile(task_id_or_path):
        path = task_id_or_path
    else:
        # Try training then evaluation
        for split in ("training", "evaluation"):
            candidate = os.path.join("data", "ARC_AGI", split, f"{task_id_or_path}.json")
            if os.path.isfile(candidate):
                path = candidate
                break
        else:
            print(f"Task not found: {task_id_or_path}")
            sys.exit(1)

    with open(path) as f:
        return json.load(f), path


def print_grid(grid, label="", use_color=False):
    """Print a 2D grid as aligned integers or ANSI color blocks."""
    if label:
        print(f"  {label} ({len(grid)}x{len(grid[0]) if grid else 0}):")
    if use_color:
        _print_color_grid(grid)
    else:
        # Find max digit width for alignment
        max_val = max(max(row) for row in grid) if grid else 0
        w = len(str(max_val))
        for row in grid:
            print("    " + " ".join(str(v).rjust(w) for v in row))


# ANSI color palette (same as basics/viz.py)
_PALETTE = {
    0:  (0,   0,   0),    1:  (0,   116, 217),  2:  (255, 65,  54),
    3:  (46,  204, 64),   4:  (255, 220, 0),    5:  (170, 170, 170),
    6:  (240, 18,  190),  7:  (255, 133, 27),   8:  (127, 219, 255),
    9:  (135, 12,  37),
}


def _print_color_grid(grid):
    """Print grid as ANSI color blocks (same style as viz.py)."""
    for row in grid:
        cells = []
        for v in row:
            r, g, b = _PALETTE.get(v, (180, 180, 180))
            cells.append(f"\033[48;2;{r};{g};{b}m  \033[0m")
        print("    " + "".join(cells))


def main():
    parser = argparse.ArgumentParser(description="View ARC task grids as 2D matrices")
    parser.add_argument("task", help="Task hex ID or path to JSON file")
    parser.add_argument("--color", "-c", action="store_true", help="Show ANSI color blocks instead of numbers")
    args = parser.parse_args()

    data, path = load_task(args.task)
    task_name = os.path.splitext(os.path.basename(path))[0]

    print(f"\n{'=' * 50}")
    print(f"  Task: {task_name}")
    print(f"  Train pairs: {len(data['train'])}  Test pairs: {len(data['test'])}")
    print(f"{'=' * 50}")

    for i, pair in enumerate(data["train"]):
        print(f"\n  --- Train Pair {i} ---")
        print_grid(pair["input"], "Input", use_color=args.color)
        print()
        print_grid(pair["output"], "Output", use_color=args.color)

    for i, pair in enumerate(data["test"]):
        print(f"\n  --- Test Pair {i} ---")
        print_grid(pair["input"], "Input", use_color=args.color)
        if "output" in pair:
            print()
            print_grid(pair["output"], "Expected Output", use_color=args.color)

    print()


if __name__ == "__main__":
    main()
