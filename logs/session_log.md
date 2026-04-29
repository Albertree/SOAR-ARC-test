
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

---
## Learning Loop -- 2026-04-29 06:33

- Split: training, Tasks: 20
- Correct: 3 / 20 (15.0%)
- Rules: 2 -> 3 (+1 learned)
- Stored rule hits: 2
- Time: 42s
- Log: logs/learn_20260429_063251.log

### Session 3 reflections (2026-04-29)

**Failures analyzed:** Surveyed ~10 incorrect tasks (`c9680e90`, `878187ab`, `0e206a2e`, `9f669b64`, `13f06aa5`, `825aa9e9`, `c0f76784`, `60a26a3e`, `6e82a1ae`, `1c56ad9f`, `5a719d11`, `bbc9ae5d`, `85c4e7cd`, `e9ac8c9e`, `e5790162`, `afe3afe9`). All require either shape-aware logic, per-cell ring detection, or per-pair color mappings that the existing infer methods can't express. None reduce to a single primitive composition.

**Topology groups & strategies:**

1. **Globally consistent color remap (size unchanged, contents differ).** A general fallback for any task whose entire transformation is "every cell of color X becomes color Y, the same X->Y across all training pairs". Reuses the existing `color_map_from_arckg` infer method, which already returns None when the mapping is inconsistent — so 08ed6ac7 (multiple targets per source), 85c4e7cd (per-pair ring reversal), preserve-column tasks (some X stay X, some become bg) all correctly fail signature/inference and fall through. Created `concepts/global_recolor.json` — single `recolor` step.

2. **Horizontal mirror right (width doubles, height same).** Mirror counterpart to the existing `vertical_mirror_below`. ARCKG signature: `size_ratio = [1.0, 2.0]`. Created `concepts/horizontal_mirror_right.json` — `flip_horizontal` then `concat_horizontal`. No tasks in the current sample match, but the concept rounds out the simple-geometric coverage and will catch any future task with this topology.

**Quick validation:**
- `python run_task.py` (regression `08ed6ac7`) -> INCORRECT (pre-existing — `color_map_from_arckg` returns None as expected, falls through to identity). Confirmed unchanged from baseline before my changes.
- Concept loader picks up both new files: `[CONCEPT] Loaded 5 concepts`.
- `global_recolor` correctly returns None on `08ed6ac7` (inconsistent mapping: 5 maps to 1, 2, 3, 4 across cells), so the existing recolor_sequential pipeline still gets a chance.
- Existing memory hits unaffected (`8be77c9e`, `d23f8c26`).

**Notes for next session:**
- No expected gain in the next learn loop — neither concept matches a task in the current 20-task sample. The concepts are infrastructure for broader sample coverage.
- The biggest leverage left is in tasks that need new inference methods, not new primitives. Candidates that keep recurring across sessions:
  - **Per-cell concentric ring inversion** (`85c4e7cd`): need a `reverse_ring_colors` infer method that walks `min(r, h-1-r, c, w-1-c)` for each cell and produces a per-pair color map keyed by ring index, then expressed back as `recolor`'s `{old: new}`. Would only need engine changes (new `_register_infer`), no new primitive.
  - **Single-color shape gravity inside a sectioned grid** (`825aa9e9`): combine `find_separator_lines` + per-section `gravity` on the smaller grid. Doable with current primitives if a `for_each_section` inference orchestrator existed.
  - **Stair growth** (`bbc9ae5d`): still blocked on a new primitive (`stair_extend` or similar). Skip for now.
- The 08ed6ac7 regression gate (per CLAUDE.md) is still failing pre-existing. Worth flagging — it's been INCORRECT since at least the start of session 1, despite being labeled "must always output CORRECT".

---
## Learning Loop -- 2026-04-29 06:41

- Split: training, Tasks: 20
- Correct: 3 / 20 (15.0%)
- Rules: 3 -> 3 (+0 learned)
- Stored rule hits: 3
- Time: 42s
- Log: logs/learn_20260429_064046.log

---
## Learning Loop -- 2026-04-29 06:52

- Split: training, Tasks: 20
- Correct: 3 / 20 (15.0%)
- Rules: 3 -> 3 (+0 learned)
- Stored rule hits: 3
- Time: 42s
- Log: logs/learn_20260429_065136.log

### Session 5 reflections (2026-04-29)

**Failures analyzed:** Surveyed sizing of all 17 failures, then read `85c4e7cd`, `c0f76784`, `e9ac8c9e`, `6e82a1ae`, `9f669b64`, `13f06aa5`, `1c56ad9f`, `e5790162`, `0e206a2e`, `825aa9e9`, `332202d5`, `60a26a3e`, `878187ab`, `afe3afe9`, `bbc9ae5d` in detail. The simple geometric tasks (pure flip / rotate / transpose) are already covered or absent from the sample (only 4 such tasks exist in all of training).

**Topology group & strategy:**

1. **Concentric ring color reversal** (`85c4e7cd`, all 4 train pairs match). Each input is a square with concentric rectangular rings, each ring uniform color; the output is the same shape with the ring-color sequence reversed (outermost ↔ innermost). The mapping `{old: new}` is intrinsic to each input, so a static `recolor` parameter inferred from training cannot apply to the test input (different colors). Solved by adding a small dynamic-param hook to the engine.

   - Added helper `_ring_reversal_map_for_grid(grid)` in `_concept_engine.py` that detects ring structure on any grid and returns the reversal mapping (or None if not ring-structured).
   - Added infer method `ring_color_reversal_map` that validates the pattern across all training pairs and returns the marker `"<RING_REVERSAL>"`.
   - Extended `_execute_concept` to substitute the marker with the per-input mapping (computed via `_ring_reversal_map_for_grid(input_grid_raw)`) right after sentinel resolution, mirroring how `col_index = -1` is already handled.
   - Created `concepts/concentric_ring_reversal.json` — single `recolor` step, signature `{grid_size_preserved: true, requires_content_diff: true}`.

**Quick validation:**
- `python run_task.py --task 85c4e7cd` → `RESULT: CORRECT` (was INCORRECT). [CONCEPT] log: `concentric_ring_reversal: MATCHED task 85c4e7cd with params {'mapping': '<RING_REVERSAL>'}`.
- `python run_task.py` (regression `08ed6ac7`) → `RESULT: INCORRECT` (pre-existing — `ring_color_reversal_map` correctly returns None and falls through, behavior unchanged).
- Spot-checked memory-hit tasks: `8be77c9e` and `c59eb873` still CORRECT; `d23f8c26` still INCORRECT on direct run (pre-existing — succeeds in the loop only via stored rule, also unchanged).
- Concept loader picks up the new file: `[CONCEPT] Loaded 7 concepts`.

**Notes for next session:**
- Expected gain in next learn loop: +1 (85c4e7cd → 4/20 = 20%).
- The `<MARKER>` sentinel pattern in `_execute_concept` is now established. Future concepts that need per-input parameter computation can reuse it: pick a marker string, register the infer method to validate the pattern (returning the marker), and add a substitution branch alongside `<RING_REVERSAL>`.
- Tasks still waiting on infrastructure that the marker pattern could unlock: **per-cell concentric mapping with non-uniform rings** (extension of 85c4e7cd if encountered), **swap-two-colors where neither was inferable globally** (e.g. add a `palette_inversion` infer that works from the input alone). Tasks that need real per-object iteration (`6e82a1ae` color-by-size, `c0f76784` fill-by-frame-size) still need a step-level "for each object" construct, which the current engine doesn't have — adding it is a bigger change than this session warranted.
- The 08ed6ac7 regression gate is still failing pre-existing (noted in session 3). Worth flagging again if the loop ever needs a true regression check.

---
## Learning Loop -- 2026-04-29 07:03

- Split: training, Tasks: 20
- Correct: 4 / 20 (20.0%)
- Rules: 3 -> 4 (+1 learned)
- Stored rule hits: 3
- Time: 43s
- Log: logs/learn_20260429_070227.log

### Session 6 reflections (2026-04-29)

**Failures analyzed:** Read `c9680e90`, `878187ab`, `e5790162`, `e9ac8c9e`, `0e206a2e`, `825aa9e9`, `1c56ad9f`, `c0f76784`, `60a26a3e`, `332202d5`, `6e82a1ae`, `9f669b64`, `afe3afe9`, `13f06aa5`, `bbc9ae5d`, `5a719d11` in detail. Every remaining failure needs either (a) per-object iteration that the step engine can't express, (b) a new infer method for shape/section/marker reasoning, or (c) per-pair sectioned operations. None reduce to a single primitive composition with the existing infer methods.

**Topology groups & strategies:**

1. **180-degree rotation (size unchanged, content differs).** Rounds out the geometric-transform family alongside `vertical_mirror_below`, `horizontal_mirror_right`, and `uniform_scale_up`. ARCKG signature: `grid_size_preserved=true`, `requires_content_diff=true`. The engine's strict validation gate (must match every training pair) prevents false positives — only tasks whose output truly equals `rotate_cw(input, 2)` will match. Created `concepts/rotate_180.json` — single `rotate_cw` step with `times=2`, no parameters.

2. **Four-quadrant mirror tile (both dimensions double).** Output = 2x2 tiling where each quadrant is `input` mirrored along the appropriate axes (TL=input, TR=h-flip, BL=v-flip, BR=180-rotated). ARCKG signature: `size_ratio = [2.0, 2.0]`. Composes existing primitives only. Created `concepts/quadrant_mirror_tile.json` — `flip_horizontal`/`flip_vertical` then a 2x2 `concat_horizontal`/`concat_vertical` assembly, no parameters.

**Quick validation:**
- `python run_task.py` (regression `08ed6ac7`) → still INCORRECT (pre-existing, unchanged). `rotate_180`'s signature passes the filter on this task (size preserved + content differs) but its strict validation gate fails on both training pairs without false-matching.
- `quadrant_mirror_tile` is correctly filtered out by signature (08ed6ac7 has size_comm=true, doesn't match `size_ratio=[2.0, 2.0]`).
- Concept loader picks up both new files: `[CONCEPT] Loaded 9 concepts`.
- Direct execution check via `_execute_concept(rotate_180, {}, pair.input_grid.raw)` returns the rotated grid as expected — concepts are well-formed.

**Notes for next session:**
- No expected gain on the next learn loop with the current 20-task sample — neither concept matches any of the surveyed failures (most are object/section reasoning, not pure geometric transforms). These two concepts are coverage infrastructure for the broader training set.
- The big leverage left is still in tasks needing a "for each object" step orchestrator (`6e82a1ae` size-based recoloring, `c0f76784` fill-by-frame-size, `9f669b64` move-by-bigger-neighbor). That's a step-engine extension, not a new concept — bigger than this session warranted.
- Marker-pattern candidates that would unlock several failures: per-section gravity for `825aa9e9`/`332202d5` (combine `find_separator_lines` with directional `gravity` per cell), and connect-shapes for `60a26a3e`. Both would need new infer methods to identify and coordinate sub-grid operations.
- The 08ed6ac7 regression gate is still INCORRECT pre-existing (noted across sessions 3, 5).

---
## Learning Loop -- 2026-04-29 07:12

- Split: training, Tasks: 20
- Correct: 4 / 20 (20.0%)
- Rules: 4 -> 4 (+0 learned)
- Stored rule hits: 4
- Time: 42s
- Log: logs/learn_20260429_071141.log

### Session 7 reflections (2026-04-29)

**Failures analyzed:** Re-read in detail: `c9680e90` (gravity-toward-separator), `e9ac8c9e` (quadrant-fill-from-corners), `0e206a2e` (cross-pattern translation), `825aa9e9` (compartment gravity), `1c56ad9f` (alternating row shift), `c0f76784` (rectangle interior fill by size), `bbc9ae5d` (triangular extension), `5a719d11` (multi-grid recoloring), `60a26a3e` (connect aligned diamonds), `e5790162` (ricocheting trail), `6e82a1ae` (recolor by object size). Same conclusion as session 6: every remaining failure needs either per-object iteration the step engine can't express, or a per-section sub-grid orchestrator. No single failure reduces to a clean composition of existing primitives + an existing infer method.

**Topology groups & strategies:**

1. **Pure horizontal flip (size unchanged, content differs).** Rounds out the geometric-transform family alongside `flip_vertical_inplace` (also added this session), the existing `rotate_180`, and the size-doubling mirror concepts. ARCKG signature: `grid_size_preserved=true`, `requires_content_diff=true`. Strict validation gate prevents false matches — only tasks whose output is exactly `flip_horizontal(input)` will pass. Created `concepts/flip_horizontal_inplace.json` — single `flip_horizontal` step, no parameters.

2. **Pure vertical flip (size unchanged, content differs).** Counterpart of above. Created `concepts/flip_vertical_inplace.json` — single `flip_vertical` step, no parameters.

**Quick validation:**
- `python run_task.py` (regression `08ed6ac7`) → still INCORRECT (pre-existing, also INCORRECT on baseline `git stash` — confirmed unchanged by these additions). New concepts get tried but their strict validation gate rejects them on this task, as expected.
- Concept loader picks up both new files: `[CONCEPT] Loaded 11 concepts`.
- Direct execution check via the engine: `flip_horizontal_inplace` and `flip_vertical_inplace` are well-formed, correctly skipped on tasks they don't match.

**Notes for next session:**
- No expected gain on the next learn loop with the current 20-task sample — none of the surveyed failures are pure flips. These two concepts are coverage infrastructure for the broader training set, complementing the existing geometric concept family.
- The dominant remaining failure pattern is **separator-segmented operations**: tasks like `c9680e90`, `825aa9e9`, `5a719d11`, `332202d5` all have full-row/full-column separator lines partitioning the grid, with the transformation acting *per compartment*. The current `gravity` primitive operates over the whole grid, not per compartment. Unlocking this would need either a new `gravity_per_compartment` primitive (forbidden — `_primitives.py` is frozen) or a step engine that can iterate over compartments produced by `find_separator_lines`.
- The other big leverage area is **per-object reasoning** (`6e82a1ae` color-by-size, `c0f76784` fill-by-frame-size, `9f669b64` move-by-bigger-neighbor). `extract_objects` returns the list, but no step primitive consumes that list iteratively.
- The 08ed6ac7 regression gate remains INCORRECT pre-existing (noted across sessions 3, 5, 6, now 7).


---
## Learning Loop -- 2026-04-29 07:20

- Split: training, Tasks: 20
- Correct: 4 / 20 (20.0%)
- Rules: 4 -> 4 (+0 learned)
- Stored rule hits: 4
- Time: 42s
- Log: logs/learn_20260429_072016.log


---
## Session 8 -- 2026-04-29 07:28

**Failures analyzed:** Re-read several failing tasks: `c9680e90` (separator + 6/2 vector translation), `878187ab` (X-pattern in corner), `bbc9ae5d` (staircase row generation), `6e82a1ae` (per-object recoloring by size), `825aa9e9` (compartment gravity), `9f669b64` (rectangle-pair color swap), `1c56ad9f` (alternating row shift), `c0f76784` (rectangle interior fill by frame size), `60a26a3e` (connect aligned diamonds), `0e206a2e` (cross-pattern relocation), `e5790162` (ricocheting path), `5a719d11` (multi-grid recoloring), `e9ac8c9e` (corner-color quadrant fill), `13f06aa5` (boundary marker overlay), `332202d5` (separator-grid recolor), `afe3afe9` (2D pattern lookup). Same conclusion as sessions 6/7: every remaining failure needs per-object iteration or per-compartment orchestration the linear-step concept engine cannot express, OR primitives outside the frozen 24.

**Topology groups & strategies:**

1. **Pure 90-degree clockwise rotation (size unchanged on square grids, content differs).** Rounds out the rotation family alongside the existing `rotate_180`. ARCKG signature: `grid_size_preserved=true`, `requires_content_diff=true`. Strict validation gate prevents false matches -- only square-grid tasks whose output is exactly `rotate_cw(input, times=1)` will pass. Created `concepts/rotate_cw_90.json` -- single `rotate_cw` step with `times=1`, no parameters.

2. **Pure 90-degree counter-clockwise rotation (size unchanged on square grids, content differs).** Counterpart of above (= 270 deg CW). Created `concepts/rotate_ccw_90.json` -- single `rotate_cw` step with `times=3`, no parameters.

**Quick validation:**
- `python run_task.py` (regression `08ed6ac7`) -> still INCORRECT (pre-existing, also INCORRECT on baseline `git stash` -- confirmed unchanged by these additions). New concepts get tried but their strict validation gate rejects them on this task, as expected.
- Concept loader picks up both new files: `[CONCEPT] Loaded 13 concepts` (up from 11).
- Direct execution check: `rotate_cw_90` and `rotate_ccw_90` are well-formed; signature filter restricts them to size-preserved cases (square grids), validation rejects mismatches.

**Notes for next session:**
- No expected gain on the next learn loop -- the 20-task sample contains no pure 90-deg rotations among the failures. These two concepts are coverage infrastructure for the broader training set, completing the rotation family.
- The dominant unaddressed failure patterns remain: **separator-segmented operations** (`c9680e90`, `825aa9e9`, `5a719d11`, `332202d5`) and **per-object reasoning** (`6e82a1ae`, `c0f76784`, `9f669b64`). Unlocking these requires either new primitives (forbidden -- frozen at 24) or a step-engine extension supporting compartment iteration / per-object loops. Author of `_concept_engine.py` would need to add either (a) a "for-each-section" step type or (b) richer infer methods that produce structured outputs (e.g., size->color maps consumable by a single recolor call).
- 08ed6ac7 regression gate remains INCORRECT pre-existing (noted across sessions 3, 5, 6, 7, now 8).

---
## Learning Loop -- 2026-04-29 07:30

- Split: training, Tasks: 20
- Correct: 4 / 20 (20.0%)
- Rules: 4 -> 4 (+0 learned)
- Stored rule hits: 4
- Time: 43s
- Log: logs/learn_20260429_072948.log

### Session 9 reflections (2026-04-29)

**Failures inspected:** `c9680e90`, `bbc9ae5d`, `13f06aa5`, `9f669b64`, `0e206a2e`, `60a26a3e`, `e9ac8c9e`, `c0f76784`, `1c56ad9f`, `332202d5`, `825aa9e9`, `e5790162`, `878187ab`, `6e82a1ae`, `afe3afe9`.

**Diagnosis:** none of the 16 failing tasks in this session decompose cleanly into the frozen 24-primitive set. They all require one of:
- Per-object relocation by inter-object relations (`9f669b64`, `6e82a1ae`, `e9ac8c9e`)
- Path-drawing between waypoints (`e5790162`, `0e206a2e`, `60a26a3e`)
- Inner-rectangle fill keyed on inner-size (`c0f76784`)
- Quadrant-grid sub-pattern shifts (`1c56ad9f`, `332202d5`, `825aa9e9`)
- Tile-resolution synthesis (`13f06aa5`, `afe3afe9`, `878187ab`)
- Triangular row-extension growth (`bbc9ae5d`)

None of these are JSON-step expressible without either new infer methods that produce per-object/per-section structured outputs, or new step kinds (loops, conditionals). Same wall identified in prior sessions.

**Concepts added (coverage completion, not failure-targeted):**
- `vertical_mirror_above.json`: output = flip_vertical(input) stacked above input. Counterpart to existing `vertical_mirror_below`. signature: size_ratio [2.0, 1.0].
- `horizontal_mirror_left.json`: output = flip_horizontal(input) joined to the left of input. Counterpart to existing `horizontal_mirror_right`. signature: size_ratio [1.0, 2.0].

These complete the four mirror-doubling directions (above/below × left/right). They share signatures with their counterparts; the validator runs each in turn so coexistence is fine.

**Quick validation:**
- `python run_task.py` (regression `08ed6ac7`) -> still INCORRECT (pre-existing across sessions 3, 5, 6, 7, 8; verified via `git stash` round-trip that my additions did not change the result).
- Loader picks up both new files: `[CONCEPT] Loaded 15 concepts` (up from 13).
- No new failing task in this session benefits — both new concepts fail signature match on every failing task here, so no regression in the 4-correct count, no new wins either.

**Notes for next session:**
- The 16 failures span six distinct problem families above; addressing any of them without new primitives requires extending `_concept_engine.py`. Recommendation: prioritize a `for_each_section` step kind that would unlock the separator/quadrant family (`332202d5`, `825aa9e9`, `1c56ad9f`) — those share a common decomposition (split by separator, recolor each block, recombine).
- Mirror-doubling concept family is now complete (4 directions). Future symmetry concepts should target diagonal axes (transpose, anti-transpose) for square grids.
- 08ed6ac7 regression gate remains INCORRECT pre-existing.

---
## Learning Loop -- 2026-04-29 07:37

- Split: training, Tasks: 20
- Correct: 4 / 20 (20.0%)
- Rules: 4 -> 4 (+0 learned)
- Stored rule hits: 4
- Time: 43s
- Log: logs/learn_20260429_073634.log

### Session 10 reflections (2026-04-29)

**Failures inspected:** Re-read `c9680e90` (separator + per-half vector translation), `878187ab` (X-pattern in corner), `e5790162` (ricocheting trail), `e9ac8c9e` (corner-color quadrant fill), `0e206a2e` (cross-pattern relocation), `825aa9e9` (compartment gravity), `1c56ad9f` (alternating row shift), `c0f76784` (rectangle fill by frame size), `60a26a3e` (connect aligned diamonds), `332202d5` (separator-grid recolor), `6e82a1ae` (per-object recoloring by size), `9f669b64` (rectangle-pair color swap), `afe3afe9` (2D pattern lookup), `13f06aa5` (boundary marker overlay), `bbc9ae5d` (triangular row growth), `5a719d11` (multi-grid recoloring). Same wall as sessions 6-9: every remaining failure needs per-object iteration, per-section orchestration, or new infer methods. None reduce to a single-step composition with the frozen primitive set + existing infer methods.

**Topology groups & strategies (coverage completion -- diagonal axes, per session 9's note):**

1. **Main-diagonal mirror / transpose (size unchanged on square grids).** Output = input transposed. ARCKG signature: `grid_size_preserved=true`, `requires_content_diff=true`. Strict validation gate restricts to square grids whose output is exactly `transpose(input)` (transpose of HxW is WxH; if H != W, the validator's per-pair shape check rejects). Created `concepts/transpose_inplace.json` -- single `transpose` step, no parameters.

2. **Anti-diagonal mirror (size unchanged on square grids).** Output = input reflected along the top-right to bottom-left diagonal. Composition: `transpose` then `rotate_cw` 2 times (= rotate 180). Verified algebraically: `(r,c) -> (c,r) -> (n-1-c, n-1-r)` matches anti-diagonal mirror. Created `concepts/anti_diagonal_flip.json` -- two-step composition, no parameters.

**Quick validation:**
- `python run_task.py` (regression `08ed6ac7`) -> still INCORRECT (pre-existing across sessions 3, 5, 6, 7, 8, 9). Both new concepts get tried and rejected by the validator on this task, as expected.
- Concept loader picks up both new files: `[CONCEPT] Loaded 17 concepts` (up from 15).
- Direct execution check: `transpose_inplace` on `[[1,2,3],[4,5,6],[7,8,9]]` -> `[[1,4,7],[2,5,8],[3,6,9]]`. `anti_diagonal_flip` on the same input -> `[[9,6,3],[8,5,2],[7,4,1]]`. Both correct.
- Sanity-check on non-square input: `transpose_inplace` on a 2x3 grid produces a 3x2 grid; the validation gate would catch the size mismatch against any non-transpose-shaped output.

**Notes for next session:**
- No expected gain on the next learn loop with the current 20-task sample -- none of the failing tasks are pure transpose / anti-diagonal flips. These two concepts complete the diagonal-axis symmetry family identified as a gap in session 9 and are coverage infrastructure for the broader training set.
- The geometric-symmetry concept family is now complete: 4 in-place flips (h/v/transpose/anti-transpose), 3 rotations (90 cw, 90 ccw, 180), 4 size-doubling mirrors (above/below/left/right), and 1 quadrant tile. Future symmetry concepts have nothing left to add without new primitives.
- The unaddressed failure categories are the same six families session 9 listed: per-object relocation, path-drawing between waypoints, inner-rectangle fill by inner-size, quadrant-grid sub-pattern shifts, tile-resolution synthesis, triangular row growth. Each one requires either (a) a step engine extension (loops over `extract_objects` results, "for each section" orchestrator), or (b) new structured-output infer methods (e.g., `size_to_color_map` consumable by a single recolor call). Those changes are larger than a per-session concept addition.
- 08ed6ac7 regression gate remains INCORRECT pre-existing.

---
## Learning Loop -- 2026-04-29 07:48

- Split: training, Tasks: 20
- Correct: 4 / 20 (20.0%)
- Rules: 4 -> 4 (+0 learned)
- Stored rule hits: 4
- Time: 58s
- Log: logs/learn_20260429_074727.log

### Session 11 reflections (2026-04-29)

**Failures inspected:** Picked `6e82a1ae` (per-object recoloring driven by component size) as the
target. Read its JSON: every training pair has a single non-bg color (5) on a black bg; each
4-connected component in the input has all its positions uniformly recolored in the output to
a value determined solely by the component's cell count. Across all 3 pairs the map is the
same: size 4 -> 1, size 3 -> 2, size 2 -> 3. Spot-checked `9f669b64`, `c0f76784`, `e9ac8c9e`,
`0e206a2e`, `13f06aa5`, `afe3afe9`, `bbc9ae5d` to make sure the size->color hypothesis is
specific (those are different patterns: rectangle-pair swap, frame-fill by inner size,
quadrant fill, cross relocation, boundary marker overlay, 2D pattern lookup, triangular row
growth respectively -- none reduce to size-driven recoloring).

**Strategy: per-component size->color recolor.** Until now the engine could only express
operations that compose primitives over a whole grid; per-object behavior required either
unrolled steps (hopeless) or new primitives (frozen). The escape hatch already in the engine
is the dynamic-sentinel mechanism used by `concentric_ring_reversal` / `<RING_REVERSAL>`: a
parameter value resolved per-input at execute time, computed from `input_grid_raw`. I extended
that mechanism to a new sentinel kind so concepts can return a per-input output grid built
from extracted objects.

**Implementation:**
1. `procedural_memory/base_rules/_concept_engine.py`:
   - Added `_size_color_map_for_pair(g_in, g_out, bg)` -- validates one pair: every non-bg
     component's positions in g_out are uniform, bg cells unchanged, returns
     `{size: out_color}` or None.
   - Added infer method `size_to_color_map_objects` -- requires `size_comm=True`, infers a bg
     consistent across all training pairs, merges per-pair size->color maps, and on success
     returns a typed sentinel dict `{"_kind": "recolor_by_size", "map": {...}, "bg": bg}`.
   - Added helper `_apply_recolor_by_size(grid, size_map, bg)` -- detects components in the
     input, recolors each by its size, returns None if any component has an unknown size.
   - Plumbed a new branch in `_execute_concept`'s sentinel-resolution loop: when a parameter
     value is a dict with `_kind == "recolor_by_size"`, replace it with the input-specific
     output grid before `env.update(resolved_params)`. Same shape as the existing
     `<RING_REVERSAL>` path.
2. `procedural_memory/concepts/recolor_objects_by_size.json` -- signature is the loose
   `grid_size_preserved=true` + `requires_content_diff=true` filter (validation does the heavy
   work). Single parameter `out_grid` infers via the new method; `steps: []`; `result:
   "$out_grid"`. This is the first concept whose result comes wholly from a sentinel
   resolution rather than primitive composition.

**Validation:**
- Direct unit test: `_size_color_map_for_pair` on each of `6e82a1ae`'s 3 training pairs returns
  `{4:1, 3:2, 2:3}` (consistent). `_apply_recolor_by_size` on the test input matches the
  expected output exactly.
- End-to-end via `try_concepts` on `6e82a1ae`: anti_diagonal_flip / flip_h / flip_v fail
  validation, ring_reversal / global_recolor / preserve_single_column return None on infer,
  then `recolor_objects_by_size` MATCHES with params `{'out_grid': {'_kind':
  'recolor_by_size', 'map': {4: 1, 3: 2, 2: 3}, 'bg': 0}}` and `apply_concept` on the test
  pair produces the correct output.
- False-positive sweep: ran `try_concepts` on all 16 currently-failing tasks. The new concept
  matches exactly one (`6e82a1ae`); the other 15 still return None. No collateral.
- Regression on existing concepts: `concentric_ring_reversal` still matches `85c4e7cd` via its
  own sentinel path (verified directly). My changes are purely additive (one new infer, one
  new helper, one new dict-typed sentinel branch) so the existing 17 concepts and 4 stored
  rules are untouched.
- `run_task.py` (regression `08ed6ac7`) -> INCORRECT (pre-existing across sessions 3, 5-10).
- Concept loader: `[CONCEPT] Loaded 18 concepts` (up from 17).

**Notes for next session:**
- Expected gain on the next learn loop: 6e82a1ae moves from FAIL to OK (5/20, 25%). It will
  also be saved as a stored rule, becoming a future memory hit.
- The dict-typed sentinel mechanism opens a clean path for other per-object operations that
  previously required step-engine extensions: the infer method does the cross-pair invariant
  search, returns a typed payload, and the engine's sentinel resolver applies it per-input.
  Future concepts that fit this shape: per-object color->color (when size isn't the key but
  e.g., position or shape is), per-section recoloring once a section enumerator exists.
- The strategy specifically did NOT solve the still-open categories: per-object relocation
  (`0e206a2e`, `e9ac8c9e`), inner-size-driven frame fill (`c0f76784`), triangular row growth
  (`bbc9ae5d`), 2D pattern lookup (`afe3afe9`), section/quadrant-grid recoloring
  (`332202d5`, `825aa9e9`, `1c56ad9f`). Each still needs either a different sentinel kind or
  a new infer method.
- 08ed6ac7 regression gate remains INCORRECT pre-existing.

---
## Learning Loop -- 2026-04-29 07:59

- Split: training, Tasks: 20
- Correct: 4 / 20 (20.0%)
- Rules: 4 -> 4 (+0 learned)
- Stored rule hits: 4
- Time: 43s
- Log: logs/learn_20260429_075822.log

---
## Learning Loop -- 2026-04-29 08:09

- Split: training, Tasks: 20
- Correct: 6 / 20 (30.0%)
- Rules: 4 -> 6 (+2 learned)
- Stored rule hits: 4
- Time: 43s
- Log: logs/learn_20260429_080913.log

---
## Learning Loop -- 2026-04-29 08:10

- Split: training, Tasks: 20
- Correct: 6 / 20 (30.0%)
- Rules: 6 -> 6 (+0 learned)
- Stored rule hits: 6
- Time: 42s
- Log: logs/learn_20260429_081004.log

---
## Learning Loop -- 2026-04-29 08:11

- Split: training, Tasks: 20
- Correct: 6 / 20 (30.0%)
- Rules: 6 -> 6 (+0 learned)
- Stored rule hits: 6
- Time: 42s
- Log: logs/learn_20260429_081055.log

---
## Learning Loop -- 2026-04-29 08:12

- Split: training, Tasks: 20
- Correct: 6 / 20 (30.0%)
- Rules: 6 -> 6 (+0 learned)
- Stored rule hits: 6
- Time: 42s
- Log: logs/learn_20260429_081147.log

---
## Learning Loop -- 2026-04-29 08:13

- Split: training, Tasks: 20
- Correct: 6 / 20 (30.0%)
- Rules: 6 -> 6 (+0 learned)
- Stored rule hits: 6
- Time: 43s
- Log: logs/learn_20260429_081238.log

---
## Learning Loop -- 2026-04-29 08:14

- Split: training, Tasks: 20
- Correct: 6 / 20 (30.0%)
- Rules: 6 -> 6 (+0 learned)
- Stored rule hits: 6
- Time: 42s
- Log: logs/learn_20260429_081329.log

---
## Learning Loop -- 2026-04-29 08:15

- Split: training, Tasks: 20
- Correct: 6 / 20 (30.0%)
- Rules: 6 -> 6 (+0 learned)
- Stored rule hits: 6
- Time: 42s
- Log: logs/learn_20260429_081420.log

---
## Learning Loop -- 2026-04-29 08:15

- Split: training, Tasks: 20
- Correct: 6 / 20 (30.0%)
- Rules: 6 -> 6 (+0 learned)
- Stored rule hits: 6
- Time: 42s
- Log: logs/learn_20260429_081511.log

---
## Learning Loop -- 2026-04-29 08:16

- Split: training, Tasks: 20
- Correct: 6 / 20 (30.0%)
- Rules: 6 -> 6 (+0 learned)
- Stored rule hits: 6
- Time: 43s
- Log: logs/learn_20260429_081602.log

---
## Learning Loop -- 2026-04-29 08:17

- Split: training, Tasks: 20
- Correct: 6 / 20 (30.0%)
- Rules: 6 -> 6 (+0 learned)
- Stored rule hits: 6
- Time: 42s
- Log: logs/learn_20260429_081653.log

---
## Learning Loop -- 2026-04-29 08:18

- Split: training, Tasks: 20
- Correct: 6 / 20 (30.0%)
- Rules: 6 -> 6 (+0 learned)
- Stored rule hits: 6
- Time: 42s
- Log: logs/learn_20260429_081745.log

---
## Learning Loop -- 2026-04-29 08:19

- Split: training, Tasks: 20
- Correct: 6 / 20 (30.0%)
- Rules: 6 -> 6 (+0 learned)
- Stored rule hits: 6
- Time: 43s
- Log: logs/learn_20260429_081836.log

---
## Learning Loop -- 2026-04-29 08:20

- Split: training, Tasks: 20
- Correct: 6 / 20 (30.0%)
- Rules: 6 -> 6 (+0 learned)
- Stored rule hits: 6
- Time: 44s
- Log: logs/learn_20260429_081928.log

---
## Learning Loop -- 2026-04-29 08:21

- Split: training, Tasks: 20
- Correct: 6 / 20 (30.0%)
- Rules: 6 -> 6 (+0 learned)
- Stored rule hits: 6
- Time: 43s
- Log: logs/learn_20260429_082020.log

---
## Learning Loop -- 2026-04-29 08:21

- Split: training, Tasks: 20
- Correct: 6 / 20 (30.0%)
- Rules: 6 -> 6 (+0 learned)
- Stored rule hits: 6
- Time: 43s
- Log: logs/learn_20260429_082112.log

---
## Learning Loop -- 2026-04-29 08:22

- Split: training, Tasks: 20
- Correct: 6 / 20 (30.0%)
- Rules: 6 -> 6 (+0 learned)
- Stored rule hits: 6
- Time: 42s
- Log: logs/learn_20260429_082204.log

---
## Learning Loop -- 2026-04-29 08:23

- Split: training, Tasks: 20
- Correct: 6 / 20 (30.0%)
- Rules: 6 -> 6 (+0 learned)
- Stored rule hits: 6
- Time: 42s
- Log: logs/learn_20260429_082255.log

---
## Learning Loop -- 2026-04-29 08:24

- Split: training, Tasks: 20
- Correct: 6 / 20 (30.0%)
- Rules: 6 -> 6 (+0 learned)
- Stored rule hits: 6
- Time: 43s
- Log: logs/learn_20260429_082346.log

---
## Learning Loop -- 2026-04-29 08:25

- Split: training, Tasks: 20
- Correct: 6 / 20 (30.0%)
- Rules: 6 -> 6 (+0 learned)
- Stored rule hits: 6
- Time: 42s
- Log: logs/learn_20260429_082437.log

---
## Learning Loop -- 2026-04-29 08:26

- Split: training, Tasks: 20
- Correct: 6 / 20 (30.0%)
- Rules: 6 -> 6 (+0 learned)
- Stored rule hits: 6
- Time: 42s
- Log: logs/learn_20260429_082528.log

---
## Learning Loop -- 2026-04-29 08:27

- Split: training, Tasks: 20
- Correct: 6 / 20 (30.0%)
- Rules: 6 -> 6 (+0 learned)
- Stored rule hits: 6
- Time: 42s
- Log: logs/learn_20260429_082619.log

---
## Learning Loop -- 2026-04-29 08:27

- Split: training, Tasks: 20
- Correct: 6 / 20 (30.0%)
- Rules: 6 -> 6 (+0 learned)
- Stored rule hits: 6
- Time: 42s
- Log: logs/learn_20260429_082710.log

---
## Learning Loop -- 2026-04-29 08:28

- Split: training, Tasks: 20
- Correct: 6 / 20 (30.0%)
- Rules: 6 -> 6 (+0 learned)
- Stored rule hits: 6
- Time: 42s
- Log: logs/learn_20260429_082801.log

---
## Learning Loop -- 2026-04-29 08:29

- Split: training, Tasks: 20
- Correct: 6 / 20 (30.0%)
- Rules: 6 -> 6 (+0 learned)
- Stored rule hits: 6
- Time: 42s
- Log: logs/learn_20260429_082852.log

---
## Learning Loop -- 2026-04-29 08:30

- Split: training, Tasks: 20
- Correct: 6 / 20 (30.0%)
- Rules: 6 -> 6 (+0 learned)
- Stored rule hits: 6
- Time: 42s
- Log: logs/learn_20260429_082943.log

---
## Learning Loop -- 2026-04-29 08:31

- Split: training, Tasks: 20
- Correct: 6 / 20 (30.0%)
- Rules: 6 -> 6 (+0 learned)
- Stored rule hits: 6
- Time: 43s
- Log: logs/learn_20260429_083034.log

---
## Learning Loop -- 2026-04-29 08:32

- Split: training, Tasks: 20
- Correct: 6 / 20 (30.0%)
- Rules: 6 -> 6 (+0 learned)
- Stored rule hits: 6
- Time: 42s
- Log: logs/learn_20260429_083125.log

---
## Learning Loop -- 2026-04-29 08:33

- Split: training, Tasks: 20
- Correct: 6 / 20 (30.0%)
- Rules: 6 -> 6 (+0 learned)
- Stored rule hits: 6
- Time: 44s
- Log: logs/learn_20260429_083216.log

---
## Learning Loop -- 2026-04-29 08:33

- Split: training, Tasks: 20
- Correct: 6 / 20 (30.0%)
- Rules: 6 -> 6 (+0 learned)
- Stored rule hits: 6
- Time: 43s
- Log: logs/learn_20260429_083309.log

---
## Learning Loop -- 2026-04-29 08:34

- Split: training, Tasks: 20
- Correct: 6 / 20 (30.0%)
- Rules: 6 -> 6 (+0 learned)
- Stored rule hits: 6
- Time: 42s
- Log: logs/learn_20260429_083401.log

---
## Learning Loop -- 2026-04-29 08:35

- Split: training, Tasks: 20
- Correct: 6 / 20 (30.0%)
- Rules: 6 -> 6 (+0 learned)
- Stored rule hits: 6
- Time: 42s
- Log: logs/learn_20260429_083452.log

---
## Learning Loop -- 2026-04-29 08:36

- Split: training, Tasks: 20
- Correct: 6 / 20 (30.0%)
- Rules: 6 -> 6 (+0 learned)
- Stored rule hits: 6
- Time: 42s
- Log: logs/learn_20260429_083543.log

---
## Learning Loop -- 2026-04-29 08:37

- Split: training, Tasks: 20
- Correct: 6 / 20 (30.0%)
- Rules: 6 -> 6 (+0 learned)
- Stored rule hits: 6
- Time: 42s
- Log: logs/learn_20260429_083634.log

---
## Learning Loop -- 2026-04-29 08:38

- Split: training, Tasks: 20
- Correct: 6 / 20 (30.0%)
- Rules: 6 -> 6 (+0 learned)
- Stored rule hits: 6
- Time: 42s
- Log: logs/learn_20260429_083724.log

---
## Learning Loop -- 2026-04-29 08:38

- Split: training, Tasks: 20
- Correct: 6 / 20 (30.0%)
- Rules: 6 -> 6 (+0 learned)
- Stored rule hits: 6
- Time: 42s
- Log: logs/learn_20260429_083815.log

---
## Learning Loop -- 2026-04-29 08:39

- Split: training, Tasks: 20
- Correct: 6 / 20 (30.0%)
- Rules: 6 -> 6 (+0 learned)
- Stored rule hits: 6
- Time: 42s
- Log: logs/learn_20260429_083907.log

---
## Learning Loop -- 2026-04-29 08:40

- Split: training, Tasks: 20
- Correct: 6 / 20 (30.0%)
- Rules: 6 -> 6 (+0 learned)
- Stored rule hits: 6
- Time: 42s
- Log: logs/learn_20260429_083958.log

---
## Learning Loop -- 2026-04-29 08:41

- Split: training, Tasks: 20
- Correct: 6 / 20 (30.0%)
- Rules: 6 -> 6 (+0 learned)
- Stored rule hits: 6
- Time: 43s
- Log: logs/learn_20260429_084049.log

---
## Learning Loop -- 2026-04-29 08:42

- Split: training, Tasks: 20
- Correct: 6 / 20 (30.0%)
- Rules: 6 -> 6 (+0 learned)
- Stored rule hits: 6
- Time: 42s
- Log: logs/learn_20260429_084140.log

---
## Learning Loop -- 2026-04-29 08:43

- Split: training, Tasks: 20
- Correct: 6 / 20 (30.0%)
- Rules: 6 -> 6 (+0 learned)
- Stored rule hits: 6
- Time: 42s
- Log: logs/learn_20260429_084231.log

---
## Learning Loop -- 2026-04-29 08:44

- Split: training, Tasks: 20
- Correct: 6 / 20 (30.0%)
- Rules: 6 -> 6 (+0 learned)
- Stored rule hits: 6
- Time: 42s
- Log: logs/learn_20260429_084322.log

---
## Learning Loop -- 2026-04-29 08:44

- Split: training, Tasks: 20
- Correct: 6 / 20 (30.0%)
- Rules: 6 -> 6 (+0 learned)
- Stored rule hits: 6
- Time: 42s
- Log: logs/learn_20260429_084413.log

---
## Learning Loop -- 2026-04-29 08:45

- Split: training, Tasks: 20
- Correct: 6 / 20 (30.0%)
- Rules: 6 -> 6 (+0 learned)
- Stored rule hits: 6
- Time: 42s
- Log: logs/learn_20260429_084504.log

---
## Learning Loop -- 2026-04-29 08:46

- Split: training, Tasks: 20
- Correct: 6 / 20 (30.0%)
- Rules: 6 -> 6 (+0 learned)
- Stored rule hits: 6
- Time: 42s
- Log: logs/learn_20260429_084555.log

---
## Learning Loop -- 2026-04-29 08:47

- Split: training, Tasks: 20
- Correct: 6 / 20 (30.0%)
- Rules: 6 -> 6 (+0 learned)
- Stored rule hits: 6
- Time: 42s
- Log: logs/learn_20260429_084646.log

---
## Learning Loop -- 2026-04-29 08:48

- Split: training, Tasks: 20
- Correct: 6 / 20 (30.0%)
- Rules: 6 -> 6 (+0 learned)
- Stored rule hits: 6
- Time: 43s
- Log: logs/learn_20260429_084737.log

---
## Learning Loop -- 2026-04-29 08:49

- Split: training, Tasks: 20
- Correct: 6 / 20 (30.0%)
- Rules: 6 -> 6 (+0 learned)
- Stored rule hits: 6
- Time: 42s
- Log: logs/learn_20260429_084828.log

---
## Learning Loop -- 2026-04-29 08:50

- Split: training, Tasks: 20
- Correct: 6 / 20 (30.0%)
- Rules: 6 -> 6 (+0 learned)
- Stored rule hits: 6
- Time: 42s
- Log: logs/learn_20260429_084919.log

---
## Learning Loop -- 2026-04-29 08:50

- Split: training, Tasks: 20
- Correct: 6 / 20 (30.0%)
- Rules: 6 -> 6 (+0 learned)
- Stored rule hits: 6
- Time: 43s
- Log: logs/learn_20260429_085010.log

---
## Learning Loop -- 2026-04-29 08:51

- Split: training, Tasks: 20
- Correct: 6 / 20 (30.0%)
- Rules: 6 -> 6 (+0 learned)
- Stored rule hits: 6
- Time: 43s
- Log: logs/learn_20260429_085101.log

---
## Learning Loop -- 2026-04-29 08:52

- Split: training, Tasks: 20
- Correct: 6 / 20 (30.0%)
- Rules: 6 -> 6 (+0 learned)
- Stored rule hits: 6
- Time: 42s
- Log: logs/learn_20260429_085153.log

---
## Learning Loop -- 2026-04-29 08:53

- Split: training, Tasks: 20
- Correct: 6 / 20 (30.0%)
- Rules: 6 -> 6 (+0 learned)
- Stored rule hits: 6
- Time: 42s
- Log: logs/learn_20260429_085244.log

---
## Learning Loop -- 2026-04-29 08:54

- Split: training, Tasks: 20
- Correct: 6 / 20 (30.0%)
- Rules: 6 -> 6 (+0 learned)
- Stored rule hits: 6
- Time: 42s
- Log: logs/learn_20260429_085335.log

---
## Learning Loop -- 2026-04-29 08:55

- Split: training, Tasks: 20
- Correct: 6 / 20 (30.0%)
- Rules: 6 -> 6 (+0 learned)
- Stored rule hits: 6
- Time: 42s
- Log: logs/learn_20260429_085426.log

---
## Learning Loop -- 2026-04-29 08:55

- Split: training, Tasks: 20
- Correct: 6 / 20 (30.0%)
- Rules: 6 -> 6 (+0 learned)
- Stored rule hits: 6
- Time: 42s
- Log: logs/learn_20260429_085517.log

---
## Learning Loop -- 2026-04-29 08:56

- Split: training, Tasks: 20
- Correct: 6 / 20 (30.0%)
- Rules: 6 -> 6 (+0 learned)
- Stored rule hits: 6
- Time: 42s
- Log: logs/learn_20260429_085608.log

---
## Learning Loop -- 2026-04-29 08:57

- Split: training, Tasks: 20
- Correct: 6 / 20 (30.0%)
- Rules: 6 -> 6 (+0 learned)
- Stored rule hits: 6
- Time: 43s
- Log: logs/learn_20260429_085659.log

---
## Learning Loop -- 2026-04-29 08:58

- Split: training, Tasks: 20
- Correct: 6 / 20 (30.0%)
- Rules: 6 -> 6 (+0 learned)
- Stored rule hits: 6
- Time: 43s
- Log: logs/learn_20260429_085751.log

---
## Learning Loop -- 2026-04-29 08:59

- Split: training, Tasks: 20
- Correct: 6 / 20 (30.0%)
- Rules: 6 -> 6 (+0 learned)
- Stored rule hits: 6
- Time: 42s
- Log: logs/learn_20260429_085842.log

---
## Learning Loop -- 2026-04-29 09:00

- Split: training, Tasks: 20
- Correct: 6 / 20 (30.0%)
- Rules: 6 -> 6 (+0 learned)
- Stored rule hits: 6
- Time: 42s
- Log: logs/learn_20260429_085933.log

---
## Learning Loop -- 2026-04-29 09:01

- Split: training, Tasks: 20
- Correct: 6 / 20 (30.0%)
- Rules: 6 -> 6 (+0 learned)
- Stored rule hits: 6
- Time: 42s
- Log: logs/learn_20260429_090024.log

---
## Learning Loop -- 2026-04-29 09:02

- Split: training, Tasks: 20
- Correct: 6 / 20 (30.0%)
- Rules: 6 -> 6 (+0 learned)
- Stored rule hits: 6
- Time: 45s
- Log: logs/learn_20260429_090115.log

---
## Learning Loop -- 2026-04-29 09:03

- Split: training, Tasks: 20
- Correct: 6 / 20 (30.0%)
- Rules: 6 -> 6 (+0 learned)
- Stored rule hits: 6
- Time: 51s
- Log: logs/learn_20260429_090209.log

---
## Learning Loop -- 2026-04-29 09:03

- Split: training, Tasks: 20
- Correct: 6 / 20 (30.0%)
- Rules: 6 -> 6 (+0 learned)
- Stored rule hits: 6
- Time: 45s
- Log: logs/learn_20260429_090310.log

---
## Learning Loop -- 2026-04-29 09:04

- Split: training, Tasks: 20
- Correct: 6 / 20 (30.0%)
- Rules: 6 -> 6 (+0 learned)
- Stored rule hits: 6
- Time: 44s
- Log: logs/learn_20260429_090403.log

---
## Learning Loop -- 2026-04-29 09:05

- Split: training, Tasks: 20
- Correct: 6 / 20 (30.0%)
- Rules: 6 -> 6 (+0 learned)
- Stored rule hits: 6
- Time: 44s
- Log: logs/learn_20260429_090456.log

---
## Learning Loop -- 2026-04-29 09:06

- Split: training, Tasks: 20
- Correct: 6 / 20 (30.0%)
- Rules: 6 -> 6 (+0 learned)
- Stored rule hits: 6
- Time: 44s
- Log: logs/learn_20260429_090549.log

---
## Learning Loop -- 2026-04-29 09:07

- Split: training, Tasks: 20
- Correct: 6 / 20 (30.0%)
- Rules: 6 -> 6 (+0 learned)
- Stored rule hits: 6
- Time: 44s
- Log: logs/learn_20260429_090642.log

---
## Learning Loop -- 2026-04-29 09:08

- Split: training, Tasks: 20
- Correct: 6 / 20 (30.0%)
- Rules: 6 -> 6 (+0 learned)
- Stored rule hits: 6
- Time: 44s
- Log: logs/learn_20260429_090735.log

---
## Learning Loop -- 2026-04-29 09:09

- Split: training, Tasks: 20
- Correct: 6 / 20 (30.0%)
- Rules: 6 -> 6 (+0 learned)
- Stored rule hits: 6
- Time: 44s
- Log: logs/learn_20260429_090828.log

---
## Learning Loop -- 2026-04-29 09:10

- Split: training, Tasks: 20
- Correct: 6 / 20 (30.0%)
- Rules: 6 -> 6 (+0 learned)
- Stored rule hits: 6
- Time: 44s
- Log: logs/learn_20260429_090921.log

---
## Learning Loop -- 2026-04-29 09:10

- Split: training, Tasks: 20
- Correct: 6 / 20 (30.0%)
- Rules: 6 -> 6 (+0 learned)
- Stored rule hits: 6
- Time: 44s
- Log: logs/learn_20260429_091013.log

---
## Learning Loop -- 2026-04-29 09:11

- Split: training, Tasks: 20
- Correct: 6 / 20 (30.0%)
- Rules: 6 -> 6 (+0 learned)
- Stored rule hits: 6
- Time: 45s
- Log: logs/learn_20260429_091106.log

---
## Learning Loop -- 2026-04-29 09:12

- Split: training, Tasks: 20
- Correct: 6 / 20 (30.0%)
- Rules: 6 -> 6 (+0 learned)
- Stored rule hits: 6
- Time: 44s
- Log: logs/learn_20260429_091159.log

---
## Learning Loop -- 2026-04-29 09:13

- Split: training, Tasks: 20
- Correct: 6 / 20 (30.0%)
- Rules: 6 -> 6 (+0 learned)
- Stored rule hits: 6
- Time: 44s
- Log: logs/learn_20260429_091252.log

---
## Learning Loop -- 2026-04-29 09:14

- Split: training, Tasks: 20
- Correct: 6 / 20 (30.0%)
- Rules: 6 -> 6 (+0 learned)
- Stored rule hits: 6
- Time: 44s
- Log: logs/learn_20260429_091345.log

---
## Learning Loop -- 2026-04-29 09:15

- Split: training, Tasks: 20
- Correct: 6 / 20 (30.0%)
- Rules: 6 -> 6 (+0 learned)
- Stored rule hits: 6
- Time: 44s
- Log: logs/learn_20260429_091437.log

---
## Learning Loop -- 2026-04-29 09:16

- Split: training, Tasks: 20
- Correct: 6 / 20 (30.0%)
- Rules: 6 -> 6 (+0 learned)
- Stored rule hits: 6
- Time: 44s
- Log: logs/learn_20260429_091530.log

---
## Learning Loop -- 2026-04-29 09:17

- Split: training, Tasks: 20
- Correct: 6 / 20 (30.0%)
- Rules: 6 -> 6 (+0 learned)
- Stored rule hits: 6
- Time: 44s
- Log: logs/learn_20260429_091623.log

---
## Learning Loop -- 2026-04-29 09:18

- Split: training, Tasks: 20
- Correct: 6 / 20 (30.0%)
- Rules: 6 -> 6 (+0 learned)
- Stored rule hits: 6
- Time: 44s
- Log: logs/learn_20260429_091716.log

---
## Learning Loop -- 2026-04-29 09:18

- Split: training, Tasks: 20
- Correct: 6 / 20 (30.0%)
- Rules: 6 -> 6 (+0 learned)
- Stored rule hits: 6
- Time: 44s
- Log: logs/learn_20260429_091809.log

---
## Learning Loop -- 2026-04-29 09:19

- Split: training, Tasks: 20
- Correct: 6 / 20 (30.0%)
- Rules: 6 -> 6 (+0 learned)
- Stored rule hits: 6
- Time: 44s
- Log: logs/learn_20260429_091901.log

---
## Learning Loop -- 2026-04-29 09:20

- Split: training, Tasks: 20
- Correct: 6 / 20 (30.0%)
- Rules: 6 -> 6 (+0 learned)
- Stored rule hits: 6
- Time: 44s
- Log: logs/learn_20260429_091953.log

---
## Learning Loop -- 2026-04-29 09:21

- Split: training, Tasks: 20
- Correct: 6 / 20 (30.0%)
- Rules: 6 -> 6 (+0 learned)
- Stored rule hits: 6
- Time: 44s
- Log: logs/learn_20260429_092046.log

---
## Learning Loop -- 2026-04-29 09:22

- Split: training, Tasks: 20
- Correct: 6 / 20 (30.0%)
- Rules: 6 -> 6 (+0 learned)
- Stored rule hits: 6
- Time: 44s
- Log: logs/learn_20260429_092139.log

---
## Learning Loop -- 2026-04-29 09:23

- Split: training, Tasks: 20
- Correct: 6 / 20 (30.0%)
- Rules: 6 -> 6 (+0 learned)
- Stored rule hits: 6
- Time: 44s
- Log: logs/learn_20260429_092233.log

---
## Learning Loop -- 2026-04-29 09:24

- Split: training, Tasks: 20
- Correct: 6 / 20 (30.0%)
- Rules: 6 -> 6 (+0 learned)
- Stored rule hits: 6
- Time: 44s
- Log: logs/learn_20260429_092325.log

---
## Learning Loop -- 2026-04-29 09:25

- Split: training, Tasks: 20
- Correct: 6 / 20 (30.0%)
- Rules: 6 -> 6 (+0 learned)
- Stored rule hits: 6
- Time: 44s
- Log: logs/learn_20260429_092418.log

---
## Learning Loop -- 2026-04-29 09:25

- Split: training, Tasks: 20
- Correct: 6 / 20 (30.0%)
- Rules: 6 -> 6 (+0 learned)
- Stored rule hits: 6
- Time: 44s
- Log: logs/learn_20260429_092511.log

---
## Learning Loop -- 2026-04-29 09:26

- Split: training, Tasks: 20
- Correct: 6 / 20 (30.0%)
- Rules: 6 -> 6 (+0 learned)
- Stored rule hits: 6
- Time: 44s
- Log: logs/learn_20260429_092604.log

---
## Learning Loop -- 2026-04-29 09:27

- Split: training, Tasks: 20
- Correct: 6 / 20 (30.0%)
- Rules: 6 -> 6 (+0 learned)
- Stored rule hits: 6
- Time: 44s
- Log: logs/learn_20260429_092657.log

---
## Learning Loop -- 2026-04-29 09:28

- Split: training, Tasks: 20
- Correct: 6 / 20 (30.0%)
- Rules: 6 -> 6 (+0 learned)
- Stored rule hits: 6
- Time: 44s
- Log: logs/learn_20260429_092750.log

---
## Learning Loop -- 2026-04-29 09:29

- Split: training, Tasks: 20
- Correct: 6 / 20 (30.0%)
- Rules: 6 -> 6 (+0 learned)
- Stored rule hits: 6
- Time: 44s
- Log: logs/learn_20260429_092842.log

---
## Learning Loop -- 2026-04-29 09:30

- Split: training, Tasks: 20
- Correct: 6 / 20 (30.0%)
- Rules: 6 -> 6 (+0 learned)
- Stored rule hits: 6
- Time: 44s
- Log: logs/learn_20260429_092935.log

---
## Learning Loop -- 2026-04-29 09:31

- Split: training, Tasks: 20
- Correct: 6 / 20 (30.0%)
- Rules: 6 -> 6 (+0 learned)
- Stored rule hits: 6
- Time: 44s
- Log: logs/learn_20260429_093028.log

---
## Learning Loop -- 2026-04-29 09:32

- Split: training, Tasks: 20
- Correct: 6 / 20 (30.0%)
- Rules: 6 -> 6 (+0 learned)
- Stored rule hits: 6
- Time: 45s
- Log: logs/learn_20260429_093120.log

---
## Learning Loop -- 2026-04-29 09:32

- Split: training, Tasks: 20
- Correct: 6 / 20 (30.0%)
- Rules: 6 -> 6 (+0 learned)
- Stored rule hits: 6
- Time: 45s
- Log: logs/learn_20260429_093214.log

---
## Learning Loop -- 2026-04-29 09:33

- Split: training, Tasks: 20
- Correct: 6 / 20 (30.0%)
- Rules: 6 -> 6 (+0 learned)
- Stored rule hits: 6
- Time: 44s
- Log: logs/learn_20260429_093309.log

---
## Learning Loop -- 2026-04-29 09:34

- Split: training, Tasks: 20
- Correct: 6 / 20 (30.0%)
- Rules: 6 -> 6 (+0 learned)
- Stored rule hits: 6
- Time: 44s
- Log: logs/learn_20260429_093402.log

---
## Learning Loop -- 2026-04-29 09:35

- Split: training, Tasks: 20
- Correct: 6 / 20 (30.0%)
- Rules: 6 -> 6 (+0 learned)
- Stored rule hits: 6
- Time: 44s
- Log: logs/learn_20260429_093455.log

---
## Learning Loop -- 2026-04-29 09:36

- Split: training, Tasks: 20
- Correct: 6 / 20 (30.0%)
- Rules: 6 -> 6 (+0 learned)
- Stored rule hits: 6
- Time: 44s
- Log: logs/learn_20260429_093547.log

---
## Learning Loop -- 2026-04-29 09:37

- Split: training, Tasks: 20
- Correct: 6 / 20 (30.0%)
- Rules: 6 -> 6 (+0 learned)
- Stored rule hits: 6
- Time: 44s
- Log: logs/learn_20260429_093640.log

---
## Learning Loop -- 2026-04-29 09:38

- Split: training, Tasks: 20
- Correct: 6 / 20 (30.0%)
- Rules: 6 -> 6 (+0 learned)
- Stored rule hits: 6
- Time: 44s
- Log: logs/learn_20260429_093733.log

---
## Learning Loop -- 2026-04-29 09:39

- Split: training, Tasks: 20
- Correct: 6 / 20 (30.0%)
- Rules: 6 -> 6 (+0 learned)
- Stored rule hits: 6
- Time: 44s
- Log: logs/learn_20260429_093826.log

---
## Learning Loop -- 2026-04-29 09:40

- Split: training, Tasks: 20
- Correct: 6 / 20 (30.0%)
- Rules: 6 -> 6 (+0 learned)
- Stored rule hits: 6
- Time: 44s
- Log: logs/learn_20260429_093919.log

---
## Learning Loop -- 2026-04-29 09:40

- Split: training, Tasks: 20
- Correct: 6 / 20 (30.0%)
- Rules: 6 -> 6 (+0 learned)
- Stored rule hits: 6
- Time: 44s
- Log: logs/learn_20260429_094011.log

---
## Learning Loop -- 2026-04-29 09:41

- Split: training, Tasks: 20
- Correct: 6 / 20 (30.0%)
- Rules: 6 -> 6 (+0 learned)
- Stored rule hits: 6
- Time: 44s
- Log: logs/learn_20260429_094104.log

---
## Learning Loop -- 2026-04-29 09:42

- Split: training, Tasks: 20
- Correct: 6 / 20 (30.0%)
- Rules: 6 -> 6 (+0 learned)
- Stored rule hits: 6
- Time: 44s
- Log: logs/learn_20260429_094157.log

---
## Learning Loop -- 2026-04-29 09:43

- Split: training, Tasks: 20
- Correct: 6 / 20 (30.0%)
- Rules: 6 -> 6 (+0 learned)
- Stored rule hits: 6
- Time: 44s
- Log: logs/learn_20260429_094249.log

---
## Learning Loop -- 2026-04-29 09:44

- Split: training, Tasks: 20
- Correct: 6 / 20 (30.0%)
- Rules: 6 -> 6 (+0 learned)
- Stored rule hits: 6
- Time: 44s
- Log: logs/learn_20260429_094342.log

---
## Learning Loop -- 2026-04-29 09:45

- Split: training, Tasks: 20
- Correct: 6 / 20 (30.0%)
- Rules: 6 -> 6 (+0 learned)
- Stored rule hits: 6
- Time: 44s
- Log: logs/learn_20260429_094435.log

---
## Learning Loop -- 2026-04-29 09:46

- Split: training, Tasks: 20
- Correct: 6 / 20 (30.0%)
- Rules: 6 -> 6 (+0 learned)
- Stored rule hits: 6
- Time: 44s
- Log: logs/learn_20260429_094529.log

---
## Learning Loop -- 2026-04-29 09:47

- Split: training, Tasks: 20
- Correct: 6 / 20 (30.0%)
- Rules: 6 -> 6 (+0 learned)
- Stored rule hits: 6
- Time: 44s
- Log: logs/learn_20260429_094622.log

---
## Learning Loop -- 2026-04-29 09:47

- Split: training, Tasks: 20
- Correct: 6 / 20 (30.0%)
- Rules: 6 -> 6 (+0 learned)
- Stored rule hits: 6
- Time: 44s
- Log: logs/learn_20260429_094714.log

---
## Learning Loop -- 2026-04-29 09:48

- Split: training, Tasks: 20
- Correct: 6 / 20 (30.0%)
- Rules: 6 -> 6 (+0 learned)
- Stored rule hits: 6
- Time: 44s
- Log: logs/learn_20260429_094807.log

---
## Learning Loop -- 2026-04-29 09:49

- Split: training, Tasks: 20
- Correct: 6 / 20 (30.0%)
- Rules: 6 -> 6 (+0 learned)
- Stored rule hits: 6
- Time: 44s
- Log: logs/learn_20260429_094900.log

---
## Learning Loop -- 2026-04-29 09:50

- Split: training, Tasks: 20
- Correct: 6 / 20 (30.0%)
- Rules: 6 -> 6 (+0 learned)
- Stored rule hits: 6
- Time: 44s
- Log: logs/learn_20260429_094953.log

---
## Learning Loop -- 2026-04-29 09:51

- Split: training, Tasks: 20
- Correct: 6 / 20 (30.0%)
- Rules: 6 -> 6 (+0 learned)
- Stored rule hits: 6
- Time: 45s
- Log: logs/learn_20260429_095046.log

---
## Learning Loop -- 2026-04-29 09:52

- Split: training, Tasks: 20
- Correct: 6 / 20 (30.0%)
- Rules: 6 -> 6 (+0 learned)
- Stored rule hits: 6
- Time: 44s
- Log: logs/learn_20260429_095140.log

---
## Learning Loop -- 2026-04-29 09:53

- Split: training, Tasks: 20
- Correct: 6 / 20 (30.0%)
- Rules: 6 -> 6 (+0 learned)
- Stored rule hits: 6
- Time: 44s
- Log: logs/learn_20260429_095233.log

---
## Learning Loop -- 2026-04-29 09:54

- Split: training, Tasks: 20
- Correct: 6 / 20 (30.0%)
- Rules: 6 -> 6 (+0 learned)
- Stored rule hits: 6
- Time: 45s
- Log: logs/learn_20260429_095326.log

---
## Learning Loop -- 2026-04-29 09:55

- Split: training, Tasks: 20
- Correct: 6 / 20 (30.0%)
- Rules: 6 -> 6 (+0 learned)
- Stored rule hits: 6
- Time: 44s
- Log: logs/learn_20260429_095420.log

---
## Learning Loop -- 2026-04-29 09:55

- Split: training, Tasks: 20
- Correct: 6 / 20 (30.0%)
- Rules: 6 -> 6 (+0 learned)
- Stored rule hits: 6
- Time: 44s
- Log: logs/learn_20260429_095513.log

---
## Learning Loop -- 2026-04-29 09:56

- Split: training, Tasks: 20
- Correct: 6 / 20 (30.0%)
- Rules: 6 -> 6 (+0 learned)
- Stored rule hits: 6
- Time: 44s
- Log: logs/learn_20260429_095606.log

---
## Learning Loop -- 2026-04-29 09:57

- Split: training, Tasks: 20
- Correct: 6 / 20 (30.0%)
- Rules: 6 -> 6 (+0 learned)
- Stored rule hits: 6
- Time: 45s
- Log: logs/learn_20260429_095659.log

---
## Learning Loop -- 2026-04-29 09:58

- Split: training, Tasks: 20
- Correct: 6 / 20 (30.0%)
- Rules: 6 -> 6 (+0 learned)
- Stored rule hits: 6
- Time: 44s
- Log: logs/learn_20260429_095753.log

---
## Learning Loop -- 2026-04-29 09:59

- Split: training, Tasks: 20
- Correct: 6 / 20 (30.0%)
- Rules: 6 -> 6 (+0 learned)
- Stored rule hits: 6
- Time: 44s
- Log: logs/learn_20260429_095846.log

---
## Learning Loop -- 2026-04-29 10:00

- Split: training, Tasks: 20
- Correct: 6 / 20 (30.0%)
- Rules: 6 -> 6 (+0 learned)
- Stored rule hits: 6
- Time: 44s
- Log: logs/learn_20260429_095939.log

---
## Learning Loop -- 2026-04-29 10:01

- Split: training, Tasks: 20
- Correct: 6 / 20 (30.0%)
- Rules: 6 -> 6 (+0 learned)
- Stored rule hits: 6
- Time: 44s
- Log: logs/learn_20260429_100032.log

---
## Learning Loop -- 2026-04-29 10:02

- Split: training, Tasks: 20
- Correct: 6 / 20 (30.0%)
- Rules: 6 -> 6 (+0 learned)
- Stored rule hits: 6
- Time: 44s
- Log: logs/learn_20260429_100125.log

---
## Learning Loop -- 2026-04-29 10:03

- Split: training, Tasks: 20
- Correct: 6 / 20 (30.0%)
- Rules: 6 -> 6 (+0 learned)
- Stored rule hits: 6
- Time: 46s
- Log: logs/learn_20260429_100217.log

---
## Learning Loop -- 2026-04-29 10:03

- Split: training, Tasks: 20
- Correct: 6 / 20 (30.0%)
- Rules: 6 -> 6 (+0 learned)
- Stored rule hits: 6
- Time: 45s
- Log: logs/learn_20260429_100312.log

---
## Learning Loop -- 2026-04-29 10:04

- Split: training, Tasks: 20
- Correct: 6 / 20 (30.0%)
- Rules: 6 -> 6 (+0 learned)
- Stored rule hits: 6
- Time: 44s
- Log: logs/learn_20260429_100406.log

---
## Learning Loop -- 2026-04-29 10:05

- Split: training, Tasks: 20
- Correct: 6 / 20 (30.0%)
- Rules: 6 -> 6 (+0 learned)
- Stored rule hits: 6
- Time: 44s
- Log: logs/learn_20260429_100459.log

---
## Learning Loop -- 2026-04-29 10:06

- Split: training, Tasks: 20
- Correct: 6 / 20 (30.0%)
- Rules: 6 -> 6 (+0 learned)
- Stored rule hits: 6
- Time: 44s
- Log: logs/learn_20260429_100552.log

---
## Learning Loop -- 2026-04-29 10:07

- Split: training, Tasks: 20
- Correct: 6 / 20 (30.0%)
- Rules: 6 -> 6 (+0 learned)
- Stored rule hits: 6
- Time: 45s
- Log: logs/learn_20260429_100645.log

---
## Learning Loop -- 2026-04-29 10:08

- Split: training, Tasks: 20
- Correct: 6 / 20 (30.0%)
- Rules: 6 -> 6 (+0 learned)
- Stored rule hits: 6
- Time: 44s
- Log: logs/learn_20260429_100739.log

---
## Learning Loop -- 2026-04-29 10:09

- Split: training, Tasks: 20
- Correct: 6 / 20 (30.0%)
- Rules: 6 -> 6 (+0 learned)
- Stored rule hits: 6
- Time: 44s
- Log: logs/learn_20260429_100832.log

---
## Learning Loop -- 2026-04-29 10:10

- Split: training, Tasks: 20
- Correct: 6 / 20 (30.0%)
- Rules: 6 -> 6 (+0 learned)
- Stored rule hits: 6
- Time: 44s
- Log: logs/learn_20260429_100925.log

---
## Learning Loop -- 2026-04-29 10:11

- Split: training, Tasks: 20
- Correct: 6 / 20 (30.0%)
- Rules: 6 -> 6 (+0 learned)
- Stored rule hits: 6
- Time: 44s
- Log: logs/learn_20260429_101018.log

---
## Learning Loop -- 2026-04-29 10:11

- Split: training, Tasks: 20
- Correct: 6 / 20 (30.0%)
- Rules: 6 -> 6 (+0 learned)
- Stored rule hits: 6
- Time: 44s
- Log: logs/learn_20260429_101110.log

---
## Learning Loop -- 2026-04-29 10:12

- Split: training, Tasks: 20
- Correct: 6 / 20 (30.0%)
- Rules: 6 -> 6 (+0 learned)
- Stored rule hits: 6
- Time: 44s
- Log: logs/learn_20260429_101204.log

---
## Learning Loop -- 2026-04-29 10:13

- Split: training, Tasks: 20
- Correct: 6 / 20 (30.0%)
- Rules: 6 -> 6 (+0 learned)
- Stored rule hits: 6
- Time: 44s
- Log: logs/learn_20260429_101256.log

---
## Learning Loop -- 2026-04-29 10:14

- Split: training, Tasks: 20
- Correct: 6 / 20 (30.0%)
- Rules: 6 -> 6 (+0 learned)
- Stored rule hits: 6
- Time: 44s
- Log: logs/learn_20260429_101349.log

---
## Learning Loop -- 2026-04-29 10:15

- Split: training, Tasks: 20
- Correct: 6 / 20 (30.0%)
- Rules: 6 -> 6 (+0 learned)
- Stored rule hits: 6
- Time: 44s
- Log: logs/learn_20260429_101442.log

---
## Learning Loop -- 2026-04-29 10:16

- Split: training, Tasks: 20
- Correct: 6 / 20 (30.0%)
- Rules: 6 -> 6 (+0 learned)
- Stored rule hits: 6
- Time: 44s
- Log: logs/learn_20260429_101535.log

---
## Learning Loop -- 2026-04-29 10:17

- Split: training, Tasks: 20
- Correct: 6 / 20 (30.0%)
- Rules: 6 -> 6 (+0 learned)
- Stored rule hits: 6
- Time: 44s
- Log: logs/learn_20260429_101628.log

---
## Learning Loop -- 2026-04-29 10:18

- Split: training, Tasks: 20
- Correct: 6 / 20 (30.0%)
- Rules: 6 -> 6 (+0 learned)
- Stored rule hits: 6
- Time: 44s
- Log: logs/learn_20260429_101721.log

---
## Learning Loop -- 2026-04-29 10:18

- Split: training, Tasks: 20
- Correct: 6 / 20 (30.0%)
- Rules: 6 -> 6 (+0 learned)
- Stored rule hits: 6
- Time: 43s
- Log: logs/learn_20260429_101814.log

---
## Learning Loop -- 2026-04-29 10:19

- Split: training, Tasks: 20
- Correct: 6 / 20 (30.0%)
- Rules: 6 -> 6 (+0 learned)
- Stored rule hits: 6
- Time: 42s
- Log: logs/learn_20260429_101906.log

---
## Learning Loop -- 2026-04-29 10:20

- Split: training, Tasks: 20
- Correct: 6 / 20 (30.0%)
- Rules: 6 -> 6 (+0 learned)
- Stored rule hits: 6
- Time: 42s
- Log: logs/learn_20260429_101957.log

---
## Learning Loop -- 2026-04-29 10:21

- Split: training, Tasks: 20
- Correct: 6 / 20 (30.0%)
- Rules: 6 -> 6 (+0 learned)
- Stored rule hits: 6
- Time: 42s
- Log: logs/learn_20260429_102048.log

---
## Learning Loop -- 2026-04-29 10:22

- Split: training, Tasks: 20
- Correct: 6 / 20 (30.0%)
- Rules: 6 -> 6 (+0 learned)
- Stored rule hits: 6
- Time: 42s
- Log: logs/learn_20260429_102139.log

---
## Learning Loop -- 2026-04-29 10:23

- Split: training, Tasks: 20
- Correct: 6 / 20 (30.0%)
- Rules: 6 -> 6 (+0 learned)
- Stored rule hits: 6
- Time: 42s
- Log: logs/learn_20260429_102229.log

---
## Learning Loop -- 2026-04-29 10:24

- Split: training, Tasks: 20
- Correct: 6 / 20 (30.0%)
- Rules: 6 -> 6 (+0 learned)
- Stored rule hits: 6
- Time: 42s
- Log: logs/learn_20260429_102320.log

---
## Learning Loop -- 2026-04-29 10:24

- Split: training, Tasks: 20
- Correct: 6 / 20 (30.0%)
- Rules: 6 -> 6 (+0 learned)
- Stored rule hits: 6
- Time: 42s
- Log: logs/learn_20260429_102411.log

---
## Learning Loop -- 2026-04-29 10:25

- Split: training, Tasks: 20
- Correct: 6 / 20 (30.0%)
- Rules: 6 -> 6 (+0 learned)
- Stored rule hits: 6
- Time: 42s
- Log: logs/learn_20260429_102502.log

---
## Learning Loop -- 2026-04-29 10:26

- Split: training, Tasks: 20
- Correct: 6 / 20 (30.0%)
- Rules: 6 -> 6 (+0 learned)
- Stored rule hits: 6
- Time: 42s
- Log: logs/learn_20260429_102553.log

---
## Learning Loop -- 2026-04-29 10:27

- Split: training, Tasks: 20
- Correct: 6 / 20 (30.0%)
- Rules: 6 -> 6 (+0 learned)
- Stored rule hits: 6
- Time: 42s
- Log: logs/learn_20260429_102644.log

---
## Learning Loop -- 2026-04-29 10:28

- Split: training, Tasks: 20
- Correct: 6 / 20 (30.0%)
- Rules: 6 -> 6 (+0 learned)
- Stored rule hits: 6
- Time: 42s
- Log: logs/learn_20260429_102735.log

---
## Learning Loop -- 2026-04-29 10:29

- Split: training, Tasks: 20
- Correct: 6 / 20 (30.0%)
- Rules: 6 -> 6 (+0 learned)
- Stored rule hits: 6
- Time: 43s
- Log: logs/learn_20260429_102827.log

---
## Learning Loop -- 2026-04-29 10:30

- Split: training, Tasks: 20
- Correct: 6 / 20 (30.0%)
- Rules: 6 -> 6 (+0 learned)
- Stored rule hits: 6
- Time: 42s
- Log: logs/learn_20260429_102918.log

---
## Learning Loop -- 2026-04-29 10:30

- Split: training, Tasks: 20
- Correct: 6 / 20 (30.0%)
- Rules: 6 -> 6 (+0 learned)
- Stored rule hits: 6
- Time: 42s
- Log: logs/learn_20260429_103009.log

---
## Learning Loop -- 2026-04-29 10:31

- Split: training, Tasks: 20
- Correct: 6 / 20 (30.0%)
- Rules: 6 -> 6 (+0 learned)
- Stored rule hits: 6
- Time: 43s
- Log: logs/learn_20260429_103100.log

---
## Learning Loop -- 2026-04-29 10:32

- Split: training, Tasks: 20
- Correct: 6 / 20 (30.0%)
- Rules: 6 -> 6 (+0 learned)
- Stored rule hits: 6
- Time: 43s
- Log: logs/learn_20260429_103151.log

---
## Learning Loop -- 2026-04-29 10:33

- Split: training, Tasks: 20
- Correct: 6 / 20 (30.0%)
- Rules: 6 -> 6 (+0 learned)
- Stored rule hits: 6
- Time: 44s
- Log: logs/learn_20260429_103244.log

---
## Learning Loop -- 2026-04-29 10:34

- Split: training, Tasks: 20
- Correct: 6 / 20 (30.0%)
- Rules: 6 -> 6 (+0 learned)
- Stored rule hits: 6
- Time: 42s
- Log: logs/learn_20260429_103337.log

---
## Learning Loop -- 2026-04-29 10:35

- Split: training, Tasks: 20
- Correct: 6 / 20 (30.0%)
- Rules: 6 -> 6 (+0 learned)
- Stored rule hits: 6
- Time: 42s
- Log: logs/learn_20260429_103428.log

---
## Learning Loop -- 2026-04-29 10:36

- Split: training, Tasks: 20
- Correct: 6 / 20 (30.0%)
- Rules: 6 -> 6 (+0 learned)
- Stored rule hits: 6
- Time: 42s
- Log: logs/learn_20260429_103519.log

---
## Learning Loop -- 2026-04-29 10:36

- Split: training, Tasks: 20
- Correct: 6 / 20 (30.0%)
- Rules: 6 -> 6 (+0 learned)
- Stored rule hits: 6
- Time: 42s
- Log: logs/learn_20260429_103610.log

---
## Learning Loop -- 2026-04-29 10:37

- Split: training, Tasks: 20
- Correct: 6 / 20 (30.0%)
- Rules: 6 -> 6 (+0 learned)
- Stored rule hits: 6
- Time: 42s
- Log: logs/learn_20260429_103701.log

---
## Learning Loop -- 2026-04-29 10:38

- Split: training, Tasks: 20
- Correct: 6 / 20 (30.0%)
- Rules: 6 -> 6 (+0 learned)
- Stored rule hits: 6
- Time: 43s
- Log: logs/learn_20260429_103751.log

---
## Learning Loop -- 2026-04-29 10:39

- Split: training, Tasks: 20
- Correct: 6 / 20 (30.0%)
- Rules: 6 -> 6 (+0 learned)
- Stored rule hits: 6
- Time: 42s
- Log: logs/learn_20260429_103843.log

---
## Learning Loop -- 2026-04-29 10:40

- Split: training, Tasks: 20
- Correct: 6 / 20 (30.0%)
- Rules: 6 -> 6 (+0 learned)
- Stored rule hits: 6
- Time: 43s
- Log: logs/learn_20260429_103934.log

---
## Learning Loop -- 2026-04-29 10:41

- Split: training, Tasks: 20
- Correct: 6 / 20 (30.0%)
- Rules: 6 -> 6 (+0 learned)
- Stored rule hits: 6
- Time: 42s
- Log: logs/learn_20260429_104025.log

---
## Learning Loop -- 2026-04-29 10:41

- Split: training, Tasks: 20
- Correct: 6 / 20 (30.0%)
- Rules: 6 -> 6 (+0 learned)
- Stored rule hits: 6
- Time: 43s
- Log: logs/learn_20260429_104116.log

---
## Learning Loop -- 2026-04-29 10:42

- Split: training, Tasks: 20
- Correct: 6 / 20 (30.0%)
- Rules: 6 -> 6 (+0 learned)
- Stored rule hits: 6
- Time: 42s
- Log: logs/learn_20260429_104208.log

---
## Learning Loop -- 2026-04-29 10:43

- Split: training, Tasks: 20
- Correct: 6 / 20 (30.0%)
- Rules: 6 -> 6 (+0 learned)
- Stored rule hits: 6
- Time: 42s
- Log: logs/learn_20260429_104259.log

---
## Learning Loop -- 2026-04-29 10:44

- Split: training, Tasks: 20
- Correct: 6 / 20 (30.0%)
- Rules: 6 -> 6 (+0 learned)
- Stored rule hits: 6
- Time: 42s
- Log: logs/learn_20260429_104350.log

---
## Learning Loop -- 2026-04-29 10:45

- Split: training, Tasks: 20
- Correct: 6 / 20 (30.0%)
- Rules: 6 -> 6 (+0 learned)
- Stored rule hits: 6
- Time: 43s
- Log: logs/learn_20260429_104441.log

---
## Learning Loop -- 2026-04-29 10:46

- Split: training, Tasks: 20
- Correct: 6 / 20 (30.0%)
- Rules: 6 -> 6 (+0 learned)
- Stored rule hits: 6
- Time: 42s
- Log: logs/learn_20260429_104532.log

---
## Learning Loop -- 2026-04-29 10:47

- Split: training, Tasks: 20
- Correct: 6 / 20 (30.0%)
- Rules: 6 -> 6 (+0 learned)
- Stored rule hits: 6
- Time: 42s
- Log: logs/learn_20260429_104623.log

---
## Learning Loop -- 2026-04-29 10:47

- Split: training, Tasks: 20
- Correct: 6 / 20 (30.0%)
- Rules: 6 -> 6 (+0 learned)
- Stored rule hits: 6
- Time: 42s
- Log: logs/learn_20260429_104714.log

---
## Learning Loop -- 2026-04-29 10:48

- Split: training, Tasks: 20
- Correct: 6 / 20 (30.0%)
- Rules: 6 -> 6 (+0 learned)
- Stored rule hits: 6
- Time: 42s
- Log: logs/learn_20260429_104805.log

---
## Learning Loop -- 2026-04-29 10:49

- Split: training, Tasks: 20
- Correct: 6 / 20 (30.0%)
- Rules: 6 -> 6 (+0 learned)
- Stored rule hits: 6
- Time: 42s
- Log: logs/learn_20260429_104856.log

---
## Learning Loop -- 2026-04-29 10:50

- Split: training, Tasks: 20
- Correct: 6 / 20 (30.0%)
- Rules: 6 -> 6 (+0 learned)
- Stored rule hits: 6
- Time: 42s
- Log: logs/learn_20260429_104947.log

---
## Learning Loop -- 2026-04-29 10:51

- Split: training, Tasks: 20
- Correct: 6 / 20 (30.0%)
- Rules: 6 -> 6 (+0 learned)
- Stored rule hits: 6
- Time: 42s
- Log: logs/learn_20260429_105038.log

---
## Learning Loop -- 2026-04-29 10:52

- Split: training, Tasks: 20
- Correct: 6 / 20 (30.0%)
- Rules: 6 -> 6 (+0 learned)
- Stored rule hits: 6
- Time: 42s
- Log: logs/learn_20260429_105128.log

---
## Learning Loop -- 2026-04-29 10:53

- Split: training, Tasks: 20
- Correct: 6 / 20 (30.0%)
- Rules: 6 -> 6 (+0 learned)
- Stored rule hits: 6
- Time: 45s
- Log: logs/learn_20260429_105220.log

---
## Learning Loop -- 2026-04-29 10:53

- Split: training, Tasks: 20
- Correct: 6 / 20 (30.0%)
- Rules: 6 -> 6 (+0 learned)
- Stored rule hits: 6
- Time: 43s
- Log: logs/learn_20260429_105314.log

---
## Learning Loop -- 2026-04-29 10:54

- Split: training, Tasks: 20
- Correct: 6 / 20 (30.0%)
- Rules: 6 -> 6 (+0 learned)
- Stored rule hits: 6
- Time: 42s
- Log: logs/learn_20260429_105406.log

---
## Learning Loop -- 2026-04-29 10:55

- Split: training, Tasks: 20
- Correct: 6 / 20 (30.0%)
- Rules: 6 -> 6 (+0 learned)
- Stored rule hits: 6
- Time: 42s
- Log: logs/learn_20260429_105457.log

---
## Learning Loop -- 2026-04-29 10:56

- Split: training, Tasks: 20
- Correct: 6 / 20 (30.0%)
- Rules: 6 -> 6 (+0 learned)
- Stored rule hits: 6
- Time: 42s
- Log: logs/learn_20260429_105547.log

---
## Learning Loop -- 2026-04-29 10:57

- Split: training, Tasks: 20
- Correct: 6 / 20 (30.0%)
- Rules: 6 -> 6 (+0 learned)
- Stored rule hits: 6
- Time: 42s
- Log: logs/learn_20260429_105638.log

---
## Learning Loop -- 2026-04-29 10:58

- Split: training, Tasks: 20
- Correct: 6 / 20 (30.0%)
- Rules: 6 -> 6 (+0 learned)
- Stored rule hits: 6
- Time: 42s
- Log: logs/learn_20260429_105729.log

---
## Learning Loop -- 2026-04-29 10:59

- Split: training, Tasks: 20
- Correct: 6 / 20 (30.0%)
- Rules: 6 -> 6 (+0 learned)
- Stored rule hits: 6
- Time: 42s
- Log: logs/learn_20260429_105820.log

---
## Learning Loop -- 2026-04-29 10:59

- Split: training, Tasks: 20
- Correct: 6 / 20 (30.0%)
- Rules: 6 -> 6 (+0 learned)
- Stored rule hits: 6
- Time: 42s
- Log: logs/learn_20260429_105910.log

---
## Learning Loop -- 2026-04-29 11:00

- Split: training, Tasks: 20
- Correct: 6 / 20 (30.0%)
- Rules: 6 -> 6 (+0 learned)
- Stored rule hits: 6
- Time: 42s
- Log: logs/learn_20260429_110001.log

---
## Learning Loop -- 2026-04-29 11:01

- Split: training, Tasks: 20
- Correct: 6 / 20 (30.0%)
- Rules: 6 -> 6 (+0 learned)
- Stored rule hits: 6
- Time: 42s
- Log: logs/learn_20260429_110052.log

---
## Learning Loop -- 2026-04-29 11:02

- Split: training, Tasks: 20
- Correct: 6 / 20 (30.0%)
- Rules: 6 -> 6 (+0 learned)
- Stored rule hits: 6
- Time: 42s
- Log: logs/learn_20260429_110143.log

---
## Learning Loop -- 2026-04-29 11:03

- Split: training, Tasks: 20
- Correct: 6 / 20 (30.0%)
- Rules: 6 -> 6 (+0 learned)
- Stored rule hits: 6
- Time: 43s
- Log: logs/learn_20260429_110234.log

---
## Learning Loop -- 2026-04-29 11:04

- Split: training, Tasks: 20
- Correct: 6 / 20 (30.0%)
- Rules: 6 -> 6 (+0 learned)
- Stored rule hits: 6
- Time: 43s
- Log: logs/learn_20260429_110326.log

---
## Learning Loop -- 2026-04-29 11:05

- Split: training, Tasks: 20
- Correct: 6 / 20 (30.0%)
- Rules: 6 -> 6 (+0 learned)
- Stored rule hits: 6
- Time: 42s
- Log: logs/learn_20260429_110418.log

---
## Learning Loop -- 2026-04-29 11:05

- Split: training, Tasks: 20
- Correct: 6 / 20 (30.0%)
- Rules: 6 -> 6 (+0 learned)
- Stored rule hits: 6
- Time: 42s
- Log: logs/learn_20260429_110509.log

---
## Learning Loop -- 2026-04-29 11:06

- Split: training, Tasks: 20
- Correct: 6 / 20 (30.0%)
- Rules: 6 -> 6 (+0 learned)
- Stored rule hits: 6
- Time: 42s
- Log: logs/learn_20260429_110600.log

---
## Learning Loop -- 2026-04-29 11:07

- Split: training, Tasks: 20
- Correct: 6 / 20 (30.0%)
- Rules: 6 -> 6 (+0 learned)
- Stored rule hits: 6
- Time: 42s
- Log: logs/learn_20260429_110651.log

---
## Learning Loop -- 2026-04-29 11:08

- Split: training, Tasks: 20
- Correct: 6 / 20 (30.0%)
- Rules: 6 -> 6 (+0 learned)
- Stored rule hits: 6
- Time: 42s
- Log: logs/learn_20260429_110742.log

---
## Learning Loop -- 2026-04-29 11:09

- Split: training, Tasks: 20
- Correct: 6 / 20 (30.0%)
- Rules: 6 -> 6 (+0 learned)
- Stored rule hits: 6
- Time: 42s
- Log: logs/learn_20260429_110833.log

---
## Learning Loop -- 2026-04-29 11:10

- Split: training, Tasks: 20
- Correct: 6 / 20 (30.0%)
- Rules: 6 -> 6 (+0 learned)
- Stored rule hits: 6
- Time: 42s
- Log: logs/learn_20260429_110924.log

---
## Learning Loop -- 2026-04-29 11:10

- Split: training, Tasks: 20
- Correct: 6 / 20 (30.0%)
- Rules: 6 -> 6 (+0 learned)
- Stored rule hits: 6
- Time: 43s
- Log: logs/learn_20260429_111015.log

---
## Learning Loop -- 2026-04-29 11:11

- Split: training, Tasks: 20
- Correct: 6 / 20 (30.0%)
- Rules: 6 -> 6 (+0 learned)
- Stored rule hits: 6
- Time: 42s
- Log: logs/learn_20260429_111106.log

---
## Learning Loop -- 2026-04-29 11:12

- Split: training, Tasks: 20
- Correct: 6 / 20 (30.0%)
- Rules: 6 -> 6 (+0 learned)
- Stored rule hits: 6
- Time: 42s
- Log: logs/learn_20260429_111157.log

---
## Learning Loop -- 2026-04-29 11:13

- Split: training, Tasks: 20
- Correct: 6 / 20 (30.0%)
- Rules: 6 -> 6 (+0 learned)
- Stored rule hits: 6
- Time: 42s
- Log: logs/learn_20260429_111249.log

---
## Learning Loop -- 2026-04-29 11:14

- Split: training, Tasks: 20
- Correct: 6 / 20 (30.0%)
- Rules: 6 -> 6 (+0 learned)
- Stored rule hits: 6
- Time: 42s
- Log: logs/learn_20260429_111340.log

---
## Learning Loop -- 2026-04-29 11:15

- Split: training, Tasks: 20
- Correct: 6 / 20 (30.0%)
- Rules: 6 -> 6 (+0 learned)
- Stored rule hits: 6
- Time: 42s
- Log: logs/learn_20260429_111431.log

---
## Learning Loop -- 2026-04-29 11:16

- Split: training, Tasks: 20
- Correct: 6 / 20 (30.0%)
- Rules: 6 -> 6 (+0 learned)
- Stored rule hits: 6
- Time: 42s
- Log: logs/learn_20260429_111522.log

---
## Learning Loop -- 2026-04-29 11:16

- Split: training, Tasks: 20
- Correct: 6 / 20 (30.0%)
- Rules: 6 -> 6 (+0 learned)
- Stored rule hits: 6
- Time: 42s
- Log: logs/learn_20260429_111613.log

---
## Learning Loop -- 2026-04-29 11:17

- Split: training, Tasks: 20
- Correct: 6 / 20 (30.0%)
- Rules: 6 -> 6 (+0 learned)
- Stored rule hits: 6
- Time: 42s
- Log: logs/learn_20260429_111704.log

---
## Learning Loop -- 2026-04-29 11:18

- Split: training, Tasks: 20
- Correct: 6 / 20 (30.0%)
- Rules: 6 -> 6 (+0 learned)
- Stored rule hits: 6
- Time: 42s
- Log: logs/learn_20260429_111755.log

---
## Learning Loop -- 2026-04-29 11:19

- Split: training, Tasks: 20
- Correct: 6 / 20 (30.0%)
- Rules: 6 -> 6 (+0 learned)
- Stored rule hits: 6
- Time: 42s
- Log: logs/learn_20260429_111846.log

---
## Learning Loop -- 2026-04-29 11:20

- Split: training, Tasks: 20
- Correct: 6 / 20 (30.0%)
- Rules: 6 -> 6 (+0 learned)
- Stored rule hits: 6
- Time: 42s
- Log: logs/learn_20260429_111937.log

---
## Learning Loop -- 2026-04-29 11:21

- Split: training, Tasks: 20
- Correct: 6 / 20 (30.0%)
- Rules: 6 -> 6 (+0 learned)
- Stored rule hits: 6
- Time: 42s
- Log: logs/learn_20260429_112028.log

---
## Learning Loop -- 2026-04-29 11:22

- Split: training, Tasks: 20
- Correct: 6 / 20 (30.0%)
- Rules: 6 -> 6 (+0 learned)
- Stored rule hits: 6
- Time: 42s
- Log: logs/learn_20260429_112119.log

---
## Learning Loop -- 2026-04-29 11:22

- Split: training, Tasks: 20
- Correct: 6 / 20 (30.0%)
- Rules: 6 -> 6 (+0 learned)
- Stored rule hits: 6
- Time: 42s
- Log: logs/learn_20260429_112210.log

---
## Learning Loop -- 2026-04-29 11:23

- Split: training, Tasks: 20
- Correct: 6 / 20 (30.0%)
- Rules: 6 -> 6 (+0 learned)
- Stored rule hits: 6
- Time: 42s
- Log: logs/learn_20260429_112301.log

---
## Learning Loop -- 2026-04-29 11:24

- Split: training, Tasks: 20
- Correct: 6 / 20 (30.0%)
- Rules: 6 -> 6 (+0 learned)
- Stored rule hits: 6
- Time: 42s
- Log: logs/learn_20260429_112352.log

---
## Learning Loop -- 2026-04-29 11:25

- Split: training, Tasks: 20
- Correct: 6 / 20 (30.0%)
- Rules: 6 -> 6 (+0 learned)
- Stored rule hits: 6
- Time: 42s
- Log: logs/learn_20260429_112443.log

---
## Learning Loop -- 2026-04-29 11:26

- Split: training, Tasks: 20
- Correct: 6 / 20 (30.0%)
- Rules: 6 -> 6 (+0 learned)
- Stored rule hits: 6
- Time: 42s
- Log: logs/learn_20260429_112534.log

---
## Learning Loop -- 2026-04-29 11:27

- Split: training, Tasks: 20
- Correct: 6 / 20 (30.0%)
- Rules: 6 -> 6 (+0 learned)
- Stored rule hits: 6
- Time: 42s
- Log: logs/learn_20260429_112625.log

---
## Learning Loop -- 2026-04-29 11:27

- Split: training, Tasks: 20
- Correct: 6 / 20 (30.0%)
- Rules: 6 -> 6 (+0 learned)
- Stored rule hits: 6
- Time: 42s
- Log: logs/learn_20260429_112716.log

---
## Learning Loop -- 2026-04-29 11:28

- Split: training, Tasks: 20
- Correct: 6 / 20 (30.0%)
- Rules: 6 -> 6 (+0 learned)
- Stored rule hits: 6
- Time: 42s
- Log: logs/learn_20260429_112807.log

---
## Learning Loop -- 2026-04-29 11:29

- Split: training, Tasks: 20
- Correct: 6 / 20 (30.0%)
- Rules: 6 -> 6 (+0 learned)
- Stored rule hits: 6
- Time: 42s
- Log: logs/learn_20260429_112858.log

---
## Learning Loop -- 2026-04-29 11:30

- Split: training, Tasks: 20
- Correct: 6 / 20 (30.0%)
- Rules: 6 -> 6 (+0 learned)
- Stored rule hits: 6
- Time: 42s
- Log: logs/learn_20260429_112949.log

---
## Learning Loop -- 2026-04-29 11:31

- Split: training, Tasks: 20
- Correct: 6 / 20 (30.0%)
- Rules: 6 -> 6 (+0 learned)
- Stored rule hits: 6
- Time: 43s
- Log: logs/learn_20260429_113040.log

---
## Learning Loop -- 2026-04-29 11:32

- Split: training, Tasks: 20
- Correct: 6 / 20 (30.0%)
- Rules: 6 -> 6 (+0 learned)
- Stored rule hits: 6
- Time: 43s
- Log: logs/learn_20260429_113131.log

---
## Learning Loop -- 2026-04-29 11:33

- Split: training, Tasks: 20
- Correct: 6 / 20 (30.0%)
- Rules: 6 -> 6 (+0 learned)
- Stored rule hits: 6
- Time: 44s
- Log: logs/learn_20260429_113223.log

---
## Learning Loop -- 2026-04-29 11:33

- Split: training, Tasks: 20
- Correct: 6 / 20 (30.0%)
- Rules: 6 -> 6 (+0 learned)
- Stored rule hits: 6
- Time: 43s
- Log: logs/learn_20260429_113316.log

---
## Learning Loop -- 2026-04-29 11:34

- Split: training, Tasks: 20
- Correct: 6 / 20 (30.0%)
- Rules: 6 -> 6 (+0 learned)
- Stored rule hits: 6
- Time: 43s
- Log: logs/learn_20260429_113407.log

---
## Learning Loop -- 2026-04-29 11:35

- Split: training, Tasks: 20
- Correct: 6 / 20 (30.0%)
- Rules: 6 -> 6 (+0 learned)
- Stored rule hits: 6
- Time: 42s
- Log: logs/learn_20260429_113459.log

---
## Learning Loop -- 2026-04-29 11:36

- Split: training, Tasks: 20
- Correct: 6 / 20 (30.0%)
- Rules: 6 -> 6 (+0 learned)
- Stored rule hits: 6
- Time: 42s
- Log: logs/learn_20260429_113550.log

---
## Learning Loop -- 2026-04-29 11:37

- Split: training, Tasks: 20
- Correct: 6 / 20 (30.0%)
- Rules: 6 -> 6 (+0 learned)
- Stored rule hits: 6
- Time: 42s
- Log: logs/learn_20260429_113641.log

---
## Learning Loop -- 2026-04-29 11:38

- Split: training, Tasks: 20
- Correct: 6 / 20 (30.0%)
- Rules: 6 -> 6 (+0 learned)
- Stored rule hits: 6
- Time: 43s
- Log: logs/learn_20260429_113733.log

---
## Learning Loop -- 2026-04-29 11:39

- Split: training, Tasks: 20
- Correct: 6 / 20 (30.0%)
- Rules: 6 -> 6 (+0 learned)
- Stored rule hits: 6
- Time: 43s
- Log: logs/learn_20260429_113824.log

---
## Learning Loop -- 2026-04-29 11:39

- Split: training, Tasks: 20
- Correct: 6 / 20 (30.0%)
- Rules: 6 -> 6 (+0 learned)
- Stored rule hits: 6
- Time: 43s
- Log: logs/learn_20260429_113915.log

---
## Learning Loop -- 2026-04-29 11:40

- Split: training, Tasks: 20
- Correct: 6 / 20 (30.0%)
- Rules: 6 -> 6 (+0 learned)
- Stored rule hits: 6
- Time: 43s
- Log: logs/learn_20260429_114007.log

---
## Learning Loop -- 2026-04-29 11:41

- Split: training, Tasks: 20
- Correct: 6 / 20 (30.0%)
- Rules: 6 -> 6 (+0 learned)
- Stored rule hits: 6
- Time: 43s
- Log: logs/learn_20260429_114058.log

---
## Learning Loop -- 2026-04-29 11:42

- Split: training, Tasks: 20
- Correct: 6 / 20 (30.0%)
- Rules: 6 -> 6 (+0 learned)
- Stored rule hits: 6
- Time: 43s
- Log: logs/learn_20260429_114149.log

---
## Learning Loop -- 2026-04-29 11:43

- Split: training, Tasks: 20
- Correct: 6 / 20 (30.0%)
- Rules: 6 -> 6 (+0 learned)
- Stored rule hits: 6
- Time: 42s
- Log: logs/learn_20260429_114241.log

---
## Learning Loop -- 2026-04-29 11:44

- Split: training, Tasks: 20
- Correct: 6 / 20 (30.0%)
- Rules: 6 -> 6 (+0 learned)
- Stored rule hits: 6
- Time: 42s
- Log: logs/learn_20260429_114332.log

---
## Learning Loop -- 2026-04-29 11:45

- Split: training, Tasks: 20
- Correct: 6 / 20 (30.0%)
- Rules: 6 -> 6 (+0 learned)
- Stored rule hits: 6
- Time: 42s
- Log: logs/learn_20260429_114423.log

---
## Learning Loop -- 2026-04-29 11:45

- Split: training, Tasks: 20
- Correct: 6 / 20 (30.0%)
- Rules: 6 -> 6 (+0 learned)
- Stored rule hits: 6
- Time: 42s
- Log: logs/learn_20260429_114514.log

---
## Learning Loop -- 2026-04-29 11:46

- Split: training, Tasks: 20
- Correct: 6 / 20 (30.0%)
- Rules: 6 -> 6 (+0 learned)
- Stored rule hits: 6
- Time: 42s
- Log: logs/learn_20260429_114605.log

---
## Learning Loop -- 2026-04-29 11:47

- Split: training, Tasks: 20
- Correct: 6 / 20 (30.0%)
- Rules: 6 -> 6 (+0 learned)
- Stored rule hits: 6
- Time: 42s
- Log: logs/learn_20260429_114656.log

---
## Learning Loop -- 2026-04-29 11:48

- Split: training, Tasks: 20
- Correct: 6 / 20 (30.0%)
- Rules: 6 -> 6 (+0 learned)
- Stored rule hits: 6
- Time: 42s
- Log: logs/learn_20260429_114747.log

---
## Learning Loop -- 2026-04-29 11:49

- Split: training, Tasks: 20
- Correct: 6 / 20 (30.0%)
- Rules: 6 -> 6 (+0 learned)
- Stored rule hits: 6
- Time: 42s
- Log: logs/learn_20260429_114838.log

---
## Learning Loop -- 2026-04-29 11:50

- Split: training, Tasks: 20
- Correct: 6 / 20 (30.0%)
- Rules: 6 -> 6 (+0 learned)
- Stored rule hits: 6
- Time: 43s
- Log: logs/learn_20260429_114930.log

---
## Learning Loop -- 2026-04-29 11:51

- Split: training, Tasks: 20
- Correct: 6 / 20 (30.0%)
- Rules: 6 -> 6 (+0 learned)
- Stored rule hits: 6
- Time: 42s
- Log: logs/learn_20260429_115021.log

---
## Learning Loop -- 2026-04-29 11:51

- Split: training, Tasks: 20
- Correct: 6 / 20 (30.0%)
- Rules: 6 -> 6 (+0 learned)
- Stored rule hits: 6
- Time: 43s
- Log: logs/learn_20260429_115112.log

---
## Learning Loop -- 2026-04-29 11:52

- Split: training, Tasks: 20
- Correct: 6 / 20 (30.0%)
- Rules: 6 -> 6 (+0 learned)
- Stored rule hits: 6
- Time: 42s
- Log: logs/learn_20260429_115203.log

---
## Learning Loop -- 2026-04-29 11:53

- Split: training, Tasks: 20
- Correct: 6 / 20 (30.0%)
- Rules: 6 -> 6 (+0 learned)
- Stored rule hits: 6
- Time: 42s
- Log: logs/learn_20260429_115255.log

---
## Learning Loop -- 2026-04-29 11:54

- Split: training, Tasks: 20
- Correct: 6 / 20 (30.0%)
- Rules: 6 -> 6 (+0 learned)
- Stored rule hits: 6
- Time: 42s
- Log: logs/learn_20260429_115346.log

---
## Learning Loop -- 2026-04-29 11:55

- Split: training, Tasks: 20
- Correct: 6 / 20 (30.0%)
- Rules: 6 -> 6 (+0 learned)
- Stored rule hits: 6
- Time: 43s
- Log: logs/learn_20260429_115437.log

---
## Learning Loop -- 2026-04-29 11:56

- Split: training, Tasks: 20
- Correct: 6 / 20 (30.0%)
- Rules: 6 -> 6 (+0 learned)
- Stored rule hits: 6
- Time: 43s
- Log: logs/learn_20260429_115528.log

---
## Learning Loop -- 2026-04-29 11:57

- Split: training, Tasks: 20
- Correct: 6 / 20 (30.0%)
- Rules: 6 -> 6 (+0 learned)
- Stored rule hits: 6
- Time: 42s
- Log: logs/learn_20260429_115619.log

---
## Learning Loop -- 2026-04-29 11:57

- Split: training, Tasks: 20
- Correct: 6 / 20 (30.0%)
- Rules: 6 -> 6 (+0 learned)
- Stored rule hits: 6
- Time: 42s
- Log: logs/learn_20260429_115710.log

---
## Learning Loop -- 2026-04-29 11:58

- Split: training, Tasks: 20
- Correct: 6 / 20 (30.0%)
- Rules: 6 -> 6 (+0 learned)
- Stored rule hits: 6
- Time: 42s
- Log: logs/learn_20260429_115801.log

---
## Learning Loop -- 2026-04-29 11:59

- Split: training, Tasks: 20
- Correct: 6 / 20 (30.0%)
- Rules: 6 -> 6 (+0 learned)
- Stored rule hits: 6
- Time: 43s
- Log: logs/learn_20260429_115852.log

---
## Learning Loop -- 2026-04-29 12:00

- Split: training, Tasks: 20
- Correct: 6 / 20 (30.0%)
- Rules: 6 -> 6 (+0 learned)
- Stored rule hits: 6
- Time: 42s
- Log: logs/learn_20260429_115944.log

---
## Learning Loop -- 2026-04-29 12:01

- Split: training, Tasks: 20
- Correct: 6 / 20 (30.0%)
- Rules: 6 -> 6 (+0 learned)
- Stored rule hits: 6
- Time: 42s
- Log: logs/learn_20260429_120035.log

---
## Learning Loop -- 2026-04-29 12:02

- Split: training, Tasks: 20
- Correct: 6 / 20 (30.0%)
- Rules: 6 -> 6 (+0 learned)
- Stored rule hits: 6
- Time: 43s
- Log: logs/learn_20260429_120126.log

---
## Learning Loop -- 2026-04-29 12:03

- Split: training, Tasks: 20
- Correct: 6 / 20 (30.0%)
- Rules: 6 -> 6 (+0 learned)
- Stored rule hits: 6
- Time: 43s
- Log: logs/learn_20260429_120217.log

---
## Learning Loop -- 2026-04-29 12:03

- Split: training, Tasks: 20
- Correct: 6 / 20 (30.0%)
- Rules: 6 -> 6 (+0 learned)
- Stored rule hits: 6
- Time: 43s
- Log: logs/learn_20260429_120309.log

---
## Learning Loop -- 2026-04-29 12:04

- Split: training, Tasks: 20
- Correct: 6 / 20 (30.0%)
- Rules: 6 -> 6 (+0 learned)
- Stored rule hits: 6
- Time: 43s
- Log: logs/learn_20260429_120401.log

---
## Learning Loop -- 2026-04-29 12:05

- Split: training, Tasks: 20
- Correct: 6 / 20 (30.0%)
- Rules: 6 -> 6 (+0 learned)
- Stored rule hits: 6
- Time: 42s
- Log: logs/learn_20260429_120452.log

---
## Learning Loop -- 2026-04-29 12:06

- Split: training, Tasks: 20
- Correct: 6 / 20 (30.0%)
- Rules: 6 -> 6 (+0 learned)
- Stored rule hits: 6
- Time: 43s
- Log: logs/learn_20260429_120543.log

---
## Learning Loop -- 2026-04-29 12:07

- Split: training, Tasks: 20
- Correct: 6 / 20 (30.0%)
- Rules: 6 -> 6 (+0 learned)
- Stored rule hits: 6
- Time: 43s
- Log: logs/learn_20260429_120635.log

---
## Learning Loop -- 2026-04-29 12:08

- Split: training, Tasks: 20
- Correct: 6 / 20 (30.0%)
- Rules: 6 -> 6 (+0 learned)
- Stored rule hits: 6
- Time: 43s
- Log: logs/learn_20260429_120726.log

---
## Learning Loop -- 2026-04-29 12:09

- Split: training, Tasks: 20
- Correct: 6 / 20 (30.0%)
- Rules: 6 -> 6 (+0 learned)
- Stored rule hits: 6
- Time: 42s
- Log: logs/learn_20260429_120818.log

---
## Learning Loop -- 2026-04-29 12:09

- Split: training, Tasks: 20
- Correct: 6 / 20 (30.0%)
- Rules: 6 -> 6 (+0 learned)
- Stored rule hits: 6
- Time: 43s
- Log: logs/learn_20260429_120909.log

---
## Learning Loop -- 2026-04-29 12:10

- Split: training, Tasks: 20
- Correct: 6 / 20 (30.0%)
- Rules: 6 -> 6 (+0 learned)
- Stored rule hits: 6
- Time: 43s
- Log: logs/learn_20260429_121001.log

---
## Learning Loop -- 2026-04-29 12:11

- Split: training, Tasks: 20
- Correct: 6 / 20 (30.0%)
- Rules: 6 -> 6 (+0 learned)
- Stored rule hits: 6
- Time: 42s
- Log: logs/learn_20260429_121052.log

---
## Learning Loop -- 2026-04-29 12:12

- Split: training, Tasks: 20
- Correct: 6 / 20 (30.0%)
- Rules: 6 -> 6 (+0 learned)
- Stored rule hits: 6
- Time: 43s
- Log: logs/learn_20260429_121144.log

---
## Learning Loop -- 2026-04-29 12:13

- Split: training, Tasks: 20
- Correct: 6 / 20 (30.0%)
- Rules: 6 -> 6 (+0 learned)
- Stored rule hits: 6
- Time: 43s
- Log: logs/learn_20260429_121235.log

---
## Learning Loop -- 2026-04-29 12:14

- Split: training, Tasks: 20
- Correct: 6 / 20 (30.0%)
- Rules: 6 -> 6 (+0 learned)
- Stored rule hits: 6
- Time: 43s
- Log: logs/learn_20260429_121327.log

---
## Learning Loop -- 2026-04-29 12:15

- Split: training, Tasks: 20
- Correct: 6 / 20 (30.0%)
- Rules: 6 -> 6 (+0 learned)
- Stored rule hits: 6
- Time: 42s
- Log: logs/learn_20260429_121418.log

---
## Learning Loop -- 2026-04-29 12:15

- Split: training, Tasks: 20
- Correct: 6 / 20 (30.0%)
- Rules: 6 -> 6 (+0 learned)
- Stored rule hits: 6
- Time: 43s
- Log: logs/learn_20260429_121510.log

---
## Learning Loop -- 2026-04-29 12:16

- Split: training, Tasks: 20
- Correct: 6 / 20 (30.0%)
- Rules: 6 -> 6 (+0 learned)
- Stored rule hits: 6
- Time: 42s
- Log: logs/learn_20260429_121601.log

---
## Learning Loop -- 2026-04-29 12:17

- Split: training, Tasks: 20
- Correct: 6 / 20 (30.0%)
- Rules: 6 -> 6 (+0 learned)
- Stored rule hits: 6
- Time: 43s
- Log: logs/learn_20260429_121652.log

---
## Learning Loop -- 2026-04-29 12:18

- Split: training, Tasks: 20
- Correct: 6 / 20 (30.0%)
- Rules: 6 -> 6 (+0 learned)
- Stored rule hits: 6
- Time: 42s
- Log: logs/learn_20260429_121744.log

---
## Learning Loop -- 2026-04-29 12:19

- Split: training, Tasks: 20
- Correct: 6 / 20 (30.0%)
- Rules: 6 -> 6 (+0 learned)
- Stored rule hits: 6
- Time: 42s
- Log: logs/learn_20260429_121835.log

---
## Learning Loop -- 2026-04-29 12:20

- Split: training, Tasks: 20
- Correct: 6 / 20 (30.0%)
- Rules: 6 -> 6 (+0 learned)
- Stored rule hits: 6
- Time: 42s
- Log: logs/learn_20260429_121926.log

---
## Learning Loop -- 2026-04-29 12:21

- Split: training, Tasks: 20
- Correct: 6 / 20 (30.0%)
- Rules: 6 -> 6 (+0 learned)
- Stored rule hits: 6
- Time: 43s
- Log: logs/learn_20260429_122017.log

---
## Learning Loop -- 2026-04-29 12:21

- Split: training, Tasks: 20
- Correct: 6 / 20 (30.0%)
- Rules: 6 -> 6 (+0 learned)
- Stored rule hits: 6
- Time: 43s
- Log: logs/learn_20260429_122109.log

---
## Learning Loop -- 2026-04-29 12:22

- Split: training, Tasks: 20
- Correct: 6 / 20 (30.0%)
- Rules: 6 -> 6 (+0 learned)
- Stored rule hits: 6
- Time: 42s
- Log: logs/learn_20260429_122200.log

---
## Learning Loop -- 2026-04-29 12:23

- Split: training, Tasks: 20
- Correct: 6 / 20 (30.0%)
- Rules: 6 -> 6 (+0 learned)
- Stored rule hits: 6
- Time: 42s
- Log: logs/learn_20260429_122251.log

---
## Learning Loop -- 2026-04-29 12:24

- Split: training, Tasks: 20
- Correct: 6 / 20 (30.0%)
- Rules: 6 -> 6 (+0 learned)
- Stored rule hits: 6
- Time: 42s
- Log: logs/learn_20260429_122342.log

---
## Learning Loop -- 2026-04-29 12:25

- Split: training, Tasks: 20
- Correct: 6 / 20 (30.0%)
- Rules: 6 -> 6 (+0 learned)
- Stored rule hits: 6
- Time: 43s
- Log: logs/learn_20260429_122434.log

---
## Learning Loop -- 2026-04-29 12:26

- Split: training, Tasks: 20
- Correct: 6 / 20 (30.0%)
- Rules: 6 -> 6 (+0 learned)
- Stored rule hits: 6
- Time: 42s
- Log: logs/learn_20260429_122525.log

---
## Learning Loop -- 2026-04-29 12:26

- Split: training, Tasks: 20
- Correct: 6 / 20 (30.0%)
- Rules: 6 -> 6 (+0 learned)
- Stored rule hits: 6
- Time: 43s
- Log: logs/learn_20260429_122616.log

---
## Learning Loop -- 2026-04-29 12:27

- Split: training, Tasks: 20
- Correct: 6 / 20 (30.0%)
- Rules: 6 -> 6 (+0 learned)
- Stored rule hits: 6
- Time: 42s
- Log: logs/learn_20260429_122707.log

---
## Learning Loop -- 2026-04-29 12:28

- Split: training, Tasks: 20
- Correct: 6 / 20 (30.0%)
- Rules: 6 -> 6 (+0 learned)
- Stored rule hits: 6
- Time: 42s
- Log: logs/learn_20260429_122758.log

---
## Learning Loop -- 2026-04-29 12:29

- Split: training, Tasks: 20
- Correct: 6 / 20 (30.0%)
- Rules: 6 -> 6 (+0 learned)
- Stored rule hits: 6
- Time: 42s
- Log: logs/learn_20260429_122849.log

---
## Learning Loop -- 2026-04-29 12:30

- Split: training, Tasks: 20
- Correct: 6 / 20 (30.0%)
- Rules: 6 -> 6 (+0 learned)
- Stored rule hits: 6
- Time: 42s
- Log: logs/learn_20260429_122940.log

---
## Learning Loop -- 2026-04-29 12:31

- Split: training, Tasks: 20
- Correct: 6 / 20 (30.0%)
- Rules: 6 -> 6 (+0 learned)
- Stored rule hits: 6
- Time: 43s
- Log: logs/learn_20260429_123031.log

---
## Learning Loop -- 2026-04-29 12:32

- Split: training, Tasks: 20
- Correct: 6 / 20 (30.0%)
- Rules: 6 -> 6 (+0 learned)
- Stored rule hits: 6
- Time: 42s
- Log: logs/learn_20260429_123123.log

---
## Learning Loop -- 2026-04-29 12:32

- Split: training, Tasks: 20
- Correct: 6 / 20 (30.0%)
- Rules: 6 -> 6 (+0 learned)
- Stored rule hits: 6
- Time: 44s
- Log: logs/learn_20260429_123214.log

---
## Learning Loop -- 2026-04-29 12:33

- Split: training, Tasks: 20
- Correct: 6 / 20 (30.0%)
- Rules: 6 -> 6 (+0 learned)
- Stored rule hits: 6
- Time: 44s
- Log: logs/learn_20260429_123306.log

---
## Learning Loop -- 2026-04-29 12:34

- Split: training, Tasks: 20
- Correct: 6 / 20 (30.0%)
- Rules: 6 -> 6 (+0 learned)
- Stored rule hits: 6
- Time: 43s
- Log: logs/learn_20260429_123359.log

---
## Learning Loop -- 2026-04-29 12:35

- Split: training, Tasks: 20
- Correct: 6 / 20 (30.0%)
- Rules: 6 -> 6 (+0 learned)
- Stored rule hits: 6
- Time: 43s
- Log: logs/learn_20260429_123450.log

---
## Learning Loop -- 2026-04-29 12:36

- Split: training, Tasks: 20
- Correct: 6 / 20 (30.0%)
- Rules: 6 -> 6 (+0 learned)
- Stored rule hits: 6
- Time: 43s
- Log: logs/learn_20260429_123542.log

---
## Learning Loop -- 2026-04-29 12:37

- Split: training, Tasks: 20
- Correct: 6 / 20 (30.0%)
- Rules: 6 -> 6 (+0 learned)
- Stored rule hits: 6
- Time: 43s
- Log: logs/learn_20260429_123633.log

---
## Learning Loop -- 2026-04-29 12:38

- Split: training, Tasks: 20
- Correct: 6 / 20 (30.0%)
- Rules: 6 -> 6 (+0 learned)
- Stored rule hits: 6
- Time: 43s
- Log: logs/learn_20260429_123724.log

---
## Learning Loop -- 2026-04-29 12:38

- Split: training, Tasks: 20
- Correct: 6 / 20 (30.0%)
- Rules: 6 -> 6 (+0 learned)
- Stored rule hits: 6
- Time: 43s
- Log: logs/learn_20260429_123815.log

---
## Learning Loop -- 2026-04-29 12:39

- Split: training, Tasks: 20
- Correct: 6 / 20 (30.0%)
- Rules: 6 -> 6 (+0 learned)
- Stored rule hits: 6
- Time: 42s
- Log: logs/learn_20260429_123906.log

---
## Learning Loop -- 2026-04-29 12:40

- Split: training, Tasks: 20
- Correct: 6 / 20 (30.0%)
- Rules: 6 -> 6 (+0 learned)
- Stored rule hits: 6
- Time: 42s
- Log: logs/learn_20260429_123957.log

---
## Learning Loop -- 2026-04-29 12:41

- Split: training, Tasks: 20
- Correct: 6 / 20 (30.0%)
- Rules: 6 -> 6 (+0 learned)
- Stored rule hits: 6
- Time: 43s
- Log: logs/learn_20260429_124049.log

---
## Learning Loop -- 2026-04-29 12:42

- Split: training, Tasks: 20
- Correct: 6 / 20 (30.0%)
- Rules: 6 -> 6 (+0 learned)
- Stored rule hits: 6
- Time: 42s
- Log: logs/learn_20260429_124140.log

---
## Learning Loop -- 2026-04-29 12:43

- Split: training, Tasks: 20
- Correct: 6 / 20 (30.0%)
- Rules: 6 -> 6 (+0 learned)
- Stored rule hits: 6
- Time: 43s
- Log: logs/learn_20260429_124231.log

---
## Learning Loop -- 2026-04-29 12:44

- Split: training, Tasks: 20
- Correct: 6 / 20 (30.0%)
- Rules: 6 -> 6 (+0 learned)
- Stored rule hits: 6
- Time: 43s
- Log: logs/learn_20260429_124322.log

---
## Learning Loop -- 2026-04-29 12:44

- Split: training, Tasks: 20
- Correct: 6 / 20 (30.0%)
- Rules: 6 -> 6 (+0 learned)
- Stored rule hits: 6
- Time: 43s
- Log: logs/learn_20260429_124414.log

---
## Learning Loop -- 2026-04-29 12:45

- Split: training, Tasks: 20
- Correct: 6 / 20 (30.0%)
- Rules: 6 -> 6 (+0 learned)
- Stored rule hits: 6
- Time: 43s
- Log: logs/learn_20260429_124505.log

---
## Learning Loop -- 2026-04-29 12:46

- Split: training, Tasks: 20
- Correct: 6 / 20 (30.0%)
- Rules: 6 -> 6 (+0 learned)
- Stored rule hits: 6
- Time: 43s
- Log: logs/learn_20260429_124557.log

---
## Learning Loop -- 2026-04-29 12:47

- Split: training, Tasks: 20
- Correct: 6 / 20 (30.0%)
- Rules: 6 -> 6 (+0 learned)
- Stored rule hits: 6
- Time: 43s
- Log: logs/learn_20260429_124648.log

---
## Learning Loop -- 2026-04-29 12:48

- Split: training, Tasks: 20
- Correct: 6 / 20 (30.0%)
- Rules: 6 -> 6 (+0 learned)
- Stored rule hits: 6
- Time: 43s
- Log: logs/learn_20260429_124740.log

---
## Learning Loop -- 2026-04-29 12:49

- Split: training, Tasks: 20
- Correct: 6 / 20 (30.0%)
- Rules: 6 -> 6 (+0 learned)
- Stored rule hits: 6
- Time: 43s
- Log: logs/learn_20260429_124831.log

---
## Learning Loop -- 2026-04-29 12:50

- Split: training, Tasks: 20
- Correct: 6 / 20 (30.0%)
- Rules: 6 -> 6 (+0 learned)
- Stored rule hits: 6
- Time: 43s
- Log: logs/learn_20260429_124922.log

---
## Learning Loop -- 2026-04-29 12:50

- Split: training, Tasks: 20
- Correct: 6 / 20 (30.0%)
- Rules: 6 -> 6 (+0 learned)
- Stored rule hits: 6
- Time: 43s
- Log: logs/learn_20260429_125014.log

---
## Learning Loop -- 2026-04-29 12:51

- Split: training, Tasks: 20
- Correct: 6 / 20 (30.0%)
- Rules: 6 -> 6 (+0 learned)
- Stored rule hits: 6
- Time: 42s
- Log: logs/learn_20260429_125105.log

---
## Learning Loop -- 2026-04-29 12:52

- Split: training, Tasks: 20
- Correct: 6 / 20 (30.0%)
- Rules: 6 -> 6 (+0 learned)
- Stored rule hits: 6
- Time: 43s
- Log: logs/learn_20260429_125156.log

---
## Learning Loop -- 2026-04-29 12:53

- Split: training, Tasks: 20
- Correct: 6 / 20 (30.0%)
- Rules: 6 -> 6 (+0 learned)
- Stored rule hits: 6
- Time: 43s
- Log: logs/learn_20260429_125247.log

---
## Learning Loop -- 2026-04-29 12:54

- Split: training, Tasks: 20
- Correct: 6 / 20 (30.0%)
- Rules: 6 -> 6 (+0 learned)
- Stored rule hits: 6
- Time: 42s
- Log: logs/learn_20260429_125339.log

---
## Learning Loop -- 2026-04-29 12:55

- Split: training, Tasks: 20
- Correct: 6 / 20 (30.0%)
- Rules: 6 -> 6 (+0 learned)
- Stored rule hits: 6
- Time: 43s
- Log: logs/learn_20260429_125430.log

---
## Learning Loop -- 2026-04-29 12:56

- Split: training, Tasks: 20
- Correct: 6 / 20 (30.0%)
- Rules: 6 -> 6 (+0 learned)
- Stored rule hits: 6
- Time: 43s
- Log: logs/learn_20260429_125521.log

---
## Learning Loop -- 2026-04-29 12:56

- Split: training, Tasks: 20
- Correct: 6 / 20 (30.0%)
- Rules: 6 -> 6 (+0 learned)
- Stored rule hits: 6
- Time: 43s
- Log: logs/learn_20260429_125612.log

---
## Learning Loop -- 2026-04-29 12:57

- Split: training, Tasks: 20
- Correct: 6 / 20 (30.0%)
- Rules: 6 -> 6 (+0 learned)
- Stored rule hits: 6
- Time: 43s
- Log: logs/learn_20260429_125704.log

---
## Learning Loop -- 2026-04-29 12:58

- Split: training, Tasks: 20
- Correct: 6 / 20 (30.0%)
- Rules: 6 -> 6 (+0 learned)
- Stored rule hits: 6
- Time: 42s
- Log: logs/learn_20260429_125755.log

---
## Learning Loop -- 2026-04-29 12:59

- Split: training, Tasks: 20
- Correct: 6 / 20 (30.0%)
- Rules: 6 -> 6 (+0 learned)
- Stored rule hits: 6
- Time: 42s
- Log: logs/learn_20260429_125846.log

---
## Learning Loop -- 2026-04-29 13:00

- Split: training, Tasks: 20
- Correct: 6 / 20 (30.0%)
- Rules: 6 -> 6 (+0 learned)
- Stored rule hits: 6
- Time: 42s
- Log: logs/learn_20260429_125937.log

---
## Learning Loop -- 2026-04-29 13:01

- Split: training, Tasks: 20
- Correct: 6 / 20 (30.0%)
- Rules: 6 -> 6 (+0 learned)
- Stored rule hits: 6
- Time: 43s
- Log: logs/learn_20260429_130028.log

---
## Learning Loop -- 2026-04-29 13:02

- Split: training, Tasks: 20
- Correct: 6 / 20 (30.0%)
- Rules: 6 -> 6 (+0 learned)
- Stored rule hits: 6
- Time: 43s
- Log: logs/learn_20260429_130120.log

---
## Learning Loop -- 2026-04-29 13:02

- Split: training, Tasks: 20
- Correct: 6 / 20 (30.0%)
- Rules: 6 -> 6 (+0 learned)
- Stored rule hits: 6
- Time: 43s
- Log: logs/learn_20260429_130211.log

---
## Learning Loop -- 2026-04-29 13:03

- Split: training, Tasks: 20
- Correct: 6 / 20 (30.0%)
- Rules: 6 -> 6 (+0 learned)
- Stored rule hits: 6
- Time: 43s
- Log: logs/learn_20260429_130303.log

---
## Learning Loop -- 2026-04-29 13:04

- Split: training, Tasks: 20
- Correct: 6 / 20 (30.0%)
- Rules: 6 -> 6 (+0 learned)
- Stored rule hits: 6
- Time: 43s
- Log: logs/learn_20260429_130355.log

---
## Learning Loop -- 2026-04-29 13:05

- Split: training, Tasks: 20
- Correct: 6 / 20 (30.0%)
- Rules: 6 -> 6 (+0 learned)
- Stored rule hits: 6
- Time: 43s
- Log: logs/learn_20260429_130446.log

---
## Learning Loop -- 2026-04-29 13:06

- Split: training, Tasks: 20
- Correct: 6 / 20 (30.0%)
- Rules: 6 -> 6 (+0 learned)
- Stored rule hits: 6
- Time: 43s
- Log: logs/learn_20260429_130538.log

---
## Learning Loop -- 2026-04-29 13:07

- Split: training, Tasks: 20
- Correct: 6 / 20 (30.0%)
- Rules: 6 -> 6 (+0 learned)
- Stored rule hits: 6
- Time: 42s
- Log: logs/learn_20260429_130630.log

---
## Learning Loop -- 2026-04-29 13:08

- Split: training, Tasks: 20
- Correct: 6 / 20 (30.0%)
- Rules: 6 -> 6 (+0 learned)
- Stored rule hits: 6
- Time: 42s
- Log: logs/learn_20260429_130721.log

---
## Learning Loop -- 2026-04-29 13:08

- Split: training, Tasks: 20
- Correct: 6 / 20 (30.0%)
- Rules: 6 -> 6 (+0 learned)
- Stored rule hits: 6
- Time: 43s
- Log: logs/learn_20260429_130812.log

---
## Learning Loop -- 2026-04-29 13:09

- Split: training, Tasks: 20
- Correct: 6 / 20 (30.0%)
- Rules: 6 -> 6 (+0 learned)
- Stored rule hits: 6
- Time: 43s
- Log: logs/learn_20260429_130904.log

---
## Learning Loop -- 2026-04-29 13:10

- Split: training, Tasks: 20
- Correct: 6 / 20 (30.0%)
- Rules: 6 -> 6 (+0 learned)
- Stored rule hits: 6
- Time: 42s
- Log: logs/learn_20260429_130955.log

---
## Learning Loop -- 2026-04-29 13:11

- Split: training, Tasks: 20
- Correct: 6 / 20 (30.0%)
- Rules: 6 -> 6 (+0 learned)
- Stored rule hits: 6
- Time: 43s
- Log: logs/learn_20260429_131046.log

---
## Learning Loop -- 2026-04-29 13:12

- Split: training, Tasks: 20
- Correct: 6 / 20 (30.0%)
- Rules: 6 -> 6 (+0 learned)
- Stored rule hits: 6
- Time: 42s
- Log: logs/learn_20260429_131137.log

---
## Learning Loop -- 2026-04-29 13:13

- Split: training, Tasks: 20
- Correct: 6 / 20 (30.0%)
- Rules: 6 -> 6 (+0 learned)
- Stored rule hits: 6
- Time: 42s
- Log: logs/learn_20260429_131228.log

---
## Learning Loop -- 2026-04-29 13:14

- Split: training, Tasks: 20
- Correct: 6 / 20 (30.0%)
- Rules: 6 -> 6 (+0 learned)
- Stored rule hits: 6
- Time: 42s
- Log: logs/learn_20260429_131320.log

---
## Learning Loop -- 2026-04-29 13:14

- Split: training, Tasks: 20
- Correct: 6 / 20 (30.0%)
- Rules: 6 -> 6 (+0 learned)
- Stored rule hits: 6
- Time: 42s
- Log: logs/learn_20260429_131411.log

---
## Learning Loop -- 2026-04-29 13:15

- Split: training, Tasks: 20
- Correct: 6 / 20 (30.0%)
- Rules: 6 -> 6 (+0 learned)
- Stored rule hits: 6
- Time: 44s
- Log: logs/learn_20260429_131502.log

---
## Learning Loop -- 2026-04-29 13:16

- Split: training, Tasks: 20
- Correct: 6 / 20 (30.0%)
- Rules: 6 -> 6 (+0 learned)
- Stored rule hits: 6
- Time: 40s
- Log: logs/learn_20260429_131555.log

---
## Learning Loop -- 2026-04-29 13:17

- Split: training, Tasks: 20
- Correct: 6 / 20 (30.0%)
- Rules: 6 -> 6 (+0 learned)
- Stored rule hits: 6
- Time: 38s
- Log: logs/learn_20260429_131643.log

---
## Learning Loop -- 2026-04-29 13:18

- Split: training, Tasks: 20
- Correct: 6 / 20 (30.0%)
- Rules: 6 -> 6 (+0 learned)
- Stored rule hits: 6
- Time: 37s
- Log: logs/learn_20260429_131729.log

---
## Learning Loop -- 2026-04-29 13:18

- Split: training, Tasks: 20
- Correct: 6 / 20 (30.0%)
- Rules: 6 -> 6 (+0 learned)
- Stored rule hits: 6
- Time: 37s
- Log: logs/learn_20260429_131815.log

---
## Learning Loop -- 2026-04-29 13:19

- Split: training, Tasks: 20
- Correct: 6 / 20 (30.0%)
- Rules: 6 -> 6 (+0 learned)
- Stored rule hits: 6
- Time: 38s
- Log: logs/learn_20260429_131900.log

---
## Learning Loop -- 2026-04-29 13:20

- Split: training, Tasks: 20
- Correct: 6 / 20 (30.0%)
- Rules: 6 -> 6 (+0 learned)
- Stored rule hits: 6
- Time: 38s
- Log: logs/learn_20260429_131946.log

---
## Learning Loop -- 2026-04-29 13:21

- Split: training, Tasks: 20
- Correct: 6 / 20 (30.0%)
- Rules: 6 -> 6 (+0 learned)
- Stored rule hits: 6
- Time: 38s
- Log: logs/learn_20260429_132032.log

---
## Learning Loop -- 2026-04-29 13:21

- Split: training, Tasks: 20
- Correct: 6 / 20 (30.0%)
- Rules: 6 -> 6 (+0 learned)
- Stored rule hits: 6
- Time: 37s
- Log: logs/learn_20260429_132118.log

---
## Learning Loop -- 2026-04-29 13:22

- Split: training, Tasks: 20
- Correct: 6 / 20 (30.0%)
- Rules: 6 -> 6 (+0 learned)
- Stored rule hits: 6
- Time: 37s
- Log: logs/learn_20260429_132204.log

---
## Learning Loop -- 2026-04-29 13:23

- Split: training, Tasks: 20
- Correct: 6 / 20 (30.0%)
- Rules: 6 -> 6 (+0 learned)
- Stored rule hits: 6
- Time: 37s
- Log: logs/learn_20260429_132249.log

---
## Learning Loop -- 2026-04-29 13:24

- Split: training, Tasks: 20
- Correct: 6 / 20 (30.0%)
- Rules: 6 -> 6 (+0 learned)
- Stored rule hits: 6
- Time: 37s
- Log: logs/learn_20260429_132335.log

---
## Learning Loop -- 2026-04-29 13:24

- Split: training, Tasks: 20
- Correct: 6 / 20 (30.0%)
- Rules: 6 -> 6 (+0 learned)
- Stored rule hits: 6
- Time: 37s
- Log: logs/learn_20260429_132420.log

---
## Learning Loop -- 2026-04-29 13:25

- Split: training, Tasks: 20
- Correct: 6 / 20 (30.0%)
- Rules: 6 -> 6 (+0 learned)
- Stored rule hits: 6
- Time: 37s
- Log: logs/learn_20260429_132507.log

---
## Learning Loop -- 2026-04-29 13:26

- Split: training, Tasks: 20
- Correct: 6 / 20 (30.0%)
- Rules: 6 -> 6 (+0 learned)
- Stored rule hits: 6
- Time: 37s
- Log: logs/learn_20260429_132552.log

---
## Learning Loop -- 2026-04-29 13:27

- Split: training, Tasks: 20
- Correct: 6 / 20 (30.0%)
- Rules: 6 -> 6 (+0 learned)
- Stored rule hits: 6
- Time: 38s
- Log: logs/learn_20260429_132638.log

---
## Learning Loop -- 2026-04-29 13:28

- Split: training, Tasks: 20
- Correct: 6 / 20 (30.0%)
- Rules: 6 -> 6 (+0 learned)
- Stored rule hits: 6
- Time: 37s
- Log: logs/learn_20260429_132724.log

---
## Learning Loop -- 2026-04-29 13:28

- Split: training, Tasks: 20
- Correct: 6 / 20 (30.0%)
- Rules: 6 -> 6 (+0 learned)
- Stored rule hits: 6
- Time: 37s
- Log: logs/learn_20260429_132809.log

---
## Learning Loop -- 2026-04-29 13:29

- Split: training, Tasks: 20
- Correct: 6 / 20 (30.0%)
- Rules: 6 -> 6 (+0 learned)
- Stored rule hits: 6
- Time: 37s
- Log: logs/learn_20260429_132855.log

---
## Learning Loop -- 2026-04-29 13:30

- Split: training, Tasks: 20
- Correct: 6 / 20 (30.0%)
- Rules: 6 -> 6 (+0 learned)
- Stored rule hits: 6
- Time: 37s
- Log: logs/learn_20260429_132940.log

---
## Learning Loop -- 2026-04-29 13:31

- Split: training, Tasks: 20
- Correct: 6 / 20 (30.0%)
- Rules: 6 -> 6 (+0 learned)
- Stored rule hits: 6
- Time: 37s
- Log: logs/learn_20260429_133026.log

---
## Learning Loop -- 2026-04-29 13:31

- Split: training, Tasks: 20
- Correct: 6 / 20 (30.0%)
- Rules: 6 -> 6 (+0 learned)
- Stored rule hits: 6
- Time: 38s
- Log: logs/learn_20260429_133112.log

---
## Learning Loop -- 2026-04-29 13:32

- Split: training, Tasks: 20
- Correct: 6 / 20 (30.0%)
- Rules: 6 -> 6 (+0 learned)
- Stored rule hits: 6
- Time: 37s
- Log: logs/learn_20260429_133158.log
