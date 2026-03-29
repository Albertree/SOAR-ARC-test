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

def save_episode(fingerprint: dict, rule_type: str, rule_id: str = None,
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


def find_similar_episodes(fingerprint: dict, episodic_memory_root: str = EPISODIC_MEMORY_ROOT,
                          threshold: float = 0.7, max_results: int = 5) -> list:
    """
    Find episodes with similar fingerprints. Returns list of
    (episode, similarity_score) tuples, sorted by score descending.
    """
    episodes = load_episodes(episodic_memory_root)
    if not episodes:
        return []

    scored = []
    for ep in episodes:
        ep_fp = ep.get("fingerprint", {})
        # Skip same task
        if ep_fp.get("task_hex") == fingerprint.get("task_hex"):
            continue
        sim = fingerprint_similarity(fingerprint, ep_fp)
        if sim >= threshold:
            scored.append((ep, sim))

    scored.sort(key=lambda x: x[1], reverse=True)
    return scored[:max_results]
