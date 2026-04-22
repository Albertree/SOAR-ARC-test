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

---
## Learning Loop -- 2026-04-22 02:08

- Split: training, Tasks: 80
- Correct: 49 / 80 (61.3%)
- Rules: 138 -> 140 (+2 learned)
- Stored rule hits: 48
- Time: 243s
- Log: logs/learn_20260422_020402.log

---
## Learning Loop -- 2026-04-22 02:22

- Split: training, Tasks: 80
- Correct: 51 / 80 (63.7%)
- Rules: 140 -> 148 (+8 learned)
- Stored rule hits: 48
- Time: 208s
- Log: logs/learn_20260422_021916.log

---
## Learning Loop -- 2026-04-22 02:26

- Split: training, Tasks: 80
- Correct: 51 / 80 (63.7%)
- Rules: 148 -> 154 (+6 learned)
- Stored rule hits: 50
- Time: 208s
- Log: logs/learn_20260422_022258.log

---
## Session 19 -- 2026-04-22 02:30

### Bug Fix
- Fixed `_try_rect_pixel_bridge` validation: was returning a valid rule even when no
  example pair actually had rects+isolates to validate. Added `validated_any` flag so
  the rule only returns when at least one pair actually validates the bridge pattern.
  Eliminated 13 false positive matches (tasks now correctly fall to identity or other rules).

### Strategies Added
1. **grid_lines_pattern** (Strategy 43): Input is all-zero NxN grid; output fills cells
   with 1 where row%2==0 OR col%2==0, creating a grid-line pattern. Placed before
   recolor_sequential to avoid false match. (solves 332efdb3)
2. **column_shadow_tile** (Strategy 44): Zero cells in columns containing any non-zero
   cell are replaced with 8 (shadow), then the modified grid is tiled 2×2 to produce
   output at 2× dimensions. (solves f5b8619d)
3. **concentric_ring_rotate** (Strategy 45): Input has concentric rectangular rings of
   uniform color. Output rotates the unique ring color sequence right by 1 position
   (innermost color becomes outermost). (solves bda2d7a6)

### Learning Loop Results
- Split: training, Tasks: 80
- Correct: 52 / 80 (65.0%) — up from 49/80 (61.3%), +3 tasks
- Solved (new): 332efdb3 (grid_lines_pattern), f5b8619d (column_shadow_tile), bda2d7a6 (concentric_ring_rotate)
- rect_pixel_bridge false positives: 13 → 0
- Rules: 154 -> 161 (+7 learned)
- Stored rule hits: 50
- Time: 208s
- Log: logs/learn_20260422_022716.log
- Regression: 08ed6ac7 CORRECT

---
## Learning Loop -- 2026-04-22 02:34

- Split: training, Tasks: 80
- Correct: 52 / 80 (65.0%)
- Rules: 161 -> 167 (+6 learned)
- Stored rule hits: 51
- Time: 209s
- Log: logs/learn_20260422_023124.log

---
## Session 20 -- 2026-04-22 02:47

### Strategies Added
1. **wedge_expansion** (Strategy 46): Input has a single horizontal line of color 2
   starting from col 0. Output expands upward with color 3 (each row adds +1 cell
   from col 0) and contracts downward with color 1 (each row removes -1 cell).
   Triangular/wedge expansion from a seed line. (solves a65b410d)
2. **mirror_row_tile** (Strategy 47): Output width = 4× input width, same height.
   Each row becomes reversed(row) + row (horizontal palindrome), then tiled 2×.
   Row-wise horizontal mirror and tile pattern. (solves 59341089)
3. **larger_interior_rect** (Strategy 48): Input has two hollow rectangles on bg 0.
   Output is 2×2 grid filled with the color of the rectangle having the larger
   interior area. Rectangle comparison by interior size. (solves 445eab21)

### Learning Loop Results
- Split: training, Tasks: 80
- Correct: 55 / 80 (68.8%) — up from 52/80 (65.0%)
- Solved (new): a65b410d (wedge_expansion), 59341089 (mirror_row_tile), 445eab21 (larger_interior_rect)
- Rules: 167 -> 176 (+9 learned)
- Stored rule hits: 51
- Discovered: 10 new rules from pipeline
- Time: 212s
- Log: logs/learn_20260422_024354.log
- Regression: 08ed6ac7 CORRECT

---
## Learning Loop -- 2026-04-22 02:51

- Split: training, Tasks: 80
- Correct: 55 / 80 (68.8%)
- Rules: 176 -> 182 (+6 learned)
- Stored rule hits: 54
- Time: 210s
- Log: logs/learn_20260422_024731.log

---
## Learning Loop -- 2026-04-22 02:51

- Split: training, Tasks: 80
- Correct: 55 / 80 (68.8%)
- Rules: 176 -> 182 (+6 learned)
- Stored rule hits: 54
- Time: 210s
- Log: logs/learn_20260422_024731.log

---
## Learning Loop -- 2026-04-22 02:55

- Split: training, Tasks: 80
- Correct: 55 / 80 (68.8%)
- Rules: 182 -> 188 (+6 learned)
- Stored rule hits: 54
- Time: 209s
- Log: logs/learn_20260422_025217.log

---
## Session 21 -- 2026-04-22 03:23

### Strategies Added
1. **bbox_fill** (Strategy 49): Input has a single fg color (e.g. 8) forming a
   shape on bg 0 with internal gaps. Output fills 0-cells within the bounding
   box of the fg shape with a fill color (e.g. 2). Placed before color_mapping
   to prevent false-positive match. (solves 6d75e8bb)
2. **symmetry_complete** (Strategy 50): Input has a pattern on bg 0 that is
   nearly 4-fold rotationally symmetric (diamond/checkerboard). Output completes
   the symmetry by filling in missing rotational counterparts around the bbox
   center. Requires square bounding box. (solves 11852cab)
3. **accelerating_sequence** (Strategy 51): Input has one row with seed colors
   at start positions matching triangular numbers (0, 1, 3, 6, ...). Output
   fills that row by cycling seed colors at positions with increasing gaps
   (1, 2, 3, 4, ...). (solves 72207abc)

### Learning Loop Results
- Split: training, Tasks: 80
- Correct: 58 / 80 (72.5%) — up from 55/80 (68.8%)
- Solved (new): 6d75e8bb (bbox_fill), 11852cab (symmetry_complete), 72207abc (accelerating_sequence)
- Rules: 202 -> 208 (+6 learned)
- Stored rule hits: 56
- Discovered: 7 new rules from pipeline
- Time: 210s
- Regression: 08ed6ac7 CORRECT

---
## Learning Loop -- 2026-04-22 03:14

- Split: training, Tasks: 80
- Correct: 57 / 80 (71.2%)
- Rules: 188 -> 196 (+8 learned)
- Stored rule hits: 54
- Time: 210s
- Log: logs/learn_20260422_031034.log

---
## Learning Loop -- 2026-04-22 03:17

- Split: training, Tasks: 80
- Correct: 57 / 80 (71.2%)
- Rules: 196 -> 202 (+6 learned)
- Stored rule hits: 56
- Time: 210s
- Log: logs/learn_20260422_031418.log

---
## Learning Loop -- 2026-04-22 03:23

- Split: training, Tasks: 80
- Correct: 58 / 80 (72.5%)
- Rules: 202 -> 208 (+6 learned)
- Stored rule hits: 56
- Time: 210s
- Log: logs/learn_20260422_031932.log

---
## Learning Loop -- 2026-04-22 03:26

- Split: training, Tasks: 80
- Correct: 58 / 80 (72.5%)
- Rules: 208 -> 213 (+5 learned)
- Stored rule hits: 57
- Time: 210s
- Log: logs/learn_20260422_032307.log

---
## Learning Loop -- 2026-04-22 03:30

- Split: training, Tasks: 80
- Correct: 58 / 80 (72.5%)
- Rules: 213 -> 218 (+5 learned)
- Stored rule hits: 57
- Time: 210s
- Log: logs/learn_20260422_032727.log

---
## Session 22 -- 2026-04-22 03:52

### Strategies Added
1. **pixel_collect_snake** (Strategy 52): Sparse grid with scattered single non-zero
   pixels on 0 background. Collect all pixels, sort by column (then row), place into
   compact output grid (e.g. 3×3) in boustrophedon (snake) order: even rows L→R, odd
   rows R→L. Category: spatial sorting / dimensionality reduction. (solves cdecee7f)
2. **frame_scale_pattern** (Strategy 53): Rectangular frame of color 2 on 0 background
   contains a 2×2 quadrant color pattern (4 distinct colors, each filling a block).
   Output crops to the frame and scales the 2×2 pattern to fill the entire interior
   evenly — each quadrant gets one color. Category: crop + scale-up / frame extraction.
   (solves e7a25a18)
3. **box_slide_trail** (Strategy 54): 3×3 box of border color (2) with center color (3)
   on 0 background, plus a trail of center-color dots spaced 2 cells apart along the
   same row or column. Box slides 1 step (2 cells) along the trail toward the side with
   more dots (positive direction if tied). Old center becomes trail dot, trail dot at new
   position absorbed into box. Category: object translation along marker path.
   (solves 5168d44c)

### Learning Loop Results
- Split: training, Tasks: 80
- Correct: 61 / 80 (76.2%) — up from 58/80 (72.5%)
- Solved (new): cdecee7f (pixel_collect_snake), e7a25a18 (frame_scale_pattern), 5168d44c (box_slide_trail)
- Rules: 218 -> 225 (+7 learned)
- Stored rule hits: 57
- Discovered: 8 new rules from pipeline
- Time: 220s
- Regression: 08ed6ac7 CORRECT

---
## Learning Loop -- 2026-04-22 03:52

- Split: training, Tasks: 80
- Correct: 61 / 80 (76.2%)
- Rules: 218 -> 225 (+7 learned)
- Stored rule hits: 57
- Time: 220s
- Log: logs/learn_20260422_034910.log

---
## Learning Loop -- 2026-04-22 03:56

- Split: training, Tasks: 80
- Correct: 61 / 80 (76.2%)
- Rules: 225 -> 229 (+4 learned)
- Stored rule hits: 60
- Time: 219s
- Log: logs/learn_20260422_035259.log

---
## Learning Loop -- 2026-04-22 04:00

- Split: training, Tasks: 80
- Correct: 61 / 80 (76.2%)
- Rules: 229 -> 233 (+4 learned)
- Stored rule hits: 60
- Time: 219s
- Log: logs/learn_20260422_035653.log

---
## Learning Loop -- 2026-04-22 04:05

- Split: training, Tasks: 80
- Correct: 61 / 80 (76.2%)
- Rules: 233 -> 237 (+4 learned)
- Stored rule hits: 60
- Time: 218s
- Log: logs/learn_20260422_040142.log

---
## Learning Loop -- 2026-04-22 04:24

- Split: training, Tasks: 80
- Correct: 60 / 80 (75.0%)
- Rules: 237 -> 237 (+0 learned)
- Stored rule hits: 60
- Time: 217s
- Log: logs/learn_20260422_042037.log

---
## Learning Loop -- 2026-04-22 04:28

- Split: training, Tasks: 80
- Correct: 60 / 80 (75.0%)
- Rules: 237 -> 237 (+0 learned)
- Stored rule hits: 60
- Time: 218s
- Log: logs/learn_20260422_042430.log

---
## Learning Loop -- 2026-04-22 04:37

- Split: training, Tasks: 80
- Correct: 61 / 80 (76.2%)
- Rules: 237 -> 241 (+4 learned)
- Stored rule hits: 60
- Time: 220s
- Log: logs/learn_20260422_043323.log

---
## Learning Loop -- 2026-04-22 04:40

- Split: training, Tasks: 80
- Correct: 61 / 80 (76.2%)
- Rules: 241 -> 245 (+4 learned)
- Stored rule hits: 60
- Time: 222s
- Log: logs/learn_20260422_043711.log

---
## Learning Loop -- 2026-04-22 04:44

- Split: training, Tasks: 80
- Correct: 61 / 80 (76.2%)
- Rules: 245 -> 249 (+4 learned)
- Stored rule hits: 60
- Time: 219s
- Log: logs/learn_20260422_044108.log

---
## Learning Loop -- 2026-04-22 04:49

- Split: training, Tasks: 80
- Correct: 64 / 80 (80.0%)
- Rules: 249 -> 256 (+7 learned)
- Stored rule hits: 60
- Time: 219s
- Log: logs/learn_20260422_044617.log

---
## Session 23 -- 2026-04-22 04:50

### Strategies Added
1. **cross_pair_lines** (Strategy 55): Grid with scattered pixel pairs; each
   non-zero color appears exactly twice, forming a horizontal pair (same row)
   or vertical pair (same column). Output draws filled lines between endpoints.
   Vertical lines overwrite horizontal lines at crossings.
   Category: pair-based line drawing. (solves 070dd51e)
2. **multi_layer_overlay** (Strategy 56): Input is N stacked layers of same
   dimensions, each with one non-zero color and 0s (binary mask per color).
   Output merges layers into one grid. Priority learned from training examples
   via pairwise comparison. Category: layer compositing / z-order merge.
   (solves 3d31c5b3)
3. **tile_grid_recolor** (Strategy 57): Grid has a regular array of tiles
   (color 5) in rows/cols separated by 0-gaps, plus a key matrix (non-0,
   non-5 rectangular block) whose dimensions match the tile count. Output
   replaces each tile's 5-cells with the corresponding key color.
   Category: template coloring / lookup table. (solves 33b52de3)

### Bug Fix
- Fixed AttributeError in all three new strategies: Task object uses
  `example_pairs` not `train_pairs`.

### Learning Loop Results
- Split: training, Tasks: 80
- Correct: 64 / 80 (80.0%) — up from 61/80 (76.2%)
- Solved (new): 070dd51e (cross_pair_lines), 3d31c5b3 (multi_layer_overlay), 33b52de3 (tile_grid_recolor)
- Rules: 249 -> 256 (+7 learned)
- Stored rule hits: 60
- Discovered: 8 new rules from pipeline
- Time: 219s
- Regression: 08ed6ac7 CORRECT

---
## Learning Loop -- 2026-04-22 04:53

- Split: training, Tasks: 80
- Correct: 64 / 80 (80.0%)
- Rules: 256 -> 260 (+4 learned)
- Stored rule hits: 63
- Time: 220s
- Log: logs/learn_20260422_045002.log

---
## Learning Loop -- 2026-04-22 04:58

- Split: training, Tasks: 80
- Correct: 64 / 80 (80.0%)
- Rules: 260 -> 264 (+4 learned)
- Stored rule hits: 63
- Time: 219s
- Log: logs/learn_20260422_045456.log

---
## Session 24 -- 2026-04-22 05:22

### Strategies Added
1. **rect_minority_gridlines** (Strategy 58): Input has a rectangular region of
   mostly one color (dominant) embedded in noisy surroundings, with a few cells
   of a second color (minority) scattered inside. Output extracts the rectangle
   and draws full horizontal+vertical grid lines through each minority cell
   position. Uses density-based scanning to find the rect even in noisy grids.
   Category: pattern extraction / grid line inference. (solves 8731374e)
2. **rect_directional_tile** (Strategy 59): Input has hollow 4×4 rectangles
   (frame of color X, 2×2 interior of 0) and lines of color 1 as direction
   indicators. Each rect tiles in the direction(s) indicated by aligned 1-lines,
   extending from its position to fill the space up to the 1-line marker.
   1-lines are consumed/replaced by the tiled pattern.
   Category: directional tiling / pattern extrusion. (solves c62e2108)
3. **corner_block_shift** (Strategy 60): Grid with uniform background has
   rectangular blocks of non-bg colors at corner-like positions. The most
   frequent color among the blocks shifts inward by one block dimension
   (toward grid center). Minority-color blocks stay in place.
   Category: object motion / corner block inward displacement. (solves 22208ba4)

### Learning Loop Results
- Split: training, Tasks: 80
- Correct: 67 / 80 (83.8%) — up from 64/80 (80.0%)
- Solved (new): 8731374e (rect_minority_gridlines), c62e2108 (rect_directional_tile), 22208ba4 (corner_block_shift)
- Rules: 274 -> 279 (+5 learned)
- Stored rule hits: 65
- Discovered: 6 new rules from pipeline
- Time: 219s
- Regression: 08ed6ac7 CORRECT

---
## Learning Loop -- 2026-04-22 05:09

- Split: training, Tasks: 80
- Correct: 66 / 80 (82.5%)
- Rules: 264 -> 270 (+6 learned)
- Stored rule hits: 63
- Time: 221s
- Log: logs/learn_20260422_050549.log

---
## Learning Loop -- 2026-04-22 05:13

- Split: training, Tasks: 80
- Correct: 66 / 80 (82.5%)
- Rules: 270 -> 274 (+4 learned)
- Stored rule hits: 65
- Time: 219s
- Log: logs/learn_20260422_050954.log

---
## Learning Loop -- 2026-04-22 05:22

- Split: training, Tasks: 80
- Correct: 67 / 80 (83.8%)
- Rules: 274 -> 279 (+5 learned)
- Stored rule hits: 65
- Time: 219s
- Log: logs/learn_20260422_051841.log

---
## Learning Loop -- 2026-04-22 05:26

- Split: training, Tasks: 80
- Correct: 67 / 80 (83.8%)
- Rules: 279 -> 283 (+4 learned)
- Stored rule hits: 65
- Time: 221s
- Log: logs/learn_20260422_052231.log

---
## Learning Loop -- 2026-04-22 05:30

- Split: training, Tasks: 80
- Correct: 67 / 80 (83.8%)
- Rules: 283 -> 287 (+4 learned)
- Stored rule hits: 65
- Time: 219s
- Log: logs/learn_20260422_052705.log

---
## Session 25 -- 2026-04-22 06:06

### Strategies Added
1. **grid_section_key_lookup** (Strategy 61): Grid divided by color-5 lines
   into 3×3 sections. Each section has scattered values from {2,3,4,6,8}.
   One "key" section has exactly 4 non-zero cells (missing color 8). Each
   value V at local position (r,c) in the key section maps to: fill section
   at grid position (r,c) with color V. Other sections get 0.
   Category: grid section analysis / key-based lookup. (solves 09629e4f)
2. **shape_template_catalog** (Strategy 62): Top-left area (bounded by
   L-shaped 5-border) contains template shapes of distinct colors. Rest of
   grid has shapes of color 3. Each 3-shape matches one template via
   rotation/reflection (all 8 orientations). Output replaces each 3-shape
   with matching template color.
   Category: shape matching / template recoloring. (solves 845d6e51)
3. **bar_chart_balance** (Strategy 63): Grid with bg=7 has vertical bars of
   colors 8 and 2 at odd columns extending from bottom. Output adds a new
   bar of color 5 at the next odd column. Height = sum(8-bar heights) -
   sum(2-bar heights). Placed early in chain to prevent false-positive
   match by recolor_sequential.
   Category: bar chart derivation / balance computation. (solves 37ce87bb)

### Learning Loop Results
- Split: training, Tasks: 80
- Correct: 70 / 80 (87.5%) — up from 67/80 (83.8%)
- Solved (new): 09629e4f (grid_section_key_lookup), 845d6e51 (shape_template_catalog), 37ce87bb (bar_chart_balance)
- Rules: 292 -> 298 (+6 learned)
- Stored rule hits: 66
- Discovered: 7 new rules from pipeline
- Time: 220s
- Regression: 08ed6ac7 CORRECT

---
## Learning Loop -- 2026-04-22 06:00

- Split: training, Tasks: 80
- Correct: 68 / 80 (85.0%)
- Rules: 287 -> 292 (+5 learned)
- Stored rule hits: 65
- Time: 222s
- Log: logs/learn_20260422_055658.log

---
## Learning Loop -- 2026-04-22 06:06

- Split: training, Tasks: 80
- Correct: 70 / 80 (87.5%)
- Rules: 292 -> 298 (+6 learned)
- Stored rule hits: 66
- Time: 220s
- Log: logs/learn_20260422_060236.log

---
## Learning Loop -- 2026-04-22 06:10

- Split: training, Tasks: 80
- Correct: 70 / 80 (87.5%)
- Rules: 298 -> 302 (+4 learned)
- Stored rule hits: 68
- Time: 219s
- Log: logs/learn_20260422_060705.log

---
## Learning Loop -- 2026-04-22 06:54

- Split: training, Tasks: 80
- Correct: 70 / 80 (87.5%)
- Rules: 302 -> 306 (+4 learned)
- Stored rule hits: 68
- Time: 223s
- Log: logs/learn_20260422_065045.log

---
## Learning Loop -- 2026-04-22 06:59

- Split: training, Tasks: 80
- Correct: 70 / 80 (87.5%)
- Rules: 306 -> 310 (+4 learned)
- Stored rule hits: 68
- Time: 220s
- Log: logs/learn_20260422_065524.log

---
## Learning Loop -- 2026-04-22 07:15

- Split: training, Tasks: 80
- Correct: 70 / 80 (87.5%)
- Rules: 310 -> 314 (+4 learned)
- Stored rule hits: 68
- Time: 221s
- Log: logs/learn_20260422_071137.log

---
## Learning Loop -- 2026-04-22 07:28

- Split: training, Tasks: 80
- Correct: 72 / 80 (90.0%)
- Rules: 314 -> 319 (+5 learned)
- Stored rule hits: 68
- Time: 220s
- Log: logs/learn_20260422_072424.log

---
## Session 26 -- 2026-04-22 07:28

### Strategies Added
1. **largest_blob_color** (Strategy 64): Noisy grid with solid-colored
   patches embedded in scattered noise. For each color, find its largest
   connected component. Patches have largest_cc == total_count (fully
   connected), while noise colors are fragmented. Output is a small
   uniform grid (e.g. 3×3) of the color with the largest fully-connected
   patch. Category: object detection / largest CC identification.
   (solves 3194b014)
2. **spiral_from_seed** (Strategy 66): Grid with a single color-3 pixel
   (seed) and color-2 obstacles on background 0. Output draws a
   rectangular spiral of 3s outward from the seed. Arm lengths follow
   2,2,4,4,6,6,... pattern in directions up/right/down/left. OOB cells
   are skipped but cursor advances theoretically, allowing the spiral to
   naturally wrap around grid edges. Stops on obstacle or self-collision.
   Category: geometric construction / rectangular spiral.
   (solves e5c44e8f)

### Learning Loop Results
- Split: training, Tasks: 80
- Correct: 72 / 80 (90.0%) — up from 70/80 (87.5%)
- Solved (new): 3194b014 (largest_blob_color), e5c44e8f (spiral_from_seed)
- Rules: 314 -> 319 (+5 learned)
- Stored rule hits: 68
- Discovered: 6 new rules from pipeline
- Time: 220s
- Regression: 08ed6ac7 CORRECT

---
## Learning Loop -- 2026-04-22 07:31

- Split: training, Tasks: 80
- Correct: 72 / 80 (90.0%)
- Rules: 319 -> 322 (+3 learned)
- Stored rule hits: 70
- Time: 222s
- Log: logs/learn_20260422_072809.log

---
## Learning Loop -- 2026-04-22 07:36

- Split: training, Tasks: 80
- Correct: 72 / 80 (90.0%)
- Rules: 322 -> 325 (+3 learned)
- Stored rule hits: 70
- Time: 221s
- Log: logs/learn_20260422_073259.log

---
## Learning Loop -- 2026-04-22 08:00

- Split: training, Tasks: 80
- Correct: 73 / 80 (91.2%)
- Rules: 325 -> 329 (+4 learned)
- Stored rule hits: 70
- Time: 223s
- Log: logs/learn_20260422_075703.log

---
## Learning Loop -- 2026-04-22 08:04

- Split: training, Tasks: 80
- Correct: 73 / 80 (91.2%)
- Rules: 329 -> 332 (+3 learned)
- Stored rule hits: 71
- Time: 222s
- Log: logs/learn_20260422_080051.log

---
## Session 27 -- 2026-04-22 08:20

### Strategies Added
1. **panel_hole_classify** — 4-row grid with 3 panels separated by 0-columns; each panel's 2×2 hole position maps to a color in a 3×3 output (solves 995c5fa3)
2. **grid_panel_decode** — N×M panel matrix separated by lines of separator color; each column has one solid-color panel and pattern panels; output merges pattern with color, using solid panel's row-label as border (solves 15660dd6)
3. **shape_gravity_sort** — multiple colored shapes on bg=0; enclosed shapes (with interior holes) pack to top of grid, open shapes (crosses, lines) pack to bottom; column positions preserved, shapes stack to avoid overlap (solves ac2e8ecf)

### Learning Loop Results
- Split: training, Tasks: 80
- Correct: 75 / 80 (93.8%) — up from 72/80 (90.0%)
- Solved: 995c5fa3 (panel_hole_classify), 15660dd6 (grid_panel_decode), ac2e8ecf (shape_gravity_sort)
- Still failing: 7d7772cc, 985ae207, b7cb93ac, e5062a87, 1acc24af
- Rules: 332 -> 337 (+5 learned)
- Stored rule hits: 71
- Discovered: 6 new rules from pipeline
- Time: 220s
- Log: logs/learn_20260422_081659.log
- Regression: 08ed6ac7 CORRECT

---
## Learning Loop -- 2026-04-22 08:25

- Split: training, Tasks: 80
- Correct: 75 / 80 (93.8%)
- Rules: 337 -> 340 (+3 learned)
- Stored rule hits: 73
- Time: 220s
- Log: logs/learn_20260422_082145.log

---
## Learning Loop -- 2026-04-22 08:56

- Split: training, Tasks: 80
- Correct: 76 / 80 (95.0%)
- Rules: 340 -> 344 (+4 learned)
- Stored rule hits: 73
- Time: 224s
- Log: logs/learn_20260422_085253.log

---
## Session 28 -- 2026-04-22 09:09

### Strategies Added
1. **separator_sequence_reflect** — grid divided by a full-row/column separator with dot sequences on each side; dots compared pairwise: matches reflect adjacent to separator, differences to far edge (solves 7d7772cc)
2. **shape_stamp_fill** (wired up) — existing strategy was implemented but never called from effect(); now activated before color_mapping (solves category of 0/5/2 grid stamping)
3. **color_mapping fix** — added full-grid validation to prevent false positives where pattern-only analysis shows 1:1 mapping but actual grids show inconsistencies (fixes e5062a87 and 1acc24af false matches)

### Learning Loop Results
- Split: training, Tasks: 80
- Correct: 76 / 80 (95.0%) — up from 75/80 (93.8%)
- Newly solved: 7d7772cc (separator_sequence_reflect)
- Still failing: 985ae207 (identity), b7cb93ac (identity), e5062a87 (identity), 1acc24af (identity)
- Rules: 344 -> 345 (+1 learned)
- Stored rule hits: 74
- Time: 220s
- Log: logs/learn_20260422_090533.log
- Regression: 08ed6ac7 CORRECT

---
## Learning Loop -- 2026-04-22 09:18

- Split: training, Tasks: 80
- Correct: 76 / 80 (95.0%)
- Rules: 345 -> 346 (+1 learned)
- Stored rule hits: 74
- Time: 220s
- Log: logs/learn_20260422_091512.log

---
## Learning Loop -- 2026-04-22 10:50

- Split: training, Tasks: 80
- Correct: 76 / 80 (95.0%)
- Rules: 346 -> 348 (+2 learned)
- Stored rule hits: 73
- Time: 221s
- Log: logs/learn_20260422_104623.log

---
## Learning Loop -- 2026-04-22 10:54

- Split: training, Tasks: 80
- Correct: 76 / 80 (95.0%)
- Rules: 348 -> 349 (+1 learned)
- Stored rule hits: 74
- Time: 216s
- Log: logs/learn_20260422_105101.log

---
## Learning Loop -- 2026-04-22 11:02

- Split: training, Tasks: 80
- Correct: 76 / 80 (95.0%)
- Rules: 349 -> 351 (+2 learned)
- Stored rule hits: 74
- Time: 217s
- Log: logs/learn_20260422_105842.log

---
## Session 29 -- 2026-04-22 11:09

### Strategies Added
1. **stamp_tile_toward_bar** (Strategy 71): Grid bg=8 with 3×3 "stamps"
   (uniform border color B, center color C≠B) and large solid-color rectangular
   "bars". Each stamp's center color matches a bar's color. The stamp tiles
   repeatedly from its position toward the matching bar, stopping when the
   latest copy reaches the bar's near edge. Supports all 4 directions
   (left/right/up/down) based on relative stamp-bar positioning.
   Category: directional pattern tiling / stamp-bar association.
   (solves 985ae207)
2. **shape_jigsaw_assemble** (Strategy 72): Input has several small colored
   shapes scattered on bg=0. Output is a compact filled rectangle (no zeros)
   containing all shapes packed together like jigsaw pieces. Shapes may be
   rotated/reflected to fit. Solver sorts shapes by size (largest first, then
   by color for tie-breaking), tries all 8 orientations, and uses backtracking.
   Category: shape assembly / exact cover / jigsaw packing.
   (solves b7cb93ac)

### Bug Fix
- Fixed `_shape_orientations` to handle both `(r, c)` 2-tuples (used by
  shape_template_catalog) and `(r, c, v)` 3-tuples (used by jigsaw). The
  change in tuple format caused a regression in 845d6e51 (shape_template_catalog)
  which was fixed by detecting tuple width at runtime.

### Learning Loop Results
- Split: training, Tasks: 80
- Correct: 78 / 80 (97.5%) — up from 76/80 (95.0%)
- Solved (new): 985ae207 (stamp_tile_toward_bar), b7cb93ac (shape_jigsaw_assemble)
- Still failing: e5062a87 (identity), 1acc24af (identity)
- Rules: 351 -> 352 (+1 learned)
- Stored rule hits: 76
- Discovered: 2 new rules from pipeline
- Time: 219s
- Log: logs/learn_20260422_110542.log
- Regression: 08ed6ac7 CORRECT

---
## Learning Loop -- 2026-04-22 11:13

- Split: training, Tasks: 80
- Correct: 78 / 80 (97.5%)
- Rules: 352 -> 353 (+1 learned)
- Stored rule hits: 76
- Time: 217s
- Log: logs/learn_20260422_111017.log

---
## Learning Loop -- 2026-04-22 12:45

- Split: training, Tasks: 80
- Correct: 78 / 80 (97.5%)
- Rules: 353 -> 354 (+1 learned)
- Stored rule hits: 76
- Time: 230s
- Log: logs/learn_20260422_124114.log

---
## Learning Loop -- 2026-04-22 13:10

- Split: training, Tasks: 80
- Correct: 78 / 80 (97.5%)
- Rules: 354 -> 356 (+2 learned)
- Stored rule hits: 76
- Time: 214s
- Log: logs/learn_20260422_130710.log

---
## Learning Loop -- 2026-04-22 13:21

- Split: training, Tasks: 80
- Correct: 79 / 80 (98.8%)
- Rules: 356 -> 357 (+1 learned)
- Stored rule hits: 77
- Time: 213s
- Log: logs/learn_20260422_131823.log

---
## Session 30 -- 2026-04-22 13:21

- **Score: 79 / 80 (98.8%)** — up from 78/80 (97.5%)
- New strategy: `frame_hole_recolor` (Strategy 74)
  - Detects U-shaped frames of 1-cells with rectangular enclosed holes
  - 5-shapes below the frame are classified: if group is within a rectangle's wall range and has same column width as the hole, check containment → recolor to 2; otherwise check against all holes
  - Category: frame-based shape classification / template matching
  - Solved: 1acc24af
- Remaining INCORRECT: e5062a87 (complex marker-shape stamping, rule not yet identified)
- Rules: 356 → 357 (+1 learned)
- Stored rule hits: 77

---
## Learning Loop -- 2026-04-22 13:26

- Split: training, Tasks: 80
- Correct: 79 / 80 (98.8%)
- Rules: 357 -> 358 (+1 learned)
- Stored rule hits: 77
- Time: 212s
- Log: logs/learn_20260422_132306.log

---
## Learning Loop -- 2026-04-22 14:08

- Split: training, Tasks: 80
- Correct: 79 / 80 (98.8%)
- Rules: 358 -> 359 (+1 learned)
- Stored rule hits: 77
- Time: 216s
- Log: logs/learn_20260422_140441.log

---
## Session 31 -- 2026-04-22 14:39

### Bug Fix: shape_stamp_fill (Strategy 65)
- Rewrote `_stamp_fill_grid` algorithm to fix e5062a87:
  1. **1D shape filter**: if template shape is a single row (or column), stamps
     are restricted to the same row (or column). Prevents false positives where
     unrelated 0-regions happen to match the shape geometry.
  2. **Isolation-score ordering**: positions sorted by ascending count of external
     0-neighbors (most "enclosed" first). Resolves overlapping stamp conflicts
     by preferring the position with fewer leak points.
  3. **Progressive stamping**: checks against evolving output grid so earlier
     stamps block conflicting later positions.
- Category: template replication / binary grid marker stamping (0/5/2 grids)
- Solved: e5062a87

### Learning Loop Results
- Split: training, Tasks: 80
- Correct: 80 / 80 (100.0%) — up from 79/80 (98.8%)
- Solved (new): e5062a87 (shape_stamp_fill)
- Rules: 359 -> 361 (+2 learned)
- Stored rule hits: 77
- Discovered: 3 new rules from pipeline
- Time: 187s
- Log: logs/learn_20260422_143647.log
- Regression: 08ed6ac7 CORRECT

---
## Learning Loop -- 2026-04-22 14:43

- Split: training, Tasks: 80
- Correct: 80 / 80 (100.0%)
- Rules: 361 -> 362 (+1 learned)
- Stored rule hits: 78
- Time: 198s
- Log: logs/learn_20260422_144032.log

---
## Session 32 -- 2026-04-22 15:39

### Strategies Added
1. **l_corner_complete** (Strategy 75): Grid has L-shaped groups of 3 cells
   (single fg color on bg=0), each forming 3 of 4 cells of a 2×2 box. Output
   marks the missing corner cell with a mark color. Detects components via
   flood-fill, filters to 3-cell L-shapes, fills missing 2×2 corner.
   Category: structural completion / L-shape corner detection.
   (solves 3aa6fb7a)
2. **quadrant_locator** (Strategy 76): Small even-dimensioned grid (e.g. 4×4)
   mostly filled with bg_color, with scattered non-bg values including a
   target_color appearing exactly once. Output fills the 2×2 quadrant
   containing target_color with that color, rest becomes bg.
   Category: spatial localization / quadrant expansion.
   (solves 87ab05b8)
3. **periodic_pattern_extend** (Strategy 77): Grid has a repeating tile pattern
   occupying most of the area, with a uniform border color filling the remaining
   edge (right cols, bottom rows, or L-shaped right+bottom). Each example may
   have a different border color and tile dimensions. Output extends the repeating
   tile to fill the entire grid, shifted by +1 column in the cycle.
   Category: pattern completion / periodic fill.
   (solves 50a16a69)

### Bug Fix
- Fixed `_try_periodic_pattern_extend` validation: was requiring border_color
  and tile dimensions to match across all training examples, but this task uses
  different border colors (1, 8, 4) and tile sizes (2×2, 2×4, 2×3) per example.
  Fixed to validate each example independently (border+tile detected per-input,
  only the shift rule must be consistent).

### Learning Loop Results
- Split: training, Tasks: 160 (expanded from 80; run hung at task 130, 129 completed)
- Correct: 87 / 129 (67.4%) — first 80 tasks: 80/80 (100.0%), new tasks: 7/49
- Solved (new): 3aa6fb7a (l_corner_complete), 87ab05b8 (quadrant_locator), 50a16a69 (periodic_pattern_extend)
- Errors: 1 (662c240a: list index out of range)
- Rules: 371 -> 379 (+8 learned)
- Time: ~370s (partial, 129/160 tasks)
- Log: logs/learn_20260422_153925.log
- Regression: 08ed6ac7 CORRECT

---
## Learning Loop -- 2026-04-22 15:39

- Split: training, Tasks: 80
- Correct: 80 / 80 (100.0%)
- Rules: 370 -> 371 (+1 learned)
- Stored rule hits: 78
- Time: 219s
- Log: logs/learn_20260422_153538.log

---
## Learning Loop -- 2026-04-22 16:26

- Split: training, Tasks: 160
- Correct: 87 / 160 (54.4%)
- Rules: 373 -> 376 (+3 learned)
- Stored rule hits: 85
- Time: 2030s
- Log: logs/learn_20260422_155259.log

---
## Session 33 -- 2026-04-22 17:31

### Bug Fixes
- Fixed `_apply_half_grid_boolean` crash: added bounds check when `bot_start + top_h > H`
  for grids that don't have equal halves below the separator row. Eliminated
  ERROR on task 662c240a.
- Fixed `_try_frame_hole_recolor` crash: added early return when input/output
  grid sizes differ. This was silently crashing the entire GeneralizeOperator
  for all tasks with different I/O dimensions, blocking the pipeline from
  reaching any strategies (including identity fallback). This fix unblocks
  all size-changing tasks.

### Strategies Added
1. **cluster_bbox_border** (Strategy 78): Scattered pixels of one color
   (marker) on background 0. Connected components (4-connected) of size >= 2
   get a rectangular border of border_color drawn 1 cell outside their
   bounding box. Isolated single pixels remain unchanged.
   Category: cluster detection / bounding box annotation.
   (solves b27ca6d3)
2. **crop_rect_flip** (Strategy 79): Input has a solid-colored rectangle
   (dominant color + minority pattern) on a zero background. Output = the
   rectangle cropped and horizontally flipped.
   Category: rectangle extraction + horizontal mirror.
   (solves 7468f01a)
3. **frame_extract** (Strategy 80): Input has a rectangular frame with
   corner_color at corners and edge_color on vertical edges, plus noise
   corner_color pixels scattered outside. Output = the frame rectangle
   cropped out, ignoring noise.
   Category: framed object extraction / noise removal.
   (solves 3f7978a0)

### Learning Loop Results
- Split: training, Tasks: 160
- Correct: 90 / 160 (56.2%) — up from 87/160 (54.4%)
- Errors: 0 (down from 1)
- Solved (new): b27ca6d3 (cluster_bbox_border), 7468f01a (crop_rect_flip), 3f7978a0 (frame_extract)
- Bug fix: 662c240a no longer ERROR (now INCORRECT identity)
- Rules: 377 -> 381 (+4 learned)
- Stored rule hits: 86
- Discovered: 6 new rules from pipeline
- Time: 2603s (16.3s/task)
- Log: logs/learn_20260422_164805.log
- Regression: 08ed6ac7 CORRECT

---
## Learning Loop -- 2026-04-22 17:47

- Split: training, Tasks: 160
- Correct: 90 / 160 (56.2%)
- Rules: 380 -> 381 (+1 learned)
- Stored rule hits: 88
- Time: 2477s
- Log: logs/learn_20260422_170554.log

---
## Learning Loop -- 2026-04-22 18:20

- Split: training, Tasks: 160
- Correct: 90 / 160 (56.2%)
- Rules: 381 -> 382 (+1 learned)
- Stored rule hits: 88
- Time: 1999s
- Log: logs/learn_20260422_174729.log

---
## Learning Loop -- 2026-04-22 19:17

- Split: training, Tasks: 160
- Correct: 93 / 160 (58.1%)
- Rules: 382 -> 388 (+6 learned)
- Stored rule hits: 88
- Time: 2738s
- Log: logs/learn_20260422_183129.log

---
## Learning Loop -- 2026-04-22 19:30

- Split: training, Tasks: 160
- Correct: 93 / 160 (58.1%)
- Rules: 386 -> 388 (+2 learned)
- Stored rule hits: 90
- Time: 2888s
- Log: logs/learn_20260422_184243.log

---
## Learning Loop -- 2026-04-22 19:34

- Split: training, Tasks: 160
- Correct: 93 / 160 (58.1%)
- Rules: 387 -> 388 (+1 learned)
- Stored rule hits: 90
- Time: 2449s
- Log: logs/learn_20260422_185356.log

---
## Learning Loop -- 2026-04-22 20:20

- Split: training, Tasks: 160
- Correct: 94 / 160 (58.8%)
- Rules: 388 -> 390 (+2 learned)
- Stored rule hits: 90
- Time: 2077s
- Log: logs/learn_20260422_194615.log

---
## Session 34 -- 2026-04-22 21:06

### Strategies Added
1. **marker_shape_extract** — Multiple colored shapes on black background; one has a marker pixel (color 8). Extract that shape's bounding box, replace marker with shape color. (solves 5117e062)
2. **template_placeholder_stamp** — One multi-color template shape + placeholder blocks (all same color, e.g. 5). Replace each placeholder with a copy of the template. (solves e76a88a6)
3. **unique_quadrant_extract** — Grid divided into 4 quadrants by zero-separators. Three quadrants share same color, one is unique. Extract the unique-color quadrant. (solves 0b148d64)
4. **self_ref_grid_fill** — Grid of NxN blocks separated by zero lines. Each block is filled with foreground color except one hole at position matching the block's grid coordinates. Fill missing blocks. (solves 9ddd00f0)

### Learning Loop Results
- Split: training, Tasks: 160
- Correct: 94 / 160 (58.8%) — up from 90/160 (56.2%) in session 33
- Newly solved: 5117e062 (marker_shape_extract), e76a88a6 (template_placeholder_stamp), 0b148d64 (unique_quadrant_extract), 9ddd00f0 (self_ref_grid_fill)
- Rules: 390 -> 391 (+1 learned)
- Stored rule hits: 91
- Errors: 0
- Time: 2067s
- Log: logs/learn_20260422_203159.log
- Regression: 08ed6ac7 CORRECT

---
## Learning Loop -- 2026-04-22 22:01

- Split: training, Tasks: 160
- Correct: 94 / 160 (58.8%)
- Rules: 391 -> 392 (+1 learned)
- Stored rule hits: 91
- Time: 2052s
- Log: logs/learn_20260422_212727.log

---
## Learning Loop -- 2026-04-22 22:49

- Split: training, Tasks: 160
- Correct: 95 / 160 (59.4%)
- Rules: 392 -> 398 (+6 learned)
- Stored rule hits: 91
- Time: 2538s
- Log: logs/learn_20260422_220649.log

---
## Learning Loop -- 2026-04-22 23:00

- Split: training, Tasks: 160
- Correct: 95 / 160 (59.4%)
- Rules: 395 -> 398 (+3 learned)
- Stored rule hits: 92
- Time: 2479s
- Log: logs/learn_20260422_221859.log

---
## Session 35 -- 2026-04-22 23:15

### Strategies Added
1. **point_reflect_tile** — NxM input → 2Nx2M output via 4-quadrant tiling with rot180/vflip/hflip/orig to create point symmetry (solves 0c786b71)
2. **nested_rect_color_reverse** — concentric rectangular layers have their unique color sequence reversed: outermost↔innermost via color remapping (solves 8dae5dfc)
3. **diagonal_ring_fill** — diagonal color markers at (0,0),(1,1),... plus hollow rect of 1s → fill interior with concentric rings using diagonal colors (solves 99306f82)

### Learning Loop Results
- Split: training, Tasks: 160
- Correct: 97 / 160 (60.6%) — up from 94/160 (58.8%)
- Solved: 0c786b71 (point_reflect_tile), 8dae5dfc (nested_rect_color_reverse), 99306f82 (diagonal_ring_fill)
- Rules: 397 -> 398 (+1 learned)
- Stored rule hits: 94
- Time: 2160s
- Log: logs/learn_20260422_223924.log
- Regression: 08ed6ac7 CORRECT
