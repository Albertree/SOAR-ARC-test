
---
## Session 63 (Claude) -- 2026-04-06

### Analysis
Picked 3 failing tasks from session 62 (63/80 = 78.8%):
- **0692e18c**: Complement self-tiling. 3x3 input → 9x9 output. For each non-bg cell, place the inverted grid (swap color↔0) at that tile position; bg cells → empty blocks.
- **0962bcdd**: Expand cross pattern into diamond. Each cross (center + 4 orthogonal arms) gets arms extended by 1 and center color placed at diagonal distance-2 corners.
- **11852cab**: Complete diamond symmetry. A sparse checkerboard-diamond pattern with some missing positions; fill by 4-fold rotational symmetry (90° rotations around center).

### Changes
1. **New primitive**: `self_tile_complement` — complement self-tiling (invert grid colors, place at non-bg tile positions)
2. **New primitive**: `expand_cross_diamond` — extend cross arms and add center-color diagonal corners
3. **New primitive**: `complete_diamond_symmetry` — fill missing diamond positions via 4-fold rotational symmetry
4. **New concept**: `self_tile_complement.json`
5. **New concept**: `expand_cross_diamond.json`
6. **New concept**: `complete_diamond_symmetry.json`

### Regression
- 0692e18c: CORRECT
- 0962bcdd: CORRECT
- 11852cab: CORRECT
- 08ed6ac7: CORRECT (regression gate)

---
## Session 60 (Claude) -- 2026-04-06

### Analysis
Picked 3 failing tasks from session 59 (63/80 = 78.8%):
- **0520fde7**: Grid split by separator column (color 5). Output is the AND of left/right halves — mark with color 2 where both sides have non-bg.
- **0d3d703e**: Fixed color pair swap: (1↔5), (2↔6), (3↔4), (8↔9). Grid structure preserved, only colors change.
- **0ca9ddb6**: Decorate isolated pixels — color 1 gets a plus(+) of color 7, color 2 gets an X of color 4. Other colors unchanged.

### Changes
1. **New primitive**: `grid_and_by_separator` — splits grid by separator row or column, outputs AND of both halves (marks with output_color where both are non-zero).
2. **New primitive**: `decorate_pixels_by_color` — adds plus/X decorations around pixels based on their color (1→plus/7, 2→X/4).
3. **New concept**: `grid_and_by_separator.json`
4. **New concept**: `color_pair_swap.json` — uses existing `recolor` primitive with `color_map_from_arckg` inference.
5. **New concept**: `decorate_pixels_by_color.json`

### Regression
- 0520fde7: CORRECT
- 0d3d703e: CORRECT
- 0ca9ddb6: CORRECT
- 08ed6ac7: CORRECT (regression gate)

---
## Session 59 (Claude) -- 2026-04-06

### Changes
- New primitive: `overlay_stacked_blocks` — split grid into N equal horizontal blocks (each with a distinct color), overlay with priority 5>4>8>2. Solves 3d31c5b3.
- New primitive: `bar_chart_difference` — find vertical bars of color 8 and 2 on bg 7, place color 5 bar with height = sum(8) - sum(2). Solves 37ce87bb.
- New primitive: `hop_box_along_dots` — move a 3x3 bordered box one hop along a trail of dots toward the side with more dots. Solves 5168d44c.
- New concepts: `overlay_stacked_blocks.json`, `bar_chart_difference.json`, `hop_box_along_dots.json`

### Regression
- 08ed6ac7: CORRECT
- 3d31c5b3: CORRECT
- 37ce87bb: CORRECT
- 5168d44c: CORRECT

---
## Session 58 (Claude) -- 2026-04-06

### Analysis
Picked 2 failing tasks from session 57 (58/80 = 72.5%):
- **29623171**: Grid divided by separator lines (color 5) into 3x3 sections. Count non-bg dots per section; fill sections with the max count, clear others.
- **070dd51e**: Pairs of same-colored pixels on a sparse grid. Connect each pair with a horizontal or vertical line. Vertical lines take priority at intersections.

### Changes
1. **New primitive**: `separator_grid_max_fill` — finds separator rows/cols, counts content cells per section, fills max-count sections, clears rest.
2. **New primitive**: `connect_dot_pairs` — groups pixels by color (pairs), draws h/v lines between them, vertical lines overwrite at crossings.
3. **New concept**: `separator_grid_max_fill.json`
4. **New concept**: `connect_dot_pairs.json`

### Regression
- 29623171: CORRECT
- 070dd51e: CORRECT
- 08ed6ac7: CORRECT (regression gate)

---
## Session 57 (Claude) -- 2026-04-06

### Changes
- New primitive: `zigzag_collect_pixels` — collect scattered non-bg pixels, sort by column, fill 3x3 in snake order. Solves cdecee7f.
- New primitive: `fill_bounding_box_interior` — find bounding box of a shape color, fill interior bg cells with a new color. Solves 6d75e8bb.
- New concepts: `zigzag_collect_pixels.json`, `fill_bounding_box_interior.json`

### Regression
- 08ed6ac7: CORRECT
- cdecee7f: CORRECT
- 6d75e8bb: CORRECT

---
## Session 56 (Claude) -- 2026-04-06

### Analysis
Picked 3 failing tasks from session 55 (50/80 = 62.5%):
- **506d28a5**: OR overlay — split grid by separator row, OR both halves into color 3
- **f5b8619d**: Column fill + tile — fill bg cells in columns containing content with 8, tile 2x2
- **72207abc**: Expanding gap sequence — place colors cyclically at triangular number positions

### Changes
1. **New primitive**: `grid_or_by_separator` — like `grid_xor_by_separator` but uses OR logic; improved separator detection to handle uniform data rows
2. **New primitive**: `fill_nonzero_columns_tile2x2` — fills empty cells in active columns with color 8, tiles result 2x2
3. **New primitive**: `expanding_gap_sequence` — reads non-zero colors from active row, places them cyclically at positions 0, 1, 3, 6, 10, 15, ...
4. **New concept**: `grid_or_by_separator.json`
5. **New concept**: `fill_nonzero_columns_tile2x2.json`
6. **New concept**: `expanding_gap_sequence.json`

### Verification
- `506d28a5`: CORRECT
- `f5b8619d`: CORRECT
- `72207abc`: CORRECT
- `08ed6ac7`: CORRECT (regression gate)

---
## Session 55 (Claude) -- 2026-04-06

### Analysis
Picked 3 failing tasks from session 54 (48/80 = 60%):
- **007bbfb7**: Self-tiling fractal — each non-bg cell becomes a copy of the whole grid
- **59341089**: Mirror horizontal tile — each row becomes [reversed | original] × 2
- **bda2d7a6**: Concentric ring color cycling — ring colors shift by 1 position

### Changes
1. **New concept**: `self_tile_fractal.json` — uses existing `self_tile` primitive with bg=0 default
2. **New concept**: `mirror_horizontal_tile_4x.json` — composes `flip_horizontal` + `concat_horizontal` × 2
3. **Fixed primitive**: `reverse_concentric_rings` — was reversing ring colors (wrong), now cyclically rotates unique ring colors by 1 position (correct)

### Verification
- `007bbfb7`: CORRECT
- `59341089`: CORRECT
- `bda2d7a6`: CORRECT
- `08ed6ac7`: CORRECT (regression gate)

---
## Session 54 (Claude) -- 2026-04-06

### Analysis

Picked 3 failing tasks from Session 53 (45/80, 56.2%):

| Task | Pattern | Solution |
|------|---------|----------|
| 332efdb3 | All-zero grid → checkerboard (1 where row or col is even) | New primitive `checkerboard_grid` + concept |
| 99b1bc43 | Two grids split by separator row; XOR → color 3 where exactly one half is non-zero | New primitive `grid_xor_by_separator` + concept |
| 445eab21 | Two hollow rectangles; output 2x2 filled with color of the one with larger interior | New primitive `larger_hollow_rect_color` + concept |

### Changes
- Added 3 primitives to `_primitives.py`: `checkerboard_grid`, `grid_xor_by_separator`, `larger_hollow_rect_color`
- Created 3 concept JSONs: `checkerboard_grid.json`, `grid_xor_by_separator.json`, `larger_hollow_rect_color.json`

### Verification
- 332efdb3: CORRECT
- 99b1bc43: CORRECT
- 445eab21: CORRECT
- 08ed6ac7 (regression gate): CORRECT

---
## Session 53 (Claude) -- 2026-04-06

### Analysis

Picked 3 failing tasks from 80-task run (41/80 = 51.2%):

1. **62c24649** — Mirror input horizontally and vertically to create 2x2 symmetric output
2. **48131b3c** — Invert binary grid (swap 0 and non-zero color), then tile 2x2
3. **e7a25a18** — Extract bordered rectangle with 2x2 color quadrant pattern, expand quadrants to fill interior

### Changes

1. **New primitive: `invert_binary`** in `_primitives.py`
   - Swaps bg (0) and the single non-bg color in a binary grid

2. **New primitive: `expand_quadrants_in_border`** in `_primitives.py`
   - Finds bordered rectangle, detects 2x2 color arrangement inside, scales quadrants to fill interior

3. **New concept: `mirror_symmetric_tile.json`**
   - Composes flip_horizontal + concat_horizontal + flip_vertical + concat_vertical
   - Zero parameters, uses existing primitives

4. **New concept: `invert_binary_tile_2x2.json`**
   - Uses new invert_binary primitive, then tiles 2x2 via concat
   - Zero parameters

5. **New concept: `expand_quadrants_in_border.json`**
   - Uses new expand_quadrants_in_border primitive
   - Signature: color_preserved=null (color 0 disappears in output)

### Results

- Previous: 41/80 (51.2%)
- New tasks solved: 62c24649, 48131b3c, e7a25a18
- Regression gate (08ed6ac7): CORRECT

---
## Session 52 (Claude) -- 2026-04-06

### Results
- **40/40 (100.0%)** -- perfect score, no failing tasks
- Rules: 43 -> 45 (+2 learned)
- Reused: 38 times (stored rule hit)
- Discovered: 2 new rules from pipeline
- Regression gate: all passing

No changes needed -- all tasks solved.

---
## Session 51 (Claude) -- 2026-04-06

### Changes
- Added 2 new primitives to `_primitives.py`:
  - `mark_domino_crosshairs`: finds domino pairs (2-cell adjacent groups) forming a crosshair with gap=1 on each side, marks center with color 4
  - `separator_zone_gravity`: finds 4 separator lines (2 vertical, 2 horizontal), extracts bounded zone, applies gravity toward the separator matching the scattered data color
- Created 2 new concept JSONs:
  - `mark_domino_crosshairs.json` (solves 9f5f939b)
  - `separator_zone_gravity.json` (solves 5daaa586)

### Results
- Previous session: 36/40 (90.0%)
- New tasks solved: 9f5f939b, 5daaa586 (+2)
- Regression gate (08ed6ac7): CORRECT
- Total concepts: 39

---
## Session 50 (Claude) -- 2026-04-06

### Changes
- Added 2 new primitives to `_primitives.py`:
  - `border_interior_fill`: classifies connected components of a target color as border-touching or interior, recolors each accordingly
  - `most_common_cross_arm_color`: finds cross patterns (center=4, uniform cardinal arms), returns 1x1 grid with the most frequent arm color
- Created 2 new concept JSONs:
  - `border_interior_fill.json` (solves 84db8fc4)
  - `most_common_cross_arm.json` (solves 642d658d)

### Results
- Previous session: 32/40 (80.0%)
- New tasks solved: 84db8fc4, 642d658d (+2)
- Regression gate (08ed6ac7): CORRECT
- Total concepts: 35

---
## Session 49 (Claude) -- 2026-04-06

### Changes
- Added 3 new primitives to `_primitives.py`:
  - `rotation_tile_4x4`: tiles a grid into 4x4 arrangement with 2x2 macro-blocks of R180/R90/R270/orig
  - `color_remap_from_keys`: extracts pattern rectangle and remaps colors using scattered 2-cell key pairs
  - `mark_square_frame_corners`: finds square frame objects and places marker color at corner extensions
- Created 3 new concept JSONs:
  - `rotation_tile_4x4.json` (solves cf5fd0ad)
  - `color_remap_from_keys.json` (solves e9b4f6fc)
  - `mark_square_frame_corners.json` (solves 14b8e18c)

### Results
- Previous session: 29/40 (72.5%)
- New tasks solved: cf5fd0ad, e9b4f6fc, 14b8e18c (+3)
- Regression gate (08ed6ac7): CORRECT
- Total concepts: 33

---
## Session 48 (Claude) -- 2026-04-06

### Changes
- Added 2 new primitives to `_primitives.py`:
  - `extract_bordered_rect_swap`: extracts bordered rectangle from bg, swaps border/interior colors
  - `denoise_rectangles`: removes noise pixels, keeps only cells belonging to a 2x2 solid fg block
- Created 2 new concept JSONs:
  - `extract_bordered_rect_swap.json` (solves b94a9452)
  - `denoise_rectangles.json` (solves 7f4411dc)

### Results
- Previous session: 27/40 (67.5%)
- New tasks solved: b94a9452, 7f4411dc (+2)
- Regression gate (08ed6ac7): CORRECT
- Total concepts: 30

---
## Session 47 (Claude) -- 2026-04-06

### Changes
- Added 3 new primitives to `_primitives.py`:
  - `extend_diagonal_arms`: extends diagonal single-pixel arms from 2x2 blocks to grid edges
  - `count_inside_bordered_rect`: counts colored pixels inside a 1-bordered rectangle, outputs 3x3 grid
  - `fill_enclosed_rectangles`: fills interiors of fully enclosed rectangles with a fill color
- Created 3 new concept JSONs:
  - `extend_diagonal_arms.json` (solves 7ddcd7ec)
  - `count_inside_bordered_rect.json` (solves c8b7cc0f)
  - `fill_enclosed_rectangles.json` (solves a5313dff)

### Results
- Previous session: 24/40 (60.0%)
- New tasks solved: 7ddcd7ec, c8b7cc0f, a5313dff (+3)
- Regression gate (08ed6ac7): CORRECT
- Total concepts: 28

---
## Session 46 (Claude) -- 2026-04-06

### Changes
- New primitive `l_shape_nearest_corner` in `_primitives.py` — each non-bg pixel extends an L-shape toward its nearest grid corner
- New concept `l_shape_nearest_corner.json` (solves 705a3229)
- New primitive `rotation_tile_2x2` in `_primitives.py` — tiles a grid into 2x2 arrangement of rotated copies (identity, 90CCW, 180, 90CW)
- New concept `rotation_tile_2x2.json` (solves ed98d772)
- New primitive `diagonal_project_2x2` in `_primitives.py` — projects 2x2 block colors diagonally to adjacent corner rectangles
- New concept `diagonal_project_2x2.json` (solves 93b581b8)
- New primitive `tile_pattern_upward` in `_primitives.py` — tiles bottom pattern upward cyclically to fill blank rows
- New concept `tile_pattern_upward.json` (solves 9b30e358)

### Regression
- 08ed6ac7: CORRECT
- 705a3229: CORRECT
- ed98d772: CORRECT
- 93b581b8: CORRECT
- 9b30e358: CORRECT

### Prior session: 20/40 (50.0%) — added 4 new concepts, expect ~24/40 (60%)

---
## Session 45 (Claude) -- 2026-04-06

### Results
- **20/20 (100%)** — perfect run, no failing tasks
- All 19 stored rules reused successfully, 1 new rule discovered (reassemble_template_at_markers from Session 44)
- Regression: 08ed6ac7 CORRECT

### Notes
- No changes needed this session — all tasks solved via memory hits or pipeline discovery

---
## Session 44 (Claude) -- 2026-04-06

### Changes
- New primitive `reassemble_template_at_markers` in `_primitives.py` — finds connected template shapes (body color + marker colors) and isolated scattered marker pixels, matches templates to marker groups via all 8 rigid transformations (rotations + reflections), places transformed templates at marker positions
- New concept `reassemble_template_at_markers.json` (solves 0e206a2e)

### Regression
- 08ed6ac7: CORRECT
- 0e206a2e: CORRECT

### Prior session: 19/20 (95.0%) — added 1 new concept, expect ~20/20 (100%)

---
## Session 43 (Claude) -- 2026-04-06

### Changes
- New helper `_extract_objects_by_color` in `_primitives.py` — same-color connected component detection (unlike `extract_objects` which groups all non-bg neighbors)
- New primitive `scattered_pixel_diamond` in `_primitives.py` — counts two non-bg colors, builds a rectangle (min_count × max_count) in the bottom-left of the output filled with color 2, with an hourglass/diamond pattern of color 4
- New concept `scattered_pixel_diamond.json` (solves 878187ab)
- New primitive `middle_object_pass_through` in `_primitives.py` — finds 3 objects on a common axis, passes the middle object through the rectangular outer one (which splits), other stays unchanged
- New concept `middle_object_pass_through.json` (solves 9f669b64)

### Regression
- 08ed6ac7: CORRECT
- 878187ab: CORRECT
- 9f669b64: CORRECT

### Prior session: 17/20 (85.0%) — added 2 new concepts, expect ~19/20 (95%)

---
## Session 42 (Claude) -- 2026-04-06

### Changes
- New primitive `arrow_border_project` in `_primitives.py` — finds arrow-shaped objects with marker cells, projects marker colors to grid borders with dotted trails every 2 cells, fills border edges, and marks corner intersections as 0
- New concept `arrow_border_project.json` (solves 13f06aa5)
- New primitive `block_grid_gravity` in `_primitives.py` — parses 30x30 grids containing 7x7 grids of 3x3 hollow blocks with a separator edge, compresses block presence into a small output using gravity (direction determined by separator position rotated 90° CW)
- New concept `block_grid_gravity.json` (solves afe3afe9)

### Regression
- 08ed6ac7: CORRECT
- 13f06aa5: CORRECT
- afe3afe9: CORRECT

### Prior session: 15/20 (75.0%) — added 2 new concepts, expect ~17/20 (85%)

---
## Session 41 (Claude) -- 2026-04-06

### Changes
- New primitive `quadrant_shape_swap` in `_primitives.py` — swaps shapes between horizontally adjacent quadrant pairs (divided by separator lines), recoloring each shape to the source quadrant's background color
- New concept `quadrant_shape_swap.json` (solves 5a719d11)
- New concept `mirror_trail_across_separator.json` (solves c9680e90) — uses existing primitive, just needed the concept JSON wiring

### Regression
- 08ed6ac7: CORRECT
- 5a719d11: CORRECT
- c9680e90: CORRECT

### Prior session: 11/20 (55.0%) — added 2 new concepts, expect ~13/20 (65%)

---
## Session 40 (Claude) -- 2026-04-06

### Changes
- New primitive `connect_aligned_diamonds` in `_primitives.py` — detects hollow 3x3 diamond shapes, connects axis-aligned nearest-neighbor pairs with blue (1) bridges
- New primitive `l_path_chain` in `_primitives.py` — draws L-shaped paths from source (3) through targets: 6 = clockwise turn, 8 = counterclockwise turn, continues to edge after last target
- New concept `connect_aligned_diamonds.json` (solves 60a26a3e)
- New concept `l_path_chain.json` (solves e5790162)

### Regression
- 08ed6ac7: CORRECT
- 60a26a3e: CORRECT
- e5790162: CORRECT

### Prior session: 9/20 (45.0%) — added 2 new concepts, expect ~11/20 (55%)

---
## Session 39 (Claude) -- 2026-04-05

### Changes
- Restored concept `reverse_concentric_rings` (solves 85c4e7cd) — concept JSON was lost when concepts dir was emptied
- Restored concept `separator_axis_zone_fill` (solves 332202d5) — concept JSON was lost
- Restored concept `fill_quadrants_from_corners` (solves e9ac8c9e) — concept JSON was lost
- Restored concept `fill_bordered_rectangles_by_size` (solves c0f76784) — concept JSON was lost
- Fixed `fill_bordered_rectangles_by_size` primitive: changed fill color from relative ranking to absolute formula (border_color + interior_side_length) so it works consistently when not all rectangle sizes are present

### Regression
- 08ed6ac7: CORRECT
- 85c4e7cd: CORRECT
- 332202d5: CORRECT
- e9ac8c9e: CORRECT
- c0f76784: CORRECT

### Prior session: 5/20 (25.0%) — restored 4 concepts, expect ~9/20 (45%)

---
## Learning Loop -- 2026-04-05 23:50

- Split: training, Tasks: 20
- Correct: 2 / 20 (10.0%)
- Rules: 3 -> 4 (+1 learned)
- Stored rule hits: 1
- Time: 154s
- Log: logs/learn_20260405_233743.log

---
## Session 38 (Claude) -- 2026-04-05

### Changes
- New concept: `mirror_vertical_concat` — stack input on top of flip_vertical(input). Solves 8be77c9e.
- New concept: `recolor_objects_by_size` — recolor connected components by size rank (largest=1, next=2, etc.). Solves 6e82a1ae.
- New concept: `keep_center_column` — keep only center column (W//2), zero everything else. Solves d23f8c26.
- New primitive: `keep_densest_column` in `_primitives.py` (unused by current concepts, available for future use).

### Regression
- 08ed6ac7: CORRECT
- 8be77c9e: CORRECT
- 6e82a1ae: CORRECT
- d23f8c26: CORRECT

---
## Session 35 (Claude) -- 2026-04-05

### Changes
- Recreated `procedural_memory/concepts/recolor_columns_by_height.json` (was deleted; fixes regression gate 08ed6ac7)
- Created `procedural_memory/concepts/scale_uniform.json` — uniform integer scaling (e.g., 2x2 per cell); solves c59eb873
- Created `procedural_memory/concepts/staircase_fill.json` — builds staircase from 1-row input, each row adds one more colored cell; solves bbc9ae5d

### Results
- Prior session: 0/20 (0.0%) — concepts dir was empty (all deleted)
- New concepts: 3 (1 restored, 2 new)
- Tasks verified: c59eb873 CORRECT, bbc9ae5d CORRECT
- Regression: CORRECT (08ed6ac7)

---
## Session 32 (Claude) -- 2026-04-05

### Changes
- Added `reverse_concentric_rings` primitive to `_primitives.py` — detects nested rectangular color frames and reverses their order (innermost becomes outermost)
- Added `separator_axis_zone_fill` primitive to `_primitives.py` — fills zones between separator rows with nearest separator color, axis column gets intersection color, boundaries at midpoints between different-color separators
- Created `procedural_memory/concepts/reverse_concentric_rings.json` (solves 85c4e7cd)
- Created `procedural_memory/concepts/separator_axis_zone_fill.json` (solves 332202d5)

### Results
- Split: training, Tasks: 20
- Correct: 9 / 20 (45.0%) — up from 7/20 (35.0%)
- Rules: 8 -> 10 (+2 learned)
- Regression: CORRECT (08ed6ac7)

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

---
## Learning Loop -- 2026-04-05 19:27

- Split: training, Tasks: 40
- Correct: 40 / 40 (100.0%)
- Rules: 20 -> 40 (+20 learned)
- Stored rule hits: 20
- Time: 107s
- Log: logs/learn_20260405_192520.log

---
## Learning Loop -- 2026-04-05 19:30

- Split: training, Tasks: 5
- Correct: 0 / 5 (0.0%)
- Rules: 42 -> 42 (+0 learned)
- Stored rule hits: 0
- Time: 10s
- Log: logs/learn_20260405_193028.log

---
## Learning Loop -- 2026-04-05 19:31

- Split: training, Tasks: 3
- Correct: 0 / 3 (0.0%)
- Rules: 0 -> 0 (+0 learned)
- Stored rule hits: 0
- Time: 4s
- Log: logs/learn_20260405_193112.log

---
## Learning Loop -- 2026-04-05 19:36

- Split: training, Tasks: 20
- Correct: 0 / 20 (0.0%)
- Rules: 0 -> 0 (+0 learned)
- Stored rule hits: 0
- Time: 48s
- Log: logs/learn_20260405_193518.log

---
## Learning Loop -- 2026-04-05 20:04

- Split: training, Tasks: 2
- Correct: 0 / 2 (0.0%)
- Rules: 1 -> 1 (+0 learned)
- Stored rule hits: 0
- Time: 13s
- Log: logs/learn_20260405_200350.log

---
## Session 32 (Claude) -- 2026-04-05 20:15

### Changes
- Created `procedural_memory/concepts/scale_uniform.json` — scale each cell into factor x factor block (solves c59eb873)
- Added `staircase_fill` primitive to `_primitives.py` — builds staircase from 1-row input with incrementing fill
- Added `first_nonzero_color` primitive to `_primitives.py` — returns first non-zero color from grid
- Created `procedural_memory/concepts/staircase_fill.json` — expands 1-row input into staircase pattern (solves bbc9ae5d)
- Added `recolor_columns_by_height` primitive to `_primitives.py` — recolors vertical columns by height rank
- Created `procedural_memory/concepts/recolor_columns_by_height.json` — recolors columns tallest=1, next=2, etc. (solves 08ed6ac7 regression gate)

### Verified
- c59eb873: CORRECT (scale by 2)
- bbc9ae5d: CORRECT (staircase fill)
- 08ed6ac7: CORRECT (regression gate — was previously broken)

---
## Learning Loop -- 2026-04-05 20:11

- Split: training, Tasks: 3
- Correct: 0 / 3 (0.0%)
- Rules: 1 -> 1 (+0 learned)
- Stored rule hits: 0
- Time: 31s
- Log: logs/learn_20260405_201044.log

---
## Learning Loop -- 2026-04-05 20:19

- Split: training, Tasks: 20
- Correct: 2 / 20 (10.0%)
- Rules: 1 -> 3 (+2 learned)
- Stored rule hits: 1
- Time: 139s
- Log: logs/learn_20260405_201726.log

### Session 32 improvements (2026-04-05)

- Added `recolor_objects_by_size` primitive to `_primitives.py` — finds connected components, recolors by size rank (largest→1, next→2, etc.)
- Created `procedural_memory/concepts/recolor_by_object_size.json` — solves 6e82a1ae, also solves 08ed6ac7 (regression gate)
- Created `procedural_memory/concepts/mirror_vertical_concat.json` — concatenates input with its vertical flip (solves 8be77c9e)
- Created `procedural_memory/concepts/extract_center_column.json` — keeps only center column, zeros rest (solves d23f8c26)

### Verified
- 08ed6ac7: CORRECT (regression gate — now via recolor_by_object_size)
- 8be77c9e: CORRECT (mirror_vertical_concat)
- d23f8c26: CORRECT (extract_center_column)
- 6e82a1ae: CORRECT (recolor_by_object_size)

---
## Session 32 (Claude) -- 2026-04-05 20:30

### Changes
- Added `trace_marker_path` primitive to `_primitives.py` — traces L-shaped paths from a start pixel through direction markers (6=turn down, 8=turn up), filling with path color
- Added `mirror_trail_across_separator` primitive to `_primitives.py` — moves colored pixels along adjacent trail pixels below a separator, mirrors displacement for corresponding pixels above
- Created `procedural_memory/concepts/trace_marker_path.json` (solves e5790162)
- Created `procedural_memory/concepts/mirror_trail_across_separator.json` (solves c9680e90)
- Added inference methods: `marker_down_color`, `marker_up_color`, `trail_color_removed`, `primary_below_sep`, `primary_above_sep` to `_concept_engine.py`
- Fixed `separator_color` inference to exclude bg color (was using `bg=-999`, now uses actual bg)

### Results
- e5790162: CORRECT (trace_marker_path concept matched)
- c9680e90: CORRECT (mirror_trail_across_separator concept matched)
- 08ed6ac7: CORRECT (regression gate passed)
- 878187ab: not attempted (complex diamond/X pattern generation)

---
## Learning Loop -- 2026-04-05 20:30

- Split: training, Tasks: 20
- Correct: 7 / 20 (35.0%)
- Rules: 3 -> 8 (+5 learned)
- Stored rule hits: 2
- Time: 143s
- Log: logs/learn_20260405_202745.log

---
## Learning Loop -- 2026-04-05 20:58

- Split: training, Tasks: 20
- Correct: 9 / 20 (45.0%)
- Rules: 9 -> 11 (+2 learned)
- Stored rule hits: 7
- Time: 137s
- Log: logs/learn_20260405_205638.log

---
## Learning Loop -- 2026-04-05 21:01

- Split: training, Tasks: 20
- Correct: 9 / 20 (45.0%)
- Rules: 11 -> 11 (+0 learned)
- Stored rule hits: 9
- Time: 125s
- Log: logs/learn_20260405_205908.log

---
## Learning Loop -- 2026-04-05 21:03

- Split: training, Tasks: 20
- Correct: 9 / 20 (45.0%)
- Rules: 11 -> 11 (+0 learned)
- Stored rule hits: 9
- Time: 120s
- Log: logs/learn_20260405_210126.log

---
## Learning Loop -- 2026-04-05 21:05

- Split: training, Tasks: 20
- Correct: 9 / 20 (45.0%)
- Rules: 11 -> 11 (+0 learned)
- Stored rule hits: 9
- Time: 116s
- Log: logs/learn_20260405_210339.log

---
## Learning Loop -- 2026-04-05 21:07

- Split: training, Tasks: 20
- Correct: 9 / 20 (45.0%)
- Rules: 11 -> 11 (+0 learned)
- Stored rule hits: 9
- Time: 112s
- Log: logs/learn_20260405_210546.log

---
## Learning Loop -- 2026-04-05 21:38

- Split: training, Tasks: 20
- Correct: 0 / 20 (0.0%)
- Rules: 0 -> 0 (+0 learned)
- Stored rule hits: 0
- Time: 104s
- Log: logs/learn_20260405_213700.log

---
## Learning Loop -- 2026-04-05 21:49

- Split: training, Tasks: 1000
- Correct: 5 / 1000 (0.5%)
- Rules: 0 -> 1 (+1 learned)
- Stored rule hits: 2
- Time: 7696s
- Log: logs/learn_20260405_194136.log

---
## Learning Loop -- 2026-04-05 21:49

- Split: training, Tasks: 1000
- Correct: 5 / 1000 (0.5%)
- Rules: 1 -> 1 (+0 learned)
- Stored rule hits: 5
- Time: 6621s
- Log: logs/learn_20260405_195931.log

---
## Learning Loop -- 2026-04-05 22:13

- Split: training, Tasks: 1000
- Correct: 5 / 1000 (0.5%)
- Rules: 3 -> 7 (+4 learned)
- Stored rule hits: 4
- Time: 6836s
- Log: logs/learn_20260405_201957.log

---
## Learning Loop -- 2026-04-05 22:13

- Split: training, Tasks: 1000
- Correct: 11 / 1000 (1.1%)
- Rules: 8 -> 7 (+-1 learned)
- Stored rule hits: 8
- Time: 6213s
- Log: logs/learn_20260405_203021.log

---
## Learning Loop -- 2026-04-05 22:56

- Split: training, Tasks: 20
- Correct: 9 / 20 (45.0%)
- Rules: 10 -> 10 (+0 learned)
- Stored rule hits: 9
- Time: 60s
- Log: logs/learn_20260405_225503.log

---
## Learning Loop -- 2026-04-05 23:07

- Split: training, Tasks: 20
- Correct: 9 / 20 (45.0%)
- Rules: 11 -> 11 (+0 learned)
- Stored rule hits: 9
- Time: 65s
- Log: logs/learn_20260405_230611.log

---
## Learning Loop -- 2026-04-05 23:18

- Split: training, Tasks: 20
- Correct: 10 / 20 (50.0%)
- Rules: 11 -> 12 (+1 learned)
- Stored rule hits: 9
- Time: 67s
- Log: logs/learn_20260405_231725.log

---
## Learning Loop -- 2026-04-05 23:32

- Split: training, Tasks: 20
- Correct: 0 / 20 (0.0%)
- Rules: 3 -> 3 (+0 learned)
- Stored rule hits: 0
- Time: 155s
- Log: logs/learn_20260405_233008.log

---
## Learning Loop -- 2026-04-05 23:40

- Split: training, Tasks: 20
- Correct: 2 / 20 (10.0%)
- Rules: 3 -> 4 (+1 learned)
- Stored rule hits: 1
- Time: 154s
- Log: logs/learn_20260405_233743.log

---
## Learning Loop -- 2026-04-05 23:47

- Split: training, Tasks: 20
- Correct: 5 / 20 (25.0%)
- Rules: 5 -> 7 (+2 learned)
- Stored rule hits: 3
- Time: 110s
- Log: logs/learn_20260405_234512.log

---
## Learning Loop -- 2026-04-06 00:08

- Split: training, Tasks: 10
- Correct: 3 / 10 (30.0%)
- Rules: 8 -> 10 (+2 learned)
- Stored rule hits: 1
- Time: 45s
- Log: logs/learn_20260406_000755.log

---
## Learning Loop -- 2026-04-06 00:10

- Split: training, Tasks: 10
- Correct: 3 / 10 (30.0%)
- Rules: 10 -> 10 (+0 learned)
- Stored rule hits: 3
- Time: 39s
- Log: logs/learn_20260406_000941.log

---
## Learning Loop -- 2026-04-06 00:11

- Split: training, Tasks: 10
- Correct: 3 / 10 (30.0%)
- Rules: 0 -> 3 (+3 learned)
- Stored rule hits: 0
- Time: 41s
- Log: logs/learn_20260406_001043.log

---
## Learning Loop -- 2026-04-06 00:17

- Split: training, Tasks: 20
- Correct: 9 / 20 (45.0%)
- Rules: 4 -> 10 (+6 learned)
- Stored rule hits: 3
- Time: 98s
- Log: logs/learn_20260406_001553.log

---
## Learning Loop -- 2026-04-06 00:19

- Split: training, Tasks: 20
- Correct: 9 / 20 (45.0%)
- Rules: 10 -> 10 (+0 learned)
- Stored rule hits: 9
- Time: 103s
- Log: logs/learn_20260406_001733.log

---
## Learning Loop -- 2026-04-06 00:19

- Split: training, Tasks: 20
- Correct: 9 / 20 (45.0%)
- Rules: 10 -> 10 (+0 learned)
- Stored rule hits: 9
- Time: 98s
- Log: logs/learn_20260406_001748.log

---
## Learning Loop -- 2026-04-06 00:31

- Split: training, Tasks: 20
- Correct: 11 / 20 (55.0%)
- Rules: 12 -> 14 (+2 learned)
- Stored rule hits: 9
- Time: 82s
- Log: logs/learn_20260406_003035.log

---
## Learning Loop -- 2026-04-06 00:43

- Split: training, Tasks: 20
- Correct: 13 / 20 (65.0%)
- Rules: 15 -> 16 (+1 learned)
- Stored rule hits: 12
- Time: 86s
- Log: logs/learn_20260406_004140.log

---
## Learning Loop -- 2026-04-06 00:47

- Split: training, Tasks: 1000
- Correct: 14 / 1000 (1.4%)
- Rules: 10 -> 16 (+6 learned)
- Stored rule hits: 5
- Time: 6701s
- Log: logs/learn_20260405_225613.log

---
## Learning Loop -- 2026-04-06 00:47

- Split: training, Tasks: 1000
- Correct: 14 / 1000 (1.4%)
- Rules: 11 -> 16 (+5 learned)
- Stored rule hits: 11
- Time: 6028s
- Log: logs/learn_20260405_230726.log

---
## Learning Loop -- 2026-04-06 00:48

- Split: training, Tasks: 20
- Correct: 13 / 20 (65.0%)
- Rules: 16 -> 16 (+0 learned)
- Stored rule hits: 13
- Time: 61s
- Log: logs/learn_20260406_004659.log

---
## Claude Code Session -- 2026-04-06 01:10

- Previous: 13/20 (65.0%)
- Analyzed 7 failing tasks: 878187ab, 0e206a2e, 825aa9e9, 1c56ad9f, 9f669b64, afe3afe9, 13f06aa5
- Solved 2 tasks:
  1. **1c56ad9f** — zigzag horizontal shearing of grid structures
     - New primitive: `zigzag_shear(grid, bg)` — auto-detects phase from bbox height
     - New concept: `zigzag_shear_grid`
  2. **825aa9e9** — gravity of content objects toward border structure
     - New primitive: `gravity_toward_border(grid, bg)` — rigid body drop with gap rule
     - New concept: `gravity_toward_border`
- Also improved `_concept_engine.py` brute-force to support explicit `candidates` lists
- Regression gate (08ed6ac7): CORRECT

---
## Learning Loop -- 2026-04-06 01:11

- Split: training, Tasks: 20
- Correct: 15 / 20 (75.0%)
- Rules: 18 -> 20 (+2 learned)
- Stored rule hits: 13
- Time: 54s
- Log: logs/learn_20260406_011040.log

---
## Learning Loop -- 2026-04-06 01:12

- Split: training, Tasks: 1000
- Correct: 10 / 1000 (1.0%)
- Rules: 7 -> 20 (+13 learned)
- Stored rule hits: 9
- Time: 5126s
- Log: logs/learn_20260405_234722.log

---
## Learning Loop -- 2026-04-06 01:35

- Split: training, Tasks: 20
- Correct: 17 / 20 (85.0%)
- Rules: 20 -> 22 (+2 learned)
- Stored rule hits: 15
- Time: 48s
- Log: logs/learn_20260406_013435.log

---
## Learning Loop -- 2026-04-06 01:46

- Split: training, Tasks: 10
- Correct: 8 / 10 (80.0%)
- Rules: 22 -> 22 (+0 learned)
- Stored rule hits: 8
- Time: 19s
- Log: logs/learn_20260406_014615.log

---
## Learning Loop -- 2026-04-06 01:48

- Split: training, Tasks: 10
- Correct: 8 / 10 (80.0%)
- Rules: 22 -> 22 (+0 learned)
- Stored rule hits: 8
- Time: 19s
- Log: logs/learn_20260406_014743.log

---
## Learning Loop -- 2026-04-06 02:06

- Split: training, Tasks: 20
- Correct: 19 / 20 (95.0%)
- Rules: 22 -> 24 (+2 learned)
- Stored rule hits: 17
- Time: 57s
- Log: logs/learn_20260406_020519.log

---
## Learning Loop -- 2026-04-06 02:18

- Split: training, Tasks: 20
- Correct: 20 / 20 (100.0%)
- Rules: 24 -> 25 (+1 learned)
- Stored rule hits: 19
- Time: 43s
- Log: logs/learn_20260406_021808.log

---
## Learning Loop -- 2026-04-06 02:21

- Split: training, Tasks: 40
- Correct: 20 / 40 (50.0%)
- Rules: 25 -> 25 (+0 learned)
- Stored rule hits: 20
- Time: 103s
- Log: logs/learn_20260406_022005.log

---
## Learning Loop -- 2026-04-06 02:32

- Split: training, Tasks: 20
- Correct: 20 / 20 (100.0%)
- Rules: 25 -> 25 (+0 learned)
- Stored rule hits: 20
- Time: 69s
- Log: logs/learn_20260406_023113.log

---
## Learning Loop -- 2026-04-06 02:33

- Split: training, Tasks: 20
- Correct: 20 / 20 (100.0%)
- Rules: 0 -> 20 (+20 learned)
- Stored rule hits: 0
- Time: 72s
- Log: logs/learn_20260406_023231.log

---
## Learning Loop -- 2026-04-06 02:54

- Split: training, Tasks: 40
- Correct: 24 / 40 (60.0%)
- Rules: 20 -> 24 (+4 learned)
- Stored rule hits: 20
- Time: 92s
- Log: logs/learn_20260406_025251.log

---
## Learning Loop -- 2026-04-06 03:02

- Split: training, Tasks: 40
- Correct: 27 / 40 (67.5%)
- Rules: 25 -> 28 (+3 learned)
- Stored rule hits: 24
- Time: 119s
- Log: logs/learn_20260406_030059.log

---
## Learning Loop -- 2026-04-06 03:10

- Split: training, Tasks: 40
- Correct: 29 / 40 (72.5%)
- Rules: 28 -> 30 (+2 learned)
- Stored rule hits: 27
- Time: 118s
- Log: logs/learn_20260406_030833.log

---
## Learning Loop -- 2026-04-06 03:27

- Split: training, Tasks: 1000
- Correct: 25 / 1000 (2.5%)
- Rules: 25 -> 31 (+6 learned)
- Stored rule hits: 24
- Time: 3955s
- Log: logs/learn_20260406_022157.log

---
## Learning Loop -- 2026-04-06 03:27

- Split: training, Tasks: 1000
- Correct: 25 / 1000 (2.5%)
- Rules: 25 -> 31 (+6 learned)
- Stored rule hits: 24
- Time: 3629s
- Log: logs/learn_20260406_022722.log

---
## Learning Loop -- 2026-04-06 03:43

- Split: training, Tasks: 40
- Correct: 32 / 40 (80.0%)
- Rules: 31 -> 34 (+3 learned)
- Stored rule hits: 29
- Time: 103s
- Log: logs/learn_20260406_034155.log

---
## Learning Loop -- 2026-04-06 04:14

- Split: training, Tasks: 1000
- Correct: 36 / 1000 (3.6%)
- Rules: 30 -> 34 (+4 learned)
- Stored rule hits: 37
- Time: 3855s
- Log: logs/learn_20260406_031039.log

---
## Learning Loop -- 2026-04-06 04:17

- Split: training, Tasks: 40
- Correct: 34 / 40 (85.0%)
- Rules: 34 -> 36 (+2 learned)
- Stored rule hits: 32
- Time: 118s
- Log: logs/learn_20260406_041535.log

---
## Session 51 (Claude) -- 2026-04-06

### Changes

1. **New primitive: `compress_grid_intersections`** (`_primitives.py`)
   - Detects separator-grid patterns (rows/cols with no bg cells)
   - Extracts colored intersections from separator grid
   - Compresses NxN bounding box to (N-1)x(N-1) via agreement regions
   - Solves task `7837ac64`

2. **New concept: `compress_grid_intersections.json`**
   - Signature: size not preserved, content diff required
   - Single-step concept using the new primitive

3. **New primitive: `denoise_swap_sections`** (`_primitives.py`)
   - Detects sections separated by 0-rows/cols (handles 5-noise on separators)
   - Identifies pattern template from clean sections with 2+ colors
   - Swaps: sections where all non-5 cells are minority color get the pattern; others become solid base color
   - Solves task `6350f1f4`

4. **New concept: `denoise_swap_sections.json`**
   - Signature: size preserved, content diff required
   - Zero-parameter concept (auto-detects everything)

### Results

- Previous: 34/40 (85.0%)
- New tasks solved: 7837ac64, 6350f1f4
- Regression gate (08ed6ac7): CORRECT

---
## Learning Loop -- 2026-04-06 04:48

- Split: training, Tasks: 40
- Correct: 36 / 40 (90.0%)
- Rules: 36 -> 38 (+2 learned)
- Stored rule hits: 34
- Time: 109s
- Log: logs/learn_20260406_044628.log

---
## Learning Loop -- 2026-04-06 04:50

- Split: training, Tasks: 1000
- Correct: 41 / 1000 (4.1%)
- Rules: 34 -> 38 (+4 learned)
- Stored rule hits: 42
- Time: 3997s
- Log: logs/learn_20260406_034346.log

---
## Learning Loop -- 2026-04-06 04:56

- Split: training, Tasks: 40
- Correct: 2 / 40 (5.0%)
- Rules: 38 -> 38 (+0 learned)
- Stored rule hits: 2
- Time: 142s
- Log: logs/learn_20260406_045346.log

---
## Learning Loop -- 2026-04-06 04:58

- Split: training, Tasks: 40
- Correct: 2 / 40 (5.0%)
- Rules: 38 -> 38 (+0 learned)
- Stored rule hits: 2
- Time: 135s
- Log: logs/learn_20260406_045626.log

---
## Learning Loop -- 2026-04-06 05:22

- Split: training, Tasks: 40
- Correct: 38 / 40 (95.0%)
- Rules: 39 -> 41 (+2 learned)
- Stored rule hits: 36
- Time: 112s
- Log: logs/learn_20260406_052018.log

---
## Learning Loop -- 2026-04-06 05:30

- Split: training, Tasks: 40
- Correct: 2 / 40 (5.0%)
- Rules: 41 -> 42 (+1 learned)
- Stored rule hits: 2
- Time: 162s
- Log: logs/learn_20260406_052810.log

---
## Learning Loop -- 2026-04-06 05:33

- Split: training, Tasks: 40
- Correct: 2 / 40 (5.0%)
- Rules: 42 -> 42 (+0 learned)
- Stored rule hits: 2
- Time: 163s
- Log: logs/learn_20260406_053056.log

---
## Learning Loop -- 2026-04-06 05:36

- Split: training, Tasks: 40
- Correct: 38 / 40 (95.0%)
- Rules: 42 -> 42 (+0 learned)
- Stored rule hits: 38
- Time: 155s
- Log: logs/learn_20260406_053424.log

---
## Learning Loop -- 2026-04-06 05:55

- Split: training, Tasks: 1000
- Correct: 50 / 1000 (5.0%)
- Rules: 38 -> 43 (+5 learned)
- Stored rule hits: 48
- Time: 4001s
- Log: logs/learn_20260406_044826.log

---
## Learning Loop -- 2026-04-06 05:57

- Split: training, Tasks: 40
- Correct: 40 / 40 (100.0%)
- Rules: 43 -> 45 (+2 learned)
- Stored rule hits: 38
- Time: 132s
- Log: logs/learn_20260406_055509.log

---
## Learning Loop -- 2026-04-06 06:04

- Split: training, Tasks: 80
- Correct: 41 / 80 (51.2%)
- Rules: 45 -> 45 (+0 learned)
- Stored rule hits: 41
- Time: 246s
- Log: logs/learn_20260406_060017.log

---
## Learning Loop -- 2026-04-06 06:39

- Split: training, Tasks: 1000
- Correct: 52 / 1000 (5.2%)
- Rules: 41 -> 45 (+4 learned)
- Stored rule hits: 53
- Time: 4603s
- Log: logs/learn_20260406_052222.log

---
## Learning Loop -- 2026-04-06 06:42

- Split: training, Tasks: 80
- Correct: 45 / 80 (56.2%)
- Rules: 45 -> 48 (+3 learned)
- Stored rule hits: 42
- Time: 285s
- Log: logs/learn_20260406_063753.log

---
## Learning Loop -- 2026-04-06 07:22

- Split: training, Tasks: 80
- Correct: 48 / 80 (60.0%)
- Rules: 48 -> 51 (+3 learned)
- Stored rule hits: 45
- Time: 335s
- Log: logs/learn_20260406_071632.log

---
## Learning Loop -- 2026-04-06 07:29

- Split: training, Tasks: 1000
- Correct: 54 / 1000 (5.4%)
- Rules: 45 -> 51 (+6 learned)
- Stored rule hits: 55
- Time: 5106s
- Log: logs/learn_20260406_060435.log

---
## Learning Loop -- 2026-04-06 08:05

- Split: training, Tasks: 80
- Correct: 50 / 80 (62.5%)
- Rules: 51 -> 53 (+2 learned)
- Stored rule hits: 48
- Time: 496s
- Log: logs/learn_20260406_075719.log

---
## Learning Loop -- 2026-04-06 08:23

- Split: training, Tasks: 1000
- Correct: 59 / 1000 (5.9%)
- Rules: 48 -> 53 (+5 learned)
- Stored rule hits: 60
- Time: 6046s
- Log: logs/learn_20260406_064248.log

---
## Learning Loop -- 2026-04-06 08:48

- Split: training, Tasks: 80
- Correct: 53 / 80 (66.2%)
- Rules: 53 -> 56 (+3 learned)
- Stored rule hits: 50
- Time: 434s
- Log: logs/learn_20260406_084114.log

---
## Session 56 (Claude) -- 2026-04-06

### Changes
- New primitive: `dual_mask_intersection` — split grid into two halves, mark positions where both are background. Solves e345f17b.
- New primitive: `staircase_from_bar` — expand staircase above/below a horizontal bar of color 2. Solves a65b410d.
- New primitive: `panel_hole_classify` — classify hole positions in 3 separated panels, map each to a color. Solves 995c5fa3.
- New concepts: `dual_mask_intersection.json`, `staircase_from_bar.json`, `panel_hole_classify.json`

### Regression
- 08ed6ac7: CORRECT
- e345f17b: CORRECT
- a65b410d: CORRECT
- 995c5fa3: CORRECT

---
## Learning Loop -- 2026-04-06 09:06

- Split: training, Tasks: 80
- Correct: 56 / 80 (70.0%)
- Rules: 56 -> 59 (+3 learned)
- Stored rule hits: 53
- Time: 351s
- Log: logs/learn_20260406_090023.log

---
## Learning Loop -- 2026-04-06 09:17

- Split: training, Tasks: 1000
- Correct: 62 / 1000 (6.2%)
- Rules: 51 -> 59 (+8 learned)
- Stored rule hits: 64
- Time: 6913s
- Log: logs/learn_20260406_072220.log

---
## Learning Loop -- 2026-04-06 09:45

- Split: training, Tasks: 80
- Correct: 58 / 80 (72.5%)
- Rules: 59 -> 61 (+2 learned)
- Stored rule hits: 56
- Time: 300s
- Log: logs/learn_20260406_094015.log

---
## Learning Loop -- 2026-04-06 09:51

- Split: training, Tasks: 1000
- Correct: 65 / 1000 (6.5%)
- Rules: 53 -> 61 (+8 learned)
- Stored rule hits: 67
- Time: 6362s
- Log: logs/learn_20260406_080550.log

---
## Learning Loop -- 2026-04-06 10:25

- Split: training, Tasks: 80
- Correct: 60 / 80 (75.0%)
- Rules: 61 -> 63 (+2 learned)
- Stored rule hits: 58
- Time: 326s
- Log: logs/learn_20260406_101955.log

---
## Learning Loop -- 2026-04-06 10:36

- Split: training, Tasks: 1000
- Correct: 72 / 1000 (7.2%)
- Rules: 59 -> 63 (+4 learned)
- Stored rule hits: 74
- Time: 5403s
- Log: logs/learn_20260406_090625.log

---
## Learning Loop -- 2026-04-06 11:04

- Split: training, Tasks: 80
- Correct: 63 / 80 (78.8%)
- Rules: 63 -> 66 (+3 learned)
- Stored rule hits: 60
- Time: 292s
- Log: logs/learn_20260406_105937.log

---
## Learning Loop -- 2026-04-06 11:12

- Split: training, Tasks: 1000
- Correct: 74 / 1000 (7.4%)
- Rules: 61 -> 66 (+5 learned)
- Stored rule hits: 76
- Time: 5201s
- Log: logs/learn_20260406_094525.log

---
## Learning Loop -- 2026-04-06 11:42

- Split: training, Tasks: 80
- Correct: 63 / 80 (78.8%)
- Rules: 66 -> 66 (+0 learned)
- Stored rule hits: 63
- Time: 262s
- Log: logs/learn_20260406_113809.log

---
## Learning Loop -- 2026-04-06 11:47

- Split: training, Tasks: 1000
- Correct: 77 / 1000 (7.7%)
- Rules: 63 -> 69 (+6 learned)
- Stored rule hits: 79
- Time: 4902s
- Log: logs/learn_20260406_102531.log

---
## Learning Loop -- 2026-04-06 12:23

- Split: training, Tasks: 80
- Correct: 63 / 80 (78.8%)
- Rules: 69 -> 69 (+0 learned)
- Stored rule hits: 63
- Time: 356s
- Log: logs/learn_20260406_121748.log

---
## Learning Loop -- 2026-04-06 12:29

- Split: training, Tasks: 1000
- Correct: 80 / 1000 (8.0%)
- Rules: 66 -> 69 (+3 learned)
- Stored rule hits: 82
- Time: 5120s
- Log: logs/learn_20260406_110439.log

---
## Learning Loop -- 2026-04-06 13:05

- Split: training, Tasks: 80
- Correct: 63 / 80 (78.8%)
- Rules: 70 -> 70 (+0 learned)
- Stored rule hits: 63
- Time: 400s
- Log: logs/learn_20260406_125915.log

---
## Learning Loop -- 2026-04-06 13:27

- Split: training, Tasks: 1000
- Correct: 83 / 1000 (8.3%)
- Rules: 66 -> 70 (+4 learned)
- Stored rule hits: 82
- Time: 6288s
- Log: logs/learn_20260406_114242.log

---
## Learning Loop -- 2026-04-06 13:41

- Split: training, Tasks: 80
- Correct: 64 / 80 (80.0%)
- Rules: 70 -> 71 (+1 learned)
- Stored rule hits: 63
- Time: 199s
- Log: logs/learn_20260406_133829.log

---
## Learning Loop -- 2026-04-06 14:18

- Split: training, Tasks: 80
- Correct: 64 / 80 (80.0%)
- Rules: 73 -> 73 (+0 learned)
- Stored rule hits: 64
- Time: 206s
- Log: logs/learn_20260406_141441.log

---
## Learning Loop -- 2026-04-06 14:45

- Split: training, Tasks: 1000
- Correct: 86 / 1000 (8.6%)
- Rules: 71 -> 76 (+5 learned)
- Stored rule hits: 87
- Time: 3818s
- Log: logs/learn_20260406_134200.log
