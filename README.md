# ARCKG — ARC Knowledge Graph Solver

A purely symbolic AI system that solves ARC (Abstraction and Reasoning Corpus) tasks.
It builds a hierarchical knowledge graph and operates SOAR cognitive architecture as the sole solver.

---

## Core Philosophy

- **Purely symbolic** — no neural networks in the knowledge layer
- **Knowledge is stored as relations (why)**, not programs (how)
- **Failure (impasse) is information** — it reveals what is missing
- **SOAR is the only solver** — no separate program synthesis engine

---

## Execution

```bash
# Full benchmark
python main.py

# Single task experiment (for error tracking)
python run_task.py
```

---

## Module Structure

```
ARC-solver2/
│
├── main.py                  ← Single entry point
├── run_task.py              ← Single task experiment script
│
├── ARCKG/                   ← Knowledge Graph base layer
│   ├── task.py              TASK node   (T{hex})
│   ├── pair.py              PAIR node   (T.P{n})
│   ├── grid.py              GRID node   (T.P.G{n})
│   ├── object.py            OBJECT node (T.P.G.O{n})
│   ├── pixel.py             PIXEL node  (T.P.G.O.X{n})
│   ├── hodel.py             Object detection function (Hodel's objects())
│   ├── comparison.py        compare() — core relation construction function
│   └── memory_paths.py      Node ID → file path conversion
│
├── agent/                   ← SOAR cognitive architecture (sole solver)
│   ├── wm.py                WorkingMemory — WME triplet, S1/S2 state stack
│   ├── elaboration_rules.py ElaborationRule, Elaborator — derived fact generation
│   ├── rules.py             ProductionRule, Proposer — operator candidate proposal
│   ├── operators.py         Operator base class
│   ├── active_operators.py  SelectTarget / Compare / ExtractPattern /
│   │                        Generalize / Predict / Submit
│   ├── preferences.py       select_operator() — PREFERENCE_ORDER-based selection
│   ├── cycle.py             run_cycle() — Elaborate→Propose→Select→Apply loop
│   ├── agent_common.py      build_wm_from_task / goal_satisfied / answers_from_wm
│   ├── memory.py            chunk_from_substate / LTM save/load
│   └── active_agent.py      ActiveSoarAgent — env-compatible agent interface
│
├── env/                     ← Evaluation environment
│   └── arc_environment.py   ARCEnvironment — task provision, scoring, trace
│
├── managers/
│   └── arc_manager.py       ARCManager — data/ load → ARCKG node hierarchy construction
│
├── program/
│   └── anti_unification.py  Relation trace → abstract rule generalization
│
├── procedural_memory/DSL/   ← DSL tools (for internal operator calls)
│   ├── apply.py             apply_DSL() dispatcher
│   ├── transformation.py    Grid/object transformation functions
│   ├── selection.py         find_object()
│   ├── util.py              Helpers
│   └── layer.py             90×90 canvas layer system
│
├── basics/
│   ├── viz.py               ANSI color visualization (show_task / show_objects / show_comparison)
│   └── utils.py             Miscellaneous utilities
│
├── data/                    ← symlink → ../ARC-solver/data (read-only)
├── semantic_memory/         ← STORAGE: KG node attributes + comparison edges (JSON)
├── episodic_memory/         ← STORAGE: Per-task solution episodes
└── inspect.py               ← Interactive debugging script
```

---

## Knowledge Graph Structure

### 5-Level Node Hierarchy

```
TASK (T{hex})
 └── PAIR (P{n} / Pa,Pb,...  for test)
      └── GRID (G0=input, G1=output)
           └── OBJECT (O{n})
                └── PIXEL (X{n})
```

### Node = Folder, Edge = JSON File

```
semantic_memory/
  N_T{hex}/
    E_T{hex}.json          ← 0th-order: TASK attributes
    E_P0G0-P0G1.json       ← 1st-order: G0 vs G1 comparison
    E_(E_...)-(...).json   ← 2nd-order: comparison between relations
    N_T{hex}.P0/
      E_P0.json            ← PAIR attributes
      E_P0G0.json          ← GRID attributes
      ...
```

### Relation Result Format

```json
{
  "id1": "T08ed6ac7.P0.G0",
  "id2": "T08ed6ac7.P0.G1",
  "lca_node_id": "T08ed6ac7.P0",
  "order": 1,
  "result": {
    "type": "COMM | DIFF",
    "score": "2/3",
    "category": { ... }
  }
}
```

---

## SOAR Decision Cycle

```
Each cycle:
  1. Elaborate  — Repeat ElaborationRules until fixed-point
                  → Fill wm.elaborated
  2. Propose    — ProductionRules read elaborated and collect operator candidates
  3. Select     — Choose one based on PREFERENCE_ORDER
  4. Apply      — Call operator.effect(wm) → Add new facts to WM (or no change)

  Impasse conditions:
    - No candidates (no_candidates) → create substate
    - Operator failure (exception, etc.) → create substate
    - No WM change from operator application at root state (no-change) → create substate

  MAX_SUBSTATE_DEPTH = 2
```

> In this implementation, operator success/failure/no-change is not stored in WM slots (`^op_status`).
> Instead, impasses are triggered within the cycle based only on `changed / no_change / failure` determination.


### Operator Flow

```
SelectTarget → Compare → ExtractPattern → Generalize → Predict → Submit
(from agenda   (relation  (COMM→invariant  (abstract    (test output  (goal
to pending)    creation)  DIFF→diff_pattern) rule         prediction)  complete)
                                            create/save)
```

---

## Environment Interface

```python
env = ARCEnvironment(task_list=["08ed6ac7"], time_budget_sec=300)
agent = ActiveSoarAgent(semantic_memory_root="semantic_memory")
results = env.run_benchmark(agent)
# → {"correct": int, "total": int, "results": list, "trace": list}
```

- `agent.solve(task)` → `list[list[list[int]]]` (output grids, one per test pair)
- `agent.can_retry` → `bool` (max 3 submissions)
- reward: 1.0 = all correct, 0.0 = any wrong (no partial credit)

---

## Data

```bash
ln -s ../ARC-solver/data ./data   # Create symbolic link once
```

`data/` is read-only. Never modify it.

---

## Implementation Status

| Layer | File | Status |
|-------|------|--------|
| ARCKG base layer | ARCKG/*.py | Done |
| DSL tools | procedural_memory/DSL/*.py | Done |
| Load/manage | managers/arc_manager.py | Done |
| Evaluation env | env/arc_environment.py | Done |
| SOAR structure | agent/*.py | Skeleton complete |
| SOAR logic | agent/wm.py etc. | Partially implemented (cycle/propose/preference sorting, etc.) |
| Entry point | main.py | Done |

---

## SOAR WM Notation Conventions (state, operator, preference)

### State Identifiers and Common Attributes

- Root state: `S1`
- Substates: `S2`, `S3`, ...

Basic form:

```text
(S1 ^type state
    ^superstate nil
    ^io I1
    ^smem I4
    ^epmem I5
    ...)
```

- Attribute output order:
  - `type`, `superstate`, `io`, `smem`, `epmem`, then other slots (`goal`, `focus`, `current-task`, `operator`, ...).
- `^io` structure:

```text
(I1 ^input-link I2
    ^output-link I3)
```

Substates (S2, S3, ...) have the following fields as priority:

```text
(S2 ^type state
    ^superstate S1
    ^impasse no-change | failure | no_candidates
    ^choices none | multiple | constraint-failure
    ^attribute operator | ...
    ^quiescence true
    ^smem I6
    ^epmem I7
    [^item ...]
    [^item-count N]
    [^non-numeric ...]
    [^non-numeric-count M])
```

### Operator and Preference Notation

- Operator proposal/selection follows Soar debugger style.

1. **Immediately after proposal (Propose)**:

```text
(S1 ^operator O1 +)
(O1 ^name solve-task
    ^task-id 08ed6ac7
    ^op-preference +)
```

2. **Immediately after selection (Select)**:

```text
(S1 ^operator O1 +)
(S1 ^operator O1)        ; official application WME added without preference
```

- Preference symbols (`+`, `!`, `~`, `-`) are always expressed:
  - at the end of the `^operator` line (`(S1 ^operator O1 +)`)
  - and only via `^op-preference` on the `O1` node,
- Meta-slots like `^proposed_ops`, `^selected_op`, `^op_status` are not placed in WM.

### Operator no-change impasse

- `SolveTaskOperator` is an **abstract operator** that, at S1:
  - is selected when `^current-task` exists,
  - but does not change WM at all within `effect()` (it only represents the abstract "solve task" goal).
- The cycle:
  - compares the length of `wm.wme_records` before and after `effect()`:
    - same → `"no_change"`
    - increased → `"changed"`
    - exception → `"failure"`
  - When `"no_change"` at root state (S1), an **operator no-change impasse** creates `S2`.

A log example looks like this:

```text
[Step 0] After: apply(solve-task)
  (S1 ^type state
      ^superstate nil
      ^io I1
      ^smem I4
      ^epmem I5
      ^current-task 08ed6ac7
      ^operator O1 +
      ^operator O1)
  (O1 ^name solve-task
      ^task-id 08ed6ac7)

[Step 1] After: elaborate
  (S2 ^type state
      ^superstate S1
      ^impasse no-change
      ^choices none
      ^attribute operator
      ^quiescence true
      ^smem I6
      ^epmem I7)
```

At this point, `(S1 ^operator O1 +)` / `(S1 ^operator O1)` on S1 are still maintained.
In the future, once S2 rules actually modify S1's goal/WM, we plan to gradually introduce Soar-style resolution where those changes break matching of parent rules and retract proposals.
