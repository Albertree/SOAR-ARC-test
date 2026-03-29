"""staircase_fill -- 1-row colored prefix expands into descending staircase triangle."""

RULE_TYPE = "staircase_fill"
CATEGORY = "fill"


def try_rule(patterns, task):
    """Detect: 1-row input, output grows rows; each row adds 1 more colored cell."""
    if not patterns.get("pair_analyses"):
        return None

    for pair in task.example_pairs:
        raw_in = pair.input_grid.raw
        raw_out = pair.output_grid.raw
        h_in = len(raw_in)
        w_in = len(raw_in[0]) if raw_in else 0

        if h_in != 1:
            return None

        # Count colored prefix
        color = None
        prefix_len = 0
        for c in range(w_in):
            if raw_in[0][c] != 0:
                if color is None:
                    color = raw_in[0][c]
                elif raw_in[0][c] != color:
                    return None
                prefix_len += 1
            else:
                break

        if prefix_len == 0 or color is None:
            return None

        # Expected output: w//2 rows, each row i has (prefix_len + i) colored cells
        h_out = len(raw_out)
        expected_h = w_in // 2
        if h_out != expected_h:
            return None

        # Verify staircase pattern
        for r in range(h_out):
            fill_count = prefix_len + r
            for c in range(w_in):
                expected = color if c < fill_count else 0
                if raw_out[r][c] != expected:
                    return None

    return {
        "type": RULE_TYPE,
        "confidence": 1.0,
    }


def apply_rule(rule, input_grid):
    """Apply staircase_fill rule."""
    raw = input_grid.raw
    w = len(raw[0]) if raw else 0

    # Find color and prefix length
    color = None
    prefix_len = 0
    for c in range(w):
        if raw[0][c] != 0:
            if color is None:
                color = raw[0][c]
            prefix_len += 1
        else:
            break

    if color is None:
        return [row[:] for row in raw]

    h_out = w // 2
    output = []
    for r in range(h_out):
        fill_count = prefix_len + r
        row = [color if c < fill_count else 0 for c in range(w)]
        output.append(row)

    return output
