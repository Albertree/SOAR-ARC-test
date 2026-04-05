"""
reflect.py — Reflector role in the ACE playbook architecture.

Reads a trajectory log from run_learn.py, analyzes failures, and produces
structured reflections with root cause analysis.

Usage:
  python scripts/reflect.py logs/trajectory_<timestamp>.json
"""

import json
import os
import sys
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def reflect(trajectory_path):
    """Analyze a trajectory log and produce reflections."""
    with open(trajectory_path, "r") as f:
        trajectory = json.load(f)

    tasks = trajectory.get("tasks", [])
    if not tasks:
        print("[REFLECT] No tasks in trajectory.")
        return None

    individual_reflections = []

    for entry in tasks:
        if entry.get("correct"):
            continue  # skip successful tasks

        task_hex = entry.get("task_hex", "?")
        method = entry.get("method", "?")
        rule_type = entry.get("rule_type", "?")
        topology = entry.get("topology")

        # Classify failure type
        if rule_type in ("identity", "none"):
            failure_type = "identity_fallback"
            diagnosis = f"Pipeline fell back to identity -- no concept matched"
        elif method == "pipeline":
            failure_type = "wrong_concept"
            diagnosis = f"Pipeline found concept '{rule_type}' but it produced wrong output"
        else:
            failure_type = "no_match"
            diagnosis = f"Method '{method}' with rule '{rule_type}' did not produce correct output"

        # Add topology context if available
        if topology:
            topo_str = ", ".join(f"{k}:{v}" for k, v in sorted(topology.items()))
            diagnosis += f" (topology: {{{topo_str}}})"

        reflection = {
            "task_hex": task_hex,
            "result": "incorrect",
            "method": method,
            "rule_type": rule_type,
            "topology": topology,
            "failure_type": failure_type,
            "diagnosis": diagnosis,
            "suggested_section": "known_failure_modes",
            "suggested_bullet": f"Tasks with topology {topology} need a matching concept",
        }
        individual_reflections.append(reflection)

    # Group by (topology_key, failure_type) for root causes
    root_cause_groups = {}
    for r in individual_reflections:
        topo = r.get("topology")
        ft = r.get("failure_type", "unknown")
        # Use sorted topology as key (or "unknown" if missing)
        if topo:
            topo_key = json.dumps(sorted(topo.items()))
        else:
            topo_key = "unknown_topology"
        group_key = f"{topo_key}|{ft}"
        root_cause_groups.setdefault(group_key, []).append(r)

    root_causes = []
    for group_key, reflections in root_cause_groups.items():
        affected = [r["task_hex"] for r in reflections]
        sample_topo = reflections[0].get("topology")
        ft = reflections[0].get("failure_type")

        if sample_topo:
            topo_str = ", ".join(f"{k}:{v}" for k, v in sorted(sample_topo.items()))
            shared_diagnosis = f"{ft}: {len(affected)} tasks share topology {{{topo_str}}} with no matching concept"
        else:
            shared_diagnosis = f"{ft}: {len(affected)} tasks failed without topology data"

        root_causes.append({
            "topology": sample_topo,
            "failure_type": ft,
            "affected_tasks": affected,
            "shared_diagnosis": shared_diagnosis,
            "proposed_strategy": f"Create concept or activation rule for topology {sample_topo}",
        })

    # Build output
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output = {
        "timestamp": timestamp,
        "source_trajectory": trajectory_path,
        "individual_reflections": individual_reflections,
        "root_causes": root_causes,
    }

    # Save
    output_path = f"logs/reflections_{timestamp}.json"
    os.makedirs("logs", exist_ok=True)
    with open(output_path, "w") as f:
        json.dump(output, f, indent=2)

    n_fail = len(individual_reflections)
    n_pass = len(tasks) - n_fail
    n_root = len(root_causes)
    print(f"[REFLECT] Analyzed {len(tasks)} tasks: {n_pass} passed, {n_fail} failed")
    print(f"[REFLECT] Root causes identified: {n_root}")
    print(f"[REFLECT] Output: {output_path}")

    return output_path


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python scripts/reflect.py <trajectory_file>")
        sys.exit(1)
    reflect(sys.argv[1])
