
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
