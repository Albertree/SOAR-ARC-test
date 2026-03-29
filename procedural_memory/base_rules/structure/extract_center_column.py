"""extract_center_column -- keep only the center column, zero everything else."""

RULE_TYPE = "extract_center_column"
CATEGORY = "structure"


def try_rule(patterns, task):
    """Detect: output keeps only center column of input, rest is background."""
    pairs = task.example_pairs
    if not pairs:
        return None

    if not patterns.get("grid_size_preserved"):
        return None

    bg_color = None

    for pair in pairs:
        inp = pair.input_grid.raw
        out = pair.output_grid.raw
        h = len(inp)
        w = len(inp[0]) if inp else 0

        # Need odd width for a clear center
        if w % 2 == 0:
            return None

        center = w // 2

        # Determine background as 0 (most common in ARC) or most frequent
        # Check if all non-center columns are a single color
        non_center_vals = set()
        for r in range(h):
            for c in range(w):
                if c != center:
                    non_center_vals.add(out[r][c])
        if len(non_center_vals) != 1:
            return None
        bg = non_center_vals.pop()

        if bg_color is None:
            bg_color = bg
        elif bg_color != bg:
            return None

        # Center column must match input center column
        for r in range(h):
            if out[r][center] != inp[r][center]:
                return None

    return {
        "type": RULE_TYPE,
        "bg_color": bg_color,
        "confidence": 1.0,
    }


def apply_rule(rule, input_grid):
    """Keep only center column, fill rest with background."""
    raw = input_grid.raw
    h = len(raw)
    w = len(raw[0]) if raw else 0
    bg = rule["bg_color"]
    center = w // 2

    output = []
    for r in range(h):
        row = [bg] * w
        row[center] = raw[r][center]
        output.append(row)
    return output
