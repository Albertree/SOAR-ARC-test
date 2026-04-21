# SOAR-ARC Session Log

---
## Learning Loop -- 2026-04-21 18:05

- Split: training, Tasks: 20
- Correct: 0 / 20 (0.0%)
- Rules: 0 -> 3 (+3 learned)
- Stored rule hits: 0
- Time: 65s
- Log: logs/learn_20260421_180356.log

---
## Session 1 -- 2026-04-21 18:14

### Strategies Added
1. **uniform_scale** — output is NxN block scale-up of input (solves c59eb873)
2. **recolor_by_size** — connected components of one color recolored by size rank (solves 6e82a1ae)
3. **corner_fill** — rectangle of fill color + 4 corner markers → quadrant fill (solves e9ac8c9e)

### Learning Loop Results
- Split: training, Tasks: 20
- Correct: 3 / 20 (15.0%) — up from 0/20
- Solved: e9ac8c9e (corner_fill), 6e82a1ae (recolor_by_size), c59eb873 (uniform_scale)
- Rules: 3 -> 8 (+5 learned)
- Stored rule hits: 0
- Time: 64s
- Log: logs/learn_20260421_181336.log
- Regression: 08ed6ac7 CORRECT

---
## Learning Loop -- 2026-04-21 18:16

- Split: training, Tasks: 20
- Correct: 3 / 20 (15.0%)
- Rules: 8 -> 10 (+2 learned)
- Stored rule hits: 3
- Time: 64s
- Log: logs/learn_20260421_181517.log

---
## Session 2 -- 2026-04-21 18:26

### Strategies Added
1. **vertical_mirror** — output = input rows + reversed input rows (solves 8be77c9e)
2. **fill_rect_by_size** — rectangular frames with hollow interiors filled by interior dimension: 1→6, 2→7, 3→8 (solves c0f76784)
3. **staircase_growth** — single row with K colored cells expands to W/2 rows, each row adding one cell (solves bbc9ae5d)

### Learning Loop Results
- Split: training, Tasks: 20
- Correct: 6 / 20 (30.0%) — up from 3/20
- Solved: e9ac8c9e, 6e82a1ae, c59eb873 (stored), c0f76784 (fill_rect_by_size), 8be77c9e (vertical_mirror), bbc9ae5d (staircase_growth)
- Rules: 10 -> 15 (+5 learned)
- Stored rule hits: 3
- Time: 55s
- Log: logs/learn_20260421_182507.log
- Regression: 08ed6ac7 CORRECT
