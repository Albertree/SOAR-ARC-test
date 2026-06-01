---
title: ARBOR Reward Signals (F1-F8 / P1-P6)
aliases: [forbidden-positive-signals, F-signals, P-signals, ARBOR invariants]
tags: [#topic/system, #project/active, #status/active]
created: 2026-05-18
updated: 2026-05-18
sources:
  - raw/notion-meeting-2026-05-18.md
---

# ARBOR Reward Signals

## 한 줄 정의
[[arbor]] outer loop 의 **reward 함수** — ARC score 가 아니라 *forbidden 위반 0건 + positive 개선 ≥1건* (→ [[raw/notion-meeting-2026-05-18]]). SOAR-ARC-test 의 `docs/INVARIANTS.md` 가 *코드 차원* 의 캐논, 이 페이지는 *wiki 차원* 의 합성.

## 위치
이 14개 signal 은 [[arbor-prompt-spec]] 의 *7대 결함 → 7대 제약* 매핑이 발전한 형태. PROMPT.md 가 **iter-agnostic** (매 iter 동일 본문) 으로 바뀌면서 reward 함수 자체가 분리·체계화됨.

| 카테고리 | 역할 | 작동 |
|---|---|---|
| **F1-F8** (Forbidden) | **게이트** — 트립 시 auto `git revert HEAD` | 어느 하나라도 위반 → iter reward 0 |
| **P1-P6** (Positive) | **그래디언트** — 하나라도 개선 시 iter "clean" | 어느 하나라도 개선 → 진전 인정 |
| **Stagnation** | 3+ 연속 iter 에 P 개선 0건 | 정보용 로깅만, auto-revert 없음 |

---

## Forbidden Signals (F1-F8)

| ID | 이름 | 금지 행위 | 이유 |
|----|------|-----------|------|
| **F1** | Frozen files modified | `data/`, `agent/cycle.py`, `agent/wm.py`, `ARCKG/{task,pair,grid,object,pixel}.py` 변경 | SOAR 사이클 + 5계층 노드 identity contract. 변경은 architecture change 지 session task 가 아님. |
| **F2** | New `_try_*` / `_apply_*` | `agent/active_operators.py` 의 이 가족에 새 메서드 추가 (기존 bug-fix 는 OK) | test13-eval 의 168 sub-coverage rule 을 만든 직접 패턴. 새 category 응답은 [[anti-unification|AU]] 또는 새 matcher 이지 새 detector 가 아님. |
| **F3** | Hand-coded DSL primitive | `procedural_memory/DSL/` 에 `coloring` / `make_grid` 외 새 `@register` | **DSL 은 의도적으로 under-equip** — 정확히 2 primitive 만. 다른 변환(move/rotate/flip/scale…) 은 *AU 가 데이터로 발견* 해야 함, Python 으로 적으면 안 됨. |
| **F4** | Rule saved without `condition` | `validate_rule()` 실패하는 새 `rule_*.json` | condition 없으면 fast path 가 매칭 못함 → dead memory. 168-rule failure mode 의 직접 형태. |
| **F5** | TF_GRID in `semantic_memory/` | `semantic_memory/` 안에 `TF_` 또는 `tf_grid` 경로 | semantic 은 declarative ARCKG 노드 전용. transformed grid 는 `episodic_memory/` 행. 섞으면 static/dynamic 분리 깨짐 ([[arckg-3repository]]). |
| **F6** | Auto-grown limit / task pool | script 가 mid-run 에 task budget 을 곱하기 | 옛 "100% score → grow pool" 이 재현 가능 평가 조건을 깸. budget 은 사용자가 CLI 로만 제어. |
| **F7** | `RuleSchemaError` swallowed | `except RuleSchemaError: pass / continue` 가 re-raise/log 없이 | 조용한 삼킴 = 검증 없음. invalid rule 생존. |
| **F8** | Score-chasing edit to `active_operators.py` | `active_operators.py` 의 net-positive 추가가 `memory.py` / `anti_unification.py` / `conditions/` 변경 없이 단독 | 옛 "generalizer hand-tune" 패턴. 순수 삭제·리팩터·doc-only 는 면제. |

---

## Positive Signals (P1-P6)

| ID | 이름 | 측정 | 진전 방향 |
|----|------|------|------------|
| **P1** | Rule coverage | `solved_tasks / total_rules` (Chollet skill-acquisition efficiency) | rule 의 `covers` 증가, AU 로 두 rule 병합, 저장된 rule 이 새 task 풀이 → 상승. task 마다 새 rule → 하강. |
| **P2** | Mean covers per rule | rule 당 일반성 — *"rule 이 잘 추상화함"* 의 단조 proxy | AU 가 끌어올림. hand-coding 은 1 에 고정. |
| **P3** | Non-null `anti_unification_trace` 비율 | 저장 rule 중 *generalize 된* 비율 (vs source-only) | 상승 = AU 가 wired & firing. |
| **P4** | Episodic memory entries | `episodic_memory/<task>/attempt_NNN/` 수 | `solve()` 호출 수와 선형 비례해야. 역사적으로 1k run 후에도 빈 상태 → writer 우회됨. |
| **P5** | Distinct `condition.type` 수 | `len(CONDITION_REGISTRY)` | 패턴 recognition vocabulary 의 성장. matcher 추가는 허용 (frozen *transformation* axis 와 별개의 *recognition* axis). |
| **P6** | `active_operators.py` net code 삭제량 | 누적 line-count delta | **Net-negative 가 가장 강한 단일 진전 신호** — AU 가 일을 하면 `_try_*` 는 *삭제*되지 *확장* 되면 안 됨. |

---

## 핵심 비대칭

> *F-signals are gates; P-signals are gradients.*

- **F**: 단일 트립 → 자동 `git revert HEAD`. 0 tolerance.
- **P**: 단일 개선 → iter "clean" 으로 마크. 1 improvement 충분.
- **Stagnation**: 3+ 연속 iter 에 P 개선 0건 → `logs/session_log.md` 에 `STAGNATION` 기록. auto-revert 없음.

이 비대칭이 *"무엇을 하지 말아야 하는가는 엄격, 무엇을 해야 하는가는 자유"* 의 형식. Claude Code 가 iter 마다 *smallest defensible gap* 을 자율 선택하되 architecture 정합성은 절대 깨지 못함.

---

## 1k iter 실행 결과 (→ [[raw/notion-meeting-2026-05-18]])

이 14개 signal 로 1000 iter 무한 루프 실행:
- **0/1000 task solved properly**
- AU 가 *시작도 못 함* — "lack of material"
- 보고서: `raw/attachments/notion-meeting-2026-05-18/test20_iter1_to_999_report.html`

진단:
- F-signals 가 *"손코딩 detector 추가"* 길을 막아 *"기존 방식으로 score 올리기"* 를 차단.
- 그러나 *대안 경로 (compare → extract_pattern → AU)* 가 충분히 *재료* 를 만들지 못해 AU 진입조차 불가.
- 즉 F-gate 는 작동 (architecture 정합성 유지), 그러나 P-gradient 가 *움직일 공간* 이 안 만들어진 상태.

다음 진단 영역: `compare()` 와 `extract_pattern` 이 AU 의 입력으로 충분한 *재료 (material)* 를 생산하는가.

---

## 관련
- [[arbor]] — 시스템 허브
- [[arbor-prompt-spec]] — 7대 결함 → 7대 제약 → 14 signals 발전 흐름
- [[arbor-modules]] — 모듈 인벤토리, F-signals 의 frozen 파일 출처
- [[anti-unification]] — P2 / P3 / P6 의 핵심 메커니즘
- [[arckg-3repository]] — F5 (static/dynamic 분리) 의 출처
- [[interpolation-extrapolation]] — P1 의 Chollet 정의 출처

## 열린 질문
- **F8 의 정밀화** — *"score-chasing"* 을 그 외 정당한 active_operators.py 수정과 어떻게 구분할 것인가? 현 정의 (memory.py 등 동반 수정 요구) 가 너무 엄격하거나 우회 가능한가?
- **P-signals 사이의 trade-off** — P6 (code removal) 와 P5 (matcher 추가) 가 동시 개선 가능한가, 아니면 일방이 다른 일방을 제한하는가?
- **Stagnation 의 처리** — 3+ iter 정체 시 *informational only* 인데, 그럼 어떤 *action* 으로 이어져야 하는가? 사용자 개입 권고? 아니면 iter strategy 자동 변경?
- **AU "lack of material"** — *compare 가 어떤 재료를 만들어야 AU 시작이 가능한가* 의 형식 정의가 필요.
