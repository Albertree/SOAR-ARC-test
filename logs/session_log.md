# SOAR-ARC Session Log

---
## Learning Loop -- 2026-04-22 15:08

- Split: training, Tasks: 16
- Correct: 0 / 16 (0.0%)
- Rules: 0 -> 8 (+8 learned)
- Stored rule hits: 0
- Time: 2s
- Log: logs/learn_20260422_150816.log

---
## Learning Loop -- 2026-04-22 15:22

- Split: training, Tasks: 16
- Correct: 0 / 16 (0.0%)
- Rules: 0 -> 8 (+8 learned)
- Stored rule hits: 0
- Time: 2s
- Log: logs/learn_20260422_152206.log

---
## Improvement -- 2026-04-22 15:27

**Strategy added**: `pixel_relocate` in GeneralizeOperator + PredictOperator

Detects single-pixel relocation tasks (1 non-bg pixel moves to new position).
Two sub-modes:
- **fixed**: all training pairs share the same output position; color is either
  fixed (always same) or preserved (matches input color)
- **conditional**: different input colors map to different output destinations
  and colors (color-conditional rules)

Tasks solved: easy0001, easy0005, easy0006, easy0007, easy0008, easy0009,
easy0013, easy0014, easy0015, easy0016

Remaining 6 failures (easy0002,0003,0004,0010,0011,0012) have ambiguous
training data: same input color produces different outputs across pairs.

---
## Learning Loop -- 2026-04-22 15:27

- Split: training, Tasks: 16
- Correct: 10 / 16 (62.5%)  ← was 0/16
- Rules: 8 -> 16 (+8 learned)
- Stored rule hits: 4
- Time: 1s
- Log: logs/learn_20260422_152753.log
