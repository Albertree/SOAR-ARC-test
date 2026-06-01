---
title: ARBOR ↔ SOAR 메모리 매핑 — "semantic memory = 영속화된 WM"
aliases: [arbor-soar-memory-mapping, semantic은 영속 WM, ARBOR 메모리 재명명]
tags: [#topic/cognitive-architecture, #topic/soar, #topic/arckg, #status/insight, #2026]
created: 2026-05-31
updated: 2026-05-31
sources:
  - 2026-05-31 세션 (ARC-solver SLICE_1_DEV 구현 논의 중 자각)
  - "[[soar-manual-reference]] (공식 SOAR 정의 정본)"
  - "[[arbor]] / arbor.md (ARBOR 3 LTM 역할 정의)"
---

# ARBOR ↔ SOAR 메모리 매핑

> **변곡점 노트**: ARBOR가 "semantic memory"라 부르던 ARCKG 디스크 그래프는, 공식 SOAR 정의로는 semantic이 **아니라 "디스크에 영속화된 Working Memory"** 다. 이 재명명 하나가 "노드는 WM에서 태어나나 semantic에서 태어나나" 의 교착을 푼다.

## 한 줄 정의
ARBOR의 메모리 3종을 [[soar-manual-reference|공식 SOAR 정의]]에 대보면, **procedural·episodic·substate·정답근거는 정렬되거나 의도적 특수화**지만, **"semantic memory"는 misnomer** — 그건 SOAR semantic(탈맥락·과제횡단 일반 사실)이 아니라 *현재 과제의 영속화된 WM* 이다.

## 핵심
- **SOAR semantic ≠ ARCKG.** SOAR semantic = 탈맥락·과제횡단 일반 사실, 의도적 store + cue 인출, 분리된 다중 그래프 (→ [[soar-manual-reference]] §8). ARCKG = *이 과제*의 단일연결·지각파생 구조 그래프. contextual + 단일연결 + 지각파생 = **WM의 성질**이다.
- **"디스크에 저장됨" ≠ "semantic memory".** 이 혼동이 misnomer의 출처. SOAR는 WM를 RAM에 두지만, ARBOR는 *검사·비교·anti-unification 입력* 을 위해 WM를 디스크에 투영하려는 것 — 정당한 엔지니어링 욕구지 semantic이 아님.
- **교착 해소**: ARCKG-디스크를 *WM의 영속 투영*으로 보면 노드는 **항상 WM에서 태어나고**, 디스크는 그 durable projection. "승격(promotion)"이 아니라 **flush**(하강이 방문·확정한 노드를 디스크로 내려쓰기). load 시점엔 아무것도 flush 안 함 → lazy materialization과 자동 일치 (→ [[arbor-open-questions]] "lazy materialization").
- **진짜 SOAR semantic 슬롯은 따로, 거의 비어있음.** 과제횡단 일반 사실(색↔이름, object 개념 등)용. ARC는 과제가 일부러 새로우니 횡단 사실이 얇은 게 정상 — Slice 1에선 비워둔다. **과제별 grid를 거기 쏟지 말 것** (그게 `task.save()` 즉시 디스크 덤프의 범주 오류였음).

## 상세

### 5축 비교

| 축 | 공식 SOAR | ARBOR 설계 | 판정 |
|---|---|---|---|
| **Semantic** | 탈맥락·과제횡단 일반 사실. store+cue 인출. attribute 상수. 분리된 다중 그래프 | ARCKG = 현재 과제의 5계층 노드/속성/관계 그래프 | **크게 어긋남** ← 핵심 |
| **Procedural** | productions. *매 사이클 match-fire되는 능동 기반*. chunking이 새 rule 추가 | DSL 모듈(C/D/A/B) + 발견된 transformation rule | 정렬 (*불린다* — 걱정 기우) |
| **Episodic** | 매 사이클 WM 스냅샷 자동 기록, cue 인출 | 풀이 에피소드(현재 빈 상태) | 정렬 (정신 동일) |
| **Impasse→substate** | 4종 막힘 → *열린* 하위 문제공간 | 막힘 → *고정 계층* 하강(TASK→PAIR→GRID), P1 | 정렬 + 의도적 특수화 |
| **정답 근거** | preference 8단계 + RL 수치 튜닝(탐색) | COMM 비교에서 *연역적* 도출, brute 금지(P3/P4) | 의도적 분기(탐색→연역) |

### 결정적 어긋남 — "semantic memory"의 정체

ARBOR는 *현재 과제의 노드/속성/관계 그래프*를 semantic이라 부른다. SOAR 기준으론 아니다:

- **SOAR semantic** = 탈맥락("색 2 = 빨강", "1×1 = pixel 개념"), 과제횡단, 분리된 다중 그래프, cue 인출.
- **ARCKG 디스크** = 이 과제에 묶인(contextual), 단일 연결 트리(task-rooted), 지각 파생, 이 과제 푸는 데 씀.

세 성질(contextual·단일연결·지각파생)이 전부 **Working Memory의 성질**이다. 결론:

> ARBOR가 "semantic memory"라 부른 ARCKG 디스크 그래프는, SOAR 기준 **"디스크에 영속화된 Working Memory"**. "semantic"이라는 이름은 *"디스크 저장 = semantic memory"* 혼동에서 온 **misnomer**.

이게 왜 변곡점이냐 — "노드는 WM에서 태어나나 semantic 디스크에서 태어나나"(이전 논의의 가/나 갈림)가 이걸로 통합된다. ARCKG-디스크 = *WM의 영속 투영*이면 노드는 항상 WM에서 태어나고, 디스크는 투영일 뿐. **promotion이 아니라 flush.** load는 빈 채로 → lazy.

(주: ARCKG-디스크의 "영속" 욕구는 사실 *episodic* 과도 가깝다 — 과제 구조의 스냅샷이 에피소드 간 [[anti-unification]] 입력이 되므로. WM-투영이냐 episodic-스냅샷이냐는 아직 열린 질문.)

### 나머지 축

- **Procedural**: "저장만 되고 안 불리는 메모리?"는 기우. SOAR procedural은 매 사이클 불리는 능동 기반이고, ARBOR에서도 DSL 모듈(C/D/A/B)이 곧 풀이 substrate라 *항상* 불린다. 학습된 transformation rule은 fast-path 재사용 (→ [[arbor]] Fast path). 둘 다 procedural, SOAR 정렬.
- **Episodic**: 풀이 trace를 *하강 스텝마다* 스냅샷하면 SOAR 정렬 + 에피소드 간 anti-unification 입력.
- **Substate**: SOAR substate는 *열린* 문제공간인데 ARBOR는 "데이터 계층 한 칸 하강"으로 **특수화**. 덜 일반적이지만 더 해석 가능 — "당위성" 목표에 부합. 단 ARBOR는 SOAR 4종 막힘 중 사실상 *no-change류*("이 레벨선 진전 불가 → 더 깊이")만 주로 씀. conflict/constraint-failure는 자연 대응이 약함 ([[impasse]]).
- **정답 근거**: SOAR는 preference+RL 탐색, ARBOR는 COMM 연역. 버그 아니라 노선 선택 — [[coarse-to-fine-abductive-reasoning]] 와 일관. 유지.

### 방향 (권장)

1. **개념 재명명**: ARCKG 디스크 = "semantic memory" 아님 → **"영속화된 WM"**. 노드는 WM에서 태어나고 디스크는 투영. load는 빈 채로.
2. **진짜 semantic 슬롯은 따로**: 과제횡단 일반 사실용, Slice 1엔 비움. 과제 grid 안 넣음.
3. **Procedural/Episodic/Substate/근거**: 위 분석대로 대체로 유지(정렬 또는 정당한 특수화).

## 관련
- [[soar-manual-reference]] — 이 노트가 대조한 SOAR 표준 정의(특히 §1 WM, §7 chunking, §8 semantic, §9 episodic).
- [[soar]] — 우리 위키 SOAR 허브.
- [[arckg-wm-design]] — WM 4영역 + SOAR 호환 수정. 이 재명명을 WM 설계에 반영할 자리.
- [[arckg-research]] / [[arckg]] — 5계층 KG = (재명명 후) 영속 WM 투영.
- [[arbor]] — 3 LTM 역할 정의(arbor.md). 이 노트가 그 semantic 라벨을 정정.
- [[coarse-to-fine-abductive-reasoning]] — COMM 연역 노선의 근거.
- [[impasse]] / [[chunking]] — substate·학습 축의 SOAR 대응.

## 후속
- **각 기억에 *무엇이* 들어가나** → [[arbor-memory-contents]] 에서 정함 (semantic = DreamCoder식 DSL 추상 라이브러리, DSL 두 얼굴, 타입 시스템 분리). 아래 "semantic엔 뭐가?" 열린 질문의 답.

## 열린 질문
- **ARCKG-디스크는 "영속 WM"인가 "episodic 스냅샷"인가?** 둘 다 WM-파생이지만 영속/투영의 목적이 다름. anti-unification 입력 역할은 episodic 쪽에 더 가까울 수 있음.
- **재명명 반영 범위**: 개념·문서만 고칠지(코드 폴더명 `semantic_memory/` 유지), 아니면 폴더/구조까지 재배치하고 빈 SOAR-semantic 슬롯을 실제로 둘지. 전자는 마이그레이션 0, 후자는 정합성↑·작업량↑.
- **진짜 SOAR-semantic을 ARBOR가 언제 쓰게 되나?** 과제횡단 일반 사실(색↔이름, object 개념, 학습된 property 정의)이 의미를 갖는 slice는 어디인가.
- 부재한 `ARC-solver/CLAUDE.md §Memory` 를 이 합의로 채워 코드의 끊긴 REF 복구 필요.
