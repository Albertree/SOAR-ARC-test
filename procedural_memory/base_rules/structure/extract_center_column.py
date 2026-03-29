"""extract_center_column -- keep only the center column, fill rest with background.

Pattern: output preserves the center column (index = width // 2) of the input
and fills every other cell with background color (0). Grid size is preserved.
The center column must have at least one non-bg cell.

Category: structure tasks that extract a single spatial feature.
"""

RULE_TYPE = "extract_center_column"
CATEGORY = "structure"


def _bg(grid):
    counts = {}
    for row in grid:
        for v in row:
            counts[v] = counts.get(v, 0) + 1
    return max(counts, key=counts.get)


def try_rule(patterns, task):
    """Detect: output = center column of input, rest filled with bg."""
    if not patterns.get("grid_size_preserved"):
        return None

    bg = None
    for pair in task.example_pairs:
        raw_in = pair.input_grid.raw
        raw_out = pair.output_grid.raw
        h = len(raw_in)
        w = len(raw_in[0]) if raw_in else 0

        if w == 0:
            return None

        b = _bg(raw_out)
        if bg is None:
            bg = b
        elif bg != b:
            return None

        center = w // 2

        # Check center column preserved
        for r in range(h):
            if raw_out[r][center] != raw_in[r][center]:
                return None

        # Check all other cells are bg
        for r in range(h):
            for c in range(w):
                if c != center and raw_out[r][c] != bg:
                    return None

        # Center column must have at least one non-bg value
        if all(raw_in[r][center] == bg for r in range(h)):
            return None

    return {
        "type": RULE_TYPE,
        "bg": bg,
        "confidence": 1.0,
    }


def apply_rule(rule, input_grid):
    """Apply extract_center_column: keep center column, fill rest with bg."""
    raw = input_grid.raw
    h = len(raw)
    w = len(raw[0]) if raw else 0
    bg = rule["bg"]
    center = w // 2

    output = [[bg] * w for _ in range(h)]
    for r in range(h):
        output[r][center] = raw[r][center]
    return output
