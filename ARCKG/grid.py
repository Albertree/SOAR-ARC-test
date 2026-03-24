"""
GRID node — a single grid under a PAIR.
Node ID format: T{hex}.P{p}.G{g}  (G0=input, G1=output)
"""

import json
import os

from ARCKG.memory_paths import id_to_json_path, node_id_to_folder_path
from ARCKG.hodel import find_all_objects
from ARCKG.object import Object
from ARCKG.pixel import Pixel


class Grid:
    """
    INTENT: A KG node holding a 2D integer grid and the list of Objects extracted from it.
            Writes the E_G{g}.json property file via to_json().
    MUST NOT: Do not perform object-level relation inference here (that is the OBJECT layer's responsibility).
    REF: ARC-solver/ARCKG/grid.py GRID (line 14)
    """

    def __init__(self, grid_id: str, raw: list):
        self.node_id = grid_id
        self.raw = raw
        self.objects: list = []
        self.pixels: list = []   # grid-level Pixel nodes (based on absolute coordinates)

    @property
    def height(self) -> int:
        return len(self.raw)

    @property
    def width(self) -> int:
        return len(self.raw[0]) if self.raw else 0

    def extract_objects(self):
        """
        INTENT: Extract unique Objects using 8 parameter combinations of hodel objects()
                and store them in self.objects / self.pixels.
                Each object holds the method dict used for its detection.
        REF: ARC-solver/DSL/object_finder.py find_all_objects (line 62)
             ARCKG/hodel.py find_all_objects
        """
        if self.height == 0 or self.width == 0:
            self.objects = []
            self.pixels = []
            return

        self.objects = []
        self.pixels = []
        grid_pixel_seen: set = set()   # prevent duplicate (r,c) grid-level Pixels

        for obj_idx, data in enumerate(find_all_objects(self.raw)):
            object_id = f"{self.node_id}.O{obj_idx}"
            obj = Object(
                object_id=object_id,
                colorgrid=data["colorgrid"],
                pos=data["pos"],
                method=data["method"],
            )

            # Object-level Pixel: sorted by row-column order
            sorted_pixels = sorted(data["obj"], key=lambda x: (x[1][0], x[1][1]))
            for pix_idx, (color, (r, c)) in enumerate(sorted_pixels):
                obj_pixel_id = f"{object_id}.X{pix_idx}"
                obj.pixels.append(
                    Pixel(pixel_id=obj_pixel_id, color=color, row=r, col=c)
                )

                # Grid-level Pixel: row-major index, no duplicates
                grid_pixel_idx = r * self.width + c
                if grid_pixel_idx not in grid_pixel_seen:
                    grid_pixel_seen.add(grid_pixel_idx)
                    grid_pixel_id = f"{self.node_id}.X{grid_pixel_idx}"
                    self.pixels.append(
                        Pixel(pixel_id=grid_pixel_id, color=color,
                              row=r, col=c)
                    )

            self.objects.append(obj)

    def to_json(self) -> dict:
        """
        3 GRID properties:
          size     : {"height": int, "width": int}
          color    : {0: bool, …, 9: bool}
          contents : 2D int array
        REF: ARC-solver/ARCKG/grid.py GRID.update_property (line 209-222)
        """
        color_dict = {i: False for i in range(10)}
        for row in self.raw:
            for val in row:
                if 0 <= val <= 9:
                    color_dict[val] = True

        return {
            "size": {
                "height": self.height,
                "width": self.width,
            },
            "color": color_dict,
            "contents": self.raw,
        }

    def save(self, semantic_memory_root: str):
        """Write E_G{g}.json then recursively save all child Objects / Pixels."""
        folder = node_id_to_folder_path(self.node_id, semantic_memory_root)
        os.makedirs(folder, exist_ok=True)
        path = id_to_json_path(self.node_id, semantic_memory_root)
        with open(path, "w") as f:
            json.dump({"id": self.node_id, "result": self.to_json()}, f, indent=2)

        for obj in self.objects:
            obj.save(semantic_memory_root)

        for pixel in self.pixels:
            pixel.save(semantic_memory_root)

    def __repr__(self) -> str:
        return (f"Grid(id={self.node_id}, "
                f"size={self.height}×{self.width}, "
                f"objects={len(self.objects)})")
