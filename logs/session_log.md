
---
## Learning Loop -- 2026-03-29 23:20

- Split: training, Tasks: 20
- Correct: 0 / 20 (0.0%)
- Rules: 0 -> 3 (+3 learned)
- Stored rule hits: 0
- Time: 42s
- Log: logs/learn_20260329_232016.log

---
## Learning Loop -- 2026-03-29 23:25

- Split: training, Tasks: 20
- Correct: 3 / 20 (15.0%)
- Rules: 3 -> 7 (+4 learned)
- Stored rule hits: 0
- Time: 36s
- Log: logs/learn_20260329_232522.log

### Session 1 Analysis (Claude Code)

**New rules added (3):**
1. `mirror_vertical_append` (geometry) — input stacked with its vertical flip → solved 8be77c9e
2. `recolor_by_size` (color) — components recolored 1,2,3 by descending size rank → solved 6e82a1ae
3. `extract_center_column` (structure) — keep only center column, zero rest → solved d23f8c26

**Improvement:** 0/20 → 3/20 (0% → 15%)

---
## Learning Loop -- 2026-03-29 23:32

- Split: training, Tasks: 20
- Correct: 3 / 20 (15.0%)
- Rules: 0 -> 5 (+5 learned)
- Stored rule hits: 0
- Time: 45s
- Log: logs/learn_20260329_233130.log

---
## Learning Loop -- 2026-03-29 23:34

- Split: training, Tasks: 20
- Correct: 6 / 20 (30.0%)
- Rules: 5 -> 9 (+4 learned)
- Stored rule hits: 3
- Time: 36s
- Log: logs/learn_20260329_233356.log

### Session 2 Analysis (Claude Code)

**New rules added (3):**
1. `scale_up` (geometry) — each pixel scaled to NxN block (detects integer scale factor) → solved c59eb873
2. `staircase_fill` (fill) — 1-row colored prefix grows into descending staircase triangle → solved bbc9ae5d
3. `reverse_frames` (structure) — concentric rectangular frames get color order reversed → solved 85c4e7cd

**Improvement:** 3/20 → 6/20 (15% → 30%)
**Memory reuse:** 3 stored rules successfully reused (mirror_vertical_append, extract_center_column, recolor_by_size)
