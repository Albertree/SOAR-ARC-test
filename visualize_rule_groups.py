"""
visualize_rule_groups.py

Group every rule in procedural_memory/ by its `rule.type` and render a
multi-page PDF.

Background
----------
A rule file is created or updated only when the agent's pipeline successfully
discovers a rule that reproduces all training pairs of a task. The task ID is
appended to the rule's `covers` list. So `covers` = "ARC tasks this rule
solved." A single task can appear in the `covers` of more than one rule when
more than one different rule (possibly of different types) fits the task.

Output
------
Page 1   : statistics overview — every rule type with:
             - # rules of that type
             - # distinct tasks those rules solved (one image per task,
               no matter how many rules of this type cover it)
             - # (rule, task) pairings (one entry per task in each rule's
               covers list — this is what adds up to the all-rules total)

Pages 2+ : one section per rule type, ordered most-rules-first. Each section
           shows:
             - the rule type
             - count of rules, distinct tasks, and (rule, task) pairings
             - explicit "Rule N -> task hex(es)" mapping for every rule
             - a thumbnail grid where each distinct task appears exactly once;
               the caption under each image lists every rule of this type
               that solved that task.

Usage:
    python visualize_rule_groups.py [--out rule_groups.pdf]
"""

import argparse
import json
import os
import textwrap
from collections import defaultdict
from pathlib import Path

import matplotlib.image as mpimg
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages

PROCEDURAL_MEMORY = Path("procedural_memory")
TASK_IMAGE_DIRS = [
    Path("data/ARC_AGI/full/train"),
    Path("data/ARC_AGI/full/eval"),
    Path("data/ARC_AGI/thumbnails/train"),
    Path("data/ARC_AGI/thumbnails/eval"),
]


def find_task_image(task_hex: str) -> Path | None:
    for d in TASK_IMAGE_DIRS:
        p = d / f"{task_hex}.png"
        if p.exists():
            return p
    return None


def load_rules() -> list:
    rules = []
    for fname in sorted(os.listdir(PROCEDURAL_MEMORY)):
        if not (fname.startswith("rule_") and fname.endswith(".json")):
            continue
        with open(PROCEDURAL_MEMORY / fname) as fh:
            rules.append(json.load(fh))
    return rules


def group_by_type(rules: list) -> dict:
    """
    For each rule type, collect:
      rules         : list of (rule_id, [task_hex, ...]) preserving covers order
      task_to_rules : task_hex -> [rule_id, ...] of rules of THIS type covering it
      task_order    : ordered list of distinct task_hexes (first-seen order)
    """
    groups = defaultdict(lambda: {"rules": [], "task_to_rules": {}, "task_order": []})
    for entry in rules:
        rule_type = entry.get("rule", {}).get("type", "unknown")
        rid = entry["id"]
        covers = entry.get("covers", [])
        g = groups[rule_type]
        g["rules"].append((rid, list(covers)))
        for task in covers:
            if task not in g["task_to_rules"]:
                g["task_to_rules"][task] = []
                g["task_order"].append(task)
            g["task_to_rules"][task].append(rid)
    return groups


def global_stats(rules: list) -> dict:
    distinct_tasks = set()
    total_pairs = 0
    unused_rules = []          # covers list is empty -> rule never applied
    one_shot_rules = []        # covers length 1 AND times_reused == 0
    for entry in rules:
        covers = entry.get("covers", [])
        total_pairs += len(covers)
        distinct_tasks.update(covers)
        if not covers:
            unused_rules.append(entry["id"])
        elif len(covers) == 1 and entry.get("times_reused", 0) == 0:
            one_shot_rules.append(entry["id"])
    return {
        "total_rules": len(rules),
        "distinct_tasks": len(distinct_tasks),
        "total_pairs": total_pairs,
        "unused_rules": sorted(unused_rules),
        "one_shot_rules": sorted(one_shot_rules),
    }


# ---------- global mapping pages -------------------------------------------

def _build_global_lines(rules: list, gstats: dict) -> list:
    """All-rules global rule->tasks then task<-rules listings."""
    lines = []

    # [A] Rule -> Tasks across ALL rules
    lines.append(f"[A] Rule -> Tasks   (every rule and the task IDs in its "
                 f"covers list; ALL {gstats['total_rules']} rules)")
    lines.append("")
    rules_sorted = sorted(rules, key=lambda e: e["id"])
    for entry in rules_sorted:
        rid = entry["id"]
        rtype = entry.get("rule", {}).get("type", "?")
        covers = entry.get("covers", [])
        head = f"rule {rid:>3}  [{rtype}]  ->  "
        body = ", ".join(covers) if covers else "(NO TASKS - rule never applied)"
        wrapped = textwrap.wrap(head + body, width=100,
                                subsequent_indent=" " * 14)
        lines.extend(wrapped)

    # [B] Task <- Rules across ALL tasks
    task_to_rules = {}
    task_order = []
    for entry in rules_sorted:
        rid = entry["id"]
        rtype = entry.get("rule", {}).get("type", "?")
        for task in entry.get("covers", []):
            if task not in task_to_rules:
                task_to_rules[task] = []
                task_order.append(task)
            task_to_rules[task].append((rid, rtype))
    task_order = sorted(task_order)

    lines.append("")
    lines.append("")
    lines.append(f"[B] Task <- Rules   (every distinct task and the rule(s) "
                 f"that cover it; ALL {gstats['distinct_tasks']} tasks; "
                 f"'<<MULTI' = covered by more than one rule)")
    lines.append("")
    for task in task_order:
        rs = sorted(task_to_rules[task])
        rule_strs = [f"rule {rid} [{rtype}]" for rid, rtype in rs]
        marker = "  <<MULTI" if len(rs) > 1 else ""
        head = f"task {task}  <-  "
        wrapped = textwrap.wrap(head + ", ".join(rule_strs) + marker,
                                width=100, subsequent_indent=" " * 18)
        lines.extend(wrapped)

    return lines


def render_global_mappings(pdf: PdfPages, rules: list, gstats: dict) -> None:
    lines = _build_global_lines(rules, gstats)
    multi_count = gstats["total_pairs"] - gstats["distinct_tasks"]

    line_h = 0.0165
    page_idx = 0
    line_idx = 0

    while True:
        fig, ax = plt.subplots(figsize=(8.5, 11))
        ax.axis("off")

        if page_idx == 0:
            ax.text(0.5, 0.975, "Procedural Memory — Global Mappings",
                    ha="center", va="top", fontsize=17, fontweight="bold")
            ax.text(0.5, 0.948,
                    f"{gstats['total_rules']} rule files   |   "
                    f"{gstats['distinct_tasks']} distinct tasks   |   "
                    f"{gstats['total_pairs']} (rule, task) entries",
                    ha="center", va="top", fontsize=11)
            ax.text(0.5, 0.928,
                    f"Tasks covered by more than one rule: {multi_count}    "
                    f"|   Unused rules (empty covers): "
                    f"{len(gstats['unused_rules'])}",
                    ha="center", va="top", fontsize=10)
            y = 0.895
        else:
            ax.text(0.5, 0.975,
                    f"Global Mappings (continued — page {page_idx + 1})",
                    ha="center", va="top", fontsize=12, style="italic")
            y = 0.945

        while line_idx < len(lines) and y > 0.04:
            ax.text(0.05, y, lines[line_idx], fontsize=7.5,
                    family="monospace")
            line_idx += 1
            y -= line_h

        pdf.savefig(fig)
        plt.close(fig)
        page_idx += 1
        if line_idx >= len(lines):
            break


# ---------- per-type section ------------------------------------------------

def _build_mapping_lines(rules: list, task_order: list,
                         task_to_rules: dict) -> list:
    """Two blocks: rule -> tasks, then task <- rules."""
    lines = []

    lines.append("[A] Rule -> Tasks   (one line per rule, showing every task "
                 "in its covers list)")
    lines.append("")
    for rid, tasks in sorted(rules):
        head = f"rule {rid:>3}  ->  "
        body = ", ".join(tasks) if tasks else "(none - rule never applied)"
        full = head + body
        wrapped = textwrap.wrap(full, width=88,
                                subsequent_indent=" " * len(head))
        lines.extend(wrapped)

    lines.append("")
    lines.append("[B] Task <- Rules   (one line per distinct task, showing "
                 "which rules of this type covered it)")
    lines.append("")
    for task in task_order:
        rule_ids = sorted(task_to_rules.get(task, []))
        head = f"task {task}  <-  "
        rule_str = ", ".join(f"rule {rid}" for rid in rule_ids)
        full = head + (rule_str if rule_str else "(no rules)")
        wrapped = textwrap.wrap(full, width=88,
                                subsequent_indent=" " * len(head))
        lines.extend(wrapped)

    return lines


def render_info_pages(pdf: PdfPages, rule_type: str, info: dict,
                      section_idx: int, total_sections: int) -> None:
    rules = info["rules"]
    n_rules = len(rules)
    n_tasks = len(info["task_order"])
    n_pairs = sum(len(t) for _, t in rules)

    mapping_lines = _build_mapping_lines(rules, info["task_order"],
                                          info["task_to_rules"])

    line_h = 0.018
    line_idx = 0
    info_page = 0

    while True:
        fig = plt.figure(figsize=(8.5, 11))
        fig.text(0.5, 0.97, f"Rule type: {rule_type}",
                 ha="center", va="top", fontsize=16, fontweight="bold")
        sub = f"Section {section_idx} / {total_sections}"
        if info_page > 0:
            sub += f"   (rule list continued, page {info_page + 1})"
        fig.text(0.5, 0.945, sub, ha="center", va="top",
                 fontsize=9, style="italic")

        if info_page == 0:
            fig.text(0.06, 0.91,
                     f"Total rules of this type: {n_rules}",
                     fontsize=11, fontweight="bold")
            fig.text(0.06, 0.89,
                     f"Total distinct tasks solved by these rules: {n_tasks}",
                     fontsize=11)
            fig.text(0.06, 0.87,
                     f"Total (rule, task) pairings (sum of covers entries): "
                     f"{n_pairs}",
                     fontsize=11)
            fig.text(0.06, 0.84,
                     "Mappings (both directions; block [A] then block [B]):",
                     fontsize=9.5, fontweight="bold")
            y = 0.815
        else:
            fig.text(0.06, 0.92,
                     "Mappings (continued):",
                     fontsize=10, fontweight="bold")
            y = 0.895

        while line_idx < len(mapping_lines) and y > 0.06:
            fig.text(0.06, y, mapping_lines[line_idx],
                     fontsize=8.5, family="monospace")
            line_idx += 1
            y -= line_h

        pdf.savefig(fig)
        plt.close(fig)
        info_page += 1
        if line_idx >= len(mapping_lines):
            break


def render_image_pages(pdf: PdfPages, rule_type: str, info: dict,
                       section_idx: int, total_sections: int) -> None:
    tasks = info["task_order"]
    task_to_rules = info["task_to_rules"]

    cols, rows = 3, 3
    images_per_page = cols * rows
    if not tasks:
        return
    n_image_pages = max(1, (len(tasks) + images_per_page - 1) // images_per_page)

    for page_idx in range(n_image_pages):
        fig = plt.figure(figsize=(8.5, 11))
        fig.text(0.5, 0.97,
                 f"Rule type: {rule_type} - task images",
                 ha="center", va="top", fontsize=14, fontweight="bold")
        fig.text(0.5, 0.945,
                 f"Section {section_idx} / {total_sections}   "
                 f"(image page {page_idx + 1} / {n_image_pages})",
                 ha="center", va="top", fontsize=9, style="italic")
        fig.text(0.5, 0.925,
                 "caption format:  task_hex   (rules: <ids>) - rules of this "
                 "type that solved this task",
                 ha="center", va="top", fontsize=8, style="italic")

        start = page_idx * images_per_page
        batch = tasks[start : start + images_per_page]

        margin_x = 0.05
        usable_w = 1 - 2 * margin_x
        cell_w = usable_w / cols
        grid_top = 0.90
        usable_h = grid_top - 0.04
        cell_h = usable_h / rows

        for i, task in enumerate(batch):
            r = i // cols
            c = i % cols
            x = margin_x + c * cell_w
            y = grid_top - (r + 1) * cell_h
            ax = fig.add_axes([x + cell_w * 0.04, y + cell_h * 0.13,
                               cell_w * 0.92, cell_h * 0.75])
            img_path = find_task_image(task)
            if img_path is not None:
                try:
                    ax.imshow(mpimg.imread(str(img_path)))
                except Exception:
                    ax.text(0.5, 0.5, "(load error)", ha="center", va="center",
                            fontsize=7, transform=ax.transAxes)
            else:
                ax.text(0.5, 0.5, "(image not found)", ha="center", va="center",
                        fontsize=8, transform=ax.transAxes)
            ax.set_xticks([])
            ax.set_yticks([])
            for spine in ax.spines.values():
                spine.set_visible(False)

            covering = task_to_rules.get(task, [])
            label = "rule" if len(covering) == 1 else "rules"
            rule_str = ", ".join(str(r) for r in sorted(covering))
            ax.set_title(f"{task}\n({label}: {rule_str})",
                         fontsize=8, family="monospace", pad=2)

        pdf.savefig(fig)
        plt.close(fig)


def render_type_section(pdf: PdfPages, rule_type: str, info: dict,
                        section_idx: int, total_sections: int) -> None:
    render_info_pages(pdf, rule_type, info, section_idx, total_sections)
    render_image_pages(pdf, rule_type, info, section_idx, total_sections)


# ---------- main ------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", default="rule_groups.pdf",
                        help="Output PDF path (default: rule_groups.pdf)")
    args = parser.parse_args()

    rules = load_rules()
    groups = group_by_type(rules)
    sorted_items = sorted(groups.items(),
                          key=lambda kv: (-len(kv[1]["rules"]), kv[0]))
    gstats = global_stats(rules)

    with PdfPages(args.out) as pdf:
        render_global_mappings(pdf, rules, gstats)
        for i, (rule_type, info) in enumerate(sorted_items, start=1):
            render_type_section(pdf, rule_type, info,
                                section_idx=i, total_sections=len(sorted_items))

    print(f"Wrote {args.out}  "
          f"({gstats['total_rules']} rules, "
          f"{len(sorted_items)} distinct types, "
          f"{gstats['distinct_tasks']} distinct tasks solved, "
          f"{gstats['total_pairs']} (rule,task) pairs)")


if __name__ == "__main__":
    main()
