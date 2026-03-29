
---
## Learning Loop -- 2026-03-30 02:58

- Split: training, Tasks: 20
- Correct: 4 / 20 (20.0%)
- Rules: 0 -> 4 (+4 learned)
- Stored rule hits: 0
- Time: 45s
- Log: logs/learn_20260330_025727.log

---
## Session 12 (Claude) -- 2026-03-30 03:05

### Changes
- Added `staircase_grow` primitive to `_primitives.py` — grows a 1-row colored prefix into W/2 rows, each adding one more cell
- Added `fill_rects_by_size` primitive to `_primitives.py` — finds bordered rectangles and fills interiors with color = start_color + interior_side - 1
- Created `procedural_memory/concepts/staircase_grow.json` (solves bbc9ae5d)
- Created `procedural_memory/concepts/fill_rects_by_size.json` (solves c0f76784)

### Results
- Split: training, Tasks: 20
- Correct: 6 / 20 (30.0%) — up from 4/20 (20.0%)
- Rules: 4 -> 6 (+2 learned)
- Stored rule hits: 4
- Time: 35s
- Log: logs/learn_20260330_030431.log

---
## Learning Loop -- 2026-03-30 03:06

- Split: training, Tasks: 20
- Correct: 6 / 20 (30.0%)
- Rules: 6 -> 6 (+0 learned)
- Stored rule hits: 6
- Time: 35s
- Log: logs/learn_20260330_030546.log

---
## Session 2 (Claude) -- 2026-03-30 03:09

### Changes
- Added `recolor_components_by_size_group` primitive to `_primitives.py` — groups connected components by size, assigns same color to all components of equal size (ranked by group)
- Added `fill_quadrants_from_corners` primitive to `_primitives.py` — finds rectangles of marker color, locates 4 diagonal corner pixels, fills each quadrant with corresponding corner color
- Created `procedural_memory/concepts/recolor_by_size_group.json` (solves 6e82a1ae)
- Created `procedural_memory/concepts/fill_quadrants_from_corners.json` (solves e9ac8c9e)

### Results
- Split: training, Tasks: 20
- Correct: 8 / 20 (40.0%) — up from 6/20 (30.0%)
- Rules: 6 -> 8 (+2 learned)
- Stored rule hits: 6
- Time: 35s
- Log: logs/learn_20260330_030944.log

---
## Learning Loop -- 2026-03-30 03:11

- Split: training, Tasks: 20
- Correct: 8 / 20 (40.0%)
- Rules: 8 -> 8 (+0 learned)
- Stored rule hits: 8
- Time: 35s
- Log: logs/learn_20260330_031042.log

---
## Session 3 (Claude) -- 2026-03-30 03:36

### Changes
- Added `draw_turn_path` primitive to `_primitives.py` — draws L-shaped path from start pixel, turning CW at one waypoint color and CCW at another, continuing to grid boundary
- Added `gravity_rigid_body` primitive to `_primitives.py` — auto-detects wall (bottom row color) and content, drops connected components as rigid bodies with 1-row gap above walls
- Added `path_start_color` inference method to `_concept_engine.py` — finds the non-bg color at the leftmost column across all pairs
- Added `content_color_that_moves` inference method to `_concept_engine.py` — finds the non-bg color whose positions change between input and output
- Created `procedural_memory/concepts/waypoint_turn_path.json` (solves e5790162)
- Created `procedural_memory/concepts/gravity_to_wall.json` (solves 825aa9e9)

### Results
- Split: training, Tasks: 20
- Correct: 10 / 20 (50.0%) — up from 8/20 (40.0%)
- Rules: 8 -> 10 (+2 learned)
- Stored rule hits: 8
- Time: 39s
- Log: logs/learn_20260330_033540.log

---
## Learning Loop -- 2026-03-30 03:37

- Split: training, Tasks: 20
- Correct: 10 / 20 (50.0%)
- Rules: 10 -> 10 (+0 learned)
- Stored rule hits: 10
- Time: 35s
- Log: logs/learn_20260330_033703.log

---
## Session 4 (Claude) -- 2026-03-30 03:49

### Changes
- Added `fill_between_separators` primitive to `_primitives.py` — finds vertical column (axis) and horizontal separator rows, fills each row with nearest separator color, equidistant rows between different-colored separators become intersection color
- Added `mirror_displacement_across_separator` primitive to `_primitives.py` — finds horizontal separator, follows chains of arrow-color pixels from data-color pixels to compute displacement, mirrors displacement across separator for partner pixels
- Created `procedural_memory/concepts/fill_between_separators.json` (solves 332202d5)
- Created `procedural_memory/concepts/mirror_displacement.json` (solves c9680e90)

### Results
- Split: training, Tasks: 20
- Correct: 12 / 20 (60.0%) — up from 10/20 (50.0%)
- Rules: 10 -> 12 (+2 learned)
- Stored rule hits: 10
- Time: 35s
- Log: logs/learn_20260330_034927.log

---
## Learning Loop -- 2026-03-30 03:51

- Split: training, Tasks: 20
- Correct: 12 / 20 (60.0%)
- Rules: 12 -> 12 (+0 learned)
- Stored rule hits: 12
- Time: 35s
- Log: logs/learn_20260330_035044.log

---
## Session 5 (Claude) -- 2026-03-30 04:04

### Changes
- Added `connect_aligned_diamonds` primitive to `_primitives.py` — finds diamond/cross shapes (4-cell cross pattern around bg center), connects those sharing same row or column center with horizontal/vertical lines
- Added `summarize_box_grid` primitive to `_primitives.py` — parses 30×30 grid of 3×3 bordered boxes into 7×7 box matrix, identifies 1-border edge and separator axis, counts colored vs 8-boxes per row/column, outputs compact bar-chart
- Created `procedural_memory/concepts/connect_aligned_diamonds.json` (solves 60a26a3e)
- Created `procedural_memory/concepts/summarize_box_grid.json` (solves afe3afe9)

### Results
- Split: training, Tasks: 20
- Correct: 14 / 20 (70.0%) — up from 12/20 (60.0%)
- Rules: 12 -> 14 (+2 learned)
- Stored rule hits: 12
- Time: 36s
- Log: logs/learn_20260330_040423.log

---
## Learning Loop -- 2026-03-30 04:06

- Split: training, Tasks: 20
- Correct: 14 / 20 (70.0%)
- Rules: 14 -> 14 (+0 learned)
- Stored rule hits: 14
- Time: 35s
- Log: logs/learn_20260330_040539.log

---
## Session 6 (Claude) -- 2026-03-30 04:19

### Changes
- Added `swap_quadrant_shapes` primitive to `_primitives.py` — finds grid divided by separator rows/cols into quadrant pairs, swaps shapes between horizontal neighbors, recoloring each with the source quadrant's background color
- Added `project_cross_to_border` primitive to `_primitives.py` — finds asymmetric cross shapes with unique center pixel, projects center color to the opposite border with a dotted trail (every 2 cells), zeroes corners where two borders meet
- Created `procedural_memory/concepts/swap_quadrant_shapes.json` (solves 5a719d11)
- Created `procedural_memory/concepts/project_cross_to_border.json` (solves 13f06aa5)

### Results
- Split: training, Tasks: 20
- Correct: 16 / 20 (80.0%) — up from 14/20 (70.0%)
- Rules: 14 -> 16 (+2 learned)
- Stored rule hits: 14
- Time: 35s
- Log: logs/learn_20260330_041943.log

---
## Learning Loop -- 2026-03-30 04:20

- Split: training, Tasks: 20
- Correct: 16 / 20 (80.0%)
- Rules: 14 -> 16 (+2 learned)
- Stored rule hits: 14
- Time: 35s
- Log: logs/learn_20260330_041943.log

---
## Learning Loop -- 2026-03-30 04:21

- Split: training, Tasks: 20
- Correct: 16 / 20 (80.0%)
- Rules: 16 -> 16 (+0 learned)
- Stored rule hits: 16
- Time: 35s
- Log: logs/learn_20260330_042104.log

---
## Session 7 (Claude) -- 2026-03-30 04:37

### Changes
- Added `zigzag_shear_grid` primitive to `_primitives.py` — finds colored rectangle/grid on background, applies zigzag horizontal shear with pattern [0,-1,0,+1] indexed by distance from bottom row (mod 4)
- Added `slide_connector_through` primitive to `_primitives.py` — finds three single-color shapes in a line, slides the smallest (connector) through one neighbor (toward farther or larger-perp-extent neighbor), splitting it ±1 perpendicular, connector exits past target clamped to grid boundary
- Created `procedural_memory/concepts/zigzag_shear_grid.json` (solves 1c56ad9f)
- Created `procedural_memory/concepts/slide_connector_through.json` (solves 9f669b64)

### Results
- Split: training, Tasks: 20
- Correct: 18 / 20 (90.0%) — up from 16/20 (80.0%)
- Rules: 16 -> 18 (+2 learned)
- Stored rule hits: 16
- Time: 35s
- Log: logs/learn_20260330_043722.log
