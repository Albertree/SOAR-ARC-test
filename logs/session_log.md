
---
## Learning Loop -- 2026-04-29 07:50

- Split: None, Tasks: 20
- Correct: 0 / 20 (0.0%)
- Rules: 0 -> 3 (+3 learned)
- Stored rule hits: 0
- Time: 13s
- Log: logs/learn_20260429_075023.log

---
## Learning Loop -- 2026-04-29 07:52

- Split: None, Tasks: 20
- Correct: 2 / 20 (10.0%)
- Rules: 3 -> 5 (+2 learned)
- Stored rule hits: 0
- Time: 9s
- Log: logs/learn_20260429_075239.log

---
## Session 1 -- 2026-04-29 07:52

Added two generalization strategies in `agent/active_operators.py`:

- **`integer_upscale`** -- detects when output dimensions are k * input
  dimensions (same k for height and width across all examples) and each
  input cell becomes a kxk block of the same color. Solves c59eb873.
- **`stack_with_mirror`** -- detects when output is the input concatenated
  with a flipped copy of itself along an axis. Tries vertical/horizontal x
  input-first/flip-first (4 configurations). Solves 8be77c9e.

Verification:
- `python run_task.py` (regression on 08ed6ac7): CORRECT
- `python run_learn.py --limit 20 --shuffle`: 2 / 20 (10.0%), up from 0 / 20
  - 8be77c9e: CORRECT via stack_with_mirror
  - c59eb873: CORRECT via integer_upscale
- Rules: 3 -> 5 (+2 new strategies stored in procedural_memory/)

---
## Learning Loop -- 2026-04-29 07:53

- Split: None, Tasks: 20
- Correct: 2 / 20 (10.0%)
- Rules: 5 -> 5 (+0 learned)
- Stored rule hits: 2
- Time: 9s
- Log: logs/learn_20260429_075320.log

---
## Learning Loop -- 2026-04-29 07:58

- Split: None, Tasks: 20
- Correct: 4 / 20 (20.0%)
- Rules: 5 -> 7 (+2 learned)
- Stored rule hits: 2
- Time: 8s
- Log: logs/learn_20260429_075816.log

---
## Session 2 -- 2026-04-29 07:58

Added two generalization strategies in `agent/active_operators.py`:

- **`rect_interior_fill`** -- detects hollow rectangular borders of a single
  foreground color on a background, learns a map
  `(interior_h, interior_w) -> fill_color` from training pairs, and fills
  matching rectangle interiors in the test input. Solves c0f76784.
- **`staircase_extend_right`** -- detects 1-row inputs that produce
  triangular outputs of `w//2` rows where each row's colored prefix grows
  by one cell. Identifies fg as the leftmost cell and bg as the only
  other color (avoids a "most common color = bg" trap when fg fills most
  of the row). Solves bbc9ae5d.

Verification:
- `python run_task.py` (regression on 08ed6ac7): CORRECT
- `python run_learn.py --limit 20 --shuffle`: 4 / 20 (20.0%), up from 2 / 20
  - c0f76784: CORRECT via rect_interior_fill (pipeline)
  - bbc9ae5d: CORRECT via staircase_extend_right (pipeline)
  - 8be77c9e, c59eb873: CORRECT via stored rules
- Rules: 5 -> 7 (+2 new strategies stored in procedural_memory/)

---
## Learning Loop -- 2026-04-29 07:59

- Split: None, Tasks: 20
- Correct: 4 / 20 (20.0%)
- Rules: 7 -> 7 (+0 learned)
- Stored rule hits: 4
- Time: 8s
- Log: logs/learn_20260429_075851.log

---
## Learning Loop -- 2026-04-29 08:07

- Split: None, Tasks: 20
- Correct: 6 / 20 (30.0%)
- Rules: 10 -> 10 (+0 learned)
- Stored rule hits: 6
- Time: 9s
- Log: logs/learn_20260429_080656.log

---
## Session 3 -- 2026-04-29 08:07

Added two generalization strategies in `agent/active_operators.py`:

- **`corner_quadrant_fill`** -- detects N solid rectangles of one shared
  "inner color" each surrounded by 4 single-cell corner markers at the
  diagonal-adjacent positions. Each rectangle is replaced by 4 equal
  quadrants colored by the corresponding corner; the corner markers are
  cleared to background. Handles multiple groups per grid (test inputs
  often contain several inner rectangles even when training pairs each
  contain only one). Solves e9ac8c9e.
- **`diamond_connector`** -- detects '+'-shaped 4-cell objects (one
  foreground cell at each of N/S/E/W around an empty center, with all
  4 diagonals empty). Adjacent collinear diamonds (sharing a row or
  column with no other diamond between them) are joined by a line of a
  learned marker color through the cells strictly between their inner
  '+' tips. Solves 60a26a3e.

Verification:
- `python run_task.py` (regression on 08ed6ac7): CORRECT
- `python run_learn.py --limit 20 --shuffle`: 6 / 20 (30.0%), up from 4 / 20
  - e9ac8c9e: CORRECT via corner_quadrant_fill
  - 60a26a3e: CORRECT via diamond_connector
  - Existing 4 stored-rule hits remain CORRECT
- Rules: 7 -> 10 (+3 stored, including a recolor_sequential variant
  discovered for 08ed6ac7 during regression checks)

---
## Learning Loop -- 2026-04-29 08:08

- Split: None, Tasks: 20
- Correct: 6 / 20 (30.0%)
- Rules: 10 -> 10 (+0 learned)
- Stored rule hits: 6
- Time: 9s
- Log: logs/learn_20260429_080804.log

---
## Learning Loop -- 2026-04-29 08:12

- Split: None, Tasks: 40
- Correct: 9 / 40 (22.5%)
- Rules: 10 -> 16 (+6 learned)
- Stored rule hits: 6
- Time: 23s
- Log: logs/learn_20260429_081223.log

---
## Session 4 -- 2026-04-29 08:12

Added two generalization strategies in `agent/active_operators.py`:

- **`axis_line_keep`** -- detects when the output preserves a single row or
  column of the input verbatim and replaces every other cell with one
  uniform background color. The line position must be consistent across
  examples (currently the middle row or column). Solves d23f8c26 -- which
  the agent previously misclassified as `color_mapping` because every
  changed cell happened to map to 0. Inserted before `color_mapping` so
  the more specific projection rule wins.
- **`recolor_by_size`** -- detects inputs with one background and one
  foreground color where each connected component of the foreground is
  uniformly recolored in the output to a color that depends solely on its
  cell count. Learns a `size -> color` map across training pairs, requires
  consistency, and rejects if non-foreground cells change. Solves
  6e82a1ae (size 4 -> 1, 3 -> 2, 2 -> 3 in this category).

Verification:
- `python run_task.py` (regression on 08ed6ac7): CORRECT
- `python run_learn.py --limit 40 --shuffle`: 9 / 40 (22.5%), up from
  6 / 20 (30%) on the same training-prefix subset:
  - d23f8c26: CORRECT via axis_line_keep (pipeline, was INCORRECT)
  - 6e82a1ae: CORRECT via recolor_by_size (pipeline, was INCORRECT)
  - All 6 prior stored-rule wins still CORRECT
- Rules: 10 -> 16 (+6 stored after the 40-task expansion).

---
## Learning Loop -- 2026-04-29 08:13

- Split: None, Tasks: 40
- Correct: 9 / 40 (22.5%)
- Rules: 16 -> 16 (+0 learned)
- Stored rule hits: 9
- Time: 20s
- Log: logs/learn_20260429_081319.log

---
## Learning Loop -- 2026-04-29 08:22

- Split: None, Tasks: 40
- Correct: 12 / 40 (30.0%)
- Rules: 19 -> 19 (+0 learned)
- Stored rule hits: 12
- Time: 20s
- Log: logs/learn_20260429_082227.log

### Session 5 (Claude) -- new generalization strategies

Added 3 strategies to `agent/active_operators.py`:

- **rect_interior_marker_fill** -- hollow rectangular borders of fg get
  interior bg cells filled with a constant marker color (preserving any
  pre-existing interior fg cells). Solves a5313dff.
- **object_extract_swap** -- input has bg + exactly two non-bg colors A, B
  forming a single bounded object; output is the object's bbox with A and B
  swapped. The swap rule is universal (no fixed colors learned). Solves
  b94a9452.
- **keep_solid_rectangles** -- keep only fg cells that lie in some 2x2
  all-fg window; erase scattered/isolated fg cells to background. Handles
  L-shaped components by keeping only their solid rectangular sub-regions.
  Solves 7f4411dc.

Result: 9/40 (22.5%) -> 12/40 (30.0%). 3 new rules stored. Regression
gate (08ed6ac7) still CORRECT.

---
## Learning Loop -- 2026-04-29 08:23

- Split: None, Tasks: 40
- Correct: 12 / 40 (30.0%)
- Rules: 19 -> 19 (+0 learned)
- Stored rule hits: 12
- Time: 20s
- Log: logs/learn_20260429_082313.log

---
## Learning Loop -- 2026-04-29 08:31

- Split: None, Tasks: 40
- Correct: 15 / 40 (37.5%)
- Rules: 19 -> 22 (+3 learned)
- Stored rule hits: 12
- Time: 21s
- Log: logs/learn_20260429_083052.log

### Session 6 (Claude) -- new generalization strategies

Added 3 strategies to `agent/active_operators.py`:

- **tile_pattern_vertical** -- input has all-bg top rows and a non-bg
  pattern at the bottom; output tiles the pattern upward anchored to the
  bottom: `output[r] = pattern[(r - first_row) mod pattern_h]`. Solves
  9b30e358.
- **diagonal_tail_extend** -- one bg + one fg, with fg forming a single
  solid 2x2 block plus 0-4 tail cells at the diagonal-adjacent positions
  to the 2x2 corners. Each tail is extended one cell at a time in its
  diagonal direction to the grid edge. Solves 7ddcd7ec.
- **corner_diagonal_2x2** -- input is a single 2x2 of 4 DISTINCT non-bg
  colors on a uniform bg. Output places 2x2 blocks at offsets
  (+/-2, +/-2) from the source's top-left, each filled with the
  diagonally-opposite source cell's color (TL<->BR, TR<->BL), clipped to
  grid bounds. Solves 93b581b8.

Result: 12/40 (30.0%) -> 15/40 (37.5%). 3 new rules stored. Regression
gate (08ed6ac7) still CORRECT.

---
## Learning Loop -- 2026-04-29 08:32

- Split: None, Tasks: 40
- Correct: 15 / 40 (37.5%)
- Rules: 22 -> 22 (+0 learned)
- Stored rule hits: 15
- Time: 20s
- Log: logs/learn_20260429_083216.log

---
## Learning Loop -- 2026-04-29 08:41

- Split: None, Tasks: 40
- Correct: 18 / 40 (45.0%)
- Rules: 22 -> 25 (+3 learned)
- Stored rule hits: 15
- Time: 21s
- Log: logs/learn_20260429_084138.log

### Session 7 (Claude) -- new generalization strategies

Added 3 strategies to `agent/active_operators.py`:

- **rotational_quadrants_2x** -- square HxH input expands to a 2H x 2H
  output composed of 4 H x H quadrants of input rotations:
  TL = input, TR = rotate 90 CCW, BL = rotate 180, BR = rotate 90 CW.
  Solves ed98d772.
- **inside_marker_count_3x3** -- input has exactly 3 colors: bg
  (most common), a 'border' color whose cells are exactly the 4 sides
  of one axis-aligned rectangle, and a 'marker' color (the third
  color). Output is always 3x3 painted with N marker cells in
  row-major order (rest = bg) where N = count of marker cells
  strictly inside the rectangle. Solves c8b7cc0f.
- **corner_l_shoot** -- each isolated single-cell non-bg pixel projects
  an L-shape of its color toward the two grid edges that meet at its
  nearest Manhattan corner (vertical arm to (corner_r, c) plus
  horizontal arm to (r, corner_c)). Solves 705a3229.

Result: 15/40 (37.5%) -> 18/40 (45.0%). 3 new rules stored. Regression
gate (08ed6ac7) still CORRECT.

---
## Learning Loop -- 2026-04-29 08:43

- Split: None, Tasks: 40
- Correct: 18 / 40 (45.0%)
- Rules: 25 -> 25 (+0 learned)
- Stored rule hits: 18
- Time: 21s
- Log: logs/learn_20260429_084240.log

---
## Learning Loop -- 2026-04-29 08:50

- Split: None, Tasks: 40
- Correct: 20 / 40 (50.0%)
- Rules: 25 -> 27 (+2 learned)
- Stored rule hits: 18
- Time: 21s
- Log: logs/learn_20260429_085027.log

### Session 8 (Claude) -- new generalization strategies

Added 2 strategies to `agent/active_operators.py`:

- **concentric_ring_reverse** -- input is HxW (>=2 in each dim) tiled in
  concentric rectangular rings, where each ring (cells with
  min(r, h-1-r, c, w-1-c) == k) is painted a single uniform color and
  there are at least 2 distinct ring colors. Output is the same shape
  with the per-ring color sequence reversed (innermost color becomes
  outermost). Works on rectangular grids of any aspect ratio.
  Solves 85c4e7cd.
- **square_corner_marker** -- output introduces exactly one new color
  (the marker), consistent across all training pairs. For each
  non-background connected component whose bbox is a square (h == w
  >= 2) AND whose cells form either a complete hollow rectangle border
  or a fully solid filled square, the output places marker cells at
  the 8 positions orthogonally adjacent to the 4 bbox corners (one
  above/below and one left/right of each corner). Components that are
  isolated single cells, lines, or non-square rectangles are ignored.
  Solves 14b8e18c.

Result: 18/40 (45.0%) -> 20/40 (50.0%). 2 new rules stored. Regression
gate (08ed6ac7) still CORRECT.
