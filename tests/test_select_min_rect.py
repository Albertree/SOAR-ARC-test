"""Tests for the selected-object *rectangular* size-grid reading (iter 35).

Covers the new general capability: per-colour (univalued) segmentation
(`objects_by_color`) plus the SELECTOR_VOCAB × RECT_DIM_VOCAB composition in
`analyze_object_size_grid`, which lets the size_to_grid family name "the smallest
distinct-colour region's bbox extent, in its own colour" — the §2.5-2b
selection-lift on the non-square axis. Grounding task: real ARC-AGI-2 task
23b5c85d + data/ARC_madeup/madeup_select_min_rect.json.
"""
import json
import os
from types import SimpleNamespace as NS

from agent.dsl_expr.selection import (
    objects_of,
    objects_by_color,
    analyze_object_size_grid,
)

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _pairs(train):
    return [
        NS(input_grid=NS(raw=p["input"]), output_grid=NS(raw=p["output"]))
        for p in train
    ]


# --- per-colour segmentation separates nested regions ----------------------

def test_by_color_separates_nested_boxes():
    # A 4-colour-2 ring around a 2x2 colour-7 inner box: connectivity fuses them
    # into one multicoloured blob; per-colour segmentation keeps them apart.
    grid = [
        [0, 0, 0, 0, 0],
        [0, 2, 2, 2, 0],
        [0, 2, 7, 7, 0],
        [0, 2, 7, 7, 0],
        [0, 2, 2, 2, 0],
    ]
    connected = objects_of(grid)
    assert len(connected) == 1                      # fused
    assert connected[0]["color"] is None            # multicoloured blob

    by_color = objects_by_color(grid)
    colors = sorted(o["color"] for o in by_color)
    assert colors == [2, 7]                          # separated
    inner = min(by_color, key=lambda o: o["size"])
    assert inner["color"] == 7
    assert inner["size"] == 4


def test_by_color_matches_objects_of_when_no_nesting():
    # Two well-separated single-colour objects: both segmentations agree.
    grid = [
        [0, 0, 0, 0, 0, 0],
        [0, 3, 3, 0, 0, 0],
        [0, 3, 3, 0, 0, 0],
        [0, 0, 0, 0, 0, 0],
        [0, 0, 0, 0, 4, 0],
        [0, 0, 0, 0, 4, 0],
    ]
    a = sorted((o["color"], o["size"]) for o in objects_of(grid))
    b = sorted((o["color"], o["size"]) for o in objects_by_color(grid))
    assert a == b == [(3, 4), (4, 2)]


def test_by_color_foreground_majority_excludes_zero():
    # 0 present but a minority: background stays 0 (0-is-canvas), the two coloured
    # regions are separated per-colour, the 0-holes are not segmented as objects.
    grid = [
        [5, 5, 5, 5],
        [5, 8, 8, 5],
        [5, 0, 0, 5],
        [5, 5, 5, 5],
    ]
    by_color = objects_by_color(grid)
    colors = sorted(o["color"] for o in by_color)
    assert colors == [5, 8]


# --- analyzer learns selector × rect reading -------------------------------

def test_analyzer_learns_min_size_bbox_extent_by_color():
    task = json.load(
        open(os.path.join(ROOT, "data", "ARC_madeup",
                          "madeup_select_min_rect.json"), encoding="utf-8"))
    sz = analyze_object_size_grid(_pairs(task["train"]))
    assert sz["dim_property"] == "bbox_extent"
    assert sz["selector"] == "min_size"
    assert sz["segmentation"] == "by_color"
    assert sz["solid_output_all"] is True
    assert sz["color_preserved_all"] is True


def test_analyzer_learns_on_real_task_23b5c85d():
    path = os.path.join(ROOT, "data", "ARC_AGI", "training", "23b5c85d.json")
    task = json.load(open(path, encoding="utf-8"))
    sz = analyze_object_size_grid(_pairs(task["train"]))
    assert sz["dim_property"] == "bbox_extent"
    assert sz["selector"] == "min_size"
    assert sz["segmentation"] == "by_color"


# --- the new branch does not steal existing single-object rect tasks --------

def test_single_object_rect_unchanged_segmentation_connected():
    # One object, non-square bbox -> rect reading off the single object, the
    # *connected* path, no selector. The new selector branch must not fire.
    train = [
        {"input": [[0, 0, 0, 0],
                   [0, 3, 3, 3],
                   [0, 3, 3, 3]],
         "output": [[3, 3, 3], [3, 3, 3]]},
        {"input": [[4, 4],
                   [4, 4],
                   [4, 4],
                   [0, 0]],
         "output": [[4, 4], [4, 4], [4, 4]]},
    ]
    sz = analyze_object_size_grid(_pairs(train))
    assert sz["dim_property"] == "bbox_extent"
    assert sz["selector"] is None
    assert sz["segmentation"] == "connected"


def test_segmentation_field_defaults_connected_when_inert():
    # A move-style task (non-solid output): analyzer stays inert and reports the
    # default segmentation.
    train = [
        {"input": [[0, 1, 0], [0, 0, 0]],
         "output": [[0, 0, 0], [0, 1, 0]]},
    ]
    sz = analyze_object_size_grid(_pairs(train))
    assert sz["dim_property"] is None
    assert sz["segmentation"] == "connected"
