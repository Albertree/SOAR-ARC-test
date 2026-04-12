"""
Shared helper functions for base rule modules.
"""


def group_positions(positions):
    """Group (row, col) positions into 4-connected components."""
    pos_set = set(positions)
    visited = set()
    groups = []

    for pos in positions:
        if pos in visited:
            continue
        group = []
        queue = [pos]
        while queue:
            p = queue.pop(0)
            if p in visited or p not in pos_set:
                continue
            visited.add(p)
            group.append(p)
            r, c = p
            for dr, dc in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                nb = (r + dr, c + dc)
                if nb in pos_set and nb not in visited:
                    queue.append(nb)
        groups.append(group)

    return groups


def find_components(grid, color):
    """Find all connected components of a given color in grid."""
    h = len(grid)
    w = len(grid[0]) if grid else 0
    visited = set()
    components = []
    for r in range(h):
        for c in range(w):
            if grid[r][c] == color and (r, c) not in visited:
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
                components.append(comp)
    return components


def find_non_bg_components(grid, bg):
    """Find 4-connected components of non-background cells (any color)."""
    h = len(grid)
    w = len(grid[0]) if grid else 0
    visited = set()
    components = []
    for r in range(h):
        for c in range(w):
            if grid[r][c] != bg and (r, c) not in visited:
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
    return components


def bounding_box(cells):
    """Return (min_r, max_r, min_c, max_c) for a list of (r, c) positions."""
    rs = [r for r, c in cells]
    cs = [c for r, c in cells]
    return min(rs), max(rs), min(cs), max(cs)
