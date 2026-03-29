"""reverse_frames — concentric rectangular frames have their colors reversed."""

RULE_TYPE = "reverse_frames"
CATEGORY = "structure"


def _extract_frame_colors(grid):
    """Extract colors of concentric rectangular frames from outside in.
    Returns list of colors or None if grid doesn't have concentric frame structure."""
    h = len(grid)
    w = len(grid[0]) if grid else 0
    if h == 0 or w == 0:
        return None

    colors = []
    layer = 0
    while True:
        r1, c1 = layer, layer
        r2, c2 = h - 1 - layer, w - 1 - layer
        if r1 > r2 or c1 > c2:
            break

        # Get the color of this frame
        color = grid[r1][c1]
        colors.append(color)

        # Verify all cells in this frame have the same color
        # Top and bottom rows
        for c in range(c1, c2 + 1):
            if grid[r1][c] != color or grid[r2][c] != color:
                return None
        # Left and right columns
        for r in range(r1, r2 + 1):
            if grid[r][c1] != color or grid[r][c2] != color:
                return None

        layer += 1

    return colors


def try_rule(patterns, task):
    """Detect: input and output have concentric frames with reversed color order."""
    pairs = task.example_pairs
    if not pairs:
        return None

    if not patterns.get("grid_size_preserved"):
        return None

    for pair in pairs:
        inp = pair.input_grid.raw
        out = pair.output_grid.raw

        in_colors = _extract_frame_colors(inp)
        out_colors = _extract_frame_colors(out)

        if in_colors is None or out_colors is None:
            return None
        if len(in_colors) != len(out_colors):
            return None
        if out_colors != list(reversed(in_colors)):
            return None

    return {
        "type": RULE_TYPE,
        "confidence": 1.0,
    }


def apply_rule(rule, input_grid):
    """Reverse the color order of concentric frames."""
    raw = input_grid.raw
    h = len(raw)
    w = len(raw[0]) if raw else 0

    in_colors = _extract_frame_colors(raw)
    if in_colors is None:
        return None

    rev_colors = list(reversed(in_colors))
    output = [row[:] for row in raw]

    layer = 0
    for color in rev_colors:
        r1, c1 = layer, layer
        r2, c2 = h - 1 - layer, w - 1 - layer
        if r1 > r2 or c1 > c2:
            break
        for r in range(r1, r2 + 1):
            for c in range(c1, c2 + 1):
                # Only paint cells that belong to this frame (not inner)
                if r == r1 or r == r2 or c == c1 or c == c2:
                    output[r][c] = color
        layer += 1

    return output
