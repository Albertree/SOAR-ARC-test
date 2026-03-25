
---
## Learning Loop -- 2026-03-25 00:32

- Split: training, Tasks: 20
- Correct: 0 / 20 (0.0%)
- Rules: 0 -> 3 (+3 learned)
- Stored rule hits: 0
- Time: 62s
- Log: logs/learn_20260325_003152.log

---
## Learning Loop -- 2026-03-25 00:40

- Split: training, Tasks: 20
- Correct: 3 / 20 (15.0%)
- Rules: 6 -> 9 (+3 learned)
- Stored rule hits: 3
- Time: 56s
- Log: logs/learn_20260325_003950.log

---
## Session 2 Analysis — 2026-03-25 00:39

### Strategies added (agent/active_operators.py)

1. **scale_up** — each input cell becomes an NxN block in the output (factor=2 for c59eb873)
   - `_try_scale_up`: detects uniform integer scaling across all example pairs
   - `_apply_scale_up`: expands each cell into factor×factor block

2. **flip_stack** — output is input stacked with its vertical or horizontal mirror
   - `_try_flip_stack`: checks if output = [original | reversed(original)] along one axis
   - `_apply_flip_stack`: concatenates original rows with reversed rows

3. **recolor_by_size** — connected components recolored by their cell-count rank
   - `_try_recolor_by_size`: verifies single source color, consistent size→color mapping
   - `_apply_recolor_by_size`: groups components, assigns colors by size lookup

### Results

| Task | Before | After | Rule |
|------|--------|-------|------|
| c59eb873 | INCORRECT (identity) | CORRECT | scale_up |
| 8be77c9e | INCORRECT (identity) | CORRECT | flip_stack |
| 6e82a1ae | INCORRECT (identity) | CORRECT | recolor_by_size |

**Score: 0/20 (0.0%) → 3/20 (15.0%)**

### Regression gate
- `python run_task.py` (08ed6ac7): CORRECT

---
## Learning Loop -- 2026-03-25 00:42

- Split: training, Tasks: 20
- Correct: 3 / 20 (15.0%)
- Rules: 9 -> 11 (+2 learned)
- Stored rule hits: 3
- Time: 57s
- Log: logs/learn_20260325_004139.log

---
## Session 3 Analysis — 2026-03-25 00:53

### Strategies added (agent/active_operators.py)

1. **ring_reversal** — concentric rectangular rings with reversed color order
   - `_try_ring_reversal`: detects nested rectangular frames, verifies color sequence reversal
   - `_apply_ring_reversal`: peels rings outside-in and reassigns reversed colors

2. **max_column** — keep only the column with the most non-zero entries
   - `_try_max_column`: finds dominant column, tie-break by closest to center; verifies all other cols zeroed
   - `_apply_max_column`: selects winning column, zeros everything else

3. **staircase_fill** — single row grows into a triangle (each row adds one more colored cell)
   - `_try_staircase_fill`: verifies 1-row input, contiguous color, W//2 output rows with incremental fill
   - `_apply_staircase_fill`: generates rows with count+0, count+1, ... colored cells

4. **corner_quadrant** — rectangular fill blocks with 4 diagonal corner markers; each quadrant gets its corner's color
   - `_try_corner_quadrant`: finds solid rectangular blocks of fill color, validates corner markers and quadrant output
   - `_apply_corner_quadrant`: splits each block into 4 quadrants, assigns corner colors, removes markers

### Results

| Task | Before | After | Rule |
|------|--------|-------|------|
| 85c4e7cd | INCORRECT (identity) | CORRECT | ring_reversal |
| d23f8c26 | INCORRECT (color_mapping) | CORRECT | max_column |
| bbc9ae5d | INCORRECT (identity) | CORRECT | staircase_fill |
| e9ac8c9e | INCORRECT (identity) | CORRECT | corner_quadrant |

**Score: 3/20 (15.0%) → 7/20 (35.0%)**

### Regression gate
- `python run_task.py` (08ed6ac7): CORRECT

---
## Learning Loop -- 2026-03-25 00:54

- Split: training, Tasks: 20
- Correct: 7 / 20 (35.0%)
- Rules: 11 -> 16 (+5 learned)
- Stored rule hits: 3
- Time: 58s
- Log: logs/learn_20260325_005304.log

---
## Learning Loop -- 2026-03-25 00:55

- Split: training, Tasks: 20
- Correct: 7 / 20 (35.0%)
- Rules: 16 -> 17 (+1 learned)
- Stored rule hits: 7
- Time: 59s
- Log: logs/learn_20260325_005453.log

---
## Session 4 Analysis — 2026-03-25 01:14

### Strategies added (agent/active_operators.py)

1. **fill_rect_interior** — rectangular frames (border of one color) with hollow interiors; fill color determined by interior area
   - `_try_fill_rect_interior`: finds rectangular frames via connected-component analysis, maps interior area → fill color across examples
   - `_apply_fill_rect_interior`: detects frames in test input, applies learned area→color mapping
   - Helper: `_find_rect_frames` — BFS to find hollow rectangular borders

2. **connect_diamonds** — diamond/cross shapes (4 cells in + pattern around empty center) connected by bridges when aligned
   - `_try_connect_diamonds`: finds diamonds, verifies bridges between adjacent pairs on same row/column
   - `_apply_connect_diamonds`: finds diamonds in test input, draws bridges between adjacent aligned pairs
   - Helper: `_find_diamonds` — scans for + patterns with diagonal check to avoid false positives

3. **stripe_zone_fill** — grid with a vertical stripe column and horizontal colored stripe rows; each stripe expands to fill its zone
   - `_try_stripe_zone_fill`: detects stripe column (no bg cells), stripe rows (uniform color with intersection marker), verifies Voronoi-style zone fill
   - `_apply_stripe_zone_fill`: dynamically detects stripe column/rows in test input, builds zone-filled output
   - Helper: `_detect_stripe_col`, `_build_stripe_zone_output`

### Results

| Task | Before | After | Rule |
|------|--------|-------|------|
| c0f76784 | INCORRECT (recolor_by_size) | CORRECT | fill_rect_interior |
| 60a26a3e | INCORRECT (color_mapping) | CORRECT | connect_diamonds |
| 332202d5 | INCORRECT (identity) | CORRECT | stripe_zone_fill |

**Score: 7/20 (35.0%) → 10/20 (50.0%)**

### Regression gate
- `python run_task.py` (08ed6ac7): CORRECT

---
## Learning Loop -- 2026-03-25 01:15

- Split: training, Tasks: 20
- Correct: 10 / 20 (50.0%)
- Rules: 17 -> 20 (+3 learned)
- Stored rule hits: 7
- Time: 58s
- Log: logs/learn_20260325_011412.log

---
## Learning Loop -- 2026-03-25 01:16

- Split: training, Tasks: 20
- Correct: 10 / 20 (50.0%)
- Rules: 20 -> 20 (+0 learned)
- Stored rule hits: 10
- Time: 59s
- Log: logs/learn_20260325_011558.log

---
## Learning Loop -- 2026-03-25 01:44

- Split: training, Tasks: 20
- Correct: 12 / 20 (60.0%)
- Rules: 20 -> 22 (+2 learned)
- Stored rule hits: 10
- Time: 59s
- Log: logs/learn_20260325_014338.log

---
## Learning Loop -- 2026-03-25 01:48

- Split: training, Tasks: 20
- Correct: 13 / 20 (65.0%)
- Rules: 22 -> 23 (+1 learned)
- Stored rule hits: 12
- Time: 58s
- Log: logs/learn_20260325_014737.log

---
## Session 5 Analysis — 2026-03-25 01:43

### Strategies added (agent/active_operators.py)

1. **path_turn_signals** — L-shaped path drawing from a start cell with turn signals
   - `_try_path_turn_signals`: finds unique start color (spreads in output), detects clockwise/ccw marker colors by testing both assignments against all training pairs
   - `_apply_path_turn_signals`: simulates path from start, turning clockwise at one marker color and counterclockwise at the other, extending to grid edge after last marker
   - Helper: `_simulate_turn_path` — core path simulation with direction vectors

2. **arrow_slide_mirror** — dots slide along arrow chains across a divider, mirrored to opposite half
   - `_try_arrow_slide_mirror`: finds uniform divider row, identifies dot/arrow colors in each half, validates slide+mirror displacement against all training pairs
   - `_apply_arrow_slide_mirror`: traces arrow chains via BFS walk, computes displacement for each dot, mirrors displacement vertically for corresponding dots above divider
   - Helper: `_walk_arrow_chain` — greedy chain walk from dot through adjacent arrow cells

3. **quadrant_shape_swap** — grid divided by separator rows/columns, horizontally paired regions swap patterns
   - `_try_quadrant_shape_swap`: parses grid into rectangular regions, verifies each horizontal pair swaps patterns with color = partner's background
   - `_apply_quadrant_shape_swap`: parses test grid regions, applies pattern swap with correct color substitution
   - Helper: `_parse_grid_regions` — detects separator color, extracts row/col ranges and per-region bg/pattern

### Results

| Task | Before | After | Rule |
|------|--------|-------|------|
| e5790162 | INCORRECT (recolor_sequential) | CORRECT | path_turn_signals |
| c9680e90 | INCORRECT (identity) | CORRECT | arrow_slide_mirror |
| 5a719d11 | INCORRECT (identity) | CORRECT | quadrant_shape_swap |

**Score: 10/20 (50.0%) → 13/20 (65.0%)**

### Regression gate
- `python run_task.py` (08ed6ac7): CORRECT

---
## Learning Loop -- 2026-03-25 01:50

- Split: training, Tasks: 20
- Correct: 13 / 20 (65.0%)
- Rules: 23 -> 23 (+0 learned)
- Stored rule hits: 13
- Time: 59s
- Log: logs/learn_20260325_014931.log

---
## Session 6 Analysis — 2026-03-25 02:21

### Strategies added (agent/active_operators.py)

1. **cross_border_project** — cross/arrow shapes project center marker color to grid borders
   - `_try_cross_border_project`: finds connected cross shapes (structural color + single center marker), determines missing arm direction (shortest arm), verifies projection rule against all training pairs
   - `_apply_cross_border_project`: finds crosses in test input, projects center color every 2 cells toward grid edge, fills border row/column, corners where two borders meet become 0
   - Helpers: `_find_arrow_crosses`, `_build_cross_border_output`, `_most_common_color`

2. **grid_zigzag** — rectangular grid shape oscillates with zigzag horizontal shifts
   - `_try_grid_zigzag`: verifies single non-bg color forming a grid, checks that from the bottom row upward, offsets cycle 0, -1, 0, +1
   - `_apply_grid_zigzag`: finds grid bounding box, applies cyclic zigzag shift to each row from bottom up

3. **block_slide_split** — three colored blocks in a line; middle slides through one outer block to grid boundary
   - `_try_block_slide_split`: groups non-bg cells by color (3 colors), determines arrangement axis, identifies which outer block is rectangular with perpendicular dim > middle, verifies output
   - `_apply_block_slide_split`: stay block unchanged, split block halves shift outward by middle's perpendicular size // 2, middle slides to grid edge toward split block
   - Helper: `_analyze_three_blocks`, `_build_block_slide_output`

### Results

| Task | Before | After | Rule |
|------|--------|-------|------|
| 13f06aa5 | INCORRECT (identity) | CORRECT | cross_border_project |
| 1c56ad9f | INCORRECT (identity) | CORRECT | grid_zigzag |
| 9f669b64 | INCORRECT (identity) | CORRECT | block_slide_split |

**Score: 13/20 (65.0%) → 16/20 (80.0%)**

### Regression gate
- `python run_task.py` (08ed6ac7): CORRECT

---
## Learning Loop -- 2026-03-25 02:23

- Split: training, Tasks: 20
- Correct: 16 / 20 (80.0%)
- Rules: 25 -> 26 (+1 learned)
- Stored rule hits: 15
- Time: 56s
- Log: logs/learn_20260325_022344.log

---
## Learning Loop -- 2026-03-25 02:22

- Split: training, Tasks: 20
- Correct: 15 / 20 (75.0%)
- Rules: 23 -> 25 (+2 learned)
- Stored rule hits: 13
- Time: 61s
- Log: logs/learn_20260325_022125.log

---
## Learning Loop -- 2026-03-25 02:24

- Split: training, Tasks: 20
- Correct: 16 / 20 (80.0%)
- Rules: 25 -> 26 (+1 learned)
- Stored rule hits: 15
- Time: 56s
- Log: logs/learn_20260325_022344.log

---
## Learning Loop -- 2026-03-25 02:26

- Split: training, Tasks: 20
- Correct: 16 / 20 (80.0%)
- Rules: 26 -> 26 (+0 learned)
- Stored rule hits: 16
- Time: 56s
- Log: logs/learn_20260325_022536.log

---
## Session 7 Analysis — 2026-03-25 03:25

### Strategies added (agent/active_operators.py)

1. **gravity_fall** — objects fall toward a border wall as rigid bodies, stopping with 1-cell gap
   - `_try_gravity_fall`: brute-forces all (bg, border, obj) color role assignments per training example; validates gravity computation against expected output
   - `_apply_gravity_fall`: auto-detects colors via edge-sides heuristic, applies gravity
   - `_compute_gravity_fall`: finds connected components of object color, sorts bottom-first, shifts each toward border (gap=1 to border, gap=0 between stacked objects)
   - `_identify_gravity_colors`: heuristic for test input: bg=most common, border=most edge sides among remaining

2. **count_diamond** — scattered dots of 2 non-bg colors counted; rectangle at bottom-left with V/diamond pattern
   - `_try_count_diamond`: counts exactly 2 non-bg colors, computes rect dims (w=max_count, h=min_count), output grid = max dims across training examples, verifies V/diamond pattern (fill=2, diagonals=4)
   - `_apply_count_diamond`: counts colors in test input, builds output with _build_count_diamond
   - `_build_count_diamond`: generates distance sequence (bottom-up: converge to center, bounce), draws diagonal 4s on fill of 2s

### Results

| Task | Before | After | Rule |
|------|--------|-------|------|
| 825aa9e9 | INCORRECT (identity) | CORRECT | gravity_fall |
| 878187ab | INCORRECT (identity) | CORRECT | count_diamond |

**Score: 16/20 (80.0%) → 18/20 (90.0%)**

### Regression gate
- `python run_task.py` (08ed6ac7): CORRECT

---
## Learning Loop -- 2026-03-25 03:25

- Split: training, Tasks: 20
- Correct: 18 / 20 (90.0%)
- Rules: 26 -> 28 (+2 learned)
- Stored rule hits: 16
- Time: 57s
- Log: logs/learn_20260325_032550.log

---
## Learning Loop -- 2026-03-25 03:12

- Split: training, Tasks: 20
- Correct: 16 / 20 (80.0%)
- Rules: 26 -> 26 (+0 learned)
- Stored rule hits: 16
- Time: 56s
- Log: logs/learn_20260325_031109.log

---
## Learning Loop -- 2026-03-25 03:13

- Split: training, Tasks: 20
- Correct: 16 / 20 (80.0%)
- Rules: 26 -> 26 (+0 learned)
- Stored rule hits: 16
- Time: 57s
- Log: logs/learn_20260325_031215.log

---
## Learning Loop -- 2026-03-25 03:26

- Split: training, Tasks: 20
- Correct: 18 / 20 (90.0%)
- Rules: 28 -> 28 (+0 learned)
- Stored rule hits: 17
- Time: 56s
- Log: logs/learn_20260325_032550.log

---
## Learning Loop -- 2026-03-25 03:28

- Split: training, Tasks: 20
- Correct: 18 / 20 (90.0%)
- Rules: 28 -> 28 (+0 learned)
- Stored rule hits: 17
- Time: 56s
- Log: logs/learn_20260325_032739.log

---
## Learning Loop -- 2026-03-25 03:47

- Split: training, Tasks: 20
- Correct: 20 / 20 (100.0%)
- Rules: 28 -> 30 (+2 learned)
- Stored rule hits: 17
- Time: 59s
- Log: logs/learn_20260325_034641.log

---
## Session 8 Analysis — 2026-03-25 03:47

### Strategies added (agent/active_operators.py)

1. **anchor_template_place** — template shapes with colored anchor points + scattered anchor pixels
   - `_try_anchor_template_place`: finds connected multi-color components (templates) and isolated single pixels (anchors); validates reconstruction on all training pairs
   - `_apply_anchor_template_place`: calls `_anchor_template_predict` — finds templates (body color + anchor colors), groups scattered anchors by trying all 8 orthogonal transforms, places transformed body + anchor pixels, removes originals
   - Handles: rotation (0/90/180/270), reflection (horizontal/vertical/diagonal), any combination

2. **block_count_gravity** — grid of 3x3 hollow squares with divider line of 1s on one edge
   - `_try_block_count_gravity`: detects 3x3 hollow blocks in grid layout, divider edge, zone separation; validates compressed output against all training pairs
   - `_apply_block_count_gravity`: calls `_block_gravity_predict` — parses blocks into a grid, splits into two spatial zones, counts blocks per zone per row/column, packs them toward the divider (top→right, bottom→left, right→down, left→up)
   - Both strategies use module-level helper functions shared between Generalize and Predict

### Results

| Task | Before | After | Rule |
|------|--------|-------|------|
| 0e206a2e | INCORRECT (identity) | CORRECT | anchor_template_place |
| afe3afe9 | INCORRECT (identity) | CORRECT | block_count_gravity |

**Score: 18/20 (90.0%) → 20/20 (100.0%)**

### Regression gate
- `python run_task.py` (08ed6ac7): CORRECT

---
## Learning Loop -- 2026-03-25 03:49

- Split: training, Tasks: 20
- Correct: 20 / 20 (100.0%)
- Rules: 30 -> 30 (+0 learned)
- Stored rule hits: 19
- Time: 59s
- Log: logs/learn_20260325_034823.log

---
## Learning Loop -- 2026-03-25 03:50

- Split: training, Tasks: 20
- Correct: 20 / 20 (100.0%)
- Rules: 30 -> 30 (+0 learned)
- Stored rule hits: 19
- Time: 59s
- Log: logs/learn_20260325_034955.log

---
## Learning Loop -- 2026-03-25 03:54

- Split: training, Tasks: 40
- Correct: 2 / 40 (5.0%)
- Rules: 30 -> 36 (+6 learned)
- Stored rule hits: 1
- Time: 181s
- Log: logs/learn_20260325_035120.log

---
## Learning Loop -- 2026-03-25 04:02

- Split: training, Tasks: 20
- Correct: 20 / 20 (100.0%)
- Rules: 36 -> 36 (+0 learned)
- Stored rule hits: 19
- Time: 59s
- Log: logs/learn_20260325_040107.log

---
## Learning Loop -- 2026-03-25 04:04

- Split: training, Tasks: 40
- Correct: 4 / 40 (10.0%)
- Rules: 36 -> 42 (+6 learned)
- Stored rule hits: 2
- Time: 154s
- Log: logs/learn_20260325_040218.log

---
## Learning Loop -- 2026-03-25 04:07

- Split: training, Tasks: 40
- Correct: 4 / 40 (10.0%)
- Rules: 42 -> 46 (+4 learned)
- Stored rule hits: 4
- Time: 154s
- Log: logs/learn_20260325_040500.log

---
## Learning Loop -- 2026-03-25 04:08

- Split: training, Tasks: 1
- Correct: 0 / 1 (0.0%)
- Rules: 46 -> 46 (+0 learned)
- Stored rule hits: 0
- Time: 0s
- Log: logs/learn_20260325_040846.log

---
## Learning Loop -- 2026-03-25 04:12

- Split: training, Tasks: 40
- Correct: 4 / 40 (10.0%)
- Rules: 46 -> 50 (+4 learned)
- Stored rule hits: 4
- Time: 153s
- Log: logs/learn_20260325_040934.log

---
## Learning Loop -- 2026-03-25 04:14

- Split: training, Tasks: 20
- Correct: 20 / 20 (100.0%)
- Rules: 50 -> 50 (+0 learned)
- Stored rule hits: 19
- Time: 59s
- Log: logs/learn_20260325_041358.log

---
## Learning Loop -- 2026-03-25 04:17

- Split: training, Tasks: 40
- Correct: 5 / 40 (12.5%)
- Rules: 50 -> 55 (+5 learned)
- Stored rule hits: 4
- Time: 155s
- Log: logs/learn_20260325_041506.log

---
## Session 8 (continued) Analysis — 2026-03-25 04:17

### Strategies added (agent/active_operators.py)

1. **cross_decorator** — isolated single-color pixels get cross (+) or diagonal (×) decorations
   - `_try_cross_decorator`: learns color→(pattern_type, deco_color) mapping from first pair; validates by building predicted output for all training pairs
   - `_apply_cross_decorator`: copies input, places decoration offsets (cross or diagonal) around each decorated color pixel

2. **tile_mirror** — output is 2× input dimensions with point-symmetric 2×2 tiling
   - `_try_tile_mirror`: verifies output = 2×height, 2×width; checks four quadrants: rot180 (top-left), vflip (top-right), hflip (bottom-left), original (bottom-right)
   - `_apply_tile_mirror`: constructs 2×2 tiling from the four transformations

3. **mask_nor** — two grid sections separated by uniform-color divider row; output = NOR
   - `_try_mask_nor`: finds divider row that splits grid into two equal halves matching output height; verifies result_color appears where both sections are 0
   - `_apply_mask_nor`: finds equal-split divider, outputs result_color at NOR positions

### Results

| Task | Before | After | Rule |
|------|--------|-------|------|
| 0ca9ddb6 | INCORRECT (identity) | CORRECT | cross_decorator |
| 0c786b71 | INCORRECT (identity) | CORRECT | tile_mirror |
| 0c9aba6e | INCORRECT (identity) | CORRECT | mask_nor |

**Score: 20/20 (100.0%) maintained on original 20-task set**
**Broader test (40 tasks, seed 42): 2/40 → 5/40**

### Regression gate
- `python run_task.py` (08ed6ac7): CORRECT

---
## Learning Loop -- 2026-03-25 04:20

- Split: training, Tasks: 20
- Correct: 20 / 20 (100.0%)
- Rules: 55 -> 55 (+0 learned)
- Stored rule hits: 19
- Time: 60s
- Log: logs/learn_20260325_041905.log

---
## Learning Loop -- 2026-03-25 04:22

- Split: training, Tasks: 40
- Correct: 20 / 40 (50.0%)
- Rules: 55 -> 60 (+5 learned)
- Stored rule hits: 19
- Time: 133s
- Log: logs/learn_20260325_042026.log

---
## Session 9 Analysis — 2026-03-25 04:32

### Strategies added (agent/active_operators.py)

1. **count_inside_frame** — rectangular frame of 1s with marker color scattered inside and outside; count interior markers, encode as filled 3x3
   - `_try_count_inside_frame`: finds rectangular frame of 1s, identifies single marker color (non-0, non-1), counts markers strictly inside frame interior, verifies output = 3x3 with first N cells filled left-to-right
   - `_apply_count_inside_frame`: detects frame, finds marker, counts interior occurrences, builds 3x3 output
   - Helper: `_find_one_frame` — locates bounding box of rectangular frame of 1s

2. **flood_fill_interior** — regions bounded by a boundary color; interior 0-cells unreachable from grid edge become fill color
   - `_try_flood_fill_interior`: determines boundary color (single non-0 non-fill color), fill color (what 0s change to), verifies flood-fill-from-edges algorithm matches all training outputs
   - `_apply_flood_fill_interior`: BFS from edge cells through non-boundary cells; remaining 0s become fill color
   - Helper: `_compute_flood_fill` — shared edge-flood algorithm used by both try and apply

3. **rotation_quad_tile** — output is 2× input dimensions (square grids only); four quadrants are 0°, 90°CCW, 180°, 90°CW rotations
   - `_try_rotation_quad_tile`: verifies output = 2H×2W, H==W, checks TL=original, TR=rot90ccw, BL=rot180, BR=rot90cw
   - `_apply_rotation_quad_tile`: builds four rotations and tiles into 2×2 quadrant output

### Results

| Task | Before | After | Rule |
|------|--------|-------|------|
| c8b7cc0f | INCORRECT (identity) | CORRECT | count_inside_frame |
| a5313dff | INCORRECT (color_mapping) | CORRECT | flood_fill_interior |
| ed98d772 | INCORRECT (identity) | CORRECT | rotation_quad_tile |

**Score on original 20-task set: 20/20 (100.0%) maintained**
**Broader test (40 tasks): 20/40 (50.0%) → 23/40 (57.5%)**

### Regression gate
- `python run_task.py` (08ed6ac7): CORRECT

---
## Learning Loop -- 2026-03-25 04:32

- Split: training, Tasks: 40
- Correct: 23 / 40 (57.5%)
- Rules: 67 -> 72 (+5 learned)
- Stored rule hits: 21
- Time: 122s
- Log: logs/learn_20260325_043051.log

---
## Learning Loop -- 2026-03-25 04:34

- Split: training, Tasks: 20
- Correct: 20 / 20 (100.0%)
- Rules: 72 -> 72 (+0 learned)
- Stored rule hits: 19
- Time: 61s
- Log: logs/learn_20260325_043319.log

---
## Learning Loop -- 2026-03-25 04:29

- Split: training, Tasks: 40
- Correct: 22 / 40 (55.0%)
- Rules: 60 -> 67 (+7 learned)
- Stored rule hits: 19
- Time: 121s
- Log: logs/learn_20260325_042742.log

---
## Learning Loop -- 2026-03-25 04:32

- Split: training, Tasks: 40
- Correct: 23 / 40 (57.5%)
- Rules: 67 -> 72 (+5 learned)
- Stored rule hits: 21
- Time: 122s
- Log: logs/learn_20260325_043011.log

---
## Learning Loop -- 2026-03-25 04:33

- Split: training, Tasks: 20
- Correct: 20 / 20 (100.0%)
- Rules: 72 -> 72 (+0 learned)
- Stored rule hits: 19
- Time: 61s
- Log: logs/learn_20260325_043218.log

---
## Learning Loop -- 2026-03-25 04:34

- Split: training, Tasks: 20
- Correct: 20 / 20 (100.0%)
- Rules: 72 -> 72 (+0 learned)
- Stored rule hits: 19
- Time: 60s
- Log: logs/learn_20260325_043324.log

---
## Learning Loop -- 2026-03-25 04:36

- Split: training, Tasks: 20
- Correct: 20 / 20 (100.0%)
- Rules: 72 -> 72 (+0 learned)
- Stored rule hits: 19
- Time: 60s
- Log: logs/learn_20260325_043523.log

---
## Learning Loop -- 2026-03-25 04:38

- Split: training, Tasks: 40
- Correct: 23 / 40 (57.5%)
- Rules: 72 -> 76 (+4 learned)
- Stored rule hits: 22
- Time: 122s
- Log: logs/learn_20260325_043644.log

---
## Learning Loop -- 2026-03-25 04:49

- Split: training, Tasks: 40
- Correct: 25 / 40 (62.5%)
- Rules: 76 -> 82 (+6 learned)
- Stored rule hits: 22
- Time: 120s
- Log: logs/learn_20260325_044712.log

---
## Learning Loop -- 2026-03-25 04:52

- Split: training, Tasks: 40
- Correct: 26 / 40 (65.0%)
- Rules: 82 -> 86 (+4 learned)
- Stored rule hits: 24
- Time: 117s
- Log: logs/learn_20260325_045035.log

---
## Learning Loop -- 2026-03-25 04:53

- Split: training, Tasks: 20
- Correct: 20 / 20 (100.0%)
- Rules: 86 -> 86 (+0 learned)
- Stored rule hits: 19
- Time: 58s
- Log: logs/learn_20260325_045238.log

---
## Session 10 Analysis — 2026-03-25 04:53

### Strategies added (agent/active_operators.py)

1. **diagonal_extend** — 2x2 block with diagonally adjacent single pixels; each tail pixel extended along its diagonal to grid edge
   - `_try_diagonal_extend`: finds 2x2 block of single non-zero color, identifies tail pixels at diagonal corners, verifies extension against all training pairs
   - `_apply_diagonal_extend`: locates 2x2 block and corner pixels, extends each along its diagonal direction

2. **core_quadrant_fill** — single 2x2 block of 4 distinct colors; surrounding quadrants each get diagonally opposite core color as 2x2 fill
   - `_try_core_quadrant_fill`: finds unique 2x2 block with 4 distinct non-zero colors, verifies quadrant fills (clipped to grid bounds) match output
   - `_apply_core_quadrant_fill`: finds 2x2 core, places 2x2 fills of diag-opposite colors in each corner quadrant

3. **noise_remove_rect** — single non-zero color with solid rectangular blocks plus scattered isolated pixels; removes all pixels not part of any 2x2+ solid block
   - `_try_noise_remove_rect`: verifies single non-zero color, checks that keeping only 2x2-member cells matches output for all training pairs
   - `_apply_noise_remove_rect`: scans for 2x2 blocks, keeps only cells belonging to at least one such block
   - Placed before color_mapping in priority chain to prevent false positive matching

### Results

| Task | Before | After | Rule |
|------|--------|-------|------|
| 7ddcd7ec | INCORRECT (identity) | CORRECT | diagonal_extend |
| 93b581b8 | INCORRECT (identity) | CORRECT | core_quadrant_fill |
| 7f4411dc | INCORRECT (color_mapping) | CORRECT | noise_remove_rect |

**Score on original 20-task set: 20/20 (100.0%) maintained**
**Broader test (40 tasks): 23/40 (57.5%) → 26/40 (65.0%)**

### Regression gate
- `python run_task.py` (08ed6ac7): CORRECT

---
## Learning Loop -- 2026-03-25 04:55

- Split: training, Tasks: 20
- Correct: 20 / 20 (100.0%)
- Rules: 86 -> 86 (+0 learned)
- Stored rule hits: 19
- Time: 58s
- Log: logs/learn_20260325_045440.log

---
## Learning Loop -- 2026-03-25 05:11

- Split: training, Tasks: 40
- Correct: 6 / 40 (15.0%)
- Rules: 86 -> 90 (+4 learned)
- Stored rule hits: 5
- Time: 152s
- Log: logs/learn_20260325_050840.log

---
## Learning Loop -- 2026-03-25 05:13

- Split: training, Tasks: 40
- Correct: 6 / 40 (15.0%)
- Rules: 90 -> 93 (+3 learned)
- Stored rule hits: 6
- Time: 150s
- Log: logs/learn_20260325_051126.log

---
## Learning Loop -- 2026-03-25 05:16

- Split: training, Tasks: 40
- Correct: 29 / 40 (72.5%)
- Rules: 93 -> 99 (+6 learned)
- Stored rule hits: 25
- Time: 119s
- Log: logs/learn_20260325_051408.log

---
## Learning Loop -- 2026-03-25 05:19

- Split: training, Tasks: 40
- Correct: 29 / 40 (72.5%)
- Rules: 99 -> 102 (+3 learned)
- Stored rule hits: 28
- Time: 119s
- Log: logs/learn_20260325_051735.log

---
## Learning Loop -- 2026-03-25 05:20

- Split: training, Tasks: 20
- Correct: 2 / 20 (10.0%)
- Rules: 102 -> 102 (+0 learned)
- Stored rule hits: 2
- Time: 78s
- Log: logs/learn_20260325_051939.log

---
## Learning Loop -- 2026-03-25 05:22

- Split: training, Tasks: 20
- Correct: 20 / 20 (100.0%)
- Rules: 102 -> 102 (+0 learned)
- Stored rule hits: 19
- Time: 59s
- Log: logs/learn_20260325_052103.log

---
## Session 11 Analysis — 2026-03-25 05:22

### Strategies added (agent/active_operators.py)

1. **frame_color_swap** — rectangular block of exactly 2 non-zero colors on zero background; extract and swap colors
   - `_try_frame_color_swap`: finds bounding box of non-zero cells, verifies exactly 2 colors, no zeros in block, swapped output matches
   - `_apply_frame_color_swap`: extracts block, swaps the two colors

2. **pattern_tile_fill** — uniform background fills top of grid, multi-row pattern at bottom; tile pattern upward to fill entire grid
   - `_try_pattern_tile_fill`: detects background rows, extracts pattern, verifies cyclic tiling matches output
   - `_apply_pattern_tile_fill`: tiles pattern using modular index from pattern start position

3. **template_color_remap** — rectangular block (all non-zero) plus scattered 2-cell key-value pairs on zero background; extract block and remap colors via keys
   - `_try_template_color_remap`: finds connected components (largest = block, 2-cell = key pairs), determines old→new mapping via block membership, verifies remapped output
   - `_apply_template_color_remap`: same detection logic applied to test input

### Results

| Task | Before | After | Rule |
|------|--------|-------|------|
| b94a9452 | INCORRECT (identity) | CORRECT | frame_color_swap |
| 9b30e358 | INCORRECT (identity) | CORRECT | pattern_tile_fill |
| e9b4f6fc | INCORRECT (identity) | CORRECT | template_color_remap |

**Score on original 20-task set: 20/20 (100.0%) maintained**
**Broader test (40 tasks): 26/40 (65.0%) → 29/40 (72.5%)**

### Regression gate
- `python run_task.py` (08ed6ac7): CORRECT

---
## Learning Loop -- 2026-03-25 05:24

- Split: training, Tasks: 20
- Correct: 20 / 20 (100.0%)
- Rules: 102 -> 102 (+0 learned)
- Stored rule hits: 19
- Time: 58s
- Log: logs/learn_20260325_052308.log

---
## Learning Loop -- 2026-03-25 05:25

- Split: training, Tasks: 20
- Correct: 20 / 20 (100.0%)
- Rules: 102 -> 102 (+0 learned)
- Stored rule hits: 19
- Time: 58s
- Log: logs/learn_20260325_052431.log

---
## Learning Loop -- 2026-03-25 05:26

- Split: training, Tasks: 20
- Correct: 3 / 20 (15.0%)
- Rules: 102 -> 107 (+5 learned)
- Stored rule hits: 2
- Time: 47s
- Log: logs/learn_20260325_052540.log

---
## Learning Loop -- 2026-03-25 05:31

- Split: training, Tasks: 20
- Correct: 5 / 20 (25.0%)
- Rules: 107 -> 114 (+7 learned)
- Stored rule hits: 2
- Time: 39s
- Log: logs/learn_20260325_053027.log

---
## Learning Loop -- 2026-03-25 05:32

- Split: training, Tasks: 20
- Correct: 19 / 20 (95.0%)
- Rules: 114 -> 114 (+0 learned)
- Stored rule hits: 19
- Time: 58s
- Log: logs/learn_20260325_053134.log

---
## Learning Loop -- 2026-03-25 05:35

- Split: training, Tasks: 20
- Correct: 20 / 20 (100.0%)
- Rules: 114 -> 114 (+0 learned)
- Stored rule hits: 19
- Time: 58s
- Log: logs/learn_20260325_053440.log

---
## Learning Loop -- 2026-03-25 05:36

- Split: training, Tasks: 20
- Correct: 6 / 20 (30.0%)
- Rules: 114 -> 118 (+4 learned)
- Stored rule hits: 5
- Time: 39s
- Log: logs/learn_20260325_053539.log

---
## Session 12 Analysis — 2026-03-25 05:24

### Context

All 20 tasks in the standard batch (seed 42) were already at 100%. Ran a new batch (seed 99) to find unsolved tasks: 3/20 correct. Picked 3 failing tasks and implemented strategies.

### Strategies added (agent/active_operators.py)

1. **marker_ray_fill** — isolated marker pixels fill rightward to grid edge, then downward along the right-edge column
   - `_try_marker_ray_fill`: verifies isolated non-zero markers on zero background; simulates L-fill and checks against expected output for all training pairs
   - `_apply_marker_ray_fill`: sorts markers by row, fills right to edge, fills down right-edge column until next marker row (or bottom)

2. **crop_bbox** — extract bounding box of non-background pixels from input grid
   - `_try_crop_bbox`: determines background (most common color), finds non-bg pixel bounding box, verifies extraction (bg→0) matches output for all training pairs
   - `_apply_crop_bbox`: finds bounding box, extracts region, replaces bg with 0

3. **binary_grid_xor** — input split by separator row into two binary halves; output is XOR of the two masks
   - `_try_binary_grid_xor`: finds uniform separator row, verifies each half is binary (0 vs one color), checks XOR matches output for all training pairs
   - `_apply_binary_grid_xor`: finds separator, extracts halves, XORs binary masks, maps result to output color

### Bug fix

- Fixed `_apply_binary_grid_xor` crash ("list index out of range") when separator row is at grid edge, causing `bot` to be empty. Added size guard returning `None` when halves are unequal.

### Results

| Task | Before | After | Rule |
|------|--------|-------|------|
| 99fa7670 | INCORRECT (identity) | CORRECT | marker_ray_fill |
| a740d043 | INCORRECT (identity) | CORRECT | crop_bbox |
| 99b1bc43 | INCORRECT (identity) | CORRECT | binary_grid_xor |

**Standard batch (seed 42): 20/20 (100.0%) — no regressions**
**New batch (seed 99): 3/20 (15.0%) → 6/20 (30.0%)**

### Regression gate
- `python run_task.py` (08ed6ac7): CORRECT

---
## Learning Loop -- 2026-03-25 05:38

- Split: training, Tasks: 20
- Correct: 20 / 20 (100.0%)
- Rules: 118 -> 118 (+0 learned)
- Stored rule hits: 19
- Time: 59s
- Log: logs/learn_20260325_053709.log

---
## Learning Loop -- 2026-03-25 05:39

- Split: training, Tasks: 20
- Correct: 20 / 20 (100.0%)
- Rules: 118 -> 118 (+0 learned)
- Stored rule hits: 19
- Time: 59s
- Log: logs/learn_20260325_053830.log

---
## Learning Loop -- 2026-03-25 05:40

- Split: training, Tasks: 20
- Correct: 6 / 20 (30.0%)
- Rules: 118 -> 122 (+4 learned)
- Stored rule hits: 5
- Time: 39s
- Log: logs/learn_20260325_053940.log

---
## Learning Loop -- 2026-03-25 05:48

- Split: training, Tasks: 20
- Correct: 20 / 20 (100.0%)
- Rules: 122 -> 122 (+0 learned)
- Stored rule hits: 19
- Time: 60s
- Log: logs/learn_20260325_054759.log

---
## Learning Loop -- 2026-03-25 05:49

- Split: training, Tasks: 20
- Correct: 9 / 20 (45.0%)
- Rules: 122 -> 129 (+7 learned)
- Stored rule hits: 5
- Time: 41s
- Log: logs/learn_20260325_054905.log

---
## Session 13 Analysis — 2026-03-25 05:38

### Input
- Default seed (42): 20/20 CORRECT (100%) — no failures in primary batch
- Ran seed 99 to find new failures: 6/20 CORRECT (30%), 14 INCORRECT

### Strategies added (agent/active_operators.py)

1. **nonzero_count_scale** — input NxN grid with K non-zero cells; output scales each cell to a KxK block (task ac0a08a4)
   - `_try_nonzero_count_scale`: counts non-zero cells, verifies scale factor matches, validates all blocks
   - `_apply_nonzero_count_scale`: expands each cell by the dynamic count factor

2. **stripe_rotate** — vertical colored stripes on right side collapse into a single cycling column (task e7b06bea)
   - `_try_stripe_rotate`: detects marker height (color 5) and uniform stripe columns, validates cycling output
   - `_apply_stripe_rotate`: builds output with cycling column at position width - num_stripes - 1

3. **frame_solid_compose** — same-sized colored rectangles: tile only hollow frames, ignore solid ones (task a680ac02)
   - `_try_frame_solid_compose`: finds colored rects, classifies frame vs solid, determines layout direction
   - `_apply_frame_solid_compose`: tiles frames horizontally (by col) or vertically (by row) based on spread

### Results
- Regression gate (08ed6ac7): CORRECT
- Default seed (42): 20/20 (100%) — no regression
- Seed 99: improved from 6/20 (30%) to 9/20 (45%) — 3 new tasks solved
- Stored rules: 118 → 122 (after seed 42 re-run) → 129 (after seed 99 run)

---
## Learning Loop -- 2026-03-25 05:51

- Split: training, Tasks: 20
- Correct: 20 / 20 (100.0%)
- Rules: 129 -> 129 (+0 learned)
- Stored rule hits: 19
- Time: 60s
- Log: logs/learn_20260325_055035.log

---
## Session 14 Analysis — 2026-03-25 06:07

### Input
- Default seed (42): 20/20 CORRECT (100%) — no failures in primary batch
- Ran seed 77 to find new failures: 2/20 CORRECT (10%), 18 INCORRECT

### Strategies added (agent/active_operators.py)

1. **self_tile** — NxN input grid tiled into N²xN² output; non-zero cells map to copies (or complement) of the input (tasks 007bbfb7, 0692e18c)
   - `_try_self_tile`: detects square input with one non-zero color, verifies NxN block structure, auto-detects "copy" vs "complement" mode
   - `_apply_self_tile`: builds N²xN² output, placing tile or zeros per input cell

2. **separator_and** — grid split by a separator column of uniform color; output = AND of left/right halves marked with a result color (task 0520fde7)
   - `_try_separator_and`: finds separator column, splits halves, validates AND logic across all examples
   - `_apply_separator_and`: finds separator, computes cell-wise AND of both halves

3. **checkerboard_tile** — HxW input tiled 3×3 with alternating horizontal flips on odd tile-rows (task 00576224)
   - `_try_checkerboard_tile`: verifies output is 3H×3W, validates even rows = normal, odd rows = h-flipped
   - `_apply_checkerboard_tile`: builds 3H×3W grid with alternating flip pattern

### Results
- Regression gate (08ed6ac7): CORRECT
- Default seed (42): 20/20 (100%) — no regression
- Seed 77: improved from 2/20 (10%) to 6/20 (30%) — 4 new tasks solved (00576224, 007bbfb7, 0520fde7, 0692e18c)
- Stored rules: 129 → 133 (after seed 77 re-run)

---
## Learning Loop -- 2026-03-25 06:07

- Split: training, Tasks: 20
- Correct: 20 / 20 (100.0%)
- Rules: 133 -> 133 (+0 learned)
- Stored rule hits: 19
- Time: 61s
- Log: logs/learn_20260325_060603.log

---
## Learning Loop -- 2026-03-25 06:05 (seed 77)

- Split: training, Tasks: 20
- Correct: 6 / 20 (30.0%)
- Rules: 133 -> 133 (+0 learned)
- Stored rule hits: 6
- Time: 84s
- Log: logs/learn_20260325_060433.log

---
## Learning Loop -- 2026-03-25 05:53

- Split: training, Tasks: 20
- Correct: 2 / 20 (10.0%)
- Rules: 129 -> 129 (+0 learned)
- Stored rule hits: 2
- Time: 84s
- Log: logs/learn_20260325_055202.log

---
## Learning Loop -- 2026-03-25 06:00

- Split: training, Tasks: 20
- Correct: 6 / 20 (30.0%)
- Rules: 129 -> 133 (+4 learned)
- Stored rule hits: 2
- Time: 84s
- Log: logs/learn_20260325_055911.log

---
## Learning Loop -- 2026-03-25 06:01

- Split: training, Tasks: 20
- Correct: 6 / 20 (30.0%)
- Rules: 133 -> 133 (+0 learned)
- Stored rule hits: 6
- Time: 82s
- Log: logs/learn_20260325_060035.log

---
## Learning Loop -- 2026-03-25 06:05

- Split: training, Tasks: 20
- Correct: 6 / 20 (30.0%)
- Rules: 133 -> 133 (+0 learned)
- Stored rule hits: 6
- Time: 84s
- Log: logs/learn_20260325_060433.log

---
## Learning Loop -- 2026-03-25 06:07

- Split: training, Tasks: 20
- Correct: 20 / 20 (100.0%)
- Rules: 133 -> 133 (+0 learned)
- Stored rule hits: 19
- Time: 61s
- Log: logs/learn_20260325_060603.log

---
## Learning Loop -- 2026-03-25 06:09

- Split: training, Tasks: 20
- Correct: 20 / 20 (100.0%)
- Rules: 133 -> 133 (+0 learned)
- Stored rule hits: 19
- Time: 61s
- Log: logs/learn_20260325_060801.log

---
## Learning Loop -- 2026-03-25 06:10

- Split: training, Tasks: 20
- Correct: 20 / 20 (100.0%)
- Rules: 133 -> 133 (+0 learned)
- Stored rule hits: 19
- Time: 61s
- Log: logs/learn_20260325_060922.log

---
## Learning Loop -- 2026-03-25 06:12

- Split: training, Tasks: 20
- Correct: 2 / 20 (10.0%)
- Rules: 133 -> 136 (+3 learned)
- Stored rule hits: 1
- Time: 85s
- Log: logs/learn_20260325_061040.log

---
## Learning Loop -- 2026-03-25 06:31

- Split: training, Tasks: 20
- Correct: 4 / 20 (20.0%)
- Rules: 136 -> 139 (+3 learned)
- Stored rule hits: 1
- Time: 72s
- Log: logs/learn_20260325_063022.log

---
## Learning Loop -- 2026-03-25 06:33

- Split: training, Tasks: 20
- Correct: 5 / 20 (25.0%)
- Rules: 139 -> 141 (+2 learned)
- Stored rule hits: 3
- Time: 70s
- Log: logs/learn_20260325_063226.log

---
## Learning Loop -- 2026-03-25 06:34

- Split: training, Tasks: 20
- Correct: 20 / 20 (100.0%)
- Rules: 141 -> 141 (+0 learned)
- Stored rule hits: 19
- Time: 62s
- Log: logs/learn_20260325_063342.log

---
## Session 15 Analysis — 2026-03-25 06:34

### Strategies added (agent/active_operators.py)

1. **point_to_line** — colored seed pixels expand to full-span row/column lines
   - `_try_point_to_line`: determines per-color axis (horizontal vs vertical) by coverage ratio; verifies reconstruction matches output with horizontal-over-vertical priority at intersections
   - `_apply_point_to_line`: draws vertical lines first, then horizontal on top

2. **quadrant_rotation_completion** — grid split by zero-separator into 4 quadrants; one is a uniform marker; output is the missing 90° rotation
   - `_try_quadrant_rotation_completion`: finds separator row/col, identifies uniform marker quadrant, verifies rot90cw of predecessor matches expected output
   - `_apply_quadrant_rotation_completion`: extracts quadrants, returns rot90cw of the predecessor quadrant

3. **stamp_pattern** — isolated marker pixels replaced by a fixed local pattern (kernel/stamp) centered on each marker
   - `_try_stamp_pattern`: learns stamp offsets from first marker in first pair, verifies all markers in all pairs reproduce the output
   - `_apply_stamp_pattern`: places learned stamp at each marker position in test input

### Results

| Task | Before | After | Rule |
|------|--------|-------|------|
| 178fcbfb | INCORRECT (identity) | CORRECT | point_to_line |
| be03b35f | INCORRECT (identity) | CORRECT | quadrant_rotation_completion |
| b60334d2 | INCORRECT (identity) | CORRECT | stamp_pattern |

**Score (seed 999): 2/20 (10.0%) → 5/20 (25.0%)**
**Score (seed 42, original 20): 20/20 (100.0%) — no regression**
**Stored rules: 133 → 141**

### Regression gate
- `python run_task.py` (08ed6ac7): CORRECT

---
## Learning Loop -- 2026-03-25 06:36

- Split: training, Tasks: 20
- Correct: 20 / 20 (100.0%)
- Rules: 141 -> 141 (+0 learned)
- Stored rule hits: 19
- Time: 60s
- Log: logs/learn_20260325_063543.log

---
## Learning Loop -- 2026-03-25 06:38

- Split: training, Tasks: 20
- Correct: 20 / 20 (100.0%)
- Rules: 141 -> 141 (+0 learned)
- Stored rule hits: 19
- Time: 61s
- Log: logs/learn_20260325_063704.log

---
## Learning Loop -- 2026-03-25 06:41

- Split: training, Tasks: 40
- Correct: 10 / 40 (25.0%)
- Rules: 141 -> 144 (+3 learned)
- Stored rule hits: 10
- Time: 195s
- Log: logs/learn_20260325_063840.log

---
## Learning Loop -- 2026-03-25 06:56

- Split: training, Tasks: 20
- Correct: 20 / 20 (100.0%)
- Rules: 144 -> 144 (+0 learned)
- Stored rule hits: 19
- Time: 62s
- Log: logs/learn_20260325_065531.log

---
## Learning Loop -- 2026-03-25 06:59

- Split: training, Tasks: 40
- Correct: 12 / 40 (30.0%)
- Rules: 144 -> 149 (+5 learned)
- Stored rule hits: 10
- Time: 196s
- Log: logs/learn_20260325_065639.log

---
## Learning Loop -- 2026-03-25 07:02

- Split: training, Tasks: 20
- Correct: 20 / 20 (100.0%)
- Rules: 149 -> 149 (+0 learned)
- Stored rule hits: 19
- Time: 61s
- Log: logs/learn_20260325_070116.log

---
## Session 16 Analysis — 2026-03-25 07:02

### Context

All 20 tasks in the standard batch were already CORRECT (100%). Ran with --limit 40 to find new unsolved tasks. Identified 3 failing tasks with generalizable patterns.

### Strategies added (agent/active_operators.py)

1. **global_color_swap** — cell-level 1:1 color remapping across entire grid
   - `_try_global_color_swap`: builds per-cell color mapping from all training pairs; verifies consistency
   - `_apply_global_color_swap`: applies the mapping to each cell
   - Fixes: existing `_try_color_mapping` fails when all cells change (single connected group has multiple input/output colors)

2. **quadrant_extract** — separator lines divide grid into 4 quadrants; extract shapes and tile 2x2
   - `_try_quadrant_extract`: finds full-span separator row+column (color varies per pair); extracts tight bounding box from each quadrant; verifies output = 2x2 tile
   - `_apply_quadrant_extract`: dynamically detects separator in test input, extracts and tiles shapes

3. **key_color_swap** — 2x2 key block in top-left corner defines pairwise color swaps
   - `_try_key_color_swap`: reads key [[A,B],[C,D]], builds swap A↔B, C↔D; verifies all non-bg cells outside key are swapped correctly
   - `_apply_key_color_swap`: reads key from test input and applies swaps

### Results

| Task | Before | After | Rule |
|------|--------|-------|------|
| 0d3d703e | INCORRECT (identity) | CORRECT | global_color_swap |
| 0bb8deee | INCORRECT (identity) | CORRECT | quadrant_extract |
| 0becf7df | INCORRECT (identity) | CORRECT | key_color_swap |

**Standard 20-task batch: 20/20 (100.0%) — no regression**
**Extended 40-task batch: 10/40 → 13/40 (+3 new solves)**

### Regression gate
- `python run_task.py` (08ed6ac7): CORRECT

---
## Learning Loop -- 2026-03-25 07:04

- Split: training, Tasks: 20
- Correct: 20 / 20 (100.0%)
- Rules: 149 -> 149 (+0 learned)
- Stored rule hits: 19
- Time: 61s
- Log: logs/learn_20260325_070307.log

---
## Learning Loop -- 2026-03-25 07:06

- Split: training, Tasks: 30
- Correct: 24 / 30 (80.0%)
- Rules: 149 -> 151 (+2 learned)
- Stored rule hits: 23
- Time: 119s
- Log: logs/learn_20260325_070424.log

---
## Learning Loop -- 2026-03-25 07:27

- Split: training, Tasks: 30
- Correct: 24 / 30 (80.0%)
- Rules: 151 -> 153 (+2 learned)
- Stored rule hits: 23
- Time: 118s
- Log: logs/learn_20260325_072505.log

---
## Learning Loop -- 2026-03-25 07:37

- Split: training, Tasks: 30
- Correct: 26 / 30 (86.7%)
- Rules: 153 -> 156 (+3 learned)
- Stored rule hits: 23
- Time: 118s
- Log: logs/learn_20260325_073521.log

---
## Learning Loop -- 2026-03-25 07:38

- Split: training, Tasks: 20
- Correct: 20 / 20 (100.0%)
- Rules: 156 -> 156 (+0 learned)
- Stored rule hits: 19
- Time: 61s
- Log: logs/learn_20260325_073727.log

---
## Session 17 Analysis — 2026-03-25 07:38

### Strategies added (agent/active_operators.py)

1. **mirror_symmetric_recolor** — for each row, cells of a single foreground color (e.g. 5) that have a mirror partner about the grid center column are recolored to a new color (e.g. 1); unpaired cells stay unchanged.
   - `_try_mirror_symmetric_recolor`: verifies single non-zero input color, single new output color, and bilateral symmetry rule across all training pairs
   - `_apply_mirror_symmetric_recolor`: for each foreground cell, checks mirror column; if partner exists, recolor
   - Category: bilateral symmetry detection / selective recoloring
   - Fixed task: ce039d91

2. **bar_frame_gravity** — grid has 4 colored bars (2 vertical full-height, 2 horizontal full-width) forming a rectangular frame. Scattered cells of one bar's color appear in the center section. Output = center section with bar borders, scattered cells cast shadows toward the matching bar (gravity direction determined by which bar's color matches the scattered cells).
   - `_try_bar_frame_gravity`: detects 4 bars, identifies scattered color and gravity direction, verifies output matches shadow prediction
   - `_apply_bar_frame_gravity`: extracts center section, applies directional shadow fill, adds bar borders with correct corner values from input intersections
   - Category: frame extraction with directional shadow projection
   - Fixed task: 5daaa586

3. **cross_center_mark** — on a uniform background with scattered foreground pixel-pairs (adjacent horizontal or vertical), finds cells equidistant from 4 surrounding pairs forming a cross pattern and marks them with a new color.
   - `_try_cross_center_mark`: detects 2-color input with 1 new output color, verifies cross-center logic
   - `_apply_cross_center_mark`: finds all fg-pairs, indexes by row/col, checks each bg cell for equidistant cross pattern
   - Category: geometric crosshair detection / center marking
   - Note: implemented speculatively; no matching task in current test set

### Results

- Previous (session 16 baseline): 20/20 (100%), 30-task expansion: 24/30 (80%)
- After session 17: 20/20 (100%), 30-task expansion: 26/30 (86.7%)
- New tasks solved: ce039d91 (mirror_symmetric_recolor), 5daaa586 (bar_frame_gravity)
- Remaining failures at 30 tasks: 7837ac64, a2d730bd, 9f5f939b, 6350f1f4
- Total stored rules: 156

---
## Learning Loop -- 2026-03-25 07:41

- Split: training, Tasks: 20
- Correct: 20 / 20 (100.0%)
- Rules: 156 -> 156 (+0 learned)
- Stored rule hits: 19
- Time: 61s
- Log: logs/learn_20260325_074000.log

---
## Learning Loop -- 2026-03-25 07:43

- Split: training, Tasks: 40
- Correct: 31 / 40 (77.5%)
- Rules: 156 -> 158 (+2 learned)
- Stored rule hits: 30
- Time: 155s
- Log: logs/learn_20260325_074113.log

---
## Learning Loop -- 2026-03-25 07:56

- Split: training, Tasks: 20
- Correct: 20 / 20 (100.0%)
- Rules: 158 -> 158 (+0 learned)
- Stored rule hits: 19
- Time: 61s
- Log: logs/learn_20260325_075512.log

---
## Learning Loop -- 2026-03-25 07:58

- Split: training, Tasks: 40
- Correct: 33 / 40 (82.5%)
- Rules: 158 -> 162 (+4 learned)
- Stored rule hits: 30
- Time: 143s
- Log: logs/learn_20260325_075617.log

---
## Learning Loop -- 2026-03-25 08:03

- Split: training, Tasks: 40
- Correct: 34 / 40 (85.0%)
- Rules: 162 -> 165 (+3 learned)
- Stored rule hits: 32
- Time: 155s
- Log: logs/learn_20260325_080031.log

---
## Learning Loop -- 2026-03-25 08:07

- Split: training, Tasks: 40
- Correct: 35 / 40 (87.5%)
- Rules: 165 -> 167 (+2 learned)
- Stored rule hits: 33
- Time: 155s
- Log: logs/learn_20260325_080433.log

---
## Learning Loop -- 2026-03-25 08:08

- Split: training, Tasks: 20
- Correct: 20 / 20 (100.0%)
- Rules: 167 -> 167 (+0 learned)
- Stored rule hits: 19
- Time: 61s
- Log: logs/learn_20260325_080713.log

---
## Session 18 Summary -- 2026-03-25 08:08

**Starting state:** 20/20 (100%) on base set, 31/40 (77.5%) on extended set

**New strategies added (4):**
1. `corner_L_extend` — isolated dots extend to nearest grid corner in L-shape (row + column arms). Fixes: 705a3229, cf5fd0ad
2. `rotation_quad_tile_4x` — NxN input → 4Nx4N output; 2x2 quadrants of 2x2 rotation tiles (TL=180°, TR=CW, BL=CCW, BR=0°). Fixes: cf5fd0ad
3. `rect_outline_decorate` — square outline shapes (hollow rect borders) get color-2 marks extending from each corner's edge directions. Fixes: 14b8e18c
4. `most_frequent_cross_color` — find cross patterns (color surrounding center=4), output the color appearing in most crosses. Fixes: 642d658d

**Ending state:** 20/20 (100%) on base set, 35/40 (87.5%) on extended set (+4 tasks fixed)

**Remaining failures (5/40):** 7837ac64, a2d730bd, 9f5f939b, 6350f1f4, 84db8fc4

---
## Learning Loop -- 2026-03-25 08:10

- Split: training, Tasks: 20
- Correct: 20 / 20 (100.0%)
- Rules: 167 -> 167 (+0 learned)
- Stored rule hits: 19
- Time: 61s
- Log: logs/learn_20260325_080900.log

---
## Learning Loop -- 2026-03-25 08:12

- Split: training, Tasks: 40
- Correct: 35 / 40 (87.5%)
- Rules: 167 -> 168 (+1 learned)
- Stored rule hits: 34
- Time: 143s
- Log: logs/learn_20260325_081025.log

---
## Learning Loop -- 2026-03-25 08:27

- Split: training, Tasks: 40
- Correct: 36 / 40 (90.0%)
- Rules: 168 -> 169 (+1 learned)
- Stored rule hits: 34
- Time: 143s
- Log: logs/learn_20260325_082523.log

---
## Learning Loop -- 2026-03-25 08:36

- Split: training, Tasks: 40
- Correct: 37 / 40 (92.5%)
- Rules: 170 -> 170 (+0 learned)
- Stored rule hits: 36
- Time: 142s
- Log: logs/learn_20260325_083352.log

---
## Learning Loop -- 2026-03-25 08:37

- Split: training, Tasks: 20
- Correct: 20 / 20 (100.0%)
- Rules: 170 -> 170 (+0 learned)
- Stored rule hits: 19
- Time: 61s
- Log: logs/learn_20260325_083625.log

---
## Session 19 Analysis — 2026-03-25 08:37

### Strategies modified/added (agent/active_operators.py)

1. **cross_center_mark** (priority fix) — moved before color_mapping in strategy order
   - Previously at strategy 46 (after color_mapping at strategy 5)
   - color_mapping was falsely matching 9f5f939b (bg→mark transition looked like 1:1 mapping)
   - Now runs before color_mapping to avoid false preemption

2. **grid_separator_invert** (new) — grid divided by 0-separator rows/cols into equal quadrants
   - `_try_grid_separator_invert`: detects 0-separator grid, base pattern vs blank quadrants, optional 5-corruption
   - `_apply_grid_separator_invert`: inverts base→all-majority, blank→base pattern, cleans separators
   - Per-example verification (base/colors vary across training examples within same task)
   - Category: grid partition inversion with noise marking

### Results

| Task | Before | After | Rule |
|------|--------|-------|------|
| 9f5f939b | INCORRECT (color_mapping) | CORRECT | cross_center_mark |
| 6350f1f4 | INCORRECT (identity) | CORRECT | grid_separator_invert |

**Score: 35/40 (87.5%) → 37/40 (92.5%)**
**Standard 20-task set: 20/20 (100%)**

### Regression gate
- `python run_task.py` (08ed6ac7): CORRECT

---
## Learning Loop -- 2026-03-25 08:39

- Split: training, Tasks: 20
- Correct: 20 / 20 (100.0%)
- Rules: 170 -> 170 (+0 learned)
- Stored rule hits: 19
- Time: 61s
- Log: logs/learn_20260325_083820.log

---
## Learning Loop -- 2026-03-25 08:42

- Split: training, Tasks: 40
- Correct: 37 / 40 (92.5%)
- Rules: 170 -> 170 (+0 learned)
- Stored rule hits: 36
- Time: 140s
- Log: logs/learn_20260325_083944.log

---
## Learning Loop -- 2026-03-25 08:50

- Split: training, Tasks: 40
- Correct: 38 / 40 (95.0%)
- Rules: 170 -> 171 (+1 learned)
- Stored rule hits: 36
- Time: 144s
- Log: logs/learn_20260325_084803.log

---
## Learning Loop -- 2026-03-25 08:58

- Split: training, Tasks: 40
- Correct: 39 / 40 (97.5%)
- Rules: 172 -> 172 (+0 learned)
- Stored rule hits: 38
- Time: 131s
- Log: logs/learn_20260325_085552.log

---
## Learning Loop -- 2026-03-25 08:59

- Split: training, Tasks: 20
- Correct: 20 / 20 (100.0%)
- Rules: 172 -> 172 (+0 learned)
- Stored rule hits: 19
- Time: 64s
- Log: logs/learn_20260325_085810.log

---
## Session 20 Analysis — 2026-03-25 08:38

### Strategies added (agent/active_operators.py)

1. **zero_region_classify** — 0-cells classified into edge-touching (exterior) vs fully-enclosed (interior) connected components, each colored differently
   - `_try_zero_region_classify`: finds 4-connected components of 0-cells, verifies edge-touching → color A, interior → color B consistently across all examples
   - `_apply_zero_region_classify`: flood-fill classifies 0-regions, assigns exterior/interior colors
   - Category: boundary/interior region classification

2. **grid_intersection_vote** — large grid with separator lines (no bg cells) → 3x3 output via 2×2 corner agreement at grid-line intersections
   - `_try_grid_intersection_vote`: finds grid-line rows/cols (no bg), identifies non-separator colors at intersections forming a 4×4 sub-grid, maps to 3×3 via unanimous 2×2 corner rule
   - `_apply_grid_intersection_vote`: applies same logic to test input
   - Category: grid-line intersection analysis / voting

### Bug fix

- **_build_count_diamond** (line 2857): added bounds check `if h > H or w > W: return None` to prevent `IndexError` when diamond dimensions exceed grid size. This bug was silently crashing `GeneralizeOperator.effect()` for any task where `_try_count_diamond` received oversized dimensions, preventing ALL subsequent strategies (including identity fallback) from running.

### Results

| Task | Before | After | Rule |
|------|--------|-------|------|
| 84db8fc4 | INCORRECT (none — crash in count_diamond) | CORRECT | zero_region_classify |
| 7837ac64 | INCORRECT (identity) | CORRECT | grid_intersection_vote |

**Score: 37/40 (92.5%) → 39/40 (97.5%)**
**Standard 20-task set: 20/20 (100%)**

### Regression gate
- `python run_task.py` (08ed6ac7): CORRECT

---
## Learning Loop -- 2026-03-25 09:01

- Split: training, Tasks: 20
- Correct: 20 / 20 (100.0%)
- Rules: 172 -> 172 (+0 learned)
- Stored rule hits: 19
- Time: 63s
- Log: logs/learn_20260325_090001.log

---
## Learning Loop -- 2026-03-25 09:02

- Split: training, Tasks: 20
- Correct: 20 / 20 (100.0%)
- Rules: 172 -> 172 (+0 learned)
- Stored rule hits: 19
- Time: 63s
- Log: logs/learn_20260325_090125.log

---
## Learning Loop -- 2026-03-25 09:04

- Split: training, Tasks: 20
- Correct: 1 / 20 (5.0%)
- Rules: 172 -> 175 (+3 learned)
- Stored rule hits: 1
- Time: 133s
- Log: logs/learn_20260325_090239.log

---
## Learning Loop -- 2026-03-25 09:12

- Split: training, Tasks: 20
- Correct: 4 / 20 (20.0%)
- Rules: 175 -> 181 (+6 learned)
- Stored rule hits: 1
- Time: 109s
- Log: logs/learn_20260325_091025.log

---
## Learning Loop -- 2026-03-25 09:13

- Split: training, Tasks: 20
- Correct: 20 / 20 (100.0%)
- Rules: 181 -> 181 (+0 learned)
- Stored rule hits: 19
- Time: 62s
- Log: logs/learn_20260325_091223.log

---
## Session 21 Analysis — 2026-03-25 09:10

### Context
All 20 default tasks (seed 42) passed at 100%. Ran with --seed 100 to find new failures (1/20 = 5%).

### Strategies added (agent/active_operators.py)

1. **sparse_grid_compress** — input grid divided into equal blocks, each with exactly one non-zero cell; output is the compressed grid of those values
   - `_try_sparse_grid_compress`: validates block divisibility, one-nonzero-per-block invariant across all training pairs
   - `_apply_sparse_grid_compress`: tries all valid block size divisors, extracts the single non-zero value from each block

2. **extract_unique_shape** — large grid with scattered noise pixels of multiple colors plus one small dense shape of a unique color; output is the bounding box of that shape
   - `_try_extract_unique_shape`: verifies single-color output, bounding box dimensions match, extracted content matches
   - `_apply_extract_unique_shape`: finds the color with smallest bounding box area (≥2 cells), extracts bbox keeping only that color

3. **shape_match_recolor** — one "template color" has shapes matching the forms of non-template colored shapes; each template gets recolored to its form-match's color
   - `_try_shape_match_recolor`: identifies the template color (only color that changes), validates shape-to-color matching via normalized connected components
   - `_apply_shape_match_recolor`: finds template components, builds shape→color map from references, recolors each template to its match

### Results

| Task | Before | After | Rule |
|------|--------|-------|------|
| 5783df64 | INCORRECT (identity) | CORRECT | sparse_grid_compress |
| 1f85a75f | INCORRECT (identity) | CORRECT | extract_unique_shape |
| 2a5f8217 | INCORRECT (identity) | CORRECT | shape_match_recolor |

**Score (seed 100): 1/20 (5.0%) → 4/20 (20.0%)**
**Score (seed 42): 20/20 (100.0%) — no regressions**

### Regression gate
- `python run_task.py` (08ed6ac7): CORRECT

---
## Learning Loop -- 2026-03-25 09:15

- Split: training, Tasks: 20
- Correct: 20 / 20 (100.0%)
- Rules: 181 -> 181 (+0 learned)
- Stored rule hits: 19
- Time: 61s
- Log: logs/learn_20260325_091427.log

---
## Learning Loop -- 2026-03-25 09:16

- Split: training, Tasks: 20
- Correct: 20 / 20 (100.0%)
- Rules: 181 -> 181 (+0 learned)
- Stored rule hits: 19
- Time: 62s
- Log: logs/learn_20260325_091549.log

---
## Learning Loop -- 2026-03-25 09:17

- Split: training, Tasks: 20
- Correct: 9 / 20 (45.0%)
- Rules: 181 -> 184 (+3 learned)
- Stored rule hits: 8
- Time: 46s
- Log: logs/learn_20260325_091707.log

---
## Learning Loop -- 2026-03-25 09:39

- Split: training, Tasks: 20
- Correct: 11 / 20 (55.0%)
- Rules: 184 -> 189 (+5 learned)
- Stored rule hits: 8
- Time: 43s
- Log: logs/learn_20260325_093817.log

---
## Learning Loop -- 2026-03-25 09:43

- Split: training, Tasks: 20
- Correct: 11 / 20 (55.0%)
- Rules: 189 -> 192 (+3 learned)
- Stored rule hits: 10
- Time: 43s
- Log: logs/learn_20260325_094235.log

---
## Learning Loop -- 2026-03-25 09:46

- Split: training, Tasks: 20
- Correct: 12 / 20 (60.0%)
- Rules: 192 -> 194 (+2 learned)
- Stored rule hits: 11
- Time: 43s
- Log: logs/learn_20260325_094519.log

---
## Learning Loop -- 2026-03-25 09:47

- Split: training, Tasks: 20
- Correct: 6 / 20 (30.0%)
- Rules: 194 -> 194 (+0 learned)
- Stored rule hits: 6
- Time: 83s
- Log: logs/learn_20260325_094609.log

---
## Learning Loop -- 2026-03-25 09:48

- Split: training, Tasks: 20
- Correct: 20 / 20 (100.0%)
- Rules: 194 -> 194 (+0 learned)
- Stored rule hits: 19
- Time: 60s
- Log: logs/learn_20260325_094738.log

---
## Session 22 Analysis — 2026-03-25 09:15

### Strategies added (agent/active_operators.py)

1. **l_triomino_extend** — L-shaped triominoes (3 cells in 2x2 bbox) extend a diagonal line from the missing corner outward to the grid edge
   - `_try_l_triomino_extend`: groups cells by 8-connectivity, verifies each group is 3 cells in 2x2 bbox, extends from missing corner
   - `_apply_l_triomino_extend`: same logic applied to test input

2. **rect_patch_overlay** — rectangular non-bg regions each contain a colored pattern; output is the overlay/union of all patches
   - `_try_rect_patch_overlay`: finds bg from border, BFS for non-bg regions, verifies same dimensions, overlays non-zero cells
   - `_apply_rect_patch_overlay`: same extraction and overlay applied to test input

3. **pair_diagonal_reflect** — same-color blocks arranged diagonally get anti-diagonal reflections placed with color 8, extended one block-step outward
   - `_try_pair_diagonal_reflect`: groups by 8-connectivity, detects diagonal quadrant arrangement, extends anti-diagonal
   - `_apply_pair_diagonal_reflect`: same diagonal extension applied to test input

### Results

| Task | Before | After | Rule |
|------|--------|-------|------|
| 6e19193c | INCORRECT (identity) | CORRECT | l_triomino_extend |
| 7c9b52a0 | INCORRECT (identity) | CORRECT | rect_patch_overlay |
| 22233c11 | INCORRECT (color_mapping) | CORRECT | pair_diagonal_reflect |

**Score (seed 99): 9/20 (45.0%) → 12/20 (60.0%)**

### Regression gate
- `python run_task.py` (08ed6ac7): CORRECT
- Original task set (default shuffle): 20/20 (100.0%)

---
## Learning Loop -- 2026-03-25 09:50

- Split: training, Tasks: 20
- Correct: 20 / 20 (100.0%)
- Rules: 194 -> 194 (+0 learned)
- Stored rule hits: 19
- Time: 58s
- Log: logs/learn_20260325_094937.log

---
## Learning Loop -- 2026-03-25 09:51

- Split: training, Tasks: 20
- Correct: 20 / 20 (100.0%)
- Rules: 194 -> 194 (+0 learned)
- Stored rule hits: 19
- Time: 59s
- Log: logs/learn_20260325_095054.log

---
## Learning Loop -- 2026-03-25 10:09

- Split: training, Tasks: 20
- Correct: 6 / 20 (30.0%)
- Rules: 202 -> 202 (+0 learned)
- Stored rule hits: 6
- Time: 81s
- Log: logs/learn_20260325_100753.log

---
## Session 23 Analysis — 2026-03-25 10:10

### Context

All 20 standard tasks at 100%. Expanded to tasks 20-40 to find new failures.

### Strategies added (agent/active_operators.py)

1. **recolor_by_holes** — connected components of a single color recolored by enclosed-hole count
   - `_try_recolor_by_holes`: finds all connected components, counts enclosed holes via flood-fill, maps hole-count to output color (1→1, 2→3, 3→2, 4→4)
   - `_apply_recolor_by_holes`: same flood-fill logic applied to test input

2. **stripe_tile** — two seed pixels define repeating vertical/horizontal stripes
   - `_try_stripe_tile`: detects exactly 2 non-bg pixels, determines axis by smaller gap, tiles stripes to grid edge
   - `_apply_stripe_tile`: reconstructs striped grid from seed pixels in test input

3. **diamond_symmetry_fill** — complete a partial diamond/lattice via 4-fold rotation
   - `_try_diamond_symmetry_fill`: finds bounding box center, applies 90° rotations to fill missing cells
   - `_apply_diamond_symmetry_fill`: same rotation logic on test input

### Results

| Task | Before | After | Rule |
|------|--------|-------|------|
| 0a2355a6 | INCORRECT (identity) | CORRECT | recolor_by_holes |
| 0a938d79 | INCORRECT (identity) | CORRECT | stripe_tile |
| 11852cab | INCORRECT (identity) | CORRECT | diamond_symmetry_fill |

**Extended batch (tasks 20-40): 7/20 → 10/20 (+3)**
**Original 20 tasks: 20/20 (no regression)**

### Regression gate
- `python run_task.py` (08ed6ac7): CORRECT

---
## Learning Loop -- 2026-03-25 10:14

- Split: training, Tasks: 20
- Correct: 20 / 20 (100.0%)
- Rules: 204 -> 204 (+0 learned)
- Stored rule hits: 19
- Time: 58s
- Log: logs/learn_20260325_101317.log

---
## Learning Loop -- 2026-03-25 10:15

- Split: training, Tasks: 20
- Correct: 20 / 20 (100.0%)
- Rules: 204 -> 204 (+0 learned)
- Stored rule hits: 19
- Time: 59s
- Log: logs/learn_20260325_101432.log

---
## Learning Loop -- 2026-03-25 10:17

- Split: training, Tasks: 40
- Correct: 39 / 40 (97.5%)
- Rules: 204 -> 204 (+0 learned)
- Stored rule hits: 38
- Time: 126s
- Log: logs/learn_20260325_101540.log

---
## Learning Loop -- 2026-03-25 10:21

- Split: training, Tasks: 60
- Correct: 41 / 60 (68.3%)
- Rules: 204 -> 207 (+3 learned)
- Stored rule hits: 39
- Time: 195s
- Log: logs/learn_20260325_101750.log

---
## Learning Loop -- 2026-03-25 10:29

- Split: training, Tasks: 60
- Correct: 41 / 60 (68.3%)
- Rules: 207 -> 209 (+2 learned)
- Stored rule hits: 39
- Time: 183s
- Log: logs/learn_20260325_102655.log

---
## Learning Loop -- 2026-03-25 10:35

- Split: training, Tasks: 60
- Correct: 44 / 60 (73.3%)
- Rules: 212 -> 214 (+2 learned)
- Stored rule hits: 42
- Time: 183s
- Log: logs/learn_20260325_103221.log

---
## Learning Loop -- 2026-03-25 10:36

- Split: training, Tasks: 20
- Correct: 20 / 20 (100.0%)
- Rules: 214 -> 214 (+0 learned)
- Stored rule hits: 19
- Time: 60s
- Log: logs/learn_20260325_103530.log

---
## Session 24 Analysis — 2026-03-25 10:35

### Context
- All 20 original tasks at 100% — expanded to 60 tasks to find new failures
- Previous run (60 tasks): 39/60 correct (65.0%)

### Strategies added (agent/active_operators.py)

1. **complement_tile** — binary grid inversion (0↔color swap) then tile 2×2
   - `_try_complement_tile`: detects single non-zero color, verifies output = inverted input tiled 2×2
   - `_apply_complement_tile`: inverts zeros and non-zero, tiles result 2×2
   - Category: complement tiling (any binary grid with invert+tile pattern)

2. **ring_color_cycle** — concentric rectangular frame color rotation
   - `_try_ring_color_cycle`: extracts uniform concentric rings, builds cyclic color mapping (each color → previous unique color)
   - `_apply_ring_color_cycle`: applies the cyclic mapping to all cells
   - Category: nested frame color permutation (any grid with uniform concentric rings)

3. **column_projection_tile** — fill active columns with marker color, tile 2×2
   - `_try_column_projection_tile`: identifies columns with non-zero cells, fills 0s in those columns with detected fill color, verifies tiling
   - `_apply_column_projection_tile`: applies column fill + 2×2 tiling
   - Category: column projection tiling (sparse binary grids with column emphasis)

### Results

| Task | Before | After | Rule |
|------|--------|-------|------|
| 48131b3c | INCORRECT (none) | CORRECT | complement_tile |
| bda2d7a6| INCORRECT (none) | CORRECT | ring_color_cycle |
| f5b8619d | INCORRECT (none) | CORRECT | column_projection_tile |

**Score (20 tasks): 20/20 (100.0%) — no regression**
**Score (60 tasks): 39/60 (65.0%) → 44/60 (73.3%) — +5 tasks**

### Regression gate
- `python run_task.py` (08ed6ac7): CORRECT

### Bug fix
- Fixed `task.training_pairs` → `task.example_pairs` (correct attribute name for Task object)

---
## Learning Loop -- 2026-03-25 10:38

- Split: training, Tasks: 20
- Correct: 20 / 20 (100.0%)
- Rules: 214 -> 214 (+0 learned)
- Stored rule hits: 19
- Time: 59s
- Log: logs/learn_20260325_103726.log

---
## Learning Loop -- 2026-03-25 10:39

- Split: training, Tasks: 20
- Correct: 20 / 20 (100.0%)
- Rules: 214 -> 214 (+0 learned)
- Stored rule hits: 19
- Time: 60s
- Log: logs/learn_20260325_103841.log

---
## Learning Loop -- 2026-03-25 10:40

- Split: training, Tasks: 20
- Correct: 20 / 20 (100.0%)
- Rules: 214 -> 214 (+0 learned)
- Stored rule hits: 19
- Time: 60s
- Log: logs/learn_20260325_103950.log

---
## Learning Loop -- 2026-03-25 10:46

- Split: training, Tasks: 40
- Correct: 13 / 40 (32.5%)
- Rules: 214 -> 220 (+6 learned)
- Stored rule hits: 12
- Time: 310s
- Log: logs/learn_20260325_104109.log

---
## Learning Loop -- 2026-03-25 11:00

- Split: training, Tasks: 40
- Correct: 16 / 40 (40.0%)
- Rules: 220 -> 229 (+9 learned)
- Stored rule hits: 12
- Time: 284s
- Log: logs/learn_20260325_105551.log

---
## Learning Loop -- 2026-03-25 11:02

- Split: training, Tasks: 20
- Correct: 6 / 20 (30.0%)
- Rules: 229 -> 229 (+0 learned)
- Stored rule hits: 6
- Time: 84s
- Log: logs/learn_20260325_110042.log

---
## Session 25 Analysis — 2026-03-25 11:00

### Strategies added (agent/active_operators.py)

1. **select_asymmetric_block** — input is K stacked NxN blocks; two are symmetric about the main diagonal, one is not; output = the asymmetric block
   - `_try_select_asymmetric_block`: checks transpose equality for each block, selects the one that differs
   - `_apply_select_asymmetric_block`: finds and returns the asymmetric block at test time
   - Category: block selection by symmetry property

2. **shape_complement_merge** — two colored shapes on a black background that interlock to fill a rectangle
   - `_try_shape_complement_merge`: finds two non-zero objects, normalizes their shapes, tries all offsets to tile a rectangle
   - `_apply_shape_complement_merge`: finds shapes, determines rectangle dimensions, merges them
   - Category: shape complement / jigsaw merge

3. **hub_assembly** — multiple shapes each adjacent to a color-5 anchor cell; output is a small grid with 5 at center
   - `_try_hub_assembly`: identifies hub (color 5) cells, maps each shape to its adjacent hub, computes relative offsets
   - `_apply_hub_assembly`: assembles shapes at their hub-relative offsets into output grid
   - Category: anchor-based shape assembly

### Tasks fixed

| Task     | Rule                    | Status |
|----------|-------------------------|--------|
| 662c240a | select_asymmetric_block | CORRECT (was INCORRECT/identity) |
| 681b3aeb | shape_complement_merge  | CORRECT (was INCORRECT/identity) |
| 137eaa0f | hub_assembly            | CORRECT (was INCORRECT/identity) |

### Verification

- Regression gate (08ed6ac7): CORRECT
- 40-task test (seed 99): 16/40 (40.0%) — up from 13/40 (32.5%), +3 correct
- Stored rules: 214 → 229
