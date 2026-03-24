"""
PAIR node — a single example pair (input grid + output grid) under a TASK.
Node ID format: T{hex}.P{p}  (test pairs use Pa, Pb, ...)
"""

import json
import os

from ARCKG.memory_paths import id_to_json_path, node_id_to_folder_path


class Pair:
    """
    INTENT: A KG node holding a pair of input_grid and output_grid.
            May hold pair-specific observations (relation result cache, etc.).
            Writes the E_P{p}.json property file via to_json().
    MUST NOT: Do not store task-level generalizations here (that is the TASK layer's responsibility).
              Do not directly hold raw pixel coordinates other than input/output.
    REF: ARC-solver/ARCKG/pair.py PAIR (line 12)
    """

    def __init__(self, pair_id: str, input_grid, output_grid=None):
        """
        INTENT: Initialize with pair_id, input_grid (Grid), and output_grid (Grid|None).
                For test pairs, output_grid is None.
        MUST NOT: Do not perform file I/O in the constructor.
        REF: ARC-solver/ARCKG/pair.py PAIR.__init__ (line 13)
        """
        self.node_id = pair_id
        self.input_grid = input_grid
        self.output_grid = output_grid
        # pair-level program loaded after program generation
        self.program: list = []

    def to_json(self) -> dict:
        """
        PAIR property: a single grid_count.
        REF: CLAUDE.md § Edge Creation Timing
        """
        return {
            "grid_count": 2 if self.output_grid is not None else 1,
        }

    def save(self, semantic_memory_root: str):
        """
        INTENT: Write to_json() as E_P{p}.json in the corresponding PAIR node folder.
                Storage location is under the parent TASK folder according to LCA rules.
        MUST NOT: Do not call inside a solve loop.
        REF: ARCKG/memory_paths.py
        """
        folder = node_id_to_folder_path(self.node_id, semantic_memory_root)
        os.makedirs(folder, exist_ok=True)
        path = id_to_json_path(self.node_id, semantic_memory_root)
        with open(path, "w") as f:
            json.dump({"id": self.node_id, "result": self.to_json()}, f, indent=2)

        if self.input_grid is not None:
            self.input_grid.save(semantic_memory_root)
        if self.output_grid is not None:
            self.output_grid.save(semantic_memory_root)

    def __repr__(self) -> str:
        out = self.output_grid is not None
        return f"Pair(id={self.node_id}, has_output={out})"
