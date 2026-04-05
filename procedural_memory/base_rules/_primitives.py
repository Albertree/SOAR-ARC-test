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


def fill_bordered_rectangles_by_size(grid, border_color=5, bg=0):
    """Find rectangles outlined by border_color, fill interiors by size rank.

    Finds all closed rectangles made of border_color. Measures interior area.
    Ranks by interior area ascending: smallest → color 6, next → 7, next → 8, etc.
    """
    h = len(grid)
    w = len(grid[0]) if grid else 0
    output = [row[:] for row in grid]

    # Find candidate rectangles: look for top-left corners of border_color rectangles
    rects = []  # (top, left, height, width, interior_h, interior_w)
    for r in range(h):
        for c in range(w):
            if grid[r][c] != border_color:
                continue
            # Try to find a rectangle starting at (r, c)
            # Find width: contiguous border_color in top row
            for rw in range(2, w - c + 1):
                if c + rw - 1 >= w or grid[r][c + rw - 1] != border_color:
                    break
                # Check if bottom row exists at some height
                for rh in range(2, h - r + 1):
                    br = r + rh - 1
                    if br >= h:
                        break
                    # Verify all 4 borders
                    # Top row
                    top_ok = all(grid[r][cc] == border_color for cc in range(c, c + rw))
                    # Bottom row
                    bot_ok = all(grid[br][cc] == border_color for cc in range(c, c + rw))
                    # Left col
                    left_ok = all(grid[rr][c] == border_color for rr in range(r, br + 1))
                    # Right col
                    right_ok = all(grid[rr][c + rw - 1] == border_color for rr in range(r, br + 1))
                    if top_ok and bot_ok and left_ok and right_ok:
                        # Check interior is all bg
                        int_h = rh - 2
                        int_w = rw - 2
                        if int_h > 0 and int_w > 0:
                            interior_ok = all(
                                grid[rr][cc] == bg
                                for rr in range(r + 1, br)
                                for cc in range(c + 1, c + rw - 1)
                            )
                            if interior_ok:
                                rects.append((r, c, rh, rw, int_h, int_w))

    # Deduplicate (same rectangle found from different corners)
    seen = set()
    unique_rects = []
    for rect in rects:
        key = (rect[0], rect[1], rect[2], rect[3])
        if key not in seen:
            seen.add(key)
            unique_rects.append(rect)

    # Fill interiors: color = border_color + interior_side_length
    # For square interiors: side = int(sqrt(area)); for non-square: use max(int_h, int_w)
    import math
    for top, left, rh, rw, int_h, int_w in unique_rects:
        side = max(int_h, int_w)
        fill_color = border_color + side
        for rr in range(top + 1, top + rh - 1):
            for cc in range(left + 1, left + rw - 1):
                output[rr][cc] = fill_color

    return output


def fill_quadrants_from_corners(grid, rect_color=5, bg=0):
    """Find a rectangle of rect_color with 4 diagonal corner markers.

    Each corner marker is a non-bg, non-rect_color pixel diagonally adjacent
    to a corner of the rectangle. The rectangle is split into quadrants and
    each quadrant filled with its nearest corner marker's color.
    Corner markers are then removed (set to bg).
    """
    h = len(grid)
    w = len(grid[0]) if grid else 0
    output = [row[:] for row in grid]

    # Find all rect_color positions
    rect_positions = set()
    for r in range(h):
        for c in range(w):
            if grid[r][c] == rect_color:
                rect_positions.add((r, c))

    if not rect_positions:
        return output

    # Find connected components of rect_color
    visited = set()
    components = []
    for r, c in rect_positions:
        if (r, c) in visited:
            continue
        comp = []
        queue = [(r, c)]
        visited.add((r, c))
        while queue:
            cr, cc = queue.pop(0)
            comp.append((cr, cc))
            for dr, dc in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                nr, nc = cr + dr, cc + dc
                if (nr, nc) in rect_positions and (nr, nc) not in visited:
                    visited.add((nr, nc))
                    queue.append((nr, nc))
        components.append(comp)

    for comp in components:
        min_r = min(p[0] for p in comp)
        max_r = max(p[0] for p in comp)
        min_c = min(p[1] for p in comp)
        max_c = max(p[1] for p in comp)

        # Look for corner markers diagonally adjacent to bbox corners
        corners = {}  # 'tl', 'tr', 'bl', 'br' -> color
        corner_positions = []
        for label, dr, dc in [
            ('tl', min_r - 1, min_c - 1),
            ('tr', min_r - 1, max_c + 1),
            ('bl', max_r + 1, min_c - 1),
            ('br', max_r + 1, max_c + 1),
        ]:
            if 0 <= dr < h and 0 <= dc < w:
                v = grid[dr][dc]
                if v != bg and v != rect_color:
                    corners[label] = v
                    corner_positions.append((dr, dc))

        if len(corners) != 4:
            continue

        # Calculate midpoints for quadrant split
        rect_h = max_r - min_r + 1
        rect_w = max_c - min_c + 1
        mid_r = min_r + rect_h // 2
        mid_c = min_c + rect_w // 2

        # Fill each cell of the rectangle with its quadrant color
        for r in range(min_r, max_r + 1):
            for c in range(min_c, max_c + 1):
                if r < mid_r and c < mid_c:
                    output[r][c] = corners['tl']
                elif r < mid_r and c >= mid_c:
                    output[r][c] = corners['tr']
                elif r >= mid_r and c < mid_c:
                    output[r][c] = corners['bl']
                else:
                    output[r][c] = corners['br']

        # Remove corner markers
        for cr, cc in corner_positions:
            output[cr][cc] = bg

    return output


def keep_densest_column(grid, bg=0):
    """Keep only the column with the most non-bg cells; zero out all others.
    Grid size is preserved. Ties broken by leftmost column."""
    h = len(grid)
    w = len(grid[0]) if grid else 0
    best_col = 0
    best_count = -1
    for c in range(w):
        count = sum(1 for r in range(h) if grid[r][c] != bg)
        if count > best_count:
            best_count = count
            best_col = c
    output = [[bg] * w for _ in range(h)]
    for r in range(h):
        output[r][best_col] = grid[r][best_col]
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


# ============================================================
# CONNECT ALIGNED DIAMONDS
# ============================================================

def connect_aligned_diamonds(grid, bg=0):
    """Find 3x3 diamond shapes and connect axis-aligned pairs with bridges.

    A diamond centered at (r,c) has pixels at (r-1,c), (r,c-1), (r,c+1), (r+1,c)
    with (r,c)==bg (hollow center). All four tips share the same non-bg color.

    Aligned pair sharing center row → horizontal bridge (color 1) between tips.
    Aligned pair sharing center col → vertical bridge (color 1) between tips.
    """
    import copy
    out = copy.deepcopy(grid)
    H = len(grid)
    W = len(grid[0]) if H else 0
    BRIDGE = 1

    # Detect diamond centers
    centers = []
    for r in range(1, H - 1):
        for c in range(1, W - 1):
            if grid[r][c] != bg:
                continue
            top = grid[r - 1][c]
            bot = grid[r + 1][c]
            left = grid[r][c - 1]
            right = grid[r][c + 1]
            if top != bg and top == bot == left == right:
                centers.append((r, c))

    # Group by row and column for nearest-neighbor connections
    from collections import defaultdict
    by_row = defaultdict(list)
    by_col = defaultdict(list)
    for r, c in centers:
        by_row[r].append(c)
        by_col[c].append(r)

    # Connect consecutive horizontally aligned pairs
    for r, cols in by_row.items():
        cols.sort()
        for k in range(len(cols) - 1):
            left_c, right_c = cols[k], cols[k + 1]
            for cc in range(left_c + 2, right_c - 1):
                if out[r][cc] == bg:
                    out[r][cc] = BRIDGE

    # Connect consecutive vertically aligned pairs
    for c, rows in by_col.items():
        rows.sort()
        for k in range(len(rows) - 1):
            top_r, bot_r = rows[k], rows[k + 1]
            for rr in range(top_r + 2, bot_r - 1):
                if out[rr][c] == bg:
                    out[rr][c] = BRIDGE

    return out


# ============================================================
# L-PATH CHAIN (source -> targets with directional turns)
# ============================================================

def l_path_chain(grid, source_color=3, cw_color=6, ccw_color=8):
    """Draw L-shaped path chains from a source pixel through target pixels.

    Starting at the source_color pixel, direction = RIGHT.
    Move in current direction, painting source_color.
    Stop one cell before a target (cw_color or ccw_color).
    - cw_color (6): turn clockwise  (right->down->left->up)
    - ccw_color (8): turn counterclockwise (right->up->left->down)
    If no target ahead in current direction, paint to grid edge.
    """
    import copy
    out = copy.deepcopy(grid)
    H = len(grid)
    W = len(grid[0]) if H else 0

    DIRS = [(0, 1), (1, 0), (0, -1), (-1, 0)]  # RIGHT, DOWN, LEFT, UP

    # Find source
    sr, sc = None, None
    for r in range(H):
        for c in range(W):
            if grid[r][c] == source_color:
                sr, sc = r, c
                break
        if sr is not None:
            break
    if sr is None:
        return out

    # Collect target positions
    targets = set()
    for r in range(H):
        for c in range(W):
            if grid[r][c] in (cw_color, ccw_color):
                targets.add((r, c))

    cur_r, cur_c = sr, sc
    d_idx = 0  # start RIGHT

    visited_targets = set()
    max_iterations = H * W * 4

    for _ in range(max_iterations):
        dr, dc = DIRS[d_idx]

        # Scan ahead for nearest target in this direction
        hit_target = None
        steps = 0
        nr, nc = cur_r + dr, cur_c + dc
        while 0 <= nr < H and 0 <= nc < W:
            steps += 1
            if (nr, nc) in targets and (nr, nc) not in visited_targets:
                hit_target = (nr, nc)
                break
            nr += dr
            nc += dc

        if hit_target is not None:
            tr, tc = hit_target
            # Paint from current position (exclusive) to one cell before target
            pr, pc = cur_r, cur_c
            for _ in range(steps - 1):
                pr += dr
                pc += dc
                if out[pr][pc] == 0:
                    out[pr][pc] = source_color
            cur_r, cur_c = pr, pc

            visited_targets.add(hit_target)
            target_color = grid[tr][tc]
            if target_color == cw_color:
                d_idx = (d_idx + 1) % 4  # clockwise
            else:
                d_idx = (d_idx - 1) % 4  # counterclockwise
        else:
            # No target ahead — paint to grid edge
            pr, pc = cur_r + dr, cur_c + dc
            while 0 <= pr < H and 0 <= pc < W:
                if out[pr][pc] == 0:
                    out[pr][pc] = source_color
                pr += dr
                pc += dc
            break

    return out


def quadrant_shape_swap(grid, sep_color=0):
    """Swap shapes between horizontally adjacent quadrant pairs in a grid
    divided by separator rows/columns.

    The grid is partitioned by full rows/columns of sep_color into rectangular
    quadrants. Each quadrant has a uniform background color and may contain a
    shape drawn in a different color. Quadrants are paired horizontally (left-right
    in the same row band). Within each pair, the shapes are swapped: each shape
    takes on the background color of the quadrant it came FROM.

    If both quadrants in a pair share the same background, the swapped shapes
    become invisible (bg on bg), effectively clearing both quadrants.
    """
    h = len(grid)
    w = len(grid[0]) if grid else 0

    # Find separator rows and columns
    sep_rows = []
    for r in range(h):
        if all(grid[r][c] == sep_color for c in range(w)):
            sep_rows.append(r)

    sep_cols = []
    for c in range(w):
        if all(grid[r][c] == sep_color for r in range(h)):
            sep_cols.append(c)

    # Extract row bands (ranges between separator row groups)
    row_bands = []
    r = 0
    while r < h:
        if r in set(sep_rows):
            r += 1
            continue
        start = r
        while r < h and r not in set(sep_rows):
            r += 1
        row_bands.append((start, r))  # [start, end)

    # Extract column bands
    col_bands = []
    c = 0
    while c < w:
        if c in set(sep_cols):
            c += 1
            continue
        start = c
        while c < w and c not in set(sep_cols):
            c += 1
        col_bands.append((start, c))

    # Build output, starting from a copy of input
    output = [row[:] for row in grid]

    # Process each row band: pair up column bands left-right
    for r_start, r_end in row_bands:
        # Pair consecutive column bands
        for i in range(0, len(col_bands) - 1, 2):
            c1_start, c1_end = col_bands[i]
            c2_start, c2_end = col_bands[i + 1]

            # Determine background of each quadrant (most frequent color)
            def _quadrant_bg(rs, re, cs, ce):
                counts = {}
                for rr in range(rs, re):
                    for cc in range(cs, ce):
                        v = grid[rr][cc]
                        counts[v] = counts.get(v, 0) + 1
                return max(counts, key=counts.get) if counts else 0

            bg1 = _quadrant_bg(r_start, r_end, c1_start, c1_end)
            bg2 = _quadrant_bg(r_start, r_end, c2_start, c2_end)

            # Extract shape positions (non-bg cells) with relative coords
            def _extract_shape(rs, re, cs, ce, bg):
                cells = []
                for rr in range(rs, re):
                    for cc in range(cs, ce):
                        if grid[rr][cc] != bg:
                            cells.append((rr - rs, cc - cs))
                return cells

            shape1 = _extract_shape(r_start, r_end, c1_start, c1_end, bg1)
            shape2 = _extract_shape(r_start, r_end, c2_start, c2_end, bg2)

            # Clear both quadrants to their own bg
            for rr in range(r_start, r_end):
                for cc in range(c1_start, c1_end):
                    output[rr][cc] = bg1
                for cc in range(c2_start, c2_end):
                    output[rr][cc] = bg2

            # Place shape2 into quadrant1 with color = bg2 (source's bg)
            for dr, dc in shape2:
                rr = r_start + dr
                cc = c1_start + dc
                if r_start <= rr < r_end and c1_start <= cc < c1_end:
                    output[rr][cc] = bg2

            # Place shape1 into quadrant2 with color = bg1 (source's bg)
            for dr, dc in shape1:
                rr = r_start + dr
                cc = c2_start + dc
                if r_start <= rr < r_end and c2_start <= cc < c2_end:
                    output[rr][cc] = bg1

    return output


def gravity_toward_border(grid, bg=7):
    """Drop connected components of content color toward the border structure.

    Auto-detects border and content colors from the grid:
    - bg is provided (background)
    - There should be exactly 2 other colors: border and content
    - The border color has cells forming the largest connected component
      that touches grid edges; content is the other color

    Content components are rigid bodies that fall toward the nearest border
    surface. Components closer to the border drop first; already-placed
    components act as obstacles.

    Gap rule: if the section height (free vertical space) >= 4, leave a gap of 1
    between the object and the border/obstacle. Otherwise gap = 0.
    """
    h = len(grid)
    w = len(grid[0]) if grid else 0
    if h == 0 or w == 0:
        return [row[:] for row in grid]

    bg_color = bg

    # Find non-bg colors
    non_bg = set()
    for row in grid:
        for v in row:
            if v != bg_color:
                non_bg.add(v)

    if len(non_bg) != 2:
        return [row[:] for row in grid]

    # Determine border vs content: the border touches more distinct grid sides
    def _edge_sides(color):
        """Count how many distinct grid sides (top, bottom, left, right) this color touches."""
        sides = set()
        for r in range(h):
            for c in range(w):
                if grid[r][c] == color:
                    if r == 0:
                        sides.add("top")
                    if r == h - 1:
                        sides.add("bottom")
                    if c == 0:
                        sides.add("left")
                    if c == w - 1:
                        sides.add("right")
        return len(sides)

    colors = list(non_bg)
    s0 = _edge_sides(colors[0])
    s1 = _edge_sides(colors[1])

    if s0 > s1:
        border_color = colors[0]
        content_color = colors[1]
    elif s1 > s0:
        border_color = colors[1]
        content_color = colors[0]
    else:
        # Tie-break: border has more total cells
        c0 = sum(1 for row in grid for v in row if v == colors[0])
        c1 = sum(1 for row in grid for v in row if v == colors[1])
        if c0 >= c1:
            border_color = colors[0]
            content_color = colors[1]
        else:
            border_color = colors[1]
            content_color = colors[0]

    # Build obstacle map (border cells are obstacles)
    obstacle = [[False] * w for _ in range(h)]
    for r in range(h):
        for c in range(w):
            if grid[r][c] == border_color:
                obstacle[r][c] = True

    # Find connected components of content_color
    visited = set()
    components = []
    for r in range(h):
        for c in range(w):
            if grid[r][c] == content_color and (r, c) not in visited:
                comp = []
                queue = [(r, c)]
                visited.add((r, c))
                while queue:
                    cr, cc = queue.pop(0)
                    comp.append((cr, cc))
                    for dr, dc in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                        nr, nc = cr + dr, cc + dc
                        if 0 <= nr < h and 0 <= nc < w and (nr, nc) not in visited:
                            if grid[nr][nc] == content_color:
                                visited.add((nr, nc))
                                queue.append((nr, nc))
                components.append(comp)

    # Sort components by max row (closest to bottom/border first)
    components.sort(key=lambda comp: -max(r for r, c in comp))

    # Build output starting with bg + border
    output = [[bg_color] * w for _ in range(h)]
    for r in range(h):
        for c in range(w):
            if grid[r][c] == border_color:
                output[r][c] = border_color

    # Drop each component
    for comp in components:
        min_r = min(r for r, c in comp)
        max_r = max(r for r, c in comp)
        cols_used = set(c for r, c in comp)

        # Find effective floor: for each column the component uses,
        # find the first obstacle row below max_r
        effective_floor = h  # default: grid bottom
        for c in cols_used:
            for r in range(max_r + 1, h):
                if obstacle[r][c]:
                    effective_floor = min(effective_floor, r)
                    break

        # Find effective ceiling: for each column, first obstacle above min_r
        effective_ceiling = 0
        for c in cols_used:
            for r in range(min_r - 1, -1, -1):
                if obstacle[r][c]:
                    effective_ceiling = max(effective_ceiling, r + 1)
                    break

        section_height = effective_floor - effective_ceiling
        gap = 1 if section_height >= 4 else 0

        # Calculate drop distance
        new_bottom = effective_floor - 1 - gap
        drop = new_bottom - max_r

        if drop < 0:
            drop = 0  # can't move up

        # Place component at new position and update obstacles
        for r, c in comp:
            new_r = r + drop
            if 0 <= new_r < h:
                output[new_r][c] = content_color
                obstacle[new_r][c] = True  # acts as obstacle for next components

    return output


def zigzag_shear(grid, bg=0):
    """Apply a zigzag horizontal shear to a grid structure.

    Finds the bounding box of non-bg pixels. For each row within the bbox,
    applies a horizontal shift following a period-4 zigzag pattern.

    The phase is auto-computed from the bounding box height:
      phase = (bbox_height + 1) % 4

    The shift sequence (indexed by row offset from bbox top) cycles:
        phase 0: [ 0, -1,  0, +1]
        phase 1: [+1,  0, -1,  0]
        phase 2: [ 0, +1,  0, -1]
        phase 3: [-1,  0, +1,  0]
    """
    h = len(grid)
    w = len(grid[0]) if grid else 0
    if h == 0 or w == 0:
        return [row[:] for row in grid]

    # Find bounding box of non-bg pixels
    min_r, max_r = h, -1
    for r in range(h):
        for c in range(w):
            if grid[r][c] != bg:
                min_r = min(min_r, r)
                max_r = max(max_r, r)

    if max_r < 0:
        return [row[:] for row in grid]

    bbox_height = max_r - min_r + 1
    phase = (bbox_height + 1) % 4

    # Define the 4 shift patterns
    patterns = [
        [0, -1, 0, 1],   # phase 0
        [1, 0, -1, 0],   # phase 1
        [0, 1, 0, -1],   # phase 2
        [-1, 0, 1, 0],   # phase 3
    ]
    pat = patterns[phase]

    output = [[bg] * w for _ in range(h)]
    for r in range(h):
        if r < min_r or r > max_r:
            output[r] = grid[r][:]
            continue
        offset = r - min_r
        shift = pat[offset % 4]
        for c in range(w):
            if grid[r][c] != bg:
                nc = c + shift
                if 0 <= nc < w:
                    output[r][nc] = grid[r][c]
    return output


def block_grid_gravity(grid):
    """Compress a 30x30 block-pattern grid into a small output via gravity.

    The input has:
    - A separator line (full row or column of uniform non-0 non-8 color) on one edge
    - A 7x7 grid of block positions, each block is a 3x3 hollow square
    - Blocks are colored (various) or template (color 8)

    Algorithm:
    1. Find separator edge and determine gravity direction (CW rotation)
    2. Build 7x7 block grid (color at each position, 0 if absent)
    3. Remove the all-zero row/column (gap between sections)
    4. For each line perpendicular to separator:
       - 8-blocks anchor toward gravity side, colored blocks opposite, 0 fills rest
    """
    h = len(grid)
    w = len(grid[0]) if grid else 0

    # Find separator: full-width row or full-height column of uniform non-0, non-8 color
    sep_side = None  # "top", "bottom", "left", "right"

    # Check rows
    for r in [0, h - 1]:
        vals = set(grid[r])
        if len(vals) == 1 and vals.pop() not in (0, 8):
            sep_side = "top" if r == 0 else "bottom"
            break

    if sep_side is None:
        # Check columns
        for c in [0, w - 1]:
            vals = set(grid[r][c] for r in range(h))
            if len(vals) == 1 and vals.pop() not in (0, 8):
                sep_side = "left" if c == 0 else "right"
                break

    if sep_side is None:
        return [row[:] for row in grid]

    # Determine block grid offsets
    # Separator side gets offset 2 (skip separator + gap row/col)
    # Other sides get offset 1 (skip gap)
    row_start = 2 if sep_side == "top" else (1 if sep_side != "bottom" else 1)
    col_start = 2 if sep_side == "left" else (1 if sep_side != "right" else 1)

    # For bottom/right separator, the last block positions need to fit
    # Block at position i: rows row_start + 4*i to row_start + 4*i + 2
    # We need 7 positions: row_start + 4*6 + 2 < h (or w)

    # Build 7x7 block grid
    block_grid = [[0] * 7 for _ in range(7)]
    for br in range(7):
        for bc in range(7):
            pr = row_start + 4 * br  # physical row of block top-left
            pc = col_start + 4 * bc  # physical col of block top-left
            if 0 <= pr < h and 0 <= pc < w:
                block_grid[br][bc] = grid[pr][pc]

    # Find and remove the all-zero row and/or column
    # Remove zero rows
    filtered_rows = [row for row in block_grid if any(v != 0 for v in row)]
    # Remove zero columns
    if filtered_rows:
        n_cols = len(filtered_rows[0])
        keep_cols = [c for c in range(n_cols)
                     if any(filtered_rows[r][c] != 0 for r in range(len(filtered_rows)))]
        result_grid = [[filtered_rows[r][c] for c in keep_cols]
                       for r in range(len(filtered_rows))]
    else:
        return [[0]]

    out_h = len(result_grid)
    out_w = len(result_grid[0]) if result_grid else 0

    # Determine gravity direction and processing dimension
    # Top → Right, Right → Down, Bottom → Left, Left → Up
    if sep_side in ("top", "bottom"):
        # Process per-row
        gravity_right = (sep_side == "top")
        output = [[0] * out_w for _ in range(out_h)]
        for r in range(out_h):
            eights = []
            colored = []
            for c in range(out_w):
                v = result_grid[r][c]
                if v == 8:
                    eights.append(v)
                elif v != 0:
                    colored.append(v)
            combined = colored + eights if gravity_right else eights + colored
            total = len(combined)
            if gravity_right:
                # Right-aligned
                start = out_w - total
                for i, v in enumerate(combined):
                    output[r][start + i] = v
            else:
                # Left-aligned
                for i, v in enumerate(combined):
                    output[r][i] = v
    else:
        # Process per-column (left/right separator)
        gravity_up = (sep_side == "left")
        output = [[0] * out_w for _ in range(out_h)]
        for c in range(out_w):
            eights = []
            colored = []
            for r in range(out_h):
                v = result_grid[r][c]
                if v == 8:
                    eights.append(v)
                elif v != 0:
                    colored.append(v)
            combined = eights + colored if gravity_up else colored + eights
            total = len(combined)
            if gravity_up:
                # Top-aligned
                for i, v in enumerate(combined):
                    output[i][c] = v
            else:
                # Bottom-aligned
                start = out_h - total
                for i, v in enumerate(combined):
                    output[start + i][c] = v

    return output


def arrow_border_project(grid, bg=0):
    """Find arrow-shaped objects and project their marker colors to grid borders.

    Each arrow is a connected component of non-bg cells containing exactly two
    colors: the 'body' color (majority) and a single 'marker' cell.
    The marker's position relative to the body's center-of-mass determines
    the projection direction (up/down/left/right).

    The marker color fills the nearest border edge in that direction.
    A dotted trail of marker color is drawn every 2 cells from marker to border.
    Where two filled border edges meet at a corner, that corner becomes 0.
    """
    h = len(grid)
    w = len(grid[0]) if grid else 0
    output = [row[:] for row in grid]

    # Find connected components of non-bg cells
    visited = set()
    arrows = []
    for r in range(h):
        for c in range(w):
            if grid[r][c] == bg or (r, c) in visited:
                continue
            comp = []
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

            if len(comp) < 3:
                continue

            # Identify colors in this component
            color_cells = {}
            for pr, pc in comp:
                v = grid[pr][pc]
                color_cells.setdefault(v, []).append((pr, pc))

            if len(color_cells) != 2:
                continue

            # Body color = more cells; marker color = exactly 1 cell
            colors_sorted = sorted(color_cells.items(), key=lambda x: len(x[1]))
            marker_color, marker_cells = colors_sorted[0]
            body_color, body_cells = colors_sorted[1]

            if len(marker_cells) != 1:
                continue

            mr, mc = marker_cells[0]

            # Center of mass of body cells
            center_r = sum(p[0] for p in body_cells) / len(body_cells)
            center_c = sum(p[1] for p in body_cells) / len(body_cells)

            # Direction: marker offset from body center
            dr = mr - center_r
            dc = mc - center_c

            if abs(dr) > abs(dc):
                direction = "up" if dr < 0 else "down"
            else:
                direction = "left" if dc < 0 else "right"

            arrows.append((marker_color, (mr, mc), direction))

    if not arrows:
        return output

    # Project each arrow's marker to its border
    border_edges = {}
    for marker_color, (mr, mc), direction in arrows:
        border_edges[direction] = marker_color

        # Draw dotted trail every 2 cells from marker toward border
        if direction == "up":
            r = mr - 2
            while r >= 0:
                output[r][mc] = marker_color
                r -= 2
        elif direction == "down":
            r = mr + 2
            while r < h:
                output[r][mc] = marker_color
                r += 2
        elif direction == "left":
            c = mc - 2
            while c >= 0:
                output[mr][c] = marker_color
                c -= 2
        elif direction == "right":
            c = mc + 2
            while c < w:
                output[mr][c] = marker_color
                c += 2

    # Fill border edges
    for direction, marker_color in border_edges.items():
        if direction == "up":
            for c in range(w):
                output[0][c] = marker_color
        elif direction == "down":
            for c in range(w):
                output[h - 1][c] = marker_color
        elif direction == "left":
            for r in range(h):
                output[r][0] = marker_color
        elif direction == "right":
            for r in range(h):
                output[r][w - 1] = marker_color

    # Corners where two edges meet become 0
    filled_dirs = set(border_edges.keys())
    if "up" in filled_dirs and "left" in filled_dirs:
        output[0][0] = 0
    if "up" in filled_dirs and "right" in filled_dirs:
        output[0][w - 1] = 0
    if "down" in filled_dirs and "left" in filled_dirs:
        output[h - 1][0] = 0
    if "down" in filled_dirs and "right" in filled_dirs:
        output[h - 1][w - 1] = 0

    return output


def scattered_pixel_diamond(grid, bg=7):
    """Count two non-bg colors scattered on the grid. Build a rectangle
    (height=smaller_count, width=larger_count) in the bottom-left corner
    of the output. The rectangle is filled with color 2, with an hourglass/
    diamond pattern of color 4.

    Output grid is square, side = max(input_H, input_W) rounded up to even.
    """
    h = len(grid)
    w = len(grid[0]) if grid else 0

    # Count non-bg colors
    counts = {}
    for r in range(h):
        for c in range(w):
            v = grid[r][c]
            if v != bg:
                counts[v] = counts.get(v, 0) + 1

    colors = sorted(counts.keys())
    if len(colors) != 2:
        return [row[:] for row in grid]

    c1, c2 = counts[colors[0]], counts[colors[1]]
    rect_h = min(c1, c2)
    rect_w = max(c1, c2)

    # Output grid: square, rounded up to even
    side = max(h, w)
    if side % 2 == 1:
        side += 1

    output = [[bg] * side for _ in range(side)]

    # Rectangle at bottom-left
    rect_top = side - rect_h

    # Fill rectangle with color 2
    for r in range(rect_top, side):
        for c in range(rect_w):
            output[r][c] = 2

    # Draw diamond/hourglass of color 4
    even_w = (rect_w % 2 == 0)
    if even_w:
        n_max = rect_w // 2 - 1  # rows from pinch to reach edges
        pinch_height_candidate = 2
    else:
        n_max = rect_w // 2
        pinch_height_candidate = 1

    pinch_height = min(pinch_height_candidate, max(1, rect_h - n_max))

    pinch_start = rect_h - pinch_height - n_max  # row within rectangle
    if pinch_start < 0:
        pinch_start = 0

    center_l = rect_w // 2 - 1 if even_w else rect_w // 2
    center_r = rect_w // 2 if even_w else rect_w // 2

    for local_r in range(rect_h):
        abs_r = rect_top + local_r
        if local_r < pinch_start:
            # Above pinch: expanding upward
            d = pinch_start - local_r
            left_4 = center_l - d
            right_4 = center_r + d
        elif local_r < pinch_start + pinch_height:
            # Pinch row(s)
            left_4 = center_l
            right_4 = center_r
        else:
            # Below pinch: expanding downward
            d = local_r - (pinch_start + pinch_height - 1)
            left_4 = center_l - d
            right_4 = center_r + d

        if 0 <= left_4 < rect_w:
            output[abs_r][left_4] = 4
        if 0 <= right_4 < rect_w and right_4 != left_4:
            output[abs_r][right_4] = 4

    return output


def _extract_objects_by_color(grid, bg=0):
    """Find connected components where BFS only follows same-color neighbors."""
    h = len(grid)
    w = len(grid[0]) if grid else 0
    visited = set()
    objects = []
    for r in range(h):
        for c in range(w):
            if grid[r][c] == bg or (r, c) in visited:
                continue
            color = grid[r][c]
            comp = []
            queue = [(r, c)]
            visited.add((r, c))
            while queue:
                cr, cc = queue.pop(0)
                comp.append((cr, cc))
                for dr, dc in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                    nr, nc = cr + dr, cc + dc
                    if 0 <= nr < h and 0 <= nc < w and (nr, nc) not in visited and grid[nr][nc] == color:
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


def middle_object_pass_through(grid, bg=7):
    """Three objects on a common axis. The middle object passes through
    the rectangular outer object (the one with strictly larger cross-dimension).
    That outer object splits in half with a gap, and the middle object
    appears on the far side.

    The non-rectangular (or non-target) outer object stays unchanged.
    """
    h = len(grid)
    w = len(grid[0]) if grid else 0

    # Find objects by color (same-color connected components)
    objs = _extract_objects_by_color(grid, bg=bg)
    if len(objs) != 3:
        return [row[:] for row in grid]

    # Each object: compute bounding box center
    for obj in objs:
        t, l, oh, ow = obj["bbox"]
        obj["center_r"] = t + oh / 2
        obj["center_c"] = l + ow / 2
        # Check if it's a filled rectangle
        obj["is_rect"] = (obj["size"] == oh * ow)

    # Determine axis: vertical or horizontal stacking
    centers_r = [o["center_r"] for o in objs]
    centers_c = [o["center_c"] for o in objs]
    spread_r = max(centers_r) - min(centers_r)
    spread_c = max(centers_c) - min(centers_c)

    if spread_r >= spread_c:
        # Vertical stacking (objects differ mainly in row)
        axis = "vertical"
        objs.sort(key=lambda o: o["center_r"])
        cross_dim = lambda o: o["bbox"][3]  # width
    else:
        # Horizontal stacking
        axis = "horizontal"
        objs.sort(key=lambda o: o["center_c"])
        cross_dim = lambda o: o["bbox"][2]  # height

    A, B, C = objs[0], objs[1], objs[2]

    # B is the middle object
    b_cross = cross_dim(B)

    # Determine target: the outer object that can accommodate B (cross > B's cross)
    a_can = cross_dim(A) > b_cross
    c_can = cross_dim(C) > b_cross

    if a_can and c_can:
        # Both can accommodate - pick the one that's rectangular
        if A["is_rect"] and not C["is_rect"]:
            target, stay = A, C
            direction = -1
        elif C["is_rect"] and not A["is_rect"]:
            target, stay = C, A
            direction = 1
        else:
            # Both rectangular - pick the one with larger cross dimension
            if cross_dim(C) >= cross_dim(A):
                target, stay = C, A
                direction = 1
            else:
                target, stay = A, C
                direction = -1
    elif a_can:
        target, stay = A, C
        direction = -1
    elif c_can:
        target, stay = C, A
        direction = 1
    else:
        return [row[:] for row in grid]

    # Build output
    output = [[bg] * w for _ in range(h)]

    # Place the staying object unchanged
    for r, c in stay["positions"]:
        output[r][c] = stay["color"]

    # Split the target and place B
    t_top, t_left, t_h, t_w = target["bbox"]
    b_top, b_left, b_h, b_w = B["bbox"]

    if axis == "vertical":
        # Target splits horizontally: left half shifts left 1, right half shifts right 1
        half_w = t_w // 2

        for r, c in target["positions"]:
            rel_c = c - t_left
            if rel_c < half_w:
                new_c = c - 1  # shift left by 1
            else:
                new_c = c + 1  # shift right by 1
            if 0 <= new_c < w:
                output[r][new_c] = target["color"]

        # Place B: vertical stacking
        if direction == -1:
            b_new_top = t_top - b_h  # above target (outside)
        else:
            b_new_top = t_top + t_h - b_h  # bottom of target (inside gap)

        for r, c in B["positions"]:
            new_r = b_new_top + (r - b_top)
            if 0 <= new_r < h and 0 <= c < w:
                output[new_r][c] = B["color"]

    else:
        # Horizontal axis: top half shifts up 1, bottom half shifts down 1
        half_h = t_h // 2

        for r, c in target["positions"]:
            rel_r = r - t_top
            if rel_r < half_h:
                new_r = r - 1  # shift up by 1
            else:
                new_r = r + 1  # shift down by 1
            if 0 <= new_r < h:
                output[new_r][c] = target["color"]

        # Place B: horizontal stacking — B goes to target's column range
        b_new_left = t_left + t_w - b_w

        for r, c in B["positions"]:
            new_c = b_new_left + (c - b_left)
            if 0 <= r < h and 0 <= new_c < w:
                output[r][new_c] = B["color"]

    return output


# ============================================================
# REASSEMBLE TEMPLATE AT SCATTERED MARKERS
# ============================================================

def reassemble_template_at_markers(grid, bg=0):
    """Find template shapes and scattered marker groups, place each template
    (rotated/reflected) at the matching scattered marker positions.

    Templates: connected multi-color shapes with a dominant body color and
    minority marker colors at distinct positions.
    Scattered groups: sets of isolated single pixels whose colors together
    match a template's marker color set.

    For each scattered group, try all 8 rigid transformations (4 rotations x
    2 reflections) to find one that maps the template's marker positions to
    the scattered pixel positions. Place the transformed template and clear
    the original.
    """
    h = len(grid)
    w = len(grid[0]) if grid else 0

    # --- Find connected components (4-connected) ---
    visited = set()
    components = []
    for r in range(h):
        for c in range(w):
            if grid[r][c] == bg or (r, c) in visited:
                continue
            comp = []
            queue = [(r, c)]
            visited.add((r, c))
            while queue:
                cr, cc = queue.pop(0)
                comp.append((cr, cc, grid[cr][cc]))
                for dr, dc in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                    nr, nc = cr + dr, cc + dc
                    if 0 <= nr < h and 0 <= nc < w and (nr, nc) not in visited and grid[nr][nc] != bg:
                        visited.add((nr, nc))
                        queue.append((nr, nc))
            components.append(comp)

    # --- Classify: templates (multi-cell) vs isolated pixels (single-cell) ---
    templates = []
    isolated = []
    for comp in components:
        if len(comp) == 1:
            isolated.append((comp[0][0], comp[0][1], comp[0][2]))
        else:
            templates.append(comp)

    if not templates or not isolated:
        return [row[:] for row in grid]

    # --- Analyze each template ---
    template_info = []
    for comp in templates:
        color_counts = {}
        for r, c, color in comp:
            color_counts[color] = color_counts.get(color, 0) + 1
        body_color = max(color_counts, key=color_counts.get)
        markers = {}
        for r, c, color in comp:
            if color != body_color:
                markers[color] = (r, c)
        template_info.append({
            'body_color': body_color,
            'markers': markers,
            'all_cells': comp,
        })

    # --- Determine marker color set ---
    marker_colors = set()
    for t in template_info:
        marker_colors.update(t['markers'].keys())
    marker_colors = sorted(marker_colors)

    # --- Group isolated pixels into scattered marker groups ---
    by_color = {}
    for r, c, color in isolated:
        if color in marker_colors:
            by_color.setdefault(color, []).append((r, c))

    first_color = marker_colors[0]
    first_pixels = by_color.get(first_color, [])
    remaining = {c: list(positions) for c, positions in by_color.items()}

    scattered_groups = []
    for r0, c0 in first_pixels:
        group = {first_color: (r0, c0)}
        remaining[first_color].remove((r0, c0))
        for mc in marker_colors:
            if mc == first_color:
                continue
            best = None
            best_dist = float('inf')
            for r1, c1 in remaining.get(mc, []):
                d = abs(r1 - r0) + abs(c1 - c0)
                if d < best_dist:
                    best_dist = d
                    best = (r1, c1)
            if best:
                group[mc] = best
                remaining[mc].remove(best)
        if len(group) == len(marker_colors):
            scattered_groups.append(group)

    # --- 8 rigid transformations ---
    def _apply_xform(dr, dc, idx):
        if idx == 0: return (dr, dc)
        if idx == 1: return (dc, -dr)       # 90 CW
        if idx == 2: return (-dr, -dc)      # 180
        if idx == 3: return (-dc, dr)       # 90 CCW
        if idx == 4: return (dr, -dc)       # horiz flip
        if idx == 5: return (-dr, dc)       # vert flip
        if idx == 6: return (dc, dr)        # transpose
        if idx == 7: return (-dc, -dr)      # anti-transpose
        return (dr, dc)

    # --- Match each scattered group to a template ---
    output = [[bg] * w for _ in range(h)]
    used_templates = set()

    for group in scattered_groups:
        for ti, tinfo in enumerate(template_info):
            if ti in used_templates:
                continue
            if set(tinfo['markers'].keys()) != set(group.keys()):
                continue

            ref_color = marker_colors[0]
            ref_r, ref_c = tinfo['markers'][ref_color]
            rel_markers = {color: (r - ref_r, c - ref_c)
                           for color, (r, c) in tinfo['markers'].items()}
            rel_cells = [(r - ref_r, c - ref_c, color)
                         for r, c, color in tinfo['all_cells']]

            found = False
            for t_idx in range(8):
                t_ref = _apply_xform(*rel_markers[ref_color], t_idx)
                off_r = group[ref_color][0] - t_ref[0]
                off_c = group[ref_color][1] - t_ref[1]

                match = True
                for color in group:
                    t_pos = _apply_xform(*rel_markers[color], t_idx)
                    if (off_r + t_pos[0], off_c + t_pos[1]) != group[color]:
                        match = False
                        break

                if match:
                    for dr, dc, color in rel_cells:
                        tdr, tdc = _apply_xform(dr, dc, t_idx)
                        nr = off_r + tdr
                        nc = off_c + tdc
                        if 0 <= nr < h and 0 <= nc < w:
                            output[nr][nc] = color
                    used_templates.add(ti)
                    found = True
                    break

            if found:
                break

    return output


# ============================================================
# L-SHAPE TOWARD NEAREST CORNER
# ============================================================

def l_shape_nearest_corner(grid, bg=0):
    """For each non-bg pixel, draw an L-shape extending to its nearest grid corner.

    The pixel extends a line toward the nearest corner in both the row and
    column direction, forming an L. The pixel's color is used for the lines.
    """
    h = len(grid)
    w = len(grid[0]) if grid else 0
    output = [row[:] for row in grid]

    # Find all non-bg pixels
    pixels = []
    for r in range(h):
        for c in range(w):
            if grid[r][c] != bg:
                pixels.append((r, c, grid[r][c]))

    for r, c, color in pixels:
        # Distances to each corner
        corners = {
            "tl": r + c,
            "tr": r + (w - 1 - c),
            "bl": (h - 1 - r) + c,
            "br": (h - 1 - r) + (w - 1 - c),
        }
        nearest = min(corners, key=corners.get)

        # Determine row and col directions
        if nearest in ("tl", "tr"):
            row_range = range(0, r)  # extend upward
        else:
            row_range = range(r + 1, h)  # extend downward

        if nearest in ("tl", "bl"):
            col_range = range(0, c)  # extend left
        else:
            col_range = range(c + 1, w)  # extend right

        # Draw vertical line
        for row_idx in row_range:
            output[row_idx][c] = color
        # Draw horizontal line
        for col_idx in col_range:
            output[r][col_idx] = color

    return output


# ============================================================
# ROTATION TILING (2x2 of rotations)
# ============================================================

def rotation_tile_2x2(grid):
    """Tile a grid into a 2x2 arrangement of rotated copies.

    Layout:
      top-left:     original
      top-right:    rotate 90 CCW (= rotate 270 CW)
      bottom-left:  rotate 180
      bottom-right: rotate 90 CW
    """
    identity = [row[:] for row in grid]
    rot90cw = rotate_cw(grid, 1)
    rot180 = rotate_cw(grid, 2)
    rot90ccw = rotate_cw(grid, 3)

    top = concat_horizontal(identity, rot90ccw)
    bottom = concat_horizontal(rot180, rot90cw)
    return concat_vertical(top, bottom)


# ============================================================
# DIAGONAL COLOR PROJECTION FROM 2x2 BLOCK
# ============================================================

def diagonal_project_2x2(grid, bg=0):
    """Find a 2x2 block of non-bg cells. Project each cell's color diagonally
    to a mirrored rectangle adjacent to the block (at most 2x2, clamped to space).

    TL cell color -> bottom-right adjacent block
    TR cell color -> bottom-left adjacent block
    BL cell color -> top-right adjacent block
    BR cell color -> top-left adjacent block
    """
    h = len(grid)
    w = len(grid[0]) if grid else 0
    output = [row[:] for row in grid]

    # Find the 2x2 block
    block_r, block_c = None, None
    for r in range(h - 1):
        for c in range(w - 1):
            if (grid[r][c] != bg and grid[r][c + 1] != bg and
                    grid[r + 1][c] != bg and grid[r + 1][c + 1] != bg):
                block_r, block_c = r, c
                break
        if block_r is not None:
            break

    if block_r is None:
        return grid

    tl = grid[block_r][block_c]
    tr = grid[block_r][block_c + 1]
    bl = grid[block_r + 1][block_c]
    br = grid[block_r + 1][block_c + 1]

    space_above = block_r
    space_below = h - block_r - 2
    space_left = block_c
    space_right = w - block_c - 2

    # Top-left: rows above, cols left -> fill with BR, size min(above,2) x min(left,2)
    sr, sc = min(space_above, 2), min(space_left, 2)
    for r in range(block_r - sr, block_r):
        for c in range(block_c - sc, block_c):
            output[r][c] = br

    # Top-right: rows above, cols right -> fill with BL
    sr, sc = min(space_above, 2), min(space_right, 2)
    for r in range(block_r - sr, block_r):
        for c in range(block_c + 2, block_c + 2 + sc):
            output[r][c] = bl

    # Bottom-left: rows below, cols left -> fill with TR
    sr, sc = min(space_below, 2), min(space_left, 2)
    for r in range(block_r + 2, block_r + 2 + sr):
        for c in range(block_c - sc, block_c):
            output[r][c] = tr

    # Bottom-right: rows below, cols right -> fill with TL
    sr, sc = min(space_below, 2), min(space_right, 2)
    for r in range(block_r + 2, block_r + 2 + sr):
        for c in range(block_c + 2, block_c + 2 + sc):
            output[r][c] = tl

    return output


# ============================================================
# TILE PATTERN UPWARD
# ============================================================

def tile_pattern_upward(grid):
    """Find the non-bg pattern at the bottom of the grid, tile it upward cyclically.

    The background color is auto-detected as the most frequent color.
    The pattern is the contiguous block of rows at the bottom that contain non-bg cells.
    Empty rows above are filled by tiling the pattern cyclically from the bottom.
    """
    h = len(grid)
    w = len(grid[0]) if grid else 0
    bg = find_bg_color(grid)

    # Find where the pattern starts (first non-uniform-bg row from bottom)
    pattern_start = h
    for r in range(h - 1, -1, -1):
        if any(grid[r][c] != bg for c in range(w)):
            pattern_start = r
        else:
            break

    if pattern_start >= h:
        return [row[:] for row in grid]

    pattern = [grid[r][:] for r in range(pattern_start, h)]
    pat_h = len(pattern)

    output = [row[:] for row in grid]

    # Fill rows above pattern_start by tiling cyclically
    empty_rows = pattern_start
    for i in range(empty_rows):
        # Which pattern row? Tile from bottom: row (empty_rows - 1) maps to pattern row (pat_h - 1)
        # row i from top -> distance from pattern_start = pattern_start - 1 - i
        # pattern index = (pat_h - 1 - (pattern_start - 1 - i)) % pat_h
        pat_idx = (pat_h - (pattern_start - i) % pat_h) % pat_h
        output[i] = pattern[pat_idx][:]

    return output


def extend_diagonal_arms(grid, bg=0):
    """Find a 2x2 block with single-pixel diagonal arms, extend arms to grid edges."""
    h = len(grid)
    w = len(grid[0]) if grid else 0
    output = [row[:] for row in grid]

    colors = set()
    for row in grid:
        for v in row:
            if v != bg:
                colors.add(v)

    for color in colors:
        for r in range(h - 1):
            for c in range(w - 1):
                if (grid[r][c] == color and grid[r][c + 1] == color and
                        grid[r + 1][c] == color and grid[r + 1][c + 1] == color):
                    arms = []
                    if r - 1 >= 0 and c - 1 >= 0 and grid[r - 1][c - 1] == color:
                        arms.append((-1, -1, r - 1, c - 1))
                    if r - 1 >= 0 and c + 2 < w and grid[r - 1][c + 2] == color:
                        arms.append((-1, 1, r - 1, c + 2))
                    if r + 2 < h and c - 1 >= 0 and grid[r + 2][c - 1] == color:
                        arms.append((1, -1, r + 2, c - 1))
                    if r + 2 < h and c + 2 < w and grid[r + 2][c + 2] == color:
                        arms.append((1, 1, r + 2, c + 2))

                    for dr, dc, sr, sc in arms:
                        nr, nc = sr + dr, sc + dc
                        while 0 <= nr < h and 0 <= nc < w:
                            output[nr][nc] = color
                            nr += dr
                            nc += dc

    return output


def count_inside_bordered_rect(grid, bg=0):
    """Find rectangle bordered with 1s, count colored pixels inside, return 3x3 grid."""
    h = len(grid)
    w = len(grid[0]) if grid else 0
    border_color = 1

    best_rect = None
    for r in range(h):
        for c in range(w):
            if grid[r][c] != border_color:
                continue
            right = c
            while right < w and grid[r][right] == border_color:
                right += 1
            right -= 1
            if right <= c:
                continue
            bottom = r
            while bottom < h and grid[bottom][c] == border_color:
                bottom += 1
            bottom -= 1
            if bottom <= r:
                continue
            rect_w = right - c + 1
            rect_h = bottom - r + 1
            if rect_w < 3 or rect_h < 3:
                continue
            top_ok = all(grid[r][cc] == border_color for cc in range(c, right + 1))
            bot_ok = all(grid[bottom][cc] == border_color for cc in range(c, right + 1))
            left_ok = all(grid[rr][c] == border_color for rr in range(r, bottom + 1))
            right_ok = all(grid[rr][right] == border_color for rr in range(r, bottom + 1))
            if top_ok and bot_ok and left_ok and right_ok:
                area = rect_w * rect_h
                if best_rect is None or area > best_rect[4]:
                    best_rect = (r, c, bottom, right, area)

    if best_rect is None:
        return [[bg] * 3 for _ in range(3)]

    top, left, bottom, right, _ = best_rect
    inside_color = None
    count = 0
    for rr in range(top + 1, bottom):
        for cc in range(left + 1, right):
            v = grid[rr][cc]
            if v != bg and v != border_color:
                count += 1
                inside_color = v

    if inside_color is None:
        inside_color = bg

    result = [[bg] * 3 for _ in range(3)]
    filled = 0
    for rr in range(3):
        for cc in range(3):
            if filled < count:
                result[rr][cc] = inside_color
                filled += 1
    return result


def fill_enclosed_rectangles(grid, border_color=2, fill_color=1, bg=0):
    """Find all fully enclosed rectangles, fill interior bg-cells with fill_color."""
    h = len(grid)
    w = len(grid[0]) if grid else 0
    output = [row[:] for row in grid]

    filled_rects = set()

    for r in range(h):
        for c in range(w):
            if grid[r][c] != border_color:
                continue
            for right in range(c + 2, w):
                if grid[r][right] != border_color:
                    continue
                if not all(grid[r][cc] == border_color for cc in range(c, right + 1)):
                    continue
                for bottom in range(r + 2, h):
                    if grid[bottom][c] != border_color:
                        continue
                    if not all(grid[bottom][cc] == border_color for cc in range(c, right + 1)):
                        continue
                    if not all(grid[rr][c] == border_color for rr in range(r, bottom + 1)):
                        continue
                    if not all(grid[rr][right] == border_color for rr in range(r, bottom + 1)):
                        continue
                    rect_key = (r, c, bottom, right)
                    if rect_key not in filled_rects:
                        filled_rects.add(rect_key)
                        for rr in range(r + 1, bottom):
                            for cc in range(c + 1, right):
                                if output[rr][cc] == bg:
                                    output[rr][cc] = fill_color

    return output


def extract_bordered_rect_swap(grid, bg=0):
    """Extract the non-bg bordered rectangle and swap border/interior colors.

    Finds a rectangle on a bg grid that has an outer border of one color
    and an interior of another color. Extracts just the rectangle and swaps
    the two colors (border becomes interior, interior becomes border).
    """
    h = len(grid)
    w = len(grid[0]) if grid else 0

    # Find bounding box of all non-bg cells
    min_r, max_r, min_c, max_c = h, -1, w, -1
    for r in range(h):
        for c in range(w):
            if grid[r][c] != bg:
                min_r = min(min_r, r)
                max_r = max(max_r, r)
                min_c = min(min_c, c)
                max_c = max(max_c, c)

    if max_r < 0:
        return grid

    # Extract the sub-rectangle
    sub = [row[min_c:max_c + 1] for row in grid[min_r:max_r + 1]]
    sh = len(sub)
    sw = len(sub[0])

    # Identify the two non-bg colors
    colors = set()
    for r in range(sh):
        for c in range(sw):
            if sub[r][c] != bg:
                colors.add(sub[r][c])

    if len(colors) != 2:
        return sub  # fallback

    # Border color is the one on the edge of the sub-rectangle
    border_color = sub[0][0]
    inner_color = (colors - {border_color}).pop()

    # Swap colors
    out = []
    for r in range(sh):
        row = []
        for c in range(sw):
            v = sub[r][c]
            if v == border_color:
                row.append(inner_color)
            elif v == inner_color:
                row.append(border_color)
            else:
                row.append(v)
        out.append(row)
    return out


def denoise_rectangles(grid, bg=0):
    """Remove isolated noise pixels and keep only solid rectangular blocks.

    A pixel is kept only if it belongs to at least one 2x2 all-foreground
    sub-rectangle. This removes isolated noise pixels and single-pixel
    protrusions from rectangles.
    """
    h = len(grid)
    w = len(grid[0]) if grid else 0
    if h == 0 or w == 0:
        return grid

    # Find non-bg color (assume single non-bg color)
    fg = None
    for r in range(h):
        for c in range(w):
            if grid[r][c] != bg:
                fg = grid[r][c]
                break
        if fg is not None:
            break
    if fg is None:
        return grid

    # Mark cells that belong to at least one 2x2 all-fg block
    keep = [[False] * w for _ in range(h)]
    for r in range(h - 1):
        for c in range(w - 1):
            if (grid[r][c] == fg and grid[r][c + 1] == fg and
                    grid[r + 1][c] == fg and grid[r + 1][c + 1] == fg):
                keep[r][c] = True
                keep[r][c + 1] = True
                keep[r + 1][c] = True
                keep[r + 1][c + 1] = True

    output = [[bg] * w for _ in range(h)]
    for r in range(h):
        for c in range(w):
            if keep[r][c]:
                output[r][c] = fg
    return output


# ============================================================
# ROTATION TILE 4x4 (2x2 macro-blocks, each doubled)
# ============================================================

def rotation_tile_4x4(grid):
    """Tile a grid into a 4x4 arrangement using four rotations.

    The 12x12 output (from 3x3 input) is a 2x2 macro-grid of rotation
    quadrants, each quadrant tiled 2x2 with the same rotation:

        TL: R180   TR: R90CW
        BL: R270   BR: original
    """
    r90 = rotate_cw(grid, 1)
    r180 = rotate_cw(grid, 2)
    r270 = rotate_cw(grid, 3)
    orig = [row[:] for row in grid]

    def tile2x2(g):
        top = concat_horizontal(g, [r[:] for r in g])
        bot = concat_horizontal([r[:] for r in g], [r[:] for r in g])
        return concat_vertical(top, bot)

    tl = tile2x2(r180)
    tr = tile2x2(r90)
    bl = tile2x2(r270)
    br = tile2x2(orig)

    top = concat_horizontal(tl, tr)
    bottom = concat_horizontal(bl, br)
    return concat_vertical(top, bottom)


# ============================================================
# COLOR REMAP FROM KEY PAIRS
# ============================================================

def color_remap_from_keys(grid, bg=0):
    """Find a pattern rectangle and scattered 2-cell color key pairs.

    Each horizontal key pair (a, b) defines a mapping b -> a.
    The pattern rectangle is extracted and remapped accordingly.
    """
    h = len(grid)
    w = len(grid[0]) if grid else 0

    # Find connected components of non-bg cells using flood fill
    visited = [[False] * w for _ in range(h)]
    components = []

    def flood(r, c):
        stack = [(r, c)]
        cells = []
        while stack:
            cr, cc = stack.pop()
            if cr < 0 or cr >= h or cc < 0 or cc >= w:
                continue
            if visited[cr][cc] or grid[cr][cc] == bg:
                continue
            visited[cr][cc] = True
            cells.append((cr, cc))
            for dr, dc in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                stack.append((cr + dr, cc + dc))
        return cells

    for r in range(h):
        for c in range(w):
            if not visited[r][c] and grid[r][c] != bg:
                cells = flood(r, c)
                if cells:
                    components.append(cells)

    # Separate key pairs (exactly 2 cells, horizontal, different colors)
    # from the pattern (largest component)
    key_pairs = []
    pattern_comp = None
    max_size = 0

    for comp in components:
        if len(comp) == 2:
            (r1, c1), (r2, c2) = comp
            # Horizontal adjacency
            if r1 == r2 and abs(c1 - c2) == 1:
                a = grid[r1][min(c1, c2)]
                b = grid[r1][max(c1, c2)]
                if a != b:
                    key_pairs.append((a, b))
                    continue
        if len(comp) > max_size:
            max_size = len(comp)
            pattern_comp = comp

    if pattern_comp is None:
        return grid

    # Build color mapping: each pair (a, b) means b -> a
    mapping = {}
    for a, b in key_pairs:
        mapping[b] = a

    # Extract bounding box of pattern
    min_r = min(r for r, c in pattern_comp)
    max_r = max(r for r, c in pattern_comp)
    min_c = min(c for r, c in pattern_comp)
    max_c = max(c for r, c in pattern_comp)

    sub = []
    for r in range(min_r, max_r + 1):
        row = []
        for c in range(min_c, max_c + 1):
            v = grid[r][c]
            row.append(mapping.get(v, v))
        sub.append(row)

    return sub


# ============================================================
# MARK SQUARE FRAME CORNERS
# ============================================================

def mark_square_frame_corners(grid, marker_color=2, bg=7):
    """Find square rectangular frames and mark their corners.

    A square frame is a connected component whose bounding box is square
    (h == w, h >= 2), and whose cells exactly match the perimeter of that
    bounding box.

    For each qualifying frame with bounding box (r1,c1)-(r2,c2), place
    marker_color at the 8 corner extension positions:
      (r1-1,c1), (r1-1,c2), (r1,c1-1), (r1,c2+1),
      (r2,c1-1), (r2,c2+1), (r2+1,c1), (r2+1,c2)
    """
    h = len(grid)
    w = len(grid[0]) if grid else 0
    output = [row[:] for row in grid]

    # Find connected components
    visited = [[False] * w for _ in range(h)]
    components = []

    def flood(r, c, color):
        stack = [(r, c)]
        cells = set()
        while stack:
            cr, cc = stack.pop()
            if cr < 0 or cr >= h or cc < 0 or cc >= w:
                continue
            if visited[cr][cc] or grid[cr][cc] != color:
                continue
            visited[cr][cc] = True
            cells.add((cr, cc))
            for dr, dc in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                stack.append((cr + dr, cc + dc))
        return cells

    for r in range(h):
        for c in range(w):
            if not visited[r][c] and grid[r][c] != bg:
                cells = flood(r, c, grid[r][c])
                if cells:
                    components.append(cells)

    for cells in components:
        min_r = min(r for r, c in cells)
        max_r = max(r for r, c in cells)
        min_c = min(c for r, c in cells)
        max_c = max(c for r, c in cells)
        bh = max_r - min_r + 1
        bw = max_c - min_c + 1

        # Must be square and at least 2x2
        if bh != bw or bh < 2:
            continue

        # Check cells match the perimeter of the bounding box
        perimeter = set()
        for r in range(min_r, max_r + 1):
            for c in range(min_c, max_c + 1):
                if r == min_r or r == max_r or c == min_c or c == max_c:
                    perimeter.add((r, c))

        if cells != perimeter:
            continue

        # Place markers at the 8 corner extension positions
        markers = [
            (min_r - 1, min_c), (min_r - 1, max_c),
            (min_r, min_c - 1), (min_r, max_c + 1),
            (max_r, min_c - 1), (max_r, max_c + 1),
            (max_r + 1, min_c), (max_r + 1, max_c),
        ]
        for mr, mc in markers:
            if 0 <= mr < h and 0 <= mc < w:
                output[mr][mc] = marker_color

    return output


def border_interior_fill(grid, target_color, border_color, interior_color):
    """Classify connected components of target_color cells (4-connected).
    Components touching the grid border are recolored to border_color.
    Components not touching the border are recolored to interior_color."""
    h = len(grid)
    w = len(grid[0]) if grid else 0
    result = [row[:] for row in grid]
    visited = set()

    for r in range(h):
        for c in range(w):
            if grid[r][c] == target_color and (r, c) not in visited:
                comp = []
                touches_border = False
                queue = [(r, c)]
                visited.add((r, c))
                while queue:
                    cr, cc = queue.pop(0)
                    comp.append((cr, cc))
                    if cr == 0 or cr == h - 1 or cc == 0 or cc == w - 1:
                        touches_border = True
                    for dr, dc in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                        nr, nc = cr + dr, cc + dc
                        if 0 <= nr < h and 0 <= nc < w and (nr, nc) not in visited and grid[nr][nc] == target_color:
                            visited.add((nr, nc))
                            queue.append((nr, nc))
                fill = border_color if touches_border else interior_color
                for cr, cc in comp:
                    result[cr][cc] = fill

    return result


def most_common_cross_arm_color(grid, center_color=4):
    """Find all cross patterns where center_color is at the center and all 4
    cardinal neighbors share the same color (different from center_color).
    Returns a 1x1 grid containing the arm color that appears most often."""
    h = len(grid)
    w = len(grid[0]) if grid else 0
    arm_colors = []

    for r in range(1, h - 1):
        for c in range(1, w - 1):
            if grid[r][c] == center_color:
                up = grid[r - 1][c]
                down = grid[r + 1][c]
                left = grid[r][c - 1]
                right = grid[r][c + 1]
                if up == down == left == right and up != center_color:
                    arm_colors.append(up)

    if not arm_colors:
        return [[0]]

    counts = {}
    for ac in arm_colors:
        counts[ac] = counts.get(ac, 0) + 1
    best = max(counts, key=counts.get)
    return [[best]]


def denoise_swap_sections(grid, noise_color=5, sep_val=0):
    """Denoise a grid divided into sections by separators, then swap pattern/solid.

    The grid is divided into rectangular sections by separator rows/cols.
    Separators contain only sep_val (0) or noise_color (5).
    Some section cells are corrupted by noise_color.

    Each section is either a 'pattern' (2+ colors) or 'solid minority' (all minority color).
    The output swaps them: pattern sections become solid base color,
    solid minority sections get the pattern template.
    Separators are restored to all sep_val.
    """
    h = len(grid)
    w = len(grid[0]) if grid else 0
    if h == 0 or w == 0:
        return grid

    # Step 1: Find separator rows and cols (all cells are sep_val or noise_color)
    sep_rows = [r for r in range(h)
                if all(grid[r][c] in (sep_val, noise_color) for c in range(w))]
    sep_cols = [c for c in range(w)
                if all(grid[r][c] in (sep_val, noise_color) for r in range(h))]

    # Build row/col ranges for sections
    def make_ranges(seps, total):
        ranges = []
        prev = 0
        for s in seps:
            if s > prev:
                ranges.append((prev, s))
            prev = s + 1
        if prev < total:
            ranges.append((prev, total))
        return ranges

    row_ranges = make_ranges(sep_rows, h)
    col_ranges = make_ranges(sep_cols, w)

    if not row_ranges or not col_ranges:
        return grid

    # Step 2: Extract sections and their non-noise color sets
    sections = {}
    for ri, (r0, r1) in enumerate(row_ranges):
        for ci, (c0, c1) in enumerate(col_ranges):
            cells = []
            non_noise = set()
            for r in range(r0, r1):
                row = []
                for c in range(c0, c1):
                    v = grid[r][c]
                    row.append(v)
                    if v != noise_color:
                        non_noise.add(v)
                cells.append(row)
            sections[(ri, ci)] = {"cells": cells, "non_noise": non_noise,
                                  "r0": r0, "r1": r1, "c0": c0, "c1": c1}

    # Step 3: Find the pattern template from a clean section with 2+ non-noise colors
    template = None
    for key, sec in sections.items():
        has_noise = any(cell == noise_color for row in sec["cells"] for cell in row)
        if not has_noise and len(sec["non_noise"]) >= 2:
            template = [row[:] for row in sec["cells"]]
            break

    if template is None:
        return grid

    # Step 4: Determine base color and minority color
    color_count = {}
    for row in template:
        for v in row:
            color_count[v] = color_count.get(v, 0) + 1
    base_color = max(color_count, key=color_count.get)
    minority_color = min(color_count, key=color_count.get)

    # Step 5: Build output
    sec_h = len(template)
    sec_w = len(template[0])
    pure_section = [[base_color] * sec_w for _ in range(sec_h)]

    output = [[sep_val] * w for _ in range(h)]

    for (ri, ci), sec in sections.items():
        r0, c0 = sec["r0"], sec["c0"]
        # If all non-noise cells are minority color -> place pattern
        if sec["non_noise"] == {minority_color}:
            fill = template
        else:
            fill = pure_section
        for dr, row in enumerate(fill):
            for dc, v in enumerate(row):
                output[r0 + dr][c0 + dc] = v

    return output


def compress_grid_intersections(grid, bg=0):
    """Extract colored intersections from a separator-grid and compress.

    The input is a large grid with regular separator lines forming a grid pattern.
    Some separator-line intersections have been replaced with non-separator colors.
    This primitive:
    1. Detects separator rows/cols (rows/cols with no bg cells)
    2. Finds the separator color (most frequent in those rows)
    3. Builds an intersection grid of non-separator colors
    4. Finds the bounding box of colored intersections
    5. Compresses NxN -> (N-1)x(N-1) via agreement regions
       (corners stay, edge pairs and center 2x2 must agree or become 0)
    """
    h = len(grid)
    w = len(grid[0]) if grid else 0
    if h == 0 or w == 0:
        return grid

    # Step 1: Find separator rows (rows containing no bg cells)
    sep_rows = []
    for r in range(h):
        if all(grid[r][c] != bg for c in range(w)):
            sep_rows.append(r)

    # Find separator cols (cols containing no bg cells)
    sep_cols = []
    for c in range(w):
        if all(grid[r][c] != bg for r in range(h)):
            sep_cols.append(c)

    if not sep_rows or not sep_cols:
        return grid

    # Step 2: Determine separator color (most frequent across sep rows)
    color_count = {}
    for r in sep_rows:
        for c in range(w):
            v = grid[r][c]
            color_count[v] = color_count.get(v, 0) + 1
    sep_color = max(color_count, key=color_count.get)

    # Step 3: Build intersection grid (sep_row x sep_col), replacing sep_color with 0
    inter = []
    for r in sep_rows:
        row = []
        for c in sep_cols:
            v = grid[r][c]
            row.append(0 if v == sep_color else v)
        inter.append(row)

    # Step 4: Bounding box of non-zero cells
    min_r = min_c = float('inf')
    max_r = max_c = -1
    for r in range(len(inter)):
        for c in range(len(inter[0])):
            if inter[r][c] != 0:
                min_r = min(min_r, r)
                max_r = max(max_r, r)
                min_c = min(min_c, c)
                max_c = max(max_c, c)

    if max_r < 0:
        return [[0]]

    bbox = [inter[r][min_c:max_c + 1] for r in range(min_r, max_r + 1)]
    N = len(bbox)
    M = len(bbox[0])

    # Step 5: Compress by grouping first, middle, last rows/cols
    def make_groups(size):
        if size <= 2:
            return [[i] for i in range(size)]
        return [[0]] + [list(range(1, size - 1))] + [[size - 1]]

    row_groups = make_groups(N)
    col_groups = make_groups(M)

    output = []
    for rg in row_groups:
        row = []
        for cg in col_groups:
            vals = set()
            for r in rg:
                for c in cg:
                    vals.add(bbox[r][c])
            row.append(vals.pop() if len(vals) == 1 else 0)
        output.append(row)

    return output
