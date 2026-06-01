---
title: ARCKG Working Memory 설계
aliases: [ARCKG WM, WM 4영역, ARCKG SOAR agent WM]
tags: [#topic/arckg, #design-decision, #status/active]
created: 2026-05-11
updated: 2026-05-11
sources:
  - raw/claude-arc-문제-해결을-위한-soar-agent-작업-메모리-구조-2026-03-18.md
---

# ARCKG Working Memory 설계

## 한 줄 정의
[[arckg-research]] ARC 풀이 에이전트의 Working Memory를 어떻게 구조화할지에 대한 설계 — [[soar]] 원칙과의 정합성 검토 포함.

> **재명명 주의** (→ [[arbor-soar-memory-mapping]]): ARBOR가 "semantic memory"라 부르던 ARCKG 디스크 그래프는 SOAR 기준 *영속화된 WM* 이다. 즉 이 WM 설계는 RAM 상의 WM 뿐 아니라 *그 디스크 투영(=ARCKG)* 까지 포괄해야 한다. 노드는 WM에서 태어나고 디스크로 flush.

## 초기 4영역 제안 (→ [[raw/claude-arc-문제-해결을-위한-soar-agent-작업-메모리-구조-2026-03-18]])

```
[목표 영역]    goal, task
[결핍 영역]    deficits (모르는 것의 목록)
[지식 영역]    relations, invariants, diff_patterns, abstract_rule
[결과 영역]    found, impasse
```

## SOAR 원칙과의 충돌 — 4가지 수정

### 1. Operator 영역 부재 → 추가
> 원래 제안에는 operator 가 없음 — 그러면 state snapshot 일 뿐 SOAR agent 가 아님.

**추가**:
```
[연산자 영역]
  proposed_operators = [op1, op2, ...]
  selected_operator  = op_compare_pair(0)
  operator_result    = {success | failure | impasse}
```

### 2. Impasse는 정보 필드가 아님 → 메커니즘으로
> [[impasse]] 는 *구조적 전이*. `결과 영역`에 정보 필드로 두면 안 됨.

**수정**: `impasse` 필드 제거. `operator_result == failure` 일 때 substate 자동 생성. 막힌 이유는 substate 안의 별도 goal 영역에 기술.

### 3. Deficit 사전 열거 → 동적 발견
> SOAR 철학상 *무엇을 모르는지는 operator 적용이 실패할 때 드러나는 것*. 처음부터 나열하면 task decomposition을 하드코딩하는 것.

**수정**:
```
[목표 영역]
  goal.type     = "predict_all_test_outputs"
  goal.subgoals = [predict(test_0), predict(test_1), ...]
  goal.status   = {test_0: pending, ...}
```

### 4. Abstract_rule 위치 → LTM
> 일반화 지식은 WM이 아니라 procedural LTM ([[chunking]]) 에 저장. ARCKG에서는 TASK 노드의 edge JSON.

**수정**: WM에는 `active_rule = pointer_to_LTM_rule` 만.

## 개정된 WM 구조
```
[목표 영역]
  goal.type     = "predict_all_test_outputs"
  goal.subgoals = {test_0: pending, test_1: solved, ...}

[연산자 영역]          
  proposed_ops  = [compare_pair(2), extract_invariant("color"), ...]
  selected_op   = compare_pair(2)
  op_status     = {running | success | failure}

[지식 영역]
  relations     = {pair_idx: {grid_comparison, object_comparisons}}
  invariants    = {grid.size: "unchanged", grid.color: "unchanged"}
  diff_patterns = {grid.contents: {type: "object_moved", direction: ...}}
  active_rule   = ref→LTM(abstract_rule)   ← WM엔 포인터만

[결과 영역]
  found         = {test_1: grid, ...}

[서브스테이트]          ← impasse 발생 시 동적 생성
  triggered_by  = op_status:failure
  subgoal       = "find_missing_knowledge(direction)"
  sub_ops       = [inspect_object_positions, ...]
```

## 남은 피드백 포인트 (→ [[raw/claude-arc-문제-해결을-위한-soar-agent-작업-메모리-구조-2026-03-18]])
- **Elaborate는 선택적이 아님**: 매 사이클마다 propose 전에 WM을 완성시키는 단계는 SOAR에서 필수. 구현 부담으로 선택적으로 두면 propose rule 설계가 훨씬 복잡해짐.
- **Active_rule 다중성**: 단일 포인터 가정은 비현실적. "크기 유지 + 색 반전 + 위치 이동" 처럼 여러 sub-rule 동시 active 가능 → `active_rules = [ref_1, ref_2, ...]` 또는 rule에 confidence 필드.
- **update_memory(reward) 와 SOAR chunking의 철학 차이** — reward 기반 업데이트는 SOAR-native가 아님. (이 부분은 추가 ingest 필요)

## 관련
- [[arckg-research]]
- [[soar]] — Propose-Select-Apply
- [[impasse]]
- [[chunking]]

## 열린 질문
- Multi-rule active 상태에서 rule 간 충돌 해결 메커니즘은?
- Elaborate 단계의 ARCKG 버전 — 어떤 derivation을 자동화할 것인가?
