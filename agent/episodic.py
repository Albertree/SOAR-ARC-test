"""
episodic — Case-Based Reasoning via structural fingerprints.

Implements episodic memory for the SOAR agent:
  1. compute_fingerprint(task) — generate a symbolic structural summary
  2. save_episode(fingerprint, ...) — store solved episode to episodic_memory/
  3. load_episodes(...) — load all stored episodes
  4. find_similar_episodes(fingerprint, ...) — retrieve similar past tasks
  5. fingerprint_similarity(a, b) — symbolic similarity metric (no embeddings)

All matching is purely symbolic: boolean flags, integer counts, and COMM ratios.
No neural networks or embeddings are used.
"""

import json
import os
from datetime import datetime

from ARCKG.comparison import compare as arckg_compare

EPISODIC_MEMORY_ROOT = "episodic_memory"


# ======================================================================
# Topology extraction and matching (used by chunking + validation)
# ======================================================================

def extract_topology(comp_result: dict, patterns: dict = None) -> dict:
    """
    Extract a COMM/DIFF topology dict from an ARCKG comparison result.

    Args:
        comp_result: the "result" dict from ARCKG compare(), containing
                     {"type": "COMM|DIFF", "score": "n/total", "category": {...}}
        patterns: optional wm.s1["patterns"] data from ExtractPatternOperator.
                  When provided and contents is DIFF, enriches with sub-fields.

    Returns:
        dict mapping each category key to "COMM" or "DIFF" (flat fields)
        or to a nested dict with sub-structure (enriched contents field).
    """
    if not comp_result or not isinstance(comp_result, dict):
        return {}

    category = comp_result.get("category", {})
    if not category:
        return {}

    topology = {}
    for key, val in category.items():
        if isinstance(val, dict):
            topology[key] = val.get("type", "DIFF")
        else:
            topology[key] = "COMM" if val == "COMM" else "DIFF"

    # Enrich contents with pattern-derived sub-fields
    if topology.get("contents") == "DIFF" and patterns:
        topology["contents"] = _enrich_contents_topology(patterns)

    return topology


def _enrich_contents_topology(patterns: dict) -> dict:
    """Derive rich sub-structure for the contents DIFF field from pattern data."""
    pair_analyses = patterns.get("pair_analyses", [])
    if not pair_analyses:
        return {"type": "DIFF"}

    change_pattern = _detect_change_pattern(pair_analyses)
    change_scope = _detect_change_scope(pair_analyses)

    group_counts = [a.get("num_groups", 0) for a in pair_analyses]
    num_groups_consistent = len(set(group_counts)) <= 1

    group_anchors_consistent = _detect_group_anchors_consistent(pair_analyses)

    return {
        "type": "DIFF",
        "change_pattern": change_pattern,
        "change_scope": change_scope,
        "num_groups_consistent": num_groups_consistent,
        "group_anchors_consistent": group_anchors_consistent,
    }


def _detect_change_pattern(pair_analyses: list) -> str:
    """Detect spatial pattern of changes. Priority: column_wise > row_wise > single_group > multi_group > scattered."""
    if not pair_analyses:
        return "scattered"

    all_column = True
    all_row = True
    all_single = True
    all_multi = True

    for pa in pair_analyses:
        groups = pa.get("groups", [])
        n = pa.get("num_groups", len(groups))

        if n != 1:
            all_single = False
        if n <= 1:
            all_multi = False

        for g in groups:
            cc = g.get("cell_count", 0)
            if cc <= 1:
                continue  # single cell is trivially both column and row
            min_col = g.get("min_col", g.get("top_col", 0))
            max_col = g.get("max_col", min_col)
            min_row = g.get("min_row", g.get("top_row", 0))
            max_row = g.get("max_row", min_row)

            # Column-wise: all cells share one column AND contiguous vertical strip
            if min_col != max_col or cc != (max_row - min_row + 1):
                all_column = False
            # Row-wise: all cells share one row AND contiguous horizontal strip
            if min_row != max_row or cc != (max_col - min_col + 1):
                all_row = False

    if all_column:
        return "column_wise"
    if all_row:
        return "row_wise"
    if all_single:
        return "single_group"
    if all_multi:
        return "multi_group"
    return "scattered"


def _detect_change_scope(pair_analyses: list) -> str:
    """Detect scope of changes: all_cells, single_object, or subset."""
    if not pair_analyses:
        return "subset"

    for pa in pair_analyses:
        total = pa.get("total_changes", 0)
        groups = pa.get("groups", [])
        n_groups = pa.get("num_groups", len(groups))

        # Estimate grid area from bounding box of all changed cells
        if groups:
            max_r = max(g.get("max_row", g.get("top_row", 0)) for g in groups)
            max_c = max(g.get("max_col", g.get("top_col", 0)) for g in groups)
            estimated_area = (max_r + 1) * (max_c + 1)
            if estimated_area > 0 and total > 0.8 * estimated_area:
                continue  # this pair looks like all_cells, check others
            elif n_groups == 1:
                return "single_object"
            else:
                return "subset"
        else:
            return "subset"

    return "all_cells"


def _detect_group_anchors_consistent(pair_analyses: list) -> bool:
    """Check if group anchor positions (top_row, top_col) are the same across all pairs."""
    if len(pair_analyses) < 2:
        return True

    anchor_sets = []
    for pa in pair_analyses:
        anchors = frozenset(
            (g.get("top_row", 0), g.get("top_col", 0))
            for g in pa.get("groups", [])
        )
        anchor_sets.append(anchors)

    return all(s == anchor_sets[0] for s in anchor_sets[1:])


def topologies_match(topo_a: dict, topo_b: dict) -> bool:
    """
    Strict structural equality: same field names, same COMM/DIFF values.
    """
    if not topo_a or not topo_b:
        return False
    if set(topo_a.keys()) != set(topo_b.keys()):
        return False
    return all(topo_a[k] == topo_b[k] for k in topo_a)


def topologies_match_with_vars(pattern: dict, concrete: dict) -> bool:
    """Match a pattern topology (may contain ?var_N / ?hedge_N) against concrete.

    Variable fields (?var_N) match any COMM/DIFF value.
    Hedge fields (?hedge_N) are ignored in matching.
    Non-variable fields must match exactly.
    """
    if not pattern or not concrete:
        return False
    # Non-hedge keys in pattern must exist in concrete
    pattern_keys = {k for k in pattern if not str(k).startswith("?")}
    concrete_keys = set(concrete.keys())
    if pattern_keys != concrete_keys:
        return False
    for k in pattern_keys:
        pv = pattern[k]
        cv = concrete.get(k)
        if cv is None:
            return False
        if isinstance(pv, str) and pv.startswith("?"):
            continue  # variable matches any value
        if isinstance(pv, dict) and isinstance(cv, dict):
            if not topologies_match_with_vars(pv, cv):
                return False
        elif pv != cv:
            return False
    return True


def topology_similarity(topo_a: dict, topo_b: dict) -> float:
    """
    Soft similarity: fraction of fields in the union that agree on COMM/DIFF.
    Returns 0.0–1.0. Identical topologies score 1.0.
    """
    all_keys = set(topo_a.keys()) | set(topo_b.keys())
    if not all_keys:
        return 0.0
    matches = sum(1 for k in all_keys if topo_a.get(k) == topo_b.get(k))
    return matches / len(all_keys)


def structural_similarity(comp_result_a: dict, comp_result_b: dict) -> float:
    """Recursive category dict comparison. Preserves nesting unlike topology_similarity.
    Returns 0.0-1.0. Identical structures → 1.0."""
    if not comp_result_a or not comp_result_b:
        return 0.0

    cat_a = comp_result_a.get("category", {})
    cat_b = comp_result_b.get("category", {})

    if not cat_a or not cat_b:
        ta = comp_result_a.get("type")
        tb = comp_result_b.get("type")
        return 1.0 if ta == tb else 0.0

    all_keys = set(cat_a.keys()) | set(cat_b.keys())
    if not all_keys:
        return 0.0

    score = 0.0
    for k in all_keys:
        va = cat_a.get(k)
        vb = cat_b.get(k)
        if va is None or vb is None:
            continue
        ta = va.get("type") if isinstance(va, dict) else str(va)
        tb = vb.get("type") if isinstance(vb, dict) else str(vb)
        if ta != tb:
            continue
        if (isinstance(va, dict) and isinstance(vb, dict)
                and "category" in va and "category" in vb):
            score += 0.5 + 0.5 * structural_similarity(va, vb)
        else:
            score += 1.0

    return score / len(all_keys)


def _episode_bucket_key(topology: dict) -> str:
    """Coarse pre-filter key: (size_preserved, color_preserved)."""
    size_comm = topology.get("size", "COMM") == "COMM"
    color_comm = topology.get("color", "COMM") == "COMM"
    return f"s{int(size_comm)}c{int(color_comm)}"


def build_episode_index(episodes: list) -> dict:
    """Bucket index for O(1) pre-filtering in retrieval."""
    index = {}
    for ep in episodes:
        topo = ep.get("topology")
        if not topo or isinstance(topo, str):
            continue
        key = _episode_bucket_key(topo)
        index.setdefault(key, []).append(ep)
    return index


# ======================================================================
# Fingerprint computation
# ======================================================================

def compute_fingerprint(task) -> dict:
    """
    Generate a lightweight structural fingerprint from a task's example pairs.
    Uses ARCKG compare() for COMM/DIFF scores and basic grid properties.
    Does NOT store the actual grid contents — only structural summaries.
    """
    input_sizes = []
    output_sizes = []
    input_color_sets = []
    output_color_sets = []
    comm_scores = []
    n_input_objects = []
    n_output_objects = []

    for pair in task.example_pairs:
        g0 = pair.input_grid
        g1 = pair.output_grid
        if g0 is None or g1 is None:
            continue

        raw_in = g0.raw
        raw_out = g1.raw

        # Grid dimensions
        h_in, w_in = len(raw_in), len(raw_in[0]) if raw_in else 0
        h_out, w_out = len(raw_out), len(raw_out[0]) if raw_out else 0
        input_sizes.append([h_in, w_in])
        output_sizes.append([h_out, w_out])

        # Color sets (non-zero)
        in_colors = set()
        for row in raw_in:
            for c in row:
                if c != 0:
                    in_colors.add(c)
        out_colors = set()
        for row in raw_out:
            for c in row:
                if c != 0:
                    out_colors.add(c)
        input_color_sets.append(sorted(in_colors))
        output_color_sets.append(sorted(out_colors))

        # ARCKG COMM/DIFF score
        try:
            comparison = arckg_compare(g0, g1)
            score_str = comparison.get("result", {}).get("score", "0/0")
            comm_scores.append(score_str)
        except Exception:
            comm_scores.append("0/0")

        # Object count (simple connected components — background-excluded, 4-connected)
        n_in = _count_objects(raw_in)
        n_out = _count_objects(raw_out)
        n_input_objects.append(n_in)
        n_output_objects.append(n_out)

    # Aggregate
    grid_size_preserved = all(
        i == o for i, o in zip(input_sizes, output_sizes)
    ) if input_sizes else False

    size_ratios = []
    for (hi, wi), (ho, wo) in zip(input_sizes, output_sizes):
        area_in = hi * wi if hi * wi > 0 else 1
        area_out = ho * wo
        size_ratios.append(round(area_out / area_in, 2))

    # Color dynamics
    all_in_colors = set()
    all_out_colors = set()
    for cs in input_color_sets:
        all_in_colors.update(cs)
    for cs in output_color_sets:
        all_out_colors.update(cs)
    colors_added = bool(all_out_colors - all_in_colors)
    colors_removed = bool(all_in_colors - all_out_colors)

    # Object count dynamics
    obj_preserved = all(
        i == o for i, o in zip(n_input_objects, n_output_objects)
    ) if n_input_objects else False

    # Overall COMM ratio
    total_comm = 0
    total_fields = 0
    for s in comm_scores:
        parts = s.split("/")
        if len(parts) == 2:
            try:
                total_comm += int(parts[0])
                total_fields += int(parts[1])
            except ValueError:
                pass
    overall_comm_ratio = round(total_comm / max(total_fields, 1), 3)

    # Finer-grained features for better discrimination
    # Average input grid size bucket: small (<7), medium (7-15), large (>15)
    avg_in_area = sum(h * w for h, w in input_sizes) / max(len(input_sizes), 1) if input_sizes else 0
    if avg_in_area < 49:
        size_bucket = "small"
    elif avg_in_area <= 225:
        size_bucket = "medium"
    else:
        size_bucket = "large"

    # Color count change direction
    in_cc = [len(cs) for cs in input_color_sets]
    out_cc = [len(cs) for cs in output_color_sets]
    avg_in_cc = sum(in_cc) / max(len(in_cc), 1) if in_cc else 0
    avg_out_cc = sum(out_cc) / max(len(out_cc), 1) if out_cc else 0
    if avg_out_cc > avg_in_cc + 0.5:
        color_count_change = "increase"
    elif avg_out_cc < avg_in_cc - 0.5:
        color_count_change = "decrease"
    else:
        color_count_change = "same"

    # Object count change direction
    avg_in_obj = sum(n_input_objects) / max(len(n_input_objects), 1) if n_input_objects else 0
    avg_out_obj = sum(n_output_objects) / max(len(n_output_objects), 1) if n_output_objects else 0
    if avg_out_obj > avg_in_obj + 0.5:
        object_count_change = "increase"
    elif avg_out_obj < avg_in_obj - 0.5:
        object_count_change = "decrease"
    else:
        object_count_change = "same"

    # Size ratio bucket
    avg_ratio = sum(size_ratios) / max(len(size_ratios), 1) if size_ratios else 1.0
    if abs(avg_ratio - 1.0) < 0.01:
        ratio_bucket = "1:1"
    elif avg_ratio > 3.5:
        ratio_bucket = "large_growth"
    elif avg_ratio > 1.5:
        ratio_bucket = "moderate_growth"
    elif avg_ratio < 0.3:
        ratio_bucket = "large_shrink"
    elif avg_ratio < 0.7:
        ratio_bucket = "moderate_shrink"
    else:
        ratio_bucket = "slight_change"

    return {
        "task_hex": task.task_hex,
        "n_example_pairs": len(task.example_pairs),
        "n_test_pairs": len(task.test_pairs),
        "grid_size_preserved": grid_size_preserved,
        "input_sizes": input_sizes,
        "output_sizes": output_sizes,
        "size_ratios": size_ratios,
        "size_bucket": size_bucket,
        "ratio_bucket": ratio_bucket,
        "input_color_counts": [len(cs) for cs in input_color_sets],
        "output_color_counts": [len(cs) for cs in output_color_sets],
        "colors_added": colors_added,
        "colors_removed": colors_removed,
        "color_count_change": color_count_change,
        "n_input_objects": n_input_objects,
        "n_output_objects": n_output_objects,
        "object_count_preserved": obj_preserved,
        "object_count_change": object_count_change,
        "comm_scores": comm_scores,
        "overall_comm_ratio": overall_comm_ratio,
    }


def _count_objects(raw) -> int:
    """Count non-background connected components (4-connected). Lightweight, no hodel import."""
    h = len(raw)
    w = len(raw[0]) if raw else 0
    if h == 0 or w == 0:
        return 0

    # Find background color (most frequent)
    counts = {}
    for row in raw:
        for c in row:
            counts[c] = counts.get(c, 0) + 1
    bg = max(counts, key=counts.get)

    visited = set()
    n_objects = 0
    for r in range(h):
        for c in range(w):
            if raw[r][c] == bg or (r, c) in visited:
                continue
            # BFS flood fill
            n_objects += 1
            queue = [(r, c)]
            while queue:
                pr, pc = queue.pop(0)
                if (pr, pc) in visited:
                    continue
                if pr < 0 or pr >= h or pc < 0 or pc >= w:
                    continue
                if raw[pr][pc] == bg:
                    continue
                visited.add((pr, pc))
                for dr, dc in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                    nb = (pr + dr, pc + dc)
                    if nb not in visited:
                        queue.append(nb)
    return n_objects


# ======================================================================
# Episode storage
# ======================================================================

def build_structural_key(wm, rule_type: str, concept_id: str = None) -> dict:
    """Build structural_key from working memory state after pipeline solve.

    Contains only relational topology (COMM/DIFF strings) — no concrete
    color values, size integers, or raw grid contents.
    """
    comparisons = wm.s1.get("comparisons", {})

    # Extract topology from first comparison
    # WM stores: comparisons[key] = {"spec": ..., "result": <full compare output>}
    # Full compare output = {"id": ..., "result": {"type": ..., "category": ...}}
    topology = {}
    score_num, score_den = 0, 0
    for _key, comp in comparisons.items():
        full_compare = comp.get("result", {})
        inner_result = full_compare.get("result", {})
        wm_patterns = wm.s1.get("patterns")
        topology = extract_topology(inner_result, patterns=wm_patterns)
        score_str = inner_result.get("score", "0/0")
        parts = score_str.split("/")
        if len(parts) == 2:
            try:
                score_num = int(parts[0])
                score_den = int(parts[1])
            except ValueError:
                pass
        break  # use first comparison

    pairs_processed = len(comparisons)

    return {
        "comparison_pattern": {
            "level": "GRID",
            "topology": topology,
            "score_numerator": score_num,
            "score_denominator": score_den,
        },
        "impasse_state": {
            "impasse_at_level": "GRID",
            "failed_operators": [],
            "pairs_processed": pairs_processed,
        },
        "resolution": {
            "descent_to": None,
            "object_topology": None,
            "dsl_fired": concept_id or rule_type,
            "dsl_param_source": None,
        },
    }


def save_episode(fingerprint: dict, rule_type: str, rule_id: str = None,
                 structural_key: dict = None,
                 episodic_memory_root: str = EPISODIC_MEMORY_ROOT) -> str:
    """Save a solved task's fingerprint + rule reference to episodic_memory/."""
    os.makedirs(episodic_memory_root, exist_ok=True)

    existing = [
        f for f in os.listdir(episodic_memory_root)
        if f.startswith("episode_") and f.endswith(".json")
    ]

    # Don't save duplicate episodes for the same task
    task_hex = fingerprint.get("task_hex", "")
    for f in existing:
        try:
            path = os.path.join(episodic_memory_root, f)
            with open(path, "r") as fh:
                stored = json.load(fh)
            if stored.get("fingerprint", {}).get("task_hex") == task_hex:
                return path  # already stored
        except (json.JSONDecodeError, IOError):
            continue

    next_id = len(existing) + 1
    episode = {
        "id": next_id,
        "fingerprint": fingerprint,
        "structural_key": structural_key,
        "solved_with_rule": rule_type,
        "rule_id": rule_id,
        "created_at": datetime.now().isoformat(),
    }

    filename = f"episode_{next_id:03d}.json"
    path = os.path.join(episodic_memory_root, filename)
    with open(path, "w") as f:
        json.dump(episode, f, indent=2)

    return path


def load_episodes(episodic_memory_root: str = EPISODIC_MEMORY_ROOT) -> list:
    """Load all stored episodes from episodic_memory/."""
    if not os.path.isdir(episodic_memory_root):
        return []

    episodes = []
    for f in sorted(os.listdir(episodic_memory_root)):
        if not (f.startswith("episode_") and f.endswith(".json")):
            continue
        path = os.path.join(episodic_memory_root, f)
        try:
            with open(path, "r") as fh:
                episode = json.load(fh)
            episode["_path"] = path
            episodes.append(episode)
        except (json.JSONDecodeError, IOError):
            continue

    return episodes


def load_solution_episodes(episodic_memory_root: str = EPISODIC_MEMORY_ROOT) -> list:
    """Load episodes from the structured solutions/ folder (new format)."""
    solutions_dir = os.path.join(episodic_memory_root, "solutions")
    if not os.path.isdir(solutions_dir):
        return []
    episodes = []
    try:
        task_dirs = os.listdir(solutions_dir)
    except OSError:
        return []
    for task_hex in task_dirs:
        sol_path = os.path.join(solutions_dir, task_hex, "solution.json")
        if not os.path.exists(sol_path):
            continue
        try:
            with open(sol_path) as f:
                sol = json.load(f)
            episode = {
                "fingerprint": {"task_hex": sol["task_hex"]},
                "solved_with_rule": (
                    f"concept:{sol['concept_id']}"
                    if sol.get("concept_id")
                    else sol.get("method", "unknown")
                ),
                "topology": sol.get("topology"),
                "source": "solutions_folder",
                "_sol": sol,
            }
            episodes.append(episode)
        except (json.JSONDecodeError, IOError, KeyError):
            continue
    return episodes


# ======================================================================
# Similarity-based retrieval
# ======================================================================

def fingerprint_similarity(a: dict, b: dict) -> float:
    """
    Compute symbolic similarity between two fingerprints.
    Returns a score between 0.0 (completely different) and 1.0 (structurally identical).
    All comparisons are discrete — no embeddings.
    """
    score = 0.0
    total = 0.0

    # Grid size preserved (high weight — most discriminative)
    total += 3.0
    if a.get("grid_size_preserved") == b.get("grid_size_preserved"):
        score += 3.0

    # Size ratio bucket (more discriminative than raw ratio)
    total += 3.0
    if a.get("ratio_bucket") == b.get("ratio_bucket"):
        score += 3.0

    # Grid size bucket
    total += 2.0
    if a.get("size_bucket") == b.get("size_bucket"):
        score += 2.0

    # Color dynamics — added/removed
    total += 2.0
    if a.get("colors_added") == b.get("colors_added"):
        score += 1.0
    if a.get("colors_removed") == b.get("colors_removed"):
        score += 1.0

    # Color count change direction
    total += 2.0
    if a.get("color_count_change") == b.get("color_count_change"):
        score += 2.0

    # Object count change direction
    total += 3.0
    if a.get("object_count_change") == b.get("object_count_change"):
        score += 3.0

    # COMM ratio similarity
    total += 2.0
    comm_a = a.get("overall_comm_ratio", 0)
    comm_b = b.get("overall_comm_ratio", 0)
    if abs(comm_a - comm_b) < 0.1:
        score += 2.0
    elif abs(comm_a - comm_b) < 0.2:
        score += 1.0

    # Input color count similarity
    total += 1.0
    cc_a = a.get("input_color_counts", [])
    cc_b = b.get("input_color_counts", [])
    if cc_a and cc_b:
        avg_cc_a = sum(cc_a) / len(cc_a)
        avg_cc_b = sum(cc_b) / len(cc_b)
        if abs(avg_cc_a - avg_cc_b) <= 1:
            score += 1.0

    # Number of example pairs
    total += 1.0
    if a.get("n_example_pairs") == b.get("n_example_pairs"):
        score += 1.0

    return score / max(total, 1.0)


def find_similar_episodes(fingerprint: dict, topology: dict = None,
                          episodic_memory_root: str = EPISODIC_MEMORY_ROOT,
                          threshold: float = 0.7, max_results: int = 5) -> list:
    """
    Find episodes similar to the current task using 4-tier lookup:
      Tier 0: structural similarity > 0.85 on full comparison result (HINTS ONLY)
      Tier 1: exact topology match (structural_key)
      Tier 2: partial topology match (topology_similarity > 0.5)
      Tier 3: fingerprint fallback
    Returns list of (episode, similarity_score) tuples.
    """
    old_episodes = load_episodes(episodic_memory_root)
    solution_eps = load_solution_episodes(episodic_memory_root)

    # Deduplicate: same task_hex → solution_folder wins (richer record)
    dedup: dict = {}
    for ep in old_episodes:
        key = ep.get("fingerprint", {}).get("task_hex")
        if key:
            dedup[key] = ep
    for ep in solution_eps:
        key = ep.get("fingerprint", {}).get("task_hex")
        if key:
            dedup[key] = ep

    all_episodes = list(dedup.values())

    task_hex = fingerprint.get("task_hex")
    all_episodes = [ep for ep in all_episodes
                    if ep.get("fingerprint", {}).get("task_hex") != task_hex]

    if not all_episodes:
        return []

    # Tier 0: Structural similarity on full comparison result (HINTS ONLY)
    if topology and isinstance(topology, dict):
        struct_matches = []
        for ep in all_episodes:
            ep_topo = ep.get("topology")
            if ep_topo and isinstance(ep_topo, dict):
                sim = structural_similarity(topology, ep_topo)
                if sim > 0.85:
                    struct_matches.append((ep, sim))
        if struct_matches:
            struct_matches.sort(key=lambda x: -x[1])
            return struct_matches[:max_results]

    # Tier 1: exact topology match
    if topology:
        exact = []
        for ep in all_episodes:
            sk = ep.get("structural_key") or {}
            ep_topo = sk.get("comparison_pattern", {}).get("topology", {})
            if ep_topo and topologies_match(topology, ep_topo):
                exact.append((ep, 1.0))
        if exact:
            exact.sort(key=lambda x: x[0].get("structural_key", {})
                       .get("comparison_pattern", {})
                       .get("score_denominator", 0), reverse=True)
            return exact[:max_results]

    # Tier 2: partial topology match
    if topology:
        partial = []
        for ep in all_episodes:
            sk = ep.get("structural_key") or {}
            ep_topo = sk.get("comparison_pattern", {}).get("topology", {})
            if ep_topo:
                sim = topology_similarity(topology, ep_topo)
                if sim > 0.5:
                    partial.append((ep, sim))
        if partial:
            partial.sort(key=lambda x: x[1], reverse=True)
            return partial[:max_results]

    # Tier 3: fingerprint fallback
    scored = []
    for ep in all_episodes:
        ep_fp = ep.get("fingerprint", {})
        sim = fingerprint_similarity(fingerprint, ep_fp)
        if sim >= threshold:
            scored.append((ep, sim))

    scored.sort(key=lambda x: x[1], reverse=True)
    return scored[:max_results]
