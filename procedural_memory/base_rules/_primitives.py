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

def isolate_middle_column(grid, bg=0):
    """Keep only the middle column (width // 2), fill rest with bg."""
    h = len(grid)
    w = len(grid[0]) if grid else 0
    mid = w // 2
    return [[grid[r][c] if c == mid else bg for c in range(w)] for r in range(h)]


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


def reverse_rings(grid):
    """Reverse the color order of concentric rectangular rings.
    Ring 0 is the outermost border, ring 1 is the next inner ring, etc.
    Each cell gets the color from the ring at the opposite depth."""
    h = len(grid)
    w = len(grid[0]) if grid else 0
    max_d = (min(h, w) - 1) // 2
    # Collect the color at each ring depth
    ring_colors = {}
    for d in range(max_d + 1):
        ring_colors[d] = grid[d][d]
    # Assign each cell the color from the reversed ring depth
    output = [row[:] for row in grid]
    for r in range(h):
        for c in range(w):
            d = min(r, c, h - 1 - r, w - 1 - c)
            rev_d = max_d - d
            output[r][c] = ring_colors[rev_d]
    return output


def rank_recolor_columns(grid, target_color, bg=0):
    """Recolor columns of `target_color` by rank of their cell count (descending).
    Tallest column of target_color gets color 1, next gets 2, etc."""
    h = len(grid)
    w = len(grid[0]) if grid else 0
    # Count target_color cells per column
    col_counts = {}
    for c in range(w):
        cnt = sum(1 for r in range(h) if grid[r][c] == target_color)
        if cnt > 0:
            col_counts[c] = cnt
    # Sort by count descending, then by column index for stable ordering
    ranked = sorted(col_counts.keys(), key=lambda c: (-col_counts[c], c))
    # Assign colors 1, 2, 3, ...
    col_to_color = {c: i + 1 for i, c in enumerate(ranked)}
    # Build output
    output = [row[:] for row in grid]
    for c, new_color in col_to_color.items():
        for r in range(h):
            if grid[r][c] == target_color:
                output[r][c] = new_color
    return output


def fill_quadrants_from_corners(grid, fill_color, bg=0):
    """Find rectangles of fill_color with 4 corner markers at diagonal positions.
    Replace each rectangle with 4 quadrants colored by the corner markers.
    Remove the corner markers."""
    h = len(grid)
    w = len(grid[0]) if grid else 0
    output = [row[:] for row in grid]

    # Find connected components of fill_color
    visited = set()
    rects = []
    for r in range(h):
        for c in range(w):
            if grid[r][c] == fill_color and (r, c) not in visited:
                comp = []
                queue = [(r, c)]
                visited.add((r, c))
                while queue:
                    cr, cc = queue.pop(0)
                    comp.append((cr, cc))
                    for dr, dc in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                        nr, nc = cr + dr, cc + dc
                        if 0 <= nr < h and 0 <= nc < w and (nr, nc) not in visited and grid[nr][nc] == fill_color:
                            visited.add((nr, nc))
                            queue.append((nr, nc))
                rs = [p[0] for p in comp]
                cs = [p[1] for p in comp]
                rects.append((min(rs), min(cs), max(rs), max(cs)))

    for top, left, bottom, right in rects:
        rh = bottom - top + 1
        rw = right - left + 1
        # Find corner markers
        positions = [
            (top - 1, left - 1),   # top-left
            (top - 1, right + 1),  # top-right
            (bottom + 1, left - 1),  # bottom-left
            (bottom + 1, right + 1),  # bottom-right
        ]
        colors = []
        for pr, pc in positions:
            if 0 <= pr < h and 0 <= pc < w and grid[pr][pc] != bg and grid[pr][pc] != fill_color:
                colors.append(grid[pr][pc])
            else:
                colors = []
                break
        if len(colors) != 4:
            continue

        tl_color, tr_color, bl_color, br_color = colors
        mid_r = top + rh // 2
        mid_c = left + rw // 2

        for r in range(top, bottom + 1):
            for c in range(left, right + 1):
                if r < mid_r and c < mid_c:
                    output[r][c] = tl_color
                elif r < mid_r and c >= mid_c:
                    output[r][c] = tr_color
                elif r >= mid_r and c < mid_c:
                    output[r][c] = bl_color
                else:
                    output[r][c] = br_color

        # Remove corner markers
        for pr, pc in positions:
            output[pr][pc] = bg

    return output


def staircase_from_row(grid, bg=0):
    """Take a 1-row input grid and expand into a staircase.
    Each row i has (start_count + i) colored cells from the left.
    Number of rows = width // 2. Color and start_count derived from input."""
    if len(grid) != 1:
        return None
    row = grid[0]
    width = len(row)
    color = None
    start_count = 0
    for v in row:
        if v != bg:
            if color is None:
                color = v
            start_count += 1
    if color is None:
        return [r[:] for r in grid]
    num_rows = width // 2
    output = []
    for i in range(num_rows):
        count = start_count + i
        r = [color] * min(count, width) + [bg] * max(0, width - count)
        output.append(r)
    return output


def staircase(grid, color, start_count, width):
    """Build a staircase grid: each row i has (start_count + i) cells of `color`
    from the left, rest are 0. Number of rows = width // 2."""
    num_rows = width // 2
    output = []
    for i in range(num_rows):
        count = start_count + i
        row = [color] * min(count, width) + [0] * max(0, width - count)
        output.append(row)
    return output


def rank_recolor_objects(grid, target_color, bg=0):
    """Find connected components of target_color. Recolor by size rank.
    Components with the same size get the same color.
    Largest -> 1, next size -> 2, etc."""
    h = len(grid)
    w = len(grid[0]) if grid else 0
    visited = set()
    components = []
    for r in range(h):
        for c in range(w):
            if grid[r][c] == target_color and (r, c) not in visited:
                comp = []
                queue = [(r, c)]
                visited.add((r, c))
                while queue:
                    cr, cc = queue.pop(0)
                    comp.append((cr, cc))
                    for dr, dc in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                        nr, nc = cr + dr, cc + dc
                        if 0 <= nr < h and 0 <= nc < w and (nr, nc) not in visited and grid[nr][nc] == target_color:
                            visited.add((nr, nc))
                            queue.append((nr, nc))
                components.append(comp)
    # Sort by size descending, then by top-left position for stability
    components.sort(key=lambda c: (-len(c), min(c)))
    output = [row[:] for row in grid]
    rank = 1
    i = 0
    while i < len(components):
        size = len(components[i])
        j = i
        while j < len(components) and len(components[j]) == size:
            for r, c in components[j]:
                output[r][c] = rank
            j += 1
        rank += 1
        i = j
    return output


def fill_rect_interiors_by_size(grid, border_color, bg=0):
    """Find rectangles bordered by border_color with bg interiors.
    Fill interiors by area rank: largest -> 8, next -> 7, next -> 6, etc."""
    h = len(grid)
    w = len(grid[0]) if grid else 0
    visited = set()
    components = []
    for r in range(h):
        for c in range(w):
            if grid[r][c] == border_color and (r, c) not in visited:
                comp = []
                queue = [(r, c)]
                visited.add((r, c))
                while queue:
                    cr, cc = queue.pop(0)
                    comp.append((cr, cc))
                    for dr, dc in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                        nr, nc = cr + dr, cc + dc
                        if 0 <= nr < h and 0 <= nc < w and (nr, nc) not in visited and grid[nr][nc] == border_color:
                            visited.add((nr, nc))
                            queue.append((nr, nc))
                components.append(comp)
    rectangles = []
    for comp in components:
        rs = [p[0] for p in comp]
        cs = [p[1] for p in comp]
        min_r, max_r = min(rs), max(rs)
        min_c, max_c = min(cs), max(cs)
        expected_border = set()
        for r in range(min_r, max_r + 1):
            for c in range(min_c, max_c + 1):
                if r == min_r or r == max_r or c == min_c or c == max_c:
                    expected_border.add((r, c))
        if set(comp) == expected_border and (max_r - min_r) >= 2 and (max_c - min_c) >= 2:
            interior = []
            for r in range(min_r + 1, max_r):
                for c in range(min_c + 1, max_c):
                    interior.append((r, c))
            if interior:
                rectangles.append((len(interior), interior))
    rectangles.sort(key=lambda x: -x[0])
    output = [row[:] for row in grid]
    rank = 0
    i = 0
    while i < len(rectangles):
        size = rectangles[i][0]
        j = i
        while j < len(rectangles) and rectangles[j][0] == size:
            color = 8 - rank
            for r, c in rectangles[j][1]:
                output[r][c] = color
            j += 1
        rank += 1
        i = j
    return output


def fill_cross_grid_sections(grid, bg=7):
    """Grid has a vertical column of one color and horizontal colored rows.
    Intersections have a marker color. Fill each section between colored rows:
    upper half gets upper row's color, lower half gets lower row's color.
    Odd-gap midpoint rows become all-intersection-color.
    Colored rows become all-intersection-color with column color at intersection."""
    h = len(grid)
    w = len(grid[0]) if grid else 0

    # Find vertical column: column where most cells are one non-bg color
    col_idx = None
    col_color = None
    for c in range(w):
        counts = {}
        for r in range(h):
            v = grid[r][c]
            if v != bg:
                counts[v] = counts.get(v, 0) + 1
        if counts:
            main = max(counts, key=counts.get)
            if counts[main] >= h // 2:
                col_idx = c
                col_color = main
                break

    if col_idx is None:
        return None

    # Find horizontal colored rows (full-width non-bg rows)
    intersection_color = None
    colored_rows = []
    for r in range(h):
        row_vals = [grid[r][c] for c in range(w) if c != col_idx]
        unique = set(row_vals)
        if len(unique) == 1:
            color = row_vals[0]
            if color != bg:
                colored_rows.append((r, color))
                if intersection_color is None:
                    intersection_color = grid[r][col_idx]

    if not colored_rows or intersection_color is None:
        return None

    # Assign colors to each row
    row_info = {}  # r -> ('colored_row'|'fill'|'midpoint', color)

    for r, color in colored_rows:
        row_info[r] = ('colored_row', color)

    # Above first colored row
    for r in range(0, colored_rows[0][0]):
        row_info[r] = ('fill', colored_rows[0][1])

    # Below last colored row
    for r in range(colored_rows[-1][0] + 1, h):
        row_info[r] = ('fill', colored_rows[-1][1])

    # Between adjacent colored rows
    for i in range(len(colored_rows) - 1):
        r1, c1 = colored_rows[i]
        r2, c2 = colored_rows[i + 1]
        gap_start = r1 + 1
        gap_end = r2 - 1
        n = gap_end - gap_start + 1
        if n <= 0:
            continue
        if c1 == c2:
            for r in range(gap_start, gap_end + 1):
                row_info[r] = ('fill', c1)
        else:
            half = n // 2
            for r in range(gap_start, gap_start + half):
                row_info[r] = ('fill', c1)
            for r in range(gap_end - half + 1, gap_end + 1):
                row_info[r] = ('fill', c2)
            if n % 2 == 1:
                row_info[gap_start + half] = ('midpoint', None)

    # Build output
    output = [[bg] * w for _ in range(h)]
    for r in range(h):
        info = row_info.get(r)
        if info is None:
            output[r] = grid[r][:]
            continue
        kind, color = info
        if kind == 'colored_row':
            for c in range(w):
                output[r][c] = intersection_color
            output[r][col_idx] = col_color
        elif kind == 'fill':
            for c in range(w):
                output[r][c] = color
            output[r][col_idx] = intersection_color
        elif kind == 'midpoint':
            for c in range(w):
                output[r][c] = intersection_color
    return output


def connect_diamonds(grid, line_color=1, bg=0):
    """Find diamond shapes (3x3 cross of a color) and connect pairs that share
    the same row or column center with a line of line_color between them."""
    h = len(grid)
    w = len(grid[0]) if grid else 0

    # Find diamond centers: (r,c) where top/left/right/bottom are non-bg, center is bg
    centers = []
    for r in range(1, h - 1):
        for c in range(1, w - 1):
            top = grid[r - 1][c]
            left = grid[r][c - 1]
            right = grid[r][c + 1]
            bottom = grid[r + 1][c]
            center = grid[r][c]
            if (center == bg and top != bg and top == left == right == bottom):
                centers.append((r, c))

    output = [row[:] for row in grid]

    # Group by row and column, then connect only adjacent pairs
    from collections import defaultdict
    row_groups = defaultdict(list)
    col_groups = defaultdict(list)
    for r, c in centers:
        row_groups[r].append(c)
        col_groups[c].append(r)

    # Connect horizontally adjacent centers on same row
    for r, cols in row_groups.items():
        cols.sort()
        for k in range(len(cols) - 1):
            lo, hi = cols[k], cols[k + 1]
            for c in range(lo + 2, hi - 1):
                output[r][c] = line_color

    # Connect vertically adjacent centers on same column
    for c, rows in col_groups.items():
        rows.sort()
        for k in range(len(rows) - 1):
            lo, hi = rows[k], rows[k + 1]
            for r in range(lo + 2, hi - 1):
                output[r][c] = line_color

    return output


def separator_reflect_trails(grid, bg=7):
    """Reflect colored markers across a horizontal separator row (all 9s).
    Above separator: color A markers (5). Below: color B markers (2) with 6-trails.
    Each B marker follows its chain of adjacent 6s to a new position.
    Each A marker moves to the mirror of the new B position.
    Clears all other cells to bg."""
    h = len(grid)
    w = len(grid[0]) if grid else 0

    # Find separator row
    sep = None
    for r in range(h):
        if all(grid[r][c] == 9 for c in range(w)):
            sep = r
            break
    if sep is None:
        return None

    # Find marker and trail positions below separator
    markers = []  # (r, c) of 2s
    trails = set()  # (r, c) of 6s
    for r in range(sep + 1, h):
        for c in range(w):
            if grid[r][c] == 2:
                markers.append((r, c))
            elif grid[r][c] == 6:
                trails.add((r, c))

    # For each marker, follow the trail of 6s
    output = [[bg] * w for _ in range(h)]
    # Keep separator
    for c in range(w):
        output[sep][c] = 9

    for mr, mc in markers:
        # BFS/DFS along adjacent 6s
        pos = (mr, mc)
        visited = {pos}
        changed = True
        while changed:
            changed = False
            cr, cc = pos
            for dr, dc in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                nr, nc = cr + dr, cc + dc
                if (nr, nc) in trails and (nr, nc) not in visited:
                    visited.add((nr, nc))
                    pos = (nr, nc)
                    changed = True
                    break  # follow one step at a time

        # Place 2 at new position
        new_r, new_c = pos
        output[new_r][new_c] = 2

        # Mirror position: distance from separator
        dist = new_r - sep
        mirror_r = sep - dist
        if 0 <= mirror_r < h:
            output[mirror_r][new_c] = 5

    return output


def connect_waypoints(grid, bg=0):
    """Draw L-shaped paths of 3s between waypoints starting from the 3 cell.
    Waypoint 6 = clockwise turn, waypoint 8 = counterclockwise turn.
    Path starts going RIGHT from the 3 position."""
    h = len(grid)
    w = len(grid[0]) if grid else 0

    # Find start (3) and waypoints (6, 8)
    start = None
    waypoints = {}  # (r,c) -> type (6 or 8)
    for r in range(h):
        for c in range(w):
            if grid[r][c] == 3:
                start = (r, c)
            elif grid[r][c] in (6, 8):
                waypoints[(r, c)] = grid[r][c]
    if start is None:
        return None

    output = [row[:] for row in grid]
    # Clear all 3s initially (will redraw)
    for r in range(h):
        for c in range(w):
            if output[r][c] == 3:
                output[r][c] = bg

    # Direction vectors: right, down, left, up
    DIRS = [(0, 1), (1, 0), (0, -1), (-1, 0)]
    # Clockwise turn: dir_idx -> (dir_idx + 1) % 4
    # Counterclockwise: dir_idx -> (dir_idx - 1) % 4

    pos = start
    dir_idx = 0  # start going RIGHT
    output[pos[0]][pos[1]] = 3

    max_steps = h * w * 4  # safety limit
    steps = 0
    while steps < max_steps:
        steps += 1
        dr, dc = DIRS[dir_idx]

        # Scan along current direction for a waypoint
        found_wp = None
        scan_r, scan_c = pos[0] + dr, pos[1] + dc
        while 0 <= scan_r < h and 0 <= scan_c < w:
            if (scan_r, scan_c) in waypoints:
                found_wp = (scan_r, scan_c)
                break
            scan_r += dr
            scan_c += dc

        if found_wp:
            wp_r, wp_c = found_wp
            wp_type = waypoints[found_wp]
            # Draw 3s from pos+1 to one cell before waypoint
            cr, cc = pos[0] + dr, pos[1] + dc
            while (cr, cc) != (wp_r, wp_c):
                output[cr][cc] = 3
                cr += dr
                cc += dc
            # Turn point is one cell before waypoint
            turn_r, turn_c = wp_r - dr, wp_c - dc
            # Update direction
            if wp_type == 6:
                dir_idx = (dir_idx + 1) % 4  # clockwise
            else:
                dir_idx = (dir_idx - 1) % 4  # counterclockwise
            pos = (turn_r, turn_c)
            # Remove used waypoint
            del waypoints[found_wp]
        else:
            # No waypoint found, draw to edge
            cr, cc = pos[0] + dr, pos[1] + dc
            while 0 <= cr < h and 0 <= cc < w:
                output[cr][cc] = 3
                cr += dr
                cc += dc
            break

    return output
