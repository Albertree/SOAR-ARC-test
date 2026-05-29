# SLICE 1 — Ralph Loop Objective (무인 자율 개발)

> 이 문서는 `PROMPT.md` 와 **함께** 읽는다. PROMPT.md = 불변 철학 (single
> ultimate goal, smallest defensible gap, F1-F8 / P1-P6). 이 문서 = *현재
> 타겟인 Slice 1* 의 구체. Slice 1 통과 시 `SLICE_2_LOOP.md` 로 교체되고
> PROMPT.md 는 절대 안 바뀐다.
>
> **압축 경고**: 이 문서는 의도적으로 길다. 요약본이 아니다. 각 iteration 은
> §0 의 원본을 *정독* 한 뒤 작업한다 — 이 문서만 보고 "그럴싸하게" 구현하지
> 말 것.

---

## 0. 매 iteration 시작 전 반드시 정독 (압축본 아닌 원본)

이 다섯을 *매번* 읽는다. 이 문서는 그 요약이 아니라 *실행 맥락* 일 뿐이다.

1. **`~/Desktop/wiki/raw/notion-idea-arbor-flow-three-task-description-2026-05-21.md`**
   — 사용자가 직접 쓴 easy000a / easy000b / 08ed6ac7 풀이 시나리오 원본.
   *왜 각 단계를 그렇게 하는지의 당위성* 이 여기 있다. Slice 1 은 그중
   **easy000a 문단** (첫 큰 문단) 이 대상.
2. **`~/Desktop/wiki/wiki/arbor-execution-trace.md`**
   — 11 모듈 각각의 역할·현 코드·다음 액션 + **7 원리** + Slice 계획.
3. **`~/Desktop/wiki/wiki/arbor-dsl-taxonomy.md`**
   — DSL 4종 분리, 씨앗 함수 명세, scope selector = filter+util+property.
4. **`~/Desktop/wiki/wiki/arbor-open-questions.md`**
   — 아직 답 없는 부분. Slice 1 범위에서 막히면 여기 먼저 확인.
5. **`CLAUDE.md` + `docs/INVARIANTS.md`** — 아키텍처 불변 + F1-F8/P1-P6.

`~/Desktop/wiki/ARBOR_flow_description/easy000a.json` 의 실제 grid 도 직접 열어
값을 확인할 것 (추측 금지).

---

## 1. Slice 1 이 무엇인가 — 그리고 왜 이렇게 시작하는가

**Vertical slice**: *한 쉬운 task 류가 input→output 전체 파이프라인을 완주*
하게 만든다. 모든 모듈의 뼈대를 먼저 깔지 않는다 (depth-first ✗). *한 task 가
끝에서 끝까지 풀리는* 최소 모듈 집합 (completion-first ✓).

**타겟 task (둘 다 통과해야 함):**
- `easy000a` — 6×6, 1×1 객체 1개. 출력이 input 과 *무관하게 고정* `(5,5) 빨강(2)`
- `easy000a2` — 같은 메커니즘, *다른 고정 출력* (예 `(0,0) 초록(3)`)

**둘 다 같은 메커니즘으로 풀린다**: 모든 example `G1`(출력 그리드)이 동일 →
role-aligned 비교 → 모든 property COMM → 그 공통 grid 를 test `G1` 으로 복사.

**왜 G0(입력)을 안 보는가** (당위성): easy000a 는 출력이 다 똑같아서 입력을
볼 필요가 없다. 이건 *의도된 가장 쉬운 출발점* — COMM-copy 경로가 작동하고
*일반적* (한 task 답을 하드코딩한 게 아님) 임을 먼저 증명하기 위함. G0 분석이
*정답에 쓰이는* 단계는 Slice 2 (easy000b) 다.

**왜 easy000a2 가 필요한가**: easy000a 만 통과시키면 `PredictByAllPairCommOp`
가 `(5,5)빨강` 을 하드코딩해도 통과해버린다. easy000a2 (다른 고정 출력)가
그걸 잡는다 — *값-agnostic* 한 일반 모듈만 둘 다 통과.

---

## 2. 7 원리 (모든 모듈이 위반하면 안 되는 설계 제약)

원본: arbor-execution-trace §7원리. (raw prose 의 사용자 원문 인용 포함)

| P# | 원리 | 함의 |
|----|------|------|
| **P1** | 계층 깊이는 *필요* 에 의해 들어간다 | descent 는 막혔을 때만. 강제로 PIXEL 까지 내려가지 않음 |
| **P2** | 비교는 *동일 레벨* 끼리 | GRID↔GRID, OBJECT↔OBJECT. 레벨 교차 비교 금지 |
| **P3** | 정답에는 *근거* 가 있어야 함 (값보다 *이유*) | 무작위·brute 값 제출 금지. 모든 예측은 논리적 근거 |
| **P4** | 근거는 *비교의 결과* 에서 나옴 | COMM/DIFF 가 유일한 정보원 |
| **P5** | 변수의 출처는 **G0** (test 엔 G1 없음) | 예측 program 이 G1 을 입력으로 받으면 안 됨 |
| **P6** | *2개씩* 짝지어 비교 | 3-way 비교 없음. N개면 pairwise |
| **P7** | 모든 정보는 *symbolic dict + json* | 벡터·임베딩 금지. 사람이 읽을 수 있는 symbolic |

Slice 1 에서 특히 P1 (막혀야 descend), P2 (레벨 동일), P4 (COMM 으로 예측),
P6 (pairwise) 가 직접 작동한다.

---

## 3. easy000a 실제 grid 와 단계별 풀이 시퀀스

### 실제 값 (json 에서 직접 확인됨)

| | G0 (input) | G1 (output) |
|---|---|---|
| **P0** | (1,1) 빨강(2) | **(5,5) 빨강(2)** |
| **P1** | (1,4) 파랑(1) | **(5,5) 빨강(2)** |
| **Pa** | (4,2) 노랑(4) | **? → (5,5) 빨강(2)** |

모든 G1 이 *완전히 동일*. ← Slice 1 의 핵심 사실.

### 풀이 시퀀스 (WM 로그가 닮아야 할 *형태* — 단계 수 정확 일치는 불필요, §8)

```
[TASK level]
  task.property = pair-count (example=2, test=1) 확인
  형제 TASK 없음 → Inter 비교 대상 0 → 비교 자연 skip (P1: 비교할 게 없음)
  → descend (PAIR 로)

[PAIR level]
  scope = select(Task, level=Pair) → {P0, P1, Pa}
  Inter-Pair, Pair-level on grid-count, pairwise 3쌍 (P6):
    compare(P0, P1) → COMM (2,2)
    compare(P1, Pa) → DIFF (2,1)
    compare(P0, Pa) → DIFF (2,1)
  goal(B): "Pa 에 빠진 grid(=출력) 만들기" — grid-count 다수결 2 vs Pa 의 1
  grid-count++ 하는 DSL 없음 → 막힘 (P1) → descend (goal 은 GoalStack 유지)

[GRID level]
  goal 구체화(B): 만들 Gx 의 {size, color, contents} 를 구하자
  ① Intra-Pair, Grid-level (한 pair 안 형제 G0↔G1):
       compare(select(P0,Grid), select(P0,Grid)) → P0.G0 ↔ P0.G1 = DIFF
       compare(select(P1,Grid), select(P1,Grid)) → P1.G0 ↔ P1.G1 = DIFF
       (Pa 는 G0뿐 → 형제 없어 자연 skip)
       → input↔output 이라 DIFF, 정보 부족 (당위: 그래도 흐름상 거쳐감)
  ② Inter-Grid, Grid-level (공통부모=Task, role-aligned):
       scope_A = select(P0, Grid, role==G1)   # {P0.G1}
       scope_B = select(P1, Grid, role==G1)   # {P1.G1}
       compare(P0.G1, P1.G1) → COMM on {size, color, contents}   ★ 결정적
       compare(P0.G0, P1.G0) → 색·위치 DIFF (정답 기여 안 함)

[예측 — PredictByAllPairCommOp]
  모든 example G1 이 role-aligned 비교에서:
    size:     COMM (6×6)        → Pa.G1.size = 6×6
    color:    COMM ({0,2})      → Pa.G1.color = {0,2}      (P4: 비교 COMM 이 근거)
    contents: COMM (동일 grid)  → Pa.G1.contents = P0.G1.contents
  → Pa.G1 = 공통 G1 = (5,5)빨강

[OUT]  K 가 Pa.G1 을 output-link 로 제출
```

**결정적 비교 한 줄**: *Inter-Grid, role==G1, {size·color·contents} 전부 COMM
→ test G1 = 공통값.* 나머지 비교(PAIR grid-count, Intra-Pair, G0 역할)는 흐름상
거쳐가지만 정답엔 직접 기여 안 함 — 이게 "이상적 흐름은 거치되 정답은 일부
비교에서만" 의 구체 사례 (§8 의 완화된 검증과 연결).

---

## 4. 모듈 범위

### IN — 빌드/와이어링 대상 (각 모듈의 현 코드·다음 액션은 arbor-execution-trace 정독)

| 모듈 | Slice 1 에서의 역할 | 다음 액션 (상세는 arbor-execution-trace) |
|------|---------------------|------------------------------------------|
| **D** (DSL: property + util ONLY) | 비교 대상·예측값의 재료 | `procedural_memory/DSL/{property,util}/` 함수형 wrapper (§6) |
| **C** (RecursiveComparisonController) | Intra/Inter 비교 schedule (§5) | `agent/compare_scheduler.py` — scope selector + Intra/Inter |
| **A** (HierarchicalDescent) | 현 레벨에서 actionable 결과 없으면 descend (P1) | `NeedsDescendRule` + `DescendOperator.effect` |
| **B** (GoalStack) | "Pa 출력 만들기" → "Gx.{size,color,contents}" 진화 | minimal GoalStack + evolve 2종 |
| **K** (OutputChannel) | 예측 G1 을 output-link 로 | `agent/io.py:emit_answer` + `SubmitOperator.effect` |
| **PredictByAllPairCommOp** | example G1 들이 property COMM → test G1 = 공통값 | Slice-1 전용 operator. **값-agnostic** 필수 |

### OUT — Slice 1 에서 만들지 말 것 (이후 slice)

- **E** (activation rule), **F** (synthesizer), **G** (per-pair program),
  **H** (anti-unification), **I** (variable-origin), **J** (skill library)
- **object / pixel level property** — Slice 1 은 GRID 에서 멈춘다 (easy000a 가
  grid-level COMM 만으로 풀리므로). object/pixel 은 Slice 2 (easy000b).
- 비교 **후처리 top-k**, **coordinate filter** — 폭증이 없으니 불필요.

---

## 5. 모듈 C 의 정확한 정의 (구 7규칙 → 2종 + scope, 압축 아님)

> 정정 출처: arbor-execution-trace §모듈 C (2026-05-29). 구 C1-C7 은 4개
> 관심사가 섞인 것이라 단순화됨. **이 정의를 그대로 따를 것 — 7규칙으로
> 되돌리지 말 것.**

```
비교 단위:  compare(scope_A, scope_B)
            · 항상 N:N (1:1 은 N=1 인 특수 케이스. cardinality 는 변수 아님)
            · 결과 = 비교 receipt 집합 (각 receipt 에 COMM/DIFF + score)
            · 구현은 기존 ARCKG/comparison.py:compare() 재사용

scope:      select(anchor, level, predicate?)
              = filter( elements-at(anchor, level), predicate )
            · elements-at = util (grids-of / objects-of / pixels-of)
            · predicate   = property/relation 식 (생략 시 전체)
            · 예: select(P0.G0, object, color-of(o)==5)  # 회색 object 만

두 분석 종류 (재귀적으로 중첩):
  · Intra-[Level]:  한 부모 아래 형제끼리       (예: 한 pair 의 G0↔G1)
  · Inter-[Level]:  role-aligned 다른 부모끼리   (예: P0.G1 ↔ P1.G1)

Slice 1 에서 쓰는 것: Intra-Pair(Grid-level), Inter-Grid(Grid-level, role==G1).
폭증 제어 (top-k 후처리 / coordinate predicate) 는 Slice 1 미사용.
```

**C–D 결합**: scope selector 가 D 의 `filter`+`grids-of`+property 를 호출하므로
**D 를 C 보다 먼저 (또는 같이) 구현한다.**

---

## 6. 모듈 D — Slice 1 필요 함수 (전부, 압축 없음)

easy000a 는 **GRID level 에서 끝나므로** object/pixel property 불필요.
ARCKG 노드의 기존 `to_json()` 키를 *함수형 wrapper* 로 노출 (값 재계산 ✗, 노출 ○).

```
util:
  pairs-of(task)   → [P0, P1, Pa]
  grids-of(pair)   → [G0, G1]  (Pa 는 [G0])
  role-of(grid)    → G0(input) | G1(output)
  filter(set, pred)→ scope selector 의 핵심 building block

property (task):   pair-count        (= example/test pair 수)
property (pair):   grid-count
property (grid):   size              (예: 6×6)
                   color             (color set, 예: {0,2})
                   contents          (그리드 셀 전체 — 하나라도 다르면 DIFF)
```

OUT: object/pixel property (`area, coordinate, shape, symmetry, ...`) 는
Slice 2+ 까지 만들지 않는다.

---

## 7. Per-iteration 목적성 (각 loop step 이 gap 을 고르는 법)

각 iteration = "easy000a + easy000a2 통과" 를 향한 *가장 작은 한 걸음*.
probe 를 *현미경* 으로 써서 진단 후, *우선순위 가장 높은 미완 모듈* 을 채운다.

**우선순위:**
1. **P0 — C + D.** 비교 스케줄링과 property DSL 없으면 아무것도 안 돈다.
   `select`/`compare`/property wrapper 가 없거나 깨졌으면 그게 이 iter 의 gap.
2. **P1 — A + B + K + PredictByAllPairCommOp.** C+D 가 돌면 descent·goal
   stack·예측·제출 경로가 필요.
3. **Integration.** 여섯이 다 있으면 gap 은 "아직 하나의 solve 로 안 엮임" —
   추가하지 말고 *와이어링*.

**진단 패턴 (probe = easy000a / easy000a2 풀이 출력):**
- `select`/`compare` 크래시 → D 또는 C gap
- TASK/PAIR 에서 못 내려감 → A gap (descend 미작동)
- GRID 도달했으나 예측 안 함 → PredictByAllPairCommOp / K gap
- **easy000a2 틀리고 easy000a 만 맞음 → PredictByAllPairCommOp 가 답을
  하드코딩** (일반-모듈 위반. 값-agnostic 으로 고칠 것, 특수처리 ✗)

각 iter 의 진단 2-3문장을 session_log 맨 위에 (PROMPT.md §Step 5 양식).

---

## 8. 합격 기준 (완화됨 — "N단계 일치" 류 문구를 이게 덮어씀)

Slice 1 통과 조건 = **다음 전부**:
- `easy000a` **그리고** `easy000a2` 가 올바른 출력 grid 생성
- 4 관찰 기준:
  1. **작동** — 모듈/비교가 에러 없이 돈다
  2. **통일성** — 같은 종류 작업이 같은 모듈로 (모듈 안 task 전용 분기 ✗).
     *모듈에만 적용 — 풀이로 생긴 program/action-sequence 는 overfit OK.*
  3. **접근성** — 풀이가 정답 *방향* 으로 간다 (우회·실패 거쳐도)
  4. **탐색 건전성** — brute-force 가 있어도 *의미있는 범위* 안

**요구하지 않는 것**: WM 로그가 raw prose 의 흐름과 *단계 수까지 정확히
일치* 하는 것. 초기 ARBOR 는 이상적 인간 흐름을 1:1 재현 못한다. 중간에
*의미있는 brute-force* 가 들어가도 전체 *형태* 가 나오면 통과.

---

## 9. Slice-1 가드레일 (INVARIANTS.md F1-F8 에 추가)

- **object/pixel-level property DSL 만들지 말 것.** Slice 1 은 GRID 에서 멈춘다.
- **모듈 E/F/G/H/I/J / anti-unification 와이어링 만들지 말 것.** easy000a/a2 는
  합성 불필요.
- **PredictByAllPairCommOp 는 값-agnostic.** 리터럴 `(5,5)`/`red` 등장 ✗ —
  *공통 G1 이 무엇이든* 복사.
- **C 는 정확히 2종 (Intra/Inter) + scope predicate.** 7규칙 나열로 되돌리지
  말 것. top-k/coordinate-filter 는 후처리/scope predicate 이고 후속 slice 의
  폭증에만.
- **transformation DSL 은 `make_grid`/`coloring` 둘뿐** (F3, 영구).

---

## 10. Slice 1 통과 시

1. `logs/session_log.md` 에 `SLICE 1 COMPLETE` 블록 — 두 task 의 probe 결과
   + 4 관찰 기준 자가평가.
2. **멈춤** — Slice 2 를 자율로 시작하지 말 것. Slice 2 (easy000b: G0 분석,
   intra 비교가 정답에 기여, activation rule, anti-unification) 는 human-gated
   전환이다. `SLICE_2_LOOP.md` 를 기다린다.
