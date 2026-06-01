---
title: ARBOR
aliases: [Abstraction Reasoning with Bottom-up Organized Rules, ARBOR system]
tags: [#topic/system, #project/active, #status/draft]
created: 2026-05-11
updated: 2026-05-18
sources:
  - raw/notion-task-kcc2026.md
  - raw/notion-idea-test-time-solving-process-analysis-2026-05-04.md
  - raw/notion-idea-test-time-generated-rule-analysis-2026-05-04-v2.md
  - raw/notion-meeting-2026-05-11.md
  - raw/notion-meeting-2026-05-18.md
  - raw/claude-soar-기반-자율-성장-지능체-이름-제안-2026-04-26.md
  - raw/notion-task-solver-development.md
  - raw/notion-task-arc-tbd-documenting-packaging.md
  - raw/claude-최근-활동-요약-요청-2026-04-30.md
---

# ARBOR

## 한 줄 정의
**A**bstraction **R**easoning with **B**ottom-up **O**rganized **R**ules — [[soar]] 인지 아키텍처와 5계층 [[arckg-research|ARCKG]] 를 결합한 순수 기호적 ARC 풀이 시스템. **현재 추진 중인 메인 프로젝트** (2026-05 기준).

## 위치 (다른 wiki 페이지와의 관계)
- [[arckg-research]] = ARBOR 의 **의미 메모리 (semantic memory)** 인 5계층 지식 그래프. ARCKG 는 데이터 구조의 이름, **ARBOR 는 그 위에서 동작하는 시스템 전체의 이름**.
- [[soar]] = ARBOR 의 **결정 엔진** (PSA 사이클, 표준 메커니즘 *수정 없이* 채택).
- [[anti-unification]] = ARBOR 가 내부 메커니즘으로 흡수해야 하는 **자동 일반화 루프** (현재 미구현, 핵심 과제).

## 명명 확정 (→ [[raw/claude-soar-기반-자율-성장-지능체-이름-제안-2026-04-26]])
2026-04-26 에 *ARBOR / LOGOS / NOUS / HEKA / SAGE / KARA / ANAX* 후보 중 **ARBOR** 채택. 라틴어로 *나무*, 계층적 성장의 이미지 + *Albert**tree*** 의 연결. KCC2026 논문에서 공식 명명 확정 (→ [[raw/notion-task-kcc2026]]).

> "ARBOR powered by ARCKG" — 데이터베이스(ARCKG)와 에이전트 시스템(ARBOR) 의 호명 분리.

## 설계 결정 — DSL 4종 분리 (→ [[arbor-dsl-taxonomy]], → [[raw/claude-arbor-dsl-4종-설계-결정-2026-05-18]])

ARC 풀이의 search 공간은 *transformation 의 조합* 이 아니라 **transformation 의 인자를 만드는 표현식의 합성 공간**. DSL 은 4 카테고리로 분리:

| 구분 | 역할 | 손코딩 |
|---|---|---|
| **transformation** | `make_grid`, `coloring` — 정확히 2개 frozen | ❌ (F3 적용) |
| **property** | `color-of`, `size-of`, `position-of`, ... — 한 노드 속성 | ⭕ 허용 |
| **relation** | `adjacent`, `inside`, `same-color`, ... — 두 노드 관계 | ⭕ 허용 |
| **util** | `objects-of`, `count`, `argmax`, ... — 집합·계산 도구 | ⭕ 허용 |

함의:
- **F3 정정**: hand-coded primitive 금지는 *transformation 에만* 적용. 나머지 3종은 합성의 *재료* 라 손코딩 권장.
- **"Lack of material" 의 더 깊은 원인**: 재료의 *양* 부족이 아니라 *종류* 부재 — property/relation/util 카테고리가 비어 있었음.
- **anti-unification 의 진짜 입력**: transformation tree 가 아니라 *argument expression tree*.
- **SOAR 와의 정렬**: LHS (condition) = property + relation 합성, RHS (action) = transformation. ARBOR 가 옵션 D 로 가도 SOAR 사용 패턴을 *더 정확히* 따른다.

상세는 [[arbor-dsl-taxonomy]].

## 아키텍처 (→ [[raw/notion-task-kcc2026]])
SOAR 의 표준 구조를 그대로 따름:

| 영역 | ARBOR 에서의 구체화 |
|---|---|
| **Semantic LTM** | [[arckg-research\|ARCKG]] — 5계층 (TASK → PAIR → GRID → OBJECT → PIXEL) |
| **Procedural LTM** | `procedural_memory/rule_NNN.json` — 발견된 변환 규칙 |
| **Episodic LTM** | `episodic_memory/` — 풀이 에피소드 (현재 비어있음) |
| **Working Memory** | (id, attr, value) **WME 삼중쌍** 집합 |
| **Decision Cycle** | elaborate → propose → select → apply |
| **Operator 순서** | `select_target` → `compare` → `extract_pattern` → `generalize` → `predict` → `submit` |
| **Impasse** | 풀이 실패가 아니라 **지식 격차의 진단 신호** (→ [[impasse]]) |

## Test-time 동작 (→ [[raw/notion-idea-test-time-solving-process-analysis-2026-05-04]])

### Fast path — 저장된 규칙 재사용
1. `procedural_memory/` 의 규칙들을 *재사용 횟수 순* 으로 로드
2. 각 규칙을 모든 example pair 에 적용
3. 하나라도 맞으면 test input 에 적용 → 답 반환 (identity rule 은 skip)
4. 맞는 규칙 없으면 → Slow path

### Slow path — SOAR 사이클로 새로 풀음
1. 문제를 ARCKG 로 변환
2. 두 grid 의 *2d array cell 단위 비교* (원래 의도는 component-wise descent 였으나 묵살됨)
3. 인접 변경 셀 grouping → (입력색, 출력색, 위치, 크기) 패턴 기록
4. `wm.s1["pattern"]` 에 단기 저장 (풀이 종료 후 사라짐)
5. `generalizeOperator` 의 `_try*` 함수들이 패턴 검출 → `rule_dict` 생성 (일반화 진행)

## 단일 궁극 목표 (재정의, → [[raw/notion-meeting-2026-05-18]])

> "**Build an agent whose knowledge grows and whose problems get solved in the way the user intends — relational, symbolic, bottom-up, self-extending. Solving ARC tasks is evidence, never the goal itself.**"

이전의 *"as many ARC tasks as possible"* 은 **폐기**. *1000 태스크를 1000개의 손코딩 detector 로 푸는 solver 는 실패*.

### Outer / Inner loop 재정의
- **Outer loop** (`run_loop.sh`): probe → invariant snapshot → invoke Claude → verify → **F1-F8 위반 시 auto `git revert`**, clean 시 commit. architectural integrity 자동 게이팅.
- **Inner loop** (`PROMPT.md`, **iter-agnostic** — 매 iter 동일 본문 발화): 현 코드 ↔ intended system 의 *smallest gap* 진단 → smallest defensible change 로 fill → F0 violation 0건 + ≥1 P-signal 개선이 reward.

→ [[arbor-signals]] 가 14개 signal (F1-F8 + P1-P6) 의 전체 명세.

## 현재 상태 (2026-05 기준)

### 3-task 풀이 시나리오 분해 → 11 모듈 도출 (2026-05-21)
사용자가 *내가 의도한 방식대로 ARBOR 가 작동하는 풀이 흐름* 을 easy000a / easy000b / 08ed6ac7 세 task 에 대해 줄글로 작성 (→ [[raw/notion-idea-arbor-flow-three-task-description-2026-05-21]]). 이를 PSA 5축 (WM / Operator / DSL / Memory I/O / Trigger) 으로 단계 분해 (→ [[raw/claude-arbor-flow-deep-analysis-2026-05-21]]) → cross-task 반복 메커니즘 11개 추출 (→ [[arbor-execution-trace]]). 본질적 미해결 질문 1개 (Q-B3 새 property 발명) + 방향만 있는 질문 7개 + 답 있음 4개 (→ [[arbor-open-questions]]).

**핵심 발견**:
- 4개월 메타 spec (signals, taxonomy, prompt-spec) 만 누적 → 0/1000 의 원인 = *실행 가능 framework 위에서만 spec 이 검증되는데 framework 자체가 비어 있었음*
- 현 ARC-solver 코드: SOAR 컨테이너 + ARCKG 노드 + compare 엔진은 있음. operator effect / elaboration rule / memory chunking·load·save / anti_unification 4 함수 — **모두 NotImplementedError 또는 `pass`**
- 다음 방향: *vertical slice first, horizontal extension* — 4 slice 계획 (easy000a → b → 08ed6ac7 → 변주+첫 skill)

### 1k iter 무한 루프 실험 결과 (→ [[raw/notion-meeting-2026-05-18]])
새 ultimate goal + F/P signals + iter-agnostic PROMPT.md 로 1000 iter 진행 결과:
- **0/1000 task solved properly** — anti-unification 시작도 못함 ("the initiation of anti-unification part haven't even started due to the lack of material")
- 결과 보고서: `raw/attachments/notion-meeting-2026-05-18/test20_iter1_to_999_report.html`
- 진단 (다음 미팅 토픽): *task 별 풀이가 task-specific 으로 끝나고 일반화 못함*. 예: 08ed6ac7 의 *"grey bars 보고 비교"* 는 그 task 만의 기술이라 그 자체로 일반화 불가.

### 이전 외부 평가 (→ [[raw/notion-idea-test-time-generated-rule-analysis-2026-05-04-v2]])
1000 task / Claude 개입 없음 (test13-eval):
- `rule_001 ~ 082`: Claude develop loop 에서 생성
- `rule_083 ~ 168`: 1k 평가 중 신규 생성
- **eval score: 72 / 1000**
- Episode 생성 안 됨

### 진단된 문제 (→ [[raw/notion-meeting-2026-05-11]])
1. **Unseen task 적응 불가** — seen pattern 없으면 못 풀음. *few-shot adaptive* 가 안 됨.
2. **Self-extension 안 됨** — Claude 도움 없이는 코드/규칙을 *본질적으로* 확장 못함. 86개 신규 규칙도 진정한 rule expansion 이 아님.
3. **실험 오염** — 20→40 task 늘리는 과정에서 ARBOR 가 임의로 200 task 시도. 통제 깨짐.
4. **규칙 구조 손상** — 본인이 의도한 `{조건부, 실행부}` DSL 설명서 구조에서 Claude 가 개발 중 **조건부를 날림** (→ [[raw/notion-idea-test-time-solving-process-analysis-2026-05-04]]).
5. **규칙 커버리지 < 1** — `풀이 태스크 수 / 누적 규칙 수` 가 두 시행 모두 1 미만, 태스크 증가해도 개선 안 됨. Chollet 의 [[interpolation-extrapolation|skill-acquisition efficiency]] 분모가 계속 증가하는 상태 (→ [[raw/notion-task-kcc2026]]).
6. **Anti-unification 미구현** — KCC 논문이 직접 future work 로 명시.

## 다음 과제

### 완료 (2026-05-13 ~ 18)
- [x] ARBOR 모듈 리스트 작성 — 전체 틀 점검 → **[[arbor-modules]]** (2026-05-13)
- [x] **Prompt 강화** — architecture detail, episodic/procedural memory 의 설계·용법·시스템 명시. 청사진: **[[arbor-prompt-spec]]** (2026-05-13). SOAR-ARC-test `test20` 브랜치에 CLAUDE.md / PROMPT.md / docs/RULE_FORMAT.md 반영.
- [x] **Session goal 재정의** — *max score* → *intended system development* 로 변경. 14 signal reward (→ [[arbor-signals]]).
- [x] **1000 iter 무한 루프 실행** — anti-unification 미시작으로 0/1000 결과. 다음 단계 진단 입력.

### 즉시 (2026-05-18 미팅 + DSL 4종 결정 후속)
- [x] **"Lack of material" 의 진짜 원인 진단** → 재료의 *종류* 부재 (property/relation/util 비어있음). [[arbor-dsl-taxonomy]] 작성 (2026-05-18).
- [x] **3-task 풀이 시나리오 분해 → 11 모듈 + spec gap 표** (2026-05-21). [[arbor-execution-trace]] + [[arbor-open-questions]].
- [ ] **F3 정정** — transformation 에만 적용, 다른 3종은 손코딩 허용. `CLAUDE.md §6` + [[arbor-signals]] F3 항목 갱신.
- [ ] **Slice 1 spec 한 페이지** — 5 모듈 (A,B,C,D,K + PredictByAllPairCommOp) 의 interface. easy000a 통과 위한 *최소* set.
- [ ] **Slice 1 코드 구현** — `agent/elaboration_rules.py`, `agent/active_operators.py` stub 채움 + `agent/compare_scheduler.py` + `agent/goal.py` + `procedural_memory/DSL/property/__init__.py`. `python run.py --task easy000a --log-wm` 통과.
- [ ] **씨앗 set 첫 구현** — property/relation/util 각 5-7개씩 (Slice 1 의 D 부분). 단 *암묵 property 14개* + *ranking util 3개* 추가 (3-task 분석 결과).
- [ ] **Slice 2 (easy000b)** — Module E (activation rule 1) + G + H (2-line linear) + I (depth-2) + C5. 회귀 없음 확인.
- [ ] **Slice 3 (08ed6ac7)** — Module C4 + C7 + ranking util + I2.
- [ ] **Slice 4 (변주 + 첫 skill)** — I3 첫 정의 + J 첫 등장.
- [ ] **Rule schema 확장** — `condition.params` 가 *표현식 트리* (`$expr`) 담을 수 있게.
- [ ] **Procedural / Episodic memory 상세 설계** — 현재 ARCKG (semantic) 수준 깊이로.
- [ ] **Soar 공식 메모리 메커니즘 참조** — SoarGroup/Soar github, episodic / procedural memory manual (→ [[soar]])
- [ ] Fast/Slow path 통합 — 두 phase 가 더 *적응적* 으로
- [ ] Harness 강화 — F1-F8 로 부분 해결됨, 추가 보강 필요

### 핵심 (KCC future work)
1. **Anti-unification 자동 일반화 루프** 를 `procedural memory` 저장 직후 단계로 통합. 두 규칙 사이 공통 골격 추출 → 더 일반적인 단위로 묶기. **규칙 커버리지 ≥ 1 달성**이 직접 목표.
2. **추상 단위 매칭 메커니즘** — 새 태스크 직면 시 누적된 추상 단위 중 적합한 것을 효율 검색·적용.

### 연구 인프라 (활성 task)
- [[raw/notion-task-solver-development]] *(In Progress, 2025-04 ~ )* — ARCKG OOP 재구성, comparison / hypothesis / rule / program 생성 모듈, Level 1-3 program, 2→3 abstraction rule, property 기반 후보 객체 검색.
- [[raw/notion-task-arc-tbd-documenting-packaging]] *(In Progress, 2025-03 ~ )* — ARC-TBD repo 의 재사용 가능 packaging. `dataset_update` / `thumbnail_gen` / `initialize` 함수, ARC1 / ARC2 / ARC1+2 선택, demo 와 구동계 분리.

## Hybrid 개발 모델 (→ [[raw/claude-최근-활동-요약-요청-2026-04-30]])
ARBOR 는 *두 개의 중첩 루프* 로 개발됨:
- **Inner loop**: ARBOR 가 ARC task 를 풀음 ([[soar]] PSA 사이클)
- **Outer loop**: Claude Code 가 ARBOR 의 코드를 개선 (별도 max 계정 무한루프, `PROMPT.md` + `run_pipeline.sh` + session log)

이 outer loop 가 *현재 발견된 모든 문제의 출처* — Claude 가 의도를 잡아먹고 (rule 조건부 누락), session goal 을 협소하게 추구 (score-maximize → no system improvement) 함. **Outer loop 자체를 통제 가능한 형태로 재설계** 하는 것이 메타 과제.

## 차별화 (vs [[dreamcoder]], → [[raw/notion-task-kcc2026]])
| 차원 | DreamCoder | ARBOR |
|---|---|---|
| 인식 모델 | Neural net | 순수 형식 논리 — full auditability |
| 라이브러리 구조 | Flat program fragments | 5계층 관계 그래프 ([[arckg-research]]) |
| 압축 원리 | [[mdl|MDL]] (통계) | [[anti-unification]] ([[structure-mapping-theory]] 기반, 인지과학적 정당성) |
| 학습 필요성 | Training examples 필요 | Zero-shot, 단일 task pair 에서 규칙 추출 (지향) |
| CA 위에서 동작? | ❌ | ✅ ([[soar]]) |

## 관련
- [[arbor-execution-trace]] — **3-task 분해에서 도출된 11 모듈 + spec gap 표 + slice 계획** (2026-05-21 신규)
- [[arbor-open-questions]] — **11 미해결 질문 누적** (사용자 prose 의 "(아직 모르겠어)" 명시적 보존)
- [[arbor-modules]] — 모듈 인벤토리 (의도 ↔ 두 레포 상태)
- [[arbor-prompt-spec]] — outer loop 두 문서 (CLAUDE.md / PROMPT.md) 청사진
- [[arbor-signals]] — F1-F8 (forbidden) / P1-P6 (positive) reward signals
- [[arbor-dsl-taxonomy]] — DSL 4종 분리 (transformation frozen + property/relation/util 손코딩 허용)
- [[arckg-research]] — ARBOR 의 의미 메모리
- [[soar]] — ARBOR 의 결정 엔진
- [[anti-unification]] — 핵심 미구현 메커니즘
- [[impasse]] — 지식 격차 신호로 사용
- [[interpolation-extrapolation]] — Chollet skill-acquisition efficiency, 규칙 커버리지 지표의 이론적 근거
- [[dreamcoder]] — 차별화 타깃 (Module J SkillLibrary 의 비교 대상; ARBOR 는 vector 가 아닌 *symbolic* 구조 비교)
- [[agentness]] — ARBOR 의 에이전트성 분석
- [[structure-mapping-theory]] — Module E (ActivationRule) 의 *관계의 관계* 비교 (easy000b 의 핵심) 의 인지과학 근거

## 열린 질문
- **Outer loop 통제**: Claude Code 의 자율 코드 개선을 어떻게 사용자 의도와 정합되게 유지할 것인가?
- **Rule 조건부 복원**: `{조건부, 실행부}` 구조를 강제하면 fast path 의 성능은 어떻게 변하는가?
- **Anti-unification 통합 지점**: procedural memory 저장 *직후* 가 맞는가, 아니면 별도 sleep phase 가 필요한가?
- **Episodic memory 의 실제 용도**: 현재 비어있음. 어떤 정보를 누적하고 언제 활용할 것인가?
- **Cell 단위 비교의 정당성**: 원래 의도였던 *component-wise descent* 가 묵살된 게 본질적 손실인가, 단순 최적화인가?
- **Outer loop 의 실험 오염**: ARBOR 가 의도되지 않은 200 task 를 시도한 원인은 무엇이며, 어떻게 harness 로 차단할 것인가?
