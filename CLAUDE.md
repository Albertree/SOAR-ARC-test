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

## How to Add Generalization Strategies (the main improvement target)

Current strategies in `GeneralizeOperator`:
- `_try_recolor_sequential` -- objects recolored 1,2,3,... by position
- `_try_color_mapping` -- each input color maps to one output color
- Fallback: `identity` (copy input)

To add a new strategy:
1. Add `_try_<name>(self, patterns)` in `GeneralizeOperator` -- returns a rule dict or None
2. Add `_apply_<name>(self, rule, input_grid)` in `PredictOperator` -- returns predicted grid
3. Call `_try_<name>` from `GeneralizeOperator.effect()` in priority order

The `patterns` dict contains per-pair cell-level analysis: changed cells grouped into connected components with input/output colors and positions.

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
  active_operators.py    <- operator implementations (MAIN EDIT TARGET)
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
episodic_memory/         <- solution episodes (future use)
logs/                    <- session logs
```

## Design Constraints

- SOAR is the only solver -- no synthesis engines, no neural networks
- Knowledge stored as relations (edges), not programs
- WM content as `(identifier ^attribute value)` triplets
- `SolveTaskOperator` intentionally makes no WM change (triggers impasse)
- `run_task.py` on task 08ed6ac7 must always output CORRECT (regression gate)
