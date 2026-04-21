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

---
## Learning Loop -- 2026-04-21 22:26

- Split: training, Tasks: 40
- Correct: 26 / 40 (65.0%)
- Rules: 74 -> 78 (+4 learned)
- Stored rule hits: 26
- Time: 136s
- Log: logs/learn_20260421_222439.log

---
## Session 12 -- 2026-04-21 22:47

### Strategies Added
1. **grid_intersection_summary** -- large grid divided by separator lines; extract colored marks at separator intersections, produce (N-1)×(M-1) summary where each cell = color if all 4 surrounding corners match, else 0 (solves 7837ac64)
2. **frame_color_swap** -- single rectangle (border_color surrounding interior_color) on black background; output extracts the rectangle with colors swapped (solves b94a9452)
3. **tile_pattern_upward** -- input has background at top, pattern at bottom; output tiles the bottom pattern upward to fill the entire grid (solves 9b30e358)

### Learning Loop Results
- Split: training, Tasks: 40
- Correct: 29 / 40 (72.5%) -- up from 26/40 (65.0%)
- Solved (new): 7837ac64 (grid_intersection_summary), b94a9452 (frame_color_swap), 9b30e358 (tile_pattern_upward)
- Rules: 84 -> 89 (+5 learned)
- Stored rule hits: 28
- Time: 141s
- Log: logs/learn_20260421_224444.log
- Regression: 08ed6ac7 CORRECT

---
## Learning Loop -- 2026-04-21 22:50

- Split: training, Tasks: 40
- Correct: 29 / 40 (72.5%)
- Rules: 89 -> 93 (+4 learned)
- Stored rule hits: 29
- Time: 142s
- Log: logs/learn_20260421_224807.log

---
## Session 13 -- 2026-04-21 23:09

### Strategies Added
1. **denoise_rectangles** -- grid has one fg color on bg 0; remove isolated single pixels and clean connected components to their largest inscribed rectangle (solves 7f4411dc)
2. **color_substitution_template** -- input has a bordered rectangular template on bg 0 plus scattered 2-cell pairs; each pair maps one template interior color to a new color; output = extracted template with substitutions applied (solves e9b4f6fc)
3. **cross_marker_duplicate** -- grid has cross patterns (center=4, same arm color X on all 4 orthogonal neighbors); one arm color appears in exactly 2 crosses; output = 1×1 grid with that color (solves 642d658d)

### Learning Loop Results
- Split: training, Tasks: 40
- Correct: 32 / 40 (80.0%) -- up from 29/40 (72.5%)
- Solved (new): 7f4411dc (denoise_rectangles), e9b4f6fc (color_substitution_template), 642d658d (cross_marker_duplicate)
- Rules: 93 -> 99 (+6 learned)
- Stored rule hits: 29
- Time: 141s
- Log: logs/learn_20260421_230730.log
- Regression: 08ed6ac7 CORRECT

---
## Learning Loop -- 2026-04-21 23:23

- Split: training, Tasks: 40
- Correct: 32 / 40 (80.0%)
- Rules: 99 -> 102 (+3 learned)
- Stored rule hits: 32
- Time: 153s
- Log: logs/learn_20260421_232035.log

---
## Learning Loop -- 2026-04-21 23:47

- Split: training, Tasks: 40
- Correct: 33 / 40 (82.5%)
- Rules: 102 -> 106 (+4 learned)
- Stored rule hits: 32
- Time: 162s
- Log: logs/learn_20260421_234507.log

---
## Session 14 -- 2026-04-21 23:55

### Strategies Added
1. **border_flood_fill** -- grid has a 'source' color (e.g. 0) separated into two regions by wall colors; source cells reachable from grid border via 4-connected path → border_color (e.g. 2), interior source cells → interior_color (e.g. 5) (solves 84db8fc4)
2. **corner_mark_square** -- background grid with rectangular shapes (frames or solid blocks); square shapes (W=H, side ≥ 2) get mark-color cells placed at each corner's outward-projecting neighbor (1 cell out perpendicular to each edge meeting at that corner) (solves 14b8e18c)
3. **cross_center_mark** -- grid has bg + fg domino pairs (2-cell segments); when 4 pairs form a symmetric cross (1 gap cell + 2 pair cells in each of 4 directions from center), the center cell becomes mark color (solves 9f5f939b)

### Learning Loop Results
- Split: training, Tasks: 40
- Correct: 35 / 40 (87.5%) -- up from 32/40 (80.0%)
- Solved (new): 84db8fc4 (border_flood_fill), 14b8e18c (corner_mark_square), 9f5f939b (cross_center_mark)
- Rules: 106 -> 109 (+3 learned)
- Stored rule hits: 33
- Time: 157s
- Log: logs/learn_20260421_235300.log
- Regression: 08ed6ac7 CORRECT

---
## Learning Loop -- 2026-04-21 23:59

- Split: training, Tasks: 40
- Correct: 35 / 40 (87.5%)
- Rules: 109 -> 110 (+1 learned)
- Stored rule hits: 35
- Time: 155s
- Log: logs/learn_20260421_235633.log

---
## Session 15 -- 2026-04-22 00:48

### Strategies Added
1. **mirror_symmetry_recolor** -- grid has bg=0 and one fg color (e.g. 5); for each row, fg cells with a symmetric partner across the vertical center axis become a new color (e.g. 1), unpaired fg cells stay unchanged (solves ce039d91)
2. **rect_pixel_bridge** -- bg grid has colored solid rectangles and isolated single pixels of the same color; each isolated pixel connects to its nearest same-color rect edge via a bridge line, the pixel shifts 1 cell further away, and perpendicular marks appear at bridge start and pixel original position (solves a2d730bd)
3. **fractal_block_denoise** -- grid divided by 0-separator lines into NxM blocks; color 5 is noise; blocks form a self-similar pattern where the meta-grid mirrors the template: blocks at template's minority-color positions show the template, others are pure dominant-color fill (solves 6350f1f4)

### Learning Loop Results
- Split: training, Tasks: 40
- Correct: 38 / 40 (95.0%) -- up from 35/40 (87.5%)
- Solved (new): ce039d91 (mirror_symmetry_recolor), a2d730bd (rect_pixel_bridge), 6350f1f4 (fractal_block_denoise)
- Still failing: 5daaa586, cf5fd0ad
- Rules: 110 -> 113 (+3 learned)
- Stored rule hits: 35
- Time: 153s
- Log: logs/learn_20260422_004557.log
- Regression: 08ed6ac7 CORRECT

---
## Learning Loop -- 2026-04-22 00:48

- Split: training, Tasks: 40
- Correct: 38 / 40 (95.0%)
- Rules: 110 -> 113 (+3 learned)
- Stored rule hits: 35
- Time: 153s
- Log: logs/learn_20260422_004557.log

---
## Learning Loop -- 2026-04-22 00:52

- Split: training, Tasks: 40
- Correct: 38 / 40 (95.0%)
- Rules: 113 -> 113 (+0 learned)
- Stored rule hits: 38
- Time: 148s
- Log: logs/learn_20260422_004941.log

---
## Session 16 -- 2026-04-22 01:05

### New Strategies
1. **separator_histogram** (Strategy 35): Grids divided by 2 horizontal + 2 vertical
   colored separator lines. Scattered marker dots in the center section (matching one
   separator color) collapse into histogram bars extending from the matching separator.
   Supports all 4 fill directions (top/bottom/left/right). Fixed task `5daaa586`.
2. **rotation_quadrant_tile_4x4** (Strategy 36): NxN input → 4Nx4N output via 4×4 block
   arrangement. Each 2×2 quadrant uses a specific rotation: TL=180°, TR=90°CW,
   BL=90°CCW, BR=original. Fixed task `cf5fd0ad`.

### Results
- Split: training, Tasks: 40
- Correct: 40 / 40 (100.0%)  ← up from 38/40 (95.0%)
- Rules: 113 -> 115 (+2 learned)
- Stored rule hits: 38
- Discovered: 2 new rules from pipeline
- Time: 147s
- Log: logs/learn_20260422_010305.log

---
## Learning Loop -- 2026-04-22 01:09

- Split: training, Tasks: 40
- Correct: 40 / 40 (100.0%)
- Rules: 115 -> 115 (+0 learned)
- Stored rule hits: 40
- Time: 148s
- Log: logs/learn_20260422_010635.log

---
## Learning Loop -- 2026-04-22 01:14

- Split: training, Tasks: 80 (expanded from 40)
- Correct: 41 / 80 (51.2%)
- Rules: 115 -> 119 (+4 learned)
- Stored rule hits: 40
- Errors: 5 (list index out of range in _apply_fractal_block_denoise)
- Time: 291s
- Log: logs/learn_20260422_010932.log

---
## Session 17 -- 2026-04-22 01:28

### Bug Fixes
- Fixed `_apply_fractal_block_denoise` crashes: added bounds checking for template
  dimensions vs meta-grid dimensions and block range sizes. Eliminated all 5 ERROR
  tasks (cdecee7f, c62e2108, 5168d44c, 845d6e51, b7cb93ac).

### Strategies Added
1. **self_tiling** (Strategy 37): NxN input → N²×N² output. Each non-zero cell in
   the input is replaced by a full copy of the input; zero cells become all-zero
   blocks. Fractal/self-referential zoom pattern. (solves 007bbfb7)
2. **double_mirror** (Strategy 38): NxM input → 2N×2M output via horizontal then
   vertical mirror (kaleidoscope). Each row becomes row+reversed(row), then rows
   are mirrored vertically. (solves 62c24649, also generalizes to 67e8384a)
3. **xor_comparison** (Strategy 39): Input has two sub-grids separated by a uniform-
   color row. Output = XOR of the two halves: cells are color 3 where exactly one
   half has a non-zero cell, 0 otherwise. (solves 99b1bc43)

### Results
- Split: training, Tasks: 80
- Correct: 45 / 80 (56.2%) -- up from 41/80 (51.2%), errors eliminated
- Solved (new): 007bbfb7 (self_tiling), 62c24649 (double_mirror), 67e8384a (double_mirror generalized), 99b1bc43 (xor_comparison)
- Errors: 0 (down from 5)
- Rules: 122 -> 124 (+2 learned)
- Stored rule hits: 44
- Time: 269s
- Log: logs/learn_20260422_012355.log
- Regression: 08ed6ac7 CORRECT

---
## Learning Loop -- 2026-04-22 01:33

- Split: training, Tasks: 80
- Correct: 45 / 80 (56.2%)
- Rules: 124 -> 126 (+2 learned)
- Stored rule hits: 44
- Time: 269s
- Log: logs/learn_20260422_012927.log

---
## Learning Loop -- 2026-04-22 01:46

- Split: training, Tasks: 80
- Correct: 48 / 80 (60.0%)
- Rules: 126 -> 131 (+5 learned)
- Stored rule hits: 44
- Time: 243s
- Log: logs/learn_20260422_014220.log

---
## Learning Loop -- 2026-04-22 01:51

- Split: training, Tasks: 80
- Correct: 48 / 80 (60.0%)
- Rules: 131 -> 133 (+2 learned)
- Stored rule hits: 47
- Time: 241s
- Log: logs/learn_20260422_014705.log

---
## Learning Loop -- 2026-04-22 01:59

- Split: training, Tasks: 80
- Correct: 49 / 80 (61.3%)
- Rules: 134 -> 136 (+2 learned)
- Stored rule hits: 48
- Time: 239s
- Log: logs/learn_20260422_015509.log

---
## Learning Loop -- 2026-04-22 02:03

- Split: training, Tasks: 80
- Correct: 49 / 80 (61.3%)
- Rules: 136 -> 138 (+2 learned)
- Stored rule hits: 48
- Time: 243s
- Log: logs/learn_20260422_015914.log

---
## Session 18 -- 2026-04-22 02:03

### Strategies Added
1. **half_grid_boolean** — split input into two halves (horizontal separator, vertical separator, or plain bisection), detect boolean operation (OR/AND/NOR/NAND), output result color (solves e345f17b via NOR, 506d28a5 via OR)
2. **inverse_tile** — invert input colors (0↔foreground) then tile 2×2 to produce output at 2× dimensions (solves 48131b3c)
3. **grid_separator_max_fill** — input divided by separator rows/cols into cell grid; fill cells with maximum non-zero pixel count, clear others (solves 29623171)

### Bug Fix
- Fixed h_separator detection in `_check_boolean_split`: was accepting the first uniform non-zero row as separator even if it didn't divide the grid into equal halves. Now validates that the candidate separator produces equal halves matching output dimensions.

### Learning Loop Results
- Split: training, Tasks: 80
- Correct: 49 / 80 (61.3%) — up from 45/80 (56.2%), +4 tasks
- Solved: e345f17b (half_grid_boolean/NOR), 506d28a5 (half_grid_boolean/OR), 48131b3c (inverse_tile), 29623171 (grid_separator_max_fill)
- Rules: 136 -> 138 (+2 learned)
- Stored rule hits: 48
- Time: 243s
- Regression: 08ed6ac7 CORRECT
