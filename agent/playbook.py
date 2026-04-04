"""
playbook — ACE-style evolving playbook for the SOAR-ARC loop.

The playbook accumulates knowledge incrementally via structured deltas.
Each bullet has an ID, section, helpful/harmful counters, and source tasks.
The playbook is never rewritten wholesale -- only deltas are applied.

Three roles interact with the playbook:
  1. Generator (run_learn.py) — produces trajectory logs
  2. Reflector (scripts/reflect.py) — analyzes failures into reflections
  3. Curator (scripts/curate.py) — applies reflections as playbook deltas
"""

import json
import os
from datetime import datetime

DEFAULT_PATH = "PLAYBOOK.json"

# Section prefix map for auto-generating IDs
_SECTION_PREFIX = {
    "descent_policy": "dp",
    "activation_rules": "ar",
    "known_failure_modes": "kf",
    "comparison_patterns": "cp",
    "anti_regression": "reg",
    "primitives": "pr",
    "chunking_heuristics": "ch",
}


def load_playbook(path=DEFAULT_PATH):
    """Load and return the playbook dict. Returns empty skeleton if missing."""
    if not os.path.exists(path):
        return _empty_playbook()
    try:
        with open(path, "r") as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        return _empty_playbook()


def save_playbook(playbook, path=DEFAULT_PATH):
    """Save playbook to disk. Updates last_updated timestamp."""
    playbook["last_updated"] = datetime.now().isoformat()
    with open(path, "w") as f:
        json.dump(playbook, f, indent=2)


def render_for_prompt(playbook, max_tokens=6000):
    """
    Render playbook as readable text for injection into Claude Code prompts.

    Format per section:
      ## Section Name
      - [id] content (+helpful/-harmful)

    Bullets sorted by (helpful - harmful) descending within each section.
    Bullets with harmful > 0 are always kept (warnings).
    If over max_tokens, drop zero-evidence bullets first.
    """
    bullets = playbook.get("bullets", [])

    # Group by section
    sections = {}
    for b in bullets:
        sec = b.get("section", "other")
        sections.setdefault(sec, []).append(b)

    # Sort each section by score descending
    for sec in sections:
        sections[sec].sort(
            key=lambda b: b.get("helpful_count", 0) - b.get("harmful_count", 0),
            reverse=True,
        )

    # Render
    lines = ["# PLAYBOOK (v{})".format(playbook.get("version", "?"))]

    section_order = [
        "descent_policy", "activation_rules", "comparison_patterns",
        "anti_regression", "primitives", "chunking_heuristics",
        "known_failure_modes",
    ]

    for sec_name in section_order:
        sec_bullets = sections.get(sec_name, [])
        if not sec_bullets:
            continue
        title = sec_name.replace("_", " ").title()
        lines.append(f"\n## {title}")
        for b in sec_bullets:
            bid = b.get("id", "?")
            content = b.get("content", "")
            h = b.get("helpful_count", 0)
            m = b.get("harmful_count", 0)
            score = f"(+{h}/-{m})" if h or m else ""
            lines.append(f"- [{bid}] {content} {score}".rstrip())

    # Handle sections not in order
    for sec_name, sec_bullets in sections.items():
        if sec_name in section_order:
            continue
        title = sec_name.replace("_", " ").title()
        lines.append(f"\n## {title}")
        for b in sec_bullets:
            bid = b.get("id", "?")
            content = b.get("content", "")
            lines.append(f"- [{bid}] {content}")

    rendered = "\n".join(lines)

    # Truncation: estimate tokens as chars/4
    est_tokens = len(rendered) // 4
    if est_tokens > max_tokens:
        # Drop zero-evidence bullets (not harmful ones)
        bullets_to_keep = [
            b for b in bullets
            if b.get("helpful_count", 0) > 0 or b.get("harmful_count", 0) > 0
        ]
        playbook_trimmed = dict(playbook)
        playbook_trimmed["bullets"] = bullets_to_keep
        return render_for_prompt(playbook_trimmed, max_tokens)

    return rendered


def apply_delta(playbook, delta):
    """
    Apply a curator delta to the playbook.

    Delta format:
      {
        "add": [{"section": "...", "content": "...", "source_tasks": [...]}],
        "update": [{"id": "...", "helpful_count_delta": N, "harmful_count_delta": M}],
        "prune": ["id1", "id2"]
      }

    Returns modified playbook (caller saves it).
    """
    bullets = playbook.get("bullets", [])
    pruned = playbook.get("pruned", [])

    # Process additions
    for entry in delta.get("add", []):
        section = entry.get("section", "known_failure_modes")
        content = entry.get("content", "")
        source_tasks = entry.get("source_tasks", [])

        new_id = _next_id(bullets, pruned, section)
        bullets.append({
            "id": new_id,
            "section": section,
            "content": content,
            "helpful_count": 0,
            "harmful_count": 0,
            "source_tasks": source_tasks,
            "created_at": datetime.now().isoformat(),
            "last_signal_at": None,
        })

    # Process updates
    bullet_map = {b["id"]: b for b in bullets}
    for entry in delta.get("update", []):
        bid = entry.get("id", "")
        if bid in bullet_map:
            b = bullet_map[bid]
            b["helpful_count"] = b.get("helpful_count", 0) + entry.get("helpful_count_delta", 0)
            b["harmful_count"] = b.get("harmful_count", 0) + entry.get("harmful_count_delta", 0)
            b["last_signal_at"] = datetime.now().isoformat()

    # Process prunes
    for bid in delta.get("prune", []):
        remaining = []
        for b in bullets:
            if b["id"] == bid:
                b["pruned_at"] = datetime.now().isoformat()
                pruned.append(b)
            else:
                remaining.append(b)
        bullets = remaining

    playbook["bullets"] = bullets
    playbook["pruned"] = pruned
    playbook["version"] = playbook.get("version", 0) + 1
    return playbook


def record_signal(playbook, bullet_id, helpful, task_hex):
    """
    Record a helpful or harmful signal on a bullet.
    Returns modified playbook (caller saves it).
    """
    for b in playbook.get("bullets", []):
        if b["id"] == bullet_id:
            if helpful:
                b["helpful_count"] = b.get("helpful_count", 0) + 1
                playbook["total_helpful_signals"] = playbook.get("total_helpful_signals", 0) + 1
            else:
                b["harmful_count"] = b.get("harmful_count", 0) + 1
                playbook["total_harmful_signals"] = playbook.get("total_harmful_signals", 0) + 1
            b["last_signal_at"] = datetime.now().isoformat()
            if task_hex and task_hex not in b.get("source_tasks", []):
                b.setdefault("source_tasks", []).append(task_hex)
            break
    return playbook


def _next_id(bullets, pruned, section):
    """Generate next sequential ID for a section."""
    prefix = _SECTION_PREFIX.get(section, section[:2])
    all_items = bullets + pruned
    max_num = 0
    for b in all_items:
        bid = b.get("id", "")
        if bid.startswith(prefix + "-"):
            try:
                num = int(bid.split("-")[1])
                max_num = max(max_num, num)
            except (ValueError, IndexError):
                pass
    return f"{prefix}-{max_num + 1:03d}"


def _empty_playbook():
    """Return an empty playbook skeleton."""
    return {
        "version": 0,
        "last_updated": datetime.now().isoformat(),
        "total_helpful_signals": 0,
        "total_harmful_signals": 0,
        "bullets": [],
        "pruned": [],
    }
