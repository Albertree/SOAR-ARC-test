"""Validate concept JSONs for structural and semantic correctness."""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def main():
    concepts_dir = os.path.join("procedural_memory", "concepts")
    if not os.path.isdir(concepts_dir):
        print("No concepts directory found.")
        return 0

    # Load available primitives and inference methods
    try:
        from procedural_memory.base_rules import _primitives as P
        from procedural_memory.base_rules._concept_engine import _INFER_METHODS
    except ImportError as e:
        print(f"Cannot import engine modules: {e}", file=sys.stderr)
        return 1

    errors = []
    checked = 0

    for fname in sorted(os.listdir(concepts_dir)):
        if not fname.endswith(".json"):
            continue
        path = os.path.join(concepts_dir, fname)
        checked += 1
        try:
            with open(path) as f:
                concept = json.load(f)
        except (json.JSONDecodeError, IOError) as e:
            errors.append(f"{fname}: invalid JSON — {e}")
            continue

        # Required top-level keys
        for key in ("concept_id", "signature", "steps", "result"):
            if key not in concept:
                errors.append(f"{fname}: missing required key '{key}'")

        # Validate each step's primitive
        for i, step in enumerate(concept.get("steps", [])):
            prim = step.get("primitive")
            if prim and not hasattr(P, prim):
                errors.append(f"{fname}: step {i} references unknown primitive '{prim}'")

        # Validate parameter inference methods
        for pname, pdef in concept.get("parameters", {}).items():
            infer = pdef.get("infer")
            if infer and infer not in _INFER_METHODS:
                errors.append(f"{fname}: parameter '{pname}' uses unknown infer method '{infer}'")

    if errors:
        print(f"Concept validation FAILED ({len(errors)} error(s) in {checked} concept(s)):")
        for e in errors:
            print(f"  - {e}")
        return 1

    print(f"Concept validation passed ({checked} concept(s) checked).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
