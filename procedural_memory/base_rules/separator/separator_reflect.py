"""separator_reflect — follow chain paths below separator, place targets at endpoints, reflect above."""

RULE_TYPE = "separator_reflect"
CATEGORY = "separator"


def _find_separator_row(grid, bg=None):
    """Find a full-width row of a single non-background color."""
    h = len(grid)
    w = len(grid[0]) if grid else 0
    if bg is None:
        counts = {}
        for r in range(h):
            for c in range(w):
                counts[grid[r][c]] = counts.get(grid[r][c], 0) + 1
        bg = max(counts, key=counts.get)
    for r in range(h):
        vals = set(grid[r])
        if len(vals) == 1 and grid[r][0] != bg and w > 1:
            return r, grid[r][0]
    return None, None


def _identify_roles(grid, sep_row, bg):
    """Identify target, chain, and mirror colors from cells below/above separator."""
    h = len(grid)
    w = len(grid[0]) if grid else 0
    above_colors = set()
    below_colors = {}
    for r in range(h):
        if r == sep_row:
            continue
        for c in range(w):
            v = grid[r][c]
            if v == bg:
                continue
            if v == grid[sep_row][0]:
                continue
            if r < sep_row:
                above_colors.add(v)
            else:
                below_colors.setdefault(v, []).append((r, c))
    return above_colors, below_colors


def _follow_chain(start, chain_set):
    """Follow a chain of adjacent positions from start. Return final position."""
    visited = {start}
    path = [start]
    while True:
        cr, cc = path[-1]
        moved = False
        for dr, dc in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
            nr, nc = cr + dr, cc + dc
            if (nr, nc) in chain_set and (nr, nc) not in visited:
                visited.add((nr, nc))
                path.append((nr, nc))
                moved = True
                break
        if not moved:
            break
    return path[-1]


def try_rule(patterns, task):
    """Detect: separator with chain-following reflection pattern."""
    pairs = task.example_pairs
    if not pairs:
        return None

    if not patterns.get("grid_size_preserved"):
        return None

    # Detect consistent colors across pairs
    found_bg = None
    found_sep = None
    found_target = None
    found_chain = None
    found_mirror = None

    for pair in pairs:
        inp = pair.input_grid.raw
        out = pair.output_grid.raw
        h = len(inp)
        w = len(inp[0]) if inp else 0

        # Find background (most common)
        counts = {}
        for r in range(h):
            for c in range(w):
                counts[inp[r][c]] = counts.get(inp[r][c], 0) + 1
        bg = max(counts, key=counts.get)

        sep_row, sep_color = _find_separator_row(inp)
        if sep_row is None:
            return None

        above_colors, below_colors = _identify_roles(inp, sep_row, bg)

        # Need exactly 1 color above and 2 colors below
        if len(above_colors) != 1 or len(below_colors) != 2:
            return None

        mirror_color = above_colors.pop()
        below_keys = list(below_colors.keys())

        # Determine which below color is target and which is chain
        # by trying both assignments
        for target_c, chain_c in [(below_keys[0], below_keys[1]),
                                   (below_keys[1], below_keys[0])]:
            target_positions = below_colors[target_c]
            chain_set = set(tuple(p) for p in below_colors[chain_c])

            # Build expected output
            expected = [[bg] * w for _ in range(h)]
            for c in range(w):
                expected[sep_row][c] = sep_color

            valid = True
            for r, c in target_positions:
                final = _follow_chain((r, c), chain_set)
                dist = final[0] - sep_row
                refl_r = sep_row - dist
                if refl_r < 0 or refl_r >= h:
                    valid = False
                    break
                expected[final[0]][final[1]] = target_c
                expected[refl_r][final[1]] = mirror_color

            if valid and expected == out:
                if found_bg is not None:
                    if (found_bg != bg or found_target != target_c or
                            found_chain != chain_c or found_mirror != mirror_color):
                        return None
                found_bg = bg
                found_sep = sep_color
                found_target = target_c
                found_chain = chain_c
                found_mirror = mirror_color
                break
        else:
            return None

    if found_target is None:
        return None

    return {
        "type": RULE_TYPE,
        "bg": found_bg,
        "sep_color": found_sep,
        "target_color": found_target,
        "chain_color": found_chain,
        "mirror_color": found_mirror,
        "confidence": 1.0,
    }


def apply_rule(rule, input_grid):
    """Follow chains from targets, place at endpoints, reflect across separator."""
    raw = input_grid.raw
    h = len(raw)
    w = len(raw[0]) if raw else 0
    bg = rule["bg"]
    sep_color = rule["sep_color"]
    target_c = rule["target_color"]
    chain_c = rule["chain_color"]
    mirror_c = rule["mirror_color"]

    sep_row, _ = _find_separator_row(raw)
    if sep_row is None:
        return None

    # Collect targets and chains below separator
    target_positions = []
    chain_set = set()
    for r in range(sep_row + 1, h):
        for c in range(w):
            if raw[r][c] == target_c:
                target_positions.append((r, c))
            elif raw[r][c] == chain_c:
                chain_set.add((r, c))

    result = [[bg] * w for _ in range(h)]
    for c in range(w):
        result[sep_row][c] = sep_color

    for r, c in target_positions:
        final = _follow_chain((r, c), chain_set)
        dist = final[0] - sep_row
        refl_r = sep_row - dist
        if 0 <= refl_r < h:
            result[final[0]][final[1]] = target_c
            result[refl_r][final[1]] = mirror_c

    return result
