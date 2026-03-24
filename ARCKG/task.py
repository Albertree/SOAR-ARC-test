"""
TASK node — top-level layer of the knowledge graph.
Node ID format: T{hex}
"""

import json
import os

from ARCKG.memory_paths import id_to_json_path, node_id_to_folder_path


class Task:
    """
    INTENT: A KG node representing a single ARC task.
            Holds task_hex ID, example pairs, test pairs, and task-level properties.
            Writes the E_T{hex}.json property file to semantic_memory via to_json().
    MUST NOT: Do not store pair-specific observations here (that is the PAIR layer's responsibility).
              Do not put any solve logic here.
    REF: ARC-solver/ARCKG/task.py TASK (line 12)
    """

    def __init__(self, task_hex: str, example_pairs: list, test_pairs: list):
        """
        INTENT: Initialize the node with task_hex, example_pairs (list of Pair),
                and test_pairs (list of Pair).
        MUST NOT: Do not perform file I/O in the constructor.
        REF: ARC-solver/ARCKG/task.py TASK.__init__ (line 13)
        """
        self.task_hex = task_hex
        self.node_id = f"T{task_hex}"
        self.example_pairs = example_pairs
        self.test_pairs = test_pairs

    def to_json(self) -> dict:
        """
        INTENT: Return this node's 0th-order properties (E_T{hex}.json contents) as a dict.
                The returned result is written to semantic_memory.
        MUST NOT: Do not include comparison results. Properties only.
        REF: CLAUDE.md § Edge Creation Timing
        """
        return {
            "example_pair_count": len(self.example_pairs),
            "test_pair_count": len(self.test_pairs),
        }

    def save(self, semantic_memory_root: str):
        """
        INTENT: Write to_json() to semantic_memory_root/N_T{hex}/E_T{hex}.json.
                Recursively save all child Pair -> Grid -> Object nodes as well.
        MUST NOT: Do not call inside a solve loop (only at task load time).
        REF: ARCKG/memory_paths.py id_to_json_path()
        """
        folder = node_id_to_folder_path(self.node_id, semantic_memory_root)
        os.makedirs(folder, exist_ok=True)
        path = id_to_json_path(self.node_id, semantic_memory_root)
        with open(path, "w") as f:
            json.dump({"id": self.node_id, "result": self.to_json()}, f, indent=2)

        for pair in self.example_pairs:
            pair.save(semantic_memory_root)
        for pair in self.test_pairs:
            pair.save(semantic_memory_root)

    def __repr__(self) -> str:
        return (
            f"Task(hex={self.task_hex}, "
            f"examples={len(self.example_pairs)}, "
            f"tests={len(self.test_pairs)})"
        )
