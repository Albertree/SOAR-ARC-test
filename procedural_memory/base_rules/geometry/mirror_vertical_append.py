"""mirror_vertical_append — output is input stacked on its vertical mirror."""

RULE_TYPE = "mirror_vertical_append"
CATEGORY = "geometry"


def try_rule(patterns, task):
    """Detect: output height = 2 * input height, bottom half is vertically flipped top half."""
    if not task or not task.example_pairs:
        return None

    for pair in task.example_pairs:
        g0 = pair.input_grid
        g1 = pair.output_grid
        if g0 is None or g1 is None:
            return None

        h0, w0 = g0.height, g0.width
        h1, w1 = g1.height, g1.width

        if h1 != 2 * h0 or w1 != w0:
            return None

        raw_in = g0.raw
        raw_out = g1.raw

        # Top half must equal input
        for r in range(h0):
            for c in range(w0):
                if raw_out[r][c] != raw_in[r][c]:
                    return None

        # Bottom half must be vertically flipped input
        for r in range(h0):
            for c in range(w0):
                if raw_out[h0 + r][c] != raw_in[h0 - 1 - r][c]:
                    return None

    return {
        "type": RULE_TYPE,
        "confidence": 1.0,
    }


def apply_rule(rule, input_grid):
    """Apply: stack input on its vertically flipped copy."""
    raw = input_grid.raw
    top = [row[:] for row in raw]
    bottom = [row[:] for row in reversed(raw)]
    return top + bottom
