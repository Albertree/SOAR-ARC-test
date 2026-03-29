
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
