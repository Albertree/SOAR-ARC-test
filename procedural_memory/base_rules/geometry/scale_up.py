"""scale_up — each cell scaled to NxN block (uniform upscaling)."""

RULE_TYPE = "scale_up"
CATEGORY = "geometry"


def try_rule(patterns, task):
    """Detect: output dimensions are integer multiples of input, each cell becomes a block."""
    if not task or not task.example_pairs:
        return None

    scale = None
    for pair in task.example_pairs:
        g0 = pair.input_grid
        g1 = pair.output_grid
        if g0 is None or g1 is None:
            return None

        h0, w0 = g0.height, g0.width
        h1, w1 = g1.height, g1.width

        if h1 == 0 or w1 == 0 or h0 == 0 or w0 == 0:
            return None
        if h1 % h0 != 0 or w1 % w0 != 0:
            return None

        sh = h1 // h0
        sw = w1 // w0
        if sh != sw or sh < 2:
            return None

        if scale is None:
            scale = sh
        elif scale != sh:
            return None

        # Verify every cell is uniformly scaled
        raw_in = g0.raw
        raw_out = g1.raw
        for r in range(h0):
            for c in range(w0):
                expected = raw_in[r][c]
                for dr in range(sh):
                    for dc in range(sw):
                        if raw_out[r * sh + dr][c * sw + dc] != expected:
                            return None

    if scale is None:
        return None

    return {
        "type": RULE_TYPE,
        "scale": scale,
        "confidence": 1.0,
    }


def apply_rule(rule, input_grid):
    """Apply scale_up: each cell becomes a scale x scale block."""
    raw = input_grid.raw
    scale = rule["scale"]
    h = len(raw)
    w = len(raw[0]) if raw else 0

    output = []
    for r in range(h):
        for _ in range(scale):
            row = []
            for c in range(w):
                row.extend([raw[r][c]] * scale)
            output.append(row)
    return output
