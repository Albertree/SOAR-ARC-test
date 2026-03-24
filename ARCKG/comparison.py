"""
compare() — core relation generation function for the knowledge graph.
Takes two nodes or two relation results, returns a COMM/DIFF relation, and optionally saves it.

Relation file ID structure (nested dict, same pattern regardless of order):

  1st-order (node vs node):
    "id": {"id1": "T0a.P0.G0", "id2": "T0a.P0.G1"}

  2nd-order (1st-order relation vs 1st-order relation):
    "id": {
      "id1": {"id1": "T0a.P0.G0.O0", "id2": "T0a.P0.G0.O1"},
      "id2": {"id1": "T0a.P1.G0.O0", "id2": "T0a.P1.G0.O1"}
    }

  nth-order: id1/id2 values are (n-1)th-order id dicts, so they can be traced recursively.
"""

import json
import os

from ARCKG.memory_paths import id_pair_to_comparison_path, node_id_to_folder_path


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _is_relation_result(obj) -> bool:
    """Determine whether the object is a previous compare() return value — a dict with a "result" key."""
    return isinstance(obj, dict) and "result" in obj


def _id_to_edge_str(id_val) -> str:
    """
    Convert an id field (str or nested dict) to an edge string.
    Used for passing to id_pair_to_comparison_path() when computing the save path.

    e.g.) "T0a.P0.G0"                            -> "T0a.P0.G0"
          {"id1": "T0a.P0.G0", "id2": "T0a.P0.G1"}
                                                 -> "E_T0a.P0.G0-T0a.P0.G1"
          {"id1": {"id1": "G0.O0", "id2": "G0.O1"},
           "id2": {"id1": "G1.O0", "id2": "G1.O1"}}
                                                 -> "E_E_G0.O0-G0.O1-E_G1.O0-G1.O1"
    """
    if isinstance(id_val, str):
        return id_val
    return f"E_{_id_to_edge_str(id_val['id1'])}-{_id_to_edge_str(id_val['id2'])}"


def _compare_values(a, b) -> dict:
    """Recursively compare two values. Return value has {type, ...} structure."""
    if isinstance(a, dict) and isinstance(b, dict):
        return _compare_dicts(a, b)
    if isinstance(a, list) and isinstance(b, list):
        return _compare_lists(a, b)
    return _compare_scalars(a, b)


def _compare_lists(a: list, b: list) -> dict:
    """Compare two lists.
    - 2D (nested lists): element-wise exact comparison (row/column order preserved)
    - 1D: order-preserving exact comparison
    """
    if len(a) != len(b):
        return {"type": "DIFF", "comp1": a, "comp2": b}

    is_2d = any(isinstance(item, list) for item in a) or any(isinstance(item, list) for item in b)
    if is_2d:
        for row_a, row_b in zip(a, b):
            if not isinstance(row_a, list) or not isinstance(row_b, list):
                if row_a != row_b:
                    return {"type": "DIFF", "comp1": a, "comp2": b}
                continue
            if len(row_a) != len(row_b):
                return {"type": "DIFF", "comp1": a, "comp2": b}
            for va, vb in zip(row_a, row_b):
                if va != vb:
                    return {"type": "DIFF", "comp1": a, "comp2": b}
        return {"type": "COMM", "comp1": a, "comp2": b}
    else:
        t = "COMM" if a == b else "DIFF"
        return {"type": t, "comp1": a, "comp2": b}


def _compare_scalars(a, b) -> dict:
    """
    INTENT: Compare two scalar values and return a COMM/DIFF result.
            At scalar leaves, comp1 and comp2 values are also included in the result.
    MUST NOT: Do not send list or dict types to this function.
    REF: CLAUDE.md § Relation result format
    """
    if a is None and b is None:
        return {"type": "COMM", "comp1": a, "comp2": b}
    if type(a) != type(b):
        return {"type": "DIFF", "comp1": a, "comp2": b}
    return {"type": "COMM" if a == b else "DIFF", "comp1": a, "comp2": b}


def _compare_dicts(a: dict, b: dict) -> dict:
    """
    INTENT: Recursively perform comparison for each key of two dicts
            and build the category structure.
    MUST NOT: Do not ignore cases where key sets differ — missing keys are also treated as DIFF.
    REF: CLAUDE.md § Relation result format
    """
    all_keys = sorted(set(a.keys()) | set(b.keys()), key=str)
    if not all_keys:
        return {"type": "COMM", "score": "0/0", "category": {}}

    category: dict = {}
    for key in all_keys:
        has_a = key in a
        has_b = key in b
        if not has_a:
            category[key] = {"type": "DIFF", "comp1": None, "comp2": b[key]}
        elif not has_b:
            category[key] = {"type": "DIFF", "comp1": a[key], "comp2": None}
        else:
            category[key] = _compare_values(a[key], b[key])

    comm = sum(1 for v in category.values() if v.get("type") == "COMM")
    total = len(category)
    overall = "COMM" if comm == total else "DIFF"
    return {
        "type": overall,
        "score": f"{comm}/{total}",
        "category": category,
    }


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def compare(a, b, save: bool = False, semantic_memory_root: str = None) -> dict:
    """
    INTENT: Compare two KG nodes (or previous compare results) and return a relation result dict
            of the form {"id": {...}, "result": {"type": "COMM|DIFF", "score": "n/total", "category": {...}}}.

            The id field is recursively nested according to the order:
              1st-order: id = {"id1": str, "id2": str}
              2nd-order: id = {"id1": {1st-order id dict}, "id2": {1st-order id dict}}
              nth-order: id = {"id1": {(n-1)th-order id dict}, "id2": {(n-1)th-order id dict}}

            Only writes E_*-*.json to the filesystem according to LCA rules when save=True.
    MUST NOT: Do not use save=True as the default — risk of creating tens of thousands of files.
              Do not perform cross-layer comparisons (e.g., directly comparing GRID and PIXEL).
    REF: CLAUDE.md § Knowledge Graph Architecture, § Edge Creation Timing
         ARCKG/memory_paths.py id_pair_to_comparison_path()
    """
    if _is_relation_result(a) and _is_relation_result(b):
        # 2nd-order or higher: compare the result of two compare result dicts
        raw = _compare_dicts(a["result"], b["result"])
        result = {
            "type": raw["type"],
            "score": raw.get("score", "0/0"),
            "category": raw.get("category", {}),
        }
        # id nests each input relation's id as-is
        id_dict = {
            "id1": a.get("id"),
            "id2": b.get("id"),
        }
        comparison = {"id": id_dict, "result": result}

        if save and semantic_memory_root is not None:
            edge_a = _id_to_edge_str(a.get("id"))
            edge_b = _id_to_edge_str(b.get("id"))
            path = id_pair_to_comparison_path(edge_a, edge_b, semantic_memory_root)
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, "w") as f:
                json.dump(comparison, f, indent=2)

        return comparison

    # 1st-order: KG node comparison — compare to_json() property dicts
    props_a = a.to_json()
    props_b = b.to_json()
    raw = _compare_dicts(props_a, props_b)
    result = {
        "type": raw["type"],
        "score": raw.get("score", "0/0"),
        "category": raw.get("category", {}),
    }
    id_a = getattr(a, "node_id", None)
    id_b = getattr(b, "node_id", None)
    id_dict = {"id1": id_a, "id2": id_b}
    comparison = {"id": id_dict, "result": result}

    if save and semantic_memory_root is not None and id_a and id_b:
        path = id_pair_to_comparison_path(id_a, id_b, semantic_memory_root)
        folder = os.path.dirname(path)
        if folder:
            os.makedirs(folder, exist_ok=True)
        with open(path, "w") as f:
            json.dump(comparison, f, indent=2)

    return comparison
