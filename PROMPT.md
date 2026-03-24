# SOAR-ARC -- Mission

## Goal

Improve the SOAR agent to solve as many ARC tasks as possible.

The agent uses a purely symbolic SOAR cognitive architecture. It discovers
transformation rules from example pairs and applies them to test inputs.
Learned rules accumulate in `procedural_memory/` across tasks.

The infinite loop (`run_loop.sh`) feeds tasks to the agent, then invokes
Claude Code to analyze failures and add new generalization strategies.

## Architecture

See **CLAUDE.md** for the full architecture, file structure, operator
pipeline, and design constraints. CLAUDE.md is the authoritative reference.

## Design Principles (non-negotiable)

- **Purely symbolic** -- no neural networks, no embeddings, no ML
- **SOAR is the only solver** -- no fallback engines or heuristics
- **Knowledge as relations** -- store why (relations), not how (programs)
- **Failure is information** -- impasses reveal what knowledge is missing
- **Memory-based learning** -- the agent reuses rules it discovered earlier

## What Claude Code Should Do Each Session

1. Read the learning loop output (which tasks passed/failed, what rules exist)
2. Pick failing tasks and read their JSON data
3. Understand the transformation pattern each task requires
4. Add generalization strategies to `agent/active_operators.py`:
   - `GeneralizeOperator._try_*()` -- detect the pattern from extracted diffs
   - `PredictOperator._apply_*()` -- apply the rule to produce output
5. Each strategy must handle a **category** of tasks, not a single task
6. Verify: `python run_task.py` must still output CORRECT
7. Append session results to `logs/session_log.md`

## Do NOT Modify

- `data/` -- ARC dataset (read-only)
- `agent/cycle.py` -- SOAR decision cycle
- `agent/wm.py` -- WorkingMemory

## Entry Point

```bash
./run_loop.sh
```
