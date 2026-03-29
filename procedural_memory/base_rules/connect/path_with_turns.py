"""path_with_turns — draw L-shaped path from edge source, turning CW/CCW at signal pixels."""

from itertools import permutations

RULE_TYPE = "path_with_turns"
CATEGORY = "connect"

# Direction vectors: RIGHT, DOWN, LEFT, UP
_DIRS = [(0, 1), (1, 0), (0, -1), (-1, 0)]


def _cw(d):
    return _DIRS[(_DIRS.index(d) + 1) % 4]


def _ccw(d):
    return _DIRS[(_DIRS.index(d) - 1) % 4]


def _find_colors(grid):
    """Find all non-zero colors and their positions."""
    h, w = len(grid), len(grid[0])
    color_positions = {}
    for r in range(h):
        for c in range(w):
            v = grid[r][c]
            if v != 0:
                color_positions.setdefault(v, []).append((r, c))
    return color_positions


def _detect_initial_direction(pos, h, w):
    """Determine initial direction based on source position at grid edge."""
    r, c = pos
    if c == 0:
        return (0, 1)   # RIGHT
    if c == w - 1:
        return (0, -1)  # LEFT
    if r == 0:
        return (1, 0)   # DOWN
    if r == h - 1:
        return (-1, 0)  # UP
    return None


def _simulate(grid, source_pos, initial_dir, path_color, cw_color, ccw_color):
    """Simulate path drawing from source. Returns resulting grid."""
    h, w = len(grid), len(grid[0])
    result = [row[:] for row in grid]
    r, c = source_pos
    dr, dc = initial_dir
    max_steps = h * w * 2

    for _ in range(max_steps):
        nr, nc = r + dr, c + dc
        if nr < 0 or nr >= h or nc < 0 or nc >= w:
            break
        cell = grid[nr][nc]
        if cell == cw_color:
            dr, dc = _cw((dr, dc))
        elif cell == ccw_color:
            dr, dc = _ccw((dr, dc))
        elif cell == 0:
            result[nr][nc] = path_color
            r, c = nr, nc
        else:
            break

    return result


def try_rule(patterns, task):
    """Detect: path drawn from edge source, turning at colored signal pixels."""
    pairs = task.example_pairs
    if not pairs:
        return None

    # Detect path color: appears exactly once per pair at an edge, with
    # more cells in the output (the drawn path).
    path_color = None
    for pair in pairs:
        inp = pair.input_grid.raw
        out = pair.output_grid.raw
        h, w = len(inp), len(inp[0])
        ic = _find_colors(inp)
        oc = _find_colors(out)
        for color, positions in ic.items():
            if len(positions) != 1:
                continue
            r, c = positions[0]
            if r == 0 or r == h - 1 or c == 0 or c == w - 1:
                if len(oc.get(color, [])) > 1:
                    path_color = color
                    break
        if path_color is not None:
            break

    if path_color is None:
        return None

    # Verify path color appears exactly once at an edge in every pair.
    for pair in pairs:
        inp = pair.input_grid.raw
        h, w = len(inp), len(inp[0])
        ic = _find_colors(inp)
        if path_color not in ic or len(ic[path_color]) != 1:
            return None
        r, c = ic[path_color][0]
        if not (r == 0 or r == h - 1 or c == 0 or c == w - 1):
            return None

    # Signal colors: collect across ALL pairs. A signal color appears at the
    # same positions in input and output (it is not overwritten by the path).
    signal_colors = set()
    for pair in pairs:
        inp = pair.input_grid.raw
        out = pair.output_grid.raw
        ic = _find_colors(inp)
        oc = _find_colors(out)
        for color, positions in ic.items():
            if color == path_color:
                continue
            out_pos = oc.get(color, [])
            if set(positions) == set(out_pos):
                signal_colors.add(color)
    signal_colors = list(signal_colors)

    if len(signal_colors) < 2:
        return None

    # Try each pair assignment of (cw_signal, ccw_signal).
    for cw_c, ccw_c in permutations(signal_colors, 2):
        valid = True
        for pair in pairs:
            inp = pair.input_grid.raw
            out = pair.output_grid.raw
            ph, pw = len(inp), len(inp[0])

            ic = _find_colors(inp)
            if path_color not in ic or len(ic[path_color]) != 1:
                valid = False
                break

            sp = ic[path_color][0]
            idir = _detect_initial_direction(sp, ph, pw)
            if idir is None:
                valid = False
                break

            result = _simulate(inp, sp, idir, path_color, cw_c, ccw_c)
            if result != out:
                valid = False
                break

        if valid:
            return {
                "type": RULE_TYPE,
                "path_color": path_color,
                "cw_color": cw_c,
                "ccw_color": ccw_c,
                "confidence": 1.0,
            }

    return None


def apply_rule(rule, input_grid):
    """Draw the L-shaped path from the source pixel."""
    raw = input_grid.raw
    h, w = len(raw), len(raw[0])
    path_color = rule["path_color"]
    cw_color = rule["cw_color"]
    ccw_color = rule["ccw_color"]

    # Find source position (single occurrence of path_color)
    source_pos = None
    for r in range(h):
        for c in range(w):
            if raw[r][c] == path_color:
                source_pos = (r, c)
                break
        if source_pos:
            break

    if source_pos is None:
        return None

    idir = _detect_initial_direction(source_pos, h, w)
    if idir is None:
        return None

    return _simulate(raw, source_pos, idir, path_color, cw_color, ccw_color)
