"""
_primitives.py -- Atomic grid operations for the concept engine.

Every grid-transforming function takes grid (list[list[int]]) as first arg,
returns list[list[int]]. No ARCKG dependency. Pure functions, no side effects.

Add new primitives here when existing ones cannot express the needed transformation.
"""


# ============================================================
# EXTRACTION primitives (grid -> smaller grid or data)
# ============================================================

def extract_subgrid(grid, top, left, height, width):
    """Extract a rectangular region. Returns height x width grid."""
    return [row[left:left + width] for row in grid[top:top + height]]


def extract_column(grid, col_index):
    """Extract a single column as Hx1 grid."""
    return [[row[col_index]] for row in grid]


def extract_row(grid, row_index):
    """Extract a single row as 1xW grid."""
    return [grid[row_index][:]]


def extract_objects(grid, bg=0):
    """Find connected components of non-bg cells.
    Returns list of dicts: {"positions": [(r,c),...], "color": int, "bbox": (top,left,h,w)}."""
    h = len(grid)
    w = len(grid[0]) if grid else 0
    visited = set()
    objects = []
    for r in range(h):
        for c in range(w):
            if grid[r][c] == bg or (r, c) in visited:
                continue
            # BFS
            comp = []
            color = grid[r][c]
            queue = [(r, c)]
            visited.add((r, c))
            while queue:
                cr, cc = queue.pop(0)
                comp.append((cr, cc))
                for dr, dc in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                    nr, nc = cr + dr, cc + dc
                    if 0 <= nr < h and 0 <= nc < w and (nr, nc) not in visited and grid[nr][nc] != bg:
                        visited.add((nr, nc))
                        queue.append((nr, nc))
            min_r = min(p[0] for p in comp)
            min_c = min(p[1] for p in comp)
            max_r = max(p[0] for p in comp)
            max_c = max(p[1] for p in comp)
            objects.append({
                "positions": comp,
                "color": color,
                "bbox": (min_r, min_c, max_r - min_r + 1, max_c - min_c + 1),
                "size": len(comp),
            })
    return objects


# ============================================================
# GEOMETRY primitives (grid -> grid)
# ============================================================

def scale(grid, factor):
    """Scale each cell into factor x factor block."""
    output = []
    for row in grid:
        for _ in range(factor):
            output.append([cell for cell in row for _ in range(factor)])
    return output


def flip_vertical(grid):
    """Reverse row order (top-bottom flip)."""
    return [row[:] for row in reversed(grid)]


def flip_horizontal(grid):
    """Reverse each row (left-right flip)."""
    return [row[::-1] for row in grid]


def rotate_cw(grid, times=1):
    """Rotate 90 degrees clockwise, `times` times."""
    g = [row[:] for row in grid]
    for _ in range(times % 4):
        h, w = len(g), len(g[0]) if g else 0
        g = [[g[h - 1 - r][c] for r in range(h)] for c in range(w)]
    return g


def transpose(grid):
    """Transpose grid (swap rows and columns)."""
    if not grid:
        return []
    return [list(col) for col in zip(*grid)]


def gravity(grid, direction="down", bg=0):
    """Drop non-bg cells in the given direction (down/up/left/right)."""
    h = len(grid)
    w = len(grid[0]) if grid else 0
    output = [[bg] * w for _ in range(h)]

    if direction in ("down", "up"):
        for c in range(w):
            col_vals = [grid[r][c] for r in range(h) if grid[r][c] != bg]
            if direction == "down":
                for i, v in enumerate(reversed(col_vals)):
                    output[h - 1 - i][c] = v
            else:
                for i, v in enumerate(col_vals):
                    output[i][c] = v
    elif direction in ("left", "right"):
        for r in range(h):
            row_vals = [grid[r][c] for c in range(w) if grid[r][c] != bg]
            if direction == "right":
                for i, v in enumerate(reversed(row_vals)):
                    output[r][w - 1 - i] = v
            else:
                for i, v in enumerate(row_vals):
                    output[r][i] = v
    return output


# ============================================================
# COMPOSITION primitives (grid, grid -> grid)
# ============================================================

def concat_vertical(grid_a, grid_b):
    """Stack grid_a on top of grid_b."""
    return [row[:] for row in grid_a] + [row[:] for row in grid_b]


def concat_horizontal(grid_a, grid_b):
    """Place grid_a left of grid_b."""
    return [a[:] + b[:] for a, b in zip(grid_a, grid_b)]


def overlay(base, top, transparent=0):
    """Overlay `top` onto `base`. Cells in `top` equal to `transparent` are ignored."""
    h = min(len(base), len(top))
    w = min(len(base[0]) if base else 0, len(top[0]) if top else 0)
    output = [row[:] for row in base]
    for r in range(h):
        for c in range(w):
            if top[r][c] != transparent:
                output[r][c] = top[r][c]
    return output


# ============================================================
# COLOR primitives (grid -> grid)
# ============================================================

def recolor(grid, mapping):
    """Replace colors according to {old: new} mapping. Unmapped colors unchanged.
    Keys in mapping can be int or str (auto-converted)."""
    int_map = {int(k): int(v) for k, v in mapping.items()}
    return [[int_map.get(cell, cell) for cell in row] for row in grid]


def fill_region(grid, positions, color):
    """Set cells at [(r,c), ...] to `color`. Returns new grid."""
    output = [row[:] for row in grid]
    for r, c in positions:
        if 0 <= r < len(output) and 0 <= c < len(output[0]):
            output[r][c] = color
    return output


def mask_keep(grid, keep_positions, bg=0):
    """Keep only cells at keep_positions, fill rest with bg."""
    h = len(grid)
    w = len(grid[0]) if grid else 0
    keep_set = set(keep_positions)
    return [[grid[r][c] if (r, c) in keep_set else bg for c in range(w)] for r in range(h)]


# ============================================================
# CONSTRUCTION primitives
# ============================================================

def make_uniform(height, width, color):
    """Create a solid-color grid."""
    return [[color] * width for _ in range(height)]


def place_column(grid, column, col_index):
    """Paste a Hx1 column into grid at col_index."""
    output = [row[:] for row in grid]
    for r in range(min(len(grid), len(column))):
        output[r][col_index] = column[r][0]
    return output


def place_row(grid, row_data, row_index):
    """Paste a 1xW row into grid at row_index."""
    output = [row[:] for row in grid]
    for c in range(min(len(grid[0]) if grid else 0, len(row_data[0]) if row_data else 0)):
        output[row_index][c] = row_data[0][c]
    return output


# ============================================================
# PATTERN primitives (grid -> grid)
# ============================================================

def staircase_fill(grid, color):
    """Build a staircase from a 1-row input.
    Counts non-zero cells in row 0 as start_count.
    Output has W/2 rows. Row i has (start_count + i) cells of `color`, rest 0."""
    if not grid or not grid[0]:
        return grid
    w = len(grid[0])
    start_count = sum(1 for v in grid[0] if v != 0)
    num_rows = w // 2
    output = []
    for i in range(num_rows):
        filled = start_count + i
        row = [color] * min(filled, w) + [0] * max(0, w - filled)
        output.append(row)
    return output


# ============================================================
# ANALYSIS primitives (return values, not grids)
# ============================================================

def find_bg_color(grid):
    """Return the most frequent color (background)."""
    counts = {}
    for row in grid:
        for c in row:
            counts[c] = counts.get(c, 0) + 1
    return max(counts, key=counts.get) if counts else 0


def grid_dimensions(grid):
    """Return (height, width)."""
    return (len(grid), len(grid[0]) if grid else 0)


def find_separator_lines(grid, bg=0):
    """Find full-width rows or full-height columns of uniform non-bg color.
    Returns {'rows': [(row_idx, color), ...], 'cols': [(col_idx, color), ...]}."""
    h = len(grid)
    w = len(grid[0]) if grid else 0
    rows = []
    for r in range(h):
        vals = set(grid[r])
        if len(vals) == 1 and vals.pop() != bg:
            rows.append((r, grid[r][0]))
    cols = []
    for c in range(w):
        vals = set(grid[r][c] for r in range(h))
        if len(vals) == 1 and vals.pop() != bg:
            cols.append((c, grid[0][c]))
    return {"rows": rows, "cols": cols}


def recolor_columns_by_height(grid, source_color, bg=0):
    """Recolor vertical columns of source_color by their height rank.
    Tallest column gets color 1, second tallest gets 2, etc.
    Columns are identified as contiguous vertical runs of source_color."""
    h = len(grid)
    w = len(grid[0]) if grid else 0
    output = [row[:] for row in grid]

    # Find columns that contain source_color and their heights
    col_heights = []
    for c in range(w):
        count = sum(1 for r in range(h) if grid[r][c] == source_color)
        if count > 0:
            col_heights.append((c, count))

    # Sort by height descending (tallest first), break ties by column index
    col_heights.sort(key=lambda x: (-x[1], x[0]))

    # Assign colors 1, 2, 3, ... based on rank
    for rank, (c, _) in enumerate(col_heights):
        new_color = rank + 1
        for r in range(h):
            if grid[r][c] == source_color:
                output[r][c] = new_color

    return output


def first_nonzero_color(grid):
    """Return the first non-zero color found scanning left-to-right, top-to-bottom."""
    for row in grid:
        for v in row:
            if v != 0:
                return v
    return 0


def count_color(grid, color):
    """Count occurrences of a color."""
    return sum(row.count(color) for row in grid)


def trace_marker_path(grid, start_color, down_color, up_color, path_color, bg=0):
    """Trace an L-shaped path from start_color through markers on the grid.

    Algorithm:
      1. Begin at the cell with start_color, direction = right.
      2. Move in current direction, filling cells with path_color.
      3. Stop one cell before a marker (down_color or up_color) or at grid edge.
      4. If stopped by a horizontal marker:
         - down_color -> next direction is DOWN
         - up_color   -> next direction is UP
      5. If stopped by a vertical marker (any type) -> next direction is RIGHT.
      6. Repeat until reaching the grid edge with no further marker.
    Markers remain in place; path_color is drawn up to (not over) them.
    """
    h = len(grid)
    w = len(grid[0]) if grid else 0
    output = [row[:] for row in grid]

    # Find start position
    start_r = start_c = None
    for r in range(h):
        for c in range(w):
            if grid[r][c] == start_color:
                start_r, start_c = r, c
                break
        if start_r is not None:
            break
    if start_r is None:
        return output

    # Build marker lookup: {(r,c): color} for down_color and up_color
    markers = {}
    for r in range(h):
        for c in range(w):
            if grid[r][c] in (down_color, up_color):
                markers[(r, c)] = grid[r][c]

    cur_r, cur_c = start_r, start_c
    direction = "right"  # always starts rightward

    for _ in range(h * w):  # safety bound
        if direction == "right":
            # Scan right for next marker on this row
            target_c = w  # default: grid edge
            marker_color = None
            for mc in range(cur_c + 1, w):
                if (cur_r, mc) in markers:
                    target_c = mc
                    marker_color = markers[(cur_r, mc)]
                    break
            # Fill from cur_c+1 to target_c-1 with path_color
            for c in range(cur_c + 1, target_c):
                output[c if False else cur_r][c] = path_color
            if marker_color is None:
                break  # reached edge
            cur_c = target_c - 1
            direction = "down" if marker_color == down_color else "up"

        elif direction == "down":
            target_r = h  # default: grid edge
            marker_color = None
            for mr in range(cur_r + 1, h):
                if (mr, cur_c) in markers:
                    target_r = mr
                    marker_color = markers[(mr, cur_c)]
                    break
            for r in range(cur_r + 1, target_r):
                output[r][cur_c] = path_color
            if marker_color is None:
                break
            cur_r = target_r - 1
            direction = "right"

        elif direction == "up":
            target_r = -1  # default: grid edge
            marker_color = None
            for mr in range(cur_r - 1, -1, -1):
                if (mr, cur_c) in markers:
                    target_r = mr
                    marker_color = markers[(mr, cur_c)]
                    break
            for r in range(cur_r - 1, max(target_r, -1), -1):
                output[r][cur_c] = path_color
            if marker_color is None:
                break
            cur_r = target_r + 1
            direction = "right"

    return output


def mirror_trail_across_separator(grid, sep_color, primary_below, trail_color,
                                   primary_above, bg):
    """Move colored pixels along their trails and mirror across a separator.

    Below the separator: each primary_below pixel has adjacent trail_color pixels
    forming a directional trail. The primary moves to the trail endpoint.
    Above the separator: corresponding primary_above pixels (same column, symmetric
    row distance) move with the same displacement but row component negated.
    All trail_color pixels and original positions are cleared.
    """
    h = len(grid)
    w = len(grid[0]) if grid else 0
    output = [[bg] * w for _ in range(h)]

    # Find separator row
    sep_row = None
    for r in range(h):
        if all(grid[r][c] == sep_color for c in range(w)):
            sep_row = r
            break
    if sep_row is None:
        return [row[:] for row in grid]

    # Copy separator
    for c in range(w):
        output[sep_row][c] = sep_color

    # Collect positions below separator
    below_primaries = []  # (r, c)
    below_trails = set()
    for r in range(sep_row + 1, h):
        for c in range(w):
            if grid[r][c] == primary_below:
                below_primaries.append((r, c))
            elif grid[r][c] == trail_color:
                below_trails.add((r, c))

    # For each primary_below, trace its trail via BFS through adjacent trail cells
    used_trails = set()
    displacements = []  # (primary_pos, displacement)
    for pr, pc in below_primaries:
        # BFS from primary through adjacent trail cells
        trail_path = []
        visited = {(pr, pc)}
        queue = [(pr, pc)]
        while queue:
            cr, cc = queue.pop(0)
            for dr, dc in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                nr, nc = cr + dr, cc + dc
                if (nr, nc) not in visited and (nr, nc) in below_trails:
                    visited.add((nr, nc))
                    trail_path.append((nr, nc))
                    queue.append((nr, nc))
                    used_trails.add((nr, nc))
        if trail_path:
            # Endpoint is the last cell found (furthest from primary)
            end_r, end_c = trail_path[-1]
            dr = end_r - pr
            dc = end_c - pc
        else:
            dr, dc = 0, 0
        displacements.append(((pr, pc), (dr, dc)))
        # Place moved primary
        new_r, new_c = pr + dr, pc + dc
        if 0 <= new_r < h and 0 <= new_c < w:
            output[new_r][new_c] = primary_below

    # Collect primaries above separator
    above_primaries = []
    for r in range(0, sep_row):
        for c in range(w):
            if grid[r][c] == primary_above:
                above_primaries.append((r, c))

    # Match above primaries to below primaries by symmetric position
    for ar, ac in above_primaries:
        dist_above = sep_row - ar  # distance from separator
        # Find matching below primary: same column, same distance below sep
        matched_disp = None
        for (br, bc), (dr, dc) in displacements:
            dist_below = br - sep_row
            if bc == ac and dist_below == dist_above:
                matched_disp = (dr, dc)
                break
        if matched_disp is not None:
            # Mirror: negate row component, keep column component
            new_r = ar - matched_disp[0]
            new_c = ac + matched_disp[1]
            if 0 <= new_r < h and 0 <= new_c < w:
                output[new_r][new_c] = primary_above
        else:
            # No match found, keep in place
            output[ar][ac] = primary_above

    return output


def recolor_objects_by_size(grid, bg=0):
    """Find connected components and recolor by size rank.
    Objects grouped by size: largest group gets color 1, next gets 2, etc."""
    objects = extract_objects(grid, bg=bg)
    if not objects:
        return [row[:] for row in grid]
    sizes = sorted(set(obj["size"] for obj in objects), reverse=True)
    size_to_color = {s: i + 1 for i, s in enumerate(sizes)}
    output = [[bg] * len(row) for row in grid]
    for obj in objects:
        new_color = size_to_color[obj["size"]]
        for r, c in obj["positions"]:
            output[r][c] = new_color
    return output


def reverse_concentric_rings(grid):
    """Reverse the color order of concentric rectangular rings.
    Detects nested rectangular frames from outside in, then rebuilds
    the grid with the ring colors in reversed order (innermost becomes outermost)."""
    h = len(grid)
    w = len(grid[0]) if grid else 0
    if h == 0 or w == 0:
        return [row[:] for row in grid]

    # Extract ring colors from outside in
    ring_colors = []
    top, left, bottom, right = 0, 0, h - 1, w - 1
    while top <= bottom and left <= right:
        color = grid[top][left]
        ring_colors.append(color)
        top += 1
        left += 1
        bottom -= 1
        right -= 1

    # Reverse the color order
    reversed_colors = ring_colors[::-1]

    # Rebuild grid with reversed ring colors
    output = [[0] * w for _ in range(h)]
    top, left, bottom, right = 0, 0, h - 1, w - 1
    for idx in range(len(reversed_colors)):
        color = reversed_colors[idx]
        for r in range(top, bottom + 1):
            for c in range(left, right + 1):
                if r == top or r == bottom or c == left or c == right:
                    output[r][c] = color
                elif output[r][c] == 0:
                    output[r][c] = color
        top += 1
        left += 1
        bottom -= 1
        right -= 1

    return output


def separator_axis_zone_fill(grid, bg=7):
    """Fill zones defined by separator rows crossing a vertical axis column.

    Detects a vertical axis column (color that appears most in a single column)
    and horizontal separator rows (uniform non-bg color with intersection at axis).
    Output rules:
    - Separator rows: all intersection_color, axis_color at axis position
    - Boundary rows (midpoint between different-color seps, only when midpoint is integer):
      all intersection_color everywhere
    - Zone rows: nearest separator's color, intersection_color at axis"""
    h = len(grid)
    w = len(grid[0]) if grid else 0

    # Find axis column: the column where one non-bg color appears most frequently
    axis_col = None
    axis_color = None
    best_count = 0
    for c in range(w):
        counts = {}
        for r in range(h):
            v = grid[r][c]
            if v != bg:
                counts[v] = counts.get(v, 0) + 1
        if counts:
            dominant = max(counts, key=counts.get)
            if counts[dominant] > best_count:
                best_count = counts[dominant]
                axis_col = c
                axis_color = dominant

    if axis_col is None:
        return [row[:] for row in grid]

    # Find separator rows: all non-axis cells are same non-bg color
    separators = []  # (row_idx, color)
    intersection_color = None
    for r in range(h):
        row_vals = [grid[r][c] for c in range(w) if c != axis_col]
        vals = set(row_vals)
        if len(vals) == 1:
            v = vals.pop()
            if v != bg:
                separators.append((r, v))
                if intersection_color is None:
                    intersection_color = grid[r][axis_col]

    if not separators or intersection_color is None:
        return [row[:] for row in grid]

    sep_set = {s[0] for s in separators}

    # Compute boundary rows: midpoint between adjacent different-color seps
    # Only when (a+b) is even (integer midpoint)
    boundaries = set()
    for i in range(len(separators) - 1):
        a, ca = separators[i]
        b, cb = separators[i + 1]
        if ca != cb and (a + b) % 2 == 0:
            boundaries.add((a + b) // 2)

    # Build output
    output = [[0] * w for _ in range(h)]
    for r in range(h):
        if r in sep_set:
            # Separator row
            for c in range(w):
                output[r][c] = intersection_color
            output[r][axis_col] = axis_color
        elif r in boundaries:
            # Boundary row: all intersection_color
            for c in range(w):
                output[r][c] = intersection_color
        else:
            # Zone row: nearest separator color
            min_dist = h + 1
            nearest_color = bg
            for sr, sc in separators:
                d = abs(r - sr)
                if d < min_dist:
                    min_dist = d
                    nearest_color = sc
            for c in range(w):
                output[r][c] = nearest_color
            output[r][axis_col] = intersection_color

    return output


def unique_colors(grid, exclude_bg=True):
    """Return sorted list of unique colors in grid. Optionally exclude background."""
    bg = find_bg_color(grid) if exclude_bg else None
    colors = set()
    for row in grid:
        for c in row:
            if c != bg:
                colors.add(c)
    return sorted(colors)


def self_tile(grid, bg=0):
    """Kronecker-style self-tiling: replace each non-bg cell with the whole grid,
    each bg cell with an all-bg block of the same size.
    Output size = (H*H) x (W*W)."""
    h = len(grid)
    w = len(grid[0]) if grid else 0
    output = [[bg] * (w * w) for _ in range(h * h)]
    for r in range(h):
        for c in range(w):
            if grid[r][c] != bg:
                for gr in range(h):
                    for gc in range(w):
                        output[r * h + gr][c * w + gc] = grid[gr][gc]
    return output


def tile_alternating_flip(grid, reps_h, reps_w):
    """Tile grid in a reps_h x reps_w arrangement. Odd block-rows are horizontally flipped."""
    h = len(grid)
    w = len(grid[0]) if grid else 0
    output = []
    for br in range(reps_h):
        use_flipped = (br % 2 == 1)
        for r in range(h):
            row = []
            for bc in range(reps_w):
                if use_flipped:
                    row.extend(grid[r][::-1])
                else:
                    row.extend(grid[r][:])
            output.append(row)
    return output
