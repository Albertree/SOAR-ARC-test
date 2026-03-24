"""
PIXEL node — a single pixel under an OBJECT or GRID.
Node ID format: T{hex}.P{p}.G{g}.O{o}.X{x}  (object-level)
                T{hex}.P{p}.G{g}.X{x}         (grid-level)
"""

import json
import os

from ARCKG.memory_paths import id_to_json_path, node_id_to_folder_path


class Pixel:
    """
    INTENT: A KG node representing a single pixel's color and absolute coordinates within the grid.
            Writes the E_X{x}.json property file via to_json().
    REF: ARC-solver/ARCKG/pixel.py PIXEL (line 11)
    """

    def __init__(self, pixel_id: str, color: int, row: int, col: int):
        """
        Args:
            pixel_id: full node_id string (e.g. "T0a.P0.G0.O2.X5")
            color:    0-9 color value
            row:      absolute row index within the grid
            col:      absolute column index within the grid
        """
        self.node_id = pixel_id
        self.color = color
        self.row = row
        self.col = col

    def to_json(self) -> dict:
        """
        PIXEL properties: color + coordinate(row_index, col_index).
        REF: ARC-solver/ARCKG/pixel.py  update_property → property['coordinate']
        """
        return {
            "color": self.color,
            "coordinate": {
                "row_index": self.row,
                "col_index": self.col,
            },
        }

    def save(self, semantic_memory_root: str):
        """Write to_json() as E_X{x}.json in the node folder."""
        folder = node_id_to_folder_path(self.node_id, semantic_memory_root)
        os.makedirs(folder, exist_ok=True)
        path = id_to_json_path(self.node_id, semantic_memory_root)
        with open(path, "w") as f:
            json.dump({"id": self.node_id, "result": self.to_json()}, f, indent=2)

    def __repr__(self) -> str:
        return (f"Pixel(id={self.node_id}, color={self.color}, "
                f"pos=({self.row},{self.col}))")
