"""recolor_by_size -- objects of single source color recolored by descending size rank."""
from procedural_memory.base_rules._helpers import find_components

RULE_TYPE = "recolor_by_size"
CATEGORY = "color"


def try_rule(patterns, task):
    """Detect: all non-bg cells are one color; objects recolored 1,2,3,... by size descending."""
    pair_analyses = patterns.get("pair_analyses", [])
    if not pair_analyses or not patterns.get("grid_size_preserved"):
        return None

    source_color = None
    for pair in task.example_pairs:
        raw = pair.input_grid.raw
        bg = _bg(raw)
        non_bg = set()
        for row in raw:
            for v in row:
                if v != bg:
                    non_bg.add(v)
        if len(non_bg) != 1:
            return None
        sc = non_bg.pop()
        if source_color is None:
            source_color = sc
        elif source_color != sc:
            return None

    # Check output: objects ranked by size descending → colors 1,2,3,...
    for pair in task.example_pairs:
        raw_in = pair.input_grid.raw
        raw_out = pair.output_grid.raw
        bg = _bg(raw_in)
        comps = find_components(raw_in, source_color)
        if not comps:
            return None

        # Group by size
        size_groups = {}
        for comp in comps:
            sz = len(comp)
            if sz not in size_groups:
                size_groups[sz] = []
            size_groups[sz].append(comp)

        sorted_sizes = sorted(size_groups.keys(), reverse=True)

        for rank, sz in enumerate(sorted_sizes):
            expected_color = rank + 1
            for comp in size_groups[sz]:
                for r, c in comp:
                    if raw_out[r][c] != expected_color:
                        return None

    return {
        "type": RULE_TYPE,
        "source_color": source_color,
        "confidence": 1.0,
    }


def apply_rule(rule, input_grid):
    """Apply recolor_by_size rule."""
    raw = input_grid.raw
    source_color = rule["source_color"]
    bg = _bg(raw)

    comps = find_components(raw, source_color)
    if not comps:
        return [row[:] for row in raw]

    # Group by size, rank descending
    size_groups = {}
    for comp in comps:
        sz = len(comp)
        if sz not in size_groups:
            size_groups[sz] = []
        size_groups[sz].append(comp)

    sorted_sizes = sorted(size_groups.keys(), reverse=True)

    output = [row[:] for row in raw]
    for rank, sz in enumerate(sorted_sizes):
        new_color = rank + 1
        for comp in size_groups[sz]:
            for r, c in comp:
                output[r][c] = new_color

    return output


def _bg(grid):
    counts = {}
    for row in grid:
        for v in row:
            counts[v] = counts.get(v, 0) + 1
    return max(counts, key=counts.get)
