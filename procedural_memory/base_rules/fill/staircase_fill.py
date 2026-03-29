"""staircase_fill — 1-row input with colored prefix grows into a descending staircase."""

RULE_TYPE = "staircase_fill"
CATEGORY = "fill"


def try_rule(patterns, task):
    """Detect: input is 1 row, output rows increase colored count by 1 each row."""
    pairs = task.example_pairs
    if not pairs:
        return None

    for pair in pairs:
        inp = pair.input_grid.raw
        out = pair.output_grid.raw
        h_in = len(inp)
        w = len(inp[0]) if inp else 0

        if h_in != 1 or w == 0:
            return None

        # Find the non-zero color and initial count
        row = inp[0]
        color = None
        count = 0
        for c in range(w):
            if row[c] != 0:
                if color is None:
                    color = row[c]
                elif row[c] != color:
                    return None
                count += 1
            elif count > 0:
                # All colored cells must be a prefix
                for c2 in range(c, w):
                    if row[c2] != 0:
                        return None
                break

        if color is None or count == 0:
            return None

        h_out = len(out)
        w_out = len(out[0]) if out else 0
        if w_out != w:
            return None

        # Verify staircase pattern: row i has (count + i) colored cells
        for r in range(h_out):
            expected_count = count + r
            if expected_count > w:
                return None
            for c in range(expected_count):
                if out[r][c] != color:
                    return None
            for c in range(expected_count, w):
                if out[r][c] != 0:
                    return None

        # Verify number of rows: last row should have count + h_out - 1 colored cells
        # and that should be <= w
        expected_last = count + h_out - 1
        if expected_last > w:
            return None

    return {
        "type": RULE_TYPE,
        "confidence": 1.0,
    }


def apply_rule(rule, input_grid):
    """Build staircase from 1-row input."""
    raw = input_grid.raw
    row = raw[0]
    w = len(row)

    # Find color and initial count
    color = None
    count = 0
    for c in range(w):
        if row[c] != 0:
            if color is None:
                color = row[c]
            count += 1
        else:
            break

    # Number of output rows: width / 2 (observed pattern)
    # Actually: output rows = w - count - (count - 1) ... let me derive from examples
    # w=6,count=2 -> rows=3; w=8,count=1 -> rows=4; w=10,count=3 -> rows=5
    # w=6,count=4 -> rows=3; w=6,count=1 -> rows=3
    # Pattern: rows = w // 2
    num_rows = w // 2

    output = []
    for r in range(num_rows):
        n = count + r
        if n > w:
            n = w
        output.append([color] * n + [0] * (w - n))
    return output
