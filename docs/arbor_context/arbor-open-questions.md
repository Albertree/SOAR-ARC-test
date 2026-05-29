---
title: ARBOR Open Questions — 미해결 질문 누적
aliases: [ARBOR 미해결 질문, ARBOR design questions]
tags: [#topic/system, #project/active, #status/draft]
created: 2026-05-21
updated: 2026-05-21
sources:
  - raw/notion-idea-arbor-flow-three-task-description-2026-05-21.md
  - raw/claude-arbor-flow-deep-analysis-2026-05-21.md
---

# ARBOR Open Questions

## 한 줄 정의
[[arbor|ARBOR]] 의 spec 에서 *답이 없거나 결정 안 된* 질문의 누적. 답이 나오면 본 페이지에서 제거 → 해당 모듈 페이지 ([[arbor-execution-trace]] 의 모듈) 로 이동.

## 위치
- 입력: 사용자 prose 의 "(아직 모르겠어)", "(의문이야)", "(질문이야)" 발화 + 본 분석에서 도출된 본질적 unresolved
- 시스템 허브: [[arbor]]
- 모듈 ↔ 질문 매핑: [[arbor-execution-trace]] 의 §7 (원본 분석 [[raw/claude-arbor-flow-deep-analysis-2026-05-21]])

## 질문 (사용자 원문 출처 명시)

### Q-A1. Goal 의 단위 symbol — *사용자 명시*

> "(이걸 어떻게 형식적으로 표현할 수 있을지, 그러려면 어느부분들이 단위 Symbol이 되야하는지도 아직 모르겠어.)"

- **모듈**: B (GoalStack with Evolution)
- **방향 제안**: goal = `{target_id, target_attr, intent_type, value_or_expression}` dict. intent_type ∈ {set-to-value, set-to-derived, create-component, modify-relation} 4종 enum.
- **본질적 미해결**: intent enum 의 *완전성* — 새 task 마다 새 intent 등장 가능. 점진 확장 패턴 필요.

### Q-A2. Object-level 비교 enumeration 제어 — *사용자 명시*

> "Object-level은 ... 비교의 경우의 수가 기하급수적으로 많아져. 이들을 정렬하고 범위별로 나누고 선택적으로 확인하는게 일단 내 머리에서는 complete하게 처리하기 어려워. 이를 그래서 너가 정밀하게 잘 생각해서 디자인에 도움을 주면 좋겠어."

- **모듈**: C 의 폭증 제어 (구 C4, 이제 *비교 후 ranking* + *scope predicate*)
- **방향 제안**: scope predicate 로 비교 *전* 범위 축소 (`select(..., pred)` 예: color==5 만) + 비교 *후* score-desc top-k. 즉 폭증 관리가 두 자리 — scope(전처리) + ranking(후처리)
- **본질적 미해결**: top-k 값과 sort key 선택은 hyperparameter — task 가 늘면 적응 메커니즘 필요

### Q-A3. 비교 결과 파일 생성 병목

> "비교는 비교한 결과의 파일을 생성해야하는 병목이될 수 있는 조금 무거운편인 작업이야"

- **모듈**: C (저장 정책)
- **답**: lazy materialization. 현 `compare(save=False)` default 가 옳음 (`ARCKG/comparison.py:148`). 의미 있는 것만 chunking 시점에 저장.
- **상태**: 사용자 의도와 코드 일치 — *해결됨*, 단 명문화 필요

### Q-A4. 같은 위치 pruning 의 형식

> "grid도 pair간 비교를 할 때, 같은 위치에 있는 grid만 선택적으로 비교하는 제한이 필요해. 아직 이 제한을 어떻게 할지"

- **모듈**: C 의 C5
- **답**: pixel level 적용. `coord_eq(a, b) ∧ color_neq(a, b)` 단순 filter. 코드 한 줄
- **상태**: 사용자 의도 명확 — *해결됨*

### Q-A5. 선택적 비교의 근거 통일 — *사용자 명시*

> "비교를 선택적으로 하게된다면 계층 상관없이 비교의 근거가 통일된 모습이 나올 수 있는지 생각하고 있어"

- **모듈**: C 전체
- **답 (2026-05-29 정정)**: 구 6+1 규칙(C1-C7) → **2종 (Intra/Inter) + scope predicate** 로 통일. 모든 비교가 `compare(select(anchor,level,pred), select(anchor,level,pred))` 의 동일 형식 → 계층 무관 통일. [[arbor-execution-trace]] §모듈 C 절
- **상태**: 답 있음, 구현 대기

### Q-B1 / Q-C1. 표현식 합성의 깊이 제한

> "표현식 깊이 제한이 필요한가?" (raw 원문 [[arbor-dsl-taxonomy]] 의 열린 질문에서 이미 명시)

- **모듈**: I (VariableOriginResolver 의 chain depth)
- **방향 제안**: depth 2 부터 시작 (08ed6ac7 도 depth 2 로 충분). var resolve 가 depth 2 로 실패 → backtrack → depth 3 시도 → 실패 → I3 (새 property 발명) trigger
- **본질적 미해결**: backtrack budget

### Q-B2. Activation Rule 조건 형식 — *사용자 명시*

> "아직 구체적으로 어떻게 생긴, 조건이 어떤 규칙인지는 모르지만"

- **모듈**: E (ActivationRuleSet)
- **방향 제안**: condition = comparison pattern (a, b, op, role) 의 conjunction; action = DSL call template with expression args
- **본질적 미해결**: pattern 언어의 *완전성* — 새 task 마다 새 pattern 필요 가능

### Q-B3. Self-introduced primitive — 새 property 발명 — *사용자 명시*

> "그러면 변수화 하는 단계에서 해당 좌표가 grid의 우측하단이라는 개념을 만들어 내야하는 상황이야 ... 현재는 구체적으로 어떻게 개념을 만들어 낼지는 의문이야"

- **모듈**: I3 + J (가장 본질적 미해결)
- **가설**: 발명 후보 = unresolved var 의 concrete value 들 (예: (5,5), (3,3)) 의 cross-pair 공통 *간접* derive — height/width 와 같음 → `right_bottom(G) = (height-1, width-1)`. 알고리즘: hypothesis enumeration (수십 후보) → 각 후보를 *모든 example pair 에 적용* → 일치하면 채택
- **본질적 미해결**: 후보 enumeration 의 효율 (조합 폭증)

### Q-B4. 발명 후보 중 선택 기준

> "다른 경우도 찾아질 수 있으니까"

- **모듈**: J
- **방향 제안**: (a) 모든 example pair 에서 같은 값을 도출하는 것 우선, (b) expression 길이 최소 ([[mdl|MDL]] like), (c) 기존 DSL 의 *재사용* 우선
- **본질적 미해결**: (a)(b)(c) 의 가중치

### Q-B5. Skill 의 activation context 형식

> "비슷한 문제상황에서 깊이 들어가는 분석을 하지 않고도 ... 의사결정을 효율적이게하는 흐름"

- **모듈**: J
- **방향 제안**: skill 의 condition = *비교 결과 패턴* + *DSL 부재 패턴*. 예: "GRID intra-pair compare 에서 contents DIFF + object level 에서 'position only diff' 매칭 → move skill trigger"
- **본질적 미해결**: context 의 정밀도 vs 일반성

### Q-C2. Var resolution 실패 → fallback chain 우선순위

> "단일 grid 내부의 object들을 비교하여 추가적인 정보를 이끌어내려고 시도한다" (사용자 prose 의 implicit 결정)

- **모듈**: I (fallback chain)
- **방향 제안**: fallback chain 명시 — (1) inter-pair surface property, (2) intra-grid object compare, (3) 2차 relation compare, (4) 새 property 발명. 우선순위 = 비용 desc
- **본질적 미해결**: 각 단계의 cutoff

### Q-C3. Ranking util DSL 의 적정 set

- **모듈**: D
- **답**: 최소 set = `(argmax, argmin, nth-by-desc, sort-by, count, filter, unique)` 7개. 08ed6ac7 충분
- **상태**: 답 있음, 등록 대기

## 답 진척 표

| Q | 상태 | 막힌 부분 |
|---|------|----------|
| A1 | ⚠ 방향만 | intent enum 완전성 |
| A2 | ⚠ 방향만 | top-k hyperparameter |
| A3 | ✅ 답 있음 (lazy materialization) | — |
| A4 | ✅ 답 있음 (coord_eq filter) | — |
| A5 | ✅ 답 있음 (C1-C7) | — |
| B1/C1 | ⚠ 방향만 | backtrack budget |
| B2 | ⚠ 방향만 | pattern 언어 완전성 |
| B3 | ❌ 본질적 미해결 | enumeration 효율 |
| B4 | ⚠ 방향만 | (a)(b)(c) 가중치 |
| B5 | ⚠ 방향만 | 정밀도-일반성 트레이드오프 |
| C2 | ⚠ 방향만 | 단계별 cutoff |
| C3 | ✅ 답 있음 (7 util) | — |

**해결**: 4개 (A3, A4, A5, C3) — 구현 대기
**방향**: 7개 — slice 진행하며 구체화
**본질적 미해결**: 1개 (B3) — slice 4 의 입력

## 관련

- [[arbor-execution-trace]] — 11 모듈 + spec gap (본 페이지의 자매)
- [[arbor]] — 시스템 허브
- [[arbor-dsl-taxonomy]] — DSL 4종 (D 모듈 관련 질문 출처)
- [[anti-unification]] — H 모듈 관련 질문 출처
- [[dreamcoder]] — J 모듈 비교 대상
