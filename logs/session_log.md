
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

---
## Learning Loop -- 2026-04-29 08:51

- Split: None, Tasks: 40
- Correct: 20 / 40 (50.0%)
- Rules: 27 -> 27 (+0 learned)
- Stored rule hits: 20
- Time: 21s
- Log: logs/learn_20260429_085124.log

---
## Learning Loop -- 2026-04-29 08:59

- Split: None, Tasks: 40
- Correct: 22 / 40 (55.0%)
- Rules: 27 -> 29 (+2 learned)
- Stored rule hits: 20
- Time: 20s
- Log: logs/learn_20260429_085918.log

---
## Learning Loop -- 2026-04-29 08:59

- Split: None, Tasks: 40
- Correct: 22 / 40 (55.0%)
- Rules: 27 -> 29 (+2 learned)
- Stored rule hits: 20
- Time: 20s
- Log: logs/learn_20260429_085918.log

### Session 9 (Claude) -- new generalization strategies

Added 2 strategies to `agent/active_operators.py`:

- **plus_center_marker** -- same grid size; output introduces exactly one
  new color (the marker), consistent across all training pairs. There is
  exactly one foreground color besides background. For each background
  cell (r, c) where the 8 cells at offsets (±2, 0), (±3, 0), (0, ±2),
  (0, ±3) are all foreground, the output places the marker at (r, c).
  All other cells are unchanged. Solves 9f5f939b.
- **rotational_4fold** -- square HxH input; output is 4H x 4H built from
  four rotated copies of the input, each tiled 2x2 inside its own
  half-grid quadrant: TL = rot180(input) tiled 2x2,
  TR = rot90CW(input) tiled 2x2, BL = rot90CCW(input) tiled 2x2,
  BR = input tiled 2x2. Solves cf5fd0ad.

Result: 20/40 (50.0%) -> 22/40 (55.0%). 2 new rules stored. Regression
gate (08ed6ac7) still CORRECT.

---
## Learning Loop -- 2026-04-29 09:00

- Split: None, Tasks: 40
- Correct: 22 / 40 (55.0%)
- Rules: 29 -> 29 (+0 learned)
- Stored rule hits: 22
- Time: 20s
- Log: logs/learn_20260429_090006.log

---
## Learning Loop -- 2026-04-29 09:08

- Split: None, Tasks: 40
- Correct: 24 / 40 (60.0%)
- Rules: 29 -> 31 (+2 learned)
- Stored rule hits: 22
- Time: 21s
- Log: logs/learn_20260429_090746.log

---
## Session 10 -- 2026-04-29 09:08

Added two generalization strategies in `agent/active_operators.py`:

- **`cross_zone_fill`** -- detects a single full-length 'main' line (one
  column or row) of color M, intersected by N >= 1 perpendicular
  cross-lines, each a uniform color C_i (with intersect color X at the
  cross). Background fills the rest with one color B. Output: each
  cross-line becomes all-X with M at the intersection (M and X swap at
  crosses); each background row/col is filled with the color of its
  NEAREST cross-line; ties between equally-distant cross-lines of
  DIFFERENT colors -> the entire row/col becomes X. Solves 332202d5.
- **`plus_majority_color`** -- detects 1x1 outputs derived from a
  'marker' color M scattered in the input, where each marker cell has
  all 4 cardinal neighbors equal to one common non-marker color V_i.
  Output is the most common V across all such markers (smallest color
  on tie). Solves 642d658d.

Verification:
- `python run_task.py` (regression on 08ed6ac7): CORRECT
- `python run_learn.py --limit 40 --shuffle`: 24 / 40 (60.0%), up from
  22 / 40 (55.0%)
  - 332202d5: CORRECT via cross_zone_fill (newly discovered)
  - 642d658d: CORRECT via plus_majority_color (newly discovered)
- Rules: 29 -> 31 (+2 new strategies stored in procedural_memory/)

---
## Learning Loop -- 2026-04-29 09:08

- Split: None, Tasks: 40
- Correct: 24 / 40 (60.0%)
- Rules: 31 -> 31 (+0 learned)
- Stored rule hits: 24
- Time: 21s
- Log: logs/learn_20260429_090838.log

---
## Learning Loop -- 2026-04-29 09:20

- Split: None, Tasks: 40
- Correct: 24 / 40 (60.0%)
- Rules: 31 -> 31 (+0 learned)
- Stored rule hits: 24
- Time: 24s
- Log: logs/learn_20260429_092008.log

---
## Learning Loop -- 2026-04-29 09:21

- Split: None, Tasks: 40
- Correct: 25 / 40 (62.5%)
- Rules: 31 -> 32 (+1 learned)
- Stored rule hits: 24
- Time: 24s
- Log: logs/learn_20260429_092118.log

---
## Session 11 -- 2026-04-29

**Strategy added:** `ricochet_ray`

Single 'shooter' cell (one-of-a-kind isolated non-bg pixel on a grid edge)
shoots a ray of its own color into the grid. Ray ricochets 90° off each
isolated 'marker' cell — each marker color has a learned fixed turn
direction (clockwise or counter-clockwise). Ray paints background cells
with shooter color and stops at the grid edge.

- Solves: e5790162 (and category of similar marker-ricochet tasks)
- Initial direction inferred from edge-position of shooter cell
- Marker turn direction (cw/ccw) learned per color from example pairs
- Placed BEFORE `recolor_sequential` to avoid false-positive matching
  (recolor_sequential was matching the bg-to-shooter cells as a single
  "recolor" group)

**Result:** 24/40 -> 25/40 (60.0% -> 62.5%), +1 rule learned (rule_032)

---
## Learning Loop -- 2026-04-29 09:22

- Split: None, Tasks: 40
- Correct: 25 / 40 (62.5%)
- Rules: 32 -> 32 (+0 learned)
- Stored rule hits: 25
- Time: 25s
- Log: logs/learn_20260429_092227.log

---
## Learning Loop -- 2026-04-29 09:33

- Split: None, Tasks: 40
- Correct: 26 / 40 (65.0%)
- Rules: 32 -> 33 (+1 learned)
- Stored rule hits: 25
- Time: 19s
- Log: logs/learn_20260429_093322.log

---
## Session 12 -- 2026-04-29

**Strategy added:** `mirror_shoot_anchor`

A full-row or full-column divider line of color D splits the grid into
two regions. The 'object' region contains connected components made
from two foreground colors: anchor A and pointer P. The 'marker' region
contains scattered cells of a third color M, each placed at the mirror
(across the divider) of an A cell. Output: each anchor moves to the
farthest connected pointer cell along its trail (BFS through P cells);
each marker moves to the mirror of the new anchor; original A, P and
M cells become background.

- Solves: c9680e90 (and category of mirror+pointer-trail tasks)
- Anchor color discovered by checking which color's cell positions
  mirror-match the marker positions across the divider.
- Both row and column dividers are supported.
- Placed BEFORE `recolor_sequential` (which would false-positive on
  these tasks since a 2 -> 6 recolor looks like a sequential recolor
  to the cell-level diff analysis).

**Result:** 25/40 -> 26/40 (62.5% -> 65.0%), +1 rule learned (rule_033)
- c9680e90: CORRECT via mirror_shoot_anchor (newly discovered)

Verification:
- `python run_task.py` (regression on 08ed6ac7): CORRECT
- `python run_learn.py --limit 40 --shuffle`: 26 / 40 (65.0%)
- Rules: 32 -> 33

---
## Learning Loop -- 2026-04-29 09:34

- Split: None, Tasks: 40
- Correct: 26 / 40 (65.0%)
- Rules: 33 -> 33 (+0 learned)
- Stored rule hits: 26
- Time: 19s
- Log: logs/learn_20260429_093417.log

---
## Learning Loop -- 2026-04-29 09:41

- Split: None, Tasks: 40
- Correct: 27 / 40 (67.5%)
- Rules: 33 -> 34 (+1 learned)
- Stored rule hits: 26
- Time: 19s
- Log: logs/learn_20260429_094056.log

---
## Session 13 -- 2026-04-29

**Strategy added:** `framed_recolor_legend`

A 'main' multi-color connected non-bg region (the largest 4-connected
component with >= 2 distinct colors) is accompanied by one or more
2-cell 'legend' pair components elsewhere in the grid. Each pair has
two distinct colors, one of which appears inside the main region (the
'source') and one which does not (the 'target'). The output is the
bbox of the main region with each source color recolored to its
partner target color; the frame color and other colors pass through
unchanged. The mapping is re-derived from the test input itself, so
no per-task parameters need to be learned.

- Solves: e9b4f6fc (and category of legend-driven inner-recolor tasks)
- Detection: largest non-bg 4-connected component with multi-colors is
  the 'main'; all remaining non-bg components must be exactly 2 cells
  of 2 distinct colors. Frame color = most common color in the main
  region; inner colors = the other colors in the main.
- Each legend pair uniquely maps source -> target by checking which of
  its two colors lies in the main's inner-color set.

**Result:** 26/40 -> 27/40 (65.0% -> 67.5%), +1 rule learned (rule_034)
- e9b4f6fc: CORRECT via framed_recolor_legend (newly discovered)

Verification:
- `python run_task.py` (regression on 08ed6ac7): CORRECT
- `python run_learn.py --limit 40 --shuffle`: 27 / 40 (67.5%)
- Rules: 33 -> 34

---
## Learning Loop -- 2026-04-29 09:42

- Split: None, Tasks: 40
- Correct: 27 / 40 (67.5%)
- Rules: 34 -> 34 (+0 learned)
- Stored rule hits: 27
- Time: 19s
- Log: logs/learn_20260429_094157.log

---
## Learning Loop -- 2026-04-29 09:47

- Split: None, Tasks: 40
- Correct: 28 / 40 (70.0%)
- Rules: 34 -> 35 (+1 learned)
- Stored rule hits: 27
- Time: 19s
- Log: logs/learn_20260429_094701.log

---
## Session 14 -- 2026-04-29

**Strategy added:** `interior_exterior_recolor`

A single input fill colour C is split in the output into two new colours:
X for cells that are 4-connected to the grid border through other C
cells (exterior open space), and Y for cells in fully enclosed pockets
(interior). All other input cells pass through unchanged. The triple
(C, X, Y) is verified consistent across every training example pair,
and the same triple is reused at test time.

- Solves: 84db8fc4 (and category of "label holes by enclosed-ness" tasks)
- Detection rejects pairs where multiple input colours disappear, where
  C maps to anything other than exactly two output colours, where any
  non-C cell changes, or where flood-fill produces an inconsistent
  side-to-side mapping.
- Placed after `framed_recolor_legend` and before `color_mapping`.

**Result:** 27/40 -> 28/40 (67.5% -> 70.0%), +1 rule learned (rule_035)
- 84db8fc4: CORRECT via interior_exterior_recolor (newly discovered)

Verification:
- `python run_task.py` (regression on 08ed6ac7): CORRECT
- `python run_learn.py --limit 40 --shuffle`: 28 / 40 (70.0%)
- Rules: 34 -> 35

---
## Learning Loop -- 2026-04-29 09:48

- Split: None, Tasks: 40
- Correct: 28 / 40 (70.0%)
- Rules: 35 -> 35 (+0 learned)
- Stored rule hits: 28
- Time: 18s
- Log: logs/learn_20260429_094756.log

---
## Learning Loop -- 2026-04-29 09:58

- Split: None, Tasks: 40
- Correct: 28 / 40 (70.0%)
- Rules: 35 -> 35 (+0 learned)
- Stored rule hits: 28
- Time: 19s
- Log: logs/learn_20260429_095822.log

---
## Learning Loop -- 2026-04-29 09:59

- Split: None, Tasks: 40
- Correct: 28 / 40 (70.0%)
- Rules: 35 -> 35 (+0 learned)
- Stored rule hits: 28
- Time: 19s
- Log: logs/learn_20260429_095847.log

---
## Learning Loop -- 2026-04-29 10:01

- Split: None, Tasks: 40
- Correct: 29 / 40 (72.5%)
- Rules: 35 -> 36 (+1 learned)
- Stored rule hits: 28
- Time: 20s
- Log: logs/learn_20260429_100138.log

---
## Learning Loop -- 2026-04-29 10:02

- Split: None, Tasks: 40
- Correct: 29 / 40 (72.5%)
- Rules: 36 -> 36 (+0 learned)
- Stored rule hits: 29
- Time: 19s
- Log: logs/learn_20260429_100201.log

---
## Session 15 -- 2026-04-29

**Strategy added:** `grid_summary_corners`

Input is a large grid containing a background colour (the cells between
gridlines) and a 'gridline' colour that forms complete non-bg rows and
columns at regular intervals. Some intersections of those gridlines
carry a third 'marker' colour. Output is a small grid of size
`(#marker_rows - 1) x (#marker_cols - 1)` where marker_rows/cols are
gridline rows/cols that contain at least one marker cell. For each
output cell `(i, j)`, the four corner intersections of the gridline
rectangle bounded by `marker_rows[i..i+1] x marker_cols[j..j+1]` are
checked: if all 4 hold the same marker colour, the output cell takes
that colour; otherwise it is background.

- Solves: 7837ac64 (and category of "corner-marker grid summary" tasks)
- Detection iterates candidate bg colours by descending frequency
  rather than blindly taking the most common, because in some pairs
  the gridline colour outnumbers the bg (e.g. 4 outnumbers 0 in
  pair 0 of 7837ac64).
- Gridline colour is the most common non-bg colour along gridline rows.
- Placed after `interior_exterior_recolor` and before `color_mapping`
  so the specific summary rule wins over generic recolour fits.

**Result:** 28/40 -> 29/40 (70.0% -> 72.5%), +1 rule learned (rule_036)
- 7837ac64: CORRECT via grid_summary_corners (newly discovered)

Verification:
- `python run_task.py` (regression on 08ed6ac7): CORRECT
- `python run_learn.py --limit 40 --shuffle`: 29 / 40 (72.5%)
- Rules: 35 -> 36

---
## Learning Loop -- 2026-04-29 10:03

- Split: None, Tasks: 40
- Correct: 29 / 40 (72.5%)
- Rules: 36 -> 36 (+0 learned)
- Stored rule hits: 29
- Time: 19s
- Log: logs/learn_20260429_100302.log

---
## Learning Loop -- 2026-04-29 10:16

- Split: None, Tasks: 40
- Correct: 29 / 40 (72.5%)
- Rules: 36 -> 36 (+0 learned)
- Stored rule hits: 29
- Time: 19s
- Log: logs/learn_20260429_101557.log

---
## Learning Loop -- 2026-04-29 10:17

- Split: None, Tasks: 40
- Correct: 30 / 40 (75.0%)
- Rules: 36 -> 37 (+1 learned)
- Stored rule hits: 29
- Time: 19s
- Log: logs/learn_20260429_101718.log

---
## Session 16 -- 2026-04-29 10:17

**New strategy: `anchor_dotted_ray`**
Each connected non-bg component is one filler color plus a single anchor cell with a unique color and exactly one open cardinal direction (no shape cells along that ray to the edge). Output adds, per anchor, a dotted ray (every other cell, starting at offset 2) of anchor color in the open direction, plus a full boundary edge fill of anchor color. Where two rays' boundary edges meet at a corner, the cell is reset to 0.

**Solved**: 13f06aa5 (anchor + dotted ray to edge with full boundary fill)
**Score**: 29/40 -> 30/40 (72.5% -> 75.0%)
**Rules**: 36 -> 37 (+1 learned)

---
## Learning Loop -- 2026-04-29 10:18

- Split: None, Tasks: 40
- Correct: 30 / 40 (75.0%)
- Rules: 37 -> 37 (+0 learned)
- Stored rule hits: 30
- Time: 19s
- Log: logs/learn_20260429_101817.log

---
## Learning Loop -- 2026-04-29 10:27

- Split: None, Tasks: 40
- Correct: 31 / 40 (77.5%)
- Rules: 37 -> 38 (+1 learned)
- Stored rule hits: 30
- Time: 19s
- Log: logs/learn_20260429_102735.log

---
## Learning Loop -- 2026-04-29 10:28

- Split: None, Tasks: 40
- Correct: 31 / 40 (77.5%)
- Rules: 38 -> 38 (+0 learned)
- Stored rule hits: 31
- Time: 19s
- Log: logs/learn_20260429_102758.log

---
## Session 17 -- 2026-04-29

- Target task: 5daaa586 (directional line extract)
- New strategy: `directional_line_extract`
  - Detects 4 full-line borders (2 rows + 2 cols, distinct non-bg colors) framing a sub-rectangle
  - Identifies a "noise" color among scattered interior cells that matches exactly one border
  - Outputs the bounded sub-rectangle (borders preserved from input) with each interior noise
    cell extended into a straight line toward its matching border
- Result: 30/40 -> 31/40 (75.0% -> 77.5%), +1 rule learned
- run_task.py 08ed6ac7: CORRECT (regression gate passing)

---
## Learning Loop -- 2026-04-29 10:29

- Split: None, Tasks: 40
- Correct: 31 / 40 (77.5%)
- Rules: 38 -> 38 (+0 learned)
- Stored rule hits: 31
- Time: 19s
- Log: logs/learn_20260429_102852.log

---
## Learning Loop -- 2026-04-29 10:39

- Split: None, Tasks: 40
- Correct: 32 / 40 (80.0%)
- Rules: 38 -> 39 (+1 learned)
- Stored rule hits: 31
- Time: 18s
- Log: logs/learn_20260429_103930.log

---
## Learning Loop -- 2026-04-29 10:45

- Split: None, Tasks: 40
- Correct: 33 / 40 (82.5%)
- Rules: 39 -> 40 (+1 learned)
- Stored rule hits: 32
- Time: 19s
- Log: logs/learn_20260429_104505.log

---
## Session 18 -- 2026-04-29

Targeted failures: 6350f1f4, 5a719d11.

Added two strategies in `agent/active_operators.py`:

- **quadrant_repair** — input is split by mostly-bg row(s)/col(s) into a regular N×M grid of equal-sized quadrants. Iterates candidate bg colors so the divider color need not be the most common. Each quadrant's dominant color is computed; the most common dominant becomes the *primary*. A canonical pattern is built by per-cell majority vote across primary-dominant quadrants. Output: any quadrant containing the primary color is filled with all-primary; any quadrant lacking the primary (only accent + noise) receives the canonical pattern. Divider rows/cols are wiped to bg. Solves 6350f1f4 and any future "voted-canonical" repair task.

- **panel_swap** — grid is split by uniform-bg rows into stacked panels; each panel is split by a contiguous uniform-bg column run into Left/Right halves of equal width. Each side has its own sub-bg and a noise-colored shape. Output swaps shapes between sides when their sub-bgs differ, recoloring the moved shape to the destination side's noise role (= source side's sub-bg). Same-bg panels become uniform bg. Solves 5a719d11 and any "two-cell symmetric panel swap" task.

Result: 31/40 → 33/40 (77.5% → 82.5%), +2 stored rules.

---
## Learning Loop -- 2026-04-29 10:46

- Split: None, Tasks: 40
- Correct: 33 / 40 (82.5%)
- Rules: 40 -> 40 (+0 learned)
- Stored rule hits: 33
- Time: 19s
- Log: logs/learn_20260429_104600.log

---
## Learning Loop -- 2026-04-29 11:02

- Split: None, Tasks: 40
- Correct: 34 / 40 (85.0%)
- Rules: 40 -> 41 (+1 learned)
- Stored rule hits: 33
- Time: 20s
- Log: logs/learn_20260429_110156.log

---
## Session 19 -- 2026-04-29 11:02

Added one generalization strategy in `agent/active_operators.py`:

- **`template_replication`** -- detects inputs that contain one or more
  "template" connected components (each with a connector color used multiple
  times plus distinct anchor colors used exactly once each) and "scattered"
  anchor cells outside the templates. The output erases all templates and
  redraws the matching template at each scattered group's anchor positions
  under one of 8 d8 transformations (rotations + reflections). Solves
  0e206a2e, which has multiple templates of different shapes; each
  scattered group is matched to whichever template's anchor offsets fit.

Verification:
- `python run_task.py` (regression on 08ed6ac7): CORRECT
- `python run_learn.py --limit 40 --shuffle`: 34 / 40 (85.0%), up from 33 / 40
  - 0e206a2e: CORRECT via template_replication (newly discovered)
- Rules: 40 -> 41 (+1 new strategy stored)

Remaining failures (6): 878187ab (size mismatch 15->16), 825aa9e9
(gravity within enclosed regions), 1c56ad9f (perspective-shear projection),
9f669b64 (three-shape Newton's-cradle interaction), afe3afe9 (output size
differs from input — shape extraction with palette), a2d730bd (rect+dot
arrow projection with asymmetric special cases).

---
## Learning Loop -- 2026-04-29 11:03

- Split: None, Tasks: 40
- Correct: 34 / 40 (85.0%)
- Rules: 41 -> 41 (+0 learned)
- Stored rule hits: 34
- Time: 19s
- Log: logs/learn_20260429_110249.log

---
## Session 20 -- 2026-04-29 11:03

No new strategy added this session. Investigated all 6 INCORRECT tasks
(878187ab, 825aa9e9, 1c56ad9f, 9f669b64, afe3afe9, a2d730bd) and could
not derive a clean cross-train-pair rule for any of them. Findings:

- **825aa9e9** -- per-compartment shape gravity, but the resting offset
  varies per pair. Pair 0 (full 8-wall floor row) settles shape bottom
  at (wall_row - 2); pair 1 (only 2-anchor markers, no full floor)
  settles at (anchor_row - 1). Pair 3 has a U-cup container into which
  a single marker enters at the cup-top row, not bottom. No single
  offset rule fits all 4 train pairs.
- **1c56ad9f** -- rectangle border sheared into a period-4 sawtooth
  wave (shifts cycle through {-1, 0, +1, 0}). All 4 train pairs share
  period 4 but have 3 distinct phases (pair 0/1 -> phase 0,-1,0,+1;
  pair 2 -> -1,0,+1,0; pair 3 -> +1,0,-1,0). Test pair has a 4th phase
  (0,+1,0,-1). I could not derive the phase from rectangle width,
  height, top-row position, or interior cell pattern.
- **9f669b64** -- three stacked objects; middle object passes through
  one neighbor which then splits perpendicularly. Direction selection
  (which neighbor splits) doesn't match a clear rule: pair 1 chose the
  larger neighbor, pair 2 chose the smaller; pair 0 had equal-sized
  neighbors with ambiguous tiebreaker.
- **a2d730bd** -- each "outside dot" projects a diamond-like decoration
  pattern between itself and the bordered rectangle, plus a row/column
  of fill connecting them. The decoration shape varies asymmetrically
  per dot.
- **878187ab** -- output size and palette differ from input; output is
  an X pattern in a sub-grid whose dimensions depend on minor-color
  counts and whose colors are completely new.
- **afe3afe9** -- 30x30 input encodes a 6x7 or 7x6 lookup table by
  comparing two side-by-side grids of 3x3 ring patterns. Pure analytic
  abstraction task, hard to symbolically detect.

Verification:
- `python run_task.py` (regression on 08ed6ac7): CORRECT
- `python run_learn.py --limit 40 --shuffle`: still 34 / 40 (85.0%)
- Rules: 41 -> 41 (no new strategies)

---
## Learning Loop -- 2026-04-29 11:17

- Split: None, Tasks: 40
- Correct: 34 / 40 (85.0%)
- Rules: 41 -> 41 (+0 learned)
- Stored rule hits: 34
- Time: 20s
- Log: logs/learn_20260429_111721.log

---
## Learning Loop -- 2026-04-29 11:18

- Split: None, Tasks: 40
- Correct: 34 / 40 (85.0%)
- Rules: 41 -> 41 (+0 learned)
- Stored rule hits: 34
- Time: 18s
- Log: logs/learn_20260429_111753.log

---
## Learning Loop -- 2026-04-29 11:30

- Split: None, Tasks: 40
- Correct: 34 / 40 (85.0%)
- Rules: 41 -> 41 (+0 learned)
- Stored rule hits: 34
- Time: 24s
- Log: logs/learn_20260429_112942.log

---
## Session 21 -- 2026-04-29 11:30

No new strategy added this session. The 6 remaining failures are all
genuinely hard ARC tasks already analyzed in earlier sessions:

- **9f669b64** -- 3 stacked colored objects; middle moves into one
  neighbor which splits perpendicularly. Re-investigated direction
  selection: pair 0 (both neighbors equally adjacent + both rectangles)
  picks the wider-perpendicular neighbor (9s). Pair 1 picks the only
  rectangle (8s). Pair 2 picks the farther neighbor by gap (4s, gap=4).
  Combined "farther > more-rectangular > wider-perpendicular" priority
  gets neighbor selection right, but the *displacement* rule is
  inconsistent: pair 0 places middle outside target's parallel span
  (above 9s) while pair 1/2 place middle nested inside target span at
  the far edge. No single placement rule fits all 3 train pairs.
- **825aa9e9** -- "shapes settle 2 above floor" works for pairs 0/2/3
  but pair 1 settles 1 above (sparse-marker floor). Adding a wall-
  thickness branch then breaks pair 0 where shape 2's two disconnected
  cells need to stack contiguously, not preserve the gap.
- **1c56ad9f** -- sawtooth-wave shifts cycling through {-1,0,+1,0}
  with period 4 but a per-rectangle phase offset. Tried correlating
  phase to rect height, width, cell width, cell height, w-h sign,
  internal-cells-count -- none give a consistent map across the 4
  training pairs.
- **a2d730bd**, **878187ab**, **afe3afe9** -- multi-feature decoration,
  output palette/size derivation, and 6×7 lookup-table abstraction
  respectively (all flagged hard in earlier sessions).

Verification:
- `python run_task.py` (regression on 08ed6ac7): CORRECT
- `python run_learn.py --limit 40 --shuffle`: 34 / 40 (85.0%) -- no change
- Rules: 41 -> 41 (no new strategies persisted)

---
## Learning Loop -- 2026-04-29 11:31

- Split: None, Tasks: 40
- Correct: 34 / 40 (85.0%)
- Rules: 41 -> 41 (+0 learned)
- Stored rule hits: 34
- Time: 25s
- Log: logs/learn_20260429_113100.log

---
## Learning Loop -- 2026-04-29 11:38

- Split: None, Tasks: 40
- Correct: 34 / 40 (85.0%)
- Rules: 41 -> 41 (+0 learned)
- Stored rule hits: 34
- Time: 19s
- Log: logs/learn_20260429_113805.log

---
## Session 22 -- 2026-04-29

Re-analysed the 6 stable failures (878187ab, 825aa9e9, 1c56ad9f,
9f669b64, afe3afe9, a2d730bd). All match prior sessions' findings:

- **1c56ad9f**: row offsets cycle {-1,0,+1,0} with starting phase
  varying by example -- 7-row rect starts 0, 11-row starts 0, 10-row
  starts -1, 12-row starts +1. Tried correlating phase to rect parity,
  off-center direction (col-center sign of `grid_center - rect_center`),
  and internal-line count -- each works for 2-3 training pairs but
  contradicts the others. No single deterministic rule across pairs.
- **825aa9e9**: per-compartment shape relocation. train[0] keeps a
  1-row gap above the wall; train[1] sits flush; train[2] cone-stacks
  inward; train[3] enters narrow valley. Different "settle" semantics
  per pair -- not unifiable as a generic gravity strategy without
  per-pair branching that can't be inferred from input alone.
- **9f669b64**: shape-collides-with-shape physics; placement rule
  for the displaced object differs between pairs (above-target vs
  nested-in-target).
- **a2d730bd**: rect projects an arrow at a stray dot, with bounded
  thickening of rect's adjacent rows. Multi-feature decoration.
- **878187ab**: input scatter -> a different-shape encoded summary.
- **afe3afe9**: 30x30 macro-grid summarised into 7x6 with side overlay.

Conservative decision: did not add a new strategy this session. The
remaining failures are all single-task patterns that would require
brittle heuristics; introducing one risks false-positives on the 34
currently-correct tasks (sequential recolor and color mapping are
already aggressive). The loop is at the diminishing-returns plateau
documented in prior sessions.

Verification:
- `python run_task.py` (regression on 08ed6ac7): CORRECT
- `python run_learn.py --limit 40 --shuffle`: 34 / 40 (85.0%) -- no change
- Rules: 41 -> 41 (no new strategies persisted)

---
## Learning Loop -- 2026-04-29 11:39

- Split: None, Tasks: 40
- Correct: 34 / 40 (85.0%)
- Rules: 41 -> 41 (+0 learned)
- Stored rule hits: 34
- Time: 19s
- Log: logs/learn_20260429_113938.log

---
## Learning Loop -- 2026-04-29 11:58

- Split: None, Tasks: 40
- Correct: 35 / 40 (87.5%)
- Rules: 41 -> 42 (+1 learned)
- Stored rule hits: 34
- Time: 20s
- Log: logs/learn_20260429_115744.log

---
## Session 23 -- 2026-04-29

Added a new strategy `gravity_to_floor` to crack **825aa9e9**:

- **Detection**: `bg = grid[0][w//2]` (middle of top row); `wall = most
  common non-bg color in bottom row`. Shape colors = remaining non-bg.
  Strategy is rejected if no wall cells exist in the bottom row, or no
  shape color is present.
- **Per-column landing row**: walking up from grid bottom, count
  consecutive wall cells in the column (`wall_thickness[c]`). If
  `wall_thickness[c] >= 1`, the shape's bottom in that column is
  `h - wall_thickness[c] - 2` (1-row buffer above the topmost wall row).
  If the column has no wall (e.g. between sparse markers), the shape's
  bottom is `h - 2` (1 row above grid bottom row), since the bottom row
  itself contains the marker pattern.
- **Component fall**: 4-connected shape components are sorted bottom-up
  and each falls rigidly the maximum delta that respects per-col
  landing rows, walls, and previously-placed cells. Disconnected cells
  in the same column thus stack contiguously.

Verified across all 4 train pairs of 825aa9e9 (continuous wall + sparse
markers + thick wall + per-column wall thickness). Safety swept
against the full 400-task training split: only 825aa9e9 matches, no
false positives on the 34 currently-correct tasks.

Verification:
- `python run_task.py` (regression on 08ed6ac7): CORRECT
- `python run_learn.py --limit 40 --shuffle`: 35 / 40 (87.5%) -- up from 34
- Rules: 41 -> 42 (+1 learned, gravity_to_floor stored for 825aa9e9)

Remaining failures: 878187ab (scatter -> encoded summary chevron),
1c56ad9f (per-pair sawtooth phase), 9f669b64 (collision physics with
inconsistent placement rule across pairs), afe3afe9 (30x30 macro-grid
to 7x6/6x7 dual-panel summary), a2d730bd (rect-projects-arrow with
diamond decoration). All were re-analysed in sessions 21-22 and have
no single-rule unification across train pairs.

---
## Learning Loop -- 2026-04-29 11:59

- Split: None, Tasks: 40
- Correct: 35 / 40 (87.5%)
- Rules: 42 -> 42 (+0 learned)
- Stored rule hits: 35
- Time: 19s
- Log: logs/learn_20260429_115905.log

---
## Learning Loop -- 2026-04-29 12:08

- Split: None, Tasks: 40
- Correct: 36 / 40 (90.0%)
- Rules: 42 -> 43 (+1 learned)
- Stored rule hits: 35
- Time: 19s
- Log: logs/learn_20260429_120837.log

---
## Session 24 -- 2026-04-29

- Failed tasks before: 878187ab, 1c56ad9f, 9f669b64, afe3afe9, a2d730bd
- Picked: a2d730bd (arrow_to_rectangle pattern)
- Strategy added: each color has one solid rectangle + N singleton dots; output erases each singleton, draws a 4-cell '+' around it, connects plus to rectangle with 1-wide shaft and a 3-wide perpendicular cap at the rectangle edge.
- Result: 35/40 (87.5%) -> 36/40 (90.0%)
- run_task.py: CORRECT (regression intact)

---
## Learning Loop -- 2026-04-29 12:09

- Split: None, Tasks: 40
- Correct: 36 / 40 (90.0%)
- Rules: 43 -> 43 (+0 learned)
- Stored rule hits: 36
- Time: 19s
- Log: logs/learn_20260429_120930.log

---
## Learning Loop -- 2026-04-29 12:14

- Split: None, Tasks: 40
- Correct: 37 / 40 (92.5%)
- Rules: 43 -> 44 (+1 learned)
- Stored rule hits: 36
- Time: 19s
- Log: logs/learn_20260429_121412.log

---
## Session 25 -- 2026-04-29

- Failed tasks before: 878187ab, 1c56ad9f, 9f669b64, afe3afe9
- Picked: 1c56ad9f (zigzag_grid_shear pattern)
- Strategy added: input has a single non-bg color forming a hollow rectangular grid (top + bottom horizontal lines with internal horizontal/vertical dividers). Output keeps the same shape but each row r in the fg bbox is shifted horizontally by an offset cycling through [0, -1, 0, +1] going UP from the bottom row. Rows outside the bbox are unchanged.
- Result: 36/40 (90.0%) -> 37/40 (92.5%)
- run_task.py: CORRECT (regression intact)
- Newly solved: 1c56ad9f via zigzag_grid_shear
- Remaining failures: 878187ab (V/triangle drawing), 9f669b64 (object split/relocate), afe3afe9 (multi-color pattern composition)

---
## Learning Loop -- 2026-04-29 12:15

- Split: None, Tasks: 40
- Correct: 37 / 40 (92.5%)
- Rules: 44 -> 44 (+0 learned)
- Stored rule hits: 37
- Time: 19s
- Log: logs/learn_20260429_121522.log

---
## Learning Loop -- 2026-04-29 12:27

- Split: None, Tasks: 40
- Correct: 38 / 40 (95.0%)
- Rules: 44 -> 45 (+1 learned)
- Stored rule hits: 37
- Time: 19s
- Log: logs/learn_20260429_122705.log

---
## Session 26 -- 2026-04-29

- Failed tasks before: 878187ab, 9f669b64, afe3afe9
- Picked: 9f669b64 (barrier_passage pattern)
- Strategy added: three collinear non-bg shapes share a common row or col span. The smallest (with most square aspect) is the SMALL; among the other two, the one whose bbox is fully filled is the BARRIER (tiebreak when both are solid: BARRIER's long axis is perpendicular to the line through shapes), and the third is the ANCHOR. Output: SMALL slides through BARRIER to the far grid edge in BARRIER's direction; BARRIER widens by SMALL's perpendicular extent (centered on its original perp center) leaving a hole at SMALL's perpendicular position; ANCHOR is unchanged.
- Result: 37/40 (92.5%) -> 38/40 (95.0%)
- run_task.py: CORRECT (regression intact)
- Newly solved: 9f669b64 via barrier_passage
- Remaining failures: 878187ab (V/triangle drawing), afe3afe9 (multi-color pattern composition)

---
## Learning Loop -- 2026-04-29 12:28

- Split: None, Tasks: 40
- Correct: 38 / 40 (95.0%)
- Rules: 45 -> 45 (+0 learned)
- Stored rule hits: 38
- Time: 19s
- Log: logs/learn_20260429_122800.log

---
## Learning Loop -- 2026-04-29 12:31

- Split: None, Tasks: 40
- Correct: 38 / 40 (95.0%)
- Rules: 45 -> 45 (+0 learned)
- Stored rule hits: 38
- Time: 19s
- Log: logs/learn_20260429_123126.log

---
## Session 27 -- 2026-04-29

- Failed tasks before: 878187ab, afe3afe9
- Re-analysed 878187ab (V/triangle drawing): pattern dims map cleanly
  to scatter-point counts (width = count of more-frequent non-bg color,
  height = count of less-frequent), shape is a V from the bottom-left
  corners drawn in a 2/4 palette with optional X-mirror when height >=
  width/2. The blocker is output dimensions: ex0 input 16x16 -> 16x16,
  ex1 input 15x15 -> 16x16, test 16x16 -> 16x16. No single deterministic
  function of the input maps to the observed output sizes (constant 16
  works for this task only and would not generalise as a category).
- afe3afe9 (multi-color macro-grid -> dual-panel summary): each input is
  a 30x30 macro grid of 3x3 hollow rings in 2-3 colours plus a 1-line
  border on one of the four edges indicating read direction; output is a
  small (6/7-wide) compositional encoding combining cell-wise presence
  of each ring colour. Each train pair uses different colour roles and
  the small-grid composition rule differs per pair -- no single
  unification across train pairs.
- No new strategy added this session: both remaining failures have
  per-pair specifics (output dimensions in 878187ab; encoding rule in
  afe3afe9) that would only solve one task each rather than a category,
  violating the "category, not single task" requirement.
- Result: 38/40 (95.0%) -- unchanged from session 26
- run_task.py: CORRECT (regression intact)
- Remaining failures: 878187ab, afe3afe9

---
## Learning Loop -- 2026-04-29 12:32

- Split: None, Tasks: 40
- Correct: 38 / 40 (95.0%)
- Rules: 45 -> 45 (+0 learned)
- Stored rule hits: 38
- Time: 19s
- Log: logs/learn_20260429_123232.log

---
## Learning Loop -- 2026-04-29 12:40

- Split: None, Tasks: 40
- Correct: 39 / 40 (97.5%)
- Rules: 45 -> 46 (+1 learned)
- Stored rule hits: 38
- Time: 19s
- Log: logs/learn_20260429_124023.log

---
## Learning Loop -- 2026-04-29 12:41

- Split: None, Tasks: 40
- Correct: 39 / 40 (97.5%)
- Rules: 46 -> 46 (+0 learned)
- Stored rule hits: 38
- Time: 19s
- Log: logs/learn_20260429_124046.log

---
## Session 28 -- 2026-04-29 12:42

Added one generalization strategy in `agent/active_operators.py`:

- **`count_wedge_v_pattern`** -- input has bg + exactly two scatter colors
  with distinct counts. The two counts give the dimensions of a wedge
  rendered in the bottom-left of the output: `W = max(count1, count2)`,
  `H = min(count1, count2)`. Inside the wedge, two learned colors render
  an inverted-V (`wedge_line` color forms the V on a `wedge_bg` field):
  bottom row has line cells at columns 0 and W-1, each row above moves
  inward by one column until convergence (single-cell apex when W is odd,
  two-cell apex when W is even). If H exceeds the convergence height, the
  V mirrors back outward forming an X / diamond (with the apex row
  doubled when W is even). Output dimensions are not constrained to match
  input (training pair sizes can differ). Solves 878187ab.

Verification:
- `python run_task.py` (regression on 08ed6ac7): CORRECT
- `python run_task.py 878187ab`: CORRECT
- `python run_learn.py --limit 40 --shuffle`: 39 / 40 (97.5%), up from
  38 / 40 (95.0%)
  - 878187ab: CORRECT via count_wedge_v_pattern (pipeline)
- Rules: 45 -> 46 (+1 new strategy stored in procedural_memory/)
- Remaining failure: afe3afe9 (complex meta-puzzle deferred)

---
## Learning Loop -- 2026-04-29 12:41

- Split: None, Tasks: 40
- Correct: 39 / 40 (97.5%)
- Rules: 46 -> 46 (+0 learned)
- Stored rule hits: 38
- Time: 19s
- Log: logs/learn_20260429_124139.log

---
## Learning Loop -- 2026-04-29 12:46

- Split: None, Tasks: 40
- Correct: 39 / 40 (97.5%)
- Rules: 46 -> 46 (+0 learned)
- Stored rule hits: 38
- Time: 19s
- Log: logs/learn_20260429_124556.log

---
## Session 29 -- 2026-04-29 12:46

No new generalization strategy added this session.

The only failing task is **afe3afe9**, a complex meta-puzzle with these
properties (decoded this session):

- A 1-pixel border on one of the four edges of a 30x30 grid; the border
  side determines orientation (top / bottom / left / right).
- Pattern primitives are 3x3 hollow squares (frame), each acting like a
  single "pixel" in a compressed representation.
- Three colors are present: one "long" color always renders an Mx3 or
  3xM grid of 1..21 hollow squares (the M-axis aligned away from the
  border), and two "small" colors each render a 3x3 grid of squares.
- The output dimensions are not a clean function of the input shape;
  empirically the long axis matches the long color's pattern (e.g. 7x6
  output when long color is 7x3 of squares, 6x7 when long color is 3x7).
- The long color's pattern in the output is NOT a pure mirror or 180
  rotation of the input pattern; some rows match the input directly,
  others are mirrored, with the small-color cells "filling in" some of
  the dropped/added cells.

Conclusion: the transformation likely encodes a layered overlay between
the long pattern and the two small patterns with orientation-dependent
priorities. A faithful category-level strategy would need to model
border orientation, square detection, pattern decoding, and the
overlay/priority rules. Given the regression risk and the rule that
each strategy must handle a category (not a single task), this remains
deferred for a future session with deeper analysis.

Verification:
- `python run_task.py` (regression on 08ed6ac7): CORRECT
- `python run_learn.py --limit 40 --shuffle`: 39 / 40 (97.5%)
  - afe3afe9: still INCORRECT (only failure)
- Rules: 46 -> 46 (no new strategies)

---
## Learning Loop -- 2026-04-29 12:47

- Split: None, Tasks: 40
- Correct: 39 / 40 (97.5%)
- Rules: 46 -> 46 (+0 learned)
- Stored rule hits: 38
- Time: 19s
- Log: logs/learn_20260429_124726.log

---
## Learning Loop -- 2026-04-29 12:50

- Split: None, Tasks: 200
- Correct: 42 / 200 (21.0%)
- Rules: 46 -> 75 (+29 learned)
- Stored rule hits: 38
- Time: 133s
- Log: logs/learn_20260429_124825.log

---
## Learning Loop -- 2026-04-29 12:54

- Split: None, Tasks: 40
- Correct: 39 / 40 (97.5%)
- Rules: 75 -> 75 (+0 learned)
- Stored rule hits: 38
- Time: 19s
- Log: logs/learn_20260429_125408.log

---
## Learning Loop -- 2026-04-29 12:56

- Split: None, Tasks: 200
- Correct: 43 / 200 (21.5%)
- Rules: 75 -> 76 (+1 learned)
- Stored rule hits: 39
- Time: 102s
- Log: logs/learn_20260429_125459.log

---
## Learning Loop -- 2026-04-29 12:57

- Split: None, Tasks: 40
- Correct: 39 / 40 (97.5%)
- Rules: 76 -> 76 (+0 learned)
- Stored rule hits: 38
- Time: 22s
- Log: logs/learn_20260429_125649.log

---
## Session 30 -- 2026-04-29 12:57

Added strategy: **marker_stamp_offsets**

Detects: same-shape input/output where each pair has bg + exactly one
non-bg cell of a fixed marker color. Output replaces the marker with bg
and writes a fixed (offset -> color) stamp around the marker, clipped
at grid bounds. Across all pairs, marker color and offset->color map
are consistent; offsets that fall in-bounds for a pair must appear in
that pair's output (only out-of-bounds offsets may be missing).

Target task: **a9f96cdd** -- a 2 marker on bg becomes a 4-corner
diagonal stamp {(-1,-1):3, (-1,+1):6, (+1,-1):8, (+1,+1):7}, clipped at
edges. Rule learned: marker_color=2, 4 diagonal offsets.

The strategy is general: any "single-marker -> fixed stamp" task with
bounds-clipping should now be solvable. (afe3afe9 still deferred.)

Verification:
- `python run_task.py` (regression on 08ed6ac7): CORRECT
- `python run_task.py a9f96cdd`: CORRECT
- `python run_learn.py --limit 40 --shuffle`: 39 / 40 (97.5%) (unchanged)
- `python run_learn.py --limit 200 --shuffle`: 43 / 200 (vs 42 / 200
  before this session) (+1 task solved by new strategy)
- Rules: 75 -> 76 (rule_076 = marker_stamp_offsets for a9f96cdd)


---
## Learning Loop -- 2026-04-29 12:58

- Split: None, Tasks: 40
- Correct: 39 / 40 (97.5%)
- Rules: 76 -> 76 (+0 learned)
- Stored rule hits: 38
- Time: 19s
- Log: logs/learn_20260429_125746.log

---
## Learning Loop -- 2026-04-29 13:03

- Split: None, Tasks: 40
- Correct: 39 / 40 (97.5%)
- Rules: 76 -> 76 (+0 learned)
- Stored rule hits: 38
- Time: 20s
- Log: logs/learn_20260429_130312.log

---
## Learning Loop -- 2026-04-29 13:05

- Split: None, Tasks: 200
- Correct: 44 / 200 (22.0%)
- Rules: 76 -> 77 (+1 learned)
- Stored rule hits: 40
- Time: 103s
- Log: logs/learn_20260429_130338.log

---
## Session 31 -- 2026-04-29 13:05

Added strategy: **stack_objects_aligned**

Detects: input has K >= 2 distinct non-bg colors, each color's cells
form an "object" with a bounding box. All objects share the same
bbox size (h, w) and have pairwise-disjoint bboxes. The output is the
concatenation of each object's bbox crop along the axis of greatest
spatial spread:
  - col-spread > row-spread -> horizontal stack, sorted by min col
  - else vertical stack, sorted by min row
Each pair's axis is determined dynamically from the input layout
(no global axis lock), so a task with mixed horizontal/vertical
example pairs is still admissible.

Target task: **67636eac** (10x10 / 13x17 / 17x18 inputs holding 2-3
small same-shape colored shapes; output is the shapes' bboxes
concatenated). Pair 0 horizontal (3x9), pair 1 vertical (9x3),
pair 2 vertical (6x3). Test horizontal (3x12, 4 objects).

Verification:
- `python run_task.py` (regression on 08ed6ac7): CORRECT
- `python run_task.py 67636eac`: CORRECT
- `python run_learn.py --limit 40 --shuffle`: 39 / 40 (97.5%) (unchanged)
- `python run_learn.py --limit 200 --shuffle`: 44 / 200 (vs 43 / 200
  before this session) -- +1 task solved by the new strategy.
- Rules: 76 -> 77 (rule_077 = stack_objects_aligned for 67636eac)

afe3afe9 remains deferred (complex meta-puzzle requiring panel
detection + overlay decoding; flagged in earlier sessions).
