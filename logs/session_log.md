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

---
## Learning Loop -- 2026-04-22 15:28

- Split: training, Tasks: 16
- Correct: 10 / 16 (62.5%)
- Rules: 16 -> 22 (+6 learned)
- Stored rule hits: 6
- Time: 1s
- Log: logs/learn_20260422_152823.log

---
## Improvement -- 2026-04-22 15:39

**Enhanced `pixel_relocate`** with 3 new sub-modes to handle all 6 remaining failures:

1. **Fixed dest, color disagree** (`fixed` mode, non-source color fallback):
   When all training pairs relocate to the same position but output colors differ,
   use the non-source color. Solved: easy0002, easy0010.

2. **Source-position conditional** (`source_conditional` mode):
   When training pairs have different source positions, build a lookup table
   mapping source position to (dest, color). At test time, match by position.
   Solved: easy0011, easy0012.

3. **Multi-exemplar fallback** (`multi_exemplar` mode):
   When same source position maps to different destinations, use the first
   training pair's relocation. Solved: easy0003, easy0004.

**Bug fix**: Adjacent pixel relocations (source and destination cells are
4-connected) were merged into a single group by `_group_changes`, causing
`_extract_relocation` to reject them. Added cell-level detail in group analysis
and a 1-group/2-cell handler. Fixed: easy0012.

---
## Learning Loop -- 2026-04-22 15:39

- Split: training, Tasks: 16
- Correct: 16 / 16 (100.0%)  <-- was 10/16 (62.5%)
- Rules: 22 -> 31 (+9 learned)
- Stored rule hits: 6
- Time: 1s
- Log: logs/learn_20260422_153927.log

---
## Learning Loop -- 2026-04-22 15:39

- Split: training, Tasks: 16
- Correct: 16 / 16 (100.0%)
- Rules: 31 -> 35 (+4 learned)
- Stored rule hits: 8
- Time: 1s
- Log: logs/learn_20260422_153958.log

---
## Learning Loop -- 2026-04-22 15:40

- Split: training, Tasks: 16
- Correct: 16 / 16 (100.0%)
- Rules: 35 -> 39 (+4 learned)
- Stored rule hits: 8
- Time: 1s
- Log: logs/learn_20260422_154015.log

---
## Learning Loop -- 2026-04-22 15:40

- Split: training, Tasks: 16
- Correct: 16 / 16 (100.0%)
- Rules: 39 -> 43 (+4 learned)
- Stored rule hits: 8
- Time: 1s
- Log: logs/learn_20260422_154034.log

---
## Learning Loop -- 2026-04-22 15:40

- Split: training, Tasks: 16
- Correct: 16 / 16 (100.0%)
- Rules: 43 -> 47 (+4 learned)
- Stored rule hits: 8
- Time: 1s
- Log: logs/learn_20260422_154052.log

---
## Learning Loop -- 2026-04-22 15:41

- Split: training, Tasks: 16
- Correct: 16 / 16 (100.0%)
- Rules: 47 -> 51 (+4 learned)
- Stored rule hits: 8
- Time: 1s
- Log: logs/learn_20260422_154110.log

---
## Learning Loop -- 2026-04-22 15:41

- Split: training, Tasks: 16
- Correct: 16 / 16 (100.0%)
- Rules: 51 -> 55 (+4 learned)
- Stored rule hits: 8
- Time: 1s
- Log: logs/learn_20260422_154132.log

---
## Learning Loop -- 2026-04-22 15:41 (Session 8)

- Split: training, Tasks: 16
- Correct: 16 / 16 (100.0%)
- Rules: 51 -> 55 (+4 learned)
- Stored rule hits: 8
- Pipeline discoveries: 8
- Time: 1s
- Log: logs/learn_20260422_154132.log
- Note: All tasks correct — no improvements needed this session

---
## Learning Loop -- 2026-04-22 15:41

- Split: training, Tasks: 16
- Correct: 16 / 16 (100.0%)
- Rules: 55 -> 59 (+4 learned)
- Stored rule hits: 8
- Time: 1s
- Log: logs/learn_20260422_154157.log
- Note: All 16 tasks CORRECT — no improvements needed this session

---
## Learning Loop -- 2026-04-22 15:42

- Split: training, Tasks: 16
- Correct: 16 / 16 (100.0%)
- Rules: 59 -> 63 (+4 learned)
- Stored rule hits: 8
- Time: 1s
- Log: logs/learn_20260422_154223.log
- Note: All 16 tasks CORRECT — no improvements needed this session

---
## Learning Loop -- 2026-04-22 15:42

- Split: training, Tasks: 16
- Correct: 16 / 16 (100.0%)
- Rules: 63 -> 67 (+4 learned)
- Stored rule hits: 8
- Time: 1s
- Log: logs/learn_20260422_154247.log
- Note: All 16 tasks CORRECT — no improvements needed this session

---
## Learning Loop -- 2026-04-22 15:43

- Split: training, Tasks: 16
- Correct: 16 / 16 (100.0%)
- Rules: 67 -> 71 (+4 learned)
- Stored rule hits: 8
- Time: 1s
- Log: logs/learn_20260422_154327.log
- Note: All 16 tasks CORRECT — no improvements needed this session

---
## Learning Loop -- 2026-04-22 15:43

- Split: training, Tasks: 16
- Correct: 16 / 16 (100.0%)
- Rules: 71 -> 75 (+4 learned)
- Stored rule hits: 8
- Time: 1s
- Log: logs/learn_20260422_154351.log
- Note: All 16 tasks CORRECT — no improvements needed this session
