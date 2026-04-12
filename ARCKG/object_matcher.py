"""
Object correspondence for SOAR pipeline.

ARCHITECTURE: Correspondence is a HYPOTHESIS. These functions produce comparison
candidates ordered by confidence — not ground truth. Color-changing tasks will have
zero color-based matches. That is expected and correct.

min_score=0.3 is conservative: at 5 match fields plus proximity bonus, a score of 0.3
means roughly 1 field matches plus some proximity. This allows position-based matching
to work on color-changing tasks where the color field contributes 0.
"""
from typing import List, Tuple
from ARCKG.object import Object


def match_score(obj_in: Object, obj_out: Object) -> float:
    """
    COMM/DIFF similarity score (0.0 to 1.0). Symmetric.
    0.7 weight on property match, 0.3 weight on positional proximity.
    to_json() is cached (T3.6) — O(1) after first call per object.
    """
    in_props = obj_in.to_json()
    out_props = obj_out.to_json()

    fields = ["area", "color", "size", "symmetry", "shape"]
    comm = sum(1 for f in fields if in_props.get(f) == out_props.get(f))

    in_pos = in_props.get("position", {}).get("left_top", {})
    out_pos = out_props.get("position", {}).get("left_top", {})
    if in_pos and out_pos:
        dr = abs(in_pos.get("row_index", 0) - out_pos.get("row_index", 0))
        dc = abs(in_pos.get("col_index", 0) - out_pos.get("col_index", 0))
        return (comm / len(fields)) * 0.7 + (1.0 / (1.0 + dr + dc)) * 0.3

    return comm / len(fields)


def build_match_matrix(
    input_objects: List[Object],
    output_objects: List[Object]
) -> List[List[float]]:
    """Returns |input| x |output| matrix of match_score values."""
    return [
        [match_score(i_obj, o_obj) for o_obj in output_objects]
        for i_obj in input_objects
    ]


def greedy_bipartite_match(
    input_objects: List[Object],
    output_objects: List[Object],
    min_score: float = 0.3
) -> Tuple[list, list, list]:
    """
    Greedy bipartite match by descending score.
    Returns (matched_pairs, unmatched_input, unmatched_output).
    """
    if not input_objects or not output_objects:
        return [], list(input_objects), list(output_objects)

    matrix = build_match_matrix(input_objects, output_objects)
    candidates = sorted(
        [(matrix[i][j], i, j)
         for i in range(len(input_objects))
         for j in range(len(output_objects))],
        key=lambda x: -x[0]
    )

    matched_in, matched_out = set(), set()
    matched_pairs = []

    for score, i, j in candidates:
        if score < min_score:
            break
        if i in matched_in or j in matched_out:
            continue
        matched_pairs.append((input_objects[i], output_objects[j]))
        matched_in.add(i)
        matched_out.add(j)

    return (
        matched_pairs,
        [o for k, o in enumerate(input_objects) if k not in matched_in],
        [o for k, o in enumerate(output_objects) if k not in matched_out],
    )


def match_objects(
    input_objects: List[Object],
    output_objects: List[Object]
) -> dict:
    """
    Returns a correspondence hypothesis dict. Caller is responsible for validation.
    Never hard-block on low match_confidence — it just means more uncertainty.
    """
    matched, unmatched_in, unmatched_out = greedy_bipartite_match(
        input_objects, output_objects
    )
    avg_conf = (
        sum(match_score(a, b) for a, b in matched) / len(matched)
        if matched else 0.0
    )
    return {
        "matched": matched,
        "added": unmatched_out,
        "deleted": unmatched_in,
        "score_matrix": build_match_matrix(input_objects, output_objects),
        "match_confidence": avg_conf,
    }
