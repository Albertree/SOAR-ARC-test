"""Tests for the 0-aware background convention + the count-bar dimension reading.

Two coupled changes, both under `agent/dsl_expr/selection.py` (F3-exempt argument
vocabulary / object-analysis correctness, no transformation primitive added):

1. `background_of` honours ARC's 0-is-canvas convention: when 0 is present it is
   the background regardless of frequency. The old plain most-frequent heuristic
   flipped foreground/background whenever a coloured shape outnumbered the 0-canvas
   (318/1000 ARC-AGI-2 training tasks have >=1 such grid), silently mis-segmenting
   the 0-holes as the object. `objects_of` now excludes *that* background.

2. `count_bar_h`/`count_bar_v` — a `RECT_DIM_VOCAB` reading that lays an object's
   cell count out as a ``1 x size`` (resp. ``size x 1``) strip, the §2.1 "grid size
   = f(object property)" concept for the line layout (real task d631b094). Folds
   into the existing `size_to_grid` family (rule_001), no new rule/matcher.
"""

from types import SimpleNamespace

from agent.dsl_expr.selection import (
    background_of,
    most_frequent_color,
    least_frequent_color,
    objects_of,
    count_bar_h_of,
    count_bar_v_of,
    bbox_extent_of,
    size_of,
    color_of,
    RECT_DIM_VOCAB,
    analyze_object_size_grid,
)
from agent.dsl_expr.render import render_solid_rect


class _G:
    def __init__(self, raw):
        self.raw = raw


def _pairs(triples):
    return [SimpleNamespace(input_grid=_G(i), output_grid=_G(o)) for i, o in triples]


# --- 1. background convention ------------------------------------------------

def test_background_honours_zero_when_present_even_if_minority():
    # color 4 outnumbers 0 (5 vs 4) but 0 is the canvas by convention.
    g = [[4, 4, 0], [4, 0, 4], [0, 0, 4]]
    assert background_of(g) == 0


def test_background_falls_back_to_most_frequent_when_no_zero():
    # no 0 at all -> genuine non-zero canvas, most-frequent wins (ties -> smallest).
    g = [[3, 3, 5], [3, 5, 3], [3, 3, 3]]
    assert background_of(g) == 3


def test_background_zero_majority_unchanged():
    g = [[0, 0, 0], [0, 3, 0], [0, 0, 0]]
    assert background_of(g) == 0


# --- 2. most_frequent_color decoupled from background_of ---------------------

def test_most_frequent_color_is_true_most_frequent_even_when_zero():
    # 0 is the most-common colour: as a fill *argument* the dominant colour is 0,
    # unlike background_of which would also say 0 here (they agree), but the point
    # is most_frequent_color is computed independently and stays true-frequency.
    g = [[0, 0, 0], [0, 3, 0], [0, 0, 0]]
    assert most_frequent_color(g) == 0


def test_most_frequent_color_returns_nonzero_majority():
    # foreground-majority grid: the dominant colour is 4, and most_frequent_color
    # must report 4 (NOT 0) — this is where it diverges from background_of.
    g = [[4, 4, 0], [4, 0, 4], [0, 0, 4]]
    assert most_frequent_color(g) == 4
    assert background_of(g) == 0
    assert least_frequent_color(g) == 0


# --- 3. objects_of segments the foreground, not the 0-holes -----------------

def test_objects_of_foreground_majority_not_flipped():
    # 5 cells of colour 4 (majority) on a 0-canvas: the object is the colour-4
    # shape (size 5), NOT the four 0-holes.
    g = [[4, 4, 0], [4, 0, 4], [0, 0, 4]]
    objs = objects_of(g)
    assert len(objs) == 1
    assert objs[0]["color"] == 4
    assert objs[0]["size"] == 5


def test_objects_of_zero_majority_unchanged():
    # ordinary case (0 is majority): behaviour identical to the hodel port.
    g = [[0, 0, 0], [0, 3, 3], [0, 0, 0]]
    objs = objects_of(g)
    assert len(objs) == 1
    assert objs[0]["color"] == 3
    assert objs[0]["size"] == 2


# --- 4. count-bar readings ---------------------------------------------------

def test_count_bar_readings():
    obj = {"size": 4}
    assert count_bar_h_of(obj) == (1, 4)
    assert count_bar_v_of(obj) == (4, 1)


def test_rect_vocab_priority_bbox_before_count_bar():
    # bbox_extent is tried first so an object whose output really is its bbox is
    # not stolen by the count-bar reading.
    names = list(RECT_DIM_VOCAB)
    assert names[0] == "bbox_extent"
    assert "count_bar_h" in RECT_DIM_VOCAB and "count_bar_v" in RECT_DIM_VOCAB


# --- 5. analyzer learns count_bar_h on a strip task -------------------------

def _strip(n, c):
    return [[c] * n]


def _grid(h, w, cells, c):
    g = [[0] * w for _ in range(h)]
    for (r, cc) in cells:
        g[r][cc] = c
    return g


def test_analyzer_learns_count_bar_h():
    # connected diagonal blobs whose bbox != 1xN, output = 1 x size strip.
    triples = [
        (_grid(5, 5, [(0, 0), (1, 1), (2, 2), (3, 3)], 3), _strip(4, 3)),
        (_grid(3, 3, [(0, 0), (0, 1), (1, 0), (1, 2), (2, 2)], 6), _strip(5, 6)),
        (_grid(4, 4, [(0, 0), (1, 1), (2, 2)], 8), _strip(3, 8)),
    ]
    r = analyze_object_size_grid(_pairs(triples))
    assert r["dim_property"] == "count_bar_h"
    assert r["color_preserved_all"] is True


def test_count_bar_render_roundtrip_foreground_majority():
    # the d631b094 test case: 6 cells of colour 7 (majority) -> 1x6 strip of 7.
    g = _grid(3, 3, [(0, 0), (0, 1), (0, 2), (1, 1), (2, 0), (2, 2)], 7)
    obj = objects_of(g)[0]
    h, w = count_bar_h_of(obj)
    assert (h, w) == (1, 6)
    assert render_solid_rect(h, w, color_of(obj)) == [[7, 7, 7, 7, 7, 7]]
