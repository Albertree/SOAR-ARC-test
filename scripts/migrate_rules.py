"""
One-time migration: convert old-format stored rules (concept_id + concrete params)
to new format (concept_id only). Removes duplicates — keeps the entry with highest
times_reused. Preserves non-concept rules unchanged. Re-numbers sequentially.
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

PROC_ROOT = "procedural_memory"


def main():
    rule_files = sorted(
        f for f in os.listdir(PROC_ROOT)
        if f.startswith("rule_") and f.endswith(".json")
    )
    if not rule_files:
        print("No stored rules found — migration is a no-op.")
        return

    all_entries = []
    for fname in rule_files:
        path = os.path.join(PROC_ROOT, fname)
        with open(path) as f:
            entry = json.load(f)
        all_entries.append((path, entry))

    seen_concept_ids = {}
    to_delete = []

    for path, entry in all_entries:
        rule = entry.get("rule", {})
        if rule.get("type", "").startswith("concept:"):
            cid = rule.get("concept_id")
            if cid is None:
                continue
            entry["rule"] = {
                "type": rule["type"],
                "concept_id": cid,
                "confidence": rule.get("confidence", 1.0),
            }
            reused = entry.get("times_reused", 0)
            if cid not in seen_concept_ids:
                seen_concept_ids[cid] = (path, entry, reused)
            else:
                _, _, existing_reused = seen_concept_ids[cid]
                if reused > existing_reused:
                    to_delete.append(seen_concept_ids[cid][0])
                    seen_concept_ids[cid] = (path, entry, reused)
                else:
                    to_delete.append(path)

    for path, entry in all_entries:
        if path not in to_delete:
            with open(path, "w") as f:
                json.dump(entry, f, indent=2)

    for path in to_delete:
        os.remove(path)
        print(f"Removed duplicate: {path}")

    remaining = sorted(
        f for f in os.listdir(PROC_ROOT)
        if f.startswith("rule_") and f.endswith(".json")
    )
    for i, fname in enumerate(remaining, 1):
        old_path = os.path.join(PROC_ROOT, fname)
        new_fname = f"rule_{i:03d}.json"
        new_path = os.path.join(PROC_ROOT, new_fname)
        if old_path != new_path:
            os.rename(old_path, new_path)

    print(f"Migration complete: {len(remaining)} rules, {len(to_delete)} duplicates removed.")


if __name__ == "__main__":
    main()
