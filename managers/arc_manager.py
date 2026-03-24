"""
ARCManager — Load ARC tasks from the data/ folder and build the ARCKG node hierarchy.
"""

import json
import os

from ARCKG.task import Task
from ARCKG.pair import Pair
from ARCKG.grid import Grid


class ARCManager:
    """
    INTENT: Read ARC JSON files from the specified data/ path,
            construct the Task → Pair → Grid → Object → Pixel node hierarchy,
            and call each node's to_json()/save() to record attributes in semantic_memory.
    MUST NOT: Do not modify data/ files (read-only).
              Do not include solve logic here.
    REF: ARCKG/task.py, ARCKG/pair.py, ARCKG/grid.py
         CLAUDE.md § Data, § Edge Creation Timing
    """

    def __init__(self, data_root: str = "data",
                 semantic_memory_root: str = "semantic_memory"):
        """
        INTENT: Initialize with data path and semantic_memory path.
        MUST NOT: Do not read files in the constructor.
        REF: ARC-solver/managers/arc_manager.py ARCManager._build_task_mapping (line 6)
        """
        self.data_root = data_root
        self.semantic_memory_root = semantic_memory_root

    def get_task_hex(self, task_file: str) -> str:
        """
        INTENT: Extract and return the hex ID from the task filename.
                Pure filename with extension (.json) and path prefix removed.
        MUST NOT: Do not open the file — filename parsing only.
        REF: CLAUDE.md § Node ID format
        """
        basename = os.path.basename(task_file)
        return basename.replace(".json", "")

    def load_task(self, task_file: str) -> Task:
        """
        INTENT: Read data_root/{task_file}.json to create a Task node,
                construct all child Pair/Grid/Object/Pixel nodes, and return the Task.
                Call save() on each node to write attribute files to semantic_memory.
        MUST NOT: Do not create comparison edges (E_*-*.json) here
                  — only attribute files (0th-order).
        REF: ARCKG/task.py Task, ARCKG/memory_paths.py
             CLAUDE.md § Edge Creation Timing
             ARC-solver/managers/arc_manager.py ARCManager.from_hex_code (line 40)
             ARC-solver/ARCKG/task.py TASK.from_json (line 59)
        """
        task_hex = self.get_task_hex(task_file)

        # Search multiple locations under data/
        candidates = [
            os.path.join(self.data_root, task_file),
            os.path.join(self.data_root, f"{task_file}.json"),
            os.path.join(self.data_root, "ARC_AGI", "training", f"{task_hex}.json"),
            os.path.join(self.data_root, "ARC_AGI", "evaluation", f"{task_hex}.json"),
            os.path.join(self.data_root, "ARC_easy", f"{task_hex}.json"),
            os.path.join(self.data_root, f"{task_hex}.json"),
        ]
        raw_data = None
        for path in candidates:
            if os.path.exists(path):
                with open(path, "r") as f:
                    raw_data = json.load(f)
                break
        if raw_data is None:
            raise FileNotFoundError(
                f"Task '{task_hex}' not found under '{self.data_root}'"
            )

        example_pairs = self._build_pairs(
            task_hex=task_hex,
            pairs_raw=raw_data["train"],
            pair_type="example",
            id_offset=0,
        )
        test_pairs = self._build_pairs(
            task_hex=task_hex,
            pairs_raw=raw_data["test"],
            pair_type="test",
            id_offset=0,
            test=True,
        )

        task = Task(
            task_hex=task_hex,
            example_pairs=example_pairs,
            test_pairs=test_pairs,
        )
        task.save(self.semantic_memory_root)
        return task

    def _build_pairs(self, task_hex: str, pairs_raw: list,
                     pair_type: str, id_offset: int,
                     test: bool = False) -> list[Pair]:
        """
        Construct Pair node list from ARC JSON train/test lists.
        - example pairs: pair_id = "T{hex}.P0", "T{hex}.P1", ...
        - test pairs:    pair_id = "T{hex}.Pa", "T{hex}.Pb", ...
        Calls extract_objects() on each Grid.
        """
        pairs = []
        for idx, raw_pair in enumerate(pairs_raw):
            if test:
                p_suffix = chr(ord("a") + idx)  # a, b, c, ...
            else:
                p_suffix = str(idx)             # 0, 1, 2, ...

            pair_id = f"T{task_hex}.P{p_suffix}"

            # Input grid (always present)
            input_id = f"{pair_id}.G0"
            input_grid = Grid(grid_id=input_id, raw=raw_pair["input"])
            input_grid.extract_objects()

            # Output grid (test pairs have no actual answer → construct if output exists, otherwise None)
            output_raw = raw_pair.get("output")
            if output_raw is not None and len(output_raw) > 0 and len(output_raw[0]) > 0:
                output_id = f"{pair_id}.G1"
                output_grid = Grid(grid_id=output_id, raw=output_raw)
                output_grid.extract_objects()
            else:
                output_grid = None

            pair = Pair(pair_id=pair_id, input_grid=input_grid, output_grid=output_grid)
            pairs.append(pair)
        return pairs

    def load_all_tasks(self, split: str = "training") -> list:
        """
        INTENT: Iterate over all task files under data_root/{split}/,
                call load_task() on each, and return the Task list.
        MUST NOT: Do not abort entirely on error — only log individual task failures.
        REF: ARC-solver/managers/arc_manager.py ARCManager._build_task_mapping (line 6)
             ARC-solver/basics/ARCLOADER.py ARCDataset.load_data (line 15)
        """
        # Search ARC_AGI sub-split folder first, fall back to data_root directly
        candidate_dirs = [
            os.path.join(self.data_root, "ARC_AGI", split),
            os.path.join(self.data_root, split),
            self.data_root,
        ]
        split_dir = None
        for d in candidate_dirs:
            if os.path.isdir(d):
                split_dir = d
                break
        if split_dir is None:
            raise FileNotFoundError(
                f"Split directory '{split}' not found under '{self.data_root}'"
            )

        json_files = sorted(
            f for f in os.listdir(split_dir) if f.endswith(".json")
        )

        tasks = []
        for filename in json_files:
            try:
                task = self.load_task(os.path.join(split_dir, filename))
                tasks.append(task)
            except Exception as e:
                print(f"[ARCManager] Warning: failed to load '{filename}': {e}")
        return tasks
