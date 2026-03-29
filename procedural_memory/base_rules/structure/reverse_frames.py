"""reverse_frames -- concentric rectangular frames get color order reversed."""

RULE_TYPE = "reverse_frames"
CATEGORY = "structure"


def try_rule(patterns, task):
    """Detect: square/rectangular concentric frames whose colors reverse in output."""
    pair_analyses = patterns.get("pair_analyses", [])
    if not pair_analyses or not patterns.get("grid_size_preserved"):
        return None

    for pair in task.example_pairs:
        raw_in = pair.input_grid.raw
        raw_out = pair.output_grid.raw
        h = len(raw_in)
        w = len(raw_in[0]) if raw_in else 0

        # Extract frame colors from input
        in_colors = _extract_frame_colors(raw_in)
        out_colors = _extract_frame_colors(raw_out)

        if in_colors is None or out_colors is None:
            return None
        if len(in_colors) < 2:
            return None
        if out_colors != list(reversed(in_colors)):
            return None

    return {
        "type": RULE_TYPE,
        "confidence": 1.0,
    }


def apply_rule(rule, input_grid):
    """Apply reverse_frames rule."""
    raw = input_grid.raw
    h = len(raw)
    w = len(raw[0]) if raw else 0

    frame_colors = _extract_frame_colors(raw)
    if frame_colors is None:
        return [row[:] for row in raw]

    reversed_colors = list(reversed(frame_colors))
    num_frames = len(frame_colors)

    output = [[0] * w for _ in range(h)]
    for f in range(num_frames):
        color = reversed_colors[f]
        for r in range(f, h - f):
            for c in range(f, w - f):
                # Only fill the frame border (outermost ring at depth f)
                if r == f or r == h - f - 1 or c == f or c == w - f - 1:
                    output[r][c] = color

    return output


def _extract_frame_colors(grid):
    """Extract colors of concentric rectangular frames from outside in.
    Returns list of colors [outer, ..., inner] or None if not concentric frames."""
    h = len(grid)
    w = len(grid[0]) if grid else 0
    if h == 0 or w == 0:
        return None

    colors = []
    max_depth = min(h, w) // 2 + (1 if min(h, w) % 2 == 1 else 0)

    for f in range(max_depth):
        # All cells on frame f should have same color
        frame_cells = set()
        for r in range(f, h - f):
            for c in range(f, w - f):
                if r == f or r == h - f - 1 or c == f or c == w - f - 1:
                    frame_cells.add(grid[r][c])

        if len(frame_cells) != 1:
            return None
        colors.append(frame_cells.pop())

    return colors
