
---
## Learning Loop -- 2026-03-25 14:40

- Split: training, Tasks: 20
- Correct: 0 / 20 (0.0%)
- Rules: 0 -> 3 (+3 learned)
- Stored rule hits: 0
- Time: 64s
- Log: logs/learn_20260325_143938.log

---
## Session 1 -- 2026-03-25 14:48

**Strategies added:**
1. `pixel_scaling` -- each input pixel becomes an NxN block (2x upscale, etc.)
2. `tile_reflect` -- output is tiled/reflected copies of input (vertical flip concat, 2x2 tiling, etc.)
3. `recolor_by_size` -- single-color objects recolored by size ranking (largest=1, 2nd=2, 3rd=3)

**Tasks solved:** c59eb873 (pixel_scaling), 8be77c9e (tile_reflect), 6e82a1ae (recolor_by_size)

**Results:** 0/20 (0.0%) -> 3/20 (15.0%)

- Split: training, Tasks: 20
- Correct: 3 / 20 (15.0%)
- Rules: 3 -> 8 (+5 learned)
- Stored rule hits: 0
- Time: 55s
- Log: logs/learn_20260325_144743.log

---
## Learning Loop -- 2026-03-25 14:50

- Split: training, Tasks: 20
- Correct: 3 / 20 (15.0%)
- Rules: 8 -> 10 (+2 learned)
- Stored rule hits: 3
- Time: 54s
- Log: logs/learn_20260325_144922.log

---
## Session 2 -- 2026-03-25 15:03

**Strategies added:**
1. `corner_quadrant_fill` -- rectangular placeholder block (e.g. all 5s) with 4 diagonal corner markers; replace block with colored quadrants matching each corner
2. `frame_fill_by_size` -- hollow rectangular frames (border of one color, interior 0s); fill interior based on side length (color = frame_color + side_length)
3. `staircase_growth` -- single-row input with C colored cells grows into (W/2) rows, each adding one more colored cell (1D -> 2D incremental triangle)

**Tasks solved:** e9ac8c9e (corner_quadrant_fill), c0f76784 (frame_fill_by_size), bbc9ae5d (staircase_growth)

**Results:** 3/20 (15.0%) -> 6/20 (30.0%)

- Split: training, Tasks: 20
- Correct: 6 / 20 (30.0%)
- Rules: 10 -> 15 (+5 learned)
- Stored rule hits: 3
- Time: 63s
- Log: logs/learn_20260325_150302.log

---
## Learning Loop -- 2026-03-25 15:06

- Split: training, Tasks: 20
- Correct: 6 / 20 (30.0%)
- Rules: 15 -> 17 (+2 learned)
- Stored rule hits: 6
- Time: 63s
- Log: logs/learn_20260325_150459.log

---
## Session 3 -- 2026-03-25 15:22

**Strategies added:**
1. `center_column_extract` -- output keeps only the center column (index W//2) of the input grid, zeroing everything else; generalizes to single-axis extraction tasks
2. `concentric_ring_reversal` -- grid of concentric rectangular rings with uniform colors per ring; output reverses the ring color order (outermost↔innermost)
3. `band_section_fill` -- grid with a vertical axis column and horizontal colored separator rows; fills sections between separators with separator colors, turns separators into border rows; axis column position varies per grid

**Tasks solved:** d23f8c26 (center_column_extract), 85c4e7cd (concentric_ring_reversal), 332202d5 (band_section_fill)

**Results:** 6/20 (30.0%) -> 9/20 (45.0%)

- Split: training, Tasks: 20
- Correct: 9 / 20 (45.0%)
- Rules: 20 -> 22 (+2 learned)
- Stored rule hits: 8
- Time: 57s
- Log: logs/learn_20260325_152129.log

---
## Learning Loop -- 2026-03-25 15:24

- Split: training, Tasks: 20
- Correct: 9 / 20 (45.0%)
- Rules: 22 -> 23 (+1 learned)
- Stored rule hits: 9
- Time: 57s
- Log: logs/learn_20260325_152326.log

---
## Session 4 -- 2026-03-25 15:47

**Strategies added:**
1. `path_waypoint` -- draws a path from a start marker (color 3), turning right at one waypoint color (6) and left at another (8) relative to current direction; handles L-shaped paths through multiple waypoints to grid edge
2. `diamond_bridge` -- cross/plus shapes (4 cells around an empty center) of one color; when two crosses' tips align horizontally or vertically with a clear gap, fills the gap with a bridge color (1)
3. `mirror_separator` -- a row of uniform non-background color (e.g. 9) divides the grid; bottom half has object pixels adjacent to arrow pixels defining movement direction (chain-following); top half has mirror pixels at reflected positions that move in the vertically-mirrored direction

**Bugfixes:**
- `recolor_sequential` now rejects patterns where source color is 0 (background); prevents false-matching path/bridge tasks
- `color_mapping` now rejects mappings from color 0; prevents false-matching tasks where new cells are added
- Cleaned 10 stale stored rules from procedural_memory (wrong rules from earlier false matches)

**Tasks solved:** e5790162 (path_waypoint), 60a26a3e (diamond_bridge), c9680e90 (mirror_separator)

**Results:** 9/20 (45.0%) -> 12/20 (60.0%)

- Split: training, Tasks: 20
- Correct: 12 / 20 (60.0%)
- Rules: 15 -> 16 (+1 learned)
- Stored rule hits: 10
- Time: 57s
- Log: logs/learn_20260325_154652.log
