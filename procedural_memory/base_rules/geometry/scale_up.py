"""scale_up — output is input scaled by an integer factor (each cell becomes NxN block)."""

RULE_TYPE = "scale_up"
CATEGORY = "geometry"


def try_rule(patterns, task):
    """Detect: output dimensions are integer multiples of input, with uniform cell scaling."""
    pairs = task.example_pairs
    if not pairs:
        return None

    scale = None

    for pair in pairs:
        inp = pair.input_grid.raw
        out = pair.output_grid.raw
        h_in = len(inp)
        w_in = len(inp[0]) if inp else 0
        h_out = len(out)
        w_out = len(out[0]) if out else 0

        if h_in == 0 or w_in == 0:
            return None
        if h_out % h_in != 0 or w_out % w_in != 0:
            return None

        sy = h_out // h_in
        sx = w_out // w_in
        if sy != sx or sy < 2:
            return None

        if scale is None:
            scale = sy
        elif scale != sy:
            return None

        # Verify every input cell maps to a uniform block
        for r in range(h_in):
            for c in range(w_in):
                val = inp[r][c]
                for dr in range(scale):
                    for dc in range(scale):
                        if out[r * scale + dr][c * scale + dc] != val:
                            return None

    return {
        "type": RULE_TYPE,
        "scale": scale,
        "confidence": 1.0,
    }


def apply_rule(rule, input_grid):
    """Scale each cell into an NxN block."""
    raw = input_grid.raw
    s = rule["scale"]
    h = len(raw)
    w = len(raw[0]) if raw else 0

    output = []
    for r in range(h):
        for dr in range(s):
            row = []
            for c in range(w):
                row.extend([raw[r][c]] * s)
            output.append(row)
    return output
