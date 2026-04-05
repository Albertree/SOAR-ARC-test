"""
curate.py — Curator role in the ACE playbook architecture.

Reads reflections from reflect.py, produces deltas, and applies them
to PLAYBOOK.json. Enforces novelty limit (max 3 new bullets per run).

Usage:
  python scripts/curate.py logs/reflections_<timestamp>.json
"""

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agent.playbook import load_playbook, apply_delta, save_playbook


def curate(reflections_path):
    """Read reflections, produce and apply playbook delta."""
    with open(reflections_path, "r") as f:
        reflections = json.load(f)

    playbook = load_playbook()
    existing_bullets = playbook.get("bullets", [])
    root_causes = reflections.get("root_causes", [])
    individual = reflections.get("individual_reflections", [])

    delta = {"add": [], "update": [], "prune": []}

    # Check which root causes are novel (not already covered by a bullet)
    existing_content = set(b.get("content", "").lower() for b in existing_bullets)

    novel_strategies = []
    for rc in root_causes:
        topology = rc.get("topology")
        failure_type = rc.get("failure_type", "")
        affected = rc.get("affected_tasks", [])

        if not topology:
            continue

        # Check if any existing bullet covers this topology
        topo_str = json.dumps(sorted(topology.items()))
        already_covered = False
        for content in existing_content:
            if topo_str.lower() in content or failure_type.lower() in content:
                already_covered = True
                break

        if not already_covered:
            novel_strategies.append({
                "topology": topology,
                "failure_type": failure_type,
                "affected_tasks": affected,
                "diagnosis": rc.get("shared_diagnosis", ""),
            })

    # Enforce novelty limit: max 3 new bullets, prefer those affecting most tasks
    novel_strategies.sort(key=lambda s: len(s.get("affected_tasks", [])), reverse=True)
    novel_strategies = novel_strategies[:3]

    for strategy in novel_strategies:
        topo = strategy["topology"]
        ft = strategy["failure_type"]
        affected = strategy["affected_tasks"]
        topo_str = ", ".join(f"{k}:{v}" for k, v in sorted(topo.items()))

        content = f"[{ft}] Tasks with topology {{{topo_str}}} have no matching concept ({len(affected)} tasks affected)"
        delta["add"].append({
            "section": "known_failure_modes",
            "content": content,
            "source_tasks": affected,
        })

    # Signal helpful on existing bullets for successful tasks
    # (from individual reflections that are correct — but we only have failures here)
    # In future: trajectory could include successes with bullet tracking

    # Apply delta
    if delta["add"] or delta["update"] or delta["prune"]:
        playbook = apply_delta(playbook, delta)
        save_playbook(playbook)

    n_added = len(delta["add"])
    n_updated = len(delta["update"])
    n_pruned = len(delta["prune"])
    version = playbook.get("version", "?")

    print(f"[CURATOR] Added {n_added} new bullets")
    print(f"[CURATOR] Updated {n_updated} existing bullets")
    print(f"[CURATOR] Pruned {n_pruned} bullets")
    print(f"[CURATOR] Playbook version: {version}")

    # Save delta for audit
    delta_path = reflections_path.replace("reflections_", "delta_")
    try:
        with open(delta_path, "w") as f:
            json.dump(delta, f, indent=2)
    except Exception:
        pass

    return playbook


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python scripts/curate.py <reflections_file>")
        sys.exit(1)
    curate(sys.argv[1])
