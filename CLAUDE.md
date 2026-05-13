# CLAUDE.md

This file provides **architectural guidance** for Claude Code when working with this
repository. It describes *what the system is*, not *what task to do*. The current
task lives in `PROMPT.md`.

This document is **authoritative for unchangeable facts**. If you find yourself
needing to violate any rule here to make a task succeed, the rule is correct and
the task is wrong — report it in `logs/session_log.md` rather than bypassing the rule.

---

## 1. System Overview

**ARBOR** = **A**bstraction **R**easoning with **B**ottom-up **O**rganized **R**ules.
A purely symbolic ARC solver built on the **SOAR** cognitive architecture, using a
5-level knowledge graph (**ARCKG**) as semantic memory. No neural networks. No
embeddings. No external ML dependencies.

The complete system specification lives outside this repo in the LLM Wiki
(`~/Desktop/wiki/`) under pages `[[arbor]]`, `[[arbor-modules]]`, and
`[[arckg-3repository]]`. This file extracts the *invariants* needed for safe
code modification.

---

## 2. Repository Layout

```
ARBOR repo (SOAR-ARC-test)
│
├── main.py / run_task.py / run_learn.py / run_1ktasks.py   ← entry points
├── run_loop.sh                                              ← outer loop driver
├── PROMPT.md                                                ← current session task
│
├── ARCKG/                  ← Knowledge Graph base layer
│   ├── task.py             TASK node   (T{hex})
│   ├── pair.py             PAIR node   (T.P{n})
│   ├── grid.py             GRID node   (T.P.G{0|1})
│   ├── object.py           OBJECT node (T.P.G.O{n})
│   ├── pixel.py            PIXEL node  (T.P.G.O.X{n})
│   ├── comparison.py       compare()  — produces COMM/DIFF edges
│   ├── hodel.py            object detection
│   └── memory_paths.py     node id → file path
│
├── agent/                  ← SOAR cognitive architecture (the sole solver)
│   ├── wm.py               WorkingMemory, WME triplets, S1/S2 stack    [FROZEN]
│   ├── cycle.py            run_cycle() Elaborate→Propose→Select→Apply  [FROZEN]
│   ├── elaboration_rules.py   ElaborationRule, Elaborator
│   ├── rules.py            ProductionRule, Proposer
│   ├── preferences.py      select_operator() — PREFERENCE_ORDER
│   ├── operators.py        Operator base class
│   ├── active_operators.py Pipeline operators (see §5)
│   ├── memory.py           save/load LTM, anti-unification trigger (§8)
│   ├── active_agent.py     ActiveSoarAgent — env-facing interface
│   ├── agent_common.py     build_wm_from_task / goal_satisfied / answers_from_wm
│   ├── io.py               input-link / output-link
│   ├── propose_wm.py       WM proposal materialization
│   └── wm_logger.py        WM display (debugging)
│
├── program/
│   └── anti_unification.py unify(programs) — abstract rule extraction
│
├── procedural_memory/
│   ├── DSL/                ← primitive transformation library
│   │   ├── apply.py        apply_DSL() dispatcher
│   │   ├── transformation.py
│   │   ├── selection.py
│   │   ├── util.py
│   │   └── layer.py
│   └── rule_NNN.json       ← learned rules (see §3 schema)
│
├── semantic_memory/        ← ARCKG storage (regenerated each run)
├── episodic_memory/        ← execution traces (one folder per attempt)
│
├── managers/arc_manager.py ← data/ → ARCKG node hierarchy
├── arc2_env/               ← evaluation environment
├── basics/                 ← viz, utils
└── data/                   ← ARC dataset                                [FROZEN]
```

**[FROZEN]** = file or directory must not be modified during any session. See §4.

---

## 3. Memory Schema

ARBOR has three long-term memory stores, matching SOAR's standard LTM trichotomy.
Each store has a *fixed* format. Violations are architecture errors, not bugs.

### 3.1 Semantic memory (`semantic_memory/`)

5-level node hierarchy. Each node is a *folder*; each edge is a JSON file.

```
semantic_memory/
└── N_T{hex}/                     ← TASK node folder
    ├── E_T{hex}.json             ← 0th-order edge: TASK properties
    ├── E_P0G0-P0G1.json          ← 1st-order edge: comparison between two nodes
    ├── E_(E_...)-(...).json      ← 2nd-order edge: comparison between two edges
    └── N_T{hex}.P0/              ← PAIR subfolder
        ├── E_P0.json
        ├── E_P0G0.json
        └── N_T{hex}.P0.G0/       ← GRID subfolder, etc.
```

Edge JSON canonical shape:
```json
{
  "id1": "<node-or-edge-path>",
  "id2": "<node-or-edge-path>",
  "lca_node_id": "<lowest common ancestor>",
  "order": 0 | 1 | 2,
  "result": {
    "type": "COMM | DIFF",
    "score": "n/m",
    "category": { ... }
  }
}
```

**Rule**: `TF_GRID` (transformed grids produced during solving) **must not** be
written into `semantic_memory/`. Those go to `episodic_memory/`. Mixing the two
collapses the static/dynamic separation that defines this architecture.

### 3.2 Procedural memory (`procedural_memory/rule_NNN.json`)

A rule is a **`{condition, action}` pair** — a manual describing *when* and *how*
to apply a DSL primitive. Both halves are mandatory.

**Canonical schema** (validated by `agent/memory.py:save_rule()`):

```json
{
  "id": <int>,
  "concept": "<human-readable label>",
  "category": "<grouping tag>",

  "condition": {
    "type": "<pattern-matcher name>",
    "params": { ... },
    "min_evidence": <int>
  },

  "action": {
    "dsl": "<DSL primitive name>",
    "args": { ... }
  },

  "covers": ["<task_id>", ...],
  "source_task": "<task_id>",
  "anti_unification_trace": "<path or null>",
  "created_at": "<ISO 8601>",
  "times_reused": <int>
}
```

**Hard requirements** (`save_rule()` raises on violation):
1. Both `condition` and `action` present and non-empty.
2. `condition.type` must reference a known matcher; `action.dsl` must reference an
   existing primitive in `procedural_memory/DSL/`.
3. `anti_unification_trace` is `null` only for the initial rule learned from a
   single task. For any rule produced by generalization across multiple
   sources, this field must point to an episode trace.

Legacy rules lacking `condition` are tagged invalid on load and must be
migrated, not silently used.

### 3.3 Episodic memory (`episodic_memory/`)

```
episodic_memory/
└── {task_id}/
    └── attempt_NNN/
        ├── trace.json        ← cycle-by-cycle operator/impasse log
        ├── grids/            ← step-by-step WM grid snapshots
        │   ├── step_000.json
        │   └── step_NNN.json
        └── metadata.json     ← outcome, score, rules used, AU invocations
```

**Rule**: every `solve()` invocation — success *or* failure — produces exactly
one `attempt_NNN/` folder. An empty `episodic_memory/` after `run_learn.py`
means the episodic writer was bypassed, which is an architecture violation.

---

## 4. Cycle Invariants

The SOAR decision cycle is defined in `agent/cycle.py` and runs:

```
Elaborate → Propose → Select → Apply  (until goal satisfied or budget exhausted)
```

State alternation:
1. **S1**: `solve-task` operator fires, intentionally produces no WM change →
   no-change impasse → push **S2**.
2. **S2**: pipeline operator fires, writes to `wm.s1` → pop S2.
3. Back to S1, repeat until goal satisfied.

All pipeline state lives in `wm.s1` so it survives S2 pop/push.

### Frozen files (do not modify under any prompt)
- `data/` — the ARC dataset
- `agent/cycle.py` — the cycle engine itself
- `agent/wm.py` — WorkingMemory representation
- `ARCKG/*.py` node classes — node-identity contract

Modifications to these constitute an architecture change, not a session task.

---

## 5. Operator Pipeline

`agent/active_operators.py` defines six pipeline operators plus the abstract
`SolveTaskOperator`. The pipeline runs strictly in this order:

```
solve-task (S1, abstract)
   ↓
select_target → compare → extract_pattern → generalize → predict → submit  (all in S2)
```

| Operator | Reads | Writes to `wm.s1` |
|----------|-------|-------------------|
| `select_target`    | task/pair structure         | `comparison-agenda`, `pending-comparisons` |
| `compare`          | pending comparisons         | `comparisons` (one per cycle via `ARCKG.compare()`) |
| `extract_pattern`  | comparisons                 | `patterns` (COMM→invariant, DIFF→diff_pattern) |
| `generalize`       | patterns + procedural_memory| `active-rules` (sourced via §8 anti-unification, **not** ad-hoc detectors) |
| `predict`          | active-rules + test inputs  | `predictions` |
| `submit`           | predictions                 | `output-link`, marks goal satisfied |

### 5.1 The `_try_*` / `_apply_*` family is closed

The current `active_operators.py` contains a family of hand-written pattern
matchers (`_try_recolor_sequential`, `_try_color_mapping`, …) paired with
appliers (`_apply_*`). **No new methods may be added to this family.**

The reason: every `_try_*` added is a manually hand-coded special case. Stacking
them indefinitely is what produced 168 rules with sub-1.0 coverage in the KCC2026
observation. Generalization belongs in §8 (anti-unification), not in `_try_*`.

Allowed modifications to the existing family:
- Bug fixes within an existing `_try_*` or `_apply_*` method.
- Removal of methods superseded by anti-unification-based generalization.
- Schema updates that change *all* methods uniformly.

**Forbidden**: introducing a new `_try_<name>` to handle a newly-seen task
category. The correct response to a missing category is to extend anti-unification
or add a DSL primitive (§6), not to grow `_try_*`.

### 5.2 Generalize operator contract

```python
class GeneralizeOperator:
    def effect(self, wm):
        # 1. Fast path: look up applicable rules from procedural_memory
        #    matching wm.s1["patterns"] against rule["condition"]
        # 2. If no rule matches and ≥2 example pairs have pair-specific programs:
        #    invoke program.anti_unification.unify(pair_programs) → abstract rule
        # 3. Append the resulting rule to wm.s1["active-rules"]
        # 4. New rules are persisted by agent/memory.py:save_rule() (§8)
```

Both branches must populate `active-rules` symbolically. No reference to
`_try_*` methods anywhere except inside §5.1's closed family.

---

## 6. DSL Interface

`procedural_memory/DSL/apply.py` exposes:

```python
apply_DSL(name: str, grid, **kwargs) -> grid
```

Adding a new primitive:
1. Implement the function in the appropriate `DSL/*.py` (transformation /
   selection / util / layer).
2. Register the name in `apply.py`'s dispatcher table.
3. Add a `condition` matcher capable of recognizing when this primitive
   applies — placed in `agent/memory.py` or its sub-module, **not** in
   `active_operators.py`.

The DSL is the only locus where new transformational vocabulary may be added.
The pattern-detection vocabulary lives in §3.2's `condition.type` registry.

---

## 7. Working Memory Notation

WM is a set of WMEs `(identifier ^attribute value)`. The conventions below are
required for consistency with SOAR debugger-style traces.

### State identifiers
```
S1                    root state
S2, S3, ...           substates pushed on impasse
```

### Standard slots on root S1
```
(S1 ^type state
    ^superstate nil
    ^io I1
    ^smem I4
    ^epmem I5
    ^current-task <task_id>
    ^operator O1 +     ; preference WME
    ^operator O1)      ; applied WME
```

### Standard slots on substate S2
```
(S2 ^type state
    ^superstate S1
    ^impasse no-change | failure | no_candidates
    ^choices none | multiple | constraint-failure
    ^attribute operator | ...
    ^quiescence true
    ^smem I6
    ^epmem I7
    [^item ...]
    [^item-count N])
```

### Preference notation
Preferences appear only on `^operator` lines and on the operator node's
`^op-preference` slot:
```
(S1 ^operator O1 +)
(O1 ^name solve-task
    ^task-id 08ed6ac7
    ^op-preference +)
```

**Forbidden meta-slots**: `^proposed_ops`, `^selected_op`, `^op_status`.
Status is inferred from preference WMEs and cycle-internal `changed /
no_change / failure` accounting, not exposed as WM content.

---

## 8. Anti-Unification Integration

The generalization mechanism. Implemented in `program/anti_unification.py`.

### Call site (only one)
```python
# agent/memory.py
def save_rule(new_rule, source_task, related_rules):
    if len(related_rules) >= 1:
        au_result = anti_unification.unify(related_rules + [new_rule])
        if au_result.is_more_general():
            new_rule = au_result.abstract_rule
            new_rule["anti_unification_trace"] = au_result.trace_path
    _write_json(new_rule)
```

`agent/memory.py:save_rule()` is the **only** function permitted to invoke
`anti_unification.unify()`. Other call sites are an architecture violation
and will be rejected by the session-end validator.

### Inputs
- A set of pair-specific or task-specific rules sharing a `category`.
- Each rule's `action` must reference a *common* DSL primitive (lifting beyond
  the primitive level requires DSL-level abstraction, not anti-unification).

### Outputs
- An abstract rule whose `condition` and `action` parameters contain
  generalization variables for the points where inputs differ.
- A trace JSON written to `episodic_memory/<task_id>/anti_unification/`
  recording which rules were combined and the resulting substitutions.

### Failure modes
- If no common skeleton exists, `unify()` returns `NoCommonSkeleton` — the
  caller leaves the input rules unchanged.
- If lifting is needed (e.g., pair-specific programs use pixel coordinates
  rather than object identifiers), `unify()` first calls
  `object_level_lift()` — see `[[object-level-lifting]]` in the wiki for the
  rationale.

### Coverage objective
`rule_coverage = solved_task_count / total_rule_count`. The system goal is to
hold this ratio ≥ 1.0 across sessions. Anti-unification is the mechanism by
which this becomes possible — without it, each task generates its own rule
and coverage stays below 1.

---

## Reference

| Wiki page | Use |
|-----------|-----|
| `[[arbor]]` | system intent, diagnosis, open questions |
| `[[arbor-modules]]` | module inventory, gap analysis |
| `[[arbor-prompt-spec]]` | how this file relates to PROMPT.md |
| `[[arckg-3repository]]` | §3 storage rationale |
| `[[arckg-node-edge]]` | §3.1 1st/2nd-order edge design |
| `[[arckg-wm-design]]` | §7 WM region design |
| `[[anti-unification]]` | §8 algorithmic background |
| `[[object-level-lifting]]` | §8 lifting rationale |
| `[[impasse]]` | §4 substate semantics |
