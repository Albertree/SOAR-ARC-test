
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
