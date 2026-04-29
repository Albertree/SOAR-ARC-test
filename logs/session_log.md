
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
