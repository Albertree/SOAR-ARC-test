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

---
## Learning Loop -- 2026-03-29 15:54

- Split: training, Tasks: 20
- Correct: 15 / 20 (75.0%)
- Rules: 16 -> 16 (+0 learned)
- Stored rule hits: 14
- Time: 36s
- Log: logs/learn_20260329_155411.log

---
## Learning Loop -- 2026-03-29 16:06

- Split: training, Tasks: 20
- Correct: 15 / 20 (75.0%)
- Rules: 16 -> 16 (+0 learned)
- Stored rule hits: 14
- Time: 35s
- Log: logs/learn_20260329_160533.log

---
## Learning Loop -- 2026-03-29 16:08

- Split: training, Tasks: 20
- Correct: 16 / 20 (80.0%)
- Rules: 17 -> 17 (+0 learned)
- Stored rule hits: 15
- Time: 36s
- Log: logs/learn_20260329_160806.log

---
## Learning Loop -- 2026-03-29 16:11

- Split: training, Tasks: 20
- Correct: 16 / 20 (80.0%)
- Rules: 18 -> 18 (+0 learned)
- Stored rule hits: 15
- Time: 35s
- Log: logs/learn_20260329_161119.log

---
## Session 8 -- Claude Code Improvements (2026-03-29)

### Strategies Added
1. **grid_zigzag_shear** -- single-color rectangular grid/lattice on a background. Each row of the bounding box shifts horizontally in a period-4 sinusoidal wave: [0, 1, 0, -1] with phase = (1 - bbox_height) % 4. Shape color varies per task. Handles grid/rectangle zigzag shear tasks.
2. **three_shape_rearrange** -- 3 non-background colored objects aligned on one axis. The smallest (connector) moves to the far side of one outer object, which splits in half perpendicular to the axis to accommodate it. The split block must have perpendicular extent >= 2x the connector's. When both qualify, the smaller one splits. Handles three-shape connector/split rearrangement tasks.

### Tasks Solved
- `1c56ad9f`: grid_zigzag_shear
- `9f669b64`: three_shape_rearrange

### Results
- Before: 15/20 (75%)
- After: 17/20 (85%)
- Regression gate (08ed6ac7): CORRECT

---
## Learning Loop -- 2026-03-29 16:13

- Split: training, Tasks: 20
- Correct: 17 / 20 (85.0%)
- Rules: 18 -> 18 (+0 learned)
- Stored rule hits: 15
- Time: 36s
- Log: logs/learn_20260329_161234.log

---
## Learning Loop -- 2026-03-29 16:14

- Split: training, Tasks: 20
- Correct: 17 / 20 (85.0%)
- Rules: 18 -> 18 (+0 learned)
- Stored rule hits: 15
- Time: 36s
- Log: logs/learn_20260329_161408.log

---
## Learning Loop -- 2026-03-29 16:30

- Split: training, Tasks: 20
- Correct: 18 / 20 (90.0%)
- Rules: 19 -> 19 (+0 learned)
- Stored rule hits: 16
- Time: 35s
- Log: logs/learn_20260329_163018.log

---
## Learning Loop -- 2026-03-29 16:41

- Split: training, Tasks: 20
- Correct: 19 / 20 (95.0%)
- Rules: 20 -> 20 (+0 learned)
- Stored rule hits: 17
- Time: 37s
- Log: logs/learn_20260329_164035.log

---
## Session 9 -- Claude Code Improvements (2026-03-29)

### Strategies Added
1. **block_grid_gravity** -- large (~30×30) grid of 3×3 hollow-square blocks arranged on a 4-cell grid. One edge has a border line of 1s. Output compresses each block to a single cell and applies directional gravity (compacting non-zero values) perpendicular to the border: top→push right, bottom→push left, left→push up, right→push down. Handles block-grid summarisation with directional compaction tasks.
2. **template_reconstruct** -- input contains multi-colour template shapes (body colour + endpoint colours) and isolated marker pixels sharing the same endpoint colours. Output removes templates and draws D4-transformed (rotation/reflection) copies centered on marker positions. The D4 element is determined by mapping template endpoint positions to marker positions. Handles template-to-marker reconstruction with symmetry tasks.

### Tasks Solved
- `afe3afe9`: block_grid_gravity
- `0e206a2e`: template_reconstruct

### Results
- Before: 17/20 (85%)
- After: 19/20 (95%)
- Regression gate (08ed6ac7): CORRECT

---
## Learning Loop -- 2026-03-29 16:42

- Split: training, Tasks: 20
- Correct: 19 / 20 (95.0%)
- Rules: 20 -> 20 (+0 learned)
- Stored rule hits: 17
- Time: 36s
- Log: logs/learn_20260329_164144.log

---
## Learning Loop -- 2026-03-29 16:46

- Split: training, Tasks: 20
- Correct: 19 / 20 (95.0%)
- Rules: 20 -> 20 (+0 learned)
- Stored rule hits: 17
- Time: 36s
- Log: logs/learn_20260329_164543.log

---
## Learning Loop -- 2026-03-29 16:49

- Split: training, Tasks: 20
- Correct: 19 / 20 (95.0%)
- Rules: 20 -> 20 (+0 learned)
- Stored rule hits: 17
- Time: 35s
- Log: logs/learn_20260329_164854.log

---
## Learning Loop -- 2026-03-29 16:52

- Split: training, Tasks: 20
- Correct: 19 / 20 (95.0%)
- Rules: 20 -> 21 (+1 learned)
- Stored rule hits: 17
- Time: 36s
- Log: logs/learn_20260329_165142.log

---
## Learning Loop -- 2026-03-29 16:53

- Split: training, Tasks: 20
- Correct: 20 / 20 (100.0%)
- Rules: 21 -> 21 (+0 learned)
- Stored rule hits: 18
- Time: 36s
- Log: logs/learn_20260329_165257.log

---
## Session 10 -- Claude Code Improvements (2026-03-29)

### Strategies Added
1. **scatter_count_x** -- input has background + exactly 2 scattered non-bg single-pixel colors. Count each color: the more-frequent count becomes rectangle width, the less-frequent becomes height. Output is a fixed-size grid (consistent across training pairs) with a W×H rectangle anchored at the bottom-left, filled with one color and an X-pattern (two crossing diagonals) drawn in another. Handles scatter-pixel counting → geometric X-diamond shape tasks.

### Tasks Solved
- `878187ab`: scatter_count_x

### Results
- Before: 19/20 (95%)
- After: 20/20 (100%)
- Regression gate (08ed6ac7): CORRECT

---
## Learning Loop -- 2026-03-29 16:55

- Split: training, Tasks: 20
- Correct: 20 / 20 (100.0%)
- Rules: 21 -> 21 (+0 learned)
- Stored rule hits: 18
- Time: 36s
- Log: logs/learn_20260329_165429.log

---
## Learning Loop -- 2026-03-29 16:56

- Split: training, Tasks: 40
- Correct: 20 / 40 (50.0%)
- Rules: 21 -> 26 (+5 learned)
- Stored rule hits: 18
- Time: 84s
- Log: logs/learn_20260329_165527.log

---
## Session 11 -- Claude Code Improvements (2026-03-29)

### Strategies Added
1. **rotation_tiling** -- NxN input tiled into a 2Nx2N output with 4 quadrants: top-left = original, top-right = 270° CW rotation, bottom-left = 180° rotation, bottom-right = 90° CW rotation. Handles rotation-symmetry expansion tasks.
2. **rectangle_interior_count** -- input has a rectangle bordered by 1s with scattered colored pixels inside. Output is a fixed-size grid (e.g. 3×3) filled left-to-right, top-to-bottom with the count of colored interior pixels. Handles count-inside-rectangle → summary grid tasks.
3. **pattern_tile_fill** -- grid has a uniform-background region and a contiguous pattern region at one end. The blank region is filled by cyclically repeating the pattern. Handles pattern repetition / tile-fill tasks.

### Tasks Solved
- `ed98d772`: rotation_tiling
- `c8b7cc0f`: rectangle_interior_count
- `9b30e358`: pattern_tile_fill

### Results
- Before: 20/20 (100%) on core 20 tasks
- After: 23/40 (57.5%) on expanded 40-task set (+3 new tasks solved)
- Regression gate (08ed6ac7): CORRECT

---
## Learning Loop -- 2026-03-29 17:07

- Split: training, Tasks: 40
- Correct: 23 / 40 (57.5%)
- Rules: 29 -> 34 (+5 learned)
- Stored rule hits: 21
- Time: 74s
- Log: logs/learn_20260329_170629.log

---
## Learning Loop -- 2026-03-29 17:10

- Split: training, Tasks: 40
- Correct: 23 / 40 (57.5%)
- Rules: 34 -> 39 (+5 learned)
- Stored rule hits: 21
- Time: 76s
- Log: logs/learn_20260329_170902.log

---
## Session 12 -- Claude Code Improvements (2026-03-29)

### Strategies Added
1. **nearest_corner_lines** -- each non-background pixel projects an L-shaped line toward its nearest corner (nearest vertical edge + nearest horizontal edge). Handles point-to-edge projection / L-line drawing tasks.
2. **frame_inversion** -- input has a single nested rectangle on black background with outer border color A and interior color B. Output extracts the rectangle and swaps A↔B (inside-out). Handles nested rectangle color-swap tasks.
3. **horizontal_mirror_mark** -- grid has one foreground color on black background. Pixels whose horizontally mirrored position (across the vertical center axis) also has the same foreground color are recolored to a new color; unpaired pixels stay. Handles horizontal symmetry detection/marking tasks.

### Tasks Solved
- `705a3229`: nearest_corner_lines
- `b94a9452`: frame_inversion
- `ce039d91`: horizontal_mirror_mark

### Results
- Before: 23/40 (57.5%)
- After: 26/40 (65.0%)
- Regression gate (08ed6ac7): CORRECT

---
## Learning Loop -- 2026-03-29 17:17

- Split: training, Tasks: 40
- Correct: 26 / 40 (65.0%)
- Rules: 42 -> 46 (+4 learned)
- Stored rule hits: 24
- Time: 74s
- Log: logs/learn_20260329_171729.log

---
## Learning Loop -- 2026-03-29 17:18

- Split: training, Tasks: 40
- Correct: 26 / 40 (65.0%)
- Rules: 42 -> 46 (+4 learned)
- Stored rule hits: 24
- Time: 74s
- Log: logs/learn_20260329_171729.log

---
## Learning Loop -- 2026-03-29 17:20

- Split: training, Tasks: 40
- Correct: 26 / 40 (65.0%)
- Rules: 46 -> 50 (+4 learned)
- Stored rule hits: 24
- Time: 74s
- Log: logs/learn_20260329_171911.log

---
## Session 13 -- Claude Code Improvements (2026-03-29)

### Strategies Added
1. **denoise_keep_rectangles** -- input has solid filled rectangles plus scattered single-pixel noise of the same color. Output keeps only pixels that belong to at least one 2×2 all-foreground block, removing isolated noise. Handles denoise / keep-rectangles tasks.
2. **extend_diagonal_arms** -- a 2×2 block of one color with 1-2 single-pixel diagonal tips. Each tip extends diagonally in the same direction to the grid edge. Handles diagonal-ray / arm-extension tasks.
3. **seed_quadrant_project** -- a 2×2 non-zero seed in an otherwise zero grid. Each quadrant around the seed gets filled with the diagonally-opposite seed color. Fill size = min(2, available_space) in each dimension, positioned adjacent to the seed. Handles 2×2 seed diagonal quadrant projection tasks.

### Tasks Solved
- `7f4411dc`: denoise_keep_rectangles
- `7ddcd7ec`: extend_diagonal_arms
- `93b581b8`: seed_quadrant_project

### Results
- Before: 26/40 (65.0%)
- After: 29/40 (72.5%)
- Regression gate (08ed6ac7): CORRECT

---
## Learning Loop -- 2026-03-29 17:34

- Split: training, Tasks: 40
- Correct: 29 / 40 (72.5%)
- Rules: 54 -> 57 (+3 learned)
- Stored rule hits: 27
- Time: 73s
- Log: logs/learn_20260329_173248.log

---
## Learning Loop -- 2026-03-29 17:35

- Split: training, Tasks: 40
- Correct: 29 / 40 (72.5%)
- Rules: 57 -> 60 (+3 learned)
- Stored rule hits: 27
- Time: 74s
- Log: logs/learn_20260329_173435.log

---
## Session 14 -- 2026-03-29 17:49

### New strategies added (3):

1. **flood_fill_partition** (84db8fc4): One color vanishes, replaced by two new
   colors. Border-reachable cells (4-connected to grid edge) get exterior color;
   unreachable cells get interior color. Category: inside/outside region coloring,
   maze partitioning.

2. **rotation_tile_repeat** (cf5fd0ad): NxN input → 4Nx4N output. Output is 2×2
   macro-quadrants, each filled with a 2×2 tiling of a specific rotation (0/90/180/270)
   of the input. Layout auto-detected from examples. Category: rotation symmetry
   expansion with repetition.

3. **cross_arm_mode** (642d658d): Grid has plus-shaped patterns centered on a
   specific color (e.g. 4). Each cross has 4 same-color arms. Output is 1×1: the
   arm color appearing in the most crosses. Category: pattern counting / mode-finding.

### Results

- Split: training, Tasks: 40
- Correct: 32 / 40 (80.0%)  [########################......]
- Previous: 29 / 40 (72.5%)  — improvement: +3 tasks
- Rules: 63 -> 66 (+3 learned)
- Stored rule hits: 30
- Time: 76s
- Log: logs/learn_20260329_174919.log

---
## Learning Loop -- 2026-03-29 17:52

- Split: training, Tasks: 40
- Correct: 32 / 40 (80.0%)
- Rules: 66 -> 69 (+3 learned)
- Stored rule hits: 30
- Time: 74s
- Log: logs/learn_20260329_175139.log

---
## Learning Loop -- 2026-03-29 18:03

- Split: training, Tasks: 40
- Correct: 35 / 40 (87.5%)
- Rules: 72 -> 74 (+2 learned)
- Stored rule hits: 33
- Time: 75s
- Log: logs/learn_20260329_180237.log

---
## Session 15 -- 2026-03-29 18:02

### New strategies added (3):

1. **grid_intersection_compress** (7837ac64): Input is a large tiled grid with
   one color forming the grid lines. Some grid-line intersections have different
   colors forming a 4×4 pattern. Output compresses this to 3×3 by overlapping
   the middle rows/cols (agree→value, disagree→0). Category: grid intersection
   summarization / compression tasks.

2. **enclosed_rect_fill** (a5313dff): Input has shapes drawn with a border color
   on background 0. Closed rectangular borders fully enclosing an interior get
   their interior 0-cells filled with color 1. Open/incomplete shapes unchanged.
   Uses flood-fill from grid boundary to distinguish inside vs outside.
   Category: enclosed region detection / interior fill tasks.

3. **color_key_remap** (e9b4f6fc): Input has a bordered rectangular shape plus
   isolated 2-pixel horizontal key pairs. Each key pair (a, b) means "replace
   color b with a" in the shape. Output is the extracted shape with all colors
   substituted. Category: color substitution / palette remapping tasks.

### Results

- Split: training, Tasks: 40
- Correct: 35 / 40 (87.5%)  [##########################....]
- Previous: 32 / 40 (80.0%)  — improvement: +3 tasks
- Rules: 72 -> 74 (+2 learned)
- Stored rule hits: 33
- Time: 75s
- Log: logs/learn_20260329_180237.log

---
## Learning Loop -- 2026-03-29 18:05

- Split: training, Tasks: 40
- Correct: 35 / 40 (87.5%)
- Rules: 74 -> 76 (+2 learned)
- Stored rule hits: 33
- Time: 74s
- Log: logs/learn_20260329_180439.log

---
## Learning Loop -- 2026-03-29 18:30

- Split: training, Tasks: 40
- Correct: 38 / 40 (95.0%)
- Rules: 79 -> 79 (+0 learned)
- Stored rule hits: 36
- Time: 75s
- Log: logs/learn_20260329_182939.log

---
## Session 16 -- 2026-03-29 18:30

### New strategies added (3):

1. **square_corner_mark** (14b8e18c): Find connected components that form
   square rectangular borders (width==height>=2, all perimeter cells filled).
   Place a marker color at corner-extension positions (one cell beyond each
   corner along the two border lines). Non-square or non-rectangular shapes
   are ignored. Category: rectangle/square detection + corner marking tasks.

2. **domino_cross_intersection** (9f5f939b): Find all 2-cell dominos
   (horizontal/vertical). Group by alignment (same row/column). For each
   pair of consecutive aligned dominos, compute the exact gap center.
   Where a vertical gap center and horizontal gap center coincide at the
   same integer cell, mark it with a learned color. Category: domino
   alignment / cross-intersection detection tasks.

3. **separator_projection** (5daaa586): Grid has 4 separator lines (2 full
   rows, 2 full columns, each a distinct color). Scattered pixels of a color
   matching one separator project lines toward that separator. Output is the
   cropped inner frame with projected lines. Category: separator-bounded
   projection / accumulation tasks.

### Results

- Split: training, Tasks: 40
- Correct: 38 / 40 (95.0%)  [############################..]
- Previous: 35 / 40 (87.5%)  -- improvement: +3 tasks
- Rules: 76 -> 79 (+3 learned)
- Stored rule hits: 36
- Time: 75s
- Log: logs/learn_20260329_182939.log

---
## Learning Loop -- 2026-03-29 18:32

- Split: training, Tasks: 40
- Correct: 38 / 40 (95.0%)
- Rules: 79 -> 79 (+0 learned)
- Stored rule hits: 36
- Time: 74s
- Log: logs/learn_20260329_183059.log

---
## Learning Loop -- 2026-03-29 18:34

- Split: training, Tasks: 40
- Correct: 38 / 40 (95.0%)
- Rules: 79 -> 79 (+0 learned)
- Stored rule hits: 36
- Time: 77s
- Log: logs/learn_20260329_183312.log

---
## Session 17 -- 2026-03-29 18:44

- Split: training, Tasks: 40
- Correct: 40 / 40 (100.0%)  [##############################]
- Rules: 79 -> 81 (+2 learned)
- Stored rule hits: 36
- Time: 75s
- Log: logs/learn_20260329_184339.log
- Strategies added:
  - `marker_arm_extend`: rectangles with isolated single-pixel markers; arms extend from nearest rect edge toward marker with cross-shaped endpoints (solves a2d730bd)
  - `subgrid_invert`: grid divided by 0-separator lines into sub-grids; swaps pattern↔uniform fill, removes colour-5 noise; uniform uses minority colour in input, majority in output (solves 6350f1f4)
- Improvement: 95.0% → 100.0% (+2 tasks)

---
## Learning Loop -- 2026-03-29 18:46

- Split: training, Tasks: 40
- Correct: 40 / 40 (100.0%)
- Rules: 81 -> 81 (+0 learned)
- Stored rule hits: 38
- Time: 74s
- Log: logs/learn_20260329_184530.log

---
## Session 18 -- 2026-03-29 18:55

### Context
Session 18 started at 40/40 (100%) on the core 40-task set. Expanded to 80 tasks
to find new failures (41/80 = 51.2% before improvements).

### New strategies added (3):

1. **invert_tile** (48131b3c): Input NxN with 0 and one non-zero color. Output is
   2Nx2N tiling of the color-inverted grid (swap 0 ↔ nonzero). Category: color
   inversion + simple tiling tasks.

2. **double_mirror** (62c24649): NxN input → 2Nx2N output via horizontal reflection
   (left-right) then vertical reflection (top-bottom), creating 4-fold kaleidoscope
   symmetry. Also solved `67e8384a` via memory reuse. Category: kaleidoscope /
   double-mirror expansion tasks.

3. **column_fill_tile** (f5b8619d): Columns with any non-zero cell have their 0s
   replaced with a learned fill color (e.g. 8); all-zero columns stay 0. Result is
   tiled 2x2 to produce 2Nx2N output. Category: column-activation fill + tiling tasks.

### Results

- Split: training, Tasks: 80
- Correct: 45 / 80 (56.2%)  [################..............]
- Previous: 41 / 80 (51.2%)  -- improvement: +4 tasks
- Core 40 tasks: 40 / 40 (100%) maintained
- Rules: 92 -> 98 (+6 learned)
- Stored rule hits: 42
- Time: 135s
- Log: logs/learn_20260329_185547.log
- Regression gate (08ed6ac7): CORRECT

---
## Learning Loop -- 2026-03-29 18:49

- Split: training, Tasks: 80
- Correct: 41 / 80 (51.2%)
- Rules: 81 -> 89 (+8 learned)
- Stored rule hits: 38
- Time: 153s
- Log: logs/learn_20260329_184704.log

---
## Learning Loop -- 2026-03-29 18:58

- Split: training, Tasks: 80
- Correct: 45 / 80 (56.2%)
- Rules: 92 -> 98 (+6 learned)
- Stored rule hits: 42
- Time: 135s
- Log: logs/learn_20260329_185547.log

---
## Learning Loop -- 2026-03-29 19:00

- Split: training, Tasks: 80
- Correct: 45 / 80 (56.2%)
- Rules: 98 -> 104 (+6 learned)
- Stored rule hits: 42
- Time: 136s
- Log: logs/learn_20260329_185837.log

---
## Learning Loop -- 2026-03-29 19:06

- Split: training, Tasks: 3
- Correct: 0 / 3 (0.0%)
- Rules: 104 -> 104 (+0 learned)
- Stored rule hits: 0
- Time: 9s
- Log: logs/learn_20260329_190601.log

---
## Learning Loop -- 2026-03-29 19:09

- Split: training, Tasks: 80
- Correct: 47 / 80 (58.8%)
- Rules: 107 -> 112 (+5 learned)
- Stored rule hits: 45
- Time: 172s
- Log: logs/learn_20260329_190650.log

---
## Learning Loop -- 2026-03-29 19:12

- Split: training, Tasks: 80
- Correct: 48 / 80 (60.0%)
- Rules: 112 -> 117 (+5 learned)
- Stored rule hits: 45
- Time: 141s
- Log: logs/learn_20260329_191017.log

---
## Session 19 -- 2026-03-29 19:06

### New strategies added (3):

1. **separator_xor** (99b1bc43): Input split by a full separator row (all same
   non-0 color) into two equal-sized sub-grids. Top half uses color A, bottom
   uses color B. Output: where exactly one half is non-zero → output_color;
   both or neither → 0. Category: two-half XOR / binary overlay tasks.

2. **bbox_fill** (6d75e8bb): Single foreground color (e.g. 8) on black
   background. The bounding box of all foreground pixels is computed; every
   0-cell inside the bbox becomes a fill color (e.g. 2), while foreground
   pixels are preserved. Category: bounding-box interior fill / shape
   completion tasks.

3. **sector_max_fill** (29623171): Grid divided by full rows/cols of a
   separator color (e.g. 5) into equal-sized sectors. Each sector has scattered
   pixels of one accent color. Sector(s) with the maximum pixel count are
   filled entirely with the accent color; all others cleared to 0. Separators
   unchanged. Category: grid-sector voting / max-count fill tasks.

### Results

- Split: training, Tasks: 80
- Correct: 48 / 80 (60.0%)  [##################............]
- Previous: 45 / 80 (56.2%)  -- improvement: +3 tasks
- Rules: 112 -> 117 (+5 learned)
- Stored rule hits: 45
- Time: 141s
- Log: logs/learn_20260329_191017.log
- Regression gate (08ed6ac7): CORRECT
