
---
## Learning Loop -- 2026-04-29 06:22

- Split: training, Tasks: 20
- Correct: 0 / 20 (0.0%)
- Rules: 0 -> 0 (+0 learned)
- Stored rule hits: 0
- Time: 55s
- Log: logs/learn_20260429_062114.log

### Session 1 reflections (2026-04-29)

**Failures analyzed:** `8be77c9e`, `d23f8c26` (both currently fall through to `identity`).

**Topology groups & strategies:**

1. **Vertical mirror (height doubles, width same).** `8be77c9e` outputs the input stacked above its vertically-flipped copy. ARCKG signature: `size_ratio = [2.0, 1.0]`. Created `concepts/vertical_mirror_below.json` — `flip_vertical` then `concat_vertical`, no parameters needed.

2. **Single-column preservation (size unchanged).** `d23f8c26` blanks every cell except one column (the center). The existing `column_index_from_arckg` inference already returns the center-column sentinel (-1) for this topology. Created `concepts/preserve_single_column.json` — `extract_column` -> `make_uniform` -> `place_column`, parameterized on `col_index` and `bg`.

**Quick validation:**
- `python run_task.py --task 8be77c9e` -> CORRECT (matched `vertical_mirror_below` with params `{}`).
- `python run_task.py --task d23f8c26` -> CORRECT (matched `preserve_single_column` with params `{col_index: -1, bg: 0}`).
- `python run_task.py` (regression task `08ed6ac7`) -> still INCORRECT, unchanged by these concepts (color-counting topology, no signature overlap).

**Notes for next session:**
- The two new concepts should each pick up a single task in the next learn run; expect 2/20.
- Many of the remaining 18 failures involve a horizontal separator row + cross-half pattern transfer (`c9680e90`, `878187ab`, `60a26a3e`). Worth a dedicated concept once the inference primitives can identify a separator and per-half objects.

---
## Learning Loop -- 2026-04-29 06:26

- Split: training, Tasks: 20
- Correct: 2 / 20 (10.0%)
- Rules: 0 -> 2 (+2 learned)
- Stored rule hits: 0
- Time: 44s
- Log: logs/learn_20260429_062610.log

### Session 2 reflections (2026-04-29)

**Failures analyzed:** `c59eb873` (3x3 -> 6x6, 2x2 -> 4x4, 4x4 -> 8x8 — every cell scaled to a 2x2 block). Surveyed others (`bbc9ae5d`, `878187ab`, `85c4e7cd`, `9f669b64`, etc.); most need shape-aware logic that the 24 frozen primitives + available infer methods can't express cleanly.

**Topology group & strategy:**

1. **Uniform integer scale-up (output dims = factor x input dims, same factor for h and w).** ARCKG signature: `size_comm=False`, all height/width ratios are equal integers >= 2. The existing `ratio_hw` infer method already returns the factor. Created `concepts/uniform_scale_up.json` — single `scale` step, parameterized on `factor`. Only one task (`c59eb873`) in the current sample matches, but the concept is fully general for any factor and is the right shape to capture future scale-up tasks.

**Quick validation:**
- `try_concepts` on `c59eb873` -> matched `uniform_scale_up` with `{factor: 2}`.
- Existing matches still hold: `8be77c9e` -> `vertical_mirror_below`, `d23f8c26` -> `preserve_single_column`.
- Non-targets (`878187ab`, `bbc9ae5d`) still NO_MATCH (no false positives from signature filter).
- `python run_task.py` (regression `08ed6ac7`) -> still INCORRECT — pre-existing, unrelated to this concept.

**Notes for next session:**
- Expect 3/20 next learn run (`c59eb873` joining `8be77c9e` and `d23f8c26`).
- The next high-leverage concept families I see in the data, but which need new infer methods or primitives:
  - **Concentric-ring color reversal** (`85c4e7cd`): the colors form nested rectangles and the output reverses the ring color order. `color_map_from_arckg` won't work — the {old:new} mapping differs per pair. Would need a `ring_color_reversal` infer method that walks rings from the outside in and pairs colors with their mirrored position.
  - **Per-cell gravity toward a wall** (`825aa9e9`): grid is partitioned by separator lines into rectangular cells, and within each cell the non-bg shape slides toward the cell's "wall" edge. Needs separator-aware sectioning + directional sub-grid gravity.
  - **Row-extension stair pattern** (`bbc9ae5d`): output adds rows below where each row extends the colored prefix by one cell. The relation between row count, prefix length, and grid width is non-obvious and may not be expressible without a new primitive.
