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
