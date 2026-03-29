"""recolor_sequential -- objects recolored 1,2,3,... by position."""
from procedural_memory.base_rules._helpers import group_positions

RULE_TYPE = "recolor_sequential"
CATEGORY = "color"


def try_rule(patterns, task):
    """Detect pattern: change groups have one source color, output colors are sequential."""
    pair_analyses = patterns.get("pair_analyses", [])
    if not pair_analyses or not patterns.get("grid_size_preserved"):
        return None

    group_counts = [a["num_groups"] for a in pair_analyses]
    if len(set(group_counts)) != 1 or group_counts[0] == 0:
        return None

    all_source_colors = set()

    for analysis in pair_analyses:
        for g in analysis["groups"]:
            if len(g["input_colors"]) != 1 or len(g["output_colors"]) != 1:
                return None
            all_source_colors.add(g["input_colors"][0])

        out_colors = sorted(set(g["output_colors"][0] for g in analysis["groups"]))
        expected = list(range(min(out_colors), min(out_colors) + len(out_colors)))
        if out_colors != expected:
            return None

    for sort_key in ["top_row", "top_col"]:
        if _check_sort_key(pair_analyses, sort_key):
            start_color = min(
                g["output_colors"][0]
                for g in pair_analyses[0]["groups"]
            )
            return {
                "type": RULE_TYPE,
                "sort_key": sort_key,
                "start_color": start_color,
                "source_colors": sorted(all_source_colors),
                "confidence": 1.0,
            }

    return None


def apply_rule(rule, input_grid):
    """Apply recolor_sequential rule to input grid."""
    raw = input_grid.raw
    height = len(raw)
    width = len(raw[0]) if raw else 0
    sort_key = rule["sort_key"]
    start_color = rule["start_color"]
    source_colors = set(rule.get("source_colors", []))

    target_cells = []
    for r in range(height):
        for c in range(width):
            if raw[r][c] in source_colors:
                target_cells.append((r, c))

    if not target_cells:
        return [row[:] for row in raw]

    groups = group_positions(target_cells)

    def _sort_val(group):
        if sort_key == "top_row":
            return min(r for r, c in group)
        if sort_key == "top_col":
            return min(c for r, c in group)
        return 0

    sorted_groups = sorted(groups, key=_sort_val)

    output = [row[:] for row in raw]
    for idx, group in enumerate(sorted_groups):
        new_color = start_color + idx
        for r, c in group:
            output[r][c] = new_color

    return output


def _check_sort_key(pair_analyses, sort_key):
    """Verify that sorting groups by sort_key produces sequential output colors."""
    for analysis in pair_analyses:
        groups = analysis["groups"]
        sorted_groups = sorted(groups, key=lambda g: g[sort_key])
        colors = [g["output_colors"][0] for g in sorted_groups]
        if colors != list(range(colors[0], colors[0] + len(colors))):
            return False
    return True
