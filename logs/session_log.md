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
