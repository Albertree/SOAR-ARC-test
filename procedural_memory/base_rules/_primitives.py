"""
_primitives.py -- Atomic grid operations for the concept engine.

Every grid-transforming function takes grid (list[list[int]]) as first arg,
returns list[list[int]]. No ARCKG dependency. Pure functions, no side effects.
"""

from procedural_memory.base_rules._helpers import find_components, group_positions


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


def count_color(grid, color):
    """Count occurrences of a color."""
    return sum(row.count(color) for row in grid)


def unique_colors(grid, exclude_bg=True):
    """Return sorted list of unique colors in grid. Optionally exclude background."""
    bg = find_bg_color(grid) if exclude_bg else None
    colors = set()
    for row in grid:
        for c in row:
            if c != bg:
                colors.add(c)
    return sorted(colors)


# ============================================================
# HIGHER-LEVEL primitives (composable, parameterized operations)
# ============================================================

def recolor_components_by_rank(grid, source_color, sort_key, start_color):
    """Find connected components of source_color, sort by sort_key, recolor sequentially.
    sort_key: 'top_row' | 'top_col' | 'size' | 'size_desc'
    Assigns start_color to first component, start_color+1 to second, etc."""
    h = len(grid)
    w = len(grid[0]) if grid else 0
    # Find all cells of source_color
    target_cells = [(r, c) for r in range(h) for c in range(w) if grid[r][c] == source_color]
    if not target_cells:
        return [row[:] for row in grid]

    # Group into connected components
    groups = group_positions(target_cells)

    # Sort by key
    def _sort_val(group):
        if sort_key == "top_row":
            return min(r for r, c in group)
        if sort_key == "top_col":
            return min(c for r, c in group)
        if sort_key == "size":
            return len(group)
        if sort_key == "size_desc":
            return -len(group)
        return 0

    sorted_groups = sorted(groups, key=_sort_val)

    output = [row[:] for row in grid]
    for idx, group in enumerate(sorted_groups):
        new_color = start_color + idx
        for r, c in group:
            output[r][c] = new_color
    return output


def recolor_components_by_size_group(grid, source_color, sort_order, start_color):
    """Find connected components of source_color, group by size, recolor by group rank.
    sort_order: 'desc' (largest first) | 'asc' (smallest first)
    All components of the same size get the same color."""
    h = len(grid)
    w = len(grid[0]) if grid else 0
    target_cells = [(r, c) for r in range(h) for c in range(w) if grid[r][c] == source_color]
    if not target_cells:
        return [row[:] for row in grid]

    groups = group_positions(target_cells)

    # Get unique sizes sorted
    sizes = sorted(set(len(g) for g in groups), reverse=(sort_order == "desc"))
    size_to_color = {s: start_color + i for i, s in enumerate(sizes)}

    output = [row[:] for row in grid]
    for group in groups:
        color = size_to_color[len(group)]
        for r, c in group:
            output[r][c] = color
    return output


def fill_quadrants_from_corners(grid, marker_color, bg=0):
    """Find rectangles of marker_color, locate 4 diagonal corner pixels,
    fill each quadrant with the corresponding corner color, remove corners."""
    h = len(grid)
    w = len(grid[0]) if grid else 0

    # Find connected components of marker_color
    comps = find_components(grid, marker_color)
    if not comps:
        return [row[:] for row in grid]

    output = [row[:] for row in grid]

    for comp in comps:
        min_r = min(r for r, c in comp)
        max_r = max(r for r, c in comp)
        min_c = min(c for r, c in comp)
        max_c = max(c for r, c in comp)

        rect_h = max_r - min_r + 1
        rect_w = max_c - min_c + 1

        # Find the 4 corner colors (diagonally adjacent to the rectangle corners)
        corners = [
            (min_r - 1, min_c - 1),  # top-left
            (min_r - 1, max_c + 1),  # top-right
            (max_r + 1, min_c - 1),  # bottom-left
            (max_r + 1, max_c + 1),  # bottom-right
        ]

        corner_colors = []
        for cr, cc in corners:
            if 0 <= cr < h and 0 <= cc < w and grid[cr][cc] != bg and grid[cr][cc] != marker_color:
                corner_colors.append(grid[cr][cc])
            else:
                corner_colors = []
                break

        if len(corner_colors) != 4:
            continue

        # Remove corner pixels
        for cr, cc in corners:
            output[cr][cc] = bg

        # Fill quadrants
        mid_r = min_r + rect_h // 2
        mid_c = min_c + rect_w // 2

        for r in range(min_r, max_r + 1):
            for c in range(min_c, max_c + 1):
                if r < mid_r and c < mid_c:
                    output[r][c] = corner_colors[0]  # top-left
                elif r < mid_r and c >= mid_c:
                    output[r][c] = corner_colors[1]  # top-right
                elif r >= mid_r and c < mid_c:
                    output[r][c] = corner_colors[2]  # bottom-left
                else:
                    output[r][c] = corner_colors[3]  # bottom-right

    return output


def reverse_frame_colors(grid):
    """Detect concentric rectangular frames, reverse their color order.
    Peels frames from outside in, collects colors, then reassigns reversed."""
    h = len(grid)
    w = len(grid[0]) if grid else 0
    if h == 0 or w == 0:
        return [row[:] for row in grid]

    # Peel frames layer by layer
    frames = []  # list of (set_of_positions, color)
    remaining = set((r, c) for r in range(h) for c in range(w))
    layer = 0
    while remaining:
        min_r = min(r for r, c in remaining)
        max_r = max(r for r, c in remaining)
        min_c = min(c for r, c in remaining)
        max_c = max(c for r, c in remaining)
        border = set()
        for r, c in remaining:
            if r == min_r or r == max_r or c == min_c or c == max_c:
                border.add((r, c))
        if not border:
            break
        # Get the color of this frame (should be uniform)
        colors = set(grid[r][c] for r, c in border)
        if len(colors) != 1:
            break  # not uniform frame, bail
        frames.append((border, colors.pop()))
        remaining -= border
        layer += 1

    if not frames:
        return [row[:] for row in grid]

    # Reverse the color assignment
    colors_reversed = [f[1] for f in reversed(frames)]
    output = [row[:] for row in grid]
    for i, (positions, _) in enumerate(frames):
        for r, c in positions:
            output[r][c] = colors_reversed[i]
    return output


def staircase_expand(grid):
    """Expand a 1-row grid with colored prefix into a staircase triangle.
    Input: 1 row with K colored cells followed by zeros.
    Output: K rows where row i has (K-i) colored cells."""
    if len(grid) != 1:
        return None
    row = grid[0]
    w = len(row)
    bg = 0
    # Find colored prefix length
    k = 0
    for c in row:
        if c != bg:
            k += 1
        else:
            break
    if k == 0:
        return None
    # Build staircase
    output = []
    for i in range(k):
        new_row = [bg] * w
        for j in range(k - i):
            new_row[j] = row[j]
        output.append(new_row)
    return output


def staircase_grow(grid):
    """Expand a 1-row grid with colored prefix into a growing staircase.
    Input: 1 row with K colored cells followed by zeros, width W.
    Output: W/2 rows where row i has (K+i) colored cells."""
    if len(grid) != 1:
        return None
    row = grid[0]
    w = len(row)
    bg = 0
    # Find colored prefix length and color
    k = 0
    color = None
    for c in row:
        if c != bg:
            k += 1
            color = c
        else:
            break
    if k == 0 or color is None:
        return None
    num_rows = w // 2
    output = []
    for i in range(num_rows):
        new_row = [bg] * w
        for j in range(k + i):
            if j < w:
                new_row[j] = color
        output.append(new_row)
    return output


def draw_turn_path(grid, path_color, cw_color, ccw_color, bg=0):
    """Draw an L-shaped path from the path_color pixel, turning at waypoints.
    Start at the path_color pixel, go RIGHT.
    When next cell is cw_color: turn clockwise (don't enter the waypoint cell).
    When next cell is ccw_color: turn counterclockwise.
    When next cell is out of bounds: stop.
    Draws the path in path_color, leaving waypoint cells unchanged."""
    h = len(grid)
    w = len(grid[0]) if grid else 0
    output = [row[:] for row in grid]

    # Find start position (path_color pixel)
    start = None
    for r in range(h):
        for c in range(w):
            if grid[r][c] == path_color:
                start = (r, c)
                break
        if start:
            break
    if not start:
        return output

    # Direction vectors: RIGHT=0, DOWN=1, LEFT=2, UP=3
    dirs = [(0, 1), (1, 0), (0, -1), (-1, 0)]
    dir_idx = 0  # Start going RIGHT

    r, c = start
    output[r][c] = path_color

    while True:
        dr, dc = dirs[dir_idx]
        nr, nc = r + dr, c + dc

        if nr < 0 or nr >= h or nc < 0 or nc >= w:
            break

        cell = grid[nr][nc]

        if cell == bg or cell == path_color:
            output[nr][nc] = path_color
            r, c = nr, nc
        elif cell == cw_color:
            dir_idx = (dir_idx + 1) % 4  # clockwise
        elif cell == ccw_color:
            dir_idx = (dir_idx - 1) % 4  # counterclockwise
        else:
            break

    return output


def gravity_rigid_body(grid, bg=0):
    """Drop content objects downward as rigid bodies with 1-row gap above walls.
    Auto-detects wall (non-bg color in bottom row) and content (all other non-bg).
    Each connected component of content drops as a rigid body.
    Components stack on each other without a gap."""
    h = len(grid)
    w = len(grid[0]) if grid else 0
    if h == 0:
        return [row[:] for row in grid]

    # Auto-detect wall color from bottom row
    bottom_colors = set(grid[h - 1][c] for c in range(w)) - {bg}
    if len(bottom_colors) != 1:
        return [row[:] for row in grid]
    wall_color = bottom_colors.pop()

    # Content = all non-bg, non-wall cells
    content_cells = set()
    for r in range(h):
        for c in range(w):
            if grid[r][c] != bg and grid[r][c] != wall_color:
                content_cells.add((r, c))
    if not content_cells:
        return [row[:] for row in grid]

    # Find connected components (4-connectivity) among content cells
    visited = set()
    components = []
    for r, c in sorted(content_cells):
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
                if (nr, nc) in content_cells and (nr, nc) not in visited:
                    visited.add((nr, nc))
                    queue.append((nr, nc))
        components.append(comp)

    # Sort by max row descending (process bottom components first)
    components.sort(key=lambda comp: -max(r for r, c in comp))

    # Clear content from output
    output = [row[:] for row in grid]
    for r, c in content_cells:
        output[r][c] = bg

    # Drop each component
    for comp in components:
        cols = set(c for _, c in comp)
        min_drop = float('inf')

        for col in cols:
            bottom = max(r for r, c in comp if c == col)

            # Find floor: first non-bg row below bottom in current output
            floor_row = h
            for r in range(bottom + 1, h):
                if output[r][col] != bg:
                    floor_row = r
                    break

            # Wall or grid-bottom: 1-row gap. Placed content: no gap.
            if floor_row >= h or grid[floor_row][col] == wall_color:
                effective = floor_row - 2
            else:
                effective = floor_row - 1

            col_drop = effective - bottom
            if col_drop < min_drop:
                min_drop = col_drop

        if min_drop < 0 or min_drop == float('inf'):
            min_drop = 0

        for r, c in comp:
            new_r = r + min_drop
            if 0 <= new_r < h:
                output[new_r][c] = grid[r][c]  # preserve original color

    return output


def fill_rects_by_size(grid, border_color, bg=0, start_color=6):
    """Find rectangles bordered by border_color, fill interiors by size.
    Fill color = start_color + (interior_width - 1), giving a fixed mapping."""
    h = len(grid)
    w = len(grid[0]) if grid else 0
    # Find rectangular outlines of border_color
    comps = find_components(grid, border_color)
    rects = []
    for comp in comps:
        min_r = min(r for r, c in comp)
        max_r = max(r for r, c in comp)
        min_c = min(c for r, c in comp)
        max_c = max(c for r, c in comp)
        rect_h = max_r - min_r + 1
        rect_w = max_c - min_c + 1
        if rect_h < 3 or rect_w < 3:
            continue
        # Check it's actually a rectangle border
        comp_set = set(comp)
        is_rect = True
        for r in range(min_r, max_r + 1):
            for c in range(min_c, max_c + 1):
                on_border = (r == min_r or r == max_r or c == min_c or c == max_c)
                if on_border and (r, c) not in comp_set:
                    is_rect = False
                    break
            if not is_rect:
                break
        if not is_rect:
            continue
        interior_h = rect_h - 2
        interior_w = rect_w - 2
        rects.append((min_r, min_c, max_r, max_c, interior_h, interior_w))
    if not rects:
        return [row[:] for row in grid]
    output = [row[:] for row in grid]
    for min_r, min_c, max_r, max_c, interior_h, interior_w in rects:
        fill_color = start_color + min(interior_h, interior_w) - 1
        for r in range(min_r + 1, max_r):
            for c in range(min_c + 1, max_c):
                output[r][c] = fill_color
    return output


def fill_between_separators(grid, bg=7):
    """Fill rows with nearest horizontal separator color.
    Finds a vertical column (constant non-bg color with intersection markers)
    and horizontal separator rows. Each non-separator row is colored by its
    nearest separator. Equidistant rows between different-colored separators
    become all intersection-color. Separator rows become all intersection-color
    with the column color at the intersection."""
    h = len(grid)
    w = len(grid[0]) if grid else 0
    if h == 0 or w == 0:
        return [row[:] for row in grid]

    # Find the vertical column with exactly 2 non-bg colors (most non-bg cells wins)
    col_idx = None
    col_color = None
    inter_color = None
    best_count = 0
    for c in range(w):
        colors = {}
        for r in range(h):
            v = grid[r][c]
            if v != bg:
                colors[v] = colors.get(v, 0) + 1
        if len(colors) == 2:
            total = sum(colors.values())
            if total > best_count:
                sorted_colors = sorted(colors.items(), key=lambda x: -x[1])
                col_idx = c
                col_color = sorted_colors[0][0]
                inter_color = sorted_colors[1][0]
                best_count = total

    if col_idx is None:
        return [row[:] for row in grid]

    # Find separator rows (where column cell = inter_color)
    separators = []
    for r in range(h):
        if grid[r][col_idx] == inter_color:
            sep_color = None
            for c in range(w):
                if c != col_idx and grid[r][c] != bg:
                    sep_color = grid[r][c]
                    break
            if sep_color is not None:
                separators.append((r, sep_color))

    if not separators:
        return [row[:] for row in grid]

    # Build output
    output = [[0] * w for _ in range(h)]
    for r in range(h):
        # Check if separator row
        is_sep = False
        for sr, sc in separators:
            if sr == r:
                is_sep = True
                for c in range(w):
                    output[r][c] = inter_color
                output[r][col_idx] = col_color
                break

        if not is_sep:
            # Find nearest separator above and below
            dist_above, color_above = h + 1, None
            dist_below, color_below = h + 1, None
            for sr, sc in separators:
                d = abs(r - sr)
                if sr < r and d < dist_above:
                    dist_above, color_above = d, sc
                elif sr > r and d < dist_below:
                    dist_below, color_below = d, sc

            if color_above is None:
                fill = color_below
            elif color_below is None:
                fill = color_above
            elif dist_above < dist_below:
                fill = color_above
            elif dist_below < dist_above:
                fill = color_below
            elif color_above == color_below:
                fill = color_above
            else:
                fill = inter_color  # equidistant, different colors

            for c in range(w):
                output[r][c] = fill
            output[r][col_idx] = inter_color

    return output


def mirror_displacement_across_separator(grid, bg=7):
    """Move colored pixels by following displacement chains, mirroring across separator.
    Finds a full-width separator row. Below it: 'data' color pixels with 'arrow'
    color chains indicating displacement. Above: 'mirror' color pixels at symmetric
    positions. Each data pixel follows its arrow chain; mirror pixels get the
    reflected displacement (vertical flipped, horizontal same)."""
    h = len(grid)
    w = len(grid[0]) if grid else 0
    if h == 0 or w == 0:
        return [row[:] for row in grid]

    # Find separator row (full-width row of single non-bg color)
    sep_row = None
    sep_color = None
    for r in range(h):
        vals = set(grid[r])
        if len(vals) == 1 and vals.pop() != bg:
            sep_row = r
            sep_color = grid[r][0]
            break
    if sep_row is None:
        return [row[:] for row in grid]

    # Identify colors: above separator has mirror_color, below has data_color and arrow_color
    above_colors = set()
    below_colors = set()
    for r in range(h):
        for c in range(w):
            v = grid[r][c]
            if v != bg and v != sep_color:
                if r < sep_row:
                    above_colors.add(v)
                elif r > sep_row:
                    below_colors.add(v)

    if len(above_colors) != 1 or len(below_colors) != 2:
        return [row[:] for row in grid]

    mirror_color = above_colors.pop()
    # Data color appears in both halves conceptually; arrow color only below
    # Data color has symmetric mirrors above; arrow color does not
    below_list = sorted(below_colors)
    data_color = None
    arrow_color = None

    # Try each candidate: data_color pixels should have mirrors above
    for cand_data in below_list:
        cand_arrow = [c for c in below_list if c != cand_data][0]
        # Check if data pixels have mirror positions above
        data_positions = [(r, c) for r in range(sep_row + 1, h)
                          for c in range(w) if grid[r][c] == cand_data]
        mirror_positions = [(r, c) for r in range(sep_row)
                            for c in range(w) if grid[r][c] == mirror_color]
        # Each data pixel should have a mirror at symmetric row, same col
        matched = 0
        for dr, dc in data_positions:
            sym_r = 2 * sep_row - dr
            if 0 <= sym_r < h and (sym_r, dc) in [(mr, mc) for mr, mc in mirror_positions]:
                matched += 1
        if matched == len(data_positions) and matched == len(mirror_positions):
            data_color = cand_data
            arrow_color = cand_arrow
            break

    if data_color is None or arrow_color is None:
        return [row[:] for row in grid]

    # Build output: start with bg everywhere, keep separator
    output = [[bg] * w for _ in range(h)]
    for c in range(w):
        output[sep_row][c] = sep_color

    # Find data pixels and their arrow chains
    data_pixels = [(r, c) for r in range(sep_row + 1, h)
                   for c in range(w) if grid[r][c] == data_color]
    arrow_set = set((r, c) for r in range(sep_row + 1, h)
                    for c in range(w) if grid[r][c] == arrow_color)

    dirs = [(-1, 0), (1, 0), (0, -1), (0, 1)]

    for dr, dc in data_pixels:
        # Follow arrow chain from data pixel
        total_dr, total_dc = 0, 0
        cr, cc = dr, dc
        visited = {(cr, cc)}
        while True:
            moved = False
            for ddr, ddc in dirs:
                nr, nc = cr + ddr, cc + ddc
                if (nr, nc) in arrow_set and (nr, nc) not in visited:
                    total_dr += ddr
                    total_dc += ddc
                    cr, cc = nr, nc
                    visited.add((nr, nc))
                    moved = True
                    break
            if not moved:
                break

        # Place data pixel at new position
        new_r, new_c = dr + total_dr, dc + total_dc
        if 0 <= new_r < h and 0 <= new_c < w:
            output[new_r][new_c] = data_color

        # Mirror pixel: symmetric position above separator
        mirror_r = 2 * sep_row - dr
        mirror_c = dc
        # Reflected displacement: vertical flipped, horizontal same
        new_mirror_r = mirror_r - total_dr
        new_mirror_c = mirror_c + total_dc
        if 0 <= new_mirror_r < h and 0 <= new_mirror_c < w:
            output[new_mirror_r][new_mirror_c] = mirror_color

    return output


def connect_aligned_diamonds(grid, diamond_color, line_color, bg=0):
    """Find diamond/cross shapes of diamond_color and connect aligned ones with lines.
    Each diamond is a 4-cell cross: top, left, right, bottom around a bg center.
    Diamonds sharing the same center row get horizontal lines between their tips.
    Diamonds sharing the same center column get vertical lines between their tips."""
    h = len(grid)
    w = len(grid[0]) if grid else 0
    output = [row[:] for row in grid]

    # Find diamond centers: bg cell with diamond_color in all 4 cardinal directions
    centers = []
    for r in range(1, h - 1):
        for c in range(1, w - 1):
            if grid[r][c] == bg:
                if (grid[r-1][c] == diamond_color and grid[r+1][c] == diamond_color and
                    grid[r][c-1] == diamond_color and grid[r][c+1] == diamond_color):
                    centers.append((r, c))

    # Connect horizontally aligned (same row) diamonds
    row_groups = {}
    for r, c in centers:
        row_groups.setdefault(r, []).append(c)
    for r, cols in row_groups.items():
        cols.sort()
        for i in range(len(cols) - 1):
            c1 = cols[i] + 2  # right tip + 1
            c2 = cols[i+1] - 1  # left tip
            for c in range(c1, c2):
                if output[r][c] == bg:
                    output[r][c] = line_color

    # Connect vertically aligned (same column) diamonds
    col_groups = {}
    for r, c in centers:
        col_groups.setdefault(c, []).append(r)
    for c, rows in col_groups.items():
        rows.sort()
        for i in range(len(rows) - 1):
            r1 = rows[i] + 2  # bottom tip + 1
            r2 = rows[i+1] - 1  # top tip
            for r in range(r1, r2):
                if output[r][c] == bg:
                    output[r][c] = line_color

    return output


def summarize_box_grid(grid, bg=0):
    """Summarize a 30x30 grid of 3x3 bordered boxes into a compact bar-chart.
    The grid has a 1-border on one edge, a 7x7 grid of box cells (3x3 each,
    spaced 4 apart), with box-row/col 3 as separator between colored and 8 halves.
    Output: bar-chart where each slice counts colored and 8 boxes."""
    h = len(grid)
    w = len(grid[0]) if grid else 0

    # Find 1-border edge
    border = None  # 'top', 'bottom', 'left', 'right'
    for r in range(h):
        if all(grid[r][c] == 1 for c in range(w)):
            border = 'top' if r < h // 2 else 'bottom'
            break
    if border is None:
        for c in range(w):
            if all(grid[r][c] == 1 for r in range(h)):
                border = 'left' if c < w // 2 else 'right'
                break
    if border is None:
        return None

    # Determine grid origin (skip the 1-border row/col)
    # Box at (bi, bj) has its top-left corner at origin + (bi*4, bj*4)
    # The 3x3 box spans 3 rows and 3 cols
    if border == 'top':
        row_origin = 2  # skip border row + separator row
        col_origin = 1
    elif border == 'bottom':
        row_origin = 1
        col_origin = 1
    elif border == 'left':
        row_origin = 1
        col_origin = 2
    else:  # right
        row_origin = 1
        col_origin = 1

    # Read 7x7 box grid
    box_colors = [[0] * 7 for _ in range(7)]
    for bi in range(7):
        for bj in range(7):
            r0 = row_origin + bi * 4
            c0 = col_origin + bj * 4
            # Check if box is present (non-bg, non-0 in the border cells)
            color = 0
            for dr in range(3):
                for dc in range(3):
                    r, c = r0 + dr, c0 + dc
                    if 0 <= r < h and 0 <= c < w:
                        v = grid[r][c]
                        if v != bg and v != 0 and v != 1:
                            color = v
            box_colors[bi][bj] = color

    # Determine separator axis and stacking direction
    if border in ('top', 'bottom'):
        # Vertical separator at col 3, horizontal stacking
        # Left half: cols 0-2, Right half: cols 4-6
        # Count per row, output is 7 rows x 6 cols
        left_colors = [[box_colors[bi][bj] for bj in range(3)] for bi in range(7)]
        right_colors = [[box_colors[bi][bj] for bj in range(4, 7)] for bi in range(7)]

        # Determine which side is 8
        left_8 = sum(1 for bi in range(7) for bj in range(3) if box_colors[bi][bj] == 8)
        right_8 = sum(1 for bi in range(7) for bj in range(4, 7) if box_colors[bi][bj] == 8)
        eight_on_right = right_8 > left_8

        output = [[0] * 6 for _ in range(7)]
        for bi in range(7):
            if eight_on_right:
                colored_cells = left_colors[bi]
                eight_cells = right_colors[bi]
            else:
                colored_cells = right_colors[bi]
                eight_cells = left_colors[bi]

            n_color = sum(1 for v in colored_cells if v != 0)
            n_eight = sum(1 for v in eight_cells if v == 8)
            # Find the non-8 color for this row
            row_color = 0
            for v in colored_cells:
                if v != 0 and v != 8:
                    row_color = v
                    break

            if eight_on_right:
                # 8 fills from right, color fills leftward
                for k in range(n_eight):
                    output[bi][5 - k] = 8
                for k in range(n_color):
                    output[bi][5 - n_eight - k] = row_color
            else:
                # 8 fills from left, color fills rightward
                for k in range(n_eight):
                    output[bi][k] = 8
                for k in range(n_color):
                    output[bi][n_eight + k] = row_color

        return output

    else:
        # Horizontal separator at row 3, vertical stacking
        # Top half: rows 0-2, Bottom half: rows 4-6
        # Count per column, output is 6 rows x 7 cols
        top_colors = [[box_colors[bi][bj] for bj in range(7)] for bi in range(3)]
        bottom_colors = [[box_colors[bi][bj] for bj in range(7)] for bi in range(4, 7)]

        # Determine which side is 8
        top_8 = sum(1 for bi in range(3) for bj in range(7) if box_colors[bi][bj] == 8)
        bottom_8 = sum(1 for bi in range(4, 7) for bj in range(7) if box_colors[bi][bj] == 8)
        eight_on_bottom = bottom_8 > top_8

        output = [[0] * 7 for _ in range(6)]
        for bj in range(7):
            if eight_on_bottom:
                colored_cells = [top_colors[bi][bj] for bi in range(3)]
                eight_cells = [bottom_colors[bi][bj] for bi in range(3)]
            else:
                colored_cells = [bottom_colors[bi][bj] for bi in range(3)]
                eight_cells = [top_colors[bi][bj] for bi in range(3)]

            n_color = sum(1 for v in colored_cells if v != 0)
            n_eight = sum(1 for v in eight_cells if v == 8)
            col_color = 0
            for v in colored_cells:
                if v != 0 and v != 8:
                    col_color = v
                    break

            if eight_on_bottom:
                # 8 fills from bottom, color fills upward
                for k in range(n_eight):
                    output[5 - k][bj] = 8
                for k in range(n_color):
                    output[5 - n_eight - k][bj] = col_color
            else:
                # 8 fills from top, color fills downward
                for k in range(n_eight):
                    output[k][bj] = 8
                for k in range(n_color):
                    output[n_eight + k][bj] = col_color

        return output
