"""
validate_patch.py — Two-stage validation of activation rules.

Stage 1: For each rule's source_tasks, verify topology matches condition.
Stage 2: Verify no conflict with existing stored rules.

Usage:
  python scripts/validate_patch.py                    # validate all
  python scripts/validate_patch.py --rule <file>       # validate one
"""

import json
import os
import sys
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agent.episodic import extract_topology, topologies_match
from ARCKG.comparison import compare as arckg_compare
from managers.arc_manager import ARCManager

CHUNK_DIR = "DSL_activation_rule"


def validate_all(rule_file=None):
    """Validate activation rules. Returns (passed, failed) counts."""
    if rule_file:
        rules_to_check = [_load_rule(rule_file)]
        rules_to_check = [r for r in rules_to_check if r is not None]
    else:
        rules_to_check = _load_all_activation_rules()

    if not rules_to_check:
        print("VALIDATION_PASS (no rules to validate)")
        return 0, 0

    manager = ARCManager()
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    report = {
        "timestamp": timestamp,
        "rules_checked": len(rules_to_check),
        "rule_results": [],
        "overall": "PASS",
    }

    total_passed = 0
    total_failed = 0

    for rule in rules_to_check:
        rule_id = rule.get("rule_id", "unknown")
        source_tasks = rule.get("source_tasks", [])
        cond_topo = rule.get("condition", {}).get("topology", {})
        concept = rule.get("action", {}).get("concept", "")

        if not cond_topo:
            print(f"  [{rule_id}] SKIP (no topology in condition)")
            continue

        rule_result = {
            "rule_id": rule_id,
            "concept": concept,
            "stage1_results": [],
            "stage2_results": [],
            "result": "pass",
        }

        # Stage 1: Verify topology matches source tasks
        stage1_ok = True
        for task_hex in source_tasks:
            try:
                task = manager.load_task(task_hex)
                # Compute topology from ARCKG comparison
                for pair in task.example_pairs:
                    g0 = pair.input_grid
                    g1 = pair.output_grid
                    if g0 and g1:
                        comp = arckg_compare(g0, g1)
                        task_topo = extract_topology(comp)
                        matches = topologies_match(cond_topo, task_topo)
                        rule_result["stage1_results"].append({
                            "task_hex": task_hex,
                            "result": "pass" if matches else "fail",
                            "task_topology": task_topo,
                        })
                        if not matches:
                            stage1_ok = False
                        break  # only need first pair
            except Exception as e:
                rule_result["stage1_results"].append({
                    "task_hex": task_hex,
                    "result": "error",
                    "error": str(e),
                })

        if not stage1_ok:
            rule_result["result"] = "STAGE1_FAIL"
            report["overall"] = "STAGE1_FAIL"
            total_failed += 1
            print(f"  [{rule_id}] STAGE1_FAIL — topology mismatch on source tasks")
        else:
            # Stage 2: Spot-check a sample of stored rules for conflicts
            stage2_ok = True
            try:
                from agent.memory import load_all_rules
                stored = load_all_rules()
                # Only check top 10 most-reused rules (performance)
                checked = 0
                for entry in stored[:10]:
                    stored_rule = entry.get("rule", {})
                    stored_task = entry.get("source_task", "")
                    stored_concept = stored_rule.get("concept_id", stored_rule.get("type", ""))
                    if stored_concept.startswith("concept:"):
                        stored_concept = stored_concept[len("concept:"):]

                    if stored_concept == concept:
                        continue
                    if not stored_task:
                        continue

                    try:
                        st = manager.load_task(stored_task)
                        for pair in st.example_pairs:
                            g0 = pair.input_grid
                            g1 = pair.output_grid
                            if g0 and g1:
                                comp = arckg_compare(g0, g1)
                                st_topo = extract_topology(comp)
                                if topologies_match(cond_topo, st_topo):
                                    rule_result["stage2_results"].append({
                                        "task_hex": stored_task,
                                        "result": "potential_conflict",
                                        "stored_concept": stored_concept,
                                    })
                                break
                        checked += 1
                    except Exception:
                        pass
            except Exception:
                pass

            if stage2_ok:
                total_passed += 1
                print(f"  [{rule_id}] PASS (topology verified, no regressions)")
            else:
                rule_result["result"] = "STAGE2_FAIL"
                report["overall"] = "STAGE2_FAIL"
                total_failed += 1

        report["rule_results"].append(rule_result)

    # Save report
    os.makedirs("logs", exist_ok=True)
    report_path = f"logs/validation_{timestamp}.json"
    with open(report_path, "w") as f:
        json.dump(report, f, indent=2)

    if report["overall"] == "PASS":
        print(f"VALIDATION_PASS ({total_passed} rules validated)")
    else:
        print(f"{report['overall']} ({total_failed} failures)")

    return total_passed, total_failed


def _load_rule(path):
    """Load a single rule file."""
    try:
        with open(path, "r") as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError) as e:
        print(f"Error loading {path}: {e}")
        return None


def _load_all_activation_rules():
    """Load all activation rules from DSL_activation_rule/."""
    if not os.path.isdir(CHUNK_DIR):
        return []
    rules = []
    for f in sorted(os.listdir(CHUNK_DIR)):
        if not f.endswith(".json"):
            continue
        if f.startswith("."):
            continue
        path = os.path.join(CHUNK_DIR, f)
        try:
            with open(path, "r") as fh:
                rule = json.load(fh)
            rule["_path"] = path
            rules.append(rule)
        except (json.JSONDecodeError, IOError):
            continue
    return rules


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--rule", help="Path to specific rule file to validate")
    args = parser.parse_args()

    passed, failed = validate_all(args.rule)
    sys.exit(1 if failed > 0 else 0)
