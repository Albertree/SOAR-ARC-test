"""
OBJECT node — a connected component under a GRID.
Node ID format: T{hex}.P{p}.G{g}.O{o}
"""

import json
import os

from ARCKG.memory_paths import id_to_json_path, node_id_to_folder_path


class Object:
    """
    INTENT: A single object detected by the hodel objects() function.
            Initialized with colorgrid (bbox size, transparent=13) and absolute position pos within the grid.
            Serializes 8 properties (area/color/coordinate/method/position/shape/size/symmetry)
            via to_json().
    MUST NOT: Do not store the entire GRID. Only holds the bbox range.
    REF: ARC-solver/ARCKG/object.py OBJECT.update_property (line 170)
         ARC-solver/DSL/object_finder.py find_all_objects (line 62)
    """

    def __init__(self, object_id: str, colorgrid: list, pos: tuple, method: dict):
        """
        Args:
            object_id:  full node_id string (e.g. "T0a.P0.G0.O3")
            colorgrid:  list[list[int]], bbox size. Transparent cell = 13.
            pos:        (row_min, col_min) — absolute coordinates of the bbox left_top
            method:     {"univalued": bool, "diagonal": bool, "without_bg": bool}
        """
        self.node_id = object_id
        self.colorgrid = colorgrid
        self.pos = pos
        self.method = method
        self.pixels: list = []  # List of Pixel objects (object-level)

        # --- transformation DSL selection interface ---
        h = len(colorgrid)
        w = len(colorgrid[0]) if colorgrid else 0
        row_min, col_min = pos

        # bbox: alias for colorgrid (accessed as selection.bbox in transformation.py)
        self.bbox = colorgrid

        # coordinate: list of absolute (row, col) for non-transparent cells
        self.coordinate = [
            (row_min + r, col_min + c)
            for r, row in enumerate(colorgrid)
            for c, cell in enumerate(row)
            if cell != 13
        ]

        # all (row, col) within the bbox — used for grab validation in teleport
        self.bbox_coordinate = [
            (row_min + r, col_min + c)
            for r in range(h)
            for c in range(w)
        ]

        # vertex absolute coordinates
        self.left_top     = (row_min,         col_min)
        self.right_top    = (row_min,         col_min + w - 1)
        self.left_bottom  = (row_min + h - 1, col_min)
        self.right_bottom = (row_min + h - 1, col_min + w - 1)

        # --- backward-compatible properties (bounding_box, mask, color) ---
        self.bounding_box = (row_min, col_min, row_min + h - 1, col_min + w - 1)
        self.mask = [[cell != 13 for cell in row] for row in colorgrid]
        colors = [cell for row in colorgrid for cell in row if cell != 13]
        self.color = max(set(colors), key=colors.count) if colors else 0

    # ------------------------------------------------------------------ #
    #  Symmetry helpers (original: ARC-solver/ARCKG/object.py)            #
    # ------------------------------------------------------------------ #

    @staticmethod
    def _hori_symmetry(grid: list) -> bool:
        """Horizontal (vertical axis) symmetry — each row is identical when reversed."""
        return all(row == list(reversed(row)) for row in grid)

    @staticmethod
    def _verti_symmetry(grid: list) -> bool:
        """Vertical (horizontal axis) symmetry — identical when flipped upside down."""
        return grid == list(reversed(grid))

    @staticmethod
    def _diag_symmetry(grid: list) -> bool:
        """Main diagonal symmetry (square grids only)."""
        n = len(grid)
        return all(grid[i][j] == grid[j][i] for i in range(n) for j in range(n))

    @staticmethod
    def _anti_symmetry(grid: list) -> bool:
        """Anti-diagonal symmetry (square grids only)."""
        n = len(grid)
        return all(
            grid[i][j] == grid[n - 1 - j][n - 1 - i]
            for i in range(n) for j in range(n)
        )

    # ------------------------------------------------------------------ #
    #  Serialization                                                      #
    # ------------------------------------------------------------------ #

    def to_json(self) -> dict:
        """
        Return a dict of 8 OBJECT properties.

        area       : number of non-transparent (0-9) cells within the bbox
        color      : {0: bool, ..., 9: bool}
        coordinate : [[row, col], ...] — list of absolute coordinates of non-transparent cells
        method     : {"univalued": bool, "diagonal": bool, "without_bg": bool}
        position   : left_top / right_top / left_bottom / right_bottom
        shape      : bbox 2D array, non-transparent=1, transparent=-1
        size       : {"height": int, "width": int}
        symmetry   : {hori_symm / verti_symm / diag_symm / anti_symm}
        """
        h = len(self.colorgrid)
        w = len(self.colorgrid[0]) if self.colorgrid else 0
        row_min, col_min = self.pos

        # color
        color_dict = {i: False for i in range(10)}
        for row in self.colorgrid:
            for cell in row:
                if 0 <= cell <= 9:
                    color_dict[cell] = True

        # coordinate (absolute coordinates)
        coordinate = [
            [row_min + r, col_min + c]
            for r, row in enumerate(self.colorgrid)
            for c, cell in enumerate(row)
            if cell != 13
        ]

        # shape: non-transparent=1, transparent=-1
        shape = [
            [1 if cell != 13 else -1 for cell in row]
            for row in self.colorgrid
        ]

        # area
        area = sum(1 for row in shape for v in row if v == 1)

        # position
        position = {
            "left_top":     {"row_index": row_min,         "col_index": col_min},
            "right_top":    {"row_index": row_min,         "col_index": col_min + w - 1},
            "left_bottom":  {"row_index": row_min + h - 1, "col_index": col_min},
            "right_bottom": {"row_index": row_min + h - 1, "col_index": col_min + w - 1},
        }

        # symmetry
        hori_symm  = self._hori_symmetry(self.colorgrid)
        verti_symm = self._verti_symmetry(self.colorgrid)
        if h == w:
            diag_symm = self._diag_symmetry(self.colorgrid)
            anti_symm = self._anti_symmetry(self.colorgrid)
        else:
            diag_symm = False
            anti_symm = False

        return {
            "area":       area,
            "color":      color_dict,
            "coordinate": coordinate,
            "method":     self.method,
            "position":   position,
            "shape":      shape,
            "size":       {"height": h, "width": w},
            "symmetry": {
                "hori_symm":  hori_symm,
                "verti_symm": verti_symm,
                "diag_symm":  diag_symm,
                "anti_symm":  anti_symm,
            },
        }

    def save(self, semantic_memory_root: str):
        """Write to_json() as E_O{o}.json and save all child Pixels as well."""
        folder = node_id_to_folder_path(self.node_id, semantic_memory_root)
        os.makedirs(folder, exist_ok=True)
        path = id_to_json_path(self.node_id, semantic_memory_root)
        with open(path, "w") as f:
            json.dump({"id": self.node_id, "result": self.to_json()}, f, indent=2)
        for pixel in self.pixels:
            pixel.save(semantic_memory_root)

    def __repr__(self) -> str:
        return (f"Object(id={self.node_id}, color={self.color}, "
                f"pos={self.pos}, pixels={len(self.pixels)})")
