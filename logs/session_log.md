# SOAR-ARC Session Log

---
## Learning Loop -- 2026-03-29 14:25

- Split: training, Tasks: 20
- Correct: 0 / 20 (0.0%)
- Rules: 0 -> 3 (+3 learned)
- Stored rule hits: 0
- Time: 45s
- Log: logs/learn_20260329_142443.log

---
## Learning Loop -- 2026-03-29 14:29

- Split: training, Tasks: 3
- Correct: 0 / 3 (0.0%)
- Rules: 0 -> 0 (+0 learned)
- Stored rule hits: 0
- Time: 6s
- Log: logs/learn_20260329_142943.log

---
## Learning Loop -- 2026-03-29 14:31

- Split: training, Tasks: 20
- Correct: 0 / 20 (0.0%)
- Rules: 0 -> 3 (+3 learned)
- Stored rule hits: 0
- Time: 46s
- Log: logs/learn_20260329_143038.log

---
## Learning Loop -- 2026-03-29 14:37

- Split: training, Tasks: 20
- Correct: 3 / 20 (15.0%)
- Rules: 7 -> 8 (+1 learned)
- Stored rule hits: 3
- Time: 36s
- Log: logs/learn_20260329_143709.log

---
## Session 1 -- Claude Code Improvements (2026-03-29)

### Strategies Added
1. **vertical_mirror_append** -- output = input rows + vertically flipped input rows. Handles tasks where the grid doubles in height via reflection.
2. **fill_rectangles_by_size** -- detect rectangles outlined with one color, fill interiors based on interior area (area->color mapping learned from examples). Handles size-based rectangle fill tasks.
3. **keep_center_column** -- output keeps only the center column of input, rest becomes background. Handles column extraction/projection tasks.

### Tasks Solved
- `8be77c9e`: vertical_mirror_append
- `c0f76784`: fill_rectangles_by_size
- `d23f8c26`: keep_center_column

### Results
- Before: 0/20 (0%)
- After: 3/20 (15%)
- Regression gate (08ed6ac7): CORRECT

---
## Learning Loop -- 2026-03-29 14:38

- Split: training, Tasks: 20
- Correct: 3 / 20 (15.0%)
- Rules: 8 -> 9 (+1 learned)
- Stored rule hits: 3
- Time: 36s
- Log: logs/learn_20260329_143821.log

---
## Session 2 -- Claude Code Improvements (2026-03-29)

### Strategies Added
1. **pixel_scale** -- each input pixel maps to an NxN block in output (integer upscaling). Detects that output dimensions are an exact integer multiple of input and verifies uniform block mapping. Handles zoom/upscale tasks.
2. **recolor_by_size** -- connected components of a single source color are recolored by size group (largest size=1, next=2, etc.). Components of equal size get the same color. Handles size-based classification tasks. Also subsumes the regression gate task (08ed6ac7).
3. **reverse_rings** -- concentric rectangular rings of distinct colors have their order reversed (outermost<->innermost). Detects perfect ring structure and verifies reversal. Handles ring inversion tasks.

### Tasks Solved
- `c59eb873`: pixel_scale (2x upscale)
- `6e82a1ae`: recolor_by_size (memory hit from 08ed6ac7 rule)
- `85c4e7cd`: reverse_rings

### Results
- Before: 3/20 (15%)
- After: 6/20 (30%)
- Regression gate (08ed6ac7): CORRECT

---
## Learning Loop -- 2026-03-29 14:44

- Split: training, Tasks: 20
- Correct: 6 / 20 (30.0%)
- Rules: 12 -> 13 (+1 learned)
- Stored rule hits: 6
- Time: 36s
- Log: logs/learn_20260329_144332.log

---
## Learning Loop -- 2026-03-29 14:45

- Split: training, Tasks: 20
- Correct: 6 / 20 (30.0%)
- Rules: 13 -> 14 (+1 learned)
- Stored rule hits: 6
- Time: 36s
- Log: logs/learn_20260329_144456.log

---
## Session 3 -- Claude Code Improvements (2026-03-29)

### Strategies Added
1. **staircase_growth** -- input is a single row with N colored cells; output has W/2 rows where each successive row adds one more colored cell, forming a right-triangle staircase. Handles 1D-to-2D staircase/triangle expansion tasks.
2. **corner_fill_quadrants** -- one or more rectangular blocks of a filler color, each with 4 colored pixels at the diagonal corners. Output replaces each filler block with 4 equal quadrants colored by the corresponding corner. Handles rectangle + corner marker → quadrant coloring tasks.

### Tasks Solved
- `bbc9ae5d`: staircase_growth
- `e9ac8c9e`: corner_fill_quadrants

### Results
- Before: 6/20 (30%)
- After: 8/20 (40%)
- Regression gate (08ed6ac7): CORRECT

---
## Learning Loop -- 2026-03-29 14:54

- Split: training, Tasks: 20
- Correct: 8 / 20 (40.0%)
- Rules: 16 -> 17 (+1 learned)
- Stored rule hits: 8
- Time: 36s
- Log: logs/learn_20260329_145332.log

---
## Learning Loop -- 2026-03-29 14:55

- Split: training, Tasks: 20
- Correct: 8 / 20 (40.0%)
- Rules: 17 -> 18 (+1 learned)
- Stored rule hits: 8
- Time: 36s
- Log: logs/learn_20260329_145459.log

---
## Session 4 -- Claude Code Improvements (2026-03-29)

### Strategies Added
1. **gravity_slide** -- grid has 3 colors (background, wall, object). Connected components of the object color slide downward toward the wall boundary, stopping with exactly 1 empty cell gap from any wall cell. Components stack against each other with 0 gap. Handles gravity/sliding-toward-boundary tasks. Tries all color permutations to detect which is bg/wall/object.

### Tasks Solved
- `825aa9e9`: gravity_slide

### Results
- Before: 8/20 (40%)
- After: 9/20 (45%)
- Regression gate (08ed6ac7): CORRECT

---
## Learning Loop -- 2026-03-29 15:12

- Split: training, Tasks: 20
- Correct: 9 / 20 (45.0%)
- Rules: 19 -> 20 (+1 learned)
- Stored rule hits: 8
- Time: 43s
- Log: logs/learn_20260329_151124.log

---
## Learning Loop -- 2026-03-29 15:13

- Split: training, Tasks: 20
- Correct: 9 / 20 (45.0%)
- Rules: 20 -> 21 (+1 learned)
- Stored rule hits: 8
- Time: 42s
- Log: logs/learn_20260329_151245.log

---
## Session 5 -- Claude Code Improvements (2026-03-29)

### Strategies Added
1. **diamond_bridge** -- find 3x3 diamond shapes (4 cardinal pixels of one color, center=0) and connect horizontally/vertically aligned pairs with blue (1) lines between their tips. Handles shape-connection / bridge-drawing tasks.
2. **stripe_zone_fill** -- grid has a vertical spine of color 8, background 7, and colored horizontal stripes (with 1 at spine intersection). Output fills zones around each stripe with its color, inverts stripe rows, and adds separator rows at odd-gap midpoints between differently-colored stripes. Handles spine + stripe zone-filling tasks.

### Tasks Solved
- `60a26a3e`: diamond_bridge
- `332202d5`: stripe_zone_fill

### Results
- Before: 9/20 (45%)
- After: 11/20 (55%)
- Regression gate (08ed6ac7): CORRECT

---
## Learning Loop -- 2026-03-29 15:21

- Split: training, Tasks: 20
- Correct: 11 / 20 (55.0%)
- Rules: 23 -> 23 (+0 learned)
- Stored rule hits: 10
- Time: 37s
- Log: logs/learn_20260329_152039.log

---
## Learning Loop -- 2026-03-29 15:22

- Split: training, Tasks: 20
- Correct: 11 / 20 (55.0%)
- Rules: 23 -> 23 (+0 learned)
- Stored rule hits: 10
- Time: 36s
- Log: logs/learn_20260329_152200.log

---
## Session 6 -- Claude Code Improvements (2026-03-29)

### Strategies Added
1. **cross_projection** -- find cross shapes (arm color + unique center color) on a uniform background. The one missing arm direction determines projection: center color is projected every 2 cells toward the nearest edge, and that full edge row/col is filled with the center color. Corners where two projected edges meet become 0. Handles directional projection / cross-marker-to-edge tasks.
2. **quadrant_shape_swap** -- grid divided into cells by rows/columns of 0s. Each cell has a background color and a foreground shape. Horizontally paired cells swap their shapes, drawing the swapped shape in the partner's background color. When both cells share the same background, swapped shapes become invisible (blank). Handles cross-quadrant shape exchange tasks.

### Tasks Solved
- `13f06aa5`: cross_projection
- `5a719d11`: quadrant_shape_swap

### Results
- Before: 11/20 (55%)
- After: 13/20 (65%)
- Regression gate (08ed6ac7): CORRECT

### Note
Procedural memory was rebuilt from scratch during this session (stale type=None rules cleaned). All 14 valid rules were rediscovered by the pipeline and stored correctly.

---
## Learning Loop -- 2026-03-29 15:39

- Split: training, Tasks: 20
- Correct: 13 / 20 (65.0%)
- Rules: 2 -> 14 (+12 learned)
- Stored rule hits: 2
- Time: 37s
- Log: logs/learn_20260329_153914.log

---
## Learning Loop -- 2026-03-29 15:40

- Split: training, Tasks: 20
- Correct: 13 / 20 (65.0%)
- Rules: 14 -> 14 (+0 learned)
- Stored rule hits: 12
- Time: 36s
- Log: logs/learn_20260329_153957.log

---
## Learning Loop -- 2026-03-29 15:42

- Split: training, Tasks: 20
- Correct: 13 / 20 (65.0%)
- Rules: 14 -> 14 (+0 learned)
- Stored rule hits: 12
- Time: 37s
- Log: logs/learn_20260329_154137.log

---
## Session 7 -- Claude Code Improvements (2026-03-29)

### Strategies Added
1. **lpath_chain** -- L-shaped path routing from a source pixel (color 3) through directional waypoints. Two waypoint colors determine turn direction (one=down, one=up). Path fills source color in L-shaped zigzag segments, turning at each waypoint. Handles path-drawing / zigzag connector tasks.
2. **arrow_chain_mirror** -- grid split by a separator row. Bottom half has "dot" pixels and "arrow" pixels. Each dot follows its adjacent chain of arrows to the end position. Top half mirrors the final dot positions across the separator. Handles separator + directional chain + mirror tasks.

### Tasks Solved
- `e5790162`: lpath_chain
- `c9680e90`: arrow_chain_mirror

### Results
- Before: 13/20 (65%)
- After: 15/20 (75%)
- Regression gate (08ed6ac7): CORRECT

---
## Learning Loop -- 2026-03-29 15:53

- Split: training, Tasks: 20
- Correct: 15 / 20 (75.0%)
- Rules: 16 -> 16 (+0 learned)
- Stored rule hits: 14
- Time: 36s
- Log: logs/learn_20260329_155302.log
