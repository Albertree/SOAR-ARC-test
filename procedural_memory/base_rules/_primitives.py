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
