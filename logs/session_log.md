
---
## Learning Loop -- 2026-03-29 23:03

- Split: training, Tasks: 20
- Correct: 0 / 20 (0.0%)
- Rules: 0 -> 3 (+3 learned)
- Stored rule hits: 0
- Time: 49s
- Log: logs/learn_20260329_230223.log

---
## Learning Loop -- 2026-03-29 23:07

- Split: training, Tasks: 20
- Correct: 3 / 20 (15.0%)
- Rules: 3 -> 8 (+5 learned)
- Stored rule hits: 0
- Time: 37s
- Log: logs/learn_20260329_230715.log

---
## Session 1 Analysis — 2026-03-29 23:07

### New Rules Added (3)
1. **scale_up** (geometry) — each cell becomes NxN block; solves c59eb873
2. **mirror_vertical_append** (geometry) — output = input + vertically flipped input; solves 8be77c9e
3. **fill_rect_by_size** (fill) — fill rectangular outlines by interior area rank; solves c0f76784

### Result
- Before: 0/20 (0%)
- After:  3/20 (15%)
- Regression gate (08ed6ac7): CORRECT

---
## Learning Loop -- 2026-03-29 23:09

- Split: training, Tasks: 20
- Correct: 3 / 20 (15.0%)
- Rules: 8 -> 10 (+2 learned)
- Stored rule hits: 3
- Time: 36s
- Log: logs/learn_20260329_230834.log

---
## Learning Loop -- 2026-03-29 23:14

- Split: training, Tasks: 20
- Correct: 5 / 20 (25.0%)
- Rules: 10 -> 14 (+4 learned)
- Stored rule hits: 3
- Time: 36s
- Log: logs/learn_20260329_231405.log

---
## Session 2 Analysis — 2026-03-29 23:14

### New Rules Added (2)
1. **corner_quadrant_fill** (fill) — rectangle of uniform color with 4 diagonal corner markers; fill each quadrant with its corner color, remove markers. Handles multiple rectangles per grid. Solves e9ac8c9e.
2. **component_size_recolor** (detect) — find connected components of a source color, rank by unique sizes (largest first), recolor each component with rank-based color (1, 2, 3, ...). Solves 6e82a1ae, also solves regression gate 08ed6ac7.

### Result
- Before: 3/20 (15%)
- After:  5/20 (25%)
- Regression gate (08ed6ac7): CORRECT

---
## Learning Loop -- 2026-03-29 23:15

- Split: training, Tasks: 20
- Correct: 5 / 20 (25.0%)
- Rules: 14 -> 16 (+2 learned)
- Stored rule hits: 5
- Time: 36s
- Log: logs/learn_20260329_231518.log
