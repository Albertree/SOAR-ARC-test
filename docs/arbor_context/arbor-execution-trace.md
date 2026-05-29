---
title: ARBOR Execution Trace — 3 task 분해에서 도출된 11 모듈 + Spec Gap
aliases: [ARBOR module list (executable), 11 modules, ARBOR slice spec]
tags: [#topic/system, #project/active, #status/draft]
created: 2026-05-21
updated: 2026-05-21
sources:
  - raw/notion-idea-arbor-flow-three-task-description-2026-05-21.md
  - raw/claude-arbor-flow-deep-analysis-2026-05-21.md
---

# ARBOR Execution Trace

## 한 줄 정의
[[arbor|ARBOR]] 가 *내가 의도한 방식대로* 동작하려면 존재해야 하는 11개의 (대부분 미구현인) 모듈과 그 spec gap. 사용자의 [[raw/notion-idea-arbor-flow-three-task-description-2026-05-21|3-task 풀이 시나리오]] 에서 *반복* 등장한 메커니즘 (= 일반화 가능한 모듈) 만 추출.

## 위치
- 입력: 사용자 prose ([[raw/notion-idea-arbor-flow-three-task-description-2026-05-21]]) + 본 분석 ([[raw/claude-arbor-flow-deep-analysis-2026-05-21]])
- 시스템 허브: [[arbor]]
- 모듈 인벤토리의 다른 시각: [[arbor-modules]] (두 레포 실제 상태 vs 의도) — 본 페이지는 *모듈의 의미* 에 집중
- DSL 관련: [[arbor-dsl-taxonomy]]
- 미해결 질문 모음: [[arbor-open-questions]]
- Outer loop 청사진: [[arbor-prompt-spec]], [[arbor-signals]]

## 7 원리 (모든 모듈의 설계 제약)

| P# | 원리 | 사용자 원문 위치 (raw) |
|----|------|------------------------|
| P1 | **계층 깊이는 *필요* 에 의해 들어간다** | "Task수준에서 막히니까 Pair로, Pair에서 막히니까 Grid로..." |
| P2 | **비교는 동일 레벨끼리** | "같은 Level에 있는 파일들끼리도 비교해서 확인" |
| P3 | **정답에는 *근거* 가 있어야 함** (값보다 *이유* 가 우선) | "값에 초점을 맞추기 보다는 ... 구조적 공통성" |
| P4 | **근거는 *비교의 결과* 에서 나옴** | "공통점과 차이점을 본다 ... 어느 관계의 공통점이 중요한지" |
| P5 | **변수의 출처는 G0** (test 에 G1 없음) | "test에는 G1이 없잖아. Pa.G0만 가지고 G1을 예측" |
| P6 | **2개씩 짝지어 비교** | "무조건 2개씩 붙잡고 비교를 하는거야" |
| P7 | **모든 정보는 symbolic dict + json** | "모두 symbolic한 dict로 구성되며 json 파일형태" |

7원리 위반하는 모듈 설계 = ARBOR 와 어긋남.

## 11 모듈

### A. HierarchicalDescentController

- **역할**: 현 레벨에서 actionable result 없을 때 다음 레벨로 descend
- **Trigger 조건**: (`n_at_level == 1` ∨ `all_results == COMM trivial` ∨ `DIFF 결과를 완화할 actionable DSL 부재`) ∧ `current_goal 달성 불가`
- **발현**: easy000a Step 3,8; easy000b Step 15b,18b; 08ed6ac7 Step 15
- **현 코드**: `agent/active_operators.py:161` DescendOperator stub (precondition / effect NotImplementedError)
- **현 wiki**: [[agentness]] 의 PSA loop, [[arckg-research]] 의 5계층 — 암시
- **다음 액션**: `NeedsDescendRule` 의 condition 구현 (5줄), `DescendOperator.effect` 의 push_substate or set descend_to 구현 (10줄)

### B. GoalStack with Evolution

- **역할**: subgoal 트리 유지. 새 노드 visit → schema 보고 *현재 노드를 refine* 또는 *child subgoal 로 분해*
- **2 종류 진화**:
  - *Refinement*: "Pa.grid_count := 2" → "create Gx" (값 → 액션)
  - *Decomposition*: "create Gx" → "{Gx.color, Gx.size, Gx.contents}" (schema 분해)
- **발현**: 모든 task 의 Step 6, 11
- **현 코드**: `wm.s1["goal"]["subgoals"]` 슬롯 있음 (cycle.py:104), *진화 메커니즘 없음*
- **현 wiki**: [[agentness]] 의 "goal-directed loop" 언급
- **다음 액션**: `agent/goal.py` 신규 (GoalStack 클래스 + `evolve(new_node, schema)` + 진화 규칙 2종)

### C. RecursiveComparisonController (구 ComparisonScheduler)

> **2026-05-29 정정**: 구 7규칙(C1-C7)은 *4개의 다른 관심사* 가 섞인 것이었음. 비교는 **2종 (Intra / Inter) + scope predicate** 로 단순화. (대화 출처: [[raw/claude-arbor-dsl-4종-설계-결정-2026-05-18]] 후속 세션)

- **역할**: 비교를 schedule. 비교 단위 = `compare(scope_A, scope_B)`, **N:N 이 기본** (1:1 = N=1 특수 케이스, cardinality 는 변수 아님)
- **두 분석 종류** (재귀적으로 중첩됨):
  - **Intra-[Level]**: 한 component 안 형제끼리 (예: 한 grid 의 object 들)
  - **Inter-[Level]**: role-aligned 다른 부모끼리 (예: P0.G1 ↔ P1.G1)
- **scope** = `select(anchor, level, predicate?)` = `filter( elements-at(anchor, level), pred )` — 모듈 D 의 util(`objects-of`/`grids-of`/`filter`) + property(`color-of`...) 를 사용. 예: `select(P0.G0, object, color-of(o)==5)` (회색 object 만)
- **구 7규칙의 행방**:
  - C1(같은 레벨)·C6(2개씩) → 비교의 *정의* 로 흡수 (규칙 아님)
  - **C2 → Intra-[Level]**, **C3 → Inter-[Level]** (role-aligned)
  - C4(score top-k) → 비교 *후* ranking (폭증 시 옵션, scope 아님)
  - C5(coordinate filter) → **scope predicate** 로 흡수 (`coord-of(a)==coord-of(b)`)
  - C7(var 실패 추가비교) → 모듈 **I** 의 제어 흐름 (C 가 아님)
- **발현**: 모든 task 의 Step 5, 12, 16, 19
- **현 코드**: `ARCKG/comparison.py` 의 compare() 함수 ✅ (N:N); **scope selector + Intra/Inter scheduling ❌**
- **현 wiki**: 명시 없음. [[arckg-wm-design]] 에 "비교 결과 저장 영역" 만
- **다음 액션**: `agent/compare_scheduler.py` 신규 — Intra/Inter 2종 + scope selector (D 의존). top-k 후처리는 폭증 slice(3+)에만.
- **C–D 결합**: scope selector 가 D 를 호출하므로 **D 를 C 보다 먼저 (또는 같이) 구현해야 함**

### D. Property/Relation/Util DSL Registry

- **역할**: 합성의 *재료* 함수 집합 ([[arbor-dsl-taxonomy]] 4종 분리의 3종)
- **현 상태**:
  - *암묵적 property*: ARCKG 노드의 `to_json()` 키 14개 (코드에 있으나 함수형 노출 X)
  - *relation*: 5개 명시 (코드 없음)
  - *util*: 7개 + ranking util 3개 (argmax/argmin/nth-by) — 08ed6ac7 발견
- **발현**: 모든 task 의 모든 Step
- **현 코드**: `procedural_memory/DSL/` 폴더 없음 (only `type_system/`)
- **현 wiki**: [[arbor-dsl-taxonomy]] 17 씨앗 (암묵 property 14 + ranking 3 누락)
- **다음 액션**: `procedural_memory/DSL/{property,relation,util}/__init__.py` 신규 — 함수형 wrapper

### E. ActivationRuleSet

- **역할**: condition-action 쌍 집합. WM 패턴 매칭 시 transformation DSL 호출
- **사용자 핵심 (raw 원문)**: "DSL activation rule이라는 이름으로 부르고 있었어 ... condition-action 쌍으로 구성된 규칙"
- **형식 후보**:
  ```yaml
  rule:
    name: color-diff-pixel-pair-to-coloring
    condition:
      pattern_type: pixel_pair_comparison
      pattern:
        a.parent.role: G0
        b.parent.role: G1
        comp(a,b).coord: COMM
        comp(a,b).color: DIFF
    action:
      dsl: coloring
      args:
        selection: "[coord-of(a)]"
        color: "color-of(b)"
  ```
- **발현**: easy000b Step 20b; 08ed6ac7 Step 17
- **현 코드**: 없음. `agent/rules.py` 는 *production rule* (operator 선택) 이지 *activation rule* (transformation 선택) 이 아님 — **2 종류 rule 동시 필요**
- **현 wiki**: [[arbor-prompt-spec]] 의 RULE_FORMAT 일부, 2 종류 구분 X
- **다음 액션**: `procedural_memory/activation_rules/__init__.py` + 첫 3 rule hardcoded

### F. Synthesizer

- **역할**: WM + DSL + ActivationRule → goal 만족 program 탐색
- **2 모드**:
  - F1. **ActionSearch**: 현 goal 달성 위한 DSL 조합 (easy000a Step 7 의 "Pa.grid_count++" 같은 실패 케이스)
  - F2. **ExpressionSynthesis**: var origin 의 expression tree 탐색 (easy000b Step 24b)
- **발현**: 모든 task 의 후반
- **현 코드**: 없음
- **현 wiki**: [[arbor-dsl-taxonomy]] 에 *언급* 만
- **다음 액션**: spec 만 — slice 3 에 구현; slice 1, 2 는 hardcoded 단순 search 로 우회

### G. PerPairProgramConstructor

- **역할**: 한 (Gin, Gout) 쌍에서 activation rule 발사를 누적해 overfit program 생성
- **I/O**: input = (G0, G1, fired_rules); output = program tree
- **발현**: easy000b Step 21b, 22b; 08ed6ac7 Step 18, 19
- **현 코드**: 없음
- **다음 액션**: `procedural_memory/program_format.md` (tree spec — RULE_FORMAT.md 확장)

### H. AntiUnifier

- **역할**: N 개 per-pair program → 1 개 abstract program (변수 lift)
- **발현**: easy000b Step 23b; 08ed6ac7 Step 20-25
- **현 코드**: `program/anti_unification.py` 4 함수 모두 `pass`. 인터페이스만
- **현 wiki**: [[anti-unification]], [[stun]] (binding 5종 명시)
- **다음 액션**: easy000b 의 2-line linear program 케이스부터 구현

### I. VariableOriginResolver

- **역할**: AU 가 도입한 변수에 G0-derivable expression chain 탐색 (P5 enforce)
- **3 단계 (08ed6ac7 발견)**:
  - **I1**. surface property 일치 시도 (1-단계 chain)
  - **I2**. intra-grid relation 도입 (2-단계 chain — argmax 등)
  - **I3**. **새 property 발명** (3-단계 — 미해결, [[arbor-open-questions]] Q-B3)
- **발현**: easy000b Step 24b; 08ed6ac7 Step 20-24
- **현 코드/wiki**: 없음
- **다음 액션**: I1 + I2 만 우선

### J. SkillLibrary

- **역할**: cross-task AU 로 새 DSL primitive 합성 + activation context 자동 derive
- **발현**: easy000b Step 31-32 (사용자 prose 의 *후속* 시나리오)
- **차이점 vs [[dreamcoder]]**: vector 가 아닌 *symbolic 구조* 비교 (raw 원문 명시)
- **현 코드/wiki**: 없음
- **다음 액션**: slice 4 이후 (multi-task 누적 후)

### K. OutputChannel

- **역할**: validated abstract program 을 test G0 에 적용 → predicted G1 → output-link
- **발현**: 모든 task 의 마지막 step
- **현 코드**: `agent/io.py:inject_arc_task` ✅ (input); output stub
- **다음 액션**: `agent/io.py:emit_answer` 추가; SubmitOperator.effect 구현 (5줄)

## Spec Gap 표 (우선순위)

| Module | 코드 | wiki | P? | 다음 액션 |
|--------|------|------|----|----------|
| A | ⚠ stub | ⚠ 암시 | **P1** | NeedsDescendRule + DescendOp.effect (15줄) |
| B | ⚠ 슬롯만 | ❌ | **P1** | `agent/goal.py` 신규 |
| C | ❌ | ❌ | **P0** | `agent/compare_scheduler.py` 신규 |
| D | ⚠ 암묵 | ⚠ 17 씨앗 | **P0** | DSL 폴더 + wrapper 24개 (14+5+7+3) |
| E | ❌ | ⚠ schema | **P1** | activation_rules 폴더 + 첫 3 rule |
| F | ❌ | ⚠ 언급 | **P2** | slice 3 |
| G | ❌ | ❌ | **P2** | program tree spec |
| H | ⚠ stub 4 | ⚠ 알고리즘 | **P2** | 2-line linear 케이스 |
| I | ❌ | ❌ | **P2** | I1 + I2 (depth ≤ 2) |
| J | ❌ | ❌ | **P3** | spec 만 |
| K | ⚠ stub | ⚠ 명시 | **P1** | emit_answer + SubmitOp.effect |

**P0** = easy000a 최소 동작 필수 (C + D)
**P1** = easy000a 완성 + easy000b 일부 (A + B + E + K)
**P2** = easy000b AU + 08ed6ac7 일부 (F + G + H + I)
**P3** = 누적 task 후 (J)

## Slice 계획

각 slice 는 *1 task 가 input→output 완주하는 최소 vertical*:

### Slice 1 — easy000a + easy000a2 (변주)
- 모듈: A + B + C(Intra/Inter + scope predicate) + D(property + util) + K + PredictByAllPairCommOp
- 제외: E, F, G, H, I, J, object/pixel property, 후처리 top-k
- **task 2개** (둘 다 G1-COMM 메커니즘으로 풀림 = output 고정, input 무관):
  - `easy000a` — 고정 출력 `(5,5)빨강(2)`
  - `easy000a2` — 같은 메커니즘, *다른* 고정 출력 (예 `(0,0)초록(3)`). **PredictByAllPairCommOp 가 답을 하드코딩 안 했는지** 검증 (값-agnostic)
- **검증 (완화)**: `easy000a` + `easy000a2` 둘 다 정답 + **4 관찰 기준** (작동 / 통일성[모듈만, 산물은 overfit OK] / 접근성 / 탐색 건전성). **§2 의 "14 단계 정확 일치" 는 요구하지 않음** — 초기 ARBOR 는 이상적 흐름을 1:1 재현 못함, 의미있는 brute-force 허용
- **결정적 비교**: Inter-Grid, role==G1, {size·color·contents} 전부 COMM → test G1 = 공통값. (G0 는 Slice 1 에서 미사용 — output 고정이라)
- **개발 프롬프트**: SOAR-ARC-test `docs/SLICE_1_LOOP.md` (무인 ralph) / ARC-solver `SLICE_1_DEV.md` (손수 협업)

### Slice 2 (1-2주) — easy000b
- 추가: E (활성 rule 1: pixel-color-diff→coloring) + G + H (2-line linear) + I (depth-2) + C5
- **회귀 점검**: easy000a 통과 유지 (= L2 overfit 없음)

### Slice 3 (2주) — 08ed6ac7
- 추가: C4 + C7 + D ranking util 3 + I2 (intra-grid relation)
- 회귀: easy000a, b 유지

### Slice 4 (1-2주) — easy 변주 + 첫 skill
- I3 첫 정의 (새 property 발명)
- J 첫 등장 (move skill)

## 관련

- [[arbor]] — 시스템 허브
- [[arbor-modules]] — 모듈 인벤토리 (두 레포 상태 비교)
- [[arbor-dsl-taxonomy]] — 4종 DSL 분리 (모듈 D 의 상위 결정)
- [[arbor-open-questions]] — 11 미해결 질문 누적
- [[arbor-signals]] — F1-F8 / P1-P6 reward signals (outer loop)
- [[arbor-prompt-spec]] — outer loop CLAUDE.md / PROMPT.md 청사진
- [[anti-unification]] — Module H 의 알고리즘
- [[soar]] — 결정 엔진 (Operator 인터페이스의 출처)
- [[structure-mapping-theory]] — Module E 의 인지과학 근거
- [[dreamcoder]] — Module J 의 비교 대상 (symbolic 차이)

## 열린 질문

11 미해결 질문 전체는 [[arbor-open-questions]] 에. 본 페이지에서는 가장 핵심 3개:

- **Q-B2**: DSL activation rule 의 condition 언어는? (Module E 의 spec)
- **Q-B3**: 새 property 발명 알고리즘? (Module I3 + J)
- **Q-A1**: goal 의 단위 symbol? (Module B 의 spec)

이 3개 답이 없으면 slice 4 이상 진행 불가. slice 1-2 는 hardcoded 우회 가능.
