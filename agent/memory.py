"""
memory — SOAR Chunking and LTM storage.

Rules are stored as JSON files in procedural_memory/:
  procedural_memory/rule_001.json
  procedural_memory/rule_002.json
  ...

Each file:
  {
    "id": 1,
    "rule": { ... },
    "source_task": "08ed6ac7",
    "created_at": "2026-03-24T19:00:00",
    "times_reused": 0
  }
"""

import json
import os
from datetime import datetime

PROCEDURAL_MEMORY_ROOT = "procedural_memory"


def save_rule_to_ltm(rule: dict, task_hex: str,
                     procedural_memory_root: str = PROCEDURAL_MEMORY_ROOT) -> str:
    """
    Save a learned rule to procedural_memory as a new JSON file.
    Returns the file path of the saved rule.
    """
    os.makedirs(procedural_memory_root, exist_ok=True)

    # Find next available ID
    existing = [
        f for f in os.listdir(procedural_memory_root)
        if f.startswith("rule_") and f.endswith(".json")
    ]
    next_id = len(existing) + 1

    # Don't save duplicate rules (same type + same key params)
    for f in existing:
        try:
            path = os.path.join(procedural_memory_root, f)
            with open(path, "r") as fh:
                stored = json.load(fh)
            if _rules_equivalent(stored.get("rule", {}), rule):
                return path
        except (json.JSONDecodeError, IOError):
            continue

    entry = {
        "id": next_id,
        "rule": rule,
        "source_task": task_hex,
        "created_at": datetime.now().isoformat(),
        "times_reused": 0,
    }

    filename = f"rule_{next_id:03d}.json"
    path = os.path.join(procedural_memory_root, filename)
    with open(path, "w") as f:
        json.dump(entry, f, indent=2)

    return path


def load_all_rules(procedural_memory_root: str = PROCEDURAL_MEMORY_ROOT) -> list:
    """
    Load all stored rules from procedural_memory.
    Returns list of entry dicts (each has "id", "rule", "source_task", etc).
    Sorted by times_reused descending (most reused first).
    """
    if not os.path.isdir(procedural_memory_root):
        return []

    rules = []
    for f in sorted(os.listdir(procedural_memory_root)):
        if not (f.startswith("rule_") and f.endswith(".json")):
            continue
        path = os.path.join(procedural_memory_root, f)
        try:
            with open(path, "r") as fh:
                entry = json.load(fh)
            entry["_path"] = path
            rules.append(entry)
        except (json.JSONDecodeError, IOError):
            continue

    rules.sort(key=lambda e: e.get("times_reused", 0), reverse=True)
    return rules


def increment_reuse_count(entry: dict) -> None:
    """Increment the times_reused counter for a stored rule and save back."""
    path = entry.get("_path")
    if not path or not os.path.exists(path):
        return
    try:
        with open(path, "r") as f:
            data = json.load(f)
        data["times_reused"] = data.get("times_reused", 0) + 1
        with open(path, "w") as f:
            json.dump(data, f, indent=2)
    except (json.JSONDecodeError, IOError):
        pass


def load_rules_from_ltm(task_hex: str,
                        semantic_memory_root: str = "semantic_memory") -> list:
    """Legacy interface — loads all rules (task_hex unused for now)."""
    return load_all_rules()


def chunk_from_substate(substate: dict) -> dict:
    """Placeholder — extract rule from resolved substate."""
    return {}


def _rules_equivalent(a: dict, b: dict) -> bool:
    """Check if two rules are functionally the same."""
    if a.get("type") != b.get("type"):
        return False
    t = a.get("type")
    # Concept rules: same concept_id + same params = equivalent
    if t and t.startswith("concept:"):
        return (a.get("concept_id") == b.get("concept_id")
                and a.get("params") == b.get("params"))
    if t == "recolor_sequential":
        return (a.get("sort_key") == b.get("sort_key")
                and a.get("start_color") == b.get("start_color")
                and a.get("source_colors") == b.get("source_colors"))
    if t == "color_mapping":
        return a.get("mapping") == b.get("mapping")
    return a == b
