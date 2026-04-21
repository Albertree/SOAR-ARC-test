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

---
## Learning Loop -- 2026-04-21 20:25

- Split: training, Tasks: 20
- Correct: 15 / 20 (75.0%)
- Rules: 29 -> 29 (+0 learned)
- Stored rule hits: 15
- Time: 62s
- Log: logs/learn_20260421_202448.log

---
## Session 7 -- 2026-04-21 20:54

### Strategies Added
1. **quadrant_pattern_swap** — grid divided into sections by separator rows/cols; left and right quadrants swap their foreground patterns, each taking the source quadrant's bg color; if both bg colors match, both patterns are erased (solves 5a719d11)
2. **block_wedge_split** — 3 colored blocks on background; middle block slides into adjacent rectangular block, splitting it into two halves perpendicular to the movement axis; the other block stays as anchor (solves 9f669b64)

### Learning Loop Results
- Split: training, Tasks: 20
- Correct: 17 / 20 (85.0%) — up from 15/20
- Solved: e9ac8c9e, c0f76784, 8be77c9e, 6e82a1ae, c59eb873, bbc9ae5d, d23f8c26, 85c4e7cd, e5790162, 60a26a3e, 332202d5, c9680e90, 1c56ad9f, 825aa9e9, 13f06aa5 (stored), 9f669b64 (block_wedge_split), 5a719d11 (quadrant_pattern_swap)
- Rules: 30 -> 31 (+1 learned)
- Stored rule hits: 16
- Time: 64s
- Log: logs/learn_20260421_205315.log
- Regression: 08ed6ac7 CORRECT

---
## Learning Loop -- 2026-04-21 20:56

- Split: training, Tasks: 20
- Correct: 17 / 20 (85.0%)
- Rules: 31 -> 31 (+0 learned)
- Stored rule hits: 17
- Time: 65s
- Log: logs/learn_20260421_205532.log

---
## Session 8 -- 2026-04-21 21:30

### Strategies Added
1. **block_grid_bar_chart** — large grid of 3×3 block tiles (one section colored, one section 8) with a divider row/column of 1s at one edge; output is a small bar chart where each bar stacks colored-count + eight-count cells, aligned relative to the divider direction (solves afe3afe9)
2. **template_stamp_rotate** — template shapes (body color + marker colors) and groups of scattered marker pixels; output places rotated/reflected template body at each marker group position, determined by finding the rigid transformation (from 8 possible rotations/reflections) that maps template markers to anchor markers (solves 0e206a2e)

### Learning Loop Results
- Split: training, Tasks: 20
- Correct: 19 / 20 (95.0%) — up from 17/20 (85.0%)
- Solved: c9680e90, e5790162, e9ac8c9e, 825aa9e9, 1c56ad9f, c0f76784, 60a26a3e, 8be77c9e, 332202d5, d23f8c26, 6e82a1ae, 9f669b64, 85c4e7cd, c59eb873, 13f06aa5, bbc9ae5d, 5a719d11 (stored), afe3afe9 (block_grid_bar_chart), 0e206a2e (template_stamp_rotate)
- Still failing: 878187ab (complex noise/diamond pattern)
- Rules: 32 -> 33 (+1 learned)
- Stored rule hits: 18
- Time: 65s
- Log: logs/learn_20260421_212918.log
- Regression: 08ed6ac7 CORRECT

---
## Learning Loop -- 2026-04-21 21:32

- Split: training, Tasks: 20
- Correct: 19 / 20 (95.0%)
- Rules: 33 -> 33 (+0 learned)
- Stored rule hits: 19
- Time: 64s
- Log: logs/learn_20260421_213122.log

---
## Session 9 -- 2026-04-21 21:41

### Strategies Added
1. **pixel_count_diamond** — input has background + 2 scattered non-bg colors; count each color → larger count = rectangle width, smaller = height; output is 16×16 with a bottom-left rectangle filled with color 2 and two diagonal lines (color 4) from bottom corners forming V/X/diamond (solves 878187ab)

### Learning Loop Results
- Split: training, Tasks: 20
- Correct: 20 / 20 (100.0%) — up from 19/20 (95.0%)
- Solved: all 20 tasks (c9680e90, 878187ab, e5790162, e9ac8c9e, 0e206a2e, 825aa9e9, 1c56ad9f, c0f76784, 60a26a3e, 8be77c9e, 332202d5, d23f8c26, 6e82a1ae, 9f669b64, afe3afe9, 85c4e7cd, c59eb873, 13f06aa5, bbc9ae5d, 5a719d11)
- Rules: 33 -> 34 (+1 learned)
- Stored rule hits: 19
- Time: 64s
- Log: logs/learn_20260421_214141.log
- Regression: 08ed6ac7 CORRECT

---
## Learning Loop -- 2026-04-21 21:44

- Split: training, Tasks: 20
- Correct: 20 / 20 (100.0%)
- Rules: 34 -> 34 (+0 learned)
- Stored rule hits: 20
- Time: 64s
- Log: logs/learn_20260421_214329.log

---
## Session 10 -- 2026-04-21 22:06

### Strategies Added
1. **rotate_tile_2x2** -- NxN input tiled into 2N×2N output as 4 rotations (original, 90°CCW, 180°, 90°CW) in a 2×2 arrangement (solves ed98d772)
2. **diagonal_extend** -- 2×2 block of one color with diagonal tail pixels; each tail extends diagonally to the grid edge in the direction away from the block (solves 7ddcd7ec)
3. **quadrant_diagonal_fill** -- 2×2 block of 4 distinct non-zero colors on zero background; 2×2 fills placed at each diagonal neighbor position (clipped to grid) with the diagonally opposite color (solves 93b581b8)

### Learning Loop Results
- Split: training, Tasks: 40 (expanded from 20)
- Correct: 23 / 40 (57.5%) -- all 20 original tasks still correct, +3 new
- Solved (new): ed98d772 (rotate_tile_2x2), 7ddcd7ec (diagonal_extend), 93b581b8 (quadrant_diagonal_fill)
- Rules: 51 -> 57 (+6 learned)
- Stored rule hits: 22
- Time: 132s
- Log: logs/learn_20260421_220443.log
- Regression: 08ed6ac7 CORRECT

---
## Learning Loop -- 2026-04-21 22:10

- Split: training, Tasks: 40
- Correct: 23 / 40 (57.5%)
- Rules: 57 -> 62 (+5 learned)
- Stored rule hits: 23
- Time: 132s
- Log: logs/learn_20260421_220752.log

---
## Session 11 -- 2026-04-21 22:18

### Strategies Added
1. **corner_ray** -- each isolated non-zero pixel on a zero background shoots L-shaped rays (horizontal + vertical) toward the nearest grid corner by Manhattan distance (solves 705a3229)
2. **flood_fill_enclosed** -- grid has non-zero frame color forming closed shapes; any 0-cell not reachable from the grid border via 0-connected path becomes color 1 (solves a5313dff)
3. **count_fill_grid** -- input has a 1-bordered rectangle with signal-colored pixels inside; output is 3��3 grid with N cells filled in reading order, where N = count of signal pixels inside the rectangle (solves c8b7cc0f)

### Learning Loop Results
- Split: training, Tasks: 40
- Correct: 26 / 40 (65.0%) -- up from 23/40 (57.5%)
- Solved (new): 705a3229 (corner_ray), a5313dff (flood_fill_enclosed), c8b7cc0f (count_fill_grid)
- Rules: 69 -> 74 (+5 learned)
- Stored rule hits: 25
- Time: 136s
- Log: logs/learn_20260421_222124.log
- Regression: 08ed6ac7 CORRECT

---
## Learning Loop -- 2026-04-21 22:23

- Split: training, Tasks: 40
- Correct: 26 / 40 (65.0%)
- Rules: 69 -> 74 (+5 learned)
- Stored rule hits: 25
- Time: 136s
- Log: logs/learn_20260421_222124.log
