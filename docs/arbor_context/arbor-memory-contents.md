---
title: ARBOR 4기억의 내용 배치 — semantic = DSL 추상 라이브러리
aliases: [arbor-memory-contents, DSL 두 얼굴, semantic은 DSL 라이브러리, ARBOR 기억별 내용]
tags: [#topic/cognitive-architecture, #topic/arckg, #topic/dsl, #topic/soar, #status/design, #2026]
created: 2026-05-31
updated: 2026-05-31
sources:
  - 2026-05-31 세션 (SLICE_1_DEV 구현 논의 — 4기억 내용 배치 합의)
  - "[[arbor-soar-memory-mapping]] (선행 변곡점: semantic ≠ persisted WM)"
  - "[[dreamcoder]] (학습된 추상 라이브러리 모델)"
---

# ARBOR 4기억의 내용 배치

> **건설적 후속편**: [[arbor-soar-memory-mapping]] 이 "semantic은 persisted WM이지 SOAR semantic이 아니다"를 *진단*했다면, 이 노트는 *그럼 SOAR 4기억(Procedural·Episodic·Semantic·Working)에 ARC 풀이 중 실제로 뭐가 들어가나*를 정한다. 핵심 결론: **semantic = [[dreamcoder]]식 인출 가능한 DSL 추상 라이브러리.**

## 한 줄 정의
WM에서 빠져나간 지식은 *종류*에 따라 **일반 사실→semantic / 경험→episodic / 방법→procedural** 로 갈린다. 그리고 "DSL을 조합·비교·병합한다"는 ARBOR 비전이, **조합 대상 DSL은 반드시 인출 가능한 선언적 데이터(=semantic)** 여야 함을 강제한다.

## 핵심
- **"flush = semantic"은 함정.** 영속되는 지식은 종류로 분류된다: 일반 사실→**semantic**, 겪은 경험→**episodic**, 행동 방법→**procedural**. WM만 비영속 작업 상태 (→ [[arbor-soar-memory-mapping]]).
- **작동 기준**: *돌려야 하면 procedural*(발화·불투명), *들여다보고·비교하고·합쳐야 하면 semantic*(인출·검사 가능) (→ [[soar-manual-reference]] §2/§8).
- **DSL은 두 얼굴.** 같은 연산자가 **실행 본체(procedural)** + **선언적 명세=타입 시그니처·arg 스키마·합성 구조(semantic)** 로 양다리. 비교·[[anti-unification]]·병합은 *명세*를 대상으로 한다.
- **semantic = 학습된 DSL 추상 라이브러리.** 온톨로지 + 연산자 시그니처 + 합성/arg 제약 + **풀이로 합성해낸 고급 DSL**. [[dreamcoder]] 의 library learning 과 같은 자리 — 문제를 풀수록 추상이 쌓여 *안 빈다*. 비전이 *필연적으로* 부르는 자리라 *억지도 아니다*.
- **타입 시스템은 두 얼굴로 분리**: 스키마/시그니처(인출해 합성·비교) → **semantic**, 체커/실행/dispatch → **procedural**. ([[project-type-system-location]] 의 "타입 시스템 = procedural" 을 이 분리로 정정.)

## 상세

### 영속의 부채살 — 종류별 분류

WM에서 빠져나가 디스크에 남는 지식은 곧장 semantic으로 가지 않는다. **종류**로 갈린다:

| 빠져나간 지식의 종류 | 목적지 |
|---|---|
| 일반 사실 (어느 과제에도 참) | **Semantic** |
| 겪은 경험 (무슨 일이 있었나) | **Episodic** |
| 행동 방법 (어떻게 하나) | **Procedural** |
| (작업 상태, 비영속) | Working |

**분류 테스트**: "*이 과제에서*"라는 맥락을 떼도 의미가 남는가? "easy000a P0.G1은 (5,5) 빨강" → 떼면 무의미 → semantic 아님(episodic/WM). "색 2 = 빨강" → 떼도 참 → semantic.

### DSL의 두 얼굴 (이 노트의 심장)

ARBOR 비전 = *DSL을 조합해 고급 DSL을 만들고, 구조를 비교하고, 합친다*. 불투명하게 발화만 하는 production은 **비교도 병합도 불가**. 따라서 조합 대상 DSL은 인출 가능한 선언적 데이터여야 한다. 하나의 연산자가 두 조각으로:

| 얼굴 | 정체 | 어디 |
|---|---|---|
| **실행 본체** | WM을 바꾸는 발화 규칙. "어떻게 돌리나" | Procedural |
| **선언적 명세** | 타입 시그니처·arg 스키마·합성 구조 = 인출해 비교·병합할 데이터. "무엇이고 어떻게 생겼나" | Semantic |

**easy000a 예**: `PredictByAllPairCommOp`(모든 G1 비교 → COMM이면 공통값 복사)는 —
- *발화해 (5,5)빨강을 내놓는 본체* → **procedural**.
- *"compose(role==G1 비교) ∘ (COMM이면 copy), 입력: grid 집합, 출력: grid" 라는 구조 명세* → **semantic**. Slice 2에서 다른 연산자와 anti-unify·병합할 때 이 명세가 입력.

### ARC 풀이 중 각 기억에 들어가는 것

- **Working** — 지금 푸는 easy000a의 살아있는 상태: 주의 중인 노드(비교 중인 P0.G1·P1.G1), goal stack, 비교 결과(COMM/DIFF), 현재 impasse. 과제 끝나면 소멸.
- **Episodic** — ARCKG가 *시간순으로 겹겹이 쌓인* 풀이 경험: TASK→PAIR→GRID 하강 순서, 각 비교, COMM-copy 궤적. 에피소드 간 [[anti-unification]] 입력(Slice 2+). 사용자가 trace로 읽는 게 이것.
- **Semantic** — 인출 가능한 **DSL 추상 라이브러리**(아래 상세). 읽기 위주 + 학습으로 성장.
- **Procedural** — 동작규칙: C/D/A/B/K 기반 모듈 + 연산자 실행 본체(고차 연산자 실행형 포함) + elaboration/proposal/application 발화. WM을 자주 확인하며 불려간다.

### Semantic = DreamCoder식 DSL 추상 라이브러리

semantic의 본체는 도메인 사실(색 팔레트)이 아니라 **학습된 DSL 라이브러리**다:

1. **타입 온톨로지/스키마** — GRID·OBJECT·color·size가 무엇이고 어떤 구조인지.
2. **DSL 연산자 시그니처** — 각 연산자를 데이터 객체로: 이름·입력타입·출력타입·arg 스키마.
3. **합성 문법 / arg 제약** — 어떤 연산자가 어떤 연산자에 먹히는지(타입 호환 합성)를 선언적 제약으로.
4. **학습된 고급 DSL** — 합성해낸 고차 연산자를 새 선언적 구조로 적재. 인출·비교·병합 가능. *풀이를 거듭할수록 채워지는 핵심.*
5. (후속) **일반 개념** — symmetry, containment 등 재사용 개념.

[[dreamcoder]] 의 library learning 과 동형: 푼 문제에서 재사용 추상을 뽑아 라이브러리에 쌓고 재조합. → semantic은 *안 비고*(학습으로 성장), *억지도 아니다*(비교·병합이 선언적 표현을 필연적으로 요구).

### 타입 시스템의 두 얼굴

[[project-type-system-location]] 은 "타입 시스템 = procedural_memory 모듈"로 잡았으나, 이 프레임이 가른다: 타입을 *체크하는 실행 코드/dispatch*는 procedural, 타입·arg **스키마(시그니처)는 인출돼 합성·비교에 쓰이므로 semantic**. 같은 타입 시스템의 두 얼굴.

## 관련
- [[arbor-soar-memory-mapping]] — 선행 진단(semantic ≠ persisted WM). 이 노트가 그 "semantic엔 뭐가?" 열린 질문에 답함.
- [[dreamcoder]] — semantic = 학습된 DSL 추상 라이브러리의 모델.
- [[anti-unification]] — DSL 명세(semantic)를 입력으로 고차 추상 합성.
- [[arbor-dsl-taxonomy]] — DSL 4종 분리. 그 명세/본체가 semantic/procedural로 갈리는 자리.
- [[soar-manual-reference]] — SOAR procedural(발화)/semantic(인출) 정의 정본.
- [[arckg-research]] / [[arbor]] — 5계층 KG = persisted WM, 그 위 4기억 배치.

## 열린 질문
- **확장 메커니즘이 아직 선명하지 않음** (사용자 자평): 라이브러리가 *실제로 어떻게* 자라는지 미구현. 푼 과제가 새 추상을 언제·어떻게 deposit하나? 합성·병합을 무엇이 trigger하나? anti-unification 결과가 라이브러리로 돌아가는 회로는?
- semantic 인출이 D 모듈의 property 계산에 *언제* 개입하나 (온톨로지 인출 시점).
- 학습된 고급 DSL의 *명세(semantic)* 와 *본체(procedural)* 를 코드에서 어떻게 한 연산자로 묶어 동기화하나.
- 기억 *쓰기 시점*: load_task는 비우고 lazy flush (→ [[arbor-soar-memory-mapping]]); 그럼 procedural/semantic의 초기 적재(미리 vs 학습)는?
