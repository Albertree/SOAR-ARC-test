"""mirror_vertical_append -- output is input stacked with its vertical flip."""

RULE_TYPE = "mirror_vertical_append"
CATEGORY = "geometry"


def try_rule(patterns, task):
    """Detect: output height = 2 * input height, top = input, bottom = rows reversed."""
    pairs = task.example_pairs
    if not pairs:
        return None

    for pair in pairs:
        inp = pair.input_grid.raw
        out = pair.output_grid.raw
        h_in = len(inp)
        w_in = len(inp[0]) if inp else 0
        h_out = len(out)
        w_out = len(out[0]) if out else 0

        # Output must be exactly double height, same width
        if h_out != 2 * h_in or w_out != w_in:
            return None

        # Top half must equal input
        for r in range(h_in):
            if out[r] != inp[r]:
                return None

        # Bottom half must equal input rows reversed
        for r in range(h_in):
            if out[h_in + r] != inp[h_in - 1 - r]:
                return None

    return {
        "type": RULE_TYPE,
        "confidence": 1.0,
    }


def apply_rule(rule, input_grid):
    """Stack input with its vertically flipped copy."""
    raw = input_grid.raw
    top = [row[:] for row in raw]
    bottom = [row[:] for row in reversed(raw)]
    return top + bottom
