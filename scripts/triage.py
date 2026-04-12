#!/usr/bin/env python3
"""
Triage script — runs N tasks and generates CLAUDE_BRIEF.md for the next session.

Usage:
    python scripts/triage.py         # 50 tasks, seed 42
    python scripts/triage.py 100 1   # 100 tasks, seed 1

Output: CLAUDE_BRIEF.md in the project root
"""
import os
import sys
import json
import random
import time
import inspect
from collections import Counter

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def classify_failure(agent, task):
    info = agent.last_solve_info
    rule = info.get("rule_type", "none")
    if rule not in ("none", "identity", ""):
        return "SOLVED", None
    try:
        from procedural_memory.base_rules._concept_engine import _last_failure_diagnostics
        diag = _last_failure_diagnostics or {}
    except Exception:
        diag = {}
    nm = diag.get("best_near_miss") or {}
    partial = nm.get("partial_score", 0.0)
    concepts_tried = info.get("concepts_tried", 0)
    if concepts_tried == 0:
        return "MISSING_CONCEPT", {"partial": 0.0}
    elif partial >= 0.9:
        return "PARAM_ERROR", {"partial": partial, "concept": nm.get("concept_id")}
    else:
        return "STRUCTURAL", {"partial": partial, "concept": nm.get("concept_id")}


def render_grid(grid, max_rows=8, max_cols=12):
    rows = []
    for row in grid[:max_rows]:
        rows.append(" ".join(str(c).rjust(1) for c in row[:max_cols]))
    if len(grid) > max_rows:
        rows.append(f"... ({len(grid) - max_rows} more rows)")
    return "\n".join(rows)


def get_unused_primitives():
    from procedural_memory.base_rules import _primitives as P
    all_prims = set(
        n for n, o in inspect.getmembers(P)
        if inspect.isfunction(o) and not n.startswith("_")
    )
    used = set()
    concepts_dir = "procedural_memory/concepts"
    if os.path.isdir(concepts_dir):
        for f in os.listdir(concepts_dir):
            if f.endswith(".json"):
                try:
                    with open(os.path.join(concepts_dir, f)) as fp:
                        c = json.load(fp)
                    for step in c.get("steps", []):
                        used.add(step.get("primitive", ""))
                except Exception:
                    pass
    return sorted(all_prims - used)


def get_task_signature(task):
    try:
        p = task.example_pairs[0]
        h_in, w_in = p.input_grid.height, p.input_grid.width
        h_out, w_out = p.output_grid.height, p.output_grid.width
        in_c = sorted(set(c for row in p.input_grid.raw for c in row))
        out_c = sorted(set(c for row in p.output_grid.raw for c in row))
        size_part = "same_size" if (h_in == h_out and w_in == w_out) else f"size_{h_out}x{w_out}"
        color_part = "color_change" if in_c != out_c else "no_color_change"
        count_part = f"{len(in_c)}in_{len(out_c)}out"
        return (size_part, color_part, count_part)
    except Exception:
        return ("unknown", "unknown", "unknown")


def find_top_gap(missing_tasks):
    sig_counter = Counter()
    sig_examples = {}
    for task, hex_id in missing_tasks:
        sig = get_task_signature(task)
        sig_counter[sig] += 1
        sig_examples.setdefault(sig, []).append((task, hex_id))
    if not sig_counter:
        return None, []
    top_sig = sig_counter.most_common(1)[0][0]
    return top_sig, sig_examples[top_sig]


def generate_brief(analyses, output_path="CLAUDE_BRIEF.md"):
    from procedural_memory.base_rules._concept_engine import _ensure_loaded, _concepts
    _ensure_loaded()

    solved = [(t, h) for t, h, cat, _ in analyses if cat == "SOLVED"]
    missing = [(t, h) for t, h, cat, _ in analyses if cat == "MISSING_CONCEPT"]
    param_err = [(t, h, m) for t, h, cat, m in analyses if cat == "PARAM_ERROR"]
    structural = [(t, h, m) for t, h, cat, m in analyses if cat == "STRUCTURAL"]

    top_sig, top_examples = find_top_gap(missing)
    unused_prims = get_unused_primitives()

    lines = []
    lines.append("# CLAUDE BRIEF")
    lines.append(f"Generated: {time.strftime('%Y-%m-%dT%H:%M:%S')}")
    lines.append(f"Tasks analyzed: {len(analyses)}")
    lines.append("")

    lines.append("## Results")
    lines.append("| Category | Count | % |")
    lines.append("|----------|-------|---|")
    total = len(analyses)
    for label, items in [("SOLVED", solved), ("MISSING_CONCEPT", missing),
                          ("PARAM_ERROR", param_err), ("STRUCTURAL", structural)]:
        pct = f"{100 * len(items) / max(total, 1):.0f}%"
        lines.append(f"| {label} | {len(items)} | {pct} |")
    lines.append("")

    lines.append("## Current Concepts")
    for c in sorted(_concepts, key=lambda x: x["concept_id"]):
        sig = c.get("signature", {})
        lines.append(f"- `{c['concept_id']}` — "
                     f"size_preserved={sig.get('grid_size_preserved', '?')}, "
                     f"color_preserved={sig.get('color_preserved', '?')}")
    lines.append("")

    if solved:
        lines.append("## Solved Tasks")
        for _, h in solved:
            lines.append(f"- `{h}`")
        lines.append("")

    if param_err:
        lines.append("## PARAM_ERROR Tasks (concept fired but wrong output)")
        lines.append("These are the easiest wins — the concept structure is right,")
        lines.append("only parameter inference needs fixing.")
        lines.append("")
        for _, h, m in sorted(param_err, key=lambda x: -(x[2] or {}).get("partial", 0))[:5]:
            partial = (m or {}).get("partial", 0)
            concept = (m or {}).get("concept")
            lines.append(f"- `{h}`: `{concept}` partial_score={partial:.2f}")
        lines.append("")

    if top_sig and top_examples:
        lines.append("## Highest Leverage Gap")
        lines.append(f"**{len(top_examples)} MISSING_CONCEPT tasks** share this signature:")
        lines.append(f"`{top_sig}`")
        lines.append("")
        lines.append("No concept covers this transformation. Writing one concept here")
        lines.append(f"could solve up to {len(top_examples)} tasks.")
        lines.append("")

        for task, hex_id in top_examples[:2]:
            if task is None:
                continue
            lines.append(f"### Example: `{hex_id}`")
            lines.append(f"Training pairs: {len(task.example_pairs)}")
            for i, p in enumerate(task.example_pairs[:2]):
                lines.append(f"**Pair {i}** "
                             f"({p.input_grid.height}x{p.input_grid.width} -> "
                             f"{p.output_grid.height}x{p.output_grid.width}):")
                lines.append("```")
                lines.append("Input:")
                lines.append(render_grid(p.input_grid.raw))
                lines.append("Output:")
                lines.append(render_grid(p.output_grid.raw))
                lines.append("```")
            lines.append("")

    lines.append("## Unused Primitives")
    lines.append(f"These {len(unused_prims)} primitives exist but no concept uses them:")
    for p in sorted(unused_prims):
        lines.append(f"- `{p}`")
    lines.append("")

    lines.append("## Your Task This Session")
    lines.append("")
    lines.append("1. Look at the grid examples in 'Highest Leverage Gap' above")
    lines.append("2. Describe the transformation in one sentence")
    lines.append("3. Find the matching primitive in the unused list above")
    lines.append("4. Write the concept JSON at `procedural_memory/concepts/<name>.json`")
    lines.append("5. Test immediately with try_single_concept")
    lines.append("6. At least 2 of 3 example tasks must validate")
    lines.append("7. Run: `python scripts/validate_concepts.py`")
    lines.append("8. Run: `python run_task.py` -- must output RESULT: CORRECT")
    lines.append("9. DO NOT modify `_primitives.py`")
    lines.append("")

    with open(output_path, "w") as f:
        f.write("\n".join(lines))

    print(f"Brief written to {output_path}")
    print(f"Summary: SOLVED={len(solved)}, MISSING={len(missing)}, "
          f"PARAM_ERROR={len(param_err)}, STRUCTURAL={len(structural)}")
    if top_sig:
        print(f"Top gap: {top_sig} ({len(top_examples)} tasks)")
    print(f"Unused primitives: {len(unused_prims)}")


def main():
    from managers.arc_manager import ARCManager
    from agent.active_agent import ActiveSoarAgent

    limit = int(sys.argv[1]) if len(sys.argv) > 1 else 50
    seed = int(sys.argv[2]) if len(sys.argv) > 2 else 42

    manager = ARCManager()
    agent = ActiveSoarAgent()
    random.seed(seed)

    all_tasks = os.listdir("data/ARC_AGI/training")
    sample = random.sample(all_tasks, min(limit, len(all_tasks)))

    analyses = []
    for i, fname in enumerate(sample):
        hex_id = fname.replace(".json", "")
        try:
            t = manager.load_task(hex_id)
            agent.solve(t)
            cat, meta = classify_failure(agent, t)
            analyses.append((t, hex_id, cat, meta))
            if (i + 1) % 10 == 0:
                print(f"[{i + 1}/{limit}] ...", flush=True)
        except Exception as e:
            analyses.append((None, hex_id, "ERROR", {"error": str(e)}))

    generate_brief(analyses)


if __name__ == "__main__":
    main()
