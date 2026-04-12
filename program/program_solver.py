"""
Per-pair program solver.

Given (input_grid_raw, output_grid_raw), finds a program from existing concepts
that transforms input to output exactly. Returns a Program (list of resolved
steps) or None.
"""
from procedural_memory.base_rules._concept_engine import (
    _ensure_loaded, _concepts, _execute_concept, _INFER_METHODS,
    _extract_arckg_features, _brute_force_resolve, _signature_matches
)


def make_program(concept_id, resolved_params, concept):
    """Build a concrete program from a concept + resolved params."""
    steps = []
    for step in concept.get("steps", []):
        resolved_args = {}
        for k, v in step.get("args", {}).items():
            if isinstance(v, str) and v.startswith("$"):
                ref = v[1:]
                if ref == "input":
                    resolved_args[k] = "$input"
                elif ref in resolved_params:
                    resolved_args[k] = resolved_params[ref]
                else:
                    # Check if it's an output reference from a prior step
                    resolved_args[k] = v
            else:
                resolved_args[k] = v
        steps.append({
            "primitive": step["primitive"],
            "args": resolved_args,
            "output": step.get("output", "result"),
        })
    return {
        "concept_id": concept_id,
        "params": resolved_params,
        "steps": steps,
    }


def solve_pair(input_raw, output_raw, task):
    """
    Find a program from existing concepts that transforms input_raw to output_raw.
    Uses the REAL task for parameter inference (cross-pair consistency) but
    validates only against this specific pair's output.
    """
    _ensure_loaded()

    try:
        arckg_features = _extract_arckg_features(task)
    except Exception:
        arckg_features = {
            "size_comm": True, "color_comm": True, "contents_comm": True,
            "height_ratios": [], "width_ratios": [],
            "colors_added": [], "colors_removed": [],
            "comm_scores": [], "diff_fields": [],
        }

    for concept in _concepts:
        sig = concept.get("signature", {})
        if not _signature_matches(sig, arckg_features, {}):
            continue

        params = {}
        all_resolved = True
        brute_force_params = []

        for pname, pdef in concept.get("parameters", {}).items():
            infer = pdef.get("infer")
            if infer and infer != "from_examples":
                fn = _INFER_METHODS.get(infer)
                if fn:
                    val = fn(task, arckg_features, {})
                    if val is not None:
                        params[pname] = val
                        continue
            if pdef.get("default") is not None:
                params[pname] = pdef["default"]
                continue
            if infer == "from_examples":
                brute_force_params.append((pname, pdef))
                continue
            all_resolved = False
            break

        if not all_resolved:
            continue

        # Cap brute force to 1 param in per-pair mode (speed)
        if len(brute_force_params) > 1:
            continue

        if brute_force_params:
            resolved = _brute_force_resolve(concept, params, brute_force_params, task)
            if resolved is None:
                continue
            params.update(resolved)

        # Validate against THIS specific pair only
        try:
            result = _execute_concept(concept, params, input_raw)
            if result == output_raw:
                return make_program(concept["concept_id"], params, concept)
        except Exception:
            continue

    return None


def solve_all_pairs(task):
    """Solve every training pair independently. Returns list of (pair_idx, program_or_None)."""
    results = []
    for i, pair in enumerate(task.example_pairs):
        if pair.input_grid is None or pair.output_grid is None:
            results.append((i, None))
            continue
        prog = solve_pair(pair.input_grid.raw, pair.output_grid.raw, task)
        results.append((i, prog))
    return results
