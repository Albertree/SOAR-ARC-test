# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

ARCKG -- a purely symbolic AI system that solves ARC (Abstraction and Reasoning Corpus) tasks using a hierarchical knowledge graph and SOAR cognitive architecture as the sole solver. No neural networks. No external dependencies.

## Entry Point

```bash
./run_loop.sh                  # the infinite improvement loop (the only command)
```

This runs the SOAR agent on ARC tasks, then invokes Claude Code to improve the agent, then repeats. Learned rules accumulate in `procedural_memory/`.

## Do NOT Modify

- `data/` -- ARC dataset (read-only)
- `agent/cycle.py` -- SOAR decision cycle engine
- `agent/wm.py` -- WorkingMemory

## SOAR Decision Cycle

```
Elaborate -> Propose -> Select -> Apply (repeat until goal satisfied)
```

The cycle alternates between S1 and S2:
1. **S1**: `solve-task` fires, intentionally no WM change -> no-change impasse -> push S2
2. **S2**: Pipeline operator fires, writes results to `wm.s1` -> pop S2
3. Back to S1, repeat until goal satisfied

All pipeline state lives in `wm.s1` so it persists across S2 pop/push cycles.

## Operator Pipeline (`agent/active_operators.py`)

```
solve-task (S1, abstract) -> select_target -> compare -> extract_pattern ->
                              generalize -> predict -> submit (all in S2)
```

| Operator | Writes to S1 |
|----------|-------------|
| `select_target` | comparison-agenda, pending-comparisons |
| `compare` | comparisons (one per cycle via ARCKG compare()) |
| `extract_pattern` | patterns (cell-level diff analysis) |
| `generalize` | active-rules (transformation rules) |
| `predict` | predictions (test output grids) |
| `submit` | output-link, goal satisfied |

## Elaboration Rules (`agent/elaboration_rules.py`)

Each rule checks S1 state, derives one flag into S2:
- `needs_target_selection` -- no comparison-agenda yet
- `has_pending_comparison` -- pending-comparisons not empty
- `ready_for_pattern_extraction` -- all compared, no patterns
- `ready_for_generalization` -- patterns exist, no rules
- `ready_for_prediction` -- rules exist, no predictions
- `all_outputs_found` -- predictions for all test pairs

## Production Rules (`agent/rules.py`)

Each fires at depth > 0 (S2 only), checks one elaboration flag. Selection is deterministic via `PREFERENCE_ORDER` in `preferences.py`.

## Memory-Based Learning

The agent accumulates rules across tasks:
1. Before solving: `ActiveSoarAgent` loads stored rules from `procedural_memory/`
2. Tries each stored rule against example pairs (fast path)
3. If none match: runs full SOAR pipeline (slow path)
4. After solving: saves newly discovered rules to `procedural_memory/`

Files:
- `agent/active_agent.py` -- `ActiveSoarAgent.solve()` with memory integration
- `agent/memory.py` -- save/load rules as JSON in `procedural_memory/`

## Rule Engine (`agent/rule_engine.py`)

Rules are **standalone Python modules** in `procedural_memory/base_rules/<category>/`.
The rule engine auto-discovers them at runtime via `importlib`.

- `WATERFALL_ORDER` in `rule_engine.py` controls evaluation priority (first match wins)
- `try_all(patterns, task)` -- iterate rules in order, return first match
- `apply(rule_type, rule, input_grid)` -- look up and call the right `apply_rule()`
- New rules dropped into `base_rules/` are auto-discovered on next load

## How to Add Generalization Strategies (the main improvement target)

### PREFERRED: Create a Concept JSON (parameterized, composable)

Create `procedural_memory/concepts/<name>.json`:

```json
{
  "concept_id": "<name>",
  "version": 1,
  "description": "One-line description",
  "signature": {
    "grid_size_preserved": true,
    "size_ratio": null,
    "color_preserved": null,
    "requires_content_diff": true,
    "input_constraints": []
  },
  "parameters": {
    "param_name": {"type": "int|color|color_map|position|str", "infer": "method_name"}
  },
  "steps": [
    {"id": "s1", "primitive": "fn_name", "args": {"grid": "$input", "param": "$param_name"}, "output": "result"}
  ],
  "result": "$result"
}
```

Available primitives (`_primitives.py`): scale, flip_vertical, flip_horizontal, rotate_cw, transpose, gravity, concat_vertical, concat_horizontal, overlay, recolor, fill_region, mask_keep, extract_subgrid, extract_column, extract_row, extract_objects, make_uniform, place_column, place_row, find_bg_color, grid_dimensions, find_separator_lines, count_color, unique_colors. If no existing primitive fits, add a new one to `_primitives.py` then create a concept JSON that uses it.

Available inference methods (`_concept_engine.py`): bg_color, ratio_hw, non_bg_single, color_map_from_arckg, column_index_from_arckg, from_examples

Concept rules use ARCKG COMM/DIFF structures for matching, not raw cell diffs.

### PROHIBITED: Do NOT create Python rule modules

Never create `.py` files in `procedural_memory/base_rules/`. The existing infrastructure files (`_primitives.py`, `_concept_engine.py`, `_helpers.py`) are the only allowed Python in that directory. All rules must be concept JSONs — no exceptions.

### DO NOT:
- Hardcode task-specific colors or positions
- Create one rule per task (that's overfitting)
- Modify `agent/active_operators.py`
- Create `.py` rule files in `procedural_memory/base_rules/` subdirectories

Categories: `color/`, `geometry/`, `fill/`, `structure/`, `connect/`, `separator/`, `detect/`

## ARCKG 5-Level Knowledge Graph (`ARCKG/`)

```
TASK (T{hex})
 -> PAIR (P{n} / Pa for test)
     -> GRID (G0=input, G1=output)
         -> OBJECT (O{n})
             -> PIXEL (X{n})
```

- Node = folder under `semantic_memory/`, Edge = JSON file
- `ARCKG/comparison.py:compare()` -- structural COMM/DIFF comparison
- `ARCKG/hodel.py` -- object detection (connected components)

## File Structure

```
run_loop.sh              <- THE entry point (infinite loop)
run_learn.py             <- internal: agent solves tasks, logs results
run_task.py              <- internal: single task test (regression check)

agent/
  active_operators.py    <- operator implementations (delegates to rule engine)
  rule_engine.py         <- dynamic rule loader (WATERFALL_ORDER here)
  active_agent.py        <- ActiveSoarAgent with memory integration
  elaboration_rules.py   <- pipeline state machine
  rules.py               <- production rules
  preferences.py         <- operator selection priority
  cycle.py               <- SOAR cycle (DO NOT MODIFY)
  wm.py                  <- WorkingMemory (DO NOT MODIFY)
  memory.py              <- save/load rules to procedural_memory/
  operators.py           <- Operator base class
  io.py                  <- I/O link management
  propose_wm.py          <- WM proposal materialization
  wm_logger.py           <- WM triplet display
  agent_common.py        <- goal checking helpers

ARCKG/                   <- knowledge graph layer
managers/                <- task loading
arc2_env/                <- evaluation environment
basics/                  <- visualization

data/ARC_AGI/            <- ARC tasks (read-only)
semantic_memory/         <- KG attributes (regenerated per run)
procedural_memory/       <- learned rules (accumulates)
  concepts/              <- concept JSONs (PREFERRED EDIT TARGET)
  base_rules/            <- rule modules (fallback for complex logic)
    _helpers.py          <- shared helper functions
    color/               <- color transformation rules
    geometry/            <- geometric transformation rules
    fill/                <- fill/flood rules
    structure/           <- structural rearrangement rules
    connect/             <- connection/line drawing rules
    separator/           <- separator-based rules
    detect/              <- detection/extraction rules
episodic_memory/         <- solution episodes (future use)
logs/                    <- session logs
```

## Design Constraints

- SOAR is the only solver -- no synthesis engines, no neural networks
- Knowledge stored as relations (edges), not programs
- WM content as `(identifier ^attribute value)` triplets
- `SolveTaskOperator` intentionally makes no WM change (triggers impasse)
- `run_task.py` on task 08ed6ac7 must always output CORRECT (regression gate)
