"""gravity_settle -- colored objects (rigid bodies) in separator-bounded cells
settle downward with a 1-row gap from the separator floor; separator color
varies per task.

Pattern:
- Grid has background (most common color) and separator (non-bg color forming
  boundary walls, detected as non-bg color present in the bottom row)
- Small colored objects (non-bg, non-separator) float above the separator floor
- Each object settles downward as a rigid body until it reaches 1 row above
  the nearest separator cell below it (per-column floor)
- Multiple objects stack on top of each other (no gap between stacked objects)
"""

RULE_TYPE = "gravity_settle"
CATEGORY = "geometry"


def _bg(grid):
    counts = {}
    for row in grid:
        for v in row:
            counts[v] = counts.get(v, 0) + 1
    return max(counts, key=counts.get)


def _detect_separator(grid, bg):
    """Detect separator as the non-bg color with the most cells in the bottom row."""
    h = len(grid)
    w = len(grid[0]) if grid else 0
    bottom_row = grid[h - 1]
    counts = {}
    for v in bottom_row:
        if v != bg:
            counts[v] = counts.get(v, 0) + 1
    if not counts:
        return None
    return max(counts, key=counts.get)


def _find_objects(grid, bg, sep):
    """Find connected components of non-bg, non-separator colors."""
    h = len(grid)
    w = len(grid[0]) if grid else 0
    visited = set()
    objects = []
    for r in range(h):
        for c in range(w):
            v = grid[r][c]
            if v != bg and v != sep and (r, c) not in visited:
                comp = []
                queue = [(r, c)]
                visited.add((r, c))
                while queue:
                    cr, cc = queue.pop(0)
                    comp.append((cr, cc))
                    for dr, dc in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                        nr, nc = cr + dr, cc + dc
                        if (0 <= nr < h and 0 <= nc < w and
                                (nr, nc) not in visited and
                                grid[nr][nc] != bg and grid[nr][nc] != sep):
                            visited.add((nr, nc))
                            queue.append((nr, nc))
                objects.append(comp)
    return objects


def _settle_objects(grid, bg, sep):
    """Settle all objects downward. Returns new grid."""
    h = len(grid)
    w = len(grid[0]) if grid else 0
    output = [[bg if grid[r][c] != sep else sep for c in range(w)] for r in range(h)]

    objects = _find_objects(grid, bg, sep)
    if not objects:
        return [row[:] for row in grid]

    # Sort objects by their bottom-most row (descending = bottom first)
    objects.sort(key=lambda obj: max(r for r, c in obj), reverse=True)

    # Track occupied cells (separator + already settled objects)
    occupied = set()
    for r in range(h):
        for c in range(w):
            if grid[r][c] == sep:
                occupied.add((r, c))

    for obj in objects:
        # For each column in the object, find bottom-most object cell
        cols = {}
        for r, c in obj:
            if c not in cols or r > cols[c]:
                cols[c] = r

        # Compute max drop per column
        min_drop = h  # impossibly large
        for c, bottom_r in cols.items():
            # Find nearest obstacle below in this column
            nearest_obstacle = h  # grid edge (virtual wall just past bottom)
            for rr in range(bottom_r + 1, h):
                if (rr, c) in occupied:
                    nearest_obstacle = rr
                    break

            # Check if obstacle is separator or another object
            is_sep_obstacle = (nearest_obstacle < h and
                               grid[nearest_obstacle][c] == sep)
            if not is_sep_obstacle and nearest_obstacle < h:
                # Obstacle is a settled object: no gap
                max_drop = nearest_obstacle - bottom_r - 1
            else:
                # Obstacle is separator or grid edge: 1-row gap
                max_drop = nearest_obstacle - bottom_r - 2

            min_drop = min(min_drop, max_drop)

        drop = max(0, min_drop)

        # Place object at new position
        for r, c in obj:
            new_r = r + drop
            output[new_r][c] = grid[r][c]
            occupied.add((new_r, c))

    return output


def try_rule(patterns, task):
    """Detect: separator-bounded grid with floating objects -> gravity settle."""
    if not patterns.get("grid_size_preserved"):
        return None

    for pair in task.example_pairs:
        raw_in = pair.input_grid.raw
        raw_out = pair.output_grid.raw
        bg = _bg(raw_in)

        sep = _detect_separator(raw_in, bg)
        if sep is None:
            return None

        objects = _find_objects(raw_in, bg, sep)
        if not objects:
            return None

        # Verify output matches gravity settle
        test_out = _settle_objects(raw_in, bg, sep)
        if test_out != raw_out:
            return None

    return {
        "type": RULE_TYPE,
        "confidence": 1.0,
    }


def apply_rule(rule, input_grid):
    raw = input_grid.raw
    bg = _bg(raw)
    sep = _detect_separator(raw, bg)
    if sep is None:
        return None

    return _settle_objects(raw, bg, sep)
