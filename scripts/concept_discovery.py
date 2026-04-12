#!/usr/bin/env python3
"""
Concept discovery from solved program templates.

Groups solved tasks by primitive sequence, runs AU merge or template-to-concept
conversion, validates, and saves new concepts.

Usage:
    python scripts/concept_discovery.py           # run discovery
    python scripts/concept_discovery.py --dry-run  # show what would be generated
"""
import os
import sys
import json
import argparse
from collections import Counter

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def load_program_records():
    sol_dir = "episodic_memory/solutions"
    if not os.path.isdir(sol_dir):
        return []
    records = []
    for task_hex in os.listdir(sol_dir):
        prog_path = os.path.join(sol_dir, task_hex, "program.json")
        if not os.path.exists(prog_path):
            continue
        try:
            with open(prog_path) as f:
                rec = json.load(f)
            if rec.get("au_template") and rec.get("all_pairs_solved"):
                records.append(rec)
        except (json.JSONDecodeError, IOError):
            pass
    return records


def primitive_sequence(template):
    return tuple(s["primitive"] for s in template.get("steps", []))


def concept_exists(concept_id):
    return os.path.exists(f"procedural_memory/concepts/{concept_id}.json")


def validate_on_tasks(concept, task_hexes):
    from procedural_memory.base_rules._concept_engine import (
        _ensure_loaded, _validate_concept, _extract_arckg_features,
        _INFER_METHODS, _brute_force_resolve
    )
    from managers.arc_manager import ARCManager
    _ensure_loaded()
    manager = ARCManager()
    passed = []
    for task_hex in task_hexes:
        try:
            t = manager.load_task(task_hex)
            feats = _extract_arckg_features(t)
            params = {}
            ok = True
            brute = []
            for pn, pd in concept.get("parameters", {}).items():
                inf = pd.get("infer")
                if inf and inf != "from_examples":
                    fn = _INFER_METHODS.get(inf)
                    if fn:
                        v = fn(t, feats, {})
                        if v is not None:
                            params[pn] = v
                            continue
                if pd.get("default") is not None:
                    params[pn] = pd["default"]
                    continue
                if pd.get("infer") == "from_examples":
                    brute.append((pn, pd))
                    continue
                ok = False
                break
            if not ok:
                continue
            if brute:
                res = _brute_force_resolve(concept, params, brute, t)
                if res is None:
                    continue
                params.update(res)
            valid, _ = _validate_concept(concept, params, t, verbose=True)
            if valid:
                passed.append(task_hex)
        except Exception:
            pass
    return passed


def run_discovery(dry_run=False):
    records = load_program_records()
    print(f"Program records with AU templates: {len(records)}")

    groups = {}
    for rec in records:
        seq = primitive_sequence(rec["au_template"])
        groups.setdefault(seq, []).append(rec)

    print(f"Primitive sequence groups: {len(groups)}")
    for seq, recs in sorted(groups.items(), key=lambda x: -len(x[1])):
        tasks = [r["task_hex"] for r in recs]
        print(f"  {seq}: {len(recs)} tasks — {tasks}")

    if dry_run:
        return

    # Check if claude CLI is available
    import shutil
    if not shutil.which("claude"):
        print("[DISCOVERY] claude CLI not found in PATH — skipping")
        return

    from program.claude_au import template_to_concept_json, au_merge_with_claude

    concepts_dir = "procedural_memory/concepts"
    os.makedirs(concepts_dir, exist_ok=True)
    generated = []

    for seq, recs in groups.items():
        task_hexes = [r["task_hex"] for r in recs]

        if len(recs) >= 2:
            print(f"\nMerging {len(recs)} templates for {seq}...")
            concept = au_merge_with_claude(
                recs[0]["au_template"], recs[1]["au_template"], task_hexes
            )
        else:
            print(f"\nConverting template for {task_hexes[0]}, {seq}...")
            pair_progs = [p["program"] for p in recs[0].get("pair_programs", []) if p.get("program")]
            concept = template_to_concept_json(recs[0]["au_template"], task_hexes[0], pair_progs)

        if concept is None:
            print(f"  Claude returned None — skipping")
            continue

        cid = concept.get("concept_id", "")
        if not cid:
            print(f"  No concept_id — skipping")
            continue
        if concept_exists(cid):
            print(f"  {cid} already exists — skipping")
            continue

        passed = validate_on_tasks(concept, task_hexes)
        print(f"  {cid}: validates on {len(passed)}/{len(task_hexes)} tasks")

        if not passed:
            print(f"  Rejected — validates on 0 tasks")
            continue

        path = os.path.join(concepts_dir, f"{cid}.json")
        with open(path, "w") as f:
            json.dump(concept, f, indent=2)
        print(f"  Saved: {path}")
        generated.append(cid)

    print(f"\nGenerated: {len(generated)} concepts")
    return generated


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    run_discovery(dry_run=args.dry_run)
