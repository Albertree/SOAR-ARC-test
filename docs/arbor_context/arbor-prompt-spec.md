---
title: ARBOR Outer Loop Prompt 명세
aliases: [prompt.md spec, ARBOR prompt design, outer loop prompt]
tags: [#topic/system, #project/active, #status/draft]
created: 2026-05-13
updated: 2026-05-18
sources:
  - raw/notion-meeting-2026-05-11.md
  - raw/notion-meeting-2026-05-18.md
  - raw/notion-task-kcc2026.md
  - raw/notion-idea-test-time-solving-process-analysis-2026-05-04.md
---

# ARBOR Outer Loop Prompt 명세

> **갱신 (2026-05-18, → [[raw/notion-meeting-2026-05-18]])**: PROMPT.md 는 결국 *iter-agnostic* (매 iter 동일 본문) 으로 진화. session 별 mission 이 아니라 *single ultimate goal* 를 발화하고, reward 는 [[arbor-signals|F1-F8 / P1-P6 의 14 signal]] 로 형식화됨. 첫 mission (legacy migration) 은 *iter strategy* 안에 흡수됨 — 더 이상 별도 session 으로 잡지 않음.

## 목적
`SOAR-ARC-test/PROMPT.md` 와 `SOAR-ARC-test/CLAUDE.md` 의 *재작성을 위한 청사진*. 직접 prompt 를 쓰지 않고, 어떤 섹션이 어떤 결함을 차단하는지 매핑 후 그 위에 본문을 채운다. 입력은 [[arbor-modules]] §9 + [[arbor]] (의도된 구조) + [[arbor-signals]] (14 signals).

## 두 문서의 역할 분리

| 문서 | 역할 | 변경 빈도 | 입력 |
|---|---|---|---|
| **`CLAUDE.md`** | *정적* 아키텍처 명세 — *불변* 사실 (모듈 구조 / 메모리 스키마 / cycle invariants / DSL 인터페이스). Claude Code 가 매 iter 첫 부분에서 읽음. | 거의 안 바뀜 | [[arbor-modules]] §1-7, [[arckg-wm-design]], [[arckg-3repository]], [[arckg-node-edge]] |
| **`PROMPT.md`** | *Iter-agnostic* mission — *어떤 iter 인지에 관계없이* 동일 본문 발화. *single ultimate goal* + 진단·수정·검증 5단계 절차. | **고정** (2026-05-18 시점, iter-agnostic 으로 안정화) | [[arbor]] *단일 궁극 목표*, [[arbor-signals]] |
| **`docs/INVARIANTS.md`** | F1-F8 + P1-P6 의 *코드 차원 캐논*. PROMPT.md 가 매 iter 참조. | F/P signals 자체가 바뀔 때만 | [[arbor-signals]] |

> **원칙**: *불변* 은 CLAUDE.md, *가변* 은 PROMPT.md. 현재 `run_loop.sh` 안에 hardcode 된 매-session prompt 가 *가변+불변* 을 섞어서 매번 architecture detail 을 잃어버리는 게 문제 ([[arbor-modules]] §9 결함 #2, [[raw/notion-meeting-2026-05-11]]).

---

## 7대 결함 → 7대 제약 매핑 (직접 변환표)

| # | 결함 ([[arbor-modules]] §9) | Prompt 제약 | 어느 문서 |
|---|---|---|---|
| 1 | Score-maximize 편향 | **Session goal 재정의** — 보상 = *score 개선 × 시스템 발전 지표*. 시스템 발전 0 이면 score 만점도 인정 안 함. | PROMPT.md |
| 2 | `_try_*` / `_apply_*` 무한 누적 권장 | **이 가족에 새 메서드 추가 금지**. 일반화는 `program/anti_unification.py` 호출로만. | CLAUDE.md (불변) |
| 3 | Rule format 의 `condition` 부재 | **rule.json 스키마 필수 키 명시**: `{condition: {...}, action: {...}}` 둘 다 있어야 valid. 없으면 거부. | CLAUDE.md (불변) |
| 4 | Anti-unification 호출 의무 없음 | **Cycle 정의 안에 호출 지점 명시**: 두 개 이상의 pair-specific program 이 procedural_memory 에 저장될 때 `anti_unification.unify()` 가 자동 호출되어야 함. | CLAUDE.md (불변) |
| 5 | Episodic memory 의무 없음 | **Episode writer 호출 의무화**: 풀이 종료 시 (성공·실패 무관) `episodic_memory/{task_id}/attempt_NNN/` 생성 강제. | CLAUDE.md (불변) |
| 6 | Auto-grow on 100% (실험 오염) | **Task pool 자동 확장 금지**. `--limit` 는 사용자 명시. session 안에서 pool 변경 금지. | PROMPT.md + run_loop.sh 수정 |
| 7 | CATEGORY 제약 약함 | **"category 처리" 의 정의** = *동일 anti-unification 골격을 공유하는 task 집합*. CATEGORY 추가는 새 골격 도출 시에만 인정. | PROMPT.md |

---

## CLAUDE.md — 섹션 구조 (불변 명세)

1. **시스템 개요** — ARBOR = [[soar]] + [[arckg-research|ARCKG]]. 4문장 이내. [[arbor]] §한줄정의 발췌.
2. **레포 구조** — [[arbor-modules]] §1-7 의 모듈 트리를 그대로. 각 모듈 한 줄 설명.
3. **메모리 스키마** — 3-Repository 의 *불변* 형식 ([[arckg-3repository]]):
   - ARCKG node 형식 (`N_T{hex}/E_*.json`, [[arckg-node-edge]])
   - **rule.json 스키마** (제약 #3) — JSON Schema 형태로 명시
   - episode 형식 (제약 #5)
4. **Cycle invariants** — `cycle.py` 의 PSA 사이클 + impasse trigger 정의 ([[arckg-wm-design]]). **수정 금지 파일**: `cycle.py`, `wm.py`, `data/`, `ARCKG/*.py` 의 노드 클래스.
5. **Operator 가족** — 6종 ([[arbor-modules]] §4). 각 operator 의 입력/출력 계약. **`_try_*` / `_apply_*` 추가 금지** (제약 #2). 새 변환은 `program/anti_unification.py` 호출 경유.
6. **DSL 인터페이스** — `apply_DSL()` 의 contract. 새 primitive 추가 시 어디에 등록할지.
7. **WM 표기 규약** — `S1 ^operator O1 +` 등 Soar-style preference 표기 (현 ARC-solver README 에서 발췌).
8. **Anti-unification 호출 지점** (제약 #4) — `agent/memory.py` 의 어느 함수가 언제 invoke 하는지. 명시되지 않은 다른 곳에서 호출하면 architecture violation.

> **CLAUDE.md 작성 시 주의**: *어떻게 풀어라* 가 아니라 *무엇이 시스템인가* 만 적는다. *과제* 는 PROMPT.md.

---

## PROMPT.md — 섹션 구조 (가변 과제)

1. **Mission 한 줄** — 이번 session 이 추구하는 *시스템 발전*. 예시: *"규칙 커버리지를 1.0 이상으로 끌어올려라"*. Score 가 아닌 *system metric* 으로 표현 (제약 #1).
2. **Session Goal 재정의** (제약 #1) —
   ```
   Reward = ΔScore × ΔSystem_Metric
   if ΔSystem_Metric ≤ 0: reward = 0  (score만 오른 것 인정 안 함)
   ```
3. **허용 행위** (whitelist) — 명시된 것만 허용:
   - `program/anti_unification.py` 의 수정·확장
   - `agent/memory.py` 의 anti-unification 호출 추가
   - rule.json 의 *기존* 항목에 `condition` 키 추가 (제약 #3 마이그레이션)
4. **금지 행위** (blacklist) —
   - `cycle.py`, `wm.py`, `ARCKG/*.py`, `data/` 수정 금지
   - `active_operators.py` 의 `_try_*` / `_apply_*` 메서드 추가 금지 (제약 #2)
   - rule.json 에 `condition` 키 없는 항목 *신규* 추가 금지 (제약 #3)
   - `--limit` task pool 자동 확장 금지 (제약 #6)
5. **검증 지표** (다음 섹션 참조)
6. **CATEGORY 정의** (제약 #7) — *"동일 anti-unification 골격을 공유하는 task 집합"*. session 끝에 새 CATEGORY 를 주장하려면 골격 (anti-unified program) 을 제시해야 함.
7. **Session 끝 산출물 형식** — `logs/session_log.md` 에 append 할 정형 보고서 (예: "Anti-unification 시도: N회, 골격 발견: M개, 새 condition 추가: K개, ΔScore: ±x").

---

## 검증 지표 (System Metrics)

[[arbor-modules]] §9 의 결함이 *측정 가능한 형태* 로 변환된 것. session 종료 시 자동 측정·기록:

| 지표 | 측정 | 합격 기준 (session 단위) |
|---|---|---|
| **Rule coverage** | `풀이 task / 누적 rule 수` | session 동안 *감소하지 않음* (이상적: ≥1.0) |
| **Condition-fill ratio** | `condition 키 있는 rule / 전체 rule` | session 동안 *증가* (목표: 1.0) |
| **Anti-unification invocations** | `program/anti_unification.unify()` 호출 횟수 | session 당 ≥ 1 (제약 #4) |
| **Episode count** | `episodic_memory/` 의 attempt 수 | 풀이 task 수와 동일 (제약 #5) |
| **`_try_*` family delta** | `active_operators.py` 의 `_try_*` 메서드 신규 추가 수 | **= 0** (제약 #2) |
| **Task pool drift** | session 시작·끝의 `--limit` 차이 | **= 0** (제약 #6) |
| **Score** | `correct / total` | 참고 지표. 단독으로는 reward 산정 안 함 (제약 #1) |

**합격 = 모든 지표 합격**. 하나라도 실패 시 session 결과 *roll back* (git revert HEAD).

---

## 보조 문서 (선택적)

| 파일 | 역할 |
|---|---|
| `docs/ARCHITECTURE.md` | CLAUDE.md 가 너무 두꺼워지면 분리. 깊은 설명은 여기로. |
| `docs/RULE_FORMAT.md` | rule.json JSON Schema 의 *완전한 정의* + 예시 5개 (good / bad / migration). |
| `docs/ANTI_UNIFICATION.md` | [[anti-unification]] 알고리즘 + [[object-level-lifting]] + 호출 지점 흐름도. |
| `docs/SESSION_LOG_FORMAT.md` | `logs/session_log.md` 의 정형 형식. 자동 파싱 가능하게. |

> wiki 의 [[arckg-3repository]], [[anti-unification]], [[arckg-wm-design]], [[arckg-node-edge]] 가 이 보조 문서들의 *원천 자료*.

---

## 작성 순서

1. **CLAUDE.md 초안** — [[arbor-modules]] §1-7 + ARC-solver README 의 모듈 트리·WM 표기 규약 발췌. *불변* 사실만.
2. **`docs/RULE_FORMAT.md`** — 제약 #3 의 JSON Schema 확정. CLAUDE.md 가 이 문서를 참조.
3. **`docs/ANTI_UNIFICATION.md`** — 제약 #4 의 호출 지점 흐름도. CLAUDE.md §8 이 이 문서를 참조.
4. **PROMPT.md** — 1번 session 의 *Mission* 으로 *"기존 168 rule 의 condition 키 마이그레이션 + anti-unification 호출 1회 이상"* 같은 **달성 가능한 첫 목표** 부터.
5. **`run_loop.sh` 의 mktemp prompt 제거** — 위 PROMPT.md 를 직접 cat 으로 읽어 사용. auto-grow 분기 제거 (제약 #6).

---

## 관련
- [[arbor]] — 시스템 허브
- [[arbor-modules]] — 본 명세의 직접 입력
- [[anti-unification]] — 제약 #4 의 메커니즘
- [[arckg-3repository]] — 메모리 스키마 원천
- [[arckg-wm-design]] — Cycle invariants 원천
- [[arckg-node-edge]] — Node/Edge 형식 원천
- [[object-level-lifting]] — anti-unification 전처리

## 열린 질문
- **첫 session 의 Mission** 으로 무엇이 가장 적합한가? 후보: ① rule condition 마이그레이션 ② anti-unification 호출 통합 ③ episodic memory writer 통합. ②가 가장 본질이지만 ①이 가장 가벼움.
- **Roll-back 정책** — 지표 하나 실패 시 git revert 가 매번 강제되면 점진 개선 불가. 어떤 지표는 *경고* 로만 둘 것인가?
- **`anti_unification.unify()` 호출 카운트** 를 어떻게 측정? 함수 안에 logger 박으면 단순하지만, Claude Code 가 logger 우회할 수도. 더 robust 한 방법?
- **CATEGORY 의 anti-unification 골격** 을 session log 에 어떻게 직렬화할 것인가? 자유 텍스트 vs 형식 JSON?
- CLAUDE.md 와 wiki 사이의 *동기화* — wiki 가 변경되면 CLAUDE.md 도 갱신되어야 하나, 그 흐름을 누가 트리거하는가?
