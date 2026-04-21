# SOAR-ARC Session Log

---
## Learning Loop -- 2026-04-21 18:05

- Split: training, Tasks: 20
- Correct: 0 / 20 (0.0%)
- Rules: 0 -> 3 (+3 learned)
- Stored rule hits: 0
- Time: 65s
- Log: logs/learn_20260421_180356.log

---
## Session 1 -- 2026-04-21 18:14

### Strategies Added
1. **uniform_scale** — output is NxN block scale-up of input (solves c59eb873)
2. **recolor_by_size** — connected components of one color recolored by size rank (solves 6e82a1ae)
3. **corner_fill** — rectangle of fill color + 4 corner markers → quadrant fill (solves e9ac8c9e)

### Learning Loop Results
- Split: training, Tasks: 20
- Correct: 3 / 20 (15.0%) — up from 0/20
- Solved: e9ac8c9e (corner_fill), 6e82a1ae (recolor_by_size), c59eb873 (uniform_scale)
- Rules: 3 -> 8 (+5 learned)
- Stored rule hits: 0
- Time: 64s
- Log: logs/learn_20260421_181336.log
- Regression: 08ed6ac7 CORRECT

---
## Learning Loop -- 2026-04-21 18:16

- Split: training, Tasks: 20
- Correct: 3 / 20 (15.0%)
- Rules: 8 -> 10 (+2 learned)
- Stored rule hits: 3
- Time: 64s
- Log: logs/learn_20260421_181517.log

---
## Session 2 -- 2026-04-21 18:26

### Strategies Added
1. **vertical_mirror** — output = input rows + reversed input rows (solves 8be77c9e)
2. **fill_rect_by_size** — rectangular frames with hollow interiors filled by interior dimension: 1→6, 2→7, 3→8 (solves c0f76784)
3. **staircase_growth** — single row with K colored cells expands to W/2 rows, each row adding one cell (solves bbc9ae5d)

### Learning Loop Results
- Split: training, Tasks: 20
- Correct: 6 / 20 (30.0%) — up from 3/20
- Solved: e9ac8c9e, 6e82a1ae, c59eb873 (stored), c0f76784 (fill_rect_by_size), 8be77c9e (vertical_mirror), bbc9ae5d (staircase_growth)
- Rules: 10 -> 15 (+5 learned)
- Stored rule hits: 3
- Time: 55s
- Log: logs/learn_20260421_182507.log
- Regression: 08ed6ac7 CORRECT

---
## Learning Loop -- 2026-04-21 18:27

- Split: training, Tasks: 20
- Correct: 6 / 20 (30.0%)
- Rules: 15 -> 17 (+2 learned)
- Stored rule hits: 6
- Time: 55s
- Log: logs/learn_20260421_182633.log

---
## Session 3 -- 2026-04-21 18:35

### Strategies Added
1. **reverse_concentric_rings** — concentric rectangular rings of uniform color; output reverses the ring order innermost ↔ outermost (solves 85c4e7cd)
2. **keep_center_column** — output preserves only the center column of the input grid, zeroing all other cells (solves d23f8c26)

### Learning Loop Results
- Split: training, Tasks: 20
- Correct: 8 / 20 (40.0%) — up from 6/20
- Solved: e9ac8c9e, c0f76784, 8be77c9e, 6e82a1ae, c59eb873, bbc9ae5d (stored), d23f8c26 (keep_center_column), 85c4e7cd (reverse_concentric_rings)
- Rules: 17 -> 20 (+3 learned)
- Stored rule hits: 6
- Time: 65s
- Log: logs/learn_20260421_183518.log
- Regression: 08ed6ac7 CORRECT

---
## Learning Loop -- 2026-04-21 18:38

- Split: training, Tasks: 20
- Correct: 8 / 20 (40.0%)
- Rules: 20 -> 21 (+1 learned)
- Stored rule hits: 8
- Time: 63s
- Log: logs/learn_20260421_183705.log

---
## Session 4 -- 2026-04-21 19:11

### Strategies Added
1. **path_trace** — start marker (3) traces L-shaped paths toward turn markers; color 6 = clockwise turn, color 8 = counter-clockwise turn (solves e5790162)
2. **diamond_connect** — diamond shapes (+ pattern of 4 cells around empty center) on same row/column are connected by lines of connector color between facing tips (solves 60a26a3e)
3. **cross_grid_fill** — grid with a colored column axis and colored horizontal rows; output fills band regions with nearest row's color, axis/rows become intersection color (solves 332202d5)

### Learning Loop Results
- Split: training, Tasks: 20
- Correct: 11 / 20 (55.0%) — up from 8/20
- Solved: e9ac8c9e, c0f76784, 8be77c9e, 6e82a1ae, c59eb873, bbc9ae5d, d23f8c26, 85c4e7cd (stored), e5790162 (path_trace), 60a26a3e (diamond_connect), 332202d5 (cross_grid_fill)
- Rules: 24 -> 25 (+1 learned)
- Stored rule hits: 10
- Time: 66s
- Log: logs/learn_20260421_191025.log
- Regression: 08ed6ac7 CORRECT

---
## Learning Loop -- 2026-04-21 19:13

- Split: training, Tasks: 20
- Correct: 11 / 20 (55.0%)
- Rules: 25 -> 25 (+0 learned)
- Stored rule hits: 11
- Time: 66s
- Log: logs/learn_20260421_191212.log

---
## Session 5 -- 2026-04-21 19:30

### Strategies Added
1. **trail_displacement** — grid split by separator row; active cells slide along adjacent trail-marker chains, target cells in the mirrored half apply the same displacement with vertical component negated (solves c9680e90)
2. **zigzag_warp** — rectangular frame on zero background; each row shifts horizontally in a [0, -1, 0, +1] cycle whose starting phase = (1 - internal_rows) % 4 (solves 1c56ad9f)

### Learning Loop Results
- Split: training, Tasks: 20
- Correct: 13 / 20 (65.0%) — up from 11/20
- Solved: e9ac8c9e, c0f76784, 8be77c9e, 6e82a1ae, c59eb873, bbc9ae5d, d23f8c26, 85c4e7cd, e5790162, 60a26a3e, 332202d5 (stored), c9680e90 (trail_displacement), 1c56ad9f (zigzag_warp)
- Rules: 25 -> 27 (+2 learned)
- Stored rule hits: 11
- Time: 68s
- Log: logs/learn_20260421_193101.log
- Regression: 08ed6ac7 CORRECT

---
## Learning Loop -- 2026-04-21 19:36

- Split: training, Tasks: 20
- Correct: 13 / 20 (65.0%)
- Rules: 27 -> 27 (+0 learned)
- Stored rule hits: 13
- Time: 70s
- Log: logs/learn_20260421_193514.log

---
## Session 6 -- 2026-04-21 20:24

### Strategies Added
1. **gravity_slide** — grid has 3 colors (bg, wall, object); wall forms stepped boundary; object components slide down toward wall, stopping 1 row before contact; stacked objects touch directly (solves 825aa9e9)
2. **arrow_projection** — shapes have a core color and a single special-color cell; the special cell projects a ray (every 2 cells) toward the nearest grid edge, filling that entire edge with the special color; corners where two borders meet become 0 (solves 13f06aa5)

### Learning Loop Results
- Split: training, Tasks: 20
- Correct: 15 / 20 (75.0%) — up from 13/20
- Solved: e9ac8c9e, c0f76784, 8be77c9e, 6e82a1ae, c59eb873, bbc9ae5d, d23f8c26, 85c4e7cd, e5790162, 60a26a3e, 332202d5, c9680e90, 1c56ad9f (stored), 825aa9e9 (gravity_slide), 13f06aa5 (arrow_projection)
- Rules: 29 -> 29 (+0 learned)
- Stored rule hits: 15
- Time: 63s
- Log: logs/learn_20260421_202308.log
- Regression: 08ed6ac7 CORRECT
