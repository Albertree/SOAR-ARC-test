
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

---
## Learning Loop -- 2026-03-30 04:39

- Split: training, Tasks: 20
- Correct: 18 / 20 (90.0%)
- Rules: 18 -> 18 (+0 learned)
- Stored rule hits: 18
- Time: 35s
- Log: logs/learn_20260330_043830.log

---
## Session 8 (Claude) -- 2026-03-30 05:02

### Changes
- Added `scatter_count_x_diamond` primitive to `_primitives.py` — counts scattered pixels by color (two non-bg colors), uses counts as W×H rectangle dimensions, draws X/hourglass diagonal pattern of diag_color on fill_color in bottom-left corner of output_side×output_side grid
- Added `relocate_cross_template` primitive to `_primitives.py` — finds cross-shaped templates (connector color + marker dots), finds isolated marker anchor dots, matches templates to anchors via 8 rotation/reflection transforms, redraws transformed connectors at anchor positions
- Added `max_dim_even` inference method to `_concept_engine.py` — infers output grid side from output dimensions across training pairs
- Created `procedural_memory/concepts/scatter_count_x_diamond.json` (solves 878187ab)
- Created `procedural_memory/concepts/relocate_cross_template.json` (solves 0e206a2e)

### Results
- Split: training, Tasks: 20
- Correct: 20 / 20 (100.0%) — up from 18/20 (90.0%)
- Rules: 18 -> 20 (+2 learned)
- Stored rule hits: 18
- Time: 35s
- Log: logs/learn_20260330_050215.log

---
## Learning Loop -- 2026-03-30 05:03

- Split: training, Tasks: 20
- Correct: 20 / 20 (100.0%)
- Rules: 20 -> 20 (+0 learned)
- Stored rule hits: 20
- Time: 35s
- Log: logs/learn_20260330_050320.log

---
## Learning Loop -- 2026-03-30 05:05

- Split: training, Tasks: 40
- Correct: 20 / 40 (50.0%)
- Rules: 20 -> 20 (+0 learned)
- Stored rule hits: 20
- Time: 83s
- Log: logs/learn_20260330_050411.log

---
## Session 9 (Claude) -- 2026-03-30 05:12

### Changes
- Created `procedural_memory/concepts/rotation_quad_tile.json` (solves ed98d772) — tiles input in 2x2 layout with rotations [0°, 270°, 180°, 90°] CW using only existing primitives (rotate_cw, concat_horizontal, concat_vertical)
- Added `invert_bordered_rect` primitive to `_primitives.py` — finds bordered rectangle on bg, crops it, swaps border and fill colors
- Created `procedural_memory/concepts/invert_bordered_rect.json` (solves b94a9452)
- Added `tile_content_upward` primitive to `_primitives.py` — detects content rows at bottom of grid, tiles them upward (bottom-aligned) to fill entire grid
- Created `procedural_memory/concepts/tile_content_upward.json` (solves 9b30e358)

### Results
- Split: training, Tasks: 40
- Correct: 23 / 40 (57.5%) — up from 20/40 (50.0%)
- Rules: 20 -> 23 (+3 learned)
- Stored rule hits: 20
- Time: 73s
- Log: logs/learn_20260330_051054.log

---
## Learning Loop -- 2026-03-30 05:13

- Split: training, Tasks: 40
- Correct: 23 / 40 (57.5%)
- Rules: 23 -> 23 (+0 learned)
- Stored rule hits: 23
- Time: 73s
- Log: logs/learn_20260330_051232.log

---
## Session 10 (Claude) -- 2026-03-30 05:35

### Changes
- Added `reflect_2x2_corners` primitive to `_primitives.py` — finds a 2×2 block of 4 distinct colors, fills each diagonal quadrant with the opposite corner's color (capped at 2×2 adjacent to block)
- Created `procedural_memory/concepts/reflect_2x2_corners.json` (solves 93b581b8)
- Added `extend_diagonal_arms` primitive to `_primitives.py` — finds a 2×2 block with single-pixel diagonal arms, extends each arm's diagonal to the grid boundary
- Created `procedural_memory/concepts/extend_diagonal_arms.json` (solves 7ddcd7ec)
- Added `fill_framed_interior` primitive to `_primitives.py` — finds closed rectangular frames of color 2, fills interiors (bg cells) with color 1
- Created `procedural_memory/concepts/fill_framed_interior.json` (solves a5313dff)

### Results
- Split: training, Tasks: 40
- Correct: 26 / 40 (65.0%) — up from 23/40 (57.5%)
- Rules: 23 -> 26 (+3 learned)
- Stored rule hits: 23
- Time: 74s
- Log: logs/learn_20260330_053353.log

---
## Learning Loop -- 2026-03-30 05:35

- Split: training, Tasks: 40
- Correct: 26 / 40 (65.0%)
- Rules: 23 -> 26 (+3 learned)
- Stored rule hits: 23
- Time: 74s
- Log: logs/learn_20260330_053353.log

---
## Learning Loop -- 2026-03-30 05:37

- Split: training, Tasks: 40
- Correct: 26 / 40 (65.0%)
- Rules: 26 -> 26 (+0 learned)
- Stored rule hits: 26
- Time: 74s
- Log: logs/learn_20260330_053556.log

---
## Session 11 (Claude) -- 2026-03-30 05:54

### Changes
- Added `mirror_recolor_vertical` primitive to `_primitives.py` — for each cell with target_color, changes to replace_color if its vertical-axis mirror also has target_color
- Added `count_inside_rect_fill` primitive to `_primitives.py` — finds rectangle bordered by 1s, counts marker pixels inside, outputs 3x3 grid filled left-to-right top-to-bottom
- Added `remove_noise_keep_blocks` primitive to `_primitives.py` — removes colored pixels that lack both a horizontal and vertical same-color neighbor
- Created `procedural_memory/concepts/mirror_recolor_symmetric.json` (solves ce039d91)
- Created `procedural_memory/concepts/count_inside_rect.json` (solves c8b7cc0f)
- Created `procedural_memory/concepts/remove_noise_blocks.json` (solves 7f4411dc)

### Results
- Split: training, Tasks: 40
- Correct: 29 / 40 (72.5%) — up from 26/40 (65.0%)
- Rules: 26 -> 29 (+3 learned)
- Stored rule hits: 26
- Time: 74s
- Log: logs/learn_20260330_055404.log

---
## Learning Loop -- 2026-03-30 05:57

- Split: training, Tasks: 40
- Correct: 29 / 40 (72.5%)
- Rules: 29 -> 29 (+0 learned)
- Stored rule hits: 29
- Time: 75s
- Log: logs/learn_20260330_055546.log

---
## Session 12 (Claude) -- 2026-03-30 06:12

### Changes
- Added `extend_pixel_to_corner` primitive to `_primitives.py` — for each non-bg pixel, draws an L-shaped line toward the nearest grid corner (horizontal + vertical to nearest edge)
- Added `mark_domino_cross_centers` primitive to `_primitives.py` — finds 2-cell domino shapes, pairs perpendicular matched pairs with integer midpoint, places mark color at crossing center
- Added `rotation_quad_tile_2x2` primitive to `_primitives.py` — creates 4×4 tiling with rotation quadrants (TL=180°, TR=90°CW, BL=270°CW, BR=0°), each tiled 2×2
- Added `color_added_in_output` inference method to `_concept_engine.py` — finds the single color present in output but absent from input
- Created `procedural_memory/concepts/extend_pixel_to_corner.json` (solves 705a3229)
- Created `procedural_memory/concepts/mark_domino_cross.json` (solves 9f5f939b)
- Created `procedural_memory/concepts/rotation_quad_tile_2x2.json` (solves cf5fd0ad)

### Results
- Split: training, Tasks: 40
- Correct: 32 / 40 (80.0%) — up from 29/40 (72.5%)
- Rules: 29 -> 32 (+3 learned)
- Stored rule hits: 29
- Time: 76s
- Log: logs/learn_20260330_061249.log

---
## Learning Loop -- 2026-03-30 06:14

- Split: training, Tasks: 40
- Correct: 32 / 40 (80.0%)
- Rules: 29 -> 32 (+3 learned)
- Stored rule hits: 29
- Time: 76s
- Log: logs/learn_20260330_061249.log

---
## Learning Loop -- 2026-03-30 06:16

- Split: training, Tasks: 40
- Correct: 32 / 40 (80.0%)
- Rules: 32 -> 32 (+0 learned)
- Stored rule hits: 32
- Time: 74s
- Log: logs/learn_20260330_061507.log

---
## Session 13 (Claude) -- 2026-03-30 06:33

### Changes
- Added `compress_separator_intersections` primitive to `_primitives.py` — extracts colored pattern from grid separator-line intersections and compresses by collapsing identical adjacent rows/cols with gap insertion
- Added `recolor_framed_pattern_by_keys` primitive to `_primitives.py` — finds a bordered pattern block, discovers 2-cell color key pairs outside it, and applies color substitution to interior colors
- Created `procedural_memory/concepts/compress_separator_intersections.json` (solves 7837ac64)
- Created `procedural_memory/concepts/recolor_framed_by_keys.json` (solves e9b4f6fc)

### Results
- Before: 32 / 40 (80.0%)
- After:  34 / 40 (85.0%)  +2 tasks fixed
- Regression gate (08ed6ac7): CORRECT
- New rules discovered: 2

---
## Learning Loop -- 2026-03-30 06:34

- Split: training, Tasks: 40
- Correct: 34 / 40 (85.0%)
- Rules: 32 -> 34 (+2 learned)
- Stored rule hits: 32
- Time: 74s
- Log: logs/learn_20260330_063331.log

---
## Learning Loop -- 2026-03-30 06:37

- Split: training, Tasks: 40
- Correct: 34 / 40 (85.0%)
- Rules: 34 -> 34 (+0 learned)
- Stored rule hits: 34
- Time: 75s
- Log: logs/learn_20260330_063547.log

---
## Session 14 (Claude) -- 2026-03-30 06:50

### Changes
- Added `cross_pattern_vote` primitive to `_primitives.py` — finds cross patterns (center=4, 4 same-color cardinal arms), returns 1x1 grid with most frequent arm color
- Added `mark_square_corners` primitive to `_primitives.py` — finds connected components with square bounding boxes (>=2x2), places color 2 at two outward-extension cells per corner
- Added `bridge_markers_to_rects` primitive to `_primitives.py` — finds isolated single-pixel markers and same-color rectangles, draws cross at marker (center->bg), line toward nearest rect face, widens connection to 3 at rect face
- Created `procedural_memory/concepts/cross_pattern_vote.json` (solves 642d658d)
- Created `procedural_memory/concepts/mark_square_corners.json` (solves 14b8e18c)
- Created `procedural_memory/concepts/bridge_markers_to_rects.json` (solves a2d730bd)

### Results
- Before: 34 / 40 (85.0%)
- After:  37 / 40 (92.5%)  +3 tasks fixed
- Regression gate (08ed6ac7): CORRECT
- New rules discovered: 3

---
## Learning Loop -- 2026-03-30 06:48

- Split: training, Tasks: 40
- Correct: 37 / 40 (92.5%)
- Rules: 34 -> 37 (+3 learned)
- Stored rule hits: 34
- Time: 75s
- Log: logs/learn_20260330_064707.log

---
## Learning Loop -- 2026-03-30 06:50

- Split: training, Tasks: 40
- Correct: 37 / 40 (92.5%)
- Rules: 37 -> 37 (+0 learned)
- Stored rule hits: 37
- Time: 74s
- Log: logs/learn_20260330_064916.log

---
## Session 15 (Claude) -- 2026-03-30 07:09

### Changes
- Added `flood_fill_border_interior` primitive to `_primitives.py` — BFS from border cells of bg color, marks border-connected bg cells as exterior_color and enclosed bg cells as interior_color
- Added `invert_tiled_subgrids` primitive to `_primitives.py` — finds separator rows/cols (value 0, ignoring corruption value 5), divides grid into tiled sub-grids, identifies majority pattern template vs uniform tiles, inverts them (pattern→uniform, uniform→pattern), and repairs corrupted tiles
- Created `procedural_memory/concepts/flood_fill_border_interior.json` (solves 84db8fc4)
- Created `procedural_memory/concepts/invert_tiled_subgrids.json` (solves 6350f1f4)

### Results
- Split: training, Tasks: 40
- Correct: 39 / 40 (97.5%) — up from 37/40 (92.5%)
- Rules: 37 -> 39 (+2 learned)
- Stored rule hits: 37
- Time: 74s
- Log: logs/learn_20260330_070806.log
- Remaining failure: 5daaa586 (separator-bounded gravity with accumulation from all regions)

---
## Learning Loop -- 2026-03-30 07:11

- Split: training, Tasks: 40
- Correct: 39 / 40 (97.5%)
- Rules: 39 -> 39 (+0 learned)
- Stored rule hits: 39
- Time: 75s
- Log: logs/learn_20260330_071038.log

---
## Session 16 (Claude) -- 2026-03-30 07:22

### Changes
- Added `separator_gravity_bars` primitive to `_primitives.py` — finds 4 separator lines (2 horizontal, 2 vertical) defining a center rectangle; identifies scattered marker color matching one separator; fills bars from the matching wall to the farthest marker per column/row within center
- Created `procedural_memory/concepts/separator_gravity_bars.json` (solves 5daaa586)

### Results
- Split: training, Tasks: 40
- Correct: 40 / 40 (100.0%) — up from 39/40 (97.5%)
- Rules: 39 -> 40 (+1 learned)
- Stored rule hits: 39
- Time: 77s
- Log: logs/learn_20260330_072140.log
- Regression gate (08ed6ac7): CORRECT

---
## Learning Loop -- 2026-03-30 07:24

- Split: training, Tasks: 40
- Correct: 40 / 40 (100.0%)
- Rules: 40 -> 40 (+0 learned)
- Stored rule hits: 40
- Time: 75s
- Log: logs/learn_20260330_072325.log

---
## Learning Loop -- 2026-03-30 07:27

- Split: training, Tasks: 80
- Correct: 41 / 80 (51.2%)
- Rules: 40 -> 41 (+1 learned)
- Stored rule hits: 40
- Time: 155s
- Log: logs/learn_20260330_072505.log

---
## Session 17 (Claude) -- 2026-03-30 07:34

### Changes
- Added `checkerboard` primitive to `_primitives.py` — generates grid-line pattern (0 only where both r and c are odd, else 1)
- Added `kronecker_self` primitive to `_primitives.py` — Kronecker product of grid with itself (non-zero cells → copy of grid, zero cells → zero block)
- Created `procedural_memory/concepts/mirror_four_way.json` (solves 62c24649, 67e8384a) — tiles input in 2x2 with horizontal and vertical mirror symmetry using existing flip/concat primitives
- Created `procedural_memory/concepts/checkerboard_fill.json` (solves 332efdb3) — fills all-zero grid with grid-line pattern
- Created `procedural_memory/concepts/kronecker_self_tile.json` (solves 007bbfb7) — Kronecker self-tiling where each non-zero cell becomes a copy of the entire grid

### Results
- Before: 41 / 80 (51.2%)
- After:  45 / 80 (56.2%)  +4 tasks fixed
- Regression gate (08ed6ac7): CORRECT
- New rules discovered: 3 (mirror_four_way, checkerboard_fill, kronecker_self_tile)
- Note: Expanded from 40-task set (100%) to 80-task set for new challenges

---
## Learning Loop -- 2026-03-30 07:34

- Split: training, Tasks: 80
- Correct: 45 / 80 (56.2%)
- Rules: 41 -> 44 (+3 learned)
- Stored rule hits: 42
- Time: 137s
- Log: logs/learn_20260330_073158.log

---
## Learning Loop -- 2026-03-30 07:37

- Split: training, Tasks: 80
- Correct: 45 / 80 (56.2%)
- Rules: 44 -> 44 (+0 learned)
- Stored rule hits: 45
- Time: 142s
- Log: logs/learn_20260330_073451.log

---
## Session 18 (Claude) -- 2026-03-30 08:31

### Changes
- Added `invert_binary` primitive to `_primitives.py` — swaps 0 and the single non-zero color in a binary grid
- Added `reverse_concentric_rings` primitive to `_primitives.py` — detects concentric rectangular color rings, extracts unique color sequence, rotates right by 1, applies as color mapping
- Added `fill_active_columns` primitive to `_primitives.py` — replaces 0s with fill_color in columns that contain any non-zero pixel
- Created `procedural_memory/concepts/invert_tile_2x2.json` (solves 48131b3c) — inverts binary grid then tiles 2x2
- Created `procedural_memory/concepts/reverse_concentric_rings.json` (solves bda2d7a6) — rotates concentric ring colors inward by one step
- Created `procedural_memory/concepts/fill_columns_tile_2x2.json` (solves f5b8619d) — fills active columns with 8, tiles 2x2
- Fixed infinite loop bug in `reverse_concentric_rings` when grid is not a concentric ring pattern (thickness=0 guard)

### Results
- Before: 45 / 80 (56.2%)
- After:  48 / 80 (60.0%)  +3 tasks fixed
- Regression gate (08ed6ac7): CORRECT
- New rules discovered: 2 (reverse_concentric_rings, fill_columns_tile_2x2) + 1 memory hit (invert_tile_2x2)

---
## Learning Loop -- 2026-03-30 08:33

- Split: training, Tasks: 80
- Correct: 48 / 80 (60.0%)
- Rules: 45 -> 47 (+2 learned)
- Stored rule hits: 46
- Time: 149s
- Log: logs/learn_20260330_083110.log

---
## Learning Loop -- 2026-03-30 08:36

- Split: training, Tasks: 80
- Correct: 48 / 80 (60.0%)
- Rules: 47 -> 47 (+0 learned)
- Stored rule hits: 48
- Time: 137s
- Log: logs/learn_20260330_083428.log

---
## Learning Loop -- 2026-03-30 08:43

- Split: training, Tasks: 80
- Correct: 51 / 80 (63.7%)
- Rules: 47 -> 50 (+3 learned)
- Stored rule hits: 48
- Time: 137s
- Log: logs/learn_20260330_084108.log

---
## Session 19 (Claude) -- 2026-03-30 08:41

### Changes
- Added `fill_bbox_holes` primitive to `_primitives.py` — finds bounding box of non-bg pixels, fills bg cells inside it with a specified fill color
- Added `xor_halves` primitive to `_primitives.py` — splits grid at separator row, XORs two binary halves (result_color where exactly one is non-zero)
- Added `sort_pixels_snake` primitive to `_primitives.py` — extracts non-bg pixels, sorts by column, fills into compact grid in boustrophedon (snake) order
- Created `procedural_memory/concepts/fill_bbox_holes.json` (solves 6d75e8bb) — fill holes within shape's bounding box
- Created `procedural_memory/concepts/xor_halves.json` (solves 99b1bc43) — XOR of two binary grid halves
- Created `procedural_memory/concepts/sort_pixels_snake.json` (solves cdecee7f) — spatial binning of scattered pixels into compact grid

### Results
- Before: 48 / 80 (60.0%)
- After:  51 / 80 (63.7%)  +3 tasks fixed
- Regression gate (08ed6ac7): CORRECT
- New rules discovered: 3 (fill_bbox_holes, xor_halves, sort_pixels_snake)

---
## Learning Loop -- 2026-03-30 08:46

- Split: training, Tasks: 80
- Correct: 51 / 80 (63.7%)
- Rules: 50 -> 50 (+0 learned)
- Stored rule hits: 51
- Time: 137s
- Log: logs/learn_20260330_084403.log

---
## Session 20 (Claude) -- 2026-03-30 08:53

### Changes
- Added `fill_max_section` primitive to `_primitives.py` — finds grid sections divided by separator lines, counts colored dots per section, fills section(s) with max count solid, clears others
- Added `largest_blob_color` primitive to `_primitives.py` — finds largest dense single-color connected component (fill ratio >= 0.5) in noisy grid, outputs 3x3 of that color
- Added `repeat_colors_growing_gaps` primitive to `_primitives.py` — extracts seed colors from middle row, repeats them with progressively increasing gaps (each gap +1 from previous)
- Added `separator_color` inference method to `_concept_engine.py` — finds the color that forms full-width rows and/or full-height columns
- Created `procedural_memory/concepts/fill_max_section.json` (solves 29623171)
- Created `procedural_memory/concepts/largest_blob_color.json` (solves 3194b014)
- Created `procedural_memory/concepts/repeat_colors_growing_gaps.json` (solves 72207abc)

### Results
- Before: 51 / 80 (63.7%)
- After:  54 / 80 (67.5%)  +3 tasks fixed
- Regression gate (08ed6ac7): CORRECT
- New rules discovered: 3 (fill_max_section, largest_blob_color, repeat_colors_growing_gaps)

---
## Learning Loop -- 2026-03-30 08:55

- Split: training, Tasks: 80
- Correct: 54 / 80 (67.5%)
- Rules: 50 -> 53 (+3 learned)
- Stored rule hits: 51
- Time: 137s
- Log: logs/learn_20260330_085340.log

---
## Learning Loop -- 2026-03-30 08:59

- Split: training, Tasks: 80
- Correct: 54 / 80 (67.5%)
- Rules: 53 -> 53 (+0 learned)
- Stored rule hits: 54
- Time: 138s
- Log: logs/learn_20260330_085654.log

---
## Learning Loop -- 2026-03-30 09:12

- Split: training, Tasks: 80
- Correct: 57 / 80 (71.2%)
- Rules: 53 -> 56 (+3 learned)
- Stored rule hits: 54
- Time: 137s
- Log: logs/learn_20260330_091039.log

---
## Session 21 (Claude) -- 2026-03-30 09:10

### Changes
- Added `pyramid_from_seed` primitive to `_primitives.py` — finds a horizontal row of 2s at left edge, grows color-3 staircase upward (+1 cell/row) and color-1 staircase downward (-1 cell/row)
- Added `connect_pairs_with_lines` primitive to `_primitives.py` — finds pairs of same-color pixels, connects each with horizontal or vertical line; vertical lines overwrite horizontal at intersections
- Added `nor_halves` primitive to `_primitives.py` — splits grid vertically into two halves, outputs 4 where both halves are 0 (NOR of binary patterns)
- Created `procedural_memory/concepts/pyramid_from_seed.json` (solves a65b410d)
- Created `procedural_memory/concepts/connect_pairs_with_lines.json` (solves 070dd51e)
- Created `procedural_memory/concepts/nor_halves.json` (solves e345f17b)

### Results
- Before: 54 / 80 (67.5%)
- After:  57 / 80 (71.2%)  +3 tasks fixed
- Regression gate (08ed6ac7): CORRECT
- New rules discovered: 3 (pyramid_from_seed, connect_pairs_with_lines, nor_halves)

---
## Learning Loop -- 2026-03-30 09:15

- Split: training, Tasks: 80
- Correct: 57 / 80 (71.2%)
- Rules: 56 -> 56 (+0 learned)
- Stored rule hits: 57
- Time: 138s
- Log: logs/learn_20260330_091340.log

---
## Session 22 (Claude) -- 2026-03-30 09:27

### Changes
- Added `or_halves` primitive to `_primitives.py` — splits grid at separator row (closest to center), ORs two binary halves into result color (where EITHER half has non-zero → result_color)
- Added `crosshatch_from_rect` primitive to `_primitives.py` — finds a large rectangle of one majority color with scattered minority cells in a noisy grid (using prefix-sum rectangle search), extracts it, extends minority cells into full rows/columns to form crosshatch
- Added `fill_interior_from_seed` primitive to `_primitives.py` — finds a bordered rectangle, locates seed color pattern inside, scales it to fill entire interior while preserving border
- Created `procedural_memory/concepts/or_halves.json` (solves 506d28a5)
- Created `procedural_memory/concepts/crosshatch_from_rect.json` (solves 8731374e)
- Created `procedural_memory/concepts/fill_interior_from_seed.json` (solves e7a25a18)

### Results
- Split: training, Tasks: 80
- Correct: 60 / 80 (75.0%) — up from 57/80 (71.2%)
- Rules: 56 -> 59 (+3 learned)
- Stored rule hits: 57
- New rules discovered: 3 (or_halves, crosshatch_from_rect, fill_interior_from_seed)
- Time: 140s
- Log: logs/learn_20260330_092513.log

---
## Learning Loop -- 2026-03-30 09:30

- Split: training, Tasks: 80
- Correct: 60 / 80 (75.0%)
- Rules: 59 -> 59 (+0 learned)
- Stored rule hits: 60
- Time: 147s
- Log: logs/learn_20260330_092812.log

---
## Session 23 -- 2026-03-30 09:40

- Split: training, Tasks: 80
- Correct: 63 / 80 (78.8%) ← was 60/80 (75.0%)
- Rules: 59 -> 62 (+3 learned)
- Stored rule hits: 60
- Time: 138s
- Log: logs/learn_20260330_093758.log
- New concepts:
  - `mirror_h_tile_2x` — flip_h + concat + tile 2x (solved 59341089)
  - `recolor_tiles_by_key` — replace tile-color pixels using key matrix (solved 33b52de3)
  - `larger_frame_2x2` — output 2x2 of the bigger rectangular frame color (solved 445eab21)
- New primitives: `recolor_tiles_by_key`, `larger_frame_2x2`

---
## Learning Loop -- 2026-03-30 09:43

- Split: training, Tasks: 80
- Correct: 63 / 80 (78.8%)
- Rules: 62 -> 62 (+0 learned)
- Stored rule hits: 63
- Time: 140s
- Log: logs/learn_20260330_094050.log

---
## Session 24 -- 2026-03-30 09:56

- Split: training, Tasks: 80
- Correct: 66 / 80 (82.5%) ← was 63/80 (78.8%)
- Rules: 62 -> 65 (+3 learned)
- Stored rule hits: 63
- Time: 138s
- Log: logs/learn_20260330_095409.log
- New concepts:
  - `separator_block_decode` — find clean block (no color 8) in separator grid, map its color positions to output blocks (solved 09629e4f)
  - `corner_blocks_reflect` — reflect majority-color corner blocks inward by block size, minority stays (solved 22208ba4)
  - `slide_block_along_dots` — slide 3x3 block one dot-step along evenly-spaced marker line (solved 5168d44c)
- New primitives: `separator_block_decode`, `corner_blocks_reflect_inward`, `slide_block_along_dots`

---
## Learning Loop -- 2026-03-30 09:59

- Split: training, Tasks: 80
- Correct: 66 / 80 (82.5%)
- Rules: 65 -> 65 (+0 learned)
- Stored rule hits: 66
- Time: 139s
- Log: logs/learn_20260330_095708.log

---
## Session 25 -- 2026-03-30 10:12

- Split: training, Tasks: 80
- Correct: 69 / 80 (86.2%) ← was 66/80 (82.5%)
- Rules: 65 -> 68 (+3 learned)
- Stored rule hits: 66
- Time: 138s
- Log: logs/learn_20260330_101242.log
- New concepts:
  - `overlay_color_layers` — overlay N vertically-stacked single-color layers with inferred priority order (solved 3d31c5b3)
  - `complete_diamond_symmetry` — complete 4-fold rotational symmetry of sparse checkerboard diamond pattern (solved 11852cab)
  - `decode_section_holes` — classify grid sections by internal hole pattern, output uniform-color rows (solved 995c5fa3)
- New primitives: `overlay_color_layers`, `complete_diamond_symmetry`, `decode_section_holes`
- New inference methods: `layer_priority`, `section_hole_mapping`

---
## Learning Loop -- 2026-03-30 10:18

- Split: training, Tasks: 80
- Correct: 69 / 80 (86.2%)
- Rules: 68 -> 68 (+0 learned)
- Stored rule hits: 69
- Time: 139s
- Log: logs/learn_20260330_101541.log

---
## Session 26 -- 2026-03-30 10:30

- Split: training, Tasks: 80
- Correct: 71 / 80 (88.8%) ← was 69/80 (86.2%)
- Rules: 68 -> 70 (+2 learned)
- Stored rule hits: 69
- Time: 140s
- Log: logs/learn_20260330_103026.log
- New concepts:
  - `bar_height_difference` — bars at odd columns; add color-5 bar with height = |sum(heights_A) - sum(heights_B)| (solved 37ce87bb)
  - `recolor_shapes_by_template` — header templates behind L-shaped separator; body shapes of color 3 recolored to matching template color via rotation/reflection-invariant matching (solved 845d6e51)
- New primitives: `bar_height_difference`, `recolor_shapes_by_template`

---
## Learning Loop -- 2026-03-30 10:35

- Split: training, Tasks: 80
- Correct: 71 / 80 (88.8%)
- Rules: 70 -> 70 (+0 learned)
- Stored rule hits: 71
- Time: 149s
- Log: logs/learn_20260330_103328.log

---
## Session 27 (Claude) -- 2026-03-30 11:14

### Changes
- Added `stamp_shape_template` primitive to `_primitives.py` — finds a colored template shape (connected cells of one color), then stamps all matching groups of a target color with that shape. Uses greedy overlap resolution (fewest external neighbors first). For 1D templates (single row/column), constrains matches to the same row/column.
- Created `procedural_memory/concepts/stamp_shape_template.json` (solves e5062a87)

### Results
- Split: training, Tasks: 80
- Correct: 72 / 80 (90.0%) — up from 71/80 (88.8%)
- Rules: 70 -> 71 (+1 learned)
- Stored rule hits: 71
- Time: 172s
- Log: logs/learn_20260330_111136.log

---
## Learning Loop -- 2026-03-30 11:18

- Split: training, Tasks: 80
- Correct: 72 / 80 (90.0%)
- Rules: 71 -> 71 (+0 learned)
- Stored rule hits: 72
- Time: 166s
- Log: logs/learn_20260330_111522.log

---
## Session 28 (Claude) -- 2026-03-30 11:47

### Changes
- Added `tile_shape_to_markers` primitive to `_primitives.py` — finds rectangular shapes and marker line segments of a given color, tiles each shape periodically toward its aligned markers (horizontal or vertical)
- Added `stamp_tile_to_strip` primitive to `_primitives.py` — finds 3x3 stamps (auto-detects border color), matches each stamp's center color to a solid-color strip, tiles the stamp pattern toward the strip using ceil(gap/3) additional periods
- Created `procedural_memory/concepts/tile_shape_to_markers.json` (solves c62e2108)
- Created `procedural_memory/concepts/stamp_tile_to_strip.json` (solves 985ae207)

### Results
- Split: training, Tasks: 80
- Correct: 74 / 80 (92.5%) — up from 72/80 (90.0%)
- Rules: 71 -> 73 (+2 learned)
- Stored rule hits: 72
- Discovered: 2 new rules from pipeline
- Time: 169s
- Log: logs/learn_20260330_114411.log

---
## Learning Loop -- 2026-03-30 11:50

- Split: training, Tasks: 80
- Correct: 74 / 80 (92.5%)
- Rules: 73 -> 73 (+0 learned)
- Stored rule hits: 74
- Time: 167s
- Log: logs/learn_20260330_114753.log

---
## Learning Loop -- 2026-04-03 00:52

- Split: training, Tasks: 3
- Correct: 1 / 3 (33.3%)
- Rules: 73 -> 73 (+0 learned)
- Stored rule hits: 1
- Time: 7s
- Log: logs/learn_20260403_005207.log

---
## Learning Loop -- 2026-04-03 00:55

- Split: training, Tasks: 10
- Correct: 10 / 10 (100.0%)
- Rules: 73 -> 73 (+0 learned)
- Stored rule hits: 10
- Time: 22s
- Log: logs/learn_20260403_005442.log

---
## Learning Loop -- 2026-04-03 00:55

- Split: training, Tasks: 10
- Correct: 10 / 10 (100.0%)
- Rules: 73 -> 73 (+0 learned)
- Stored rule hits: 10
- Time: 20s
- Log: logs/learn_20260403_005510.log

---
## Learning Loop -- 2026-04-03 00:56

- Split: training, Tasks: 20
- Correct: 20 / 20 (100.0%)
- Rules: 73 -> 73 (+0 learned)
- Stored rule hits: 20
- Time: 48s
- Log: logs/learn_20260403_005600.log

---
## Features: Routing + 2nd-Order Key + Chunking -- 2026-04-03

### Implementation Summary
Three architectural features added to the SOAR pipeline:

**Feature 1: Symbolic Memory Store Routing** (`agent/memory_router.py`)
- Static routing table maps (level, phase) -> relevant memory stores
- Each operator logs its store access: `[ROUTER] generalize @ (GRID, generalize) -> [procedural_memory]`
- Prevents irrelevant stores from being loaded at each pipeline stage

**Feature 2: 2nd-Order Comparison as Episodic Key** (`agent/episodic.py`)
- Episodes now store `structural_key` with COMM/DIFF topology (no concrete values)
- Retrieval: exact topology match -> partial topology match -> fingerprint fallback
- Functions: `extract_topology()`, `topologies_match()`, `topology_similarity()`, `build_structural_key()`

**Feature 3: Impasse-Driven Chunking** (`agent/chunking.py`)
- When GeneralizeOperator finds a concept, chunks topology + concept into activation rule
- Chunked rules stored in `DSL_activation_rule/` with only COMM/DIFF topology, no values
- Duplicate detection: same topology + same concept = increment counter
- Anti-regression check before saving

### Verification Results
- `python run_task.py` -> RESULT: CORRECT (regression gate passed)
- `python run_learn.py --limit 20 --shuffle` -> 20/20 (100.0%)
- Chunked rules created: 1
- Chunked rules rejected: 0
- Chunked rule example: `{color: DIFF, contents: DIFF, size: COMM}` -> `recolor_by_size_group` (validated 2x)
- Topology matching confirmed: `[CHUNK] Topology match!` observed during pipeline runs
- All episodes eligible for structural key enrichment on next pipeline pass

---
## Learning Loop -- 2026-04-03 20:40

- Split: training, Tasks: 5
- Correct: 5 / 5 (100.0%)
- Rules: 73 -> 73 (+0 learned)
- Stored rule hits: 5
- Time: 9s
- Log: logs/learn_20260403_204015.log

---
## Learning Loop -- 2026-04-03 20:47

- Split: training, Tasks: 10
- Correct: 10 / 10 (100.0%)
- Rules: 73 -> 73 (+0 learned)
- Stored rule hits: 10
- Time: 19s
- Log: logs/learn_20260403_204731.log

---
## Features: LGG Merger + ACE Playbook + POLARIS Loop -- 2026-04-03

### Feature 4: LGG Rule Merger (`agent/rule_merger.py`)
- Groups chunked rules by (topology, concept), merges duplicates via anti-unification
- SMT constraint: only identical topologies can merge
- Merged rules saved as `merged_<hash>_<concept>.json`, originals to `superseded/`
- Current state: 1 chunked rule, no merges possible yet (need 2+ with same topology)
- Runs automatically after each run_learn.py session

### Feature 5: ACE-Style Playbook (`agent/playbook.py`, `PLAYBOOK.json`)
- 13 initial bullets across 7 sections, seeded from PROMPT.md
- Trajectory logging: run_learn.py now writes `logs/trajectory_<ts>.json` per session
- Reflector (`scripts/reflect.py`): analyzes failures, groups by topology, identifies root causes
- Curator (`scripts/curate.py`): applies deltas to PLAYBOOK.json (max 3 new bullets per run)
- Playbook rendered into Claude Code prompt via `render_for_prompt()`

### Feature 6: POLARIS Structured Failure Analysis
- `scripts/validate_patch.py`: 2-stage validation (topology match + regression check)
- New Claude Code prompt: structured diagnosis → strategy synthesis → implementation → validation
- Reflect/curate runs between learning and Claude Code improvement in run_loop.sh
- Validation gate before git commit

### Verification Results
- `python run_task.py` -> RESULT: CORRECT (regression gate)
- `python run_learn.py --limit 10 --shuffle` -> 10/10 (100%)
- Trajectory logging: confirmed topology captured for all tasks
- Reflect/curate pipeline: confirmed working (0 failures = 0 new bullets, as expected)
- `python scripts/validate_patch.py` -> VALIDATION_PASS (1 rule verified)
- Playbook version: 1, bullets: 13
- Merged rules: 0 (only 1 chunked rule exists, need 2+ for merging)
- PROMPT.md kept as backup reference

---
## Learning Loop -- 2026-04-04 21:58

- Split: training, Tasks: 20
- Correct: 20 / 20 (100.0%)
- Rules: 0 -> 20 (+20 learned)
- Stored rule hits: 0
- Time: 49s
- Log: logs/learn_20260404_215749.log

---
## Learning Loop -- 2026-04-04 22:16

- Split: training, Tasks: 20
- Correct: 0 / 20 (0.0%)
- Rules: 0 -> 0 (+0 learned)
- Stored rule hits: 0
- Time: 43s
- Log: logs/learn_20260404_221551.log

---
## Learning Loop -- 2026-04-04 22:17

- Split: training, Tasks: 20
- Correct: 0 / 20 (0.0%)
- Rules: 0 -> 0 (+0 learned)
- Stored rule hits: 0
- Time: 33s
- Log: logs/learn_20260404_221643.log

---
## Learning Loop -- 2026-04-04 22:18

- Split: training, Tasks: 20
- Correct: 0 / 20 (0.0%)
- Rules: 0 -> 0 (+0 learned)
- Stored rule hits: 0
- Time: 37s
- Log: logs/learn_20260404_221724.log

---
## Learning Loop -- 2026-04-04 22:18

- Split: training, Tasks: 20
- Correct: 0 / 20 (0.0%)
- Rules: 0 -> 0 (+0 learned)
- Stored rule hits: 0
- Time: 37s
- Log: logs/learn_20260404_221809.log

---
## Learning Loop -- 2026-04-04 22:19

- Split: training, Tasks: 20
- Correct: 0 / 20 (0.0%)
- Rules: 0 -> 0 (+0 learned)
- Stored rule hits: 0
- Time: 37s
- Log: logs/learn_20260404_221853.log

---
## Learning Loop -- 2026-04-04 22:20

- Split: training, Tasks: 20
- Correct: 0 / 20 (0.0%)
- Rules: 0 -> 0 (+0 learned)
- Stored rule hits: 0
- Time: 37s
- Log: logs/learn_20260404_221937.log

---
## Learning Loop -- 2026-04-04 22:20

- Split: training, Tasks: 20
- Correct: 0 / 20 (0.0%)
- Rules: 0 -> 0 (+0 learned)
- Stored rule hits: 0
- Time: 37s
- Log: logs/learn_20260404_222022.log

---
## Learning Loop -- 2026-04-04 22:21

- Split: training, Tasks: 20
- Correct: 0 / 20 (0.0%)
- Rules: 0 -> 0 (+0 learned)
- Stored rule hits: 0
- Time: 37s
- Log: logs/learn_20260404_222106.log

---
## Learning Loop -- 2026-04-04 22:22

- Split: training, Tasks: 20
- Correct: 0 / 20 (0.0%)
- Rules: 0 -> 0 (+0 learned)
- Stored rule hits: 0
- Time: 38s
- Log: logs/learn_20260404_222151.log

---
## Learning Loop -- 2026-04-04 22:23

- Split: training, Tasks: 20
- Correct: 0 / 20 (0.0%)
- Rules: 0 -> 0 (+0 learned)
- Stored rule hits: 0
- Time: 38s
- Log: logs/learn_20260404_222236.log

---
## Learning Loop -- 2026-04-04 22:23

- Split: training, Tasks: 20
- Correct: 0 / 20 (0.0%)
- Rules: 0 -> 0 (+0 learned)
- Stored rule hits: 0
- Time: 37s
- Log: logs/learn_20260404_222321.log

---
## Learning Loop -- 2026-04-04 22:24

- Split: training, Tasks: 20
- Correct: 0 / 20 (0.0%)
- Rules: 0 -> 0 (+0 learned)
- Stored rule hits: 0
- Time: 37s
- Log: logs/learn_20260404_222406.log

---
## Learning Loop -- 2026-04-04 22:38

- Split: training, Tasks: 1
- Correct: 0 / 1 (0.0%)
- Rules: 0 -> 0 (+0 learned)
- Stored rule hits: 0
- Time: 1s
- Log: logs/learn_20260404_223827.log

---
## Learning Loop -- 2026-04-04 22:52

- Split: training, Tasks: 1
- Correct: 0 / 1 (0.0%)
- Rules: 2 -> 3 (+1 learned)
- Stored rule hits: 0
- Time: 98s
- Log: logs/learn_20260404_225037.log

---
## Learning Loop -- 2026-04-04 22:57

- Split: training, Tasks: 20
- Correct: 0 / 20 (0.0%)
- Rules: 0 -> 0 (+0 learned)
- Stored rule hits: 0
- Time: 65s
- Log: logs/learn_20260404_225557.log

---
## Learning Loop -- 2026-04-04 23:00

- Split: training, Tasks: 20
- Correct: 20 / 20 (100.0%)
- Rules: 3 -> 23 (+20 learned)
- Stored rule hits: 1
- Time: 59s
- Log: logs/learn_20260404_225916.log

---
## Learning Loop -- 2026-04-04 23:02

- Split: training, Tasks: 20
- Correct: 7 / 20 (35.0%)
- Rules: 25 -> 25 (+0 learned)
- Stored rule hits: 2
- Time: 83s
- Log: logs/learn_20260404_230121.log

---
## Learning Loop -- 2026-04-04 23:04

- Split: training, Tasks: 80
- Correct: 74 / 80 (92.5%)
- Rules: 23 -> 16 (+-7 learned)
- Stored rule hits: 22
- Time: 231s
- Log: logs/learn_20260404_230023.log

---
## Learning Loop -- 2026-04-04 23:09

- Split: training, Tasks: 20
- Correct: 6 / 20 (30.0%)
- Rules: 1 -> 7 (+6 learned)
- Stored rule hits: 0
- Time: 64s
- Log: logs/learn_20260404_230852.log

---
## Learning Loop -- 2026-04-04 23:13

- Split: training, Tasks: 80
- Correct: 5 / 80 (6.2%)
- Rules: 0 -> 13 (+13 learned)
- Stored rule hits: 1
- Time: 327s
- Log: logs/learn_20260404_230815.log

---
## Learning Loop -- 2026-04-04 23:21

- Split: training, Tasks: 100
- Correct: 4 / 100 (4.0%)
- Rules: 7 -> 0 (+-7 learned)
- Stored rule hits: 0
- Time: 674s
- Log: logs/learn_20260404_231016.log

---
## Learning Loop -- 2026-04-04 23:22

- Split: training, Tasks: 20
- Correct: 5 / 20 (25.0%)
- Rules: 1 -> 3 (+2 learned)
- Stored rule hits: 0
- Time: 238s
- Log: logs/learn_20260404_231852.log

---
## Learning Loop -- 2026-04-04 23:25

- Split: training, Tasks: 20
- Correct: 12 / 20 (60.0%)
- Rules: 5 -> 6 (+1 learned)
- Stored rule hits: 0
- Time: 88s
- Log: logs/learn_20260404_232359.log

---
## Learning Loop -- 2026-04-04 23:57

- Split: training, Tasks: 20
- Correct: 0 / 20 (0.0%)
- Rules: 0 -> 0 (+0 learned)
- Stored rule hits: 0
- Time: 44s
- Log: logs/learn_20260404_235622.log

---
## Learning Loop -- 2026-04-05 00:21

- Split: training, Tasks: 20
- Correct: 0 / 20 (0.0%)
- Rules: 0 -> 0 (+0 learned)
- Stored rule hits: 0
- Time: 44s
- Log: logs/learn_20260405_002102.log

---
## Learning Loop -- 2026-04-05 14:18

- Split: training, Tasks: 20
- Correct: 0 / 20 (0.0%)
- Rules: 0 -> 0 (+0 learned)
- Stored rule hits: 0
- Time: 56s
- Log: logs/learn_20260405_141707.log

---
## Learning Loop -- 2026-04-05 16:12

- Split: training, Tasks: 20
- Correct: 0 / 20 (0.0%)
- Rules: 0 -> 0 (+0 learned)
- Stored rule hits: 0
- Time: 46s
- Log: logs/learn_20260405_161212.log

---
## Learning Loop -- 2026-04-05 16:32

- Split: training, Tasks: 5
- Correct: 0 / 5 (0.0%)
- Rules: 0 -> 0 (+0 learned)
- Stored rule hits: 0
- Time: 9s
- Log: logs/learn_20260405_163245.log

---
## Learning Loop -- 2026-04-05 16:42

- Split: training, Tasks: 20
- Correct: 0 / 20 (0.0%)
- Rules: 0 -> 0 (+0 learned)
- Stored rule hits: 0
- Time: 49s
- Log: logs/learn_20260405_164132.log

---
## Learning Loop -- 2026-04-05 16:52

- Split: training, Tasks: 20
- Correct: 0 / 20 (0.0%)
- Rules: 0 -> 0 (+0 learned)
- Stored rule hits: 0
- Time: 51s
- Log: logs/learn_20260405_165203.log

---
## Learning Loop -- 2026-04-05 17:02

- Split: training, Tasks: 20
- Correct: 0 / 20 (0.0%)
- Rules: 0 -> 0 (+0 learned)
- Stored rule hits: 0
- Time: 50s
- Log: logs/learn_20260405_170202.log

---
## Learning Loop -- 2026-04-05 17:43

- Split: training, Tasks: 20
- Correct: 0 / 20 (0.0%)
- Rules: 0 -> 0 (+0 learned)
- Stored rule hits: 0
- Time: 49s
- Log: logs/learn_20260405_174249.log

---
## Learning Loop -- 2026-04-05 18:03

- Split: training, Tasks: 20
- Correct: 0 / 20 (0.0%)
- Rules: 0 -> 0 (+0 learned)
- Stored rule hits: 0
- Time: 44s
- Log: logs/learn_20260405_180218.log

---
## Learning Loop -- 2026-04-05 18:12

- Split: training, Tasks: 2
- Correct: 0 / 2 (0.0%)
- Rules: 0 -> 0 (+0 learned)
- Stored rule hits: 0
- Time: 3s
- Log: logs/learn_20260405_181245.log

---
## Learning Loop -- 2026-04-05 18:17

- Split: training, Tasks: 3
- Correct: 0 / 3 (0.0%)
- Rules: 0 -> 0 (+0 learned)
- Stored rule hits: 0
- Time: 5s
- Log: logs/learn_20260405_181703.log

---
## Learning Loop -- 2026-04-05 18:22

- Split: training, Tasks: 20
- Correct: 0 / 20 (0.0%)
- Rules: 0 -> 0 (+0 learned)
- Stored rule hits: 0
- Time: 45s
- Log: logs/learn_20260405_182159.log

---
## Learning Loop -- 2026-04-05 18:36

- Split: training, Tasks: 20
- Correct: 0 / 20 (0.0%)
- Rules: 0 -> 0 (+0 learned)
- Stored rule hits: 0
- Time: 55s
- Log: logs/learn_20260405_183553.log

---
## Learning Loop -- 2026-04-05 18:45

- Split: training, Tasks: 20
- Correct: 0 / 20 (0.0%)
- Rules: 0 -> 0 (+0 learned)
- Stored rule hits: 0
- Time: 51s
- Log: logs/learn_20260405_184428.log

---
## Learning Loop -- 2026-04-05 19:12

- Split: training, Tasks: 20
- Correct: 1 / 20 (5.0%)
- Rules: 0 -> 1 (+1 learned)
- Stored rule hits: 0
- Time: 41s
- Log: logs/learn_20260405_191143.log

---
## Learning Loop -- 2026-04-05 19:19

- Split: training, Tasks: 20
- Correct: 1 / 20 (5.0%)
- Rules: 1 -> 1 (+0 learned)
- Stored rule hits: 1
- Time: 62s
- Log: logs/learn_20260405_191831.log

---
## Session (Claude) -- 2026-04-05

### Changes
- Created `procedural_memory/concepts/color_remap.json` — bijective color remapping using `recolor` + `color_map_from_arckg` (solves 0d3d703e)
- Created `procedural_memory/concepts/gravity_down.json` — gravity-drop cells to bottom using `gravity` primitive (solves 1e0a9b12)
- Added `staircase_grow` primitive to `_primitives.py` — grows 1-row prefix into staircase triangle
- Created `procedural_memory/concepts/staircase_grow.json` — parameterless staircase concept (solves bbc9ae5d)

### Results
- 0d3d703e: CORRECT (color remap)
- 1e0a9b12: CORRECT (gravity down)
- bbc9ae5d: CORRECT (staircase grow)
- 08ed6ac7: CORRECT (regression gate)

---
## Learning Loop -- 2026-04-05 19:24

- Split: training, Tasks: 20
- Correct: 20 / 20 (100.0%)
- Rules: 1 -> 20 (+19 learned)
- Stored rule hits: 1
- Time: 52s
- Log: logs/learn_20260405_192353.log

---
## Learning Loop -- 2026-04-05 19:24

- Split: training, Tasks: 20
- Correct: 20 / 20 (100.0%)
- Rules: 5 -> 20 (+15 learned)
- Stored rule hits: 20
- Time: 50s
- Log: logs/learn_20260405_192404.log
