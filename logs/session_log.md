
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
