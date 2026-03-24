"""
hodel.py — Minimal port of only the functions needed for object extraction from Michael Hodel's ARC DSL.
Original: ARC-solver/DSL/base.py  (objects, dneighbors, neighbors, mostcolor, asindices)

Uses pure Python only, with no external dependencies.
"""


def _mostcolor(grid: tuple) -> int:
    """Return the most frequently occurring color in the grid."""
    values = [v for row in grid for v in row]
    return max(set(values), key=values.count)


def _dneighbors(loc: tuple) -> frozenset:
    """4-directional (up/down/left/right) neighboring coordinates."""
    r, c = loc
    return frozenset({(r - 1, c), (r + 1, c), (r, c - 1), (r, c + 1)})


def _allneighbors(loc: tuple) -> frozenset:
    """8-directional (4 cardinal + 4 diagonal) neighboring coordinates."""
    r, c = loc
    return frozenset({
        (r - 1, c), (r + 1, c), (r, c - 1), (r, c + 1),
        (r - 1, c - 1), (r - 1, c + 1), (r + 1, c - 1), (r + 1, c + 1),
    })


def hodel_objects(grid: tuple, univalued: bool,
                   diagonal: bool, without_bg: bool) -> frozenset:
    """
    Port of Michael Hodel's objects() function.
    Finds connected components in the grid and returns a frozenset of frozensets.
    Each object: frozenset of (color, (row, col)) pairs.

    Args:
        grid:        tuple[tuple[int]] — read-only 2D grid
        univalued:   True -> only group same-color pixels into the same object
        diagonal:    True -> treat diagonal directions as connected
        without_bg:  True -> exclude the most frequent color (background) from objects
    """
    h, w = len(grid), len(grid[0])
    bg = _mostcolor(grid) if without_bg else None
    neighborfun = _allneighbors if diagonal else _dneighbors

    objs = set()
    occupied = set()

    for start_r in range(h):
        for start_c in range(w):
            loc = (start_r, start_c)
            if loc in occupied:
                continue
            val = grid[start_r][start_c]
            if val == bg:
                continue

            obj = {(val, loc)}
            cands = {loc}

            while cands:
                next_cands = set()
                for cand in cands:
                    v = grid[cand[0]][cand[1]]
                    if (val == v) if univalued else (v != bg):
                        obj.add((v, cand))
                        occupied.add(cand)
                        for nb in neighborfun(cand):
                            if 0 <= nb[0] < h and 0 <= nb[1] < w and nb not in occupied:
                                next_cands.add(nb)
                cands = next_cands

            objs.add(frozenset(obj))

    return frozenset(objs)


# 8 parameter combinations — same order as the original object_finder.py find_all_objects
PARAM_COMBINATIONS = [
    (True,  True,  True),   # univalued, diagonal, without_bg
    (False, True,  True),
    (True,  False, True),
    (False, False, True),
    (True,  True,  False),
    (False, True,  False),
    (True,  False, False),
    (False, False, False),
]


def find_all_objects(raw: list) -> list:
    """
    Run hodel_objects with 8 parameter combinations and return a list of unique objects.

    Returns: list of dict, each dict:
        {
          "obj":    frozenset of (color, (row, col)),
          "pos":    (row_min, col_min),            <- absolute coordinates of left_top
          "color":  {0: bool, ..., 9: bool},
          "method": {"univalued": bool, "diagonal": bool, "without_bg": bool},
          "colorgrid": list[list[int]],           <- bbox size, transparent=13
        }
    """
    grid = tuple(tuple(row) for row in raw)
    seen: set = set()
    result: list = []

    for univalued, diagonal, without_bg in PARAM_COMBINATIONS:
        for obj_fs in hodel_objects(grid, univalued, diagonal, without_bg):
            key = frozenset(obj_fs)
            if key in seen:
                continue
            seen.add(key)

            pixels = sorted(obj_fs, key=lambda x: (x[1][0], x[1][1]))
            rows = [r for _, (r, _) in pixels]
            cols = [c for _, (_, c) in pixels]
            row_min, row_max = min(rows), max(rows)
            col_min, col_max = min(cols), max(cols)

            bb_h = row_max - row_min + 1
            bb_w = col_max - col_min + 1
            colorgrid = [[13] * bb_w for _ in range(bb_h)]
            color_dict = {i: False for i in range(10)}
            for color, (r, c) in pixels:
                colorgrid[r - row_min][c - col_min] = color
                if 0 <= color <= 9:
                    color_dict[color] = True

            result.append({
                "obj":       frozenset(obj_fs),
                "pos":       (row_min, col_min),
                "color":     color_dict,
                "method":    {
                    "univalued":   univalued,
                    "diagonal":    diagonal,
                    "without_bg":  without_bg,
                },
                "colorgrid": colorgrid,
            })

    return result
