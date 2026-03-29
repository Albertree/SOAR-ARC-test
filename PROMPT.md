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

## Rule Architecture

Rules are **standalone Python modules** in `procedural_memory/base_rules/<category>/`.
The rule engine (`agent/rule_engine.py`) auto-discovers them at runtime.

Each rule module has this interface:
```python
"""<name> — one-line description."""
from procedural_memory.base_rules._helpers import <needed_helpers>

RULE_TYPE = "<name>"
CATEGORY = "<category>"

def try_rule(patterns, task):
    """Returns rule dict or None."""
    ...

def apply_rule(rule, input_grid):
    """Returns grid (list-of-lists) or None."""
    ...
```

Categories: `color/`, `geometry/`, `fill/`, `structure/`, `connect/`, `separator/`, `detect/`

Shared helpers live in `procedural_memory/base_rules/_helpers.py`.

After creating a new rule, add its RULE_TYPE to `WATERFALL_ORDER` in
`agent/rule_engine.py` at the appropriate priority position.

## What Claude Code Should Do Each Session

1. Read the learning loop output (which tasks passed/failed, what rules exist)
2. Pick failing tasks and read their JSON data
3. Understand the transformation pattern each task requires
4. Create new rule modules in `procedural_memory/base_rules/<category>/<name>.py`:
   - `try_rule(patterns, task)` -- detect the pattern from extracted diffs
   - `apply_rule(rule, input_grid)` -- apply the rule to produce output
5. Add the new rule's RULE_TYPE to `WATERFALL_ORDER` in `agent/rule_engine.py`
6. Each strategy must handle a **category** of tasks, not a single task
7. Use helpers from `_helpers.py` or add new shared helpers there
8. Verify: `python run_task.py` must still output CORRECT
9. Append session results to `logs/session_log.md`

## Do NOT Modify

- `data/` -- ARC dataset (read-only)
- `agent/cycle.py` -- SOAR decision cycle
- `agent/wm.py` -- WorkingMemory
- `agent/active_operators.py` -- operators (delegates to rule engine)

## Entry Point

```bash
./run_loop.sh
```
