"""recolor_by_size -- connected components recolored by descending size rank."""
from procedural_memory.base_rules._helpers import find_components

RULE_TYPE = "recolor_by_size"
CATEGORY = "color"


def try_rule(patterns, task):
    """Detect: single non-bg color's components are recolored 1,2,3,... by size descending."""
    pairs = task.example_pairs
    if not pairs:
        return None

    if not patterns.get("grid_size_preserved"):
        return None

    source_color = None

    for pair in pairs:
        inp = pair.input_grid.raw
        out = pair.output_grid.raw
        h = len(inp)
        w = len(inp[0]) if inp else 0

        # Find non-background colors in input (background = most common color)
        color_counts = {}
        for r in range(h):
            for c in range(w):
                color_counts[inp[r][c]] = color_counts.get(inp[r][c], 0) + 1
        bg = max(color_counts, key=color_counts.get)

        # Find the single non-bg color
        non_bg = set(color_counts.keys()) - {bg}
        if len(non_bg) != 1:
            return None
        src = non_bg.pop()

        if source_color is None:
            source_color = src
        elif source_color != src:
            return None

        # Find connected components of source color
        comps = find_components(inp, src)
        if not comps:
            return None

        # Check that background cells are unchanged
        for r in range(h):
            for c in range(w):
                if inp[r][c] == bg and out[r][c] != bg:
                    return None

        # Map each component to its output color (should be uniform per component)
        comp_colors = []
        for comp in comps:
            out_colors = set(out[r][c] for r, c in comp)
            if len(out_colors) != 1:
                return None
            comp_colors.append((len(comp), out_colors.pop()))

        # Group by size, check each size maps to one color
        size_to_color = {}
        for size, color in comp_colors:
            if size in size_to_color:
                if size_to_color[size] != color:
                    return None
            else:
                size_to_color[size] = color

        # Colors should be sequential starting from 1, assigned by descending size
        sorted_sizes = sorted(size_to_color.keys(), reverse=True)
        for i, sz in enumerate(sorted_sizes):
            if size_to_color[sz] != i + 1:
                return None

    return {
        "type": RULE_TYPE,
        "source_color": source_color,
        "confidence": 1.0,
    }


def apply_rule(rule, input_grid):
    """Recolor components by descending size: largest->1, next->2, etc."""
    raw = input_grid.raw
    h = len(raw)
    w = len(raw[0]) if raw else 0
    src = rule["source_color"]

    comps = find_components(raw, src)
    if not comps:
        return [row[:] for row in raw]

    # Get distinct sizes sorted descending
    sizes = sorted(set(len(c) for c in comps), reverse=True)
    size_to_color = {sz: i + 1 for i, sz in enumerate(sizes)}

    output = [row[:] for row in raw]
    for comp in comps:
        new_color = size_to_color[len(comp)]
        for r, c in comp:
            output[r][c] = new_color

    return output
