# SOAR-ARC Inner Loop — Claude Code Autonomous Development Instructions

> This file is the only instruction document that Claude Code reads at the start of each session.
> When starting a session, you must read this entire file before proceeding.

---

## Repository

- **GitHub**: https://github.com/Albertree/SOAR-ARC-test.git
- **Local root**: current working directory

---

## Mission (unchanging)

```
Output "CORRECT" when running python run_task.py
```

Target task: `08ed6ac7`
Success = accurately predict the test output grid for this task.

This is the completion criterion for inner loop stage 1.
Improve the code each session until CORRECT is output.

---

## Do NOT Modify Under Any Circumstances

```
data/          ← ARC data source (read-only)
PROMPT.md      ← This file itself
```

All other files may be modified.

---

## Current Implementation Status

### Completed
| Layer | File | Status |
|-------|------|--------|
| ARCKG base layer | `ARCKG/*.py` | Done |
| DSL tools | `procedural_memory/DSL/*.py` | Done |
| Task loading | `managers/arc_manager.py` | Done |
| Evaluation env | `arc2_env/arc_environment.py` | Done |
| SOAR structure | `agent/*.py` | Skeleton complete |
| Entry point | `run_task.py` | Done |

### Incomplete (this is the target of the current mission)
| Layer | Issue |
|-------|-------|
| SOAR operator implementation | `substate-progress` is a placeholder — does nothing |
| WM slots | Core slots like `^focus-level`, `^focus-parent-id` are unused |
| compare integration | `ARCKG/comparison.py`'s `compare()` is not called from the agent loop |
| predict/submit | No logic to write prediction results to the output-link |

---

## System Design Principles

### ARCKG 5-Level Hierarchy

```
TASK (T{hex})
 └── PAIR (P{n} / Pa for test)
      └── GRID (G0=input, G1=output)
           └── OBJECT (O{n})
                └── PIXEL (X{n})
```

- Node = folder, Edge = JSON file
- Relations are lazily generated — `compare()` is called only when needed
- Comparison results are stored under `semantic_memory/`

### SOAR Decision Cycle

```
Each cycle:
  1. Elaborate  — Repeat ElaborationRules until fixed-point
  2. Propose    — ProductionRules collect operator candidates
  3. Select     — Choose one based on PREFERENCE_ORDER
  4. Apply      — Call operator.effect(wm)

Impasse conditions:
  - No WM change (no-change) → create substate
  - Operator failure         → create substate
  - No candidates            → create substate
```

### Operator Design Intent (implementation target)

| Operator | Intent | What to write to WM |
|----------|--------|---------------------|
| `solve-task` | Top-level goal representation. No WM change → trigger no-change impasse | Nothing (intentional) |
| `deepen` | Move focus one level down | `^focus-level`, `^focus-ids` |
| `compare-within-parent` | Compare G0 vs G1 within a single PAIR | `^last-comparison` |
| `compare-siblings` | Compare sibling nodes at the same level (e.g., P0 vs P1) | `^last-comparison` |
| `note-imbalance` | Detect structural imbalance | `^imbalance`, `^imbalance-kind` |
| `extract-invariants` | Extract common patterns from comparison results | `^invariant-chunk` |
| `generalize` | Create abstract rules | Save to `procedural_memory` |
| `predict` | Apply rules to test input | Predicted grid on output-link |
| `submit` | Submit prediction → complete goal | `^goal-satisfied true` |

**Prohibited**: Do not use TASK, PAIR, GRID, OBJECT, PIXEL directly in operator names/docstrings.
Levels are expressed only through the `^focus-level` WM slot value.

---

## How the Agent Solves the Problem (implementation reference)

Below is a concrete exploration flow based on task `08ed6ac7`.
Use this as a reference to implement operators that actually perform this flow.

### Step 1 — Receive TASK
- Load task with `ARCManager` → build ARCKG (already working)
- Inject into WM input-link with `inject_arc_task(task, wm)` (already working)
- `solve-task` operator proposed → no WM change → no-change impasse → S2 created

### Step 2 — Check TASK properties
- `deepen` operator proposed in S2
- Write `^focus-level = "TASK"` to WM
- Read `E_T{hex}.json` to check TASK properties (`number_of_pairs`, etc.)

### Step 3 — Compare with other TASKs in semantic_memory
- On first run, no other TASKs exist → this step can be skipped
- If other TASKs exist in semantic_memory, run `compare-siblings`

### Step 4 — Descend to PAIR level
- TASK properties alone cannot achieve the goal → impasse
- `deepen` → `^focus-level = "PAIR"`
- Check all PAIR properties (`number_of_grids`, example vs test distinction)

### Step 5 — Compare between PAIRs
- `compare-siblings` (P0 vs Pa)
- Result: Pa's grid_count = 1 ≠ P0's grid_count = 2
- `note-imbalance` → `^imbalance-kind = "grid_count"`
- Set goal: make Pa's grid_count = 2 = generate output GRID

### Step 6 — Descend to GRID level
- `deepen` → `^focus-level = "GRID"`
- Compare G0 (input) vs G1 (output) within P0: `compare-within-parent`
- Call `compare()` → generate `E_P0G0-P0G1.json`
- Check GRID property (color, size, contents) differences/commonalities

### Step 7 — Compare with other PAIR GRIDs
- `compare-siblings` (P0G0 vs P1G0, P0G1 vs P1G1)
- Discovery: all GRID sizes identical, inputs share same colors, outputs share same colors
- Conclusion: Pa's output GRID size = example output size, color = example output color
- However, contents cannot be predicted yet → new goal: predict contents

### Step 8 — Descend to OBJECT level
- `deepen` → `^focus-level = "OBJECT"`
- Check all Object properties in P0G0
- Check all Object properties in P0G1
- `compare-within-parent` (P0G0 objects vs P0G1 objects, 1:1 mapping)
- Result: Object with area=9 color=5 → transformed to area=9 color=1 (score 7/8)
- Generate temporary program → apply to P0G0 → compare with P0G1

### Step 9 — Compare OBJECTs from other PAIRs
- Repeat the same process for P1G0, P1G1
- Discovery: color=5 → color=1 pattern exists in P1 as well
- However, criteria for which Object is selected in each PAIR are needed

### Step 10 — Extract Object selection criteria
- Search for common internal relations among transformed Objects in P0G0 and P1G0
- Discovery: transformed Object is the one with the largest area among Objects with the same color
- This becomes the selection criterion → `extract-invariants`
- `^invariant-chunk = "select object where color=X and area=max among siblings"`

### Step 11 — Rule generation
- `generalize` operator
- Rule: "Transform the color of the Object with max area among Objects with color=X to Y"
- X, Y are values extracted from PAIR comparisons

### Step 12 — Apply to test input
- `predict` operator
- Apply rule to Pa's G0 (input only)
- Generate output GRID

### Step 13 — Submit
- `submit` operator
- `^goal-satisfied true`
- `run_task.py` → confirm "CORRECT"

---

## Per-Session Procedure

### At session start

```bash
# 1. Check previous session logs
cat logs/session_log.md | tail -50

# 2. Check current status
python run_task.py

# 3. Analyze errors/output, then set goals for this session
```

### During session

- Implement one operator or rule at a time
- After implementation, always run `python run_task.py` to verify direction
- If errors occur, analyze error messages to identify causes and fix them

### At session end (must follow this order)

```bash
# 1. Final run_task.py execution and capture results
python run_task.py 2>&1 | tee /tmp/session_result.txt

# 2. Write session log (format below)
# Append to logs/session_log.md

# 3. git add & commit & push
git add -A
git commit -m "Session N: <one-line summary>"
git push origin main
```

---

## Session Log Format

**Append** to the file `logs/session_log.md` in the format below.
(Create the file if it does not exist)

```markdown
---
## Session N — YYYY-MM-DD HH:MM

### This session's goal
(What was intended)

### Modified files
- `agent/active_operators.py` — Implemented deepen operator (reason: ...)
- `agent/rules.py` — Added siblings-ready rule (reason: ...)

### run_task.py result
(Paste key parts of execution output)

### Discoveries / Gotchas
(Unexpected findings, caveats, reasons for getting stuck)

### Starting point for next session
(Stopped here, next session should do this)
```

---

## Implementation Priority (refer to when stuck)

1. `agent/active_operators.py` — Implement `DeepenOperator`
   - Lower `^focus-level` WM slot by one step
   - Record list of node IDs at that level in `^focus-ids`

2. `agent/rules.py` — Implement `top-scope-no-detail` rule
   - Condition: no `^focus-level`, `^current-task` exists
   - Propose: `deepen`

3. `agent/active_operators.py` — Implement `CompareWithinParentOperator`
   - Call `compare()` from `ARCKG/comparison.py`
   - Write result to WM `^last-comparison`

4. `agent/active_operators.py` — Implement `CompareSiblingsOperator`
   - Sequentially compare sibling nodes under the same parent

5. `agent/active_operators.py` — Implement `NoteImbalanceOperator`
   - Detect DIFF items from `^last-comparison`
   - Write `^imbalance-kind` to WM

6. `agent/active_operators.py` — Implement `ExtractInvariantsOperator`
   - Extract COMM patterns → `^invariant-chunk`

7. `agent/active_operators.py` — Implement `PredictOperator`
   - Apply invariant + diff patterns to test input

8. `agent/active_operators.py` — Implement `SubmitOperator`
   - Write result to output-link
   - `^goal-satisfied true`

---

## Key File Structure

```
agent/
  cycle.py          ← run_cycle() — modify with caution
  wm.py             ← WorkingMemory — modify with caution
  active_operators.py ← Core implementation target
  rules.py            ← Core implementation target
  elaboration_rules.py← Secondary implementation target
  preferences.py      ← PREFERENCE_ORDER (operator priorities)

ARCKG/
  comparison.py     ← compare() — already complete, just needs to be called
  task.py, pair.py, grid.py, object.py, pixel.py

managers/
  arc_manager.py    ← ARCManager — already complete

run_task.py         ← Success criteria evaluation script (do not modify)
```

---

## Completion Condition

```bash
python run_task.py
# When output contains "CORRECT", inner loop stage 1 is complete
# → Record "MISSION COMPLETE" in logs/session_log.md
# → git push
# → Loop terminated
```
