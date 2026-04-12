"""
Anti-unification over programs (lists of resolved steps).

Given two programs that each solve one training pair, finds the most specific
generalization that subsumes both. Variables replace concrete values that differ.
"""


def _hashable(v):
    if isinstance(v, dict):
        return tuple(sorted((_hashable(k), _hashable(val)) for k, val in v.items()))
    if isinstance(v, list):
        return tuple(_hashable(x) for x in v)
    return v


def au_values(v0, v1, state):
    """Anti-unify two values with coreference tracking."""
    if v0 == v1:
        return v0
    pair_key = (_hashable(v0), _hashable(v1))
    if pair_key in state["solved"]:
        return state["solved"][pair_key]
    state["counter"] += 1
    var = f"?var_{state['counter']}"
    state["solved"][pair_key] = var
    return var


def au_args(args0, args1, state):
    """Anti-unify two argument dicts."""
    all_keys = sorted(set(args0.keys()) | set(args1.keys()))
    result = {}
    for k in all_keys:
        v0 = args0.get(k)
        v1 = args1.get(k)
        if v0 is None or v1 is None:
            state["counter"] += 1
            result[k] = f"?hedge_{state['counter']}"
        else:
            result[k] = au_values(v0, v1, state)
    return result


def au_steps(steps0, steps1, state):
    """Anti-unify two step lists. Returns None on structural mismatch."""
    if len(steps0) != len(steps1):
        return None
    result = []
    for s0, s1 in zip(steps0, steps1):
        if s0["primitive"] != s1["primitive"]:
            return None
        merged = {
            "primitive": s0["primitive"],
            "args": au_args(s0["args"], s1["args"], state),
            "output": s0["output"],
        }
        result.append(merged)
    return result


def au_programs(prog0, prog1):
    """Anti-unify two programs. Returns template with ?var_N placeholders or None."""
    if prog0 is None or prog1 is None:
        return None
    state = {"counter": 0, "solved": {}}
    merged = au_steps(prog0["steps"], prog1["steps"], state)
    if merged is None:
        return None

    variables = []
    def _collect(obj):
        if isinstance(obj, str) and obj.startswith("?") and obj not in variables:
            variables.append(obj)
        elif isinstance(obj, dict):
            for v in obj.values():
                _collect(v)
        elif isinstance(obj, list):
            for v in obj:
                _collect(v)
    for step in merged:
        _collect(step["args"])

    return {
        "concept_id_a": prog0.get("concept_id", "?"),
        "concept_id_b": prog1.get("concept_id", "?"),
        "steps": merged,
        "variables": variables,
        "variable_count": len(variables),
    }


def au_program_list(programs):
    """Anti-unify a list of programs. Folds left."""
    programs = [p for p in programs if p is not None]
    if not programs:
        return None
    if len(programs) == 1:
        return {
            "concept_id_a": programs[0].get("concept_id", "?"),
            "concept_id_b": programs[0].get("concept_id", "?"),
            "steps": programs[0]["steps"],
            "variables": [],
            "variable_count": 0,
        }
    result = au_programs(programs[0], programs[1])
    if result is None:
        return None
    for prog in programs[2:]:
        current = {"concept_id": result["concept_id_a"], "steps": result["steps"], "params": {}}
        result = au_programs(current, prog)
        if result is None:
            return None
    return result
