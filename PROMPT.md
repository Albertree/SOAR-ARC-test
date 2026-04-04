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
- **Structure Mapping Theory** -- all matching uses ARCKG COMM/DIFF, not raw cell diffs

## Concept Architecture (PREFERRED)

Concepts are **parameterized JSON definitions** in `procedural_memory/concepts/`.
Each concept composes primitives from `_primitives.py` with inferred parameters.

```json
{
  "concept_id": "<name>",
  "version": 1,
  "description": "One-line description",
  "signature": {"grid_size_preserved": true, "requires_content_diff": true},
  "parameters": {"param": {"type": "int", "infer": "method_name"}},
  "steps": [
    {"id": "s1", "primitive": "fn", "args": {"grid": "$input"}, "output": "result"}
  ],
  "result": "$result"
}
```

Concepts are matched using ARCKG COMM/DIFF structures, parameters inferred
from relational graphs, and validated by execution against example pairs.

Available primitives: `procedural_memory/base_rules/_primitives.py`
Available inference methods: `procedural_memory/base_rules/_concept_engine.py`

## Rule Module Architecture (FALLBACK)

For complex procedural logic (pathfinding, simulation) that can't be expressed
as primitive compositions, create Python modules in `base_rules/<category>/`.

## What Claude Code Should Do Each Session

1. Read the learning loop output (which tasks passed/failed)
2. Pick failing tasks and read their JSON data
3. Understand the transformation pattern each task requires
4. PREFERRED: Create concept JSONs in `procedural_memory/concepts/`
   - Compose primitives, use inference methods, parameterize variations
   - Each concept must handle a **category** of tasks, not just one
   - Do NOT hardcode task-specific colors or positions
5. FALLBACK: Create Python rule modules for complex procedural logic
6. Do NOT modify `_primitives.py` (frozen). Add inference methods to `_concept_engine.py` as needed.
7. Verify: `python run_task.py` must still output CORRECT
8. Append session results to `logs/session_log.md`

## Do NOT Modify

- `data/` -- ARC dataset (read-only)
- `agent/cycle.py` -- SOAR decision cycle
- `agent/wm.py` -- WorkingMemory
- `agent/active_operators.py` -- operators (delegates to rule engine)

## Entry Point

```bash
./run_loop.sh
```
