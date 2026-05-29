---
title: ARBOR 모듈 인벤토리
aliases: [ARBOR modules, ARBOR module map, ARBOR component list]
tags: [#topic/system, #project/active, #status/draft]
created: 2026-05-13
updated: 2026-05-13
sources:
  - raw/notion-meeting-2026-05-11.md
  - raw/notion-task-kcc2026.md
  - raw/notion-idea-test-time-solving-process-analysis-2026-05-04.md
  - raw/notion-task-solver-development.md
  - raw/notion-task-arc-tbd-documenting-packaging.md
---

# ARBOR 모듈 인벤토리

## 목적
ARBOR 시스템이 *무엇을 갖고 있고 무엇이 없는지* 의 단일 테이블. 2026-05-11 미팅의 첫 액션 아이템 ("ARBOR 아키텍처가 무엇을 가지고 있는지 없는지, 모든 모듈리스트를 제작해서 전체적인 틀을 짠다"). 이 페이지가 `prompt.md` 의 *architecture detail* 섹션의 입력.

## 레포 구분
- **ARC-solver** (`~/Desktop/ARC-solver/`): 손수 개발, 의도된 설계가 더 정확.
- **SOAR-ARC-test** (`~/Desktop/SOAR-ARC-test/`): Claude infinite loop 실험장.

두 레포의 `ARCKG/ / agent/ / managers/ / program/ / basics/` 는 **동일 구조**. 차이는 harness 와 메모리 데이터.

---

## 1. Storage Layer (LTM 3종)

| 모듈 | 의도 ([[arckg-3repository]]) | ARC-solver 상태 | SOAR-ARC-test 상태 | Gap |
|---|---|---|---|---|
| `semantic_memory/` | Declarative — *"이 문제는 무엇인가"*. TASK/PAIR/GRID/OBJECT/PIXEL 노드 + 비교 엣지. **TF_GRID 금지**. | 비어 있음 (0 entries) | 1000 entries (1k 실험) | — |
| `procedural_memory/` | Programs / skills. **`{조건부, 실행부}` DSL 설명서** ([[raw/notion-idea-test-time-solving-process-analysis-2026-05-04]]). | 비어 있음 | **168 rule.json** — `condition` 키 부재. `rule.type` + 파라미터만 있음 | **조건부 누락** — KCC 진단의 직접 증거 |
| `episodic_memory/` | Execution traces. *self-evolution loop* 인프라. | 비어 있음 | **0 entries** (1k 평가 후에도) | **에피소드 생성 안 됨** — KCC 진단 |
| `procedural_memory/DSL/` | apply / transformation / selection / util / layer. operator 내부 호출용. | ✅ | ✅ | — |

**과제**:
1. rule.json 스키마에 `condition` 필수 키 추가 + 검증
2. episodic_memory writer 가 어디서 호출되어야 하는지 명세 (현재 cycle.py 가 호출 안 함)

---

## 2. ARCKG Layer (5계층 + 관계)

| 모듈 | 의도 | 상태 | Gap |
|---|---|---|---|
| `ARCKG/task.py` | TASK 노드 (`T{hex}`) | ✅ | — |
| `ARCKG/pair.py` | PAIR 노드 (`T.P{n}`) | ✅ | — |
| `ARCKG/grid.py` | GRID 노드 (`T.P.G{0|1}`) | ✅ | — |
| `ARCKG/object.py` | OBJECT 노드 ([[object-level-lifting]] 의 anchor) | ✅ | anti-unification 이 객체 수준에서 동작하는지 미검증 |
| `ARCKG/pixel.py` | PIXEL 노드 | ✅ | — |
| `ARCKG/comparison.py` | `compare()` — COMM/DIFF receipt 생성 ([[arckg-node-edge]]) | ✅ | **2차 relation 미지원** — edge-of-edge 비교 ([[arckg-node-edge]]) |
| `ARCKG/hodel.py` | Hodel `objects()` — 객체 검출 | ✅ | — |
| `ARCKG/memory_paths.py` | 노드 ID → 파일 경로 변환 | ✅ | — |

**과제**:
1. `comparison.py` 에 2차 relation 지원 — `compare(edge1, edge2)` 가능하게
2. "가장 긴" 같은 derived/ranking 속성을 어떻게 표현할지 ([[arckg-node-edge]] 의 한계 발견 사례)

---

## 3. Agent Layer (SOAR core)

| 모듈 | 의도 | 상태 | Gap |
|---|---|---|---|
| `agent/wm.py` | WME triplet, S1/S2 상태 스택 ([[arckg-wm-design]]) | ✅ 뼈대 | impasse 가 *필드* 가 아닌 *구조적 전이* 로 정확히 구현됐는지 검증 필요 |
| `agent/elaboration_rules.py` | ElaborationRule, Elaborator — fixed-point 까지 derivation | ✅ | **어떤 derivation 을 자동화할지 미정** ([[arckg-research]] 열린 질문) |
| `agent/rules.py` | ProductionRule, Proposer — operator 후보 제안 | ✅ | — |
| `agent/preferences.py` | `select_operator()` — PREFERENCE_ORDER 기반 | ✅ | — |
| `agent/cycle.py` | `run_cycle()` — Elaborate→Propose→Select→Apply + impasse trigger (MAX_SUBSTATE_DEPTH=2) | ✅ | episodic_memory writer 호출 안 함 |
| `agent/memory.py` | `chunk_from_substate` / LTM 저장·로드 | ✅ | **anti-unification 통합 지점이 여기인지 확인** |
| `agent/active_agent.py` | `ActiveSoarAgent` — env 호환 인터페이스 | ✅ | — |
| `agent/agent_common.py` | `build_wm_from_task` / `goal_satisfied` / `answers_from_wm` | ✅ | — |
| `agent/io.py` | input-link / output-link 구조 | ✅ | — |
| `agent/wm_logger.py` | WM 상태 로깅 (디버깅) | ✅ | — |
| `agent/propose_wm.py` | (이름으로 추정) WM 제안 단계 | ✅ | 역할 명세 미문서 |

**과제**:
1. `cycle.py` 의 impasse 처리 — substate 안에서 *부족한 지식이 무엇인지* 의 구체화 ([[impasse]] knowledge-gap vs abstraction-gap 구분)
2. `memory.py` 에 **anti-unification 자동 일반화 루프 통합** (KCC future work [1])
3. `propose_wm.py` 의 역할 README 에 명세

---

## 4. Operators

`agent/active_operators.py` 에 6종:

| Operator | 의도 | 상태 | Gap |
|---|---|---|---|
| `SelectTarget` | agenda 에서 pending → 비교 대상 선정 | ✅ | — |
| `Compare` | `compare()` 호출 → 관계 생성 | ✅ | 2차 relation 미지원 |
| `ExtractPattern` | COMM → invariant, DIFF → diff_pattern 분류 | ✅ | — |
| `Generalize` | 추상 규칙 생성·저장 — `_try_*` 패턴 검출기 다수 | ⚠️ | **이게 outer loop 가 무한정 추가하는 곳** (run_loop.sh 의 직접 타깃). [[anti-unification]] 으로 대체되어야 할 위치. |
| `Predict` | 매칭 `_apply_*` 호출 → test 출력 예측 | ⚠️ | `_try_*` ↔ `_apply_*` 쌍이 손으로 동기화. 자동화 필요. |
| `Submit` | goal 완료 | ✅ | — |
| `SolveTaskOperator` | 추상 operator (S1 에서 no-change → S2 trigger) | ✅ | — |

**과제**:
1. `Generalize` 의 `_try_*` 가족을 [[anti-unification]] + [[object-level-lifting]] 으로 대체. 무한 if-elif 누적 차단
2. `_try_*` ↔ `_apply_*` 일대일 강제 (스키마 검증)

---

## 5. Program / Generalization

| 모듈 | 의도 | 상태 | Gap |
|---|---|---|---|
| `program/anti_unification.py` | 관계 trace → 추상 규칙 일반화 ([[anti-unification]]) | ✅ 파일 존재 | **`cycle.py` / `memory.py` 에서 호출되는지 미확인** — 호출되지 않으면 KCC 진단의 핵심 원인 |

**과제**: 호출 지점 명세 후 `memory.py` 또는 `Generalize` operator 의 effect 함수에서 invoke.

---

## 6. DSL Layer (`procedural_memory/DSL/`)

| 모듈 | 의도 | 상태 |
|---|---|---|
| `apply.py` | `apply_DSL()` 디스패처 | ✅ |
| `transformation.py` | 그리드/객체 변환 함수 | ✅ |
| `selection.py` | `find_object()` | ✅ |
| `util.py` | 헬퍼 | ✅ |
| `layer.py` | 90×90 캔버스 레이어 시스템 | ✅ |

**Gap**: DSL primitive 가 어떤 *조건* 에서 쓰여야 하는지의 메타 정보 (= rule.json 의 `condition` 키) 가 분리되어 있지 않음.

---

## 7. Manager / Env / Basics

| 모듈 | 역할 | 상태 |
|---|---|---|
| `managers/arc_manager.py` | data/ 로드 → ARCKG 노드 계층 구성 | ✅ |
| `env/arc_environment.py` | `ARCEnvironment` — 태스크 제공, 채점, trace | ✅ |
| `basics/viz.py` | ANSI 시각화 (show_task / show_objects / show_comparison) | ✅ |
| `basics/utils.py` | 기타 유틸 | ✅ |

---

## 8. Harness Layer

| 모듈 | ARC-solver | SOAR-ARC-test | 비고 |
|---|---|---|---|
| `main.py` | ✅ 단일 진입점 | ✅ | — |
| `run.py` / `run.sh` | ✅ | ❌ | ARC-solver 전용 |
| `init.py` | ✅ 메모리 초기화 | ❌ | — |
| `run_task.py` | ❌ | ✅ 단일 태스크 | — |
| `run_learn.py` | ❌ | ✅ session 학습 (`--limit` `--shuffle`) | outer loop 가 호출 |
| `run_1ktasks.py` | ❌ | ✅ 1k 평가 | KCC 평가 산물 |
| `run_loop.sh` | ❌ | ✅ **infinite loop** | 핵심 outer loop |
| `run_pipeline.sh` | ❌ | ✅ | — |
| `PROMPT.md` | ❌ | ✅ (구버전, 1812B) | **재작성 대상** |
| `CLAUDE.md` | ❌ | ✅ (구버전, 5793B) | **재작성 대상** |
| `logs/` | ❌ | ✅ session log | — |
| `eval_results.json` / `.md` | ❌ | ✅ | — |
| `docs/REFERENCE.md`, dev_log | ✅ | ❌ | — |

---

## 9. Outer Loop 의 결함 (`run_loop.sh` 분석)

### 현재 prompt (loop 안에서 mktemp 로 매 session 생성)
> "Pick 1-3 INCORRECT tasks. Add `_try_*` methods in `GeneralizeOperator`. Add matching `_apply_*` methods in `PredictOperator`. Verify run_learn.py shows improvement. Do NOT modify: data/, agent/cycle.py, agent/wm.py. Each strategy must handle a CATEGORY of tasks, not just one."

### 진단된 결함
1. **Score-maximize 편향** — "INCORRECT tasks 를 풀어라" 가 직접 목표. 시스템 발전 자체가 보상 함수에 없음 ([[arbor]] 진단 #2, [[raw/notion-meeting-2026-05-11]]).
2. **`_try_*` / `_apply_*` 가족 무한 누적** 을 *권장* — anti-unification 의 자리를 빼앗음.
3. **Rule format 제약 없음** — `condition` 키 강제 없음 → 168개 rule 이 조건부 없이 누적됨.
4. **Anti-unification 시도 의무 없음** — `program/anti_unification.py` 호출이 prompt 어디에도 없음.
5. **Episodic memory 의무 없음** — 1k 풀이 후에도 0 entries.
6. **Auto-grow on 100%** (task pool 2배) — outer loop 가 본인이 정한 *재현 가능한 평가 조건* 을 깬다. 실험 오염의 직접 원인 ([[arbor]] 진단 #3).
7. **CATEGORY 제약은 약함** — *"한 category 의 task 들을 처리"* 가 *anti-unification 기반 일반화* 와 동치인지 검증 안 됨.

---

## 다음 작업으로의 입력

이 인벤토리는 **prompt.md 의 architecture detail 섹션의 입력**. 다음 단계 ([[arbor]] *다음 과제* 의 *Prompt 강화*) 에서:

- **§1-2 (Storage / ARCKG)** → prompt 의 *Memory 스키마* 섹션
- **§3 (Agent)** → prompt 의 *Cycle invariants* (`cycle.py`, `wm.py` 수정 금지)
- **§4-5 (Operators / Generalization)** → prompt 의 *Rule format + anti-unification 의무* 섹션 — 가장 두꺼워질 곳
- **§9 (현재 결함)** → prompt 의 *금지 사항 + 검증 지표* 섹션

## 관련
- [[arbor]] — 시스템 허브
- [[arckg-3repository]] — Storage 3분리
- [[arckg-wm-design]] — WM 영역 + impasse 메커니즘
- [[arckg-node-edge]] — Node/Edge 형식 + 2차 relation
- [[anti-unification]] — Generalization 의 의도된 메커니즘
- [[object-level-lifting]] — Generalize 가 객체 수준에서 동작하기 위한 전처리
- [[impasse]] — Cycle 의 substate 자동 생성
- [[adaptive-search]] — 탐색 순서 결정

## 열린 질문
- `agent/memory.py` 의 `chunk_from_substate` 가 [[anti-unification]] 호출의 자연스러운 위치인가, 아니면 `Generalize.effect()` 안인가?
- `propose_wm.py` 의 역할이 README 에 없음 — `rules.py` 와 어떻게 다른가?
- `_try_*` / `_apply_*` 가족을 [[anti-unification]] 으로 대체할 때 기존 168 rule 의 *데이터* (concept / category / covers 메타) 는 어떻게 마이그레이션할 것인가?
- Outer loop 의 *재현 가능 평가 조건* 을 prompt 안에서 어떻게 강제할 것인가 (auto-grow 차단)?
