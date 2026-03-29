
---
## Learning Loop -- 2026-03-29 23:20

- Split: training, Tasks: 20
- Correct: 0 / 20 (0.0%)
- Rules: 0 -> 3 (+3 learned)
- Stored rule hits: 0
- Time: 42s
- Log: logs/learn_20260329_232016.log

---
## Learning Loop -- 2026-03-29 23:25

- Split: training, Tasks: 20
- Correct: 3 / 20 (15.0%)
- Rules: 3 -> 7 (+4 learned)
- Stored rule hits: 0
- Time: 36s
- Log: logs/learn_20260329_232522.log

### Session 1 Analysis (Claude Code)

**New rules added (3):**
1. `mirror_vertical_append` (geometry) — input stacked with its vertical flip → solved 8be77c9e
2. `recolor_by_size` (color) — components recolored 1,2,3 by descending size rank → solved 6e82a1ae
3. `extract_center_column` (structure) — keep only center column, zero rest → solved d23f8c26

**Improvement:** 0/20 → 3/20 (0% → 15%)

---
## Learning Loop -- 2026-03-29 23:32

- Split: training, Tasks: 20
- Correct: 3 / 20 (15.0%)
- Rules: 0 -> 5 (+5 learned)
- Stored rule hits: 0
- Time: 45s
- Log: logs/learn_20260329_233130.log

---
## Learning Loop -- 2026-03-29 23:34

- Split: training, Tasks: 20
- Correct: 6 / 20 (30.0%)
- Rules: 5 -> 9 (+4 learned)
- Stored rule hits: 3
- Time: 36s
- Log: logs/learn_20260329_233356.log

### Session 2 Analysis (Claude Code)

**New rules added (3):**
1. `scale_up` (geometry) — each pixel scaled to NxN block (detects integer scale factor) → solved c59eb873
2. `staircase_fill` (fill) — 1-row colored prefix grows into descending staircase triangle → solved bbc9ae5d
3. `reverse_frames` (structure) — concentric rectangular frames get color order reversed → solved 85c4e7cd

**Improvement:** 3/20 → 6/20 (15% → 30%)
**Memory reuse:** 3 stored rules successfully reused (mirror_vertical_append, extract_center_column, recolor_by_size)

---
## Learning Loop -- 2026-03-29 23:35

- Split: training, Tasks: 20
- Correct: 6 / 20 (30.0%)
- Rules: 9 -> 10 (+1 learned)
- Stored rule hits: 6
- Time: 36s
- Log: logs/learn_20260329_233456.log

---
## Learning Loop -- 2026-03-29 23:40

- Split: training, Tasks: 20
- Correct: 8 / 20 (40.0%)
- Rules: 10 -> 13 (+3 learned)
- Stored rule hits: 6
- Time: 35s
- Log: logs/learn_20260329_233953.log

### Session 3 Analysis (Claude Code)

**New rules added (2):**
1. `quadrant_fill` (fill) — solid rectangle of filler color (e.g. 5) with 4 diagonal corner markers; fills each quadrant with its nearest corner's color → solved e9ac8c9e
2. `fill_by_interior_size` (fill) — hollow rectangles bordered by a single color get interiors filled based on interior dimensions (1x1→6, 2x2→7, 3x3→8) → solved c0f76784

**Improvement:** 6/20 → 8/20 (30% → 40%)
**Memory reuse:** 6 stored rules successfully reused (mirror_vertical_append, extract_center_column, recolor_by_size, reverse_frames, scale_up, staircase_fill)

---
## Learning Loop -- 2026-03-29 23:41

- Split: training, Tasks: 20
- Correct: 8 / 20 (40.0%)
- Rules: 13 -> 14 (+1 learned)
- Stored rule hits: 8
- Time: 36s
- Log: logs/learn_20260329_234100.log

---
## Learning Loop -- 2026-03-29 23:54

- Split: training, Tasks: 20
- Correct: 10 / 20 (50.0%)
- Rules: 14 -> 17 (+3 learned)
- Stored rule hits: 8
- Time: 37s
- Log: logs/learn_20260329_235419.log

### Session 4 Analysis (Claude Code)

**New rules added (2):**
1. `path_with_turns` (connect) — draw L-shaped path from edge source pixel, turning CW at color-6 signals and CCW at color-8 signals; path bounces through a chain of waypoints → solved e5790162
2. `zone_expand` (separator) — grid has a vertical spine column (color 8) and horizontal marker rows; each background row fills with the nearest marker's color (Voronoi); ties between different-colored markers create boundary rows of crossing color → solved 332202d5

**Improvement:** 8/20 → 10/20 (40% → 50%)
**Memory reuse:** 8 stored rules successfully reused (mirror_vertical_append, extract_center_column, recolor_by_size, reverse_frames, scale_up, staircase_fill, quadrant_fill, fill_by_interior_size)

---
## Learning Loop -- 2026-03-29 23:56

- Split: training, Tasks: 20
- Correct: 10 / 20 (50.0%)
- Rules: 17 -> 18 (+1 learned)
- Stored rule hits: 10
- Time: 37s
- Log: logs/learn_20260329_235548.log

---
## Learning Loop -- 2026-03-30 00:05

- Split: training, Tasks: 20
- Correct: 12 / 20 (60.0%)
- Rules: 18 -> 20 (+2 learned)
- Stored rule hits: 10
- Time: 43s
- Log: logs/learn_20260330_000456.log

### Session 5 Analysis (Claude Code)

**New rules added (2):**
1. `connect_diamonds` (connect) — find diamond/cross shapes (4-cell crosses of one color), connect consecutive aligned diamonds (same row or column) with lines of a new color between their tips → solved 60a26a3e
2. `separator_reflect` (separator) — grid split by a uniform-color separator row; below: target dots follow chains of adjacent guide dots to final positions; those positions are reflected across the separator to the top half as mirror-color dots → solved c9680e90

**Improvement:** 10/20 → 12/20 (50% → 60%)
**Memory reuse:** 10 stored rules successfully reused (mirror_vertical_append, extract_center_column, recolor_by_size, reverse_frames, scale_up, staircase_fill, quadrant_fill, fill_by_interior_size, path_with_turns, zone_expand)

---
## Learning Loop -- 2026-03-30 00:07

- Split: training, Tasks: 20
- Correct: 12 / 20 (60.0%)
- Rules: 20 -> 20 (+0 learned)
- Stored rule hits: 12
- Time: 43s
- Log: logs/learn_20260330_000622.log

---
## Learning Loop -- 2026-03-30 00:27

- Split: training, Tasks: 20
- Correct: 14 / 20 (70.0%)
- Rules: 20 -> 22 (+2 learned)
- Stored rule hits: 12
- Time: 37s
- Log: logs/learn_20260330_002720.log

### Session 6 Analysis (Claude Code)

**New rules added (2):**
1. `grid_shear` (geometry) — single-color grid/rectangle structure on bg=0; each row is cyclically shifted left/right following the pattern [-1, 0, +1, 0] with phase=(2-N)%4 where N=row count; bottom bar stays fixed → solved 1c56ad9f
2. `gravity_settle` (geometry) — colored objects (rigid bodies) in separator-bounded cells settle downward with a 1-row gap from the separator floor; separator color varies per task, detected via unchanged positions (train) or bottom-row heuristic (test) → solved 825aa9e9

**Improvement:** 12/20 → 14/20 (60% → 70%)
**Memory reuse:** 12 stored rules successfully reused
