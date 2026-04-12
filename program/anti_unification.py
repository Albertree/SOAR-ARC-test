"""
Anti-unification over ARCKG comparison result trees.

Implements Plotkin's term-graph anti-unification adapted for COMM/DIFF trees.
The result of anti_unify(r0, r1) is a pattern where:
- Fields with identical COMM/DIFF status are preserved
- Disagreements are replaced with ?var_N variables
"""


def anti_unify(r0: dict, r1: dict) -> dict:
    """Anti-unify two ARCKG comparison results."""
    def _get_result(r):
        if "result" in r and "id" in r:
            return r["result"]
        if "type" in r or "category" in r:
            return r
        return r

    var_counter = [0]
    return _au_result_dicts(_get_result(r0), _get_result(r1), var_counter)


def _au_result_dicts(r0: dict, r1: dict, var_counter: list) -> dict:
    if not r0 or not r1:
        return {}
    result = {}

    t0 = r0.get("type", "")
    t1 = r1.get("type", "")
    if t0 == t1:
        result["type"] = t0
    else:
        var_counter[0] += 1
        result["type"] = f"?var_{var_counter[0]}"

    s0 = r0.get("score", "")
    s1 = r1.get("score", "")
    result["score"] = s0 if s0 == s1 else "?"

    cat0 = r0.get("category", {})
    cat1 = r1.get("category", {})
    if cat0 or cat1:
        result["category"] = _au_category_dicts(cat0, cat1, var_counter)

    return result


def _au_category_dicts(cat0: dict, cat1: dict, var_counter: list) -> dict:
    all_keys = set(cat0.keys()) | set(cat1.keys())
    result = {}

    for key in sorted(all_keys):
        v0 = cat0.get(key)
        v1 = cat1.get(key)

        if v0 is None or v1 is None:
            var_counter[0] += 1
            result[key] = {"type": f"?hedge_{var_counter[0]}"}
            continue

        if isinstance(v0, dict) and isinstance(v1, dict):
            result[key] = _au_nodes(v0, v1, var_counter)
        elif v0 == v1:
            result[key] = v0
        else:
            var_counter[0] += 1
            result[key] = f"?var_{var_counter[0]}"

    return result


def _au_nodes(n0, n1, var_counter: list):
    if not isinstance(n0, dict) or not isinstance(n1, dict):
        if n0 == n1:
            return n0
        var_counter[0] += 1
        return f"?var_{var_counter[0]}"

    t0 = n0.get("type", "")
    t1 = n1.get("type", "")

    if t0 != t1:
        var_counter[0] += 1
        return {"type": f"?var_{var_counter[0]}"}

    result = {"type": t0}

    for field in ("comp1", "comp2"):
        c0 = n0.get(field)
        c1 = n1.get(field)
        if c0 is not None or c1 is not None:
            if c0 == c1:
                result[field] = c0
            else:
                var_counter[0] += 1
                result[field] = f"?var_{var_counter[0]}"

    sub0 = n0.get("category", {})
    sub1 = n1.get("category", {})
    if sub0 or sub1:
        result["category"] = _au_category_dicts(sub0, sub1, var_counter)

    s0 = n0.get("score")
    s1 = n1.get("score")
    if s0 is not None and s0 == s1:
        result["score"] = s0

    return result


def anti_unify_pairs(comparison_results: list) -> dict:
    """Anti-unify a list of comparison results. Returns most specific common pattern."""
    if not comparison_results:
        return {}
    if len(comparison_results) == 1:
        return comparison_results[0]

    result = comparison_results[-1]
    for r in reversed(comparison_results[:-1]):
        result = anti_unify(r, result)
    return result


def extract_invariants(pattern: dict) -> dict:
    """Extract discriminative invariant features from an anti-unified pattern.

    Returns dict with:
    - top_level: {field: COMM/DIFF} for top-level category fields
    - variable_count: total ?var_N and ?hedge_N in pattern (lower = more consistent)
    - sub_fields: nested sub-field patterns that are concrete (no variables)
    - comm_fields / diff_fields: sorted lists of top-level field names
    """
    def _count_variables(obj) -> int:
        if isinstance(obj, str):
            return 1 if obj.startswith("?") else 0
        if isinstance(obj, dict):
            return sum(_count_variables(v) for v in obj.values())
        if isinstance(obj, list):
            return sum(_count_variables(v) for v in obj)
        return 0

    def _is_concrete(val) -> bool:
        return _count_variables(val) == 0

    def _extract_type(val) -> str:
        if isinstance(val, str):
            return val
        if isinstance(val, dict):
            return val.get("type", "?")
        return str(val)

    inner = pattern
    if "result" in pattern and "id" in pattern:
        inner = pattern["result"]
    cat = inner.get("category", {}) if isinstance(inner, dict) else {}

    top_level = {}
    sub_fields = {}
    comm_fields = []
    diff_fields = []

    for field, val in cat.items():
        if not isinstance(val, dict):
            continue
        t = val.get("type", "")
        if isinstance(t, str) and t.startswith("?"):
            continue
        top_level[field] = t
        if t == "COMM":
            comm_fields.append(field)
        elif t == "DIFF":
            diff_fields.append(field)

        sub_cat = val.get("category", {})
        if sub_cat and isinstance(sub_cat, dict):
            sub_level = {}
            for sf, sv in sub_cat.items():
                if not _is_concrete(sv):
                    continue
                st = _extract_type(sv)
                if not st.startswith("?"):
                    sub_level[sf] = st
            if sub_level:
                sub_fields[field] = sub_level

        score = val.get("score")
        if score and isinstance(score, str) and not score.startswith("?") and "/" in score:
            sub_fields.setdefault(field, {})["score"] = score

    return {
        "top_level": top_level,
        "variable_count": _count_variables(pattern),
        "sub_fields": sub_fields,
        "comm_fields": sorted(comm_fields),
        "diff_fields": sorted(diff_fields),
    }
