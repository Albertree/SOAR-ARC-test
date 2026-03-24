
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
