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


def project_cross_to_border(grid):
    """Find asymmetric cross shapes with unique center pixel.
    Each cross has an arm pointing in one direction; the center color
    projects to the OPPOSITE border with a dotted trail (every 2 cells).
    Corners where two borders meet become 0. Auto-detects bg."""
    h = len(grid)
    w = len(grid[0]) if grid else 0
    bg = find_bg_color(grid)
    output = [row[:] for row in grid]

    # Find connected components of non-bg cells
    visited = set()
    crosses = []

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

            # Check for exactly 2 colors, one appearing once (center)
            colors = {}
            for cr, cc in comp:
                v = grid[cr][cc]
                colors[v] = colors.get(v, 0) + 1
            if len(colors) != 2:
                continue
            sorted_colors = sorted(colors.items(), key=lambda x: x[1])
            if sorted_colors[0][1] != 1:
                continue

            center_color = sorted_colors[0][0]
            center_pos = None
            for cr, cc in comp:
                if grid[cr][cc] == center_color:
                    center_pos = (cr, cc)
                    break

            # Compute asymmetry: sum of relative positions of shape cells
            sum_dr, sum_dc = 0, 0
            for cr, cc in comp:
                if grid[cr][cc] != center_color:
                    sum_dr += (cr - center_pos[0])
                    sum_dc += (cc - center_pos[1])

            # Arm direction = direction of sum; project = opposite
            if abs(sum_dr) >= abs(sum_dc):
                proj_dir = 'up' if sum_dr > 0 else 'down'
            else:
                proj_dir = 'left' if sum_dc > 0 else 'right'

            crosses.append((center_pos[0], center_pos[1], center_color, proj_dir))

    if not crosses:
        return output

    # Draw dotted trails and fill borders
    borders = {}  # side -> color

    for cr, cc, center_color, proj_dir in crosses:
        if proj_dir == 'up':
            borders['top'] = center_color
            r = cr - 2
            while r >= 0:
                output[r][cc] = center_color
                r -= 2
        elif proj_dir == 'down':
            borders['bottom'] = center_color
            r = cr + 2
            while r < h:
                output[r][cc] = center_color
                r += 2
        elif proj_dir == 'left':
            borders['left'] = center_color
            c = cc - 2
            while c >= 0:
                output[cr][c] = center_color
                c -= 2
        elif proj_dir == 'right':
            borders['right'] = center_color
            c = cc + 2
            while c < w:
                output[cr][c] = center_color
                c += 2

    # Fill border rows/cols
    for side, color in borders.items():
        if side == 'top':
            for c in range(w):
                output[0][c] = color
        elif side == 'bottom':
            for c in range(w):
                output[h - 1][c] = color
        elif side == 'left':
            for r in range(h):
                output[r][0] = color
        elif side == 'right':
            for r in range(h):
                output[r][w - 1] = color

    # Zero corners where two borders meet
    if 'top' in borders and 'left' in borders:
        output[0][0] = 0
    if 'top' in borders and 'right' in borders:
        output[0][w - 1] = 0
    if 'bottom' in borders and 'left' in borders:
        output[h - 1][0] = 0
    if 'bottom' in borders and 'right' in borders:
        output[h - 1][w - 1] = 0

    return output


def swap_quadrant_shapes(grid, sep_color=0):
    """Grid divided into quadrant pairs by separator rows/cols of sep_color.
    For each horizontal pair, swap shapes: each shape is recolored with the
    partner quadrant's background color. When both bgs match, shapes vanish."""
    h = len(grid)
    w = len(grid[0]) if grid else 0

    # Find separator rows (full-width rows of sep_color)
    sep_rows = []
    for r in range(h):
        if all(grid[r][c] == sep_color for c in range(w)):
            sep_rows.append(r)

    # Find separator cols (full-height cols of sep_color)
    sep_cols = []
    for c in range(w):
        if all(grid[r][c] == sep_color for r in range(h)):
            sep_cols.append(c)

    if not sep_cols:
        return [row[:] for row in grid]

    # Group consecutive separator rows/cols into bands
    def _group_consecutive(indices):
        if not indices:
            return []
        bands = []
        start = indices[0]
        end = indices[0]
        for i in indices[1:]:
            if i == end + 1:
                end = i
            else:
                bands.append((start, end))
                start = end = i
        bands.append((start, end))
        return bands

    row_bands = _group_consecutive(sep_rows)
    col_bands = _group_consecutive(sep_cols)

    # Determine row regions (between separator bands)
    row_regions = []
    prev = 0
    for band_start, band_end in row_bands:
        if band_start > prev:
            row_regions.append((prev, band_start - 1))
        prev = band_end + 1
    if prev < h:
        row_regions.append((prev, h - 1))

    # Determine col regions (between separator bands)
    col_regions = []
    prev = 0
    for band_start, band_end in col_bands:
        if band_start > prev:
            col_regions.append((prev, band_start - 1))
        prev = band_end + 1
    if prev < w:
        col_regions.append((prev, w - 1))

    if len(col_regions) != 2:
        return [row[:] for row in grid]

    output = [row[:] for row in grid]

    # Process each row of quadrants — horizontal pairs
    for r_start, r_end in row_regions:
        left_c0, left_c1 = col_regions[0]
        right_c0, right_c1 = col_regions[1]

        # Detect bg for each quadrant (most frequent color in the quadrant)
        def _quad_bg(rs, re, cs, ce):
            counts = {}
            for r in range(rs, re + 1):
                for c in range(cs, ce + 1):
                    v = grid[r][c]
                    counts[v] = counts.get(v, 0) + 1
            return max(counts, key=counts.get) if counts else 0

        left_bg = _quad_bg(r_start, r_end, left_c0, left_c1)
        right_bg = _quad_bg(r_start, r_end, right_c0, right_c1)

        # Extract shape positions (non-bg cells) relative to quadrant
        def _shape_rel(rs, re, cs, ce, bg):
            positions = []
            for r in range(rs, re + 1):
                for c in range(cs, ce + 1):
                    if grid[r][c] != bg:
                        positions.append((r - rs, c - cs))
            return positions

        left_shape = _shape_rel(r_start, r_end, left_c0, left_c1, left_bg)
        right_shape = _shape_rel(r_start, r_end, right_c0, right_c1, right_bg)

        # Clear both quadrants to their bg
        for r in range(r_start, r_end + 1):
            for c in range(left_c0, left_c1 + 1):
                output[r][c] = left_bg
            for c in range(right_c0, right_c1 + 1):
                output[r][c] = right_bg

        # Place right's shape into left, colored with right's bg
        for dr, dc in right_shape:
            r, c = r_start + dr, left_c0 + dc
            if r_start <= r <= r_end and left_c0 <= c <= left_c1:
                output[r][c] = right_bg

        # Place left's shape into right, colored with left's bg
        for dr, dc in left_shape:
            r, c = r_start + dr, right_c0 + dc
            if r_start <= r <= r_end and right_c0 <= c <= right_c1:
                output[r][c] = left_bg

    return output


def zigzag_shear_grid(grid, bg=0):
    """Find a colored rectangle/grid pattern on background and apply zigzag shear.
    Each row of the rectangle shifts horizontally by [0, -1, 0, +1] based on
    distance from the bottom row of the rectangle (mod 4).
    Works for grids with internal dividers (sub-cells) — the entire row shifts."""
    h = len(grid)
    w = len(grid[0]) if grid else 0
    if h == 0 or w == 0:
        return [row[:] for row in grid]

    # Find bounding box of all non-bg cells
    non_bg = []
    for r in range(h):
        for c in range(w):
            if grid[r][c] != bg:
                non_bg.append((r, c))
    if not non_bg:
        return [row[:] for row in grid]

    min_r = min(r for r, c in non_bg)
    max_r = max(r for r, c in non_bg)

    # Shift pattern indexed by distance from bottom: [0, -1, 0, +1] repeating
    shift_pattern = [0, -1, 0, 1]

    output = [[bg] * w for _ in range(h)]
    for r in range(h):
        if r < min_r or r > max_r:
            # Outside the rectangle — keep as bg
            continue
        dist_from_bottom = max_r - r
        shift = shift_pattern[dist_from_bottom % 4]
        for c in range(w):
            if grid[r][c] != bg:
                nc = c + shift
                if 0 <= nc < w:
                    output[r][nc] = grid[r][c]
    return output


def slide_connector_through(grid, bg=7):
    """Three single-color shapes in a line. The smallest (connector) slides through
    one neighbor, splitting it ±1 perpendicular. Direction: toward farther neighbor;
    if equidistant, toward larger perpendicular extent. Connector exits past target
    (clamped to grid boundary)."""
    h = len(grid)
    w = len(grid[0]) if grid else 0
    if h == 0 or w == 0:
        return [row[:] for row in grid]

    # Per-color connected components
    visited = set()
    comps = []
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
            min_r = min(r for r, _ in comp)
            max_r = max(r for r, _ in comp)
            min_c = min(c for _, c in comp)
            max_c = max(c for _, c in comp)
            comps.append({
                "positions": comp, "bbox": (min_r, min_c, max_r, max_c),
                "size": len(comp), "height": max_r - min_r + 1, "width": max_c - min_c + 1,
            })

    if len(comps) != 3:
        return [row[:] for row in grid]

    # Identify the connector as the geometrically middle shape.
    # Compute centers, find which is between the other two.
    shape_centers = []
    for s in comps:
        cr = (s["bbox"][0] + s["bbox"][2]) / 2.0
        cc = (s["bbox"][1] + s["bbox"][3]) / 2.0
        shape_centers.append((cr, cc))

    # Try each as connector: it's the one whose center is between the other two
    conn_idx = None
    for i in range(3):
        j, k = [x for x in range(3) if x != i]
        cr_i, cc_i = shape_centers[i]
        cr_j, cc_j = shape_centers[j]
        cr_k, cc_k = shape_centers[k]
        # Check if i is between j and k in rows OR cols
        between_r = min(cr_j, cr_k) <= cr_i <= max(cr_j, cr_k)
        between_c = min(cc_j, cc_k) <= cc_i <= max(cc_j, cc_k)
        if between_r and between_c:
            # Among ties, prefer the smallest shape
            if conn_idx is None or comps[i]["size"] < comps[conn_idx]["size"]:
                conn_idx = i
    if conn_idx is None:
        # Fallback: smallest shape
        conn_idx = min(range(3), key=lambda i: comps[i]["size"])

    conn = comps[conn_idx]
    nbs = [comps[i] for i in range(3) if i != conn_idx]

    conn_cr = (conn["bbox"][0] + conn["bbox"][2]) / 2.0
    conn_cc = (conn["bbox"][1] + conn["bbox"][3]) / 2.0
    nb_centers = [((n["bbox"][0] + n["bbox"][2]) / 2.0, (n["bbox"][1] + n["bbox"][3]) / 2.0) for n in nbs]

    vert_spread = max(abs(nb_centers[0][0] - conn_cr), abs(nb_centers[1][0] - conn_cr))
    horiz_spread = max(abs(nb_centers[0][1] - conn_cc), abs(nb_centers[1][1] - conn_cc))
    vertical = vert_spread >= horiz_spread

    c0r, c0c, c1r, c1c = conn["bbox"]
    ch, cw = conn["height"], conn["width"]

    if vertical:
        # Order: before (above) / after (below)
        if nb_centers[0][0] < nb_centers[1][0]:
            nb_bef, nb_aft = nbs[0], nbs[1]
        else:
            nb_bef, nb_aft = nbs[1], nbs[0]

        gap_bef = c0r - nb_bef["bbox"][2] - 1
        gap_aft = nb_aft["bbox"][0] - c1r - 1

        if gap_bef > gap_aft:
            target, fixed = nb_bef, nb_aft
        elif gap_aft > gap_bef:
            target, fixed = nb_aft, nb_bef
        else:
            if nb_bef["width"] >= nb_aft["width"]:
                target, fixed = nb_bef, nb_aft
            else:
                target, fixed = nb_aft, nb_bef

        toward_min = (target is nb_bef)
        t0r, t0c, t1r, t1c = target["bbox"]
        mid_c = (c0c + c1c) / 2.0

        left_half = [(r, c) for r, c in target["positions"] if c < mid_c]
        right_half = [(r, c) for r, c in target["positions"] if c >= mid_c]

        output = [[bg] * w for _ in range(h)]
        for r, c in fixed["positions"]:
            output[r][c] = grid[r][c]
        for r, c in left_half:
            nc = c - 1
            if 0 <= nc < w:
                output[r][nc] = grid[r][c]
        for r, c in right_half:
            nc = c + 1
            if 0 <= nc < w:
                output[r][nc] = grid[r][c]

        if toward_min:
            new_top = t0r - ch
            if new_top < 0:
                new_top = 0
            shift_r = new_top - c0r
        else:
            new_bottom = t1r + ch
            if new_bottom >= h:
                new_bottom = h - 1
            shift_r = (new_bottom - ch + 1) - c0r

        for r, c in conn["positions"]:
            nr = r + shift_r
            if 0 <= nr < h:
                output[nr][c] = grid[r][c]
    else:
        if nb_centers[0][1] < nb_centers[1][1]:
            nb_bef, nb_aft = nbs[0], nbs[1]
        else:
            nb_bef, nb_aft = nbs[1], nbs[0]

        gap_bef = c0c - nb_bef["bbox"][3] - 1
        gap_aft = nb_aft["bbox"][1] - c1c - 1

        if gap_bef > gap_aft:
            target, fixed = nb_bef, nb_aft
        elif gap_aft > gap_bef:
            target, fixed = nb_aft, nb_bef
        else:
            if nb_bef["height"] >= nb_aft["height"]:
                target, fixed = nb_bef, nb_aft
            else:
                target, fixed = nb_aft, nb_bef

        toward_min = (target is nb_bef)
        t0r, t0c, t1r, t1c = target["bbox"]
        mid_r = (c0r + c1r) / 2.0

        top_half = [(r, c) for r, c in target["positions"] if r < mid_r]
        bottom_half = [(r, c) for r, c in target["positions"] if r >= mid_r]

        output = [[bg] * w for _ in range(h)]
        for r, c in fixed["positions"]:
            output[r][c] = grid[r][c]
        for r, c in top_half:
            nr = r - 1
            if 0 <= nr < h:
                output[nr][c] = grid[r][c]
        for r, c in bottom_half:
            nr = r + 1
            if 0 <= nr < h:
                output[nr][c] = grid[r][c]

        if toward_min:
            new_left = t0c - cw
            if new_left < 0:
                new_left = 0
            shift_c = new_left - c0c
        else:
            new_right = t1c + cw
            if new_right >= w:
                new_right = w - 1
            shift_c = (new_right - cw + 1) - c0c

        for r, c in conn["positions"]:
            nc = c + shift_c
            if 0 <= nc < w:
                output[r][nc] = grid[r][c]

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


def relocate_cross_template(grid, bg=0):
    """Find cross-shaped templates (connector + markers), find isolated marker dots,
    match templates to anchor groups via rotation/reflection, and redraw connectors
    at anchor positions. Erases templates and draws transformed connectors around anchors.

    A template is a connected cluster containing a 'connector' color (most frequent non-bg).
    Anchor markers are isolated non-connector pixels not part of any template."""
    h = len(grid)
    w = len(grid[0]) if grid else 0

    # Find all non-bg cells by color
    color_counts = {}
    for r in range(h):
        for c in range(w):
            if grid[r][c] != bg:
                color_counts[grid[r][c]] = color_counts.get(grid[r][c], 0) + 1

    if not color_counts:
        return [row[:] for row in grid]

    # Connector = most frequent non-bg color
    connector_color = max(color_counts, key=color_counts.get)

    # Find connected components (4-connectivity) of all non-bg cells
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
                comp.append((cr, cc))
                for dr, dc in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                    nr, nc = cr + dr, cc + dc
                    if 0 <= nr < h and 0 <= nc < w and (nr, nc) not in visited and grid[nr][nc] != bg:
                        visited.add((nr, nc))
                        queue.append((nr, nc))
            components.append(comp)

    # Classify: templates (connected clusters with connector) vs isolated marker pixels
    templates = []
    # isolated_markers: {color: [(r,c), ...]}
    isolated_markers = {}
    for comp in components:
        has_connector = any(grid[r][c] == connector_color for r, c in comp)
        if has_connector:
            marker_cells = {grid[r][c]: (r, c) for r, c in comp if grid[r][c] != connector_color}
            connector_cells = [(r, c) for r, c in comp if grid[r][c] == connector_color]
            templates.append({"markers": marker_cells, "connectors": connector_cells})
        else:
            # Each isolated pixel is a marker
            for r, c in comp:
                color = grid[r][c]
                isolated_markers.setdefault(color, []).append((r, c))

    if not templates or not isolated_markers:
        return [row[:] for row in grid]

    # 8 transformations: (dr, dc) -> transformed
    # Use closures with default args to avoid late-binding issues
    transforms = [
        lambda dr, dc, _=None: (dr, dc),
        lambda dr, dc, _=None: (dc, -dr),
        lambda dr, dc, _=None: (-dr, -dc),
        lambda dr, dc, _=None: (-dc, dr),
        lambda dr, dc, _=None: (dr, -dc),
        lambda dr, dc, _=None: (-dr, dc),
        lambda dr, dc, _=None: (dc, dr),
        lambda dr, dc, _=None: (-dc, -dr),
    ]

    # Build output: bg everywhere
    output = [[bg] * w for _ in range(h)]

    # For each template, find matching anchor group from isolated markers
    used_anchors = {}  # color -> set of used positions
    for tmpl in templates:
        marker_colors = sorted(tmpl["markers"].keys())
        # Check all marker colors have available anchor positions
        available = {}
        for mc in marker_colors:
            positions = [p for p in isolated_markers.get(mc, [])
                         if p not in used_anchors.get(mc, set())]
            if not positions:
                break
            available[mc] = positions
        if len(available) != len(marker_colors):
            continue

        ref_color = marker_colors[0]
        t_ref = tmpl["markers"][ref_color]

        # Try each candidate anchor position for the reference color
        found = False
        for a_ref_pos in available[ref_color]:
            for transform in transforms:
                # Check if this transform maps all template markers to valid anchor positions
                anchor_assignment = {ref_color: a_ref_pos}
                match = True
                for mc in marker_colors:
                    if mc == ref_color:
                        continue
                    t_pos = tmpl["markers"][mc]
                    dr, dc = t_pos[0] - t_ref[0], t_pos[1] - t_ref[1]
                    tr, tc = transform(dr, dc)
                    expected = (a_ref_pos[0] + tr, a_ref_pos[1] + tc)
                    if expected in available.get(mc, []):
                        anchor_assignment[mc] = expected
                    else:
                        match = False
                        break
                if match:
                    # Place anchor markers and transformed connectors
                    for mc, pos in anchor_assignment.items():
                        output[pos[0]][pos[1]] = mc
                        used_anchors.setdefault(mc, set()).add(pos)
                    for cr, cc in tmpl["connectors"]:
                        dr, dc = cr - t_ref[0], cc - t_ref[1]
                        tr, tc = transform(dr, dc)
                        nr, nc = a_ref_pos[0] + tr, a_ref_pos[1] + tc
                        if 0 <= nr < h and 0 <= nc < w:
                            output[nr][nc] = connector_color
                    found = True
                    break
            if found:
                break

    return output


def scatter_count_x_diamond(grid, bg=7, fill_color=2, diag_color=4, output_side=16):
    """Count scattered pixels of each non-bg color. Use counts as rectangle dimensions.
    Draw an X/hourglass pattern of diag_color on fill_color background in the
    bottom-left corner of an output_side x output_side grid.
    W = larger count, H = smaller count.
    At each row r (0..H-1): diag at cols min(r+W-H, H-1-r) and max(r+W-H, H-1-r)."""
    # Count non-bg pixels by color
    color_counts = {}
    for row in grid:
        for v in row:
            if v != bg:
                color_counts[v] = color_counts.get(v, 0) + 1

    if len(color_counts) != 2:
        return None

    counts = sorted(color_counts.values())
    rect_h = counts[0]  # smaller count
    rect_w = counts[1]  # larger count

    if rect_h > output_side or rect_w > output_side:
        return None

    # Build output: all bg, output_side x output_side
    output = [[bg] * output_side for _ in range(output_side)]

    # Fill rectangle in bottom-left
    offset = rect_w - rect_h
    start_row = output_side - rect_h
    for r in range(rect_h):
        left = min(r + offset, rect_h - 1 - r)
        right = max(r + offset, rect_h - 1 - r)
        for c in range(rect_w):
            output[start_row + r][c] = fill_color
        output[start_row + r][left] = diag_color
        if right != left:
            output[start_row + r][right] = diag_color

    return output


def invert_bordered_rect(grid, bg=0):
    """Find a bordered rectangle (frame of color A, interior of color B) on bg grid.
    Return the rectangle cropped out with border and fill colors swapped.
    Frame becomes B, interior becomes A."""
    h = len(grid)
    w = len(grid[0]) if grid else 0

    # Find all non-bg cells to locate the rectangle
    non_bg = set()
    for r in range(h):
        for c in range(w):
            if grid[r][c] != bg:
                non_bg.add((r, c))
    if not non_bg:
        return None

    min_r = min(p[0] for p in non_bg)
    max_r = max(p[0] for p in non_bg)
    min_c = min(p[1] for p in non_bg)
    max_c = max(p[1] for p in non_bg)

    rect_h = max_r - min_r + 1
    rect_w = max_c - min_c + 1

    # Extract the rectangle region
    rect = [grid[min_r + r][min_c:min_c + rect_w] for r in range(rect_h)]

    # Identify border color (top-left corner) and fill color (center)
    border_color = rect[0][0]
    # Find the interior color: first non-border color in interior cells
    fill_color = None
    for r in range(1, rect_h - 1):
        for c in range(1, rect_w - 1):
            if rect[r][c] != border_color:
                fill_color = rect[r][c]
                break
        if fill_color is not None:
            break

    if fill_color is None:
        return None

    # Build output with swapped colors
    output = []
    for r in range(rect_h):
        row = []
        for c in range(rect_w):
            if rect[r][c] == border_color:
                row.append(fill_color)
            elif rect[r][c] == fill_color:
                row.append(border_color)
            else:
                row.append(rect[r][c])
        output.append(row)

    return output


def tile_content_upward(grid, bg=None):
    """Find content region at bottom of grid, tile it upward to fill the entire grid.
    Content is detected as the bottom rows containing non-bg pixels.
    Tiling is bottom-aligned: the original content stays in place."""
    h = len(grid)
    w = len(grid[0]) if grid else 0

    if bg is None:
        bg = find_bg_color(grid)

    # Find the first row (from top) containing non-bg pixels
    content_start = h
    for r in range(h):
        if any(grid[r][c] != bg for c in range(w)):
            content_start = r
            break

    if content_start >= h:
        return [row[:] for row in grid]

    # Content rows = from content_start to end
    content = [grid[r][:] for r in range(content_start, h)]
    content_h = len(content)

    # Tile content to fill the full grid, bottom-aligned
    output = []
    for r in range(h):
        # Distance from bottom
        dist_from_bottom = h - 1 - r
        # Map to content row (bottom-aligned tiling)
        content_row_idx = content_h - 1 - (dist_from_bottom % content_h)
        output.append(content[content_row_idx][:])

    return output


def reflect_2x2_corners(grid, bg=0):
    """Find a 2x2 block of non-bg colors in the grid. For each corner of the 2x2,
    fill the rectangular area between the adjacent grid edge and the 2x2 block
    with the OPPOSITE (diagonally opposite) corner's color.

    The fill area for corner (r,c) going toward grid edge:
    - rows: from (r±1) to edge, exclusive of the last row/col
    - cols: from (c±1) to edge, exclusive of the last row/col
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
        return output

    # The 4 corners of the 2x2 block
    tl = grid[block_r][block_c]          # top-left
    tr = grid[block_r][block_c + 1]      # top-right
    bl = grid[block_r + 1][block_c]      # bottom-left
    br = grid[block_r + 1][block_c + 1]  # bottom-right

    # For each corner, fill a rectangle adjacent to the 2x2 block,
    # capped at block size (2) in each dimension, with opposite corner's color.

    # Top-left -> fill with bottom-right color
    fh = min(block_r, 2)
    fw = min(block_c, 2)
    for r in range(block_r - fh, block_r):
        for c in range(block_c - fw, block_c):
            output[r][c] = br

    # Top-right -> fill with bottom-left color
    fh = min(block_r, 2)
    fw = min(w - block_c - 2, 2)
    for r in range(block_r - fh, block_r):
        for c in range(block_c + 2, block_c + 2 + fw):
            output[r][c] = bl

    # Bottom-left -> fill with top-right color
    fh = min(h - block_r - 2, 2)
    fw = min(block_c, 2)
    for r in range(block_r + 2, block_r + 2 + fh):
        for c in range(block_c - fw, block_c):
            output[r][c] = tr

    # Bottom-right -> fill with top-left color
    fh = min(h - block_r - 2, 2)
    fw = min(w - block_c - 2, 2)
    for r in range(block_r + 2, block_r + 2 + fh):
        for c in range(block_c + 2, block_c + 2 + fw):
            output[r][c] = tl

    return output


def extend_diagonal_arms(grid, bg=0):
    """Find a shape consisting of a 2x2 block with single-pixel 'arms' at diagonal
    corners. Extend each arm's diagonal line to the grid boundary.

    The 2x2 block is identified, then each adjacent single pixel on a diagonal
    is an 'arm'. The arm's direction determines the extension direction."""
    h = len(grid)
    w = len(grid[0]) if grid else 0
    output = [row[:] for row in grid]

    # Find the 2x2 block of non-bg cells (all same color)
    block_r, block_c = None, None
    color = None
    for r in range(h - 1):
        for c in range(w - 1):
            if (grid[r][c] != bg and grid[r][c + 1] != bg and
                grid[r + 1][c] != bg and grid[r + 1][c + 1] != bg):
                vals = {grid[r][c], grid[r][c + 1], grid[r + 1][c], grid[r + 1][c + 1]}
                if len(vals) == 1:
                    block_r, block_c = r, c
                    color = grid[r][c]
                    break
        if block_r is not None:
            break

    if block_r is None:
        return output

    # Check 4 diagonal positions for arms
    diag_checks = [
        (block_r - 1, block_c - 1, -1, -1),  # top-left diagonal
        (block_r - 1, block_c + 2, -1, +1),  # top-right diagonal
        (block_r + 2, block_c - 1, +1, -1),  # bottom-left diagonal
        (block_r + 2, block_c + 2, +1, +1),  # bottom-right diagonal
    ]

    for arm_r, arm_c, dr, dc in diag_checks:
        if 0 <= arm_r < h and 0 <= arm_c < w and grid[arm_r][arm_c] == color:
            # Extend from the arm position outward
            r, c = arm_r + dr, arm_c + dc
            while 0 <= r < h and 0 <= c < w:
                output[r][c] = color
                r += dr
                c += dc

    return output


def fill_framed_interior(grid, frame_color=2, fill_color=1, bg=0):
    """Find closed rectangular frames of frame_color. If a frame's interior
    contains a single pixel of frame_color (marker dot), fill the rest of
    the interior with fill_color, keeping the marker dot.

    Frames without interior marker dots are left unchanged."""
    h = len(grid)
    w = len(grid[0]) if grid else 0
    output = [row[:] for row in grid]

    visited_frames = set()

    for top in range(h):
        for left in range(w):
            if grid[top][left] != frame_color:
                continue

            for right in range(left + 2, w):
                if grid[top][right] != frame_color:
                    continue
                if not all(grid[top][c] == frame_color for c in range(left, right + 1)):
                    continue

                for bottom in range(top + 2, h):
                    if grid[bottom][left] != frame_color or grid[bottom][right] != frame_color:
                        continue
                    if not all(grid[bottom][c] == frame_color for c in range(left, right + 1)):
                        continue
                    if not all(grid[r][left] == frame_color for r in range(top, bottom + 1)):
                        continue
                    if not all(grid[r][right] == frame_color for r in range(top, bottom + 1)):
                        continue

                    # Valid frame border. Check interior has only bg or frame_color.
                    valid_interior = True
                    has_bg = False
                    for r in range(top + 1, bottom):
                        for c in range(left + 1, right):
                            v = grid[r][c]
                            if v == bg:
                                has_bg = True
                            elif v != frame_color:
                                valid_interior = False
                                break
                        if not valid_interior:
                            break

                    if not valid_interior or not has_bg:
                        continue

                    frame_key = (top, left, bottom, right)
                    if frame_key not in visited_frames:
                        visited_frames.add(frame_key)
                        for r in range(top + 1, bottom):
                            for c in range(left + 1, right):
                                if output[r][c] == bg:
                                    output[r][c] = fill_color

    return output


def mirror_recolor_vertical(grid, target_color, replace_color):
    """For each cell with target_color, check if its vertical-axis mirror also
    has target_color. If so, change both to replace_color; otherwise keep as-is."""
    h = len(grid)
    w = len(grid[0]) if grid else 0
    output = [row[:] for row in grid]
    for r in range(h):
        for c in range(w):
            if grid[r][c] == target_color:
                mc = w - 1 - c
                if 0 <= mc < w and grid[r][mc] == target_color:
                    output[r][c] = replace_color
    return output


def count_inside_rect_fill(grid):
    """Find rectangle bordered by 1s, count non-0 non-1 cells inside,
    output 3x3 grid filled left-to-right top-to-bottom with marker color."""
    h = len(grid)
    w = len(grid[0]) if grid else 0
    # Find the rectangle of 1s
    ones = [(r, c) for r in range(h) for c in range(w) if grid[r][c] == 1]
    if not ones:
        return [[0]*3 for _ in range(3)]
    top = min(r for r, c in ones)
    bottom = max(r for r, c in ones)
    left = min(c for r, c in ones)
    right = max(c for r, c in ones)
    # Find marker color and count inside interior
    marker = None
    count = 0
    for r in range(top + 1, bottom):
        for c in range(left + 1, right):
            v = grid[r][c]
            if v != 0 and v != 1:
                if marker is None:
                    marker = v
                if v == marker:
                    count += 1
    if marker is None:
        return [[0]*3 for _ in range(3)]
    # Fill 3x3 grid
    out = [[0]*3 for _ in range(3)]
    filled = 0
    for r in range(3):
        for c in range(3):
            if filled < count:
                out[r][c] = marker
                filled += 1
    return out


def remove_noise_keep_blocks(grid, bg=0):
    """Remove colored pixels that lack both a horizontal and vertical
    same-color neighbor. Keeps only pixels that are part of solid blocks."""
    h = len(grid)
    w = len(grid[0]) if grid else 0
    output = [[bg]*w for _ in range(h)]
    for r in range(h):
        for c in range(w):
            v = grid[r][c]
            if v == bg:
                continue
            has_h = ((c > 0 and grid[r][c-1] == v) or
                     (c < w-1 and grid[r][c+1] == v))
            has_v = ((r > 0 and grid[r-1][c] == v) or
                     (r < h-1 and grid[r+1][c] == v))
            if has_h and has_v:
                output[r][c] = v
    return output


def extend_pixel_to_corner(grid, bg=0):
    """For each non-bg pixel, draw an L-shaped line toward the nearest grid corner.

    The pixel extends horizontally to the nearest left/right edge and vertically
    to the nearest top/bottom edge, forming an L going into the nearest corner."""
    h = len(grid)
    w = len(grid[0]) if grid else 0
    output = [row[:] for row in grid]

    pixels = []
    for r in range(h):
        for c in range(w):
            if grid[r][c] != bg:
                pixels.append((r, c, grid[r][c]))

    for r, c, color in pixels:
        # Determine nearest corner direction
        go_left = c < (w - 1 - c)     # True if closer to left edge
        go_up = r < (h - 1 - r)       # True if closer to top edge

        # Draw horizontal line to nearest horizontal edge
        if go_left:
            for cc in range(0, c + 1):
                output[r][cc] = color
        else:
            for cc in range(c, w):
                output[r][cc] = color

        # Draw vertical line to nearest vertical edge
        if go_up:
            for rr in range(0, r + 1):
                output[rr][c] = color
        else:
            for rr in range(r, h):
                output[rr][c] = color

    return output


def mark_domino_cross_centers(grid, domino_color=1, mark_color=4, bg=8):
    """Find 2-cell domino shapes of domino_color, pair perpendicular matched
    pairs, and place mark_color at the center of each cross.

    A cross is formed when:
    - Two vertical dominoes share the same column, with integer midpoint row R
    - Two horizontal dominoes share the same row, with integer midpoint col C
    - R and C coincide: place mark_color at (R, C)
    """
    h = len(grid)
    w = len(grid[0]) if grid else 0

    # Find all 2-cell dominoes (connected components of domino_color with size 2)
    visited = set()
    vert_dominoes = {}   # col -> list of (center_row,)
    horiz_dominoes = {}  # row -> list of (center_col,)

    for r in range(h):
        for c in range(w):
            if grid[r][c] != domino_color or (r, c) in visited:
                continue
            # BFS to find connected component
            comp = []
            queue = [(r, c)]
            visited.add((r, c))
            while queue:
                cr, cc = queue.pop(0)
                comp.append((cr, cc))
                for dr, dc in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                    nr, nc = cr + dr, cc + dc
                    if (0 <= nr < h and 0 <= nc < w and
                            (nr, nc) not in visited and grid[nr][nc] == domino_color):
                        visited.add((nr, nc))
                        queue.append((nr, nc))

            if len(comp) != 2:
                continue

            (r1, c1), (r2, c2) = comp
            if c1 == c2:  # vertical domino
                center_r = (r1 + r2) / 2.0
                col = c1
                vert_dominoes.setdefault(col, []).append(center_r)
            elif r1 == r2:  # horizontal domino
                center_c = (c1 + c2) / 2.0
                row = r1
                horiz_dominoes.setdefault(row, []).append(center_c)

    # Find midpoints of vertical domino pairs (per column)
    vert_midpoints = {}  # (R, C) -> True
    for col, centers in vert_dominoes.items():
        centers.sort()
        for i in range(len(centers)):
            for j in range(i + 1, len(centers)):
                mid_r = (centers[i] + centers[j]) / 2.0
                if mid_r == int(mid_r):
                    vert_midpoints.setdefault(int(mid_r), set()).add(col)

    # Find midpoints of horizontal domino pairs (per row)
    horiz_midpoints = {}  # (R, C) -> True
    for row, centers in horiz_dominoes.items():
        centers.sort()
        for i in range(len(centers)):
            for j in range(i + 1, len(centers)):
                mid_c = (centers[i] + centers[j]) / 2.0
                if mid_c == int(mid_c):
                    horiz_midpoints.setdefault(row, set()).add(int(mid_c))

    # Find intersections
    output = [r[:] for r in grid]
    for R, v_cols in vert_midpoints.items():
        if R in horiz_midpoints:
            h_cols = horiz_midpoints[R]
            for C in v_cols & h_cols:
                if 0 <= R < h and 0 <= C < w and output[R][C] == bg:
                    output[R][C] = mark_color

    return output


def rotation_quad_tile_2x2(grid):
    """Create a 4x4 tiling (12x12 from 3x3) with rotation quadrants.

    Layout:
      TL: 180° tiled 2x2    TR: 90°CW tiled 2x2
      BL: 270°CW tiled 2x2  BR: 0° tiled 2x2
    """
    rot180 = rotate_cw(grid, 2)
    rot90 = rotate_cw(grid, 1)
    rot270 = rotate_cw(grid, 3)

    def tile_2x2(g):
        top = concat_horizontal(g, g)
        return concat_vertical(top, top)

    tl = tile_2x2(rot180)
    tr = tile_2x2(rot90)
    bl = tile_2x2(rot270)
    br = tile_2x2(grid)

    top_half = concat_horizontal(tl, tr)
    bottom_half = concat_horizontal(bl, br)
    return concat_vertical(top_half, bottom_half)


def compress_separator_intersections(grid):
    """Extract colored pattern from grid separator intersections and compress.

    For grids with regular separator lines forming a mega-grid, extracts the
    colors at separator-line intersections that differ from the separator color,
    then compresses by collapsing identical adjacent rows/cols with gap insertion.

    Algorithm:
    1. Find separator color (most common), detect regular row/col positions
    2. Extract intersection values (non-separator → color, separator → 0)
    3. Crop to bounding box of non-zero values
    4. Group adjacent identical rows and columns
    5. Each group of N identical rows/cols → N-1 output rows/cols
    6. Insert 1 gap row/col between adjacent groups
    7. Gap cells: use neighbor value if all adjacent corners agree, else 0
    """
    h = len(grid)
    w = len(grid[0]) if grid else 0
    if h < 5 or w < 5:
        return None

    # Find separator color by detecting rows dominated by one color (>= 70%)
    # Group candidate separator rows by their dominant color
    threshold_frac = 0.7
    row_candidates = {}  # color -> list of row indices
    for r in range(h):
        counts = {}
        for c in range(w):
            v = grid[r][c]
            counts[v] = counts.get(v, 0) + 1
        dominant = max(counts, key=counts.get)
        if counts[dominant] >= w * threshold_frac:
            row_candidates.setdefault(dominant, []).append(r)

    # For each candidate color, check if its rows form a regular stride
    sep_color = None
    sep_rows = None
    best_regularity = 0
    for color, rows in row_candidates.items():
        if len(rows) < 3:
            continue
        # Find most common stride
        diffs = [rows[i + 1] - rows[i] for i in range(len(rows) - 1)]
        stride_counts = {}
        for d in diffs:
            stride_counts[d] = stride_counts.get(d, 0) + 1
        if not stride_counts:
            continue
        best_stride = max(stride_counts, key=stride_counts.get)
        regularity = stride_counts[best_stride]
        if regularity > best_regularity and best_stride >= 2:
            best_regularity = regularity
            sep_color = color
            row_stride = best_stride
    if sep_color is None:
        return None

    # Generate all separator row positions using detected stride
    candidate_rows = row_candidates[sep_color]
    first_r = candidate_rows[0] % row_stride
    sep_rows = list(range(first_r, h, row_stride))

    # Detect separator columns similarly
    col_candidates = {}
    for c in range(w):
        counts = {}
        for r in range(h):
            v = grid[r][c]
            counts[v] = counts.get(v, 0) + 1
        dominant = max(counts, key=counts.get)
        if counts[dominant] >= h * threshold_frac:
            col_candidates.setdefault(dominant, []).append(c)

    candidate_cols = col_candidates.get(sep_color, [])
    if len(candidate_cols) < 3:
        return None
    col_diffs = [candidate_cols[i + 1] - candidate_cols[i] for i in range(len(candidate_cols) - 1)]
    col_stride_counts = {}
    for d in col_diffs:
        col_stride_counts[d] = col_stride_counts.get(d, 0) + 1
    col_stride = max(col_stride_counts, key=col_stride_counts.get)
    if col_stride < 2:
        return None

    first_c = candidate_cols[0] % col_stride
    sep_cols = list(range(first_c, w, col_stride))

    # Extract intersection grid
    inter = []
    for ri in sep_rows:
        row = []
        for ci in sep_cols:
            v = grid[ri][ci]
            row.append(0 if v == sep_color else v)
        inter.append(row)

    # Find bounding box of non-zero values
    min_r = min_c = float('inf')
    max_r = max_c = -1
    for ri in range(len(inter)):
        for ci in range(len(inter[0])):
            if inter[ri][ci] != 0:
                min_r = min(min_r, ri)
                max_r = max(max_r, ri)
                min_c = min(min_c, ci)
                max_c = max(max_c, ci)
    if max_r < 0:
        return None

    # Crop to bounding box
    cropped = [inter[ri][min_c:max_c + 1] for ri in range(min_r, max_r + 1)]
    nr = len(cropped)
    nc = len(cropped[0]) if cropped else 0

    # Group adjacent identical rows
    row_groups = []  # list of (representative_row, count)
    i = 0
    while i < nr:
        j = i + 1
        while j < nr and cropped[j] == cropped[i]:
            j += 1
        row_groups.append((cropped[i], j - i))
        i = j

    # Group adjacent identical columns
    col_sigs = [tuple(cropped[ri][ci] for ri in range(nr)) for ci in range(nc)]
    col_groups = []  # list of (start_col_index, count)
    i = 0
    while i < nc:
        j = i + 1
        while j < nc and col_sigs[j] == col_sigs[i]:
            j += 1
        col_groups.append((i, j - i))
        i = j

    # Build column mapping: list of ('block', col_start) or ('gap', left_gj, right_gj)
    col_map = []
    for gj, (cs, cnt) in enumerate(col_groups):
        for _ in range(cnt - 1):
            col_map.append(('block', cs))
        if gj < len(col_groups) - 1:
            col_map.append(('gap', gj, gj + 1))

    # Build row mapping
    row_map = []
    for gi, (rep, cnt) in enumerate(row_groups):
        for _ in range(cnt - 1):
            row_map.append(('block', gi))
        if gi < len(row_groups) - 1:
            row_map.append(('gap', gi, gi + 1))

    if not row_map or not col_map:
        return None

    # Build output grid
    output = []
    for rm in row_map:
        out_row = []
        for cm in col_map:
            if rm[0] == 'block' and cm[0] == 'block':
                out_row.append(row_groups[rm[1]][0][cm[1]])
            elif rm[0] == 'block' and cm[0] == 'gap':
                rep = row_groups[rm[1]][0]
                left_val = rep[col_groups[cm[1]][0]]
                right_val = rep[col_groups[cm[2]][0]]
                out_row.append(left_val if left_val == right_val else 0)
            elif rm[0] == 'gap' and cm[0] == 'block':
                above_val = row_groups[rm[1]][0][cm[1]]
                below_val = row_groups[rm[2]][0][cm[1]]
                out_row.append(above_val if above_val == below_val else 0)
            else:  # gap x gap
                tl = row_groups[rm[1]][0][col_groups[cm[1]][0]]
                tr = row_groups[rm[1]][0][col_groups[cm[2]][0]]
                bl = row_groups[rm[2]][0][col_groups[cm[1]][0]]
                br = row_groups[rm[2]][0][col_groups[cm[2]][0]]
                out_row.append(tl if tl == tr == bl == br else 0)
        output.append(out_row)

    return output


def recolor_framed_pattern_by_keys(grid, bg=0):
    """Find a bordered pattern block, find 2-cell color key pairs outside it,
    and apply color substitution to non-frame colors in the block.

    Algorithm:
    1. Find bg color, extract all non-bg connected components
    2. Largest component = the pattern block
    3. Determine frame color (most common on perimeter of bounding box)
    4. Find horizontal 2-cell key pairs among remaining non-bg cells
    5. Build color map: key (A,B) maps whichever color is in the block interior
    6. Extract bounding box, apply substitution, return
    """
    h = len(grid)
    w = len(grid[0]) if grid else 0
    if h < 3 or w < 3:
        return None

    # Find all non-bg connected components
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
                comp.append((cr, cc))
                for dr, dc in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                    nr, nc = cr + dr, cc + dc
                    if 0 <= nr < h and 0 <= nc < w and (nr, nc) not in visited and grid[nr][nc] != bg:
                        visited.add((nr, nc))
                        queue.append((nr, nc))
            components.append(comp)

    if not components:
        return None

    # Largest component = pattern block
    components.sort(key=len, reverse=True)
    block = components[0]
    block_set = set(block)

    # Bounding box
    min_r = min(r for r, c in block)
    max_r = max(r for r, c in block)
    min_c = min(c for r, c in block)
    max_c = max(c for r, c in block)

    # Frame color = most common on perimeter of bounding box
    perim_counts = {}
    for r, c in block:
        if r == min_r or r == max_r or c == min_c or c == max_c:
            v = grid[r][c]
            perim_counts[v] = perim_counts.get(v, 0) + 1
    if not perim_counts:
        return None
    frame_color = max(perim_counts, key=perim_counts.get)

    # Interior colors in the block (non-frame)
    interior_colors = set()
    for r, c in block:
        v = grid[r][c]
        if v != frame_color:
            interior_colors.add(v)

    # Find 2-cell horizontal key pairs outside the block
    remaining_cells = set()
    for comp in components[1:]:
        for r, c in comp:
            remaining_cells.add((r, c))

    key_pairs = []
    used = set()
    for r, c in sorted(remaining_cells):
        if (r, c) in used:
            continue
        if (r, c + 1) in remaining_cells and (r, c + 1) not in used:
            a = grid[r][c]
            b = grid[r][c + 1]
            if a != bg and b != bg:
                key_pairs.append((a, b))
                used.add((r, c))
                used.add((r, c + 1))

    # Build color map
    color_map = {}
    for a, b in key_pairs:
        if b in interior_colors and b not in color_map:
            color_map[b] = a
        elif a in interior_colors and a not in color_map:
            color_map[a] = b

    # Extract bounding box and apply substitution
    output = []
    for r in range(min_r, max_r + 1):
        row = []
        for c in range(min_c, max_c + 1):
            v = grid[r][c]
            if v in color_map and v != frame_color:
                row.append(color_map[v])
            else:
                row.append(v)
        output.append(row)

    return output


def cross_pattern_vote(grid):
    """Find all cross patterns (center=4, 4 cardinal arms of same color).
    Return 1x1 grid with the arm color that appears most frequently."""
    h = len(grid)
    w = len(grid[0]) if grid else 0
    counts = {}
    for r in range(1, h - 1):
        for c in range(1, w - 1):
            if grid[r][c] != 4:
                continue
            up = grid[r - 1][c]
            down = grid[r + 1][c]
            left = grid[r][c - 1]
            right = grid[r][c + 1]
            if up == down == left == right and up != 4:
                counts[up] = counts.get(up, 0) + 1
    if not counts:
        return grid
    winner = max(counts, key=counts.get)
    return [[winner]]


def mark_square_corners(grid):
    """Find rectangular connected components of non-bg color that have a square
    bounding box. For each, place color 2 at the two outward-extension cells
    of each corner. Non-square shapes and 1D lines are left unchanged."""
    bg = find_bg_color(grid)
    h = len(grid)
    w = len(grid[0]) if grid else 0
    out = [row[:] for row in grid]

    visited = set()
    for r in range(h):
        for c in range(w):
            if grid[r][c] == bg or (r, c) in visited:
                continue
            # BFS to find connected component
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

            # Bounding box
            min_r = min(p[0] for p in comp)
            max_r = max(p[0] for p in comp)
            min_c = min(p[1] for p in comp)
            max_c = max(p[1] for p in comp)
            bh = max_r - min_r + 1
            bw = max_c - min_c + 1

            # Must be square and at least 2x2
            if bh != bw or bh < 2:
                continue

            # Place 2 at each outer corner's two perpendicular extension cells
            corners = [
                (min_r, min_c, -1, 0, 0, -1),  # top-left: up and left
                (min_r, max_c, -1, 0, 0, 1),    # top-right: up and right
                (max_r, min_c, 1, 0, 0, -1),    # bottom-left: down and left
                (max_r, max_c, 1, 0, 0, 1),     # bottom-right: down and right
            ]
            for cr, cc, dr1, dc1, dr2, dc2 in corners:
                nr1, nc1 = cr + dr1, cc + dc1
                nr2, nc2 = cr + dr2, cc + dc2
                if 0 <= nr1 < h and 0 <= nc1 < w:
                    out[nr1][nc1] = 2
                if 0 <= nr2 < h and 0 <= nc2 < w:
                    out[nr2][nc2] = 2

    return out


def bridge_markers_to_rects(grid):
    """Find rectangular blocks and isolated single-pixel markers of the same color.
    For each marker, draw a cross at marker (center->bg, 4 arms->color),
    a line from marker to nearest rect face, and widen the connection by 1 at the rect face."""
    bg = find_bg_color(grid)
    h = len(grid)
    w = len(grid[0]) if grid else 0
    out = [row[:] for row in grid]

    # Find connected components of non-bg cells
    visited = set()
    components = []
    for r in range(h):
        for c in range(w):
            if grid[r][c] == bg or (r, c) in visited:
                continue
            comp = []
            color = grid[r][c]
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
            max_r = max(p[0] for p in comp)
            min_c = min(p[1] for p in comp)
            max_c = max(p[1] for p in comp)
            components.append({
                "positions": set(comp),
                "color": color,
                "bbox": (min_r, min_c, max_r, max_c),
                "size": len(comp),
            })

    # Separate rectangles (size > 1) from markers (size == 1)
    rects = [c for c in components if c["size"] > 1]
    markers = [c for c in components if c["size"] == 1]

    for marker in markers:
        mc = marker["color"]
        mr, mcc = list(marker["positions"])[0]

        # Find nearest rect of same color
        best_rect = None
        best_dist = float("inf")
        for rect in rects:
            if rect["color"] != mc:
                continue
            rmin_r, rmin_c, rmax_r, rmax_c = rect["bbox"]
            # Distance to nearest edge
            dist = float("inf")
            if rmin_c <= mcc <= rmax_c:
                # Vertically aligned
                if mr < rmin_r:
                    dist = rmin_r - mr
                elif mr > rmax_r:
                    dist = mr - rmax_r
            if rmin_r <= mr <= rmax_r:
                # Horizontally aligned
                if mcc < rmin_c:
                    d = rmin_c - mcc
                elif mcc > rmax_c:
                    d = mcc - rmax_c
                else:
                    d = 0
                dist = min(dist, d)
            # General distance to nearest edge
            if dist == float("inf"):
                dr = max(rmin_r - mr, 0, mr - rmax_r)
                dc = max(rmin_c - mcc, 0, mcc - rmax_c)
                dist = dr + dc
            if dist < best_dist:
                best_dist = dist
                best_rect = rect

        if best_rect is None:
            continue

        rmin_r, rmin_c, rmax_r, rmax_c = best_rect["bbox"]

        # Determine direction from marker to rect
        # Find which face is closest
        candidates = []
        if rmin_c <= mcc <= rmax_c:
            if mr < rmin_r:
                candidates.append(("down", rmin_r - mr))
            if mr > rmax_r:
                candidates.append(("up", mr - rmax_r))
        if rmin_r <= mr <= rmax_r:
            if mcc < rmin_c:
                candidates.append(("right", rmin_c - mcc))
            if mcc > rmax_c:
                candidates.append(("left", mcc - rmax_c))

        if not candidates:
            continue

        direction = min(candidates, key=lambda x: x[1])[0]

        # Draw cross at marker position (center -> bg, 4 arms -> color)
        out[mr][mcc] = bg
        for dr, dc in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
            nr, nc = mr + dr, mcc + dc
            if 0 <= nr < h and 0 <= nc < w:
                out[nr][nc] = mc

        # Draw line from marker toward rect
        if direction == "down":
            # Line goes from mr+1 to rmin_r-1 at col mcc
            for r in range(mr + 2, rmin_r):
                out[r][mcc] = mc
            # Widen at rmin_r-1 (row just before rect face)
            wr = rmin_r - 1
            if wr > mr:
                if 0 <= mcc - 1 < w:
                    out[wr][mcc - 1] = mc
                out[wr][mcc] = mc
                if 0 <= mcc + 1 < w:
                    out[wr][mcc + 1] = mc
        elif direction == "up":
            for r in range(mr - 2, rmax_r, -1):
                out[r][mcc] = mc
            wr = rmax_r + 1
            if wr < mr:
                if 0 <= mcc - 1 < w:
                    out[wr][mcc - 1] = mc
                out[wr][mcc] = mc
                if 0 <= mcc + 1 < w:
                    out[wr][mcc + 1] = mc
        elif direction == "right":
            for c in range(mcc + 2, rmin_c):
                out[mr][c] = mc
            wc = rmin_c - 1
            if wc > mcc:
                if 0 <= mr - 1 < h:
                    out[mr - 1][wc] = mc
                out[mr][wc] = mc
                if 0 <= mr + 1 < h:
                    out[mr + 1][wc] = mc
        elif direction == "left":
            for c in range(mcc - 2, rmax_c, -1):
                out[mr][c] = mc
            wc = rmax_c + 1
            if wc < mcc:
                if 0 <= mr - 1 < h:
                    out[mr - 1][wc] = mc
                out[mr][wc] = mc
                if 0 <= mr + 1 < h:
                    out[mr + 1][wc] = mc

    return out


def flood_fill_border_interior(grid, bg=0, exterior_color=2, interior_color=5):
    """Replace bg cells connected to the grid border with exterior_color,
    and bg cells NOT connected to the border with interior_color.
    Non-bg cells are unchanged."""
    h = len(grid)
    w = len(grid[0]) if grid else 0
    if h == 0 or w == 0:
        return [row[:] for row in grid]

    # BFS from all border bg cells
    visited = set()
    queue = []
    for r in range(h):
        for c in range(w):
            if (r == 0 or r == h - 1 or c == 0 or c == w - 1) and grid[r][c] == bg:
                if (r, c) not in visited:
                    visited.add((r, c))
                    queue.append((r, c))

    while queue:
        cr, cc = queue.pop(0)
        for dr, dc in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
            nr, nc = cr + dr, cc + dc
            if 0 <= nr < h and 0 <= nc < w and (nr, nc) not in visited and grid[nr][nc] == bg:
                visited.add((nr, nc))
                queue.append((nr, nc))

    output = [row[:] for row in grid]
    for r in range(h):
        for c in range(w):
            if grid[r][c] == bg:
                output[r][c] = exterior_color if (r, c) in visited else interior_color
    return output


def invert_tiled_subgrids(grid, sep_value=0, corrupt_value=5):
    """Grid divided by sep_value rows/cols into a tiled arrangement of sub-grids.
    Two tile types exist: 'pattern' (uses 2 colors) and 'uniform' (single color).
    Corrupt tiles have corrupt_value replacing some cells.
    Inversion: pattern tiles become uniform (dominant color), uniform become pattern.
    Corrupt tiles are classified by surviving non-corrupt cells, then inverted.
    Separator lines are cleaned (corrupt_value -> sep_value)."""
    h = len(grid)
    w = len(grid[0]) if grid else 0
    if h == 0 or w == 0:
        return [row[:] for row in grid]

    # Find separator rows and cols (all sep_value, ignoring corrupt_value)
    sep_rows = []
    for r in range(h):
        if all(grid[r][c] == sep_value or grid[r][c] == corrupt_value for c in range(w)):
            non_corrupt = [grid[r][c] for c in range(w) if grid[r][c] != corrupt_value]
            if not non_corrupt or all(v == sep_value for v in non_corrupt):
                sep_rows.append(r)

    sep_cols = []
    for c in range(w):
        if all(grid[r][c] == sep_value or grid[r][c] == corrupt_value for r in range(h)):
            non_corrupt = [grid[r][c] for r in range(h) if grid[r][c] != corrupt_value]
            if not non_corrupt or all(v == sep_value for v in non_corrupt):
                sep_cols.append(c)

    # Extract row/col regions between separators
    def _regions(sep_indices, total):
        regions = []
        prev = 0
        for s in sorted(sep_indices):
            if s > prev:
                regions.append((prev, s - 1))
            prev = s + 1
        if prev < total:
            regions.append((prev, total - 1))
        return regions

    row_regions = _regions(sep_rows, h)
    col_regions = _regions(sep_cols, w)

    if not row_regions or not col_regions:
        return [row[:] for row in grid]

    # Extract sub-grids
    subgrids = []
    for ri, (r0, r1) in enumerate(row_regions):
        for ci, (c0, c1) in enumerate(col_regions):
            cells = []
            for r in range(r0, r1 + 1):
                row_cells = []
                for c in range(c0, c1 + 1):
                    row_cells.append(grid[r][c])
                cells.append(row_cells)
            subgrids.append((ri, ci, r0, r1, c0, c1, cells))

    # Find the two non-sep, non-corrupt colors
    all_colors = set()
    for _, _, _, _, _, _, cells in subgrids:
        for row in cells:
            for v in row:
                if v != sep_value and v != corrupt_value:
                    all_colors.add(v)

    if len(all_colors) < 2:
        return [row[:] for row in grid]

    # Find the "pattern" template from clean sub-grids (no corrupt_value)
    clean_grids = []
    for ri, ci, r0, r1, c0, c1, cells in subgrids:
        has_corrupt = any(v == corrupt_value for row in cells for v in row)
        if not has_corrupt:
            clean_grids.append(cells)

    if not clean_grids:
        return [row[:] for row in grid]

    # Count distinct sub-grid types among clean grids
    grid_counts = {}
    for cg in clean_grids:
        key = tuple(tuple(r) for r in cg)
        grid_counts[key] = grid_counts.get(key, 0) + 1

    # The pattern is the most common clean sub-grid
    sorted_patterns = sorted(grid_counts.items(), key=lambda x: -x[1])
    pattern_key = sorted_patterns[0][0]
    pattern_template = [list(r) for r in pattern_key]

    # Determine dominant color (most frequent in pattern)
    color_counts = {}
    for row in pattern_template:
        for v in row:
            if v != sep_value and v != corrupt_value:
                color_counts[v] = color_counts.get(v, 0) + 1

    dominant_color = max(color_counts, key=color_counts.get)

    # Determine the secondary color
    secondary_colors = [c for c in all_colors if c != dominant_color]
    secondary_color = secondary_colors[0] if secondary_colors else dominant_color

    # Uniform template = all dominant_color, same dimensions as pattern
    sh = len(pattern_template)
    sw = len(pattern_template[0]) if pattern_template else 0
    uniform_template = [[dominant_color] * sw for _ in range(sh)]

    # Classify each sub-grid as pattern or uniform
    def _classify(cells):
        """Returns 'pattern', 'uniform', or 'unknown'."""
        ch = len(cells)
        cw = len(cells[0]) if cells else 0
        if ch != sh or cw != sw:
            return 'unknown'
        pattern_match = True
        uniform_match = True
        for r in range(ch):
            for c in range(cw):
                v = cells[r][c]
                if v == corrupt_value:
                    continue
                if v != pattern_template[r][c]:
                    pattern_match = False
                if v != secondary_color:
                    uniform_match = False
        if pattern_match and not uniform_match:
            return 'pattern'
        if uniform_match and not pattern_match:
            return 'uniform'
        if pattern_match and uniform_match:
            return 'pattern'
        return 'unknown'

    # Build output
    output = [[sep_value] * w for _ in range(h)]

    for ri, ci, r0, r1, c0, c1, cells in subgrids:
        cls = _classify(cells)
        if cls == 'pattern':
            template = uniform_template
        elif cls == 'uniform':
            template = pattern_template
        else:
            template = uniform_template

        for r in range(r0, r1 + 1):
            for c in range(c0, c1 + 1):
                tr = r - r0
                tc = c - c0
                if tr < len(template) and tc < len(template[0]):
                    output[r][c] = template[tr][tc]

    return output


# ------------------------------------------------------------------
# separator_gravity_bars -- extract center rectangle from a grid
# divided by 4 separators, then fill bars toward the gravity wall
# ------------------------------------------------------------------

def separator_gravity_bars(grid):
    """Grid has 2 horizontal + 2 vertical full-span separator lines defining
    a center rectangle.  One separator's color also appears scattered elsewhere
    as a marker.  The output is the center rectangle framed by the separator
    borders.  Inside, for each column (vertical gravity) or row (horizontal
    gravity), a solid bar of the marker color extends from the matching
    separator wall to the farthest marker in that line within the center.

    Returns the framed output grid, or None on failure.
    """
    from collections import Counter

    H = len(grid)
    W = len(grid[0]) if grid else 0
    if H < 4 or W < 4:
        return None

    # -- find separator rows (every cell non-zero) -------------------
    sep_rows = []
    for r in range(H):
        if all(grid[r][c] != 0 for c in range(W)):
            cnt = Counter(grid[r])
            sep_rows.append((r, cnt.most_common(1)[0][0]))
    if len(sep_rows) != 2:
        return None

    # -- find separator cols -----------------------------------------
    sep_cols = []
    for c in range(W):
        col = [grid[r][c] for r in range(H)]
        if all(v != 0 for v in col):
            cnt = Counter(col)
            sep_cols.append((c, cnt.most_common(1)[0][0]))
    if len(sep_cols) != 2:
        return None

    r1, top_c = sep_rows[0]
    r2, bot_c = sep_rows[1]
    c1, left_c = sep_cols[0]
    c2, right_c = sep_cols[1]

    sep_colors = {top_c, bot_c, left_c, right_c}

    # -- identify marker color (separator color that appears scattered)
    marker = None
    for r in range(H):
        if r == r1 or r == r2:
            continue
        for c in range(W):
            if c == c1 or c == c2:
                continue
            v = grid[r][c]
            if v != 0 and v in sep_colors:
                marker = v
                break
        if marker is not None:
            break
    if marker is None:
        return None

    # -- gravity direction -------------------------------------------
    if marker == top_c:
        gravity = 'up'
    elif marker == bot_c:
        gravity = 'down'
    elif marker == left_c:
        gravity = 'left'
    else:
        gravity = 'right'

    # -- center region bounds ----------------------------------------
    inner_r1 = r1 + 1
    inner_r2 = r2 - 1
    inner_c1 = c1 + 1
    inner_c2 = c2 - 1
    inner_h = inner_r2 - inner_r1 + 1
    inner_w = inner_c2 - inner_c1 + 1
    if inner_h < 1 or inner_w < 1:
        return None

    # -- build inner grid with gravity bars --------------------------
    inner = [[0] * inner_w for _ in range(inner_h)]

    if gravity in ('up', 'down'):
        for col in range(inner_w):
            ic = inner_c1 + col
            positions = []
            for r in range(inner_r1, inner_r2 + 1):
                if grid[r][ic] == marker:
                    positions.append(r - inner_r1)
            if not positions:
                continue
            if gravity == 'down':
                farthest = min(positions)
                for row in range(farthest, inner_h):
                    inner[row][col] = marker
            else:
                farthest = max(positions)
                for row in range(farthest + 1):
                    inner[row][col] = marker
    else:
        for row in range(inner_h):
            ir = inner_r1 + row
            positions = []
            for c in range(inner_c1, inner_c2 + 1):
                if grid[ir][c] == marker:
                    positions.append(c - inner_c1)
            if not positions:
                continue
            if gravity == 'right':
                farthest = min(positions)
                for col in range(farthest, inner_w):
                    inner[row][col] = marker
            else:
                farthest = max(positions)
                for col in range(farthest + 1):
                    inner[row][col] = marker

    # -- assemble output with borders from input intersections -------
    out_h = inner_h + 2
    out_w = inner_w + 2
    out = [[0] * out_w for _ in range(out_h)]

    # top / bottom border rows (read directly from input separators)
    for oc in range(out_w):
        out[0][oc] = grid[r1][c1 + oc]
        out[out_h - 1][oc] = grid[r2][c1 + oc]

    # left / right border columns
    for orow in range(out_h):
        out[orow][0] = grid[r1 + orow][c1]
        out[orow][out_w - 1] = grid[r1 + orow][c2]

    # fill inner
    for r in range(inner_h):
        for c in range(inner_w):
            out[r + 1][c + 1] = inner[r][c]

    return out


# ============================================================
# PATTERN GENERATION primitives
# ============================================================

def checkerboard(grid):
    """Generate grid-line pattern: cell (r,c) = 0 only when both r and c are odd, else 1.
    Output same dimensions as input."""
    h = len(grid)
    w = len(grid[0]) if grid else 0
    return [[(0 if (r % 2 == 1 and c % 2 == 1) else 1) for c in range(w)] for r in range(h)]


def kronecker_self(grid):
    """Kronecker product of grid with itself.
    Each non-zero cell is replaced by a copy of the entire grid;
    each zero cell is replaced by an NxM block of zeros."""
    h = len(grid)
    w = len(grid[0]) if grid else 0
    out_h = h * h
    out_w = w * w
    out = [[0] * out_w for _ in range(out_h)]
    for br in range(h):
        for bc in range(w):
            if grid[br][bc] != 0:
                for r in range(h):
                    for c in range(w):
                        out[br * h + r][bc * w + c] = grid[r][c]
    return out
